"""
Configuration management for SmartInvest Discord Bot.
Loads environment variables and provides configuration classes.
"""

import os
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base configuration class."""
    
    # Discord Configuration
    DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    DISCORD_CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID', '0'))
    
    # API Keys
    NEWS_API_KEY = os.getenv('NEWS_API_KEY')
    FINNHUB_API_KEY = os.getenv('FINNHUB_API_KEY')  # Finnhub API key (real-time quotes)
    FMP_API_KEY = os.getenv('FMP_API_KEY')  # Financial Modeling Prep (historical data)
    
    # Database Configuration
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///smartinvest.db')
    
    # Environment
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
    
    # Stock Universe - S&P 100 tickers (representative sample)
    STOCK_UNIVERSE: List[str] = [
        # Technology
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'AVGO', 'ORCL', 'ADBE',
        'CRM', 'CSCO', 'ACN', 'AMD', 'INTC', 'IBM', 'QCOM', 'TXN', 'INTU', 'AMAT',
        # Financial
        'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'BLK', 'SCHW', 'AXP', 'USB',
        # Healthcare
        'UNH', 'JNJ', 'LLY', 'PFE', 'ABBV', 'TMO', 'MRK', 'ABT', 'DHR', 'BMY',
        'AMGN', 'CVS', 'MDT', 'GILD', 'CI',
        # Consumer
        'WMT', 'HD', 'PG', 'KO', 'PEP', 'COST', 'MCD', 'NKE', 'SBUX', 'TGT',
        'LOW', 'TJX', 'MDLZ', 'CL', 'EL',
        # Communication
        'DIS', 'NFLX', 'CMCSA', 'VZ', 'T', 'TMUS',
        # Industrial
        'BA', 'HON', 'UPS', 'CAT', 'GE', 'MMM', 'LMT', 'RTX', 'DE', 'UNP',
        # Energy
        'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'PXD',
        # Utilities & Real Estate
        'NEE', 'DUK', 'SO', 'AMT', 'PLD',
        # Materials
        'LIN', 'APD', 'SHW', 'NEM', 'FCX'
    ]
    
    # Stock Filtering Criteria
    MIN_PRICE = float(os.getenv('MIN_PRICE', '5.0'))  # Minimum stock price
    MIN_VOLUME = int(os.getenv('MIN_VOLUME', '500000'))  # Minimum daily volume
    
    # Analysis Configuration
    ANALYSIS_TIME = os.getenv('ANALYSIS_TIME', '09:30')  # Time to run daily analysis
    TIMEZONE = os.getenv('TIMEZONE', 'America/New_York')  # Market timezone
    
    # Feature Engineering
    TECHNICAL_INDICATORS = ['RSI', 'MACD', 'SMA', 'EMA', 'BB', 'ATR', 'OBV']
    LOOKBACK_DAYS = 252  # Trading days (~1 year)
    
    # Model Configuration
    TRAIN_TEST_SPLIT = 0.2
    RANDOM_STATE = 42
    
    # Recommendation Thresholds
    HIGH_SCORE_THRESHOLD = 80
    MEDIUM_SCORE_THRESHOLD = 60
    LOW_SCORE_THRESHOLD = 40
    
    # Performance Tracking
    TRACKING_PERIODS = [5, 30]  # Days to track performance
    
    @classmethod
    def validate(cls):
        """
        Validate that all required configuration variables are set.
        Raises ValueError if any required variables are missing.
        """
        errors = []
        
        if not cls.DISCORD_BOT_TOKEN:
            errors.append("DISCORD_BOT_TOKEN is not set")
        
        if cls.DISCORD_CHANNEL_ID == 0:
            errors.append("DISCORD_CHANNEL_ID is not set or invalid")
        
        if cls.ENVIRONMENT not in ['development', 'production']:
            errors.append(f"ENVIRONMENT must be 'development' or 'production', got '{cls.ENVIRONMENT}'")
        
        if errors:
            raise ValueError(f"Configuration validation failed:\n" + "\n".join(f"  - {err}" for err in errors))
    
    @classmethod
    def display(cls):
        """Display current configuration (masking sensitive data)."""
        print("=" * 50)
        print("SmartInvest Bot Configuration")
        print("=" * 50)
        print(f"Environment: {cls.ENVIRONMENT}")
        print(f"Database: {cls.DATABASE_URL}")
        print(f"Discord Token: {'*' * 20 if cls.DISCORD_BOT_TOKEN else 'NOT SET'}")
        print(f"Discord Channel: {cls.DISCORD_CHANNEL_ID}")
        print(f"News API Key: {'*' * 20 if cls.NEWS_API_KEY else 'NOT SET'}")
        print(f"Finnhub API Key: {'*' * 20 if cls.FINNHUB_API_KEY else 'NOT SET'}")
        print(f"FMP API Key: {'*' * 20 if cls.FMP_API_KEY else 'NOT SET'}")
        print(f"Stock Universe: {len(cls.STOCK_UNIVERSE)} tickers")
        print(f"Min Price: ${cls.MIN_PRICE}")
        print(f"Min Volume: {cls.MIN_VOLUME:,}")
        print(f"Analysis Time: {cls.ANALYSIS_TIME} {cls.TIMEZONE}")
        print("=" * 50)


class DevelopmentConfig(Config):
    """Development environment configuration."""
    
    ENVIRONMENT = 'development'
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///smartinvest_dev.db')
    
    # Reduced stock universe for faster testing
    STOCK_UNIVERSE: List[str] = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA',
        'JPM', 'BAC', 'UNH', 'JNJ', 'WMT'
    ]
    
    # More lenient filters for testing
    MIN_PRICE = 1.0
    MIN_VOLUME = 100000
    
    # Shorter lookback for faster processing
    LOOKBACK_DAYS = 90
    
    # Debug settings
    DEBUG = True
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(Config):
    """Production environment configuration."""
    
    ENVIRONMENT = 'production'
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost/smartinvest')
    
    # Strict validation for production
    @classmethod
    def validate(cls):
        """Extended validation for production environment."""
        super().validate()
        
        errors = []
        
        # Require NewsAPI key in production
        if not cls.NEWS_API_KEY:
            errors.append("NEWS_API_KEY is required in production")
        
        # Ensure PostgreSQL is used in production
        if not cls.DATABASE_URL.startswith('postgresql'):
            errors.append("Production must use PostgreSQL database")
        
        if errors:
            raise ValueError(f"Production configuration validation failed:\n" + 
                           "\n".join(f"  - {err}" for err in errors))
    
    # Production settings
    DEBUG = False
    LOG_LEVEL = 'INFO'


def get_config():
    """
    Get the appropriate configuration based on ENVIRONMENT variable.
    
    Returns:
        Config class (DevelopmentConfig or ProductionConfig)
    """
    env = os.getenv('ENVIRONMENT', 'development').lower()
    
    if env == 'production':
        config = ProductionConfig
    else:
        config = DevelopmentConfig
    
    # Validate configuration
    config.validate()
    
    return config


# Convenience: Get active configuration
active_config = get_config()


if __name__ == '__main__':
    # Display configuration when run directly
    try:
        config = get_config()
        config.display()
    except ValueError as e:
        print(f"❌ Configuration Error:\n{e}")

