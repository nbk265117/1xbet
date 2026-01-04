import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from typing import Optional, List, Dict, Any


class Database:
    """Service de base de données MongoDB pour stocker les prédictions et historiques"""

    def __init__(self):
        self.mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        self.db_name = os.getenv("MONGODB_DB", "1xbet_predictions")
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None

    async def connect(self):
        """Connexion à MongoDB"""
        try:
            self.client = AsyncIOMotorClient(self.mongo_url)
            self.db = self.client[self.db_name]
            # Test de connexion
            await self.client.admin.command('ping')
            print(f"Connecté à MongoDB: {self.db_name}")
            return True
        except Exception as e:
            print(f"Erreur connexion MongoDB: {e}")
            print("Utilisation du mode cache fichier (fallback)")
            return False

    async def disconnect(self):
        """Déconnexion de MongoDB"""
        if self.client:
            self.client.close()

    # ==================== Collections ====================

    @property
    def predictions(self):
        """Collection des prédictions"""
        return self.db["predictions"] if self.db else None

    @property
    def markets(self):
        """Collection des marchés Polymarket"""
        return self.db["markets"] if self.db else None

    @property
    def combos(self):
        """Collection des combinés"""
        return self.db["combos"] if self.db else None

    @property
    def history(self):
        """Collection de l'historique des résultats"""
        return self.db["history"] if self.db else None

    @property
    def user_bets(self):
        """Collection des paris de l'utilisateur"""
        return self.db["user_bets"] if self.db else None

    # ==================== Prédictions ====================

    async def save_prediction(self, prediction: Dict[str, Any]) -> bool:
        """Sauvegarde une prédiction"""
        if not self.predictions:
            return False

        prediction["created_at"] = datetime.utcnow()
        prediction["updated_at"] = datetime.utcnow()

        try:
            await self.predictions.update_one(
                {"market_id": prediction.get("id") or prediction.get("market_id")},
                {"$set": prediction},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Erreur sauvegarde prediction: {e}")
            return False

    async def get_predictions_by_date(self, date_str: str) -> List[Dict[str, Any]]:
        """Récupère les prédictions pour une date"""
        if not self.predictions:
            return []

        try:
            cursor = self.predictions.find({"date": date_str})
            return await cursor.to_list(length=100)
        except Exception as e:
            print(f"Erreur récupération predictions: {e}")
            return []

    async def get_all_predictions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Récupère toutes les prédictions récentes"""
        if not self.predictions:
            return []

        try:
            cursor = self.predictions.find().sort("created_at", -1).limit(limit)
            return await cursor.to_list(length=limit)
        except Exception as e:
            print(f"Erreur: {e}")
            return []

    # ==================== Marchés Polymarket ====================

    async def save_market(self, market: Dict[str, Any]) -> bool:
        """Sauvegarde un marché Polymarket"""
        if not self.markets:
            return False

        market["updated_at"] = datetime.utcnow()

        try:
            await self.markets.update_one(
                {"id": market.get("id")},
                {"$set": market},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Erreur sauvegarde market: {e}")
            return False

    async def save_markets_bulk(self, markets: List[Dict[str, Any]]) -> int:
        """Sauvegarde plusieurs marchés en bulk"""
        if not self.markets or not markets:
            return 0

        saved = 0
        for market in markets:
            if await self.save_market(market):
                saved += 1

        return saved

    async def get_football_markets(self) -> List[Dict[str, Any]]:
        """Récupère les marchés football"""
        if not self.markets:
            return []

        try:
            cursor = self.markets.find({
                "$or": [
                    {"tags": {"$in": ["football", "soccer", "sports"]}},
                    {"question": {"$regex": "football|soccer|premier league|champions", "$options": "i"}}
                ]
            }).sort("volume", -1)
            return await cursor.to_list(length=100)
        except Exception as e:
            print(f"Erreur: {e}")
            return []

    # ==================== Combinés ====================

    async def save_combo(self, combo: Dict[str, Any]) -> bool:
        """Sauvegarde un combiné"""
        if not self.combos:
            return False

        combo["created_at"] = datetime.utcnow()

        try:
            await self.combos.insert_one(combo)
            return True
        except Exception as e:
            print(f"Erreur: {e}")
            return False

    async def get_combos_by_date(self, date_str: str) -> List[Dict[str, Any]]:
        """Récupère les combinés d'une date"""
        if not self.combos:
            return []

        try:
            cursor = self.combos.find({"date": date_str}).sort("total_probability", -1)
            return await cursor.to_list(length=20)
        except Exception as e:
            print(f"Erreur: {e}")
            return []

    # ==================== Historique & Stats ====================

    async def save_result(self, market_id: str, result: str, was_correct: bool):
        """Sauvegarde le résultat d'un pari"""
        if not self.history:
            return False

        try:
            await self.history.insert_one({
                "market_id": market_id,
                "result": result,
                "was_correct": was_correct,
                "resolved_at": datetime.utcnow()
            })
            return True
        except Exception as e:
            print(f"Erreur: {e}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """Calcule les statistiques de performance"""
        if not self.history:
            return {"total": 0, "correct": 0, "accuracy": 0}

        try:
            total = await self.history.count_documents({})
            correct = await self.history.count_documents({"was_correct": True})
            accuracy = (correct / total * 100) if total > 0 else 0

            return {
                "total": total,
                "correct": correct,
                "accuracy": round(accuracy, 2)
            }
        except Exception as e:
            print(f"Erreur: {e}")
            return {"total": 0, "correct": 0, "accuracy": 0}

    # ==================== Paris utilisateur ====================

    async def save_user_bet(self, bet: Dict[str, Any]) -> bool:
        """Sauvegarde un pari de l'utilisateur"""
        if not self.user_bets:
            return False

        bet["created_at"] = datetime.utcnow()
        bet["status"] = "pending"

        try:
            await self.user_bets.insert_one(bet)
            return True
        except Exception as e:
            print(f"Erreur: {e}")
            return False

    async def get_user_bets(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Récupère les paris de l'utilisateur"""
        if not self.user_bets:
            return []

        try:
            query = {"status": status} if status else {}
            cursor = self.user_bets.find(query).sort("created_at", -1)
            return await cursor.to_list(length=100)
        except Exception as e:
            print(f"Erreur: {e}")
            return []


# Instance globale
db = Database()
