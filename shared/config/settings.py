from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Shared configuration settings for all services using Pydantic validation."""

    database_url: str = Field(
        default="postgresql://coverage:coverage@postgres:5432/coverage_db",
        env="DATABASE_URL"
    )
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    service_version: str = Field(default="1.0.0", env="SERVICE_VERSION")
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")

    # CORS: comma-separated list of allowed origins, or "*" for any origin.
    # Browser clients (the web plugin) need this; native clients ignore it.
    cors_allow_origins: str = Field(default="*", env="CORS_ALLOW_ORIGINS")

    # IP geolocation (data-service): MaxMind GeoLite2 City database.
    geoip_enabled: bool = Field(default=True, env="GEOIP_ENABLED")
    geoip_db_path: str = Field(
        default="/geoip/GeoLite2-City.mmdb", env="GEOIP_DB_PATH")
    # Accuracy stored for IP-derived locations when the database gives none.
    geoip_default_accuracy_m: float = Field(
        default=25000.0, env="GEOIP_DEFAULT_ACCURACY_M")

    # Download speed test (test-service): maximum payload size in bytes.
    max_download_bytes: int = Field(
        default=10_000_000, env="MAX_DOWNLOAD_BYTES")

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    @property
    def is_debug(self) -> bool:
        """Check if debug mode is enabled."""
        return self.debug

    @property
    def cors_allow_origins_list(self) -> List[str]:
        """CORS origins as a list, as expected by CORSMiddleware."""
        origins = [o.strip() for o in self.cors_allow_origins.split(",")]
        return [o for o in origins if o] or ["*"]

    class Config:
        env_file = ".env"
        case_sensitive = False
        # .env also holds variables for docker-compose (POSTGRES_*, GEOIPUPDATE_*...)
        extra = "ignore"


class ServiceSettings(Settings):
    """Service-specific settings that extend base settings."""

    service_name: str = Field(..., description="Name of the service")
    service_description: str = Field(
        default="", description="Service description")
    service_port: int = Field(default=8000, env="PORT")
    service_host: str = Field(default="0.0.0.0", env="HOST")


# Global settings instance
settings = Settings()
