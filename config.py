# ==== EDIT THIS FILE TO CUSTOMIZE YOUR SETUP ====

# Stock universe to scan.
#
# Default: scan the official NIFTY LargeMidcap 250 list (top 100 large-cap
# plus 150 mid-cap NSE companies). Set UNIVERSE_MODE = "watchlist" if you
# only want to scan the custom WATCHLIST below.
UNIVERSE_MODE = "nifty_largemidcap250"
NIFTY_LARGEMIDCAP_250_URL = "https://nsearchives.nseindia.com/content/indices/ind_niftylargemidcap250list.csv"
MAX_STOCKS = 250
DOWNLOAD_BATCH_SIZE = 50

# Fallback/custom stocks to watch (NSE symbols need ".NS" suffix for Yahoo Finance)
WATCHLIST = [
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "SBIN.NS",
    "LT.NS",
    "AXISBANK.NS",
    "POLYCAB.NS",
    "NETWEB.NS",
    "INDIGO.NS",
]

# Candle size for swing analysis. Daily candles are the default because they
# are less noisy than intraday bars and fit free Yahoo data much better.
TIMEFRAME = "1d"

# How many days of history to pull for the dashboard. Swing indicators need
# more history so longer trend filters can warm up.
LOOKBACK_DAYS = 240

# How many days of history to pull for backtesting.
BACKTEST_DAYS = 365

# Risk management
CAPITAL = 100000            # total trading capital in Rupees
RISK_PER_TRADE_PCT = 1.0    # % of capital you're willing to lose per trade
RISK_REWARD_RATIO = 2.0     # target = risk * this ratio (used for stop-loss/target sizing)
