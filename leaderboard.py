import asyncio
from typing import Optional, List, Dict, Any
import database
import config

class Leaderboard:
    def __init__(self):
        self.cache = {}
        
    async def update_leaderboard(self):
        """Update the leaderboard with current user rankings"""
        # Get all users and their net worth
        # This would be implemented with actual database queries
        
        # For now, we'll simulate it
        users = database.get_all_users(config.DB_PATH)  # This method needs to be added to database.py
        
        user_worths = []
        for user in users:
            worth = await self.get_user_net_worth(user['id'])
            user_worths.append({
                'user_id': user['id'],
                'username': user['username'],
                'worth': worth
            })
            
        # Sort by worth (descending)
        user_worths.sort(key=lambda x: x['worth'], reverse=True)
        
        # Update leaderboard in database
        for rank, user_data in enumerate(user_worths, 1):
            database.update_leaderboard_entry(user_data['user_id'], user_data['worth'], rank, config.DB_PATH)
            
        # Cache the results
        self.cache = {
            'leaderboard': user_worths,
            'last_updated': time.time()
        }
    
    async def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get leaderboard data"""
        # Try cache first
        if 'leaderboard' in self.cache:
            cached_data = self.cache['leaderboard']
            if time.time() - cached_data['last_updated'] < 300:  # 5 minutes cache
                return cached_data['leaderboard'][:limit]
        
        # Get from database
        leaderboard_data = database.get_leaderboard_data(config.DB_PATH)
        
        # Cache and return
        self.cache['leaderboard'] = {
            'leaderboard': leaderboard_data,
            'last_updated': time.time()
        }
        
        return leaderboard_data[:limit]
    
    async def get_user_rank(self, user_id: int) -> Optional[int]:
        """Get a user's rank in the leaderboard"""
        # Try cache first
        if 'user_rank' in self.cache:
            cached_data = self.cache['user_rank']
            if time.time() - cached_data['last_updated'] < 300:
                return cached_data.get(user_id)
        
        # Get from database
        rank = database.get_user_rank(user_id, config.DB_PATH)
        
        # Cache the result
        if 'user_rank' not in self.cache:
            self.cache['user_rank'] = {}
        self.cache['user_rank'][user_id] = rank
        self.cache['user_rank']['last_updated'] = time.time()
        
        return rank
    
    async def get_user_net_worth(self, user_id: int) -> float:
        """Get a user's net worth for leaderboard"""
        # This would be implemented with actual portfolio and balance calculations
        # For now, we'll simulate it
        return 10000.0 + (hash(str(user_id)) % 5000)
