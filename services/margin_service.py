import logging

import config
from database import Database
from market import Market

logger = logging.getLogger(__name__)


class MarginService:
    def __init__(self, db: Database, market: Market):
        self.db = db
        self.market = market

    async def open_margin_position(self, user_id: int, ticker: str,
                                   shares: int, leverage: float = 2.0) -> dict:
        if shares <= 0:
            raise ValueError("Shares must be a positive integer.")
        await self.db.ensure_user(user_id)
        if leverage < 1.5 or leverage > config.MAX_LEVERAGE:
            raise ValueError(f"Leverage must be between 1.5x and {config.MAX_LEVERAGE}x")

        price = await self.market.get_price(ticker)
        if price is None:
            raise ValueError(f"Stock `{ticker}` not found.")

        position_value = shares * price
        margin_used = position_value / leverage
        borrowed = position_value - margin_used
        liq_price = round(price * (1 - (1 - config.MARGIN_CALL_THRESHOLD) / leverage), 2)

        balance = await self.db.get_user_balance(user_id)
        if balance < margin_used:
            raise ValueError(
                f"Insufficient margin. Need ${margin_used:,.2f} but have ${balance:,.2f}"
            )

        existing = await self._count_open_positions(user_id)
        if existing >= 5:
            raise ValueError("Maximum 5 open margin positions allowed.")

        await self.db.increment_user_balance(user_id, -margin_used)

        async with self.db._connect() as db:
            cur = await db.execute(
                "INSERT INTO margin_positions "
                "(user_id, ticker, shares, entry_price, leverage, margin_used, "
                "borrowed, liquidation_price) VALUES (?,?,?,?,?,?,?,?)",
                (user_id, ticker, shares, price, leverage, margin_used,
                 borrowed, liq_price),
            )
            await db.commit()
            position_id = cur.lastrowid

        await self.db.add_transaction(user_id, ticker, "margin_buy", shares, price)

        logger.info("Margin opened: user=%s ticker=%s shares=%d leverage=%.1fx id=%d",
                     user_id, ticker, shares, leverage, position_id)
        return {
            "position_id": position_id, "ticker": ticker, "shares": shares,
            "entry_price": price, "leverage": leverage, "margin_used": margin_used,
            "borrowed": borrowed, "liquidation_price": liq_price,
            "position_value": position_value,
        }

    async def close_margin_position(self, user_id: int, position_id: int) -> dict:
        async with self.db._connect() as db:
            cur = await db.execute(
                "SELECT * FROM margin_positions WHERE id=? AND user_id=? AND status='open'",
                (position_id, user_id),
            )
            pos = await cur.fetchone()
            if not pos:
                raise ValueError("Margin position not found or already closed.")
            pos = dict(pos)

        price = await self.market.get_price(pos["ticker"])
        if price is None:
            raise ValueError(f"Cannot get price for {pos['ticker']}")

        current_value = pos["shares"] * price
        equity = current_value - pos["borrowed"]
        profit = equity - pos["margin_used"]

        payout = max(0, equity)
        await self.db.increment_user_balance(user_id, payout)

        async with self.db._connect() as db:
            await db.execute(
                "UPDATE margin_positions SET status='closed', closed_at=datetime('now') "
                "WHERE id=?", (position_id,),
            )
            await db.commit()

        await self.db.add_transaction(user_id, pos["ticker"], "margin_sell", pos["shares"], price)

        if profit > 0:
            await self.db.add_achievement(user_id, "margin_master")

        logger.info("Margin closed: id=%d user=%s profit=%.2f", position_id, user_id, profit)
        return {
            "position_id": position_id, "ticker": pos["ticker"],
            "shares": pos["shares"], "entry_price": pos["entry_price"],
            "close_price": price, "leverage": pos["leverage"],
            "profit": profit, "payout": payout,
        }

    async def check_liquidations(self) -> list[dict]:
        liquidated = []
        async with self.db._connect() as db:
            cur = await db.execute(
                "SELECT * FROM margin_positions WHERE status='open'"
            )
            positions = [dict(r) for r in await cur.fetchall()]

        for pos in positions:
            price = await self.market.get_price(pos["ticker"])
            if price is None:
                continue

            if price <= pos["liquidation_price"]:
                current_value = pos["shares"] * price
                equity = max(0, current_value - pos["borrowed"])
                loss = pos["margin_used"] - equity

                await self.db.increment_user_balance(pos["user_id"], equity)

                async with self.db._connect() as db:
                    await db.execute(
                        "UPDATE margin_positions SET status='liquidated', "
                        "closed_at=datetime('now') WHERE id=?", (pos["id"],),
                    )
                    await db.commit()

                await self.db.add_transaction(
                    pos["user_id"], pos["ticker"], "liquidation", pos["shares"], price,
                )

                liquidated.append({
                    "user_id": pos["user_id"], "position_id": pos["id"],
                    "ticker": pos["ticker"], "entry_price": pos["entry_price"],
                    "liq_price": price, "loss": loss, "equity_returned": equity,
                })
                logger.warning("LIQUIDATED: user=%s pos=%d ticker=%s loss=%.2f",
                               pos["user_id"], pos["id"], pos["ticker"], loss)

        return liquidated

    async def get_user_positions(self, user_id: int) -> list[dict]:
        async with self.db._connect() as db:
            cur = await db.execute(
                "SELECT * FROM margin_positions WHERE user_id=? AND status='open'",
                (user_id,),
            )
            positions = [dict(r) for r in await cur.fetchall()]

        for pos in positions:
            price = await self.market.get_price(pos["ticker"]) or pos["entry_price"]
            pos["current_price"] = price
            pos["current_value"] = pos["shares"] * price
            pos["equity"] = pos["current_value"] - pos["borrowed"]
            pos["profit"] = pos["equity"] - pos["margin_used"]
            pos["pnl_pct"] = (pos["profit"] / pos["margin_used"]) * 100 if pos["margin_used"] else 0

        return positions

    async def _count_open_positions(self, user_id: int) -> int:
        async with self.db._connect() as db:
            cur = await db.execute(
                "SELECT COUNT(*) as c FROM margin_positions WHERE user_id=? AND status='open'",
                (user_id,),
            )
            return (await cur.fetchone())["c"]
