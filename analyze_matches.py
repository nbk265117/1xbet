#!/usr/bin/env python3
"""
Analyseur de matchs Over 2.5 - Calcul des probabilités
"""

import re
from html import escape

# Équipes offensives connues (historiquement > 2.5 buts/match)
OFFENSIVE_TEAMS = {
    # Pays-Bas
    'psv', 'psv eindhoven', 'ajax', 'feyenoord', 'az alkmaar', 'twente', 'utrecht',
    'jong psv', 'jong ajax', 'jong az', 'jong utrecht', 'vitesse', 'go ahead eagles',
    # Allemagne
    'bayern', 'bayern munich', 'dortmund', 'borussia dortmund', 'bayer leverkusen',
    'rb leipzig', 'eintracht frankfurt', 'wolfsburg', 'stuttgart', 'gladbach',
    # Angleterre
    'manchester city', 'liverpool', 'arsenal', 'chelsea', 'tottenham', 'manchester united',
    'newcastle', 'brighton', 'aston villa', 'west ham', 'bournemouth',
    # Espagne
    'barcelona', 'real madrid', 'atletico madrid', 'real betis', 'villarreal',
    'athletic bilbao', 'real sociedad', 'sevilla', 'valencia',
    # Italie
    'inter', 'ac milan', 'juventus', 'napoli', 'atalanta', 'roma', 'lazio', 'fiorentina',
    # France
    'psg', 'paris saint germain', 'marseille', 'monaco', 'lyon', 'lille', 'lens', 'nice',
    # Suisse
    'young boys', 'basel', 'servette', 'zurich', 'st. gallen', 'lugano',
    # Belgique
    'club brugge', 'anderlecht', 'genk', 'gent', 'antwerp', 'union st.-gilloise',
    # Portugal
    'benfica', 'porto', 'sporting cp', 'braga', 'guimaraes',
    # Autriche
    'rb salzburg', 'rapid wien', 'sturm graz', 'austria vienna',
    # Hongrie
    'ferencvarosi', 'ferencvarosi tc',
    # Argentine
    'river plate', 'boca juniors', 'racing club', 'independiente',
}

# Ligues premium (généralement plus de buts)
PREMIUM_LEAGUES = {
    'eredivisie': 85,          # Très offensif
    'bundesliga': 82,          # Très offensif
    'eerste divisie': 80,      # Division 2 NL très prolifique
    'super league': 78,        # Suisse
    '2. bundesliga': 77,       # Div 2 Allemagne
    'championship': 76,        # Div 2 Angleterre
    'ligue 1': 75,
    'premier league': 74,
    'la liga': 73,
    'serie a': 72,
    'serie b': 71,
    'segunda división': 70,
    'jupiler pro league': 75,  # Belgique
    'liga profesional argentina': 72,
    'nb i': 73,                # Hongrie
    'primeira liga': 71,       # Portugal
    'austrian bundesliga': 74,
    'czech liga': 72,
    'allsvenskan': 73,         # Suède
    'eliteserien': 74,         # Norvège
    'greek super league': 70,
    'caf confederation cup': 68,
    'caf champions league': 68,
}

# Bonus pour les matchs avec équipes réserves (Jong)
RESERVE_TEAMS = ['jong', 'u21', 'ii', 'b team', 'reserve']

def calculate_probability(match_data, league):
    """Calcule la probabilité d'Over 2.5 pour un match"""

    base_prob = 65  # Tous ces matchs sont déjà présélectionnés

    # Bonus ligue
    league_lower = league.lower()
    for league_name, bonus in PREMIUM_LEAGUES.items():
        if league_name in league_lower:
            base_prob = max(base_prob, bonus)
            break

    match_lower = match_data.lower()

    # Bonus équipes offensives
    offensive_count = 0
    for team in OFFENSIVE_TEAMS:
        if team in match_lower:
            offensive_count += 1

    if offensive_count >= 2:
        base_prob += 12  # Deux équipes offensives
    elif offensive_count == 1:
        base_prob += 7   # Une équipe offensive

    # Bonus équipes réserves (souvent matchs ouverts)
    for reserve in RESERVE_TEAMS:
        if reserve in match_lower:
            base_prob += 5
            break

    # Détection des gros matchs/derbys
    big_match_pairs = [
        ('psv', 'ajax'), ('psv', 'feyenoord'), ('ajax', 'feyenoord'),
        ('bayern', 'dortmund'), ('barcelona', 'real madrid'),
        ('inter', 'ac milan'), ('inter', 'juventus'),
        ('manchester city', 'liverpool'), ('arsenal', 'chelsea'),
        ('psg', 'marseille'), ('lyon', 'marseille'),
    ]

    for team1, team2 in big_match_pairs:
        if team1 in match_lower and team2 in match_lower:
            base_prob += 8
            break

    # Limiter entre 58% et 92%
    return min(92, max(58, base_prob))


def get_color_class(prob):
    """Retourne la classe de couleur selon la probabilité"""
    if prob >= 85:
        return 'prob-excellent'
    elif prob >= 78:
        return 'prob-high'
    elif prob >= 70:
        return 'prob-medium'
    else:
        return 'prob-low'


def process_html():
    """Traite le fichier HTML et ajoute les probabilités"""

    with open('/Users/mac/1xbet/frontend/index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # Extraire toutes les sections par pays
    sections = re.findall(
        r'(<div class="country-section".*?</div>\s*</div>)',
        content,
        re.DOTALL
    )

    # Ajouter les styles CSS pour les barres de progression
    new_styles = '''
        .prob-col {
            width: 140px;
        }
        .progress-container {
            width: 100%;
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
            overflow: hidden;
            height: 24px;
            position: relative;
        }
        .progress-bar {
            height: 100%;
            border-radius: 10px;
            transition: width 0.5s ease;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .progress-text {
            position: absolute;
            width: 100%;
            text-align: center;
            font-weight: bold;
            font-size: 0.85em;
            color: #fff;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
            line-height: 24px;
        }
        .prob-excellent .progress-bar {
            background: linear-gradient(90deg, #00c853, #00e676);
        }
        .prob-high .progress-bar {
            background: linear-gradient(90deg, #00bcd4, #00e5ff);
        }
        .prob-medium .progress-bar {
            background: linear-gradient(90deg, #ff9800, #ffc107);
        }
        .prob-low .progress-bar {
            background: linear-gradient(90deg, #f44336, #ff5722);
        }
        .legend {
            display: flex;
            justify-content: center;
            gap: 20px;
            margin: 20px 0;
            flex-wrap: wrap;
        }
        .legend-item {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.9em;
        }
        .legend-color {
            width: 20px;
            height: 20px;
            border-radius: 5px;
        }
        .legend-excellent { background: linear-gradient(90deg, #00c853, #00e676); }
        .legend-high { background: linear-gradient(90deg, #00bcd4, #00e5ff); }
        .legend-medium { background: linear-gradient(90deg, #ff9800, #ffc107); }
        .legend-low { background: linear-gradient(90deg, #f44336, #ff5722); }
        .avg-prob {
            font-size: 1.8em;
            color: #00ff88;
        }
    '''

    # Insérer les nouveaux styles
    content = content.replace('</style>', new_styles + '\n    </style>')

    # Ajouter la légende après les stats
    legend_html = '''
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-color legend-excellent"></div>
                    <span>Excellent (85%+)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color legend-high"></div>
                    <span>Elevé (78-84%)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color legend-medium"></div>
                    <span>Moyen (70-77%)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color legend-low"></div>
                    <span>Standard (58-69%)</span>
                </div>
            </div>
    '''

    content = content.replace('</header>', legend_html + '\n        </header>')

    # Ajouter colonne Probabilité aux en-têtes
    content = re.sub(
        r'(<th>Ligue</th>\s*</tr>)',
        r'<th>Ligue</th>\n                        <th class="prob-col">Probabilité</th>\n                    </tr>',
        content
    )

    # Traiter chaque ligne de match
    all_probs = []

    def add_probability(match):
        data_search = match.group(1)
        num = match.group(2)
        date = match.group(3)
        match_name = match.group(4)
        league = match.group(5)

        prob = calculate_probability(data_search, league)
        all_probs.append(prob)
        color_class = get_color_class(prob)

        prob_cell = f'''<td class="prob-col {color_class}">
                            <div class="progress-container">
                                <div class="progress-bar" style="width: {prob}%"></div>
                                <span class="progress-text">{prob}%</span>
                            </div>
                        </td>'''

        return f'''<tr class="match-row" data-search="{data_search}">
                        <td>{num}</td>
                        <td class="date">{date}</td>
                        <td class="match-name">{match_name}</td>
                        <td class="league">{league}</td>
                        {prob_cell}
                    </tr>'''

    # Pattern pour trouver les lignes de match
    pattern = r'<tr class="match-row" data-search="([^"]+)">\s*<td>(\d+)</td>\s*<td class="date">([^<]+)</td>\s*<td class="match-name">([^<]+)</td>\s*<td class="league">([^<]+)</td>\s*</tr>'

    content = re.sub(pattern, add_probability, content)

    # Calculer la moyenne
    avg_prob = sum(all_probs) / len(all_probs) if all_probs else 0

    # Compter par catégorie
    excellent = sum(1 for p in all_probs if p >= 85)
    high = sum(1 for p in all_probs if 78 <= p < 85)
    medium = sum(1 for p in all_probs if 70 <= p < 78)
    low = sum(1 for p in all_probs if p < 70)

    # Ajouter stats supplémentaires
    extra_stats = f'''
                <div class="stat-box">
                    <div class="stat-number avg-prob">{avg_prob:.1f}%</div>
                    <div class="stat-label">Probabilité Moyenne</div>
                </div>
            </div>

            <div class="stats" style="margin-top: 15px;">
                <div class="stat-box" style="padding: 15px 25px;">
                    <div class="stat-number" style="font-size: 1.8em; color: #00e676;">{excellent}</div>
                    <div class="stat-label">Excellent (85%+)</div>
                </div>
                <div class="stat-box" style="padding: 15px 25px;">
                    <div class="stat-number" style="font-size: 1.8em; color: #00e5ff;">{high}</div>
                    <div class="stat-label">Elevé (78-84%)</div>
                </div>
                <div class="stat-box" style="padding: 15px 25px;">
                    <div class="stat-number" style="font-size: 1.8em; color: #ffc107;">{medium}</div>
                    <div class="stat-label">Moyen (70-77%)</div>
                </div>
                <div class="stat-box" style="padding: 15px 25px;">
                    <div class="stat-number" style="font-size: 1.8em; color: #ff5722;">{low}</div>
                    <div class="stat-label">Standard (<70%)</div>
                </div>'''

    # Remplacer la dernière stat-box pour ajouter les nouvelles
    content = re.sub(
        r'(<div class="stat-box">\s*<div class="stat-number">29</div>\s*<div class="stat-label">Pays</div>\s*</div>\s*</div>)',
        r'''<div class="stat-box">
                    <div class="stat-number">29</div>
                    <div class="stat-label">Pays</div>
                </div>''' + extra_stats,
        content
    )

    # Mettre à jour le titre
    content = content.replace(
        '<title>🏆 390 Matchs Over 2.5 - Jan/Fév/Mars 2026</title>',
        '<title>🏆 354 Matchs Over 2.5 avec Probabilités - 2026</title>'
    )

    content = content.replace(
        '<h1>🏆 MATCHS OVER 2.5 GOALS</h1>',
        '<h1>🏆 MATCHS OVER 2.5 GOALS + PROBABILITES</h1>'
    )

    # Écrire le fichier
    with open('/Users/mac/1xbet/frontend/index.html', 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ Fichier mis à jour avec {len(all_probs)} matchs analysés")
    print(f"📊 Probabilité moyenne: {avg_prob:.1f}%")
    print(f"🟢 Excellent (85%+): {excellent} matchs")
    print(f"🔵 Elevé (78-84%): {high} matchs")
    print(f"🟡 Moyen (70-77%): {medium} matchs")
    print(f"🔴 Standard (<70%): {low} matchs")


if __name__ == '__main__':
    process_html()
