"""
engine

The Trusted Data Power analysis engine: pure Python, no web framework,
no UI code. Given a pandas DataFrame, it produces a full data-quality
analysis - profile, issues, reliability score, and recommendations.

The four analysis modules (profiling.py, quality_checks.py, scoring.py,
recommendations.py) each handle one stage of the pipeline. The only
addition here is `analyze_dataframe()`, a single entry point that glues
them together into one full analysis, so any caller (a FastAPI route,
a test, a script) can get a full result in one call.
"""

from .profiling import build_dataset_profile, get_column_dtypes
from .quality_checks import run_all_checks
from .scoring import (
    compute_reliability_score,
    compute_column_reliability_scores,
    explain_reliability_score,
    score_label,
    DIMENSION_EXPLANATIONS,
)
from .recommendations import get_prioritized_recommendations, summarize_issue_counts
from .comparison import compare_analysis_results
from .cleaning import clean_dataframe

__all__ = [
    "analyze_dataframe",
    "build_dataset_profile",
    "get_column_dtypes",
    "run_all_checks",
    "compute_reliability_score",
    "compute_column_reliability_scores",
    "explain_reliability_score",
    "score_label",
    "DIMENSION_EXPLANATIONS",
    "get_prioritized_recommendations",
    "summarize_issue_counts",
    "compare_analysis_results",
    "clean_dataframe",
]


def analyze_dataframe(df, top_n_recommendations: int = 5) -> dict:
    """
    Run the full Trusted Data Power analysis pipeline on a DataFrame.

    This is the one function a caller (API route, script, test) needs -
    it performs the same sequence app.py currently does inline:
    profile -> checks -> score -> recommendations.

    Raises ValueError if `df` is empty or has no columns, matching the
    validation app.py already performs before analysis.

    Returns a single dict:
        {
            "profile": {...},                  # from build_dataset_profile
            "column_dtypes": DataFrame,         # from get_column_dtypes
            "issues": [...],                    # from run_all_checks
            "numeric_stats": DataFrame,         # from run_all_checks
            "issue_counts": {...},              # from summarize_issue_counts
            "recommendations": [...],           # from get_prioritized_recommendations
            "score": float,                     # from compute_reliability_score
            "score_label": str,                 # from score_label
            "dimension_scores": {...},
            "dimension_weights": {...},
            "score_explanation": [...],         # from explain_reliability_score
            "column_scores": {...},             # from compute_column_reliability_scores
        }
    """
    if df is None or df.empty or df.shape[1] == 0:
        raise ValueError("The dataset does not contain any readable tabular data.")

    profile = build_dataset_profile(df)
    column_dtypes = get_column_dtypes(df)

    check_results = run_all_checks(df)
    issues = check_results["issues"]
    numeric_stats = check_results["numeric_stats"]

    issue_counts = summarize_issue_counts(issues)
    recommendations = get_prioritized_recommendations(issues, top_n=top_n_recommendations)

    score_result = compute_reliability_score(profile, issues)
    score_explanation = explain_reliability_score(
        score_result["dimension_scores"], score_result["dimension_weights"], issues
    )
    column_scores = compute_column_reliability_scores(profile, issues)

    return {
        "profile": profile,
        "column_dtypes": column_dtypes,
        "issues": issues,
        "numeric_stats": numeric_stats,
        "issue_counts": issue_counts,
        "recommendations": recommendations,
        "score": score_result["score"],
        "score_label": score_label(score_result["score"]),
        "dimension_scores": score_result["dimension_scores"],
        "dimension_weights": score_result["dimension_weights"],
        "score_explanation": score_explanation,
        "column_scores": column_scores,
    }
