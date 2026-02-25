import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from src.bot.telegram_bot import bot
from src.market.reports import build_morning_report, build_signal_report
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
    logger.info("Morgen-Report wird gesendet...")
    report = build_morning_report()
    await bot.send_message(report)


async def job_signal_scan():
    logger.info("Signal-Scan läuft...")
    watchlist = load_watchlist()
    signals = market_data.scan_signals(watchlist)
    if signals:
        report = build_signal_report(watchlist)
        await bot.send_message("🚨 <b>Signal-Alert!</b>\n\n" + report)


async def job_market_alert():
    """Prüft auf starke Marktbewegungen (>2%) - VIX invertiert"""
    logger.info("Markt-Alert Check...")
    indices = market_data.get_indices()
    alerts = []
    for idx in indices:
        if abs(idx["change_pct"]) >= 2.0:
            name = idx["name"]

            # VIX ist invertiert: VIX fällt = gut, VIX steigt = schlecht
            if name == "VIX":
                if idx["change_pct"] > 0:
                    alerts.append(f"⚠️ VIX steigt {idx['change_pct']:+.2f}% - Angst nimmt zu")
                else:
                    alerts.append(f"😎 VIX fällt {idx['change_pct']:+.2f}% - Markt entspannt sich")
            else:
                direction = "📈 RALLYE" if idx["change_pct"] > 0 else "📉 CRASH"
                alerts.append(f"{direction} {name}: {idx['change_pct']:+.2f}%")

    if alerts:
        text = "🚨 <b>MARKT-ALARM!</b>\n\n" + "\n".join(alerts)
        vix = market_data.get_vix()
        if vix:
            text += f"\n\nVIX: {vix['price']} - {vix['signal']}"
        await bot.send_message(text)


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

    # Morgen-Report Mo-Fr 08:00
    scheduler.add_job(
        job_morning_report,
        CronTrigger(day_of_week="mon-fri", hour=8, minute=0),
        id="morning_report",
        name="Morgen-Report",
    )

    # Signal-Scan Mo-Fr 10:00 und 16:00
    scheduler.add_job(
        job_signal_scan,
        CronTrigger(day_of_week="mon-fri", hour=10, minute=0),
        id="signal_scan_morning",
        name="Signal-Scan Vormittag",
    )
    scheduler.add_job(
        job_signal_scan,
        CronTrigger(day_of_week="mon-fri", hour=16, minute=0),
        id="signal_scan_afternoon",
        name="Signal-Scan Nachmittag",
    )

    # Markt-Alert alle 30 Min während Handelszeiten
    scheduler.add_job(
        job_market_alert,
        CronTrigger(day_of_week="mon-fri", hour="9-17", minute="*/30"),
        id="market_alert",
        name="Markt-Alert",
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

    # Auto-Trade Scan Mo-Fr 09:30, 14:00, 15:30 (Börsenöffnung EU + US)
    scheduler.add_job(
        job_auto_trade,
        CronTrigger(day_of_week="mon-fri", hour=9, minute=30),
        id="auto_trade_eu_open",
        name="Auto-Trade EU Open",
    )
    scheduler.add_job(
        job_auto_trade,
        CronTrigger(day_of_week="mon-fri", hour=14, minute=0),
        id="auto_trade_pre_us",
        name="Auto-Trade Pre-US",
    )
    scheduler.add_job(
        job_auto_trade,
        CronTrigger(day_of_week="mon-fri", hour=15, minute=30),
        id="auto_trade_us_open",
        name="Auto-Trade US Open",
    )

    # Stop-Loss / Take-Profit Check alle 30 Min während Handelszeiten
    scheduler.add_job(
        job_stop_loss_check,
        CronTrigger(day_of_week="mon-fri", hour="9-22", minute="*/30"),
        id="stop_loss_check",
        name="Stop-Loss Check",
    )

    # Wöchentlicher Report Sonntag 18:00
    scheduler.add_job(
        job_weekly_summary,
        CronTrigger(day_of_week="sun", hour=18, minute=0),
        id="weekly_summary",
        name="Wöchentlicher Report",
    )

    return scheduler
