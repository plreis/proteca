"""Banco de dados: engine, criação das tabelas, carga inicial e sessão por requisição.

Nenhuma parte do código fala com o banco sem passar pelo SQLModel (ADR 0003): voltar
para Postgres é trocar DATABASE_URL.
"""

from collections.abc import Iterator
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, Request
from sqlalchemy import Engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.auth.users import sync_demo_user
from app.core.config import settings
from app.models.entities import School
from app.repositories.seed import load_demo_data
from app.repositories.sql_repo import SqlRepository


def _enable_sqlite_foreign_keys(dbapi_connection: Any, _: Any) -> None:
    # O SQLite só confere chaves estrangeiras quando a conexão pede.
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_db_engine(url: str) -> Engine:
    parsed = make_url(url)
    if parsed.get_backend_name() != "sqlite":
        return create_engine(url, pool_pre_ping=True)

    connect_args = {"check_same_thread": False}
    database = parsed.database
    if not database or database == ":memory:":
        # Banco em memória (testes): uma conexão única, senão cada conexão veria um banco vazio.
        engine = create_engine(url, connect_args=connect_args, poolclass=StaticPool)
    else:
        # No container, ./data/proteca.db é o volume do Coolify montado em /app/data.
        Path(database).parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(url, connect_args=connect_args)
    event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    return engine


def init_db(engine: Engine) -> None:
    """Cria as tabelas, grava a carga inicial num banco vazio e o usuário de demonstração."""
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        if settings.SEED_DEMO_DATA and session.exec(select(School)).first() is None:
            load_demo_data(SqlRepository(session))
            session.commit()
        sync_demo_user(session)


def get_session(request: Request) -> Iterator[Session]:
    with Session(request.app.state.engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
