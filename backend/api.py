"""FastAPI routes for the open due diligence workflow."""

from __future__ import annotations

import uuid
import asyncio
import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .config import Settings, get_settings
from .model_catalog import provider_catalog
from .pipeline import is_comprehensive_request, run_domain_pipeline
from .providers import ProviderError, get_provider
from .rag import LocalRagIndex
from .report import format_due_diligence_report
from .storage import SessionStore
from .auth import Principal, get_principal
from .jobs import JobManager

router = APIRouter()
stores: Dict[str, SessionStore] = {}
rag_indexes: Dict[str, LocalRagIndex] = {}
job_managers: Dict[str, JobManager] = {}


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


def tenant_settings(settings: Settings, principal: Principal) -> Settings:
    if settings.app_env == "production":
        raise HTTPException(503, "Standalone SQLite storage requires persistent single-host deployment; production cloud datastore is not configured")
    if principal.uid == "local":
        return settings
    namespace = hashlib.sha256(principal.uid.encode()).hexdigest()
    return settings.model_copy(update={"local_storage_dir": settings.local_storage_dir / "tenants" / namespace,
        "session_store": settings.session_store.parent / "tenants" / namespace / "sessions.json",
        "rag_storage_dir": settings.rag_storage_dir / "tenants" / namespace})

def get_store(settings: Settings = Depends(get_settings), principal: Principal = Depends(get_principal)) -> SessionStore:
    settings = tenant_settings(settings, principal)
    key = str(settings.session_store.resolve())
    if key not in stores:
        stores[key] = SessionStore(settings)
    return stores[key]


def get_rag(settings: Settings = Depends(get_settings), principal: Principal = Depends(get_principal)) -> LocalRagIndex:
    settings = tenant_settings(settings, principal)
    key = str(settings.rag_storage_dir.resolve())
    if key not in rag_indexes:
        rag_indexes[key] = LocalRagIndex(settings)
    return rag_indexes[key]


def ensure_session_rag(session_id: str, store: SessionStore, rag: LocalRagIndex) -> Dict[str, Any]:
    documents = store.documents(session_id)
    if not documents:
        return {
            "session_id": session_id,
            "documents_indexed": 0,
            "chunks_indexed": 0,
            "total_documents": 0,
            "total_chunks": 0,
        }
    return rag.index_documents(
        session_id,
        documents,
        source_directory="uploaded files",
        append=True,
    )


def due_diligence_context(session_id: str, focus: str, store: SessionStore, rag: LocalRagIndex) -> List[Dict[str, Any]]:
    ensure_session_rag(session_id, store, rag)
    queries = diligence_queries(session_id, focus, rag)
    documents = rag.multi_query_context_documents(
        session_id,
        queries,
        top_k_per_query=12,
        max_results=rag.settings.rag_report_top_k,
        per_file_limit=5,
    )
    if documents:
        return documents
    return store.documents(session_id)[:12]


def diligence_queries(session_id: str, focus: str, rag: LocalRagIndex) -> List[str]:
    base = focus or "comprehensive due diligence report on the uploaded data room"
    queries = [
        base,
        f"critical red flags fraud fabricated data contradictions inconsistencies related to: {base}",
        f"financial metrics revenue ARR EBITDA margins burn runway customer concentration related to: {base}",
        f"legal contracts change of control termination assignment IP compliance regulatory related to: {base}",
        f"commercial market customers competition pricing growth retention churn related to: {base}",
        f"technical architecture security SOC 2 privacy scalability product roadmap related to: {base}",
        f"management team founders HR resumes org chart governance cap table related to: {base}",
        f"write an investment committee due diligence memo with risks recommendations and cited evidence related to: {base}",
    ]
    for file_name in rag.document_names(session_id, limit=rag.settings.rag_file_query_limit):
        queries.append(f"Extract key facts, risks, numbers, contradictions, and diligence issues from {file_name}")
    return queries


async def _execute_analysis(
    session_id: str,
    focus: str,
    provider: Any,
    store: SessionStore,
    rag: LocalRagIndex,
    settings: Settings,
) -> Dict[str, Any]:
    ingestion = await asyncio.to_thread(ensure_session_rag, session_id, store, rag)
    if settings.due_diligence_multi_pass:
        result = await run_domain_pipeline(session_id, focus, provider, rag, settings)
        extraction_errors = [item for item in ingestion.get("skipped", [])]
        if extraction_errors:
            result["errors"].extend(item["reason"] for item in extraction_errors)
            result["status"] = "partial" if result["findings"] else "incomplete"
        return result

    documents = due_diligence_context(session_id, focus, store, rag)
    findings = await asyncio.wait_for(provider.analyze(documents, focus), settings.provider_timeout_seconds)
    findings = [provider._normalize_finding(finding, documents) for finding in findings]
    return {
        "findings": findings,
        "documents": documents,
        "steps": [
            {
                "action": "local_multi_query_rag_retrieval",
                "tool_input": focus,
                "observation": f"Retrieved {len(documents)} diversified chunks using domain and file-specific queries.",
            },
            {
                "action": "single_pass_analysis",
                "tool_input": focus,
                "observation": f"Generated {len(findings)} evidence-backed findings from retrieved source blocks.",
            },
        ],
        "errors": [],
        "status": "completed" if documents else "incomplete",
    }


def get_job_manager(settings, store, rag):
    key = str(store.database.path.resolve())
    if key not in job_managers:
        async def runner(session_id, payload):
            result = await _execute_analysis(session_id, payload["focus"], get_provider(settings), store, rag, settings)
            store.update_findings(session_id, result["findings"])
            return result
        job_managers[key] = JobManager(store.database, runner, settings.analysis_concurrency)
    return job_managers[key]


async def run_analysis(session_id, focus, provider, store, rag, settings):
    # Keep the existing synchronous-response frontend contract while durably recording work.
    manager = get_job_manager(settings, store, rag)
    job_id = manager.submit(session_id, {"focus": focus})
    result = await manager.wait(job_id)
    return {**result, "job_id": job_id}


class JobRequest(BaseModel):
    session_id: str
    focus: str = Field(min_length=1, max_length=10000)
    idempotency_key: str | None = Field(default=None, max_length=200)


@router.post("/jobs", status_code=202)
async def submit_job(payload: JobRequest, settings: Settings = Depends(get_settings), store: SessionStore = Depends(get_store), rag: LocalRagIndex = Depends(get_rag)):
    manager = get_job_manager(settings, store, rag)
    job_id = manager.submit(payload.session_id, {"focus": payload.focus}, payload.idempotency_key)
    return {"job_id": job_id, "status": manager.get(job_id)["status"]}


@router.get("/jobs/{job_id}")
async def job_status(job_id: str, settings: Settings = Depends(get_settings), store: SessionStore = Depends(get_store), rag: LocalRagIndex = Depends(get_rag)):
    manager = get_job_manager(settings, store, rag)
    manager.recover()
    job = manager.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


def format_chat_response(findings: List[Dict[str, Any]], industry: str | None = None) -> str:
    return format_due_diligence_report(findings, [], industry)


def citations_from_findings(findings: List[Dict[str, Any]], documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_file = {doc.get("file_name"): doc for doc in documents}
    citations = []
    seen: Dict[tuple[Any, str], str] = {}
    for index, finding in enumerate(findings, start=1):
        file_name = finding.get("source_file") or finding.get("file_name")
        matched_document = by_file.get(file_name)
        snippet = finding.get("text_snippet") or finding.get("evidence") or ""
        if matched_document and not snippet:
            snippet = matched_document.get("text", "")
        key = (file_name, snippet[:80])
        if not file_name or not snippet or not any(doc.get("file_name") == file_name and snippet in doc.get("text", "") for doc in documents):
            continue
        if key in seen:
            finding["_citation_id"] = seen[key]
            continue
        citation_id = f"finding-{index}"
        finding["_citation_id"] = citation_id
        seen[key] = citation_id
        citations.append(
            {
                "id": citation_id,
                "file_name": file_name,
                "relative_path": file_name,
                "source_path": file_name,
                "page": finding.get("page"),
                "sheet": finding.get("sheet"),
                "chunk_id": finding.get("chunk_id"),
                "source_hash": finding.get("source_hash"),
                "text_snippet": snippet[:320],
            }
        )

    for index, doc in enumerate(documents, start=1):
        file_name = doc.get("file_name", "Source Document")
        snippet = (doc.get("text") or "")[:320]
        key = (file_name, snippet[:80])
        if key in seen:
            doc["_citation_id"] = seen[key]
            continue
        citation_id = f"document-{index}"
        doc["_citation_id"] = citation_id
        citations.append(
            {
                "id": citation_id,
                "file_name": file_name,
                "relative_path": file_name,
                "source_path": file_name,
                "page": doc.get("page"),
                "sheet": doc.get("sheet"),
                "chunk_id": doc.get("chunk_id"),
                "text_snippet": snippet,
            }
        )
        seen[key] = citation_id

    return citations


@router.get("/health")
async def health(settings: Settings = Depends(get_settings)) -> Dict[str, Any]:
    return {
        "service": "due-diligence-agent-open",
        "status": "ok",
        "provider": settings.due_diligence_provider,
        "model": settings.effective_model(),
        "reasoning_effort": settings.openai_reasoning_effort if settings.due_diligence_provider == "openai" else None,
        "provider_key_available": settings.provider_key_available(),
        "rag_embedding_provider": settings.local_embedding_provider,
        "rag_embedding_model": settings.local_embedding_model,
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
    file_path: str | None = Form(None),
    store: SessionStore = Depends(get_store),
    rag: LocalRagIndex = Depends(get_rag),
) -> Dict[str, Any]:
    uploaded = await store.save_uploads(session_id, files, relative_paths=[file_path] if file_path else None)
    rag_result = await asyncio.to_thread(ensure_session_rag, session_id, store, rag)
    return {
        "success": True,
        "session_id": session_id,
        "uploaded_files": uploaded,
        "rag": {
            "embedding_provider": rag_result.get("embedding_provider", "local-hashing"),
            "embedding_model": rag_result.get("embedding_model"),
            "documents_indexed": rag_result.get("documents_indexed", 0),
            "chunks_indexed": rag_result.get("chunks_indexed", 0),
            "total_documents": rag_result.get("total_documents", 0),
            "total_chunks": rag_result.get("total_chunks", 0),
        },
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
    rag: LocalRagIndex = Depends(get_rag),
) -> Dict[str, Any]:
    resolved_session_id = session_id or f"session_{uuid.uuid4().hex[:10]}"
    uploaded = await store.save_uploads(resolved_session_id, files, relative_paths=[file_path] if file_path else None)
    rag_result = await asyncio.to_thread(ensure_session_rag, resolved_session_id, store, rag)
    return {
        "success": True,
        "session_id": resolved_session_id,
        "uploaded_files": uploaded,
        "rag": {
            "embedding_provider": rag_result.get("embedding_provider", "local-hashing"),
            "embedding_model": rag_result.get("embedding_model"),
            "documents_indexed": rag_result.get("documents_indexed", 0),
            "chunks_indexed": rag_result.get("chunks_indexed", 0),
            "total_documents": rag_result.get("total_documents", 0),
            "total_chunks": rag_result.get("total_chunks", 0),
        },
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
    provider = get_provider(settings)
    try:
        result = await run_analysis(session_id, focus, provider, store, rag, settings)
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    findings = result["findings"]
    documents = result["documents"]
    store.update_findings(session_id, findings)
    return {
        "success": result.get("status") == "completed",
        "status": result.get("status"),
        "errors": result.get("errors", []),
        "coverage": result.get("coverage", []),
        "job_id": result.get("job_id"),
        "session_id": session_id,
        "provider": settings.due_diligence_provider,
        "model": settings.effective_model(),
        "documents_used": len(documents),
        "rag_chunks_used": len(documents),
        "findings": findings,
        "steps": result["steps"],
    }


@router.post("/industry-dd")
async def industry_due_diligence(
    payload: IndustryAnalysisRequest,
    settings: Settings = Depends(get_settings),
    store: SessionStore = Depends(get_store),
    rag: LocalRagIndex = Depends(get_rag),
) -> Dict[str, Any]:
    focus = f"{payload.industry or 'general'} due diligence. {payload.query}".strip()
    provider = get_provider(settings)
    try:
        result = await run_analysis(payload.session_id, focus, provider, store, rag, settings)
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    findings = result["findings"]
    documents = result["documents"]
    store.update_findings(payload.session_id, findings)
    citations = citations_from_findings(findings, documents)
    return {
        "success": result.get("status") == "completed",
        "session_id": payload.session_id,
        "industry": payload.industry,
        "findings": findings,
        "response": format_due_diligence_report(findings, documents, payload.industry),
        "citations": citations,
        "status": result.get("status"),
        "errors": result.get("errors", []),
        "coverage": result.get("coverage", []),
        "job_id": result.get("job_id"),
        "steps": [
            *result["steps"],
            {
                "action": "investment_memo_synthesis",
                "tool_input": "Markdown IC memo with tables, chart placeholders, citations, and actions",
                "observation": f"Generated {len(findings)} evidence-backed findings.",
            },
        ],
        "warnings": result.get("errors", []),
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
    provider = get_provider(settings)
    try:
        result = await run_analysis(session_id, focus, provider, store, rag, settings)
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    findings = result["findings"]
    documents = result["documents"]
    citations = citations_from_findings(findings, documents)
    return {
        "session_id": session_id,
        "response": format_due_diligence_report(findings, documents, payload.industry),
        "citations": citations,
        "status": result.get("status"),
        "errors": result.get("errors", []),
        "coverage": result.get("coverage", []),
        "job_id": result.get("job_id"),
        "steps": [
            *result["steps"],
            {
                "action": "investment_memo_synthesis",
                "tool_input": "Markdown IC memo with tables, chart placeholders, citations, and actions",
                "observation": "Formatted the response as a structured due diligence memo.",
            }
        ],
        "warnings": result.get("errors", []),
        "chat_title": (payload.content[:48] or "Due Diligence Review").strip(),
    }


@router.post("/cancel/{session_id}")
async def cancel(session_id: str, store: SessionStore = Depends(get_store)) -> Dict[str, Any]:
    manager = job_managers.get(str(store.database.path.resolve()))
    count = manager.cancel_session(session_id) if manager else 0
    return {"success": True, "session_id": session_id, "status": "cancel_requested", "jobs_affected": count}


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
    findings = session.get("findings", [])
    documents = store.documents(session_id)
    citations = citations_from_findings(findings, documents) if findings else []
    return {
        "session": {
            "id": session_id,
            "title": "Due Diligence Review",
            "user_id": user_id,
        },
        "messages": [],
        "findings": findings,
        "report": format_due_diligence_report(findings, documents, None) if findings else None,
        "citations": citations,
    }


@router.post("/rag/index-local-directory")
async def index_local_directory(
    payload: IndexDirectoryRequest,
    rag: LocalRagIndex = Depends(get_rag),
) -> Dict[str, Any]:
    raise HTTPException(403, "Server directory indexing is CLI-only")

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
