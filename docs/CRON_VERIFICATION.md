# Cron Job Verification Guide

## Quick Status Check

Your cron job is configured to run **daily at 6:00 AM**.

### Current Status (Nov 12, 8:20 AM)

✅ **Cron job installed**: Yes (verified in crontab)  
✅ **Cron daemon running**: Yes (verified with `ps aux`)  
❌ **Latest data**: Nov 11 (yesterday) - **No new data today!**  
❌ **Log file**: Does not exist

**Conclusion**: The cron job did NOT run this morning.

---

## Why It Didn't Run (macOS Specific)

On **macOS Catalina and later**, cron needs **Full Disk Access** permission to run scripts.

### Fix: Grant Full Disk Access to Cron

1. **Open System Preferences**
   - Click Apple menu → System Settings (or System Preferences)

2. **Go to Privacy & Security**
   - Click "Privacy & Security"
   - Scroll down and click "Full Disk Access"

3. **Add Cron**
   - Click the lock icon 🔒 and enter your password
   - Click the "+" button
   - Press `Cmd + Shift + G` and enter: `/usr/sbin/cron`
   - Click "Open"
   - Enable the checkbox next to `cron`

4. **Restart Cron** (optional but recommended)
   ```bash
   sudo launchctl stop com.vix.cron
   sudo launchctl start com.vix.cron
   ```

---

## Manual Verification Methods

### Method 1: Check Database for Today's Data

```bash
cd /Users/himnish03/Documents/Projects/SmartInvest/smartinvest-bot
source venv/bin/activate
python -c "
from data.storage import DatabaseManager
from config import Config
from datetime import date

db = DatabaseManager(Config.DATABASE_URL)
stock = db.get_stock_by_ticker('AAPL')
prices = db.get_price_history(stock.id, start_date=date.today(), end_date=date.today())
if prices:
    print(f'✅ Data updated! Latest: {prices[0].date.date()}')
else:
    print('❌ No data for today yet')
"
```

### Method 2: Check Log File

```bash
cat logs/daily_refresh.log | tail -50
```

If the log exists and has recent entries, the job ran.

### Method 3: Check Cron System Logs (macOS)

```bash
log show --predicate 'process == "cron"' --last 24h | grep daily_refresh
```

### Method 4: Check Stock Count

```bash
cd /Users/himnish03/Documents/Projects/SmartInvest/smartinvest-bot
source venv/bin/activate
python -c "
from data.storage import DatabaseManager
from config import Config

db = DatabaseManager(Config.DATABASE_URL)
stocks = db.get_all_stocks()
print(f'Total stocks: {len(stocks)}')

# Check a sample stock
stock = db.get_stock_by_ticker('AAPL')
prices = db.get_price_history(stock.id, start_date=None, end_date=None)
print(f'AAPL total price records: {len(prices)}')
if prices:
    latest = max(prices, key=lambda p: p.date)
    print(f'AAPL latest: {latest.date.date()} at \${latest.close:.2f}')
"
```

---

## Alternative: Use launchd Instead of Cron (Recommended for macOS)

macOS prefers `launchd` over cron. Here's how to set it up:

### Create Launch Agent

```bash
cat > ~/Library/LaunchAgents/com.smartinvest.dailyrefresh.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.smartinvest.dailyrefresh</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/Users/himnish03/Documents/Projects/SmartInvest/smartinvest-bot/venv/bin/python</string>
        <string>/Users/himnish03/Documents/Projects/SmartInvest/smartinvest-bot/scripts/daily_refresh.py</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>/Users/himnish03/Documents/Projects/SmartInvest/smartinvest-bot</string>
    
    <key>StandardOutPath</key>
    <string>/Users/himnish03/Documents/Projects/SmartInvest/smartinvest-bot/logs/daily_refresh.log</string>
    
    <key>StandardErrorPath</key>
    <string>/Users/himnish03/Documents/Projects/SmartInvest/smartinvest-bot/logs/daily_refresh_error.log</string>
    
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>6</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
EOF
```

### Load the Launch Agent

```bash
launchctl load ~/Library/LaunchAgents/com.smartinvest.dailyrefresh.plist
```

### Verify It's Loaded

```bash
launchctl list | grep smartinvest
```

### Test It Manually

```bash
launchctl start com.smartinvest.dailyrefresh
```

### Check Logs

```bash
tail -f ~/Documents/Projects/SmartInvest/smartinvest-bot/logs/daily_refresh.log
```

### Remove Old Cron Job (if using launchd)

```bash
crontab -l > /tmp/current_cron.txt
crontab -r  # Remove current crontab
```

---

## Quick Test: Run Manually Now

To verify the script works independently of cron:

```bash
cd /Users/himnish03/Documents/Projects/SmartInvest/smartinvest-bot
source venv/bin/activate
python scripts/daily_refresh.py
```

**Expected output**:
- "Refreshing prices for 483 stocks..."
- Progress updates
- "✓ Refresh complete"

Then verify:
```bash
python -c "
from data.storage import DatabaseManager
from config import Config
from datetime import date

db = DatabaseManager(Config.DATABASE_URL)
stock = db.get_stock_by_ticker('AAPL')
prices = db.get_price_history(stock.id, start_date=date.today(), end_date=date.today())
print(f'Data for today: {len(prices)} records')
if prices:
    print(f'✅ Success! Latest: {prices[0].date.date()} at \${prices[0].close:.2f}')
"
```

---

## Summary

**Current Issue**: Cron job didn't run this morning (Nov 12, 6 AM)  
**Most Likely Cause**: macOS Full Disk Access permission not granted to cron  
**Best Solution**: Grant Full Disk Access OR switch to launchd (recommended)

**Next Steps**:
1. ✅ Grant cron Full Disk Access (see above)
2. ⏰ Wait until tomorrow 6 AM and check again
3. 🔍 Or manually run script now to verify it works
4. 💡 Consider switching to launchd for better macOS compatibility

---

**Last Updated**: November 12, 2025, 8:20 AM  
**Status**: Awaiting user action to grant permissions

