from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.agent.graph import PlatformGraph
from app.agent.graph.checkpoint import postgres_checkpointer
from app.api.routes import router
from app.core.config import settings
from app.db.postgres import init_db
from app.observability.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    if settings.init_db_on_startup:
        init_db()
    async with postgres_checkpointer() as checkpointer:
        app.state.platform_graph = PlatformGraph(checkpointer=checkpointer)
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
