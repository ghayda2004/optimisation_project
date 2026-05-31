#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
import logging
from dotenv import load_dotenv

# 1. Charger les variables d'environnement
load_dotenv()

# 2. Configuration du chemin système pour trouver 'app'
# __file__ is central_agent/scripts/pipeline.py
# so we go up 2 levels to reach the project root, 
# then down into central_agent/backend_agent
scripts_dir = os.path.dirname(os.path.abspath(__file__))
central_agent_dir = os.path.dirname(scripts_dir)
backend_path = os.path.join(central_agent_dir, 'backend_agent')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.services.data_reader import get_orders_from_csv, get_drivers_mock
from app.services.routing import optimize_routes
from app.services.database_handler import save_results_to_db, save_profitability
from app.services.map_generator import generate_map_html
from app.models.models import Driver, Order
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import DATABASE_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constantes financières
REVENUE_PER_DELIVERY = 8.0
FUEL_RATE_PER_KM = 0.35
HANDLING_COST_PER_STOP = 0.5
DRIVER_HOURLY_RATE = 8.0

def run_pipeline():
    print("\n🚀 DÉMARRAGE DU PIPELINE V-2-V\n")
    
    # Setup database session
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # 1. Load orders from CSV and populate database
    orders_data = get_orders_from_csv()
    for order_data in orders_data:
        existing = session.query(Order).filter_by(id=order_data['id']).first()
        if not existing:
            order = Order(
                id=order_data['id'],
                reference=order_data.get('Reference', ''),
                expediteur=order_data.get('Expediteur', ''),
                adresse_destinataire=order_data.get('Adresse_destinataire', ''),
                action=order_data.get('Action', ''),
                contenu=order_data.get('Contenu', ''),
                poids=order_data.get('Poids', 0),
                lat=order_data.get('lat'),
                lng=order_data.get('lng'),
                delivery_value=order_data.get('delivery_value', 8.0),
                frais_livraison=order_data.get('Frais_Livraison_TND', 0),
                statut_csv=order_data.get('Statut', ''),
                gouvernorat=order_data.get('Gouvernorat', ''),
                priorite=order_data.get('Priorite', ''),
                mode_paiement=order_data.get('Mode_Paiement', ''),
                type_client=order_data.get('Type_Client', '')
            )
            session.add(order)
    session.commit()
    
    # 2. Populate drivers in database
    drivers_data = get_drivers_mock()
    for driver_data in drivers_data:
        existing = session.query(Driver).filter_by(id=driver_data['id']).first()
        if not existing:
            driver = Driver(
                id=driver_data['id'],
                name=driver_data['name'],
                vehicle_capacity=driver_data['vehicle_capacity'],
                current_lat=driver_data['lat'],
                current_lng=driver_data['lng'],
                is_active=True
            )
            session.add(driver)
    session.commit()
    session.close()
    
    orders = get_orders_from_csv()
    drivers = get_drivers_mock()
    routes = optimize_routes(orders, drivers)
    
    if not routes: return

    profitability_results = []

    for r in routes:
        nb_stops = len(r['order_ids'])
        revenue = nb_stops * REVENUE_PER_DELIVERY
        cost = (r['total_distance_km'] * FUEL_RATE_PER_KM) + \
               (nb_stops * HANDLING_COST_PER_STOP) + \
               ((r['total_duration_min'] / 60) * DRIVER_HOURLY_RATE)
        
        gain_net = round(revenue - cost, 2)
        margin_pct = round((gain_net / revenue * 100), 1) if revenue > 0 else 0

        # Génération de la carte Leaflet
        route_data = {
            "driver_id": r['driver_id'],
            "driver_name": r['driver_name'],
            "nb_colis": nb_stops,
            "total_distance_km": r['total_distance_km'],
            "gain_net": gain_net,
            "depot": r['driver_start_coords'],
            "stops": [{"sequence": i+1, "lat": o['lat'], "lng": o['lng'], "client": o['Expediteur'], "adresse": o['Adresse_destinataire']} 
                      for i, o in enumerate(r['full_orders'])]
        }
        map_path = generate_map_html(route_data)

        print(f"│ 🚗 Driver: {r['driver_name']:20} | Gain: {gain_net} DT | 🗺️  Map: {map_path}")

        profitability_results.append({
            "driver_id": r['driver_id'],
            "total_revenue": revenue,
            "total_cost": cost,
            "gain_net": gain_net,
            "margin_pct": margin_pct
        })

    # Sauvegarde DB
    route_ids = save_results_to_db(routes)
    if route_ids:
        for i, r_id in enumerate(route_ids):
            profitability_results[i]['route_id'] = r_id
        save_profitability(profitability_results)
        print("\n✅ Pipeline terminé. Résultats en base et cartes générées.")

if __name__ == "__main__":
    run_pipeline()