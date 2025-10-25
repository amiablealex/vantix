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


def get_current_gameweek():
    """Get the current active gameweek"""
    conn = get_db_connection()
    # Find first unfinished gameweek
    current = conn.execute(
        'SELECT id FROM gameweeks WHERE finished = 0 ORDER BY id LIMIT 1'
    ).fetchone()
    
    if not current:
        # All finished, get last gameweek
        current = conn.execute(
            'SELECT id FROM gameweeks ORDER BY id DESC LIMIT 1'
        ).fetchone()
    
    conn.close()
    return current['id'] if current else 1


def get_last_completed_gameweek():
    """Get the last completed (finished) gameweek"""
    conn = get_db_connection()
    last_completed = conn.execute(
        'SELECT MAX(id) as max_gw FROM gameweeks WHERE finished = 1'
    ).fetchone()
    conn.close()
    return last_completed['max_gw'] if last_completed and last_completed['max_gw'] else 1


def get_season_string():
    """Get current FPL season string (e.g., '2024/25')"""
    now = datetime.now()
    if now.month >= 8:  # Season starts in August
        return f"{now.year}/{str(now.year + 1)[-2:]}"
    else:
        return f"{now.year - 1}/{str(now.year)[-2:]}"


@app.route('/')
def index():
    """Main dashboard view"""
    try:
        conn = get_db_connection()
        
        # Get current gameweek
        current_gw = get_current_gameweek()
        
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
            current_gameweek=current_gw,
            season=get_season_string(),
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
        last_completed_gw = get_last_completed_gameweek()
        
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
        last_completed_gw = get_last_completed_gameweek()
        
        conn = get_db_connection()
        
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
        
        # Get chip usage
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
        current_gw = get_current_gameweek()
        
        conn = get_db_connection()
        
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
            params = [current_gw] + selected_teams
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
            ''', [current_gw]).fetchall()
        
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
        
        return jsonify({'transfers': transfers, 'gameweek': current_gw})
    except Exception as e:
        logger.error(f"Error fetching recent transfers: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats')
def api_stats():
    """API endpoint for league statistics - NOW FILTERED BY SELECTED TEAMS"""
    try:
        selected_teams = request.args.getlist('teams')
        conn = get_db_connection()
        
        # Build WHERE clause for filtering
        where_clause = ""
        params = []
        if selected_teams:
            placeholders = ','.join('?' * len(selected_teams))
            where_clause = f"WHERE t.entry_id IN ({placeholders})"
            params = selected_teams
        
        # Most goals scored
        most_goals = conn.execute(f'''
            SELECT t.team_name, ps.total_goals
            FROM teams t
            JOIN player_stats ps ON t.entry_id = ps.entry_id
            {where_clause}
            ORDER BY ps.total_goals DESC
            LIMIT 1
        ''', params).fetchone()
        
        # Most clean sheets
        most_clean_sheets = conn.execute(f'''
            SELECT t.team_name, ps.total_clean_sheets
            FROM teams t
            JOIN player_stats ps ON t.entry_id = ps.entry_id
            {where_clause}
            ORDER BY ps.total_clean_sheets DESC
            LIMIT 1
        ''', params).fetchone()
        
        # Highest gameweek score
        highest_gw_score = conn.execute(f'''
            SELECT t.team_name, gp.gameweek, gp.points
            FROM teams t
            JOIN gameweek_points gp ON t.entry_id = gp.entry_id
            {where_clause}
            ORDER BY gp.points DESC
            LIMIT 1
        ''', params).fetchone()
        
        # Current leader
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


@app.route('/api/form-chart')
def api_form_chart():
    """API endpoint for recent form (last 5 gameweeks)"""
    try:
        # Get the last completed gameweek
        conn = get_db_connection()
        last_completed = conn.execute('''
            SELECT MAX(id) as max_gw
            FROM gameweeks
            WHERE finished = 1
        ''').fetchone()
        
        if not last_completed or not last_completed['max_gw']:
            conn.close()
            return jsonify({'teams': []})
        
        end_gw = last_completed['max_gw']
        start_gw = max(1, end_gw - 4)  # Last 5 completed gameweeks
        
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
        
        # Transform data
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
        
        return jsonify({
            'teams': list(teams_data.values())
        })
    except Exception as e:
        logger.error(f"Error fetching form chart: {e}")
        return jsonify({'error': str(e), 'teams': []}), 500


@app.route('/api/points-distribution')
def api_points_distribution():
    """API endpoint for points distribution across all gameweeks"""
    try:
        selected_teams = request.args.getlist('teams')
        
        conn = get_db_connection()
        
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
        
        # Create histogram bins
        points_list = [row['points'] for row in rows]
        
        if not points_list:
            return jsonify({'bins': [], 'counts': []})
        
        # Create bins (0-20, 20-40, 40-60, 60-80, 80-100, 100+)
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


@app.route('/api/team-comparison')
def api_team_comparison():
    """API endpoint for detailed team comparison stats"""
    try:
        selected_teams = request.args.getlist('teams')
        
        if not selected_teams:
            return jsonify({'teams': []})
        
        conn = get_db_connection()
        
        comparison_data = []
        
        for team_id in selected_teams:
            # Get basic stats
            team_info = conn.execute('''
                SELECT t.team_name, t.manager_name
                FROM teams t
                WHERE t.entry_id = ?
            ''', [team_id]).fetchone()
            
            if not team_info:
                continue
            
            # Total points
            total_points = conn.execute('''
                SELECT SUM(points) as total
                FROM gameweek_points
                WHERE entry_id = ?
            ''', [team_id]).fetchone()
            
            # Average points per GW
            avg_points = conn.execute('''
                SELECT AVG(points) as avg
                FROM gameweek_points
                WHERE entry_id = ?
            ''', [team_id]).fetchone()
            
            # Highest GW score
            highest_gw = conn.execute('''
                SELECT MAX(points) as highest
                FROM gameweek_points
                WHERE entry_id = ?
            ''', [team_id]).fetchone()
            
            # Lowest GW score
            lowest_gw = conn.execute('''
                SELECT MIN(points) as lowest
                FROM gameweek_points
                WHERE entry_id = ?
            ''', [team_id]).fetchone()
            
            # Total transfers
            total_transfers = conn.execute('''
                SELECT SUM(transfer_count) as total
                FROM transfers
                WHERE entry_id = ?
            ''', [team_id]).fetchone()
            
            # Chips used
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
                'chips_used': chips_used['count'] if chips_used['count'] else 0
            })
        
        conn.close()
        
        return jsonify({'teams': comparison_data})
    except Exception as e:
        logger.error(f"Error fetching team comparison: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/biggest-movers')
def api_biggest_movers():
    """API endpoint for biggest position changes in last 5 GWs"""
    try:
        current_gw = get_current_gameweek()
        past_gw = max(1, current_gw - 5)
        
        selected_teams = request.args.getlist('teams')
        
        conn = get_db_connection()
        
        # Get rankings for past_gw and current_gw
        if selected_teams:
            placeholders = ','.join('?' * len(selected_teams))
            query = f'''
                WITH past_rankings AS (
                    SELECT 
                        t.entry_id,
                        t.team_name,
                        SUM(gp.points) OVER (PARTITION BY t.entry_id ORDER BY gp.gameweek) as total_points,
                        RANK() OVER (ORDER BY SUM(gp.points) OVER (PARTITION BY t.entry_id ORDER BY gp.gameweek) DESC) as rank
                    FROM teams t
                    JOIN gameweek_points gp ON t.entry_id = gp.entry_id
                    WHERE gp.gameweek <= ? AND t.entry_id IN ({placeholders})
                ),
                current_rankings AS (
                    SELECT 
                        t.entry_id,
                        t.team_name,
                        SUM(gp.points) as total_points,
                        RANK() OVER (ORDER BY SUM(gp.points) DESC) as rank
                    FROM teams t
                    JOIN gameweek_points gp ON t.entry_id = gp.entry_id
                    WHERE t.entry_id IN ({placeholders})
                    GROUP BY t.entry_id
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
            params = [past_gw] + selected_teams + selected_teams
            rows = conn.execute(query, params).fetchall()
        else:
            rows = conn.execute('''
                WITH past_rankings AS (
                    SELECT 
                        t.entry_id,
                        t.team_name,
                        SUM(gp.points) OVER (PARTITION BY t.entry_id ORDER BY gp.gameweek) as total_points,
                        RANK() OVER (ORDER BY SUM(gp.points) OVER (PARTITION BY t.entry_id ORDER BY gp.gameweek) DESC) as rank
                    FROM teams t
                    JOIN gameweek_points gp ON t.entry_id = gp.entry_id
                    WHERE gp.gameweek <= ?
                ),
                current_rankings AS (
                    SELECT 
                        t.entry_id,
                        t.team_name,
                        SUM(gp.points) as total_points,
                        RANK() OVER (ORDER BY SUM(gp.points) DESC) as rank
                    FROM teams t
                    JOIN gameweek_points gp ON t.entry_id = gp.entry_id
                    GROUP BY t.entry_id
                )
                SELECT 
                    c.team_name,
                    c.rank as current_rank,
                    p.rank as past_rank,
                    (p.rank - c.rank) as change
                FROM current_rankings c
                LEFT JOIN past_rankings p ON c.entry_id = p.entry_id
                ORDER BY change DESC
            ''', [past_gw]).fetchall()
        
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
            'climbers': climbers[:5],  # Top 5 climbers
            'fallers': fallers[:5]  # Top 5 fallers
        })
    except Exception as e:
        logger.error(f"Error fetching biggest movers: {e}")
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
