import discord
from discord.ext import commands
import sqlite3
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
        
        # Load cogs
        await self.load_extension('cogs.market_commands')
        await self.load_extension('cogs.trading_commands')
        await self.load_extension('cogs.portfolio_commands')
        await self.load_extension('cogs.leaderboard_commands')
        
    async def on_ready(self):
        print(f'{self.user} has logged in!')

# Create and run the bot
if __name__ == '__main__':
    bot = StockTradingBot()
    bot.run(TOKEN)
