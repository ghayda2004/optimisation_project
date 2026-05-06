from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from app.models.models import Route, Driver, Order, RouteStop, RouteProfitability
from app.core.database import SessionLocal

router = APIRouter(prefix="/api/driver", tags=["Driver Mobile Interface"])

# Dépendance DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/{driver_id}/route")
def get_driver_current_route(driver_id: int, db: Session = Depends(get_db)):
    """
    Récupère la tournée actuelle 'planned' pour un chauffeur spécifique
    avec le détail complet des colis et l'URL Google Maps.
    """
    # 1. Vérifier si le chauffeur existe
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Chauffeur non trouvé")

    # 2. Récupérer la route active (la plus récente planifiée)
    route = db.query(Route).filter(
        Route.driver_id == driver_id, 
        Route.status == "planned"
    ).order_by(Route.created_at.desc()).first()

    if not route:
        raise HTTPException(status_code=404, detail="Aucune tournée planifiée pour ce chauffeur")

    # 3. Récupérer la rentabilité
    profit = db.query(RouteProfitability).filter(RouteProfitability.route_id == route.id).first()

    # 4. Récupérer les arrêts et les détails des commandes
    stops_data = db.query(RouteStop, Order).join(
        Order, RouteStop.order_id == Order.id
    ).filter(RouteStop.route_id == route.id).order_by(RouteStop.stop_sequence).all()

    # Construction de l'URL Google Maps (séquence complète)
    # On commence par la position actuelle du chauffeur ou du dépôt
    depot_coords = f"{driver.current_lat or 36.806},{driver.current_lng or 10.181}"
    waypoints = "/".join([f"{o.lat},{o.lng}" for _, o in stops_data])
    map_url = f"https://www.google.com/maps/dir/{depot_coords}/{waypoints}"

    # Formatage des détails des colis
    colis_list = []
    for stop, order in stops_data:
        colis_list.append({
            "stop_sequence": stop.stop_sequence,
            "order_id": order.id,
            "reference": order.reference,
            "expediteur": order.expediteur,
            "adresse": order.adresse_destinataire,
            "gouvernorat": order.gouvernorat,
            "delivery_value": order.delivery_value,
            "lat": order.lat,
            "lng": order.lng,
            "nav_url": f"https://www.google.com/maps/search/?api=1&query={order.lat},{order.lng}"
        })

    return {
        "driver_name": driver.name,
        "nb_colis": len(colis_list),
        "total_distance": route.total_distance_km,
        "total_duration": route.total_duration_min,
        "gain_net": profit.gain_net if profit else 0,
        "map_url": map_url,
        "stops": colis_list
    }

@router.get("/{driver_id}/stats")
def get_driver_personal_stats(driver_id: int, db: Session = Depends(get_db)):
    """
    Récupère l'historique personnel d'un chauffeur : total gagné, 
    nombre de colis livrés et marge moyenne.
    """
    stats = db.query(
        func.count(Route.id).label("total_routes"),
        func.sum(RouteProfitability.total_revenue).label("revenue"),
        func.sum(RouteProfitability.gain_net).label("gain"),
        func.avg(RouteProfitability.margin_pct).label("margin")
    ).select_from(Route).join(RouteProfitability).filter(Route.driver_id == driver_id).first()

    total_colis = db.query(func.count(RouteStop.id)).join(Route).filter(Route.driver_id == driver_id).scalar()

    if not stats.total_routes:
        return {
            "total_routes_done": 0,
            "total_colis_delivered": 0,
            "total_gain": 0,
            "avg_margin": 0
        }

    return {
        "total_routes_done": stats.total_routes,
        "total_colis_delivered": total_colis or 0,
        "total_gain": round(stats.gain or 0, 2),
        "avg_margin": round(stats.margin or 0, 1)
    }