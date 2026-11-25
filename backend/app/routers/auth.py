# backend/app/routers/auth.py

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.auth.middleware import (
    CurrentUser,
    authenticate_user,
    create_access_token,
)
from app.db import SessionDep
from app.schemas.auth import TokenResponse, UserPublic


router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/token", response_model=TokenResponse)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDep,
):
    user = authenticate_user(session, form.username, form.password)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha inválidos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(
        access_token=create_access_token(user),
    )


@router.get("/me", response_model=UserPublic)
def get_authenticated_user(
    current_user: CurrentUser,
):
    return current_user