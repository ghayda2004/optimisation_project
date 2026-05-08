import sys
import os

# Ajouter le path DANS l'environnement AVANT que uvicorn spawne le subprocess
backend_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "central_agent", "backend_agent"
)

# Ces deux lignes ensemble — sys.path pour le process principal
# PYTHONPATH pour le subprocess uvicorn reload
sys.path.insert(0, backend_path)
os.environ["PYTHONPATH"] = backend_path

print(f"✅ Démarrage V2V — Path: {backend_path}")

import uvicorn

if __name__ == "__main__":
   uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)