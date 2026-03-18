import pytest


@pytest.mark.asyncio
async def test_init_creates_tables(db):
    async with db._connect() as conn:
        cur = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row["name"] for row in await cur.fetchall()}
    expected = {
        "users", "portfolios", "transactions", "stocks",
        "leaderboard", "achievements", "market_events",
        "limit_orders", "short_positions", "options", "dividends",
    }
    assert expected.issubset(tables)


@pytest.mark.asyncio
async def test_ensure_user_creates_new(db):
    await db.ensure_user(123, "testuser")
    user = await db.get_user(123)
    assert user is not None
    assert user["discord_id"] == 123
    assert user["username"] == "testuser"
    assert user["cash_balance"] == 10000.0


@pytest.mark.asyncio
async def test_ensure_user_idempotent(db):
    await db.ensure_user(123, "testuser")
    await db.ensure_user(123, "testuser")
    user = await db.get_user(123)
    assert user["cash_balance"] == 10000.0


@pytest.mark.asyncio
async def test_balance_operations(db):
    await db.ensure_user(1)
    bal = await db.get_user_balance(1)
    assert bal == 10000.0

    await db.update_user_balance(1, 5000.0)
    bal = await db.get_user_balance(1)
    assert bal == 5000.0


@pytest.mark.asyncio
async def test_stock_operations(db):
    await db.upsert_stock("TEST", 100.0, name="Test Corp", sector="Tech")
    stock = await db.get_stock("TEST")
    assert stock is not None
    assert stock["price"] == 100.0
    assert stock["name"] == "Test Corp"

    await db.upsert_stock("TEST", 110.0)
    stock = await db.get_stock("TEST")
    assert stock["price"] == 110.0
    assert stock["previous_price"] == 100.0


@pytest.mark.asyncio
async def test_portfolio_upsert_and_reduce(db):
    await db.ensure_user(1)
    await db.upsert_portfolio(1, "AAPL", 10, 150.0)
    portfolio = await db.get_user_portfolio(1)
    assert len(portfolio) == 1
    assert portfolio[0]["shares"] == 10
    assert portfolio[0]["avg_purchase_price"] == 150.0

    await db.upsert_portfolio(1, "AAPL", 10, 200.0)
    portfolio = await db.get_user_portfolio(1)
    assert portfolio[0]["shares"] == 20
    assert portfolio[0]["avg_purchase_price"] == 175.0

    await db.reduce_portfolio(1, "AAPL", 5)
    portfolio = await db.get_user_portfolio(1)
    assert portfolio[0]["shares"] == 15


@pytest.mark.asyncio
async def test_reduce_portfolio_insufficient_raises(db):
    await db.ensure_user(1)
    await db.upsert_portfolio(1, "AAPL", 5, 100.0)
    with pytest.raises(ValueError, match="Insufficient"):
        await db.reduce_portfolio(1, "AAPL", 10)


@pytest.mark.asyncio
async def test_transaction_logging(db):
    await db.ensure_user(1)
    await db.add_transaction(1, "AAPL", "buy", 10, 150.0)
    await db.add_transaction(1, "AAPL", "sell", 5, 160.0)
    txns = await db.get_user_transactions(1)
    assert len(txns) == 2
    assert txns[0]["type"] == "sell"
    assert txns[1]["type"] == "buy"


@pytest.mark.asyncio
async def test_execute_buy_atomic(db):
    await db.ensure_user(1)
    await db.upsert_stock("AAPL", 100.0, name="Apple")
    result = await db.execute_buy(1, "AAPL", 10, 100.0)
    assert result["total"] == 1000.0
    assert result["new_balance"] == 9000.0

    portfolio = await db.get_user_portfolio(1)
    assert len(portfolio) == 1
    assert portfolio[0]["shares"] == 10


@pytest.mark.asyncio
async def test_execute_buy_insufficient_funds(db):
    await db.ensure_user(1)
    with pytest.raises(ValueError, match="Insufficient funds"):
        await db.execute_buy(1, "AAPL", 1000, 100.0)


@pytest.mark.asyncio
async def test_execute_sell_atomic(db):
    await db.ensure_user(1)
    await db.execute_buy(1, "AAPL", 10, 100.0)
    result = await db.execute_sell(1, "AAPL", 5, 120.0)
    assert result["profit"] == 100.0
    assert result["new_balance"] == 9000.0 + 600.0


@pytest.mark.asyncio
async def test_execute_sell_insufficient_shares(db):
    await db.ensure_user(1)
    with pytest.raises(ValueError, match="Insufficient holdings"):
        await db.execute_sell(1, "AAPL", 10, 100.0)


@pytest.mark.asyncio
async def test_achievements(db):
    await db.ensure_user(1)
    added = await db.add_achievement(1, "first_trade")
    assert added is True

    duplicate = await db.add_achievement(1, "first_trade")
    assert duplicate is False

    has = await db.has_achievement(1, "first_trade")
    assert has is True

    achs = await db.get_user_achievements(1)
    assert len(achs) == 1
    assert achs[0]["achievement_id"] == "first_trade"


@pytest.mark.asyncio
async def test_limit_orders(db):
    await db.ensure_user(1)
    oid = await db.add_limit_order(1, "AAPL", "buy", 140.0, 10)
    assert oid > 0

    orders = await db.get_pending_limit_orders()
    assert len(orders) == 1

    await db.fill_limit_order(oid)
    orders = await db.get_pending_limit_orders()
    assert len(orders) == 0


@pytest.mark.asyncio
async def test_short_positions(db):
    await db.ensure_user(1)
    pid = await db.add_short_position(1, "TSLA", 10, 250.0)
    shorts = await db.get_user_shorts(1)
    assert len(shorts) == 1

    await db.close_short_position(pid)
    shorts = await db.get_user_shorts(1)
    assert len(shorts) == 0


@pytest.mark.asyncio
async def test_market_events(db):
    eid = await db.add_market_event("tech_rally", "Tech up", 1.1, ["AAPL"], 600)
    events = await db.get_active_events()
    assert len(events) == 1
    assert events[0]["multiplier"] == 1.1

    expired = await db.expire_events()
    assert expired == 0


@pytest.mark.asyncio
async def test_leaderboard(db):
    await db.ensure_user(1)
    await db.ensure_user(2)
    await db.update_leaderboard_entry(1, 15000.0, 5000.0, 1)
    await db.update_leaderboard_entry(2, 12000.0, 2000.0, 2)

    lb = await db.get_leaderboard(10)
    assert len(lb) == 2
    assert lb[0]["rank"] == 1

    rank = await db.get_user_rank(2)
    assert rank["rank"] == 2
