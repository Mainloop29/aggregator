FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_NO_SYNC=1

RUN pip install --no-cache-dir uv==0.5.11

RUN groupadd --system --gid 1000 appuser && \
    useradd --system --uid 1000 --gid appuser --create-home appuser

WORKDIR /app
RUN chown appuser:appuser /app

COPY --chown=appuser:appuser pyproject.toml uv.lock ./

USER appuser

RUN uv sync --frozen --no-install-project --no-group dev

COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser run.sh ./run.sh
RUN chmod +x ./run.sh

EXPOSE 8000

CMD ["bash", "./run.sh"]