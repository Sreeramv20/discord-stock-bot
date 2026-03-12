import sqlite3
from contextlib import contextmanager
import logging
import config

logger = logging.getLogger(__name__)

def init_db(db_path):
    """Initialize the database with required tables"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                balance REAL DEFAULT 50000.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create stocks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stocks (
                symbol TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                current_price REAL NOT NULL,
                previous_price REAL,
                volume INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create user portfolios table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                purchase_price REAL NOT NULL,
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (symbol) REFERENCES stocks (symbol)
            )
        ''')
        
        # Create transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                type TEXT NOT NULL,  -- 'buy' or 'sell'
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                total_amount REAL NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (symbol) REFERENCES stocks (symbol)
            )
        ''')
        
        # Create leaderboard table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leaderboard (
                user_id INTEGER PRIMARY KEY,
                total_worth REAL NOT NULL,
                rank INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Create competitions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS competitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create competition participants table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS competition_participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                competition_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                score REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (competition_id) REFERENCES competitions (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Create AI traders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_traders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                strategy TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                balance REAL DEFAULT 50000.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Create options table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS options (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                option_type TEXT NOT NULL,  -- 'call' or 'put'
                strike_price REAL NOT NULL,
                expiry_time TIMESTAMP NOT NULL,
                current_price REAL NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (symbol) REFERENCES stocks (symbol)
            )
        ''')
        
        # Create option purchases table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS option_purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                option_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                purchase_price REAL NOT NULL,
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (option_id) REFERENCES options (id)
            )
        ''')
        
        # Create market events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                description TEXT NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise
    finally:
        conn.close()

@contextmanager
def get_db_connection(db_path):
    """Get a database connection"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        yield conn
    except Exception as e:
        logger.error(f"Error creating database connection: {e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()

def get_user_balance(user_id, db_path):
    """Get user's balance from database"""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT balance FROM users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        return result['balance'] if result else None

def update_user_balance(user_id, balance, db_path):
    """Update user's balance in database"""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET balance = ? WHERE id = ?', (balance, user_id))
        conn.commit()

def get_user_portfolio(user_id, db_path):
    """Get user's portfolio from database"""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.symbol, p.quantity, p.purchase_price, s.current_price
            FROM portfolios p
            JOIN stocks s ON p.symbol = s.symbol
            WHERE p.user_id = ?
        ''', (user_id,))
        return [dict(row) for row in cursor.fetchall()]

def get_all_stocks(db_path):
    """Get all stocks from database"""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM stocks')
        return [dict(row) for row in cursor.fetchall()]

def update_stock_price(symbol, price, db_path):
    """Update stock price in database"""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE stocks 
            SET current_price = ?, previous_price = COALESCE(previous_price, ?), last_updated = CURRENT_TIMESTAMP
            WHERE symbol = ?
        ''', (price, price, symbol))
        conn.commit()

def add_transaction(user_id, symbol, transaction_type, quantity, 
                   price, total_amount, db_path):
    """Add a transaction to the database"""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO transactions (user_id, symbol, type, quantity, price, total_amount)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, symbol, transaction_type, quantity, price, total_amount))
        conn.commit()

def get_user_transactions(user_id, db_path):
    """Get user's transaction history"""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM transactions 
            WHERE user_id = ? 
            ORDER BY timestamp DESC
        ''', (user_id,))
        return [dict(row) for row in cursor.fetchall()]

def create_competition(name, start_time, end_time, db_path):
    """Create a new competition"""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO competitions (name, start_time, end_time)
            VALUES (?, ?, ?)
        ''', (name, start_time, end_time))
        conn.commit()

def get_active_competitions(db_path):
    """Get all active competitions"""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM competitions WHERE is_active = 1')
        return [dict(row) for row in cursor.fetchall()]

def add_competition_participant(competition_id, user_id, db_path):
    """Add a user to a competition"""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO competition_participants (competition_id, user_id)
            VALUES (?, ?)
        ''', (competition_id, user_id))
        conn.commit()

def update_competition_score(competition_id, user_id, score, db_path):
    """Update a user's score in a competition"""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE competition_participants 
            SET score = ?
            WHERE competition_id = ? AND user_id = ?
        ''', (score, competition_id, user_id))
        conn.commit()

def create_ai_trader(user_id, strategy, risk_level, db_path):
    """Create a new AI trader"""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO ai_traders (user_id, strategy, risk_level)
            VALUES (?, ?, ?)
        ''', (user_id, strategy, risk_level))
        conn.commit()

def get_ai_trader(user_id, db_path):
    """Get AI trader information"""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM ai_traders WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        return dict(result) if result else None

def create_option(symbol, option_type, strike_price, 
                  expiry_time, current_price, db_path):
    """Create a new option"""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO options (symbol, option_type, strike_price, expiry_time, current_price)
            VALUES (?, ?, ?, ?, ?)
        ''', (symbol, option_type, strike_price, expiry_time, current_price))
        conn.commit()

def get_active_options(db_path):
    """Get all active options"""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM options WHERE is_active = 1')
        return [dict(row) for row in cursor.fetchall()]

def add_option_purchase(user_id, option_id, quantity, 
                       purchase_price, db_path):
    """Record an option purchase"""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO option_purchases (user_id, option_id, quantity, purchase_price)
            VALUES (?, ?, ?, ?)
        ''', (user_id, option_id, quantity, purchase_price))
        conn.commit()

def get_user_option_purchases(user_id, db_path):
    """Get user's option purchases"""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT op.*, o.option_type, o.strike_price, o.expiry_time
            FROM option_purchases op
            JOIN options o ON op.option_id = o.id
            WHERE op.user_id = ?
        ''', (user_id,))
        return [dict(row) for row in cursor.fetchall()]

def create_market_event(event_type, description, start_time, 
                       end_time, db_path):
    """Create a new market event"""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO market_events (event_type, description, start_time, end_time)
            VALUES (?, ?, ?, ?)
        ''', (event_type, description, start_time, end_time))
        conn.commit()

def get_active_market_events(db_path):
    """Get all active market events"""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM market_events WHERE is_active = 1')
        return [dict(row) for row in cursor.fetchall()]

def get_all_users(db_path):
    """Get all users from database"""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, balance FROM users')
        return [dict(row) for row in cursor.fetchall()]

def update_leaderboard_entry(user_id, total_worth, rank, db_path):
    """Update leaderboard entry"""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO leaderboard (user_id, total_worth, rank, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (user_id, total_worth, rank))
        conn.commit()

def get_leaderboard_data(db_path):
    """Get leaderboard data"""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.id as user_id, u.username, l.total_worth, l.rank
            FROM leaderboard l
            JOIN users u ON l.user_id = u.id
            ORDER BY l.rank
        ''')
        return [dict(row) for row in cursor.fetchall()]

def get_user_rank(user_id, db_path):
    """Get user's rank from leaderboard"""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT rank FROM leaderboard WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        return result['rank'] if result else None

def get_stock_info(symbol, db_path):
    """Get stock information from database"""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM stocks WHERE symbol = ?', (symbol,))
        result = cursor.fetchone()
        return dict(result) if result else None
