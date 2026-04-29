"""FastAPI routes for the open due diligence workflow."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, File, Form, UploadFile

from .config import Settings, get_settings
from .model_catalog import provider_catalog
from .providers import get_provider
from .storage import SessionStore

router = APIRouter()
stores: Dict[str, SessionStore] = {}


def get_store(settings: Settings = Depends(get_settings)) -> SessionStore:
    key = str(settings.session_store.resolve())
    if key not in stores:
        stores[key] = SessionStore(settings)
    return stores[key]


@router.get("/health")
async def health(settings: Settings = Depends(get_settings)) -> Dict[str, Any]:
    return {
        "service": "due-diligence-agent-open",
        "status": "ok",
        "provider": settings.due_diligence_provider,
        "model": settings.effective_model(),
        "reasoning_effort": settings.openai_reasoning_effort if settings.due_diligence_provider == "openai" else None,
        "provider_key_available": settings.provider_key_available(),
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/providers")
async def providers() -> Dict[str, Any]:
    return provider_catalog()


@router.post("/due-diligence/upload")
async def upload_files(
    session_id: str = Form(...),
    files: List[UploadFile] = File(...),
    store: SessionStore = Depends(get_store),
) -> Dict[str, Any]:
    uploaded = await store.save_uploads(session_id, files)
    return {
        "success": True,
        "session_id": session_id,
        "uploaded_files": uploaded,
        "message": "Files uploaded locally.",
    }


@router.post("/due-diligence/analyze")
async def analyze(
    payload: Dict[str, Any],
    settings: Settings = Depends(get_settings),
    store: SessionStore = Depends(get_store),
) -> Dict[str, Any]:
    session_id = payload.get("session_id") or payload.get("sessionId") or f"session_{uuid.uuid4().hex[:8]}"
    focus = payload.get("focus") or payload.get("query") or ""
    provider = get_provider(settings)
    findings = await provider.analyze(store.documents(session_id), focus)
    store.update_findings(session_id, findings)
    return {
        "success": True,
        "session_id": session_id,
        "provider": settings.due_diligence_provider,
        "model": settings.effective_model(),
        "findings": findings,
    }
