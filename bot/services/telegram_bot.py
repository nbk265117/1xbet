"""
Module de notification Telegram
"""
import requests
import logging
from typing import List, Optional, Dict
from datetime import datetime
from models.match import Ticket, Prediction
from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Gère les notifications Telegram"""

    def __init__(self, token: str = None, chat_id: str = None):
        self.token = token or TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """
        Envoie un message Telegram
        Args:
            text: Le message à envoyer
            parse_mode: HTML ou Markdown
        Returns:
            True si envoyé avec succès
        """
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()

            if result.get("ok"):
                logger.info("Message sent successfully to Telegram")
                return True
            else:
                logger.error(f"Telegram API error: {result}")
                return False

        except requests.RequestException as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    def send_tickets(self, tickets: List[Ticket]) -> bool:
        """Envoie tous les tickets du jour"""
        if not tickets:
            return self.send_message("⚠️ Aucun ticket généré pour demain.")

        # Message d'introduction
        intro = self._format_intro(tickets)
        self.send_message(intro)

        # Envoyer chaque ticket séparément
        for ticket in tickets:
            ticket_msg = self._format_ticket(ticket)
            self.send_message(ticket_msg)

        # Message de conclusion
        outro = self._format_outro()
        self.send_message(outro)

        return True

    def _format_intro(self, tickets: List[Ticket]) -> str:
        """Formate le message d'introduction"""
        tomorrow = datetime.now().strftime("%d/%m/%Y")
        total_selections = sum(len(t) for t in tickets)

        return f"""
🎯 <b>PRÉDICTIONS DU JOUR</b> 🎯
━━━━━━━━━━━━━━━━━━━━

📅 <b>Date:</b> {tomorrow}
🎟️ <b>Tickets:</b> {len(tickets)}
⚽ <b>Sélections:</b> {total_selections}

<i>Voici les tickets optimisés pour demain...</i>
"""

    def _format_ticket(self, ticket: Ticket) -> str:
        """Formate un ticket pour Telegram"""
        # Emoji selon le niveau de risque
        risk_emoji = {"FAIBLE": "🟢", "MOYEN": "🟡", "ÉLEVÉ": "🔴"}.get(ticket.risk_level, "⚪")
        conf_emoji = {"ÉLEVÉ": "⭐⭐⭐", "MOYEN": "⭐⭐", "FAIBLE": "⭐"}.get(ticket.confidence_level, "⭐")

        lines = [
            f"🎟️ <b>TICKET #{ticket.id} - {ticket.name}</b>",
            f"━━━━━━━━━━━━━━━━━━━━",
            f"📊 Confiance: {conf_emoji}",
            f"⚡ Risque: {risk_emoji} {ticket.risk_level}",
            f"💰 Cote totale: <b>{ticket.total_odds:.2f}</b>",
            f"",
            f"📋 <b>SÉLECTIONS:</b>",
        ]

        for i, pred in enumerate(ticket.predictions, 1):
            match_time = pred.match.date.strftime("%H:%M")
            lines.append(f"")
            lines.append(f"<b>{i}.</b> {pred.match.home_team.name} vs {pred.match.away_team.name}")
            lines.append(f"   🏆 {pred.match.league_name}")
            lines.append(f"   ⏰ {match_time}")
            lines.append(f"   🎯 <b>{pred.bet_type.value}</b> @ ~{pred.odds_estimate:.2f}")
            lines.append(f"   💡 <i>{pred.reasoning[:80]}...</i>" if len(pred.reasoning) > 80 else f"   💡 <i>{pred.reasoning}</i>")

        return "\n".join(lines)

    def _format_outro(self) -> str:
        """Formate le message de conclusion"""
        return """
━━━━━━━━━━━━━━━━━━━━
⚠️ <b>AVERTISSEMENT</b>

Les paris sportifs comportent des risques.
Ne misez que ce que vous pouvez vous permettre de perdre.

Ces prédictions sont basées sur des analyses statistiques
et ne garantissent pas de gains.

🤖 <i>Bot 1xBet Predictions</i>
"""

    def send_daily_summary(self, tickets: List[Ticket], matches_analyzed: int) -> bool:
        """Envoie un résumé quotidien"""
        if not tickets:
            message = f"""
📊 <b>RÉSUMÉ QUOTIDIEN</b>
━━━━━━━━━━━━━━━━━━━━

⚽ Matchs analysés: {matches_analyzed}
🎟️ Tickets générés: 0

<i>Pas assez de matchs intéressants aujourd'hui.</i>
"""
        else:
            high_conf = sum(1 for t in tickets for p in t.predictions if p.confidence == "ÉLEVÉ")
            total_selections = sum(len(t) for t in tickets)

            message = f"""
📊 <b>RÉSUMÉ QUOTIDIEN</b>
━━━━━━━━━━━━━━━━━━━━

⚽ Matchs analysés: {matches_analyzed}
🎟️ Tickets générés: {len(tickets)}
📋 Sélections totales: {total_selections}
⭐ Confiance élevée: {high_conf}

<b>Tickets disponibles:</b>
"""
            for ticket in tickets:
                message += f"\n• {ticket.name} ({len(ticket)} matchs) - {ticket.confidence_level}"

        return self.send_message(message)

    def send_error_notification(self, error: str) -> bool:
        """Envoie une notification d'erreur"""
        message = f"""
❌ <b>ERREUR BOT</b>
━━━━━━━━━━━━━━━━━━━━

Une erreur s'est produite lors de l'exécution:

<code>{error[:500]}</code>

<i>Veuillez vérifier les logs.</i>
"""
        return self.send_message(message)

    def send_startup_notification(self) -> bool:
        """Envoie une notification de démarrage"""
        message = f"""
🚀 <b>BOT DÉMARRÉ</b>
━━━━━━━━━━━━━━━━━━━━

Le bot de prédictions 1xBet est en ligne!

⏰ Prochaine exécution: 21h00
📅 Prédictions pour: Demain

<i>Utilisez /status pour vérifier l'état du bot.</i>
"""
        return self.send_message(message)

    def test_connection(self) -> bool:
        """Teste la connexion au bot Telegram"""
        url = f"{self.base_url}/getMe"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            result = response.json()

            if result.get("ok"):
                bot_info = result.get("result", {})
                logger.info(f"Connected to Telegram bot: @{bot_info.get('username')}")
                return True
            return False

        except requests.RequestException as e:
            logger.error(f"Telegram connection test failed: {e}")
            return False

    def send_results(self, results: List, stats) -> bool:
        """Envoie les résultats des paris"""
        from models.result import BetResult

        if not results:
            return self.send_message("📊 Aucun résultat à afficher pour aujourd'hui.")

        # Message d'introduction avec résumé
        date_str = stats.date.strftime("%d/%m/%Y")
        profit_emoji = "📈" if stats.total_profit >= 0 else "📉"

        intro = f"""
📊 <b>RÉSULTATS DU {date_str}</b>
━━━━━━━━━━━━━━━━━━━━

✅ Paris gagnés: <b>{stats.won}</b>
❌ Paris perdus: <b>{stats.lost}</b>
📈 Taux de réussite: <b>{stats.win_rate:.1f}%</b>

🎟️ Tickets gagnés: <b>{stats.tickets_won}</b>/{stats.total_tickets}
{profit_emoji} Profit du jour: <b>{stats.total_profit:+.2f}€</b>
💹 ROI: <b>{stats.roi:+.1f}%</b>
"""
        self.send_message(intro)

        # Détail de chaque ticket
        for ticket in results:
            self._send_ticket_result(ticket)

        return True

    def _send_ticket_result(self, ticket) -> bool:
        """Envoie le résultat d'un ticket"""
        from models.result import BetResult

        status_emoji = "✅" if ticket.status == BetResult.WON else "❌" if ticket.status == BetResult.LOST else "⏳"
        profit_text = f"+{ticket.profit:.2f}€" if ticket.profit > 0 else f"{ticket.profit:.2f}€"

        lines = [
            f"{status_emoji} <b>TICKET #{ticket.ticket_id} - {ticket.ticket_name}</b>",
            f"━━━━━━━━━━━━━━━━━━━━",
            f"📊 Score: {ticket.won_count}/{len(ticket.predictions)} paris gagnés",
            f"💰 Résultat: <b>{profit_text}</b>",
            f"",
            f"📋 <b>Détails:</b>"
        ]

        for pred in ticket.predictions:
            result_emoji = "✅" if pred.result == BetResult.WON else "❌" if pred.result == BetResult.LOST else "⏳"
            score = f"{pred.home_score}-{pred.away_score}" if pred.home_score is not None else "N/A"

            lines.append(f"")
            lines.append(f"{result_emoji} {pred.home_team} vs {pred.away_team}")
            lines.append(f"   📍 Score: <b>{score}</b>")
            lines.append(f"   🎯 Pari: {pred.bet_type}")
            lines.append(f"   📌 {pred.result.value}")

        return self.send_message("\n".join(lines))

    def send_pro_predictions(self, predictions: List[Dict]) -> bool:
        """
        [PRO] Envoie les prédictions détaillées avec mi-temps, cartons, corners
        """
        if not predictions:
            return self.send_message("⚠️ Aucune prédiction Pro disponible.")

        # Message d'introduction
        date_str = datetime.now().strftime("%d/%m/%Y")
        intro = f"""
🎯 <b>PRÉDICTIONS PRO DU JOUR</b> 🎯
━━━━━━━━━━━━━━━━━━━━
📅 Date: {date_str}
⚽ Matchs analysés: {len(predictions)}

<i>Analyse complète avec Mi-temps, Cartons & Corners</i>
"""
        self.send_message(intro)

        # Envoyer chaque match (max 10 pour éviter spam)
        for pred in predictions[:10]:
            msg = self._format_pro_prediction(pred)
            self.send_message(msg)

        return True

    def _format_pro_prediction(self, pred: Dict) -> str:
        """Formate une prédiction Pro complète"""
        match = pred.get('match', 'Match inconnu')
        league = pred.get('league', '')
        date = pred.get('date', '')
        importance = pred.get('match_importance', 'NORMAL')
        description = pred.get('match_description', '')[:150]

        # Importance emoji
        imp_emoji = {"CRUCIAL": "🔥", "IMPORTANT": "⭐", "NORMAL": "⚽"}.get(importance, "⚽")

        # Goals data
        goals = pred.get('goals', {})
        result = pred.get('result_1x2', '')
        over_under = goals.get('over_under', '')
        btts = goals.get('btts', '')
        score_exact = goals.get('score_exact', '')

        # First half data
        first_half = pred.get('first_half', {})
        ht_result = first_half.get('result', '')
        ht_score = first_half.get('score_exact', '')
        ht_over_05 = first_half.get('over_05_prob', 0)

        # HT/FT
        ht_ft_data = pred.get('ht_ft', {})
        ht_ft = ht_ft_data.get('prediction', '')
        ht_ft_prob = ht_ft_data.get('probability', 0)

        # Corners
        corners = pred.get('corners', {})
        corners_pred = corners.get('prediction', '')
        corners_expected = corners.get('expected', 0)
        corners_rec = corners.get('recommendation', '')

        # Cards
        cards = pred.get('cards', {})
        cards_expected = cards.get('expected_yellow', 0)
        cards_rec = cards.get('recommendation', '')
        red_prob = cards.get('red_card_prob', 0)

        lines = [
            f"{imp_emoji} <b>{match}</b>",
            f"━━━━━━━━━━━━━━━━━━━━",
            f"🏆 {league} | ⏰ {date}",
            f"📝 <i>{description}</i>",
            f"",
            f"<b>📊 MATCH COMPLET</b>",
            f"🎯 1X2: <b>{result}</b>",
            f"⚽ Buts: <b>{over_under}</b> | BTTS: <b>{btts}</b>",
            f"📌 Score exact: <b>{score_exact}</b>",
            f"",
            f"<b>⏱️ 1ÈRE MI-TEMPS</b>",
            f"🎯 Résultat MT: <b>{ht_result}</b>",
            f"📌 Score MT: <b>{ht_score}</b>",
            f"⚽ MT Over 0.5: <b>{ht_over_05:.0f}%</b>",
            f"",
            f"<b>🔄 MI-TEMPS / FIN</b>",
            f"🎯 HT/FT: <b>{ht_ft}</b> ({ht_ft_prob:.0f}%)",
            f"",
            f"<b>🚩 CORNERS</b>",
            f"📊 Attendus: <b>{corners_expected:.1f}</b>",
            f"🎯 Pari: <b>{corners_rec}</b>",
            f"",
            f"<b>🟨 CARTONS</b>",
            f"📊 Jaunes attendus: <b>{cards_expected:.1f}</b>",
            f"🎯 Pari: <b>{cards_rec}</b>",
            f"🟥 Rouge: <b>{red_prob:.0f}%</b>",
        ]

        return "\n".join(lines)

    def send_weekly_stats(self, stats: Dict) -> bool:
        """Envoie les statistiques hebdomadaires"""
        profit_emoji = "📈" if stats["total_profit"] >= 0 else "📉"
        roi_emoji = "🟢" if stats["roi"] >= 0 else "🔴"

        message = f"""
📊 <b>STATISTIQUES ({stats['period_days']} JOURS)</b>
━━━━━━━━━━━━━━━━━━━━

<b>🎯 PARIS</b>
✅ Gagnés: {stats['won']}
❌ Perdus: {stats['lost']}
📈 Taux: <b>{stats['win_rate']:.1f}%</b>

<b>🎟️ TICKETS</b>
✅ Gagnés: {stats['tickets_won']}
❌ Perdus: {stats['tickets_lost']}
📈 Taux: <b>{stats['ticket_win_rate']:.1f}%</b>

<b>💰 FINANCES</b>
💵 Mise totale: {stats['total_stake']:.2f}€
{profit_emoji} Profit: <b>{stats['total_profit']:+.2f}€</b>
{roi_emoji} ROI: <b>{stats['roi']:+.1f}%</b>
"""

        if stats.get("best_day"):
            message += f"""
<b>📅 JOURS REMARQUABLES</b>
🏆 Meilleur: {stats['best_day']['date']} (+{stats['best_day']['profit']:.2f}€)
💀 Pire: {stats['worst_day']['date']} ({stats['worst_day']['profit']:.2f}€)
"""

        message += """
━━━━━━━━━━━━━━━━━━━━
🤖 <i>Bot 1xBet Predictions</i>
"""

        return self.send_message(message)
