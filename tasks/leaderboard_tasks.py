import logging

from discord.ext import commands, tasks

import config

logger = logging.getLogger(__name__)


class LeaderboardTasks(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.refresh_leaderboard.start()

    def cog_unload(self):
        self.refresh_leaderboard.cancel()

    @tasks.loop(seconds=config.LEADERBOARD_UPDATE_INTERVAL)
    async def refresh_leaderboard(self):
        try:
            await self.bot.leaderboard.update_rankings()
        except Exception as e:
            logger.error("Leaderboard refresh error: %s", e, exc_info=True)

    @refresh_leaderboard.before_loop
    async def before_refresh(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(LeaderboardTasks(bot))
