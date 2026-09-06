from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = f"sqlite:///{(BACKEND_ROOT / 'data' / 'screener.db').as_posix()}"
    google_spreadsheet_id: str = "1xzT_B1vlCr_MlYN6a-CVfxDUbB8BhZiqfQUJkPGPBBk"
    google_sheet_gid: int = 0
    google_sheet_name: str = "StockFilter"
    google_service_account_file: str | None = None
    google_oauth_client_file: str | None = None
    google_token_file: str | None = None
    google_sheets_csv_url: str | None = None
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"
    batch_size: int = 500
    scheduler_enabled: bool = False
    scheduler_sheet_sync_minutes: int = 15
    scheduler_screener_max_per_day: int = 400
    scheduler_screener_enabled: bool = True
    timezone: str = "Asia/Kolkata"
    yfinance_suffix: str = ".NS"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    def _resolve(self, value: str | None, *defaults: Path) -> Path | None:
        candidates: list[Path] = []
        if value:
            path = Path(value)
            candidates.append(path if path.is_absolute() else PROJECT_ROOT / path)
            if not path.is_absolute():
                candidates.append(BACKEND_ROOT / path)
        candidates.extend(defaults)
        for path in candidates:
            if path.exists():
                return path
        return None

    @property
    def service_account_path(self) -> Path | None:
        return self._resolve(
            self.google_service_account_file,
            PROJECT_ROOT / "google-credentials.json",
            PROJECT_ROOT / "service-account.json",
            BACKEND_ROOT / "credentials" / "service-account.json",
        )

    @property
    def oauth_client_path(self) -> Path | None:
        return self._resolve(
            self.google_oauth_client_file,
            PROJECT_ROOT / "credentials.json",
            BACKEND_ROOT / "credentials" / "credentials.json",
            BACKEND_ROOT / "credentials" / "client_secret.json",
        )

    @property
    def token_path(self) -> Path:
        if self.google_token_file:
            path = Path(self.google_token_file)
            return path if path.is_absolute() else PROJECT_ROOT / path
        return PROJECT_ROOT / "token.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
