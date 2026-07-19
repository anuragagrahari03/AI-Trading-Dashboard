"""
Run this to see swing-trade signals for your watchlist.

    python main.py

Produces:
  - a table printed to your terminal
  - dashboard.html (open it in any browser)
"""
import io
import math
import urllib.request
from datetime import datetime
from html import escape

import pandas as pd

from config import (
    DOWNLOAD_BATCH_SIZE,
    LOOKBACK_DAYS,
    MAX_STOCKS,
    NIFTY_LARGEMIDCAP_250_URL,
    TIMEFRAME,
    UNIVERSE_MODE,
    WATCHLIST,
)
from signals import compute_indicators, generate_signal

SIGNAL_SORT_ORDER = {"BUY": 0, "HOLD": 1, "SELL": 2}


def fetch_data(symbol, period="5d", interval="5m"):
    import yfinance as yf
    df = yf.download(symbol, period=period, interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def normalize_nse_symbol(symbol):
    symbol = str(symbol).strip().upper()
    if not symbol:
        return ""
    return symbol if symbol.endswith(".NS") else f"{symbol}.NS"


def unique_symbols(symbols):
    seen = set()
    unique = []
    for symbol in symbols:
        symbol = normalize_nse_symbol(symbol)
        if symbol and symbol not in seen:
            unique.append(symbol)
            seen.add(symbol)
    return unique


def fetch_nifty_largemidcap250_symbols():
    request = urllib.request.Request(
        NIFTY_LARGEMIDCAP_250_URL,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        csv_text = response.read().decode("utf-8-sig")

    df = pd.read_csv(io.StringIO(csv_text))
    if "Symbol" not in df.columns:
        raise ValueError("NSE index CSV did not include a Symbol column")

    return unique_symbols(df["Symbol"].dropna().tolist())[:MAX_STOCKS]


def load_stock_universe():
    fallback = unique_symbols(WATCHLIST)[:MAX_STOCKS]

    if UNIVERSE_MODE == "watchlist":
        return fallback, "custom watchlist"

    if UNIVERSE_MODE != "nifty_largemidcap250":
        print(f"Unknown UNIVERSE_MODE={UNIVERSE_MODE!r}; using WATCHLIST instead.")
        return fallback, "custom watchlist"

    try:
        symbols = fetch_nifty_largemidcap250_symbols()
        if not symbols:
            raise ValueError("NSE index CSV returned no symbols")
        return symbols, "NIFTY LargeMidcap 250"
    except Exception as exc:
        print(f"Could not load NIFTY LargeMidcap 250 list: {exc}")
        print("Falling back to WATCHLIST from config.py.")
        return fallback, "custom watchlist"


def batched(items, size):
    size = max(1, size)
    for start in range(0, len(items), size):
        yield items[start:start + size]


def fetch_data_batch(symbols, period, interval):
    import yfinance as yf

    if len(symbols) == 1:
        return {symbols[0]: fetch_data(symbols[0], period=period, interval=interval)}

    data = yf.download(
        symbols,
        period=period,
        interval=interval,
        group_by="ticker",
        threads=True,
        progress=False,
    )
    if data.empty:
        return {}

    symbol_data = {}
    if isinstance(data.columns, pd.MultiIndex):
        level_0 = data.columns.get_level_values(0)
        level_1 = data.columns.get_level_values(1)

        for symbol in symbols:
            if symbol in level_0:
                df = data[symbol].copy()
            elif symbol in level_1:
                df = data.xs(symbol, axis=1, level=1).copy()
            else:
                continue

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(-1)
            symbol_data[symbol] = df.dropna(how="all")
    else:
        symbol_data[symbols[0]] = data.dropna(how="all")

    return symbol_data


def sort_dashboard(df):
    if df.empty:
        return df

    return (
        df.assign(_signal_order=df["Signal"].map(SIGNAL_SORT_ORDER).fillna(1))
        .sort_values(["_signal_order", "Confidence %", "Symbol"], ascending=[True, False, True])
        .drop(columns="_signal_order")
        .reset_index(drop=True)
    )


def build_dashboard():
    rows = []
    symbols, universe_name = load_stock_universe()
    print(f"Scanning {len(symbols)} stocks from {universe_name}...")

    for batch_number, batch in enumerate(batched(symbols, DOWNLOAD_BATCH_SIZE), start=1):
        print(f"Fetching batch {batch_number} ({len(batch)} stocks)...")
        batch_data = fetch_data_batch(batch, period=f"{LOOKBACK_DAYS}d", interval=TIMEFRAME)

        for symbol in batch:
            try:
                df = batch_data.get(symbol, pd.DataFrame())
                if df.empty or len(df) < 30:
                    print(f"Skipping {symbol}: not enough data returned")
                    continue
                df_ind = compute_indicators(df)
                sig = generate_signal(df_ind)
                rows.append({
                    "Symbol": symbol.replace(".NS", ""),
                    "Price": sig['price'],
                    "Signal": sig['signal'],
                    "Confidence %": sig['confidence'],
                    "Stop Loss": sig['stop_loss'],
                    "Target": sig['target'],
                    "Why": "; ".join(sig['reasons'][:3]),
                })
            except Exception as e:
                print(f"Error processing {symbol}: {e}")

    return sort_dashboard(pd.DataFrame(rows))


def save_html_report(df, filename="dashboard.html"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def row_class(signal):
        return {"BUY": "buy-row", "SELL": "sell-row", "HOLD": "hold-row"}.get(signal, "hold-row")

    table_rows = ""
    for _, r in df.iterrows():
        signal = r['Signal']
        signal_class = {"BUY": "signal-buy", "SELL": "signal-sell"}.get(signal, "signal-hold")

        def display(value):
            if value is None or (isinstance(value, float) and math.isnan(value)) or pd.isna(value):
                return ""
            return escape(str(value))

        table_rows += f"""
        <tr class="{row_class(r['Signal'])}">
            <td>{display(r['Symbol'])}</td>
            <td class="price">{display(r['Price'])}</td>
            <td><span class="signal-pill {signal_class}">{display(signal)}</span></td>
            <td>{display(r['Confidence %'])}%</td>
            <td>{display(r['Stop Loss'])}</td>
            <td>{display(r['Target'])}</td>
            <td class="why">{display(r['Why'])}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>NSE Swing Trade Dashboard</title>
<style>
    :root {{ --bg: #f2efe8; --panel: #fffdf8; --ink: #1f2a1f; --muted: #6f6a60; --line: #ddd4c4; --buy: #e1f0dd; --sell: #f7dfd8; --hold: #f3ead0; --accent: #163a2b; }}
    body {{ font-family: Georgia, "Times New Roman", serif; margin: 0; background: radial-gradient(circle at top, #f9f5eb 0%, var(--bg) 55%, #e9e2d5 100%); color: var(--ink); }}
    .page {{ max-width: 1180px; margin: 0 auto; padding: 32px 20px 48px; }}
    .hero {{ display: flex; justify-content: space-between; gap: 16px; align-items: end; margin-bottom: 24px; }}
    h1 {{ margin: 0; font-size: 38px; letter-spacing: -0.02em; }}
    .subtitle {{ color: var(--muted); margin-top: 8px; max-width: 760px; line-height: 1.5; }}
    .stamp {{ color: var(--muted); font-size: 14px; white-space: nowrap; }}
    .panel {{ background: color-mix(in srgb, var(--panel) 88%, white 12%); border: 1px solid var(--line); border-radius: 20px; box-shadow: 0 18px 50px rgba(53, 40, 19, 0.08); overflow: hidden; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 14px 16px; text-align: left; font-size: 14px; vertical-align: top; }}
    th {{ background: var(--accent); color: #f8f4ea; font-weight: 600; letter-spacing: 0.02em; }}
    .buy-row {{ background: var(--buy); }}
    .sell-row {{ background: var(--sell); }}
    .hold-row {{ background: var(--hold); }}
    .price {{ font-variant-numeric: tabular-nums; }}
    .signal-pill {{ display: inline-block; padding: 6px 10px; border-radius: 999px; font-size: 12px; font-weight: 700; letter-spacing: 0.04em; }}
    .signal-buy {{ background: #2d6a4f; color: #eff9f1; }}
    .signal-sell {{ background: #9c2f28; color: #fff3f1; }}
    .signal-hold {{ background: #7a6424; color: #fff9e8; }}
    .why {{ color: #4f4a40; font-size: 13px; max-width: 380px; line-height: 1.45; }}
    .disclaimer {{ margin-top: 18px; color: var(--muted); font-size: 13px; max-width: 760px; line-height: 1.5; }}
    @media (max-width: 900px) {{
        .hero {{ display: block; }}
        .stamp {{ margin-top: 12px; }}
        .panel {{ overflow-x: auto; }}
        table {{ min-width: 860px; }}
    }}
</style></head>
<body>
    <div class="page">
        <div class="hero">
            <div>
                <h1>NSE Swing Trade Dashboard</h1>
                <div class="subtitle">Daily swing setups based on trend alignment, breakout structure, RSI, MACD, and ATR-based risk levels.</div>
            </div>
            <div class="stamp">Generated: {ts}</div>
        </div>
        <div class="panel">
            <table>
                <tr><th>Symbol</th><th>Price</th><th>Signal</th><th>Confidence</th><th>Stop Loss</th><th>Target</th><th>Why</th></tr>
                {table_rows}
            </table>
        </div>
        <div class="disclaimer">
            Educational tool only, not financial advice. These are swing-trade candidates, not execution-grade alerts. Review the chart, upcoming earnings, liquidity, and your brokerage costs before taking any trade.
        </div>
    </div>
</body></html>"""

    with open(filename, "w") as f:
        f.write(html)
    print(f"\nDashboard saved to {filename} — open it in your browser.")


if __name__ == "__main__":
    print("Fetching data and computing swing-trade signals... (needs internet access)\n")
    df = build_dashboard()
    if df.empty:
        print("No signals generated. Check your internet connection and symbol list.")
    else:
        print(df.to_string(index=False))
        save_html_report(df)
