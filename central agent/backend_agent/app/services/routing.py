import openrouteservice
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import logging
import numpy as np
from app.core.config import settings

logger = logging.getLogger(__name__)

# --- CONFIGURATION LOGISTIQUE 
VITESSE_MOYENNE_KMH = 30 
TEMPS_STOP_LIVRAISON_SEC = 600  # 10 minutes
TEMPS_TRAVAIL_MAX_SEC = 32400   # 9 heures
MARGE_RESERVE_SEC = 10800      # 3 heures
TEMPS_PLANIF_MAX_SEC = TEMPS_TRAVAIL_MAX_SEC - MARGE_RESERVE_SEC # 6h
CAP_CAMION_KG = 50

def get_ors_matrices(points_lat_lon):
    """
    Récupère les matrices de DISTANCE et de DURÉE via OpenRouteService.
    """
    coords_lon_lat = [[lon, lat] for lat, lon in points_lat_lon]
    client = openrouteservice.Client(key=settings.ORS_API_KEY)
    
    try:
        logger.info(f"Appel ORS pour {len(coords_lon_lat)} points...")
        # On demande les deux métriques : distance et durée
        result = client.distance_matrix(
            locations=coords_lon_lat,
            profile='driving-car',
            metrics=['distance', 'duration']
        )
        return result['distances'], result['durations']
        
    except Exception as e:
        logger.error(f"Erreur API ORS: {e}. Utilisation du fallback Haversine.")
        # Fallback simplifié si l'API échoue
        n = len(points_lat_lon)
        dist_m = np.zeros((n, n), dtype=int)
        time_m = np.zeros((n, n), dtype=int)
        for i in range(n):
            for j in range(n):
                d = int((((points_lat_lon[i][0]-points_lat_lon[j][0])**2 + 
                          (points_lat_lon[i][1]-points_lat_lon[j][1])**2)**0.5) * 111000)
                dist_m[i][j] = d
                time_m[i][j] = int((d / 1000) / VITESSE_MOYENNE_KMH * 3600)
        return dist_m.tolist(), time_m.tolist()

def optimize_routes(dist_matrix, time_matrix, weights, deadlines, num_vehicles, depot_index=0):
    """
    Moteur OR-Tools avec la logique de rentabilité et contraintes du Code 2.
    """
    manager = pywrapcp.RoutingIndexManager(len(dist_matrix), num_vehicles, depot_index)
    routing = pywrapcp.RoutingModel(manager)

    # 1. OBJECTIF : Minimiser la distance (Carburant)
    def distance_callback(from_index, to_index):
        return int(dist_matrix[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)])
    
    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # 2. DIMENSION TEMPS : Max 6h (Planning) + Gestion des Stops
    def time_callback(from_index, to_index):
        # On ajoute le temps de trajet + le temps de service au client
        node_to = manager.IndexToNode(to_index)
        service_time = TEMPS_STOP_LIVRAISON_SEC if node_to != depot_index else 0
        return int(time_matrix[manager.IndexToNode(from_index)][node_to]) + service_time

    time_callback_index = routing.RegisterTransitCallback(time_callback)
    routing.AddDimension(time_callback_index, 3600, TEMPS_PLANIF_MAX_SEC, True, 'Time')
    time_dimension = routing.GetDimensionOrDie('Time')

    # 3. DEADLINES : Fenêtres de temps (Durée de vie du colis)
    for node_idx, deadline in enumerate(deadlines):
        if node_idx == depot_index: continue
        index = manager.NodeToIndex(node_idx)
        time_dimension.CumulVar(index).SetRange(0, int(deadline))

    # 4. CAPACITÉ : Max 50kg par camion
    def demand_callback(from_index):
        return int(weights[manager.IndexToNode(from_index)])
    
    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index, 0, [CAP_CAMION_KG]*num_vehicles, True, 'Capacity'
    )

    # Paramètres de recherche
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search_parameters.time_limit.seconds = 5

    solution = routing.SolveWithParameters(search_parameters)

    if not solution:
        return None

    # Extraction des résultats 
    results = {'total_distance': 0, 'vehicles_used': 0, 'routes': {}}
    
    for v_id in range(num_vehicles):
        index = routing.Start(v_id)
        if routing.IsEnd(solution.Value(routing.NextVar(index))): continue
        
        results['vehicles_used'] += 1
        route_data = {'path_indices': [], 'path_distance_m': 0, 'path_time_h': 0}
        
        while not routing.IsEnd(index):
            node_idx = manager.IndexToNode(index)
            route_data['path_indices'].append(node_idx)
            prev_index = index
            index = solution.Value(routing.NextVar(index))
            route_data['path_distance_m'] += routing.GetArcCostForVehicle(prev_index, index, v_id)
            
        route_data['path_indices'].append(manager.IndexToNode(index))
        route_data['path_time_h'] = solution.Value(time_dimension.CumulVar(index)) / 3600
        results['total_distance'] += route_data['path_distance_m']
        results['routes'][v_id] = route_data

    return results