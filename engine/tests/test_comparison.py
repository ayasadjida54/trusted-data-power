"""
test_comparison.py

Phase 5 tests for engine.compare_analysis_results, using small
hand-built result dicts (not full analyze_dataframe() output) so each
scenario is explicit and easy to verify by hand.
"""

import pytest

from engine.comparison import compare_analysis_results


def _result(score, dimension_scores, issues):
    return {
        "score": score,
        "score_label": "Strong" if score >= 85 else "Moderate",
        "dimension_scores": dimension_scores,
        "issues": issues,
    }


def _issue(category, severity, columns=None):
    return {
        "category": category,
        "severity": severity,
        "columns": columns or [],
        "metric": "n/a",
        "explanation": f"{category} issue",
        "recommendation": "fix it",
    }


def test_score_delta_is_current_minus_previous():
    previous = _result(80.0, {"Completeness": 80.0}, [])
    current = _result(92.0, {"Completeness": 92.0}, [])
    diff = compare_analysis_results(previous, current)
    assert diff["score_delta"] == 12.0
    assert diff["previous_score"] == 80.0
    assert diff["current_score"] == 92.0


def test_negative_score_delta_when_score_drops():
    previous = _result(92.0, {"Completeness": 92.0}, [])
    current = _result(80.0, {"Completeness": 80.0}, [])
    diff = compare_analysis_results(previous, current)
    assert diff["score_delta"] == -12.0


def test_dimension_deltas_computed_per_dimension():
    previous = _result(80.0, {"Completeness": 70.0, "Consistency": 90.0}, [])
    current = _result(85.0, {"Completeness": 85.0, "Consistency": 80.0}, [])
    diff = compare_analysis_results(previous, current)
    assert diff["dimension_deltas"]["Completeness"] == 15.0
    assert diff["dimension_deltas"]["Consistency"] == -10.0


def test_new_issue_detected():
    previous = _result(90.0, {}, [])
    current = _result(80.0, {}, [_issue("Missing Values", "Warning", ["notes"])])
    diff = compare_analysis_results(previous, current)
    assert len(diff["new_issues"]) == 1
    assert diff["new_issues"][0]["category"] == "Missing Values"
    assert diff["resolved_issues"] == []


def test_resolved_issue_detected():
    previous = _result(80.0, {}, [_issue("Missing Values", "Warning", ["notes"])])
    current = _result(90.0, {}, [])
    diff = compare_analysis_results(previous, current)
    assert len(diff["resolved_issues"]) == 1
    assert diff["new_issues"] == []


def test_worsened_issue_detected_by_severity_change():
    previous = _result(85.0, {}, [_issue("Categorical Consistency", "Warning", ["category"])])
    current = _result(70.0, {}, [_issue("Categorical Consistency", "Critical", ["category"])])
    diff = compare_analysis_results(previous, current)
    assert len(diff["worsened_issues"]) == 1
    assert diff["improved_issues"] == []


def test_improved_issue_detected_by_severity_change():
    previous = _result(70.0, {}, [_issue("Categorical Consistency", "Critical", ["category"])])
    current = _result(85.0, {}, [_issue("Categorical Consistency", "Warning", ["category"])])
    diff = compare_analysis_results(previous, current)
    assert len(diff["improved_issues"]) == 1
    assert diff["worsened_issues"] == []


def test_same_severity_issue_is_neither_worsened_nor_improved():
    previous = _result(85.0, {}, [_issue("Data Types", "Warning", ["amount"])])
    current = _result(85.0, {}, [_issue("Data Types", "Warning", ["amount"])])
    diff = compare_analysis_results(previous, current)
    assert diff["worsened_issues"] == []
    assert diff["improved_issues"] == []
    assert diff["new_issues"] == []
    assert diff["resolved_issues"] == []


def test_good_severity_issues_are_not_counted_as_new_or_resolved():
    # A "Good" issue appearing/disappearing (e.g. Data Types' per-column
    # status issues) isn't a real finding change worth surfacing.
    previous = _result(90.0, {}, [])
    current = _result(90.0, {}, [_issue("Data Types", "Good", ["id"])])
    diff = compare_analysis_results(previous, current)
    assert diff["new_issues"] == []


def test_different_columns_are_treated_as_different_findings():
    previous = _result(85.0, {}, [_issue("Missing Values", "Warning", ["notes"])])
    current = _result(80.0, {}, [_issue("Missing Values", "Warning", ["email"])])
    diff = compare_analysis_results(previous, current)
    assert len(diff["new_issues"]) == 1
    assert len(diff["resolved_issues"]) == 1
    assert diff["worsened_issues"] == []


def test_summary_mentions_improvement():
    previous = _result(70.0, {"Completeness": 70.0}, [])
    current = _result(90.0, {"Completeness": 90.0}, [])
    diff = compare_analysis_results(previous, current)
    assert any("improved" in s for s in diff["summary"])


def test_summary_mentions_drop():
    previous = _result(90.0, {"Completeness": 90.0}, [])
    current = _result(70.0, {"Completeness": 70.0}, [])
    diff = compare_analysis_results(previous, current)
    assert any("dropped" in s for s in diff["summary"])


def test_summary_mentions_new_issues_by_category():
    previous = _result(90.0, {}, [])
    current = _result(80.0, {}, [_issue("Constant Columns", "Critical", ["status"])])
    diff = compare_analysis_results(previous, current)
    assert any("Constant Columns" in s for s in diff["summary"])


def test_no_change_produces_unchanged_summary():
    previous = _result(90.0, {"Completeness": 90.0}, [_issue("Data Types", "Warning", ["x"])])
    current = _result(90.0, {"Completeness": 90.0}, [_issue("Data Types", "Warning", ["x"])])
    diff = compare_analysis_results(previous, current)
    assert diff["score_delta"] == 0.0
    assert any("unchanged" in s for s in diff["summary"])
