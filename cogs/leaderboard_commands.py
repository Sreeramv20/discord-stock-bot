import logging

import discord
from discord import app_commands
from discord.ext import commands

from utils.formatting import format_currency, rank_emoji, profit_emoji

logger = logging.getLogger(__name__)


class LeaderboardCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="leaderboard", description="View the top traders leaderboard")
    @app_commands.checks.cooldown(1, 10.0)
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            top = await self.bot.leaderboard.get_top(10)
            if not top:
                await interaction.followup.send(
                    "Leaderboard is empty. Start trading to get ranked!"
                )
                return

            embed = discord.Embed(
                title="Leaderboard — Top Traders",
                color=discord.Color.gold(),
            )

            lines = []
            for entry in top:
                rank = entry.get("rank", "?")
                username = entry.get("username", str(entry["user_id"]))

                try:
                    user = await self.bot.fetch_user(entry["user_id"])
                    if user:
                        username = user.display_name
                except Exception:
                    pass

                nw = entry.get("net_worth", 0)
                profit = entry.get("profit", 0)
                emoji = profit_emoji(profit)
                lines.append(
                    f"{rank_emoji(rank)} **{username}**\n"
                    f"  Net Worth: {format_currency(nw)} | "
                    f"Profit: {emoji} {format_currency(profit)}"
                )

            embed.description = "\n\n".join(lines)
            embed.set_footer(text="Rankings update periodically")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error("Leaderboard error: %s", e, exc_info=True)
            await interaction.followup.send("Failed to load leaderboard.", ephemeral=True)

    @app_commands.command(name="rank", description="Check your ranking on the leaderboard")
    @app_commands.checks.cooldown(1, 5.0)
    async def rank(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            entry = await self.bot.leaderboard.get_rank(interaction.user.id)
            if not entry:
                await interaction.followup.send(
                    "You're not ranked yet. Make a trade or claim `/daily` to get started!",
                    ephemeral=True,
                )
                return

            profit = entry.get("profit", 0)
            embed = discord.Embed(
                title=f"{interaction.user.display_name}'s Ranking",
                color=discord.Color.blue(),
            )
            embed.add_field(name="Rank", value=rank_emoji(entry["rank"]), inline=True)
            embed.add_field(name="Net Worth", value=format_currency(entry["net_worth"]), inline=True)
            embed.add_field(
                name="Profit",
                value=f"{profit_emoji(profit)} {format_currency(profit)}",
                inline=True,
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error("Rank error: %s", e, exc_info=True)
            await interaction.followup.send("Failed to get rank.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(LeaderboardCommands(bot))
