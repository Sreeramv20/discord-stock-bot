import logging

import discord
from discord import app_commands
from discord.ext import commands

from utils.formatting import format_currency, profit_color, profit_emoji, format_timestamp

logger = logging.getLogger(__name__)


class TradingCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Buy / Sell ──────────────────────────────────────────────────

    @app_commands.command(name="buy", description="Buy shares of a stock")
    @app_commands.describe(ticker="Stock ticker symbol (e.g. AAPL)", shares="Number of shares to buy")
    @app_commands.checks.cooldown(1, 5.0)
    async def buy(self, interaction: discord.Interaction, ticker: str, shares: int):
        await interaction.response.defer(ephemeral=True)
        try:
            result = await self.bot.trading.buy_stock(interaction.user.id, ticker.upper(), shares)
            embed = discord.Embed(title="Buy Order Filled", color=discord.Color.green())
            embed.add_field(name="Stock", value=ticker.upper(), inline=True)
            embed.add_field(name="Shares", value=str(shares), inline=True)
            embed.add_field(name="Price", value=format_currency(result["price"]), inline=True)
            embed.add_field(name="Total Cost", value=format_currency(result["total"]), inline=True)
            embed.add_field(name="New Balance", value=format_currency(result["new_balance"]), inline=True)
            embed.set_footer(text=f"Requested by {interaction.user.display_name}")
            await interaction.followup.send(embed=embed)

            awarded = await self.bot.achievements.check_and_award(interaction.user.id)
            if awarded:
                await self.bot.notifications.notify_achievement(interaction.user.id, awarded)
        except ValueError as e:
            await interaction.followup.send(f"**Error:** {e}", ephemeral=True)
        except Exception as e:
            logger.error("Buy command error: %s", e, exc_info=True)
            await interaction.followup.send("An unexpected error occurred.", ephemeral=True)

    @app_commands.command(name="sell", description="Sell shares of a stock")
    @app_commands.describe(ticker="Stock ticker symbol", shares="Number of shares to sell")
    @app_commands.checks.cooldown(1, 5.0)
    async def sell(self, interaction: discord.Interaction, ticker: str, shares: int):
        await interaction.response.defer(ephemeral=True)
        try:
            result = await self.bot.trading.sell_stock(interaction.user.id, ticker.upper(), shares)
            color = profit_color(result["profit"])
            embed = discord.Embed(title="Sell Order Filled", color=color)
            embed.add_field(name="Stock", value=ticker.upper(), inline=True)
            embed.add_field(name="Shares", value=str(shares), inline=True)
            embed.add_field(name="Price", value=format_currency(result["price"]), inline=True)
            embed.add_field(name="Total", value=format_currency(result["total"]), inline=True)
            embed.add_field(name="Avg Cost", value=format_currency(result["avg_cost"]), inline=True)
            embed.add_field(
                name="Profit/Loss",
                value=f"{profit_emoji(result['profit'])} {format_currency(result['profit'])}",
                inline=True,
            )
            embed.add_field(name="New Balance", value=format_currency(result["new_balance"]), inline=True)
            await interaction.followup.send(embed=embed)

            awarded = await self.bot.achievements.check_and_award(interaction.user.id)
            if awarded:
                await self.bot.notifications.notify_achievement(interaction.user.id, awarded)
        except ValueError as e:
            await interaction.followup.send(f"**Error:** {e}", ephemeral=True)
        except Exception as e:
            logger.error("Sell command error: %s", e, exc_info=True)
            await interaction.followup.send("An unexpected error occurred.", ephemeral=True)

    # ── Balance / History / Stats ───────────────────────────────────

    @app_commands.command(name="balance", description="Check your cash balance")
    @app_commands.checks.cooldown(1, 3.0)
    async def balance(self, interaction: discord.Interaction):
        await self.bot.db.ensure_user(interaction.user.id, interaction.user.display_name)
        bal = await self.bot.db.get_user_balance(interaction.user.id)
        embed = discord.Embed(
            title=f"{interaction.user.display_name}'s Balance",
            description=f"**Cash:** {format_currency(bal)}",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="history", description="View your trade history")
    @app_commands.checks.cooldown(1, 5.0)
    async def history(self, interaction: discord.Interaction):
        await interaction.response.defer()
        txns = await self.bot.db.get_user_transactions(interaction.user.id)
        if not txns:
            await interaction.followup.send("No transaction history yet.")
            return

        embed = discord.Embed(
            title=f"{interaction.user.display_name}'s Trade History",
            color=discord.Color.blue(),
        )
        for t in txns[:10]:
            emoji = "🟢" if t["type"] in ("buy", "dividend") else "🔴" if t["type"] == "sell" else "🟡"
            embed.add_field(
                name=f"{emoji} {t['type'].upper()} {t['ticker']}",
                value=(
                    f"Shares: {t['shares']:.0f} | Price: {format_currency(t['price'])}\n"
                    f"Total: {format_currency(t['total'])} | {format_timestamp(t['timestamp'])}"
                ),
                inline=False,
            )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="stats", description="View your trading statistics")
    @app_commands.checks.cooldown(1, 5.0)
    async def stats(self, interaction: discord.Interaction):
        await interaction.response.defer()
        stats = await self.bot.trading.get_user_stats(interaction.user.id)
        net_worth = await self.bot.portfolio_system.get_net_worth(interaction.user.id)
        color = profit_color(stats["net_profit_loss"])
        embed = discord.Embed(
            title=f"{interaction.user.display_name}'s Trading Stats",
            color=color,
        )
        embed.add_field(name="Total Trades", value=str(stats["total_trades"]), inline=True)
        embed.add_field(name="Buys", value=str(stats["total_buys"]), inline=True)
        embed.add_field(name="Sells", value=str(stats["total_sells"]), inline=True)
        embed.add_field(name="Buy Volume", value=format_currency(stats["buy_volume"]), inline=True)
        embed.add_field(name="Sell Volume", value=format_currency(stats["sell_volume"]), inline=True)
        embed.add_field(
            name="Net P/L",
            value=f"{profit_emoji(stats['net_profit_loss'])} {format_currency(stats['net_profit_loss'])}",
            inline=True,
        )
        embed.add_field(name="Net Worth", value=format_currency(net_worth), inline=True)
        embed.add_field(name="Open Shorts", value=str(stats["open_shorts"]), inline=True)
        embed.add_field(name="Active Options", value=str(stats["active_options"]), inline=True)
        embed.add_field(name="Pending Orders", value=str(stats["pending_limit_orders"]), inline=True)
        await interaction.followup.send(embed=embed)

    # ── Limit Orders ────────────────────────────────────────────────

    @app_commands.command(name="limitbuy", description="Place a limit buy order")
    @app_commands.describe(
        ticker="Stock ticker symbol",
        price="Target price to buy at",
        shares="Number of shares",
    )
    @app_commands.checks.cooldown(1, 5.0)
    async def limitbuy(self, interaction: discord.Interaction, ticker: str, price: float, shares: int):
        await interaction.response.defer(ephemeral=True)
        try:
            order_id = await self.bot.trading.place_limit_order(
                interaction.user.id, ticker.upper(), "buy", price, shares,
            )
            embed = discord.Embed(title="Limit Buy Order Placed", color=discord.Color.blue())
            embed.add_field(name="Order ID", value=str(order_id), inline=True)
            embed.add_field(name="Stock", value=ticker.upper(), inline=True)
            embed.add_field(name="Target Price", value=format_currency(price), inline=True)
            embed.add_field(name="Shares", value=str(shares), inline=True)
            embed.set_footer(text="Order will execute when price drops to target")
            await interaction.followup.send(embed=embed)
        except ValueError as e:
            await interaction.followup.send(f"**Error:** {e}", ephemeral=True)
        except Exception as e:
            logger.error("Limitbuy error: %s", e, exc_info=True)
            await interaction.followup.send("An unexpected error occurred.", ephemeral=True)

    @app_commands.command(name="limitsell", description="Place a limit sell order")
    @app_commands.describe(
        ticker="Stock ticker symbol",
        price="Target price to sell at",
        shares="Number of shares",
    )
    @app_commands.checks.cooldown(1, 5.0)
    async def limitsell(self, interaction: discord.Interaction, ticker: str, price: float, shares: int):
        await interaction.response.defer(ephemeral=True)
        try:
            order_id = await self.bot.trading.place_limit_order(
                interaction.user.id, ticker.upper(), "sell", price, shares,
            )
            embed = discord.Embed(title="Limit Sell Order Placed", color=discord.Color.blue())
            embed.add_field(name="Order ID", value=str(order_id), inline=True)
            embed.add_field(name="Stock", value=ticker.upper(), inline=True)
            embed.add_field(name="Target Price", value=format_currency(price), inline=True)
            embed.add_field(name="Shares", value=str(shares), inline=True)
            embed.set_footer(text="Order will execute when price rises to target")
            await interaction.followup.send(embed=embed)
        except ValueError as e:
            await interaction.followup.send(f"**Error:** {e}", ephemeral=True)
        except Exception as e:
            logger.error("Limitsell error: %s", e, exc_info=True)
            await interaction.followup.send("An unexpected error occurred.", ephemeral=True)

    # ── Short Selling ───────────────────────────────────────────────

    @app_commands.command(name="short", description="Short sell a stock (borrow and sell)")
    @app_commands.describe(ticker="Stock ticker symbol", shares="Number of shares to short")
    @app_commands.checks.cooldown(1, 5.0)
    async def short(self, interaction: discord.Interaction, ticker: str, shares: int):
        await interaction.response.defer(ephemeral=True)
        try:
            result = await self.bot.trading.short_stock(interaction.user.id, ticker.upper(), shares)
            embed = discord.Embed(title="Short Position Opened", color=discord.Color.orange())
            embed.add_field(name="Stock", value=ticker.upper(), inline=True)
            embed.add_field(name="Shares", value=str(shares), inline=True)
            embed.add_field(name="Borrow Price", value=format_currency(result["borrow_price"]), inline=True)
            embed.add_field(name="Proceeds", value=format_currency(result["proceeds"]), inline=True)
            embed.add_field(name="Margin Held", value=format_currency(result["margin"]), inline=True)
            embed.add_field(name="New Balance", value=format_currency(result["new_balance"]), inline=True)
            embed.set_footer(text="Use /cover to close this position")
            await interaction.followup.send(embed=embed)
        except ValueError as e:
            await interaction.followup.send(f"**Error:** {e}", ephemeral=True)

    @app_commands.command(name="cover", description="Cover (close) a short position")
    @app_commands.describe(position_id="ID of the short position to close")
    @app_commands.checks.cooldown(1, 5.0)
    async def cover(self, interaction: discord.Interaction, position_id: int):
        await interaction.response.defer(ephemeral=True)
        try:
            result = await self.bot.trading.cover_short(interaction.user.id, position_id)
            color = profit_color(result["profit"])
            embed = discord.Embed(title="Short Position Closed", color=color)
            embed.add_field(name="Stock", value=result["ticker"], inline=True)
            embed.add_field(name="Shares", value=str(result["shares"]), inline=True)
            embed.add_field(name="Borrow Price", value=format_currency(result["borrow_price"]), inline=True)
            embed.add_field(name="Cover Price", value=format_currency(result["cover_price"]), inline=True)
            embed.add_field(
                name="Profit/Loss",
                value=f"{profit_emoji(result['profit'])} {format_currency(result['profit'])}",
                inline=True,
            )
            embed.add_field(name="New Balance", value=format_currency(result["new_balance"]), inline=True)
            await interaction.followup.send(embed=embed)

            awarded = await self.bot.achievements.check_and_award(interaction.user.id)
            if awarded:
                await self.bot.notifications.notify_achievement(interaction.user.id, awarded)
        except ValueError as e:
            await interaction.followup.send(f"**Error:** {e}", ephemeral=True)

    # ── Options Trading ─────────────────────────────────────────────

    @app_commands.command(name="call", description="Buy a call option (bet price goes up)")
    @app_commands.describe(
        ticker="Stock ticker symbol",
        strike="Strike price",
        expiry_days="Days until expiry (1-90)",
    )
    @app_commands.checks.cooldown(1, 5.0)
    async def call_option(self, interaction: discord.Interaction, ticker: str,
                          strike: float, expiry_days: int):
        await interaction.response.defer(ephemeral=True)
        try:
            result = await self.bot.trading.buy_option(
                interaction.user.id, ticker.upper(), "call", strike, expiry_days,
            )
            embed = discord.Embed(title="Call Option Purchased", color=discord.Color.green())
            embed.add_field(name="Stock", value=result["ticker"], inline=True)
            embed.add_field(name="Current Price", value=format_currency(result["current_price"]), inline=True)
            embed.add_field(name="Strike", value=format_currency(result["strike"]), inline=True)
            embed.add_field(name="Premium Paid", value=format_currency(result["premium"]), inline=True)
            embed.add_field(name="Expiry", value=f"{expiry_days} days", inline=True)
            embed.add_field(name="Contract", value="100 shares", inline=True)
            embed.set_footer(text="Profit if price > strike at expiry")
            await interaction.followup.send(embed=embed)

            awarded = await self.bot.achievements.check_and_award(interaction.user.id)
            if awarded:
                await self.bot.notifications.notify_achievement(interaction.user.id, awarded)
        except ValueError as e:
            await interaction.followup.send(f"**Error:** {e}", ephemeral=True)

    @app_commands.command(name="put", description="Buy a put option (bet price goes down)")
    @app_commands.describe(
        ticker="Stock ticker symbol",
        strike="Strike price",
        expiry_days="Days until expiry (1-90)",
    )
    @app_commands.checks.cooldown(1, 5.0)
    async def put_option(self, interaction: discord.Interaction, ticker: str,
                         strike: float, expiry_days: int):
        await interaction.response.defer(ephemeral=True)
        try:
            result = await self.bot.trading.buy_option(
                interaction.user.id, ticker.upper(), "put", strike, expiry_days,
            )
            embed = discord.Embed(title="Put Option Purchased", color=discord.Color.red())
            embed.add_field(name="Stock", value=result["ticker"], inline=True)
            embed.add_field(name="Current Price", value=format_currency(result["current_price"]), inline=True)
            embed.add_field(name="Strike", value=format_currency(result["strike"]), inline=True)
            embed.add_field(name="Premium Paid", value=format_currency(result["premium"]), inline=True)
            embed.add_field(name="Expiry", value=f"{expiry_days} days", inline=True)
            embed.add_field(name="Contract", value="100 shares", inline=True)
            embed.set_footer(text="Profit if price < strike at expiry")
            await interaction.followup.send(embed=embed)

            awarded = await self.bot.achievements.check_and_award(interaction.user.id)
            if awarded:
                await self.bot.notifications.notify_achievement(interaction.user.id, awarded)
        except ValueError as e:
            await interaction.followup.send(f"**Error:** {e}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(TradingCommands(bot))
