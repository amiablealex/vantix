"""
Database initialization and connection management
"""

import sqlite3
import os
from datetime import datetime
import config

DATABASE_PATH = config.DATABASE_PATH


def get_db_connection():
    """Get a database connection with row factory"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database with required tables"""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Teams table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS teams (
            entry_id INTEGER PRIMARY KEY,
            team_name TEXT NOT NULL,
            manager_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Gameweeks table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gameweeks (
            id INTEGER PRIMARY KEY,
            deadline TEXT NOT NULL,
            finished INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Gameweek points table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gameweek_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id INTEGER NOT NULL,
            gameweek INTEGER NOT NULL,
            points INTEGER NOT NULL,
            total_points INTEGER NOT NULL,
            rank INTEGER,
            bank REAL,
            value REAL,
            event_transfers INTEGER,
            event_transfers_cost INTEGER,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (entry_id) REFERENCES teams (entry_id),
            FOREIGN KEY (gameweek) REFERENCES gameweeks (id),
            UNIQUE(entry_id, gameweek)
        )
    ''')
    
    # Transfers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transfers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id INTEGER NOT NULL,
            gameweek INTEGER NOT NULL,
            transfer_count INTEGER DEFAULT 0,
            transfers_in TEXT,
            transfers_out TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (entry_id) REFERENCES teams (entry_id),
            UNIQUE(entry_id, gameweek)
        )
    ''')
    
    # Chip usage table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chip_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id INTEGER NOT NULL,
            gameweek INTEGER NOT NULL,
            chip_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (entry_id) REFERENCES teams (entry_id),
            UNIQUE(entry_id, gameweek, chip_name)
        )
    ''')
    
    # Player stats table (aggregated goals, assists, clean sheets per team)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS player_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id INTEGER NOT NULL,
            total_goals INTEGER DEFAULT 0,
            total_assists INTEGER DEFAULT 0,
            total_clean_sheets INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (entry_id) REFERENCES teams (entry_id),
            UNIQUE(entry_id)
        )
    ''')
    
    # Differentials table (players unique to each team)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS differentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id INTEGER NOT NULL,
            gameweek INTEGER NOT NULL,
            differential_players TEXT,
            differential_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (entry_id) REFERENCES teams (entry_id),
            UNIQUE(entry_id, gameweek)
        )
    ''')
    
    # Current squads table (stores full 15-player squad for each team)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS current_squads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id INTEGER NOT NULL,
            gameweek INTEGER NOT NULL,
            player_ids TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (entry_id) REFERENCES teams (entry_id),
            UNIQUE(entry_id, gameweek)
        )
    ''')
    
    # Players table (stores player ID to name mapping)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            player_id INTEGER PRIMARY KEY,
            web_name TEXT NOT NULL,
            full_name TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create indexes for better query performance
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_gameweek_points_entry 
        ON gameweek_points(entry_id, gameweek)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_transfers_entry 
        ON transfers(entry_id, gameweek)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_chip_usage_entry 
        ON chip_usage(entry_id, gameweek)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_differentials_entry 
        ON differentials(entry_id, gameweek)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_current_squads_entry 
        ON current_squads(entry_id, gameweek)
    ''')
    
    conn.commit()
    conn.close()
    
    print(f"Database initialized at {DATABASE_PATH}")


def clear_data():
    """Clear all data from tables (useful for fresh data collection)"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM differentials')
    cursor.execute('DELETE FROM player_stats')
    cursor.execute('DELETE FROM chip_usage')
    cursor.execute('DELETE FROM transfers')
    cursor.execute('DELETE FROM gameweek_points')
    cursor.execute('DELETE FROM gameweeks')
    cursor.execute('DELETE FROM teams')
    
    conn.commit()
    conn.close()
    
    print("All data cleared from database")


if __name__ == '__main__':
    init_db()
