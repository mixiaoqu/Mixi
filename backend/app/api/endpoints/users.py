from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Response, status

from app.api.auth import CurrentUser
from app.api.deps import RepositoryDep
from app.schemas.user import UserRead, UserUpdate


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: uuid.UUID, current_user: CurrentUser):
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return current_user


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    current_user: CurrentUser,
    repositories: RepositoryDep,
):
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return repositories.users.update(current_user, **payload.model_dump(exclude_unset=True))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: uuid.UUID,
    current_user: CurrentUser,
    repositories: RepositoryDep,
) -> Response:
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user = current_user
    if user.owned_workspaces:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Delete or transfer the user's owned workspaces first",
        )
    repositories.users.delete(user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
