"""Multi-pass due diligence analysis pipeline."""

from __future__ import annotations

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
    session_id: str,
    focus: str,
    provider: BaseProvider,
    rag: LocalRagIndex,
    settings: Settings,
) -> Dict[str, Any]:
    all_findings: List[Dict[str, Any]] = []
    all_documents: List[Dict[str, Any]] = []
    steps: List[Dict[str, str]] = []
    errors: List[str] = []

    for domain in DOMAIN_PASSES:
        queries = [f"{query} related to: {focus}" for query in domain.queries]
        documents = rag.multi_query_context_documents(
            session_id,
            queries,
            top_k_per_query=8,
            max_results=settings.due_diligence_domain_top_k,
            per_file_limit=3,
        )
        if not documents:
            steps.append(
                {
                    "action": f"{domain.name.lower().replace(' ', '_')}_retrieval",
                    "tool_input": "; ".join(domain.queries),
                    "observation": "No relevant local chunks retrieved for this domain.",
                }
            )
            continue

        all_documents.extend(documents)
        domain_focus = (
            f"{domain.name} domain pass for {focus}. "
            f"Return 5 to 10 evidence-backed findings for the {domain.category} category. "
            "Prioritize material red flags, contradictions, missing support, and IC follow-up actions."
        )
        try:
            findings = await provider.analyze(documents, domain_focus)
        except ProviderError as exc:
            errors.append(f"{domain.name}: {exc}")
            steps.append(
                {
                    "action": f"{domain.name.lower().replace(' ', '_')}_analysis",
                    "tool_input": domain_focus,
                    "observation": f"Provider failed for this domain: {exc}",
                }
            )
            continue

        for finding in findings:
            if not finding.get("category") or finding.get("category") == "General":
                finding["category"] = domain.category
            finding["domain_pass"] = domain.name
        all_findings.extend(findings)
        steps.append(
            {
                "action": f"{domain.name.lower().replace(' ', '_')}_analysis",
                "tool_input": domain_focus,
                "observation": f"Retrieved {len(documents)} chunks and produced {len(findings)} findings.",
            }
        )

    deduped = _dedupe_findings(all_findings)[: settings.due_diligence_max_findings]
    if not deduped and errors:
        raise ProviderError("; ".join(errors[:3]))

    return {
        "findings": deduped,
        "documents": _dedupe_documents(all_documents),
        "steps": steps,
        "errors": errors,
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
