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
    
    def collect_all_data(self):
        """Main method to collect all FPL data and store in database"""
        logger.info("Starting data collection...")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 1. Get bootstrap data for players and gameweeks
            logger.info("Fetching bootstrap data...")
            bootstrap = self.get_bootstrap_data()
            
            # Build player map
            for player in bootstrap['elements']:
                self.player_map[player['id']] = player['web_name']
            
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
                    
                    # Calculate player stats (goals, assists, clean sheets)
                    total_goals = 0
                    total_assists = 0
                    total_clean_sheets = 0
                    
                    # Get current gameweek for latest picks
                    current_gw = max([gw['event'] for gw in history['current']]) if history['current'] else 1
                    
                    for gw in range(1, current_gw + 1):
                        try:
                            picks = self.get_entry_picks(entry_id, gw)
                            for pick in picks['picks']:
                                player_id = pick['element']
                                # Find player in bootstrap data
                                for player in bootstrap['elements']:
                                    if player['id'] == player_id:
                                        total_goals += player.get('goals_scored', 0)
                                        total_assists += player.get('assists', 0)
                                        total_clean_sheets += player.get('clean_sheets', 0)
                                        break
                        except Exception as e:
                            logger.warning(f"Could not fetch picks for GW {gw}: {e}")
                            continue
                    
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
