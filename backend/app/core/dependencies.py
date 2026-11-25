from typing import Annotated

from fastapi import Depends

from app.db import SessionDep
from app.repositories.sql_repo import SqlRepository
from app.services.class_screen import ClassVoiceCache

# Voz da tela da turma, em memória e compartilhada pelo processo.
class_voices = ClassVoiceCache()


def get_repository(session: SessionDep) -> SqlRepository:
    return SqlRepository(session)


RepositoryDependency = Annotated[SqlRepository, Depends(get_repository)]
