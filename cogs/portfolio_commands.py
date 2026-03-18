import logging

import discord
from discord import app_commands
from discord.ext import commands

from utils.formatting import format_currency, profit_color, profit_emoji, format_percent

logger = logging.getLogger(__name__)


class PortfolioCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="portfolio", description="View your investment portfolio")
    @app_commands.checks.cooldown(1, 5.0)
    async def portfolio(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            summary = await self.bot.portfolio_system.get_summary(interaction.user.id)
            balance = summary["balance"]
            portfolio_value = summary["portfolio_value"]
            net_worth = summary["net_worth"]
            total_profit = summary["total_profit"]
            holdings = summary["holdings"]

            color = profit_color(total_profit)
            embed = discord.Embed(
                title=f"{interaction.user.display_name}'s Portfolio",
                color=color,
            )

            if holdings:
                lines = []
                for h in holdings:
                    emoji = profit_emoji(h["profit_loss"])
                    lines.append(
                        f"{emoji} **{h['ticker']}** — "
                        f"{h['shares']:.0f} shares @ {format_currency(h['avg_price'])} avg\n"
                        f"  Price: {format_currency(h['current_price'])} | "
                        f"Value: {format_currency(h['current_value'])} | "
                        f"P/L: {format_currency(h['profit_loss'])} ({format_percent(h['profit_pct'])})"
                    )
                embed.description = "\n\n".join(lines)
            else:
                embed.description = "Your portfolio is empty. Use `/buy` to start trading!"

            shorts = await self.bot.db.get_user_shorts(interaction.user.id)
            if shorts:
                short_lines = []
                for s in shorts:
                    price = await self.bot.market.get_price(s["ticker"]) or s["borrow_price"]
                    pl = (s["borrow_price"] - price) * s["shares"]
                    emoji = profit_emoji(pl)
                    short_lines.append(
                        f"{emoji} **{s['ticker']}** (SHORT) — "
                        f"{s['shares']:.0f} shares @ {format_currency(s['borrow_price'])}\n"
                        f"  Current: {format_currency(price)} | P/L: {format_currency(pl)} | ID: {s['id']}"
                    )
                embed.add_field(
                    name="Short Positions",
                    value="\n\n".join(short_lines),
                    inline=False,
                )

            options = await self.bot.db.get_user_options(interaction.user.id)
            active_opts = [o for o in options if o["status"] == "active"]
            if active_opts:
                opt_lines = []
                for o in active_opts:
                    opt_lines.append(
                        f"**{o['ticker']}** {o['option_type'].upper()} @ "
                        f"{format_currency(o['strike_price'])} | "
                        f"Premium: {format_currency(o['premium'])} | Expiry: {o['expiry'][:10]}"
                    )
                embed.add_field(
                    name="Active Options",
                    value="\n".join(opt_lines),
                    inline=False,
                )

            limit_orders = await self.bot.db.get_user_limit_orders(interaction.user.id)
            pending = [o for o in limit_orders if o["status"] == "pending"]
            if pending:
                order_lines = []
                for o in pending:
                    order_lines.append(
                        f"#{o['id']} {o['order_type'].upper()} **{o['ticker']}** "
                        f"@ {format_currency(o['target_price'])} x{o['shares']}"
                    )
                embed.add_field(
                    name="Pending Limit Orders",
                    value="\n".join(order_lines),
                    inline=False,
                )

            embed.add_field(name="Cash", value=format_currency(balance), inline=True)
            embed.add_field(name="Holdings Value", value=format_currency(portfolio_value), inline=True)
            embed.add_field(name="Net Worth", value=format_currency(net_worth), inline=True)
            embed.set_footer(text="Use /buy, /sell, /short, /call, /put to trade")

            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error("Portfolio command error: %s", e, exc_info=True)
            await interaction.followup.send("Failed to load portfolio.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(PortfolioCommands(bot))
