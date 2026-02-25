import asyncio
import logging
import signal
import sys
from telegram.ext import Application
from src.utils.config import TELEGRAM_BOT_TOKEN
from src.bot.telegram_bot import bot
from src.bot.handlers import register_handlers
from src.bot.trading_handlers import register_trading_handlers
from src.bot.scheduler import setup_scheduler
from src.utils.config import T212_API_KEY, T212_MODE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("data/finanzbot.log"),
    ],
)
logger = logging.getLogger(__name__)


async def startup_message():
    t212_status = ""
    if T212_API_KEY:
        t212_status = f"\n\n💰 Trading 212 ({T212_MODE.upper()}) verbunden!"
    else:
        t212_status = "\n\n⚠️ Trading 212 nicht konfiguriert (T212_API_KEY fehlt)"

    await bot.send_message(
        f"🚀 <b>Finanz-Bot gestartet!</b>\n\n"
        f"Automatische Reports & Alerts aktiv.{t212_status}\n"
        f"Schreib /help für alle Commands."
    )


async def main():
    logger.info("Finanz-Bot startet...")

    # Log-Verzeichnis
    from pathlib import Path
    Path("data").mkdir(exist_ok=True)

    # Telegram Bot Application
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Handlers registrieren
    bot.setup_handlers(app)
    register_handlers(app)
    register_trading_handlers(app)

    # Scheduler starten
    scheduler = setup_scheduler()
    scheduler.start()
    logger.info(f"Scheduler aktiv - {len(scheduler.get_jobs())} Jobs geplant")
    for job in scheduler.get_jobs():
        logger.info(f"  Job: {job.name} -> {job.trigger}")

    # Startup-Nachricht
    await app.initialize()
    await startup_message()

    # Bot starten
    await app.start()
    await app.updater.start_polling()

    logger.info("Bot läuft! Strg+C zum Beenden.")

    # Keep alive
    stop_event = asyncio.Event()

    def handle_signal(sig, frame):
        logger.info("Shutdown Signal empfangen...")
        stop_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    await stop_event.wait()

    # Cleanup
    logger.info("Shutdown...")
    scheduler.shutdown()
    await app.updater.stop()
    await app.stop()
    await app.shutdown()
    logger.info("Bot beendet.")


if __name__ == "__main__":
    asyncio.run(main())
