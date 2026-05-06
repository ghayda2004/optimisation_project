import math
import logging
from typing import List, Dict, Any, Tuple
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

# Configuration du logger
logger = logging.getLogger(__name__)

# --- CONSTANTES LOGISTIQUES ---
VITESSE_KMH = 50
TEMPS_STOP_SEC = 600
DISTANCE_MAX_M = 150000  # 150km
TEMPS_MAX_SEC = 28800    # 8h (Work day)

def get_distance_matrix(points: List[Tuple[float, float]]) -> List[List[int]]:
    """
    Calcule une matrice de distances complète entre tous les points en utilisant
    la formule de Haversine (distance sphérique).
    
    Args:
        points: Liste de tuples (lat, lng)
    Returns:
        Matrice carrée des distances en mètres (entiers).
    """
    n = len(points)
    matrix = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            lat1, lon1 = math.radians(points[i][0]), math.radians(points[i][1])
            lat2, lon2 = math.radians(points[j][0]), math.radians(points[j][1])
            
            # Formule de Haversine
            dlon = lon2 - lon1
            dlat = lat2 - lat1
            a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
            c = 2 * math.asin(math.sqrt(a))
            # Rayon de la Terre : 6371000 mètres
            matrix[i][j] = int(c * 6371000)
    return matrix

def optimize_routes(orders: List[Dict[str, Any]], drivers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Moteur d'optimisation OR-Tools (VRP). Calcule les tournées en respectant
    la capacité des véhicules, la distance maximale et le temps de travail.
    
    Args:
        orders: Liste des dictionnaires de commandes avec lat, lng, weight, id.
        drivers: Liste des dictionnaires de chauffeurs avec lat, lng, capacity, id.
    Returns:
        Liste de dictionnaires représentant les tournées optimisées.
    """
    if not orders or not drivers:
        logger.warning("Optimisation impossible : liste de commandes ou de chauffeurs vide.")
        return []

    # 1. Validation des entrées et préparation des points
    valid_orders = []
    for o in orders:
        if o.get('lat') is None or o.get('lng') is None:
            logger.warning(f"Commande {o.get('id', 'Inconnue')} ignorée : Coordonnées GPS manquantes.")
            continue
        valid_orders.append(o)

    if not valid_orders:
        logger.error("Aucune commande valide avec coordonnées GPS n'a été trouvée.")
        return []

    # Le dépôt est basé sur la position du premier chauffeur
    depot_lat = drivers[0].get('lat')
    depot_lng = drivers[0].get('lng') or drivers[0].get('lon')
    
    # Construction de la liste des points : Index 0 = Dépôt
    points = [(depot_lat, depot_lng)] + [(o['lat'], o['lng']) for o in valid_orders]
    
    # 2. Création du modèle OR-Tools
    dist_matrix = get_distance_matrix(points)
    num_vehicles = len(drivers)
    manager = pywrapcp.RoutingIndexManager(len(dist_matrix), num_vehicles, 0)
    routing = pywrapcp.RoutingModel(manager)

    # 3. Callback de Distance et Coût
    def distance_callback(from_index, to_index):
        return dist_matrix[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]
    
    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # 4. Dimension Distance (Limite 150km)
    routing.AddDimension(
        transit_callback_index,
        0,  # Pas de slack
        DISTANCE_MAX_M,
        True,  # Cumul repart à zéro pour chaque véhicule
        "Distance"
    )

    # 5. Dimension Temps
    def time_callback(from_index, to_index):
        node_to = manager.IndexToNode(to_index)
        dist = dist_matrix[manager.IndexToNode(from_index)][node_to]
        # Durée de trajet (sec) + Temps de service (si ce n'est pas le dépôt)
        travel_time = dist / (VITESSE_KMH / 3.6)
        service_time = TEMPS_STOP_SEC if node_to != 0 else 0
        return int(travel_time + service_time)

    time_callback_index = routing.RegisterTransitCallback(time_callback)
    routing.AddDimension(time_callback_index, 0, TEMPS_MAX_SEC, True, "Time")

    # 6. Dimension Capacité
    def demand_callback(from_index):
        node = manager.IndexToNode(from_index)
        if node == 0: return 0
        return int(valid_orders[node - 1].get('weight', 1))

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    capacities = [int(d.get('vehicle_capacity', 100)) for d in drivers]
    routing.AddDimensionWithVehicleCapacity(demand_callback_index, 0, capacities, True, "Capacity")

    # 7. Paramètres de recherche et Pénalités (Disjonctions)
    # Permet de ne pas livrer un colis s'il brise une contrainte (distance/temps)
    penalty = 1000000
    for i in range(1, len(points)):
        routing.AddDisjunction([manager.NodeToIndex(i)], penalty)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search_parameters.time_limit.seconds = 5

    # 8. Résolution
    solution = routing.SolveWithParameters(search_parameters)

    # 9. Extraction des résultats
    if not solution:
        logger.warning(f"No solution found for {len(valid_orders)} orders and {num_vehicles} drivers")
        return []

    optimized_routes = []
    for vehicle_id in range(num_vehicles):
        index = routing.Start(vehicle_id)
        route_orders = []
        route_distance = 0
        
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            if node_index != 0:
                # On récupère l'objet commande complet pour le détail ultérieur
                route_orders.append(valid_orders[node_index - 1])
            
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            route_distance += routing.GetArcCostForVehicle(previous_index, index, vehicle_id)

        if route_orders:
            # Calcul de la durée totale (Trajet + Stops)
            duration_min = ((route_distance / (VITESSE_KMH / 3.6)) + (len(route_orders) * TEMPS_STOP_SEC)) / 60
            
            optimized_routes.append({
                "driver_id": drivers[vehicle_id]['id'],
                "driver_name": drivers[vehicle_id].get('name', f"Chauffeur {drivers[vehicle_id]['id']}"),
                "driver_start_coords": {"lat": depot_lat, "lng": depot_lng},
                "order_ids": [o['id'] for o in route_orders],
                "full_orders": route_orders, # Gardé pour le détail des colis (Feature 3)
                "total_distance_km": round(route_distance / 1000.0, 2),
                "total_duration_min": round(duration_min, 2)
            })

    return optimized_routes