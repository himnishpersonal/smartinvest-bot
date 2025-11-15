"""
SmartInvest Discord Bot - WITH REAL DATA INTEGRATION
AI-powered stock recommendation bot using REAL market data
"""

import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
from datetime import datetime, timedelta, time, date
import pytz
import logging
import os
import traceback
import numpy as np
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import all components
from config import Config
from data.storage import DatabaseManager
from data.schema import Stock, ExitSignal
from data.collectors import StockDataCollector, NewsCollector, SentimentAnalyzer
from data.pipeline import DataPipeline
from features.technical import TechnicalFeatures
from features.fundamental import FundamentalAnalyzer
from features.sentiment import SentimentFeatureEngine
from models.feature_pipeline import FeaturePipeline
from models.scoring import RecommendationEngine
from models.dip_scanner import DipScanner


class SmartInvestBot(commands.Bot):
    """
    Main Discord bot for stock analysis and recommendations.
    USES REAL DATA from Yahoo Finance, NewsAPI, and ML models.
    """
    
    def __init__(self):
        """Initialize SmartInvestBot with all real data components."""
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            description='AI-powered stock recommendation bot',
            help_command=None
        )
        
        # Add on_ready event
        self.setup_hook_called = False
        
        # Initialize configuration
        self.config = Config()
        
        # Initialize database
        self.db_manager = DatabaseManager(self.config.DATABASE_URL)
        
        # Initialize data collectors with FMP + Finnhub hybrid
        self.stock_collector = StockDataCollector(
            fmp_api_key=self.config.FMP_API_KEY,
            finnhub_api_key=self.config.FINNHUB_API_KEY
        )
        self.news_collector = NewsCollector(self.config.NEWS_API_KEY) if self.config.NEWS_API_KEY else None
        self.sentiment_analyzer = SentimentAnalyzer() if self.news_collector else None
        
        # Initialize feature calculators
        self.technical_features = TechnicalFeatures()
        self.fundamental_analyzer = FundamentalAnalyzer()
        self.sentiment_engine = SentimentFeatureEngine() if self.sentiment_analyzer else None
        
        # Initialize feature pipeline
        self.feature_pipeline = FeaturePipeline(
            self.technical_features,
            self.fundamental_analyzer,
            self.sentiment_engine
        )
        
        # Initialize recommendation engine
        # Try to load ML model
        self.ml_model = None
        self.has_ml_model = False
        
        try:
            import joblib
            import os
            model_path = 'models/saved_models/model_latest.pkl'
            if os.path.exists(model_path):
                self.ml_model = joblib.load(model_path)
                self.has_ml_model = True
                logger.info("ML model loaded successfully")
            else:
                logger.warning("No ML model found - will use rule-based scoring")
        except Exception as e:
            logger.warning(f"Could not load ML model: {e} - will use rule-based scoring")
        
        # Initialize recommendation engine (with or without ML model)
        if self.has_ml_model:
            self.recommendation_engine = RecommendationEngine(
                ml_model=self.ml_model,
                feature_pipeline=self.feature_pipeline,
                db_manager=self.db_manager
            )
        else:
            self.recommendation_engine = None
        
        # Initialize dip scanner
        self.dip_scanner = DipScanner(
            db_manager=self.db_manager,
            min_dip_score=60  # Higher threshold with yfinance fundamentals
        )
        
        # Bot state
        self.last_update = None
        self.current_recommendations = []
        self.analysis_in_progress = False
        
        logger.info("SmartInvestBot initialized with REAL data components")
    
    async def setup_hook(self):
        """Called when bot is starting up - sync commands globally."""
        logger.info("🔄 Syncing commands globally...")
        try:
            # Sync commands (don't clear, just update)
            synced = await self.tree.sync()
            logger.info(f"✅ Synced {len(synced)} commands globally")
            logger.info(f"📋 Commands: {', '.join([cmd.name for cmd in synced])}")
        except Exception as e:
            logger.error(f"❌ Failed to sync commands: {e}")
        
        print(f"\n{'='*60}")
        print("🤖 SmartInvest Bot Ready (REAL DATA MODE)!")
        print(f"{'='*60}")
        print(f"Bot Name: {self.user}")
        print(f"ML Model: {'✅ Loaded' if self.has_ml_model else '⚠️  Not found (using rules)'}")
        print(f"News API: {'✅ Configured' if self.news_collector else '⚠️  Not configured'}")
        print(f"Synced Commands: {len(self.tree.get_commands())}")
        print(f"{'='*60}\n")
    
    async def on_ready(self):
        """Called when bot successfully connects."""
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f'Bot is in {len(self.guilds)} guild(s)')
        
        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="real market data 📈"
            )
        )
        
        # Start scheduled tasks
        if not self.daily_analysis.is_running():
            self.daily_analysis.start()
    
    def _calculate_backtest_features(self, price_df: pd.DataFrame, articles: list) -> dict:
        """
        Calculate features for backtesting - MUST MATCH score_stock_simple() exactly!
        
        Args:
            price_df: DataFrame with OHLCV data
            articles: List of NewsArticle objects
            
        Returns:
            Dictionary with 8 features (matching production)
        """
        try:
            if len(price_df) < 30:
                return None
            
            closes = price_df['close'].values
            volumes = price_df['volume'].values
            
            # EXACT SAME FEATURES AS score_stock_simple()
            # Feature 1-3: Returns
            return_5d = (closes[-1] - closes[-6]) / closes[-6] if len(closes) >= 6 else 0
            return_10d = (closes[-1] - closes[-11]) / closes[-11] if len(closes) >= 11 else 0
            return_20d = (closes[-1] - closes[-21]) / closes[-21] if len(closes) >= 21 else 0
            
            # Feature 4: Momentum (direction count)
            momentum = sum([1 if closes[i] > closes[i-1] else -1 for i in range(1, len(closes))]) / len(closes)
            
            # Feature 5: Volume trend
            avg_volume = sum(volumes) / len(volumes)
            volume_trend = (volumes[-1] - avg_volume) / avg_volume if avg_volume > 0 else 0
            
            # Features 6-8: Sentiment
            if articles:
                sentiment_scores = [a.sentiment_score for a in articles if a.sentiment_score is not None]
                if sentiment_scores:
                    avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
                    sentiment_positive = sum(1 for s in sentiment_scores if s > 0.3) / len(sentiment_scores)
                    sentiment_negative = sum(1 for s in sentiment_scores if s < -0.3) / len(sentiment_scores)
                else:
                    avg_sentiment = 0
                    sentiment_positive = 0
                    sentiment_negative = 0
            else:
                avg_sentiment = 0
                sentiment_positive = 0
                sentiment_negative = 0
            
            # Return features in EXACT ORDER as production
            return {
                'return_5d': return_5d,
                'return_10d': return_10d,
                'return_20d': return_20d,
                'momentum': momentum,
                'volume_trend': volume_trend,
                'avg_sentiment': avg_sentiment,
                'sentiment_positive': sentiment_positive,
                'sentiment_negative': sentiment_negative
            }
            
        except Exception as e:
            logger.error(f"Error calculating backtest features: {e}")
            return None
    
    def score_stock_simple(self, ticker: str) -> dict:
        """
        Score a stock using ML model + database data (NO API CALLS)
        Fast scoring using pre-loaded data
        """
        import pandas as pd
        import numpy as np
        from datetime import timedelta
        
        try:
            # Get stock from database
            stock = self.db_manager.get_stock_by_ticker(ticker)
            if not stock:
                raise ValueError(f"Stock {ticker} not in database. Run load_sp100.py first.")
            
            # Get price data from DATABASE (not API)
            with self.db_manager.get_session() as session:
                from data.schema import StockPrice, NewsArticle
                
                # Get prices from database
                end_date = datetime.now()
                start_date = end_date - timedelta(days=60)  # Last 60 days
                
                price_records = session.query(StockPrice).filter(
                    StockPrice.stock_id == stock.id,
                    StockPrice.date >= start_date
                ).order_by(StockPrice.date).all()
                
                if not price_records or len(price_records) < 30:
                    raise ValueError(f"Insufficient price data for {ticker} in database")
                
                # Convert to lists for feature calculation
                closes = [p.close for p in price_records]
                volumes = [p.volume for p in price_records]
                
                current_price = closes[-1]
                
                # Calculate simple features (same as training)
                return_5d = (closes[-1] - closes[-6]) / closes[-6] if len(closes) >= 6 else 0
                return_10d = (closes[-1] - closes[-11]) / closes[-11] if len(closes) >= 11 else 0
                return_20d = (closes[-1] - closes[-21]) / closes[-21] if len(closes) >= 21 else 0
                momentum = sum([1 if closes[i] > closes[i-1] else -1 for i in range(1, len(closes))]) / len(closes)
                
                avg_volume = sum(volumes) / len(volumes)
                volume_trend = (volumes[-1] - avg_volume) / avg_volume if avg_volume > 0 else 0
                
                # Get news sentiment from DATABASE
                news_articles = session.query(NewsArticle).filter_by(
                    stock_id=stock.id
                ).order_by(NewsArticle.published_at.desc()).limit(20).all()
                
                if news_articles:
                    sentiment_scores = [a.sentiment_score for a in news_articles if a.sentiment_score is not None]
                    avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
                    sentiment_positive = sum(1 for s in sentiment_scores if s > 0.3) / len(sentiment_scores) if sentiment_scores else 0
                    sentiment_negative = sum(1 for s in sentiment_scores if s < -0.3) / len(sentiment_scores) if sentiment_scores else 0
                else:
                    avg_sentiment = 0
                    sentiment_positive = 0
                    sentiment_negative = 0
                
                # Create feature vector (same as training)
                features = np.array([[
                    return_5d,
                    return_10d,
                    return_20d,
                    momentum,
                    volume_trend,
                    avg_sentiment,
                    sentiment_positive,
                    sentiment_negative
                ]])
                
                # Use ML model if available
                if self.ml_model:
                    model = self.ml_model['model']
                    prediction_proba = model.predict_proba(features)[0]
                    ml_score = int(prediction_proba[1] * 100)  # Probability of positive outcome
                    overall_score = ml_score
                else:
                    # Fallback: simple scoring
                    overall_score = int((return_10d + 1) * 50)
                    ml_score = overall_score
                
                # Generate signals
                signals = []
                if return_10d > 0.05:
                    signals.append(f"Strong momentum: +{return_10d*100:.1f}% in 10 days")
                elif return_10d < -0.05:
                    signals.append(f"Negative momentum: {return_10d*100:.1f}% in 10 days")
                
                if avg_sentiment > 0.3:
                    signals.append(f"Positive news sentiment: {avg_sentiment:.2f}")
                elif avg_sentiment < -0.3:
                    signals.append(f"Negative news sentiment: {avg_sentiment:.2f}")
                
                if volume_trend > 0.5:
                    signals.append("High volume surge detected")
                
                # Risk level
                volatility = np.std([closes[i]/closes[i-1] - 1 for i in range(1, len(closes))])
                if volatility > 0.03:
                    risk_level = 'High'
                elif volatility > 0.02:
                    risk_level = 'Medium'
                else:
                    risk_level = 'Low'
                
                return {
                    'ticker': ticker,
                    'company_name': stock.company_name,
                    'sector': stock.sector,
                    'industry': stock.industry,
                    'price': current_price,
                    'overall_score': overall_score,
                    'technical_score': int(momentum * 50 + 50),
                    'fundamental_score': 50,  # Not used in this model
                    'sentiment_score': int((avg_sentiment + 1) * 50),
                    'ml_confidence': ml_score,
                    'confidence': ml_score,
                    'risk_level': risk_level,
                    'signals': signals[:4] if signals else ['Normal market conditions'],
                    'warnings': [],
                    'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            
        except Exception as e:
            logger.error(f"Error scoring {ticker}: {e}")
            return None
    
    def generate_recommendations(self, num_stocks=10, save_to_db=True, strategy_type='momentum') -> list:
        """
        Generate REAL stock recommendations
        
        Args:
            num_stocks: Number of top stocks to return
            save_to_db: Whether to save recommendations and create performance trackers
            strategy_type: Strategy type for tracking ('momentum', 'dip', etc.)
        """
        try:
            # Get all stocks from database
            stocks = self.db_manager.get_all_stocks()
            
            if not stocks:
                logger.warning("No stocks in database")
                return []
            
            # Score each stock using database + ML model
            scored_stocks = []
            for stock in stocks:
                try:
                    # Always use score_stock_simple (it uses ML model internally)
                    score_dict = self.score_stock_simple(stock.ticker)
                    
                    # Only add if scoring succeeded
                    if score_dict is not None:
                        scored_stocks.append(score_dict)
                    else:
                        logger.debug(f"Skipping {stock.ticker} - no score returned")
                except Exception as e:
                    logger.warning(f"Failed to score {stock.ticker}: {e}")
                    continue
            
            # Sort by overall score
            scored_stocks.sort(key=lambda x: x['overall_score'], reverse=True)
            
            # Get top N
            top_stocks = scored_stocks[:num_stocks]
            
            # Save to database and create performance trackers
            if save_to_db and top_stocks:
                self._save_recommendations_to_db(top_stocks, strategy_type)
            
            return top_stocks
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return []
    
    def _save_recommendations_to_db(self, recommendations: list, strategy_type: str = 'momentum'):
        """
        Save recommendations to database and create performance trackers.
        
        Args:
            recommendations: List of recommendation dictionaries
            strategy_type: Strategy type ('momentum', 'dip', etc.)
        """
        from data.schema import Recommendation, RecommendationPerformance
        
        try:
            session = self.db_manager.Session()
            current_time = datetime.utcnow()
            
            for rank, rec in enumerate(recommendations, 1):
                try:
                    # Get stock from database
                    stock = session.query(self.db_manager.Stock)\
                        .filter_by(ticker=rec['ticker'])\
                        .first()
                    
                    if not stock:
                        logger.warning(f"Stock {rec['ticker']} not found in database")
                        continue
                    
                    # Create recommendation record
                    recommendation = Recommendation(
                        stock_id=stock.id,
                        created_at=current_time,
                        overall_score=rec['overall_score'],
                        technical_score=rec.get('technical_score', 0),
                        fundamental_score=rec.get('fundamental_score', 0),
                        sentiment_score=rec.get('sentiment_score', 0),
                        signals=rec.get('signals', []),
                        rank=rank,
                        price_at_recommendation=rec['current_price'],
                        strategy_type=strategy_type
                    )
                    
                    session.add(recommendation)
                    session.flush()  # Get the recommendation ID
                    
                    # Create performance tracker
                    performance_tracker = RecommendationPerformance(
                        recommendation_id=recommendation.id,
                        entry_date=current_time,
                        entry_price=rec['current_price'],
                        peak_price=rec['current_price'],
                        peak_return=0.0,
                        trough_price=rec['current_price'],
                        trough_return=0.0,
                        status='tracking'
                    )
                    
                    session.add(performance_tracker)
                    
                    logger.debug(f"Saved recommendation for {rec['ticker']} (rank {rank}) with performance tracker")
                
                except Exception as e:
                    logger.error(f"Error saving recommendation for {rec.get('ticker', 'unknown')}: {e}")
                    continue
            
            session.commit()
            logger.info(f"✅ Saved {len(recommendations)} recommendations with performance trackers")
            
        except Exception as e:
            logger.error(f"Error in _save_recommendations_to_db: {e}")
            session.rollback()
        finally:
            session.close()
    
    @tasks.loop(time=time(hour=9, minute=30, tzinfo=pytz.timezone('America/New_York')))
    async def daily_analysis(self):
        """Run full analysis pipeline every market day at 9:30 AM ET"""
        try:
            et_tz = pytz.timezone('America/New_York')
            now = datetime.now(et_tz)
            
            # Skip weekends
            if now.weekday() >= 5:
                logger.info("Market closed (weekend) - skipping analysis")
                return
            
            if self.analysis_in_progress:
                logger.warning("Analysis already in progress")
                return
            
            self.analysis_in_progress = True
            
            channel = self.get_channel(int(self.config.DISCORD_CHANNEL_ID))
            if not channel:
                logger.error("Could not find configured channel")
                return
            
            # Send initial message
            await channel.send("🔄 Running daily stock analysis with REAL data... This may take a few minutes.")
            
            # Generate REAL recommendations
            logger.info("Generating real recommendations...")
            recommendations = self.generate_recommendations(num_stocks=10)
            
            if not recommendations:
                await channel.send("❌ Failed to generate recommendations. Check logs.")
                return
            
            self.current_recommendations = recommendations
            self.last_update = datetime.now(et_tz)
            
            # Create and send embed
            embed = self.create_daily_recommendations_embed(
                recommendations,
                {
                    'total_scored': len(recommendations),
                    'avg_score': sum(r['overall_score'] for r in recommendations) / len(recommendations),
                    'avg_confidence': sum(r['confidence'] for r in recommendations) / len(recommendations)
                }
            )
            
            await channel.send(embed=embed)
            
            # Send top 3 detailed views
            for i, rec in enumerate(recommendations[:3], 1):
                detail_embed = self.create_stock_detail_embed(rec)
                await channel.send(embed=detail_embed)
                await asyncio.sleep(1)
            
            logger.info(f"Daily analysis complete. Posted {len(recommendations)} recommendations.")
            
        except Exception as e:
            logger.error(f"Error in daily_analysis: {e}")
            logger.error(traceback.format_exc())
            if channel:
                await channel.send(f"❌ Error during analysis: {str(e)}")
        finally:
            self.analysis_in_progress = False
    
    @daily_analysis.before_loop
    async def before_daily_analysis(self):
        """Wait until bot is ready."""
        await self.wait_until_ready()
    
    def create_daily_recommendations_embed(self, recommendations, summary):
        """Create rich embed for daily recommendations (REAL DATA)"""
        embed = discord.Embed(
            title="📈 Today's Top 10 Stock Picks (REAL DATA)",
            description=f"AI-powered recommendations | Last updated: {datetime.now().strftime('%I:%M %p ET')}",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        # Add summary stats
        embed.add_field(
            name="📊 Analysis Summary",
            value=f"• Stocks analyzed: {summary['total_scored']}\n"
                  f"• Average score: {summary['avg_score']:.0f}/100\n"
                  f"• ML Model: {'✅ Active' if self.has_ml_model else '⚠️ Rule-based'}",
            inline=False
        )
        
        # Add top 10 picks
        for i, rec in enumerate(recommendations[:10], 1):
            risk_emoji = {"Low": "🟢", "Medium": "🟡", "High": "🔴"}[rec['risk_level']]
            
            signals_text = "\n".join([f" • {s}" for s in rec['signals'][:2]])
            
            embed.add_field(
                name=f"{i}. {rec['ticker']} - {rec['company_name']} {risk_emoji}",
                value=f"**${rec['price']:.2f}** | Score: **{rec['overall_score']}/100**\n{signals_text}",
                inline=False
            )
        
        embed.set_footer(text="💡 Use /stock <ticker> for detailed analysis | All data is REAL")
        
        return embed
    
    def create_stock_detail_embed(self, recommendation):
        """Create detailed embed for single stock (REAL DATA)"""
        embed = discord.Embed(
            title=f"📊 {recommendation['ticker']} - {recommendation['company_name']}",
            description=f"{recommendation['sector']} | {recommendation['industry']}",
            color=discord.Color.blue(),
            url=f"https://finance.yahoo.com/quote/{recommendation['ticker']}"
        )
        
        # Price and scores
        embed.add_field(
            name="💰 Current Price (REAL)",
            value=f"${recommendation['price']:.2f}",
            inline=True
        )
        embed.add_field(
            name="🎯 Overall Score",
            value=f"{recommendation['overall_score']}/100",
            inline=True
        )
        embed.add_field(
            name="🔒 Risk Level",
            value=recommendation['risk_level'],
            inline=True
        )
        
        # Component scores
        embed.add_field(
            name="📈 Technical (REAL)",
            value=f"{recommendation['technical_score']}/100",
            inline=True
        )
        embed.add_field(
            name="💼 Fundamental (REAL)",
            value=f"{recommendation['fundamental_score']}/100",
            inline=True
        )
        embed.add_field(
            name="📰 Sentiment",
            value=f"{recommendation['sentiment_score']}/100",
            inline=True
        )
        
        # Key signals
        signals_text = "\n".join([f"• {s}" for s in recommendation['signals']])
        embed.add_field(
            name="🎯 Key Signals",
            value=signals_text or "No specific signals",
            inline=False
        )
        
        # Confidence
        confidence_text = (
            f"{'🤖 ML Model' if self.has_ml_model else '📊 Rule-Based'}: "
            f"{recommendation['confidence']}% confidence"
        )
        embed.add_field(
            name="🎯 Confidence",
            value=confidence_text,
            inline=False
        )
        
        embed.set_footer(text=f"Last updated: {recommendation.get('last_updated', 'Unknown')} | Data: Yahoo Finance")
        
        return embed
    
    async def on_error(self, event, *args, **kwargs):
        """Global error handler"""
        logger.error(f"Error in {event}")
        logger.error(traceback.format_exc())
    
    async def on_command_error(self, ctx, error):
        """Command error handler"""
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: {error.param.name}")
        else:
            await ctx.send(f"❌ An error occurred: {str(error)}")
            logger.error(f"Command error: {error}")


# Register slash commands (will add after class definition)
def register_slash_commands(bot: SmartInvestBot):
    """Register all slash commands with REAL data integration."""
    
    @bot.tree.command(name="stock", description="Get REAL detailed analysis for a specific stock")
    @app_commands.describe(ticker="Stock ticker symbol (e.g., AAPL)")
    async def stock_command(interaction: discord.Interaction, ticker: str):
        """Detailed analysis of a single stock using REAL DATA"""
        await interaction.response.defer()
        
        try:
            ticker = ticker.upper().strip()
            
            if not ticker.isalpha() or len(ticker) > 5:
                await interaction.followup.send("❌ Invalid ticker symbol")
                return
            
            await interaction.followup.send(f"🔍 Analyzing {ticker} from database...")
            
            # Score using database + ML model
            score_dict = bot.score_stock_simple(ticker)
            
            if not score_dict:
                await interaction.followup.send(f"❌ Could not score {ticker}. Stock may not be in database or has insufficient data.")
                return
            
            # Create embed with REAL data
            embed = bot.create_stock_detail_embed(score_dict)
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error analyzing {ticker}: {str(e)}\n\nMake sure stock data is loaded.")
            logger.error(f"Error in stock_command for {ticker}: {e}")
            logger.error(traceback.format_exc())
    
    @bot.tree.command(name="daily", description="Get today's top REAL stock recommendations")
    async def daily_command(interaction: discord.Interaction):
        """Display current daily recommendations using REAL DATA"""
        await interaction.response.defer()
        
        try:
            if not bot.current_recommendations:
                # Generate fresh recommendations
                await interaction.followup.send("📊 Generating REAL recommendations... This may take a minute.")
                
                recommendations = bot.generate_recommendations(num_stocks=10)
                
                if not recommendations:
                    await interaction.followup.send(
                        "❌ No recommendations available. Make sure stocks are loaded in database.\n"
                        "Run: `python scripts/load_full_data.py`"
                    )
                    return
                
                bot.current_recommendations = recommendations
                bot.last_update = datetime.now(pytz.timezone('America/New_York'))
            
            # Check freshness
            if bot.last_update:
                age_hours = (datetime.now(pytz.timezone('America/New_York')) - bot.last_update).total_seconds() / 3600
                if age_hours > 24:
                    staleness_warning = f"\n⚠️ Recommendations are {age_hours:.0f} hours old. Use `/refresh` for latest."
                else:
                    staleness_warning = ""
            else:
                staleness_warning = ""
            
            # Create embed with REAL data
            embed = bot.create_daily_recommendations_embed(
                bot.current_recommendations,
                {
                    'total_scored': len(bot.current_recommendations),
                    'avg_score': sum(r['overall_score'] for r in bot.current_recommendations) / len(bot.current_recommendations),
                    'avg_confidence': sum(r['confidence'] for r in bot.current_recommendations) / len(bot.current_recommendations)
                }
            )
            
            await interaction.followup.send(content=staleness_warning, embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}")
            logger.error(f"Error in daily_command: {e}")
            logger.error(traceback.format_exc())
    
    @bot.tree.command(name="backtest", description="Run portfolio backtest simulation")
    @app_commands.describe(
        days="Number of days to backtest (default: 90)",
        capital="Starting capital in dollars (default: 10000)",
        hold_days="Days to hold each position (default: 5)"
    )
    async def backtest_command(interaction: discord.Interaction, days: int = 90, 
                               capital: int = 10000, hold_days: int = 5):
        """Run comprehensive portfolio backtest"""
        await interaction.response.defer()
        
        try:
            # Validate inputs
            if days < 30 or days > 365:
                await interaction.followup.send("❌ Days must be between 30 and 365")
                return
            
            if capital < 1000 or capital > 1000000:
                await interaction.followup.send("❌ Capital must be between $1,000 and $1,000,000")
                return
            
            if hold_days < 1 or hold_days > 30:
                await interaction.followup.send("❌ Hold days must be between 1 and 30")
                return
            
            # Import backtest components
            from models.backtester import Backtester, PortfolioSimulator
            from utils.performance import PerformanceAnalyzer
            from utils.visualizer import BacktestVisualizer
            from datetime import date, timedelta
            
            await interaction.followup.send(
                f"⏳ Running {days}-day backtest with ${capital:,} starting capital...\n"
                f"This may take 30-60 seconds. Please wait!"
            )
            
            # Calculate date range
            end_date = date.today() - timedelta(days=1)  # Yesterday
            start_date = end_date - timedelta(days=days)
            
            logger.info(f"Starting backtest: {start_date} to {end_date}")
            
            # Initialize backtester
            backtester = Backtester(
                db_manager=bot.db_manager,
                ml_model=bot.ml_model.get('model') if bot.ml_model else None,
                feature_calculator=bot._calculate_backtest_features
            )
            
            # Initialize simulator
            simulator = PortfolioSimulator(
                starting_capital=capital,
                hold_days=hold_days,
                max_positions=10
            )
            
            # Run backtest
            results = simulator.run_backtest(backtester, start_date, end_date)
            
            # Calculate metrics
            analyzer = PerformanceAnalyzer(
                closed_trades=results['closed_trades'],
                equity_curve=results['equity_curve'],
                starting_capital=capital
            )
            metrics = analyzer.calculate_all_metrics()
            
            # Generate visualizations
            visualizer = BacktestVisualizer()
            equity_chart = visualizer.plot_equity_curve(results['equity_curve'])
            drawdown_chart = visualizer.plot_drawdown(results['equity_curve'])
            trade_dist_chart = visualizer.plot_trade_distribution(results['closed_trades'])
            
            # Create Discord embed
            embed = discord.Embed(
                title=f"📊 Backtest Results ({days} Days)",
                description=f"Simulated performance following SmartInvest top-10 daily picks",
                color=discord.Color.green() if metrics['total_return_pct'] > 0 else discord.Color.red()
            )
            
            # Returns section
            embed.add_field(
                name="💰 Returns",
                value=(
                    f"**Starting:** ${metrics['starting_capital']:,.0f}\n"
                    f"**Ending:** ${metrics['final_value']:,.0f}\n"
                    f"**Total Return:** {metrics['total_return_pct']:+.2f}%\n"
                    f"**S&P 500:** {metrics['benchmark_return']:+.2f}%\n"
                    f"**Alpha (Outperform):** {metrics['alpha']:+.2f}%"
                ),
                inline=False
            )
            
            # Trade statistics
            embed.add_field(
                name="📈 Trade Statistics",
                value=(
                    f"**Total Trades:** {metrics['total_trades']}\n"
                    f"**Winners:** {metrics['winning_trades']} ({metrics['win_rate']:.1f}%)\n"
                    f"**Losers:** {metrics['losing_trades']}\n"
                    f"**Avg Win:** +{metrics['avg_win']:.2f}%\n"
                    f"**Avg Loss:** {metrics['avg_loss']:.2f}%\n"
                    f"**Avg Hold:** {metrics['avg_days_held']:.1f} days"
                ),
                inline=True
            )
            
            # Risk metrics
            embed.add_field(
                name="⚠️ Risk Metrics",
                value=(
                    f"**Sharpe Ratio:** {metrics['sharpe_ratio']:.2f}\n"
                    f"**Max Drawdown:** {metrics['max_drawdown']:.2f}%\n"
                    f"**Profit Factor:** {metrics['profit_factor']:.2f}"
                ),
                inline=True
            )
            
            # Best/worst trades
            if metrics['best_trade']:
                best = metrics['best_trade']
                embed.add_field(
                    name="🏆 Best Trade",
                    value=f"{best['ticker']}: {best['pnl_pct']:+.2f}%\n({best['entry_date']} → {best['exit_date']})",
                    inline=True
                )
            
            if metrics['worst_trade']:
                worst = metrics['worst_trade']
                embed.add_field(
                    name="💀 Worst Trade",
                    value=f"{worst['ticker']}: {worst['pnl_pct']:+.2f}%\n({worst['entry_date']} → {worst['exit_date']})",
                    inline=True
                )
            
            # Interpretation
            if metrics['total_return_pct'] > 15:
                interpretation = "🎉 Excellent returns! Strategy significantly outperformed."
            elif metrics['total_return_pct'] > 5:
                interpretation = "✅ Good returns. Strategy showed positive edge."
            elif metrics['total_return_pct'] > 0:
                interpretation = "💼 Modest returns. Strategy was profitable."
            else:
                interpretation = "⚠️ Negative returns. Strategy needs refinement."
            
            embed.add_field(
                name="📝 Interpretation",
                value=interpretation,
                inline=False
            )
            
            embed.set_footer(text=f"Period: {start_date} to {end_date} | {metrics['total_days']} calendar days")
            
            # Send embed with charts
            files = []
            if equity_chart:
                files.append(discord.File(equity_chart))
            if drawdown_chart:
                files.append(discord.File(drawdown_chart))
            if trade_dist_chart:
                files.append(discord.File(trade_dist_chart))
            
            await interaction.followup.send(embed=embed, files=files)
            
            logger.info(f"Backtest completed: {metrics['total_return_pct']:.2f}% return, {metrics['win_rate']:.1f}% win rate")
            
        except Exception as e:
            await interaction.followup.send(f"❌ Backtest failed: {str(e)}")
            logger.error(f"Error in backtest_command: {e}")
            logger.error(traceback.format_exc())
    
    @bot.tree.command(name="refresh", description="Force refresh with REAL data now")
    async def refresh_command(interaction: discord.Interaction):
        """Manually trigger a full analysis refresh with REAL DATA"""
        await interaction.response.defer()
        
        try:
            await interaction.followup.send(
                "🔄 Starting fresh analysis with REAL data... This will take 2-5 minutes.\n"
                "I'll ping you when it's done!"
            )
            
            # Generate REAL recommendations
            logger.info("Manual refresh triggered - generating real recommendations")
            recommendations = bot.generate_recommendations(num_stocks=10)
            
            if not recommendations:
                await interaction.followup.send(
                    "❌ Failed to generate recommendations. Make sure stocks are loaded.\n"
                    "Run: `python scripts/load_full_data.py`"
                )
                return
            
            bot.current_recommendations = recommendations
            bot.last_update = datetime.now(pytz.timezone('America/New_York'))
            
            # Create embed
            embed = bot.create_daily_recommendations_embed(
                recommendations,
                {
                    'total_scored': len(recommendations),
                    'avg_score': sum(r['overall_score'] for r in recommendations) / len(recommendations),
                    'avg_confidence': sum(r['confidence'] for r in recommendations) / len(recommendations)
                }
            )
            
            await interaction.followup.send(
                content=f"✅ {interaction.user.mention} Analysis complete with REAL DATA!",
                embed=embed
            )
            
            logger.info("Manual refresh complete")
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error during refresh: {str(e)}")
            logger.error(f"Error in refresh_command: {e}")
            logger.error(traceback.format_exc())
    
    @bot.tree.command(name="dip", description="Find quality stocks on sale (buy the dip)")
    @app_commands.describe(
        limit="Number of stocks to show (default: 10)"
    )
    async def dip_command(interaction: discord.Interaction, limit: int = 10):
        """Find buy-the-dip opportunities"""
        await interaction.response.defer()
        
        try:
            # Validate input
            if limit < 1 or limit > 20:
                await interaction.followup.send("❌ Limit must be between 1 and 20")
                return
            
            await interaction.followup.send(
                f"🔍 Scanning {len(bot.db_manager.get_all_stocks())} stocks for dip opportunities...\n"
                f"Looking for quality stocks that dropped 10-30% with strong fundamentals.\n"
                f"⏳ This may take 15-30 seconds. Please wait!"
            )
            
            logger.info(f"Finding dip candidates (limit: {limit})")
            
            # Find dip candidates
            candidates = bot.dip_scanner.find_dip_candidates(limit=limit)
            
            if not candidates:
                await interaction.followup.send(
                    "📊 No dip opportunities found right now.\n\n"
                    "This means either:\n"
                    "• Market is strong (no major drops)\n"
                    "• Stocks that dropped don't meet quality filters\n"
                    "• Try again later or lower min_dip_score threshold"
                )
                return
            
            # Create Discord embed
            embed = discord.Embed(
                title="📉 Buy The Dip - Top Opportunities",
                description=f"Quality stocks temporarily on sale (found {len(candidates)})",
                color=discord.Color.orange()
            )
            
            # Add top candidates
            for i, candidate in enumerate(candidates[:min(limit, 10)], 1):
                # Determine emoji based on rank
                if i == 1:
                    emoji = "🥇"
                elif i == 2:
                    emoji = "🥈"
                elif i == 3:
                    emoji = "🥉"
                else:
                    emoji = f"{i}."
                
                # Format RSI color
                rsi = candidate['rsi']
                if rsi < 30:
                    rsi_indicator = "🔴"
                elif rsi < 40:
                    rsi_indicator = "🟡"
                else:
                    rsi_indicator = "🟢"
                
                # Get dip reason
                reason = bot.dip_scanner.get_dip_reason(candidate)
                
                # Format fundamentals if available
                fundamentals_str = ""
                if candidate.get('pe_ratio'):
                    fundamentals_str += f"P/E: {candidate['pe_ratio']:.1f} | "
                if candidate.get('roe'):
                    fundamentals_str += f"ROE: {candidate['roe']:.1f}% | "
                if candidate.get('debt_to_equity') is not None:
                    fundamentals_str += f"D/E: {candidate['debt_to_equity']:.1f}"
                
                # Format field
                field_value = (
                    f"**Current:** ${candidate['current_price']:.2f} "
                    f"(was ${candidate['recent_high']:.2f}, {candidate['price_drop_pct']:.1f}%)\n"
                    f"**RSI:** {rsi:.0f} {rsi_indicator} | "
                    f"**Quality:** {candidate['quality']}\n"
                    f"**Dip Score:** {candidate['total_score']}/100 "
                    f"(Fund: {candidate.get('fundamental_score', 0)}/30)\n"
                )
                
                if fundamentals_str:
                    field_value += f"**Fundamentals:** {fundamentals_str}\n"
                
                field_value += (
                    f"**Why:** {reason}\n"
                    f"**Risk:** {candidate['risk_level']}"
                )
                
                embed.add_field(
                    name=f"{emoji} {candidate['ticker']} - {candidate['company_name']}",
                    value=field_value,
                    inline=False
                )
            
            # Add interpretation
            embed.add_field(
                name="📝 How To Use",
                value=(
                    "**🟢 Low Risk:** Safe dips in quality stocks\n"
                    "**🟡 Moderate Risk:** Larger drops, still good fundamentals\n"
                    "**🔴 High Risk:** Major drops, higher risk/reward\n\n"
                    "💡 **Tip:** RSI < 30 = deeply oversold (bounce likely)\n"
                    "⭐⭐⭐⭐⭐ = Highest quality companies"
                ),
                inline=False
            )
            
            embed.set_footer(
                text=f"Scanned {len(bot.db_manager.get_all_stocks())} stocks | "
                     f"Min score: {bot.dip_scanner.min_dip_score}"
            )
            
            await interaction.followup.send(embed=embed)
            
            logger.info(f"Dip scan complete: {len(candidates)} candidates found")
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error during dip scan: {str(e)}")
            logger.error(f"Error in dip_command: {e}")
            logger.error(traceback.format_exc())
    
    @bot.tree.command(name="backtest-dip", description="Backtest the buy-the-dip strategy")
    @app_commands.describe(
        days="Number of days to backtest (default: 90)",
        capital="Starting capital in dollars (default: 10000)",
        hold_days="Days to hold each dip position (default: 15)",
        max_positions="Max concurrent positions (default: 5)"
    )
    async def backtest_dip_command(interaction: discord.Interaction, days: int = 90,
                                   capital: int = 10000, hold_days: int = 15,
                                   max_positions: int = 5):
        """Backtest the dip-buying strategy"""
        await interaction.response.defer()
        
        try:
            # Validate inputs
            if days < 30 or days > 365:
                await interaction.followup.send("❌ Days must be between 30 and 365")
                return
            
            if capital < 1000 or capital > 1000000:
                await interaction.followup.send("❌ Capital must be between $1,000 and $1,000,000")
                return
            
            if hold_days < 5 or hold_days > 60:
                await interaction.followup.send("❌ Hold days must be between 5 and 60")
                return
            
            if max_positions < 1 or max_positions > 10:
                await interaction.followup.send("❌ Max positions must be between 1 and 10")
                return
            
            from models.dip_backtester import DipBacktester
            from utils.performance import PerformanceAnalyzer
            from datetime import date, timedelta
            
            await interaction.followup.send(
                f"⏳ Running {days}-day dip strategy backtest with ${capital:,}...\n"
                f"Hold period: {hold_days} days, Max positions: {max_positions}\n"
                f"This may take 1-2 minutes. Please wait!"
            )
            
            # Calculate date range
            end_date = date.today() - timedelta(days=1)
            start_date = end_date - timedelta(days=days)
            
            logger.info(f"Starting dip backtest: {start_date} to {end_date}")
            
            # Initialize backtester
            dip_backtester = DipBacktester(
                db_manager=bot.db_manager,
                dip_scanner=bot.dip_scanner
            )
            
            # Run backtest
            results = dip_backtester.run_backtest(
                start_date=start_date,
                end_date=end_date,
                initial_capital=float(capital),
                hold_days=hold_days,
                max_positions=max_positions
            )
            
            # Create result embed
            embed = discord.Embed(
                title=f"📉 Dip Strategy Backtest Results ({days} Days)",
                description=f"Tested buying oversold stocks with strong fundamentals",
                color=discord.Color.orange()
            )
            
            # Returns section
            total_return = results['total_return']
            return_color = "🟢" if total_return > 0 else "🔴"
            
            embed.add_field(
                name="💰 Returns",
                value=f"**Starting:** ${results['initial_capital']:,.0f}\n"
                      f"**Ending:** ${results['final_value']:,.0f}\n"
                      f"**Total Return:** {return_color} {total_return:+.2f}%",
                inline=False
            )
            
            # Trade statistics
            if results['total_trades'] > 0:
                embed.add_field(
                    name="📈 Trade Statistics",
                    value=f"**Total Trades:** {results['total_trades']}\n"
                          f"**Winners:** {results['winning_trades']} ({results['win_rate']:.1f}%)\n"
                          f"**Losers:** {results['losing_trades']}\n"
                          f"**Avg Win:** +{results['avg_win']:.2f}%\n"
                          f"**Avg Loss:** {results['avg_loss']:.2f}%\n"
                          f"**Avg Hold:** {results['avg_hold']:.1f} days",
                    inline=False
                )
                
                # Best/Worst trades
                if results['best_trade']:
                    best = results['best_trade']
                    worst = results['worst_trade']
                    
                    embed.add_field(
                        name="🏆 Best Trade",
                        value=f"**{best['ticker']}:** {best['return_pct']:+.2f}%\n"
                              f"({best['entry_date']} → {best['exit_date']})",
                        inline=True
                    )
                    
                    embed.add_field(
                        name="💀 Worst Trade",
                        value=f"**{worst['ticker']}:** {worst['return_pct']:+.2f}%\n"
                              f"({worst['entry_date']} → {worst['exit_date']})",
                        inline=True
                    )
                
                # Interpretation
                if total_return > 5 and results['win_rate'] > 55:
                    interpretation = "✅ Strong performance. Dip strategy showed positive edge."
                elif total_return > 0:
                    interpretation = "✅ Profitable. Strategy beat cash (0% return)."
                else:
                    interpretation = "⚠️ Strategy underperformed. Consider adjusting parameters."
                
                embed.add_field(
                    name="📝 Interpretation",
                    value=interpretation,
                    inline=False
                )
            else:
                embed.add_field(
                    name="⚠️ No Trades",
                    value="No dip opportunities met the criteria during this period.\n"
                          "Try: Longer period, lower min_dip_score, or different hold days.",
                    inline=False
                )
            
            embed.set_footer(text=f"Period: {start_date} to {end_date} | {days} calendar days")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}")
            logger.error(f"Error in backtest_dip_command: {e}")
            logger.error(traceback.format_exc())
    
    @bot.tree.command(name="backtest-stock", description="Backtest a specific stock's performance")
    @app_commands.describe(
        ticker="Stock ticker symbol (e.g., AAPL)",
        days="Number of days to backtest (default: 90)",
        capital="Starting capital in dollars (default: 10000)"
    )
    async def backtest_stock_command(interaction: discord.Interaction, ticker: str,
                                     days: int = 90, capital: int = 10000):
        """Backtest a specific stock's buy-and-hold performance"""
        await interaction.response.defer()
        
        try:
            ticker = ticker.upper()
            
            # Validate inputs
            if days < 30 or days > 365:
                await interaction.followup.send("❌ Days must be between 30 and 365")
                return
            
            if capital < 100 or capital > 1000000:
                await interaction.followup.send("❌ Capital must be between $100 and $1,000,000")
                return
            
            from models.dip_backtester import StockBacktester
            from datetime import date, timedelta
            
            await interaction.followup.send(
                f"⏳ Backtesting {ticker} for {days} days with ${capital:,}...\n"
                f"Testing buy-and-hold strategy. Please wait!"
            )
            
            # Calculate date range
            end_date = date.today() - timedelta(days=1)
            start_date = end_date - timedelta(days=days)
            
            logger.info(f"Starting stock backtest: {ticker} from {start_date} to {end_date}")
            
            # Initialize backtester
            stock_backtester = StockBacktester(db_manager=bot.db_manager)
            
            # Run backtest
            results = stock_backtester.backtest_stock(
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
                initial_capital=float(capital)
            )
            
            # Check for errors
            if 'error' in results:
                await interaction.followup.send(f"❌ {results['error']}")
                return
            
            # Create result embed
            total_return = results['total_return']
            return_color = "🟢" if total_return > 0 else "🔴"
            
            embed = discord.Embed(
                title=f"📊 {ticker} Backtest Results ({days} Days)",
                description=f"{results['company_name']} - Buy & Hold Strategy",
                color=discord.Color.green() if total_return > 0 else discord.Color.red()
            )
            
            # Price & Returns
            embed.add_field(
                name="💰 Performance",
                value=f"**Entry Price:** ${results['entry_price']:.2f}\n"
                      f"**Exit Price:** ${results['exit_price']:.2f}\n"
                      f"**Total Return:** {return_color} {total_return:+.2f}%\n"
                      f"**Profit:** {return_color} ${results['profit']:+,.2f}",
                inline=False
            )
            
            # Position Details
            embed.add_field(
                name="📈 Position",
                value=f"**Capital:** ${results['initial_capital']:,.0f}\n"
                      f"**Shares:** {results['shares']:,}\n"
                      f"**Entry Value:** ${results['entry_value']:,.2f}\n"
                      f"**Exit Value:** ${results['exit_value']:,.2f}",
                inline=True
            )
            
            # Risk Metrics
            embed.add_field(
                name="⚠️ Risk",
                value=f"**Volatility:** {results['annualized_volatility']:.1f}%\n"
                      f"**Max Drawdown:** {results['max_drawdown']:.1f}%\n"
                      f"**Days Held:** {results['days']}",
                inline=True
            )
            
            # Sentiment
            if results['news_articles'] > 0:
                sentiment_emoji = "😊" if results['avg_sentiment'] > 0.1 else "😐" if results['avg_sentiment'] > -0.1 else "😟"
                embed.add_field(
                    name="📰 News Sentiment",
                    value=f"**Avg Sentiment:** {sentiment_emoji} {results['avg_sentiment']:.3f}\n"
                          f"**Articles:** {results['news_articles']}",
                    inline=False
                )
            
            # Interpretation
            annualized_return = (((results['exit_value'] / results['entry_value']) ** (365 / results['days'])) - 1) * 100
            
            if total_return > 10:
                interpretation = f"✅ Strong performer! Annualized: ~{annualized_return:+.1f}%"
            elif total_return > 0:
                interpretation = f"✅ Profitable. Annualized: ~{annualized_return:+.1f}%"
            else:
                interpretation = f"📉 Declined {abs(total_return):.1f}% during this period"
            
            embed.add_field(
                name="📝 Summary",
                value=interpretation,
                inline=False
            )
            
            embed.set_footer(text=f"Period: {results['start_date']} to {results['end_date']}")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}")
            logger.error(f"Error in backtest_stock_command: {e}")
            logger.error(traceback.format_exc())
    
    @bot.tree.command(name="performance", description="View SmartInvest bot's recommendation performance stats")
    @app_commands.describe(
        days="Number of days to analyze (default: 90)",
        strategy="Filter by strategy: 'all', 'momentum', 'dip' (default: all)"
    )
    async def performance_command(interaction: discord.Interaction, days: int = 90, strategy: str = "all"):
        """Display performance statistics for bot recommendations"""
        await interaction.response.defer()
        
        try:
            logger.info(f"Performance command called by {interaction.user}: days={days}, strategy={strategy}")
            
            # Validate inputs
            if days < 7 or days > 365:
                await interaction.followup.send("❌ Please choose between 7-365 days")
                return
            
            if strategy not in ['all', 'momentum', 'dip']:
                await interaction.followup.send("❌ Strategy must be 'all', 'momentum', or 'dip'")
                return
            
            # Get performance stats
            strategy_filter = None if strategy == 'all' else strategy
            stats = bot.db_manager.get_performance_stats(days=days, strategy_type=strategy_filter)
            
            # Check if data exists
            if 'error' in stats or stats['total_recommendations'] == 0:
                await interaction.followup.send(
                    f"ℹ️ No performance data available yet for the last {days} days.\n\n"
                    f"**Performance tracking is automatic!** The bot tracks every recommendation it makes.\n\n"
                    f"Start getting recommendations with `/daily` and check back after a few days."
                )
                return
            
            # Create embed
            strategy_name = strategy.capitalize() if strategy != 'all' else 'All Strategies'
            embed = discord.Embed(
                title=f"📊 Bot Performance - {strategy_name}",
                description=f"Tracking {stats['total_recommendations']} recommendations over the last {days} days",
                color=discord.Color.blue()
            )
            
            # 5-day performance
            if '5day' in stats:
                day5 = stats['5day']
                win_emoji = "🟢" if day5['win_rate'] >= 50 else "🔴"
                embed.add_field(
                    name="📈 5-Day Performance",
                    value=f"**Win Rate:** {win_emoji} {day5['win_rate']:.1f}%\n"
                          f"**Total Tracked:** {day5['total']}\n"
                          f"**Winners:** {day5['winners']}\n"
                          f"**Avg Return:** {day5['avg_return']:+.2f}%\n"
                          f"**Avg Win:** +{day5['avg_win']:.2f}%\n"
                          f"**Avg Loss:** {day5['avg_loss']:.2f}%\n"
                          f"**Best:** +{day5['best_return']:.2f}%\n"
                          f"**Worst:** {day5['worst_return']:.2f}%",
                    inline=True
                )
            
            # 30-day performance
            if '30day' in stats:
                day30 = stats['30day']
                win_emoji = "🟢" if day30['win_rate'] >= 50 else "🔴"
                embed.add_field(
                    name="📊 30-Day Performance",
                    value=f"**Win Rate:** {win_emoji} {day30['win_rate']:.1f}%\n"
                          f"**Total Tracked:** {day30['total']}\n"
                          f"**Winners:** {day30['winners']}\n"
                          f"**Avg Return:** {day30['avg_return']:+.2f}%\n"
                          f"**Avg Win:** +{day30['avg_win']:.2f}%\n"
                          f"**Avg Loss:** {day30['avg_loss']:.2f}%\n"
                          f"**Best:** +{day30['best_return']:.2f}%\n"
                          f"**Worst:** {day30['worst_return']:.2f}%",
                    inline=True
                )
            
            # Interpretation
            if '30day' in stats:
                day30 = stats['30day']
                if day30['avg_return'] > 2:
                    interpretation = "✅ **Strong performance!** Recommendations are profitable on average."
                elif day30['avg_return'] > 0:
                    interpretation = "✅ **Positive performance.** Recommendations show modest gains."
                elif day30['avg_return'] > -2:
                    interpretation = "⚠️ **Flat performance.** Returns are near breakeven."
                else:
                    interpretation = "❌ **Underperforming.** Consider refining strategy parameters."
                
                embed.add_field(
                    name="📝 Interpretation",
                    value=interpretation,
                    inline=False
                )
            
            embed.set_footer(text=f"Use /leaderboard to see top performers • Analysis Period: {days} days")
            
            await interaction.followup.send(embed=embed)
        
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}")
            logger.error(f"Error in performance_command: {e}")
            logger.error(traceback.format_exc())
    
    @bot.tree.command(name="leaderboard", description="View top and worst performing stock recommendations")
    @app_commands.describe(
        timeframe="Timeframe to analyze: '5day' or '30day' (default: 30day)",
        limit="Number of stocks to show (default: 10)"
    )
    async def leaderboard_command(interaction: discord.Interaction, timeframe: str = "30day", limit: int = 10):
        """Display leaderboard of best and worst recommendations"""
        await interaction.response.defer()
        
        try:
            logger.info(f"Leaderboard command called by {interaction.user}: timeframe={timeframe}, limit={limit}")
            
            # Validate inputs
            if timeframe not in ['5day', '30day']:
                await interaction.followup.send("❌ Timeframe must be '5day' or '30day'")
                return
            
            if limit < 1 or limit > 25:
                await interaction.followup.send("❌ Limit must be between 1-25")
                return
            
            # Get top and worst performers
            top_performers = bot.db_manager.get_top_performers(limit=limit, timeframe=timeframe)
            worst_performers = bot.db_manager.get_worst_performers(limit=limit, timeframe=timeframe)
            
            if not top_performers and not worst_performers:
                await interaction.followup.send(
                    f"ℹ️ No performance data available yet for {timeframe} timeframe.\n\n"
                    f"Use `/daily` to get recommendations, then check back in a few days!"
                )
                return
            
            # Create embed
            timeframe_name = "5-Day" if timeframe == "5day" else "30-Day"
            embed = discord.Embed(
                title=f"🏆 Leaderboard - {timeframe_name}",
                description="Best and worst performing recommendations",
                color=discord.Color.gold()
            )
            
            # Top performers
            if top_performers:
                top_text = ""
                for i, (perf, rec, stock) in enumerate(top_performers[:limit], 1):
                    return_val = perf.return_30d if timeframe == "30day" else perf.return_5d
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                    top_text += f"{medal} **{stock.ticker}** - {stock.company_name[:20]}\n"
                    top_text += f"    Return: +{return_val:.2f}% | Score: {rec.overall_score}/100\n"
                
                embed.add_field(
                    name="🟢 Top Performers",
                    value=top_text,
                    inline=False
                )
            
            # Worst performers
            if worst_performers:
                worst_text = ""
                for i, (perf, rec, stock) in enumerate(worst_performers[:5], 1):  # Show fewer losers
                    return_val = perf.return_30d if timeframe == "30day" else perf.return_5d
                    worst_text += f"{i}. **{stock.ticker}** - {stock.company_name[:20]}\n"
                    worst_text += f"    Return: {return_val:.2f}% | Score: {rec.overall_score}/100\n"
                
                embed.add_field(
                    name="🔴 Worst Performers",
                    value=worst_text,
                    inline=False
                )
            
            embed.set_footer(text=f"Use /performance for detailed stats • Timeframe: {timeframe_name}")
            
            await interaction.followup.send(embed=embed)
        
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}")
            logger.error(f"Error in leaderboard_command: {e}")
            logger.error(traceback.format_exc())
    
    @bot.tree.command(name="position", description="Manage your stock positions (add/close)")
    @app_commands.describe(
        action="Action: 'add' to open position, 'close' to exit position",
        ticker="Stock ticker symbol",
        shares="Number of shares (for add)",
        price="Entry/exit price per share"
    )
    async def position_command(interaction: discord.Interaction, action: str, ticker: str, 
                               shares: float = None, price: float = None):
        """Add or close a position"""
        await interaction.response.defer()
        
        try:
            action = action.lower()
            ticker = ticker.upper()
            user_id = str(interaction.user.id)
            
            if action == 'add':
                # Validate inputs
                if shares is None or price is None:
                    await interaction.followup.send("❌ For 'add' action, you must provide shares and price")
                    return
                
                if shares <= 0 or price <= 0:
                    await interaction.followup.send("❌ Shares and price must be positive numbers")
                    return
                
                # Add position
                position = bot.db_manager.add_position(
                    discord_user_id=user_id,
                    ticker=ticker,
                    shares=shares,
                    entry_price=price
                )
                
                entry_value = shares * price
                
                embed = discord.Embed(
                    title="✅ Position Added",
                    description=f"Now tracking {ticker}",
                    color=discord.Color.green()
                )
                
                embed.add_field(
                    name="📊 Position Details",
                    value=f"**Ticker:** {ticker}\n"
                          f"**Shares:** {shares:,.2f}\n"
                          f"**Entry Price:** ${price:.2f}\n"
                          f"**Total Value:** ${entry_value:,.2f}",
                    inline=False
                )
                
                embed.add_field(
                    name="🎯 Exit Targets",
                    value=f"**Profit Target:** ${position.profit_target_price:.2f} (+{position.profit_target_pct}%)\n"
                          f"**Stop Loss:** ${position.stop_loss_price:.2f} ({position.stop_loss_pct}%)",
                    inline=False
                )
                
                embed.add_field(
                    name="🔔 Monitoring",
                    value="• Exit signals will be generated automatically\n"
                          "• Check `/exits` to view active alerts\n"
                          "• Use `/alerts` to toggle notifications",
                    inline=False
                )
                
                await interaction.followup.send(embed=embed)
                logger.info(f"User {user_id} added position: {ticker} {shares} @ ${price}")
            
            elif action == 'close':
                # Validate inputs
                if price is None:
                    await interaction.followup.send("❌ For 'close' action, you must provide the exit price")
                    return
                
                if price <= 0:
                    await interaction.followup.send("❌ Price must be a positive number")
                    return
                
                # Find open position for this user and ticker
                positions = bot.db_manager.get_user_positions(user_id, status='open')
                
                matching_position = None
                for pos in positions:
                    session = bot.db_manager.Session()
                    stock = session.query(Stock).filter_by(id=pos.stock_id).first()
                    session.close()
                    if stock and stock.ticker == ticker:
                        matching_position = pos
                        break
                
                if not matching_position:
                    await interaction.followup.send(f"❌ No open position found for {ticker}")
                    return
                
                # Close the position
                closed_pos = bot.db_manager.close_position(
                    position_id=matching_position.id,
                    exit_price=price,
                    exit_reason='manual'
                )
                
                # Create result embed
                profit_color = discord.Color.green() if closed_pos.return_pct > 0 else discord.Color.red()
                profit_emoji = "📈" if closed_pos.return_pct > 0 else "📉"
                
                embed = discord.Embed(
                    title=f"{profit_emoji} Position Closed - {ticker}",
                    description=f"{'Profit' if closed_pos.return_pct > 0 else 'Loss'}: {closed_pos.return_pct:+.2f}%",
                    color=profit_color
                )
                
                embed.add_field(
                    name="💰 Trade Summary",
                    value=f"**Entry:** ${closed_pos.entry_price:.2f} ({closed_pos.entry_date.strftime('%b %d')})\n"
                          f"**Exit:** ${closed_pos.exit_price:.2f} ({closed_pos.exit_date.strftime('%b %d')})\n"
                          f"**Shares:** {closed_pos.shares:,.2f}\n"
                          f"**Hold Time:** {(closed_pos.exit_date - closed_pos.entry_date).days} days",
                    inline=True
                )
                
                embed.add_field(
                    name="📊 Performance",
                    value=f"**Return:** {closed_pos.return_pct:+.2f}%\n"
                          f"**Profit/Loss:** ${closed_pos.profit_loss:+,.2f}\n"
                          f"**Entry Value:** ${closed_pos.entry_value:,.2f}\n"
                          f"**Exit Value:** ${closed_pos.exit_value:,.2f}",
                    inline=True
                )
                
                embed.set_footer(text="Trade added to your performance history • Use /track to view all trades")
                
                await interaction.followup.send(embed=embed)
                logger.info(f"User {user_id} closed position: {ticker} {closed_pos.return_pct:+.2f}%")
            
            else:
                await interaction.followup.send("❌ Action must be 'add' or 'close'")
        
        except ValueError as e:
            await interaction.followup.send(f"❌ {str(e)}")
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}")
            logger.error(f"Error in position_command: {e}")
            logger.error(traceback.format_exc())
    
    @bot.tree.command(name="positions", description="View your open stock positions")
    async def positions_command(interaction: discord.Interaction):
        """Display user's open positions"""
        await interaction.response.defer()
        
        try:
            user_id = str(interaction.user.id)
            positions = bot.db_manager.get_user_positions(user_id, status='open')
            
            if not positions:
                await interaction.followup.send(
                    "ℹ️ You don't have any open positions.\n\n"
                    "Use `/position add <ticker> <shares> <price>` to start tracking a position!"
                )
                return
            
            # Create embed
            embed = discord.Embed(
                title=f"💼 Your Open Positions ({len(positions)})",
                description="Currently tracking the following positions",
                color=discord.Color.blue()
            )
            
            # Add each position
            for i, pos in enumerate(positions[:10], 1):  # Limit to 10 for display
                # Get stock info
                session = bot.db_manager.Session()
                stock = session.query(Stock).filter_by(id=pos.stock_id).first()
                session.close()
                
                if not stock:
                    continue
                
                # Get current price
                from models.exit_signals import ExitSignalDetector
                detector = ExitSignalDetector(bot.db_manager)
                current_price = detector.get_current_price(stock.ticker)
                
                if current_price:
                    current_return = ((current_price - pos.entry_price) / pos.entry_price) * 100
                    current_pl = (current_price - pos.entry_price) * pos.shares
                    return_emoji = "🟢" if current_return > 0 else "🔴" if current_return < -3 else "🟡"
                else:
                    current_return = 0
                    current_pl = 0
                    return_emoji = "⚪"
                
                days_held = (datetime.now() - pos.entry_date).days
                
                # Check for pending signals
                session = bot.db_manager.Session()
                signals = session.query(ExitSignal)\
                    .filter_by(position_id=pos.id, status='pending')\
                    .count()
                session.close()
                
                signal_warning = f" ⚠️ {signals} signal(s)" if signals > 0 else ""
                
                embed.add_field(
                    name=f"{i}. {stock.ticker}{signal_warning}",
                    value=f"**Entry:** ${pos.entry_price:.2f} × {pos.shares:,.0f} shares\n"
                          f"**Current:** ${current_price:.2f} ({return_emoji} {current_return:+.2f}%)\n"
                          f"**P/L:** ${current_pl:+,.2f} | **Age:** {days_held}d\n"
                          f"**Stop:** ${pos.stop_loss_price:.2f} | **Target:** ${pos.profit_target_price:.2f}",
                    inline=False
                )
            
            if len(positions) > 10:
                embed.set_footer(text=f"Showing 10 of {len(positions)} positions")
            else:
                embed.set_footer(text="Use /exits to view active exit signals")
            
            await interaction.followup.send(embed=embed)
        
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}")
            logger.error(f"Error in positions_command: {e}")
            logger.error(traceback.format_exc())
    
    @bot.tree.command(name="exits", description="View active exit signals for your positions")
    async def exits_command(interaction: discord.Interaction):
        """Display active exit signals"""
        await interaction.response.defer()
        
        try:
            user_id = str(interaction.user.id)
            signals = bot.db_manager.get_active_exit_signals(discord_user_id=user_id)
            
            if not signals:
                await interaction.followup.send(
                    "✅ No active exit signals.\n\n"
                    "Your positions are looking good! The bot will alert you when exit conditions are met."
                )
                return
            
            # Group by urgency
            high = [(s, p, st) for s, p, st in signals if s.urgency == 'high']
            medium = [(s, p, st) for s, p, st in signals if s.urgency == 'medium']
            low = [(s, p, st) for s, p, st in signals if s.urgency == 'low']
            
            embed = discord.Embed(
                title=f"🚨 Active Exit Signals ({len(signals)})",
                description="Exit conditions detected for your positions",
                color=discord.Color.red() if high else discord.Color.gold()
            )
            
            # High urgency signals
            if high:
                high_text = ""
                for signal, position, stock in high[:3]:  # Limit to 3
                    emoji = "🛑" if signal.signal_type == 'stop_loss' else "⚠️"
                    high_text += f"{emoji} **{stock.ticker}** - {signal.signal_type.replace('_', ' ').title()}\n"
                    high_text += f"   {signal.reason}\n"
                    high_text += f"   Current: ${signal.current_price:.2f} ({signal.price_change_pct:+.1f}%)\n\n"
                
                embed.add_field(
                    name="🔴 HIGH URGENCY - Act Today",
                    value=high_text,
                    inline=False
                )
            
            # Medium urgency signals
            if medium:
                med_text = ""
                for signal, position, stock in medium[:3]:  # Limit to 3
                    emoji = "✅" if signal.signal_type == 'profit_target' else "📉"
                    med_text += f"{emoji} **{stock.ticker}** - {signal.signal_type.replace('_', ' ').title()}\n"
                    med_text += f"   {signal.reason}\n"
                    med_text += f"   Current: ${signal.current_price:.2f} ({signal.price_change_pct:+.1f}%)\n\n"
                
                embed.add_field(
                    name="🟡 MEDIUM URGENCY - Act This Week",
                    value=med_text,
                    inline=False
                )
            
            # Low urgency signals
            if low and not high and not medium:  # Only show if no higher priority
                low_text = ""
                for signal, position, stock in low[:2]:  # Limit to 2
                    low_text += f"🟢 **{stock.ticker}** - {signal.signal_type.replace('_', ' ').title()}\n"
                    low_text += f"   {signal.reason}\n\n"
                
                embed.add_field(
                    name="🟢 LOW URGENCY - Monitor",
                    value=low_text,
                    inline=False
                )
            
            embed.set_footer(text="Use /position close <ticker> <price> to exit a position")
            
            await interaction.followup.send(embed=embed)
        
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}")
            logger.error(f"Error in exits_command: {e}")
            logger.error(traceback.format_exc())
    
    @bot.tree.command(name="track", description="View your trading performance history")
    @app_commands.describe(days="Number of days to analyze (default: 365)")
    async def track_command(interaction: discord.Interaction, days: int = 365):
        """Display user's trading performance"""
        await interaction.response.defer()
        
        try:
            user_id = str(interaction.user.id)
            stats = bot.db_manager.get_user_trading_stats(user_id, days=days)
            
            if 'error' in stats:
                await interaction.followup.send(
                    f"ℹ️ {stats['error']}\n\n"
                    "Start tracking your trades:\n"
                    "1. Use `/position add` when you buy\n"
                    "2. Use `/position close` when you sell\n"
                    "3. Come back here to see your performance!"
                )
                return
            
            # Create embed
            overall_color = discord.Color.green() if stats['avg_return'] > 0 else discord.Color.red()
            
            embed = discord.Embed(
                title="📈 Your Trading Performance",
                description=f"Analysis of your last {days} days",
                color=overall_color
            )
            
            # Overall stats
            embed.add_field(
                name="📊 Overall",
                value=f"**Total Trades:** {stats['total_trades']}\n"
                      f"**Win Rate:** {stats['win_rate']:.1f}% ({stats['winners']}W / {stats['losers']}L)\n"
                      f"**Avg Return:** {stats['avg_return']:+.2f}%\n"
                      f"**Total P/L:** ${stats['total_profit_loss']:+,.2f}",
                inline=True
            )
            
            # Win/Loss breakdown
            embed.add_field(
                name="✅❌ Breakdown",
                value=f"**Avg Win:** +{stats['avg_win']:.2f}%\n"
                      f"**Avg Loss:** {stats['avg_loss']:.2f}%\n"
                      f"**Avg Hold:** {stats['avg_hold_days']:.0f} days",
                inline=True
            )
            
            # Best/worst trades
            best = stats['best_trade']
            worst = stats['worst_trade']
            
            session = bot.db_manager.Session()
            best_stock = session.query(Stock).filter_by(id=best.stock_id).first()
            worst_stock = session.query(Stock).filter_by(id=worst.stock_id).first()
            session.close()
            
            embed.add_field(
                name="🏆 Best Trade",
                value=f"**{best_stock.ticker if best_stock else 'Unknown'}**\n"
                      f"Return: +{best.return_pct:.2f}%\n"
                      f"Profit: ${best.profit_loss:+,.2f}",
                inline=True
            )
            
            embed.add_field(
                name="💀 Worst Trade",
                value=f"**{worst_stock.ticker if worst_stock else 'Unknown'}**\n"
                      f"Return: {worst.return_pct:.2f}%\n"
                      f"Loss: ${worst.profit_loss:+,.2f}",
                inline=True
            )
            
            # Interpretation
            if stats['win_rate'] >= 55 and stats['avg_return'] > 2:
                interpretation = "✅ Excellent performance! You're beating the market."
            elif stats['win_rate'] >= 50 and stats['avg_return'] > 0:
                interpretation = "✅ Good performance. Profitable trading strategy."
            elif stats['avg_return'] > 0:
                interpretation = "⚠️ Profitable but low win rate. Consider risk management."
            else:
                interpretation = "❌ Underperforming. Review your strategy and use exit signals."
            
            embed.add_field(
                name="💡 Assessment",
                value=interpretation,
                inline=False
            )
            
            embed.set_footer(text=f"Period: Last {days} days • Use /positions to view open trades")
            
            await interaction.followup.send(embed=embed)
        
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}")
            logger.error(f"Error in track_command: {e}")
            logger.error(traceback.format_exc())
    
    @bot.tree.command(name="help", description="Learn how to use SmartInvest Bot")
    async def help_command(interaction: discord.Interaction):
        """Display help information"""
        embed = discord.Embed(
            title="🤖 SmartInvest Bot - Help (REAL DATA MODE)",
            description="AI-powered stock recommendations using REAL market data from Yahoo Finance",
            color=discord.Color.blue()
        )
        
        commands_info = [
            ("📊 /daily", "View today's top 10 stock recommendations"),
            ("🔍 /stock <ticker>", "Get detailed analysis for any stock (price, indicators, sentiment)"),
            ("📉 /dip", "Find quality stocks on sale (buy the dip opportunities)"),
            ("📈 /backtest", "Run portfolio backtest (test momentum strategy)"),
            ("📉 /backtest-dip", "Backtest the dip-buying strategy"),
            ("📊 /backtest-stock <ticker>", "Backtest a specific stock's performance"),
            ("🏆 /performance", "View bot's recommendation performance stats"),
            ("🥇 /leaderboard", "See top/worst performing recommendations"),
            ("", ""),  # Separator
            ("💼 /position add/close", "Track your actual trades (add/close positions)"),
            ("📋 /positions", "View your open positions with live P/L"),
            ("🚨 /exits", "View active exit signals (profit targets, stop losses)"),
            ("📈 /track", "View your trading performance and stats"),
            ("", ""),  # Separator
            ("🔄 /refresh", "Force refresh recommendations with latest data"),
            ("❓ /help", "Show this help message")
        ]
        
        for cmd, desc in commands_info:
            embed.add_field(name=cmd, value=desc, inline=False)
        
        embed.add_field(
            name="📚 How It Works",
            value="The bot analyzes stocks using:\n"
                  "• **REAL price data** from Yahoo Finance\n"
                  "• **REAL technical indicators** (RSI, MACD, Bollinger Bands)\n"
                  "• **REAL fundamental analysis** (P/E, ROE, growth metrics)\n"
                  f"• **{'ML predictions (XGBoost)' if bot.has_ml_model else 'Rule-based scoring'}**\n"
                  f"• **{'News sentiment (FinBERT)' if bot.news_collector else 'No news data'}**\n\n"
                  "All recommendations use REAL market data!",
            inline=False
        )
        
        embed.add_field(
            name="💡 Tips",
            value="• Use `/daily` every morning for top picks\n"
                  "• Deep dive stocks with `/stock <ticker>`\n"
                  "• Find bargains with `/dip` (contrarian strategy)\n"
                  "• **Track your trades:** `/position add` when you buy\n"
                  "• **Exit smartly:** Check `/exits` for profit/stop signals\n"
                  "• **Monitor performance:** Use `/positions` and `/track`\n"
                  "• Validate strategies with `/backtest`, `/backtest-dip`\n"
                  "• Scores >= 80 indicate highest confidence",
            inline=False
        )
        
        embed.set_footer(text="SmartInvest Bot v2.0 | Powered by Real Data & AI")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    logger.info("Slash commands registered (REAL DATA MODE)")


def create_bot() -> SmartInvestBot:
    """
    Factory function to create and configure bot.
    
    Returns:
        Configured SmartInvestBot instance with REAL data integration
    """
    bot = SmartInvestBot()
    
    # Register all slash commands
    register_slash_commands(bot)
    
    return bot


def main():
    """Main entry point for the bot."""
    # Get Discord token from environment
    config = Config()
    
    if not config.DISCORD_BOT_TOKEN:
        print("❌ DISCORD_BOT_TOKEN not set in .env file")
        return
    
    # Create and run bot
    bot = create_bot()
    
    try:
        bot.run(config.DISCORD_BOT_TOKEN)
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    main()

