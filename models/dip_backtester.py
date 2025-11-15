"""
Dip Strategy Backtesting Engine
Tests the "buy the dip" strategy with historical data
"""

import logging
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class DipBacktester:
    """
    Backtester specifically for the dip-buying strategy.
    Tests buying stocks that are oversold with strong fundamentals.
    """
    
    def __init__(self, db_manager, dip_scanner):
        """
        Initialize dip backtester.
        
        Args:
            db_manager: DatabaseManager instance
            dip_scanner: DipScanner instance (for scoring logic)
        """
        self.db = db_manager
        self.dip_scanner = dip_scanner
    
    def find_dip_candidates_at_date(self, target_date: date, limit: int = 10) -> List[Dict]:
        """
        Find dip candidates using only data available BEFORE target_date.
        This prevents lookahead bias.
        
        Args:
            target_date: Date to find dips (as if it's "today")
            limit: Max number of candidates
            
        Returns:
            List of dip candidates with scores
        """
        logger.info(f"Finding dip candidates for {target_date}")
        
        stocks = self.db.get_all_stocks()
        candidates = []
        
        for stock in stocks:
            try:
                # Get price history BEFORE target_date
                start_date = target_date - timedelta(days=365)
                prices = self.db.get_price_history(
                    stock.id,
                    start_date=start_date,
                    end_date=target_date - timedelta(days=1)
                )
                
                if not prices or len(prices) < 30:
                    continue
                
                # Convert to DataFrame
                prices_df = pd.DataFrame([{
                    'date': p.date,
                    'open': float(p.open),
                    'high': float(p.high),
                    'low': float(p.low),
                    'close': float(p.close),
                    'volume': float(p.volume)
                } for p in prices])
                
                prices_df = prices_df.sort_values('date')
                
                # Get news sentiment BEFORE target_date
                news_start = target_date - timedelta(days=30)
                articles = self.db.get_news_articles_in_range(
                    stock.id,
                    start_date=news_start,
                    end_date=target_date - timedelta(days=1)
                )
                
                avg_sentiment = 0.0
                if articles:
                    sentiments = [a.sentiment_score for a in articles if a.sentiment_score]
                    if sentiments:
                        avg_sentiment = sum(sentiments) / len(sentiments)
                
                # Get fundamentals from database (cached from daily refresh)
                # Much faster than fetching from yfinance each time
                fundamentals_db = self.db.get_latest_fundamentals(stock.id)
                
                # Convert database fundamentals to format expected by dip_scanner
                if fundamentals_db:
                    fundamentals = {
                        'pe_ratio': fundamentals_db.pe_ratio,
                        'pb_ratio': fundamentals_db.pb_ratio,
                        'roe': fundamentals_db.roe,
                        'roa': fundamentals_db.roa,
                        'debt_to_equity': fundamentals_db.debt_to_equity,
                        'current_ratio': fundamentals_db.current_ratio,
                        'profit_margin': fundamentals_db.profit_margin,
                        'revenue_growth': fundamentals_db.revenue_growth,
                        'earnings_growth': None,  # Not stored yet
                        'free_cash_flow': None,  # Not stored yet
                        'market_cap': stock.market_cap,
                        'sector': stock.sector,
                        'industry': stock.industry
                    }
                else:
                    # No fundamentals in DB, use neutral score
                    fundamentals = None
                
                # Calculate dip score
                stock_data = {
                    'stock': stock,
                    'prices_df': prices_df,
                    'news_sentiment': avg_sentiment,
                    'fundamentals': fundamentals
                }
                
                dip_details = self.dip_scanner.calculate_dip_score(stock_data)
                
                if dip_details and dip_details['total_score'] >= self.dip_scanner.min_dip_score:
                    candidate = {
                        'ticker': stock.ticker,
                        'company_name': stock.company_name,
                        'stock_id': stock.id,
                        **dip_details
                    }
                    candidates.append(candidate)
            
            except Exception as e:
                logger.debug(f"Error scoring {stock.ticker}: {e}")
                continue
        
        # Sort by total score
        candidates.sort(key=lambda x: x['total_score'], reverse=True)
        
        return candidates[:limit]
    
    def run_backtest(self, start_date: date, end_date: date, 
                     initial_capital: float = 10000.0,
                     hold_days: int = 15,
                     max_positions: int = 5) -> Dict:
        """
        Run dip strategy backtest.
        
        Strategy:
        - Each day, find top dip candidates
        - Buy up to max_positions stocks
        - Hold for hold_days
        - Track returns
        
        Args:
            start_date: Backtest start date
            end_date: Backtest end date
            initial_capital: Starting capital
            hold_days: Days to hold each position
            max_positions: Max concurrent positions
            
        Returns:
            Dict with backtest results
        """
        logger.info(f"Running dip backtest: {start_date} to {end_date}")
        logger.info(f"Capital: ${initial_capital:,.0f}, Hold: {hold_days} days, Max positions: {max_positions}")
        
        capital = initial_capital
        positions = []  # List of open positions
        closed_trades = []  # List of completed trades
        
        current_date = start_date
        
        while current_date <= end_date:
            # Close positions that have reached hold_days
            for position in positions[:]:
                days_held = (current_date - position['entry_date']).days
                
                if days_held >= hold_days:
                    # Get exit price
                    exit_price_obj = self.db.get_price_at_date(position['stock_id'], current_date)
                    
                    if exit_price_obj:
                        exit_price = float(exit_price_obj.close)
                        shares = position['shares']
                        exit_value = shares * exit_price
                        profit = exit_value - position['entry_value']
                        return_pct = (exit_price / position['entry_price'] - 1) * 100
                        
                        # Return capital
                        capital += exit_value
                        
                        # Record trade
                        closed_trades.append({
                            'ticker': position['ticker'],
                            'entry_date': position['entry_date'],
                            'exit_date': current_date,
                            'entry_price': position['entry_price'],
                            'exit_price': exit_price,
                            'shares': shares,
                            'profit': profit,
                            'return_pct': return_pct,
                            'days_held': days_held
                        })
                        
                        positions.remove(position)
                        logger.debug(f"Closed {position['ticker']}: {return_pct:+.2f}% in {days_held} days")
            
            # Open new positions if we have capital and space
            if len(positions) < max_positions and capital > 0:
                # Find dip candidates
                dip_candidates = self.find_dip_candidates_at_date(current_date, limit=max_positions * 2)
                
                # Buy top candidates we don't already own
                for candidate in dip_candidates:
                    if len(positions) >= max_positions:
                        break
                    
                    # Check if we already own this stock
                    if any(p['ticker'] == candidate['ticker'] for p in positions):
                        continue
                    
                    # Get entry price
                    entry_price_obj = self.db.get_price_at_date(candidate['stock_id'], current_date)
                    if not entry_price_obj:
                        continue
                    
                    entry_price = float(entry_price_obj.close)
                    
                    # Position size: equal weight across max_positions
                    position_size = initial_capital / max_positions
                    
                    if position_size <= capital:
                        shares = int(position_size / entry_price)
                        if shares > 0:
                            entry_value = shares * entry_price
                            capital -= entry_value
                            
                            positions.append({
                                'ticker': candidate['ticker'],
                                'stock_id': candidate['stock_id'],
                                'entry_date': current_date,
                                'entry_price': entry_price,
                                'shares': shares,
                                'entry_value': entry_value,
                                'dip_score': candidate['total_score']
                            })
                            
                            logger.debug(f"Opened {candidate['ticker']} @ ${entry_price:.2f} (Score: {candidate['total_score']})")
            
            # Move to next day
            current_date += timedelta(days=1)
        
        # Close any remaining positions at end_date
        for position in positions:
            exit_price_obj = self.db.get_price_at_date(position['stock_id'], end_date)
            
            if exit_price_obj:
                exit_price = float(exit_price_obj.close)
                shares = position['shares']
                exit_value = shares * exit_price
                profit = exit_value - position['entry_value']
                return_pct = (exit_price / position['entry_price'] - 1) * 100
                days_held = (end_date - position['entry_date']).days
                
                capital += exit_value
                
                closed_trades.append({
                    'ticker': position['ticker'],
                    'entry_date': position['entry_date'],
                    'exit_date': end_date,
                    'entry_price': position['entry_price'],
                    'exit_price': exit_price,
                    'shares': shares,
                    'profit': profit,
                    'return_pct': return_pct,
                    'days_held': days_held
                })
        
        # Calculate summary statistics
        final_value = capital
        total_return = (final_value - initial_capital) / initial_capital * 100
        
        if closed_trades:
            winning_trades = [t for t in closed_trades if t['return_pct'] > 0]
            losing_trades = [t for t in closed_trades if t['return_pct'] <= 0]
            
            win_rate = len(winning_trades) / len(closed_trades) * 100
            avg_win = np.mean([t['return_pct'] for t in winning_trades]) if winning_trades else 0
            avg_loss = np.mean([t['return_pct'] for t in losing_trades]) if losing_trades else 0
            avg_hold = np.mean([t['days_held'] for t in closed_trades])
            
            best_trade = max(closed_trades, key=lambda x: x['return_pct'])
            worst_trade = min(closed_trades, key=lambda x: x['return_pct'])
        else:
            win_rate = 0
            avg_win = 0
            avg_loss = 0
            avg_hold = 0
            best_trade = None
            worst_trade = None
        
        results = {
            'start_date': start_date,
            'end_date': end_date,
            'initial_capital': initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'total_trades': len(closed_trades),
            'winning_trades': len(winning_trades) if closed_trades else 0,
            'losing_trades': len(losing_trades) if closed_trades else 0,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'avg_hold': avg_hold,
            'best_trade': best_trade,
            'worst_trade': worst_trade,
            'all_trades': closed_trades
        }
        
        logger.info(f"Dip backtest complete: {len(closed_trades)} trades, {total_return:+.2f}% return")
        
        return results


class StockBacktester:
    """
    Backtester for individual stock performance.
    Tests buy-and-hold strategy for specific stocks.
    """
    
    def __init__(self, db_manager):
        """
        Initialize stock backtester.
        
        Args:
            db_manager: DatabaseManager instance
        """
        self.db = db_manager
    
    def backtest_stock(self, ticker: str, start_date: date, end_date: date,
                       initial_capital: float = 10000.0) -> Dict:
        """
        Backtest buy-and-hold for a specific stock.
        
        Args:
            ticker: Stock ticker symbol
            start_date: Backtest start date
            end_date: Backtest end date
            initial_capital: Starting capital
            
        Returns:
            Dict with backtest results
        """
        logger.info(f"Backtesting {ticker}: {start_date} to {end_date}")
        
        # Get stock
        stock = self.db.get_stock_by_ticker(ticker)
        if not stock:
            return {'error': f'Stock {ticker} not found in database'}
        
        # Get price history
        prices = self.db.get_price_history(
            stock.id,
            start_date=start_date,
            end_date=end_date
        )
        
        if not prices or len(prices) < 2:
            return {'error': f'Insufficient price data for {ticker}'}
        
        # Get entry and exit prices
        entry_price = float(prices[0].close)
        exit_price = float(prices[-1].close)
        
        # Calculate shares and returns
        shares = int(initial_capital / entry_price)
        entry_value = shares * entry_price
        exit_value = shares * exit_price
        
        profit = exit_value - entry_value
        total_return = (exit_value / entry_value - 1) * 100
        
        # Calculate daily returns for volatility
        price_df = pd.DataFrame([{
            'date': p.date,
            'close': float(p.close)
        } for p in prices])
        
        price_df['return'] = price_df['close'].pct_change()
        daily_volatility = price_df['return'].std()
        annualized_volatility = daily_volatility * np.sqrt(252)
        
        # Calculate max drawdown
        price_df['cummax'] = price_df['close'].cummax()
        price_df['drawdown'] = (price_df['close'] - price_df['cummax']) / price_df['cummax']
        max_drawdown = price_df['drawdown'].min() * 100
        
        # Get news sentiment stats
        articles = self.db.get_news_articles_in_range(
            stock.id,
            start_date=start_date,
            end_date=end_date
        )
        
        avg_sentiment = 0.0
        if articles:
            sentiments = [a.sentiment_score for a in articles if a.sentiment_score]
            if sentiments:
                avg_sentiment = np.mean(sentiments)
        
        results = {
            'ticker': ticker,
            'company_name': stock.company_name,
            'start_date': start_date,
            'end_date': end_date,
            'days': (end_date - start_date).days,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'shares': shares,
            'initial_capital': initial_capital,
            'entry_value': entry_value,
            'exit_value': exit_value,
            'profit': profit,
            'total_return': total_return,
            'annualized_volatility': annualized_volatility * 100,
            'max_drawdown': max_drawdown,
            'avg_sentiment': avg_sentiment,
            'news_articles': len(articles)
        }
        
        logger.info(f"{ticker} backtest complete: {total_return:+.2f}% return")
        
        return results

