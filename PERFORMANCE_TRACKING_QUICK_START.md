# 📊 Performance Tracking - Quick Start

**Track your bot's recommendation accuracy automatically!**

---

## 🚀 Setup (5 minutes)

### 1. Run Migration
```bash
cd /Users/himnish03/Documents/Projects/SmartInvest/smartinvest-bot
python scripts/migrate_add_performance_tracking.py
```

### 2. Restart Your Bot
```bash
# Find and kill running bot
ps aux | grep bot_with_real_data.py
kill <PID>

# Restart
python bot_with_real_data.py
```

### 3. Done! ✅
Performance tracking is now enabled and automatic.

---

## 💻 New Discord Commands

### `/performance [days] [strategy]`
View bot's recommendation performance stats

**Examples:**
```
/performance
/performance days:30
/performance days:90 strategy:momentum
/performance strategy:dip
```

### `/leaderboard [timeframe] [limit]`
See top and worst performing recommendations

**Examples:**
```
/leaderboard
/leaderboard timeframe:5day
/leaderboard timeframe:30day limit:15
```

---

## 🎯 How It Works

### Automatic Tracking
Every time your bot makes a recommendation (via `/daily`), it:
1. Saves the recommendation to database
2. Creates a performance tracker
3. Records entry price and date

### Daily Updates
Your existing `daily_refresh.py` cron job automatically updates performance:
- Fetches current prices
- Calculates returns (1d, 5d, 10d, 30d)
- Updates win/loss status
- Marks as completed after 30 days

### Zero Manual Work
Everything happens automatically. Just use `/performance` and `/leaderboard` to view results!

---

## 📈 What You'll See

### Example `/performance` Output
```
📊 Bot Performance - All Strategies
Tracking 87 recommendations over the last 90 days

📈 5-Day Performance
Win Rate: 🟢 56.3%
Total Tracked: 87
Winners: 49
Avg Return: +2.1%
Best: +18.5%
Worst: -6.2%

📊 30-Day Performance
Win Rate: 🟢 61.2%
Total Tracked: 67
Winners: 41
Avg Return: +4.3%
Best: +28.7%
Worst: -9.8%

📝 Interpretation
✅ Strong performance! Recommendations are profitable on average.
```

### Example `/leaderboard` Output
```
🏆 Leaderboard - 30-Day

🟢 Top Performers
🥇 NVDA - NVIDIA Corporation
    Return: +24.75% | Score: 89/100
🥈 AMD - Advanced Micro Devic
    Return: +18.32% | Score: 85/100
🥉 TSLA - Tesla Inc
    Return: +15.67% | Score: 82/100

🔴 Worst Performers
1. INTC - Intel Corporation
    Return: -8.45% | Score: 75/100
```

---

## ⏱️ Timeline

| Time | What Happens |
|------|-------------|
| **Day 0** | Bot generates recommendations, tracking starts |
| **Day 1** | 1-day returns calculated |
| **Day 5** | 5-day returns calculated |
| **Day 10** | 10-day returns calculated |
| **Day 30** | 30-day returns calculated, tracking completes |

**Note:** You need to wait at least 5 days before seeing meaningful performance data.

---

## 🎯 Use Cases

### 1. Validate Bot Accuracy
```
/performance days:90
```
Look for: Win rate > 50%, Avg return > market average

### 2. Compare Strategies
```
/performance strategy:momentum
/performance strategy:dip
```
See which strategy performs better

### 3. Find Best Picks
```
/leaderboard timeframe:30day
```
Identify stocks your bot consistently picks well

### 4. Spot Patterns
```
/leaderboard timeframe:5day
/leaderboard timeframe:30day
```
Compare short-term vs. long-term performance

---

## ❓ FAQ

**Q: When will I see performance data?**  
A: After your bot makes recommendations and 1+ days pass. Use `/daily` to generate recommendations.

**Q: What if `/performance` shows "No data available"?**  
A: Generate recommendations with `/daily`, wait 1+ days, then check again.

**Q: How often does performance update?**  
A: Automatically every day via your `daily_refresh.py` cron job.

**Q: Can I backfill historical recommendations?**  
A: No. Only new recommendations (after migration) are tracked. But backtesting (`/backtest`) shows historical performance!

**Q: What's the difference between `/backtest` and `/performance`?**  
- `/backtest`: Simulates past performance (historical what-if)
- `/performance`: Tracks actual live recommendations (real-time accuracy)

---

## 🛠️ Troubleshooting

### No data showing
```bash
# 1. Check if tracking is working
sqlite3 smartinvest.db
SELECT COUNT(*) FROM recommendation_performance;
# Should show > 0

# 2. Manually update performance
python scripts/update_performance.py

# 3. Check Discord
/performance
```

### Performance not updating
```bash
# Check if daily refresh includes performance update
grep "UPDATE PERFORMANCE" scripts/daily_refresh.py

# Manually trigger update
python scripts/update_performance.py
```

---

## 📚 Learn More

- **Full Documentation**: [`docs/PERFORMANCE_TRACKING.md`](docs/PERFORMANCE_TRACKING.md)
- **System Architecture**: [`docs/SMARTINVEST_COMPLETE_GUIDE.md`](docs/SMARTINVEST_COMPLETE_GUIDE.md)
- **Backtesting**: [`BACKTEST_QUICK_START.md`](BACKTEST_QUICK_START.md)

---

## ✅ Checklist

- [ ] Run migration script
- [ ] Restart Discord bot
- [ ] Use `/daily` to generate recommendations
- [ ] Wait 1+ days
- [ ] Use `/performance` to view stats
- [ ] Use `/leaderboard` to see top picks
- [ ] Check `/help` to see new commands listed

---

**🎉 You're all set! Performance tracking is now active.**

*Your bot will automatically track every recommendation it makes and show you how accurate it is over time.*

---

*Questions? Check the full docs or ask in Discord support channel.*

