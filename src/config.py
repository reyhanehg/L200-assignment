"""Configuration module with Google Cloud Secret Manager integration for NutriConcierge."""

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

try:
    from pydantic_settings import BaseSettings
except ImportError:
    class BaseSettings(BaseModel):  # type: ignore
        pass


def load_secret_from_secret_manager(
    secret_id: str,
    project_id: Optional[str] = None,
    version_id: str = "latest",
) -> Optional[str]:
    """Retrieve a secret payload from Google Cloud Secret Manager with fallback to environment variables.

    Args:
        secret_id: Name of the secret in Secret Manager (e.g. 'gemini-api-key').
        project_id: GCP project ID. If omitted, uses GOOGLE_CLOUD_PROJECT env var.
        version_id: Secret version (defaults to 'latest').

    Returns:
        The secret payload string if available, else None.
    """
    proj = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
    if not proj:
        return os.getenv(secret_id.upper().replace("-", "_"))

    try:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{proj}/secrets/{secret_id}/versions/{version_id}"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8").strip()
    except Exception:
        # Graceful fallback to local environment variable
        return os.getenv(secret_id.upper().replace("-", "_"))


class Settings(BaseSettings):
    """Application settings and environment configurations with Secret Manager support."""

    # Project metadata
    app_name: str = "NutriConcierge AI"
    app_version: str = "0.1.0"
    debug: bool = False

    # Google Cloud & Vertex AI / Gemini
    google_cloud_project: str = Field(
        default_factory=lambda: os.getenv("GOOGLE_CLOUD_PROJECT", "mock-gcp-project")
    )
    google_cloud_location: str = Field(
        default_factory=lambda: os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    )
    gemini_model: str = Field(
        default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
    )
    gemini_flash_model: str = Field(
        default_factory=lambda: os.getenv("GEMINI_FLASH_MODEL", "gemini-1.5-flash")
    )

    # API Keys & Secrets injected via Secret Manager or environment
    gemini_api_key: Optional[str] = Field(
        default_factory=lambda: load_secret_from_secret_manager("gemini-api-key") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    )

    # Storage Paths
    base_dir: Path = Path(__file__).resolve().parent.parent
    data_dir: Path = Field(
        default_factory=lambda: Path(os.getenv("DATA_DIR", str(Path(__file__).resolve().parent.parent / "data")))
    )

    # Observability & Tracing
    enable_tracing: bool = Field(
        default_factory=lambda: os.getenv("ENABLE_TRACING", "true").lower() in ["true", "1", "yes"]
    )
    log_level: str = Field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO")
    )

    # Server settings
    api_host: str = Field(
        default_factory=lambda: os.getenv("API_HOST", "0.0.0.0")
    )
    api_port: int = Field(
        default_factory=lambda: int(os.getenv("API_PORT", "8000"))
    )

    def ensure_directories(self) -> None:
        """Ensure runtime storage directories exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
