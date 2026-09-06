from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import DataSourceBatch
from database.repository import mark_batch_attempt, upsert_batch
from google_sheets.export_batch_workbooks import USER_WORKBOOKS
from google_sheets.sheets_client import SheetsReadError, load_batch_config, read_batch, read_named_tab
from ingestion.ingest_stocks import ingest_momentum_history, ingest_snapshots
from ingestion.normalize import normalize_rows
from ingestion.validate import validate_rows


def register_configured_batches(session: Session) -> list[DataSourceBatch]:
    registered = []
    configured_names: set[str] = set()
    for item in load_batch_config():
        payload = {
            "batch_name": item["batch_name"],
            "spreadsheet_id": item["spreadsheet_id"],
            "gid": item.get("gid"),
            "sheet_name": item.get("sheet_name") or "StockFilter",
            "status": item.get("status") or "ACTIVE",
        }
        configured_names.add(payload["batch_name"])
        registered.append(upsert_batch(session, payload))
    leftover = session.scalars(
        select(DataSourceBatch).where(DataSourceBatch.batch_name.notin_(configured_names))
    ).all()
    for batch in leftover:
        batch.status = "INACTIVE"
        batch.error_message = "Not in batches.yaml (reference-only or replaced)"
    session.commit()
    return registered


def _batch_config_by_name() -> dict[str, dict]:
    return {item["batch_name"]: item for item in load_batch_config()}


def _momentum_sheet_name(spreadsheet_id: str, batch_name: str | None = None, configured: str | None = None) -> str | None:
    if configured:
        return configured
    if batch_name:
        from_yaml = (_batch_config_by_name().get(batch_name) or {}).get("momentum_sheet")
        if from_yaml:
            return from_yaml
    for book in USER_WORKBOOKS:
        if book["spreadsheet_id"] == spreadsheet_id:
            return book.get("momentum_sheet")
    return None


def sync_all_batches(session: Session, snapshot_date: date | None = None, allow_local_csv: bool = False) -> dict:
    register_configured_batches(session)
    config_by_name = _batch_config_by_name()
    summary: dict = {
        "ok": [],
        "failed": [],
        "empty": [],
        "batches": [],
        "rows": 0,
        "prices": 0,
        "invalid": 0,
    }
    batches = session.scalars(
        select(DataSourceBatch).where(DataSourceBatch.status.in_(["ACTIVE", "FAILED"]))
    ).all()

    for batch in batches:
        batch_detail: dict = {
            "batch": batch.batch_name,
            "rows": 0,
            "invalid": 0,
            "prices": 0,
            "status": "ok",
        }
        try:
            raw = read_batch(
                {
                    "spreadsheet_id": batch.spreadsheet_id,
                    "gid": batch.gid,
                    "sheet_name": batch.sheet_name,
                },
                allow_local_csv=allow_local_csv,
            )
            if not raw:
                mark_batch_attempt(session, batch)
                session.commit()
                summary["ok"].append(batch.batch_name)
                summary["empty"].append({"batch": batch.batch_name, "reason": "no rows read"})
                batch_detail["status"] = "empty"
                batch_detail["reason"] = "no rows read"
                summary["batches"].append(batch_detail)
                continue
            normalized = normalize_rows(raw)
            valid, invalid = validate_rows(normalized)
            batch_detail["invalid"] = len(invalid)
            summary["invalid"] += len(invalid)
            if not valid:
                mark_batch_attempt(session, batch)
                session.commit()
                summary["ok"].append(batch.batch_name)
                reason = "all rows invalid (often missing LTP / blank GOOGLEFINANCE)"
                summary["empty"].append(
                    {
                        "batch": batch.batch_name,
                        "reason": reason,
                        "invalid": len(invalid),
                        "raw_rows": len(normalized),
                    }
                )
                batch_detail["status"] = "empty"
                batch_detail["reason"] = reason
                batch_detail["raw_rows"] = len(normalized)
                summary["batches"].append(batch_detail)
                continue
            count = ingest_snapshots(
                session,
                valid,
                source=f"sheets:{batch.batch_name}",
                snapshot_date=snapshot_date,
            )
            yaml_cfg = config_by_name.get(batch.batch_name) or {}
            momentum_name = _momentum_sheet_name(
                batch.spreadsheet_id,
                batch_name=batch.batch_name,
                configured=yaml_cfg.get("momentum_sheet"),
            )
            prices = 0
            if momentum_name:
                try:
                    momentum_rows = read_named_tab(
                        batch.spreadsheet_id, momentum_name, allow_local_csv=allow_local_csv
                    )
                    prices = ingest_momentum_history(session, momentum_rows)
                    if prices == 0:
                        from ingestion.ingest_stocks import backfill_prices
                        from ingestion.momentum_history import momentum_symbols

                        symbols = momentum_symbols(momentum_rows)
                        if symbols:
                            prices = backfill_prices(session, symbols, period="2y")
                except SheetsReadError:
                    prices = 0
            session.commit()
            mark_batch_attempt(session, batch)
            session.commit()
            summary["ok"].append(batch.batch_name)
            summary["rows"] += count
            summary["prices"] += prices
            batch_detail["rows"] = count
            batch_detail["prices"] = prices
            if invalid:
                batch_detail["status"] = "partial"
                batch_detail["reason"] = f"{len(invalid)} invalid rows skipped"
            summary["batches"].append(batch_detail)
        except SheetsReadError as exc:
            session.rollback()
            mark_batch_attempt(session, batch, str(exc))
            session.commit()
            summary["failed"].append({"batch": batch.batch_name, "error": str(exc)})
            batch_detail["status"] = "failed"
            batch_detail["reason"] = str(exc)
            summary["batches"].append(batch_detail)
        except Exception as exc:
            session.rollback()
            mark_batch_attempt(session, batch, str(exc))
            session.commit()
            summary["failed"].append({"batch": batch.batch_name, "error": str(exc)})
            batch_detail["status"] = "failed"
            batch_detail["reason"] = str(exc)
            summary["batches"].append(batch_detail)
    return summary
