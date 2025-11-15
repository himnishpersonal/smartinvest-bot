# SmartInvest Bot - Expansion Plan

**Goal:** Scale from 100 to 500+ stocks with enhanced features  
**Timeline:** 4-6 weeks  
**Priority:** High Impact → Low Effort First

---

## Phase 1: Scale to 500 Stocks (Week 1)

### 1.1 Load Additional Stocks

**Current:** 100 S&P 100 stocks  
**Target:** 500 stocks (S&P 500 + popular stocks)

#### Action Plan

```bash
# Step 1: Update stock loader to handle S&P 500
# Modify load_incremental.py

# Step 2: Load in batches (avoid rate limits)
# Batch 1: S&P 100 (already done) ✓
# Batch 2: Next 100 stocks (Mon)
# Batch 3: Next 100 stocks (Tue)
# Batch 4: Next 100 stocks (Wed)
# Batch 5: Next 100 stocks (Thu)
# Batch 6: Remaining stocks (Fri)

# Each batch takes ~20 minutes
python load_incremental.py  # Interactive: "How many to add?"
```

#### Rate Limit Strategy

```
API Limits:
- yfinance: ~2000/hour → Can load 100 stocks/hour
- FMP: 250/day → BOTTLENECK!
- NewsAPI: 500/day → BOTTLENECK!

Solution:
1. Spread loading over 5 days (100 stocks/day)
2. Use yfinance only (skip FMP for now)
3. Collect news for top 100 only (by market cap)
```

#### Database Impact

```
Before: ~5 MB
After:  ~25 MB (500 stocks × 250 days × 5 fields)
Query Time: Still <100ms (SQLite handles this fine)
```

### 1.2 Optimize Data Storage

**Problem:** 500 stocks = 5x data = 5x slower queries

**Solutions:**

1. **Add Database Indexes**
```sql
CREATE INDEX idx_prices_stock_id ON stock_prices(stock_id);
CREATE INDEX idx_prices_date ON stock_prices(date);
CREATE INDEX idx_news_stock_id ON news_articles(stock_id);
```

2. **Implement Data Pruning**
```python
# Keep only last 2 years of price data
# Delete prices older than 730 days
def prune_old_data():
    cutoff = datetime.now() - timedelta(days=730)
    session.query(StockPrice).filter(
        StockPrice.date < cutoff
    ).delete()
```

3. **Add Data Compression**
```python
# Store prices as INT (multiply by 100)
# 175.43 → 17543 (saves 50% space)
```

---

## Phase 2: Automated Daily Refresh (Week 2)

### 2.1 Implement Auto-Update System

**Goal:** Bot updates data every morning before market open

#### Option A: Cron Jobs (Linux/Mac)

```bash
# Edit crontab
crontab -e

# Daily at 6 AM ET (before market): Update prices
0 6 * * 1-5 cd /path/to/smartinvest-bot && venv/bin/python scripts/daily_price_update.py

# Daily at 7 AM ET: Update news for top 100
0 7 * * 1-5 cd /path/to/smartinvest-bot && venv/bin/python scripts/daily_news_update.py

# Daily at 8 AM ET: Retrain model
0 8 * * 1-5 cd /path/to/smartinvest-bot && venv/bin/python scripts/train_model_v2.py

# Daily at 8:30 AM ET: Restart bot
30 8 * * 1-5 sudo systemctl restart smartinvest-bot
```

#### Option B: Internal Bot Scheduler (Recommended)

```python
# Add to bot_with_real_data.py

@tasks.loop(time=time(hour=6, minute=0, tzinfo=pytz.timezone('America/New_York')))
async def daily_price_update(self):
    """Update prices every morning at 6 AM ET"""
    if datetime.now(et_tz).weekday() >= 5:  # Skip weekends
        return
    
    logger.info("Starting daily price update...")
    
    # Update only last 5 days (faster)
    stocks = self.db_manager.get_all_stocks()
    for stock in stocks:
        try:
            df = self.stock_collector.fetch_price_history(
                stock.ticker, 
                period='5d'
            )
            self.db_manager.bulk_insert_prices(stock.id, df)
        except:
            continue
    
    logger.info("Daily price update complete!")

@tasks.loop(time=time(hour=7, minute=0, tzinfo=pytz.timezone('America/New_York')))
async def daily_news_update(self):
    """Update news every morning at 7 AM ET"""
    # Similar logic for news...

@tasks.loop(time=time(hour=8, minute=0, tzinfo=pytz.timezone('America/New_York')))
async def daily_model_retrain(self):
    """Retrain model every morning at 8 AM ET"""
    # Call training script...
```

### 2.2 Create Incremental Update Scripts

**File:** `scripts/daily_price_update.py`
```python
"""
Update only last 5 days of prices (fast!)
Runtime: ~2-3 minutes for 500 stocks
"""
def update_recent_prices():
    stocks = db.get_all_stocks()
    
    for stock in stocks:
        # Get last 5 days only
        df = yf.download(stock.ticker, period='5d')
        
        # Update or insert
        for date, row in df.iterrows():
            db.upsert_price(stock.id, date, row)
```

**File:** `scripts/daily_news_update.py`
```python
"""
Update news for top 100 stocks by market cap
Runtime: ~10 minutes (100 stocks, 5 articles each)
"""
def update_daily_news():
    # Get top 100 by market cap
    stocks = db.get_top_stocks(limit=100)
    
    for stock in stocks:
        # Only fetch yesterday's news
        articles = news_collector.fetch_stock_news(
            stock.ticker,
            days_back=1
        )
        # Analyze and store...
```

### 2.3 Implement Health Checks

```python
# Add to bot
@tasks.loop(minutes=30)
async def health_check(self):
    """Monitor bot health"""
    checks = {
        'database': self.check_database(),
        'ml_model': self.check_model(),
        'data_freshness': self.check_data_age(),
    }
    
    if not all(checks.values()):
        # Send alert to Discord admin channel
        await self.admin_channel.send(
            f"⚠️ Health Check Failed: {checks}"
        )
```

---

## Phase 3: Enhanced Discord Commands (Week 3)

### 3.1 New Command: Watchlist

```python
@bot.tree.command(name="watchlist")
@app_commands.describe(
    action="add, remove, list, or check",
    ticker="Stock ticker (for add/remove)"
)
async def watchlist_command(
    interaction: discord.Interaction, 
    action: str, 
    ticker: str = None
):
    """
    Manage your personal watchlist
    
    Examples:
      /watchlist add AAPL
      /watchlist list
      /watchlist check  (scores your watchlist only)
    """
    user_id = interaction.user.id
    
    if action == "add":
        db.add_to_watchlist(user_id, ticker)
        await interaction.response.send_message(
            f"✅ Added {ticker} to your watchlist"
        )
    
    elif action == "list":
        tickers = db.get_watchlist(user_id)
        await interaction.response.send_message(
            f"📋 Your Watchlist: {', '.join(tickers)}"
        )
    
    elif action == "check":
        # Score only watchlist stocks
        tickers = db.get_watchlist(user_id)
        scores = [bot.score_stock_simple(t) for t in tickers]
        # Display...
```

### 3.2 New Command: Compare

```python
@bot.tree.command(name="compare")
@app_commands.describe(
    ticker1="First stock",
    ticker2="Second stock"
)
async def compare_command(
    interaction: discord.Interaction,
    ticker1: str,
    ticker2: str
):
    """
    Compare two stocks side-by-side
    
    Example: /compare AAPL MSFT
    """
    score1 = bot.score_stock_simple(ticker1)
    score2 = bot.score_stock_simple(ticker2)
    
    embed = discord.Embed(title=f"{ticker1} vs {ticker2}")
    embed.add_field(
        name=ticker1,
        value=f"Score: {score1['overall_score']}\nPrice: ${score1['price']}",
        inline=True
    )
    embed.add_field(
        name=ticker2,
        value=f"Score: {score2['overall_score']}\nPrice: ${score2['price']}",
        inline=True
    )
    
    winner = ticker1 if score1['overall_score'] > score2['overall_score'] else ticker2
    embed.add_field(
        name="Winner",
        value=f"🏆 {winner}",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)
```

### 3.3 New Command: Alert

```python
@bot.tree.command(name="alert")
@app_commands.describe(
    action="set or list",
    ticker="Stock ticker",
    condition="score_above, score_below, price_above, price_below",
    value="Threshold value"
)
async def alert_command(
    interaction: discord.Interaction,
    action: str,
    ticker: str = None,
    condition: str = None,
    value: float = None
):
    """
    Set price or score alerts
    
    Examples:
      /alert set AAPL score_above 80
      /alert set TSLA price_below 150
      /alert list
    """
    if action == "set":
        db.create_alert(
            user_id=interaction.user.id,
            ticker=ticker,
            condition=condition,
            value=value
        )
        await interaction.response.send_message(
            f"🔔 Alert set: {ticker} {condition} {value}"
        )
    
    elif action == "list":
        alerts = db.get_user_alerts(interaction.user.id)
        # Display...

# Check alerts daily
@tasks.loop(minutes=15)
async def check_alerts(self):
    """Check user alerts every 15 minutes"""
    active_alerts = db.get_active_alerts()
    
    for alert in active_alerts:
        current_score = self.score_stock_simple(alert.ticker)
        
        if alert.condition == "score_above" and current_score['overall_score'] > alert.value:
            user = await self.fetch_user(alert.user_id)
            await user.send(
                f"🔔 Alert triggered: {alert.ticker} score is {current_score['overall_score']} (above {alert.value})"
            )
            db.mark_alert_triggered(alert.id)
```

### 3.4 New Command: Sector

```python
@bot.tree.command(name="sector")
@app_commands.describe(sector="Technology, Healthcare, Finance, etc.")
async def sector_command(interaction: discord.Interaction, sector: str):
    """
    Get top stocks in a specific sector
    
    Example: /sector Technology
    """
    stocks = db.get_stocks_by_sector(sector)
    scores = [bot.score_stock_simple(s.ticker) for s in stocks]
    scores.sort(key=lambda x: x['overall_score'], reverse=True)
    
    # Display top 10 in sector...
```

### 3.5 New Command: Portfolio

```python
@bot.tree.command(name="portfolio")
@app_commands.describe(
    action="add, remove, list, or performance",
    ticker="Stock ticker",
    shares="Number of shares",
    buy_price="Purchase price"
)
async def portfolio_command(
    interaction: discord.Interaction,
    action: str,
    ticker: str = None,
    shares: float = None,
    buy_price: float = None
):
    """
    Track your portfolio performance
    
    Examples:
      /portfolio add AAPL 10 150.00
      /portfolio list
      /portfolio performance
    """
    if action == "add":
        db.add_portfolio_position(
            user_id=interaction.user.id,
            ticker=ticker,
            shares=shares,
            buy_price=buy_price
        )
    
    elif action == "performance":
        positions = db.get_portfolio(interaction.user.id)
        total_gain = 0
        
        for pos in positions:
            current_price = bot.get_current_price(pos.ticker)
            gain = (current_price - pos.buy_price) * pos.shares
            total_gain += gain
        
        # Display beautiful performance report...
```

---

## Phase 4: Data Consolidation (Week 4)

### 4.1 Implement Data Aggregation Tables

**Goal:** Pre-calculate common queries for speed

```sql
-- Daily stock snapshots (pre-calculated scores)
CREATE TABLE daily_snapshots (
    id INTEGER PRIMARY KEY,
    stock_id INTEGER,
    date DATE,
    ml_score INTEGER,
    price FLOAT,
    volume BIGINT,
    sentiment_score FLOAT,
    created_at DATETIME,
    UNIQUE(stock_id, date)
);

-- Sector performance (pre-aggregated)
CREATE TABLE sector_performance (
    id INTEGER PRIMARY KEY,
    sector VARCHAR(100),
    date DATE,
    avg_score FLOAT,
    stock_count INTEGER,
    top_performer VARCHAR(10),
    created_at DATETIME
);
```

### 4.2 Create Materialized Views

```python
# scripts/consolidate_data.py

def create_daily_snapshot():
    """
    Run daily after market close
    Pre-calculate all scores and store
    """
    stocks = db.get_all_stocks()
    today = datetime.now().date()
    
    for stock in stocks:
        score = bot.score_stock_simple(stock.ticker)
        
        db.create_snapshot(
            stock_id=stock.id,
            date=today,
            ml_score=score['overall_score'],
            price=score['price'],
            sentiment_score=score['sentiment_score']
        )
    
    # Now /daily queries this table instead of calculating!
```

### 4.3 Implement Data Archiving

```python
def archive_old_data():
    """
    Move data older than 2 years to archive
    """
    cutoff = datetime.now() - timedelta(days=730)
    
    # Export to CSV
    old_prices = db.get_prices_before(cutoff)
    old_prices.to_csv('archive/prices_2023.csv')
    
    # Delete from main DB
    db.delete_prices_before(cutoff)
    
    # Database now stays <50 MB
```

---

## Phase 5: Advanced Technical Indicators (Week 5)

### 5.1 Add More Features (Expand from 8 to 20+)

```python
# Current: 8 features
# Target: 20+ features

NEW TECHNICAL INDICATORS:
9.  rsi_14          : Relative Strength Index
10. macd_histogram  : MACD momentum
11. bb_width        : Bollinger Band width (volatility)
12. adx_14          : Average Directional Index (trend strength)
13. stochastic_k    : Stochastic oscillator
14. obv_slope       : On-Balance Volume trend
15. atr_14          : Average True Range
16. williams_r      : Williams %R
17. cci_20          : Commodity Channel Index

NEW FUNDAMENTAL INDICATORS:
18. pe_ratio        : Price-to-Earnings
19. debt_ratio      : Debt-to-Equity
20. profit_margin   : Net profit margin

NEW SENTIMENT INDICATORS:
21. sentiment_trend : Change in sentiment last 7 days
22. news_volume     : Number of articles (attention metric)
```

### 5.2 Implement Advanced Technical Analysis

**File:** `features/technical_advanced.py`

```python
import pandas_ta as ta

class AdvancedTechnicalFeatures:
    def calculate_rsi(self, df, period=14):
        """Relative Strength Index"""
        return ta.rsi(df['close'], length=period)
    
    def calculate_macd(self, df):
        """MACD with histogram"""
        macd = ta.macd(df['close'])
        return {
            'macd': macd['MACD_12_26_9'],
            'signal': macd['MACDs_12_26_9'],
            'histogram': macd['MACDh_12_26_9']
        }
    
    def calculate_bollinger_bands(self, df, period=20):
        """Bollinger Bands"""
        bb = ta.bbands(df['close'], length=period)
        width = (bb['BBU_20_2.0'] - bb['BBL_20_2.0']) / bb['BBM_20_2.0']
        return {
            'upper': bb['BBU_20_2.0'],
            'lower': bb['BBL_20_2.0'],
            'width': width  # Volatility measure
        }
    
    def calculate_all(self, df):
        """Calculate all indicators"""
        return {
            'rsi': self.calculate_rsi(df),
            'macd': self.calculate_macd(df),
            'bb': self.calculate_bollinger_bands(df),
            # ... more
        }
```

### 5.3 Retrain Model with New Features

```bash
# After adding new features:
python scripts/train_model_v2.py

# Expected improvement: 84% → 87-90% accuracy
```

---

## Phase 6: Backtesting System (Week 6)

### 6.1 Implement Historical Performance Tracking

**File:** `models/backtesting.py`

```python
class Backtester:
    def __init__(self, db_manager, model):
        self.db = db_manager
        self.model = model
    
    def backtest(self, start_date, end_date, top_n=10):
        """
        Simulate trading strategy:
        1. Each day, get top N recommendations
        2. "Buy" them (track hypothetically)
        3. Hold for 5 days
        4. Calculate return
        """
        results = []
        current_date = start_date
        
        while current_date < end_date:
            # Get recommendations for this day
            recommendations = self.get_daily_recommendations(current_date, top_n)
            
            # Check returns 5 days later
            for stock in recommendations:
                price_buy = self.get_price(stock, current_date)
                price_sell = self.get_price(stock, current_date + timedelta(days=5))
                
                returns = (price_sell - price_buy) / price_buy
                results.append({
                    'date': current_date,
                    'ticker': stock,
                    'return': returns
                })
            
            current_date += timedelta(days=1)
        
        return self.calculate_metrics(results)
    
    def calculate_metrics(self, results):
        """Calculate backtest performance"""
        df = pd.DataFrame(results)
        
        return {
            'total_trades': len(df),
            'win_rate': (df['return'] > 0).sum() / len(df),
            'avg_return': df['return'].mean(),
            'total_return': (1 + df['return']).prod() - 1,
            'sharpe_ratio': df['return'].mean() / df['return'].std() * np.sqrt(252),
            'max_drawdown': self.calculate_max_drawdown(df)
        }
```

### 6.2 Add Backtest Command

```python
@bot.tree.command(name="backtest")
@app_commands.describe(months="Number of months to backtest")
async def backtest_command(interaction: discord.Interaction, months: int = 3):
    """
    Show historical performance of bot's strategy
    
    Example: /backtest 6  (test last 6 months)
    """
    await interaction.response.defer()  # This takes time
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months * 30)
    
    backtester = Backtester(bot.db_manager, bot.ml_model)
    results = backtester.backtest(start_date, end_date, top_n=10)
    
    embed = discord.Embed(
        title=f"📊 Backtest Results ({months} months)",
        color=discord.Color.green()
    )
    embed.add_field(name="Total Trades", value=results['total_trades'])
    embed.add_field(name="Win Rate", value=f"{results['win_rate']:.1%}")
    embed.add_field(name="Avg Return", value=f"{results['avg_return']:.2%}")
    embed.add_field(name="Total Return", value=f"{results['total_return']:.1%}")
    embed.add_field(name="Sharpe Ratio", value=f"{results['sharpe_ratio']:.2f}")
    
    await interaction.followup.send(embed=embed)
```

---

## Phase 7: Options Analysis (Bonus - Week 7+)

### 7.1 Collect Options Data

**Challenge:** Options data is expensive/hard to get

**Solutions:**
1. Yahoo Finance (delayed, free)
2. TDAmeritrade API (free with account)
3. Polygon.io (paid, $200/month)

```python
# Example: Using yfinance for options
import yfinance as yf

ticker = yf.Ticker("AAPL")
options_dates = ticker.options  # Available expiration dates

# Get options chain
opt_chain = ticker.option_chain('2025-11-15')
calls = opt_chain.calls
puts = opt_chain.puts

# Analyze unusual activity
unusual_volume = calls[calls['volume'] > calls['volume'].mean() * 3]
```

### 7.2 Options Features

```python
class OptionsAnalyzer:
    def calculate_put_call_ratio(self, ticker):
        """
        Put/Call ratio indicator
        High ratio = bearish sentiment
        Low ratio = bullish sentiment
        """
        chain = yf.Ticker(ticker).option_chain(self.get_nearest_expiry())
        
        put_volume = chain.puts['volume'].sum()
        call_volume = chain.calls['volume'].sum()
        
        ratio = put_volume / call_volume
        return ratio
    
    def find_unusual_activity(self, ticker):
        """
        Find options with unusual volume
        (volume > 3x average = possible big move)
        """
        chain = yf.Ticker(ticker).option_chain(self.get_nearest_expiry())
        
        calls = chain.calls
        calls['unusual'] = calls['volume'] > calls['volume'].mean() * 3
        
        return calls[calls['unusual']]
```

### 7.3 Add Options Command

```python
@bot.tree.command(name="options")
@app_commands.describe(ticker="Stock ticker")
async def options_command(interaction: discord.Interaction, ticker: str):
    """
    Analyze options activity
    
    Example: /options AAPL
    """
    analyzer = OptionsAnalyzer()
    
    # Get metrics
    pc_ratio = analyzer.calculate_put_call_ratio(ticker)
    unusual = analyzer.find_unusual_activity(ticker)
    
    embed = discord.Embed(title=f"📈 {ticker} Options Analysis")
    embed.add_field(
        name="Put/Call Ratio",
        value=f"{pc_ratio:.2f} {'🐻 Bearish' if pc_ratio > 1 else '🐂 Bullish'}"
    )
    
    if len(unusual) > 0:
        embed.add_field(
            name="⚡ Unusual Activity Detected",
            value=f"{len(unusual)} options with high volume",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)
```

---

## Implementation Timeline

### Week 1: Scale to 500 Stocks
- [ ] Monday: Load 100 more stocks
- [ ] Tuesday: Load 100 more stocks
- [ ] Wednesday: Load 100 more stocks
- [ ] Thursday: Load 100 more stocks
- [ ] Friday: Load remaining stocks
- [ ] Saturday: Fetch news for all
- [ ] Sunday: Retrain model

### Week 2: Auto-Refresh System
- [ ] Monday: Implement cron jobs
- [ ] Tuesday: Create incremental update scripts
- [ ] Wednesday: Add health checks
- [ ] Thursday: Test automation
- [ ] Friday: Deploy to production

### Week 3: New Commands
- [ ] Monday-Tuesday: Watchlist command
- [ ] Wednesday: Compare & Alert commands
- [ ] Thursday: Sector & Portfolio commands
- [ ] Friday: Testing & debugging

### Week 4: Data Consolidation
- [ ] Monday: Create snapshot tables
- [ ] Tuesday: Implement aggregation
- [ ] Wednesday: Add archiving
- [ ] Thursday: Optimize queries
- [ ] Friday: Performance testing

### Week 5: Advanced Indicators
- [ ] Monday-Tuesday: Add 12 new features
- [ ] Wednesday: Test feature calculations
- [ ] Thursday: Retrain model
- [ ] Friday: Compare performance

### Week 6: Backtesting
- [ ] Monday-Wednesday: Build backtesting engine
- [ ] Thursday: Add backtest command
- [ ] Friday: Generate reports

### Week 7+: Options (Optional)
- [ ] As time permits

---

## Success Metrics

```
✅ Phase 1: 500 stocks loaded
✅ Phase 2: Daily auto-refresh working (zero downtime)
✅ Phase 3: 5 new commands working
✅ Phase 4: Query time <100ms for /daily
✅ Phase 5: Model accuracy 87%+ (up from 84%)
✅ Phase 6: Backtest shows positive returns
✅ Phase 7: Options data collecting
```

---

**End of Expansion Plan**

