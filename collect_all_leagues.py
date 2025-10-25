#!/usr/bin/env python3
"""
Collect FPL data for all configured leagues
Run this script to update data for all leagues at once
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
import logging
from data.fpl_api import FPLDataCollector

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def collect_league_data(league_code, league_name):
    """Collect data for a single league"""
    try:
        logger.info(f"\n{'='*70}")
        logger.info(f"Collecting data for: {league_name} (Code: {league_code})")
        logger.info(f"{'='*70}\n")
        
        collector = FPLDataCollector(team_id=None, league_id=league_code)
        collector.collect_all_data()
        
        logger.info(f"\n✅ Successfully collected data for {league_name}")
        return True
        
    except Exception as e:
        logger.error(f"\n❌ Failed to collect data for {league_name}: {e}")
        return False


def main():
    """Collect data for all configured leagues"""
    if not config.LEAGUES:
        logger.error("No leagues configured in config.py!")
        logger.error("Please add leagues to the LEAGUES list in config.py")
        return 1
    
    logger.info(f"\n{'='*70}")
    logger.info(f"Multi-League Data Collection")
    logger.info(f"Total leagues: {len(config.LEAGUES)}")
    logger.info(f"{'='*70}")
    
    success_count = 0
    failed_count = 0
    
    for league in config.LEAGUES:
        league_code = league['code']
        league_name = league['name']
        
        if collect_league_data(league_code, league_name):
            success_count += 1
        else:
            failed_count += 1
    
    # Summary
    logger.info(f"\n{'='*70}")
    logger.info(f"Data Collection Complete")
    logger.info(f"{'='*70}")
    logger.info(f"✅ Successful: {success_count}/{len(config.LEAGUES)}")
    logger.info(f"❌ Failed: {failed_count}/{len(config.LEAGUES)}")
    logger.info(f"{'='*70}\n")
    
    return 0 if failed_count == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
