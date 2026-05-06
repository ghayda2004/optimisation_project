"""
FILE 8: api.py
Single job: Provide a REST API via FastAPI to read route, stop, and profitability data 
from PostgreSQL for the Admin and Driver dashboards.
"""

from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from typing import List

from app.config import DATABASE_URL
from app.models import Route, RouteStop, Order, RouteProfitability, Driver

app = FastAPI(title="V2V Logistics API")

# Database Setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/routes")
def get_all_routes(db: Session = Depends(get_db)):
    """Manager Dashboard: Fetch all routes with their profitability scores."""
    routes = db.query(Route).all()
    results = []
    for r in routes:
        results.append({
            "route_id": r.id,
            "driver_id": r.driver_id,
            "distance_km": r.total_distance_km,
            "duration_min": r.total_duration_min,
            "status": r.status,
            "profitability": {
                "score": r.profitability.profit_score if r.profitability else 0,
                "margin_pct": r.profitability.margin_pct if r.profitability else 0
            }
        })
    return results

@app.get("/routes/{route_id}")
def get_route_details(route_id: int, db: Session = Depends(get_db)):
    """Fetch a single route with all its stops and full order details."""
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    
    stops = db.query(RouteStop, Order).join(Order, RouteStop.order_id == Order.id)\
              .filter(RouteStop.route_id == route_id)\
              .order_by(RouteStop.stop_sequence).all()
    
    return {
        "route_id": route.id,
        "total_distance": route.total_distance_km,
        "stops": [
            {
                "sequence": s.RouteStop.stop_sequence,
                "customer": s.Order.customer_name,
                "address": s.Order.address,
                "lat": s.Order.lat,
                "lng": s.Order.lng,
                "value": s.Order.delivery_value
            } for s in stops
        ]
    }

@app.get("/driver/{driver_id}/route")
def get_driver_route(driver_id: int, db: Session = Depends(get_db)):
    """Driver Dashboard: Fetch the current active route for a specific driver."""
    route = db.query(Route).filter(Route.driver_id == driver_id, Route.status != "completed").first()
    if not route:
        return {"message": "No active route assigned"}
    
    return get_route_details(route.id, db)

@app.get("/dashboard/summary")
def get_summary(db: Session = Depends(get_db)):
    """Manager Dashboard: High-level KPIs for the day."""
    total_routes = db.query(func.count(Route.id)).scalar()
    total_profit = db.query(func.sum(RouteProfitability.profit_score)).scalar() or 0
    avg_margin = db.query(func.avg(RouteProfitability.margin_pct)).scalar() or 0
    
    return {
        "total_routes_today": total_routes,
        "total_profit": round(total_profit, 2),
        "average_margin_pct": round(avg_margin, 2)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)