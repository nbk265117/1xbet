import os
import sys

# Ajouter le dossier backend au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# IMPORTANT: Charger les variables d'environnement AVANT les imports
# pour que les services aient accès aux clés API
from dotenv import load_dotenv
load_dotenv()

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from services.database import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie de l'application"""
    # Startup
    print("Démarrage de l'API 1xbet Predictions...")
    connected = await db.connect()
    if connected:
        print("MongoDB connecté avec succès")
    else:
        print("Mode sans base de données (cache fichier)")

    yield

    # Shutdown
    print("Arrêt de l'API...")
    await db.disconnect()


app = FastAPI(
    title="1xbet Prediction API",
    description="API de prédiction de matchs de football avec Polymarket",
    version="2.0.0",
    lifespan=lifespan,
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
        "version": "2.0.0",
        "status": "running",
        "database": "connected" if db.db is not None else "file_cache",
        "endpoints": {
            "polymarket_predictions": "/api/polymarket/predictions",
            "polymarket_combos": "/api/polymarket/combos",
            "polymarket_football": "/api/polymarket/football",
            "polymarket_sports": "/api/polymarket/sports",
            "auth": "/api/auth",
        },
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected" if db.db is not None else "disconnected"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
