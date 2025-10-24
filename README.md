# Vantix - Fantasy Premier League Dashboard

A beautiful, lightweight FPL league dashboard optimized for Raspberry Pi 4, featuring real-time statistics, interactive charts, and automated data updates.

![Vantix Dashboard](https://via.placeholder.com/800x400/FAF8F3/3A3A3A?text=Vantix+Dashboard)

## Features

- 📊 **Interactive Charts**: Cumulative points and league position tracking with Chart.js
- 🎨 **Beautiful Design**: Creamy pastel theme with professional typography
- 📱 **Responsive Layout**: Optimized for tablet, mobile, and desktop with containerized app layout
- 🔄 **Automated Updates**: Scheduled data collection after each gameweek
- ⚡ **Lightweight**: Minimal API calls with SQLite caching
- 🎯 **Team Filtering**: Select specific teams to compare on charts
- 📈 **Rich Statistics**: Goals, clean sheets, highest scores, and more
- 🔀 **Transfer Tracking**: View recent squad changes by gameweek
- 💎 **Chip Markers**: Visualize chip usage on position charts

## Prerequisites

- Raspberry Pi 4 (or any Linux server)
- Python 3.8 or higher
- Nginx
- Domain name pointing to your Pi's IP address

## Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
cd ~
git clone <your-repo-url> fpl-dashboard
cd fpl-dashboard

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Your FPL Details

Edit `config.py` and update with your information:

```python
FPL_TEAM_ID = 123456      # Your FPL Team ID
FPL_LEAGUE_ID = 123456    # Your Classic League ID
LEAGUE_NAME = "My League" # League display name (optional)
```

**Finding Your IDs:**
- **Team ID**: Go to https://fantasy.premierleague.com/entry/YOUR_TEAM_ID/history - the number in the URL
- **League ID**: Visit your league page, the number in the URL after `/leagues-classic/`

### 3. Initialize Database and Collect Data

```bash
# Create database tables
python data/database.py

# Collect initial FPL data (this may take 2-3 minutes)
python data/fpl_api.py
```

### 4. Test the Application

```bash
# Run Flask development server
python app.py

# Visit http://localhost:5000 in your browser
```

## Production Deployment

### 1. Setup Gunicorn

```bash
# Create logs directory
mkdir -p logs

# Test Gunicorn
gunicorn --bind 127.0.0.1:8000 wsgi:app
```

### 2. Configure Nginx

```bash
# Copy nginx configuration
sudo cp nginx/vantix.conf /etc/nginx/sites-available/vantix

# Update domain name in the config file
sudo nano /etc/nginx/sites-available/vantix
# Replace 'your-domain.com' with your actual domain

# Enable the site
sudo ln -s /etc/nginx/sites-available/vantix /etc/nginx/sites-enabled/

# Test nginx configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx
```

### 3. Setup Systemd Service

```bash
# Copy service file
sudo cp systemd/vantix.service /etc/systemd/system/

# Update paths in service file if not using /home/pi/fpl-dashboard
sudo nano /etc/systemd/system/vantix.service

# Reload systemd
sudo systemctl daemon-reload

# Start the service
sudo systemctl start vantix

# Enable auto-start on boot
sudo systemctl enable vantix

# Check status
sudo systemctl status vantix
```

### 4. Setup SSL with Let's Encrypt (Recommended)

```bash
# Install certbot
sudo apt update
sudo apt install certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Follow the prompts to complete setup
# Certbot will automatically configure Nginx for HTTPS
```

## Configuration

### Data Refresh Schedule

Edit `config.py` to customize when data updates occur:

```python
REFRESH_SCHEDULE = {
    'hour': 3,              # Hour (0-23)
    'minute': 0,            # Minute (0-59)
    'day_of_week': 'tue'    # Day: mon, tue, wed, thu, fri, sat, sun
}
```

Default: Every Tuesday at 3:00 AM

### Manual Data Refresh

Trigger a manual refresh:

1. Via the web interface: Click the refresh button (↻) in the bottom-right corner
2. Via command line:
   ```bash
   cd ~/fpl-dashboard
   source venv/bin/activate
   python data/fpl_api.py
   ```

## Maintenance

### View Logs

```bash
# Application logs
tail -f ~/fpl-dashboard/logs/error.log
tail -f ~/fpl-dashboard/logs/access.log

# Systemd service logs
sudo journalctl -u vantix -f

# Nginx logs
sudo tail -f /var/log/nginx/vantix_error.log
```

### Restart Services

```bash
# Restart Vantix application
sudo systemctl restart vantix

# Restart Nginx
sudo systemctl restart nginx
```

### Update Application

```bash
cd ~/fpl-dashboard
git pull
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart vantix
```

### Clear and Refresh All Data

```bash
cd ~/fpl-dashboard
source venv/bin/activate
python -c "from data.database import clear_data; clear_data()"
python data/fpl_api.py
```

## Troubleshooting

### Application Won't Start

1. Check if the port is already in use:
   ```bash
   sudo lsof -i :8000
   ```

2. Check systemd logs:
   ```bash
   sudo journalctl -u vantix -n 50
   ```

3. Verify virtual environment:
   ```bash
   which python
   # Should show: /home/pi/fpl-dashboard/venv/bin/python
   ```

### No Data Showing

1. Verify FPL IDs are correct in `config.py`
2. Check if initial data collection completed:
   ```bash
   sqlite3 data/fpl_dashboard.db "SELECT COUNT(*) FROM teams;"
   ```
3. Re-run data collection:
   ```bash
   python data/fpl_api.py
   ```

### Nginx 502 Bad Gateway

1. Check if Gunicorn is running:
   ```bash
   sudo systemctl status vantix
   ```

2. Verify Gunicorn is listening on port 8000:
   ```bash
   sudo netstat -tulpn | grep 8000
   ```

3. Check Nginx configuration:
   ```bash
   sudo nginx -t
   ```

### Charts Not Loading

1. Check browser console for JavaScript errors (F12)
2. Verify API endpoints are returning data:
   ```bash
   curl http://localhost:8000/api/stats
   ```
3. Clear browser cache and reload

## Performance Optimization

### For Raspberry Pi 4

The default configuration is optimized for Pi 4, but you can adjust:

1. **Gunicorn Workers**: In `systemd/vantix.service`, adjust `--workers`:
   - 2 workers: Minimal (1GB RAM)
   - 3 workers: Recommended (2GB+ RAM)
   - 4 workers: Maximum for Pi 4

2. **Database Location**: For better performance, ensure database is on SD card or USB SSD

3. **Scheduled Updates**: Avoid scheduling during peak usage times

## API Rate Limiting

The FPL API has rate limits. The application includes built-in delays (`API_RATE_LIMIT_DELAY = 1` second in `config.py`). If you encounter rate limit issues:

1. Increase the delay value
2. Schedule updates during off-peak hours
3. Avoid manual refreshes during gameweek deadlines

## Architecture

```
┌─────────────────┐
│   Web Browser   │
└────────┬────────┘
         │
    ┌────▼────┐
    │  Nginx  │ (Port 80/443)
    └────┬────┘
         │
  ┌──────▼──────┐
  │  Gunicorn   │ (Port 8000)
  └──────┬──────┘
         │
    ┌────▼────┐
    │  Flask  │
    └────┬────┘
         │
  ┌──────┴──────┐
  │   SQLite    │
  │  APScheduler │
  │   FPL API   │
  └─────────────┘
```

## Technology Stack

- **Backend**: Flask, Gunicorn, APScheduler
- **Database**: SQLite
- **Frontend**: Vanilla JavaScript, Chart.js
- **Web Server**: Nginx
- **Fonts**: Playfair Display, Inter (Google Fonts)

## Contributing

Feel free to submit issues and enhancement requests!

## License

MIT License - feel free to use this for your own leagues!

## Acknowledgments

- Fantasy Premier League for providing the API
- Chart.js for beautiful visualizations
- The FPL community for inspiration

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review systemd and nginx logs
3. Verify FPL API is accessible: https://fantasy.premierleague.com/api/bootstrap-static/

---

**Built with ❤️ for FPL managers everywhere**

*Vantix - Your competitive advantage in Fantasy Premier League*
