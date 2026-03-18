import logging
from datetime import datetime, timedelta, timezone

import config
from database import Database
from market import Market

logger = logging.getLogger(__name__)


class TournamentService:
    def __init__(self, db: Database, market: Market):
        self.db = db
        self.market = market

    async def create_tournament(self, name: str, duration_days: int | None = None,
                                start_cash: float | None = None,
                                created_by: int | None = None) -> dict:
        duration_days = duration_days or config.TOURNAMENT_DEFAULT_DURATION_DAYS
        start_cash = start_cash or config.TOURNAMENT_DEFAULT_CASH
        start_time = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        end_time = (datetime.now(timezone.utc) + timedelta(days=duration_days, hours=1)).isoformat()

        async with self.db._connect() as db:
            cur = await db.execute(
                "INSERT INTO tournaments (name, start_cash, start_time, end_time, "
                "reward_1st, reward_2nd, reward_3rd, created_by) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (name, start_cash, start_time, end_time,
                 config.TOURNAMENT_REWARD_1ST, config.TOURNAMENT_REWARD_2ND,
                 config.TOURNAMENT_REWARD_3RD, created_by),
            )
            await db.commit()
            tid = cur.lastrowid

        logger.info("Tournament created: %s (id=%d, days=%d)", name, tid, duration_days)
        return {"id": tid, "name": name, "start_cash": start_cash,
                "duration_days": duration_days, "start_time": start_time, "end_time": end_time}

    async def join_tournament(self, tournament_id: int, user_id: int) -> dict:
        t = await self._get_tournament(tournament_id)
        if not t:
            raise ValueError("Tournament not found.")
        if t["status"] == "ended":
            raise ValueError("Tournament has already ended.")
        if t["status"] == "active":
            now = datetime.now(timezone.utc)
            start = datetime.fromisoformat(t["start_time"])
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            if now > start + timedelta(minutes=30):
                raise ValueError("Tournament already started. Late registration closed.")

        async with self.db._connect() as db:
            cur = await db.execute(
                "SELECT 1 FROM tournament_participants WHERE tournament_id=? AND user_id=?",
                (tournament_id, user_id),
            )
            if await cur.fetchone():
                raise ValueError("You have already joined this tournament.")

            await db.execute(
                "INSERT INTO tournament_participants (tournament_id, user_id, cash_balance) "
                "VALUES (?, ?, ?)",
                (tournament_id, user_id, t["start_cash"]),
            )
            await db.commit()

        logger.info("User %s joined tournament %d", user_id, tournament_id)
        return {"tournament_id": tournament_id, "start_cash": t["start_cash"]}

    async def tournament_buy(self, tournament_id: int, user_id: int,
                             ticker: str, shares: int) -> dict:
        if shares <= 0:
            raise ValueError("Shares must be a positive integer.")
        t = await self._get_tournament(tournament_id)
        if not t or t["status"] != "active":
            raise ValueError("Tournament is not active.")

        price = await self.market.get_price(ticker)
        if price is None:
            raise ValueError(f"Stock `{ticker}` not found.")

        total_cost = shares * price
        async with self.db.transaction() as db:
            cur = await db.execute(
                "SELECT cash_balance FROM tournament_participants "
                "WHERE tournament_id=? AND user_id=?",
                (tournament_id, user_id),
            )
            row = await cur.fetchone()
            if not row:
                raise ValueError("You are not in this tournament.")
            if row["cash_balance"] < total_cost:
                raise ValueError(f"Insufficient tournament funds. Have ${row['cash_balance']:,.2f}")

            new_bal = row["cash_balance"] - total_cost
            await db.execute(
                "UPDATE tournament_participants SET cash_balance=? "
                "WHERE tournament_id=? AND user_id=?",
                (new_bal, tournament_id, user_id),
            )

            cur2 = await db.execute(
                "SELECT shares, avg_price FROM tournament_portfolios "
                "WHERE tournament_id=? AND user_id=? AND ticker=?",
                (tournament_id, user_id, ticker),
            )
            existing = await cur2.fetchone()
            if existing:
                old_s, old_p = existing["shares"], existing["avg_price"]
                new_s = old_s + shares
                new_p = ((old_s * old_p) + (shares * price)) / new_s
                await db.execute(
                    "UPDATE tournament_portfolios SET shares=?, avg_price=? "
                    "WHERE tournament_id=? AND user_id=? AND ticker=?",
                    (new_s, new_p, tournament_id, user_id, ticker),
                )
            else:
                await db.execute(
                    "INSERT INTO tournament_portfolios VALUES (?,?,?,?,?)",
                    (tournament_id, user_id, ticker, shares, price),
                )

            await db.execute(
                "INSERT INTO tournament_trades (tournament_id,user_id,ticker,type,shares,price,total) "
                "VALUES (?,?,?,?,?,?,?)",
                (tournament_id, user_id, ticker, "buy", shares, price, total_cost),
            )

        return {"ticker": ticker, "shares": shares, "price": price,
                "total": total_cost, "new_balance": new_bal}

    async def tournament_sell(self, tournament_id: int, user_id: int,
                              ticker: str, shares: int) -> dict:
        if shares <= 0:
            raise ValueError("Shares must be a positive integer.")
        t = await self._get_tournament(tournament_id)
        if not t or t["status"] != "active":
            raise ValueError("Tournament is not active.")

        price = await self.market.get_price(ticker)
        if price is None:
            raise ValueError(f"Stock `{ticker}` not found.")

        total_value = shares * price
        async with self.db.transaction() as db:
            cur = await db.execute(
                "SELECT shares FROM tournament_portfolios "
                "WHERE tournament_id=? AND user_id=? AND ticker=?",
                (tournament_id, user_id, ticker),
            )
            row = await cur.fetchone()
            if not row or row["shares"] < shares:
                raise ValueError("Insufficient tournament holdings.")

            remaining = row["shares"] - shares
            if remaining <= 0:
                await db.execute(
                    "DELETE FROM tournament_portfolios "
                    "WHERE tournament_id=? AND user_id=? AND ticker=?",
                    (tournament_id, user_id, ticker),
                )
            else:
                await db.execute(
                    "UPDATE tournament_portfolios SET shares=? "
                    "WHERE tournament_id=? AND user_id=? AND ticker=?",
                    (remaining, tournament_id, user_id, ticker),
                )

            await db.execute(
                "UPDATE tournament_participants SET cash_balance=cash_balance+? "
                "WHERE tournament_id=? AND user_id=?",
                (total_value, tournament_id, user_id),
            )

            await db.execute(
                "INSERT INTO tournament_trades (tournament_id,user_id,ticker,type,shares,price,total) "
                "VALUES (?,?,?,?,?,?,?)",
                (tournament_id, user_id, ticker, "sell", shares, price, total_value),
            )

        return {"ticker": ticker, "shares": shares, "price": price, "total": total_value}

    async def start_pending_tournaments(self) -> list[dict]:
        started = []
        now = datetime.now(timezone.utc).isoformat()
        async with self.db._connect() as db:
            cur = await db.execute(
                "SELECT * FROM tournaments WHERE status='pending' AND start_time<=?", (now,)
            )
            pending = [dict(r) for r in await cur.fetchall()]
            for t in pending:
                await db.execute(
                    "UPDATE tournaments SET status='active' WHERE id=?", (t["id"],)
                )
                await db.commit()
                started.append(t)
                logger.info("Tournament %d started: %s", t["id"], t["name"])
        return started

    async def end_expired_tournaments(self) -> list[dict]:
        ended = []
        now = datetime.now(timezone.utc).isoformat()
        async with self.db._connect() as db:
            cur = await db.execute(
                "SELECT * FROM tournaments WHERE status='active' AND end_time<=?", (now,)
            )
            active = [dict(r) for r in await cur.fetchall()]

        for t in active:
            results = await self._calculate_results(t["id"], t["start_cash"])
            await self._award_prizes(t["id"], results, t)

            async with self.db._connect() as db:
                await db.execute(
                    "UPDATE tournaments SET status='ended' WHERE id=?", (t["id"],)
                )
                await db.commit()
            ended.append({**t, "results": results})
            logger.info("Tournament %d ended: %s", t["id"], t["name"])
        return ended

    async def _calculate_results(self, tournament_id: int, start_cash: float) -> list[dict]:
        async with self.db._connect() as db:
            cur = await db.execute(
                "SELECT user_id, cash_balance FROM tournament_participants "
                "WHERE tournament_id=?", (tournament_id,),
            )
            participants = [dict(r) for r in await cur.fetchall()]

        results = []
        for p in participants:
            cur2_data = []
            async with self.db._connect() as db:
                cur2 = await db.execute(
                    "SELECT ticker, shares FROM tournament_portfolios "
                    "WHERE tournament_id=? AND user_id=?",
                    (tournament_id, p["user_id"]),
                )
                cur2_data = [dict(r) for r in await cur2.fetchall()]

            portfolio_value = 0.0
            for holding in cur2_data:
                price = await self.market.get_price(holding["ticker"]) or 0
                portfolio_value += holding["shares"] * price

            net_worth = p["cash_balance"] + portfolio_value
            pct_return = ((net_worth - start_cash) / start_cash) * 100
            results.append({"user_id": p["user_id"], "net_worth": net_worth,
                            "pct_return": pct_return})

        results.sort(key=lambda x: x["pct_return"], reverse=True)
        for rank, r in enumerate(results, 1):
            r["rank"] = rank
            async with self.db._connect() as db:
                await db.execute(
                    "UPDATE tournament_participants SET final_return=?, rank=? "
                    "WHERE tournament_id=? AND user_id=?",
                    (r["pct_return"], rank, tournament_id, r["user_id"]),
                )
                await db.commit()
        return results

    async def _award_prizes(self, tournament_id: int, results: list[dict], tournament: dict):
        rewards = {1: tournament["reward_1st"], 2: tournament["reward_2nd"],
                   3: tournament["reward_3rd"]}
        for r in results[:3]:
            prize = rewards.get(r["rank"], 0)
            if prize > 0:
                balance = await self.db.get_user_balance(r["user_id"])
                await self.db.update_user_balance(r["user_id"], balance + prize)
                if r["rank"] == 1:
                    await self.db.add_achievement(r["user_id"], "tournament_winner")

    async def get_tournament_leaderboard(self, tournament_id: int) -> list[dict]:
        t = await self._get_tournament(tournament_id)
        if not t:
            raise ValueError("Tournament not found.")

        async with self.db._connect() as db:
            cur = await db.execute(
                "SELECT user_id, cash_balance FROM tournament_participants "
                "WHERE tournament_id=?", (tournament_id,),
            )
            participants = [dict(r) for r in await cur.fetchall()]

        entries = []
        for p in participants:
            portfolio_value = 0.0
            async with self.db._connect() as db:
                cur = await db.execute(
                    "SELECT ticker, shares FROM tournament_portfolios "
                    "WHERE tournament_id=? AND user_id=?",
                    (tournament_id, p["user_id"]),
                )
                for row in await cur.fetchall():
                    price = await self.market.get_price(row["ticker"]) or 0
                    portfolio_value += row["shares"] * price

            nw = p["cash_balance"] + portfolio_value
            pct = ((nw - t["start_cash"]) / t["start_cash"]) * 100
            entries.append({"user_id": p["user_id"], "net_worth": nw, "pct_return": pct})

        entries.sort(key=lambda x: x["pct_return"], reverse=True)
        for rank, e in enumerate(entries, 1):
            e["rank"] = rank
        return entries

    async def get_active_tournaments(self) -> list[dict]:
        async with self.db._connect() as db:
            cur = await db.execute(
                "SELECT * FROM tournaments WHERE status IN ('pending','active') ORDER BY created_at DESC"
            )
            return [dict(r) for r in await cur.fetchall()]

    async def get_user_active_tournament(self, user_id: int) -> dict | None:
        async with self.db._connect() as db:
            cur = await db.execute(
                "SELECT t.* FROM tournaments t "
                "JOIN tournament_participants tp ON t.id = tp.tournament_id "
                "WHERE tp.user_id=? AND t.status='active' LIMIT 1",
                (user_id,),
            )
            row = await cur.fetchone()
            return dict(row) if row else None

    async def _get_tournament(self, tournament_id: int) -> dict | None:
        async with self.db._connect() as db:
            cur = await db.execute("SELECT * FROM tournaments WHERE id=?", (tournament_id,))
            row = await cur.fetchone()
            return dict(row) if row else None
