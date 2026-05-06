"""
FILE 6: database.py
Rôle : Sauvegarder les routes, les arrêts et la rentabilité dans PostgreSQL.
"""

import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
# Correction des imports pour utiliser les chemins courts (PythonPATH)
from app.core.config import DATABASE_URL
from app.models.models import Route, RouteStop, RouteProfitability

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost/v2v_db")
# Configuration du Logging
logger = logging.getLogger(__name__)

# Initialisation du moteur et de la session
# "pool_pre_ping=True" aide à maintenir la connexion avec PostgreSQL
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def save_routes(enriched_routes):
    """
    Insère ou met à jour les tables Route, RouteStop et RouteProfitability.
    Retourne le nombre de routes traitées.
    """
    db = SessionLocal()
    routes_count = 0

    try:
        for r_data in enriched_routes:
            # 1. UPSERT ROUTE
            # On vérifie si une route planifiée existe déjà pour ce livreur
            route = db.query(Route).filter(
                Route.driver_id == r_data['driver_id'],
                Route.status == "planned"
            ).first()

            if not route:
                route = Route(driver_id=r_data['driver_id'])
                db.add(route)
                db.flush()  # Pour générer l'ID de la route immédiatement

            route.total_distance_km = r_data['total_distance_km']
            route.total_duration_min = r_data['total_duration_min']
            route.status = "planned"

            # 2. RAFRAÎCHIR LES ARRÊTS (STOPS)
            # On supprime les anciens arrêts pour reconstruire la nouvelle séquence
            db.query(RouteStop).filter(RouteStop.route_id == route.id).delete()
            
            for seq, order_id in enumerate(r_data['order_ids']):
                stop = RouteStop(
                    route_id=route.id,
                    order_id=order_id,
                    stop_sequence=seq + 1
                )
                db.add(stop)

            # 3. UPSERT RENTABILITÉ (PROFITABILITY)
            prof_data = r_data['profitability']
            profit_record = db.query(RouteProfitability).filter(
                RouteProfitability.route_id == route.id
            ).first()

            if not profit_record:
                profit_record = RouteProfitability(route_id=route.id)
                db.add(profit_record)

            # Mapping des données financières
            profit_record.total_revenue = prof_data['breakdown']['revenue']
            profit_record.total_cost = prof_data['total_costs']
            profit_record.profit_score = prof_data['net_profit']
            profit_record.margin_pct = prof_data['profit_margin_percentage']

            routes_count += 1

        # Validation finale de la transaction
        db.commit()
        logger.info(f"✅ {routes_count} routes sauvegardées/mises à jour en base de données.")
        return routes_count

    except Exception as e:
        db.rollback() # Annule tout en cas d'erreur pour garder la DB propre
        logger.error(f"❌ Erreur lors de la sauvegarde : {e}")
        return 0
    finally:
        db.close()