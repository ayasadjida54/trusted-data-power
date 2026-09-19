"""
comparison.py

Compares two analysis results - typically the two most recent runs for
the same dataset slot - and produces a structured diff: how the overall
score and each dimension changed, which issues are new/resolved/
worsened/improved, and a short plain-language summary of what changed
and why.

This is comparison, not monitoring: it runs when a user (or a caller)
asks to compare two specific runs. Automated, unprompted "your score
dropped" alerts triggered by a schedule are Phase 7 (monitoring) - this
module's diff logic is exactly what that will build on, but Phase 5
itself only wires it into an on-demand comparison endpoint.

Nothing here re-runs analysis - both inputs are the already-computed
results (or their JSON-serialized equivalents) of two separate
analyze_dataframe() calls, so this module never touches a DataFrame.
"""

from engine.recommendations import SEVERITY_ORDER

# An issue is treated as "the same finding" across two runs if it has
# the same category AND the same set of columns - e.g. "Categorical
# Consistency" on "category" in both runs is one finding whose severity
# may have changed, not two separate findings. Dataset-wide issues
# (duplicate rows, with no columns) match on category alone.


def _issue_key(issue: dict) -> tuple:
    columns = tuple(sorted(issue.get("columns") or []))
    return (issue.get("category"), columns)


def _index_issues(issues: list) -> dict:
    return {_issue_key(issue): issue for issue in issues}


def _severity_rank(severity: str) -> int:
    # Lower rank = worse, matching SEVERITY_ORDER (Critical=0 is worst).
    return SEVERITY_ORDER.get(severity, 99)


def compare_analysis_results(previous: dict, current: dict) -> dict:
    """
    Compare two analysis results. Each must be a dict containing (at
    minimum) the keys "score", "score_label", "dimension_scores", and
    "issues" - exactly what analyze_dataframe() returns, and exactly
    what's stored per AnalysisRun, so callers can pass either directly.

    `previous` is the earlier run, `current` is the later one - deltas
    are current-minus-previous, so a positive score_delta is an
    improvement.

    Returns:
        {
            "score_delta": float,               # current.score - previous.score
            "previous_score": float,
            "current_score": float,
            "previous_label": str,
            "current_label": str,
            "dimension_deltas": {dimension: float, ...},
            "new_issues": [...],                # present now, weren't before
            "resolved_issues": [...],           # were present, aren't now
            "worsened_issues": [...],           # present in both, got worse
            "improved_issues": [...],           # present in both, got better
            "summary": [str, ...],              # plain-language highlights
        }
    """
    score_delta = round(current["score"] - previous["score"], 1)

    dimension_deltas = {
        dimension: round(current["dimension_scores"][dimension] - previous_score, 1)
        for dimension, previous_score in previous["dimension_scores"].items()
    }

    previous_by_key = _index_issues(previous["issues"])
    current_by_key = _index_issues(current["issues"])

    new_issues = [
        issue
        for key, issue in current_by_key.items()
        if key not in previous_by_key and issue.get("severity") != "Good"
    ]
    resolved_issues = [
        issue
        for key, issue in previous_by_key.items()
        if key not in current_by_key and issue.get("severity") != "Good"
    ]

    worsened_issues = []
    improved_issues = []
    for key, current_issue in current_by_key.items():
        previous_issue = previous_by_key.get(key)
        if previous_issue is None:
            continue
        rank_change = _severity_rank(current_issue.get("severity")) - _severity_rank(
            previous_issue.get("severity")
        )
        # Lower rank = worse severity (Critical=0 is worst), so a
        # DECREASE in rank means the issue got worse.
        if rank_change < 0:
            worsened_issues.append(current_issue)
        elif rank_change > 0:
            improved_issues.append(current_issue)

    summary = _build_summary(
        score_delta=score_delta,
        dimension_deltas=dimension_deltas,
        new_issues=new_issues,
        resolved_issues=resolved_issues,
        worsened_issues=worsened_issues,
        improved_issues=improved_issues,
    )

    return {
        "score_delta": score_delta,
        "previous_score": previous["score"],
        "current_score": current["score"],
        "previous_label": previous["score_label"],
        "current_label": current["score_label"],
        "dimension_deltas": dimension_deltas,
        "new_issues": new_issues,
        "resolved_issues": resolved_issues,
        "worsened_issues": worsened_issues,
        "improved_issues": improved_issues,
        "summary": summary,
    }


def _build_summary(
    score_delta: float,
    dimension_deltas: dict,
    new_issues: list,
    resolved_issues: list,
    worsened_issues: list,
    improved_issues: list,
) -> list:
    """
    A handful of plain-language sentences highlighting what changed -
    template-based over the already-computed diff above, in the same
    spirit as scoring.explain_reliability_score: every sentence traces
    back to a real number or a real issue, nothing inferred.
    """
    sentences = []

    if score_delta > 0:
        sentences.append(f"The reliability score improved by {score_delta} points.")
    elif score_delta < 0:
        sentences.append(f"The reliability score dropped by {abs(score_delta)} points.")
    else:
        sentences.append("The reliability score is unchanged.")

    biggest_dimension_drop = min(dimension_deltas.items(), key=lambda item: item[1], default=None)
    if biggest_dimension_drop and biggest_dimension_drop[1] < 0:
        name, delta = biggest_dimension_drop
        sentences.append(f"{name} fell the most, down {abs(delta)} points.")

    biggest_dimension_gain = max(dimension_deltas.items(), key=lambda item: item[1], default=None)
    if biggest_dimension_gain and biggest_dimension_gain[1] > 0:
        name, delta = biggest_dimension_gain
        sentences.append(f"{name} improved the most, up {delta} points.")

    if new_issues:
        categories = ", ".join(sorted({issue["category"] for issue in new_issues}))
        sentences.append(f"{len(new_issues)} new issue(s) appeared: {categories}.")

    if resolved_issues:
        categories = ", ".join(sorted({issue["category"] for issue in resolved_issues}))
        sentences.append(f"{len(resolved_issues)} issue(s) were resolved: {categories}.")

    if worsened_issues:
        sentences.append(f"{len(worsened_issues)} existing issue(s) got worse.")

    if improved_issues:
        sentences.append(f"{len(improved_issues)} existing issue(s) improved.")

    return sentences
