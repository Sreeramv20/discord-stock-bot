import logging
from datetime import datetime, timezone

import config

logger = logging.getLogger(__name__)


class MarketHoursService:
    def __init__(self):
        self.sessions = config.MARKET_SESSIONS

    def get_current_session(self) -> dict | None:
        if not config.MARKET_HOURS_ENABLED:
            return {"name": "Always Open", "region": "Global", "volatility": 1.0}

        hour = datetime.now(timezone.utc).hour
        active = []
        for s in self.sessions:
            if s["open_hour"] <= s["close_hour"]:
                if s["open_hour"] <= hour < s["close_hour"]:
                    active.append(s)
            else:
                if hour >= s["open_hour"] or hour < s["close_hour"]:
                    active.append(s)

        if active:
            return active[0]
        return None

    def get_volatility_multiplier(self) -> float:
        if not config.MARKET_HOURS_ENABLED:
            return 1.0

        session = self.get_current_session()
        if session:
            return session.get("volatility", 1.0)
        return config.AFTER_HOURS_VOLATILITY

    def get_all_sessions_status(self) -> list[dict]:
        hour = datetime.now(timezone.utc).hour
        statuses = []
        for s in self.sessions:
            if s["open_hour"] <= s["close_hour"]:
                is_open = s["open_hour"] <= hour < s["close_hour"]
            else:
                is_open = hour >= s["open_hour"] or hour < s["close_hour"]

            statuses.append({
                "name": s["name"],
                "region": s["region"],
                "hours": f"{s['open_hour']:02d}:00 - {s['close_hour']:02d}:00 UTC",
                "is_open": is_open,
                "volatility": s.get("volatility", 1.0),
            })

        return statuses

    def is_after_hours(self) -> bool:
        return self.get_current_session() is None and config.MARKET_HOURS_ENABLED
