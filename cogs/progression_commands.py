import logging

import discord
from discord import app_commands
from discord.ext import commands

import config
from utils.formatting import format_currency, format_timestamp

logger = logging.getLogger(__name__)


class ProgressionCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Prestige ────────────────────────────────────────────────────

    @app_commands.command(name="prestige", description="Reset your portfolio for permanent bonuses")
    @app_commands.checks.cooldown(1, 30.0)
    async def prestige(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            can, net_worth = await self.bot.prestige.can_prestige(interaction.user.id)
            current = await self.bot.prestige.get_prestige_level(interaction.user.id)

            if not can:
                embed = discord.Embed(
                    title="Prestige System",
                    description=(
                        f"You need **{format_currency(config.PRESTIGE_NET_WORTH_REQ)}** net worth to prestige.\n"
                        f"Current net worth: {format_currency(net_worth)}\n"
                        f"Current level: ⭐ **{current['level']}**"
                    ),
                    color=discord.Color.greyple(),
                )
                next_bonus = (current["level"] + 1) * config.PRESTIGE_DAILY_BONUS * 100
                embed.add_field(
                    name="Next Prestige Bonus",
                    value=f"+{next_bonus:.0f}% daily rewards",
                )
                await interaction.followup.send(embed=embed)
                return

            result = await self.bot.prestige.prestige(interaction.user.id)
            embed = discord.Embed(
                title="⭐ PRESTIGE ACHIEVED! ⭐",
                description=(
                    f"You reset from **{format_currency(result['previous_net_worth'])}** "
                    f"to earn permanent bonuses!"
                ),
                color=discord.Color.gold(),
            )
            embed.add_field(name="New Level", value=f"⭐ {result['level']}", inline=True)
            embed.add_field(name="Title", value=result["title"] or "None", inline=True)
            embed.add_field(
                name="Daily Bonus",
                value=f"{result['daily_bonus_mult']:.1f}x multiplier",
                inline=True,
            )
            embed.add_field(
                name="Reset Details",
                value=(
                    f"Portfolio liquidated\n"
                    f"Cash reset to {format_currency(config.INITIAL_CASH)}\n"
                    f"Achievements preserved"
                ),
                inline=False,
            )
            await interaction.followup.send(embed=embed)
        except ValueError as e:
            await interaction.followup.send(f"**Error:** {e}", ephemeral=True)

    @app_commands.command(name="prestigeinfo", description="View your prestige level and bonuses")
    @app_commands.checks.cooldown(1, 5.0)
    async def prestige_info(self, interaction: discord.Interaction):
        await interaction.response.defer()
        current = await self.bot.prestige.get_prestige_level(interaction.user.id)
        net_worth = 0.0
        try:
            _, net_worth = await self.bot.prestige.can_prestige(interaction.user.id)
        except Exception:
            pass

        embed = discord.Embed(
            title=f"{interaction.user.display_name}'s Prestige",
            color=discord.Color.gold() if current["level"] > 0 else discord.Color.greyple(),
        )
        embed.add_field(name="Level", value=f"⭐ {current['level']}", inline=True)
        embed.add_field(name="Title", value=current.get("title") or "None", inline=True)
        embed.add_field(
            name="Daily Bonus",
            value=f"{current['daily_bonus_mult']:.1f}x",
            inline=True,
        )
        embed.add_field(name="Total Resets", value=str(current.get("total_resets", 0)), inline=True)
        progress = (net_worth / config.PRESTIGE_NET_WORTH_REQ) * 100
        bar_len = 10
        filled = min(bar_len, int(progress / 100 * bar_len))
        bar = "█" * filled + "░" * (bar_len - filled)
        embed.add_field(
            name="Progress to Next Prestige",
            value=f"`{bar}` {progress:.1f}%\n{format_currency(net_worth)} / {format_currency(config.PRESTIGE_NET_WORTH_REQ)}",
            inline=False,
        )
        await interaction.followup.send(embed=embed)

    # ── IPO ─────────────────────────────────────────────────────────

    @app_commands.command(name="ipos", description="View upcoming and active IPOs")
    @app_commands.checks.cooldown(1, 5.0)
    async def ipos(self, interaction: discord.Interaction):
        await interaction.response.defer()
        active = await self.bot.ipo_service.get_active_ipos()
        if not active:
            await interaction.followup.send("No active IPOs right now. Stay tuned!")
            return

        embed = discord.Embed(title="IPO Center", color=discord.Color.blue())
        for ipo in active:
            phase_emoji = {"announced": "📢", "open": "🟢"}.get(ipo["phase"], "⬜")
            status = "OPEN FOR TRADING" if ipo["phase"] == "open" else "ANNOUNCED"
            embed.add_field(
                name=f"{phase_emoji} {ipo['ticker']} — {ipo['name']}",
                value=(
                    f"Status: **{status}**\n"
                    f"Initial Price: {format_currency(ipo['initial_price'])}\n"
                    f"Sector: {ipo.get('sector', 'N/A')}\n"
                    f"Opens: {(ipo.get('opens_at') or 'TBD')[:16]}"
                ),
                inline=False,
            )
        embed.set_footer(text="IPO stocks have higher volatility during their open phase")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="ipo", description="View details of a specific IPO")
    @app_commands.describe(ticker="IPO ticker symbol")
    @app_commands.checks.cooldown(1, 5.0)
    async def ipo(self, interaction: discord.Interaction, ticker: str):
        await interaction.response.defer()
        all_ipos = await self.bot.ipo_service.get_all_ipos()
        ipo = next((i for i in all_ipos if i["ticker"] == ticker.upper()), None)
        if not ipo:
            await interaction.followup.send(f"IPO `{ticker.upper()}` not found.", ephemeral=True)
            return

        stock = await self.bot.market.get_stock_info(ticker.upper())
        embed = discord.Embed(
            title=f"IPO: {ipo['ticker']} — {ipo['name']}",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Phase", value=ipo["phase"].title(), inline=True)
        embed.add_field(name="IPO Price",
                        value=format_currency(ipo["initial_price"]), inline=True)
        if stock:
            embed.add_field(name="Current Price",
                            value=format_currency(stock["price"]), inline=True)
            change_pct = ((stock["price"] - ipo["initial_price"]) / ipo["initial_price"]) * 100
            embed.add_field(name="Change from IPO",
                            value=f"{change_pct:+.1f}%", inline=True)
        embed.add_field(name="Sector", value=ipo.get("sector", "N/A"), inline=True)
        embed.add_field(name="Volatility",
                        value=f"{ipo['volatility_multiplier']}x", inline=True)
        await interaction.followup.send(embed=embed)

    # ── Market Hours ────────────────────────────────────────────────

    @app_commands.command(name="markethours", description="View current market session status")
    @app_commands.checks.cooldown(1, 5.0)
    async def market_hours(self, interaction: discord.Interaction):
        sessions = self.bot.market_hours.get_all_sessions_status()
        is_after = self.bot.market_hours.is_after_hours()
        vol = self.bot.market_hours.get_volatility_multiplier()

        embed = discord.Embed(title="Market Hours", color=discord.Color.blue())
        for s in sessions:
            status = "🟢 OPEN" if s["is_open"] else "🔴 CLOSED"
            embed.add_field(
                name=f"{s['name']} ({s['region']})",
                value=f"{status}\nHours: {s['hours']}\nVolatility: {s['volatility']}x",
                inline=True,
            )
        if is_after:
            embed.add_field(
                name="After Hours",
                value=f"⚡ Volatility: {vol}x",
                inline=False,
            )
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(ProgressionCommands(bot))
