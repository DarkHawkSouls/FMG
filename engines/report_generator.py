"""
engines/report_generator.py
─────────────────────────────────────────────────────────────────────────────
Generates a downloadable PDF investment report from the analysis memo and
supporting financial metrics.

Requires: reportlab
Falls back to a styled Markdown file if reportlab is not available.
"""

from __future__ import annotations

import io
import re
from datetime import datetime
from pathlib import Path
from typing import Any

REPORT_DIR = Path(__file__).parent.parent / "output" / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# PDF generation (reportlab)
# ---------------------------------------------------------------------------
try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        HRFlowable,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    _REPORTLAB = True
except ImportError:
    _REPORTLAB = False


def _pdf_bytes(
    memo_markdown: str,
    metrics: dict[str, Any],
    project_type: str,
    industry: str,
) -> bytes:
    """Render the memo to a PDF and return raw bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=18,
        textColor=colors.HexColor("#1a237e"),
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#5c6e91"),
        spaceAfter=12,
    )
    h1_style = ParagraphStyle(
        "H1",
        parent=styles["Heading1"],
        fontSize=13,
        textColor=colors.HexColor("#1a237e"),
        spaceBefore=14,
        spaceAfter=4,
        borderPad=4,
    )
    h2_style = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontSize=11,
        textColor=colors.HexColor("#3949ab"),
        spaceBefore=10,
        spaceAfter=3,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=14,
        spaceAfter=6,
    )
    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=7.5,
        textColor=colors.grey,
        alignment=TA_CENTER,
    )

    story = []

    # ── Header ──
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("AI Financial Model Platform", title_style))
    story.append(
        Paragraph(
            f"Investment Analysis Report &nbsp;|&nbsp; {project_type} — {industry} Sector &nbsp;|&nbsp; "
            f"Generated: {datetime.now().strftime('%d %b %Y, %H:%M')}",
            subtitle_style,
        )
    )
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1a237e")))
    story.append(Spacer(1, 0.4 * cm))

    # ── Metrics Table ──
    from engines.metrics_extractor import METRIC_LABELS  # local import to avoid circular

    metric_rows = [["Metric", "Value"]]
    for key, label in METRIC_LABELS.items():
        val = metrics.get(key)
        if val is not None:
            metric_rows.append([label, f"{val:,.2f}"])

    if len(metric_rows) > 1:
        tbl = Table(metric_rows, colWidths=[10 * cm, 5 * cm])
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a237e")),
                    ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
                    ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE",   (0, 0), (-1, 0), 9),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f5f7ff"), colors.white]),
                    ("FONTSIZE",   (0, 1), (-1, -1), 9),
                    ("GRID",       (0, 0), (-1, -1), 0.4, colors.HexColor("#c5cae9")),
                    ("ALIGN",      (1, 0), (1, -1), "RIGHT"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(Paragraph("Key Financial Metrics", h1_style))
        story.append(tbl)
        story.append(Spacer(1, 0.5 * cm))

    # ── Memo body ──
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#c5cae9")))
    story.append(Spacer(1, 0.3 * cm))

    for line in memo_markdown.split("\n"):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 0.2 * cm))
        elif line.startswith("## "):
            story.append(Paragraph(line[3:], h1_style))
        elif line.startswith("### "):
            story.append(Paragraph(line[4:], h2_style))
        elif line.startswith("| "):
            # Markdown table — render as plain text (simplified)
            story.append(Paragraph(line.replace("|", " | "), body_style))
        elif line.startswith("**") and line.endswith("**"):
            story.append(
                Paragraph(f"<b>{line.strip('*')}</b>", body_style)
            )
        elif line.startswith("- ") or line.startswith("* "):
            story.append(Paragraph(f"&bull; {line[2:]}", body_style))
        elif line.startswith("#"):
            pass  # top-level h1 already rendered in header
        else:
            # Replace markdown bold
            clean = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", line)
            story.append(Paragraph(clean, body_style))

    # ── Footer ──
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Spacer(1, 0.2 * cm))
    story.append(
        Paragraph(
            "This report is generated by AI Financial Model Platform for informational "
            "purposes only and does not constitute investment advice.",
            footer_style,
        )
    )

    doc.build(story)
    buf.seek(0)
    return buf.read()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_pdf_report(
    memo_markdown: str,
    metrics: dict[str, Any],
    project_type: str,
    industry: str,
) -> tuple[bytes, str]:
    """
    Generate a PDF investment report.

    Returns:
        (file_bytes, filename)
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_pt = project_type.replace(" ", "_").lower()
    filename = f"investment_report_{safe_pt}_{timestamp}.pdf"

    if _REPORTLAB:
        pdf_bytes = _pdf_bytes(memo_markdown, metrics, project_type, industry)
    else:
        # Fallback: return UTF-8 markdown as bytes (still downloadable)
        header = (
            f"# Investment Analysis Report\n"
            f"## {project_type} — {industry} Sector\n"
            f"Generated: {datetime.now().strftime('%d %b %Y, %H:%M')}\n\n"
            "---\n\n"
        )
        pdf_bytes = (header + memo_markdown).encode("utf-8")
        filename = filename.replace(".pdf", ".md")

    # Save to disk
    out_path = REPORT_DIR / filename
    with open(out_path, "wb") as f:
        f.write(pdf_bytes)

    return pdf_bytes, filename


def is_pdf_available() -> bool:
    return _REPORTLAB
