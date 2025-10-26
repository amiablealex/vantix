"""
Vantix - Fantasy Premier League Dashboard
Main Flask Application (Production Optimized)
"""

from flask import Flask, render_template, jsonify, request
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import datetime
import logging
import os
import requests
from functools import wraps

from data.database import init_db, get_db_connection, get_league_connection, get_league_db_path
from data.fpl_api import FPLDataCollector
import config

# Configure logging
os.makedirs(os.path.dirname(config.LOG_FILE), exist_ok=True)
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(config)

# Initialize Flask-Caching
cache = Cache(app)

# Initialize Flask-Limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[config.RATELIMIT_DEFAULT],
    storage_uri=config.RATELIMIT_STORAGE_URL,
    strategy=config.RATELIMIT_STRATEGY
)

# Initialize database
init_db()

# Global refresh lock
_refresh_lock = {}

# ==================== HELPER FUNCTIONS ====================

def get_current_gameweek(league_code=None):
    """Get the current active gameweek"""
    conn = get_league_connection(league_code) if league_code else get_db_connection()
    current = conn.execute(
        'SELECT id FROM gameweeks WHERE finished = 0 ORDER BY id LIMIT 1'
    ).fetchone()
    
    if not current:
        current = conn.execute(
            'SELECT id FROM gameweeks ORDER BY id DESC LIMIT 1'
        ).fetchone()
    
    conn.close()
    return current['id'] if current else 1


def get_last_completed_gameweek(league_code=None):
    """Get the last completed (finished) gameweek"""
    conn = get_league_connection(league_code) if league_code else get_db_connection()
    last_completed = conn.execute(
        'SELECT MAX(id) as max_gw FROM gameweeks WHERE finished = 1'
    ).fetchone()
    conn.close()
    return last_completed['max_gw'] if last_completed and last_completed['max_gw'] else 1


def get_season_string():
    """Get current FPL season string (e.g., '2024/25')"""
    now = datetime.now()
    if now.month >= 8:
        return f"{now.year}/{str(now.year + 1)[-2:]}"
    else:
        return f"{now.year - 1}/{str(now.year)[-2:]}"


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


def check_fpl_api_updated():
    """Check if FPL API has new data by comparing current GW status"""
    try:
        response = requests.get(
            'https://fantasy.premierleague.com/api/bootstrap-static/',
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        # Get current event
        current_event = next(
            (e for e in data['events'] if not e['finished']),
            data['events'][-1] if data['events'] else None
        )
        
        if not current_event:
            return False, "No gameweek data available"
        
        # Check if current GW is finished but not yet updated in DB
        return current_event, None
        
    except Exception as e:
        logger.error(f"Error checking FPL API: {e}")
        return False, str(e)


def is_refresh_needed(league_code):
    """Smart refresh logic - check if refresh is actually needed"""
    try:
        # Check FPL API current gameweek status
        fpl_current, error = check_fpl_api_updated()
        if error:
            return False, f"Cannot check FPL API: {error}"
        
        if not fpl_current:
            return False, "No FPL data available"
        
        # Get our database status
        conn = get_league_connection(league_code)
        
        # Get last updated time
        last_update = conn.execute(
            'SELECT MAX(created_at) as last_update FROM gameweek_points'
        ).fetchone()
        
        if not last_update or not last_update['last_update']:
            conn.close()
            return True, "No data in database yet"
        
        # Get latest gameweek in DB
        latest_gw = conn.execute(
            'SELECT MAX(id) as max_gw FROM gameweeks WHERE finished = 1'
        ).fetchone()
        
        conn.close()
        
        db_latest_finished_gw = latest_gw['max_gw'] if latest_gw else 0
        fpl_current_gw = fpl_current['id']
        fpl_is_finished = fpl_current['finished']
        
        # If FPL current GW is finished but we don't have it yet, refresh needed
        if fpl_is_finished and db_latest_finished_gw < fpl_current_gw:
            return True, f"GW{fpl_current_gw} finished but not in database"
        
        # Check if data is stale (>6 hours old)
        last_update_time = datetime.fromisoformat(
            last_update['last_update'].replace('Z', '+00:00')
        )
        now = datetime.now(last_update_time.tzinfo) if last_update_time.tzinfo else datetime.now()
        hours_since_update = (now - last_update_time).total_seconds() / 3600
        
        if hours_since_update > 6:
            return True, f"Data is {hours_since_update:.1f} hours old"
        
        return False, "Data is up to date"
        
    except Exception as e:
        logger.error(f"Error checking refresh need: {e}")
        return False, f"Error: {str(e)}"


def require_refresh_token(f):
    """Decorator to protect refresh endpoints with token"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('X-Refresh-Token') or request.args.get('token')
        
        if not token or token != config.REFRESH_TOKEN:
            logger.warning(f"Unauthorized refresh attempt from {get_remote_address()}")
            return jsonify({
                'status': 'error',
                'message': 'Unauthorized. Valid refresh token required.'
            }), 401
        
        return f(*args, **kwargs)
    
    return decorated_function


# ==================== ROUTES ====================

@app.route('/')
@limiter.limit("60 per minute")
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
@limiter.limit("60 per minute")
def dashboard_league(league_code):
    """Dashboard for specific league"""
    league_config = next((l for l in config.LEAGUES if l['code'] == league_code), None)
    
    if not league_config:
        return render_template('error.html', error=f'League {league_code} not configured'), 404
    
    db_path = get_league_db_path(league_code)
    if not os.path.exists(db_path):
        return render_template('error.html', 
            error=f'No data for league {league_code}. Run collect_all_leagues.py first.'), 404

    conn = get_league_connection(league_code)
    teams = conn.execute('SELECT * FROM teams ORDER BY team_name').fetchall()
    teams = [dict(team) for team in teams]
    
    current_gw = get_current_gameweek(league_code)
    
    last_update_row = conn.execute(
        'SELECT MAX(created_at) as last_update FROM gameweek_points'
    ).fetchone()
    last_update = format_time_ago(last_update_row['last_update']) if last_update_row and last_update_row['last_update'] else None
    
    conn.close()
    
    return render_template('dashboard.html', 
        league_code=league_code,
        league_name=league_config['name'],
        teams=teams,
        current_gameweek=current_gw,
        season=get_season_string(),
        last_update=last_update
    )


# ==================== API ENDPOINTS (All with Caching) ====================

@app.route('/api/<int:league_code>/cumulative-points')
@limiter.limit("120 per minute")
@cache.cached(timeout=300, query_string=True)
def api_cumulative_points(league_code):
    """API endpoint for cumulative points chart data"""
    try:
        selected_teams = request.args.getlist('teams')
        last_completed_gw = get_last_completed_gameweek(league_code)
        
        conn = get_league_connection(league_code)
        
        if selected_teams:
            placeholders = ','.join('?' * len(selected_teams))
            query = f'''
                SELECT 
                    t.entry_id,
                    t.team_name,
                    gp.gameweek,
                    SUM(gp.points) OVER (PARTITION BY t.entry_id ORDER BY gp.gameweek) as cumulative_points
                FROM teams t
                JOIN gameweek_points gp ON t.entry_id = gp.entry_id
                WHERE t.entry_id IN ({placeholders}) AND gp.gameweek <= ?
                ORDER BY gp.gameweek, t.team_name
            '''
            rows = conn.execute(query, selected_teams + [last_completed_gw]).fetchall()
        else:
            rows = conn.execute('''
                SELECT 
                    t.entry_id,
                    t.team_name,
                    gp.gameweek,
                    SUM(gp.points) OVER (PARTITION BY t.entry_id ORDER BY gp.gameweek) as cumulative_points
                FROM teams t
                JOIN gameweek_points gp ON t.entry_id = gp.entry_id
                WHERE gp.gameweek <= ?
                ORDER BY gp.gameweek, t.team_name
            ''', [last_completed_gw]).fetchall()
        
        conn.close()
        
        teams_data = {}
        for row in rows:
            entry_id = row['entry_id']
            if entry_id not in teams_data:
                teams_data[entry_id] = {
                    'team_name': row['team_name'],
                    'data': []
                }
            teams_data[entry_id]['data'].append({
                'x': row['gameweek'],
                'y': row['cumulative_points']
            })
        
        return jsonify({'teams': list(teams_data.values())})
    except Exception as e:
        logger.error(f"Error fetching cumulative points: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/<int:league_code>/league-positions')
@limiter.limit("120 per minute")
@cache.cached(timeout=300, query_string=True)
def api_league_positions(league_code):
    """API endpoint for league position worm chart"""
    try:
        selected_teams = request.args.getlist('teams')
        last_completed_gw = get_last_completed_gameweek(league_code)
        
        conn = get_league_connection(league_code)
        
        if selected_teams:
            placeholders = ','.join('?' * len(selected_teams))
            query = f'''
                WITH cumulative_points AS (
                    SELECT 
                        t.entry_id,
                        t.team_name,
                        gp.gameweek,
                        SUM(gp.points) OVER (PARTITION BY t.entry_id ORDER BY gp.gameweek) as total_points
                    FROM teams t
                    JOIN gameweek_points gp ON t.entry_id = gp.entry_id
                    WHERE t.entry_id IN ({placeholders}) AND gp.gameweek <= ?
                ),
                ranked AS (
                    SELECT 
                        entry_id,
                        team_name,
                        gameweek,
                        total_points,
                        RANK() OVER (PARTITION BY gameweek ORDER BY total_points DESC) as position
                    FROM cumulative_points
                )
                SELECT * FROM ranked ORDER BY gameweek, position
            '''
            rows = conn.execute(query, selected_teams + [last_completed_gw]).fetchall()
        else:
            rows = conn.execute('''
                WITH cumulative_points AS (
                    SELECT 
                        t.entry_id,
                        t.team_name,
                        gp.gameweek,
                        SUM(gp.points) OVER (PARTITION BY t.entry_id ORDER BY gp.gameweek) as total_points
                    FROM teams t
                    JOIN gameweek_points gp ON t.entry_id = gp.entry_id
                    WHERE gp.gameweek <= ?
                ),
                ranked AS (
                    SELECT 
                        entry_id,
                        team_name,
                        gameweek,
                        total_points,
                        RANK() OVER (PARTITION BY gameweek ORDER BY total_points DESC) as position
                    FROM cumulative_points
                )
                SELECT * FROM ranked ORDER BY gameweek, position
            ''', [last_completed_gw]).fetchall()
        
        if selected_teams:
            chip_query = f'''
                SELECT entry_id, gameweek, chip_name
                FROM chip_usage
                WHERE entry_id IN ({placeholders}) AND gameweek <= ?
            '''
            chips = conn.execute(chip_query, selected_teams + [last_completed_gw]).fetchall()
        else:
            chips = conn.execute('''
                SELECT entry_id, gameweek, chip_name
                FROM chip_usage
                WHERE gameweek <= ?
            ''', [last_completed_gw]).fetchall()
        
        conn.close()
        
        teams_data = {}
        for row in rows:
            entry_id = row['entry_id']
            if entry_id not in teams_data:
                teams_data[entry_id] = {
                    'team_name': row['team_name'],
                    'data': [],
                    'chips': []
                }
            teams_data[entry_id]['data'].append({
                'x': row['gameweek'],
                'y': row['position']
            })
        
        for chip in chips:
            if chip['entry_id'] in teams_data:
                teams_data[chip['entry_id']]['chips'].append({
                    'gameweek': chip['gameweek'],
                    'chip': chip['chip_name']
                })
        
        return jsonify({'teams': list(teams_data.values())})
    except Exception as e:
        logger.error(f"Error fetching league positions: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/<int:league_code>/recent-transfers')
@limiter.limit("120 per minute")
@cache.cached(timeout=300, query_string=True)
def api_recent_transfers(league_code):
    """API endpoint for recent transfers"""
    try:
        selected_teams = request.args.getlist('teams')
        current_gw = get_current_gameweek(league_code)
        
        conn = get_league_connection(league_code)
        
        if selected_teams:
            placeholders = ','.join('?' * len(selected_teams))
            query = f'''
                SELECT 
                    t.team_name,
                    tr.gameweek,
                    tr.transfers_in,
                    tr.transfers_out,
                    tr.transfer_count,
                    gp.event_transfers_cost
                FROM teams t
                LEFT JOIN transfers tr ON t.entry_id = tr.entry_id AND tr.gameweek = ?
                LEFT JOIN gameweek_points gp ON t.entry_id = gp.entry_id AND gp.gameweek = ?
                WHERE t.entry_id IN ({placeholders})
                ORDER BY t.team_name
            '''
            params = [current_gw, current_gw] + selected_teams
            rows = conn.execute(query, params).fetchall()
        else:
            rows = conn.execute('''
                SELECT 
                    t.team_name,
                    tr.gameweek,
                    tr.transfers_in,
                    tr.transfers_out,
                    tr.transfer_count,
                    gp.event_transfers_cost
                FROM teams t
                LEFT JOIN transfers tr ON t.entry_id = tr.entry_id AND tr.gameweek = ?
                LEFT JOIN gameweek_points gp ON t.entry_id = gp.entry_id AND gp.gameweek = ?
                ORDER BY t.team_name
            ''', [current_gw, current_gw]).fetchall()
        
        # Get chip usage for current gameweek
        if selected_teams:
            chip_query = f'''
                SELECT entry_id, chip_name
                FROM chip_usage
                WHERE gameweek = ? AND entry_id IN ({placeholders})
            '''
            chip_params = [current_gw] + selected_teams
            chips = conn.execute(chip_query, chip_params).fetchall()
        else:
            chips = conn.execute('''
                SELECT cu.entry_id, cu.chip_name
                FROM chip_usage cu
                JOIN teams t ON cu.entry_id = t.entry_id
                WHERE cu.gameweek = ?
            ''', [current_gw]).fetchall()
        
        conn.close()
        
        # Create chip lookup
        chip_lookup = {}
        for chip in chips:
            chip_lookup[chip['entry_id']] = chip['chip_name']
        
        # Get entry_id lookup
        conn = get_league_connection(league_code)
        if selected_teams:
            team_query = f'''
                SELECT entry_id, team_name
                FROM teams
                WHERE entry_id IN ({placeholders})
            '''
            teams_data = conn.execute(team_query, selected_teams).fetchall()
        else:
            teams_data = conn.execute('SELECT entry_id, team_name FROM teams').fetchall()
        conn.close()
        
        team_to_entry = {team['team_name']: team['entry_id'] for team in teams_data}
        
        transfers = []
        for row in rows:
            entry_id = team_to_entry.get(row['team_name'])
            chip_used = chip_lookup.get(entry_id, None) if entry_id else None
            transfer_cost = row['event_transfers_cost'] if row['event_transfers_cost'] else 0
            
            if row['transfer_count'] and row['transfer_count'] > 0:
                transfers.append({
                    'team_name': row['team_name'],
                    'transfers_in': row['transfers_in'].split(',') if row['transfers_in'] else [],
                    'transfers_out': row['transfers_out'].split(',') if row['transfers_out'] else [],
                    'count': row['transfer_count'],
                    'transfer_cost': transfer_cost,
                    'chip_used': chip_used
                })
            else:
                transfers.append({
                    'team_name': row['team_name'],
                    'transfers_in': [],
                    'transfers_out': [],
                    'count': 0,
                    'transfer_cost': 0,
                    'chip_used': chip_used
                })
        
        return jsonify({'transfers': transfers, 'gameweek': current_gw})
    except Exception as e:
        logger.error(f"Error fetching recent transfers: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/<int:league_code>/stats')
@limiter.limit("120 per minute")
@cache.cached(timeout=300, query_string=True)
def api_stats(league_code):
    """API endpoint for league statistics"""
    try:
        selected_teams = request.args.getlist('teams')
        conn = get_league_connection(league_code)
        
        where_clause = ""
        params = []
        if selected_teams:
            placeholders = ','.join('?' * len(selected_teams))
            where_clause = f"WHERE t.entry_id IN ({placeholders})"
            params = selected_teams
        
        most_goals = conn.execute(f'''
            SELECT t.team_name, ps.total_goals
            FROM teams t
            JOIN player_stats ps ON t.entry_id = ps.entry_id
            {where_clause}
            ORDER BY ps.total_goals DESC
            LIMIT 1
        ''', params).fetchone()
        
        most_clean_sheets = conn.execute(f'''
            SELECT t.team_name, ps.total_clean_sheets
            FROM teams t
            JOIN player_stats ps ON t.entry_id = ps.entry_id
            {where_clause}
            ORDER BY ps.total_clean_sheets DESC
            LIMIT 1
        ''', params).fetchone()
        
        highest_gw_score = conn.execute(f'''
            SELECT t.team_name, gp.gameweek, gp.points
            FROM teams t
            JOIN gameweek_points gp ON t.entry_id = gp.entry_id
            {where_clause}
            ORDER BY gp.points DESC
            LIMIT 1
        ''', params).fetchone()
        
        current_leader = conn.execute(f'''
            SELECT 
                t.team_name,
                SUM(gp.points) as total_points
            FROM teams t
            JOIN gameweek_points gp ON t.entry_id = gp.entry_id
            {where_clause}
            GROUP BY t.entry_id
            ORDER BY total_points DESC
            LIMIT 1
        ''', params).fetchone()
        
        conn.close()
        
        return jsonify({
            'most_goals': {
                'team': most_goals['team_name'] if most_goals else 'N/A',
                'goals': most_goals['total_goals'] if most_goals else 0
            },
            'most_clean_sheets': {
                'team': most_clean_sheets['team_name'] if most_clean_sheets else 'N/A',
                'clean_sheets': most_clean_sheets['total_clean_sheets'] if most_clean_sheets else 0
            },
            'highest_gameweek': {
                'team': highest_gw_score['team_name'] if highest_gw_score else 'N/A',
                'gameweek': highest_gw_score['gameweek'] if highest_gw_score else 0,
                'points': highest_gw_score['points'] if highest_gw_score else 0
            },
            'current_leader': {
                'team': current_leader['team_name'] if current_leader else 'N/A',
                'points': current_leader['total_points'] if current_leader else 0
            }
        })
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/<int:league_code>/form-chart')
@limiter.limit("120 per minute")
@cache.cached(timeout=300, query_string=True)
def api_form_chart(league_code):
    """API endpoint for recent form (last 5 gameweeks)"""
    try:
        conn = get_league_connection(league_code)
        last_completed = conn.execute('''
            SELECT MAX(id) as max_gw
            FROM gameweeks
            WHERE finished = 1
        ''').fetchone()
        
        if not last_completed or not last_completed['max_gw']:
            conn.close()
            return jsonify({'teams': []})
        
        end_gw = last_completed['max_gw']
        start_gw = max(1, end_gw - 4)
        
        selected_teams = request.args.getlist('teams')
        
        if selected_teams:
            placeholders = ','.join('?' * len(selected_teams))
            query = f'''
                SELECT 
                    t.entry_id,
                    t.team_name,
                    gp.gameweek,
                    gp.points
                FROM teams t
                JOIN gameweek_points gp ON t.entry_id = gp.entry_id
                WHERE gp.gameweek BETWEEN ? AND ? AND t.entry_id IN ({placeholders})
                ORDER BY gp.gameweek, t.team_name
            '''
            params = [start_gw, end_gw] + selected_teams
            rows = conn.execute(query, params).fetchall()
        else:
            rows = conn.execute('''
                SELECT 
                    t.entry_id,
                    t.team_name,
                    gp.gameweek,
                    gp.points
                FROM teams t
                JOIN gameweek_points gp ON t.entry_id = gp.entry_id
                WHERE gp.gameweek BETWEEN ? AND ?
                ORDER BY gp.gameweek, t.team_name
            ''', [start_gw, end_gw]).fetchall()
        
        conn.close()
        
        teams_data = {}
        for row in rows:
            entry_id = row['entry_id']
            if entry_id not in teams_data:
                teams_data[entry_id] = {
                    'team_name': row['team_name'],
                    'data': []
                }
            teams_data[entry_id]['data'].append({
                'x': row['gameweek'],
                'y': row['points']
            })
        
        return jsonify({'teams': list(teams_data.values())})
    except Exception as e:
        logger.error(f"Error fetching form chart: {e}")
        return jsonify({'error': str(e), 'teams': []}), 500


@app.route('/api/<int:league_code>/points-distribution')
@limiter.limit("120 per minute")
@cache.cached(timeout=300, query_string=True)
def api_points_distribution(league_code):
    """API endpoint for points distribution"""
    try:
        selected_teams = request.args.getlist('teams')
        
        conn = get_league_connection(league_code)
        
        if selected_teams:
            placeholders = ','.join('?' * len(selected_teams))
            query = f'''
                SELECT points
                FROM gameweek_points
                WHERE entry_id IN ({placeholders})
                ORDER BY points
            '''
            rows = conn.execute(query, selected_teams).fetchall()
        else:
            rows = conn.execute('''
                SELECT points
                FROM gameweek_points
                ORDER BY points
            ''').fetchall()
        
        conn.close()
        
        points_list = [row['points'] for row in rows]
        
        if not points_list:
            return jsonify({'bins': [], 'counts': []})
        
        bins = [0, 20, 40, 60, 80, 100, 150]
        counts = [0] * (len(bins) - 1)
        
        for points in points_list:
            for i in range(len(bins) - 1):
                if bins[i] <= points < bins[i + 1]:
                    counts[i] += 1
                    break
            else:
                if points >= bins[-1]:
                    counts[-1] += 1
        
        bin_labels = [f"{bins[i]}-{bins[i+1]}" for i in range(len(bins) - 1)]
        
        return jsonify({
            'labels': bin_labels,
            'counts': counts
        })
    except Exception as e:
        logger.error(f"Error fetching points distribution: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/<int:league_code>/team-comparison')
@limiter.limit("120 per minute")
@cache.cached(timeout=300, query_string=True)
def api_team_comparison(league_code):
    """API endpoint for detailed team comparison stats"""
    try:
        selected_teams = request.args.getlist('teams')
        
        if not selected_teams:
            return jsonify({'teams': []})
        
        conn = get_league_connection(league_code)
        last_completed_gw = get_last_completed_gameweek(league_code)
        
        comparison_data = []
        
        for team_id in selected_teams:
            team_info = conn.execute('''
                SELECT t.team_name, t.manager_name
                FROM teams t
                WHERE t.entry_id = ?
            ''', [team_id]).fetchone()
            
            if not team_info:
                continue
            
            total_points = conn.execute('''
                SELECT SUM(points) as total
                FROM gameweek_points
                WHERE entry_id = ? AND gameweek <= ?
            ''', [team_id, last_completed_gw]).fetchone()
            
            avg_points = conn.execute('''
                SELECT AVG(points) as avg
                FROM gameweek_points
                WHERE entry_id = ? AND gameweek <= ?
            ''', [team_id, last_completed_gw]).fetchone()
            
            highest_gw = conn.execute('''
                SELECT MAX(points) as highest
                FROM gameweek_points
                WHERE entry_id = ? AND gameweek <= ?
            ''', [team_id, last_completed_gw]).fetchone()
            
            lowest_gw = conn.execute('''
                SELECT MIN(points) as lowest
                FROM gameweek_points
                WHERE entry_id = ? AND gameweek <= ?
            ''', [team_id, last_completed_gw]).fetchone()
            
            total_transfers = conn.execute('''
                SELECT SUM(transfer_count) as total
                FROM transfers
                WHERE entry_id = ?
            ''', [team_id]).fetchone()
            
            hits_taken = conn.execute('''
                SELECT COUNT(*) as hits
                FROM transfers
                WHERE entry_id = ? AND transfer_count > 1
            ''', [team_id]).fetchone()
            
            chips_used = conn.execute('''
                SELECT COUNT(*) as count
                FROM chip_usage
                WHERE entry_id = ?
            ''', [team_id]).fetchone()
            
            comparison_data.append({
                'team_name': team_info['team_name'],
                'manager_name': team_info['manager_name'],
                'total_points': total_points['total'] if total_points['total'] else 0,
                'avg_points': round(avg_points['avg'], 1) if avg_points['avg'] else 0,
                'highest_gw': highest_gw['highest'] if highest_gw['highest'] else 0,
                'lowest_gw': lowest_gw['lowest'] if lowest_gw['lowest'] else 0,
                'total_transfers': total_transfers['total'] if total_transfers['total'] else 0,
                'hits_taken': hits_taken['hits'] if hits_taken['hits'] else 0,
                'chips_used': chips_used['count'] if chips_used['count'] else 0
            })
        
        conn.close()
        
        return jsonify({'teams': comparison_data})
    except Exception as e:
        logger.error(f"Error fetching team comparison: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/<int:league_code>/biggest-movers')
@limiter.limit("120 per minute")
@cache.cached(timeout=300, query_string=True)
def api_biggest_movers(league_code):
    """API endpoint for biggest position changes"""
    try:
        last_completed_gw = get_last_completed_gameweek(league_code)
        past_gw = max(1, last_completed_gw - 5)
        
        selected_teams = request.args.getlist('teams')
        
        conn = get_league_connection(league_code)
        
        if selected_teams:
            placeholders = ','.join('?' * len(selected_teams))
            query = f'''
                WITH past_totals AS (
                    SELECT 
                        t.entry_id,
                        t.team_name,
                        SUM(gp.points) as total_points
                    FROM teams t
                    JOIN gameweek_points gp ON t.entry_id = gp.entry_id
                    WHERE gp.gameweek <= ? AND t.entry_id IN ({placeholders})
                    GROUP BY t.entry_id, t.team_name
                ),
                past_rankings AS (
                    SELECT 
                        entry_id,
                        team_name,
                        total_points,
                        RANK() OVER (ORDER BY total_points DESC) as rank
                    FROM past_totals
                ),
                current_totals AS (
                    SELECT 
                        t.entry_id,
                        t.team_name,
                        SUM(gp.points) as total_points
                    FROM teams t
                    JOIN gameweek_points gp ON t.entry_id = gp.entry_id
                    WHERE gp.gameweek <= ? AND t.entry_id IN ({placeholders})
                    GROUP BY t.entry_id, t.team_name
                ),
                current_rankings AS (
                    SELECT 
                        entry_id,
                        team_name,
                        total_points,
                        RANK() OVER (ORDER BY total_points DESC) as rank
                    FROM current_totals
                )
                SELECT 
                    c.team_name,
                    c.rank as current_rank,
                    p.rank as past_rank,
                    (p.rank - c.rank) as change
                FROM current_rankings c
                LEFT JOIN past_rankings p ON c.entry_id = p.entry_id
                ORDER BY change DESC
            '''
            params = [past_gw] + selected_teams + [last_completed_gw] + selected_teams
            rows = conn.execute(query, params).fetchall()
        else:
            rows = conn.execute('''
                WITH past_totals AS (
                    SELECT 
                        t.entry_id,
                        t.team_name,
                        SUM(gp.points) as total_points
                    FROM teams t
                    JOIN gameweek_points gp ON t.entry_id = gp.entry_id
                    WHERE gp.gameweek <= ?
                    GROUP BY t.entry_id, t.team_name
                ),
                past_rankings AS (
                    SELECT 
                        entry_id,
                        team_name,
                        total_points,
                        RANK() OVER (ORDER BY total_points DESC) as rank
                    FROM past_totals
                ),
                current_totals AS (
                    SELECT 
                        t.entry_id,
                        t.team_name,
                        SUM(gp.points) as total_points
                    FROM teams t
                    JOIN gameweek_points gp ON t.entry_id = gp.entry_id
                    WHERE gp.gameweek <= ?
                    GROUP BY t.entry_id, t.team_name
                ),
                current_rankings AS (
                    SELECT 
                        entry_id,
                        team_name,
                        total_points,
                        RANK() OVER (ORDER BY total_points DESC) as rank
                    FROM current_totals
                )
                SELECT 
                    c.team_name,
                    c.rank as current_rank,
                    p.rank as past_rank,
                    (p.rank - c.rank) as change
                FROM current_rankings c
                LEFT JOIN past_rankings p ON c.entry_id = p.entry_id
                ORDER BY change DESC
            ''', [past_gw, last_completed_gw]).fetchall()
        
        conn.close()
        
        climbers = []
        fallers = []
        
        for row in rows:
            mover = {
                'team_name': row['team_name'],
                'change': abs(row['change']) if row['change'] else 0,
                'current_rank': row['current_rank'],
                'past_rank': row['past_rank']
            }
            
            if row['change'] > 0:
                climbers.append(mover)
            elif row['change'] < 0:
                fallers.append(mover)
        
        return jsonify({
            'climbers': climbers[:5],
            'fallers': fallers[:5]
        })
    except Exception as e:
        logger.error(f"Error fetching biggest movers: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/<int:league_code>/weekly-performance')
@limiter.limit("120 per minute")
@cache.cached(timeout=300, query_string=True)
def api_weekly_performance(league_code):
    """API endpoint for weekly performance heatmap"""
    try:
        selected_teams = request.args.getlist('teams')
        last_completed_gw = get_last_completed_gameweek(league_code)
        
        conn = get_league_connection(league_code)
        
        if not selected_teams:
            conn.close()
            return jsonify({'teams': []})
        
        placeholders = ','.join('?' * len(selected_teams))
        
        query = f'''
            SELECT 
                t.entry_id,
                t.team_name,
                gp.gameweek,
                gp.points
            FROM teams t
            JOIN gameweek_points gp ON t.entry_id = gp.entry_id
            WHERE t.entry_id IN ({placeholders}) AND gp.gameweek <= ?
            ORDER BY t.entry_id, gp.gameweek
        '''
        rows = conn.execute(query, selected_teams + [last_completed_gw]).fetchall()
        
        conn.close()
        
        teams_data = {}
        for row in rows:
            entry_id = row['entry_id']
            if entry_id not in teams_data:
                teams_data[entry_id] = {
                    'team_name': row['team_name'],
                    'gameweeks': []
                }
            teams_data[entry_id]['gameweeks'].append({
                'gameweek': row['gameweek'],
                'points': row['points']
            })
        
        return jsonify({'teams': list(teams_data.values())})
    except Exception as e:
        logger.error(f"Error fetching weekly performance: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/<int:league_code>/head-to-head')
@limiter.limit("120 per minute")
@cache.cached(timeout=300, query_string=True)
def api_head_to_head(league_code):
    """API endpoint for head-to-head weekly wins"""
    try:
        selected_teams = request.args.getlist('teams')
        last_completed_gw = get_last_completed_gameweek(league_code)
        
        conn = get_league_connection(league_code)
        
        if not selected_teams or len(selected_teams) < 2:
            conn.close()
            return jsonify({'teams': []})
        
        placeholders = ','.join('?' * len(selected_teams))
        
        query = f'''
            SELECT 
                t.entry_id,
                t.team_name,
                gp.gameweek,
                gp.points
            FROM teams t
            JOIN gameweek_points gp ON t.entry_id = gp.entry_id
            WHERE t.entry_id IN ({placeholders}) AND gp.gameweek <= ?
            ORDER BY gp.gameweek, gp.points DESC
        '''
        rows = conn.execute(query, selected_teams + [last_completed_gw]).fetchall()
        
        conn.close()
        
        gameweeks = {}
        for row in rows:
            gw = row['gameweek']
            if gw not in gameweeks:
                gameweeks[gw] = []
            gameweeks[gw].append({
                'entry_id': row['entry_id'],
                'team_name': row['team_name'],
                'points': row['points']
            })
        
        team_records = {}
        for team_id in selected_teams:
            team_records[int(team_id)] = {'wins': 0, 'draws': 0, 'team_name': ''}
        
        for gw, teams in gameweeks.items():
            if not teams:
                continue
            
            max_points = max(team['points'] for team in teams)
            winners = [team for team in teams if team['points'] == max_points]
            
            if len(winners) == 1:
                winner_id = winners[0]['entry_id']
                team_records[winner_id]['wins'] += 1
                team_records[winner_id]['team_name'] = winners[0]['team_name']
            else:
                for winner in winners:
                    winner_id = winner['entry_id']
                    team_records[winner_id]['draws'] += 1
                    team_records[winner_id]['team_name'] = winner['team_name']
            
            for team in teams:
                team_records[team['entry_id']]['team_name'] = team['team_name']
        
        result = [
            {
                'team_name': record['team_name'],
                'wins': record['wins'],
                'draws': record['draws']
            }
            for record in team_records.values()
            if record['team_name']
        ]
        
        result.sort(key=lambda x: (x['wins'], x['draws']), reverse=True)
        
        return jsonify({'teams': result})
    except Exception as e:
        logger.error(f"Error fetching head-to-head: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/<int:league_code>/differentials')
@limiter.limit("120 per minute")
@cache.cached(timeout=300, query_string=True)
def api_differentials(league_code):
    """API endpoint for differential tracker"""
    try:
        selected_teams = request.args.getlist('teams')
        
        conn = get_league_connection(league_code)
        
        if not selected_teams or len(selected_teams) < 2:
            conn.close()
            return jsonify({'teams': []})
        
        current_gw = get_current_gameweek(league_code)
        
        placeholders = ','.join('?' * len(selected_teams))
        
        squad_rows = conn.execute(f'''
            SELECT cs.entry_id, cs.player_ids, t.team_name
            FROM current_squads cs
            JOIN teams t ON cs.entry_id = t.entry_id
            WHERE cs.entry_id IN ({placeholders})
            AND cs.gameweek = ?
        ''', selected_teams + [current_gw]).fetchall()
        
        if not squad_rows:
            conn.close()
            return jsonify({'teams': []})
        
        squads = {}
        team_names = {}
        for row in squad_rows:
            entry_id = row['entry_id']
            team_names[entry_id] = row['team_name']
            if row['player_ids']:
                squads[entry_id] = set(map(int, row['player_ids'].split(',')))
            else:
                squads[entry_id] = set()
        
        player_ownership = {}
        for squad in squads.values():
            for player_id in squad:
                player_ownership[player_id] = player_ownership.get(player_id, 0) + 1
        
        all_player_ids = set(player_ownership.keys())
        
        player_names_map = {}
        if all_player_ids:
            placeholders_players = ','.join('?' * len(all_player_ids))
            player_rows = conn.execute(f'''
                SELECT player_id, web_name
                FROM players
                WHERE player_id IN ({placeholders_players})
            ''', list(all_player_ids)).fetchall()
            
            for row in player_rows:
                player_names_map[row['player_id']] = row['web_name']
        
        conn.close()
        
        differentials_data = []
        
        for entry_id, squad in squads.items():
            true_differentials = []
            
            for player_id in squad:
                if player_ownership.get(player_id, 0) == 1:
                    player_name = player_names_map.get(player_id, f'Player {player_id}')
                    true_differentials.append(player_name)
            
            differentials_data.append({
                'team_name': team_names[entry_id],
                'differential_count': len(true_differentials),
                'recent_differentials': true_differentials
            })
        
        return jsonify({'teams': differentials_data})
        
    except Exception as e:
        logger.error(f"Error fetching differentials: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/<int:league_code>/podium')
@limiter.limit("120 per minute")
@cache.cached(timeout=300, query_string=True)
def api_podium(league_code):
    """API endpoint for top 3 podium"""
    try:
        selected_teams = request.args.getlist('teams')
        
        conn = get_league_connection(league_code)
        
        if not selected_teams:
            conn.close()
            return jsonify({'podium': []})
        
        placeholders = ','.join('?' * len(selected_teams))
        
        query = f'''
            SELECT 
                t.entry_id,
                t.team_name,
                t.manager_name,
                SUM(gp.points) as total_points
            FROM teams t
            JOIN gameweek_points gp ON t.entry_id = gp.entry_id
            WHERE t.entry_id IN ({placeholders})
            GROUP BY t.entry_id
            ORDER BY total_points DESC
            LIMIT 3
        '''
        rows = conn.execute(query, selected_teams).fetchall()
        
        podium = []
        for idx, row in enumerate(rows):
            recent_form = conn.execute('''
                SELECT AVG(points) as avg_points
                FROM (
                    SELECT points
                    FROM gameweek_points
                    WHERE entry_id = ?
                    ORDER BY gameweek DESC
                    LIMIT 3
                )
            ''', [row['entry_id']]).fetchone()
            
            if idx == 0:
                gap = 0
            else:
                leader_points = rows[0]['total_points']
                gap = leader_points - row['total_points']
            
            podium.append({
                'position': idx + 1,
                'team_name': row['team_name'],
                'manager_name': row['manager_name'],
                'total_points': row['total_points'],
                'recent_form': round(recent_form['avg_points'], 1) if recent_form['avg_points'] else 0,
                'gap': gap
            })
        
        conn.close()
        return jsonify({'podium': podium})
    except Exception as e:
        logger.error(f"Error fetching podium: {e}")
        return jsonify({'error': str(e)}), 500


# ==================== REFRESH ENDPOINTS (Token Protected) ====================

@app.route('/api/<int:league_code>/refresh', methods=['POST'])
@limiter.limit("3 per hour")
@require_refresh_token
def api_refresh_league(league_code):
    """Refresh specific league (token protected)"""
    try:
        league_config = next((l for l in config.LEAGUES if l['code'] == league_code), None)
        if not league_config:
            return jsonify({'status': 'error', 'message': 'League not found'}), 404
        
        # Check if refresh is needed
        refresh_needed, reason = is_refresh_needed(league_code)
        if not refresh_needed:
            return jsonify({
                'status': 'skipped',
                'message': f'Refresh not needed: {reason}'
            })
        
        # Check lock
        if _refresh_lock.get(league_code, False):
            return jsonify({
                'status': 'error',
                'message': 'Refresh already in progress'
            }), 409
        
        _refresh_lock[league_code] = True
        
        try:
            logger.info(f"Refreshing league {league_code}: {reason}")
            collector = FPLDataCollector(team_id=None, league_id=league_code)
            collector.collect_all_data()
            
            # Clear cache for this league
            cache.clear()
            
            return jsonify({
                'status': 'success',
                'message': f'League {league_code} refreshed successfully',
                'reason': reason
            })
        finally:
            _refresh_lock[league_code] = False
            
    except Exception as e:
        logger.error(f"Error refreshing league {league_code}: {e}")
        _refresh_lock[league_code] = False
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/refresh-all', methods=['POST'])
@limiter.limit("1 per hour")
@require_refresh_token
def api_refresh_all():
    """Refresh all configured leagues (token protected)"""
    try:
        logger.info("Refreshing all leagues")
        results = []
        
        for league in config.LEAGUES:
            league_code = league['code']
            
            # Check if refresh needed
            refresh_needed, reason = is_refresh_needed(league_code)
            
            if not refresh_needed:
                results.append({
                    'league_code': league_code,
                    'status': 'skipped',
                    'reason': reason
                })
                continue
            
            # Check lock
            if _refresh_lock.get(league_code, False):
                results.append({
                    'league_code': league_code,
                    'status': 'error',
                    'reason': 'Refresh already in progress'
                })
                continue
            
            _refresh_lock[league_code] = True
            
            try:
                logger.info(f"Refreshing league {league_code}: {reason}")
                collector = FPLDataCollector(team_id=None, league_id=league_code)
                collector.collect_all_data()
                
                results.append({
                    'league_code': league_code,
                    'status': 'success',
                    'reason': reason
                })
            except Exception as e:
                logger.error(f"Error refreshing league {league_code}: {e}")
                results.append({
                    'league_code': league_code,
                    'status': 'error',
                    'reason': str(e)
                })
            finally:
                _refresh_lock[league_code] = False
        
        # Clear all cache
        cache.clear()
        
        return jsonify({
            'status': 'completed',
            'message': 'Refresh process completed',
            'results': results
        })
    except Exception as e:
        logger.error(f"Error refreshing all leagues: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ==================== HEALTH CHECK ====================

@app.route('/health')
@limiter.exempt
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Check if leagues configured
        if not config.LEAGUES:
            return jsonify({
                'status': 'warning',
                'message': 'No leagues configured',
                'timestamp': datetime.now().isoformat()
            }), 200
        
        # Check if at least one league DB exists
        leagues_status = []
        for league in config.LEAGUES:
            db_path = get_league_db_path(league['code'])
            exists = os.path.exists(db_path)
            leagues_status.append({
                'code': league['code'],
                'name': league['name'],
                'database_exists': exists
            })
        
        all_exist = all(l['database_exists'] for l in leagues_status)
        
        return jsonify({
            'status': 'healthy' if all_exist else 'degraded',
            'leagues': leagues_status,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', error='Page not found'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', error='Internal server error'), 500


@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({
        'error': 'Rate limit exceeded',
        'message': str(e.description)
    }), 429


if __name__ == '__main__':
    app.run(debug=config.DEBUG, host='0.0.0.0', port=5000)
