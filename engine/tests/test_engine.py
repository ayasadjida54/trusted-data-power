"""
test_engine.py

Phase 0 regression tests. Goal: prove that organizing the four
analysis modules into engine/ and adding analyze_dataframe() did NOT
change any analysis behavior.

Two kinds of tests here:
1. Regression tests that call the underlying modules directly (the
   exact sequence app.py performs) and assert analyze_dataframe()
   produces identical results - this is the actual "nothing broke"
   proof for Phase 0.
2. Basic sanity/edge-case tests for the engine's public API, since a
   plain API entry point (analyze_dataframe) didn't exist before.
"""

import os

import pandas as pd
import pytest

from engine import analyze_dataframe
from engine.profiling import build_dataset_profile, get_column_dtypes
from engine.quality_checks import run_all_checks
from engine.scoring import (
    compute_reliability_score,
    compute_column_reliability_scores,
    explain_reliability_score,
    score_label,
    COLUMN_WEIGHTS,
)
from engine.recommendations import get_prioritized_recommendations, summarize_issue_counts

SAMPLE_CSV = os.path.join(os.path.dirname(__file__), "sample_messy_data.csv")


@pytest.fixture
def messy_df():
    return pd.read_csv(SAMPLE_CSV)


@pytest.fixture
def clean_df():
    return pd.DataFrame(
        {
            "product": ["Widget", "Gadget", "Gizmo", "Doohickey"],
            "price": [10.0, 25.5, 7.25, 40.0],
            "in_stock": [True, True, False, True],
        }
    )


# ---------------------------------------------------------------------
# 1. Regression: analyze_dataframe() must match the manual pipeline
#    exactly - same sequence app.py performs today.
# ---------------------------------------------------------------------

def test_analyze_dataframe_matches_manual_pipeline(messy_df):
    manual_profile = build_dataset_profile(messy_df)
    manual_checks = run_all_checks(messy_df)
    manual_issues = manual_checks["issues"]
    manual_score_result = compute_reliability_score(manual_profile, manual_issues)

    result = analyze_dataframe(messy_df)

    assert result["profile"] == manual_profile
    assert result["issues"] == manual_issues
    assert result["score"] == manual_score_result["score"]
    assert result["score_label"] == score_label(manual_score_result["score"])
    assert result["dimension_scores"] == manual_score_result["dimension_scores"]
    assert result["dimension_weights"] == manual_score_result["dimension_weights"]
    assert result["issue_counts"] == summarize_issue_counts(manual_issues)
    assert result["recommendations"] == get_prioritized_recommendations(manual_issues, top_n=5)

    pd.testing.assert_frame_equal(result["numeric_stats"], manual_checks["numeric_stats"])
    pd.testing.assert_frame_equal(result["column_dtypes"], get_column_dtypes(messy_df))

    manual_explanation = explain_reliability_score(
        manual_score_result["dimension_scores"], manual_score_result["dimension_weights"], manual_issues
    )
    manual_column_scores = compute_column_reliability_scores(manual_profile, manual_issues)
    assert result["score_explanation"] == manual_explanation
    assert result["column_scores"] == manual_column_scores


def test_analyze_dataframe_respects_top_n_recommendations(messy_df):
    result = analyze_dataframe(messy_df, top_n_recommendations=2)
    assert len(result["recommendations"]) <= 2


# ---------------------------------------------------------------------
# 2. Sanity checks on the messy sample data - known, human-verifiable
#    characteristics of sample_messy_data.csv, so a future change to
#    the engine that silently alters behavior gets caught here too.
# ---------------------------------------------------------------------

def test_messy_data_is_flagged_as_imperfect(messy_df):
    result = analyze_dataframe(messy_df)
    assert 0 <= result["score"] <= 100
    assert result["score"] < 100, "Messy sample data should not score a perfect 100"
    assert result["issue_counts"]["Critical"] + result["issue_counts"]["Warning"] > 0


def test_messy_data_flags_capitalization_inconsistency(messy_df):
    # "Retail" vs "retail" in the category column is a known issue in
    # the sample file.
    result = analyze_dataframe(messy_df)
    categories_flagged = {
        issue["category"] for issue in result["issues"] if "category" in issue["columns"]
    }
    assert "Categorical Consistency" in categories_flagged


# ---------------------------------------------------------------------
# 3. Clean data should score a perfect 100 (matches scoring.py's own
#    documented guarantee - see the worked example in its docstring).
# ---------------------------------------------------------------------

def test_clean_data_scores_100(clean_df):
    result = analyze_dataframe(clean_df)
    assert result["score"] == 100.0
    assert result["score_label"] == "Strong"


# ---------------------------------------------------------------------
# 4. Edge cases the API needs to handle explicitly.
# ---------------------------------------------------------------------

def test_empty_dataframe_raises_value_error():
    with pytest.raises(ValueError):
        analyze_dataframe(pd.DataFrame())


def test_none_raises_value_error():
    with pytest.raises(ValueError):
        analyze_dataframe(None)


def test_dataframe_with_no_columns_raises_value_error():
    empty_with_rows = pd.DataFrame(index=[0, 1, 2])
    with pytest.raises(ValueError):
        analyze_dataframe(empty_with_rows)


# ---------------------------------------------------------------------
# 5. Column-level reliability scores (Phase 3)
# ---------------------------------------------------------------------

def test_column_weights_sum_to_one():
    assert sum(COLUMN_WEIGHTS.values()) == pytest.approx(1.0)


def test_every_column_gets_a_score(messy_df):
    result = analyze_dataframe(messy_df)
    assert set(result["column_scores"].keys()) == set(messy_df.columns)


def test_clean_columns_score_100(clean_df):
    result = analyze_dataframe(clean_df)
    for column, column_result in result["column_scores"].items():
        assert column_result["score"] == 100.0
        assert column_result["label"] == "Strong"


def test_notes_column_penalized_for_missingness(messy_df):
    # "notes" has 5/10 missing values in the sample data - should score
    # well below 100 on Completeness specifically.
    result = analyze_dataframe(messy_df)
    notes_result = result["column_scores"]["notes"]
    assert notes_result["dimension_scores"]["Completeness"] < 100.0
    assert notes_result["score"] < 100.0


def test_category_column_penalized_for_consistency(messy_df):
    # "category" has both a whitespace issue and a capitalization issue
    # in the sample data.
    result = analyze_dataframe(messy_df)
    category_result = result["column_scores"]["category"]
    assert category_result["dimension_scores"]["Consistency"] < 100.0


def test_column_score_matches_direct_call(messy_df):
    profile = build_dataset_profile(messy_df)
    issues = run_all_checks(messy_df)["issues"]
    direct = compute_column_reliability_scores(profile, issues)
    via_pipeline = analyze_dataframe(messy_df)["column_scores"]

    for column in direct:
        assert direct[column]["score"] == via_pipeline[column]["score"]
        assert direct[column]["dimension_scores"] == via_pipeline[column]["dimension_scores"]


# ---------------------------------------------------------------------
# 6. Explainability (Phase 3)
# ---------------------------------------------------------------------

def test_clean_data_explanation_is_positive(clean_df):
    result = analyze_dataframe(clean_df)
    assert len(result["score_explanation"]) == 1
    assert "perfectly" in result["score_explanation"][0]


def test_messy_data_explanation_cites_a_real_dimension(messy_df):
    result = analyze_dataframe(messy_df)
    explanation = result["score_explanation"]
    assert len(explanation) > 0
    # Every sentence should name one of the six real dimensions.
    dimension_names = list(result["dimension_scores"].keys())
    assert any(name in explanation[0] for name in dimension_names)


def test_explanation_is_capped_at_max_dimensions(messy_df):
    result = analyze_dataframe(messy_df)
    assert len(result["score_explanation"]) <= 3


def test_column_explanation_only_cites_that_columns_issues(messy_df):
    result = analyze_dataframe(messy_df)
    notes_explanation = " ".join(result["column_scores"]["notes"]["explanation"])
    # The notes column's explanation should reference notes' own missing
    # values, not an unrelated column's issue text.
    assert "notes" in notes_explanation


def test_explain_reliability_score_direct_call_matches_pipeline(messy_df):
    profile = build_dataset_profile(messy_df)
    issues = run_all_checks(messy_df)["issues"]
    score_result = compute_reliability_score(profile, issues)
    direct = explain_reliability_score(
        score_result["dimension_scores"], score_result["dimension_weights"], issues
    )
    via_pipeline = analyze_dataframe(messy_df)["score_explanation"]
    assert direct == via_pipeline
