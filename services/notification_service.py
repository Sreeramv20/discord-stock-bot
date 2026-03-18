import logging

import discord

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, bot):
        self.bot = bot

    async def notify_user(self, discord_id: int, content: str | None = None,
                          embed: discord.Embed | None = None):
        try:
            user = await self.bot.fetch_user(discord_id)
            if user:
                await user.send(content=content, embed=embed)
                logger.debug("DM sent to %s", discord_id)
        except discord.Forbidden:
            logger.debug("Cannot DM user %s (DMs disabled)", discord_id)
        except Exception as e:
            logger.warning("Failed to DM user %s: %s", discord_id, e)

    async def notify_limit_order_filled(self, order: dict):
        embed = discord.Embed(
            title="Limit Order Filled!",
            color=discord.Color.green(),
        )
        embed.add_field(
            name=f"{order['order_type'].upper()} {order['ticker']}",
            value=(
                f"Shares: {order['shares']}\n"
                f"Target: ${order['target_price']:,.2f}\n"
                f"Filled at: ${order.get('fill_price', order['target_price']):,.2f}"
            ),
        )
        await self.notify_user(order["user_id"], embed=embed)

    async def notify_market_event(self, event: dict):
        embed = discord.Embed(
            title="Market Event",
            description=event.get("description", event.get("event_type", "Unknown")),
            color=discord.Color.orange(),
        )
        affected = event.get("affected_tickers", [])
        if affected:
            embed.add_field(name="Affected Stocks", value=", ".join(affected))
        mult = event.get("multiplier", 1.0)
        effect = f"{(mult - 1) * 100:+.0f}%" if mult != 1.0 else "Neutral"
        embed.add_field(name="Effect", value=effect)
        duration_min = event.get("duration", 0) // 60
        embed.add_field(name="Duration", value=f"{duration_min} minutes")

        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    try:
                        await channel.send(embed=embed)
                    except Exception:
                        pass
                    break

    async def notify_dividend(self, dividend: dict):
        for payout in dividend.get("payouts", []):
            embed = discord.Embed(
                title="Dividend Received!",
                description=f"**{dividend['ticker']}** paid a dividend",
                color=discord.Color.gold(),
            )
            embed.add_field(
                name="Payout",
                value=f"${payout['payout']:,.2f} (${dividend['amount_per_share']:.4f}/share)",
            )
            await self.notify_user(payout["user_id"], embed=embed)

    async def notify_stock_split(self, split: dict):
        embed = discord.Embed(
            title="Stock Split!",
            description=f"**{split['ticker']}** has split {split['ratio']}:1",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Old Price", value=f"${split['old_price']:,.2f}")
        embed.add_field(name="New Price", value=f"${split['new_price']:,.2f}")
        embed.add_field(name="Effect", value=f"Your shares have been multiplied by {split['ratio']}x")

        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    try:
                        await channel.send(embed=embed)
                    except Exception:
                        pass
                    break

    async def notify_achievement(self, discord_id: int, achievement_ids: list[str]):
        import config
        for ach_id in achievement_ids:
            defn = config.ACHIEVEMENTS.get(ach_id, {})
            embed = discord.Embed(
                title="Achievement Unlocked!",
                description=f"{defn.get('icon', '🏆')} **{defn.get('name', ach_id)}**",
                color=discord.Color.gold(),
            )
            embed.add_field(name="Description", value=defn.get("description", ""))
            await self.notify_user(discord_id, embed=embed)

    async def notify_option_result(self, option: dict):
        status = option.get("status", "expired")
        payout = option.get("payout", 0)
        color = discord.Color.green() if payout > 0 else discord.Color.red()
        embed = discord.Embed(
            title=f"Option {status.title()}!",
            description=f"{option['option_type'].upper()} on **{option['ticker']}**",
            color=color,
        )
        embed.add_field(name="Strike", value=f"${option['strike_price']:,.2f}")
        embed.add_field(name="Final Price", value=f"${option.get('final_price', 0):,.2f}")
        embed.add_field(name="Payout", value=f"${payout:,.2f}")
        await self.notify_user(option["user_id"], embed=embed)
