import logging

import discord
from discord import app_commands
from discord.ext import commands

from utils.formatting import format_currency, format_percent, rank_emoji

logger = logging.getLogger(__name__)


def is_admin():
    async def predicate(interaction: discord.Interaction) -> bool:
        if not interaction.user.guild_permissions.administrator:
            raise app_commands.CheckFailure("Administrator permissions required.")
        return True
    return app_commands.check(predicate)


class TournamentCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="tournament", description="[Admin] Create a new trading tournament")
    @app_commands.describe(
        name="Tournament name", duration_days="Duration in days (default 7)",
        start_cash="Starting cash for each player (default 10000)",
    )
    @is_admin()
    async def tournament(self, interaction: discord.Interaction, name: str,
                         duration_days: int = 7, start_cash: float = 10000):
        await interaction.response.defer()
        try:
            result = await self.bot.tournaments.create_tournament(
                name, duration_days, start_cash, interaction.user.id,
            )
            embed = discord.Embed(title="Tournament Created!", color=discord.Color.gold())
            embed.add_field(name="Name", value=result["name"], inline=True)
            embed.add_field(name="ID", value=str(result["id"]), inline=True)
            embed.add_field(name="Duration", value=f"{duration_days} days", inline=True)
            embed.add_field(name="Starting Cash", value=format_currency(start_cash), inline=True)
            embed.add_field(name="Starts", value=result["start_time"][:16], inline=True)
            embed.set_footer(text="Use /jointournament to enter!")
            await interaction.followup.send(embed=embed)
        except ValueError as e:
            await interaction.followup.send(f"**Error:** {e}", ephemeral=True)

    @app_commands.command(name="jointournament", description="Join an active tournament")
    @app_commands.describe(tournament_id="Tournament ID to join")
    @app_commands.checks.cooldown(1, 10.0)
    async def join_tournament(self, interaction: discord.Interaction, tournament_id: int):
        await interaction.response.defer(ephemeral=True)
        try:
            await self.bot.db.ensure_user(interaction.user.id, interaction.user.display_name)
            result = await self.bot.tournaments.join_tournament(tournament_id, interaction.user.id)
            embed = discord.Embed(
                title="Tournament Joined!",
                description=f"You're in! Starting cash: **{format_currency(result['start_cash'])}**",
                color=discord.Color.green(),
            )
            embed.set_footer(text="Use /tournamenttrade to buy/sell within the tournament")
            await interaction.followup.send(embed=embed)
        except ValueError as e:
            await interaction.followup.send(f"**Error:** {e}", ephemeral=True)

    @app_commands.command(name="tournamenttrade", description="Buy or sell stocks in your active tournament")
    @app_commands.describe(action="buy or sell", ticker="Stock ticker", shares="Number of shares")
    @app_commands.checks.cooldown(1, 3.0)
    async def tournament_trade(self, interaction: discord.Interaction,
                               action: str, ticker: str, shares: int):
        await interaction.response.defer(ephemeral=True)
        try:
            action = action.lower()
            if action not in ("buy", "sell"):
                raise ValueError("Action must be 'buy' or 'sell'")

            t = await self.bot.tournaments.get_user_active_tournament(interaction.user.id)
            if not t:
                raise ValueError("You are not in any active tournament.")

            if action == "buy":
                result = await self.bot.tournaments.tournament_buy(
                    t["id"], interaction.user.id, ticker.upper(), shares,
                )
            else:
                result = await self.bot.tournaments.tournament_sell(
                    t["id"], interaction.user.id, ticker.upper(), shares,
                )

            color = discord.Color.green() if action == "buy" else discord.Color.orange()
            embed = discord.Embed(title=f"Tournament {action.upper()}", color=color)
            embed.add_field(name="Stock", value=ticker.upper(), inline=True)
            embed.add_field(name="Shares", value=str(shares), inline=True)
            embed.add_field(name="Price", value=format_currency(result["price"]), inline=True)
            embed.add_field(name="Total", value=format_currency(result["total"]), inline=True)
            await interaction.followup.send(embed=embed)
        except ValueError as e:
            await interaction.followup.send(f"**Error:** {e}", ephemeral=True)

    @app_commands.command(name="tournamentleaderboard", description="View tournament standings")
    @app_commands.describe(tournament_id="Tournament ID")
    @app_commands.checks.cooldown(1, 10.0)
    async def tournament_leaderboard(self, interaction: discord.Interaction, tournament_id: int):
        await interaction.response.defer()
        try:
            entries = await self.bot.tournaments.get_tournament_leaderboard(tournament_id)
            if not entries:
                await interaction.followup.send("No participants in this tournament yet.")
                return

            embed = discord.Embed(title="Tournament Leaderboard", color=discord.Color.gold())
            lines = []
            for e in entries[:10]:
                try:
                    user = await self.bot.fetch_user(e["user_id"])
                    name = user.display_name
                except Exception:
                    name = str(e["user_id"])
                lines.append(
                    f"{rank_emoji(e['rank'])} **{name}** — "
                    f"{format_currency(e['net_worth'])} ({format_percent(e['pct_return'])} return)"
                )
            embed.description = "\n\n".join(lines)
            await interaction.followup.send(embed=embed)
        except ValueError as e:
            await interaction.followup.send(f"**Error:** {e}", ephemeral=True)

    @app_commands.command(name="tournamentinfo", description="View active tournaments")
    @app_commands.checks.cooldown(1, 5.0)
    async def tournament_info(self, interaction: discord.Interaction):
        await interaction.response.defer()
        tournaments = await self.bot.tournaments.get_active_tournaments()
        if not tournaments:
            await interaction.followup.send("No active tournaments. Ask an admin to create one!")
            return

        embed = discord.Embed(title="Active Tournaments", color=discord.Color.blue())
        for t in tournaments:
            status_emoji = "⏳" if t["status"] == "pending" else "🏁"
            embed.add_field(
                name=f"{status_emoji} {t['name']} (ID: {t['id']})",
                value=(
                    f"Status: **{t['status'].title()}**\n"
                    f"Start Cash: {format_currency(t['start_cash'])}\n"
                    f"Prizes: 🥇{format_currency(t['reward_1st'])} "
                    f"🥈{format_currency(t['reward_2nd'])} 🥉{format_currency(t['reward_3rd'])}\n"
                    f"Ends: {(t.get('end_time') or 'TBD')[:16]}"
                ),
                inline=False,
            )
        embed.set_footer(text="Use /jointournament <id> to enter")
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(TournamentCommands(bot))
