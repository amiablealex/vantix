"""
Vantix Configuration
Update these values with your FPL details
"""

# FPL API Configuration
FPL_TEAM_ID = 5699556  # Your FPL Team ID (entry ID)
FPL_LEAGUE_ID = 1507022  # Your Classic League ID

# League display name (will be fetched from API but can be overridden here)
LEAGUE_NAME = "Code vs Coach"

# Data refresh schedule (cron format: minute hour day month day_of_week)
# Default: Every Tuesday at 3:00 AM (after GW deadline typically passes)
REFRESH_SCHEDULE = {
    'hour': 3,
    'minute': 0,
    'day_of_week': 'tue'
}

# Application settings
SECRET_KEY = 'your-secret-key-change-this-in-production'
DATABASE_PATH = 'data/fpl_dashboard.db'

# API Rate Limiting
API_RATE_LIMIT_DELAY = 1  # Seconds between API calls

# Logging
LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/vantix.log'
