# Vantix - Project Overview

## Brand Name
**Vantix** - Derived from "vantage" (position of advantage) with a modern tech twist. Represents the competitive edge your FPL league dashboard provides.

## Project Description
A lightweight, aesthetically beautiful Fantasy Premier League dashboard optimized for Raspberry Pi 4. Features interactive charts, real-time statistics, and automated data collection from the FPL API.

## Key Features
- 📊 Interactive cumulative points and league position charts
- 🎨 Premium creamy pastel design with professional typography
- 📱 Containerized responsive layout (tablet/mobile/desktop)
- 🔄 Automated weekly data updates via APScheduler
- ⚡ Lightweight SQLite database for fast local access
- 🎯 Team filtering and comparison tools
- 📈 Rich statistics and insights
- 💎 Chip usage visualization

## Technology Stack

### Backend
- **Flask** - Lightweight Python web framework
- **Gunicorn** - Production WSGI server
- **APScheduler** - Automated data refresh scheduling
- **SQLite** - Lightweight embedded database
- **Requests** - FPL API communication

### Frontend
- **Vanilla JavaScript** - No framework bloat
- **Chart.js** - Beautiful, responsive charts
- **Google Fonts** - Playfair Display + Inter pairing
- **Custom CSS** - Mobile-first responsive design

### Infrastructure
- **Nginx** - Reverse proxy and static file serving
- **Systemd** - Service management
- **Let's Encrypt** - SSL/TLS certificates

## File Structure

```
fpl-dashboard/
├── app.py                      # Main Flask application
├── config.py                   # Configuration (FPL IDs, settings)
├── wsgi.py                     # Gunicorn entry point
├── requirements.txt            # Python dependencies
├── setup.sh                    # Automated setup script
├── inspect_db.py              # Database inspection utility
├── .gitignore                 # Git ignore rules
│
├── data/                       # Data layer
│   ├── __init__.py
│   ├── database.py            # Database initialization and connections
│   ├── fpl_api.py             # FPL API wrapper and data collection
│   ├── scheduler.py           # APScheduler configuration
│   └── fpl_dashboard.db       # SQLite database (generated)
│
├── static/                     # Static assets
│   ├── css/
│   │   └── style.css          # Main stylesheet (creamy theme)
│   ├── js/
│   │   ├── dashboard.js       # Main dashboard logic
│   │   ├── charts.js          # Chart.js implementations
│   │   └── filters.js         # Team filtering logic
│   └── images/
│       ├── README.md          # Favicon instructions
│       └── favicon.ico        # Site icon (user provides)
│
├── templates/                  # Jinja2 templates
│   ├── base.html              # Base template with meta tags
│   ├── dashboard.html         # Main dashboard view
│   └── error.html             # Error page
│
├── nginx/                      # Nginx configuration
│   └── vantix.conf            # Nginx site configuration
│
├── systemd/                    # Systemd service
│   └── vantix.service         # Service definition
│
├── logs/                       # Application logs (generated)
│   ├── error.log
│   ├── access.log
│   └── vantix.log
│
└── docs/                       # Documentation
    ├── README.md              # Comprehensive documentation
    ├── QUICKSTART.md          # 5-minute setup guide
    ├── DEPLOYMENT_CHECKLIST.md # Step-by-step deployment
    └── PRODUCTION.md          # Production configuration guide
```

## Database Schema

### Tables

**teams**
- entry_id (PK)
- team_name
- manager_name
- created_at

**gameweeks**
- id (PK)
- deadline
- finished
- created_at

**gameweek_points**
- id (PK)
- entry_id (FK)
- gameweek (FK)
- points
- total_points
- rank
- bank
- value
- event_transfers
- event_transfers_cost
- updated_at

**transfers**
- id (PK)
- entry_id (FK)
- gameweek
- transfer_count
- transfers_in (CSV)
- transfers_out (CSV)
- created_at

**chip_usage**
- id (PK)
- entry_id (FK)
- gameweek
- chip_name
- created_at

**player_stats**
- id (PK)
- entry_id (FK)
- total_goals
- total_assists
- total_clean_sheets
- updated_at

## API Endpoints

### Public Endpoints
- `GET /` - Main dashboard view
- `GET /api/cumulative-points` - Cumulative points data
- `GET /api/league-positions` - League position worm data
- `GET /api/recent-transfers` - Recent transfers by gameweek
- `GET /api/stats` - League statistics
- `POST /api/refresh` - Manual data refresh trigger

### Query Parameters
All chart endpoints accept:
- `teams` (multiple) - Filter by team entry IDs

Example: `/api/cumulative-points?teams=123456&teams=789012`

## Design System

### Colors
```css
--bg-primary: #FAF8F3       /* Warm off-white background */
--bg-secondary: #F5F2EB     /* Secondary background */
--bg-card: #FFFFFF          /* Card background */
--color-primary: #E8DCC4    /* Soft beige */
--color-accent-1: #A8DADC   /* Powder blue */
--color-accent-2: #F1C6B7   /* Dusty pink */
--color-accent-3: #B8D4B8   /* Sage green */
--color-text: #3A3A3A       /* Soft black */
```

### Typography
- **Headings**: Playfair Display (elegant serif)
- **Body**: Inter (clean sans-serif)
- **Base Size**: 16px (14px on mobile)

### Spacing
- xs: 8px
- sm: 12px
- md: 20px
- lg: 32px
- xl: 48px

### Container
- Max Width (Tablet): 900px
- Max Width (Desktop): 1100px
- Optimized for iPad-style viewing

## Configuration Options

### FPL Settings (config.py)
```python
FPL_TEAM_ID = 123456        # Your FPL team entry ID
FPL_LEAGUE_ID = 123456      # Classic league ID
LEAGUE_NAME = "My League"   # Display name
```

### Refresh Schedule (config.py)
```python
REFRESH_SCHEDULE = {
    'hour': 3,              # 3 AM
    'minute': 0,
    'day_of_week': 'tue'    # Tuesday after GW deadline
}
```

### Rate Limiting (config.py)
```python
API_RATE_LIMIT_DELAY = 1    # Seconds between API calls
```

## Performance Characteristics

### Resource Usage (Raspberry Pi 4)
- **Memory**: ~150-300MB (depending on workers)
- **CPU**: <10% during normal operation
- **Database**: ~5-20MB depending on league size
- **Initial Data Collection**: 2-3 minutes
- **Page Load**: <1 second (after first load)

### Scalability
- Supports leagues up to 50+ teams
- Handles multiple concurrent users
- Efficient caching minimizes API calls

## Security Features

- **No authentication required** (private league data only)
- **Rate limiting** on API calls
- **HTTPS/SSL** support via Let's Encrypt
- **Security headers** configured in Nginx
- **Input validation** on all API endpoints
- **No user data collection** or tracking

## Browser Compatibility

Tested and optimized for:
- Chrome/Edge (latest)
- Firefox (latest)
- Safari (iOS 13+, macOS)
- Mobile browsers (iOS/Android)

## Future Enhancement Ideas

Potential features for future versions:
- Dark mode toggle
- Head-to-head comparison view
- Historical season data
- Export data as CSV/PDF
- Email notifications for milestones
- Player price change tracking
- Fixture difficulty analysis
- Dream team comparison

## Development Workflow

1. **Local Development**
   ```bash
   python app.py  # Runs on localhost:5000
   ```

2. **Testing**
   ```bash
   python inspect_db.py  # Check database
   python data/fpl_api.py  # Test data collection
   ```

3. **Deployment**
   ```bash
   sudo systemctl restart vantix  # Deploy changes
   ```

## Maintenance Schedule

### Weekly
- Monitor logs for errors
- Verify data updates after gameweeks

### Monthly
- Check disk space
- Review application logs
- Update system packages

### Quarterly
- Update Python dependencies
- Review and optimize database
- Check SSL certificate renewal

## Known Limitations

1. **FPL API Rate Limits**: Includes built-in delays to respect limits
2. **Historical Data**: Only collects from current season
3. **Live Scores**: Not real-time during matches (scheduled updates)
4. **Private Leagues Only**: Requires league membership for data access

## Credits

**Created by**: [Your Name]
**Built for**: FPL managers who want beautiful league insights
**Inspired by**: The competitive spirit of Fantasy Premier League

## License

MIT License - Free to use, modify, and distribute

## Version

**v1.0.0** - Initial Release
- Core dashboard functionality
- Automated data collection
- Interactive charts
- Responsive design
- Production-ready deployment

---

**Vantix** - Your competitive advantage in Fantasy Premier League! 🏆
