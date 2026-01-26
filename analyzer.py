#!/usr/bin/env python3
"""
🎯 ANALYSEUR DE MATCHS OVER 2.5 - v2.0
=====================================

Basé sur l'analyse des résultats du 25/01/2026:
- Over 2.5 avec Expected >= 3.5 = 87% de réussite
- Over 2.5 avec Expected 3.0-3.5 = 50% seulement
- Over 1.5 = 77% de réussite (alternative plus sûre)

Usage:
    python analyzer.py --date 2026-01-26
    python analyzer.py --fixture 1234567
"""

import os
import sys
import json
import argparse
import requests
from typing import Dict, List, Optional
from datetime import datetime

# Configuration
API_KEY = os.getenv("API_KEY", "111a3d8d8abb91aacf250df4ea6f5116")
API_BASE = "https://v3.football.api-sports.io"

# =============================================================================
# CONFIGURATION ALGORITHME v2.0
# =============================================================================

THRESHOLDS = {
    "over_25_safe": 3.5,      # Expected >= 3.5 = 87% de réussite
    "over_25_moderate": 3.0,  # Expected 3.0-3.5 = 50% (risqué)
    "over_15_safe": 2.5,      # Expected >= 2.5 = 77% de réussite
    "failed_to_score_max": 0.35,
    "h2h_min_goals": 2.5,
}

DEFENSIVE_LEAGUES = [
    "jordan", "thailand", "greece", "morocco", "iran", "turkey"
]

OFFENSIVE_LEAGUES = [
    "switzerland", "netherlands", "hong kong", "mexico",
    "laos", "singapore", "gibraltar"
]


# =============================================================================
# API FUNCTIONS
# =============================================================================

def fetch_fixtures(date: str) -> List[Dict]:
    """Récupère les matchs pour une date donnée."""
    url = f"{API_BASE}/fixtures?date={date}"
    headers = {"x-apisports-key": API_KEY}

    response = requests.get(url, headers=headers)
    data = response.json()

    return data.get("response", [])


def fetch_prediction(fixture_id: int) -> Dict:
    """Récupère la prédiction pour un match."""
    url = f"{API_BASE}/predictions?fixture={fixture_id}"
    headers = {"x-apisports-key": API_KEY}

    response = requests.get(url, headers=headers)
    return response.json()


# =============================================================================
# ANALYSIS FUNCTIONS
# =============================================================================

def calculate_expected_goals(
    home_for: float, home_against: float,
    away_for: float, away_against: float
) -> float:
    """Calcule les Expected Goals."""
    if home_for + away_for == 0:
        return 0.0
    return round((home_for + away_against) / 2 + (away_for + home_against) / 2, 2)


def check_risks(
    home_fts_rate: float,
    away_fts_rate: float,
    league: str,
    country: str,
    away_strength: float,
    home_strength: float
) -> List[str]:
    """Vérifie tous les risques pour un match."""
    alerts = []

    # Failed to score risk
    if home_fts_rate > THRESHOLDS["failed_to_score_max"]:
        alerts.append(f"⚠️ Home fails to score {home_fts_rate*100:.0f}% of matches")
    if away_fts_rate > THRESHOLDS["failed_to_score_max"]:
        alerts.append(f"⚠️ Away fails to score {away_fts_rate*100:.0f}% of matches")

    # Defensive league
    for defensive in DEFENSIVE_LEAGUES:
        if defensive in league.lower() or defensive in country.lower():
            alerts.append(f"⚠️ {country} - Ligue défensive")
            break

    # Big team away
    if away_strength - home_strength > 0.3:
        alerts.append("⚠️ Grande équipe en déplacement - risque défensif")

    return alerts


def analyze_match(pred_data: Dict) -> Optional[Dict]:
    """Analyse complète d'un match."""
    try:
        pred = pred_data.get("response", [{}])[0]
        if not pred:
            return None

        home = pred.get("teams", {}).get("home", {})
        away = pred.get("teams", {}).get("away", {})
        league = pred.get("league", {})

        home_league = home.get("league", {})
        away_league = away.get("league", {})

        # Extract goals stats
        home_for = float(home_league.get("goals", {}).get("for", {}).get("average", {}).get("total", 0) or 0)
        home_against = float(home_league.get("goals", {}).get("against", {}).get("average", {}).get("total", 0) or 0)
        away_for = float(away_league.get("goals", {}).get("for", {}).get("average", {}).get("total", 0) or 0)
        away_against = float(away_league.get("goals", {}).get("against", {}).get("average", {}).get("total", 0) or 0)

        # Calculate expected goals
        expected = calculate_expected_goals(home_for, home_against, away_for, away_against)

        # Failed to score rates
        home_fts = home_league.get("failed_to_score", {}).get("total", 0)
        home_matches = home_league.get("fixtures", {}).get("played", {}).get("total", 1)
        away_fts = away_league.get("failed_to_score", {}).get("total", 0)
        away_matches = away_league.get("fixtures", {}).get("played", {}).get("total", 1)

        home_fts_rate = home_fts / home_matches if home_matches > 0 else 0
        away_fts_rate = away_fts / away_matches if away_matches > 0 else 0

        # Form scores (for big team detection)
        home_form = home_league.get("form", "") or ""
        away_form = away_league.get("form", "") or ""
        home_strength = sum(3 if r == 'W' else 1 if r == 'D' else 0 for r in home_form[-5:]) / 15 if home_form else 0.5
        away_strength = sum(3 if r == 'W' else 1 if r == 'D' else 0 for r in away_form[-5:]) / 15 if away_form else 0.5

        # H2H average
        h2h = pred.get("h2h", [])
        h2h_avg = 0
        if h2h:
            total = sum((m.get("goals", {}).get("home", 0) or 0) + (m.get("goals", {}).get("away", 0) or 0) for m in h2h[:5])
            h2h_avg = total / min(5, len(h2h))

        # Check risks
        league_name = league.get("name", "")
        country = league.get("country", "")
        alerts = check_risks(home_fts_rate, away_fts_rate, league_name, country, away_strength, home_strength)

        # Determine recommendation
        over_25_rec = False
        over_25_conf = "low"
        over_25_prob = 30

        # Check if league is defensive
        is_defensive = any(d in league_name.lower() or d in country.lower() for d in DEFENSIVE_LEAGUES)
        min_expected = 4.0 if is_defensive else THRESHOLDS["over_25_safe"]

        if expected >= min_expected:
            over_25_rec = True
            over_25_conf = "very_high"
            over_25_prob = 87
            verdict = "🔥 TRÈS SÛR"
        elif expected >= THRESHOLDS["over_25_moderate"]:
            if len(alerts) == 0 and h2h_avg >= THRESHOLDS["h2h_min_goals"]:
                over_25_rec = True
                over_25_conf = "medium"
                over_25_prob = 55
                verdict = "⚠️ MOYEN"
            else:
                verdict = "❌ RISQUÉ"
        else:
            verdict = "❌ ÉVITER"

        # Over 1.5 (more reliable alternative)
        over_15_rec = expected >= 2.0
        over_15_prob = 77 if expected >= THRESHOLDS["over_15_safe"] else 65 if expected >= 2.0 else 50

        return {
            "match": f"{home.get('name', 'Home')} vs {away.get('name', 'Away')}",
            "league": f"{league_name}",
            "country": country,
            "expected_goals": expected,
            "h2h_avg": round(h2h_avg, 2),
            "home_fts_rate": round(home_fts_rate * 100, 1),
            "away_fts_rate": round(away_fts_rate * 100, 1),
            "alerts": alerts,
            "over_25": {
                "recommended": over_25_rec,
                "confidence": over_25_conf,
                "probability": over_25_prob,
                "verdict": verdict
            },
            "over_15": {
                "recommended": over_15_rec,
                "probability": over_15_prob
            }
        }

    except Exception as e:
        return {"error": str(e)}


def print_analysis(analysis: Dict) -> None:
    """Affiche l'analyse d'un match."""
    if analysis.get("error"):
        print(f"❌ Erreur: {analysis['error']}")
        return

    print(f"\n{'='*70}")
    print(f"🎯 {analysis['match']}")
    print(f"   {analysis['league']} ({analysis['country']})")
    print(f"{'='*70}")
    print(f"\n📊 STATISTIQUES:")
    print(f"   Expected Goals: {analysis['expected_goals']}")
    print(f"   H2H Average: {analysis['h2h_avg']} buts/match")
    print(f"   Home Failed to Score: {analysis['home_fts_rate']}%")
    print(f"   Away Failed to Score: {analysis['away_fts_rate']}%")

    if analysis['alerts']:
        print(f"\n🚨 ALERTES:")
        for alert in analysis['alerts']:
            print(f"   {alert}")

    over_25 = analysis['over_25']
    over_15 = analysis['over_15']

    print(f"\n🎯 RECOMMANDATIONS:")
    print(f"   Over 2.5: {over_25['verdict']} ({over_25['probability']}%)")
    print(f"   Over 1.5: {'✅ OUI' if over_15['recommended'] else '❌ NON'} ({over_15['probability']}%)")

    if over_25['recommended']:
        print(f"\n   ✅ PRENDRE Over 2.5 - Confiance: {over_25['confidence'].upper()}")
    else:
        print(f"\n   ❌ NE PAS prendre Over 2.5")
        if over_15['recommended']:
            print(f"   💡 Alternative: Over 1.5 ({over_15['probability']}%)")


def analyze_date(date: str, min_expected: float = 3.5) -> List[Dict]:
    """Analyse tous les matchs d'une date et retourne les meilleurs."""
    print(f"\n🔍 Récupération des matchs du {date}...")
    fixtures = fetch_fixtures(date)
    print(f"   {len(fixtures)} matchs trouvés")

    results = []
    analyzed = 0

    # Filter for non-started matches only
    pending = [f for f in fixtures if f.get("fixture", {}).get("status", {}).get("short") == "NS"]
    print(f"   {len(pending)} matchs pas encore commencés")

    for fixture in pending[:50]:  # Limit API calls
        fixture_id = fixture.get("fixture", {}).get("id")
        home = fixture.get("teams", {}).get("home", {}).get("name", "")
        away = fixture.get("teams", {}).get("away", {}).get("name", "")

        print(f"   Analyse {home} vs {away}...", end="\r")

        pred_data = fetch_prediction(fixture_id)
        analysis = analyze_match(pred_data)

        if analysis and not analysis.get("error"):
            analysis["fixture_id"] = fixture_id
            if analysis["expected_goals"] >= 2.5:  # Pre-filter
                results.append(analysis)
                analyzed += 1

    print(f"\n   ✅ {analyzed} matchs analysés avec Expected >= 2.5")

    # Sort by expected goals
    results.sort(key=lambda x: x["expected_goals"], reverse=True)

    return results


def print_top_matches(matches: List[Dict], category: str, min_expected: float = 3.5) -> None:
    """Affiche les meilleurs matchs filtrés."""
    filtered = [m for m in matches if m["expected_goals"] >= min_expected]

    print(f"\n{'='*70}")
    print(f"🏆 {category} (Expected >= {min_expected})")
    print(f"{'='*70}")
    print(f"{'#':<3} {'Match':<40} {'Expected':<10} {'Verdict':<15}")
    print("-" * 70)

    for i, m in enumerate(filtered[:15], 1):
        verdict = m["over_25"]["verdict"]
        alerts = "⚠️" if m["alerts"] else ""
        print(f"{i:<3} {m['match'][:38]:<40} {m['expected_goals']:<10} {verdict:<15} {alerts}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Analyseur de matchs Over 2.5 v2.0")
    parser.add_argument("--date", help="Date à analyser (YYYY-MM-DD)")
    parser.add_argument("--fixture", type=int, help="ID du fixture à analyser")
    parser.add_argument("--min-expected", type=float, default=3.5, help="Expected minimum (défaut: 3.5)")

    args = parser.parse_args()

    if args.fixture:
        # Analyse d'un match spécifique
        print(f"🔍 Analyse du match {args.fixture}...")
        pred_data = fetch_prediction(args.fixture)
        analysis = analyze_match(pred_data)
        print_analysis(analysis)

    elif args.date:
        # Analyse d'une date
        matches = analyze_date(args.date, args.min_expected)

        # Afficher les catégories
        print_top_matches(matches, "TOP MATCHS OVER 2.5 - TRÈS SÛR", 3.5)
        print_top_matches(matches, "MATCHS OVER 2.5 - SÛR", 3.0)

        # Générer ticket recommandé
        safe_matches = [m for m in matches if m["over_25"]["recommended"] and m["over_25"]["confidence"] == "very_high"]

        if safe_matches:
            print(f"\n{'='*70}")
            print(f"🎫 TICKET RECOMMANDÉ - {len(safe_matches[:8])} MATCHS")
            print(f"{'='*70}")
            combined_prob = 1.0
            for i, m in enumerate(safe_matches[:8], 1):
                prob = m["over_25"]["probability"] / 100
                combined_prob *= prob
                print(f"{i}. {m['match']} - Expected: {m['expected_goals']} - {m['over_25']['verdict']}")

            print(f"\n   📊 Probabilité combinée: {combined_prob*100:.1f}%")
            print(f"   💰 Cote estimée: ~{1/combined_prob:.2f}")

    else:
        # Par défaut, analyser demain
        from datetime import date, timedelta
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        print(f"Utilisation de la date par défaut: {tomorrow}")
        matches = analyze_date(tomorrow, args.min_expected)
        print_top_matches(matches, "TOP MATCHS OVER 2.5", args.min_expected)


if __name__ == "__main__":
    main()
