"""
report_generator.py

Generates a downloadable PDF report summarizing a contract's analysis
results, using reportlab (pure-Python, no system dependencies required).
"""
from __future__ import annotations

from io import BytesIO
from typing import Dict

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)

RISK_COLORS = {
    "LOW": colors.HexColor("#3F6B4F"),
    "MEDIUM": colors.HexColor("#C08A2E"),
    "HIGH": colors.HexColor("#B3541E"),
    "CRITICAL": colors.HexColor("#9B2226"),
    "NONE": colors.HexColor("#6B7280"),
}

INK = colors.HexColor("#14213D")
MUTED = colors.HexColor("#4A5568")


def _styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ReportTitle", fontSize=20, textColor=INK, spaceAfter=4, fontName="Helvetica-Bold"
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportSubtitle", fontSize=10, textColor=MUTED, spaceAfter=14
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionHeading", fontSize=13, textColor=INK, spaceBefore=16, spaceAfter=8, fontName="Helvetica-Bold"
        )
    )
    styles.add(ParagraphStyle(name="BodySmall", fontSize=9.5, textColor=colors.HexColor("#1F2937"), leading=14))
    styles.add(ParagraphStyle(name="Disclaimer", fontSize=8, textColor=MUTED, leading=11))
    return styles


def generate_pdf_report(contract: Dict) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=18 * mm,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        title=f"Contract Analysis Report - {contract.get('file_name', 'contract')}",
    )
    styles = _styles()
    story = []

    # --- Header -------------------------------------------------------
    story.append(Paragraph("AI Contract Review &amp; Risk Analyzer", styles["ReportTitle"]))
    story.append(Paragraph("Automated Contract Analysis Report", styles["ReportSubtitle"]))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#D1D5DB"), thickness=1))
    story.append(Spacer(1, 10))

    meta_table = Table(
        [
            ["Contract Name:", contract.get("file_name", "-")],
            ["Analysis Date:", contract.get("upload_date", "-")],
            ["Overall Risk Score:", f"{contract.get('risk_score', 0)} / 100"],
            ["Risk Classification:", contract.get("risk_level", "-")],
        ],
        colWidths=[110, 350],
    )
    meta_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                ("TEXTCOLOR", (0, 0), (0, -1), INK),
                ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#1F2937")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 6))

    # --- Summary --------------------------------------------------------
    story.append(Paragraph("Contract Summary", styles["SectionHeading"]))
    story.append(Paragraph(contract.get("summary", "No summary available."), styles["BodySmall"]))

    # --- Clause analysis --------------------------------------------------------
    story.append(Paragraph("Clause Analysis", styles["SectionHeading"]))
    clause_rows = [["Clause", "Status", "Risk Level", "Confidence"]]
    for clause in contract.get("clauses", []):
        clause_rows.append(
            [
                clause.get("clause_name", "-"),
                "Found" if clause.get("found") else "Missing",
                clause.get("risk_level", "-"),
                f"{clause.get('confidence', 0)}%",
            ]
        )
    clause_table = Table(clause_rows, colWidths=[160, 80, 90, 90], repeatRows=1)
    clause_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), INK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F9FB")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(clause_table)

    # --- Detected risks --------------------------------------------------------
    story.append(Paragraph("Detected Risks", styles["SectionHeading"]))
    risks = contract.get("risks", [])
    if not risks:
        story.append(Paragraph("No significant risks were detected.", styles["BodySmall"]))
    else:
        for risk in risks:
            level = risk.get("risk_level", "LOW")
            color = RISK_COLORS.get(level, MUTED)
            title_style = ParagraphStyle(
                name=f"RiskTitle-{risk.get('risk_id', '')}",
                parent=styles["BodySmall"],
                textColor=color,
                fontName="Helvetica-Bold",
                fontSize=10.5,
                spaceBefore=8,
            )
            story.append(Paragraph(f"[{level}] {risk.get('risk_title', '')}", title_style))
            story.append(Paragraph(risk.get("description", ""), styles["BodySmall"]))
            story.append(
                Paragraph(f"<b>Recommendation:</b> {risk.get('recommendation', '')}", styles["BodySmall"])
            )

    # --- Recommendations --------------------------------------------------------
    story.append(Paragraph("Final Recommendations", styles["SectionHeading"]))
    for rec in contract.get("recommendations", []):
        story.append(Paragraph(f"&bull; {rec}", styles["BodySmall"]))

    # --- Disclaimer --------------------------------------------------------
    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#D1D5DB"), thickness=1))
    story.append(Spacer(1, 6))
    story.append(
        Paragraph(
            "AI-generated analysis for informational purposes only. This is not legal advice. "
            "This report was produced by an automated rule-based / AI-assisted system and should "
            "be reviewed by a qualified legal professional before making any decisions.",
            styles["Disclaimer"],
        )
    )

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
