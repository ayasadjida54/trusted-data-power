"""
quality_checks.py

Each function below performs ONE type of data-quality check and returns
a list of "issue" dicts with a consistent shape:

    {
        "category": str,        # e.g. "Missing Values"
        "severity": str,        # "Good" | "Warning" | "Critical"
        "columns": list[str],   # affected column(s)
        "metric": str,          # short, quantitative human-readable metric
        "explanation": str,     # what was found and why it matters
        "recommendation": str,  # what the user might do about it
    }

Nothing here modifies the user's data. Nothing here claims the data is
"correct" or "true" - only that certain measurable characteristics were
observed.

--------------------------------------------------------------------
CONFIGURATION - all thresholds live here so they're easy to tune.
--------------------------------------------------------------------
"""

import re
import numpy as np
import pandas as pd

from ._text_normalization import standardize_capitalization

# --- Missing values -------------------------------------------------
MISSING_WARNING_THRESHOLD = 5.0     # % missing in a column -> Warning
MISSING_CRITICAL_THRESHOLD = 30.0   # % missing in a column -> Critical

# --- Exact / potential duplicate rows -------------------------------
DUPLICATE_WARNING_THRESHOLD = 1.0     # % exact duplicate rows -> Warning
DUPLICATE_CRITICAL_THRESHOLD = 10.0   # % exact duplicate rows -> Critical
# Potential duplicates (found only after normalizing text) are inherently
# uncertain - normalization can create legitimate coincidental matches -
# so they are capped at "Warning" and never escalate to "Critical".

# --- Numerical outliers (IQR method) --------------------------------
# Outliers are observations that warrant review, not confirmed errors,
# so their severity is capped at "Warning" (see check_numerical_analysis).
OUTLIER_REPORT_THRESHOLD = 0  # any outlier count > this is reported

# --- Identifier-column detection (for numerical analysis exclusion) --
# Conservative on purpose: requires a name signal (id / identifier /
# uuid / guid, as a separate token or CamelCase suffix) AND integer-like
# values. Uniqueness is reported for context but is NOT a required gate,
# since real identifier columns (e.g. a foreign key "customer_id") can
# legitimately repeat across rows.
ID_NAME_TOKEN_PATTERN = re.compile(
    r'(^|[_\-\s])(id|identifier|uuid|guid|uid)($|[_\-\s])', re.IGNORECASE
)
ID_CAMELCASE_SUFFIX_PATTERN = re.compile(r'(?<=[a-z0-9])(Id|ID)$')
ID_CAMELCASE_PREFIX_PATTERN = re.compile(r'^(Id|ID)(?=[A-Z])')
ID_HIGH_UNIQUENESS_NOTE_THRESHOLD = 0.95  # informational only, not a gate

# --- Categorical consistency (whitespace / capitalization) ----------
# Severity scales with the proportion of *values* affected in a column,
# not just the raw count, so a couple of stray values in a huge dataset
# don't read the same as a systemic formatting problem.
CONSISTENCY_CRITICAL_PROPORTION = 0.25  # >=25% of values affected -> Critical

# --- Constant columns -------------------------------------------------
# A single constant column is not automatically a problem (it may be
# intentional - a filter column, a schema placeholder, etc.), so it
# defaults to Warning. It only escalates to Critical when a large share
# of the *whole dataset's columns* are constant, which is a measurable
# sign that something went wrong with the export/extraction itself.
CONSTANT_COLUMNS_CRITICAL_DATASET_PROPORTION = 0.40

# --- Suspicious / numeric-looking text values ------------------------
# A column is flagged when this fraction (or more) of its non-null text
# values look numeric once common formatting (currency symbols, thousands
# separators, percent signs) is stripped away.
SUSPICIOUS_TYPE_THRESHOLD = 0.8


def _issue(category, severity, columns, metric, explanation, recommendation,
           affected_proportion=0.0):
    """
    Build a structured issue dict.

    `affected_proportion` is an explicit numeric field (0-1) giving the
    fraction of the relevant scope (rows/values/columns, depending on
    the check) that this issue affects. It is computed here from the
    same numbers each check already calculates internally - never
    derived by parsing `metric`, which remains a presentation-only,
    human-readable string. Downstream consumers (e.g. scoring.py)
    should read this field directly rather than parsing `metric`.
    """
    return {
        "category": category,
        "severity": severity,
        "columns": columns if isinstance(columns, list) else [columns],
        "metric": metric,
        "explanation": explanation,
        "recommendation": recommendation,
        "affected_proportion": max(0.0, min(1.0, affected_proportion)),
    }


# =====================================================================
# 1. Missing values
# =====================================================================

def check_missing_values(df: pd.DataFrame) -> list:
    """Detect missing values per column, with count and percentage."""
    issues = []
    n_rows = len(df)
    if n_rows == 0:
        return issues

    for col in df.columns:
        n_missing = int(df[col].isna().sum())
        if n_missing == 0:
            continue
        pct_missing = round((n_missing / n_rows) * 100, 2)

        if pct_missing >= MISSING_CRITICAL_THRESHOLD:
            severity = "Critical"
        elif pct_missing >= MISSING_WARNING_THRESHOLD:
            severity = "Warning"
        else:
            severity = "Good"

        issues.append(
            _issue(
                category="Missing Values",
                severity=severity,
                columns=col,
                metric=f"{n_missing} of {n_rows} rows ({pct_missing}%) are missing",
                explanation=(
                    f"Column '{col}' has {n_missing} missing value(s), "
                    f"which is {pct_missing}% of all rows."
                ),
                recommendation=(
                    "Consider whether this column should be imputed, "
                    "dropped, or investigated for a data-collection issue."
                    if severity != "Good"
                    else "Missingness is low; likely not a concern on its own."
                ),
                affected_proportion=n_missing / n_rows,
            )
        )
    return issues


# =====================================================================
# 2. Duplicate rows - exact AND potential (normalized)
# =====================================================================

def check_duplicate_rows(df: pd.DataFrame) -> list:
    """
    Count EXACT duplicate rows (identical values, no normalization) and
    report their percentage. This is intentionally strict - a value that
    differs by even a trailing space or a capital letter is NOT counted
    here. See check_potential_duplicate_rows for that softer signal.
    """
    n_rows = len(df)
    if n_rows == 0:
        return []

    n_duplicates = int(df.duplicated().sum())
    pct_duplicates = round((n_duplicates / n_rows) * 100, 2)

    if n_duplicates == 0:
        severity = "Good"
    elif pct_duplicates >= DUPLICATE_CRITICAL_THRESHOLD:
        severity = "Critical"
    elif pct_duplicates >= DUPLICATE_WARNING_THRESHOLD:
        severity = "Warning"
    else:
        severity = "Good"

    return [
        _issue(
            category="Exact Duplicate Rows",
            severity=severity,
            columns=[],
            metric=f"{n_duplicates} of {n_rows} rows ({pct_duplicates}%) are exact duplicates",
            explanation=(
                f"{n_duplicates} row(s) are byte-for-byte identical to an "
                f"earlier row, representing {pct_duplicates}% of the dataset."
                if n_duplicates
                else "No exact duplicate rows were found."
            ),
            recommendation=(
                "Review whether duplicates are legitimate (e.g. repeated "
                "transactions) or should be removed before analysis."
                if n_duplicates
                else "No action needed."
            ),
            affected_proportion=n_duplicates / n_rows,
        )
    ]


def check_potential_duplicate_rows(df: pd.DataFrame) -> list:
    """
    Detect rows that become duplicates of an earlier row ONLY after a
    conservative, non-destructive normalization: leading/trailing
    whitespace stripped and text lowercased. Numerical columns are left
    untouched. The original DataFrame is never modified - all work
    happens on a copy.

    These are explicitly labeled "Potential" (never "exact") because
    normalization can also create legitimate coincidental matches (e.g.
    two different people both named "Sam"), so they always require
    manual review and are never escalated past "Warning".
    """
    n_rows = len(df)
    if n_rows == 0:
        return []

    normalized = df.copy()
    text_cols = df.select_dtypes(exclude="number").columns
    for col in text_cols:
        normalized[col] = df[col].apply(
            lambda v: v.strip().lower() if isinstance(v, str) else v
        )

    exact_dup_mask = df.duplicated(keep="first")
    normalized_dup_mask = normalized.duplicated(keep="first")
    # Only count rows that are duplicates AFTER normalization but were
    # NOT already counted as exact duplicates, to avoid double-reporting
    # the same rows in two different categories.
    potential_only_mask = normalized_dup_mask & ~exact_dup_mask
    n_potential = int(potential_only_mask.sum())
    pct_potential = round((n_potential / n_rows) * 100, 2)

    severity = "Warning" if n_potential > 0 else "Good"

    return [
        _issue(
            category="Potential Duplicate Rows",
            severity=severity,
            columns=[],
            metric=(
                f"{n_potential} of {n_rows} rows ({pct_potential}%) match another "
                "row only after normalizing whitespace/capitalization"
            ),
            explanation=(
                f"{n_potential} row(s), beyond the exact duplicates already "
                "reported, match an earlier row once text is trimmed and "
                "lowercased. This does NOT confirm they are duplicate "
                "records - normalization can also produce coincidental "
                "matches between genuinely different rows."
                if n_potential
                else "No additional rows were found to match after normalizing text formatting."
            ),
            recommendation=(
                "Review these rows manually. If they represent the same "
                "record entered with inconsistent formatting, consider "
                "standardizing the text before deduplicating. Do not "
                "delete automatically."
                if n_potential
                else "No action needed."
            ),
            affected_proportion=n_potential / n_rows,
        )
    ]


# =====================================================================
# 3. Data types / suspicious numeric-looking text
# =====================================================================

def _looks_numeric_after_cleaning(value: str) -> bool:
    """
    Return True if `value`, after stripping common numeric formatting
    (currency symbols, thousands separators, a trailing percent sign,
    surrounding whitespace), is a plain number.

    This intentionally does NOT match things like "42 years" or
    "unknown" - those still contain letters/words after cleaning and
    correctly fail the check.
    """
    v = value.strip()
    if v == "":
        return False
    v = re.sub(r'^[\$€£]', '', v)
    v = v.replace(',', '')
    v = v.rstrip('%').strip()
    return bool(re.match(r'^-?\d+(\.\d+)?$', v))


def check_data_types(df: pd.DataFrame) -> list:
    """
    Display detected dtypes and flag columns whose type looks suspicious -
    e.g. a column typed as text but where most values actually look
    numeric once common formatting (currency symbols, thousands
    separators, percent signs) is stripped away.

    Uses pandas' dtype-kind classification (is_string_dtype) rather than
    a hard `dtype == object` check, since pandas 2.x/3.x can represent
    text columns as classic numpy `object` dtype OR the newer pandas
    `StringDtype` depending on version/settings - relying only on
    `object` silently misses text columns on newer pandas versions.
    """
    issues = []
    for col in df.columns:
        dtype = df[col].dtype

        if pd.api.types.is_string_dtype(dtype) or dtype == object:
            non_null = df[col].dropna().astype(str)
            n_total = len(non_null)
            if n_total == 0:
                continue
            numeric_like = non_null.map(_looks_numeric_after_cleaning)
            n_numeric_like = int(numeric_like.sum())
            frac_numeric_like = n_numeric_like / n_total

            if frac_numeric_like >= SUSPICIOUS_TYPE_THRESHOLD:
                pct = round(frac_numeric_like * 100, 1)
                issues.append(
                    _issue(
                        category="Data Types",
                        severity="Warning",
                        columns=col,
                        metric=(
                            f"{n_numeric_like} of {n_total} values ({pct}%) look "
                            "numeric despite being stored as text"
                        ),
                        explanation=(
                            f"Column '{col}' is stored as text, but "
                            f"{pct}% of its values look like numbers once "
                            "common formatting (currency symbols, thousands "
                            "separators, percent signs) is accounted for. "
                            "This can happen due to stray characters or "
                            "mixed entries."
                        ),
                        recommendation=(
                            "Consider cleaning and converting this column to a "
                            "numeric type if it is meant to represent numbers."
                        ),
                        affected_proportion=frac_numeric_like,
                    )
                )
            else:
                issues.append(
                    _issue(
                        category="Data Types",
                        severity="Good",
                        columns=col,
                        metric=str(dtype),
                        explanation=f"Column '{col}' is detected as type '{dtype}'.",
                        recommendation="No action needed.",
                    )
                )
        else:
            issues.append(
                _issue(
                    category="Data Types",
                    severity="Good",
                    columns=col,
                    metric=str(dtype),
                    explanation=f"Column '{col}' is detected as type '{dtype}'.",
                    recommendation="No action needed.",
                )
            )
    return issues


# =====================================================================
# 4. Constant columns
# =====================================================================

def check_constant_columns(df: pd.DataFrame) -> list:
    """
    Detect columns that contain only one unique (non-null) value.

    Severity defaults to "Warning" - a constant column is not
    automatically a data-quality problem; it may be intentional (a
    filter value, a schema placeholder, a single-category export).
    It only escalates to "Critical" when a large share of ALL columns
    in the dataset are constant, which is a measurable, dataset-wide
    signal that something likely went wrong upstream (e.g. an overly
    filtered export), rather than a judgment call about one column.
    """
    n_total_cols = df.shape[1]
    constant_cols = [
        col for col in df.columns if df[col].nunique(dropna=True) == 1
    ]
    n_constant = len(constant_cols)
    dataset_proportion_constant = (
        n_constant / n_total_cols if n_total_cols else 0.0
    )
    escalate = dataset_proportion_constant >= CONSTANT_COLUMNS_CRITICAL_DATASET_PROPORTION

    issues = []
    for col in constant_cols:
        n_non_null = int(df[col].notna().sum())
        severity = "Critical" if escalate else "Warning"
        issues.append(
            _issue(
                category="Constant Columns",
                severity=severity,
                columns=col,
                metric=f"1 unique value across all {n_non_null} non-missing row(s)",
                explanation=(
                    f"Column '{col}' contains only a single unique value "
                    "across all non-missing rows."
                    + (
                        f" This is one of {n_constant} of {n_total_cols} columns "
                        f"({round(dataset_proportion_constant * 100, 1)}%) that are "
                        "constant, which is a large enough share of the dataset "
                        "to suggest a broader extraction or filtering issue."
                        if escalate
                        else ""
                    )
                ),
                affected_proportion=1.0,  # every value in a constant column is identical, by definition
                recommendation=(
                    "A constant column carries no information for most "
                    "analyses. Review whether it is expected (e.g. a "
                    "filter value) before deciding whether to keep it - "
                    "this tool does not recommend automatically deleting it."
                ),
            )
        )
    return issues


# =====================================================================
# 5. Identifier-column detection (used by numerical analysis)
# =====================================================================

def _column_name_looks_like_identifier(col_name) -> bool:
    """Conservative name-based signal for likely ID/identifier columns."""
    name = str(col_name).strip()
    lowered = name.lower()
    if ID_NAME_TOKEN_PATTERN.search(lowered):
        return True
    if ID_CAMELCASE_SUFFIX_PATTERN.search(name):
        return True
    if ID_CAMELCASE_PREFIX_PATTERN.search(name):
        return True
    return False


def _is_integer_like(series: pd.Series) -> bool:
    """True if every non-null value is a whole number."""
    non_null = series.dropna()
    if non_null.empty:
        return False
    if pd.api.types.is_integer_dtype(non_null):
        return True
    if pd.api.types.is_float_dtype(non_null):
        return bool((non_null == non_null.round()).all())
    return False


def identify_identifier_columns(df: pd.DataFrame) -> list:
    """
    Conservatively identify numeric columns that are likely identifiers
    (e.g. 'id', 'customer_id', 'OrderID') rather than measurements.

    Requires BOTH a name-based signal AND integer-like values. High
    uniqueness is reported for context but is intentionally NOT a
    required condition, since real identifier columns (foreign keys)
    can legitimately repeat across rows.
    """
    identifier_cols = []
    for col in df.select_dtypes(include="number").columns:
        if _column_name_looks_like_identifier(col) and _is_integer_like(df[col]):
            identifier_cols.append(col)
    return identifier_cols


# =====================================================================
# 6. Numerical analysis (descriptive stats + IQR outliers)
# =====================================================================

def check_numerical_analysis(df: pd.DataFrame) -> tuple:
    """
    Compute descriptive statistics for numerical MEASUREMENT columns
    (identifier-like columns are excluded - see identify_identifier_columns)
    and flag potential outliers using the IQR method.

    Outliers are capped at "Warning" severity - they are observations
    that warrant review, not confirmed errors (see module docstring and
    CONFIGURATION section).

    Returns (issues, stats_df) where stats_df is a DataFrame of
    descriptive statistics suitable for display.
    """
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    identifier_cols = identify_identifier_columns(df)
    measurement_cols = [c for c in numeric_cols if c not in identifier_cols]

    issues = []
    stats_rows = []

    for col in measurement_cols:
        series = df[col].dropna()
        if series.empty:
            continue

        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        outliers = series[(series < lower_bound) | (series > upper_bound)]
        n_outliers = len(outliers)
        n_total = len(series)
        frac_outliers = n_outliers / n_total if n_total else 0

        stats_rows.append(
            {
                "column": col,
                "mean": round(series.mean(), 3),
                "std": round(series.std(), 3),
                "min": round(series.min(), 3),
                "25%": round(q1, 3),
                "median": round(series.median(), 3),
                "75%": round(q3, 3),
                "max": round(series.max(), 3),
                "potential_outliers": n_outliers,
            }
        )

        if n_outliers > OUTLIER_REPORT_THRESHOLD:
            pct = round(frac_outliers * 100, 1)
            issues.append(
                _issue(
                    category="Numerical Outliers",
                    severity="Warning",  # capped - see module docstring
                    columns=col,
                    metric=(
                        f"{n_outliers} of {n_total} values ({pct}%) fall "
                        "outside the IQR range"
                    ),
                    explanation=(
                        f"Column '{col}' has {n_outliers} value(s) outside the "
                        f"typical IQR range ({round(lower_bound, 3)} to "
                        f"{round(upper_bound, 3)}). Potential outlier - "
                        "observation requiring review, not automatically an "
                        "error. It may reflect a genuine extreme value."
                    ),
                    affected_proportion=frac_outliers,
                    recommendation=(
                        "Review these observations manually to decide whether "
                        "they are legitimate extreme values or data-entry issues."
                    ),
                )
            )

    # Informational note for columns excluded as likely identifiers, so
    # the exclusion is visible rather than silent.
    for col in identifier_cols:
        series = df[col].dropna()
        uniqueness_ratio = series.nunique() / len(series) if len(series) else 0.0
        note = (
            f" Values are highly unique ({round(uniqueness_ratio * 100, 1)}%), "
            "consistent with a primary key."
            if uniqueness_ratio >= ID_HIGH_UNIQUENESS_NOTE_THRESHOLD
            else ""
        )
        issues.append(
            _issue(
                category="Identifier Columns",
                severity="Good",
                columns=col,
                metric="excluded from numerical analysis",
                explanation=(
                    f"Column '{col}' looks like an identifier, based on its "
                    "name and integer-like values, rather than a measurement, "
                    "so it was excluded from descriptive statistics and "
                    "outlier detection." + note
                ),
                recommendation="No action needed. This is informational only.",
            )
        )

    stats_df = pd.DataFrame(stats_rows)
    return issues, stats_df


# =====================================================================
# 7. Categorical consistency (whitespace / capitalization)
# =====================================================================

def check_categorical_consistency(df: pd.DataFrame) -> list:
    """
    Look for formatting inconsistencies in categorical/text columns:
    - mixed capitalization of otherwise-identical values
    - leading/trailing whitespace differences

    Severity scales with the PROPORTION of values affected in a column
    (see CONSISTENCY_CRITICAL_PROPORTION), so a couple of stray values
    in a large dataset are not treated the same as a systemic problem.

    This never modifies the data - it only reports what it finds.
    """
    issues = []
    categorical_cols = df.select_dtypes(exclude="number").columns.tolist()

    for col in categorical_cols:
        series = df[col].dropna().astype(str)
        n_total = len(series)
        if n_total == 0:
            continue

        stripped = series.str.strip()

        # --- Whitespace ---
        whitespace_mask = series != stripped
        n_whitespace = int(whitespace_mask.sum())
        if n_whitespace > 0:
            pct_whitespace = round((n_whitespace / n_total) * 100, 1)
            severity = (
                "Critical"
                if (n_whitespace / n_total) >= CONSISTENCY_CRITICAL_PROPORTION
                else "Warning"
            )
            issues.append(
                _issue(
                    category="Categorical Consistency",
                    severity=severity,
                    columns=col,
                    metric=(
                        f"{n_whitespace} of {n_total} values ({pct_whitespace}%) "
                        "contain leading/trailing whitespace"
                    ),
                    explanation=(
                        f"Column '{col}' has {n_whitespace} value(s) with "
                        "leading or trailing whitespace, which can cause "
                        "values that look identical to be treated as different."
                    ),
                    recommendation="Consider trimming whitespace before analysis.",
                    affected_proportion=n_whitespace / n_total,
                )
            )

        # --- Capitalization ---
        # A group of values that normalize to the same lowercase form is
        # "inconsistent" if it contains more than one distinct raw variant
        # (e.g. {"Yes": 90, "yes": 10}). But not every VALUE in such a
        # group actually needs to change: the majority variant is already
        # the de-facto standard for that group, so only the value(s) that
        # differ from it require normalization. Counting every member of
        # an inconsistent group (including the 90 already-standard "Yes"
        # rows) would overstate how much data is actually affected.
        #
        # standardize_capitalization is shared with cleaning.py (see
        # _text_normalization.py) - this is deliberate, so "N values need
        # normalization" (detected here) and "N values normalized" (done
        # there) can never disagree.
        normalized = stripped.str.lower()
        standardized = standardize_capitalization(stripped)
        inconsistent_mask = stripped != standardized
        n_inconsistent_values = int(inconsistent_mask.sum())
        n_inconsistent_groups = (
            int(normalized[inconsistent_mask].nunique()) if n_inconsistent_values else 0
        )

        if n_inconsistent_values > 0:
            pct_inconsistent = round((n_inconsistent_values / n_total) * 100, 1)
            severity = (
                "Critical"
                if (n_inconsistent_values / n_total) >= CONSISTENCY_CRITICAL_PROPORTION
                else "Warning"
            )
            issues.append(
                _issue(
                    category="Categorical Consistency",
                    severity=severity,
                    columns=col,
                    metric=(
                        f"{n_inconsistent_values} of {n_total} values "
                        f"({pct_inconsistent}%) need capitalization "
                        "normalization to match the dominant form used "
                        "for their category"
                    ),
                    explanation=(
                        f"Column '{col}' has {n_inconsistent_groups} set(s) of "
                        "values that appear to represent the same category but "
                        "differ in capitalization (e.g. 'Yes' vs 'yes'). Within "
                        "each set, the most common variant is treated as the "
                        f"already-standard form; {n_inconsistent_values} "
                        "value(s) total are minority variants that don't "
                        "match it."
                    ),
                    recommendation=(
                        "Consider standardizing capitalization if these values "
                        "are meant to represent the same category."
                    ),
                    affected_proportion=n_inconsistent_values / n_total,
                )
            )

    return issues


# =====================================================================
# Runner
# =====================================================================

def run_all_checks(df: pd.DataFrame) -> dict:
    """
    Run every quality check and return a combined result dict:
        {
            "issues": [ ... all issue dicts ... ],
            "numeric_stats": DataFrame,
        }

    Nothing in this module modifies `df` - every check either reads it
    directly or works on an internal copy (see check_potential_duplicate_rows).
    """
    issues = []
    issues.extend(check_missing_values(df))
    issues.extend(check_duplicate_rows(df))
    issues.extend(check_potential_duplicate_rows(df))
    issues.extend(check_data_types(df))
    issues.extend(check_constant_columns(df))

    numeric_issues, numeric_stats = check_numerical_analysis(df)
    issues.extend(numeric_issues)

    issues.extend(check_categorical_consistency(df))

    return {
        "issues": issues,
        "numeric_stats": numeric_stats,
    }
