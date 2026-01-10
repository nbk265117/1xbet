"""
Configuration par ligue pour les prédictions
Chaque ligue a ses propres caractéristiques (style de jeu, nombre de buts, cartons, etc.)
"""

# IDs des ligues API-Football
LEAGUE_IDS = {
    # Top 5 européens
    "Premier League": 39,
    "La Liga": 140,
    "Bundesliga": 78,
    "Serie A": 135,
    "Ligue 1": 61,

    # Autres ligues européennes
    "Eredivisie": 88,
    "Primeira Liga": 94,
    "Championship": 40,
    "Serie B": 136,
    "Segunda División": 141,
    "Eerste Divisie": 89,

    # Coupes
    "FA Cup": 45,
    "Coupe de France": 66,
    "DFB Pokal": 81,
    "Coppa Italia": 137,
    "Copa del Rey": 143,

    # International
    "Africa Cup of Nations": 6,
    "Super Cup": 556,  # Supercopa España

    # Autres
    "Pro League": 307,  # Saudi
    "Ligue 1 Tunisie": 202,
}

# Configuration par défaut (utilisée si ligue non configurée)
DEFAULT_CONFIG = {
    "weights": {
        "form": 0.20,
        "standings": 0.15,
        "h2h": 0.15,
        "home_adv": 0.12,  # Augmenté pour mieux valoriser le domicile
        "api_predictions": 0.23,
        "odds_implied": 0.10,
        "motivation": 0.05,
    },
    "home_advantage": 0.10,  # Augmenté de 0.08 à 0.10
    "defaults": {
        "goals_scored": 1.2,
        "goals_conceded": 1.1,
        "corners": 5.0,
        "yellow_cards": 1.5,
        "red_cards": 0.08,
    },
    "thresholds": {
        "over_25": 0.55,      # Prob minimale pour recommander Over 2.5
        "under_25": 0.40,     # Prob maximale pour recommander Under 2.5
        "btts_yes": 0.58,     # Augmenté de 0.50 à 0.58 (plus strict)
        "confidence_high": 0.70,
        "confidence_medium": 0.55,
        "draw_threshold": 0.08,  # Nouveau: écart min pour prédire victoire vs nul
    },
    "avg_goals_per_match": 2.5,
    "style": "balanced",  # balanced, attacking, defensive, physical
}

# Configuration spécifique par ligue
LEAGUE_CONFIGS = {
    # ==================== TOP 5 EUROPÉENS ====================

    39: {  # Premier League
        "name": "Premier League",
        "weights": {
            "form": 0.18,
            "standings": 0.12,
            "h2h": 0.12,
            "home_adv": 0.10,  # Augmenté
            "api_predictions": 0.28,
            "odds_implied": 0.15,
            "motivation": 0.05,
        },
        "home_advantage": 0.08,  # Augmenté de 0.06
        "defaults": {
            "goals_scored": 1.4,
            "goals_conceded": 1.2,
            "corners": 5.5,
            "yellow_cards": 1.6,
            "red_cards": 0.06,
        },
        "thresholds": {
            "over_25": 0.52,
            "under_25": 0.38,
            "btts_yes": 0.55,  # Augmenté de 0.48
            "confidence_high": 0.68,
            "confidence_medium": 0.53,
            "draw_threshold": 0.10,  # Plus difficile de prédire nul en PL
        },
        "avg_goals_per_match": 2.8,
        "style": "attacking",
    },

    140: {  # La Liga
        "name": "La Liga",
        "weights": {
            "form": 0.18,
            "standings": 0.18,
            "h2h": 0.15,
            "home_adv": 0.14,  # Augmenté - fort avantage domicile en Liga
            "api_predictions": 0.20,
            "odds_implied": 0.10,
            "motivation": 0.05,
        },
        "home_advantage": 0.12,  # Augmenté de 0.10
        "defaults": {
            "goals_scored": 1.2,
            "goals_conceded": 1.0,
            "corners": 4.8,
            "yellow_cards": 2.0,
            "red_cards": 0.10,
        },
        "thresholds": {
            "over_25": 0.55,
            "under_25": 0.42,
            "btts_yes": 0.55,  # Augmenté de 0.48
            "confidence_high": 0.70,
            "confidence_medium": 0.55,
            "draw_threshold": 0.07,  # Nuls plus fréquents en Liga
        },
        "avg_goals_per_match": 2.5,
        "style": "balanced",
    },

    78: {  # Bundesliga
        "name": "Bundesliga",
        "weights": {
            "form": 0.20,
            "standings": 0.12,
            "h2h": 0.12,
            "home_adv": 0.15,  # Augmenté - très fort avantage domicile
            "api_predictions": 0.24,
            "odds_implied": 0.12,
            "motivation": 0.05,
        },
        "home_advantage": 0.14,  # Augmenté de 0.12
        "defaults": {
            "goals_scored": 1.6,
            "goals_conceded": 1.4,
            "corners": 5.2,
            "yellow_cards": 1.8,
            "red_cards": 0.07,
        },
        "thresholds": {
            "over_25": 0.50,
            "under_25": 0.35,
            "btts_yes": 0.58,  # Augmenté de 0.52
            "confidence_high": 0.68,
            "confidence_medium": 0.52,
            "draw_threshold": 0.10,  # Moins de nuls en Bundesliga
        },
        "avg_goals_per_match": 3.1,
        "style": "attacking",
    },

    135: {  # Serie A
        "name": "Serie A",
        "weights": {
            "form": 0.18,
            "standings": 0.18,
            "h2h": 0.16,
            "home_adv": 0.14,  # Augmenté - fort avantage domicile en Italie
            "api_predictions": 0.20,
            "odds_implied": 0.10,
            "motivation": 0.04,
        },
        "home_advantage": 0.12,  # Augmenté de 0.09
        "defaults": {
            "goals_scored": 1.3,
            "goals_conceded": 1.1,
            "corners": 5.0,
            "yellow_cards": 2.2,
            "red_cards": 0.09,
        },
        "thresholds": {
            "over_25": 0.55,
            "under_25": 0.42,
            "btts_yes": 0.52,  # Augmenté de 0.45
            "confidence_high": 0.70,
            "confidence_medium": 0.55,
            "draw_threshold": 0.06,  # Nuls plus fréquents en Serie A
        },
        "avg_goals_per_match": 2.6,
        "style": "defensive",
    },

    61: {  # Ligue 1
        "name": "Ligue 1",
        "weights": {
            "form": 0.20,
            "standings": 0.15,
            "h2h": 0.12,
            "home_adv": 0.12,  # Augmenté
            "api_predictions": 0.24,
            "odds_implied": 0.12,
            "motivation": 0.05,
        },
        "home_advantage": 0.10,  # Augmenté de 0.08
        "defaults": {
            "goals_scored": 1.3,
            "goals_conceded": 1.2,
            "corners": 4.8,
            "yellow_cards": 1.9,
            "red_cards": 0.08,
        },
        "thresholds": {
            "over_25": 0.55,
            "under_25": 0.42,
            "btts_yes": 0.55,  # Augmenté de 0.48
            "confidence_high": 0.70,
            "confidence_medium": 0.55,
            "draw_threshold": 0.08,
        },
        "avg_goals_per_match": 2.7,
        "style": "balanced",
    },

    # ==================== AUTRES LIGUES EUROPÉENNES ====================

    88: {  # Eredivisie
        "name": "Eredivisie",
        "weights": {
            "form": 0.20,
            "standings": 0.15,
            "h2h": 0.10,
            "home_adv": 0.14,  # Augmenté - fort avantage domicile
            "api_predictions": 0.24,
            "odds_implied": 0.12,
            "motivation": 0.05,
        },
        "home_advantage": 0.12,  # Augmenté de 0.09
        "defaults": {
            "goals_scored": 1.6,
            "goals_conceded": 1.5,
            "corners": 5.3,
            "yellow_cards": 1.6,
            "red_cards": 0.06,
        },
        "thresholds": {
            "over_25": 0.48,
            "under_25": 0.32,
            "btts_yes": 0.60,  # Augmenté de 0.55 - plus strict
            "confidence_high": 0.68,
            "confidence_medium": 0.52,
            "draw_threshold": 0.12,  # Moins de nuls en Eredivisie
        },
        "avg_goals_per_match": 3.2,
        "style": "attacking",
    },

    94: {  # Primeira Liga (Portugal)
        "name": "Primeira Liga",
        "weights": {
            "form": 0.18,
            "standings": 0.18,
            "h2h": 0.15,
            "home_adv": 0.12,
            "api_predictions": 0.22,
            "odds_implied": 0.10,
            "motivation": 0.05,
        },
        "home_advantage": 0.10,
        "defaults": {
            "goals_scored": 1.3,
            "goals_conceded": 1.1,
            "corners": 5.0,
            "yellow_cards": 2.3,  # Physique
            "red_cards": 0.10,
        },
        "thresholds": {
            "over_25": 0.55,
            "under_25": 0.42,
            "btts_yes": 0.45,
            "confidence_high": 0.70,
            "confidence_medium": 0.55,
        },
        "avg_goals_per_match": 2.5,
        "style": "physical",
    },

    # ==================== DIVISIONS INFÉRIEURES ====================

    40: {  # Championship
        "name": "Championship",
        "weights": {
            "form": 0.25,  # Forme très importante
            "standings": 0.12,
            "h2h": 0.10,
            "home_adv": 0.12,
            "api_predictions": 0.22,
            "odds_implied": 0.12,
            "motivation": 0.07,
        },
        "home_advantage": 0.10,
        "defaults": {
            "goals_scored": 1.3,
            "goals_conceded": 1.2,
            "corners": 5.0,
            "yellow_cards": 1.8,
            "red_cards": 0.07,
        },
        "thresholds": {
            "over_25": 0.53,
            "under_25": 0.40,
            "btts_yes": 0.50,
            "confidence_high": 0.68,
            "confidence_medium": 0.53,
        },
        "avg_goals_per_match": 2.6,
        "style": "physical",
    },

    136: {  # Serie B
        "name": "Serie B",
        "weights": {
            "form": 0.22,
            "standings": 0.15,
            "h2h": 0.12,
            "home_adv": 0.12,
            "api_predictions": 0.22,
            "odds_implied": 0.10,
            "motivation": 0.07,
        },
        "home_advantage": 0.10,
        "defaults": {
            "goals_scored": 1.2,
            "goals_conceded": 1.1,
            "corners": 4.8,
            "yellow_cards": 2.0,
            "red_cards": 0.08,
        },
        "thresholds": {
            "over_25": 0.55,
            "under_25": 0.42,
            "btts_yes": 0.45,
            "confidence_high": 0.68,
            "confidence_medium": 0.53,
        },
        "avg_goals_per_match": 2.4,
        "style": "defensive",
    },

    141: {  # Segunda División
        "name": "Segunda División",
        "weights": {
            "form": 0.22,
            "standings": 0.15,
            "h2h": 0.12,
            "home_adv": 0.12,
            "api_predictions": 0.22,
            "odds_implied": 0.10,
            "motivation": 0.07,
        },
        "home_advantage": 0.11,
        "defaults": {
            "goals_scored": 1.1,
            "goals_conceded": 1.0,
            "corners": 4.5,
            "yellow_cards": 2.2,
            "red_cards": 0.09,
        },
        "thresholds": {
            "over_25": 0.58,  # Moins de buts
            "under_25": 0.45,
            "btts_yes": 0.42,
            "confidence_high": 0.68,
            "confidence_medium": 0.53,
        },
        "avg_goals_per_match": 2.2,
        "style": "defensive",
    },

    89: {  # Eerste Divisie
        "name": "Eerste Divisie",
        "weights": {
            "form": 0.25,
            "standings": 0.12,
            "h2h": 0.08,
            "home_adv": 0.10,
            "api_predictions": 0.25,
            "odds_implied": 0.12,
            "motivation": 0.08,
        },
        "home_advantage": 0.09,
        "defaults": {
            "goals_scored": 1.5,
            "goals_conceded": 1.4,
            "corners": 5.0,
            "yellow_cards": 1.5,
            "red_cards": 0.06,
        },
        "thresholds": {
            "over_25": 0.50,
            "under_25": 0.35,
            "btts_yes": 0.52,
            "confidence_high": 0.65,
            "confidence_medium": 0.50,
        },
        "avg_goals_per_match": 3.0,
        "style": "attacking",
    },

    # ==================== COUPES ====================

    45: {  # FA Cup
        "name": "FA Cup",
        "weights": {
            "form": 0.18,
            "standings": 0.05,  # Classement peu pertinent en coupe
            "h2h": 0.10,
            "home_adv": 0.08,  # Réduit - équipes de divisions différentes
            "api_predictions": 0.30,  # Plus important car matchs imprévisibles
            "odds_implied": 0.22,  # Cotes plus fiables
            "motivation": 0.07,
        },
        "home_advantage": 0.06,  # Réduit - surprises fréquentes
        "defaults": {
            "goals_scored": 1.2,
            "goals_conceded": 1.1,
            "corners": 4.8,
            "yellow_cards": 1.5,
            "red_cards": 0.06,
        },
        "thresholds": {
            "over_25": 0.55,
            "under_25": 0.42,
            "btts_yes": 0.50,  # Augmenté de 0.45
            "confidence_high": 0.65,
            "confidence_medium": 0.50,
            "draw_threshold": 0.05,  # Moins de nuls en coupe
        },
        "avg_goals_per_match": 2.4,
        "style": "balanced",
    },

    # ==================== LIGUES HORS EUROPE ====================

    307: {  # Saudi Pro League
        "name": "Pro League",
        "weights": {
            "form": 0.22,
            "standings": 0.15,
            "h2h": 0.12,
            "home_adv": 0.12,
            "api_predictions": 0.22,
            "odds_implied": 0.12,
            "motivation": 0.05,
        },
        "home_advantage": 0.10,
        "defaults": {
            "goals_scored": 1.2,
            "goals_conceded": 1.0,
            "corners": 4.5,
            "yellow_cards": 1.8,
            "red_cards": 0.07,
        },
        "thresholds": {
            "over_25": 0.58,
            "under_25": 0.45,
            "btts_yes": 0.55,  # Augmenté de 0.40 - était trop bas
            "confidence_high": 0.65,
            "confidence_medium": 0.50,
            "draw_threshold": 0.08,
        },
        "avg_goals_per_match": 2.3,
        "style": "defensive",
    },

    202: {  # Ligue 1 Tunisie
        "name": "Ligue 1 Tunisie",
        "weights": {
            "form": 0.25,
            "standings": 0.15,
            "h2h": 0.15,
            "home_adv": 0.15,
            "api_predictions": 0.18,
            "odds_implied": 0.07,
            "motivation": 0.05,
        },
        "home_advantage": 0.12,
        "defaults": {
            "goals_scored": 1.0,
            "goals_conceded": 0.9,
            "corners": 4.2,
            "yellow_cards": 2.0,
            "red_cards": 0.08,
        },
        "thresholds": {
            "over_25": 0.60,  # Moins de buts
            "under_25": 0.48,
            "btts_yes": 0.38,  # Beaucoup de clean sheets
            "confidence_high": 0.65,
            "confidence_medium": 0.50,
        },
        "avg_goals_per_match": 2.0,
        "style": "defensive",
    },

    # ==================== COMPÉTITIONS INTERNATIONALES ====================

    6: {  # Africa Cup of Nations
        "name": "Africa Cup of Nations",
        "weights": {
            "form": 0.20,
            "standings": 0.05,  # Pas de classement ligue
            "h2h": 0.20,  # H2H important
            "home_adv": 0.05,  # Terrain neutre souvent
            "api_predictions": 0.30,
            "odds_implied": 0.15,
            "motivation": 0.05,
        },
        "home_advantage": 0.03,  # Presque neutre
        "defaults": {
            "goals_scored": 1.1,
            "goals_conceded": 1.0,
            "corners": 4.5,
            "yellow_cards": 1.8,
            "red_cards": 0.08,
        },
        "thresholds": {
            "over_25": 0.58,
            "under_25": 0.45,
            "btts_yes": 0.42,
            "confidence_high": 0.65,
            "confidence_medium": 0.50,
        },
        "avg_goals_per_match": 2.2,
        "style": "balanced",
    },

    556: {  # Supercopa España
        "name": "Supercopa España",
        "weights": {
            "form": 0.22,
            "standings": 0.08,
            "h2h": 0.18,
            "home_adv": 0.05,  # Souvent terrain neutre
            "api_predictions": 0.28,
            "odds_implied": 0.14,
            "motivation": 0.05,
        },
        "home_advantage": 0.04,
        "defaults": {
            "goals_scored": 1.4,
            "goals_conceded": 1.2,
            "corners": 5.0,
            "yellow_cards": 1.8,
            "red_cards": 0.08,
        },
        "thresholds": {
            "over_25": 0.52,
            "under_25": 0.38,
            "btts_yes": 0.50,
            "confidence_high": 0.68,
            "confidence_medium": 0.53,
        },
        "avg_goals_per_match": 2.8,
        "style": "attacking",
    },
}


def get_league_config(league_id: int = None, league_name: str = None) -> dict:
    """
    Récupère la configuration pour une ligue donnée.

    Args:
        league_id: ID de la ligue (API-Football)
        league_name: Nom de la ligue

    Returns:
        Configuration de la ligue ou configuration par défaut
    """
    # Chercher par ID
    if league_id and league_id in LEAGUE_CONFIGS:
        return LEAGUE_CONFIGS[league_id]

    # Chercher par nom
    if league_name:
        # Chercher l'ID par nom
        for name, lid in LEAGUE_IDS.items():
            if name.lower() in league_name.lower() or league_name.lower() in name.lower():
                if lid in LEAGUE_CONFIGS:
                    return LEAGUE_CONFIGS[lid]

    # Retourner la config par défaut
    return DEFAULT_CONFIG


def get_all_leagues() -> dict:
    """Retourne toutes les ligues configurées"""
    return {
        lid: config.get("name", f"League {lid}")
        for lid, config in LEAGUE_CONFIGS.items()
    }


def get_league_style(league_id: int) -> str:
    """Retourne le style de jeu d'une ligue"""
    config = get_league_config(league_id)
    return config.get("style", "balanced")


def is_high_scoring_league(league_id: int) -> bool:
    """Vérifie si c'est une ligue avec beaucoup de buts"""
    config = get_league_config(league_id)
    return config.get("avg_goals_per_match", 2.5) >= 2.8


def is_physical_league(league_id: int) -> bool:
    """Vérifie si c'est une ligue physique (beaucoup de cartons)"""
    config = get_league_config(league_id)
    return config.get("style") == "physical" or config["defaults"]["yellow_cards"] >= 2.0
