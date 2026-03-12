import discord
from discord.ext import commands
import asyncio
from config import TOKEN, DATABASE_PATH
from database import init_db
from market import Market
from trading import TradingEngine
from portfolio import PortfolioSystem
from leaderboard import Leaderboard

class StockTradingBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        
        self.market = Market()
        self.trading_engine = TradingEngine()
        self.portfolio_system = PortfolioSystem()
        self.leaderboard = Leaderboard()
        
    async def setup_hook(self):
        # Initialize database
        init_db(DATABASE_PATH)
        
        # Initialize market with default stocks
        await self.market.initialize_stocks()
        
        # Load cogs
        await self.load_extension('cogs.market_commands')
        await self.load_extension('cogs.trading_commands')
        await self.load_extension('cogs.portfolio_commands')
        await self.load_extension('cogs.leaderboard_commands')
        
    async def on_ready(self):
        print(f'{self.user} has logged in!')
        
        # Start market price updates
        asyncio.create_task(self.update_market_prices())

    async def update_market_prices(self):
        """Periodically update stock prices"""
        while True:
            try:
                await self.market.update_all_prices()
                print("Stock prices updated")
            except Exception as e:
                print(f"Error updating stock prices: {e}")
            
            # Update every 30 seconds
            await asyncio.sleep(30)

# Create and run the bot
if __name__ == '__main__':
    bot = StockTradingBot()
    bot.run(TOKEN)
