#!/bin/bash
# Vantix Deployment Script
# Run this after pulling updates or making changes

set -e

echo "=================================="
echo "Vantix Deployment Script"
echo "=================================="
echo ""

# Check if we're in the right directory
if [ ! -f "config.py" ]; then
    echo "ERROR: Run this from the vantix root directory"
    exit 1
fi

# 1. Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found!"
    echo "   Copying .env.example to .env..."
    cp .env.example .env
    echo "   ✓ Please edit .env and set your SECRET_KEY and REFRESH_TOKEN"
    echo ""
fi

# 2. Check for leagues.json
if [ ! -f "leagues.json" ]; then
    echo "⚠️  No leagues.json found!"
    echo "   Copying leagues.json.example to leagues.json..."
    cp leagues.json.example leagues.json
    echo "   ✓ Please edit leagues.json with your league codes"
    echo ""
fi

# 3. Create necessary directories
echo "Creating directories..."
mkdir -p logs data
echo "✓ Directories created"
echo ""

# 4. Install/update dependencies
echo "Installing dependencies..."
if [ -d "venv" ]; then
    source venv/bin/activate
else
    python3 -m venv venv
    source venv/bin/activate
fi

pip install -r requirements.txt --quiet
echo "✓ Dependencies installed"
echo ""

# 5. Make scripts executable
if [ -d "scripts" ]; then
    chmod +x scripts/*.sh
    echo "✓ Scripts made executable"
    echo ""
fi

# 6. Initialize databases (if needed)
echo "Checking databases..."
python3 << EOF
import os
from data.database import init_db_for_league
import config

for league in config.LEAGUES:
    init_db_for_league(league['code'])
    print(f"  ✓ Database initialized for league {league['code']}")
EOF
echo ""

# 7. Test configuration
echo "Testing configuration..."
python3 << EOF
import config
print(f"  Leagues configured: {len(config.LEAGUES)}")
print(f"  Secret key set: {'Yes' if config.SECRET_KEY != 'dev-secret-key-change-in-production' else 'No (WARNING!)'}")
print(f"  Refresh token set: {'Yes' if config.REFRESH_TOKEN != 'change-me-in-production' else 'No (WARNING!)'}")
print(f"  Debug mode: {config.DEBUG}")
EOF
echo ""

# 8. Restart service if running
if systemctl is-active --quiet vantix; then
    echo "Restarting vantix service..."
    sudo systemctl restart vantix
    echo "✓ Service restarted"
    echo ""
fi

echo "=================================="
echo "Deployment Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Edit .env if you haven't already"
echo "2. Edit leagues.json with your league codes"
echo "3. Run: python collect_all_leagues.py"
echo "4. Setup cron: crontab -e"
echo "   Add: 0 3 * * 2 $PWD/scripts/cron_refresh.sh"
echo ""
