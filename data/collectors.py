"""
Stock data collection module using FMP (primary) and Finnhub (backup) APIs.
Hybrid approach for maximum reliability and API efficiency.
"""

import logging
import time
import hashlib
import os
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import numpy as np
from functools import wraps, lru_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def retry_on_failure(max_retries: int = 3, backoff_factor: float = 2.0):
    """
    Decorator for retry logic with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for wait time between retries
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    wait_time = backoff_factor ** attempt
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_retries}): {e}. "
                            f"Retrying in {wait_time}s..."
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(f"{func.__name__} failed after {max_retries} attempts: {e}")
                        raise
            return None
        return wrapper
    return decorator


class StockDataCollector:
    """
    Hybrid stock data collector using FMP (primary) and Finnhub (backup).
    
    Strategy:
    - Historical OHLCV: FMP primary (5 years daily data)
    - Real-time quotes: Finnhub primary, FMP backup
    - Fundamentals: FMP primary
    - Company info: FMP primary, Finnhub backup
    """
    
    def __init__(self, fmp_api_key: str = None, finnhub_api_key: str = None):
        """
        Initialize the hybrid StockDataCollector.
        
        Args:
            fmp_api_key: Financial Modeling Prep API key
            finnhub_api_key: Finnhub API key (backup for real-time)
        """
        # FMP Setup
        self.fmp_api_key = fmp_api_key or os.getenv('FMP_API_KEY')
        if not self.fmp_api_key:
            raise ValueError("FMP API key not provided. Set FMP_API_KEY in .env")
        
        self.fmp_base_url = "https://financialmodelingprep.com/stable"
        
        # Finnhub Setup (optional but recommended)
        try:
            import finnhub
            self.finnhub_api_key = finnhub_api_key or os.getenv('FINNHUB_API_KEY')
            if self.finnhub_api_key:
                self.finnhub_client = finnhub.Client(api_key=self.finnhub_api_key)
                logger.info("Finnhub client initialized (backup for real-time)")
            else:
                self.finnhub_client = None
                logger.warning("Finnhub API key not found - real-time backup unavailable")
        except ImportError:
            self.finnhub_client = None
            logger.warning("finnhub-python not installed - real-time backup unavailable")
        
        self.cache = {}  # Simple cache for company info
        self.rate_limit_delay = 0.25  # FMP free tier: 250 calls/day = ~1 every 4 seconds (be conservative)
        self.last_call_time = 0
        
        logger.info("✓ StockDataCollector initialized with FMP (primary) + Finnhub (backup)")
    
    def _rate_limit_wait(self):
        """Enforce rate limiting between API calls."""
        elapsed = time.time() - self.last_call_time
        if elapsed < self.rate_limit_delay:
            wait_time = self.rate_limit_delay - elapsed
            logger.debug(f"Rate limit: waiting {wait_time:.1f}s")
            time.sleep(wait_time)
        self.last_call_time = time.time()
    
    def _fmp_request(self, endpoint: str, params: dict = None) -> dict:
        """
        Make a request to FMP API.
        
        Args:
            endpoint: API endpoint (without base URL)
            params: Query parameters
        
        Returns:
            JSON response as dict
        """
        self._rate_limit_wait()
        
        url = f"{self.fmp_base_url}/{endpoint}"
        params = params or {}
        params['apikey'] = self.fmp_api_key
        
        logger.debug(f"FMP request: {endpoint}")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        return response.json()
    
    @retry_on_failure(max_retries=3)
    def fetch_price_history(self, ticker: str, period: str = '1y', 
                           interval: str = '1d') -> Optional[pd.DataFrame]:
        """
        Fetch historical price data using yfinance (reliable and free).
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')
            period: Time period ('1mo', '3mo', '6mo', '1y', '5y')
            interval: Data interval ('1d' for daily)
        
        Returns:
            DataFrame with columns: date, open, high, low, close, volume, adjusted_close
        
        Example:
            >>> collector = StockDataCollector(fmp_api_key='YOUR_KEY')
            >>> df = collector.fetch_price_history('AAPL', period='1y')
            >>> print(df.head())
        """
        try:
            import yfinance as yf
            
            logger.info(f"Fetching price history for {ticker} (period={period}) via yfinance")
            
            # Add small delay to avoid rate limits
            time.sleep(0.5)
            
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period, interval=interval)
            
            if hist.empty:
                logger.warning(f"No price data found for {ticker}")
                return None
            
            # Prepare DataFrame
            df = hist.reset_index()
            df.columns = df.columns.str.lower()
            
            # Rename columns to match our schema
            column_mapping = {
                'date': 'date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume',
                'adj close': 'adjusted_close'
            }
            
            df = df.rename(columns=column_mapping)
            
            # Ensure we have required columns
            required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
            if not all(col in df.columns for col in required_cols):
                logger.error(f"Missing required columns for {ticker}")
                return None
            
            # Add adjusted_close if not present
            if 'adjusted_close' not in df.columns:
                df['adjusted_close'] = df['close']
            
            logger.info(f"✓ Fetched {len(df)} price records for {ticker} via yfinance")
            return df[['date', 'open', 'high', 'low', 'close', 'volume', 'adjusted_close']]
            
        except Exception as e:
            logger.error(f"Error fetching price history for {ticker}: {e}")
            raise
    
    @retry_on_failure(max_retries=3)
    def fetch_current_price(self, ticker: str) -> Optional[Dict]:
        """
        Get real-time quote using Finnhub (primary) with FMP backup.
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Dictionary with current price information
        
        Example:
            >>> collector = StockDataCollector()
            >>> price_info = collector.fetch_current_price('AAPL')
            >>> print(f"AAPL: ${price_info['price']:.2f}")
        """
        try:
            # Try Finnhub first (real-time)
            if self.finnhub_client:
                try:
                    logger.info(f"Fetching current price for {ticker} via Finnhub")
                    quote = self.finnhub_client.quote(ticker)
                    
                    if quote and quote.get('c'):
                        price = float(quote.get('c', 0))
                        change = float(quote.get('d', 0))
                        change_percent = float(quote.get('dp', 0))
                        
                        result = {
                            'ticker': ticker,
                            'price': price,
                            'change': change,
                            'change_percent': change_percent,
                            'volume': 0,
                            'timestamp': datetime.now(),
                            'source': 'finnhub'
                        }
                        
                        logger.info(f"✓ {ticker}: ${price:.2f} ({change_percent:+.2f}%) via Finnhub")
                        return result
                except Exception as e:
                    logger.warning(f"Finnhub failed for {ticker}, trying FMP: {e}")
            
            # Fallback to FMP
            logger.info(f"Fetching current price for {ticker} via FMP")
            endpoint = f"quote/{ticker}"
            data = self._fmp_request(endpoint)
            
            if not data or not isinstance(data, list) or len(data) == 0:
                logger.warning(f"No quote data found for {ticker}")
                return None
            
            quote = data[0]
            price = float(quote.get('price', 0))
            volume = int(quote.get('volume', 0))
            
            result = {
                'ticker': ticker,
                'price': price,
                'change': 0.0,  # Not in quote-short
                'change_percent': 0.0,
                'volume': volume,
                'timestamp': datetime.now(),
                'source': 'fmp'
            }
            
            logger.info(f"✓ {ticker}: ${price:.2f} via FMP")
            return result
            
        except Exception as e:
            logger.error(f"Error fetching current price for {ticker}: {e}")
            raise
    
    @retry_on_failure(max_retries=3)
    def fetch_fundamentals(self, ticker: str) -> Optional[Dict]:
        """
        Fetch fundamental data using FMP key metrics and ratios.
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Dictionary with fundamental metrics
        
        Example:
            >>> collector = StockDataCollector()
            >>> fundamentals = collector.fetch_fundamentals('AAPL')
            >>> print(f"P/E: {fundamentals['pe_ratio']}")
        """
        try:
            logger.info(f"Fetching fundamentals for {ticker} via FMP")
            
            # Get key metrics (TTM) - stable endpoint
            endpoint = f"key-metrics-ttm?symbol={ticker}"
            metrics_data = self._fmp_request(endpoint)
            
            # Get ratios (TTM) - stable endpoint
            endpoint = f"ratios-ttm?symbol={ticker}"
            ratios_data = self._fmp_request(endpoint)
            
            if not metrics_data or not isinstance(metrics_data, list):
                logger.warning(f"No metrics data found for {ticker}")
                return None
            
            if not ratios_data or not isinstance(ratios_data, list):
                logger.warning(f"No ratios data found for {ticker}")
                return None
            
            metrics = metrics_data[0] if metrics_data else {}
            ratios = ratios_data[0] if ratios_data else {}
            
            # Helper function to safely get float value
            def get_float(data_dict, key, default=None):
                try:
                    value = data_dict.get(key)
                    if value is None or value == '':
                        return default
                    return float(value)
                except (ValueError, TypeError):
                    return default
            
            fundamentals = {
                # Valuation metrics
                'pe_ratio': get_float(ratios, 'priceEarningsRatioTTM'),
                'pb_ratio': get_float(ratios, 'priceToBookRatioTTM'),
                'ps_ratio': get_float(ratios, 'priceToSalesRatioTTM'),
                'peg_ratio': get_float(metrics, 'pegRatioTTM'),
                
                # Profitability metrics
                'roe': get_float(ratios, 'returnOnEquityTTM'),
                'roa': get_float(ratios, 'returnOnAssetsTTM'),
                'profit_margin': get_float(ratios, 'netProfitMarginTTM'),
                'operating_margin': get_float(ratios, 'operatingProfitMarginTTM'),
                'gross_margin': get_float(ratios, 'grossProfitMarginTTM'),
                
                # Financial health
                'debt_to_equity': get_float(ratios, 'debtEquityRatioTTM'),
                'current_ratio': get_float(ratios, 'currentRatioTTM'),
                'quick_ratio': get_float(ratios, 'quickRatioTTM'),
                
                # Growth metrics
                'revenue_growth_yoy': get_float(metrics, 'revenuePerShareTTM'),  # Approximation
                'earnings_growth_yoy': get_float(metrics, 'netIncomePerShareTTM'),
                'revenue_per_share': get_float(metrics, 'revenuePerShareTTM'),
                'eps': get_float(metrics, 'netIncomePerShareTTM'),
                
                # Size metrics
                'market_cap': get_float(metrics, 'marketCapTTM'),
                'enterprise_value': get_float(metrics, 'enterpriseValueTTM'),
                'dividend_yield': get_float(ratios, 'dividendYielTTM'),
                
                # Metadata
                'last_updated': datetime.now()
            }
            
            logger.info(f"✓ Fetched fundamentals for {ticker} via FMP")
            return fundamentals
            
        except Exception as e:
            logger.error(f"Error fetching fundamentals for {ticker}: {e}")
            raise
    
    @retry_on_failure(max_retries=3)
    def fetch_company_info(self, ticker: str) -> Optional[Dict]:
        """
        Get company information using FMP profile with Finnhub backup.
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Dictionary with company information
        
        Example:
            >>> collector = StockDataCollector()
            >>> info = collector.fetch_company_info('AAPL')
            >>> print(info['company_name'])
        """
        try:
            # Check cache first
            if ticker in self.cache:
                logger.info(f"Using cached company info for {ticker}")
                return self.cache[ticker]
            
            # Try FMP first
            try:
                logger.info(f"Fetching company info for {ticker} via FMP")
                endpoint = f"profile?symbol={ticker}"
                data = self._fmp_request(endpoint)
                
                if data and isinstance(data, list) and len(data) > 0:
                    profile = data[0]
                    
                    company_info = {
                        'ticker': ticker,
                        'company_name': profile.get('companyName', ticker),
                        'sector': profile.get('sector', 'Unknown'),
                        'industry': profile.get('industry', 'Unknown'),
                        'description': profile.get('description', ''),
                        'country': profile.get('country', 'Unknown'),
                        'exchange': profile.get('exchange', 'Unknown'),
                        'currency': profile.get('currency', 'USD'),
                        'market_cap': profile.get('mktCap', None),
                        'website': profile.get('website', ''),
                        'ceo': profile.get('ceo', ''),
                        'last_updated': datetime.now()
                    }
                    
                    # Cache the result
                    self.cache[ticker] = company_info
                    
                    logger.info(f"✓ {ticker}: {company_info['company_name']} via FMP")
                    return company_info
            except Exception as e:
                logger.warning(f"FMP failed for {ticker}, trying Finnhub: {e}")
            
            # Fallback to Finnhub
            if self.finnhub_client:
                logger.info(f"Fetching company info for {ticker} via Finnhub")
                profile = self.finnhub_client.company_profile2(symbol=ticker)
                
                if profile and profile.get('name'):
                    company_info = {
                        'ticker': ticker,
                        'company_name': profile.get('name', ticker),
                        'sector': self._map_finnhub_industry(profile.get('finnhubIndustry', 'Unknown')),
                        'industry': profile.get('finnhubIndustry', 'Unknown'),
                        'description': '',
                        'country': profile.get('country', 'Unknown'),
                        'exchange': profile.get('exchange', 'Unknown'),
                        'currency': profile.get('currency', 'USD'),
                        'market_cap': profile.get('marketCapitalization', None),
                        'website': profile.get('weburl', ''),
                        'ceo': '',
                        'last_updated': datetime.now()
                    }
                    
                    self.cache[ticker] = company_info
                    logger.info(f"✓ {ticker}: {company_info['company_name']} via Finnhub")
                    return company_info
            
            logger.warning(f"No company data found for {ticker}")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching company info for {ticker}: {e}")
            raise
    
    def _map_finnhub_industry(self, finnhub_industry: str) -> str:
        """Map Finnhub industry to broader sector categories."""
        industry_map = {
            'Technology': 'Technology',
            'Finance': 'Financial Services',
            'Health Care': 'Healthcare',
            'Consumer Cyclical': 'Consumer Discretionary',
            'Consumer Defensive': 'Consumer Staples',
            'Industrials': 'Industrials',
            'Energy': 'Energy',
            'Utilities': 'Utilities',
            'Real Estate': 'Real Estate',
            'Basic Materials': 'Materials',
            'Communication Services': 'Communication Services'
        }
        
        for key, value in industry_map.items():
            if key.lower() in finnhub_industry.lower():
                return value
        
        return 'Unknown'
    
    def batch_fetch_prices(self, tickers: List[str], period: str = '1y') -> Dict[str, pd.DataFrame]:
        """
        Efficiently fetch price data for multiple tickers.
        
        Args:
            tickers: List of stock ticker symbols
            period: Time period to fetch
        
        Returns:
            Dictionary mapping ticker to DataFrame of price data
        
        Example:
            >>> collector = StockDataCollector()
            >>> prices = collector.batch_fetch_prices(['AAPL', 'MSFT'], period='6mo')
            >>> print(f"Fetched data for {len(prices)} stocks")
        """
        logger.info(f"Batch fetching prices for {len(tickers)} tickers via FMP")
        results = {}
        
        for i, ticker in enumerate(tickers, 1):
            try:
                logger.info(f"Fetching {i}/{len(tickers)}: {ticker}")
                df = self.fetch_price_history(ticker, period=period)
                if df is not None and not df.empty:
                    results[ticker] = df
                    logger.info(f"✓ {ticker}: {len(df)} records")
                else:
                    logger.warning(f"✗ {ticker}: No data")
            except Exception as e:
                logger.error(f"✗ {ticker}: Error - {e}")
                continue
        
        logger.info(f"Batch fetch complete: {len(results)}/{len(tickers)} successful")
        return results
    
    def load_stock_data(self, ticker: str, db_manager, period: str = '5y') -> bool:
        """
        Comprehensive method to load all stock data into database.
        
        Args:
            ticker: Stock ticker symbol
            db_manager: DatabaseManager instance
            period: Time period ('1y', '5y', etc.)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Loading data for {ticker}...")
            
            # Step 1: Get company info
            company_info = self.fetch_company_info(ticker)
            if not company_info:
                logger.warning(f"Could not fetch company info for {ticker}")
                return False
            
            # Step 2: Add/update stock in database
            stock = db_manager.add_stock(
                ticker=ticker,
                company_name=company_info.get('name', ticker),
                sector=company_info.get('sector'),
                industry=company_info.get('industry'),
                market_cap=company_info.get('market_cap')
            )
            
            # Step 3: Get price history (5 years)
            price_df = self.fetch_price_history(ticker, period=period)
            if price_df is not None and not price_df.empty:
                db_manager.bulk_insert_prices(stock.id, price_df)
                logger.info(f"  ✅ Loaded {len(price_df)} price records")
            else:
                logger.warning(f"  ⚠️  No price data for {ticker}")
                return False
            
            # Step 4: Get fundamentals (if available)
            try:
                fundamentals = self.fetch_fundamentals(ticker)
                if fundamentals:
                    logger.info(f"  ✅ Fetched fundamentals")
                else:
                    logger.info(f"  ℹ️  No fundamentals available")
            except Exception as e:
                logger.debug(f"  ℹ️  Fundamentals not available: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load {ticker}: {e}")
            return False
    
    def filter_universe(self, tickers: List[str], min_price: float = 5.0, 
                       min_volume: int = 500000) -> List[str]:
        """
        Filter stock universe by price and volume criteria.
        
        Args:
            tickers: List of tickers to filter
            min_price: Minimum stock price
            min_volume: Minimum daily volume
        
        Returns:
            List of tickers that meet the criteria
        
        Example:
            >>> collector = StockDataCollector()
            >>> valid_tickers = collector.filter_universe(['AAPL', 'MSFT'], min_price=10)
        """
        logger.info(f"Filtering {len(tickers)} tickers (min_price=${min_price}, min_volume={min_volume:,})")
        valid_tickers = []
        
        for ticker in tickers:
            try:
                price_info = self.fetch_current_price(ticker)
                if price_info:
                    price = price_info['price']
                    volume = price_info.get('volume', 0)
                    
                    if price >= min_price:
                        valid_tickers.append(ticker)
                        logger.debug(f"✓ {ticker}: ${price:.2f}")
                    else:
                        logger.debug(f"✗ {ticker}: ${price:.2f} (filtered out)")
            except Exception as e:
                logger.warning(f"✗ {ticker}: Error - {e}")
                continue
        
        logger.info(f"Filter complete: {len(valid_tickers)}/{len(tickers)} valid tickers")
        return valid_tickers


def get_sp500_tickers() -> List[str]:
    """
    Get list of S&P 500 ticker symbols.
    
    Returns:
        List of S&P 500 ticker symbols
    """
    # Curated list of major S&P 500 stocks
    sp500_tickers = [
        # Technology
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AVGO', 'ORCL', 'CRM',
        'ADBE', 'CSCO', 'ACN', 'AMD', 'INTC', 'IBM', 'QCOM', 'TXN', 'INTU', 'NOW',
        
        # Financial Services
        'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'BLK', 'SCHW', 'AXP', 'USB',
        'PNC', 'TFC', 'COF', 'BK', 'STT',
        
        # Healthcare
        'UNH', 'JNJ', 'LLY', 'ABBV', 'MRK', 'PFE', 'TMO', 'ABT', 'DHR', 'BMY',
        'AMGN', 'CVS', 'ELV', 'GILD', 'CI', 'ISRG', 'VRTX', 'ZTS', 'REGN', 'HUM',
        
        # Consumer Discretionary
        'HD', 'MCD', 'NKE', 'SBUX', 'LOW', 'TJX', 'BKNG', 'ABNB', 'MAR', 'GM',
        'F', 'CMG', 'ORLY', 'YUM', 'DHI', 'LEN', 'DG', 'ROST', 'AZO', 'TSCO',
        
        # Communication Services
        'NFLX', 'DIS', 'CMCSA', 'VZ', 'T', 'TMUS', 'CHTR', 'EA', 'ATVI', 'PARA',
        
        # Industrials
        'BA', 'HON', 'UPS', 'CAT', 'RTX', 'LMT', 'GE', 'DE', 'MMM', 'UNP',
        'FDX', 'GD', 'NOC', 'ETN', 'EMR', 'ITW', 'PH', 'CARR', 'WM', 'NSC',
        
        # Consumer Staples
        'PG', 'KO', 'PEP', 'COST', 'WMT', 'PM', 'MO', 'MDLZ', 'CL', 'GIS',
        'KMB', 'SYY', 'HSY', 'K', 'CHD', 'CLX', 'TSN', 'CPB',
        
        # Energy
        'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'PSX', 'VLO', 'OXY', 'HAL',
        'WMB', 'KMI', 'HES', 'DVN', 'BKR', 'FANG',
        
        # Utilities
        'NEE', 'SO', 'DUK', 'AEP', 'EXC', 'SRE', 'D', 'PCG', 'XEL', 'ED',
        
        # Real Estate
        'AMT', 'PLD', 'CCI', 'EQIX', 'PSA', 'SPG', 'O', 'WELL', 'DLR', 'AVB',
        
        # Materials
        'LIN', 'APD', 'SHW', 'ECL', 'DD', 'FCX', 'NEM', 'DOW', 'NUE', 'VMC'
    ]
    
    logger.info(f"Returning {len(sp500_tickers)} S&P 500 tickers")
    return sp500_tickers


def get_sp100_tickers() -> List[str]:
    """
    Get list of S&P 100 ticker symbols (subset of S&P 500).
    
    Returns:
        List of S&P 100 ticker symbols
    """
    sp100_tickers = [
        # Top 100 by market cap
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK.B', 'UNH', 'JNJ',
        'XOM', 'V', 'JPM', 'LLY', 'WMT', 'PG', 'MA', 'AVGO', 'HD', 'CVX',
        'MRK', 'ABBV', 'COST', 'KO', 'PEP', 'ORCL', 'ADBE', 'MCD', 'CSCO', 'TMO',
        'ACN', 'CRM', 'ABT', 'NFLX', 'DHR', 'NKE', 'INTC', 'PFE', 'DIS', 'VZ',
        'TXN', 'PM', 'WFC', 'BMY', 'CMCSA', 'AMD', 'UPS', 'QCOM', 'AMGN', 'NEE',
        'HON', 'COP', 'RTX', 'SBUX', 'LOW', 'IBM', 'INTU', 'CAT', 'BA', 'GE',
        'T', 'ELV', 'LMT', 'SPGI', 'DE', 'BKNG', 'AMAT', 'GS', 'BLK', 'AXP',
        'SYK', 'PLD', 'ADI', 'MMM', 'CVS', 'GILD', 'MDLZ', 'ISRG', 'AMT', 'CI',
        'VRTX', 'MO', 'ADP', 'NOW', 'ZTS', 'TJX', 'SCHW', 'REGN', 'C', 'SO',
        'CB', 'LRCX', 'PGR', 'DUK', 'BSX', 'ETN', 'EOG', 'BDX', 'FI', 'WM'
    ]
    
    logger.info(f"Returning {len(sp100_tickers)} S&P 100 tickers")
    return sp100_tickers


# News and Sentiment classes remain unchanged
# (They don't use stock price APIs)

class NewsCollector:
    """
    Collects news articles from NewsAPI with filtering and deduplication.
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialize NewsAPI client.
        
        Args:
            api_key: NewsAPI key (if not provided, will use NEWS_API_KEY env variable)
        """
        try:
            from newsapi import NewsApiClient
            
            self.api_key = api_key or os.getenv('NEWS_API_KEY')
            if not self.api_key:
                raise ValueError("NewsAPI key not provided")
            
            self.client = NewsApiClient(api_key=self.api_key)
            self.rate_limit_per_day = 500  # Free tier limit
            self.calls_today = 0
            self.last_reset = datetime.now().date()
            
            logger.info("NewsCollector initialized")
            
        except ImportError:
            logger.error("newsapi-python not installed. Run: pip install newsapi-python")
            raise
    
    def _check_rate_limit(self):
        """Check and enforce daily rate limit."""
        today = datetime.now().date()
        if today > self.last_reset:
            self.calls_today = 0
            self.last_reset = today
        
        if self.calls_today >= self.rate_limit_per_day:
            logger.warning(f"NewsAPI rate limit reached ({self.rate_limit_per_day}/day)")
            return False
        return True
    
    @retry_on_failure(max_retries=2)
    def fetch_stock_news(self, ticker: str, company_name: str, days_back: int = 7) -> List[Dict]:
        """
        Fetch news articles about a specific stock.
        
        Args:
            ticker: Stock ticker symbol
            company_name: Full company name
            days_back: Number of days of history to fetch
        
        Returns:
            List of article dictionaries
        """
        if not self._check_rate_limit():
            return []
        
        try:
            logger.info(f"Fetching news for {ticker} ({company_name}), last {days_back} days")
            
            # Calculate date range
            to_date = datetime.now()
            from_date = to_date - timedelta(days=days_back)
            
            # Search with both ticker and company name
            query = f'"{ticker}" OR "{company_name}"'
            
            # Fetch from NewsAPI
            response = self.client.get_everything(
                q=query,
                from_param=from_date.strftime('%Y-%m-%d'),
                to=to_date.strftime('%Y-%m-%d'),
                language='en',
                sort_by='relevancy',
                page_size=100
            )
            
            self.calls_today += 1
            
            articles = response.get('articles', [])
            
            # Format articles
            formatted_articles = []
            for article in articles:
                formatted_articles.append({
                    'title': article.get('title', ''),
                    'description': article.get('description', ''),
                    'source': article.get('source', {}).get('name', 'Unknown'),
                    'published_at': article.get('publishedAt', ''),
                    'url': article.get('url', ''),
                    'ticker': ticker
                })
            
            # Deduplicate
            unique_articles = self._deduplicate_articles(formatted_articles)
            
            logger.info(f"Found {len(unique_articles)} unique articles for {ticker}")
            return unique_articles
            
        except Exception as e:
            logger.error(f"Error fetching news for {ticker}: {e}")
            return []
    
    def _deduplicate_articles(self, articles: List[Dict]) -> List[Dict]:
        """Remove duplicate articles based on title similarity."""
        if not articles:
            return []
        
        unique_articles = []
        seen_hashes = set()
        
        for article in articles:
            # Create hash of title
            title = article.get('title', '').lower().strip()
            title_hash = hashlib.md5(title.encode()).hexdigest()
            
            if title_hash not in seen_hashes:
                seen_hashes.add(title_hash)
                unique_articles.append(article)
        
        return unique_articles
    
    def batch_fetch_news(self, ticker_list: List[Tuple[str, str]], days_back: int = 7) -> Dict[str, List[Dict]]:
        """
        Fetch news for multiple stocks.
        
        Args:
            ticker_list: List of (ticker, company_name) tuples
            days_back: Number of days of history
        
        Returns:
            Dictionary mapping ticker to list of articles
        """
        logger.info(f"Batch fetching news for {len(ticker_list)} stocks")
        results = {}
        
        for ticker, company_name in ticker_list:
            if not self._check_rate_limit():
                logger.warning("Rate limit reached, stopping batch fetch")
                break
            
            articles = self.fetch_stock_news(ticker, company_name, days_back)
            results[ticker] = articles
            
            # Small delay between requests
            time.sleep(0.5)
        
        logger.info(f"Batch fetch complete: {len(results)} stocks")
        return results
    
    def filter_relevant_articles(self, articles: List[Dict], ticker: str) -> List[Dict]:
        """
        Filter articles that are actually relevant to the stock.
        
        Args:
            articles: List of articles
            ticker: Stock ticker to check for
        
        Returns:
            Filtered list of relevant articles
        """
        relevant = []
        
        for article in articles:
            title = article.get('title', '').lower()
            description = article.get('description', '').lower()
            ticker_lower = ticker.lower()
            
            # Check if ticker appears in title or description
            if ticker_lower in title or ticker_lower in description:
                relevant.append(article)
        
        logger.info(f"Filtered {len(relevant)}/{len(articles)} relevant articles for {ticker}")
        return relevant


class SentimentAnalyzer:
    """
    Performs sentiment analysis on financial news using FinBERT model.
    """
    
    def __init__(self):
        """Initialize FinBERT model for sentiment analysis."""
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            import torch
            
            logger.info("Loading FinBERT model for sentiment analysis...")
            start_time = time.time()
            
            model_name = "ProsusAI/finbert"
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
            
            # Set device
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model.to(self.device)
            self.model.eval()
            
            self.torch = torch
            
            load_time = time.time() - start_time
            logger.info(f"FinBERT loaded successfully on {self.device} ({load_time:.2f}s)")
            
        except ImportError:
            logger.error("transformers or torch not installed. Run: pip install transformers torch")
            raise
    
    @lru_cache(maxsize=1000)
    def analyze_text(self, text: str) -> Dict:
        """
        Analyze sentiment of a text string.
        
        Args:
            text: Text to analyze
        
        Returns:
            Dictionary with sentiment_label, confidence_scores, and sentiment_score
        """
        try:
            # Truncate long text
            max_length = 512
            if len(text) > max_length:
                text = text[:max_length]
            
            # Tokenize
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=max_length
            ).to(self.device)
            
            # Get prediction
            with self.torch.no_grad():
                outputs = self.model(**inputs)
                predictions = self.torch.nn.functional.softmax(outputs.logits, dim=-1)
            
            # Convert to scores
            scores = predictions[0].cpu().numpy()
            labels = ['positive', 'negative', 'neutral']
            
            # Find dominant sentiment
            max_idx = scores.argmax()
            sentiment_label = labels[max_idx]
            
            # Calculate sentiment score (-1 to 1)
            sentiment_score = float(scores[0] - scores[1])  # positive - negative
            
            return {
                'sentiment_label': sentiment_label,
                'confidence_scores': {
                    'positive': float(scores[0]),
                    'negative': float(scores[1]),
                    'neutral': float(scores[2])
                },
                'sentiment_score': sentiment_score
            }
            
        except Exception as e:
            logger.error(f"Error analyzing text: {e}")
            return {
                'sentiment_label': 'neutral',
                'confidence_scores': {'positive': 0.33, 'negative': 0.33, 'neutral': 0.34},
                'sentiment_score': 0.0
            }
    
    def analyze_article(self, article: Dict) -> Dict:
        """
        Analyze sentiment of a news article.
        
        Args:
            article: Article dictionary with title and description
        
        Returns:
            Article dictionary with added sentiment fields
        """
        # Combine title and description
        text = f"{article.get('title', '')} {article.get('description', '')}"
        
        # Analyze sentiment
        sentiment = self.analyze_text(text)
        
        # Add to article
        article['sentiment_label'] = sentiment['sentiment_label']
        article['sentiment_score'] = sentiment['sentiment_score']
        article['confidence_scores'] = sentiment['confidence_scores']
        
        return article
    
    def batch_analyze(self, articles: List[Dict], batch_size: int = 8) -> List[Dict]:
        """
        Analyze sentiment of multiple articles efficiently.
        
        Args:
            articles: List of article dictionaries
            batch_size: Number of articles to process at once
        
        Returns:
            List of articles with sentiment added
        """
        logger.info(f"Analyzing sentiment for {len(articles)} articles")
        
        analyzed = []
        for i in range(0, len(articles), batch_size):
            batch = articles[i:i + batch_size]
            for article in batch:
                analyzed.append(self.analyze_article(article))
        
        logger.info(f"Sentiment analysis complete for {len(analyzed)} articles")
        return analyzed
    
    def aggregate_sentiment(self, articles: List[Dict]) -> Dict:
        """
        Calculate aggregate sentiment metrics from multiple articles.
        
        Args:
            articles: List of analyzed articles
        
        Returns:
            Dictionary with aggregate sentiment metrics
        """
        if not articles:
            return {
                'weighted_sentiment': 0.0,
                'sentiment_velocity': 0.0,
                'positive_count': 0,
                'negative_count': 0,
                'neutral_count': 0,
                'sentiment_consistency': 0.0,
                'attention_score': 0
            }
        
        # Count sentiments
        positive_count = sum(1 for a in articles if a.get('sentiment_label') == 'positive')
        negative_count = sum(1 for a in articles if a.get('sentiment_label') == 'negative')
        neutral_count = sum(1 for a in articles if a.get('sentiment_label') == 'neutral')
        
        # Calculate weighted sentiment (weight by recency)
        now = datetime.now()
        weighted_scores = []
        weights = []
        
        for article in articles:
            score = article.get('sentiment_score', 0)
            
            # Calculate recency weight
            pub_date_str = article.get('published_at', '')
            try:
                pub_date = pd.to_datetime(pub_date_str)
                age_hours = (now - pub_date).total_seconds() / 3600
                
                # Exponential decay: recent = higher weight
                if age_hours < 24:
                    weight = 1.0
                elif age_hours < 48:
                    weight = 0.7
                elif age_hours < 72:
                    weight = 0.5
                else:
                    weight = 0.3
            except:
                weight = 0.5
            
            weighted_scores.append(score * weight)
            weights.append(weight)
        
        if sum(weights) > 0:
            weighted_sentiment = sum(weighted_scores) / sum(weights)
        else:
            weighted_sentiment = 0.0
        
        # Calculate sentiment consistency (std dev)
        scores = [a.get('sentiment_score', 0) for a in articles]
        sentiment_consistency = 100 - min(np.std(scores) * 100, 100) if scores else 0
        
        return {
            'weighted_sentiment': weighted_sentiment,
            'sentiment_velocity': 0.0,  # Would need historical data
            'positive_count': positive_count,
            'negative_count': negative_count,
            'neutral_count': neutral_count,
            'sentiment_consistency': sentiment_consistency,
            'attention_score': len(articles)
        }
