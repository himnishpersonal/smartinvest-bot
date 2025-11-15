# 📊 Load Stock Data - Quick Guide

## 🚨 Your Current Issue

Your bot is running but says:
```
❌ No recommendations available. Make sure stocks are loaded in database.
```

**This is because your database is empty!**

I also fixed a bug in the bot code:
- ❌ **Before:** `get_all_stocks(limit=100)` - wrong parameter
- ✅ **After:** `get_all_stocks()` - correct

---

## ✅ **Solution: Load Test Data (2 Minutes)**

### **Step 1: Stop Your Bot**

In the terminal where your bot is running, press:
```
Ctrl + C
```

### **Step 2: Load Test Stocks**

Run this command:
```bash
cd /Users/himnish03/Documents/Projects/SmartInvest/smartinvest-bot
source venv/bin/activate
python load_test_data.py
```

**What this does:**
- Loads 5 stocks: AAPL, MSFT, GOOGL, NVDA, TSLA
- Fetches 1 year of price history for each
- Stores everything in your database
- Takes about 2 minutes

**Expected output:**
```
============================================================
Loading Test Stock Data
============================================================

Loading 5 stocks...

[1/5] AAPL... ✓ Loaded 252 days of data
[2/5] MSFT... ✓ Loaded 252 days of data
[3/5] GOOGL... ✓ Loaded 252 days of data
[4/5] NVDA... ✓ Loaded 252 days of data
[5/5] TSLA... ✓ Loaded 252 days of data

============================================================
✅ Successfully loaded: 5 stocks
❌ Failed: 0 stocks
============================================================

🎉 Success! Your bot now has data!
```

### **Step 3: Restart Your Bot**

```bash
python bot_with_real_data.py
```

You should see the same startup messages as before.

### **Step 4: Test in Discord**

Now try these commands:

#### **Test 1: `/stock AAPL`**
```
/stock AAPL
```

Should show:
- ✅ REAL current price
- ✅ REAL technical score (RSI, MACD, etc.)
- ✅ REAL fundamental score (P/E, ROE, etc.)
- ✅ Key signals based on real data

#### **Test 2: `/daily`**
```
/daily
```

Should show:
- ✅ Top 5 recommendations (you only have 5 stocks)
- ✅ Each with real prices and scores
- ✅ Ranked by analysis

---

## 🔄 **If You Get Rate Limited**

If you see errors like:
```
429 Too Many Requests
```

**This means Yahoo Finance is rate limiting you.**

**Solution:**
1. Wait 1 hour
2. Try running `load_test_data.py` again

**Why this happens:**
- You've made too many requests to Yahoo Finance recently
- The limit resets after ~1 hour
- This is normal when testing

---

## 📊 **What Gets Loaded**

For each stock, the script loads:

| Data Type | What It Is | Example |
|-----------|------------|---------|
| **Company Info** | Name, sector, industry | Apple Inc., Technology |
| **Price History** | 1 year of daily prices | 252 trading days |
| **OHLCV Data** | Open, High, Low, Close, Volume | For technical analysis |

**This is enough for:**
- ✅ `/stock` command to work
- ✅ `/daily` recommendations
- ✅ Technical analysis (RSI, MACD, etc.)
- ✅ Price charts and trends

**Not included yet (optional):**
- ⚠️ Fundamentals (P/E, ROE) - fetched on-demand
- ⚠️ News articles - optional enhancement
- ⚠️ ML model - optional enhancement

---

## 🚀 **Quick Commands Summary**

```bash
# 1. Stop bot (if running)
Ctrl + C

# 2. Load data
python load_test_data.py

# 3. Restart bot
python bot_with_real_data.py

# 4. Test in Discord
/stock AAPL
/daily
```

---

## 📈 **Want More Stocks?**

### **Option A: Add More Manually**

Edit `load_test_data.py` and change line 18:
```python
# Add more tickers here
test_stocks = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA', 'AMZN', 'META', 'NFLX']
```

Then run it again.

### **Option B: Load Full S&P 500**

```bash
python scripts/load_full_data.py
```

**Warning:** Takes 25-30 minutes and loads ~500 stocks!

---

## ✅ **Verification**

After loading data, verify it worked:

```bash
python -c "
from data.storage import DatabaseManager
from config import Config

db = DatabaseManager(Config().DATABASE_URL)
stocks = db.get_all_stocks()
print(f'✅ Database has {len(stocks)} stocks')

for stock in stocks[:5]:
    print(f'  - {stock.ticker}: {stock.company_name}')
"
```

Should output:
```
✅ Database has 5 stocks
  - AAPL: Apple Inc.
  - MSFT: Microsoft Corporation
  - GOOGL: Alphabet Inc.
  - NVDA: NVIDIA Corporation
  - TSLA: Tesla, Inc.
```

---

## 🐛 **Troubleshooting**

### **"No module named 'data'"**
**Fix:** Make sure you're in the right directory and venv is activated:
```bash
cd /Users/himnish03/Documents/Projects/SmartInvest/smartinvest-bot
source venv/bin/activate
```

### **"429 Too Many Requests"**
**Fix:** Wait 1 hour, Yahoo Finance is rate limiting you.

### **"Connection timeout"**
**Fix:** Check your internet connection.

### **Bot still says "No stocks"**
**Fix:** 
1. Verify data loaded (use verification script above)
2. Restart the bot
3. Wait 30 seconds for bot to fully start

---

## 🎯 **What's Next?**

After loading data:

1. ✅ **Bot works with real data**
2. ✅ **Can analyze stocks**
3. ✅ **Can generate recommendations**

**Optional enhancements (later):**
- 📰 Add news sentiment (`python scripts/fetch_news_sentiment.py`)
- 🤖 Train ML model (`python scripts/train_model.py`)
- 📊 Load more stocks (`python scripts/load_full_data.py`)

**But you don't need these to start using the bot!**

---

## 🎉 **Ready!**

Run these 3 commands:

```bash
# 1. Load data
python load_test_data.py

# 2. Start bot
python bot_with_real_data.py

# 3. Test in Discord
/stock AAPL
```

Your bot will now show REAL analysis! 🚀

