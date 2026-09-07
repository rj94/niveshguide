# NiveshGuide — cloud deploy checklist
#
# Run after code is pushed and you have Railway + Vercel + DNS access.
# Check each box in order.

## Pre-flight (repo)
- [ ] Branding shows NiveshGuide (sidebar, layout title, API / )
- [ ] backend/Dockerfile uses PORT
- [ ] railway.toml present at repo root
- [ ] web/vercel.json present; Root Directory will be `web`

## Railway
- [ ] Create project + Postgres plugin
- [ ] Deploy API from this repo (Docker via railway.toml)
- [ ] Env: DATABASE_URL, CORS_ORIGINS=https://niveshguide.com,https://www.niveshguide.com
- [ ] Env: TIMEZONE=Asia/Kolkata, SCHEDULER_ENABLED=true
- [ ] Env: SCHEDULER_SCREENER_ENABLED=false (until cloud scrape is configured)
- [ ] Health: GET /health returns ok
- [ ] Custom domain: api.niveshguide.com

## Vercel
- [ ] Import repo; Root Directory = web
- [ ] Env: NEXT_PUBLIC_API_URL=https://api.niveshguide.com/api/v1
- [ ] Domains: niveshguide.com + www
- [ ] Production deploy succeeds

## DNS (registrar)
- [ ] @ / www → Vercel records
- [ ] api CNAME → Railway hostname
- [ ] HTTPS certificates issued

## Data
- [ ] Prefer full copy from local SQLite (see below) OR bootstrap_prod.py
- [ ] Dashboard shows indices / stocks

### Migrate local SQLite → Railway Postgres

Uses public TCP proxy only (`*.proxy.rlwy.net`), never `postgres.railway.internal`.

```powershell
cd d:\Projects\Trade\backend
.\.venv\Scripts\Activate.ps1
# Public URL from Postgres → Variables → DATABASE_PUBLIC_URL (use postgresql+psycopg2://)
$env:DATABASE_URL = "postgresql+psycopg2://USER:PASS@HOST.proxy.rlwy.net:PORT/railway"
python scripts\migrate_sqlite_to_postgres.py --truncate
```

`--truncate` wipes existing Postgres tables first. Expect tens of minutes (~391 MB / millions of rows).

Resume after a failed run: `python scripts\migrate_sqlite_to_postgres.py --resume`

If you hit `DiskFull` / no space left: resize the Postgres volume to ≥5 GB (Railway Live Resize), or lean-migrate with `--skip-tables stock_financial_periods --price-since 2026-01-01` (~0.5M price rows). Do not paste DB passwords into chat; rotate if exposed.

## Smoke
- [ ] https://niveshguide.com loads
- [ ] Browser calls go to api.niveshguide.com/api/v1
- [ ] Momentum / Strategies / Volume / Stock pages work
