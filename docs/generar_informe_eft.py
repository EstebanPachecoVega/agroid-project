"""Genera el PDF del informe EFT desde Markdown.

Soporta portada, índice, encabezados, tablas, imágenes con pie, listas,
bloques de código, enlaces y saltos de página. Usa reportlab y no requiere
Pandoc ni LaTeX.

Uso:
    python docs/generar_informe_eft.py
    python docs/generar_informe_eft.py docs/INFORME_EFT.md docs/INFORME_EFT.pdf
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "docs" / "INFORME_EFT.md"
DEFAULT_OUTPUT = ROOT / "docs" / "INFORME_EFT.pdf"
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 2.0 * cm
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN
LAND_W, LAND_H = landscape(A4)
LAND_CONTENT_WIDTH = LAND_W - 2 * MARGIN


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _inline(text: str) -> str:
    text = _escape(text)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r'<link href="\2" color="#1d4ed8">\1</link>',
        text,
    )
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`([^`]+)`", r'<font name="Courier" size="8">\1</font>', text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", text)
    return text


class Heading(Paragraph):
    def __init__(self, text: str, style: ParagraphStyle, level: int):
        super().__init__(_inline(text), style)
        self._toc = (level, text)


class EFTDoc(BaseDocTemplate):
    def __init__(self, filename: str, **kwargs):
        super().__init__(filename, **kwargs)
        self.toc = TableOfContents()
        self.toc.levelStyles = [
            ParagraphStyle(
                name="TOC1",
                fontName="Helvetica-Bold",
                fontSize=9.2,
                leading=13,
                leftIndent=0,
                rightIndent=10,
                firstLineIndent=0,
                spaceBefore=4,
                spaceAfter=1,
            ),
            ParagraphStyle(
                name="TOC2",
                fontName="Helvetica",
                fontSize=8.4,
                leading=11,
                leftIndent=14,
                rightIndent=10,
                firstLineIndent=0,
                textColor=colors.HexColor("#374151"),
            ),
        ]

    def afterFlowable(self, flowable):
        if hasattr(flowable, "_toc"):
            level, text = flowable._toc
            self.notify("TOCEntry", (level, text, self.page))


def _styles():
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "TitleCover",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=23,
            leading=28,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#111827"),
            spaceAfter=12,
        ),
        "subtitle": ParagraphStyle(
            "SubtitleCover",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#374151"),
            spaceAfter=6,
        ),
        "cover_meta": ParagraphStyle(
            "CoverMeta",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=14,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#4b5563"),
            spaceAfter=2,
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=19,
            spaceBefore=14,
            spaceAfter=6,
            textColor=colors.HexColor("#111827"),
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11.5,
            leading=15,
            spaceBefore=10,
            spaceAfter=4,
            textColor=colors.HexColor("#1f2937"),
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "H3",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            spaceBefore=7,
            spaceAfter=3,
            textColor=colors.HexColor("#374151"),
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.1,
            leading=12.3,
            alignment=TA_JUSTIFY,
            spaceAfter=4,
        ),
        "reference": ParagraphStyle(
            "Reference",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8.7,
            leading=11.4,
            alignment=0,
            leftIndent=14,
            firstLineIndent=-14,
            spaceAfter=3,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.0,
            leading=12.0,
            leftIndent=12,
            spaceAfter=2,
        ),
        "quote": ParagraphStyle(
            "Quote",
            parent=base["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=8.8,
            leading=11.8,
            leftIndent=14,
            rightIndent=8,
            textColor=colors.HexColor("#4b5563"),
            spaceAfter=5,
        ),
        "caption": ParagraphStyle(
            "Caption",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=7.8,
            leading=10,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#4b5563"),
            spaceBefore=2,
            spaceAfter=8,
        ),
        "code": ParagraphStyle(
            "Code",
            parent=base["Code"],
            fontName="Courier",
            fontSize=7.2,
            leading=8.8,
            leftIndent=6,
            backColor=colors.HexColor("#f3f4f6"),
            borderPadding=4,
            spaceBefore=3,
            spaceAfter=7,
        ),
        "table_header": ParagraphStyle(
            "TableHeader",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=6.4,
            leading=7.7,
        ),
        "table_body": ParagraphStyle(
            "TableBody",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=6.3,
            leading=7.6,
        ),
    }
    return styles


def _table(rows: list[list[str]], styles: dict) -> Table | None:
    if len(rows) < 2:
        return None
    header, body = rows[0], rows[1:]
    body = [
        row
        for row in body
        if not all(set(cell.strip()) <= {"-", ":", " "} for cell in row)
    ]
    columns = max(len(header), max((len(row) for row in body), default=0))
    header = header + [""] * (columns - len(header))
    body = [row + [""] * (columns - len(row)) for row in body]
    data = [[Paragraph(_inline(cell), styles["table_header"]) for cell in header]]
    for row in body:
        data.append([Paragraph(_inline(cell), styles["table_body"]) for cell in row])
    weights = []
    for column in range(columns):
        values = [header[column]] + [row[column] for row in body]
        longest = max(len(str(value)) for value in values)
        weights.append(max(7, min(38, longest)))
    total = sum(weights) or 1
    widths = [CONTENT_WIDTH * weight / total for weight in weights]
    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#9ca3af")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2.5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2.5),
                ("TOPPADDING", (0, 0), (-1, -1), 1.8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.8),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#f9fafb")],
                ),
            ]
        )
    )
    return table


def _image_flowable(
    path: Path,
    alt: str,
    styles: dict,
    content_width: float = CONTENT_WIDTH,
    max_height: float = 11.0 * cm,
):
    if not path.exists():
        return Paragraph(
            f"<i>[Figura no disponible: {_escape(str(path))}]</i>",
            styles["caption"],
        )
    try:
        image = Image(str(path))
        ratio = image.imageHeight / image.imageWidth
        width = content_width
        height = width * ratio
        if height > max_height:
            height = max_height
            width = height / ratio
        image.drawWidth = width
        image.drawHeight = height
        image.hAlign = "CENTER"
        caption = Paragraph(_inline(alt), styles["caption"])
        caption.hAlign = "CENTER"
        return KeepTogether([image, caption])
    except Exception as exc:
        return Paragraph(
            f"<i>[No se pudo cargar la figura: {_escape(str(exc))}]</i>",
            styles["caption"],
        )


def _cover(lines: list[str], styles: dict):
    story = [Spacer(1, 1.2 * cm)]
    title = ""
    meta: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("# "):
            title = stripped[2:].strip()
        elif stripped.startswith(">"):
            meta.append(stripped.lstrip("> ").strip())
        else:
            meta.append(stripped)
    story.append(
        Paragraph(
            '<font color="#1d4ed8">ISY0101 · Ingeniería de Soluciones con IA</font>',
            styles["subtitle"],
        )
    )
    story.append(Spacer(1, 0.8 * cm))
    story.append(Paragraph(_inline(title), styles["title"]))
    story.append(Spacer(1, 0.4 * cm))
    story.append(
        HRFlowable(width="60%", thickness=1.2, color=colors.HexColor("#1d4ed8"))
    )
    story.append(Spacer(1, 0.6 * cm))
    story.append(
        Paragraph(
            "<b>Evaluación Final Transversal (EFT)</b>",
            styles["subtitle"],
        )
    )
    story.append(Spacer(1, 0.7 * cm))
    for item in meta:
        story.append(Paragraph(_inline(item), styles["cover_meta"]))
    story.append(Spacer(1, 1.2 * cm))
    story.append(
        Paragraph(
            "Informe académico · Caso verosímil con datos simulados",
            styles["cover_meta"],
        )
    )
    story.append(PageBreak())
    return story


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.2)
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.drawString(MARGIN, 1.0 * cm, "AgroID Huevos · Informe EFT ISY0101")
    canvas.drawRightString(
        PAGE_WIDTH - MARGIN, 1.0 * cm, f"Página {doc.page}"
    )
    canvas.restoreState()


def _footer_landscape(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.2)
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.drawString(MARGIN, 1.0 * cm, "AgroID Huevos · Informe EFT ISY0101")
    canvas.drawRightString(
        LAND_W - MARGIN, 1.0 * cm, f"Página {doc.page}"
    )
    canvas.restoreState()


def build(source: Path, output: Path) -> int:
    text = source.read_text(encoding="utf-8")
    lines = text.splitlines()
    styles = _styles()

    first_section = next(
        (index for index, line in enumerate(lines) if line.startswith("## ")),
        len(lines),
    )
    cover_lines = lines[:first_section]
    body_lines = lines[first_section:]

    story: list = []
    story.extend(_cover(cover_lines, styles))

    # Índice
    story.append(Paragraph("Índice", styles["h1"]))
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle(
            name="TOC1",
            fontName="Helvetica-Bold",
            fontSize=9.0,
            leading=12.5,
            leftIndent=0,
            rightIndent=10,
            spaceBefore=4,
            spaceAfter=1,
        ),
        ParagraphStyle(
            name="TOC2",
            fontName="Helvetica",
            fontSize=8.2,
            leading=10.8,
            leftIndent=14,
            rightIndent=10,
            textColor=colors.HexColor("#374151"),
        ),
    ]
    story.append(toc)
    story.append(PageBreak())

    paragraph: list[str] = []
    bullets: list[tuple[str, str]] = []
    table_lines: list[str] = []
    code_lines: list[str] = []
    in_code = False
    in_references = False
    in_landscape = False

    def flush_paragraph():
        nonlocal paragraph
        if paragraph:
            style = styles["reference"] if in_references else styles["body"]
            story.append(
                Paragraph(_inline(" ".join(paragraph)), style)
            )
            paragraph = []

    def flush_bullets():
        nonlocal bullets
        if bullets:
            for kind, item in bullets:
                prefix = "• " if kind == "bullet" else ""
                story.append(
                    Paragraph(prefix + _inline(item), styles["bullet"])
                )
            story.append(Spacer(1, 2))
            bullets = []

    def flush_table():
        nonlocal table_lines
        if table_lines:
            rows = [
                [cell.strip() for cell in line.strip().strip("|").split("|")]
                for line in table_lines
            ]
            rendered = _table(rows, styles)
            if rendered is not None:
                if len(rows) <= 10:
                    story.append(KeepTogether([rendered, Spacer(1, 6)]))
                else:
                    story.append(rendered)
                    story.append(Spacer(1, 6))
            table_lines = []

    for raw in body_lines:
        line = raw.rstrip()
        if line.startswith("```"):
            if in_code:
                story.append(
                    Preformatted(
                        "\n".join(code_lines),
                        styles["code"],
                    )
                )
                code_lines = []
                in_code = False
            else:
                flush_paragraph()
                flush_bullets()
                flush_table()
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue
        if not line.strip():
            flush_paragraph()
            flush_bullets()
            flush_table()
            continue
        if line.strip() == "<!-- landscape:start -->":
            flush_paragraph()
            flush_bullets()
            flush_table()
            in_landscape = True
            story.append(NextPageTemplate("landscape"))
            story.append(PageBreak())
            continue
        if line.strip() == "<!-- landscape:end -->":
            flush_paragraph()
            flush_bullets()
            flush_table()
            in_landscape = False
            story.append(NextPageTemplate("content"))
            story.append(PageBreak())
            continue
        if line.strip() == "<!-- pagebreak -->":
            flush_paragraph()
            flush_bullets()
            flush_table()
            story.append(PageBreak())
            continue
        image_match = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", line.strip())
        if image_match:
            flush_paragraph()
            flush_bullets()
            flush_table()
            alt, src = image_match.groups()
            path = (source.parent / src).resolve()
            if in_landscape:
                story.append(
                    _image_flowable(
                        path,
                        alt,
                        styles,
                        content_width=LAND_CONTENT_WIDTH,
                        max_height=15.2 * cm,
                    )
                )
            else:
                story.append(_image_flowable(path, alt, styles))
            continue
        if line.startswith("|"):
            flush_paragraph()
            flush_bullets()
            table_lines.append(line)
            continue
        flush_table()
        if line.startswith("## "):
            flush_paragraph()
            flush_bullets()
            heading_text = line[3:].strip()
            in_references = heading_text.startswith("9. Referencias")
            if heading_text == "Anexos":
                in_references = False
            heading = Heading(heading_text, styles["h1"], 0)
            story.append(heading)
        elif line.startswith("### "):
            flush_paragraph()
            flush_bullets()
            heading = Heading(line[4:].strip(), styles["h2"], 1)
            story.append(heading)
        elif line.startswith("#### "):
            flush_paragraph()
            flush_bullets()
            heading = Heading(line[5:].strip(), styles["h3"], 1)
            story.append(heading)
        elif line.startswith(">"):
            flush_paragraph()
            flush_bullets()
            story.append(
                Paragraph(_inline(line.lstrip("> ").strip()), styles["quote"])
            )
        elif line.startswith("- ") or line.startswith("* "):
            flush_paragraph()
            bullets.append(("bullet", line[2:].strip()))
        elif re.match(r"^\d+\.\s+", line):
            flush_paragraph()
            match = re.match(r"^(\d+)\.\s+(.*)$", line)
            if match:
                bullets.append(("number", f"{match.group(1)}. {match.group(2)}"))
        elif line.strip() in {"---", "***"}:
            flush_paragraph()
            flush_bullets()
            story.append(
                HRFlowable(
                    width="100%",
                    thickness=0.5,
                    color=colors.HexColor("#d1d5db"),
                )
            )
            story.append(Spacer(1, 4))
        else:
            paragraph.append(line.strip())

    flush_paragraph()
    flush_bullets()
    flush_table()
    if in_code and code_lines:
        story.append(Preformatted("\n".join(code_lines), styles["code"]))

    doc = EFTDoc(
        str(output),
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        title="AgroID Huevos - Informe EFT",
        author="Esteban Pacheco Vega y Javier Perez Mora",
        subject="Evaluación Final Transversal - ISY0101",
    )
    frame = Frame(
        MARGIN,
        1.8 * cm,
        CONTENT_WIDTH,
        PAGE_HEIGHT - 3.6 * cm,
        id="content",
    )
    land_frame = Frame(
        MARGIN,
        1.8 * cm,
        LAND_CONTENT_WIDTH,
        LAND_H - 3.6 * cm,
        id="landscape",
    )
    doc.addPageTemplates(
        [
            PageTemplate(id="content", frames=[frame], onPage=_footer),
            PageTemplate(
                id="landscape",
                frames=[land_frame],
                onPage=_footer_landscape,
                pagesize=landscape(A4),
            ),
        ]
    )
    doc.multiBuild(story)
    print(f"PDF: {output}")
    print(f"Páginas: {doc.page}")
    if doc.page < 15:
        print("ADVERTENCIA: el informe parece corto para la EFT.")
    if doc.page > 45:
        print("ADVERTENCIA: el informe es muy extenso; revisar tablas.")
    return doc.page


def main() -> int:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SOURCE
    output = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUTPUT
    if not source.exists():
        print(f"No existe: {source}")
        return 1
    build(source, output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
