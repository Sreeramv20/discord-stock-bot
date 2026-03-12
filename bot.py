import discord
from discord.ext import commands
import asyncio
import config
import database
import market
import portfolio
import trading
import leaderboard

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
        
        # Initialize systems
        self.market = market.Market()
        self.portfolio_system = portfolio.PortfolioSystem()
        self.trading_engine = trading.TradingEngine()
        self.leaderboard = leaderboard.Leaderboard()
        
    async def setup_hook(self):
        """Setup bot with cogs."""
        # Initialize database
        database.init_db(config.DB_PATH)
        
        # Load all cogs
        await self.load_extension('cogs.daily_commands')
        await self.load_extension('cogs.leaderboard_commands')
        await self.load_extension('cogs.market_commands')
        await self.load_extension('cogs.portfolio_commands')
        await self.load_extension('cogs.trading_commands')
        
        # Start background tasks
        self.loop.create_task(self.start_background_tasks())
    
    async def start_background_tasks(self):
        """Start background tasks like market updates."""
        # Start market updates
        self.loop.create_task(self.market.start_market_updates())
        
        # Start leaderboard updates (every 10 minutes)
        while True:
            try:
                await self.leaderboard.update_leaderboard()
                await asyncio.sleep(600)  # 10 minutes
            except Exception as e:
                print(f"Error updating leaderboard: {e}")
                await asyncio.sleep(60)
    
    async def on_ready(self):
        """Called when bot is ready."""
        print(f'{self.user} has logged in!')
        
        # Initialize market with default stocks
        await self.market.initialize_stocks()

# Create bot instance
bot = StockTradingBot()
