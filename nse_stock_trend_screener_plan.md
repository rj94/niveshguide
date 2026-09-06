# NSE Stock Trend Screener - Architecture and Implementation Plan

## 1. Objective

Build a scalable stock-trend discovery system for NSE-listed stocks.

The system should:

1. Maintain a master list of NSE symbols.
2. Divide the symbols into multiple Google Spreadsheets to avoid performance and calculation issues.
3. Use `GOOGLEFINANCE` in Google Sheets to collect the latest market data where available.
4. Pull data from all spreadsheets into a central database.
5. Calculate moving averages and technical trend signals efficiently.
6. Store historical snapshots.
7. Expose the processed data to a website/dashboard and stock screener.
8. Identify stocks in strong uptrends, fresh momentum phases, long-term uptrends, breakout zones, and downtrends.

---

# 2. Problem With a Single Large Google Spreadsheet

The desired output contains columns such as:

| Symbol | Market Cap | LTP | High | Prev Close | 52 Week High | 52 Week Low | 3 Days MA | 7 Days MA | 21 Days MA | 50 Days MA | 200 Days MA | Crossover 3D > 7D | LTP > 21D | LTP > 200D | Crossover 50D > 200D | Trend | PE | EPS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---|---:|---:|
| EPIGRAL | 5327.95 | 1235 | 1241 | 1206.4 | 1838.9 | 807 | 1233 | 1226 | 1146 | 1125 | 1085 | Yes | Yes | Yes | Yes | Up | 19.66 | 62.82 |
| APLAPOLLO | 62700.62 | 2270 | 2278.4 | 2188 | 2301.4 | 1578 | 2266 | 2179 | 2111 | 1966 | 1959 | Yes | Yes | Yes | Yes | Up | 51.28 | 44.27 |
| ABBOTINDIA | 55620.05 | 26200 | 26745 | 26350 | 32775 | 25150 | 26175 | 26383 | 26835 | 27476 | 26673 | No | No | No | Yes | Down | 34.48 | 759.88 |

When this calculation is extended to the complete NSE universe, Google Sheets can become slow or hang because:

- Every `GOOGLEFINANCE` formula can trigger a separate calculation.
- Historical data requests for moving averages are especially expensive.
- Thousands of symbols multiplied by multiple indicators can create tens of thousands of calculations.
- A single sheet becomes a single point of failure.
- One slow recalculation can affect the complete stock universe.

The solution is to split collection into smaller batches and move historical calculations into the backend/database.

---

# 3. Recommended Architecture

```text
                    ┌─────────────────────┐
                    │ NSE Symbol Master   │
                    └──────────┬──────────┘
                               │
                  Split into 400-500 symbols
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ▼                    ▼                    ▼
   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
   │ Batch 01     │     │ Batch 02     │ ... │ Batch 06     │
   │ Google Sheet │     │ Google Sheet │     │ Google Sheet │
   │ 400-500      │     │ 400-500      │     │ Remaining    │
   └──────┬───────┘     └──────┬───────┘     └──────┬───────┘
          │                    │                    │
          └────────────────────┼────────────────────┘
                               ▼
                     ┌──────────────────┐
                     │ ETL / Ingestion  │
                     │ Python Scheduler │
                     └────────┬─────────┘
                              ▼
                  ┌────────────────────────┐
                  │ PostgreSQL Database    │
                  │                        │
                  │ Stocks                 │
                  │ Daily Snapshots        │
                  │ Price History          │
                  │ Technical Indicators   │
                  │ Trend History          │
                  └───────────┬────────────┘
                              ▼
                     ┌──────────────────┐
                     │ API / Backend    │
                     └────────┬─────────┘
                              ▼
                  ┌────────────────────────┐
                  │ Website / Dashboard    │
                  │                        │
                  │ Strong Momentum        │
                  │ Fresh Uptrend          │
                  │ Breakout Watchlist     │
                  │ Long-Term Uptrend      │
                  │ Weak / Avoid           │
                  └────────────────────────┘
```

---

# 4. Batch Strategy

## Recommended batch size

Use approximately **400 to 500 symbols per spreadsheet**.

Although 500-700 symbols may work, 400-500 provides a better margin for:

- Formula recalculation.
- API ingestion.
- Spreadsheet editing.
- Failure isolation.
- Future additional columns.
- Historical data requirements.

Example:

```text
NSE Master Universe
│
├── NSE Batch 01: Symbol 1-500
├── NSE Batch 02: Symbol 501-1000
├── NSE Batch 03: Symbol 1001-1500
├── NSE Batch 04: Symbol 1501-2000
├── NSE Batch 05: Symbol 2001-2500
└── NSE Batch 06: Remaining symbols
```

All spreadsheets should use exactly the same column layout.

---

# 5. Google Spreadsheet Structure

Each batch spreadsheet should contain the following tabs.

## 5.1 CONFIG

Example:

| Setting | Value |
|---|---|
| Batch ID | NSE_01 |
| Exchange | NSE |
| Symbol Count | 500 |
| Refresh Date | Automatically updated |
| Status | Active |

## 5.2 STOCK_DATA

This is the main sheet read by the ETL pipeline.

Recommended columns:

| Column | Field |
|---|---|
| A | Symbol |
| B | Market Cap |
| C | LTP |
| D | Day High |
| E | Previous Close |
| F | 52 Week High |
| G | 52 Week Low |
| H | 3 Day MA |
| I | 7 Day MA |
| J | 21 Day MA |
| K | 50 Day MA |
| L | 200 Day MA |
| M | 3D > 7D |
| N | LTP > 21D |
| O | LTP > 200D |
| P | 50D > 200D |
| Q | Trend Score |
| R | Trend |
| S | PE |
| T | EPS |
| U | Distance from 52W High |
| V | Last Updated |

The exact Google Sheets implementation can be adjusted based on which attributes are supported for the exchange and symbols being queried.

---

# 6. Example GOOGLEFINANCE Formulas

Assume the NSE symbol is in `A2`.

## LTP

```excel
=IFERROR(GOOGLEFINANCE("NSE:"&A2,"price"),)
```

## Day High

```excel
=IFERROR(GOOGLEFINANCE("NSE:"&A2,"high"),)
```

## Previous Close

```excel
=IFERROR(GOOGLEFINANCE("NSE:"&A2,"closeyest"),)
```

## 52 Week High

```excel
=IFERROR(GOOGLEFINANCE("NSE:"&A2,"high52"),)
```

## 52 Week Low

```excel
=IFERROR(GOOGLEFINANCE("NSE:"&A2,"low52"),)
```

### Important implementation note

The spreadsheet should primarily be treated as a **data collection and lightweight calculation layer**.

Avoid independently requesting historical data for 3-day, 7-day, 21-day, 50-day, and 200-day averages for every symbol whenever possible.

The moving averages should preferably be calculated from centrally stored historical price data.

---

# 7. Moving Average Calculation Strategy

For every stock, maintain historical closing prices.

Conceptually:

| Symbol | Date | Close |
|---|---|---:|
| EPIGRAL | 2026-01-01 | 1100 |
| EPIGRAL | 2026-01-02 | 1112 |
| EPIGRAL | 2026-01-03 | 1125 |
| ... | ... | ... |

The backend can then calculate:

```text
3D MA   = Average of the latest 3 trading closes
7D MA   = Average of the latest 7 trading closes
21D MA  = Average of the latest 21 trading closes
50D MA  = Average of the latest 50 trading closes
200D MA = Average of the latest 200 trading closes
```

## Recommended approach

Instead of this:

```text
2500 stocks
×
5 separate historical GOOGLEFINANCE calculations
=
12500+ expensive calculations
```

Use:

```text
Historical price data
        │
        ▼
Database
        │
        ▼
Python / SQL calculations
        │
        ├── 3D MA
        ├── 7D MA
        ├── 21D MA
        ├── 50D MA
        └── 200D MA
```

This makes the architecture substantially more scalable.

---

# 8. Trend Signal Logic

The system should not rely only on a binary `Up` or `Down` trend.

Instead, calculate individual signals.

## Signal 1: Short-Term Momentum

```text
3D MA > 7D MA
```

## Signal 2: Medium-Term Strength

```text
LTP > 21D MA
```

## Signal 3: Intermediate Trend

```text
21D MA > 50D MA
```

## Signal 4: Long-Term Strength

```text
LTP > 200D MA
```

## Signal 5: Long-Term Trend Confirmation

```text
50D MA > 200D MA
```

---

# 9. Trend Score

Assign one point for every bullish condition.

| Condition | Score |
|---|---:|
| 3D MA > 7D MA | +1 |
| LTP > 21D MA | +1 |
| 21D MA > 50D MA | +1 |
| LTP > 200D MA | +1 |
| 50D MA > 200D MA | +1 |

Maximum score:

```text
5
```

## Trend classification

| Score | Trend |
|---:|---|
| 5 | Strong Uptrend |
| 4 | Uptrend |
| 3 | Mild Uptrend |
| 2 | Neutral |
| 1 | Downtrend |
| 0 | Strong Downtrend |

The classification can later be expanded with bearish scores, volatility, volume confirmation, and breakout conditions.

---

# 10. Additional Metric: Distance from 52 Week High

Calculate:

```text
Distance from 52W High = ((LTP / 52W High) - 1) × 100
```

Example:

| Symbol | LTP | 52W High | Distance |
|---|---:|---:|---:|
| APLAPOLLO | 2270 | 2301.4 | -1.36% |
| EPIGRAL | 1235 | 1838.9 | -32.84% |

This is useful because a stock with a strong trend score that is close to its 52-week high may be a potential momentum or breakout candidate.

---

# 11. Stock Screener Categories

The website should expose predefined trend screens.

## 11.1 Strong Momentum

Conditions:

```text
3D MA > 7D MA
AND
LTP > 21D MA
AND
21D MA > 50D MA
AND
LTP > 200D MA
AND
50D MA > 200D MA
```

Optional:

```text
Distance from 52W High > -10%
```

These stocks receive the highest momentum score.

---

## 11.2 Fresh Uptrend

Conditions can include:

```text
3D MA recently crossed above 7D MA
AND
LTP > 21D MA
```

The system should store the previous day's signal so that it can detect a new crossover rather than only the current state.

Example:

```text
Yesterday: 3D MA <= 7D MA
Today:    3D MA > 7D MA
```

Result:

```text
Fresh Bullish Crossover
```

---

## 11.3 Long-Term Uptrend

```text
LTP > 200D MA
AND
50D MA > 200D MA
```

These stocks may not necessarily have immediate short-term momentum but remain structurally strong.

---

## 11.4 Breakout Watchlist

Example conditions:

```text
Distance from 52W High >= -5%
AND
LTP > 21D MA
AND
50D MA > 200D MA
```

Later enhancements can add:

```text
Volume > 20D Average Volume
```

---

## 11.5 Weak / Avoid

```text
LTP < 21D MA
AND
LTP < 50D MA
AND
LTP < 200D MA
AND
50D MA < 200D MA
```

---

# 12. Database Architecture

PostgreSQL is recommended as the central storage layer.

## 12.1 `stocks`

```sql
CREATE TABLE stocks (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(30) UNIQUE NOT NULL,
    company_name VARCHAR(255),
    exchange VARCHAR(10) DEFAULT 'NSE',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 12.2 `stock_snapshots`

Stores the latest or daily market/fundamental snapshot.

```sql
CREATE TABLE stock_snapshots (
    id BIGSERIAL PRIMARY KEY,

    stock_id INTEGER NOT NULL REFERENCES stocks(id),

    snapshot_date DATE NOT NULL,

    market_cap NUMERIC,
    ltp NUMERIC,
    day_high NUMERIC,
    prev_close NUMERIC,

    high_52_week NUMERIC,
    low_52_week NUMERIC,

    pe NUMERIC,
    eps NUMERIC,

    source VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(stock_id, snapshot_date)
);
```

---

## 12.3 `stock_prices`

Stores daily price history.

```sql
CREATE TABLE stock_prices (
    id BIGSERIAL PRIMARY KEY,

    stock_id INTEGER NOT NULL REFERENCES stocks(id),

    price_date DATE NOT NULL,

    open NUMERIC,
    high NUMERIC,
    low NUMERIC,
    close NUMERIC,
    volume BIGINT,

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(stock_id, price_date)
);
```

Indexes:

```sql
CREATE INDEX idx_stock_prices_stock_date
ON stock_prices(stock_id, price_date DESC);
```

---

## 12.4 `stock_indicators`

```sql
CREATE TABLE stock_indicators (
    id BIGSERIAL PRIMARY KEY,

    stock_id INTEGER NOT NULL REFERENCES stocks(id),

    calculation_date DATE NOT NULL,

    ma_3 NUMERIC,
    ma_7 NUMERIC,
    ma_21 NUMERIC,
    ma_50 NUMERIC,
    ma_200 NUMERIC,

    crossover_3_7 BOOLEAN,
    above_ma_21 BOOLEAN,
    above_ma_200 BOOLEAN,
    golden_cross BOOLEAN,

    trend_score INTEGER,
    trend VARCHAR(30),

    distance_from_52w_high NUMERIC,

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(stock_id, calculation_date)
);
```

---

# 13. Crossover History

The current value alone is not enough.

For example:

```text
3D MA > 7D MA
```

does not tell us when the crossover occurred.

Create a separate table:

```sql
CREATE TABLE stock_signals (
    id BIGSERIAL PRIMARY KEY,

    stock_id INTEGER NOT NULL REFERENCES stocks(id),

    signal_date DATE NOT NULL,

    signal_type VARCHAR(100) NOT NULL,

    direction VARCHAR(20),

    metadata JSONB,

    created_at TIMESTAMP DEFAULT NOW()
);
```

Example signals:

```text
BULLISH_3_7_CROSSOVER
BEARISH_3_7_CROSSOVER
GOLDEN_CROSS
DEATH_CROSS
ENTERED_STRONG_UPTREND
EXITED_STRONG_UPTREND
NEW_52_WEEK_HIGH
BREAKOUT_WATCHLIST
```

This enables historical analysis.

---

# 14. Google Sheets Registry

Do not hardcode spreadsheet IDs throughout the application.

Create a configuration table:

```sql
CREATE TABLE data_source_batches (
    id SERIAL PRIMARY KEY,

    batch_name VARCHAR(50) UNIQUE NOT NULL,

    spreadsheet_id VARCHAR(255) NOT NULL,

    sheet_name VARCHAR(100) DEFAULT 'STOCK_DATA',

    symbol_start VARCHAR(30),
    symbol_end VARCHAR(30),

    status VARCHAR(20) DEFAULT 'ACTIVE',

    last_successful_sync TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW()
);
```

Example:

| Batch | Spreadsheet | Sheet | Symbols | Status |
|---|---|---|---:|---|
| NSE_01 | Google Sheet ID | STOCK_DATA | 500 | ACTIVE |
| NSE_02 | Google Sheet ID | STOCK_DATA | 500 | ACTIVE |
| NSE_03 | Google Sheet ID | STOCK_DATA | 500 | ACTIVE |

---

# 15. ETL Pipeline

The ingestion process should read each spreadsheet in bulk.

Do not make one Google Sheets API request per row.

Recommended flow:

```text
Scheduler starts
      │
      ▼
Load active spreadsheet batches
      │
      ▼
For each spreadsheet:
      │
      ├── Read STOCK_DATA!A2:V
      │
      ├── Validate headers
      │
      ├── Validate symbols
      │
      ├── Convert numeric fields
      │
      ├── Handle blank / error values
      │
      └── Store valid rows
              │
              ▼
        Combine batches
              │
              ▼
       Upsert database data
              │
              ▼
       Update price history
              │
              ▼
       Calculate indicators
              │
              ▼
       Generate new signals
              │
              ▼
       Mark batch sync successful
```

---

# 16. Python Project Structure

```text
stock-platform/
│
├── config/
│   ├── settings.py
│   └── batches.yaml
│
├── data/
│   ├── nse_symbols.csv
│   └── batches/
│       ├── batch_01.csv
│       ├── batch_02.csv
│       └── ...
│
├── google_sheets/
│   ├── create_batches.py
│   ├── create_spreadsheet.py
│   ├── populate_symbols.py
│   ├── formulas.py
│   └── sheets_client.py
│
├── ingestion/
│   ├── read_batches.py
│   ├── validate.py
│   ├── normalize.py
│   └── ingest_stocks.py
│
├── indicators/
│   ├── moving_averages.py
│   ├── crossover.py
│   ├── trend_score.py
│   ├── breakout.py
│   └── signal_generator.py
│
├── database/
│   ├── models.py
│   ├── repository.py
│   └── migrations/
│
├── api/
│   ├── stocks.py
│   ├── screener.py
│   └── trends.py
│
├── scheduler/
│   ├── daily_update.py
│   └── retry_failed_batches.py
│
├── monitoring/
│   ├── healthcheck.py
│   └── alerts.py
│
└── tests/
    ├── test_indicators.py
    ├── test_ingestion.py
    └── test_trend_score.py
```

---

# 17. Google Sheets Batch Reader

Pseudo-code:

```python
def sync_all_batches():

    batches = get_active_batches()

    for batch in batches:

        try:
            rows = read_google_sheet(
                spreadsheet_id=batch.spreadsheet_id,
                range_name=f"{batch.sheet_name}!A2:V"
            )

            normalized_data = normalize_rows(rows)

            valid_data, invalid_data = validate_rows(normalized_data)

            bulk_upsert_snapshots(valid_data)

            mark_batch_success(batch.id)

        except Exception as error:

            mark_batch_failed(
                batch.id,
                str(error)
            )
```

The important point is:

```text
One batch = one bulk sheet read
```

not:

```text
One symbol = one API call
```

---

# 18. Data Validation Rules

Before inserting data into the database:

## Symbol

```text
- Must not be blank.
- Must exist in master symbol table.
- Must not be duplicated.
```

## LTP

```text
- Must be numeric.
- Must be greater than zero.
```

## Moving averages

```text
- Should be numeric if enough history exists.
- 200D MA can remain null for stocks with insufficient history.
```

## PE

PE should allow null or non-positive values where appropriate.

Do not convert invalid values into zero because:

```text
NULL != 0
```

Zero can incorrectly imply a valid financial metric.

---

# 19. Indicator Calculation in Python

Conceptual implementation:

```python
def calculate_indicators(closes):

    ma_3 = closes.tail(3).mean()
    ma_7 = closes.tail(7).mean()
    ma_21 = closes.tail(21).mean()
    ma_50 = closes.tail(50).mean()
    ma_200 = closes.tail(200).mean()

    latest_price = closes.iloc[-1]

    crossover_3_7 = ma_3 > ma_7
    above_ma_21 = latest_price > ma_21
    above_ma_200 = latest_price > ma_200
    golden_cross = ma_50 > ma_200

    score = (
        int(crossover_3_7)
        + int(above_ma_21)
        + int(ma_21 > ma_50)
        + int(above_ma_200)
        + int(golden_cross)
    )

    return {
        "ma_3": ma_3,
        "ma_7": ma_7,
        "ma_21": ma_21,
        "ma_50": ma_50,
        "ma_200": ma_200,
        "trend_score": score
    }
```

Production code should also handle:

- Missing dates.
- Insufficient price history.
- Delisted symbols.
- Corporate actions.
- Non-trading days.
- Null prices.

---

# 20. Detecting a New Crossover

A current signal:

```text
MA3 > MA7
```

is different from a fresh crossover.

Use both yesterday and today:

```python
bullish_crossover = (
    previous_ma_3 <= previous_ma_7
    and
    current_ma_3 > current_ma_7
)
```

Similarly:

```python
bearish_crossover = (
    previous_ma_3 >= previous_ma_7
    and
    current_ma_3 < current_ma_7
)
```

This distinction is important for the screener.

---

# 21. Daily Update Schedule

A recommended workflow is:

```text
After market close
        │
        ▼
Wait for source data availability
        │
        ▼
Refresh spreadsheet values
        │
        ▼
Run ETL ingestion
        │
        ▼
Validate all batches
        │
        ▼
Store daily snapshots
        │
        ▼
Update price history
        │
        ▼
Calculate indicators
        │
        ▼
Generate new signals
        │
        ▼
Refresh website cache/API
```

The exact execution time should be configurable because data availability can vary.

---

# 22. Retry and Failure Handling

Each batch should be independent.

Example:

```text
Batch 01 → Success
Batch 02 → Success
Batch 03 → Failed
Batch 04 → Success
Batch 05 → Success
```

The pipeline should not fail completely because one spreadsheet fails.

Store:

```text
Batch ID
Last attempted sync
Last successful sync
Status
Error message
Retry count
```

Then retry only failed batches.

---

# 23. Website/API Output

The API can expose endpoints such as:

```text
GET /stocks
GET /stocks/{symbol}
GET /screener
GET /screener?trend=strong-uptrend
GET /screener?min_score=4
GET /signals/today
GET /signals/fresh-crossover
GET /signals/golden-cross
GET /breakout-watchlist
```

Example API response:

```json
{
  "symbol": "APLAPOLLO",
  "ltp": 2270,
  "ma_3": 2266,
  "ma_7": 2179,
  "ma_21": 2111,
  "ma_50": 1966,
  "ma_200": 1959,
  "trend_score": 5,
  "trend": "Strong Uptrend",
  "distance_from_52w_high": -1.36
}
```

---

# 24. Recommended Dashboard Views

## Market Overview

Display:

```text
Total Active Stocks
Strong Uptrend
Uptrend
Neutral
Downtrend
Strong Downtrend
Fresh Bullish Crossovers Today
Fresh Bearish Crossovers Today
New 52 Week Highs
```

## Strong Momentum

Sort by:

```text
Trend Score DESC
Distance from 52W High DESC
```

## Fresh Signals

Display only stocks where a signal changed today.

Example:

```text
Symbol
Signal
Date
LTP
Trend Score
```

## Stock Detail Page

For each stock:

```text
Current Price
52W High / Low
Moving Averages
Trend Score
Current Trend
PE
EPS
Historical Trend
Signal History
```

---

# 25. Recommended Final Data Model

The system can eventually contain:

```text
stocks
│
├── stock_snapshots
├── stock_prices
├── stock_indicators
├── stock_signals
└── data_source_batches
```

Relationship:

```text
stocks
  │
  ├──── stock_snapshots
  │
  ├──── stock_prices
  │
  ├──── stock_indicators
  │
  └──── stock_signals
```

---

# 26. Implementation Phases

## Phase 1 - Spreadsheet Infrastructure

Deliverables:

- Master NSE symbol list.
- Automatic splitting into batches of approximately 500 symbols.
- Multiple Google Spreadsheets with identical structure.
- Symbol population.
- Formula population.
- Batch registry.

## Phase 2 - Database

Deliverables:

- PostgreSQL setup.
- `stocks` table.
- `stock_snapshots` table.
- `stock_prices` table.
- `stock_indicators` table.
- `stock_signals` table.
- Indexes and upsert logic.

## Phase 3 - ETL

Deliverables:

- Google Sheets authentication.
- Bulk batch reader.
- Data normalization.
- Validation.
- Bulk database insertion.
- Error handling.
- Retry mechanism.

## Phase 4 - Trend Engine

Deliverables:

- 3D MA.
- 7D MA.
- 21D MA.
- 50D MA.
- 200D MA.
- 3D/7D crossover detection.
- 50D/200D crossover detection.
- Trend score.
- Trend classification.
- Distance from 52-week high.

## Phase 5 - Website Screener

Deliverables:

- Strong Momentum screen.
- Fresh Uptrend screen.
- Long-Term Uptrend screen.
- Breakout Watchlist.
- Weak/Downtrend screen.
- Sorting and filtering.
- Stock detail pages.

---

# 27. Final Recommendation

The recommended architecture is:

```text
                NSE Symbol Master
                       │
                       ▼
          Split into 400-500 symbol batches
                       │
                       ▼
          Multiple Google Spreadsheets
                       │
                       ▼
          GOOGLEFINANCE data collection
                       │
                       ▼
               Python ETL Pipeline
                       │
                       ▼
                PostgreSQL Database
                       │
          ┌────────────┼─────────────┐
          ▼            ▼             ▼
      Price History  Indicators    Signals
          │            │             │
          └────────────┼─────────────┘
                       ▼
                Trend Engine
                       │
                       ▼
                 API / Backend
                       │
                       ▼
              Stock Screener Website
```

## Core design principles

1. Do not place the complete NSE universe into one calculation-heavy Google Spreadsheet.
2. Split symbols into batches of approximately 400-500.
3. Keep the spreadsheet structure identical across all batches.
4. Read every spreadsheet in bulk rather than row-by-row.
5. Use the database as the source of truth.
6. Store historical price and signal data.
7. Calculate moving averages centrally instead of repeatedly requesting the same historical data.
8. Track fresh crossovers, not just the current crossover state.
9. Use a multi-factor trend score instead of a simple Up/Down label.
10. Build the website around actionable screener categories and historical signals.

This architecture allows the system to start with Google Sheets and scale later without redesigning the complete application.
