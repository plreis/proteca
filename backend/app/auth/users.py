# backend/app/auth/users.py

from sqlmodel import Session, select

from app.core.config import settings
from app.models.entities import User
from app.schemas.auth import UserInDB, UserRole

DEMO_USER_ID = "usr-professor-01"
DEMO_USERNAME = "professor@proteca.local"


def get_user(session: Session, username: str) -> UserInDB | None:
    row = session.exec(select(User).where(User.username == username.strip().lower())).first()
    return UserInDB.model_validate(row, from_attributes=True) if row else None


def sync_demo_user(session: Session) -> None:
    """Cria ou atualiza o professor de demonstração ao iniciar a API.

    SENHA_TESTE_HASH é a fonte da verdade da senha: trocar a variável e reiniciar
    a API troca a senha gravada no banco.
    """
    row = session.exec(select(User).where(User.username == DEMO_USERNAME)).first()
    if row is None:
        row = User(
            id=DEMO_USER_ID,
            username=DEMO_USERNAME,
            full_name="Professor Demonstração",
            role=UserRole.PROFESSOR,
            hashed_password=settings.SENHA_TESTE_HASH,
        )
    else:
        row.hashed_password = settings.SENHA_TESTE_HASH
    session.add(row)
    session.commit()
