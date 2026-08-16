"""Configuration module for NutriConcierge."""

import os
from pathlib import Path
from pydantic import BaseModel, Field

try:
    from pydantic_settings import BaseSettings
except ImportError:
    # Fallback to standard BaseModel if pydantic_settings is not installed
    class BaseSettings(BaseModel):  # type: ignore
        pass


class Settings(BaseSettings):
    """Application settings and environment configurations."""

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
