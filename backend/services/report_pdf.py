"""
services.report_pdf

Builds a downloadable/shareable PDF quality report for one AnalysisRun.
Uses reportlab's Platypus layer (SimpleDocTemplate + flowables) rather
than raw Canvas drawing, since the report has real structure (title,
score, tables, wrapped paragraphs) that Platypus handles for free -
pagination, text wrapping, and table layout would all be manual work
with Canvas.

Colors match the frontend's Tailwind design tokens (see
frontend/tailwind.config.js) so a report someone downloads looks like
it came from the same product as the dashboard.
"""

import io
from datetime import datetime, timezone

from reportlab.graphics.shapes import Drawing, Path, Rect
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

NAVY = colors.HexColor("#0B2545")
CYAN = colors.HexColor("#17B6E0")
MUTED = colors.HexColor("#6B7686")
BORDER = colors.HexColor("#E3E7EE")
SUCCESS = colors.HexColor("#1BAA5E")
WARNING = colors.HexColor("#F5A623")
DANGER = colors.HexColor("#E0524C")

# reportlab's paragraph markup wants "#rrggbb", not the "0xrrggbb" that
# Color.hexval() returns - using hexval() directly in <font color="...">
# tags silently breaks the parser and can misrender the surrounding
# text (this actually happened - a stray line through the score text -
# before this was switched to plain hex strings).
NAVY_HEX = "#0B2545"
CYAN_HEX = "#17B6E0"
MUTED_HEX = "#6B7686"
SUCCESS_HEX = "#1BAA5E"
WARNING_HEX = "#F5A623"
DANGER_HEX = "#E0524C"

LABEL_HEX = {
    "Strong": SUCCESS_HEX,
    "Moderate": CYAN_HEX,
    "Weak": WARNING_HEX,
    "Poor": DANGER_HEX,
}

SEVERITY_HEX = {
    "Critical": DANGER_HEX,
    "Warning": WARNING_HEX,
    "Good": SUCCESS_HEX,
}

# The prototype's exact shield-with-rising-bars mark (viewBox "0 0 58
# 62"), redrawn as vector shapes so it stays crisp at any size instead
# of embedding a raster image. Coordinates below are the SVG path/rect
# values from the prototype, y-flipped once (reportlab's origin is
# bottom-left, SVG's is top-left) - see frontend/src/components/Logo.jsx
# for the SVG version these must stay in sync with.
_SHIELD_FILL = colors.HexColor("#103A6B")
_BAR_MID = colors.HexColor("#3DD3F0")


def _logo_drawing(target_width=22):
    scale = target_width / 58.0

    def sx(v):
        return v * scale

    drawing = Drawing(target_width, 62 * scale)

    shield = Path(fillColor=_SHIELD_FILL, strokeColor=CYAN, strokeWidth=max(0.75, 2 * scale))
    shield.moveTo(sx(29), sx(60))
    shield.lineTo(sx(52), sx(51))
    shield.curveTo(sx(52), sx(32), sx(46), sx(15), sx(29), sx(2))
    shield.curveTo(sx(12), sx(15), sx(6), sx(32), sx(6), sx(51))
    shield.closePath()
    drawing.add(shield)

    bar_base_y = sx(18)
    drawing.add(Rect(sx(20), bar_base_y, sx(5.5), sx(10), fillColor=CYAN, strokeColor=None))
    drawing.add(Rect(sx(27.5), bar_base_y, sx(5.5), sx(16), fillColor=_BAR_MID, strokeColor=None))
    drawing.add(Rect(sx(35), bar_base_y, sx(5.5), sx(24), fillColor=colors.white, strokeColor=None))

    return drawing


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("ReportTitle", parent=base["Title"], textColor=NAVY, fontSize=20),
        "subtitle": ParagraphStyle("Subtitle", parent=base["Normal"], textColor=MUTED, fontSize=10),
        "h2": ParagraphStyle("H2", parent=base["Heading2"], textColor=NAVY, spaceBefore=18, spaceAfter=8),
        "body": ParagraphStyle("Body", parent=base["Normal"], fontSize=9.5, leading=13),
        "cell": ParagraphStyle("Cell", parent=base["Normal"], fontSize=8.5, leading=11),
        "footer": ParagraphStyle("Footer", parent=base["Normal"], fontSize=7.5, textColor=MUTED),
        # Explicit, generous leading matching each one's actual font
        # size - mixing a big inline <font size="28"> inside a
        # normal-leading Paragraph made reportlab compute too short a
        # row height, so the table border ended up drawn through the
        # middle of the oversized text. Giving the score its own
        # correctly-sized style (and a separate Paragraph for the
        # "/100" part, stacked rather than inlined) avoids that.
        "score_big": ParagraphStyle("ScoreBig", parent=base["Normal"], fontSize=30, leading=34, textColor=NAVY),
        "score_unit": ParagraphStyle("ScoreUnit", parent=base["Normal"], fontSize=10, leading=13, textColor=MUTED),
        "score_label": ParagraphStyle("ScoreLabel", parent=base["Normal"], fontSize=13, leading=16),
    }


def build_pdf_report(run) -> bytes:
    """
    `run` is an AnalysisRun ORM instance (or any object with the same
    attributes - score, score_label, filename, profile, issues,
    dimension_scores, dimension_weights, score_explanation,
    recommendations, issue_counts, created_at, dataset.name).

    Returns the PDF file's raw bytes.
    """
    styles = _styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        title=f"Data Reliability Report — {run.filename}",
    )

    story = []
    header_text = [
        Paragraph("Trusted Data Power", styles["subtitle"]),
        Paragraph("Data Reliability Report", styles["title"]),
    ]
    header_table = Table([[_logo_drawing(28), header_text]], colWidths=[0.45 * inch, 6.3 * inch])
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("LEFTPADDING", (1, 0), (1, 0), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(header_table)
    story.append(Spacer(1, 4))
    generated_at = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")
    story.append(
        Paragraph(
            f"{run.dataset.name} &middot; {run.filename} &middot; analyzed "
            f"{run.created_at.strftime('%B %d, %Y')} &middot; report generated {generated_at}",
            styles["subtitle"],
        )
    )
    story.append(Spacer(1, 16))

    story.append(_score_summary_table(run, styles))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Dataset overview", styles["h2"]))
    story.append(_overview_table(run, styles))

    story.append(Paragraph("Score breakdown by dimension", styles["h2"]))
    story.append(_dimension_table(run, styles))

    story.append(Paragraph("Why this score", styles["h2"]))
    for sentence in run.score_explanation:
        story.append(Paragraph(f"&bull; {sentence}", styles["body"]))
        story.append(Spacer(1, 3))

    story.append(Paragraph("Top recommendations", styles["h2"]))
    if run.recommendations:
        for rec in run.recommendations:
            story.append(Paragraph(f"&bull; {rec}", styles["body"]))
            story.append(Spacer(1, 3))
    else:
        story.append(Paragraph("No high-priority recommendations.", styles["body"]))

    story.append(Paragraph("Findings", styles["h2"]))
    actionable_issues = [i for i in run.issues if i.get("severity") != "Good"]
    if actionable_issues:
        story.append(_findings_table(actionable_issues, styles))
    else:
        story.append(Paragraph("No issues were detected.", styles["body"]))

    story.append(Spacer(1, 20))
    story.append(
        Paragraph(
            "This report summarizes measurable structural data-quality signals "
            "(missingness, duplicates, type consistency, outliers, formatting "
            "consistency). It is not a measure of factual correctness or truth, "
            "and not a guarantee the dataset is fit for any particular purpose.",
            styles["footer"],
        )
    )

    doc.build(story)
    return buffer.getvalue()


def _score_summary_table(run, styles):
    label_hex = LABEL_HEX.get(run.score_label, MUTED_HEX)
    score_number = Paragraph(f"<b>{run.score}</b>", styles["score_big"])
    score_unit = Paragraph("out of 100", styles["score_unit"])
    label_cell = Paragraph(
        f'<font color="{label_hex}"><b>{run.score_label}</b></font>', styles["score_label"]
    )
    counts = run.issue_counts
    counts_cell = Paragraph(
        f'<font color="{DANGER_HEX}"><b>{counts.get("Critical", 0)}</b></font> critical &nbsp;&nbsp;'
        f'<font color="{WARNING_HEX}"><b>{counts.get("Warning", 0)}</b></font> warning &nbsp;&nbsp;'
        f'<font color="{SUCCESS_HEX}"><b>{counts.get("Good", 0)}</b></font> good',
        styles["cell"],
    )

    table = Table(
        [[[score_number, score_unit], label_cell, counts_cell]],
        colWidths=[1.6 * inch, 2.2 * inch, 3.1 * inch],
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOX", (0, 0), (-1, -1), 1, BORDER),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F4F6F8")),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    return table


def _overview_table(run, styles):
    profile = run.profile
    rows = [
        ["Rows", f"{profile['n_rows']:,}", "Columns", str(profile["n_columns"])],
        [
            "Missing cells",
            f"{profile['missing_cells_pct']}% ({profile['total_missing_cells']:,} cells)",
            "Duplicate rows",
            f"{profile['duplicate_rows_pct']}% ({profile['duplicate_rows']:,} rows)",
        ],
    ]
    table_rows = [
        [
            Paragraph(f"<b>{a}</b>", styles["cell"]),
            Paragraph(b, styles["cell"]),
            Paragraph(f"<b>{c}</b>", styles["cell"]),
            Paragraph(d, styles["cell"]),
        ]
        for a, b, c, d in rows
    ]
    table = Table(table_rows, colWidths=[1.1 * inch, 2.3 * inch, 1.1 * inch, 2.4 * inch])
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _dimension_table(run, styles):
    header = [Paragraph("<b>Dimension</b>", styles["cell"]), Paragraph("<b>Score</b>", styles["cell"]), Paragraph("<b>Weight</b>", styles["cell"])]
    rows = [header]
    for dimension, score in run.dimension_scores.items():
        weight = run.dimension_weights.get(dimension, 0)
        rows.append(
            [
                Paragraph(dimension, styles["cell"]),
                Paragraph(f"{round(score, 1)} / 100", styles["cell"]),
                Paragraph(f"{round(weight * 100)}%", styles["cell"]),
            ]
        )

    table = Table(rows, colWidths=[3.2 * inch, 1.8 * inch, 1.9 * inch])
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _findings_table(issues, styles):
    header = [
        Paragraph("<b>Category</b>", styles["cell"]),
        Paragraph("<b>Severity</b>", styles["cell"]),
        Paragraph("<b>Column(s)</b>", styles["cell"]),
        Paragraph("<b>Recommendation</b>", styles["cell"]),
    ]
    rows = [header]
    for issue in issues:
        severity = issue.get("severity", "")
        color_hex = SEVERITY_HEX.get(severity, MUTED_HEX)
        rows.append(
            [
                Paragraph(issue.get("category", ""), styles["cell"]),
                Paragraph(f'<font color="{color_hex}"><b>{severity}</b></font>', styles["cell"]),
                Paragraph(", ".join(issue.get("columns") or []) or "—", styles["cell"]),
                Paragraph(issue.get("recommendation", ""), styles["cell"]),
            ]
        )

    table = Table(rows, colWidths=[1.5 * inch, 0.8 * inch, 1.3 * inch, 3.3 * inch], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table
