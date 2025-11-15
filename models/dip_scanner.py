"""
Buy-the-Dip Scanner Module
Identifies quality stocks that have dropped significantly (bargain hunting).

Strategy (WITH YFINANCE FUNDAMENTALS):
    1. Find stocks with recent price drops (10-30% from highs)
    2. Verify they're oversold (RSI < 40)
    3. Check volume patterns (capitulation signals)
    4. Analyze fundamentals (P/E, ROE, debt - yfinance)
    5. Consider news sentiment (safe dip vs risky drop)
    6. Look for recovery signals (price stabilization/bounce)
    
Result: Quality stocks on sale (strong fundamentals + technical dip)
"""

import logging
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional
import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


class DipScanner:
    """
    Scanner for identifying "buy the dip" opportunities.
    
    Finds stocks that:
    - Recently dropped in price (temporary weakness)
    - Have strong fundamentals (long-term strength)
    - Show technical oversold signals (bounce likely)
    """
    
    def __init__(self, db_manager, min_dip_score: int = 60):
        """
        Initialize the dip scanner.
        
        Args:
            db_manager: DatabaseManager instance
            min_dip_score: Minimum score threshold (0-100)
        """
        self.db_manager = db_manager
        self.min_dip_score = min_dip_score
        logger.info(f"DipScanner initialized (min score: {min_dip_score})")
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """
        Calculate RSI (Relative Strength Index).
        
        Args:
            prices: Series of closing prices
            period: RSI period (default 14)
            
        Returns:
            RSI value (0-100)
        """
        if len(prices) < period + 1:
            return 50.0  # Neutral if insufficient data
        
        # Calculate price changes
        delta = prices.diff()
        
        # Separate gains and losses
        gains = delta.where(delta > 0, 0.0)
        losses = -delta.where(delta < 0, 0.0)
        
        # Calculate average gains and losses
        avg_gain = gains.rolling(window=period, min_periods=period).mean()
        avg_loss = losses.rolling(window=period, min_periods=period).mean()
        
        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0
    
    def fetch_fundamentals_yfinance(self, ticker: str) -> Dict:
        """
        Fetch fundamental data using yfinance (free).
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary with fundamental metrics or None if unavailable
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Extract key fundamentals
            fundamentals = {
                'pe_ratio': info.get('trailingPE') or info.get('forwardPE'),
                'roe': info.get('returnOnEquity'),  # Decimal (e.g., 0.15 = 15%)
                'debt_to_equity': info.get('debtToEquity'),
                'profit_margin': info.get('profitMargins'),  # Decimal
                'revenue_growth': info.get('revenueGrowth'),  # Decimal (YoY)
                'earnings_growth': info.get('earningsGrowth'),  # Decimal (YoY)
                'current_ratio': info.get('currentRatio'),  # Liquidity
                'free_cash_flow': info.get('freeCashflow'),
                'market_cap': info.get('marketCap'),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
            }
            
            # Log what we got
            available_metrics = [k for k, v in fundamentals.items() if v is not None]
            logger.debug(f"{ticker} fundamentals: {len(available_metrics)}/11 metrics available")
            
            return fundamentals
            
        except Exception as e:
            logger.warning(f"Could not fetch fundamentals for {ticker}: {e}")
            return None
    
    def calculate_dip_score(self, stock_data: Dict) -> Dict:
        """
        Calculate "dip score" for a stock (0-100).
        
        Scoring breakdown:
        - Price drop (0-30 pts): Recent decline from highs
        - RSI oversold (0-25 pts): Technical bounce signal
        - Volume spike (0-15 pts): Capitulation signal
        - Fundamentals (0-30 pts): Company quality (yfinance)
        
        Args:
            stock_data: Dictionary with stock info and price history
            
        Returns:
            Dictionary with score and details
        """
        score = 0
        details = {}
        
        stock = stock_data['stock']
        prices_df = stock_data['prices_df']
        news_sentiment = stock_data.get('news_sentiment', 0.0)
        fundamentals = stock_data.get('fundamentals')  # yfinance data
        
        if len(prices_df) < 30:
            return None  # Need at least 30 days of data
        
        # Get price data
        current_price = float(prices_df['close'].iloc[-1])
        
        # Calculate 52-week (or available) high
        lookback_days = min(252, len(prices_df))
        recent_high = float(prices_df['close'].tail(lookback_days).max())
        
        # Calculate 10-day and 5-day drops
        if len(prices_df) >= 10:
            price_10d_ago = float(prices_df['close'].iloc[-10])
            drop_10d_pct = (current_price - price_10d_ago) / price_10d_ago
        else:
            drop_10d_pct = 0.0
        
        if len(prices_df) >= 5:
            price_5d_ago = float(prices_df['close'].iloc[-5])
            drop_5d_pct = (current_price - price_5d_ago) / price_5d_ago
        else:
            drop_5d_pct = 0.0
        
        # 1. PRICE DROP SCORE (0-30 points)
        # =====================================
        drop_from_high = (current_price - recent_high) / recent_high
        
        if -0.05 <= drop_from_high < 0:
            price_score = 10  # Small dip
        elif -0.10 <= drop_from_high < -0.05:
            price_score = 20  # Moderate dip
        elif -0.20 <= drop_from_high < -0.10:
            price_score = 30  # Sweet spot
        elif -0.30 <= drop_from_high < -0.20:
            price_score = 25  # Large dip (slightly riskier)
        elif drop_from_high < -0.30:
            price_score = 10  # Too big, might be broken
        else:
            price_score = 0  # Not a dip
        
        score += price_score
        details['price_drop_pct'] = drop_from_high * 100
        details['price_score'] = price_score
        
        # 2. RSI OVERSOLD SCORE (0-25 points)
        # =====================================
        rsi = self.calculate_rsi(prices_df['close'])
        
        if rsi < 20:
            rsi_score = 25  # Deeply oversold
        elif rsi < 30:
            rsi_score = 20  # Oversold
        elif rsi < 40:
            rsi_score = 15  # Moderately oversold
        elif rsi < 50:
            rsi_score = 10  # Slightly weak
        else:
            rsi_score = 5  # Not oversold
        
        score += rsi_score
        details['rsi'] = round(rsi, 1)
        details['rsi_score'] = rsi_score
        
        # 3. VOLUME SPIKE SCORE (0-15 points)
        # =====================================
        if len(prices_df) >= 20:
            recent_volume = float(prices_df['volume'].tail(5).mean())
            avg_volume = float(prices_df['volume'].tail(20).mean())
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1.0
            
            if volume_ratio > 2.0:
                volume_score = 15  # High volume capitulation
            elif volume_ratio > 1.5:
                volume_score = 10  # Elevated volume
            elif volume_ratio > 1.2:
                volume_score = 5  # Slightly higher volume
            else:
                volume_score = 3  # Normal volume
        else:
            volume_score = 3
            volume_ratio = 1.0
        
        score += volume_score
        details['volume_ratio'] = round(volume_ratio, 2)
        details['volume_score'] = volume_score
        
        # 4. FUNDAMENTALS SCORE (0-30 points)
        # =====================================
        # Use yfinance fundamentals to assess quality
        fundamental_score = 0
        
        if fundamentals:
            # P/E Ratio (0-8 pts) - Lower is better, but not too low
            pe = fundamentals.get('pe_ratio')
            if pe:
                if 5 <= pe <= 20:
                    fundamental_score += 8  # Excellent value
                    details['pe_rating'] = 'Excellent'
                elif 20 < pe <= 30 or 3 <= pe < 5:
                    fundamental_score += 5  # Good
                    details['pe_rating'] = 'Good'
                elif pe < 3 or pe > 50:
                    fundamental_score += 1  # Too extreme
                    details['pe_rating'] = 'Extreme'
                else:
                    fundamental_score += 3  # Acceptable
                    details['pe_rating'] = 'Acceptable'
                details['pe_ratio'] = round(pe, 2)
            
            # ROE - Return on Equity (0-7 pts) - Higher is better
            roe = fundamentals.get('roe')
            if roe:
                roe_pct = roe * 100  # Convert to percentage
                if roe_pct >= 20:
                    fundamental_score += 7  # Excellent profitability
                    details['roe_rating'] = 'Excellent'
                elif roe_pct >= 15:
                    fundamental_score += 5  # Good
                    details['roe_rating'] = 'Good'
                elif roe_pct >= 10:
                    fundamental_score += 3  # Acceptable
                    details['roe_rating'] = 'Acceptable'
                else:
                    fundamental_score += 1  # Weak
                    details['roe_rating'] = 'Weak'
                details['roe'] = round(roe_pct, 1)
            
            # Debt to Equity (0-5 pts) - Lower is better
            debt_to_equity = fundamentals.get('debt_to_equity')
            if debt_to_equity is not None:
                if debt_to_equity < 50:
                    fundamental_score += 5  # Low debt
                    details['debt_rating'] = 'Low'
                elif debt_to_equity < 100:
                    fundamental_score += 3  # Moderate debt
                    details['debt_rating'] = 'Moderate'
                else:
                    fundamental_score += 1  # High debt
                    details['debt_rating'] = 'High'
                details['debt_to_equity'] = round(debt_to_equity, 1)
            
            # Profit Margin (0-5 pts) - Higher is better
            profit_margin = fundamentals.get('profit_margin')
            if profit_margin:
                margin_pct = profit_margin * 100
                if margin_pct >= 20:
                    fundamental_score += 5  # Excellent margins
                    details['margin_rating'] = 'Excellent'
                elif margin_pct >= 10:
                    fundamental_score += 3  # Good margins
                    details['margin_rating'] = 'Good'
                else:
                    fundamental_score += 1  # Thin margins
                    details['margin_rating'] = 'Thin'
                details['profit_margin'] = round(margin_pct, 1)
            
            # Growth (0-5 pts) - Revenue or Earnings growth
            revenue_growth = fundamentals.get('revenue_growth')
            earnings_growth = fundamentals.get('earnings_growth')
            
            if revenue_growth or earnings_growth:
                growth_rate = max(revenue_growth or 0, earnings_growth or 0) * 100
                if growth_rate >= 15:
                    fundamental_score += 5  # High growth
                    details['growth_rating'] = 'High'
                elif growth_rate >= 5:
                    fundamental_score += 3  # Moderate growth
                    details['growth_rating'] = 'Moderate'
                elif growth_rate >= 0:
                    fundamental_score += 1  # Stable
                    details['growth_rating'] = 'Stable'
                else:
                    fundamental_score += 0  # Declining
                    details['growth_rating'] = 'Declining'
                details['growth_rate'] = round(growth_rate, 1)
            
            details['fundamental_score'] = fundamental_score
        else:
            # No fundamentals available - give neutral score
            fundamental_score = 15  # Middle ground (50% of max)
            details['fundamental_score'] = fundamental_score
            details['fundamentals_available'] = False
        
        score += fundamental_score
        
        # FINAL RESULT
        # =====================================
        details['total_score'] = score
        details['current_price'] = current_price
        details['recent_high'] = recent_high
        details['drop_5d_pct'] = round(drop_5d_pct * 100, 2)
        details['drop_10d_pct'] = round(drop_10d_pct * 100, 2)
        
        # Risk assessment
        if drop_from_high < -0.25:
            details['risk_level'] = 'HIGH'
        elif drop_from_high < -0.15:
            details['risk_level'] = 'MODERATE'
        else:
            details['risk_level'] = 'LOW'
        
        # Quality rating (based on fundamentals)
        if fundamental_score >= 25:
            details['quality'] = '⭐⭐⭐⭐⭐'  # Excellent fundamentals
        elif fundamental_score >= 20:
            details['quality'] = '⭐⭐⭐⭐'  # Good fundamentals
        elif fundamental_score >= 15:
            details['quality'] = '⭐⭐⭐'  # Decent fundamentals
        elif fundamental_score >= 10:
            details['quality'] = '⭐⭐'  # Weak fundamentals
        else:
            details['quality'] = '⭐'  # Poor fundamentals
        
        return details
    
    def find_dip_candidates(self, limit: int = 10) -> List[Dict]:
        """
        Scan all stocks and find top "buy the dip" candidates.
        
        Args:
            limit: Maximum number of candidates to return
            
        Returns:
            List of dicts with stock info and dip scores
        """
        logger.info(f"Scanning for dip opportunities (min score: {self.min_dip_score})")
        
        # Get all stocks from database
        stocks = self.db_manager.get_all_stocks()
        logger.info(f"Analyzing {len(stocks)} stocks...")
        
        candidates = []
        
        for stock in stocks:
            try:
                # Get price history (last 252 days or available)
                end_date = date.today()
                start_date = end_date - timedelta(days=365)
                
                prices = self.db_manager.get_price_history(
                    stock_id=stock.id,
                    start_date=start_date,
                    end_date=end_date
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
                
                # Get news sentiment (last 30 days)
                news_start = end_date - timedelta(days=30)
                news_articles = self.db_manager.get_news_articles_in_range(
                    stock_id=stock.id,
                    start_date=news_start,
                    end_date=end_date
                )
                
                avg_sentiment = 0.0
                if news_articles:
                    sentiments = [a.sentiment_score for a in news_articles if a.sentiment_score]
                    if sentiments:
                        avg_sentiment = sum(sentiments) / len(sentiments)
                
                # Get fundamentals from database (much faster than yfinance)
                fundamentals_db = self.db_manager.get_latest_fundamentals(stock.id)
                
                # Convert database fundamentals to expected format
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
                    # Fallback to yfinance if not in DB (e.g., new stock)
                    fundamentals = self.fetch_fundamentals_yfinance(stock.ticker)
                
                # Calculate dip score
                stock_data = {
                    'stock': stock,
                    'prices_df': prices_df,
                    'news_sentiment': avg_sentiment,
                    'fundamentals': fundamentals
                }
                
                dip_details = self.calculate_dip_score(stock_data)
                
                if dip_details and dip_details['total_score'] >= self.min_dip_score:
                    candidate = {
                        'ticker': stock.ticker,
                        'company_name': stock.company_name,
                        'sector': stock.sector,
                        **dip_details
                    }
                    candidates.append(candidate)
                    logger.debug(f"  ✓ {stock.ticker}: Score {dip_details['total_score']}")
            
            except Exception as e:
                logger.debug(f"  ✗ {stock.ticker}: {e}")
                continue
        
        # Sort by total score (descending)
        candidates.sort(key=lambda x: x['total_score'], reverse=True)
        
        logger.info(f"Found {len(candidates)} dip candidates (min score: {self.min_dip_score})")
        
        return candidates[:limit]
    
    def get_dip_reason(self, dip_details: Dict) -> str:
        """
        Generate human-readable explanation for why stock is a dip candidate.
        
        Args:
            dip_details: Dip scoring details
            
        Returns:
            String explanation
        """
        reasons = []
        
        # Price drop reason
        drop_pct = dip_details['price_drop_pct']
        if drop_pct < -20:
            reasons.append(f"Down {abs(drop_pct):.1f}% from high")
        elif drop_pct < -10:
            reasons.append(f"Dropped {abs(drop_pct):.1f}%")
        else:
            reasons.append(f"Pullback {abs(drop_pct):.1f}%")
        
        # RSI reason
        rsi = dip_details['rsi']
        if rsi < 30:
            reasons.append("deeply oversold")
        elif rsi < 40:
            reasons.append("oversold")
        
        # Fundamental reasons
        pe_rating = dip_details.get('pe_rating')
        if pe_rating == 'Excellent':
            reasons.append("attractive valuation")
        
        roe_rating = dip_details.get('roe_rating')
        if roe_rating in ['Excellent', 'Good']:
            reasons.append("strong profitability")
        
        debt_rating = dip_details.get('debt_rating')
        if debt_rating == 'Low':
            reasons.append("low debt")
        
        growth_rating = dip_details.get('growth_rating')
        if growth_rating == 'High':
            reasons.append("high growth")
        
        # Overall fundamental quality
        fundamental_score = dip_details.get('fundamental_score', 0)
        if fundamental_score >= 25:
            reasons.append("💎 excellent fundamentals")
        elif fundamental_score >= 20:
            reasons.append("strong fundamentals")
        
        return ", ".join(reasons) if reasons else "technical dip"

