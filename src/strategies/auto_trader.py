import json
import logging
from pathlib import Path
from datetime import datetime
from src.market.data import market_data
from src.utils.database import save_signal, log_alert, add_transaction

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "auto_trade.json"

DEFAULT_CONFIG = {
    "enabled": True,
    "mode": "semi",  # "semi" = fragt via Telegram, "full" = handelt autonom
    "max_trade_eur": 25.0,
    "min_cash_reserve": 5.0,
    "max_position_pct": 30.0,  # Max 30% des Portfolios in eine Aktie
    "buy_score_threshold": 50,  # Ab diesem Score wird gekauft
    "alert_score_threshold": 30,  # Ab hier Telegram Alert
    "take_profit_pct": 15.0,
    "stop_loss_pct": -10.0,
    "max_trades_per_day": 3,
    "watchlist": [
        "AAPL_US_EQ", "MSFT_US_EQ", "GOOGL_US_EQ", "AMZN_US_EQ", "NVDA_US_EQ",
        "JNJ_US_EQ", "PG_US_EQ", "KO_US_EQ",
        "SAPd_EQ", "SIEd_EQ", "ALVd_EQ",
        "EUNLd_EQ", "SXR8d_EQ",
    ],
    # Yahoo-Ticker Mapping für Analyse (T212 Ticker → Yahoo Ticker)
    "ticker_map": {
        "AAPL_US_EQ": "AAPL", "MSFT_US_EQ": "MSFT", "GOOGL_US_EQ": "GOOGL",
        "AMZN_US_EQ": "AMZN", "NVDA_US_EQ": "NVDA", "JNJ_US_EQ": "JNJ",
        "PG_US_EQ": "PG", "KO_US_EQ": "KO",
        "SAPd_EQ": "SAP.DE", "SIEd_EQ": "SIE.DE", "ALVd_EQ": "ALV.DE",
        "EUNLd_EQ": "EUNL.DE", "SXR8d_EQ": "SXR8.DE",
    },
    "score_weights": {
        "rsi_oversold_30": 30,
        "rsi_oversold_20": 40,
        "below_sma200": 20,
        "below_bollinger": 15,
        "vix_high": 15,
        "fear_extreme": 10,
    },
    "sell_weights": {
        "rsi_overbought_70": 30,
        "rsi_overbought_80": 40,
        "above_bollinger": 15,
        "take_profit": 50,
        "stop_loss": 100,
    },
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            saved = json.load(f)
            # Merge mit Defaults falls neue Keys dazukommen
            merged = {**DEFAULT_CONFIG, **saved}
            return merged
    return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def calculate_buy_score(ticker: str, config: dict = None) -> dict:
    if config is None:
        config = load_config()

    yahoo_ticker = config["ticker_map"].get(ticker, ticker)
    tech = market_data.get_technicals(yahoo_ticker)
    if not tech:
        return {"ticker": ticker, "score": 0, "reasons": ["Keine Daten"]}

    vix = market_data.get_vix()
    fg = market_data.get_fear_greed()
    weights = config["score_weights"]

    score = 0
    reasons = []

    # RSI
    if tech["rsi"] < 20:
        score += weights["rsi_oversold_20"]
        reasons.append(f"RSI {tech['rsi']} - extrem überverkauft (+{weights['rsi_oversold_20']})")
    elif tech["rsi"] < 30:
        score += weights["rsi_oversold_30"]
        reasons.append(f"RSI {tech['rsi']} - überverkauft (+{weights['rsi_oversold_30']})")

    # SMA200
    if tech["sma200"] and tech["price"] < tech["sma200"] * 0.98:
        score += weights["below_sma200"]
        reasons.append(f"Unter SMA200 ({tech['sma200']}) (+{weights['below_sma200']})")

    # Bollinger Band
    if tech["price"] < tech["bb_lower"]:
        score += weights["below_bollinger"]
        reasons.append(f"Unter Bollinger ({tech['bb_lower']}) (+{weights['below_bollinger']})")

    # VIX
    if vix and vix["price"] >= 25:
        score += weights["vix_high"]
        reasons.append(f"VIX {vix['price']} - Angst im Markt (+{weights['vix_high']})")

    # Fear & Greed
    if fg and fg["index"] < 25:
        score += weights["fear_extreme"]
        reasons.append(f"Fear&Greed {fg['index']} - extreme Angst (+{weights['fear_extreme']})")

    return {
        "ticker": ticker,
        "yahoo_ticker": yahoo_ticker,
        "score": score,
        "price": tech["price"],
        "rsi": tech["rsi"],
        "sma200": tech["sma200"],
        "reasons": reasons,
    }


def calculate_sell_score(ticker: str, position: dict, config: dict = None) -> dict:
    if config is None:
        config = load_config()

    yahoo_ticker = config["ticker_map"].get(ticker, ticker)
    tech = market_data.get_technicals(yahoo_ticker)
    if not tech:
        return {"ticker": ticker, "score": 0, "reasons": ["Keine Daten"]}

    weights = config["sell_weights"]
    score = 0
    reasons = []

    # P&L Check
    ppl_pct = position.get("pplPercentage", 0)

    if ppl_pct >= config["take_profit_pct"]:
        score += weights["take_profit"]
        reasons.append(f"Take Profit: {ppl_pct:+.1f}% (+{weights['take_profit']})")

    if ppl_pct <= config["stop_loss_pct"]:
        score += weights["stop_loss"]
        reasons.append(f"STOP LOSS: {ppl_pct:+.1f}% (+{weights['stop_loss']})")

    # RSI
    if tech["rsi"] > 80:
        score += weights["rsi_overbought_80"]
        reasons.append(f"RSI {tech['rsi']} - extrem überkauft (+{weights['rsi_overbought_80']})")
    elif tech["rsi"] > 70:
        score += weights["rsi_overbought_70"]
        reasons.append(f"RSI {tech['rsi']} - überkauft (+{weights['rsi_overbought_70']})")

    # Bollinger Band
    if tech["price"] > tech["bb_upper"]:
        score += weights["above_bollinger"]
        reasons.append(f"Über Bollinger ({tech['bb_upper']}) (+{weights['above_bollinger']})")

    return {
        "ticker": ticker,
        "score": score,
        "price": tech["price"],
        "ppl_pct": ppl_pct,
        "reasons": reasons,
    }


def scan_opportunities(config: dict = None) -> dict:
    """Scannt alle Watchlist-Aktien und gibt Kauf-/Verkaufsempfehlungen"""
    if config is None:
        config = load_config()

    buy_candidates = []
    sell_candidates = []
    alerts = []

    # Kaufsignale
    for ticker in config["watchlist"]:
        result = calculate_buy_score(ticker, config)
        if result["score"] >= config["buy_score_threshold"]:
            buy_candidates.append(result)
            save_signal(ticker, "auto_buy", result["price"], result.get("rsi"),
                       f"Score {result['score']}: {', '.join(result['reasons'])}")
        elif result["score"] >= config["alert_score_threshold"]:
            alerts.append(result)

    # Verkaufssignale (nur bestehende Positionen)
    try:
        from src.broker.trading212 import Trading212
        broker = Trading212()
        positions = broker.get_positions()
        for pos in positions:
            ticker = pos.get("ticker", "")
            result = calculate_sell_score(ticker, pos, config)
            if result["score"] >= 50:
                sell_candidates.append(result)
                save_signal(ticker, "auto_sell", result["price"], 0,
                           f"Score {result['score']}: {', '.join(result['reasons'])}")
    except Exception as e:
        logger.error(f"Verkaufssignal-Check Fehler: {e}")

    # Sortieren nach Score (höchster zuerst)
    buy_candidates.sort(key=lambda x: x["score"], reverse=True)
    sell_candidates.sort(key=lambda x: x["score"], reverse=True)

    return {
        "buy": buy_candidates,
        "sell": sell_candidates,
        "alerts": alerts,
        "timestamp": datetime.now().isoformat(),
    }


def calculate_position_size(price: float, config: dict = None) -> float:
    """Berechnet optimale Positionsgröße"""
    if config is None:
        config = load_config()

    try:
        from src.broker.trading212 import Trading212
        broker = Trading212()
        cash = broker.get_account_cash()
        free = cash.get("free", 0)
        total = cash.get("total", 0)

        # Reserve behalten
        available = free - config["min_cash_reserve"]
        if available <= 0:
            return 0

        # Max pro Trade
        trade_amount = min(available, config["max_trade_eur"])

        # Max Position als % des Portfolios
        if total > 0:
            max_for_ticker = total * (config["max_position_pct"] / 100)
            trade_amount = min(trade_amount, max_for_ticker)

        # Stückzahl berechnen (2 Dezimalstellen für T212)
        quantity = round(trade_amount / price, 2)
        return max(quantity, 0.01)  # Minimum 0.01

    except Exception as e:
        logger.error(f"Position Size Fehler: {e}")
        return 0


def execute_auto_trades(opportunities: dict, config: dict = None) -> list:
    """Führt Trades im Vollautomatik-Modus aus"""
    if config is None:
        config = load_config()

    if not config["enabled"] or config["mode"] != "full":
        return []

    executed = []

    try:
        from src.broker.trading212 import Trading212
        broker = Trading212()

        # Käufe
        for candidate in opportunities["buy"][:config["max_trades_per_day"]]:
            qty = calculate_position_size(candidate["price"], config)
            if qty > 0:
                try:
                    result = broker.market_order(candidate["ticker"], qty)
                    executed.append({
                        "action": "BUY",
                        "ticker": candidate["ticker"],
                        "quantity": qty,
                        "price": candidate["price"],
                        "score": candidate["score"],
                        "order_id": result.get("id"),
                        "reasons": candidate["reasons"],
                    })
                    log_alert("auto_buy", f"{candidate['ticker']} {qty} Stk @ {candidate['price']}")
                except Exception as e:
                    logger.error(f"Auto-Buy Fehler {candidate['ticker']}: {e}")

        # Verkäufe
        for candidate in opportunities["sell"]:
            try:
                positions = broker.get_positions()
                for pos in positions:
                    if pos.get("ticker") == candidate["ticker"]:
                        qty = pos.get("quantity", 0)
                        if qty > 0:
                            result = broker.market_order(candidate["ticker"], -qty)
                            executed.append({
                                "action": "SELL",
                                "ticker": candidate["ticker"],
                                "quantity": qty,
                                "price": candidate["price"],
                                "score": candidate["score"],
                                "order_id": result.get("id"),
                                "reasons": candidate["reasons"],
                            })
                            log_alert("auto_sell", f"{candidate['ticker']} {qty} Stk @ {candidate['price']}")
            except Exception as e:
                logger.error(f"Auto-Sell Fehler {candidate['ticker']}: {e}")

    except Exception as e:
        logger.error(f"Auto-Trade Fehler: {e}")

    return executed


def format_opportunities_message(opportunities: dict) -> str:
    """Formatiert Scan-Ergebnisse für Telegram"""
    text = f"🤖 <b>Auto-Trade Scan</b> ({opportunities['timestamp'][:16]})\n\n"

    if opportunities["buy"]:
        text += "🟢 <b>Kaufkandidaten:</b>\n"
        for c in opportunities["buy"]:
            text += f"  <b>{c['ticker']}</b> | Score: {c['score']} | {c['price']}€\n"
            for r in c["reasons"]:
                text += f"    → {r}\n"
            text += "\n"

    if opportunities["sell"]:
        text += "🔴 <b>Verkaufskandidaten:</b>\n"
        for c in opportunities["sell"]:
            text += f"  <b>{c['ticker']}</b> | Score: {c['score']} | P&L: {c.get('ppl_pct', 0):+.1f}%\n"
            for r in c["reasons"]:
                text += f"    → {r}\n"
            text += "\n"

    if opportunities["alerts"]:
        text += "👀 <b>Beobachten:</b>\n"
        for c in opportunities["alerts"]:
            text += f"  {c['ticker']} | Score: {c['score']} | RSI: {c.get('rsi', '?')}\n"

    if not opportunities["buy"] and not opportunities["sell"] and not opportunities["alerts"]:
        text += "😴 Keine Signale - Markt ist ruhig."

    return text


def format_trade_execution_message(executed: list) -> str:
    """Formatiert ausgeführte Trades für Telegram"""
    if not executed:
        return ""

    text = "⚡ <b>Auto-Trades ausgeführt:</b>\n\n"
    for t in executed:
        emoji = "🟢" if t["action"] == "BUY" else "🔴"
        text += (
            f"{emoji} <b>{t['action']}</b> {t['ticker']}\n"
            f"  {t['quantity']} Stk @ {t['price']}€ | Score: {t['score']}\n"
            f"  Order-ID: {t['order_id']}\n"
        )
        for r in t["reasons"]:
            text += f"  → {r}\n"
        text += "\n"

    return text


# Config beim ersten Import erstellen
if not CONFIG_PATH.exists():
    save_config(DEFAULT_CONFIG)
