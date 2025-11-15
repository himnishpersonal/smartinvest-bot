# SmartInvest Database Schema

## Entity Relationship Diagram (ERD)

```
┌─────────────────┐
│     Stock       │
├─────────────────┤
│ id (PK)         │
│ ticker (UQ)     │◄───────┐
│ company_name    │        │
│ sector          │        │
│ industry        │        │
│ market_cap      │        │
│ last_updated    │        │
└─────────────────┘        │
        ▲                  │
        │                  │
        │ 1:N              │
        │                  │
┌───────┴──────────────────┴───────────────────────┐
│                                                   │
│  ┌─────────────────┐    ┌──────────────────┐    │
│  │  StockPrice     │    │   Fundamental    │    │
│  ├─────────────────┤    ├──────────────────┤    │
│  │ id (PK)         │    │ id (PK)          │    │
│  │ stock_id (FK)   │    │ stock_id (FK)    │    │
│  │ date            │    │ date             │    │
│  │ open            │    │ pe_ratio         │    │
│  │ high            │    │ pb_ratio         │    │
│  │ low             │    │ ps_ratio         │    │
│  │ close           │    │ debt_to_equity   │    │
│  │ volume          │    │ current_ratio    │    │
│  │ adjusted_close  │    │ quick_ratio      │    │
│  └─────────────────┘    │ roe, roa         │    │
│                         │ profit_margin    │    │
│  ┌─────────────────┐    │ revenue_growth   │    │
│  │  NewsArticle    │    │ earnings_growth  │    │
│  ├─────────────────┤    └──────────────────┘    │
│  │ id (PK)         │                             │
│  │ stock_id (FK)   │    ┌──────────────────┐    │
│  │ published_at    │    │ Recommendation   │    │
│  │ title           │    ├──────────────────┤    │
│  │ source          │    │ id (PK)          │    │
│  │ url (UQ)        │    │ stock_id (FK)    │    │
│  │ sentiment_score │    │ overall_score    │    │
│  │ sentiment_label │    │ technical_score  │    │
│  └─────────────────┘    │ fundamental_score│    │
│                         │ sentiment_score  │    │
│  ┌─────────────────┐    │ signals (JSON)   │    │
│  │ UserWatchlist   │    │ rank             │    │
│  ├─────────────────┤    │ price_at_rec     │    │
│  │ id (PK)         │    │ price_after_5d   │    │
│  │ discord_user_id │    │ price_after_30d  │    │
│  │ stock_id (FK)   │    │ return_5days     │    │
│  │ added_at        │    │ return_30days    │    │
│  └─────────────────┘    └──────────────────┘    │
│                                                   │
│  ┌─────────────────┐                             │
│  │   UserAlert     │                             │
│  ├─────────────────┤                             │
│  │ id (PK)         │                             │
│  │ discord_user_id │                             │
│  │ stock_id (FK)   │                             │
│  │ threshold_score │                             │
│  │ is_active       │                             │
│  │ triggered_at    │                             │
│  └─────────────────┘                             │
│                                                   │
└───────────────────────────────────────────────────┘
```

## Table Details

### 1. Stock (Core Table)
**Purpose:** Store basic stock information

| Column | Type | Description |
|--------|------|-------------|
| id | Integer (PK) | Primary key |
| ticker | String(10) (UQ, IDX) | Stock ticker (e.g., AAPL) |
| company_name | String(255) | Full company name |
| sector | String(100) | Business sector |
| industry | String(100) | Specific industry |
| market_cap | BigInteger | Market capitalization |
| last_updated | DateTime | Last update timestamp |
| created_at | DateTime | Creation timestamp |

**Indexes:** ticker

---

### 2. StockPrice
**Purpose:** Store historical OHLCV data

| Column | Type | Description |
|--------|------|-------------|
| id | Integer (PK) | Primary key |
| stock_id | Integer (FK) | Reference to Stock |
| date | DateTime (IDX) | Trading date |
| open | Float | Opening price |
| high | Float | Highest price |
| low | Float | Lowest price |
| close | Float | Closing price |
| volume | BigInteger | Trading volume |
| adjusted_close | Float | Adjusted closing price |
| created_at | DateTime | Record creation time |

**Indexes:** stock_id + date  
**Constraints:** UNIQUE(stock_id, date)

---

### 3. Fundamental
**Purpose:** Store fundamental analysis metrics

| Column | Type | Description |
|--------|------|-------------|
| id | Integer (PK) | Primary key |
| stock_id | Integer (FK) | Reference to Stock |
| date | DateTime (IDX) | Data date |
| pe_ratio | Float | Price-to-Earnings ratio |
| pb_ratio | Float | Price-to-Book ratio |
| ps_ratio | Float | Price-to-Sales ratio |
| debt_to_equity | Float | Debt-to-Equity ratio |
| current_ratio | Float | Current ratio |
| quick_ratio | Float | Quick ratio |
| roe | Float | Return on Equity |
| roa | Float | Return on Assets |
| profit_margin | Float | Profit margin |
| revenue_growth | Float | Revenue growth rate |
| earnings_growth | Float | Earnings growth rate |
| last_updated | DateTime | Last update time |
| created_at | DateTime | Record creation time |

**Indexes:** stock_id + date

---

### 4. NewsArticle
**Purpose:** Store news with sentiment analysis

| Column | Type | Description |
|--------|------|-------------|
| id | Integer (PK) | Primary key |
| stock_id | Integer (FK) | Reference to Stock |
| published_at | DateTime (IDX) | Publication timestamp |
| title | Text | Article headline |
| source | String(100) | News source |
| url | Text (UQ) | Article URL |
| sentiment_score | Float | Sentiment (-1.0 to 1.0) |
| sentiment_label | String(20) | positive/negative/neutral |
| created_at | DateTime | Record creation time |

**Indexes:** stock_id + published_at

---

### 5. Recommendation
**Purpose:** Store ML-generated recommendations with tracking

| Column | Type | Description |
|--------|------|-------------|
| id | Integer (PK) | Primary key |
| stock_id | Integer (FK) | Reference to Stock |
| created_at | DateTime (IDX) | Recommendation time |
| overall_score | Integer | Overall score (0-100) |
| technical_score | Integer | Technical analysis score |
| fundamental_score | Integer | Fundamental analysis score |
| sentiment_score | Integer | Sentiment score |
| signals | JSON | Array of key signals |
| rank | Integer | Ranking (1-10 for top picks) |
| price_at_recommendation | Float | Price when recommended |
| price_after_5days | Float | Price after 5 days |
| price_after_30days | Float | Price after 30 days |
| return_5days | Float | 5-day return % |
| return_30days | Float | 30-day return % |
| updated_at | DateTime | Last update time |

**Indexes:** stock_id + created_at, overall_score, rank

---

### 6. UserWatchlist
**Purpose:** Track user's favorite stocks

| Column | Type | Description |
|--------|------|-------------|
| id | Integer (PK) | Primary key |
| discord_user_id | String(100) (IDX) | Discord user ID |
| stock_id | Integer (FK) | Reference to Stock |
| added_at | DateTime | When added |

**Indexes:** discord_user_id  
**Constraints:** UNIQUE(discord_user_id, stock_id)

---

### 7. UserAlert
**Purpose:** User notification preferences

| Column | Type | Description |
|--------|------|-------------|
| id | Integer (PK) | Primary key |
| discord_user_id | String(100) (IDX) | Discord user ID |
| stock_id | Integer (FK) | Reference to Stock |
| threshold_score | Integer | Min score to trigger alert |
| created_at | DateTime | Alert creation time |
| triggered_at | DateTime | Last trigger time |
| is_active | Boolean | Alert enabled/disabled |
| updated_at | DateTime | Last update time |

**Indexes:** discord_user_id + is_active, stock_id + is_active

---

## Relationships

- **Stock → StockPrice**: One-to-Many
- **Stock → Fundamental**: One-to-Many
- **Stock → NewsArticle**: One-to-Many
- **Stock → Recommendation**: One-to-Many
- **Stock → UserWatchlist**: One-to-Many
- **Stock → UserAlert**: One-to-Many

All foreign keys use `CASCADE` on delete.

## Database Engines Supported

- **SQLite** (Development) - Default, file-based
- **PostgreSQL** (Production) - Recommended for production

## Performance Optimizations

1. **Indexes** on frequently queried columns:
   - Stock ticker lookups
   - Price date ranges
   - Recommendation scores and rankings
   - User-specific queries

2. **Connection Pooling**:
   - Pool size: 5
   - Max overflow: 10
   - Pre-ping enabled

3. **Constraints**:
   - Unique constraints prevent duplicates
   - Foreign keys with CASCADE ensure data integrity

## Migration Strategy

For schema changes, use SQLAlchemy migrations:
```bash
# TODO: Add Alembic for migrations
pip install alembic
alembic init migrations
```

