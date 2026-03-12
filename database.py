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
                user_id INTEGER PRIMARY KEY,
                cash_balance REAL DEFAULT 50000.0,
                last_daily_claim TIMESTAMP
            )
        ''')
        
        # Create portfolios table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolios (
                user_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                shares INTEGER NOT NULL,
                PRIMARY KEY (user_id, ticker),
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Create transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                type TEXT NOT NULL,  -- 'buy' or 'sell'
                shares INTEGER NOT NULL,
                price REAL NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Create achievements table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                achievement_name TEXT NOT NULL,
                achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
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
        cursor.execute('SELECT cash_balance FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        return result['cash_balance'] if result else None

def update_user_balance(user_id, balance, db_path):
    """Update user's balance in database"""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET cash_balance = ? WHERE user_id = ?', (balance, user_id))
        conn.commit()

def get_user_portfolio(user_id, db_path):
    """Get user's portfolio from database"""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ticker, shares FROM portfolios WHERE user_id = ?
        ''', (user_id,))
        return [dict(row) for row in cursor.fetchall()]

def add_transaction(user_id, symbol, transaction_type, quantity, 
                   price, total_amount, db_path):
    """Add a transaction to the database"""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO transactions (user_id, ticker, type, shares, price)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, symbol, transaction_type, quantity, price))
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

def add_stock_to_portfolio(user_id, symbol, quantity):
    """Add stock to user's portfolio"""
    # This function would be implemented based on the new schema
    pass

def remove_stock_from_portfolio(user_id, symbol, quantity):
    """Remove stock from user's portfolio"""
    # This function would be implemented based on the new schema
    pass

def get_all_users(db_path):
    """Get all users from database"""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, cash_balance FROM users')
        return [dict(row) for row in cursor.fetchall()]
