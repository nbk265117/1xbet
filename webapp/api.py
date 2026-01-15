"""
API FastAPI pour les prédictions de matchs de football
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import requests
from datetime import datetime
import asyncio
import httpx

app = FastAPI(title="Football Predictions API")

# CORS pour permettre les requêtes du frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = "111a3d8d8abb91aacf250df4ea6f5116"
BASE_URL = "https://v3.football.api-sports.io"

# Ligues prioritaires
PRIORITY_LEAGUES = {
    39: "Premier League",
    140: "La Liga",
    135: "Serie A",
    78: "Bundesliga",
    61: "Ligue 1",
    2: "Champions League",
    3: "Europa League",
    848: "Conference League",
    262: "Liga MX",
    94: "Primeira Liga",
    88: "Eredivisie",
    90: "KNVB Beker",
    144: "Jupiler Pro",
    203: "Super Lig",
    206: "Türkiye Kupası",
    179: "Scottish Prem",
    197: "Super League",
    307: "Saudi Pro League",
    305: "Qatar Stars",
    301: "UAE Pro League",
    330: "Kuwait Premier",
    417: "Bahrain Premier",
    895: "Egypt Cup",
    233: "Egypt Premier",
    1: "World Cup",
    4: "Euro",
    5: "Nations League",
    6: "Coupe de France",
    9: "Copa America",
    10: "Friendlies",
}

class PredictionResponse(BaseModel):
    date: str
    total_matches: int
    predictions: list


def get_confidence(home_pct: str, away_pct: str, draw_pct: str, h2h_home: str = "50%") -> int:
    """Calcule le niveau de confiance basé sur les probabilités"""
    try:
        home = int(home_pct.replace('%', ''))
        away = int(away_pct.replace('%', ''))
        draw = int(draw_pct.replace('%', ''))

        max_prob = max(home, away, draw)
        if max_prob >= 50:
            return 4
        elif max_prob >= 45:
            return 3
        else:
            return 2
    except:
        return 2


def determine_prediction(home_pct: str, away_pct: str, draw_pct: str,
                         home_name: str, away_name: str, advice: str) -> tuple:
    """Détermine la prédiction basée sur les probabilités et le conseil API"""
    try:
        home = int(home_pct.replace('%', ''))
        away = int(away_pct.replace('%', ''))
        draw = int(draw_pct.replace('%', ''))
    except:
        return "X", "Match Nul"

    # Grands clubs égyptiens - correction manuelle
    big_clubs = ["Al Ahly", "Zamalek", "Zamalek SC", "Pyramids FC"]

    if home >= 45 and away <= 10:
        return "1", f"{home_name} gagne"
    elif away >= 45 and home <= 10:
        # Vérifier si c'est un grand club à domicile
        if any(club in home_name for club in big_clubs):
            return "1X", f"DC {home_name}"
        return "2", f"{away_name} gagne"
    elif home >= 35 and draw >= 35:
        return "1X", f"DC {home_name}"
    elif away >= 35 and draw >= 35:
        # Vérifier si c'est un grand club à l'extérieur
        if any(club in away_name for club in big_clubs):
            return "X2", f"DC {away_name}"
        return "X2", f"DC {away_name}"
    elif draw >= 40:
        return "X", "Match Nul probable"
    else:
        if home > away:
            return "1X", f"DC {home_name}"
        else:
            return "X2", f"DC {away_name}"


def determine_over_under(goals_home: str, goals_away: str, advice: str) -> str:
    """Détermine Over/Under basé sur les prédictions de buts"""
    try:
        # Parser les ranges de buts
        if goals_home and goals_away:
            # Format typique: "-1.5" ou "-2.5--3.5"
            if "3.5" in str(goals_home) or "3.5" in str(goals_away):
                return "Over 2.5"
            elif "2.5" in str(goals_home) or "2.5" in str(goals_away):
                return "Under 3.5"
            else:
                return "Under 2.5"
    except:
        pass

    # Vérifier le conseil
    if advice:
        if "+2.5" in advice or "+3.5" in advice:
            return "Over 2.5"
        elif "-2.5" in advice or "-3.5" in advice:
            return "Under 2.5"

    return "Under 2.5"


async def fetch_prediction(client: httpx.AsyncClient, fixture_id: int, fixture_info: dict) -> Optional[dict]:
    """Récupère la prédiction pour un match"""
    try:
        resp = await client.get(
            f"{BASE_URL}/predictions",
            headers={"x-apisports-key": API_KEY},
            params={"fixture": fixture_id}
        )
        data = resp.json()
        pred = data.get("response", [{}])[0]

        if not pred:
            return None

        predictions = pred.get("predictions", {})
        percent = predictions.get("percent", {})
        goals = predictions.get("goals", {})
        comparison = pred.get("comparison", {})

        home_pct = percent.get("home", "33%")
        draw_pct = percent.get("draw", "33%")
        away_pct = percent.get("away", "33%")
        advice = predictions.get("advice", "")

        prediction, prediction_text = determine_prediction(
            home_pct, away_pct, draw_pct,
            fixture_info["home"], fixture_info["away"],
            advice
        )

        over_under = determine_over_under(
            goals.get("home", ""),
            goals.get("away", ""),
            advice
        )

        confidence = get_confidence(home_pct, away_pct, draw_pct)

        return {
            "id": fixture_id,
            "time": fixture_info["time"],
            "league": fixture_info["league"],
            "home": fixture_info["home"],
            "away": fixture_info["away"],
            "home_pct": home_pct,
            "draw_pct": draw_pct,
            "away_pct": away_pct,
            "prediction": prediction,
            "prediction_text": prediction_text,
            "over_under": over_under,
            "confidence": confidence,
            "advice": advice
        }
    except Exception as e:
        print(f"Error fetching prediction for {fixture_id}: {e}")
        return None


@app.get("/api/predictions/{date}")
async def get_predictions(date: str):
    """
    Récupère les prédictions pour une date donnée
    Format date: YYYY-MM-DD
    """
    try:
        # Valider le format de date
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Format de date invalide. Utilisez YYYY-MM-DD")

    # Récupérer les matchs du jour
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{BASE_URL}/fixtures",
            headers={"x-apisports-key": API_KEY},
            params={"date": date}
        )
        data = resp.json()
        fixtures = data.get("response", [])

        if not fixtures:
            return PredictionResponse(
                date=date,
                total_matches=0,
                predictions=[]
            )

        # Filtrer les matchs des ligues prioritaires
        important_fixtures = []
        for f in fixtures:
            league_id = f["league"]["id"]
            league_name = f["league"]["name"]

            # Inclure si ligue prioritaire ou contient des mots-clés importants
            is_priority = league_id in PRIORITY_LEAGUES
            is_important_name = any(kw in league_name for kw in [
                "Serie A", "Liga", "Premier", "Bundesliga", "Ligue 1",
                "Champions", "Europa", "Cup", "Copa", "Coupe"
            ])

            if is_priority or is_important_name:
                important_fixtures.append({
                    "id": f["fixture"]["id"],
                    "time": f["fixture"]["date"][11:16],
                    "league": league_name,
                    "home": f["teams"]["home"]["name"],
                    "away": f["teams"]["away"]["name"]
                })

        # Limiter à 30 matchs max pour éviter les timeouts
        important_fixtures = important_fixtures[:30]

        # Récupérer les prédictions en parallèle
        tasks = [
            fetch_prediction(client, fix["id"], fix)
            for fix in important_fixtures
        ]
        results = await asyncio.gather(*tasks)

        # Filtrer les résultats valides et trier par heure
        predictions = [r for r in results if r is not None]
        predictions.sort(key=lambda x: x["time"])

        return PredictionResponse(
            date=date,
            total_matches=len(predictions),
            predictions=predictions
        )


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
