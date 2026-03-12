import discord
from discord.ext import commands
from leaderboard import Leaderboard

class LeaderboardCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.leaderboard = Leaderboard()
        
    @commands.slash_command(name="leaderboard", description="View the leaderboard")
    async def leaderboard(self, ctx):
        """Display the leaderboard"""
        top_users = await self.leaderboard.get_leaderboard(10)
        
        if not top_users:
            await ctx.respond("No users in the leaderboard yet.")
            return
            
        embed = discord.Embed(
            title="Leaderboard",
            description="Top 10 Users by Net Worth",
            color=discord.Color.gold()
        )
        
        for i, user in enumerate(top_users, 1):
            embed.add_field(
                name=f"{i}. {user['username']}",
                value=f"Net Worth: ${user['net_worth']:.2f}\nProfit: ${user['total_profit']:.2f}",
                inline=False
            )
            
        await ctx.respond(embed=embed)
        
    @commands.slash_command(name="rank", description="Check your rank in the leaderboard")
    async def rank(self, ctx):
        """Display user's rank"""
        user_data = await self.leaderboard.get_user_rank(ctx.user.id)
        
        if not user_data:
            await ctx.respond("You are not in the leaderboard yet.")
            return
            
        embed = discord.Embed(
            title=f"{ctx.user.display_name}'s Rank",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Rank", value=user_data['rank'])
        embed.add_field(name="Net Worth", value=f"${user_data['net_worth']:.2f}")
        embed.add_field(name="Total Profit", value=f"${user_data['total_profit']:.2f}")
        
        await ctx.respond(embed=embed)

def setup(bot):
    bot.add_cog(LeaderboardCommands(bot))
