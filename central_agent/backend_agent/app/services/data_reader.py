import pandas as pd
import os
import logging
from app.core.config import CSV_ORDERS_PATH

logger = logging.getLogger(__name__)

def get_orders_from_csv():
    # Construction du chemin absolu pour éviter les erreurs de dossier
    if not CSV_ORDERS_PATH:
        raise ValueError("Le chemin du CSV n'est pas défini dans le .env")
    
    # Résolution du chemin pour être sûr qu'on pointe au bon endroit
    # Si le chemin est relatif dans le .env, il sera relatif à la racine du projet
    if not os.path.isabs(CSV_ORDERS_PATH):
        from app.core.config import BASE_DIR
        full_path = os.path.join(BASE_DIR, CSV_ORDERS_PATH)
    else:
        full_path = CSV_ORDERS_PATH

    print(f"📂 Lecture du fichier : {full_path}")

    if not os.path.exists(full_path):
        raise FileNotFoundError(f"Fichier CSV introuvable : {full_path}")
    
    df = pd.read_csv(full_path, sep=None, engine='python', encoding='utf-8-sig')
    
    # Fix column names to match CSV structure
    mapping = {
        'Reference': 'id',
        'lon': 'lng',
        'Prix_Total': 'delivery_value'
    }
    df = df.rename(columns=mapping)
    
    for col in ['lat', 'lng']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    
    df = df.dropna(subset=['lat', 'lng'])
    print(f"✅ {len(df)} commandes chargées.")
    return df.to_dict(orient="records")

def get_drivers_mock():
    return [
        {"id": 1, "name": "Livreur Ahmad", "vehicle_capacity": 500, "lat": 36.806, "lng": 10.181},
        {"id": 2, "name": "Livreur Ali", "vehicle_capacity": 500, "lat": 36.806, "lng": 10.181},
        {"id": 5, "name": "Livreur Salah", "vehicle_capacity": 500, "lat": 36.806, "lng": 10.181},
        {"id": 3, "name": "Livreur Karim", "vehicle_capacity": 500, "lat": 36.806, "lng": 10.181},
        {"id": 4, "name": "Livreur Yessin", "vehicle_capacity": 500, "lat": 36.806, "lng": 10.181}
    ]