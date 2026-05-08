from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func  # Import indispensable pour sum() et avg()
from app.models.models import Route, Driver, RouteProfitability, RouteStop
from app.core.database import SessionLocal

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