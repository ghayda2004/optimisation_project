import os
import sys
import pandas as pd
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

# --- CONFIGURATION DES CHEMINS (Standardisée) ---
# 1. Charger le .env depuis la racine
project_root = Path(__file__).resolve().parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

# 2. Configurer le PYTHONPATH pour accéder au dossier backend_agent
path_from_env = os.getenv("PYTHONPATH", "./backend_agent")
backend_path = (project_root / path_from_env).resolve()

if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# 3. Dossier de sortie pour les résultats
data_dir = project_root / "data"
data_dir.mkdir(exist_ok=True) # Crée le dossier s'il n'existe pas

# --- IMPORTS DU BACKEND ---
try:
    # Note: On importe get_orders depuis data_reader plutôt que pipeline pour plus de clarté
    from app.services.data_reader import get_orders 
    from app.services.routing import get_ors_distance_matrix, optimize_routes
    from app.services.messaging import generate_google_maps_url
except ImportError as e:
    print(f"❌ Erreur d'importation : {e}")
    sys.exit(1)

def test_routing_from_csv():
    """
    Lit le dataset CSV, calcule les routes, et affiche les résultats
    """
    print("\n" + "="*60)
    print("🚀 TEST DE ROUTING (MODE CSV)")
    print("="*60)

    # 1. Chargement des données
    print("📂 Chargement des données...")
    df = get_orders()
    
    if df is None or df.empty:
        print("❌ Erreur: Impossible de charger les données ou DataFrame vide.")
        return

    print(f"✅ {len(df)} livraisons trouvées")
    
    # 2. Nettoyage (Vérifie 'lat' et 'lon' ou 'lng' selon ton CSV)
    # J'ai ajouté 'lon' et 'lng' au cas où le nom varie dans ton fichier
    lon_col = 'lon' if 'lon' in df.columns else 'lng'
    df = df.dropna(subset=['lat', lon_col])
    print(f"✅ {len(df)} livraisons avec coordonnées GPS valides")
    
    # 3. Sous-ensemble pour le test (Limite API OpenRouteService)
    df_subset = df.head(49) # 49 + 1 (dépôt) = 50 points (limite ORS standard)
    print(f"📍 Utilisation de {len(df_subset)} points pour ce test\n")
    
    # 4. Préparation des points (Dépôt : Tunis)
    depot = (36.82857, 10.20616)
    points = [depot] + list(zip(df_subset['lat'], df_subset[lon_col]))
    
    print("📡 ÉTAPE 1: Récupération de la matrice de distances (ORS)...")
    try:
        distance_matrix = get_ors_distance_matrix(points)
        print(f"✅ Matrice récupérée ! Dimensions: {len(distance_matrix)}x{len(distance_matrix[0])}\n")
    except Exception as e:
        print(f"❌ ERREUR API: {e}\n")
        return

    print("⚙️  ÉTAPE 2: Optimisation via OR-Tools...")
    num_vehicles = 3
    max_dist_m = 150000 # 150 km
    
    result = optimize_routes(
        distance_matrix=distance_matrix, 
        num_vehicles=num_vehicles, 
        depot_index=0, 
        max_distance=max_dist_m
    )

    # 5. Affichage des résultats
    print("=" * 60)
    print("🎯 RÉSULTATS DU ROUTING")
    print("=" * 60)
    
    if result and 'routes' in result:
        print(f"\n✅ Total distance: {result['total_distance'] / 1000:.2f} km")
        print(f"✅ Véhicules utilisés: {result['vehicles_used']} / {num_vehicles}\n")
        
        for v_id, route_info in result['routes'].items():
            print(f"\n🚚 VÉHICULE {v_id + 1}")
            print(f"─" * 20)
            
            # Extraire les coordonnées pour Google Maps
            driver_route_coords = [points[i] for i in route_info['path_indices']]
            distance_km = route_info['path_distance_m'] / 1000
            num_deliveries = max(0, len(route_info['path_indices']) - 2)
            
            print(f"  📏 Distance: {distance_km:.2f} km")
            print(f"  📦 Livraisons: {num_deliveries}")
            print(f"  🗺️  Stops: {' → '.join(map(str, route_info['path_indices']))}")
            
            # Générer lien Google Maps
            try:
                gmaps_link = generate_google_maps_url(driver_route_coords)
                print(f"  🔗 Google Maps: {gmaps_link}")
            except Exception:
                pass
        
        # 6. Sauvegarde JSON
        output_file = data_dir / "routing_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Résultats sauvegardés dans: {output_file}\n")
        
    else:
        print("\n❌ Pas de solution trouvée ! Vérifiez les contraintes de distance.")

if __name__ == "__main__":
    test_routing_from_csv()