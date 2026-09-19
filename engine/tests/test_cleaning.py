"""
test_cleaning.py

Phase 9 (DataScore cleaning pipeline) tests. Verifies the cleaner only
touches what it claims to (duplicates, whitespace, capitalization),
never touches what it says it won't (missing values, outliers,
constant columns), and that its reported actions match what actually
changed.
"""

import pandas as pd
import pytest

from engine import analyze_dataframe
from engine.cleaning import clean_dataframe
from engine.quality_checks import run_all_checks


@pytest.fixture
def messy_df():
    return pd.read_csv(
        __import__("os").path.join(
            __import__("os").path.dirname(__file__), "sample_messy_data.csv"
        )
    )


def test_exact_duplicates_are_removed():
    df = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})
    issues = run_all_checks(df)["issues"]
    cleaned, actions = clean_dataframe(df, issues)

    assert len(cleaned) == 2
    assert any("duplicate" in a.lower() for a in actions)


def test_no_duplicates_produces_no_duplicate_action():
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    issues = run_all_checks(df)["issues"]
    cleaned, actions = clean_dataframe(df, issues)

    assert len(cleaned) == 3
    assert not any(a.lower().startswith("removed") for a in actions)


def test_whitespace_is_trimmed():
    df = pd.DataFrame({"name": ["Alice", "Bob ", " Carol"], "n": [1, 2, 3]})
    issues = run_all_checks(df)["issues"]
    cleaned, actions = clean_dataframe(df, issues)

    assert list(cleaned["name"]) == ["Alice", "Bob", "Carol"]
    assert any("whitespace" in a.lower() and "name" in a for a in actions)


def test_capitalization_is_standardized_to_majority_form():
    df = pd.DataFrame({"status": ["Active"] * 8 + ["active"] * 2, "n": range(10)})
    issues = run_all_checks(df)["issues"]
    cleaned, actions = clean_dataframe(df, issues)

    assert (cleaned["status"] == "Active").all()
    assert any("capitalization" in a.lower() and "status" in a for a in actions)


def test_cleaning_never_touches_missing_values():
    df = pd.DataFrame({"a": [1.0, None, 3.0], "b": ["x", "y", "z"]})
    issues = run_all_checks(df)["issues"]
    cleaned, _actions = clean_dataframe(df, issues)

    assert cleaned["a"].isna().sum() == 1  # unchanged


def test_cleaning_never_touches_outliers():
    df = pd.DataFrame({"amount": [10, 11, 9, 10, 12, 9999], "n": range(6)})
    issues = run_all_checks(df)["issues"]
    cleaned, actions = clean_dataframe(df, issues)

    assert 9999 in cleaned["amount"].values
    assert not any("outlier" in a.lower() for a in actions)


def test_cleaning_never_touches_constant_columns():
    df = pd.DataFrame({"status": ["active"] * 5, "n": range(5)})
    issues = run_all_checks(df)["issues"]
    cleaned, actions = clean_dataframe(df, issues)

    assert list(cleaned.columns) == ["status", "n"]
    assert not any("constant" in a.lower() for a in actions)


def test_cleaning_never_touches_potential_duplicates_only():
    # Rows that match only after normalization (not exact duplicates)
    # should NOT be dropped - only a genuinely exact duplicate row
    # should be.
    df = pd.DataFrame({"name": ["Alice", "alice "], "n": [1, 2]})
    issues = run_all_checks(df)["issues"]
    cleaned, _actions = clean_dataframe(df, issues)

    # whitespace/capitalization cleaning WILL normalize the text, but
    # the row itself (with its distinct 'n' value) must not be dropped
    # as a "duplicate" - only exact full-row duplicates are removed.
    assert len(cleaned) == 2


def test_clean_data_produces_only_the_no_op_message():
    df = pd.DataFrame({"product": ["Widget", "Gadget"], "price": [10.0, 20.0]})
    issues = run_all_checks(df)["issues"]
    cleaned, actions = clean_dataframe(df, issues)

    pd.testing.assert_frame_equal(cleaned, df)
    assert len(actions) == 1
    assert "no automatic fixes" in actions[0].lower()


def test_cleaning_the_sample_data_improves_the_real_score(messy_df):
    issues = run_all_checks(messy_df)["issues"]
    cleaned, actions = clean_dataframe(messy_df, issues)

    before_score = analyze_dataframe(messy_df)["score"]
    after_score = analyze_dataframe(cleaned)["score"]

    assert after_score >= before_score
    assert len(actions) > 0
    # Sanity: cleaning must not change row count for THIS file (no
    # exact duplicates in the sample data) or drop any columns.
    assert len(cleaned) == len(messy_df)
    assert list(cleaned.columns) == list(messy_df.columns)


def test_cleaning_is_idempotent(messy_df):
    # Running the cleaner on already-cleaned data should report nothing
    # left to fix (beyond what it deliberately never touches, like
    # missing values).
    issues = run_all_checks(messy_df)["issues"]
    cleaned_once, _ = clean_dataframe(messy_df, issues)

    issues_again = run_all_checks(cleaned_once)["issues"]
    cleaned_twice, actions_twice = clean_dataframe(cleaned_once, issues_again)

    pd.testing.assert_frame_equal(cleaned_once, cleaned_twice)
    assert "no automatic fixes" in actions_twice[0].lower()


def test_reported_action_counts_match_actual_changes():
    df = pd.DataFrame(
        {
            "category": ["Retail", "retail", "Retail", "Wholesale", " Retail"],
            "n": range(5),
        }
    )
    issues = run_all_checks(df)["issues"]
    cleaned, actions = clean_dataframe(df, issues)

    # 3 "Retail" already correct, "retail" needs recapitalization,
    # " Retail" needs both whitespace trim (no case change needed).
    assert (cleaned["category"] == "Retail").sum() == 4
    assert (cleaned["category"] == "Wholesale").sum() == 1
    joined = " ".join(actions)
    assert "whitespace" in joined.lower()
    assert "capitalization" in joined.lower()
