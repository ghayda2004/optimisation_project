import os
import sys
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Configurer les chemins
load_dotenv()
sys.path.insert(0, os.path.abspath("backend_agent"))

from app.models.models import Order, Driver
from app.core.config import DATABASE_URL, CSV_ORDERS_PATH, CSV_DRIVERS_PATH

def clean_float(value):
    """Nettoie les nombres (ex: remplace virgule par point)"""
    try:
        if pd.isna(value): return 0.0
        return float(str(value).replace(',', '.'))
    except:
        return 0.0

def run_import():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    print("🚀 Début de l'importation manuelle sécurisée...")

    try:
        # 1. Nettoyage rapide (Optionnel: décommente si tu veux vider avant d'importer)
        # session.query(Order).delete()
        # session.commit()

        # 2. Import des Orders
        if os.path.exists(CSV_ORDERS_PATH):
            print(f"Reading {CSV_ORDERS_PATH}...")
            # On utilise sep=None pour que pandas devine tout seul le délimiteur (, ou ;)
            df_orders = pd.read_csv(CSV_ORDERS_PATH, sep=None, engine='python', encoding='utf-8-sig')
            
            for _, row in df_orders.iterrows():
                new_order = Order(
                    reference=str(row.get('Reference', '')),
                    expediteur=str(row.get('Expéditeur', 'Inconnu')),
                    adresse_destinataire=str(row.get('Adresse destinataire', '')),
                    lat=clean_float(row.get('lat')),
                    lng=clean_float(row.get('lon')), # Mappe lon -> lng
                    delivery_value=clean_float(row.get('Prix Total')),
                    poids=clean_float(row.get('Poids')),
                    frais_livraison=clean_float(row.get('Frais_Livraison_TND')),
                    gouvernorat=str(row.get('Gouvernorat', '')),
                    priorite=str(row.get('Priorite', 'Normal'))
                )
                session.add(new_order)
            print(f"✅ {len(df_orders)} commandes ajoutées à la file.")

        # 3. Import des Drivers (Si tu as un CSV drivers)
        if os.path.exists(CSV_DRIVERS_PATH):
            df_drivers = pd.read_csv(CSV_DRIVERS_PATH, sep=None, engine='python')
            for _, row in df_drivers.iterrows():
                new_driver = Driver(
                    name=row.get('name', 'Livreur'),
                    vehicle_capacity=clean_float(row.get('capacity', 50.0)),
                    current_lat=36.8, # Position par défaut (Tunis)
                    current_lng=10.1
                )
                session.add(new_driver)
            print(f"✅ Drivers ajoutés.")

        session.commit()
        print("🎉 TOUT EST DANS LA BASE DE DONNÉES !")

    except Exception as e:
        session.rollback()
        print(f"❌ Erreur lors de l'insertion : {e}")
    finally:
        session.close()

if __name__ == "__main__":
    run_import()