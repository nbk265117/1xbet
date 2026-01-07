"""
Analyseur amélioré avec données enrichies multi-sources
Utilise: Flashscore, Sofascore, API-Football, base de données locale
"""
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from models.match import Match, Prediction, BetType, Team
from config.settings import CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, CONFIDENCE_LOW
from services.data_enricher import DataEnricher, MatchEnrichedData, TeamStats

logger = logging.getLogger(__name__)


@dataclass
class EnhancedPrediction:
    """Prédiction enrichie avec tous les types de paris"""
    match_name: str
    league: str
    date: str

    # 1X2
    result_1x2: str
    home_prob: float
    draw_prob: float
    away_prob: float

    # Goals
    over_under: str
    over_25_prob: float
    total_expected_goals: float

    # Team +1.5
    team_plus_15: str

    # Corners
    corners: str
    expected_corners: float

    # Score exact
    score_exact: str
    score_prob: float

    # Clean sheet
    clean_sheet: str
    clean_sheet_prob: float

    # BTTS
    btts: str
    btts_prob: float

    # Double Chance + BTTS
    dc_btts: str

    # Mi-temps / Fin
    ht_ft: str

    # Confiance globale
    confidence: str
    reasoning: List[str]


class EnhancedMatchAnalyzer:
    """Analyseur amélioré avec données multi-sources"""

    def __init__(self):
        self.enricher = DataEnricher()
        self.home_advantage = 0.08

    def analyze_match_full(self, home_team: str, away_team: str,
                           league: str, match_date: str = "") -> EnhancedPrediction:
        """
        Analyse complète d'un match avec toutes les sources de données
        """
        logger.info(f"Enhanced analysis: {home_team} vs {away_team}")

        # Enrichir les données
        enriched = self.enricher.enrich_match(home_team, away_team, league)

        # Analyse détaillée
        analysis = self._compute_analysis(home_team, away_team, enriched)

        # Générer la prédiction
        return self._generate_prediction(
            home_team, away_team, league, match_date,
            enriched, analysis
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
        """Analyse détaillée des buts"""

        # Buts moyens par match
        home_scored = home.avg_goals_scored if home.avg_goals_scored > 0 else 1.4
        home_conceded = home.avg_goals_conceded if home.avg_goals_conceded > 0 else 1.1
        away_scored = away.avg_goals_scored if away.avg_goals_scored > 0 else 1.2
        away_conceded = away.avg_goals_conceded if away.avg_goals_conceded > 0 else 1.3

        # Si pas de données, utiliser le classement
        if home.league_position > 0:
            home_scored = 1.8 - (home.league_position - 1) * 0.05
            home_conceded = 0.8 + (home.league_position - 1) * 0.04
        if away.league_position > 0:
            away_scored = 1.5 - (away.league_position - 1) * 0.04
            away_conceded = 1.0 + (away.league_position - 1) * 0.05

        expected_home = (home_scored + away_conceded) / 2
        expected_away = (away_scored + home_conceded) / 2
        total_expected = expected_home + expected_away

        # Ajuster avec H2H
        if enriched.h2h_avg_goals > 0:
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
        """Calcule la probabilité d'over basée sur les buts attendus"""
        diff = expected - threshold
        prob = 0.50 + (diff * 0.20)
        return max(0.25, min(0.85, prob))

    def _calculate_btts_prob(self, home: TeamStats, away: TeamStats,
                             enriched: MatchEnrichedData) -> float:
        """Calcule la probabilité BTTS"""
        # Base sur le H2H
        base_prob = enriched.h2h_btts_percentage / 100 if enriched.h2h_btts_percentage else 0.50

        # Ajuster selon les clean sheets
        if home.clean_sheets > 3:
            base_prob -= 0.10
        if away.clean_sheets > 3:
            base_prob -= 0.10
        if home.failed_to_score > 3:
            base_prob -= 0.08
        if away.failed_to_score > 3:
            base_prob -= 0.08

        return max(0.30, min(0.80, base_prob))

    def _analyze_corners(self, home: TeamStats, away: TeamStats) -> Dict:
        """Analyse des corners"""
        # Récupérer les moyennes de corners si disponibles
        home_data = self.enricher._get_known_team_data(home.name, "")
        away_data = self.enricher._get_known_team_data(away.name, "")

        home_corners = home_data.get('avg_corners', 5.0)
        away_corners = away_data.get('avg_corners', 4.5)

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

        # 1X2
        if home_prob >= 0.50:
            result_1x2 = f"1 ({home_team})"
        elif away_prob >= 0.45:
            result_1x2 = f"2 ({away_team})"
        elif draw_prob >= 0.30:
            result_1x2 = "X (Nul)"
        else:
            result_1x2 = f"1 ({home_team})" if home_prob > away_prob else f"2 ({away_team})"

        # Over/Under - Format clair
        if goals["over_25_prob"] >= 0.55:
            over_under = "Over 2.5"
        elif goals["over_25_prob"] <= 0.40:
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

        # Score exact - Amélioration pour éviter trop de 1-1
        exp_home = goals["expected_home"]
        exp_away = goals["expected_away"]
        total_exp = goals["total_expected"]

        # Déterminer le score basé sur les probabilités et buts attendus
        if home_prob >= 0.55:
            # Victoire domicile nette
            if total_exp >= 3.0:
                score_exact = "3-1"
            elif total_exp >= 2.5:
                score_exact = "2-0"
            else:
                score_exact = "2-1"
            score_prob = 0.11
        elif away_prob >= 0.50:
            # Victoire extérieur
            if total_exp >= 3.0:
                score_exact = "1-3"
            elif total_exp >= 2.5:
                score_exact = "0-2"
            else:
                score_exact = "1-2"
            score_prob = 0.10
        elif home_prob > away_prob + 0.08:
            # Légère victoire domicile
            score_exact = "2-1"
            score_prob = 0.10
        elif away_prob > home_prob + 0.05:
            # Légère victoire extérieur
            score_exact = "1-2"
            score_prob = 0.09
        elif total_exp >= 2.8:
            # Match ouvert = nul avec buts
            score_exact = "2-2"
            score_prob = 0.08
        elif total_exp <= 2.0:
            # Match fermé
            score_exact = "1-0" if home_prob > away_prob else "0-1"
            score_prob = 0.10
        else:
            # Nul équilibré
            score_exact = "1-1"
            score_prob = 0.11

        # BTTS - Cohérent avec le score exact
        score_parts = score_exact.split("-")
        home_goals = int(score_parts[0])
        away_goals = int(score_parts[1])

        # Si le score prédit a les deux équipes qui marquent, BTTS = Oui
        if home_goals > 0 and away_goals > 0:
            btts = "Oui"
            btts_prob_final = max(goals["btts_prob"], 0.55)
        elif goals["btts_prob"] >= 0.55:
            btts = "Oui"
            btts_prob_final = goals["btts_prob"]
        else:
            btts = "Non"
            btts_prob_final = goals["btts_prob"]

        # Clean sheet - Cohérent avec BTTS et score
        if btts == "Non" and home_goals > 0 and away_goals == 0:
            clean_sheet = f"{home_team} gagne à 0"
            clean_sheet_prob = home_prob * 0.6
        elif btts == "Non" and away_goals > 0 and home_goals == 0:
            clean_sheet = f"{away_team} gagne à 0"
            clean_sheet_prob = away_prob * 0.5
        else:
            clean_sheet = "Non recommandé"
            clean_sheet_prob = 0.0

        # Double Chance + BTTS
        if home_prob > away_prob:
            dc_btts = "1X + BTTS Oui"
        else:
            dc_btts = "X2 + BTTS Oui"

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

        # Confiance
        max_prob = max(home_prob, draw_prob, away_prob)
        if max_prob >= 0.55:
            confidence = CONFIDENCE_HIGH
        elif max_prob >= 0.42:
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
            reasoning.append(f"Blessures {home_team}: {', '.join(home_stats.injuries)}")
        if away_stats.injuries:
            reasoning.append(f"Blessures {away_team}: {', '.join(away_stats.injuries)}")
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


# Instance globale
enhanced_analyzer = EnhancedMatchAnalyzer()
