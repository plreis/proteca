from fastapi import APIRouter

from app.core.dependencies import RepositoryDependency
from app.schemas.school import ClassroomResponse, SchoolResponse

router = APIRouter(tags=["Escola"])


@router.get("/school", response_model=SchoolResponse)
def get_school(repository: RepositoryDependency):
    return repository.get_school()


@router.get("/classrooms", response_model=list[ClassroomResponse])
def list_classrooms(repository: RepositoryDependency):
    return repository.list_classrooms()


@router.get("/classrooms/{classroom_id}", response_model=ClassroomResponse)
def get_classroom(classroom_id: str, repository: RepositoryDependency):
    return repository.get_classroom(classroom_id)
