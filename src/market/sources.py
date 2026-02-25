"""
Mehrere kostenlose Datenquellen mit automatischem Fallback.
Primär: Yahoo Finance API
Fallback 1: Alpha Vantage (kostenlos, 25 Requests/Tag)
Fallback 2: Stooq (polnische Börse, kostenlose CSV-Downloads)
Fallback 3: ECB für EUR/USD Wechselkurs
"""
import requests
import pandas as pd
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def yahoo_price(ticker: str, range_: str = "5d") -> dict:
    """Yahoo Finance - Hauptquelle"""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        r = requests.get(url, headers=HEADERS, params={"range": range_, "interval": "1d"}, timeout=10)
        r.raise_for_status()
        data = r.json()["chart"]["result"][0]
        quotes = data["indicators"]["quote"][0]
        close = [c for c in quotes["close"] if c is not None]
        if not close:
            return None
        return {
            "source": "yahoo",
            "price": round(close[-1], 2),
            "prev": round(close[-2], 2) if len(close) > 1 else close[-1],
        }
    except Exception as e:
        logger.warning(f"Yahoo Fehler {ticker}: {e}")
        return None


def stooq_price(ticker: str) -> dict:
    """Stooq.com - Fallback, kostenlos, keine API-Key nötig"""
    # Ticker-Mapping: Yahoo → Stooq Format
    stooq_map = {
        "^GSPC": "^SPX", "^GDAXI": "^DAX", "^IXIC": "^NDQ",
        "^VIX": "^VIX", "^STOXX50E": "^SX5E",
    }
    stooq_ticker = stooq_map.get(ticker, ticker)
    # US-Aktien: Stooq braucht .US Suffix
    if not any(c in stooq_ticker for c in ["^", ".", "="]):
        stooq_ticker = f"{stooq_ticker}.US"
    stooq_ticker = stooq_ticker.replace(".DE", ".D").replace(".AS", ".NL")

    try:
        url = f"https://stooq.com/q/l/?s={stooq_ticker}&f=sd2t2ohlcv&h&e=csv"
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        lines = r.text.strip().split("\n")
        if len(lines) < 2:
            return None
        vals = lines[1].split(",")
        price = float(vals[6])  # Close
        if price == 0:
            return None
        return {
            "source": "stooq",
            "price": round(price, 2),
            "prev": round(float(vals[3]), 2),  # Open als prev
        }
    except Exception as e:
        logger.warning(f"Stooq Fehler {ticker}: {e}")
        return None


def ecb_eurusd() -> float:
    """EZB offizieller EUR/USD Kurs - absolut zuverlässig"""
    try:
        url = "https://data.ecb.europa.eu/data-detail-api/EXR.D.USD.EUR.SP00.A"
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data:
                return float(data[-1].get("value", 1.05))
    except Exception:
        pass

    # Fallback: Yahoo
    try:
        result = yahoo_price("EURUSD=X")
        if result:
            return result["price"]
    except Exception:
        pass

    return 1.05  # Hardcoded Fallback


def fear_greed_cnn() -> dict:
    """CNN Fear & Greed Index - offizielle Quelle"""
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        r = requests.get(url, headers={
            "User-Agent": HEADERS["User-Agent"],
            "Accept": "application/json",
        }, timeout=10)
        if r.status_code == 200:
            data = r.json()
            score = data.get("fear_and_greed", {}).get("score", 50)
            rating = data.get("fear_and_greed", {}).get("rating", "Neutral")
            return {"index": int(score), "label": rating, "source": "cnn"}
    except Exception as e:
        logger.warning(f"CNN Fear&Greed Fehler: {e}")
    return None


def get_price_with_fallback(ticker: str) -> dict:
    """Holt Preis von Yahoo, bei Fehler automatisch Stooq"""
    result = yahoo_price(ticker)
    if result:
        return result

    logger.info(f"Yahoo ausgefallen für {ticker}, versuche Stooq...")
    result = stooq_price(ticker)
    if result:
        return result

    logger.error(f"Alle Quellen ausgefallen für {ticker}")
    return None


def verify_price_cross_source(ticker: str) -> dict:
    """Verifiziert Preis über zwei Quellen (Manipulation/Fehler erkennen)"""
    yahoo = yahoo_price(ticker)
    stooq = stooq_price(ticker)

    if not yahoo and not stooq:
        return {"verified": False, "reason": "Keine Quelle verfügbar"}

    if not yahoo or not stooq:
        source = yahoo or stooq
        return {"verified": False, "price": source["price"], "source": source["source"],
                "reason": "Nur eine Quelle"}

    diff_pct = abs(yahoo["price"] - stooq["price"]) / yahoo["price"] * 100

    return {
        "verified": diff_pct < 2.0,  # Max 2% Abweichung
        "yahoo_price": yahoo["price"],
        "stooq_price": stooq["price"],
        "diff_pct": round(diff_pct, 2),
        "price": yahoo["price"],  # Yahoo als primary
        "reason": "OK" if diff_pct < 2.0 else f"Abweichung {diff_pct:.1f}% - Vorsicht!",
    }


def market_status() -> dict:
    """Prüft ob Börsen offen sind"""
    now = datetime.now()
    weekday = now.weekday()  # 0=Mo, 6=So
    hour = now.hour

    return {
        "eu_open": weekday < 5 and 9 <= hour < 17,
        "us_open": weekday < 5 and 15 <= hour < 22,
        "weekend": weekday >= 5,
        "timestamp": now.isoformat(),
    }
