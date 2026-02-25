import logging
from datetime import datetime
from src.market.data import market_data

logger = logging.getLogger(__name__)


def format_change(change_pct: float) -> str:
    if change_pct > 0:
        return f"🟢 +{change_pct}%"
    elif change_pct < 0:
        return f"🔴 {change_pct}%"
    return f"⚪ {change_pct}%"


def build_morning_report() -> str:
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    # Indizes
    indices = market_data.get_indices()
    idx_text = ""
    for idx in indices:
        idx_text += f"  {idx['name']}: <b>{idx['price']:,.2f}</b> {format_change(idx['change_pct'])}\n"

    # VIX
    vix = market_data.get_vix()
    vix_text = ""
    if vix:
        vix_text = (
            f"\n📊 <b>VIX (Angst-Index):</b> {vix['price']}\n"
            f"  {vix['signal']}\n"
            f"  Aktion: {vix['action']}\n"
        )

    # Fear & Greed
    fg = market_data.get_fear_greed()
    fg_text = f"\n🧠 <b>Fear & Greed:</b> {fg['index']}/100 - {fg['label']}\n"

    # Signale
    signals = market_data.scan_signals()
    sig_text = ""
    if signals:
        sig_text = "\n🎯 <b>Aktuelle Signale:</b>\n"
        for s in signals:
            sig_text += f"  <b>{s['ticker']}</b> ({s['price']}€ | RSI: {s['rsi']})\n"
            for sig in s["signals"]:
                sig_text += f"    {sig}\n"

    # Smart-DCA Empfehlung
    dca_text = ""
    if vix and vix["price"] >= 25:
        dca_text = (
            "\n💰 <b>Smart-DCA Empfehlung:</b>\n"
            "  VIX ist hoch - JETZT mehr investieren!\n"
            "  Empfehlung: 150% des normalen Sparplan-Betrags\n"
        )
    elif vix and vix["price"] >= 20:
        dca_text = (
            "\n💰 <b>Smart-DCA Empfehlung:</b>\n"
            "  VIX moderat erhöht - 120% des normalen Betrags\n"
        )

    report = (
        f"📈 <b>Morgen-Report {now}</b>\n"
        f"{'='*30}\n\n"
        f"🌍 <b>Indizes:</b>\n{idx_text}"
        f"{vix_text}"
        f"{fg_text}"
        f"{sig_text}"
        f"{dca_text}"
        f"\n{'='*30}\n"
        f"💡 /signal für Details | /watchlist für Watchlist"
    )
    return report


def build_signal_report(watchlist: list = None) -> str:
    signals = market_data.scan_signals(watchlist)

    if not signals:
        return "📊 <b>Keine aktiven Signale</b>\n\nAlle Aktien in der Watchlist sind im neutralen Bereich."

    text = "🎯 <b>Aktuelle Kauf-/Verkaufssignale</b>\n\n"
    for s in signals:
        text += f"<b>{s['ticker']}</b> - {s['price']}€\n"
        text += f"  RSI: {s['rsi']} | SMA20: {s['sma20']} | SMA50: {s['sma50']}\n"
        if s['sma200']:
            text += f"  SMA200: {s['sma200']}\n"
        text += f"  Bollinger: {s['bb_lower']} - {s['bb_upper']}\n"
        for sig in s["signals"]:
            text += f"  → {sig}\n"
        text += "\n"

    return text


def build_vix_report() -> str:
    vix = market_data.get_vix()
    fg = market_data.get_fear_greed()

    if not vix:
        return "❌ VIX-Daten nicht verfügbar"

    text = (
        f"📊 <b>Markt-Stimmung</b>\n\n"
        f"<b>VIX:</b> {vix['price']} ({format_change(vix['change_pct'])})\n"
        f"Signal: {vix['signal']}\n"
        f"Empfehlung: {vix['action']}\n\n"
        f"<b>Fear & Greed Index:</b> {fg['index']}/100\n"
        f"Stimmung: {fg['label']}\n\n"
    )

    # Interpretation
    if fg["index"] < 25:
        text += "⚡ <b>Extreme Angst = Kaufgelegenheit!</b>\n"
        text += "Historisch gesehen sind die besten Einstiegspunkte bei extremer Angst.\n"
    elif fg["index"] > 75:
        text += "⚠️ <b>Extreme Gier = Vorsicht!</b>\n"
        text += "Nicht der beste Zeitpunkt für große Investitionen.\n"

    return text


def build_watchlist_report(watchlist: list) -> str:
    text = "📋 <b>Deine Watchlist</b>\n\n"

    for ticker in watchlist:
        data = market_data.get_price(ticker)
        if data:
            text += f"<b>{ticker}</b>: {data['price']}€ {format_change(data['change_pct'])}\n"
        else:
            text += f"<b>{ticker}</b>: ❌ Keine Daten\n"

    text += f"\n💡 /signal für Kauf-/Verkaufssignale"
    return text
