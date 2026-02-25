# MASTER ROADMAP - Finanz-Toolkit

**Startkapital:** 100€ | **Kein Crypto** | **Alerts via Telegram Bot** | **Broker: Trading 212**

---

## Phase 1: Fundament (Infrastruktur & Telegram Bot) ✅

- [x] Python-Projekt aufsetzen (venv, requirements, .env)
- [x] Telegram Bot erstellen und konfigurieren
- [x] Alert-System bauen (Nachrichten, Formatierung, Kategorien)
- [x] Täglicher Markt-Report via Telegram (DAX, S&P500, VIX, Fear&Greed Index)
- [x] Error-Handling & Logging
- [x] SQLite Datenbank für Statistik & Analyse
- [x] Portfolio-Tracking (Kauf/Verkauf/Performance)
- [x] GitHub-ready (setup.sh, .gitignore)

## Phase 2: Markt-Intelligence (Daten & Analyse) ✅

- [x] Marktdaten-Pipeline (Yahoo Finance API - Primär)
- [x] Fallback-Datenquelle: Stooq (automatisch bei Yahoo-Ausfall)
- [x] Cross-Source Preisverifizierung (Yahoo vs. Stooq)
- [x] EZB offizieller EUR/USD Wechselkurs
- [x] CNN Fear & Greed Index (offizielle Quelle)
- [x] VIX / Fear & Greed Index Tracker
- [x] Technische Indikatoren (RSI, SMA20/50/200, Bollinger Bands)
- [x] Watchlist-Management via Telegram Commands
- [x] Börsenstatus-Erkennung (EU/US offen/geschlossen)
- [ ] Dividenden-Screener (Top Dividenden-Aktien DE/US)

## Phase 3: Auto-Trade System ✅

- [x] Score-basiertes Kauf-/Verkaufssystem (0-100 Punkte)
- [x] Konfigurierbares Regelwerk (config/auto_trade.json)
- [x] Semi-Modus: Bot informiert, User entscheidet
- [x] Full-Modus: Bot handelt autonom
- [x] Stop-Loss Überwachung (alle 30 Min)
- [x] Take-Profit Automatik
- [x] Position Sizing (Max pro Trade, Max pro Aktie, Cash Reserve)
- [x] Max Trades pro Tag Limit
- [x] Automatische Scans: 09:30 (EU Open), 14:00 (Pre-US), 15:30 (US Open)
- [x] Kauf-/Verkaufssignale als Telegram Alert
- [x] Telegram-Steuerung: /autotrade semi|full|off|scan|set

## Phase 4: Trading 212 Live-Integration ✅

- [x] Trading 212 API (Basic Auth, Key + Secret)
- [x] Market/Limit/Stop/StopLimit Orders
- [x] Live-Positionen & Kontostand via Telegram
- [x] Kauf/Verkauf direkt via Telegram (/t212buy, /t212sell)
- [x] Dividenden-Tracking via T212 API
- [x] Erste Investition: 40€ AMZN + 30€ GOOGL + 24€ EUNL + 3€ Cash
- [ ] Monatlicher Rebalancing-Alert
- [ ] Sparplan-Empfehlungen basierend auf Marktlage

## Phase 5: Backtesting & Optimierung ✅

- [x] Backtesting-Engine aufbauen
- [x] Score-System historisch validieren (2J historische Daten)
- [x] Backtesting-Ergebnisse via Telegram als Chart (/backtest)
- [x] Buy & Hold Vergleich + Max Drawdown Analyse
- [x] Position Sizing Fix (EUR/USD via EZB)
- [x] Doppelkauf-Schutz (gleiche Aktie nicht 2x am Tag)
- [x] Portfolio in Morgen-Report integriert
- [ ] Strategie-Optimierung basierend auf Backtesting

## Phase 6: Passives Einkommen skalieren

- [ ] Tagesgeld-Zinsen-Tracker (beste Angebote DE/EU)
- [ ] Cashback-Optimierer
- [ ] Sektor-Rotation Strategie
- [ ] Earnings-Kalender mit Alerts

## Phase 7: Fortgeschritten (ab 500€+)

- [ ] Options-Screener (Wheel Strategy)
- [ ] Automatische Portfolio-Analyse (Sharpe Ratio, Drawdown)
- [ ] Monatlicher Performance-Report mit Charts

---

## Laufende Features (aktiv)

- [x] Täglicher Morgen-Report (08:00) via Telegram
- [x] Echtzeit-Alerts bei starken Marktbewegungen (>2%)
- [x] Wöchentlicher Portfolio-Überblick (Sonntag 18:00)
- [x] Auto-Trade Scans (09:30, 14:00, 15:30)
- [x] Stop-Loss / Take-Profit Check (alle 30 Min)
- [x] DB Snapshots (12:00, 18:00)
- [x] Portfolio Performance Snapshot (18:30)

---

## Auto-Trade Score-System

### Kaufsignale (Score 0-100)
| Indikator | Bedingung | Punkte |
|---|---|---|
| RSI < 30 | Überverkauft | +30 |
| RSI < 20 | Extrem überverkauft | +40 |
| Preis < SMA200 | Unter langfristigem Trend | +20 |
| Preis < Bollinger Band | Unter statistischem Band | +15 |
| VIX > 25 | Markt-Angst | +15 |
| Fear & Greed < 25 | Extreme Angst | +10 |

**Score >= 50 → KAUFEN | Score 30-49 → ALERT | Score < 30 → IGNORIEREN**

### Verkaufssignale
| Indikator | Bedingung | Punkte |
|---|---|---|
| RSI > 70 | Überkauft | +30 |
| RSI > 80 | Extrem überkauft | +40 |
| Preis > Bollinger Band | Über statistischem Band | +15 |
| Position +15% | Take Profit | +50 |
| Position -10% | Stop Loss | +100 (sofort!) |

---

## Datenquellen & Fallbacks

| Quelle | Typ | Status | Fallback |
|---|---|---|---|
| Yahoo Finance API | Kursdaten, Historie | ✅ Primär | → Stooq |
| Stooq.com | Kursdaten | ✅ Fallback | → Cache |
| CNN Fear & Greed | Marktstimmung | ✅ Primär | → Eigene Berechnung |
| EZB Data API | EUR/USD Kurs | ✅ Primär | → Yahoo FX |
| Trading 212 API | Orders, Portfolio | ✅ Live | - |
| Telegram Bot API | Alerts, Commands | ✅ Live | - |

---

## Tech-Stack

| Komponente | Tool | Kosten |
|---|---|---|
| Sprache | Python 3.12 | Gratis |
| Marktdaten | Yahoo Finance + Stooq | Gratis |
| Marktstimmung | CNN Fear & Greed | Gratis |
| Wechselkurse | EZB Data API | Gratis |
| Datenbank | SQLite (WAL-Modus) | Gratis |
| Alerts | Telegram Bot API | Gratis |
| Broker | Trading 212 (Invest) | Gratis |
| Scheduling | APScheduler | Gratis |

**Gesamtkosten Infrastruktur: 0€**
