import asyncio
import logging
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from src.utils.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)


class FinanzBot:
    def __init__(self):
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
        self.chat_id = TELEGRAM_CHAT_ID
        self.app = None

    async def send_message(self, text: str, parse_mode: str = "HTML"):
        try:
            # Telegram limit: 4096 chars
            if len(text) > 4096:
                chunks = [text[i:i+4096] for i in range(0, len(text), 4096)]
                for chunk in chunks:
                    await self.bot.send_message(
                        chat_id=self.chat_id,
                        text=chunk,
                        parse_mode=parse_mode
                    )
            else:
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=text,
                    parse_mode=parse_mode
                )
            logger.info("Nachricht gesendet")
        except Exception as e:
            logger.error(f"Telegram Fehler: {e}")

    async def send_photo(self, photo_path: str, caption: str = ""):
        try:
            with open(photo_path, "rb") as f:
                await self.bot.send_photo(
                    chat_id=self.chat_id,
                    photo=f,
                    caption=caption,
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Foto-Fehler: {e}")

    def send_sync(self, text: str, parse_mode: str = "HTML"):
        asyncio.run(self.send_message(text, parse_mode))

    def send_photo_sync(self, photo_path: str, caption: str = ""):
        asyncio.run(self.send_photo(photo_path, caption))

    # --- Command Handlers ---

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🏦 <b>Finanz-Bot aktiv!</b>\n\n"
            "Dein automatischer Trading-Assistent.\n"
            "Schreib /help für alle Commands.",
            parse_mode="HTML"
        )

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Seite 1
        await update.message.reply_text(
            "📋 <b>ALLE COMMANDS - Übersicht</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"

            "📊 <b>MARKT & ANALYSE</b>\n\n"

            "/report\n"
            "  Kompletter Markt-Report: Indizes (DAX, S&P500,\n"
            "  NASDAQ), VIX, Fear&Greed, aktive Signale,\n"
            "  Smart-DCA Empfehlung. Kommt auch täglich 08:00.\n\n"

            "/vix\n"
            "  VIX (Angst-Index) + Fear & Greed Index.\n"
            "  Zeigt ob Markt in Panik oder Euphorie ist.\n"
            "  🟢 VIX<15 ruhig | 🟡 15-20 | 🟠 20-30 Kaufchance | 🔴 >30 Panik=Kaufen!\n\n"

            "/signal\n"
            "  Scannt alle Watchlist-Aktien auf Kauf-/Verkaufs-\n"
            "  signale (RSI, SMA200, Bollinger Bands).\n\n"

            "/watchlist\n"
            "  Zeigt alle beobachteten Aktien mit Live-Kursen.\n\n"

            "/add TICKER\n"
            "  Aktie zur Watchlist hinzufügen.\n"
            "  Beispiel: /add TSLA\n\n"

            "/remove TICKER\n"
            "  Aktie von Watchlist entfernen.\n"
            "  Beispiel: /remove MMM",
            parse_mode="HTML"
        )

        # Seite 2
        await update.message.reply_text(
            "🤖 <b>AUTO-TRADE SYSTEM</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"

            "/autotrade\n"
            "  Zeigt aktuellen Status des Auto-Traders.\n\n"

            "/autotrade semi\n"
            "  Halbautomatik: Bot erkennt Signale und schickt\n"
            "  dir eine Nachricht. Du entscheidest ob gekauft wird.\n\n"

            "/autotrade full\n"
            "  Vollautomatik: Bot kauft/verkauft selbstständig\n"
            "  nach dem Score-System. Stop-Loss & Take-Profit aktiv.\n\n"

            "/autotrade off\n"
            "  Auto-Trade komplett deaktivieren.\n\n"

            "/autotrade scan\n"
            "  Sofort alle Aktien scannen und Signale anzeigen.\n\n"

            "/autotrade set OPTION WERT\n"
            "  Einstellungen ändern. Optionen:\n"
            "  • max_trade_eur - Max € pro Trade (Standard: 25)\n"
            "  • stop_loss_pct - Stop-Loss in % (Standard: -10)\n"
            "  • take_profit_pct - Take-Profit in % (Standard: 15)\n"
            "  • max_trades_per_day - Max Trades/Tag (Standard: 3)\n"
            "  • min_cash_reserve - Cash-Reserve in € (Standard: 5)\n"
            "  • buy_score_threshold - Min Score zum Kaufen (Standard: 50)\n"
            "  • max_position_pct - Max % Portfolio pro Aktie (Standard: 30)\n"
            "  Beispiel: /autotrade set stop_loss_pct -15\n\n"

            "📈 <b>Score-System:</b>\n"
            "  RSI < 30 → +30 Pkt | RSI < 20 → +40 Pkt\n"
            "  Unter SMA200 → +20 | Unter Bollinger → +15\n"
            "  VIX > 25 → +15 | Fear&Greed < 25 → +10\n"
            "  <b>Score ≥ 50 = KAUFEN | 30-49 = ALERT</b>",
            parse_mode="HTML"
        )

        # Seite 3
        await update.message.reply_text(
            "💰 <b>TRADING 212 (Live-Broker)</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"

            "/t212status\n"
            "  Kontostand, freies Cash, investiertes Kapital,\n"
            "  Gesamtwert und P&L.\n\n"

            "/t212pos\n"
            "  Alle offenen Positionen mit Live-Kursen,\n"
            "  Stückzahl, Einstiegspreis und aktuellem P&L.\n\n"

            "/t212buy TICKER ANZAHL [LIMIT]\n"
            "  Aktie kaufen über Trading 212.\n"
            "  Market Order: /t212buy AAPL_US_EQ 0.5\n"
            "  Limit Order:  /t212buy AAPL_US_EQ 0.5 170.00\n"
            "  T212-Ticker enden auf _US_EQ, d_EQ etc.\n\n"

            "/t212sell TICKER ANZAHL [LIMIT]\n"
            "  Aktie verkaufen über Trading 212.\n"
            "  Beispiel: /t212sell AMZN_US_EQ 0.23\n\n"

            "/t212orders\n"
            "  Alle offenen/wartenden Orders anzeigen.\n\n"

            "/t212cancel ORDER_ID\n"
            "  Offene Order stornieren.\n"
            "  Beispiel: /t212cancel 47154105065\n\n"

            "/t212div\n"
            "  Alle erhaltenen Dividendenzahlungen anzeigen.\n\n"

            "💼 <b>PORTFOLIO (Lokales Tracking)</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"

            "/portfolio - Alle Positionen mit P&L\n"
            "/buy TICKER ANZAHL PREIS - Kauf manuell eintragen\n"
            "/sell TICKER ANZAHL PREIS - Verkauf eintragen\n"
            "/history [TICKER] - Transaktionshistorie\n\n"

            "⏰ <b>AUTOMATISCHE JOBS:</b>\n"
            "  08:00 Morgen-Report | 09:30 + 14:00 + 15:30 Auto-Trade\n"
            "  Alle 30 Min: Stop-Loss Check | So 18:00 Wochenreport",
            parse_mode="HTML"
        )

    def setup_handlers(self, app: Application):
        app.add_handler(CommandHandler("start", self.cmd_start))
        app.add_handler(CommandHandler("help", self.cmd_help))

    async def run_polling(self):
        self.app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self.setup_handlers(self.app)
        logger.info("Bot Polling gestartet...")
        await self.app.run_polling()


# Singleton
bot = FinanzBot()
