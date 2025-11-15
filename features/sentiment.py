"""
Advanced sentiment feature engineering for stock analysis.
Analyzes news sentiment with weighting, dynamics, and divergence detection.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class SentimentFeatureEngine:
    """
    Advanced sentiment analysis with weighted scoring, dynamics, and divergence.
    """
    
    # Source credibility tiers
    SOURCE_TIERS = {
        # Tier 1 (Highly credible)
        'bloomberg': 1.0,
        'reuters': 1.0,
        'wall-street-journal': 1.0,
        'financial-times': 1.0,
        'wsj': 1.0,
        'bloomberg.com': 1.0,
        'reuters.com': 1.0,
        
        # Tier 2 (Moderately credible)
        'cnbc': 0.8,
        'marketwatch': 0.8,
        'barron\'s': 0.8,
        'barrons': 0.8,
        'fortune': 0.8,
        'forbes': 0.8,
        'business-insider': 0.8,
        'the-economist': 0.8,
        
        # Tier 3 (General sources)
        'yahoo': 0.6,
        'yahoo-finance': 0.6,
        'seeking-alpha': 0.6,
        'motley-fool': 0.6,
        'fool': 0.6,
        'benzinga': 0.6
    }
    
    DEFAULT_WEIGHT = 0.6
    
    def __init__(self):
        """Initialize SentimentFeatureEngine."""
        pass
    
    def _get_time_weight(self, article_time: datetime, now: datetime = None) -> float:
        """
        Get recency weight for an article.
        
        Args:
            article_time: When article was published
            now: Current time (defaults to now)
        
        Returns:
            Weight from 0 to 1
        """
        if now is None:
            now = datetime.now()
        
        age_hours = (now - article_time).total_seconds() / 3600
        
        if age_hours <= 24:
            return 1.0
        elif age_hours <= 48:
            return 0.7
        elif age_hours <= 72:
            return 0.5
        else:
            return 0.3
    
    def _get_source_weight(self, source: str) -> float:
        """
        Get credibility weight for a news source.
        
        Args:
            source: News source name
        
        Returns:
            Weight from 0 to 1
        """
        source_lower = source.lower() if source else ''
        
        # Check for tier matches
        for tier_source, weight in self.SOURCE_TIERS.items():
            if tier_source in source_lower:
                return weight
        
        # Check for partial matches
        if 'bloomberg' in source_lower:
            return 1.0
        elif 'reuters' in source_lower:
            return 1.0
        elif 'wsj' in source_lower or 'wall street' in source_lower:
            return 1.0
        elif 'cnbc' in source_lower:
            return 0.8
        elif 'marketwatch' in source_lower:
            return 0.8
        elif 'yahoo' in source_lower:
            return 0.6
        
        return self.DEFAULT_WEIGHT
    
    def calculate_weighted_sentiment(self, articles: List[Dict], now: datetime = None) -> Dict:
        """
        Calculate weighted average sentiment score.
        
        Args:
            articles: List of articles with sentiment data
            now: Current time for recency calculation
        
        Returns:
            Dictionary with weighted sentiment metrics
        
        Example:
            >>> engine = SentimentFeatureEngine()
            >>> articles = [{'sentiment_score': 0.8, 'source': 'Bloomberg', 'published_at': datetime.now()}]
            >>> weighted = engine.calculate_weighted_sentiment(articles)
        """
        if not articles:
            return {
                'weighted_sentiment': 0.0,
                'raw_sentiment': 0.0,
                'article_count': 0,
                'weight_sum': 0.0
            }
        
        if now is None:
            now = datetime.now()
        
        weighted_sum = 0.0
        weight_sum = 0.0
        sentiment_scores = []
        
        for article in articles:
            sentiment_score = article.get('sentiment_score', 0.0)
            published_at = article.get('published_at', now)
            source = article.get('source', '')
            
            # Get weights
            time_weight = self._get_time_weight(published_at, now)
            source_weight = self._get_source_weight(source)
            
            # Combined weight
            total_weight = time_weight * source_weight
            
            # Add to weighted sum
            weighted_sum += sentiment_score * total_weight
            weight_sum += total_weight
            sentiment_scores.append(sentiment_score)
        
        # Calculate weighted average
        if weight_sum > 0:
            weighted_sentiment = weighted_sum / weight_sum
        else:
            weighted_sentiment = 0.0
        
        # Raw average for comparison
        raw_sentiment = np.mean(sentiment_scores) if sentiment_scores else 0.0
        
        # Convert to score (0-100)
        sentiment_score = (weighted_sentiment + 1) * 50  # Map -1:1 to 0:100
        
        return {
            'weighted_sentiment': float(weighted_sentiment),
            'raw_sentiment': float(raw_sentiment),
            'sentiment_score': float(sentiment_score),
            'article_count': len(articles),
            'weight_sum': float(weight_sum)
        }
    
    def calculate_sentiment_velocity(self, articles: List[Dict], now: datetime = None) -> Dict:
        """
        Calculate sentiment velocity (rate of change).
        
        Args:
            articles: List of articles with sentiment data
            now: Current time
        
        Returns:
            Dictionary with velocity metrics
        """
        if not articles or len(articles) < 2:
            return {
                'velocity': 0.0,
                'trend': 'stable',
                'velocity_score': 50.0
            }
        
        if now is None:
            now = datetime.now()
        
        # Split into recent (last 24h) and older (previous 3 days)
        recent_cutoff = now - timedelta(hours=24)
        older_cutoff = now - timedelta(days=3)
        
        recent_articles = []
        older_articles = []
        
        for article in articles:
            pub_time = article.get('published_at', now)
            sentiment = article.get('sentiment_score', 0.0)
            
            if pub_time >= recent_cutoff:
                recent_articles.append(sentiment)
            elif pub_time >= older_cutoff:
                older_articles.append(sentiment)
        
        # Calculate averages
        recent_avg = np.mean(recent_articles) if recent_articles else 0.0
        older_avg = np.mean(older_articles) if older_articles else 0.0
        
        # Velocity = change in sentiment
        velocity = recent_avg - older_avg
        
        # Determine trend
        if velocity > 0.3:
            trend = 'improving'
        elif velocity < -0.3:
            trend = 'declining'
        else:
            trend = 'stable'
        
        # Velocity score (0-100, 50 = stable)
        velocity_score = 50 + (velocity * 50)  # Map -1:1 to 0:100
        
        return {
            'velocity': float(velocity),
            'trend': trend,
            'velocity_score': float(np.clip(velocity_score, 0, 100)),
            'recent_sentiment': float(recent_avg),
            'older_sentiment': float(older_avg)
        }
    
    def calculate_sentiment_consistency(self, articles: List[Dict]) -> Dict:
        """
        Calculate sentiment consistency (agreement across articles).
        
        Args:
            articles: List of articles with sentiment data
        
        Returns:
            Dictionary with consistency metrics
        """
        if not articles:
            return {
                'consistency': 0.0,
                'consistency_score': 0.0,
                'std_dev': 0.0
            }
        
        sentiment_scores = [article.get('sentiment_score', 0.0) for article in articles]
        
        # Calculate standard deviation
        std_dev = np.std(sentiment_scores)
        
        # Consistency: lower std dev = higher consistency
        # Map to 0-100 score (perfect consistency = 100)
        consistency_score = max(0, 100 - (std_dev * 100))
        
        return {
            'consistency': float(1 - std_dev),  # Inverse of std dev
            'consistency_score': float(consistency_score),
            'std_dev': float(std_dev)
        }
    
    def detect_sentiment_divergence(self, articles: List[Dict], price_trend: str) -> Dict:
        """
        Detect sentiment-price divergence.
        
        Args:
            articles: List of articles with sentiment data
            price_trend: 'up', 'down', or 'neutral'
        
        Returns:
            Dictionary with divergence detection
        """
        if not articles:
            return {
                'divergence_type': None,
                'divergence_strength': 0,
                'divergence_detected': False
            }
        
        # Calculate overall sentiment trend
        sentiment_scores = [article.get('sentiment_score', 0.0) for article in articles]
        avg_sentiment = np.mean(sentiment_scores)
        
        # Determine divergence
        divergence_type = None
        divergence_strength = 0
        
        # Bullish divergence: positive sentiment but price falling
        if price_trend == 'down' and avg_sentiment > 0.3:
            divergence_type = 'bullish'
            divergence_strength = min(100, avg_sentiment * 100)
        
        # Bearish divergence: negative sentiment but price rising
        elif price_trend == 'up' and avg_sentiment < -0.3:
            divergence_type = 'bearish'
            divergence_strength = min(100, abs(avg_sentiment) * 100)
        
        return {
            'divergence_type': divergence_type,
            'divergence_strength': float(divergence_strength),
            'divergence_detected': divergence_type is not None,
            'sentiment_trend': 'positive' if avg_sentiment > 0 else 'negative',
            'price_trend': price_trend
        }
    
    def calculate_attention_score(self, articles: List[Dict], historical_avg: float = 10.0,
                                  overall_avg: float = 8.0) -> Dict:
        """
        Calculate media attention score.
        
        Args:
            articles: List of articles
            historical_avg: Historical average articles for this stock
            overall_avg: Average across all stocks
        
        Returns:
            Dictionary with attention metrics
        """
        article_count = len(articles)
        
        # Compare to historical average
        vs_historical = article_count / historical_avg if historical_avg > 0 else 1.0
        
        # Compare to overall average
        vs_overall = article_count / overall_avg if overall_avg > 0 else 1.0
        
        # Combined attention score
        attention_score = min(100, (vs_historical * 0.6 + vs_overall * 0.4) * 50)
        
        # Detect spike
        spike_detected = vs_historical > 2.0 or vs_overall > 1.5
        
        return {
            'attention_score': float(attention_score),
            'article_count': article_count,
            'vs_historical': float(vs_historical),
            'vs_overall': float(vs_overall),
            'spike_detected': spike_detected
        }
    
    def analyze_source_diversity(self, articles: List[Dict]) -> Dict:
        """
        Analyze source diversity of articles.
        
        Args:
            articles: List of articles with source info
        
        Returns:
            Dictionary with diversity metrics
        """
        if not articles:
            return {
                'unique_sources': 0,
                'diversity_score': 0.0,
                'sources': []
            }
        
        sources = [article.get('source', 'unknown') for article in articles]
        unique_sources = len(set(sources))
        total_articles = len(sources)
        
        # Diversity score (0-100)
        # Perfect diversity: each article from different source
        diversity_score = (unique_sources / max(total_articles, 1)) * 100
        
        return {
            'unique_sources': unique_sources,
            'total_articles': total_articles,
            'diversity_score': float(diversity_score),
            'sources': list(set(sources))
        }
    
    def calculate_comprehensive_sentiment(self, articles: List[Dict], 
                                         price_trend: str = 'neutral',
                                         historical_avg: float = 10.0) -> Dict:
        """
        Calculate comprehensive sentiment analysis with all metrics.
        
        Args:
            articles: List of articles with sentiment data
            price_trend: Price trend ('up', 'down', 'neutral')
            historical_avg: Historical average article count
        
        Returns:
            Comprehensive sentiment analysis dict
        
        Example:
            >>> engine = SentimentFeatureEngine()
            >>> sentiment = engine.calculate_comprehensive_sentiment(articles, 'up')
            >>> print(f"Sentiment Score: {sentiment['sentiment_score']}")
        """
        logger.info(f"Calculating comprehensive sentiment for {len(articles)} articles")
        
        # Calculate all metrics
        weighted = self.calculate_weighted_sentiment(articles)
        velocity = self.calculate_sentiment_velocity(articles)
        consistency = self.calculate_sentiment_consistency(articles)
        divergence = self.detect_sentiment_divergence(articles, price_trend)
        attention = self.calculate_attention_score(articles, historical_avg)
        diversity = self.analyze_source_diversity(articles)
        
        # Overall sentiment score (weighted average)
        # Weight: base sentiment (50%), velocity (20%), consistency (20%), attention (10%)
        sentiment_score = (
            weighted['sentiment_score'] * 0.50 +
            velocity['velocity_score'] * 0.20 +
            consistency['consistency_score'] * 0.20 +
            attention['attention_score'] * 0.10
        )
        
        # Compile signals
        signals = []
        
        if weighted['sentiment_score'] > 70:
            signals.append("Strongly positive sentiment")
        elif weighted['sentiment_score'] < 30:
            signals.append("Strongly negative sentiment")
        
        if velocity['trend'] == 'improving':
            signals.append(f"Sentiment improving (velocity: {velocity['velocity']:+.2f})")
        elif velocity['trend'] == 'declining':
            signals.append(f"Sentiment declining (velocity: {velocity['velocity']:+.2f})")
        
        if consistency['consistency_score'] > 80:
            signals.append("High sentiment consistency")
        
        if attention['spike_detected']:
            signals.append(f"High media attention (价格{attention['article_count']} articles)")
        
        if divergence['divergence_detected']:
            signals.append(f"{divergence['divergence_type'].capitalize()} divergence detected")
        
        if diversity['diversity_score'] < 30:
            signals.append(f"Low source diversity ({diversity['unique_sources']} sources)")
        
        logger.info(f"Sentiment analysis complete: Score={sentiment_score:.1f}")
        
        return {
            'sentiment_score': round(float(sentiment_score), 1),
            'weighted_sentiment': weighted,
            'velocity': velocity,
            'consistency': consistency,
            'divergence': divergence,
            'attention': attention,
            'diversity': diversity,
            'signals': signals[:8],  # Limit to 8 signals
            'raw_articles': len(articles)
        }

