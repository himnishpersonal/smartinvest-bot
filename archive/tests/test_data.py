"""
Test suite for data collection components
"""
import pytest
from data.collectors import StockDataCollector, NewsCollector
from config import Config


class TestStockDataCollector:
    @pytest.fixture
    def collector(self):
        return StockDataCollector()
    
    def test_fetch_price_history(self, collector):
        """Test fetching historical prices"""
        df = collector.fetch_price_history('AAPL', period='1mo')
        
        assert not df.empty
        assert 'close' in df.columns
        assert 'volume' in df.columns
        assert len(df) > 0
    
    def test_fetch_current_price(self, collector):
        """Test fetching current price"""
        price_data = collector.fetch_current_price('AAPL')
        
        assert price_data is not None
        assert 'price' in price_data
        assert price_data['price'] > 0
    
    def test_fetch_fundamentals(self, collector):
        """Test fetching fundamental data"""
        fundamentals = collector.fetch_fundamentals('AAPL')
        
        assert fundamentals is not None
        assert 'pe_ratio' in fundamentals or fundamentals.get('pe_ratio') is not None
    
    def test_invalid_ticker(self, collector):
        """Test handling of invalid ticker"""
        # This should raise an error or return empty
        result = collector.fetch_price_history('INVALID123')
        # Should handle gracefully
        assert result is not None
    
    def test_batch_fetch_prices(self, collector):
        """Test batch price fetching"""
        tickers = ['AAPL', 'MSFT', 'GOOGL']
        results = collector.batch_fetch_prices(tickers, period='1mo')
        
        assert len(results) == 3
        for ticker in tickers:
            assert ticker in results
            # Should have some data (even if empty DataFrame)
            assert results[ticker] is not None


class TestNewsCollector:
    @pytest.fixture
    def collector(self):
        config = Config()
        if not config.NEWS_API_KEY or config.NEWS_API_KEY == 'your_newsapi_key':
            pytest.skip("NewsAPI key not configured")
        return NewsCollector(config.NEWS_API_KEY)
    
    @pytest.mark.skip(reason="Requires NewsAPI key")
    def test_fetch_stock_news(self, collector):
        """Test fetching stock news"""
        articles = collector.fetch_stock_news('AAPL', 'Apple Inc', days_back=7)
        
        assert isinstance(articles, list)
        if len(articles) > 0:
            assert 'title' in articles[0]
            assert 'published_at' in articles[0]
    
    @pytest.mark.skip(reason="Requires NewsAPI key")
    def test_batch_fetch_news(self, collector):
        """Test batch news fetching"""
        tickers = {'AAPL': 'Apple Inc', 'MSFT': 'Microsoft'}
        results = collector.batch_fetch_news(tickers, days_back=3)
        
        assert isinstance(results, dict)
        assert 'AAPL' in results or 'MSFT' in results
