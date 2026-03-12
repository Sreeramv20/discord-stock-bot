import sqlite3
from database import get_db_connection
import logging

logger = logging.getLogger(__name__)

class Leaderboard:
    def __init__(self):
        self.db_path = "stock_trading.db"
        
    async def update_leaderboard(self):
        """Update the leaderboard with current net worths"""
        try:
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            # Get all users and their net worth
            cursor.execute('''
                SELECT u.id, u.balance, 
                       COALESCE(SUM(p.quantity * s.current_price), 0) as portfolio_value
                FROM users u
                LEFT JOIN portfolios p ON u.id = p.user_id
                LEFT JOIN stocks s ON p.stock_symbol = s.symbol
                GROUP BY u.id, u.balance
            ''')
            
            users = cursor.fetchall()
            
            # Calculate net worth for each user and update leaderboard
            for user in users:
                user_id = user[0]
                balance = user[1]
                portfolio_value = user[2]
                
                total_value = balance + portfolio_value
                
                # Insert or update leaderboard entry
                cursor.execute('''
                    INSERT OR REPLACE INTO leaderboard (user_id, total_value)
                    VALUES (?, ?)
                ''', (user_id, total_value))
                
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
                SELECT l.user_id, u.username, l.total_value
                FROM leaderboard l
                JOIN users u ON l.user_id = u.id
                ORDER BY l.total_value DESC
                LIMIT ?
            ''', (limit,))
            
            leaderboard = cursor.fetchall()
            return [dict(item) for item in leaderboard]
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
            
            cursor.execute('''
                SELECT COUNT(*) + 1 as rank
                FROM leaderboard l1
                WHERE l1.total_value > (
                    SELECT total_value 
                    FROM leaderboard l2 
                    WHERE l2.user_id = ?
                )
            ''', (user_id,))
            
            result = cursor.fetchone()
            return result[0] if result else 1
        except Exception as e:
            logger.error(f"Error getting user rank: {e}")
            raise
        finally:
            conn.close()
