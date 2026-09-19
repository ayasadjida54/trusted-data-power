"""
scoring.py

Calculates a transparent Data Reliability Score from measurable
dataset-quality dimensions.

The score is NOT a measure of factual correctness, truth, or fitness
for a specific purpose. It summarizes measurable data-quality signals
detected by this tool.

--------------------------------------------------------------------
METHODOLOGY
--------------------------------------------------------------------
Six dimensions, each scored 0-100, are combined into one overall score:

    Completeness        25%   - are values present? (from Missing Values)
    Uniqueness           15%   - are rows non-duplicated? (exact + potential dupes)
    Type Quality         15%   - do columns look like they're stored as the
                                 right type? (from Data Types)
    Consistency          15%   - is text formatted consistently? (from
                                 Categorical Consistency)
    Numerical Quality    10%   - do numeric columns look statistically
                                 "normal"? (from Numerical Outliers)
    Structural Quality   20%   - does the table's shape look reasonable?
                                 (from Constant Columns)

WHY THESE WEIGHTS: Completeness and Structural Quality get the largest
weights because missing data and broken/constant columns most directly
limit what analyses are even possible. Uniqueness and Type Quality are
mid-weighted, common but usually fixable problems. Consistency
(formatting) is mid-weighted because it's easy to fix but still affects
grouping/joins. Numerical Quality (outliers) gets the smallest weight
on purpose: an outlier is an observation that warrants review, not a
confirmed error, so it should nudge the score rather than dominate it.

--------------------------------------------------------------------
STEP 1: PER-ISSUE FRACTION (unchanged from the previous revision)
--------------------------------------------------------------------
    fraction = SEVERITY_WEIGHT[severity] * affected_proportion
capped per tier (CONFIRMED vs REVIEW-ONLY - see below). Both severity
AND how much of the data is actually affected drive the penalty - a
Critical issue affecting 5% of a column costs far less than a Critical
issue affecting 90% of it.

`affected_proportion` is read from an explicit structured numeric
field on the issue dict (see AFFECTED PROPORTION below) - NOT parsed
from the human-readable "metric" display string.

REVIEW-ONLY vs CONFIRMED issues: numerical outliers and "potential"
(normalized) duplicate rows represent observations for human judgment
rather than confirmed problems, so they use a lower severity-weight
table AND a tighter per-issue cap than confirmed formatting/structural
issues - even a widespread outlier signal can only ever nudge its
dimension, never dominate it.

--------------------------------------------------------------------
STEP 2: COMBINING ISSUES WITHIN A DIMENSION (avoiding double-counting)
--------------------------------------------------------------------
Issues are first grouped by the column(s) they affect. Within a group,
we take the SINGLE STRONGEST fraction rather than multiplying every
issue in the group together. Different groups (different columns) are
then combined multiplicatively, since they represent independent
problems.

WHY: two checks - whitespace and capitalization - can both fire on the
SAME column, on overlapping observations (e.g. " Retail" has both a
leading space AND inconsistent capitalization relative to "retail").
Multiplying their fractions together would effectively penalize the
same underlying messy values twice. Taking the strongest signal per
column avoids this while still letting genuinely independent problems
in different columns compound (which is correct - five separately
messy columns are a bigger problem than one).

This grouping is a no-op for every category except Categorical
Consistency, since every other check already emits at most one issue
per column - so this change affects only the specific overlap it was
introduced to fix.

--------------------------------------------------------------------
STEP 3: COMBINING THE SIX DIMENSIONS INTO ONE OVERALL SCORE
--------------------------------------------------------------------
Previously this was a plain weighted ARITHMETIC mean of the dimension
SCORES:
    overall = sum(weight_i * dimension_i)
The problem: because each dimension's contribution is capped by its
own weight, a dimension-wide problem confined to ONE dimension could
never push the overall score below (100 - that dimension's weight) -
e.g. a completely destroyed Consistency dimension (15% weight) could
never push the score below 85, no matter how severe or widespread the
underlying problem was. That made severe, widespread single-dimension
problems read as "Strong" when they shouldn't.

FIX: aggregate the six dimensions' PENALTIES (100 - dimension_i, i.e.
how far each dimension falls short of a perfect 100), not their raw
scores, using a weighted power mean with exponent Q > 1:

    penalty_i  = 100 - dimension_i
    overall    = 100 - ( sum(weight_i * penalty_i ** Q) ) ** (1/Q)

with Q = 2 (see AGGREGATION_POWER below) - i.e. the weighted quadratic
mean (RMS) of the six penalties, the same "root-mean-square" idea used
whenever larger deviations should count disproportionately more than
smaller ones (e.g. RMSE vs. MAE).

WHY AGGREGATE PENALTIES RATHER THAN RAW VALUES: an earlier version of
this fix applied a NEGATIVE exponent directly to the dimension VALUES
(a "power mean of scores"). That is mathematically elegant in
isolation, but it has a sharp failure mode here: a negative-exponent
power mean is pulled toward 0 whenever ANY single component approaches
0, essentially regardless of that component's weight (as x_i -> 0,
x_i**P -> +infinity for P<0, and that one term swamps the weighted
sum no matter how small its weight is). Our per-issue fraction model
(STEP 1) can legitimately push a single dimension to near-zero when
several Critical issues stack up in it (e.g. two fully-constant
columns can crash Structural Quality to ~0.25) - that is intentional,
correct behavior for that ONE dimension. But feeding a near-zero
dimension value into a negative-power mean caused the OVERALL score to
collapse toward zero almost entirely too, blowing straight past the
"Moderate/Weak" target into "Poor" for cases that should not be Poor.
Aggregating PENALTIES with a POSITIVE exponent avoids this failure
mode entirely: penalties are bounded in [0, 100] and are never
inverted, so there is no blow-up near either end of the range - a
severely damaged low-weight dimension contributes a large, bounded
term to the sum instead of an unbounded one.

WHY THIS WORKS MATHEMATICALLY: for Q=1, this formula reduces EXACTLY
to the old weighted arithmetic mean (sum(weight_i*penalty_i) = 100 -
sum(weight_i*dimension_i)), so the whole family is a strict superset
of the previous behavior, not an unrelated replacement. By the
power-mean inequality, the weighted Q-mean of the penalties is
non-decreasing in Q for Q >= 1 - so for any Q > 1, the aggregated
penalty is >= what the old arithmetic mean would have produced,
meaning the new overall score is always <= the old one, for the exact
same underlying issues. That is the formal guarantee that this change
can only make scores MORE representative of serious problems, never
less. Concretely: for the QA example (Consistency dimension = 57,
weight 0.15, everything else = 100), the old arithmetic mean gives
93.55 (Strong); Q=2 gives 88.5 (still Strong, but closer to the
boundary, matching the "at least move toward it" spirit for a
MODERATE single-dimension shortfall); for a fully-destroyed dimension
(the constant_columns_test.csv shape - Structural Quality crushed to
near 0, weight 0.20), the old arithmetic mean bottoms out at exactly
80 (Moderate); Q=2 pushes it to about 55 (Weak) - a materially bigger,
principled consequence for a materially worse underlying problem.

WORKED EXAMPLE (clean data): if every dimension_i = 100, every
penalty_i = 0, so sum(weight_i * 0**Q) = 0, and 100 - 0**(1/Q) = 100
exactly, for any Q > 0. A genuinely clean dataset always scores
exactly 100 regardless of the exponent chosen.

NO SPECIAL-CASING NEEDED FOR ZERO: unlike the earlier (rejected)
negative-exponent-on-values approach, raising a bounded penalty
(which can validly be as low as 0) to a POSITIVE power is always
well-defined - 0**Q = 0 for Q>0 - so there is no division-by-zero or
overflow edge case to guard against here.
"""

import re

# ---------------------------------------------------------------------
# Dimension weights (must sum to 1.0) - UNCHANGED from prior revisions.
# ---------------------------------------------------------------------

WEIGHTS = {
    "completeness": 0.25,
    "uniqueness": 0.15,
    "type_quality": 0.15,
    "consistency": 0.15,
    "numerical_quality": 0.10,
    "structural_quality": 0.20,
}

# Which quality_checks.py issue category feeds each issue-based dimension.
CATEGORY_FOR_DIMENSION = {
    "Type Quality": "Data Types",
    "Consistency": "Categorical Consistency",
    "Numerical Quality": "Numerical Outliers",
    "Structural Quality": "Constant Columns",
}

# One-line explanation of what each dimension measures, for the UI.
DIMENSION_EXPLANATIONS = {
    "Completeness": "How many cells have values vs. are missing.",
    "Uniqueness": "How many rows are exact or likely (normalized) duplicates.",
    "Type Quality": "Whether columns look like they're stored as the right type.",
    "Consistency": "Whether text values use consistent whitespace/capitalization.",
    "Numerical Quality": "Whether numeric columns contain statistical outliers.",
    "Structural Quality": "Whether any columns carry no information (constant values).",
}

# The exponent (Q) used to combine the six dimensions' PENALTIES
# (100 - dimension_i) into one overall score (STEP 3 above). Q=1 would
# reproduce the old plain weighted-arithmetic-mean behavior exactly;
# Q>1 makes larger, more widespread penalties count disproportionately
# more (the same principle as RMSE vs. MAE). Q=2 (the quadratic mean /
# RMS of penalties) was chosen empirically against the calibration
# targets - it noticeably increases the impact of one seriously
# degraded dimension without over-punishing several only-moderate
# ones. The clean-data-scores-100 guarantee holds exactly for any Q>0.
AGGREGATION_POWER = 2

# ---------------------------------------------------------------------
# Per-issue penalty configuration (STEP 1)
#
# fraction_for_issue = SEVERITY_WEIGHT[severity] * affected_proportion
# ---------------------------------------------------------------------

CONFIRMED_SEVERITY_WEIGHT = {
    "Good": 0.0,
    "Warning": 0.50,
    "Critical": 1.00,
}

REVIEW_ONLY_SEVERITY_WEIGHT = {
    "Good": 0.0,
    "Warning": 0.20,
    "Critical": 0.40,  # rarely reached - outliers are capped at Warning upstream
}

# Categories whose issues represent observations for human review rather
# than confirmed problems, and therefore use the lighter table above.
REVIEW_ONLY_CATEGORIES = {"Numerical Outliers", "Potential Duplicate Rows"}

MAX_FRACTION_CONFIRMED = 0.95
MAX_FRACTION_REVIEW_ONLY = 0.30

# Legacy fallback only: used when an issue has no "affected_proportion"
# field (see _get_affected_proportion). Kept for backward compatibility
# with any issue producer that hasn't been updated to the structured
# field yet.
_PERCENT_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*%")


def _get_affected_proportion(issue: dict) -> float:
    """
    The fraction (0-1) of the relevant scope (rows/values/columns) that
    this issue affects.

    Preferred source: the issue's own explicit "affected_proportion"
    numeric field, populated by quality_checks.py from the same values
    it already computes internally (see quality_checks.py's _issue()
    calls). This is a structured value, not text parsing.

    Fallback (backward compatibility only): if an issue lacks that
    field - e.g. it came from an older or third-party producer - fall
    back to parsing a percentage out of the human-readable "metric"
    string, and failing that, assume full relevance (1.0) rather than
    silently zeroing out an issue's impact.
    """
    value = issue.get("affected_proportion")
    if value is not None:
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            pass

    match = _PERCENT_PATTERN.search(issue.get("metric", ""))
    if match:
        return float(match.group(1)) / 100.0

    return 1.0


def _fraction_for_issue(issue: dict) -> float:
    """
    The fraction of a dimension's remaining score that a single issue
    removes: severity_weight * affected_proportion, capped per tier.
    """
    severity = issue.get("severity", "Good")
    category = issue.get("category", "")
    is_review_only = category in REVIEW_ONLY_CATEGORIES

    weight_table = REVIEW_ONLY_SEVERITY_WEIGHT if is_review_only else CONFIRMED_SEVERITY_WEIGHT
    severity_weight = weight_table.get(severity, 0.0)
    if severity_weight == 0.0:
        return 0.0

    proportion = _get_affected_proportion(issue)
    fraction = severity_weight * proportion

    max_fraction = MAX_FRACTION_REVIEW_ONLY if is_review_only else MAX_FRACTION_CONFIRMED
    return min(fraction, max_fraction)


def _score_from_issues(issues: list, category: str) -> float:
    """
    Start a dimension at 100 and apply matching issues' fractions.

    STEP 2 (double-counting fix): issues are grouped by the column(s)
    they affect. Within a group, only the STRONGEST fraction counts
    (max, not product) - this is what prevents e.g. a whitespace issue
    and a capitalization issue on the same column from compounding as
    if they were two independent problems, when they may describe
    overlapping observations. Different columns (different groups)
    still combine multiplicatively, since those genuinely are
    independent problems.
    """
    groups: dict = {}
    for issue in issues:
        if issue.get("category") != category:
            continue
        key = tuple(issue.get("columns") or [])
        groups.setdefault(key, []).append(_fraction_for_issue(issue))

    score = 100.0
    for fractions in groups.values():
        strongest = max(fractions)
        score *= (1 - strongest)

    return max(0.0, min(100.0, score))


# ---------------------------------------------------------------------
# Individual dimension scores
# ---------------------------------------------------------------------

def calculate_completeness_score(profile: dict) -> float:
    """
    Calculate completeness based on the percentage of missing cells.

    100 = no missing cells
    0 = all cells are missing
    """

    missing_pct = profile.get("missing_cells_pct", 0.0)

    score = 100.0 - missing_pct

    return max(0.0, min(100.0, score))


def calculate_uniqueness_score(profile: dict, issues: list) -> float:
    """
    Uniqueness combines two signals:
      - Exact duplicate rows (from the profile) - the dominant, most
        certain signal, subtracted directly as before.
      - Potential (normalized) duplicate rows (from the issues list) -
        a softer, review-only signal, applied multiplicatively on top
        so it can never by itself be as damaging as an exact duplicate.
    There is at most one "Potential Duplicate Rows" issue per dataset
    (it's a dataset-wide check, not per-column), so no grouping is
    needed here - the double-counting fix in _score_from_issues is not
    applicable to this dimension.
    """
    duplicate_pct = profile.get("duplicate_rows_pct", 0.0)
    base_score = max(0.0, min(100.0, 100.0 - duplicate_pct))

    score = base_score
    for issue in issues:
        if issue.get("category") == "Potential Duplicate Rows":
            fraction = _fraction_for_issue(issue)
            score *= (1 - fraction)

    return max(0.0, min(100.0, score))


def calculate_type_quality_score(profile: dict, issues: list) -> float:
    """
    Type quality is reduced whenever a column is flagged in the
    "Data Types" category - e.g. a text column whose values mostly
    look numeric (mixed/suspicious typing).
    """

    return _score_from_issues(issues, CATEGORY_FOR_DIMENSION["Type Quality"])


def calculate_consistency_score(profile: dict, issues: list) -> float:
    """
    Consistency is reduced whenever a column is flagged in the
    "Categorical Consistency" category - e.g. capitalization or
    whitespace variants of what looks like the same value. See
    _score_from_issues for how overlapping whitespace/capitalization
    issues on the same column avoid being double-counted.
    """

    return _score_from_issues(issues, CATEGORY_FOR_DIMENSION["Consistency"])


def calculate_numerical_quality_score(profile: dict, issues: list) -> float:
    """
    Numerical quality is reduced whenever a numeric MEASUREMENT column
    (identifier-like columns are excluded upstream) is flagged in the
    "Numerical Outliers" category. Outliers are a statistical
    observation, not automatically an error - this dimension uses the
    lighter review-only penalty fraction so it reflects how much of the
    data looks unusual without overstating certainty.
    """

    return _score_from_issues(issues, CATEGORY_FOR_DIMENSION["Numerical Quality"])


def calculate_structural_quality_score(profile: dict, issues: list) -> float:
    """
    Structural quality is reduced whenever a column is flagged in the
    "Constant Columns" category - a column with only one unique value
    carries no information for most analyses.
    """

    return _score_from_issues(issues, CATEGORY_FOR_DIMENSION["Structural Quality"])


# ---------------------------------------------------------------------
# Overall score
# ---------------------------------------------------------------------

def _combine_dimensions(dimension_scores: dict, weights: dict) -> float:
    """
    Combine the six dimension scores into one overall score by
    aggregating their PENALTIES (100 - score) with a weighted power
    mean of exponent AGGREGATION_POWER, then converting back to a
    score (see STEP 3 in the module docstring for the full
    mathematical justification):

        penalty_i = 100 - dimension_i
        overall   = 100 - ( sum(weight_i * penalty_i ** Q) ) ** (1/Q)

    Well-defined for any dimension score in [0, 100] and any Q > 0 -
    no special-casing needed for a dimension score of exactly 0 or 100.
    """
    q = AGGREGATION_POWER
    weighted_penalty_sum = sum(
        weights[name] * (100.0 - dimension_scores[name]) ** q
        for name in dimension_scores
    )
    overall_penalty = weighted_penalty_sum ** (1.0 / q)
    overall = 100.0 - overall_penalty

    return max(0.0, min(100.0, overall))


def compute_reliability_score(profile: dict, issues: list) -> dict:
    """
    Calculate the overall Data Reliability Score.

    Each of the six quality dimensions is scored from 0 to 100 (using
    the weights in WEIGHTS to describe each dimension's importance),
    then combined into one overall score via a weighted power mean
    (see _combine_dimensions and the module docstring, STEP 3).
    """

    dimension_scores = {
        "Completeness": calculate_completeness_score(profile),
        "Uniqueness": calculate_uniqueness_score(profile, issues),
        "Type Quality": calculate_type_quality_score(profile, issues),
        "Consistency": calculate_consistency_score(profile, issues),
        "Numerical Quality": calculate_numerical_quality_score(profile, issues),
        "Structural Quality": calculate_structural_quality_score(profile, issues),
    }

    dimension_weights = {
        "Completeness": WEIGHTS["completeness"],
        "Uniqueness": WEIGHTS["uniqueness"],
        "Type Quality": WEIGHTS["type_quality"],
        "Consistency": WEIGHTS["consistency"],
        "Numerical Quality": WEIGHTS["numerical_quality"],
        "Structural Quality": WEIGHTS["structural_quality"],
    }

    overall_score = _combine_dimensions(dimension_scores, dimension_weights)

    return {
        "score": round(overall_score, 1),
        "dimension_scores": dimension_scores,
        "dimension_weights": dimension_weights,
    }


# ---------------------------------------------------------------------
# Score label
# ---------------------------------------------------------------------

def score_label(score: float) -> str:
    """
    Return a simple human-readable interpretation of the score.
    """

    if score >= 85:
        return "Strong"

    if score >= 65:
        return "Moderate"

    if score >= 40:
        return "Weak"

    return "Poor"


# =======================================================================
# PHASE 3: column-level reliability scores and plain-language explanation
# =======================================================================
#
# Column-level scores reuse the exact same penalty methodology as the
# dataset-level score above (STEPS 1-3) - no new math, just the same
# _fraction_for_issue / power-mean logic scoped to one column's issues
# instead of the whole dataset's.
#
# Uniqueness is deliberately EXCLUDED from column-level scoring: it
# measures whole-ROW duplication (exact/potential duplicate ROWS), which
# is not a property any single column owns - attributing it to one
# column would misrepresent what the signal actually means. The other
# five dimensions' weights are renormalized (divided by their sum) so
# they still sum to 1.0, preserving their RELATIVE importance from the
# dataset-level score.

COLUMN_DIMENSION_CATEGORIES = {
    "Completeness": "Missing Values",
    "Type Quality": "Data Types",
    "Consistency": "Categorical Consistency",
    "Numerical Quality": "Numerical Outliers",
    "Structural Quality": "Constant Columns",
}

_COLUMN_WEIGHT_BASIS = {
    "Completeness": WEIGHTS["completeness"],
    "Type Quality": WEIGHTS["type_quality"],
    "Consistency": WEIGHTS["consistency"],
    "Numerical Quality": WEIGHTS["numerical_quality"],
    "Structural Quality": WEIGHTS["structural_quality"],
}
_COLUMN_WEIGHT_TOTAL = sum(_COLUMN_WEIGHT_BASIS.values())
COLUMN_WEIGHTS = {
    name: weight / _COLUMN_WEIGHT_TOTAL for name, weight in _COLUMN_WEIGHT_BASIS.items()
}


def _score_from_issues_for_column(issues: list, category: str, column: str) -> float:
    """
    Same STEP 1/2 penalty logic as _score_from_issues, scoped to issues
    that both match `category` AND name this specific `column`. Multiple
    matching issues for the same column (e.g. whitespace AND
    capitalization, both under Categorical Consistency) take the
    strongest fraction - the same double-counting fix as STEP 2, just
    pre-filtered to one column instead of grouped across all of them.

    A column with no matching issues at all scores 100 for that
    dimension - identical to how a dataset with no issues in a category
    scores 100 in _score_from_issues.
    """
    column_issues = [
        issue
        for issue in issues
        if issue.get("category") == category and column in (issue.get("columns") or [])
    ]
    if not column_issues:
        return 100.0

    strongest = max(_fraction_for_issue(issue) for issue in column_issues)
    return max(0.0, min(100.0, 100.0 * (1 - strongest)))


def compute_column_reliability_scores(profile: dict, issues: list) -> dict:
    """
    Per-column reliability scores, using the same methodology as the
    dataset-level score (STEPS 1-3), scoped to each column individually.

    Every column in the dataset gets an entry, including columns with
    zero issues (all five dimensions default to 100, overall score 100).

    Returns:
        {
            column_name: {
                "score": float,
                "label": str,
                "dimension_scores": {5 dims},
                "dimension_weights": {5 dims, renormalized - see COLUMN_WEIGHTS},
                "explanation": [str, ...],
            },
            ...
        }
    """
    all_columns = list(profile.get("numeric_columns", [])) + list(
        profile.get("categorical_columns", [])
    )

    column_scores = {}
    for column in all_columns:
        dimension_scores = {
            dimension: _score_from_issues_for_column(issues, category, column)
            for dimension, category in COLUMN_DIMENSION_CATEGORIES.items()
        }
        overall = _combine_dimensions(dimension_scores, COLUMN_WEIGHTS)

        column_scores[column] = {
            "score": round(overall, 1),
            "label": score_label(overall),
            "dimension_scores": dimension_scores,
            "dimension_weights": COLUMN_WEIGHTS,
            "explanation": explain_reliability_score(
                dimension_scores, COLUMN_WEIGHTS, issues, columns=[column]
            ),
        }

    return column_scores


# Maps every scored dimension to the issue category/categories that feed
# it, for explanation purposes. Uniqueness maps to two categories since
# it combines two separate checks (exact + potential duplicate rows).
DIMENSION_TO_CATEGORIES = {
    "Completeness": ["Missing Values"],
    "Uniqueness": ["Exact Duplicate Rows", "Potential Duplicate Rows"],
    "Type Quality": ["Data Types"],
    "Consistency": ["Categorical Consistency"],
    "Numerical Quality": ["Numerical Outliers"],
    "Structural Quality": ["Constant Columns"],
}

MAX_EXPLANATION_DIMENSIONS = 3
MAX_ISSUES_CITED_PER_DIMENSION = 2


def explain_reliability_score(
    dimension_scores: dict,
    dimension_weights: dict,
    issues: list,
    columns: list | None = None,
) -> list:
    """
    Produce an ordered list of plain-language sentences explaining WHY a
    score is what it is. Every sentence traces back to a specific
    dimension score and the underlying issue(s) that produced it - this
    is template-based generation over data already computed elsewhere in
    this module (dimension_scores + issues), not a generative model, so
    it can never say anything the score itself doesn't already reflect.

    `columns`, if given, restricts cited issues to ones naming one of
    these columns (used for per-column explanations). When omitted
    (dataset-level explanations), issues from any column are eligible,
    including dataset-wide ones like duplicate rows.

    Ordering: dimensions are ranked by their contribution to the overall
    penalty - weight * penalty**2, mirroring the same Q=2 aggregation
    used to compute the score itself (see STEP 3) - so the FIRST
    sentence names the single biggest driver of a less-than-perfect
    score. A low-weight dimension that's badly damaged can matter more
    than a high-weight one that's only slightly off; this ranking
    reflects that rather than just sorting by raw score.
    """
    ranked = []
    for name, score in dimension_scores.items():
        weight = dimension_weights.get(name, 0.0)
        penalty = 100.0 - score
        impact = weight * (penalty ** 2)
        ranked.append((name, score, penalty, impact))

    ranked.sort(key=lambda item: item[3], reverse=True)

    sentences = []
    for name, score, penalty, _impact in ranked:
        if penalty <= 0 or len(sentences) >= MAX_EXPLANATION_DIMENSIONS:
            continue

        categories = DIMENSION_TO_CATEGORIES.get(name, [])
        candidate_issues = [
            issue
            for issue in issues
            if issue.get("category") in categories
            and issue.get("severity") != "Good"
            and (
                columns is None
                or not issue.get("columns")  # dataset-wide issue (e.g. duplicates)
                or any(col in columns for col in issue["columns"])
            )
        ]
        candidate_issues.sort(
            key=lambda issue: _get_affected_proportion(issue), reverse=True
        )
        cited = candidate_issues[:MAX_ISSUES_CITED_PER_DIMENSION]

        lead = "is the biggest factor lowering the score" if not sentences else "also falls short"
        sentence = f"{name} {lead} ({round(score, 1)}/100)."
        for issue in cited:
            sentence += f" {issue['explanation']}"

        sentences.append(sentence)

    if not sentences:
        scope = "This column" if columns else "This dataset"
        sentences.append(f"{scope} scored perfectly on every measured dimension.")

    return sentences
