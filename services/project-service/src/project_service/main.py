import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.episodes_chroma import router as episodes_router
from .api.health import router as health_router
from .api.projects import router as projects_router
from .database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Project Service", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(projects_router, prefix="/api/v1")
app.include_router(episodes_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")

if __name__ == "__main__":
    host = os.getenv("PROJECT_SERVICE_HOST", "0.0.0.0")
    port = int(os.getenv("PROJECT_SERVICE_PORT", "8001"))
    reload = os.getenv("PROJECT_SERVICE_RELOAD", "true").lower() in {"1", "true", "yes"}
    print(f"🔥 Starting Project Service on {host}:{port} (reload={reload})")
    uvicorn.run(
        "project_service.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )
