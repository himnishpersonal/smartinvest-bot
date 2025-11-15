"""
Machine learning model training for stock prediction.
Includes model training, evaluation, backtesting, and persistence.
"""

import logging
import joblib
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import json

from xgboost import XGBClassifier, XGBRegressor
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, VotingClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)
from sklearn.model_selection import TimeSeriesSplit

logger = logging.getLogger(__name__)


class StockMLModel:
    """
    Machine learning model for stock prediction and recommendation.
    """
    
    def __init__(self, db_manager=None, feature_pipeline=None):
        """
        Initialize StockMLModel.
        
        Args:
            db_manager: DatabaseManager instance (optional)
            feature_pipeline: FeaturePipeline instance (optional)
        """
        self.db_manager = db_manager
        self.feature_pipeline = feature_pipeline
        self.models = {}
        self.feature_names = []
        self.metadata = {}
        self.version = '1.0.0'
    
    def create_labels(self, returns_df: pd.DataFrame, horizon: str = '5d',
                     threshold: str = 'market') -> pd.Series:
        """
        Create binary or continuous labels for training.
        
        Args:
            returns_df: DataFrame with stock returns and market returns
            horizon: '5d', '10d', '30d'
            threshold: 'market' (outperform market) or numeric threshold
        
        Returns:
            Labels array
        """
        horizon_days = int(horizon.replace('d', ''))
        returns_col = f'return_{horizon_days}d'
        
        if returns_col not in returns_df.columns:
            raise ValueError(f"Column {returns_col} not found in returns_df")
        
        stock_returns = returns_df[returns_col]
        
        if threshold == 'market':
            market_returns = returns_df.get('market_return', 0)
            labels = (stock_returns > market_returns).astype(int)
        else:
            labels = (stock_returns > float(threshold)).astype(int)
        
        logger.info(f"Created {horizon} labels: {labels.sum()} positive ({labels.mean()*100:.1f}%)")
        
        return labels
    
    def train_test_split_time_series(self, X: np.ndarray, y: np.ndarray,
                                     metadata: pd.DataFrame, test_size: float = 0.2) -> Tuple:
        """
        Time-series aware train/test split.
        
        Args:
            X: Feature matrix
            y: Labels
            metadata: Metadata DataFrame with dates
            test_size: Proportion for test set
        
        Returns:
            Tuple of (X_train, X_test, y_train, y_test, train_dates, test_dates)
        """
        n_samples = len(X)
        split_idx = int(n_samples * (1 - test_size))
        
        X_train = X[:split_idx]
        X_test = X[split_idx:]
        y_train = y[:split_idx]
        y_test = y[split_idx:]
        
        train_dates = metadata.iloc[:split_idx]['date'].values
        test_dates = metadata.iloc[split_idx:]['date'].values
        
        logger.info(f"Split: {len(X_train)} training, {len(X_test)} test samples")
        logger.info(f"Train period: {train_dates[0]} to {train_dates[-1]}")
        logger.info(f"Test period: {test_dates[0]} to {test_dates[-1]}")
        
        return X_train, X_test, y_train, y_test, train_dates, test_dates
    
    def train_xgboost_model(self, X_train: np.ndarray, y_train: np.ndarray,
                           task: str = 'classification', X_test: np.ndarray = None,
                           y_test: np.ndarray = None) -> XGBClassifier:
        """
        Train XGBoost model.
        
        Args:
            X_train: Training features
            y_train: Training labels
            task: 'classification' or 'regression'
            X_test: Optional test set for early stopping
            y_test: Optional test labels
        
        Returns:
            Trained XGBoost model
        """
        logger.info(f"Training XGBoost {task} model")
        
        if task == 'classification':
            model = XGBClassifier(
                n_estimators=300,
                max_depth=6,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                scale_pos_weight=1.5,
                objective='binary:logistic',
                eval_metric='auc',
                random_state=42,
                early_stopping_rounds=20,
                verbose=False
            )
        else:
            model = XGBRegressor(
                n_estimators=300,
                max_depth=6,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                objective='reg:squarederror',
                eval_metric='rmse',
                random_state=42,
                verbose=False
            )
        
        # Fit with early stopping
        if X_test is not None and y_test is not None:
            model.fit(
                X_train, y_train,
                eval_set=[(X_test, y_test)],
                verbose=False
            )
        else:
            model.fit(X_train, y_train, verbose=False)
        
        logger.info(f"XGBoost model trained: {model.best_iteration if hasattr(model, 'best_iteration') else 'N/A'} iterations")
        
        return model
    
    def train_ensemble_model(self, X_train: np.ndarray, y_train: np.ndarray,
                            X_test: np.ndarray = None, y_test: np.ndarray = None) -> VotingClassifier:
        """
        Train ensemble model (XGBoost + Random Forest).
        
        Args:
            X_train: Training features
            y_train: Training labels
            X_test: Optional test set
            y_test: Optional test labels
        
        Returns:
            Trained ensemble model
        """
        logger.info("Training ensemble model")
        
        # XGBoost
        xgb_model = self.train_xgboost_model(X_train, y_train, 'classification', X_test, y_test)
        
        # Random Forest
        rf_model = RandomForestClassifier(
            n_estimators=200,
            max_depth=10,
            min_samples_split=10,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1
        )
        rf_model.fit(X_train, y_train)
        
        # Ensemble - just return dict of models instead of VotingClassifier
        # VotingClassifier requires both models to have fit() called, which we already did
        
        logger.info("Ensemble model trained (components trained separately)")
        
        # Return the XGBoost model as the primary model
        # Ensemble logic would be applied at prediction time
        self.models['xgb'] = xgb_model
        self.models['rf'] = rf_model
        
        return xgb_model  # Return primary model
    
    def evaluate_classification_model(self, model, X_test: np.ndarray, y_test: np.ndarray,
                                     test_dates: np.ndarray) -> Dict:
        """
        Evaluate classification model with comprehensive metrics.
        
        Args:
            model: Trained model
            X_test: Test features
            y_test: Test labels
            test_dates: Test dates for analysis
        
        Returns:
            Dictionary with evaluation metrics
        """
        logger.info("Evaluating model")
        
        # Predictions
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1] if hasattr(model, 'predict_proba') else y_pred
        
        # Basic metrics
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, zero_division=0)
        recall = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        
        # ROC AUC
        try:
            roc_auc = roc_auc_score(y_test, y_pred_proba)
        except:
            roc_auc = 0.0
        
        # Precision@10 (top 10 predictions)
        top_10_idx = np.argsort(y_pred_proba)[-10:]
        precision_at_10 = precision_score(y_test[top_10_idx], y_pred[top_10_idx], zero_division=0)
        
        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        
        results = {
            'accuracy': float(accuracy),
            'precision': float(precision),
            'recall': float(recall),
            'f1': float(f1),
            'roc_auc': float(roc_auc),
            'precision_at_10': float(precision_at_10),
            'confusion_matrix': cm.tolist(),
            'test_samples': len(y_test),
            'positive_predictions': int(y_pred.sum()),
            'actual_positives': int(y_test.sum())
        }
        
        logger.info(f"Model evaluation complete:")
        logger.info(f"  Accuracy: {accuracy:.3f}")
        logger.info(f"  Precision: {precision:.3f}")
        logger.info(f"  Precision@10: {precision_at_10:.3f}")
        
        return results
    
    def analyze_feature_importance(self, model, feature_names: List[str]) -> Dict:
        """
        Analyze feature importance.
        
        Args:
            model: Trained model
            feature_names: List of feature names
        
        Returns:
            Dictionary with feature importance scores
        """
        try:
            # Get feature importance
            if hasattr(model, 'feature_importances_'):
                importances = model.feature_importances_
            elif hasattr(model, 'named_steps'):
                # Ensemble - average importance
                importances = np.mean([est.feature_importances_ for est in model.estimators_], axis=0)
            else:
                logger.warning("Could not extract feature importance")
                return {}
            
            # Create importance dict
            importance_dict = dict(zip(feature_names, importances))
            
            # Sort by importance
            sorted_importance = sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)
            
            # Group by category
            categories = {'technical': [], 'fundamental': [], 'sentiment': [], 'other': []}
            
            for name, importance in sorted_importance:
                if any(x in name for x in ['rsi', 'macd', 'trend', 'momentum', 'volume']):
                    categories['technical'].append((name, importance))
                elif any(x in name for x in ['pe_ratio', 'roe', 'growth', 'value', 'profitability']):
                    categories['fundamental'].append((name, importance))
                elif any(x in name for x in ['sentiment', 'attention', 'velocity']):
                    categories['sentiment'].append((name, importance))
                else:
                    categories['other'].append((name, importance))
            
            logger.info("Feature importance analysis complete")
            
            return {
                'all_features': sorted_importance,
                'by_category': categories,
                'top_10': sorted_importance[:10]
            }
            
        except Exception as e:
            logger.error(f"Error analyzing feature importance: {e}")
            return {}
    
    def save_model(self, model, feature_names: List[str], metadata: Dict,
                  filepath: str):
        """
        Save model with all associated data.
        
        Args:
            model: Trained model
            feature_names: Feature names
            metadata: Model metadata
            filepath: Save path
        """
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        # Save model
        joblib.dump(model, filepath)
        
        # Save metadata
        metadata_path = filepath.replace('.pkl', '_metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump({
                'feature_names': feature_names,
                'metadata': metadata,
                'version': self.version,
                'save_date': datetime.now().isoformat()
            }, f, indent=2)
        
        logger.info(f"Model saved to {filepath}")
    
    def load_model(self, filepath: str):
        """
        Load model and metadata.
        
        Args:
            filepath: Model file path
        
        Returns:
            Tuple of (model, metadata_dict)
        """
        # Load model
        model = joblib.load(filepath)
        
        # Load metadata
        metadata_path = filepath.replace('.pkl', '_metadata.json')
        try:
            with open(metadata_path, 'r') as f:
                data = json.load(f)
            metadata = data
        except FileNotFoundError:
            metadata = {}
        
        logger.info(f"Model loaded from {filepath}")
        
        return model, metadata
    
    def explain_prediction(self, model, stock_features: np.ndarray,
                          feature_names: List[str]) -> List[Tuple[str, float]]:
        """
        Explain individual prediction using SHAP values.
        
        Args:
            model: Trained model
            stock_features: Feature vector for one stock
            feature_names: Feature names
        
        Returns:
            List of (feature_name, contribution) tuples
        
        Example:
            >>> explanation = model.explain_prediction(model, features, names)
            >>> print(f"Top contributor: {explanation[0]}")
        """
        try:
            import shap
            
            # Create explainer
            explainer = shap.TreeExplainer(model)
            
            # Calculate SHAP values
            shap_values = explainer.shap_values(stock_features.reshape(1, -1))
            
            # Format as list of (name, value) tuples
            contributions = list(zip(feature_names, shap_values[0]))
            
            # Sort by absolute value
            contributions.sort(key=lambda x: abs(x[1]), reverse=True)
            
            return contributions[:10]  # Top 10
            
        except ImportError:
            logger.warning("SHAP not installed. Using feature importance instead.")
            # Fallback to feature importance
            importances = model.feature_importances_
            contributions = list(zip(feature_names, importances))
            contributions.sort(key=lambda x: abs(x[1]), reverse=True)
            return contributions[:10]

