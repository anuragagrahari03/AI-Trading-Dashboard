"""
Combines indicators into a single BUY / SELL / HOLD signal with a confidence
score and suggested stop-loss / target. This is a rule-based "confluence"
strategy: it only signals when several indicators agree, which cuts down on
false signals compared to using any single indicator alone.

IMPORTANT: this is a starting strategy, not a proven edge. Always run
backtest.py on a stock/timeframe before trusting its signals with real money.
"""
import pandas as pd
from indicators import ema, rsi, macd, vwap, bollinger_bands, atr


def compute_indicators(df):
    df = df.copy()
    df['ema20'] = ema(df['Close'], 20)
    df['ema50'] = ema(df['Close'], 50)
    df['ema200'] = ema(df['Close'], 200)
    df['rsi14'] = rsi(df['Close'], 14)
    df['macd_line'], df['macd_signal'], df['macd_hist'] = macd(df['Close'])
    df['vwap'] = vwap(df)
    df['bb_upper'], df['bb_mid'], df['bb_lower'] = bollinger_bands(df['Close'])
    df['atr14'] = atr(df, 14)
    df['vol_avg20'] = df['Volume'].rolling(20).mean()
    df['high_20'] = df['High'].rolling(20).max()
    df['low_20'] = df['Low'].rolling(20).min()
    return df


def generate_signal(df):
    """
    df must already have indicators computed (see compute_indicators).
    Returns a dict describing the signal on the LAST row of df.
    """
    if len(df) < 220:
        return {"signal": "HOLD", "confidence": 0, "price": None,
                "stop_loss": None, "target": None, "reasons": ["Not enough history for swing setup yet"]}

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    bullish_points = 0
    bearish_points = 0
    reasons = []

    # --- Trend: longer moving averages for swing direction ---
    if latest['ema20'] > latest['ema50'] > latest['ema200'] and prev['ema20'] <= prev['ema50']:
        bullish_points += 2
        reasons.append("EMA20 crossed above EMA50 inside a long-term uptrend")
    elif latest['ema20'] < latest['ema50'] < latest['ema200'] and prev['ema20'] >= prev['ema50']:
        bearish_points += 2
        reasons.append("EMA20 crossed below EMA50 inside a long-term downtrend")
    elif latest['ema20'] > latest['ema50'] > latest['ema200']:
        bullish_points += 2
        reasons.append("Price is in a strong swing uptrend (EMA20 > EMA50 > EMA200)")
    elif latest['ema20'] > latest['ema50']:
        bullish_points += 1
        reasons.append("Medium-term trend is up (EMA20 > EMA50)")
    elif latest['ema20'] < latest['ema50'] < latest['ema200']:
        bearish_points += 2
        reasons.append("Price is in a strong swing downtrend (EMA20 < EMA50 < EMA200)")
    elif latest['ema20'] < latest['ema50']:
        bearish_points += 1
        reasons.append("Medium-term trend is down (EMA20 < EMA50)")

    # --- Breakout / breakdown on closing basis ---
    if pd.notna(prev['high_20']) and latest['Close'] > prev['high_20']:
        bullish_points += 2
        reasons.append("Close broke above the prior 20-bar swing high")
    elif pd.notna(prev['low_20']) and latest['Close'] < prev['low_20']:
        bearish_points += 2
        reasons.append("Close broke below the prior 20-bar swing low")

    # --- Position inside Bollinger structure ---
    if pd.notna(latest['bb_mid']):
        if latest['Close'] > latest['bb_mid'] and latest['Close'] < latest['bb_upper']:
            bullish_points += 1
            reasons.append("Close is holding above the 20-day mean")
        elif latest['Close'] < latest['bb_mid'] and latest['Close'] > latest['bb_lower']:
            bearish_points += 1
            reasons.append("Close is holding below the 20-day mean")

    # --- RSI momentum for swing continuation / exhaustion ---
    if 50 < latest['rsi14'] < 68 and latest['rsi14'] > prev['rsi14']:
        bullish_points += 1
        reasons.append("RSI is rising in a healthy bullish range")
    elif 32 < latest['rsi14'] < 50 and latest['rsi14'] < prev['rsi14']:
        bearish_points += 1
        reasons.append("RSI is fading in a bearish range")
    if latest['rsi14'] > 72:
        bearish_points += 1
        reasons.append("RSI is stretched on the upside")
    elif latest['rsi14'] < 28:
        bullish_points += 1
        reasons.append("RSI is deeply oversold and bounce risk is rising")

    # --- MACD trend confirmation ---
    if latest['macd_line'] > latest['macd_signal'] and prev['macd_line'] <= prev['macd_signal']:
        bullish_points += 2
        reasons.append("MACD gave a fresh bullish crossover")
    elif latest['macd_line'] < latest['macd_signal'] and prev['macd_line'] >= prev['macd_signal']:
        bearish_points += 2
        reasons.append("MACD gave a fresh bearish crossover")
    elif latest['macd_hist'] > 0:
        bullish_points += 1
        reasons.append("MACD remains above its signal line")
    elif latest['macd_hist'] < 0:
        bearish_points += 1
        reasons.append("MACD remains below its signal line")

    # --- Volume confirmation on breakouts ---
    if pd.notna(latest['vol_avg20']) and latest['vol_avg20'] > 0:
        if latest['Volume'] > 1.2 * latest['vol_avg20']:
            if bullish_points > bearish_points:
                bullish_points += 1
                reasons.append("Volume expansion confirms the bullish setup")
            elif bearish_points > bullish_points:
                bearish_points += 1
                reasons.append("Volume expansion confirms the bearish setup")

    total = bullish_points + bearish_points
    confidence = 0 if total == 0 else round(100 * max(bullish_points, bearish_points) / total, 1)
    bullish_trend = latest['ema20'] > latest['ema50']
    bearish_trend = latest['ema20'] < latest['ema50']

    if bullish_trend and bullish_points >= bearish_points + 2 and bullish_points >= 4:
        signal = "BUY"
    elif bearish_trend and bearish_points >= bullish_points + 2 and bearish_points >= 4:
        signal = "SELL"
    else:
        signal = "HOLD"

    stop_loss = None
    target = None
    atr_val = latest['atr14'] if pd.notna(latest['atr14']) else 0

    if signal == "BUY" and atr_val > 0:
        stop_loss = round(latest['Close'] - 2.0 * atr_val, 2)
        target = round(latest['Close'] + 4.0 * atr_val, 2)
    elif signal == "SELL" and atr_val > 0:
        stop_loss = round(latest['Close'] + 2.0 * atr_val, 2)
        target = round(latest['Close'] - 4.0 * atr_val, 2)

    return {
        "signal": signal,
        "confidence": confidence,
        "price": round(latest['Close'], 2),
        "stop_loss": stop_loss,
        "target": target,
        "reasons": reasons,
    }
