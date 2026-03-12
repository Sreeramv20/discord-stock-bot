import sqlite3
from datetime import datetime
import logging
from database import get_db_connection

logger = logging.getLogger(__name__)

class TradingEngine:
    def __init__(self):
        self.db_path = "stock_trading.db"
        
    async def buy_stock(self, user_id, symbol, quantity):
        """Buy stocks for a user"""
        try:
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            # Get stock info
            cursor.execute('''
                SELECT current_price FROM stocks WHERE symbol = ?
            ''', (symbol,))
            
            result = cursor.fetchone()
            if not result:
                return False, "Stock not found"
                
            price = result[0]
            total_cost = price * quantity
            
            # Check if user has enough balance
            cursor.execute('''
                SELECT balance FROM users WHERE id = ?
            ''', (user_id,))
            
            balance = cursor.fetchone()[0]
            
            if balance < total_cost:
                return False, "Insufficient balance"
                
            # Update user balance
            cursor.execute('''
                UPDATE users SET balance = balance - ? WHERE id = ?
            ''', (total_cost, user_id))
            
            # Check if user already owns this stock
            cursor.execute('''
                SELECT quantity, avg_buy_price FROM portfolios 
                WHERE user_id = ? AND stock_symbol = ?
            ''', (user_id, symbol))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing position
                old_quantity = existing[0]
                old_avg_price = existing[1]
                
                new_quantity = old_quantity + quantity
                new_avg_price = ((old_quantity * old_avg_price) + (quantity * price)) / new_quantity
                
                cursor.execute('''
                    UPDATE portfolios 
                    SET quantity = ?, avg_buy_price = ?
                    WHERE user_id = ? AND stock_symbol = ?
                ''', (new_quantity, new_avg_price, user_id, symbol))
            else:
                # Create new position
                cursor.execute('''
                    INSERT INTO portfolios (user_id, stock_symbol, quantity, avg_buy_price)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, symbol, quantity, price))
                
            # Record transaction
            cursor.execute('''
                INSERT INTO transactions 
                (user_id, stock_symbol, transaction_type, quantity, price, total_amount)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, symbol, 'buy', quantity, price, total_cost))
            
            conn.commit()
            return True, f"Bought {quantity} shares of {symbol} at ${price:.2f} each"
        except Exception as e:
            logger.error(f"Error buying stock: {e}")
            raise
        finally:
            conn.close()
            
    async def sell_stock(self, user_id, symbol, quantity):
        """Sell stocks for a user"""
        try:
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            # Get stock info
            cursor.execute('''
                SELECT current_price FROM stocks WHERE symbol = ?
            ''', (symbol,))
            
            result = cursor.fetchone()
            if not result:
                return False, "Stock not found"
                
            price = result[0]
            total_value = price * quantity
            
            # Check if user owns enough stock
            cursor.execute('''
                SELECT quantity FROM portfolios 
                WHERE user_id = ? AND stock_symbol = ?
            ''', (user_id, symbol))
            
            result = cursor.fetchone()
            if not result:
                return False, "You don't own this stock"
                
            owned_quantity = result[0]
            
            if owned_quantity < quantity:
                return False, f"You only own {owned_quantity} shares of {symbol}"
                
            # Update user balance
            cursor.execute('''
                UPDATE users SET balance = balance + ? WHERE id = ?
            ''', (total_value, user_id))
            
            # Update portfolio
            new_quantity = owned_quantity - quantity
            
            if new_quantity == 0:
                # Remove the position entirely
                cursor.execute('''
                    DELETE FROM portfolios 
                    WHERE user_id = ? AND stock_symbol = ?
                ''', (user_id, symbol))
            else:
                # Update quantity
                cursor.execute('''
                    UPDATE portfolios 
                    SET quantity = ? 
                    WHERE user_id = ? AND stock_symbol = ?
                ''', (new_quantity, user_id, symbol))
                
            # Record transaction
            cursor.execute('''
                INSERT INTO transactions 
                (user_id, stock_symbol, transaction_type, quantity, price, total_amount)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, symbol, 'sell', quantity, price, total_value))
            
            conn.commit()
            return True, f"Sold {quantity} shares of {symbol} at ${price:.2f} each"
        except Exception as e:
            logger.error(f"Error selling stock: {e}")
            raise
        finally:
            conn.close()
