#!/usr/bin/env python3
"""
Bot de prédictions de paris sportifs 1xBet
Exécution automatique à 21h chaque jour
"""
import sys
import os
import json
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Ajouter le dossier bot au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import (
    EXECUTION_HOUR, OUTPUT_DIR, LOG_FILE,
    MIN_TICKETS_PER_DAY, MAX_TICKETS_PER_DAY
)
from services.football_api import FootballAPIService
from services.analyzer import MatchAnalyzer
from services.enhanced_analyzer import EnhancedMatchAnalyzer
from services.ticket_generator import TicketGenerator
from services.telegram_bot import TelegramNotifier
from services.result_tracker import ResultTracker

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BettingBot:
    """Bot principal de prédictions"""

    def __init__(self, use_pro_features: bool = True):
        self.api = FootballAPIService()
        self.analyzer = MatchAnalyzer()
        self.enhanced_analyzer = EnhancedMatchAnalyzer() if use_pro_features else None
        self.ticket_gen = TicketGenerator(self.analyzer)
        self.telegram = TelegramNotifier()
        self.tracker = ResultTracker()
        self.use_pro_features = use_pro_features

        # Créer le dossier output si nécessaire
        Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

        # Cache des ligues prioritaires
        self._priority_league_ids = None

    def _get_priority_leagues(self) -> set:
        """Retourne les IDs des ligues prioritaires (priority 1-2)"""
        if self._priority_league_ids is None:
            from config.leagues import ALLOWED_LEAGUES
            self._priority_league_ids = {
                lid for lid, info in ALLOWED_LEAGUES.items()
                if info.get("priority", 99) <= 2
            }
        return self._priority_league_ids

    def run(self, send_telegram: bool = True, save_output: bool = True, target_date: str = None) -> bool:
        """
        Exécute le bot pour générer les prédictions
        Args:
            target_date: Date spécifique (YYYY-MM-DD) ou None pour demain
        """
        logger.info("=" * 60)
        logger.info("Starting betting bot...")
        logger.info("=" * 60)

        try:
            # 1. Vérifier l'API
            logger.info("Checking API status...")
            api_status = self.api.check_api_status()
            if api_status:
                requests_remaining = api_status.get("requests", {}).get("current", 0)
                logger.info(f"API Status: OK - Requests today: {requests_remaining}")

            # 2. Récupérer les matchs
            if target_date:
                logger.info(f"Fetching matches for {target_date}...")
                self._current_date_str = target_date
            else:
                logger.info("Fetching tomorrow's matches...")
                self._current_date_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

            # Utiliser la nouvelle méthode qui charge tous les matchs importants
            matches, league_stats = self.api.get_all_fixtures_by_date(self._current_date_str)
            logger.info(f"Found {len(matches)} matches across {len(league_stats)} leagues")

            if not matches:
                logger.warning("No matches found for tomorrow")
                if send_telegram:
                    self.telegram.send_message("⚠️ Aucun match trouvé pour demain dans les ligues suivies.")
                return False

            # 3. Enrichir les données des matchs (H2H, forme, classement)
            logger.info("Enriching match data...")
            if self.use_pro_features:
                logger.info("[PRO] Using enhanced analyzer with API predictions & odds")

            enriched_matches = []
            enhanced_predictions = []

            # Limiter aux matchs prioritaires (priority 1-2) pour l'enrichissement
            priority_matches = [m for m in matches if m.league_id in self._get_priority_leagues()]
            other_matches = [m for m in matches if m.league_id not in self._get_priority_leagues()]

            # Enrichir d'abord les matchs prioritaires, puis les autres si quota API disponible
            matches_to_enrich = priority_matches[:40] + other_matches[:20]  # Max 60 matchs
            logger.info(f"Enriching {len(matches_to_enrich)} matches ({len(priority_matches)} priority + {min(20, len(other_matches))} others)")

            for i, match in enumerate(matches_to_enrich):  # Limiter pour éviter trop d'appels API
                logger.info(f"  [{i+1}/{len(matches_to_enrich)}] {match}")
                try:
                    # Enrichissement de base
                    enriched = self.api.enrich_match_data(match)
                    enriched_matches.append(enriched)

                    # [PRO] Analyse avancée avec prédictions API et cotes
                    if self.use_pro_features and self.enhanced_analyzer:
                        try:
                            enhanced_pred = self.enhanced_analyzer.analyze_match_full(
                                home_team=match.home_team.name,
                                away_team=match.away_team.name,
                                league=match.league_name,
                                match_date=match.date.strftime("%Y-%m-%d %H:%M"),
                                league_id=match.league_id,
                                home_team_id=match.home_team.id,
                                away_team_id=match.away_team.id,
                                fixture_id=match.id
                            )
                            enhanced_predictions.append({
                                'match': match,
                                'prediction': enhanced_pred
                            })
                            logger.info(f"    [PRO] {enhanced_pred.result_1x2} | {enhanced_pred.over_under} | BTTS: {enhanced_pred.btts}")
                        except Exception as e:
                            logger.warning(f"    [PRO] Enhanced analysis failed: {e}")

                except Exception as e:
                    logger.error(f"Error enriching {match}: {e}")
                    enriched_matches.append(match)  # Utiliser les données de base

            # Sauvegarder les prédictions améliorées
            if enhanced_predictions:
                self._save_enhanced_predictions(enhanced_predictions)

            # 4. Générer les tickets
            logger.info("Generating tickets...")
            tickets = self.ticket_gen.generate_tickets(enriched_matches)
            logger.info(f"Generated {len(tickets)} tickets")

            # 5. Sauvegarder les résultats
            if save_output:
                self._save_output(tickets, enriched_matches)
                # Sauvegarder pour le suivi des résultats
                target = datetime.strptime(self._current_date_str, "%Y-%m-%d")
                self.tracker.save_predictions(tickets, target)

            # 6. Envoyer les Prédictions en format DÉTAILLÉ + TABLEAU sur Telegram
            if send_telegram:
                logger.info("Sending predictions (detailed + table) to Telegram...")
                pro_file = os.path.join(OUTPUT_DIR, f"predictions_complete_{self._current_date_str}.json")
                if os.path.exists(pro_file):
                    with open(pro_file, 'r', encoding='utf-8') as f:
                        pro_data = json.load(f)
                    # Envoyer format détaillé pour chaque match + tableau récapitulatif
                    self.telegram.send_predictions_full(pro_data.get('predictions', []), target_date=self._current_date_str)

            # 7. Afficher le résumé
            self._print_summary(tickets, len(enriched_matches))

            logger.info("Bot execution completed successfully!")
            return True

        except Exception as e:
            logger.exception(f"Bot execution failed: {e}")
            if send_telegram:
                self.telegram.send_error_notification(str(e))
            return False

    def _save_enhanced_predictions(self, enhanced_predictions):
        """[PRO] Sauvegarde les prédictions améliorées avec tous les marchés"""
        date_str = getattr(self, '_current_date_str', (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"))
        json_path = os.path.join(OUTPUT_DIR, f"predictions_complete_{date_str}.json")

        output = {
            "date": date_str,
            "generated_at": datetime.now().isoformat(),
            "total_matches": len(enhanced_predictions),
            "predictions": []
        }

        for item in enhanced_predictions:
            match = item['match']
            pred = item['prediction']

            output["predictions"].append({
                "match": pred.match_name,
                "league": pred.league,
                "date": pred.date,
                "match_description": pred.match_description,
                "match_importance": pred.match_importance,
                "confidence": pred.confidence,

                # ========== 1X2 Match complet ==========
                "result_1x2": pred.result_1x2,
                "probabilities": {
                    "home": round(pred.home_prob * 100, 1),
                    "draw": round(pred.draw_prob * 100, 1),
                    "away": round(pred.away_prob * 100, 1)
                },

                # ========== Buts ==========
                "goals": {
                    "over_under": pred.over_under,
                    "expected_goals": round(pred.total_expected_goals, 2),
                    "over_15_prob": round(pred.over_15_prob * 100, 1),
                    "over_25_prob": round(pred.over_25_prob * 100, 1),
                    "over_35_prob": round(pred.over_35_prob * 100, 1),
                    "btts": pred.btts,
                    "btts_prob": round(pred.btts_prob * 100, 1),
                    "score_exact": pred.score_exact,
                    "clean_sheet": pred.clean_sheet,
                    "dc_btts": pred.dc_btts
                },

                # ========== Mi-temps (1ère période) ==========
                "first_half": {
                    "result": pred.ht_result,
                    "probabilities": {
                        "home": round(pred.ht_home_prob * 100, 1),
                        "draw": round(pred.ht_draw_prob * 100, 1),
                        "away": round(pred.ht_away_prob * 100, 1)
                    },
                    "expected_goals": round(pred.ht_expected_goals, 2),
                    "over_05": pred.ht_over_05,
                    "over_05_prob": round(pred.ht_over_05_prob * 100, 1),
                    "over_15": pred.ht_over_15,
                    "over_15_prob": round(pred.ht_over_15_prob * 100, 1),
                    "btts": pred.ht_btts,
                    "btts_prob": round(pred.ht_btts_prob * 100, 1),
                    "score_exact": pred.ht_score_exact
                },

                # ========== 2ème Mi-temps ==========
                "second_half": {
                    "expected_goals": round(pred.h2_expected_goals, 2),
                    "over_05": pred.h2_over_05,
                    "over_05_prob": round(pred.h2_over_05_prob * 100, 1),
                    "over_15": pred.h2_over_15,
                    "over_15_prob": round(pred.h2_over_15_prob * 100, 1)
                },

                # ========== HT/FT ==========
                "ht_ft": {
                    "prediction": pred.ht_ft,
                    "probability": round(pred.ht_ft_prob * 100, 1),
                    "alternatives": pred.ht_ft_alternatives
                },

                # ========== Corners ==========
                "corners": {
                    "prediction": pred.corners,
                    "expected": round(pred.expected_corners, 1),
                    "home_avg": round(pred.home_corners_avg, 1),
                    "away_avg": round(pred.away_corners_avg, 1),
                    "over_85_prob": round(pred.corners_over_85_prob * 100, 1),
                    "over_95_prob": round(pred.corners_over_95_prob * 100, 1),
                    "over_105_prob": round(pred.corners_over_105_prob * 100, 1),
                    "recommendation": pred.corners_recommendation
                },

                # ========== Cartons ==========
                "cards": {
                    "expected_yellow": round(pred.expected_yellow_cards, 1),
                    "expected_total": round(pred.expected_total_cards, 1),
                    "over_35_prob": round(pred.cards_over_35_prob * 100, 1),
                    "over_45_prob": round(pred.cards_over_45_prob * 100, 1),
                    "over_55_prob": round(pred.cards_over_55_prob * 100, 1),
                    "red_card_prob": round(pred.red_card_prob * 100, 1),
                    "recommendation": pred.cards_recommendation,
                    "referee": pred.referee_name,
                    "referee_strictness": pred.referee_strictness
                },

                "reasoning": pred.reasoning
            })

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        logger.info(f"[PRO] Saved enhanced predictions: {json_path}")

    def _save_output(self, tickets, matches):
        """Sauvegarde les résultats dans des fichiers"""
        date_str = getattr(self, '_current_date_str', (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"))

        # Sauvegarder en JSON
        json_path = os.path.join(OUTPUT_DIR, f"tickets_{date_str}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.ticket_gen.export_to_json(tickets), f, ensure_ascii=False, indent=2)
        logger.info(f"Saved JSON: {json_path}")

        # Sauvegarder en texte
        txt_path = os.path.join(OUTPUT_DIR, f"tickets_{date_str}.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(self.ticket_gen.format_tickets_for_output(tickets))
        logger.info(f"Saved TXT: {txt_path}")

    def _print_summary(self, tickets, matches_count):
        """Affiche un résumé dans la console"""
        print("\n" + "=" * 60)
        print("📊 RÉSUMÉ DE L'EXÉCUTION")
        print("=" * 60)
        print(f"⚽ Matchs analysés: {matches_count}")
        print(f"🎟️ Tickets générés: {len(tickets)}")

        if tickets:
            print("\n📋 TICKETS:")
            for ticket in tickets:
                print(f"  • {ticket.name}: {len(ticket)} sélections (Cote: {ticket.total_odds:.2f})")

        print("=" * 60 + "\n")

    def test_telegram(self):
        """Teste la connexion Telegram"""
        logger.info("Testing Telegram connection...")
        if self.telegram.test_connection():
            self.telegram.send_startup_notification()
            logger.info("Telegram test successful!")
            return True
        logger.error("Telegram test failed!")
        return False

    def test_api(self):
        """Teste la connexion à l'API Football"""
        logger.info("Testing Football API connection...")
        status = self.api.check_api_status()
        if status:
            account = status.get("account", {})
            requests = status.get("requests", {})
            print(f"✅ API OK")
            print(f"   Account: {account.get('firstname', 'N/A')} {account.get('lastname', '')}")
            print(f"   Plan: {status.get('subscription', {}).get('plan', 'N/A')}")
            print(f"   Requests today: {requests.get('current', 0)} / {requests.get('limit_day', 0)}")
            return True
        logger.error("API test failed!")
        return False

    def check_results(self, date: str = None, send_telegram: bool = True) -> bool:
        """
        Vérifie les résultats des paris pour une date donnée
        Args:
            date: Date au format YYYY-MM-DD (défaut: aujourd'hui)
            send_telegram: Envoyer les résultats sur Telegram
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        logger.info("=" * 60)
        logger.info(f"Checking results for {date}...")
        logger.info("=" * 60)

        try:
            # Vérifier les résultats
            results = self.tracker.check_results(date)

            if not results:
                logger.warning(f"No predictions found for {date}")
                if send_telegram:
                    self.telegram.send_message(f"📊 Aucune prédiction trouvée pour le {date}")
                return False

            # Calculer les statistiques
            stats = self.tracker.get_daily_stats(date)

            # Afficher le rapport
            report = self.tracker.format_results_report(results, stats)
            print(report)

            # Envoyer sur Telegram
            if send_telegram:
                logger.info("Sending results to Telegram...")
                self.telegram.send_results(results, stats)

            logger.info("Results check completed!")
            return True

        except Exception as e:
            logger.exception(f"Results check failed: {e}")
            if send_telegram:
                self.telegram.send_error_notification(str(e))
            return False

    def show_stats(self, days: int = 7, send_telegram: bool = False) -> bool:
        """
        Affiche les statistiques globales
        Args:
            days: Nombre de jours à analyser
            send_telegram: Envoyer sur Telegram
        """
        logger.info(f"Generating statistics for last {days} days...")

        stats = self.tracker.get_global_stats(days)

        print("\n" + "=" * 60)
        print(f"📊 STATISTIQUES ({days} DERNIERS JOURS)")
        print("=" * 60)
        print(f"\n🎯 PARIS")
        print(f"   ✅ Gagnés: {stats['won']}")
        print(f"   ❌ Perdus: {stats['lost']}")
        print(f"   📈 Taux de réussite: {stats['win_rate']:.1f}%")
        print(f"\n🎟️ TICKETS")
        print(f"   ✅ Gagnés: {stats['tickets_won']}")
        print(f"   ❌ Perdus: {stats['tickets_lost']}")
        print(f"   📈 Taux de réussite: {stats['ticket_win_rate']:.1f}%")
        print(f"\n💰 FINANCES")
        print(f"   💵 Mise totale: {stats['total_stake']:.2f}€")
        print(f"   {'📈' if stats['total_profit'] >= 0 else '📉'} Profit: {stats['total_profit']:+.2f}€")
        print(f"   {'🟢' if stats['roi'] >= 0 else '🔴'} ROI: {stats['roi']:+.1f}%")

        if stats.get("best_day"):
            print(f"\n📅 JOURS REMARQUABLES")
            print(f"   🏆 Meilleur: {stats['best_day']['date']} (+{stats['best_day']['profit']:.2f}€)")
            print(f"   💀 Pire: {stats['worst_day']['date']} ({stats['worst_day']['profit']:.2f}€)")

        print("=" * 60 + "\n")

        if send_telegram:
            self.telegram.send_weekly_stats(stats)

        return True


def run_scheduler():
    """Lance le scheduler pour exécution à 21h"""
    try:
        import schedule
        import time

        bot = BettingBot()

        logger.info(f"Scheduler started. Will run daily at {EXECUTION_HOUR}:00")
        bot.telegram.send_startup_notification()

        # Planifier l'exécution quotidienne
        schedule.every().day.at(f"{EXECUTION_HOUR:02d}:00").do(bot.run)

        while True:
            schedule.run_pending()
            time.sleep(60)  # Vérifier toutes les minutes

    except ImportError:
        logger.error("Module 'schedule' not installed. Run: pip install schedule")
        sys.exit(1)


def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(description="Bot de prédictions 1xBet")
    parser.add_argument("--run", action="store_true", help="Exécuter maintenant")
    parser.add_argument("--scheduler", action="store_true", help="Lancer le scheduler (21h)")
    parser.add_argument("--check-results", action="store_true", help="Vérifier les résultats du jour")
    parser.add_argument("--stats", action="store_true", help="Afficher les statistiques")
    parser.add_argument("--date", type=str, help="Date spécifique (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, default=7, help="Nombre de jours pour les stats")
    parser.add_argument("--test-telegram", action="store_true", help="Tester Telegram")
    parser.add_argument("--test-api", action="store_true", help="Tester l'API Football")
    parser.add_argument("--no-telegram", action="store_true", help="Désactiver Telegram")
    parser.add_argument("--no-save", action="store_true", help="Ne pas sauvegarder les fichiers")

    args = parser.parse_args()

    bot = BettingBot()

    if args.test_telegram:
        bot.test_telegram()
    elif args.test_api:
        bot.test_api()
    elif args.scheduler:
        run_scheduler()
    elif args.check_results:
        bot.check_results(
            date=args.date,
            send_telegram=not args.no_telegram
        )
    elif args.stats:
        bot.show_stats(
            days=args.days,
            send_telegram=not args.no_telegram
        )
    elif args.run:
        bot.run(
            send_telegram=not args.no_telegram,
            save_output=not args.no_save,
            target_date=args.date
        )
    else:
        # Par défaut, afficher l'aide
        parser.print_help()
        print("\nExemples:")
        print("  python main.py --run                    # Générer les prédictions")
        print("  python main.py --check-results          # Vérifier les résultats du jour")
        print("  python main.py --check-results --date 2026-01-07")
        print("  python main.py --stats                  # Stats des 7 derniers jours")
        print("  python main.py --stats --days 30        # Stats des 30 derniers jours")
        print("  python main.py --scheduler              # Lancer le scheduler (21h)")
        print("  python main.py --test-telegram          # Tester Telegram")
        print("  python main.py --test-api               # Tester l'API")


if __name__ == "__main__":
    main()
