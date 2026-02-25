import sqlite3
import json
import logging
from datetime import datetime, date
from pathlib import Path

logger = logging.getLogger(__name__)
DB_PATH = Path(__file__).parent.parent.parent / "data" / "finanzbot.db"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS market_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL DEFAULT (datetime('now')),
            ticker TEXT NOT NULL,
            price REAL,
            change_pct REAL,
            volume INTEGER,
            rsi REAL,
            sma20 REAL,
            sma50 REAL,
            sma200 REAL,
            vix REAL,
            fear_greed INTEGER
        );

        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL DEFAULT (datetime('now')),
            ticker TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            price REAL,
            rsi REAL,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            shares REAL NOT NULL DEFAULT 0,
            avg_buy_price REAL NOT NULL DEFAULT 0,
            total_invested REAL NOT NULL DEFAULT 0,
            added_at TEXT NOT NULL DEFAULT (datetime('now')),
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL DEFAULT (datetime('now')),
            ticker TEXT NOT NULL,
            action TEXT NOT NULL,
            shares REAL NOT NULL,
            price REAL NOT NULL,
            total REAL NOT NULL,
            fees REAL DEFAULT 0,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS daily_performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            total_value REAL,
            total_invested REAL,
            total_return REAL,
            total_return_pct REAL,
            best_performer TEXT,
            worst_performer TEXT
        );

        CREATE TABLE IF NOT EXISTS alerts_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL DEFAULT (datetime('now')),
            alert_type TEXT NOT NULL,
            message TEXT NOT NULL,
            acknowledged INTEGER DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_snapshots_ticker ON market_snapshots(ticker);
        CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp ON market_snapshots(timestamp);
        CREATE INDEX IF NOT EXISTS idx_signals_ticker ON signals(ticker);
        CREATE INDEX IF NOT EXISTS idx_transactions_ticker ON transactions(ticker);
    """)

    conn.commit()
    conn.close()
    logger.info("Datenbank initialisiert")


def save_market_snapshot(ticker: str, price: float, change_pct: float,
                         volume: int = 0, rsi: float = None,
                         sma20: float = None, sma50: float = None,
                         sma200: float = None, vix: float = None,
                         fear_greed: int = None):
    conn = get_connection()
    conn.execute(
        """INSERT INTO market_snapshots
        (ticker, price, change_pct, volume, rsi, sma20, sma50, sma200, vix, fear_greed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (ticker, price, change_pct, volume, rsi, sma20, sma50, sma200, vix, fear_greed)
    )
    conn.commit()
    conn.close()


def save_signal(ticker: str, signal_type: str, price: float,
                rsi: float = None, description: str = ""):
    conn = get_connection()
    conn.execute(
        "INSERT INTO signals (ticker, signal_type, price, rsi, description) VALUES (?, ?, ?, ?, ?)",
        (ticker, signal_type, price, rsi, description)
    )
    conn.commit()
    conn.close()


def add_transaction(ticker: str, action: str, shares: float,
                    price: float, fees: float = 0, notes: str = ""):
    total = shares * price
    conn = get_connection()
    conn.execute(
        """INSERT INTO transactions (ticker, action, shares, price, total, fees, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (ticker, action, shares, price, total, fees, notes)
    )

    # Portfolio aktualisieren
    if action == "buy":
        existing = conn.execute(
            "SELECT * FROM portfolio WHERE ticker = ?", (ticker,)
        ).fetchone()

        if existing:
            new_shares = existing["shares"] + shares
            new_invested = existing["total_invested"] + total
            new_avg = new_invested / new_shares if new_shares > 0 else 0
            conn.execute(
                """UPDATE portfolio SET shares = ?, avg_buy_price = ?,
                total_invested = ? WHERE ticker = ?""",
                (new_shares, round(new_avg, 4), new_invested, ticker)
            )
        else:
            conn.execute(
                "INSERT INTO portfolio (ticker, shares, avg_buy_price, total_invested) VALUES (?, ?, ?, ?)",
                (ticker, shares, price, total)
            )
    elif action == "sell":
        existing = conn.execute(
            "SELECT * FROM portfolio WHERE ticker = ?", (ticker,)
        ).fetchone()
        if existing:
            new_shares = existing["shares"] - shares
            if new_shares <= 0:
                conn.execute("DELETE FROM portfolio WHERE ticker = ?", (ticker,))
            else:
                conn.execute(
                    "UPDATE portfolio SET shares = ? WHERE ticker = ?",
                    (new_shares, ticker)
                )

    conn.commit()
    conn.close()


def get_portfolio() -> list:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM portfolio ORDER BY total_invested DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_transactions(ticker: str = None, limit: int = 50) -> list:
    conn = get_connection()
    if ticker:
        rows = conn.execute(
            "SELECT * FROM transactions WHERE ticker = ? ORDER BY timestamp DESC LIMIT ?",
            (ticker, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM transactions ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_signal_history(days: int = 30) -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT * FROM signals
        WHERE timestamp >= datetime('now', ?)
        ORDER BY timestamp DESC""",
        (f"-{days} days",)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_price_history(ticker: str, days: int = 90) -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT * FROM market_snapshots
        WHERE ticker = ? AND timestamp >= datetime('now', ?)
        ORDER BY timestamp ASC""",
        (ticker, f"-{days} days")
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def log_alert(alert_type: str, message: str):
    conn = get_connection()
    conn.execute(
        "INSERT INTO alerts_log (alert_type, message) VALUES (?, ?)",
        (alert_type, message)
    )
    conn.commit()
    conn.close()


def save_daily_performance(total_value: float, total_invested: float,
                           best: str = "", worst: str = ""):
    total_return = total_value - total_invested
    total_return_pct = (total_return / total_invested * 100) if total_invested > 0 else 0

    conn = get_connection()
    today = date.today().isoformat()
    conn.execute(
        """INSERT OR REPLACE INTO daily_performance
        (date, total_value, total_invested, total_return, total_return_pct, best_performer, worst_performer)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (today, total_value, total_invested, round(total_return, 2),
         round(total_return_pct, 2), best, worst)
    )
    conn.commit()
    conn.close()


def get_performance_history(days: int = 90) -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT * FROM daily_performance
        WHERE date >= date('now', ?)
        ORDER BY date ASC""",
        (f"-{days} days",)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# DB beim Import initialisieren
init_db()
