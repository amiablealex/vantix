#!/usr/bin/env python3
"""
Automatic patcher for app.py to add multi-league support
This script modifies app.py in-place to support multiple leagues
"""

import re
import sys

def patch_app_py(filename='app.py'):
    """Patch app.py for multi-league support"""
    
    print(f"Reading {filename}...")
    with open(filename, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # 1. Update imports
    print("1. Updating imports...")
    content = content.replace(
        'from data.database import init_db, get_db_connection',
        'from data.database import init_db, get_db_connection, get_league_connection, get_league_db_path'
    )
    
    if 'import os' not in content[:500]:
        content = content.replace(
            'import config',
            'import config\nimport os'
        )
    
    # 2. Remove old FPL collector initialization
    print("2. Removing old FPL collector initialization...")
    content = re.sub(
        r'# Initialize FPL data collector\nfpl_collector = FPLDataCollector\([^)]+\)',
        '# FPL collectors created per-league as needed',
        content
    )
    
    # 3. Update helper functions to accept league_code
    print("3. Updating helper functions...")
    
    # Update get_current_gameweek
    content = re.sub(
        r'def get_current_gameweek\(\):',
        'def get_current_gameweek(league_code=None):',
        content
    )
    content = re.sub(
        r"def get_current_gameweek\(league_code=None\):\s+\"\"\"[^\"]+\"\"\"\s+conn = get_db_connection\(\)",
        """def get_current_gameweek(league_code=None):
    \"\"\"Get the current active gameweek\"\"\"
    conn = get_league_connection(league_code) if league_code else get_db_connection()""",
        content
    )
    
    # Update get_last_completed_gameweek
    content = re.sub(
        r'def get_last_completed_gameweek\(\):',
        'def get_last_completed_gameweek(league_code=None):',
        content
    )
    content = re.sub(
        r"def get_last_completed_gameweek\(league_code=None\):\s+\"\"\"[^\"]+\"\"\"\s+conn = get_db_connection\(\)",
        """def get_last_completed_gameweek(league_code=None):
    \"\"\"Get the last completed gameweek\"\"\"
    conn = get_league_connection(league_code) if league_code else get_db_connection()""",
        content
    )
    
    # 4. Add format_time_ago helper function (after get_season_string)
    print("4. Adding format_time_ago helper...")
    if 'def format_time_ago' not in content:
        time_ago_func = '''

def format_time_ago(timestamp_str):
    """Format timestamp as relative time"""
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
        diff = now - dt
        
        if diff.days > 365:
            return f"{diff.days // 365}y ago"
        elif diff.days > 30:
            return f"{diff.days // 30}mo ago"
        elif diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600}h ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60}m ago"
        else:
            return "Just now"
    except:
        return "Unknown"
'''
        # Insert after get_season_string function
        content = re.sub(
            r"(def get_season_string\(\):.*?return f.*?\n)",
            r"\1" + time_ago_func,
            content,
            flags=re.DOTALL
        )
    
    # 5. Replace main dashboard route with league list + league-specific dashboard
    print("5. Adding multi-league routes...")
    
    # Find and replace the @app.route('/') def dashboard()
    old_dashboard_route = r"@app\.route\('/'\)\ndef dashboard\(\):[^@]+"
    
    new_routes = '''@app.route('/')
def league_list():
    """Landing page with all configured leagues"""
    leagues_info = []
    
    for league in config.LEAGUES:
        league_code = league['code']
        db_path = get_league_db_path(league_code)
        
        info = {
            'code': league_code,
            'name': league['name'],
            'description': league['description'],
            'team_count': 0,
            'last_updated': None,
            'last_updated_display': 'Never'
        }
        
        if os.path.exists(db_path):
            try:
                conn = get_league_connection(league_code)
                count = conn.execute('SELECT COUNT(*) as count FROM teams').fetchone()
                info['team_count'] = count['count'] if count else 0
                
                last_update = conn.execute(
                    'SELECT MAX(created_at) as last_update FROM gameweek_points'
                ).fetchone()
                
                if last_update and last_update['last_update']:
                    info['last_updated'] = last_update['last_update']
                    info['last_updated_display'] = format_time_ago(last_update['last_update'])
                
                conn.close()
            except Exception as e:
                logger.error(f"Error reading league {league_code}: {e}")
        
        leagues_info.append(info)
    
    return render_template('league_list.html', leagues=leagues_info)


@app.route('/<int:league_code>')
def dashboard_league(league_code):
    """Dashboard for specific league"""
    league_config = next((l for l in config.LEAGUES if l['code'] == league_code), None)
    
    if not league_config:
        return render_template('error.html', error=f'League {league_code} not configured'), 404
    
    db_path = get_league_db_path(league_code)
    if not os.path.exists(db_path):
        return render_template('error.html', 
            error=f'No data for league {league_code}. Run collect_all_leagues.py first.'), 404
    
    return render_template('dashboard.html', 
        league_code=league_code,
        league_name=league_config['name']
    )


'''
    
    content = re.sub(old_dashboard_route, new_routes, content, flags=re.DOTALL)
    
    # 6. Update all API routes to include league_code
    print("6. Updating API routes...")
    
    api_endpoints = [
        'cumulative-points',
        'league-positions',
        'recent-transfers',
        'stats',
        'form-chart',
        'points-distribution',
        'team-comparison',
        'biggest-movers',
        'weekly-performance',
        'head-to-head',
        'differentials',
        'podium'
    ]
    
    for endpoint in api_endpoints:
        # Update route decorator
        content = re.sub(
            rf"@app\.route\('/api/{endpoint}'\)",
            f"@app.route('/api/<int:league_code>/{endpoint}')",
            content
        )
        
        # Update function signature
        func_name = endpoint.replace('-', '_')
        content = re.sub(
            rf"def api_{func_name}\(\):",
            f"def api_{func_name}(league_code):",
            content
        )
        
        # Update get_db_connection() calls to use league
        # This is done in the next step for all functions
    
    # 7. Replace get_db_connection() with get_league_connection(league_code) in API functions
    print("7. Updating database connections in API functions...")
    
    # Find all API functions and replace conn = get_db_connection()
    for endpoint in api_endpoints:
        func_name = endpoint.replace('-', '_')
        pattern = rf"(def api_{func_name}\(league_code\):.*?)(conn = get_db_connection\(\))"
        replacement = r"\1conn = get_league_connection(league_code)"
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        # Also update helper function calls
        pattern2 = rf"(def api_{func_name}\(league_code\):.*?)(get_current_gameweek\(\))"
        replacement2 = r"\1get_current_gameweek(league_code)"
        content = re.sub(pattern2, replacement2, content, flags=re.DOTALL)
        
        pattern3 = rf"(def api_{func_name}\(league_code\):.*?)(get_last_completed_gameweek\(\))"
        replacement3 = r"\1get_last_completed_gameweek(league_code)"
        content = re.sub(pattern3, replacement3, content, flags=re.DOTALL)
    
    # 8. Replace old /api/refresh with new league-specific endpoints
    print("8. Updating refresh endpoints...")
    
    old_refresh = r"@app\.route\('/api/refresh', methods=\['POST'\]\)\ndef api_refresh\(\):.*?return jsonify.*?\n\n"
    
    new_refresh = '''@app.route('/api/<int:league_code>/refresh', methods=['POST'])
def api_refresh_league(league_code):
    """Refresh specific league"""
    try:
        league_config = next((l for l in config.LEAGUES if l['code'] == league_code), None)
        if not league_config:
            return jsonify({'status': 'error', 'message': 'League not found'}), 404
        
        logger.info(f"Refreshing league {league_code}")
        collector = FPLDataCollector(team_id=None, league_id=league_code)
        collector.collect_all_data()
        
        return jsonify({'status': 'success', 'message': f'League {league_code} refreshed'})
    except Exception as e:
        logger.error(f"Error refreshing league {league_code}: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/refresh-all', methods=['POST'])
def api_refresh_all():
    """Refresh all configured leagues"""
    try:
        logger.info("Refreshing all leagues")
        for league in config.LEAGUES:
            logger.info(f"Refreshing league {league['code']}")
            collector = FPLDataCollector(team_id=None, league_id=league['code'])
            collector.collect_all_data()
        
        return jsonify({'status': 'success', 'message': 'All leagues refreshed'})
    except Exception as e:
        logger.error(f"Error refreshing all leagues: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


'''
    
    content = re.sub(old_refresh, new_refresh, content, flags=re.DOTALL)
    
    # Check if anything changed
    if content == original_content:
        print("\n⚠️  Warning: No changes were made to the file!")
        print("The file may already be patched or the patterns didn't match.")
        return False
    
    # Write the patched content
    print(f"\nWriting patched version to {filename}...")
    with open(filename, 'w') as f:
        f.write(content)
    
    print("\n✅ Successfully patched app.py!")
    print("\nNext steps:")
    print("1. Review the changes in app.py")
    print("2. Update dashboard.js to use /api/<league_code>/... URLs")
    print("3. Run: python collect_all_leagues.py")
    print("4. Restart Flask")
    
    return True


if __name__ == '__main__':
    import sys
    
    filename = sys.argv[1] if len(sys.argv) > 1 else 'app.py'
    
    print("="*70)
    print("App.py Multi-League Patcher")
    print("="*70)
    print(f"\nThis will modify {filename} to add multi-league support")
    print("A backup will NOT be created - commit your changes first!")
    print()
    
    response = input("Continue? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        success = patch_app_py(filename)
        sys.exit(0 if success else 1)
    else:
        print("Patching cancelled.")
        sys.exit(0)
