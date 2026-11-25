"""Tabelas do banco (SQLModel). As rotas falam com elas só pelo repositório."""

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, DateTime
from sqlalchemy.types import TypeDecorator
from sqlmodel import Field, Relationship, SQLModel

from app.schemas.auth import UserRole
from app.schemas.devices import DeviceStatus, DeviceType
from app.schemas.incidents import IncidentCategory, IncidentStatus
from app.schemas.sessions import SessionStatus
from app.schemas.telemetry import TelemetryEventType


class UTCDateTime(TypeDecorator):
    """Grava em UTC e devolve sempre com fuso.

    O SQLite não guarda o fuso e devolveria datas sem ele; aqui toda data lida do
    banco volta como UTC, e uma data sem fuso recebida pela API é tratada como UTC.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        value = value.astimezone(timezone.utc)
        return value.replace(tzinfo=None) if dialect.name == "sqlite" else value

    def process_result_value(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class School(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    city: str
    created_at: datetime = Field(default_factory=_now, sa_type=UTCDateTime)

    classrooms: list["Classroom"] = Relationship(back_populates="school")
    devices: list["Device"] = Relationship(back_populates="school")


class Classroom(SQLModel, table=True):
    """Turma: identificada só pelo nome do grupo, nunca pelos estudantes."""

    id: str = Field(primary_key=True)
    school_id: str = Field(foreign_key="school.id", index=True)
    name: str
    grade: str

    school: Optional[School] = Relationship(back_populates="classrooms")
    sessions: list["LessonSession"] = Relationship(back_populates="classroom")


class SessionDevice(SQLModel, table=True):
    """Dispositivos alocados a uma sessão; position guarda a ordem informada pelo professor."""

    session_id: str = Field(foreign_key="lessonsession.id", primary_key=True)
    device_id: str = Field(foreign_key="device.id", primary_key=True)
    position: int = Field(default=0)


class Device(SQLModel, table=True):
    id: str = Field(primary_key=True)
    school_id: str = Field(foreign_key="school.id", index=True)
    patrimonio: str = Field(unique=True, index=True)
    type: DeviceType
    model: str
    status: DeviceStatus = Field(default=DeviceStatus.DISPONIVEL)

    school: Optional[School] = Relationship(back_populates="devices")
    # Somente leitura: o vínculo é gravado em SessionDevice, com a posição.
    sessions: list["LessonSession"] = Relationship(
        back_populates="devices",
        link_model=SessionDevice,
        sa_relationship_kwargs={"viewonly": True},
    )


class LessonSession(SQLModel, table=True):
    id: str = Field(primary_key=True)
    school_id: str = Field(foreign_key="school.id", index=True)
    classroom_id: str = Field(foreign_key="classroom.id", index=True)
    teacher_name: str
    objective: str
    status: SessionStatus = Field(default=SessionStatus.ABERTA, index=True)
    started_at: datetime = Field(default_factory=_now, sa_type=UTCDateTime)
    ended_at: Optional[datetime] = Field(default=None, sa_type=UTCDateTime)
    closing_justification: Optional[str] = None
    # Código da turma e intervenção enviada à tela da turma (ADR 0004).
    class_code: str = Field(unique=True, index=True, max_length=6)
    broadcast_intervention: Optional[dict[str, Any]] = Field(default=None, sa_type=JSON)
    broadcast_at: Optional[datetime] = Field(default=None, sa_type=UTCDateTime)

    classroom: Optional[Classroom] = Relationship(back_populates="sessions")
    devices: list[Device] = Relationship(
        back_populates="sessions",
        link_model=SessionDevice,
        sa_relationship_kwargs={"viewonly": True, "order_by": "SessionDevice.position"},
    )
    actions: list["SessionAction"] = Relationship(
        back_populates="session",
        cascade_delete=True,
        sa_relationship_kwargs={"order_by": "SessionAction.timestamp"},
    )
    incidents: list["Incident"] = Relationship(back_populates="session")
    telemetry_events: list["TelemetryEvent"] = Relationship(back_populates="session")


class SessionAction(SQLModel, table=True):
    """Histórico da sessão (abertura, encerramento)."""

    id: str = Field(primary_key=True)
    session_id: str = Field(foreign_key="lessonsession.id", index=True, ondelete="CASCADE")
    timestamp: datetime = Field(sa_type=UTCDateTime)
    action: str
    author: str
    note: Optional[str] = None

    session: Optional[LessonSession] = Relationship(back_populates="actions")


class Incident(SQLModel, table=True):
    id: str = Field(primary_key=True)
    school_id: str = Field(foreign_key="school.id", index=True)
    session_id: str = Field(foreign_key="lessonsession.id", index=True)
    device_id: Optional[str] = Field(default=None, foreign_key="device.id")
    category: IncidentCategory
    description: str
    status: IncidentStatus = Field(default=IncidentStatus.ABERTA)
    created_at: datetime = Field(default_factory=_now, sa_type=UTCDateTime)
    updated_at: Optional[datetime] = Field(default=None, sa_type=UTCDateTime)
    closing_justification: Optional[str] = None

    session: Optional[LessonSession] = Relationship(back_populates="incidents")
    device: Optional[Device] = Relationship()
    actions: list["IncidentAction"] = Relationship(
        back_populates="incident",
        cascade_delete=True,
        sa_relationship_kwargs={"order_by": "IncidentAction.timestamp"},
    )


class IncidentAction(SQLModel, table=True):
    """Histórico da ocorrência (registro e cada mudança de estado)."""

    id: str = Field(primary_key=True)
    incident_id: str = Field(foreign_key="incident.id", index=True, ondelete="CASCADE")
    timestamp: datetime = Field(sa_type=UTCDateTime)
    action: str
    author: str
    note: str = ""

    incident: Optional[Incident] = Relationship(back_populates="actions")


class TelemetryEvent(SQLModel, table=True):
    id: str = Field(primary_key=True)
    session_id: str = Field(foreign_key="lessonsession.id", index=True)
    device_id: str = Field(foreign_key="device.id", index=True)
    event_type: TelemetryEventType
    occurred_at: datetime = Field(sa_type=UTCDateTime)
    duration_seconds: Optional[int] = None
    received_at: datetime = Field(default_factory=_now, sa_type=UTCDateTime)

    session: Optional[LessonSession] = Relationship(back_populates="telemetry_events")


class User(SQLModel, table=True):
    id: str = Field(primary_key=True)
    username: str = Field(unique=True, index=True)
    full_name: str
    role: UserRole = Field(default=UserRole.PROFESSOR)
    hashed_password: str
    disabled: bool = False
