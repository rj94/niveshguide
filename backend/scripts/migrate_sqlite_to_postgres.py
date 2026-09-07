"""
Copy all Trade tables from local SQLite into Railway (or any) Postgres.

Usage (from backend/, public Railway URL only — never commit secrets):

  $env:DATABASE_URL = "postgresql+psycopg2://USER:PASS@HOST.proxy.rlwy.net:PORT/railway"
  .\\.venv\\Scripts\\python.exe scripts\\migrate_sqlite_to_postgres.py --truncate

Resume after a network drop (no truncate):

  .\\.venv\\Scripts\\python.exe scripts\\migrate_sqlite_to_postgres.py --resume

Do not use postgres.railway.internal from your laptop.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import MetaData, Table, create_engine, func, inspect, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

TABLE_ORDER: list[str] = [
    "stocks",
    "market_indices",
    "data_source_batches",
    "stock_snapshots",
    "stock_prices",
    "stock_indicators",
    "stock_signals",
    "stock_fundamentals",
    "stock_ownership",
    "stock_financial_periods",
    "market_index_snapshots",
    "market_index_prices",
    "stock_index_membership",
]

TRUNCATE_ORDER: list[str] = list(reversed(TABLE_ORDER))

DEFAULT_SOURCE = f"sqlite:///{(_BACKEND_ROOT / 'data' / 'screener.db').as_posix()}"
BATCH_SIZE = 1000
MAX_RETRIES = 5


def normalize_pg_url(url: str) -> str:
    url = url.strip()
    if url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[len("postgres://") :]
    return url


def redact_url(url: str) -> str:
    if "://" not in url or "@" not in url:
        return url
    scheme, rest = url.split("://", 1)
    if "@" not in rest:
        return url
    creds, host = rest.rsplit("@", 1)
    if ":" in creds:
        user = creds.split(":", 1)[0]
        return f"{scheme}://{user}:***@{host}"
    return f"{scheme}://***@{host}"


def row_to_dict(table: Table, row: Any) -> dict[str, Any]:
    mapping = row._mapping if hasattr(row, "_mapping") else dict(row)
    out: dict[str, Any] = {}
    for col in table.columns:
        val = mapping[col.name]
        out[col.name] = val
    return out


def target_max_id(target: Engine, table_name: str) -> int | None:
    insp = inspect(target)
    if table_name not in insp.get_table_names():
        return None
    pk = insp.get_pk_constraint(table_name).get("constrained_columns") or []
    if "id" not in pk:
        return None
    with target.connect() as conn:
        n = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar() or 0
        if n == 0:
            return 0
        return int(conn.execute(text(f"SELECT MAX(id) FROM {table_name}")).scalar() or 0)


def insert_batch_with_retry(
    target: Engine,
    table: Table,
    batch: list[dict[str, Any]],
) -> None:
    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with target.begin() as conn:
                conn.execute(table.insert(), batch)
            return
        except OperationalError as exc:
            last_exc = exc
            wait = min(2**attempt, 30)
            print(
                f"    retry {attempt}/{MAX_RETRIES} after DB error "
                f"(wait {wait}s): {exc.__class__.__name__}",
                flush=True,
            )
            time.sleep(wait)
            target.dispose()
    assert last_exc is not None
    raise last_exc


def copy_table(
    source: Engine,
    target: Engine,
    table_name: str,
    *,
    batch_size: int,
    resume: bool,
    price_since: str | None = None,
) -> int:
    src_meta = MetaData()
    tgt_meta = MetaData()
    src_table = Table(table_name, src_meta, autoload_with=source)
    tgt_table = Table(table_name, tgt_meta, autoload_with=target)

    after_id = 0
    if resume:
        mx = target_max_id(target, table_name)
        if mx is None:
            after_id = 0
        elif mx > 0:
            with source.connect() as sconn:
                src_max = sconn.execute(select(func.max(src_table.c.id))).scalar()
            if src_max is not None and mx >= int(src_max):
                # For filtered price copy, max-id completeness check is wrong; still ok if unfiltered
                if not (table_name == "stock_prices" and price_since):
                    print(f"  {table_name}: already complete ({mx:,} rows) — skip")
                    return 0
            after_id = mx
            print(f"  {table_name}: resuming after id={after_id:,}", flush=True)

    stmt = select(src_table)
    if after_id and "id" in src_table.c:
        stmt = stmt.where(src_table.c.id > after_id)
    if table_name == "stock_prices" and price_since and "price_date" in src_table.c:
        stmt = stmt.where(src_table.c.price_date >= price_since)
        print(f"  {table_name}: filter price_date >= {price_since}", flush=True)
    if "id" in src_table.c:
        stmt = stmt.order_by(src_table.c.id)

    count_stmt = select(func.count()).select_from(src_table)
    if after_id and "id" in src_table.c:
        count_stmt = count_stmt.where(src_table.c.id > after_id)
    if table_name == "stock_prices" and price_since and "price_date" in src_table.c:
        count_stmt = count_stmt.where(src_table.c.price_date >= price_since)

    with source.connect() as sconn:
        total = sconn.execute(count_stmt).scalar() or 0

    if total == 0:
        print(f"  {table_name}: 0 rows (skip)")
        return 0

    print(f"  {table_name}: copying {total:,} rows…", flush=True)
    copied = 0
    t0 = time.time()
    with source.connect() as sconn:
        result = sconn.execute(stmt)
        while True:
            rows = result.fetchmany(batch_size)
            if not rows:
                break
            batch = [row_to_dict(src_table, r) for r in rows]
            insert_batch_with_retry(target, tgt_table, batch)
            copied += len(batch)
            if copied % (batch_size * 10) == 0 or copied == total:
                elapsed = time.time() - t0
                rate = copied / elapsed if elapsed else 0
                print(
                    f"    … {copied:,}/{total:,} ({rate:,.0f} rows/s)",
                    flush=True,
                )
    return copied


def reset_sequences(target: Engine, table_names: list[str]) -> None:
    insp = inspect(target)
    with target.begin() as conn:
        for name in table_names:
            if name not in insp.get_table_names():
                continue
            pk_cols = insp.get_pk_constraint(name).get("constrained_columns") or []
            if pk_cols != ["id"]:
                continue
            conn.execute(
                text(
                    f"""
                    SELECT setval(
                      pg_get_serial_sequence('{name}', 'id'),
                      COALESCE((SELECT MAX(id) FROM {name}), 1),
                      true
                    )
                    """
                )
            )
    print("  Sequences reset for id columns.")


def truncate_tables(target: Engine, table_names: list[str]) -> None:
    insp = inspect(target)
    existing = [t for t in table_names if t in set(insp.get_table_names())]
    if not existing:
        return
    joined = ", ".join(existing)
    print(f"  Truncating: {joined}")
    with target.begin() as conn:
        conn.execute(text(f"TRUNCATE {joined} RESTART IDENTITY CASCADE"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate Trade SQLite to Postgres")
    parser.add_argument(
        "--source",
        default=os.environ.get("SOURCE_DATABASE_URL", DEFAULT_SOURCE),
        help="Source SQLite URL",
    )
    parser.add_argument(
        "--target",
        default=os.environ.get("DATABASE_URL"),
        help="Target Postgres URL (or set DATABASE_URL)",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="TRUNCATE all target tables before copy (destructive)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip rows already present (by max id) after a failed run",
    )
    parser.add_argument(
        "--tables",
        default="",
        help="Comma-separated subset of tables (default: all)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help=f"Insert batch size (default {BATCH_SIZE})",
    )
    parser.add_argument(
        "--price-since",
        default="",
        help="Only copy stock_prices on/after this date (YYYY-MM-DD). Saves disk.",
    )
    parser.add_argument(
        "--skip-tables",
        default="",
        help="Comma-separated tables to skip (e.g. stock_financial_periods)",
    )
    args = parser.parse_args()

    if not args.target:
        print("ERROR: pass --target or set DATABASE_URL", file=sys.stderr)
        return 1

    target_url = normalize_pg_url(args.target)
    if "railway.internal" in target_url:
        print(
            "ERROR: target uses railway.internal — use DATABASE_PUBLIC_URL "
            "(*.proxy.rlwy.net) from your laptop.",
            file=sys.stderr,
        )
        return 1
    if not (
        target_url.startswith("postgresql+psycopg2://")
        or target_url.startswith("postgresql+psycopg://")
    ):
        print(
            f"ERROR: target must be Postgres, got: {redact_url(target_url)}",
            file=sys.stderr,
        )
        return 1

    tables = TABLE_ORDER
    if args.tables.strip():
        wanted = {t.strip() for t in args.tables.split(",") if t.strip()}
        tables = [t for t in TABLE_ORDER if t in wanted]
        unknown = wanted - set(TABLE_ORDER)
        if unknown:
            print(f"ERROR: unknown tables: {sorted(unknown)}", file=sys.stderr)
            return 1
    if args.skip_tables.strip():
        skip = {t.strip() for t in args.skip_tables.split(",") if t.strip()}
        tables = [t for t in tables if t not in skip]

    price_since = args.price_since.strip() or None

    print(f"Source: {redact_url(args.source)}")
    print(f"Target: {redact_url(target_url)}")

    source = create_engine(args.source, future=True)
    target = create_engine(
        target_url,
        future=True,
        pool_pre_ping=True,
        connect_args={
            "connect_timeout": 30,
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
        },
    )

    from database.models import Base

    Base.metadata.create_all(bind=target)
    print("Target schema ready (create_all).")

    if args.truncate and args.resume:
        print("ERROR: use either --truncate or --resume, not both", file=sys.stderr)
        return 1

    if args.truncate:
        truncate_tables(target, TRUNCATE_ORDER)

    totals: dict[str, int] = {}
    t0 = time.time()
    for name in tables:
        try:
            totals[name] = copy_table(
                source,
                target,
                name,
                batch_size=max(100, args.batch_size),
                resume=args.resume,
                price_since=price_since,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR copying {name}: {exc}", file=sys.stderr)
            print("Re-run with --resume to continue from the last committed batch.", file=sys.stderr)
            return 1

    reset_sequences(target, tables)

    elapsed = time.time() - t0
    print("\nDone.")
    for name, n in totals.items():
        print(f"  {name}: {n:,}")
    print(f"Elapsed: {elapsed / 60:.1f} min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
