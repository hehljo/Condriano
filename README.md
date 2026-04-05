<p align="center">
  <img src="Condriano.png" width="250" />
</p>

<h1 align="center">Condriano</h1>

<p align="center">
  <i>Your personal finance otter. Glasses on, charts loaded, let's go.</i><br>
  <sub>(Yes, his name is Condriano. No, you can't change it. The bot literally won't work if you call it anything else. We tried.)</sub>
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" /></a>
  <a href="https://core.telegram.org/bots"><img src="https://img.shields.io/badge/Telegram-Bot-26A5E4?style=for-the-badge&logo=telegram&logoColor=white" /></a>
  <a href="https://www.trading212.com/"><img src="https://img.shields.io/badge/Trading_212-API-00B4D8?style=for-the-badge" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" /></a>
  <a href="https://buymeacoffee.com/pommesbude"><img src="https://img.shields.io/badge/Buy_Me_A_Coffee-☕-FFDD00?style=for-the-badge&logo=buymeacoffee&logoColor=black" /></a>
</p>

<p align="center">
  <b>An autonomous trading bot with a score-based auto-trade system</b><br>
  Market analysis · Automatic orders · Telegram control · Real-time alerts<br>
  <sub>Total infrastructure cost: $0. Condriano works for fish.</sub>
</p>

---

## What is this?

Condriano is a self-hosted Telegram bot that monitors markets, analyzes stocks using technical indicators and market sentiment, and can automatically trade real stocks & ETFs through the [Trading 212](https://www.trading212.com/) API.

Buy/sell decisions are made through a configurable **score system** — no black-box AI, no "trust me bro" signals. You can see exactly why Condriano wants to buy or sell something.

> **Important:** You need a Trading 212 **Invest** account (not CFD). Condriano doesn't do leverage. He's an otter, not a degen.

### Features

| Feature | Description |
|---|---|
| **Auto-Trade** | Score-based buy/sell system (semi-auto or full-auto) |
| **Live Trading** | Market, Limit, Stop & StopLimit orders via Trading 212 |
| **Telegram Bot** | 20+ commands, daily reports, real-time alerts |
| **Technical Analysis** | RSI, SMA20/50/200, Bollinger Bands |
| **Market Sentiment** | CNN Fear & Greed Index, VIX tracking |
| **Stop-Loss / Take-Profit** | Automatic monitoring every 30 minutes |
| **Multi-Source Data** | Yahoo Finance + Stooq fallback + ECB exchange rates |
| **Database** | SQLite for statistics, signal history, performance tracking |

---

## How the Score System Works

Condriano doesn't guess. He calculates a score from 0–100 based on multiple indicators:

```
BUY SIGNALS                              SELL SIGNALS
─────────────────────────────            ─────────────────────────────
RSI < 30  (oversold)           +30       RSI > 70  (overbought)      +30
RSI < 20  (extreme)            +40       RSI > 80  (extreme)         +40
Price < SMA200                 +20       Price > Bollinger Band      +15
Price < Bollinger Band         +15       Position ≥ +15%             +50
VIX > 25  (market fear)        +15       Position ≤ -10%            +100
Fear & Greed < 25              +10

Score ≥ 50 → BUY                         Score ≥ 50 → SELL
Score 30–49 → ALERT only                 Stop-Loss → IMMEDIATE SELL
Score < 30 → IGNORE
```

All thresholds are configurable via `/autotrade set` or `config/auto_trade.json`.

---

## Quick Start

### Prerequisites

- Python 3.11+
- A [Telegram Bot](https://t.me/BotFather) (free, takes 30 seconds)
- Optional: [Trading 212](https://www.trading212.com/) Invest account for live trading

### 1. Clone & Setup

```bash
git clone https://github.com/hehljo/Condriano.git
cd Condriano
bash setup.sh
```

Or manually:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
mkdir -p data config
```

### 2. Configure

```bash
cp .env.example .env
nano .env  # or vim, we don't judge
```

Fill in your values:

```env
# Telegram Bot (talk to @BotFather → /newbot)
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Your Chat ID (talk to @userinfobot → /start)
TELEGRAM_CHAT_ID=your_chat_id_here

# Trading 212 (optional — leave empty for monitoring only)
T212_API_KEY=
T212_API_SECRET=
T212_MODE=practice
```

> **Tip:** Start with `T212_MODE=practice` to paper-trade first. Switch to `live` when you're comfortable. Condriano respects your risk tolerance.

### 3. Run

```bash
source venv/bin/activate
python3 main.py
```

Condriano will send you a Telegram message. You're in business.

### 4. Run as a Service (Server/VPS)

```bash
sudo cp condriano.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable condriano
sudo systemctl start condriano
```

Auto-restarts on crash. Auto-starts on reboot. Condriano is persistent like that.

---

## Telegram Commands

### Market & Analysis
| Command | What it does |
|---|---|
| `/report` | Full market report (indices, VIX, signals) |
| `/vix` | VIX fear index + Fear & Greed |
| `/signal` | Current buy/sell signals |
| `/watchlist` | Your watched stocks with live prices |
| `/add TICKER` | Add stock to watchlist |
| `/remove TICKER` | Remove from watchlist |

### Auto-Trade
| Command | What it does |
|---|---|
| `/autotrade` | Show current status |
| `/autotrade semi` | Semi-auto (alerts only, you decide) |
| `/autotrade full` | Full-auto (Condriano trades for you) |
| `/autotrade off` | Disable auto-trading |
| `/autotrade scan` | Run a scan right now |
| `/autotrade set KEY VALUE` | Change a setting |

### Trading 212
| Command | What it does |
|---|---|
| `/t212status` | Account balance & P&L |
| `/t212pos` | Live positions |
| `/t212buy TICKER QTY [LIMIT]` | Place buy order |
| `/t212sell TICKER QTY [LIMIT]` | Place sell order |
| `/t212orders` | Open orders |
| `/t212cancel ID` | Cancel an order |
| `/t212div` | Dividends received |

### Local Portfolio
| Command | What it does |
|---|---|
| `/portfolio` | Overview with P&L |
| `/buy TICKER QTY PRICE` | Log a buy |
| `/sell TICKER QTY PRICE` | Log a sell |
| `/history` | Transaction history |

---

## Scheduled Jobs

| When | What |
|---|---|
| **Daily 08:00** | Portfolio morning report |
| **Mon–Fri 09–17, every 30 min** | Portfolio alert (your positions) |
| **Mon–Fri 09–22, every 30 min** | Stop-Loss / Take-Profit check |
| **Mon–Fri 12:00 + 18:00** | Database snapshots |
| **Mon–Fri 18:30** | Daily performance snapshot |

All times are Europe/Berlin. Condriano respects weekends (unlike some of us).

---

## Data Sources

| Source | Purpose | Cost |
|---|---|---|
| Yahoo Finance | Price data, history, indicators | Free |
| Stooq.com | Price data (fallback) | Free |
| CNN Fear & Greed | Market sentiment | Free |
| ECB Data API | EUR/USD exchange rate | Free |
| Trading 212 API | Orders, portfolio, positions | Free |

No paid APIs. No subscriptions. Condriano is free-range and organic.

---

## Project Structure

```
Condriano/
├── main.py                     # Entry point + scheduler
├── config/
│   └── auto_trade.json         # Auto-trade configuration (generated on first run)
├── src/
│   ├── bot/
│   │   ├── telegram_bot.py     # Telegram bot core
│   │   ├── handlers.py         # Market & portfolio commands
│   │   ├── trading_handlers.py # T212 trading commands + auto-trade
│   │   └── scheduler.py        # Scheduled jobs
│   ├── broker/
│   │   └── trading212.py       # Trading 212 API client
│   ├── market/
│   │   ├── data.py             # Market data pipeline
│   │   ├── reports.py          # Report generation
│   │   └── sources.py          # Multi-source data + fallbacks
│   ├── strategies/
│   │   └── auto_trader.py      # Score system & auto-trade logic
│   └── utils/
│       ├── config.py           # Configuration & .env
│       └── database.py         # SQLite persistence
└── data/                       # DB + logs (not in repo)
```

---

## Resource Usage

| Resource | Value |
|---|---|
| **RAM** | ~90 MB |
| **CPU** | ~0.1% idle, 2–5% during scans |
| **Disk** | ~1 MB code, ~314 MB venv |
| **Network** | ~2 MB/day (~50 API calls) |
| **Min. Hardware** | 1 vCPU, 512 MB RAM |

Runs happily on a Raspberry Pi, a $5 VPS, or that old laptop you forgot about.

---

## FAQ

**Q: Does Condriano guarantee profits?**
A: No. Condriano is an otter with glasses, not a financial advisor. Past performance of otters does not guarantee future results.

**Q: Can I use a different broker?**
A: Currently only Trading 212 is supported. But you can use Condriano without a broker — he'll still analyze markets and send you signals via Telegram.

**Q: Is this safe for real money?**
A: Start with `T212_MODE=practice`. The score system is transparent and configurable. Position sizing and stop-losses are built in. But ultimately, you're responsible for your trades. Condriano is just the messenger (with very cute glasses).

**Q: Why "Condriano"?**
A: Some questions are better left unanswered. Just know that renaming him will void the warranty.

---

## Support the Project

If Condriano helped you make smarter trades (or at least entertained you), consider buying him a coffee:

<p align="center">
  <a href="https://buymeacoffee.com/pommesbude">
    <img src="https://img.buymeacoffee.com/button-api/?text=Buy Condriano a coffee&emoji=🦦&slug=pommesbude&button_colour=FFDD00&font_colour=000000&font_family=Poppins&outline_colour=000000&coffee_colour=ffffff" />
  </a>
</p>

---

## License

MIT — do whatever you want. Just don't blame the otter.

---

<p align="center">
  <sub>Made with ☕ and questionable financial decisions</sub>
</p>
