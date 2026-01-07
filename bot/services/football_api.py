"""
Service pour récupérer les données depuis API-Football
"""
import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from config.settings import FOOTBALL_API_KEY, FOOTBALL_API_BASE_URL
from config.leagues import is_league_allowed, get_league_name, get_league_priority
from models.match import Match, Team

logger = logging.getLogger(__name__)


class FootballAPIService:
    """Service pour interagir avec API-Football"""

    def __init__(self):
        self.base_url = FOOTBALL_API_BASE_URL
        self.headers = {
            "x-apisports-key": FOOTBALL_API_KEY
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Effectue une requête vers l'API"""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get("errors"):
                logger.error(f"API Error: {data['errors']}")
                return None

            return data
        except requests.RequestException as e:
            logger.error(f"Request error: {e}")
            return None

    def get_fixtures_by_date(self, date: str) -> List[Match]:
        """
        Récupère les matchs pour une date donnée
        Args:
            date: Format YYYY-MM-DD
        Returns:
            Liste des matchs filtrés par ligues autorisées
        """
        logger.info(f"Fetching fixtures for {date}")

        data = self._make_request("fixtures", {"date": date})
        if not data or "response" not in data:
            return []

        matches = []
        for fixture in data["response"]:
            league_id = fixture["league"]["id"]

            # Filtrer par ligues autorisées
            if not is_league_allowed(league_id):
                continue

            match = self._parse_fixture(fixture)
            if match:
                matches.append(match)

        # Trier par priorité de ligue
        matches.sort(key=lambda m: get_league_priority(m.league_id))
        logger.info(f"Found {len(matches)} matches in allowed leagues")
        return matches

    def get_tomorrow_fixtures(self) -> List[Match]:
        """Récupère les matchs de demain"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        return self.get_fixtures_by_date(tomorrow)

    def _parse_fixture(self, fixture: Dict) -> Optional[Match]:
        """Parse un fixture de l'API en objet Match"""
        try:
            home_team = Team(
                id=fixture["teams"]["home"]["id"],
                name=fixture["teams"]["home"]["name"],
                logo=fixture["teams"]["home"].get("logo")
            )

            away_team = Team(
                id=fixture["teams"]["away"]["id"],
                name=fixture["teams"]["away"]["name"],
                logo=fixture["teams"]["away"].get("logo")
            )

            match = Match(
                id=fixture["fixture"]["id"],
                league_id=fixture["league"]["id"],
                league_name=fixture["league"]["name"],
                country=fixture["league"]["country"],
                home_team=home_team,
                away_team=away_team,
                date=datetime.fromisoformat(fixture["fixture"]["date"].replace("Z", "+00:00")),
                venue=fixture["fixture"].get("venue", {}).get("name"),
                referee=fixture["fixture"].get("referee")
            )

            return match
        except (KeyError, TypeError) as e:
            logger.error(f"Error parsing fixture: {e}")
            return None

    def get_team_statistics(self, team_id: int, league_id: int, season: int = None) -> Dict:
        """Récupère les statistiques d'une équipe"""
        if season is None:
            season = datetime.now().year if datetime.now().month >= 8 else datetime.now().year - 1

        data = self._make_request("teams/statistics", {
            "team": team_id,
            "league": league_id,
            "season": season
        })

        return data.get("response", {}) if data else {}

    def get_standings(self, league_id: int, season: int = None) -> List[Dict]:
        """Récupère le classement d'une ligue"""
        if season is None:
            season = datetime.now().year if datetime.now().month >= 8 else datetime.now().year - 1

        data = self._make_request("standings", {
            "league": league_id,
            "season": season
        })

        if data and "response" in data and data["response"]:
            standings = data["response"][0].get("league", {}).get("standings", [])
            return standings[0] if standings else []
        return []

    def get_head_to_head(self, team1_id: int, team2_id: int, last: int = 10) -> Dict:
        """Récupère l'historique des confrontations"""
        # Note: Le plan gratuit ne supporte pas le paramètre 'last'
        data = self._make_request("fixtures/headtohead", {
            "h2h": f"{team1_id}-{team2_id}"
        })

        if not data or "response" not in data:
            return {"matches": [], "home_wins": 0, "draws": 0, "away_wins": 0, "avg_goals": 0}

        matches = data["response"]
        home_wins = 0
        away_wins = 0
        draws = 0
        total_goals = 0

        for m in matches:
            home_goals = m["goals"]["home"] or 0
            away_goals = m["goals"]["away"] or 0
            total_goals += home_goals + away_goals

            if m["teams"]["home"]["id"] == team1_id:
                if home_goals > away_goals:
                    home_wins += 1
                elif away_goals > home_goals:
                    away_wins += 1
                else:
                    draws += 1
            else:
                if away_goals > home_goals:
                    home_wins += 1
                elif home_goals > away_goals:
                    away_wins += 1
                else:
                    draws += 1

        return {
            "matches": matches,
            "home_wins": home_wins,
            "draws": draws,
            "away_wins": away_wins,
            "total_games": len(matches),
            "avg_goals": total_goals / len(matches) if matches else 0
        }

    def get_team_form(self, team_id: int, last: int = 5) -> Dict:
        """Récupère la forme récente d'une équipe"""
        # Note: Le plan gratuit ne supporte pas le paramètre 'last', on utilise season
        from datetime import datetime
        season = datetime.now().year if datetime.now().month >= 8 else datetime.now().year - 1
        data = self._make_request("fixtures", {
            "team": team_id,
            "season": season,
            "status": "FT"  # Finished
        })

        if not data or "response" not in data:
            return {"form": "", "goals_scored": 0, "goals_conceded": 0, "wins": 0, "draws": 0, "losses": 0}

        matches = data["response"]
        form = ""
        goals_scored = 0
        goals_conceded = 0
        wins = 0
        draws = 0
        losses = 0

        for m in matches:
            home_goals = m["goals"]["home"] or 0
            away_goals = m["goals"]["away"] or 0

            is_home = m["teams"]["home"]["id"] == team_id
            team_goals = home_goals if is_home else away_goals
            opponent_goals = away_goals if is_home else home_goals

            goals_scored += team_goals
            goals_conceded += opponent_goals

            if team_goals > opponent_goals:
                form += "W"
                wins += 1
            elif team_goals < opponent_goals:
                form += "L"
                losses += 1
            else:
                form += "D"
                draws += 1

        return {
            "form": form,
            "goals_scored": goals_scored,
            "goals_conceded": goals_conceded,
            "wins": wins,
            "draws": draws,
            "losses": losses
        }

    def get_predictions(self, fixture_id: int) -> Dict:
        """Récupère les prédictions de l'API pour un match"""
        data = self._make_request("predictions", {"fixture": fixture_id})

        if not data or "response" not in data or not data["response"]:
            return {}

        return data["response"][0]

    def enrich_match_data(self, match: Match) -> Match:
        """Enrichit un match avec toutes les données nécessaires à l'analyse"""
        logger.info(f"Enriching data for {match}")

        # H2H
        h2h = self.get_head_to_head(match.home_team.id, match.away_team.id)
        match.h2h_home_wins = h2h["home_wins"]
        match.h2h_draws = h2h["draws"]
        match.h2h_away_wins = h2h["away_wins"]
        match.h2h_total_games = h2h["total_games"]
        match.h2h_avg_goals = h2h["avg_goals"]

        # Forme des équipes
        home_form = self.get_team_form(match.home_team.id)
        match.home_team.form = home_form["form"]
        match.home_team.goals_scored_last_5 = home_form["goals_scored"]
        match.home_team.goals_conceded_last_5 = home_form["goals_conceded"]
        match.home_team.wins_last_5 = home_form["wins"]
        match.home_team.draws_last_5 = home_form["draws"]
        match.home_team.losses_last_5 = home_form["losses"]

        away_form = self.get_team_form(match.away_team.id)
        match.away_team.form = away_form["form"]
        match.away_team.goals_scored_last_5 = away_form["goals_scored"]
        match.away_team.goals_conceded_last_5 = away_form["goals_conceded"]
        match.away_team.wins_last_5 = away_form["wins"]
        match.away_team.draws_last_5 = away_form["draws"]
        match.away_team.losses_last_5 = away_form["losses"]

        # Classement
        standings = self.get_standings(match.league_id)
        for team_standing in standings:
            if team_standing["team"]["id"] == match.home_team.id:
                match.home_team.league_position = team_standing["rank"]
                match.home_team.league_points = team_standing["points"]
            elif team_standing["team"]["id"] == match.away_team.id:
                match.away_team.league_position = team_standing["rank"]
                match.away_team.league_points = team_standing["points"]

        return match

    def check_api_status(self) -> Dict:
        """Vérifie le statut de l'API et les quotas"""
        data = self._make_request("status")
        if data and "response" in data:
            return data["response"]
        return {}
