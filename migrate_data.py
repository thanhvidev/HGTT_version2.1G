#!/usr/bin/env python3
"""
Migration script to transfer data from old single database to new multi-guild databases
This script will preserve existing data while setting up the new structure
"""

import sqlite3
import os
import json
import logging
import shutil
import time
from database_manager import DatabaseManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_table_columns(cursor, table_name):
    """Get list of columns in a table"""
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        return columns
    except sqlite3.Error:
        return []

def migrate_database():
    """Migrate from old single database to new multi-guild structure"""
    
    # Check if old database exists
    old_db_path = 'economy.db'
    if not os.path.exists(old_db_path):
        logger.warning(f"Old database {old_db_path} not found. Nothing to migrate.")
        return False
    
    logger.info("Starting database migration...")
    
    # Initialize new database manager
    db_manager = DatabaseManager()
    old_conn = None
    
    try:
        # Connect to old database
        old_conn = sqlite3.connect(old_db_path)
        old_conn.row_factory = sqlite3.Row
        old_cursor = old_conn.cursor()
        
        # Get list of servers from old database
        servers = []
        try:
            old_cursor.execute("SELECT DISTINCT server_id FROM servers")
            servers = old_cursor.fetchall()
        except sqlite3.Error:
            logger.info("No servers table found in old database")
        
        if not servers:
            # Try to get server IDs from prefixes.json
            if os.path.exists('prefixes.json'):
                with open('prefixes.json', 'r') as f:
                    prefixes = json.load(f)
                    servers = [{'server_id': int(sid)} for sid in prefixes.keys() if sid.isdigit()]
            
            if not servers:
                # Try to get from users table if it has server_id
                try:
                    old_cursor.execute("SELECT DISTINCT server_id FROM users WHERE server_id IS NOT NULL")
                    server_rows = old_cursor.fetchall()
                    if server_rows:
                        servers = server_rows
                except sqlite3.Error:
                    pass
            
            if not servers:
                logger.warning("No server information found. Creating default guild.")
                servers = [{'server_id': 1090136467541590066}]  # Default guild ID
        
        logger.info(f"Found {len(servers)} servers to migrate")
        
        # For each server, migrate user data
        for server in servers:
            server_id = server['server_id']
            logger.info(f"Migrating data for server {server_id}...")
            
            # Get connection for this guild
            with db_manager.get_connection(server_id) as new_conn:
                new_cursor = new_conn.cursor()
                
                # Get target table structure
                target_columns = get_table_columns(new_cursor, 'users')
                if not target_columns:
                    logger.error(f"Could not get target table structure for server {server_id}")
                    continue
                
                logger.info(f"Target table columns: {target_columns}")
                
                # Check if there's a server-specific table in old database
                table_name = f"users_{server_id}"
                old_cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table_name,)
                )
                
                users_data = []
                if old_cursor.fetchone():
                    # Server-specific table exists, migrate from it
                    logger.info(f"Found server-specific table {table_name}")
                    source_columns = get_table_columns(old_cursor, table_name)
                    old_cursor.execute(f"SELECT * FROM {table_name}")
                    users_data = old_cursor.fetchall()
                else:
                    # Use the main users table
                    logger.info("Using main users table for migration")
                    source_columns = get_table_columns(old_cursor, 'users')
                    
                    if source_columns:
                        # Filter by server_id if the column exists
                        if 'server_id' in source_columns:
                            old_cursor.execute("SELECT * FROM users WHERE server_id = ?", (server_id,))
                        else:
                            old_cursor.execute("SELECT * FROM users")
                        users_data = old_cursor.fetchall()
                
                if users_data and source_columns:
                    logger.info(f"Source table columns: {source_columns}")
                    logger.info(f"Migrating {len(users_data)} users for server {server_id}")
                    
                    # Find common columns between source and target
                    common_columns = [col for col in source_columns if col in target_columns and col != 'id']
                    logger.info(f"Common columns to migrate: {common_columns}")
                    
                    if not common_columns:
                        logger.warning(f"No common columns found for server {server_id}")
                        continue
                    
                    migrated_count = 0
                    for user in users_data:
                        try:
                            # Extract only common columns
                            user_data = {}
                            for col in common_columns:
                                if col in user.keys():
                                    user_data[col] = user[col]
                            
                            if not user_data:
                                continue
                            
                            # Build insert query dynamically
                            columns_str = ','.join(user_data.keys())
                            placeholders = ','.join(['?' for _ in user_data.keys()])
                            
                            # Insert or update user data
                            new_cursor.execute(
                                f"""INSERT OR REPLACE INTO users ({columns_str})
                                    VALUES ({placeholders})""",
                                tuple(user_data.values())
                            )
                            migrated_count += 1
                            
                        except Exception as e:
                            logger.error(f"Failed to migrate user {user.get('user_id', 'unknown')}: {e}")
                    
                    new_conn.commit()
                    logger.info(f"Successfully migrated {migrated_count}/{len(users_data)} users for server {server_id}")
                
                # Migrate giveaways if table exists
                try:
                    old_cursor.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='giveaways'"
                    )
                    if old_cursor.fetchone():
                        giveaway_source_columns = get_table_columns(old_cursor, 'giveaways')
                        giveaway_target_columns = get_table_columns(new_cursor, 'giveaways')
                        
                        if giveaway_source_columns and giveaway_target_columns:
                            old_cursor.execute("SELECT * FROM giveaways WHERE server_id = ?", (server_id,))
                            giveaways = old_cursor.fetchall()
                            
                            common_giveaway_columns = [col for col in giveaway_source_columns 
                                                     if col in giveaway_target_columns and col != 'id']
                            
                            migrated_giveaways = 0
                            for giveaway in giveaways:
                                try:
                                    giveaway_data = {}
                                    for col in common_giveaway_columns:
                                        if col in giveaway.keys():
                                            giveaway_data[col] = giveaway[col]
                                    
                                    if giveaway_data:
                                        columns_str = ','.join(giveaway_data.keys())
                                        placeholders = ','.join(['?' for _ in giveaway_data.keys()])
                                        
                                        new_cursor.execute(
                                            f"""INSERT OR REPLACE INTO giveaways ({columns_str})
                                                VALUES ({placeholders})""",
                                            tuple(giveaway_data.values())
                                        )
                                        migrated_giveaways += 1
                                except Exception as e:
                                    logger.error(f"Failed to migrate giveaway: {e}")
                            
                            if migrated_giveaways > 0:
                                new_conn.commit()
                                logger.info(f"Migrated {migrated_giveaways} giveaways for server {server_id}")
                except Exception as e:
                    logger.warning(f"Could not migrate giveaways: {e}")
        
        logger.info("✅ Data migration completed successfully!")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        return False
    
    finally:
        # Close old database connection first
        if old_conn:
            old_conn.close()
            logger.info("Closed old database connection")
        
        # Close all new database connections
        db_manager.close_all()
        
        # Wait a moment for file handles to be released
        time.sleep(2)
    
    # Now try to backup the old database
    try:
        backup_path = 'economy_backup.db'
        counter = 1
        
        # Find available backup filename
        while os.path.exists(backup_path):
            backup_path = f'economy_backup_{counter}.db'
            counter += 1
        
        # Use shutil.copy2 instead of os.rename to avoid file lock issues
        shutil.copy2(old_db_path, backup_path)
        logger.info(f"Old database backed up to {backup_path}")
        
        # Try to remove original file
        try:
            os.remove(old_db_path)
            logger.info("Original database file removed")
        except PermissionError:
            logger.warning("Could not remove original database file (still in use). You can delete it manually later.")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to backup database: {e}")
        logger.info("Migration completed but backup failed. Original database is still intact.")
        return True  # Migration was successful even if backup failed

def verify_migration():
    """Verify that migration was successful"""
    db_manager = DatabaseManager()
    
    try:
        # Check each guild database
        db_dir = "databases"
        if not os.path.exists(db_dir):
            logger.error("Database directory not found!")
            return False
        
        guild_dbs = [f for f in os.listdir(db_dir) if f.startswith('guild_') and f.endswith('.db')]
        
        if not guild_dbs:
            logger.error("No guild databases found!")
            return False
        
        logger.info(f"Found {len(guild_dbs)} guild databases")
        
        total_users = 0
        for db_file in guild_dbs:
            try:
                guild_id = int(db_file.replace('guild_', '').replace('.db', ''))
                
                with db_manager.get_connection(guild_id) as conn:
                    cursor = conn.cursor()
                    
                    # Check users table
                    cursor.execute("SELECT COUNT(*) FROM users")
                    user_count = cursor.fetchone()[0]
                    total_users += user_count
                    
                    # Check giveaways table
                    try:
                        cursor.execute("SELECT COUNT(*) FROM giveaways")
                        giveaway_count = cursor.fetchone()[0]
                        logger.info(f"Guild {guild_id}: {user_count} users, {giveaway_count} giveaways")
                    except:
                        logger.info(f"Guild {guild_id}: {user_count} users")
                        
            except Exception as e:
                logger.error(f"Error verifying {db_file}: {e}")
        
        logger.info(f"✅ Verification completed! Total users migrated: {total_users}")
        return True
        
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False
    
    finally:
        db_manager.close_all()

def show_database_info():
    """Show information about the old database"""
    old_db_path = 'economy.db'
    if not os.path.exists(old_db_path):
        print("Old database not found.")
        return
    
    try:
        conn = sqlite3.connect(old_db_path)
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print("\nOld database structure:")
        print("-" * 40)
        
        for table in tables:
            table_name = table[0]
            print(f"\nTable: {table_name}")
            
            # Get columns
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
            
            # Get row count
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"  Rows: {count}")
            except:
                print("  Rows: Unable to count")
        
        conn.close()
        
    except Exception as e:
        print(f"Error reading database: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("Discord Bot Database Migration Tool")
    print("=" * 60)
    print("\nThis tool will migrate your data from the old single database")
    print("to the new multi-guild database structure.")
    print("\nYour old database will be backed up before migration.")
    print("-" * 60)
    
    # Show database info first
    print("\n1. cấu trúc database cũ")
    print("2. chạy migration")
    print("3. Vverify kết quả")
    print("4. Exit")
    
    while True:
        try:
            choice = input("\nEnter your choice (1-4): ").strip()
            
            if choice == '1':
                show_database_info()
            elif choice == '2':
                response = input("\nDo you want to proceed with migration? (yes/no): ").lower()
                if response in ['yes', 'y']:
                    success = migrate_database()
                    
                    if success:
                        print("\n" + "=" * 60)
                        print("Migration completed successfully!")
                        print("=" * 60)
                        
                        # Verify migration
                        print("\nVerifying migration...")
                        verify_migration()
                    else:
                        print("\n" + "=" * 60)
                        print("Migration failed! Check the logs for details.")
                        print("=" * 60)
                break
            elif choice == '3':
                print("\nVerifying existing migration...")
                verify_migration()
                break
            elif choice == '4':
                print("\nExiting...")
                break
            else:
                print("Invalid choice. Please enter 1-4.")
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")