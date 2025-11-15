# 📊 Performance Tracking System

**Automatic recommendation performance tracking for SmartInvest Bot**

---

## 🎯 What It Does

The Performance Tracking system automatically monitors every stock recommendation the bot makes and measures how well they perform over time (1-day, 5-day, 10-day, and 30-day returns).

### Key Features

✅ **Automatic Tracking** - Every recommendation is automatically tracked  
✅ **Multiple Timeframes** - 1d, 5d, 10d, 30d returns  
✅ **Peak/Trough Tracking** - Records best and worst prices  
✅ **Win Rate Calculation** - Tracks percentage of profitable picks  
✅ **Strategy Comparison** - Compare momentum vs. dip strategies  
✅ **Leaderboard** - See top and worst performers  
✅ **Daily Updates** - Automatically updated with your daily refresh  

---

## 🏗️ Architecture

### Database Schema

#### `recommendation_performance` Table
```sql
CREATE TABLE recommendation_performance (
    id INTEGER PRIMARY KEY,
    recommendation_id INTEGER UNIQUE,  -- Links to recommendations table
    entry_date DATETIME,
    entry_price FLOAT,
    
    -- Performance at different timeframes
    price_1d FLOAT,
    price_5d FLOAT,
    price_10d FLOAT,
    price_30d FLOAT,
    
    return_1d FLOAT,  -- Percentage returns
    return_5d FLOAT,
    return_10d FLOAT,
    return_30d FLOAT,
    
    -- Peak/trough tracking
    peak_price FLOAT,
    peak_return FLOAT,
    peak_date DATETIME,
    
    trough_price FLOAT,
    trough_return FLOAT,
    trough_date DATETIME,
    
    -- Status
    status VARCHAR(20),  -- 'tracking', 'completed', 'failed'
    days_tracked INTEGER,
    last_checked DATETIME,
    
    -- Win/loss flags
    is_winner_1d BOOLEAN,
    is_winner_5d BOOLEAN,
    is_winner_10d BOOLEAN,
    is_winner_30d BOOLEAN
);
```

#### Updated `recommendations` Table
```sql
ALTER TABLE recommendations ADD COLUMN strategy_type VARCHAR(50);
-- Values: 'momentum', 'dip', 'manual'
```

---

## 🔄 How It Works

### 1. **Recommendation Creation**
```python
# When bot generates recommendations
recommendations = bot.generate_recommendations(num_stocks=10)

# Automatically saves to DB and creates performance trackers
# → recommendations table (with entry price)
# → recommendation_performance table (tracking status)
```

### 2. **Daily Updates**
```bash
# Runs as part of daily_refresh.py
python scripts/daily_refresh.py

# Or standalone
python scripts/update_performance.py
```

**Update Logic:**
```python
for tracker in active_trackers:
    current_price = fetch_price(stock.ticker)
    days_since = (today - entry_date).days
    
    # Update specific timeframe
    if days_since >= 1: update 1-day stats
    if days_since >= 5: update 5-day stats
    if days_since >= 10: update 10-day stats
    if days_since >= 30:
        update 30-day stats
        mark as 'completed'
    
    # Track peak/trough
    if current_price > peak: update peak
    if current_price < trough: update trough
```

### 3. **Status Lifecycle**
```
tracking → (30 days pass) → completed
tracking → (price fetch fails) → failed
```

---

## 💻 Discord Commands

### `/performance [days] [strategy]`
View aggregate performance statistics

**Parameters:**
- `days` (optional): 7-365 days (default: 90)
- `strategy` (optional): 'all', 'momentum', 'dip' (default: all)

**Example:**
```
/performance days:90 strategy:momentum
```

**Output:**
```
📊 Bot Performance - Momentum

📈 5-Day Performance
Win Rate: 🟢 55.2%
Total Tracked: 42
Winners: 23
Avg Return: +2.34%
Avg Win: +5.12%
Avg Loss: -2.18%
Best: +18.45%
Worst: -7.23%

📊 30-Day Performance
Win Rate: 🟢 58.7%
Total Tracked: 35
Winners: 21
Avg Return: +3.67%
...

📝 Interpretation
✅ Strong performance! Recommendations are profitable on average.
```

---

### `/leaderboard [timeframe] [limit]`
View top and worst performing recommendations

**Parameters:**
- `timeframe` (optional): '5day' or '30day' (default: 30day)
- `limit` (optional): 1-25 stocks (default: 10)

**Example:**
```
/leaderboard timeframe:30day limit:10
```

**Output:**
```
🏆 Leaderboard - 30-Day

🟢 Top Performers
🥇 NVDA - NVIDIA Corporation
    Return: +24.75% | Score: 89/100
🥈 AMD - Advanced Micro Devic
    Return: +18.32% | Score: 85/100
🥉 TSLA - Tesla Inc
    Return: +15.67% | Score: 82/100
...

🔴 Worst Performers
1. INTC - Intel Corporation
    Return: -8.45% | Score: 75/100
...
```

---

## 📈 Metrics Explained

### Win Rate
```
Win Rate = (Number of Profitable Trades / Total Trades) × 100

Example: 23 wins out of 42 trades = 54.8% win rate
```

**Interpretation:**
- **> 55%**: Strong performance
- **50-55%**: Good performance
- **45-50%**: Acceptable (considering market randomness)
- **< 45%**: Needs improvement

### Average Return
```
Avg Return = Sum of all returns / Number of trades

Example: (5% + 3% + -2% + 8% + -1%) / 5 = 2.6%
```

**Interpretation:**
- **> 3%**: Excellent (especially for 30-day)
- **1-3%**: Good
- **0-1%**: Acceptable
- **< 0%**: Underperforming

### Peak/Trough
```
Peak: Highest price reached during tracking period
Trough: Lowest price reached during tracking period

Peak Return = ((Peak - Entry) / Entry) × 100
Trough Return = ((Trough - Entry) / Entry) × 100
```

**Use Case:**
- Shows potential profit if sold at optimal time
- Shows worst drawdown experienced
- Helps set stop-loss levels

---

## 🔧 Technical Implementation

### Database Methods

#### `create_performance_tracker()`
```python
db.create_performance_tracker(
    recommendation_id=123,
    entry_date=datetime.utcnow(),
    entry_price=150.50
)
```

#### `update_performance_tracker()`
```python
db.update_performance_tracker(
    recommendation_id=123,
    current_date=datetime.utcnow(),
    current_price=155.75
)
# Returns: Updated RecommendationPerformance object
```

#### `get_performance_stats()`
```python
stats = db.get_performance_stats(
    days=90,
    strategy_type='momentum'
)
# Returns: Dict with aggregate stats
```

#### `get_top_performers()`
```python
top = db.get_top_performers(
    limit=10,
    timeframe='30day'
)
# Returns: List[(Performance, Recommendation, Stock)]
```

---

## 🚀 Setup Instructions

### 1. Run Migration
```bash
cd /Users/himnish03/Documents/Projects/SmartInvest/smartinvest-bot
python scripts/migrate_add_performance_tracking.py
```

### 2. Restart Bot
```bash
# Stop existing bot
ps aux | grep bot_with_real_data.py
kill <PID>

# Start bot
python bot_with_real_data.py
```

### 3. Verify Setup
```discord
/performance
```

**Expected Output (if no data yet):**
```
ℹ️ No performance data available yet for the last 90 days.

Performance tracking is automatic! The bot tracks every recommendation it makes.

Start getting recommendations with /daily and check back after a few days.
```

---

## 📅 Daily Workflow

### Automatic (Recommended)
Performance updates run automatically as part of your daily cron job:

```bash
# Your existing cron job already includes performance updates
0 18 * * 1-5 cd /path/to/smartinvest-bot && /path/to/venv/bin/python scripts/daily_refresh.py
```

### Manual
```bash
# Run performance update only
python scripts/update_performance.py

# Or full data refresh (includes performance)
python scripts/daily_refresh.py
```

---

## 🎯 Use Cases

### 1. **Validate Bot Accuracy**
```
Question: Is my bot actually good at picking stocks?
Command: /performance days:90

Look for:
- Win rate > 50%
- Avg return > market return (~2-3% per month)
```

### 2. **Compare Strategies**
```
Question: Is momentum better than dip-buying?
Commands:
  /performance strategy:momentum
  /performance strategy:dip

Compare:
- Win rates
- Avg returns
- Best/worst trades
```

### 3. **Identify Best Picks**
```
Question: Which stocks does my bot pick best?
Command: /leaderboard

Look for:
- Consistent top performers (appear multiple times)
- High return + high original score = good model
- Low score but high return = lucky pick
```

### 4. **Improve Model**
```
Question: Why are some recommendations failing?
Command: /leaderboard limit:10

Analyze worst performers:
- What signals did the bot see?
- What went wrong?
- Should scoring weights change?
```

---

## 🧪 Testing

### Test Performance Update
```bash
# Generate test recommendations
python bot_with_real_data.py  # Let it generate recs via /daily

# Wait 1+ days
# Then update performance
python scripts/update_performance.py

# Check results
# In Discord: /performance
```

### Test Commands
```discord
# Test with no data
/performance

# Test with filters
/performance days:30 strategy:momentum

# Test leaderboard
/leaderboard timeframe:5day limit:5

# Test with invalid inputs
/performance days:999  # Should error: "choose between 7-365"
/leaderboard timeframe:invalid  # Should error
```

---

## 📊 Example Performance Report

```
Period: Last 90 days (Dec 15, 2024 - Mar 15, 2025)
Strategy: All
Total Recommendations: 87

5-Day Performance:
├─ Win Rate: 56.3% (49/87)
├─ Avg Return: +2.1%
├─ Best: NVDA +18.5%
└─ Worst: INTC -6.2%

30-Day Performance:
├─ Win Rate: 61.2% (41/67)  # 67 completed 30-day
├─ Avg Return: +4.3%
├─ Best: AMD +28.7%
└─ Worst: BA -9.8%

Interpretation:
✅ Strong performance! Bot beats market average.
   S&P 500 (same period): +2.8%
   SmartInvest: +4.3%
   Alpha: +1.5%
```

---

## 🛠️ Troubleshooting

### No Performance Data
**Problem:** `/performance` shows "No data available"

**Solutions:**
1. Generate recommendations: `/daily`
2. Wait 1+ days
3. Run update: `python scripts/update_performance.py`
4. Check again: `/performance`

### Performance Not Updating
**Problem:** Returns stay at 0% after several days

**Solutions:**
```bash
# 1. Check if update script ran
python scripts/update_performance.py

# 2. Check database
sqlite3 smartinvest.db
SELECT COUNT(*) FROM recommendation_performance WHERE status='tracking';

# 3. Check logs
tail -f logs/daily_refresh.log
```

### High Failure Rate
**Problem:** Many recommendations marked as 'failed'

**Possible Causes:**
- Yfinance API issues
- Delisted stocks
- Data gaps

**Solution:**
```python
# Check failed trackers
SELECT r.ticker, p.status, p.last_checked
FROM recommendation_performance p
JOIN recommendations rec ON p.recommendation_id = rec.id
JOIN stocks r ON rec.stock_id = r.id
WHERE p.status = 'failed';
```

---

## 🎓 Best Practices

### 1. **Wait for Sufficient Data**
- Don't judge performance after 1 week
- Wait for at least 30 completed 30-day tracks
- Compare to market benchmarks (S&P 500)

### 2. **Compare Timeframes**
```
Good bot:
5-day win rate: ~52-55%
30-day win rate: ~55-60% (should improve over time)

Why? Short-term noise vs. long-term signal
```

### 3. **Strategy Evaluation**
```python
# Run both strategies for 60 days
# Then compare:
/performance strategy:momentum
/performance strategy:dip

# Which has:
- Higher win rate?
- Better avg return?
- Lower worst loss?
```

### 4. **Continuous Improvement**
```
Every month:
1. Review /leaderboard
2. Analyze top performers (what signals worked?)
3. Analyze worst performers (what failed?)
4. Adjust scoring weights in models/scoring.py
5. Retrain ML model with new data
6. Repeat
```

---

## 📚 Related Documentation

- [`BACKTEST_COMMANDS.md`](./BACKTEST_COMMANDS.md) - Historical performance simulation
- [`SMARTINVEST_COMPLETE_GUIDE.md`](./SMARTINVEST_COMPLETE_GUIDE.md) - Full system docs
- [`BUY_THE_DIP_GUIDE.md`](./BUY_THE_DIP_GUIDE.md) - Dip strategy docs

---

## 🎉 Summary

**Performance Tracking gives you:**
- ✅ Objective measure of bot accuracy
- ✅ Data-driven strategy comparison
- ✅ Continuous improvement feedback loop
- ✅ Portfolio confidence metrics
- ✅ Zero manual effort (automatic)

**Next Steps:**
1. Run migration: `python scripts/migrate_add_performance_tracking.py`
2. Generate recommendations: `/daily`
3. Wait a few days
4. Check performance: `/performance`
5. See top picks: `/leaderboard`

**Questions?** Check the troubleshooting section or Discord support channel.

---

*Last Updated: January 2025*  
*SmartInvest Bot v2.1 - Performance Tracking Edition*

