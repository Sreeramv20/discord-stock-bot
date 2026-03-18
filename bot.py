import logging
import sys

import discord
from discord import app_commands
from discord.ext import commands

import config
from database import Database
from leaderboard import Leaderboard
from market import Market
from portfolio import PortfolioSystem
from services.achievement_service import AchievementService
from services.copy_trade_service import CopyTradeService
from services.event_service import EventService
from services.fund_service import FundService
from services.insider_service import InsiderService
from services.ipo_service import IPOService
from services.margin_service import MarginService
from services.market_hours_service import MarketHoursService
from services.notification_service import NotificationService
from services.prestige_service import PrestigeService
from services.tournament_service import TournamentService
from trading import TradingEngine
from utils.logging_config import setup_logging

logger = setup_logging()


class StockTradingBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True

        super().__init__(command_prefix="!", intents=intents, help_command=None)

        self.db = Database(config.DATABASE_PATH)
        self.market = Market(self.db)
        self.trading = TradingEngine(self.db, self.market)
        self.portfolio_system = PortfolioSystem(self.db, self.market)
        self.leaderboard = Leaderboard(self.db, self.portfolio_system)
        self.achievements = AchievementService(self.db)
        self.events = EventService(self.db)
        self.notifications: NotificationService = None

        self.tournaments = TournamentService(self.db, self.market)
        self.insiders = InsiderService(self.db)
        self.funds = FundService(self.db, self.market)
        self.margin = MarginService(self.db, self.market)
        self.copy_trades = CopyTradeService(self.db)
        self.ipo_service = IPOService(self.db)
        self.market_hours = MarketHoursService()
        self.prestige = PrestigeService(self.db, self.portfolio_system)

        self.market_update_interval = config.MARKET_UPDATE_INTERVAL

    async def setup_hook(self):
        logger.info("Setting up bot...")
        await self.db.init()
        self.notifications = NotificationService(self)

        self.trading.register_trade_callback(self._on_trade_copy)

        cog_modules = [
            "cogs.trading_commands",
            "cogs.portfolio_commands",
            "cogs.market_commands",
            "cogs.leaderboard_commands",
            "cogs.daily_commands",
            "cogs.admin_commands",
            "cogs.tournament_commands",
            "cogs.fund_commands",
            "cogs.margin_commands",
            "cogs.social_commands",
            "cogs.progression_commands",
            "tasks.market_tasks",
            "tasks.leaderboard_tasks",
            "tasks.viral_tasks",
        ]
        for module in cog_modules:
            try:
                await self.load_extension(module)
                logger.info("Loaded extension: %s", module)
            except Exception as e:
                logger.error("Failed to load %s: %s", module, e, exc_info=True)

        await self.market.initialize_default_stocks()
        logger.info("Setup complete.")

    async def _on_trade_copy(self, leader_id: int, ticker: str,
                             trade_type: str, shares: int, price: float):
        """Callback fired after every trade to propagate copy-trades."""
        try:
            await self.copy_trades.execute_copy_trades(
                leader_id, ticker, trade_type, shares, price,
            )
        except Exception as e:
            logger.debug("Copy-trade callback error: %s", e)

    async def on_ready(self):
        logger.info("Logged in as %s (ID: %s)", self.user, self.user.id)
        logger.info("Connected to %d guild(s)", len(self.guilds))

        try:
            synced = await self.tree.sync()
            logger.info("Synced %d slash command(s)", len(synced))
        except Exception as e:
            logger.error("Failed to sync commands: %s", e, exc_info=True)


bot = StockTradingBot()


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await _safe_respond(
            interaction,
            f"Cooldown! Try again in **{error.retry_after:.1f}s**.",
            ephemeral=True,
        )
    elif isinstance(error, app_commands.CheckFailure):
        await _safe_respond(interaction, f"Permission denied: {error}", ephemeral=True)
    else:
        logger.error("Unhandled command error: %s", error, exc_info=error)
        await _safe_respond(
            interaction,
            "An unexpected error occurred. Please try again later.",
            ephemeral=True,
        )


async def _safe_respond(interaction: discord.Interaction, content: str, **kwargs):
    try:
        if interaction.response.is_done():
            await interaction.followup.send(content, **kwargs)
        else:
            await interaction.response.send_message(content, **kwargs)
    except discord.HTTPException:
        pass


def main():
    if not config.DISCORD_TOKEN or config.DISCORD_TOKEN == "YOUR_DISCORD_BOT_TOKEN":
        logger.error("DISCORD_TOKEN not set. Copy .env.example to .env and add your token.")
        sys.exit(1)

    logger.info("Starting Stock Trading Bot...")
    bot.run(config.DISCORD_TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
