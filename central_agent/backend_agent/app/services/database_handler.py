import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.models import Route, RouteStop, RouteProfitability, Order
from app.core.config import DATABASE_URL

# Configuration du logging
logger = logging.getLogger(__name__)

# Initialisation sécurisée de l'engine
try:
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
except Exception as e:
    logger.error(f"Erreur lors de la création de l'engine Postgres : {e}")
    raise

def save_results_to_db(optimized_routes: list) -> list:
    """
    Enregistre ou met à jour les tournées dans la base de données.
    Si une route 'planned' existe pour un chauffeur, elle est mise à jour.
    
    Returns:
        list: Liste des IDs des routes sauvegardées.
    """
    saved_route_ids = []
    
    with Session() as session:
        try:
            for r_data in optimized_routes:
                driver_id = r_data['driver_id']
                
                # Logic d'UPSERT : On cherche une route existante 'planned' pour ce chauffeur
                existing_route = session.query(Route).filter_by(
                    driver_id=driver_id, 
                    status="planned"
                ).first()

                if existing_route:
                    # UPDATE
                    existing_route.total_distance_km = r_data['total_distance_km']
                    existing_route.total_duration_min = r_data['total_duration_min']
                    route_obj = existing_route
                    # On nettoie les anciens arrêts pour reconstruire la séquence
                    session.query(RouteStop).filter_by(route_id=route_obj.id).delete()
                    logger.info(f"Mise à jour de la route ID {route_obj.id} pour le chauffeur {driver_id}")
                else:
                    # INSERT
                    route_obj = Route(
                        driver_id=driver_id,
                        total_distance_km=r_data['total_distance_km'],
                        total_duration_min=r_data['total_duration_min'],
                        status="planned"
                    )
                    session.add(route_obj)
                    session.flush() # Récupère l'ID généré
                    logger.info(f"Création d'une nouvelle route pour le chauffeur {driver_id}")

                # Insertion des nouveaux arrêts (RouteStops)
                for i, order_id in enumerate(r_data['order_ids']):
                    new_stop = RouteStop(
                        route_id=route_obj.id,
                        order_id=order_id,
                        stop_sequence=i + 1
                    )
                    session.add(new_stop)
                    
                    # Optionnel: Mettre à jour le statut interne de la commande
                    session.query(Order).filter_by(id=order_id).update({"status_internal": "assigned"})

                saved_route_ids.append(route_obj.id)
            
            session.commit()
            return saved_route_ids

        except Exception as e:
            session.rollback()
            logger.error(f"Erreur lors de la sauvegarde des routes : {e}")
            return []

def save_profitability(profitability_results: list):
    """
    Insère les données de rentabilité financière pour chaque route calculée.
    """
    with Session() as session:
        try:
            for p in profitability_results:
                # Supprimer l'ancienne analyse si elle existe
                session.query(RouteProfitability).filter_by(route_id=p['route_id']).delete()
                
                new_profit = RouteProfitability(
                    route_id=p['route_id'],
                    total_revenue=p['total_revenue'],
                    total_cost=p['total_cost'],
                    gain_net=p['gain_net'],
                    margin_pct=p['margin_pct']
                )
                session.add(new_profit)
            
            session.commit()
            logger.info(f"Analyse de rentabilité sauvegardée pour {len(profitability_results)} routes.")
        except Exception as e:
            session.rollback()
            logger.error(f"Erreur lors de la sauvegarde de la rentabilité : {e}")