from typing import List, Tuple, Dict, Optional
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


# =============================================================================
# CONFIGURATION ALGORITHME v2.0 - Basé sur analyse du 25/01/2026
# =============================================================================

# Ligues défensives à éviter pour Over 2.5
DEFENSIVE_LEAGUES = [
    "jordan", "thailand", "greece", "morocco", "iran",
    "saudi arabia",  # Sauf matchs avec Expected > 3.5
]

# Ligues offensives à privilégier
OFFENSIVE_LEAGUES = [
    "switzerland", "netherlands", "hong kong", "mexico",
    "laos", "singapore", "gibraltar",
]

# Seuils pour Over 2.5
THRESHOLDS = {
    "over_25_safe": 3.5,      # Expected >= 3.5 = 87% de réussite
    "over_25_moderate": 3.0,  # Expected 3.0-3.5 = 50% de réussite (risqué)
    "over_15_safe": 2.5,      # Expected >= 2.5 = 77% de réussite
    "failed_to_score_max": 0.35,  # Si équipe rate > 35% des matchs = danger
    "h2h_min_goals": 2.5,     # Moyenne H2H minimum pour Over 2.5
}


class MatchPredictor:
    """Moteur de prédiction basé sur l'analyse de données - v2.0"""

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

    # =========================================================================
    # NOUVELLES MÉTHODES OVER/UNDER - v2.0
    # =========================================================================

    def calculate_expected_goals(
        self,
        home_goals_for: float,
        home_goals_against: float,
        away_goals_for: float,
        away_goals_against: float
    ) -> float:
        """
        Calcule les Expected Goals pour un match.
        Formule: (home_for + away_against)/2 + (away_for + home_against)/2
        """
        if home_goals_for + away_goals_for == 0:
            return 0.0

        expected = (home_goals_for + away_goals_against) / 2 + (away_goals_for + home_goals_against) / 2
        return round(expected, 2)

    def check_failed_to_score_risk(
        self,
        home_failed_to_score: int,
        home_matches: int,
        away_failed_to_score: int,
        away_matches: int
    ) -> Dict[str, any]:
        """
        Vérifie le risque de "failed to score" pour chaque équipe.
        Retourne un dict avec les taux et les alertes.
        """
        home_rate = home_failed_to_score / home_matches if home_matches > 0 else 0
        away_rate = away_failed_to_score / away_matches if away_matches > 0 else 0

        alerts = []
        risk_level = "low"

        if home_rate > THRESHOLDS["failed_to_score_max"]:
            alerts.append(f"⚠️ Home team fails to score {home_rate*100:.0f}% of matches")
            risk_level = "high"

        if away_rate > THRESHOLDS["failed_to_score_max"]:
            alerts.append(f"⚠️ Away team fails to score {away_rate*100:.0f}% of matches")
            risk_level = "high"

        return {
            "home_rate": round(home_rate, 2),
            "away_rate": round(away_rate, 2),
            "alerts": alerts,
            "risk_level": risk_level
        }

    def check_big_team_away_risk(
        self,
        away_team_strength: float,
        home_team_strength: float,
        league: str
    ) -> Dict[str, any]:
        """
        Détecte si une grande équipe joue en déplacement contre une petite.
        Ces matchs sont souvent défensifs (ex: Raja Casablanca).
        """
        strength_diff = away_team_strength - home_team_strength

        if strength_diff > 0.3:  # Grande équipe en déplacement
            return {
                "is_risky": True,
                "alert": "⚠️ Grande équipe en déplacement - risque de jeu défensif",
                "recommendation": "Éviter Over 2.5, préférer Under 2.5 ou 1X2"
            }

        return {"is_risky": False, "alert": None, "recommendation": None}

    def check_league_defensive(self, league: str, country: str) -> Dict[str, any]:
        """
        Vérifie si la ligue est connue pour être défensive.
        """
        league_lower = league.lower()
        country_lower = country.lower()

        for defensive in DEFENSIVE_LEAGUES:
            if defensive in league_lower or defensive in country_lower:
                return {
                    "is_defensive": True,
                    "alert": f"⚠️ {country} - Ligue défensive, Over 2.5 risqué",
                    "min_expected": 4.0  # Exiger Expected plus élevé
                }

        for offensive in OFFENSIVE_LEAGUES:
            if offensive in league_lower or offensive in country_lower:
                return {
                    "is_defensive": False,
                    "is_offensive": True,
                    "bonus": "✅ Ligue offensive - Over 2.5 recommandé"
                }

        return {"is_defensive": False, "is_offensive": False}

    def predict_over_under(
        self,
        expected_goals: float,
        h2h_avg_goals: float,
        league_info: Dict,
        failed_to_score_info: Dict,
        big_team_away_info: Dict
    ) -> Dict[str, any]:
        """
        Prédit Over/Under avec niveau de confiance et recommandations.
        Retourne les prédictions pour Over 2.5, Over 1.5, et alertes.
        """
        result = {
            "expected_goals": expected_goals,
            "over_25": {"recommended": False, "confidence": "low", "probability": 0},
            "over_15": {"recommended": False, "confidence": "low", "probability": 0},
            "alerts": [],
            "recommendation": None
        }

        # Collecter les alertes
        result["alerts"].extend(failed_to_score_info.get("alerts", []))
        if big_team_away_info.get("is_risky"):
            result["alerts"].append(big_team_away_info["alert"])
        if league_info.get("is_defensive"):
            result["alerts"].append(league_info["alert"])

        # Ajuster le seuil si ligue défensive
        over_25_threshold = THRESHOLDS["over_25_safe"]
        if league_info.get("is_defensive"):
            over_25_threshold = league_info.get("min_expected", 4.0)

        # =====================================================================
        # OVER 2.5 ANALYSIS
        # =====================================================================
        if expected_goals >= over_25_threshold:
            # Expected >= 3.5 (ou 4.0 pour ligues défensives) = TRÈS SÛR
            result["over_25"] = {
                "recommended": True,
                "confidence": "very_high",
                "probability": 87,
                "verdict": "🔥 TRÈS SÛR"
            }
            result["recommendation"] = "✅ Over 2.5 RECOMMANDÉ"

        elif expected_goals >= THRESHOLDS["over_25_moderate"]:
            # Expected 3.0-3.5 = RISQUÉ (50% seulement)
            # Vérifier les facteurs de risque
            risk_count = len(result["alerts"])

            if risk_count == 0 and h2h_avg_goals >= THRESHOLDS["h2h_min_goals"]:
                result["over_25"] = {
                    "recommended": True,
                    "confidence": "medium",
                    "probability": 60,
                    "verdict": "⚠️ MOYEN - Prudence"
                }
                result["recommendation"] = "⚠️ Over 2.5 possible mais risqué"
            else:
                result["over_25"] = {
                    "recommended": False,
                    "confidence": "low",
                    "probability": 40,
                    "verdict": "❌ ÉVITER"
                }
                result["recommendation"] = "❌ Over 2.5 NON recommandé - Trop de risques"

        else:
            # Expected < 3.0 = NE PAS PRENDRE
            result["over_25"] = {
                "recommended": False,
                "confidence": "very_low",
                "probability": 30,
                "verdict": "❌ ÉVITER"
            }
            result["recommendation"] = "❌ Over 2.5 NON recommandé - Expected trop bas"

        # =====================================================================
        # OVER 1.5 ANALYSIS (Alternative plus sûre)
        # =====================================================================
        if expected_goals >= THRESHOLDS["over_15_safe"]:
            result["over_15"] = {
                "recommended": True,
                "confidence": "high",
                "probability": 77,
                "verdict": "✅ SÛR"
            }
        elif expected_goals >= 2.0:
            result["over_15"] = {
                "recommended": True,
                "confidence": "medium",
                "probability": 65,
                "verdict": "⚠️ ACCEPTABLE"
            }
        else:
            result["over_15"] = {
                "recommended": False,
                "confidence": "low",
                "probability": 50,
                "verdict": "❌ RISQUÉ"
            }

        # =====================================================================
        # ONE TEAM OVER 1.5 (Une équipe marque 2+ buts)
        # =====================================================================
        # Cette stratégie a 68% de réussite
        if expected_goals >= 3.0:
            result["one_team_over_15"] = {
                "recommended": True,
                "confidence": "high",
                "probability": 68,
                "verdict": "✅ BON"
            }

        return result

    def analyze_match_for_over_under(self, api_prediction_data: Dict) -> Dict[str, any]:
        """
        Analyse complète d'un match pour Over/Under à partir des données API.

        Args:
            api_prediction_data: Données de l'endpoint /predictions de l'API

        Returns:
            Dict avec analyse complète et recommandations
        """
        try:
            pred = api_prediction_data.get('response', [{}])[0]
            if not pred:
                return {"error": "No prediction data"}

            # Extraire les données des équipes
            home = pred.get('teams', {}).get('home', {})
            away = pred.get('teams', {}).get('away', {})
            league = pred.get('league', {})

            home_league = home.get('league', {})
            away_league = away.get('league', {})

            # Goals averages
            home_goals_for = float(home_league.get('goals', {}).get('for', {}).get('average', {}).get('total', 0) or 0)
            home_goals_against = float(home_league.get('goals', {}).get('against', {}).get('average', {}).get('total', 0) or 0)
            away_goals_for = float(away_league.get('goals', {}).get('for', {}).get('average', {}).get('total', 0) or 0)
            away_goals_against = float(away_league.get('goals', {}).get('against', {}).get('average', {}).get('total', 0) or 0)

            # Calcul Expected Goals
            expected_goals = self.calculate_expected_goals(
                home_goals_for, home_goals_against,
                away_goals_for, away_goals_against
            )

            # Failed to score stats
            home_fts = home_league.get('failed_to_score', {}).get('total', 0)
            home_matches = home_league.get('fixtures', {}).get('played', {}).get('total', 1)
            away_fts = away_league.get('failed_to_score', {}).get('total', 0)
            away_matches = away_league.get('fixtures', {}).get('played', {}).get('total', 1)

            fts_info = self.check_failed_to_score_risk(
                home_fts, home_matches,
                away_fts, away_matches
            )

            # League analysis
            league_name = league.get('name', '')
            country = league.get('country', '')
            league_info = self.check_league_defensive(league_name, country)

            # Big team away analysis
            home_form_score = self.calculate_form_score(list(home_league.get('form', '') or ''))
            away_form_score = self.calculate_form_score(list(away_league.get('form', '') or ''))
            big_team_info = self.check_big_team_away_risk(
                away_form_score, home_form_score, league_name
            )

            # H2H analysis
            h2h = pred.get('h2h', [])
            h2h_avg_goals = 0
            if h2h:
                total_goals = sum(
                    (m.get('goals', {}).get('home', 0) or 0) + (m.get('goals', {}).get('away', 0) or 0)
                    for m in h2h[:5]
                )
                h2h_avg_goals = total_goals / min(5, len(h2h))

            # Generate Over/Under prediction
            over_under = self.predict_over_under(
                expected_goals, h2h_avg_goals,
                league_info, fts_info, big_team_info
            )

            return {
                "match": f"{home.get('name', 'Home')} vs {away.get('name', 'Away')}",
                "league": f"{league_name} ({country})",
                "expected_goals": expected_goals,
                "h2h_avg_goals": round(h2h_avg_goals, 2),
                "stats": {
                    "home_goals_for": home_goals_for,
                    "home_goals_against": home_goals_against,
                    "away_goals_for": away_goals_for,
                    "away_goals_against": away_goals_against,
                    "home_failed_to_score_rate": fts_info["home_rate"],
                    "away_failed_to_score_rate": fts_info["away_rate"],
                },
                "over_under": over_under,
                "should_bet_over_25": over_under["over_25"]["recommended"],
                "should_bet_over_15": over_under["over_15"]["recommended"],
                "alerts": over_under["alerts"],
                "final_recommendation": over_under["recommendation"]
            }

        except Exception as e:
            return {"error": str(e)}

    def filter_matches_for_over_25(
        self,
        matches_analysis: List[Dict],
        min_expected: float = 3.5
    ) -> List[Dict]:
        """
        Filtre les matchs pour Over 2.5 selon les nouveaux critères.

        Args:
            matches_analysis: Liste des analyses de matchs
            min_expected: Expected Goals minimum (défaut 3.5 = 87% réussite)

        Returns:
            Liste des matchs filtrés et triés par Expected
        """
        filtered = []

        for match in matches_analysis:
            if match.get("error"):
                continue

            over_under = match.get("over_under", {})
            over_25 = over_under.get("over_25", {})

            # Appliquer les critères stricts
            if over_25.get("recommended") and over_25.get("confidence") in ["very_high", "high"]:
                filtered.append(match)

        # Trier par Expected Goals décroissant
        filtered.sort(key=lambda x: x.get("expected_goals", 0), reverse=True)

        return filtered

    def generate_safe_over_25_ticket(
        self,
        matches_analysis: List[Dict],
        max_matches: int = 8
    ) -> Dict[str, any]:
        """
        Génère un ticket sécurisé pour Over 2.5 avec les meilleurs matchs.

        Args:
            matches_analysis: Liste des analyses de matchs
            max_matches: Nombre maximum de matchs (recommandé: 5-8)

        Returns:
            Dict avec le ticket et les statistiques
        """
        # Filtrer avec critères stricts (Expected >= 3.5)
        safe_matches = self.filter_matches_for_over_25(matches_analysis, min_expected=3.5)

        # Limiter le nombre de matchs
        selected = safe_matches[:max_matches]

        # Calculer la probabilité combinée
        combined_prob = 1.0
        for match in selected:
            prob = match.get("over_under", {}).get("over_25", {}).get("probability", 50) / 100
            combined_prob *= prob

        return {
            "ticket_type": "SAFE_OVER_25",
            "matches_count": len(selected),
            "matches": [
                {
                    "match": m["match"],
                    "league": m["league"],
                    "expected": m["expected_goals"],
                    "confidence": m["over_under"]["over_25"]["confidence"],
                    "verdict": m["over_under"]["over_25"]["verdict"]
                }
                for m in selected
            ],
            "combined_probability": round(combined_prob * 100, 2),
            "recommendation": f"✅ Ticket SAFE avec {len(selected)} matchs - Probabilité: {round(combined_prob * 100, 1)}%"
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
