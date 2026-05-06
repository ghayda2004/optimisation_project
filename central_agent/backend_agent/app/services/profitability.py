"""
FILE 5: profitability.py
Calcul du score de profit pour chaque route optimisée en soustrayant les coûts 
(carburant, main-d'œuvre, manutention) du revenu total.
"""

from app.core.config import FUEL_RATE, HOURLY_RATE, HANDLING_COST

def calculate_net_profit(
    base_revenue: float, 
    distance_km: float, 
    estimated_time_hours: float, 
    fuel_cost_per_km: float = FUEL_RATE,
    driver_hourly_wage: float = HOURLY_RATE,
    vehicle_wear_per_km: float = 0.05, 
    tolls_and_fees: float = 0.0
) -> dict:
    """
    Calcule le profit net basé sur les paramètres de coût et de revenu.
    """
    # Calcul des coûts variables
    fuel_cost = distance_km * fuel_cost_per_km
    wear_cost = distance_km * vehicle_wear_per_km
    labor_cost = estimated_time_hours * driver_hourly_wage
    
    # Coût total incluant les frais fixes (manutention/péages)
    total_costs = fuel_cost + wear_cost + labor_cost + tolls_and_fees
    
    net_profit = base_revenue - total_costs
    profit_margin = (net_profit / base_revenue) * 100 if base_revenue > 0 else 0.0
    
    return {
        "net_profit": round(net_profit, 2),
        "total_costs": round(total_costs, 2),
        "profit_margin_percentage": round(profit_margin, 2),
        "breakdown": {
            "revenue": base_revenue,
            "fuel_cost": round(fuel_cost, 2),
            "labor_cost": round(labor_cost, 2),
            "wear_cost": round(wear_cost, 2),
            "tolls_and_fees": round(tolls_and_fees, 2)
        },
        "is_profitable": net_profit > 0
    }

def calculate_profitability(routes, orders):
    """
    Point d'entrée principal pour le pipeline. 
    Enrichit les objets routes avec les données de rentabilité.
    """
    # Création d'un dictionnaire pour recherche rapide des valeurs de livraison
    # Supporte les formats dictionnaire (CSV) et objets SQLAlchemy
    order_map = {}
    for o in orders:
        o_id = o.get('id') if isinstance(o, dict) else getattr(o, 'id', None)
        o_val = o.get('delivery_value') if isinstance(o, dict) else getattr(o, 'delivery_value', 0.0)
        if o_id is not None:
            order_map[o_id] = float(o_val)
    
    enriched_routes = []
    
    for route in routes:
        # Somme des revenus pour toutes les commandes de cette route
        route_revenue = sum(order_map.get(oid, 0.0) for oid in route['order_ids'])
        
        # Coût de manutention (basé sur le nombre de stops)
        num_stops = len(route['order_ids'])
        stop_costs = num_stops * HANDLING_COST
        
        # Calcul des métriques financières
        metrics = calculate_net_profit(
            base_revenue=route_revenue,
            distance_km=route['total_distance_km'],
            estimated_time_hours=route['total_duration_min'] / 60.0,
            tolls_and_fees=stop_costs
        )
        
        # Injection des résultats dans l'objet route pour la sauvegarde en base
        route['profitability'] = metrics
        enriched_routes.append(route)
        
    return enriched_routes

def evaluate_dynamic_pickup(
    current_route_profit: float, 
    new_distance_km: float, 
    new_time_hours: float, 
    new_package_revenue: float
) -> bool:
    """
    Évalue si l'ajout d'un nouveau colis dynamique est rentable.
    """
    marginal_profit = calculate_net_profit(
        base_revenue=new_package_revenue,
        distance_km=new_distance_km,
        estimated_time_hours=new_time_hours
    )
    
    return marginal_profit["is_profitable"]