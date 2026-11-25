from fastapi import APIRouter, status

from app.core.dependencies import RepositoryDependency
from app.schemas.telemetry import TelemetryEventCreate, TelemetryEventResponse

router = APIRouter(prefix="/telemetry", tags=["Telemetria"])


@router.post(
    "",
    response_model=TelemetryEventResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_telemetry_event(
    data: TelemetryEventCreate,
    repository: RepositoryDependency,
):
    return repository.create_telemetry_event(data)


@router.get("", response_model=list[TelemetryEventResponse])
def list_telemetry_events(
    repository: RepositoryDependency,
    session_id: str | None = None,
    device_id: str | None = None,
):
    return repository.list_telemetry_events(session_id=session_id, device_id=device_id)
