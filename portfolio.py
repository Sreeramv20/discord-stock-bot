import asyncio
from typing import Optional, Dict, List, Any
import database
import config

class PortfolioSystem:
    def __init__(self):
        self.cache = {}
        
    async def get_user_portfolio(self, user_id: int) -> List[Dict[str, Any]]:
        """Get a user's portfolio"""
        # Try cache first
        if str(user_id) in self.cache:
            cached_data = self.cache[str(user_id)]
            if time.time() - cached_data['last_updated'] < 300:  # 5 minutes cache
                return cached_data['portfolio']
        
        # Get from database
        portfolio = database.get_user_portfolio(user_id, config.DB_PATH)
        
        # Calculate current values
        for item in portfolio:
            # This would be replaced with actual market data lookup
            item['current_value'] = item['quantity'] * item['current_price']
            item['profit_loss'] = (item['current_value'] - 
                                 (item['quantity'] * item['purchase_price']))
        
        self.cache[str(user_id)] = {
            'portfolio': portfolio,
            'last_updated': time.time()
        }
        
        return portfolio
    
    async def get_user_balance(self, user_id: int) -> Optional[float]:
        """Get user's balance"""
        return database.get_user_balance(user_id, config.DB_PATH)
    
    async def get_total_portfolio_value(self, user_id: int) -> float:
        """Calculate total portfolio value including cash"""
        balance = await self.get_user_balance(user_id)
        if balance is None:
            balance = 0.0
            
        portfolio = await self.get_user_portfolio(user_id)
        portfolio_value = sum(item['current_value'] for item in portfolio)
        
        return balance + portfolio_value
    
    async def get_user_net_worth(self, user_id: int) -> float:
        """Get user's net worth (balance + portfolio value)"""
        return await self.get_total_portfolio_value(user_id)
    
    async def get_user_performance_metrics(self, user_id: int) -> Dict[str, Any]:
        """Get performance metrics for a user"""
        portfolio = await self.get_user_portfolio(user_id)
        
        total_invested = sum(item['quantity'] * item['purchase_price'] for item in portfolio)
        total_value = sum(item['current_value'] for item in portfolio)
        total_profit_loss = total_value - total_invested
        
        # Calculate performance percentage
        if total_invested > 0:
            performance_percentage = (total_profit_loss / total_invested) * 100
        else:
            performance_percentage = 0.0
            
        return {
            'total_invested': total_invested,
            'total_value': total_value,
            'total_profit_loss': total_profit_loss,
            'performance_percentage': performance_percentage
        }
    
    async def add_stock_to_portfolio(self, user_id: int, symbol: str, quantity: int, price: float):
        """Add stock to user's portfolio"""
        # Check if user has enough balance
        balance = await self.get_user_balance(user_id)
        total_cost = quantity * price
        
        if balance is None or balance < total_cost:
            raise ValueError("Insufficient balance")
            
        # Deduct from balance
        new_balance = balance - total_cost
        database.update_user_balance(user_id, new_balance, config.DB_PATH)
        
        # Add to portfolio (this would be implemented with actual database operations)
        
    async def remove_stock_from_portfolio(self, user_id: int, symbol: str, quantity: int):
        """Remove stock from user's portfolio"""
        # Implementation would be similar to add_stock_to_portfolio but in reverse
        pass
    
    async def get_portfolio_history(self, user_id: int) -> List[Dict[str, Any]]:
        """Get portfolio history for a user"""
        # This would return historical data about the portfolio
        return []
