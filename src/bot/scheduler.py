import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from src.bot.telegram_bot import bot
from src.market.reports import build_morning_report, build_signal_report, build_portfolio_morning_report
from src.market.data import market_data
from src.bot.handlers import load_watchlist
from src.utils.database import (
    save_market_snapshot, save_signal, save_daily_performance,
    get_portfolio, log_alert
)

from src.strategies.auto_trader import (
    scan_opportunities, execute_auto_trades, load_config,
    format_opportunities_message, format_trade_execution_message,
)

logger = logging.getLogger(__name__)


async def job_auto_trade():
    """Auto-Trade: Scannt Markt und handelt bei starken Signalen"""
    logger.info("Auto-Trade Scan läuft...")
    config = load_config()

    if not config["enabled"]:
        return

    opportunities = scan_opportunities(config)

    # Im Semi-Modus: nur informieren
    if config["mode"] == "semi":
        if opportunities["buy"] or opportunities["sell"]:
            msg = format_opportunities_message(opportunities)
            msg += "\n\n💡 Modus: SEMI - Trades manuell ausführen"
            msg += "\n/autotrade full → Vollautomatik aktivieren"
            await bot.send_message(msg)
        return

    # Im Full-Modus: automatisch handeln
    if config["mode"] == "full":
        if opportunities["buy"] or opportunities["sell"]:
            # Erst informieren was passiert
            msg = format_opportunities_message(opportunities)
            await bot.send_message(msg)

            # Dann ausführen
            executed = execute_auto_trades(opportunities, config)
            if executed:
                exec_msg = format_trade_execution_message(executed)
                await bot.send_message(exec_msg)


async def job_stop_loss_check():
    """Prüft Stop-Loss und Take-Profit für alle Positionen"""
    logger.info("Stop-Loss Check...")
    config = load_config()
    if not config["enabled"]:
        return

    try:
        from src.broker.trading212 import Trading212
        broker = Trading212()
        positions = broker.get_positions()

        for pos in positions:
            ppl_pct = pos.get("pplPercentage", 0)
            ticker = pos.get("ticker", "")

            # Stop Loss
            if ppl_pct <= config["stop_loss_pct"]:
                if config["mode"] == "full":
                    qty = pos.get("quantity", 0)
                    broker.market_order(ticker, -qty)
                    await bot.send_message(
                        f"🛑 <b>STOP LOSS ausgelöst!</b>\n\n"
                        f"{ticker}: {ppl_pct:+.1f}%\n"
                        f"{qty} Stk verkauft."
                    )
                else:
                    await bot.send_message(
                        f"🛑 <b>STOP LOSS Warnung!</b>\n\n"
                        f"{ticker}: {ppl_pct:+.1f}%\n"
                        f"Verkaufen mit: /t212sell {ticker} {pos.get('quantity', 0)}"
                    )

            # Take Profit
            elif ppl_pct >= config["take_profit_pct"]:
                if config["mode"] == "full":
                    qty = pos.get("quantity", 0)
                    broker.market_order(ticker, -qty)
                    await bot.send_message(
                        f"🎯 <b>TAKE PROFIT!</b>\n\n"
                        f"{ticker}: {ppl_pct:+.1f}%\n"
                        f"{qty} Stk verkauft. Gewinn gesichert!"
                    )
                else:
                    await bot.send_message(
                        f"🎯 <b>Take Profit erreicht!</b>\n\n"
                        f"{ticker}: {ppl_pct:+.1f}%\n"
                        f"Verkaufen mit: /t212sell {ticker} {pos.get('quantity', 0)}"
                    )
    except Exception as e:
        logger.error(f"Stop-Loss Check Fehler: {e}")


async def job_morning_report():
    """Schlanker Morgen-Report: nur Portfolio + Performance"""
    logger.info("Portfolio Morgen-Report wird gesendet...")
    report = build_portfolio_morning_report()
    await bot.send_message(report)


async def job_signal_scan():
    logger.info("Signal-Scan läuft...")
    watchlist = load_watchlist()
    signals = market_data.scan_signals(watchlist)
    if signals:
        report = build_signal_report(watchlist)
        await bot.send_message("🚨 <b>Signal-Alert!</b>\n\n" + report)


async def job_market_alert():
    """Prüft Portfolio-Positionen auf starke Bewegungen"""
    logger.info("Portfolio-Alert Check...")

    try:
        from src.broker.trading212 import Trading212
        broker = Trading212()
        positions = broker.get_positions()

        if not positions:
            return

        alerts = []
        for pos in positions:
            ppl_pct = pos.get("pplPercentage", 0)
            ticker = pos.get("ticker", "")
            ppl = pos.get("ppl", 0)

            if ppl_pct >= 5.0:
                alerts.append(f"🟢 <b>{ticker}</b>: {ppl_pct:+.1f}% ({ppl:+.2f}€) - Läuft gut!")
            elif ppl_pct >= 10.0:
                alerts.append(f"🚀 <b>{ticker}</b>: {ppl_pct:+.1f}% ({ppl:+.2f}€) - Take-Profit prüfen!")
            elif ppl_pct <= -5.0:
                alerts.append(f"🔴 <b>{ticker}</b>: {ppl_pct:+.1f}% ({ppl:+.2f}€) - Beobachten!")
            elif ppl_pct <= -8.0:
                alerts.append(f"⚠️ <b>{ticker}</b>: {ppl_pct:+.1f}% ({ppl:+.2f}€) - Stop-Loss nahe!")

        if alerts:
            summary = broker.get_portfolio_value()
            emoji = "🟢" if summary["pnl"] >= 0 else "🔴"
            text = (
                f"📋 <b>Portfolio-Alert</b>\n\n"
                + "\n".join(alerts)
                + f"\n\n{emoji} Gesamt: {summary['pnl']:+.2f}€ ({summary['pnl_pct']:+.1f}%)"
            )
            await bot.send_message(text)

    except Exception as e:
        logger.error(f"Portfolio-Alert Fehler: {e}")


async def job_snapshot():
    """Speichert Marktdaten in DB für Statistik & Analyse"""
    logger.info("DB Snapshot wird gespeichert...")
    watchlist = load_watchlist()
    vix = market_data.get_vix()
    fg = market_data.get_fear_greed()

    for ticker in watchlist:
        tech = market_data.get_technicals(ticker)
        if tech:
            save_market_snapshot(
                ticker=ticker,
                price=tech["price"],
                change_pct=0,
                rsi=tech["rsi"],
                sma20=tech["sma20"],
                sma50=tech["sma50"],
                sma200=tech["sma200"],
                vix=vix["price"] if vix else None,
                fear_greed=fg["index"]
            )
            for sig in tech.get("signals", []):
                save_signal(ticker, "auto_scan", tech["price"], tech["rsi"], sig)


async def job_portfolio_snapshot():
    """Tägliche Portfolio-Performance in DB"""
    portfolio = get_portfolio()
    if not portfolio:
        return

    total_invested = 0
    total_value = 0
    best = ("", -999)
    worst = ("", 999)

    for pos in portfolio:
        current = market_data.get_price(pos["ticker"])
        if current:
            value = pos["shares"] * current["price"]
            pnl_pct = ((current["price"] / pos["avg_buy_price"]) - 1) * 100
            total_value += value
            total_invested += pos["total_invested"]
            if pnl_pct > best[1]:
                best = (pos["ticker"], pnl_pct)
            if pnl_pct < worst[1]:
                worst = (pos["ticker"], pnl_pct)

    if total_invested > 0:
        save_daily_performance(total_value, total_invested, best[0], worst[0])


async def job_weekly_summary():
    logger.info("Wöchentlicher Report...")
    report = build_morning_report()
    await bot.send_message("📊 <b>Wöchentlicher Überblick</b>\n\n" + report)


def setup_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="Europe/Berlin")

    # Morgen-Report täglich 08:00 (nur Portfolio + Performance)
    scheduler.add_job(
        job_morning_report,
        CronTrigger(hour=8, minute=0),
        id="morning_report",
        name="Portfolio Morgen-Report",
    )

    # Portfolio-Alert alle 30 Min während Handelszeiten
    # (nur eigene Positionen, keine allgemeinen Signale)
    scheduler.add_job(
        job_market_alert,
        CronTrigger(day_of_week="mon-fri", hour="9-17", minute="*/30"),
        id="market_alert",
        name="Portfolio-Alert",
    )

    # DB Snapshots Mo-Fr 12:00 und 18:00
    scheduler.add_job(
        job_snapshot,
        CronTrigger(day_of_week="mon-fri", hour=12, minute=0),
        id="snapshot_noon",
        name="DB Snapshot Mittag",
    )
    scheduler.add_job(
        job_snapshot,
        CronTrigger(day_of_week="mon-fri", hour=18, minute=0),
        id="snapshot_evening",
        name="DB Snapshot Abend",
    )

    # Portfolio-Performance täglich 18:30
    scheduler.add_job(
        job_portfolio_snapshot,
        CronTrigger(day_of_week="mon-fri", hour=18, minute=30),
        id="portfolio_snapshot",
        name="Portfolio Snapshot",
    )

    # Stop-Loss / Take-Profit Check alle 30 Min während Handelszeiten
    scheduler.add_job(
        job_stop_loss_check,
        CronTrigger(day_of_week="mon-fri", hour="9-22", minute="*/30"),
        id="stop_loss_check",
        name="Stop-Loss Check",
    )

    return scheduler
