"""
Data module for handling stock data, news, and database operations
"""

from .schema import (
    Base,
    Stock,
    StockPrice,
    Fundamental,
    NewsArticle,
    Recommendation,
    UserWatchlist,
    UserAlert,
    create_tables,
    drop_tables
)

from .database import (
    engine,
    Session,
    init_db,
    drop_db,
    get_db_session,
    get_session,
    close_session
)

from .storage import DatabaseManager
from .collectors import (
    StockDataCollector, 
    NewsCollector,
    SentimentAnalyzer,
    get_sp500_tickers, 
    get_sp100_tickers
)
from .pipeline import DataPipeline, get_data_freshness

__all__ = [
    # Schema models
    'Base',
    'Stock',
    'StockPrice',
    'Fundamental',
    'NewsArticle',
    'Recommendation',
    'UserWatchlist',
    'UserAlert',
    'create_tables',
    'drop_tables',
    # Database utilities
    'engine',
    'Session',
    'init_db',
    'drop_db',
    'get_db_session',
    'get_session',
    'close_session',
    # Database Manager
    'DatabaseManager',
    # Data Collectors
    'StockDataCollector',
    'NewsCollector',
    'SentimentAnalyzer',
    'get_sp500_tickers',
    'get_sp100_tickers',
    # Data Pipeline
    'DataPipeline',
    'get_data_freshness'
]
