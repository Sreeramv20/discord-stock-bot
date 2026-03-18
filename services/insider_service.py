import logging
import random
from datetime import datetime, timedelta, timezone

import config
from database import Database

logger = logging.getLogger(__name__)

LEAK_TEMPLATES = [
    {"ticker": "NVDA", "bullish": "NVDA earnings may beat expectations significantly",
     "bearish": "NVDA facing major supply chain disruptions"},
    {"ticker": "AAPL", "bullish": "Apple planning surprise product launch next week",
     "bearish": "iPhone sales reportedly declining in key markets"},
    {"ticker": "TSLA", "bullish": "Tesla securing massive new government contract",
     "bearish": "Tesla recall affecting millions of vehicles"},
    {"ticker": "MSFT", "bullish": "Microsoft cloud revenue doubling estimates",
     "bearish": "Microsoft facing antitrust investigation"},
    {"ticker": "AMZN", "bullish": "Amazon AWS landing unprecedented enterprise deal",
     "bearish": "Amazon warehouse workers staging nationwide strike"},
    {"ticker": "GOOGL", "bullish": "Google AI breakthrough driving ad revenue surge",
     "bearish": "Google search market share declining rapidly"},
    {"ticker": "META", "bullish": "Meta VR headset sales exceeding all projections",
     "bearish": "Meta facing massive user data breach"},
    {"ticker": "AMD", "bullish": "AMD winning major datacenter contracts from Intel",
     "bearish": "AMD chip defect found in latest processor line"},
]


class InsiderService:
    def __init__(self, db: Database):
        self.db = db

    async def generate_leaks(self, count: int = 3) -> list[dict]:
        generated = []
        templates = random.sample(LEAK_TEMPLATES, min(count, len(LEAK_TEMPLATES)))
        expires = (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat()

        for t in templates:
            is_bullish = random.random() < 0.5
            is_accurate = random.random() < config.INSIDER_ACCURACY_PCT
            leak_type = "bullish" if is_bullish else "bearish"
            magnitude = round(random.uniform(0.05, 0.20), 2)
            desc = t["bullish"] if is_bullish else t["bearish"]

            async with self.db._connect() as db:
                cur = await db.execute(
                    "INSERT INTO insider_leaks "
                    "(ticker, leak_type, is_accurate, magnitude, description, cost, expires_at) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (t["ticker"], leak_type, int(is_accurate), magnitude, desc,
                     config.INSIDER_LEAK_COST, expires),
                )
                await db.commit()
                generated.append({"id": cur.lastrowid, "ticker": t["ticker"],
                                  "description": desc, "cost": config.INSIDER_LEAK_COST})

        logger.info("Generated %d insider leaks", len(generated))
        return generated

    async def get_available_leaks(self) -> list[dict]:
        now = datetime.now(timezone.utc).isoformat()
        async with self.db._connect() as db:
            cur = await db.execute(
                "SELECT id, ticker, description, cost, expires_at FROM insider_leaks "
                "WHERE expires_at > ? ORDER BY created_at DESC LIMIT 10", (now,),
            )
            return [dict(r) for r in await cur.fetchall()]

    async def purchase_leak(self, user_id: int, leak_id: int) -> dict:
        async with self.db._connect() as db:
            cur = await db.execute("SELECT * FROM insider_leaks WHERE id=?", (leak_id,))
            leak = await cur.fetchone()
            if not leak:
                raise ValueError("Leak not found.")
            leak = dict(leak)

            now = datetime.now(timezone.utc).isoformat()
            if leak["expires_at"] < now:
                raise ValueError("This leak has expired.")

            dup = await db.execute(
                "SELECT 1 FROM leak_purchases WHERE user_id=? AND leak_id=?",
                (user_id, leak_id),
            )
            if await dup.fetchone():
                raise ValueError("You already purchased this leak.")

            recent = await db.execute(
                "SELECT COUNT(*) as cnt FROM leak_purchases WHERE user_id=? "
                "AND purchased_at > datetime('now', '-1 hour')", (user_id,),
            )
            cnt_row = await recent.fetchone()
            if cnt_row and cnt_row["cnt"] >= 3:
                raise ValueError("Cooldown active. Max 3 leak purchases per hour.")

        balance = await self.db.get_user_balance(user_id)
        if balance < leak["cost"]:
            raise ValueError(f"Insufficient funds. Need ${leak['cost']:,.2f}")

        await self.db.increment_user_balance(user_id, -leak["cost"])

        async with self.db._connect() as db:
            await db.execute(
                "INSERT INTO leak_purchases (user_id, leak_id) VALUES (?,?)",
                (user_id, leak_id),
            )
            await db.commit()

        accuracy_hint = "HIGH confidence" if leak["is_accurate"] else "UNVERIFIED"
        direction = "📈 Bullish" if leak["leak_type"] == "bullish" else "📉 Bearish"

        logger.info("User %s purchased leak %d (%s, accurate=%s)",
                     user_id, leak_id, leak["ticker"], leak["is_accurate"])
        return {
            "ticker": leak["ticker"],
            "description": leak["description"],
            "direction": direction,
            "confidence": accuracy_hint,
            "cost": leak["cost"],
            "is_accurate": bool(leak["is_accurate"]),
        }

    async def apply_leak_effects(self) -> list[dict]:
        applied = []
        now = datetime.now(timezone.utc)
        async with self.db._connect() as db:
            cur = await db.execute(
                "SELECT * FROM insider_leaks WHERE expires_at > ? AND is_accurate = 1",
                (now.isoformat(),),
            )
            leaks = [dict(r) for r in await cur.fetchall()]

        for leak in leaks:
            purchased = await self._has_purchases(leak["id"])
            if not purchased:
                continue
            mult = 1.0 + leak["magnitude"] if leak["leak_type"] == "bullish" else 1.0 - leak["magnitude"]
            stock = await self.db.get_stock(leak["ticker"])
            if stock:
                new_price = round(stock["price"] * mult, 2)
                await self.db.upsert_stock(leak["ticker"], new_price)
                applied.append({"ticker": leak["ticker"], "multiplier": mult})

        return applied

    async def _has_purchases(self, leak_id: int) -> bool:
        async with self.db._connect() as db:
            cur = await db.execute(
                "SELECT 1 FROM leak_purchases WHERE leak_id=? LIMIT 1", (leak_id,),
            )
            return await cur.fetchone() is not None
