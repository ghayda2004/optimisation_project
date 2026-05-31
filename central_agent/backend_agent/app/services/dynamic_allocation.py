"""
Dynamic Order Allocation Service
Handles real-time order assignment to drivers based on marginal cost
"""

import math
import logging
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models.models import Order, Driver, Route, RouteStop
from app.core.config import FUEL_RATE, HOURLY_RATE, HANDLING_COST

logger = logging.getLogger(__name__)

VITESSE_KMH = 50
TEMPS_STOP_SEC = 600

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in kilometers"""
    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)
    
    dlon = lon2_r - lon1_r
    dlat = lat2_r - lat1_r
    a = math.sin(dlat / 2)**2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    return (c * 6371)  # Distance in km

def find_optimal_insertion_position(route_stops: List, new_lat: float, new_lng: float, orders: Dict) -> Tuple[int, float]:
    """
    Find the best position to insert the new order in the route
    Returns: (best_position, distance_added)
    """
    if not route_stops:
        return 1, 0.0
    
    # Get current order coordinates
    stop_coords = []
    for stop in route_stops:
        order = orders.get(stop.order_id)
        if order:
            stop_coords.append((order.lat, order.lng))
    
    best_position = len(route_stops) + 1
    min_distance_added = float('inf')
    
    # Try inserting at each position
    for i in range(len(route_stops) + 1):
        distance_added = 0.0
        
        if i == 0:
            # Insert at beginning
            if stop_coords:
                distance_added = haversine_distance(new_lat, new_lng, stop_coords[0][0], stop_coords[0][1])
        elif i == len(route_stops):
            # Insert at end
            distance_added = haversine_distance(stop_coords[-1][0], stop_coords[-1][1], new_lat, new_lng)
        else:
            # Insert in middle
            prev_lat, prev_lng = stop_coords[i-1]
            next_lat, next_lng = stop_coords[i]
            
            # Cost: prev -> new -> next (instead of prev -> next)
            original_dist = haversine_distance(prev_lat, prev_lng, next_lat, next_lng)
            new_dist = (haversine_distance(prev_lat, prev_lng, new_lat, new_lng) + 
                       haversine_distance(new_lat, new_lng, next_lat, next_lng))
            distance_added = new_dist - original_dist
        
        if distance_added < min_distance_added:
            min_distance_added = distance_added
            best_position = i + 1
    
    return best_position, min_distance_added

def calculate_marginal_cost_per_driver(
    new_order: Dict[str, Any], 
    db: Session
) -> List[Dict[str, Any]]:
    """
    Calculate marginal cost and profit for adding this order to each active driver
    
    Returns sorted list of drivers with cost breakdown
    """
    
    # Get all active drivers
    active_drivers = db.query(Driver).filter(Driver.is_active == True).all()
    
    if not active_drivers:
        logger.warning("No active drivers found")
        return []
    
    # Get all orders for reference
    all_orders = {}
    for order in db.query(Order).all():
        all_orders[order.id] = order
    
    results = []
    
    for driver in active_drivers:
        # Get driver's current route
        route = db.query(Route).filter_by(driver_id=driver.id, status="planned").first()
        
        if not route:
            # Driver has no route yet
            current_distance = 0.0
            current_duration = 0.0
            current_revenue = 0.0
            num_stops = 0
            best_position = 1
            distance_added = 0.0
        else:
            # Get route stops
            stops = db.query(RouteStop).filter_by(route_id=route.id).order_by(RouteStop.stop_sequence).all()
            current_distance = route.total_distance_km
            current_duration = route.total_duration_min
            
            # Calculate current revenue
            current_revenue = sum(all_orders.get(s.order_id, Order()).delivery_value or 0.0 for s in stops)
            num_stops = len(stops)
            
            # Find optimal position
            best_position, distance_added = find_optimal_insertion_position(stops, new_order['lat'], new_order['lng'], all_orders)
        
        # Calculate new distance and time
        new_distance = current_distance + distance_added
        new_duration = current_duration + (distance_added / VITESSE_KMH * 60) + TEMPS_STOP_SEC / 60
        new_stops = num_stops + 1
        
        # Calculate costs
        fuel_cost = distance_added * FUEL_RATE
        labor_cost = (distance_added / VITESSE_KMH) * HOURLY_RATE
        handling_cost = HANDLING_COST
        
        total_marginal_cost = fuel_cost + labor_cost + handling_cost
        marginal_profit = new_order.get('delivery_value', 0.0) - total_marginal_cost
        
        # Check constraints
        is_feasible = (
            new_distance <= 150 and  # Max 150 km
            new_duration <= 480 and  # Max 8 hours
            new_stops <= driver.vehicle_capacity  # Simple capacity check
        )
        
        results.append({
            'driver_id': driver.id,
            'driver_name': driver.name,
            'route_id': route.id if route else None,
            'current_distance_km': round(current_distance, 2),
            'new_distance_km': round(new_distance, 2),
            'distance_added_km': round(distance_added, 2),
            'current_stops': num_stops,
            'new_stops': new_stops,
            'current_revenue': round(current_revenue, 2),
            'new_revenue': round(current_revenue + new_order.get('delivery_value', 0.0), 2),
            'marginal_cost': round(total_marginal_cost, 2),
            'fuel_cost': round(fuel_cost, 2),
            'labor_cost': round(labor_cost, 2),
            'handling_cost': round(handling_cost, 2),
            'marginal_profit': round(marginal_profit, 2),
            'profit_margin_pct': round((marginal_profit / new_order.get('delivery_value', 1.0)) * 100, 1) if new_order.get('delivery_value') else 0,
            'is_feasible': is_feasible,
            'best_position': best_position,
            'reason': '' if is_feasible else 'Constraints violated'
        })
    
    # Sort by marginal profit (highest first = best)
    results.sort(key=lambda x: x['marginal_profit'], reverse=True)
    
    return results

def assign_order_to_driver(
    order_id: int,
    driver_id: int,
    best_position: int,
    db: Session
) -> bool:
    """
    Assign order to driver by inserting into their route
    """
    try:
        # Get order
        order = db.query(Order).filter_by(id=order_id).first()
        if not order:
            logger.error(f"Order {order_id} not found")
            return False
        
        # Get or create route for driver
        route = db.query(Route).filter_by(driver_id=driver_id, status="planned").first()
        
        if not route:
            # Create new route if doesn't exist
            route = Route(
                driver_id=driver_id,
                total_distance_km=0.0,
                total_duration_min=0.0,
                status="planned"
            )
            db.add(route)
            db.flush()
        
        # Get existing stops
        existing_stops = db.query(RouteStop).filter_by(route_id=route.id).all()
        
        # If inserting in middle, re-sequence everything after
        if best_position <= len(existing_stops):
            for stop in existing_stops:
                if stop.stop_sequence >= best_position:
                    stop.stop_sequence += 1
        
        # Create new stop
        new_stop = RouteStop(
            route_id=route.id,
            order_id=order_id,
            stop_sequence=best_position
        )
        db.add(new_stop)
        db.flush()
        
        # Mark order as assigned
        order.status_internal = "assigned"
        
        # Recalculate route metrics
        update_route_metrics(route, db)
        
        db.commit()
        logger.info(f"Order {order_id} assigned to driver {driver_id} at position {best_position}")
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error assigning order: {e}")
        return False

def update_route_metrics(route: Route, db: Session):
    """Recalculate route distance, duration, and profitability"""
    try:
        from app.services.profitability import calculate_net_profit
        
        stops = db.query(RouteStop).filter_by(route_id=route.id).order_by(RouteStop.stop_sequence).all()
        orders = {o.id: o for o in db.query(Order).all()}
        driver = db.query(Driver).filter_by(id=route.driver_id).first()
        
        if not stops or not driver:
            return
        
        # Calculate total distance and time
        total_distance = 0.0
        total_time = 0.0
        total_revenue = 0.0
        
        prev_lat, prev_lng = driver.current_lat or 36.8, driver.current_lng or 10.1
        
        for stop in stops:
            order = orders.get(stop.order_id)
            if order:
                distance = haversine_distance(prev_lat, prev_lng, order.lat, order.lng)
                total_distance += distance
                total_time += (distance / VITESSE_KMH * 60) + TEMPS_STOP_SEC / 60
                total_revenue += order.delivery_value or 0.0
                prev_lat, prev_lng = order.lat, order.lng
        
        route.total_distance_km = round(total_distance, 2)
        route.total_duration_min = round(total_time, 2)
        
        # Calculate profitability
        profit_metrics = calculate_net_profit(
            base_revenue=total_revenue,
            distance_km=total_distance,
            estimated_time_hours=total_time / 60.0
        )
        
        # Update or create profitability record
        from app.models.models import RouteProfitability
        profit_record = db.query(RouteProfitability).filter_by(route_id=route.id).first()
        
        if profit_record:
            profit_record.total_revenue = total_revenue
            profit_record.total_cost = profit_metrics['total_costs']
            profit_record.gain_net = profit_metrics['net_profit']
            profit_record.margin_pct = profit_metrics['profit_margin_percentage']
        else:
            profit_record = RouteProfitability(
                route_id=route.id,
                total_revenue=total_revenue,
                total_cost=profit_metrics['total_costs'],
                gain_net=profit_metrics['net_profit'],
                margin_pct=profit_metrics['profit_margin_percentage']
            )
            db.add(profit_record)
        
        db.commit()
        logger.info(f"Route {route.id} metrics updated: {total_distance}km, {total_time}min, {total_revenue}DT revenue")
        
    except Exception as e:
        logger.error(f"Error updating route metrics: {e}")
        db.rollback()
