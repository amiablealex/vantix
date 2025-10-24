#!/usr/bin/env python3
"""
Database Inspection Utility
Quick tool to view database contents and statistics
"""

import sqlite3
import sys
from datetime import datetime
import config

def print_header(text):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def inspect_database():
    """Inspect and display database contents"""
    try:
        conn = sqlite3.connect(config.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        print_header("Vantix Database Inspection")
        print(f"Database: {config.DATABASE_PATH}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Teams
        print_header("Teams")
        teams = cursor.execute('SELECT * FROM teams ORDER BY team_name').fetchall()
        print(f"Total teams: {len(teams)}")
        if teams:
            print("\nTeams in league:")
            for team in teams:
                print(f"  • {team['team_name']} ({team['manager_name']}) - ID: {team['entry_id']}")
        
        # Gameweeks
        print_header("Gameweeks")
        gameweeks = cursor.execute(
            'SELECT * FROM gameweeks ORDER BY id DESC LIMIT 5'
        ).fetchall()
        print(f"Total gameweeks: {cursor.execute('SELECT COUNT(*) FROM gameweeks').fetchone()[0]}")
        if gameweeks:
            print("\nRecent gameweeks:")
            for gw in gameweeks:
                status = "✓ Finished" if gw['finished'] else "⏳ In Progress"
                print(f"  GW{gw['id']}: {gw['deadline']} - {status}")
        
        # Points Summary
        print_header("Points Summary")
        points_summary = cursor.execute('''
            SELECT 
                t.team_name,
                SUM(gp.points) as total_points,
                COUNT(gp.gameweek) as gameweeks_played
            FROM teams t
            LEFT JOIN gameweek_points gp ON t.entry_id = gp.entry_id
            GROUP BY t.entry_id
            ORDER BY total_points DESC
        ''').fetchall()
        
        if points_summary:
            print("\nCurrent Standings:")
            for i, team in enumerate(points_summary, 1):
                print(f"  {i}. {team['team_name']}: {team['total_points']} pts ({team['gameweeks_played']} GWs)")
        
        # Transfer Activity
        print_header("Transfer Activity")
        transfer_count = cursor.execute(
            'SELECT COUNT(*) as count FROM transfers WHERE transfer_count > 0'
        ).fetchone()
        print(f"Teams with transfers: {transfer_count['count']}")
        
        recent_transfers = cursor.execute('''
            SELECT t.team_name, tr.gameweek, tr.transfer_count
            FROM teams t
            JOIN transfers tr ON t.entry_id = tr.entry_id
            WHERE tr.transfer_count > 0
            ORDER BY tr.gameweek DESC
            LIMIT 10
        ''').fetchall()
        
        if recent_transfers:
            print("\nRecent transfer activity:")
            for transfer in recent_transfers:
                print(f"  GW{transfer['gameweek']}: {transfer['team_name']} made {transfer['transfer_count']} transfer(s)")
        
        # Chip Usage
        print_header("Chip Usage")
        chip_count = cursor.execute('SELECT COUNT(*) as count FROM chip_usage').fetchone()
        print(f"Total chips played: {chip_count['count']}")
        
        chips_by_type = cursor.execute('''
            SELECT chip_name, COUNT(*) as count
            FROM chip_usage
            GROUP BY chip_name
            ORDER BY count DESC
        ''').fetchall()
        
        if chips_by_type:
            print("\nChips by type:")
            for chip in chips_by_type:
                print(f"  • {chip['chip_name']}: {chip['count']} times")
        
        # Player Stats
        print_header("Player Statistics")
        top_scorers = cursor.execute('''
            SELECT t.team_name, ps.total_goals, ps.total_assists, ps.total_clean_sheets
            FROM teams t
            JOIN player_stats ps ON t.entry_id = ps.entry_id
            ORDER BY ps.total_goals DESC
            LIMIT 5
        ''').fetchall()
        
        if top_scorers:
            print("\nTop teams by goals scored:")
            for i, team in enumerate(top_scorers, 1):
                print(f"  {i}. {team['team_name']}: {team['total_goals']} goals, "
                      f"{team['total_assists']} assists, {team['total_clean_sheets']} clean sheets")
        
        # Data Freshness
        print_header("Data Freshness")
        last_update = cursor.execute(
            'SELECT MAX(updated_at) as last_update FROM gameweek_points'
        ).fetchone()
        
        if last_update and last_update['last_update']:
            print(f"Last data update: {last_update['last_update']}")
        else:
            print("No update timestamp found")
        
        print("\n" + "=" * 60)
        print("Inspection complete!")
        print("=" * 60 + "\n")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"\n❌ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    inspect_database()
