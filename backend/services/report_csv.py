"""
services.report_csv

Builds a CSV export of one AnalysisRun's findings - the same data the
Findings page shows in the UI, in a format someone can open directly
in Excel/Sheets. Uses the stdlib csv module rather than pandas: this
is plain tabular output with no numeric computation, so pandas would
be an unnecessary dependency here even though it's already in the
engine.
"""

import csv
import io


def build_csv_report(run) -> str:
    """
    `run` needs .filename, .score, .score_label, and .issues (list of
    dicts with category/severity/columns/metric/explanation/
    recommendation - the same shape the engine produces).

    Returns the CSV content as a string.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    writer.writerow(["Dataset", run.dataset.name])
    writer.writerow(["File", run.filename])
    writer.writerow(["Score", run.score])
    writer.writerow(["Score label", run.score_label])
    writer.writerow([])

    writer.writerow(["Category", "Severity", "Column(s)", "Metric", "Explanation", "Recommendation"])
    for issue in run.issues:
        writer.writerow(
            [
                issue.get("category", ""),
                issue.get("severity", ""),
                ", ".join(issue.get("columns") or []),
                issue.get("metric", ""),
                issue.get("explanation", ""),
                issue.get("recommendation", ""),
            ]
        )

    return buffer.getvalue()
