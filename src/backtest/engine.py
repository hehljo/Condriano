"""
Backtesting-Engine: Testet das Score-System gegen historische Daten.
Simuliert Käufe/Verkäufe und berechnet Performance.
"""
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.market.data import _yahoo_chart
from src.strategies.auto_trader import DEFAULT_CONFIG

logger = logging.getLogger(__name__)


def _calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def _calculate_bollinger(close: pd.Series, period: int = 20) -> tuple:
    sma = close.rolling(period).mean()
    std = close.rolling(period).std()
    return sma - 2 * std, sma + 2 * std


def backtest_score_strategy(
    tickers: list = None,
    period: str = "2y",
    initial_cash: float = 100.0,
    config: dict = None,
) -> dict:
    """
    Backtestet das Score-System über historische Daten.
    Returns: Performance-Statistiken und Trade-Historie.
    """
    if config is None:
        config = DEFAULT_CONFIG.copy()
    if tickers is None:
        tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "JNJ", "KO", "PG"]

    weights = config["score_weights"]
    cash = initial_cash
    positions = {}  # {ticker: {"shares": x, "avg_price": y}}
    trades = []
    portfolio_history = []
    max_trade = config["max_trade_eur"]

    # Historische Daten laden
    all_data = {}
    for ticker in tickers:
        hist = _yahoo_chart(ticker, period, "1d")
        if hist.empty or len(hist) < 200:
            continue
        hist["RSI"] = _calculate_rsi(hist["Close"])
        hist["SMA200"] = hist["Close"].rolling(200).mean()
        hist["SMA50"] = hist["Close"].rolling(50).mean()
        hist["BB_Lower"], hist["BB_Upper"] = _calculate_bollinger(hist["Close"])
        all_data[ticker] = hist.dropna()

    if not all_data:
        return {"error": "Keine historischen Daten verfügbar"}

    # Gemeinsamer Zeitraum
    common_dates = None
    for ticker, df in all_data.items():
        dates = set(df.index.date)
        common_dates = dates if common_dates is None else common_dates & dates
    common_dates = sorted(common_dates)

    # Simulation Tag für Tag
    trades_today = 0
    last_trade_date = None

    for day in common_dates:
        day_str = str(day)

        # Reset täglicher Trade-Counter
        if last_trade_date != day:
            trades_today = 0
            last_trade_date = day

        for ticker, df in all_data.items():
            day_data = df[df.index.date == day]
            if day_data.empty:
                continue

            row = day_data.iloc[-1]
            price = row["Close"]
            rsi = row["RSI"]
            sma200 = row["SMA200"]
            bb_lower = row["BB_Lower"]
            bb_upper = row["BB_Upper"]

            # === KAUFSIGNAL Score ===
            buy_score = 0
            if rsi < 20:
                buy_score += weights["rsi_oversold_20"]
            elif rsi < 30:
                buy_score += weights["rsi_oversold_30"]
            if price < sma200 * 0.98:
                buy_score += weights["below_sma200"]
            if price < bb_lower:
                buy_score += weights["below_bollinger"]

            # Kaufen?
            if buy_score >= config["buy_score_threshold"] and trades_today < config["max_trades_per_day"]:
                available = min(cash, max_trade)
                if available >= 1.0:
                    shares = available / price
                    cash -= available

                    if ticker in positions:
                        old = positions[ticker]
                        total_shares = old["shares"] + shares
                        total_cost = old["shares"] * old["avg_price"] + available
                        positions[ticker] = {"shares": total_shares, "avg_price": total_cost / total_shares}
                    else:
                        positions[ticker] = {"shares": shares, "avg_price": price}

                    trades.append({
                        "date": day_str, "ticker": ticker, "action": "BUY",
                        "shares": round(shares, 4), "price": round(price, 2),
                        "score": buy_score, "cash_after": round(cash, 2),
                    })
                    trades_today += 1

            # === VERKAUFSSIGNAL ===
            if ticker in positions:
                pos = positions[ticker]
                pnl_pct = ((price / pos["avg_price"]) - 1) * 100

                sell = False
                sell_reason = ""

                if pnl_pct >= config["take_profit_pct"]:
                    sell = True
                    sell_reason = f"Take Profit {pnl_pct:+.1f}%"
                elif pnl_pct <= config["stop_loss_pct"]:
                    sell = True
                    sell_reason = f"Stop Loss {pnl_pct:+.1f}%"
                elif rsi > 70 and price > bb_upper:
                    sell = True
                    sell_reason = f"RSI {rsi:.0f} + über Bollinger"

                if sell:
                    proceeds = pos["shares"] * price
                    cash += proceeds
                    pnl = proceeds - (pos["shares"] * pos["avg_price"])
                    trades.append({
                        "date": day_str, "ticker": ticker, "action": "SELL",
                        "shares": round(pos["shares"], 4), "price": round(price, 2),
                        "pnl": round(pnl, 2), "reason": sell_reason,
                        "cash_after": round(cash, 2),
                    })
                    del positions[ticker]

        # Tageswert berechnen
        portfolio_value = cash
        for ticker, pos in positions.items():
            day_data = all_data[ticker][all_data[ticker].index.date == day]
            if not day_data.empty:
                portfolio_value += pos["shares"] * day_data.iloc[-1]["Close"]

        portfolio_history.append({"date": day_str, "value": round(portfolio_value, 2)})

    # Endwert berechnen
    final_value = cash
    open_positions = {}
    for ticker, pos in positions.items():
        last_price = all_data[ticker].iloc[-1]["Close"]
        value = pos["shares"] * last_price
        pnl_pct = ((last_price / pos["avg_price"]) - 1) * 100
        final_value += value
        open_positions[ticker] = {
            "shares": round(pos["shares"], 4),
            "avg_price": round(pos["avg_price"], 2),
            "current_price": round(last_price, 2),
            "value": round(value, 2),
            "pnl_pct": round(pnl_pct, 1),
        }

    # Statistiken
    total_return = final_value - initial_cash
    total_return_pct = (total_return / initial_cash) * 100
    buy_trades = [t for t in trades if t["action"] == "BUY"]
    sell_trades = [t for t in trades if t["action"] == "SELL"]
    winning_sells = [t for t in sell_trades if t.get("pnl", 0) > 0]
    losing_sells = [t for t in sell_trades if t.get("pnl", 0) <= 0]

    # Max Drawdown
    values = [h["value"] for h in portfolio_history]
    peak = values[0]
    max_drawdown = 0
    for v in values:
        peak = max(peak, v)
        drawdown = (v - peak) / peak * 100
        max_drawdown = min(max_drawdown, drawdown)

    # Buy & Hold Vergleich (gleiche Aktien, gleich gewichtet)
    bh_start = sum(
        all_data[t].iloc[0]["Close"] for t in all_data
    )
    bh_end = sum(
        all_data[t].iloc[-1]["Close"] for t in all_data
    )
    bh_return_pct = ((bh_end / bh_start) - 1) * 100

    days = len(common_dates)
    years = days / 252

    return {
        "initial_cash": initial_cash,
        "final_value": round(final_value, 2),
        "cash": round(cash, 2),
        "total_return": round(total_return, 2),
        "total_return_pct": round(total_return_pct, 1),
        "annualized_return_pct": round(total_return_pct / years, 1) if years > 0 else 0,
        "max_drawdown_pct": round(max_drawdown, 1),
        "total_trades": len(trades),
        "buy_trades": len(buy_trades),
        "sell_trades": len(sell_trades),
        "win_rate": round(len(winning_sells) / len(sell_trades) * 100, 1) if sell_trades else 0,
        "avg_win": round(np.mean([t["pnl"] for t in winning_sells]), 2) if winning_sells else 0,
        "avg_loss": round(np.mean([t["pnl"] for t in losing_sells]), 2) if losing_sells else 0,
        "buy_hold_return_pct": round(bh_return_pct, 1),
        "outperformance_pct": round(total_return_pct - bh_return_pct, 1),
        "period_days": days,
        "period_years": round(years, 1),
        "open_positions": open_positions,
        "trades": trades[-20:],  # Letzte 20 Trades
        "portfolio_history": portfolio_history,
    }


def format_backtest_message(result: dict) -> str:
    """Formatiert Backtesting-Ergebnis für Telegram"""
    if "error" in result:
        return f"❌ Backtest Fehler: {result['error']}"

    emoji = "🟢" if result["total_return"] >= 0 else "🔴"
    vs_bh = "📈 Besser" if result["outperformance_pct"] > 0 else "📉 Schlechter"

    text = (
        f"📊 <b>Backtest-Ergebnis (Simulation)</b>\n"
        f"⚠️ <i>Historische Simulation - nicht dein echtes Portfolio!</i>\n"
        f"{'='*28}\n\n"
        f"⏱️ Zeitraum: {result['period_years']} Jahre ({result['period_days']} Tage)\n"
        f"💶 Startkapital: {result['initial_cash']}€\n"
        f"{emoji} <b>Endwert: {result['final_value']}€</b>\n"
        f"{emoji} <b>Rendite: {result['total_return']:+.2f}€ ({result['total_return_pct']:+.1f}%)</b>\n"
        f"📅 Jährlich: {result['annualized_return_pct']:+.1f}%\n"
        f"📉 Max Drawdown: {result['max_drawdown_pct']:.1f}%\n\n"

        f"🔄 <b>Trades:</b>\n"
        f"  Käufe: {result['buy_trades']} | Verkäufe: {result['sell_trades']}\n"
        f"  Win-Rate: {result['win_rate']}%\n"
        f"  Ø Gewinn: {result['avg_win']:+.2f}€ | Ø Verlust: {result['avg_loss']:+.2f}€\n\n"

        f"📈 <b>vs. Buy & Hold:</b>\n"
        f"  B&H Rendite: {result['buy_hold_return_pct']:+.1f}%\n"
        f"  {vs_bh} als B&H: {result['outperformance_pct']:+.1f}%\n"
    )

    if result["open_positions"]:
        text += "\n📂 <b>Offene Positionen (Simulation):</b>\n"
        for ticker, pos in result["open_positions"].items():
            e = "🟢" if pos["pnl_pct"] >= 0 else "🔴"
            text += f"  {e} {ticker}: {pos['value']}€ ({pos['pnl_pct']:+.1f}%)\n"

    return text


def generate_backtest_chart(result: dict) -> str:
    """Erzeugt Portfolio-Chart als PNG, gibt Dateipfad zurück"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from pathlib import Path

    history = result["portfolio_history"]
    dates = [h["date"] for h in history]
    values = [h["value"] for h in history]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(range(len(values)), values, color="#2196F3", linewidth=1.5)
    ax.fill_between(range(len(values)), values, alpha=0.1, color="#2196F3")
    ax.axhline(y=result["initial_cash"], color="gray", linestyle="--", alpha=0.5, label="Startkapital")

    # X-Achse: nur einige Datum-Labels
    step = max(len(dates) // 6, 1)
    ax.set_xticks(range(0, len(dates), step))
    ax.set_xticklabels([dates[i] for i in range(0, len(dates), step)], rotation=45, fontsize=8)

    ax.set_title(f"Backtest: {result['initial_cash']}€ → {result['final_value']}€ ({result['total_return_pct']:+.1f}%)", fontsize=12)
    ax.set_ylabel("Portfolio-Wert (€)")
    ax.legend()
    ax.grid(alpha=0.3)
    plt.tight_layout()

    chart_path = str(Path(__file__).parent.parent.parent / "data" / "backtest_chart.png")
    plt.savefig(chart_path, dpi=150)
    plt.close()
    return chart_path
