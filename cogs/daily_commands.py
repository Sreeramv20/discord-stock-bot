import logging
import random
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands

import config
from utils.formatting import format_currency

logger = logging.getLogger(__name__)


class DailyCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="daily", description="Claim your daily cash reward")
    @app_commands.checks.cooldown(1, 10.0)
    async def daily(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            await self.bot.db.ensure_user(interaction.user.id, interaction.user.display_name)

            last_claim = await self.bot.db.get_last_daily(interaction.user.id)
            now = datetime.now(timezone.utc)

            if last_claim:
                try:
                    last_dt = datetime.fromisoformat(last_claim)
                    if last_dt.tzinfo is None:
                        last_dt = last_dt.replace(tzinfo=timezone.utc)
                    diff = now - last_dt
                    if diff < timedelta(hours=24):
                        remaining = timedelta(hours=24) - diff
                        hours = int(remaining.total_seconds() // 3600)
                        minutes = int((remaining.total_seconds() % 3600) // 60)
                        embed = discord.Embed(
                            title="Daily Reward",
                            description=f"You already claimed today! Come back in **{hours}h {minutes}m**.",
                            color=discord.Color.orange(),
                        )
                        await interaction.followup.send(embed=embed)
                        return
                except (ValueError, TypeError):
                    pass

            base_reward = random.randint(config.DAILY_MIN_REWARD, config.DAILY_MAX_REWARD)
            prestige_mult = await self.bot.prestige.get_daily_multiplier(interaction.user.id)
            reward = int(base_reward * prestige_mult)
            await self.bot.db.increment_user_balance(interaction.user.id, reward)
            await self.bot.db.set_daily_claimed(interaction.user.id)
            new_balance = await self.bot.db.get_user_balance(interaction.user.id)

            embed = discord.Embed(
                title="Daily Reward Claimed!",
                description=f"You received **{format_currency(reward)}**!",
                color=discord.Color.green(),
            )
            embed.add_field(name="New Balance", value=format_currency(new_balance))
            if prestige_mult > 1.0:
                embed.add_field(name="Prestige Bonus", value=f"{prestige_mult:.1f}x multiplier")
            embed.set_footer(text="Come back tomorrow for more!")
            await interaction.followup.send(embed=embed)

            awarded = await self.bot.achievements.check_and_award(interaction.user.id)
            if awarded:
                await self.bot.notifications.notify_achievement(interaction.user.id, awarded)
        except Exception as e:
            logger.error("Daily command error: %s", e, exc_info=True)
            await interaction.followup.send("Failed to claim daily reward.", ephemeral=True)

    @app_commands.command(name="achievements", description="View your achievements")
    @app_commands.checks.cooldown(1, 5.0)
    async def achievements(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            display = await self.bot.achievements.get_achievements_display(interaction.user.id)

            if not display:
                all_achs = config.ACHIEVEMENTS
                embed = discord.Embed(
                    title=f"{interaction.user.display_name}'s Achievements",
                    description="No achievements yet! Start trading to unlock them.",
                    color=discord.Color.greyple(),
                )
                preview = "\n".join(
                    f"{a['icon']} **{a['name']}** — {a['description']}"
                    for a in list(all_achs.values())[:5]
                )
                embed.add_field(name="Available Achievements", value=preview, inline=False)
                embed.set_footer(text=f"{len(all_achs)} achievements to unlock")
                await interaction.followup.send(embed=embed)
                return

            embed = discord.Embed(
                title=f"{interaction.user.display_name}'s Achievements",
                description=f"**{len(display)}/{len(config.ACHIEVEMENTS)}** unlocked",
                color=discord.Color.gold(),
            )

            for ach in display:
                embed.add_field(
                    name=f"{ach['icon']} {ach['name']}",
                    value=f"{ach['description']}\n*Earned: {ach['earned_at'][:10]}*",
                    inline=False,
                )

            unearned_ids = set(config.ACHIEVEMENTS.keys()) - {a["id"] for a in display}
            if unearned_ids:
                locked = ", ".join(
                    f"{config.ACHIEVEMENTS[aid]['icon']} {config.ACHIEVEMENTS[aid]['name']}"
                    for aid in list(unearned_ids)[:5]
                )
                embed.set_footer(text=f"Locked: {locked}{'...' if len(unearned_ids) > 5 else ''}")

            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error("Achievements error: %s", e, exc_info=True)
            await interaction.followup.send("Failed to load achievements.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(DailyCommands(bot))
