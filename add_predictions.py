#!/usr/bin/env python3
"""
Algorithme de prédiction avancé - Meilleur pari + Score exact
Version 2.0 - Cohérence garantie entre score et pari
"""

import re

# Équipes très offensives (moyenne > 2 buts/match)
SUPER_OFFENSIVE = {
    'bayern', 'bayern munich', 'manchester city', 'psg', 'paris saint germain',
    'barcelona', 'real madrid', 'inter', 'atalanta', 'dortmund', 'borussia dortmund',
    'rb leipzig', 'bayer leverkusen', 'liverpool', 'arsenal', 'psv', 'psv eindhoven',
    'ajax', 'feyenoord', 'sporting cp', 'benfica', 'napoli', 'rb salzburg'
}

# Équipes offensives (moyenne > 1.5 buts/match)
OFFENSIVE = {
    'chelsea', 'manchester united', 'tottenham', 'newcastle', 'brighton', 'aston villa',
    'west ham', 'ac milan', 'juventus', 'roma', 'lazio', 'fiorentina',
    'atletico madrid', 'real betis', 'villarreal', 'sevilla', 'real sociedad',
    'marseille', 'monaco', 'lyon', 'lille', 'lens', 'nice', 'toulouse',
    'twente', 'utrecht', 'az alkmaar', 'club brugge', 'anderlecht', 'genk',
    'young boys', 'basel', 'porto', 'braga', 'wolfsburg', 'stuttgart', 'gladbach',
    'eintracht frankfurt', 'ferencvarosi', 'racing club', 'river plate', 'boca juniors',
    'go ahead eagles', 'heerenveen', 'groningen', 'vitesse', 'excelsior', 'volendam'
}

# Équipes réserves/jeunes (matchs ouverts)
RESERVE_KEYWORDS = ['jong', 'u21', 'u23', 'ii', 'b team', 'reserve', 'u19']

# Ligues à beaucoup de buts
HIGH_SCORING_LEAGUES = {
    'eredivisie': 3.3,
    'eerste divisie': 3.5,
    'bundesliga': 3.2,
    '2. bundesliga': 3.1,
    'super league': 3.0,
    'jupiler pro league': 2.9,
    'austrian bundesliga': 3.0,
    'championship': 2.8,
    'premier league': 2.8,
    'ligue 1': 2.7,
    'serie a': 2.6,
    'la liga': 2.5,
}


def get_team_strength(team_name):
    """Retourne la force offensive d'une équipe (1-10)"""
    team_lower = team_name.lower()

    for team in SUPER_OFFENSIVE:
        if team in team_lower:
            return 9

    for team in OFFENSIVE:
        if team in team_lower:
            return 7

    for keyword in RESERVE_KEYWORDS:
        if keyword in team_lower:
            return 6

    return 5


def predict_match(home_team, away_team, league, probability):
    """
    Prédit le meilleur pari et le score exact pour un match
    RÈGLE: Le score doit TOUJOURS être cohérent avec le pari
    """
    home_lower = home_team.lower()
    away_lower = away_team.lower()
    league_lower = league.lower()

    home_strength = get_team_strength(home_team)
    away_strength = get_team_strength(away_team)

    # Détection équipe réserve
    home_reserve = any(k in home_lower for k in RESERVE_KEYWORDS)
    away_reserve = any(k in away_lower for k in RESERVE_KEYWORDS)

    # Bonus ligue
    league_multiplier = 1.0
    for lg, avg in HIGH_SCORING_LEAGUES.items():
        if lg in league_lower:
            league_multiplier = avg / 2.7
            break

    # Calcul des buts attendus avec avantage domicile
    home_base = (home_strength / 10) * 2.2 * league_multiplier
    away_base = (away_strength / 10) * 1.7 * league_multiplier

    # Ajustement si équipe réserve adverse
    if away_reserve:
        home_base *= 1.3
    if home_reserve:
        away_base *= 1.25

    # Différence de force
    strength_diff = home_strength - away_strength

    # ============================================
    # DÉTERMINER D'ABORD LE SCORE EXACT
    # ============================================

    if probability >= 85:
        # Haute probabilité Over 2.5 -> scores élevés
        if strength_diff >= 3:  # Gros favori domicile
            scores = ['3-1', '3-0', '4-1', '2-1']
        elif strength_diff <= -3:  # Gros favori extérieur
            scores = ['1-3', '0-3', '1-2', '2-3']
        elif home_strength >= 8 and away_strength >= 8:  # Deux grandes équipes
            scores = ['2-2', '3-2', '2-3', '3-1']
        else:
            scores = ['2-1', '1-2', '2-2', '3-1']

    elif probability >= 78:
        # Bonne probabilité
        if strength_diff >= 2:
            scores = ['2-1', '3-1', '2-0', '3-0']
        elif strength_diff <= -2:
            scores = ['1-2', '1-3', '0-2', '0-3']
        else:
            scores = ['2-1', '1-2', '2-2', '1-1']

    elif probability >= 70:
        # Probabilité moyenne
        if strength_diff >= 2:
            scores = ['2-1', '2-0', '3-1']
        elif strength_diff <= -2:
            scores = ['1-2', '0-2', '1-3']
        else:
            scores = ['2-1', '1-1', '2-2', '1-2']

    else:
        # Probabilité standard
        scores = ['2-1', '1-1', '2-0', '1-2']

    # Choisir le score basé sur la force relative
    import hashlib
    seed = hashlib.md5(f"{home_team}{away_team}{league}".encode()).hexdigest()
    score_index = int(seed[:2], 16) % len(scores)
    score = scores[score_index]

    home_goals, away_goals = map(int, score.split('-'))
    total_goals = home_goals + away_goals

    # ============================================
    # DÉTERMINER LE MEILLEUR PARI BASÉ SUR LE SCORE
    # ============================================

    # Les deux équipes marquent ?
    btts = home_goals > 0 and away_goals > 0

    # Over 2.5 ?
    over25 = total_goals >= 3

    # Une équipe marque 2+ ?
    home_over15 = home_goals >= 2
    away_over15 = away_goals >= 2

    # Logique de décision
    if over25 and btts:
        best_bet = "⚽ BTTS + Over 2.5"
    elif over25 and home_over15 and strength_diff >= 2:
        best_bet = f"🏠 {home_team.split()[0][:10]} +1.5"
    elif over25 and away_over15 and strength_diff <= -2:
        best_bet = f"✈️ {away_team.split()[0][:10]} +1.5"
    elif over25:
        best_bet = "📊 Over 2.5"
    elif btts:
        best_bet = "🎯 BTTS"
    elif home_over15:
        best_bet = f"🏠 {home_team.split()[0][:10]} +1.5"
    elif away_over15:
        best_bet = f"✈️ {away_team.split()[0][:10]} +1.5"
    else:
        # Forcer un score compatible Over 2.5 car ce sont des matchs présélectionnés
        if strength_diff >= 1:
            score = "2-1"
            best_bet = "📊 Over 2.5"
        else:
            score = "1-2"
            best_bet = "📊 Over 2.5"

    return best_bet, score


def process_html():
    """Met à jour le fichier HTML avec les prédictions"""

    with open('/Users/mac/1xbet/frontend/index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # Vérifier si les styles existent déjà
    if '.best-bet {' not in content:
        new_styles = '''
        .best-bet {
            font-size: 0.8em;
            padding: 4px 8px;
            border-radius: 8px;
            white-space: nowrap;
            font-weight: 500;
        }
        .bet-over { background: rgba(0, 200, 83, 0.2); color: #00e676; }
        .bet-btts { background: rgba(0, 188, 212, 0.2); color: #00e5ff; }
        .bet-team { background: rgba(255, 152, 0, 0.2); color: #ffc107; }
        .score-prediction {
            font-weight: bold;
            font-size: 1.1em;
            color: #ff6b6b;
            background: rgba(255, 107, 107, 0.15);
            padding: 4px 10px;
            border-radius: 8px;
        }
        .prediction-col {
            min-width: 120px;
        }
        .score-col {
            min-width: 55px;
            text-align: center;
        }
        @media (max-width: 768px) {
            .prediction-col { min-width: 90px; }
            .best-bet { font-size: 0.7em; padding: 3px 5px; }
            .score-prediction { font-size: 0.9em; padding: 3px 6px; }
        }
        @media (max-width: 480px) {
            .prediction-col { display: none; }
            .score-col .score-prediction { font-size: 0.8em; }
        }
    '''
        content = content.replace('    </style>', new_styles + '\n    </style>')

    # Vérifier si les colonnes header existent déjà
    if 'Meilleur Pari</th>' not in content:
        content = re.sub(
            r'(<th class="prob-col">Probabilité</th>\s*</tr>)',
            r'<th class="prob-col">Probabilité</th>\n                        <th class="prediction-col">Meilleur Pari</th>\n                        <th class="score-col">Score</th>\n                    </tr>',
            content
        )

    # Supprimer les anciennes prédictions si elles existent
    content = re.sub(
        r'<td class="prediction-col">.*?</td>\s*<td class="score-col">.*?</td>\s*</tr>',
        '</tr>',
        content,
        flags=re.DOTALL
    )

    # Pattern pour matcher les lignes de match
    pattern = r'(<tr class="match-row" data-search="([^"]+)">\s*<td>(\d+)</td>\s*<td class="date">([^<]+)</td>\s*<td class="match-name">([^<]+)</td>\s*<td class="league">([^<]+)</td>\s*<td class="prob-col[^"]*">\s*<div class="progress-container">\s*<div class="progress-bar" style="width: (\d+)%"></div>\s*<span class="progress-text">\d+%</span>\s*</div>\s*</td>\s*)</tr>'

    def add_predictions(match):
        row_content = match.group(1)
        match_name = match.group(5)
        league = match.group(6)
        prob = int(match.group(7))

        # Extraire les équipes
        teams = match_name.split(' vs ')
        if len(teams) == 2:
            home_team = teams[0].strip()
            away_team = teams[1].strip()
        else:
            home_team = match_name
            away_team = "Unknown"

        # Obtenir les prédictions
        best_bet, score = predict_match(home_team, away_team, league, prob)

        # Déterminer la classe CSS du pari
        if 'Over' in best_bet:
            bet_class = 'bet-over'
        elif 'BTTS' in best_bet:
            bet_class = 'bet-btts'
        else:
            bet_class = 'bet-team'

        return f'''{row_content}<td class="prediction-col"><span class="best-bet {bet_class}">{best_bet}</span></td>
                        <td class="score-col"><span class="score-prediction">{score}</span></td>
                    </tr>'''

    content = re.sub(pattern, add_predictions, content)

    with open('/Users/mac/1xbet/frontend/index.html', 'w', encoding='utf-8') as f:
        f.write(content)

    # Statistiques
    over_count = content.count('bet-over')
    btts_count = content.count('bet-btts')
    team_count = content.count('bet-team')

    print("✅ Prédictions ajoutées avec succès!")
    print(f"📊 Over 2.5: {over_count} matchs")
    print(f"🎯 BTTS: {btts_count} matchs")
    print(f"🏠 Team +1.5: {team_count} matchs")


if __name__ == '__main__':
    process_html()
