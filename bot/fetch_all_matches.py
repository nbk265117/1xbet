#!/usr/bin/env python3
"""
Script pour charger TOUS les matchs d'une date via API-Football
Sans aucun filtrage - affiche tout ce qui est disponible
"""
import requests
import json
from datetime import datetime, timedelta
import sys

API_KEY = "111a3d8d8abb91aacf250df4ea6f5116"
BASE_URL = "https://v3.football.api-sports.io"

def fetch_all_fixtures(date: str):
    """Récupère TOUS les matchs pour une date donnée"""
    url = f"{BASE_URL}/fixtures"
    headers = {"x-apisports-key": API_KEY}
    params = {"date": date}
    
    print(f"\n🔍 Fetching ALL matches for {date}...")
    response = requests.get(url, headers=headers, params=params, timeout=60)
    data = response.json()
    
    if data.get("errors"):
        print(f"❌ API Error: {data['errors']}")
        return None
    
    fixtures = data.get("response", [])
    print(f"✅ Total matches found: {len(fixtures)}")
    
    return fixtures

def analyze_fixtures(fixtures):
    """Analyse et affiche les matchs par ligue/pays"""
    if not fixtures:
        return
    
    # Grouper par pays puis par ligue
    by_country = {}
    for f in fixtures:
        country = f["league"]["country"]
        league = f["league"]["name"]
        league_id = f["league"]["id"]
        
        if country not in by_country:
            by_country[country] = {}
        if league not in by_country[country]:
            by_country[country][league] = {"id": league_id, "matches": []}
        
        by_country[country][league]["matches"].append({
            "fixture_id": f["fixture"]["id"],
            "home": f["teams"]["home"]["name"],
            "away": f["teams"]["away"]["name"],
            "date": f["fixture"]["date"],
            "status": f["fixture"]["status"]["short"]
        })
    
    # Afficher le résumé
    print("\n" + "="*80)
    print(f"📊 RÉSUMÉ PAR PAYS/LIGUE ({len(fixtures)} matchs au total)")
    print("="*80)
    
    # Trier par nombre de matchs
    sorted_countries = sorted(by_country.items(), 
                            key=lambda x: sum(len(l["matches"]) for l in x[1].values()), 
                            reverse=True)
    
    for country, leagues in sorted_countries:
        total_matches = sum(len(l["matches"]) for l in leagues.values())
        print(f"\n🏳️ {country} ({total_matches} matchs)")
        print("-"*40)
        
        for league_name, league_data in sorted(leagues.items(), 
                                               key=lambda x: len(x[1]["matches"]), 
                                               reverse=True):
            matches = league_data["matches"]
            league_id = league_data["id"]
            print(f"  📍 {league_name} (ID: {league_id}) - {len(matches)} matchs")
            
            for m in matches[:5]:  # Afficher max 5 matchs par ligue
                time = m["date"][11:16] if m["date"] else "TBD"
                status = m["status"]
                print(f"      [{time}] {m['home']} vs {m['away']} ({status})")
            
            if len(matches) > 5:
                print(f"      ... et {len(matches)-5} autres matchs")

def save_to_json(fixtures, date):
    """Sauvegarde les matchs en JSON"""
    output = {
        "date": date,
        "generated_at": datetime.now().isoformat(),
        "total_matches": len(fixtures),
        "fixtures": fixtures
    }
    
    filename = f"all_fixtures_{date}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Saved to {filename}")

if __name__ == "__main__":
    # Date par défaut = demain
    if len(sys.argv) > 1:
        date = sys.argv[1]
    else:
        date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    fixtures = fetch_all_fixtures(date)
    
    if fixtures:
        analyze_fixtures(fixtures)
        save_to_json(fixtures, date)
        
        # Stats API
        print("\n" + "="*80)
        print("📈 API QUOTA STATUS")
        url = f"{BASE_URL}/status"
        headers = {"x-apisports-key": API_KEY}
        resp = requests.get(url, headers=headers)
        status = resp.json().get("response", {})
        if status:
            sub = status.get("subscription", {})
            req = status.get("requests", {})
            print(f"  Plan: {sub.get('plan', 'N/A')}")
            print(f"  Requests today: {req.get('current', 0)}/{req.get('limit_day', 0)}")
