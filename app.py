"""
Vantix - Fantasy Premier League Dashboard
Main Flask Application
"""

from flask import Flask, render_template, jsonify, request
from datetime import datetime
import logging
from data.database import init_db, get_db_connection
from data.scheduler import init_scheduler
from data.fpl_api import FPLDataCollector
import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(config)

# Initialize database
init_db()

# Initialize scheduler for data updates
scheduler = init_scheduler(app)

# Initialize FPL data collector
fpl_collector = FPLDataCollector(
    team_id=config.FPL_TEAM_ID,
    league_id=config.FPL_LEAGUE_ID
)


@app.route('/')
def index():
    """Main dashboard view"""
    try:
        conn = get_db_connection()
        
        # Get current gameweek
        current_gw = conn.execute(
            'SELECT id, deadline, finished FROM gameweeks ORDER BY id DESC LIMIT 1'
        ).fetchone()
        
        # Get league teams
        teams = conn.execute(
            'SELECT entry_id, team_name, manager_name FROM teams ORDER BY team_name'
        ).fetchall()
        
        # Get last updated timestamp
        last_update = conn.execute(
            'SELECT MAX(updated_at) as last_update FROM gameweek_points'
        ).fetchone()
        
        conn.close()
        
        return render_template(
            'dashboard.html',
            current_gameweek=current_gw['id'] if current_gw else 1,
            teams=[dict(t) for t in teams],
            last_update=last_update['last_update'] if last_update else None,
            league_name=config.LEAGUE_NAME
        )
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        return render_template('error.html', error=str(e)), 500


@app.route('/api/cumulative-points')
def api_cumulative_points():
    """API endpoint for cumulative points chart data"""
    try:
        selected_teams = request.args.getlist('teams')
        
        conn = get_db_connection()
        
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
                WHERE t.entry_id IN ({placeholders})
                ORDER BY gp.gameweek, t.team_name
            '''
            rows = conn.execute(query, selected_teams).fetchall()
        else:
            rows = conn.execute('''
                SELECT 
                    t.entry_id,
                    t.team_name,
                    gp.gameweek,
                    SUM(gp.points) OVER (PARTITION BY t.entry_id ORDER BY gp.gameweek) as cumulative_points
                FROM teams t
                JOIN gameweek_points gp ON t.entry_id = gp.entry_id
                ORDER BY gp.gameweek, t.team_name
            ''').fetchall()
        
        conn.close()
        
        # Transform data for Chart.js
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
        
        return jsonify({
            'teams': list(teams_data.values())
        })
    except Exception as e:
        logger.error(f"Error fetching cumulative points: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/league-positions')
def api_league_positions():
    """API endpoint for league position worm chart"""
    try:
        selected_teams = request.args.getlist('teams')
        
        conn = get_db_connection()
        
        if selected_teams:
            placeholders = ','.join('?' * len(selected_teams))
            query = f'''
                WITH ranked_teams AS (
                    SELECT 
                        t.entry_id,
                        t.team_name,
                        gp.gameweek,
                        SUM(gp.points) OVER (PARTITION BY t.entry_id ORDER BY gp.gameweek) as cumulative_points,
                        RANK() OVER (PARTITION BY gp.gameweek ORDER BY SUM(gp.points) OVER (PARTITION BY t.entry_id ORDER BY gp.gameweek) DESC) as position
                    FROM teams t
                    JOIN gameweek_points gp ON t.entry_id = gp.entry_id
                    WHERE t.entry_id IN ({placeholders})
                )
                SELECT * FROM ranked_teams ORDER BY gameweek, position
            '''
            rows = conn.execute(query, selected_teams).fetchall()
        else:
            rows = conn.execute('''
                WITH ranked_teams AS (
                    SELECT 
                        t.entry_id,
                        t.team_name,
                        gp.gameweek,
                        SUM(gp.points) OVER (PARTITION BY t.entry_id ORDER BY gp.gameweek) as cumulative_points,
                        RANK() OVER (PARTITION BY gp.gameweek ORDER BY SUM(gp.points) OVER (PARTITION BY t.entry_id ORDER BY gp.gameweek) DESC) as position
                    FROM teams t
                    JOIN gameweek_points gp ON t.entry_id = gp.entry_id
                )
                SELECT * FROM ranked_teams ORDER BY gameweek, position
            ''').fetchall()
        
        # Get chip usage
        if selected_teams:
            chip_query = f'''
                SELECT entry_id, gameweek, chip_name
                FROM chip_usage
                WHERE entry_id IN ({placeholders})
            '''
            chips = conn.execute(chip_query, selected_teams).fetchall()
        else:
            chips = conn.execute('''
                SELECT entry_id, gameweek, chip_name
                FROM chip_usage
            ''').fetchall()
        
        conn.close()
        
        # Transform data
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
        
        # Add chip markers
        for chip in chips:
            if chip['entry_id'] in teams_data:
                teams_data[chip['entry_id']]['chips'].append({
                    'gameweek': chip['gameweek'],
                    'chip': chip['chip_name']
                })
        
        return jsonify({
            'teams': list(teams_data.values())
        })
    except Exception as e:
        logger.error(f"Error fetching league positions: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/recent-transfers')
def api_recent_transfers():
    """API endpoint for recent transfers"""
    try:
        selected_teams = request.args.getlist('teams')
        
        conn = get_db_connection()
        
        # Get current gameweek
        current_gw = conn.execute(
            'SELECT id FROM gameweeks ORDER BY id DESC LIMIT 1'
        ).fetchone()
        
        if not current_gw:
            return jsonify({'transfers': []})
        
        if selected_teams:
            placeholders = ','.join('?' * len(selected_teams))
            query = f'''
                SELECT 
                    t.team_name,
                    tr.gameweek,
                    tr.transfers_in,
                    tr.transfers_out,
                    tr.transfer_count
                FROM teams t
                LEFT JOIN transfers tr ON t.entry_id = tr.entry_id AND tr.gameweek = ?
                WHERE t.entry_id IN ({placeholders})
                ORDER BY t.team_name
            '''
            params = [current_gw['id']] + selected_teams
            rows = conn.execute(query, params).fetchall()
        else:
            rows = conn.execute('''
                SELECT 
                    t.team_name,
                    tr.gameweek,
                    tr.transfers_in,
                    tr.transfers_out,
                    tr.transfer_count
                FROM teams t
                LEFT JOIN transfers tr ON t.entry_id = tr.entry_id AND tr.gameweek = ?
                ORDER BY t.team_name
            ''', [current_gw['id']]).fetchall()
        
        conn.close()
        
        transfers = []
        for row in rows:
            if row['transfer_count'] and row['transfer_count'] > 0:
                transfers.append({
                    'team_name': row['team_name'],
                    'transfers_in': row['transfers_in'].split(',') if row['transfers_in'] else [],
                    'transfers_out': row['transfers_out'].split(',') if row['transfers_out'] else [],
                    'count': row['transfer_count']
                })
            else:
                transfers.append({
                    'team_name': row['team_name'],
                    'transfers_in': [],
                    'transfers_out': [],
                    'count': 0
                })
        
        return jsonify({'transfers': transfers})
    except Exception as e:
        logger.error(f"Error fetching recent transfers: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats')
def api_stats():
    """API endpoint for league statistics"""
    try:
        conn = get_db_connection()
        
        # Most goals scored
        most_goals = conn.execute('''
            SELECT t.team_name, ps.total_goals
            FROM teams t
            JOIN player_stats ps ON t.entry_id = ps.entry_id
            ORDER BY ps.total_goals DESC
            LIMIT 1
        ''').fetchone()
        
        # Most clean sheets
        most_clean_sheets = conn.execute('''
            SELECT t.team_name, ps.total_clean_sheets
            FROM teams t
            JOIN player_stats ps ON t.entry_id = ps.entry_id
            ORDER BY ps.total_clean_sheets DESC
            LIMIT 1
        ''').fetchone()
        
        # Highest gameweek score
        highest_gw_score = conn.execute('''
            SELECT t.team_name, gp.gameweek, gp.points
            FROM teams t
            JOIN gameweek_points gp ON t.entry_id = gp.entry_id
            ORDER BY gp.points DESC
            LIMIT 1
        ''').fetchone()
        
        # Current leader
        current_leader = conn.execute('''
            SELECT 
                t.team_name,
                SUM(gp.points) as total_points
            FROM teams t
            JOIN gameweek_points gp ON t.entry_id = gp.entry_id
            GROUP BY t.entry_id
            ORDER BY total_points DESC
            LIMIT 1
        ''').fetchone()
        
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


@app.route('/api/refresh', methods=['POST'])
def api_refresh():
    """Manually trigger data refresh"""
    try:
        logger.info("Manual data refresh triggered")
        fpl_collector.collect_all_data()
        return jsonify({'status': 'success', 'message': 'Data refreshed successfully'})
    except Exception as e:
        logger.error(f"Error refreshing data: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', error='Page not found'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', error='Internal server error'), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
