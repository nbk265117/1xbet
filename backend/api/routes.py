from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBasic
from datetime import date, datetime
from typing import List, Dict, Any
import os

from models.match import Match, Prediction, BestCombo
from services.match_fetcher import MatchFetcher
from services.predictor import MatchPredictor
from services.polymarket_fetcher import PolymarketFetcher
from services.xbet_fetcher import XbetFetcher

router = APIRouter(prefix="/api", tags=["predictions"])

# Services
match_fetcher = MatchFetcher()
predictor = MatchPredictor()
polymarket = PolymarketFetcher()
xbet = XbetFetcher(language="en")

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


# ==================== POLYMARKET ENDPOINTS ====================

@router.get("/polymarket/football")
async def get_polymarket_football():
    """Récupère les marchés football depuis Polymarket"""
    markets = await polymarket.fetch_football_markets()

    parsed_markets = []
    for market in markets:
        parsed = polymarket.parse_market_to_match(market)
        if parsed:
            parsed_markets.append(parsed)

    return {
        "source": "polymarket",
        "count": len(parsed_markets),
        "markets": parsed_markets,
    }


@router.get("/polymarket/sports")
async def get_polymarket_sports():
    """Récupère TOUS les marchés sportifs depuis Polymarket"""
    markets = await polymarket.fetch_all_sports_markets()

    parsed_markets = []
    for market in markets:
        parsed = polymarket.parse_market_to_match(market)
        if parsed:
            parsed_markets.append(parsed)

    return {
        "source": "polymarket",
        "count": len(parsed_markets),
        "markets": parsed_markets,
    }


@router.get("/polymarket/predictions")
async def get_polymarket_predictions():
    """Génère des prédictions basées sur les marchés Polymarket"""
    predictions = await polymarket.get_football_predictions()

    return {
        "source": "polymarket",
        "count": len(predictions),
        "predictions": predictions,
    }


@router.get("/polymarket/combos")
async def get_polymarket_combos(max_combos: int = 5):
    """Génère les meilleurs combinés basés sur Polymarket"""
    predictions = await polymarket.get_football_predictions()
    combos = await polymarket.generate_best_combos(predictions, max_combos)

    return {
        "source": "polymarket",
        "combos": combos,
    }


@router.get("/polymarket/market/{market_id}")
async def get_polymarket_market_detail(market_id: str):
    """Détails d'un marché Polymarket spécifique"""
    markets = await polymarket.fetch_all_sports_markets()

    market = next((m for m in markets if m.get("id") == market_id), None)

    if not market:
        raise HTTPException(status_code=404, detail="Marché non trouvé")

    parsed = polymarket.parse_market_to_match(market)

    return {
        "market": parsed,
        "raw": market,
    }


# ==================== 1XBET ENDPOINTS ====================

@router.get("/xbet/sports")
async def get_xbet_sports():
    """Récupère la liste des sports disponibles sur 1xbet"""
    sports = await xbet.get_sports()
    return {
        "source": "1xbet",
        "count": len(sports),
        "sports": sports,
    }


@router.get("/xbet/leagues")
async def get_xbet_leagues(sport_id: int = 1):
    """Récupère les ligues pour un sport (1=Football)"""
    leagues = await xbet.get_leagues(sport_id)
    return {
        "source": "1xbet",
        "sport_id": sport_id,
        "count": len(leagues),
        "leagues": leagues,
    }


@router.get("/xbet/matches")
async def get_xbet_matches(date_str: str = None, sport_id: int = 1):
    """Récupère les matchs pour une date donnée depuis 1xbet"""
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Format de date invalide. Utilisez YYYY-MM-DD")
    else:
        target_date = date.today()

    matches = await xbet.get_matches_by_date(target_date, sport_id)

    return {
        "source": "1xbet",
        "date": target_date.isoformat(),
        "count": len(matches),
        "matches": matches,
    }


@router.get("/xbet/match/{match_id}")
async def get_xbet_match_detail(match_id: str):
    """Récupère les détails d'un match avec TOUTES les cotes depuis 1xbet"""
    match_details = await xbet.get_match_details(match_id)

    if not match_details:
        raise HTTPException(status_code=404, detail="Match non trouvé")

    return {
        "source": "1xbet",
        "match": match_details,
    }


@router.get("/xbet/predictions")
async def get_xbet_predictions(date_str: str = None):
    """Génère des prédictions basées sur les cotes 1xbet"""
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Format de date invalide. Utilisez YYYY-MM-DD")
    else:
        target_date = date.today()

    predictions = await xbet.get_football_predictions(target_date)

    return {
        "source": "1xbet",
        "date": target_date.isoformat(),
        "count": len(predictions),
        "predictions": predictions,
    }


@router.get("/xbet/combos")
async def get_xbet_combos(date_str: str = None, max_combos: int = 5):
    """Génère les meilleurs combinés basés sur les cotes 1xbet"""
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Format de date invalide. Utilisez YYYY-MM-DD")
    else:
        target_date = date.today()

    predictions = await xbet.get_football_predictions(target_date)
    combos = await xbet.generate_best_combos(predictions, max_combos)

    return {
        "source": "1xbet",
        "date": target_date.isoformat(),
        "combos": combos,
    }


# ==================== LEGACY ENDPOINTS (API-Football) ====================

@router.get("/matches/{date_str}", response_model=List[Match])
async def get_matches(date_str: str):
    """Récupère tous les matchs pour une date donnée (API-Football)"""
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
    """Génère les prédictions pour tous les matchs d'une date (API-Football)"""
    try:
        match_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Format de date invalide. Utilisez YYYY-MM-DD")

    matches = await match_fetcher.fetch_matches_by_date(match_date)

    if not matches:
        return []

    predictions = []

    for match in matches:
        analysis = await match_fetcher.fetch_match_analysis(match)
        prediction = predictor.predict_match(analysis)
        predictions.append(prediction)

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
    """Génère les meilleurs combinés pour une date (API-Football)"""
    try:
        match_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Format de date invalide. Utilisez YYYY-MM-DD")

    matches = await match_fetcher.fetch_matches_by_date(match_date)

    if not matches:
        return []

    predictions = []
    for match in matches:
        analysis = await match_fetcher.fetch_match_analysis(match)
        prediction = predictor.predict_match(analysis)
        predictions.append(prediction)

    combos = predictor.generate_best_combos(predictions, max_combos)

    return combos


@router.get("/match/{match_id}/analysis")
async def get_match_analysis(match_id: int, date_str: str):
    """Analyse détaillée d'un match spécifique (API-Football)"""
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
