import logging
from datetime import datetime, timedelta, timezone

import config
from database import Database

logger = logging.getLogger(__name__)


class AchievementService:
    def __init__(self, db: Database):
        self.db = db

    async def check_and_award(self, discord_id: int, *, net_worth: float | None = None) -> list[str]:
        awarded = []

        trade_count = await self.db.count_user_transactions(discord_id)
        portfolio = await self.db.get_user_portfolio(discord_id)
        shorts = await self.db.get_user_shorts(discord_id)
        options = await self.db.get_user_options(discord_id)
        balance = await self.db.get_user_balance(discord_id)

        checks = [
            ("first_trade", trade_count >= 1),
            ("10_trades", trade_count >= 10),
            ("100_trades", trade_count >= 100),
            ("diverse", len(portfolio) >= 5),
            ("penny_pincher", trade_count > 0 and balance < 100),
            ("options_trader", len(options) > 0),
        ]

        if net_worth is not None:
            checks.append(("millionaire", net_worth >= 1_000_000))

        for hold in portfolio:
            if hold.get("avg_purchase_price") and hold["avg_purchase_price"] > 0:
                from market import Market  # deferred to avoid circular
                stock = await self.db.get_stock(hold["ticker"])
                if stock:
                    current = stock["price"]
                    ratio = current / hold["avg_purchase_price"]
                    if ratio >= 10:
                        checks.append(("10x_return", True))

            if hold.get("acquired_at"):
                try:
                    acq = datetime.fromisoformat(hold["acquired_at"])
                    if acq.tzinfo is None:
                        acq = acq.replace(tzinfo=timezone.utc)
                    if datetime.now(timezone.utc) - acq >= timedelta(days=30):
                        checks.append(("diamond_hands", True))
                except (ValueError, TypeError):
                    pass

        txns = await self.db.get_user_transactions(discord_id, limit=1000)
        for t in txns:
            if t["type"] == "sell" and t["total"] >= 50_000:
                checks.append(("big_spender", True))
            if t["type"] == "buy" and t["total"] >= 50_000:
                checks.append(("big_spender", True))

        cover_txns = [t for t in txns if t["type"] == "cover"]
        if cover_txns:
            checks.append(("short_master", True))

        for ach_id, condition in checks:
            if condition and ach_id in config.ACHIEVEMENTS:
                if not await self.db.has_achievement(discord_id, ach_id):
                    if await self.db.add_achievement(discord_id, ach_id):
                        awarded.append(ach_id)
                        logger.info("Achievement awarded: %s -> user %s", ach_id, discord_id)

        return awarded

    async def get_achievements_display(self, discord_id: int) -> list[dict]:
        earned = await self.db.get_user_achievements(discord_id)
        result = []
        for a in earned:
            defn = config.ACHIEVEMENTS.get(a["achievement_id"], {})
            result.append({
                "id": a["achievement_id"],
                "name": defn.get("name", a["achievement_id"]),
                "description": defn.get("description", ""),
                "icon": defn.get("icon", "🏆"),
                "earned_at": a["earned_at"],
            })
        return result
