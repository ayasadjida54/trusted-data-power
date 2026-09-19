"""
cleaning.py

Automated, explainable data cleaning - the real version of what the
original prototype simulated as a one-click "Execute Pipeline" going
from DataScore 55 to 98. This module actually transforms the data and
returns a genuine before/after, computed by re-running analyze_dataframe()
on the result - nothing here is a scripted demo number.

Scope is deliberately narrow, on purpose: this only fixes issues that
are objectively safe and lose no information -

    - Exact duplicate rows (drop_duplicates)
    - Leading/trailing whitespace in text columns (str.strip)
    - Inconsistent capitalization of the same category
      (standardize to the majority raw variant - see _text_normalization.py)

It deliberately does NOT touch:

    - Missing values (impute vs. drop is a judgment call about the
      data's meaning, not a formatting fix)
    - Outliers (a "potential outlier" may be a genuine extreme value -
      see quality_checks.py's own caution about this)
    - Constant columns (removing a column is a structural decision,
      not a cleanup)
    - Potential (normalized) duplicate rows (these require human
      judgment to confirm they're not coincidental matches - see
      check_potential_duplicate_rows's own docstring)

This split mirrors the product's larger explainability principle: an
automatic action is only automatic if a reasonable person would always
make the same call given the same facts. Everything else stays a
recommendation for a human to decide on, not a silent transformation.
"""

import pandas as pd

from ._text_normalization import standardize_capitalization

CLEANABLE_CATEGORIES = {"Exact Duplicate Rows", "Categorical Consistency"}


def clean_dataframe(df: pd.DataFrame, issues: list) -> tuple:
    """
    Apply automatic fixes to `df` for the safe-to-clean issue
    categories found in `issues` (the output of run_all_checks - only
    issues that are ALREADY FLAGGED get acted on; this never
    re-detects anything on its own, so cleaning and detection can't
    disagree about what needed fixing).

    Returns (cleaned_df, actions) where `actions` is a list of
    plain-language sentences describing exactly what changed - same
    "no black box" discipline as scoring.explain_reliability_score.
    """
    cleaned = df.copy()
    actions: list[str] = []

    _clean_exact_duplicates(cleaned, issues, actions)
    _clean_categorical_consistency(cleaned, issues, actions)

    if not actions:
        actions.append(
            "No automatic fixes were needed - nothing found matched the "
            "safe-to-clean categories (exact duplicates, whitespace, "
            "capitalization)."
        )

    return cleaned, actions


def _clean_exact_duplicates(df: pd.DataFrame, issues: list, actions: list) -> None:
    duplicate_issue = next(
        (i for i in issues if i.get("category") == "Exact Duplicate Rows"), None
    )
    if duplicate_issue is None or duplicate_issue.get("severity") == "Good":
        return

    before = len(df)
    df.drop_duplicates(keep="first", inplace=True)
    df.reset_index(drop=True, inplace=True)
    removed = before - len(df)
    if removed > 0:
        actions.append(
            f"Removed {removed} exact duplicate row(s), keeping the first "
            "occurrence of each."
        )


def _clean_categorical_consistency(df: pd.DataFrame, issues: list, actions: list) -> None:
    flagged_columns = sorted(
        {
            column
            for issue in issues
            if issue.get("category") == "Categorical Consistency"
            and issue.get("severity") != "Good"
            for column in (issue.get("columns") or [])
        }
    )

    for column in flagged_columns:
        if column not in df.columns:
            continue

        series = df[column]
        non_null_mask = series.notna()
        if not non_null_mask.any():
            continue

        original = series[non_null_mask].astype(str)
        stripped = original.str.strip()
        n_whitespace = int((original != stripped).sum())

        standardized = standardize_capitalization(stripped)
        n_recapitalized = int((stripped != standardized).sum())

        df.loc[non_null_mask, column] = standardized

        if n_whitespace:
            actions.append(
                f"Trimmed whitespace in '{column}' ({n_whitespace} value(s))."
            )
        if n_recapitalized:
            actions.append(
                f"Standardized capitalization in '{column}' "
                f"({n_recapitalized} value(s))."
            )
