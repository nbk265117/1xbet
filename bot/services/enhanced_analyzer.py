"""
Analyseur amélioré avec données enrichies multi-sources
Utilise: Flashscore, Sofascore, API-Football, base de données locale
Configuration adaptative par ligue
"""
import logging
import math
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from models.match import Match, Prediction, BetType, Team
from config.settings import CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, CONFIDENCE_LOW
from config.league_config import get_league_config, DEFAULT_CONFIG, is_high_scoring_league, is_physical_league
from services.data_enricher import DataEnricher, MatchEnrichedData, TeamStats

logger = logging.getLogger(__name__)


@dataclass
class EnhancedPrediction:
    """Prédiction enrichie avec tous les types de paris PRO"""
    match_name: str
    league: str
    date: str

    # Description du match
    match_description: str = ""
    match_importance: str = "NORMAL"  # NORMAL, IMPORTANT, CRUCIAL

    # 1X2 Match complet
    result_1x2: str = ""
    home_prob: float = 0.0
    draw_prob: float = 0.0
    away_prob: float = 0.0

    # Buts (Match complet)
    over_under: str = ""
    over_25_prob: float = 0.0
    over_15_prob: float = 0.0
    over_35_prob: float = 0.0
    total_expected_goals: float = 0.0

    # BTTS
    btts: str = ""
    btts_prob: float = 0.0

    # Team +1.5
    team_plus_15: str = ""

    # Score exact
    score_exact: str = ""
    score_prob: float = 0.0

    # Clean sheet
    clean_sheet: str = ""
    clean_sheet_prob: float = 0.0

    # Double Chance + BTTS
    dc_btts: str = ""

    # ========== MI-TEMPS (1ère période) ==========
    ht_result: str = ""  # 1X2 mi-temps
    ht_home_prob: float = 0.0
    ht_draw_prob: float = 0.0
    ht_away_prob: float = 0.0
    ht_over_05: str = ""
    ht_over_05_prob: float = 0.0
    ht_over_15: str = ""
    ht_over_15_prob: float = 0.0
    ht_btts: str = ""
    ht_btts_prob: float = 0.0
    ht_expected_goals: float = 0.0
    ht_score_exact: str = ""

    # ========== 2ème MI-TEMPS ==========
    h2_over_05: str = ""
    h2_over_05_prob: float = 0.0
    h2_over_15: str = ""
    h2_over_15_prob: float = 0.0
    h2_expected_goals: float = 0.0

    # ========== HT/FT (Mi-temps / Fin) ==========
    ht_ft: str = ""
    ht_ft_prob: float = 0.0
    ht_ft_alternatives: List[str] = None

    # ========== CORNERS ==========
    corners: str = ""
    expected_corners: float = 0.0
    corners_over_85_prob: float = 0.0
    corners_over_95_prob: float = 0.0
    corners_over_105_prob: float = 0.0
    home_corners_avg: float = 0.0
    away_corners_avg: float = 0.0
    corners_recommendation: str = ""

    # ========== CARTONS ==========
    expected_yellow_cards: float = 0.0
    expected_total_cards: float = 0.0
    cards_over_35_prob: float = 0.0
    cards_over_45_prob: float = 0.0
    cards_over_55_prob: float = 0.0
    red_card_prob: float = 0.0
    cards_recommendation: str = ""
    referee_name: str = ""
    referee_strictness: str = ""

    # ========== CONFIANCE & RAISONNEMENT ==========
    confidence: str = ""
    reasoning: List[str] = None

    def __post_init__(self):
        if self.reasoning is None:
            self.reasoning = []
        if self.ht_ft_alternatives is None:
            self.ht_ft_alternatives = []


class EnhancedMatchAnalyzer:
    """Analyseur amélioré avec données multi-sources DYNAMIQUES + Pro API

    Configuration adaptative par ligue:
    - Poids des facteurs ajustés par ligue
    - Valeurs par défaut spécifiques à chaque ligue
    - Seuils de décision optimisés
    """

    def __init__(self):
        self.enricher = DataEnricher()
        # Configuration par défaut (sera surchargée par ligue)
        self._default_config = DEFAULT_CONFIG
        self._current_league_id = None
        self._current_config = DEFAULT_CONFIG

    def _load_league_config(self, league_id: int = None, league_name: str = None):
        """Charge la configuration spécifique à la ligue"""
        self._current_config = get_league_config(league_id, league_name)
        self._current_league_id = league_id
        logger.debug(f"[CONFIG] Loaded config for league {league_id}: {self._current_config.get('name', 'Default')}")

    @property
    def weights(self) -> dict:
        """Retourne les poids actuels (selon la ligue)"""
        return self._current_config.get("weights", self._default_config["weights"])

    @property
    def home_advantage(self) -> float:
        """Retourne l'avantage domicile (selon la ligue)"""
        return self._current_config.get("home_advantage", 0.08)

    @property
    def defaults(self) -> dict:
        """Retourne les valeurs par défaut (selon la ligue)"""
        return self._current_config.get("defaults", self._default_config["defaults"])

    @property
    def thresholds(self) -> dict:
        """Retourne les seuils de décision (selon la ligue)"""
        return self._current_config.get("thresholds", self._default_config["thresholds"])

    @property
    def avg_goals_per_match(self) -> float:
        """Retourne la moyenne de buts par match de la ligue"""
        return self._current_config.get("avg_goals_per_match", 2.5)

    @property
    def league_style(self) -> str:
        """Retourne le style de jeu de la ligue"""
        return self._current_config.get("style", "balanced")

    def _poisson_prob(self, lam: float, k: int) -> float:
        """Calcule la probabilité Poisson P(X=k) pour lambda donné"""
        if lam <= 0:
            return 1.0 if k == 0 else 0.0
        return (lam ** k) * math.exp(-lam) / math.factorial(k)

    def _predict_score_poisson(self, exp_home: float, exp_away: float, max_goals: int = 6,
                                  home_prob: float = 0.40, away_prob: float = 0.30) -> Tuple[str, float]:
        """
        Prédit le score exact en utilisant la distribution Poisson améliorée

        Args:
            exp_home: Buts attendus équipe domicile
            exp_away: Buts attendus équipe extérieur
            max_goals: Maximum de buts à considérer par équipe
            home_prob: Probabilité victoire domicile (pour ajuster le biais)
            away_prob: Probabilité victoire extérieur (pour ajuster le biais)

        Returns:
            (score_exact, probabilité)
        """
        best_score = "1-1"
        best_prob = 0.0

        # Ajuster les xG en fonction de la force relative des équipes
        # Si une équipe est clairement favorite, augmenter légèrement son xG
        prob_diff = home_prob - away_prob
        if prob_diff > 0.15:  # Home est clairement favori
            exp_home *= 1.10
            exp_away *= 0.95
        elif prob_diff < -0.15:  # Away est clairement favori
            exp_home *= 0.95
            exp_away *= 1.10

        # Calculer la probabilité de chaque score possible
        scores_probs = []
        for h in range(max_goals + 1):
            for a in range(max_goals + 1):
                prob = self._poisson_prob(exp_home, h) * self._poisson_prob(exp_away, a)

                # Pénaliser légèrement les scores nuls si une équipe est favorite
                if h == a:
                    if abs(prob_diff) > 0.10:
                        prob *= 0.85  # Réduire prob des nuls si écart de force
                    else:
                        prob *= 0.95  # Légère réduction même pour matchs équilibrés

                # Bonus pour scores réalistes de favoris
                if prob_diff > 0.12 and h > a:  # Home favori et victoire home
                    prob *= 1.08
                elif prob_diff < -0.12 and a > h:  # Away favori et victoire away
                    prob *= 1.08

                scores_probs.append((f"{h}-{a}", prob, h, a))

        # Trier par probabilité décroissante
        scores_probs.sort(key=lambda x: -x[1])

        # Le score le plus probable
        if scores_probs:
            best_score = scores_probs[0][0]
            best_prob = scores_probs[0][1]

        return best_score, best_prob

    def analyze_match_full(self, home_team: str, away_team: str,
                           league: str, match_date: str = "",
                           league_id: int = None, home_team_id: int = None,
                           away_team_id: int = None, fixture_id: int = None) -> EnhancedPrediction:
        """
        Analyse complète d'un match avec toutes les sources de données DYNAMIQUES + PRO

        Args:
            home_team: Nom de l'équipe à domicile
            away_team: Nom de l'équipe à l'extérieur
            league: Nom de la ligue
            match_date: Date du match
            league_id: ID de la ligue (API-Football)
            home_team_id: ID de l'équipe à domicile (API-Football)
            away_team_id: ID de l'équipe à l'extérieur (API-Football)
            fixture_id: ID du match (API-Football) pour les prédictions/cotes PRO
        """
        # Charger la configuration spécifique à la ligue
        self._load_league_config(league_id, league)
        logger.info(f"[PRO] Enhanced analysis: {home_team} vs {away_team} (League config: {self._current_config.get('name', 'Default')})")

        # Enrichir les données DYNAMIQUEMENT avec les IDs
        enriched = self.enricher.enrich_match(
            home_team, away_team, league,
            league_id=league_id,
            home_team_id=home_team_id,
            away_team_id=away_team_id
        )

        # [PRO] Récupérer les prédictions officielles de l'API
        api_predictions = None
        odds_data = None
        halftime_odds = None
        corners_odds = None
        home_cards_stats = None
        away_cards_stats = None
        referee_stats = None

        if fixture_id:
            api_predictions = self.enricher.get_predictions_api(fixture_id)
            odds_data = self.enricher.get_odds_api(fixture_id)
            halftime_odds = self.enricher.get_halftime_odds_api(fixture_id)
            corners_odds = self.enricher.get_corners_odds_api(fixture_id)
            referee_stats = self.enricher.get_referee_stats_api(fixture_id=fixture_id)
            logger.info(f"[PRO] API Predictions: {api_predictions.get('advice') if api_predictions else 'N/A'}")

        # [PRO] Récupérer les stats des derniers matchs (corners, tirs, etc.)
        home_fixture_stats = None
        away_fixture_stats = None
        if home_team_id and league_id:
            home_fixture_stats = self.enricher.get_team_last_fixtures_stats(home_team_id, league_id)
            home_cards_stats = self.enricher.get_cards_stats_api(home_team_id, league_id)
        if away_team_id and league_id:
            away_fixture_stats = self.enricher.get_team_last_fixtures_stats(away_team_id, league_id)
            away_cards_stats = self.enricher.get_cards_stats_api(away_team_id, league_id)

        # Analyse détaillée avec données PRO
        analysis = self._compute_analysis_pro(
            home_team, away_team, enriched,
            api_predictions, odds_data,
            home_fixture_stats, away_fixture_stats
        )

        # [PRO] Analyse mi-temps
        halftime_analysis = self._analyze_halftime_pro(
            enriched, analysis, halftime_odds, api_predictions
        )
        analysis['halftime'] = halftime_analysis

        # [PRO] Analyse cartons
        cards_analysis = self._analyze_cards_pro(
            home_cards_stats, away_cards_stats, referee_stats, league_id
        )
        analysis['cards'] = cards_analysis

        # [PRO] Analyse corners améliorée
        corners_analysis = self._analyze_corners_pro(
            enriched.home_stats, enriched.away_stats,
            home_fixture_stats, away_fixture_stats
        )
        if corners_odds:
            corners_analysis['odds'] = corners_odds
        analysis['corners'] = corners_analysis

        # Générer la prédiction enrichie
        return self._generate_prediction_pro(
            home_team, away_team, league, match_date,
            enriched, analysis, referee_stats
        )

    def _compute_analysis(self, home_team: str, away_team: str,
                          enriched: MatchEnrichedData) -> Dict:
        """Calcule l'analyse détaillée"""

        home_stats = enriched.home_stats
        away_stats = enriched.away_stats

        # Score de forme (basé sur les 5 derniers matchs)
        home_form_score = self._form_to_score(home_stats.form)
        away_form_score = self._form_to_score(away_stats.form)
        form_diff = (home_form_score - away_form_score) / 100

        # Score de classement
        standings_diff = 0
        if home_stats.league_position > 0 and away_stats.league_position > 0:
            standings_diff = (away_stats.league_position - home_stats.league_position) / 20

        # Score H2H
        h2h_diff = 0
        if enriched.h2h_matches > 0:
            h2h_diff = (enriched.h2h_home_wins - enriched.h2h_away_wins) / enriched.h2h_matches

        # Score de motivation
        motivation_diff = self._get_motivation_diff(home_stats, away_stats)

        # Blessures et suspensions
        injury_impact = self._calculate_injury_impact(home_stats, away_stats)

        # Score global pondéré
        weights = {
            "form": 0.25,
            "standings": 0.20,
            "h2h": 0.15,
            "home_adv": 0.15,
            "motivation": 0.10,
            "injuries": 0.10,
            "style": 0.05
        }

        weighted_score = (
            form_diff * weights["form"] +
            standings_diff * weights["standings"] +
            h2h_diff * weights["h2h"] +
            self.home_advantage * weights["home_adv"] +
            motivation_diff * weights["motivation"] +
            injury_impact * weights["injuries"]
        )

        # Probabilités 1X2
        home_prob, draw_prob, away_prob = self._score_to_probs(weighted_score)

        # Analyse des buts
        goals_analysis = self._analyze_goals_detailed(home_stats, away_stats, enriched)

        # Analyse des corners
        corners_analysis = self._analyze_corners(home_stats, away_stats)

        return {
            "weighted_score": weighted_score,
            "home_prob": home_prob,
            "draw_prob": draw_prob,
            "away_prob": away_prob,
            "form_diff": form_diff,
            "standings_diff": standings_diff,
            "h2h_diff": h2h_diff,
            "motivation_diff": motivation_diff,
            "injury_impact": injury_impact,
            "goals": goals_analysis,
            "corners": corners_analysis
        }

    def _compute_analysis_pro(self, home_team: str, away_team: str,
                               enriched: MatchEnrichedData,
                               api_predictions: Dict = None,
                               odds_data: Dict = None,
                               home_fixture_stats: Dict = None,
                               away_fixture_stats: Dict = None) -> Dict:
        """[PRO] Calcule l'analyse avec données API-Football Pro"""

        home_stats = enriched.home_stats
        away_stats = enriched.away_stats

        # Score de forme (basé sur les 5 derniers matchs)
        home_form_score = self._form_to_score(home_stats.form)
        away_form_score = self._form_to_score(away_stats.form)
        form_diff = (home_form_score - away_form_score) / 100

        # Score de classement
        standings_diff = 0
        if home_stats.league_position > 0 and away_stats.league_position > 0:
            standings_diff = (away_stats.league_position - home_stats.league_position) / 20

        # Score H2H
        h2h_diff = 0
        if enriched.h2h_matches > 0:
            h2h_diff = (enriched.h2h_home_wins - enriched.h2h_away_wins) / enriched.h2h_matches

        # Score de motivation
        motivation_diff = self._get_motivation_diff(home_stats, away_stats)

        # [PRO] Score des prédictions API
        api_home_prob = 0.40
        api_draw_prob = 0.25
        api_away_prob = 0.35
        api_advice = ""

        if api_predictions:
            # Parser les pourcentages (format "45%")
            try:
                api_home_prob = float(api_predictions.get('percent_home', '40%').replace('%', '')) / 100
                api_draw_prob = float(api_predictions.get('percent_draw', '25%').replace('%', '')) / 100
                api_away_prob = float(api_predictions.get('percent_away', '35%').replace('%', '')) / 100
                api_advice = api_predictions.get('advice', '')
            except (ValueError, AttributeError):
                pass

        # [PRO] Probabilités implicites des cotes
        odds_home_prob = 0.40
        odds_draw_prob = 0.25
        odds_away_prob = 0.35

        if odds_data and odds_data.get('match_winner', {}).get('home', 0) > 0:
            home_odd = odds_data['match_winner']['home']
            draw_odd = odds_data['match_winner']['draw']
            away_odd = odds_data['match_winner']['away']

            # Convertir cotes en probabilités (formule: 1/cote)
            raw_home = 1 / home_odd if home_odd > 0 else 0.40
            raw_draw = 1 / draw_odd if draw_odd > 0 else 0.25
            raw_away = 1 / away_odd if away_odd > 0 else 0.35

            # Normaliser (enlever la marge du bookmaker)
            total = raw_home + raw_draw + raw_away
            if total > 0:
                odds_home_prob = raw_home / total
                odds_draw_prob = raw_draw / total
                odds_away_prob = raw_away / total

        # Score global pondéré avec données PRO
        # Combiner forme, standings, h2h, home advantage
        base_score = (
            form_diff * self.weights['form'] +
            standings_diff * self.weights['standings'] +
            h2h_diff * self.weights['h2h'] +
            self.home_advantage * self.weights['home_adv'] +
            motivation_diff * self.weights['motivation']
        )

        # Convertir le base_score en probabilités de base
        base_home, base_draw, base_away = self._score_to_probs(base_score)

        # [PRO] Fusionner avec les prédictions API et les cotes implicites
        final_home_prob = (
            base_home * 0.40 +
            api_home_prob * self.weights['api_predictions'] +
            odds_home_prob * self.weights['odds_implied'] +
            base_home * 0.10  # Ajustement
        )
        final_draw_prob = (
            base_draw * 0.40 +
            api_draw_prob * self.weights['api_predictions'] +
            odds_draw_prob * self.weights['odds_implied'] +
            base_draw * 0.10
        )
        final_away_prob = (
            base_away * 0.40 +
            api_away_prob * self.weights['api_predictions'] +
            odds_away_prob * self.weights['odds_implied'] +
            base_away * 0.10
        )

        # Normaliser
        total_prob = final_home_prob + final_draw_prob + final_away_prob
        final_home_prob /= total_prob
        final_draw_prob /= total_prob
        final_away_prob /= total_prob

        # [PRO] Analyse des buts avec stats de matchs réels
        goals_analysis = self._analyze_goals_pro(
            home_stats, away_stats, enriched,
            api_predictions, odds_data,
            home_fixture_stats, away_fixture_stats
        )

        # [PRO] Analyse des corners avec stats réelles
        corners_analysis = self._analyze_corners_pro(
            home_stats, away_stats,
            home_fixture_stats, away_fixture_stats
        )

        return {
            "weighted_score": base_score,
            "home_prob": final_home_prob,
            "draw_prob": final_draw_prob,
            "away_prob": final_away_prob,
            "form_diff": form_diff,
            "standings_diff": standings_diff,
            "h2h_diff": h2h_diff,
            "motivation_diff": motivation_diff,
            "api_advice": api_advice,
            "api_probs": {"home": api_home_prob, "draw": api_draw_prob, "away": api_away_prob},
            "odds_probs": {"home": odds_home_prob, "draw": odds_draw_prob, "away": odds_away_prob},
            "odds_data": odds_data,
            "goals": goals_analysis,
            "corners": corners_analysis
        }

    def _analyze_goals_pro(self, home: TeamStats, away: TeamStats,
                           enriched: MatchEnrichedData,
                           api_predictions: Dict = None,
                           odds_data: Dict = None,
                           home_fixture_stats: Dict = None,
                           away_fixture_stats: Dict = None) -> Dict:
        """[PRO] Analyse des buts avec données API Pro - VERSION ADAPTIVE PAR LIGUE"""

        # Buts moyens par match - VALEURS PAR DÉFAUT ADAPTÉES À LA LIGUE
        league_defaults = self.defaults
        default_scored = league_defaults.get("goals_scored", 1.2)
        default_conceded = league_defaults.get("goals_conceded", 1.1)

        home_scored = home.avg_goals_scored if home.avg_goals_scored > 0 else default_scored
        home_conceded = home.avg_goals_conceded if home.avg_goals_conceded > 0 else default_conceded
        away_scored = away.avg_goals_scored if away.avg_goals_scored > 0 else default_scored * 0.9  # Légèrement moins à l'extérieur
        away_conceded = away.avg_goals_conceded if away.avg_goals_conceded > 0 else default_conceded * 1.1

        # Calcul des buts attendus avec pondération selon style de ligue
        if self.league_style == "attacking":
            # Ligues offensives: plus de poids sur l'attaque
            expected_home = (home_scored * 0.65 + away_conceded * 0.35)
            expected_away = (away_scored * 0.65 + home_conceded * 0.35)
        elif self.league_style == "defensive":
            # Ligues défensives: plus de poids sur la défense
            expected_home = (home_scored * 0.55 + away_conceded * 0.45)
            expected_away = (away_scored * 0.55 + home_conceded * 0.45)
        else:
            # Style équilibré
            expected_home = (home_scored * 0.6 + away_conceded * 0.4)
            expected_away = (away_scored * 0.6 + home_conceded * 0.4)

        total_expected = expected_home + expected_away

        # Cap maximum adapté à la ligue
        max_xg = self.avg_goals_per_match + 1.0  # Ex: Bundesliga 3.1 → max 4.1
        total_expected = min(total_expected, max_xg)

        # [PRO] Ajuster avec les prédictions API
        if api_predictions:
            api_goals_home = api_predictions.get('goals_home')
            api_goals_away = api_predictions.get('goals_away')
            if api_goals_home and api_goals_away:
                try:
                    api_home = float(api_goals_home.replace('-', '0'))
                    api_away = float(api_goals_away.replace('-', '0'))
                    # Moyenne pondérée avec les prédictions API
                    expected_home = (expected_home * 0.6) + (api_home * 0.4)
                    expected_away = (expected_away * 0.6) + (api_away * 0.4)
                    total_expected = expected_home + expected_away
                except (ValueError, AttributeError):
                    pass

        # Ajuster avec H2H (seulement si données fiables)
        if enriched.h2h_avg_goals > 0 and enriched.h2h_matches >= 3:
            total_expected = (total_expected * 0.7) + (enriched.h2h_avg_goals * 0.3)

        # CAP FINAL adapté à la ligue
        total_expected = min(total_expected, max_xg)

        # [PRO] Probabilités basées sur les cotes réelles
        over_25_prob = self._calculate_over_prob(total_expected, 2.5)
        if odds_data and odds_data.get('over_under_25', {}).get('over', 0) > 0:
            odds_over = odds_data['over_under_25']['over']
            odds_under = odds_data['over_under_25']['under']
            # Probabilité implicite des cotes
            odds_over_prob = (1 / odds_over) / ((1 / odds_over) + (1 / odds_under)) if odds_over > 0 and odds_under > 0 else 0.50
            # Moyenne pondérée
            over_25_prob = (over_25_prob * 0.5) + (odds_over_prob * 0.5)

        over_15_prob = self._calculate_over_prob(total_expected, 1.5)
        over_35_prob = self._calculate_over_prob(total_expected, 3.5)

        # [PRO] BTTS avec cotes réelles
        btts_prob = self._calculate_btts_prob(home, away, enriched)
        if odds_data and odds_data.get('btts', {}).get('yes', 0) > 0:
            odds_btts_yes = odds_data['btts']['yes']
            odds_btts_no = odds_data['btts']['no']
            odds_btts_prob = (1 / odds_btts_yes) / ((1 / odds_btts_yes) + (1 / odds_btts_no)) if odds_btts_yes > 0 and odds_btts_no > 0 else 0.50
            btts_prob = (btts_prob * 0.5) + (odds_btts_prob * 0.5)

        return {
            "expected_home": expected_home,
            "expected_away": expected_away,
            "total_expected": total_expected,
            "over_15_prob": over_15_prob,
            "over_25_prob": over_25_prob,
            "over_35_prob": over_35_prob,
            "btts_prob": btts_prob
        }

    def _analyze_corners_pro(self, home: TeamStats, away: TeamStats,
                              home_fixture_stats: Dict = None,
                              away_fixture_stats: Dict = None) -> Dict:
        """[PRO] Analyse des corners avec stats de matchs réels + détection valeurs par défaut"""

        # Flags pour détecter les données réelles vs par défaut
        home_is_real = False
        away_is_real = False

        # Valeurs par défaut ADAPTÉES À LA LIGUE
        default_corners = self.defaults.get("corners", 5.0)
        home_corners = default_corners
        away_corners = default_corners * 0.95  # Légèrement moins pour l'extérieur

        # Priorité 1: Stats des derniers matchs (API)
        if home_fixture_stats and home_fixture_stats.get('avg_corners', 0) > 0:
            home_corners = home_fixture_stats['avg_corners']
            home_is_real = True
        # Priorité 2: Stats d'équipe enrichies (vérifier que ce n'est pas une valeur par défaut)
        elif home.avg_corners > 0 and abs(home.avg_corners - default_corners) > 0.1:
            home_corners = home.avg_corners
            home_is_real = True

        if away_fixture_stats and away_fixture_stats.get('avg_corners', 0) > 0:
            away_corners = away_fixture_stats['avg_corners']
            away_is_real = True
        elif away.avg_corners > 0 and abs(away.avg_corners - default_corners) > 0.1:
            away_corners = away.avg_corners
            away_is_real = True

        total_corners = home_corners + away_corners

        # Évaluer la fiabilité des données
        if home_is_real and away_is_real:
            data_quality = "FIABLE"
            confidence_multiplier = 1.0
        elif home_is_real or away_is_real:
            data_quality = "PARTIEL"
            confidence_multiplier = 0.8  # Réduire confiance de 20%
        else:
            data_quality = "DEFAUT"
            confidence_multiplier = 0.5  # Réduire confiance de 50%
            # Avec données par défaut, utiliser l'estimation de la ligue
            total_corners = default_corners * 2 - 0.5  # Approximation basée sur la config ligue

        # Calcul des probabilités (ajustées selon la fiabilité)
        base_over_75 = 0.70 if total_corners >= 10.0 else (0.60 if total_corners >= 9.0 else (0.50 if total_corners >= 8.0 else 0.40))
        base_over_85 = 0.60 if total_corners >= 11.0 else (0.50 if total_corners >= 10.0 else (0.40 if total_corners >= 9.0 else 0.30))
        base_over_95 = 0.50 if total_corners >= 12.0 else (0.40 if total_corners >= 11.0 else (0.30 if total_corners >= 10.0 else 0.22))
        base_over_105 = 0.40 if total_corners >= 13.0 else (0.30 if total_corners >= 12.0 else 0.20)

        # Appliquer le multiplicateur de confiance
        over_75_prob = base_over_75 * confidence_multiplier
        over_85_prob = base_over_85 * confidence_multiplier
        over_95_prob = base_over_95 * confidence_multiplier
        over_105_prob = base_over_105 * confidence_multiplier

        return {
            "home_avg": home_corners,
            "away_avg": away_corners,
            "expected": total_corners,
            "over_75_prob": over_75_prob,
            "over_85_prob": over_85_prob,
            "over_95_prob": over_95_prob,
            "over_105_prob": over_105_prob,
            "data_quality": data_quality,
            "home_is_real": home_is_real,
            "away_is_real": away_is_real
        }

    def _analyze_halftime_pro(self, enriched: 'MatchEnrichedData', analysis: Dict,
                               halftime_odds: Dict = None, api_predictions: Dict = None) -> Dict:
        """[PRO] Analyse des mi-temps avec cotes et prédictions"""

        # Estimation des buts en 1ère mi-temps (généralement ~40% des buts)
        total_expected = analysis['goals']['total_expected']
        ht_expected_goals = total_expected * 0.42  # 42% des buts en MT1

        # Estimation 2ème mi-temps
        h2_expected_goals = total_expected * 0.58  # 58% des buts en MT2

        # Probabilités 1X2 mi-temps basées sur les probabilités finales
        home_prob = analysis['home_prob']
        away_prob = analysis['away_prob']
        draw_prob = analysis['draw_prob']

        # En mi-temps, plus de matchs nuls (moins de temps pour marquer)
        ht_draw_prob = min(0.50, draw_prob * 1.4)
        ht_home_prob = home_prob * 0.75
        ht_away_prob = away_prob * 0.70

        # Normaliser
        total = ht_home_prob + ht_draw_prob + ht_away_prob
        ht_home_prob /= total
        ht_draw_prob /= total
        ht_away_prob /= total

        # [PRO] Ajuster avec les cotes si disponibles
        if halftime_odds and halftime_odds.get('ht_1x2', {}).get('home', 0) > 0:
            ht_odds = halftime_odds['ht_1x2']
            # Probabilités implicites
            raw_home = 1 / ht_odds['home'] if ht_odds['home'] > 0 else ht_home_prob
            raw_draw = 1 / ht_odds['draw'] if ht_odds['draw'] > 0 else ht_draw_prob
            raw_away = 1 / ht_odds['away'] if ht_odds['away'] > 0 else ht_away_prob
            total = raw_home + raw_draw + raw_away
            if total > 0:
                # Moyenne pondérée avec les cotes
                ht_home_prob = (ht_home_prob * 0.5) + ((raw_home / total) * 0.5)
                ht_draw_prob = (ht_draw_prob * 0.5) + ((raw_draw / total) * 0.5)
                ht_away_prob = (ht_away_prob * 0.5) + ((raw_away / total) * 0.5)

        # Probabilités Over/Under mi-temps
        ht_over_05_prob = self._calculate_over_prob(ht_expected_goals, 0.5)
        ht_over_15_prob = self._calculate_over_prob(ht_expected_goals, 1.5)

        # BTTS mi-temps (plus rare)
        btts_prob = analysis['goals']['btts_prob']
        ht_btts_prob = btts_prob * 0.35  # Beaucoup plus rare en MT

        # Score exact mi-temps le plus probable
        if ht_draw_prob > max(ht_home_prob, ht_away_prob):
            if ht_expected_goals >= 1.2:
                ht_score_exact = "1-1"
            else:
                ht_score_exact = "0-0"
        elif ht_home_prob > ht_away_prob:
            ht_score_exact = "1-0"
        else:
            ht_score_exact = "0-1"

        # HT/FT predictions
        ht_ft_predictions = self._calculate_ht_ft_probs(
            ht_home_prob, ht_draw_prob, ht_away_prob,
            home_prob, draw_prob, away_prob
        )

        return {
            "ht_expected_goals": ht_expected_goals,
            "h2_expected_goals": h2_expected_goals,
            "ht_home_prob": ht_home_prob,
            "ht_draw_prob": ht_draw_prob,
            "ht_away_prob": ht_away_prob,
            "ht_over_05_prob": ht_over_05_prob,
            "ht_over_15_prob": ht_over_15_prob,
            "ht_btts_prob": ht_btts_prob,
            "ht_score_exact": ht_score_exact,
            "h2_over_05_prob": self._calculate_over_prob(h2_expected_goals, 0.5),
            "h2_over_15_prob": self._calculate_over_prob(h2_expected_goals, 1.5),
            "ht_ft": ht_ft_predictions
        }

    def _calculate_ht_ft_probs(self, ht_home: float, ht_draw: float, ht_away: float,
                                ft_home: float, ft_draw: float, ft_away: float) -> Dict:
        """Calcule les probabilités HT/FT"""
        probs = {
            "1/1": ht_home * ft_home * 1.2,  # Plus probable si mène à la MT
            "1/X": ht_home * ft_draw * 0.6,  # Moins probable
            "1/2": ht_home * ft_away * 0.3,  # Comeback rare
            "X/1": ht_draw * ft_home * 0.9,
            "X/X": ht_draw * ft_draw * 1.3,
            "X/2": ht_draw * ft_away * 0.9,
            "2/1": ht_away * ft_home * 0.3,  # Comeback rare
            "2/X": ht_away * ft_draw * 0.6,
            "2/2": ht_away * ft_away * 1.2,
        }

        # Normaliser
        total = sum(probs.values())
        for k in probs:
            probs[k] = probs[k] / total

        # Trier par probabilité
        sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)
        best_ht_ft = sorted_probs[0][0]
        best_prob = sorted_probs[0][1]

        return {
            "best": best_ht_ft,
            "best_prob": best_prob,
            "all_probs": dict(sorted_probs[:5])  # Top 5
        }

    def _analyze_cards_pro(self, home_cards_stats: Dict = None, away_cards_stats: Dict = None,
                           referee_stats: Dict = None, league_id: int = None) -> Dict:
        """[PRO] Analyse des cartons avec stats d'équipes et arbitre + détection valeurs par défaut"""

        # Flags pour détecter les données réelles
        home_is_real = False
        away_is_real = False
        referee_is_real = False

        # Valeurs par défaut ADAPTÉES À LA LIGUE
        default_yellow = self.defaults.get("yellow_cards", 1.5)
        default_red = self.defaults.get("red_cards", 0.08)

        home_avg_yellow = default_yellow
        away_avg_yellow = default_yellow
        home_avg_red = default_red
        away_avg_red = default_red

        if home_cards_stats and home_cards_stats.get('avg_yellow_per_match', 0) > 0:
            home_avg_yellow = home_cards_stats.get('avg_yellow_per_match', default_yellow)
            home_avg_red = home_cards_stats.get('avg_red_per_match', default_red)
            # Vérifier si ce n'est pas une valeur par défaut
            if abs(home_avg_yellow - default_yellow) > 0.1:
                home_is_real = True

        if away_cards_stats and away_cards_stats.get('avg_yellow_per_match', 0) > 0:
            away_avg_yellow = away_cards_stats.get('avg_yellow_per_match', default_yellow)
            away_avg_red = away_cards_stats.get('avg_red_per_match', default_red)
            if abs(away_avg_yellow - default_yellow) > 0.1:
                away_is_real = True

        total_yellow_expected = home_avg_yellow + away_avg_yellow
        total_red_expected = home_avg_red + away_avg_red
        total_cards_expected = total_yellow_expected + total_red_expected

        # Ajuster selon l'arbitre
        referee_multiplier = 1.0
        referee_name = ""
        referee_strictness = "MOYEN"

        if referee_stats and referee_stats.get('name'):
            referee_name = referee_stats.get('name', '')
            referee_strictness = referee_stats.get('strictness', 'MOYEN')
            referee_is_real = True
            if referee_strictness == 'STRICT':
                referee_multiplier = 1.25
            elif referee_strictness == 'FAIBLE':
                referee_multiplier = 0.80

        total_yellow_expected *= referee_multiplier
        total_cards_expected *= referee_multiplier

        # Ajuster selon la ligue (certaines ligues sont plus physiques)
        if is_physical_league(league_id or self._current_league_id or 0):
            total_yellow_expected *= 1.1
            logger.debug(f"[CARDS] Physical league bonus applied")

        # Évaluer la fiabilité des données
        real_count = sum([home_is_real, away_is_real, referee_is_real])
        if real_count >= 2:
            data_quality = "FIABLE"
            confidence_multiplier = 1.0
        elif real_count == 1:
            data_quality = "PARTIEL"
            confidence_multiplier = 0.85
        else:
            data_quality = "DEFAUT"
            confidence_multiplier = 0.6
            # Avec données par défaut, utiliser la moyenne de la ligue
            total_yellow_expected = default_yellow * 2

        # Probabilités (ajustées selon fiabilité)
        base_over_25 = self._calculate_cards_over_prob(total_yellow_expected, 2.5)
        base_over_35 = self._calculate_cards_over_prob(total_yellow_expected, 3.5)
        base_over_45 = self._calculate_cards_over_prob(total_yellow_expected, 4.5)
        base_over_55 = self._calculate_cards_over_prob(total_yellow_expected, 5.5)

        cards_over_25_prob = base_over_25 * confidence_multiplier
        cards_over_35_prob = base_over_35 * confidence_multiplier
        cards_over_45_prob = base_over_45 * confidence_multiplier
        cards_over_55_prob = base_over_55 * confidence_multiplier

        # Probabilité carton rouge
        red_card_prob = min(0.40, total_red_expected * 2.5) * confidence_multiplier

        # Recommandation avec indicateur de fiabilité
        quality_indicator = "✓" if data_quality == "FIABLE" else ("~" if data_quality == "PARTIEL" else "?")

        if total_yellow_expected >= 5.0:
            recommendation = f"Cartons +4.5 ({cards_over_45_prob:.0%}) {quality_indicator}"
        elif total_yellow_expected >= 4.0:
            recommendation = f"Cartons +3.5 ({cards_over_35_prob:.0%}) {quality_indicator}"
        else:
            recommendation = f"Cartons +2.5 ({cards_over_25_prob:.0%}) {quality_indicator}"

        return {
            "home_avg_yellow": home_avg_yellow,
            "away_avg_yellow": away_avg_yellow,
            "expected_yellow": total_yellow_expected,
            "expected_total": total_cards_expected,
            "cards_over_25_prob": cards_over_25_prob,
            "cards_over_35_prob": cards_over_35_prob,
            "cards_over_45_prob": cards_over_45_prob,
            "cards_over_55_prob": cards_over_55_prob,
            "red_card_prob": red_card_prob,
            "recommendation": recommendation,
            "referee_name": referee_name,
            "referee_strictness": referee_strictness,
            "data_quality": data_quality,
            "home_is_real": home_is_real,
            "away_is_real": away_is_real,
            "referee_is_real": referee_is_real
        }

    def _calculate_cards_over_prob(self, expected: float, threshold: float) -> float:
        """Calcule la probabilité de plus de X cartons"""
        diff = expected - threshold
        prob = 0.50 + (diff * 0.15)
        return max(0.20, min(0.85, prob))

    def _assess_data_quality(self, enriched: 'MatchEnrichedData') -> str:
        """
        Évalue la qualité des données disponibles.
        Retourne: 'BON', 'MOYEN', ou 'INSUFFISANT'
        """
        score = 0
        max_score = 6

        home = enriched.home_stats
        away = enriched.away_stats

        # 1. Forme récente (2 points si disponible)
        if home.form and len(home.form) >= 3:
            score += 1
        if away.form and len(away.form) >= 3:
            score += 1

        # 2. Position au classement (1 point si disponible)
        if home.league_position > 0 and away.league_position > 0:
            score += 1

        # 3. H2H (1 point si au moins 3 matchs)
        if enriched.h2h_matches >= 3:
            score += 1

        # 4. Stats de buts (1 point si disponibles)
        if home.avg_goals_scored > 0 and away.avg_goals_scored > 0:
            score += 1

        # 5. Pas de valeurs par défaut (1 point)
        # Si les corners sont exactement 5.0/5.0, ce sont probablement des valeurs par défaut
        if not (home.avg_corners == 5.0 and away.avg_corners == 5.0 and
                home.avg_corners == away.avg_corners):
            score += 1

        # Évaluation
        ratio = score / max_score
        if ratio >= 0.70:
            return "BON"
        elif ratio >= 0.40:
            return "MOYEN"
        else:
            return "INSUFFISANT"

    def _generate_match_description(self, home_team: str, away_team: str,
                                     enriched: 'MatchEnrichedData', analysis: Dict) -> Tuple[str, str]:
        """Génère une description détaillée du match"""

        home_stats = enriched.home_stats
        away_stats = enriched.away_stats

        # Déterminer l'importance
        importance = "NORMAL"
        importance_reasons = []

        if home_stats.motivation in ['title', 'relegation'] or away_stats.motivation in ['title', 'relegation']:
            importance = "CRUCIAL"
            if home_stats.motivation == 'title' or away_stats.motivation == 'title':
                importance_reasons.append("course au titre")
            if home_stats.motivation == 'relegation' or away_stats.motivation == 'relegation':
                importance_reasons.append("lutte pour le maintien")
        elif home_stats.motivation in ['champions_league', 'europa'] or away_stats.motivation in ['champions_league', 'europa']:
            importance = "IMPORTANT"
            importance_reasons.append("qualification européenne en jeu")

        # Construire la description
        parts = []

        # Forme
        home_form_score = self._form_to_score(home_stats.form)
        away_form_score = self._form_to_score(away_stats.form)

        if home_form_score >= 80:
            parts.append(f"{home_team} en excellente forme ({home_stats.form})")
        elif home_form_score <= 30:
            parts.append(f"{home_team} en difficulté ({home_stats.form})")

        if away_form_score >= 80:
            parts.append(f"{away_team} en pleine confiance ({away_stats.form})")
        elif away_form_score <= 30:
            parts.append(f"{away_team} en crise ({away_stats.form})")

        # Classement
        if home_stats.league_position > 0 and away_stats.league_position > 0:
            pos_diff = abs(home_stats.league_position - away_stats.league_position)
            if pos_diff >= 10:
                if home_stats.league_position < away_stats.league_position:
                    parts.append(f"écart au classement: {home_team} ({home_stats.league_position}e) vs {away_team} ({away_stats.league_position}e)")
                else:
                    parts.append(f"écart au classement: {away_team} ({away_stats.league_position}e) vs {home_team} ({home_stats.league_position}e)")

        # H2H
        if enriched.h2h_matches >= 3:
            if enriched.h2h_home_wins > enriched.h2h_away_wins + 2:
                parts.append(f"H2H favorable à {home_team} ({enriched.h2h_home_wins}V-{enriched.h2h_draws}N-{enriched.h2h_away_wins}D)")
            elif enriched.h2h_away_wins > enriched.h2h_home_wins + 2:
                parts.append(f"H2H favorable à {away_team} ({enriched.h2h_away_wins}V-{enriched.h2h_draws}N-{enriched.h2h_home_wins}D)")

        # Tendance buts
        goals_expected = analysis['goals']['total_expected']
        if goals_expected >= 3.5:
            parts.append(f"match à buts attendu ({goals_expected:.1f} buts prévus)")
        elif goals_expected <= 2.0:
            parts.append(f"match potentiellement fermé ({goals_expected:.1f} buts prévus)")

        description = ". ".join(parts) if parts else f"Match équilibré entre {home_team} et {away_team}"

        if importance_reasons:
            description += f". Enjeu: {', '.join(importance_reasons)}"

        return description, importance

    def _form_to_score(self, form: str) -> float:
        """Convertit la forme en score (0-100)"""
        if not form:
            return 50

        score = 0
        weights = [1.5, 1.3, 1.1, 0.9, 0.7]

        for i, result in enumerate(form[:5].upper()):
            w = weights[i] if i < len(weights) else 0.5
            if result == 'W':
                score += 20 * w
            elif result == 'D':
                score += 10 * w

        return min(100, score)

    def _get_motivation_diff(self, home: TeamStats, away: TeamStats) -> float:
        """Calcule la différence de motivation"""
        motivation_scores = {
            "title": 1.0,
            "champions_league": 0.8,
            "europa": 0.6,
            "conference": 0.4,
            "normal": 0.2,
            "relegation": 0.9  # Forte motivation aussi
        }

        home_mot = motivation_scores.get(home.motivation, 0.2)
        away_mot = motivation_scores.get(away.motivation, 0.2)

        return (home_mot - away_mot) * 0.3

    def _calculate_injury_impact(self, home: TeamStats, away: TeamStats) -> float:
        """Calcule l'impact des blessures"""
        home_impact = len(home.injuries) * 0.03
        away_impact = len(away.injuries) * 0.03

        return away_impact - home_impact  # Positif = avantage domicile

    def _score_to_probs(self, score: float) -> Tuple[float, float, float]:
        """Convertit le score en probabilités"""
        base_home = 0.42
        base_draw = 0.26
        base_away = 0.32

        adjustment = score * 0.35

        home_prob = max(0.12, min(0.78, base_home + adjustment))
        away_prob = max(0.12, min(0.70, base_away - adjustment))
        draw_prob = 1 - home_prob - away_prob
        draw_prob = max(0.12, min(0.38, draw_prob))

        # Normaliser
        total = home_prob + draw_prob + away_prob
        return home_prob/total, draw_prob/total, away_prob/total

    def _analyze_goals_detailed(self, home: TeamStats, away: TeamStats,
                                enriched: MatchEnrichedData) -> Dict:
        """Analyse détaillée des buts - VERSION ADAPTIVE PAR LIGUE"""

        # Buts moyens par match - VALEURS PAR DÉFAUT ADAPTÉES À LA LIGUE
        league_defaults = self.defaults
        default_scored = league_defaults.get("goals_scored", 1.2)
        default_conceded = league_defaults.get("goals_conceded", 1.1)

        home_scored = home.avg_goals_scored if home.avg_goals_scored > 0 else default_scored
        home_conceded = home.avg_goals_conceded if home.avg_goals_conceded > 0 else default_conceded
        away_scored = away.avg_goals_scored if away.avg_goals_scored > 0 else default_scored * 0.9
        away_conceded = away.avg_goals_conceded if away.avg_goals_conceded > 0 else default_conceded * 1.1

        # Si pas de données, utiliser le classement
        if home.avg_goals_scored == 0 and home.league_position > 0:
            home_scored = default_scored + 0.3 - (home.league_position - 1) * 0.04
            home_conceded = default_conceded - 0.2 + (home.league_position - 1) * 0.03
        if away.avg_goals_scored == 0 and away.league_position > 0:
            away_scored = default_scored + 0.1 - (away.league_position - 1) * 0.03
            away_conceded = default_conceded + (away.league_position - 1) * 0.04

        # Calcul selon le style de ligue
        if self.league_style == "attacking":
            expected_home = (home_scored * 0.65 + away_conceded * 0.35)
            expected_away = (away_scored * 0.65 + home_conceded * 0.35)
        elif self.league_style == "defensive":
            expected_home = (home_scored * 0.55 + away_conceded * 0.45)
            expected_away = (away_scored * 0.55 + home_conceded * 0.45)
        else:
            expected_home = (home_scored * 0.6 + away_conceded * 0.4)
            expected_away = (away_scored * 0.6 + home_conceded * 0.4)

        total_expected = expected_home + expected_away

        # Cap maximum adapté à la ligue
        max_xg = self.avg_goals_per_match + 1.0
        total_expected = min(total_expected, max_xg)

        # Ajuster avec H2H
        if enriched.h2h_avg_goals > 0 and enriched.h2h_matches >= 3:
            total_expected = (total_expected * 0.7) + (enriched.h2h_avg_goals * 0.3)

        # Probabilités
        over_25_prob = self._calculate_over_prob(total_expected, 2.5)
        over_15_prob = self._calculate_over_prob(total_expected, 1.5)
        over_35_prob = self._calculate_over_prob(total_expected, 3.5)

        # BTTS
        btts_prob = self._calculate_btts_prob(home, away, enriched)

        return {
            "expected_home": expected_home,
            "expected_away": expected_away,
            "total_expected": total_expected,
            "over_15_prob": over_15_prob,
            "over_25_prob": over_25_prob,
            "over_35_prob": over_35_prob,
            "btts_prob": btts_prob
        }

    def _calculate_over_prob(self, expected: float, threshold: float) -> float:
        """Calcule la probabilité d'over basée sur les buts attendus - VERSION CONSERVATIVE"""
        diff = expected - threshold

        # Formule plus conservative: coefficient réduit
        # Pour Over 2.5 avec xG de 2.5, la prob devrait être ~50%, pas 60%
        prob = 0.48 + (diff * 0.18)

        # Limites ajustées: max 80% (pas 85%)
        return max(0.20, min(0.80, prob))

    def _calculate_btts_prob(self, home: TeamStats, away: TeamStats,
                             enriched: MatchEnrichedData) -> float:
        """Calcule la probabilité BTTS - VERSION ULTRA CONSERVATIVE (basée sur analyse 09/01/2026)

        CONSTAT: Sur 5 matchs avec BTTS Oui prédit, 4 ont échoué (80% d'échec!)
        Les clean sheets sont TRÈS fréquentes, surtout dans les ligues non-européennes.
        """

        # ========== DÉTECTION MATCH DÉSÉQUILIBRÉ ==========
        position_diff = 0
        if home.league_position > 0 and away.league_position > 0:
            position_diff = abs(home.league_position - away.league_position)

        is_heavily_unbalanced = False
        is_moderately_unbalanced = False

        # Top 5 vs 10+ = très déséquilibré (élargi de top 3 à top 5)
        if (home.league_position <= 5 and away.league_position >= 10) or \
           (away.league_position <= 5 and home.league_position >= 10):
            is_heavily_unbalanced = True
            logger.info(f"[BTTS] Match TRÈS déséquilibré: pos {home.league_position} vs {away.league_position}")

        # Différence de classement > 5 positions = modérément déséquilibré
        if position_diff >= 5:
            is_moderately_unbalanced = True

        # Différence > 7 = très déséquilibré
        if position_diff >= 7:
            is_heavily_unbalanced = True

        # ========== BASE PROB ULTRA CONSERVATIVE ==========
        # CHANGEMENT MAJEUR: Partir de 35% au lieu de 45%
        # Car la réalité montre que BTTS est moins fréquent qu'on ne le pense
        if enriched.h2h_btts_percentage and enriched.h2h_matches >= 5:
            # Exiger plus de matchs H2H (5 au lieu de 3)
            base_prob = enriched.h2h_btts_percentage / 100
            # Mais plafonner à 55% même avec un bon historique
            base_prob = min(0.55, base_prob)
        else:
            # Sans données H2H fiables, partir de 35% (très conservateur)
            base_prob = 0.35

        # ========== MALUS POUR MATCH DÉSÉQUILIBRÉ ==========
        if is_heavily_unbalanced:
            base_prob -= 0.25  # Augmenté de 20% à 25%
            logger.info(f"[BTTS] Malus -25% pour match très déséquilibré → {base_prob:.2f}")
        elif is_moderately_unbalanced:
            base_prob -= 0.12
            logger.info(f"[BTTS] Malus -12% pour match modérément déséquilibré")

        # ========== AJUSTEMENTS CLEAN SHEETS (RENFORCÉS) ==========
        # Une équipe avec beaucoup de clean sheets = danger pour BTTS
        if home.clean_sheets >= 4:
            base_prob -= 0.18  # Augmenté
        elif home.clean_sheets >= 2:
            base_prob -= 0.08

        if away.clean_sheets >= 4:
            base_prob -= 0.18
        elif away.clean_sheets >= 2:
            base_prob -= 0.08

        # Équipe qui ne marque pas souvent
        if home.failed_to_score >= 4:
            base_prob -= 0.15
        elif home.failed_to_score >= 2:
            base_prob -= 0.08

        if away.failed_to_score >= 4:
            base_prob -= 0.15
        elif away.failed_to_score >= 2:
            base_prob -= 0.08

        # ========== BONUS BTTS (RÉDUITS) ==========
        # Bonus seulement si les DEUX équipes marquent régulièrement
        if home.avg_goals_scored >= 1.8 and away.avg_goals_scored >= 1.5:
            base_prob += 0.08  # Réduit de 10% à 8%
        elif home.avg_goals_scored >= 1.5 and away.avg_goals_scored >= 1.2:
            base_prob += 0.05

        # ========== MALUS DÉFENSE SOLIDE (RENFORCÉ) ==========
        if home.avg_goals_conceded < 0.7 or away.avg_goals_conceded < 0.7:
            base_prob -= 0.20  # Augmenté de 15% à 20%
        elif home.avg_goals_conceded < 1.0 or away.avg_goals_conceded < 1.0:
            base_prob -= 0.10

        # ========== MALUS ÉQUIPE DOMINANTE VS FAIBLE ==========
        if (home.league_position <= 2 and away.league_position >= 12) or \
           (away.league_position <= 2 and home.league_position >= 12):
            base_prob -= 0.15  # Augmenté de 10% à 15%
            logger.info(f"[BTTS] Malus -15% (équipe dominante vs très faible)")

        # ========== MALUS LIGUES AVEC BEAUCOUP DE CLEAN SHEETS ==========
        # Saudi Pro League, Ligue 1 Algérie: beaucoup de victoires à zéro
        # Ce sera géré par les stats d'équipe

        return max(0.15, min(0.60, base_prob))  # Max réduit de 70% à 60%

    def _analyze_corners(self, home: TeamStats, away: TeamStats) -> Dict:
        """Analyse des corners basée sur les stats dynamiques"""
        # Utiliser les moyennes de corners des stats d'équipe
        home_corners = home.avg_corners if home.avg_corners > 0 else 5.0
        away_corners = away.avg_corners if away.avg_corners > 0 else 4.5

        total_corners = home_corners + away_corners

        return {
            "expected": total_corners,
            "over_75_prob": 0.70 if total_corners >= 9.5 else (0.55 if total_corners >= 8.5 else 0.45),
            "over_85_prob": 0.55 if total_corners >= 10.5 else (0.45 if total_corners >= 9.5 else 0.35),
            "over_95_prob": 0.40 if total_corners >= 11.5 else (0.32 if total_corners >= 10.5 else 0.25)
        }

    def _generate_prediction(self, home_team: str, away_team: str,
                            league: str, match_date: str,
                            enriched: MatchEnrichedData,
                            analysis: Dict) -> EnhancedPrediction:
        """Génère la prédiction finale"""

        home_prob = analysis["home_prob"]
        draw_prob = analysis["draw_prob"]
        away_prob = analysis["away_prob"]
        goals = analysis["goals"]
        corners = analysis["corners"]

        # 1X2 - Logique AMÉLIORÉE basée sur analyse du 12/01/2026
        # PROBLÈME IDENTIFIÉ: 43.1% de réussite, trop de X prédits à tort
        # SOLUTION: Prédire le favori plus souvent, X seulement si vraiment équilibré

        prob_gap = abs(home_prob - away_prob)
        max_prob = max(home_prob, draw_prob, away_prob)

        # RÈGLE 1: Si une équipe a >= 48%, elle gagne (pas de X)
        if home_prob >= 0.48:
            result_1x2 = f"1 ({home_team})"
        elif away_prob >= 0.45:
            result_1x2 = f"2 ({away_team})"
        # RÈGLE 2: X seulement si probabilités TRÈS proches ET draw élevé
        elif draw_prob >= 0.34 and prob_gap < 0.04:
            result_1x2 = "X (Nul)"
        # RÈGLE 3: Favori avec marge de 8% (au lieu de 3%)
        elif home_prob > away_prob + 0.08:
            result_1x2 = f"1 ({home_team})"
        elif away_prob > home_prob + 0.08:
            result_1x2 = f"2 ({away_team})"
        # RÈGLE 4: Si home > away (même faible marge), prédire home (pas X)
        elif home_prob > away_prob:
            result_1x2 = f"1 ({home_team})"
        elif away_prob > home_prob:
            result_1x2 = f"2 ({away_team})"
        # RÈGLE 5: Vraiment équilibré -> X
        else:
            result_1x2 = "X (Nul)"

        # Over/Under - Format clair avec seuils adaptatifs
        over_threshold = self.thresholds.get("over_25", 0.55)
        under_threshold = self.thresholds.get("under_25", 0.40)

        if goals["over_25_prob"] >= over_threshold:
            over_under = "Over 2.5"
        elif goals["over_25_prob"] <= under_threshold:
            over_under = "Under 2.5"
        elif goals["over_15_prob"] >= 0.75:
            over_under = "Over 1.5"
        else:
            over_under = "Under 2.5"

        # Team +1.5
        if home_prob > away_prob:
            team_plus_15 = f"{home_team} +1.5 buts"
        else:
            team_plus_15 = f"{away_team} +1.5 buts"

        # Corners
        if corners["expected"] >= 10.5:
            corners_pred = "+8.5"
        elif corners["expected"] >= 9:
            corners_pred = "+7.5"
        else:
            corners_pred = "+7.5"

        # Score exact - Distribution Poisson pour scores réalistes et variés
        exp_home = goals["expected_home"]
        exp_away = goals["expected_away"]
        total_exp = goals["total_expected"]

        # Utiliser Poisson amélioré pour prédire le score (avec biais pour favoris)
        score_exact, score_prob = self._predict_score_poisson(
            exp_home, exp_away,
            home_prob=home_prob, away_prob=away_prob
        )
        logger.debug(f"[POISSON] Score prédit: {score_exact} (prob: {score_prob:.1%}) - xG: {exp_home:.2f}-{exp_away:.2f}")

        # BTTS - CALCULÉ INDÉPENDAMMENT (basé sur analyse du 12/01/2026)
        # PROBLÈME: BTTS dérivé du score exact (5.2% de réussite) = incohérent
        # SOLUTION: Utiliser la probabilité BTTS brute avec seuil strict
        score_parts = score_exact.split("-")
        home_goals = int(score_parts[0])
        away_goals = int(score_parts[1])
        btts_prob_raw = goals["btts_prob"]

        # BTTS avec seuil de 45% (compromis entre précision et rappel)
        # Analyse: Les faux BTTS Oui avaient une prob moyenne de 41.8%
        if btts_prob_raw >= 0.45:
            btts = "Oui"
            btts_prob_final = btts_prob_raw
            logger.debug(f"[BTTS] Oui (prob {btts_prob_raw:.1%} >= 50%)")
        else:
            btts = "Non"
            btts_prob_final = btts_prob_raw
            logger.debug(f"[BTTS] Non (prob {btts_prob_raw:.1%} < 50%)")

        # Clean sheet - Basé sur le score prédit uniquement
        if home_goals > 0 and away_goals == 0:
            clean_sheet = f"{home_team} gagne à 0"
            clean_sheet_prob = home_prob * 0.6
        elif away_goals > 0 and home_goals == 0:
            clean_sheet = f"{away_team} gagne à 0"
            clean_sheet_prob = away_prob * 0.5
        else:
            clean_sheet = "Non recommandé"
            clean_sheet_prob = 0.0

        # Double Chance + BTTS (cohérent avec BTTS)
        if btts == "Oui":
            dc_btts = "1X + BTTS Oui" if home_prob > away_prob else "X2 + BTTS Oui"
        else:
            dc_btts = "1X" if home_prob > away_prob else "X2"

        # Mi-temps / Fin - Plus varié
        if home_prob >= 0.55:
            ht_ft = f"1/1 ({home_team}/{home_team})"
        elif away_prob >= 0.50:
            ht_ft = f"2/2 ({away_team}/{away_team})"
        elif home_prob > away_prob + 0.05:
            ht_ft = f"X/1 (Nul/{home_team})"
        elif away_prob > home_prob:
            ht_ft = f"X/2 (Nul/{away_team})"
        else:
            ht_ft = "X/X (Nul/Nul)"

        # Confiance AMÉLIORÉE (basée sur analyse 12/01/2026)
        # PROBLÈME: 0% de confiance HIGH, 36% de réussite sur MEDIUM
        max_prob = max(home_prob, draw_prob, away_prob)
        data_quality = self._assess_data_quality(enriched)

        # Nouveaux seuils plus réalistes
        # HIGH: prob >= 55% ET bonnes données (H2H, forme, etc.)
        # MEDIUM: prob >= 45% ET données acceptables
        has_good_h2h = enriched.h2h_matches >= 5
        has_clear_favorite = max_prob >= 0.50
        has_form_data = bool(enriched.home_stats.form and enriched.away_stats.form)

        if data_quality == "INSUFFISANT":
            confidence = CONFIDENCE_LOW
        elif max_prob >= 0.55 and has_good_h2h and has_form_data:
            confidence = CONFIDENCE_HIGH
        elif max_prob >= 0.50 and has_clear_favorite:
            confidence = CONFIDENCE_MEDIUM
        elif max_prob >= 0.45 and (has_good_h2h or has_form_data):
            confidence = CONFIDENCE_MEDIUM
        else:
            confidence = CONFIDENCE_LOW

        # Raisonnement
        reasoning = []
        home_stats = enriched.home_stats
        away_stats = enriched.away_stats

        if home_stats.form:
            reasoning.append(f"Forme {home_team}: {home_stats.form}")
        if away_stats.form:
            reasoning.append(f"Forme {away_team}: {away_stats.form}")
        if home_stats.league_position > 0:
            reasoning.append(f"Classement: {home_team} {home_stats.league_position}e vs {away_team} {away_stats.league_position}e")
        if enriched.h2h_matches > 0:
            reasoning.append(f"H2H: {enriched.h2h_home_wins}V-{enriched.h2h_draws}N-{enriched.h2h_away_wins}D")
        if home_stats.injuries:
            reasoning.append(f"Blessures {home_team}: {', '.join(home_stats.injuries[:2])}")
        if away_stats.injuries:
            reasoning.append(f"Blessures {away_team}: {', '.join(away_stats.injuries[:2])}")
        if home_stats.motivation != "normal":
            reasoning.append(f"{home_team}: enjeu {home_stats.motivation}")

        return EnhancedPrediction(
            match_name=f"{home_team} vs {away_team}",
            league=league,
            date=match_date,
            result_1x2=result_1x2,
            home_prob=home_prob,
            draw_prob=draw_prob,
            away_prob=away_prob,
            over_under=over_under,
            over_25_prob=goals["over_25_prob"],
            total_expected_goals=goals["total_expected"],
            team_plus_15=team_plus_15,
            corners=corners_pred,
            expected_corners=corners["expected"],
            score_exact=score_exact,
            score_prob=score_prob,
            clean_sheet=clean_sheet,
            clean_sheet_prob=clean_sheet_prob,
            btts=btts,
            btts_prob=btts_prob_final,
            dc_btts=dc_btts,
            ht_ft=ht_ft,
            confidence=confidence,
            reasoning=reasoning
        )

    def _generate_prediction_pro(self, home_team: str, away_team: str,
                                  league: str, match_date: str,
                                  enriched: MatchEnrichedData,
                                  analysis: Dict,
                                  referee_stats: Dict = None) -> EnhancedPrediction:
        """[PRO] Génère la prédiction enrichie avec tous les marchés"""

        home_prob = analysis["home_prob"]
        draw_prob = analysis["draw_prob"]
        away_prob = analysis["away_prob"]
        goals = analysis["goals"]
        corners = analysis["corners"]
        halftime = analysis.get("halftime", {})
        cards = analysis.get("cards", {})

        # ========== Description du match ==========
        match_description, match_importance = self._generate_match_description(
            home_team, away_team, enriched, analysis
        )

        # ========== Score exact - Distribution Poisson pour scores réalistes ==========
        exp_home = goals["expected_home"]
        exp_away = goals["expected_away"]
        total_exp = goals["total_expected"]

        # Utiliser Poisson amélioré pour prédire le score (avec biais pour favoris)
        score_exact, score_prob = self._predict_score_poisson(
            exp_home, exp_away,
            home_prob=home_prob, away_prob=away_prob
        )
        logger.debug(f"[POISSON PRO] Score: {score_exact} (prob: {score_prob:.1%}) - xG: {exp_home:.2f}-{exp_away:.2f}")

        # Extraire les buts du score exact
        score_parts = score_exact.split("-")
        home_goals = int(score_parts[0])
        away_goals = int(score_parts[1])
        total_goals = home_goals + away_goals

        # ========== 1X2 Match complet (BASÉ SUR PROBABILITÉS - pas score exact) ==========
        # AMÉLIORATION 12/01/2026: Le score exact a 5.2% de réussite
        # Donc on utilise les probabilités directement pour 1X2
        prob_gap = abs(home_prob - away_prob)

        if home_prob >= 0.48:
            result_1x2 = f"1 ({home_team})"
        elif away_prob >= 0.45:
            result_1x2 = f"2 ({away_team})"
        elif draw_prob >= 0.34 and prob_gap < 0.04:
            result_1x2 = "X (Nul)"
        elif home_prob > away_prob + 0.08:
            result_1x2 = f"1 ({home_team})"
        elif away_prob > home_prob + 0.08:
            result_1x2 = f"2 ({away_team})"
        elif home_prob > away_prob:
            result_1x2 = f"1 ({home_team})"
        elif away_prob > home_prob:
            result_1x2 = f"2 ({away_team})"
        else:
            result_1x2 = "X (Nul)"

        # ========== Over/Under (DÉRIVÉ DU SCORE EXACT) ==========
        if total_goals >= 3:
            over_under = "Over 2.5"
        elif total_goals >= 2:
            # 2 buts = Under 2.5, mais vérifier si on était proche de Over
            if goals["over_25_prob"] >= 0.60:
                over_under = "Over 2.5"  # Recommander Over même si score prédit = 2
            else:
                over_under = "Under 2.5"
        else:
            over_under = "Under 2.5"

        # ========== Team +1.5 ==========
        team_plus_15 = f"{home_team} +1.5 buts" if home_goals > away_goals else f"{away_team} +1.5 buts"

        # ========== BTTS - CALCULÉ INDÉPENDAMMENT avec seuil strict ==========
        # AMÉLIORATION 12/01/2026: BTTS basé sur probabilité brute (pas score)
        btts_prob_raw = goals["btts_prob"]

        # BTTS Oui seulement si prob >= 45% (les faux Oui avaient 41.8% en moyenne)
        if btts_prob_raw >= 0.45:
            btts = "Oui"
            btts_prob_final = btts_prob_raw
        else:
            btts = "Non"
            btts_prob_final = btts_prob_raw

        # ========== Clean Sheet - Basé sur le score prédit ==========
        if home_goals > 0 and away_goals == 0:
            clean_sheet = f"{home_team} gagne à 0"
            clean_sheet_prob = home_prob * 0.6
        elif away_goals > 0 and home_goals == 0:
            clean_sheet = f"{away_team} gagne à 0"
            clean_sheet_prob = away_prob * 0.5
        else:
            clean_sheet = "Non recommandé"
            clean_sheet_prob = 0.0

        # ========== Double Chance + BTTS (cohérent avec BTTS calculé) ==========
        if btts == "Oui":
            dc_btts = "1X + BTTS Oui" if home_prob > away_prob else "X2 + BTTS Oui"
        else:
            # Si BTTS = Non, recommander DC seul ou DC + Under
            dc_btts = "1X" if home_prob > away_prob else "X2"

        # ========== MI-TEMPS (1ère période) ==========
        ht_home_prob = halftime.get('ht_home_prob', 0.30)
        ht_draw_prob = halftime.get('ht_draw_prob', 0.40)
        ht_away_prob = halftime.get('ht_away_prob', 0.30)

        # Note: ht_result sera calculé plus bas, dérivé du ht_score_exact

        ht_over_05_prob = halftime.get('ht_over_05_prob', 0.55)
        ht_over_05 = "Oui" if ht_over_05_prob >= 0.55 else "Non"

        ht_over_15_prob = halftime.get('ht_over_15_prob', 0.25)
        ht_over_15 = "Oui" if ht_over_15_prob >= 0.40 else "Non"

        ht_btts_prob = halftime.get('ht_btts_prob', 0.20)
        ht_btts = "Oui" if ht_btts_prob >= 0.35 else "Non"

        ht_expected_goals = halftime.get('ht_expected_goals', total_exp * 0.42)

        # ========== Score exact MT - DÉRIVÉ DU SCORE FINAL ==========
        # Le score MT doit être cohérent avec le score final prédit
        if home_goals > away_goals:
            # Victoire domicile - le domicile mène souvent à la MT
            if home_goals >= 3:
                ht_score_exact = "2-0" if away_goals == 0 else "1-0"
            elif home_goals == 2 and away_goals == 0:
                ht_score_exact = "1-0"
            elif home_goals == 2 and away_goals == 1:
                ht_score_exact = "1-0"  # Mène 1-0, puis 2-1 en FT
            else:
                ht_score_exact = "1-0"
        elif away_goals > home_goals:
            # Victoire extérieur - l'extérieur mène souvent à la MT
            if away_goals >= 3:
                ht_score_exact = "0-2" if home_goals == 0 else "0-1"
            elif away_goals == 2 and home_goals == 0:
                ht_score_exact = "0-1"
            elif away_goals == 2 and home_goals == 1:
                ht_score_exact = "0-1"  # Mène 0-1, puis 1-2 en FT
            else:
                ht_score_exact = "0-1"
        else:
            # Match nul - souvent 0-0 à la MT
            if home_goals == 0:
                ht_score_exact = "0-0"
            elif home_goals == 1:
                ht_score_exact = "0-0"  # 0-0 MT, puis 1-1 FT
            else:
                ht_score_exact = "1-1"  # 1-1 MT, puis 2-2 FT

        # Extraire buts MT
        ht_parts = ht_score_exact.split("-")
        ht_home_goals = int(ht_parts[0])
        ht_away_goals = int(ht_parts[1])

        # ========== ht_result DÉRIVÉ du score MT ==========
        if ht_home_goals > ht_away_goals:
            ht_result = f"1 ({home_team} MT)"
        elif ht_away_goals > ht_home_goals:
            ht_result = f"2 ({away_team} MT)"
        else:
            ht_result = "X (Nul MT)"

        # ========== 2ème MI-TEMPS ==========
        h2_expected_goals = halftime.get('h2_expected_goals', total_exp * 0.58)
        h2_over_05_prob = halftime.get('h2_over_05_prob', 0.70)
        h2_over_05 = "Oui" if h2_over_05_prob >= 0.60 else "Non"

        h2_over_15_prob = halftime.get('h2_over_15_prob', 0.35)
        h2_over_15 = "Oui" if h2_over_15_prob >= 0.45 else "Non"

        # ========== HT/FT (DÉRIVÉ DES SCORES MT ET FT) ==========
        # Déterminer résultat HT
        if ht_home_goals > ht_away_goals:
            ht_code = "1"
        elif ht_away_goals > ht_home_goals:
            ht_code = "2"
        else:
            ht_code = "X"

        # Déterminer résultat FT (déjà calculé via score_exact)
        if home_goals > away_goals:
            ft_code = "1"
        elif away_goals > home_goals:
            ft_code = "2"
        else:
            ft_code = "X"

        best_ht_ft = f"{ht_code}/{ft_code}"
        ht_ft_prob = halftime.get('ht_ft', {}).get('best_prob', 0.22)
        ht_ft_alternatives = []

        # Formater HT/FT
        ht_ft_map = {
            "1/1": f"1/1 ({home_team}/{home_team})",
            "1/X": f"1/X ({home_team}/Nul)",
            "1/2": f"1/2 ({home_team}/{away_team})",
            "X/1": f"X/1 (Nul/{home_team})",
            "X/X": "X/X (Nul/Nul)",
            "X/2": f"X/2 (Nul/{away_team})",
            "2/1": f"2/1 ({away_team}/{home_team})",
            "2/X": f"2/X ({away_team}/Nul)",
            "2/2": f"2/2 ({away_team}/{away_team})",
        }
        ht_ft = ht_ft_map.get(best_ht_ft, best_ht_ft)

        # ========== CORNERS (avec indicateur de fiabilité) ==========
        expected_corners = corners.get("expected", 9.5)
        corners_over_85_prob = corners.get("over_85_prob", 0.50)
        corners_over_95_prob = corners.get("over_95_prob", 0.35)
        corners_over_105_prob = corners.get("over_105_prob", 0.25)
        corners_data_quality = corners.get("data_quality", "DEFAUT")

        # Indicateur de fiabilité: ✓ = fiable, ~ = partiel, ? = par défaut
        corners_quality_indicator = "✓" if corners_data_quality == "FIABLE" else ("~" if corners_data_quality == "PARTIEL" else "?")

        if expected_corners >= 11.5:
            corners_pred = "+10.5"
            corners_recommendation = f"Corners +10.5 ({corners_over_105_prob:.0%}) {corners_quality_indicator}"
        elif expected_corners >= 10.5:
            corners_pred = "+9.5"
            corners_recommendation = f"Corners +9.5 ({corners_over_95_prob:.0%}) {corners_quality_indicator}"
        elif expected_corners >= 9.5:
            corners_pred = "+8.5"
            corners_recommendation = f"Corners +8.5 ({corners_over_85_prob:.0%}) {corners_quality_indicator}"
        else:
            corners_pred = "+7.5"
            corners_recommendation = f"Corners +7.5 ({corners.get('over_75_prob', 0.55):.0%}) {corners_quality_indicator}"

        # ========== CARTONS ==========
        expected_yellow = cards.get('expected_yellow', 3.0)
        expected_total_cards = cards.get('expected_total', 3.2)
        cards_over_35_prob = cards.get('cards_over_35_prob', 0.50)
        cards_over_45_prob = cards.get('cards_over_45_prob', 0.35)
        cards_over_55_prob = cards.get('cards_over_55_prob', 0.25)
        red_card_prob = cards.get('red_card_prob', 0.15)
        cards_recommendation = cards.get('recommendation', "Cartons +3.5")
        referee_name = cards.get('referee_name', '')
        referee_strictness = cards.get('referee_strictness', 'MOYEN')

        # ========== Confiance AMÉLIORÉE (basée sur analyse 12/01/2026) ==========
        max_prob = max(home_prob, draw_prob, away_prob)
        data_quality = self._assess_data_quality(enriched)

        # Critères de confiance améliorés
        has_good_h2h = enriched.h2h_matches >= 5
        has_clear_favorite = max_prob >= 0.50
        has_form_data = bool(enriched.home_stats.form and enriched.away_stats.form)

        if data_quality == "INSUFFISANT":
            confidence = CONFIDENCE_LOW
        elif max_prob >= 0.55 and has_good_h2h and has_form_data:
            confidence = CONFIDENCE_HIGH
        elif max_prob >= 0.50 and has_clear_favorite:
            confidence = CONFIDENCE_MEDIUM
        elif max_prob >= 0.45 and (has_good_h2h or has_form_data):
            confidence = CONFIDENCE_MEDIUM
        else:
            confidence = CONFIDENCE_LOW

        # ========== Raisonnement ==========
        reasoning = []
        home_stats = enriched.home_stats
        away_stats = enriched.away_stats

        if home_stats.form:
            reasoning.append(f"Forme {home_team}: {home_stats.form}")
        if away_stats.form:
            reasoning.append(f"Forme {away_team}: {away_stats.form}")
        if home_stats.league_position > 0:
            reasoning.append(f"Classement: {home_team} {home_stats.league_position}e vs {away_team} {away_stats.league_position}e")
        if enriched.h2h_matches > 0:
            reasoning.append(f"H2H: {enriched.h2h_home_wins}V-{enriched.h2h_draws}N-{enriched.h2h_away_wins}D")
        if home_stats.injuries:
            reasoning.append(f"Blessures {home_team}: {', '.join(home_stats.injuries[:2])}")
        if away_stats.injuries:
            reasoning.append(f"Blessures {away_team}: {', '.join(away_stats.injuries[:2])}")
        if home_stats.motivation != "normal":
            reasoning.append(f"{home_team}: enjeu {home_stats.motivation}")
        if referee_name:
            reasoning.append(f"Arbitre: {referee_name} ({referee_strictness})")

        return EnhancedPrediction(
            match_name=f"{home_team} vs {away_team}",
            league=league,
            date=match_date,
            # Description
            match_description=match_description,
            match_importance=match_importance,
            # 1X2
            result_1x2=result_1x2,
            home_prob=home_prob,
            draw_prob=draw_prob,
            away_prob=away_prob,
            # Buts
            over_under=over_under,
            over_25_prob=goals["over_25_prob"],
            over_15_prob=goals["over_15_prob"],
            over_35_prob=goals["over_35_prob"],
            total_expected_goals=goals["total_expected"],
            # BTTS
            btts=btts,
            btts_prob=btts_prob_final,
            # Score exact
            team_plus_15=team_plus_15,
            score_exact=score_exact,
            score_prob=score_prob,
            clean_sheet=clean_sheet,
            clean_sheet_prob=clean_sheet_prob,
            dc_btts=dc_btts,
            # Mi-temps
            ht_result=ht_result,
            ht_home_prob=ht_home_prob,
            ht_draw_prob=ht_draw_prob,
            ht_away_prob=ht_away_prob,
            ht_over_05=ht_over_05,
            ht_over_05_prob=ht_over_05_prob,
            ht_over_15=ht_over_15,
            ht_over_15_prob=ht_over_15_prob,
            ht_btts=ht_btts,
            ht_btts_prob=ht_btts_prob,
            ht_expected_goals=ht_expected_goals,
            ht_score_exact=ht_score_exact,
            # 2ème mi-temps
            h2_over_05=h2_over_05,
            h2_over_05_prob=h2_over_05_prob,
            h2_over_15=h2_over_15,
            h2_over_15_prob=h2_over_15_prob,
            h2_expected_goals=h2_expected_goals,
            # HT/FT
            ht_ft=ht_ft,
            ht_ft_prob=ht_ft_prob,
            ht_ft_alternatives=ht_ft_alternatives,
            # Corners
            corners=corners_pred,
            expected_corners=expected_corners,
            corners_over_85_prob=corners_over_85_prob,
            corners_over_95_prob=corners_over_95_prob,
            corners_over_105_prob=corners_over_105_prob,
            home_corners_avg=corners.get("home_avg", 5.0),
            away_corners_avg=corners.get("away_avg", 4.5),
            corners_recommendation=corners_recommendation,
            # Cartons
            expected_yellow_cards=expected_yellow,
            expected_total_cards=expected_total_cards,
            cards_over_35_prob=cards_over_35_prob,
            cards_over_45_prob=cards_over_45_prob,
            cards_over_55_prob=cards_over_55_prob,
            red_card_prob=red_card_prob,
            cards_recommendation=cards_recommendation,
            referee_name=referee_name,
            referee_strictness=referee_strictness,
            # Confiance
            confidence=confidence,
            reasoning=reasoning
        )


# Instance globale
enhanced_analyzer = EnhancedMatchAnalyzer()
