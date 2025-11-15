# Data Module

This module handles all database operations for the SmartInvest bot.

## Database Schema

### Tables Overview

1. **stocks** - Core stock information
2. **stock_prices** - Historical price data
3. **fundamentals** - Fundamental analysis metrics
4. **news_articles** - News articles with sentiment analysis
5. **recommendations** - ML-generated stock recommendations
6. **user_watchlists** - User's tracked stocks
7. **user_alerts** - User notification preferences

## Models

### Stock
Core stock information table.

**Fields:**
- `ticker` (unique, indexed) - Stock ticker symbol (e.g., 'AAPL')
- `company_name` - Full company name
- `sector` - Business sector
- `industry` - Specific industry
- `market_cap` - Market capitalization
- `last_updated` - Last update timestamp

**Relationships:**
- One-to-many with StockPrice, Fundamental, NewsArticle, Recommendation, UserWatchlist, UserAlert

### StockPrice
Historical stock price data.

**Fields:**
- `stock_id` (foreign key) - Reference to Stock
- `date` (indexed) - Trading date
- `open`, `high`, `low`, `close` - OHLC price data
- `volume` - Trading volume
- `adjusted_close` - Adjusted closing price

**Constraints:**
- Unique constraint on (stock_id, date)

### Fundamental
Fundamental analysis metrics.

**Fields:**
- **Valuation Ratios:** `pe_ratio`, `pb_ratio`, `ps_ratio`
- **Financial Health:** `debt_to_equity`, `current_ratio`, `quick_ratio`
- **Profitability:** `roe`, `roa`, `profit_margin`
- **Growth Metrics:** `revenue_growth`, `earnings_growth`

### NewsArticle
News articles with sentiment analysis.

**Fields:**
- `published_at` (indexed) - Publication timestamp
- `title` - Article headline
- `source` - News source
- `url` - Article URL (unique)
- `sentiment_score` - Sentiment score (-1.0 to 1.0)
- `sentiment_label` - Classification (positive/negative/neutral)

### Recommendation
ML-generated stock recommendations with tracking.

**Fields:**
- `overall_score` (0-100) - Composite recommendation score
- `technical_score` (0-100) - Technical analysis score
- `fundamental_score` (0-100) - Fundamental analysis score
- `sentiment_score` (0-100) - News sentiment score
- `signals` (JSON) - Array of key signals
- `rank` (1-10) - Ranking for top picks
- `price_at_recommendation` - Stock price when recommended
- `price_after_5days`, `price_after_30days` - Price tracking
- `return_5days`, `return_30days` - Return tracking

### UserWatchlist
User's tracked stocks.

**Fields:**
- `discord_user_id` - Discord user ID
- `stock_id` (foreign key) - Reference to Stock
- `added_at` - When stock was added

**Constraints:**
- Unique constraint on (discord_user_id, stock_id)

### UserAlert
User notification preferences.

**Fields:**
- `discord_user_id` - Discord user ID
- `stock_id` (foreign key) - Reference to Stock
- `threshold_score` - Minimum score to trigger alert
- `is_active` - Whether alert is enabled
- `triggered_at` - When alert was last triggered

## Usage Examples

### Initialize Database

```python
from data import init_db

# Create all tables
init_db()
```

### Add a Stock

```python
from data import get_db_session, Stock

with get_db_session() as session:
    stock = Stock(
        ticker='AAPL',
        company_name='Apple Inc.',
        sector='Technology',
        industry='Consumer Electronics',
        market_cap=3000000000000
    )
    session.add(stock)
```

### Query Stocks

```python
from data import get_db_session, Stock

with get_db_session() as session:
    # Get stock by ticker
    apple = session.query(Stock).filter_by(ticker='AAPL').first()
    
    # Get all tech stocks
    tech_stocks = session.query(Stock).filter_by(sector='Technology').all()
    
    # Access related data
    latest_price = apple.prices[-1] if apple.prices else None
    recommendations = apple.recommendations
```

### Add Recommendation

```python
from data import get_db_session, Recommendation

with get_db_session() as session:
    rec = Recommendation(
        stock_id=1,
        overall_score=85,
        technical_score=80,
        fundamental_score=88,
        sentiment_score=87,
        signals=['Strong RSI', 'Positive earnings'],
        rank=1,
        price_at_recommendation=177.45
    )
    session.add(rec)
```

### User Watchlist

```python
from data import get_db_session, UserWatchlist, Stock

with get_db_session() as session:
    # Add to watchlist
    watchlist = UserWatchlist(
        discord_user_id='123456789',
        stock_id=1
    )
    session.add(watchlist)
    
    # Get user's watchlist
    user_stocks = session.query(UserWatchlist).filter_by(
        discord_user_id='123456789'
    ).all()
```

## Database Configuration

Set the `DATABASE_URL` in your `.env` file:

### SQLite (Default - for development)
```
DATABASE_URL=sqlite:///smartinvest.db
```

### PostgreSQL (Recommended for production)
```
DATABASE_URL=postgresql://user:password@localhost/smartinvest
```

## Indexes

The schema includes optimized indexes for common queries:
- Stock ticker lookup
- Price data by stock and date
- News articles by publication date
- Recommendations by score and rank
- User watchlists and alerts by user ID

## Relationships

All foreign keys use `CASCADE` on delete to maintain referential integrity.

