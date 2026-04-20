# Broker Comparison: Trading 212 vs. CapTrader

> Why Condriano uses Trading 212 and when CapTrader (Interactive Brokers) might be the better choice.
>
> Last updated: April 2026

---

## TL;DR

**Condriano uses Trading 212** because the score-based strategy places many small orders (€200–€500) and the REST API runs natively on any VPS. CapTrader (reseller for Interactive Brokers) has a more powerful API and access to more markets, but charges a €4 minimum per order and requires a permanently running TWS/Gateway process — which makes it a poor fit for small, frequent trades on a headless server.

If you average >€5,000 per order, trade options/futures, or need markets beyond US/EU stocks, CapTrader wins. For everything else, Trading 212.

---

## Direct Fee Comparison (April 2026)

| | **Trading 212 Invest** | **CapTrader (IBKR)** |
|---|---|---|
| Commission (stocks) | 0 € | Xetra: 0.1 % (min €4, max €99) |
| US stocks | 0 € | $0.01 / share (min $2) |
| ETFs Germany | 0 € | from €2 |
| FX fee | 0.15 % | Included in IBKR spread (~0.03 %) |
| Custody fee | 0 € | 0 € |
| Inactivity fee | 0 € | 0 € (older sources mention $1/month under $1,000 — not currently advertised) |
| Minimum deposit | none | **€2,000** |
| Withdrawals | free | 1st/month free, then €1–€8 |
| Interest on cash | variable (~1.5–4 % by currency) | 2.372 % for balances over €10,000 |
| Tax handling (DE) | No automatic German tax deduction | No automatic German tax deduction |
| Regulation | FCA (UK), BaFin (DE), ASIC (AU) | IBKR UK / IBKR Ireland |

### What this means in practice

For a typical Condriano trade of €300:
- **Trading 212:** 0 € commission + maybe 0.45 € FX fee (if USD stock) = **~0.45 €**
- **CapTrader:** 4 € minimum = **4 €**

For 50 round-trips per year (buy + sell = 100 orders):
- **Trading 212:** ~45 € total cost
- **CapTrader:** ~400 € total cost

Break-even point where CapTrader's percentage fee becomes cheaper than the minimum: **€4,000 per order**.

---

## API Comparison (the important part)

| | **Trading 212 API** | **CapTrader / IBKR TWS API** |
|---|---|---|
| API type | REST over HTTPS | TCP socket (to TWS or IB Gateway) |
| Auth | API key in header | Client connects to local TWS/Gateway on port 7496/7497/4001/4002 |
| Setup | Generate key in app → done | Install TWS/Gateway → configure auto-login → keep running 24/7 |
| Rate limits | Per-account, burst-capable, headers in response | ~50 messages/sec, more complex |
| Documentation | [docs.trading212.com](https://docs.trading212.com) — public OpenAPI | IBKR GitHub + PDFs, extensive but steep learning curve |
| Status | Beta, actively developed | Stable for 20+ years |
| Supported accounts | Invest & Stocks ISA only | All IBKR products |
| Architecture | Stateless (REST) | Stateful (TWS must run permanently) |
| Cloud/VPS-friendly | Yes, out of the box | No — requires X11/GUI workaround or IBC wrapper |
| Instruments via API | Stocks, ETFs | Stocks, ETFs, Options, Futures, Forex, Bonds, CFDs |
| Order types | Market, Limit, Stop, StopLimit | All of the above + algo, bracket, OCA, etc. |

### Why the API architecture matters

Trading 212's stateless REST API means Condriano runs as a single Python process on a €5 VPS. One `systemctl restart condriano` and you're back up.

CapTrader requires:
1. A Windows or Linux machine with a GUI (or headless IB Gateway + IBC automation)
2. TWS or IB Gateway running permanently
3. Daily auto-login handling (IBKR forces a daily restart)
4. Your Python bot connecting to that local process

For a simple "run forever on a VPS" bot, this is significantly more complex.

---

## When to choose which

### Trading 212 is the right choice if...

- You trade stocks and ETFs (not derivatives)
- Your typical order size is under €5,000
- You want zero commission
- You want a simple REST API you can deploy anywhere
- You're building a bot on a VPS / Raspberry Pi / cloud container
- You want to start with minimal capital (no minimum deposit)

### CapTrader is the right choice if...

- You trade options, futures, forex, or bonds
- Your typical order size is over €5,000 (percentage fee beats minimum)
- You need access to Asian, Canadian, or smaller European markets
- You want professional-grade reporting and tax export
- You want margin / short selling
- You're OK with running TWS/Gateway on a dedicated machine
- You have €2,000+ starting capital

---

## Condriano-specific analysis

The Condriano score system is explicitly designed for **many small, automated trades** based on RSI, Bollinger Bands, and market sentiment. Typical scenarios:

- Score hits 50 on AAPL at $180 → buy 2 shares ≈ €340
- Score drops below 30 on MSFT → sell 1 share ≈ €380
- Stop-loss triggers on TSLA at -10 % → exit position ≈ €250

Every one of those trades would cost €4 at CapTrader. Most of them cost €0 at Trading 212.

Additionally, Trading 212 supports **fractional shares** via their API — you can buy €50 worth of Amazon without owning a whole share. CapTrader/IBKR supports fractionals too, but the €4 minimum makes it pointless for small amounts.

---

## 2025/2026 changes worth noting

**Trading 212:**
- Multi-currency account now supports 13 currencies — you can hold EUR, USD, GBP separately and avoid the 0.15 % FX fee entirely when trading in matching currencies
- API remains in beta but is stable in production use
- Cash interest rates adjusted downward from the 2023/2024 highs following ECB rate cuts

**CapTrader:**
- Xetra pricing unchanged: 0.1 % / €4 min / €99 max
- Margin rate currently 6.372 %
- Cash interest 2.372 % on balances over €10,000

---

## Sources

All data verified against official sources in April 2026:

- [Trading 212 — Invest fees](https://helpcentre.trading212.com/hc/en-us/articles/11471996799517)
- [Trading 212 — FX fee details](https://helpcentre.trading212.com/hc/en-us/articles/360018909758)
- [Trading 212 — API rate limiting](https://docs.trading212.com/api/section/rate-limiting)
- [Trading 212 — Public API docs](https://t212public-api-docs.redoc.ly/)
- [CapTrader — Conditions](https://www.captrader.com/en/conditions/)
- [CapTrader — Stock trading fees](https://www.captrader.com/en/conditions/stocks-trade/)
- [CapTrader — IB API info](https://www.captrader.com/en/platforms/trade-via-api/ib-api/)
- [CapTrader — Fee overview (depotkonto.de)](https://www.depotkonto.de/captrader/gebuehren/)
- [IBKR TWS API documentation](https://interactivebrokers.github.io/tws-api/introduction.html)

---

## Disclaimer

This comparison reflects publicly available information at the time of writing. Broker fees, API features, and regulations change. Always verify current conditions on the official websites before making decisions. Condriano is not affiliated with either broker and receives no compensation for this comparison.
