"""
Exit Signal Detection for SmartInvest Bot

Analyzes open positions and generates exit signals based on:
- Profit targets
- Stop losses
- Technical reversals
- Sentiment shifts
- Time-based exits
- Score degradation
"""

import logging
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class ExitSignalDetector:
    """
    Detects exit signals for open positions.
    """
    
    def __init__(self, db_manager):
        """
        Initialize ExitSignalDetector.
        
        Args:
            db_manager: DatabaseManager instance
        """
        self.db = db_manager
        
        # Default thresholds (can be customized per position)
        self.default_profit_target = 15.0  # %
        self.default_stop_loss = -7.0  # %
        self.max_hold_days_momentum = 45
        self.max_hold_days_dip = 90
        
        logger.info("ExitSignalDetector initialized")
    
    def check_position_for_exits(self, position, current_price: float,
                                 price_data: pd.DataFrame = None,
                                 news_sentiment: float = None) -> List[Dict]:
        """
        Check a single position for all exit signals.
        
        Args:
            position: UserPosition object
            current_price: Current stock price
            price_data: Optional price DataFrame for technical analysis
            news_sentiment: Optional current news sentiment
            
        Returns:
            List of exit signal dictionaries
        """
        signals = []
        
        # Calculate current return
        return_pct = ((current_price - position.entry_price) / position.entry_price) * 100
        days_held = (datetime.utcnow() - position.entry_date).days
        
        # 1. Profit Target
        if position.profit_target_pct and return_pct >= position.profit_target_pct:
            signals.append(self._profit_target_signal(position, current_price, return_pct))
        
        # 2. Stop Loss
        if position.stop_loss_pct and return_pct <= position.stop_loss_pct:
            signals.append(self._stop_loss_signal(position, current_price, return_pct))
        
        # 3. Approaching Stop Loss (warning)
        if position.stop_loss_pct:
            stop_distance = return_pct - position.stop_loss_pct
            if 0 < stop_distance < 1.0:  # Within 1% of stop
                signals.append(self._approaching_stop_signal(position, current_price, return_pct, stop_distance))
        
        # 4. Technical Reversal (if price data available)
        if price_data is not None and len(price_data) >= 20:
            reversal_signal = self._check_technical_reversal(position, current_price, price_data, return_pct)
            if reversal_signal:
                signals.append(reversal_signal)
        
        # 5. Sentiment Shift (if sentiment available)
        if news_sentiment is not None:
            sentiment_signal = self._check_sentiment_shift(position, current_price, news_sentiment, return_pct)
            if sentiment_signal:
                signals.append(sentiment_signal)
        
        # 6. Time Exit
        time_signal = self._check_time_exit(position, current_price, days_held, return_pct)
        if time_signal:
            signals.append(time_signal)
        
        return signals
    
    def _profit_target_signal(self, position, current_price: float, return_pct: float) -> Dict:
        """Generate profit target exit signal."""
        return {
            'type': 'profit_target',
            'urgency': 'medium',
            'current_price': current_price,
            'target_price': position.profit_target_price,
            'return_pct': return_pct,
            'reason': f"Profit target reached (+{return_pct:.1f}%). Consider taking profits.",
            'technical_signals': {},
            'sentiment_data': {}
        }
    
    def _stop_loss_signal(self, position, current_price: float, return_pct: float) -> Dict:
        """Generate stop loss exit signal."""
        return {
            'type': 'stop_loss',
            'urgency': 'high',
            'current_price': current_price,
            'target_price': position.stop_loss_price,
            'return_pct': return_pct,
            'reason': f"Stop loss triggered ({return_pct:.1f}%). Exit to preserve capital.",
            'technical_signals': {},
            'sentiment_data': {}
        }
    
    def _approaching_stop_signal(self, position, current_price: float, 
                                 return_pct: float, distance: float) -> Dict:
        """Generate approaching stop loss warning."""
        return {
            'type': 'stop_loss_near',
            'urgency': 'high',
            'current_price': current_price,
            'target_price': position.stop_loss_price,
            'return_pct': return_pct,
            'reason': f"Approaching stop loss ({return_pct:.1f}%). Only {distance:.1f}% away. Prepare to exit.",
            'technical_signals': {},
            'sentiment_data': {}
        }
    
    def _check_technical_reversal(self, position, current_price: float,
                                  price_data: pd.DataFrame, return_pct: float) -> Optional[Dict]:
        """
        Check for technical reversal signals.
        
        Looks for:
        - RSI overbought (>70) when in profit
        - Price below key moving averages
        - Bearish MACD crossover
        - Volume spike on down days
        """
        try:
            closes = price_data['close'].values
            volumes = price_data['volume'].values
            
            # Calculate RSI
            rsi = self._calculate_rsi(closes)
            
            # Calculate moving averages
            ema_20 = pd.Series(closes).ewm(span=20).mean().iloc[-1]
            
            # Count reversal signals
            reversal_count = 0
            signals_detected = []
            
            # 1. RSI overbought (if in profit)
            if return_pct > 5 and rsi > 70:
                reversal_count += 1
                signals_detected.append(f"RSI overbought ({rsi:.1f})")
            
            # 2. Price below 20 EMA
            if current_price < ema_20:
                reversal_count += 1
                signals_detected.append(f"Below 20-EMA (${ema_20:.2f})")
            
            # 3. Volume spike on recent down day
            if len(closes) >= 2 and closes[-1] < closes[-2]:
                avg_volume = np.mean(volumes[:-1])
                if volumes[-1] > avg_volume * 1.5:
                    reversal_count += 1
                    signals_detected.append("Volume spike on down day")
            
            # 4. Lower highs pattern
            if len(closes) >= 5:
                recent_highs = [max(closes[i-2:i+1]) for i in range(2, len(closes))]
                if len(recent_highs) >= 3 and recent_highs[-1] < recent_highs[-2] < recent_highs[-3]:
                    reversal_count += 1
                    signals_detected.append("Lower highs pattern")
            
            # Generate signal if 2+ reversal indicators
            if reversal_count >= 2:
                return {
                    'type': 'reversal',
                    'urgency': 'medium' if return_pct > 0 else 'high',
                    'current_price': current_price,
                    'target_price': None,
                    'return_pct': return_pct,
                    'reason': f"Trend reversal detected ({reversal_count} signals). Momentum weakening.",
                    'technical_signals': {
                        'rsi': rsi,
                        'ema_20': ema_20,
                        'signals': signals_detected,
                        'reversal_count': reversal_count
                    },
                    'sentiment_data': {}
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking technical reversal: {e}")
            return None
    
    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """Calculate RSI indicator."""
        if len(prices) < period + 1:
            return 50.0  # Neutral if not enough data
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _check_sentiment_shift(self, position, current_price: float,
                               current_sentiment: float, return_pct: float) -> Optional[Dict]:
        """
        Check for significant sentiment shift.
        
        Args:
            position: UserPosition
            current_price: Current price
            current_sentiment: Current sentiment score (-1 to 1)
            return_pct: Current return %
        """
        # Get entry date sentiment from news articles
        try:
            session = self.db.Session()
            stock = session.query(self.db.Stock).filter_by(id=position.stock_id).first()
            
            if not stock:
                return None
            
            # Get sentiment at entry
            entry_date = position.entry_date
            entry_window_start = entry_date - timedelta(days=7)
            entry_window_end = entry_date + timedelta(days=1)
            
            entry_articles = session.query(self.db.NewsArticle)\
                .filter_by(stock_id=stock.id)\
                .filter(self.db.NewsArticle.published_at >= entry_window_start)\
                .filter(self.db.NewsArticle.published_at <= entry_window_end)\
                .all()
            
            session.close()
            
            if not entry_articles:
                return None
            
            entry_sentiment = np.mean([a.sentiment_score for a in entry_articles if a.sentiment_score])
            
            # Calculate sentiment change
            sentiment_change = current_sentiment - entry_sentiment
            
            # Signal if sentiment significantly worsened
            if sentiment_change < -0.4:  # Dropped by 0.4+ (significant)
                return {
                    'type': 'sentiment_shift',
                    'urgency': 'high' if current_sentiment < -0.3 else 'medium',
                    'current_price': current_price,
                    'target_price': None,
                    'return_pct': return_pct,
                    'reason': f"News sentiment turned negative. Entry: {entry_sentiment:+.2f}, Now: {current_sentiment:+.2f}",
                    'technical_signals': {},
                    'sentiment_data': {
                        'entry_sentiment': entry_sentiment,
                        'current_sentiment': current_sentiment,
                        'change': sentiment_change
                    }
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking sentiment shift: {e}")
            return None
    
    def _check_time_exit(self, position, current_price: float,
                        days_held: int, return_pct: float) -> Optional[Dict]:
        """
        Check if position has been held too long.
        """
        # Get strategy type from recommendation if available
        max_days = self.max_hold_days_momentum  # Default
        
        if position.recommendation_id:
            try:
                session = self.db.Session()
                recommendation = session.query(self.db.Recommendation)\
                    .filter_by(id=position.recommendation_id)\
                    .first()
                session.close()
                
                if recommendation and recommendation.strategy_type == 'dip':
                    max_days = self.max_hold_days_dip
            except Exception as e:
                logger.error(f"Error getting recommendation: {e}")
        
        # Signal if held too long with minimal movement
        if days_held >= max_days:
            if -5 < return_pct < 10:  # Minimal movement (-5% to +10%)
                return {
                    'type': 'time_exit',
                    'urgency': 'low',
                    'current_price': current_price,
                    'target_price': None,
                    'return_pct': return_pct,
                    'reason': f"Held for {days_held} days with minimal movement ({return_pct:+.1f}%). Consider reallocating capital.",
                    'technical_signals': {},
                    'sentiment_data': {}
                }
        
        return None
    
    def get_current_price(self, ticker: str) -> Optional[float]:
        """Fetch current price for a stock."""
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period='1d')
            
            if data.empty:
                logger.warning(f"No price data for {ticker}")
                return None
            
            return float(data['Close'].iloc[-1])
        
        except Exception as e:
            logger.error(f"Error fetching price for {ticker}: {e}")
            return None
    
    def get_price_data(self, ticker: str, days: int = 30) -> Optional[pd.DataFrame]:
        """Fetch historical price data for technical analysis."""
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period=f"{days}d")
            
            if data.empty:
                return None
            
            # Normalize column names
            data.columns = [c.lower() for c in data.columns]
            return data
        
        except Exception as e:
            logger.error(f"Error fetching price data for {ticker}: {e}")
            return None
    
    def get_current_sentiment(self, stock_id: int, days: int = 7) -> Optional[float]:
        """Get recent news sentiment for a stock."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            session = self.db.Session()
            articles = session.query(self.db.NewsArticle)\
                .filter_by(stock_id=stock_id)\
                .filter(self.db.NewsArticle.published_at >= cutoff_date)\
                .all()
            session.close()
            
            if not articles:
                return None
            
            sentiments = [a.sentiment_score for a in articles if a.sentiment_score is not None]
            if not sentiments:
                return None
            
            return np.mean(sentiments)
        
        except Exception as e:
            logger.error(f"Error getting sentiment: {e}")
            return None

