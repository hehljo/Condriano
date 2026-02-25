# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projekt: Finanz-Toolkit

Automatisierte Finanz-Strategien und Tools für passives Einkommen. Fokus auf sichere, regelbasierte Ansätze mit klarem Risikomanagement.

## Architektur

Das Projekt ist modular aufgebaut:
- `strategies/` - Trading- und Investment-Strategien (Python)
- `data/` - Datenquellen, APIs, Scraper
- `backtest/` - Backtesting-Engine für Strategievalidierung
- `alerts/` - Benachrichtigungssystem (Telegram, Email)
- `dashboard/` - Web-Dashboard für Monitoring
- `config/` - Konfigurationsdateien, API-Keys (.env)

## Tech Stack

- **Python 3.11+** als Hauptsprache
- **pandas/numpy** für Datenverarbeitung
- **yfinance / ccxt** für Marktdaten (Aktien / Crypto)
- **backtrader** für Backtesting
- **FastAPI** für Dashboard-Backend
- **SQLite/PostgreSQL** für Datenpersistenz

## Commands

```bash
# Setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Backtest einer Strategie
python -m backtest.run --strategy <name> --period 1y

# Live-Monitoring starten
python -m dashboard.app

# Alerts konfigurieren
cp config/.env.example config/.env  # API-Keys eintragen
```

## Wichtige Regeln

- **Keine API-Keys committen** - immer .env nutzen
- **Jede Strategie MUSS Backtesting haben** bevor live
- **Risk Management ist Pflicht** - Stop-Loss, Position Sizing
- **Kein Margin-Trading** ohne explizite User-Freigabe
- **Datenbank-Safety:** Niemals Finanzdaten automatisch löschen
