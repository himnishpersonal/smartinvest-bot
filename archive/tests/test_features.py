"""
Test suite for feature engineering components
"""
import pytest
import pandas as pd
import numpy as np
from features.technical import TechnicalFeatures
from features.fundamental import FundamentalAnalyzer


class TestTechnicalFeatures:
    @pytest.fixture
    def price_data(self):
        """Generate sample price data"""
        dates = pd.date_range(start='2024-01-01', periods=200, freq='D')
        data = {
            'open': np.random.randn(200).cumsum() + 100,
            'high': np.random.randn(200).cumsum() + 102,
            'low': np.random.randn(200).cumsum() + 98,
            'close': np.random.randn(200).cumsum() + 100,
            'volume': np.random.randint(1000000, 5000000, 200)
        }
        df = pd.DataFrame(data, index=dates)
        # Ensure high >= close >= low
        df['high'] = df[['close', 'high']].max(axis=1) + 1
        df['low'] = df[['close', 'low']].min(axis=1) - 1
        return df
    
    @pytest.fixture
    def tech_features(self):
        return TechnicalFeatures()
    
    def test_calculate_rsi(self, tech_features, price_data):
        """Test RSI calculation"""
        result = tech_features.calculate_rsi(price_data)
        
        assert 'rsi' in result
        assert 0 <= result['rsi'] <= 100
        assert result['level'] in ['overbought', 'oversold', 'neutral']
    
    def test_calculate_macd(self, tech_features, price_data):
        """Test MACD calculation"""
        result = tech_features.calculate_macd(price_data)
        
        assert 'macd' in result
        assert 'signal' in result
        assert 'histogram' in result
    
    def test_calculate_all_features(self, tech_features, price_data):
        """Test complete feature calculation"""
        result = tech_features.calculate_all_features(price_data)
        
        assert 'technical_score' in result
        assert 'signals' in result
        assert isinstance(result['signals'], list)
        assert 0 <= result['technical_score'] <= 100


class TestFundamentalAnalyzer:
    @pytest.fixture
    def fundamentals(self):
        return {
            'pe_ratio': 18.5,
            'pb_ratio': 3.2,
            'roe': 0.22,
            'roa': 0.15,
            'debt_to_equity': 0.4,
            'current_ratio': 1.8,
            'revenue_growth': 0.28,
            'earnings_growth': 0.32
        }
    
    @pytest.fixture
    def analyzer(self):
        return FundamentalAnalyzer()
    
    def test_analyze_valuation(self, analyzer, fundamentals):
        """Test valuation analysis"""
        sector_avg = {'pe_ratio': 25, 'pb_ratio': 4, 'ps_ratio': 3}
        result = analyzer.analyze_valuation(fundamentals, sector_avg)
        
        assert 'value_score' in result
        assert 0 <= result['value_score'] <= 100
    
    def test_calculate_all_fundamentals(self, analyzer, fundamentals):
        """Test complete fundamental analysis"""
        result = analyzer.calculate_all_fundamentals(fundamentals, {})
        
        assert 'fundamental_score' in result
        assert 'signals' in result
        assert 0 <= result['fundamental_score'] <= 100
