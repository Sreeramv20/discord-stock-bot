import discord
from discord.ext import commands
from market import Market

class MarketCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.market = Market()
        
    @commands.slash_command(name="stocks", description="View all available stocks")
    async def stocks(self, ctx):
        """Display all available stocks"""
        stocks = await self.market.get_all_stocks()
        
        if not stocks:
            await ctx.respond("No stocks found in the market.")
            return
            
        embed = discord.Embed(
            title="Available Stocks",
            description="Here are the stocks you can trade:",
            color=discord.Color.blue()
        )
        
        for stock in stocks:
            embed.add_field(
                name=f"{stock['symbol']} - {stock['name']}",
                value=f"Price: ${stock['current_price']:.2f}\nVolume: {stock['volume']}",
                inline=False
            )
            
        await ctx.respond(embed=embed)
        
    @commands.slash_command(name="stock", description="View details of a specific stock")
    async def stock(self, ctx, symbol: str):
        """Display details of a specific stock"""
        stock = await self.market.get_stock_info(symbol.upper())
        
        if not stock:
            await ctx.respond(f"Stock {symbol} not found.")
            return
            
        embed = discord.Embed(
            title=f"{stock['symbol']} - {stock['name']}",
            description=f"Current Price: ${stock['current_price']:.2f}",
            color=discord.Color.green()
        )
        
        embed.add_field(name="Previous Price", value=f"${stock['previous_price']:.2f}" if stock['previous_price'] else "N/A")
        embed.add_field(name="Volume", value=stock['volume'])
        embed.add_field(name="Last Updated", value=stock['last_updated'])
        
        await ctx.respond(embed=embed)

def setup(bot):
    bot.add_cog(MarketCommands(bot))
