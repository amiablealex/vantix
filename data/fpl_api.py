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
        self.league_code = league_id  # Store as league_code for clarity
        self.session = requests.Session()
        self.player_map = {}  # Cache for player ID to name mapping
        self.player_details = {}  # Cache for full player details
        self.current_season_start_gw = 1  # FPL seasons always start at GW1
        
    def _get_db_connection(self):
        """Get database connection for this league"""
        from data.database import get_league_connection
        return get_league_connection(self.league_code)
        
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
    
    def get_entry_event_live(self, entry_id, gameweek):
        """Fetch live data for a team in a specific gameweek (includes player points)"""
        url = f"{self.BASE_URL}/entry/{entry_id}/event/{gameweek}/picks/"
        return self._make_request(url)
    
    def get_entry_picks(self, entry_id, gameweek):
        """Alias for get_entry_event_live"""
        return self.get_entry_event_live(entry_id, gameweek)


    
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
        logger.info(f"Starting data collection for league {self.league_code}...")
        
        conn = self._get_db_connection()
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
                
                # Store in database for quick lookup
                cursor.execute('''
                    INSERT OR REPLACE INTO players (player_id, web_name, full_name, updated_at)
                    VALUES (?, ?, ?, ?)
                ''', (
                    player['id'],
                    player['web_name'],
                    player['first_name'] + ' ' + player['second_name'],
                    datetime.now()
                ))
            
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
                    
                    # Store cumulative player stats for this manager
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
                    
                    # Store current squad for differential analysis
                    try:
                        current_picks = self.get_entry_picks(entry_id, current_gw)
                        squad_player_ids = [pick['element'] for pick in current_picks['picks']]
                        all_squads[entry_id] = squad_player_ids
                        
                        # Store squad in database for filter-aware differentials
                        cursor.execute('''
                            INSERT OR REPLACE INTO current_squads
                            (entry_id, gameweek, player_ids, updated_at)
                            VALUES (?, ?, ?, ?)
                        ''', (
                            entry_id,
                            current_gw,
                            ','.join(map(str, squad_player_ids)),
                            datetime.now()
                        ))
                        
                    except Exception as e:
                        logger.warning(f"Could not fetch current picks for differential: {e}")
                    
                except Exception as e:
                    logger.error(f"Error collecting data for team {entry_id}: {e}")
                    continue
            
            # 4. Calculate differentials (players owned by ONLY this team, not by anyone else)
            if len(all_squads) > 0:
                logger.info("Calculating true differentials...")
                
                player_ownership = {}
                for squad in all_squads.values():
                    for player_id in squad:
                        player_ownership[player_id] = player_ownership.get(player_id, 0) + 1
                
                for entry_id, squad in all_squads.items():
                    true_differentials = []
                    for player_id in squad:
                        ownership_count = player_ownership.get(player_id, 0)
                        
                        # TRUE differential = only owned by this team (count == 1)
                        if ownership_count == 1:
                            player_name = self.player_map.get(player_id, 'Unknown')
                            true_differentials.append(player_name)
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO differentials
                        (entry_id, gameweek, differential_players, differential_count)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        entry_id,
                        current_gw,
                        ','.join(true_differentials) if true_differentials else '',
                        len(true_differentials)
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
    # Use first configured league for manual runs
    if not config.LEAGUES:
        print("No leagues configured in config.py")
        sys.exit(1)
    
    league_code = config.LEAGUES[0]['code']
    print(f"Collecting data for league {league_code}")
    
    collector = FPLDataCollector(team_id=None, league_id=league_code)
    collector.collect_all_data()
