import discord
from discord.ext import commands
from trading import TradingEngine
from database import get_db_connection
import logging

logger = logging.getLogger(__name__)

class TradingCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.trading_engine = TradingEngine()
        
    @commands.slash_command(name="buy", description="Buy stocks")
    async def buy(self, ctx, symbol: str, quantity: int):
        """Buy stocks"""
        if quantity <= 0:
            await ctx.respond("Quantity must be greater than 0.", ephemeral=True)
            return
            
        try:
            success = await self.trading_engine.buy_stock(
                ctx.user.id, symbol.upper(), quantity
            )
            
            if success:
                await ctx.respond(f"Successfully bought {quantity} shares of {symbol.upper()}!", ephemeral=True)
            else:
                await ctx.respond("Failed to buy stocks. Check if you have enough funds or if the stock exists.", ephemeral=True)
                
        except ValueError as e:
            await ctx.respond(str(e), ephemeral=True)
        except Exception as e:
            logger.error(f"Error buying stocks: {e}")
            await ctx.respond("An error occurred while processing your buy order.", ephemeral=True)
            
    @commands.slash_command(name="sell", description="Sell stocks")
    async def sell(self, ctx, symbol: str, quantity: int):
        """Sell stocks"""
        if quantity <= 0:
            await ctx.respond("Quantity must be greater than 0.", ephemeral=True)
            return
            
        try:
            success = await self.trading_engine.sell_stock(
                ctx.user.id, symbol.upper(), quantity
            )
            
            if success:
                await ctx.respond(f"Successfully sold {quantity} shares of {symbol.upper()}!", ephemeral=True)
            else:
                await ctx.respond("Failed to sell stocks. Check if you own enough shares or if the stock exists.", ephemeral=True)
                
        except ValueError as e:
            await ctx.respond(str(e), ephemeral=True)
        except Exception as e:
            logger.error(f"Error selling stocks: {e}")
            await ctx.respond("An error occurred while processing your sell order.", ephemeral=True)
            
    @commands.slash_command(name="balance", description="Check your balance")
    async def balance(self, ctx):
        """Check user's cash balance"""
        try:
            balance = self.trading_engine.get_user_balance(ctx.user.id)
            
            embed = discord.Embed(
                title=f"{ctx.user.display_name}'s Balance",
                description=f"Cash: ${balance:.2f}",
                color=discord.Color.green()
            )
            
            await ctx.respond(embed=embed)
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            await ctx.respond("Could not retrieve balance.", ephemeral=True)
        
    @commands.slash_command(name="history", description="View your trade history")
    async def history(self, ctx):
        """View user's trade history"""
        try:
            transactions = await self.trading_engine.get_user_transactions(ctx.user.id)
            
            if not transactions:
                await ctx.respond("You have no transaction history.", ephemeral=True)
                return
                
            # Create embed with transaction history
            embed = discord.Embed(
                title=f"{ctx.user.display_name}'s Transaction History",
                color=discord.Color.blue()
            )
            
            for transaction in transactions[-10:]:  # Show last 10 transactions
                transaction_type = transaction['type'].upper()
                symbol = transaction['symbol']
                quantity = transaction['quantity']
                price = transaction['price']
                total_amount = transaction['total_amount']
                
                embed.add_field(
                    name=f"{transaction_type} {quantity} shares of {symbol}",
                    value=f"Price: ${price:.2f}\nTotal: ${total_amount:.2f}",
                    inline=False
                )
                
            await ctx.respond(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting transaction history: {e}")
            await ctx.respond("Error retrieving transaction history.", ephemeral=True)
            
    @commands.slash_command(name="stats", description="View your trading statistics")
    async def stats(self, ctx):
        """View user's trading statistics"""
        try:
            # Get performance metrics
            stats = await self.trading_engine.get_user_stats(ctx.user.id)
            
            # Create embed with stats
            embed = discord.Embed(
                title=f"{ctx.user.display_name}'s Trading Stats",
                color=discord.Color.purple()
            )
            
            embed.add_field(
                name="Total Buys",
                value=str(stats['total_buys']),
                inline=True
            )
            
            embed.add_field(
                name="Total Sells",
                value=str(stats['total_sells']),
                inline=True
            )
            
            embed.add_field(
                name="Net Profit/Loss",
                value=f"${stats['net_profit_loss']:.2f}",
                inline=False
            )
            
            await ctx.respond(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            await ctx.respond("Error retrieving trading statistics.", ephemeral=True)

def setup(bot):
    bot.add_cog(TradingCommands(bot))
