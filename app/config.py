from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки сервиса, читаются из переменных окружения и .env.

    Поддерживает два способа задать БД:
      1) DATABASE_URL — прямой URL (локальная разработка, .env).
      2) POSTGRES_* — переменные, которые выдаёт шаблон LMS.
         Приоритет: POSTGRES_CONNECTION_STRING, иначе сборка из частей.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---------- БД ----------
    database_url: str = ""

    # Формат LMS-шаблона (заполняется в проде автоматически)
    postgres_connection_string: str = ""
    postgres_host: str = ""
    postgres_port: int = 5432
    postgres_database_name: str = ""
    postgres_username: str = ""
    postgres_password: str = ""

    # ---------- Events Provider API ----------
    events_provider_base_url: str
    events_provider_api_key: str
    events_provider_timeout: float = 10.0

    # ---------- Фоновая синхронизация ----------
    sync_interval_hours: int = 24
    seats_cache_ttl: int = 30

    # ---------- Публичный адрес сервиса ----------
    hostname: str = "http://localhost:8000"

    @model_validator(mode="after")
    def _build_database_url(self) -> "Settings":
        """Собирает DATABASE_URL из POSTGRES_* переменных, если он не задан явно.

        Также приводит схему к asyncpg: postgres:// -> postgresql+asyncpg://.
        """
        if self.database_url:
            return self

        url = self.postgres_connection_string
        if not url:
            if not (
                self.postgres_host and self.postgres_database_name and self.postgres_username and self.postgres_password
            ):
                raise ValueError("Set DATABASE_URL or POSTGRES_* environment variables")
            url = (
                f"postgresql://{self.postgres_username}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_database_name}"
            )

        # asyncpg требует схему postgresql+asyncpg://
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

        self.database_url = url
        return self


settings = Settings()
