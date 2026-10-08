import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@localhost:5432/test",
)
os.environ.setdefault(
    "EVENTS_PROVIDER_BASE_URL",
    "http://test.local",
)
os.environ.setdefault(
    "EVENTS_PROVIDER_API_KEY",
    "test-api-key",
)
