import httpx
import os
from datetime import datetime, date
from typing import List, Optional, Dict, Any
import json
from pathlib import Path
import re

from models.match import Match, Team, Prediction, PredictionConfidence, ComboMatch, BestCombo


class PolymarketFetcher:
    """Service pour récupérer les marchés sportifs depuis Polymarket"""

    def __init__(self):
        self.gamma_api = "https://gamma-api.polymarket.com"
        self.clob_api = "https://clob.polymarket.com"
        self.cache_dir = Path(__file__).parent.parent / "data" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Ton adresse wallet
        self.wallet_address = os.getenv(
            "POLYMARKET_WALLET",
            "0x09894262713eAE7D99631ee0cA79559470925247"
        )

    def _get_cache_path(self, cache_key: str) -> Path:
        return self.cache_dir / f"{cache_key}.json"

    def _get_from_cache(self, cache_key: str, max_age_minutes: int = 5) -> Optional[dict]:
        """Cache court pour les données de marché (5 min par défaut)"""
        cache_path = self._get_cache_path(cache_key)
        if cache_path.exists():
            cache_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
            age_minutes = (datetime.now() - cache_time).total_seconds() / 60
            if age_minutes < max_age_minutes:
                with open(cache_path, "r") as f:
                    return json.load(f)
        return None

    def _save_to_cache(self, cache_key: str, data: Any):
        cache_path = self._get_cache_path(cache_key)
        with open(cache_path, "w") as f:
            json.dump(data, f)

    async def fetch_football_markets(self) -> List[Dict[str, Any]]:
        """Récupère tous les marchés de football actifs sur Polymarket"""
        cache_key = "polymarket_football_markets"

        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        markets = []

        async with httpx.AsyncClient() as client:
            try:
                # Récupérer les marchés de sports
                # Polymarket utilise des tags pour catégoriser les marchés
                response = await client.get(
                    f"{self.gamma_api}/markets",
                    params={
                        "closed": "false",
                        "limit": 100,
                        "order": "endDate",
                        "ascending": "true",
                    },
                    timeout=30.0,
                )

                if response.status_code == 200:
                    all_markets = response.json()

                    # Filtrer les marchés de football
                    football_keywords = [
                        "soccer", "football", "premier league", "la liga",
                        "serie a", "bundesliga", "ligue 1", "champions league",
                        "world cup", "euro", "copa", "uefa", "fifa",
                        "manchester", "liverpool", "chelsea", "arsenal",
                        "real madrid", "barcelona", "psg", "bayern",
                        "juventus", "inter", "milan", "dortmund"
                    ]

                    for market in all_markets:
                        question = market.get("question", "").lower()
                        description = market.get("description", "").lower()
                        tags = [t.lower() for t in market.get("tags", [])]

                        # Vérifier si c'est un marché de football
                        is_football = (
                            "football" in tags or
                            "soccer" in tags or
                            "sports" in tags or
                            any(kw in question for kw in football_keywords) or
                            any(kw in description for kw in football_keywords)
                        )

                        if is_football:
                            markets.append(market)

                # Essayer aussi la recherche directe
                search_response = await client.get(
                    f"{self.gamma_api}/markets",
                    params={
                        "tag": "Sports",
                        "closed": "false",
                        "limit": 50,
                    },
                    timeout=30.0,
                )

                if search_response.status_code == 200:
                    sports_markets = search_response.json()
                    for market in sports_markets:
                        if market.get("id") not in [m.get("id") for m in markets]:
                            question = market.get("question", "").lower()
                            if any(kw in question for kw in football_keywords):
                                markets.append(market)

            except Exception as e:
                print(f"Erreur lors de la récupération des marchés Polymarket: {e}")

        if markets:
            self._save_to_cache(cache_key, markets)

        return markets

    async def fetch_all_sports_markets(self) -> List[Dict[str, Any]]:
        """Récupère TOUS les marchés sportifs sur Polymarket"""
        cache_key = "polymarket_all_sports"

        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        markets = []

        async with httpx.AsyncClient() as client:
            try:
                # Méthode 1: Recherche par tag Sports
                response = await client.get(
                    f"{self.gamma_api}/markets",
                    params={
                        "closed": "false",
                        "limit": 200,
                    },
                    timeout=30.0,
                )

                if response.status_code == 200:
                    all_markets = response.json()

                    sports_keywords = [
                        "win", "winner", "championship", "match", "game",
                        "vs", "versus", "beat", "defeat", "score",
                        "soccer", "football", "basketball", "nba", "nfl",
                        "tennis", "f1", "formula", "boxing", "ufc", "mma",
                        "premier league", "champions league", "world cup",
                        "super bowl", "playoffs", "finals"
                    ]

                    for market in all_markets:
                        question = market.get("question", "").lower()
                        tags = [t.lower() for t in market.get("tags", [])]

                        is_sports = (
                            "sports" in tags or
                            any(kw in question for kw in sports_keywords)
                        )

                        if is_sports:
                            markets.append(market)

            except Exception as e:
                print(f"Erreur: {e}")

        if markets:
            self._save_to_cache(cache_key, markets)

        return markets

    def parse_market_to_match(self, market: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convertit un marché Polymarket en format match pour notre app"""
        try:
            question = market.get("question", "")

            # Extraire les équipes du titre (pattern: "Team A vs Team B" ou "Will Team A win")
            vs_match = re.search(r"(.+?)\s+(?:vs\.?|versus)\s+(.+?)(?:\?|$)", question, re.IGNORECASE)
            win_match = re.search(r"Will\s+(.+?)\s+(?:win|beat|defeat)", question, re.IGNORECASE)

            home_team = "Team A"
            away_team = "Team B"

            if vs_match:
                home_team = vs_match.group(1).strip()
                away_team = vs_match.group(2).strip()
            elif win_match:
                home_team = win_match.group(1).strip()
                away_team = "Opponent"

            # Récupérer les outcomes et leurs prix
            outcomes = market.get("outcomes", [])
            outcome_prices = market.get("outcomePrices", [])

            # Calculer les probabilités à partir des prix
            probabilities = {}
            if outcome_prices:
                try:
                    prices = [float(p) for p in outcome_prices]
                    for i, outcome in enumerate(outcomes):
                        if i < len(prices):
                            probabilities[outcome] = prices[i] * 100
                except:
                    pass

            return {
                "id": market.get("id"),
                "condition_id": market.get("conditionId"),
                "question": question,
                "description": market.get("description", ""),
                "home_team": home_team,
                "away_team": away_team,
                "end_date": market.get("endDate"),
                "outcomes": outcomes,
                "probabilities": probabilities,
                "volume": market.get("volume", 0),
                "liquidity": market.get("liquidity", 0),
                "image": market.get("image"),
                "slug": market.get("slug"),
                "polymarket_url": f"https://polymarket.com/event/{market.get('slug', '')}",
                "tags": market.get("tags", []),
            }
        except Exception as e:
            print(f"Erreur parsing market: {e}")
            return None

    async def get_market_orderbook(self, token_id: str) -> Dict[str, Any]:
        """Récupère le carnet d'ordres pour un marché"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.clob_api}/book",
                    params={"token_id": token_id},
                    timeout=30.0,
                )

                if response.status_code == 200:
                    return response.json()
            except Exception as e:
                print(f"Erreur orderbook: {e}")

        return {}

    async def get_football_predictions(self) -> List[Dict[str, Any]]:
        """Génère des prédictions basées sur les marchés Polymarket"""
        markets = await self.fetch_football_markets()

        if not markets:
            # Essayer tous les sports si pas de football spécifique
            markets = await self.fetch_all_sports_markets()

        predictions = []

        for market in markets:
            parsed = self.parse_market_to_match(market)
            if parsed:
                # Calculer la confiance basée sur le volume et la liquidité
                volume = float(parsed.get("volume", 0) or 0)
                liquidity = float(parsed.get("liquidity", 0) or 0)

                if volume > 100000:
                    confidence = "very_high"
                elif volume > 50000:
                    confidence = "high"
                elif volume > 10000:
                    confidence = "medium"
                else:
                    confidence = "low"

                # Déterminer la meilleure prédiction
                probs = parsed.get("probabilities", {})
                if probs:
                    best_outcome = max(probs.items(), key=lambda x: x[1])
                    parsed["recommended_bet"] = best_outcome[0]
                    parsed["best_probability"] = best_outcome[1]
                else:
                    parsed["recommended_bet"] = parsed.get("outcomes", ["Yes"])[0]
                    parsed["best_probability"] = 50.0

                parsed["confidence"] = confidence
                parsed["volume_formatted"] = f"${volume:,.0f}"

                predictions.append(parsed)

        # Trier par volume (plus de liquidité = plus fiable)
        predictions.sort(key=lambda x: float(x.get("volume", 0) or 0), reverse=True)

        return predictions

    async def generate_best_combos(self, predictions: List[Dict[str, Any]], max_combos: int = 5) -> List[Dict[str, Any]]:
        """Génère les meilleurs combinés basés sur les marchés Polymarket"""
        # Filtrer les prédictions avec bonne confiance
        good_predictions = [
            p for p in predictions
            if p.get("confidence") in ["very_high", "high", "medium"]
        ]

        if len(good_predictions) < 2:
            good_predictions = predictions[:5]

        combos = []

        # Combo sécurisé (2 marchés à haute probabilité)
        safe_preds = sorted(
            good_predictions,
            key=lambda x: x.get("best_probability", 0),
            reverse=True
        )[:2]

        if len(safe_preds) >= 2:
            total_prob = 1.0
            for p in safe_preds:
                total_prob *= (p.get("best_probability", 50) / 100)

            combos.append({
                "id": "safe_1",
                "type": "safe",
                "description": "Combiné Sécurisé - 2 marchés haute probabilité",
                "matches": [
                    {
                        "question": p.get("question"),
                        "bet": p.get("recommended_bet"),
                        "probability": p.get("best_probability"),
                        "url": p.get("polymarket_url"),
                    }
                    for p in safe_preds
                ],
                "total_probability": round(total_prob * 100, 2),
                "risk_level": "safe",
            })

        # Combo modéré (3 marchés)
        if len(good_predictions) >= 3:
            moderate_preds = good_predictions[:3]
            total_prob = 1.0
            for p in moderate_preds:
                total_prob *= (p.get("best_probability", 50) / 100)

            combos.append({
                "id": "moderate_1",
                "type": "moderate",
                "description": "Combiné Équilibré - 3 marchés",
                "matches": [
                    {
                        "question": p.get("question"),
                        "bet": p.get("recommended_bet"),
                        "probability": p.get("best_probability"),
                        "url": p.get("polymarket_url"),
                    }
                    for p in moderate_preds
                ],
                "total_probability": round(total_prob * 100, 2),
                "risk_level": "moderate",
            })

        # Combo risqué (4-5 marchés)
        if len(predictions) >= 4:
            risky_preds = predictions[:5]
            total_prob = 1.0
            for p in risky_preds:
                total_prob *= (p.get("best_probability", 50) / 100)

            combos.append({
                "id": "risky_1",
                "type": "risky",
                "description": "Combiné Ambitieux - 5 marchés pour gros gains",
                "matches": [
                    {
                        "question": p.get("question"),
                        "bet": p.get("recommended_bet"),
                        "probability": p.get("best_probability"),
                        "url": p.get("polymarket_url"),
                    }
                    for p in risky_preds
                ],
                "total_probability": round(total_prob * 100, 2),
                "risk_level": "risky",
            })

        return combos[:max_combos]
