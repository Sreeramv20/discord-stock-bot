import logging
import random
from datetime import datetime, timedelta, timezone

import config
from database import Database

logger = logging.getLogger(__name__)

IPO_POOL = [
    {"ticker": "OAI", "name": "OpenAI Corp", "sector": "Technology", "price_range": (40, 100)},
    {"ticker": "SPC", "name": "SpaceCorp Industries", "sector": "Aerospace", "price_range": (20, 60)},
    {"ticker": "QBT", "name": "QuantumBit Technologies", "sector": "Technology", "price_range": (30, 80)},
    {"ticker": "GRN", "name": "GreenFuture Energy", "sector": "Energy", "price_range": (15, 45)},
    {"ticker": "BIO", "name": "BioGenesis Labs", "sector": "Healthcare", "price_range": (25, 70)},
    {"ticker": "RBT", "name": "RoboTech Automation", "sector": "Technology", "price_range": (35, 90)},
    {"ticker": "LUN", "name": "Lunar Mining Co.", "sector": "Mining", "price_range": (10, 40)},
    {"ticker": "CYB", "name": "CyberShield Security", "sector": "Technology", "price_range": (20, 55)},
    {"ticker": "AQU", "name": "AquaPure Systems", "sector": "Utilities", "price_range": (12, 35)},
    {"ticker": "NRO", "name": "NeuroLink Interfaces", "sector": "Healthcare", "price_range": (50, 120)},
    {"ticker": "SKY", "name": "SkyNet Logistics", "sector": "Transport", "price_range": (18, 50)},
    {"ticker": "FUS", "name": "FusionCore Power", "sector": "Energy", "price_range": (30, 75)},
]


class IPOService:
    def __init__(self, db: Database):
        self.db = db

    async def maybe_launch_ipo(self) -> dict | None:
        async with self.db._connect() as db:
            cur = await db.execute("SELECT ticker FROM ipos")
            existing = {r["ticker"] for r in await cur.fetchall()}

            cur2 = await db.execute("SELECT ticker FROM stocks")
            stock_tickers = {r["ticker"] for r in await cur2.fetchall()}

        available = [i for i in IPO_POOL
                     if i["ticker"] not in existing and i["ticker"] not in stock_tickers]
        if not available:
            return None

        ipo = random.choice(available)
        price = round(random.uniform(*ipo["price_range"]), 2)
        now = datetime.now(timezone.utc)
        opens = (now + timedelta(hours=1)).isoformat()
        trades = (now + timedelta(hours=3)).isoformat()

        async with self.db._connect() as db:
            cur = await db.execute(
                "INSERT INTO ipos (ticker, name, initial_price, sector, "
                "volatility_multiplier, opens_at, trades_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (ipo["ticker"], ipo["name"], price, ipo.get("sector"),
                 config.IPO_VOLATILITY_MULTIPLIER, opens, trades),
            )
            await db.commit()
            ipo_id = cur.lastrowid

        logger.info("IPO announced: %s (%s) at $%.2f", ipo["ticker"], ipo["name"], price)
        return {
            "id": ipo_id, "ticker": ipo["ticker"], "name": ipo["name"],
            "price": price, "sector": ipo.get("sector"),
            "opens_at": opens, "trades_at": trades,
        }

    async def process_ipo_phases(self) -> list[dict]:
        transitions = []
        now = datetime.now(timezone.utc).isoformat()

        async with self.db._connect() as db:
            cur = await db.execute(
                "SELECT * FROM ipos WHERE phase='announced' AND opens_at <= ?", (now,),
            )
            to_open = [dict(r) for r in await cur.fetchall()]
            for ipo in to_open:
                await db.execute("UPDATE ipos SET phase='open' WHERE id=?", (ipo["id"],))
                await self.db.upsert_stock(
                    ipo["ticker"], ipo["initial_price"],
                    name=ipo["name"], sector=ipo.get("sector"),
                )
                transitions.append({**ipo, "new_phase": "open"})
                logger.info("IPO %s is now OPEN for trading", ipo["ticker"])

            cur2 = await db.execute(
                "SELECT * FROM ipos WHERE phase='open' AND trades_at <= ?", (now,),
            )
            to_trade = [dict(r) for r in await cur2.fetchall()]
            for ipo in to_trade:
                await db.execute("UPDATE ipos SET phase='trading' WHERE id=?", (ipo["id"],))
                transitions.append({**ipo, "new_phase": "trading"})
                logger.info("IPO %s now in normal trading", ipo["ticker"])

            await db.commit()

        return transitions

    async def get_active_ipos(self) -> list[dict]:
        async with self.db._connect() as db:
            cur = await db.execute(
                "SELECT * FROM ipos WHERE phase IN ('announced','open') "
                "ORDER BY announced_at DESC"
            )
            return [dict(r) for r in await cur.fetchall()]

    async def get_all_ipos(self) -> list[dict]:
        async with self.db._connect() as db:
            cur = await db.execute("SELECT * FROM ipos ORDER BY announced_at DESC LIMIT 20")
            return [dict(r) for r in await cur.fetchall()]

    async def is_ipo_stock(self, ticker: str) -> bool:
        async with self.db._connect() as db:
            cur = await db.execute(
                "SELECT phase FROM ipos WHERE ticker=? AND phase='open'", (ticker,),
            )
            return await cur.fetchone() is not None
