# SmartInvest Bot - Complete Technical Documentation

**Version:** 1.0  
**Last Updated:** October 27, 2025  
**Author:** Himnish

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Data Pipeline](#data-pipeline)
4. [Machine Learning Model](#machine-learning-model)
5. [Discord Bot](#discord-bot)
6. [Database Schema](#database-schema)
7. [API Integrations](#api-integrations)
8. [Deployment](#deployment)
9. [Troubleshooting](#troubleshooting)

---

## 1. System Overview

### Purpose
SmartInvest is an AI-powered Discord bot that provides stock recommendations using machine learning, technical analysis, and sentiment analysis.

### Key Features
- **ML-Powered Recommendations**: 84% accuracy XGBoost classifier
- **Sentiment Analysis**: FinBERT-based news sentiment scoring
- **Real-Time Data**: yfinance, FMP, and Finnhub integration
- **Discord Interface**: Slash commands for easy access
- **Automated Updates**: Daily analysis at market open

### Technology Stack
```
Backend:        Python 3.13
ML Framework:   XGBoost, scikit-learn
NLP:            Transformers (FinBERT)
Database:       SQLite (SQLAlchemy ORM)
Bot Framework:  discord.py
APIs:           yfinance, FMP, Finnhub, NewsAPI
```

---

## 2. Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     DATA SOURCES                             │
│  yfinance  │  FMP API  │  Finnhub  │  NewsAPI              │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│                  DATA COLLECTORS                             │
│  StockDataCollector  │  NewsCollector  │  SentimentAnalyzer │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│                    DATABASE (SQLite)                         │
│  stocks  │  stock_prices  │  news_articles  │  others       │
└──────────────────┬──────────────────────────────────────────┘
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
┌─────────────────┐  ┌─────────────────┐
│  ML TRAINING    │  │  DISCORD BOT    │
│  train_model    │  │  (24/7 running) │
│  (Weekly)       │  │                 │
└─────────┬───────┘  └────────┬────────┘
          │                   │
          ▼                   ▼
┌─────────────────┐  ┌─────────────────┐
│  SAVED MODEL    │→ │   /daily        │
│  (stock_model   │  │   /stock        │
│   _v1.pkl)      │  │   /refresh      │
└─────────────────┘  └─────────────────┘
```

### Directory Structure

```
smartinvest-bot/
├── config.py                 # Configuration management
├── bot_with_real_data.py    # Main Discord bot
│
├── data/
│   ├── schema.py            # Database models (SQLAlchemy)
│   ├── storage.py           # Database operations
│   ├── collectors.py        # API data collection
│   └── pipeline.py          # Data pipeline orchestration
│
├── features/
│   ├── technical.py         # Technical indicators
│   ├── fundamental.py       # Fundamental analysis
│   └── sentiment.py         # Sentiment feature engineering
│
├── models/
│   ├── feature_pipeline.py  # Feature preparation
│   ├── training.py          # ML training logic
│   ├── scoring.py           # Stock scoring engine
│   └── saved_models/        # Trained models
│       ├── stock_model_v1.pkl
│       └── model_latest.pkl → stock_model_v1.pkl
│
├── scripts/
│   ├── train_model_v2.py           # ML training script
│   └── fetch_news_sentiment.py     # News collection script
│
├── load_sp100.py            # S&P 100 data loader
├── load_incremental.py      # Incremental stock loader
└── smartinvest_dev.db       # SQLite database
```

---

## 3. Data Pipeline

### 3.1 Data Collection Flow

```
1. STOCK DATA LOADING (Weekly)
   ├─ Source: yfinance (primary), FMP (backup)
   ├─ Frequency: Weekly or as needed
   ├─ Script: load_sp100.py
   └─ Data: 1 year OHLCV + company info
   
2. NEWS COLLECTION (Weekly)
   ├─ Source: NewsAPI
   ├─ Frequency: Weekly
   ├─ Script: fetch_news_sentiment.py
   └─ Process:
      ├─ Fetch articles (last 7 days)
      ├─ Run through FinBERT
      └─ Store sentiment scores (-1 to +1)

3. ML TRAINING (Weekly)
   ├─ Script: train_model_v2.py
   ├─ Frequency: Weekly (after news update)
   └─ Process:
      ├─ Read prices & sentiment from DB
      ├─ Calculate 8 features
      ├─ Train XGBoost classifier
      └─ Save model (84% accuracy)

4. DISCORD BOT (24/7)
   ├─ Script: bot_with_real_data.py
   ├─ Process:
      ├─ Load ML model on startup
      ├─ On /daily command:
      │  ├─ Read data from DB
      │  ├─ Calculate features
      │  ├─ Run ML prediction
      │  └─ Return top 10 stocks
      └─ Auto-refresh: 9:30 AM ET daily
```

### 3.2 Data Collection Scripts

#### load_sp100.py
```python
Purpose: Load S&P 100 stocks into database
Runtime: ~15-20 minutes
Process:
  1. Create database tables if needed
  2. Fetch S&P 100 ticker list
  3. For each ticker:
     - Fetch company info (FMP)
     - Fetch 1 year price history (yfinance)
     - Store in database
  4. Summary report

Usage: python load_sp100.py
```

#### fetch_news_sentiment.py
```python
Purpose: Collect news and analyze sentiment
Runtime: ~25-30 minutes for 100 stocks
API Limit: 500 requests/day (NewsAPI free tier)
Process:
  1. Load stocks from database
  2. For each stock (last 7 days):
     - Fetch news articles (NewsAPI)
     - Analyze sentiment (FinBERT)
     - Store in database
  3. Summary report

Usage: python scripts/fetch_news_sentiment.py
```

#### train_model_v2.py
```python
Purpose: Train ML model on collected data
Runtime: ~1-2 minutes
Process:
  1. Load price & sentiment data from DB
  2. Calculate 8 features per stock
  3. Create labels (price up/down in 5 days)
  4. Train XGBoost classifier
  5. Evaluate (accuracy, precision, ROC)
  6. Save model to models/saved_models/

Usage: python scripts/train_model_v2.py
```

---

## 4. Machine Learning Model

### 4.1 Model Architecture

**Algorithm:** XGBoost Classifier  
**Accuracy:** 84%  
**Precision:** 88%  
**F1 Score:** 82%  

### 4.2 Features (8 Total)

```python
PRICE FEATURES (5):
1. return_5d    : 5-day return percentage
2. return_10d   : 10-day return percentage  
3. return_20d   : 20-day return percentage
4. momentum     : Price direction consistency (-1 to 1)
5. volume_trend : Volume change vs average

SENTIMENT FEATURES (3):
6. avg_sentiment      : Average news sentiment (-1 to 1)
7. sentiment_positive : % of positive articles
8. sentiment_negative : % of negative articles
```

### 4.3 Training Process

```python
# Simplified training logic
for each stock in database:
    # Get last 30 days of prices
    prices = get_prices(stock_id, days=30)
    
    # Calculate features
    features = calculate_features(prices, news)
    
    # Create label: did price go up in next 5 days?
    label = 1 if prices[day+5] > prices[day] else 0
    
    # Add to training data
    X.append(features)
    y.append(label)

# Train model
model = XGBClassifier(n_estimators=100, max_depth=4)
model.fit(X_train, y_train)

# Evaluate
accuracy = model.score(X_test, y_test)
```

### 4.4 Prediction Process

```python
# Bot scoring logic (simplified)
def score_stock(ticker):
    # Get data from DB (NO API calls)
    prices = db.get_prices(ticker, days=60)
    news = db.get_news(ticker)
    
    # Calculate same 8 features
    features = calculate_features(prices, news)
    
    # Run through ML model
    probability = model.predict_proba(features)[0][1]
    score = int(probability * 100)  # 0-100
    
    return score
```

### 4.5 Feature Importance

```
1. return_10d         : 35.7%  ← Most important!
2. volume_trend       : 11.8%
3. momentum           : 11.6%
4. avg_sentiment      : 10.6%
5. sentiment_negative : 9.5%
6. return_20d         : 7.6%
7. return_5d          : 6.8%
8. sentiment_positive : 6.4%
```

**Interpretation:** 10-day momentum is the strongest predictor!

---

## 5. Discord Bot

### 5.1 Available Commands

```python
/daily
  Description: Get top 10 stock recommendations
  Response Time: ~10 seconds
  Example Output:
    📊 Today's Top 10 Stock Picks
    1. V    - Visa Inc.              Score: 99 ⭐
    2. MA   - Mastercard             Score: 95 ⭐
    3. NVDA - NVIDIA Corporation     Score: 92 ⭐
    ...

/stock <ticker>
  Description: Detailed analysis for specific stock
  Response Time: ~1 second
  Example: /stock AAPL
  Output:
    📊 AAPL - Apple Inc.
    Price: $175.43
    ML Score: 87/100
    Technical: 85/100
    Sentiment: 72/100
    Risk: Medium
    Signals:
      • Strong momentum: +8.5% in 10 days
      • Positive news sentiment: 0.65

/refresh
  Description: Force refresh recommendations
  Response Time: ~30 seconds (scores all stocks)
  Note: Use sparingly (computationally expensive)

/help
  Description: Show help message
```

### 5.2 Bot Lifecycle

```python
# Startup
1. Load configuration from .env
2. Initialize database connection
3. Load ML model (model_latest.pkl)
4. Connect to Discord
5. Sync slash commands
6. Start scheduled tasks

# Runtime
- Listen for slash commands
- Execute on user request
- Daily auto-refresh at 9:30 AM ET

# Scoring Process (per stock)
1. Query database for prices & news
2. Calculate 8 features
3. Run through ML model
4. Return score (0-100)
   Time: ~10ms per stock
```

### 5.3 Error Handling

```python
# Bot handles these gracefully:
- Stock not in database → Clear error message
- Insufficient data → Skip stock, continue
- ML model not loaded → Use fallback scoring
- API rate limits → Use cached data
- Database errors → Log & notify user
```

---

## 6. Database Schema

### 6.1 Tables

#### stocks
```sql
CREATE TABLE stocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker VARCHAR(10) UNIQUE NOT NULL,
    company_name VARCHAR(255),
    sector VARCHAR(100),
    industry VARCHAR(100),
    market_cap BIGINT,
    last_updated DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### stock_prices
```sql
CREATE TABLE stock_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id INTEGER NOT NULL,
    date DATE NOT NULL,
    open FLOAT,
    high FLOAT,
    low FLOAT,
    close FLOAT NOT NULL,
    volume BIGINT,
    adjusted_close FLOAT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (stock_id) REFERENCES stocks(id),
    UNIQUE(stock_id, date)
);
```

#### news_articles
```sql
CREATE TABLE news_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id INTEGER NOT NULL,
    published_at DATETIME NOT NULL,
    title TEXT NOT NULL,
    source VARCHAR(100),
    url TEXT,
    sentiment_score FLOAT,      -- -1.0 to 1.0
    sentiment_label VARCHAR(20), -- positive/negative/neutral
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (stock_id) REFERENCES stocks(id),
    UNIQUE(stock_id, url)  -- Same article can link to multiple stocks
);
```

### 6.2 Indexes

```sql
-- Performance indexes
CREATE INDEX idx_prices_stock_date ON stock_prices(stock_id, date);
CREATE INDEX idx_news_stock_published ON news_articles(stock_id, published_at);
CREATE INDEX idx_news_url ON news_articles(stock_id, url);
```

### 6.3 Current Data Volume

```
Stocks:        100 records
Prices:        ~25,000 records (250 days × 100 stocks)
News:          0 records (needs weekly refresh)
Database Size: ~5 MB
```

---

## 7. API Integrations

### 7.1 yfinance (Free)

```python
Usage: Primary source for price data
Limits: ~2000 requests/hour
Cost: Free

Example:
import yfinance as yf
data = yf.download('AAPL', period='1y', interval='1d')
```

### 7.2 Financial Modeling Prep (Free Tier)

```python
Usage: Company info, fundamentals (backup)
Limits: 250 API calls/day
Cost: Free tier
Endpoints Used:
  - /stable/profile/{ticker}
  - /stable/key-metrics-ttm?symbol={ticker}

Note: Free tier restricted to /stable/ endpoints only
```

### 7.3 Finnhub (Free Tier)

```python
Usage: Real-time quotes (backup)
Limits: 60 API calls/minute
Cost: Free tier

Example:
import finnhub
client = finnhub.Client(api_key="YOUR_KEY")
quote = client.quote('AAPL')
```

### 7.4 NewsAPI (Free Tier)

```python
Usage: News article collection
Limits: 500 requests/day
Cost: Free tier
Lookback: 30 days max on free tier

Example:
from newsapi import NewsApiClient
newsapi = NewsApiClient(api_key='YOUR_KEY')
articles = newsapi.get_everything(
    q='Apple stock',
    language='en',
    sort_by='publishedAt',
    from_param='2025-10-20',
    to='2025-10-27'
)
```

### 7.5 API Key Management

```bash
# .env file
DISCORD_BOT_TOKEN=your_discord_token
FMP_API_KEY=your_fmp_key
FINNHUB_API_KEY=your_finnhub_key
NEWS_API_KEY=your_newsapi_key
DATABASE_URL=sqlite:///smartinvest_dev.db
```

---

## 8. Deployment

### 8.1 Local Development

```bash
# Setup
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your API keys

# Load data
python load_sp100.py                      # ~15 min
python scripts/fetch_news_sentiment.py    # ~25 min  
python scripts/train_model_v2.py          # ~1 min

# Run bot
python bot_with_real_data.py
```

### 8.2 Production Deployment

**Recommended: Cloud Server (VPS)**

```bash
# Example: DigitalOcean Droplet / AWS EC2
Instance: 2 GB RAM, 1 vCPU ($10-15/month)
OS: Ubuntu 22.04

# Setup
git clone <your-repo>
cd smartinvest-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
nano .env  # Add your keys

# Run with systemd
sudo nano /etc/systemd/system/smartinvest-bot.service

[Unit]
Description=SmartInvest Discord Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/smartinvest-bot
Environment="PATH=/home/ubuntu/smartinvest-bot/venv/bin"
ExecStart=/home/ubuntu/smartinvest-bot/venv/bin/python bot_with_real_data.py
Restart=always

[Install]
WantedBy=multi-user.target

# Enable & start
sudo systemctl enable smartinvest-bot
sudo systemctl start smartinvest-bot
sudo systemctl status smartinvest-bot
```

### 8.3 Weekly Maintenance Cron Jobs

```bash
# Edit crontab
crontab -e

# Run news update every Sunday at 8 AM
0 8 * * 0 cd /home/ubuntu/smartinvest-bot && /home/ubuntu/smartinvest-bot/venv/bin/python scripts/fetch_news_sentiment.py >> /var/log/smartinvest_news.log 2>&1

# Run model training every Sunday at 9 AM
0 9 * * 0 cd /home/ubuntu/smartinvest-bot && /home/ubuntu/smartinvest-bot/venv/bin/python scripts/train_model_v2.py >> /var/log/smartinvest_train.log 2>&1

# Restart bot every Sunday at 9:30 AM
30 9 * * 0 sudo systemctl restart smartinvest-bot
```

---

## 9. Troubleshooting

### 9.1 Common Issues

#### Bot Won't Start
```
Error: "DISCORD_BOT_TOKEN not found"
Fix: Check .env file exists and has correct token

Error: "No module named 'discord'"
Fix: pip install -r requirements.txt
```

#### No Recommendations
```
Error: "No recommendations available"
Causes:
  1. No stocks in database → Run load_sp100.py
  2. Stocks have insufficient data → Check last 60 days
  3. ML model not found → Check models/saved_models/
  
Debug:
  python -c "from data.storage import DatabaseManager; ..."
```

#### API Rate Limits
```
Error: "402 Payment Required" (FMP)
Fix: You've hit daily limit (250 calls). Wait or upgrade.

Error: "429 Too Many Requests" (NewsAPI)
Fix: You've hit daily limit (500 calls). Wait 24 hours.
```

### 9.2 Database Issues

```bash
# Reset database (CAUTION: Deletes all data)
rm smartinvest_dev.db
python load_sp100.py

# Check database integrity
sqlite3 smartinvest_dev.db
> .tables
> SELECT COUNT(*) FROM stocks;
> SELECT COUNT(*) FROM stock_prices;
> .exit
```

### 9.3 Model Issues

```bash
# Retrain model
python scripts/train_model_v2.py

# Check model exists
ls -lh models/saved_models/

# Test model loading
python -c "import joblib; m = joblib.load('models/saved_models/model_latest.pkl'); print(m['metrics'])"
```

---

## Appendix A: Weekly Maintenance Checklist

```
□ Sunday Morning (or weekly):
  □ Run: python scripts/fetch_news_sentiment.py (~25 min)
  □ Run: python scripts/train_model_v2.py (~1 min)
  □ Restart bot: python bot_with_real_data.py
  □ Test /daily command in Discord
  □ Check logs for errors

□ Monthly:
  □ Backup database: cp smartinvest_dev.db backup_YYYYMMDD.db
  □ Review model performance
  □ Update stock list if needed (load_incremental.py)
```

---

## Appendix B: Performance Benchmarks

```
Operation              Time        Notes
─────────────────────────────────────────────────────────────
Load 100 stocks        15-20 min   One-time or weekly
Fetch news (100)       25-30 min   Weekly
Train ML model         1-2 min     Weekly
Score single stock     10 ms       Per request
Score all stocks       1-2 sec     99 stocks
/daily command         10 sec      End-to-end
Bot startup            5 sec       Model loading
```

---

## Appendix C: Dependencies

```
# requirements.txt (key packages)
discord.py==2.3.2
yfinance==0.2.66
pandas==2.1.3
numpy==1.26.2
sqlalchemy==2.0.23
python-dotenv==1.0.0
transformers==4.35.2
torch==2.1.1
xgboost==2.0.2
scikit-learn==1.3.2
newsapi-python==0.2.7
finnhub-python==2.4.19
```

---

**End of Technical Documentation**

