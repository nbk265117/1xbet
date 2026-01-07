"""
Modèles de données pour le bot de paris
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class BetType(Enum):
    """Types de paris disponibles"""
    # 1X2
    HOME_WIN = "1"
    DRAW = "X"
    AWAY_WIN = "2"
    DOUBLE_CHANCE_1X = "1X"
    DOUBLE_CHANCE_X2 = "X2"
    DOUBLE_CHANCE_12 = "12"

    # Buts (Match entier)
    OVER_1_5 = "Over 1.5"
    OVER_2_5 = "Over 2.5"
    OVER_3_5 = "Over 3.5"
    UNDER_1_5 = "Under 1.5"
    UNDER_2_5 = "Under 2.5"
    UNDER_3_5 = "Under 3.5"
    BTTS_YES = "BTTS Oui"
    BTTS_NO = "BTTS Non"
    HOME_OVER_0_5 = "Domicile +0.5"
    HOME_OVER_1_5 = "Domicile +1.5"
    AWAY_OVER_0_5 = "Extérieur +0.5"
    AWAY_OVER_1_5 = "Extérieur +1.5"
    HOME_CLEAN_SHEET = "Domicile sans encaisser"
    AWAY_CLEAN_SHEET = "Extérieur sans encaisser"

    # Mi-temps (1ère période)
    HT_HOME_WIN = "MT 1"
    HT_DRAW = "MT X"
    HT_AWAY_WIN = "MT 2"
    HT_OVER_0_5 = "MT Over 0.5"
    HT_OVER_1_5 = "MT Over 1.5"
    HT_UNDER_0_5 = "MT Under 0.5"
    HT_UNDER_1_5 = "MT Under 1.5"
    HT_BTTS_YES = "MT BTTS Oui"
    HT_BTTS_NO = "MT BTTS Non"

    # 2ème Mi-temps
    H2_OVER_0_5 = "2MT Over 0.5"
    H2_OVER_1_5 = "2MT Over 1.5"
    H2_BTTS_YES = "2MT BTTS Oui"

    # HT/FT (Mi-temps / Fin)
    HT_FT_1_1 = "MT/FT 1/1"
    HT_FT_1_X = "MT/FT 1/X"
    HT_FT_1_2 = "MT/FT 1/2"
    HT_FT_X_1 = "MT/FT X/1"
    HT_FT_X_X = "MT/FT X/X"
    HT_FT_X_2 = "MT/FT X/2"
    HT_FT_2_1 = "MT/FT 2/1"
    HT_FT_2_X = "MT/FT 2/X"
    HT_FT_2_2 = "MT/FT 2/2"

    # Corners
    CORNERS_OVER_7_5 = "Corners +7.5"
    CORNERS_OVER_8_5 = "Corners +8.5"
    CORNERS_OVER_9_5 = "Corners +9.5"
    CORNERS_OVER_10_5 = "Corners +10.5"
    CORNERS_UNDER_9_5 = "Corners -9.5"
    CORNERS_UNDER_10_5 = "Corners -10.5"
    HOME_CORNERS_OVER_4_5 = "Corners Dom +4.5"
    AWAY_CORNERS_OVER_3_5 = "Corners Ext +3.5"

    # Cartons
    CARDS_OVER_2_5 = "Cartons +2.5"
    CARDS_OVER_3_5 = "Cartons +3.5"
    CARDS_OVER_4_5 = "Cartons +4.5"
    CARDS_OVER_5_5 = "Cartons +5.5"
    CARDS_UNDER_4_5 = "Cartons -4.5"
    YELLOW_CARDS_OVER_2_5 = "Jaunes +2.5"
    YELLOW_CARDS_OVER_3_5 = "Jaunes +3.5"
    RED_CARD_YES = "Carton Rouge Oui"
    RED_CARD_NO = "Carton Rouge Non"
    HOME_CARD_FIRST = "1er Carton Dom"
    AWAY_CARD_FIRST = "1er Carton Ext"

    # Combinés
    HOME_WIN_AND_OVER_1_5 = "1 + Over 1.5"
    AWAY_WIN_AND_OVER_1_5 = "2 + Over 1.5"
    BTTS_AND_OVER_2_5 = "BTTS + Over 2.5"
    FIRST_HALF_BTTS = "MT BTTS"


@dataclass
class Team:
    """Représente une équipe"""
    id: int
    name: str
    logo: Optional[str] = None

    # Statistiques de forme
    form: str = ""  # Ex: "WWDLW"
    goals_scored_last_5: int = 0
    goals_conceded_last_5: int = 0
    wins_last_5: int = 0
    draws_last_5: int = 0
    losses_last_5: int = 0

    # Classement
    league_position: int = 0
    league_points: int = 0

    # Stats saison
    home_wins: int = 0
    home_draws: int = 0
    home_losses: int = 0
    away_wins: int = 0
    away_draws: int = 0
    away_losses: int = 0

    # Clean sheets
    clean_sheets: int = 0
    failed_to_score: int = 0


@dataclass
class Match:
    """Représente un match"""
    id: int
    league_id: int
    league_name: str
    country: str

    home_team: Team
    away_team: Team

    date: datetime
    venue: Optional[str] = None
    referee: Optional[str] = None

    # Head to Head
    h2h_home_wins: int = 0
    h2h_draws: int = 0
    h2h_away_wins: int = 0
    h2h_total_games: int = 0
    h2h_avg_goals: float = 0.0

    # Statistiques avancées
    home_avg_goals_scored: float = 0.0
    home_avg_goals_conceded: float = 0.0
    away_avg_goals_scored: float = 0.0
    away_avg_goals_conceded: float = 0.0

    # Corners moyens
    home_avg_corners: float = 0.0
    away_avg_corners: float = 0.0

    # Cartons moyens
    home_avg_cards: float = 0.0
    away_avg_cards: float = 0.0

    # Importance du match
    is_derby: bool = False
    is_title_decider: bool = False
    is_relegation_battle: bool = False

    def __str__(self):
        return f"{self.home_team.name} vs {self.away_team.name} ({self.league_name})"


@dataclass
class Prediction:
    """Représente une prédiction pour un match"""
    match: Match
    bet_type: BetType
    confidence: str  # ÉLEVÉ, MOYEN, FAIBLE
    odds_estimate: float = 1.0
    reasoning: str = ""

    # Scores de l'analyse
    home_win_probability: float = 0.0
    draw_probability: float = 0.0
    away_win_probability: float = 0.0
    over_2_5_probability: float = 0.0
    btts_probability: float = 0.0

    def __str__(self):
        return f"{self.match} → {self.bet_type.value} ({self.confidence})"


@dataclass
class Ticket:
    """Représente un ticket de paris (combiné)"""
    id: int
    name: str
    predictions: List[Prediction] = field(default_factory=list)
    total_odds: float = 1.0
    confidence_level: str = "MOYEN"
    risk_level: str = "MOYEN"  # FAIBLE, MOYEN, ÉLEVÉ
    created_at: datetime = field(default_factory=datetime.now)

    def add_prediction(self, prediction: Prediction):
        self.predictions.append(prediction)
        self.total_odds *= prediction.odds_estimate
        self._update_confidence()

    def _update_confidence(self):
        """Met à jour le niveau de confiance global du ticket"""
        if not self.predictions:
            return

        high_count = sum(1 for p in self.predictions if p.confidence == "ÉLEVÉ")
        low_count = sum(1 for p in self.predictions if p.confidence == "FAIBLE")
        total = len(self.predictions)

        if high_count / total >= 0.7:
            self.confidence_level = "ÉLEVÉ"
        elif low_count / total >= 0.5:
            self.confidence_level = "FAIBLE"
        else:
            self.confidence_level = "MOYEN"

    def get_summary(self) -> str:
        """Génère un résumé du ticket"""
        lines = [
            f"🎟️ TICKET #{self.id} - {self.name}",
            f"📊 Confiance: {self.confidence_level} | Risque: {self.risk_level}",
            f"💰 Cote totale estimée: {self.total_odds:.2f}",
            f"📅 Créé le: {self.created_at.strftime('%d/%m/%Y %H:%M')}",
            "",
            "📋 SÉLECTIONS:",
            "-" * 40
        ]

        for i, pred in enumerate(self.predictions, 1):
            lines.append(
                f"{i}. {pred.match.home_team.name} vs {pred.match.away_team.name}"
            )
            lines.append(f"   🏆 {pred.match.league_name}")
            lines.append(f"   🎯 Pari: {pred.bet_type.value}")
            lines.append(f"   📈 Confiance: {pred.confidence}")
            lines.append(f"   💡 {pred.reasoning}")
            lines.append("")

        return "\n".join(lines)

    def __len__(self):
        return len(self.predictions)
