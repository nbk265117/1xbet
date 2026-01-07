"""
Service d'enrichissement des données DYNAMIQUE depuis API-Football
Toutes les données sont récupérées en temps réel avec cache intelligent
"""
import requests
import logging
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import time

logger = logging.getLogger(__name__)

# Configuration API - Import from settings
from config.settings import FOOTBALL_API_KEY, FOOTBALL_API_BASE_URL

# Cache file path
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "api_cache.json")


@dataclass
class TeamStats:
    """Statistiques enrichies d'une équipe"""
    name: str
    team_id: int = 0
    form: str = ""  # Ex: "WWDLW"
    form_score: float = 0.0
    league_position: int = 0
    league_points: int = 0
    goals_scored: int = 0
    goals_conceded: int = 0
    clean_sheets: int = 0
    failed_to_score: int = 0
    avg_goals_scored: float = 0.0
    avg_goals_conceded: float = 0.0
    home_form: str = ""
    away_form: str = ""
    home_wins: int = 0
    home_draws: int = 0
    home_losses: int = 0
    away_wins: int = 0
    away_draws: int = 0
    away_losses: int = 0
    injuries: List[str] = None
    suspensions: List[str] = None
    key_players: List[str] = None
    coach: str = ""
    motivation: str = "normal"
    style: str = "balanced"
    avg_corners: float = 5.0

    def __post_init__(self):
        if self.injuries is None:
            self.injuries = []
        if self.suspensions is None:
            self.suspensions = []
        if self.key_players is None:
            self.key_players = []


@dataclass
class MatchEnrichedData:
    """Données enrichies pour un match"""
    home_stats: TeamStats
    away_stats: TeamStats
    h2h_matches: int = 0
    h2h_home_wins: int = 0
    h2h_draws: int = 0
    h2h_away_wins: int = 0
    h2h_avg_goals: float = 0.0
    h2h_btts_percentage: float = 0.0
    h2h_over25_percentage: float = 0.0
    weather: str = ""
    referee: str = ""
    referee_avg_cards: float = 0.0
    referee_avg_fouls: float = 0.0
    venue: str = ""
    importance: str = "normal"
    news: List[str] = None
    odds_home: float = 0.0
    odds_draw: float = 0.0
    odds_away: float = 0.0

    def __post_init__(self):
        if self.news is None:
            self.news = []


class DynamicDataEnricher:
    """Service d'enrichissement 100% dynamique via API-Football"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'x-apisports-key': FOOTBALL_API_KEY,
            'User-Agent': 'Mozilla/5.0'
        })
        self.cache = self._load_cache()
        self.cache_ttl = {
            'standings': 3600 * 6,   # 6 heures
            'team_stats': 3600 * 12,  # 12 heures
            'h2h': 3600 * 24,         # 24 heures
            'form': 3600 * 6,         # 6 heures
            'injuries': 3600 * 3,     # 3 heures
        }
        self.api_calls_count = 0
        self.max_api_calls = 500  # Limite par session (Pro plan = 7500/jour)

        # Créer le dossier cache si nécessaire
        os.makedirs(CACHE_DIR, exist_ok=True)

    def _load_cache(self) -> Dict:
        """Charge le cache depuis le fichier"""
        try:
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Erreur chargement cache: {e}")
        return {}

    def _save_cache(self):
        """Sauvegarde le cache dans le fichier"""
        try:
            with open(CACHE_FILE, 'w') as f:
                json.dump(self.cache, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Erreur sauvegarde cache: {e}")

    def _is_cache_valid(self, cache_key: str, cache_type: str) -> bool:
        """Vérifie si une entrée de cache est encore valide"""
        if cache_key not in self.cache:
            return False

        entry = self.cache[cache_key]
        if 'timestamp' not in entry:
            return False

        ttl = self.cache_ttl.get(cache_type, 3600)
        age = time.time() - entry['timestamp']
        return age < ttl

    def _api_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Effectue une requête à l'API-Football avec gestion des limites et rate limiting"""
        if self.api_calls_count >= self.max_api_calls:
            logger.warning("Limite d'appels API atteinte pour cette session")
            return None

        try:
            url = f"{FOOTBALL_API_BASE_URL}/{endpoint}"
            response = self.session.get(url, params=params, timeout=15)
            self.api_calls_count += 1

            if response.status_code == 200:
                data = response.json()
                if data.get('errors'):
                    # Check for rate limit error
                    if 'rateLimit' in str(data.get('errors', {})):
                        logger.warning("Rate limit hit, waiting 1 second...")
                        time.sleep(1)
                        return self._api_request(endpoint, params)  # Retry
                    logger.warning(f"API Error: {data['errors']}")
                    return None
                return data.get('response', [])
            elif response.status_code == 429:
                # Rate limit - wait and retry
                logger.warning("Rate limit 429, waiting 2 seconds...")
                time.sleep(2)
                return self._api_request(endpoint, params)
            else:
                logger.warning(f"API HTTP {response.status_code}: {endpoint}")
                return None

        except Exception as e:
            logger.error(f"Erreur API {endpoint}: {e}")
            return None

    def enrich_match(self, home_team: str, away_team: str, league: str,
                     league_id: int = None, home_team_id: int = None,
                     away_team_id: int = None, match_date: datetime = None) -> MatchEnrichedData:
        """
        Enrichit un match avec données DYNAMIQUES depuis l'API
        """
        logger.info(f"[DYNAMIC] Enriching: {home_team} vs {away_team}")

        # Récupérer les stats dynamiques de chaque équipe
        home_stats = self._get_team_stats_dynamic(home_team, league_id, home_team_id)
        away_stats = self._get_team_stats_dynamic(away_team, league_id, away_team_id)

        # H2H dynamique
        h2h_data = self._get_h2h_dynamic(home_team_id, away_team_id, home_team, away_team)

        # Blessures dynamiques
        if home_team_id:
            home_stats.injuries = self._get_injuries_dynamic(home_team_id)
        if away_team_id:
            away_stats.injuries = self._get_injuries_dynamic(away_team_id)

        # News contextuelles
        news = self._generate_context_news(home_stats, away_stats)

        # Sauvegarder le cache
        self._save_cache()

        return MatchEnrichedData(
            home_stats=home_stats,
            away_stats=away_stats,
            h2h_matches=h2h_data.get('total', 0),
            h2h_home_wins=h2h_data.get('home_wins', 0),
            h2h_draws=h2h_data.get('draws', 0),
            h2h_away_wins=h2h_data.get('away_wins', 0),
            h2h_avg_goals=h2h_data.get('avg_goals', 2.5),
            h2h_btts_percentage=h2h_data.get('btts_pct', 50),
            h2h_over25_percentage=h2h_data.get('over25_pct', 50),
            news=news
        )

    def _get_team_stats_dynamic(self, team_name: str, league_id: int = None,
                                 team_id: int = None) -> TeamStats:
        """Récupère les stats d'une équipe DYNAMIQUEMENT depuis l'API"""
        stats = TeamStats(name=team_name, team_id=team_id or 0)

        if not team_id or not league_id:
            logger.debug(f"IDs manquants pour {team_name}, utilisation valeurs par défaut")
            return stats

        # 1. Récupérer le classement (inclut forme, points, position)
        standings_data = self._get_standings_dynamic(league_id, team_id)
        if standings_data:
            stats.league_position = standings_data.get('rank', 0)
            stats.league_points = standings_data.get('points', 0)
            stats.form = standings_data.get('form', '')
            stats.goals_scored = standings_data.get('goals_for', 0)
            stats.goals_conceded = standings_data.get('goals_against', 0)
            stats.home_wins = standings_data.get('home_wins', 0)
            stats.home_draws = standings_data.get('home_draws', 0)
            stats.home_losses = standings_data.get('home_losses', 0)
            stats.away_wins = standings_data.get('away_wins', 0)
            stats.away_draws = standings_data.get('away_draws', 0)
            stats.away_losses = standings_data.get('away_losses', 0)

        # 2. Récupérer les statistiques détaillées de l'équipe
        team_stats_data = self._get_team_statistics_dynamic(team_id, league_id)
        if team_stats_data:
            stats.clean_sheets = team_stats_data.get('clean_sheets', 0)
            stats.failed_to_score = team_stats_data.get('failed_to_score', 0)
            stats.avg_goals_scored = team_stats_data.get('avg_goals_scored', 0.0)
            stats.avg_goals_conceded = team_stats_data.get('avg_goals_conceded', 0.0)
            stats.avg_corners = team_stats_data.get('avg_corners', 5.0)

        # 3. Déterminer la motivation basée sur la position
        stats.motivation = self._determine_motivation(stats.league_position, league_id)

        # 4. Calculer le score de forme
        stats.form_score = self._calculate_form_score(stats.form)

        return stats

    def _get_standings_dynamic(self, league_id: int, team_id: int) -> Optional[Dict]:
        """Récupère le classement dynamique depuis l'API"""
        cache_key = f"standings_{league_id}_{datetime.now().year}"

        # Vérifier le cache
        if self._is_cache_valid(cache_key, 'standings'):
            standings = self.cache[cache_key].get('data', [])
            for team in standings:
                if team.get('team_id') == team_id:
                    return team

        # Appel API
        season = datetime.now().year if datetime.now().month >= 7 else datetime.now().year - 1
        response = self._api_request('standings', {
            'league': league_id,
            'season': season
        })

        if response and len(response) > 0:
            standings_list = []
            league_standings = response[0].get('league', {}).get('standings', [[]])

            for group in league_standings:
                for team_data in group:
                    team_info = team_data.get('team', {})
                    all_stats = team_data.get('all', {})
                    home_stats = team_data.get('home', {})
                    away_stats = team_data.get('away', {})

                    parsed = {
                        'team_id': team_info.get('id'),
                        'team_name': team_info.get('name'),
                        'rank': team_data.get('rank', 0),
                        'points': team_data.get('points', 0),
                        'form': team_data.get('form', ''),
                        'goals_for': all_stats.get('goals', {}).get('for', 0),
                        'goals_against': all_stats.get('goals', {}).get('against', 0),
                        'home_wins': home_stats.get('win', 0),
                        'home_draws': home_stats.get('draw', 0),
                        'home_losses': home_stats.get('lose', 0),
                        'away_wins': away_stats.get('win', 0),
                        'away_draws': away_stats.get('draw', 0),
                        'away_losses': away_stats.get('lose', 0),
                    }
                    standings_list.append(parsed)

            # Sauvegarder en cache
            self.cache[cache_key] = {
                'timestamp': time.time(),
                'data': standings_list
            }

            # Retourner les données de l'équipe demandée
            for team in standings_list:
                if team.get('team_id') == team_id:
                    return team

        return None

    def _get_team_statistics_dynamic(self, team_id: int, league_id: int) -> Optional[Dict]:
        """Récupère les statistiques détaillées d'une équipe"""
        cache_key = f"team_stats_{team_id}_{league_id}"

        # Vérifier le cache
        if self._is_cache_valid(cache_key, 'team_stats'):
            return self.cache[cache_key].get('data')

        # Appel API
        season = datetime.now().year if datetime.now().month >= 7 else datetime.now().year - 1
        response = self._api_request('teams/statistics', {
            'team': team_id,
            'league': league_id,
            'season': season
        })

        if response:
            data = response if isinstance(response, dict) else (response[0] if response else {})

            # Parser les statistiques
            clean_sheets = data.get('clean_sheet', {})
            failed_to_score = data.get('failed_to_score', {})
            goals = data.get('goals', {})

            total_clean = (clean_sheets.get('home', 0) or 0) + (clean_sheets.get('away', 0) or 0)
            total_failed = (failed_to_score.get('home', 0) or 0) + (failed_to_score.get('away', 0) or 0)

            # Moyennes de buts
            goals_for = goals.get('for', {}).get('average', {})
            goals_against = goals.get('against', {}).get('average', {})

            avg_scored = float(goals_for.get('total', '0') or '0')
            avg_conceded = float(goals_against.get('total', '0') or '0')

            parsed = {
                'clean_sheets': total_clean,
                'failed_to_score': total_failed,
                'avg_goals_scored': avg_scored,
                'avg_goals_conceded': avg_conceded,
                'avg_corners': 5.0  # API ne fournit pas les corners par défaut
            }

            # Sauvegarder en cache
            self.cache[cache_key] = {
                'timestamp': time.time(),
                'data': parsed
            }

            return parsed

        return None

    def _get_h2h_dynamic(self, home_team_id: int, away_team_id: int,
                         home_name: str, away_name: str) -> Dict:
        """Récupère l'historique H2H dynamique depuis l'API"""
        if not home_team_id or not away_team_id:
            return self._default_h2h()

        cache_key = f"h2h_{min(home_team_id, away_team_id)}_{max(home_team_id, away_team_id)}"

        # Vérifier le cache
        if self._is_cache_valid(cache_key, 'h2h'):
            return self.cache[cache_key].get('data', self._default_h2h())

        # Appel API
        response = self._api_request('fixtures/headtohead', {
            'h2h': f"{home_team_id}-{away_team_id}",
            'last': 10
        })

        if response and len(response) > 0:
            home_wins = 0
            away_wins = 0
            draws = 0
            total_goals = 0
            btts_count = 0
            over25_count = 0
            total_matches = len(response)

            for match in response:
                goals = match.get('goals', {})
                home_goals = goals.get('home', 0) or 0
                away_goals = goals.get('away', 0) or 0
                total_goals += home_goals + away_goals

                # Déterminer le vainqueur
                teams = match.get('teams', {})
                home_team = teams.get('home', {})
                away_team = teams.get('away', {})

                if home_team.get('id') == home_team_id:
                    if home_team.get('winner') == True:
                        home_wins += 1
                    elif away_team.get('winner') == True:
                        away_wins += 1
                    else:
                        draws += 1
                else:
                    # Inverser si l'équipe "home" dans l'API n'est pas notre home
                    if home_team.get('winner') == True:
                        away_wins += 1
                    elif away_team.get('winner') == True:
                        home_wins += 1
                    else:
                        draws += 1

                # BTTS et Over 2.5
                if home_goals > 0 and away_goals > 0:
                    btts_count += 1
                if home_goals + away_goals > 2.5:
                    over25_count += 1

            h2h_data = {
                'total': total_matches,
                'home_wins': home_wins,
                'draws': draws,
                'away_wins': away_wins,
                'avg_goals': round(total_goals / total_matches, 2) if total_matches > 0 else 2.5,
                'btts_pct': round((btts_count / total_matches) * 100) if total_matches > 0 else 50,
                'over25_pct': round((over25_count / total_matches) * 100) if total_matches > 0 else 50
            }

            # Sauvegarder en cache
            self.cache[cache_key] = {
                'timestamp': time.time(),
                'data': h2h_data
            }

            return h2h_data

        return self._default_h2h()

    def _get_injuries_dynamic(self, team_id: int) -> List[str]:
        """Récupère les blessures/suspensions dynamiques"""
        cache_key = f"injuries_{team_id}"

        # Vérifier le cache
        if self._is_cache_valid(cache_key, 'injuries'):
            return self.cache[cache_key].get('data', [])

        # Appel API
        response = self._api_request('injuries', {
            'team': team_id,
            'season': datetime.now().year if datetime.now().month >= 7 else datetime.now().year - 1
        })

        injuries = []
        if response:
            for injury in response[:5]:  # Limiter à 5 blessures
                player = injury.get('player', {})
                player_name = player.get('name', 'Unknown')
                injury_type = injury.get('player', {}).get('type', 'injury')
                reason = injury.get('player', {}).get('reason', '')
                injuries.append(f"{player_name} ({reason})" if reason else player_name)

        # Sauvegarder en cache
        self.cache[cache_key] = {
            'timestamp': time.time(),
            'data': injuries
        }

        return injuries

    def _determine_motivation(self, position: int, league_id: int) -> str:
        """Détermine la motivation basée sur la position au classement"""
        if position == 0:
            return "normal"

        # Top leagues (20 équipes généralement)
        if position <= 2:
            return "title"
        elif position <= 4:
            return "champions_league"
        elif position <= 6:
            return "europa"
        elif position <= 7:
            return "conference"
        elif position >= 18:
            return "relegation"
        elif position >= 15:
            return "relegation_danger"
        else:
            return "normal"

    def _calculate_form_score(self, form: str) -> float:
        """Calcule un score de forme (0-100) basé sur les 5 derniers matchs"""
        if not form:
            return 50.0

        score = 0
        weights = [1.5, 1.3, 1.1, 0.9, 0.7]  # Plus récent = plus important

        for i, result in enumerate(form[:5]):
            weight = weights[i] if i < len(weights) else 0.5
            if result.upper() == 'W':
                score += 20 * weight
            elif result.upper() == 'D':
                score += 10 * weight
            # L = 0

        return min(100, score)

    def _generate_context_news(self, home_stats: TeamStats, away_stats: TeamStats) -> List[str]:
        """Génère des news contextuelles basées sur les données"""
        news = []

        # Blessures
        if home_stats.injuries:
            news.append(f"🏥 {home_stats.name}: {', '.join(home_stats.injuries[:3])}")
        if away_stats.injuries:
            news.append(f"🏥 {away_stats.name}: {', '.join(away_stats.injuries[:3])}")

        # Motivation
        motivation_messages = {
            'title': "en course pour le titre",
            'champions_league': "vise la Champions League",
            'europa': "vise l'Europa League",
            'relegation': "lutte pour le maintien",
            'relegation_danger': "en danger de relégation"
        }

        if home_stats.motivation in motivation_messages:
            news.append(f"🎯 {home_stats.name} {motivation_messages[home_stats.motivation]}")
        if away_stats.motivation in motivation_messages:
            news.append(f"🎯 {away_stats.name} {motivation_messages[away_stats.motivation]}")

        # Forme exceptionnelle
        if home_stats.form and home_stats.form.count('W') >= 4:
            news.append(f"🔥 {home_stats.name} en grande forme ({home_stats.form})")
        if away_stats.form and away_stats.form.count('W') >= 4:
            news.append(f"🔥 {away_stats.name} en grande forme ({away_stats.form})")

        # Mauvaise forme
        if home_stats.form and home_stats.form.count('L') >= 3:
            news.append(f"📉 {home_stats.name} en difficulté ({home_stats.form})")
        if away_stats.form and away_stats.form.count('L') >= 3:
            news.append(f"📉 {away_stats.name} en difficulté ({away_stats.form})")

        return news

    def _default_h2h(self) -> Dict:
        """Retourne des valeurs H2H par défaut"""
        return {
            'total': 5,
            'home_wins': 2,
            'draws': 1,
            'away_wins': 2,
            'avg_goals': 2.5,
            'btts_pct': 50,
            'over25_pct': 50
        }

    def get_predictions_api(self, fixture_id: int) -> Optional[Dict]:
        """
        [PRO] Récupère les prédictions officielles de l'API-Football
        Inclut: winner, goals over/under, advice, percentages
        """
        cache_key = f"predictions_{fixture_id}"

        if self._is_cache_valid(cache_key, 'team_stats'):
            return self.cache[cache_key].get('data')

        response = self._api_request('predictions', {'fixture': fixture_id})

        if response and len(response) > 0:
            pred_data = response[0]

            predictions = pred_data.get('predictions', {})
            teams = pred_data.get('teams', {})
            comparison = pred_data.get('comparison', {})

            parsed = {
                'winner_id': predictions.get('winner', {}).get('id'),
                'winner_name': predictions.get('winner', {}).get('name'),
                'winner_comment': predictions.get('winner', {}).get('comment'),
                'win_or_draw': predictions.get('win_or_draw', False),
                'under_over': predictions.get('under_over'),
                'goals_home': predictions.get('goals', {}).get('home'),
                'goals_away': predictions.get('goals', {}).get('away'),
                'advice': predictions.get('advice'),
                'percent_home': predictions.get('percent', {}).get('home', '0%'),
                'percent_draw': predictions.get('percent', {}).get('draw', '0%'),
                'percent_away': predictions.get('percent', {}).get('away', '0%'),
                # Comparaison détaillée
                'comp_form_home': comparison.get('form', {}).get('home', '0%'),
                'comp_form_away': comparison.get('form', {}).get('away', '0%'),
                'comp_att_home': comparison.get('att', {}).get('home', '0%'),
                'comp_att_away': comparison.get('att', {}).get('away', '0%'),
                'comp_def_home': comparison.get('def', {}).get('home', '0%'),
                'comp_def_away': comparison.get('def', {}).get('away', '0%'),
                'comp_h2h_home': comparison.get('h2h', {}).get('home', '0%'),
                'comp_h2h_away': comparison.get('h2h', {}).get('away', '0%'),
                'comp_goals_home': comparison.get('goals', {}).get('home', '0%'),
                'comp_goals_away': comparison.get('goals', {}).get('away', '0%'),
                'comp_total_home': comparison.get('total', {}).get('home', '0%'),
                'comp_total_away': comparison.get('total', {}).get('away', '0%'),
                # Stats des équipes
                'home_last_5_form': teams.get('home', {}).get('last_5', {}).get('form'),
                'home_last_5_att': teams.get('home', {}).get('last_5', {}).get('att'),
                'home_last_5_def': teams.get('home', {}).get('last_5', {}).get('def'),
                'home_last_5_goals_for': teams.get('home', {}).get('last_5', {}).get('goals', {}).get('for', {}).get('total'),
                'home_last_5_goals_against': teams.get('home', {}).get('last_5', {}).get('goals', {}).get('against', {}).get('total'),
                'away_last_5_form': teams.get('away', {}).get('last_5', {}).get('form'),
                'away_last_5_att': teams.get('away', {}).get('last_5', {}).get('att'),
                'away_last_5_def': teams.get('away', {}).get('last_5', {}).get('def'),
                'away_last_5_goals_for': teams.get('away', {}).get('last_5', {}).get('goals', {}).get('for', {}).get('total'),
                'away_last_5_goals_against': teams.get('away', {}).get('last_5', {}).get('goals', {}).get('against', {}).get('total'),
            }

            self.cache[cache_key] = {
                'timestamp': time.time(),
                'data': parsed
            }

            return parsed

        return None

    def get_odds_api(self, fixture_id: int) -> Optional[Dict]:
        """
        [PRO] Récupère les cotes des bookmakers pour un match
        """
        cache_key = f"odds_{fixture_id}"

        if self._is_cache_valid(cache_key, 'team_stats'):
            return self.cache[cache_key].get('data')

        response = self._api_request('odds', {
            'fixture': fixture_id,
            'bookmaker': 8  # Bet365 comme référence
        })

        odds_data = {
            'match_winner': {'home': 0, 'draw': 0, 'away': 0},
            'over_under_25': {'over': 0, 'under': 0},
            'over_under_15': {'over': 0, 'under': 0},
            'btts': {'yes': 0, 'no': 0},
            'double_chance': {'1X': 0, 'X2': 0, '12': 0},
        }

        if response and len(response) > 0:
            bookmakers = response[0].get('bookmakers', [])
            for bookmaker in bookmakers:
                bets = bookmaker.get('bets', [])
                for bet in bets:
                    bet_name = bet.get('name', '')
                    values = bet.get('values', [])

                    if bet_name == 'Match Winner':
                        for v in values:
                            if v['value'] == 'Home':
                                odds_data['match_winner']['home'] = float(v['odd'])
                            elif v['value'] == 'Draw':
                                odds_data['match_winner']['draw'] = float(v['odd'])
                            elif v['value'] == 'Away':
                                odds_data['match_winner']['away'] = float(v['odd'])

                    elif bet_name == 'Goals Over/Under' and '2.5' in str(values):
                        for v in values:
                            if 'Over 2.5' in v['value']:
                                odds_data['over_under_25']['over'] = float(v['odd'])
                            elif 'Under 2.5' in v['value']:
                                odds_data['over_under_25']['under'] = float(v['odd'])

                    elif bet_name == 'Both Teams Score':
                        for v in values:
                            if v['value'] == 'Yes':
                                odds_data['btts']['yes'] = float(v['odd'])
                            elif v['value'] == 'No':
                                odds_data['btts']['no'] = float(v['odd'])

                    elif bet_name == 'Double Chance':
                        for v in values:
                            if v['value'] == 'Home/Draw':
                                odds_data['double_chance']['1X'] = float(v['odd'])
                            elif v['value'] == 'Draw/Away':
                                odds_data['double_chance']['X2'] = float(v['odd'])
                            elif v['value'] == 'Home/Away':
                                odds_data['double_chance']['12'] = float(v['odd'])

            self.cache[cache_key] = {
                'timestamp': time.time(),
                'data': odds_data
            }

        return odds_data

    def get_fixture_statistics(self, fixture_id: int) -> Optional[Dict]:
        """
        [PRO] Récupère les statistiques détaillées d'un match passé
        Utile pour analyser les tendances des équipes
        """
        cache_key = f"fixture_stats_{fixture_id}"

        if self._is_cache_valid(cache_key, 'team_stats'):
            return self.cache[cache_key].get('data')

        response = self._api_request('fixtures/statistics', {'fixture': fixture_id})

        if response and len(response) >= 2:
            stats = {'home': {}, 'away': {}}

            for team_stats in response:
                team_type = 'home' if response.index(team_stats) == 0 else 'away'
                statistics = team_stats.get('statistics', [])

                for stat in statistics:
                    stat_type = stat.get('type', '')
                    value = stat.get('value')

                    # Convertir en nombre si possible
                    if value is not None:
                        if isinstance(value, str) and '%' in value:
                            value = float(value.replace('%', ''))
                        elif isinstance(value, str) and value.isdigit():
                            value = int(value)

                    stats[team_type][stat_type] = value

            self.cache[cache_key] = {
                'timestamp': time.time(),
                'data': stats
            }

            return stats

        return None

    def get_team_last_fixtures_stats(self, team_id: int, league_id: int, last: int = 5) -> Optional[Dict]:
        """
        [PRO] Récupère les stats agrégées des derniers matchs d'une équipe
        Corners, tirs, possession, etc.
        """
        cache_key = f"team_fixtures_stats_{team_id}_{league_id}_{last}"

        if self._is_cache_valid(cache_key, 'team_stats'):
            return self.cache[cache_key].get('data')

        # Récupérer les derniers matchs terminés
        season = datetime.now().year if datetime.now().month >= 7 else datetime.now().year - 1
        response = self._api_request('fixtures', {
            'team': team_id,
            'league': league_id,
            'season': season,
            'last': last,
            'status': 'FT'
        })

        if not response:
            return None

        # Agréger les stats
        aggregated = {
            'matches': 0,
            'total_corners': 0,
            'total_shots': 0,
            'total_shots_on_target': 0,
            'total_possession': 0,
            'total_fouls': 0,
            'total_cards': 0,
            'avg_corners': 0,
            'avg_shots': 0,
            'avg_possession': 0,
            'xg_for': 0,
            'xg_against': 0,
        }

        for fixture in response:
            fixture_id = fixture.get('fixture', {}).get('id')
            stats = self.get_fixture_statistics(fixture_id)

            if stats:
                # Déterminer si l'équipe était à domicile ou à l'extérieur
                is_home = fixture.get('teams', {}).get('home', {}).get('id') == team_id
                team_stats = stats.get('home' if is_home else 'away', {})

                aggregated['matches'] += 1
                aggregated['total_corners'] += team_stats.get('Corner Kicks', 0) or 0
                aggregated['total_shots'] += team_stats.get('Total Shots', 0) or 0
                aggregated['total_shots_on_target'] += team_stats.get('Shots on Goal', 0) or 0

                possession = team_stats.get('Ball Possession', 0)
                if isinstance(possession, (int, float)):
                    aggregated['total_possession'] += possession

                aggregated['total_fouls'] += team_stats.get('Fouls', 0) or 0

                yellow = team_stats.get('Yellow Cards', 0) or 0
                red = team_stats.get('Red Cards', 0) or 0
                aggregated['total_cards'] += yellow + red

                xg = team_stats.get('expected_goals', 0)
                if xg:
                    aggregated['xg_for'] += float(xg)

        # Calculer les moyennes
        if aggregated['matches'] > 0:
            n = aggregated['matches']
            aggregated['avg_corners'] = round(aggregated['total_corners'] / n, 2)
            aggregated['avg_shots'] = round(aggregated['total_shots'] / n, 2)
            aggregated['avg_possession'] = round(aggregated['total_possession'] / n, 1)
            aggregated['avg_shots_on_target'] = round(aggregated['total_shots_on_target'] / n, 2)
            aggregated['avg_fouls'] = round(aggregated['total_fouls'] / n, 2)
            aggregated['avg_cards'] = round(aggregated['total_cards'] / n, 2)
            aggregated['avg_xg'] = round(aggregated['xg_for'] / n, 2)

        self.cache[cache_key] = {
            'timestamp': time.time(),
            'data': aggregated
        }

        return aggregated

    def get_halftime_odds_api(self, fixture_id: int) -> Optional[Dict]:
        """
        [PRO] Récupère les cotes mi-temps pour un match
        Inclut: 1X2 MT, Over/Under MT, BTTS MT
        """
        cache_key = f"odds_ht_{fixture_id}"

        if self._is_cache_valid(cache_key, 'team_stats'):
            return self.cache[cache_key].get('data')

        response = self._api_request('odds', {
            'fixture': fixture_id,
            'bookmaker': 8  # Bet365
        })

        ht_odds = {
            'ht_1x2': {'home': 0, 'draw': 0, 'away': 0},
            'ht_over_under_05': {'over': 0, 'under': 0},
            'ht_over_under_15': {'over': 0, 'under': 0},
            'ht_ft': {},  # HT/FT combinations
        }

        if response and len(response) > 0:
            bookmakers = response[0].get('bookmakers', [])
            for bookmaker in bookmakers:
                bets = bookmaker.get('bets', [])
                for bet in bets:
                    bet_name = bet.get('name', '')
                    values = bet.get('values', [])

                    # 1X2 Mi-temps
                    if 'First Half' in bet_name and 'Winner' in bet_name:
                        for v in values:
                            if v['value'] == 'Home':
                                ht_odds['ht_1x2']['home'] = float(v['odd'])
                            elif v['value'] == 'Draw':
                                ht_odds['ht_1x2']['draw'] = float(v['odd'])
                            elif v['value'] == 'Away':
                                ht_odds['ht_1x2']['away'] = float(v['odd'])

                    # Over/Under 0.5 MT
                    elif 'First Half' in bet_name and '0.5' in bet_name:
                        for v in values:
                            if 'Over' in v['value']:
                                ht_odds['ht_over_under_05']['over'] = float(v['odd'])
                            elif 'Under' in v['value']:
                                ht_odds['ht_over_under_05']['under'] = float(v['odd'])

                    # Over/Under 1.5 MT
                    elif 'First Half' in bet_name and '1.5' in bet_name:
                        for v in values:
                            if 'Over' in v['value']:
                                ht_odds['ht_over_under_15']['over'] = float(v['odd'])
                            elif 'Under' in v['value']:
                                ht_odds['ht_over_under_15']['under'] = float(v['odd'])

                    # HT/FT
                    elif bet_name == 'HT/FT Double':
                        for v in values:
                            ht_odds['ht_ft'][v['value']] = float(v['odd'])

            self.cache[cache_key] = {
                'timestamp': time.time(),
                'data': ht_odds
            }

        return ht_odds

    def get_cards_stats_api(self, team_id: int, league_id: int) -> Optional[Dict]:
        """
        [PRO] Récupère les statistiques de cartons d'une équipe
        Analyse des 10 derniers matchs pour les cartons jaunes/rouges
        """
        cache_key = f"cards_stats_{team_id}_{league_id}"

        if self._is_cache_valid(cache_key, 'team_stats'):
            return self.cache[cache_key].get('data')

        # Récupérer les derniers matchs avec les événements
        season = datetime.now().year if datetime.now().month >= 7 else datetime.now().year - 1
        response = self._api_request('fixtures', {
            'team': team_id,
            'league': league_id,
            'season': season,
            'last': 10,
            'status': 'FT'
        })

        if not response:
            return None

        cards_data = {
            'total_yellow': 0,
            'total_red': 0,
            'matches_analyzed': 0,
            'avg_yellow_per_match': 0.0,
            'avg_red_per_match': 0.0,
            'avg_total_cards': 0.0,
            'matches_with_red': 0,
            'yellow_first_half': 0,
            'yellow_second_half': 0,
        }

        for fixture in response:
            fixture_id = fixture.get('fixture', {}).get('id')

            # Récupérer les événements du match
            events_response = self._api_request('fixtures/events', {'fixture': fixture_id})

            if events_response:
                cards_data['matches_analyzed'] += 1
                match_yellows = 0
                match_reds = 0

                for event in events_response:
                    event_type = event.get('type', '')
                    event_detail = event.get('detail', '')
                    event_time = event.get('time', {}).get('elapsed', 0) or 0
                    event_team_id = event.get('team', {}).get('id')

                    if event_type == 'Card':
                        # Vérifier si c'est pour notre équipe
                        if event_team_id == team_id:
                            if 'Yellow' in event_detail:
                                match_yellows += 1
                                cards_data['total_yellow'] += 1
                                if event_time <= 45:
                                    cards_data['yellow_first_half'] += 1
                                else:
                                    cards_data['yellow_second_half'] += 1
                            elif 'Red' in event_detail:
                                match_reds += 1
                                cards_data['total_red'] += 1

                if match_reds > 0:
                    cards_data['matches_with_red'] += 1

        # Calculer les moyennes
        if cards_data['matches_analyzed'] > 0:
            n = cards_data['matches_analyzed']
            cards_data['avg_yellow_per_match'] = round(cards_data['total_yellow'] / n, 2)
            cards_data['avg_red_per_match'] = round(cards_data['total_red'] / n, 2)
            cards_data['avg_total_cards'] = round((cards_data['total_yellow'] + cards_data['total_red']) / n, 2)
            cards_data['red_probability'] = round(cards_data['matches_with_red'] / n, 2)

        self.cache[cache_key] = {
            'timestamp': time.time(),
            'data': cards_data
        }

        return cards_data

    def get_referee_stats_api(self, referee_name: str = None, fixture_id: int = None) -> Optional[Dict]:
        """
        [PRO] Récupère les statistiques de l'arbitre
        Cartons moyens, fautes sifflées, etc.
        """
        if not fixture_id:
            return None

        cache_key = f"referee_{fixture_id}"

        if self._is_cache_valid(cache_key, 'team_stats'):
            return self.cache[cache_key].get('data')

        # Récupérer les infos du match pour avoir l'arbitre
        response = self._api_request('fixtures', {'id': fixture_id})

        referee_stats = {
            'name': '',
            'avg_yellow_cards': 4.0,  # Moyenne par défaut
            'avg_red_cards': 0.2,
            'avg_fouls': 25.0,
            'avg_penalties': 0.3,
            'strictness': 'MOYEN',  # FAIBLE, MOYEN, STRICT
        }

        if response and len(response) > 0:
            fixture = response[0]
            referee = fixture.get('fixture', {}).get('referee', '')

            if referee:
                referee_stats['name'] = referee

                # Rechercher les stats historiques de cet arbitre
                # (L'API ne fournit pas directement les stats d'arbitre, on peut estimer)
                # On utilise une estimation basée sur les ligues
                league_id = fixture.get('league', {}).get('id', 0)

                # Ajuster selon la ligue (certaines ligues sont plus strictes)
                strict_leagues = [39, 140, 135]  # Premier League, La Liga, Serie A
                lenient_leagues = [78, 88]  # Bundesliga, Eredivisie

                if league_id in strict_leagues:
                    referee_stats['avg_yellow_cards'] = 4.5
                    referee_stats['strictness'] = 'STRICT'
                elif league_id in lenient_leagues:
                    referee_stats['avg_yellow_cards'] = 3.2
                    referee_stats['strictness'] = 'FAIBLE'

            self.cache[cache_key] = {
                'timestamp': time.time(),
                'data': referee_stats
            }

        return referee_stats

    def get_corners_odds_api(self, fixture_id: int) -> Optional[Dict]:
        """
        [PRO] Récupère les cotes corners pour un match
        """
        cache_key = f"odds_corners_{fixture_id}"

        if self._is_cache_valid(cache_key, 'team_stats'):
            return self.cache[cache_key].get('data')

        response = self._api_request('odds', {
            'fixture': fixture_id,
            'bookmaker': 8  # Bet365
        })

        corners_odds = {
            'over_8_5': 0,
            'under_8_5': 0,
            'over_9_5': 0,
            'under_9_5': 0,
            'over_10_5': 0,
            'under_10_5': 0,
            'home_over_4_5': 0,
            'away_over_3_5': 0,
        }

        if response and len(response) > 0:
            bookmakers = response[0].get('bookmakers', [])
            for bookmaker in bookmakers:
                bets = bookmaker.get('bets', [])
                for bet in bets:
                    bet_name = bet.get('name', '').lower()
                    values = bet.get('values', [])

                    if 'corner' in bet_name:
                        for v in values:
                            val_str = str(v['value']).lower()
                            odd = float(v['odd'])

                            if 'over 8.5' in val_str:
                                corners_odds['over_8_5'] = odd
                            elif 'under 8.5' in val_str:
                                corners_odds['under_8_5'] = odd
                            elif 'over 9.5' in val_str:
                                corners_odds['over_9_5'] = odd
                            elif 'under 9.5' in val_str:
                                corners_odds['under_9_5'] = odd
                            elif 'over 10.5' in val_str:
                                corners_odds['over_10_5'] = odd
                            elif 'under 10.5' in val_str:
                                corners_odds['under_10_5'] = odd

            self.cache[cache_key] = {
                'timestamp': time.time(),
                'data': corners_odds
            }

        return corners_odds

    def get_api_status(self) -> Dict:
        """Retourne le statut de l'API et du cache"""
        response = self._api_request('status')

        cache_stats = {
            'entries': len(self.cache),
            'file_exists': os.path.exists(CACHE_FILE)
        }

        return {
            'api_calls_this_session': self.api_calls_count,
            'max_calls': self.max_api_calls,
            'cache': cache_stats,
            'api_response': response
        }

    def clear_cache(self, cache_type: str = None):
        """Vide le cache (tout ou par type)"""
        if cache_type:
            keys_to_remove = [k for k in self.cache if k.startswith(cache_type)]
            for key in keys_to_remove:
                del self.cache[key]
        else:
            self.cache = {}

        self._save_cache()
        logger.info(f"Cache cleared: {cache_type or 'all'}")


# Instance globale - utiliser DynamicDataEnricher
data_enricher = DynamicDataEnricher()


# Alias pour compatibilité avec l'ancien code
DataEnricher = DynamicDataEnricher
