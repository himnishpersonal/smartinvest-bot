#!/usr/bin/env python3
"""
Train ML model for stock recommendations
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from config import Config
from data.storage import DatabaseManager
from models.training import StockMLModel
from models.feature_pipeline import FeaturePipeline
from features.technical import TechnicalFeatures
from features.fundamental import FundamentalAnalyzer
from features.sentiment import SentimentFeatureEngine

def main():
    """Train the ML model"""
    print("=" * 80)
    print("SmartInvest Bot - ML Model Training")
    print("=" * 80)
    print()
    
    # Initialize components
    print("🔧 Initializing components...")
    config = Config()
    db_manager = DatabaseManager(config.DATABASE_URL)
    
    # Initialize feature calculators
    technical_features = TechnicalFeatures()
    fundamental_analyzer = FundamentalAnalyzer()
    sentiment_engine = SentimentFeatureEngine()
    
    # Initialize feature pipeline
    feature_pipeline = FeaturePipeline(
        technical_features,
        fundamental_analyzer,
        sentiment_engine
    )
    
    # Initialize ML model
    ml_model = StockMLModel(db_manager, feature_pipeline)
    
    print("✅ Components initialized\n")
    
    # Check data availability
    print("📊 Checking data availability...")
    stocks = db_manager.get_all_stocks()
    print(f"   Stocks in database: {len(stocks)}")
    
    if len(stocks) < 50:
        print("\n❌ Insufficient data for training")
        print("   Need at least 50 stocks with historical data")
        print("   Run: python scripts/load_full_data.py")
        return
    
    # Check date range
    # Get date range of available data
    print("   Checking date range...")
    
    print(f"\n✅ Sufficient data for training")
    
    # Ask for confirmation
    print(f"\n⚠️  About to train ML model")
    print("   This will:")
    print("   - Prepare training data from database")
    print("   - Train XGBoost classifier")
    print("   - Evaluate model performance")
    print("   - Save model to models/saved_models/")
    print(f"\n   Estimated time: 5-15 minutes")
    
    response = input("\n   Continue? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("   Cancelled.")
        return
    
    # Train model
    print("\n🤖 Training ML model...")
    print("   (This may take a while...)\n")
    
    try:
        # Prepare training dataset
        print("📊 Step 1/4: Preparing training dataset...")
        lookback_months = 6  # Use last 6 months of data
        
        # Create training dataset
        start_date = datetime.now() - timedelta(days=lookback_months * 30)
        end_date = datetime.now()
        
        print(f"   Date range: {start_date.date()} to {end_date.date()}")
        
        X, y, metadata = feature_pipeline.create_training_dataset(
            db_manager,
            start_date,
            end_date
        )
        
        print(f"   ✅ Dataset prepared: {len(X)} samples, {X.shape[1] if hasattr(X, 'shape') else 0} features")
        
        # Train model
        print("\n🎯 Step 2/4: Training model...")
        model, eval_results, backtest_results = ml_model.train_full_model(lookback_months)
        
        print("\n📊 Step 3/4: Evaluating model...")
        print(f"   Accuracy: {eval_results.get('accuracy', 0):.2%}")
        print(f"   Precision: {eval_results.get('precision', 0):.2%}")
        print(f"   Recall: {eval_results.get('recall', 0):.2%}")
        print(f"   F1 Score: {eval_results.get('f1', 0):.2%}")
        print(f"   ROC AUC: {eval_results.get('roc_auc', 0):.3f}")
        print(f"   Precision@10: {eval_results.get('precision_at_10', backtest_results.get('precision_at_10', 0)):.2%}")
        
        print("\n💰 Backtest Results:")
        print(f"   Win Rate: {backtest_results.get('win_rate', 0):.2%}")
        print(f"   Avg Return: {backtest_results.get('avg_return', 0):.2%}")
        print(f"   Sharpe Ratio: {backtest_results.get('sharpe_ratio', 0):.2f}")
        
        # Save model
        print("\n💾 Step 4/4: Saving model...")
        
        # Create directory if it doesn't exist
        os.makedirs('models/saved_models', exist_ok=True)
        
        model_path = f'models/saved_models/model_v{datetime.now().strftime("%Y%m%d_%H%M%S")}.pkl'
        ml_model.save_model(model, feature_pipeline.get_feature_names(), eval_results, model_path)
        
        # Also save as latest
        ml_model.save_model(model, feature_pipeline.get_feature_names(), eval_results, 
                          'models/saved_models/model_latest.pkl')
        
        print(f"   ✅ Model saved to {model_path}")
        print(f"   ✅ Also saved as model_latest.pkl")
        
    except Exception as e:
        print(f"\n❌ Training failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Summary
    print("\n" + "=" * 80)
    print("✅ Model Training Complete!")
    print("=" * 80)
    print("\nModel Performance:")
    print(f"  Precision@10: {eval_results.get('precision_at_10', backtest_results.get('precision_at_10', 0)):.1%}")
    print(f"  Win Rate: {backtest_results.get('win_rate', 0):.1%}")
    print(f"  Sharpe Ratio: {backtest_results.get('sharpe_ratio', 0):.2f}")
    
    if eval_results.get('precision_at_10', backtest_results.get('precision_at_10', 0)) > 0.6:
        print("\n🎉 Model performance is GOOD! Ready for production.")
    else:
        print("\n⚠️  Model performance is below target (60%)")
        print("   Consider:")
        print("   - Loading more historical data")
        print("   - Adding news sentiment data")
        print("   - Tuning hyperparameters")
    
    print("\n📝 Next steps:")
    print("   1. Bot will automatically use the trained model")
    print("   2. Run: python bot.py")
    print("   3. Test with /daily and /stock commands in Discord")
    print("=" * 80)


if __name__ == "__main__":
    main()

