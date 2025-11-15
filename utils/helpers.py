"""
Utility functions for SmartInvest Bot
Includes date/time utilities, data validation, formatting, and performance calculations
"""
import pytz
import re
import logging
from datetime import datetime, timedelta
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# Date and Time Utilities
# ============================================================================

def is_market_open(dt: Optional[datetime] = None) -> bool:
    """
    Check if US stock market is currently open
    
    Args:
        dt: Datetime to check (default: current time)
    
    Returns:
        True if market is open, False otherwise
    """
    if dt is None:
        dt = datetime.now(pytz.timezone('America/New_York'))
    else:
        # Convert to ET if timezone aware
        if dt.tzinfo is not None:
            dt = dt.astimezone(pytz.timezone('America/New_York'))
    
    # Check if weekday
    if dt.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False
    
    # Check market hours (9:30 AM - 4:00 PM ET)
    market_open = dt.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = dt.replace(hour=16, minute=0, second=0, microsecond=0)
    
    return market_open <= dt <= market_close


def next_market_open() -> datetime:
    """
    Get datetime of next market open
    
    Returns:
        Datetime of next market open (9:30 AM ET on next trading day)
    """
    et_tz = pytz.timezone('America/New_York')
    now = datetime.now(et_tz)
    
    # Start with tomorrow 9:30 AM
    next_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    if now.time() < datetime.strptime("09:30", "%H:%M").time():
        # If before 9:30 AM today, use today
        next_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    else:
        # Otherwise next day
        next_open += timedelta(days=1)
    
    # Skip weekends
    while next_open.weekday() >= 5:
        next_open += timedelta(days=1)
    
    return next_open


def format_time_ago(dt: datetime) -> str:
    """
    Format datetime as 'X hours ago' or 'X days ago'
    
    Args:
        dt: Datetime to format
    
    Returns:
        Human-readable string like "2h ago", "3d ago"
    """
    now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
    diff = now - dt
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes}m ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours}h ago"
    else:
        days = int(seconds / 86400)
        return f"{days}d ago"


# ============================================================================
# Data Validation Utilities
# ============================================================================

def validate_ticker(ticker: str) -> Tuple[bool, str]:
    """
    Validate stock ticker format
    
    Args:
        ticker: Ticker symbol to validate
    
    Returns:
        Tuple of (is_valid, cleaned_ticker_or_error_message)
    """
    if not ticker:
        return False, "Ticker cannot be empty"
    
    ticker = ticker.upper().strip()
    
    # Basic format check: 1-5 letters
    if not re.match(r'^[A-Z]{1,5}$', ticker):
        return False, "Invalid ticker format (must be 1-5 letters)"
    
    return True, ticker


def validate_score_range(score: float) -> Tuple[bool, float]:
    """
    Ensure score is between 0 and 100
    
    Args:
        score: Score value to validate
    
    Returns:
        Tuple of (is_valid, score_or_error_message)
    """
    try:
        score = float(score)
        if not (0 <= score <= 100):
            return False, "Score must be between 0 and 100"
        return True, score
    except (ValueError, TypeError):
        return False, "Score must be a number"


def sanitize_sql_input(text: str) -> str:
    """
    Basic SQL injection prevention
    
    Args:
        text: Text to sanitize
    
    Returns:
        Sanitized text
    """
    if not isinstance(text, str):
        return text
    
    # Remove potentially dangerous characters
    dangerous_chars = [';', '--', '/*', '*/', 'xp_', 'sp_']
    for char in dangerous_chars:
        text = text.replace(char, '')
    
    return text.strip()


# ============================================================================
# Formatting Utilities
# ============================================================================

def format_price(price: float) -> str:
    """
    Format price with appropriate decimal places
    
    Args:
        price: Price value
    
    Returns:
        Formatted price string
    """
    if price >= 1000:
        return f"${price:,.0f}"
    elif price >= 100:
        return f"${price:,.2f}"
    else:
        return f"${price:.2f}"


def format_percentage(value: float, include_sign: bool = True) -> str:
    """
    Format percentage with + or - sign
    
    Args:
        value: Percentage value
        include_sign: Include + or - sign
    
    Returns:
        Formatted percentage string
    """
    if include_sign:
        return f"{value:+.2f}%"
    return f"{abs(value):.2f}%"


def format_large_number(num: float) -> str:
    """
    Format large numbers with K, M, B suffixes
    
    Args:
        num: Number to format
    
    Returns:
        Formatted string like "$1.2B", "$500M"
    """
    if num >= 1_000_000_000:
        return f"${num/1_000_000_000:.1f}B"
    elif num >= 1_000_000:
        return f"${num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"${num/1_000:.1f}K"
    else:
        return f"${num:.0f}"


def truncate_text(text: str, max_length: int = 100) -> str:
    """
    Truncate text to max length with ellipsis
    
    Args:
        text: Text to truncate
        max_length: Maximum length
    
    Returns:
        Truncated text with ... if needed
    """
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


# ============================================================================
# Performance Calculation Utilities
# ============================================================================

def calculate_return(initial_price: float, final_price: float) -> float:
    """
    Calculate percentage return
    
    Args:
        initial_price: Starting price
        final_price: Ending price
    
    Returns:
        Percentage return
    """
    if initial_price == 0:
        return 0
    return ((final_price - initial_price) / initial_price) * 100


def calculate_sharpe_ratio(returns: list, risk_free_rate: float = 0.02) -> float:
    """
    Calculate Sharpe ratio from list of returns
    
    Args:
        returns: List of percentage returns
        risk_free_rate: Risk-free rate (annual, as decimal)
    
    Returns:
        Sharpe ratio
    """
    import numpy as np
    
    if len(returns) == 0:
        return 0
    
    returns_array = np.array(returns)
    excess_returns = returns_array - risk_free_rate
    
    if np.std(excess_returns) == 0:
        return 0
    
    return np.mean(excess_returns) / np.std(excess_returns)


def calculate_max_drawdown(prices: list) -> float:
    """
    Calculate maximum drawdown from price series
    
    Args:
        prices: List of prices
    
    Returns:
        Maximum drawdown as percentage
    """
    import numpy as np
    
    prices_array = np.array(prices)
    cummax = np.maximum.accumulate(prices_array)
    drawdown = (prices_array - cummax) / cummax
    
    return np.min(drawdown) * 100  # Return as percentage


# ============================================================================
# Error Handling Decorator
# ============================================================================

import functools


def handle_errors(default_return=None):
    """
    Decorator to handle errors gracefully
    
    Args:
        default_return: Value to return on error
    
    Example:
        @handle_errors(default_return=[])
        def some_function():
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
                return default_return
        return wrapper
    return decorator
