from datetime import date

from database.models import Stock
from database.repository import upsert_snapshot, upsert_stock


def test_sqlite_snapshot_upsert_assigns_id(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    from config.settings import get_settings

    get_settings.cache_clear()
    # session.engine is already bound at import; use a fresh engine for this test
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from database.models import Base

    engine = create_engine(f"sqlite:///{db_path.as_posix()}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    stock = upsert_stock(session, "EPIGRAL", "EPIGRAL LIMITED")
    upsert_snapshot(
        session,
        stock.id,
        date(2026, 8, 31),
        {"ltp": 1235, "source": "test"},
    )
    session.commit()
    assert session.query(Stock).count() == 1
    session.close()
