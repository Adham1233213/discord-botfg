import discord
from discord.ext import commands
import asyncio
import os
from config import Config
from database import Database
from moderation import ModerationCog
from games import GamesCog
from anti_spam import AntiSpamCog
from anti_raid import AntiRaidCog
from anti_nuke import AntiNukeCog
from logging_system import LoggingCog

# Bot configuration
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize database
db = Database()

@bot.event
async def on_ready():
    print(f'{bot.user} has logged in!')
    print(f'Bot ID: {bot.user.id}')
    print('Initializing database...')
    await db.initialize()
    print('Database initialized!')
    
    # Set bot status
    await bot.change_presence(activity=discord.Game(name="Moderating the server | !help"))

@bot.event
async def on_guild_join(guild):
    """When bot joins a new guild, create log channel if it doesn't exist"""
    log_channel = discord.utils.get(guild.channels, name='mod-logs')
    if not log_channel:
        try:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            log_channel = await guild.create_text_channel('mod-logs', overwrites=overwrites)
            await log_channel.send("🔧 **Moderation Log Channel Created**\nThis channel will log all moderation activities.")
        except discord.Forbidden:
            print(f"Could not create log channel in {guild.name} - insufficient permissions")

async def setup_cogs():
    """Setup all bot cogs"""
    await bot.add_cog(ModerationCog(bot, db))
    await bot.add_cog(GamesCog(bot, db))
    await bot.add_cog(AntiSpamCog(bot, db))
    await bot.add_cog(AntiRaidCog(bot, db))
    await bot.add_cog(AntiNukeCog(bot, db))
    await bot.add_cog(LoggingCog(bot, db))

async def main():
    """Main bot startup function"""
    async with bot:
        await setup_cogs()
        await bot.start(Config.MTM3NjkwOTE0MzkyNjg5ODcxOA.GMGsuI.bfSRQXM36oz6xWVp27v9yUR9BEJLWtk2Dx8Rmw)

if __name__ == "__main__":
    asyncio.run(main())
