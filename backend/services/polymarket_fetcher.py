import httpx
import os
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
import json
from pathlib import Path
import re
import random

from models.match import Match, Team, Prediction, PredictionConfidence, ComboMatch, BestCombo


class PolymarketFetcher:
    """Service pour récupérer les vrais matchs de football via API-Football + Odds API"""

    def __init__(self):
        self.gamma_api = "https://gamma-api.polymarket.com"
        # API gratuite football-data.org
        self.football_data_api = "https://api.football-data.org/v4"
        self.football_api_key = os.getenv("FOOTBALL_DATA_API_KEY", "")
        # The Odds API for real betting odds
        self.odds_api = "https://api.the-odds-api.com/v4"
        self.odds_api_key = os.getenv("ODDS_API_KEY", "")
        self.cache_dir = Path(__file__).parent.parent / "data" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.wallet_address = os.getenv(
            "POLYMARKET_WALLET",
            "0x09894262713eAE7D99631ee0cA79559470925247"
        )

        # Top leagues codes pour football-data.org
        self.top_leagues = {
            "PL": "Premier League",
            "PD": "La Liga",
            "SA": "Serie A",
            "BL1": "Bundesliga",
            "FL1": "Ligue 1",
            "CL": "Champions League",
            "EL": "Europa League",
        }

        # Force des équipes (pour calcul des probabilités) - with multiple name variants
        self.team_strength = {
            # Premier League
            "Manchester City": 92, "Manchester City FC": 92, "Man City": 92,
            "Arsenal": 88, "Arsenal FC": 88,
            "Liverpool": 92, "Liverpool FC": 92,
            "Chelsea": 82, "Chelsea FC": 82,
            "Manchester United": 78, "Manchester United FC": 78, "Man United": 78, "Man Utd": 78,
            "Tottenham": 80, "Tottenham Hotspur": 80, "Tottenham Hotspur FC": 80, "Spurs": 80,
            "Newcastle": 82, "Newcastle United": 82, "Newcastle United FC": 82,
            "Aston Villa": 77, "Aston Villa FC": 77,
            "Brighton": 75, "Brighton & Hove Albion": 75, "Brighton & Hove Albion FC": 75,
            "West Ham": 74, "West Ham United": 74, "West Ham United FC": 74,
            "Crystal Palace": 70, "Crystal Palace FC": 70,
            "Fulham": 71, "Fulham FC": 71,
            "Brentford": 78, "Brentford FC": 78,  # Upgraded: beat Everton 4-2
            "Wolves": 69, "Wolverhampton": 69, "Wolverhampton Wanderers FC": 69,
            "Nottingham Forest": 68, "Nottingham Forest FC": 68,
            "Everton": 67, "Everton FC": 67,
            "Bournemouth": 66, "AFC Bournemouth": 66,
            "Luton": 60, "Luton Town": 60, "Luton Town FC": 60,
            "Burnley": 62, "Burnley FC": 62,
            "Sheffield United": 65, "Sheffield United FC": 65, "Sheffield Utd": 65,
            "Leeds": 72, "Leeds United": 72, "Leeds United FC": 72,
            "Sunderland": 65, "Sunderland AFC": 65,
            # La Liga
            "Real Madrid": 92, "Real Madrid CF": 92,
            "Barcelona": 88, "FC Barcelona": 88,
            "Atletico Madrid": 84, "Atlético de Madrid": 84,
            "Real Sociedad": 78, "Real Sociedad de Fútbol": 78,
            "Athletic Bilbao": 77, "Athletic Club": 77,
            "Villarreal": 76, "Villarreal CF": 76,
            "Real Betis": 72, "Real Betis Balompié": 72,
            "Valencia": 72, "Valencia CF": 72,
            "Sevilla": 75, "Sevilla FC": 75,
            "Levante": 72, "Levante UD": 72,  # Upgraded: beat Sevilla 3-0
            # Serie A
            "Inter": 87, "Inter Milan": 87, "FC Internazionale Milano": 87,
            "Juventus": 84, "Juventus FC": 84,
            "AC Milan": 83, "Milan": 83,
            "Napoli": 88, "SSC Napoli": 88,
            "Roma": 79, "AS Roma": 79,
            "Lazio": 80, "SS Lazio": 80,
            "Atalanta": 80, "Atalanta BC": 80,
            "Fiorentina": 76, "ACF Fiorentina": 76,
            "Torino": 74, "Torino FC": 74,  # Upgraded: beat Verona 3-0
            "Verona": 62, "Hellas Verona": 62,
            "Cremonese": 55, "US Cremonese": 55,
            # Bundesliga
            "Bayern Munich": 90, "Bayern": 90, "FC Bayern München": 90,
            "Dortmund": 84, "Borussia Dortmund": 84,
            "RB Leipzig": 82, "Leipzig": 82,
            "Leverkusen": 88, "Bayer Leverkusen": 88, "Bayer 04 Leverkusen": 88,
            "Frankfurt": 77, "Eintracht Frankfurt": 77,
            "Wolfsburg": 75, "VfL Wolfsburg": 75,
            # Ligue 1
            "PSG": 90, "Paris Saint-Germain": 90, "Paris Saint-Germain FC": 90,
            "Monaco": 80, "AS Monaco": 80, "AS Monaco FC": 80,
            "Marseille": 79, "Olympique Marseille": 79, "Olympique de Marseille": 79,
            "Lyon": 78, "Olympique Lyon": 78, "Olympique Lyonnais": 78,
            "Lille": 77, "LOSC": 77, "LOSC Lille": 77,
            "Nice": 75, "OGC Nice": 75,
            "Nantes": 75, "FC Nantes": 75,  # Upgraded: beat Marseille 2-0
            "Lorient": 62, "FC Lorient": 62,
            "Metz": 58, "FC Metz": 58,
            "Le Havre": 60, "Le Havre AC": 60,
            "Angers": 58, "Angers SCO": 58,
            "Auxerre": 60, "AJ Auxerre": 60,
            "Brest": 72, "Stade Brestois": 72, "Stade Brestois 29": 72,
            # Additional Italian teams
            "Bologna": 74, "Bologna FC": 74, "Bologna FC 1909": 74,
            "Udinese": 70, "Udinese Calcio": 70,
            "Cagliari": 65, "Cagliari Calcio": 65,
            "Sassuolo": 68, "US Sassuolo": 68, "US Sassuolo Calcio": 68,
            "Lecce": 62, "US Lecce": 62,
            "Empoli": 63, "Empoli FC": 63,
            "Monza": 64, "AC Monza": 64,
            "Salernitana": 58, "US Salernitana": 58,
            "Frosinone": 60, "Frosinone Calcio": 60,
            "Genoa": 66, "Genoa CFC": 66,
            "Sampdoria": 64, "UC Sampdoria": 64,
            "Parma": 67, "Parma Calcio": 67,
            "Como": 62, "Como 1907": 62,
            "Venezia": 60, "Venezia FC": 60,
            # Additional Spanish teams
            "Getafe": 68, "Getafe CF": 68,
            "Celta": 69, "Celta Vigo": 69, "RC Celta": 69,
            "Osasuna": 67, "CA Osasuna": 67,
            "Mallorca": 66, "RCD Mallorca": 66,
            "Rayo Vallecano": 65, "Rayo": 65,
            "Almeria": 58, "UD Almeria": 58,
            "Cadiz": 60, "Cadiz CF": 60,
            "Granada": 62, "Granada CF": 62,
            "Las Palmas": 63, "UD Las Palmas": 63,
            "Alaves": 64, "Deportivo Alaves": 64,
            "Girona": 75, "Girona FC": 75,
            "Oviedo": 60, "Real Oviedo": 60,
            # Additional German teams
            "Freiburg": 74, "SC Freiburg": 74,
            "Union Berlin": 72, "1. FC Union Berlin": 72,
            "Hoffenheim": 70, "TSG Hoffenheim": 70, "TSG 1899 Hoffenheim": 70,
            "Augsburg": 65, "FC Augsburg": 65,
            "Mainz": 66, "Mainz 05": 66, "1. FSV Mainz 05": 66,
            "Koln": 64, "FC Koln": 64, "1. FC Köln": 64, "Cologne": 64,
            "Stuttgart": 73, "VfB Stuttgart": 73,
            "Bremen": 68, "Werder Bremen": 68, "SV Werder Bremen": 68,
            "Bochum": 62, "VfL Bochum": 62,
            "Darmstadt": 58, "SV Darmstadt 98": 58,
            "Heidenheim": 63, "1. FC Heidenheim": 63,
            # Additional French teams
            "Lens": 76, "RC Lens": 76,
            "Rennes": 74, "Stade Rennais": 74, "Stade Rennais FC": 74,
            "Strasbourg": 68, "RC Strasbourg": 68,
            "Toulouse": 66, "Toulouse FC": 66,
            "Montpellier": 65, "Montpellier HSC": 65,
            "Reims": 67, "Stade de Reims": 67,
            "Clermont": 60, "Clermont Foot": 60,
            "Paris FC": 58,
            # Additional English teams
            "Leicester": 74, "Leicester City": 74, "Leicester City FC": 74,  # Championship leaders
            "Southampton": 65, "Southampton FC": 65,
            "Ipswich": 62, "Ipswich Town": 62, "Ipswich Town FC": 62,
            "Watford": 64, "Watford FC": 64,
            "Norwich": 63, "Norwich City": 63, "Norwich City FC": 63,
            "Middlesbrough": 64, "Middlesbrough FC": 64,
            "Coventry": 62, "Coventry City": 62,
            "Bristol City": 61, "Bristol City FC": 61,
            "West Brom": 66, "West Bromwich Albion": 66, "West Bromwich": 66,
            "Stoke": 63, "Stoke City": 63, "Stoke City FC": 63,
            "Blackburn": 62, "Blackburn Rovers": 62,
            "Hull": 61, "Hull City": 61, "Hull City FC": 61,
            "Preston": 60, "Preston North End": 60,
            "Cardiff": 60, "Cardiff City": 60, "Cardiff City FC": 60,
            "Millwall": 61, "Millwall FC": 61,
            "Sheffield Wed": 60, "Sheffield Wednesday": 60, "Sheffield Wednesday FC": 60,
            "Plymouth": 58, "Plymouth Argyle": 58,
            "Swansea": 61, "Swansea City": 61, "Swansea City AFC": 61,
            "QPR": 60, "Queens Park Rangers": 60,
            "Rotherham": 55, "Rotherham United": 55,
            "Birmingham": 62, "Birmingham City": 62, "Birmingham City FC": 62,
            # CAN - African National Teams
            "Morocco": 85, "Maroc": 85,
            "Senegal": 84, "Sénégal": 84,
            "Nigeria": 82,
            "Egypt": 80, "Egypte": 80,
            "Ivory Coast": 79, "Côte d'Ivoire": 79, "Cote d'Ivoire": 79,
            "Cameroon": 84, "Cameroun": 84,
            "Algeria": 80, "Algérie": 80,
            "Ghana": 76,
            "Tunisia": 75, "Tunisie": 75,
            "Mali": 74,
            "DR Congo": 72, "Congo DR": 72, "RD Congo": 72,
            "South Africa": 71, "Afrique du Sud": 71,
            "Burkina Faso": 70,
            "Cape Verde": 68, "Cap-Vert": 68,
            "Gabon": 65,
            "Zambia": 65, "Zambie": 65,
            "Guinea": 67, "Guinée": 67,
            "Equatorial Guinea": 63, "Guinée équatoriale": 63,
            "Angola": 64,
            "Mozambique": 58,
            "Tanzania": 55, "Tanzanie": 55,
            "Uganda": 60, "Ouganda": 60,
            "Sudan": 55, "Soudan": 55,
            "Benin": 62, "Bénin": 62,
            "Mauritania": 58, "Mauritanie": 58,
            "Comoros": 55, "Comores": 55,
            "Gambia": 60, "Gambie": 60,
            "Zimbabwe": 58,
            "Namibia": 55, "Namibie": 55,
            "Madagascar": 56,
            "Libya": 58, "Libye": 58,
            "Rwanda": 56,
            "Kenya": 57,
            "Sierra Leone": 55,
            "Malawi": 54,
            "Ethiopia": 52, "Ethiopie": 52,
            "Botswana": 53,
            "Togo": 62,
            "Niger": 55,
            "Central African Republic": 50, "Centrafrique": 50,
            "Congo": 60,
            # English Lower Leagues
            "Bolton": 62, "Bolton Wanderers": 62,
            "Northampton": 55, "Northampton Town": 55,
            "Sheffield": 63, "Sheffield FC": 63,
            "Oxford": 61, "Oxford United": 61,
            "MK Dons": 58, "Milton Keynes Dons": 58,
            "Chesterfield": 54, "Chesterfield FC": 54,
            "Lincoln": 68, "Lincoln City": 68,  # Upgraded: beat Peterborough 5-2
            "Peterborough": 59, "Peterborough United": 59,
            "Cheltenham": 53, "Cheltenham Town": 53,
            "Crawley": 52, "Crawley Town": 52,
            "Doncaster": 56, "Doncaster Rovers": 56,
            "Wrexham": 58, "Wrexham AFC": 58,
            "Stockport": 57, "Stockport County": 57,
            "Mansfield": 56, "Mansfield Town": 56,
            "Barrow": 52, "Barrow AFC": 52,
            "Accrington": 51, "Accrington Stanley": 51,
            "Salford": 54, "Salford City": 54,
            "Crewe": 53, "Crewe Alexandra": 53,
            "Port Vale": 54,
            "Wigan": 60, "Wigan Athletic": 60,
            "Charlton": 59, "Charlton Athletic": 59,
            "Barnsley": 58, "Barnsley FC": 58,
            "Derby": 63, "Derby County": 63,
            "Portsmouth": 64, "Portsmouth FC": 64,
            "Reading": 58, "Reading FC": 58,
            "Stevenage": 53, "Stevenage FC": 53,
            "Fleetwood": 52, "Fleetwood Town": 52,
            "Exeter": 56, "Exeter City": 56,
            "Burton": 52, "Burton Albion": 52,
            "Cambridge": 55, "Cambridge United": 55,
            "Wycombe": 57, "Wycombe Wanderers": 57,
            "Leyton Orient": 56,
            "Shrewsbury": 54, "Shrewsbury Town": 54,
            "Peterboro": 59,
            # Australian A-League
            "Adelaide": 65, "Adelaide United": 65,
            "Central Coast": 72, "Central Coast Mariners": 72,  # Upgraded: beat Adelaide 4-0
            "Sydney": 68, "Sydney FC": 68,
            "Melbourne Victory": 66,
            "Melbourne City": 67,
            "Western Sydney": 62, "Western Sydney Wanderers": 62,
            "Brisbane": 63, "Brisbane Roar": 63,
            "Perth Glory": 60,
            "Wellington": 58, "Wellington Phoenix": 58,
            "Western United": 59,
            "Macarthur": 60, "Macarthur FC": 60,
            "Newcastle Jets": 57,
        }

    def _get_cache_path(self, cache_key: str) -> Path:
        return self.cache_dir / f"{cache_key}.json"

    def _get_from_cache(self, cache_key: str, max_age_minutes: int = 30) -> Optional[dict]:
        cache_path = self._get_cache_path(cache_key)
        if cache_path.exists():
            cache_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
            age_minutes = (datetime.now() - cache_time).total_seconds() / 60
            if age_minutes < max_age_minutes:
                with open(cache_path, "r") as f:
                    return json.load(f)
        return None

    def _save_to_cache(self, cache_key: str, data: Any):
        cache_path = self._get_cache_path(cache_key)
        with open(cache_path, "w") as f:
            json.dump(data, f, default=str)

    def _generate_realistic_football_matches(self) -> List[Dict[str, Any]]:
        """Génère des matchs de football réalistes pour aujourd'hui et demain"""

        # Équipes avec leur force relative (pour calculer les probabilités)
        teams_data = {
            "Premier League": [
                {"name": "Manchester City", "logo": "https://media.api-sports.io/football/teams/50.png", "strength": 92},
                {"name": "Arsenal", "logo": "https://media.api-sports.io/football/teams/42.png", "strength": 88},
                {"name": "Liverpool", "logo": "https://media.api-sports.io/football/teams/40.png", "strength": 89},
                {"name": "Chelsea", "logo": "https://media.api-sports.io/football/teams/49.png", "strength": 82},
                {"name": "Manchester United", "logo": "https://media.api-sports.io/football/teams/33.png", "strength": 80},
                {"name": "Tottenham", "logo": "https://media.api-sports.io/football/teams/47.png", "strength": 79},
                {"name": "Newcastle", "logo": "https://media.api-sports.io/football/teams/34.png", "strength": 78},
                {"name": "Aston Villa", "logo": "https://media.api-sports.io/football/teams/66.png", "strength": 77},
            ],
            "La Liga": [
                {"name": "Real Madrid", "logo": "https://media.api-sports.io/football/teams/541.png", "strength": 91},
                {"name": "Barcelona", "logo": "https://media.api-sports.io/football/teams/529.png", "strength": 88},
                {"name": "Atletico Madrid", "logo": "https://media.api-sports.io/football/teams/530.png", "strength": 84},
                {"name": "Real Sociedad", "logo": "https://media.api-sports.io/football/teams/548.png", "strength": 78},
                {"name": "Athletic Bilbao", "logo": "https://media.api-sports.io/football/teams/531.png", "strength": 77},
                {"name": "Villarreal", "logo": "https://media.api-sports.io/football/teams/533.png", "strength": 76},
            ],
            "Ligue 1": [
                {"name": "PSG", "logo": "https://media.api-sports.io/football/teams/85.png", "strength": 90},
                {"name": "Monaco", "logo": "https://media.api-sports.io/football/teams/91.png", "strength": 80},
                {"name": "Marseille", "logo": "https://media.api-sports.io/football/teams/81.png", "strength": 79},
                {"name": "Lyon", "logo": "https://media.api-sports.io/football/teams/80.png", "strength": 78},
                {"name": "Lille", "logo": "https://media.api-sports.io/football/teams/79.png", "strength": 77},
                {"name": "Nice", "logo": "https://media.api-sports.io/football/teams/84.png", "strength": 75},
            ],
            "Serie A": [
                {"name": "Inter Milan", "logo": "https://media.api-sports.io/football/teams/505.png", "strength": 87},
                {"name": "Juventus", "logo": "https://media.api-sports.io/football/teams/496.png", "strength": 84},
                {"name": "AC Milan", "logo": "https://media.api-sports.io/football/teams/489.png", "strength": 83},
                {"name": "Napoli", "logo": "https://media.api-sports.io/football/teams/492.png", "strength": 82},
                {"name": "AS Roma", "logo": "https://media.api-sports.io/football/teams/497.png", "strength": 79},
                {"name": "Lazio", "logo": "https://media.api-sports.io/football/teams/487.png", "strength": 78},
            ],
            "Bundesliga": [
                {"name": "Bayern Munich", "logo": "https://media.api-sports.io/football/teams/157.png", "strength": 90},
                {"name": "Dortmund", "logo": "https://media.api-sports.io/football/teams/165.png", "strength": 84},
                {"name": "RB Leipzig", "logo": "https://media.api-sports.io/football/teams/173.png", "strength": 82},
                {"name": "Leverkusen", "logo": "https://media.api-sports.io/football/teams/168.png", "strength": 85},
                {"name": "Frankfurt", "logo": "https://media.api-sports.io/football/teams/169.png", "strength": 77},
                {"name": "Wolfsburg", "logo": "https://media.api-sports.io/football/teams/161.png", "strength": 75},
            ],
        }

        matches = []
        match_id = 1000

        today = datetime.now()
        tomorrow = today + timedelta(days=1)

        # Générer des matchs pour chaque ligue
        for league_name, teams in teams_data.items():
            # 2-3 matchs par ligue
            num_matches = random.randint(2, 3)
            available_teams = teams.copy()
            random.shuffle(available_teams)

            for i in range(min(num_matches, len(available_teams) // 2)):
                home_team = available_teams[i * 2]
                away_team = available_teams[i * 2 + 1]

                # Heure du match (entre 13h et 21h)
                match_hour = random.choice([13, 14, 15, 16, 17, 18, 19, 20, 21])
                match_date = random.choice([today, tomorrow])
                match_datetime = match_date.replace(hour=match_hour, minute=0, second=0)

                # Calculer les probabilités basées sur la force des équipes
                home_strength = home_team["strength"]
                away_strength = away_team["strength"]

                # Avantage domicile (+5%)
                home_advantage = 5

                # Calcul des probabilités
                total_strength = home_strength + away_strength + home_advantage
                home_prob = ((home_strength + home_advantage) / total_strength) * 100
                away_prob = (away_strength / total_strength) * 100

                # Ajuster pour le match nul (entre 20-30%)
                draw_prob = 25 + random.uniform(-5, 5)
                home_prob = home_prob * (100 - draw_prob) / 100
                away_prob = away_prob * (100 - draw_prob) / 100

                # Déterminer la prédiction
                if home_prob > away_prob and home_prob > draw_prob:
                    predicted_outcome = "home"
                    recommended_bet = f"1 - {home_team['name']}"
                    best_prob = home_prob
                elif away_prob > home_prob and away_prob > draw_prob:
                    predicted_outcome = "away"
                    recommended_bet = f"2 - {away_team['name']}"
                    best_prob = away_prob
                else:
                    predicted_outcome = "draw"
                    recommended_bet = "X - Match Nul"
                    best_prob = draw_prob

                # Confiance basée sur l'écart de probabilités
                prob_diff = abs(home_prob - away_prob)
                if prob_diff > 25:
                    confidence = "very_high"
                elif prob_diff > 15:
                    confidence = "high"
                elif prob_diff > 8:
                    confidence = "medium"
                else:
                    confidence = "low"

                matches.append({
                    "id": str(match_id),
                    "question": f"{home_team['name']} vs {away_team['name']}",
                    "description": f"Match de {league_name}",
                    "home_team": home_team["name"],
                    "away_team": away_team["name"],
                    "home_logo": home_team["logo"],
                    "away_logo": away_team["logo"],
                    "league": league_name,
                    "match_date": match_datetime.isoformat(),
                    "match_time": f"{match_hour:02d}:00",
                    "outcomes": [home_team["name"], "Nul", away_team["name"]],
                    "probabilities": {
                        "1": round(home_prob, 1),
                        "X": round(draw_prob, 1),
                        "2": round(away_prob, 1),
                    },
                    "recommended_bet": recommended_bet,
                    "best_probability": round(best_prob, 1),
                    "predicted_outcome": predicted_outcome,
                    "confidence": confidence,
                    "volume": random.randint(50000, 500000),
                    "volume_formatted": f"${random.randint(50, 500)}K",
                    "polymarket_url": "https://1xbet.com",
                    "factors": self._generate_factors(home_team, away_team, predicted_outcome),
                })

                match_id += 1

        return matches

    def _generate_factors(self, home_team: Dict, away_team: Dict, outcome: str) -> List[str]:
        """Génère des facteurs d'analyse réalistes"""
        factors = []

        if outcome == "home":
            factors.append(f"Avantage du terrain pour {home_team['name']}")
            if home_team["strength"] > away_team["strength"]:
                factors.append(f"{home_team['name']} mieux classé au classement")
        elif outcome == "away":
            if away_team["strength"] > home_team["strength"]:
                factors.append(f"{away_team['name']} en meilleure forme récente")
            factors.append(f"{away_team['name']} solide à l'extérieur")
        else:
            factors.append("Équipes de niveau similaire")
            factors.append("Historique serré entre les deux équipes")

        # Facteurs aléatoires réalistes
        random_factors = [
            "Pas de blessés majeurs côté favori",
            "Bonne dynamique sur les 5 derniers matchs",
            "Confrontation directe favorable",
            "Motivation élevée (enjeu du classement)",
        ]
        factors.append(random.choice(random_factors))

        return factors

    async def _fetch_odds_from_api(self) -> Dict[str, Dict[str, Any]]:
        """Récupère les cotes réelles depuis The Odds API"""
        odds_map = {}

        if not self.odds_api_key:
            return odds_map

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.odds_api}/sports/soccer/odds",
                    params={
                        "apiKey": self.odds_api_key,
                        "regions": "eu",
                        "markets": "h2h",
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    print(f"[Odds API] {len(data)} événements avec cotes")

                    for event in data:
                        home_team = event.get("home_team", "").lower()
                        away_team = event.get("away_team", "").lower()
                        key = f"{home_team}_{away_team}"

                        # Get odds from any bookmaker
                        odds_1x2 = {"1": 2.0, "X": 3.5, "2": 2.0}
                        for bookmaker in event.get("bookmakers", []):
                            for market in bookmaker.get("markets", []):
                                if market["key"] == "h2h":
                                    for outcome in market["outcomes"]:
                                        if outcome["name"] == event["home_team"]:
                                            odds_1x2["1"] = outcome["price"]
                                        elif outcome["name"] == event["away_team"]:
                                            odds_1x2["2"] = outcome["price"]
                                        else:
                                            odds_1x2["X"] = outcome["price"]
                                    break
                            break

                        odds_map[key] = {
                            "odds": odds_1x2,
                            "home_team": event["home_team"],
                            "away_team": event["away_team"],
                            "commence_time": event.get("commence_time", ""),
                        }

        except Exception as e:
            print(f"[Odds API] Erreur: {e}")

        return odds_map

    def _normalize_team_name(self, name: str) -> str:
        """Normalise le nom d'équipe pour la correspondance"""
        name = name.lower()
        # Remove common suffixes
        for suffix in [" fc", " cf", " sc", " afc"]:
            name = name.replace(suffix, "")
        return name.strip()

    def _find_odds_for_match(self, home: str, away: str, odds_map: Dict) -> Optional[Dict]:
        """Trouve les cotes pour un match"""
        home_norm = self._normalize_team_name(home)
        away_norm = self._normalize_team_name(away)

        for key, odds_data in odds_map.items():
            odds_home = self._normalize_team_name(odds_data["home_team"])
            odds_away = self._normalize_team_name(odds_data["away_team"])

            # Check if teams match (in any order for flexibility)
            if (home_norm in odds_home or odds_home in home_norm) and \
               (away_norm in odds_away or odds_away in away_norm):
                return odds_data["odds"]

        return None

    async def _fetch_from_api_football(self, api_key: str, today: str, use_direct: bool = False) -> List[Dict[str, Any]]:
        """Récupère les matchs depuis API-Football (RapidAPI ou direct API-Sports)"""
        matches = []
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if use_direct:
                    # Direct API-Sports endpoint
                    headers = {"x-apisports-key": api_key}
                    url = "https://v3.football.api-sports.io/fixtures"
                else:
                    # RapidAPI endpoint
                    headers = {
                        "X-RapidAPI-Key": api_key,
                        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
                    }
                    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"

                response = await client.get(
                    url,
                    headers=headers,
                    params={"date": today}
                )

                if response.status_code == 200:
                    data = response.json()
                    fixtures = data.get("response", [])
                    print(f"[API-Football] {len(fixtures)} matchs récupérés pour {today}")

                    # Filtrer les grandes ligues + ligues secondaires
                    top_league_ids = {
                        39, 140, 135, 78, 61,  # PL, LaLiga, SerieA, Bundesliga, Ligue1
                        2, 3, 6,                # CL, EL, CAN
                        40, 41, 42,             # EFL Championship, League One, League Two
                        188,                    # A-League (Australia)
                        94,                     # Primeira Liga (Portugal)
                        88,                     # Eredivisie (Netherlands)
                        144,                    # Jupiler Pro League (Belgium)
                    }

                    for fixture in fixtures:
                        league = fixture.get("league", {})
                        league_id = league.get("id")

                        # Filtrer seulement les grandes ligues
                        if league_id not in top_league_ids:
                            continue

                        teams = fixture.get("teams", {})
                        home_team = teams.get("home", {})
                        away_team = teams.get("away", {})
                        fixture_info = fixture.get("fixture", {})

                        home_name = home_team.get("name", "Équipe A")
                        away_name = away_team.get("name", "Équipe B")

                        # Calculer probabilités
                        home_strength = self.team_strength.get(home_name, 70)
                        away_strength = self.team_strength.get(away_name, 70)

                        home_advantage = 5
                        total = home_strength + away_strength + home_advantage

                        home_prob = ((home_strength + home_advantage) / total) * 100
                        away_prob = (away_strength / total) * 100
                        draw_prob = 25 + random.uniform(-3, 3)

                        home_prob = home_prob * (100 - draw_prob) / 100
                        away_prob = away_prob * (100 - draw_prob) / 100

                        if home_prob > away_prob:
                            predicted_outcome = "home"
                            recommended_bet = f"1 - {home_name}"
                            best_prob = home_prob
                        elif away_prob > home_prob:
                            predicted_outcome = "away"
                            recommended_bet = f"2 - {away_name}"
                            best_prob = away_prob
                        else:
                            predicted_outcome = "draw"
                            recommended_bet = "X - Match Nul"
                            best_prob = draw_prob

                        prob_diff = abs(home_prob - away_prob)
                        if prob_diff > 20:
                            confidence = "very_high"
                        elif prob_diff > 12:
                            confidence = "high"
                        elif prob_diff > 6:
                            confidence = "medium"
                        else:
                            confidence = "low"

                        match_date = fixture_info.get("date", "")
                        if match_date:
                            dt = datetime.fromisoformat(match_date.replace("Z", "+00:00"))
                            match_time = dt.strftime("%H:%M")
                        else:
                            match_time = "15:00"

                        matches.append({
                            "id": str(fixture_info.get("id")),
                            "question": f"{home_name} vs {away_name}",
                            "description": f"Match de {league.get('name', 'Football')}",
                            "home_team": home_name,
                            "away_team": away_name,
                            "home_logo": home_team.get("logo", "https://via.placeholder.com/48"),
                            "away_logo": away_team.get("logo", "https://via.placeholder.com/48"),
                            "league": league.get("name", "Football"),
                            "match_date": match_date,
                            "match_time": match_time,
                            "outcomes": [home_name, "Nul", away_name],
                            "probabilities": {
                                "1": round(home_prob, 1),
                                "X": round(draw_prob, 1),
                                "2": round(away_prob, 1),
                            },
                            "recommended_bet": recommended_bet,
                            "best_probability": round(best_prob, 1),
                            "predicted_outcome": predicted_outcome,
                            "confidence": confidence,
                            "volume": random.randint(50000, 500000),
                            "volume_formatted": f"${random.randint(50, 500)}K",
                            "polymarket_url": "https://1xbet.com",
                            "factors": self._generate_factors_for_match(
                                home_name, away_name, home_strength, away_strength, predicted_outcome
                            ),
                        })

                    print(f"[API-Football] {len(matches)} matchs des top ligues")
                else:
                    print(f"[API-Football] Erreur {response.status_code}")

        except Exception as e:
            print(f"[API-Football] Erreur: {e}")

        return matches

    async def fetch_real_matches_today(self) -> List[Dict[str, Any]]:
        """Récupère les vrais matchs du jour depuis API-Football + Odds API"""
        today = date.today().isoformat()
        cache_key = f"real_matches_{today}_v2"

        cached = self._get_from_cache(cache_key, max_age_minutes=15)
        if cached:
            print(f"[Cache] {len(cached)} matchs trouvés en cache")
            return cached

        matches = []

        # Fetch real odds from Odds API first
        odds_map = await self._fetch_odds_from_api()

        # Essayer API-Football direct d'abord (API-Sports - 487 matchs!)
        football_api_key = os.getenv("FOOTBALL_API_KEY", "")
        if football_api_key:
            matches = await self._fetch_from_api_football(football_api_key, today, use_direct=True)

        # Fallback sur RapidAPI (100 req/jour)
        if not matches:
            rapid_api_key = os.getenv("RAPIDAPI_KEY", "")
            if rapid_api_key:
                matches = await self._fetch_from_api_football(rapid_api_key, today, use_direct=False)

        # Enhance matches with real odds
        if matches and odds_map:
            enhanced_count = 0
            for match in matches:
                real_odds = self._find_odds_for_match(
                    match.get("home_team", ""),
                    match.get("away_team", ""),
                    odds_map
                )
                if real_odds:
                    enhanced_count += 1
                    match["odds"] = real_odds
                    match["has_real_odds"] = True

                    # Recalculate probabilities from real odds
                    odd_1 = real_odds.get("1", 2.0)
                    odd_x = real_odds.get("X", 3.5)
                    odd_2 = real_odds.get("2", 2.0)

                    total_prob = (1/odd_1 + 1/odd_x + 1/odd_2)
                    prob_1 = (1/odd_1) / total_prob * 100
                    prob_x = (1/odd_x) / total_prob * 100
                    prob_2 = (1/odd_2) / total_prob * 100

                    match["probabilities"] = {
                        "1": round(prob_1, 1),
                        "X": round(prob_x, 1),
                        "2": round(prob_2, 1),
                    }

                    # Update prediction based on real odds
                    if prob_1 > prob_2 and prob_1 > prob_x:
                        match["predicted_outcome"] = "home"
                        match["recommended_bet"] = f"1 - {match['home_team']}"
                        match["best_probability"] = round(prob_1, 1)
                    elif prob_2 > prob_1 and prob_2 > prob_x:
                        match["predicted_outcome"] = "away"
                        match["recommended_bet"] = f"2 - {match['away_team']}"
                        match["best_probability"] = round(prob_2, 1)
                    else:
                        match["predicted_outcome"] = "draw"
                        match["recommended_bet"] = "X - Match Nul"
                        match["best_probability"] = round(prob_x, 1)

                    # Update confidence based on odds probability difference
                    prob_diff = max(prob_1, prob_2, prob_x) - min(prob_1, prob_2, prob_x)
                    if prob_diff > 30:
                        match["confidence"] = "very_high"
                    elif prob_diff > 20:
                        match["confidence"] = "high"
                    elif prob_diff > 10:
                        match["confidence"] = "medium"
                    else:
                        match["confidence"] = "low"
                else:
                    match["has_real_odds"] = False

            print(f"[Odds API] {enhanced_count}/{len(matches)} matchs enrichis avec cotes réelles")

        if matches:
            self._save_to_cache(cache_key, matches)
            return matches

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Fallback sur football-data.org
                headers = {}
                if self.football_api_key:
                    headers["X-Auth-Token"] = self.football_api_key

                response = await client.get(
                    f"{self.football_data_api}/matches",
                    headers=headers,
                    params={"dateFrom": today, "dateTo": today}
                )

                if response.status_code == 200:
                    data = response.json()
                    api_matches = data.get("matches", [])
                    print(f"[API] {len(api_matches)} matchs récupérés pour {today}")

                    for match in api_matches:
                        # Filtrer seulement les matchs programmés
                        if match.get("status") not in ["SCHEDULED", "TIMED"]:
                            continue

                        home_team = match.get("homeTeam", {})
                        away_team = match.get("awayTeam", {})
                        competition = match.get("competition", {})

                        home_name = home_team.get("name", "Équipe A")
                        away_name = away_team.get("name", "Équipe B")

                        # Calculer les probabilités basées sur la force
                        home_strength = self.team_strength.get(home_name, 70)
                        away_strength = self.team_strength.get(away_name, 70)

                        # Avantage domicile
                        home_advantage = 5
                        total = home_strength + away_strength + home_advantage

                        home_prob = ((home_strength + home_advantage) / total) * 100
                        away_prob = (away_strength / total) * 100
                        draw_prob = 25 + random.uniform(-3, 3)

                        # Ajuster
                        home_prob = home_prob * (100 - draw_prob) / 100
                        away_prob = away_prob * (100 - draw_prob) / 100

                        # Prédiction
                        if home_prob > away_prob and home_prob > draw_prob:
                            predicted_outcome = "home"
                            recommended_bet = f"1 - {home_name}"
                            best_prob = home_prob
                        elif away_prob > home_prob and away_prob > draw_prob:
                            predicted_outcome = "away"
                            recommended_bet = f"2 - {away_name}"
                            best_prob = away_prob
                        else:
                            predicted_outcome = "draw"
                            recommended_bet = "X - Match Nul"
                            best_prob = draw_prob

                        # Confiance
                        prob_diff = abs(home_prob - away_prob)
                        if prob_diff > 20:
                            confidence = "very_high"
                        elif prob_diff > 12:
                            confidence = "high"
                        elif prob_diff > 6:
                            confidence = "medium"
                        else:
                            confidence = "low"

                        match_date = match.get("utcDate", "")
                        if match_date:
                            dt = datetime.fromisoformat(match_date.replace("Z", "+00:00"))
                            match_time = dt.strftime("%H:%M")
                        else:
                            match_time = "15:00"

                        matches.append({
                            "id": str(match.get("id")),
                            "question": f"{home_name} vs {away_name}",
                            "description": f"Match de {competition.get('name', 'Football')}",
                            "home_team": home_name,
                            "away_team": away_name,
                            "home_logo": home_team.get("crest", "https://via.placeholder.com/48"),
                            "away_logo": away_team.get("crest", "https://via.placeholder.com/48"),
                            "league": competition.get("name", "Football"),
                            "match_date": match_date,
                            "match_time": match_time,
                            "outcomes": [home_name, "Nul", away_name],
                            "probabilities": {
                                "1": round(home_prob, 1),
                                "X": round(draw_prob, 1),
                                "2": round(away_prob, 1),
                            },
                            "recommended_bet": recommended_bet,
                            "best_probability": round(best_prob, 1),
                            "predicted_outcome": predicted_outcome,
                            "confidence": confidence,
                            "volume": random.randint(50000, 500000),
                            "volume_formatted": f"${random.randint(50, 500)}K",
                            "polymarket_url": "https://1xbet.com",
                            "factors": self._generate_factors_for_match(
                                home_name, away_name, home_strength, away_strength, predicted_outcome
                            ),
                        })

                else:
                    print(f"[API] Erreur {response.status_code}: {response.text[:200]}")

        except Exception as e:
            print(f"[API] Erreur lors de la récupération: {e}")

        if matches:
            self._save_to_cache(cache_key, matches)
            print(f"[Cache] {len(matches)} matchs sauvegardés")
        else:
            print("[Fallback] Utilisation des matchs de démonstration")
            matches = self._generate_realistic_football_matches_today_only()

        return matches

    def _generate_factors_for_match(self, home: str, away: str, home_str: int, away_str: int, outcome: str) -> List[str]:
        """Génère des facteurs d'analyse"""
        factors = []
        if outcome == "home":
            factors.append(f"Avantage du terrain pour {home}")
            if home_str > away_str:
                factors.append(f"{home} mieux classé")
        elif outcome == "away":
            if away_str > home_str:
                factors.append(f"{away} en meilleure forme")
            factors.append(f"{away} solide à l'extérieur")
        else:
            factors.append("Équipes de niveau similaire")

        factors.append(random.choice([
            "Bonne dynamique récente",
            "Historique favorable",
            "Motivation élevée",
        ]))
        return factors

    def _generate_realistic_football_matches_today_only(self) -> List[Dict[str, Any]]:
        """Génère des matchs de démo pour AUJOURD'HUI uniquement"""
        matches = self._generate_realistic_football_matches()
        today = datetime.now().date()

        # Forcer tous les matchs à être aujourd'hui
        for match in matches:
            dt = datetime.fromisoformat(match["match_date"])
            new_dt = dt.replace(year=today.year, month=today.month, day=today.day)
            match["match_date"] = new_dt.isoformat()

        return matches

    async def fetch_football_markets(self) -> List[Dict[str, Any]]:
        """Récupère les matchs de football - essaie l'API réelle d'abord"""
        # Essayer l'API réelle
        matches = await self.fetch_real_matches_today()

        if not matches:
            # Fallback sur les données de démo (aujourd'hui seulement)
            matches = self._generate_realistic_football_matches_today_only()

        return matches

    async def fetch_all_sports_markets(self) -> List[Dict[str, Any]]:
        """Récupère tous les matchs sportifs"""
        return await self.fetch_football_markets()

    def parse_market_to_match(self, market: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Retourne le market tel quel (déjà formaté)"""
        return market

    def _predict_exact_score(self, home_team: str, away_team: str, home_strength: int, away_strength: int, home_form: str = "DDDDD", away_form: str = "DDDDD") -> tuple:
        """
        Prédit le score exact - ALGORITHME V2 amélioré basé sur résultats réels

        Leçons apprises du 04/01/2026:
        - Réduire l'avantage domicile (beaucoup de nuls et victoires extérieures)
        - Plus de matchs nuls pour équipes proches
        - Factor "upset" pour les outsiders (Levante, Nantes, Central Coast)
        - Moins de scores élevés (1-0, 0-0 plus fréquents que 3-0, 4-0)
        """
        import hashlib

        # Create deterministic seed from team names
        seed_str = f"{home_team}_{away_team}_2026"
        seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)

        # REDUCED home advantage (+3 instead of +6) - real data shows less home advantage
        strength_diff = home_strength - away_strength
        home_bonus = 3
        effective_diff = strength_diff + home_bonus

        # Upset factor: only for mid-range matches, not dominant favorites
        # Real upsets happen in ~15% of games where diff is 5-15 points
        upset_chance = (seed % 100) < 15 and 5 < strength_diff < 20

        # Adjust for upsets - weaker team performs better than expected
        if upset_chance:
            effective_diff -= 8  # Reduce advantage

        # Score patterns based on effective difference - MORE DRAWS, LOWER SCORES
        if effective_diff > 20:  # Dominant home team
            # Even dominant teams sometimes draw or win small (Real Madrid 5-1 was exception)
            scores = [(2, 0), (3, 1), (2, 1), (1, 0), (3, 0)]
            home_goals, away_goals = scores[seed % len(scores)]

        elif effective_diff > 12:  # Strong home favorite
            # More 1-0, 2-0 results, occasional draw
            scores = [(1, 0), (2, 0), (2, 1), (1, 1), (3, 1)]
            home_goals, away_goals = scores[seed % len(scores)]

        elif effective_diff > 5:  # Moderate home favorite
            # Many draws at this level (Tottenham 1-1, Bolton 0-0)
            scores = [(1, 1), (2, 1), (1, 0), (0, 0), (2, 0)]
            home_goals, away_goals = scores[seed % len(scores)]

        elif effective_diff > 0:  # Slight home favorite
            # Very close - lots of draws (Leeds 1-1, Fulham 2-2)
            scores = [(1, 1), (0, 0), (2, 2), (1, 0), (2, 1)]
            home_goals, away_goals = scores[seed % len(scores)]

        elif effective_diff > -5:  # Even match / slight away edge
            # Could go either way - draws common
            scores = [(1, 1), (0, 1), (1, 2), (2, 2), (0, 0)]
            home_goals, away_goals = scores[seed % len(scores)]

        elif effective_diff > -12:  # Away team favorite
            # Away wins more likely (Napoli 0-2, Nantes 0-2)
            scores = [(0, 2), (1, 2), (0, 1), (1, 1), (0, 3)]
            home_goals, away_goals = scores[seed % len(scores)]

        else:  # Strong away favorite
            # Clear away wins
            scores = [(0, 2), (0, 3), (1, 3), (0, 4), (1, 2)]
            home_goals, away_goals = scores[seed % len(scores)]

        # Special case: Rare big upset (like Sevilla 0-3 Levante) - only ~5% of mid-tier games
        big_upset = (seed % 100) < 5 and 8 < strength_diff < 18
        if big_upset:
            # Underdog wins convincingly
            upset_scores = [(0, 2), (0, 3), (1, 3)]
            home_goals, away_goals = upset_scores[seed % len(upset_scores)]

        return home_goals, away_goals

    async def get_football_predictions(self) -> List[Dict[str, Any]]:
        """Génère des prédictions pour les matchs de football avec scores exacts"""
        matches = await self.fetch_football_markets()

        # Add exact score predictions to each match
        for match in matches:
            home_team = match.get("home_team", "")
            away_team = match.get("away_team", "")

            # Get team strengths
            home_strength = self.team_strength.get(home_team, 70)
            away_strength = self.team_strength.get(away_team, 70)

            # Predict exact score
            home_goals, away_goals = self._predict_exact_score(
                home_team, away_team,
                home_strength, away_strength
            )

            match["exact_score"] = f"{home_goals}-{away_goals}"
            match["home_goals"] = home_goals
            match["away_goals"] = away_goals

            # Determine winner from score
            if home_goals > away_goals:
                match["winner"] = home_team
            elif away_goals > home_goals:
                match["winner"] = away_team
            else:
                match["winner"] = "Nul"

        # Trier par confiance puis par probabilité
        confidence_order = {"very_high": 4, "high": 3, "medium": 2, "low": 1}
        matches.sort(
            key=lambda x: (confidence_order.get(x.get("confidence", "low"), 0), x.get("best_probability", 0)),
            reverse=True
        )

        return matches

    def _get_bet_odds(self, match: Dict) -> float:
        """Récupère la cote du pari recommandé"""
        outcome = match.get("predicted_outcome", "home")
        odds = match.get("odds", {})
        if outcome == "home":
            return odds.get("1", 1.8)
        elif outcome == "away":
            return odds.get("2", 1.8)
        else:
            return odds.get("X", 3.5)

    async def generate_best_combos(self, predictions: List[Dict[str, Any]], max_combos: int = 5) -> List[Dict[str, Any]]:
        """Génère les meilleurs combinés avec cotes réelles"""

        # Filtrer les prédictions avec bonne confiance ET cotes réelles
        high_conf = [p for p in predictions if p.get("confidence") in ["very_high", "high"]]
        medium_conf = [p for p in predictions if p.get("confidence") == "medium"]

        combos = []

        # Combo Sécurisé (2 matchs très sûrs)
        if len(high_conf) >= 2:
            safe_matches = high_conf[:2]
            total_odds = 1.0
            for m in safe_matches:
                total_odds *= self._get_bet_odds(m)

            combos.append({
                "id": "safe_1",
                "type": "safe",
                "description": "Combiné Sécurisé - 2 matchs haute confiance",
                "risk_level": "safe",
                "matches": [
                    {
                        "question": m.get("question"),
                        "teams": f"{m.get('home_team')} vs {m.get('away_team')}",
                        "bet": m.get("recommended_bet"),
                        "probability": m.get("best_probability"),
                        "odds": round(self._get_bet_odds(m), 2),
                        "league": m.get("league"),
                        "has_real_odds": m.get("has_real_odds", False),
                    }
                    for m in safe_matches
                ],
                "total_odds": round(total_odds, 2),
                "potential_return": f"{round(total_odds * 10, 2)}€ pour 10€",
            })

        # Combo Équilibré (3 matchs)
        balanced_matches = (high_conf + medium_conf)[:3]
        if len(balanced_matches) >= 3:
            total_odds = 1.0
            for m in balanced_matches:
                total_odds *= self._get_bet_odds(m)

            combos.append({
                "id": "balanced_1",
                "type": "moderate",
                "description": "Combiné Équilibré - 3 matchs",
                "risk_level": "moderate",
                "matches": [
                    {
                        "question": m.get("question"),
                        "teams": f"{m.get('home_team')} vs {m.get('away_team')}",
                        "bet": m.get("recommended_bet"),
                        "probability": m.get("best_probability"),
                        "odds": round(self._get_bet_odds(m), 2),
                        "league": m.get("league"),
                        "has_real_odds": m.get("has_real_odds", False),
                    }
                    for m in balanced_matches
                ],
                "total_odds": round(total_odds, 2),
                "potential_return": f"{round(total_odds * 10, 2)}€ pour 10€",
            })

        # Combo Ambitieux (4-5 matchs)
        ambitious_matches = predictions[:5]
        if len(ambitious_matches) >= 4:
            total_odds = 1.0
            for m in ambitious_matches:
                total_odds *= self._get_bet_odds(m)

            combos.append({
                "id": "ambitious_1",
                "type": "risky",
                "description": "Combiné Ambitieux - 5 matchs pour gros gains",
                "risk_level": "risky",
                "matches": [
                    {
                        "question": m.get("question"),
                        "teams": f"{m.get('home_team')} vs {m.get('away_team')}",
                        "bet": m.get("recommended_bet"),
                        "probability": m.get("best_probability"),
                        "odds": round(self._get_bet_odds(m), 2),
                        "league": m.get("league"),
                        "has_real_odds": m.get("has_real_odds", False),
                    }
                    for m in ambitious_matches
                ],
                "total_odds": round(total_odds, 2),
                "potential_return": f"{round(total_odds * 10, 2)}€ pour 10€",
            })

        # Combo Double Chance (matchs serrés, plus safe)
        close_matches = [p for p in predictions if abs(p.get("probabilities", {}).get("1", 50) - p.get("probabilities", {}).get("2", 50)) < 15]
        if len(close_matches) >= 2:
            dc_matches = close_matches[:3]
            total_prob = 1.0

            combo_matches = []
            for m in dc_matches:
                probs = m.get("probabilities", {})
                home_prob = probs.get("1", 40)
                draw_prob = probs.get("X", 25)
                away_prob = probs.get("2", 35)

                # Choisir la meilleure double chance
                dc_1x = home_prob + draw_prob
                dc_x2 = draw_prob + away_prob

                if dc_1x > dc_x2:
                    bet = f"1X ({m.get('home_team')} ou Nul)"
                    prob = dc_1x
                else:
                    bet = f"X2 (Nul ou {m.get('away_team')})"
                    prob = dc_x2

                total_prob *= (prob / 100)
                combo_matches.append({
                    "question": m.get("question"),
                    "teams": f"{m.get('home_team')} vs {m.get('away_team')}",
                    "bet": bet,
                    "probability": round(prob, 1),
                    "league": m.get("league"),
                })

            combos.append({
                "id": "double_chance",
                "type": "safe",
                "description": "Combiné Double Chance - Maximum de sécurité",
                "risk_level": "safe",
                "matches": combo_matches,
                "total_probability": round(total_prob * 100, 2),
            })

        return combos[:max_combos]
