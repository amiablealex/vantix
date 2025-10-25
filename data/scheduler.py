"""
Scheduler module - DISABLED
APScheduler has been replaced with cron for scheduled updates
This file is kept for compatibility but does nothing
"""

import logging

logger = logging.getLogger(__name__)


def init_scheduler(app):
    """
    Scheduler initialization - DISABLED
    
    Scheduled refreshes are now handled by cron.
    See scripts/cron_refresh.sh for the refresh script.
    
    To setup cron:
    1. Make script executable: chmod +x scripts/cron_refresh.sh
    2. Add to crontab: crontab -e
    3. Add line: 0 3 * * 2 /path/to/fpl-dashboard/scripts/cron_refresh.sh
    """
    logger.info("APScheduler disabled - using cron for scheduled refreshes")
    return None
