"""
services.comparison_service

Loads two already-stored AnalysisRun rows and feeds them to
engine.compare_analysis_results. Deliberately does NOT re-run the
engine - every field compare_analysis_results needs (score,
score_label, dimension_scores, issues) is already sitting in the
database from when each run was originally analyzed, so comparing two
runs is just two SELECTs and a pure function call.
"""

from sqlalchemy.orm import Session

from backend.models import AnalysisRun
from engine import compare_analysis_results


class RunNotFound(Exception):
    pass


def _as_engine_result(run: AnalysisRun) -> dict:
    return {
        "score": run.score,
        "score_label": run.score_label,
        "dimension_scores": run.dimension_scores,
        "issues": run.issues,
    }


def compare_runs(db: Session, organization_id: int, run_id_a: int, run_id_b: int) -> dict:
    """
    Compare two runs, both scoped to `organization_id` (a run belonging
    to a different organization is treated as not found, same as the
    other dataset/run routes). `run_id_a` is treated as the earlier
    run and `run_id_b` as the later one, REGARDLESS of which was
    actually analyzed first - the caller picks the direction; this
    just diffs A -> B.

    Raises RunNotFound if either run doesn't resolve within this
    organization.
    """
    runs = {
        run.id: run
        for run in (
            db.query(AnalysisRun)
            .join(AnalysisRun.dataset)
            .filter(
                AnalysisRun.id.in_([run_id_a, run_id_b]),
            )
            .all()
        )
        if run.dataset.organization_id == organization_id
    }

    if run_id_a not in runs or run_id_b not in runs:
        raise RunNotFound("One or both runs were not found in this organization.")

    diff = compare_analysis_results(
        _as_engine_result(runs[run_id_a]), _as_engine_result(runs[run_id_b])
    )
    diff["previous_run_id"] = run_id_a
    diff["current_run_id"] = run_id_b
    return diff
