from fastapi import APIRouter, BackgroundTasks

from app.api.schemas import SyncTriggerResponse
from app.worker import run_sync_job

router = APIRouter()


@router.post(
    "/sync/trigger",
    response_model=SyncTriggerResponse,
    summary="Запустить синхронизацию вручную",
)
async def trigger_sync(background_tasks: BackgroundTasks) -> SyncTriggerResponse:

    background_tasks.add_task(run_sync_job)
    return SyncTriggerResponse(status="scheduled")
