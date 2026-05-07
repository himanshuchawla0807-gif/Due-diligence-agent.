"""FastAPI routes for the open due diligence workflow."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .config import Settings, get_settings
from .model_catalog import provider_catalog
from .providers import ProviderError, get_provider
from .rag import LocalRagIndex
from .storage import SessionStore

router = APIRouter()
stores: Dict[str, SessionStore] = {}
rag_indexes: Dict[str, LocalRagIndex] = {}


class IndexDirectoryRequest(BaseModel):
    session_id: str = Field(default="default")
    directory: str
    recursive: bool = True


class RagQueryRequest(BaseModel):
    session_id: str = Field(default="default")
    query: str
    top_k: int | None = None


class ChatRequest(BaseModel):
    content: str
    withSearch: bool = False
    session_id: str | None = None
    user_id: str | None = None
    industry: str | None = None


class IndustryAnalysisRequest(BaseModel):
    session_id: str
    industry: str | None = None
    query: str = "Generate comprehensive due diligence report"
    user_id: str | None = None


def get_store(settings: Settings = Depends(get_settings)) -> SessionStore:
    key = str(settings.session_store.resolve())
    if key not in stores:
        stores[key] = SessionStore(settings)
    return stores[key]


def get_rag(settings: Settings = Depends(get_settings)) -> LocalRagIndex:
    key = str(settings.rag_storage_dir.resolve())
    if key not in rag_indexes:
        rag_indexes[key] = LocalRagIndex(settings)
    return rag_indexes[key]


@router.get("/health")
async def health(settings: Settings = Depends(get_settings)) -> Dict[str, Any]:
    return {
        "service": "due-diligence-agent-open",
        "status": "ok",
        "provider": settings.due_diligence_provider,
        "model": settings.effective_model(),
        "reasoning_effort": settings.openai_reasoning_effort if settings.due_diligence_provider == "openai" else None,
        "provider_key_available": settings.provider_key_available(),
        "rag_embedding_provider": "local-hashing",
        "rag_storage_dir": str(settings.rag_storage_dir),
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


@router.post("/upload")
async def upload_files_legacy(
    session_id: str | None = Form(None),
    files: List[UploadFile] = File(...),
    auto_process: str | None = Form(None),
    user_id: str | None = Form(None),
    file_path: str | None = Form(None),
    store: SessionStore = Depends(get_store),
) -> Dict[str, Any]:
    resolved_session_id = session_id or f"session_{uuid.uuid4().hex[:10]}"
    uploaded = await store.save_uploads(resolved_session_id, files)
    return {
        "success": True,
        "session_id": resolved_session_id,
        "uploaded_files": uploaded,
        "auto_process": auto_process,
        "user_id": user_id,
        "file_path": file_path,
        "message": "Files uploaded locally.",
    }


@router.post("/due-diligence/analyze")
async def analyze(
    payload: Dict[str, Any],
    settings: Settings = Depends(get_settings),
    store: SessionStore = Depends(get_store),
    rag: LocalRagIndex = Depends(get_rag),
) -> Dict[str, Any]:
    session_id = payload.get("session_id") or payload.get("sessionId") or f"session_{uuid.uuid4().hex[:8]}"
    focus = payload.get("focus") or payload.get("query") or ""
    uploaded_documents = store.documents(session_id)
    rag_documents = []
    if payload.get("use_rag", True):
        rag_documents = rag.context_documents(session_id, focus or "due diligence risks")
    documents = uploaded_documents + rag_documents
    provider = get_provider(settings)
    try:
        findings = await provider.analyze(documents, focus)
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    store.update_findings(session_id, findings)
    return {
        "success": True,
        "session_id": session_id,
        "provider": settings.due_diligence_provider,
        "model": settings.effective_model(),
        "documents_used": len(documents),
        "rag_chunks_used": len(rag_documents),
        "findings": findings,
    }


@router.post("/industry-dd")
async def industry_due_diligence(
    payload: IndustryAnalysisRequest,
    settings: Settings = Depends(get_settings),
    store: SessionStore = Depends(get_store),
    rag: LocalRagIndex = Depends(get_rag),
) -> Dict[str, Any]:
    focus = f"{payload.industry or 'general'} due diligence. {payload.query}".strip()
    documents = store.documents(payload.session_id) + rag.context_documents(payload.session_id, focus)
    provider = get_provider(settings)
    try:
        findings = await provider.analyze(documents, focus)
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    store.update_findings(payload.session_id, findings)
    return {
        "success": True,
        "status": "completed",
        "session_id": payload.session_id,
        "industry": payload.industry,
        "findings": findings,
    }


@router.post("/chat")
async def chat(
    payload: ChatRequest,
    settings: Settings = Depends(get_settings),
    store: SessionStore = Depends(get_store),
    rag: LocalRagIndex = Depends(get_rag),
) -> Dict[str, Any]:
    session_id = payload.session_id or "default"
    focus = payload.content
    documents = store.documents(session_id) + rag.context_documents(session_id, focus)
    provider = get_provider(settings)
    try:
        findings = await provider.analyze(documents, focus)
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    lines = [f"## Due diligence response for {payload.industry or 'general'} review"]
    for finding in findings:
        category = finding.get("category", "General")
        severity = finding.get("severity", "medium")
        summary = finding.get("finding", "")
        recommendation = finding.get("recommendation", "")
        evidence = finding.get("evidence", "")
        lines.append(f"- **{category} ({severity})**: {summary}")
        if evidence:
            lines.append(f"  Evidence: {evidence}")
        if recommendation:
            lines.append(f"  Recommendation: {recommendation}")

    citations = [
        {
            "id": f"citation-{index}",
            "file_name": doc.get("file_name", "Source Document"),
            "relative_path": doc.get("file_name", "Source Document"),
            "page": 1,
            "text_snippet": (doc.get("text") or "")[:240],
        }
        for index, doc in enumerate(documents[:5], start=1)
    ]
    return {
        "status": "success",
        "session_id": session_id,
        "response": "\n".join(lines),
        "citations": citations,
        "steps": [
            {
                "action": "local_rag_context",
                "tool_input": payload.content,
                "observation": f"Used {len(documents)} local documents/chunks.",
            }
        ],
        "chat_title": (payload.content[:48] or "Due Diligence Review").strip(),
    }


@router.post("/cancel/{session_id}")
async def cancel(session_id: str) -> Dict[str, Any]:
    return {"success": True, "session_id": session_id, "status": "cancelled"}


@router.get("/session/{session_id}/documents")
async def session_documents(
    session_id: str,
    user_id: str | None = None,
    store: SessionStore = Depends(get_store),
) -> Dict[str, Any]:
    return {**store.document_tree(session_id), "user_id": user_id}


@router.get("/document/{session_id}/{file_path:path}")
async def get_document(
    session_id: str,
    file_path: str,
    user_id: str | None = None,
    store: SessionStore = Depends(get_store),
) -> FileResponse:
    path = store.resolve_file(session_id, file_path)
    if not path:
        raise HTTPException(status_code=404, detail="Document not found")
    return FileResponse(path)


@router.get("/sessions/{user_id}/{session_id}")
async def get_session(
    user_id: str,
    session_id: str,
    store: SessionStore = Depends(get_store),
) -> Dict[str, Any]:
    session = store.get_or_create(session_id)
    return {
        "session": {
            "id": session_id,
            "title": "Due Diligence Review",
            "user_id": user_id,
        },
        "messages": [],
        "findings": session.get("findings", []),
    }


@router.post("/rag/index-local-directory")
async def index_local_directory(
    payload: IndexDirectoryRequest,
    rag: LocalRagIndex = Depends(get_rag),
) -> Dict[str, Any]:
    try:
        return {
            "success": True,
            **rag.index_directory(payload.session_id, Path(payload.directory), recursive=payload.recursive),
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/rag/status/{session_id}")
async def rag_status(session_id: str, rag: LocalRagIndex = Depends(get_rag)) -> Dict[str, Any]:
    return rag.status(session_id)


@router.post("/rag/query")
async def rag_query(payload: RagQueryRequest, rag: LocalRagIndex = Depends(get_rag)) -> Dict[str, Any]:
    results = rag.query(payload.session_id, payload.query, top_k=payload.top_k)
    return {
        "success": True,
        "session_id": payload.session_id,
        "query": payload.query,
        "results": results,
    }
