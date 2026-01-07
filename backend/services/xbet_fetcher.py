"""
Service pour récupérer les matchs et cotes depuis 1xbet
API publique sans authentification requise
"""
import httpx
import json
import os
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path
import random


class XbetFetcher:
    """Fetcher pour l'API 1xbet officielle"""

    def __init__(self, language: str = "en"):
        self.line_api = "https://1xbet.com/LineFeed/"
        self.live_api = "https://1xbet.com/LiveFeed/"
        # API The Odds API (gratuit 500 req/mois)
        self.odds_api = "https://api.the-odds-api.com/v4"
        self.odds_api_key = os.getenv("ODDS_API_KEY", "")
        self.language = language
        self.country = 1
        self.cache_dir = Path(__file__).parent.parent / "data" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # IDs des sports
        self.SPORT_FOOTBALL = 1
        self.SPORT_BASKETBALL = 3
        self.SPORT_TENNIS = 4

        # IDs des grandes ligues de football
        self.TOP_LEAGUES = {
            # Premier League, La Liga, Serie A, Bundesliga, Ligue 1
            # Champions League, Europa League, etc.
        }

        # Types de paris importants
        self.BET_TYPES = {
            1: "1X2",  # Victoire 1 / Nul / Victoire 2
            2: "Handicap",
            3: "1X2 1ère mi-temps",
            4: "1X2 2ème mi-temps",
            5: "Double chance",
            7: "Score exact",
            8: "Total buts",
            9: "Total équipe 1",
            10: "Total équipe 2",
            11: "Les deux équipes marquent",
            12: "Pair/Impair",
            14: "Mi-temps/Fin de match",
            15: "Over/Under",
            17: "Total",
            19: "Score exact 1ère mi-temps",
            21: "Handicap asiatique",
            28: "But de la tête",
            29: "Carton rouge",
            37: "Corners",
            45: "Score correct groupe",
            62: "Nombre de buts",
        }

    def _get_cache_path(self, cache_key: str) -> Path:
        return self.cache_dir / f"xbet_{cache_key}.json"

    def _get_from_cache(self, cache_key: str, max_age_minutes: int = 5) -> Optional[dict]:
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
            json.dump(data, f, default=str, ensure_ascii=False)

    async def _fetch(self, url: str, params: dict) -> Optional[dict]:
        """Effectue une requête HTTP vers l'API 1xbet"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
            "Referer": "https://1xbet.com/",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params, headers=headers)
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"[1xbet] Erreur {response.status_code}: {url}")
                    return None
        except Exception as e:
            print(f"[1xbet] Erreur requête: {e}")
            return None

    async def get_sports(self) -> List[Dict[str, Any]]:
        """Récupère la liste des sports disponibles"""
        cache_key = "sports"
        cached = self._get_from_cache(cache_key, max_age_minutes=60)
        if cached:
            return cached

        params = {
            "sports": 0,
            "lng": self.language,
            "tf": 1000000,
            "country": self.country
        }

        data = await self._fetch(f"{self.line_api}GetSportsShortZip", params)

        if not data or "Value" not in data:
            return []

        sports = []
        for sport in data.get("Value", []):
            if "N" in sport and "I" in sport:
                sports.append({
                    "id": sport["I"],
                    "name": sport["N"],
                })

        self._save_to_cache(cache_key, sports)
        return sports

    async def get_leagues(self, sport_id: int = 1) -> List[Dict[str, Any]]:
        """Récupère les ligues pour un sport"""
        cache_key = f"leagues_{sport_id}"
        cached = self._get_from_cache(cache_key, max_age_minutes=30)
        if cached:
            return cached

        params = {
            "sport": sport_id,
            "lng": self.language,
            "tf": 1000000,
            "tz": 5,
            "country": self.country
        }

        data = await self._fetch(f"{self.line_api}GetChampsZip", params)

        if not data or "Value" not in data:
            return []

        leagues = []
        for league in data.get("Value", []):
            if "L" in league and "LI" in league:
                leagues.append({
                    "id": league["LI"],
                    "name": league.get("L", league.get("LE", "Unknown")),
                    "country_icon": league.get("CI", ""),
                })

        self._save_to_cache(cache_key, leagues)
        return leagues

    async def get_matches_by_date(self, target_date: date = None, sport_id: int = 1) -> List[Dict[str, Any]]:
        """Récupère les matchs pour une date donnée"""
        if target_date is None:
            target_date = date.today()

        cache_key = f"matches_{target_date.isoformat()}_{sport_id}"
        cached = self._get_from_cache(cache_key, max_age_minutes=5)
        if cached:
            print(f"[1xbet Cache] {len(cached)} matchs pour {target_date}")
            return cached

        all_matches = []

        # Essayer The Odds API d'abord (si clé disponible)
        if self.odds_api_key:
            all_matches = await self._fetch_from_odds_api(target_date)
            if all_matches:
                self._save_to_cache(cache_key, all_matches)
                return all_matches

        # Essayer l'API 1xbet directe
        params = {
            "sports": sport_id,
            "count": 1000,
            "lng": self.language,
            "mode": 4,
            "country": self.country
        }

        data = await self._fetch(f"{self.line_api}BestGamesExtZip", params)

        if data and "Value" in data:
            print(f"[1xbet API] {len(data['Value'])} matchs récupérés")

            for match in data.get("Value", []):
                try:
                    match_ts = match.get("S", 0)
                    match_dt = datetime.fromtimestamp(match_ts)

                    if match_dt.date() != target_date:
                        continue

                    home_team = match.get("O1", "Équipe 1")
                    away_team = match.get("O2", "Équipe 2")
                    league_name = match.get("L", match.get("LE", "Football"))

                    odds_1x2 = {"1": 0, "X": 0, "2": 0}
                    events = match.get("E", [])
                    for event in events:
                        t = event.get("T")
                        c = event.get("C", 0)
                        if t == 1:
                            odds_1x2["1"] = c
                        elif t == 2:
                            odds_1x2["X"] = c
                        elif t == 3:
                            odds_1x2["2"] = c

                    all_matches.append({
                        "id": str(match.get("I", "")),
                        "home_team": home_team,
                        "away_team": away_team,
                        "home_logo": f"https://v3.traincdn.com/sfiles/logo_teams/{match.get('O1I', 0)}.png",
                        "away_logo": f"https://v3.traincdn.com/sfiles/logo_teams/{match.get('O2I', 0)}.png",
                        "league": league_name,
                        "league_icon": match.get("CI", ""),
                        "match_date": match_dt.isoformat(),
                        "match_time": match_dt.strftime("%H:%M"),
                        "timestamp": match_ts,
                        "odds_1x2": odds_1x2,
                        "sport_id": sport_id,
                    })
                except Exception as e:
                    print(f"[1xbet] Erreur parsing match: {e}")
                    continue

        # Si aucun match, générer des données de démo réalistes
        if not all_matches:
            print(f"[1xbet] Fallback sur données de démo pour {target_date}")
            all_matches = self._generate_demo_matches(target_date)

        if all_matches:
            self._save_to_cache(cache_key, all_matches)
            print(f"[1xbet] {len(all_matches)} matchs pour {target_date}")

        return all_matches

    async def _fetch_from_odds_api(self, target_date: date) -> List[Dict[str, Any]]:
        """Récupère les matchs depuis The Odds API"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.odds_api}/sports/soccer/odds",
                    params={
                        "apiKey": self.odds_api_key,
                        "regions": "eu",
                        "markets": "h2h",
                        "bookmakers": "onexbet"  # 1xbet
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    matches = []

                    for event in data:
                        commence_time = datetime.fromisoformat(event["commence_time"].replace("Z", "+00:00"))

                        if commence_time.date() != target_date:
                            continue

                        odds_1x2 = {"1": 1.5, "X": 3.5, "2": 2.5}

                        for bookmaker in event.get("bookmakers", []):
                            if bookmaker["key"] == "onexbet":
                                for market in bookmaker.get("markets", []):
                                    if market["key"] == "h2h":
                                        outcomes = market["outcomes"]
                                        for outcome in outcomes:
                                            if outcome["name"] == event["home_team"]:
                                                odds_1x2["1"] = outcome["price"]
                                            elif outcome["name"] == event["away_team"]:
                                                odds_1x2["2"] = outcome["price"]
                                            else:
                                                odds_1x2["X"] = outcome["price"]

                        matches.append({
                            "id": event["id"],
                            "home_team": event["home_team"],
                            "away_team": event["away_team"],
                            "home_logo": "https://via.placeholder.com/48",
                            "away_logo": "https://via.placeholder.com/48",
                            "league": event.get("sport_title", "Football"),
                            "match_date": commence_time.isoformat(),
                            "match_time": commence_time.strftime("%H:%M"),
                            "odds_1x2": odds_1x2,
                            "source": "odds-api",
                        })

                    print(f"[Odds API] {len(matches)} matchs récupérés")
                    return matches
        except Exception as e:
            print(f"[Odds API] Erreur: {e}")

        return []

    def _generate_demo_matches(self, target_date: date) -> List[Dict[str, Any]]:
        """Génère des matchs de démo avec cotes réalistes de type 1xbet"""
        teams_data = {
            "Premier League": [
                {"name": "Manchester City", "logo": "https://media.api-sports.io/football/teams/50.png", "strength": 92},
                {"name": "Arsenal", "logo": "https://media.api-sports.io/football/teams/42.png", "strength": 88},
                {"name": "Liverpool", "logo": "https://media.api-sports.io/football/teams/40.png", "strength": 89},
                {"name": "Chelsea", "logo": "https://media.api-sports.io/football/teams/49.png", "strength": 82},
                {"name": "Manchester United", "logo": "https://media.api-sports.io/football/teams/33.png", "strength": 80},
                {"name": "Tottenham", "logo": "https://media.api-sports.io/football/teams/47.png", "strength": 79},
            ],
            "La Liga": [
                {"name": "Real Madrid", "logo": "https://media.api-sports.io/football/teams/541.png", "strength": 91},
                {"name": "Barcelona", "logo": "https://media.api-sports.io/football/teams/529.png", "strength": 88},
                {"name": "Atletico Madrid", "logo": "https://media.api-sports.io/football/teams/530.png", "strength": 84},
                {"name": "Real Sociedad", "logo": "https://media.api-sports.io/football/teams/548.png", "strength": 78},
            ],
            "Serie A": [
                {"name": "Inter Milan", "logo": "https://media.api-sports.io/football/teams/505.png", "strength": 87},
                {"name": "Juventus", "logo": "https://media.api-sports.io/football/teams/496.png", "strength": 84},
                {"name": "AC Milan", "logo": "https://media.api-sports.io/football/teams/489.png", "strength": 83},
                {"name": "Napoli", "logo": "https://media.api-sports.io/football/teams/492.png", "strength": 82},
            ],
            "Bundesliga": [
                {"name": "Bayern Munich", "logo": "https://media.api-sports.io/football/teams/157.png", "strength": 90},
                {"name": "Dortmund", "logo": "https://media.api-sports.io/football/teams/165.png", "strength": 84},
                {"name": "RB Leipzig", "logo": "https://media.api-sports.io/football/teams/173.png", "strength": 82},
                {"name": "Leverkusen", "logo": "https://media.api-sports.io/football/teams/168.png", "strength": 85},
            ],
            "Ligue 1": [
                {"name": "PSG", "logo": "https://media.api-sports.io/football/teams/85.png", "strength": 90},
                {"name": "Monaco", "logo": "https://media.api-sports.io/football/teams/91.png", "strength": 80},
                {"name": "Marseille", "logo": "https://media.api-sports.io/football/teams/81.png", "strength": 79},
                {"name": "Lyon", "logo": "https://media.api-sports.io/football/teams/80.png", "strength": 78},
            ],
        }

        matches = []
        match_id = 500000

        for league_name, teams in teams_data.items():
            available = teams.copy()
            random.shuffle(available)

            for i in range(min(2, len(available) // 2)):
                home = available[i * 2]
                away = available[i * 2 + 1]

                # Générer cotes réalistes style 1xbet
                home_str = home["strength"]
                away_str = away["strength"]

                # Cotes basées sur la force relative
                diff = home_str - away_str + 5  # Avantage domicile
                if diff > 15:
                    odd_1 = round(1.20 + random.uniform(0, 0.15), 2)
                    odd_x = round(5.50 + random.uniform(0, 1), 2)
                    odd_2 = round(8.00 + random.uniform(0, 2), 2)
                elif diff > 8:
                    odd_1 = round(1.45 + random.uniform(0, 0.2), 2)
                    odd_x = round(4.00 + random.uniform(0, 0.5), 2)
                    odd_2 = round(5.50 + random.uniform(0, 1), 2)
                elif diff > 3:
                    odd_1 = round(1.75 + random.uniform(0, 0.25), 2)
                    odd_x = round(3.40 + random.uniform(0, 0.3), 2)
                    odd_2 = round(4.00 + random.uniform(0, 0.5), 2)
                elif diff > -3:
                    odd_1 = round(2.10 + random.uniform(0, 0.3), 2)
                    odd_x = round(3.20 + random.uniform(0, 0.2), 2)
                    odd_2 = round(3.00 + random.uniform(0, 0.4), 2)
                else:
                    odd_1 = round(2.80 + random.uniform(0, 0.5), 2)
                    odd_x = round(3.10 + random.uniform(0, 0.2), 2)
                    odd_2 = round(2.20 + random.uniform(0, 0.3), 2)

                match_hour = random.choice([14, 15, 16, 17, 18, 19, 20, 21])
                match_dt = datetime.combine(target_date, datetime.min.time().replace(hour=match_hour))

                matches.append({
                    "id": str(match_id),
                    "home_team": home["name"],
                    "away_team": away["name"],
                    "home_logo": home["logo"],
                    "away_logo": away["logo"],
                    "league": league_name,
                    "match_date": match_dt.isoformat(),
                    "match_time": match_dt.strftime("%H:%M"),
                    "odds_1x2": {"1": odd_1, "X": odd_x, "2": odd_2},
                    "source": "demo",
                })
                match_id += 1

        return matches

    async def get_match_details(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Récupère les détails d'un match avec TOUTES les cotes"""
        cache_key = f"match_{match_id}"
        cached = self._get_from_cache(cache_key, max_age_minutes=2)
        if cached:
            return cached

        params = {
            "id": match_id,
            "lng": self.language,
            "cfview": 0,
            "isSubGames": "true",
            "GroupEvents": "true",
            "countevents": 500  # Plus d'événements pour avoir tous les marchés
        }

        data = await self._fetch(f"{self.line_api}GetGameZip", params)

        if not data or "Value" not in data:
            return None

        match_data = data["Value"]

        # Informations de base
        result = {
            "id": match_id,
            "home_team": match_data.get("O1", ""),
            "away_team": match_data.get("O2", ""),
            "home_logo": f"https://v3.traincdn.com/sfiles/logo_teams/{match_data.get('O1I', 0)}.png",
            "away_logo": f"https://v3.traincdn.com/sfiles/logo_teams/{match_data.get('O2I', 0)}.png",
            "league": match_data.get("L", match_data.get("LE", "")),
            "sport": match_data.get("SN", "Football"),
            "match_date": datetime.fromtimestamp(match_data.get("S", 0)).isoformat(),
            "video_available": match_data.get("VI", False),
            "markets": {},
        }

        # Parser tous les marchés de paris
        markets = self._parse_all_markets(match_data)
        result["markets"] = markets

        self._save_to_cache(cache_key, result)
        return result

    def _parse_all_markets(self, match_data: dict) -> Dict[str, Any]:
        """Parse tous les marchés de paris disponibles"""
        markets = {
            "1x2": {"1": None, "X": None, "2": None},
            "double_chance": {"1X": None, "12": None, "X2": None},
            "total": {},  # Over/Under 0.5, 1.5, 2.5, 3.5, etc.
            "total_home": {},  # Total équipe domicile
            "total_away": {},  # Total équipe extérieur
            "btts": {"yes": None, "no": None},  # Les deux marquent
            "exact_score": {},  # Score exact
            "half_time": {"1": None, "X": None, "2": None},  # 1ère mi-temps
            "handicap": {},  # Handicap
            "asian_handicap": {},  # Handicap asiatique
            "odd_even": {"odd": None, "even": None},  # Pair/Impair
            "ht_ft": {},  # Mi-temps / Fin de match
            "corners": {},  # Corners
            "cards": {},  # Cartons
            "first_goal": {},  # Premier but
            "other": [],  # Autres marchés
        }

        # Parser les événements simples (E)
        for event in match_data.get("E", []):
            self._parse_event(event, markets)

        # Parser les événements groupés (GE)
        for group in match_data.get("GE", []):
            for event_group in group.get("E", []):
                if isinstance(event_group, list):
                    for event in event_group:
                        self._parse_event(event, markets)
                elif isinstance(event_group, dict):
                    self._parse_event(event_group, markets)

        # Aussi parser SG (SubGames) si disponible
        for subgame in match_data.get("SG", []):
            for event in subgame.get("E", []):
                self._parse_event(event, markets)

        return markets

    def _parse_event(self, event: dict, markets: dict):
        """Parse un événement de pari individuel"""
        t = event.get("T")  # Type de pari
        c = event.get("C")  # Cote
        p = event.get("P")  # Paramètre (ex: handicap, total)
        g = event.get("G")  # Groupe

        if c is None:
            return

        # 1X2 (types 1, 2, 3)
        if t == 1:
            markets["1x2"]["1"] = c
        elif t == 2:
            markets["1x2"]["X"] = c
        elif t == 3:
            markets["1x2"]["2"] = c

        # Double chance (types 4, 5, 6)
        elif t == 4:
            markets["double_chance"]["1X"] = c
        elif t == 5:
            markets["double_chance"]["12"] = c
        elif t == 6:
            markets["double_chance"]["X2"] = c

        # Total Over/Under (types 9, 10 avec paramètre)
        elif t == 9 and p is not None:
            key = f"over_{p}"
            markets["total"][key] = c
        elif t == 10 and p is not None:
            key = f"under_{p}"
            markets["total"][key] = c

        # Total équipe domicile
        elif t == 20 and p is not None:
            markets["total_home"][f"over_{p}"] = c
        elif t == 21 and p is not None:
            markets["total_home"][f"under_{p}"] = c

        # Total équipe extérieur
        elif t == 22 and p is not None:
            markets["total_away"][f"over_{p}"] = c
        elif t == 23 and p is not None:
            markets["total_away"][f"under_{p}"] = c

        # Les deux équipes marquent (BTTS)
        elif t == 33:
            markets["btts"]["yes"] = c
        elif t == 34:
            markets["btts"]["no"] = c

        # Score exact (type 7 ou autre avec paramètre spécifique)
        elif t == 7 and p is not None:
            markets["exact_score"][str(p)] = c

        # 1ère mi-temps 1X2 (types 11, 12, 13)
        elif t == 11:
            markets["half_time"]["1"] = c
        elif t == 12:
            markets["half_time"]["X"] = c
        elif t == 13:
            markets["half_time"]["2"] = c

        # Handicap (type 15, 16 avec paramètre)
        elif t == 15 and p is not None:
            markets["handicap"][f"1_{p}"] = c
        elif t == 16 and p is not None:
            markets["handicap"][f"2_{p}"] = c

        # Pair/Impair
        elif t == 18:
            markets["odd_even"]["even"] = c
        elif t == 19:
            markets["odd_even"]["odd"] = c

        # Corners
        elif t in [37, 38, 39] and p is not None:
            if t == 37:
                markets["corners"][f"over_{p}"] = c
            elif t == 38:
                markets["corners"][f"under_{p}"] = c
            elif t == 39:
                markets["corners"][f"exact_{p}"] = c

    async def get_football_predictions(self, target_date: date = None) -> List[Dict[str, Any]]:
        """Génère des prédictions pour les matchs de football"""
        if target_date is None:
            target_date = date.today()

        matches = await self.get_matches_by_date(target_date, sport_id=1)

        predictions = []

        for match in matches:
            odds = match.get("odds_1x2", {})
            odd_1 = odds.get("1", 0)
            odd_x = odds.get("X", 0)
            odd_2 = odds.get("2", 0)

            # Calculer les probabilités implicites des cotes
            if odd_1 and odd_x and odd_2:
                total_prob = (1/odd_1 + 1/odd_x + 1/odd_2)
                prob_1 = (1/odd_1) / total_prob * 100
                prob_x = (1/odd_x) / total_prob * 100
                prob_2 = (1/odd_2) / total_prob * 100

                # Déterminer la prédiction
                if prob_1 > prob_2 and prob_1 > prob_x:
                    predicted_outcome = "home"
                    recommended_bet = f"1 - {match['home_team']}"
                    best_prob = prob_1
                elif prob_2 > prob_1 and prob_2 > prob_x:
                    predicted_outcome = "away"
                    recommended_bet = f"2 - {match['away_team']}"
                    best_prob = prob_2
                else:
                    predicted_outcome = "draw"
                    recommended_bet = "X - Match Nul"
                    best_prob = prob_x

                # Confiance basée sur l'écart
                prob_diff = max(prob_1, prob_2, prob_x) - min(prob_1, prob_2, prob_x)
                if prob_diff > 30:
                    confidence = "very_high"
                elif prob_diff > 20:
                    confidence = "high"
                elif prob_diff > 10:
                    confidence = "medium"
                else:
                    confidence = "low"
            else:
                prob_1 = prob_x = prob_2 = 33.3
                predicted_outcome = "draw"
                recommended_bet = "X - Match Nul"
                best_prob = 33.3
                confidence = "low"

            predictions.append({
                "id": match["id"],
                "question": f"{match['home_team']} vs {match['away_team']}",
                "description": f"Match de {match['league']}",
                "home_team": match["home_team"],
                "away_team": match["away_team"],
                "home_logo": match["home_logo"],
                "away_logo": match["away_logo"],
                "league": match["league"],
                "match_date": match["match_date"],
                "match_time": match["match_time"],
                "outcomes": [match["home_team"], "Nul", match["away_team"]],
                "probabilities": {
                    "1": round(prob_1, 1),
                    "X": round(prob_x, 1),
                    "2": round(prob_2, 1),
                },
                "odds": {
                    "1": odd_1,
                    "X": odd_x,
                    "2": odd_2,
                },
                "recommended_bet": recommended_bet,
                "best_probability": round(best_prob, 1),
                "predicted_outcome": predicted_outcome,
                "confidence": confidence,
                "source": "1xbet",
                "factors": self._generate_factors(predicted_outcome, prob_1, prob_2),
            })

        # Trier par confiance puis probabilité
        confidence_order = {"very_high": 4, "high": 3, "medium": 2, "low": 1}
        predictions.sort(
            key=lambda x: (confidence_order.get(x["confidence"], 0), x["best_probability"]),
            reverse=True
        )

        return predictions

    def _generate_factors(self, outcome: str, prob_1: float, prob_2: float) -> List[str]:
        """Génère des facteurs d'analyse"""
        factors = []

        if outcome == "home":
            factors.append("Cotes favorables pour l'équipe à domicile")
            if prob_1 > 50:
                factors.append("Forte probabilité de victoire domicile")
        elif outcome == "away":
            factors.append("L'équipe visiteuse est favorite")
            if prob_2 > 50:
                factors.append("Forte probabilité de victoire extérieure")
        else:
            factors.append("Match équilibré")
            factors.append("Les cotes suggèrent un match serré")

        factors.append(random.choice([
            "Analyse des cotes 1xbet",
            "Basé sur les données du marché",
            "Probabilités calculées des cotes",
        ]))

        return factors

    async def generate_best_combos(self, predictions: List[Dict[str, Any]], max_combos: int = 5) -> List[Dict[str, Any]]:
        """Génère les meilleurs combinés basés sur les prédictions"""
        high_conf = [p for p in predictions if p.get("confidence") in ["very_high", "high"]]
        medium_conf = [p for p in predictions if p.get("confidence") == "medium"]

        combos = []

        def get_bet_odds(m):
            """Récupère la cote du pari recommandé"""
            outcome = m.get("predicted_outcome", "home")
            odds = m.get("odds", {})
            if outcome == "home":
                return odds.get("1", 1.5)
            elif outcome == "away":
                return odds.get("2", 1.5)
            else:
                return odds.get("X", 1.5)

        # Combo Sécurisé
        if len(high_conf) >= 2:
            safe_matches = high_conf[:2]
            total_odds = 1.0
            for m in safe_matches:
                total_odds *= get_bet_odds(m)

            combos.append({
                "id": "safe_1xbet",
                "type": "safe",
                "description": "Combiné Sécurisé 1xbet - 2 matchs haute confiance",
                "risk_level": "safe",
                "matches": [
                    {
                        "question": m.get("question"),
                        "teams": f"{m.get('home_team')} vs {m.get('away_team')}",
                        "bet": m.get("recommended_bet"),
                        "probability": m.get("best_probability"),
                        "odds": get_bet_odds(m),
                        "league": m.get("league"),
                    }
                    for m in safe_matches
                ],
                "total_odds": round(total_odds, 2),
                "potential_return": f"{round(total_odds * 10, 2)}€ pour 10€ misés",
            })

        # Combo Équilibré
        balanced = (high_conf + medium_conf)[:3]
        if len(balanced) >= 3:
            total_odds = 1.0
            for m in balanced:
                total_odds *= get_bet_odds(m)

            combos.append({
                "id": "balanced_1xbet",
                "type": "moderate",
                "description": "Combiné Équilibré 1xbet - 3 matchs",
                "risk_level": "moderate",
                "matches": [
                    {
                        "question": m.get("question"),
                        "teams": f"{m.get('home_team')} vs {m.get('away_team')}",
                        "bet": m.get("recommended_bet"),
                        "probability": m.get("best_probability"),
                        "odds": get_bet_odds(m),
                        "league": m.get("league"),
                    }
                    for m in balanced
                ],
                "total_odds": round(total_odds, 2),
                "potential_return": f"{round(total_odds * 10, 2)}€ pour 10€ misés",
            })

        # Combo Ambitieux
        ambitious = predictions[:5]
        if len(ambitious) >= 4:
            total_odds = 1.0
            for m in ambitious:
                total_odds *= get_bet_odds(m)

            combos.append({
                "id": "ambitious_1xbet",
                "type": "risky",
                "description": "Combiné Ambitieux 1xbet - 5 matchs gros gains",
                "risk_level": "risky",
                "matches": [
                    {
                        "question": m.get("question"),
                        "teams": f"{m.get('home_team')} vs {m.get('away_team')}",
                        "bet": m.get("recommended_bet"),
                        "probability": m.get("best_probability"),
                        "odds": get_bet_odds(m),
                        "league": m.get("league"),
                    }
                    for m in ambitious
                ],
                "total_odds": round(total_odds, 2),
                "potential_return": f"{round(total_odds * 10, 2)}€ pour 10€ misés",
            })

        return combos[:max_combos]
