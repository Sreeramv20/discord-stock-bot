import logging
import time

import config
from database import Database
from portfolio import PortfolioSystem

logger = logging.getLogger(__name__)


class Leaderboard:
    def __init__(self, db: Database, portfolio: PortfolioSystem):
        self.db = db
        self.portfolio = portfolio
        self._cache: list[dict] | None = None
        self._cache_ts: float = 0

    async def update_rankings(self):
        users = await self.db.get_all_users()
        entries = []
        for user in users:
            uid = user["discord_id"]
            try:
                net_worth = await self.portfolio.get_net_worth(uid)
                profit = net_worth - config.INITIAL_CASH
                entries.append({
                    "user_id": uid,
                    "username": user.get("username") or str(uid),
                    "net_worth": net_worth,
                    "profit": profit,
                })
            except Exception as e:
                logger.warning("Failed to calc net worth for %s: %s", uid, e)

        entries.sort(key=lambda x: x["net_worth"], reverse=True)

        for rank, entry in enumerate(entries, 1):
            entry["rank"] = rank
            await self.db.update_leaderboard_entry(
                entry["user_id"], entry["net_worth"], entry["profit"], rank,
            )

        self._cache = entries
        self._cache_ts = time.time()
        logger.info("Leaderboard updated: %d users ranked", len(entries))

    async def get_top(self, limit: int = 10) -> list[dict]:
        if self._cache and time.time() - self._cache_ts < config.LEADERBOARD_UPDATE_INTERVAL:
            return self._cache[:limit]

        data = await self.db.get_leaderboard(limit)
        if data:
            for entry in data:
                user = await self.db.get_user(entry["user_id"])
                entry["username"] = (user.get("username") if user else None) or str(entry["user_id"])
            return data

        return []

    async def get_rank(self, discord_id: int) -> dict | None:
        entry = await self.db.get_user_rank(discord_id)
        if entry:
            user = await self.db.get_user(discord_id)
            entry["username"] = (user.get("username") if user else None) or str(discord_id)
        return entry
