"""
Run this to see the REAL historical win rate of the strategy on a stock,
before trusting it with money.

    python run_backtest.py                 # defaults to RELIANCE.NS
    python run_backtest.py TCS.NS
    python run_backtest.py INFY.NS 60m      # optional: custom interval
"""
import sys
from config import BACKTEST_DAYS, TIMEFRAME
from main import fetch_data
from backtest import run_backtest


def main(symbol="RELIANCE.NS", interval=None):
    interval = interval or TIMEFRAME
    print(f"Fetching {BACKTEST_DAYS} days of {interval} data for {symbol}...")
    df = fetch_data(symbol, period=f"{BACKTEST_DAYS}d", interval=interval)

    if df.empty:
        print("No data fetched. Check the symbol or your internet connection.")
        return

    results = run_backtest(df)

    print(f"\n=== Backtest Results: {symbol} ({interval} candles, {BACKTEST_DAYS} days) ===")
    print(f"Total trades:   {results['total_trades']}")
    if results['total_trades'] > 0:
        print(f"Win rate:       {results['win_rate']}%")
        print(f"Profit factor:  {results['profit_factor']}  (>1 means gross wins exceed gross losses)")
        print(f"Total P&L:      {results['total_pnl']} points (before brokerage/taxes/slippage)")
    print("\nNote: this does not include brokerage, STT, slippage, or taxes — real")
    print("results will be lower. Test on several stocks and time periods before trusting it.")


if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else "RELIANCE.NS"
    interval = sys.argv[2] if len(sys.argv) > 2 else None
    main(symbol, interval)
