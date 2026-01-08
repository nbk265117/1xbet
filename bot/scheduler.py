#!/usr/bin/env python3
"""
Scheduler automatique pour les prédictions à 21h
Lance les prédictions complètes chaque jour
"""
import sys
import os
import json
import logging
import schedule
import time
import requests
from datetime import datetime, timedelta
import pytz

# Ajouter le dossier bot au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import (
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
    EXECUTION_HOUR, TIMEZONE, OUTPUT_DIR
)
from services.football_api import FootballAPIService
from services.enhanced_analyzer import EnhancedMatchAnalyzer

# Configuration du logging
LOG_FILE = os.path.join(os.path.dirname(__file__), "scheduler.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Timezone
TZ = pytz.timezone(TIMEZONE)


class PredictionScheduler:
    """Scheduler pour les prédictions automatiques"""

    def __init__(self):
        self.api = FootballAPIService()
        self.analyzer = EnhancedMatchAnalyzer()
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    def send_telegram(self, text: str) -> bool:
        """Envoie un message sur Telegram"""
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "Markdown"
            }
            r = requests.post(url, data=data, timeout=10)
            time.sleep(0.5)  # Rate limit
            return r.status_code == 200
        except Exception as e:
            logger.error(f"Telegram error: {e}")
            return False

    def run_predictions(self):
        """Génère et envoie les prédictions du lendemain"""
        logger.info("=" * 60)
        logger.info("🚀 DÉMARRAGE DES PRÉDICTIONS")
        logger.info("=" * 60)

        try:
            # Date de demain
            tomorrow = (datetime.now(TZ) + timedelta(days=1)).strftime("%Y-%m-%d")
            tomorrow_display = (datetime.now(TZ) + timedelta(days=1)).strftime("%d/%m/%Y")

            # Notification de démarrage
            self.send_telegram(f"🤖 *Bot démarré*\n📅 Analyse des matchs du {tomorrow_display}...")

            # 1. Récupérer les matchs
            logger.info(f"Fetching matches for {tomorrow}...")
            matches = self.api.get_fixtures_by_date(tomorrow)
            logger.info(f"Found {len(matches)} matches")

            if not matches:
                self.send_telegram(f"⚠️ Aucun match trouvé pour le {tomorrow_display}")
                return

            # 2. Analyser chaque match
            logger.info("Analyzing matches...")
            predictions = []

            for match in matches[:50]:  # Plan Pro = jusqu'à 50 matchs
                try:
                    pred = self.analyzer.analyze_match_full(
                        home_team=match.home_team.name,
                        away_team=match.away_team.name,
                        league=match.league_name,
                        match_date=match.date.strftime("%Y-%m-%d %H:%M"),
                        league_id=match.league_id,
                        home_team_id=match.home_team.id,
                        away_team_id=match.away_team.id
                    )
                    predictions.append({
                        "match": match,
                        "prediction": pred
                    })
                except Exception as e:
                    logger.error(f"Error analyzing {match}: {e}")

            logger.info(f"Analyzed {len(predictions)} matches")

            # 3. Envoyer les prédictions
            self._send_predictions(predictions, tomorrow_display)

            # 4. Sauvegarder
            self._save_predictions(predictions, tomorrow)

            logger.info("✅ Prédictions terminées!")

        except Exception as e:
            logger.exception(f"Error in predictions: {e}")
            self.send_telegram(f"❌ *Erreur Bot*\n`{str(e)}`")

    def _send_predictions(self, predictions: list, date_display: str):
        """Envoie toutes les prédictions sur Telegram"""

        # En-tête
        header = f"""🎯 *PRÉDICTIONS DU {date_display}*
━━━━━━━━━━━━━━━━━━━━━━━━

📊 *{len(predictions)} MATCHS ANALYSÉS*
🔮 Score exact • Corners • BTTS • DC

━━━━━━━━━━━━━━━━━━━━━━━━
"""
        self.send_telegram(header)

        # Grouper par ligue
        leagues = {}
        for item in predictions:
            league = item["match"].league_name
            if league not in leagues:
                leagues[league] = []
            leagues[league].append(item)

        # Envoyer par ligue
        for league_name, items in leagues.items():
            # Titre de la ligue
            self.send_telegram(f"🏆 *{league_name}*")

            for item in items:
                match = item["match"]
                pred = item["prediction"]

                conf_emoji = "✅" if pred.confidence == "ÉLEVÉ" else "🔶" if pred.confidence == "MOYEN" else "⚪"

                msg = f"""{conf_emoji} *{match.home_team.name} vs {match.away_team.name}*
⏰ {match.date.strftime("%H:%M")}

📊 *PRONOSTICS:*
├ 1X2: *{pred.result_1x2}*
├ Score: *{pred.score_exact}*
├ O/U: *{pred.over_under}* ({pred.over_25_prob*100:.0f}%)
├ BTTS: *{pred.btts}* ({pred.btts_prob*100:.0f}%)
├ Corners: *{pred.corners}* ({pred.expected_corners:.1f})
├ DC+BTTS: *{pred.dc_btts}*
└ MT/FT: *{pred.ht_ft}*

📈 🏠{pred.home_prob*100:.0f}% 🤝{pred.draw_prob*100:.0f}% ✈️{pred.away_prob*100:.0f}%
"""
                self.send_telegram(msg)

        # Résumé des best picks
        best_picks = [p for p in predictions if p["prediction"].confidence == "ÉLEVÉ"]
        if best_picks:
            summary = "━━━━━━━━━━━━━━━━━━━━━━━━\n🏆 *BEST PICKS (Confiance ÉLEVÉ)*\n\n"
            for item in best_picks[:5]:
                match = item["match"]
                pred = item["prediction"]
                summary += f"✅ {match.home_team.name} vs {match.away_team.name}\n"
                summary += f"   🎯 {pred.result_1x2} | Score: {pred.score_exact}\n\n"

            summary += "━━━━━━━━━━━━━━━━━━━━━━━━\n⚠️ Jouez responsable!\n🤖 بالقليل نديرو الكثير"
            self.send_telegram(summary)

    def _save_predictions(self, predictions: list, date: str):
        """Sauvegarde les prédictions en JSON"""
        output = {
            "date": date,
            "generated_at": datetime.now().isoformat(),
            "predictions": []
        }

        for item in predictions:
            match = item["match"]
            pred = item["prediction"]
            output["predictions"].append({
                "match": f"{match.home_team.name} vs {match.away_team.name}",
                "league": match.league_name,
                "time": match.date.strftime("%H:%M"),
                "1x2": pred.result_1x2,
                "score_exact": pred.score_exact,
                "over_under": pred.over_under,
                "btts": pred.btts,
                "corners": pred.corners,
                "dc_btts": pred.dc_btts,
                "ht_ft": pred.ht_ft,
                "confidence": pred.confidence
            })

        filepath = os.path.join(OUTPUT_DIR, f"predictions_{date}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved: {filepath}")


def main():
    """Point d'entrée principal"""
    scheduler = PredictionScheduler()

    print("=" * 60)
    print(f"🤖 SCHEDULER DE PRÉDICTIONS")
    print(f"⏰ Exécution quotidienne à {EXECUTION_HOUR}:00 ({TIMEZONE})")
    print(f"📱 Groupe: {TELEGRAM_CHAT_ID}")
    print("=" * 60)

    # Notification de démarrage
    now = datetime.now(TZ).strftime("%d/%m/%Y %H:%M")
    scheduler.send_telegram(f"""🤖 *Scheduler Démarré*
━━━━━━━━━━━━━━━━━━━━━━━━
⏰ Heure: {now}
📅 Exécution quotidienne à {EXECUTION_HOUR}:00
🌍 Timezone: {TIMEZONE}
━━━━━━━━━━━━━━━━━━━━━━━━
""")

    # Planifier l'exécution quotidienne
    schedule.every().day.at(f"{EXECUTION_HOUR:02d}:00").do(scheduler.run_predictions)

    logger.info(f"Scheduler started. Next run at {EXECUTION_HOUR}:00")

    # Boucle principale
    while True:
        schedule.run_pending()
        time.sleep(60)  # Vérifier toutes les minutes


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scheduler de prédictions")
    parser.add_argument("--now", action="store_true", help="Exécuter maintenant")
    parser.add_argument("--daemon", action="store_true", help="Lancer en arrière-plan")

    args = parser.parse_args()

    if args.now:
        # Exécuter immédiatement
        scheduler = PredictionScheduler()
        scheduler.run_predictions()
    else:
        # Lancer le scheduler
        main()
