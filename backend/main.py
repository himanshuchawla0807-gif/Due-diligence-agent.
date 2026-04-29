"""FastAPI entrypoint for Due Diligence Agent Open."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import router
from .config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Open-source localhost due diligence agent with provider routing.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    return {
        "service": "Due Diligence Agent Open",
        "status": "running",
        "api": "/api/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host=settings.host, port=settings.port, reload=True)
