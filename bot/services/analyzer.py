"""
Moteur d'analyse et de prédiction des matchs
"""
import logging
from typing import List, Dict, Tuple
from models.match import Match, Prediction, BetType, Team
from config.settings import CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, CONFIDENCE_LOW

logger = logging.getLogger(__name__)


class MatchAnalyzer:
    """Analyse les matchs et génère des prédictions"""

    # Poids pour les différents facteurs d'analyse
    WEIGHTS = {
        "form": 0.25,
        "h2h": 0.15,
        "home_advantage": 0.15,
        "standings": 0.20,
        "goals": 0.15,
        "motivation": 0.10
    }

    # Équipes connues avec estimation de force (1-100)
    KNOWN_TEAMS = {
        # Premier League
        "manchester city": 95, "arsenal": 90, "liverpool": 92, "chelsea": 85,
        "manchester united": 82, "tottenham": 80, "newcastle": 78, "aston villa": 75,
        "brighton": 72, "west ham": 70,
        # La Liga
        "real madrid": 95, "barcelona": 92, "atletico madrid": 85, "sevilla": 75,
        "real sociedad": 74, "villarreal": 73, "athletic bilbao": 72,
        # Serie A
        "inter": 90, "ac milan": 85, "juventus": 84, "napoli": 83, "roma": 78,
        "lazio": 76, "atalanta": 77, "fiorentina": 72,
        # Bundesliga
        "bayern munich": 94, "bayern": 94, "borussia dortmund": 85, "dortmund": 85,
        "rb leipzig": 82, "bayer leverkusen": 83, "leverkusen": 83,
        # Ligue 1
        "paris saint-germain": 92, "psg": 92, "marseille": 78, "monaco": 76, "lyon": 74,
        # Saudi Pro League
        "al-hilal": 88, "al-nassr": 86, "al-ittihad": 82, "al-ahli": 80,
        # Other big teams
        "benfica": 80, "porto": 79, "sporting": 77, "ajax": 76, "psv": 75,
        "galatasaray": 77, "fenerbahce": 76, "besiktas": 74,
    }

    # Ligues offensives (plus de buts en moyenne)
    OFFENSIVE_LEAGUES = {78, 79, 88, 89}  # Bundesliga, Eredivisie
    DEFENSIVE_LEAGUES = {135, 136}  # Serie A

    def __init__(self):
        self.home_advantage_factor = 0.08  # 8% d'avantage à domicile

    def _get_team_strength(self, team_name: str) -> int:
        """Estime la force d'une équipe basée sur son nom"""
        name_lower = team_name.lower()
        for known, strength in self.KNOWN_TEAMS.items():
            if known in name_lower or name_lower in known:
                return strength
        return 60  # Force par défaut pour équipes inconnues

    def analyze_match(self, match: Match) -> Dict:
        """
        Analyse complète d'un match
        Retourne les probabilités et recommandations
        """
        logger.info(f"Analyzing: {match}")

        # Estimer la force des équipes si données insuffisantes
        home_strength = self._get_team_strength(match.home_team.name)
        away_strength = self._get_team_strength(match.away_team.name)
        strength_diff = (home_strength - away_strength) / 100  # Entre -1 et 1

        # Calculer les scores pour chaque facteur
        form_score = self._analyze_form(match)
        h2h_score = self._analyze_h2h(match)
        home_adv_score = self._analyze_home_advantage(match)
        standings_score = self._analyze_standings(match)
        goals_analysis = self._analyze_goals(match, home_strength, away_strength)
        motivation_score = self._analyze_motivation(match)

        # Si pas assez de données, utiliser l'estimation de force
        if form_score == 0 and standings_score == 0:
            form_score = strength_diff * 0.5  # Simuler la forme basée sur la force

        # Score final pondéré (positif = avantage domicile, négatif = avantage extérieur)
        weighted_score = (
            form_score * self.WEIGHTS["form"] +
            h2h_score * self.WEIGHTS["h2h"] +
            home_adv_score * self.WEIGHTS["home_advantage"] +
            standings_score * self.WEIGHTS["standings"] +
            motivation_score * self.WEIGHTS["motivation"] +
            strength_diff * 0.25  # Bonus basé sur force estimée
        )

        # Convertir en probabilités
        home_prob, draw_prob, away_prob = self._score_to_probabilities(weighted_score)

        return {
            "match": match,
            "home_win_prob": home_prob,
            "draw_prob": draw_prob,
            "away_win_prob": away_prob,
            "over_2_5_prob": goals_analysis["over_2_5_prob"],
            "btts_prob": goals_analysis["btts_prob"],
            "corners_prob": goals_analysis["high_corners_prob"],
            "form_score": form_score,
            "h2h_score": h2h_score,
            "standings_score": standings_score,
            "weighted_score": weighted_score,
            "goals_analysis": goals_analysis,
            "home_strength": home_strength,
            "away_strength": away_strength
        }

    def _analyze_form(self, match: Match) -> float:
        """
        Analyse la forme récente des équipes
        Retourne un score entre -1 (extérieur domine) et 1 (domicile domine)
        """
        home_form_score = self._form_to_score(match.home_team.form)
        away_form_score = self._form_to_score(match.away_team.form)

        # Différentiel de forme
        diff = home_form_score - away_form_score
        return max(-1, min(1, diff / 10))

    def _form_to_score(self, form: str) -> float:
        """Convertit une chaîne de forme (ex: WWDLW) en score numérique"""
        if not form:
            return 0

        score = 0
        weights = [1.5, 1.3, 1.1, 0.9, 0.7]  # Plus récent = plus important

        for i, result in enumerate(form[:5]):
            weight = weights[i] if i < len(weights) else 0.5
            if result == "W":
                score += 3 * weight
            elif result == "D":
                score += 1 * weight
            # L = 0

        return score

    def _analyze_h2h(self, match: Match) -> float:
        """Analyse l'historique des confrontations"""
        if match.h2h_total_games == 0:
            return 0

        # Calculer le ratio de victoires
        home_ratio = match.h2h_home_wins / match.h2h_total_games
        away_ratio = match.h2h_away_wins / match.h2h_total_games

        return (home_ratio - away_ratio)

    def _analyze_home_advantage(self, match: Match) -> float:
        """Analyse l'avantage à domicile"""
        # Base: 8% d'avantage à domicile
        base_advantage = self.home_advantage_factor

        # Ajuster selon les performances dom/ext
        home_record = match.home_team.home_wins - match.home_team.home_losses
        away_record = match.away_team.away_wins - match.away_team.away_losses

        # Normaliser
        home_strength = home_record * 0.05
        away_weakness = away_record * 0.05

        return base_advantage + home_strength - away_weakness

    def _analyze_standings(self, match: Match) -> float:
        """Analyse les positions au classement"""
        if match.home_team.league_position == 0 or match.away_team.league_position == 0:
            return 0

        # Différence de position (inversée car position 1 > position 20)
        position_diff = match.away_team.league_position - match.home_team.league_position

        # Points différentiel
        points_diff = match.home_team.league_points - match.away_team.league_points

        # Combiner position et points
        combined = (position_diff / 20) * 0.6 + (points_diff / 50) * 0.4
        return max(-1, min(1, combined))

    def _analyze_goals(self, match: Match, home_strength: int = 60, away_strength: int = 60) -> Dict:
        """Analyse les tendances de buts"""
        # Moyennes des 5 derniers matchs
        home_scored_avg = match.home_team.goals_scored_last_5 / 5 if match.home_team.goals_scored_last_5 else 0
        home_conceded_avg = match.home_team.goals_conceded_last_5 / 5 if match.home_team.goals_conceded_last_5 else 0
        away_scored_avg = match.away_team.goals_scored_last_5 / 5 if match.away_team.goals_scored_last_5 else 0
        away_conceded_avg = match.away_team.goals_conceded_last_5 / 5 if match.away_team.goals_conceded_last_5 else 0

        # Si pas de données, estimer basé sur la force et la ligue
        if home_scored_avg == 0 and away_scored_avg == 0:
            # Estimer les buts basé sur la force des équipes
            home_scored_avg = 1.2 + (home_strength - 60) / 50  # 1.0 - 1.9
            away_scored_avg = 1.0 + (away_strength - 60) / 50  # 0.8 - 1.7
            home_conceded_avg = 1.2 - (home_strength - 60) / 100
            away_conceded_avg = 1.2 - (away_strength - 60) / 100

            # Ajuster selon la ligue
            if match.league_id in self.OFFENSIVE_LEAGUES:
                home_scored_avg += 0.3
                away_scored_avg += 0.3
            elif match.league_id in self.DEFENSIVE_LEAGUES:
                home_scored_avg -= 0.2
                away_scored_avg -= 0.2

        # Estimation du nombre de buts attendu
        expected_home_goals = (home_scored_avg + away_conceded_avg) / 2
        expected_away_goals = (away_scored_avg + home_conceded_avg) / 2
        total_expected = expected_home_goals + expected_away_goals

        # H2H average
        if match.h2h_avg_goals > 0:
            total_expected = (total_expected + match.h2h_avg_goals) / 2

        # Probabilité Over 2.5
        if total_expected >= 3.0:
            over_2_5_prob = 0.70
        elif total_expected >= 2.5:
            over_2_5_prob = 0.58
        elif total_expected >= 2.2:
            over_2_5_prob = 0.50
        elif total_expected >= 2.0:
            over_2_5_prob = 0.45
        else:
            over_2_5_prob = 0.38

        # Probabilité BTTS - basée sur la force relative
        strength_diff = abs(home_strength - away_strength)
        if strength_diff < 10:
            # Match équilibré, BTTS plus probable
            btts_prob = 0.55
        elif strength_diff < 20:
            btts_prob = 0.50
        else:
            # Grande différence, une équipe peut ne pas marquer
            btts_prob = 0.40

        # Ajuster avec les données si disponibles
        if home_scored_avg > 0:
            home_scores = home_scored_avg >= 1.0
            home_concedes = home_conceded_avg >= 0.8
            away_scores = away_scored_avg >= 1.0
            away_concedes = away_conceded_avg >= 0.8
            btts_factors = sum([home_scores, home_concedes, away_scores, away_concedes])
            btts_prob = 0.35 + (btts_factors * 0.12)

        return {
            "expected_home_goals": expected_home_goals,
            "expected_away_goals": expected_away_goals,
            "total_expected_goals": total_expected,
            "over_2_5_prob": min(0.85, max(0.35, over_2_5_prob)),
            "btts_prob": min(0.80, max(0.35, btts_prob)),
            "high_corners_prob": 0.50 + (home_strength + away_strength - 120) / 200
        }

    def _analyze_motivation(self, match: Match) -> float:
        """Analyse la motivation des équipes (enjeux du match)"""
        home_motivation = 0
        away_motivation = 0

        # Top du classement = titre en jeu
        if match.home_team.league_position <= 3:
            home_motivation += 0.2
        if match.away_team.league_position <= 3:
            away_motivation += 0.2

        # Bas du classement = relégation
        if match.home_team.league_position >= 17:
            home_motivation += 0.15
        if match.away_team.league_position >= 17:
            away_motivation += 0.15

        return home_motivation - away_motivation

    def _score_to_probabilities(self, score: float) -> Tuple[float, float, float]:
        """
        Convertit un score pondéré en probabilités 1X2
        Score positif = avantage domicile
        Score négatif = avantage extérieur
        """
        # Base probabilities
        base_home = 0.40
        base_draw = 0.25
        base_away = 0.35

        # Ajuster selon le score
        adjustment = score * 0.30  # Max ±30% adjustment

        home_prob = base_home + adjustment
        away_prob = base_away - adjustment
        draw_prob = 1 - home_prob - away_prob

        # Normaliser pour s'assurer que le total = 1
        home_prob = max(0.10, min(0.80, home_prob))
        away_prob = max(0.10, min(0.80, away_prob))
        draw_prob = max(0.10, min(0.40, draw_prob))

        total = home_prob + draw_prob + away_prob
        return home_prob / total, draw_prob / total, away_prob / total

    def generate_predictions(self, match: Match) -> List[Prediction]:
        """Génère toutes les prédictions possibles pour un match"""
        analysis = self.analyze_match(match)
        predictions = []

        # 1X2 Predictions
        predictions.extend(self._generate_1x2_predictions(match, analysis))

        # Over/Under Predictions
        predictions.extend(self._generate_goals_predictions(match, analysis))

        # BTTS Predictions
        predictions.extend(self._generate_btts_predictions(match, analysis))

        # Double Chance Predictions
        predictions.extend(self._generate_double_chance_predictions(match, analysis))

        # Combo Predictions
        predictions.extend(self._generate_combo_predictions(match, analysis))

        # Trier par confiance
        predictions.sort(key=lambda p: {"ÉLEVÉ": 3, "MOYEN": 2, "FAIBLE": 1}.get(p.confidence, 0), reverse=True)

        return predictions

    def _generate_1x2_predictions(self, match: Match, analysis: Dict) -> List[Prediction]:
        """Génère les prédictions 1X2"""
        predictions = []

        home_prob = analysis["home_win_prob"]
        draw_prob = analysis["draw_prob"]
        away_prob = analysis["away_win_prob"]

        # Victoire domicile
        if home_prob >= 0.55:
            confidence = CONFIDENCE_HIGH if home_prob >= 0.65 else CONFIDENCE_MEDIUM
            reasoning = self._build_reasoning(match, "home", analysis)
            predictions.append(Prediction(
                match=match,
                bet_type=BetType.HOME_WIN,
                confidence=confidence,
                odds_estimate=round(1 / home_prob, 2),
                reasoning=reasoning,
                home_win_probability=home_prob,
                draw_probability=draw_prob,
                away_win_probability=away_prob
            ))

        # Victoire extérieur
        if away_prob >= 0.50:
            confidence = CONFIDENCE_HIGH if away_prob >= 0.60 else CONFIDENCE_MEDIUM
            reasoning = self._build_reasoning(match, "away", analysis)
            predictions.append(Prediction(
                match=match,
                bet_type=BetType.AWAY_WIN,
                confidence=confidence,
                odds_estimate=round(1 / away_prob, 2),
                reasoning=reasoning,
                home_win_probability=home_prob,
                draw_probability=draw_prob,
                away_win_probability=away_prob
            ))

        # Nul (moins fréquent mais possible)
        if draw_prob >= 0.32:
            predictions.append(Prediction(
                match=match,
                bet_type=BetType.DRAW,
                confidence=CONFIDENCE_MEDIUM if draw_prob >= 0.38 else CONFIDENCE_LOW,
                odds_estimate=round(1 / draw_prob, 2),
                reasoning=f"Match équilibré, les deux équipes ont des forces similaires",
                home_win_probability=home_prob,
                draw_probability=draw_prob,
                away_win_probability=away_prob
            ))

        return predictions

    def _generate_goals_predictions(self, match: Match, analysis: Dict) -> List[Prediction]:
        """Génère les prédictions Over/Under"""
        predictions = []
        goals = analysis["goals_analysis"]
        over_prob = analysis["over_2_5_prob"]

        if over_prob >= 0.55:
            confidence = CONFIDENCE_HIGH if over_prob >= 0.65 else CONFIDENCE_MEDIUM
            reasoning = f"Moyenne de {goals['total_expected_goals']:.1f} buts attendus. H2H: {match.h2h_avg_goals:.1f} buts/match"
            predictions.append(Prediction(
                match=match,
                bet_type=BetType.OVER_2_5,
                confidence=confidence,
                odds_estimate=round(1 / over_prob, 2),
                reasoning=reasoning,
                over_2_5_probability=over_prob
            ))

        # Over 1.5 (plus sûr)
        over_1_5_prob = min(0.85, over_prob + 0.20)
        if over_1_5_prob >= 0.75:
            predictions.append(Prediction(
                match=match,
                bet_type=BetType.OVER_1_5,
                confidence=CONFIDENCE_HIGH,
                odds_estimate=round(1 / over_1_5_prob, 2),
                reasoning=f"Au moins 2 buts très probable dans ce match",
                over_2_5_probability=over_prob
            ))

        # Under 2.5
        under_prob = 1 - over_prob
        if under_prob >= 0.55:
            predictions.append(Prediction(
                match=match,
                bet_type=BetType.UNDER_2_5,
                confidence=CONFIDENCE_MEDIUM if under_prob >= 0.60 else CONFIDENCE_LOW,
                odds_estimate=round(1 / under_prob, 2),
                reasoning=f"Match défensif attendu, faible moyenne de buts",
                over_2_5_probability=over_prob
            ))

        return predictions

    def _generate_btts_predictions(self, match: Match, analysis: Dict) -> List[Prediction]:
        """Génère les prédictions BTTS"""
        predictions = []
        btts_prob = analysis["btts_prob"]

        if btts_prob >= 0.55:
            confidence = CONFIDENCE_HIGH if btts_prob >= 0.65 else CONFIDENCE_MEDIUM
            reasoning = f"Les deux équipes ont tendance à marquer et à encaisser"
            predictions.append(Prediction(
                match=match,
                bet_type=BetType.BTTS_YES,
                confidence=confidence,
                odds_estimate=round(1 / btts_prob, 2),
                reasoning=reasoning,
                btts_probability=btts_prob
            ))

        # BTTS Non
        btts_no_prob = 1 - btts_prob
        if btts_no_prob >= 0.50:
            predictions.append(Prediction(
                match=match,
                bet_type=BetType.BTTS_NO,
                confidence=CONFIDENCE_MEDIUM if btts_no_prob >= 0.55 else CONFIDENCE_LOW,
                odds_estimate=round(1 / btts_no_prob, 2),
                reasoning=f"Une équipe devrait garder sa cage inviolée",
                btts_probability=btts_prob
            ))

        return predictions

    def _generate_double_chance_predictions(self, match: Match, analysis: Dict) -> List[Prediction]:
        """Génère les prédictions Double Chance"""
        predictions = []

        home_prob = analysis["home_win_prob"]
        draw_prob = analysis["draw_prob"]
        away_prob = analysis["away_win_prob"]

        # 1X (Domicile ou Nul)
        dc_1x_prob = home_prob + draw_prob
        if dc_1x_prob >= 0.70 and home_prob >= 0.40:
            confidence = CONFIDENCE_HIGH if dc_1x_prob >= 0.80 else CONFIDENCE_MEDIUM
            predictions.append(Prediction(
                match=match,
                bet_type=BetType.DOUBLE_CHANCE_1X,
                confidence=confidence,
                odds_estimate=round(1 / dc_1x_prob, 2),
                reasoning=f"Le domicile ne devrait pas perdre ce match",
                home_win_probability=home_prob,
                draw_probability=draw_prob,
                away_win_probability=away_prob
            ))

        # X2 (Nul ou Extérieur)
        dc_x2_prob = draw_prob + away_prob
        if dc_x2_prob >= 0.65 and away_prob >= 0.35:
            confidence = CONFIDENCE_HIGH if dc_x2_prob >= 0.75 else CONFIDENCE_MEDIUM
            predictions.append(Prediction(
                match=match,
                bet_type=BetType.DOUBLE_CHANCE_X2,
                confidence=confidence,
                odds_estimate=round(1 / dc_x2_prob, 2),
                reasoning=f"L'extérieur a de bonnes chances de ne pas perdre",
                home_win_probability=home_prob,
                draw_probability=draw_prob,
                away_win_probability=away_prob
            ))

        return predictions

    def _generate_combo_predictions(self, match: Match, analysis: Dict) -> List[Prediction]:
        """Génère les prédictions combinées"""
        predictions = []

        home_prob = analysis["home_win_prob"]
        over_prob = analysis["over_2_5_prob"]
        btts_prob = analysis["btts_prob"]

        # Victoire domicile + Over 1.5
        if home_prob >= 0.55 and over_prob >= 0.50:
            combo_prob = home_prob * 0.85  # Estimation
            predictions.append(Prediction(
                match=match,
                bet_type=BetType.HOME_WIN_AND_OVER_1_5,
                confidence=CONFIDENCE_MEDIUM if combo_prob >= 0.45 else CONFIDENCE_LOW,
                odds_estimate=round(1 / combo_prob, 2),
                reasoning=f"Victoire domicile avec au moins 2 buts dans le match"
            ))

        # BTTS + Over 2.5
        if btts_prob >= 0.55 and over_prob >= 0.55:
            combo_prob = btts_prob * over_prob
            if combo_prob >= 0.35:
                predictions.append(Prediction(
                    match=match,
                    bet_type=BetType.BTTS_AND_OVER_2_5,
                    confidence=CONFIDENCE_MEDIUM,
                    odds_estimate=round(1 / combo_prob, 2),
                    reasoning=f"Match ouvert avec buts des deux côtés"
                ))

        return predictions

    def _build_reasoning(self, match: Match, winner: str, analysis: Dict) -> str:
        """Construit l'argumentaire pour une prédiction"""
        reasons = []

        if winner == "home":
            team = match.home_team
            opp = match.away_team
            prefix = "Le domicile"
        else:
            team = match.away_team
            opp = match.home_team
            prefix = "L'extérieur"

        # Forme
        wins = team.wins_last_5
        if wins >= 4:
            reasons.append(f"excellente forme ({wins}V sur 5)")
        elif wins >= 3:
            reasons.append(f"bonne forme ({wins}V sur 5)")

        # Position
        if team.league_position > 0 and opp.league_position > 0:
            if team.league_position < opp.league_position - 5:
                reasons.append(f"mieux classé ({team.league_position}e vs {opp.league_position}e)")

        # H2H
        if winner == "home" and match.h2h_home_wins > match.h2h_away_wins:
            reasons.append(f"domine les H2H ({match.h2h_home_wins}V)")
        elif winner == "away" and match.h2h_away_wins > match.h2h_home_wins:
            reasons.append(f"domine les H2H ({match.h2h_away_wins}V)")

        if reasons:
            return f"{prefix}: {', '.join(reasons)}"
        return f"{prefix} favori selon notre analyse"

    def get_best_prediction(self, match: Match) -> Prediction:
        """Retourne la meilleure prédiction pour un match"""
        predictions = self.generate_predictions(match)
        if predictions:
            return predictions[0]
        # Fallback
        return Prediction(
            match=match,
            bet_type=BetType.OVER_1_5,
            confidence=CONFIDENCE_LOW,
            odds_estimate=1.30,
            reasoning="Prédiction par défaut - données insuffisantes"
        )
