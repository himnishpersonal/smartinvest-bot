"""
Fundamental analysis calculator for stock evaluation.
Analyzes valuation, profitability, financial health, growth, and quality metrics.
"""

import logging
import numpy as np
from typing import Dict, Optional, List, Tuple

logger = logging.getLogger(__name__)


class FundamentalAnalyzer:
    """
    Analyze fundamental metrics to evaluate stock quality and value.
    Supports valuation, profitability, health, growth, and quality analysis.
    """
    
    def __init__(self):
        """Initialize FundamentalAnalyzer."""
        pass
    
    def analyze_valuation(self, fundamentals: Dict, sector_avg: Dict = None) -> Dict:
        """
        Analyze valuation metrics.
        
        Args:
            fundamentals: Stock fundamental data dict
            sector_avg: Sector average metrics (optional)
        
        Returns:
            Dictionary with valuation analysis and score
        
        Example:
            >>> analyzer = FundamentalAnalyzer()
            >>> valuation = analyzer.analyze_valuation(stock_fundamentals)
        """
        value_score = 50  # Start neutral
        signals = []
        
        pe_ratio = fundamentals.get('pe_ratio')
        pb_ratio = fundamentals.get('pb_ratio')
        ps_ratio = fundamentals.get('ps_ratio')
        peg_ratio = fundamentals.get('peg_ratio')
        
        # P/E Analysis
        if pe_ratio is not None and pe_ratio > 0:
            # Compare to sector average
            if sector_avg and sector_avg.get('pe_ratio'):
                sector_pe = sector_avg['pe_ratio']
                if pe_ratio < sector_pe * 0.8:
                    value_score += 20
                    signals.append(f"Undervalued: P/E {pe_ratio:.1f} vs sector {sector_pe:.1f}")
                elif pe_ratio > sector_pe * 1.2:
                    value_score -= 15
                    signals.append(f"Overvalued: P/E {pe_ratio:.1f} vs sector {sector_pe:.1f}")
                else:
                    signals.append(f"Fair value: P/E {pe_ratio:.1f} vs sector {sector_pe:.1f}")
            else:
                # Absolute analysis
                if pe_ratio < 15:
                    value_score += 15
                    signals.append(f"Low P/E: {pe_ratio:.1f} (potential value)")
                elif pe_ratio > 40:
                    value_score -= 20
                    signals.append(f"High P/E: {pe_ratio:.1f} (expensive)")
                else:
                    signals.append(f"Moderate P/E: {pe_ratio:.1f}")
        
        # P/B Analysis
        if pb_ratio is not None and pb_ratio > 0:
            if sector_avg and sector_avg.get('pb_ratio'):
                sector_pb = sector_avg['pb_ratio']
                if pb_ratio < sector_pb * 0.8:
                    value_score += 15
                    signals.append(f"Low P/B: {pb_ratio:.1f} vs sector {sector_pb:.1f}")
                elif pb_ratio > sector_pb * 1.5:
                    value_score -= 10
                    signals.append(f"High P/B: {pb_ratio:.1f} vs sector {sector_pb:.1f}")
        else:
            # Absolute analysis
            if pb_ratio and pb_ratio < 2:
                value_score += 10
                signals.append(f"Reasonable P/B: {pb_ratio:.1f}")
        
        # P/S Analysis
        if ps_ratio is not None and ps_ratio > 0:
            if sector_avg and sector_avg.get('ps_ratio'):
                sector_ps = sector_avg['ps_ratio']
                if ps_ratio < sector_ps * 0.8:
                    value_score += 10
                    signals.append(f"Low P/S: {ps_ratio:.1f} vs sector {sector_ps:.1f}")
            else:
                if ps_ratio < 3:
                    value_score += 8
        
        # PEG Ratio Analysis (Goldilocks zone)
        if peg_ratio is not None:
            if 0.5 < peg_ratio < 1.5:
                value_score += 15
                signals.append(f"Ideal PEG: {peg_ratio:.2f} (good growth/price balance)")
            elif peg_ratio < 0.5:
                value_score -= 10
                signals.append(f"Very low PEG: {peg_ratio:.2f} (potential value or declining growth)")
            elif peg_ratio > 2:
                value_score -= 15
                signals.append(f"High PEG: {peg_ratio:.2f} (expensive relative to growth)")
        
        return {
            'value_score': max(0, min(100, value_score)),
            'pe_ratio': pe_ratio,
            'pb_ratio': pb_ratio,
            'ps_ratio': ps_ratio,
            'peg_ratio': peg_ratio,
            'value_signals': signals
        }
    
    def analyze_profitability(self, fundamentals: Dict, sector_avg: Dict = None) -> Dict:
        """
        Analyze profitability metrics.
        
        Args:
            fundamentals: Stock fundamental data dict
            sector_avg: Sector average metrics (optional)
        
        Returns:
            Dictionary with profitability analysis and score
        """
        profitability_score = 50
        signals = []
        
        roe = fundamentals.get('roe')  # Return on Equity
        roa = fundamentals.get('roa')  # Return on Assets
        profit_margin = fundamentals.get('profit_margin')
        operating_margin = fundamentals.get('operating_margin')
        
        # ROE Analysis
        if roe is not None:
            roe_pct = roe * 100 if roe <= 1 else roe  # Handle decimal vs percentage
            if roe_pct > 15:
                profitability_score += 25
                signals.append(f"Excellent ROE: {roe_pct:.1f}%")
            elif roe_pct > 10:
                profitability_score += 15
                signals.append(f"Good ROE: {roe_pct:.1f}%")
            elif roe_pct > 5:
                profitability_score += 5
                signals.append(f"Moderate ROE: {roe_pct:.1f}%")
            else:
                profitability_score -= 10
                signals.append(f"Low ROE: {roe_pct:.1f}%")
            
            # Compare to sector
            if sector_avg and sector_avg.get('roe'):
                sector_roe = sector_avg['roe'] * 100 if sector_avg['roe'] <= 1 else sector_avg['roe']
                if roe_pct > sector_roe * 1.2:
                    profitability_score += 10
                elif roe_pct < sector_roe * 0.8:
                    profitability_score -= 10
        
        # ROA Analysis
        if roa is not None:
            roa_pct = roa * 100 if roa <= 1 else roa
            if roa_pct > 10:
                profitability_score += 15
                signals.append(f"Strong ROA: {roa_pct:.1f}%")
            elif roa_pct > 5:
                profitability_score += 8
            elif roa_pct < 2:
                profitability_score -= 8
                signals.append(f"Weak ROA: {roa_pct:.1f}%")
        
        # Profit Margin Analysis
        if profit_margin is not None:
            margin_pct = profit_margin * 100 if profit_margin <= 1 else profit_margin
            if margin_pct > 20:
                profitability_score += 15
                signals.append(f"Excellent profit margin: {margin_pct:.1f}%")
            elif margin_pct > 10:
                profitability_score += 10
            elif margin_pct < 5:
                profitability_score -= 10
                signals.append(f"Low profit margin: {margin_pct:.1f}%")
        
        # Operating Margin Analysis
        if operating_margin is not None:
            op_margin_pct = operating_margin * 100 if operating_margin <= 1 else operating_margin
            if op_margin_pct > 15:
                profitability_score += 10
                signals.append(f"Strong operating margin: {op_margin_pct:.1f}%")
            elif op_margin_pct < 5:
                profitability_score -= 8
        
        return {
            'profitability_score': max(0, min(100, profitability_score)),
            'roe': roe,
            'roa': roa,
            'profit_margin': profit_margin,
            'operating_margin': operating_margin,
            'profitability_signals': signals
        }
    
    def analyze_financial_health(self, fundamentals: Dict) -> Dict:
        """
        Analyze financial health metrics.
        
        Args:
            fundamentals: Stock fundamental data dict
        
        Returns:
            Dictionary with health analysis and score
        """
        health_score = 50
        signals = []
        
        debt_to_equity = fundamentals.get('debt_to_equity')
        current_ratio = fundamentals.get('current_ratio')
        quick_ratio = fundamentals.get('quick_ratio')
        
        # Debt-to-Equity Analysis
        if debt_to_equity is not None:
            if debt_to_equity < 0.5:
                health_score += 25
                signals.append(f"Very healthy D/E: {debt_to_equity:.2f}")
            elif debt_to_equity < 1.0:
                health_score += 15
                signals.append(f"Healthy D/E: {debt_to_equity:.2f}")
            elif debt_to_equity < 2.0:
                health_score += 5
                signals.append(f"Moderate D/E: {debt_to_equity:.2f}")
            else:
                health_score -= 20
                signals.append(f"Risky D/E: {debt_to_equity:.2f} (high debt)")
        
        # Current Ratio Analysis
        if current_ratio is not None:
            if current_ratio > 2.0:
                health_score += 20
                signals.append(f"Very liquid: Current ratio {current_ratio:.2f}")
            elif current_ratio > 1.5:
                health_score += 10
                signals.append(f"Healthy liquidity: Current ratio {current_ratio:.2f}")
            elif current_ratio > 1.0:
                health_score += 5
                signals.append(f"Adequate liquidity: Current ratio {current_ratio:.2f}")
            else:
                health_score -= 15
                signals.append(f"Low liquidity concern: Current ratio {current_ratio:.2f}")
        
        # Quick Ratio Analysis
        if quick_ratio is not None:
            if quick_ratio > 1.0:
                health_score += 10
                signals.append(f"Strong quick ratio: {quick_ratio:.2f}")
            elif quick_ratio < 0.5:
                health_score -= 10
                signals.append(f"Weak quick ratio: {quick_ratio:.2f}")
        
        return {
            'health_score': max(0, min(100, health_score)),
            'debt_to_equity': debt_to_equity,
            'current_ratio': current_ratio,
            'quick_ratio': quick_ratio,
            'health_signals': signals
        }
    
    def analyze_growth(self, fundamentals: Dict, sector_avg: Dict = None) -> Dict:
        """
        Analyze growth metrics.
        
        Args:
            fundamentals: Stock fundamental data dict
            sector_avg: Sector average metrics (optional)
        
        Returns:
            Dictionary with growth analysis and score
        """
        growth_score = 50
        signals = []
        
        revenue_growth = fundamentals.get('revenue_growth')
        earnings_growth = fundamentals.get('earnings_growth')
        
        # Revenue Growth Analysis
        if revenue_growth is not None:
            growth_pct = revenue_growth * 100 if revenue_growth <= 1 else revenue_growth
            
            if growth_pct > 20:
                growth_score += 30
                signals.append(f"High growth: Revenue +{growth_pct:.1f}% YoY")
            elif growth_pct > 10:
                growth_score += 20
                signals.append(f"Good growth: Revenue +{growth_pct:.1f}% YoY")
            elif growth_pct > 5:
                growth_score += 10
                signals.append(f"Moderate growth: Revenue +{growth_pct:.1f}% YoY")
            elif growth_pct < 0:
                growth_score -= 20
                signals.append(f"Declining revenue: {growth_pct:.1f}%")
            else:
                signals.append(f"Slow growth: Revenue +{growth_pct:.1f}% YoY")
            
            # Compare to sector
            if sector_avg and sector_avg.get('revenue_growth'):
                sector_growth = sector_avg['revenue_growth'] * 100 if sector_avg['revenue_growth'] <= 1 else sector_avg['revenue_growth']
                if growth_pct > sector_growth * 1.5:
                    growth_score += 10
                elif growth_pct < sector_growth * 0.5:
                    growth_score -= 10
        
        # Earnings Growth Analysis
        if earnings_growth is not None:
            earnings_growth_pct = earnings_growth * 100 if earnings_growth <= 1 else earnings_growth
            
            if earnings_growth_pct > 20:
                growth_score += 20
                signals.append(f"Strong earnings growth: +{earnings_growth_pct:.1f}%")
            elif earnings_growth_pct > 10:
                growth_score += 15
                signals.append(f"Good earnings growth: +{earnings_growth_pct:.1f}%")
            elif earnings_growth_pct < 0:
                growth_score -= 15
                signals.append(f"Declining earnings: {earnings_growth_pct:.1f}%")
            else:
                signals.append(f"Moderate earnings growth: +{earnings_growth_pct:.1f}%")
        
        return {
            'growth_score': max(0, min(100, growth_score)),
            'revenue_growth': revenue_growth,
            'earnings_growth': earnings_growth,
            'growth_signals': signals
        }
    
    def calculate_piotroski_f_score(self, fundamentals: Dict) -> Dict:
        """
        Calculate Piotroski F-Score (0-9 points for quality).
        
        Args:
            fundamentals: Stock fundamental data dict (needs financials)
        
        Returns:
            Dictionary with Piotroski score and breakdown
        """
        # This is a simplified version - would need more detailed financial data for full implementation
        score = 0
        breakdown = {
            'profitability': 0,
            'leverage': 0,
            'efficiency': 0
        }
        
        roa = fundamentals.get('roa')
        roe = fundamentals.get('roe')
        profit_margin = fundamentals.get('profit_margin')
        debt_to_equity = fundamentals.get('debt_to_equity')
        current_ratio = fundamentals.get('current_ratio')
        
        # Profitability (4 points)
        if roa and roa > 0:
            breakdown['profitability'] += 1
            score += 1
        
        if roe and roe > 0:
            breakdown['profitability'] += 1
            score += 1
        
        if profit_margin and profit_margin > 0:
            breakdown['profitability'] += 1
            score += 1
        
        if profit_margin and profit_margin > 0.05:  # Positive margin
            breakdown['profitability'] += 1
            score += 1
        
        # Leverage/Liquidity (3 points)
        if debt_to_equity is not None and debt_to_equity < 1.0:
            breakdown['leverage'] += 1
            score += 1
        
        if current_ratio and current_ratio > 1.0:
            breakdown['leverage'] += 1
            score += 1
        
        if current_ratio and current_ratio > 1.5:
            breakdown['leverage'] += 1
            score += 1
        
        # Operating Efficiency (2 points)
        roa_val = roa if roa else 0
        if roa_val > 0.05:  # 5% ROA
            breakdown['efficiency'] += 1
            score += 1
        
        if roa_val > 0.10:  # 10% ROA
            breakdown['efficiency'] += 1
            score += 1
        
        # Interpretation
        if score >= 8:
            quality = "Excellent"
        elif score >= 6:
            quality = "Good"
        elif score >= 4:
            quality = "Moderate"
        else:
            quality = "Poor"
        
        return {
            'piotroski_score': score,
            'quality': quality,
            'breakdown': breakdown,
            'max_score': 9
        }
    
    def calculate_altman_z_score(self, fundamentals: Dict) -> Dict:
        """
        Calculate Altman Z-Score for bankruptcy risk.
        
        Args:
            fundamentals: Stock fundamental data dict
        
        Returns:
            Dictionary with Z-score and risk category
        """
        # Simplified version - full calculation needs more balance sheet data
        # Z = 1.2*Working Capital/Total Assets + 1.4*Retained Earnings/Total Assets + 
        #     3.3*EBIT/Total Assets + 0.6*Market Cap/Total Liabilities + Sales/Total Assets
        
        # Using available metrics for approximation
        roa = fundamentals.get('roa', 0)
        current_ratio = fundamentals.get('current_ratio', 1.0)
        profit_margin = fundamentals.get('profit_margin', 0)
        
        # Simplified Z-score approximation
        z_score = 1.5 + (roa * 50) + (current_ratio * 0.5) + (profit_margin * 3)
        
        # Risk categorization
        if z_score > 3.0:
            risk = "Safe"
        elif z_score > 2.7:
            risk = "Grey Zone"
        elif z_score > 1.8:
            risk = "Stressed"
        else:
            risk = "Distress Zone"
        
        return {
            'z_score': float(z_score),
            'risk': risk
        }
    
    def calculate_all_fundamentals(self, fundamentals: Dict, sector_avg: Dict = None) -> Dict:
        """
        Calculate comprehensive fundamental analysis.
        
        Args:
            fundamentals: Stock fundamental data dict
            sector_avg: Sector average metrics (optional)
        
        Returns:
            Comprehensive dictionary with all fundamental analysis
        
        Example:
            >>> analyzer = FundamentalAnalyzer()
            >>> analysis = analyzer.calculate_all_fundamentals(stock_fundamentals)
            >>> print(f"Fundamental Score: {analysis['fundamental_score']}")
        """
        logger.info("Calculating fundamental analysis")
        
        # Run all analyses
        valuation = self.analyze_valuation(fundamentals, sector_avg)
        profitability = self.analyze_profitability(fundamentals, sector_avg)
        health = self.analyze_financial_health(fundamentals)
        growth = self.analyze_growth(fundamentals, sector_avg)
        piotroski = self.calculate_piotroski_f_score(fundamentals)
        altman = self.calculate_altman_z_score(fundamentals)
        
        # Calculate composite fundamental score (weighted)
        fundamental_score = (
            valuation['value_score'] * 0.25 +
            profitability['profitability_score'] * 0.25 +
            growth['growth_score'] * 0.25 +
            health['health_score'] * 0.15 +
            (piotroski['piotroski_score'] / 9 * 100) * 0.10
        )
        
        # Compile all signals
        all_signals = []
        all_signals.extend(valuation.get('value_signals', []))
        all_signals.extend(profitability.get('profitability_signals', []))
        all_signals.extend(health.get('health_signals', []))
        all_signals.extend(growth.get('growth_signals', []))
        
        # Filter to most important (limit to 8)
        key_signals = all_signals[:8]
        
        # Identify strengths and weaknesses
        strengths = []
        weaknesses = []
        
        if valuation['value_score'] > 70:
            strengths.append('value')
        elif valuation['value_score'] < 40:
            weaknesses.append('valuation')
        
        if profitability['profitability_score'] > 75:
            strengths.append('profitability')
        elif profitability['profitability_score'] < 40:
            weaknesses.append('profitability')
        
        if growth['growth_score'] > 70:
            strengths.append('growth')
        elif growth['growth_score'] < 30:
            weaknesses.append('growth')
        
        if health['health_score'] < 40:
            weaknesses.append('financial_health')
        
        # Calculate data completeness for confidence
        required_metrics = ['pe_ratio', 'roe', 'profit_margin', 'debt_to_equity', 'revenue_growth']
        available_metrics = sum(1 for m in required_metrics if fundamentals.get(m) is not None)
        completeness = available_metrics / len(required_metrics)
        
        if completeness > 0.8:
            confidence = 'high'
        elif completeness > 0.6:
            confidence = 'medium'
        else:
            confidence = 'low'
        
        logger.info(f"Fundamental analysis complete: Score={fundamental_score:.1f}, Confidence={confidence}")
        
        return {
            'fundamental_score': round(float(fundamental_score), 1),
            'value_score': round(float(valuation['value_score']), 1),
            'profitability_score': round(float(profitability['profitability_score']), 1),
            'health_score': round(float(health['health_score']), 1),
            'growth_score': round(float(growth['growth_score']), 1),
            'quality_score': round(float((piotroski['piotroski_score'] / 9 * 100)), 1),
            'piotroski_score': piotroski['piotroski_score'],
            'altman_z_score': altman['z_score'],
            'altman_risk': altman['risk'],
            'signals': key_signals,
            'strengths': strengths,
            'weaknesses': weaknesses,
            'confidence': confidence,
            'raw_metrics': {
                'valuation': valuation,
                'profitability': profitability,
                'health': health,
                'growth': growth,
                'piotroski': piotroski,
                'altman': altman
            }
        }

