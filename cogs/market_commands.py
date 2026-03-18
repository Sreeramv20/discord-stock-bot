import logging
import time

import discord
from discord import app_commands
from discord.ext import commands

from utils.formatting import format_currency, format_change, format_percent, profit_emoji, format_timestamp

logger = logging.getLogger(__name__)


class MarketCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="stocks", description="View all available stocks")
    @app_commands.checks.cooldown(1, 5.0)
    async def stocks(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            stocks = await self.bot.market.get_all_stocks()
            if not stocks:
                await interaction.followup.send("No stocks available yet. Market is initializing...")
                return

            embed = discord.Embed(
                title="Stock Market",
                description=f"**{len(stocks)} stocks available**",
                color=discord.Color.blue(),
            )

            for s in stocks:
                change = s.get("change", 0)
                pct = s.get("percent_change", 0)
                emoji = profit_emoji(change)
                embed.add_field(
                    name=f"{emoji} {s['ticker']} — {s.get('name', s['ticker'])}",
                    value=(
                        f"Price: **{format_currency(s['price'])}** | "
                        f"Change: {format_change(change)} ({format_percent(pct)})\n"
                        f"Volume: {s.get('volume', 0):,} | "
                        f"Sector: {s.get('sector', 'N/A')}"
                    ),
                    inline=False,
                )

            events = await self.bot.events.get_active_events()
            if events:
                event_text = "\n".join(
                    f"• **{e['event_type'].replace('_', ' ').title()}** — {e.get('description', '')}"
                    for e in events
                )
                embed.add_field(name="Active Market Events", value=event_text, inline=False)

            embed.set_footer(text=f"Prices update every {self.bot.market_update_interval // 60} minutes")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error("Stocks command error: %s", e, exc_info=True)
            await interaction.followup.send("Failed to load stock data.", ephemeral=True)

    @app_commands.command(name="stock", description="View details of a specific stock")
    @app_commands.describe(ticker="Stock ticker symbol (e.g. AAPL)")
    @app_commands.checks.cooldown(1, 3.0)
    async def stock(self, interaction: discord.Interaction, ticker: str):
        await interaction.response.defer()
        try:
            info = await self.bot.market.get_stock_info(ticker.upper())
            if not info:
                await interaction.followup.send(
                    f"Stock `{ticker.upper()}` not found. Use `/stocks` to see available stocks.",
                    ephemeral=True,
                )
                return

            change = info.get("change", 0)
            pct = info.get("percent_change", 0)
            color = discord.Color.green() if change >= 0 else discord.Color.red()

            embed = discord.Embed(
                title=f"{info['ticker']} — {info.get('name', info['ticker'])}",
                color=color,
            )
            embed.add_field(name="Price", value=format_currency(info["price"]), inline=True)
            embed.add_field(
                name="Change",
                value=f"{profit_emoji(change)} {format_change(change)} ({format_percent(pct)})",
                inline=True,
            )
            prev = info.get("previous_price")
            embed.add_field(name="Previous Close", value=format_currency(prev) if prev else "N/A", inline=True)
            embed.add_field(name="Volume", value=f"{info.get('volume', 0):,}", inline=True)
            embed.add_field(name="Sector", value=info.get("sector", "N/A"), inline=True)
            embed.add_field(
                name="Last Updated",
                value=format_timestamp(info.get("last_updated")),
                inline=True,
            )

            multiplier = await self.bot.market.get_event_multiplier(ticker.upper())
            if multiplier != 1.0:
                effect = f"{(multiplier - 1) * 100:+.1f}%"
                embed.add_field(name="Event Effect", value=effect, inline=True)

            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error("Stock command error: %s", e, exc_info=True)
            await interaction.followup.send("Failed to load stock data.", ephemeral=True)

    @app_commands.command(name="marketnews", description="View market news, events, and movers")
    @app_commands.checks.cooldown(1, 10.0)
    async def marketnews(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            summary = await self.bot.market.get_market_summary()
            embed = discord.Embed(title="Market News", color=discord.Color.gold())

            winners = summary.get("winners", [])
            if winners:
                w_text = "\n".join(
                    f"📈 **{s['ticker']}** {format_currency(s['price'])} "
                    f"({format_percent(s.get('percent_change', 0))})"
                    for s in winners
                )
                embed.add_field(name="Top Gainers", value=w_text, inline=True)

            losers = summary.get("losers", [])
            if losers:
                l_text = "\n".join(
                    f"📉 **{s['ticker']}** {format_currency(s['price'])} "
                    f"({format_percent(s.get('percent_change', 0))})"
                    for s in losers
                )
                embed.add_field(name="Top Losers", value=l_text, inline=True)

            events = summary.get("events", [])
            if events:
                e_lines = []
                for ev in events:
                    remaining = max(0, ev.get("expires_at", 0) - time.time())
                    mins = int(remaining // 60)
                    e_lines.append(
                        f"• **{ev['event_type'].replace('_', ' ').title()}**\n"
                        f"  {ev.get('description', '')} ({mins}m remaining)"
                    )
                embed.add_field(name="Active Events", value="\n".join(e_lines), inline=False)
            else:
                embed.add_field(name="Events", value="No active market events", inline=False)

            dividends = await self.bot.db.get_recent_dividends(5)
            if dividends:
                d_text = "\n".join(
                    f"• **{d['ticker']}** — ${d['amount_per_share']:.4f}/share ({d['pay_date'][:10]})"
                    for d in dividends
                )
                embed.add_field(name="Recent Dividends", value=d_text, inline=False)

            embed.set_footer(text=f"Total stocks: {summary.get('total_stocks', 0)}")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error("Market news error: %s", e, exc_info=True)
            await interaction.followup.send("Failed to load market news.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(MarketCommands(bot))
