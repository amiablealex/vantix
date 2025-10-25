#!/usr/bin/env python3
"""
Improved app.py patcher for multi-league support
Handles actual function names and structure
"""

import re
import sys

def patch_app_py(filename='app.py'):
    """Patch app.py for multi-league support"""
    
    print(f"Reading {filename}...")
    with open(filename, 'r') as f:
        lines = f.readlines()
    
    content = ''.join(lines)
    original_content = content
    
    # 1. Update imports
    print("1. Updating imports...")
    content = content.replace(
        'from data.database import init_db, get_db_connection',
        'from data.database import init_db, get_db_connection, get_league_connection, get_league_db_path'
    )
    
    if '\nimport os\n' not in content and 'import os' not in content[:1000]:
        # Add after other imports
        content = content.replace(
            'import config\n',
            'import config\nimport os\n'
        )
    
    # 2. Update helper functions
    print("2. Updating helper functions...")
    
    # Update get_current_gameweek
    content = re.sub(
        r'def get_current_gameweek\(\):',
        'def get_current_gameweek(league_code=None):',
        content
    )
    
    # Update the function body
    content = re.sub(
        r"(def get_current_gameweek\(league_code=None\):\s+['\"].*?['\"])\s+conn = get_db_connection\(\)",
        r"\1\n    conn = get_league_connection(league_code) if league_code else get_db_connection()",
        content,
        flags=re.DOTALL
    )
    
    # Update get_last_completed_gameweek
    content = re.sub(
        r'def get_last_completed_gameweek\(\):',
        'def get_last_completed_gameweek(league_code=None):',
        content
    )
    
    content = re.sub(
        r"(def get_last_completed_gameweek\(league_code=None\):\s+['\"].*?['\"])\s+conn = get_db_connection\(\)",
        r"\1\n    conn = get_league_connection(league_code) if league_code else get_db_connection()",
        content,
        flags=re.DOTALL
    )
    
    # 3. Add format_time_ago if not present
    print("3. Adding format_time_ago helper...")
    if 'def format_time_ago' not in content:
        time_ago_func = '''

def format_time_ago(timestamp_str):
    """Format timestamp as relative time"""
    try:
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
        # Find position after get_season_string
        season_string_pos = content.find('def get_season_string():')
        if season_string_pos > 0:
            # Find end of function (next @app or def at same indentation)
            next_func = content.find('\n\n@app', season_string_pos)
            if next_func > 0:
                content = content[:next_func] + time_ago_func + content[next_func:]
    
    # 4. Replace main route
    print("4. Replacing main route...")
    
    # Find the @app.route('/') block - it might be called index() or dashboard()
    main_route_pattern = r"@app\.route\('/'\)\ndef (index|dashboard)\(\):.*?(?=\n@app\.route|$)"
    
    new_main_routes = '''@app.route('/')
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
        league_name=league_config['name'])


'''
    
    content = re.sub(main_route_pattern, new_main_routes, content, flags=re.DOTALL)
    
    # 5. Update ALL API routes
    print("5. Updating API routes...")
    
    api_endpoints = [
        ('cumulative-points', 'cumulative_points'),
        ('league-positions', 'league_positions'),
        ('recent-transfers', 'recent_transfers'),
        ('stats', 'stats'),
        ('form-chart', 'form_chart'),
        ('points-distribution', 'points_distribution'),
        ('team-comparison', 'team_comparison'),
        ('biggest-movers', 'biggest_movers'),
        ('weekly-performance', 'weekly_performance'),
        ('head-to-head', 'head_to_head'),
        ('differentials', 'differentials'),
        ('podium', 'podium')
    ]
    
    for endpoint_url, endpoint_func in api_endpoints:
        # Update route decorator
        old_route = f"@app.route('/api/{endpoint_url}')"
        new_route = f"@app.route('/api/<int:league_code>/{endpoint_url}')"
        content = content.replace(old_route, new_route)
        
        # Update function signature
        old_sig = f"def api_{endpoint_func}():"
        new_sig = f"def api_{endpoint_func}(league_code):"
        content = content.replace(old_sig, new_sig)
        
        # Update get_db_connection() in each function
        # Find the function and replace its first get_db_connection()
        func_pattern = f"(def api_{endpoint_func}\\(league_code\\):.*?)(conn = get_db_connection\\(\\))"
        replacement = r"\1conn = get_league_connection(league_code)"
        content = re.sub(func_pattern, replacement, content, count=1, flags=re.DOTALL)
        
        # Update helper calls
        func_pattern2 = f"(def api_{endpoint_func}\\(league_code\\):.*?)(get_current_gameweek\\(\\))"
        replacement2 = r"\1get_current_gameweek(league_code)"
        content = re.sub(func_pattern2, replacement2, content, flags=re.DOTALL)
        
        func_pattern3 = f"(def api_{endpoint_func}\\(league_code\\):.*?)(get_last_completed_gameweek\\(\\))"
        replacement3 = r"\1get_last_completed_gameweek(league_code)"
        content = re.sub(func_pattern3, replacement3, content, flags=re.DOTALL)
    
    # 6. Add new refresh endpoints (remove old one)
    print("6. Updating refresh endpoints...")
    
    # Remove old refresh endpoint
    old_refresh_pattern = r"@app\.route\('/api/refresh', methods=\['POST'\]\)\ndef api_refresh\(\):.*?(?=\n@app\.route|$)"
    content = re.sub(old_refresh_pattern, '', content, flags=re.DOTALL)
    
    # Add new refresh endpoints at the end (before error handlers)
    new_refresh = '''

@app.route('/api/<int:league_code>/refresh', methods=['POST'])
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
    
    # Insert before error handlers
    error_handler_pos = content.find('@app.errorhandler(404)')
    if error_handler_pos > 0:
        content = content[:error_handler_pos] + new_refresh + '\n' + content[error_handler_pos:]
    else:
        # Add at end
        content += new_refresh
    
    # Check if changes were made
    if content == original_content:
        print("\n⚠️  Warning: No changes were made!")
        return False
    
    # Write patched file
    print(f"\nWriting patched version to {filename}...")
    with open(filename, 'w') as f:
        f.write(content)
    
    print("\n✅ Successfully patched app.py!")
    print("\nVerify the changes:")
    print("  grep 'def league_list' app.py")
    print("  grep 'def dashboard_league' app.py")
    print("  grep '/api/<int:league_code>/' app.py")
    
    return True


if __name__ == '__main__':
    filename = sys.argv[1] if len(sys.argv) > 1 else 'app.py'
    
    print("="*70)
    print("Improved App.py Multi-League Patcher")
    print("="*70)
    print()
    
    response = input("Continue? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        success = patch_app_py(filename)
        sys.exit(0 if success else 1)
    else:
        print("Cancelled.")
        sys.exit(0)
