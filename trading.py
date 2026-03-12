import asyncio
from typing import Optional, Dict, List, Any
import time
import database
import config

class TradingEngine:
    def __init__(self):
        self.cache = {}
        
    async def buy_stock(self, user_id: int, symbol: str, quantity: int) -> bool:
        """Buy stocks for a user"""
        # Validate inputs
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
            
        # Get stock information
        stock_info = await self.get_stock_info(symbol)
        if not stock_info:
            raise ValueError(f"Stock {symbol} not found")
            
        # Calculate total cost
        total_cost = quantity * stock_info['current_price']
        
        # Check user balance
        balance = database.get_user_balance(user_id, config.DB_PATH)
        if balance is None or balance < total_cost:
            raise ValueError("Insufficient balance")
            
        # Process the transaction
        try:
            # Deduct from user's balance
            new_balance = balance - total_cost
            database.update_user_balance(user_id, new_balance, config.DB_PATH)
            
            # Add to portfolio
            database.add_stock_to_portfolio(user_id, symbol, quantity, stock_info['current_price'])
            
            # Record transaction
            database.add_transaction(user_id, symbol, 'buy', quantity, 
                                   stock_info['current_price'], total_cost, config.DB_PATH)
            
            return True
            
        except Exception as e:
            print(f"Error processing buy order: {e}")
            return False
    
    async def sell_stock(self, user_id: int, symbol: str, quantity: int) -> bool:
        """Sell stocks for a user"""
        # Validate inputs
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
            
        # Get stock information
        stock_info = await self.get_stock_info(symbol)
        if not stock_info:
            raise ValueError(f"Stock {symbol} not found")
            
        # Check if user has enough stocks
        portfolio = database.get_user_portfolio(user_id, config.DB_PATH)
        user_stock = next((item for item in portfolio if item['symbol'] == symbol), None)
        
        if not user_stock or user_stock['quantity'] < quantity:
            raise ValueError("Insufficient stock holdings")
            
        # Calculate total value
        total_value = quantity * stock_info['current_price']
        
        # Process the transaction
        try:
            # Add to user's balance
            balance = database.get_user_balance(user_id, config.DB_PATH)
            new_balance = balance + total_value
            database.update_user_balance(user_id, new_balance, config.DB_PATH)
            
            # Remove from portfolio or reduce quantity
            database.remove_stock_from_portfolio(user_id, symbol, quantity)
            
            # Record transaction
            database.add_transaction(user_id, symbol, 'sell', quantity, 
                                   stock_info['current_price'], total_value, config.DB_PATH)
            
            return True
            
        except Exception as e:
            print(f"Error processing sell order: {e}")
            return False
    
    async def get_stock_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific stock"""
        # This would be implemented with actual market data lookup
        # For now, we'll simulate it
        return {
            'symbol': symbol,
            'name': f'{symbol} Company',
            'current_price': 100.0 + (hash(symbol) % 100),
            'previous_price': 95.0 + (hash(symbol) % 100),
            'volume': 1000000,
            'last_updated': time.time()
        }
    
    async def get_user_transactions(self, user_id: int) -> List[Dict[str, Any]]:
        """Get user's transaction history"""
        return database.get_user_transactions(user_id, config.DB_PATH)
    
    async def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user's trading statistics"""
        transactions = await self.get_user_transactions(user_id)
        
        total_buys = len([t for t in transactions if t['type'] == 'buy'])
        total_sells = len([t for t in transactions if t['type'] == 'sell'])
        
        # Calculate profit/loss
        total_profit_loss = 0.0
        for transaction in transactions:
            if transaction['type'] == 'buy':
                total_profit_loss -= transaction['total_amount']
            else:
                total_profit_loss += transaction['total_amount']
                
        return {
            'total_buys': total_buys,
            'total_sells': total_sells,
            'net_profit_loss': total_profit_loss
        }
