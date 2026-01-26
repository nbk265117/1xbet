#!/usr/bin/env python3
"""
Ajoute des heures réalistes aux matchs basées sur la ligue et le pays
"""

import re
import hashlib

# Heures typiques par ligue/pays
LEAGUE_TIMES = {
    # Pays-Bas
    'eredivisie': ['14:30', '16:45', '18:45', '20:00', '21:00'],
    'eerste divisie': ['14:30', '16:30', '18:45', '20:00'],

    # Angleterre
    'premier league': ['13:30', '16:00', '18:30', '21:00'],
    'championship': ['13:30', '16:00', '19:45', '20:45'],

    # Allemagne
    'bundesliga': ['15:30', '18:30', '20:30'],
    '2. bundesliga': ['13:30', '18:30', '20:30'],

    # Espagne
    'la liga': ['14:00', '16:15', '18:30', '21:00'],
    'segunda división': ['14:00', '16:15', '19:00', '21:00'],

    # Italie
    'serie a': ['12:30', '15:00', '18:00', '20:45'],
    'serie b': ['14:00', '16:15', '18:30', '20:45'],

    # France
    'ligue 1': ['13:00', '15:00', '17:00', '20:45'],

    # Suisse
    'super league': ['14:15', '16:30', '18:00', '20:30'],

    # Belgique
    'jupiler pro league': ['14:30', '16:30', '18:30', '20:45'],

    # Autres
    'default': ['15:00', '17:00', '19:00', '20:00', '21:00']
}


def get_match_time(match_name, league, date):
    """Génère une heure réaliste pour un match"""
    league_lower = league.lower()

    # Trouver les heures pour cette ligue
    times = LEAGUE_TIMES.get('default')
    for lg, lg_times in LEAGUE_TIMES.items():
        if lg in league_lower:
            times = lg_times
            break

    # Utiliser un hash pour avoir une heure constante pour chaque match
    seed = hashlib.md5(f"{match_name}{league}{date}".encode()).hexdigest()
    time_index = int(seed[:2], 16) % len(times)

    return times[time_index]


def process_html():
    """Met à jour le fichier HTML avec les heures"""

    with open('/Users/mac/1xbet/frontend/index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern pour trouver les dates
    pattern = r'(<td class="date">)(\d{2}/\d{2})(</td>)'

    matches_updated = 0

    def add_time(match):
        nonlocal matches_updated
        prefix = match.group(1)
        date = match.group(2)
        suffix = match.group(3)

        # Trouver le contexte pour déterminer la ligue
        start = match.start()
        context_start = max(0, start - 500)
        context = content[context_start:start + 200]

        # Extraire le nom du match et la ligue
        match_name_match = re.search(r'class="match-name">([^<]+)<', context)
        league_match = re.search(r'class="league">([^<]+)<', context)

        match_name = match_name_match.group(1) if match_name_match else ""
        league = league_match.group(1) if league_match else ""

        # Générer l'heure
        time = get_match_time(match_name, league, date)

        matches_updated += 1
        return f'{prefix}{date} {time}{suffix}'

    content = re.sub(pattern, add_time, content)

    with open('/Users/mac/1xbet/frontend/index.html', 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ Heures ajoutées à {matches_updated} matchs")


if __name__ == '__main__':
    process_html()
