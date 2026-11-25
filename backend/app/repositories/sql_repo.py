import secrets
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from app.core.errors import ConflictError, InvalidReferenceError, NotFoundError
from app.models.entities import (
    Classroom,
    Device,
    Incident,
    IncidentAction,
    LessonSession,
    School,
    SessionAction,
    SessionDevice,
    TelemetryEvent,
)
from app.schemas.ai import ProtecaIntervention
from app.schemas.devices import DeviceCreate, DeviceResponse, DeviceStatus
from app.schemas.incidents import (
    IncidentActionLog,
    IncidentCategory,
    IncidentCreate,
    IncidentResponse,
    IncidentStatus,
)
from app.schemas.school import ClassroomResponse, SchoolResponse
from app.schemas.sessions import (
    SessionActionEntry,
    SessionCreate,
    SessionResponse,
    SessionStatus,
)
from app.schemas.turma import ClassScreenState
from app.schemas.telemetry import TelemetryEventCreate, TelemetryEventResponse

# Sem 0/O e 1/I, que se confundem quando o professor dita o código para a turma.
CLASS_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CLASS_CODE_LENGTH = 6

INCIDENT_TRANSITIONS: dict[IncidentStatus, set[IncidentStatus]] = {
    IncidentStatus.ABERTA: {IncidentStatus.EM_ANALISE, IncidentStatus.ENCERRADA},
    IncidentStatus.EM_ANALISE: {IncidentStatus.ABERTA, IncidentStatus.ENCERRADA},
    IncidentStatus.ENCERRADA: {IncidentStatus.ABERTA},
}

INCIDENT_ACTION_LABELS = {
    IncidentStatus.ABERTA: "Reabertura de ocorrência",
    IncidentStatus.EM_ANALISE: "Transição para Em Análise",
    IncidentStatus.ENCERRADA: "Ocorrência encerrada",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


# ---------- Conversão das tabelas para os contratos da API ----------
def _school_response(row: School) -> SchoolResponse:
    return SchoolResponse.model_validate(row, from_attributes=True)


def _classroom_response(row: Classroom) -> ClassroomResponse:
    return ClassroomResponse.model_validate(row, from_attributes=True)


def _device_response(row: Device) -> DeviceResponse:
    return DeviceResponse.model_validate(row, from_attributes=True)


def _session_response(row: LessonSession) -> SessionResponse:
    return SessionResponse(
        id=row.id,
        school_id=row.school_id,
        classroom_id=row.classroom_id,
        teacher_name=row.teacher_name,
        objective=row.objective,
        status=row.status,
        started_at=row.started_at,
        ended_at=row.ended_at,
        allocated_device_ids=[device.id for device in row.devices],
        closing_justification=row.closing_justification,
        class_code=row.class_code,
        action_log=[
            SessionActionEntry.model_validate(action, from_attributes=True)
            for action in row.actions
        ],
    )


def _incident_response(row: Incident) -> IncidentResponse:
    return IncidentResponse(
        id=row.id,
        school_id=row.school_id,
        session_id=row.session_id,
        device_id=row.device_id,
        category=row.category,
        description=row.description,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
        closing_justification=row.closing_justification,
        actions=[
            IncidentActionLog.model_validate(action, from_attributes=True)
            for action in row.actions
        ],
    )


def _event_response(row: TelemetryEvent) -> TelemetryEventResponse:
    return TelemetryEventResponse.model_validate(row, from_attributes=True)


class SqlRepository:
    """Regras de negócio sobre o banco (SQLModel).

    Os métodos públicos são os mesmos do antigo repositório em memória: recebem e
    devolvem contratos Pydantic e levantam os erros de domínio de app/core/errors.py.
    Cada operação que altera dados confirma a própria transação.
    """

    def __init__(self, session: Session):
        self.session = session

    # ---------- Carga inicial ----------
    def add_school(self, school: SchoolResponse) -> None:
        self.session.add(School(**school.model_dump()))
        self.session.flush()

    def add_classroom(self, classroom: ClassroomResponse) -> None:
        self.session.add(Classroom(**classroom.model_dump()))
        self.session.flush()

    def add_device(self, device: DeviceResponse) -> None:
        self.session.add(Device(**device.model_dump()))
        self.session.flush()

    def add_session(self, session: SessionResponse) -> None:
        self.session.add(
            LessonSession(
                **session.model_dump(exclude={"allocated_device_ids", "action_log"})
            )
        )
        self.session.flush()
        self._link_devices(session.id, session.allocated_device_ids)
        for entry in session.action_log:
            self.session.add(SessionAction(session_id=session.id, **entry.model_dump()))
        self.session.flush()

    def add_incident(self, incident: IncidentResponse) -> None:
        self.session.add(Incident(**incident.model_dump(exclude={"actions"})))
        self.session.flush()
        for action in incident.actions:
            self.session.add(IncidentAction(incident_id=incident.id, **action.model_dump()))
        self.session.flush()

    # ---------- Escola e turmas ----------
    def get_school(self) -> SchoolResponse:
        return _school_response(self._school_row())

    def list_classrooms(self) -> list[ClassroomResponse]:
        rows = self.session.exec(select(Classroom).order_by(Classroom.name)).all()
        return [_classroom_response(row) for row in rows]

    def get_classroom(self, classroom_id: str) -> ClassroomResponse:
        return _classroom_response(self._classroom_row(classroom_id))

    # ---------- Dispositivos ----------
    def list_devices(self, status: DeviceStatus | None = None) -> list[DeviceResponse]:
        query = select(Device).order_by(Device.patrimonio)
        if status:
            query = query.where(Device.status == status)
        return [_device_response(row) for row in self.session.exec(query).all()]

    def get_device(self, device_id: str) -> DeviceResponse:
        return _device_response(self._device_row(device_id))

    def create_device(self, data: DeviceCreate) -> DeviceResponse:
        patrimonio = data.patrimonio.strip().upper()
        duplicated = ConflictError(f"Já existe um dispositivo com patrimônio '{patrimonio}'.")
        if self.session.exec(select(Device.id).where(Device.patrimonio == patrimonio)).first():
            raise duplicated

        row = Device(
            id=_new_id("dev"),
            school_id=self._school_row().id,
            patrimonio=patrimonio,
            type=data.type,
            model=data.model.strip(),
            status=DeviceStatus.DISPONIVEL,
        )
        self.session.add(row)
        try:
            self.session.commit()
        except IntegrityError:
            # Outra requisição gravou o mesmo patrimônio entre a consulta e o commit.
            self.session.rollback()
            raise duplicated
        return _device_response(row)

    def update_device_status(self, device_id: str, status: DeviceStatus) -> DeviceResponse:
        if status == DeviceStatus.EM_USO:
            raise InvalidReferenceError(
                "O status 'em_uso' é definido ao abrir uma sessão de aula."
            )
        row = self._device_row(device_id)
        if row.status == DeviceStatus.EM_USO:
            raise ConflictError(
                "Dispositivo em uso em uma sessão aberta. Encerre a sessão antes."
            )
        row.status = status
        self.session.add(row)
        self.session.commit()
        return _device_response(row)

    # ---------- Sessões ----------
    def list_sessions(self, status: SessionStatus | None = None) -> list[SessionResponse]:
        query = (
            select(LessonSession)
            .options(selectinload(LessonSession.devices), selectinload(LessonSession.actions))
            .order_by(LessonSession.started_at.desc())
        )
        if status:
            query = query.where(LessonSession.status == status)
        return [_session_response(row) for row in self.session.exec(query).all()]

    def get_session(self, session_id: str) -> SessionResponse:
        return _session_response(self._session_row(session_id))

    def get_open_session(self, session_id: str) -> SessionResponse:
        return _session_response(self._open_session_row(session_id))

    def create_session(self, data: SessionCreate) -> SessionResponse:
        device_ids = list(dict.fromkeys(data.device_ids))
        classroom = self._classroom_row(data.classroom_id)
        devices = [self._device_row(device_id) for device_id in device_ids]
        for device in devices:
            if device.status != DeviceStatus.DISPONIVEL:
                raise ConflictError(f"Dispositivo '{device.patrimonio}' não está disponível.")

        now = _now()
        teacher_name = data.teacher_name.strip()
        row = LessonSession(
            id=_new_id("sess"),
            school_id=classroom.school_id,
            classroom_id=classroom.id,
            teacher_name=teacher_name,
            objective=data.objective.strip(),
            status=SessionStatus.ABERTA,
            started_at=now,
            class_code=self._new_class_code(),
        )
        self.session.add(row)
        self.session.flush()
        self._link_devices(row.id, device_ids)
        for device in devices:
            device.status = DeviceStatus.EM_USO
            self.session.add(device)
        self.session.add(
            SessionAction(
                id=_new_id("log"),
                session_id=row.id,
                timestamp=now,
                action="Sessão aberta",
                author=teacher_name,
                note=f"Dispositivos vinculados: {len(device_ids)}.",
            )
        )
        self.session.commit()
        return _session_response(row)

    def close_session(self, session_id: str, justification: str) -> SessionResponse:
        row = self._open_session_row(session_id)
        now = _now()
        row.status = SessionStatus.ENCERRADA
        row.ended_at = now
        row.closing_justification = justification.strip()
        self.session.add(row)
        self.session.add(
            SessionAction(
                id=_new_id("log"),
                session_id=row.id,
                timestamp=now,
                action="Sessão encerrada",
                author=row.teacher_name,
                note=f"Justificativa: {justification.strip()}",
            )
        )
        for device in row.devices:
            if device.status == DeviceStatus.EM_USO:
                device.status = DeviceStatus.DISPONIVEL
                self.session.add(device)
        self.session.commit()
        return _session_response(row)

    # ---------- Ocorrências ----------
    def list_incidents(
        self,
        session_id: str | None = None,
        category: IncidentCategory | None = None,
        status: IncidentStatus | None = None,
    ) -> list[IncidentResponse]:
        query = (
            select(Incident)
            .options(selectinload(Incident.actions))
            .order_by(Incident.created_at.desc())
        )
        if session_id:
            query = query.where(Incident.session_id == session_id)
        if category:
            query = query.where(Incident.category == category)
        if status:
            query = query.where(Incident.status == status)
        return [_incident_response(row) for row in self.session.exec(query).all()]

    def get_incident(self, incident_id: str) -> IncidentResponse:
        return _incident_response(self._incident_row(incident_id))

    def create_incident(self, data: IncidentCreate) -> IncidentResponse:
        session = self._open_session_row(data.session_id)
        if data.device_id:
            self._check_device_in_session(session, data.device_id)

        now = _now()
        row = Incident(
            id=_new_id("inc"),
            school_id=session.school_id,
            session_id=session.id,
            device_id=data.device_id,
            category=data.category,
            description=data.description.strip(),
            status=IncidentStatus.ABERTA,
            created_at=now,
        )
        self.session.add(row)
        self.session.flush()
        self.session.add(
            IncidentAction(
                id=_new_id("act"),
                incident_id=row.id,
                timestamp=now,
                action="Ocorrência registrada",
                author=session.teacher_name,
                note="Registro feito durante a sessão de aula.",
            )
        )
        self.session.commit()
        return _incident_response(row)

    def update_incident_status(
        self,
        incident_id: str,
        new_status: IncidentStatus,
        justification: str | None = None,
    ) -> IncidentResponse:
        row = self._incident_row(incident_id)
        if new_status not in INCIDENT_TRANSITIONS[row.status]:
            raise ConflictError(
                f"Não é possível mudar a ocorrência de '{row.status.value}' "
                f"para '{new_status.value}'."
            )

        session = self._session_row(row.session_id)
        now = _now()
        if new_status == IncidentStatus.ENCERRADA and justification:
            row.closing_justification = justification.strip()
        row.status = new_status
        row.updated_at = now
        self.session.add(row)
        self.session.add(
            IncidentAction(
                id=_new_id("act"),
                incident_id=row.id,
                timestamp=now,
                action=INCIDENT_ACTION_LABELS[new_status],
                author=session.teacher_name,
                note=justification or "Atualização de estado no fluxo pedagógico.",
            )
        )
        self.session.commit()
        return _incident_response(row)

    # ---------- Telemetria ----------
    def create_telemetry_event(self, data: TelemetryEventCreate) -> TelemetryEventResponse:
        session = self._open_session_row(data.session_id)
        self._check_device_in_session(session, data.device_id)
        row = TelemetryEvent(id=_new_id("evt"), received_at=_now(), **data.model_dump())
        self.session.add(row)
        self.session.commit()
        return _event_response(row)

    def list_telemetry_events(
        self,
        session_id: str | None = None,
        device_id: str | None = None,
    ) -> list[TelemetryEventResponse]:
        query = select(TelemetryEvent).order_by(TelemetryEvent.occurred_at.desc())
        if session_id:
            query = query.where(TelemetryEvent.session_id == session_id)
        if device_id:
            query = query.where(TelemetryEvent.device_id == device_id)
        return [_event_response(row) for row in self.session.exec(query).all()]

    # ---------- Tela da turma ----------
    def set_broadcast(
        self, session_id: str, intervention: ProtecaIntervention
    ) -> datetime:
        row = self._open_session_row(session_id)
        now = _now()
        row.broadcast_intervention = intervention.model_dump(mode="json")
        row.broadcast_at = now
        self.session.add(row)
        self.session.commit()
        return row.broadcast_at

    def clear_broadcast(self, session_id: str) -> None:
        row = self._session_row(session_id)
        row.broadcast_intervention = None
        row.broadcast_at = None
        self.session.add(row)
        self.session.commit()

    def get_class_screen_state(self, class_code: str) -> ClassScreenState:
        row = self.session.exec(
            select(LessonSession).where(LessonSession.class_code == class_code.strip().upper())
        ).first()
        if row is None:
            raise NotFoundError("Código da turma não encontrado.")
        shown = row.status == SessionStatus.ABERTA and row.broadcast_intervention is not None
        return ClassScreenState(
            session_id=row.id,
            class_code=row.class_code,
            objective=row.objective,
            session_status=row.status,
            intervention=(
                ProtecaIntervention.model_validate(row.broadcast_intervention) if shown else None
            ),
            broadcast_at=row.broadcast_at if shown else None,
        )

    # ---------- Apoio ----------
    def _school_row(self) -> School:
        row = self.session.exec(select(School).order_by(School.id)).first()
        if row is None:
            raise NotFoundError("Nenhuma escola cadastrada.")
        return row

    def _classroom_row(self, classroom_id: str) -> Classroom:
        row = self.session.get(Classroom, classroom_id)
        if row is None:
            raise NotFoundError(f"Turma '{classroom_id}' não encontrada.")
        return row

    def _device_row(self, device_id: str) -> Device:
        row = self.session.get(Device, device_id)
        if row is None:
            raise NotFoundError(f"Dispositivo '{device_id}' não encontrado.")
        return row

    def _session_row(self, session_id: str) -> LessonSession:
        row = self.session.get(LessonSession, session_id)
        if row is None:
            raise NotFoundError(f"Sessão '{session_id}' não encontrada.")
        return row

    def _open_session_row(self, session_id: str) -> LessonSession:
        row = self._session_row(session_id)
        if row.status != SessionStatus.ABERTA:
            raise ConflictError("A sessão já foi encerrada.")
        return row

    def _incident_row(self, incident_id: str) -> Incident:
        row = self.session.get(Incident, incident_id)
        if row is None:
            raise NotFoundError(f"Ocorrência '{incident_id}' não encontrada.")
        return row

    def _new_class_code(self) -> str:
        # 32^6 combinações: colisão é rara, mas o código precisa ser único.
        while True:
            code = "".join(
                secrets.choice(CLASS_CODE_ALPHABET) for _ in range(CLASS_CODE_LENGTH)
            )
            taken = self.session.exec(
                select(LessonSession.id).where(LessonSession.class_code == code)
            ).first()
            if taken is None:
                return code

    def _link_devices(self, session_id: str, device_ids: list[str]) -> None:
        for position, device_id in enumerate(device_ids):
            self.session.add(
                SessionDevice(session_id=session_id, device_id=device_id, position=position)
            )

    def _check_device_in_session(self, session: LessonSession, device_id: str) -> None:
        self._device_row(device_id)
        if device_id not in {device.id for device in session.devices}:
            raise InvalidReferenceError(
                f"Dispositivo '{device_id}' não está vinculado à sessão '{session.id}'."
            )
