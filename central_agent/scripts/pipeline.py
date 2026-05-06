import sys
import os
import logging

# Configuration du chemin pour importer les modules du backend
sys.path.insert(0, os.path.abspath("backend_agent"))

from app.services.data_reader import get_orders_from_csv, get_drivers_mock
from app.services.routing import optimize_routes
from app.services.database_handler import save_results_to_db, save_profitability

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURATION FINANCIÈRE (Variables d'environnement ou fallback) ---
REVENUE_PER_DELIVERY = float(os.getenv("REVENUE_PER_DELIVERY", 8.0))
FUEL_RATE_PER_KM = float(os.getenv("FUEL_RATE_PER_KM", 0.35))
HANDLING_COST_PER_STOP = float(os.getenv("HANDLING_COST_PER_STOP", 0.5))
DRIVER_HOURLY_RATE = float(os.getenv("DRIVER_HOURLY_RATE", 8.0))

def run_pipeline(source="csv"):
    print("\n🚀 DÉMARRAGE DU PIPELINE LOGISTIQUE V-2-V\n")
    
    # 1. Chargement des données
    if source == "csv":
        orders = get_orders_from_csv()
        drivers = get_drivers_mock()
    else:
        # Logique pour charger depuis la DB si nécessaire
        logger.error("Source 'db' non implémentée pour ce test.")
        return

    # 2. Optimisation des routes
    routes = optimize_routes(orders, drivers)
    
    if not routes:
        return

    profitability_results = []
    total_colis_global = 0
    total_gain_global = 0.0
    all_margins = []

    # 3 & 4. Calcul Rentabilité et Affichage Console (Features 1, 2, 3)
    for r in routes:
        nb_stops = len(r['order_ids'])
        
        # Formule de Rentabilité
        revenue = nb_stops * REVENUE_PER_DELIVERY
        cost = (r['total_distance_km'] * FUEL_RATE_PER_KM) + \
               (nb_stops * HANDLING_COST_PER_STOP) + \
               ((r['total_duration_min'] / 60) * DRIVER_HOURLY_RATE)
        
        gain_net = revenue - cost
        margin_pct = (gain_net / revenue * 100) if revenue > 0 else 0
        
        # Construction de l'URL Google Maps (Feature 2)
        base_url = "https://www.google.com/maps/dir/"
        depot = f"{r['driver_start_coords']['lat']},{r['driver_start_coords']['lng']}"
        stops_coords = "/".join([f"{o['lat']},{o['lng']}" for o in r['full_orders']])
        map_url = f"{base_url}{depot}/{stops_coords}"

        # Affichage Feature 1
        print(f"┌─────────────────────────────────────────┐")
        print(f"│ 🚗 Driver: {r['driver_name']:28} │")
        print(f"│ 📦 Colis: {nb_stops:2} commandes                │")
        print(f"│ 📍 Distance: {r['total_distance_km']:6} km                │")
        print(f"│ 💰 Revenu: {nb_stops} x {REVENUE_PER_DELIVERY} DT = {revenue:6} DT      │")
        print(f"│ 💸 Coût: {round(cost, 2):6} DT                     │")
        print(f"│ ✅ Gain net: {round(gain_net, 2):6} DT (margin: {round(margin_pct, 1)}%) │")
        print(f"│ 🗺️  Map: {map_url[:30]}... │")
        print(f"└─────────────────────────────────────────┘")

        # Affichage Feature 3 (Détail Colis)
        print("📋 Détail des colis:")
        for idx, o in enumerate(r['full_orders'], 1):
            print(f"   [{idx}]. Ref: {o.get('reference', 'N/A')} | Client: {o.get('expediteur', 'N/A')[:15]}")
            print(f"        Adresse: {o.get('adresse_destinataire', 'N/A')[:40]}... | Valeur: {o.get('delivery_value', 0)} DT")
        print("\n")

        # Accumulation pour le résumé global et la DB
        total_colis_global += nb_stops
        total_gain_global += gain_net
        all_margins.append(margin_pct)
        
        # On prépare l'objet pour save_profitability (besoin de l'ID route plus tard)
        profitability_results.append({
            "driver_id": r['driver_id'], # Temporaire pour mapper après save
            "total_revenue": revenue,
            "total_cost": cost,
            "gain_net": gain_net,
            "margin_pct": margin_pct
        })

    # Résumé Global
    marge_moyenne = sum(all_margins) / len(all_margins) if all_margins else 0
    print("═══════════════════════════════════════")
    print(f" TOTAL ROUTES    : {len(routes)}")
    print(f" TOTAL COLIS     : {total_colis_global}")
    print(f" GAIN TOTAL      : {round(total_gain_global, 2)} DT")
    print(f" MARGE MOYENNE   : {round(marge_moyenne, 2)} %")
    print("═══════════════════════════════════════\n")

    # 5 & 6. Sauvegarde en Base de données
    route_ids = save_results_to_db(routes)
    
    if route_ids:
        # On injecte les vrais IDs de routes retournés par la DB dans nos résultats financiers
        for i, r_id in enumerate(route_ids):
            profitability_results[i]['route_id'] = r_id
            
        save_profitability(profitability_results)
        print("🎉 Pipeline terminé avec succès.")

if __name__ == "__main__":
    run_pipeline(source="csv")