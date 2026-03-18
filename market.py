import asyncio
import logging
import random
import time
from typing import Optional

import yfinance as yf

import config
from database import Database

logger = logging.getLogger(__name__)


class Market:
    def __init__(self, db: Database):
        self.db = db
        self._price_cache: dict[str, dict] = {}
        self._info_cache: dict[str, dict] = {}

    # ── Price Fetching ──────────────────────────────────────────────

    async def get_price(self, ticker: str) -> Optional[float]:
        cached = self._price_cache.get(ticker)
        if cached and time.time() - cached["ts"] < config.YFINANCE_CACHE_SECONDS:
            return cached["price"]

        stock = await self.db.get_stock(ticker)
        if stock:
            self._price_cache[ticker] = {"price": stock["price"], "ts": time.time()}
            return stock["price"]
        return None

    async def get_stock_info(self, ticker: str) -> Optional[dict]:
        cached = self._info_cache.get(ticker)
        if cached and time.time() - cached["ts"] < config.YFINANCE_CACHE_SECONDS:
            return cached["data"]

        stock = await self.db.get_stock(ticker)
        if stock:
            data = dict(stock)
            change = data["price"] - (data.get("previous_price") or data["price"])
            prev = data.get("previous_price") or data["price"]
            data["change"] = change
            data["percent_change"] = (change / prev * 100) if prev else 0
            self._info_cache[ticker] = {"data": data, "ts": time.time()}
            return data
        return None

    async def get_all_stocks(self) -> list[dict]:
        stocks = await self.db.get_all_stocks()
        result = []
        for s in stocks:
            s = dict(s)
            prev = s.get("previous_price") or s["price"]
            s["change"] = s["price"] - prev
            s["percent_change"] = (s["change"] / prev * 100) if prev else 0
            result.append(s)
        return result

    # ── yfinance Integration ────────────────────────────────────────

    async def fetch_yfinance_price(self, ticker: str) -> Optional[dict]:
        try:
            loop = asyncio.get_running_loop()
            data = await loop.run_in_executor(None, self._yf_fetch_sync, ticker)
            return data
        except Exception as e:
            logger.warning("yfinance fetch failed for %s: %s", ticker, e)
            return None

    def _yf_fetch_sync(self, ticker: str) -> Optional[dict]:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            price = info.get("currentPrice") or info.get("regularMarketPrice")
            if not price:
                hist = stock.history(period="1d")
                if not hist.empty:
                    price = float(hist["Close"].iloc[-1])
            if not price:
                return None
            return {
                "ticker": ticker,
                "name": info.get("longName") or info.get("shortName") or ticker,
                "price": float(price),
                "previous_close": info.get("previousClose"),
                "volume": info.get("volume", 0),
                "sector": info.get("sector"),
            }
        except Exception:
            return None

    # ── Price Update Cycle ──────────────────────────────────────────

    async def update_all_prices(self):
        stocks = await self.db.get_all_stocks()
        for stock in stocks:
            try:
                await self._update_single_price(stock["ticker"])
            except Exception as e:
                logger.warning("Failed to update price for %s: %s", stock["ticker"], e)

    async def _update_single_price(self, ticker: str):
        data = await self.fetch_yfinance_price(ticker)
        if data and data.get("price"):
            multiplier = await self.get_event_multiplier(ticker)
            adjusted = data["price"] * multiplier
            await self.db.upsert_stock(
                ticker, adjusted,
                name=data.get("name"),
                volume=data.get("volume", 0),
                sector=data.get("sector"),
            )
            self._price_cache[ticker] = {"price": adjusted, "ts": time.time()}
            self._info_cache.pop(ticker, None)
            logger.debug("Updated %s: $%.2f (mult=%.2f)", ticker, adjusted, multiplier)
        else:
            existing = await self.db.get_stock(ticker)
            if existing:
                fluctuation = random.uniform(-0.02, 0.02)
                multiplier = await self.get_event_multiplier(ticker)
                new_price = max(0.01, existing["price"] * (1 + fluctuation) * multiplier)
                await self.db.upsert_stock(ticker, round(new_price, 2))
                self._price_cache[ticker] = {"price": new_price, "ts": time.time()}
                self._info_cache.pop(ticker, None)

    async def get_event_multiplier(self, ticker: str) -> float:
        events = await self.db.get_active_events()
        multiplier = 1.0
        for event in events:
            affected = event.get("affected_tickers", [])
            if not affected or ticker in affected:
                multiplier *= event["multiplier"]
        return multiplier

    # ── Initialization ──────────────────────────────────────────────

    async def initialize_default_stocks(self):
        existing = await self.db.get_all_stocks()
        existing_tickers = {s["ticker"] for s in existing}

        for stock_def in config.DEFAULT_STOCKS:
            if stock_def["ticker"] not in existing_tickers:
                data = await self.fetch_yfinance_price(stock_def["ticker"])
                price = data["price"] if data else random.uniform(50, 500)
                name = (data["name"] if data else stock_def["name"])
                await self.db.upsert_stock(
                    stock_def["ticker"], round(price, 2),
                    name=name,
                    sector=stock_def.get("sector"),
                )
                logger.info("Initialized stock %s at $%.2f", stock_def["ticker"], price)

        logger.info("Default stocks initialized (%d total)", len(config.DEFAULT_STOCKS))

    # ── Market News / Summaries ─────────────────────────────────────

    async def get_market_summary(self) -> dict:
        stocks = await self.get_all_stocks()
        if not stocks:
            return {"winners": [], "losers": [], "events": []}

        sorted_by_change = sorted(stocks, key=lambda s: s.get("percent_change", 0), reverse=True)
        winners = sorted_by_change[:3]
        losers = sorted_by_change[-3:]
        events = await self.db.get_active_events()

        return {"winners": winners, "losers": losers, "events": events, "total_stocks": len(stocks)}
