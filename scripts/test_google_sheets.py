"""Read the Drive-hosted workbook tab. No Google Cloud required.

Share the sheet as: Anyone with the link → Viewer.

    python scripts/test_google_sheets.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from config.settings import get_settings  # noqa: E402
from google_sheets.sheets_client import read_batch  # noqa: E402


def main() -> None:
    settings = get_settings()
    rows = read_batch(
        {
            "spreadsheet_id": settings.google_spreadsheet_id,
            "gid": settings.google_sheet_gid,
            "sheet_name": settings.google_sheet_name,
        },
        allow_local_csv=True,
    )
    print("Successfully connected.")
    print(f"Spreadsheet: {settings.google_spreadsheet_id}")
    print(f"gid:         {settings.google_sheet_gid}")
    print(f"Rows:        {len(rows)}")
    if not rows:
        print("The tab is empty.")
        return
    headers = rows[0]
    print("Headers:", headers)
    print("--- first 10 data rows ---")
    for row in rows[1:11]:
        record = {headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))}
        print(json.dumps(record, ensure_ascii=False))


if __name__ == "__main__":
    main()
