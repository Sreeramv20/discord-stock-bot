import discord
from discord.ext import commands
from portfolio import PortfolioSystem

class PortfolioCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.portfolio_system = PortfolioSystem()
        
    @commands.slash_command(name="portfolio", description="View your portfolio")
    async def portfolio(self, ctx):
        """Display user's portfolio"""
        portfolio = await self.portfolio_system.get_user_portfolio(ctx.user.id)
        balance = await self.portfolio_system.get_user_balance(ctx.user.id)
        net_worth = await self.portfolio_system.get_user_net_worth(ctx.user.id)
        
        if not portfolio:
            embed = discord.Embed(
                title=f"{ctx.user.display_name}'s Portfolio",
                description="Your portfolio is empty.",
                color=discord.Color.blue()
            )
            embed.add_field(name="Cash Balance", value=f"${balance:.2f}")
            embed.add_field(name="Net Worth", value=f"${net_worth:.2f}")
            await ctx.respond(embed=embed)
            return
            
        embed = discord.Embed(
            title=f"{ctx.user.display_name}'s Portfolio",
            color=discord.Color.blue()
        )
        
        total_value = 0
        for item in portfolio:
            value = item['current_value']
            total_value += value
            profit_loss = item['profit_loss']
            
            embed.add_field(
                name=f"{item['stock_symbol']}",
                value=f"Qty: {item['quantity']}\nAvg Price: ${item['avg_buy_price']:.2f}\nCurrent: ${item['current_price']:.2f}\nValue: ${value:.2f}\nProfit/Loss: ${profit_loss:.2f}",
                inline=False
            )
            
        embed.add_field(name="Cash Balance", value=f"${balance:.2f}")
        embed.add_field(name="Portfolio Value", value=f"${total_value:.2f}")
        embed.add_field(name="Net Worth", value=f"${net_worth:.2f}")
        
        await ctx.respond(embed=embed)

def setup(bot):
    bot.add_cog(PortfolioCommands(bot))
