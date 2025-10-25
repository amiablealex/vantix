"""
FPL API Wrapper and Data Collection
"""

import requests
import time
import logging
from datetime import datetime
import config
from data.database import get_db_connection

logger = logging.getLogger(__name__)


class FPLDataCollector:
    """Handles all FPL API interactions and data collection"""
    
    BASE_URL = "https://fantasy.premierleague.com/api"
    
    def __init__(self, team_id, league_id):
        self.team_id = team_id
        self.league_id = league_id
        self.session = requests.Session()
        self.player_map = {}  # Cache for player ID to name mapping
        self.player_details = {}  # Cache for full player details
        self.current_season_start_gw = 1  # FPL seasons always start at GW1
        
    def _make_request(self, url):
        """Make API request with rate limiting and error handling"""
        try:
            time.sleep(config.API_RATE_LIMIT_DELAY)
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for {url}: {e}")
            raise
    
    def get_bootstrap_data(self):
        """Fetch bootstrap-static data (players, teams, gameweeks)"""
        url = f"{self.BASE_URL}/bootstrap-static/"
        return self._make_request(url)
    
    def get_league_standings(self):
        """Fetch classic league standings"""
        url = f"{self.BASE_URL}/leagues-classic/{self.league_id}/standings/"
        return self._make_request(url)
    
    def get_entry_history(self, entry_id):
        """Fetch team's gameweek history"""
        url = f"{self.BASE_URL}/entry/{entry_id}/history/"
        return self._make_request(url)
    
    def get_entry_picks(self, entry_id, gameweek):
        """Fetch team's picks for a specific gameweek"""
        url = f"{self.BASE_URL}/entry/{entry_id}/event/{gameweek}/picks/"
        return self._make_request(url)
    
    def get_entry_transfers(self, entry_id):
        """Fetch team's transfer history"""
        url = f"{self.BASE_URL}/entry/{entry_id}/transfers/"
        return self._make_request(url)
    
    def get_current_gameweek(self, bootstrap):
        """Determine the current active gameweek"""
        events = bootstrap['events']
        
        # Find the first gameweek that is either in progress or not finished
        for event in events:
            if not event['finished']:
                return event['id']
        
        # If all gameweeks are finished, return the last one
        return events[-1]['id'] if events else 1
    
    def collect_all_data(self):
        """Main method to collect all FPL data and store in database"""
        logger.info("Starting data collection...")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 1. Get bootstrap data for players and gameweeks
            logger.info("Fetching bootstrap data...")
            bootstrap = self.get_bootstrap_data()
            
            # Determine current gameweek
            current_gw = self.get_current_gameweek(bootstrap)
            logger.info(f"Current gameweek: {current_gw}")
            
            # Build player maps with full details
            for player in bootstrap['elements']:
                self.player_map[player['id']] = player['web_name']
                self.player_details[player['id']] = {
                    'name': player['web_name'],
                    'position': player['element_type'],  # 1=GK, 2=DEF, 3=MID, 4=FWD
                    'team': player['team']
                }
            
            # Store gameweeks
            for event in bootstrap['events']:
                cursor.execute('''
                    INSERT OR REPLACE INTO gameweeks (id, deadline, finished)
                    VALUES (?, ?, ?)
                ''', (event['id'], event['deadline_time'], event['finished']))
            
            logger.info(f"Stored {len(bootstrap['events'])} gameweeks")
            
            # 2. Get league standings and teams
            logger.info("Fetching league standings...")
            league_data = self.get_league_standings()
            
            teams = league_data['standings']['results']
            
            for team in teams:
                cursor.execute('''
                    INSERT OR REPLACE INTO teams (entry_id, team_name, manager_name)
                    VALUES (?, ?, ?)
                ''', (
                    team['entry'],
                    team['entry_name'],
                    team['player_name']
                ))
            
            logger.info(f"Stored {len(teams)} teams")
            
            # Collect all squads for differential analysis
            all_squads = {}
            
            # 3. Get detailed history for each team
            for team in teams:
                entry_id = team['entry']
                logger.info(f"Fetching data for team: {team['entry_name']}")
                
                try:
                    # Get team history
                    history = self.get_entry_history(entry_id)
                    
                    # Store gameweek points
                    for gw in history['current']:
                        cursor.execute('''
                            INSERT OR REPLACE INTO gameweek_points 
                            (entry_id, gameweek, points, total_points, rank, bank, value, 
                             event_transfers, event_transfers_cost, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            entry_id,
                            gw['event'],
                            gw['points'],
                            gw['total_points'],
                            gw['rank'],
                            gw['bank'] / 10,  # Convert to actual value
                            gw['value'] / 10,
                            gw['event_transfers'],
                            gw['event_transfers_cost'],
                            datetime.now()
                        ))
                    
                    # Store chip usage
                    for chip in history.get('chips', []):
                        cursor.execute('''
                            INSERT OR IGNORE INTO chip_usage (entry_id, gameweek, chip_name)
                            VALUES (?, ?, ?)
                        ''', (entry_id, chip['event'], chip['name']))
                    
                    # Get transfers
                    transfers_data = self.get_entry_transfers(entry_id)
                    
                    # Group transfers by gameweek
                    transfers_by_gw = {}
                    for transfer in transfers_data:
                        gw = transfer['event']
                        if gw not in transfers_by_gw:
                            transfers_by_gw[gw] = {
                                'in': [],
                                'out': [],
                                'count': 0
                            }
                        
                        player_in = self.player_map.get(transfer['element_in'], 'Unknown')
                        player_out = self.player_map.get(transfer['element_out'], 'Unknown')
                        
                        transfers_by_gw[gw]['in'].append(player_in)
                        transfers_by_gw[gw]['out'].append(player_out)
                        transfers_by_gw[gw]['count'] += 1
                    
                    # Store transfers
                    for gw, data in transfers_by_gw.items():
                        cursor.execute('''
                            INSERT OR REPLACE INTO transfers 
                            (entry_id, gameweek, transfer_count, transfers_in, transfers_out)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (
                            entry_id,
                            gw,
                            data['count'],
                            ','.join(data['in']),
                            ','.join(data['out'])
                        ))
                    
                    # NEW: Collect captain and position data for each completed gameweek
                    for gw in history['current']:
                        gameweek_num = gw['event']
                        
                        # Check if gameweek is finished
                        is_finished = cursor.execute(
                            'SELECT finished FROM gameweeks WHERE id = ?',
                            [gameweek_num]
                        ).fetchone()
                        
                        if is_finished and is_finished['finished']:
                            try:
                                picks_data = self.get_entry_picks(entry_id, gameweek_num)
                                
                                # Track captain and position points
                                captain_id = None
                                captain_name = None
                                captain_points = 0
                                position_points = {'GK': 0, 'DEF': 0, 'MID': 0, 'FWD': 0}
                                position_map = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}
                                
                                for pick in picks_data['picks']:
                                    player_id = pick['element']
                                    multiplier = pick['multiplier']
                                    
                                    # Get player details
                                    player_info = self.player_details.get(player_id, {})
                                    position_type = player_info.get('position', 2)
                                    position = position_map.get(position_type, 'DEF')
                                    
                                    # Points for this player (multiplier already applied in pick)
                                    player_points = multiplier * pick.get('points', 0) if 'points' in pick else 0
                                    
                                    # Track captain
                                    if pick['is_captain']:
                                        captain_id = player_id
                                        captain_name = player_info.get('name', 'Unknown')
                                        captain_points = player_points
                                    
                                    # Add to position totals
                                    position_points[position] += player_points
                                
                                # Store captain choice
                                if captain_id:
                                    cursor.execute('''
                                        INSERT OR REPLACE INTO captain_choices
                                        (entry_id, gameweek, player_id, player_name, captain_points)
                                        VALUES (?, ?, ?, ?, ?)
                                    ''', (entry_id, gameweek_num, captain_id, captain_name, captain_points))
                                
                                # Store position breakdown
                                cursor.execute('''
                                    INSERT OR REPLACE INTO position_points
                                    (entry_id, gameweek, gk_points, def_points, mid_points, fwd_points)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                ''', (
                                    entry_id, gameweek_num,
                                    position_points['GK'],
                                    position_points['DEF'],
                                    position_points['MID'],
                                    position_points['FWD']
                                ))
                                
                            except Exception as e:
                                logger.warning(f"Could not fetch picks for GW{gameweek_num}: {e}")
                    
                    # Store current squad for differential analysis
                    try:
                        current_picks = self.get_entry_picks(entry_id, current_gw)
                        all_squads[entry_id] = [pick['element'] for pick in current_picks['picks']]
                    except Exception as e:
                        logger.warning(f"Could not fetch current picks for differential: {e}")
                    
                    # Calculate cumulative player stats for this manager
                    total_goals = 0
                    total_assists = 0
                    total_clean_sheets = 0
                    
                    try:
                        picks = self.get_entry_picks(entry_id, current_gw)
                        for pick in picks['picks']:
                            player_id = pick['element']
                            # Get player from bootstrap data
                            player = next((p for p in bootstrap['elements'] if p['id'] == player_id), None)
                            if player:
                                total_goals += player.get('goals_scored', 0)
                                total_assists += player.get('assists', 0)
                                total_clean_sheets += player.get('clean_sheets', 0)
                    except Exception as e:
                        logger.warning(f"Could not calculate player stats: {e}")
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO player_stats 
                        (entry_id, total_goals, total_assists, total_clean_sheets, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        entry_id,
                        total_goals,
                        total_assists,
                        total_clean_sheets,
                        datetime.now()
                    ))
                    
                except Exception as e:
                    logger.error(f"Error collecting data for team {entry_id}: {e}")
                    continue
            
            # 4. Calculate differentials (players owned by <50% of league)
            if len(all_squads) > 0:
                logger.info("Calculating differentials...")
                
                player_ownership = {}
                for squad in all_squads.values():
                    for player_id in squad:
                        player_ownership[player_id] = player_ownership.get(player_id, 0) + 1
                
                total_teams = len(all_squads)
                
                for entry_id, squad in all_squads.items():
                    differentials = []
                    for player_id in squad:
                        ownership_count = player_ownership.get(player_id, 0)
                        ownership_pct = (ownership_count / total_teams) * 100
                        
                        if ownership_pct < 50:  # Differential = owned by less than 50%
                            player_name = self.player_map.get(player_id, 'Unknown')
                            differentials.append(f"{player_name} ({ownership_pct:.0f}%)")
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO differentials
                        (entry_id, gameweek, differential_players, differential_count)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        entry_id,
                        current_gw,
                        ','.join(differentials) if differentials else '',
                        len(differentials)
                    ))
            
            conn.commit()
            logger.info("Data collection completed successfully!")
            
        except Exception as e:
            logger.error(f"Data collection failed: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()


if __name__ == '__main__':
    # Test data collection
    collector = FPLDataCollector(
        team_id=config.FPL_TEAM_ID,
        league_id=config.FPL_LEAGUE_ID
    )
    collector.collect_all_data()
