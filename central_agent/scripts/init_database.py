#!/usr/bin/env python3
"""
Script d'initialisation de la base de données PostgreSQL
"""

import os
import sys
from sqlalchemy import create_engine
from dotenv import load_dotenv

# 1. Charger les variables d'environnement (PYTHONPATH, DATABASE_URL)
load_dotenv()

# 2. Configuration du chemin système pour trouver 'app'
# On ajoute 'backend_agent' au sys.path pour que "from app..." fonctionne
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
backend_path = os.path.join(project_root, 'backend_agent')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

def init_database():
    """Initialise la base de données PostgreSQL"""

    # Récupération de l'URL depuis le .env
    database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/logistics_db")

    print("🔄 Initialisation de la base de données PostgreSQL...")
    print(f"📍 URL: {database_url}")

    try:
        # Créer le moteur SQLAlchemy
        engine = create_engine(database_url)

        # Tester la connexion
        with engine.connect() as conn:
            print("✅ Connexion à PostgreSQL réussie!")

            # --- CORRECTION ICI ---
            # On importe 'Base' en utilisant le chemin relatif à backend_agent
            from app.models.models import Base
            
            print("⏳ Création des tables en cours...")
            Base.metadata.create_all(engine)
            print("✅ Tables créées avec succès")

        print("🎉 Initialisation terminée!")

    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation: {e}")
        print("\n🔧 Solutions possibles:")
        print("1. Vérifiez que PostgreSQL est installé et démarré")
        print("2. Vérifiez que la base 'logistics_db' existe bien")
        print("3. Assurez-vous que le dossier 'app/models/' contient un __init__.py")
        sys.exit(1)

if __name__ == "__main__":
    init_database()