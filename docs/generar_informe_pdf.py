"""Genera el PDF del informe EP3 desde Markdown y avisa si supera 5 páginas.

Uso:
    python docs/generar_informe_pdf.py
    python docs/generar_informe_pdf.py docs/INFORME_TECNICO_EP3.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "docs" / "INFORME_TECNICO_EP3.md"
DEFAULT_OUTPUT = ROOT / "docs" / "INFORME_TECNICO_EP3.pdf"
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 1.9 * cm
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN


def _inline(text: str) -> str:
    text = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r'<link href="\2" color="blue">\1</link>',
        text,
    )
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(
        r"`([^`]+)`",
        r'<font name="Courier" size="8">\1</font>',
        text,
    )
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", text)
    return text


def _table(rows: list[list[str]], styles: dict) -> Table | None:
    if len(rows) < 2:
        return None
    header, body = rows[0], rows[1:]
    body = [row for row in body if not all(set(cell) <= {"-", ":"} for cell in row)]
    columns = max(len(header), max((len(row) for row in body), default=0))
    header = header + [""] * (columns - len(header))
    body = [row + [""] * (columns - len(row)) for row in body]
    data = [
        [Paragraph(_inline(cell), styles["table_header"]) for cell in header]
    ]
    for row in body:
        data.append([Paragraph(_inline(cell), styles["table_body"]) for cell in row])
    weights = []
    for column in range(columns):
        values = [header[column]] + [row[column] for row in body]
        longest = max(len(str(value)) for value in values)
        weights.append(max(8, min(42, longest)))
    total = sum(weights) or 1
    widths = [CONTENT_WIDTH * weight / total for weight in weights]
    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9ca3af")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
            ]
        )
    )
    return table


def build(source: Path, output: Path) -> int:
    text = source.read_text(encoding="utf-8")
    lines = text.splitlines()

    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=21,
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["Normal"],
            fontSize=9,
            leading=12,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#374151"),
            spaceAfter=10,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12.5,
            leading=15,
            spaceBefore=10,
            spaceAfter=4,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "H3",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=13,
            spaceBefore=7,
            spaceAfter=3,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.3,
            leading=12.1,
            alignment=TA_JUSTIFY,
            spaceAfter=4,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.3,
            leading=12.1,
            leftIndent=10,
            spaceAfter=2,
        ),
        "quote": ParagraphStyle(
            "Quote",
            parent=base["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=9,
            leading=12,
            leftIndent=12,
            textColor=colors.HexColor("#4b5563"),
            spaceAfter=5,
        ),
        "code": ParagraphStyle(
            "Code",
            parent=base["Code"],
            fontName="Courier",
            fontSize=7.5,
            leading=9,
            leftIndent=8,
            backColor=colors.HexColor("#f3f4f6"),
            borderPadding=4,
            spaceAfter=6,
        ),
        "table_header": ParagraphStyle(
            "TableHeader",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=6.9,
            leading=8.2,
        ),
        "table_body": ParagraphStyle(
            "TableBody",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=6.9,
            leading=8.2,
        ),
        "footer": ParagraphStyle(
            "Footer",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            textColor=colors.HexColor("#6b7280"),
        ),
    }

    story: list = []
    paragraph_lines: list[str] = []
    bullet_lines: list[str] = []
    table_lines: list[str] = []
    code_lines: list[str] = []
    in_code = False

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        if paragraph_lines:
            story.append(Paragraph(_inline(" ".join(paragraph_lines)), styles["body"]))
            paragraph_lines = []

    def flush_bullets() -> None:
        nonlocal bullet_lines
        if bullet_lines:
            items = [
                ListItem(Paragraph(_inline(item), styles["bullet"]))
                for item in bullet_lines
            ]
            story.append(
                ListFlowable(
                    items,
                    bulletType="bullet",
                    start="•",
                    leftIndent=10,
                    bulletFontSize=8,
                )
            )
            story.append(Spacer(1, 3))
            bullet_lines = []

    def flush_table() -> None:
        nonlocal table_lines
        if table_lines:
            rows = [
                [cell.strip() for cell in line.strip().strip("|").split("|")]
                for line in table_lines
            ]
            rendered = _table(rows, styles)
            if rendered is not None:
                if len(rows) <= 8:
                    story.append(KeepTogether([rendered, Spacer(1, 6)]))
                else:
                    story.append(rendered)
                    story.append(Spacer(1, 6))
            table_lines = []

    for raw in lines:
        line = raw.rstrip()
        if line.startswith("```"):
            if in_code:
                story.append(Paragraph("<br/>".join(code_lines), styles["code"]))
                code_lines = []
                in_code = False
            else:
                flush_paragraph()
                flush_bullets()
                flush_table()
                in_code = True
            continue
        if in_code:
            code_lines.append(line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
            continue
        if line.startswith("|"):
            flush_paragraph()
            flush_bullets()
            table_lines.append(line)
            continue
        flush_table()
        if line.startswith("# "):
            flush_paragraph()
            flush_bullets()
            story.append(Paragraph(_inline(line[2:].strip()), styles["title"]))
        elif line.startswith("## "):
            flush_paragraph()
            flush_bullets()
            story.append(Paragraph(_inline(line[3:].strip()), styles["h2"]))
        elif line.startswith("### "):
            flush_paragraph()
            flush_bullets()
            story.append(Paragraph(_inline(line[4:].strip()), styles["h3"]))
        elif line.startswith("> "):
            flush_paragraph()
            flush_bullets()
            story.append(Paragraph(_inline(line[2:].strip()), styles["quote"]))
        elif line.startswith("- "):
            flush_paragraph()
            bullet_lines.append(line[2:].strip())
        elif re.match(r"^\d+\.\s+", line):
            flush_paragraph()
            bullet_lines.append(re.sub(r"^\d+\.\s+", "", line).strip())
        elif line.strip() in {"---", "***"}:
            flush_paragraph()
            flush_bullets()
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#d1d5db")))
            story.append(Spacer(1, 4))
        elif not line.strip():
            flush_paragraph()
            flush_bullets()
        else:
            paragraph_lines.append(line.strip())

    flush_paragraph()
    flush_bullets()
    flush_table()
    if in_code and code_lines:
        story.append(Paragraph("<br/>".join(code_lines), styles["code"]))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#6b7280"))
        canvas.drawString(MARGIN, 1.0 * cm, "AgroID Huevos · EP3 Observabilidad")
        canvas.drawRightString(
            PAGE_WIDTH - MARGIN, 1.0 * cm, f"Página {doc.page}"
        )
        canvas.restoreState()

    doc = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm,
        title="AgroID Huevos - EP3 Observabilidad",
        author="Esteban Pacheco Vega y Javier Perez Mora",
        subject="Evaluación Parcial N°3 - ISY0101",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(f"PDF: {output}")
    print(f"Páginas: {doc.page}")
    if doc.page > 5:
        print("ADVERTENCIA: el informe supera el límite de 5 páginas.")
    return doc.page


def main() -> int:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SOURCE
    output = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUTPUT
    if not source.exists():
        print(f"No existe: {source}")
        return 1
    pages = build(source, output)
    return 0 if pages <= 5 else 2


if __name__ == "__main__":
    raise SystemExit(main())
