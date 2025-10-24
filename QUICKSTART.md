# Vantix Quick Start Guide

Get your FPL dashboard running in 5 minutes!

## Prerequisites
- Raspberry Pi 4 with Raspberry Pi OS
- Internet connection
- Your FPL Team ID and League ID

## Finding Your FPL IDs

### Team ID
1. Go to https://fantasy.premierleague.com
2. Click on "Points" or "Gameweek history"
3. Look at the URL: `.../entry/YOUR_TEAM_ID/...`
4. Your Team ID is the number in the URL

### League ID
1. Go to your league page
2. Look at the URL: `.../leagues-classic/YOUR_LEAGUE_ID/...`
3. Your League ID is the number in the URL

## Installation (5 Steps)

### 1. Download Vantix
```bash
cd ~
# If you have git:
git clone <repository-url> fpl-dashboard

# Or download and extract the zip file
cd fpl-dashboard
```

### 2. Run Setup Script
```bash
chmod +x setup.sh
./setup.sh
```

The script will:
- Create a Python virtual environment
- Install all dependencies
- Initialize the database
- Ask for your FPL Team ID and League ID
- Collect initial data (takes 2-3 minutes)
- Start a test server

### 3. Test Locally
Visit http://localhost:5000 in your browser to verify everything works!

Press Ctrl+C to stop the test server.

### 4. Configure for Production

#### Setup Nginx
```bash
# Install Nginx
sudo apt update
sudo apt install nginx -y

# Copy and edit config
sudo cp nginx/vantix.conf /etc/nginx/sites-available/vantix
sudo nano /etc/nginx/sites-available/vantix

# Replace 'your-domain.com' with your actual domain (in two places)
# Save with Ctrl+X, then Y, then Enter

# Enable the site
sudo ln -s /etc/nginx/sites-available/vantix /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### Setup Systemd Service
```bash
# Copy service file
sudo cp systemd/vantix.service /etc/systemd/system/

# If you're not using 'pi' user or different path, edit the file:
# sudo nano /etc/systemd/system/vantix.service

# Start and enable service
sudo systemctl daemon-reload
sudo systemctl start vantix
sudo systemctl enable vantix

# Check status
sudo systemctl status vantix
```

### 5. Setup SSL (Optional but Recommended)
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate (replace with your domain)
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Follow the prompts
```

## That's It! 🎉

Your dashboard is now running at:
- **HTTP**: http://yourdomain.com
- **HTTPS**: https://yourdomain.com (if SSL is configured)

## Common Commands

### View Logs
```bash
# Application errors
tail -f ~/fpl-dashboard/logs/error.log

# Service status
sudo systemctl status vantix

# Nginx errors
sudo tail -f /var/log/nginx/vantix_error.log
```

### Restart Services
```bash
# Restart Vantix
sudo systemctl restart vantix

# Restart Nginx
sudo systemctl restart nginx
```

### Update Data Manually
```bash
cd ~/fpl-dashboard
source venv/bin/activate
python data/fpl_api.py
```

### Inspect Database
```bash
cd ~/fpl-dashboard
source venv/bin/activate
python inspect_db.py
```

## Troubleshooting

### Dashboard shows no data
1. Check if data collection completed:
   ```bash
   python inspect_db.py
   ```
2. If no data, run collection again:
   ```bash
   python data/fpl_api.py
   ```

### Can't access via domain
1. Verify Nginx is running:
   ```bash
   sudo systemctl status nginx
   ```
2. Check if Vantix service is running:
   ```bash
   sudo systemctl status vantix
   ```
3. Verify DNS points to your Pi's IP address

### 502 Bad Gateway
1. Check Gunicorn is running:
   ```bash
   sudo systemctl status vantix
   ```
2. Restart the service:
   ```bash
   sudo systemctl restart vantix
   ```

## Configuration

### Change Update Schedule
Edit `config.py`:
```python
REFRESH_SCHEDULE = {
    'hour': 3,              # 3 AM
    'minute': 0,
    'day_of_week': 'tue'    # Tuesday
}
```

Available days: mon, tue, wed, thu, fri, sat, sun

Restart after changes:
```bash
sudo systemctl restart vantix
```

## Features Overview

- **📊 Cumulative Points Chart**: Track everyone's points progression
- **📈 League Position Worm**: See rank changes over time with chip markers
- **🔄 Recent Transfers**: View latest squad changes
- **📊 Stats Cards**: Goals, clean sheets, highest scores, current leader
- **🎯 Team Filtering**: Select specific teams to compare
- **↻ Manual Refresh**: Click the button to update data on demand

## Need Help?

1. Check `README.md` for detailed documentation
2. Review `DEPLOYMENT_CHECKLIST.md` for step-by-step deployment
3. Use `inspect_db.py` to check database contents
4. Check logs for error messages

## Performance Tips

- Pi 4 with 2GB+ RAM recommended
- Schedule updates during off-peak hours (3 AM)
- Use SSD storage for better performance
- Keep browser cache cleared for best experience

---

**Enjoy tracking your FPL league with Vantix! 🏆**
