import pytest


@pytest.mark.asyncio
async def test_buy_stock(trading, db):
    await db.ensure_user(1, "trader1")
    result = await trading.buy_stock(1, "AAPL", 5)
    assert result["shares"] == 5
    assert result["new_balance"] < 10000.0

    portfolio = await db.get_user_portfolio(1)
    assert len(portfolio) == 1
    assert portfolio[0]["ticker"] == "AAPL"
    assert portfolio[0]["shares"] == 5


@pytest.mark.asyncio
async def test_sell_stock(trading, db):
    await db.ensure_user(1, "trader1")
    await trading.buy_stock(1, "AAPL", 10)
    result = await trading.sell_stock(1, "AAPL", 5)
    assert result["shares"] == 5
    assert "profit" in result

    portfolio = await db.get_user_portfolio(1)
    assert portfolio[0]["shares"] == 5


@pytest.mark.asyncio
async def test_buy_insufficient_funds(trading, db):
    await db.ensure_user(1, "trader1")
    with pytest.raises(ValueError, match="Insufficient funds"):
        await trading.buy_stock(1, "AAPL", 10000)


@pytest.mark.asyncio
async def test_sell_insufficient_shares(trading, db):
    await db.ensure_user(1, "trader1")
    with pytest.raises(ValueError, match="Insufficient holdings"):
        await trading.sell_stock(1, "AAPL", 10)


@pytest.mark.asyncio
async def test_buy_invalid_ticker(trading, db):
    await db.ensure_user(1, "trader1")
    with pytest.raises(ValueError, match="not found"):
        await trading.buy_stock(1, "ZZZZ", 1)


@pytest.mark.asyncio
async def test_buy_invalid_shares(trading, db):
    await db.ensure_user(1, "trader1")
    with pytest.raises(ValueError, match="positive"):
        await trading.buy_stock(1, "AAPL", 0)


@pytest.mark.asyncio
async def test_place_limit_order(trading, db):
    await db.ensure_user(1, "trader1")
    oid = await trading.place_limit_order(1, "AAPL", "buy", 140.0, 5)
    assert oid > 0

    orders = await db.get_user_limit_orders(1)
    assert len(orders) == 1
    assert orders[0]["status"] == "pending"


@pytest.mark.asyncio
async def test_cancel_limit_order(trading, db):
    await db.ensure_user(1, "trader1")
    oid = await trading.place_limit_order(1, "AAPL", "buy", 140.0, 5)
    success = await trading.cancel_limit_order(1, oid)
    assert success is True

    orders = await db.get_user_limit_orders(1)
    assert orders[0]["status"] == "cancelled"


@pytest.mark.asyncio
async def test_short_stock(trading, db):
    await db.ensure_user(1, "trader1")
    result = await trading.short_stock(1, "TSLA", 5)
    assert result["shares"] == 5
    assert result["borrow_price"] == 250.0

    shorts = await db.get_user_shorts(1)
    assert len(shorts) == 1


@pytest.mark.asyncio
async def test_cover_short(trading, db):
    await db.ensure_user(1, "trader1")
    result = await trading.short_stock(1, "TSLA", 5)
    shorts = await db.get_user_shorts(1)
    pid = shorts[0]["id"]

    cover_result = await trading.cover_short(1, pid)
    assert "profit" in cover_result

    shorts = await db.get_user_shorts(1)
    assert len(shorts) == 0


@pytest.mark.asyncio
async def test_buy_option(trading, db):
    await db.ensure_user(1, "trader1")
    result = await trading.buy_option(1, "AAPL", "call", 160.0, 30)
    assert result["type"] == "call"
    assert result["premium"] > 0
    assert result["new_balance"] < 10000.0


@pytest.mark.asyncio
async def test_user_stats(trading, db):
    await db.ensure_user(1, "trader1")
    await trading.buy_stock(1, "AAPL", 5)
    await trading.sell_stock(1, "AAPL", 3)

    stats = await trading.get_user_stats(1)
    assert stats["total_buys"] == 1
    assert stats["total_sells"] == 1
    assert stats["total_trades"] == 2
