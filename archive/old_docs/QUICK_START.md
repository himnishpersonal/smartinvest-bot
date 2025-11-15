# SmartInvest Bot - Quick Start Guide

## ✅ What You Have Already
- ✅ Python 3.13 installed
- ✅ Virtual environment created and activated
- ✅ All dependencies installed
- ✅ `.env` file configured with Discord token, channel ID, and NewsAPI key
- ✅ Database (SQLite) configured

## 🚀 Next Steps to Launch Your Bot

### Step 1: Initialize the Database (1 minute)

Create the database tables:

```bash
python -c "
from data.database import create_tables, get_engine
from config import Config

config = Config()
engine = get_engine(config.DATABASE_URL)
create_tables(engine)
print('✅ Database tables created!')
"
```

### Step 2: Test Basic Components (2 minutes)

Run the manual test script to verify everything works:

```bash
python scripts/test_pipeline.py
```

This will test:
- Data collection from Yahoo Finance
- News fetching (if configured)
- Basic functionality

### Step 3: Launch the Bot (NOW!)

Start your Discord bot:

```bash
python bot.py
```

You should see:
```
SmartInvestBot#1234 has connected to Discord!
Bot is in 1 guild(s)
```

### Step 4: Test in Discord

Go to your Discord channel and try these commands:

1. **`/help`** - See all available commands
2. **`/daily`** - View today's recommendations (placeholder data for now)
3. **`/stock AAPL`** - Analyze Apple stock
4. **`/compare AAPL MSFT`** - Compare two stocks
5. **`/refresh`** - Trigger analysis

## 📊 Loading Real Data (Optional - Takes 10-20 minutes)

To get real stock recommendations, you need to:

### 1. Load Stock Universe and Historical Data

Create a data loading script:

```bash
cat > scripts/load_initial_data.py << 'EOF'
#!/usr/bin/env python3
"""Load initial stock data"""
import sys
sys.path.insert(0, '.')

from config import Config
from data.storage import DatabaseManager
from data.collectors import StockDataCollector
from data.pipeline import get_sp500_tickers

print("Loading S&P 500 stock data...")

config = Config()
db_manager = DatabaseManager(config.DATABASE_URL)
collector = StockDataCollector()

# Get S&P 500 tickers
tickers = get_sp500_tickers()
print(f"Found {len(tickers)} tickers")

# Load first 50 for testing (faster)
test_tickers = tickers[:50]

for i, ticker in enumerate(test_tickers, 1):
    print(f"[{i}/{len(test_tickers)}] Loading {ticker}...")
    try:
        # Fetch historical data
        df = collector.fetch_price_history(ticker, period='1y')
        
        # Get company info
        info = collector.fetch_company_info(ticker)
        
        # Add to database
        stock = db_manager.add_stock(
            ticker=ticker,
            company_name=info.get('company_name', ticker),
            sector=info.get('sector', 'Unknown'),
            industry=info.get('industry', 'Unknown')
        )
        
        # Add price data
        if not df.empty:
            db_manager.bulk_insert_prices(stock.id, df)
        
        print(f"  ✓ {ticker} loaded")
    except Exception as e:
        print(f"  ✗ {ticker} failed: {e}")

print("\n✅ Initial data loaded!")
EOF

chmod +x scripts/load_initial_data.py
python scripts/load_initial_data.py
```

### 2. Train ML Model (Optional - Advanced)

This requires more data and time. For now, the bot works with placeholder scores.

## 🎯 Current Bot Features

Right now, your bot can:
- ✅ Respond to slash commands
- ✅ Display formatted stock information
- ✅ Create beautiful Discord embeds
- ✅ Fetch real-time stock prices from Yahoo Finance
- ✅ Handle errors gracefully

## 🔧 Troubleshooting

### Bot doesn't come online
- Check your Discord bot token in `.env`
- Make sure bot has proper permissions in Discord
- Verify bot is added to your server

### Commands don't appear
- Wait ~1 minute for Discord to sync slash commands
- Try leaving and rejoining the server
- Check bot has "applications.commands" scope

### Database errors
- Make sure you ran the database initialization (Step 1)
- Check DATABASE_URL in `.env`

## 📝 What's Next?

1. **Get bot running** - Follow Steps 1-4 above
2. **Test commands** - Try all slash commands in Discord
3. **Load real data** (optional) - Run data loading script
4. **Train ML model** (optional) - For real recommendations
5. **Customize** - Add your own features!

## 🎮 Commands Available Now

- `/help` - See all commands
- `/daily` - Top 10 recommendations (sample data)
- `/stock <ticker>` - Analyze any stock
- `/compare <ticker1> <ticker2>` - Compare stocks
- `/refresh` - Trigger analysis
- `/performance` - View track record
- `/watchlist` - Manage watchlist (coming soon)

## 🚨 Important Notes

- Bot uses **SQLite** (perfect for personal use)
- **No ML model yet** = placeholder scores (still useful!)
- **NewsAPI** has rate limits (500 requests/day free tier)
- Bot will run **scheduled analysis at 9:30 AM ET** on weekdays

---

**Ready to launch?** Just run: `python bot.py`

