#!/bin/bash
# Vantix Database Maintenance Script
# Runs: VACUUM to optimize + Archive old seasons
# Schedule: Weekly (Sundays at 2 AM)

set -e

# Configuration
APP_DIR="/home/pi/fpl-dashboard"
ARCHIVE_DIR="${APP_DIR}/archive_dbs"
LOG_FILE="${APP_DIR}/logs/maintenance.log"

# Ensure directories exist
mkdir -p "${ARCHIVE_DIR}"
mkdir -p "$(dirname ${LOG_FILE})"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

log "===== Database Maintenance Started ====="

# Change to app directory
cd "${APP_DIR}"

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Activate virtual environment
source venv/bin/activate

# Run Python maintenance script
python3 << 'PYTHON_SCRIPT'
import os
import sys
import sqlite3
import json
import shutil
from datetime import datetime
from pathlib import Path

APP_DIR = Path("/home/pi/fpl-dashboard")
ARCHIVE_DIR = APP_DIR / "archive_dbs"
DATA_DIR = APP_DIR / "data"

# Load leagues
with open(APP_DIR / "leagues.json") as f:
    leagues = json.load(f)

def get_current_fpl_season():
    """Get current FPL season (e.g., 2024/25)"""
    now = datetime.now()
    if now.month >= 8:  # Season starts August
        return f"{now.year}/{str(now.year + 1)[-2:]}"
    else:
        return f"{now.year - 1}/{str(now.year)[-2:]}"

def get_season_from_gameweek_dates(db_path):
    """Determine season from gameweek deadline dates in database"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get earliest gameweek deadline
        result = cursor.execute(
            "SELECT MIN(deadline) FROM gameweeks WHERE id = 1"
        ).fetchone()
        
        conn.close()
        
        if result and result[0]:
            # Parse deadline (format: 2024-08-16T17:30:00Z)
            deadline_year = int(result[0][:4])
            
            # FPL season starts in August
            return f"{deadline_year}/{str(deadline_year + 1)[-2:]}"
        
        return None
    except Exception as e:
        print(f"Error determining season: {e}")
        return None

def vacuum_database(db_path):
    """Run VACUUM to optimize database"""
    try:
        conn = sqlite3.connect(db_path)
        print(f"  Running VACUUM on {db_path.name}...")
        conn.execute("VACUUM")
        conn.close()
        print(f"  ✓ VACUUM completed")
        return True
    except Exception as e:
        print(f"  ✗ VACUUM failed: {e}")
        return False

def archive_old_season(league_code, db_path):
    """Archive database if it contains old season data"""
    current_season = get_current_fpl_season()
    db_season = get_season_from_gameweek_dates(db_path)
    
    if not db_season:
        print(f"  Could not determine season for {db_path.name}")
        return False
    
    print(f"  Database season: {db_season}, Current season: {current_season}")
    
    if db_season != current_season:
        # This is an old season - archive it
        archive_filename = f"fpl_data_{league_code}_{db_season.replace('/', '-')}.db"
        archive_path = ARCHIVE_DIR / archive_filename
        
        print(f"  → Archiving old season to {archive_filename}")
        shutil.copy2(db_path, archive_path)
        
        # Remove the old database (will be recreated on next data collection)
        db_path.unlink()
        print(f"  ✓ Archived and removed old season database")
        return True
    else:
        print(f"  ✓ Database is current season - keeping active")
        return False

# Main maintenance
print(f"\n=== Current FPL Season: {get_current_fpl_season()} ===\n")

for league in leagues:
    league_code = league['code']
    db_path = DATA_DIR / f"fpl_data_{league_code}.db"
    
    print(f"League {league_code} ({league['name']}):")
    
    if not db_path.exists():
        print(f"  Database not found - skipping")
        continue
    
    # Check if old season
    archived = archive_old_season(league_code, db_path)
    
    if not archived and db_path.exists():
        # Only VACUUM if not archived (i.e., current season)
        vacuum_database(db_path)
    
    print()

print("=== Maintenance Complete ===")
PYTHON_SCRIPT

log "===== Database Maintenance Completed ====="
log ""
