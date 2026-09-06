from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


JSONType = JSON().with_variant(JSONB, "postgresql")
# SQLite only autoincrements INTEGER PKs. BigInteger is stored as INT
# but SQLAlchemy still omits the id unless we map it this way.
PK = BigInteger().with_variant(Integer, "sqlite")


class Stock(Base):
    __tablename__ = "stocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    company_name: Mapped[str | None] = mapped_column(String(255))
    isin: Mapped[str | None] = mapped_column(String(20))
    exchange: Mapped[str] = mapped_column(String(10), default="NSE")
    broad_sector: Mapped[str | None] = mapped_column(String(120))
    sector: Mapped[str | None] = mapped_column(String(120), index=True)
    broad_industry: Mapped[str | None] = mapped_column(String(120))
    industry: Mapped[str | None] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    snapshots: Mapped[list["StockSnapshot"]] = relationship(back_populates="stock")
    prices: Mapped[list["StockPrice"]] = relationship(back_populates="stock")
    indicators: Mapped[list["StockIndicator"]] = relationship(back_populates="stock")
    signals: Mapped[list["StockSignal"]] = relationship(back_populates="stock")
    fundamentals: Mapped[list["StockFundamental"]] = relationship(back_populates="stock")
    ownership_rows: Mapped[list["StockOwnership"]] = relationship(back_populates="stock")
    financial_periods: Mapped[list["StockFinancialPeriod"]] = relationship(back_populates="stock")
    index_memberships: Mapped[list["StockIndexMembership"]] = relationship(back_populates="stock")


class StockSnapshot(Base):
    __tablename__ = "stock_snapshots"
    __table_args__ = (UniqueConstraint("stock_id", "snapshot_date", name="uq_snapshot_stock_date"),)

    id: Mapped[int] = mapped_column(PK, primary_key=True, autoincrement=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), nullable=False, index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    market_cap: Mapped[float | None] = mapped_column(Numeric)
    ltp: Mapped[float | None] = mapped_column(Numeric)
    day_high: Mapped[float | None] = mapped_column(Numeric)
    prev_close: Mapped[float | None] = mapped_column(Numeric)
    high_52_week: Mapped[float | None] = mapped_column(Numeric)
    low_52_week: Mapped[float | None] = mapped_column(Numeric)
    pe: Mapped[float | None] = mapped_column(Numeric)
    eps: Mapped[float | None] = mapped_column(Numeric)
    volume: Mapped[int | None] = mapped_column(BigInteger)
    avg_volume_3m: Mapped[float | None] = mapped_column(Numeric)
    avg_volume_6m: Mapped[float | None] = mapped_column(Numeric)
    avg_volume_1y: Mapped[float | None] = mapped_column(Numeric)
    source: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    stock: Mapped[Stock] = relationship(back_populates="snapshots")


class StockPrice(Base):
    __tablename__ = "stock_prices"
    __table_args__ = (
        UniqueConstraint("stock_id", "price_date", name="uq_price_stock_date"),
        Index("idx_stock_prices_stock_date", "stock_id", "price_date"),
    )

    id: Mapped[int] = mapped_column(PK, primary_key=True, autoincrement=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), nullable=False)
    price_date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[float | None] = mapped_column(Numeric)
    high: Mapped[float | None] = mapped_column(Numeric)
    low: Mapped[float | None] = mapped_column(Numeric)
    close: Mapped[float | None] = mapped_column(Numeric)
    volume: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    stock: Mapped[Stock] = relationship(back_populates="prices")


class StockIndicator(Base):
    __tablename__ = "stock_indicators"
    __table_args__ = (UniqueConstraint("stock_id", "calculation_date", name="uq_indicator_stock_date"),)

    id: Mapped[int] = mapped_column(PK, primary_key=True, autoincrement=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), nullable=False, index=True)
    calculation_date: Mapped[date] = mapped_column(Date, nullable=False)

    ma_3: Mapped[float | None] = mapped_column(Numeric)
    ma_7: Mapped[float | None] = mapped_column(Numeric)
    ma_20: Mapped[float | None] = mapped_column(Numeric)
    ma_21: Mapped[float | None] = mapped_column(Numeric)
    ma_50: Mapped[float | None] = mapped_column(Numeric)
    ma_200: Mapped[float | None] = mapped_column(Numeric)

    crossover_3_7: Mapped[bool | None] = mapped_column(Boolean)
    above_ma_21: Mapped[bool | None] = mapped_column(Boolean)
    ma21_gt_ma50: Mapped[bool | None] = mapped_column(Boolean)
    above_ma_200: Mapped[bool | None] = mapped_column(Boolean)
    golden_cross: Mapped[bool | None] = mapped_column(Boolean)

    trend_score: Mapped[int | None] = mapped_column(Integer)
    trend: Mapped[str | None] = mapped_column(String(30))
    distance_from_52w_high: Mapped[float | None] = mapped_column(Numeric)
    return_1m: Mapped[float | None] = mapped_column(Numeric)
    return_3m: Mapped[float | None] = mapped_column(Numeric)
    return_6m: Mapped[float | None] = mapped_column(Numeric)
    return_12m: Mapped[float | None] = mapped_column(Numeric)

    distance_20_dma: Mapped[float | None] = mapped_column(Numeric)
    distance_50_dma: Mapped[float | None] = mapped_column(Numeric)
    distance_200_dma: Mapped[float | None] = mapped_column(Numeric)
    volume_avg_5: Mapped[float | None] = mapped_column(Numeric)
    volume_avg_20: Mapped[float | None] = mapped_column(Numeric)
    volume_ratio: Mapped[float | None] = mapped_column(Numeric)
    positive_volume_days_20: Mapped[float | None] = mapped_column(Numeric)

    revenue_growth_yoy: Mapped[float | None] = mapped_column(Numeric)
    pat_growth_yoy: Mapped[float | None] = mapped_column(Numeric)
    revenue_growth_qoq: Mapped[float | None] = mapped_column(Numeric)
    pat_growth_qoq: Mapped[float | None] = mapped_column(Numeric)
    margin_change: Mapped[float | None] = mapped_column(Numeric)
    earnings_acceleration: Mapped[float | None] = mapped_column(Numeric)

    return_score: Mapped[float | None] = mapped_column(Numeric)
    dma_score: Mapped[float | None] = mapped_column(Numeric)
    volume_score: Mapped[float | None] = mapped_column(Numeric)
    result_score: Mapped[float | None] = mapped_column(Numeric)
    momentum_score: Mapped[float | None] = mapped_column(Numeric)
    momentum_score_20d_ago: Mapped[float | None] = mapped_column(Numeric)
    momentum_acceleration: Mapped[float | None] = mapped_column(Numeric)
    momentum_category: Mapped[str | None] = mapped_column(String(40))

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    stock: Mapped[Stock] = relationship(back_populates="indicators")


class StockSignal(Base):
    __tablename__ = "stock_signals"

    id: Mapped[int] = mapped_column(PK, primary_key=True, autoincrement=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), nullable=False, index=True)
    signal_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    signal_type: Mapped[str] = mapped_column(String(100), nullable=False)
    direction: Mapped[str | None] = mapped_column(String(20))
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONType)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    stock: Mapped[Stock] = relationship(back_populates="signals")


class DataSourceBatch(Base):
    __tablename__ = "data_source_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    spreadsheet_id: Mapped[str] = mapped_column(String(255), nullable=False)
    gid: Mapped[int | None] = mapped_column(Integer)
    sheet_name: Mapped[str] = mapped_column(String(100), default="STOCK_DATA")
    symbol_start: Mapped[str | None] = mapped_column(String(30))
    symbol_end: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    last_attempted_sync: Mapped[datetime | None] = mapped_column(DateTime)
    last_successful_sync: Mapped[datetime | None] = mapped_column(DateTime)
    error_message: Mapped[str | None] = mapped_column(String(1000))
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class StockFundamental(Base):
    __tablename__ = "stock_fundamentals"
    __table_args__ = (UniqueConstraint("stock_id", "as_of_date", name="uq_fundamental_stock_date"),)

    id: Mapped[int] = mapped_column(PK, primary_key=True, autoincrement=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), nullable=False, index=True)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    market_cap: Mapped[float | None] = mapped_column(Numeric)
    pe: Mapped[float | None] = mapped_column(Numeric)
    book_value: Mapped[float | None] = mapped_column(Numeric)
    dividend_yield: Mapped[float | None] = mapped_column(Numeric)
    roe: Mapped[float | None] = mapped_column(Numeric)
    roce: Mapped[float | None] = mapped_column(Numeric)
    sales: Mapped[float | None] = mapped_column(Numeric)
    pat: Mapped[float | None] = mapped_column(Numeric)
    eps: Mapped[float | None] = mapped_column(Numeric)
    debt_equity: Mapped[float | None] = mapped_column(Numeric)
    source: Mapped[str | None] = mapped_column(String(50), default="screener.in")
    source_url: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    stock: Mapped[Stock] = relationship(back_populates="fundamentals")


class StockOwnership(Base):
    __tablename__ = "stock_ownership"
    __table_args__ = (UniqueConstraint("stock_id", "period_label", name="uq_ownership_stock_period"),)

    id: Mapped[int] = mapped_column(PK, primary_key=True, autoincrement=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), nullable=False, index=True)
    period_label: Mapped[str] = mapped_column(String(40), nullable=False)
    promoter_pct: Mapped[float | None] = mapped_column(Numeric)
    fii_pct: Mapped[float | None] = mapped_column(Numeric)
    dii_pct: Mapped[float | None] = mapped_column(Numeric)
    public_pct: Mapped[float | None] = mapped_column(Numeric)
    promoter_pledge_pct: Mapped[float | None] = mapped_column(Numeric)
    source: Mapped[str | None] = mapped_column(String(50), default="screener.in")
    scraped_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    stock: Mapped[Stock] = relationship(back_populates="ownership_rows")


class StockFinancialPeriod(Base):
    __tablename__ = "stock_financial_periods"
    __table_args__ = (
        UniqueConstraint(
            "stock_id",
            "section",
            "metric",
            "period_label",
            name="uq_fin_period_stock_metric",
        ),
        Index("idx_fin_period_stock_section", "stock_id", "section"),
    )

    id: Mapped[int] = mapped_column(PK, primary_key=True, autoincrement=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), nullable=False, index=True)
    section: Mapped[str] = mapped_column(String(40), nullable=False)
    metric: Mapped[str] = mapped_column(String(120), nullable=False)
    period_label: Mapped[str] = mapped_column(String(40), nullable=False)
    value_num: Mapped[float | None] = mapped_column(Numeric)
    value_raw: Mapped[str | None] = mapped_column(String(80))
    source: Mapped[str | None] = mapped_column(String(50), default="screener.in")
    scraped_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    stock: Mapped[Stock] = relationship(back_populates="financial_periods")


class MarketIndex(Base):
    __tablename__ = "market_indices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), default="index")  # broad | sectoral | other
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    snapshots: Mapped[list["MarketIndexSnapshot"]] = relationship(back_populates="index")
    prices: Mapped[list["MarketIndexPrice"]] = relationship(back_populates="index")


class MarketIndexSnapshot(Base):
    __tablename__ = "market_index_snapshots"
    __table_args__ = (UniqueConstraint("index_id", "as_of", name="uq_index_snap_date"),)

    id: Mapped[int] = mapped_column(PK, primary_key=True, autoincrement=True)
    index_id: Mapped[int] = mapped_column(ForeignKey("market_indices.id"), nullable=False, index=True)
    as_of: Mapped[date] = mapped_column(Date, nullable=False)
    last: Mapped[float | None] = mapped_column(Numeric)
    prev_close: Mapped[float | None] = mapped_column(Numeric)
    change: Mapped[float | None] = mapped_column(Numeric)
    change_pct: Mapped[float | None] = mapped_column(Numeric)
    open: Mapped[float | None] = mapped_column(Numeric)
    high: Mapped[float | None] = mapped_column(Numeric)
    low: Mapped[float | None] = mapped_column(Numeric)
    year_high: Mapped[float | None] = mapped_column(Numeric)
    year_low: Mapped[float | None] = mapped_column(Numeric)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    index: Mapped[MarketIndex] = relationship(back_populates="snapshots")


class MarketIndexPrice(Base):
    __tablename__ = "market_index_prices"
    __table_args__ = (
        UniqueConstraint("index_id", "price_date", name="uq_index_price_date"),
        Index("idx_market_index_prices_date", "index_id", "price_date"),
    )

    id: Mapped[int] = mapped_column(PK, primary_key=True, autoincrement=True)
    index_id: Mapped[int] = mapped_column(ForeignKey("market_indices.id"), nullable=False)
    price_date: Mapped[date] = mapped_column(Date, nullable=False)
    close: Mapped[float | None] = mapped_column(Numeric)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    index: Mapped[MarketIndex] = relationship(back_populates="prices")


class StockIndexMembership(Base):
    """NiftyIndices / NSE index constituent membership for a stock."""

    __tablename__ = "stock_index_membership"
    __table_args__ = (
        UniqueConstraint("stock_id", "index_key", name="uq_stock_index_membership"),
        Index("idx_stock_index_membership_key", "index_key"),
        Index("idx_stock_index_membership_category", "category"),
    )

    id: Mapped[int] = mapped_column(PK, primary_key=True, autoincrement=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), nullable=False, index=True)
    index_key: Mapped[str] = mapped_column(String(80), nullable=False)
    index_name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)  # broad | sectoral | thematic
    industry: Mapped[str | None] = mapped_column(String(120))
    weight: Mapped[float | None] = mapped_column(Numeric)
    as_of: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    stock: Mapped[Stock] = relationship(back_populates="index_memberships")
