"""
Ayarlar — Buraya kendi bilgilerinizi girin
"""
import os

# Telegram bot token (@BotFather'dan alın)
BOT_TOKEN = os.getenv("BOT_TOKEN", "BURAYA_BOT_TOKEN_YAZIN")

# Desteklenen havayolları
SUPPORTED_AIRLINES = [
    "Pegasus",
    "THY (Turkish Airlines)",
    "SunExpress",
    "AnadoluJet",
]

# Veritabanı dosyası
DB_PATH = "flights.db"
