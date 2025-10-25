# Vantix Production Deployment Guide

## 🚀 Quick Setup

### 1. Clone and Navigate
```bash
git clone <your-repo-url> fpl-dashboard
cd fpl-dashboard
```

### 2. Run Deployment Script
```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

### 3. Generate Secrets
```bash
python3 scripts/generate_secrets.py
```

Copy the output and add to `.env` file.

### 4. Configure Leagues
Edit `leagues.json`:
```json
[
  {
    "code": 123456,
    "name": "My League",
    "description": "Main league"
  }
]
```

### 5. Collect Initial Data
```bash
source venv/bin/activate
python collect_all_leagues.py
```

### 6. Setup Cron for Auto-Refresh
```bash
chmod +x scripts/cron_refresh.sh
crontab -e
```

Add this line (runs Tuesdays at 3 AM):
```
0 3 * * 2 /home/pi/fpl-dashboard/scripts/cron_refresh.sh
```

### 7. Start Service
```bash
sudo systemctl restart vantix
sudo systemctl status vantix
```

---

## 🔒 Security Features

### Token-Protected Refresh
All refresh endpoints require a token:

```bash
# Refresh single league
curl -X POST http://localhost:8000/api/1234567/refresh \
  -H "X-Refresh-Token: your-token-here"

# Refresh all leagues
curl -X POST http://localhost:8000/api/refresh-all \
  -H "X-Refresh-Token: your-token-here"
```

### Environment Variables
All secrets are in `.env` (not committed to git):
- `SECRET_KEY` - Flask session security
- `REFRESH_TOKEN` - Protects refresh endpoints

---

## ⚡ Performance Features

### Caching
- **API responses cached for 5 minutes**
- Automatic cache clearing on refresh
- Reduces database load

### Rate Limiting
- **30 requests/minute** for general routes
- **120 requests/minute** for API endpoints
- **3 requests/hour** for single league refresh
- **1 request/hour** for all leagues refresh

### Smart Refresh Logic
Refresh only happens when:
1. New gameweek finished but not in database
2. Data is >6 hours old
3. No data exists yet

### Refresh Lock
Prevents concurrent refreshes that could overload the Pi.

---

## 📁 File Structure

```
fpl-dashboard/
├── .env                  # Secrets (NOT in git)
├── .env.example          # Template
├── leagues.json          # Your leagues (NOT in git)
├── leagues.json.example  # Template
├── app.py                # Main application
├── config.py             # Configuration
├── collect_all_leagues.py
├── data/
│   ├── database.py
│   ├── fpl_api.py
│   └── scheduler.py      # Disabled (using cron)
├── scripts/
│   ├── deploy.sh         # Deployment helper
│   ├── cron_refresh.sh   # Cron job script
│   └── generate_secrets.py
└── archive/              # Old migration scripts

DO NOT COMMIT:
- .env
- leagues.json
- *.db files
- logs/
```

---

## 🔧 Maintenance

### Manual Refresh
```bash
cd /home/pi/fpl-dashboard
source venv/bin/activate

# Check if refresh needed
python3 -c "
from app import is_refresh_needed
needed, reason = is_refresh_needed(1234567)  # Your league code
print(f'Refresh needed: {needed}')
print(f'Reason: {reason}')
"

# Force refresh with token
curl -X POST http://localhost:8000/api/1234567/refresh \
  -H "X-Refresh-Token: $(grep REFRESH_TOKEN .env | cut -d= -f2)"
```

### View Logs
```bash
# Application logs
tail -f logs/app.log

# Cron logs
tail -f logs/cron.log

# Systemd logs
sudo journalctl -u vantix -f
```

### Clear Cache
```bash
# Restart service (clears cache)
sudo systemctl restart vantix
```

### Update Application
```bash
git pull
./scripts/deploy.sh
```

---

## 📊 Monitoring

### Health Check
```bash
curl http://localhost:8000/health
```

Response indicates:
- **healthy**: All leagues have databases
- **degraded**: Some leagues missing data
- **unhealthy**: Critical error

### Check Cron Status
```bash
# View cron schedule
crontab -l

# Check last cron run
tail -20 logs/cron.log
```

---

## 🐛 Troubleshooting

### Refresh Returns "Not Needed"
This is normal! The app checks if:
- Latest gameweek already in database
- Data is less than 6 hours old

To force refresh, wait until a gameweek finishes or data is >6 hours old.

### Rate Limit Errors
Wait a few minutes. Rate limits protect your Pi from overload.

### "Unauthorized" on Refresh
Check your `REFRESH_TOKEN` in `.env` matches the token you're using.

### Database Missing
Run:
```bash
python collect_all_leagues.py
```

---

## 🔐 Sharing with Friends

Your friends can access the dashboard, but they **cannot** trigger refreshes without the token.

**Share with friends:**
- ✅ Dashboard URL: `https://your-domain.com/1234567`
- ✅ They can view, filter, interact
- ❌ They cannot refresh data

**Keep private:**
- 🔒 `.env` file
- 🔒 `REFRESH_TOKEN`
- 🔒 `SECRET_KEY`

---

## 🎯 Best Practices

1. **Never commit `.env` or `leagues.json`** to git
2. **Use strong secrets** - run `generate_secrets.py`
3. **Let cron handle refreshes** - don't refresh manually unless needed
4. **Monitor `/health` endpoint** for issues
5. **Check logs regularly** for errors
6. **Update dependencies** monthly:
   ```bash
   pip install --upgrade -r requirements.txt
   ```

---

## 📝 Cron Schedule Reference

```
# Every Tuesday at 3 AM
0 3 * * 2 /path/to/scripts/cron_refresh.sh

# Every day at 3 AM
0 3 * * * /path/to/scripts/cron_refresh.sh

# Twice a week (Tue, Fri at 3 AM)
0 3 * * 2,5 /path/to/scripts/cron_refresh.sh
```

---

## 🆘 Support

If you run into issues:
1. Check logs: `tail -f logs/app.log`
2. Check health: `curl http://localhost:8000/health`
3. Verify `.env` is configured
4. Verify `leagues.json` exists and is valid JSON

---

**Built with ❤️ for FPL managers everywhere**
