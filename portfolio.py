import sqlite3
from database import get_db_connection
import logging

logger = logging.getLogger(__name__)

class PortfolioSystem:
    def __init__(self):
        self.db_path = "stock_trading.db"
        
    async def get_user_portfolio(self, user_id):
        """Get a user's portfolio"""
        try:
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
            return [dict(item) for item in portfolio]
        except Exception as e:
            logger.error(f"Error getting user portfolio: {e}")
            raise
        finally:
            conn.close()
            
    async def get_user_balance(self, user_id):
        """Get a user's cash balance"""
        try:
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT balance FROM users WHERE id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            return result[0] if result else 0.0
        except Exception as e:
            logger.error(f"Error getting user balance: {e}")
            raise
        finally:
            conn.close()
            
    async def get_total_portfolio_value(self, user_id):
        """Get the total value of a user's portfolio"""
        try:
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
            return result[0] if result and result[0] else 0.0
        except Exception as e:
            logger.error(f"Error getting total portfolio value: {e}")
            raise
        finally:
            conn.close()
            
    async def get_user_net_worth(self, user_id):
        """Get a user's total net worth (cash + portfolio value)"""
        try:
            balance = await self.get_user_balance(user_id)
            portfolio_value = await self.get_total_portfolio_value(user_id)
            return balance + portfolio_value
        except Exception as e:
            logger.error(f"Error getting user net worth: {e}")
            raise
            
    async def add_stock_to_portfolio(self, user_id, symbol, quantity, price):
        """Add a stock to user's portfolio or update existing position"""
        try:
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            # Check if user already has this stock
            cursor.execute('''
                SELECT quantity, avg_buy_price FROM portfolios 
                WHERE user_id = ? AND stock_symbol = ?
            ''', (user_id, symbol))
            
            existing_position = cursor.fetchone()
            
            if existing_position:
                # Update existing position
                old_quantity = existing_position['quantity']
                old_avg_price = existing_position['avg_buy_price']
                
                new_quantity = old_quantity + quantity
                new_avg_price = ((old_quantity * old_avg_price) + (quantity * price)) / new_quantity
                
                cursor.execute('''
                    UPDATE portfolios 
                    SET quantity = ?, avg_buy_price = ?
                    WHERE user_id = ? AND stock_symbol = ?
                ''', (new_quantity, new_avg_price, user_id, symbol))
            else:
                # Add new position
                cursor.execute('''
                    INSERT INTO portfolios (user_id, stock_symbol, quantity, avg_buy_price)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, symbol, quantity, price))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding stock to portfolio: {e}")
            raise
        finally:
            conn.close()
            
    async def remove_stock_from_portfolio(self, user_id, symbol, quantity):
        """Remove a stock from user's portfolio"""
        try:
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            # Check if user has this stock
            cursor.execute('''
                SELECT quantity FROM portfolios 
                WHERE user_id = ? AND stock_symbol = ?
            ''', (user_id, symbol))
            
            existing_position = cursor.fetchone()
            
            if not existing_position:
                return False
                
            current_quantity = existing_position['quantity']
            
            if quantity > current_quantity:
                return False  # Trying to sell more than owned
                
            new_quantity = current_quantity - quantity
            
            if new_quantity == 0:
                # Remove the entire position
                cursor.execute('''
                    DELETE FROM portfolios 
                    WHERE user_id = ? AND stock_symbol = ?
                ''', (user_id, symbol))
            else:
                # Update remaining quantity
                cursor.execute('''
                    UPDATE portfolios 
                    SET quantity = ?
                    WHERE user_id = ? AND stock_symbol = ?
                ''', (new_quantity, user_id, symbol))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error removing stock from portfolio: {e}")
            raise
        finally:
            conn.close()
