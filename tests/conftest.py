import os
import sys
import pytest
import pytest_asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("DATABASE_PATH", ":memory:")
os.environ.setdefault("DISCORD_TOKEN", "test_token")
os.environ.setdefault("INITIAL_CASH", "10000")

import config  # noqa: E402
from database import Database  # noqa: E402
from market import Market  # noqa: E402
from trading import TradingEngine  # noqa: E402
from portfolio import PortfolioSystem  # noqa: E402
from leaderboard import Leaderboard  # noqa: E402


@pytest_asyncio.fixture
async def db(tmp_path):
    path = str(tmp_path / "test.db")
    database = Database(path)
    await database.init()
    return database


@pytest_asyncio.fixture
async def market(db):
    m = Market(db)
    await db.upsert_stock("AAPL", 150.0, name="Apple Inc.", sector="Technology")
    await db.upsert_stock("MSFT", 300.0, name="Microsoft Corporation", sector="Technology")
    await db.upsert_stock("TSLA", 250.0, name="Tesla Inc.", sector="Automotive")
    return m


@pytest_asyncio.fixture
async def trading(db, market):
    return TradingEngine(db, market)


@pytest_asyncio.fixture
async def portfolio(db, market):
    return PortfolioSystem(db, market)


@pytest_asyncio.fixture
async def leaderboard(db, market, portfolio):
    return Leaderboard(db, portfolio)
