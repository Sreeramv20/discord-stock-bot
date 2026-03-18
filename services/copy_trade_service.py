import logging

import config
from database import Database

logger = logging.getLogger(__name__)


class CopyTradeService:
    def __init__(self, db: Database):
        self.db = db

    async def follow(self, follower_id: int, leader_id: int) -> dict:
        if follower_id == leader_id:
            raise ValueError("You cannot copy-trade yourself.")

        await self.db.ensure_user(follower_id)
        leader = await self.db.get_user(leader_id)
        if not leader:
            raise ValueError("Leader user not found.")

        async with self.db._connect() as db:
            cur = await db.execute(
                "SELECT 1 FROM copy_traders WHERE follower_id=? AND leader_id=? AND active=1",
                (follower_id, leader_id),
            )
            if await cur.fetchone():
                raise ValueError("You are already copy-trading this user.")

            cnt = await db.execute(
                "SELECT COUNT(*) as c FROM copy_traders WHERE leader_id=? AND active=1",
                (leader_id,),
            )
            count = (await cnt.fetchone())["c"]
            if count >= config.MAX_COPY_FOLLOWERS:
                raise ValueError("This trader has reached the maximum follower limit.")

            follower_cnt = await db.execute(
                "SELECT COUNT(*) as c FROM copy_traders WHERE follower_id=? AND active=1",
                (follower_id,),
            )
            f_count = (await follower_cnt.fetchone())["c"]
            if f_count >= 3:
                raise ValueError("You can only follow up to 3 traders.")

            await db.execute(
                "INSERT OR REPLACE INTO copy_traders "
                "(follower_id, leader_id, active, max_trade_pct) VALUES (?,?,1,?)",
                (follower_id, leader_id, config.COPY_TRADE_MAX_PCT),
            )
            await db.commit()

        if count + 1 >= 5:
            await self.db.add_achievement(leader_id, "copy_leader")

        logger.info("Copy-trade: user %s now following %s", follower_id, leader_id)
        return {"leader_id": leader_id, "leader_name": leader.get("username", str(leader_id))}

    async def unfollow(self, follower_id: int, leader_id: int) -> bool:
        async with self.db._connect() as db:
            cur = await db.execute(
                "UPDATE copy_traders SET active=0 WHERE follower_id=? AND leader_id=? AND active=1",
                (follower_id, leader_id),
            )
            await db.commit()
            return cur.rowcount > 0

    async def get_followers(self, leader_id: int) -> list[dict]:
        async with self.db._connect() as db:
            cur = await db.execute(
                "SELECT follower_id, max_trade_pct, created_at FROM copy_traders "
                "WHERE leader_id=? AND active=1",
                (leader_id,),
            )
            return [dict(r) for r in await cur.fetchall()]

    async def get_following(self, follower_id: int) -> list[dict]:
        async with self.db._connect() as db:
            cur = await db.execute(
                "SELECT leader_id, max_trade_pct, created_at FROM copy_traders "
                "WHERE follower_id=? AND active=1",
                (follower_id,),
            )
            return [dict(r) for r in await cur.fetchall()]

    async def execute_copy_trades(self, leader_id: int, ticker: str,
                                  trade_type: str, leader_shares: int,
                                  price: float) -> list[dict]:
        followers = await self.get_followers(leader_id)
        results = []

        for f in followers:
            follower_id = f["follower_id"]
            try:
                balance = await self.db.get_user_balance(follower_id)
                max_spend = balance * f["max_trade_pct"]

                if trade_type == "buy":
                    affordable = int(max_spend / price) if price > 0 else 0
                    copy_shares = min(leader_shares, max(1, affordable))
                    if copy_shares > 0 and balance >= copy_shares * price:
                        await self.db.execute_buy(follower_id, ticker, copy_shares, price)
                        results.append({"follower_id": follower_id, "shares": copy_shares,
                                        "type": "buy", "success": True})
                elif trade_type == "sell":
                    portfolio = await self.db.get_user_portfolio(follower_id)
                    held = next((p for p in portfolio if p["ticker"] == ticker), None)
                    if held and held["shares"] > 0:
                        copy_shares = min(leader_shares, int(held["shares"]))
                        if copy_shares > 0:
                            await self.db.execute_sell(follower_id, ticker, copy_shares, price)
                            results.append({"follower_id": follower_id, "shares": copy_shares,
                                            "type": "sell", "success": True})
            except Exception as e:
                logger.debug("Copy-trade failed for follower %s: %s", follower_id, e)
                results.append({"follower_id": follower_id, "success": False, "error": str(e)})

        if results:
            logger.info("Copy-trades executed: leader=%s ticker=%s %s -> %d followers",
                        leader_id, ticker, trade_type, len([r for r in results if r.get("success")]))
        return results
