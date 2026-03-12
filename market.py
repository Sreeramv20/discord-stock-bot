import asyncio
import time
from typing import Optional, Dict, List
import config
import database
import yfinance as yf
import random

class Market:
    def __init__(self):
        self.cache = {}
        self.active_events = {}  # {event_name: {expiry_time: float}}
        
    async def fetch_stock_data(self, symbol: str) -> Optional[Dict]:
        """Fetch stock data from external API"""
        try:
            # Fetch data using yfinance
            stock = yf.Ticker(symbol)
            info = stock.info
            
            # Get current price and previous close
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            previous_close = info.get('previousClose')
            
            if not current_price:
                return None
                
            # Calculate change and percent change
            change = 0.0
            percent_change = 0.0
            
            if previous_close:
                change = current_price - previous_close
                percent_change = (change / previous_close) * 100
            
            return {
                'symbol': symbol,
                'name': info.get('longName', symbol),
                'current_price': current_price,
                'previous_price': previous_close,
                'change': change,
                'percent_change': percent_change,
                'volume': info.get('volume', 0),
                'last_updated': time.time()
            }
        except Exception as e:
            print(f"Error fetching stock data for {symbol}: {e}")
            return None
    
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
    
    async def get_price_multiplier(self, symbol: str) -> float:
        """Get the current price multiplier for a stock based on active events"""
        # Check if any events are affecting this stock
        multiplier = 1.0
        
        # Apply event multipliers (if any)
        for event_name, event_data in self.active_events.items():
            if 'affected_stocks' in event_data and symbol in event_data['affected_stocks']:
                multiplier *= event_data['multiplier']
                
        return multiplier
    
    async def update_stock_price(self, symbol: str) -> Optional[float]:
        """Update a single stock's price"""
        # In a real implementation, this would fetch from an API
        # For now, we'll simulate price changes
        current_price = 100.0 + (hash(symbol) % 100)
        
        # Add some random fluctuation
        import random
        fluctuation = random.uniform(-5, 5)
        new_price = current_price + fluctuation
        
        # Apply event multipliers
        multiplier = await self.get_price_multiplier(symbol)
        new_price *= multiplier
        
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
                # Check for expired events
                current_time = time.time()
                expired_events = []
                for event_name, event_data in self.active_events.items():
                    if current_time > event_data['expiry_time']:
                        expired_events.append(event_name)
                
                # Remove expired events
                for event_name in expired_events:
                    del self.active_events[event_name]
                    print(f"Event {event_name} has ended")
                
                # Occasionally trigger a new random event
                if random.random() < 0.1:  # 10% chance per update cycle
                    await self.trigger_random_event()
                
                await self.update_all_prices()
                await asyncio.sleep(config.MARKET_UPDATE_INTERVAL)
            except Exception as e:
                print(f"Error updating market prices: {e}")
                await asyncio.sleep(60)  # Wait a minute before retrying
    
    async def trigger_random_event(self):
        """Trigger a random market event"""
        events = [
            {
                'name': 'tech_crash',
                'description': 'Tech sector crash! Prices dropping rapidly.',
                'multiplier': 0.7,  # 30% reduction
                'duration': 120,  # 2 minutes
                'affected_stocks': ['AAPL', 'MSFT', 'GOOGL', 'TSLA']
            },
            {
                'name': 'energy_rally',
                'description': 'Energy sector rally! Prices soaring.',
                'multiplier': 1.5,  # 50% increase
                'duration': 180,  # 3 minutes
                'affected_stocks': ['XOM', 'CVX', 'RDS-A', 'BP']
            },
            {
                'name': 'market_boom',
                'description': 'Market boom! All stocks rising.',
                'multiplier': 1.3,  # 30% increase
                'duration': 150,  # 2.5 minutes
                'affected_stocks': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
            },
            {
                'name': 'economic_uncertainty',
                'description': 'Economic uncertainty! Market volatility increasing.',
                'multiplier': 1.2,  # 20% increase
                'duration': 200,  # 3.3 minutes
                'affected_stocks': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
            }
        ]
        
        # Select a random event
        event = random.choice(events)
        
        # Set expiry time
        event['expiry_time'] = time.time() + event['duration']
        
        # Add to active events
        self.active_events[event['name']] = event
        
        print(f"Market Event Triggered: {event['name']} - {event['description']}")
    
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
