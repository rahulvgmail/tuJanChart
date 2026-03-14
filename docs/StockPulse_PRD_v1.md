# StockPulse — Product Requirements Document v1.0

**Indian Equity Technical Screener & Analytics Platform**

| | |
|---|---|
| **Version** | 1.0 |
| **Date** | March 7, 2026 |
| **Author** | Etah & Team |
| **Status** | Draft for Review |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Goals](#3-goals)
4. [Non-Goals (v1)](#4-non-goals-v1)
5. [User Personas & Stories](#5-user-personas--stories)
6. [Detailed Requirements](#6-detailed-requirements)
7. [Data Model](#7-data-model)
8. [Architecture & Tech Stack](#8-architecture--tech-stack)
9. [Migration from Spreadsheet](#9-migration-from-spreadsheet)
10. [Success Metrics](#10-success-metrics)
11. [Timeline & Phasing](#11-timeline--phasing)
12. [Open Questions](#12-open-questions)
13. [Risks & Mitigations](#13-risks--mitigations)
14. [Glossary](#14-glossary)

---

## 1. Executive Summary

StockPulse is a private, access-controlled web application that replaces a manually-maintained Google Sheets workbook currently used by a 4-person private investment fund to screen, analyze, and monitor approximately 1,640 Indian equities across NSE and BSE.

The current spreadsheet tracks 85+ technical indicators per stock, implements ~90 named screening strategies, and requires daily manual data updates from multiple sources (GOOGLEFINANCE, BSE announcements, NSE surveillance lists). It has served as a functional proof-of-concept for 4+ years but has reached the limits of what a spreadsheet can do: data refresh is manual and fragile, there is no alerting, no API for programmatic access, no audit trail, and no way for the fund's equity research agentic application (built on Python/Pydantic/DSPy) to consume screener results.

This PRD defines the first production-quality version of StockPulse — significantly beyond MVP. It automates all data ingestion, replicates and extends all existing screening logic, exposes a REST API for the agentic app, and introduces an event/webhook system so that technical analysis signals can trigger automated equity research workflows.

---

## 2. Problem Statement

Four fund members rely on a Google Sheets workbook with 15 interconnected sheets, 1,640+ stock rows, and 85+ computed columns per row to make daily investment decisions. The system breaks in three critical ways:

- **Manual data dependency:** Historical price data (daily, weekly, yearly), board meeting dates, quarterly result dates, ASM surveillance lists, and circuit band data must be copy-pasted from external sources. A single missed update corrupts downstream indicators for all 1,640 stocks. The runmacro sheet shows the last update was March 4, 2026 — three days stale.

- **No programmatic access:** The fund's equity research agentic app (Python/Pydantic/DSPy) cannot query screener results. Every insight requires a human to manually run a filter in the spreadsheet, read the results, and relay them. This bottleneck prevents the agentic app from doing its job: automated stock filtering and recommendation.

- **No event-driven analysis:** When a stock hits a 52-week high, touches a key DMA, or shows a volume breakout, nothing happens automatically. A human must notice the signal in a sea of 1,640 rows. The fund misses time-sensitive opportunities because no alerting or webhook mechanism exists.

The cost of not solving this is direct: missed trades, stale analysis, and an agentic research app that cannot function at its designed capability.

---

## 3. Goals

### 3.1 User Goals

1. **Zero manual data entry:** All price data, corporate actions, result dates, board meetings, ASM lists, and circuit bands are ingested automatically. No fund member should ever need to copy-paste data.
2. **Faster signal discovery:** Reduce time from market close to fully-computed screener results from ~45 minutes (manual) to under 5 minutes (automated).
3. **Always-on screening:** Near real-time (1–5 minute) intraday indicator refresh during market hours, with all 90+ screeners available for instant query.
4. **Collaborative annotation:** All 4 members can assign stock color classifications, add comments, and manage watchlists with full audit history of who changed what and when.

### 3.2 System Goals

5. **API-first architecture:** Every piece of data and every screener result is accessible via authenticated REST API, enabling the DSPy agentic app to filter, query, and recommend stocks programmatically.
6. **Event-driven integration:** Technical analysis events (DMA crossovers, 52-week highs, volume breakouts, result proximity) trigger outbound webhooks to the agentic research app within 60 seconds of detection.
7. **Portable deployment:** Run on both a self-hosted machine (home server) and a cloud VPS, with Docker-based deployment for environment parity.

---

## 4. Non-Goals (v1)

- **Fundamental analysis:** StockPulse v1 is a technical screener. Earnings analysis, financial statement parsing, and valuation models are the agentic app's domain, not this platform's. We provide the signals; the agent does the deep analysis.

- **Trade execution:** No broker integration for placing orders. This is a screening and alerting tool, not a trading terminal. Broker API integration (Zerodha Kite, etc.) is a v2 consideration for live data feeds.

- **Mobile app:** The web UI will be responsive but there is no native iOS/Android app. Four power users on desktops do not justify the investment.

- **Public access / multi-tenancy:** This is a private tool for 4 named users. No self-service signup, no tenant isolation, no billing. Authentication is invite-only.

- **Backtesting engine:** While we store historical indicator values (new capability), v1 does not include a backtesting framework for evaluating strategy performance over historical periods. The data model supports this for v2.

---

## 5. User Personas & Stories

### 5.1 Personas

| Persona | Role | Primary Need |
|---|---|---|
| Fund Member | Active screener user (all 4 members) | Run screeners daily, annotate stocks, monitor signals in near real-time |
| Agentic App | DSPy-based equity research agent | Query screeners via API, receive event webhooks, pull indicator data for LLM-driven analysis |
| Admin | System administrator (Etah) | Manage stock universe, configure data pipelines, invite/revoke users, monitor system health |

### 5.2 User Stories — Fund Member

- As a fund member, I want to see a dashboard of all 90+ screener results updated within 5 minutes of market data refresh, so that I can identify actionable stocks without manually running filters.
- As a fund member, I want to assign a color classification (Pink, Yellow, Orange, Blue, Red, Green) to any stock with a comment explaining my reasoning, so that the team shares a common qualitative view.
- As a fund member, I want to click on any stock and see its full indicator panel (all DMAs, WMAs, volume metrics, 52-week position, result dates) on a single page, so that I do not need to scroll through 85 columns.
- As a fund member, I want to create a custom screener by combining conditions (e.g., 10 DMA Hold + Orange color + result in next 15 days + volume > average) without writing code, so that I can test new strategies quickly.
- As a fund member, I want to receive a notification (in-app and/or via webhook to a Telegram bot) when a stock in my watchlist triggers a new screener or hits a technical event, so that I do not miss time-sensitive signals.
- As a fund member, I want to see the history of when a stock was added to/removed from each screener result, so that I can understand the trajectory of a signal over time.
- As a fund member, I want to view an audit log of all color classification and comment changes by all members, so that I know who said what and when.

### 5.3 User Stories — Agentic App (API Consumer)

- As the agentic app, I want to call `GET /api/screeners/{id}/results` with optional filters (min PE, max market cap, color, sector) and receive a JSON array of matching stocks with all indicators, so that I can feed them into my DSPy pipeline for analysis.
- As the agentic app, I want to register a webhook URL and receive HTTP POST events when stocks trigger specific technical events (52W high, DMA crossover, volume breakout, result proximity), so that I can initiate deep-dive research autonomously.
- As the agentic app, I want to call `GET /api/stocks/{symbol}/indicators?period=90d` and receive a time-series of all computed indicators, so that I can reason about trends rather than just point-in-time values.
- As the agentic app, I want to call `POST /api/stocks/{symbol}/notes` to attach research findings back to a stock record, so that human members can see AI-generated insights alongside their own annotations.

### 5.4 User Stories — Admin

- As the admin, I want to add or remove stocks from the universe via the UI or API, and have all historical data backfilled automatically, so that I never need to manually insert rows and formulas.
- As the admin, I want to see a system health dashboard showing last successful data pull, any failed ingestion jobs, queue depth, and database size, so that I know the platform is functioning.
- As the admin, I want to invite a new fund member by email and revoke access instantly, so that membership changes do not require code deployment.

---

## 6. Detailed Requirements

### 6.1 Must-Have (P0) — Cannot Ship Without

#### 6.1.1 Automated Data Ingestion Pipeline

Replace all manual data entry with scheduled, automated ingestion jobs.

| Data Source | Current Method | Frequency | New Method |
|---|---|---|---|
| Daily OHLCV prices | GOOGLEFINANCE + manual paste to TDailyHistoricalData | Every 1–5 min intraday; EOD batch | yfinance / jugaad-data API (swappable to broker API) |
| Weekly close prices | Manual paste to TWeeklyHistoricalData | Computed from daily | SQL aggregation from daily_prices table |
| 52-week high data | Manual paste to T1YEARHistoricalDataHIGH | Computed from daily | Window function over daily_prices |
| Board meeting dates | Copy from BSE website to Q1BM/Q3BM/Q4BM sheets | Daily check | BSE India API (api.bseindia.com) |
| Quarterly result dates | Manual update in ResultDate sheet | Daily check | BSE/NSE corporate filings API |
| ASM surveillance lists | Manual snapshot to ASM/ASM v1 sheets | Daily | NSE CSV download automation |
| Circuit band limits | Manual snapshot to Circuit bands sheet | Daily | NSE CSV download automation |
| PE, Market Cap, fundamentals | GOOGLEFINANCE(symbol, "PE"/"marketcap") | EOD | yfinance or screener.in scrape |

**Acceptance Criteria:**

- [ ] Given market hours have ended, when the EOD job runs at 4:00 PM IST, then OHLCV data for all stocks in the universe is stored within 15 minutes.
- [ ] Given a new board meeting announcement on BSE, when the daily corporate actions job runs, then the meeting appears in the system within 24 hours.
- [ ] Given an ingestion job fails, when the admin views the health dashboard, then the failure is visible with error details, and a retry can be triggered manually.
- [ ] Given the free data source (yfinance) is swapped for a broker API (Zerodha Kite), then only the data adapter layer changes; no computation or API code is modified.

#### 6.1.2 Technical Indicator Computation Engine

Port all 85+ formula columns from the Final sheet to server-side computation. Every indicator currently calculated in the spreadsheet must be available in the new system.

**Moving Averages (Daily):** 10, 20, 50, 100, 200 DMA computed from daily close prices. Current formula: `=AVERAGE(OFFSET(TDailyHistoricalData!$C{row},0,COUNT(...)-N+2,1,N),$E{row})` where N is the DMA period and the current price is included.

**Moving Averages (Weekly):** 5, 10, 20, 30 WMA computed from weekly close data.

**DMA/WMA Hold/Break/Reverse Signals:** For each DMA/WMA, determine if price is holding above (Hold), has broken below (Break), or is reversing at the level. Current logic: `IF(touch_DMA, IF(price >= DMA_value, "Hold", "Reverse"), "")`. Touch detection: `AND(today_low < DMA, today_high > DMA)`.

**52-Week High Detection:** Three variants — intraday (today's high = 52W high), closing (current price >= max of 252 daily closes), and yesterday's (was yesterday the 52W closing high). Track the date when 52W high was last achieved.

**Volume Analytics:** Max volume over 21 days, average volume over 140 days, average volume over 280 days, today's volume. Breakout flags: today's volume > max/avg thresholds.

**Biweekly/Weekly Breakout:** Biweekly high and volume vs. historical comparison. Weekly breakout detection with price and volume confirmation.

**Gap-Up/Gap-Down:** Current formula: `IF(ABS((open - prev_close) / prev_close * 100) > threshold, value, "")`. Default threshold: 3%.

**90-Day High/Low:** Sourced from weekly data. 90-day low touch detection: today's low <= 90-day low.

**Result Date Proximity:** Days until/since the nearest quarterly result date. Flag stocks with results within N days (configurable, currently 7/10/15 days).

**Acceptance Criteria:**

- [ ] Given the same input data, when indicators are computed for any stock, then the values match the spreadsheet's calculated values within 0.01% tolerance.
- [ ] Given 1,640 stocks, when the full indicator recomputation runs after EOD data pull, then all indicators are updated within 3 minutes.
- [ ] Given an intraday price update, when the near-real-time refresh runs, then affected indicators (price-dependent DMAs, breakout flags) update within 60 seconds.

#### 6.1.3 Screener Engine

Replace the ~90 FILTER formulas from the links/Copyoflinks sheets with a composable, database-driven screener engine.

Each screener is defined as a set of conditions that can be combined with AND logic. Conditions reference computed indicators and stock metadata.

**Condition Types:**

- Numeric comparison: `field {>, <, >=, <=, ==, between} value` (e.g., PE < 25, market_cap > 100)
- Boolean flag: `field is {true/false}` (e.g., is_52w_closing_high = true, dma_10_hold = true)
- Enum match: `field in {set}` (e.g., color in [Orange, Yellow, Pink])
- Date proximity: `field {within_days, after_days} N` (e.g., result_date within_days 15)
- Relative comparison: `field {>, <} other_field` (e.g., today_volume > avg_volume_140d)

All 90 existing screeners from the spreadsheet must be pre-loaded as built-in screeners. Examples:

- **001HighestClosen52WeekHigh:** is_52w_closing_high AND has_result_within_7_days
- **021-ONLY10DMA-ORANGEnYELLOW:** dma_10_touch AND color IN [Orange, Yellow]
- **01IMP-GAPUP+52WeekHigh+Volume:** gap_up AND (is_52w_high_today OR is_52w_closing_high) AND today_volume > avg_volume_140d

**Acceptance Criteria:**

- [ ] Given any of the 90 existing screeners, when run against the same data, then the results match the spreadsheet's FILTER output.
- [ ] Given a fund member on the screener builder UI, when they select conditions from dropdowns and click Run, then results appear in under 2 seconds.
- [ ] Given a new screener is created via UI, when saved, then it is immediately available via the API at `GET /api/screeners/{id}/results`.

#### 6.1.4 REST API

All data and functionality must be accessible via authenticated JSON REST API. The API is the primary integration point for the DSPy agentic app.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/stocks` | List all stocks with latest indicators, filterable by sector/color/market cap |
| GET | `/api/stocks/{symbol}` | Full stock detail: all indicators, metadata, color, comments, watchlist status |
| GET | `/api/stocks/{symbol}/prices` | Historical OHLCV data with period/interval params |
| GET | `/api/stocks/{symbol}/indicators` | Time-series of computed indicators over a date range |
| GET | `/api/screeners` | List all screeners (built-in + custom) |
| GET | `/api/screeners/{id}/results` | Run screener, return matching stocks with indicators. Supports additional filter params. |
| POST | `/api/screeners` | Create a new custom screener (condition set) |
| GET | `/api/events` | Recent technical events, filterable by type/symbol/date |
| GET | `/api/events/stream` | Server-Sent Events stream for real-time event push |
| POST | `/api/stocks/{symbol}/notes` | Attach a note/comment (human or agent-authored) |
| PUT | `/api/stocks/{symbol}/classification` | Update color classification with comment |
| GET | `/api/webhooks` | List registered webhook subscriptions |
| POST | `/api/webhooks` | Register a new webhook (URL + event types to subscribe) |
| POST | `/api/universe` | Add stocks to universe (triggers backfill) |
| DELETE | `/api/universe/{symbol}` | Remove stock from active universe (data retained) |

**Acceptance Criteria:**

- [ ] Given a valid API key, when any endpoint is called, then response is returned in under 500ms for single-stock queries and under 2 seconds for full-universe screener runs.
- [ ] Given an invalid or missing API key, when any endpoint is called, then a 401 Unauthorized response is returned.
- [ ] Given the agentic app calls `GET /api/screeners/{id}/results`, then the response includes a Pydantic-compatible JSON schema that the DSPy app can deserialize directly.

#### 6.1.5 Event Detection & Webhook System

Detect meaningful technical events and push them to registered webhook endpoints (primarily the DSPy agentic app).

| Event Type | Trigger Condition | Priority |
|---|---|---|
| 52W_HIGH_INTRADAY | Today's high = 52-week high | Critical |
| 52W_HIGH_CLOSING | Close price >= max of 252 daily closes | Critical |
| DMA_CROSSOVER | Price crosses above/below any DMA (10/20/50/100/200) | High |
| WMA_CROSSOVER | Price crosses above/below any WMA (5/10/20/30) | High |
| VOLUME_BREAKOUT | Today's volume > max volume (21d) or > 2x avg volume (140d) | High |
| GAP_UP / GAP_DOWN | Open vs. prev close exceeds threshold (default 3%) | Medium |
| RESULT_APPROACHING | Quarterly result date within N days (configurable) | Medium |
| 90D_LOW_TOUCH | Today's low <= 90-day low | Medium |
| 90D_HIGH_TOUCH | Today's high >= 90-day high | Medium |
| SCREENER_ENTRY | Stock appears in a screener result for the first time | High |
| SCREENER_EXIT | Stock drops out of a screener result | Low |
| ASM_CHANGE | Stock added to / moved between ASM stages | High |

**Acceptance Criteria:**

- [ ] Given a webhook is registered for 52W_HIGH_INTRADAY events, when a stock hits its 52-week high during intraday refresh, then the webhook POST is delivered within 60 seconds.
- [ ] Given the DSPy app endpoint is temporarily down, when events fire, then they are queued and retried with exponential backoff (max 3 retries over 15 minutes).
- [ ] Given multiple events fire for the same stock within 5 minutes, then they are batched into a single webhook payload to reduce noise.

#### 6.1.6 Authentication & Access Control

Private, invite-only access for 4 fund members plus API key authentication for the agentic app.

- Flask-Login session auth for web UI with email/password.
- API key authentication (Bearer token) for programmatic access. Each user and the agentic app gets a unique API key.
- Admin role can invite/revoke users, manage API keys, and access system health.
- No public registration endpoint. Users are created by admin only.

**Acceptance Criteria:**

- [ ] Given an unauthenticated request to any page or API endpoint, then the user is redirected to login (web) or receives 401 (API).
- [ ] Given an admin revokes a user's access, then their session and API key are invalidated immediately.

#### 6.1.7 Stock Universe Management

Replace the static list in column A of the Final sheet with a managed stock universe.

- Import existing 1,640 stocks from the spreadsheet as the initial universe.
- Each stock record: symbol (NSE/BSE), BSE security code, company name, sector/industry, color classification, active/inactive status.
- Adding a stock triggers automatic historical data backfill (1 year of daily prices).
- Removing a stock marks it inactive (data retained, excluded from screeners).

#### 6.1.8 Web Dashboard

Server-rendered UI (Flask + Jinja2 + HTMX) providing the core screening workflow.

- **Home/Dashboard:** Summary cards showing count of stocks triggering key screeners (52W highs, DMA touches, volume breakouts). Equivalent of the Summary sheet.
- **Screener List:** All 90+ screeners in a categorized sidebar. Click to see matching stocks in a sortable, filterable table.
- **Stock Detail Page:** Single stock with all indicators, price chart (lightweight charting library), color classification controls, comment thread, result date timeline, event history.
- **Screener Builder:** Drag-and-drop or form-based condition composer to create custom screeners.
- **Watchlist:** Personal watchlist per user with at-a-glance indicator summary.

---

### 6.2 Nice-to-Have (P1) — High-Priority Fast Follows

- **Intraday sparkline charts:** Mini price charts on screener result rows showing intraday movement. Lightweight, no charting library overhead.
- **Screener diff view:** Show which stocks entered/exited a screener compared to previous day. Highlights "what changed" rather than just "what is."
- **Telegram/Discord bot integration:** Push critical events (52W high, volume breakout) to a Telegram group chat in addition to webhooks. Low effort, high value for 4 users who are likely on mobile.
- **Bulk color classification:** Select multiple stocks from a screener result and assign color in one action, rather than stock-by-stock.
- **Data source health monitoring:** Dashboard showing last successful pull per data source, failure rate, latency. Alert the admin if any source fails 3 consecutive times.
- **Export to CSV/Excel:** Download any screener result or stock data as CSV or XLSX for ad-hoc analysis in Excel/Google Sheets.
- **Historical screener snapshots:** Store which stocks matched each screener at EOD daily. Enables "show me what this screener looked like last Tuesday."

### 6.3 Future Considerations (P2) — Design For, Do Not Build

- **Broker API integration (Zerodha Kite Connect):** Swap free data sources for official broker APIs for real-time tick data. The data adapter interface must support this without computation layer changes.
- **Backtesting framework:** Evaluate screener strategies over historical periods. Requires the indicator history table (P0) to be populated over time.
- **Options chain integration:** Pull option chain data for stocks in screener results. Requires a separate data source.
- **Sector rotation analysis:** Aggregate screener signals by sector to identify sector-level momentum. Requires sector metadata on all stocks (P0 data model includes this).
- **Multi-fund support:** If any of the 4 members starts a second fund or invites external partners. Current architecture should not preclude adding tenant isolation later.

---

## 7. Data Model

PostgreSQL schema designed for time-series queries, efficient indicator computation, and flexible screener definitions.

### 7.1 Core Tables

| Table | Key Columns & Purpose |
|---|---|
| **stocks** | symbol (PK), bse_code, nse_symbol, company_name, sector, industry, color, color_updated_by, color_updated_at, watchlist_users[], is_active, created_at |
| **daily_prices** | symbol (FK), date, open, high, low, close, volume, adj_close. Composite PK: (symbol, date). Partitioned by month for performance. |
| **indicators** | symbol (FK), date, dma_10/20/50/100/200, wma_5/10/20/30, is_52w_high_intraday, is_52w_high_closing, prev_52w_closing_high, gap_pct, volume_vs_avg_140d, volume_vs_max_21d, result_days_away, 90d_high, 90d_low, etc. One row per stock per day. |
| **result_dates** | symbol (FK), quarter, result_date, announcement_date, purpose, source (BSE/NSE). Replaces ResultDate + Historical Result Dates sheets. |
| **board_meetings** | bse_code, company_name, industry, purpose, meeting_date, announcement_datetime. Replaces Q1BM/Q3BM/Q4BM sheets. |
| **asm_entries** | symbol, effective_date, stage (I/II/III/IV), exchange (BSE/NSE), previous_stage. Replaces ASM sheets. |
| **circuit_bands** | symbol, series, band_pct, effective_date. Replaces Circuit bands sheet. |
| **screeners** | id, name, description, conditions (JSONB), is_builtin, created_by, category. 90 built-in + user-created. |
| **screener_history** | screener_id, symbol, date, action (ENTERED/EXITED). Tracks first appearance and exit. |
| **events** | id, symbol, event_type, event_data (JSONB), created_at, delivered_at. Central event log. |
| **webhooks** | id, url, event_types[], created_by, is_active, last_delivery_at, failure_count. |
| **notes** | id, symbol (FK), author (user or "agent"), content, created_at. Replaces BD (Comments) column. |
| **users** | id, email, name, password_hash, role (admin/member), api_key, is_active, last_login. |
| **audit_log** | id, user_id, action, entity_type, entity_id, old_value, new_value, timestamp. Tracks all mutations. |

### 7.2 Key Indexes

- **daily_prices:** composite index on (symbol, date DESC) for fast lookback queries
- **indicators:** composite index on (date, symbol) + partial indexes on boolean flags (is_52w_high_closing WHERE true)
- **events:** index on (event_type, created_at DESC) for webhook delivery and API queries
- **screener_history:** composite index on (screener_id, date DESC, symbol)

---

## 8. Architecture & Tech Stack

### 8.1 Component Architecture

| Component | Technology | Rationale |
|---|---|---|
| Web Framework | Flask 3.x + Blueprints | Lightweight, Python-native (matches agentic app stack), sufficient for 4 users |
| Database | PostgreSQL 16 | Window functions for DMA/WMA, JSONB for screener conditions, table partitioning for price data |
| Task Queue | Celery 5.x + Redis | Scheduled data pulls, indicator computation, event detection, webhook delivery |
| Cache / Broker | Redis 7.x | Celery broker, response caching, real-time event pub/sub for SSE |
| Frontend | Jinja2 + HTMX + Alpine.js | Server-rendered, minimal JS. HTMX for dynamic updates without SPA complexity |
| Charts | Lightweight-charts (TradingView) | Purpose-built for financial charts, tiny bundle, free for personal use |
| API Docs | Flask-Smorest + OpenAPI 3.1 | Auto-generated API spec. Pydantic-compatible schemas for DSPy integration. |
| ORM | SQLAlchemy 2.x | Mature, supports raw SQL for complex queries, good Pydantic interop |
| Auth | Flask-Login + bcrypt | Simple session auth for 4 users. No need for OAuth/OIDC complexity. |
| Deployment | Docker Compose | Single docker-compose.yml runs Flask, Celery worker, Celery beat, PostgreSQL, Redis. Works on home server and cloud VPS. |
| Data Adapter | Abstract interface + yfinance impl | Pluggable data source. yfinance/jugaad-data for v1, broker API swap later. |

### 8.2 Data Flow

1. Celery Beat triggers scheduled jobs (EOD pull at 4 PM IST, intraday refresh every 3 min during market hours 9:15 AM – 3:30 PM IST, corporate actions daily at 6 PM IST).
2. Data adapter fetches from external sources, normalizes, and writes to PostgreSQL.
3. Indicator computation job runs after each data write. Uses SQL window functions for DMAs/WMAs, Python for complex logic (breakout detection, screener evaluation).
4. Event detector compares current indicators to previous state. New events are written to the events table.
5. Webhook dispatcher picks up new events, matches them against registered webhooks, and delivers HTTP POST payloads. Failed deliveries are retried with exponential backoff.
6. Web UI and API read from PostgreSQL. HTMX partial updates keep the dashboard current without full page reloads.

### 8.3 Deployment Architecture

A single `docker-compose.yml` defines the full stack. Environment variables control all configuration (database URL, Redis URL, API keys, data source selection, webhook secrets).

- **Self-hosted:** `docker-compose up` on a Linux machine with 4GB+ RAM. Data persists in Docker volumes.
- **Cloud VPS:** Same `docker-compose.yml` on a $20/mo DigitalOcean/Hetzner droplet. Add Caddy reverse proxy for HTTPS.
- **Backups:** `pg_dump` cron job to local disk + optional S3-compatible object storage.

---

## 9. Migration from Spreadsheet

One-time data migration from the Google Sheets workbook to seed the system.

| # | Data | Source Sheet(s) | Target Table |
|---|---|---|---|
| 1 | Stock universe (1,640 stocks) | Final: col A (symbol), BF-BG (names), V (industry), BI (color) | stocks |
| 2 | Historical daily prices (~250 days × 1,640 stocks) | TDailyHistoricalData | daily_prices |
| 3 | Historical weekly prices (~52 weeks × 1,640 stocks) | TWeeklyHistoricalData | Computed from daily_prices |
| 4 | 52-week high history | T1YEARHistoricalDataHIGH | Computed from daily_prices |
| 5 | Result dates (all quarters) | ResultDate + Historical Result Dates | result_dates |
| 6 | Board meetings (3 quarters) | Q1BM, Q3BM, Q4BM | board_meetings |
| 7 | ASM surveillance lists | ASM, ASM v1 | asm_entries |
| 8 | Circuit bands | Circuit bands | circuit_bands |
| 9 | Color classifications | Final: col BI (color), ResultDate: col G | stocks.color |
| 10 | Screener definitions (90 filters) | links + Copyoflinks (FILTER formulas) | screeners |
| 11 | Stock comments | Final: col BD | notes |

---

## 10. Success Metrics

### 10.1 Leading Indicators (Week 1–4)

| Metric | Target | Stretch | Measurement |
|---|---|---|---|
| Data freshness | EOD data within 15 min of market close | Within 5 min | Celery task completion timestamp |
| Indicator accuracy | 100% match vs spreadsheet on same data | N/A (binary) | Automated comparison script |
| API response time (p95) | < 500ms single stock | < 200ms | Flask request logging |
| Screener result time | < 2s for full universe | < 500ms | API timing headers |
| Webhook delivery latency | < 60s from event | < 15s | Event created_at vs delivered_at |
| Ingestion success rate | > 99% of scheduled jobs succeed | 99.9% | Celery task status logs |

### 10.2 Lagging Indicators (Month 1–3)

| Metric | Target | Measurement |
|---|---|---|
| Spreadsheet dependency eliminated | 0 manual data pastes per week (was ~5-7) | Team self-report |
| Agentic app integration active | Agent making > 50 API calls/day | API access logs |
| Custom screeners created | > 10 new screeners beyond the original 90 | screeners table count |
| Event-driven research workflows | > 5 automated research reports triggered by webhooks/week | Agentic app logs |
| All 4 members active weekly | 4/4 members log in at least 3x/week | users.last_login |

---

## 11. Timeline & Phasing

Suggested build order, prioritized by which components unblock others:

| Phase | Deliverable | Depends On | Est. Effort |
|---|---|---|---|
| 1 | Database schema + stock universe import + auth | — | 1 week |
| 2 | Price ingestion pipeline (EOD + intraday) | Phase 1 | 1–2 weeks |
| 3 | Indicator computation engine (all 85+ indicators) | Phase 2 | 2 weeks |
| 4 | Screener engine + migration of 90 screeners | Phase 3 | 1–2 weeks |
| 5 | REST API layer (full endpoint set) | Phase 3–4 | 1 week |
| 6 | Event detection + webhook system | Phase 3 | 1–2 weeks |
| 7 | Corporate actions pipeline (result dates, board meetings, ASM, circuit bands) | Phase 1 | 1–2 weeks |
| 8 | Web dashboard UI | Phase 3–5 | 2–3 weeks |
| 9 | Docker deployment + documentation | All above | 3–5 days |

**Total estimated effort:** 10–14 weeks for one developer, or 5–7 weeks with two developers working in parallel (phases 2+7 can parallel, phases 5+6 can parallel, phase 8 can begin once phase 5 has the API skeleton).

---

## 12. Open Questions

| # | Question | Owner | Blocking? |
|---|---|---|---|
| 1 | The color classification system (Pink/Yellow/Orange/Blue/Red/Green) is partially documented. What are the exact definitions? Are any rule-based vs. purely discretionary? | Etah + fund members | Non-blocking (can launch with manual-only colors) |
| 2 | Which BSE/NSE endpoints are stable enough for production scraping? Have any of the 4 members used jugaad-data or similar libraries in production? | Engineering | Blocking for Phase 2 |
| 3 | The DSPy agentic app — does it have specific Pydantic models for stock data today? Should the API response schemas match those models exactly? | Etah | Blocking for Phase 5 |
| 4 | For near-real-time intraday refresh (1–5 min), what is the acceptable cost? yfinance has rate limits; jugaad-data may require login. A broker API removes these limits but costs ~₹2,000/mo. | Etah | Non-blocking (start with EOD, add intraday incrementally) |
| 5 | The spreadsheet has columns for Alert Price 1 and Alert Price 2 (cols W, G4-G5 in links). How are these set and what should happen when triggered? | Etah | Non-blocking |
| 6 | Should the webhook payload format follow any standard (CloudEvents, custom schema)? Does the DSPy app have a preferred input format? | Engineering + Etah | Blocking for Phase 6 |
| 7 | Self-hosted vs. cloud: should the system support both simultaneously (e.g., dev on local, prod on cloud), or will one be primary? | Etah | Non-blocking |
| 8 | The runmacro sheet mentions Google Apps Scripts. Are there existing scripts beyond what is visible in the spreadsheet that should be ported? | Etah | Non-blocking |

---

## 13. Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Free data APIs (yfinance) get rate-limited or shut down | Medium | Data adapter interface allows quick swap. Maintain a 1-day data buffer. Monitor API health actively. |
| BSE/NSE scraping endpoints change format | Medium | Isolate parsing logic. Use versioned schemas. Automated tests catch format changes within 24 hours. |
| Indicator values diverge from spreadsheet during migration | High | Automated comparison suite runs both systems in parallel for 2 weeks. Flag any divergence > 0.01%. |
| Scope creep from the 4 fund members | High | This PRD is the scope contract. P1 items are explicitly deferred. Weekly check-ins to manage requests. |
| PostgreSQL performance with 1,640 stocks × 250 days × 85 indicators | Low | Table partitioning on daily_prices. Materialized views for common screener queries. 4 users = minimal concurrency. |

---

## 14. Glossary

| Term | Definition |
|---|---|
| **DMA** | Daily Moving Average. Average of N most recent daily closing prices (e.g., 200 DMA = average of last 200 closes). |
| **WMA** | Weekly Moving Average. Average of N most recent weekly closing prices. |
| **ASM** | Additional Surveillance Measure. NSE/BSE regulatory list of stocks with unusual price/volume activity. Stages I-IV with increasing trading restrictions. |
| **Circuit Band** | Maximum percentage price movement allowed in a single trading session (e.g., 2%, 5%, 10%, 20%). |
| **52W High** | 52-Week High. The highest price (intraday or closing) a stock has reached in the last 252 trading days. |
| **Breakout (BO)** | When price moves above a significant resistance level (DMA, previous high, etc.) with confirming volume. |
| **Hold/Reverse** | At a DMA/WMA level: Hold = price stays above the average; Reverse = price drops below. Indicates support/resistance behavior. |
| **Color Classification** | Analyst-assigned qualitative tag: Pink (portfolio), Yellow (capex/promoter buying), Orange (post-result breakout), Blue (good results), Red (bad results/breakdown), Green (watchlist). |
| **DSPy** | Stanford NLP framework for programming language models. Used by the fund's agentic equity research application. |
| **OHLCV** | Open, High, Low, Close, Volume. Standard daily price data fields for any security. |
