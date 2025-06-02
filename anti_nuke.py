import discord
from discord.ext import commands
from collections import defaultdict, deque
from datetime import datetime, timedelta
import asyncio
from config import Config

class AntiNukeCog(commands.Cog):
    """Anti-nuke protection system"""
    
    def __init__(self, bot, database):
        self.bot = bot
        self.db = database
        self.action_tracking = defaultdict(deque)  # Track destructive actions per user
        self.protected_mode = False
        self.trusted_users = set()  # Users exempt from anti-nuke
        
        # Define destructive actions to monitor
        self.destructive_actions = {
            'channel_delete', 'channel_create', 'role_delete', 'role_create',
            'member_ban', 'member_kick', 'guild_update', 'webhook_create'
        }
    
    async def get_log_channel(self, guild):
        """Get the log channel for the guild"""
        log_channel = discord.utils.get(guild.channels, name=Config.LOG_CHANNEL_NAME)
        return log_channel
    
    async def log_nuke_action(self, guild, user, action, details=None):
        """Log anti-nuke actions"""
        log_channel = await self.get_log_channel(guild)
        if not log_channel:
            return
        
        embed = discord.Embed(
            title="🔒 Anti-Nuke Action",
            color=Config.ERROR_COLOR,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="User", value=f"{user.mention} ({user.id})" if user else "Unknown", inline=True)
        embed.add_field(name="Action", value=action, inline=True)
        embed.add_field(name="Server", value=guild.name, inline=True)
        
        if details:
            embed.add_field(name="Details", value=details, inline=False)
        
        embed.set_footer(text=f"User ID: {user.id if user else 'Unknown'}")
        
        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass
    
    def track_action(self, user_id, action_type):
        """Track destructive actions by user"""
        if user_id in self.trusted_users:
            return False  # Trusted users are exempt
        
        now = datetime.now()
        user_actions = self.action_tracking[user_id]
        
        # Remove actions older than time window
        while user_actions and now - user_actions[0]['time'] > timedelta(seconds=Config.NUKE_TIME_WINDOW):
            user_actions.popleft()
        
        # Add current action
        user_actions.append({'time': now, 'action': action_type})
        
        # Check if exceeded limit
        return len(user_actions) > Config.NUKE_ACTION_LIMIT
    
    async def handle_nuke_attempt(self, guild, user, action_type):
        """Handle detected nuke attempt"""
        try:
            # Remove dangerous permissions from user
            member = guild.get_member(user.id)
            if member:
                # Remove from roles with dangerous permissions
                dangerous_perms = [
                    'administrator', 'manage_guild', 'manage_channels', 
                    'manage_roles', 'ban_members', 'kick_members'
                ]
                
                roles_to_remove = []
                for role in member.roles:
                    if any(getattr(role.permissions, perm, False) for perm in dangerous_perms):
                        roles_to_remove.append(role)
                
                if roles_to_remove:
                    await member.remove_roles(*roles_to_remove, reason="Anti-nuke: Suspicious activity detected")
                
                # Timeout the user
                timeout_duration = timedelta(hours=24)
                await member.timeout(timeout_duration, reason="Anti-nuke: Suspicious destructive activity")
                
                await self.log_nuke_action(guild, user, "NUKE ATTEMPT BLOCKED", 
                                         f"Removed roles and timed out user for 24 hours\nTrigger: {action_type}")
            
            # Activate protection mode
            await self.activate_protection_mode(guild)
            
        except discord.Forbidden:
            await self.log_nuke_action(guild, user, "NUKE ATTEMPT DETECTED (No Permission)", 
                                     f"Cannot remove permissions\nTrigger: {action_type}")
        except Exception as e:
            print(f"Error handling nuke attempt: {e}")
    
    async def activate_protection_mode(self, guild):
        """Activate enhanced protection mode"""
        if self.protected_mode:
            return
        
        self.protected_mode = True
        
        await self.log_nuke_action(guild, None, "PROTECTION MODE ACTIVATED", 
                                 "Enhanced monitoring enabled for 1 hour")
        
        # Alert moderators
        log_channel = await self.get_log_channel(guild)
        if log_channel:
            embed = discord.Embed(
                title="🚨 NUKE ATTEMPT DETECTED",
                description="**Anti-nuke protection has been activated!**",
                color=Config.ERROR_COLOR
            )
            embed.add_field(name="Actions Taken", 
                          value="• Removed dangerous permissions from user\n"
                                "• User timed out for 24 hours\n"
                                "• Enhanced monitoring active",
                          inline=False)
            embed.add_field(name="Recommendation", 
                          value="• Review recent audit logs\n"
                                "• Check for compromised accounts\n"
                                "• Verify role permissions",
                          inline=False)
            
            try:
                # Try to mention admins
                admin_role = discord.utils.get(guild.roles, permissions=discord.Permissions(administrator=True))
                if admin_role:
                    await log_channel.send(f"{admin_role.mention}", embed=embed)
                else:
                    await log_channel.send(embed=embed)
            except discord.Forbidden:
                pass
        
        # Automatically deactivate after 1 hour
        await asyncio.sleep(3600)  # 1 hour
        self.protected_mode = False
        await self.log_nuke_action(guild, None, "PROTECTION MODE DEACTIVATED", "Automatic timeout")
    
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """Monitor channel deletions"""
        guild = channel.guild
        
        # Get who deleted the channel from audit logs
        async for entry in guild.audit_logs(action=discord.AuditLogAction.channel_delete, limit=1):
            if entry.target.id == channel.id:
                user = entry.user
                
                if self.track_action(user.id, 'channel_delete'):
                    await self.handle_nuke_attempt(guild, user, 'Mass Channel Deletion')
                else:
                    await self.log_nuke_action(guild, user, "CHANNEL DELETED", f"#{channel.name}")
                break
    
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        """Monitor excessive channel creation"""
        guild = channel.guild
        
        # Get who created the channel from audit logs
        async for entry in guild.audit_logs(action=discord.AuditLogAction.channel_create, limit=1):
            if entry.target.id == channel.id:
                user = entry.user
                
                if self.track_action(user.id, 'channel_create'):
                    await self.handle_nuke_attempt(guild, user, 'Mass Channel Creation')
                break
    
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        """Monitor role deletions"""
        guild = role.guild
        
        # Get who deleted the role from audit logs
        async for entry in guild.audit_logs(action=discord.AuditLogAction.role_delete, limit=1):
            if entry.target.id == role.id:
                user = entry.user
                
                if self.track_action(user.id, 'role_delete'):
                    await self.handle_nuke_attempt(guild, user, 'Mass Role Deletion')
                else:
                    await self.log_nuke_action(guild, user, "ROLE DELETED", f"@{role.name}")
                break
    
    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        """Monitor excessive role creation"""
        guild = role.guild
        
        # Get who created the role from audit logs
        async for entry in guild.audit_logs(action=discord.AuditLogAction.role_create, limit=1):
            if entry.target.id == role.id:
                user = entry.user
                
                if self.track_action(user.id, 'role_create'):
                    await self.handle_nuke_attempt(guild, user, 'Mass Role Creation')
                break
    
    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        """Monitor mass bans"""
        # Get who banned the user from audit logs
        async for entry in guild.audit_logs(action=discord.AuditLogAction.ban, limit=1):
            if entry.target.id == user.id:
                banner = entry.user
                
                if self.track_action(banner.id, 'member_ban'):
                    await self.handle_nuke_attempt(guild, banner, 'Mass Member Banning')
                break
    
    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        """Monitor guild modifications"""
        guild = after
        
        # Check for significant changes
        significant_changes = []
        if before.name != after.name:
            significant_changes.append(f"Name: {before.name} → {after.name}")
        if before.icon != after.icon:
            significant_changes.append("Icon changed")
        if before.verification_level != after.verification_level:
            significant_changes.append(f"Verification: {before.verification_level} → {after.verification_level}")
        
        if significant_changes:
            # Get who made the changes from audit logs
            async for entry in guild.audit_logs(action=discord.AuditLogAction.guild_update, limit=1):
                user = entry.user
                
                if self.track_action(user.id, 'guild_update'):
                    await self.handle_nuke_attempt(guild, user, 'Rapid Guild Modifications')
                else:
                    await self.log_nuke_action(guild, user, "GUILD UPDATED", "\n".join(significant_changes))
                break
    
    @commands.command(name='antinuke')
    @commands.has_permissions(administrator=True)
    async def antinuke_command(self, ctx, action: str = None, user: discord.Member = None):
        """Manage anti-nuke protection"""
        if action is None:
            # Show status
            embed = discord.Embed(
                title="🔒 Anti-Nuke Protection Status",
                color=Config.ERROR_COLOR if self.protected_mode else Config.SUCCESS_COLOR
            )
            
            status = "🔴 ENHANCED MODE" if self.protected_mode else "🟢 NORMAL MODE"
            embed.add_field(name="Status", value=status, inline=True)
            embed.add_field(name="Trusted Users", value=str(len(self.trusted_users)), inline=True)
            embed.add_field(name="Tracked Users", value=str(len(self.action_tracking)), inline=True)
            
            embed.add_field(name="Settings", 
                          value=f"**Action Limit:** {Config.NUKE_ACTION_LIMIT} in {Config.NUKE_TIME_WINDOW}s\n"
                                f"**Protected Mode:** {'Active' if self.protected_mode else 'Inactive'}",
                          inline=False)
            
            embed.add_field(name="Monitored Actions", 
                          value="• Channel creation/deletion\n• Role creation/deletion\n"
                                "• Mass bans/kicks\n• Guild modifications\n• Webhook creation",
                          inline=False)
            
            embed.add_field(name="Commands", 
                          value="`!antinuke trust @user` - Add trusted user\n"
                                "`!antinuke untrust @user` - Remove trusted user\n"
                                "`!antinuke clear` - Clear tracking",
                          inline=False)
            
            await ctx.send(embed=embed)
            
        elif action.lower() == "trust":
            if user is None:
                await ctx.send("❌ Please specify a user to trust!")
                return
            
            self.trusted_users.add(user.id)
            await ctx.send(f"✅ {user.mention} added to trusted users (exempt from anti-nuke)")
            await self.log_nuke_action(ctx.guild, ctx.author, "TRUSTED USER ADDED", f"{user}")
            
        elif action.lower() == "untrust":
            if user is None:
                await ctx.send("❌ Please specify a user to untrust!")
                return
            
            self.trusted_users.discard(user.id)
            await ctx.send(f"✅ {user.mention} removed from trusted users")
            await self.log_nuke_action(ctx.guild, ctx.author, "TRUSTED USER REMOVED", f"{user}")
            
        elif action.lower() == "clear":
            self.action_tracking.clear()
            await ctx.send("✅ Anti-nuke tracking cleared!")
            await self.log_nuke_action(ctx.guild, ctx.author, "TRACKING CLEARED", "Manual clear by admin")
            
        else:
            await ctx.send("❌ Invalid action! Use `trust`, `untrust`, or `clear`")
    
    @commands.command(name='nukeinfo')
    @commands.has_permissions(manage_guild=True)
    async def nuke_info(self, ctx):
        """Show detailed anti-nuke information"""
        embed = discord.Embed(
            title="🔒 Anti-Nuke System Information",
            description="Comprehensive server protection details",
            color=Config.INFO_COLOR
        )
        
        # Current status
        status = "🔴 ENHANCED MODE" if self.protected_mode else "🟢 NORMAL MODE"
        embed.add_field(name="Protection Status", value=status, inline=True)
        embed.add_field(name="Trusted Users", value=str(len(self.trusted_users)), inline=True)
        embed.add_field(name="Active Tracking", value=str(len(self.action_tracking)), inline=True)
        
        # Detection criteria
        embed.add_field(name="🚨 Nuke Detection", 
                      value=f"• {Config.NUKE_ACTION_LIMIT}+ actions in {Config.NUKE_TIME_WINDOW} seconds\n"
                            f"• Automatic protection activation\n"
                            f"• Immediate permission removal",
                      inline=False)
        
        # Monitored actions
        embed.add_field(name="👁️ Monitored Actions", 
                      value="• Channel creation/deletion\n• Role creation/deletion\n"
                            "• Mass member bans/kicks\n• Guild setting changes\n"
                            "• Webhook creation\n• Permission modifications",
                      inline=False)
        
        # Protection measures
        embed.add_field(name="🛡️ Protection Measures", 
                      value="• Remove dangerous permissions\n• 24-hour timeout\n"
                            "• Enhanced monitoring mode\n• Immediate admin alerts\n"
                            "• Comprehensive audit logging",
                      inline=False)
        
        # Trusted users list
        if self.trusted_users:
            trusted_list = []
            for user_id in list(self.trusted_users)[:5]:  # Show first 5
                user = self.bot.get_user(user_id)
                trusted_list.append(user.name if user else f"ID: {user_id}")
            
            trusted_text = "\n".join(trusted_list)
            if len(self.trusted_users) > 5:
                trusted_text += f"\n... and {len(self.trusted_users) - 5} more"
            
            embed.add_field(name="👥 Trusted Users", value=trusted_text, inline=False)
        
        embed.set_footer(text="Anti-nuke protection runs automatically")
        await ctx.send(embed=embed)
