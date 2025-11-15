# SmartInvest Bot - Automated Daily Refresh Guide

## 📋 Overview

This guide explains how to set up **fully automated daily data refresh** for your SmartInvest bot, handling **500 stocks** with continuous historical data preservation.

---

## 🎯 What Gets Automated

### Daily Refresh (6:00 AM ET)
1. **Stock Prices** - Latest OHLCV data for all 500 stocks
2. **Fundamentals** - Quarterly metrics (P/E, EPS, market cap, etc.)
3. **News & Sentiment** - Last 7 days of articles with FinBERT sentiment
4. **ML Model** - Automatic retraining with fresh data (optional)

### Key Features
- ✅ Preserves ALL historical data (never deletes)
- ✅ Only adds new data points (incremental)
- ✅ Respects API rate limits automatically
- ✅ Runs unattended (no manual intervention)
- ✅ Logs all operations for debugging

---

## 🚀 Quick Setup (3 Steps)

### Step 1: Load Initial S&P 500 Data

```bash
cd /Users/himnish03/Documents/Projects/SmartInvest/smartinvest-bot
source venv/bin/activate

# Load S&P 500 stocks (first time only)
python scripts/load_sp500.py
```

**What it does:**
- Fetches S&P 500 ticker list from Wikipedia
- Loads company info for each stock
- Downloads 5 years of historical price data
- Saves to database

**Time:** ~25 minutes for 250 stocks (FMP API limit)
**Note:** Run twice (today + tomorrow) to complete all 500 stocks

---

### Step 2: Test Daily Refresh (Manual Run)

```bash
# Test the refresh script manually
python scripts/daily_refresh.py
```

**What it does:**
- Updates prices for all stocks (adds new data only)
- Refreshes fundamentals
- Fetches latest news + sentiment
- Preserves historical data

**Time:** ~10-15 minutes for 500 stocks

**Expected output:**
```
╔════════════════════════════════════════════════════════════╗
║            DAILY DATA REFRESH - SmartInvest Bot            ║
╚════════════════════════════════════════════════════════════╝

STEP 1: REFRESH STOCK PRICES
  [AAPL] Updating from 2025-11-08...
    ✅ Added 1 new price records
  [MSFT] Updating from 2025-11-08...
    ✅ Added 1 new price records
  ...
✅ Price refresh complete: 498 success, 2 failed

STEP 2: REFRESH FUNDAMENTALS
  ...
✅ Fundamentals refresh complete: 495 success, 5 failed

STEP 3: REFRESH NEWS & SENTIMENT
  ...
✅ News refresh complete: 480 success, 20 failed

╔════════════════════════════════════════════════════════════╗
║                    REFRESH COMPLETE!                       ║
╚════════════════════════════════════════════════════════════╝

📊 Results:
   Prices:       498 ✅  2 ❌
   Fundamentals: 495 ✅  5 ❌
   News:         480 ✅  20 ❌

⏱️  Time: 12.3 minutes
```

---

### Step 3: Set Up Automatic Daily Cron Job

```bash
# Set up cron job (runs daily at 6 AM)
python scripts/setup_cron.py
```

**What it does:**
- Creates cron job that runs `daily_refresh.py` every day at 6 AM ET
- Redirects output to `logs/daily_refresh.log`
- Handles errors gracefully

**Cron schedule:**
```cron
0 6 * * * cd /path/to/smartinvest-bot && /path/to/venv/bin/python scripts/daily_refresh.py >> logs/daily_refresh.log 2>&1
```

**Platform-specific:**
- **macOS/Linux:** Cron (automatic)
- **Windows:** Task Scheduler (manual setup, instructions provided)

---

## 📊 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DAILY REFRESH FLOW                       │
└─────────────────────────────────────────────────────────────┘

6:00 AM ET - Cron triggers daily_refresh.py
    │
    ├─ STEP 1: Update Stock Prices (yfinance)
    │    └─ For each stock:
    │         ├─ Check latest date in DB
    │         ├─ Fetch new data from (latest + 1) to today
    │         └─ Insert new records (preserves old data)
    │
    ├─ STEP 2: Update Fundamentals (FMP)
    │    └─ Fetch latest quarterly metrics
    │
    ├─ STEP 3: Update News & Sentiment (NewsAPI + FinBERT)
    │    └─ Fetch last 7 days of news
    │         └─ Analyze sentiment with FinBERT
    │
    └─ 6:15 AM - Refresh complete
         └─ Log results to logs/daily_refresh.log

9:30 AM ET - Market opens (bot has fresh data)
```

---

## 🗄️ Database Architecture

### Historical Data Preservation

```sql
-- Example: AAPL price history
stocks
  id: 1
  ticker: 'AAPL'
  company_name: 'Apple Inc.'

stock_prices (preserved forever)
  stock_id: 1, date: '2020-11-09', close: 115.32  ← 5 years ago
  stock_id: 1, date: '2020-11-10', close: 116.11
  ...
  stock_id: 1, date: '2025-11-07', close: 226.96  ← yesterday
  stock_id: 1, date: '2025-11-08', close: 227.48  ← NEW (added today)
```

**Key principles:**
1. **Never delete** - Historical data is preserved forever
2. **Incremental only** - Only new data points are added
3. **Idempotent** - Safe to run multiple times (no duplicates)
4. **Space efficient** - 500 stocks × 5 years ≈ 50 MB

---

## 📈 API Usage & Limits

### Daily Consumption (500 stocks)

| API | Purpose | Daily Calls | Limit | Status |
|-----|---------|-------------|-------|--------|
| **yfinance** | Historical prices | 500 | ∞ | ✅ Free |
| **FMP** | Fundamentals | 250 | 250/day | ⚠️ Split over 2 days |
| **Finnhub** | Real-time quotes | 500 | 60/min | ✅ Within limit |
| **NewsAPI** | News articles | 500 | 500/day | ✅ Exact match |
| **FinBERT** | Sentiment | Local | ∞ | ✅ Offline |

**Strategy to handle FMP limit:**
- Day 1: Refresh fundamentals for stocks 1-250
- Day 2: Refresh fundamentals for stocks 251-500
- Fundamentals only change quarterly, so this is fine

---

## 🔍 Monitoring & Logs

### View Recent Logs

```bash
# View last 50 lines
tail -50 logs/daily_refresh.log

# Follow live (during refresh)
tail -f logs/daily_refresh.log

# Search for errors
grep -i error logs/daily_refresh.log
```

### Check Cron Status

```bash
# View cron jobs
crontab -l

# Test cron job manually
cd /Users/himnish03/Documents/Projects/SmartInvest/smartinvest-bot
source venv/bin/activate
python scripts/daily_refresh.py
```

### Database Health Check

```bash
# Check stock count
python -c "
from config import Config
from data.storage import DatabaseManager

db = DatabaseManager(Config.DATABASE_URL)
stocks = db.get_all_stocks()
print(f'Total stocks: {len(stocks)}')

# Check latest price date
for stock in stocks[:5]:
    latest = db.get_latest_price(stock.id)
    if latest:
        print(f'{stock.ticker}: Latest price date = {latest.date}')
"
```

---

## 🛠️ Troubleshooting

### Issue 1: Cron job not running

**Symptoms:**
- No new data appearing
- Logs not updating

**Fix:**
```bash
# Check if cron service is running (Linux)
sudo systemctl status cron

# macOS: Check if cron is allowed
sudo launchctl list | grep cron

# View cron logs
grep CRON /var/log/syslog  # Linux
log show --predicate 'process == "cron"' --last 1d  # macOS
```

### Issue 2: API rate limits exceeded

**Symptoms:**
```
FMP API Error: 429 Too Many Requests
```

**Fix:**
- FMP limit: 250/day
- Solution: Split fundamentals refresh over 2 days
- Or upgrade FMP plan ($15/month for 500 calls/day)

### Issue 3: Database locked

**Symptoms:**
```
sqlite3.OperationalError: database is locked
```

**Fix:**
```bash
# Make sure bot is not running during refresh
ps aux | grep bot_with_real_data.py
kill <PID>

# Run refresh
python scripts/daily_refresh.py

# Restart bot
python bot_with_real_data.py &
```

### Issue 4: Missing data for some stocks

**Symptoms:**
- Some stocks have no price data

**Fix:**
```bash
# Re-run load for specific tickers
python -c "
from config import Config
from data.storage import DatabaseManager
from data.collectors import StockDataCollector

db = DatabaseManager(Config.DATABASE_URL)
collector = StockDataCollector(Config.FMP_API_KEY, Config.FINNHUB_API_KEY)

# Re-load specific stocks
failed_tickers = ['BRK-B', 'GOOGL']
for ticker in failed_tickers:
    collector.load_stock_data(ticker, db)
"
```

---

## 📅 Maintenance Schedule

### Daily (Automated)
- ✅ 6:00 AM - Data refresh runs automatically
- ✅ Check logs occasionally: `tail logs/daily_refresh.log`

### Weekly (5 minutes)
- Review success rate in logs
- Check for API errors
- Verify database size growth is reasonable

### Monthly (10 minutes)
- Retrain ML model: `python scripts/train_model_v2.py`
- Review bot performance metrics
- Update stock universe if needed

### Quarterly (30 minutes)
- Review API usage vs. limits
- Consider API plan upgrades if needed
- Backup database: `cp smartinvest_dev.db backups/`

---

## 🎯 Production Deployment (Optional)

### For 24/7 Server Deployment

#### Option 1: Systemd (Linux - Recommended)

```bash
# Create service file
sudo nano /etc/systemd/system/smartinvest-refresh.service
```

```ini
[Unit]
Description=SmartInvest Daily Data Refresh
After=network.target

[Service]
Type=oneshot
User=your_username
WorkingDirectory=/path/to/smartinvest-bot
ExecStart=/path/to/venv/bin/python scripts/daily_refresh.py
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
# Create timer
sudo nano /etc/systemd/system/smartinvest-refresh.timer
```

```ini
[Unit]
Description=Run SmartInvest refresh daily at 6 AM
Requires=smartinvest-refresh.service

[Timer]
OnCalendar=*-*-* 06:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable smartinvest-refresh.timer
sudo systemctl start smartinvest-refresh.timer

# Check status
sudo systemctl status smartinvest-refresh.timer
sudo systemctl list-timers
```

#### Option 2: Docker + cron

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt

# Add cron job
RUN echo "0 6 * * * cd /app && python scripts/daily_refresh.py >> /app/logs/refresh.log 2>&1" | crontab -

CMD ["cron", "-f"]
```

---

## 📊 Expected Results

### After Initial Setup
```
Database Stats:
  • Stocks: 500 (S&P 500)
  • Price records: ~630,000 (500 stocks × 5 years × 252 trading days)
  • News articles: ~5,000 (10 per stock × 500 stocks)
  • Database size: ~60 MB
```

### After 30 Days
```
Database Stats:
  • Stocks: 500
  • Price records: ~636,000 (+6,000 new daily records)
  • News articles: ~8,500 (+3,500 new articles)
  • Database size: ~65 MB
  • Historical data: Fully preserved
```

### After 1 Year
```
Database Stats:
  • Stocks: 500
  • Price records: ~756,000 (+126,000 = 1 extra year)
  • News articles: ~50,000
  • Database size: ~120 MB
  • Historical data: 6 years preserved
```

---

## ✅ Verification Checklist

After setup, verify everything works:

- [ ] S&P 500 stocks loaded (`python scripts/load_sp500.py`)
- [ ] Manual refresh successful (`python scripts/daily_refresh.py`)
- [ ] Cron job created (`crontab -l`)
- [ ] Logs directory exists (`ls logs/`)
- [ ] Database contains data (`ls -lh smartinvest_dev.db`)
- [ ] Bot can query data (`python bot_with_real_data.py` → `/daily`)
- [ ] Next morning: Check logs for automatic run

---

## 🎉 You're Done!

Your SmartInvest bot now:
- ✅ Tracks 500 stocks automatically
- ✅ Refreshes data every day at 6 AM
- ✅ Preserves all historical data for ML training
- ✅ Runs unattended with zero maintenance
- ✅ Logs all operations for monitoring

**Next steps:**
1. Let it run for a week
2. Monitor logs daily
3. Retrain ML model weekly
4. Enjoy automated stock recommendations! 🚀

---

## 📞 Support

If you run into issues:
1. Check logs: `tail -50 logs/daily_refresh.log`
2. Review troubleshooting section above
3. Test manually: `python scripts/daily_refresh.py`
4. Verify API keys in `.env` file

---

**Last updated:** November 9, 2025

