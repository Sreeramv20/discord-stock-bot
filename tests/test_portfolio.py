import pytest


@pytest.mark.asyncio
async def test_empty_portfolio(portfolio, db):
    await db.ensure_user(1)
    holdings = await portfolio.get_portfolio(1)
    assert holdings == []


@pytest.mark.asyncio
async def test_portfolio_with_holdings(portfolio, db):
    await db.ensure_user(1)
    await db.execute_buy(1, "AAPL", 10, 150.0)
    await db.execute_buy(1, "MSFT", 5, 300.0)

    holdings = await portfolio.get_portfolio(1)
    assert len(holdings) == 2

    aapl = next(h for h in holdings if h["ticker"] == "AAPL")
    assert aapl["shares"] == 10
    assert aapl["avg_price"] == 150.0
    assert aapl["current_value"] == 10 * 150.0


@pytest.mark.asyncio
async def test_portfolio_value(portfolio, db):
    await db.ensure_user(1)
    await db.execute_buy(1, "AAPL", 10, 150.0)
    value = await portfolio.get_portfolio_value(1)
    assert value == 10 * 150.0


@pytest.mark.asyncio
async def test_net_worth(portfolio, db):
    await db.ensure_user(1)
    nw = await portfolio.get_net_worth(1)
    assert nw == 10000.0

    await db.execute_buy(1, "AAPL", 10, 150.0)
    nw = await portfolio.get_net_worth(1)
    assert nw == 10000.0


@pytest.mark.asyncio
async def test_portfolio_summary(portfolio, db):
    await db.ensure_user(1)
    await db.execute_buy(1, "AAPL", 10, 150.0)
    summary = await portfolio.get_summary(1)

    assert summary["balance"] == 10000.0 - 1500.0
    assert summary["portfolio_value"] == 1500.0
    assert summary["net_worth"] == 10000.0
    assert summary["positions"] == 1


@pytest.mark.asyncio
async def test_profit_loss_display(portfolio, db):
    await db.ensure_user(1)
    await db.execute_buy(1, "AAPL", 10, 100.0)

    await db.upsert_stock("AAPL", 120.0)

    holdings = await portfolio.get_portfolio(1)
    aapl = holdings[0]
    assert aapl["current_price"] == 120.0
    assert aapl["profit_loss"] == 200.0
    assert aapl["profit_pct"] == pytest.approx(20.0)
