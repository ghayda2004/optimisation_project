# Configuration PostgreSQL pour le système de logistique

## 📋 Prérequis

Avant de lancer l'application, vous devez configurer PostgreSQL.

## 🛠️ Installation de PostgreSQL

### Windows
1. Téléchargez PostgreSQL depuis https://www.postgresql.org/download/windows/
2. Installez avec les paramètres par défaut
3. Notez le mot de passe de l'utilisateur `postgres`

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### macOS
```bash
brew install postgresql
brew services start postgresql
```

## ⚙️ Configuration

1. **Créer un fichier `.env`** à la racine du projet :
```env
DATABASE_URL=postgresql://postgres:VOTRE_MOT_DE_PASSE@localhost:5432/logistics_db
```

2. **Créer la base de données** :
```sql
-- Connectez-vous à PostgreSQL
psql -U postgres

-- Créez la base de données
CREATE DATABASE logistics_db;

-- Quittez
\q
```

## 🚀 Initialisation

1. **Activer l'environnement virtuel** :
```bash
# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate
```

2. **Initialiser la base de données** :
```bash
python scripts/init_database.py
```

3. **Importer les données des livreurs** :
```bash
python central_agent/scripts/import_csv_to_db.py
```

## 📊 Structure des données

La base de données contient les tables suivantes :

- **`drivers`** : Informations sur les chauffeurs
- **`packages`** : Colis à livrer
- **`livraisons`** : Données de livraison importées du CSV

## 🔍 Vérification

Pour vérifier que tout fonctionne :

```bash
# Tester la connexion
python -c "from central_agent.backend_agent.app.core.config import settings; print('✅ Configuration chargée')"
```

## 🆘 Dépannage

### Erreur "Connection refused"
- Vérifiez que PostgreSQL est démarré : `sudo systemctl status postgresql`
- Vérifiez le port : `netstat -tlnp | grep 5432`

### Erreur "FATAL: password authentication failed"
- Modifiez `pg_hba.conf` pour autoriser l'authentification locale
- Ou utilisez : `psql -U postgres -h localhost`

### Erreur "database does not exist"
- Créez la base manuellement : `createdb logistics_db`