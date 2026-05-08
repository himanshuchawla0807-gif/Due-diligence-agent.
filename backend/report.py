"""Markdown report formatting for due diligence responses."""

from __future__ import annotations

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
    title = f"Due diligence response for {industry or 'VC'} review"
    if not findings:
        return f"## {title}\n\nNo evidence-backed findings were produced from the uploaded files."

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

    lines = [
        f"# {title}",
        "",
        "## Executive Summary",
        "",
        _executive_summary(ordered_findings, top_documents),
        "",
        "## Risk Snapshot",
        "",
        "| Severity | Count | Interpretation |",
        "| --- | ---: | --- |",
    ]
    for severity in ["Critical", "High", "Medium", "Low"]:
        count = severity_counts.get(severity, 0)
        lines.append(f"| {severity} | {count} | {_severity_interpretation(severity, count)} |")
    lines.extend(["", "*Bar chart of risk findings by severity*", ""])

    lines.extend(
        [
            "## Domain Coverage",
            "",
            "| Domain | Findings | Primary question answered |",
            "| --- | ---: | --- |",
        ]
    )
    for domain in DOMAIN_ORDER:
        count = category_counts.get(domain, 0)
        if count:
            lines.append(f"| {domain} | {count} | {_domain_question(domain)} |")
    for domain, count in sorted(category_counts.items()):
        if domain not in DOMAIN_ORDER:
            lines.append(f"| {domain} | {count} | Evidence-backed diligence issue |")
    lines.extend(["", "*Pie chart of due diligence findings by domain*", ""])

    lines.extend(["## Key Findings", ""])
    grouped = _group_by_domain(ordered_findings)
    for domain in DOMAIN_ORDER:
        if domain not in grouped:
            continue
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
    for index, finding in enumerate(ordered_findings[:20], start=1):
        lines.append(
            "| "
            f"{index} | {_severity(finding)} | {_category(finding)} | "
            f"{_source_file(finding)} | {_table_text(finding.get('evidence') or finding.get('text_snippet') or finding.get('finding'))} |"
        )
    lines.extend([""])

    lines.extend(
        [
            "## Source Coverage",
            "",
            "| Source document | Citations |",
            "| --- | ---: |",
        ]
    )
    for document, count in Counter(_source_file(finding) for finding in ordered_findings).most_common(12):
        lines.append(f"| {_table_text(document)} | {count} |")
    lines.extend(["", "*Bar chart of top cited source documents*", ""])

    lines.extend(
        [
            "## Immediate Diligence Actions",
            "",
            "| Priority | Action | Source basis |",
            "| --- | --- | --- |",
        ]
    )
    for index, finding in enumerate(ordered_findings[:12], start=1):
        lines.append(
            f"| P{min(index, 5)} | {_table_text(finding.get('recommendation') or 'Request supporting evidence and management explanation.')} | {_source_file(finding)} |"
        )

    lines.extend(["", "## Referenced Documents", ""])
    for index, document in enumerate(top_documents[:12], start=1):
        lines.append(f"{index}. `{document}`")

    return "\n".join(lines).strip()


def _executive_summary(findings: List[Dict[str, Any]], top_documents: List[str]) -> str:
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
        f"{stance} The strongest evidence comes from {source_text}. "
        f"This report is grounded in {len(findings)} extracted findings and should be used as a working diligence memo, "
        "not as final legal, financial, or investment advice."
    )


def _domain_section(domain: str, findings: List[Dict[str, Any]]) -> List[str]:
    lines = [f"### {domain}", ""]
    for finding in findings:
        lines.append(f"- **{_severity(finding)} - {_plain(finding.get('finding'))}**")
        lines.append(f"  Source: `{_source_file(finding)}`")
        if finding.get("evidence"):
            lines.append(f"  Evidence: {_plain(finding.get('evidence'))}")
        if finding.get("recommendation"):
            lines.append(f"  Recommendation: {_plain(finding.get('recommendation'))}")
    lines.append("")
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


def _category(finding: Dict[str, Any]) -> str:
    return str(finding.get("category") or "General").strip() or "General"


def _severity(finding: Dict[str, Any]) -> str:
    value = str(finding.get("severity") or "Medium").strip().title()
    return value if value in SEVERITY_ORDER else "Medium"


def _source_file(finding: Dict[str, Any]) -> str:
    return str(finding.get("source_file") or finding.get("file_name") or "Source Document")


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
