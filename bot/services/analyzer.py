"""
Moteur d'analyse et de prédiction des matchs
Version 2.0 - Améliorations basées sur l'analyse du 11/01/2026
"""
import logging
from typing import List, Dict, Tuple, Optional
from models.match import Match, Prediction, BetType, Team
from config.settings import CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, CONFIDENCE_LOW
from config.league_config import get_league_config

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
        self._elo_service = None

    def _get_elo_service(self):
        """Récupère le service Elo (lazy loading)"""
        if self._elo_service is None:
            try:
                from services.elo_service import get_elo_service
                self._elo_service = get_elo_service()
            except ImportError:
                pass
        return self._elo_service

    def _get_team_strength(self, team_name: str, team_id: int = 0, league_id: int = 0) -> int:
        """
        Estime la force d'une équipe

        Priorité:
        1. Service Elo (si disponible et team_id fourni)
        2. KNOWN_TEAMS (fallback statique)
        3. Valeur par défaut (60)
        """
        # Essayer le service Elo d'abord
        elo_service = self._get_elo_service()
        if elo_service and team_id:
            elo_rating = elo_service.get_team_rating_sync(team_id, team_name, league_id)
            if elo_rating != 1500:  # Si pas la valeur par défaut
                strength = elo_service.elo_to_strength(elo_rating)
                logger.debug(f"[ELO] {team_name}: Elo={elo_rating:.0f} → Strength={strength}")
                return strength

        # Fallback: KNOWN_TEAMS statique
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

        # Estimer la force des équipes (priorité: Elo > KNOWN_TEAMS > défaut)
        home_strength = self._get_team_strength(
            match.home_team.name,
            team_id=match.home_team.id,
            league_id=match.league_id
        )
        away_strength = self._get_team_strength(
            match.away_team.name,
            team_id=match.away_team.id,
            league_id=match.league_id
        )
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
        Analyse la forme récente des équipes - VERSION 2.0
        Retourne un score entre -1 (extérieur domine) et 1 (domicile domine)

        Amélioration: Prend en compte la forme SPÉCIFIQUE dom/ext
        """
        # Forme générale
        home_form_score = self._form_to_score(match.home_team.form)
        away_form_score = self._form_to_score(match.away_team.form)

        # ===== NOUVEAU: Forme spécifique domicile/extérieur =====
        home_specific_score = self._analyze_home_away_specific_form(match.home_team, is_home=True)
        away_specific_score = self._analyze_home_away_specific_form(match.away_team, is_home=False)

        # Combiner forme générale (60%) et forme spécifique (40%)
        home_combined = (home_form_score * 0.6) + (home_specific_score * 0.4)
        away_combined = (away_form_score * 0.6) + (away_specific_score * 0.4)

        # Différentiel de forme
        diff = home_combined - away_combined
        return max(-1, min(1, diff / 10))

    def _analyze_home_away_specific_form(self, team: Team, is_home: bool) -> float:
        """
        Analyse la forme spécifique à domicile ou à l'extérieur

        Args:
            team: L'équipe à analyser
            is_home: True si l'équipe joue à domicile

        Returns:
            Score de forme spécifique (0-15)
        """
        if is_home:
            # Performance à domicile
            wins = team.home_wins if team.home_wins else 0
            draws = team.home_draws if team.home_draws else 0
            losses = team.home_losses if team.home_losses else 0
        else:
            # Performance à l'extérieur
            wins = team.away_wins if team.away_wins else 0
            draws = team.away_draws if team.away_draws else 0
            losses = team.away_losses if team.away_losses else 0

        total = wins + draws + losses
        if total == 0:
            return 7.5  # Score neutre

        # Calculer le score basé sur les résultats
        score = (wins * 3 + draws * 1) / total * 5

        # Bonus/malus selon le ratio victoires
        win_ratio = wins / total if total > 0 else 0
        if win_ratio >= 0.6:
            score += 3  # Très forte performance
        elif win_ratio >= 0.4:
            score += 1
        elif win_ratio < 0.2:
            score -= 2  # Très faible performance

        return max(0, min(15, score))

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
        """Analyse les tendances de buts - VERSION 2.0 avec filtres améliorés"""

        # Récupérer la config de la ligue
        league_config = get_league_config(match.league_id)

        # Moyennes des 5 derniers matchs
        home_scored_avg = match.home_team.goals_scored_last_5 / 5 if match.home_team.goals_scored_last_5 else 0
        home_conceded_avg = match.home_team.goals_conceded_last_5 / 5 if match.home_team.goals_conceded_last_5 else 0
        away_scored_avg = match.away_team.goals_scored_last_5 / 5 if match.away_team.goals_scored_last_5 else 0
        away_conceded_avg = match.away_team.goals_conceded_last_5 / 5 if match.away_team.goals_conceded_last_5 else 0

        # Si pas de données, estimer basé sur la force et la ligue
        if home_scored_avg == 0 and away_scored_avg == 0:
            league_avg = league_config.get("avg_goals_per_match", 2.5) / 2
            home_scored_avg = league_avg + (home_strength - 60) / 80
            away_scored_avg = league_avg * 0.85 + (away_strength - 60) / 80
            home_conceded_avg = league_avg - (home_strength - 60) / 100
            away_conceded_avg = league_avg - (away_strength - 60) / 100

            # Ajuster selon le style de la ligue
            style = league_config.get("style", "balanced")
            if style == "attacking":
                home_scored_avg += 0.2
                away_scored_avg += 0.2
            elif style == "defensive":
                home_scored_avg -= 0.15
                away_scored_avg -= 0.15

        # Estimation du nombre de buts attendu
        expected_home_goals = (home_scored_avg + away_conceded_avg) / 2
        expected_away_goals = (away_scored_avg + home_conceded_avg) / 2
        total_expected = expected_home_goals + expected_away_goals

        # H2H average
        if match.h2h_avg_goals > 0:
            total_expected = (total_expected * 0.6) + (match.h2h_avg_goals * 0.4)

        # ========== PROBABILITÉ OVER 2.5 - AJUSTÉE PAR LIGUE ==========
        league_avg_goals = league_config.get("avg_goals_per_match", 2.5)

        if total_expected >= 3.2:
            over_2_5_prob = 0.72
        elif total_expected >= 2.8:
            over_2_5_prob = 0.62
        elif total_expected >= 2.5:
            over_2_5_prob = 0.52
        elif total_expected >= 2.2:
            over_2_5_prob = 0.45
        else:
            over_2_5_prob = 0.38

        # Ajuster selon la moyenne de la ligue
        if league_avg_goals < 2.4:  # Ligue défensive
            over_2_5_prob -= 0.08
        elif league_avg_goals > 2.9:  # Ligue offensive
            over_2_5_prob += 0.05

        # ========== PROBABILITÉ BTTS - VERSION 2.0 ==========
        strength_diff = abs(home_strength - away_strength)
        position_diff = abs(match.home_team.league_position - match.away_team.league_position) if match.home_team.league_position > 0 and match.away_team.league_position > 0 else 0

        # ===== NOUVEAU: Détection des équipes à clean sheet =====
        home_clean_sheet_rate = self._estimate_clean_sheet_rate(match.home_team, home_strength)
        away_clean_sheet_rate = self._estimate_clean_sheet_rate(match.away_team, away_strength)

        clean_sheet_threshold = league_config.get("thresholds", {}).get("clean_sheet_threshold", 0.30)
        high_clean_sheet_risk = home_clean_sheet_rate > clean_sheet_threshold or away_clean_sheet_rate > clean_sheet_threshold

        # ===== Détection match déséquilibré =====
        is_heavily_unbalanced = False
        if (home_strength >= 85 and away_strength <= 65) or \
           (away_strength >= 85 and home_strength <= 65) or \
           position_diff >= 12:
            is_heavily_unbalanced = True
            logger.info(f"[BTTS] Match déséquilibré: force {home_strength} vs {away_strength}, diff position: {position_diff}")

        # Calcul de base BTTS
        if strength_diff < 8:
            btts_prob = 0.58
        elif strength_diff < 15:
            btts_prob = 0.52
        elif strength_diff < 25:
            btts_prob = 0.42
        else:
            btts_prob = 0.32

        # ===== NOUVEAU: Malus pour clean sheet risk =====
        if high_clean_sheet_risk:
            btts_prob -= 0.12
            logger.info(f"[BTTS] Malus clean sheet: home={home_clean_sheet_rate:.0%}, away={away_clean_sheet_rate:.0%}")

        # Malus pour match déséquilibré
        if is_heavily_unbalanced:
            btts_prob -= 0.15
            logger.info(f"[BTTS] Malus match déséquilibré")

        # ===== NOUVEAU: Vérifier si une équipe marque peu =====
        if home_scored_avg < 0.8 or away_scored_avg < 0.6:
            btts_prob -= 0.10
            logger.info(f"[BTTS] Malus équipe peu offensive: home={home_scored_avg:.1f}, away={away_scored_avg:.1f}")

        # Ajuster avec les données si disponibles
        if home_scored_avg > 0:
            home_scores = home_scored_avg >= 1.2
            home_concedes = home_conceded_avg >= 1.0
            away_scores = away_scored_avg >= 1.0
            away_concedes = away_conceded_avg >= 1.0
            btts_factors = sum([home_scores, home_concedes, away_scores, away_concedes])

            if is_heavily_unbalanced or high_clean_sheet_risk:
                btts_prob = min(btts_prob, 0.32 + (btts_factors * 0.06))
            else:
                btts_prob = max(btts_prob, 0.35 + (btts_factors * 0.10))

        return {
            "expected_home_goals": expected_home_goals,
            "expected_away_goals": expected_away_goals,
            "total_expected_goals": total_expected,
            "over_2_5_prob": min(0.80, max(0.32, over_2_5_prob)),
            "btts_prob": min(0.75, max(0.25, btts_prob)),
            "high_corners_prob": 0.50 + (home_strength + away_strength - 120) / 200,
            "home_clean_sheet_rate": home_clean_sheet_rate,
            "away_clean_sheet_rate": away_clean_sheet_rate,
            "is_heavily_unbalanced": is_heavily_unbalanced,
            "high_clean_sheet_risk": high_clean_sheet_risk
        }

    def _estimate_clean_sheet_rate(self, team: Team, strength: int) -> float:
        """Estime le taux de clean sheet d'une équipe"""
        # Si on a des données de buts encaissés
        if team.goals_conceded_last_5 is not None and team.goals_conceded_last_5 >= 0:
            avg_conceded = team.goals_conceded_last_5 / 5
            if avg_conceded < 0.6:
                return 0.45  # Très défensif
            elif avg_conceded < 0.9:
                return 0.35
            elif avg_conceded < 1.2:
                return 0.25
            else:
                return 0.15

        # Estimation basée sur la force
        if strength >= 85:
            return 0.38
        elif strength >= 75:
            return 0.28
        elif strength >= 65:
            return 0.22
        else:
            return 0.18

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
        """Génère les prédictions 1X2 - VERSION 2.0 avec filtre de confiance

        Amélioration: Ne prédit que si la probabilité max dépasse un seuil minimum (45%)
        pour éviter les prédictions incertaines.
        """
        predictions = []

        home_prob = analysis["home_win_prob"]
        draw_prob = analysis["draw_prob"]
        away_prob = analysis["away_win_prob"]

        # Récupérer la config de la ligue
        league_config = get_league_config(match.league_id)
        thresholds = league_config.get("thresholds", {})
        min_confidence = thresholds.get("min_1x2_confidence", 0.45)
        draw_threshold = thresholds.get("draw_threshold", 0.08)

        # ========== FILTRE DE CONFIANCE ==========
        max_prob = max(home_prob, draw_prob, away_prob)
        if max_prob < min_confidence:
            logger.info(f"[1X2] Match trop incertain: max_prob={max_prob:.0%} < {min_confidence:.0%}")
            # Ne pas faire de prédiction 1X2 si trop incertain
            return predictions

        # ========== VICTOIRE DOMICILE ==========
        # Vérifier que home_prob est significativement supérieur aux autres
        if home_prob >= 0.52 and (home_prob - draw_prob) >= draw_threshold:
            confidence = CONFIDENCE_HIGH if home_prob >= 0.62 else CONFIDENCE_MEDIUM
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

        # ========== VICTOIRE EXTÉRIEUR ==========
        # Seuil plus strict pour victoire extérieur (plus difficile)
        if away_prob >= 0.48 and (away_prob - draw_prob) >= draw_threshold:
            confidence = CONFIDENCE_HIGH if away_prob >= 0.58 else CONFIDENCE_MEDIUM
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

        # ========== NUL ==========
        # Prédire nul seulement si c'est vraiment le résultat le plus probable
        # ou si home/away sont très proches
        home_away_diff = abs(home_prob - away_prob)
        if draw_prob >= 0.32 and home_away_diff < 0.10:
            confidence = CONFIDENCE_MEDIUM if draw_prob >= 0.36 else CONFIDENCE_LOW
            predictions.append(Prediction(
                match=match,
                bet_type=BetType.DRAW,
                confidence=confidence,
                odds_estimate=round(1 / draw_prob, 2),
                reasoning=f"Match très équilibré (dom {home_prob:.0%} vs ext {away_prob:.0%})",
                home_win_probability=home_prob,
                draw_probability=draw_prob,
                away_win_probability=away_prob
            ))

        return predictions

    def _generate_goals_predictions(self, match: Match, analysis: Dict) -> List[Prediction]:
        """Génère les prédictions Over/Under - VERSION 2.0 avec seuils par ligue"""
        predictions = []
        goals = analysis["goals_analysis"]
        over_prob = analysis["over_2_5_prob"]

        # Récupérer les seuils de la ligue
        league_config = get_league_config(match.league_id)
        thresholds = league_config.get("thresholds", {})
        over_25_threshold = thresholds.get("over_25", 0.58)
        under_25_threshold = thresholds.get("under_25", 0.42)

        # ========== OVER 2.5 ==========
        if over_prob >= over_25_threshold:
            confidence = CONFIDENCE_HIGH if over_prob >= 0.65 else CONFIDENCE_MEDIUM
            h2h_info = f"H2H: {match.h2h_avg_goals:.1f} buts/match" if match.h2h_avg_goals > 0 else ""
            reasoning = f"Moyenne de {goals['total_expected_goals']:.1f} buts attendus. {h2h_info}"
            predictions.append(Prediction(
                match=match,
                bet_type=BetType.OVER_2_5,
                confidence=confidence,
                odds_estimate=round(1 / over_prob, 2),
                reasoning=reasoning.strip(),
                over_2_5_probability=over_prob
            ))

        # ========== OVER 1.5 (plus sûr) ==========
        over_1_5_prob = min(0.88, over_prob + 0.22)
        if over_1_5_prob >= 0.78:
            predictions.append(Prediction(
                match=match,
                bet_type=BetType.OVER_1_5,
                confidence=CONFIDENCE_HIGH,
                odds_estimate=round(1 / over_1_5_prob, 2),
                reasoning=f"Au moins 2 buts très probable ({over_1_5_prob:.0%})",
                over_2_5_probability=over_prob
            ))

        # ========== UNDER 2.5 ==========
        under_prob = 1 - over_prob

        # Utiliser le seuil inverse: si over_prob < under_25_threshold, recommander Under
        if over_prob <= under_25_threshold or under_prob >= 0.58:
            if under_prob >= 0.62:
                confidence = CONFIDENCE_HIGH
            elif under_prob >= 0.55:
                confidence = CONFIDENCE_MEDIUM
            else:
                confidence = CONFIDENCE_LOW

            league_style = league_config.get("style", "balanced")
            if league_style == "defensive":
                reasoning = f"Ligue défensive, match fermé attendu ({under_prob:.0%})"
            else:
                reasoning = f"Match défensif attendu ({under_prob:.0%})"

            predictions.append(Prediction(
                match=match,
                bet_type=BetType.UNDER_2_5,
                confidence=confidence,
                odds_estimate=round(1 / under_prob, 2),
                reasoning=reasoning,
                over_2_5_probability=over_prob
            ))

        return predictions

    def _generate_btts_predictions(self, match: Match, analysis: Dict) -> List[Prediction]:
        """Génère les prédictions BTTS - VERSION 2.0 avec filtres stricts

        Améliorations basées sur l'analyse du 11/01/2026:
        - Seuil BTTS Oui augmenté à 0.62 (configurable par ligue)
        - Filtre clean sheet
        - Filtre match déséquilibré
        """
        predictions = []
        btts_prob = analysis["btts_prob"]
        goals_analysis = analysis.get("goals_analysis", {})

        # Récupérer la config de la ligue
        league_config = get_league_config(match.league_id)
        thresholds = league_config.get("thresholds", {})

        # ========== RÉCUPÉRER LES INDICATEURS ==========
        home_strength = analysis.get("home_strength", 60)
        away_strength = analysis.get("away_strength", 60)
        is_heavily_unbalanced = goals_analysis.get("is_heavily_unbalanced", False)
        high_clean_sheet_risk = goals_analysis.get("high_clean_sheet_risk", False)

        # ========== BTTS OUI - SEUIL STRICT ==========
        btts_yes_threshold = thresholds.get("btts_yes", 0.62)

        # Augmenter le seuil si risques identifiés
        if high_clean_sheet_risk:
            btts_yes_threshold += 0.08
            logger.info(f"[BTTS] Seuil augmenté à {btts_yes_threshold:.0%} (clean sheet risk)")

        if is_heavily_unbalanced:
            btts_yes_threshold = 0.90  # Quasi impossible
            logger.info(f"[BTTS] Match déséquilibré → BTTS Oui désactivé")

        # Recommander BTTS Oui uniquement si prob très élevée
        if btts_prob >= btts_yes_threshold and not is_heavily_unbalanced and not high_clean_sheet_risk:
            confidence = CONFIDENCE_HIGH if btts_prob >= 0.70 else CONFIDENCE_MEDIUM
            reasoning = f"Les deux équipes marquent régulièrement (prob {btts_prob:.0%})"
            predictions.append(Prediction(
                match=match,
                bet_type=BetType.BTTS_YES,
                confidence=confidence,
                odds_estimate=round(1 / btts_prob, 2),
                reasoning=reasoning,
                btts_probability=btts_prob
            ))

        # ========== BTTS NON - FAVORISÉ ==========
        btts_no_prob = 1 - btts_prob
        btts_no_threshold = thresholds.get("btts_no", 0.45)

        if btts_no_prob >= btts_no_threshold:
            # Déterminer la confiance et le reasoning
            if is_heavily_unbalanced:
                confidence = CONFIDENCE_HIGH
                reasoning = f"Match déséquilibré ({home_strength} vs {away_strength}): clean sheet probable"
            elif high_clean_sheet_risk:
                confidence = CONFIDENCE_HIGH
                home_cs = goals_analysis.get("home_clean_sheet_rate", 0)
                away_cs = goals_analysis.get("away_clean_sheet_rate", 0)
                reasoning = f"Risque clean sheet élevé (dom: {home_cs:.0%}, ext: {away_cs:.0%})"
            elif btts_no_prob >= 0.60:
                confidence = CONFIDENCE_HIGH
                reasoning = f"Clean sheet très probable (prob {btts_no_prob:.0%})"
            elif btts_no_prob >= 0.52:
                confidence = CONFIDENCE_MEDIUM
                reasoning = f"Une équipe devrait garder sa cage inviolée"
            else:
                confidence = CONFIDENCE_LOW
                reasoning = f"Clean sheet possible"

            predictions.append(Prediction(
                match=match,
                bet_type=BetType.BTTS_NO,
                confidence=confidence,
                odds_estimate=round(1 / btts_no_prob, 2),
                reasoning=reasoning,
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

    def validate_prediction_with_odds(self, prediction: Prediction, market_odds: float) -> Dict:
        """
        Valide une prédiction en la comparant aux cotes du marché

        Args:
            prediction: La prédiction à valider
            market_odds: La cote du marché pour ce pari

        Returns:
            Dict avec validation, value, et recommandation
        """
        if market_odds <= 1.0:
            return {"valid": False, "reason": "Cote invalide"}

        # Probabilité implicite du marché (sans marge)
        implied_prob = 1 / market_odds

        # Probabilité prédite
        predicted_prob = 1 / prediction.odds_estimate if prediction.odds_estimate > 0 else 0

        # Calculer la "value"
        # Value = (prob_prédite * cote_marché) - 1
        value = (predicted_prob * market_odds) - 1

        result = {
            "implied_prob": implied_prob,
            "predicted_prob": predicted_prob,
            "market_odds": market_odds,
            "value": value,
            "valid": True
        }

        # ========== RÈGLES DE VALIDATION ==========

        # Règle 1: Si la cote est trop élevée (>3.0) pour BTTS Oui, être prudent
        if prediction.bet_type == BetType.BTTS_YES and market_odds > 2.10:
            result["warning"] = "BTTS Oui risqué: cote élevée suggère faible probabilité"
            result["recommendation"] = "ÉVITER"

        # Règle 2: Si Under 2.5 coté < 1.60, c'est probablement bon
        elif prediction.bet_type == BetType.OVER_2_5 and market_odds > 2.20:
            result["warning"] = "Over 2.5 risqué: cote élevée"
            result["recommendation"] = "PRUDENCE"

        # Règle 3: Value betting - si value > 10%, c'est intéressant
        elif value > 0.10:
            result["recommendation"] = "VALUE BET"
        elif value > 0:
            result["recommendation"] = "OK"
        elif value > -0.10:
            result["recommendation"] = "ACCEPTABLE"
        else:
            result["recommendation"] = "ÉVITER"
            result["warning"] = f"Valeur négative: {value:.1%}"

        return result

    def filter_predictions_by_odds(self, predictions: List[Prediction], odds_data: Dict) -> List[Prediction]:
        """
        Filtre les prédictions en fonction des cotes du marché

        Args:
            predictions: Liste de prédictions
            odds_data: Dict avec les cotes {bet_type: odds}

        Returns:
            Liste de prédictions validées
        """
        validated = []

        for pred in predictions:
            bet_key = pred.bet_type.value if hasattr(pred.bet_type, 'value') else str(pred.bet_type)

            if bet_key in odds_data:
                market_odds = odds_data[bet_key]
                validation = self.validate_prediction_with_odds(pred, market_odds)

                if validation.get("recommendation") in ["VALUE BET", "OK", "ACCEPTABLE"]:
                    validated.append(pred)
                else:
                    logger.info(f"[ODDS] Prédiction filtrée: {bet_key} - {validation.get('warning', 'value négative')}")
            else:
                # Si pas de cote disponible, garder la prédiction
                validated.append(pred)

        return validated
