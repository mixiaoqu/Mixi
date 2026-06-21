from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.postgres import get_db
from app.db.repositories import Repositories


def get_repositories(db: Session) -> Repositories:
    return Repositories.from_session(db)


def get_repository_bundle(db: Annotated[Session, Depends(get_db, scope="function")]) -> Repositories:
    return get_repositories(db)


RepositoryDep = Annotated[Repositories, Depends(get_repository_bundle)]
