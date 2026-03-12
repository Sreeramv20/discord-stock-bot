import sqlite3
import asyncio
import random
from datetime import datetime
from database import get_db_connection

class Market:
    def __init__(self):
        self.db_path = "stock_trading.db"
        
    async def initialize_stocks(self):
        """Initialize some default stocks in the market"""
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        
        # Sample stocks
        stocks = [
            ('AAPL', 'Apple Inc.', 150.0),
            ('MSFT', 'Microsoft Corp.', 300.0),
            ('GOOGL', 'Alphabet Inc.', 2800.0),
            ('AMZN', 'Amazon.com Inc.', 3400.0),
            ('TSLA', 'Tesla Inc.', 250.0),
        ]
        
        for symbol, name, price in stocks:
            cursor.execute('''
                INSERT OR IGNORE INTO stocks (symbol, name, current_price)
                VALUES (?, ?, ?)
            ''', (symbol, name, price))
            
        conn.commit()
        conn.close()
        
    async def get_stock_info(self, symbol):
        """Get information about a specific stock"""
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM stocks WHERE symbol = ?
        ''', (symbol,))
        
        stock = cursor.fetchone()
        conn.close()
        
        return dict(stock) if stock else None
        
    async def get_all_stocks(self):
        """Get information about all stocks"""
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM stocks ORDER BY symbol
        ''')
        
        stocks = cursor.fetchall()
        conn.close()
        
        return [dict(stock) for stock in stocks]
        
    async def update_stock_price(self, symbol):
        """Update the price of a stock randomly"""
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        
        # Get current price
        cursor.execute('''
            SELECT current_price FROM stocks WHERE symbol = ?
        ''', (symbol,))
        
        result = cursor.fetchone()
        if not result:
            conn.close()
            return None
            
        current_price = result[0]
        
        # Randomly change price by up to 10%
        change_percent = random.uniform(-0.1, 0.1)
        new_price = current_price * (1 + change_percent)
        
        # Update the database
        cursor.execute('''
            UPDATE stocks 
            SET current_price = ?, previous_price = ?, last_updated = ?
            WHERE symbol = ?
        ''', (new_price, current_price, datetime.now(), symbol))
        
        conn.commit()
        conn.close()
        
        return new_price
        
    async def update_all_prices(self):
        """Update prices for all stocks"""
        stocks = await self.get_all_stocks()
        tasks = [self.update_stock_price(stock['symbol']) for stock in stocks]
        await asyncio.gather(*tasks)
