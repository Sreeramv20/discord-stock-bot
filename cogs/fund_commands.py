import logging

import discord
from discord import app_commands
from discord.ext import commands

from utils.formatting import format_currency, rank_emoji, profit_emoji

logger = logging.getLogger(__name__)


class FundCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="createfund", description="Create a new hedge fund")
    @app_commands.describe(name="Fund name", description="Fund description")
    @app_commands.checks.cooldown(1, 30.0)
    async def create_fund(self, interaction: discord.Interaction, name: str,
                          description: str = ""):
        await interaction.response.defer(ephemeral=True)
        try:
            result = await self.bot.funds.create_fund(
                interaction.user.id, name, description,
            )
            embed = discord.Embed(title="Hedge Fund Created!", color=discord.Color.gold())
            embed.add_field(name="Name", value=result["name"], inline=True)
            embed.add_field(name="ID", value=str(result["id"]), inline=True)
            embed.set_footer(text="Others can join with /joinfund. Use /fundcontribute to add capital.")
            await interaction.followup.send(embed=embed)
        except ValueError as e:
            await interaction.followup.send(f"**Error:** {e}", ephemeral=True)

    @app_commands.command(name="joinfund", description="Join an existing hedge fund")
    @app_commands.describe(fund_id="Fund ID to join")
    @app_commands.checks.cooldown(1, 10.0)
    async def join_fund(self, interaction: discord.Interaction, fund_id: int):
        await interaction.response.defer(ephemeral=True)
        try:
            result = await self.bot.funds.join_fund(interaction.user.id, fund_id)
            embed = discord.Embed(
                title="Fund Joined!",
                description=f"You joined **{result['fund_name']}**",
                color=discord.Color.green(),
            )
            embed.set_footer(text="Use /fundcontribute to add capital")
            await interaction.followup.send(embed=embed)
        except ValueError as e:
            await interaction.followup.send(f"**Error:** {e}", ephemeral=True)

    @app_commands.command(name="leavefund", description="Leave your current hedge fund")
    @app_commands.checks.cooldown(1, 10.0)
    async def leave_fund(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            result = await self.bot.funds.leave_fund(interaction.user.id)
            embed = discord.Embed(title="Left Fund", color=discord.Color.orange())
            if result["refund"] > 0:
                embed.add_field(name="Refund", value=format_currency(result["refund"]))
            await interaction.followup.send(embed=embed)
        except ValueError as e:
            await interaction.followup.send(f"**Error:** {e}", ephemeral=True)

    @app_commands.command(name="fundcontribute", description="Contribute cash to your fund")
    @app_commands.describe(amount="Amount to contribute")
    @app_commands.checks.cooldown(1, 10.0)
    async def fund_contribute(self, interaction: discord.Interaction, amount: float):
        await interaction.response.defer(ephemeral=True)
        try:
            result = await self.bot.funds.contribute(interaction.user.id, amount)
            embed = discord.Embed(
                title="Contribution Made",
                description=f"Added **{format_currency(amount)}** to fund",
                color=discord.Color.green(),
            )
            await interaction.followup.send(embed=embed)
        except ValueError as e:
            await interaction.followup.send(f"**Error:** {e}", ephemeral=True)

    @app_commands.command(name="fundtrade", description="Trade stocks with fund capital (leader/officer only)")
    @app_commands.describe(action="buy or sell", ticker="Stock ticker", shares="Number of shares")
    @app_commands.checks.cooldown(1, 5.0)
    async def fund_trade(self, interaction: discord.Interaction,
                         action: str, ticker: str, shares: int):
        await interaction.response.defer(ephemeral=True)
        try:
            action = action.lower()
            if action == "buy":
                result = await self.bot.funds.fund_buy(
                    interaction.user.id, ticker.upper(), shares,
                )
            elif action == "sell":
                result = await self.bot.funds.fund_sell(
                    interaction.user.id, ticker.upper(), shares,
                )
            else:
                raise ValueError("Action must be 'buy' or 'sell'")

            color = discord.Color.green() if action == "buy" else discord.Color.orange()
            embed = discord.Embed(title=f"Fund {action.upper()}", color=color)
            embed.add_field(name="Stock", value=ticker.upper(), inline=True)
            embed.add_field(name="Shares", value=str(shares), inline=True)
            embed.add_field(name="Price", value=format_currency(result["price"]), inline=True)
            embed.add_field(name="Total", value=format_currency(result["total"]), inline=True)
            await interaction.followup.send(embed=embed)
        except ValueError as e:
            await interaction.followup.send(f"**Error:** {e}", ephemeral=True)

    @app_commands.command(name="fundportfolio", description="View your fund's portfolio")
    @app_commands.describe(fund_id="Fund ID (optional, uses your fund if omitted)")
    @app_commands.checks.cooldown(1, 5.0)
    async def fund_portfolio(self, interaction: discord.Interaction, fund_id: int | None = None):
        await interaction.response.defer()
        try:
            if fund_id is None:
                membership = await self.bot.funds._get_user_fund(interaction.user.id)
                if not membership:
                    raise ValueError("You are not in any fund. Specify a fund_id.")
                fund_id = membership["fund_id"]

            data = await self.bot.funds.get_fund_portfolio(fund_id)
            fund = data["fund"]
            embed = discord.Embed(
                title=f"Fund: {fund['name']}", color=discord.Color.blue(),
            )

            if data["holdings"]:
                lines = []
                for h in data["holdings"]:
                    lines.append(
                        f"**{h['ticker']}** — {h['shares']:.0f} shares @ "
                        f"{format_currency(h['avg_price'])} avg | "
                        f"Value: {format_currency(h['value'])}"
                    )
                embed.description = "\n".join(lines)
            else:
                embed.description = "No holdings yet."

            embed.add_field(name="Cash", value=format_currency(fund["cash_balance"]), inline=True)
            embed.add_field(name="Holdings Value",
                            value=format_currency(data["portfolio_value"]), inline=True)
            embed.add_field(name="Total Value",
                            value=format_currency(data["total_value"]), inline=True)
            embed.add_field(name="Members", value=str(len(data["members"])), inline=True)
            await interaction.followup.send(embed=embed)
        except ValueError as e:
            await interaction.followup.send(f"**Error:** {e}", ephemeral=True)

    @app_commands.command(name="fundleaderboard", description="View hedge fund rankings")
    @app_commands.checks.cooldown(1, 10.0)
    async def fund_leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            entries = await self.bot.funds.get_fund_leaderboard()
            if not entries:
                await interaction.followup.send("No funds exist yet. Create one with /createfund!")
                return

            embed = discord.Embed(title="Hedge Fund Leaderboard", color=discord.Color.gold())
            lines = []
            for e in entries[:10]:
                lines.append(
                    f"{rank_emoji(e['rank'])} **{e['name']}** — "
                    f"{format_currency(e['total_value'])} | {e['members']} members"
                )
            embed.description = "\n\n".join(lines)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error("Fund leaderboard error: %s", e, exc_info=True)
            await interaction.followup.send("Failed to load fund leaderboard.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(FundCommands(bot))
