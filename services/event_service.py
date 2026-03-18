import logging
import random

import config
from database import Database

logger = logging.getLogger(__name__)

MARKET_EVENTS = [
    {
        "event_type": "pump_tech",
        "description": "🚨 PUMP ALERT — Tech stocks pumping hard!",
        "multiplier": 1.40,
        "duration": 300,
        "affected_tickers": ["AAPL", "MSFT", "GOOGL", "NVDA", "META", "AMD"],
        "is_pump": True,
    },
    {
        "event_type": "pump_ev",
        "description": "🚨 PUMP ALERT — EV stocks mooning!",
        "multiplier": 1.45,
        "duration": 300,
        "affected_tickers": ["TSLA"],
        "is_pump": True,
    },
    {
        "event_type": "dump_tech",
        "description": "💥 DUMP — Tech stocks crashing after pump!",
        "multiplier": 0.70,
        "duration": 300,
        "affected_tickers": ["AAPL", "MSFT", "GOOGL", "NVDA", "META", "AMD"],
    },
    {
        "event_type": "dump_ev",
        "description": "💥 DUMP — EV stocks tanking after pump!",
        "multiplier": 0.65,
        "duration": 300,
        "affected_tickers": ["TSLA"],
    },
    {
        "event_type": "global_crash",
        "description": "🌎 GLOBAL MARKET PANIC — All stocks dropping 25%!",
        "multiplier": 0.75,
        "duration": 600,
        "affected_tickers": [],
    },
    {
        "event_type": "sector_crash_tech",
        "description": "💀 SECTOR CRASH — Technology sector collapsing!",
        "multiplier": 0.70,
        "duration": 480,
        "affected_tickers": ["AAPL", "MSFT", "GOOGL", "NVDA", "META", "AMD"],
    },
    {
        "event_type": "sector_crash_finance",
        "description": "🏦 BANKING CRISIS — Finance sector in freefall!",
        "multiplier": 0.72,
        "duration": 480,
        "affected_tickers": ["JPM", "V"],
    },
    {
        "event_type": "tech_rally",
        "description": "Tech Rally! Technology stocks surging!",
        "multiplier": 1.10,
        "duration": 600,
        "affected_tickers": ["AAPL", "MSFT", "GOOGL", "NVDA", "META", "AMD"],
    },
    {
        "event_type": "market_panic",
        "description": "Market Panic! Broad selloff across all sectors!",
        "multiplier": 0.85,
        "duration": 480,
        "affected_tickers": [],
    },
    {
        "event_type": "ev_boom",
        "description": "EV Boom! Electric vehicle stocks skyrocketing!",
        "multiplier": 1.20,
        "duration": 600,
        "affected_tickers": ["TSLA"],
    },
    {
        "event_type": "ai_bubble",
        "description": "AI Bubble! AI-related stocks pumping!",
        "multiplier": 1.15,
        "duration": 720,
        "affected_tickers": ["NVDA", "MSFT", "GOOGL", "META", "AMD"],
    },
    {
        "event_type": "energy_crisis",
        "description": "Energy Crisis! Energy sector volatile!",
        "multiplier": 1.25,
        "duration": 540,
        "affected_tickers": ["XOM"],
    },
    {
        "event_type": "healthcare_boom",
        "description": "Healthcare Boom! Pharma stocks rising!",
        "multiplier": 1.12,
        "duration": 600,
        "affected_tickers": ["JNJ"],
    },
    {
        "event_type": "fed_rate_cut",
        "description": "Fed Rate Cut! Markets rallying on rate decision!",
        "multiplier": 1.08,
        "duration": 900,
        "affected_tickers": [],
    },
    {
        "event_type": "recession_fears",
        "description": "Recession Fears! Consumer stocks dropping!",
        "multiplier": 0.90,
        "duration": 600,
        "affected_tickers": ["AMZN", "WMT", "DIS"],
    },
    {
        "event_type": "streaming_wars",
        "description": "Streaming Wars! Entertainment stocks volatile!",
        "multiplier": 1.15,
        "duration": 480,
        "affected_tickers": ["NFLX", "DIS"],
    },
    {
        "event_type": "crypto_crash",
        "description": "Crypto Crash! Risk-off sentiment spreading to equities!",
        "multiplier": 0.92,
        "duration": 360,
        "affected_tickers": ["TSLA", "META"],
    },
]


class EventService:
    def __init__(self, db: Database):
        self.db = db

    async def maybe_trigger_event(self) -> dict | None:
        if random.random() > config.EVENT_PROBABILITY:
            return None

        active = await self.db.get_active_events()
        active_types = {e["event_type"] for e in active}

        available = [e for e in MARKET_EVENTS if e["event_type"] not in active_types]
        if not available:
            return None

        event = random.choice(available)
        event_id = await self.db.add_market_event(
            event["event_type"], event["description"],
            event["multiplier"], event["affected_tickers"],
            event["duration"],
        )
        logger.info("Market event triggered: %s (id=%d)", event["event_type"], event_id)
        return {**event, "id": event_id}

    async def maybe_trigger_pump_dump(self) -> dict | None:
        if random.random() > config.PUMP_DUMP_PROBABILITY:
            return None
        pump_events = [e for e in MARKET_EVENTS if e.get("is_pump")]
        if not pump_events:
            return None
        active = await self.db.get_active_events()
        active_types = {e["event_type"] for e in active}
        available = [e for e in pump_events if e["event_type"] not in active_types]
        if not available:
            return None
        event = random.choice(available)
        event_id = await self.db.add_market_event(
            event["event_type"], event["description"],
            event["multiplier"], event["affected_tickers"], event["duration"],
        )
        logger.info("PUMP triggered: %s (id=%d)", event["event_type"], event_id)
        return {**event, "id": event_id}

    async def trigger_dump_after_pump(self) -> list[dict]:
        import time
        dumps_triggered = []
        active = await self.db.get_active_events()
        active_types = {e["event_type"] for e in active}
        expired_pumps = []
        async with self.db._connect() as db:
            cur = await db.execute(
                "SELECT * FROM market_events WHERE event_type LIKE 'pump_%' "
                "AND expires_at <= ?", (time.time(),),
            )
            expired_pumps = [dict(r) for r in await cur.fetchall()]

        dump_map = {"pump_tech": "dump_tech", "pump_ev": "dump_ev"}
        for pump in expired_pumps:
            dump_type = dump_map.get(pump["event_type"])
            if dump_type and dump_type not in active_types:
                dump_event = next((e for e in MARKET_EVENTS if e["event_type"] == dump_type), None)
                if dump_event:
                    eid = await self.db.add_market_event(
                        dump_event["event_type"], dump_event["description"],
                        dump_event["multiplier"], dump_event["affected_tickers"],
                        dump_event["duration"],
                    )
                    dumps_triggered.append({**dump_event, "id": eid})
                    logger.info("DUMP auto-triggered: %s after %s", dump_type, pump["event_type"])
        return dumps_triggered

    async def cleanup_expired(self) -> int:
        dumps = await self.trigger_dump_after_pump()
        count = await self.db.expire_events()
        if count:
            logger.info("Expired %d market events", count)
        return count

    async def get_active_events(self) -> list[dict]:
        return await self.db.get_active_events()

    async def maybe_issue_dividend(self) -> dict | None:
        if random.random() > config.DIVIDEND_PROBABILITY:
            return None

        stocks = await self.db.get_all_stocks()
        if not stocks:
            return None

        stock = random.choice(stocks)
        amount = round(stock["price"] * random.uniform(0.001, 0.01), 4)
        payouts = await self.db.pay_dividends(stock["ticker"], amount)

        if payouts:
            logger.info("Dividend: %s pays $%.4f/share to %d holders",
                        stock["ticker"], amount, len(payouts))
            return {
                "ticker": stock["ticker"], "amount_per_share": amount,
                "holders": len(payouts), "total_paid": sum(p["payout"] for p in payouts),
                "payouts": payouts,
            }
        return None

    async def maybe_stock_split(self) -> dict | None:
        if random.random() > config.SPLIT_PROBABILITY:
            return None

        stocks = await self.db.get_all_stocks()
        eligible = [s for s in stocks if s["price"] > 200]
        if not eligible:
            return None

        stock = random.choice(eligible)
        ratio = random.choice([2, 3])
        await self.db.apply_stock_split(stock["ticker"], ratio)
        logger.info("Stock split: %s %d:1 (price %.2f -> %.2f)",
                     stock["ticker"], ratio, stock["price"], stock["price"] / ratio)
        return {
            "ticker": stock["ticker"], "ratio": ratio,
            "old_price": stock["price"], "new_price": stock["price"] / ratio,
        }
