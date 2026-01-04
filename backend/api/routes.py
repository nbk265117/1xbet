from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBasic
from datetime import date, datetime
from typing import List
import os

from models.match import Match, Prediction, BestCombo
from services.match_fetcher import MatchFetcher
from services.predictor import MatchPredictor

router = APIRouter(prefix="/api", tags=["predictions"])

# Services
match_fetcher = MatchFetcher()
predictor = MatchPredictor()

# PIN pour l'authentification
APP_PIN = os.getenv("APP_PIN", "1991")


def verify_pin(pin: str) -> bool:
    """Vérifie le PIN d'accès"""
    return pin == APP_PIN


@router.post("/auth")
async def authenticate(pin: str):
    """Vérifie le PIN et retourne un token de session"""
    if verify_pin(pin):
        return {"success": True, "message": "Authentification réussie"}
    raise HTTPException(status_code=401, detail="PIN incorrect")


@router.get("/matches/{date_str}", response_model=List[Match])
async def get_matches(date_str: str):
    """Récupère tous les matchs pour une date donnée"""
    try:
        match_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Format de date invalide. Utilisez YYYY-MM-DD")

    matches = await match_fetcher.fetch_matches_by_date(match_date)

    if not matches:
        return []

    return matches


@router.get("/predictions/{date_str}", response_model=List[Prediction])
async def get_predictions(date_str: str):
    """Génère les prédictions pour tous les matchs d'une date"""
    try:
        match_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Format de date invalide. Utilisez YYYY-MM-DD")

    # Récupérer les matchs
    matches = await match_fetcher.fetch_matches_by_date(match_date)

    if not matches:
        return []

    predictions = []

    for match in matches:
        # Récupérer l'analyse complète du match
        analysis = await match_fetcher.fetch_match_analysis(match)
        # Générer la prédiction
        prediction = predictor.predict_match(analysis)
        predictions.append(prediction)

    # Trier par confiance décroissante
    predictions.sort(
        key=lambda x: (
            x.confidence.value,
            max(x.home_win_probability, x.away_win_probability),
        ),
        reverse=True,
    )

    return predictions


@router.get("/best-combos/{date_str}", response_model=List[BestCombo])
async def get_best_combos(date_str: str, max_combos: int = 5):
    """Génère les meilleurs combinés pour une date"""
    try:
        match_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Format de date invalide. Utilisez YYYY-MM-DD")

    # Récupérer les prédictions
    matches = await match_fetcher.fetch_matches_by_date(match_date)

    if not matches:
        return []

    predictions = []
    for match in matches:
        analysis = await match_fetcher.fetch_match_analysis(match)
        prediction = predictor.predict_match(analysis)
        predictions.append(prediction)

    # Générer les combinés
    combos = predictor.generate_best_combos(predictions, max_combos)

    return combos


@router.get("/match/{match_id}/analysis")
async def get_match_analysis(match_id: int, date_str: str):
    """Analyse détaillée d'un match spécifique"""
    try:
        match_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Format de date invalide")

    matches = await match_fetcher.fetch_matches_by_date(match_date)

    match = next((m for m in matches if m.id == match_id), None)

    if not match:
        raise HTTPException(status_code=404, detail="Match non trouvé")

    analysis = await match_fetcher.fetch_match_analysis(match)
    prediction = predictor.predict_match(analysis)

    return {
        "match": match,
        "analysis": {
            "head_to_head": analysis.head_to_head,
            "home_team_form": analysis.home_team_form,
            "away_team_form": analysis.away_team_form,
            "home_injuries": analysis.home_injuries,
            "away_injuries": analysis.away_injuries,
        },
        "prediction": prediction,
    }


@router.get("/leagues")
async def get_supported_leagues():
    """Retourne la liste des ligues supportées"""
    return {
        "leagues": [
            {"id": 39, "name": "Premier League", "country": "England"},
            {"id": 140, "name": "La Liga", "country": "Spain"},
            {"id": 135, "name": "Serie A", "country": "Italy"},
            {"id": 78, "name": "Bundesliga", "country": "Germany"},
            {"id": 61, "name": "Ligue 1", "country": "France"},
            {"id": 2, "name": "Champions League", "country": "Europe"},
            {"id": 3, "name": "Europa League", "country": "Europe"},
            {"id": 848, "name": "Conference League", "country": "Europe"},
        ]
    }
