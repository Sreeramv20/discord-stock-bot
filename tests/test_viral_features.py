import pytest
import pytest_asyncio

from services.tournament_service import TournamentService
from services.fund_service import FundService
from services.margin_service import MarginService
from services.copy_trade_service import CopyTradeService
from services.insider_service import InsiderService
from services.ipo_service import IPOService
from services.prestige_service import PrestigeService
from services.market_hours_service import MarketHoursService


@pytest_asyncio.fixture
async def tournaments(db, market):
    return TournamentService(db, market)


@pytest_asyncio.fixture
async def funds(db, market):
    return FundService(db, market)


@pytest_asyncio.fixture
async def margin(db, market):
    return MarginService(db, market)


@pytest_asyncio.fixture
async def copy_trades(db):
    return CopyTradeService(db)


@pytest_asyncio.fixture
async def insiders(db):
    return InsiderService(db)


@pytest_asyncio.fixture
async def ipo_service(db):
    return IPOService(db)


@pytest_asyncio.fixture
async def prestige(db, market, portfolio):
    return PrestigeService(db, portfolio)


# ── Tournament Tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_and_join_tournament(tournaments, db):
    await db.ensure_user(1, "alice")
    t = await tournaments.create_tournament("Cup", 1, 10000.0, 1)
    assert t["id"] > 0
    result = await tournaments.join_tournament(t["id"], 1)
    assert result["start_cash"] == 10000.0


@pytest.mark.asyncio
async def test_duplicate_join_rejected(tournaments, db):
    await db.ensure_user(1)
    t = await tournaments.create_tournament("Cup", 1, 10000.0)
    await tournaments.join_tournament(t["id"], 1)
    with pytest.raises(ValueError, match="already joined"):
        await tournaments.join_tournament(t["id"], 1)


@pytest.mark.asyncio
async def test_tournament_buy_sell(tournaments, db, market):
    await db.ensure_user(1)
    t = await tournaments.create_tournament("Cup", 1, 10000.0)
    await tournaments.join_tournament(t["id"], 1)

    async with db._connect() as conn:
        await conn.execute("UPDATE tournaments SET status='active' WHERE id=?", (t["id"],))
        await conn.commit()

    result = await tournaments.tournament_buy(t["id"], 1, "AAPL", 5)
    assert result["shares"] == 5

    result = await tournaments.tournament_sell(t["id"], 1, "AAPL", 3)
    assert result["shares"] == 3


@pytest.mark.asyncio
async def test_tournament_shares_validation(tournaments, db):
    await db.ensure_user(1)
    t = await tournaments.create_tournament("Cup", 1, 10000.0)
    await tournaments.join_tournament(t["id"], 1)
    async with db._connect() as conn:
        await conn.execute("UPDATE tournaments SET status='active' WHERE id=?", (t["id"],))
        await conn.commit()
    with pytest.raises(ValueError, match="positive"):
        await tournaments.tournament_buy(t["id"], 1, "AAPL", 0)


# ── Fund Tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_fund(funds, db):
    await db.ensure_user(1, "alice")
    f = await funds.create_fund(1, "Alpha Fund")
    assert f["id"] > 0


@pytest.mark.asyncio
async def test_fund_join_contribute_trade(funds, db, market):
    await db.ensure_user(1, "alice")
    await db.ensure_user(2, "bob")
    f = await funds.create_fund(1, "Alpha")
    await funds.join_fund(2, f["id"])
    await funds.contribute(1, 5000)
    result = await funds.fund_buy(1, "AAPL", 5)
    assert result["total"] > 0


@pytest.mark.asyncio
async def test_fund_leader_leave_liquidates(funds, db, market):
    await db.ensure_user(1, "alice")
    f = await funds.create_fund(1, "Alpha")
    await funds.contribute(1, 5000)
    await funds.fund_buy(1, "AAPL", 5)

    balance_before = await db.get_user_balance(1)
    result = await funds.leave_fund(1)
    balance_after = await db.get_user_balance(1)
    assert result["refund"] > 0
    assert balance_after > balance_before


@pytest.mark.asyncio
async def test_fund_shares_validation(funds, db):
    await db.ensure_user(1)
    await funds.create_fund(1, "Alpha")
    await funds.contribute(1, 5000)
    with pytest.raises(ValueError, match="positive"):
        await funds.fund_buy(1, "AAPL", -1)


# ── Margin Tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_margin_open_close(margin, db, market):
    await db.ensure_user(1, "alice")
    pos = await margin.open_margin_position(1, "AAPL", 5, 2.0)
    assert pos["leverage"] == 2.0
    assert pos["liquidation_price"] > 0

    positions = await margin.get_user_positions(1)
    assert len(positions) == 1

    closed = await margin.close_margin_position(1, pos["position_id"])
    assert "profit" in closed

    positions = await margin.get_user_positions(1)
    assert len(positions) == 0


@pytest.mark.asyncio
async def test_margin_shares_validation(margin, db):
    await db.ensure_user(1)
    with pytest.raises(ValueError, match="positive"):
        await margin.open_margin_position(1, "AAPL", 0, 2.0)


@pytest.mark.asyncio
async def test_margin_leverage_validation(margin, db):
    await db.ensure_user(1)
    with pytest.raises(ValueError, match="Leverage"):
        await margin.open_margin_position(1, "AAPL", 5, 10.0)


@pytest.mark.asyncio
async def test_margin_liquidation_check(margin, db, market):
    await db.ensure_user(1, "alice")
    pos = await margin.open_margin_position(1, "AAPL", 5, 3.0)

    await db.upsert_stock("AAPL", 1.0)
    market._price_cache.pop("AAPL", None)

    liquidated = await margin.check_liquidations()
    assert len(liquidated) == 1
    assert liquidated[0]["user_id"] == 1


# ── Copy Trade Tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_copy_follow_unfollow(copy_trades, db):
    await db.ensure_user(1, "alice")
    await db.ensure_user(2, "bob")
    await copy_trades.follow(2, 1)
    followers = await copy_trades.get_followers(1)
    assert len(followers) == 1

    await copy_trades.unfollow(2, 1)
    followers = await copy_trades.get_followers(1)
    assert len(followers) == 0


@pytest.mark.asyncio
async def test_copy_self_rejected(copy_trades, db):
    await db.ensure_user(1)
    with pytest.raises(ValueError, match="yourself"):
        await copy_trades.follow(1, 1)


@pytest.mark.asyncio
async def test_copy_trade_execution(copy_trades, db, market):
    await db.ensure_user(1, "alice")
    await db.ensure_user(2, "bob")
    await copy_trades.follow(2, 1)

    results = await copy_trades.execute_copy_trades(1, "AAPL", "buy", 5, 150.0)
    assert len(results) == 1
    assert results[0]["success"]


# ── Insider Tests ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_insider_generate_and_list(insiders, db):
    leaks = await insiders.generate_leaks(3)
    assert len(leaks) == 3
    available = await insiders.get_available_leaks()
    assert len(available) >= 3


@pytest.mark.asyncio
async def test_insider_purchase(insiders, db):
    await db.ensure_user(1, "alice")
    leaks = await insiders.generate_leaks(1)
    result = await insiders.purchase_leak(1, leaks[0]["id"])
    assert result["cost"] > 0


@pytest.mark.asyncio
async def test_insider_duplicate_purchase_rejected(insiders, db):
    await db.ensure_user(1)
    leaks = await insiders.generate_leaks(1)
    await insiders.purchase_leak(1, leaks[0]["id"])
    with pytest.raises(ValueError, match="already purchased"):
        await insiders.purchase_leak(1, leaks[0]["id"])


# ── IPO Tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ipo_launch(ipo_service, db):
    ipo = await ipo_service.maybe_launch_ipo()
    assert ipo is not None
    assert ipo["ticker"]
    assert ipo["price"] > 0

    active = await ipo_service.get_active_ipos()
    assert len(active) >= 1


# ── Market Hours Tests ──────────────────────────────────────────────


def test_market_hours_sessions():
    mh = MarketHoursService()
    sessions = mh.get_all_sessions_status()
    assert len(sessions) == 3
    for s in sessions:
        assert "is_open" in s
        assert "volatility" in s


def test_market_hours_volatility():
    mh = MarketHoursService()
    vol = mh.get_volatility_multiplier()
    assert vol > 0


# ── Prestige Tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_prestige_insufficient_net_worth(prestige, db):
    await db.ensure_user(1, "alice")
    can, nw = await prestige.can_prestige(1)
    assert not can


@pytest.mark.asyncio
async def test_prestige_level_default(prestige, db):
    await db.ensure_user(1)
    level = await prestige.get_prestige_level(1)
    assert level["level"] == 0
    assert level["daily_bonus_mult"] == 1.0


@pytest.mark.asyncio
async def test_prestige_daily_multiplier(prestige, db):
    await db.ensure_user(1)
    mult = await prestige.get_daily_multiplier(1)
    assert mult == 1.0
