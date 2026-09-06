from __future__ import annotations

import logging
from datetime import datetime, time
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from config.settings import get_settings
from database.session import SessionLocal
from indicators.engine import calculate_all
from ingestion.read_batches import sync_all_batches

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None

_JOB_DEFAULTS = {
    "max_instances": 1,
    "coalesce": True,
    "misfire_grace_time": 300,
}


def sync_and_calculate(session: Session, allow_local_csv: bool = False) -> dict:
    """Pull sheet values, then recompute MAs / scores / signals.

    Yahoo backfill stays only as the momentum-empty fallback inside sync_all_batches.
    """
    sync_result = sync_all_batches(session, allow_local_csv=allow_local_csv)
    calculated = calculate_all(session)
    return {"sync": sync_result, "calculated": calculated}


def run_sheet_sync() -> dict:
    """Ingest Google Sheet snapshots into SQLite (no full indicator recalculation)."""
    settings = get_settings()
    now = datetime.now(ZoneInfo(settings.timezone))
    if now.weekday() >= 5:
        logger.info("sheet_sync skipped: weekend")
        return {"skipped": True, "reason": "weekend"}
    clock = now.time()
    if clock < time(9, 15) or clock > time(15, 30):
        logger.info("sheet_sync skipped: outside market hours (%s)", clock.isoformat(timespec="minutes"))
        return {"skipped": True, "reason": "outside_market_hours", "local_time": clock.isoformat(timespec="minutes")}

    session = SessionLocal()
    try:
        logger.info("sheet_sync starting")
        result = sync_all_batches(session)
        logger.info("sheet_sync finished: %s", result)
        return result
    except Exception:
        logger.exception("sheet_sync failed")
        raise
    finally:
        session.close()


def run_daily_update() -> dict:
    """End-of-day: optional NSE indices scrape, then sheet sync + calculate."""
    session = SessionLocal()
    try:
        logger.info("daily_update starting")
        payload: dict = {}
        try:
            from ingestion.nse_indices import scrape_and_store

            payload["indices"] = scrape_and_store(session)
        except Exception as exc:  # noqa: BLE001 — continue if NSE blocks
            logger.warning("daily_update indices scrape failed: %s", exc)
            payload["indices"] = {"ok": False, "error": str(exc)}

        payload.update(sync_and_calculate(session))
        logger.info("daily_update finished")
        return payload
    except Exception:
        logger.exception("daily_update failed")
        raise
    finally:
        session.close()


def retry_failed_batches() -> dict:
    return run_daily_update()


def run_screener_scrape() -> dict:
    """Nightly Screener.in scrape with resume + daily fetch cap (rolling weekly refresh)."""
    settings = get_settings()
    if not settings.scheduler_screener_enabled:
        logger.info("screener_scrape skipped: scheduler_screener_enabled=false")
        return {"skipped": True, "reason": "screener_disabled"}

    from ingestion.screener_in.run import scrape_screener

    try:
        logger.info(
            "screener_scrape starting (max_per_day=%s)",
            settings.scheduler_screener_max_per_day,
        )
        result = scrape_screener(
            resume=True,
            max_per_day=settings.scheduler_screener_max_per_day,
            cache_ttl_days=7,
        )
        logger.info(
            "screener_scrape finished: ok=%s failed=%s day_fetches=%s total=%s",
            result.get("ok"),
            result.get("failed"),
            result.get("day_fetches"),
            result.get("total"),
        )
        return result
    except Exception:
        logger.exception("screener_scrape failed")
        raise


def run_screener_import() -> dict:
    """Weekly import of Screener CSVs into SQLite (+ sector map when possible)."""
    settings = get_settings()
    if not settings.scheduler_screener_enabled:
        logger.info("screener_import skipped: scheduler_screener_enabled=false")
        return {"skipped": True, "reason": "screener_disabled"}

    from ingestion.screener_in.import_excel import import_screener_excel

    session = SessionLocal()
    try:
        logger.info("screener_import starting")
        payload: dict = {"import": import_screener_excel(session)}
        try:
            from ingestion.screener_in.map_sectors import map_screener_sectors

            payload["sectors"] = map_screener_sectors(session)
        except Exception as exc:  # noqa: BLE001 — import still useful without sectors
            logger.warning("screener_import sector map failed: %s", exc)
            payload["sectors"] = {"ok": False, "error": str(exc)}
        logger.info("screener_import finished: %s", payload.get("import"))
        return payload
    except Exception:
        logger.exception("screener_import failed")
        raise
    finally:
        session.close()


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler:
        return _scheduler

    settings = get_settings()
    tz = settings.timezone
    sync_minutes = max(1, int(settings.scheduler_sheet_sync_minutes))

    _scheduler = BackgroundScheduler(timezone=tz)
    _scheduler.add_job(
        run_sheet_sync,
        CronTrigger(
            minute=f"*/{sync_minutes}",
            hour="9-15",
            day_of_week="mon-fri",
            timezone=tz,
        ),
        id="sheet_sync_15m",
        replace_existing=True,
        **_JOB_DEFAULTS,
    )
    _scheduler.add_job(
        run_daily_update,
        CronTrigger(hour=16, minute=45, day_of_week="mon-fri", timezone=tz),
        id="daily_db_update",
        replace_existing=True,
        **_JOB_DEFAULTS,
    )
    if settings.scheduler_screener_enabled:
        _scheduler.add_job(
            run_screener_scrape,
            CronTrigger(hour=1, minute=0, timezone=tz),
            id="screener_scrape_nightly",
            replace_existing=True,
            **_JOB_DEFAULTS,
        )
        _scheduler.add_job(
            run_screener_import,
            CronTrigger(day_of_week="sun", hour=5, minute=0, timezone=tz),
            id="screener_import_weekly",
            replace_existing=True,
            **_JOB_DEFAULTS,
        )

    _scheduler.start()
    job_ids = [job.id for job in _scheduler.get_jobs()]
    logger.info("APScheduler started timezone=%s jobs=%s", tz, job_ids)
    return _scheduler
