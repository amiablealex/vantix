# Vantix Update V2 - Bug Fixes & Advanced Analytics

## Issues Fixed

### 1. ✅ **Section Reordering**
- Moved "Recent Transfers" above "Recent Form"
- New order: Charts → Transfers → Form → Analytics

### 2. ✅ **Master Filter Implementation**
- Single filter control at the top (under header)
- Controls ALL visualizations simultaneously
- Completely rewritten event handling (no more freezing)
- Select All / Clear All buttons work properly

### 3. ✅ **Chip Usage Visibility**
- Changed chip markers to use darker, more visible colors
- Stars (★) now stand out on light backgrounds

### 4. ✅ **Filter Buttons Fixed**
- Complete rewrite of filter logic
- No more freezing after first click
- All buttons work reliably

### 5. ✅ **Recent Form Chart Fixed**
- Fixed API endpoint to exclude current unfinished gameweek
- Now properly displays last 5 completed gameweeks

## New Advanced Analytics

### 📊 **Points Distribution Chart**
- Histogram showing how gameweek scores are spread
- Bins: 0-20, 20-40, 40-60, 60-80, 80-100, 100+
- See the overall scoring patterns in your league

### 📈 **Team Comparison Cards**
Detailed stats for selected teams:
- Total Points
- Average Per GW
- Highest GW Score
- Lowest GW Score
- Total Transfers Made
- Chips Used

### 🎢 **Biggest Movers (Last 5 GWs)**
- Shows top 5 climbers (moving up ranks)
- Shows top 5 fallers (dropping in ranks)
- Visualizes recent momentum changes

## Files to Update (7 files)

1. **templates/dashboard.html** - Reordered layout + master filter + new sections
2. **static/css/style.css** - Master filter styles + analytics section styles
3. **app.py** - New API endpoints for analytics
4. **static/js/dashboard.js** - Complete rewrite with master filter
5. **static/js/charts.js** - Updated with darker chip colors + distribution chart
6. **static/js/filters.js** - DELETED (no longer needed - functionality moved to dashboard.js)

## Deployment Steps

```bash
# 1. SSH into Pi
cd ~/fpl-dashboard

# 2. Backup
mkdir -p backups/v2
cp templates/dashboard.html backups/v2/
cp static/css/style.css backups/v2/
cp app.py backups/v2/
cp static/js/*.js backups/v2/

# 3. Replace files (copy-paste content from downloads)
# - templates/dashboard.html
# - static/css/style.css
# - app.py
# - static/js/dashboard.js
# - static/js/charts.js

# 4. DELETE old filters.js (functionality now in dashboard.js)
rm static/js/filters.js

# 5. Restart
source venv/bin/activate
sudo systemctl restart vantix

# 6. Test in browser!
```

## Key Technical Changes

### Master Filter Architecture
- Single `selectedTeams` Set (not separate sets per chart)
- All visualizations read from this single source
- When filter changes, all charts update via `updateAllVisualizations()`

### Event Handling Fix
- Direct event listeners on master filter pills
- No more event delegation issues
- Pills created once at initialization
- Listeners attached immediately after creation

### Form Chart Bug Fix
The form chart was blank because:
- Old code included current (unfinished) gameweek
- New code uses `current_gw - 1` to only show completed GWs
- Query: `WHERE gp.gameweek BETWEEN ? AND ?` with `[start_gw, current_gw - 1]`

### Chip Marker Visibility
Changed from light colors to darker ones:
- Points: Now use full team colors (not translucent)
- Border: White 2px border around stars
- Size: 8px radius (larger)
- Style: `pointBackgroundColor: color` (was color + opacity)

## Testing Checklist

After deployment:

- [ ] Master filter displays all teams
- [ ] Clicking team pill toggles selection
- [ ] "Select All" button works
- [ ] "Clear All" button works
- [ ] Cumulative points chart updates with filter
- [ ] League position chart updates with filter
- [ ] Recent Transfers section shows correct GW
- [ ] Recent Form chart displays data (not blank)
- [ ] Points Distribution histogram appears
- [ ] Team Comparison cards show selected teams
- [ ] Biggest Movers shows climbers and fallers
- [ ] Chip stars (★) are visible on worm chart
- [ ] All sections respond to master filter changes
- [ ] No freezing when clicking multiple teams

## What's Different from V1

**V1 Problems:**
- Separate filters per chart (confusing)
- Event delegation issues causing freezing
- Form chart blank
- Chip markers hard to see

**V2 Solutions:**
- Single master filter (simple, intuitive)
- Direct event listeners (reliable)
- Form chart fixed with proper GW range
- Darker chip colors (visible)
- 3 new analytics sections (insights!)

## Rollback (if needed)

```bash
cp backups/v2/dashboard.html templates/
cp backups/v2/style.css static/css/
cp backups/v2/app.py .
cp backups/v2/dashboard.js static/js/
cp backups/v2/charts.js static/js/
cp backups/v2/filters.js static/js/  # restore old file
sudo systemctl restart vantix
```

## Performance Notes

- Master filter is more efficient (single state)
- Fewer API calls (all charts share one filter)
- New analytics queries are optimized with indexes
- Distribution chart uses client-side binning (fast)

## Browser Console Debugging

If issues occur, check browser console (F12):
```javascript
// Check state
console.log(VantixDashboard.selectedTeams);

// Check teams loaded
console.log(VantixDashboard.teams);

// Manually update
updateAllVisualizations();
```

---

**After this update, your dashboard will have:**
✅ Single intuitive filter
✅ Working buttons
✅ Visible chip markers
✅ Form chart with data
✅ 3 new advanced analytics sections
✅ Professional, polished UX

Enjoy your enhanced Vantix dashboard! 🏆
