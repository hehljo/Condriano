import requests
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from src.utils.config import INDICES, WATCHLIST_DEFAULT

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def _yahoo_chart(ticker: str, range_: str = "5d", interval: str = "1d") -> pd.DataFrame:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    params = {"range": range_, "interval": interval}
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        quotes = result["indicators"]["quote"][0]

        df = pd.DataFrame({
            "Open": quotes["open"],
            "High": quotes["high"],
            "Low": quotes["low"],
            "Close": quotes["close"],
            "Volume": quotes["volume"],
        }, index=pd.to_datetime(timestamps, unit="s"))

        return df.dropna(subset=["Close"])
    except Exception as e:
        logger.error(f"Yahoo API Fehler {ticker}: {e}")
        return pd.DataFrame()


class MarketData:
    def __init__(self):
        self.cache = {}
        self.cache_time = {}
        self.cache_ttl = 300  # 5 Minuten

    def _get_cached(self, key: str):
        if key in self.cache:
            if (datetime.now() - self.cache_time[key]).seconds < self.cache_ttl:
                return self.cache[key]
        return None

    def _set_cache(self, key: str, data):
        self.cache[key] = data
        self.cache_time[key] = datetime.now()

    def get_price(self, ticker: str) -> dict:
        cached = self._get_cached(f"price_{ticker}")
        if cached:
            return cached

        try:
            hist = _yahoo_chart(ticker, "5d", "1d")
            if hist.empty:
                return None

            current = hist["Close"].iloc[-1]
            prev = hist["Close"].iloc[-2] if len(hist) > 1 else current
            change = current - prev
            change_pct = (change / prev) * 100

            result = {
                "ticker": ticker,
                "price": round(current, 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
                "high": round(hist["High"].iloc[-1], 2),
                "low": round(hist["Low"].iloc[-1], 2),
                "volume": int(hist["Volume"].iloc[-1]) if pd.notna(hist["Volume"].iloc[-1]) else 0,
            }
            self._set_cache(f"price_{ticker}", result)
            return result
        except Exception as e:
            logger.error(f"Fehler bei {ticker}: {e}")
            return None

    def get_indices(self) -> list:
        results = []
        for name, ticker in INDICES.items():
            data = self.get_price(ticker)
            if data:
                data["name"] = name
                results.append(data)
        return results

    def get_vix(self) -> dict:
        data = self.get_price("^VIX")
        if data:
            vix = data["price"]
            if vix < 15:
                data["signal"] = "🟢 Niedrig - Markt ruhig"
                data["action"] = "Normal investieren"
            elif vix < 20:
                data["signal"] = "🟡 Moderat - Leichte Unsicherheit"
                data["action"] = "Watchlist beobachten"
            elif vix < 30:
                data["signal"] = "🟠 Erhöht - Gute Kaufgelegenheiten möglich"
                data["action"] = "Nachkaufen prüfen!"
            else:
                data["signal"] = "🔴 Extrem - Panik im Markt!"
                data["action"] = "STARK nachkaufen (Smart-DCA)"
        return data

    def get_fear_greed(self) -> dict:
        try:
            hist = _yahoo_chart("^GSPC", "3mo", "1d")
            if hist.empty:
                return {"index": 50, "label": "Neutral"}

            current = hist["Close"].iloc[-1]
            sma50 = hist["Close"].rolling(50).mean().iloc[-1]
            returns = hist["Close"].pct_change().dropna()
            volatility = returns.std() * np.sqrt(252) * 100

            score = 50
            if current > sma50:
                score += 20
            else:
                score -= 20

            if volatility < 15:
                score += 15
            elif volatility > 25:
                score -= 15

            recent_return = ((current / hist["Close"].iloc[0]) - 1) * 100
            if recent_return > 5:
                score += 15
            elif recent_return < -5:
                score -= 15

            score = max(0, min(100, score))

            if score >= 75:
                label = "😎 Extreme Gier"
            elif score >= 55:
                label = "🙂 Gier"
            elif score >= 45:
                label = "😐 Neutral"
            elif score >= 25:
                label = "😰 Angst"
            else:
                label = "😱 Extreme Angst"

            return {"index": int(score), "label": label}
        except Exception as e:
            logger.error(f"Fear&Greed Fehler: {e}")
            return {"index": 50, "label": "Neutral"}

    def get_technicals(self, ticker: str) -> dict:
        try:
            hist = _yahoo_chart(ticker, "1y", "1d")
            if hist.empty or len(hist) < 50:
                return None

            close = hist["Close"]
            current = close.iloc[-1]

            sma20 = close.rolling(20).mean().iloc[-1]
            sma50 = close.rolling(50).mean().iloc[-1]
            sma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else None

            # RSI
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain.iloc[-1] / loss.iloc[-1] if loss.iloc[-1] != 0 else 0
            rsi = 100 - (100 / (1 + rs))

            # Bollinger Bands
            bb_sma = close.rolling(20).mean().iloc[-1]
            bb_std = close.rolling(20).std().iloc[-1]
            bb_upper = bb_sma + 2 * bb_std
            bb_lower = bb_sma - 2 * bb_std

            # Signale
            signals = []
            if rsi < 30:
                signals.append("🟢 RSI überverkauft - Kaufsignal")
            elif rsi > 70:
                signals.append("🔴 RSI überkauft - Verkaufssignal")

            if current < bb_lower:
                signals.append("🟢 Unter Bollinger Band - Kaufzone")
            elif current > bb_upper:
                signals.append("🔴 Über Bollinger Band - Verkaufszone")

            if sma200 and current < sma200 * 0.98:
                signals.append("🟢 >2% unter SMA200 - Mean Reversion möglich")

            return {
                "ticker": ticker,
                "price": round(current, 2),
                "rsi": round(rsi, 1),
                "sma20": round(sma20, 2),
                "sma50": round(sma50, 2),
                "sma200": round(sma200, 2) if sma200 else None,
                "bb_upper": round(bb_upper, 2),
                "bb_lower": round(bb_lower, 2),
                "signals": signals,
            }
        except Exception as e:
            logger.error(f"Technicals Fehler {ticker}: {e}")
            return None

    def scan_signals(self, watchlist: list = None) -> list:
        if watchlist is None:
            watchlist = WATCHLIST_DEFAULT

        signals = []
        for ticker in watchlist:
            tech = self.get_technicals(ticker)
            if tech and tech["signals"]:
                signals.append(tech)
        return signals


market_data = MarketData()
