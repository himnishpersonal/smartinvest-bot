"""
Performance Metrics Calculator for Backtesting
Calculates comprehensive trading performance statistics
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class PerformanceAnalyzer:
    """
    Calculates comprehensive performance metrics for backtest results.
    """
    
    def __init__(self, closed_trades: List[Dict], equity_curve: List[Dict], starting_capital: float):
        """
        Initialize performance analyzer.
        
        Args:
            closed_trades: List of completed trades
            equity_curve: List of daily portfolio values
            starting_capital: Initial capital
        """
        self.trades = closed_trades
        self.equity_curve = equity_curve
        self.starting_capital = starting_capital
        
        logger.info(f"Analyzing {len(closed_trades)} trades")
    
    def calculate_all_metrics(self) -> Dict:
        """
        Calculate all performance metrics.
        
        Returns:
            Dictionary with comprehensive metrics
        """
        if not self.trades or not self.equity_curve:
            return self._empty_metrics()
        
        final_value = self.equity_curve[-1]['value']
        
        metrics = {
            # Basic returns
            'starting_capital': self.starting_capital,
            'final_value': final_value,
            'total_return': self._calculate_total_return(),
            'total_return_pct': ((final_value - self.starting_capital) / self.starting_capital) * 100,
            
            # Trade statistics
            'total_trades': len(self.trades),
            'winning_trades': self._count_winners(),
            'losing_trades': self._count_losers(),
            'win_rate': self._calculate_win_rate(),
            'avg_win': self._calculate_avg_win(),
            'avg_loss': self._calculate_avg_loss(),
            'avg_trade_return': self._calculate_avg_trade_return(),
            'best_trade': self._get_best_trade(),
            'worst_trade': self._get_worst_trade(),
            
            # Risk metrics
            'sharpe_ratio': self._calculate_sharpe_ratio(),
            'sortino_ratio': self._calculate_sortino_ratio(),
            'max_drawdown': self._calculate_max_drawdown(),
            'max_drawdown_duration': self._calculate_max_drawdown_duration(),
            
            # Benchmark comparison
            'benchmark_return': self._get_benchmark_return(),
            'alpha': 0.0,  # Will be calculated after benchmark
            
            # Additional metrics
            'profit_factor': self._calculate_profit_factor(),
            'avg_days_held': self._calculate_avg_hold_period(),
            'total_days': (self.equity_curve[-1]['date'] - self.equity_curve[0]['date']).days,
        }
        
        # Calculate alpha (outperformance vs benchmark)
        metrics['alpha'] = metrics['total_return_pct'] - metrics['benchmark_return']
        
        logger.info(f"Metrics calculated: Return {metrics['total_return_pct']:.2f}%, Win Rate {metrics['win_rate']:.1f}%")
        
        return metrics
    
    def _empty_metrics(self) -> Dict:
        """Return empty metrics if no trades."""
        return {
            'starting_capital': self.starting_capital,
            'final_value': self.starting_capital,
            'total_return': 0.0,
            'total_return_pct': 0.0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'avg_trade_return': 0.0,
            'best_trade': None,
            'worst_trade': None,
            'sharpe_ratio': 0.0,
            'sortino_ratio': 0.0,
            'max_drawdown': 0.0,
            'max_drawdown_duration': 0,
            'benchmark_return': 0.0,
            'alpha': 0.0,
            'profit_factor': 0.0,
            'avg_days_held': 0,
            'total_days': 0,
        }
    
    def _calculate_total_return(self) -> float:
        """Calculate total return in dollars."""
        return self.equity_curve[-1]['value'] - self.starting_capital
    
    def _count_winners(self) -> int:
        """Count winning trades."""
        return sum(1 for t in self.trades if t['pnl'] > 0)
    
    def _count_losers(self) -> int:
        """Count losing trades."""
        return sum(1 for t in self.trades if t['pnl'] <= 0)
    
    def _calculate_win_rate(self) -> float:
        """Calculate win rate percentage."""
        if not self.trades:
            return 0.0
        return (self._count_winners() / len(self.trades)) * 100
    
    def _calculate_avg_win(self) -> float:
        """Calculate average winning trade percentage."""
        winners = [t['pnl_pct'] for t in self.trades if t['pnl'] > 0]
        return np.mean(winners) if winners else 0.0
    
    def _calculate_avg_loss(self) -> float:
        """Calculate average losing trade percentage."""
        losers = [t['pnl_pct'] for t in self.trades if t['pnl'] <= 0]
        return np.mean(losers) if losers else 0.0
    
    def _calculate_avg_trade_return(self) -> float:
        """Calculate average return per trade."""
        if not self.trades:
            return 0.0
        return np.mean([t['pnl_pct'] for t in self.trades])
    
    def _get_best_trade(self) -> Dict:
        """Get best performing trade."""
        if not self.trades:
            return None
        return max(self.trades, key=lambda x: x['pnl_pct'])
    
    def _get_worst_trade(self) -> Dict:
        """Get worst performing trade."""
        if not self.trades:
            return None
        return min(self.trades, key=lambda x: x['pnl_pct'])
    
    def _calculate_sharpe_ratio(self, risk_free_rate: float = 0.0) -> float:
        """
        Calculate Sharpe ratio (risk-adjusted returns).
        
        Sharpe = (Average Return - Risk Free Rate) / Standard Deviation
        Annualized for 252 trading days
        """
        if len(self.equity_curve) < 2:
            return 0.0
        
        # Calculate daily returns
        returns = []
        for i in range(1, len(self.equity_curve)):
            prev_value = self.equity_curve[i-1]['value']
            curr_value = self.equity_curve[i]['value']
            daily_return = (curr_value - prev_value) / prev_value
            returns.append(daily_return)
        
        if not returns or np.std(returns) == 0:
            return 0.0
        
        avg_return = np.mean(returns)
        std_return = np.std(returns)
        
        # Annualize
        sharpe = (avg_return - risk_free_rate) / std_return * np.sqrt(252)
        
        return sharpe
    
    def _calculate_sortino_ratio(self, risk_free_rate: float = 0.0) -> float:
        """
        Calculate Sortino ratio (like Sharpe, but only penalizes downside volatility).
        """
        if len(self.equity_curve) < 2:
            return 0.0
        
        # Calculate daily returns
        returns = []
        for i in range(1, len(self.equity_curve)):
            prev_value = self.equity_curve[i-1]['value']
            curr_value = self.equity_curve[i]['value']
            daily_return = (curr_value - prev_value) / prev_value
            returns.append(daily_return)
        
        if not returns:
            return 0.0
        
        # Only use negative returns for downside deviation
        downside_returns = [r for r in returns if r < 0]
        
        if not downside_returns or np.std(downside_returns) == 0:
            return 0.0
        
        avg_return = np.mean(returns)
        downside_std = np.std(downside_returns)
        
        # Annualize
        sortino = (avg_return - risk_free_rate) / downside_std * np.sqrt(252)
        
        return sortino
    
    def _calculate_max_drawdown(self) -> float:
        """
        Calculate maximum drawdown (worst peak-to-trough decline).
        Returns as negative percentage.
        """
        if not self.equity_curve:
            return 0.0
        
        values = [point['value'] for point in self.equity_curve]
        peak = values[0]
        max_dd = 0.0
        
        for value in values:
            if value > peak:
                peak = value
            
            dd = ((value - peak) / peak) * 100
            if dd < max_dd:
                max_dd = dd
        
        return max_dd
    
    def _calculate_max_drawdown_duration(self) -> int:
        """
        Calculate longest drawdown duration in days.
        """
        if not self.equity_curve:
            return 0
        
        values = [point['value'] for point in self.equity_curve]
        peak = values[0]
        peak_date = self.equity_curve[0]['date']
        current_dd_start = peak_date
        max_dd_days = 0
        
        for i, value in enumerate(values):
            if value > peak:
                # New peak, drawdown ended
                if current_dd_start:
                    dd_duration = (self.equity_curve[i]['date'] - current_dd_start).days
                    max_dd_days = max(max_dd_days, dd_duration)
                
                peak = value
                peak_date = self.equity_curve[i]['date']
                current_dd_start = None
            elif value < peak and current_dd_start is None:
                # Drawdown started
                current_dd_start = peak_date
        
        # Check if still in drawdown at end
        if current_dd_start:
            dd_duration = (self.equity_curve[-1]['date'] - current_dd_start).days
            max_dd_days = max(max_dd_days, dd_duration)
        
        return max_dd_days
    
    def _get_benchmark_return(self) -> float:
        """
        Get S&P 500 return for comparison.
        Uses yfinance to fetch ^GSPC data.
        """
        try:
            import yfinance as yf
            
            start_date = self.equity_curve[0]['date']
            end_date = self.equity_curve[-1]['date']
            
            spy = yf.Ticker("^GSPC")
            data = spy.history(start=start_date, end=end_date)
            
            if len(data) < 2:
                return 0.0
            
            start_price = data.iloc[0]['Close']
            end_price = data.iloc[-1]['Close']
            
            return ((end_price - start_price) / start_price) * 100
            
        except Exception as e:
            logger.warning(f"Could not fetch benchmark data: {e}")
            return 0.0
    
    def _calculate_profit_factor(self) -> float:
        """
        Calculate profit factor (total wins / total losses).
        > 1.0 is profitable.
        """
        total_wins = sum(t['pnl'] for t in self.trades if t['pnl'] > 0)
        total_losses = abs(sum(t['pnl'] for t in self.trades if t['pnl'] < 0))
        
        if total_losses == 0:
            return float('inf') if total_wins > 0 else 0.0
        
        return total_wins / total_losses
    
    def _calculate_avg_hold_period(self) -> float:
        """Calculate average days held per position."""
        if not self.trades:
            return 0.0
        
        return np.mean([t['days_held'] for t in self.trades])
    
    def get_monthly_returns(self) -> pd.DataFrame:
        """
        Calculate monthly returns for detailed analysis.
        
        Returns:
            DataFrame with monthly returns
        """
        if not self.equity_curve:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.equity_curve)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        
        # Resample to month-end
        monthly = df['value'].resample('M').last()
        monthly_returns = monthly.pct_change() * 100
        
        return pd.DataFrame({
            'Month': monthly.index.strftime('%Y-%m'),
            'Return (%)': monthly_returns.values
        })
    
    def get_trade_distribution(self) -> Dict:
        """
        Get distribution of trade returns for visualization.
        
        Returns:
            Dict with bins and counts
        """
        if not self.trades:
            return {'bins': [], 'counts': []}
        
        returns = [t['pnl_pct'] for t in self.trades]
        
        # Create histogram bins
        hist, bin_edges = np.histogram(returns, bins=20)
        
        return {
            'bins': bin_edges.tolist(),
            'counts': hist.tolist(),
            'returns': returns
        }

