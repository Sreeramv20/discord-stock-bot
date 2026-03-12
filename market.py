import yfinance as yf
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class Market:
    def __init__(self):
        self.cache = {}
        self.cache_duration = 60  # 60 seconds
        
    async def fetch_stock_data(self, symbol: str) -> Optional[Dict]:
        """Fetch stock data using yfinance with caching"""
        # Check if data is cached and still valid
        if symbol in self.cache:
            cached_data, timestamp = self.cache[symbol]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_duration):
                logger.debug(f"Using cached data for {symbol}")
                return cached_data
        
        try:
            # Fetch data from yfinance
            stock = yf.Ticker(symbol)
            info = stock.info
            
            # Extract required information
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            previous_close = info.get('previousClose')
            company_name = info.get('longName', symbol)
            
            # Calculate daily change percentage
            if current_price and previous_close:
                daily_change_percent = ((current_price - previous_close) / previous_close) * 100
            else:
                daily_change_percent = 0.0
            
            data = {
                'symbol': symbol,
                'company_name': company_name,
                'current_price': current_price,
                'daily_change_percent': daily_change_percent,
                'last_updated': datetime.now().isoformat()
            }
            
            # Cache the data
            self.cache[symbol] = (data, datetime.now())
            logger.info(f"Fetched and cached data for {symbol}")
            return data
            
        except Exception as e:
            logger.error(f"Error fetching stock data for {symbol}: {e}")
            return None
    
    async def get_stock_info(self, symbol: str) -> Optional[Dict]:
        """Get information about a specific stock"""
        return await self.fetch_stock_data(symbol)
    
    async def get_all_stocks(self) -> Dict[str, Dict]:
        """Get information about all stocks (mock implementation for now)"""
        # This would be implemented based on your specific requirements
        # For now, returning empty dict as we're focusing on fetching data
        return {}
    
    async def update_stock_price(self, symbol: str) -> Optional[float]:
        """Update the price of a stock (mock implementation using cached data)"""
        data = await self.fetch_stock_data(symbol)
        return data['current_price'] if data else None
    
    async def update_all_prices(self):
        """Update prices for all stocks (mock implementation)"""
        # This would be implemented based on your specific requirements
        pass
