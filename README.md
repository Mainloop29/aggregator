# Events Aggregator

Backend-сервис-агрегатор для работы с мероприятиями через Events Provider API.
Синхронизирует события в свою PostgreSQL, отдаёт быстрый REST API,
регистрирует и отменяет тикеты.

## Стек

- **Python 3.12**, **uv** — окружение и пакеты
- **FastAPI** — HTTP API
- **SQLAlchemy 2.0 (async)** + **asyncpg** — работа с БД
- **PostgreSQL 16** — хранение данных
- **httpx** — клиент к Events Provider API
- **APScheduler** — фоновая синхронизация раз в сутки
- **Ruff** — линтер и форматтер (PEP8)
- **pytest** + **pytest-asyncio** — тесты

## Архитектура

- `app/api/` — HTTP-слой (роутеры, схемы, DI)
- `app/usecases/` — бизнес-логика (не знает про БД и HTTP)
- `app/repositories/` — работа с PostgreSQL
- `app/providers/` — клиент Events Provider API + итератор пагинации
- `app/db/` — модели SQLAlchemy и движок
- `app/worker.py` — фоновый воркер синхронизации
- `tests/` — модульные тесты (pytest + unittest.mock)

## Эндпоинты

| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/health` | Healthcheck |
| POST | `/api/sync/trigger` | Ручной запуск синхронизации |
| GET | `/api/events` | Список событий (фильтр `date_from`, пагинация) |
| GET | `/api/events/{id}` | Детали события |
| GET | `/api/events/{id}/seats` | Свободные места (кэш 30 сек) |
| POST | `/api/tickets` | Регистрация на событие |
| DELETE | `/api/tickets/{id}` | Отмена регистрации |

Swagger: `http://localhost:8000/docs`

## Запуск локально

1. Скопируйте пример окружения:
   ```bash
   cp .env.example .env
   ```

2. Поднимите PostgreSQL:
   ```bash
   docker compose up -d db
   ```

3. Установите зависимости:
   ```bash
   uv sync --all-groups
   ```

4. Запустите сервер:
   ```bash
   uv run uvicorn app.main:app --reload
   ```

## Запуск в Docker

```bash
docker compose up --build
```

Приложение будет доступно на `http://localhost:8000`.

## Разработка

```bash
uv run ruff check .       # линтер
uv run ruff format .      # форматтер
uv run pytest -q          # тесты
```

## CI/CD

Workflow `.github/workflows/deploy.yml`:

1. **Lint** — Ruff (PEP8) + pytest. Без зелёного lint деплой не стартует.
2. **Build** — образ пушится в GHCR с тегом = SHA коммита.
3. **Deploy** — POST-запрос в LMS для обновления сервиса.