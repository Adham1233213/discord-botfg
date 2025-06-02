import discord
from discord.ext import commands
from datetime import datetime
from config import Config

class LoggingCog(commands.Cog):
    """Comprehensive logging system for all server activities"""
    
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
    
    async def send_log(self, guild, embed):
        """Send log message to log channel"""
        log_channel = await self.get_log_channel(guild)
        if log_channel:
            try:
                await log_channel.send(embed=embed)
            except discord.Forbidden:
                pass
    
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """Log deleted messages"""
        if message.author.bot or not message.guild:
            return
        
        embed = discord.Embed(
            title="🗑️ Message Deleted",
            color=Config.ERROR_COLOR,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Author", value=f"{message.author.mention} ({message.author.id})", inline=True)
        embed.add_field(name="Channel", value=f"{message.channel.mention}", inline=True)
        embed.add_field(name="Message ID", value=str(message.id), inline=True)
        
        if message.content:
            content = message.content[:1000] + "..." if len(message.content) > 1000 else message.content
            embed.add_field(name="Content", value=f"```{content}```", inline=False)
        
        if message.attachments:
            attachments = "\n".join([att.filename for att in message.attachments])
            embed.add_field(name="Attachments", value=attachments, inline=False)
        
        embed.set_footer(text=f"User ID: {message.author.id}")
        
        await self.send_log(message.guild, embed)
    
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        """Log edited messages"""
        if before.author.bot or not before.guild or before.content == after.content:
            return
        
        embed = discord.Embed(
            title="✏️ Message Edited",
            color=Config.WARNING_COLOR,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Author", value=f"{before.author.mention} ({before.author.id})", inline=True)
        embed.add_field(name="Channel", value=f"{before.channel.mention}", inline=True)
        embed.add_field(name="Message ID", value=str(before.id), inline=True)
        
        if before.content:
            before_content = before.content[:500] + "..." if len(before.content) > 500 else before.content
            embed.add_field(name="Before", value=f"```{before_content}```", inline=False)
        
        if after.content:
            after_content = after.content[:500] + "..." if len(after.content) > 500 else after.content
            embed.add_field(name="After", value=f"```{after_content}```", inline=False)
        
        embed.add_field(name="Jump to Message", value=f"[Click here]({after.jump_url})", inline=True)
        embed.set_footer(text=f"User ID: {before.author.id}")
        
        await self.send_log(before.guild, embed)
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Log when members join (handled in anti_raid.py)"""
        pass  # This is handled in the anti-raid cog for better integration
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Log when members leave (handled in anti_raid.py)"""
        pass  # This is handled in the anti-raid cog for better integration
    
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Log member updates (roles, nickname, etc.)"""
        if before.roles != after.roles:
            # Role changes
            added_roles = [role for role in after.roles if role not in before.roles]
            removed_roles = [role for role in before.roles if role not in after.roles]
            
            if added_roles or removed_roles:
                embed = discord.Embed(
                    title="👤 Member Roles Updated",
                    color=Config.INFO_COLOR,
                    timestamp=datetime.utcnow()
                )
                
                embed.add_field(name="Member", value=f"{after.mention} ({after.id})", inline=True)
                
                if added_roles:
                    roles_text = ", ".join([f"@{role.name}" for role in added_roles])
                    embed.add_field(name="✅ Roles Added", value=roles_text, inline=False)
                
                if removed_roles:
                    roles_text = ", ".join([f"@{role.name}" for role in removed_roles])
                    embed.add_field(name="❌ Roles Removed", value=roles_text, inline=False)
                
                # Try to find who made the change
                async for entry in after.guild.audit_logs(action=discord.AuditLogAction.member_role_update, limit=1):
                    if entry.target.id == after.id:
                        embed.add_field(name="Changed By", value=f"{entry.user.mention}", inline=True)
                        break
                
                embed.set_footer(text=f"User ID: {after.id}")
                await self.send_log(after.guild, embed)
        
        if before.nick != after.nick:
            # Nickname changes
            embed = discord.Embed(
                title="📝 Nickname Changed",
                color=Config.INFO_COLOR,
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(name="Member", value=f"{after.mention} ({after.id})", inline=True)
            embed.add_field(name="Before", value=before.nick or "None", inline=True)
            embed.add_field(name="After", value=after.nick or "None", inline=True)
            
            # Try to find who made the change
            async for entry in after.guild.audit_logs(action=discord.AuditLogAction.member_update, limit=1):
                if entry.target.id == after.id:
                    embed.add_field(name="Changed By", value=f"{entry.user.mention}", inline=True)
                    break
            
            embed.set_footer(text=f"User ID: {after.id}")
            await self.send_log(after.guild, embed)
    
    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        """Log user profile updates"""
        if before.name != after.name:
            # Username changes
            for guild in self.bot.guilds:
                if guild.get_member(after.id):
                    embed = discord.Embed(
                        title="👤 Username Changed",
                        color=Config.INFO_COLOR,
                        timestamp=datetime.utcnow()
                    )
                    
                    embed.add_field(name="User", value=f"{after.mention} ({after.id})", inline=True)
                    embed.add_field(name="Before", value=before.name, inline=True)
                    embed.add_field(name="After", value=after.name, inline=True)
                    
                    embed.set_footer(text=f"User ID: {after.id}")
                    await self.send_log(guild, embed)
        
        if before.avatar != after.avatar:
            # Avatar changes
            for guild in self.bot.guilds:
                if guild.get_member(after.id):
                    embed = discord.Embed(
                        title="🖼️ Avatar Changed",
                        color=Config.INFO_COLOR,
                        timestamp=datetime.utcnow()
                    )
                    
                    embed.add_field(name="User", value=f"{after.mention} ({after.id})", inline=True)
                    
                    if after.avatar:
                        embed.set_thumbnail(url=after.avatar.url)
                    
                    embed.set_footer(text=f"User ID: {after.id}")
                    await self.send_log(guild, embed)
    
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        """Log channel creation"""
        embed = discord.Embed(
            title="➕ Channel Created",
            color=Config.SUCCESS_COLOR,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Channel", value=f"{channel.mention} ({channel.id})", inline=True)
        embed.add_field(name="Type", value=str(channel.type).title(), inline=True)
        embed.add_field(name="Category", value=channel.category.name if channel.category else "None", inline=True)
        
        # Try to find who created it
        async for entry in channel.guild.audit_logs(action=discord.AuditLogAction.channel_create, limit=1):
            if entry.target.id == channel.id:
                embed.add_field(name="Created By", value=f"{entry.user.mention}", inline=True)
                break
        
        embed.set_footer(text=f"Channel ID: {channel.id}")
        await self.send_log(channel.guild, embed)
    
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """Log channel deletion (handled in anti_nuke.py for better integration)"""
        pass  # This is handled in the anti-nuke cog
    
    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        """Log channel updates"""
        changes = []
        
        if before.name != after.name:
            changes.append(f"**Name:** {before.name} → {after.name}")
        
        if before.topic != after.topic:
            changes.append(f"**Topic:** {before.topic or 'None'} → {after.topic or 'None'}")
        
        if hasattr(before, 'slowmode_delay') and before.slowmode_delay != after.slowmode_delay:
            changes.append(f"**Slowmode:** {before.slowmode_delay}s → {after.slowmode_delay}s")
        
        if changes:
            embed = discord.Embed(
                title="✏️ Channel Updated",
                color=Config.WARNING_COLOR,
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(name="Channel", value=f"{after.mention} ({after.id})", inline=True)
            embed.add_field(name="Changes", value="\n".join(changes), inline=False)
            
            # Try to find who made the change
            async for entry in after.guild.audit_logs(action=discord.AuditLogAction.channel_update, limit=1):
                if entry.target.id == after.id:
                    embed.add_field(name="Updated By", value=f"{entry.user.mention}", inline=True)
                    break
            
            embed.set_footer(text=f"Channel ID: {after.id}")
            await self.send_log(after.guild, embed)
    
    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        """Log role creation"""
        embed = discord.Embed(
            title="➕ Role Created",
            color=role.color or Config.SUCCESS_COLOR,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Role", value=f"@{role.name} ({role.id})", inline=True)
        embed.add_field(name="Color", value=str(role.color), inline=True)
        embed.add_field(name="Mentionable", value="Yes" if role.mentionable else "No", inline=True)
        embed.add_field(name="Hoisted", value="Yes" if role.hoist else "No", inline=True)
        
        # Try to find who created it
        async for entry in role.guild.audit_logs(action=discord.AuditLogAction.role_create, limit=1):
            if entry.target.id == role.id:
                embed.add_field(name="Created By", value=f"{entry.user.mention}", inline=True)
                break
        
        embed.set_footer(text=f"Role ID: {role.id}")
        await self.send_log(role.guild, embed)
    
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        """Log role deletion (handled in anti_nuke.py for better integration)"""
        pass  # This is handled in the anti-nuke cog
    
    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        """Log role updates"""
        changes = []
        
        if before.name != after.name:
            changes.append(f"**Name:** {before.name} → {after.name}")
        
        if before.color != after.color:
            changes.append(f"**Color:** {before.color} → {after.color}")
        
        if before.permissions != after.permissions:
            changes.append("**Permissions:** Updated")
        
        if before.mentionable != after.mentionable:
            changes.append(f"**Mentionable:** {before.mentionable} → {after.mentionable}")
        
        if before.hoist != after.hoist:
            changes.append(f"**Hoisted:** {before.hoist} → {after.hoist}")
        
        if changes:
            embed = discord.Embed(
                title="✏️ Role Updated",
                color=after.color or Config.WARNING_COLOR,
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(name="Role", value=f"@{after.name} ({after.id})", inline=True)
            embed.add_field(name="Changes", value="\n".join(changes), inline=False)
            
            # Try to find who made the change
            async for entry in after.guild.audit_logs(action=discord.AuditLogAction.role_update, limit=1):
                if entry.target.id == after.id:
                    embed.add_field(name="Updated By", value=f"{entry.user.mention}", inline=True)
                    break
            
            embed.set_footer(text=f"Role ID: {after.id}")
            await self.send_log(after.guild, embed)
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Log voice channel activity"""
        # User joined voice channel
        if before.channel is None and after.channel is not None:
            embed = discord.Embed(
                title="🔊 Joined Voice Channel",
                color=Config.SUCCESS_COLOR,
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="User", value=f"{member.mention} ({member.id})", inline=True)
            embed.add_field(name="Channel", value=after.channel.name, inline=True)
            embed.set_footer(text=f"User ID: {member.id}")
            await self.send_log(member.guild, embed)
        
        # User left voice channel
        elif before.channel is not None and after.channel is None:
            embed = discord.Embed(
                title="🔇 Left Voice Channel",
                color=Config.ERROR_COLOR,
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="User", value=f"{member.mention} ({member.id})", inline=True)
            embed.add_field(name="Channel", value=before.channel.name, inline=True)
            embed.set_footer(text=f"User ID: {member.id}")
            await self.send_log(member.guild, embed)
        
        # User moved between voice channels
        elif before.channel != after.channel and before.channel is not None and after.channel is not None:
            embed = discord.Embed(
                title="🔄 Moved Voice Channels",
                color=Config.INFO_COLOR,
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="User", value=f"{member.mention} ({member.id})", inline=True)
            embed.add_field(name="From", value=before.channel.name, inline=True)
            embed.add_field(name="To", value=after.channel.name, inline=True)
            embed.set_footer(text=f"User ID: {member.id}")
            await self.send_log(member.guild, embed)
    
    @commands.command(name='logs')
    @commands.has_permissions(manage_guild=True)
    async def logs_command(self, ctx, action: str = None):
        """Manage logging system"""
        if action is None:
            # Show logging status
            log_channel = await self.get_log_channel(ctx.guild)
            
            embed = discord.Embed(
                title="📋 Logging System Status",
                color=Config.SUCCESS_COLOR if log_channel else Config.ERROR_COLOR
            )
            
            if log_channel:
                embed.add_field(name="Log Channel", value=log_channel.mention, inline=True)
                embed.add_field(name="Status", value="🟢 Active", inline=True)
            else:
                embed.add_field(name="Status", value="🔴 No log channel", inline=True)
            
            embed.add_field(name="📊 Logged Events", 
                          value="• Message edits/deletions\n• Member joins/leaves\n"
                                "• Role changes\n• Channel changes\n• Voice activity\n"
                                "• Moderation actions", 
                          inline=False)
            
            embed.add_field(name="Commands", 
                          value="`!logs setup` - Create log channel\n"
                                "`!logs test` - Send test message",
                          inline=False)
            
            await ctx.send(embed=embed)
            
        elif action.lower() == "setup":
            log_channel = await self.get_log_channel(ctx.guild)
            if log_channel:
                await ctx.send(f"✅ Log channel already exists: {log_channel.mention}")
            else:
                await ctx.send("❌ Could not create log channel. Check bot permissions!")
                
        elif action.lower() == "test":
            embed = discord.Embed(
                title="🧪 Test Log Message",
                description="This is a test message to verify logging is working.",
                color=Config.INFO_COLOR,
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Triggered By", value=ctx.author.mention, inline=True)
            embed.set_footer(text="Logging system test")
            
            await self.send_log(ctx.guild, embed)
            await ctx.send("✅ Test log message sent!")
            
        else:
            await ctx.send("❌ Invalid action! Use `setup` or `test`")
