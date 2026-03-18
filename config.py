import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
DATABASE_PATH = os.getenv("DATABASE_PATH", "stocks.db")
INITIAL_CASH = float(os.getenv("INITIAL_CASH", "10000"))
DAILY_MIN_REWARD = int(os.getenv("DAILY_MIN_REWARD", "500"))
DAILY_MAX_REWARD = int(os.getenv("DAILY_MAX_REWARD", "2000"))
MARKET_UPDATE_INTERVAL = int(os.getenv("MARKET_UPDATE_INTERVAL", "300"))
LEADERBOARD_UPDATE_INTERVAL = int(os.getenv("LEADERBOARD_UPDATE_INTERVAL", "300"))
YFINANCE_CACHE_SECONDS = int(os.getenv("YFINANCE_CACHE_SECONDS", "120"))
MAX_HISTORY_RESULTS = int(os.getenv("MAX_HISTORY_RESULTS", "10"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))
COMMAND_COOLDOWN = float(os.getenv("COMMAND_COOLDOWN", "5"))
OPTION_PREMIUM_PCT = float(os.getenv("OPTION_PREMIUM_PCT", "0.05"))
SHORT_MARGIN_PCT = float(os.getenv("SHORT_MARGIN_PCT", "1.5"))
EVENT_PROBABILITY = float(os.getenv("EVENT_PROBABILITY", "0.08"))
DIVIDEND_PROBABILITY = float(os.getenv("DIVIDEND_PROBABILITY", "0.03"))
SPLIT_PROBABILITY = float(os.getenv("SPLIT_PROBABILITY", "0.01"))

# ── Viral gameplay settings ─────────────────────────────────────
TOURNAMENT_DEFAULT_CASH = float(os.getenv("TOURNAMENT_DEFAULT_CASH", "10000"))
TOURNAMENT_DEFAULT_DURATION_DAYS = int(os.getenv("TOURNAMENT_DEFAULT_DURATION_DAYS", "7"))
TOURNAMENT_REWARD_1ST = float(os.getenv("TOURNAMENT_REWARD_1ST", "50000"))
TOURNAMENT_REWARD_2ND = float(os.getenv("TOURNAMENT_REWARD_2ND", "25000"))
TOURNAMENT_REWARD_3RD = float(os.getenv("TOURNAMENT_REWARD_3RD", "10000"))
INSIDER_LEAK_COST = float(os.getenv("INSIDER_LEAK_COST", "500"))
INSIDER_ACCURACY_PCT = float(os.getenv("INSIDER_ACCURACY_PCT", "0.6"))
INSIDER_COOLDOWN_SECONDS = int(os.getenv("INSIDER_COOLDOWN_SECONDS", "3600"))
FUND_MAX_MEMBERS = int(os.getenv("FUND_MAX_MEMBERS", "10"))
FUND_MIN_CONTRIBUTION = float(os.getenv("FUND_MIN_CONTRIBUTION", "1000"))
MAX_LEVERAGE = float(os.getenv("MAX_LEVERAGE", "3.0"))
MARGIN_CALL_THRESHOLD = float(os.getenv("MARGIN_CALL_THRESHOLD", "0.25"))
MARGIN_CHECK_INTERVAL = int(os.getenv("MARGIN_CHECK_INTERVAL", "60"))
COPY_TRADE_MAX_PCT = float(os.getenv("COPY_TRADE_MAX_PCT", "0.10"))
MAX_COPY_FOLLOWERS = int(os.getenv("MAX_COPY_FOLLOWERS", "20"))
IPO_VOLATILITY_MULTIPLIER = float(os.getenv("IPO_VOLATILITY_MULTIPLIER", "2.0"))
PRESTIGE_NET_WORTH_REQ = float(os.getenv("PRESTIGE_NET_WORTH_REQ", "10000000"))
PRESTIGE_DAILY_BONUS = float(os.getenv("PRESTIGE_DAILY_BONUS", "0.10"))
MARKET_HOURS_ENABLED = os.getenv("MARKET_HOURS_ENABLED", "true").lower() == "true"
AFTER_HOURS_VOLATILITY = float(os.getenv("AFTER_HOURS_VOLATILITY", "1.5"))
PUMP_DUMP_PROBABILITY = float(os.getenv("PUMP_DUMP_PROBABILITY", "0.03"))

DEFAULT_STOCKS = [
    {"ticker": "AAPL", "name": "Apple Inc.", "sector": "Technology"},
    {"ticker": "MSFT", "name": "Microsoft Corporation", "sector": "Technology"},
    {"ticker": "GOOGL", "name": "Alphabet Inc.", "sector": "Technology"},
    {"ticker": "AMZN", "name": "Amazon.com Inc.", "sector": "Consumer"},
    {"ticker": "TSLA", "name": "Tesla Inc.", "sector": "Automotive"},
    {"ticker": "NVDA", "name": "NVIDIA Corporation", "sector": "Technology"},
    {"ticker": "META", "name": "Meta Platforms Inc.", "sector": "Technology"},
    {"ticker": "JPM", "name": "JPMorgan Chase & Co.", "sector": "Finance"},
    {"ticker": "V", "name": "Visa Inc.", "sector": "Finance"},
    {"ticker": "XOM", "name": "Exxon Mobil Corporation", "sector": "Energy"},
    {"ticker": "JNJ", "name": "Johnson & Johnson", "sector": "Healthcare"},
    {"ticker": "WMT", "name": "Walmart Inc.", "sector": "Consumer"},
    {"ticker": "DIS", "name": "The Walt Disney Company", "sector": "Entertainment"},
    {"ticker": "NFLX", "name": "Netflix Inc.", "sector": "Entertainment"},
    {"ticker": "AMD", "name": "Advanced Micro Devices", "sector": "Technology"},
]

ACHIEVEMENTS = {
    "first_trade": {"name": "First Trade", "description": "Complete your first trade", "icon": "🎯"},
    "10_trades": {"name": "Active Trader", "description": "Complete 10 trades", "icon": "📊"},
    "100_trades": {"name": "Trading Machine", "description": "Complete 100 trades", "icon": "🤖"},
    "millionaire": {"name": "Millionaire", "description": "Reach $1,000,000 net worth", "icon": "💰"},
    "10x_return": {"name": "10x Bagger", "description": "Get a 10x return on a stock", "icon": "🚀"},
    "diamond_hands": {"name": "Diamond Hands", "description": "Hold a stock for 30+ days", "icon": "💎"},
    "diverse": {"name": "Diversified", "description": "Own 5 different stocks", "icon": "🌐"},
    "short_master": {"name": "Short Master", "description": "Profit from a short sale", "icon": "📉"},
    "options_trader": {"name": "Options Trader", "description": "Buy your first option", "icon": "📋"},
    "daily_streak_7": {"name": "Weekly Regular", "description": "Claim daily 7 days in a row", "icon": "📅"},
    "penny_pincher": {"name": "Penny Pincher", "description": "Have less than $100 cash", "icon": "🪙"},
    "big_spender": {"name": "Big Spender", "description": "Make a single trade worth $50,000+", "icon": "💸"},
    "tournament_winner": {"name": "Champion", "description": "Win a trading tournament", "icon": "🏆"},
    "fund_founder": {"name": "Fund Founder", "description": "Create a hedge fund", "icon": "🏦"},
    "margin_master": {"name": "Margin Master", "description": "Profit on a margin trade", "icon": "⚡"},
    "prestige_1": {"name": "Prestige I", "description": "Prestige for the first time", "icon": "⭐"},
    "copy_leader": {"name": "Influencer", "description": "Have 5+ copy traders following you", "icon": "👥"},
    "ipo_early": {"name": "Early Bird", "description": "Buy shares in an IPO", "icon": "🐣"},
    "insider_win": {"name": "Insider Edge", "description": "Profit from an insider leak", "icon": "🕵️"},
}

MARKET_SESSIONS = [
    {"name": "Asia", "region": "Asia", "open_hour": 0, "close_hour": 6, "volatility": 1.1},
    {"name": "Europe", "region": "Europe", "open_hour": 7, "close_hour": 15, "volatility": 1.0},
    {"name": "US", "region": "US", "open_hour": 14, "close_hour": 21, "volatility": 1.0},
]

PRESTIGE_TITLES = {
    0: "",
    1: "Bronze Trader",
    2: "Silver Trader",
    3: "Gold Trader",
    4: "Platinum Trader",
    5: "Diamond Trader",
}
