import requests
import logging
import base64
from typing import Optional
from src.utils.config import T212_API_KEY, T212_API_SECRET, T212_MODE

logger = logging.getLogger(__name__)

BASE_URLS = {
    "paper": "https://demo.trading212.com/api/v0",
    "live": "https://live.trading212.com/api/v0",
}


class Trading212:
    def __init__(self, api_key: str = None, api_secret: str = None, mode: str = None):
        self.api_key = api_key or T212_API_KEY
        self.api_secret = api_secret or T212_API_SECRET
        self.mode = mode or T212_MODE or "live"
        self.base_url = BASE_URLS[self.mode]
        self.session = requests.Session()

        # Basic Auth: base64(api_key:api_secret)
        creds = base64.b64encode(f"{self.api_key}:{self.api_secret}".encode()).decode()
        self.session.headers.update({
            "Authorization": f"Basic {creds}",
            "Content-Type": "application/json",
        })

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self.base_url}{path}"
        try:
            r = self.session.request(method, url, timeout=15, **kwargs)
            r.raise_for_status()
            return r.json() if r.text else {}
        except requests.exceptions.HTTPError as e:
            logger.error(f"T212 API Fehler {r.status_code}: {r.text}")
            raise
        except Exception as e:
            logger.error(f"T212 Request Fehler: {e}")
            raise

    # --- Account ---

    def get_account_cash(self) -> dict:
        return self._request("GET", "/equity/account/cash")

    def get_account_info(self) -> dict:
        return self._request("GET", "/equity/account/info")

    # --- Positionen ---

    def get_positions(self) -> list:
        return self._request("GET", "/equity/portfolio")

    def get_position(self, ticker: str) -> dict:
        return self._request("GET", f"/equity/portfolio/{ticker}")

    # --- Orders ---

    def market_order(self, ticker: str, quantity: float) -> dict:
        """Market Order. quantity > 0 = Buy, quantity < 0 = Sell"""
        return self._request("POST", "/equity/orders/market", json={
            "ticker": ticker,
            "quantity": quantity,
        })

    def limit_order(self, ticker: str, quantity: float, limit_price: float,
                    time_validity: str = "DAY") -> dict:
        return self._request("POST", "/equity/orders/limit", json={
            "ticker": ticker,
            "quantity": quantity,
            "limitPrice": limit_price,
            "timeValidity": time_validity,
        })

    def stop_order(self, ticker: str, quantity: float, stop_price: float,
                   time_validity: str = "DAY") -> dict:
        return self._request("POST", "/equity/orders/stop", json={
            "ticker": ticker,
            "quantity": quantity,
            "stopPrice": stop_price,
            "timeValidity": time_validity,
        })

    def stop_limit_order(self, ticker: str, quantity: float,
                         stop_price: float, limit_price: float,
                         time_validity: str = "DAY") -> dict:
        return self._request("POST", "/equity/orders/stop_limit", json={
            "ticker": ticker,
            "quantity": quantity,
            "stopPrice": stop_price,
            "limitPrice": limit_price,
            "timeValidity": time_validity,
        })

    def cancel_order(self, order_id: int) -> dict:
        return self._request("DELETE", f"/equity/orders/{order_id}")

    def get_orders(self) -> list:
        return self._request("GET", "/equity/orders")

    def get_order(self, order_id: int) -> dict:
        return self._request("GET", f"/equity/orders/{order_id}")

    # --- Instrumente ---

    def get_instruments(self) -> list:
        return self._request("GET", "/equity/metadata/instruments")

    def get_exchanges(self) -> list:
        return self._request("GET", "/equity/metadata/exchanges")

    # --- Historisch ---

    def get_order_history(self, limit: int = 50) -> dict:
        return self._request("GET", "/equity/history/orders", params={"limit": limit})

    def get_dividends(self, limit: int = 50) -> dict:
        return self._request("GET", "/equity/history/dividends", params={"limit": limit})

    def get_transactions(self, limit: int = 50) -> dict:
        return self._request("GET", "/equity/history/transactions", params={"limit": limit})

    # --- Pies (Auto-Invest) ---

    def get_pies(self) -> list:
        return self._request("GET", "/equity/pies")

    def create_pie(self, name: str, instruments: dict, dividend_action: str = "REINVEST") -> dict:
        """
        instruments: {"AAPL_US_EQ": 0.5, "MSFT_US_EQ": 0.5}  (Ticker: Gewichtung 0-1)
        """
        return self._request("POST", "/equity/pies", json={
            "name": name,
            "dividendCashAction": dividend_action,
            "instrumentShares": instruments,
        })

    def get_pie(self, pie_id: int) -> dict:
        return self._request("GET", f"/equity/pies/{pie_id}")

    def delete_pie(self, pie_id: int) -> dict:
        return self._request("DELETE", f"/equity/pies/{pie_id}")

    # --- Hilfsfunktionen ---

    def get_portfolio_value(self) -> dict:
        positions = self.get_positions()
        cash = self.get_account_cash()

        total_invested = sum(p.get("investedValue", 0) for p in positions)
        total_value = sum(p.get("currentPrice", 0) * p.get("quantity", 0) for p in positions)
        total_pnl = sum(p.get("ppl", 0) for p in positions)
        free_cash = cash.get("free", 0)

        return {
            "positions": len(positions),
            "invested": round(total_invested, 2),
            "market_value": round(total_value, 2),
            "pnl": round(total_pnl, 2),
            "pnl_pct": round((total_pnl / total_invested * 100) if total_invested > 0 else 0, 2),
            "free_cash": round(free_cash, 2),
            "total": round(total_value + free_cash, 2),
        }

    def is_connected(self) -> bool:
        try:
            self.get_account_info()
            return True
        except Exception:
            return False
