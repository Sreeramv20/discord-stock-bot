import discord
from discord.ext import commands
import asyncio
import logging
from datetime import datetime, timedelta
from database import get_db_connection, update_user_balance, get_user_balance

logger = logging.getLogger(__name__)

class DailyCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.slash_command(name="daily", description="Claim your daily reward")
    async def daily(self, ctx):
        """Claim daily reward with cooldown"""
        try:
            conn = get_db_connection("stock_trading.db")
            cursor = conn.cursor()
            
            # Check if user has claimed today
            cursor.execute('''
                SELECT last_daily_claim FROM users WHERE user_id = ?
            ''', (ctx.user.id,))
            
            result = cursor.fetchone()
            
            if result and result[0]:
                last_claim = datetime.fromisoformat(result[0])
                now = datetime.utcnow()
                
                # Check if 24 hours have passed since last claim
                if now - last_claim < timedelta(hours=24):
                    time_left = timedelta(hours=24) - (now - last_claim)
                    await ctx.respond(f"You can claim your daily reward again in {time_left}")
                    return
            
            # Generate random reward between $500 and $2000
            import random
            reward = random.randint(500, 2000)
            
            # Update user balance
            current_balance = get_user_balance(ctx.user.id, "stock_trading.db")
            if current_balance is None:
                # User doesn't exist in database, create them
                cursor.execute('''
                    INSERT OR IGNORE INTO users (user_id, cash_balance) 
                    VALUES (?, ?)
                ''', (ctx.user.id, 0))
                current_balance = 0
            
            new_balance = current_balance + reward
            update_user_balance(ctx.user.id, new_balance, "stock_trading.db")
            
            # Update last daily claim time
            cursor.execute('''
                UPDATE users SET last_daily_claim = ?
                WHERE user_id = ?
            ''', (datetime.utcnow().isoformat(), ctx.user.id))
            
            conn.commit()
            
            await ctx.respond(f"You've claimed your daily reward of ${reward:,}!")
            
        except Exception as e:
            logger.error(f"Error claiming daily reward: {e}")
            await ctx.respond("Error claiming daily reward.")
        finally:
            if 'conn' in locals():
                conn.close()
                
    @commands.slash_command(name="achievements", description="View your achievements")
    async def achievements(self, ctx):
        """View user's achievements"""
        try:
            conn = get_db_connection("stock_trading.db")
            cursor = conn.cursor()
            
            # Get user's achievements
            cursor.execute('''
                SELECT achievement_name, achieved_at FROM achievements 
                WHERE user_id = ?
                ORDER BY achieved_at DESC
            ''', (ctx.user.id,))
            
            achievements = cursor.fetchall()
            
            if not achievements:
                await ctx.respond("You haven't earned any achievements yet.")
                return
                
            # Create embed with achievements
            embed = discord.Embed(
                title=f"{ctx.user.display_name}'s Achievements",
                color=discord.Color.gold()
            )
            
            for achievement in achievements:
                name = achievement['achievement_name']
                achieved_at = achievement['achieved_at']
                
                embed.add_field(
                    name=name,
                    value=f"Achieved: {achieved_at}",
                    inline=False
                )
                
            await ctx.respond(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting achievements: {e}")
            await ctx.respond("Error retrieving achievements.")
        finally:
            if 'conn' in locals():
                conn.close()

def setup(bot):
    bot.add_cog(DailyCommands(bot))
