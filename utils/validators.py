"""
Input validation utilities for SmartInvest Bot
"""
import re
from datetime import datetime
from typing import Tuple, Optional


def validate_ticker_format(ticker: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate ticker symbol format
    
    Args:
        ticker: Ticker symbol to validate
    
    Returns:
        Tuple of (is_valid, cleaned_ticker, error_message)
    """
    if not ticker:
        return False, None, "Ticker cannot be empty"
    
    # Clean input
    ticker = ticker.upper().strip()
    
    # Check format: 1-5 letters only
    if not re.match(r'^[A-Z]{1,5}$', ticker):
        return False, None, "Ticker must be 1-5 letters (A-Z)"
    
    return True, ticker, None


def validate_share_count(shares: int) -> Tuple[bool, Optional[str]]:
    """
    Validate share count
    
    Args:
        shares: Number of shares
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(shares, int):
        return False, "Shares must be a whole number"
    
    if shares <= 0:
        return False, "Shares must be positive"
    
    if shares > 1000000:
        return False, "Share count too large (max: 1,000,000)"
    
    return True, None


def validate_threshold(threshold: float) -> Tuple[bool, Optional[str]]:
    """
    Validate score threshold
    
    Args:
        threshold: Threshold value
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(threshold, (int, float)):
        return False, "Threshold must be a number"
    
    if not (0 <= threshold <= 100):
        return False, "Threshold must be between 0 and 100"
    
    return True, None


def validate_date_range(start_date, end_date) -> Tuple[bool, Optional[str]]:
    """
    Validate date range
    
    Args:
        start_date: Start date
        end_date: End date
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if start_date >= end_date:
        return False, "Start date must be before end date"
    
    if end_date > datetime.now():
        return False, "End date cannot be in the future"
    
    return True, None
