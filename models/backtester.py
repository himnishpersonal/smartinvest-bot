"""
Portfolio Backtesting Engine for SmartInvest Bot
Simulates historical trading performance with no lookahead bias
"""

import logging
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class Backtester:
    """
    Core backtesting engine that scores stocks using only historical data.
    KEY PRINCIPLE: Never use future data when scoring past dates.
    """
    
    def __init__(self, db_manager, ml_model, feature_calculator):
        """
        Initialize backtester with database and model.
        
        Args:
            db_manager: DatabaseManager instance
            ml_model: Trained ML model (loaded from .pkl)
            feature_calculator: Feature calculation function
        """
        self.db = db_manager
        self.model = ml_model
        self.calculate_features_func = feature_calculator
    
    def score_stocks_at_date(self, target_date: date, min_data_points: int = 30) -> List[Dict]:
        """
        Score all stocks using only data available BEFORE target_date.
        This prevents lookahead bias.
        
        Args:
            target_date: Date to score stocks (as if it's "today")
            min_data_points: Minimum price history required
            
        Returns:
            List of dicts with ticker, score, price
        """
        logger.info(f"Scoring stocks for {target_date}")
        
        stocks = self.db.get_all_stocks()
        scores = []
        
        for stock in stocks:
            try:
                # Get price history BEFORE target_date (60 days lookback)
                start_date = target_date - timedelta(days=90)  # Extra buffer
                prices = self.db.get_price_history(
                    stock.id,
                    start_date=start_date,
                    end_date=target_date - timedelta(days=1)  # Exclude target date itself
                )
                
                # Convert to DataFrame
                if not prices or len(prices) < min_data_points:
                    continue
                
                price_df = pd.DataFrame([{
                    'date': p.date,
                    'open': p.open,
                    'high': p.high,
                    'low': p.low,
                    'close': p.close,
                    'volume': p.volume
                } for p in prices])
                
                # Get news articles BEFORE target_date (30 days lookback)
                news_start = target_date - timedelta(days=30)
                articles = self.db.get_news_articles_in_range(
                    stock.id,
                    start_date=news_start,
                    end_date=target_date - timedelta(days=1)
                )
                
                # Calculate features using historical data only
                features_dict = self.calculate_features_func(price_df, articles)
                
                if not features_dict:
                    continue
                
                # ML prediction - MUST MATCH score_stock_simple()
                # Create feature array in EXACT order
                feature_values = [
                    features_dict['return_5d'],
                    features_dict['return_10d'],
                    features_dict['return_20d'],
                    features_dict['momentum'],
                    features_dict['volume_trend'],
                    features_dict['avg_sentiment'],
                    features_dict['sentiment_positive'],
                    features_dict['sentiment_negative']
                ]
                
                if self.model:
                    try:
                        prediction_proba = self.model.predict_proba([feature_values])[0]
                        ml_score = int(prediction_proba[1] * 100)  # Probability of positive outcome
                        overall_score = ml_score  # DIRECT from ML model (not weighted)
                    except Exception as e:
                        logger.debug(f"ML prediction failed for {stock.ticker}: {e}")
                        # Fallback: simple scoring based on 10-day return
                        overall_score = int((features_dict['return_10d'] + 1) * 50)
                else:
                    # No ML model: use fallback scoring
                    overall_score = int((features_dict['return_10d'] + 1) * 50)
                
                # Get price at target_date for entry
                entry_price_obj = self.db.get_price_at_date(stock.id, target_date)
                if not entry_price_obj:
                    # Use last available price before target date
                    entry_price = prices[-1].close
                else:
                    entry_price = entry_price_obj.close
                
                scores.append({
                    'ticker': stock.ticker,
                    'stock_id': stock.id,
                    'score': int(overall_score),
                    'entry_price': entry_price
                })
                
            except Exception as e:
                logger.debug(f"Error scoring {stock.ticker} at {target_date}: {e}")
                continue
        
        # Sort by score and return top stocks
        scores.sort(key=lambda x: x['score'], reverse=True)
        logger.info(f"Scored {len(scores)} stocks for {target_date}")
        
        return scores


class PortfolioSimulator:
    """
    Simulates portfolio trading based on backtest signals.
    """
    
    def __init__(self, starting_capital: float = 10000, hold_days: int = 5, max_positions: int = 10):
        """
        Initialize portfolio simulator.
        
        Args:
            starting_capital: Starting cash amount
            hold_days: Days to hold each position
            max_positions: Maximum concurrent positions
        """
        self.starting_capital = starting_capital
        self.cash = starting_capital
        self.hold_days = hold_days
        self.max_positions = max_positions
        
        self.positions = []  # Active positions
        self.closed_trades = []  # Completed trades
        self.equity_curve = []  # Daily portfolio value
        
        logger.info(f"Portfolio initialized: ${starting_capital:,.0f}, hold {hold_days} days, max {max_positions} positions")
    
    def run_backtest(self, backtester: Backtester, start_date: date, end_date: date) -> Dict:
        """
        Run complete backtest simulation.
        
        Args:
            backtester: Backtester instance
            start_date: Start date of backtest
            end_date: End date of backtest
            
        Returns:
            Dictionary with backtest results
        """
        logger.info(f"Starting backtest: {start_date} to {end_date}")
        
        current_date = start_date
        trading_days = 0
        
        while current_date <= end_date:
            # Skip weekends (Saturday=5, Sunday=6)
            if current_date.weekday() >= 5:
                current_date += timedelta(days=1)
                continue
            
            trading_days += 1
            
            # Step 1: Close positions that reached hold period
            self._check_and_close_positions(backtester, current_date)
            
            # Step 2: Get recommendations for this date
            recommendations = backtester.score_stocks_at_date(current_date)
            
            # Step 3: Open new positions if we have cash and slots
            self._open_positions(recommendations, current_date)
            
            # Step 4: Track portfolio value
            portfolio_value = self._calculate_portfolio_value(backtester, current_date)
            self.equity_curve.append({
                'date': current_date,
                'value': portfolio_value,
                'cash': self.cash,
                'positions': len(self.positions)
            })
            
            # Progress logging
            if trading_days % 10 == 0:
                logger.info(f"Progress: {current_date} | Portfolio: ${portfolio_value:,.0f} | Positions: {len(self.positions)}")
            
            # Next day
            current_date += timedelta(days=1)
        
        # Close all remaining positions at end date
        self._close_all_positions(backtester, end_date)
        
        logger.info(f"Backtest complete: {len(self.closed_trades)} trades executed")
        
        return {
            'closed_trades': self.closed_trades,
            'equity_curve': self.equity_curve,
            'starting_capital': self.starting_capital,
            'final_value': self.equity_curve[-1]['value'] if self.equity_curve else self.starting_capital
        }
    
    def _open_positions(self, recommendations: List[Dict], current_date: date):
        """Open new positions based on recommendations."""
        available_slots = self.max_positions - len(self.positions)
        
        if available_slots <= 0 or self.cash < 100:
            return
        
        # Calculate position size (equal weight)
        cash_per_position = self.cash / available_slots
        
        # Only buy top-scoring stocks (score >= 70)
        # This matches the confidence threshold used in production
        top_picks = [r for r in recommendations if r['score'] >= 70][:available_slots]
        
        logger.info(f"{current_date}: Found {len(recommendations)} recommendations, {len(top_picks)} with score >= 70")
        
        for rec in top_picks:
            if self.cash < 100:
                break
            
            entry_price = rec['entry_price']
            position_size = min(cash_per_position, self.cash)
            shares = int(position_size / entry_price)
            
            if shares == 0:
                continue
            
            cost = shares * entry_price
            
            position = {
                'ticker': rec['ticker'],
                'stock_id': rec['stock_id'],
                'entry_date': current_date,
                'entry_price': entry_price,
                'shares': shares,
                'cost': cost,
                'entry_score': rec['score']
            }
            
            self.positions.append(position)
            self.cash -= cost
            
            logger.debug(f"{current_date}: BUY {shares} {rec['ticker']} @ ${entry_price:.2f} (score: {rec['score']})")
    
    def _check_and_close_positions(self, backtester: Backtester, current_date: date):
        """Check and close positions that reached hold period."""
        positions_to_close = []
        
        for pos in self.positions:
            days_held = (current_date - pos['entry_date']).days
            
            if days_held >= self.hold_days:
                positions_to_close.append(pos)
        
        for pos in positions_to_close:
            self._close_position(backtester, pos, current_date)
    
    def _close_position(self, backtester: Backtester, position: Dict, exit_date: date):
        """Close a single position and record the trade."""
        # Get exit price
        exit_price_obj = backtester.db.get_price_at_date(position['stock_id'], exit_date)
        
        if not exit_price_obj:
            # No data available, use entry price (break even)
            exit_price = position['entry_price']
        else:
            exit_price = exit_price_obj.close
        
        # Calculate P&L
        proceeds = position['shares'] * exit_price
        pnl = proceeds - position['cost']
        pnl_pct = (pnl / position['cost']) * 100
        
        # Record trade
        trade = {
            **position,
            'exit_date': exit_date,
            'exit_price': exit_price,
            'proceeds': proceeds,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'days_held': (exit_date - position['entry_date']).days
        }
        
        self.closed_trades.append(trade)
        self.positions.remove(position)
        self.cash += proceeds
        
        result = "WIN" if pnl > 0 else "LOSS"
        logger.debug(f"{exit_date}: SELL {position['shares']} {position['ticker']} @ ${exit_price:.2f} | {result} {pnl_pct:+.2f}%")
    
    def _close_all_positions(self, backtester: Backtester, exit_date: date):
        """Close all remaining positions at end of backtest."""
        for pos in list(self.positions):  # Copy list since we're modifying it
            self._close_position(backtester, pos, exit_date)
    
    def _calculate_portfolio_value(self, backtester: Backtester, current_date: date) -> float:
        """Calculate total portfolio value (cash + positions)."""
        total = self.cash
        
        for pos in self.positions:
            # Get current price
            current_price_obj = backtester.db.get_price_at_date(pos['stock_id'], current_date)
            if current_price_obj:
                current_price = current_price_obj.close
            else:
                current_price = pos['entry_price']  # Fallback
            
            total += pos['shares'] * current_price
        
        return total

