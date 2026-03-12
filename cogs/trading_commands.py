import discord
from discord.ext import commands
from trading import TradingEngine
from portfolio import PortfolioSystem

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

def setup(bot):
    bot.add_cog(TradingCommands(bot))
