"""
Service de Rating Elo Dynamique
Remplace le dictionnaire statique KNOWN_TEAMS par un système Elo
stocké dans MongoDB avec mise à jour après chaque match.

Formule Elo:
- New Rating = Old Rating + K * (Actual - Expected)
- Expected = 1 / (1 + 10^((OpponentRating - MyRating) / 400))

Initialisation:
- Basée sur le classement actuel: 1er = 1800, dernier = 1200
"""
import logging
from datetime import datetime
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ==================== CONSTANTES ELO ====================
DEFAULT_ELO = 1500
MIN_ELO = 1200
MAX_ELO = 2000

# K-Factor: Vitesse d'ajustement du rating
# Top ligues = plus stable (K=20), autres = plus volatile (K=30)
K_FACTOR_TOP = 20
K_FACTOR_OTHER = 30

# Top ligues avec K-Factor réduit
TOP_LEAGUES = {
    39,   # Premier League
    140,  # La Liga
    78,   # Bundesliga
    135,  # Serie A
    61,   # Ligue 1
    2,    # Champions League
    3,    # Europa League
    848,  # Conference League
    94,   # Primeira Liga
    88,   # Eredivisie
}


@dataclass
class EloTeam:
    """Équipe avec son rating Elo"""
    team_id: int
    name: str
    elo_rating: float = DEFAULT_ELO
    league_id: int = 0
    country: str = ""
    matches_played: int = 0
    last_updated: datetime = None
    initial_elo: float = DEFAULT_ELO
    season: int = 2025

    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.utcnow()


@dataclass
class EloUpdate:
    """Résultat d'une mise à jour Elo après un match"""
    home_old_elo: float
    home_new_elo: float
    home_change: float
    away_old_elo: float
    away_new_elo: float
    away_change: float
    result: str  # "home_win", "draw", "away_win"
    k_factor: int


class EloService:
    """
    Service de gestion des ratings Elo dynamiques

    Utilisation:
    - get_team_rating(): Récupère le rating Elo d'une équipe
    - initialize_from_standings(): Initialise les ratings depuis le classement
    - update_after_match(): Met à jour les ratings après un résultat
    - elo_to_strength(): Convertit Elo (1200-2000) en force (40-100)
    """

    def __init__(self, db=None):
        """
        Args:
            db: Instance de connexion MongoDB (optionnel)
        """
        self.db = db
        self._cache: Dict[int, EloTeam] = {}
        self._cache_timestamp: Dict[int, float] = {}
        self._cache_ttl = 3600  # 1 heure
        self._initialized_leagues: set = set()

    # ==================== MÉTHODES PUBLIQUES ====================

    async def get_team_rating(self, team_id: int, team_name: str = "",
                               league_id: int = 0) -> float:
        """
        Récupère le rating Elo d'une équipe

        Args:
            team_id: ID de l'équipe (API-Football)
            team_name: Nom de l'équipe (pour création si inexistant)
            league_id: ID de la ligue

        Returns:
            Rating Elo (1200-2000), DEFAULT_ELO si non trouvé
        """
        import time

        # Vérifier le cache
        if team_id in self._cache:
            cache_age = time.time() - self._cache_timestamp.get(team_id, 0)
            if cache_age < self._cache_ttl:
                return self._cache[team_id].elo_rating

        # Chercher dans MongoDB
        if self.db:
            try:
                collection = self.db.db["team_ratings"] if hasattr(self.db, 'db') and self.db.db else None
                if collection:
                    doc = await collection.find_one({"team_id": team_id})
                    if doc:
                        elo = doc.get("elo_rating", DEFAULT_ELO)
                        self._cache[team_id] = EloTeam(
                            team_id=team_id,
                            name=doc.get("team_name", team_name),
                            elo_rating=elo,
                            league_id=doc.get("league_id", league_id),
                            matches_played=doc.get("matches_played", 0)
                        )
                        self._cache_timestamp[team_id] = time.time()
                        return elo
            except Exception as e:
                logger.warning(f"Erreur MongoDB get_team_rating: {e}")

        # Équipe non trouvée - retourner défaut
        # L'initialisation se fera via initialize_from_standings()
        return DEFAULT_ELO

    def get_team_rating_sync(self, team_id: int, team_name: str = "",
                              league_id: int = 0) -> float:
        """
        Version synchrone de get_team_rating (pour backward compatibility)
        Utilise uniquement le cache local
        """
        if team_id in self._cache:
            return self._cache[team_id].elo_rating
        return DEFAULT_ELO

    async def initialize_from_standings(self, league_id: int,
                                         standings: List[Dict]) -> int:
        """
        Initialise les ratings Elo de toutes les équipes d'une ligue
        basé sur leur position au classement actuel.

        Formule: elo = 1800 - ((rank - 1) / (total - 1)) * 600
        - 1er: 1800 Elo
        - Dernier: 1200 Elo

        Args:
            league_id: ID de la ligue
            standings: Liste des équipes avec leur classement
                       Format: [{"team_id": 33, "team_name": "Man Utd", "rank": 1}, ...]

        Returns:
            Nombre d'équipes initialisées
        """
        if not standings:
            logger.warning(f"Pas de classement fourni pour ligue {league_id}")
            return 0

        total_teams = len(standings)
        initialized = 0
        now = datetime.utcnow()
        season = datetime.now().year if datetime.now().month >= 8 else datetime.now().year - 1

        for team_data in standings:
            rank = team_data.get('rank', total_teams)
            team_id = team_data.get('team_id')
            team_name = team_data.get('team_name', '')

            if not team_id:
                continue

            # Interpolation linéaire: 1er = 1800, dernier = 1200
            if total_teams > 1:
                elo = 1800 - ((rank - 1) / (total_teams - 1)) * 600
            else:
                elo = DEFAULT_ELO

            elo = max(MIN_ELO, min(MAX_ELO, round(elo, 1)))

            # Sauvegarder dans MongoDB
            if self.db:
                try:
                    collection = self.db.db["team_ratings"] if hasattr(self.db, 'db') and self.db.db else None
                    if collection:
                        await collection.update_one(
                            {"team_id": team_id},
                            {"$set": {
                                "team_id": team_id,
                                "team_name": team_name,
                                "league_id": league_id,
                                "elo_rating": elo,
                                "initial_elo": elo,
                                "season": season,
                                "last_updated": now,
                                "matches_played": 0,
                                "history": []
                            }},
                            upsert=True
                        )
                        initialized += 1
                except Exception as e:
                    logger.error(f"Erreur MongoDB initialize: {e}")

            # Mettre en cache
            import time
            self._cache[team_id] = EloTeam(
                team_id=team_id,
                name=team_name,
                elo_rating=elo,
                league_id=league_id,
                initial_elo=elo,
                season=season
            )
            self._cache_timestamp[team_id] = time.time()

        self._initialized_leagues.add(league_id)
        logger.info(f"[ELO] Initialisé {initialized} équipes pour ligue {league_id}")
        return initialized

    async def update_after_match(self, home_id: int, away_id: int,
                                  home_goals: int, away_goals: int,
                                  league_id: int = 0) -> EloUpdate:
        """
        Met à jour les ratings Elo après un match

        Args:
            home_id: ID équipe domicile
            away_id: ID équipe extérieur
            home_goals: Buts domicile
            away_goals: Buts extérieur
            league_id: ID de la ligue (pour K-factor)

        Returns:
            EloUpdate avec les anciens/nouveaux ratings
        """
        # Récupérer les ratings actuels
        home_elo = await self.get_team_rating(home_id, league_id=league_id)
        away_elo = await self.get_team_rating(away_id, league_id=league_id)

        # Déterminer K-factor
        k = K_FACTOR_TOP if league_id in TOP_LEAGUES else K_FACTOR_OTHER

        # Calculer les scores attendus (formule Elo)
        exp_home = 1 / (1 + 10 ** ((away_elo - home_elo) / 400))
        exp_away = 1 - exp_home

        # Scores réels (1 = victoire, 0.5 = nul, 0 = défaite)
        if home_goals > away_goals:
            actual_home, actual_away = 1.0, 0.0
            result = "home_win"
        elif away_goals > home_goals:
            actual_home, actual_away = 0.0, 1.0
            result = "away_win"
        else:
            actual_home, actual_away = 0.5, 0.5
            result = "draw"

        # Calculer les nouveaux ratings
        new_home_elo = home_elo + k * (actual_home - exp_home)
        new_away_elo = away_elo + k * (actual_away - exp_away)

        # Limiter aux bornes
        new_home_elo = max(MIN_ELO, min(MAX_ELO, round(new_home_elo, 1)))
        new_away_elo = max(MIN_ELO, min(MAX_ELO, round(new_away_elo, 1)))

        # Sauvegarder dans MongoDB
        now = datetime.utcnow()
        if self.db:
            try:
                collection = self.db.db["team_ratings"] if hasattr(self.db, 'db') and self.db.db else None
                if collection:
                    # Update équipe domicile
                    await collection.update_one(
                        {"team_id": home_id},
                        {
                            "$set": {
                                "elo_rating": new_home_elo,
                                "last_updated": now
                            },
                            "$inc": {"matches_played": 1},
                            "$push": {
                                "history": {
                                    "$each": [{
                                        "date": now,
                                        "opponent_id": away_id,
                                        "result": "W" if result == "home_win" else ("D" if result == "draw" else "L"),
                                        "old_elo": home_elo,
                                        "new_elo": new_home_elo,
                                        "k_factor": k
                                    }],
                                    "$slice": -20  # Garder les 20 derniers
                                }
                            }
                        },
                        upsert=True
                    )

                    # Update équipe extérieur
                    await collection.update_one(
                        {"team_id": away_id},
                        {
                            "$set": {
                                "elo_rating": new_away_elo,
                                "last_updated": now
                            },
                            "$inc": {"matches_played": 1},
                            "$push": {
                                "history": {
                                    "$each": [{
                                        "date": now,
                                        "opponent_id": home_id,
                                        "result": "W" if result == "away_win" else ("D" if result == "draw" else "L"),
                                        "old_elo": away_elo,
                                        "new_elo": new_away_elo,
                                        "k_factor": k
                                    }],
                                    "$slice": -20
                                }
                            }
                        },
                        upsert=True
                    )
            except Exception as e:
                logger.error(f"Erreur MongoDB update_after_match: {e}")

        # Mettre à jour le cache
        import time
        if home_id in self._cache:
            self._cache[home_id].elo_rating = new_home_elo
            self._cache[home_id].matches_played += 1
            self._cache_timestamp[home_id] = time.time()
        if away_id in self._cache:
            self._cache[away_id].elo_rating = new_away_elo
            self._cache[away_id].matches_played += 1
            self._cache_timestamp[away_id] = time.time()

        change_home = new_home_elo - home_elo
        change_away = new_away_elo - away_elo
        logger.info(f"[ELO] Update: Home {home_elo:.0f}→{new_home_elo:.0f} ({change_home:+.1f}), "
                    f"Away {away_elo:.0f}→{new_away_elo:.0f} ({change_away:+.1f})")

        return EloUpdate(
            home_old_elo=home_elo,
            home_new_elo=new_home_elo,
            home_change=change_home,
            away_old_elo=away_elo,
            away_new_elo=new_away_elo,
            away_change=change_away,
            result=result,
            k_factor=k
        )

    def elo_to_strength(self, elo: float) -> int:
        """
        Convertit un rating Elo (1200-2000) en score de force (40-100)
        pour compatibilité avec le système existant

        Mapping linéaire:
        - 1200 Elo → 40 strength
        - 2000 Elo → 100 strength

        Args:
            elo: Rating Elo

        Returns:
            Score de force (40-100)
        """
        # strength = 40 + ((elo - 1200) / 800) * 60
        strength = 40 + ((elo - MIN_ELO) / (MAX_ELO - MIN_ELO)) * 60
        return max(40, min(100, int(round(strength))))

    def strength_to_elo(self, strength: int) -> float:
        """
        Convertit un score de force (40-100) en rating Elo (1200-2000)
        Inverse de elo_to_strength()

        Args:
            strength: Score de force (40-100)

        Returns:
            Rating Elo
        """
        # elo = 1200 + ((strength - 40) / 60) * 800
        elo = MIN_ELO + ((strength - 40) / 60) * (MAX_ELO - MIN_ELO)
        return max(MIN_ELO, min(MAX_ELO, round(elo, 1)))

    def calculate_expected_score(self, rating_a: float, rating_b: float) -> float:
        """
        Calcule le score attendu pour l'équipe A contre l'équipe B

        Args:
            rating_a: Rating Elo équipe A
            rating_b: Rating Elo équipe B

        Returns:
            Probabilité de victoire (0-1)
        """
        return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

    async def get_league_rankings(self, league_id: int) -> List[Dict]:
        """
        Récupère le classement Elo d'une ligue

        Args:
            league_id: ID de la ligue

        Returns:
            Liste des équipes triées par Elo décroissant
        """
        rankings = []

        if self.db:
            try:
                collection = self.db.db["team_ratings"] if hasattr(self.db, 'db') and self.db.db else None
                if collection:
                    cursor = collection.find({"league_id": league_id}).sort("elo_rating", -1)
                    async for doc in cursor:
                        rankings.append({
                            "team_id": doc["team_id"],
                            "team_name": doc.get("team_name", ""),
                            "elo_rating": doc["elo_rating"],
                            "matches_played": doc.get("matches_played", 0),
                            "strength": self.elo_to_strength(doc["elo_rating"])
                        })
            except Exception as e:
                logger.error(f"Erreur get_league_rankings: {e}")

        return rankings

    def clear_cache(self):
        """Vide le cache local"""
        self._cache.clear()
        self._cache_timestamp.clear()
        logger.info("[ELO] Cache vidé")

    def is_league_initialized(self, league_id: int) -> bool:
        """Vérifie si une ligue a été initialisée"""
        return league_id in self._initialized_leagues


# ==================== INSTANCE GLOBALE ====================
# Sera initialisée avec la connexion DB au démarrage
elo_service: Optional[EloService] = None


def init_elo_service(db=None) -> EloService:
    """
    Initialise le service Elo global

    Args:
        db: Connexion MongoDB

    Returns:
        Instance EloService
    """
    global elo_service
    elo_service = EloService(db)
    logger.info("[ELO] Service Elo initialisé")
    return elo_service


def get_elo_service() -> Optional[EloService]:
    """Retourne l'instance globale du service Elo"""
    return elo_service
