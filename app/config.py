from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str
    database_url: str = "sqlite+aiosqlite:///fittrain.db"
    bot_timezone: str = "Europe/Moscow"
    admin_ids: str = ""
    cms_api_url: str = "http://localhost:8000/api"
    cms_frontend_url: str = "http://localhost:3000"
    evening_check_hour: int = 20
    followup_delay_minutes: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def admin_id_list(self) -> list[int]:
        if not self.admin_ids.strip():
            return [1021677544]
        return [int(x.strip()) for x in self.admin_ids.split(",") if x.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
