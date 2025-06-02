import os

class Config:
    """Configuration settings for the Discord bot"""
    
    # Discord Bot Token - gets from environment or uses provided token as fallback
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "MTM3NjkwOTE0MzkyNjg5ODcxOA.G9e0xq.pUuWU0ino7mwA-ak1S2fb8pMFT-NiM8tAtY0EE")
    
    # Anti-spam settings
    SPAM_MESSAGE_LIMIT = 30  # Max messages per minute
    SPAM_TIME_WINDOW = 60    # Time window in seconds
    
    # Anti-raid settings
    RAID_JOIN_LIMIT = 10     # Max joins in time window
    RAID_TIME_WINDOW = 60    # Time window in seconds
    
    # Anti-nuke settings
    NUKE_ACTION_LIMIT = 5    # Max destructive actions per minute
    NUKE_TIME_WINDOW = 60    # Time window in seconds
    
    # Database file
    DATABASE_FILE = "bot_data.db"
    
    # Log channel name
    LOG_CHANNEL_NAME = "mod-logs"
    
    # Bot colors (in hex)
    SUCCESS_COLOR = 0x00ff00
    ERROR_COLOR = 0xff0000
    WARNING_COLOR = 0xffff00
    INFO_COLOR = 0x0099ff
