from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "ok"


class SyncTriggerResponse(BaseModel):
    status: str
