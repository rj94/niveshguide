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
- [ ] From laptop: DATABASE_URL=<prod> python scripts/bootstrap_prod.py
- [ ] Dashboard shows indices / stocks

## Smoke
- [ ] https://niveshguide.com loads
- [ ] Browser calls go to api.niveshguide.com/api/v1
- [ ] Momentum / Strategies / Volume / Stock pages work
