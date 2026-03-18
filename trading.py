import logging
from datetime import datetime, timedelta, timezone

import config
from database import Database
from market import Market
from utils.validation import validate_ticker, validate_shares, validate_price, validate_expiry_days

logger = logging.getLogger(__name__)


class TradingEngine:
    def __init__(self, db: Database, market: Market):
        self.db = db
        self.market = market
        self._on_trade_callbacks: list = []

    def register_trade_callback(self, callback):
        self._on_trade_callbacks.append(callback)

    async def _fire_trade_callbacks(self, discord_id: int, ticker: str,
                                    trade_type: str, shares: int, price: float):
        for cb in self._on_trade_callbacks:
            try:
                await cb(discord_id, ticker, trade_type, shares, price)
            except Exception as e:
                logger.debug("Trade callback error: %s", e)

    # ── Buy / Sell ──────────────────────────────────────────────────

    async def buy_stock(self, discord_id: int, ticker: str, shares: int,
                        *, _from_copy: bool = False) -> dict:
        ticker = validate_ticker(ticker)
        shares = validate_shares(shares)
        await self.db.ensure_user(discord_id)

        price = await self.market.get_price(ticker)
        if price is None:
            raise ValueError(f"Stock `{ticker}` not found in the market.")

        result = await self.db.execute_buy(discord_id, ticker, shares, price)
        logger.info("BUY  user=%s ticker=%s shares=%d price=%.2f", discord_id, ticker, shares, price)

        if not _from_copy:
            await self._fire_trade_callbacks(discord_id, ticker, "buy", shares, price)

        return result

    async def sell_stock(self, discord_id: int, ticker: str, shares: int,
                         *, _from_copy: bool = False) -> dict:
        ticker = validate_ticker(ticker)
        shares = validate_shares(shares)
        await self.db.ensure_user(discord_id)

        price = await self.market.get_price(ticker)
        if price is None:
            raise ValueError(f"Stock `{ticker}` not found in the market.")

        result = await self.db.execute_sell(discord_id, ticker, shares, price)
        logger.info("SELL user=%s ticker=%s shares=%d price=%.2f profit=%.2f",
                     discord_id, ticker, shares, price, result.get("profit", 0))

        if not _from_copy:
            await self._fire_trade_callbacks(discord_id, ticker, "sell", shares, price)

        return result

    # ── Limit Orders ────────────────────────────────────────────────

    async def place_limit_order(self, discord_id: int, ticker: str,
                                order_type: str, target_price: float, shares: int) -> int:
        ticker = validate_ticker(ticker)
        shares = validate_shares(shares)
        target_price = validate_price(target_price)
        await self.db.ensure_user(discord_id)

        stock = await self.market.get_price(ticker)
        if stock is None:
            raise ValueError(f"Stock `{ticker}` not found in the market.")

        if order_type == "buy":
            balance = await self.db.get_user_balance(discord_id)
            needed = target_price * shares
            if balance < needed:
                raise ValueError(f"Insufficient funds for limit buy. Need ${needed:,.2f}")
        elif order_type == "sell":
            portfolio = await self.db.get_user_portfolio(discord_id)
            held = next((p for p in portfolio if p["ticker"] == ticker), None)
            if not held or held["shares"] < shares:
                raise ValueError(f"Insufficient holdings to place sell order for {ticker}")

        order_id = await self.db.add_limit_order(discord_id, ticker, order_type, target_price, shares)
        logger.info("LIMIT %s user=%s ticker=%s price=%.2f shares=%d id=%d",
                     order_type.upper(), discord_id, ticker, target_price, shares, order_id)
        return order_id

    async def cancel_limit_order(self, discord_id: int, order_id: int) -> bool:
        success = await self.db.cancel_limit_order(order_id, discord_id)
        if success:
            logger.info("CANCEL limit order id=%d user=%s", order_id, discord_id)
        return success

    async def check_limit_orders(self) -> list[dict]:
        filled = []
        pending = await self.db.get_pending_limit_orders()
        for order in pending:
            try:
                price = await self.market.get_price(order["ticker"])
                if price is None:
                    continue

                should_fill = False
                if order["order_type"] == "buy" and price <= order["target_price"]:
                    should_fill = True
                elif order["order_type"] == "sell" and price >= order["target_price"]:
                    should_fill = True

                if not should_fill:
                    continue

                try:
                    if order["order_type"] == "buy":
                        await self.db.execute_buy(
                            order["user_id"], order["ticker"],
                            order["shares"], price,
                        )
                    else:
                        await self.db.execute_sell(
                            order["user_id"], order["ticker"],
                            order["shares"], price,
                        )
                except ValueError:
                    await self.db.cancel_limit_order(order["id"], order["user_id"])
                    logger.info("Limit order %d cancelled: trade failed", order["id"])
                    continue

                await self.db.fill_limit_order(order["id"])
                filled.append({**order, "fill_price": price})
                logger.info("FILLED limit order id=%d user=%s ticker=%s at %.2f",
                            order["id"], order["user_id"], order["ticker"], price)
            except Exception as e:
                logger.warning("Failed to fill limit order %d: %s", order["id"], e)
        return filled

    # ── Short Selling ───────────────────────────────────────────────

    async def short_stock(self, discord_id: int, ticker: str, shares: int) -> dict:
        ticker = validate_ticker(ticker)
        shares = validate_shares(shares)
        await self.db.ensure_user(discord_id)

        price = await self.market.get_price(ticker)
        if price is None:
            raise ValueError(f"Stock `{ticker}` not found in the market.")

        result = await self.db.execute_short(discord_id, ticker, shares, price)
        logger.info("SHORT user=%s ticker=%s shares=%d price=%.2f", discord_id, ticker, shares, price)
        return result

    async def cover_short(self, discord_id: int, position_id: int) -> dict:
        pos = await self.db.get_short_position(position_id, discord_id)
        if not pos:
            raise ValueError("Short position not found or already closed.")

        price = await self.market.get_price(pos["ticker"])
        if price is None:
            raise ValueError(f"Cannot get current price for {pos['ticker']}")

        result = await self.db.execute_cover(discord_id, position_id, price)
        logger.info("COVER user=%s pos=%d ticker=%s profit=%.2f",
                     discord_id, position_id, pos["ticker"], result["profit"])
        return result

    # ── Options Trading ─────────────────────────────────────────────

    async def buy_option(self, discord_id: int, ticker: str, option_type: str,
                         strike: float, expiry_days: int) -> dict:
        ticker = validate_ticker(ticker)
        strike = validate_price(strike)
        expiry_days = validate_expiry_days(expiry_days)
        await self.db.ensure_user(discord_id)

        price = await self.market.get_price(ticker)
        if price is None:
            raise ValueError(f"Stock `{ticker}` not found in the market.")

        premium = round(price * config.OPTION_PREMIUM_PCT * (expiry_days / 30) * 100, 2)
        balance = await self.db.get_user_balance(discord_id)
        if balance < premium:
            raise ValueError(f"Insufficient funds for premium. Need ${premium:,.2f}")

        expiry = (datetime.now(timezone.utc) + timedelta(days=expiry_days)).isoformat()
        await self.db.increment_user_balance(discord_id, -premium)
        new_balance = balance - premium

        option_id = await self.db.add_option(
            discord_id, ticker, option_type, strike, premium, expiry
        )
        await self.db.add_transaction(discord_id, ticker, f"option_{option_type}", 100, premium / 100)

        logger.info("OPTION %s user=%s ticker=%s strike=%.2f premium=%.2f expiry=%dd",
                     option_type.upper(), discord_id, ticker, strike, premium, expiry_days)
        return {
            "option_id": option_id, "ticker": ticker, "type": option_type,
            "strike": strike, "premium": premium, "expiry_days": expiry_days,
            "new_balance": new_balance, "current_price": price,
        }

    async def process_expired_options(self) -> list[dict]:
        results = []
        options = await self.db.get_active_options()
        now = datetime.now(timezone.utc)

        for opt in options:
            try:
                expiry = datetime.fromisoformat(opt["expiry"])
                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=timezone.utc)
                if now < expiry:
                    continue

                price = await self.market.get_price(opt["ticker"])
                if price is None:
                    await self.db.update_option_status(opt["id"], "expired")
                    continue

                payout = 0.0
                if opt["option_type"] == "call" and price > opt["strike_price"]:
                    payout = (price - opt["strike_price"]) * 100
                elif opt["option_type"] == "put" and price < opt["strike_price"]:
                    payout = (opt["strike_price"] - price) * 100

                if payout > 0:
                    await self.db.increment_user_balance(opt["user_id"], payout)
                    await self.db.update_option_status(opt["id"], "exercised")
                    status = "exercised"
                else:
                    await self.db.update_option_status(opt["id"], "expired")
                    status = "expired"

                results.append({**opt, "status": status, "payout": payout, "final_price": price})
                logger.info("Option %d %s: payout=%.2f", opt["id"], status, payout)
            except Exception as e:
                logger.warning("Error processing option %d: %s", opt["id"], e)
        return results

    # ── User Stats ──────────────────────────────────────────────────

    async def get_user_stats(self, discord_id: int) -> dict:
        txns = await self.db.get_user_transactions(discord_id, limit=1000)
        total_buys = sum(1 for t in txns if t["type"] == "buy")
        total_sells = sum(1 for t in txns if t["type"] == "sell")
        buy_volume = sum(t["total"] for t in txns if t["type"] == "buy")
        sell_volume = sum(t["total"] for t in txns if t["type"] == "sell")
        net_pl = sell_volume - buy_volume

        shorts = await self.db.get_user_shorts(discord_id)
        options = await self.db.get_user_options(discord_id)
        limit_orders = await self.db.get_user_limit_orders(discord_id)
        pending_orders = [o for o in limit_orders if o["status"] == "pending"]

        return {
            "total_trades": total_buys + total_sells,
            "total_buys": total_buys,
            "total_sells": total_sells,
            "buy_volume": buy_volume,
            "sell_volume": sell_volume,
            "net_profit_loss": net_pl,
            "open_shorts": len(shorts),
            "active_options": len([o for o in options if o["status"] == "active"]),
            "pending_limit_orders": len(pending_orders),
        }
