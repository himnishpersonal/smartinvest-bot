"""
Database schema for SmartInvest stock recommendation system.
Uses SQLAlchemy ORM for PostgreSQL database.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, 
    ForeignKey, UniqueConstraint, Index, JSON, Text, BigInteger
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class Stock(Base):
    """Stock information table."""
    __tablename__ = 'stocks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10), unique=True, nullable=False, index=True)
    company_name = Column(String(255), nullable=False)
    sector = Column(String(100))
    industry = Column(String(100))
    market_cap = Column(BigInteger)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    prices = relationship('StockPrice', back_populates='stock', cascade='all, delete-orphan')
    fundamentals = relationship('Fundamental', back_populates='stock', cascade='all, delete-orphan')
    news_articles = relationship('NewsArticle', back_populates='stock', cascade='all, delete-orphan')
    recommendations = relationship('Recommendation', back_populates='stock', cascade='all, delete-orphan')
    watchlists = relationship('UserWatchlist', back_populates='stock', cascade='all, delete-orphan')
    alerts = relationship('UserAlert', back_populates='stock', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Stock(ticker='{self.ticker}', company_name='{self.company_name}')>"


class StockPrice(Base):
    """Historical stock price data."""
    __tablename__ = 'stock_prices'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_id = Column(Integer, ForeignKey('stocks.id', ondelete='CASCADE'), nullable=False)
    date = Column(DateTime, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=False)
    adjusted_close = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    stock = relationship('Stock', back_populates='prices')
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('stock_id', 'date', name='uq_stock_price_date'),
        Index('idx_stock_date', 'stock_id', 'date'),
    )
    
    def __repr__(self):
        return f"<StockPrice(stock_id={self.stock_id}, date='{self.date}', close={self.close})>"


class Fundamental(Base):
    """Fundamental analysis metrics for stocks."""
    __tablename__ = 'fundamentals'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_id = Column(Integer, ForeignKey('stocks.id', ondelete='CASCADE'), nullable=False)
    date = Column(DateTime, nullable=False, index=True)
    
    # Valuation ratios
    pe_ratio = Column(Float)
    pb_ratio = Column(Float)
    ps_ratio = Column(Float)
    
    # Financial health ratios
    debt_to_equity = Column(Float)
    current_ratio = Column(Float)
    quick_ratio = Column(Float)
    
    # Profitability metrics
    roe = Column(Float)  # Return on Equity
    roa = Column(Float)  # Return on Assets
    profit_margin = Column(Float)
    
    # Growth metrics
    revenue_growth = Column(Float)
    earnings_growth = Column(Float)
    
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    stock = relationship('Stock', back_populates='fundamentals')
    
    # Indexes
    __table_args__ = (
        Index('idx_fundamental_stock_date', 'stock_id', 'date'),
    )
    
    def __repr__(self):
        return f"<Fundamental(stock_id={self.stock_id}, date='{self.date}', pe_ratio={self.pe_ratio})>"


class NewsArticle(Base):
    """News articles related to stocks with sentiment analysis."""
    __tablename__ = 'news_articles'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_id = Column(Integer, ForeignKey('stocks.id', ondelete='CASCADE'), nullable=False)
    published_at = Column(DateTime, nullable=False, index=True)
    title = Column(Text, nullable=False)
    source = Column(String(100))
    url = Column(Text)
    
    # Sentiment analysis
    sentiment_score = Column(Float)  # Range: -1.0 to 1.0
    sentiment_label = Column(String(20))  # positive, negative, neutral
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    stock = relationship('Stock', back_populates='news_articles')
    
    # Indexes - unique constraint on (stock_id, url) to allow same article for multiple stocks
    __table_args__ = (
        Index('idx_news_stock_published', 'stock_id', 'published_at'),
        Index('idx_news_url', 'stock_id', 'url', unique=True),  # Unique per stock
    )
    
    def __repr__(self):
        return f"<NewsArticle(stock_id={self.stock_id}, title='{self.title[:50]}...', sentiment='{self.sentiment_label}')>"


class Recommendation(Base):
    """Stock recommendations with scoring and tracking."""
    __tablename__ = 'recommendations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_id = Column(Integer, ForeignKey('stocks.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Scoring components (0-100)
    overall_score = Column(Integer, nullable=False)
    technical_score = Column(Integer, nullable=False)
    fundamental_score = Column(Integer, nullable=False)
    sentiment_score = Column(Integer, nullable=False)
    
    # Key signals that led to recommendation
    signals = Column(JSON)  # Array of signal descriptions
    
    # Ranking (1-10 for top picks)
    rank = Column(Integer)
    
    # Price tracking
    price_at_recommendation = Column(Float, nullable=False)
    price_after_5days = Column(Float)
    price_after_30days = Column(Float)
    return_5days = Column(Float)  # Percentage return
    return_30days = Column(Float)  # Percentage return
    
    # Strategy type for performance tracking
    strategy_type = Column(String(50), default='momentum')  # momentum, dip, manual
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    stock = relationship('Stock', back_populates='recommendations')
    performance = relationship('RecommendationPerformance', back_populates='recommendation', uselist=False, cascade='all, delete-orphan')
    
    # Indexes
    __table_args__ = (
        Index('idx_recommendation_stock_created', 'stock_id', 'created_at'),
        Index('idx_recommendation_score', 'overall_score'),
        Index('idx_recommendation_rank', 'rank'),
        Index('idx_recommendation_strategy', 'strategy_type'),
    )
    
    def __repr__(self):
        return f"<Recommendation(stock_id={self.stock_id}, overall_score={self.overall_score}, rank={self.rank})>"


class RecommendationPerformance(Base):
    """Tracks performance of recommendations over multiple timeframes."""
    __tablename__ = 'recommendation_performance'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    recommendation_id = Column(Integer, ForeignKey('recommendations.id', ondelete='CASCADE'), nullable=False, unique=True)
    
    # Entry data
    entry_date = Column(DateTime, nullable=False, index=True)
    entry_price = Column(Float, nullable=False)
    
    # Performance at different timeframes
    price_1d = Column(Float)
    price_5d = Column(Float)
    price_10d = Column(Float)
    price_30d = Column(Float)
    
    return_1d = Column(Float)  # Percentage returns
    return_5d = Column(Float)
    return_10d = Column(Float)
    return_30d = Column(Float)
    
    # Best/worst during tracking period
    peak_price = Column(Float)
    peak_return = Column(Float)
    peak_date = Column(DateTime)
    
    trough_price = Column(Float)
    trough_return = Column(Float)
    trough_date = Column(DateTime)
    
    # Status tracking
    status = Column(String(20), default='tracking', nullable=False)  # tracking, completed, failed
    days_tracked = Column(Integer, default=0)
    last_checked = Column(DateTime, default=datetime.utcnow)
    
    # Win/loss classification
    is_winner_1d = Column(Boolean)  # True if return > 0
    is_winner_5d = Column(Boolean)
    is_winner_10d = Column(Boolean)
    is_winner_30d = Column(Boolean)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    recommendation = relationship('Recommendation', back_populates='performance')
    
    # Indexes
    __table_args__ = (
        Index('idx_performance_entry_date', 'entry_date'),
        Index('idx_performance_status', 'status'),
        Index('idx_performance_winner_5d', 'is_winner_5d'),
        Index('idx_performance_winner_30d', 'is_winner_30d'),
    )
    
    def __repr__(self):
        return f"<RecommendationPerformance(recommendation_id={self.recommendation_id}, status='{self.status}', return_5d={self.return_5d})>"


class UserWatchlist(Base):
    """User watchlists for tracking favorite stocks."""
    __tablename__ = 'user_watchlists'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    discord_user_id = Column(String(100), nullable=False, index=True)
    stock_id = Column(Integer, ForeignKey('stocks.id', ondelete='CASCADE'), nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    stock = relationship('Stock', back_populates='watchlists')
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('discord_user_id', 'stock_id', name='uq_user_stock_watchlist'),
        Index('idx_watchlist_user', 'discord_user_id'),
    )
    
    def __repr__(self):
        return f"<UserWatchlist(discord_user_id='{self.discord_user_id}', stock_id={self.stock_id})>"


class UserAlert(Base):
    """User alerts for stock recommendations."""
    __tablename__ = 'user_alerts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    discord_user_id = Column(String(100), nullable=False, index=True)
    stock_id = Column(Integer, ForeignKey('stocks.id', ondelete='CASCADE'), nullable=False)
    threshold_score = Column(Integer, nullable=False)  # Alert when score >= threshold
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    triggered_at = Column(DateTime)
    is_active = Column(Boolean, default=True, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    stock = relationship('Stock', back_populates='alerts')
    
    # Indexes
    __table_args__ = (
        Index('idx_alert_user_active', 'discord_user_id', 'is_active'),
        Index('idx_alert_stock_active', 'stock_id', 'is_active'),
    )
    
    def __repr__(self):
        return f"<UserAlert(discord_user_id='{self.discord_user_id}', stock_id={self.stock_id}, threshold={self.threshold_score}, active={self.is_active})>"


class UserPosition(Base):
    """User stock positions for exit signal tracking."""
    __tablename__ = 'user_positions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    discord_user_id = Column(String(100), nullable=False, index=True)
    stock_id = Column(Integer, ForeignKey('stocks.id', ondelete='CASCADE'), nullable=False)
    recommendation_id = Column(Integer, ForeignKey('recommendations.id', ondelete='SET NULL'))
    
    # Entry details
    entry_date = Column(DateTime, nullable=False, index=True)
    entry_price = Column(Float, nullable=False)
    shares = Column(Float, nullable=False)
    entry_value = Column(Float, nullable=False)  # shares * entry_price
    
    # Exit targets
    profit_target_price = Column(Float)  # Take profit at this price
    profit_target_pct = Column(Float)  # Target return %
    stop_loss_price = Column(Float)  # Stop loss at this price
    stop_loss_pct = Column(Float)  # Max loss %
    
    # Position status
    status = Column(String(20), default='open', nullable=False)  # open, closed, alerted
    
    # Exit details (when closed)
    exit_date = Column(DateTime)
    exit_price = Column(Float)
    exit_value = Column(Float)  # shares * exit_price
    exit_reason = Column(String(100))  # profit_target, stop_loss, manual, etc.
    profit_loss = Column(Float)  # $ P&L
    return_pct = Column(Float)  # % return
    
    # Monitoring preferences
    alerts_enabled = Column(Boolean, default=True, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    stock = relationship('Stock')
    recommendation = relationship('Recommendation')
    exit_signals = relationship('ExitSignal', back_populates='position', cascade='all, delete-orphan')
    
    # Indexes
    __table_args__ = (
        Index('idx_position_user_status', 'discord_user_id', 'status'),
        Index('idx_position_stock', 'stock_id'),
        Index('idx_position_entry_date', 'entry_date'),
    )
    
    def __repr__(self):
        return f"<UserPosition(user='{self.discord_user_id}', stock_id={self.stock_id}, status='{self.status}', entry=${self.entry_price})>"


class ExitSignal(Base):
    """Exit signals for user positions."""
    __tablename__ = 'exit_signals'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    position_id = Column(Integer, ForeignKey('user_positions.id', ondelete='CASCADE'), nullable=False)
    
    # Signal details
    signal_date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    signal_type = Column(String(50), nullable=False, index=True)  # profit_target, stop_loss, reversal, sentiment, time, score_drop
    
    # Price information
    current_price = Column(Float, nullable=False)
    target_price = Column(Float)  # The price threshold that triggered signal
    price_change_pct = Column(Float)  # % change from entry
    
    # Signal metadata
    reason = Column(Text)  # Human-readable explanation
    technical_signals = Column(JSON)  # Supporting technical data
    sentiment_data = Column(JSON)  # Sentiment information
    urgency = Column(String(20), default='medium', nullable=False)  # high, medium, low
    
    # Signal status
    status = Column(String(20), default='pending', nullable=False)  # pending, acted, ignored, expired
    notified_at = Column(DateTime)
    acted_at = Column(DateTime)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    position = relationship('UserPosition', back_populates='exit_signals')
    
    # Indexes
    __table_args__ = (
        Index('idx_exit_signal_position_status', 'position_id', 'status'),
        Index('idx_exit_signal_type_urgency', 'signal_type', 'urgency'),
        Index('idx_exit_signal_date', 'signal_date'),
    )
    
    def __repr__(self):
        return f"<ExitSignal(position_id={self.position_id}, type='{self.signal_type}', urgency='{self.urgency}', status='{self.status}')>"


# Utility function to create all tables
def create_tables(engine):
    """
    Create all tables in the database.
    
    Args:
        engine: SQLAlchemy engine instance
    """
    Base.metadata.create_all(engine)


# Utility function to drop all tables (use with caution!)
def drop_tables(engine):
    """
    Drop all tables from the database. Use with caution!
    
    Args:
        engine: SQLAlchemy engine instance
    """
    Base.metadata.drop_all(engine)

