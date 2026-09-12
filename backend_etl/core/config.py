import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


class Settings:
    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "dev-only-secret-change-me-before-production-2026",
    )
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    SHOTGUN_TICKET_API_KEY = os.getenv("SHOTGUN_TICKET_API_KEY")
    SHOTGUN_TICKET_API_BASE_URL = os.getenv("SHOTGUN_TICKET_API_BASE_URL")
    # Flux Client Credentials : réservé aux données publiques (catalogue, pas de compte utilisateur)
    SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
    SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
    SPOTIFY_WEB_API_BASE_URL = os.getenv("SPOTIFY_WEB_API_BASE_URL", "https://api.spotify.com/v1")
    SRGSSR_MX3_CONSUMER_KEY = os.getenv("SRGSSR_MX3_CONSUMER_KEY")
    SRGSSR_MX3_CONSUMER_SECRET = os.getenv("SRGSSR_MX3_CONSUMER_SECRET")
    SRGSSR_MX3_API_BASE_URL = os.getenv("SRGSSR_MX3_API_BASE_URL", "https://api.srgssr.ch/mx3/v2")
    SRGSSR_OAUTH_TOKEN_URL = os.getenv(
        "SRGSSR_OAUTH_TOKEN_URL",
        "https://api.srgssr.ch/oauth/v1/accesstoken?grant_type=client_credentials",
    )
    METABASE_SITE_URL = os.getenv("METABASE_SITE_URL", "http://localhost:3000")
    METABASE_EMBEDDING_SECRET_KEY = os.getenv("METABASE_EMBEDDING_SECRET_KEY")
    METABASE_DASHBOARD_ID = os.getenv("METABASE_DASHBOARD_ID")
    ASSET_STORAGE_DIR = Path(os.getenv("ASSET_STORAGE_DIR", PROJECT_ROOT / "data" / "uploads")).resolve()
    ASSET_PUBLIC_BASE_URL = os.getenv("ASSET_PUBLIC_BASE_URL", "http://localhost:8000/uploads").rstrip("/")
    ASSET_MAX_BYTES = int(os.getenv("ASSET_MAX_BYTES", str(25 * 1024 * 1024)))

    @property
    def shotgun_ticket_is_configured(self) -> bool:
        return bool(self.SHOTGUN_TICKET_API_KEY and self.SHOTGUN_TICKET_API_BASE_URL)

    @property
    def spotify_is_configured(self) -> bool:
        return bool(self.SPOTIFY_CLIENT_ID and self.SPOTIFY_CLIENT_SECRET)

    @property
    def mx3_is_configured(self) -> bool:
        return bool(self.SRGSSR_MX3_CONSUMER_KEY and self.SRGSSR_MX3_CONSUMER_SECRET)

    @property
    def metabase_is_configured(self) -> bool:
        return bool(self.METABASE_EMBEDDING_SECRET_KEY and self.METABASE_DASHBOARD_ID)


settings = Settings()
