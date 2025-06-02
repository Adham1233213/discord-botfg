import discord
from discord.ext import commands
from datetime import datetime, timedelta
import asyncio
from config import Config

class ModerationCog(commands.Cog):
    """Moderation commands and functionality"""
    
    def __init__(self, bot, database):
        self.bot = bot
        self.db = database
    
    async def get_log_channel(self, guild):
        """Get or create the log channel"""
        log_channel = discord.utils.get(guild.channels, name=Config.LOG_CHANNEL_NAME)
        if not log_channel:
            try:
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                }
                log_channel = await guild.create_text_channel(Config.LOG_CHANNEL_NAME, overwrites=overwrites)
            except discord.Forbidden:
                return None
        return log_channel
    
    async def log_action(self, guild, action, moderator, target, reason=None, duration=None):
        """Log moderation actions"""
        log_channel = await self.get_log_channel(guild)
        if not log_channel:
            return
        
        embed = discord.Embed(
            title=f"🔨 {action}",
            color=Config.WARNING_COLOR,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Target", value=f"{target.mention} ({target.id})", inline=True)
        embed.add_field(name="Moderator", value=f"{moderator.mention} ({moderator.id})", inline=True)
        
        if reason:
            embed.add_field(name="Reason", value=reason, inline=False)
        
        if duration:
            embed.add_field(name="Duration", value=duration, inline=True)
        
        embed.set_footer(text=f"User ID: {target.id}")
        
        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass
    
    @commands.command(name='kick')
    @commands.has_permissions(kick_members=True)
    async def kick_user(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """Kick a member from the server"""
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("❌ You cannot kick someone with a higher or equal role!")
            return
        
        if member == ctx.guild.owner:
            await ctx.send("❌ Cannot kick the server owner!")
            return
        
        try:
            await member.kick(reason=f"Kicked by {ctx.author}: {reason}")
            
            embed = discord.Embed(
                title="✅ User Kicked",
                description=f"{member.mention} has been kicked from the server.",
                color=Config.SUCCESS_COLOR
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            
            await ctx.send(embed=embed)
            await self.log_action(ctx.guild, "KICK", ctx.author, member, reason)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to kick this user!")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}")
    
    @commands.command(name='ban')
    @commands.has_permissions(ban_members=True)
    async def ban_user(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """Ban a member from the server"""
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("❌ You cannot ban someone with a higher or equal role!")
            return
        
        if member == ctx.guild.owner:
            await ctx.send("❌ Cannot ban the server owner!")
            return
        
        try:
            await member.ban(reason=f"Banned by {ctx.author}: {reason}")
            
            embed = discord.Embed(
                title="🔨 User Banned",
                description=f"{member.mention} has been banned from the server.",
                color=Config.ERROR_COLOR
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            
            await ctx.send(embed=embed)
            await self.log_action(ctx.guild, "BAN", ctx.author, member, reason)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to ban this user!")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}")
    
    @commands.command(name='unban')
    @commands.has_permissions(ban_members=True)
    async def unban_user(self, ctx, user_id: int, *, reason="No reason provided"):
        """Unban a user by their ID"""
        try:
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.unban(user, reason=f"Unbanned by {ctx.author}: {reason}")
            
            embed = discord.Embed(
                title="✅ User Unbanned",
                description=f"{user.mention} has been unbanned.",
                color=Config.SUCCESS_COLOR
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            
            await ctx.send(embed=embed)
            await self.log_action(ctx.guild, "UNBAN", ctx.author, user, reason)
            
        except discord.NotFound:
            await ctx.send("❌ User not found or not banned!")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to unban users!")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}")
    
    @commands.command(name='timeout')
    @commands.has_permissions(moderate_members=True)
    async def timeout_user(self, ctx, member: discord.Member, duration: int, unit: str = "minutes", *, reason="No reason provided"):
        """Timeout a member for a specified duration"""
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("❌ You cannot timeout someone with a higher or equal role!")
            return
        
        if member == ctx.guild.owner:
            await ctx.send("❌ Cannot timeout the server owner!")
            return
        
        # Convert duration to timedelta
        if unit.lower() in ['m', 'min', 'minute', 'minutes']:
            delta = timedelta(minutes=duration)
            duration_str = f"{duration} minute(s)"
        elif unit.lower() in ['h', 'hour', 'hours']:
            delta = timedelta(hours=duration)
            duration_str = f"{duration} hour(s)"
        elif unit.lower() in ['d', 'day', 'days']:
            delta = timedelta(days=duration)
            duration_str = f"{duration} day(s)"
        else:
            await ctx.send("❌ Invalid time unit! Use: minutes, hours, or days")
            return
        
        # Discord timeout limit is 28 days
        if delta > timedelta(days=28):
            await ctx.send("❌ Timeout duration cannot exceed 28 days!")
            return
        
        try:
            until = datetime.utcnow() + delta
            await member.timeout(until, reason=f"Timed out by {ctx.author}: {reason}")
            
            embed = discord.Embed(
                title="⏰ User Timed Out",
                description=f"{member.mention} has been timed out.",
                color=Config.WARNING_COLOR
            )
            embed.add_field(name="Duration", value=duration_str, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            
            await ctx.send(embed=embed)
            await self.log_action(ctx.guild, "TIMEOUT", ctx.author, member, reason, duration_str)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to timeout this user!")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}")
    
    @commands.command(name='untimeout')
    @commands.has_permissions(moderate_members=True)
    async def untimeout_user(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """Remove timeout from a member"""
        try:
            await member.timeout(None, reason=f"Timeout removed by {ctx.author}: {reason}")
            
            embed = discord.Embed(
                title="✅ Timeout Removed",
                description=f"Timeout removed from {member.mention}.",
                color=Config.SUCCESS_COLOR
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            
            await ctx.send(embed=embed)
            await self.log_action(ctx.guild, "UNTIMEOUT", ctx.author, member, reason)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to remove timeout from this user!")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}")
    
    @commands.command(name='warn')
    @commands.has_permissions(manage_messages=True)
    async def warn_user(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """Warn a member"""
        try:
            await self.db.add_warning(member.id, ctx.guild.id, ctx.author.id, reason)
            
            warnings = await self.db.get_warnings(member.id, ctx.guild.id)
            warning_count = len(warnings)
            
            embed = discord.Embed(
                title="⚠️ User Warned",
                description=f"{member.mention} has been warned.",
                color=Config.WARNING_COLOR
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Warning Count", value=f"{warning_count}", inline=True)
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            
            await ctx.send(embed=embed)
            await self.log_action(ctx.guild, "WARN", ctx.author, member, reason)
            
            # Try to DM the user
            try:
                dm_embed = discord.Embed(
                    title="⚠️ You have been warned",
                    description=f"You have been warned in **{ctx.guild.name}**",
                    color=Config.WARNING_COLOR
                )
                dm_embed.add_field(name="Reason", value=reason, inline=False)
                dm_embed.add_field(name="Warning Count", value=f"{warning_count}", inline=True)
                await member.send(embed=dm_embed)
            except discord.Forbidden:
                pass
            
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}")
    
    @commands.command(name='warnings')
    @commands.has_permissions(manage_messages=True)
    async def check_warnings(self, ctx, member: discord.Member = None):
        """Check warnings for a member"""
        if member is None:
            member = ctx.author
        
        try:
            warnings = await self.db.get_warnings(member.id, ctx.guild.id)
            
            if not warnings:
                embed = discord.Embed(
                    title="✅ No Warnings",
                    description=f"{member.mention} has no warnings.",
                    color=Config.SUCCESS_COLOR
                )
                await ctx.send(embed=embed)
                return
            
            embed = discord.Embed(
                title=f"⚠️ Warnings for {member.display_name}",
                color=Config.WARNING_COLOR
            )
            
            for i, warning in enumerate(warnings[-10:], 1):  # Show last 10 warnings
                warning_id, user_id, guild_id, moderator_id, reason, timestamp = warning
                moderator = self.bot.get_user(moderator_id)
                mod_name = moderator.display_name if moderator else "Unknown"
                
                embed.add_field(
                    name=f"Warning #{i}",
                    value=f"**Reason:** {reason}\n**Moderator:** {mod_name}\n**Date:** {timestamp}",
                    inline=False
                )
            
            embed.add_field(name="Total Warnings", value=str(len(warnings)), inline=True)
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}")
    
    @commands.command(name='clearwarnings')
    @commands.has_permissions(manage_guild=True)
    async def clear_warnings(self, ctx, member: discord.Member):
        """Clear all warnings for a member"""
        try:
            await self.db.clear_warnings(member.id, ctx.guild.id)
            
            embed = discord.Embed(
                title="✅ Warnings Cleared",
                description=f"All warnings cleared for {member.mention}.",
                color=Config.SUCCESS_COLOR
            )
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            
            await ctx.send(embed=embed)
            await self.log_action(ctx.guild, "CLEAR WARNINGS", ctx.author, member)
            
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}")
    
    @commands.command(name='purge')
    @commands.has_permissions(manage_messages=True)
    async def purge_messages(self, ctx, amount: int, member: discord.Member = None):
        """Delete a specified number of messages"""
        if amount < 1 or amount > 100:
            await ctx.send("❌ Amount must be between 1 and 100!")
            return
        
        def check(message):
            if member:
                return message.author == member
            return True
        
        try:
            deleted = await ctx.channel.purge(limit=amount + 1, check=check)
            count = len(deleted) - 1  # Subtract 1 for the command message
            
            embed = discord.Embed(
                title="🗑️ Messages Purged",
                description=f"Deleted {count} messages.",
                color=Config.SUCCESS_COLOR
            )
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            if member:
                embed.add_field(name="Target User", value=member.mention, inline=True)
            
            message = await ctx.send(embed=embed)
            await asyncio.sleep(5)
            await message.delete()
            
            # Log the action
            reason = f"Purged {count} messages" + (f" from {member}" if member else "")
            await self.log_action(ctx.guild, "PURGE", ctx.author, member or ctx.author, reason)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to delete messages!")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}")