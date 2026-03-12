import sqlite3
import os

def init_db(db_path):
    """Initialize the database with required tables"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            balance REAL DEFAULT 10000.0,
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
            user_id INTEGER,
            stock_symbol TEXT,
            quantity INTEGER NOT NULL,
            avg_buy_price REAL NOT NULL,
            PRIMARY KEY (user_id, stock_symbol),
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (stock_symbol) REFERENCES stocks (symbol)
        )
    ''')
    
    # Create transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            stock_symbol TEXT,
            transaction_type TEXT NOT NULL, -- buy or sell
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            total_amount REAL NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (stock_symbol) REFERENCES stocks (symbol)
        )
    ''')
    
    # Create leaderboard table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leaderboard (
            user_id INTEGER PRIMARY KEY,
            total_value REAL NOT NULL,
            rank INTEGER,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db_connection(db_path):
    """Get a database connection"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
