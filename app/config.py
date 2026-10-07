from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # База данных
    database_url: str

    # Events Provider API
    events_provider_base_url: str
    events_provider_api_key: str
    events_provider_timeout: float = 10.0

    # Фоновая синхронизация
    sync_interval_hours: int = 24

    # Кэш мест
    seats_cache_ttl: int = 30

    # Публичный адрес нашего сервиса
    hostname: str = "http://localhost:8000"


settings = Settings()
