from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func  # Import indispensable pour sum() et avg()
from app.models.models import Route, Driver, RouteProfitability, RouteStop, Order
from app.core.database import SessionLocal
from app.services.dynamic_allocation import calculate_marginal_cost_per_driver, assign_order_to_driver

router = APIRouter(prefix="/api/admin", tags=["Admin Dashboard"])

# Fonction pour obtenir la session de base de données
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/summary")
def get_admin_summary(db: Session = Depends(get_db)):
    """Calcule les indicateurs clés de performance (KPIs) en temps réel."""
    
    # 1. Nombre de chauffeurs actifs
    active_drivers = db.query(Driver).filter(Driver.is_active == True).count()
    
    # 2. Nombre total de tournées
    total_routes = db.query(Route).count()
    
    # 3. Nombre total de colis (arrêts)
    total_colis = db.query(RouteStop).count()
    
    # 4. Calcul de la somme des gains et de la moyenne des marges
    # On interroge la table RouteProfitability
    stats = db.query(
        func.sum(RouteProfitability.gain_net).label("total_gain"),
        func.avg(RouteProfitability.margin_pct).label("avg_margin")
    ).first()

    # On sécurise les valeurs au cas où la base est vide (None -> 0)
    gain_total = round(stats.total_gain or 0.0, 2)
    marge_moyenne = round(stats.avg_margin or 0.0, 1)

    return {
        "active_drivers": active_drivers,
        "total_routes": total_routes,
        "total_colis": total_colis,
        "gain_total": gain_total,
        "marge_moyenne": marge_moyenne
    }

@router.get("/routes")
def get_all_routes(db: Session = Depends(get_db)):
    """Récupère la liste de toutes les routes avec leurs détails et lien carte."""
    
    results = db.query(Route, Driver, RouteProfitability)\
        .join(Driver, Route.driver_id == Driver.id)\
        .join(RouteProfitability, Route.id == RouteProfitability.route_id)\
        .all()
    
    routes_list = []
    for route, driver, profit in results:
        # Chemin vers le fichier HTML généré par le pipeline
        map_filename = f"map_driver_{driver.id}.html"
        
        routes_list.append({
            "route_id": route.id,
            "driver_name": driver.name,
            "nb_colis": db.query(RouteStop).filter(RouteStop.route_id == route.id).count(),
            "distance": route.total_distance_km,
            "gain_net": profit.gain_net,
            "margin_pct": profit.margin_pct,
            "status": route.status,
            "map_url": f"outputs/{map_filename}"
        })
    
    return routes_list

# ============================================================================
# DYNAMIC ORDER ALLOCATION - NEW ENDPOINTS
# ============================================================================

@router.post("/propose-order")
def propose_new_order(
    reference: str,
    customer_name: str,
    address: str,
    lat: float,
    lng: float,
    delivery_value: float,
    db: Session = Depends(get_db)
):
    """
    STEP 1: Admin proposes a new order
    System calculates suitable drivers ranked by marginal profit
    
    Returns list of drivers with cost breakdown (most suitable first)
    """
    
    # Validate inputs
    if not reference or not customer_name or lat is None or lng is None:
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    if delivery_value <= 0:
        raise HTTPException(status_code=400, detail="Delivery value must be positive")
    
    # Create order object for cost calculation
    new_order = {
        'lat': lat,
        'lng': lng,
        'delivery_value': delivery_value,
        'reference': reference
    }
    
    # Calculate marginal cost per driver
    suitable_drivers = calculate_marginal_cost_per_driver(new_order, db)
    
    if not suitable_drivers:
        raise HTTPException(status_code=400, detail="No active drivers available")
    
    # Find feasible drivers (sorted by profit)
    feasible = [d for d in suitable_drivers if d['is_feasible']]
    infeasible = [d for d in suitable_drivers if not d['is_feasible']]
    
    return {
        "order": {
            "reference": reference,
            "customer": customer_name,
            "address": address,
            "lat": lat,
            "lng": lng,
            "value": delivery_value
        },
        "feasible_drivers": feasible,
        "infeasible_drivers": infeasible,
        "best_driver_id": feasible[0]['driver_id'] if feasible else None,
        "best_driver_name": feasible[0]['driver_name'] if feasible else None,
        "status": "ready_for_confirmation"
    }

@router.post("/confirm-order")
def confirm_new_order(
    reference: str,
    customer_name: str,
    address: str,
    lat: float,
    lng: float,
    delivery_value: float,
    driver_id: int,
    db: Session = Depends(get_db)
):
    """
    STEP 2: Admin confirms the order assignment
    Order is inserted into selected driver's route
    Route metrics and profitability are recalculated
    
    Returns success status with updated route info
    """
    
    # Create order in database
    try:
        order = Order(
            reference=reference,
            expediteur=customer_name,
            adresse_destinataire=address,
            lat=lat,
            lng=lng,
            delivery_value=delivery_value,
            status_internal="assigned"
        )
        db.add(order)
        db.flush()
        order_id = order.id
        
        # Get best position for insertion
        new_order = {
            'lat': lat,
            'lng': lng,
            'delivery_value': delivery_value
        }
        
        drivers_proposal = calculate_marginal_cost_per_driver(new_order, db)
        selected = [d for d in drivers_proposal if d['driver_id'] == driver_id][0]
        best_position = selected['best_position']
        
        # Assign to driver
        success = assign_order_to_driver(order_id, driver_id, best_position, db)
        
        if not success:
            db.rollback()
            raise HTTPException(status_code=500, detail="Failed to assign order")
        
        # Get updated route info
        route = db.query(Route).filter_by(driver_id=driver_id, status="planned").first()
        profit = db.query(RouteProfitability).filter_by(route_id=route.id).first()
        driver = db.query(Driver).filter_by(id=driver_id).first()
        
        return {
            "success": True,
            "message": f"Order assigned to {driver.name}",
            "order": {
                "id": order_id,
                "reference": reference,
                "status": "assigned"
            },
            "route": {
                "route_id": route.id,
                "driver_name": driver.name,
                "total_distance_km": route.total_distance_km,
                "total_duration_min": route.total_duration_min,
                "num_stops": db.query(RouteStop).filter(RouteStop.route_id == route.id).count(),
                "total_revenue": profit.total_revenue if profit else 0,
                "net_profit": profit.gain_net if profit else 0,
                "margin_pct": profit.margin_pct if profit else 0
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")