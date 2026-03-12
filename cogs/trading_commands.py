import discord
from discord.ext import commands
from trading import TradingEngine
from portfolio import PortfolioSystem
from database import get_db_connection
import logging

logger = logging.getLogger(__name__)

class TradingCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.trading_engine = TradingEngine()
        self.portfolio_system = PortfolioSystem()
        
    @commands.slash_command(name="buy", description="Buy stocks")
    async def buy(self, ctx, symbol: str, quantity: int):
        """Buy stocks"""
        if quantity <= 0:
            await ctx.respond("Quantity must be greater than 0.")
            return
            
        success, message = await self.trading_engine.buy_stock(
            ctx.user.id, symbol.upper(), quantity
        )
        
        if success:
            await ctx.respond(message)
        else:
            await ctx.respond(f"Error: {message}")
            
    @commands.slash_command(name="sell", description="Sell stocks")
    async def sell(self, ctx, symbol: str, quantity: int):
        """Sell stocks"""
        if quantity <= 0:
            await ctx.respond("Quantity must be greater than 0.")
            return
            
        success, message = await self.trading_engine.sell_stock(
            ctx.user.id, symbol.upper(), quantity
        )
        
        if success:
            await ctx.respond(message)
        else:
            await ctx.respond(f"Error: {message}")
            
    @commands.slash_command(name="balance", description="Check your balance")
    async def balance(self, ctx):
        """Check user's cash balance"""
        balance = await self.portfolio_system.get_user_balance(ctx.user.id)
        
        embed = discord.Embed(
            title=f"{ctx.user.display_name}'s Balance",
            description=f"Cash: ${balance:.2f}",
            color=discord.Color.green()
        )
        
        await ctx.respond(embed=embed)
        
    @commands.slash_command(name="history", description="View your trade history")
    async def history(self, ctx):
        """View user's trade history"""
        try:
            conn = get_db_connection("stock_trading.db")
            cursor = conn.cursor()
            
            # Get last 10 transactions for the user
            cursor.execute('''
                SELECT stock_symbol, transaction_type, quantity, price, total_amount, timestamp
                FROM transactions 
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT 10
            ''', (ctx.user.id,))
            
            transactions = cursor.fetchall()
            
            if not transactions:
                await ctx.respond("You have no transaction history.")
                return
                
            # Create embed with transaction history
            embed = discord.Embed(
                title=f"{ctx.user.display_name}'s Transaction History",
                color=discord.Color.blue()
            )
            
            for transaction in transactions:
                transaction_type = transaction['transaction_type'].upper()
                symbol = transaction['stock_symbol']
                quantity = transaction['quantity']
                price = transaction['price']
                total_amount = transaction['total_amount']
                timestamp = transaction['timestamp']
                
                embed.add_field(
                    name=f"{transaction_type} {quantity} shares of {symbol}",
                    value=f"Price: ${price:.2f}\nTotal: ${total_amount:.2f}\nTime: {timestamp}",
                    inline=False
                )
                
            await ctx.respond(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting transaction history: {e}")
            await ctx.respond("Error retrieving transaction history.")
        finally:
            if 'conn' in locals():
                conn.close()
                
    @commands.slash_command(name="stats", description="View your trading statistics")
    async def stats(self, ctx):
        """View user's trading statistics"""
        try:
            # Get performance metrics
            metrics = await self.portfolio_system.get_user_performance_metrics(ctx.user.id)
            
            # Calculate win rate
            win_rate = 0.0
            if metrics['total_trades'] > 0:
                win_rate = (metrics['wins'] / metrics['total_trades']) * 100
            
            # Create embed with stats
            embed = discord.Embed(
                title=f"{ctx.user.display_name}'s Trading Stats",
                color=discord.Color.purple()
            )
            
            embed.add_field(
                name="Total Profit/Loss",
                value=f"${metrics['total_profit']:.2f}",
                inline=True
            )
            
            embed.add_field(
                name="Total Trades",
                value=str(metrics['total_trades']),
                inline=True
            )
            
            embed.add_field(
                name="Wins",
                value=str(metrics['wins']),
                inline=True
            )
            
            embed.add_field(
                name="Losses",
                value=str(metrics['losses']),
                inline=True
            )
            
            embed.add_field(
                name="Win Rate",
                value=f"{win_rate:.1f}%",
                inline=True
            )
            
            embed.add_field(
                name="ROI",
                value=f"{metrics['roi']:.2f}%",
                inline=True
            )
            
            await ctx.respond(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            await ctx.respond("Error retrieving trading statistics.")
        finally:
            if 'conn' in locals():
                conn.close()

def setup(bot):
    bot.add_cog(TradingCommands(bot))
