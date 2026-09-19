"""
recommendations.py

Turns the raw list of issues into a small set of prioritized,
human-readable recommendations. Kept separate from quality_checks.py
so that wording/prioritization can be iterated on without touching
detection logic.

This module is intentionally generic: it operates on the standard
issue shape (category/severity/columns/metric/explanation/
recommendation) and does not special-case any particular category -
including the newer "Potential Duplicate Rows" and "Identifier
Columns" categories. New categories are handled automatically as long
as they follow that shape, so no changes were needed here to support
them.
"""

SEVERITY_ORDER = {"Critical": 0, "Warning": 1, "Good": 2}


def get_prioritized_recommendations(issues: list, top_n: int = 5) -> list:
    """
    Return up to `top_n` recommendation strings, prioritized by
    severity (Critical first), for the most actionable issues.

    "Good" severity issues are excluded since they require no action.
    """
    actionable = [i for i in issues if i.get("severity") in ("Critical", "Warning")]
    actionable_sorted = sorted(
        actionable, key=lambda i: SEVERITY_ORDER.get(i.get("severity"), 99)
    )

    recommendations = []
    for issue in actionable_sorted[:top_n]:
        cols = ", ".join(issue.get("columns", [])) or "dataset-wide"
        recommendations.append(
            f"[{issue['severity']}] {issue['category']} ({cols}): "
            f"{issue['recommendation']}"
        )
    return recommendations


def summarize_issue_counts(issues: list) -> dict:
    """Count how many issues fall into each severity bucket."""
    counts = {"Good": 0, "Warning": 0, "Critical": 0}
    for issue in issues:
        severity = issue.get("severity", "Good")
        if severity in counts:
            counts[severity] += 1
    return counts
