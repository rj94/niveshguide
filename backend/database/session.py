from collections.abc import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from config.settings import get_settings
from database.models import Base


def _make_engine():
    from sqlalchemy.pool import NullPool

    settings = get_settings()
    connect_args = {}
    engine_kwargs: dict = {"future": True, "connect_args": connect_args}
    if settings.database_url.startswith("sqlite"):
        # Avoid QueuePool exhaustion under concurrent FastAPI/UI requests.
        connect_args["check_same_thread"] = False
        engine_kwargs["poolclass"] = NullPool
    engine = create_engine(settings.database_url, **engine_kwargs)
    if settings.database_url.startswith("sqlite"):

        @event.listens_for(Engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_columns()


def _ensure_sqlite_columns() -> None:
    if not str(engine.url).startswith("sqlite"):
        return
    with engine.begin() as conn:
        indicators = {row[1] for row in conn.execute(text("PRAGMA table_info(stock_indicators)"))}
        indicator_columns = {
            "return_3m": "NUMERIC",
            "return_6m": "NUMERIC",
            "ma_20": "NUMERIC",
            "return_1m": "NUMERIC",
            "return_12m": "NUMERIC",
            "distance_20_dma": "NUMERIC",
            "distance_50_dma": "NUMERIC",
            "distance_200_dma": "NUMERIC",
            "volume_avg_5": "NUMERIC",
            "volume_avg_20": "NUMERIC",
            "volume_ratio": "NUMERIC",
            "positive_volume_days_20": "NUMERIC",
            "revenue_growth_yoy": "NUMERIC",
            "pat_growth_yoy": "NUMERIC",
            "revenue_growth_qoq": "NUMERIC",
            "pat_growth_qoq": "NUMERIC",
            "margin_change": "NUMERIC",
            "earnings_acceleration": "NUMERIC",
            "return_score": "NUMERIC",
            "dma_score": "NUMERIC",
            "volume_score": "NUMERIC",
            "result_score": "NUMERIC",
            "momentum_score": "NUMERIC",
            "momentum_score_20d_ago": "NUMERIC",
            "momentum_acceleration": "NUMERIC",
            "momentum_category": "VARCHAR(40)",
        }
        for column, ddl in indicator_columns.items():
            if column not in indicators:
                conn.execute(text(f"ALTER TABLE stock_indicators ADD COLUMN {column} {ddl}"))
        snapshots = {row[1] for row in conn.execute(text("PRAGMA table_info(stock_snapshots)"))}
        snapshot_columns = {
            "volume": "BIGINT",
            "avg_volume_3m": "NUMERIC",
            "avg_volume_6m": "NUMERIC",
            "avg_volume_1y": "NUMERIC",
        }
        for column, ddl in snapshot_columns.items():
            if column not in snapshots:
                conn.execute(text(f"ALTER TABLE stock_snapshots ADD COLUMN {column} {ddl}"))
        stocks = {row[1] for row in conn.execute(text("PRAGMA table_info(stocks)"))}
        stock_columns = {
            "broad_sector": "VARCHAR(120)",
            "sector": "VARCHAR(120)",
            "broad_industry": "VARCHAR(120)",
            "industry": "VARCHAR(120)",
        }
        for column, ddl in stock_columns.items():
            if column not in stocks:
                conn.execute(text(f"ALTER TABLE stocks ADD COLUMN {column} {ddl}"))
        try:
            memberships = {row[1] for row in conn.execute(text("PRAGMA table_info(stock_index_membership)"))}
        except Exception:  # noqa: BLE001 — table may not exist yet
            memberships = set()
        if memberships and "industry" not in memberships:
            conn.execute(text("ALTER TABLE stock_index_membership ADD COLUMN industry VARCHAR(120)"))


def get_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
