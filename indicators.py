"""
Technical indicator functions. All take/return pandas Series or DataFrames.
Written from scratch with plain pandas so there are no tricky C-library
dependencies to install (like TA-Lib).
"""
import pandas as pd
import numpy as np


def ema(series, period):
    """Exponential moving average."""
    return series.ewm(span=period, adjust=False).mean()


def rsi(series, period=14):
    """Relative Strength Index (0-100). >70 = overbought, <30 = oversold."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_val = 100 - (100 / (1 + rs))
    return rsi_val.fillna(50)


def macd(series, fast=12, slow=26, signal=9):
    """Returns (macd_line, signal_line, histogram)."""
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def vwap(df):
    """Volume Weighted Average Price — resets conceptually each session,
    but for simplicity here it's a running VWAP over the loaded data."""
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    cum_vol = df['Volume'].cumsum()
    cum_vol_price = (typical_price * df['Volume']).cumsum()
    return cum_vol_price / cum_vol.replace(0, np.nan)


def bollinger_bands(series, period=20, num_std=2):
    """Returns (upper_band, middle_band/SMA, lower_band)."""
    sma = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = sma + num_std * std
    lower = sma - num_std * std
    return upper, sma, lower


def atr(df, period=14):
    """Average True Range — used for volatility-based stop-loss sizing."""
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(period).mean()
