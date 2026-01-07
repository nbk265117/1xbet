"""
Modèles pour le suivi des résultats des paris
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict
from enum import Enum


class BetResult(Enum):
    """Résultat d'un pari"""
    PENDING = "En attente"
    WON = "Gagné"
    LOST = "Perdu"
    VOID = "Annulé"
    POSTPONED = "Reporté"


@dataclass
class PredictionResult:
    """Résultat d'une prédiction individuelle"""
    match_id: int
    home_team: str
    away_team: str
    league: str
    match_date: datetime

    # Prédiction
    bet_type: str
    predicted_odds: float
    confidence: str

    # Résultat réel
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    result: BetResult = BetResult.PENDING

    # Statistiques du match
    total_goals: Optional[int] = None
    both_scored: Optional[bool] = None

    def evaluate(self) -> BetResult:
        """Évalue si le pari est gagné ou perdu"""
        if self.home_score is None or self.away_score is None:
            return BetResult.PENDING

        self.total_goals = self.home_score + self.away_score
        self.both_scored = self.home_score > 0 and self.away_score > 0

        bet = self.bet_type.upper()

        # 1X2
        if bet == "1":
            self.result = BetResult.WON if self.home_score > self.away_score else BetResult.LOST
        elif bet == "X":
            self.result = BetResult.WON if self.home_score == self.away_score else BetResult.LOST
        elif bet == "2":
            self.result = BetResult.WON if self.away_score > self.home_score else BetResult.LOST

        # Double Chance
        elif bet == "1X":
            self.result = BetResult.WON if self.home_score >= self.away_score else BetResult.LOST
        elif bet == "X2":
            self.result = BetResult.WON if self.away_score >= self.home_score else BetResult.LOST
        elif bet == "12":
            self.result = BetResult.WON if self.home_score != self.away_score else BetResult.LOST

        # Over/Under
        elif "OVER 1.5" in bet:
            self.result = BetResult.WON if self.total_goals >= 2 else BetResult.LOST
        elif "OVER 2.5" in bet:
            self.result = BetResult.WON if self.total_goals >= 3 else BetResult.LOST
        elif "OVER 3.5" in bet:
            self.result = BetResult.WON if self.total_goals >= 4 else BetResult.LOST
        elif "UNDER 1.5" in bet:
            self.result = BetResult.WON if self.total_goals < 2 else BetResult.LOST
        elif "UNDER 2.5" in bet:
            self.result = BetResult.WON if self.total_goals < 3 else BetResult.LOST
        elif "UNDER 3.5" in bet:
            self.result = BetResult.WON if self.total_goals < 4 else BetResult.LOST

        # BTTS
        elif "BTTS OUI" in bet or "BTTS YES" in bet:
            self.result = BetResult.WON if self.both_scored else BetResult.LOST
        elif "BTTS NON" in bet or "BTTS NO" in bet:
            self.result = BetResult.WON if not self.both_scored else BetResult.LOST

        # Combinés
        elif "1 + OVER 1.5" in bet:
            self.result = BetResult.WON if (self.home_score > self.away_score and self.total_goals >= 2) else BetResult.LOST
        elif "2 + OVER 1.5" in bet:
            self.result = BetResult.WON if (self.away_score > self.home_score and self.total_goals >= 2) else BetResult.LOST
        elif "BTTS + OVER 2.5" in bet:
            self.result = BetResult.WON if (self.both_scored and self.total_goals >= 3) else BetResult.LOST

        # Domicile/Extérieur +0.5/+1.5
        elif "DOMICILE +0.5" in bet:
            self.result = BetResult.WON if self.home_score >= 1 else BetResult.LOST
        elif "DOMICILE +1.5" in bet:
            self.result = BetResult.WON if self.home_score >= 2 else BetResult.LOST
        elif "EXTÉRIEUR +0.5" in bet or "EXTERIEUR +0.5" in bet:
            self.result = BetResult.WON if self.away_score >= 1 else BetResult.LOST
        elif "EXTÉRIEUR +1.5" in bet or "EXTERIEUR +1.5" in bet:
            self.result = BetResult.WON if self.away_score >= 2 else BetResult.LOST

        else:
            # Type de pari non reconnu
            self.result = BetResult.VOID

        return self.result

    def to_dict(self) -> Dict:
        """Convertit en dictionnaire pour JSON"""
        return {
            "match_id": self.match_id,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "league": self.league,
            "match_date": self.match_date.isoformat(),
            "bet_type": self.bet_type,
            "predicted_odds": self.predicted_odds,
            "confidence": self.confidence,
            "home_score": self.home_score,
            "away_score": self.away_score,
            "result": self.result.value,
            "total_goals": self.total_goals,
            "both_scored": self.both_scored
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "PredictionResult":
        """Crée depuis un dictionnaire"""
        result = cls(
            match_id=data["match_id"],
            home_team=data["home_team"],
            away_team=data["away_team"],
            league=data["league"],
            match_date=datetime.fromisoformat(data["match_date"]),
            bet_type=data["bet_type"],
            predicted_odds=data["predicted_odds"],
            confidence=data["confidence"],
            home_score=data.get("home_score"),
            away_score=data.get("away_score"),
            total_goals=data.get("total_goals"),
            both_scored=data.get("both_scored")
        )
        result.result = BetResult(data.get("result", "En attente"))
        return result


@dataclass
class TicketResult:
    """Résultat d'un ticket complet"""
    ticket_id: int
    ticket_name: str
    date: datetime
    predictions: List[PredictionResult] = field(default_factory=list)
    total_odds: float = 1.0
    stake: float = 10.0  # Mise par défaut

    @property
    def status(self) -> BetResult:
        """Statut global du ticket"""
        if any(p.result == BetResult.PENDING for p in self.predictions):
            return BetResult.PENDING
        if all(p.result == BetResult.WON for p in self.predictions):
            return BetResult.WON
        if any(p.result == BetResult.LOST for p in self.predictions):
            return BetResult.LOST
        return BetResult.VOID

    @property
    def won_count(self) -> int:
        return sum(1 for p in self.predictions if p.result == BetResult.WON)

    @property
    def lost_count(self) -> int:
        return sum(1 for p in self.predictions if p.result == BetResult.LOST)

    @property
    def potential_win(self) -> float:
        return self.stake * self.total_odds

    @property
    def profit(self) -> float:
        if self.status == BetResult.WON:
            return self.potential_win - self.stake
        elif self.status == BetResult.LOST:
            return -self.stake
        return 0.0

    def to_dict(self) -> Dict:
        return {
            "ticket_id": self.ticket_id,
            "ticket_name": self.ticket_name,
            "date": self.date.isoformat(),
            "total_odds": self.total_odds,
            "stake": self.stake,
            "status": self.status.value,
            "won_count": self.won_count,
            "lost_count": self.lost_count,
            "profit": self.profit,
            "predictions": [p.to_dict() for p in self.predictions]
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "TicketResult":
        ticket = cls(
            ticket_id=data["ticket_id"],
            ticket_name=data["ticket_name"],
            date=datetime.fromisoformat(data["date"]),
            total_odds=data["total_odds"],
            stake=data.get("stake", 10.0)
        )
        ticket.predictions = [PredictionResult.from_dict(p) for p in data["predictions"]]
        return ticket


@dataclass
class DailyStats:
    """Statistiques quotidiennes"""
    date: datetime
    total_predictions: int = 0
    won: int = 0
    lost: int = 0
    void: int = 0
    pending: int = 0

    total_tickets: int = 0
    tickets_won: int = 0
    tickets_lost: int = 0

    total_stake: float = 0.0
    total_profit: float = 0.0

    @property
    def win_rate(self) -> float:
        decided = self.won + self.lost
        return (self.won / decided * 100) if decided > 0 else 0.0

    @property
    def roi(self) -> float:
        return (self.total_profit / self.total_stake * 100) if self.total_stake > 0 else 0.0

    def to_dict(self) -> Dict:
        return {
            "date": self.date.isoformat(),
            "total_predictions": self.total_predictions,
            "won": self.won,
            "lost": self.lost,
            "void": self.void,
            "pending": self.pending,
            "win_rate": round(self.win_rate, 2),
            "total_tickets": self.total_tickets,
            "tickets_won": self.tickets_won,
            "tickets_lost": self.tickets_lost,
            "total_stake": self.total_stake,
            "total_profit": round(self.total_profit, 2),
            "roi": round(self.roi, 2)
        }
