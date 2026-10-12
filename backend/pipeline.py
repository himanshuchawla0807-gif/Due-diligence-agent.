"""Multi-pass due diligence analysis pipeline."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List

from .config import Settings
from .providers import BaseProvider, ProviderError
from .rag import LocalRagIndex


@dataclass(frozen=True)
class DomainPass:
    name: str
    category: str
    queries: List[str]


DOMAIN_PASSES = [
    DomainPass(
        name="Financial Team",
        category="Financial",
        queries=[
            "revenue ARR MRR bookings EBITDA gross margin burn runway cash balance forecast projections",
            "financial statements quality of earnings customer concentration working capital debt tax",
            "hockey stick forecast unrealistic growth margin inconsistency financial red flags",
        ],
    ),
    DomainPass(
        name="Legal Team",
        category="Legal",
        queries=[
            "client contracts assignment termination change of control warranties indemnity limitation liability",
            "IP ownership patents trademarks licenses founder assignment corporate structure cap table",
            "regulatory compliance litigation disputes legal blockers material contracts",
        ],
    ),
    DomainPass(
        name="Commercial Team",
        category="Commercial",
        queries=[
            "market size TAM SAM SOM competition positioning pricing customer retention churn NRR",
            "customer contracts pipeline sales motion go to market expansion upsell pricing power",
            "market research competitive analysis product differentiation customer concentration",
        ],
    ),
    DomainPass(
        name="Technical Team",
        category="Technical",
        queries=[
            "architecture scalability infrastructure reliability uptime data pipeline product roadmap",
            "security SOC 2 ISO privacy data protection vulnerabilities access controls",
            "technical debt engineering velocity code quality platform dependencies",
        ],
    ),
    DomainPass(
        name="People and Governance Team",
        category="Human Resources",
        queries=[
            "founders executives resumes org chart board governance advisors employees compensation",
            "HR employee handbook payroll job titles references background checks management credibility",
            "fabricated resumes fake employees mismatched emails unusual roles people risk",
        ],
    ),
    DomainPass(
        name="Operations Team",
        category="Operations",
        queries=[
            "operating plan process controls vendor dependencies delivery operations support implementation",
            "SOP policies insurance facilities suppliers business continuity operational bottlenecks",
            "execution risk operating metrics customer support service delivery",
        ],
    ),
    DomainPass(
        name="Data Integrity Team",
        category="Data Integrity",
        queries=[
            "contradictions inconsistencies fabricated fake placeholder example template mismatch anomalies",
            "same dates repeated generic templates impossible claims data quality red flags",
            "cross document inconsistencies source reliability missing evidence unverifiable claims",
        ],
    ),
]


def is_comprehensive_request(query: str) -> bool:
    normalized = (query or "").lower()
    triggers = (
        "due diligence",
        "comprehensive",
        "full report",
        "all documents",
        "given documents",
        "data room",
        "investment memo",
        "vc review",
        "pe review",
        "complete review",
    )
    return any(trigger in normalized for trigger in triggers)


async def run_domain_pipeline(
    session_id: str, focus: str, provider: BaseProvider,
    rag: LocalRagIndex, settings: Settings,
) -> Dict[str, Any]:
    """Bounded independent workstreams with explicit coverage and failure states."""
    normalized = focus.lower()
    selected = list(DOMAIN_PASSES) if is_comprehensive_request(focus) else [
        domain for domain in DOMAIN_PASSES
        if domain.category.lower() in normalized or domain.name.lower().split()[0] in normalized
    ]
    if not selected:
        selected = [DomainPass("Requested Analysis", "General", [focus])]
    semaphore = asyncio.Semaphore(max(1, min(settings.analysis_concurrency, 7)))

    async def analyze_domain(domain):
        async with semaphore:
            queries = [f"{query} related to: {focus}" for query in domain.queries]
            documents = await asyncio.to_thread(rag.multi_query_context_documents,
                session_id, queries, top_k_per_query=8,
                max_results=settings.due_diligence_domain_top_k, per_file_limit=3)
            if not documents:
                return {"domain": domain.name, "status": "missing_evidence", "findings": [], "documents": [], "error": "No relevant evidence retrieved"}
            domain_focus = f"{domain.name}: {focus}. Identify material evidence-backed issues and explicit unanswered questions. Do not invent a finding quota."
            try:
                findings = await asyncio.wait_for(provider.analyze(documents, domain_focus), settings.provider_timeout_seconds)
                # Apply provenance checks to every provider, including custom adapters.
                findings = [provider._normalize_finding(finding, documents) for finding in findings]
                for finding in findings:
                    finding["domain_pass"] = domain.name
                    if finding["category"] == "General":
                        finding["category"] = domain.category
                return {"domain": domain.name, "status": "completed", "findings": findings, "documents": documents, "error": None}
            except (ProviderError, TimeoutError, ValueError) as exc:
                return {"domain": domain.name, "status": "error", "findings": [], "documents": documents, "error": str(exc)}

    outcomes = await asyncio.wait_for(asyncio.gather(*(analyze_domain(domain) for domain in selected)), settings.analysis_timeout_seconds)
    findings = _dedupe_findings([finding for outcome in outcomes for finding in outcome["findings"]])[:settings.due_diligence_max_findings]
    errors = [f"{outcome['domain']}: {outcome['error']}" for outcome in outcomes if outcome["error"]]
    completed = sum(outcome["status"] == "completed" for outcome in outcomes)
    status = "completed" if completed == len(outcomes) else "partial" if completed else "incomplete"
    return {
        "findings": findings,
        "documents": _dedupe_documents([document for outcome in outcomes for document in outcome["documents"]]),
        "steps": [{"action": outcome["domain"].lower().replace(" ", "_")+"_analysis", "tool_input": focus,
                   "observation": f"{outcome['status']}: {len(outcome['findings'])} verified findings"} for outcome in outcomes],
        "errors": errors, "status": status,
        "coverage": [{"domain": outcome["domain"], "status": outcome["status"], "evidence_chunks": len(outcome["documents"])} for outcome in outcomes],
    }


def _dedupe_findings(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    deduped = []
    for finding in findings:
        key = (
            str(finding.get("source_file") or finding.get("file_name") or "").lower(),
            " ".join(str(finding.get("finding") or "").lower().split())[:160],
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(finding)
    return sorted(deduped, key=_finding_sort_key)


def _dedupe_documents(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    deduped = []
    for document in documents:
        key = (
            document.get("source_path"),
            document.get("chunk_index"),
            document.get("text", "")[:80],
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(document)
    return deduped


def _finding_sort_key(finding: Dict[str, Any]) -> tuple[int, str]:
    severity = str(finding.get("severity") or "Medium").title()
    severity_rank = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}.get(severity, 4)
    return severity_rank, str(finding.get("category") or "")
