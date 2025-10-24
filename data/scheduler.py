"""
APScheduler configuration for automated data updates
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
import config
from data.fpl_api import FPLDataCollector

logger = logging.getLogger(__name__)


def scheduled_data_update():
    """Function to run on schedule to update FPL data"""
    logger.info("Running scheduled data update...")
    try:
        collector = FPLDataCollector(
            team_id=config.FPL_TEAM_ID,
            league_id=config.FPL_LEAGUE_ID
        )
        collector.collect_all_data()
        logger.info("Scheduled data update completed successfully")
    except Exception as e:
        logger.error(f"Scheduled data update failed: {e}")


def init_scheduler(app):
    """Initialize and configure the scheduler"""
    scheduler = BackgroundScheduler()
    
    # Add job based on config
    trigger = CronTrigger(
        hour=config.REFRESH_SCHEDULE['hour'],
        minute=config.REFRESH_SCHEDULE['minute'],
        day_of_week=config.REFRESH_SCHEDULE['day_of_week']
    )
    
    scheduler.add_job(
        func=scheduled_data_update,
        trigger=trigger,
        id='data_update',
        name='FPL Data Update',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info(f"Scheduler started. Data updates scheduled for: {config.REFRESH_SCHEDULE}")
    
    # Shutdown scheduler when app stops
    import atexit
    atexit.register(lambda: scheduler.shutdown())
    
    return scheduler


if __name__ == '__main__':
    # Test scheduler
    from flask import Flask
    app = Flask(__name__)
    init_scheduler(app)
    
    # Keep running
    import time
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        pass
