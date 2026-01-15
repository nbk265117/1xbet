"""
Service Météo pour les Prédictions Football
Utilise OpenWeatherMap API (Free Tier: 1000 calls/jour)

Impact de la météo sur les matchs:
- Pluie: -5% à -10% buts, +3% à +5% corners (jeu long)
- Vent fort (>10 m/s): -3% buts, -5% corners
- Froid extrême (<5°C): -3% buts
- Chaleur extrême (>35°C): -5% buts
- Neige: -8% buts, -2% corners
"""
import requests
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================

# Cache configuration
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")
WEATHER_CACHE_FILE = os.path.join(CACHE_DIR, "weather_cache.json")

# Impact de la météo sur les performances
WEATHER_IMPACTS = {
    "rain": {
        "goals": -0.05,      # -5% de buts
        "corners": 0.03,     # +3% corners (jeu long)
        "description": "Pluie légère"
    },
    "heavy_rain": {
        "goals": -0.10,      # -10% de buts
        "corners": 0.05,     # +5% corners
        "description": "Pluie forte"
    },
    "drizzle": {
        "goals": -0.03,      # -3% de buts
        "corners": 0.02,
        "description": "Bruine"
    },
    "thunderstorm": {
        "goals": -0.12,      # -12% de buts
        "corners": 0.05,
        "description": "Orage"
    },
    "snow": {
        "goals": -0.08,      # -8% de buts
        "corners": -0.02,
        "description": "Neige"
    },
    "wind_strong": {
        "goals": -0.03,      # -3% de buts
        "corners": -0.05,    # -5% corners (passes imprécises)
        "description": "Vent fort"
    },
    "extreme_cold": {
        "goals": -0.03,      # -3% de buts
        "corners": 0,
        "description": "Froid extrême (<5°C)"
    },
    "extreme_heat": {
        "goals": -0.05,      # -5% de buts (fatigue)
        "corners": 0,
        "description": "Chaleur extrême (>35°C)"
    },
    "fog": {
        "goals": -0.02,
        "corners": 0,
        "description": "Brouillard"
    },
    "clear": {
        "goals": 0,
        "corners": 0,
        "description": "Temps clair"
    }
}

# Stades connus avec coordonnées (fallback si geocoding échoue)
KNOWN_VENUES = {
    # Premier League
    "Old Trafford": (53.4631, -2.2913),
    "Anfield": (53.4308, -2.9608),
    "Emirates Stadium": (51.5549, -0.1084),
    "Stamford Bridge": (51.4817, -0.1910),
    "Etihad Stadium": (53.4831, -2.2004),
    "Tottenham Hotspur Stadium": (51.6043, -0.0664),
    "St. James' Park": (54.9756, -1.6217),
    "Villa Park": (52.5092, -1.8847),
    "London Stadium": (51.5387, -0.0166),
    "Goodison Park": (53.4387, -2.9663),
    # La Liga
    "Camp Nou": (41.3809, 2.1228),
    "Santiago Bernabéu": (40.4531, -3.6883),
    "Wanda Metropolitano": (40.4362, -3.5995),
    "Ramón Sánchez Pizjuán": (37.3840, -5.9706),
    "San Mamés": (43.2641, -2.9494),
    # Bundesliga
    "Allianz Arena": (48.2188, 11.6247),
    "Signal Iduna Park": (51.4926, 7.4518),
    "Veltins-Arena": (51.5536, 7.0678),
    "Volksparkstadion": (53.5872, 9.8986),
    "Mercedes-Benz Arena": (48.7924, 9.2320),
    # Serie A
    "San Siro": (45.4781, 9.1240),
    "Stadio Olimpico": (41.9341, 12.4547),
    "Allianz Stadium": (45.1096, 7.6411),
    "Stadio Diego Armando Maradona": (40.8280, 14.1931),
    "Gewiss Stadium": (45.7089, 9.6808),
    # Ligue 1
    "Parc des Princes": (48.8414, 2.2530),
    "Groupama Stadium": (45.7653, 4.9822),
    "Orange Vélodrome": (43.2699, 5.3958),
    "Allianz Riviera": (43.7050, 7.1926),
    "Roazhon Park": (48.1075, -1.7128),
}


@dataclass
class WeatherData:
    """Données météo pour un match"""
    venue: str
    city: str
    country: str
    date: datetime

    # Conditions météo
    temperature: float = 20.0           # Température en °C
    feels_like: float = 20.0            # Ressenti
    humidity: int = 50                  # Humidité %
    wind_speed: float = 5.0             # Vitesse vent m/s
    wind_gust: float = 0.0              # Rafales
    weather_main: str = "Clear"         # Type principal (Clear, Rain, Snow...)
    weather_description: str = ""       # Description détaillée
    precipitation_prob: float = 0.0     # Probabilité précipitation (0-1)
    clouds: int = 0                     # Couverture nuageuse %

    # Impacts calculés
    goals_impact: float = 0.0           # Multiplicateur buts (-0.12 à 0)
    corners_impact: float = 0.0         # Multiplicateur corners (-0.05 à 0.05)
    impact_description: str = ""        # Description de l'impact

    # Métadonnées
    is_cached: bool = False
    cache_age_hours: float = 0.0
    data_source: str = "api"            # "api", "cache", "default"
    latitude: float = 0.0
    longitude: float = 0.0


class WeatherService:
    """
    Service de récupération des données météo pour les matchs

    Utilise OpenWeatherMap API:
    - Free tier: 1000 calls/jour
    - Forecast: jusqu'à 5 jours
    - Current weather: temps réel
    """

    def __init__(self, api_key: str = None):
        """
        Args:
            api_key: Clé API OpenWeatherMap (optionnel, lue depuis env sinon)
        """
        self.api_key = api_key or os.getenv("OPENWEATHERMAP_API_KEY", "")
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.geocode_url = "https://api.openweathermap.org/geo/1.0"

        self._cache = self._load_cache()
        self._api_calls_today = 0
        self._max_calls_per_day = 950  # Marge de sécurité

        # TTL du cache
        self.cache_ttl = {
            "historical": 24 * 3600,    # 24h pour météo passée
            "forecast": 3 * 3600,       # 3h pour prévisions
        }

        # Créer dossier cache
        os.makedirs(CACHE_DIR, exist_ok=True)

    def _load_cache(self) -> Dict:
        """Charge le cache météo depuis le fichier"""
        try:
            if os.path.exists(WEATHER_CACHE_FILE):
                with open(WEATHER_CACHE_FILE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Erreur chargement cache météo: {e}")
        return {}

    def _save_cache(self):
        """Sauvegarde le cache météo"""
        try:
            with open(WEATHER_CACHE_FILE, 'w') as f:
                json.dump(self._cache, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Erreur sauvegarde cache météo: {e}")

    def _get_cache_key(self, location: str, date: datetime) -> str:
        """Génère une clé de cache unique"""
        date_str = date.strftime("%Y-%m-%d_%H")
        return f"{location.lower().replace(' ', '_')}_{date_str}"

    def _is_cache_valid(self, cache_key: str, is_forecast: bool) -> bool:
        """Vérifie si le cache est encore valide"""
        if cache_key not in self._cache:
            return False

        entry = self._cache[cache_key]
        timestamp = entry.get('timestamp', 0)
        ttl = self.cache_ttl['forecast'] if is_forecast else self.cache_ttl['historical']

        import time
        return (time.time() - timestamp) < ttl

    async def get_weather_for_match(self, venue: str, city: str,
                                     match_date: datetime,
                                     country: str = "") -> WeatherData:
        """
        Récupère les conditions météo pour un match

        Args:
            venue: Nom du stade
            city: Ville du match
            match_date: Date et heure du match
            country: Pays (aide au geocoding)

        Returns:
            WeatherData avec conditions et impacts calculés
        """
        # Créer objet de base
        weather = WeatherData(
            venue=venue,
            city=city,
            country=country,
            date=match_date
        )

        # Vérifier si API key disponible
        if not self.api_key:
            logger.warning("Pas de clé API OpenWeatherMap configurée")
            weather.data_source = "default"
            return weather

        # Déterminer la localisation
        location = venue if venue else city
        cache_key = self._get_cache_key(location, match_date)
        is_forecast = match_date > datetime.now()

        # Vérifier le cache
        if self._is_cache_valid(cache_key, is_forecast):
            cached = self._cache[cache_key]
            weather = self._parse_cached_weather(cached, venue, city, country, match_date)
            weather.is_cached = True
            import time
            weather.cache_age_hours = (time.time() - cached.get('timestamp', 0)) / 3600
            return weather

        # Vérifier limite API
        if self._api_calls_today >= self._max_calls_per_day:
            logger.warning("Limite journalière OpenWeatherMap atteinte")
            weather.data_source = "default"
            return weather

        # Obtenir coordonnées
        lat, lon = await self._get_coordinates(venue, city, country)
        if lat is None:
            logger.warning(f"Impossible de localiser: {venue}, {city}")
            weather.data_source = "default"
            return weather

        weather.latitude = lat
        weather.longitude = lon

        # Récupérer la météo
        if is_forecast:
            weather_data = await self._fetch_forecast(lat, lon, match_date)
        else:
            weather_data = await self._fetch_current(lat, lon)

        if weather_data:
            weather = self._parse_weather_response(weather_data, venue, city, country, match_date)
            weather = self._calculate_impacts(weather)
            weather.latitude = lat
            weather.longitude = lon

            # Mettre en cache
            import time
            self._cache[cache_key] = {
                'timestamp': time.time(),
                'data': weather_data,
                'lat': lat,
                'lon': lon
            }
            self._save_cache()
        else:
            weather.data_source = "default"

        return weather

    def get_weather_for_match_sync(self, venue: str, city: str,
                                    match_date: datetime,
                                    country: str = "") -> WeatherData:
        """
        Version synchrone (utilise requests directement)
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Si on est déjà dans une boucle async, utiliser le cache uniquement
                return self._get_cached_or_default(venue, city, match_date, country)
            return loop.run_until_complete(
                self.get_weather_for_match(venue, city, match_date, country)
            )
        except RuntimeError:
            # Pas de boucle, en créer une
            return asyncio.run(
                self.get_weather_for_match(venue, city, match_date, country)
            )

    def _get_cached_or_default(self, venue: str, city: str,
                                match_date: datetime, country: str) -> WeatherData:
        """Retourne les données en cache ou par défaut"""
        weather = WeatherData(venue=venue, city=city, country=country, date=match_date)

        location = venue if venue else city
        cache_key = self._get_cache_key(location, match_date)

        if cache_key in self._cache:
            cached = self._cache[cache_key]
            weather = self._parse_cached_weather(cached, venue, city, country, match_date)
            weather.is_cached = True

        weather.data_source = "cache" if weather.is_cached else "default"
        return weather

    async def _get_coordinates(self, venue: str, city: str,
                                country: str) -> Tuple[Optional[float], Optional[float]]:
        """Obtient les coordonnées GPS d'un lieu"""
        # Vérifier les stades connus
        if venue in KNOWN_VENUES:
            return KNOWN_VENUES[venue]

        # Geocoding via API
        try:
            query = f"{city},{country}" if country else city
            response = requests.get(
                f"{self.geocode_url}/direct",
                params={"q": query, "limit": 1, "appid": self.api_key},
                timeout=10
            )
            self._api_calls_today += 1

            if response.status_code == 200:
                data = response.json()
                if data:
                    return data[0]['lat'], data[0]['lon']
        except Exception as e:
            logger.error(f"Erreur geocoding: {e}")

        return None, None

    async def _fetch_forecast(self, lat: float, lon: float,
                               target_date: datetime) -> Optional[Dict]:
        """Récupère les prévisions météo (jusqu'à 5 jours)"""
        try:
            response = requests.get(
                f"{self.base_url}/forecast",
                params={
                    "lat": lat,
                    "lon": lon,
                    "appid": self.api_key,
                    "units": "metric"
                },
                timeout=15
            )
            self._api_calls_today += 1

            if response.status_code == 200:
                data = response.json()
                forecasts = data.get('list', [])
                target_ts = target_date.timestamp()

                # Trouver la prévision la plus proche
                closest = min(
                    forecasts,
                    key=lambda x: abs(x['dt'] - target_ts),
                    default=None
                )
                return closest
        except Exception as e:
            logger.error(f"Erreur forecast: {e}")

        return None

    async def _fetch_current(self, lat: float, lon: float) -> Optional[Dict]:
        """Récupère la météo actuelle"""
        try:
            response = requests.get(
                f"{self.base_url}/weather",
                params={
                    "lat": lat,
                    "lon": lon,
                    "appid": self.api_key,
                    "units": "metric"
                },
                timeout=15
            )
            self._api_calls_today += 1

            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Erreur current weather: {e}")

        return None

    def _parse_weather_response(self, data: Dict, venue: str, city: str,
                                 country: str, match_date: datetime) -> WeatherData:
        """Parse la réponse API en WeatherData"""
        main = data.get('main', {})
        wind = data.get('wind', {})
        weather_list = data.get('weather', [{}])
        weather_info = weather_list[0] if weather_list else {}
        clouds = data.get('clouds', {})

        return WeatherData(
            venue=venue,
            city=city,
            country=country,
            date=match_date,
            temperature=main.get('temp', 20),
            feels_like=main.get('feels_like', 20),
            humidity=main.get('humidity', 50),
            wind_speed=wind.get('speed', 5),
            wind_gust=wind.get('gust', 0),
            weather_main=weather_info.get('main', 'Clear'),
            weather_description=weather_info.get('description', ''),
            precipitation_prob=data.get('pop', 0),
            clouds=clouds.get('all', 0),
            data_source="api"
        )

    def _parse_cached_weather(self, cached: Dict, venue: str, city: str,
                               country: str, match_date: datetime) -> WeatherData:
        """Parse les données en cache"""
        data = cached.get('data', {})
        weather = self._parse_weather_response(data, venue, city, country, match_date)
        weather = self._calculate_impacts(weather)
        weather.latitude = cached.get('lat', 0)
        weather.longitude = cached.get('lon', 0)
        return weather

    def _calculate_impacts(self, weather: WeatherData) -> WeatherData:
        """
        Calcule l'impact de la météo sur les performances

        Accumule les impacts de plusieurs conditions si applicable
        """
        goals_impact = 0.0
        corners_impact = 0.0
        descriptions = []

        # Type de météo principal
        main = weather.weather_main.lower()
        desc = weather.weather_description.lower()

        # Pluie
        if main == 'rain':
            if 'heavy' in desc or 'shower' in desc:
                goals_impact += WEATHER_IMPACTS['heavy_rain']['goals']
                corners_impact += WEATHER_IMPACTS['heavy_rain']['corners']
                descriptions.append(WEATHER_IMPACTS['heavy_rain']['description'])
            else:
                goals_impact += WEATHER_IMPACTS['rain']['goals']
                corners_impact += WEATHER_IMPACTS['rain']['corners']
                descriptions.append(WEATHER_IMPACTS['rain']['description'])

        # Bruine
        elif main == 'drizzle':
            goals_impact += WEATHER_IMPACTS['drizzle']['goals']
            corners_impact += WEATHER_IMPACTS['drizzle']['corners']
            descriptions.append(WEATHER_IMPACTS['drizzle']['description'])

        # Orage
        elif main == 'thunderstorm':
            goals_impact += WEATHER_IMPACTS['thunderstorm']['goals']
            corners_impact += WEATHER_IMPACTS['thunderstorm']['corners']
            descriptions.append(WEATHER_IMPACTS['thunderstorm']['description'])

        # Neige
        elif main == 'snow':
            goals_impact += WEATHER_IMPACTS['snow']['goals']
            corners_impact += WEATHER_IMPACTS['snow']['corners']
            descriptions.append(WEATHER_IMPACTS['snow']['description'])

        # Brouillard
        elif main in ('fog', 'mist', 'haze'):
            goals_impact += WEATHER_IMPACTS['fog']['goals']
            descriptions.append(WEATHER_IMPACTS['fog']['description'])

        # Vent fort (>10 m/s = 36 km/h)
        if weather.wind_speed > 10:
            goals_impact += WEATHER_IMPACTS['wind_strong']['goals']
            corners_impact += WEATHER_IMPACTS['wind_strong']['corners']
            descriptions.append(f"Vent fort ({weather.wind_speed:.0f} m/s)")

        # Température extrême
        if weather.temperature < 5:
            goals_impact += WEATHER_IMPACTS['extreme_cold']['goals']
            descriptions.append(f"Froid ({weather.temperature:.0f}°C)")
        elif weather.temperature > 35:
            goals_impact += WEATHER_IMPACTS['extreme_heat']['goals']
            descriptions.append(f"Chaleur ({weather.temperature:.0f}°C)")

        # Aucun impact significatif
        if not descriptions:
            descriptions.append("Conditions normales")

        weather.goals_impact = max(-0.15, goals_impact)  # Plafond -15%
        weather.corners_impact = max(-0.10, min(0.10, corners_impact))
        weather.impact_description = ", ".join(descriptions)

        return weather

    def get_api_calls_remaining(self) -> int:
        """Retourne le nombre d'appels API restants aujourd'hui"""
        return max(0, self._max_calls_per_day - self._api_calls_today)

    def reset_daily_counter(self):
        """Remet à zéro le compteur journalier (à appeler à minuit)"""
        self._api_calls_today = 0


# ==================== INSTANCE GLOBALE ====================
weather_service: Optional[WeatherService] = None


def init_weather_service(api_key: str = None) -> WeatherService:
    """
    Initialise le service météo global

    Args:
        api_key: Clé API OpenWeatherMap

    Returns:
        Instance WeatherService
    """
    global weather_service
    weather_service = WeatherService(api_key)
    logger.info("[WEATHER] Service météo initialisé")
    return weather_service


def get_weather_service() -> Optional[WeatherService]:
    """Retourne l'instance globale du service météo"""
    return weather_service
