from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Ответ GET /api/health."""

    status: str = "ok"
