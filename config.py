import os

# Application Configuration
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# Multiple League Support - Add your leagues here
LEAGUES = [
    {
        'code': 1507022,  # Replace with your first league code
        'name': 'Code vs Coach',
        'description': 'My primary FPL league'
    },
    {
        'code': 307899,  # Replace with your first league code
        'name': 'The Dandy Lions',
        'description': 'My secondary FPL league'
    },
    {
        'code': 1049424,  # Replace with your first league code
        'name': 'Cals Pals',
        'description': 'My tertiary FPL league'
    },
    # Add more leagues as needed:
    # {
    #     'code': 456789,
    #     'name': 'Work League', 
    #     'description': 'Office competition'
    # },
]

# Data refresh schedule (cron format: minute hour day month day_of_week)
# Default: Every Tuesday at 3:00 AM (after GW deadline typically passes)
REFRESH_SCHEDULE = {
    'hour': 3,
    'minute': 0,
    'day_of_week': 'tue'
}

# FPL API Configuration
API_RATE_LIMIT_DELAY = 0.5  # Delay between API requests in seconds
FPL_TEAM_ID = None  # Not needed for multi-league, kept for compatibility

# Database Configuration
DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'fpl_data.db')

# Logging Configuration
LOG_LEVEL = 'INFO'
LOG_FILE = os.path.join(os.path.dirname(__file__), 'logs', 'app.log')
