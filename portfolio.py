import logging

import config
from database import Database
from market import Market

logger = logging.getLogger(__name__)


class PortfolioSystem:
    def __init__(self, db: Database, market: Market):
        self.db = db
        self.market = market

    async def get_portfolio(self, discord_id: int) -> list[dict]:
        await self.db.ensure_user(discord_id)
        holdings = await self.db.get_user_portfolio(discord_id)
        enriched = []
        for h in holdings:
            price = await self.market.get_price(h["ticker"]) or h["avg_purchase_price"]
            current_value = h["shares"] * price
            cost_basis = h["shares"] * h["avg_purchase_price"]
            profit_loss = current_value - cost_basis
            pct = (profit_loss / cost_basis * 100) if cost_basis else 0

            enriched.append({
                "ticker": h["ticker"],
                "shares": h["shares"],
                "avg_price": h["avg_purchase_price"],
                "current_price": price,
                "current_value": current_value,
                "cost_basis": cost_basis,
                "profit_loss": profit_loss,
                "profit_pct": pct,
                "acquired_at": h.get("acquired_at"),
            })
        return enriched

    async def get_portfolio_value(self, discord_id: int) -> float:
        portfolio = await self.get_portfolio(discord_id)
        return sum(p["current_value"] for p in portfolio)

    async def get_net_worth(self, discord_id: int) -> float:
        balance = await self.db.get_user_balance(discord_id)
        portfolio_value = await self.get_portfolio_value(discord_id)

        shorts = await self.db.get_user_shorts(discord_id)
        short_liability = 0.0
        for s in shorts:
            price = await self.market.get_price(s["ticker"]) or s["borrow_price"]
            short_liability += s["shares"] * price

        options = await self.db.get_user_options(discord_id)
        option_value = 0.0
        for o in options:
            if o["status"] != "active":
                continue
            price = await self.market.get_price(o["ticker"])
            if price is None:
                continue
            if o["option_type"] == "call":
                intrinsic = max(0, price - o["strike_price"]) * 100
            else:
                intrinsic = max(0, o["strike_price"] - price) * 100
            option_value += intrinsic

        margin_equity = 0.0
        async with self.db._connect() as conn:
            cur = await conn.execute(
                "SELECT ticker, shares, entry_price, borrowed FROM margin_positions "
                "WHERE user_id=? AND status='open'", (discord_id,),
            )
            for row in await cur.fetchall():
                mp_price = await self.market.get_price(row["ticker"]) or row["entry_price"]
                margin_equity += max(0, row["shares"] * mp_price - row["borrowed"])

        return balance + portfolio_value - short_liability + option_value + margin_equity

    async def get_profit(self, discord_id: int) -> float:
        net_worth = await self.get_net_worth(discord_id)
        return net_worth - config.INITIAL_CASH

    async def get_summary(self, discord_id: int) -> dict:
        balance = await self.db.get_user_balance(discord_id)
        portfolio = await self.get_portfolio(discord_id)
        portfolio_value = sum(p["current_value"] for p in portfolio)
        total_profit = sum(p["profit_loss"] for p in portfolio)
        net_worth = await self.get_net_worth(discord_id)

        return {
            "balance": balance,
            "portfolio_value": portfolio_value,
            "net_worth": net_worth,
            "total_profit": total_profit,
            "positions": len(portfolio),
            "holdings": portfolio,
        }
