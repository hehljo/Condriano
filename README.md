<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Trading_212-API-00B4D8?style=for-the-badge&logo=bitcoin&logoColor=white" />
  <img src="https://img.shields.io/badge/Telegram-Bot-26A5E4?style=for-the-badge&logo=telegram&logoColor=white" />
  <img src="https://img.shields.io/badge/Lizenz-Privat-red?style=for-the-badge" />
</p>

<h1 align="center">🏦 Condriano</h1>

<p align="center">
  <b>Autonomer Trading-Bot mit Score-basiertem Auto-Trade System</b><br>
  Marktanalyse · Automatische Orders · Telegram-Steuerung · Echtzeit-Alerts
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Status-Live%20Trading-brightgreen?style=flat-square" />
  <img src="https://img.shields.io/badge/Broker-Trading%20212-blue?style=flat-square" />
  <img src="https://img.shields.io/badge/Kosten-0%20€-success?style=flat-square" />
  <img src="https://img.shields.io/badge/Datenquellen-Yahoo%20%7C%20Stooq%20%7C%20CNN%20%7C%20EZB-informational?style=flat-square" />
</p>

---

## Was ist das?

Ein vollautonomer Trading-Bot der über Telegram gesteuert wird und über die Trading 212 API echte Aktien & ETFs handelt. Kaufentscheidungen werden über ein konfigurierbares **Score-System** getroffen — basierend auf technischen Indikatoren, Marktstimmung und Volatilität.

### Kernfunktionen

| Feature | Beschreibung |
|---|---|
| **Auto-Trade** | Score-basiertes Kauf-/Verkaufssystem (Semi oder Vollautomatik) |
| **Live-Trading** | Market, Limit, Stop & StopLimit Orders via Trading 212 |
| **Telegram Bot** | 20+ Commands, tägliche Reports, Echtzeit-Alerts |
| **Technische Analyse** | RSI, SMA20/50/200, Bollinger Bands |
| **Marktstimmung** | CNN Fear & Greed Index, VIX-Tracking |
| **Stop-Loss / Take-Profit** | Automatische Überwachung alle 30 Minuten |
| **Multi-Source Daten** | Yahoo Finance + Stooq Fallback + EZB Wechselkurse |
| **Datenbank** | SQLite für Statistik, Signalhistorie, Performance-Tracking |

---

## Score-System

Kaufentscheidungen basieren auf einem Punktesystem (0–100):

```
KAUFSIGNALE                              VERKAUFSSIGNALE
─────────────────────────────            ─────────────────────────────
RSI < 30  (überverkauft)    +30          RSI > 70  (überkauft)     +30
RSI < 20  (extrem)          +40          RSI > 80  (extrem)        +40
Preis < SMA200              +20          Preis > Bollinger Band    +15
Preis < Bollinger Band      +15          Position ≥ +15%           +50
VIX > 25  (Markt-Angst)     +15          Position ≤ -10%          +100
Fear & Greed < 25           +10

Score ≥ 50 → KAUFEN                      Score ≥ 50 → VERKAUFEN
Score 30–49 → ALERT                      Stop-Loss → SOFORT
Score < 30 → IGNORIEREN
```

Alle Schwellenwerte sind konfigurierbar über `/autotrade set` oder `config/auto_trade.json`.

---

## Architektur

```
Condriano/
├── main.py                    # Entry Point + Scheduler
├── config/
│   └── auto_trade.json        # Auto-Trade Konfiguration
├── src/
│   ├── bot/
│   │   ├── telegram_bot.py    # Telegram Bot Core
│   │   ├── handlers.py        # Markt & Portfolio Commands
│   │   ├── trading_handlers.py# T212 Trading Commands + Auto-Trade
│   │   └── scheduler.py       # Zeitgesteuerte Jobs
│   ├── broker/
│   │   └── trading212.py      # Trading 212 API Client
│   ├── market/
│   │   ├── data.py            # Marktdaten-Pipeline
│   │   ├── reports.py         # Report-Generierung
│   │   └── sources.py         # Multi-Source + Fallbacks
│   ├── strategies/
│   │   └── auto_trader.py     # Score-System & Auto-Trade Logik
│   └── utils/
│       ├── config.py          # Konfiguration & .env
│       └── database.py        # SQLite Persistenz
└── data/                      # DB + Logs (nicht im Repo)
```

---

## Installation

### Voraussetzungen

- Python 3.11+
- [Trading 212](https://www.trading212.com/) **Invest-Konto** (kein CFD)
- Telegram Account + Bot via [@BotFather](https://t.me/BotFather)

### 1. Repo klonen

```bash
git clone https://github.com/hehljo/Condriano.git
cd Condriano
```

### 2. Setup ausführen

```bash
bash setup.sh
```

Oder manuell:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
mkdir -p data
```

### 3. Konfiguration

```bash
cp .env.example .env
```

`.env` ausfüllen:

```env
# Telegram Bot (@BotFather → /newbot)
TELEGRAM_BOT_TOKEN=dein_bot_token

# Telegram Chat-ID (@userinfobot → /start)
TELEGRAM_CHAT_ID=deine_chat_id

# Trading 212 (App → Einstellungen → API → Key generieren)
T212_API_KEY=dein_api_key
T212_API_SECRET=dein_api_secret
T212_MODE=live
```

### 4. Starten

```bash
source venv/bin/activate
python3 main.py
```

Der Bot meldet sich via Telegram und ist einsatzbereit.

### 5. Im Hintergrund laufen lassen (Server/VPS)

```bash
# Mit nohup
nohup python3 main.py > /dev/null 2>&1 &

# Oder als systemd Service
sudo nano /etc/systemd/system/condriano.service
```

```ini
[Unit]
Description=Condriano Trading Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/Finanz
ExecStart=/root/Finanz/venv/bin/python3 main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable condriano
sudo systemctl start condriano
```

---

## Telegram Commands

### Markt & Analyse
| Command | Beschreibung |
|---|---|
| `/report` | Kompletter Markt-Report (Indizes, VIX, Signale) |
| `/vix` | VIX Angst-Index + Fear & Greed |
| `/signal` | Aktuelle Kauf-/Verkaufssignale |
| `/watchlist` | Beobachtete Aktien mit Live-Kursen |
| `/add TICKER` | Aktie zur Watchlist |
| `/remove TICKER` | Aktie von Watchlist |

### Auto-Trade
| Command | Beschreibung |
|---|---|
| `/autotrade` | Status anzeigen |
| `/autotrade semi` | Halbautomatik (nur Alerts) |
| `/autotrade full` | Vollautomatik (Bot handelt) |
| `/autotrade off` | Deaktivieren |
| `/autotrade scan` | Sofort scannen |
| `/autotrade set KEY WERT` | Einstellung ändern |

### Trading 212
| Command | Beschreibung |
|---|---|
| `/t212status` | Kontostand & P&L |
| `/t212pos` | Live-Positionen |
| `/t212buy TICKER QTY [LIMIT]` | Kauforder |
| `/t212sell TICKER QTY [LIMIT]` | Verkaufsorder |
| `/t212orders` | Offene Orders |
| `/t212cancel ID` | Order stornieren |
| `/t212div` | Erhaltene Dividenden |

### Portfolio (lokal)
| Command | Beschreibung |
|---|---|
| `/portfolio` | Überblick mit P&L |
| `/buy TICKER QTY PREIS` | Kauf eintragen |
| `/sell TICKER QTY PREIS` | Verkauf eintragen |
| `/history` | Transaktionshistorie |

---

## Automatische Jobs

| Zeit | Job |
|---|---|
| **Mo–Fr 08:00** | Morgen-Report via Telegram |
| **Mo–Fr 09:30** | Auto-Trade Scan (EU-Börsenöffnung) |
| **Mo–Fr 10:00 + 16:00** | Signal-Scans |
| **Mo–Fr 14:00** | Auto-Trade Scan (Pre-US) |
| **Mo–Fr 15:30** | Auto-Trade Scan (US-Börsenöffnung) |
| **Mo–Fr 09–22 alle 30 Min** | Stop-Loss / Take-Profit Check |
| **Mo–Fr 09–17 alle 30 Min** | Markt-Crash-Alert (>2% Bewegung) |
| **Mo–Fr 12:00 + 18:00** | DB Snapshots |
| **Mo–Fr 18:30** | Portfolio-Performance Snapshot |
| **So 18:00** | Wöchentlicher Report |

---

## Datenquellen

| Quelle | Zweck | Fallback |
|---|---|---|
| **Yahoo Finance API** | Kursdaten, Historie, Indikatoren | → Stooq |
| **Stooq.com** | Kursdaten (Fallback) | → Cache |
| **CNN Fear & Greed** | Marktstimmung | → Eigene Berechnung |
| **EZB Data API** | EUR/USD Wechselkurs | → Yahoo FX |
| **Trading 212 API** | Orders, Portfolio, Positionen | — |

Alle Quellen sind kostenlos und benötigen keine separaten API-Keys.

---

## Wiederherstellung / Neues Gerät

```bash
git clone https://github.com/hehljo/Condriano.git
cd Condriano
bash setup.sh
cp .env.example .env
# .env mit gleichen Keys befüllen
python3 main.py
```

Der Bot verbindet sich mit dem bestehenden Trading 212 Konto und sieht sofort alle Positionen, Orders und den Kontostand. Die Auto-Trade Konfiguration ist im Repo gespeichert.

---

## Tech-Stack

| Komponente | Tool | Kosten |
|---|---|---|
| Sprache | Python 3.12 | Gratis |
| Marktdaten | Yahoo Finance + Stooq | Gratis |
| Marktstimmung | CNN Fear & Greed | Gratis |
| Wechselkurse | EZB Data API | Gratis |
| Datenbank | SQLite (WAL) | Gratis |
| Alerts | Telegram Bot API | Gratis |
| Broker | Trading 212 Invest | Gratis |
| Scheduling | APScheduler | Gratis |

**Gesamtkosten Infrastruktur: 0 €**

---

## Ressourcenverbrauch

| Ressource | Wert | Details |
|---|---|---|
| **RAM** | ~90 MB | Alle Module geladen, idle |
| **CPU** | ~0.1% | 99.9% idle, 2–5% bei Scans (5–10 Sek) |
| **Disk (Code)** | ~1 MB | Ohne venv |
| **Disk (venv)** | ~314 MB | Alle Dependencies |
| **Disk (DB)** | ~5–10 MB/Monat | Snapshots, Signale, Historie |
| **Netzwerk** | ~2 MB/Tag | ~50 API-Calls (Yahoo, T212, Telegram) |
| **Min. Server** | 1 vCPU, 512 MB RAM | Raspberry Pi reicht |

Der Bot läuft problemlos auf einem Raspberry Pi, kleinen VPS oder jedem Linux-Server.

---

## systemd Service (Dauerbetrieb)

Die Datei `condriano.service` ist im Repo enthalten:

```bash
# Service installieren
sudo cp condriano.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable condriano
sudo systemctl start condriano

# Status prüfen
sudo systemctl status condriano

# Logs ansehen
journalctl -u condriano -f

# Neustart
sudo systemctl restart condriano
```

Der Service startet automatisch bei Server-Reboot und wird bei Crashes nach 15 Sekunden neu gestartet.
