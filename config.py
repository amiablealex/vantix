import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Application Configuration
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
FLASK_ENV = os.environ.get('FLASK_ENV', 'production')

# Refresh Token for Protected Endpoints
REFRESH_TOKEN = os.environ.get('REFRESH_TOKEN', 'change-me-in-production')

# Load leagues from leagues.json
LEAGUES_FILE = os.path.join(os.path.dirname(__file__), 'leagues.json')

def load_leagues():
    """Load leagues from leagues.json file"""
    if os.path.exists(LEAGUES_FILE):
        with open(LEAGUES_FILE, 'r') as f:
            return json.load(f)
    else:
        # Fallback to empty list if file doesn't exist
        print(f"WARNING: {LEAGUES_FILE} not found. No leagues configured.")
        return []

LEAGUES = load_leagues()

# Data refresh schedule (for cron reference)
REFRESH_SCHEDULE = {
    'hour': int(os.environ.get('REFRESH_HOUR', 3)),
    'minute': int(os.environ.get('REFRESH_MINUTE', 0)),
    'day_of_week': os.environ.get('REFRESH_DAY_OF_WEEK', 'tue')
}

# FPL API Configuration
API_RATE_LIMIT_DELAY = float(os.environ.get('API_RATE_LIMIT_DELAY', 0.5))
FPL_TEAM_ID = None  # Not needed for multi-league

# Database Configuration
DATABASE_PATH = os.path.join(
    os.path.dirname(__file__), 
    os.environ.get('DATABASE_PATH', 'data/fpl_data.db')
)

# Logging Configuration
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
LOG_FILE = os.path.join(
    os.path.dirname(__file__), 
    os.environ.get('LOG_FILE', 'logs/app.log')
)

# Caching Configuration
CACHE_TYPE = 'SimpleCache'
CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes
CACHE_THRESHOLD = 100  # Max items in cache

# Rate Limiting Configuration
RATELIMIT_ENABLED = True
RATELIMIT_STORAGE_URL = "memory://"
RATELIMIT_STRATEGY = "fixed-window"
RATELIMIT_DEFAULT = "30 per minute"  # Default for all routes
RATELIMIT_HEADERS_ENABLED = True
