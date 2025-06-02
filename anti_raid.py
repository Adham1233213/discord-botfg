import discord
from discord.ext import commands
from collections import defaultdict, deque
from datetime import datetime, timedelta
from config import Config

class AntiRaidCog(commands.Cog):
    """Anti-raid protection system"""
    
    def __init__(self, bot, database):
        self.bot = bot
        self.db = database
        self.join_tracking = deque()  # Track recent joins
        self.raid_protection_active = False
        self.suspicious_users = set()  # Track suspicious accounts
    
    async def get_log_channel(self, guild):
        """Get the log channel for the guild"""
        log_channel = discord.utils.get(guild.channels, name=Config.LOG_CHANNEL_NAME)
        return log_channel
    
    async def log_raid_action(self, guild, action, details=None):
        """Log anti-raid actions"""
        log_channel = await self.get_log_channel(guild)
        if not log_channel:
            return
        
        embed = discord.Embed(
            title="🛡️ Anti-Raid Action",
            color=Config.ERROR_COLOR,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Action", value=action, inline=True)
        embed.add_field(name="Server", value=guild.name, inline=True)
        
        if details:
            embed.add_field(name="Details", value=details, inline=False)
        
        embed.set_footer(text="Anti-Raid Protection")
        
        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass
    
    def is_suspicious_account(self, member):
        """Check if account appears suspicious"""
        now = datetime.utcnow()
        account_age = now - member.created_at
        
        # Account less than 7 days old
        if account_age < timedelta(days=7):
            return True, f"New account ({account_age.days} days old)"
        
        # No avatar
        if member.avatar is None:
            return True, "No profile picture"
        
        # Generic/suspicious username patterns
        username = member.name.lower()
        suspicious_patterns = ['user', 'member', 'discord', 'raid', 'spam']
        if any(pattern in username for pattern in suspicious_patterns):
            return True, "Suspicious username pattern"
        
        # Username is mostly numbers
        if sum(c.isdigit() for c in member.name) > len(member.name) * 0.7:
            return True, "Username mostly numbers"
        
        return False, None
    
    def detect_raid(self):
        """Detect if a raid is happening based on join patterns"""
        now = datetime.now()
        
        # Remove joins older than the time window
        while self.join_tracking and now - self.join_tracking[0] > timedelta(seconds=Config.RAID_TIME_WINDOW):
            self.join_tracking.popleft()
        
        # Check if too many joins in time window
        return len(self.join_tracking) >= Config.RAID_JOIN_LIMIT
    
    async def activate_raid_protection(self, guild):
        """Activate raid protection mode"""
        if self.raid_protection_active:
            return
        
        self.raid_protection_active = True
        
        # Try to enable community features for better protection
        try:
            # Set verification level to high
            await guild.edit(verification_level=discord.VerificationLevel.high)
        except discord.Forbidden:
            pass
        
        await self.log_raid_action(guild, "RAID PROTECTION ACTIVATED", 
                                 f"Detected {len(self.join_tracking)} joins in {Config.RAID_TIME_WINDOW} seconds")
        
        # Send alert to moderators
        log_channel = await self.get_log_channel(guild)
        if log_channel:
            embed = discord.Embed(
                title="🚨 RAID DETECTED",
                description="**Automatic raid protection has been activated!**",
                color=Config.ERROR_COLOR
            )
            embed.add_field(name="Actions Taken", 
                          value="• High verification level enabled\n• Monitoring new joins\n• Auto-kicking suspicious accounts",
                          inline=False)
            embed.add_field(name="Recommendation", 
                          value="Consider temporarily enabling member screening or locking down channels",
                          inline=False)
            
            try:
                # Try to mention moderators
                mod_role = discord.utils.get(guild.roles, permissions=discord.Permissions(manage_guild=True))
                if mod_role:
                    await log_channel.send(f"{mod_role.mention}", embed=embed)
                else:
                    await log_channel.send(embed=embed)
            except discord.Forbidden:
                pass
        
        # Automatically deactivate after 30 minutes
        await asyncio.sleep(1800)  # 30 minutes
        await self.deactivate_raid_protection(guild)
    
    async def deactivate_raid_protection(self, guild):
        """Deactivate raid protection mode"""
        if not self.raid_protection_active:
            return
        
        self.raid_protection_active = False
        
        try:
            # Reset verification level to medium
            await guild.edit(verification_level=discord.VerificationLevel.medium)
        except discord.Forbidden:
            pass
        
        await self.log_raid_action(guild, "RAID PROTECTION DEACTIVATED", "Automatic protection timeout")
        self.suspicious_users.clear()
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Monitor member joins for raid detection"""
        guild = member.guild
        now = datetime.now()
        
        # Add to join tracking
        self.join_tracking.append(now)
        
        # Check if account is suspicious
        is_suspicious, reason = self.is_suspicious_account(member)
        
        # Log the join
        log_channel = await self.get_log_channel(guild)
        if log_channel:
            embed = discord.Embed(
                title="👋 Member Joined",
                color=Config.WARNING_COLOR if is_suspicious else Config.SUCCESS_COLOR,
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(name="User", value=f"{member.mention} ({member.id})", inline=True)
            embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d"), inline=True)
            
            if is_suspicious:
                embed.add_field(name="⚠️ Suspicious", value=reason, inline=False)
                self.suspicious_users.add(member.id)
            
            embed.set_footer(text=f"User ID: {member.id}")
            
            try:
                await log_channel.send(embed=embed)
            except discord.Forbidden:
                pass
        
        # Check for raid
        if self.detect_raid():
            await self.activate_raid_protection(guild)
        
        # If raid protection is active, handle suspicious accounts
        if self.raid_protection_active and is_suspicious:
            try:
                # Kick suspicious accounts during raid
                await member.kick(reason=f"Raid Protection: {reason}")
                await self.log_raid_action(guild, "SUSPICIOUS USER KICKED", 
                                         f"{member} - {reason}")
            except discord.Forbidden:
                # Can't kick, try to timeout
                try:
                    timeout_duration = timedelta(hours=1)
                    await member.timeout(timeout_duration, reason=f"Raid Protection: {reason}")
                    await self.log_raid_action(guild, "SUSPICIOUS USER TIMED OUT", 
                                             f"{member} - {reason}")
                except discord.Forbidden:
                    # Log that we detected but couldn't act
                    await self.log_raid_action(guild, "SUSPICIOUS USER DETECTED (No Permission)", 
                                             f"{member} - {reason}")
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Log member leaves"""
        guild = member.guild
        log_channel = await self.get_log_channel(guild)
        
        if log_channel:
            embed = discord.Embed(
                title="👋 Member Left",
                color=Config.INFO_COLOR,
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(name="User", value=f"{member} ({member.id})", inline=True)
            embed.add_field(name="Joined", value=member.joined_at.strftime("%Y-%m-%d") if member.joined_at else "Unknown", inline=True)
            
            embed.set_footer(text=f"User ID: {member.id}")
            
            try:
                await log_channel.send(embed=embed)
            except discord.Forbidden:
                pass
        
        # Remove from suspicious users if they leave
        self.suspicious_users.discard(member.id)
    
    @commands.command(name='raidprotection', aliases=['rp'])
    @commands.has_permissions(manage_guild=True)
    async def raid_protection_command(self, ctx, action: str = None):
        """Manually control raid protection"""
        if action is None:
            # Show current status
            embed = discord.Embed(
                title="🛡️ Raid Protection Status",
                color=Config.ERROR_COLOR if self.raid_protection_active else Config.SUCCESS_COLOR
            )
            
            status = "🔴 ACTIVE" if self.raid_protection_active else "🟢 INACTIVE"
            embed.add_field(name="Status", value=status, inline=True)
            embed.add_field(name="Recent Joins", value=str(len(self.join_tracking)), inline=True)
            embed.add_field(name="Suspicious Users", value=str(len(self.suspicious_users)), inline=True)
            
            embed.add_field(name="Settings", 
                          value=f"**Join Limit:** {Config.RAID_JOIN_LIMIT} in {Config.RAID_TIME_WINDOW}s\n"
                                f"**Auto-Protection:** Enabled",
                          inline=False)
            
            embed.add_field(name="Commands", 
                          value="`!raidprotection on` - Activate protection\n"
                                "`!raidprotection off` - Deactivate protection\n"
                                "`!raidprotection clear` - Clear tracking",
                          inline=False)
            
            await ctx.send(embed=embed)
            
        elif action.lower() == "on":
            if not self.raid_protection_active:
                await self.activate_raid_protection(ctx.guild)
                await ctx.send("🛡️ Raid protection manually activated!")
            else:
                await ctx.send("⚠️ Raid protection is already active!")
                
        elif action.lower() == "off":
            if self.raid_protection_active:
                await self.deactivate_raid_protection(ctx.guild)
                await ctx.send("✅ Raid protection deactivated!")
            else:
                await ctx.send("⚠️ Raid protection is already inactive!")
                
        elif action.lower() == "clear":
            self.join_tracking.clear()
            self.suspicious_users.clear()
            await ctx.send("✅ Raid protection tracking cleared!")
            
        else:
            await ctx.send("❌ Invalid action! Use `on`, `off`, or `clear`")
    
    @commands.command(name='raidinfo')
    @commands.has_permissions(manage_guild=True)
    async def raid_info(self, ctx):
        """Show detailed raid protection information"""
        embed = discord.Embed(
            title="🛡️ Anti-Raid System Information",
            description="Comprehensive raid protection details",
            color=Config.INFO_COLOR
        )
        
        # Current status
        status = "🔴 ACTIVE" if self.raid_protection_active else "🟢 INACTIVE"
        embed.add_field(name="Protection Status", value=status, inline=True)
        embed.add_field(name="Recent Joins", value=str(len(self.join_tracking)), inline=True)
        embed.add_field(name="Suspicious Users", value=str(len(self.suspicious_users)), inline=True)
        
        # Protection criteria
        embed.add_field(name="🚨 Raid Detection", 
                      value=f"• {Config.RAID_JOIN_LIMIT}+ joins in {Config.RAID_TIME_WINDOW} seconds\n"
                            f"• Automatic activation\n"
                            f"• 30-minute protection duration",
                      inline=False)
        
        # Suspicious account criteria
        embed.add_field(name="⚠️ Suspicious Account Detection", 
                      value="• Account less than 7 days old\n"
                            "• No profile picture\n"
                            "• Suspicious username patterns\n"
                            "• Username mostly numbers",
                      inline=False)
        
        # Actions taken
        embed.add_field(name="🛡️ Protection Actions", 
                      value="• Increase verification level\n"
                            "• Auto-kick suspicious accounts\n"
                            "• Alert moderators\n"
                            "• Enhanced logging",
                      inline=False)
        
        embed.set_footer(text="Anti-raid protection runs automatically")
        await ctx.send(embed=embed)
