"""
Walks through historical bars one at a time (so the strategy only ever sees
data it would have actually had "at the time"), takes trades when the signal
fires, and exits at stop-loss or target. Reports real win rate / profit
factor — this is the honest number to look at, not a marketing claim.
"""
import pandas as pd
from signals import compute_indicators, generate_signal


def run_backtest(df):
    df = compute_indicators(df).dropna().reset_index(drop=True)
    trades = []
    position = None

    for i in range(30, len(df)):
        window = df.iloc[: i + 1]
        current = df.iloc[i]

        if position is None:
            sig = generate_signal(window)
            if sig['signal'] in ("BUY", "SELL") and sig['stop_loss'] is not None:
                position = {
                    "type": sig['signal'],
                    "entry_price": current['Close'],
                    "stop_loss": sig['stop_loss'],
                    "target": sig['target'],
                    "entry_index": i,
                }
        else:
            exit_trade = False
            pnl = 0
            if position['type'] == "BUY":
                if current['Low'] <= position['stop_loss']:
                    pnl = position['stop_loss'] - position['entry_price']
                    exit_trade = True
                elif current['High'] >= position['target']:
                    pnl = position['target'] - position['entry_price']
                    exit_trade = True
            else:  # SELL
                if current['High'] >= position['stop_loss']:
                    pnl = position['entry_price'] - position['stop_loss']
                    exit_trade = True
                elif current['Low'] <= position['target']:
                    pnl = position['entry_price'] - position['target']
                    exit_trade = True

            if exit_trade:
                trades.append({**position, "exit_index": i, "pnl": pnl})
                position = None

    return summarize_trades(trades)


def summarize_trades(trades):
    if not trades:
        return {"total_trades": 0, "win_rate": 0, "profit_factor": 0, "total_pnl": 0, "trades": []}

    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] <= 0]
    total_pnl = sum(t['pnl'] for t in trades)
    gross_profit = sum(t['pnl'] for t in wins)
    gross_loss = abs(sum(t['pnl'] for t in losses))

    return {
        "total_trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(100 * len(wins) / len(trades), 1),
        "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss > 0 else float('inf'),
        "total_pnl": round(total_pnl, 2),
        "trades": trades,
    }
