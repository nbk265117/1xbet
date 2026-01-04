from typing import List, Tuple
import uuid

from models.match import (
    Match,
    MatchAnalysis,
    Prediction,
    PredictionConfidence,
    HeadToHead,
    ComboMatch,
    BestCombo,
)


class MatchPredictor:
    """Moteur de prédiction basé sur l'analyse de données"""

    def __init__(self):
        # Poids pour chaque facteur de prédiction
        self.weights = {
            "head_to_head": 0.15,
            "home_form": 0.20,
            "away_form": 0.20,
            "home_advantage": 0.15,
            "injuries": 0.15,
            "league_position": 0.15,
        }

    def calculate_form_score(self, form: List[str]) -> float:
        """Calcule un score basé sur les derniers résultats"""
        if not form:
            return 0.5

        points = 0
        for i, result in enumerate(form):
            weight = 1 + (len(form) - i) * 0.1  # Plus récent = plus de poids
            if result == "W":
                points += 3 * weight
            elif result == "D":
                points += 1 * weight

        max_points = sum((3 * (1 + (len(form) - i) * 0.1)) for i in range(len(form)))
        return points / max_points if max_points > 0 else 0.5

    def calculate_h2h_advantage(self, h2h: HeadToHead) -> Tuple[float, float]:
        """Calcule l'avantage basé sur l'historique des confrontations"""
        if h2h.total_matches == 0:
            return 0.5, 0.5

        home_score = (h2h.home_wins * 3 + h2h.draws) / (h2h.total_matches * 3)
        away_score = (h2h.away_wins * 3 + h2h.draws) / (h2h.total_matches * 3)

        return home_score, away_score

    def calculate_injury_impact(self, injuries: List, is_key_player_missing: bool = False) -> float:
        """Évalue l'impact des blessures (0 = beaucoup de blessés, 1 = pas de blessés)"""
        if not injuries:
            return 1.0

        # Pénalité de base par joueur absent
        penalty = len(injuries) * 0.05

        # Pénalité supplémentaire si joueur clé absent
        key_players = sum(1 for p in injuries if getattr(p, "is_key_player", False))
        penalty += key_players * 0.1

        return max(0.5, 1.0 - penalty)

    def predict_match(self, analysis: MatchAnalysis) -> Prediction:
        """Génère une prédiction pour un match"""
        match = analysis.match

        # Calculer les scores pour chaque facteur
        home_form_score = self.calculate_form_score(analysis.home_team_form)
        away_form_score = self.calculate_form_score(analysis.away_team_form)

        h2h_home, h2h_away = self.calculate_h2h_advantage(analysis.head_to_head)

        home_injury_factor = self.calculate_injury_impact(analysis.home_injuries)
        away_injury_factor = self.calculate_injury_impact(analysis.away_injuries)

        # Avantage domicile (environ 10-15% d'avantage statistique)
        home_advantage = 0.12

        # Calculer les probabilités brutes
        home_strength = (
            home_form_score * self.weights["home_form"]
            + h2h_home * self.weights["head_to_head"]
            + home_injury_factor * self.weights["injuries"]
            + home_advantage * self.weights["home_advantage"]
        )

        away_strength = (
            away_form_score * self.weights["away_form"]
            + h2h_away * self.weights["head_to_head"]
            + away_injury_factor * self.weights["injuries"]
        )

        # Normaliser les probabilités
        total = home_strength + away_strength
        if total == 0:
            home_prob = 0.4
            away_prob = 0.3
            draw_prob = 0.3
        else:
            home_prob = home_strength / total * 0.7 + 0.15  # Ajustement pour inclure les nuls
            away_prob = away_strength / total * 0.7 + 0.1
            draw_prob = 1 - home_prob - away_prob

        # Ajuster pour avoir des probabilités réalistes
        home_prob = max(0.1, min(0.7, home_prob))
        away_prob = max(0.1, min(0.6, away_prob))
        draw_prob = 1 - home_prob - away_prob
        draw_prob = max(0.15, min(0.4, draw_prob))

        # Re-normaliser
        total = home_prob + away_prob + draw_prob
        home_prob /= total
        away_prob /= total
        draw_prob /= total

        # Déterminer le résultat prédit
        max_prob = max(home_prob, draw_prob, away_prob)
        if max_prob == home_prob:
            predicted_outcome = "home"
            recommended_bet = f"Victoire {match.home_team.name}"
        elif max_prob == away_prob:
            predicted_outcome = "away"
            recommended_bet = f"Victoire {match.away_team.name}"
        else:
            predicted_outcome = "draw"
            recommended_bet = "Match nul"

        # Évaluer la confiance
        confidence = self._calculate_confidence(max_prob, analysis)

        # Construire les facteurs d'analyse
        factors = self._build_analysis_factors(analysis, home_form_score, away_form_score)

        # Résumé de l'analyse
        summary = self._build_summary(
            match, predicted_outcome, max_prob, home_form_score, away_form_score, analysis
        )

        return Prediction(
            match_id=match.id,
            match=match,
            predicted_outcome=predicted_outcome,
            home_win_probability=round(home_prob * 100, 1),
            draw_probability=round(draw_prob * 100, 1),
            away_win_probability=round(away_prob * 100, 1),
            confidence=confidence,
            recommended_bet=recommended_bet,
            analysis_summary=summary,
            factors=factors,
        )

    def _calculate_confidence(self, max_prob: float, analysis: MatchAnalysis) -> PredictionConfidence:
        """Calcule le niveau de confiance de la prédiction"""
        # Plus la probabilité est élevée et plus on a de données, plus on est confiant
        data_quality = 1.0

        if analysis.head_to_head.total_matches < 3:
            data_quality -= 0.2
        if len(analysis.home_team_form) < 4:
            data_quality -= 0.1
        if len(analysis.away_team_form) < 4:
            data_quality -= 0.1

        adjusted_confidence = max_prob * data_quality

        if adjusted_confidence >= 0.55:
            return PredictionConfidence.VERY_HIGH
        elif adjusted_confidence >= 0.45:
            return PredictionConfidence.HIGH
        elif adjusted_confidence >= 0.35:
            return PredictionConfidence.MEDIUM
        else:
            return PredictionConfidence.LOW

    def _build_analysis_factors(
        self, analysis: MatchAnalysis, home_form_score: float, away_form_score: float
    ) -> List[str]:
        """Construit la liste des facteurs d'analyse"""
        factors = []

        # Forme récente
        if home_form_score > 0.7:
            factors.append(f"✅ {analysis.match.home_team.name} en excellente forme")
        elif home_form_score < 0.3:
            factors.append(f"⚠️ {analysis.match.home_team.name} en mauvaise forme")

        if away_form_score > 0.7:
            factors.append(f"✅ {analysis.match.away_team.name} en excellente forme")
        elif away_form_score < 0.3:
            factors.append(f"⚠️ {analysis.match.away_team.name} en mauvaise forme")

        # H2H
        h2h = analysis.head_to_head
        if h2h.total_matches >= 3:
            if h2h.home_wins > h2h.away_wins:
                factors.append(f"📊 H2H favorable à {analysis.match.home_team.name}")
            elif h2h.away_wins > h2h.home_wins:
                factors.append(f"📊 H2H favorable à {analysis.match.away_team.name}")

        # Blessures
        if analysis.home_injuries:
            factors.append(f"🏥 {len(analysis.home_injuries)} absent(s) chez {analysis.match.home_team.name}")
        if analysis.away_injuries:
            factors.append(f"🏥 {len(analysis.away_injuries)} absent(s) chez {analysis.match.away_team.name}")

        # Avantage domicile
        factors.append(f"🏟️ Avantage domicile pour {analysis.match.home_team.name}")

        return factors

    def _build_summary(
        self,
        match: Match,
        outcome: str,
        probability: float,
        home_form: float,
        away_form: float,
        analysis: MatchAnalysis,
    ) -> str:
        """Construit un résumé textuel de l'analyse"""
        home = match.home_team.name
        away = match.away_team.name

        if outcome == "home":
            winner = home
            summary = f"{home} favori à domicile"
        elif outcome == "away":
            winner = away
            summary = f"{away} favori malgré le déplacement"
        else:
            summary = f"Match équilibré entre {home} et {away}"

        details = []

        if home_form > away_form + 0.2:
            details.append(f"{home} en meilleure forme")
        elif away_form > home_form + 0.2:
            details.append(f"{away} en meilleure forme")

        if analysis.head_to_head.total_matches > 0:
            details.append(f"{analysis.head_to_head.total_matches} confrontations analysées")

        if details:
            summary += f". {'. '.join(details)}."

        return summary

    def generate_best_combos(
        self, predictions: List[Prediction], max_combos: int = 5
    ) -> List[BestCombo]:
        """Génère les meilleurs combinés basés sur les prédictions"""
        # Filtrer les prédictions avec confiance suffisante
        confident_predictions = [
            p for p in predictions
            if p.confidence in [PredictionConfidence.HIGH, PredictionConfidence.VERY_HIGH]
        ]

        if len(confident_predictions) < 2:
            confident_predictions = [
                p for p in predictions if p.confidence != PredictionConfidence.LOW
            ]

        combos = []

        # Combo sécurisé (2-3 matchs très sûrs)
        safe_predictions = sorted(
            confident_predictions,
            key=lambda x: max(x.home_win_probability, x.away_win_probability),
            reverse=True,
        )[:3]

        if len(safe_predictions) >= 2:
            combos.append(self._create_combo(
                safe_predictions[:2],
                "safe",
                "Combiné sécurisé - 2 matchs haute confiance"
            ))

        # Combo modéré (3-4 matchs)
        if len(confident_predictions) >= 3:
            moderate_predictions = confident_predictions[:4]
            combos.append(self._create_combo(
                moderate_predictions[:3],
                "moderate",
                "Combiné équilibré - 3 matchs"
            ))

        # Combo risqué (4-5 matchs pour gros gains)
        if len(predictions) >= 4:
            risky_predictions = sorted(
                predictions, key=lambda x: x.confidence.value, reverse=True
            )[:5]
            combos.append(self._create_combo(
                risky_predictions,
                "risky",
                "Combiné ambitieux - 5 matchs pour gros gains"
            ))

        # Combo double chance (matchs serrés)
        draw_heavy = [
            p for p in predictions if p.draw_probability > 25
        ]
        if len(draw_heavy) >= 2:
            combo_matches = []
            for p in draw_heavy[:3]:
                # Suggérer double chance plutôt que résultat exact
                if p.home_win_probability > p.away_win_probability:
                    bet = f"1X ({p.match.home_team.name} ou Nul)"
                else:
                    bet = f"X2 (Nul ou {p.match.away_team.name})"

                combo_matches.append(ComboMatch(
                    match_id=p.match_id,
                    teams=f"{p.match.home_team.name} vs {p.match.away_team.name}",
                    prediction=bet,
                    confidence=p.confidence,
                    probability=max(
                        p.home_win_probability + p.draw_probability,
                        p.away_win_probability + p.draw_probability,
                    ),
                ))

            if combo_matches:
                total_prob = 1.0
                for cm in combo_matches:
                    total_prob *= (cm.probability / 100)

                combos.append(BestCombo(
                    id=str(uuid.uuid4())[:8],
                    matches=combo_matches,
                    total_probability=round(total_prob * 100, 2),
                    risk_level="safe",
                    expected_value=round(total_prob * 100 * 1.5, 2),
                    description="Combiné Double Chance - Plus de sécurité",
                ))

        return combos[:max_combos]

    def _create_combo(
        self, predictions: List[Prediction], risk_level: str, description: str
    ) -> BestCombo:
        """Crée un objet BestCombo à partir d'une liste de prédictions"""
        combo_matches = []
        total_prob = 1.0

        for p in predictions:
            # Déterminer le meilleur pari
            if p.predicted_outcome == "home":
                bet = f"1 ({p.match.home_team.name})"
                prob = p.home_win_probability
            elif p.predicted_outcome == "away":
                bet = f"2 ({p.match.away_team.name})"
                prob = p.away_win_probability
            else:
                bet = "X (Nul)"
                prob = p.draw_probability

            combo_matches.append(ComboMatch(
                match_id=p.match_id,
                teams=f"{p.match.home_team.name} vs {p.match.away_team.name}",
                prediction=bet,
                confidence=p.confidence,
                probability=prob,
            ))

            total_prob *= (prob / 100)

        # Estimation de la valeur attendue (simplifiée)
        odds_multiplier = {"safe": 2.5, "moderate": 5.0, "risky": 15.0}
        expected_value = total_prob * 100 * odds_multiplier.get(risk_level, 3.0)

        return BestCombo(
            id=str(uuid.uuid4())[:8],
            matches=combo_matches,
            total_probability=round(total_prob * 100, 2),
            risk_level=risk_level,
            expected_value=round(expected_value, 2),
            description=description,
        )
