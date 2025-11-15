"""
Feature pipeline for integrating technical, fundamental, and sentiment features.
Prepares features for machine learning models.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
from features import TechnicalFeatures, FundamentalAnalyzer, SentimentFeatureEngine
from sklearn.preprocessing import RobustScaler

logger = logging.getLogger(__name__)


class FeaturePipeline:
    """
    Integrates all feature engineering for stock analysis.
    Combines technical, fundamental, and sentiment features.
    """
    
    def __init__(self, technical_calculator: TechnicalFeatures,
                 fundamental_analyzer: FundamentalAnalyzer,
                 sentiment_engine: SentimentFeatureEngine):
        """
        Initialize FeaturePipeline with all feature calculators.
        
        Args:
            technical_calculator: TechnicalFeatures instance
            fundamental_analyzer: FundamentalAnalyzer instance
            sentiment_engine: SentimentFeatureEngine instance
        """
        self.technical_calculator = technical_calculator
        self.fundamental_analyzer = fundamental_analyzer
        self.sentiment_engine = sentiment_engine
        
        # Feature metadata
        self.feature_categories = {
            'technical': [],
            'fundamental': [],
            'sentiment': [],
            'derived': [],
            'temporal': []
        }
        
        logger.info("FeaturePipeline initialized")
    
    def prepare_features_for_stock(self, stock_data: Dict) -> Dict:
        """
        Prepare comprehensive features for a stock.
        
        Args:
            stock_data: Dict with:
                - ticker: Stock symbol
                - price_df: OHLCV DataFrame
                - fundamentals: Fundamental data dict
                - articles: List of news articles
                - sector_data: Sector average data (optional)
        
        Returns:
            Comprehensive feature dict
        
        Example:
            >>> features = pipeline.prepare_features_for_stock(stock_data)
            >>> print(f"Feature count: {len(features)}")
        """
        logger.info(f"Preparing features for {stock_data.get('ticker', 'UNKNOWN')}")
        
        ticker = stock_data.get('ticker', '')
        price_df = stock_data.get('price_df')
        fundamentals = stock_data.get('fundamentals', {})
        articles = stock_data.get('articles', [])
        sector_data = stock_data.get('sector_data')
        price_trend = stock_data.get('price_trend', 'neutral')
        
        feature_dict = {'ticker': ticker}
        
        try:
            # 1. Technical Features
            if price_df is not None and len(price_df) >= 200:
                technical_features = self.technical_calculator.calculate_all_features(price_df)
                if 'error' not in technical_features:
                    feature_dict.update({
                        'technical_score': technical_features.get('technical_score', 50),
                        'trend_score': technical_features.get('trend_score', 50),
                        'momentum_score': technical_features.get('momentum_score', 50),
                        'volume_score': technical_features.get('volume_score', 50),
                        'rsi': technical_features.get('raw_indicators', {}).get('rsi', {}).get('rsi', 50),
                        'macd': technical_features.get('raw_indicators', {}).get('macd', {}).get('macd', 0),
                        'macd_signal': technical_features.get('raw_indicators', {}).get('macd', {}).get('signal', 0),
                        'bb_percent_b': technical_features.get('raw_indicators', {}).get('bollinger', {}).get('percent_b', 0.5),
                        'atr_normalized': technical_features.get('raw_indicators', {}).get('atr', {}).get('normalized_atr', 0),
                        'obv_trend': technical_features.get('raw_indicators', {}).get('obv', {}).get('obv_trend', 0),
                    })
            
            # 2. Fundamental Features
            if fundamentals:
                fundamental_features = self.fundamental_analyzer.calculate_all_fundamentals(
                    fundamentals, sector_data
                )
                feature_dict.update({
                    'fundamental_score': fundamental_features.get('fundamental_score', 50),
                    'value_score': fundamental_features.get('value_score', 50),
                    'profitability_score': fundamental_features.get('profitability_score', 50),
                    'health_score': fundamental_features.get('health_score', 50),
                    'growth_score': fundamental_features.get('growth_score', 50),
                    'quality_score': fundamental_features.get('quality_score', 50),
                    'pe_ratio': fundamentals.get('pe_ratio'),
                    'roe': fundamentals.get('roe'),
                    'debt_to_equity': fundamentals.get('debt_to_equity'),
                    'revenue_growth': fundamentals.get('revenue_growth'),
                })
            
            # 3. Sentiment Features
            if articles:
                sentiment_features = self.sentiment_engine.calculate_comprehensive_sentiment(
                    articles, price_trend
                )
                feature_dict.update({
                    'sentiment_score': sentiment_features.get('sentiment_score', 50),
                    'sentiment_velocity': sentiment_features.get('velocity', {}).get('velocity', 0),
                    'sentiment_consistency': sentiment_features.get('consistency', {}).get('consistency_score', 50),
                    'attention_score': sentiment_features.get('attention', {}).get('attention_score', 50),
                })
            
            # 4. Derived Features
            derived = self.add_derived_features(feature_dict)
            feature_dict.update(derived)
            
            # 5. Temporal Features
            if price_df is not None:
                temporal = self.add_temporal_features(price_df)
                feature_dict.update(temporal)
            
            logger.info(f"Created {len(feature_dict)} features for {ticker}")
            
        except Exception as e:
            logger.error(f"Error preparing features for {ticker}: {e}")
            raise
        
        return feature_dict
    
    def add_derived_features(self, features: Dict) -> Dict:
        """
        Create interaction and derived features.
        
        Args:
            features: Base feature dict
        
        Returns:
            Dict with additional derived features
        """
        derived = {}
        
        # Interaction features
        try:
            momentum = features.get('momentum_score', 50)
            sentiment = features.get('sentiment_score', 50)
            derived['momentum_x_sentiment'] = (momentum * sentiment) / 100
            
            value = features.get('value_score', 50)
            quality = features.get('quality_score', 50)
            derived['value_x_quality'] = (value * quality) / 100
            
            growth = features.get('growth_score', 50)
            attention = features.get('attention_score', 50)
            derived['growth_x_attention'] = (growth * attention) / 100
            
            trend = features.get('trend_score', 50)
            volume = features.get('volume_score', 50)
            derived['trend_x_volume'] = (trend * volume) / 100
        except Exception as e:
            logger.debug(f"Error creating interaction features: {e}")
        
        # Composite scores
        try:
            derived['overall_composite'] = (
                features.get('technical_score', 50) * 0.40 +
                features.get('fundamental_score', 50) * 0.35 +
                features.get('sentiment_score', 50) * 0.25
            )
        except Exception as e:
            derived['overall_composite'] = 50
        
        return derived
    
    def add_temporal_features(self, price_df: pd.DataFrame) -> Dict:
        """
        Add temporal/seasonal features.
        
        Args:
            price_df: DataFrame with date column
        
        Returns:
            Dict with temporal features
        """
        if 'date' not in price_df.columns:
            return {}
        
        latest_date = pd.to_datetime(price_df['date'].iloc[-1])
        
        temporal = {
            'day_of_week': latest_date.dayofweek,  # 0=Monday, 6=Sunday
            'week_of_year': latest_date.isocalendar()[1],
            'month': latest_date.month,
            'quarter': (latest_date.month - 1) // 3 + 1,
        }
        
        # Add binary indicators
        temporal['is_monday'] = 1 if temporal['day_of_week'] == 0 else 0
        temporal['is_friday'] = 1 if temporal['day_of_week'] == 4 else 0
        temporal['is_quarter_end'] = 1 if latest_date.month in [3, 6, 9, 12] else 0
        
        return temporal
    
    def create_feature_vector(self, feature_dict: Dict) -> Tuple[np.ndarray, List[str]]:
        """
        Convert feature dict to numpy array.
        
        Args:
            feature_dict: Feature dictionary
        
        Returns:
            Tuple of (feature_vector, feature_names)
        """
        # Define feature order
        feature_names = [
            # Technical
            'technical_score', 'trend_score', 'momentum_score', 'volume_score',
            'rsi', 'macd', 'macd_signal', 'bb_percent_b', 'atr_normalized', 'obv_trend',
            
            # Fundamental
            'fundamental_score', 'value_score', 'profitability_score', 'health_score',
            'growth_score', 'quality_score', 'pe_ratio', 'roe', 'debt_to_equity', 'revenue_growth',
            
            # Sentiment
            'sentiment_score', 'sentiment_velocity', 'sentiment_consistency', 'attention_score',
            
            # Derived
            'momentum_x_sentiment', 'value_x_quality', 'growth_x_attention', 'trend_x_volume',
            'overall_composite',
            
            # Temporal
            'day_of_week', 'month', 'quarter', 'is_monday', 'is_friday', 'is_quarter_end'
        ]
        
        # Extract values
        feature_vector = []
        available_features = []
        
        for name in feature_names:
            value = feature_dict.get(name)
            if value is None:
                value = 0.0
            elif isinstance(value, (int, float, np.number)):
                feature_vector.append(float(value))
                available_features.append(name)
            else:
                # Skip non-numeric values
                feature_vector.append(0.0)
                available_features.append(name)
        
        return np.array(feature_vector), feature_names
    
    def validate_features(self, feature_dict: Dict) -> Dict:
        """
        Validate feature quality.
        
        Args:
            feature_dict: Feature dictionary
        
        Returns:
            Validation report
        """
        report = {
            'is_valid': True,
            'nan_count': 0,
            'inf_count': 0,
            'outlier_count': 0,
            'issues': []
        }
        
        numeric_features = {k: v for k, v in feature_dict.items() 
                          if isinstance(v, (int, float, np.number))}
        
        values = np.array(list(numeric_features.values()))
        
        # Check for NaN
        nan_count = np.isnan(values).sum()
        report['nan_count'] = int(nan_count)
        if nan_count > 0:
            report['issues'].append(f"{nan_count} NaN values found")
        
        # Check for inf
        inf_count = np.isinf(values).sum()
        report['inf_count'] = int(inf_count)
        if inf_count > 0:
            report['issues'].append(f"{inf_count} infinite values found")
        
        # Check for outliers (using Z-score > 5)
        if len(values) > 0:
            z_scores = np.abs((values - np.mean(values)) / (np.std(values) + 1e-10))
            outlier_count = (z_scores > 5).sum()
            report['outlier_count'] = int(outlier_count)
            if outlier_count > 0:
                report['issues'].append(f"{outlier_count} outliers detected")
        
        report['is_valid'] = len(report['issues']) == 0
        
        return report
    
    def get_feature_metadata(self) -> Dict:
        """
        Return metadata describing all features.
        
        Returns:
            Dictionary with feature descriptions
        """
        return {
            'technical_score': {
                'category': 'technical',
                'description': 'Overall technical analysis score (0-100)',
                'range': (0, 100),
                'importance': 'high'
            },
            'fundamental_score': {
                'category': 'fundamental',
                'description': 'Overall fundamental analysis score (0-100)',
                'range': (0, 100),
                'importance': 'high'
            },
            'sentiment_score': {
                'category': 'sentiment',
                'description': 'Weighted sentiment score (0-100)',
                'range': (0, 100),
                'importance': 'high'
            },
            # ... add more features as needed
        }
    
    def prepare_batch_features(self, stock_data_list: List[Dict],
                              max_workers: int = 4) -> List[Dict]:
        """
        Prepare features for multiple stocks in parallel.
        
        Args:
            stock_data_list: List of stock data dicts
            max_workers: Number of parallel workers
        
        Returns:
            List of feature dicts
        """
        logger.info(f"Preparing features for {len(stock_data_list)} stocks")
        
        feature_list = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.prepare_features_for_stock, data): i 
                for i, data in enumerate(stock_data_list)
            }
            
            for future in futures:
                try:
                    features = future.result()
                    feature_list.append(features)
                except Exception as e:
                    idx = futures[future]
                    logger.error(f"Error processing stock {idx}: {e}")
                    feature_list.append({'error': str(e)})
        
        logger.info(f"Completed feature preparation for {len(feature_list)} stocks")
        
        return feature_list
    
    def create_training_dataset(self, db_manager, start_date, end_date):
        """
        Create training dataset from database.
        
        Args:
            db_manager: DatabaseManager instance
            start_date: Start date for training data
            end_date: End date for training data
        
        Returns:
            Tuple of (X, y, metadata) where:
                - X: Feature matrix (numpy array or DataFrame)
                - y: Labels (binary: 1 = outperform, 0 = underperform)
                - metadata: Dict with ticker, date info
        """
        logger.info(f"Creating training dataset from {start_date.date()} to {end_date.date()}")
        
        stocks = db_manager.get_all_stocks()
        logger.info(f"Found {len(stocks)} stocks in database")
        
        # Prepare lists to collect data
        X_list = []
        y_list = []
        metadata_list = []
        
        for stock in stocks:
            try:
                # Get price history (last 365 days)
                end_date_query = datetime.now()
                start_date_query = end_date_query - timedelta(days=365)
                
                price_records = db_manager.get_price_history(
                    stock.id, 
                    start_date=start_date_query,
                    end_date=end_date_query
                )
                
                if not price_records or len(price_records) < 200:
                    logger.debug(f"Insufficient price data for {stock.ticker}: {len(price_records) if price_records else 0} days")
                    continue
                
                # Convert to DataFrame
                price_df = pd.DataFrame([{
                    'date': p.date,
                    'open': p.open,
                    'high': p.high,
                    'low': p.low,
                    'close': p.close,
                    'volume': p.volume,
                    'adj_close': p.adjusted_close
                } for p in price_records])
                
                # Get news articles
                articles = db_manager.get_news_articles(stock.id, days_back=7)
                
                # Prepare stock data
                stock_data = {
                    'ticker': stock.ticker,
                    'price_df': price_df,
                    'fundamentals': {},  # TODO: Add fundamentals if available
                    'articles': [
                        {
                            'title': article.title,
                            'source': article.source,
                            'published_at': article.published_at,
                            'sentiment_score': article.sentiment_score,
                            'sentiment_label': article.sentiment_label
                        }
                        for article in articles
                    ],
                    'sector_data': None,
                    'price_trend': 'neutral'
                }
                
                # Prepare features
                features = self.prepare_features_for_stock(stock_data)
                
                # Calculate forward return (label)
                # Use last 5 days as prediction target
                if len(price_df) >= 5:
                    current_price = price_df.iloc[-1]['close']
                    past_price = price_df.iloc[-6]['close']  # 5 days ago
                    return_pct = (current_price - past_price) / past_price
                    
                    # Label: 1 if positive return, 0 if negative
                    label = 1 if return_pct > 0 else 0
                    
                    # Convert features to vector
                    feature_vector, feature_names = self.create_feature_vector(features)
                    
                    X_list.append(feature_vector)
                    y_list.append(label)
                    metadata_list.append({
                        'ticker': stock.ticker,
                        'date': price_df.iloc[-1]['date'],
                        'return': return_pct
                    })
                    
                    logger.debug(f"Processed {stock.ticker}: {len(feature_vector)} features, label={label}")
                
            except Exception as e:
                logger.error(f"Error processing {stock.ticker}: {e}")
                continue
        
        if len(X_list) == 0:
            raise ValueError("No training data generated. Check stock data availability.")
        
        # Convert to numpy arrays
        X = np.array(X_list)
        y = np.array(y_list)
        
        logger.info(f"Training dataset created: {X.shape[0]} samples, {X.shape[1]} features")
        logger.info(f"Label distribution: {np.sum(y == 1)} positive, {np.sum(y == 0)} negative")
        
        return X, y, metadata_list

