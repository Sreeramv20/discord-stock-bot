import logging

import discord
from discord import app_commands
from discord.ext import commands

from utils.formatting import format_currency

logger = logging.getLogger(__name__)


class SocialCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Copy Trading ────────────────────────────────────────────────

    @app_commands.command(name="copytrader", description="Automatically mirror another trader's moves")
    @app_commands.describe(user="The trader to copy")
    @app_commands.checks.cooldown(1, 10.0)
    async def copy_trader(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)
        try:
            result = await self.bot.copy_trades.follow(interaction.user.id, user.id)
            embed = discord.Embed(
                title="Copy Trading Activated",
                description=f"You are now copy-trading **{user.display_name}**",
                color=discord.Color.green(),
            )
            embed.add_field(name="Max Trade %", value="10% of your balance per trade")
            embed.set_footer(text="Their buys/sells will be automatically mirrored")
            await interaction.followup.send(embed=embed)
        except ValueError as e:
            await interaction.followup.send(f"**Error:** {e}", ephemeral=True)

    @app_commands.command(name="unfollow", description="Stop copy-trading a user")
    @app_commands.describe(user="The trader to unfollow")
    @app_commands.checks.cooldown(1, 5.0)
    async def unfollow(self, interaction: discord.Interaction, user: discord.Member):
        success = await self.bot.copy_trades.unfollow(interaction.user.id, user.id)
        if success:
            await interaction.response.send_message(
                f"Stopped copy-trading **{user.display_name}**.", ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "You are not copy-trading this user.", ephemeral=True,
            )

    @app_commands.command(name="copystatus", description="View your copy-trading relationships")
    @app_commands.checks.cooldown(1, 5.0)
    async def copy_status(self, interaction: discord.Interaction):
        await interaction.response.defer()
        following = await self.bot.copy_trades.get_following(interaction.user.id)
        followers = await self.bot.copy_trades.get_followers(interaction.user.id)

        embed = discord.Embed(
            title=f"{interaction.user.display_name}'s Copy Trading",
            color=discord.Color.blue(),
        )

        if following:
            lines = []
            for f in following:
                try:
                    user = await self.bot.fetch_user(f["leader_id"])
                    name = user.display_name
                except Exception:
                    name = str(f["leader_id"])
                lines.append(f"📋 Following **{name}** ({f['max_trade_pct']*100:.0f}% per trade)")
            embed.add_field(name="Following", value="\n".join(lines), inline=False)
        else:
            embed.add_field(name="Following", value="Nobody yet", inline=False)

        embed.add_field(name="Followers", value=str(len(followers)), inline=True)
        await interaction.followup.send(embed=embed)

    # ── Insider Leaks ───────────────────────────────────────────────

    @app_commands.command(name="insider", description="Purchase insider market intelligence")
    @app_commands.describe(leak_id="Specific leak ID to buy (omit to see available)")
    @app_commands.checks.cooldown(1, 10.0)
    async def insider(self, interaction: discord.Interaction, leak_id: int | None = None):
        await interaction.response.defer(ephemeral=True)
        try:
            if leak_id is None:
                leaks = await self.bot.insiders.get_available_leaks()
                if not leaks:
                    await interaction.followup.send(
                        "No insider leaks available right now. Check back later!",
                        ephemeral=True,
                    )
                    return

                embed = discord.Embed(
                    title="🕵️ Available Insider Leaks",
                    description="Purchase intel on upcoming market movements",
                    color=discord.Color.dark_grey(),
                )
                for leak in leaks:
                    embed.add_field(
                        name=f"#{leak['id']} — {leak['ticker']}",
                        value=(
                            f"*\"{leak['description']}\"*\n"
                            f"Cost: **{format_currency(leak['cost'])}** | "
                            f"Expires: {leak['expires_at'][:16]}"
                        ),
                        inline=False,
                    )
                embed.set_footer(text="Use /insider <id> to purchase a leak")
                await interaction.followup.send(embed=embed)
            else:
                await self.bot.db.ensure_user(interaction.user.id, interaction.user.display_name)
                result = await self.bot.insiders.purchase_leak(interaction.user.id, leak_id)
                embed = discord.Embed(
                    title="🕵️ Insider Intelligence Acquired",
                    color=discord.Color.dark_gold(),
                )
                embed.add_field(name="Stock", value=result["ticker"], inline=True)
                embed.add_field(name="Signal", value=result["direction"], inline=True)
                embed.add_field(name="Confidence", value=result["confidence"], inline=True)
                embed.add_field(name="Intel", value=f"*\"{result['description']}\"*", inline=False)
                embed.add_field(name="Cost", value=format_currency(result["cost"]), inline=True)
                embed.set_footer(text="⚠️ Rumors may be inaccurate. Trade at your own risk.")
                await interaction.followup.send(embed=embed)
        except ValueError as e:
            await interaction.followup.send(f"**Error:** {e}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(SocialCommands(bot))
