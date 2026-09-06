# NiveshGuide API — Railway notes
#
# Preferred: deploy from monorepo root using ../railway.toml (Docker).
# If this directory is the Railway service root, use:
#   Start: uvicorn main:app --host 0.0.0.0 --port $PORT
#   Watch: main.py
#
# Required env (Railway → Variables):
#   DATABASE_URL=postgresql+psycopg2://...   # from Railway Postgres plugin
#   CORS_ORIGINS=https://niveshguide.com,https://www.niveshguide.com
#   TIMEZONE=Asia/Kolkata
#   SCHEDULER_ENABLED=true
# Optional: Google sheet secrets (token.json / credentials) for sheet sync;
# without them, disable sheet sync by keeping OAuth files unset — daily
# indices + calculate still run when SCHEDULER_ENABLED=true.
