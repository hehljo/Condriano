import json
import logging
from pathlib import Path
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from src.market.reports import (
    build_morning_report,
    build_signal_report,
    build_vix_report,
    build_watchlist_report,
)
from src.utils.config import WATCHLIST_DEFAULT
from src.utils.database import (
    add_transaction, get_portfolio, get_transactions,
    get_signal_history, get_performance_history
)
from src.market.data import market_data

logger = logging.getLogger(__name__)
WATCHLIST_FILE = Path(__file__).parent.parent.parent / "data" / "watchlist.json"


def load_watchlist() -> list:
    if WATCHLIST_FILE.exists():
        with open(WATCHLIST_FILE) as f:
            return json.load(f)
    return list(WATCHLIST_DEFAULT)


def save_watchlist(watchlist: list):
    WATCHLIST_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(WATCHLIST_FILE, "w") as f:
        json.dump(watchlist, f, indent=2)


async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Report wird erstellt...")
    report = build_morning_report()
    await update.message.reply_text(report, parse_mode="HTML")


async def cmd_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Signale werden gescannt...")
    watchlist = load_watchlist()
    report = build_signal_report(watchlist)
    await update.message.reply_text(report, parse_mode="HTML")


async def cmd_vix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    report = build_vix_report()
    await update.message.reply_text(report, parse_mode="HTML")


async def cmd_watchlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    watchlist = load_watchlist()
    report = build_watchlist_report(watchlist)
    await update.message.reply_text(report, parse_mode="HTML")


async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /add TICKER (z.B. /add TSLA)")
        return

    ticker = context.args[0].upper()
    watchlist = load_watchlist()

    if ticker in watchlist:
        await update.message.reply_text(f"⚠️ {ticker} ist bereits in der Watchlist.")
        return

    watchlist.append(ticker)
    save_watchlist(watchlist)
    await update.message.reply_text(f"✅ <b>{ticker}</b> zur Watchlist hinzugefügt!", parse_mode="HTML")


async def cmd_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /remove TICKER (z.B. /remove TSLA)")
        return

    ticker = context.args[0].upper()
    watchlist = load_watchlist()

    if ticker not in watchlist:
        await update.message.reply_text(f"⚠️ {ticker} ist nicht in der Watchlist.")
        return

    watchlist.remove(ticker)
    save_watchlist(watchlist)
    await update.message.reply_text(f"🗑️ <b>{ticker}</b> von Watchlist entfernt.", parse_mode="HTML")


async def cmd_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text(
            "Usage: /buy TICKER ANZAHL PREIS\n"
            "Beispiel: /buy AAPL 0.5 180.50"
        )
        return

    ticker = context.args[0].upper()
    try:
        shares = float(context.args[1])
        price = float(context.args[2])
    except ValueError:
        await update.message.reply_text("❌ Ungültige Zahlen!")
        return

    add_transaction(ticker, "buy", shares, price)
    total = shares * price
    await update.message.reply_text(
        f"✅ <b>Kauf eingetragen!</b>\n\n"
        f"Aktie: {ticker}\n"
        f"Stück: {shares}\n"
        f"Preis: {price}€\n"
        f"Gesamt: {total:.2f}€",
        parse_mode="HTML"
    )


async def cmd_sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text("Usage: /sell TICKER ANZAHL PREIS")
        return

    ticker = context.args[0].upper()
    try:
        shares = float(context.args[1])
        price = float(context.args[2])
    except ValueError:
        await update.message.reply_text("❌ Ungültige Zahlen!")
        return

    add_transaction(ticker, "sell", shares, price)
    total = shares * price
    await update.message.reply_text(
        f"✅ <b>Verkauf eingetragen!</b>\n\n"
        f"Aktie: {ticker}\n"
        f"Stück: {shares}\n"
        f"Preis: {price}€\n"
        f"Erlös: {total:.2f}€",
        parse_mode="HTML"
    )


async def cmd_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    portfolio = get_portfolio()
    if not portfolio:
        await update.message.reply_text(
            "📂 <b>Portfolio ist leer</b>\n\n"
            "Trag Käufe ein mit:\n/buy TICKER ANZAHL PREIS",
            parse_mode="HTML"
        )
        return

    text = "💼 <b>Dein Portfolio</b>\n\n"
    total_invested = 0
    total_value = 0

    for pos in portfolio:
        current = market_data.get_price(pos["ticker"])
        current_price = current["price"] if current else pos["avg_buy_price"]
        value = pos["shares"] * current_price
        pnl = value - pos["total_invested"]
        pnl_pct = (pnl / pos["total_invested"] * 100) if pos["total_invested"] > 0 else 0
        emoji = "🟢" if pnl >= 0 else "🔴"

        text += (
            f"<b>{pos['ticker']}</b>\n"
            f"  {pos['shares']:.4f} Stk @ {pos['avg_buy_price']:.2f}€\n"
            f"  Aktuell: {current_price:.2f}€ | Wert: {value:.2f}€\n"
            f"  {emoji} P&L: {pnl:+.2f}€ ({pnl_pct:+.1f}%)\n\n"
        )
        total_invested += pos["total_invested"]
        total_value += value

    total_pnl = total_value - total_invested
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0
    emoji = "🟢" if total_pnl >= 0 else "🔴"

    text += (
        f"{'='*25}\n"
        f"<b>Gesamt:</b>\n"
        f"  Investiert: {total_invested:.2f}€\n"
        f"  Wert: {total_value:.2f}€\n"
        f"  {emoji} P&L: {total_pnl:+.2f}€ ({total_pnl_pct:+.1f}%)"
    )

    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ticker = context.args[0].upper() if context.args else None
    transactions = get_transactions(ticker, limit=20)

    if not transactions:
        await update.message.reply_text("📂 Keine Transaktionen gefunden.")
        return

    text = "📜 <b>Transaktionshistorie</b>\n\n"
    for t in transactions:
        emoji = "🟢" if t["action"] == "buy" else "🔴"
        text += f"{emoji} {t['timestamp'][:16]} | {t['action'].upper()} {t['ticker']} {t['shares']}x {t['price']}€ = {t['total']:.2f}€\n"

    await update.message.reply_text(text, parse_mode="HTML")


def register_handlers(app):
    app.add_handler(CommandHandler("report", cmd_report))
    app.add_handler(CommandHandler("signal", cmd_signal))
    app.add_handler(CommandHandler("vix", cmd_vix))
    app.add_handler(CommandHandler("watchlist", cmd_watchlist))
    app.add_handler(CommandHandler("add", cmd_add))
    app.add_handler(CommandHandler("remove", cmd_remove))
    app.add_handler(CommandHandler("buy", cmd_buy))
    app.add_handler(CommandHandler("sell", cmd_sell))
    app.add_handler(CommandHandler("portfolio", cmd_portfolio))
    app.add_handler(CommandHandler("history", cmd_history))
