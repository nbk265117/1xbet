"""
Configuration des ligues et compétitions autorisées
IDs basés sur API-Football (api-sports.io)

MISE À JOUR: Configuration complète avec 100+ ligues
Priority: 1 = Compétitions majeures, 2 = Ligues importantes, 3 = Autres ligues
"""

# Format: league_id: {"name": "Nom", "country": "Pays", "priority": 1-3}
ALLOWED_LEAGUES = {
    # ========================================
    # 🌍 COMPÉTITIONS INTERNATIONALES
    # ========================================

    # Équipes nationales
    1: {"name": "World Cup", "country": "World", "priority": 1},
    4: {"name": "Euro Championship", "country": "Europe", "priority": 1},
    9: {"name": "Copa America", "country": "South America", "priority": 1},
    6: {"name": "Africa Cup of Nations", "country": "Africa", "priority": 1},
    29: {"name": "World Cup Qualifiers - Africa", "country": "World", "priority": 2},
    30: {"name": "World Cup Qualifiers - South America", "country": "World", "priority": 2},
    31: {"name": "World Cup Qualifiers - Europe", "country": "World", "priority": 2},
    32: {"name": "World Cup Qualifiers - North America", "country": "World", "priority": 2},
    33: {"name": "World Cup Qualifiers - Asia", "country": "World", "priority": 2},
    34: {"name": "World Cup Qualifiers - Oceania", "country": "World", "priority": 2},

    # Clubs - Europe
    2: {"name": "UEFA Champions League", "country": "Europe", "priority": 1},
    3: {"name": "UEFA Europa League", "country": "Europe", "priority": 1},
    848: {"name": "UEFA Conference League", "country": "Europe", "priority": 2},
    531: {"name": "UEFA Super Cup", "country": "Europe", "priority": 2},

    # Clubs - Autres continents
    13: {"name": "CONMEBOL Libertadores", "country": "South America", "priority": 1},
    14: {"name": "CONMEBOL Sudamericana", "country": "South America", "priority": 2},
    11: {"name": "Recopa Sudamericana", "country": "South America", "priority": 2},
    12: {"name": "CAF Champions League", "country": "Africa", "priority": 1},
    20: {"name": "CAF Confederation Cup", "country": "Africa", "priority": 2},
    17: {"name": "AFC Champions League", "country": "Asia", "priority": 2},
    18: {"name": "AFC Cup", "country": "Asia", "priority": 3},
    15: {"name": "FIFA Club World Cup", "country": "World", "priority": 1},

    # ========================================
    # 🏴󠁧󠁢󠁥󠁮󠁧󠁿 ANGLETERRE
    # ========================================
    39: {"name": "Premier League", "country": "England", "priority": 1},
    40: {"name": "Championship", "country": "England", "priority": 2},
    41: {"name": "League One", "country": "England", "priority": 3},
    42: {"name": "League Two", "country": "England", "priority": 3},
    43: {"name": "National League", "country": "England", "priority": 3},
    45: {"name": "FA Cup", "country": "England", "priority": 1},
    48: {"name": "League Cup (EFL Cup)", "country": "England", "priority": 1},
    46: {"name": "EFL Trophy", "country": "England", "priority": 3},
    528: {"name": "Community Shield", "country": "England", "priority": 2},

    # ========================================
    # 🇪🇸 ESPAGNE
    # ========================================
    140: {"name": "La Liga", "country": "Spain", "priority": 1},
    141: {"name": "Segunda División", "country": "Spain", "priority": 2},
    435: {"name": "Primera RFEF", "country": "Spain", "priority": 3},
    143: {"name": "Copa del Rey", "country": "Spain", "priority": 1},
    556: {"name": "Super Cup", "country": "Spain", "priority": 1},

    # ========================================
    # 🇩🇪 ALLEMAGNE
    # ========================================
    78: {"name": "Bundesliga", "country": "Germany", "priority": 1},
    79: {"name": "Bundesliga 2", "country": "Germany", "priority": 2},
    80: {"name": "3. Liga", "country": "Germany", "priority": 3},
    81: {"name": "DFB Pokal", "country": "Germany", "priority": 1},
    529: {"name": "DFL Super Cup", "country": "Germany", "priority": 2},

    # ========================================
    # 🇮🇹 ITALIE
    # ========================================
    135: {"name": "Serie A", "country": "Italy", "priority": 1},
    136: {"name": "Serie B", "country": "Italy", "priority": 2},
    137: {"name": "Coppa Italia", "country": "Italy", "priority": 1},
    547: {"name": "Serie C", "country": "Italy", "priority": 3},
    530: {"name": "Super Cup", "country": "Italy", "priority": 2},

    # ========================================
    # 🇫🇷 FRANCE
    # ========================================
    61: {"name": "Ligue 1", "country": "France", "priority": 1},
    62: {"name": "Ligue 2", "country": "France", "priority": 2},
    63: {"name": "National 1", "country": "France", "priority": 3},
    66: {"name": "Coupe de France", "country": "France", "priority": 1},
    65: {"name": "Coupe de la Ligue", "country": "France", "priority": 2},
    526: {"name": "Trophée des Champions", "country": "France", "priority": 2},

    # ========================================
    # 🇵🇹 PORTUGAL
    # ========================================
    94: {"name": "Primeira Liga", "country": "Portugal", "priority": 1},
    95: {"name": "Segunda Liga", "country": "Portugal", "priority": 2},
    96: {"name": "Taça de Portugal", "country": "Portugal", "priority": 2},
    97: {"name": "Taça da Liga", "country": "Portugal", "priority": 2},
    550: {"name": "Supertaça", "country": "Portugal", "priority": 2},

    # ========================================
    # 🇳🇱 PAYS-BAS
    # ========================================
    88: {"name": "Eredivisie", "country": "Netherlands", "priority": 1},
    89: {"name": "Eerste Divisie", "country": "Netherlands", "priority": 2},
    90: {"name": "KNVB Beker", "country": "Netherlands", "priority": 2},
    543: {"name": "Johan Cruijff Schaal", "country": "Netherlands", "priority": 2},

    # ========================================
    # 🇧🇪 BELGIQUE
    # ========================================
    144: {"name": "Pro League", "country": "Belgium", "priority": 1},
    145: {"name": "Challenger Pro League", "country": "Belgium", "priority": 2},
    147: {"name": "Cup", "country": "Belgium", "priority": 2},

    # ========================================
    # 🇹🇷 TURQUIE
    # ========================================
    203: {"name": "Süper Lig", "country": "Turkey", "priority": 1},
    204: {"name": "1. Lig", "country": "Turkey", "priority": 2},
    206: {"name": "Türkiye Kupası", "country": "Turkey", "priority": 2},
    551: {"name": "Super Cup", "country": "Turkey", "priority": 2},

    # ========================================
    # 🏴󠁧󠁢󠁳󠁣󠁴󠁿 ÉCOSSE
    # ========================================
    179: {"name": "Premiership", "country": "Scotland", "priority": 2},
    180: {"name": "Championship", "country": "Scotland", "priority": 3},
    181: {"name": "League One", "country": "Scotland", "priority": 3},
    183: {"name": "FA Cup", "country": "Scotland", "priority": 3},

    # ========================================
    # 🇬🇷 GRÈCE
    # ========================================
    197: {"name": "Super League 1", "country": "Greece", "priority": 2},
    199: {"name": "Cup", "country": "Greece", "priority": 2},

    # ========================================
    # 🇨🇭 SUISSE
    # ========================================
    207: {"name": "Super League", "country": "Switzerland", "priority": 2},
    208: {"name": "Challenge League", "country": "Switzerland", "priority": 3},
    209: {"name": "Schweizer Pokal", "country": "Switzerland", "priority": 3},

    # ========================================
    # 🇦🇹 AUTRICHE
    # ========================================
    218: {"name": "Bundesliga", "country": "Austria", "priority": 2},
    219: {"name": "2. Liga", "country": "Austria", "priority": 3},
    220: {"name": "ÖFB Cup", "country": "Austria", "priority": 3},

    # ========================================
    # 🇵🇱 POLOGNE
    # ========================================
    106: {"name": "Ekstraklasa", "country": "Poland", "priority": 2},
    107: {"name": "I Liga", "country": "Poland", "priority": 3},
    108: {"name": "Cup", "country": "Poland", "priority": 3},

    # ========================================
    # 🇷🇺 RUSSIE
    # ========================================
    235: {"name": "Premier League", "country": "Russia", "priority": 2},
    236: {"name": "FNL", "country": "Russia", "priority": 3},
    237: {"name": "Cup", "country": "Russia", "priority": 3},

    # ========================================
    # 🇺🇦 UKRAINE
    # ========================================
    333: {"name": "Premier League", "country": "Ukraine", "priority": 2},
    335: {"name": "Cup", "country": "Ukraine", "priority": 3},

    # ========================================
    # 🇨🇿 RÉPUBLIQUE TCHÈQUE
    # ========================================
    345: {"name": "First League", "country": "Czech-Republic", "priority": 2},
    346: {"name": "FNL", "country": "Czech-Republic", "priority": 3},
    347: {"name": "Cup", "country": "Czech-Republic", "priority": 3},

    # ========================================
    # 🇷🇴 ROUMANIE
    # ========================================
    283: {"name": "Liga I", "country": "Romania", "priority": 2},
    284: {"name": "Liga II", "country": "Romania", "priority": 3},
    285: {"name": "Cupa României", "country": "Romania", "priority": 3},

    # ========================================
    # 🇭🇷 CROATIE
    # ========================================
    210: {"name": "HNL", "country": "Croatia", "priority": 2},
    212: {"name": "Cup", "country": "Croatia", "priority": 3},

    # ========================================
    # 🇷🇸 SERBIE
    # ========================================
    286: {"name": "Super Liga", "country": "Serbia", "priority": 2},
    287: {"name": "Prva Liga", "country": "Serbia", "priority": 3},
    288: {"name": "Cup", "country": "Serbia", "priority": 3},

    # ========================================
    # 🇩🇰 DANEMARK
    # ========================================
    119: {"name": "Superliga", "country": "Denmark", "priority": 2},
    120: {"name": "1st Division", "country": "Denmark", "priority": 3},
    121: {"name": "DBU Pokalen", "country": "Denmark", "priority": 3},

    # ========================================
    # 🇳🇴 NORVÈGE
    # ========================================
    103: {"name": "Eliteserien", "country": "Norway", "priority": 2},
    104: {"name": "OBOS-ligaen", "country": "Norway", "priority": 3},
    105: {"name": "NM Cupen", "country": "Norway", "priority": 3},

    # ========================================
    # 🇸🇪 SUÈDE
    # ========================================
    113: {"name": "Allsvenskan", "country": "Sweden", "priority": 2},
    114: {"name": "Superettan", "country": "Sweden", "priority": 3},
    115: {"name": "Svenska Cupen", "country": "Sweden", "priority": 3},

    # ========================================
    # 🇫🇮 FINLANDE
    # ========================================
    244: {"name": "Veikkausliiga", "country": "Finland", "priority": 3},
    246: {"name": "Cup", "country": "Finland", "priority": 3},

    # ========================================
    # 🇮🇸 ISLANDE
    # ========================================
    350: {"name": "Úrvalsdeild", "country": "Iceland", "priority": 3},

    # ========================================
    # 🇨🇾 CHYPRE
    # ========================================
    318: {"name": "1. Division", "country": "Cyprus", "priority": 3},
    321: {"name": "Cup", "country": "Cyprus", "priority": 3},

    # ========================================
    # 🇮🇱 ISRAËL
    # ========================================
    383: {"name": "Ligat Ha'al", "country": "Israel", "priority": 2},
    384: {"name": "State Cup", "country": "Israel", "priority": 3},

    # ========================================
    # 🌍 AFRIQUE
    # ========================================

    # Maroc
    200: {"name": "Botola Pro", "country": "Morocco", "priority": 1},
    201: {"name": "Botola 2", "country": "Morocco", "priority": 2},

    # Algérie
    186: {"name": "Ligue 1", "country": "Algeria", "priority": 2},
    187: {"name": "Ligue 2", "country": "Algeria", "priority": 3},

    # Tunisie
    202: {"name": "Ligue 1", "country": "Tunisia", "priority": 2},

    # Égypte
    233: {"name": "Premier League", "country": "Egypt", "priority": 1},
    234: {"name": "Second Division", "country": "Egypt", "priority": 3},

    # Afrique du Sud
    288: {"name": "Premier Soccer League", "country": "South-Africa", "priority": 2},

    # Nigeria
    399: {"name": "NPFL", "country": "Nigeria", "priority": 2},

    # Ghana
    404: {"name": "Premier League", "country": "Ghana", "priority": 3},

    # Côte d'Ivoire
    380: {"name": "Ligue 1", "country": "Ivory-Coast", "priority": 3},

    # Sénégal
    406: {"name": "Ligue 1", "country": "Senegal", "priority": 3},

    # Cameroun
    409: {"name": "Elite One", "country": "Cameroon", "priority": 3},

    # RD Congo
    424: {"name": "Ligue 1", "country": "Congo-DR", "priority": 3},

    # Kenya
    276: {"name": "FKF Premier League", "country": "Kenya", "priority": 3},

    # ========================================
    # 🇸🇦 MOYEN-ORIENT / GOLFE
    # ========================================

    # Arabie Saoudite
    307: {"name": "Saudi Pro League", "country": "Saudi-Arabia", "priority": 1},
    308: {"name": "Division 1", "country": "Saudi-Arabia", "priority": 2},
    309: {"name": "King Cup", "country": "Saudi-Arabia", "priority": 2},

    # Émirats Arabes Unis
    305: {"name": "UAE Pro League", "country": "UAE", "priority": 2},
    301: {"name": "Pro League", "country": "UAE", "priority": 2},

    # Qatar
    306: {"name": "Stars League", "country": "Qatar", "priority": 2},

    # Koweït
    330: {"name": "Premier League", "country": "Kuwait", "priority": 3},

    # Bahreïn
    417: {"name": "Premier League", "country": "Bahrain", "priority": 3},

    # Oman
    388: {"name": "Professional League", "country": "Oman", "priority": 3},

    # Irak
    368: {"name": "Premier League", "country": "Iraq", "priority": 3},
    542: {"name": "Iraqi League", "country": "Iraq", "priority": 3},

    # Iran
    290: {"name": "Persian Gulf Pro League", "country": "Iran", "priority": 2},

    # ========================================
    # 🌏 ASIE
    # ========================================

    # Japon
    98: {"name": "J1 League", "country": "Japan", "priority": 1},
    99: {"name": "J2 League", "country": "Japan", "priority": 2},
    517: {"name": "J3 League", "country": "Japan", "priority": 3},
    102: {"name": "Emperor Cup", "country": "Japan", "priority": 2},

    # Corée du Sud
    292: {"name": "K League 1", "country": "South-Korea", "priority": 1},
    293: {"name": "K League 2", "country": "South-Korea", "priority": 2},

    # Chine
    169: {"name": "Super League", "country": "China", "priority": 2},

    # Australie
    188: {"name": "A-League", "country": "Australia", "priority": 2},

    # Thaïlande
    296: {"name": "Thai League 1", "country": "Thailand", "priority": 3},
    298: {"name": "FA Cup", "country": "Thailand", "priority": 3},

    # Malaisie
    278: {"name": "Super League", "country": "Malaysia", "priority": 3},

    # Inde
    323: {"name": "Indian Super League", "country": "India", "priority": 3},

    # ========================================
    # 🇺🇸 AMÉRIQUES
    # ========================================

    # USA
    253: {"name": "MLS", "country": "USA", "priority": 1},
    254: {"name": "MLS Cup", "country": "USA", "priority": 2},
    255: {"name": "USL Championship", "country": "USA", "priority": 3},
    257: {"name": "US Open Cup", "country": "USA", "priority": 3},

    # Mexique
    262: {"name": "Liga MX", "country": "Mexico", "priority": 1},
    263: {"name": "Liga de Expansión", "country": "Mexico", "priority": 2},
    264: {"name": "Copa MX", "country": "Mexico", "priority": 2},

    # Argentine
    128: {"name": "Liga Profesional", "country": "Argentina", "priority": 1},
    129: {"name": "Primera Nacional", "country": "Argentina", "priority": 2},
    130: {"name": "Copa Argentina", "country": "Argentina", "priority": 2},

    # Brésil
    71: {"name": "Série A", "country": "Brazil", "priority": 1},
    72: {"name": "Série B", "country": "Brazil", "priority": 2},
    73: {"name": "Copa do Brasil", "country": "Brazil", "priority": 2},
    75: {"name": "Série C", "country": "Brazil", "priority": 3},
    475: {"name": "Paulista A1", "country": "Brazil", "priority": 2},
    604: {"name": "Catarinense", "country": "Brazil", "priority": 3},
    629: {"name": "Mineiro", "country": "Brazil", "priority": 3},
    624: {"name": "Carioca", "country": "Brazil", "priority": 2},

    # Colombie
    239: {"name": "Primera A", "country": "Colombia", "priority": 2},
    240: {"name": "Primera B", "country": "Colombia", "priority": 3},

    # Chili
    265: {"name": "Primera División", "country": "Chile", "priority": 2},

    # Uruguay
    268: {"name": "Primera División", "country": "Uruguay", "priority": 2},
    1212: {"name": "Copa de la Liga AUF", "country": "Uruguay", "priority": 3},

    # Paraguay
    270: {"name": "División Profesional", "country": "Paraguay", "priority": 3},

    # Pérou
    281: {"name": "Liga 1", "country": "Peru", "priority": 3},

    # Équateur
    242: {"name": "Serie A", "country": "Ecuador", "priority": 3},

    # Costa Rica
    162: {"name": "Primera División", "country": "Costa-Rica", "priority": 3},

    # Jamaïque
    322: {"name": "Premier League", "country": "Jamaica", "priority": 3},
}

# ========================================
# FONCTIONS UTILITAIRES
# ========================================

# Liste des IDs pour filtrage rapide
ALLOWED_LEAGUE_IDS = set(ALLOWED_LEAGUES.keys())


def get_league_priority(league_id: int) -> int:
    """Retourne la priorité d'une ligue (1=top, 3=faible, 99=non configuré)"""
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


def get_league_info(league_id: int) -> dict:
    """Retourne les infos complètes d'une ligue"""
    return ALLOWED_LEAGUES.get(league_id, {
        "name": f"Unknown League {league_id}",
        "country": "Unknown",
        "priority": 99
    })


def get_leagues_by_country(country: str) -> list:
    """Retourne toutes les ligues d'un pays"""
    return [
        {"id": lid, **info}
        for lid, info in ALLOWED_LEAGUES.items()
        if info["country"].lower() == country.lower()
    ]


def get_priority_leagues(priority: int = 1) -> list:
    """Retourne les ligues d'une priorité donnée"""
    return [
        {"id": lid, **info}
        for lid, info in ALLOWED_LEAGUES.items()
        if info["priority"] == priority
    ]


def add_league(league_id: int, name: str, country: str, priority: int = 3) -> bool:
    """Ajoute dynamiquement une ligue à la configuration"""
    if league_id not in ALLOWED_LEAGUES:
        ALLOWED_LEAGUES[league_id] = {
            "name": name,
            "country": country,
            "priority": priority
        }
        ALLOWED_LEAGUE_IDS.add(league_id)
        return True
    return False


# Statistiques
TOTAL_LEAGUES = len(ALLOWED_LEAGUES)
PRIORITY_1_COUNT = len([l for l in ALLOWED_LEAGUES.values() if l["priority"] == 1])
PRIORITY_2_COUNT = len([l for l in ALLOWED_LEAGUES.values() if l["priority"] == 2])
PRIORITY_3_COUNT = len([l for l in ALLOWED_LEAGUES.values() if l["priority"] == 3])
