import logging

import discord
from discord import app_commands
from discord.ext import commands

from utils.formatting import format_currency, format_percent, profit_color, profit_emoji

logger = logging.getLogger(__name__)


class MarginCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="marginbuy", description="Open a leveraged long position")
    @app_commands.describe(
        ticker="Stock ticker", shares="Number of shares",
        leverage="Leverage multiplier (1.5x - 3x, default 2x)",
    )
    @app_commands.checks.cooldown(1, 5.0)
    async def margin_buy(self, interaction: discord.Interaction, ticker: str,
                         shares: int, leverage: float = 2.0):
        await interaction.response.defer(ephemeral=True)
        try:
            result = await self.bot.margin.open_margin_position(
                interaction.user.id, ticker.upper(), shares, leverage,
            )
            embed = discord.Embed(title="Margin Position Opened", color=discord.Color.orange())
            embed.add_field(name="Stock", value=ticker.upper(), inline=True)
            embed.add_field(name="Shares", value=str(shares), inline=True)
            embed.add_field(name="Entry Price", value=format_currency(result["entry_price"]), inline=True)
            embed.add_field(name="Leverage", value=f"{leverage}x", inline=True)
            embed.add_field(name="Position Value",
                            value=format_currency(result["position_value"]), inline=True)
            embed.add_field(name="Margin Used",
                            value=format_currency(result["margin_used"]), inline=True)
            embed.add_field(name="Liquidation Price",
                            value=f"⚠️ {format_currency(result['liquidation_price'])}", inline=True)
            embed.set_footer(text=f"Position ID: {result['position_id']}. Use /marginsell to close.")
            await interaction.followup.send(embed=embed)
        except ValueError as e:
            await interaction.followup.send(f"**Error:** {e}", ephemeral=True)

    @app_commands.command(name="marginsell", description="Close a margin position")
    @app_commands.describe(position_id="Margin position ID to close")
    @app_commands.checks.cooldown(1, 5.0)
    async def margin_sell(self, interaction: discord.Interaction, position_id: int):
        await interaction.response.defer(ephemeral=True)
        try:
            result = await self.bot.margin.close_margin_position(
                interaction.user.id, position_id,
            )
            color = profit_color(result["profit"])
            embed = discord.Embed(title="Margin Position Closed", color=color)
            embed.add_field(name="Stock", value=result["ticker"], inline=True)
            embed.add_field(name="Shares", value=str(result["shares"]), inline=True)
            embed.add_field(name="Entry", value=format_currency(result["entry_price"]), inline=True)
            embed.add_field(name="Exit", value=format_currency(result["close_price"]), inline=True)
            embed.add_field(name="Leverage", value=f"{result['leverage']}x", inline=True)
            embed.add_field(
                name="Profit/Loss",
                value=f"{profit_emoji(result['profit'])} {format_currency(result['profit'])}",
                inline=True,
            )
            embed.add_field(name="Payout", value=format_currency(result["payout"]), inline=True)
            await interaction.followup.send(embed=embed)
        except ValueError as e:
            await interaction.followup.send(f"**Error:** {e}", ephemeral=True)

    @app_commands.command(name="marginpositions", description="View your open margin positions")
    @app_commands.checks.cooldown(1, 5.0)
    async def margin_positions(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            positions = await self.bot.margin.get_user_positions(interaction.user.id)
            if not positions:
                await interaction.followup.send("No open margin positions.")
                return

            embed = discord.Embed(
                title=f"{interaction.user.display_name}'s Margin Positions",
                color=discord.Color.orange(),
            )
            for p in positions:
                emoji = profit_emoji(p["profit"])
                embed.add_field(
                    name=f"#{p['id']} {p['ticker']} ({p['leverage']}x)",
                    value=(
                        f"Shares: {p['shares']:.0f} | Entry: {format_currency(p['entry_price'])}\n"
                        f"Current: {format_currency(p['current_price'])} | "
                        f"Value: {format_currency(p['current_value'])}\n"
                        f"P/L: {emoji} {format_currency(p['profit'])} "
                        f"({format_percent(p['pnl_pct'])})\n"
                        f"Liq. Price: ⚠️ {format_currency(p['liquidation_price'])}"
                    ),
                    inline=False,
                )
            embed.set_footer(text="Use /marginsell <id> to close a position")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error("Margin positions error: %s", e, exc_info=True)
            await interaction.followup.send("Failed to load positions.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(MarginCommands(bot))
