"""
Data pipeline for orchestrating all data collection and updates.
Coordinates stock data, fundamentals, news, and sentiment analysis.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from data import DatabaseManager, Stock, StockPrice, Fundamental, NewsArticle, Recommendation
from data.collectors import StockDataCollector, NewsCollector, SentimentAnalyzer, get_sp500_tickers
import pandas as pd
import numpy as np

# Configure logging
logger = logging.getLogger(__name__)


class DataPipeline:
    """
    Orchestrates data collection, processing, and storage.
    Coordinates stock prices, fundamentals, news, and sentiment analysis.
    """
    
    def __init__(self, db_manager: DatabaseManager, stock_collector: StockDataCollector,
                 news_collector: NewsCollector, sentiment_analyzer: SentimentAnalyzer):
        """
        Initialize DataPipeline with all collectors.
        
        Args:
            db_manager: Database manager instance
            stock_collector: Stock data collector
            news_collector: News collector
            sentiment_analyzer: Sentiment analyzer
        
        Example:
            >>> from data import DatabaseManager, StockDataCollector
            >>> from data import NewsCollector, SentimentAnalyzer
            >>> 
            >>> db = DatabaseManager('sqlite:///smartinvest.db')
            >>> stock_collector = StockDataCollector()
            >>> news_collector = NewsCollector(api_key='your_key')
            >>> sentiment_analyzer = SentimentAnalyzer()
            >>> 
            >>> pipeline = DataPipeline(db, stock_collector, news_collector, sentiment_analyzer)
        """
        self.db_manager = db_manager
        self.stock_collector = stock_collector
        self.news_collector = news_collector
        self.sentiment_analyzer = sentiment_analyzer
        
        # Initialize database tables
        self.db_manager.create_all_tables()
        
        # State tracking
        self.last_update_time = None
        self.update_stats = {}
        
        logger.info("DataPipeline initialized")
    
    def update_stock_universe(self, config_stock_universe: List[str] = None,
                             min_price: float = 5.0, min_volume: int = 500000) -> List[str]:
        """
        Update stock universe in database.
        
        Args:
            config_stock_universe: Pre-configured list of tickers (optional)
            min_price: Minimum stock price filter
            min_volume: Minimum volume filter
        
        Returns:
            List of valid ticker symbols
        
        Example:
            >>> valid_tickers = pipeline.update_stock_universe(min_price=10, min_volume=1000000)
            >>> print(f"Valid tickers: {len(valid_tickers)}")
        """
        logger.info("=" * 60)
        logger.info("Updating Stock Universe")
        logger.info("=" * 60)
        
        start_time = time.time()
        
        # Get ticker list
        if config_stock_universe:
            tickers = config_stock_universe
            logger.info(f"Using configured universe: {len(tickers)} tickers")
        else:
            # Fetch S&P 500
            tickers = get_sp500_tickers()
            logger.info(f"Fetched {len(tickers)} S&P 500 tickers")
        
        # Filter by criteria
        valid_tickers = self.stock_collector.filter_universe(tickers, min_price, min_volume)
        logger.info(f"Filtered to {len(valid_tickers)} valid tickers")
        
        # Update database
        added_count = 0
        updated_count = 0
        
        for ticker in valid_tickers:
            try:
                # Fetch company info
                company_info = self.stock_collector.fetch_company_info(ticker)
                
                if not company_info:
                    logger.warning(f"Could not fetch company info for {ticker}")
                    continue
                
                # Check if stock exists
                existing = self.db_manager.get_stock_by_ticker(ticker)
                
                if existing:
                    # Update existing
                    self.db_manager.add_stock(
                        ticker=ticker,
                        company_name=company_info['company_name'],
                        sector=company_info['sector'],
                        industry=company_info['industry'],
                        market_cap=company_info.get('market_cap')
                    )
                    updated_count += 1
                else:
                    # Add new stock
                    self.db_manager.add_stock(
                        ticker=ticker,
                        company_name=company_info['company_name'],
                        sector=company_info['sector'],
                        industry=company_info['industry'],
                        market_cap=company_info.get('market_cap')
                    )
                    added_count += 1
                
            except Exception as e:
                logger.error(f"Error updating {ticker}: {e}")
                continue
        
        elapsed = time.time() - start_time
        logger.info(f"Stock universe updated: +{added_count} new, {updated_count} updated, {elapsed:.1f}s")
        
        # Store stats
        self.update_stats['stocks_added'] = added_count
        self.update_stats['stocks_updated'] = updated_count
        self.update_stats['total_stocks'] = len(valid_tickers)
        
        return valid_tickers
    
    def update_price_data(self, tickers: List[str], period: str = '1y') -> Dict[str, bool]:
        """
        Fetch and store historical price data for all tickers.
        
        Args:
            tickers: List of ticker symbols
            period: Time period for historical data
        
        Returns:
            Dictionary mapping ticker to success/failure status
        
        Example:
            >>> results = pipeline.update_price_data(['AAPL', 'MSFT'])
            >>> print(f"Success: {sum(results.values())}/{len(results)}")
        """
        logger.info("=" * 60)
        logger.info(f"Updating Price Data for {len(tickers)} stocks")
        logger.info("=" * 60)
        
        start_time = time.time()
        
        # Batch fetch prices
        batch_results = {}
        price_data = self.stock_collector.batch_fetch_prices(tickers, period=period)
        
        successful = 0
        failed = 0
        
        # Store price data in database
        for ticker, df in price_data.items():
            try:
                # Get stock from database
                stock = self.db_manager.get_stock_by_ticker(ticker)
                if not stock:
                    logger.warning(f"Stock {ticker} not found in database, skipping")
                    batch_results[ticker] = False
                    failed += 1
                    continue
                
                # Bulk insert prices
                self.db_manager.bulk_insert_prices(stock.id, df)
                batch_results[ticker] = True
                successful += 1
                logger.info(f"✓ {ticker}: {len(df)} price records")
                
            except Exception as e:
                logger.error(f"✗ {ticker}: {e}")
                batch_results[ticker] = False
                failed += 1
        
        elapsed = time.time() - start_time
        logger.info(f"Price data updated: {successful} successful, {failed} failed, {elapsed:.1f}s")
        
        self.update_stats['price_update_success'] = successful
        self.update_stats['price_update_failed'] = failed
        
        return batch_results
    
    def update_fundamental_data(self, tickers: List[str]) -> Dict[str, Optional[Dict]]:
        """
        Fetch and store fundamental analysis data.
        
        Args:
            tickers: List of ticker symbols
        
        Returns:
            Dictionary mapping ticker to fundamental metrics
        
        Example:
            >>> fundamentals = pipeline.update_fundamental_data(['AAPL', 'MSFT'])
            >>> print(fundamentals['AAPL']['pe_ratio'])
        """
        logger.info("=" * 60)
        logger.info(f"Updating Fundamental Data for {len(tickers)} stocks")
        logger.info("=" * 60)
        
        start_time = time.time()
        
        results = {}
        successful = 0
        failed = 0
        
        for i, ticker in enumerate(tickers, 1):
            try:
                # Get stock from database
                stock = self.db_manager.get_stock_by_ticker(ticker)
                if not stock:
                    results[ticker] = None
                    continue
                
                # Fetch fundamentals
                fundamentals = self.stock_collector.fetch_fundamentals(ticker)
                
                if fundamentals:
                    # Store in database
                    with self.db_manager.get_session() as session:
                        # Check if fundamental data exists
                        existing = session.query(Fundamental).filter_by(
                            stock_id=stock.id,
                            date=datetime.now().date()
                        ).first()
                        
                        if not existing:
                            # Create new fundamental record
                            fundamental = Fundamental(
                                stock_id=stock.id,
                                date=datetime.now(),
                                pe_ratio=fundamentals.get('pe_ratio'),
                                pb_ratio=fundamentals.get('pb_ratio'),
                                ps_ratio=fundamentals.get('ps_ratio'),
                                debt_to_equity=fundamentals.get('debt_to_equity'),
                                current_ratio=fundamentals.get('current_ratio'),
                                quick_ratio=fundamentals.get('quick_ratio'),
                                roe=fundamentals.get('roe'),
                                roa=fundamentals.get('roa'),
                                profit_margin=fundamentals.get('profit_margin'),
                                revenue_growth=fundamentals.get('revenue_growth'),
                                earnings_growth=fundamentals.get('earnings_growth')
                            )
                            session.add(fundamental)
                    
                    results[ticker] = fundamentals
                    successful += 1
                    
                    if i % 10 == 0:
                        logger.info(f"Progress: {i}/{len(tickers)}")
                
                else:
                    results[ticker] = None
                    failed += 1
                
            except Exception as e:
                logger.error(f"Error updating fundamentals for {ticker}: {e}")
                results[ticker] = None
                failed += 1
        
        elapsed = time.time() - start_time
        logger.info(f"Fundamental data updated: {successful} successful, {failed} failed, {elapsed:.1f}s")
        
        self.update_stats['fundamentals_updated'] = successful
        self.update_stats['fundamentals_failed'] = failed
        
        return results
    
    def update_news_and_sentiment(self, tickers: List[str], days_back: int = 7) -> Dict[str, Dict]:
        """
        Fetch news and analyze sentiment for stocks.
        
        Args:
            tickers: List of ticker symbols
            days_back: Number of days to look back for news
        
        Returns:
            Dictionary mapping ticker to sentiment metrics
        
        Example:
            >>> sentiment = pipeline.update_news_and_sentiment(['AAPL'], days_back=3)
            >>> print(f"AAPL sentiment: {sentiment['AAPL']['weighted_sentiment']:.3f}")
        """
        logger.info("=" * 60)
        logger.info(f"Updating News & Sentiment for {len(tickers)} stocks")
        logger.info("=" * 60)
        
        start_time = time.time()
        
        # Fetch company names for news search
        ticker_company_pairs = []
        for ticker in tickers:
            try:
                stock = self.db_manager.get_stock_by_ticker(ticker)
                if stock:
                    ticker_company_pairs.append((ticker, stock.company_name))
            except Exception as e:
                logger.warning(f"Could not get company name for {ticker}: {e}")
        
        # Batch fetch news
        logger.info("Fetching news articles...")
        news_data = self.news_collector.batch_fetch_news(ticker_company_pairs, days_back=days_back)
        
        # Analyze sentiment
        results = {}
        analyzed_count = 0
        
        for ticker, articles in news_data.items():
            try:
                # Filter relevant articles
                stock = self.db_manager.get_stock_by_ticker(ticker)
                if not stock:
                    continue
                
                relevant_articles = self.news_collector.filter_relevant_articles(
                    articles, ticker, stock.company_name if stock else None
                )
                
                if not relevant_articles:
                    results[ticker] = {
                        'weighted_sentiment': 0.0,
                        'attention_score': 0,
                        'article_count': 0
                    }
                    continue
                
                # Analyze sentiment
                analyzed = self.sentiment_analyzer.batch_analyze(relevant_articles)
                
                # Calculate aggregate sentiment
                metrics = self.sentiment_analyzer.aggregate_sentiment(analyzed)
                results[ticker] = metrics
                
                # Store articles in database
                for article in analyzed[:10]:  # Limit to 10 most recent
                    try:
                        with self.db_manager.get_session() as session:
                            # Check if article already exists
                            existing = session.query(NewsArticle).filter_by(
                                stock_id=stock.id,
                                url=article.get('url', '')
                            ).first()
                            
                            if not existing and article.get('url'):
                                news_article = NewsArticle(
                                    stock_id=stock.id,
                                    published_at=article.get('published_at', datetime.now()),
                                    title=article.get('title', ''),
                                    source=article.get('source', ''),
                                    url=article.get('url', ''),
                                    sentiment_score=article.get('sentiment_score', 0.0),
                                    sentiment_label=article.get('sentiment_label', 'neutral')
                                )
                                session.add(news_article)
                    except Exception as e:
                        logger.debug(f"Error storing article for {ticker}: {e}")
                        continue
                
                analyzed_count += 1
                logger.info(f"✓ {ticker}: {len(analyzed)} articles, sentiment={metrics['weighted_sentiment']:.3f}")
                
            except Exception as e:
                logger.error(f"Error processing news for {ticker}: {e}")
                results[ticker] = {
                    'weighted_sentiment': 0.0,
                    'attention_score': 0,
                    'article_count': 0
                }
        
        elapsed = time.time() - start_time
        logger.info(f"News & sentiment updated: {analyzed_count} stocks, {elapsed:.1f}s")
        
        self.update_stats['sentiment_updated'] = analyzed_count
        
        return results
    
    def run_full_update(self, skip_prices: bool = False) -> Dict:
        """
        Run complete data update pipeline.
        
        Args:
            skip_prices: Skip price data update (faster for testing)
        
        Returns:
            Dictionary with update statistics
        
        Example:
            >>> result = pipeline.run_full_update()
            >>> print(f"Updated {result['stocks_updated']} stocks in {result['duration']:.1f}s")
        """
        logger.info("")
        logger.info("=" * 60)
        logger.info("STARTING FULL DATA UPDATE")
        logger.info("=" * 60)
        
        pipeline_start = time.time()
        
        try:
            # Step 1: Update stock universe
            logger.info("\n📊 Step 1: Update Stock Universe")
            valid_tickers = self.update_stock_universe()
            
            # Step 2: Update price data
            if not skip_prices:
                logger.info("\n📈 Step 2: Update Price Data")
                price_results = self.update_price_data(valid_tickers)
            else:
                logger.info("\n⏭️  Step 2: Skipping Price Data Update")
                price_results = {}
            
            # Step 3: Update fundamentals
            logger.info("\n📊 Step 3: Update Fundamental Data")
            fundamental_results = self.update_fundamental_data(valid_tickers)
            
            # Step 4: Update news & sentiment
            logger.info("\n📰 Step 4: Update News & Sentiment")
            sentiment_results = self.update_news_and_sentiment(valid_tickers)
            
            # Calculate total duration
            total_duration = time.time() - pipeline_start
            
            # Build summary
            summary = {
                'success': True,
                'duration': total_duration,
                'tickers_processed': len(valid_tickers),
                'stocks_added': self.update_stats.get('stocks_added', 0),
                'stocks_updated': self.update_stats.get('stocks_updated', 0),
                'price_updates_success': self.update_stats.get('price_update_success', 0),
                'fundamentals_updated': self.update_stats.get('fundamentals_updated', 0),
                'sentiment_updated': self.update_stats.get('sentiment_updated', 0),
                'timestamp': datetime.now()
            }
            
            logger.info("")
            logger.info("=" * 60)
            logger.info("FULL UPDATE COMPLETE")
            logger.info("=" * 60)
            logger.info(f"Duration: {total_duration:.1f}s")
            logger.info(f"Tickers processed: {len(valid_tickers)}")
            logger.info(f"Stocks added: {summary['stocks_added']}")
            logger.info(f"Fundamentals updated: {summary['fundamentals_updated']}")
            logger.info(f"Sentiment analyzed: {summary['sentiment_updated']}")
            logger.info("=" * 60)
            
            self.last_update_time = datetime.now()
            return summary
            
        except Exception as e:
            logger.error(f"Pipeline update failed: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                'success': False,
                'duration': time.time() - pipeline_start,
                'error': str(e),
                'timestamp': datetime.now()
            }
    
    def quick_refresh(self, tickers: List[str] = None) -> List[str]:
        """
        Quick intraday refresh (lightweight update).
        
        Args:
            tickers: Optional list of specific tickers to refresh
        
        Returns:
            List of updated ticker symbols
        
        Example:
            >>> updated = pipeline.quick_refresh(['AAPL', 'MSFT'])
            >>> print(f"Refreshed {len(updated)} stocks")
        """
        logger.info("=" * 60)
        logger.info("QUICK REFRESH")
        logger.info("=" * 60)
        
        start_time = time.time()
        
        if tickers is None:
            # Get all stocks from database
            stocks = self.db_manager.get_all_stocks()
            tickers = [stock.ticker for stock in stocks]
        
        updated = []
        
        for ticker in tickers:
            try:
                # Fetch current price
                price_info = self.stock_collector.fetch_current_price(ticker)
                if price_info:
                    updated.append(ticker)
                    logger.debug(f"✓ {ticker}: ${price_info['price']:.2f}")
                    
            except Exception as e:
                logger.debug(f"✗ {ticker}: {e}")
        
        elapsed = time.time() - start_time
        logger.info(f"Quick refresh complete: {len(updated)} stocks in {elapsed:.1f}s")
        
        return updated


def get_data_freshness(db_manager: DatabaseManager) -> Dict[str, Dict]:
    """
    Check data freshness for each data type.
    
    Args:
        db_manager: Database manager instance
    
    Returns:
        Dictionary with freshness information for each data type
    
    Example:
        >>> freshness = get_data_freshness(db_manager)
        >>> print(f"Price data: {freshness['price_data']['age_hours']:.1f} hours old")
    """
    with db_manager.get_session() as session:
        # Get latest price update
        latest_price = session.query(StockPrice.date).order_by(StockPrice.date.desc()).first()
        
        # Get latest fundamental update
        latest_fundamental = session.query(Fundamental.last_updated)\
            .order_by(Fundamental.last_updated.desc()).first()
        
        # Get latest news update
        latest_news = session.query(NewsArticle.published_at)\
            .order_by(NewsArticle.published_at.desc()).first()
        
        # Get latest recommendation
        latest_rec = session.query(Recommendation.created_at)\
            .order_by(Recommendation.created_at.desc()).first()
        
        now = datetime.now()
        
        def calculate_age(timestamp):
            if timestamp is None:
                return None
            if isinstance(timestamp, tuple):
                timestamp = timestamp[0]
            delta = now - timestamp
            return {
                'timestamp': timestamp,
                'age_seconds': delta.total_seconds(),
                'age_hours': delta.total_seconds() / 3600,
                'age_days': delta.days
            }
        
        freshness = {
            'price_data': calculate_age(latest_price) if latest_price else None,
            'fundamental_data': calculate_age(latest_fundamental) if latest_fundamental else None,
            'news_data': calculate_age(latest_news) if latest_news else None,
            'recommendations': calculate_age(latest_rec) if latest_rec else None
        }
        
        return freshness

