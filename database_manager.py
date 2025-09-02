"""
Database Manager for Multi-Guild Support
Manages separate SQLite databases for each Discord guild
"""

import sqlite3
import os
import threading
import time
from contextlib import contextmanager
from typing import Optional, Dict, Any, List, Tuple
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabasePool:
    """Connection pool for a single guild database"""
    
    def __init__(self, db_path: str, max_connections: int = 10):
        self.db_path = db_path
        self.max_connections = max_connections
        self.connections = []
        self.lock = threading.Lock()
        self._closed = False
        
    def get_connection(self) -> sqlite3.Connection:
        """Get a connection from the pool"""
        with self.lock:
            if self._closed:
                raise RuntimeError("Connection pool is closed")
                
            # Reuse existing connection if available
            if self.connections:
                conn = self.connections.pop()
                # Test if connection is still valid
                try:
                    conn.execute("SELECT 1")
                    return conn
                except:
                    # Connection is dead, create new one
                    pass
            
            # Create new connection
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.execute("PRAGMA temp_store=MEMORY")
            return conn
    
    def return_connection(self, conn: sqlite3.Connection):
        """Return a connection to the pool"""
        with self.lock:
            if not self._closed and len(self.connections) < self.max_connections:
                self.connections.append(conn)
            else:
                conn.close()
    
    def close(self):
        """Close all connections in the pool"""
        with self.lock:
            self._closed = True
            for conn in self.connections:
                conn.close()
            self.connections.clear()

class DatabaseManager:
    """Main database manager for multi-guild support"""
    
    def __init__(self, database_dir: str = "databases", max_connections: int = 10):
        self.database_dir = database_dir
        self.max_connections = max_connections
        self.pools: Dict[int, DatabasePool] = {}
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.cache_ttl = 300  # 5 minutes
        self.executor = ThreadPoolExecutor(max_workers=20)
        self._ensure_directory()
        
    def _ensure_directory(self):
        """Ensure database directory exists"""
        if not os.path.exists(self.database_dir):
            os.makedirs(self.database_dir)
            logger.info(f"Created database directory: {self.database_dir}")
    
    def get_guild_db_path(self, guild_id: int) -> str:
        """Get database path for a guild"""
        return os.path.join(self.database_dir, f"guild_{guild_id}.db")
    
    def get_pool(self, guild_id: int) -> DatabasePool:
        """Get or create connection pool for a guild"""
        if guild_id not in self.pools:
            db_path = self.get_guild_db_path(guild_id)
            self.pools[guild_id] = DatabasePool(db_path, self.max_connections)
            self._initialize_guild_database(guild_id)
            logger.info(f"Created connection pool for guild {guild_id}")
        return self.pools[guild_id]
    
    @contextmanager
    def get_connection(self, guild_id: int):
        """Context manager for getting a database connection"""
        pool = self.get_pool(guild_id)
        conn = pool.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            pool.return_connection(conn)
    
    def _initialize_guild_database(self, guild_id: int):
        """Initialize database schema for a guild"""
        with self.get_connection(guild_id) as conn:
            cursor = conn.cursor()
            
            # Main users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    balance INTEGER DEFAULT 0,
                    captcha_attempts INTEGER DEFAULT 0,
                    is_locked INTEGER DEFAULT 0,
                    last_daily INTEGER DEFAULT 0,
                    purchased_items TEXT DEFAULT '',
                    marry TEXT DEFAULT '',
                    num_gold_tickets INTEGER DEFAULT 0,
                    num_diamond_tickets INTEGER DEFAULT 0,
                    open_items TEXT DEFAULT '',
                    daily_tickets INTEGER DEFAULT 0,
                    daily_streak INTEGER DEFAULT 0,
                    total_tickets INTEGER DEFAULT 0,
                    vietlottery_tickets INTEGER DEFAULT 0,
                    vietlottery_numbers TEXT DEFAULT '',
                    kimcuong INTEGER DEFAULT 0,
                    pray INTEGER DEFAULT 0,
                    love_marry INTEGER DEFAULT 0,
                    response TEXT DEFAULT '',
                    reaction TEXT DEFAULT '',
                    love_items TEXT DEFAULT '',
                    coin_kc INTEGER DEFAULT 0,
                    last_voice TEXT DEFAULT NULL,
                    kho_ca TEXT DEFAULT '',
                    kho_moi TEXT DEFAULT '',
                    kho_can TEXT DEFAULT '',
                    exp_fish INTEGER DEFAULT 0,
                    quest_time INTEGER DEFAULT 0,
                    quest_mess INTEGER DEFAULT 0,
                    quest_image INTEGER DEFAULT 0,
                    quest TEXT DEFAULT '',
                    quest_done INTEGER DEFAULT 0,
                    quest_time_start INTEGER DEFAULT 0,
                    streak_toan INTEGER DEFAULT 0,
                    setup_marry1 TEXT DEFAULT '',
                    setup_marry2 TEXT DEFAULT '',
                    xu_hlw INTEGER DEFAULT 0,
                    xu_love INTEGER DEFAULT 0,
                    bxh_love INTEGER DEFAULT 0,
                    pray_so INTEGER DEFAULT 0,
                    pray_time INTEGER DEFAULT NULL,
                    work_so INTEGER DEFAULT 0,
                    work_time INTEGER DEFAULT NULL,
                    love_so INTEGER DEFAULT 0,
                    love_time INTEGER DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Guild settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS guild_settings (
                    id INTEGER PRIMARY KEY,
                    setting_key TEXT UNIQUE NOT NULL,
                    setting_value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Transactions log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_user_id INTEGER,
                    to_user_id INTEGER,
                    amount INTEGER,
                    transaction_type TEXT,
                    description TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Giveaways table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS giveaways (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    host_id INTEGER NOT NULL,
                    prize TEXT NOT NULL,
                    winners_count INTEGER DEFAULT 1,
                    participants TEXT DEFAULT '[]',
                    ended INTEGER DEFAULT 0,
                    end_time INTEGER,
                    channel_id INTEGER,
                    message_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_balance ON users(balance)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_users ON transactions(from_user_id, to_user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions(timestamp)')
            
            logger.info(f"Initialized database schema for guild {guild_id}")
    
    async def execute_async(self, guild_id: int, query: str, params: Tuple = ()) -> List[sqlite3.Row]:
        """Execute query asynchronously"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._execute_sync,
            guild_id,
            query,
            params
        )
    
    def _execute_sync(self, guild_id: int, query: str, params: Tuple = ()) -> List[sqlite3.Row]:
        """Execute query synchronously"""
        with self.get_connection(guild_id) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
    
    async def execute_many_async(self, guild_id: int, query: str, params_list: List[Tuple]):
        """Execute many queries asynchronously"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._execute_many_sync,
            guild_id,
            query,
            params_list
        )
    
    def _execute_many_sync(self, guild_id: int, query: str, params_list: List[Tuple]):
        """Execute many queries synchronously"""
        with self.get_connection(guild_id) as conn:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
    
    def get_cached(self, key: str) -> Optional[Any]:
        """Get cached value"""
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.cache_ttl:
                return value
            else:
                del self.cache[key]
        return None
    
    def set_cached(self, key: str, value: Any):
        """Set cached value"""
        self.cache[key] = (value, time.time())
    
    def clear_cache(self, guild_id: Optional[int] = None):
        """Clear cache for a guild or all guilds"""
        if guild_id:
            keys_to_delete = [k for k in self.cache.keys() if k.startswith(f"{guild_id}:")]
            for key in keys_to_delete:
                del self.cache[key]
        else:
            self.cache.clear()
    
    # User management methods
    async def get_user(self, guild_id: int, user_id: int) -> Optional[Dict]:
        """Get user data"""
        cache_key = f"{guild_id}:user:{user_id}"
        cached = self.get_cached(cache_key)
        if cached:
            return cached
        
        result = await self.execute_async(
            guild_id,
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,)
        )
        
        if result:
            user_data = dict(result[0])
            self.set_cached(cache_key, user_data)
            return user_data
        return None
    
    async def create_user(self, guild_id: int, user_id: int, initial_balance: int = 0) -> bool:
        """Create new user"""
        try:
            await self.execute_async(
                guild_id,
                "INSERT INTO users (user_id, balance) VALUES (?, ?)",
                (user_id, initial_balance)
            )
            self.clear_cache(guild_id)
            return True
        except sqlite3.IntegrityError:
            return False
    
    async def update_user_balance(self, guild_id: int, user_id: int, amount: int, operation: str = "add") -> bool:
        """Update user balance"""
        if operation == "add":
            query = "UPDATE users SET balance = balance + ? WHERE user_id = ?"
        elif operation == "subtract":
            query = "UPDATE users SET balance = balance - ? WHERE user_id = ?"
        elif operation == "set":
            query = "UPDATE users SET balance = ? WHERE user_id = ?"
        else:
            raise ValueError(f"Invalid operation: {operation}")
        
        await self.execute_async(guild_id, query, (amount, user_id))
        
        # Clear cache for this user
        cache_key = f"{guild_id}:user:{user_id}"
        if cache_key in self.cache:
            del self.cache[cache_key]
        
        return True
    
    async def transfer_money(self, guild_id: int, from_user_id: int, to_user_id: int, amount: int) -> bool:
        """Transfer money between users with transaction logging"""
        try:
            # Use a single connection for the transaction
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self.executor,
                self._transfer_money_sync,
                guild_id,
                from_user_id,
                to_user_id,
                amount
            )
        except Exception as e:
            logger.error(f"Transfer failed: {e}")
            return False
    
    def _transfer_money_sync(self, guild_id: int, from_user_id: int, to_user_id: int, amount: int) -> bool:
        """Synchronous money transfer with transaction"""
        with self.get_connection(guild_id) as conn:
            cursor = conn.cursor()
            
            try:
                # Start transaction
                conn.execute("BEGIN TRANSACTION")
                
                # Check sender balance
                cursor.execute("SELECT balance FROM users WHERE user_id = ?", (from_user_id,))
                sender = cursor.fetchone()
                if not sender or sender[0] < amount:
                    conn.rollback()
                    return False
                
                # Update balances
                cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, from_user_id))
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, to_user_id))
                
                # Log transaction
                cursor.execute("""
                    INSERT INTO transactions (from_user_id, to_user_id, amount, transaction_type, description)
                    VALUES (?, ?, ?, 'transfer', 'User transfer')
                """, (from_user_id, to_user_id, amount))
                
                conn.commit()
                
                # Clear cache
                self.clear_cache(guild_id)
                
                return True
            except Exception as e:
                conn.rollback()
                raise e
    
    async def get_leaderboard(self, guild_id: int, limit: int = 10) -> List[Dict]:
        """Get balance leaderboard"""
        cache_key = f"{guild_id}:leaderboard:{limit}"
        cached = self.get_cached(cache_key)
        if cached:
            return cached
        
        result = await self.execute_async(
            guild_id,
            "SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT ?",
            (limit,)
        )
        
        leaderboard = [dict(row) for row in result]
        self.set_cached(cache_key, leaderboard)
        return leaderboard
    
    def close_all(self):
        """Close all connection pools"""
        for pool in self.pools.values():
            pool.close()
        self.pools.clear()
        self.executor.shutdown(wait=True)
        logger.info("Closed all database connections")

# Global database manager instance
db_manager = DatabaseManager()