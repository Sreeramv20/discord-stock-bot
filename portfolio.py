import sqlite3
from database import get_db_connection

class PortfolioSystem:
    def __init__(self):
        self.db_path = "stock_trading.db"
        
    async def get_user_portfolio(self, user_id):
        """Get a user's portfolio"""
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        
        # Get portfolio with stock details
        cursor.execute('''
            SELECT p.stock_symbol, p.quantity, p.avg_buy_price,
                   s.current_price, 
                   (p.quantity * s.current_price) as current_value,
                   ((p.quantity * s.current_price) - (p.quantity * p.avg_buy_price)) as profit_loss
            FROM portfolios p
            JOIN stocks s ON p.stock_symbol = s.symbol
            WHERE p.user_id = ?
            ORDER BY s.current_price DESC
        ''', (user_id,))
        
        portfolio = cursor.fetchall()
        conn.close()
        
        return [dict(item) for item in portfolio]
        
    async def get_user_balance(self, user_id):
        """Get a user's cash balance"""
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT balance FROM users WHERE id = ?
        ''', (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else 0.0
        
    async def get_total_portfolio_value(self, user_id):
        """Get the total value of a user's portfolio"""
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        
        # Get portfolio with current values
        cursor.execute('''
            SELECT SUM(p.quantity * s.current_price) as total_value
            FROM portfolios p
            JOIN stocks s ON p.stock_symbol = s.symbol
            WHERE p.user_id = ?
        ''', (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result and result[0] else 0.0
        
    async def get_user_net_worth(self, user_id):
        """Get a user's total net worth (cash + portfolio value)"""
        balance = await self.get_user_balance(user_id)
        portfolio_value = await self.get_total_portfolio_value(user_id)
        
        return balance + portfolio_value
