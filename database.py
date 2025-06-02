import sqlite3
import asyncio
import aiosqlite
from datetime import datetime, timedelta

class Database:
    """Database handler for the Discord bot"""
    
    def __init__(self, db_file="bot_data.db"):
        self.db_file = db_file
    
    async def initialize(self):
        """Initialize database tables"""
        async with aiosqlite.connect(self.db_file) as db:
            # Warnings table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS warnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    moderator_id INTEGER NOT NULL,
                    reason TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Game stats table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS game_stats (
                    user_id INTEGER,
                    guild_id INTEGER,
                    game_name TEXT,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    points INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, guild_id, game_name)
                )
            ''')
            
            # Anti-spam tracking
            await db.execute('''
                CREATE TABLE IF NOT EXISTS spam_tracking (
                    user_id INTEGER,
                    guild_id INTEGER,
                    message_count INTEGER DEFAULT 0,
                    last_reset DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, guild_id)
                )
            ''')
            
            await db.commit()
    
    async def add_warning(self, user_id, guild_id, moderator_id, reason):
        """Add a warning to the database"""
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute(
                'INSERT INTO warnings (user_id, guild_id, moderator_id, reason) VALUES (?, ?, ?, ?)',
                (user_id, guild_id, moderator_id, reason)
            )
            await db.commit()
    
    async def get_warnings(self, user_id, guild_id):
        """Get warnings for a user"""
        async with aiosqlite.connect(self.db_file) as db:
            cursor = await db.execute(
                'SELECT * FROM warnings WHERE user_id = ? AND guild_id = ?',
                (user_id, guild_id)
            )
            return await cursor.fetchall()
    
    async def clear_warnings(self, user_id, guild_id):
        """Clear all warnings for a user"""
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute(
                'DELETE FROM warnings WHERE user_id = ? AND guild_id = ?',
                (user_id, guild_id)
            )
            await db.commit()
    
    async def update_game_stats(self, user_id, guild_id, game_name, won=False, points=0):
        """Update game statistics"""
        async with aiosqlite.connect(self.db_file) as db:
            # Check if record exists
            cursor = await db.execute(
                'SELECT * FROM game_stats WHERE user_id = ? AND guild_id = ? AND game_name = ?',
                (user_id, guild_id, game_name)
            )
            existing = await cursor.fetchone()
            
            if existing:
                if won:
                    await db.execute(
                        'UPDATE game_stats SET wins = wins + 1, points = points + ? WHERE user_id = ? AND guild_id = ? AND game_name = ?',
                        (points, user_id, guild_id, game_name)
                    )
                else:
                    await db.execute(
                        'UPDATE game_stats SET losses = losses + 1 WHERE user_id = ? AND guild_id = ? AND game_name = ?',
                        (user_id, guild_id, game_name)
                    )
            else:
                wins = 1 if won else 0
                losses = 0 if won else 1
                await db.execute(
                    'INSERT INTO game_stats (user_id, guild_id, game_name, wins, losses, points) VALUES (?, ?, ?, ?, ?, ?)',
                    (user_id, guild_id, game_name, wins, losses, points)
                )
            
            await db.commit()
    
    async def get_game_stats(self, user_id, guild_id):
        """Get game statistics for a user"""
        async with aiosqlite.connect(self.db_file) as db:
            cursor = await db.execute(
                'SELECT * FROM game_stats WHERE user_id = ? AND guild_id = ?',
                (user_id, guild_id)
            )
            return await cursor.fetchall()
    
    async def track_spam(self, user_id, guild_id):
        """Track spam messages for anti-spam system"""
        async with aiosqlite.connect(self.db_file) as db:
            now = datetime.now()
            
            # Check existing record
            cursor = await db.execute(
                'SELECT message_count, last_reset FROM spam_tracking WHERE user_id = ? AND guild_id = ?',
                (user_id, guild_id)
            )
            existing = await cursor.fetchone()
            
            if existing:
                message_count, last_reset_str = existing
                last_reset = datetime.fromisoformat(last_reset_str)
                
                # Check if we need to reset (more than 1 minute passed)
                if now - last_reset > timedelta(minutes=1):
                    await db.execute(
                        'UPDATE spam_tracking SET message_count = 1, last_reset = ? WHERE user_id = ? AND guild_id = ?',
                        (now.isoformat(), user_id, guild_id)
                    )
                    return 1
                else:
                    new_count = message_count + 1
                    await db.execute(
                        'UPDATE spam_tracking SET message_count = ? WHERE user_id = ? AND guild_id = ?',
                        (new_count, user_id, guild_id)
                    )
                    await db.commit()
                    return new_count
            else:
                await db.execute(
                    'INSERT INTO spam_tracking (user_id, guild_id, message_count, last_reset) VALUES (?, ?, 1, ?)',
                    (user_id, guild_id, now.isoformat())
                )
                await db.commit()
                return 1
