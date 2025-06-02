import discord
from discord.ext import commands
from collections import defaultdict, deque
from datetime import datetime, timedelta
import asyncio
from config import Config

class AntiSpamCog(commands.Cog):
    """Anti-spam protection system"""
    
    def __init__(self, bot, database):
        self.bot = bot
        self.db = database
        self.user_messages = defaultdict(deque)  # Track messages per user
        self.warned_users = set()  # Track users who have been warned
    
    async def get_log_channel(self, guild):
        """Get the log channel for the guild"""
        log_channel = discord.utils.get(guild.channels, name=Config.LOG_CHANNEL_NAME)
        return log_channel
    
    async def log_spam_action(self, guild, user, action, message_count):
        """Log anti-spam actions"""
        log_channel = await self.get_log_channel(guild)
        if not log_channel:
            return
        
        embed = discord.Embed(
            title="🚫 Anti-Spam Action",
            color=Config.ERROR_COLOR,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="User", value=f"{user.mention} ({user.id})", inline=True)
        embed.add_field(name="Action", value=action, inline=True)
        embed.add_field(name="Message Count", value=f"{message_count} in 1 minute", inline=True)
        embed.add_field(name="Reason", value="Exceeded spam limit (30 messages/minute)", inline=False)
        
        embed.set_footer(text=f"User ID: {user.id}")
        
        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass
    
    def is_spam(self, user_id):
        """Check if user is spamming based on message frequency"""
        now = datetime.now()
        user_msgs = self.user_messages[user_id]
        
        # Remove messages older than 1 minute
        while user_msgs and now - user_msgs[0] > timedelta(minutes=1):
            user_msgs.popleft()
        
        # Add current message timestamp
        user_msgs.append(now)
        
        # Check if user exceeded limit
        return len(user_msgs) > Config.SPAM_MESSAGE_LIMIT
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Monitor messages for spam"""
        # Ignore bots and DMs
        if message.author.bot or not message.guild:
            return
        
        # Ignore messages from moderators
        if message.author.guild_permissions.manage_messages:
            return
        
        user_id = message.author.id
        
        # Check for spam
        if self.is_spam(user_id):
            try:
                # First violation - warn the user
                if user_id not in self.warned_users:
                    self.warned_users.add(user_id)
                    
                    try:
                        warning_embed = discord.Embed(
                            title="⚠️ Spam Warning",
                            description="You are sending messages too quickly! Please slow down or you will be kicked.",
                            color=Config.WARNING_COLOR
                        )
                        await message.author.send(embed=warning_embed)
                    except discord.Forbidden:
                        pass
                    
                    # Send warning in channel
                    warning_msg = await message.channel.send(
                        f"⚠️ {message.author.mention}, you're sending messages too quickly! Slow down or you'll be kicked."
                    )
                    
                    # Delete warning after 10 seconds
                    await asyncio.sleep(10)
                    try:
                        await warning_msg.delete()
                    except discord.NotFound:
                        pass
                    
                    await self.log_spam_action(message.guild, message.author, "WARNING", len(self.user_messages[user_id]))
                    
                    # Give user 30 seconds to slow down
                    await asyncio.sleep(30)
                    
                    # Check if they're still spamming after warning
                    if self.is_spam(user_id):
                        # Kick the user
                        await message.author.kick(reason="Spam: Exceeded 30 messages per minute after warning")
                        await self.log_spam_action(message.guild, message.author, "KICKED", len(self.user_messages[user_id]))
                        
                        # Clean up tracking
                        del self.user_messages[user_id]
                        self.warned_users.discard(user_id)
                    else:
                        # User slowed down, remove from warned list
                        self.warned_users.discard(user_id)
                
                else:
                    # User was already warned and is still spamming - kick immediately
                    await message.author.kick(reason="Spam: Continued spamming after warning")
                    await self.log_spam_action(message.guild, message.author, "KICKED", len(self.user_messages[user_id]))
                    
                    # Clean up tracking
                    del self.user_messages[user_id]
                    self.warned_users.discard(user_id)
                    
            except discord.Forbidden:
                # Bot doesn't have permission to kick
                try:
                    # Try to timeout instead
                    timeout_duration = timedelta(minutes=10)
                    await message.author.timeout(timeout_duration, reason="Spam: Exceeded message limit")
                    await self.log_spam_action(message.guild, message.author, "TIMED OUT (10 min)", len(self.user_messages[user_id]))
                except discord.Forbidden:
                    # Can't timeout either, just log
                    await self.log_spam_action(message.guild, message.author, "DETECTED (No Permission)", len(self.user_messages[user_id]))
            
            except Exception as e:
                print(f"Error in anti-spam: {e}")
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Clean up tracking when member leaves"""
        user_id = member.id
        if user_id in self.user_messages:
            del self.user_messages[user_id]
        self.warned_users.discard(user_id)
    
    @commands.command(name='antispam')
    @commands.has_permissions(manage_guild=True)
    async def antispam_info(self, ctx):
        """Show anti-spam information and statistics"""
        embed = discord.Embed(
            title="🚫 Anti-Spam System",
            description="Information about the anti-spam protection",
            color=Config.INFO_COLOR
        )
        
        embed.add_field(
            name="📊 Current Settings",
            value=f"**Message Limit:** {Config.SPAM_MESSAGE_LIMIT} per minute\n"
                  f"**Action:** Warning → Kick\n"
                  f"**Exempt:** Users with Manage Messages permission",
            inline=False
        )
        
        # Count currently tracked users
        active_users = len([uid for uid, msgs in self.user_messages.items() if msgs])
        warned_count = len(self.warned_users)
        
        embed.add_field(
            name="📈 Current Status",
            value=f"**Active Users Tracked:** {active_users}\n"
                  f"**Users with Warnings:** {warned_count}",
            inline=True
        )
        
        embed.add_field(
            name="⚙️ How it works",
            value="• Tracks messages per user per minute\n"
                  "• First violation: Warning + 30s grace period\n"
                  "• Continued spam: Kick from server\n"
                  "• Automatically logs all actions",
            inline=False
        )
        
        embed.set_footer(text="Anti-spam protection is always active")
        await ctx.send(embed=embed)
    
    @commands.command(name='clearspam')
    @commands.has_permissions(manage_guild=True)
    async def clear_spam_tracking(self, ctx, member: discord.Member = None):
        """Clear spam tracking for a user or all users"""
        if member:
            # Clear tracking for specific user
            user_id = member.id
            if user_id in self.user_messages:
                del self.user_messages[user_id]
            self.warned_users.discard(user_id)
            
            embed = discord.Embed(
                title="✅ Spam Tracking Cleared",
                description=f"Cleared spam tracking for {member.mention}",
                color=Config.SUCCESS_COLOR
            )
        else:
            # Clear all tracking
            self.user_messages.clear()
            self.warned_users.clear()
            
            embed = discord.Embed(
                title="✅ All Spam Tracking Cleared",
                description="Cleared spam tracking for all users",
                color=Config.SUCCESS_COLOR
            )
        
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        await ctx.send(embed=embed)
