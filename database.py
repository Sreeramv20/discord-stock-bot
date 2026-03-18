import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import aiosqlite

import config

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, path: str | None = None):
        self.path = path or config.DATABASE_PATH

    async def init(self):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("PRAGMA foreign_keys=ON")
            await self._create_tables(db)
            await self._create_viral_tables(db)
            await self._create_indexes(db)
            await self._create_viral_indexes(db)
            await db.commit()
        logger.info("Database initialized at %s", self.path)

    @asynccontextmanager
    async def _connect(self):
        db = await aiosqlite.connect(self.path)
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys=ON")
        try:
            yield db
        finally:
            await db.close()

    @asynccontextmanager
    async def transaction(self):
        db = await aiosqlite.connect(self.path)
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys=ON")
        try:
            await db.execute("BEGIN IMMEDIATE")
            yield db
            await db.commit()
        except Exception:
            await db.rollback()
            raise
        finally:
            await db.close()

    # ── Schema ──────────────────────────────────────────────────────

    async def _create_tables(self, db):
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                discord_id   INTEGER PRIMARY KEY,
                username     TEXT,
                cash_balance REAL    NOT NULL DEFAULT 10000.0,
                created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
                last_daily   TEXT
            );

            CREATE TABLE IF NOT EXISTS portfolios (
                user_id           INTEGER NOT NULL,
                ticker            TEXT    NOT NULL,
                shares            REAL    NOT NULL DEFAULT 0,
                avg_purchase_price REAL   NOT NULL DEFAULT 0,
                acquired_at       TEXT    NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (user_id, ticker),
                FOREIGN KEY (user_id) REFERENCES users(discord_id)
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER NOT NULL,
                ticker    TEXT    NOT NULL,
                type      TEXT    NOT NULL,
                shares    REAL    NOT NULL,
                price     REAL    NOT NULL,
                total     REAL    NOT NULL,
                timestamp TEXT    NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(discord_id)
            );

            CREATE TABLE IF NOT EXISTS stocks (
                ticker       TEXT PRIMARY KEY,
                name         TEXT,
                price        REAL NOT NULL,
                previous_price REAL,
                volume       INTEGER DEFAULT 0,
                sector       TEXT,
                last_updated REAL
            );

            CREATE TABLE IF NOT EXISTS leaderboard (
                user_id    INTEGER PRIMARY KEY,
                net_worth  REAL    NOT NULL,
                profit     REAL    NOT NULL DEFAULT 0,
                rank       INTEGER NOT NULL,
                updated_at REAL,
                FOREIGN KEY (user_id) REFERENCES users(discord_id)
            );

            CREATE TABLE IF NOT EXISTS achievements (
                user_id        INTEGER NOT NULL,
                achievement_id TEXT    NOT NULL,
                earned_at      TEXT    NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (user_id, achievement_id),
                FOREIGN KEY (user_id) REFERENCES users(discord_id)
            );

            CREATE TABLE IF NOT EXISTS market_events (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type       TEXT NOT NULL,
                description      TEXT,
                multiplier       REAL NOT NULL DEFAULT 1.0,
                affected_tickers TEXT,
                duration         INTEGER NOT NULL,
                created_at       REAL NOT NULL,
                expires_at       REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS limit_orders (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL,
                ticker       TEXT    NOT NULL,
                order_type   TEXT    NOT NULL CHECK(order_type IN ('buy','sell')),
                target_price REAL    NOT NULL,
                shares       INTEGER NOT NULL,
                status       TEXT    NOT NULL DEFAULT 'pending'
                                     CHECK(status IN ('pending','filled','cancelled')),
                created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
                filled_at    TEXT,
                FOREIGN KEY (user_id) REFERENCES users(discord_id)
            );

            CREATE TABLE IF NOT EXISTS short_positions (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL,
                ticker       TEXT    NOT NULL,
                shares       REAL    NOT NULL,
                borrow_price REAL    NOT NULL,
                created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
                closed       INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(discord_id)
            );

            CREATE TABLE IF NOT EXISTS options (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL,
                ticker       TEXT    NOT NULL,
                option_type  TEXT    NOT NULL CHECK(option_type IN ('call','put')),
                strike_price REAL    NOT NULL,
                premium      REAL    NOT NULL,
                expiry       TEXT    NOT NULL,
                status       TEXT    NOT NULL DEFAULT 'active'
                                     CHECK(status IN ('active','exercised','expired')),
                created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(discord_id)
            );

            CREATE TABLE IF NOT EXISTS dividends (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker           TEXT NOT NULL,
                amount_per_share REAL NOT NULL,
                pay_date         TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)

    async def _create_viral_tables(self, db):
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS tournaments (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                status      TEXT    NOT NULL DEFAULT 'pending'
                                    CHECK(status IN ('pending','active','ended')),
                start_cash  REAL    NOT NULL DEFAULT 10000,
                start_time  TEXT,
                end_time    TEXT,
                reward_1st  REAL    NOT NULL DEFAULT 50000,
                reward_2nd  REAL    NOT NULL DEFAULT 25000,
                reward_3rd  REAL    NOT NULL DEFAULT 10000,
                created_by  INTEGER,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS tournament_participants (
                tournament_id INTEGER NOT NULL,
                user_id       INTEGER NOT NULL,
                cash_balance  REAL    NOT NULL,
                final_return  REAL,
                rank          INTEGER,
                joined_at     TEXT    NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (tournament_id, user_id),
                FOREIGN KEY (tournament_id) REFERENCES tournaments(id)
            );

            CREATE TABLE IF NOT EXISTS tournament_portfolios (
                tournament_id INTEGER NOT NULL,
                user_id       INTEGER NOT NULL,
                ticker        TEXT    NOT NULL,
                shares        REAL    NOT NULL DEFAULT 0,
                avg_price     REAL    NOT NULL DEFAULT 0,
                PRIMARY KEY (tournament_id, user_id, ticker),
                FOREIGN KEY (tournament_id) REFERENCES tournaments(id)
            );

            CREATE TABLE IF NOT EXISTS tournament_trades (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL,
                user_id       INTEGER NOT NULL,
                ticker        TEXT    NOT NULL,
                type          TEXT    NOT NULL,
                shares        REAL    NOT NULL,
                price         REAL    NOT NULL,
                total         REAL    NOT NULL,
                timestamp     TEXT    NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (tournament_id) REFERENCES tournaments(id)
            );

            CREATE TABLE IF NOT EXISTS insider_leaks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker      TEXT    NOT NULL,
                leak_type   TEXT    NOT NULL CHECK(leak_type IN ('bullish','bearish')),
                is_accurate INTEGER NOT NULL DEFAULT 1,
                magnitude   REAL    NOT NULL DEFAULT 0.10,
                description TEXT,
                cost        REAL    NOT NULL DEFAULT 500,
                expires_at  TEXT    NOT NULL,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS leak_purchases (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL,
                leak_id      INTEGER NOT NULL,
                purchased_at TEXT    NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (leak_id) REFERENCES insider_leaks(id)
            );

            CREATE TABLE IF NOT EXISTS funds (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                name         TEXT    UNIQUE NOT NULL,
                leader_id    INTEGER NOT NULL,
                description  TEXT,
                cash_balance REAL    NOT NULL DEFAULT 0,
                max_members  INTEGER NOT NULL DEFAULT 10,
                created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS fund_members (
                fund_id      INTEGER NOT NULL,
                user_id      INTEGER NOT NULL,
                role         TEXT    NOT NULL DEFAULT 'member'
                                     CHECK(role IN ('leader','officer','member')),
                contribution REAL    NOT NULL DEFAULT 0,
                joined_at    TEXT    NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (fund_id, user_id),
                FOREIGN KEY (fund_id) REFERENCES funds(id)
            );

            CREATE TABLE IF NOT EXISTS fund_portfolios (
                fund_id   INTEGER NOT NULL,
                ticker    TEXT    NOT NULL,
                shares    REAL    NOT NULL DEFAULT 0,
                avg_price REAL    NOT NULL DEFAULT 0,
                PRIMARY KEY (fund_id, ticker),
                FOREIGN KEY (fund_id) REFERENCES funds(id)
            );

            CREATE TABLE IF NOT EXISTS fund_transactions (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                fund_id   INTEGER NOT NULL,
                user_id   INTEGER NOT NULL,
                ticker    TEXT    NOT NULL,
                type      TEXT    NOT NULL,
                shares    REAL    NOT NULL,
                price     REAL    NOT NULL,
                total     REAL    NOT NULL,
                timestamp TEXT    NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (fund_id) REFERENCES funds(id)
            );

            CREATE TABLE IF NOT EXISTS margin_positions (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id           INTEGER NOT NULL,
                ticker            TEXT    NOT NULL,
                shares            REAL    NOT NULL,
                entry_price       REAL    NOT NULL,
                leverage          REAL    NOT NULL DEFAULT 2.0,
                margin_used       REAL    NOT NULL,
                borrowed          REAL    NOT NULL,
                liquidation_price REAL    NOT NULL,
                status            TEXT    NOT NULL DEFAULT 'open'
                                          CHECK(status IN ('open','closed','liquidated')),
                created_at        TEXT    NOT NULL DEFAULT (datetime('now')),
                closed_at         TEXT
            );

            CREATE TABLE IF NOT EXISTS copy_traders (
                follower_id   INTEGER NOT NULL,
                leader_id     INTEGER NOT NULL,
                active        INTEGER NOT NULL DEFAULT 1,
                max_trade_pct REAL    NOT NULL DEFAULT 0.10,
                created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (follower_id, leader_id)
            );

            CREATE TABLE IF NOT EXISTS ipos (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker                TEXT    UNIQUE NOT NULL,
                name                  TEXT    NOT NULL,
                initial_price         REAL    NOT NULL,
                sector                TEXT,
                phase                 TEXT    NOT NULL DEFAULT 'announced'
                                              CHECK(phase IN ('announced','open','trading')),
                volatility_multiplier REAL    NOT NULL DEFAULT 2.0,
                announced_at          TEXT    NOT NULL DEFAULT (datetime('now')),
                opens_at              TEXT,
                trades_at             TEXT
            );

            CREATE TABLE IF NOT EXISTS prestige_levels (
                user_id              INTEGER PRIMARY KEY,
                level                INTEGER NOT NULL DEFAULT 0,
                total_resets         INTEGER NOT NULL DEFAULT 0,
                daily_bonus_mult     REAL    NOT NULL DEFAULT 1.0,
                title                TEXT    NOT NULL DEFAULT '',
                last_prestige_at     TEXT
            );
        """)

    async def _create_indexes(self, db):
        await db.executescript("""
            CREATE INDEX IF NOT EXISTS idx_portfolios_user ON portfolios(user_id);
            CREATE INDEX IF NOT EXISTS idx_portfolios_ticker ON portfolios(ticker);
            CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id);
            CREATE INDEX IF NOT EXISTS idx_transactions_ticker ON transactions(ticker);
            CREATE INDEX IF NOT EXISTS idx_limit_orders_status ON limit_orders(status);
            CREATE INDEX IF NOT EXISTS idx_limit_orders_user ON limit_orders(user_id);
            CREATE INDEX IF NOT EXISTS idx_short_positions_user ON short_positions(user_id);
            CREATE INDEX IF NOT EXISTS idx_options_user ON options(user_id);
            CREATE INDEX IF NOT EXISTS idx_options_status ON options(status);
            CREATE INDEX IF NOT EXISTS idx_leaderboard_rank ON leaderboard(rank);
            CREATE INDEX IF NOT EXISTS idx_market_events_expires ON market_events(expires_at);
        """)

    async def _create_viral_indexes(self, db):
        await db.executescript("""
            CREATE INDEX IF NOT EXISTS idx_tourn_part_tid ON tournament_participants(tournament_id);
            CREATE INDEX IF NOT EXISTS idx_tourn_port_tid ON tournament_portfolios(tournament_id);
            CREATE INDEX IF NOT EXISTS idx_tourn_trades_tid ON tournament_trades(tournament_id);
            CREATE INDEX IF NOT EXISTS idx_fund_members_fid ON fund_members(fund_id);
            CREATE INDEX IF NOT EXISTS idx_fund_port_fid ON fund_portfolios(fund_id);
            CREATE INDEX IF NOT EXISTS idx_margin_user ON margin_positions(user_id);
            CREATE INDEX IF NOT EXISTS idx_margin_status ON margin_positions(status);
            CREATE INDEX IF NOT EXISTS idx_copy_leader ON copy_traders(leader_id);
            CREATE INDEX IF NOT EXISTS idx_copy_follower ON copy_traders(follower_id);
            CREATE INDEX IF NOT EXISTS idx_ipos_phase ON ipos(phase);
            CREATE INDEX IF NOT EXISTS idx_leaks_expires ON insider_leaks(expires_at);
            CREATE INDEX IF NOT EXISTS idx_leak_purchases_user ON leak_purchases(user_id);
        """)

    # ── Users ───────────────────────────────────────────────────────

    async def ensure_user(self, discord_id: int, username: str | None = None):
        async with self._connect() as db:
            await db.execute(
                "INSERT OR IGNORE INTO users (discord_id, username, cash_balance) VALUES (?, ?, ?)",
                (discord_id, username, config.INITIAL_CASH),
            )
            if username:
                await db.execute(
                    "UPDATE users SET username = ? WHERE discord_id = ? AND (username IS NULL OR username != ?)",
                    (username, discord_id, username),
                )
            await db.commit()

    async def get_user(self, discord_id: int) -> dict | None:
        async with self._connect() as db:
            cur = await db.execute("SELECT * FROM users WHERE discord_id = ?", (discord_id,))
            row = await cur.fetchone()
            return dict(row) if row else None

    async def get_user_balance(self, discord_id: int) -> float:
        await self.ensure_user(discord_id)
        async with self._connect() as db:
            cur = await db.execute(
                "SELECT cash_balance FROM users WHERE discord_id = ?", (discord_id,)
            )
            row = await cur.fetchone()
            return row["cash_balance"] if row else config.INITIAL_CASH

    async def update_user_balance(self, discord_id: int, new_balance: float):
        async with self._connect() as db:
            await db.execute(
                "UPDATE users SET cash_balance = ? WHERE discord_id = ?",
                (new_balance, discord_id),
            )
            await db.commit()

    async def increment_user_balance(self, discord_id: int, delta: float):
        """Atomically add (or subtract if negative) from user's balance."""
        async with self._connect() as db:
            await db.execute(
                "UPDATE users SET cash_balance = cash_balance + ? WHERE discord_id = ?",
                (delta, discord_id),
            )
            await db.commit()

    async def get_all_users(self) -> list[dict]:
        async with self._connect() as db:
            cur = await db.execute("SELECT * FROM users")
            return [dict(r) for r in await cur.fetchall()]

    # ── Portfolio ───────────────────────────────────────────────────

    async def get_user_portfolio(self, discord_id: int) -> list[dict]:
        async with self._connect() as db:
            cur = await db.execute(
                "SELECT ticker, shares, avg_purchase_price, acquired_at "
                "FROM portfolios WHERE user_id = ? AND shares > 0",
                (discord_id,),
            )
            return [dict(r) for r in await cur.fetchall()]

    async def upsert_portfolio(self, discord_id: int, ticker: str, shares: float, price: float, *, db=None):
        """Add shares to portfolio with weighted-average cost basis. Uses provided db connection for atomicity."""
        async def _exec(conn):
            cur = await conn.execute(
                "SELECT shares, avg_purchase_price FROM portfolios WHERE user_id = ? AND ticker = ?",
                (discord_id, ticker),
            )
            row = await cur.fetchone()
            if row:
                old_shares = row["shares"]
                old_avg = row["avg_purchase_price"]
                new_total = old_shares + shares
                new_avg = ((old_shares * old_avg) + (shares * price)) / new_total if new_total else 0
                await conn.execute(
                    "UPDATE portfolios SET shares = ?, avg_purchase_price = ? WHERE user_id = ? AND ticker = ?",
                    (new_total, new_avg, discord_id, ticker),
                )
            else:
                await conn.execute(
                    "INSERT INTO portfolios (user_id, ticker, shares, avg_purchase_price) VALUES (?, ?, ?, ?)",
                    (discord_id, ticker, shares, price),
                )

        if db:
            await _exec(db)
        else:
            async with self._connect() as conn:
                await _exec(conn)
                await conn.commit()

    async def reduce_portfolio(self, discord_id: int, ticker: str, shares: float, *, db=None):
        async def _exec(conn):
            cur = await conn.execute(
                "SELECT shares FROM portfolios WHERE user_id = ? AND ticker = ?",
                (discord_id, ticker),
            )
            row = await cur.fetchone()
            if not row or row["shares"] < shares:
                raise ValueError(f"Insufficient holdings of {ticker}")
            remaining = row["shares"] - shares
            if remaining <= 0:
                await conn.execute(
                    "DELETE FROM portfolios WHERE user_id = ? AND ticker = ?",
                    (discord_id, ticker),
                )
            else:
                await conn.execute(
                    "UPDATE portfolios SET shares = ? WHERE user_id = ? AND ticker = ?",
                    (remaining, discord_id, ticker),
                )

        if db:
            await _exec(db)
        else:
            async with self._connect() as conn:
                await _exec(conn)
                await conn.commit()

    # ── Transactions ────────────────────────────────────────────────

    async def add_transaction(self, discord_id: int, ticker: str, tx_type: str,
                              shares: float, price: float, *, db=None):
        total = shares * price

        async def _exec(conn):
            await conn.execute(
                "INSERT INTO transactions (user_id, ticker, type, shares, price, total) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (discord_id, ticker, tx_type, shares, price, total),
            )

        if db:
            await _exec(db)
        else:
            async with self._connect() as conn:
                await _exec(conn)
                await conn.commit()

    async def get_user_transactions(self, discord_id: int, limit: int | None = None) -> list[dict]:
        limit = limit or config.MAX_HISTORY_RESULTS
        async with self._connect() as db:
            cur = await db.execute(
                "SELECT * FROM transactions WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (discord_id, limit),
            )
            return [dict(r) for r in await cur.fetchall()]

    async def count_user_transactions(self, discord_id: int) -> int:
        async with self._connect() as db:
            cur = await db.execute(
                "SELECT COUNT(*) as cnt FROM transactions WHERE user_id = ?", (discord_id,)
            )
            row = await cur.fetchone()
            return row["cnt"] if row else 0

    async def count_user_transactions_today(self, discord_id: int) -> int:
        async with self._connect() as db:
            cur = await db.execute(
                "SELECT COUNT(*) as cnt FROM transactions "
                "WHERE user_id = ? AND date(timestamp) = date('now')",
                (discord_id,),
            )
            row = await cur.fetchone()
            return row["cnt"] if row else 0

    # ── Stocks ──────────────────────────────────────────────────────

    async def get_stock(self, ticker: str) -> dict | None:
        async with self._connect() as db:
            cur = await db.execute("SELECT * FROM stocks WHERE ticker = ?", (ticker,))
            row = await cur.fetchone()
            return dict(row) if row else None

    async def upsert_stock(self, ticker: str, price: float, *,
                           name: str | None = None, volume: int = 0,
                           sector: str | None = None):
        async with self._connect() as db:
            cur = await db.execute("SELECT price FROM stocks WHERE ticker = ?", (ticker,))
            existing = await cur.fetchone()
            prev = existing["price"] if existing else price
            await db.execute(
                "INSERT INTO stocks (ticker, name, price, previous_price, volume, sector, last_updated) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(ticker) DO UPDATE SET "
                "price=excluded.price, previous_price=?, "
                "volume=COALESCE(excluded.volume, stocks.volume), "
                "name=COALESCE(excluded.name, stocks.name), "
                "sector=COALESCE(excluded.sector, stocks.sector), "
                "last_updated=excluded.last_updated",
                (ticker, name or ticker, price, prev, volume, sector, time.time(), prev),
            )
            await db.commit()

    async def get_all_stocks(self) -> list[dict]:
        async with self._connect() as db:
            cur = await db.execute(
                "SELECT * FROM stocks ORDER BY ticker"
            )
            return [dict(r) for r in await cur.fetchall()]

    async def remove_stock(self, ticker: str):
        async with self._connect() as db:
            await db.execute("DELETE FROM stocks WHERE ticker = ?", (ticker,))
            await db.commit()

    # ── Leaderboard ─────────────────────────────────────────────────

    async def update_leaderboard_entry(self, discord_id: int, net_worth: float,
                                       profit: float, rank: int):
        async with self._connect() as db:
            await db.execute(
                "INSERT INTO leaderboard (user_id, net_worth, profit, rank, updated_at) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET "
                "net_worth=excluded.net_worth, profit=excluded.profit, "
                "rank=excluded.rank, updated_at=excluded.updated_at",
                (discord_id, net_worth, profit, rank, time.time()),
            )
            await db.commit()

    async def get_leaderboard(self, limit: int = 10) -> list[dict]:
        async with self._connect() as db:
            cur = await db.execute(
                "SELECT user_id, net_worth, profit, rank FROM leaderboard ORDER BY rank LIMIT ?",
                (limit,),
            )
            return [dict(r) for r in await cur.fetchall()]

    async def get_user_rank(self, discord_id: int) -> dict | None:
        async with self._connect() as db:
            cur = await db.execute(
                "SELECT user_id, net_worth, profit, rank FROM leaderboard WHERE user_id = ?",
                (discord_id,),
            )
            row = await cur.fetchone()
            return dict(row) if row else None

    # ── Achievements ────────────────────────────────────────────────

    async def add_achievement(self, discord_id: int, achievement_id: str) -> bool:
        async with self._connect() as db:
            try:
                await db.execute(
                    "INSERT INTO achievements (user_id, achievement_id) VALUES (?, ?)",
                    (discord_id, achievement_id),
                )
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                return False

    async def get_user_achievements(self, discord_id: int) -> list[dict]:
        async with self._connect() as db:
            cur = await db.execute(
                "SELECT achievement_id, earned_at FROM achievements "
                "WHERE user_id = ? ORDER BY earned_at DESC",
                (discord_id,),
            )
            return [dict(r) for r in await cur.fetchall()]

    async def has_achievement(self, discord_id: int, achievement_id: str) -> bool:
        async with self._connect() as db:
            cur = await db.execute(
                "SELECT 1 FROM achievements WHERE user_id = ? AND achievement_id = ?",
                (discord_id, achievement_id),
            )
            return await cur.fetchone() is not None

    # ── Market Events ───────────────────────────────────────────────

    async def add_market_event(self, event_type: str, description: str,
                               multiplier: float, affected_tickers: list[str],
                               duration: int) -> int:
        now = time.time()
        async with self._connect() as db:
            cur = await db.execute(
                "INSERT INTO market_events "
                "(event_type, description, multiplier, affected_tickers, duration, created_at, expires_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (event_type, description, multiplier, json.dumps(affected_tickers),
                 duration, now, now + duration),
            )
            await db.commit()
            return cur.lastrowid

    async def get_active_events(self) -> list[dict]:
        async with self._connect() as db:
            cur = await db.execute(
                "SELECT * FROM market_events WHERE expires_at > ?", (time.time(),)
            )
            rows = [dict(r) for r in await cur.fetchall()]
            for r in rows:
                if r.get("affected_tickers"):
                    try:
                        r["affected_tickers"] = json.loads(r["affected_tickers"])
                    except (json.JSONDecodeError, TypeError):
                        r["affected_tickers"] = []
            return rows

    async def expire_events(self) -> int:
        async with self._connect() as db:
            cur = await db.execute(
                "DELETE FROM market_events WHERE expires_at <= ?", (time.time(),)
            )
            await db.commit()
            return cur.rowcount

    # ── Limit Orders ───────────────────────────────────────────────

    async def add_limit_order(self, discord_id: int, ticker: str, order_type: str,
                              target_price: float, shares: int) -> int:
        async with self._connect() as db:
            cur = await db.execute(
                "INSERT INTO limit_orders (user_id, ticker, order_type, target_price, shares) "
                "VALUES (?, ?, ?, ?, ?)",
                (discord_id, ticker, order_type, target_price, shares),
            )
            await db.commit()
            return cur.lastrowid

    async def get_pending_limit_orders(self) -> list[dict]:
        async with self._connect() as db:
            cur = await db.execute(
                "SELECT * FROM limit_orders WHERE status = 'pending' ORDER BY created_at"
            )
            return [dict(r) for r in await cur.fetchall()]

    async def get_user_limit_orders(self, discord_id: int) -> list[dict]:
        async with self._connect() as db:
            cur = await db.execute(
                "SELECT * FROM limit_orders WHERE user_id = ? ORDER BY created_at DESC LIMIT 20",
                (discord_id,),
            )
            return [dict(r) for r in await cur.fetchall()]

    async def fill_limit_order(self, order_id: int):
        async with self._connect() as db:
            await db.execute(
                "UPDATE limit_orders SET status = 'filled', filled_at = datetime('now') WHERE id = ?",
                (order_id,),
            )
            await db.commit()

    async def cancel_limit_order(self, order_id: int, discord_id: int) -> bool:
        async with self._connect() as db:
            cur = await db.execute(
                "UPDATE limit_orders SET status = 'cancelled' "
                "WHERE id = ? AND user_id = ? AND status = 'pending'",
                (order_id, discord_id),
            )
            await db.commit()
            return cur.rowcount > 0

    # ── Short Positions ─────────────────────────────────────────────

    async def add_short_position(self, discord_id: int, ticker: str,
                                 shares: float, borrow_price: float, *, db=None) -> int:
        async def _exec(conn):
            cur = await conn.execute(
                "INSERT INTO short_positions (user_id, ticker, shares, borrow_price) "
                "VALUES (?, ?, ?, ?)",
                (discord_id, ticker, shares, borrow_price),
            )
            return cur.lastrowid

        if db:
            return await _exec(db)
        async with self._connect() as conn:
            rid = await _exec(conn)
            await conn.commit()
            return rid

    async def get_user_shorts(self, discord_id: int) -> list[dict]:
        async with self._connect() as db:
            cur = await db.execute(
                "SELECT * FROM short_positions WHERE user_id = ? AND closed = 0",
                (discord_id,),
            )
            return [dict(r) for r in await cur.fetchall()]

    async def get_short_position(self, position_id: int, discord_id: int) -> dict | None:
        async with self._connect() as db:
            cur = await db.execute(
                "SELECT * FROM short_positions WHERE id = ? AND user_id = ? AND closed = 0",
                (position_id, discord_id),
            )
            row = await cur.fetchone()
            return dict(row) if row else None

    async def close_short_position(self, position_id: int, *, db=None):
        async def _exec(conn):
            await conn.execute(
                "UPDATE short_positions SET closed = 1 WHERE id = ?", (position_id,)
            )

        if db:
            await _exec(db)
        else:
            async with self._connect() as conn:
                await _exec(conn)
                await conn.commit()

    # ── Options ─────────────────────────────────────────────────────

    async def add_option(self, discord_id: int, ticker: str, option_type: str,
                         strike_price: float, premium: float, expiry: str, *, db=None) -> int:
        async def _exec(conn):
            cur = await conn.execute(
                "INSERT INTO options (user_id, ticker, option_type, strike_price, premium, expiry) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (discord_id, ticker, option_type, strike_price, premium, expiry),
            )
            return cur.lastrowid

        if db:
            return await _exec(db)
        async with self._connect() as conn:
            rid = await _exec(conn)
            await conn.commit()
            return rid

    async def get_user_options(self, discord_id: int) -> list[dict]:
        async with self._connect() as db:
            cur = await db.execute(
                "SELECT * FROM options WHERE user_id = ? ORDER BY created_at DESC",
                (discord_id,),
            )
            return [dict(r) for r in await cur.fetchall()]

    async def get_active_options(self) -> list[dict]:
        async with self._connect() as db:
            cur = await db.execute(
                "SELECT * FROM options WHERE status = 'active'"
            )
            return [dict(r) for r in await cur.fetchall()]

    async def update_option_status(self, option_id: int, status: str):
        async with self._connect() as db:
            await db.execute(
                "UPDATE options SET status = ? WHERE id = ?", (status, option_id)
            )
            await db.commit()

    # ── Dividends ───────────────────────────────────────────────────

    async def get_recent_dividends(self, limit: int = 10) -> list[dict]:
        async with self._connect() as db:
            cur = await db.execute(
                "SELECT * FROM dividends ORDER BY pay_date DESC LIMIT ?", (limit,)
            )
            return [dict(r) for r in await cur.fetchall()]

    # ── Daily ───────────────────────────────────────────────────────

    async def get_last_daily(self, discord_id: int) -> str | None:
        async with self._connect() as db:
            cur = await db.execute(
                "SELECT last_daily FROM users WHERE discord_id = ?", (discord_id,)
            )
            row = await cur.fetchone()
            return row["last_daily"] if row else None

    async def set_daily_claimed(self, discord_id: int):
        now = datetime.now(timezone.utc).isoformat()
        async with self._connect() as db:
            await db.execute(
                "UPDATE users SET last_daily = ? WHERE discord_id = ?", (now, discord_id)
            )
            await db.commit()

    # ── Atomic Trading Helpers ──────────────────────────────────────

    async def execute_buy(self, discord_id: int, ticker: str,
                          shares: int, price: float) -> dict:
        total_cost = shares * price
        async with self.transaction() as db:
            cur = await db.execute(
                "SELECT cash_balance FROM users WHERE discord_id = ?", (discord_id,)
            )
            row = await cur.fetchone()
            if not row:
                raise ValueError("User not found")
            if row["cash_balance"] < total_cost:
                raise ValueError(
                    f"Insufficient funds. Need {total_cost:,.2f} but have {row['cash_balance']:,.2f}"
                )
            new_balance = row["cash_balance"] - total_cost
            await db.execute(
                "UPDATE users SET cash_balance = ? WHERE discord_id = ?",
                (new_balance, discord_id),
            )
            await self.upsert_portfolio(discord_id, ticker, shares, price, db=db)
            await self.add_transaction(discord_id, ticker, "buy", shares, price, db=db)

        return {"shares": shares, "price": price, "total": total_cost, "new_balance": new_balance}

    async def execute_sell(self, discord_id: int, ticker: str,
                           shares: int, price: float) -> dict:
        total_value = shares * price
        async with self.transaction() as db:
            cur = await db.execute(
                "SELECT shares, avg_purchase_price FROM portfolios WHERE user_id = ? AND ticker = ?",
                (discord_id, ticker),
            )
            row = await cur.fetchone()
            if not row or row["shares"] < shares:
                owned = row["shares"] if row else 0
                raise ValueError(
                    f"Insufficient holdings. Own {owned:.0f} shares of {ticker}"
                )
            avg_cost = row["avg_purchase_price"]
            await self.reduce_portfolio(discord_id, ticker, shares, db=db)

            cur2 = await db.execute(
                "SELECT cash_balance FROM users WHERE discord_id = ?", (discord_id,)
            )
            urow = await cur2.fetchone()
            new_balance = urow["cash_balance"] + total_value
            await db.execute(
                "UPDATE users SET cash_balance = ? WHERE discord_id = ?",
                (new_balance, discord_id),
            )
            await self.add_transaction(discord_id, ticker, "sell", shares, price, db=db)

        profit = (price - avg_cost) * shares
        return {
            "shares": shares, "price": price, "total": total_value,
            "new_balance": new_balance, "profit": profit, "avg_cost": avg_cost,
        }

    async def execute_short(self, discord_id: int, ticker: str,
                            shares: int, price: float) -> dict:
        margin_required = shares * price * config.SHORT_MARGIN_PCT
        proceeds = shares * price
        async with self.transaction() as db:
            cur = await db.execute(
                "SELECT cash_balance FROM users WHERE discord_id = ?", (discord_id,)
            )
            row = await cur.fetchone()
            if not row or row["cash_balance"] < margin_required:
                raise ValueError(
                    f"Insufficient margin. Need {margin_required:,.2f} (150% of position value)"
                )
            new_balance = row["cash_balance"] + proceeds - margin_required
            await db.execute(
                "UPDATE users SET cash_balance = ? WHERE discord_id = ?",
                (new_balance, discord_id),
            )
            await self.add_short_position(discord_id, ticker, shares, price, db=db)
            await self.add_transaction(discord_id, ticker, "short", shares, price, db=db)

        return {
            "shares": shares, "borrow_price": price, "margin": margin_required,
            "proceeds": proceeds, "new_balance": new_balance,
        }

    async def execute_cover(self, discord_id: int, position_id: int,
                            current_price: float) -> dict:
        async with self.transaction() as db:
            cur = await db.execute(
                "SELECT * FROM short_positions WHERE id = ? AND user_id = ? AND closed = 0",
                (position_id, discord_id),
            )
            pos = await cur.fetchone()
            if not pos:
                raise ValueError("Short position not found or already closed")
            pos = dict(pos)
            cover_cost = pos["shares"] * current_price
            margin_return = pos["shares"] * pos["borrow_price"] * config.SHORT_MARGIN_PCT
            profit = (pos["borrow_price"] - current_price) * pos["shares"]

            cur2 = await db.execute(
                "SELECT cash_balance FROM users WHERE discord_id = ?", (discord_id,)
            )
            urow = await cur2.fetchone()
            new_balance = urow["cash_balance"] - cover_cost + margin_return
            if new_balance < 0:
                raise ValueError("Insufficient funds to cover short position")
            await db.execute(
                "UPDATE users SET cash_balance = ? WHERE discord_id = ?",
                (new_balance, discord_id),
            )
            await self.close_short_position(position_id, db=db)
            await self.add_transaction(
                discord_id, pos["ticker"], "cover", pos["shares"], current_price, db=db
            )

        return {
            "ticker": pos["ticker"], "shares": pos["shares"],
            "borrow_price": pos["borrow_price"], "cover_price": current_price,
            "profit": profit, "new_balance": new_balance,
        }

    # ── Stock Split Helper ──────────────────────────────────────────

    async def apply_stock_split(self, ticker: str, ratio: int):
        async with self.transaction() as db:
            cur = await db.execute("SELECT price FROM stocks WHERE ticker = ?", (ticker,))
            stock = await cur.fetchone()
            if not stock:
                return
            new_price = stock["price"] / ratio
            await db.execute(
                "UPDATE stocks SET price = ?, previous_price = ? WHERE ticker = ?",
                (new_price, stock["price"], ticker),
            )
            await db.execute(
                "UPDATE portfolios SET shares = shares * ?, avg_purchase_price = avg_purchase_price / ? "
                "WHERE ticker = ?",
                (ratio, ratio, ticker),
            )

    # ── Dividend Payout Helper ──────────────────────────────────────

    async def pay_dividends(self, ticker: str, amount_per_share: float) -> list[dict]:
        payouts = []
        async with self.transaction() as db:
            cur = await db.execute(
                "SELECT user_id, shares FROM portfolios WHERE ticker = ? AND shares > 0",
                (ticker,),
            )
            holders = await cur.fetchall()
            for holder in holders:
                payout = holder["shares"] * amount_per_share
                await db.execute(
                    "UPDATE users SET cash_balance = cash_balance + ? WHERE discord_id = ?",
                    (payout, holder["user_id"]),
                )
                await self.add_transaction(
                    holder["user_id"], ticker, "dividend", holder["shares"],
                    amount_per_share, db=db,
                )
                payouts.append({"user_id": holder["user_id"], "payout": payout})
            await self.add_dividend(ticker, amount_per_share, db=db)
        return payouts

    async def add_dividend(self, ticker: str, amount_per_share: float, *, db=None):
        async def _exec(conn):
            await conn.execute(
                "INSERT INTO dividends (ticker, amount_per_share) VALUES (?, ?)",
                (ticker, amount_per_share),
            )

        if db:
            await _exec(db)
        else:
            async with self._connect() as conn:
                await _exec(conn)
                await conn.commit()
