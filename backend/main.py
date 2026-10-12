"""FastAPI entrypoint for Due Diligence Agent Open."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from .api import router, job_managers
from .config import get_settings

settings = get_settings()

@asynccontextmanager
async def lifespan(app):
    yield
    for manager in list(job_managers.values()):
        await manager.close()
    job_managers.clear()

app = FastAPI(
    title=settings.app_name,
    description="Open-source localhost due diligence agent with provider routing.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

@app.exception_handler(ValueError)
async def invalid_request(request: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.get("/")
async def root():
    return {
        "service": "Due Diligence Agent Open",
        "status": "running",
        "api": "/api/health",
    }


@app.get("/health")
async def root_health():
    return {
        "service": "Due Diligence Agent Open",
        "status": "running",
        "api": "/api/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host=settings.host, port=settings.port, reload=True)
