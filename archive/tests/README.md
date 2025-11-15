# SmartInvest Bot Test Suite

## Overview

Test suite for the SmartInvest Discord bot, covering data collection, feature engineering, and ML model components.

## Running Tests

### Run all tests
```bash
python run_tests.py
# or
pytest tests/ -v
```

### Run specific test file
```bash
pytest tests/test_data.py -v
pytest tests/test_features.py -v
pytest tests/test_models.py -v
```

### Run manual pipeline tests
```bash
python scripts/test_pipeline.py
```

## Test Structure

- **test_data.py** - Tests for data collection (StockDataCollector, NewsCollector)
- **test_features.py** - Tests for feature engineering (TechnicalFeatures, FundamentalAnalyzer)
- **test_models.py** - Tests for ML models and recommendation engine

## Test Requirements

- Python 3.9+
- pytest
- Test data from Yahoo Finance (AAPL, MSFT, etc.)
- NewsAPI key (optional, for news tests)

## Notes

- Some tests require API keys and will be skipped if not configured
- Model tests require a trained model in `models/saved_models/`
- Use `@pytest.mark.skip` to skip tests that require external services
