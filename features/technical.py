"""
Technical indicator calculator for stock analysis.
Implements trend, momentum, volatility, and volume indicators.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Tuple, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TechnicalFeatures:
    """
    Calculate technical analysis indicators from OHLCV price data.
    Supports trend, momentum, volatility, and volume indicators.
    """
    
    def __init__(self):
        """Initialize TechnicalFeatures calculator."""
        self.min_bars_required = 250  # Need ~1 year for 200-day MA
        
    def calculate_moving_averages(self, df: pd.DataFrame) -> Dict:
        """
        Calculate moving averages and trend signals.
        
        Args:
            df: DataFrame with OHLCV columns
        
        Returns:
            Dictionary with MA values and signals
        
        Example:
            >>> features = TechnicalFeatures()
            >>> df = load_price_data('AAPL')
            >>> ma_signals = features.calculate_moving_averages(df)
        """
        df = df.copy()
        
        # Calculate MAs
        df['SMA_20'] = df['close'].rolling(window=20).mean()
        df['SMA_50'] = df['close'].rolling(window=50).mean()
        df['SMA_200'] = df['close'].rolling(window=200).mean()
        
        df['EMA_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['EMA_26'] = df['close'].ewm(span=26, adjust=False).mean()
        
        # Get latest values
        current_price = df['close'].iloc[-1]
        sma_20 = df['SMA_20'].iloc[-1]
        sma_50 = df['SMA_50'].iloc[-1]
        sma_200 = df['SMA_200'].iloc[-1]
        ema_12 = df['EMA_12'].iloc[-1]
        ema_26 = df['EMA_26'].iloc[-1]
        
        # Price relative to MAs (% above/below)
        price_vs_ma = {
            'price_vs_sma_20': ((current_price / sma_20 - 1) * 100) if not pd.isna(sma_20) else 0,
            'price_vs_sma_50': ((current_price / sma_50 - 1) * 100) if not pd.isna(sma_50) else 0,
            'price_vs_sma_200': ((current_price / sma_200 - 1) * 100) if not pd.isna(sma_200) else 0,
        }
        
        # Cross signals
        signals = []
        
        # Golden/Death Cross (50 vs 200)
        golden_cross = not pd.isna(sma_50) and not pd.isna(sma_200) and sma_50 > sma_200
        death_cross = not pd.isna(sma_50) and not pd.isna(sma_200) and sma_50 < sma_200
        
        if golden_cross:
            signals.append("Golden Cross: 50-day MA above 200-day MA (Bullish)")
        elif death_cross:
            signals.append("Death Cross: 50-day MA below 200-day MA (Bearish)")
        
        # Price above/below key MAs
        if not pd.isna(sma_200):
            if current_price > sma_200:
                signals.append("Price above 200-day MA (Long-term uptrend)")
            else:
                signals.append("Price below 200-day MA (Long-term downtrend)")
        
        # EMA cross
        if not pd.isna(ema_12) and not pd.isna(ema_26):
            if ema_12 > ema_26:
                signals.append("12 EMA above 26 EMA (Short-term uptrend)")
            else:
                signals.append("12 EMA below 26 EMA (Short-term downtrend)")
        
        return {
            'sma_20': sma_20,
            'sma_50': sma_50,
            'sma_200': sma_200,
            'ema_12': ema_12,
            'ema_26': ema_26,
            'price_vs_ma': price_vs_ma,
            'golden_cross': golden_cross,
            'death_cross': death_cross,
            'signals': signals
        }
    
    def calculate_macd(self, df: pd.DataFrame) -> Dict:
        """
        Calculate MACD (Moving Average Convergence Divergence).
        
        Args:
            df: DataFrame with OHLCV columns
        
        Returns:
            Dictionary with MACD values and signals
        """
        df = df.copy()
        
        # Calculate EMAs
        ema_12 = df['close'].ewm(span=12, adjust=False).mean()
        ema_26 = df['close'].ewm(span=26, adjust=False).mean()
        
        # MACD line
        df['macd'] = ema_12 - ema_26
        
        # Signal line (9 EMA of MACD)
        df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        
        # Histogram
        df['histogram'] = df['macd'] - df['signal']
        
        # Get latest values
        macd_current = df['macd'].iloc[-1]
        signal_current = df['signal'].iloc[-1]
        histogram_current = df['histogram'].iloc[-1]
        
        # Crossover signals
        signals = []
        
        # Bullish cross
        if len(df) >= 2:
            macd_prev = df['macd'].iloc[-2]
            signal_prev = df['signal'].iloc[-2]
            
            # Bullish crossover
            if macd_prev <= signal_prev and macd_current > signal_current:
                signals.append("Bullish MACD crossover detected")
            
            # Bearish crossover
            elif macd_prev >= signal_prev and macd_current < signal_current:
                signals.append("Bearish MACD crossover detected")
        
        # Histogram interpretation
        if histogram_current > 0:
            signals.append("MACD above signal line (Bullish)")
        else:
            signals.append("MACD below signal line (Bearish)")
        
        return {
            'macd': float(macd_current),
            'signal': float(signal_current),
            'histogram': float(histogram_current),
            'macd_signals': signals
        }
    
    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> Dict:
        """
        Calculate RSI (Relative Strength Index).
        
        Args:
            df: DataFrame with OHLCV columns
            period: RSI period (default 14)
        
        Returns:
            Dictionary with RSI value, level, and divergence
        """
        df = df.copy()
        
        # Calculate price changes
        delta = df['close'].diff()
        
        # Separate gains and losses
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # Calculate average gain/loss
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        rsi_current = df['rsi'].iloc[-1]
        
        # Interpret RSI
        level = 'neutral'
        if rsi_current > 70:
            level = 'overbought'
        elif rsi_current < 30:
            level = 'oversold'
        
        signals = [f"RSI: {rsi_current:.1f} ({level})"]
        
        # Detect divergence
        price_highs = df['close'].rolling(window=10).max()
        price_lows = df['close'].rolling(window=10).min()
        
        # Simple divergence check (last 20 periods)
        if len(df) >= 20:
            recent_price = df['close'].tail(20)
            recent_rsi = df['rsi'].tail(20)
            
            price_trend = recent_price.iloc[-1] - recent_price.iloc[0]
            rsi_trend = recent_rsi.iloc[-1] - recent_rsi.iloc[0]
            
            # Bearish divergence (price up, RSI down)
            if price_trend > 0 and rsi_trend < -5:
                signals.append("Bearish RSI divergence detected")
            # Bullish divergence (price down, RSI up)
            elif price_trend < 0 and rsi_trend > 5:
                signals.append("Bullish RSI divergence detected")
        
        return {
            'rsi': float(rsi_current),
            'level': level,
            'overbought': rsi_current > 70,
            'oversold': rsi_current < 30,
            'rsi_signals': signals
        }
    
    def calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20, 
                                   num_std: float = 2.0) -> Dict:
        """
        Calculate Bollinger Bands.
        
        Args:
            df: DataFrame with OHLCV columns
            period: Moving average period
            num_std: Number of standard deviations
        
        Returns:
            Dictionary with band values and signals
        """
        df = df.copy()
        
        # Middle band (SMA)
        df['bb_middle'] = df['close'].rolling(window=period).mean()
        
        # Standard deviation
        rolling_std = df['close'].rolling(window=period).std()
        
        # Upper and lower bands
        df['bb_upper'] = df['bb_middle'] + (rolling_std * num_std)
        df['bb_lower'] = df['bb_middle'] - (rolling_std * num_std)
        
        # Get latest values
        current_price = df['close'].iloc[-1]
        upper = df['bb_upper'].iloc[-1]
        middle = df['bb_middle'].iloc[-1]
        lower = df['bb_lower'].iloc[-1]
        
        # Bandwidth (volatility measure)
        bandwidth = (upper - lower) / middle * 100 if not pd.isna(middle) else 0
        
        # %B indicator (0 = at lower band, 1 = at upper band)
        percent_b = (current_price - lower) / (upper - lower) if not pd.isna(upper) and not pd.isna(lower) else 0.5
        
        # Squeeze detection (low volatility)
        avg_bandwidth = df['bb_middle'].rolling(window=20).apply(
            lambda x: (x.iloc[-1] - x.iloc[0]) / x.iloc[0] if len(x) > 1 else 0
        ).mean() if len(df) > 20 else bandwidth
        squeeze = bandwidth < avg_bandwidth * 0.7 if not pd.isna(avg_bandwidth) else False
        
        signals = []
        
        # Price position
        if not pd.isna(upper) and not pd.isna(lower):
            if current_price > upper:
                signals.append(f"Price above upper Bollinger Band (Overbought) - {percent_b*100:.1f}%B")
            elif current_price < lower:
                signals.append(f"Price below lower Bollinger Band (Oversold) - {percent_b*100:.1f}%B")
            else:
                signals.append(f"Price within Bollinger Bands ({percent_b*100:.1f}%B)")
        
        # Squeeze signal
        if squeeze:
            signals.append("Bollinger Band Squeeze (Low volatility - potential breakout)")
        
        return {
            'bb_upper': float(upper) if not pd.isna(upper) else None,
            'bb_middle': float(middle) if not pd.isna(middle) else None,
            'bb_lower': float(lower) if not pd.isna(lower) else None,
            'bandwidth': float(bandwidth),
            'percent_b': float(percent_b),
            'squeeze': squeeze,
            'bb_signals': signals
        }
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> Dict:
        """
        Calculate Average True Range.
        
        Args:
            df: DataFrame with OHLCV columns
            period: ATR period
        
        Returns:
            Dictionary with ATR values and signals
        """
        df = df.copy()
        
        # True Range calculation
        high_low = df['high'] - df['low']
        high_close_prev = abs(df['high'] - df['close'].shift())
        low_close_prev = abs(df['low'] - df['close'].shift())
        
        df['tr'] = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
        
        # ATR
        df['atr'] = df['tr'].rolling(window=period).mean()
        
        # Get latest values
        atr_current = df['atr'].iloc[-1]
        current_price = df['close'].iloc[-1]
        
        # Normalized ATR
        normalized_atr = (atr_current / current_price * 100) if current_price > 0 else 0
        
        # Historical comparison
        avg_atr = df['atr'].tail(60).mean()
        high_volatility = atr_current > avg_atr * 1.2 if not pd.isna(avg_atr) else False
        low_volatility = atr_current < avg_atr * 0.8 if not pd.isna(avg_atr) else False
        
        signals = [f"ATR: {atr_current:.2f} ({normalized_atr:.2f}% of price)"]
        
        if high_volatility:
            signals.append("High volatility detected (ATR above average)")
        elif low_volatility:
            signals.append("Low volatility detected (ATR below average)")
        
        return {
            'atr': float(atr_current) if not pd.isna(atr_current) else None,
            'normalized_atr': float(normalized_atr),
            'high_volatility': high_volatility,
            'low_volatility': low_volatility,
            'atr_signals': signals
        }
    
    def calculate_obv(self, df: pd.DataFrame) -> Dict:
        """
        Calculate On-Balance Volume.
        
        Args:
            df: DataFrame with OHLCV columns
        
        Returns:
            Dictionary with OBV values and signals
        """
        df = df.copy()
        
        # OBV calculation
        df['price_change'] = df['close'].diff()
        df['obv'] = 0.0
        
        for i in range(1, len(df)):
            if df['price_change'].iloc[i] > 0:
                df.loc[df.index[i], 'obv'] = df['obv'].iloc[i-1] + df['volume'].iloc[i]
            elif df['price_change'].iloc[i] < 0:
                df.loc[df.index[i], 'obv'] = df['obv'].iloc[i-1] - df['volume'].iloc[i]
            else:
                df.loc[df.index[i], 'obv'] = df['obv'].iloc[i-1]
        
        obv_current = df['obv'].iloc[-1]
        
        # OBV trend (20-day slope)
        if len(df) >= 20:
            obv_trend = (df['obv'].iloc[-1] - df['obv'].iloc[-20]) / abs(df['obv'].iloc[-20]) * 100
        else:
            obv_trend = 0
        
        # Divergence check
        price_change = df['close'].iloc[-1] - df['close'].iloc[-20] if len(df) >= 20 else 0
        
        signals = []
        
        if obv_trend > 0:
            signals.append("OBV trending up (Buying pressure)")
        else:
            signals.append("OBV trending down (Selling pressure)")
        
        # Detect divergence
        if price_change > 0 and obv_trend < -10:
            signals.append("Bearish OBV divergence (Volume declining while price rising)")
        elif price_change < 0 and obv_trend > 10:
            signals.append("Bullish OBV divergence (Volume rising while price falling)")
        
        return {
            'obv': float(obv_current),
            'obv_trend': float(obv_trend),
            'obv_signals': signals
        }
    
    def calculate_volume_sma(self, df: pd.DataFrame, period: int = 20) -> Dict:
        """
        Calculate volume moving average and volume signals.
        
        Args:
            df: DataFrame with OHLCV columns
            period: SMA period
        
        Returns:
            Dictionary with volume signals
        """
        df = df.copy()
        
        # Volume SMA
        df['volume_sma'] = df['volume'].rolling(window=period).mean()
        
        # Get latest values
        current_volume = df['volume'].iloc[-1]
        avg_volume = df['volume_sma'].iloc[-1]
        
        # Volume vs average
        if avg_volume > 0:
            volume_ratio = current_volume / avg_volume
        else:
            volume_ratio = 1.0
        
        signals = []
        
        if volume_ratio > 2.0:
            signals.append(f"High volume spike detected ({volume_ratio:.1f}x average)")
        elif volume_ratio < 0.5:
            signals.append(f"Low volume ({volume_ratio:.1f}x average)")
        else:
            signals.append(f"Average volume ({volume_ratio:.1f}x)")
        
        return {
            'current_volume': float(current_volume),
            'avg_volume': float(avg_volume) if not pd.isna(avg_volume) else 0,
            'volume_ratio': float(volume_ratio),
            'volume_signals': signals
        }
    
    def calculate_historical_volatility(self, df: pd.DataFrame, period: int = 30) -> Dict:
        """
        Calculate historical volatility.
        
        Args:
            df: DataFrame with OHLCV columns
            period: Period for calculation
        
        Returns:
            Dictionary with volatility metrics
        """
        df = df.copy()
        
        # Calculate returns
        df['returns'] = df['close'].pct_change()
        
        # Standard deviation of returns
        df['volatility'] = df['returns'].rolling(window=period).std()
        
        # Annualized volatility
        df['volatility_annualized'] = df['volatility'] * np.sqrt(252)  # Trading days
        
        current_vol = df['volatility_annualized'].iloc[-1] * 100  # As percentage
        
        # Compare to 6-month average
        if len(df) >= 120:
            avg_vol = df['volatility_annualized'].tail(120).mean() * 100
        else:
            avg_vol = current_vol
        
        high_volatility = current_vol > avg_vol * 1.2
        
        return {
            'volatility': float(current_vol) if not pd.isna(current_vol) else 0,
            'avg_volatility': float(avg_vol),
            'high_volatility': high_volatility
        }
    
    def calculate_all_features(self, price_df: pd.DataFrame) -> Dict:
        """
        Calculate all technical features and generate composite scores.
        
        Args:
            price_df: DataFrame with OHLCV columns (date, open, high, low, close, volume)
        
        Returns:
            Comprehensive dictionary with all indicators, scores, and signals
        
        Example:
            >>> features = TechnicalFeatures()
            >>> results = features.calculate_all_features(price_data)
            >>> print(f"Technical Score: {results['technical_score']}")
        """
        logger.info("Calculating all technical features")
        
        # Validate data
        if len(price_df) < self.min_bars_required:
            logger.warning(f"Insufficient data: {len(price_df)} bars (need {self.min_bars_required})")
            return {
                'error': 'Insufficient data',
                'bars_available': len(price_df),
                'bars_required': self.min_bars_required
            }
        
        # Check required columns
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in price_df.columns for col in required_cols):
            logger.error(f"Missing required columns. Need: {required_cols}")
            return {'error': 'Missing required columns'}
        
        try:
            # Calculate all indicators
            ma_results = self.calculate_moving_averages(price_df)
            macd_results = self.calculate_macd(price_df)
            rsi_results = self.calculate_rsi(price_df)
            bb_results = self.calculate_bollinger_bands(price_df)
            atr_results = self.calculate_atr(price_df)
            obv_results = self.calculate_obv(price_df)
            volume_results = self.calculate_volume_sma(price_df)
            volatility_results = self.calculate_historical_volatility(price_df)
            
            # Score each category
            trend_score = self._score_trend(ma_results, macd_results)
            momentum_score = self._score_momentum(rsi_results, bb_results)
            volume_score = self._score_volume(obv_results, volume_results)
            
            # Composite technical score
            technical_score = (
                trend_score * 0.40 +
                momentum_score * 0.35 +
                volume_score * 0.25
            )
            
            # Compile all signals
            all_signals = []
            all_signals.extend(ma_results.get('signals', []))
            all_signals.extend(macd_results.get('macd_signals', []))
            all_signals.extend(rsi_results.get('rsi_signals', []))
            all_signals.extend(bb_results.get('bb_signals', []))
            all_signals.extend(obv_results.get('obv_signals', []))
            all_signals.extend(volume_results.get('volume_signals', []))
            
            # Filter to most important signals (limit to 8)
            key_signals = all_signals[:8]
            
            logger.info(f"Technical analysis complete: Score={technical_score:.1f}")
            
            return {
                'technical_score': round(float(technical_score), 1),
                'trend_score': round(float(trend_score), 1),
                'momentum_score': round(float(momentum_score), 1),
                'volume_score': round(float(volume_score), 1),
                'signals': key_signals,
                'raw_indicators': {
                    'ma': ma_results,
                    'macd': macd_results,
                    'rsi': rsi_results,
                    'bollinger': bb_results,
                    'atr': atr_results,
                    'obv': obv_results,
                    'volume': volume_results,
                    'volatility': volatility_results
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating technical features: {e}")
            return {'error': str(e)}
    
    def _score_trend(self, ma_results: Dict, macd_results: Dict) -> float:
        """Score trend indicators (0-100)."""
        score = 50  # Start neutral
        signals = ma_results.get('signals', [])
        macd_signals = macd_results.get('macd_signals', [])
        
        # Moving average signals
        for signal in signals:
            if 'Golden Cross' in signal or 'uptrend' in signal.lower():
                score += 10
            elif 'Death Cross' in signal or 'downtrend' in signal.lower():
                score -= 10
        
        # MACD signals
        for signal in macd_signals:
            if 'Bullish' in signal:
                score += 8
            elif 'Bearish' in signal:
                score -= 8
        
        # Price position
        price_vs_ma = ma_results.get('price_vs_ma', {})
        if price_vs_ma.get('price_vs_sma_200', 0) > 0:
            score += 15
        elif price_vs_ma.get('price_vs_sma_200', 0) < -5:
            score -= 15
        
        return max(0, min(100, score))
    
    def _score_momentum(self, rsi_results: Dict, bb_results: Dict) -> float:
        """Score momentum indicators (0-100)."""
        score = 50
        rsi = rsi_results.get('rsi', 50)
        
        # RSI scoring (neutral zone is best)
        if 30 < rsi < 70:
            score += 15
        elif rsi > 70:
            score -= 10  # Overbought
        elif rsi < 30:
            score -= 5   # Oversold (but could be buy opportunity)
        
        # Add points for momentum
        if rsi > 55 and rsi < 65:
            score += 10  # Strong but not overbought
        elif rsi < 45 and rsi > 35:
            score += 5   # Oversold recovery
        
        # Bollinger bands
        percent_b = bb_results.get('percent_b', 0.5)
        if 0.2 < percent_b < 0.8:
            score += 5  # In healthy range
        elif percent_b > 0.9:
            score -= 8  # Overbought
        elif percent_b < 0.1:
            score -= 5  # Oversold
        
        return max(0, min(100, score))
    
    def _score_volume(self, obv_results: Dict, volume_results: Dict) -> float:
        """Score volume indicators (0-100)."""
        score = 50
        
        # OBV trend
        obv_trend = obv_results.get('obv_trend', 0)
        if obv_trend > 5:
            score += 15  # Strong buying pressure
        elif obv_trend < -5:
            score -= 10  # Selling pressure
        
        # Volume ratio
        volume_ratio = volume_results.get('volume_ratio', 1.0)
        if volume_ratio > 1.5:
            score += 10  # High interest
        elif volume_ratio < 0.7:
            score -= 5   # Low interest
        
        return max(0, min(100, score))

