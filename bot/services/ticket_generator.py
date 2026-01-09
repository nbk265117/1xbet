"""
Générateur de tickets de paris optimisés
"""
import logging
import random
from typing import List, Dict, Set
from datetime import datetime
from models.match import Match, Prediction, Ticket, BetType
from services.analyzer import MatchAnalyzer
from config.settings import (
    MIN_TICKETS_PER_DAY, MAX_TICKETS_PER_DAY,
    MIN_MATCHES_PER_TICKET, MAX_MATCHES_PER_TICKET,
    CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, CONFIDENCE_LOW
)

logger = logging.getLogger(__name__)


class TicketGenerator:
    """Génère des tickets de paris optimisés"""

    # Types de tickets - DIVERSIFIÉS
    TICKET_TYPES = {
        "safe": {
            "name": "Ticket Sécurisé",
            "min_confidence": CONFIDENCE_MEDIUM,
            "preferred_bets": [BetType.DOUBLE_CHANCE_1X, BetType.DOUBLE_CHANCE_X2,
                              BetType.OVER_1_5],
            "max_matches": 5,
            "risk": "FAIBLE",
            "max_same_type": 2  # Max 2 paris du même type
        },
        "balanced": {
            "name": "Ticket Mixte",
            "min_confidence": CONFIDENCE_MEDIUM,
            "preferred_bets": [BetType.HOME_WIN, BetType.AWAY_WIN, BetType.OVER_1_5,
                              BetType.DOUBLE_CHANCE_1X, BetType.DOUBLE_CHANCE_X2],  # BTTS Oui remplacé par Over 1.5
            "max_matches": 5,
            "risk": "MOYEN",
            "max_same_type": 1  # Forcer la diversité - 1 seul pari par type
        },
        "goals": {
            "name": "Ticket Buts",
            "min_confidence": CONFIDENCE_MEDIUM,
            "preferred_bets": [BetType.OVER_2_5, BetType.OVER_1_5, BetType.BTTS_NO],  # BTTS Oui retiré
            "max_matches": 5,
            "risk": "MOYEN",
            "max_same_type": 2
        },
        "favorites": {
            "name": "Ticket Favoris",
            "min_confidence": CONFIDENCE_HIGH,
            "preferred_bets": [BetType.HOME_WIN, BetType.AWAY_WIN],
            "max_matches": 4,
            "risk": "MOYEN",
            "max_same_type": 3
        },
        "btts": {
            "name": "Ticket Over/Under",  # Renommé car BTTS Oui n'est plus fiable
            "min_confidence": CONFIDENCE_MEDIUM,
            "preferred_bets": [BetType.OVER_2_5, BetType.OVER_1_5, BetType.BTTS_NO],  # Favoriser Over au lieu de BTTS Oui
            "max_matches": 5,
            "risk": "MOYEN",
            "max_same_type": 3
        },
        "combo": {
            "name": "Ticket Combo",
            "min_confidence": CONFIDENCE_MEDIUM,
            "preferred_bets": [BetType.HOME_WIN_AND_OVER_1_5, BetType.AWAY_WIN_AND_OVER_1_5,
                              BetType.BTTS_AND_OVER_2_5],
            "max_matches": 4,
            "risk": "ÉLEVÉ",
            "max_same_type": 2
        }
    }

    def __init__(self, analyzer: MatchAnalyzer):
        self.analyzer = analyzer
        self.used_matches: Set[int] = set()

    def generate_tickets(self, matches: List[Match]) -> List[Ticket]:
        """
        Génère les tickets du jour
        Args:
            matches: Liste des matchs disponibles
        Returns:
            Liste des tickets générés (3-6 tickets)
        """
        logger.info(f"Generating tickets from {len(matches)} matches")

        if len(matches) < MIN_MATCHES_PER_TICKET:
            logger.warning("Not enough matches to generate tickets")
            return []

        # Analyser tous les matchs et générer les prédictions
        all_predictions = []
        for match in matches:
            predictions = self.analyzer.generate_predictions(match)
            all_predictions.extend(predictions)

        logger.info(f"Generated {len(all_predictions)} predictions")

        # Grouper les prédictions par match
        predictions_by_match: Dict[int, List[Prediction]] = {}
        for pred in all_predictions:
            match_id = pred.match.id
            if match_id not in predictions_by_match:
                predictions_by_match[match_id] = []
            predictions_by_match[match_id].append(pred)

        # Générer les différents types de tickets DIVERSIFIÉS
        tickets = []
        self.used_matches.clear()

        # Ticket 1: Sécurisé (Double Chance + Over 1.5)
        safe_ticket = self._generate_ticket_by_type("safe", predictions_by_match, 1)
        if safe_ticket:
            tickets.append(safe_ticket)

        # Ticket 2: Mixte (1X2 + BTTS + DC) - MAXIMUM 1 pari par type
        self.used_matches.clear()  # Reset pour permettre la réutilisation des matchs
        balanced_ticket = self._generate_ticket_by_type("balanced", predictions_by_match, 2)
        if balanced_ticket:
            tickets.append(balanced_ticket)

        # Ticket 3: BTTS uniquement
        self.used_matches.clear()
        btts_ticket = self._generate_ticket_by_type("btts", predictions_by_match, 3)
        if btts_ticket:
            tickets.append(btts_ticket)

        # Tickets supplémentaires si assez de matchs
        if len(matches) >= 10:
            self.used_matches.clear()
            favorites_ticket = self._generate_ticket_by_type("favorites", predictions_by_match, 4)
            if favorites_ticket:
                tickets.append(favorites_ticket)

        if len(matches) >= 12:
            self.used_matches.clear()
            goals_ticket = self._generate_ticket_by_type("goals", predictions_by_match, 5)
            if goals_ticket:
                tickets.append(goals_ticket)

        if len(matches) >= 15:
            self.used_matches.clear()
            combo_ticket = self._generate_ticket_by_type("combo", predictions_by_match, 6)
            if combo_ticket:
                tickets.append(combo_ticket)

        # S'assurer d'avoir au moins 3 tickets
        while len(tickets) < MIN_TICKETS_PER_DAY and len(matches) >= MIN_MATCHES_PER_TICKET:
            extra_ticket = self._generate_random_ticket(predictions_by_match, len(tickets) + 1)
            if extra_ticket:
                tickets.append(extra_ticket)
            else:
                break

        logger.info(f"Generated {len(tickets)} tickets")
        return tickets[:MAX_TICKETS_PER_DAY]

    def _generate_ticket_by_type(
        self,
        ticket_type: str,
        predictions_by_match: Dict[int, List[Prediction]],
        ticket_id: int
    ) -> Ticket:
        """Génère un ticket selon un type spécifique avec DIVERSITÉ"""
        config = self.TICKET_TYPES[ticket_type]

        ticket = Ticket(
            id=ticket_id,
            name=config["name"],
            risk_level=config["risk"]
        )

        # Compteur pour limiter les paris du même type
        bet_type_count: Dict[BetType, int] = {}
        max_same_type = config.get("max_same_type", 3)

        # Sélectionner les meilleures prédictions pour ce type
        suitable_predictions = []

        for match_id, preds in predictions_by_match.items():
            # Éviter de réutiliser trop les mêmes matchs
            if match_id in self.used_matches and random.random() > 0.3:
                continue

            for pred in preds:
                # Vérifier le niveau de confiance
                if not self._meets_confidence(pred.confidence, config["min_confidence"]):
                    continue

                # Vérifier si c'est un type de pari préféré
                if pred.bet_type not in config["preferred_bets"]:
                    continue

                # Bonus si c'est un type de pari préféré
                score = self._calculate_prediction_score(pred, config["preferred_bets"])
                suitable_predictions.append((pred, score))

        # Trier par score décroissant
        suitable_predictions.sort(key=lambda x: x[1], reverse=True)

        # Sélectionner les prédictions pour le ticket avec DIVERSITÉ
        max_matches = min(config["max_matches"], MAX_MATCHES_PER_TICKET)
        selected_matches: Set[int] = set()

        for pred, score in suitable_predictions:
            match_id = pred.match.id
            bet_type = pred.bet_type

            # Un seul pari par match
            if match_id in selected_matches:
                continue

            # Limiter le nombre de paris du même type
            current_count = bet_type_count.get(bet_type, 0)
            if current_count >= max_same_type:
                continue

            ticket.add_prediction(pred)
            selected_matches.add(match_id)
            self.used_matches.add(match_id)
            bet_type_count[bet_type] = current_count + 1

            if len(ticket) >= max_matches:
                break

        # Vérifier que le ticket a assez de matchs
        if len(ticket) < MIN_MATCHES_PER_TICKET:
            return None

        return ticket

    def _generate_random_ticket(
        self,
        predictions_by_match: Dict[int, List[Prediction]],
        ticket_id: int
    ) -> Ticket:
        """Génère un ticket avec des sélections variées"""
        ticket = Ticket(
            id=ticket_id,
            name=f"Ticket Mix #{ticket_id}",
            risk_level="MOYEN"
        )

        # Mélanger les types de tickets
        mixed_config = {
            "preferred_bets": [
                BetType.HOME_WIN, BetType.AWAY_WIN, BetType.OVER_2_5,
                BetType.BTTS_YES, BetType.DOUBLE_CHANCE_1X
            ]
        }

        available_matches = [
            (match_id, preds)
            for match_id, preds in predictions_by_match.items()
            if match_id not in self.used_matches
        ]

        random.shuffle(available_matches)

        for match_id, preds in available_matches[:6]:
            # Prendre la meilleure prédiction pour chaque match
            best_pred = max(preds, key=lambda p: self._calculate_prediction_score(p, mixed_config["preferred_bets"]))
            ticket.add_prediction(best_pred)
            self.used_matches.add(match_id)

        if len(ticket) < MIN_MATCHES_PER_TICKET:
            return None

        return ticket

    def _meets_confidence(self, pred_confidence: str, min_confidence: str) -> bool:
        """Vérifie si une prédiction atteint le niveau de confiance minimum"""
        levels = {CONFIDENCE_LOW: 1, CONFIDENCE_MEDIUM: 2, CONFIDENCE_HIGH: 3}
        return levels.get(pred_confidence, 0) >= levels.get(min_confidence, 0)

    def _calculate_prediction_score(self, prediction: Prediction, preferred_bets: List[BetType]) -> float:
        """Calcule un score pour une prédiction"""
        score = 0.0

        # Score de confiance
        confidence_scores = {CONFIDENCE_HIGH: 30, CONFIDENCE_MEDIUM: 20, CONFIDENCE_LOW: 10}
        score += confidence_scores.get(prediction.confidence, 0)

        # Bonus si type de pari préféré
        if prediction.bet_type in preferred_bets:
            score += 20

        # Bonus selon la cote estimée (sweet spot entre 1.40 et 2.20)
        odds = prediction.odds_estimate
        if 1.40 <= odds <= 2.20:
            score += 15
        elif 1.20 <= odds <= 1.40:
            score += 10
        elif 2.20 < odds <= 3.00:
            score += 8

        # Bonus pour les grandes ligues (priorité basse)
        from config.leagues import get_league_priority
        priority = get_league_priority(prediction.match.league_id)
        if priority == 1:
            score += 10
        elif priority == 2:
            score += 5

        return score

    def format_tickets_for_output(self, tickets: List[Ticket]) -> str:
        """Formate les tickets pour l'affichage/export"""
        output = []
        output.append("=" * 60)
        output.append(f"🎯 TICKETS DU JOUR - {datetime.now().strftime('%d/%m/%Y')}")
        output.append("=" * 60)
        output.append("")

        for ticket in tickets:
            output.append(ticket.get_summary())
            output.append("")
            output.append("-" * 60)
            output.append("")

        output.append("")
        output.append("⚠️ AVERTISSEMENT: Les paris sportifs comportent des risques.")
        output.append("   Ne misez que ce que vous pouvez vous permettre de perdre.")
        output.append("   Ces prédictions sont basées sur des analyses statistiques")
        output.append("   et ne garantissent pas de gains.")

        return "\n".join(output)

    def export_to_json(self, tickets: List[Ticket]) -> Dict:
        """Exporte les tickets au format JSON"""
        return {
            "date": datetime.now().isoformat(),
            "total_tickets": len(tickets),
            "tickets": [
                {
                    "id": ticket.id,
                    "name": ticket.name,
                    "confidence": ticket.confidence_level,
                    "risk": ticket.risk_level,
                    "total_odds": round(ticket.total_odds, 2),
                    "selections": [
                        {
                            "match": f"{p.match.home_team.name} vs {p.match.away_team.name}",
                            "league": p.match.league_name,
                            "date": p.match.date.isoformat(),
                            "bet": p.bet_type.value,
                            "confidence": p.confidence,
                            "odds": p.odds_estimate,
                            "reasoning": p.reasoning
                        }
                        for p in ticket.predictions
                    ]
                }
                for ticket in tickets
            ]
        }
