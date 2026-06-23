from fastapi import APIRouter

from app.api.endpoints.agents import router as agents_router
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.git_data_sources import router as git_data_sources_router
from app.api.endpoints.mixi import router as mixi_router
from app.api.endpoints.runs import router as runs_router
from app.api.endpoints.users import router as users_router
from app.api.endpoints.workspaces import router as workspaces_router

router = APIRouter(prefix="/api")
v1_router = APIRouter(prefix="/v1")


@router.get("/meta")
def get_meta() -> dict[str, object]:
    return {
        "service": "agent-platform",
        "version": "0.1.0",
        "status": "ok",
    }


v1_router.include_router(auth_router)
v1_router.include_router(git_data_sources_router)
v1_router.include_router(mixi_router)
v1_router.include_router(runs_router)
v1_router.include_router(users_router)
v1_router.include_router(workspaces_router)
v1_router.include_router(agents_router)
router.include_router(v1_router)
