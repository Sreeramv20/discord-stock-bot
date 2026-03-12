# Configuration file
import os

# Bot token - should be set in environment variables for security
TOKEN = os.getenv("DISCORD_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Database path
DATABASE_PATH = "stock_trading.db"

# Bot prefix
PREFIX = "!"

# Market update interval (seconds)
MARKET_UPDATE_INTERVAL = 30

# Leaderboard refresh interval (seconds)
LEADERBOARD_REFRESH_INTERVAL = 60
