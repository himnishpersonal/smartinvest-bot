"""
Stock scoring and recommendation engine.
Uses ML models and feature analysis to generate stock recommendations.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Generate stock recommendations using ML models and feature analysis.
    """
    
    def __init__(self, ml_model, feature_pipeline, db_manager):
        """
        Initialize RecommendationEngine.
        
        Args:
            ml_model: Trained ML model
            feature_pipeline: FeaturePipeline instance
            db_manager: DatabaseManager instance
        """
        self.ml_model = ml_model
        self.feature_pipeline = feature_pipeline
        self.db_manager = db_manager
        
        # Scoring weights
        self.scoring_weights = {
            'ml_confidence': 0.35,
            'technical': 0.25,
            'fundamental': 0.25,
            'sentiment': 0.15
        }
        
        logger.info("RecommendationEngine initialized")
    
    def score_single_stock(self, ticker: str) -> Dict:
        """
        Score a single stock and generate recommendation data.
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Comprehensive score dictionary
        
        Example:
            >>> score = engine.score_single_stock('AAPL')
            >>> print(f"AAPL Score: {score['overall_score']}")
        """
        logger.info(f"Scoring {ticker}")
        
        try:
            # Get data from database
            stock = self.db_manager.get_stock_by_ticker(ticker)
            if not stock:
                logger.warning(f"Stock {ticker} not found in database")
                return None
            
            # Get latest price data
            latest_price = self.db_manager.get_latest_price(stock.id)
            if not latest_price:
                logger.warning(f"No price data for {ticker}")
                return None
            
            # Get price history
            end_date = datetime.now()
            start_date = end_date - timedelta(days=252)
            price_history = self.db_manager.get_price_history(stock.id, start_date, end_date)
            
            if len(price_history) < 200:
                logger.warning(f"Insufficient price history for {ticker}")
                return None
            
            # Convert to DataFrame
            price_df = pd.DataFrame([{
                'date': p.date,
                'open': p.open,
                'high': p.high,
                'low': p.low,
                'close': p.close,
                'volume': p.volume
            } for p in price_history])
            
            # Get fundamentals (latest)
            fundamentals = {}
            # Would get from database in real implementation
            
            # Get articles (latest news)
            articles = []
            # Would get from database in real implementation
            
            # Calculate features
            stock_data = {
                'ticker': ticker,
                'price_df': price_df,
                'fundamentals': fundamentals,
                'articles': articles,
                'price_trend': 'neutral'
            }
            
            features = self.feature_pipeline.prepare_features_for_stock(stock_data)
            
            # Get ML prediction
            feature_vector, feature_names = self.feature_pipeline.create_feature_vector(features)
            ml_probability = self.ml_model.predict_proba(feature_vector.reshape(1, -1))[0][1]
            ml_confidence_score = ml_probability * 100
            
            # Extract component scores
            technical_score = features.get('technical_score', 50)
            fundamental_score = features.get('fundamental_score', 50)
            sentiment_score = features.get('sentiment_score', 50)
            
            # Calculate composite score
            overall_score = (
                self.scoring_weights['ml_confidence'] * ml_confidence_score +
                self.scoring_weights['technical'] * technical_score +
                self.scoring_weights['fundamental'] * fundamental_score +
                self.scoring_weights['sentiment'] * sentiment_score
            )
            
            # Generate signals
            signals = self.generate_signals(features, technical_score, fundamental_score, sentiment_score)
            
            # Assess risk
            risk_level, risk_score = self.calculate_risk_level(price_df)
            
            # Calculate confidence
            confidence = self.calculate_recommendation_confidence({
                'ml_probability': ml_probability,
                'features': features,
                'data_completeness': 0.85  # Would calculate based on available data
            })
            
            # Check for warnings
            warnings = self.flag_low_quality_signals({
                'latest_price': latest_price.date if latest_price else None,
                'price_count': len(price_history),
                'fundamentals': fundamentals
            })
            
            result = {
                'ticker': ticker,
                'company_name': stock.company_name,
                'sector': stock.sector,
                'industry': stock.industry,
                'price': float(latest_price.close),
                'overall_score': round(overall_score, 1),
                'technical_score': round(technical_score, 1),
                'fundamental_score': round(fundamental_score, 1),
                'sentiment_score': round(sentiment_score, 1),
                'ml_confidence': round(ml_confidence_score, 1),
                'confidence': round(confidence, 1),
                'risk_level': risk_level,
                'risk_score': round(risk_score, 1),
                'signals': signals[:5],  # Top 5 signals
                'warnings': warnings,
                'last_updated': datetime.now(),
                'features': features  # Store raw features for reference
            }
            
            logger.info(f"Scored {ticker}: {overall_score:.1f} (confidence: {confidence:.1f}%)")
            
            return result
            
        except Exception as e:
            logger.error(f"Error scoring {ticker}: {e}")
            return None
    
    def score_all_stocks(self, ticker_list: List[str], max_workers: int = 4) -> List[Dict]:
        """
        Score multiple stocks in parallel.
        
        Args:
            ticker_list: List of ticker symbols
            max_workers: Number of parallel workers
        
        Returns:
            List of score dictionaries
        """
        logger.info(f"Scoring {len(ticker_list)} stocks")
        start_time = datetime.now()
        
        scored_stocks = []
        failed = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.score_single_stock, ticker): ticker 
                for ticker in ticker_list
            }
            
            for future in futures:
                ticker = futures[future]
                try:
                    score = future.result()
                    if score:
                        scored_stocks.append(score)
                    else:
                        failed.append(ticker)
                except Exception as e:
                    logger.error(f"Failed to score {ticker}: {e}")
                    failed.append(ticker)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Scored {len(scored_stocks)} stocks ({len(scored_stocks)/len(ticker_list)*100:.1f}%) in {elapsed:.1f}s")
        
        return scored_stocks
    
    def rank_stocks(self, scored_stocks: List[Dict], 
                   min_score: float = 70.0,
                   min_confidence: float = 65.0) -> List[Dict]:
        """
        Rank and filter stocks.
        
        Args:
            scored_stocks: List of scored stock dicts
            min_score: Minimum overall score
            min_confidence: Minimum confidence level
        
        Returns:
            Ranked and filtered list
        """
        logger.info(f"Ranking {len(scored_stocks)} stocks")
        
        # Filter by thresholds
        filtered = [
            stock for stock in scored_stocks
            if stock['overall_score'] >= min_score 
            and stock['confidence'] >= min_confidence
        ]
        
        # Sort by score
        ranked = sorted(filtered, key=lambda x: x['overall_score'], reverse=True)
        
        logger.info(f"Filtered to {len(ranked)} stocks (score >= {min_score}, confidence >= {min_confidence})")
        
        return ranked
    
    def apply_diversification_rules(self, ranked_stocks: List[Dict], 
                                   max_per_sector: int = 3) -> List[Dict]:
        """
        Apply diversification rules.
        
        Args:
            ranked_stocks: Ranked stock list
            max_per_sector: Maximum picks per sector
        
        Returns:
            Diversified stock list
        """
        sector_counts = {}
        diversified = []
        
        for stock in ranked_stocks:
            sector = stock.get('sector', 'Unknown')
            count = sector_counts.get(sector, 0)
            
            if count < max_per_sector:
                diversified.append(stock)
                sector_counts[sector] = count + 1
            
            if len(diversified) >= 10:
                break
        
        logger.info(f"Diversified to {len(diversified)} stocks across sectors")
        
        return diversified
    
    def select_top_recommendations(self, ranked_stocks: List[Dict], n: int = 10) -> List[Dict]:
        """
        Select top N recommendations with ranking.
        
        Args:
            ranked_stocks: Ranked and filtered stocks
            n: Number of recommendations
        
        Returns:
            Top N recommendations with ranks
        """
        top_picks = ranked_stocks[:n]
        
        # Add rank
        for i, stock in enumerate(top_picks, 1):
            stock['rank'] = i
        
        logger.info(f"Selected top {len(top_picks)} recommendations")
        
        return top_picks
    
    def generate_signals(self, features: Dict, technical_score: float,
                        fundamental_score: float, sentiment_score: float) -> List[str]:
        """
        Generate human-readable signals.
        
        Args:
            features: Feature dictionary
            technical_score: Technical score
            fundamental_score: Fundamental score
            sentiment_score: Sentiment score
        
        Returns:
            List of signal strings
        """
        signals = []
        
        # Technical signals
        raw = features.get('raw_indicators', {})
        if raw:
            rsi = raw.get('rsi', {}).get('rsi', 50)
            if rsi > 65:
                signals.append(f"Strong momentum: RSI {rsi:.1f}")
            elif rsi < 35:
                signals.append(f"Oversold: RSI {rsi:.1f}")
            
            macd_signals = raw.get('macd', {}).get('macd_signals', [])
            if macd_signals:
                signals.append(macd_signals[0])
        
        if technical_score > 80:
            signals.append("Strong technical setup")
        
        # Fundamental signals
        if fundamental_score > 80:
            signals.append("Strong fundamentals")
        
        pe_ratio = features.get('pe_ratio')
        if pe_ratio and pe_ratio < 20:
            signals.append(f"Undervalued: P/E {pe_ratio:.1f}")
        
        roe = features.get('roe')
        if roe and roe > 0.15:
            signals.append(f"High ROE: {roe*100:.1f}%")
        
        # Sentiment signals
        if sentiment_score > 80:
            signals.append("Very positive sentiment")
        elif sentiment_score < 30:
            signals.append("Negative sentiment warning")
        
        # ML confidence
        ml_prob = features.get('ml_confidence', 50)
        if ml_prob > 80:
            signals.append(f"ML model highly confident ({ml_prob:.0f}%)")
        
        # Ensure we have signals
        if not signals:
            signals.append("Moderate overall signals")
        
        return signals[:5]
    
    def calculate_risk_level(self, price_df: pd.DataFrame) -> Tuple[str, float]:
        """
        Calculate risk level for a stock.
        
        Args:
            price_df: Price history DataFrame
        
        Returns:
            Tuple of (risk_level, risk_score)
        """
        try:
            # Calculate volatility
            returns = price_df['close'].pct_change()
            volatility = returns.std() * np.sqrt(252) * 100  # Annualized %
            
            if volatility < 15:
                risk_level = 'Low'
                risk_score = 25
            elif volatility < 30:
                risk_level = 'Medium'
                risk_score = 50
            else:
                risk_level = 'High'
                risk_score = 75
            
            return risk_level, risk_score
            
        except:
            return 'Medium', 50
    
    def calculate_recommendation_confidence(self, stock_data: Dict) -> float:
        """
        Calculate confidence in recommendation.
        
        Args:
            stock_data: Stock data dictionary
        
        Returns:
            Confidence score 0-100
        """
        confidence = 50  # Start neutral
        
        ml_prob = stock_data.get('ml_probability', 0.5)
        confidence += (ml_prob - 0.5) * 40  # ±20 points based on ML
        
        data_completeness = stock_data.get('data_completeness', 0.5)
        confidence += (data_completeness - 0.5) * 20  # ±10 points based on data
        
        return np.clip(confidence, 0, 100)
    
    def flag_low_quality_signals(self, stock_data: Dict) -> List[str]:
        """
        Flag potential data quality issues.
        
        Args:
            stock_data: Stock data dictionary
        
        Returns:
            List of warning strings
        """
        warnings = []
        
        latest_price = stock_data.get('latest_price')
        if latest_price:
            age = (datetime.now() - latest_price).days
            if age > 1:
                warnings.append(f"Stale price data ({age} days old)")
        
        price_count = stock_data.get('price_count', 0)
        if price_count < 200:
            warnings.append("Insufficient historical data")
        
        fundamentals = stock_data.get('fundamentals', {})
        if not fundamentals:
            warnings.append("Missing fundamental data")
        
        return warnings
    
    def generate_daily_recommendations(self, ticker_universe: List[str] = None) -> Tuple[List[Dict], Dict]:
        """
        Generate daily stock recommendations.
        
        Args:
            ticker_universe: Optional list of tickers to analyze
        
        Returns:
            Tuple of (recommendations, summary_statistics)
        
        Example:
            >>> recommendations, summary = engine.generate_daily_recommendations()
            >>> print(f"Top pick: {recommendations[0]['ticker']}")
        """
        logger.info("=" * 60)
        logger.info("Generating Daily Recommendations")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        
        # 1. Get stock universe
        if ticker_universe is None:
            # Would get from database in production
            ticker_universe = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'NFLX']
        
        # 2. Score all stocks
        logger.info(f"Step 1: Scoring {len(ticker_universe)} stocks")
        scored_stocks = self.score_all_stocks(ticker_universe)
        
        if not scored_stocks:
            logger.warning("No stocks successfully scored")
            return [], {}
        
        # 3. Rank and filter
        logger.info("Step 2: Ranking and filtering stocks")
        ranked_stocks = self.rank_stocks(scored_stocks)
        
        # 4. Apply diversification
        logger.info("Step 3: Applying diversification rules")
        diversified_stocks = self.apply_diversification_rules(ranked_stocks)
        
        # 5. Select top 10
        logger.info("Step 4: Selecting top recommendations")
        recommendations = self.select_top_recommendations(diversified_stocks, n=10)
        
        # 6. Generate summary
        elapsed = (datetime.now() - start_time).total_seconds()
        
        summary = {
            'total_scored': len(scored_stocks),
            'passed_filters': len(ranked_stocks),
            'final_picks': len(recommendations),
            'avg_score': float(np.mean([r['overall_score'] for r in recommendations])) if recommendations else 0,
            'avg_confidence': float(np.mean([r['confidence'] for r in recommendations])) if recommendations else 0,
            'sectors': [r.get('sector', 'Unknown') for r in recommendations],
            'risk_distribution': {
                'low': sum(1 for r in recommendations if r.get('risk_level') == 'Low'),
                'medium': sum(1 for r in recommendations if r.get('risk_level') == 'Medium'),
                'high': sum(1 for r in recommendations if r.get('risk_level') == 'High')
            },
            'processing_time': elapsed
        }
        
        logger.info(f"Recommendations complete: {len(recommendations)} picks in {elapsed:.1f}s")
        
        return recommendations, summary

