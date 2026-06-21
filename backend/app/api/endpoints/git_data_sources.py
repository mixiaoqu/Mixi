from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Response, status

from app.api.auth import CurrentUser
from app.api.deps import RepositoryDep
from app.schemas.git_data_source import (
    GitConnectionTest,
    GitConnectionTestResult,
    GitDataSourceCreate,
    GitDataSourceRead,
)
from app.services.git_remote import GitConnectionError, encrypt_credential, inspect_remote


router = APIRouter(prefix="/git-data-sources", tags=["git-data-sources"])


def _inspect(payload: GitConnectionTest | GitDataSourceCreate):
    try:
        return inspect_remote(payload.repository_url, payload.auth_type, payload.credential)
    except GitConnectionError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.post("/test", response_model=GitConnectionTestResult)
def test_git_connection(payload: GitConnectionTest, _: CurrentUser):
    remote = _inspect(payload)
    return GitConnectionTestResult(
        repository_name=remote.repository_name,
        branches=remote.branches,
        default_branch=remote.default_branch,
    )


@router.get("", response_model=list[GitDataSourceRead])
def list_git_data_sources(current_user: CurrentUser, repositories: RepositoryDep):
    return repositories.git_data_sources.list_by_user(current_user.id)


@router.post("", response_model=GitDataSourceRead, status_code=status.HTTP_201_CREATED)
def create_git_data_source(
    payload: GitDataSourceCreate,
    current_user: CurrentUser,
    repositories: RepositoryDep,
):
    remote = _inspect(payload)
    if payload.default_branch not in remote.branches:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="默认分支不存在")
    return repositories.git_data_sources.create(
        user_id=current_user.id,
        name=remote.repository_name,
        repository_url=payload.repository_url.strip(),
        auth_type=payload.auth_type,
        encrypted_credential=encrypt_credential(payload.credential),
        default_branch=payload.default_branch,
        status="connected",
    )


@router.delete("/{data_source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_git_data_source(
    data_source_id: uuid.UUID,
    current_user: CurrentUser,
    repositories: RepositoryDep,
) -> Response:
    data_source = repositories.git_data_sources.get(data_source_id)
    if data_source is None or data_source.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Git 数据源不存在")
    repositories.git_data_sources.delete(data_source)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
