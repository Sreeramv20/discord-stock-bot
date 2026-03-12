# Configuration file
import os

# Database path
DB_PATH = os.getenv("DB_PATH", "stock_trading.db")

# Bot token - should be set in environment variables for security
TOKEN = os.getenv("DISCORD_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Bot prefix
PREFIX = os.getenv("PREFIX", "!")

# Market update interval (seconds)
MARKET_UPDATE_INTERVAL = int(os.getenv("MARKET_UPDATE_INTERVAL", "30"))

# Leaderboard refresh interval (seconds)
LEADERBOARD_REFRESH_INTERVAL = int(os.getenv("LEADERBOARD_REFRESH_INTERVAL", "60"))

# AI Trader configuration
AI_TRADER_ENABLED = os.getenv("AI_TRADER_ENABLED", "false").lower() == "true"
AI_TRADER_UPDATE_INTERVAL = int(os.getenv("AI_TRADER_UPDATE_INTERVAL", "3600"))

# Competition configuration
COMPETITION_ENABLED = os.getenv("COMPETITION_ENABLED", "false").lower() == "true"
COMPETITION_DURATION = int(os.getenv("COMPETITION_DURATION", "604800"))  # 1 week in seconds

# Options trading configuration
OPTIONS_TRADING_ENABLED = os.getenv("OPTIONS_TRADING_ENABLED", "false").lower() == "true"

# Market events configuration
MARKET_EVENTS_ENABLED = os.getenv("MARKET_EVENTS_ENABLED", "false").lower() == "true"
EVENT_PROBABILITY = float(os.getenv("EVENT_PROBABILITY", "0.05"))
EVENT_DURATION = int(os.getenv("EVENT_DURATION", "3600"))  # 1 hour in seconds
