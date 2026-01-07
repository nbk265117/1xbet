import httpx
import os
from datetime import datetime, date
from typing import List, Optional
import json
from pathlib import Path

from models.match import Match, Team, HeadToHead, Player, Coach, MatchAnalysis


class MatchFetcher:
    """Service pour récupérer les matchs depuis API-Football"""

    def __init__(self):
        self.api_key = os.getenv("FOOTBALL_API_KEY", "")
        self.api_host = os.getenv("FOOTBALL_API_HOST", "v3.football.api-sports.io")
        self.base_url = f"https://{self.api_host}"
        self.cache_dir = Path(__file__).parent.parent / "data" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Ligues principales à suivre
        self.top_leagues = {
            39: "Premier League",
            140: "La Liga",
            135: "Serie A",
            78: "Bundesliga",
            61: "Ligue 1",
            2: "Champions League",
            3: "Europa League",
            848: "Conference League",
        }

    def _get_headers(self) -> dict:
        # Support both RapidAPI and direct API-Sports endpoints
        if "rapidapi" in self.api_host:
            return {
                "x-rapidapi-host": self.api_host,
                "x-rapidapi-key": self.api_key,
            }
        else:
            # Direct API-Sports endpoint
            return {
                "x-apisports-key": self.api_key,
            }

    def _get_cache_path(self, cache_key: str) -> Path:
        return self.cache_dir / f"{cache_key}.json"

    def _get_from_cache(self, cache_key: str, max_age_hours: int = 1) -> Optional[dict]:
        cache_path = self._get_cache_path(cache_key)
        if cache_path.exists():
            cache_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
            age_hours = (datetime.now() - cache_time).total_seconds() / 3600
            if age_hours < max_age_hours:
                with open(cache_path, "r") as f:
                    return json.load(f)
        return None

    def _save_to_cache(self, cache_key: str, data: dict):
        cache_path = self._get_cache_path(cache_key)
        with open(cache_path, "w") as f:
            json.dump(data, f)

    async def fetch_matches_by_date(self, match_date: date) -> List[Match]:
        """Récupère tous les matchs pour une date donnée"""
        date_str = match_date.strftime("%Y-%m-%d")
        cache_key = f"matches_{date_str}"

        # Vérifier le cache
        cached = self._get_from_cache(cache_key)
        if cached:
            return self._parse_matches(cached)

        matches = []

        async with httpx.AsyncClient() as client:
            for league_id in self.top_leagues.keys():
                try:
                    response = await client.get(
                        f"{self.base_url}/fixtures",
                        headers=self._get_headers(),
                        params={
                            "date": date_str,
                            "league": league_id,
                            "season": match_date.year if match_date.month > 7 else match_date.year - 1,
                        },
                        timeout=30.0,
                    )

                    if response.status_code == 200:
                        data = response.json()
                        if data.get("response"):
                            matches.extend(data["response"])
                except Exception as e:
                    print(f"Erreur lors de la récupération de la ligue {league_id}: {e}")

        # Sauvegarder en cache
        if matches:
            self._save_to_cache(cache_key, matches)

        return self._parse_matches(matches)

    def _parse_matches(self, raw_matches: List[dict]) -> List[Match]:
        """Parse les données brutes en objets Match"""
        matches = []

        for raw in raw_matches:
            try:
                fixture = raw.get("fixture", {})
                league = raw.get("league", {})
                teams = raw.get("teams", {})

                home_team = Team(
                    id=teams.get("home", {}).get("id", 0),
                    name=teams.get("home", {}).get("name", "Unknown"),
                    logo=teams.get("home", {}).get("logo"),
                )

                away_team = Team(
                    id=teams.get("away", {}).get("id", 0),
                    name=teams.get("away", {}).get("name", "Unknown"),
                    logo=teams.get("away", {}).get("logo"),
                )

                match = Match(
                    id=fixture.get("id", 0),
                    league_id=league.get("id", 0),
                    league_name=league.get("name", "Unknown"),
                    league_country=league.get("country", "Unknown"),
                    date=datetime.fromisoformat(fixture.get("date", datetime.now().isoformat()).replace("Z", "+00:00")),
                    home_team=home_team,
                    away_team=away_team,
                    venue=fixture.get("venue", {}).get("name"),
                    referee=fixture.get("referee"),
                    status=fixture.get("status", {}).get("short", "NS"),
                )
                matches.append(match)
            except Exception as e:
                print(f"Erreur parsing match: {e}")
                continue

        return matches

    async def fetch_head_to_head(self, team1_id: int, team2_id: int) -> HeadToHead:
        """Récupère l'historique des confrontations entre deux équipes"""
        cache_key = f"h2h_{min(team1_id, team2_id)}_{max(team1_id, team2_id)}"

        cached = self._get_from_cache(cache_key, max_age_hours=24)
        if cached:
            return HeadToHead(**cached)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/fixtures/headtohead",
                    headers=self._get_headers(),
                    params={"h2h": f"{team1_id}-{team2_id}", "last": 10},
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    h2h = self._parse_head_to_head(data.get("response", []), team1_id)
                    self._save_to_cache(cache_key, h2h.model_dump())
                    return h2h
            except Exception as e:
                print(f"Erreur H2H: {e}")

        return HeadToHead()

    def _parse_head_to_head(self, matches: List[dict], home_team_id: int) -> HeadToHead:
        """Parse les données H2H"""
        h2h = HeadToHead(total_matches=len(matches))

        for match in matches:
            teams = match.get("teams", {})
            goals = match.get("goals", {})

            home_goals = goals.get("home", 0) or 0
            away_goals = goals.get("away", 0) or 0

            home_id = teams.get("home", {}).get("id")

            if home_id == home_team_id:
                h2h.home_goals += home_goals
                h2h.away_goals += away_goals
                if home_goals > away_goals:
                    h2h.home_wins += 1
                elif away_goals > home_goals:
                    h2h.away_wins += 1
                else:
                    h2h.draws += 1
            else:
                h2h.home_goals += away_goals
                h2h.away_goals += home_goals
                if away_goals > home_goals:
                    h2h.home_wins += 1
                elif home_goals > away_goals:
                    h2h.away_wins += 1
                else:
                    h2h.draws += 1

        return h2h

    async def fetch_team_form(self, team_id: int, last_n: int = 5) -> List[str]:
        """Récupère les derniers résultats d'une équipe"""
        cache_key = f"form_{team_id}"

        cached = self._get_from_cache(cache_key, max_age_hours=6)
        if cached:
            return cached.get("form", [])

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/fixtures",
                    headers=self._get_headers(),
                    params={"team": team_id, "last": last_n, "status": "FT"},
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    form = self._parse_form(data.get("response", []), team_id)
                    self._save_to_cache(cache_key, {"form": form})
                    return form
            except Exception as e:
                print(f"Erreur form: {e}")

        return []

    def _parse_form(self, matches: List[dict], team_id: int) -> List[str]:
        """Parse la forme récente"""
        form = []

        for match in matches:
            teams = match.get("teams", {})
            goals = match.get("goals", {})

            home_goals = goals.get("home", 0) or 0
            away_goals = goals.get("away", 0) or 0

            is_home = teams.get("home", {}).get("id") == team_id

            if is_home:
                if home_goals > away_goals:
                    form.append("W")
                elif away_goals > home_goals:
                    form.append("L")
                else:
                    form.append("D")
            else:
                if away_goals > home_goals:
                    form.append("W")
                elif home_goals > away_goals:
                    form.append("L")
                else:
                    form.append("D")

        return form

    async def fetch_injuries(self, team_id: int) -> List[Player]:
        """Récupère les joueurs blessés/suspendus"""
        cache_key = f"injuries_{team_id}"

        cached = self._get_from_cache(cache_key, max_age_hours=12)
        if cached:
            return [Player(**p) for p in cached]

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/injuries",
                    headers=self._get_headers(),
                    params={"team": team_id, "season": datetime.now().year},
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    injuries = self._parse_injuries(data.get("response", []))
                    self._save_to_cache(cache_key, [i.model_dump() for i in injuries])
                    return injuries
            except Exception as e:
                print(f"Erreur injuries: {e}")

        return []

    def _parse_injuries(self, raw_injuries: List[dict]) -> List[Player]:
        """Parse les blessures"""
        injuries = []

        for raw in raw_injuries:
            player = raw.get("player", {})
            reason = raw.get("player", {}).get("reason", "")

            injuries.append(Player(
                id=player.get("id", 0),
                name=player.get("name", "Unknown"),
                position=player.get("type", "Unknown"),
                is_injured="injury" in reason.lower() if reason else True,
                is_suspended="suspend" in reason.lower() or "card" in reason.lower() if reason else False,
            ))

        return injuries

    async def fetch_match_analysis(self, match: Match) -> MatchAnalysis:
        """Récupère toutes les données pour analyser un match"""
        h2h = await self.fetch_head_to_head(match.home_team.id, match.away_team.id)
        home_form = await self.fetch_team_form(match.home_team.id)
        away_form = await self.fetch_team_form(match.away_team.id)
        home_injuries = await self.fetch_injuries(match.home_team.id)
        away_injuries = await self.fetch_injuries(match.away_team.id)

        return MatchAnalysis(
            match=match,
            head_to_head=h2h,
            home_team_form=home_form,
            away_team_form=away_form,
            home_injuries=home_injuries,
            away_injuries=away_injuries,
        )
