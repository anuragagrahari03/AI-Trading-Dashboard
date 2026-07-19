# NSE Intraday Technical Analysis Dashboard

A rule-based technical analysis system for NSE stocks. It scans the official
NIFTY LargeMidcap 250 universe by default, computes standard indicators (EMA,
RSI, MACD, VWAP, Bollinger Bands, ATR), and produces BUY / SELL / HOLD signals
with a confidence score, suggested stop-loss, and target — shown in a dashboard
you can open in your browser.

**Read this whole file before you use it with real money.** It also includes
an honest backtester so you can see the strategy's real historical win rate
instead of trusting a marketing number.

---

## 1. Important expectations (please read)

No technical analysis system reliably hits 75%+ intraday accuracy — that
number doesn't survive contact with real markets, and anyone claiming it is
usually either overfitting a backtest or selling something. A realistic
starter strategy like this one might land somewhere around 40-55% win rate,
and still be profitable if winners are bigger than losers (that's what the
stop-loss/target ratio in `config.py` is for). **Run the backtester on
several stocks before you trust this with real money**, and start with paper
trading regardless of what the backtest shows.

This is an educational tool, not financial advice, and I'm not a financial
advisor. You are responsible for any trading decisions you make.

## 2. One-time setup

1. Install Python (3.10+) from [python.org](https://www.python.org/downloads/)
   if you don't have it. On Windows, tick "Add Python to PATH" during install.
2. Open a terminal (Command Prompt / PowerShell on Windows, Terminal on Mac)
   and navigate to this folder, e.g.:
   ```
   cd path/to/nse_intraday_agent
   ```
3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

## 3. Choose your stock universe

The dashboard scans the official NIFTY LargeMidcap 250 list by default. This
means it covers 250 NSE companies instead of only the sample watchlist.

Open `config.py` if you want to change this:

- Keep `UNIVERSE_MODE = "nifty_largemidcap250"` to scan the top-250 universe.
- Set `UNIVERSE_MODE = "watchlist"` to scan only `WATCHLIST`.
- Edit `WATCHLIST` to control the fallback/custom stocks. NSE symbols need a
  `.NS` suffix, e.g. `"WIPRO.NS"`.

You can also adjust the timeframe, batch size, and risk settings there.

## 4. See today's signals (the dashboard)

```
python main.py
```

This fetches recent intraday data, prints a signal table in the terminal,
and saves `dashboard.html` — open that file in any browser for a nicer view.
Results are sorted as BUY, then HOLD, then SELL, with stronger-confidence
signals first inside each group. Run it again anytime during market hours
(9:15 AM - 3:30 PM IST) to refresh.

**Data note:** this uses Yahoo Finance, which is free but can lag real-time
prices by a few minutes. Always confirm the actual price with your broker
before placing a trade — don't act on stale numbers.

## 5. Check the real win rate (the backtester)

Before trusting any signal, test it on history:

```
python run_backtest.py RELIANCE.NS
python run_backtest.py TCS.NS
python run_backtest.py INFY.NS
```

This shows total trades, win rate, and profit factor over the last ~60 days
of 5-minute candles (Yahoo's intraday history limit). A profit factor above
1.0 means the strategy made more on winners than it lost on losers, even if
the win rate itself is below 50%.

Test several stocks — a strategy that works on banking stocks may not work
on IT stocks, since they have different volatility patterns.

## 6. How the signal logic works

`signals.py` scores each stock on 5 factors and only signals BUY/SELL when
enough of them agree (this is what's called a "confluence" strategy — it
trades less often but with more confirmation than any single indicator
alone):

- EMA9/EMA21 crossover (trend direction)
- Price vs VWAP (who's in control today)
- RSI momentum and overbought/oversold levels
- MACD crossover
- Volume spike confirmation

Stop-loss and target are set using ATR (Average True Range), so they adapt
to each stock's actual volatility rather than using a fixed percentage.

Feel free to open `signals.py` and adjust the point thresholds or add your
own rules — you don't need to be a programmer to tweak the numbers, and I'm
happy to help you make changes if you come back with what you'd like
different.

## 7. Phase 2: moving to automated order placement (later)

When you're ready to automate:

1. Enable API access on your broker. Zerodha's Kite Connect
   (developer.kite.trade) is the most documented option and costs about
   ₹500/month; Upstox and Angel One offer free APIs.
2. Replace the "print to dashboard" step in `main.py` with an actual order
   placement call using your broker's SDK.
3. Add safeguards before going live: a max-loss-per-day circuit breaker, a
   max number of trades per day, and a manual kill switch.
4. Run it in your broker's paper-trading/sandbox mode (if available) for at
   least a few weeks before using real capital.

I can help you build this phase too when you get there — just come back
with which broker you've chosen.

## 8. File overview

| File | Purpose |
|---|---|
| `config.py` | Your watchlist and risk settings — edit this first |
| `indicators.py` | Math for EMA, RSI, MACD, VWAP, Bollinger Bands, ATR |
| `signals.py` | Combines indicators into BUY/SELL/HOLD signals |
| `backtest.py` | Simulates the strategy on historical data |
| `main.py` | Run this for today's live dashboard |
| `run_backtest.py` | Run this to check historical win rate |
