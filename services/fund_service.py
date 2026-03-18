import logging

import config
from database import Database
from market import Market

logger = logging.getLogger(__name__)


class FundService:
    def __init__(self, db: Database, market: Market):
        self.db = db
        self.market = market

    async def create_fund(self, leader_id: int, name: str,
                          description: str = "") -> dict:
        await self.db.ensure_user(leader_id)

        existing = await self._get_user_fund(leader_id)
        if existing:
            raise ValueError("You are already in a fund. Leave first.")

        async with self.db._connect() as db:
            try:
                cur = await db.execute(
                    "INSERT INTO funds (name, leader_id, description, max_members) "
                    "VALUES (?,?,?,?)",
                    (name, leader_id, description, config.FUND_MAX_MEMBERS),
                )
                fund_id = cur.lastrowid
                await db.execute(
                    "INSERT INTO fund_members (fund_id, user_id, role) VALUES (?,?,?)",
                    (fund_id, leader_id, "leader"),
                )
                await db.commit()
            except Exception as e:
                if "UNIQUE" in str(e):
                    raise ValueError(f"Fund name `{name}` is already taken.")
                raise

        await self.db.add_achievement(leader_id, "fund_founder")
        logger.info("Fund created: %s (id=%d) by user %s", name, fund_id, leader_id)
        return {"id": fund_id, "name": name}

    async def join_fund(self, user_id: int, fund_id: int) -> dict:
        await self.db.ensure_user(user_id)
        existing = await self._get_user_fund(user_id)
        if existing:
            raise ValueError("You are already in a fund. Leave first.")

        async with self.db._connect() as db:
            cur = await db.execute("SELECT * FROM funds WHERE id=?", (fund_id,))
            fund = await cur.fetchone()
            if not fund:
                raise ValueError("Fund not found.")
            fund = dict(fund)

            cnt = await db.execute(
                "SELECT COUNT(*) as c FROM fund_members WHERE fund_id=?", (fund_id,),
            )
            count = (await cnt.fetchone())["c"]
            if count >= fund["max_members"]:
                raise ValueError("Fund is full.")

            await db.execute(
                "INSERT INTO fund_members (fund_id, user_id, role) VALUES (?,?,?)",
                (fund_id, user_id, "member"),
            )
            await db.commit()

        logger.info("User %s joined fund %d", user_id, fund_id)
        return {"fund_id": fund_id, "fund_name": fund["name"]}

    async def leave_fund(self, user_id: int) -> dict:
        membership = await self._get_user_fund(user_id)
        if not membership:
            raise ValueError("You are not in any fund.")

        fund_id = membership["fund_id"]
        role = membership["role"]
        contribution = membership["contribution"]

        if role == "leader":
            async with self.db._connect() as db:
                cnt = await db.execute(
                    "SELECT COUNT(*) as c FROM fund_members WHERE fund_id=? AND user_id!=?",
                    (fund_id, user_id),
                )
                other_count = (await cnt.fetchone())["c"]
                if other_count > 0:
                    raise ValueError("Transfer leadership first or remove all members.")

        refund = 0.0
        if role == "leader":
            async with self.db._connect() as db:
                cur = await db.execute(
                    "SELECT ticker, shares FROM fund_portfolios WHERE fund_id=?", (fund_id,),
                )
                holdings = [dict(r) for r in await cur.fetchall()]
            liquidation_value = 0.0
            for h in holdings:
                price = await self.market.get_price(h["ticker"]) or 0
                liquidation_value += h["shares"] * price
            async with self.db._connect() as db:
                cur = await db.execute(
                    "SELECT cash_balance FROM funds WHERE id=?", (fund_id,),
                )
                fund = await cur.fetchone()
            refund = fund["cash_balance"] + liquidation_value
            await self.db.increment_user_balance(user_id, refund)

            async with self.db._connect() as db:
                await db.execute("DELETE FROM fund_transactions WHERE fund_id=?", (fund_id,))
                await db.execute("DELETE FROM fund_members WHERE fund_id=?", (fund_id,))
                await db.execute("DELETE FROM fund_portfolios WHERE fund_id=?", (fund_id,))
                await db.execute("DELETE FROM funds WHERE id=?", (fund_id,))
                await db.commit()
        else:
            if contribution > 0:
                async with self.db._connect() as db:
                    cur = await db.execute(
                        "SELECT cash_balance FROM funds WHERE id=?", (fund_id,),
                    )
                    fund = await cur.fetchone()
                    refund = min(contribution, fund["cash_balance"])
                    await db.execute(
                        "UPDATE funds SET cash_balance = cash_balance - ? WHERE id=?",
                        (refund, fund_id),
                    )
                    await db.commit()
                await self.db.increment_user_balance(user_id, refund)

            async with self.db._connect() as db:
                await db.execute(
                    "DELETE FROM fund_members WHERE fund_id=? AND user_id=?",
                    (fund_id, user_id),
                )
                await db.commit()

        return {"refund": refund, "fund_id": fund_id}

    async def contribute(self, user_id: int, amount: float) -> dict:
        if amount < config.FUND_MIN_CONTRIBUTION:
            raise ValueError(f"Minimum contribution is ${config.FUND_MIN_CONTRIBUTION:,.0f}")

        membership = await self._get_user_fund(user_id)
        if not membership:
            raise ValueError("You are not in any fund.")

        balance = await self.db.get_user_balance(user_id)
        if balance < amount:
            raise ValueError("Insufficient personal funds.")

        fund_id = membership["fund_id"]
        await self.db.update_user_balance(user_id, balance - amount)

        async with self.db._connect() as db:
            await db.execute(
                "UPDATE funds SET cash_balance = cash_balance + ? WHERE id=?",
                (amount, fund_id),
            )
            await db.execute(
                "UPDATE fund_members SET contribution = contribution + ? "
                "WHERE fund_id=? AND user_id=?",
                (amount, fund_id, user_id),
            )
            await db.commit()

        return {"amount": amount, "fund_id": fund_id}

    async def fund_buy(self, user_id: int, ticker: str, shares: int) -> dict:
        if shares <= 0:
            raise ValueError("Shares must be a positive integer.")
        membership = await self._get_user_fund(user_id)
        if not membership:
            raise ValueError("You are not in any fund.")
        if membership["role"] not in ("leader", "officer"):
            raise ValueError("Only the fund leader or officers can trade.")

        fund_id = membership["fund_id"]
        price = await self.market.get_price(ticker)
        if price is None:
            raise ValueError(f"Stock `{ticker}` not found.")

        total_cost = shares * price
        async with self.db.transaction() as db:
            cur = await db.execute("SELECT cash_balance FROM funds WHERE id=?", (fund_id,))
            fund = await cur.fetchone()
            if fund["cash_balance"] < total_cost:
                raise ValueError(f"Insufficient fund cash. Have ${fund['cash_balance']:,.2f}")

            await db.execute(
                "UPDATE funds SET cash_balance = cash_balance - ? WHERE id=?",
                (total_cost, fund_id),
            )

            cur2 = await db.execute(
                "SELECT shares, avg_price FROM fund_portfolios WHERE fund_id=? AND ticker=?",
                (fund_id, ticker),
            )
            existing = await cur2.fetchone()
            if existing:
                old_s, old_p = existing["shares"], existing["avg_price"]
                new_s = old_s + shares
                new_p = ((old_s * old_p) + (shares * price)) / new_s
                await db.execute(
                    "UPDATE fund_portfolios SET shares=?, avg_price=? "
                    "WHERE fund_id=? AND ticker=?",
                    (new_s, new_p, fund_id, ticker),
                )
            else:
                await db.execute(
                    "INSERT INTO fund_portfolios VALUES (?,?,?,?)",
                    (fund_id, ticker, shares, price),
                )

            await db.execute(
                "INSERT INTO fund_transactions (fund_id,user_id,ticker,type,shares,price,total) "
                "VALUES (?,?,?,?,?,?,?)",
                (fund_id, user_id, ticker, "buy", shares, price, total_cost),
            )

        return {"ticker": ticker, "shares": shares, "price": price, "total": total_cost}

    async def fund_sell(self, user_id: int, ticker: str, shares: int) -> dict:
        if shares <= 0:
            raise ValueError("Shares must be a positive integer.")
        membership = await self._get_user_fund(user_id)
        if not membership:
            raise ValueError("You are not in any fund.")
        if membership["role"] not in ("leader", "officer"):
            raise ValueError("Only the fund leader or officers can trade.")

        fund_id = membership["fund_id"]
        price = await self.market.get_price(ticker)
        if price is None:
            raise ValueError(f"Stock `{ticker}` not found.")

        total_value = shares * price
        async with self.db.transaction() as db:
            cur = await db.execute(
                "SELECT shares FROM fund_portfolios WHERE fund_id=? AND ticker=?",
                (fund_id, ticker),
            )
            row = await cur.fetchone()
            if not row or row["shares"] < shares:
                raise ValueError("Fund has insufficient holdings.")

            remaining = row["shares"] - shares
            if remaining <= 0:
                await db.execute(
                    "DELETE FROM fund_portfolios WHERE fund_id=? AND ticker=?",
                    (fund_id, ticker),
                )
            else:
                await db.execute(
                    "UPDATE fund_portfolios SET shares=? WHERE fund_id=? AND ticker=?",
                    (remaining, fund_id, ticker),
                )

            await db.execute(
                "UPDATE funds SET cash_balance = cash_balance + ? WHERE id=?",
                (total_value, fund_id),
            )
            await db.execute(
                "INSERT INTO fund_transactions (fund_id,user_id,ticker,type,shares,price,total) "
                "VALUES (?,?,?,?,?,?,?)",
                (fund_id, user_id, ticker, "sell", shares, price, total_value),
            )

        return {"ticker": ticker, "shares": shares, "price": price, "total": total_value}

    async def get_fund_portfolio(self, fund_id: int) -> dict:
        async with self.db._connect() as db:
            cur = await db.execute("SELECT * FROM funds WHERE id=?", (fund_id,))
            fund = await cur.fetchone()
            if not fund:
                raise ValueError("Fund not found.")
            fund = dict(fund)

            cur2 = await db.execute(
                "SELECT * FROM fund_portfolios WHERE fund_id=?", (fund_id,),
            )
            holdings = [dict(r) for r in await cur2.fetchall()]

            cur3 = await db.execute(
                "SELECT * FROM fund_members WHERE fund_id=?", (fund_id,),
            )
            members = [dict(r) for r in await cur3.fetchall()]

        portfolio_value = 0.0
        enriched = []
        for h in holdings:
            price = await self.market.get_price(h["ticker"]) or h["avg_price"]
            value = h["shares"] * price
            portfolio_value += value
            enriched.append({**h, "current_price": price, "value": value})

        return {
            "fund": fund, "holdings": enriched, "members": members,
            "portfolio_value": portfolio_value,
            "total_value": fund["cash_balance"] + portfolio_value,
        }

    async def get_fund_leaderboard(self) -> list[dict]:
        async with self.db._connect() as db:
            cur = await db.execute("SELECT * FROM funds ORDER BY id")
            funds = [dict(r) for r in await cur.fetchall()]

        entries = []
        for f in funds:
            pv = 0.0
            async with self.db._connect() as db:
                cur = await db.execute(
                    "SELECT ticker, shares FROM fund_portfolios WHERE fund_id=?", (f["id"],)
                )
                for row in await cur.fetchall():
                    price = await self.market.get_price(row["ticker"]) or 0
                    pv += row["shares"] * price
            total = f["cash_balance"] + pv
            async with self.db._connect() as db:
                cnt = await db.execute(
                    "SELECT COUNT(*) as c FROM fund_members WHERE fund_id=?", (f["id"],),
                )
                member_count = (await cnt.fetchone())["c"]
            entries.append({"fund_id": f["id"], "name": f["name"],
                            "total_value": total, "members": member_count,
                            "leader_id": f["leader_id"]})

        entries.sort(key=lambda x: x["total_value"], reverse=True)
        for rank, e in enumerate(entries, 1):
            e["rank"] = rank
        return entries

    async def _get_user_fund(self, user_id: int) -> dict | None:
        async with self.db._connect() as db:
            cur = await db.execute(
                "SELECT fm.*, f.name as fund_name FROM fund_members fm "
                "JOIN funds f ON fm.fund_id = f.id WHERE fm.user_id=?",
                (user_id,),
            )
            row = await cur.fetchone()
            return dict(row) if row else None
