import logging

import config
from database import Database
from portfolio import PortfolioSystem

logger = logging.getLogger(__name__)


class PrestigeService:
    def __init__(self, db: Database, portfolio: PortfolioSystem):
        self.db = db
        self.portfolio = portfolio

    async def can_prestige(self, user_id: int) -> tuple[bool, float]:
        net_worth = await self.portfolio.get_net_worth(user_id)
        return net_worth >= config.PRESTIGE_NET_WORTH_REQ, net_worth

    async def get_prestige_level(self, user_id: int) -> dict:
        async with self.db._connect() as db:
            cur = await db.execute(
                "SELECT * FROM prestige_levels WHERE user_id=?", (user_id,),
            )
            row = await cur.fetchone()
            if row:
                return dict(row)
        return {"user_id": user_id, "level": 0, "total_resets": 0,
                "daily_bonus_mult": 1.0, "title": ""}

    async def prestige(self, user_id: int) -> dict:
        can, net_worth = await self.can_prestige(user_id)
        if not can:
            raise ValueError(
                f"Need ${config.PRESTIGE_NET_WORTH_REQ:,.0f} net worth to prestige. "
                f"Current: ${net_worth:,.2f}"
            )

        current = await self.get_prestige_level(user_id)
        new_level = current["level"] + 1
        new_mult = 1.0 + (new_level * config.PRESTIGE_DAILY_BONUS)
        title = config.PRESTIGE_TITLES.get(
            min(new_level, max(config.PRESTIGE_TITLES.keys())),
            f"Prestige {new_level}",
        )

        portfolio = await self.db.get_user_portfolio(user_id)
        for h in portfolio:
            if h["shares"] > 0:
                await self.db.reduce_portfolio(user_id, h["ticker"], h["shares"])

        shorts = await self.db.get_user_shorts(user_id)
        for s in shorts:
            price = await self.portfolio.market.get_price(s["ticker"]) or s["borrow_price"]
            try:
                await self.db.execute_cover(user_id, s["id"], price)
            except Exception:
                await self.db.close_short_position(s["id"])

        margin_positions = []
        async with self.db._connect() as db:
            cur = await db.execute(
                "SELECT id FROM margin_positions WHERE user_id=? AND status='open'",
                (user_id,),
            )
            margin_positions = [dict(r) for r in await cur.fetchall()]
        for mp in margin_positions:
            async with self.db._connect() as db:
                await db.execute(
                    "UPDATE margin_positions SET status='closed', closed_at=datetime('now') WHERE id=?",
                    (mp["id"],),
                )
                await db.commit()

        await self.db.update_user_balance(user_id, config.INITIAL_CASH)

        async with self.db._connect() as db:
            await db.execute(
                "INSERT INTO prestige_levels (user_id, level, total_resets, "
                "daily_bonus_mult, title, last_prestige_at) "
                "VALUES (?, ?, ?, ?, ?, datetime('now')) "
                "ON CONFLICT(user_id) DO UPDATE SET "
                "level=excluded.level, total_resets=total_resets+1, "
                "daily_bonus_mult=excluded.daily_bonus_mult, "
                "title=excluded.title, last_prestige_at=excluded.last_prestige_at",
                (user_id, new_level, 1, new_mult, title),
            )
            await db.commit()

        if new_level == 1:
            await self.db.add_achievement(user_id, "prestige_1")

        logger.info("PRESTIGE: user=%s level=%d title=%s", user_id, new_level, title)
        return {
            "level": new_level, "title": title,
            "daily_bonus_mult": new_mult,
            "previous_net_worth": net_worth,
        }

    async def get_daily_multiplier(self, user_id: int) -> float:
        p = await self.get_prestige_level(user_id)
        return p.get("daily_bonus_mult", 1.0)
