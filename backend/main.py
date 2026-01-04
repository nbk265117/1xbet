import os
import sys

# Ajouter le dossier backend au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from api.routes import router

# Charger les variables d'environnement
load_dotenv()

app = FastAPI(
    title="1xbet Prediction API",
    description="API de prédiction de matchs de football",
    version="1.0.0",
)

# Configuration CORS pour le frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, limiter aux domaines autorisés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclure les routes
app.include_router(router)


@app.get("/")
async def root():
    return {
        "name": "1xbet Prediction API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "matches": "/api/matches/{date}",
            "predictions": "/api/predictions/{date}",
            "best_combos": "/api/best-combos/{date}",
            "auth": "/api/auth",
        },
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
