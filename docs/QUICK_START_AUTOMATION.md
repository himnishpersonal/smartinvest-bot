# Quick Start: Automated 500-Stock System

## ✅ Phase 1 & 2 Implementation Complete!

Your bot now has **automatic daily refresh** for **500 stocks** with **continuous historical data preservation**.

---

## 🚀 Quick Start (3 Commands)

### 1. Load S&P 500 Stocks (Initial Setup)

```bash
cd /Users/himnish03/Documents/Projects/SmartInvest/smartinvest-bot
source venv/bin/activate
python scripts/load_sp500.py
```

**First run:** Loads 250 stocks (FMP API limit)  
**Second run (next day):** Loads remaining 250 stocks  
**Time:** ~25 minutes per run

---

### 2. Test Daily Refresh (Manual)

```bash
python scripts/daily_refresh.py
```

**What it does:**
- Updates all stock prices (adds new data only)
- Refreshes fundamentals
- Fetches latest news + sentiment
- **Preserves ALL historical data**

**Time:** ~10-15 minutes for 500 stocks

---

### 3. Enable Automatic Daily Updates

```bash
python scripts/setup_cron.py
```

**What it does:**
- Creates cron job that runs daily at 6:00 AM ET
- Completely automated (zero maintenance)
- Logs to `logs/daily_refresh.log`

---

## 📊 What You Get

### Before (Manual, 100 stocks)
```
❌ Manual data loading
❌ 100 stocks only
❌ One-time data snapshot
❌ No automatic updates
```

### After (Automated, 500 stocks)
```
✅ 500 S&P 500 stocks
✅ Automatic daily refresh at 6 AM
✅ Preserves ALL historical data
✅ Continuous ML training data
✅ Fresh data every market day
✅ Zero maintenance required
```

---

## 🗄️ Data Architecture

```
Historical Data (Preserved Forever)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  2020-11-09  AAPL: $115.32  ← 5 years ago
  2020-11-10  AAPL: $116.11
  ...
  2025-11-07  AAPL: $226.96  ← yesterday
  2025-11-08  AAPL: $227.48  ← NEW (added today)
  2025-11-09  AAPL: $228.12  ← tomorrow (will add)

New Data (Added Daily)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  • Latest OHLCV prices (500 stocks)
  • Fundamentals (quarterly)
  • News articles (last 7 days)
  • Sentiment scores (FinBERT)
```

**Key principle:** Never delete, only append!

---

## 📈 Daily Flow

```
┌─────────────────────────────────────────┐
│  6:00 AM ET - Cron Job Triggers        │
└─────────────────────────────────────────┘
              │
              ├─ Fetch latest prices (yfinance)
              ├─ Update fundamentals (FMP)
              ├─ Fetch news (NewsAPI)
              ├─ Analyze sentiment (FinBERT)
              └─ Save to database (append only)
              │
┌─────────────────────────────────────────┐
│  6:15 AM ET - Refresh Complete          │
│  Database now has fresh data            │
└─────────────────────────────────────────┘
              │
┌─────────────────────────────────────────┐
│  9:30 AM ET - Market Opens              │
│  Bot ready with latest data             │
└─────────────────────────────────────────┘
```

---

## 📦 New Files Created

### Scripts
1. **`scripts/load_sp500.py`**  
   - Loads S&P 500 stocks from Wikipedia
   - Fetches 5 years of historical data
   - Respects API limits (250/day)

2. **`scripts/daily_refresh.py`**  
   - Updates existing stocks with latest data
   - Preserves historical data
   - Safe to run multiple times

3. **`scripts/setup_cron.py`**  
   - Creates automatic daily cron job
   - Platform-specific (macOS/Linux/Windows)

4. **`scripts/test_automation.py`**  
   - Tests the entire pipeline
   - Verifies data preservation

### Documentation
5. **`AUTOMATION_GUIDE.md`**  
   - Complete guide (30+ pages)
   - Troubleshooting
   - Monitoring
   - Production deployment

6. **`QUICK_START_AUTOMATION.md`** (this file)  
   - Quick reference

---

## 🔍 Monitoring

### Check if refresh is running
```bash
# View logs
tail -f logs/daily_refresh.log

# Check last refresh time
ls -lh logs/daily_refresh.log
```

### View cron schedule
```bash
crontab -l
```

### Check database stats
```bash
ls -lh smartinvest_dev.db
```

### Verify latest data
```bash
python -c "
from config import Config
from data.storage import DatabaseManager

db = DatabaseManager(Config.DATABASE_URL)
stocks = db.get_all_stocks()
print(f'Stocks in database: {len(stocks)}')

for stock in stocks[:5]:
    latest = db.get_latest_price(stock.id)
    print(f'{stock.ticker}: {latest.date}')
"
```

---

## 🎯 API Usage (Daily)

| API | Purpose | Calls | Limit | Status |
|-----|---------|-------|-------|--------|
| yfinance | Prices | 500 | ∞ | ✅ Free |
| FMP | Fundamentals | 250 | 250/day | ⚠️ 2-day rotation |
| Finnhub | Real-time | 500 | 60/min | ✅ OK |
| NewsAPI | News | 500 | 500/day | ✅ Exact match |

**Strategy:** Fundamentals rotate over 2 days (change quarterly anyway)

---

## 🛠️ Troubleshooting

### Issue: "No stocks in database"
```bash
# Run initial load
python scripts/load_sp500.py
```

### Issue: "API key not found"
```bash
# Check .env file
cat .env | grep API_KEY

# Should have:
FMP_API_KEY=your_key_here
FINNHUB_API_KEY=your_key_here
NEWS_API_KEY=your_key_here
```

### Issue: "Cron not running"
```bash
# Check cron jobs
crontab -l

# Re-run setup
python scripts/setup_cron.py
```

### Issue: "Database locked"
```bash
# Stop bot
ps aux | grep bot_with_real_data
kill <PID>

# Run refresh
python scripts/daily_refresh.py

# Restart bot
python bot_with_real_data.py &
```

---

## ✅ Verification Checklist

After setup:

- [ ] API keys configured in `.env`
- [ ] S&P 500 stocks loaded (run `load_sp500.py`)
- [ ] Manual refresh successful (run `daily_refresh.py`)
- [ ] Cron job created (run `setup_cron.py`)
- [ ] Logs directory exists (`mkdir -p logs`)
- [ ] Bot commands work (`/daily` in Discord)
- [ ] Tomorrow: Check logs for automatic run

---

## 📊 Expected Database Growth

```
Day 0 (Initial Load):
  • Stocks: 500
  • Price records: ~630,000 (5 years × 500 stocks)
  • Database size: ~60 MB

Day 1 (After first refresh):
  • Price records: ~630,500 (+500 new)
  • Database size: ~60.1 MB

Day 30:
  • Price records: ~645,000 (+15,000)
  • Database size: ~62 MB

Day 365:
  • Price records: ~756,000 (+126,000 = 1 extra year)
  • Database size: ~75 MB
  • Historical data: 6 years preserved!
```

---

## 🎉 You're Done!

Run these commands:
```bash
# 1. Load stocks (first time)
python scripts/load_sp500.py

# 2. Test refresh
python scripts/daily_refresh.py

# 3. Enable automation
python scripts/setup_cron.py
```

That's it! Your bot now:
- ✅ Tracks 500 stocks
- ✅ Updates automatically every day
- ✅ Preserves all historical data
- ✅ Zero maintenance required

**Full documentation:** See `AUTOMATION_GUIDE.md` for details

**Need help?** Check logs: `tail -50 logs/daily_refresh.log`

---

**Ready to scale? Your SmartInvest bot is now production-ready! 🚀**

