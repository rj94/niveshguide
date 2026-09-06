# Cloud deploy notes (NiveshGuide)

This workspace has **no git remote** and no Railway/Vercel CLI installed, so
live project creation must be done in the dashboards (or after you `git init` +
push to GitHub and install CLIs).

## What is ready in-repo

| Artifact | Purpose |
|---|---|
| `railway.toml` + `backend/Dockerfile` | Railway Docker deploy on `$PORT` |
| `backend/RAILWAY.md` | API env vars |
| `web/vercel.json` + `web/VERCEL.md` | Vercel Root = `web` |
| `backend/scripts/bootstrap_prod.py` | Fill Railway Postgres |
| `docs/CLOUD_DEPLOY_CHECKLIST.md` | Step-by-step go-live |
| README **Production** section | DNS + smoke test |

## Your next clicks

1. `git init` (if needed), push to GitHub.
2. Railway: New Project → Postgres → Deploy from repo → set env → domain `api.niveshguide.com`.
3. Vercel: Import repo → Root `web` → `NEXT_PUBLIC_API_URL` → domains `niveshguide.com` / `www`.
4. DNS at registrar (see README).
5. Run `bootstrap_prod.py` against prod `DATABASE_URL`.

When Railway/Vercel URLs and DNS are live, re-open this chat to smoke-test
`https://niveshguide.com` and `https://api.niveshguide.com/health`.
