import logging

from discord.ext import commands, tasks

import config

logger = logging.getLogger(__name__)


class ViralTasks(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_margins.start()
        self.process_tournaments.start()
        self.process_ipos.start()
        self.generate_leaks.start()
        self.pump_dump_cycle.start()

    def cog_unload(self):
        self.check_margins.cancel()
        self.process_tournaments.cancel()
        self.process_ipos.cancel()
        self.generate_leaks.cancel()
        self.pump_dump_cycle.cancel()

    @tasks.loop(seconds=config.MARGIN_CHECK_INTERVAL)
    async def check_margins(self):
        try:
            liquidated = await self.bot.margin.check_liquidations()
            for liq in liquidated:
                try:
                    user = await self.bot.fetch_user(liq["user_id"])
                    if user:
                        import discord
                        embed = discord.Embed(
                            title="⚠️ Margin Position Liquidated!",
                            description=f"Your **{liq['ticker']}** margin position was liquidated.",
                            color=discord.Color.red(),
                        )
                        embed.add_field(name="Entry Price",
                                        value=f"${liq['entry_price']:,.2f}", inline=True)
                        embed.add_field(name="Liquidation Price",
                                        value=f"${liq['liq_price']:,.2f}", inline=True)
                        embed.add_field(name="Loss",
                                        value=f"${liq['loss']:,.2f}", inline=True)
                        await user.send(embed=embed)
                except Exception:
                    pass
        except Exception as e:
            logger.error("Margin check error: %s", e, exc_info=True)

    @check_margins.before_loop
    async def before_check_margins(self):
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=2)
    async def process_tournaments(self):
        try:
            started = await self.bot.tournaments.start_pending_tournaments()
            for t in started:
                await self._broadcast(f"🏁 **Tournament Started:** {t['name']} (ID: {t['id']})")

            ended = await self.bot.tournaments.end_expired_tournaments()
            for t in ended:
                results = t.get("results", [])
                msg = f"🏆 **Tournament Ended:** {t['name']}\n"
                for r in results[:3]:
                    try:
                        user = await self.bot.fetch_user(r["user_id"])
                        name = user.display_name
                    except Exception:
                        name = str(r["user_id"])
                    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
                    msg += f"{medals.get(r['rank'], '')} {name} — {r['pct_return']:+.1f}% return\n"
                await self._broadcast(msg)
        except Exception as e:
            logger.error("Tournament task error: %s", e, exc_info=True)

    @process_tournaments.before_loop
    async def before_process_tournaments(self):
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=5)
    async def process_ipos(self):
        try:
            ipo = await self.bot.ipo_service.maybe_launch_ipo()
            if ipo:
                import discord
                embed = discord.Embed(
                    title="🚀 NEW IPO ANNOUNCED!",
                    description=f"**{ipo['ticker']}** — {ipo['name']}",
                    color=discord.Color.blue(),
                )
                embed.add_field(name="Initial Price",
                                value=f"${ipo['price']:,.2f}", inline=True)
                embed.add_field(name="Sector", value=ipo.get("sector", "N/A"), inline=True)
                embed.add_field(name="Trading Opens", value=ipo["opens_at"][:16], inline=True)
                embed.set_footer(text="Use /ipos to see all active IPOs")
                await self._broadcast_embed(embed)

            transitions = await self.bot.ipo_service.process_ipo_phases()
            for t in transitions:
                if t.get("new_phase") == "open":
                    await self._broadcast(
                        f"🟢 **IPO NOW OPEN:** {t['ticker']} — {t['name']} "
                        f"at ${t['initial_price']:,.2f}. Buy now!"
                    )
        except Exception as e:
            logger.error("IPO task error: %s", e, exc_info=True)

    @process_ipos.before_loop
    async def before_process_ipos(self):
        await self.bot.wait_until_ready()

    @tasks.loop(hours=4)
    async def generate_leaks(self):
        try:
            await self.bot.insiders.generate_leaks(3)
            await self.bot.insiders.apply_leak_effects()
        except Exception as e:
            logger.error("Leak generation error: %s", e, exc_info=True)

    @generate_leaks.before_loop
    async def before_generate_leaks(self):
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=5)
    async def pump_dump_cycle(self):
        try:
            event = await self.bot.events.maybe_trigger_pump_dump()
            if event:
                await self.bot.notifications.notify_market_event(event)
        except Exception as e:
            logger.error("Pump/dump cycle error: %s", e, exc_info=True)

    @pump_dump_cycle.before_loop
    async def before_pump_dump(self):
        await self.bot.wait_until_ready()

    async def _broadcast(self, content: str):
        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    try:
                        await channel.send(content)
                    except Exception:
                        pass
                    break

    async def _broadcast_embed(self, embed):
        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    try:
                        await channel.send(embed=embed)
                    except Exception:
                        pass
                    break


async def setup(bot: commands.Bot):
    await bot.add_cog(ViralTasks(bot))
