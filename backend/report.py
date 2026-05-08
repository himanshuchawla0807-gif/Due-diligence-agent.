"""Markdown report formatting for due diligence responses.

The open-source backend returns structured findings from any supported LLM
provider, then renders a Markdown-first IC memo. The frontend already knows how
to render headings, tables, chart placeholders, and citation anchors, so this
module is the stable response contract.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any, Dict, List


DOMAIN_ORDER = [
    "Financial",
    "Legal",
    "Commercial",
    "Technical",
    "Security & Compliance",
    "Data Integrity",
    "Human Resources",
    "Operations",
    "Product",
    "General",
]

SEVERITY_ORDER = {
    "Critical": 0,
    "High": 1,
    "Medium": 2,
    "Low": 3,
}


def format_due_diligence_report(
    findings: List[Dict[str, Any]],
    documents: List[Dict[str, Any]],
    industry: str | None = None,
) -> str:
    company = _infer_company_name(findings, documents)
    audience = (industry or "VC").strip() or "VC"
    title = f"{company} - Comprehensive Due Diligence Report" if company else "Comprehensive Due Diligence Report"
    if not findings:
        return f"# {title}\n\nNo evidence-backed findings were produced from the uploaded files."

    ordered_findings = sorted(
        findings,
        key=lambda item: (
            SEVERITY_ORDER.get(str(item.get("severity", "Medium")).title(), 9),
            str(item.get("category", "General")),
        ),
    )
    severity_counts = Counter(_severity(item) for item in ordered_findings)
    category_counts = Counter(_category(item) for item in ordered_findings)
    top_documents = _top_documents(ordered_findings, documents)
    recommendation = _recommendation(ordered_findings)
    metrics = _extract_metrics(ordered_findings, documents)

    lines = [
        f"# {title}",
        "",
        "## Executive Summary",
        "",
        _executive_summary(ordered_findings, top_documents, recommendation, audience),
        "",
        "| Decision Area | Assessment | Evidence |",
        "| --- | --- | --- |",
        f"| Investment posture | **{recommendation}** | {_finding_citation(ordered_findings[0])} |",
        f"| Critical findings | {severity_counts.get('Critical', 0)} | {_first_citation_for_severity(ordered_findings, 'Critical')} |",
        f"| High-priority findings | {severity_counts.get('High', 0)} | {_first_citation_for_severity(ordered_findings, 'High')} |",
        f"| Cited documents | {len(top_documents)} | {_doc_citation(top_documents[0], documents) if top_documents else ''} |",
        "",
        "*Bar chart of decision area assessment*",
        "",
        "## Business Model and Product Strategy",
        "",
        _domain_narrative(ordered_findings, ["Commercial", "Product", "Operations"], top_documents),
        "",
        "## Financial Performance Overview",
        "",
    ]

    if metrics:
        lines.extend(["| Metric | Value | Source |", "| --- | ---: | --- |"])
        for metric in metrics[:12]:
            lines.append(
                f"| {_table_text(metric['metric'])} | {_table_text(metric['value'])} | {_doc_citation(metric['file_name'], documents)} |"
            )
        lines.extend(["", "*Bar chart of financial and operating metrics*", ""])
    else:
        lines.extend(
            [
                "No clean financial metric table could be extracted from the retrieved context. Treat this as a diligence gap and request primary financial statements, cohort data, and a current management model.",
                "",
            ]
        )

    financial_findings = _filter_domains(ordered_findings, ["Financial"])
    if financial_findings:
        lines.extend(["### Financial Inconsistencies and Red Flags", ""])
        lines.extend(_finding_bullets(financial_findings[:8]))
        lines.append("")

    lines.extend(["## Legal, Governance, and Compliance", ""])
    lines.append(_domain_narrative(ordered_findings, ["Legal", "Security & Compliance", "Data Integrity"], top_documents))
    legal_findings = _filter_domains(ordered_findings, ["Legal", "Security & Compliance", "Data Integrity"])
    if legal_findings:
        lines.extend(["", "| Severity | Issue | Source | Required Follow-up |", "| --- | --- | --- | --- |"])
        for finding in legal_findings[:10]:
            lines.append(
                f"| {_severity(finding)} | {_table_text(finding.get('finding'))} | {_finding_citation(finding)} | {_table_text(finding.get('recommendation') or 'Request source backup and management explanation.')} |"
            )

    lines.extend(["", "## Technical, IP, and Data Security", ""])
    lines.append(_domain_narrative(ordered_findings, ["Technical", "Product", "Security & Compliance"], top_documents))
    technical_findings = _filter_domains(ordered_findings, ["Technical", "Product", "Security & Compliance"])
    if technical_findings:
        lines.extend(["", "| Domain | Severity | Evidence-backed concern | Source |", "| --- | --- | --- | --- |"])
        for finding in technical_findings[:10]:
            lines.append(
                f"| {_category(finding)} | {_severity(finding)} | {_table_text(finding.get('finding'))} | {_finding_citation(finding)} |"
            )

    lines.extend(["", "## Risk Register", "", "| Severity | Count | Interpretation |", "| --- | ---: | --- |"])
    for severity in ["Critical", "High", "Medium", "Low"]:
        count = severity_counts.get(severity, 0)
        lines.append(f"| {severity} | {count} | {_severity_interpretation(severity, count)} |")
    lines.extend(["", "*Bar chart of risk findings by severity*", ""])

    lines.extend(["## Domain Coverage", "", "| Domain | Findings | Primary question answered |", "| --- | ---: | --- |"])
    for domain in DOMAIN_ORDER:
        count = category_counts.get(domain, 0)
        if count:
            lines.append(f"| {domain} | {count} | {_domain_question(domain)} |")
    for domain, count in sorted(category_counts.items()):
        if domain not in DOMAIN_ORDER:
            lines.append(f"| {domain} | {count} | Evidence-backed diligence issue |")
    lines.extend(["", "*Pie chart of due diligence findings by domain*", ""])

    lines.extend(["## Key Findings By Workstream", ""])
    grouped = _group_by_domain(ordered_findings)
    for domain in DOMAIN_ORDER:
        if domain in grouped:
            lines.extend(_domain_section(domain, grouped[domain]))
    for domain in sorted(set(grouped) - set(DOMAIN_ORDER)):
        lines.extend(_domain_section(domain, grouped[domain]))

    lines.extend(
        [
            "## Evidence Matrix",
            "",
            "| # | Severity | Domain | Source document | Evidence basis |",
            "| ---: | --- | --- | --- | --- |",
        ]
    )
    for index, finding in enumerate(ordered_findings[:24], start=1):
        lines.append(
            "| "
            f"{index} | {_severity(finding)} | {_category(finding)} | "
            f"{_table_text(_source_file(finding))} {_finding_citation(finding)} | "
            f"{_table_text(finding.get('evidence') or finding.get('text_snippet') or finding.get('finding'))} |"
        )
    lines.append("")

    lines.extend(["## Source Coverage", "", "| Source document | Citations |", "| --- | ---: |"])
    for document, count in Counter(_source_file(finding) for finding in ordered_findings).most_common(12):
        lines.append(f"| {_table_text(document)} | {count} |")
    lines.extend(["", "*Bar chart of top cited source documents*", ""])

    lines.extend(["## Immediate Diligence Actions", "", "| Priority | Action | Source basis |", "| --- | --- | --- |"])
    for index, finding in enumerate(ordered_findings[:12], start=1):
        lines.append(
            f"| P{min(index, 5)} | {_table_text(finding.get('recommendation') or 'Request supporting evidence and management explanation.')} | {_table_text(_source_file(finding))} {_finding_citation(finding)} |"
        )

    lines.extend(["", "## Referenced Documents", ""])
    for index, document in enumerate(top_documents[:12], start=1):
        lines.append(f"{index}. `{document}` {_doc_citation(document, documents)}")

    return "\n".join(lines).strip()


def _executive_summary(
    findings: List[Dict[str, Any]],
    top_documents: List[str],
    recommendation: str,
    audience: str,
) -> str:
    critical = sum(1 for item in findings if _severity(item) == "Critical")
    high = sum(1 for item in findings if _severity(item) == "High")
    source_text = ", ".join(f"`{name}`" for name in top_documents[:4]) or "the uploaded files"
    if critical:
        stance = "The data room contains critical red flags that should pause the process until management provides primary evidence."
    elif high:
        stance = "The data room contains high-priority diligence issues that require management follow-up before investment committee review."
    else:
        stance = "The data room has reviewable diligence issues, but the currently retrieved evidence does not show a deal-stopping item."
    return (
        f"{stance} Current recommendation for {audience} review: **{recommendation}**. "
        f"The strongest evidence comes from {source_text}. This report is grounded in {len(findings)} extracted findings "
        "and should be used as a working diligence memo, not as final legal, financial, or investment advice."
    )


def _domain_section(domain: str, findings: List[Dict[str, Any]]) -> List[str]:
    lines = [f"### {domain}", ""]
    lines.extend(_finding_bullets(findings))
    lines.append("")
    return lines


def _finding_bullets(findings: List[Dict[str, Any]]) -> List[str]:
    lines: List[str] = []
    for finding in findings:
        lines.append(f"- **{_severity(finding)} - {_plain(finding.get('finding'))}** {_finding_citation(finding)}")
        lines.append(f"  Source: `{_source_file(finding)}`")
        if finding.get("evidence"):
            lines.append(f"  Evidence: {_plain(finding.get('evidence'))}")
        if finding.get("recommendation"):
            lines.append(f"  Recommendation: {_plain(finding.get('recommendation'))}")
    return lines


def _group_by_domain(findings: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for finding in findings:
        grouped[_category(finding)].append(finding)
    return grouped


def _top_documents(findings: List[Dict[str, Any]], documents: List[Dict[str, Any]]) -> List[str]:
    counts = Counter(_source_file(finding) for finding in findings if _source_file(finding) != "Source Document")
    if counts:
        return [name for name, _ in counts.most_common()]
    return [str(document.get("file_name") or "Source Document") for document in documents]


def _filter_domains(findings: List[Dict[str, Any]], domains: List[str]) -> List[Dict[str, Any]]:
    domain_set = set(domains)
    return [finding for finding in findings if _category(finding) in domain_set]


def _domain_narrative(findings: List[Dict[str, Any]], domains: List[str], top_documents: List[str]) -> str:
    scoped = _filter_domains(findings, domains)
    if not scoped:
        return (
            "The retrieved context did not produce enough evidence-backed findings for this workstream. "
            "Treat this as a data-room coverage gap rather than a clean diligence result."
        )

    critical_or_high = [item for item in scoped if _severity(item) in {"Critical", "High"}]
    lead = critical_or_high[0] if critical_or_high else scoped[0]
    support = ", ".join(f"`{name}`" for name in top_documents[:3]) or "the retrieved files"
    return (
        f"The strongest workstream signal is **{_plain(lead.get('finding'))}** {_finding_citation(lead)}. "
        f"The relevant evidence is concentrated in {support}. "
        "The sections below separate source-backed facts from diligence interpretation and list the follow-up required before an investment decision."
    )


def _recommendation(findings: List[Dict[str, Any]]) -> str:
    critical = sum(1 for item in findings if _severity(item) == "Critical")
    high = sum(1 for item in findings if _severity(item) == "High")
    if critical >= 2:
        return "NO GO until critical evidence is remediated"
    if critical == 1 or high >= 4:
        return "PROCEED WITH CONDITIONS"
    if high:
        return "PROCEED TO CONFIRMATORY DILIGENCE"
    return "CONTINUE DILIGENCE"


def _extract_metrics(findings: List[Dict[str, Any]], documents: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    metric_names = [
        "Revenue",
        "ARR",
        "MRR",
        "Gross Profit",
        "Gross Margin",
        "EBITDA",
        "Operating Income",
        "Net Income",
        "Burn Rate",
        "Runway",
        "Cash Balance",
        "Accounts Receivable",
        "Intangible Assets",
        "Customer Count",
        "NRR",
        "Churn",
    ]
    seen = set()
    metrics: List[Dict[str, str]] = []
    texts = []
    for finding in findings:
        joined = " ".join(
            _plain(finding.get(key))
            for key in ("finding", "evidence", "text_snippet")
            if finding.get(key)
        )
        texts.append((joined, _source_file(finding)))
    for document in documents:
        texts.append((_plain(document.get("text"))[:2500], str(document.get("file_name") or "Source Document")))

    for text, file_name in texts:
        if not text:
            continue
        for name in metric_names:
            pattern = rf"\b{name}\b[^$\d%-]{{0,40}}(\$?\(?-?\d[\d,]*(?:\.\d+)?\)?\s?(?:M|B|K|m|b|k|%|months|x)?)"
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                value = match.group(1).strip()
                key = (name.lower(), value.lower(), file_name.lower())
                if key in seen:
                    continue
                seen.add(key)
                metrics.append({"metric": name, "value": value, "file_name": file_name})
                if len(metrics) >= 16:
                    return metrics
    return metrics


def _infer_company_name(findings: List[Dict[str, Any]], documents: List[Dict[str, Any]]) -> str:
    haystack = " ".join(
        [_plain(item.get("finding")) + " " + _plain(item.get("evidence")) for item in findings[:20]]
        + [_plain(document.get("text"))[:1000] for document in documents[:20]]
    )
    patterns = [
        r"\b([A-Z][A-Za-z0-9&.,' -]{2,80}\s(?:Inc\.|LLC|Ltd\.|Limited|Corp\.|Corporation|Technologies|Solutions|Enterprises))\b",
        r"\b(?:company|issuer|target)\s+(?:named|called|is)\s+([A-Z][A-Za-z0-9&.,' -]{2,80})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, haystack)
        if match:
            name = re.sub(r"\s+", " ", match.group(1)).strip(" .,-")
            if 3 <= len(name) <= 90 and not name.lower().startswith(("source", "document", "table")):
                return name
    return ""


def _category(finding: Dict[str, Any]) -> str:
    return str(finding.get("category") or "General").strip() or "General"


def _severity(finding: Dict[str, Any]) -> str:
    value = str(finding.get("severity") or "Medium").strip().title()
    return value if value in SEVERITY_ORDER else "Medium"


def _source_file(finding: Dict[str, Any]) -> str:
    return str(finding.get("source_file") or finding.get("file_name") or "Source Document")


def _finding_citation(finding: Dict[str, Any]) -> str:
    citation_id = finding.get("_citation_id")
    return f"<c>{citation_id}</c>" if citation_id else ""


def _doc_citation(file_name: str, documents: List[Dict[str, Any]]) -> str:
    for document in documents:
        if document.get("file_name") == file_name and document.get("_citation_id"):
            return f"<c>{document['_citation_id']}</c>"
    return ""


def _first_citation_for_severity(findings: List[Dict[str, Any]], severity: str) -> str:
    for finding in findings:
        if _severity(finding) == severity:
            return _finding_citation(finding)
    return ""


def _severity_interpretation(severity: str, count: int) -> str:
    if count == 0:
        return "No findings at this severity in retrieved evidence"
    if severity == "Critical":
        return "Potential deal blocker or fraud indicator"
    if severity == "High":
        return "Requires management response before IC"
    if severity == "Medium":
        return "Track in diligence request list"
    return "Monitor or resolve in confirmatory diligence"


def _domain_question(domain: str) -> str:
    questions = {
        "Financial": "Are the numbers internally consistent and investment-grade?",
        "Legal": "Do contracts, structure, or obligations create closing risk?",
        "Commercial": "Do customer, market, and pricing signals support the story?",
        "Technical": "Can the product and architecture support the plan?",
        "Security & Compliance": "Can the company satisfy enterprise and regulatory expectations?",
        "Data Integrity": "Can the data room be trusted?",
        "Human Resources": "Are team and personnel records credible?",
        "Operations": "Can the company execute repeatably?",
        "Product": "Does the roadmap match product and market evidence?",
        "General": "What other evidence-backed issues require follow-up?",
    }
    return questions.get(domain, "Evidence-backed diligence issue")


def _plain(value: Any) -> str:
    return str(value or "").replace("\n", " ").strip()


def _table_text(value: Any) -> str:
    text = _plain(value)
    text = text.replace("|", "\\|")
    if len(text) > 180:
        text = text[:177].rstrip() + "..."
    return text
