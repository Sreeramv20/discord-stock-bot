import logging

from discord.ext import commands, tasks

import config

logger = logging.getLogger(__name__)


class MarketTasks(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.update_prices.start()
        self.check_limit_orders.start()
        self.process_events.start()
        self.process_options.start()

    def cog_unload(self):
        self.update_prices.cancel()
        self.check_limit_orders.cancel()
        self.process_events.cancel()
        self.process_options.cancel()

    @tasks.loop(seconds=config.MARKET_UPDATE_INTERVAL)
    async def update_prices(self):
        try:
            await self.bot.market.update_all_prices()

            event = await self.bot.events.maybe_trigger_event()
            if event:
                await self.bot.notifications.notify_market_event(event)

            dividend = await self.bot.events.maybe_issue_dividend()
            if dividend:
                await self.bot.notifications.notify_dividend(dividend)

            split = await self.bot.events.maybe_stock_split()
            if split:
                await self.bot.notifications.notify_stock_split(split)

        except Exception as e:
            logger.error("Market update error: %s", e, exc_info=True)

    @update_prices.before_loop
    async def before_update_prices(self):
        await self.bot.wait_until_ready()

    @tasks.loop(seconds=60)
    async def check_limit_orders(self):
        try:
            filled = await self.bot.trading.check_limit_orders()
            for order in filled:
                await self.bot.notifications.notify_limit_order_filled(order)
        except Exception as e:
            logger.error("Limit order check error: %s", e, exc_info=True)

    @check_limit_orders.before_loop
    async def before_check_limit_orders(self):
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=10)
    async def process_events(self):
        try:
            await self.bot.events.cleanup_expired()
        except Exception as e:
            logger.error("Event cleanup error: %s", e, exc_info=True)

    @process_events.before_loop
    async def before_process_events(self):
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=30)
    async def process_options(self):
        try:
            results = await self.bot.trading.process_expired_options()
            for opt in results:
                await self.bot.notifications.notify_option_result(opt)
        except Exception as e:
            logger.error("Options processing error: %s", e, exc_info=True)

    @process_options.before_loop
    async def before_process_options(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(MarketTasks(bot))
