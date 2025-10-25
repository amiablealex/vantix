#!/bin/bash
# Vantix Scheduled Refresh Script
# Add to crontab: 0 3 * * 2 /home/pi/fpl-dashboard/scripts/cron_refresh.sh

set -e

# Change to app directory
cd /home/pi/fpl-dashboard

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Activate virtual environment
source venv/bin/activate

# Run refresh with token
python3 << EOF
import requests
import os
import sys

REFRESH_TOKEN = os.environ.get('REFRESH_TOKEN')
BASE_URL = 'http://localhost:8000'

if not REFRESH_TOKEN:
    print("ERROR: REFRESH_TOKEN not set in .env")
    sys.exit(1)

try:
    response = requests.post(
        f'{BASE_URL}/api/refresh-all',
        headers={'X-Refresh-Token': REFRESH_TOKEN},
        timeout=600  # 10 minute timeout
    )
    
    print(f"Status Code: {response.status_code}")
    print(response.json())
    
    if response.status_code == 200:
        sys.exit(0)
    else:
        sys.exit(1)
        
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
EOF

# Log completion
echo "$(date): Cron refresh completed" >> logs/cron.log
