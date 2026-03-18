import logging

import discord
from discord import app_commands
from discord.ext import commands

import config
from utils.formatting import format_currency

logger = logging.getLogger(__name__)


def is_admin():
    async def predicate(interaction: discord.Interaction) -> bool:
        if not interaction.user.guild_permissions.administrator:
            raise app_commands.CheckFailure("You need Administrator permissions.")
        return True
    return app_commands.check(predicate)


class AdminCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="forcerefresh", description="[Admin] Force refresh market prices and leaderboard")
    @is_admin()
    @app_commands.checks.cooldown(1, 30.0)
    async def forcerefresh(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            await self.bot.market.update_all_prices()
            await self.bot.leaderboard.update_rankings()
            await interaction.followup.send("Market prices and leaderboard refreshed.", ephemeral=True)
        except Exception as e:
            logger.error("Force refresh error: %s", e, exc_info=True)
            await interaction.followup.send("Refresh failed.", ephemeral=True)

    @app_commands.command(name="givecash", description="[Admin] Give cash to a user")
    @app_commands.describe(user="Target user", amount="Amount to give")
    @is_admin()
    async def givecash(self, interaction: discord.Interaction, user: discord.Member, amount: float):
        if amount <= 0 or amount > 10_000_000:
            await interaction.response.send_message("Amount must be between $0 and $10,000,000.", ephemeral=True)
            return
        try:
            await self.bot.db.ensure_user(user.id, user.display_name)
            await self.bot.db.increment_user_balance(user.id, amount)
            new_balance = await self.bot.db.get_user_balance(user.id)
            embed = discord.Embed(
                title="Cash Granted",
                description=f"Gave **{format_currency(amount)}** to {user.mention}",
                color=discord.Color.green(),
            )
            embed.add_field(name="New Balance", value=format_currency(new_balance))
            await interaction.response.send_message(embed=embed)
            logger.info("Admin %s gave $%.2f to %s", interaction.user.id, amount, user.id)
        except Exception as e:
            logger.error("Givecash error: %s", e, exc_info=True)
            await interaction.response.send_message("Failed to give cash.", ephemeral=True)

    @app_commands.command(name="reseteconomy", description="[Admin] Reset all users to starting balance")
    @is_admin()
    async def reseteconomy(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            users = await self.bot.db.get_all_users()
            for user in users:
                await self.bot.db.update_user_balance(user["discord_id"], config.INITIAL_CASH)
            await interaction.followup.send(
                f"Economy reset. {len(users)} users set to {format_currency(config.INITIAL_CASH)}.",
                ephemeral=True,
            )
            logger.warning("Economy reset by admin %s", interaction.user.id)
        except Exception as e:
            logger.error("Reset economy error: %s", e, exc_info=True)
            await interaction.followup.send("Failed to reset economy.", ephemeral=True)

    @app_commands.command(name="addstock", description="[Admin] Add a new stock to the market")
    @app_commands.describe(ticker="Stock ticker", name="Company name", price="Initial price")
    @is_admin()
    async def addstock(self, interaction: discord.Interaction, ticker: str,
                       name: str, price: float):
        ticker = ticker.upper().strip()
        if price <= 0:
            await interaction.response.send_message("Price must be positive.", ephemeral=True)
            return
        try:
            existing = await self.bot.db.get_stock(ticker)
            if existing:
                await interaction.response.send_message(f"`{ticker}` already exists.", ephemeral=True)
                return
            await self.bot.db.upsert_stock(ticker, price, name=name)
            embed = discord.Embed(title="Stock Added", color=discord.Color.green())
            embed.add_field(name="Ticker", value=ticker, inline=True)
            embed.add_field(name="Name", value=name, inline=True)
            embed.add_field(name="Price", value=format_currency(price), inline=True)
            await interaction.response.send_message(embed=embed)
            logger.info("Admin %s added stock %s at $%.2f", interaction.user.id, ticker, price)
        except Exception as e:
            logger.error("Add stock error: %s", e, exc_info=True)
            await interaction.response.send_message("Failed to add stock.", ephemeral=True)

    @app_commands.command(name="removestock", description="[Admin] Remove a stock from the market")
    @app_commands.describe(ticker="Stock ticker to remove")
    @is_admin()
    async def removestock(self, interaction: discord.Interaction, ticker: str):
        ticker = ticker.upper().strip()
        try:
            existing = await self.bot.db.get_stock(ticker)
            if not existing:
                await interaction.response.send_message(f"`{ticker}` not found.", ephemeral=True)
                return
            await self.bot.db.remove_stock(ticker)
            await interaction.response.send_message(f"Stock `{ticker}` removed from the market.")
            logger.info("Admin %s removed stock %s", interaction.user.id, ticker)
        except Exception as e:
            logger.error("Remove stock error: %s", e, exc_info=True)
            await interaction.response.send_message("Failed to remove stock.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCommands(bot))
