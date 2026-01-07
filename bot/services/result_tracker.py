"""
Service de suivi et vérification des résultats des paris
"""
import json
import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path

from models.result import PredictionResult, TicketResult, DailyStats, BetResult
from services.football_api import FootballAPIService
from config.settings import OUTPUT_DIR

logger = logging.getLogger(__name__)

# Dossier pour l'historique
HISTORY_DIR = os.path.join(os.path.dirname(OUTPUT_DIR), "history")
Path(HISTORY_DIR).mkdir(parents=True, exist_ok=True)


class ResultTracker:
    """Gère le suivi des résultats des paris"""

    def __init__(self):
        self.api = FootballAPIService()
        self.history_file = os.path.join(HISTORY_DIR, "betting_history.json")
        self.stats_file = os.path.join(HISTORY_DIR, "statistics.json")

    def save_predictions(self, tickets: List, date: datetime) -> str:
        """
        Sauvegarde les prédictions du jour pour suivi ultérieur
        Args:
            tickets: Liste des tickets générés
            date: Date des matchs (demain)
        """
        date_str = date.strftime("%Y-%m-%d")
        predictions_file = os.path.join(HISTORY_DIR, f"predictions_{date_str}.json")

        predictions_data = []
        for ticket in tickets:
            ticket_data = {
                "ticket_id": ticket.id,
                "ticket_name": ticket.name,
                "date": date_str,
                "total_odds": ticket.total_odds,
                "confidence": ticket.confidence_level,
                "risk": ticket.risk_level,
                "predictions": []
            }

            for pred in ticket.predictions:
                pred_data = {
                    "match_id": pred.match.id,
                    "home_team": pred.match.home_team.name,
                    "away_team": pred.match.away_team.name,
                    "league": pred.match.league_name,
                    "match_date": pred.match.date.isoformat(),
                    "bet_type": pred.bet_type.value,
                    "predicted_odds": pred.odds_estimate,
                    "confidence": pred.confidence,
                    "reasoning": pred.reasoning,
                    "home_score": None,
                    "away_score": None,
                    "result": "En attente"
                }
                ticket_data["predictions"].append(pred_data)

            predictions_data.append(ticket_data)

        with open(predictions_file, "w", encoding="utf-8") as f:
            json.dump(predictions_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Predictions saved to {predictions_file}")
        return predictions_file

    def check_results(self, date: str = None) -> List[TicketResult]:
        """
        Vérifie les résultats des matchs pour une date donnée
        Args:
            date: Date au format YYYY-MM-DD (défaut: aujourd'hui)
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        predictions_file = os.path.join(HISTORY_DIR, f"predictions_{date}.json")

        if not os.path.exists(predictions_file):
            logger.warning(f"No predictions file found for {date}")
            return []

        with open(predictions_file, "r", encoding="utf-8") as f:
            predictions_data = json.load(f)

        # Récupérer les résultats des matchs
        logger.info(f"Fetching results for {date}")
        fixtures = self._get_finished_fixtures(date)

        results = []
        for ticket_data in predictions_data:
            ticket = TicketResult(
                ticket_id=ticket_data["ticket_id"],
                ticket_name=ticket_data["ticket_name"],
                date=datetime.fromisoformat(ticket_data["date"]),
                total_odds=ticket_data["total_odds"]
            )

            for pred_data in ticket_data["predictions"]:
                pred = PredictionResult.from_dict(pred_data)

                # Trouver le résultat du match
                match_result = fixtures.get(pred.match_id)
                if match_result:
                    pred.home_score = match_result["home_score"]
                    pred.away_score = match_result["away_score"]
                    pred.evaluate()

                    # Mettre à jour les données
                    pred_data["home_score"] = pred.home_score
                    pred_data["away_score"] = pred.away_score
                    pred_data["result"] = pred.result.value

                ticket.predictions.append(pred)

            results.append(ticket)

        # Sauvegarder les résultats mis à jour
        with open(predictions_file, "w", encoding="utf-8") as f:
            json.dump(predictions_data, f, ensure_ascii=False, indent=2)

        # Mettre à jour l'historique global
        self._update_history(results, date)

        logger.info(f"Results checked for {date}: {len(results)} tickets")
        return results

    def _get_finished_fixtures(self, date: str) -> Dict[int, Dict]:
        """Récupère les matchs terminés pour une date"""
        data = self.api._make_request("fixtures", {"date": date, "status": "FT"})

        fixtures = {}
        if data and "response" in data:
            for fixture in data["response"]:
                match_id = fixture["fixture"]["id"]
                fixtures[match_id] = {
                    "home_score": fixture["goals"]["home"],
                    "away_score": fixture["goals"]["away"],
                    "status": fixture["fixture"]["status"]["short"]
                }

        return fixtures

    def _update_history(self, results: List[TicketResult], date: str):
        """Met à jour l'historique global"""
        history = self._load_history()

        # Ajouter ou mettre à jour les résultats du jour
        history[date] = {
            "tickets": [t.to_dict() for t in results],
            "updated_at": datetime.now().isoformat()
        }

        self._save_history(history)

    def _load_history(self) -> Dict:
        """Charge l'historique"""
        if os.path.exists(self.history_file):
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_history(self, history: Dict):
        """Sauvegarde l'historique"""
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    def get_daily_stats(self, date: str = None) -> DailyStats:
        """Calcule les statistiques pour une journée"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        history = self._load_history()
        day_data = history.get(date, {})

        stats = DailyStats(date=datetime.fromisoformat(date))

        if "tickets" not in day_data:
            return stats

        for ticket_data in day_data["tickets"]:
            ticket = TicketResult.from_dict(ticket_data)
            stats.total_tickets += 1
            stats.total_stake += ticket.stake

            if ticket.status == BetResult.WON:
                stats.tickets_won += 1
                stats.total_profit += ticket.profit
            elif ticket.status == BetResult.LOST:
                stats.tickets_lost += 1
                stats.total_profit += ticket.profit

            for pred in ticket.predictions:
                stats.total_predictions += 1
                if pred.result == BetResult.WON:
                    stats.won += 1
                elif pred.result == BetResult.LOST:
                    stats.lost += 1
                elif pred.result == BetResult.VOID:
                    stats.void += 1
                else:
                    stats.pending += 1

        return stats

    def get_global_stats(self, days: int = 30) -> Dict:
        """Calcule les statistiques globales sur une période"""
        history = self._load_history()

        total_stats = {
            "period_days": days,
            "total_predictions": 0,
            "won": 0,
            "lost": 0,
            "void": 0,
            "win_rate": 0.0,
            "total_tickets": 0,
            "tickets_won": 0,
            "tickets_lost": 0,
            "ticket_win_rate": 0.0,
            "total_stake": 0.0,
            "total_profit": 0.0,
            "roi": 0.0,
            "best_day": None,
            "worst_day": None,
            "current_streak": 0,
            "best_streak": 0,
            "daily_stats": []
        }

        cutoff_date = datetime.now() - timedelta(days=days)
        daily_profits = []

        for date_str, day_data in sorted(history.items()):
            try:
                date = datetime.fromisoformat(date_str)
                if date < cutoff_date:
                    continue
            except:
                continue

            day_stats = self.get_daily_stats(date_str)
            total_stats["total_predictions"] += day_stats.total_predictions
            total_stats["won"] += day_stats.won
            total_stats["lost"] += day_stats.lost
            total_stats["void"] += day_stats.void
            total_stats["total_tickets"] += day_stats.total_tickets
            total_stats["tickets_won"] += day_stats.tickets_won
            total_stats["tickets_lost"] += day_stats.tickets_lost
            total_stats["total_stake"] += day_stats.total_stake
            total_stats["total_profit"] += day_stats.total_profit

            daily_profits.append({
                "date": date_str,
                "profit": day_stats.total_profit,
                "win_rate": day_stats.win_rate
            })
            total_stats["daily_stats"].append(day_stats.to_dict())

        # Calculer les taux
        decided = total_stats["won"] + total_stats["lost"]
        if decided > 0:
            total_stats["win_rate"] = round(total_stats["won"] / decided * 100, 2)

        if total_stats["total_tickets"] > 0:
            tickets_decided = total_stats["tickets_won"] + total_stats["tickets_lost"]
            if tickets_decided > 0:
                total_stats["ticket_win_rate"] = round(total_stats["tickets_won"] / tickets_decided * 100, 2)

        if total_stats["total_stake"] > 0:
            total_stats["roi"] = round(total_stats["total_profit"] / total_stats["total_stake"] * 100, 2)

        # Meilleur/pire jour
        if daily_profits:
            best = max(daily_profits, key=lambda x: x["profit"])
            worst = min(daily_profits, key=lambda x: x["profit"])
            total_stats["best_day"] = best
            total_stats["worst_day"] = worst

        total_stats["total_profit"] = round(total_stats["total_profit"], 2)

        return total_stats

    def format_results_report(self, results: List[TicketResult], stats: DailyStats) -> str:
        """Formate le rapport de résultats"""
        lines = [
            "=" * 50,
            f"📊 RÉSULTATS DU {stats.date.strftime('%d/%m/%Y')}",
            "=" * 50,
            ""
        ]

        for ticket in results:
            status_emoji = "✅" if ticket.status == BetResult.WON else "❌" if ticket.status == BetResult.LOST else "⏳"
            lines.append(f"{status_emoji} TICKET #{ticket.ticket_id} - {ticket.ticket_name}")
            lines.append(f"   Résultat: {ticket.won_count}/{len(ticket.predictions)} paris gagnés")

            if ticket.status == BetResult.WON:
                lines.append(f"   💰 Gain: +{ticket.profit:.2f}€")
            elif ticket.status == BetResult.LOST:
                lines.append(f"   💸 Perte: {ticket.profit:.2f}€")

            lines.append("")

            for pred in ticket.predictions:
                result_emoji = "✅" if pred.result == BetResult.WON else "❌" if pred.result == BetResult.LOST else "⏳"
                score = f"{pred.home_score}-{pred.away_score}" if pred.home_score is not None else "N/A"
                lines.append(f"   {result_emoji} {pred.home_team} vs {pred.away_team}: {score}")
                lines.append(f"      Pari: {pred.bet_type} → {pred.result.value}")

            lines.append("-" * 50)
            lines.append("")

        # Résumé
        lines.extend([
            "📈 RÉSUMÉ DU JOUR",
            f"   Paris: {stats.won}✅ / {stats.lost}❌ ({stats.win_rate:.1f}%)",
            f"   Tickets: {stats.tickets_won}✅ / {stats.tickets_lost}❌",
            f"   Profit: {stats.total_profit:+.2f}€ (ROI: {stats.roi:+.1f}%)",
        ])

        return "\n".join(lines)
