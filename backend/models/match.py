from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum


class PredictionConfidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class Team(BaseModel):
    id: int
    name: str
    logo: Optional[str] = None
    ranking: Optional[int] = None
    form: Optional[str] = None  # ex: "WWDLW"
    home_wins: int = 0
    home_draws: int = 0
    home_losses: int = 0
    away_wins: int = 0
    away_draws: int = 0
    away_losses: int = 0


class Player(BaseModel):
    id: int
    name: str
    position: str
    is_injured: bool = False
    is_suspended: bool = False
    is_key_player: bool = False
    goals_scored: int = 0
    assists: int = 0


class Coach(BaseModel):
    id: int
    name: str
    win_rate: float = 0.0
    experience_years: int = 0


class Match(BaseModel):
    id: int
    league_id: int
    league_name: str
    league_country: str
    date: datetime
    home_team: Team
    away_team: Team
    venue: Optional[str] = None
    referee: Optional[str] = None
    status: str = "scheduled"


class HeadToHead(BaseModel):
    total_matches: int = 0
    home_wins: int = 0
    away_wins: int = 0
    draws: int = 0
    home_goals: int = 0
    away_goals: int = 0


class MatchAnalysis(BaseModel):
    match: Match
    head_to_head: HeadToHead
    home_team_form: List[str] = []  # Derniers 5 résultats
    away_team_form: List[str] = []
    home_injuries: List[Player] = []
    away_injuries: List[Player] = []
    home_coach: Optional[Coach] = None
    away_coach: Optional[Coach] = None


class Prediction(BaseModel):
    match_id: int
    match: Match
    predicted_outcome: str  # "home", "draw", "away"
    home_win_probability: float
    draw_probability: float
    away_win_probability: float
    confidence: PredictionConfidence
    recommended_bet: str
    odds_value: Optional[float] = None
    analysis_summary: str
    factors: List[str] = []


class ComboMatch(BaseModel):
    match_id: int
    teams: str  # "Team A vs Team B"
    prediction: str
    confidence: PredictionConfidence
    probability: float


class BestCombo(BaseModel):
    id: str
    matches: List[ComboMatch]
    total_probability: float
    risk_level: str  # "safe", "moderate", "risky"
    expected_value: float
    description: str
