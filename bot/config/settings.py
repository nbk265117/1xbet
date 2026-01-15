"""
Configuration du bot de paris sportifs
"""
import os
from datetime import datetime

# API Football Configuration
FOOTBALL_API_KEY = "111a3d8d8abb91aacf250df4ea6f5116"
FOOTBALL_API_BASE_URL = "https://v3.football.api-sports.io"

# Telegram Configuration
TELEGRAM_BOT_TOKEN = "8208049358:AAGIcq-nGcqEqbGHrZ6T-uKsI_EjwZoYLSQ"
TELEGRAM_CHAT_ID = "@bel9lil"  # Canal Telegram @bel9lil

# Scheduler Configuration
EXECUTION_HOUR = 21  # 21h heure locale
TIMEZONE = "Europe/Paris"

# Ticket Configuration
MIN_TICKETS_PER_DAY = 3
MAX_TICKETS_PER_DAY = 6
MIN_MATCHES_PER_TICKET = 3
MAX_MATCHES_PER_TICKET = 9

# Confidence Levels
CONFIDENCE_HIGH = "ÉLEVÉ"
CONFIDENCE_MEDIUM = "MOYEN"
CONFIDENCE_LOW = "FAIBLE"

# OpenWeatherMap Configuration (Free tier: 1000 calls/day)
OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY", "")

# Output Configuration
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bot.log")
