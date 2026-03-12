import sqlite3
from database import get_db_connection
import logging

logger = logging.getLogger(__name__)

class Leaderboard:
    def __init__(self):
        self.db_path = "stock_trading.db"
        
    async def update_leaderboard(self):
        """Update the leaderboard with current net worths and profits"""
        try:
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            # Get all users with their balances, portfolio values, and initial investments
            cursor.execute('''
                SELECT 
                    u.id, 
                    u.username,
                    u.balance, 
                    COALESCE(SUM(p.quantity * s.current_price), 0) as portfolio_value,
                    COALESCE(SUM(p.quantity * p.purchase_price), 0) as total_investment
                FROM users u
                LEFT JOIN portfolios p ON u.id = p.user_id
                LEFT JOIN stocks s ON p.stock_symbol = s.symbol
                GROUP BY u.id, u.username, u.balance
            ''')
            
            users = cursor.fetchall()
            
            # Calculate net worth and profit for each user and update leaderboard
            for user in users:
                user_id = user[0]
                username = user[1]
                balance = user[2]
                portfolio_value = user[3]
                total_investment = user[4]
                
                net_worth = balance + portfolio_value
                total_profit = net_worth - total_investment
                
                # Insert or update leaderboard entry
                cursor.execute('''
                    INSERT OR REPLACE INTO leaderboard (user_id, username, net_worth, total_profit)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, username, net_worth, total_profit))
                
            conn.commit()
            logger.info("Leaderboard updated successfully")
        except Exception as e:
            logger.error(f"Error updating leaderboard: {e}")
            raise
        finally:
            conn.close()
            
    async def get_leaderboard(self, limit=10):
        """Get the top users by net worth"""
        try:
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT user_id, username, net_worth, total_profit
                FROM leaderboard
                ORDER BY net_worth DESC
                LIMIT ?
            ''', (limit,))
            
            leaderboard = cursor.fetchall()
            
            # Convert to list of dictionaries
            result = []
            for row in leaderboard:
                result.append({
                    'user_id': row[0],
                    'username': row[1],
                    'net_worth': row[2],
                    'total_profit': row[3]
                })
                
            return result
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            raise
        finally:
            conn.close()
            
    async def get_user_rank(self, user_id):
        """Get a user's rank in the leaderboard"""
        try:
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            # Get user's net worth and profit
            cursor.execute('''
                SELECT net_worth, total_profit
                FROM leaderboard
                WHERE user_id = ?
            ''', (user_id,))
            
            user_data = cursor.fetchone()
            
            if not user_data:
                return None
                
            net_worth = user_data[0]
            total_profit = user_data[1]
            
            # Calculate rank based on net worth
            cursor.execute('''
                SELECT COUNT(*) + 1 as rank
                FROM leaderboard l1
                WHERE l1.net_worth > ?
            ''', (net_worth,))
            
            result = cursor.fetchone()
            rank = result[0] if result else 1
            
            return {
                'rank': rank,
                'net_worth': net_worth,
                'total_profit': total_profit
            }
        except Exception as e:
            logger.error(f"Error getting user rank: {e}")
            raise
        finally:
            conn.close()
