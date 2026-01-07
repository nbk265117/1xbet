"""
Configuration des ligues et compétitions autorisées
IDs basés sur API-Football (api-sports.io)
"""

# Format: league_id: {"name": "Nom", "country": "Pays", "priority": 1-3}
# Priority 1 = Top européen, 2 = Grandes ligues, 3 = Autres

ALLOWED_LEAGUES = {
    # 🏴󠁧󠁢󠁥󠁮󠁧󠁿 Angleterre
    39: {"name": "Premier League", "country": "England", "priority": 1},
    40: {"name": "Championship", "country": "England", "priority": 2},
    45: {"name": "FA Cup", "country": "England", "priority": 2},
    48: {"name": "League Cup", "country": "England", "priority": 2},

    # 🇪🇸 Espagne
    140: {"name": "La Liga", "country": "Spain", "priority": 1},
    141: {"name": "Segunda División", "country": "Spain", "priority": 2},
    143: {"name": "Copa del Rey", "country": "Spain", "priority": 2},

    # 🇫🇷 France
    61: {"name": "Ligue 1", "country": "France", "priority": 1},
    62: {"name": "Ligue 2", "country": "France", "priority": 2},
    66: {"name": "Coupe de France", "country": "France", "priority": 2},

    # 🇮🇹 Italie
    135: {"name": "Serie A", "country": "Italy", "priority": 1},
    136: {"name": "Serie B", "country": "Italy", "priority": 2},
    137: {"name": "Coppa Italia", "country": "Italy", "priority": 2},

    # 🇩🇪 Allemagne
    78: {"name": "Bundesliga", "country": "Germany", "priority": 1},
    79: {"name": "Bundesliga 2", "country": "Germany", "priority": 2},
    81: {"name": "DFB Pokal", "country": "Germany", "priority": 2},

    # 🇳🇱 Pays-Bas
    88: {"name": "Eredivisie", "country": "Netherlands", "priority": 1},
    89: {"name": "Eerste Divisie", "country": "Netherlands", "priority": 2},

    # 🇵🇹 Portugal
    94: {"name": "Primeira Liga", "country": "Portugal", "priority": 1},

    # 🇹🇷 Turquie
    203: {"name": "Süper Lig", "country": "Turkey", "priority": 1},

    # 🇧🇪 Belgique
    144: {"name": "Pro League", "country": "Belgium", "priority": 2},

    # 🌍 Afrique
    200: {"name": "Botola Pro", "country": "Morocco", "priority": 2},
    186: {"name": "Ligue 1", "country": "Algeria", "priority": 2},
    202: {"name": "Ligue 1", "country": "Tunisia", "priority": 2},
    233: {"name": "Premier League", "country": "Egypt", "priority": 2},

    # 🇸🇦 Arabie Saoudite & Golfe
    307: {"name": "Saudi Pro League", "country": "Saudi-Arabia", "priority": 1},
    305: {"name": "UAE Pro League", "country": "UAE", "priority": 2},
    306: {"name": "Stars League", "country": "Qatar", "priority": 2},
    253: {"name": "Premier League", "country": "Kuwait", "priority": 3},
    388: {"name": "Professional League", "country": "Oman", "priority": 3},
    368: {"name": "Premier League", "country": "Iraq", "priority": 3},

    # 🇺🇸 Amériques
    253: {"name": "MLS", "country": "USA", "priority": 2},
    128: {"name": "Liga Profesional", "country": "Argentina", "priority": 1},
    130: {"name": "Copa Argentina", "country": "Argentina", "priority": 2},
    71: {"name": "Brasileirão Série A", "country": "Brazil", "priority": 1},
    72: {"name": "Brasileirão Série B", "country": "Brazil", "priority": 2},
    73: {"name": "Copa do Brasil", "country": "Brazil", "priority": 2},

    # 🌏 Asie
    98: {"name": "J1 League", "country": "Japan", "priority": 2},
    292: {"name": "K League 1", "country": "South-Korea", "priority": 2},
    169: {"name": "Super League", "country": "China", "priority": 2},

    # 🏆 Compétitions internationales
    2: {"name": "UEFA Champions League", "country": "World", "priority": 1},
    3: {"name": "UEFA Europa League", "country": "World", "priority": 1},
    848: {"name": "UEFA Conference League", "country": "World", "priority": 2},
    4: {"name": "UEFA Super Cup", "country": "World", "priority": 2},

    # 🌍 Compétitions nationales
    6: {"name": "CAN - Africa Cup of Nations", "country": "World", "priority": 1},
    4: {"name": "Euro Championship", "country": "World", "priority": 1},
    9: {"name": "Copa America", "country": "World", "priority": 1},
    1: {"name": "World Cup", "country": "World", "priority": 1},
    15: {"name": "FIFA Club World Cup", "country": "World", "priority": 1},

    # 🏆 Autres compétitions majeures
    13: {"name": "CONMEBOL Libertadores", "country": "World", "priority": 1},
    14: {"name": "CONMEBOL Sudamericana", "country": "World", "priority": 2},
    17: {"name": "AFC Champions League", "country": "World", "priority": 2},
    12: {"name": "CAF Champions League", "country": "World", "priority": 2},
}

# Liste des IDs pour filtrage rapide
ALLOWED_LEAGUE_IDS = set(ALLOWED_LEAGUES.keys())

def get_league_priority(league_id: int) -> int:
    """Retourne la priorité d'une ligue (1=top, 3=faible)"""
    if league_id in ALLOWED_LEAGUES:
        return ALLOWED_LEAGUES[league_id]["priority"]
    return 99

def is_league_allowed(league_id: int) -> bool:
    """Vérifie si une ligue est dans la liste autorisée"""
    return league_id in ALLOWED_LEAGUE_IDS

def get_league_name(league_id: int) -> str:
    """Retourne le nom d'une ligue"""
    if league_id in ALLOWED_LEAGUES:
        return f"{ALLOWED_LEAGUES[league_id]['name']} ({ALLOWED_LEAGUES[league_id]['country']})"
    return f"League {league_id}"
