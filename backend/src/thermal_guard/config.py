"""Runtime configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="PTG_",
        extra="ignore",
    )

    database_path: str = "data/thermal_guard.db"
    cors_origins: str = "http://localhost:3000,http://localhost:4173"
    mqtt_enabled: bool = False
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_username: str | None = None
    mqtt_password: str | None = None
    mqtt_topic: str = "thermal-guard/+/telemetry"
    absolute_warning_c: float = 70.0
    absolute_critical_c: float = 85.0
    anomaly_z_warning: float = 3.5
    baseline_alpha: float = 0.05

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
