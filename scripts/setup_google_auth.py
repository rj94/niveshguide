"""One-time browser login with the Gmail account that owns the Drive spreadsheet.

Place the Desktop OAuth client JSON at the project root as credentials.json, then:

    python scripts/setup_google_auth.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from google_auth_oauthlib.flow import InstalledAppFlow  # noqa: E402

from config.settings import get_settings  # noqa: E402
from google_sheets.sheets_client import SHEETS_SCOPES  # noqa: E402


def main() -> None:
    settings = get_settings()
    client_path = settings.oauth_client_path
    if client_path is None:
        raise SystemExit(
            "credentials.json not found.\n"
            "Download the Desktop OAuth client from Google Cloud Console and save it as:\n"
            f"  {PROJECT_ROOT / 'credentials.json'}"
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(client_path), SHEETS_SCOPES)
    credentials = flow.run_local_server(port=0, prompt="consent")
    token_path = settings.token_path
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(credentials.to_json(), encoding="utf-8")
    print("Google authentication successful.")
    print(f"Token saved to {token_path}")
    print("Next: python scripts/test_google_sheets.py")


if __name__ == "__main__":
    main()
