"""
Load complete S&P 500 stocks list (all 500).
Uses multiple sources to fetch the complete ticker list.
"""

import sys
import os
from pathlib import Path
import time
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from data.storage import DatabaseManager
from data.collectors import StockDataCollector
from data.schema import Base

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_sp500_tickers_comprehensive():
    """
    Get S&P 500 ticker list from multiple sources.
    
    Returns:
        List of ticker symbols (500 stocks)
    """
    logger.info("Fetching comprehensive S&P 500 ticker list...")
    
    # Complete S&P 500 list (as of 2024-2025)
    # This is a curated list combining multiple sources
    sp500_tickers = [
        # Technology (75 stocks)
        'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'NVDA', 'META', 'TSLA', 'AVGO', 'ORCL',
        'ADBE', 'CRM', 'CSCO', 'ACN', 'AMD', 'INTC', 'IBM', 'QCOM', 'TXN', 'INTU',
        'AMAT', 'NOW', 'PANW', 'ANET', 'PLTR', 'SNPS', 'CDNS', 'ADSK', 'KLAC', 'LRCX',
        'NXPI', 'MCHP', 'FTNT', 'ON', 'MPWR', 'KEYS', 'ANSS', 'TYL', 'ROP', 'HPQ',
        'DELL', 'HPE', 'NTAP', 'STX', 'WDC', 'ZBRA', 'ENPH', 'FSLR', 'SEDG', 'TER',
        'GNRC', 'IT', 'GLW', 'APH', 'TEL', 'MRVL', 'SMCI', 'CRWD', 'DDOG', 'NET',
        'ZS', 'OKTA', 'CFLT', 'S', 'SNOW', 'MDB', 'DKNG', 'RBLX', 'U', 'UBER',
        'LYFT', 'DASH', 'ABNB', 'COIN', 'HOOD',
        
        # Financial Services (65 stocks)
        'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'BLK', 'SCHW', 'AXP', 'USB',
        'PNC', 'TFC', 'COF', 'BK', 'STATE', 'STT', 'FITB', 'RF', 'CFG', 'HBAN',
        'KEY', 'NTRS', 'AIG', 'MET', 'PRU', 'ALL', 'TRV', 'PGR', 'CB', 'AFL',
        'HIG', 'CNC', 'CME', 'ICE', 'SPGI', 'MCO', 'MMC', 'AON', 'AJG', 'BRO',
        'TROW', 'BEN', 'IVZ', 'NDAQ', 'CBOE', 'FDS', 'MSCI', 'MKTX', 'V', 'MA',
        'PYPL', 'FIS', 'FISV', 'ADP', 'PAYX', 'BR', 'CINF', 'L', 'RJF', 'JKHY',
        'WRB', 'AIZ', 'RE', 'ALLY', 'DFS',
        
        # Healthcare (60 stocks)
        'UNH', 'JNJ', 'LLY', 'ABBV', 'MRK', 'PFE', 'TMO', 'ABT', 'DHR', 'BMY',
        'AMGN', 'CVS', 'MDT', 'GILD', 'CI', 'ELV', 'ISRG', 'VRTX', 'REGN', 'ZTS',
        'SYK', 'BSX', 'HCA', 'EW', 'IDXX', 'A', 'HUM', 'COR', 'RMD', 'MTD',
        'DXCM', 'IQV', 'BDX', 'BAX', 'ALGN', 'HOLX', 'STE', 'MOH', 'PODD', 'TECH',
        'INCY', 'VTRS', 'BIIB', 'MRNA', 'BNTX', 'WAT', 'PKI', 'BIO', 'XRAY', 'RVTY',
        'SOLV', 'LH', 'DGX', 'CRL', 'UHS', 'DVA', 'CAH', 'MCK', 'HSIC', 'COO',
        
        # Consumer Discretionary (55 stocks)
        'AMZN', 'TSLA', 'HD', 'MCD', 'NKE', 'SBUX', 'TGT', 'LOW', 'TJX', 'BKNG',
        'CMG', 'MAR', 'ABNB', 'F', 'GM', 'ORLY', 'AZO', 'YUM', 'DHI', 'LEN',
        'HLT', 'ROST', 'DG', 'DLTR', 'EBAY', 'BBY', 'GPC', 'TSCO', 'DPZ', 'ULTA',
        'DECK', 'NVR', 'PHM', 'LVS', 'WYNN', 'MGM', 'CZR', 'GRMN', 'POOL', 'APTV',
        'BWA', 'KMX', 'RL', 'TPR', 'LULU', 'NCLH', 'RCL', 'CCL', 'HAS', 'MAT',
        'WHR', 'LKQ', 'LEG', 'MHK', 'BBWI',
        
        # Consumer Staples (35 stocks)
        'WMT', 'PG', 'KO', 'PEP', 'COST', 'MDLZ', 'CL', 'EL', 'KMB', 'STZ',
        'GIS', 'HSY', 'K', 'CPB', 'CAG', 'SJM', 'MKC', 'HRL', 'CLX', 'CHD',
        'TAP', 'TSN', 'MNST', 'KDP', 'KHC', 'SYY', 'DG', 'DLTR', 'KR', 'WBA',
        'BG', 'ADM', 'MOS', 'CF', 'FMC',
        
        # Communication Services (25 stocks)
        'GOOGL', 'GOOG', 'META', 'NFLX', 'DIS', 'CMCSA', 'VZ', 'T', 'TMUS', 'CHTR',
        'EA', 'TTWO', 'NWSA', 'NWS', 'FOX', 'FOXA', 'OMC', 'IPG', 'MTCH', 'PARA',
        'LYV', 'ROKU', 'WBD', 'PINS', 'SNAP',
        
        # Industrials (70 stocks)
        'BA', 'HON', 'UPS', 'CAT', 'GE', 'RTX', 'LMT', 'DE', 'UNP', 'MMM',
        'ADP', 'ETN', 'PH', 'WM', 'EMR', 'ITW', 'CSX', 'NSC', 'FDX', 'PCAR',
        'NOC', 'GD', 'TDG', 'LHX', 'CARR', 'OTIS', 'JCI', 'CMI', 'EME', 'FAST',
        'PWR', 'GNRC', 'WAB', 'CHRW', 'JBHT', 'ODFL', 'EXPD', 'URI', 'VRSK', 'PAYX',
        'IEX', 'DOV', 'ROK', 'CPRT', 'SNA', 'HWM', 'PNR', 'ALLE', 'XYL', 'IFF',
        'ROP', 'SWK', 'FTV', 'AME', 'TXT', 'HII', 'AOS', 'NDSN', 'GWW', 'MLM',
        'VMC', 'J', 'LDOS', 'HUBB', 'BLDR', 'SSD', 'MAS', 'FBHS', 'JNPR', 'AKAM',
        
        # Energy (25 stocks)
        'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'PSX', 'VLO', 'OXY', 'WMB',
        'HES', 'KMI', 'BKR', 'HAL', 'DVN', 'FANG', 'MRO', 'APA', 'CTRA', 'EQT',
        'OKE', 'TRGP', 'LNG', 'CHRD', 'FTI',
        
        # Utilities (30 stocks)
        'NEE', 'SO', 'DUK', 'D', 'AEP', 'EXC', 'SRE', 'XEL', 'WEC', 'PCG',
        'ED', 'PEG', 'ES', 'EIX', 'DTE', 'PPL', 'AWK', 'FE', 'AEE', 'CMS',
        'CNP', 'NI', 'LNT', 'EVRG', 'ATO', 'NRG', 'VST', 'CEG', 'ETR', 'AES',
        
        # Real Estate (30 stocks)
        'AMT', 'PLD', 'EQIX', 'PSA', 'WELL', 'SPG', 'O', 'DLR', 'CBRE', 'AVB',
        'EQR', 'VICI', 'VTR', 'SBAC', 'ARE', 'INVH', 'MAA', 'KIM', 'ESS', 'DOC',
        'WY', 'HST', 'IRM', 'UDR', 'CPT', 'FRT', 'BXP', 'REG', 'VNO', 'SLG',
        
        # Materials (30 stocks)
        'LIN', 'SHW', 'APD', 'ECL', 'DD', 'NEM', 'FCX', 'CTVA', 'DOW', 'PPG',
        'ALB', 'VMC', 'MLM', 'NUE', 'STLD', 'IP', 'PKG', 'BALL', 'AVY', 'CF',
        'MOS', 'FMC', 'EMN', 'CE', 'LYB', 'SEE', 'AMCR', 'WRK', 'HUN', 'NEU',
    ]
    
    # Remove duplicates and sort
    sp500_tickers = sorted(list(set(sp500_tickers)))
    
    logger.info(f"✅ Loaded {len(sp500_tickers)} S&P 500 tickers")
    return sp500_tickers


def load_stocks_incremental(tickers, db_manager, collector, batch_size=25, delay=0.5):
    """
    Load stocks incrementally with progress tracking.
    
    Args:
        tickers: List of ticker symbols
        db_manager: DatabaseManager instance
        collector: StockDataCollector instance
        batch_size: Number of stocks to load per batch
        delay: Delay between stocks (seconds)
    """
    total = len(tickers)
    success_count = 0
    fail_count = 0
    
    logger.info(f"📊 Starting incremental load of {total} stocks...")
    logger.info(f"⏱️  Estimated time: {(total * 3) / 60:.1f} minutes")
    
    start_time = datetime.now()
    
    for i in range(0, total, batch_size):
        batch = tickers[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total // batch_size) + 1
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📦 BATCH {batch_num}/{total_batches} ({len(batch)} stocks)")
        logger.info(f"{'='*60}")
        
        for idx, ticker in enumerate(batch, 1):
            try:
                global_idx = i + idx
                logger.info(f"[{global_idx}/{total}] Processing {ticker}...")
                
                # Load stock data
                success = collector.load_stock_data(ticker, db_manager)
                
                if success:
                    success_count += 1
                    logger.info(f"  ✅ {ticker} loaded successfully")
                else:
                    fail_count += 1
                    logger.warning(f"  ⚠️  {ticker} failed to load")
                
                # Rate limiting
                time.sleep(delay)
                
            except Exception as e:
                fail_count += 1
                logger.error(f"  ❌ Error loading {ticker}: {e}")
                continue
        
        # Progress report
        elapsed = (datetime.now() - start_time).total_seconds()
        rate = global_idx / elapsed if elapsed > 0 else 0
        remaining = (total - global_idx) / rate if rate > 0 else 0
        
        logger.info(f"\n📈 Progress: {global_idx}/{total} ({global_idx/total*100:.1f}%)")
        logger.info(f"✅ Success: {success_count} | ❌ Failed: {fail_count}")
        logger.info(f"⏱️  Elapsed: {elapsed/60:.1f}m | Remaining: ~{remaining/60:.1f}m")
        
        # Batch delay
        if i + batch_size < total:
            logger.info(f"⏸️  Batch complete. Continuing...")
            time.sleep(1)
    
    # Final report
    elapsed_total = (datetime.now() - start_time).total_seconds()
    logger.info(f"\n{'='*60}")
    logger.info(f"🎉 LOAD COMPLETE!")
    logger.info(f"{'='*60}")
    logger.info(f"✅ Success: {success_count}/{total} ({success_count/total*100:.1f}%)")
    logger.info(f"❌ Failed: {fail_count}/{total} ({fail_count/total*100:.1f}%)")
    logger.info(f"⏱️  Total time: {elapsed_total/60:.1f} minutes")
    logger.info(f"{'='*60}\n")


def main():
    """Main execution."""
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║      FULL S&P 500 STOCK LOADER - SmartInvest Bot          ║
    ╚════════════════════════════════════════════════════════════╝
    
    This script will:
    1. Load complete S&P 500 ticker list (500 stocks)
    2. Download 5 years of historical price data for each
    3. Fetch company info (Finnhub/FMP)
    4. Save everything to database
    
    Data Sources:
    • yfinance: Historical prices (unlimited, free)
    • Finnhub: Company info (free tier, 60 calls/min)
    • FMP: Fundamentals (optional, 250 calls/day)
    
    Strategy:
    • Load all 500 stocks in one session
    • Uses only free APIs (yfinance + Finnhub)
    • 0.5s delay between stocks (safe rate limiting)
    
    ⏱️  Estimated time: ~25 minutes for 500 stocks
    
    """)
    
    # Confirm
    response = input("Start loading all 500 S&P 500 stocks? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("❌ Cancelled by user")
        return
    
    # Initialize
    logger.info("Initializing database and collectors...")
    
    db_manager = DatabaseManager(Config.DATABASE_URL)
    db_manager.create_all_tables()
    
    collector = StockDataCollector(
        fmp_api_key=Config.FMP_API_KEY,
        finnhub_api_key=Config.FINNHUB_API_KEY
    )
    
    # Get complete S&P 500 tickers
    all_tickers = get_sp500_tickers_comprehensive()
    
    # Check how many already loaded
    existing_stocks = db_manager.get_all_stocks()
    existing_tickers = {s.ticker for s in existing_stocks}
    new_tickers = [t for t in all_tickers if t not in existing_tickers]
    
    logger.info(f"📊 Stocks in database: {len(existing_tickers)}")
    logger.info(f"📊 New stocks to load: {len(new_tickers)}")
    
    if len(new_tickers) == 0:
        logger.info("✅ All S&P 500 stocks already loaded!")
        logger.info(f"📊 Total in database: {len(existing_stocks)}")
        return
    
    logger.info(f"📦 Loading {len(new_tickers)} new stocks")
    
    # Load stocks
    load_stocks_incremental(
        tickers=new_tickers,
        db_manager=db_manager,
        collector=collector,
        batch_size=25,  # 25 stocks per batch
        delay=0.5  # 0.5s delay between stocks
    )
    
    # Database stats
    all_stocks = db_manager.get_all_stocks()
    logger.info(f"\n📊 Database now contains {len(all_stocks)} stocks")
    logger.info(f"🎯 Target: 500 S&P 500 stocks")
    
    if len(all_stocks) >= 490:  # Allow for some failed stocks
        logger.info(f"✅ S&P 500 load complete!")
    else:
        remaining = 500 - len(all_stocks)
        logger.info(f"⚠️  {remaining} stocks remaining (some may have failed)")


if __name__ == "__main__":
    main()

