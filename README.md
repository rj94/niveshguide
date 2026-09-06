# NiveshGuide

Trend discovery for NSE stocks: Google Sheets collection → PostgreSQL/SQLite → moving averages and signals → [niveshguide.com](https://niveshguide.com).

Live collection is **six Drive workbooks**. They use the StockFilter column layout (one symbol per row) but **StockFilter itself is not the app source** — that tab has 78 duplicate symbols and dead tickers.

Fill them with:

```powershell
cd d:\Projects\Trade\backend
python -m cli fill-batch-sheets
```

That command writes via Google API if you have signed in, otherwise it generates `backend/data/spreadsheets/FillExistingNseSpreadsheets.gs` for Apps Script.

1. [NSE 0–500](https://docs.google.com/spreadsheets/d/1xzT_B1vlCr_MlYN6a-CVfxDUbB8BhZiqfQUJkPGPBBk/edit?gid=0#gid=0)
2. [NSE 500–1000](https://docs.google.com/spreadsheets/d/1hc33TZaVWf9qRbsSH__07sn_XDkiBDliJF3zf2MAa-4/edit?gid=0#gid=0)
3. [NSE 1000–1500](https://docs.google.com/spreadsheets/d/1obC866jNti_X7yvtugWdh_zhJe5gHPQQRKzRPi1JqyU/edit?gid=0#gid=0)
4. [NSE 1500–2000](https://docs.google.com/spreadsheets/d/1Iv13XpfD1NMWLZYo1NXElJbZnVcqpNyyiNdFYZVN34s/edit?gid=0#gid=0)
5. [NSE 2000–2500](https://docs.google.com/spreadsheets/d/17I3gCKHas-2nf-crUw9br3rKAeNYCXdpSqVXVZsGQxw/edit?gid=0#gid=0)
6. [NSE 2500–3000](https://docs.google.com/spreadsheets/d/1UBLESBcoLqa65uUdlbk72YSlR9HhytoVbl18fKH_GKg/edit?gid=0#gid=0) (unused leftover)

Layout reference only: [StockFilter](https://docs.google.com/spreadsheets/d/1RAX7B2YJfdHrhDbuS4ohUBUwwU7ROsozP8j-zkjUoAM/edit?gid=1375108259#gid=1375108259)

The original wide StockTrade sheet is reference-only. Do not put the full NSE universe in one tab.

## What it does

1. Keeps an NSE symbol master (~2,389 names).
2. Reads market snapshots in **one bulk request per spreadsheet batch** (never per symbol).
3. Stores daily snapshots, price history, indicators, and signal events.
4. Calculates 3/7/21/50/200-day MAs and a 0–5 trend score in Python.
5. Screens for strong momentum, fresh 3/7 crossovers, long-term uptrends, breakout names, and weak/avoid names.

## Quick start (local)

```powershell
cd d:\Projects\Trade
copy .env.example .env

cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m cli bootstrap --demo
python -m cli serve --reload
```

In another terminal:

```powershell
cd d:\Projects\Trade\web
copy .env.example .env.local
npm install
npm run dev
```

Open http://localhost:3000 (API default in `.env.local`: `http://localhost:8011/api/v1`).

`bootstrap --demo` loads the NSE master. Live market data comes from your Google Drive spreadsheet via `GOOGLEFINANCE`.

## Google Drive spreadsheet + GOOGLEFINANCE

The database does **not** call Google Finance itself. Every collection tab follows **StockFilter** (gid `1375108259`): one symbol per row, these 19 columns:

`Symbol | marketcap | LTP | High | Prev Close | 52 week high | 52 week low | 3Days MA | 7Days MA | 21Days MA | 50Days MA | 200Days MA | Crossover(3D>7D) | LTP > 21 D | LTP > 200 D | Crossover(50D>200D) | Trend | PE | EPS`

Quotes and MAs come from `GOOGLEFINANCE`. Trend is `Up` only when LTP > 21D, LTP > 200D, and 50D > 200D (columns N, O, P). This app downloads each tab as CSV. **Google Cloud is not required.**

Each workbook has two tabs, named like the original StockTrade file:

- **Momentum NSE 500** (or **Momentum NSE 500-1000**, …) — one symbol per column, **2 years** of daily closes, 3-month / 6-month returns from that series, dates as `yyyy-mm-dd`. `python -m cli sync` loads those closes into `stock_prices`.
- **StockFilter** — one symbol per row, live quotes and trend flags.

The Drive file titles become `NSE 0-500 Stocks`, `NSE 500-1000 Stocks`, and so on.

### Fill the six empty sheets (once)

Each blank workbook is filled as a copy of StockFilter (~500 NSE symbols, same headers and formulas), then a Momentum tab is added.

1. Open any of the six sheets.
2. **Extensions → Apps Script**.
3. Delete the default code. Paste `backend/data/spreadsheets/FillExistingNseSpreadsheets.gs` (generate it with `python -m cli export-sheet-batches` if the file is missing).
4. Save. If **StockFilter already has rows**, select **addMomentumAndFixTrendNse0_500** and **Run** (does not wipe quotes). If a workbook is still blank, run `fillNse0_500` / `fillNse500_1000` / …
5. If Apps Script times out, run one fill function at a time.
6. Leave each spreadsheet open so `GOOGLEFINANCE` can calculate.

Alternatively, **File → Import** `NSE_STOCK_BATCH_01.csv` … `_05.csv` into the matching workbook (0–500 through 2000–2500).

### Share each sheet (no Cloud)

1. Open the spreadsheet.
2. Click **Share**.
3. **General access** → **Anyone with the link** → **Viewer**.
4. Keep the sheet open in the browser so `GOOGLEFINANCE` can calculate.

Then:

```powershell
cd d:\Projects\Trade
.\backend\.venv\Scripts\Activate.ps1
python scripts\test_google_sheets.py
cd backend
python -m cli load-symbols
python -m cli sync
python -m cli calculate
```

### If you do not want to share the link

In Google Sheets: **File → Download → Comma Separated Values (.csv)**. Save it as:

```text
d:\Projects\Trade\backend\data\sheet_export.csv
```

Then run `python -m cli sync --local-csv`.

Put `GOOGLEFINANCE` formulas in the sheet yourself. Example for LTP in column C, symbol in A2:

```excel
=IFERROR(GOOGLEFINANCE("NSE:"&A2,"price"),)
```

## CLI

| Command | Purpose |
|---|---|
| `python scripts/test_google_sheets.py` | Check the shared sheet is readable |
| `python -m cli load-symbols` | Load NSE master into `stocks` |
| `python -m cli sync` | Pull computed sheet values into the database |
| `python -m cli calculate` | MAs, scores, crossovers, signals |
| `python -m cli export-sheet-batches` | Write CSVs + `FillExistingNseSpreadsheets.gs` |

## Automatic scheduler

With the API process running and `SCHEDULER_ENABLED=true` in `.env`, APScheduler runs unattended jobs (Asia/Kolkata):

| Job | When | Action |
|---|---|---|
| Sheet sync | Mon–Fri every 15 min, 09:15–15:30 | Pull Google Sheets → DB (`sync_all_batches`) |
| Daily DB update | Mon–Fri 16:45 | NSE indices (best-effort) + sync + `calculate_all` |
| Screener scrape | Daily 01:00 | `scrape-screener` with resume, `--max-per-day` 400 (rolling weekly refresh) |
| Screener import | Sunday 05:00 | Import Screener CSVs into SQLite (+ sector map) |

Enable:

```powershell
# In project .env
SCHEDULER_ENABLED=true
SCHEDULER_SHEET_SYNC_MINUTES=15
SCHEDULER_SCREENER_ENABLED=true
SCHEDULER_SCREENER_MAX_PER_DAY=400

cd d:\Projects\Trade\backend
.\.venv\Scripts\Activate.ps1
# One-time (or when token expires) for sheet sync:
python -m cli google-login
python -m cli serve
```

The API must stay up for jobs to fire. Sheet sync needs a valid `token.json` from `google-login`. Screener jobs can be disabled with `SCHEDULER_SCREENER_ENABLED=false`.

## Ads monetization (no signup)

There is **no user signup or login**. Revenue is via Google ads.

### Website (AdSense)

1. Create a [Google AdSense](https://www.google.com/adsense/) account and add your site.
2. After approval, create display ad units for Dashboard, Momentum, and Stock.
3. Copy values into `web/.env.local` (see `web/.env.example`):

```text
NEXT_PUBLIC_ADSENSE_CLIENT=ca-pub-xxxxxxxxxxxxxxxx
NEXT_PUBLIC_ADSENSE_SLOT_DASHBOARD=##########
NEXT_PUBLIC_ADSENSE_SLOT_MOMENTUM=##########
NEXT_PUBLIC_ADSENSE_SLOT_STOCK=##########
```

4. Restart `npm run dev` / rebuild. Without these vars, ad slots stay hidden.

Slots appear on Dashboard (below indices), Momentum (below filters), and Stock detail (below the quote).

### Android app (AdMob)

See [`mobile/README.md`](mobile/README.md) for Expo Go, Android `minSdk 24`, multi-phone preview matrix, and AdMob notes. Market **scraping stays on the backend**; the app only calls the API after DB updates.

```powershell
cd d:\Projects\Trade\mobile
npm start
```

## API

- `GET /health`
- `GET /dashboard`
- `GET /stocks`
- `GET /stocks/{symbol}`
- `GET /screener?trend=strong-momentum`
- `GET /screener?trend=fresh-uptrend`
- `GET /screener?min_score=4`
- `GET /signals/today`
- `GET /signals/fresh-crossover`
- `GET /signals/golden-cross`
- `GET /breakout-watchlist`

## Trend score

| Condition | Points |
|---|---:|
| 3D MA > 7D MA | +1 |
| LTP > 21D MA | +1 |
| 21D MA > 50D MA | +1 |
| LTP > 200D MA | +1 |
| 50D MA > 200D MA | +1 |

5 = Strong Uptrend … 0 = Strong Downtrend.

Moving averages are calculated from stored price history, not from repeated `GOOGLEFINANCE` historical calls.

## Docker

```powershell
docker compose up --build
```

API: http://localhost:8000 · UI: http://localhost:8080

Optional Postgres URL:

```
DATABASE_URL=postgresql+psycopg2://screener:screener@localhost:5432/screener
```

SQLite (`backend/data/screener.db`) is the default for local use.

## Production (niveshguide.com)

Live stack:

| Piece | Host | URL |
|---|---|---|
| Web (Next.js in `web/`) | Vercel | https://niveshguide.com |
| API (FastAPI in `backend/`) | Railway | https://api.niveshguide.com |
| Database | Railway Postgres | `DATABASE_URL` on the API service |

Do **not** deploy the legacy Vite app in `frontend/`.

### 1. Railway (API + Postgres)

1. Create a Railway project; add a **PostgreSQL** plugin.
2. Add a service from this GitHub repo (root). Railway uses [`railway.toml`](railway.toml) → `backend/Dockerfile` (listens on `$PORT`).
3. Set variables on the API service:

```text
DATABASE_URL=<Railway Postgres URL — use postgresql+psycopg2:// …>
CORS_ORIGINS=https://niveshguide.com,https://www.niveshguide.com
TIMEZONE=Asia/Kolkata
SCHEDULER_ENABLED=true
SCHEDULER_SCREENER_ENABLED=false
```

Leave screener scrape off in cloud until you mount volume/credentials; daily indices + calculate still run when the scheduler is enabled. Sheet sync needs Google OAuth files as Railway secrets — skip until configured (see [`backend/RAILWAY.md`](backend/RAILWAY.md)).

4. Deploy, then open `https://<railway-default-host>/health` and `/docs`.
5. Attach custom domain **api.niveshguide.com** (Railway → Settings → Domains).

### 2. Vercel (web)

1. Import the same repo; set **Root Directory** to `web`.
2. Environment variable (Production):

```text
NEXT_PUBLIC_API_URL=https://api.niveshguide.com/api/v1
```

3. Deploy. Attach **niveshguide.com** and **www.niveshguide.com**.
4. Details: [`web/VERCEL.md`](web/VERCEL.md).

### 3. DNS

At your registrar for **niveshguide.com**:

| Host | Type | Value |
|---|---|---|
| `@` / `www` | A / CNAME | As shown in the Vercel domain UI |
| `api` | CNAME | Railway service hostname |

Wait for HTTPS certificates (usually a few minutes).

### 4. Bootstrap market data

Postgres starts empty. From a machine with Google/NSE access:

```powershell
cd d:\Projects\Trade\backend
.\.venv\Scripts\Activate.ps1
$env:DATABASE_URL = "postgresql+psycopg2://USER:PASS@HOST:5432/railway"
python scripts\bootstrap_prod.py
```

Use `--skip-sync` if Google OAuth is not available yet (indices + calculate only). Re-run after sheet credentials work.

### 5. Smoke test

- https://niveshguide.com — Dashboard loads indices / ETFs / movers
- https://api.niveshguide.com/health — `ok`
- Strategies, Momentum, Volume, Stock detail pages hit the live API (browser Network tab → `api.niveshguide.com`)

Full checkbox list: [`docs/CLOUD_DEPLOY_CHECKLIST.md`](docs/CLOUD_DEPLOY_CHECKLIST.md).

If this folder is not on GitHub yet: `git init -b main`, commit, push, then connect Railway/Vercel to that repo. See [`docs/CLOUD_DEPLOY_STATUS.md`](docs/CLOUD_DEPLOY_STATUS.md).

### 6. Mobile (optional)

Point EAS/production builds at:

```text
EXPO_PUBLIC_API_URL=https://api.niveshguide.com/api/v1
```
