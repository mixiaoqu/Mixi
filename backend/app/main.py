from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.api.routes import router
from app.core.config import settings
from app.db.postgres import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.init_db_on_startup:
        init_db()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.include_router(router)


@app.exception_handler(IntegrityError)
def handle_integrity_error(_: Request, __: IntegrityError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "The request conflicts with an existing or referenced resource"},
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
