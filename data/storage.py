"""
Database operations manager for SmartInvest bot.
Provides high-level interface for database operations.
"""

import logging
from contextlib import contextmanager
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
import pandas as pd

from sqlalchemy import create_engine, func, and_, desc, case
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.pool import QueuePool

from .schema import (
    Base, Stock, StockPrice, Fundamental, NewsArticle,
    Recommendation, RecommendationPerformance, UserWatchlist, UserAlert,
    UserPosition, ExitSignal
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    High-level database operations manager.
    Handles all database interactions with proper error handling and logging.
    """
    
    def __init__(self, database_url: str):
        """
        Initialize DatabaseManager with connection to database.
        
        Args:
            database_url: SQLAlchemy database URL
        """
        self.database_url = database_url
        
        # Create engine with connection pooling
        self.engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,  # Verify connections before using
            echo=False  # Set to True for SQL query logging
        )
        
        # Create session factory
        self.SessionFactory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(self.SessionFactory)
        
        logger.info(f"DatabaseManager initialized with {database_url}")
    
    def create_all_tables(self):
        """Create all tables in the database."""
        try:
            Base.metadata.create_all(self.engine)
            logger.info("✅ All database tables created successfully")
        except SQLAlchemyError as e:
            logger.error(f"❌ Error creating tables: {e}")
            raise
    
    @contextmanager
    def get_session(self):
        """
        Context manager for database sessions.
        Automatically handles commit/rollback and cleanup.
        
        Usage:
            with db_manager.get_session() as session:
                stock = session.query(Stock).first()
        """
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Session error: {e}")
            raise
        finally:
            session.close()
    
    # ==================== STOCK OPERATIONS ====================
    
    def add_stock(self, ticker: str, company_name: str, 
                  sector: str = None, industry: str = None,
                  market_cap: int = None) -> Stock:
        """
        Add or update stock information.
        
        Args:
            ticker: Stock ticker symbol
            company_name: Full company name
            sector: Business sector
            industry: Industry classification
            market_cap: Market capitalization
            
        Returns:
            Stock object
        """
        with self.get_session() as session:
            stock = session.query(Stock).filter_by(ticker=ticker).first()
            
            if stock:
                # Update existing stock
                stock.company_name = company_name
                stock.sector = sector
                stock.industry = industry
                stock.market_cap = market_cap
                stock.last_updated = datetime.utcnow()
                logger.info(f"Updated stock: {ticker}")
            else:
                # Create new stock
                stock = Stock(
                    ticker=ticker,
                    company_name=company_name,
                    sector=sector,
                    industry=industry,
                    market_cap=market_cap
                )
                session.add(stock)
                logger.info(f"Added new stock: {ticker}")
            
            session.flush()
            # Detach from session before returning
            session.expunge(stock)
            return stock
    
    def get_stock_by_ticker(self, ticker: str) -> Optional[Stock]:
        """
        Get stock by ticker symbol.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Stock object or None if not found
        """
        with self.get_session() as session:
            stock = session.query(Stock).filter_by(ticker=ticker).first()
            if stock:
                # Detach from session to avoid lazy loading issues
                session.expunge(stock)
            return stock
    
    def get_all_stocks(self) -> List[Stock]:
        """
        Get all stocks in the database.
        
        Returns:
            List of Stock objects
        """
        with self.get_session() as session:
            stocks = session.query(Stock).all()
            for stock in stocks:
                session.expunge(stock)
            return stocks
    
    # ==================== PRICE OPERATIONS ====================
    
    def bulk_insert_prices(self, stock_id: int, price_data_df: pd.DataFrame):
        """
        Efficiently bulk insert price data.
        
        Args:
            stock_id: Stock ID
            price_data_df: DataFrame with columns: date, open, high, low, close, volume, adjusted_close
        """
        with self.get_session() as session:
            try:
                # Prepare records for bulk insert
                records = []
                for _, row in price_data_df.iterrows():
                    records.append({
                        'stock_id': stock_id,
                        'date': row['date'],
                        'open': float(row['open']),
                        'high': float(row['high']),
                        'low': float(row['low']),
                        'close': float(row['close']),
                        'volume': int(row['volume']),
                        'adjusted_close': float(row.get('adjusted_close', row['close']))
                    })
                
                # Bulk insert
                session.bulk_insert_mappings(StockPrice, records)
                logger.info(f"Bulk inserted {len(records)} price records for stock_id={stock_id}")
                
            except IntegrityError as e:
                logger.warning(f"Some price records already exist for stock_id={stock_id}: {e}")
                # Try inserting one by one, skipping duplicates
                for record in records:
                    try:
                        session.add(StockPrice(**record))
                        session.flush()
                    except IntegrityError:
                        session.rollback()
                        continue
    
    def get_latest_price(self, stock_id: int) -> Optional[StockPrice]:
        """
        Get the most recent price for a stock.
        
        Args:
            stock_id: Stock ID
            
        Returns:
            StockPrice object or None
        """
        with self.get_session() as session:
            price = session.query(StockPrice)\
                .filter_by(stock_id=stock_id)\
                .order_by(desc(StockPrice.date))\
                .first()
            if price:
                session.expunge(price)
            return price
    
    def get_latest_fundamentals(self, stock_id: int) -> Optional[Fundamental]:
        """
        Get the most recent fundamentals for a stock.
        
        Args:
            stock_id: Stock ID
            
        Returns:
            Fundamental object or None
        """
        with self.get_session() as session:
            fundamental = session.query(Fundamental)\
                .filter_by(stock_id=stock_id)\
                .order_by(desc(Fundamental.date))\
                .first()
            if fundamental:
                session.expunge(fundamental)
            return fundamental
    
    def get_price_history(self, stock_id: int, start_date: datetime = None, 
                         end_date: datetime = None) -> List[StockPrice]:
        """
        Get price history for a stock within date range.
        
        Args:
            stock_id: Stock ID
            start_date: Start date (optional)
            end_date: End date (optional)
            
        Returns:
            List of StockPrice objects
        """
        with self.get_session() as session:
            query = session.query(StockPrice).filter_by(stock_id=stock_id)
            
            if start_date:
                query = query.filter(StockPrice.date >= start_date)
            if end_date:
                query = query.filter(StockPrice.date <= end_date)
            
            prices = query.order_by(StockPrice.date).all()
            for price in prices:
                session.expunge(price)
            return prices
    
    # ==================== NEWS OPERATIONS ====================
    
    def add_news_article(self, stock_id: int, title: str, source: str,
                        url: str, published_at: str, sentiment_score: float,
                        sentiment_label: str) -> NewsArticle:
        """
        Add a news article with sentiment analysis.
        
        Args:
            stock_id: Stock ID
            title: Article title
            source: News source
            url: Article URL
            published_at: Publication timestamp
            sentiment_score: Sentiment score (-1 to 1)
            sentiment_label: Sentiment label (positive/negative/neutral)
            
        Returns:
            NewsArticle object
        """
        with self.get_session() as session:
            # Parse published_at if string
            if isinstance(published_at, str):
                try:
                    from dateutil import parser
                    published_at = parser.parse(published_at)
                except:
                    published_at = datetime.now()
            
            article = NewsArticle(
                stock_id=stock_id,
                title=title,
                source=source,
                url=url,
                published_at=published_at,
                sentiment_score=sentiment_score,
                sentiment_label=sentiment_label
            )
            session.add(article)
            session.flush()
            session.expunge(article)
            return article
    
    def get_news_articles(self, stock_id: int, limit: int = 50) -> List[NewsArticle]:
        """
        Get news articles for a stock.
        
        Args:
            stock_id: Stock ID
            limit: Maximum number of articles to return
            
        Returns:
            List of NewsArticle objects
        """
        with self.get_session() as session:
            articles = session.query(NewsArticle)\
                .filter(NewsArticle.stock_id == stock_id)\
                .order_by(desc(NewsArticle.published_at))\
                .limit(limit)\
                .all()
            
            # Detach from session
            for article in articles:
                session.expunge(article)
            
            return articles
    
    def get_news_articles_in_range(self, stock_id: int, start_date: datetime, 
                                   end_date: datetime) -> List[NewsArticle]:
        """
        Get news articles for a stock within date range (for backtesting).
        
        Args:
            stock_id: Stock ID
            start_date: Start date (inclusive)
            end_date: End date (exclusive - don't include this date)
            
        Returns:
            List of NewsArticle objects
        """
        with self.get_session() as session:
            articles = session.query(NewsArticle)\
                .filter(NewsArticle.stock_id == stock_id)\
                .filter(NewsArticle.published_at >= start_date)\
                .filter(NewsArticle.published_at < end_date)\
                .order_by(desc(NewsArticle.published_at))\
                .all()
            
            # Detach from session
            for article in articles:
                session.expunge(article)
            
            return articles
    
    def get_price_at_date(self, stock_id: int, target_date: date) -> Optional[StockPrice]:
        """
        Get price for a specific date (for backtesting).
        
        Args:
            stock_id: Stock ID
            target_date: Target date
            
        Returns:
            StockPrice object or None if not found
        """
        from sqlalchemy import func
        
        with self.get_session() as session:
            # Handle both date and datetime comparisons
            # SQLite stores as datetime, so we need to match on date portion only
            price = session.query(StockPrice)\
                .filter(StockPrice.stock_id == stock_id)\
                .filter(func.date(StockPrice.date) == target_date)\
                .first()
            
            if price:
                session.expunge(price)
            
            return price
    
    # ==================== RECOMMENDATION OPERATIONS ====================
    
    def add_recommendation(self, stock_id: int, overall_score: int,
                          technical_score: int, fundamental_score: int,
                          sentiment_score: int, signals: List[str],
                          rank: int = None, price: float = None) -> Recommendation:
        """
        Add a new stock recommendation.
        
        Args:
            stock_id: Stock ID
            overall_score: Overall recommendation score (0-100)
            technical_score: Technical analysis score
            fundamental_score: Fundamental analysis score
            sentiment_score: Sentiment analysis score
            signals: List of key signals
            rank: Ranking (1-10 for top picks)
            price: Current stock price
            
        Returns:
            Recommendation object
        """
        with self.get_session() as session:
            recommendation = Recommendation(
                stock_id=stock_id,
                overall_score=overall_score,
                technical_score=technical_score,
                fundamental_score=fundamental_score,
                sentiment_score=sentiment_score,
                signals=signals,
                rank=rank,
                price_at_recommendation=price or 0.0
            )
            session.add(recommendation)
            session.flush()
            session.expunge(recommendation)
            logger.info(f"Added recommendation for stock_id={stock_id}, score={overall_score}")
            return recommendation
    
    def get_recommendations_by_date(self, target_date: date = None, 
                                   min_score: int = 0) -> List[Tuple[Recommendation, Stock]]:
        """
        Get recommendations for a specific date.
        
        Args:
            target_date: Date to query (defaults to today)
            min_score: Minimum overall score filter
            
        Returns:
            List of (Recommendation, Stock) tuples
        """
        if target_date is None:
            target_date = date.today()
        
        with self.get_session() as session:
            results = session.query(Recommendation, Stock)\
                .join(Stock)\
                .filter(func.date(Recommendation.created_at) == target_date)\
                .filter(Recommendation.overall_score >= min_score)\
                .order_by(desc(Recommendation.overall_score))\
                .all()
            
            # Detach from session
            output = []
            for rec, stock in results:
                session.expunge(rec)
                session.expunge(stock)
                output.append((rec, stock))
            
            return output
    
    def get_top_recommendations(self, limit: int = 10) -> List[Tuple[Recommendation, Stock]]:
        """
        Get top N recommendations by rank and score.
        
        Args:
            limit: Number of recommendations to return
            
        Returns:
            List of (Recommendation, Stock) tuples
        """
        with self.get_session() as session:
            results = session.query(Recommendation, Stock)\
                .join(Stock)\
                .filter(Recommendation.rank.isnot(None))\
                .order_by(Recommendation.rank, desc(Recommendation.overall_score))\
                .limit(limit)\
                .all()
            
            output = []
            for rec, stock in results:
                session.expunge(rec)
                session.expunge(stock)
                output.append((rec, stock))
            
            return output
    
    def get_historical_performance(self) -> Dict[str, float]:
        """
        Calculate historical performance metrics for recommendations.
        
        Returns:
            Dictionary with performance metrics
        """
        with self.get_session() as session:
            # Get recommendations with tracked returns
            recs_5d = session.query(Recommendation)\
                .filter(Recommendation.return_5days.isnot(None))\
                .all()
            
            recs_30d = session.query(Recommendation)\
                .filter(Recommendation.return_30days.isnot(None))\
                .all()
            
            # Calculate metrics
            metrics = {
                'total_recommendations': session.query(Recommendation).count(),
                'avg_score': session.query(func.avg(Recommendation.overall_score)).scalar() or 0,
                'win_rate_5d': 0.0,
                'avg_return_5d': 0.0,
                'win_rate_30d': 0.0,
                'avg_return_30d': 0.0
            }
            
            if recs_5d:
                wins_5d = sum(1 for r in recs_5d if r.return_5days > 0)
                metrics['win_rate_5d'] = (wins_5d / len(recs_5d)) * 100
                metrics['avg_return_5d'] = sum(r.return_5days for r in recs_5d) / len(recs_5d)
            
            if recs_30d:
                wins_30d = sum(1 for r in recs_30d if r.return_30days > 0)
                metrics['win_rate_30d'] = (wins_30d / len(recs_30d)) * 100
                metrics['avg_return_30d'] = sum(r.return_30days for r in recs_30d) / len(recs_30d)
            
            return metrics
    
    # ==================== WATCHLIST OPERATIONS ====================
    
    def add_to_watchlist(self, discord_user_id: str, ticker: str) -> UserWatchlist:
        """
        Add a stock to user's watchlist.
        
        Args:
            discord_user_id: Discord user ID
            ticker: Stock ticker symbol
            
        Returns:
            UserWatchlist object
        """
        with self.get_session() as session:
            # Get stock
            stock = session.query(Stock).filter_by(ticker=ticker).first()
            if not stock:
                raise ValueError(f"Stock {ticker} not found in database")
            
            # Check if already in watchlist
            existing = session.query(UserWatchlist)\
                .filter_by(discord_user_id=discord_user_id, stock_id=stock.id)\
                .first()
            
            if existing:
                session.expunge(existing)
                logger.info(f"Stock {ticker} already in watchlist for user {discord_user_id}")
                return existing
            
            # Add to watchlist
            watchlist = UserWatchlist(
                discord_user_id=discord_user_id,
                stock_id=stock.id
            )
            session.add(watchlist)
            session.flush()
            session.expunge(watchlist)
            logger.info(f"Added {ticker} to watchlist for user {discord_user_id}")
            return watchlist
    
    def remove_from_watchlist(self, discord_user_id: str, ticker: str) -> bool:
        """
        Remove a stock from user's watchlist.
        
        Args:
            discord_user_id: Discord user ID
            ticker: Stock ticker symbol
            
        Returns:
            True if removed, False if not found
        """
        with self.get_session() as session:
            stock = session.query(Stock).filter_by(ticker=ticker).first()
            if not stock:
                return False
            
            deleted = session.query(UserWatchlist)\
                .filter_by(discord_user_id=discord_user_id, stock_id=stock.id)\
                .delete()
            
            if deleted:
                logger.info(f"Removed {ticker} from watchlist for user {discord_user_id}")
            
            return deleted > 0
    
    def get_user_watchlist(self, discord_user_id: str) -> List[Tuple[UserWatchlist, Stock]]:
        """
        Get user's watchlist.
        
        Args:
            discord_user_id: Discord user ID
            
        Returns:
            List of (UserWatchlist, Stock) tuples
        """
        with self.get_session() as session:
            results = session.query(UserWatchlist, Stock)\
                .join(Stock)\
                .filter(UserWatchlist.discord_user_id == discord_user_id)\
                .order_by(UserWatchlist.added_at.desc())\
                .all()
            
            output = []
            for watchlist, stock in results:
                session.expunge(watchlist)
                session.expunge(stock)
                output.append((watchlist, stock))
            
            return output
    
    # ==================== ALERT OPERATIONS ====================
    
    def create_alert(self, discord_user_id: str, ticker: str, 
                    threshold_score: int) -> UserAlert:
        """
        Create an alert for a stock.
        
        Args:
            discord_user_id: Discord user ID
            ticker: Stock ticker symbol
            threshold_score: Minimum score to trigger alert
            
        Returns:
            UserAlert object
        """
        with self.get_session() as session:
            stock = session.query(Stock).filter_by(ticker=ticker).first()
            if not stock:
                raise ValueError(f"Stock {ticker} not found in database")
            
            alert = UserAlert(
                discord_user_id=discord_user_id,
                stock_id=stock.id,
                threshold_score=threshold_score,
                is_active=True
            )
            session.add(alert)
            session.flush()
            session.expunge(alert)
            logger.info(f"Created alert for {ticker} (threshold={threshold_score}) for user {discord_user_id}")
            return alert
    
    def get_active_alerts(self, discord_user_id: str = None) -> List[Tuple[UserAlert, Stock]]:
        """
        Get active alerts, optionally filtered by user.
        
        Args:
            discord_user_id: Optional user ID to filter by
            
        Returns:
            List of (UserAlert, Stock) tuples
        """
        with self.get_session() as session:
            query = session.query(UserAlert, Stock)\
                .join(Stock)\
                .filter(UserAlert.is_active == True)
            
            if discord_user_id:
                query = query.filter(UserAlert.discord_user_id == discord_user_id)
            
            results = query.all()
            
            output = []
            for alert, stock in results:
                session.expunge(alert)
                session.expunge(stock)
                output.append((alert, stock))
            
            return output
    
    def deactivate_alert(self, alert_id: int):
        """
        Deactivate an alert.
        
        Args:
            alert_id: Alert ID
        """
        with self.get_session() as session:
            alert = session.query(UserAlert).filter_by(id=alert_id).first()
            if alert:
                alert.is_active = False
                logger.info(f"Deactivated alert {alert_id}")
    
    def trigger_alert(self, alert_id: int):
        """
        Mark an alert as triggered.
        
        Args:
            alert_id: Alert ID
        """
        with self.get_session() as session:
            alert = session.query(UserAlert).filter_by(id=alert_id).first()
            if alert:
                alert.triggered_at = datetime.utcnow()
                logger.info(f"Triggered alert {alert_id}")
    
    # ==================== PERFORMANCE TRACKING ====================
    
    def create_performance_tracker(self, recommendation_id: int, entry_date: datetime,
                                   entry_price: float) -> RecommendationPerformance:
        """
        Create a performance tracker for a recommendation.
        
        Args:
            recommendation_id: Recommendation ID to track
            entry_date: Date of recommendation
            entry_price: Price at recommendation
            
        Returns:
            RecommendationPerformance object
        """
        with self.get_session() as session:
            performance = RecommendationPerformance(
                recommendation_id=recommendation_id,
                entry_date=entry_date,
                entry_price=entry_price,
                peak_price=entry_price,
                peak_return=0.0,
                trough_price=entry_price,
                trough_return=0.0,
                status='tracking'
            )
            session.add(performance)
            session.flush()
            session.expunge(performance)
            logger.info(f"Created performance tracker for recommendation {recommendation_id}")
            return performance
    
    def update_performance_tracker(self, recommendation_id: int, current_date: datetime,
                                   current_price: float) -> Optional[RecommendationPerformance]:
        """
        Update performance metrics for a recommendation.
        
        Args:
            recommendation_id: Recommendation ID
            current_date: Current date for update
            current_price: Current stock price
            
        Returns:
            Updated RecommendationPerformance object or None
        """
        with self.get_session() as session:
            performance = session.query(RecommendationPerformance)\
                .filter_by(recommendation_id=recommendation_id)\
                .first()
            
            if not performance:
                return None
            
            # Calculate days since entry
            days_since_entry = (current_date - performance.entry_date).days
            return_pct = ((current_price - performance.entry_price) / performance.entry_price) * 100
            
            # Update based on days tracked
            if days_since_entry >= 1 and not performance.price_1d:
                performance.price_1d = current_price
                performance.return_1d = return_pct
                performance.is_winner_1d = return_pct > 0
            
            if days_since_entry >= 5 and not performance.price_5d:
                performance.price_5d = current_price
                performance.return_5d = return_pct
                performance.is_winner_5d = return_pct > 0
            
            if days_since_entry >= 10 and not performance.price_10d:
                performance.price_10d = current_price
                performance.return_10d = return_pct
                performance.is_winner_10d = return_pct > 0
            
            if days_since_entry >= 30:
                performance.price_30d = current_price
                performance.return_30d = return_pct
                performance.is_winner_30d = return_pct > 0
                performance.status = 'completed'
            
            # Update peak/trough
            if current_price > (performance.peak_price or 0):
                performance.peak_price = current_price
                performance.peak_return = return_pct
                performance.peak_date = current_date
            
            if current_price < (performance.trough_price or float('inf')):
                performance.trough_price = current_price
                performance.trough_return = return_pct
                performance.trough_date = current_date
            
            performance.days_tracked = days_since_entry
            performance.last_checked = current_date
            
            session.flush()
            session.expunge(performance)
            return performance
    
    def get_active_performance_trackers(self) -> List[RecommendationPerformance]:
        """
        Get all active (tracking) performance records.
        
        Returns:
            List of RecommendationPerformance objects
        """
        with self.get_session() as session:
            trackers = session.query(RecommendationPerformance)\
                .filter_by(status='tracking')\
                .all()
            
            for tracker in trackers:
                session.expunge(tracker)
            
            return trackers
    
    def get_performance_stats(self, days: int = 90, strategy_type: str = None) -> Dict:
        """
        Get aggregate performance statistics.
        
        Args:
            days: Number of days to look back
            strategy_type: Filter by strategy type (momentum, dip, etc.)
            
        Returns:
            Dictionary with performance stats
        """
        with self.get_session() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            query = session.query(RecommendationPerformance)\
                .join(Recommendation)\
                .filter(RecommendationPerformance.entry_date >= cutoff_date)
            
            if strategy_type:
                query = query.filter(Recommendation.strategy_type == strategy_type)
            
            all_trackers = query.all()
            
            if not all_trackers:
                return {
                    'total_recommendations': 0,
                    'error': 'No data available for this period'
                }
            
            # Calculate stats for different timeframes
            stats = {
                'total_recommendations': len(all_trackers),
                'days_analyzed': days,
                'strategy_type': strategy_type or 'all'
            }
            
            # 5-day stats
            trackers_5d = [t for t in all_trackers if t.return_5d is not None]
            if trackers_5d:
                winners_5d = [t for t in trackers_5d if t.is_winner_5d]
                stats['5day'] = {
                    'total': len(trackers_5d),
                    'winners': len(winners_5d),
                    'win_rate': (len(winners_5d) / len(trackers_5d)) * 100,
                    'avg_return': sum(t.return_5d for t in trackers_5d) / len(trackers_5d),
                    'avg_win': sum(t.return_5d for t in winners_5d) / len(winners_5d) if winners_5d else 0,
                    'avg_loss': sum(t.return_5d for t in trackers_5d if not t.is_winner_5d) / (len(trackers_5d) - len(winners_5d)) if len(trackers_5d) > len(winners_5d) else 0,
                    'best_return': max(t.return_5d for t in trackers_5d),
                    'worst_return': min(t.return_5d for t in trackers_5d)
                }
            
            # 30-day stats
            trackers_30d = [t for t in all_trackers if t.return_30d is not None]
            if trackers_30d:
                winners_30d = [t for t in trackers_30d if t.is_winner_30d]
                stats['30day'] = {
                    'total': len(trackers_30d),
                    'winners': len(winners_30d),
                    'win_rate': (len(winners_30d) / len(trackers_30d)) * 100,
                    'avg_return': sum(t.return_30d for t in trackers_30d) / len(trackers_30d),
                    'avg_win': sum(t.return_30d for t in winners_30d) / len(winners_30d) if winners_30d else 0,
                    'avg_loss': sum(t.return_30d for t in trackers_30d if not t.is_winner_30d) / (len(trackers_30d) - len(winners_30d)) if len(trackers_30d) > len(winners_30d) else 0,
                    'best_return': max(t.return_30d for t in trackers_30d),
                    'worst_return': min(t.return_30d for t in trackers_30d)
                }
            
            return stats
    
    def get_top_performers(self, limit: int = 10, timeframe: str = '30day') -> List[Tuple[RecommendationPerformance, Recommendation, Stock]]:
        """
        Get top performing recommendations.
        
        Args:
            limit: Number of results to return
            timeframe: '5day' or '30day'
            
        Returns:
            List of (Performance, Recommendation, Stock) tuples
        """
        with self.get_session() as session:
            # Choose return column based on timeframe
            return_col = RecommendationPerformance.return_30d if timeframe == '30day' else RecommendationPerformance.return_5d
            
            results = session.query(RecommendationPerformance, Recommendation, Stock)\
                .join(Recommendation, RecommendationPerformance.recommendation_id == Recommendation.id)\
                .join(Stock, Recommendation.stock_id == Stock.id)\
                .filter(return_col.isnot(None))\
                .order_by(desc(return_col))\
                .limit(limit)\
                .all()
            
            # Detach from session
            output = []
            for perf, rec, stock in results:
                session.expunge(perf)
                session.expunge(rec)
                session.expunge(stock)
                output.append((perf, rec, stock))
            
            return output
    
    def get_worst_performers(self, limit: int = 10, timeframe: str = '30day') -> List[Tuple[RecommendationPerformance, Recommendation, Stock]]:
        """
        Get worst performing recommendations.
        
        Args:
            limit: Number of results to return
            timeframe: '5day' or '30day'
            
        Returns:
            List of (Performance, Recommendation, Stock) tuples
        """
        with self.get_session() as session:
            # Choose return column based on timeframe
            return_col = RecommendationPerformance.return_30d if timeframe == '30day' else RecommendationPerformance.return_5d
            
            results = session.query(RecommendationPerformance, Recommendation, Stock)\
                .join(Recommendation, RecommendationPerformance.recommendation_id == Recommendation.id)\
                .join(Stock, Recommendation.stock_id == Stock.id)\
                .filter(return_col.isnot(None))\
                .order_by(return_col)\
                .limit(limit)\
                .all()
            
            # Detach from session
            output = []
            for perf, rec, stock in results:
                session.expunge(perf)
                session.expunge(rec)
                session.expunge(stock)
                output.append((perf, rec, stock))
            
            return output
    
    def get_stock_recommendation_history(self, ticker: str) -> List[Tuple[Recommendation, RecommendationPerformance]]:
        """
        Get recommendation history for a specific stock.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            List of (Recommendation, Performance) tuples
        """
        with self.get_session() as session:
            results = session.query(Recommendation, RecommendationPerformance)\
                .join(Stock)\
                .outerjoin(RecommendationPerformance)\
                .filter(Stock.ticker == ticker)\
                .order_by(desc(Recommendation.created_at))\
                .all()
            
            output = []
            for rec, perf in results:
                session.expunge(rec)
                if perf:
                    session.expunge(perf)
                output.append((rec, perf))
            
            return output
    
    # ==================== POSITION MANAGEMENT ====================
    
    def add_position(self, discord_user_id: str, ticker: str, shares: float, 
                    entry_price: float, entry_date: datetime = None,
                    profit_target_pct: float = 15.0, stop_loss_pct: float = -7.0,
                    recommendation_id: int = None) -> UserPosition:
        """
        Add a new user position.
        
        Args:
            discord_user_id: Discord user ID
            ticker: Stock ticker
            shares: Number of shares
            entry_price: Entry price per share
            entry_date: Entry date (default: now)
            profit_target_pct: Profit target percentage
            stop_loss_pct: Stop loss percentage (negative)
            recommendation_id: Optional recommendation ID
            
        Returns:
            UserPosition object
        """
        with self.get_session() as session:
            # Get stock
            stock = session.query(Stock).filter_by(ticker=ticker.upper()).first()
            if not stock:
                raise ValueError(f"Stock {ticker} not found in database")
            
            entry_date = entry_date or datetime.utcnow()
            entry_value = shares * entry_price
            
            # Calculate target prices
            profit_target_price = entry_price * (1 + profit_target_pct / 100)
            stop_loss_price = entry_price * (1 + stop_loss_pct / 100)
            
            position = UserPosition(
                discord_user_id=discord_user_id,
                stock_id=stock.id,
                recommendation_id=recommendation_id,
                entry_date=entry_date,
                entry_price=entry_price,
                shares=shares,
                entry_value=entry_value,
                profit_target_price=profit_target_price,
                profit_target_pct=profit_target_pct,
                stop_loss_price=stop_loss_price,
                stop_loss_pct=stop_loss_pct,
                status='open',
                alerts_enabled=True
            )
            
            session.add(position)
            session.flush()
            session.expunge(position)
            
            logger.info(f"Added position for {discord_user_id}: {ticker} {shares} shares @ ${entry_price}")
            return position
    
    def close_position(self, position_id: int, exit_price: float, 
                      exit_date: datetime = None, exit_reason: str = 'manual') -> UserPosition:
        """
        Close a position.
        
        Args:
            position_id: Position ID
            exit_price: Exit price
            exit_date: Exit date (default: now)
            exit_reason: Reason for exit
            
        Returns:
            Updated UserPosition object
        """
        with self.get_session() as session:
            position = session.query(UserPosition).filter_by(id=position_id).first()
            if not position:
                raise ValueError(f"Position {position_id} not found")
            
            if position.status == 'closed':
                raise ValueError(f"Position {position_id} is already closed")
            
            exit_date = exit_date or datetime.utcnow()
            exit_value = position.shares * exit_price
            profit_loss = exit_value - position.entry_value
            return_pct = ((exit_price - position.entry_price) / position.entry_price) * 100
            
            position.status = 'closed'
            position.exit_date = exit_date
            position.exit_price = exit_price
            position.exit_value = exit_value
            position.exit_reason = exit_reason
            position.profit_loss = profit_loss
            position.return_pct = return_pct
            
            session.flush()
            session.expunge(position)
            
            logger.info(f"Closed position {position_id}: {return_pct:+.2f}% return")
            return position
    
    def get_user_positions(self, discord_user_id: str, status: str = 'open') -> List[UserPosition]:
        """
        Get user's positions.
        
        Args:
            discord_user_id: Discord user ID
            status: Position status ('open', 'closed', or 'all')
            
        Returns:
            List of UserPosition objects
        """
        with self.get_session() as session:
            query = session.query(UserPosition)\
                .filter_by(discord_user_id=discord_user_id)
            
            if status != 'all':
                query = query.filter_by(status=status)
            
            positions = query.order_by(desc(UserPosition.entry_date)).all()
            
            for pos in positions:
                session.expunge(pos)
            
            return positions
    
    def get_position_by_id(self, position_id: int) -> Optional[UserPosition]:
        """Get position by ID."""
        with self.get_session() as session:
            position = session.query(UserPosition).filter_by(id=position_id).first()
            if position:
                session.expunge(position)
            return position
    
    def get_all_open_positions(self) -> List[UserPosition]:
        """Get all open positions across all users."""
        with self.get_session() as session:
            positions = session.query(UserPosition)\
                .filter_by(status='open')\
                .order_by(UserPosition.entry_date)\
                .all()
            
            for pos in positions:
                session.expunge(pos)
            
            return positions
    
    def toggle_position_alerts(self, position_id: int, enabled: bool) -> UserPosition:
        """Toggle alerts for a position."""
        with self.get_session() as session:
            position = session.query(UserPosition).filter_by(id=position_id).first()
            if position:
                position.alerts_enabled = enabled
                session.flush()
                session.expunge(position)
            return position
    
    # ==================== EXIT SIGNALS ====================
    
    def create_exit_signal(self, position_id: int, signal_type: str, current_price: float,
                          reason: str, urgency: str = 'medium', target_price: float = None,
                          technical_signals: dict = None, sentiment_data: dict = None) -> ExitSignal:
        """
        Create an exit signal for a position.
        
        Args:
            position_id: Position ID
            signal_type: Type of signal (profit_target, stop_loss, reversal, sentiment, time, score_drop)
            current_price: Current stock price
            reason: Human-readable explanation
            urgency: Signal urgency (high, medium, low)
            target_price: Price threshold that triggered signal
            technical_signals: Technical indicator data
            sentiment_data: Sentiment information
            
        Returns:
            ExitSignal object
        """
        with self.get_session() as session:
            # Get position to calculate price change
            position = session.query(UserPosition).filter_by(id=position_id).first()
            if not position:
                raise ValueError(f"Position {position_id} not found")
            
            price_change_pct = ((current_price - position.entry_price) / position.entry_price) * 100
            
            signal = ExitSignal(
                position_id=position_id,
                signal_type=signal_type,
                current_price=current_price,
                target_price=target_price,
                price_change_pct=price_change_pct,
                reason=reason,
                technical_signals=technical_signals or {},
                sentiment_data=sentiment_data or {},
                urgency=urgency,
                status='pending'
            )
            
            session.add(signal)
            session.flush()
            session.expunge(signal)
            
            # Update position status to alerted
            position.status = 'alerted'
            
            logger.info(f"Created {urgency} urgency {signal_type} signal for position {position_id}")
            return signal
    
    def get_active_exit_signals(self, discord_user_id: str = None) -> List[Tuple[ExitSignal, UserPosition, Stock]]:
        """
        Get active (pending) exit signals.
        
        Args:
            discord_user_id: Optional user ID to filter by
            
        Returns:
            List of (ExitSignal, UserPosition, Stock) tuples
        """
        with self.get_session() as session:
            query = session.query(ExitSignal, UserPosition, Stock)\
                .join(UserPosition, ExitSignal.position_id == UserPosition.id)\
                .join(Stock, UserPosition.stock_id == Stock.id)\
                .filter(ExitSignal.status == 'pending')\
                .filter(UserPosition.status.in_(['open', 'alerted']))
            
            if discord_user_id:
                query = query.filter(UserPosition.discord_user_id == discord_user_id)
            
            results = query.order_by(
                # High urgency first
                case(
                    (ExitSignal.urgency == 'high', 1),
                    (ExitSignal.urgency == 'medium', 2),
                    else_=3
                ),
                desc(ExitSignal.signal_date)
            ).all()
            
            output = []
            for signal, position, stock in results:
                session.expunge(signal)
                session.expunge(position)
                session.expunge(stock)
                output.append((signal, position, stock))
            
            return output
    
    def mark_signal_acted(self, signal_id: int) -> ExitSignal:
        """Mark an exit signal as acted upon."""
        with self.get_session() as session:
            signal = session.query(ExitSignal).filter_by(id=signal_id).first()
            if signal:
                signal.status = 'acted'
                signal.acted_at = datetime.utcnow()
                session.flush()
                session.expunge(signal)
            return signal
    
    def mark_signal_ignored(self, signal_id: int) -> ExitSignal:
        """Mark an exit signal as ignored."""
        with self.get_session() as session:
            signal = session.query(ExitSignal).filter_by(id=signal_id).first()
            if signal:
                signal.status = 'ignored'
                session.flush()
                session.expunge(signal)
            return signal
    
    def get_user_trading_stats(self, discord_user_id: str, days: int = 365) -> Dict:
        """
        Get user's trading performance statistics.
        
        Args:
            discord_user_id: Discord user ID
            days: Number of days to look back
            
        Returns:
            Dictionary with trading stats
        """
        with self.get_session() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get all closed positions
            closed_positions = session.query(UserPosition)\
                .filter_by(discord_user_id=discord_user_id, status='closed')\
                .filter(UserPosition.entry_date >= cutoff_date)\
                .all()
            
            if not closed_positions:
                return {
                    'total_trades': 0,
                    'error': 'No closed positions found'
                }
            
            # Calculate statistics
            winners = [p for p in closed_positions if p.return_pct > 0]
            losers = [p for p in closed_positions if p.return_pct <= 0]
            
            total_pl = sum(p.profit_loss for p in closed_positions)
            total_return_pct = sum(p.return_pct for p in closed_positions) / len(closed_positions)
            
            stats = {
                'total_trades': len(closed_positions),
                'winners': len(winners),
                'losers': len(losers),
                'win_rate': (len(winners) / len(closed_positions)) * 100,
                'total_profit_loss': total_pl,
                'avg_return': total_return_pct,
                'avg_win': sum(p.return_pct for p in winners) / len(winners) if winners else 0,
                'avg_loss': sum(p.return_pct for p in losers) / len(losers) if losers else 0,
                'best_trade': max(closed_positions, key=lambda p: p.return_pct),
                'worst_trade': min(closed_positions, key=lambda p: p.return_pct),
                'avg_hold_days': sum((p.exit_date - p.entry_date).days for p in closed_positions) / len(closed_positions)
            }
            
            # Detach objects
            if stats['best_trade']:
                session.expunge(stats['best_trade'])
            if stats['worst_trade']:
                session.expunge(stats['worst_trade'])
            
            return stats
    
    # ==================== CLEANUP ====================
    
    def close(self):
        """Close all database connections."""
        self.Session.remove()
        self.engine.dispose()
        logger.info("DatabaseManager connections closed")

