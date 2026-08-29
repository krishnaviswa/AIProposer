"""Server-side PDF render from the structured proposal record (mvp-spec.md §3, §8).

No LLM. Pure `reportlab` — no system libraries, works in CI. The Free plan gets a
diagonal "NOT FOR SENDING" watermark on every page (mvp-spec.md §15).
"""

from __future__ import annotations

import io

from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    ListFlowable,
    ListItem,
    PageTemplate,
    Paragraph,
    Spacer,
)

from app.services.pricing import money  # display helper


def _watermark(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica-Bold", 60)
    canvas.setFillGray(0.85)
    canvas.translate(A4[0] / 2, A4[1] / 2)
    canvas.rotate(30)
    canvas.drawCentredString(0, 0, "NOT FOR SENDING")
    canvas.restoreState()


def render_proposal_pdf(proposal_json: dict, *, watermark: bool, client_name: str) -> bytes:
    buf = io.BytesIO()
    styles = getSampleStyleSheet()
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], spaceBefore=12, spaceAfter=4)
    body = ParagraphStyle("body", parent=styles["BodyText"], alignment=TA_LEFT, leading=14)

    doc = BaseDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title=f"Proposal for {client_name}",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    on_page = _watermark if watermark else (lambda c, d: None)
    doc.addPageTemplates([PageTemplate(id="tpl", frames=[frame], onPage=on_page)])

    pj = proposal_json or {}
    story: list = [Paragraph(f"Proposal for {client_name}", styles["Title"]), Spacer(1, 6)]

    def section(title: str, items: list[str]) -> None:
        story.append(Paragraph(title, h2))
        story.append(
            ListFlowable(
                [ListItem(Paragraph(x, body)) for x in items], bulletType="bullet", leftIndent=12
            )
        )

    if pj.get("executive_summary"):
        story += [Paragraph("Executive summary", h2), Paragraph(pj["executive_summary"], body)]
    if pj.get("scope_of_work"):
        section("Scope of work", pj["scope_of_work"])
    if pj.get("timeline"):
        section("Timeline", [f"<b>{t['label']}:</b> {t['detail']}" for t in pj["timeline"]])
    if pj.get("pricing"):
        rows = []
        for line in pj["pricing"]:
            amt = money(line["amount_minor"], line["currency"])
            j = f" &mdash; {line['justification']}" if line.get("justification") else ""
            rows.append(f"<b>{line['label']}: {amt}</b>{j}")
        section("Pricing", rows)
    if pj.get("terms"):
        section("Terms", pj["terms"])
    if not watermark and pj.get("followup_email"):
        story += [
            Paragraph("Follow-up email", h2),
            Paragraph(pj["followup_email"].replace("\n", "<br/>"), body),
        ]

    doc.build(story)
    return buf.getvalue()
