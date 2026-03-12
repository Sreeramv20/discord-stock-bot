import asyncio
import time
from typing import Optional, Dict, List
import config
import database

class Market:
    def __init__(self):
        self.cache = {}
        
    async def fetch_stock_data(self, symbol: str) -> Optional[Dict]:
        """Fetch stock data from external API"""
        # This would be implemented with actual API calls
        # For now, we'll simulate it with mock data
        return {
            'symbol': symbol,
            'name': f'{symbol} Company',
            'current_price': 100.0 + (hash(symbol) % 100),
            'previous_price': 95.0 + (hash(symbol) % 100),
            'volume': 1000000,
            'last_updated': time.time()
        }
    
    async def get_stock_info(self, symbol: str) -> Optional[Dict]:
        """Get stock information with caching"""
        if symbol in self.cache:
            cached_data = self.cache[symbol]
            if time.time() - cached_data['last_updated'] < config.MARKET_UPDATE_INTERVAL:
                return cached_data
        
        # Try to get from database first
        stock_info = database.get_stock_info(symbol, config.DB_PATH)
        if stock_info:
            self.cache[symbol] = stock_info
            return stock_info
            
        # If not in cache or DB, fetch from API
        stock_data = await self.fetch_stock_data(symbol)
        if stock_data:
            database.update_stock_price(symbol, stock_data['current_price'], config.DB_PATH)
            self.cache[symbol] = stock_data
            return stock_data
            
        return None
    
    async def get_all_stocks(self) -> Dict[str, Dict]:
        """Get all available stocks"""
        # Try to get from cache first
        if 'all_stocks' in self.cache:
            cached_data = self.cache['all_stocks']
            if time.time() - cached_data['last_updated'] < config.MARKET_UPDATE_INTERVAL:
                return cached_data['stocks']
        
        # Get from database
        stocks = database.get_all_stocks(config.DB_PATH)
        stocks_dict = {stock['symbol']: stock for stock in stocks}
        
        self.cache['all_stocks'] = {
            'stocks': stocks_dict,
            'last_updated': time.time()
        }
        
        return stocks_dict
    
    async def update_stock_price(self, symbol: str) -> Optional[float]:
        """Update a single stock's price"""
        # In a real implementation, this would fetch from an API
        # For now, we'll simulate price changes
        current_price = 100.0 + (hash(symbol) % 100)
        
        # Add some random fluctuation
        import random
        fluctuation = random.uniform(-5, 5)
        new_price = current_price + fluctuation
        
        database.update_stock_price(symbol, new_price, config.DB_PATH)
        return new_price
    
    async def update_all_prices(self):
        """Update prices for all stocks"""
        stocks = await self.get_all_stocks()
        tasks = [self.update_stock_price(symbol) for symbol in stocks.keys()]
        await asyncio.gather(*tasks)
    
    async def start_market_updates(self):
        """Start periodic market updates"""
        while True:
            try:
                await self.update_all_prices()
                await asyncio.sleep(config.MARKET_UPDATE_INTERVAL)
            except Exception as e:
                print(f"Error updating market prices: {e}")
                await asyncio.sleep(60)  # Wait a minute before retrying
    
    async def initialize_stocks(self):
        """Initialize default stocks in the database"""
        default_stocks = [
            {'symbol': 'AAPL', 'name': 'Apple Inc.', 'current_price': 150.0},
            {'symbol': 'MSFT', 'name': 'Microsoft Corporation', 'current_price': 300.0},
            {'symbol': 'GOOGL', 'name': 'Alphabet Inc.', 'current_price': 2800.0},
            {'symbol': 'AMZN', 'name': 'Amazon.com Inc.', 'current_price': 3400.0},
            {'symbol': 'TSLA', 'name': 'Tesla Inc.', 'current_price': 250.0}
        ]
        
        for stock in default_stocks:
            # Check if stock exists
            existing_stock = database.get_stock_info(stock['symbol'], config.DB_PATH)
            if not existing_stock:
                # Insert new stock
                database.update_stock_price(stock['symbol'], stock['current_price'], config.DB_PATH)
