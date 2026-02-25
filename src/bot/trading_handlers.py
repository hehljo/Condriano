import logging
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from src.utils.config import T212_API_KEY, T212_API_SECRET, T212_MODE
from src.utils.database import add_transaction

logger = logging.getLogger(__name__)


def _get_broker():
    if not T212_API_KEY or not T212_API_SECRET:
        return None
    from src.broker.trading212 import Trading212
    return Trading212()


async def cmd_t212status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    broker = _get_broker()
    if not broker:
        await update.message.reply_text(
            "❌ Trading 212 nicht konfiguriert.\n"
            "T212_API_KEY in .env eintragen!"
        )
        return

    try:
        info = broker.get_account_info()
        cash = broker.get_account_cash()
        mode_emoji = "🧪" if T212_MODE == "paper" else "💰"

        await update.message.reply_text(
            f"{mode_emoji} <b>Trading 212 - {T212_MODE.upper()}</b>\n\n"
            f"Konto-ID: {info.get('id', '?')}\n"
            f"Währung: {info.get('currencyCode', '?')}\n"
            f"Frei: {cash.get('free', 0):.2f}€\n"
            f"Investiert: {cash.get('invested', 0):.2f}€\n"
            f"Gesamt: {cash.get('total', 0):.2f}€\n"
            f"P&L: {cash.get('ppl', 0):+.2f}€",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Verbindungsfehler: {e}")


async def cmd_t212positions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    broker = _get_broker()
    if not broker:
        await update.message.reply_text("❌ T212 nicht konfiguriert.")
        return

    try:
        positions = broker.get_positions()
        if not positions:
            await update.message.reply_text("📂 Keine offenen Positionen.")
            return

        text = "💼 <b>T212 Positionen</b>\n\n"
        for p in positions:
            ppl = p.get("ppl", 0)
            emoji = "🟢" if ppl >= 0 else "🔴"
            text += (
                f"<b>{p.get('ticker', '?')}</b>\n"
                f"  {p.get('quantity', 0):.4f} Stk @ {p.get('averagePrice', 0):.2f}€\n"
                f"  Aktuell: {p.get('currentPrice', 0):.2f}€\n"
                f"  {emoji} P&L: {ppl:+.2f}€ ({p.get('pplPercentage', 0):+.1f}%)\n\n"
            )

        summary = broker.get_portfolio_value()
        text += (
            f"{'='*25}\n"
            f"Investiert: {summary['invested']:.2f}€\n"
            f"Wert: {summary['market_value']:.2f}€\n"
            f"Cash: {summary['free_cash']:.2f}€\n"
            f"{'🟢' if summary['pnl'] >= 0 else '🔴'} Gesamt P&L: {summary['pnl']:+.2f}€ ({summary['pnl_pct']:+.1f}%)"
        )

        await update.message.reply_text(text, parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Fehler: {e}")


async def cmd_t212buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    broker = _get_broker()
    if not broker:
        await update.message.reply_text("❌ T212 nicht konfiguriert.")
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /t212buy TICKER ANZAHL [LIMIT_PREIS]\n\n"
            "Beispiele:\n"
            "/t212buy AAPL_US_EQ 0.5 (Market Order)\n"
            "/t212buy AAPL_US_EQ 0.5 170.00 (Limit Order)"
        )
        return

    ticker = context.args[0]
    try:
        quantity = float(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Ungültige Anzahl!")
        return

    try:
        if len(context.args) >= 3:
            limit_price = float(context.args[2])
            result = broker.limit_order(ticker, quantity, limit_price)
            order_type = f"Limit @ {limit_price}€"
        else:
            result = broker.market_order(ticker, quantity)
            order_type = "Market"

        fill_price = result.get("filledValue", result.get("limitPrice", 0))

        # In lokale DB eintragen
        if fill_price:
            add_transaction(ticker, "buy", quantity, fill_price)

        await update.message.reply_text(
            f"✅ <b>Kauforder platziert!</b>\n\n"
            f"Typ: {order_type}\n"
            f"Ticker: {ticker}\n"
            f"Anzahl: {quantity}\n"
            f"Order-ID: {result.get('id', '?')}\n"
            f"Status: {result.get('status', '?')}",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Order fehlgeschlagen: {e}")


async def cmd_t212sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    broker = _get_broker()
    if not broker:
        await update.message.reply_text("❌ T212 nicht konfiguriert.")
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /t212sell TICKER ANZAHL [LIMIT_PREIS]\n"
            "Beispiel: /t212sell AAPL_US_EQ 0.5"
        )
        return

    ticker = context.args[0]
    try:
        quantity = float(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Ungültige Anzahl!")
        return

    try:
        if len(context.args) >= 3:
            limit_price = float(context.args[2])
            result = broker.limit_order(ticker, -quantity, limit_price)
            order_type = f"Limit @ {limit_price}€"
        else:
            result = broker.market_order(ticker, -quantity)
            order_type = "Market"

        fill_price = result.get("filledValue", result.get("limitPrice", 0))
        if fill_price:
            add_transaction(ticker, "sell", quantity, abs(fill_price))

        await update.message.reply_text(
            f"✅ <b>Verkaufsorder platziert!</b>\n\n"
            f"Typ: {order_type}\n"
            f"Ticker: {ticker}\n"
            f"Anzahl: {quantity}\n"
            f"Order-ID: {result.get('id', '?')}\n"
            f"Status: {result.get('status', '?')}",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Order fehlgeschlagen: {e}")


async def cmd_t212orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    broker = _get_broker()
    if not broker:
        await update.message.reply_text("❌ T212 nicht konfiguriert.")
        return

    try:
        orders = broker.get_orders()
        if not orders:
            await update.message.reply_text("📂 Keine offenen Orders.")
            return

        text = "📋 <b>Offene Orders</b>\n\n"
        for o in orders:
            text += (
                f"#{o.get('id', '?')} | {o.get('type', '?')}\n"
                f"  {o.get('ticker', '?')} x{o.get('quantity', 0)}\n"
                f"  Status: {o.get('status', '?')}\n\n"
            )
        await update.message.reply_text(text, parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Fehler: {e}")


async def cmd_t212cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    broker = _get_broker()
    if not broker:
        await update.message.reply_text("❌ T212 nicht konfiguriert.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /t212cancel ORDER_ID")
        return

    try:
        order_id = int(context.args[0])
        broker.cancel_order(order_id)
        await update.message.reply_text(f"✅ Order #{order_id} storniert.")
    except Exception as e:
        await update.message.reply_text(f"❌ Fehler: {e}")


async def cmd_t212dividends(update: Update, context: ContextTypes.DEFAULT_TYPE):
    broker = _get_broker()
    if not broker:
        await update.message.reply_text("❌ T212 nicht konfiguriert.")
        return

    try:
        data = broker.get_dividends(limit=20)
        items = data.get("items", [])
        if not items:
            await update.message.reply_text("📂 Noch keine Dividenden erhalten.")
            return

        text = "💸 <b>Erhaltene Dividenden</b>\n\n"
        total = 0
        for d in items:
            amount = d.get("amount", 0)
            total += amount
            text += f"  {d.get('paidOn', '?')[:10]} | {d.get('ticker', '?')}: {amount:+.2f}€\n"

        text += f"\n<b>Gesamt: {total:.2f}€</b>"
        await update.message.reply_text(text, parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Fehler: {e}")


async def cmd_autotrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from src.strategies.auto_trader import load_config, save_config, scan_opportunities, format_opportunities_message

    config = load_config()

    if not context.args:
        mode_emoji = {"semi": "👀", "full": "⚡"}.get(config["mode"], "❓")
        await update.message.reply_text(
            f"🤖 <b>Auto-Trade Status</b>\n\n"
            f"Aktiv: {'✅' if config['enabled'] else '❌'}\n"
            f"Modus: {mode_emoji} {config['mode'].upper()}\n"
            f"Max pro Trade: {config['max_trade_eur']}€\n"
            f"Take Profit: +{config['take_profit_pct']}%\n"
            f"Stop Loss: {config['stop_loss_pct']}%\n"
            f"Max Trades/Tag: {config['max_trades_per_day']}\n"
            f"Cash Reserve: {config['min_cash_reserve']}€\n\n"
            f"<b>Commands:</b>\n"
            f"/autotrade semi - Halbautomatik (Alerts)\n"
            f"/autotrade full - Vollautomatik\n"
            f"/autotrade off - Deaktivieren\n"
            f"/autotrade scan - Jetzt scannen\n"
            f"/autotrade set KEY WERT - Einstellung ändern",
            parse_mode="HTML"
        )
        return

    action = context.args[0].lower()

    if action == "semi":
        config["enabled"] = True
        config["mode"] = "semi"
        save_config(config)
        await update.message.reply_text("👀 Auto-Trade: SEMI-Modus aktiv\nBot informiert, du entscheidest.")

    elif action == "full":
        config["enabled"] = True
        config["mode"] = "full"
        save_config(config)
        await update.message.reply_text(
            "⚡ Auto-Trade: VOLLAUTOMATIK aktiv!\n"
            f"Max {config['max_trade_eur']}€/Trade | Stop-Loss {config['stop_loss_pct']}% | Take-Profit +{config['take_profit_pct']}%"
        )

    elif action == "off":
        config["enabled"] = False
        save_config(config)
        await update.message.reply_text("❌ Auto-Trade deaktiviert.")

    elif action == "scan":
        await update.message.reply_text("⏳ Scanne Markt...")
        opportunities = scan_opportunities(config)
        msg = format_opportunities_message(opportunities)
        await update.message.reply_text(msg, parse_mode="HTML")

    elif action == "set" and len(context.args) >= 3:
        key = context.args[1]
        value = context.args[2]
        valid_keys = ["max_trade_eur", "min_cash_reserve", "take_profit_pct",
                      "stop_loss_pct", "max_trades_per_day", "buy_score_threshold",
                      "max_position_pct"]
        if key in valid_keys:
            try:
                config[key] = float(value)
                save_config(config)
                await update.message.reply_text(f"✅ {key} = {value}")
            except ValueError:
                await update.message.reply_text("❌ Ungültiger Wert!")
        else:
            await update.message.reply_text(f"❌ Unbekannt. Gültig: {', '.join(valid_keys)}")
    else:
        await update.message.reply_text("❓ Unbekannter Befehl. Schreib /autotrade für Hilfe.")


async def cmd_backtest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Backtesting des Score-Systems über historische Daten"""
    from src.backtest.engine import backtest_score_strategy, format_backtest_message, generate_backtest_chart

    # Parameter parsen
    period = "2y"
    initial_cash = 100.0
    tickers = None

    if context.args:
        for arg in context.args:
            if arg.endswith(("y", "mo", "d")):
                period = arg
            elif arg.replace(".", "").isdigit():
                initial_cash = float(arg)
            elif "," in arg:
                tickers = arg.upper().split(",")

    await update.message.reply_text(
        f"⏳ Backtest läuft... ({period}, {initial_cash}€)\n"
        "Das kann 10-30 Sekunden dauern."
    )

    try:
        result = backtest_score_strategy(
            tickers=tickers, period=period, initial_cash=initial_cash
        )
        msg = format_backtest_message(result)
        await update.message.reply_text(msg, parse_mode="HTML")

        # Chart generieren und senden
        if "error" not in result and result.get("portfolio_history"):
            try:
                chart_path = generate_backtest_chart(result)
                from src.bot.telegram_bot import bot
                await bot.send_photo(chart_path)
            except Exception as e:
                logger.error(f"Backtest Chart Fehler: {e}")

    except Exception as e:
        logger.error(f"Backtest Fehler: {e}")
        await update.message.reply_text(f"❌ Backtest fehlgeschlagen: {e}")


def register_trading_handlers(app):
    app.add_handler(CommandHandler("t212status", cmd_t212status))
    app.add_handler(CommandHandler("t212pos", cmd_t212positions))
    app.add_handler(CommandHandler("t212buy", cmd_t212buy))
    app.add_handler(CommandHandler("t212sell", cmd_t212sell))
    app.add_handler(CommandHandler("t212orders", cmd_t212orders))
    app.add_handler(CommandHandler("t212cancel", cmd_t212cancel))
    app.add_handler(CommandHandler("t212div", cmd_t212dividends))
    app.add_handler(CommandHandler("autotrade", cmd_autotrade))
    app.add_handler(CommandHandler("backtest", cmd_backtest))
