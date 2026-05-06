import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Import des modèles pour les requêtes
from app.models.models import Route, RouteStop, RouteProfitability

# Configuration
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/v2v_db")
logger = logging.getLogger(__name__)

# Initialisation du moteur SQLAlchemy
# pool_pre_ping=True vérifie la santé de la connexion avant chaque requête
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# On définit la Base ici pour qu'elle soit partagée par les modèles
Base = declarative_base()

def save_routes(enriched_routes):
    """
    Insère ou met à jour les tables Route, RouteStop et RouteProfitability.
    Gère la transaction complète (Commit ou Rollback).
    """
    db = SessionLocal()
    routes_count = 0

    try:
        for r_data in enriched_routes:
            # 1. UPSERT ROUTE (Mise à jour si une route 'planned' existe pour ce driver)
            route = db.query(Route).filter(
                Route.driver_id == r_data['driver_id'],
                Route.status == "planned"
            ).first()

            if not route:
                route = Route(driver_id=r_data['driver_id'])
                db.add(route)
                db.flush()  # Récupère l'ID immédiatement pour les clés étrangères

            route.total_distance_km = r_data['total_distance_km']
            route.total_duration_min = r_data['total_duration_min']
            route.status = "planned"

            # 2. RAFRAÎCHIR LES ARRÊTS (STOPS)
            # On supprime les anciens arrêts pour garantir l'ordre de la nouvelle séquence
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

            # Mapping des données financières (Utilisation des noms de colonnes du modèle)
            profit_record.total_revenue = prof_data['breakdown']['revenue']
            profit_record.total_cost = prof_data['total_costs']
            profit_record.gain_net = prof_data['net_profit']
            profit_record.margin_pct = prof_data['profit_margin_percentage']

            routes_count += 1

        # Validation de la transaction
        db.commit()
        logger.info(f"✅ {routes_count} routes sauvegardées/mises à jour en base de données.")
        return routes_count

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erreur lors de la sauvegarde en base : {e}")
        return 0
    finally:
        db.close()