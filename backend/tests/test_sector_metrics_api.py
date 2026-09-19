"""Seeded sector metrics persist + API payload shape."""

from datetime import date, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from database.models import Base, MarketIndex, MarketIndexPrice, Stock, StockIndicator, StockPrice
from market_platform.services.sector_metrics import persist_daily_metrics
from market_platform.services.sectors import get_sector, list_sector_industries, list_sectors


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _add_series(
    session: Session,
    *,
    symbol: str,
    sector: str,
    industry: str,
    start: float,
    daily_return: float,
    volume: int,
    as_of: date,
    days: int = 80,
) -> Stock:
    stock = Stock(
        symbol=symbol,
        company_name=symbol,
        exchange="NSE",
        sector=sector,
        industry=industry,
        is_active=True,
    )
    session.add(stock)
    session.flush()
    price = start
    start_date = as_of - timedelta(days=days - 1)
    for i in range(days):
        price *= 1.0 + daily_return
        session.add(
            StockPrice(
                stock_id=stock.id,
                price_date=start_date + timedelta(days=i),
                close=round(price, 4),
                high=round(price * 1.01, 4),
                volume=volume,
            )
        )
    bull = daily_return > 0
    session.add(
        StockIndicator(
            stock_id=stock.id,
            calculation_date=as_of,
            ma_21=price * (0.96 if bull else 1.06),
            ma_50=price * (0.93 if bull else 1.10),
            ma_200=price * (0.88 if bull else 1.16),
            above_ma_21=bull,
            above_ma_200=bull,
            ma21_gt_ma50=bull,
            golden_cross=bull,
            distance_50_dma=0.04 if bull else -0.08,
            distance_from_52w_high=-0.02 if bull else -0.28,
            volume_ratio=1.8 if bull else 0.7,
            return_1m=daily_return * 21,
            return_3m=daily_return * 63,
            return_6m=daily_return * 126,
            momentum_score=80 if bull else 25,
        )
    )
    return stock


def _seed_two_sectors(session: Session, as_of: date) -> None:
    for i in range(3):
        _add_series(
            session,
            symbol=f"BANK{i}",
            sector="Banks",
            industry="Private Banks",
            start=100 + i,
            daily_return=0.004,
            volume=200_000,
            as_of=as_of,
        )
        _add_series(
            session,
            symbol=f"REAL{i}",
            sector="Realty",
            industry="Residential Realty",
            start=80 + i,
            daily_return=-0.002,
            volume=40_000,
            as_of=as_of,
        )
    nifty = MarketIndex(key="NIFTY 500", name="Nifty 500", kind="broad", is_active=True)
    session.add(nifty)
    session.flush()
    start_date = as_of - timedelta(days=79)
    close = 20_000.0
    for i in range(80):
        close *= 1.001
        session.add(
            MarketIndexPrice(
                index_id=nifty.id,
                price_date=start_date + timedelta(days=i),
                close=close,
            )
        )
    session.commit()


def test_seeded_sectors_rank_and_classify():
    session = _session()
    as_of = date(2026, 9, 10)
    _seed_two_sectors(session, as_of)
    persist_daily_metrics(session, as_of, min_constituents=2)

    payload = list_sectors(session, limit=20, min_constituents=2)
    names = [row.name for row in payload.items]
    assert names[0] == "Banks"
    assert "Realty" in names
    banks = next(row for row in payload.items if row.name == "Banks")
    realty = next(row for row in payload.items if row.name == "Realty")
    assert banks.strength_score is not None
    assert realty.strength_score is not None
    assert float(banks.strength_score) > float(realty.strength_score)
    assert banks.rotation_state in {"Leading", "Improving"}
    assert realty.rotation_state in {"Lagging", "Weakening"}
    assert banks.volume_score is not None
    assert banks.breakout_score is not None
    assert banks.trend_score is not None
    assert banks.relative_strength_score is not None
    session.close()


def test_list_and_detail_api_shape():
    session = _session()
    as_of = date(2026, 9, 10)
    _seed_two_sectors(session, as_of)
    persist_daily_metrics(session, as_of, min_constituents=2)

    payload = list_sectors(session, limit=20, min_constituents=2)
    assert payload.items
    row = payload.items[0]
    dumped = row.model_dump()
    for key in (
        "volume_score",
        "breakout_score",
        "trend_score",
        "emerging_score",
        "score_change_5d",
        "score_change_21d",
        "relative_strength_score",
        "momentum_score",
        "breadth_score",
    ):
        assert key in dumped

    detail = get_sector(session, "Banks")
    assert detail.name == "Banks"
    assert detail.industries
    assert any(ind.name == "Private Banks" for ind in detail.industries)
    nested = list_sector_industries(session, "Banks")
    assert nested
    assert nested[0].parent_sector == "Banks"
    session.close()
