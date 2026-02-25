import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent.parent / ".env")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

WATCHLIST_DEFAULT = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",  # US Tech
    "JNJ", "PG", "KO", "PEP", "MMM",            # US Dividenden
    "SAP.DE", "SIE.DE", "ALV.DE", "BAS.DE", "DTE.DE",  # DAX
    "VWRL.AS",  # Vanguard All-World ETF
    "EUNL.DE",  # iShares MSCI World
    "SXR8.DE",  # iShares S&P 500
]

INDICES = {
    "S&P 500": "^GSPC",
    "DAX": "^GDAXI",
    "NASDAQ": "^IXIC",
    "VIX": "^VIX",
    "Euro Stoxx 50": "^STOXX50E",
}

T212_API_KEY = os.getenv("T212_API_KEY", "")
T212_API_SECRET = os.getenv("T212_API_SECRET", "")
T212_MODE = os.getenv("T212_MODE", "live")  # "paper" oder "live"

REPORT_TIME_MORNING = "08:00"
REPORT_TIME_WEEKLY = "18:00"
