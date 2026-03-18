import pytest


@pytest.mark.asyncio
async def test_empty_leaderboard(leaderboard):
    top = await leaderboard.get_top(10)
    assert top == []


@pytest.mark.asyncio
async def test_update_rankings(leaderboard, db):
    await db.ensure_user(1, "alice")
    await db.ensure_user(2, "bob")
    await db.update_user_balance(1, 20000.0)
    await db.update_user_balance(2, 15000.0)

    await leaderboard.update_rankings()

    top = await leaderboard.get_top(10)
    assert len(top) == 2
    assert top[0]["user_id"] == 1
    assert top[0]["net_worth"] == 20000.0
    assert top[1]["user_id"] == 2


@pytest.mark.asyncio
async def test_rank_lookup(leaderboard, db):
    await db.ensure_user(1, "alice")
    await db.ensure_user(2, "bob")
    await db.update_user_balance(1, 20000.0)

    await leaderboard.update_rankings()

    rank = await leaderboard.get_rank(1)
    assert rank is not None
    assert rank["rank"] == 1

    rank2 = await leaderboard.get_rank(2)
    assert rank2["rank"] == 2


@pytest.mark.asyncio
async def test_rankings_with_portfolio(leaderboard, db):
    await db.ensure_user(1, "alice")
    await db.ensure_user(2, "bob")

    await db.upsert_stock("AAPL", 150.0, name="Apple")
    await db.execute_buy(1, "AAPL", 20, 150.0)

    await leaderboard.update_rankings()

    rank1 = await leaderboard.get_rank(1)
    rank2 = await leaderboard.get_rank(2)
    assert rank1["rank"] == rank2["rank"] or rank1["net_worth"] >= rank2["net_worth"]


@pytest.mark.asyncio
async def test_nonexistent_user_rank(leaderboard):
    rank = await leaderboard.get_rank(99999)
    assert rank is None
