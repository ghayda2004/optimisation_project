import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import admin_api, driver_api
from .core.database import engine, Base

# Création des tables dans la base de données si elles n'existent pas
# Note: Dans un environnement de production, on utiliserait plutôt Alembic.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="V2V Logistics API",
    description="Backend de gestion de tournées et rentabilité logistique",
    version="1.0.0"
)

# --- CONFIGURATION CORS ---
# Indispensable pour permettre à tes fichiers HTML locaux (frontend) 
# d'appeler l'API FastAPI sans être bloqués par le navigateur.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En dev, on autorise tout. À restreindre en prod.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- INCLUSION DES ROUTES ---
app.include_router(admin_api.router)
app.include_router(driver_api.router)

@app.get("/")
async def root():
    return {
        "message": "Bienvenue sur l'API V2V Logistics",
        "docs": "/docs",
        "status": "online"
    }

if __name__ == "__main__":
    # Lancement du serveur sur le port 8000
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)