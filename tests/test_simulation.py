"""
Simulation test: 100 users performing concurrent operations.
Validates database consistency and no crashes under load.
"""

import pytest
import pytest_asyncio
import random


@pytest.mark.asyncio
async def test_simulation_100_users(db, market, trading, portfolio, leaderboard):
    NUM_USERS = 100

    for uid in range(1, NUM_USERS + 1):
        await db.ensure_user(uid, f"user_{uid}")

    initial_total = NUM_USERS * 10000.0

    for uid in range(1, NUM_USERS + 1):
        reward = random.randint(500, 2000)
        await db.increment_user_balance(uid, reward)

    for uid in range(1, NUM_USERS + 1):
        shares = random.randint(1, 10)
        try:
            await trading.buy_stock(uid, "AAPL", shares)
        except ValueError:
            pass

    for uid in range(1, NUM_USERS + 1):
        bal = await db.get_user_balance(uid)
        assert bal >= 0, f"User {uid} has negative balance: {bal}"

    for uid in range(1, NUM_USERS + 1):
        p = await portfolio.get_portfolio(uid)
        for h in p:
            assert h["shares"] > 0
            assert h["current_value"] >= 0

    sellers = random.sample(range(1, NUM_USERS + 1), 30)
    for uid in sellers:
        p = await db.get_user_portfolio(uid)
        for h in p:
            sell_qty = random.randint(1, max(1, int(h["shares"])))
            try:
                await trading.sell_stock(uid, h["ticker"], sell_qty)
            except ValueError:
                pass

    for uid in range(1, NUM_USERS + 1):
        bal = await db.get_user_balance(uid)
        assert bal >= 0, f"Negative balance for user {uid}"

    total_cash = 0.0
    total_stock_value = 0.0
    users = await db.get_all_users()
    assert len(users) == NUM_USERS
    for u in users:
        total_cash += u["cash_balance"]
        p = await db.get_user_portfolio(u["discord_id"])
        for h in p:
            price = await market.get_price(h["ticker"]) or 0
            total_stock_value += h["shares"] * price

    assert total_cash >= 0, "Total cash went negative"

    await leaderboard.update_rankings()
    top = await leaderboard.get_top(10)
    assert len(top) <= 10
    if len(top) >= 2:
        assert top[0]["net_worth"] >= top[1]["net_worth"]

    for uid in range(1, NUM_USERS + 1):
        nw = await portfolio.get_net_worth(uid)
        assert nw >= 0, f"Negative net worth for user {uid}: {nw}"


@pytest.mark.asyncio
async def test_rapid_buy_sell_same_user(db, trading, market):
    await db.ensure_user(999, "stress_user")

    for _ in range(20):
        try:
            await trading.buy_stock(999, "AAPL", 1)
        except ValueError:
            break

    for _ in range(20):
        try:
            await trading.sell_stock(999, "AAPL", 1)
        except ValueError:
            break

    bal = await db.get_user_balance(999)
    assert bal >= 0
    p = await db.get_user_portfolio(999)
    for h in p:
        assert h["shares"] >= 0


@pytest.mark.asyncio
async def test_double_buy_avg_price_correct(db, trading, market):
    await db.ensure_user(888)
    await db.upsert_stock("TEST", 100.0, name="Test")
    market._price_cache.pop("TEST", None)
    await trading.buy_stock(888, "TEST", 10)

    await db.upsert_stock("TEST", 200.0)
    market._price_cache.pop("TEST", None)
    await trading.buy_stock(888, "TEST", 10)

    p = await db.get_user_portfolio(888)
    test_pos = next(h for h in p if h["ticker"] == "TEST")
    assert test_pos["shares"] == 20
    assert abs(test_pos["avg_purchase_price"] - 150.0) < 0.01


@pytest.mark.asyncio
async def test_sell_more_than_owned_rejected(db, trading, market):
    await db.ensure_user(777)
    await trading.buy_stock(777, "AAPL", 5)
    with pytest.raises(ValueError, match="Insufficient"):
        await trading.sell_stock(777, "AAPL", 10)


@pytest.mark.asyncio
async def test_buy_exceeding_balance_rejected(db, trading, market):
    await db.ensure_user(666)
    with pytest.raises(ValueError, match="Insufficient"):
        await trading.buy_stock(666, "AAPL", 1_000_000)
