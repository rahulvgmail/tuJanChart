# StockPulse — Business Requirements Document v1.0

**Indian Equity Technical Screener & Analytics Platform**
*Transforming a 4-year-old spreadsheet POC into a production platform*

| | |
|---|---|
| **Version** | 1.0 |
| **Date** | March 7, 2026 |
| **Author** | Etah |
| **Status** | Draft — For Review |
| **Distribution** | Fund Members (4) |
| **Companion Doc** | StockPulse PRD v1.0 |

---

## Table of Contents

1. [Document Control](#1-document-control)
2. [Business Context](#2-business-context)
3. [Current State Analysis](#3-current-state-analysis)
4. [Stakeholder Analysis](#4-stakeholder-analysis)
5. [Business Requirements](#5-business-requirements)
6. [Business Rules](#6-business-rules)
7. [Business Process Flows](#7-business-process-flows)
8. [Constraints & Assumptions](#8-constraints--assumptions)
9. [Cost-Benefit Analysis](#9-cost-benefit-analysis)
10. [Business Acceptance Criteria](#10-business-acceptance-criteria)
11. [Glossary of Business Terms](#11-glossary-of-business-terms)

---

## 1. Document Control

### 1.1 Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | March 7, 2026 | Etah | Initial draft based on analysis of Q3FY21 spreadsheet workbook |

### 1.2 Approval Matrix

| Role | Name | Approval Scope | Status |
|---|---|---|---|
| Fund Lead / Admin | Etah | Full document, budget, timeline | Pending |
| Fund Member | Member 2 | Business rules, screener logic | Pending |
| Fund Member | Member 3 | Business rules, screener logic | Pending |
| Fund Member | Member 4 | Business rules, screener logic | Pending |

### 1.3 Referenced Documents

| Document | Version | Relationship |
|---|---|---|
| StockPulse PRD v1.0 | 1.0 | Technical implementation spec derived from this BRD |
| Copy of Q3FY21.xlsx | Current | Existing system (Google Sheets workbook) being replaced |

---

## 2. Business Context

### 2.1 Background

Our fund is a private, 4-member investment partnership focused on Indian equities listed on NSE and BSE. For the past four-plus years, the fund has relied on a Google Sheets workbook ("Q3FY21") as its primary stock screening and technical analysis tool. This workbook has grown organically from a simple watchlist into a 15-sheet, 1,640-stock, 85-column analytical engine that tracks daily moving averages, weekly moving averages, 52-week highs, volume breakouts, result date proximity, and approximately 90 named screening strategies.

The workbook works. It has generated real value for the fund. But it was never designed to be a production system, and it has reached hard limits:

- **Scale:** At 1,640 stocks with 85+ computed columns each, the sheet is slow, fragile, and at the mercy of Google Sheets' GOOGLEFINANCE rate limits.
- **Automation:** Seven distinct data sources (daily prices, weekly prices, 52-week highs, board meetings, result dates, ASM lists, circuit bands) require manual copy-paste operations. The most recent update was March 4, 2026—three days stale at time of writing.
- **Integration:** The fund has built a separate equity research agentic application using Python, Pydantic, and DSPy. This application needs programmatic access to screener results to function. Today, a human must manually extract data from the spreadsheet and relay it to the agent—a process that defeats the purpose of having an autonomous research agent.
- **Collaboration:** Four people sharing a single Google Sheet means overwriting each other's color classifications, losing comment history, and having no audit trail of who changed what.

### 2.2 Business Opportunity

Converting this spreadsheet into a proper web application is not a technology exercise for its own sake. It unlocks three concrete business capabilities:

**1. Automated signal detection:** The fund's edge comes from catching technical breakouts (52-week highs, DMA reversals, volume spikes) near earnings announcements. Today, a 45-minute manual refresh cycle means signals are spotted hours late—after the move has already happened. Automated, near-real-time computation reduces this to minutes.

**2. Agentic research pipeline:** The DSPy research agent can analyze a stock in depth (reading filings, comparing peers, assessing sector trends), but only if it knows which stocks to look at. The screener platform feeding the agent via API creates an end-to-end pipeline: market data → technical screening → AI-driven fundamental analysis → investment recommendation. No human bottleneck in the middle.

**3. Decision audit trail:** When the fund reviews past decisions, there is currently no record of what the indicators looked like when a buy/sell was made. A database-backed system stores historical indicator snapshots, screener membership history, and timestamped annotations—creating an institutional memory the spreadsheet cannot provide.

### 2.3 Strategic Alignment

This initiative aligns with three strategic priorities the fund has discussed:

- **Reduce operational overhead:** Less time on data plumbing means more time on research and decision-making.
- **Scale the research capability:** The agentic app is the fund's bet on AI-augmented investing. StockPulse is the data backbone it needs to function.
- **Professionalize the infrastructure:** If the fund grows (more capital, more members, more stocks), the current spreadsheet cannot scale. A proper platform can.

---

## 3. Current State Analysis

### 3.1 System Inventory

The existing workbook contains 15 sheets serving distinct functions:

| Sheet | Function | Rows | Update | Freshness |
|---|---|---|---|---|
| Final | Central computation hub: 85+ indicator columns for each stock | 1,660 | Formulas (auto) | Real-time* |
| TDailyHistoricalData | 1-year daily close prices (250+ columns per stock) | 1,600 | Manual paste | 3 days stale |
| TWeeklyHistoricalData | 1-year weekly close prices (52+ columns per stock) | 1,600 | Manual paste | 3 days stale |
| T1YEARHistoricalDataHIGH | 1-year daily high prices for 52W high detection | 1,600 | Manual paste | 3 days stale |
| ResultDate | Quarterly result dates for ~4,000 securities | 4,182 | Manual update | Unknown |
| Historical Result Dates | Archive of result dates across 4+ quarters | 4,081 | Manual paste | Quarterly |
| Q4BM / Q3BM / Q1BM | Board meeting data from BSE (3 quarters) | ~4,400 each | Manual paste | Quarterly |
| CurrentQtrRDfilterData | Filtered current-quarter result dates | 4,241 | Manual paste | Unknown |
| ASM / ASM v1 | NSE Additional Surveillance Measure lists | 361 / 981 | Manual paste | Unknown |
| Circuit bands | Price circuit limits per stock | 1,937 | Manual paste | Unknown |
| links / Copyoflinks | ~90 named screener definitions (FILTER formulas) | 1,056 | Manual formula | N/A |
| Summary | Dashboard: DMA touches, 52W highs, 90D lows | 40 | Formulas (auto) | Real-time* |
| runmacro | Buttons to trigger Google Apps Script refresh jobs | 28 | Manual trigger | Last: Mar 4 |
| testsheet | Scratch pad for testing GOOGLEFINANCE formulas | 141 | Ad hoc | N/A |

*\* "Real-time" is conditional on GOOGLEFINANCE refreshing, which is throttled by Google to approximately 15-minute intervals and frequently returns stale or error values.*

### 3.2 Pain Points (Quantified)

| Pain Point | Impact | Evidence |
|---|---|---|
| Manual data refresh | ~45 min/day wasted | 7 data sources, each requiring export → paste → verify. runmacro sheet shows last run 3 days ago. |
| Stale indicators | Missed signals | If historical data is 3 days old, all DMAs/WMAs computed from it are wrong. 52W high detection uses stale max values. |
| No API for agentic app | Agent is crippled | The DSPy research agent exists and is functional but cannot access screener results without human relay. |
| No alerting | Delayed action | A stock hitting 52W high during market hours goes unnoticed until someone manually scans 1,640 rows. |
| Collaboration conflicts | Lost annotations | Color classifications in column BI are overwritten without history. Comments in column BD have no attribution. |
| No decision audit trail | Cannot learn from past | When reviewing a past trade, there is no record of what indicators showed at the time of decision. |
| GOOGLEFINANCE fragility | Cascading errors | Rate limits cause #N/A errors that propagate through dependent formulas. Biweekly BO and weekly BO columns show #N/A. |

### 3.3 What Works Well (Preserve)

Not everything about the spreadsheet is broken. The following strengths must be preserved in the new system:

- **Comprehensive indicator coverage:** The 85+ columns in the Final sheet represent years of iterative refinement. Each DMA, WMA, breakout flag, and proximity check was added because it helped make better decisions. All must be replicated.
- **Screener library:** The ~90 named screeners in links/Copyoflinks encode sophisticated multi-condition strategies (e.g., "10 DMA touch + Orange color + result declared in last 10 days + high volume"). These represent hard-won domain knowledge.
- **Color classification system:** The 6-color system (Pink, Yellow, Orange, Blue, Red, Green) is a shared qualitative vocabulary among the 4 members. It bridges technical signals and human judgment.
- **Single-pane-of-glass:** The Final sheet, despite its 85 columns, gives a unified view of every stock. The new system must not fragment this into disconnected pages.

---

## 4. Stakeholder Analysis

| Stakeholder | Role | Key Interest | Influence | Engagement |
|---|---|---|---|---|
| **Etah** | Fund Lead / Admin | System reliability, API for agentic app, deployment control | High | Decision maker |
| **Member 2** | Fund Member | Screener accuracy, color classification workflow, daily usability | High | Active user |
| **Member 3** | Fund Member | Screener accuracy, new screener creation, watchlist management | High | Active user |
| **Member 4** | Fund Member | Screener accuracy, notification alerts, mobile access to results | High | Active user |
| **Agentic App** | System consumer | Reliable API, low latency, structured event webhooks, Pydantic-compatible schemas | Medium | Automated |

All 4 human stakeholders are both commissioners and daily users of the system. There are no external stakeholders, regulators, or customers. This simplifies governance: decisions can be made by consensus among the 4 members, with Etah holding tiebreaker authority as admin.

---

## 5. Business Requirements

Business requirements describe what the business needs, independent of any specific technical solution. Each requirement is numbered BR-XXX for traceability to the PRD.

### 5.1 Data Availability & Freshness

**BR-001:** The system must automatically acquire end-of-day OHLCV price data for all stocks in the universe within 15 minutes of NSE/BSE market close (3:30 PM IST), with zero manual intervention.

**BR-002:** The system must provide near-real-time price data during market hours (9:15 AM – 3:30 PM IST) with a maximum staleness of 5 minutes.

**BR-003:** The system must automatically acquire quarterly result dates, board meeting dates, and corporate action announcements from BSE and NSE within 24 hours of publication.

**BR-004:** The system must automatically acquire ASM surveillance lists and circuit band data from NSE daily.

**BR-005:** The system must retain at minimum 1 year of historical daily price data and 2 years of weekly data per stock for moving average computation.

**BR-006:** The system must support swapping between data providers (free APIs today, paid broker APIs in the future) without disrupting computation or reporting.

### 5.2 Technical Analysis & Screening

**BR-007:** The system must compute all technical indicators currently present in the spreadsheet's Final sheet, including: 10/20/50/100/200 DMA, 5/10/20/30 WMA, hold/break/reverse signals, 52-week high detection (intraday, closing, historical), volume analytics (max, average, breakout), gap-up/gap-down, 90-day high/low, and result date proximity.

**BR-008:** Computed indicators must be numerically identical (within 0.01% tolerance) to the spreadsheet's values when given the same input data. This is the acceptance bar for migration.

**BR-009:** The system must support the existing library of approximately 90 named screening strategies, each producing the same stock set as the corresponding FILTER formula in the spreadsheet.

**BR-010:** Fund members must be able to create, modify, and delete custom screening strategies by combining conditions through the user interface, without writing code or formulas.

**BR-011:** The system must track screener membership history—recording when each stock enters and exits each screener's result set—to support signal trajectory analysis.

### 5.3 Collaboration & Annotation

**BR-012:** Fund members must be able to assign one of 6 color classifications (Pink, Yellow, Orange, Blue, Red, Green) to any stock, with each classification change recording the user, timestamp, and optional comment.

**BR-013:** Fund members and the agentic app must be able to attach timestamped notes to any stock, creating a threaded annotation history visible to all members.

**BR-014:** All data mutations (color changes, notes, screener creation, stock universe changes) must be recorded in an audit log showing who, what, when, and the before/after values.

**BR-015:** Each member must have a personal watchlist. Watchlist stocks should surface prominently in the dashboard and be subscribable for event notifications.

### 5.4 Agentic App Integration

**BR-016:** All stock data, indicators, and screener results must be accessible via authenticated REST API endpoints returning structured JSON.

**BR-017:** The API response schemas must be compatible with Pydantic model deserialization, as the consuming application is built on Python/Pydantic/DSPy.

**BR-018:** The system must support webhook subscriptions: external systems register a URL and select event types, and the system delivers HTTP POST payloads when matching events occur.

**BR-019:** Webhook delivery must be reliable: failed deliveries must be retried with exponential backoff, and persistent failures must be surfaced to the admin.

**BR-020:** The agentic app must be able to write back to the system (attach research notes to stocks) to close the analysis loop.

### 5.5 Event Detection & Alerting

**BR-021:** The system must detect and record technical events when they occur, including: 52-week high (intraday and closing), DMA/WMA crossovers, volume breakouts, gap-up/gap-down, 90-day extremes, result date proximity, screener entry/exit, and ASM stage changes.

**BR-022:** Detected events must be delivered to registered webhooks within 60 seconds of detection.

**BR-023:** Events must be persisted with full context (symbol, event type, indicator values at time of event) for historical analysis.

### 5.6 Access Control & Security

**BR-024:** The system must be private and access-controlled. No public registration. Users are created by the admin via invitation only.

**BR-025:** The system must support two authentication mechanisms: session-based login for the web UI and API key (Bearer token) for programmatic access.

**BR-026:** The admin must be able to invite new members and revoke access immediately (invalidating sessions and API keys).

**BR-027:** All communication must be encrypted in transit (HTTPS). API keys must be stored hashed in the database.

### 5.7 Operations & Reliability

**BR-028:** The system must be deployable on both a self-hosted Linux machine and a cloud VPS using the same deployment artifact (Docker).

**BR-029:** The admin must have visibility into system health: last successful data pull per source, failed jobs, queue depth, and database size.

**BR-030:** The system must support automated daily database backups with a retention period of at least 30 days.

**BR-031:** The system must be recoverable from backup within 1 hour.

---

## 6. Business Rules

Business rules encode the domain logic that the system must enforce. These are derived from the formulas and conventions in the existing spreadsheet.

### 6.1 Moving Average Computation

**Rule 6.1.1:** A Daily Moving Average (DMA) of period N is the arithmetic mean of the N most recent daily closing prices, including the current day's close if available. For example, the 200 DMA on March 7 is the average of closes from approximately July 2025 through March 7, 2026.

**Rule 6.1.2:** A Weekly Moving Average (WMA) of period N is the arithmetic mean of the N most recent weekly closing prices. A "weekly close" is the closing price on the last trading day of the week (typically Friday).

**Rule 6.1.3:** If fewer than N data points are available (e.g., a newly listed stock), the moving average is computed from all available data points and flagged as "insufficient data."

### 6.2 DMA/WMA Signal Logic

**Rule 6.2.1:** A "touch" occurs when the current day's price range (low to high) straddles a moving average value: `today_low < DMA AND today_high > DMA`.

**Rule 6.2.2:** When a touch occurs, the signal is "Hold" if the current price is at or above the DMA value, or "Reverse" if the current price is below.

**Rule 6.2.3:** If no touch occurs, no Hold/Reverse signal is generated for that DMA/WMA on that day.

### 6.3 52-Week High Detection

**Rule 6.3.1:** "52-week high (intraday)" is true when today's high price equals the maximum high price across the last 252 trading days.

**Rule 6.3.2:** "52-week closing high" is true when the current close is greater than or equal to the maximum closing price across the last 252 trading days.

**Rule 6.3.3:** The system must track the date on which the 52-week high was last achieved, to support "52-week high age" filters (e.g., "52-week high older than 3 months").

### 6.4 Volume Breakout

**Rule 6.4.1:** Volume breakout is detected when today's volume exceeds at least one of: max volume over 21 trading days, average volume over 140 trading days, or average volume over 280 trading days.

**Rule 6.4.2:** Volume periods (21d, 140d, 280d) must be configurable per deployment without code changes.

### 6.5 Gap-Up / Gap-Down

**Rule 6.5.1:** A gap-up occurs when `(today_open − prev_close) / prev_close × 100` exceeds a positive threshold (default: 3%).

**Rule 6.5.2:** A gap-down occurs when the same calculation yields a value below the negative threshold (default: −3%).

**Rule 6.5.3:** The gap threshold must be configurable.

### 6.6 Result Date Proximity

**Rule 6.6.1:** The system must calculate the number of calendar days between the current date and the nearest upcoming quarterly result date for each stock.

**Rule 6.6.2:** A stock is flagged as "result approaching" when the result date is within N calendar days (configurable; current default windows are 7, 10, and 15 days).

**Rule 6.6.3:** A stock is flagged as "result declared" when the result date is in the past and within M calendar days (configurable; current default: 10 days).

### 6.7 Color Classification

**Rule 6.7.1:** Each stock carries exactly one color classification at any time. The 6 colors and their general meanings (as observed from the spreadsheet) are:

- **Pink:** Portfolio stocks (currently held positions)
- **Yellow:** Capex stories, promoter buying, positive management outlook
- **Orange:** Post-result breakout, 52-week high after results, circuit after results, high volume jump after results
- **Blue:** Good quarterly results
- **Red:** Bad results or technical breakdown
- **Green:** Watchlist / tracking interest

**Rule 6.7.2:** Color assignment is a human judgment call by any fund member. The system enforces no automated color assignment but must record who set each color and when.

**Rule 6.7.3:** Color history must be preserved. Changing a stock's color creates a new audit record; it does not overwrite the previous one.

### 6.8 Screener Composition

**Rule 6.8.1:** A screener is a named set of conditions combined with AND logic. A stock matches the screener if and only if it satisfies all conditions.

**Rule 6.8.2:** The 90 built-in screeners are read-only (cannot be modified or deleted by users). Users can create copies to customize.

**Rule 6.8.3:** Screener results must be deterministic: given the same indicator values, the same stock set must be returned every time.

### 6.9 ASM & Circuit Band Treatment

**Rule 6.9.1:** Stocks in ASM Stage III or Stage IV should be visually flagged in all screener results and stock detail views as a risk indicator.

**Rule 6.9.2:** ASM stage changes (entry, stage promotion, exit) must generate events that can trigger webhooks.

**Rule 6.9.3:** Circuit band data is informational. It does not affect indicator computation but should be displayed on the stock detail page.

---

## 7. Business Process Flows

### 7.1 Daily Screening Workflow (Current vs. Future)

**CURRENT (manual, ~60 minutes):**

1. Open Google Sheet. Wait for GOOGLEFINANCE formulas to refresh (~5–15 min).
2. Check if historical data is stale. If yes, export from data sources, paste into TDailyHistoricalData / TWeeklyHistoricalData / T1YEARHistoricalDataHIGH sheets (~20–30 min).
3. Click macro buttons on runmacro sheet to recalculate (~5 min).
4. Navigate to links or Summary sheet. Scroll through screener results. Identify interesting stocks.
5. Manually copy findings to the agentic app or a Telegram group.

**FUTURE (automated, ~5 minutes of human attention):**

1. Celery beat auto-triggers EOD data pull at 4 PM IST. Indicators recompute in ~3 min. Zero human action.
2. Events fire webhooks to the agentic app. It begins automated deep-dive research on triggered stocks.
3. Fund member opens StockPulse dashboard. Reviews pre-computed screener cards. Clicks into interesting screeners. Reviews agent-generated research notes already attached to stocks.
4. Member updates color classifications, adds personal notes, manages watchlist.

### 7.2 New Stock Addition (Current vs. Future)

**CURRENT:** Insert a row in the Final sheet. Copy all 85+ formulas from an adjacent row. Add the stock to ResultDate, TDailyHistoricalData, TWeeklyHistoricalData, and T1YEARHistoricalDataHIGH. Paste historical data. Run macros. Verify. Takes ~30 minutes per stock and is error-prone.

**FUTURE:** POST /api/universe with the stock symbol. The system auto-resolves the BSE/NSE code, backfills 1 year of price data, computes all indicators, and the stock appears in screener results within 15 minutes. Zero formula copying.

### 7.3 Quarterly Result Date Update (Current vs. Future)

**CURRENT:** Each quarter, manually visit BSE/NSE announcement pages, download board meeting data, paste into Q1BM/Q3BM/Q4BM sheets, then manually update ResultDate and CurrentQtrRDfilterData sheets for ~4,000 securities. Multi-hour process.

**FUTURE:** Celery job checks BSE API daily. New board meetings and result dates are ingested automatically. Result proximity indicators update without intervention.

---

## 8. Constraints & Assumptions

### 8.1 Constraints

- **Budget:** No significant recurring cost. The system must run on infrastructure costing less than ₹2,000/month (cloud VPS) or on existing hardware (home server). Data sources should be free or low-cost.
- **Team size:** Development will likely be done by 1–2 people. The architecture must be simple enough for a small team to maintain without dedicated DevOps.
- **Data source availability:** Free Indian market data APIs (yfinance, jugaad-data) are unofficial and may experience rate limits, outages, or format changes. The system must handle graceful degradation.
- **Regulatory:** This is a private tool for a private fund. There are no SEBI regulatory requirements for the tool itself, though the fund's trading activities are separately regulated.
- **Privacy:** Stock universe composition, screener logic, and color classifications are proprietary intellectual property of the fund. The system must not leak this data.

### 8.2 Assumptions

- All 4 fund members have reliable internet access and use desktop/laptop browsers as their primary interface.
- The DSPy agentic app is functional and can consume REST APIs with JSON responses. It does not require GraphQL, gRPC, or WebSocket APIs.
- The stock universe will remain in the range of 1,500–3,000 stocks. A 10x increase in universe size is not expected.
- Market hours for NSE/BSE are 9:15 AM – 3:30 PM IST, Monday through Friday, excluding market holidays.
- The fund members are technically literate and comfortable with web applications. No specialized UX training is needed.

---

## 9. Cost-Benefit Analysis

### 9.1 Costs

| Item | Type | Estimate | Notes |
|---|---|---|---|
| Development effort | One-time | 10–14 weeks (1 dev) | Or 5–7 weeks with 2 devs |
| Cloud VPS hosting | Monthly | ~₹1,500/mo | 4GB RAM droplet + managed DB |
| Domain + SSL | Annual | ~₹1,000/yr | Optional if self-hosted only |
| Data APIs | Monthly | ₹0 (v1) / ₹2,000 (v2) | Free APIs in v1; broker API in v2 |
| Maintenance | Ongoing | ~2–4 hrs/week | Monitoring, data source fixes, minor enhancements |

### 9.2 Benefits

| Benefit | Value | Measurement |
|---|---|---|
| Time saved on data refresh | ~45 min/day × 250 trading days = 187 hrs/yr | Elimination of manual data paste operations |
| Faster signal detection | Hours → minutes | Time from market event to fund awareness. Direct impact on entry/exit timing. |
| Unlocked agentic pipeline | Qualitative: transformational | The DSPy agent can finally operate autonomously. Research throughput scales from human to machine speed. |
| Decision audit trail | Qualitative: risk reduction | Ability to review past decisions in context. Supports learning and accountability. |
| Collaboration quality | Qualitative: reduced friction | No more overwritten classifications. Attributed annotations. Shared watchlists. |

### 9.3 Break-Even Assessment

The primary cost is development time. Ongoing costs (~₹1,500–3,500/month) are negligible relative to the fund's AUM. The time savings alone (187 hours/year across the team) justify the build within the first year. The real ROI, however, is not in time savings—it is in the agentic pipeline enablement. The fund invested in building a DSPy research agent that is currently operating at a fraction of its capability because it has no data feed. StockPulse is the missing infrastructure that makes that investment productive.

---

## 10. Business Acceptance Criteria

The system is accepted for production use when all of the following conditions are met:

| # | Criterion | Verified By | Method |
|---|---|---|---|
| AC-1 | All 1,640 stocks from the spreadsheet are present in the system with correct symbols, names, and color classifications | Etah | Data comparison |
| AC-2 | EOD data for all stocks is ingested automatically without manual intervention for 5 consecutive trading days | Etah | Job monitoring |
| AC-3 | All 85+ indicators match spreadsheet values within 0.01% tolerance on a defined test date | All members | Automated test |
| AC-4 | All 90 built-in screeners return the same stock sets as the spreadsheet's FILTER formulas on the same test date | All members | Automated test |
| AC-5 | The DSPy agentic app can successfully call /api/screeners/{id}/results and deserialize the response into its Pydantic models | Etah | Integration test |
| AC-6 | At least one webhook event type (52W_HIGH) is successfully delivered to the agentic app's endpoint | Etah | End-to-end test |
| AC-7 | All 4 members can log in, view screeners, assign colors, add notes, and manage their watchlist | All members | User testing |
| AC-8 | The system runs continuously for 5 trading days on the target deployment environment without crashes or data gaps | Etah | Soak test |
| AC-9 | The Google Sheets workbook is no longer needed for daily operations (may be retained as a backup/reference) | All members | Team consensus |

---

## 11. Glossary of Business Terms

| Term | Definition |
|---|---|
| **Universe** | The complete set of stocks tracked by the system. Currently ~1,640 NSE/BSE equities. |
| **Screener** | A named set of conditions that filters the universe to a subset of stocks matching all conditions. |
| **Indicator** | A computed value derived from price, volume, or date data (e.g., 200 DMA, volume breakout flag). |
| **Signal** | A meaningful change in an indicator (e.g., price crossing above 200 DMA, new 52-week high). |
| **Event** | A recorded occurrence of a signal, timestamped and stored for delivery and history. |
| **Color Classification** | A 6-category qualitative tag (Pink/Yellow/Orange/Blue/Red/Green) assigned by fund members. |
| **Agentic App** | The fund's Python/Pydantic/DSPy-based AI research application that consumes StockPulse data. |
| **DMA** | Daily Moving Average. Arithmetic mean of N recent daily closing prices. |
| **WMA** | Weekly Moving Average. Arithmetic mean of N recent weekly closing prices. |
| **Breakout (BO)** | Price exceeding a resistance level (e.g., DMA, 52W high) with volume confirmation. |
| **ASM** | Additional Surveillance Measure. NSE/BSE regulatory stages (I–IV) for volatile stocks. |
| **EOD** | End of Day. Refers to data collected after market close. |
| **OHLCV** | Open, High, Low, Close, Volume. Standard daily price data. |
| **Result Date** | The date a company announces quarterly financial results to stock exchanges. |
