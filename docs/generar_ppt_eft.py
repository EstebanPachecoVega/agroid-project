"""Genera el deck PPTX de defensa EFT replicando el sistema visual de la EP3.

El deck final es un archivo nuevo con el mismo lenguaje visual: 20 x 11,25 in,
navy #0B2545, amarillo #FDB913, Calibri, barra lateral y pie de página. La
portada reutiliza los activos visuales de la PPTX EP3.

Uso:
    python docs/generar_ppt_eft.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "defensa_eft" / "diapositivas.pptx"
EVID = ROOT / "docs" / "defensa_eft" / "evidencias"

NAVY = RGBColor(0x0B, 0x25, 0x45)
NAVY_2 = RGBColor(0x13, 0x35, 0x5C)
YELLOW = RGBColor(0xFD, 0xB9, 0x13)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GRAY = RGBColor(0x64, 0x74, 0x8B)
LIGHT = RGBColor(0xF4, 0xF6, 0xFA)
LINE = RGBColor(0xE2, 0xE8, 0xF0)
INK = RGBColor(0x1F, 0x29, 0x37)
BLUE = RGBColor(0x1D, 0x4E, 0xD8)
TEAL = RGBColor(0x0F, 0x76, 0x6E)
AMBER = RGBColor(0xB4, 0x53, 0x09)
RED = RGBColor(0xB9, 0x1C, 0x1C)
PURPLE = RGBColor(0x6D, 0x28, 0xD9)
PALE_BLUE = RGBColor(0xDB, 0xEA, 0xFE)
PALE_GREEN = RGBColor(0xD1, 0xFA, 0xE5)
PALE_AMBER = RGBColor(0xFE, 0xF3, 0xC7)
PALE_RED = RGBColor(0xFE, 0xE2, 0xE2)
PALE_PURPLE = RGBColor(0xED, 0xE9, 0xFE)

FONT = "Calibri"
MONO = "Consolas"


# ---------------------------------------------------------------------------
# Helpers de dibujo
# ---------------------------------------------------------------------------
def _set_fill(shape, color: RGBColor) -> None:
    shape.fill.solid()
    shape.fill.fore_color.rgb = color


def _set_line(shape, color: RGBColor | None, width: float = 0.9) -> None:
    if color is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = color
        shape.line.width = Pt(width)


def _strip_style(shape) -> None:
    """Quita el estilo de tema (sombra, relleno y línea) para un look plano."""
    from pptx.oxml.ns import qn

    style = shape._element.find(qn("p:style"))
    if style is not None:
        shape._element.remove(style)


def rect(
    slide,
    x: float,
    y: float,
    w: float,
    h: float,
    fill: RGBColor = LIGHT,
    line: RGBColor | None = LINE,
    radius: float = 0.06,
    shape_type=MSO_SHAPE.ROUNDED_RECTANGLE,
):
    shape = slide.shapes.add_shape(
        shape_type, Inches(x), Inches(y), Inches(w), Inches(h)
    )
    if shape_type == MSO_SHAPE.ROUNDED_RECTANGLE:
        try:
            shape.adjustments[0] = radius
        except Exception:
            pass
    _set_fill(shape, fill)
    _set_line(shape, line)
    shape.shadow.inherit = False
    _strip_style(shape)
    shape.text_frame.text = ""
    return shape


def line(slide, x1: float, y1: float, x2: float, y2: float, color=LINE, width=1.0):
    from pptx.enum.shapes import MSO_CONNECTOR

    connector = slide.shapes.add_connector(
        MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2)
    )
    connector.line.color.rgb = color
    connector.line.width = Pt(width)
    _strip_style(connector)
    return connector


def arrow_right(slide, x: float, y: float, w: float = 0.36, h: float = 0.28, color=GRAY):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RIGHT_ARROW, Inches(x), Inches(y), Inches(w), Inches(h)
    )
    _set_fill(shape, color)
    _set_line(shape, None)
    _strip_style(shape)
    return shape


def arrow_down(slide, x: float, y: float, w: float = 0.28, h: float = 0.34, color=GRAY):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.DOWN_ARROW, Inches(x), Inches(y), Inches(w), Inches(h)
    )
    _set_fill(shape, color)
    _set_line(shape, None)
    _strip_style(shape)
    return shape


def add_text(
    slide,
    x: float,
    y: float,
    w: float,
    h: float,
    paragraphs,
    size: float = 18,
    color: RGBColor = INK,
    bold: bool = False,
    align=PP_ALIGN.LEFT,
    anchor=MSO_ANCHOR.TOP,
    line_spacing: float = 1.0,
    margins=(0, 0, 0, 0),
    font: str = FONT,
    space_after: float = 0,
):
    """Agrega texto. ``paragraphs`` puede ser str o lista de dicts."""
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left, tf.margin_right, tf.margin_top, tf.margin_bottom = [
        Inches(value) for value in margins
    ]
    if isinstance(paragraphs, str):
        paragraphs = [{"text": paragraphs}]
    first = True
    for item in paragraphs:
        if isinstance(item, str):
            item = {"text": item}
        paragraph = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        paragraph.alignment = item.get("align", align)
        paragraph.line_spacing = item.get("line_spacing", line_spacing)
        paragraph.space_before = Pt(item.get("space_before", 0))
        paragraph.space_after = Pt(item.get("space_after", space_after))
        runs = item.get("runs")
        if runs is None:
            runs = [
                {
                    "text": item.get("text", ""),
                    "size": item.get("size", size),
                    "color": item.get("color", color),
                    "bold": item.get("bold", bold),
                    "font": item.get("font", font),
                }
            ]
        for run_data in runs:
            run = paragraph.add_run()
            run.text = run_data.get("text", "")
            run.font.name = run_data.get("font", font)
            run.font.size = Pt(run_data.get("size", size))
            run.font.bold = run_data.get("bold", bold)
            run.font.color.rgb = run_data.get("color", color)
    return box


def pill(slide, x: float, y: float, text: str, fill=NAVY, color=WHITE, w: float = 2.4, h: float = 0.38, size: float = 13):
    rect(slide, x, y, w, h, fill=fill, line=None, radius=0.5)
    add_text(
        slide,
        x,
        y,
        w,
        h,
        text,
        size=size,
        color=color,
        bold=True,
        align=PP_ALIGN.CENTER,
        anchor=MSO_ANCHOR.MIDDLE,
    )


def metric_card(
    slide,
    x: float,
    y: float,
    w: float,
    h: float,
    value: str,
    label: str,
    accent: RGBColor = YELLOW,
    dark: bool = True,
):
    rect(slide, x, y, w, h, fill=NAVY if dark else LIGHT, line=None if dark else LINE)
    rect(slide, x, y, 0.09, h, fill=accent, line=None, radius=0)
    add_text(
        slide,
        x + 0.28,
        y + 0.18,
        w - 0.45,
        h * 0.56,
        value,
        size=42,
        color=WHITE if dark else NAVY,
        bold=True,
        anchor=MSO_ANCHOR.MIDDLE,
    )
    add_text(
        slide,
        x + 0.28,
        y + h * 0.66,
        w - 0.45,
        h * 0.3,
        label,
        size=14.5,
        color=RGBColor(0xCB, 0xD5, 0xE1) if dark else GRAY,
        anchor=MSO_ANCHOR.TOP,
    )


def add_header(slide, title: str, subtitle: str, number: int, section: str = ""):
    # Barra amarilla
    rect(slide, 0, 0, 0.28, 11.25, fill=YELLOW, line=None, radius=0)
    # Título y subtítulo
    add_text(slide, 0.9, 0.38, 16.8, 0.9, title, size=38, color=NAVY, bold=True)
    add_text(slide, 0.9, 1.24, 16.8, 0.5, subtitle, size=19, color=GRAY)
    if section:
        pill(slide, 16.95, 0.52, section, fill=NAVY, color=YELLOW, w=2.15, h=0.38, size=12)
    # Pie
    line(slide, 0.9, 10.49, 19.1, 10.49, color=LINE, width=1.0)
    add_text(
        slide,
        0.9,
        10.56,
        16.8,
        0.3,
        "AgroID Huevos · ISY0101 Ingeniería de Soluciones con IA · EFT · Esteban Pacheco Vega y Javier Perez Mora",
        size=12.5,
        color=GRAY,
    )
    add_text(
        slide,
        18.3,
        10.56,
        0.75,
        0.3,
        str(number),
        size=12.5,
        color=GRAY,
        align=PP_ALIGN.RIGHT,
    )


def evidence_tag(slide, text: str):
    rect(slide, 0.9, 9.78, 18.2, 0.3, fill=LIGHT, line=None, radius=0.3)
    add_text(
        slide,
        1.05,
        9.79,
        17.9,
        0.27,
        f"Evidencia: {text}",
        size=11.5,
        color=GRAY,
        anchor=MSO_ANCHOR.MIDDLE,
    )


def takeaway(slide, text: str, y: float = 9.05, h: float = 0.6):
    rect(slide, 0.9, y, 18.2, h, fill=RGBColor(0xFF, 0xF8, 0xE1), line=None)
    rect(slide, 0.9, y, 0.1, h, fill=YELLOW, line=None, radius=0)
    add_text(
        slide,
        1.18,
        y,
        17.7,
        h,
        text,
        size=17,
        color=NAVY,
        bold=True,
        anchor=MSO_ANCHOR.MIDDLE,
    )


def add_diagram_header(slide, title: str, subtitle: str, number: int, section: str = ""):
    """Cabecera compacta para que el diagrama ocupe el ancho completo."""
    rect(slide, 0, 0, 0.28, 11.25, fill=YELLOW, line=None, radius=0)
    add_text(slide, 0.9, 0.3, 15.3, 0.62, title, size=32, color=NAVY, bold=True)
    add_text(slide, 0.9, 0.98, 15.3, 0.32, subtitle, size=15, color=GRAY)
    if section:
        pill(slide, 16.95, 0.45, section, fill=NAVY, color=YELLOW, w=2.15, h=0.38, size=12)
    line(slide, 0.9, 10.49, 19.1, 10.49, color=LINE, width=1.0)
    add_text(
        slide,
        0.9,
        10.56,
        16.8,
        0.3,
        "AgroID Huevos · ISY0101 Ingeniería de Soluciones con IA · EFT · Esteban Pacheco Vega y Javier Perez Mora",
        size=12.5,
        color=GRAY,
    )
    add_text(
        slide,
        18.3,
        10.56,
        0.75,
        0.3,
        str(number),
        size=12.5,
        color=GRAY,
        align=PP_ALIGN.RIGHT,
    )


def add_diagram_full(slide, path: Path):
    """Recorta título/pie del diagrama y lo pone a ancho completo."""
    image = Image.open(path).convert("RGB")
    crop = image.crop((0, 110, image.width, 1880))
    out = EVID / f"diagram_{path.stem}.png"
    crop.save(out)
    height = 18.2 * crop.height / crop.width
    add_image(slide, out, 0.9, 1.38, 18.2, height)


def add_image(slide, path: Path, x: float, y: float, w: float, h: float | None = None):
    if h is None:
        image = Image.open(path)
        h = w * image.height / image.width
    return slide.shapes.add_picture(str(path), Inches(x), Inches(y), Inches(w), Inches(h))


def add_table(slide, x, y, w, h, rows, col_widths, font_size=14, header_size=14):
    table_shape = slide.shapes.add_table(
        len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(h)
    )
    table = table_shape.table
    total = sum(col_widths)
    for index, width in enumerate(col_widths):
        table.columns[index].width = Emu(int(Inches(w) * width / total))
    for r_idx, row in enumerate(rows):
        table.rows[r_idx].height = Emu(int(Inches(h) / len(rows)))
        for c_idx, value in enumerate(row):
            cell = table.cell(r_idx, c_idx)
            cell.margin_left = Inches(0.08)
            cell.margin_right = Inches(0.08)
            cell.margin_top = Inches(0.03)
            cell.margin_bottom = Inches(0.03)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            if r_idx == 0:
                cell.fill.fore_color.rgb = NAVY
            else:
                cell.fill.fore_color.rgb = LIGHT if r_idx % 2 else WHITE
            tf = cell.text_frame
            tf.word_wrap = True
            paragraph = tf.paragraphs[0]
            paragraph.alignment = PP_ALIGN.LEFT
            run = paragraph.add_run()
            run.text = str(value)
            run.font.name = FONT
            run.font.size = Pt(header_size if r_idx == 0 else font_size)
            run.font.bold = r_idx == 0
            run.font.color.rgb = WHITE if r_idx == 0 else INK
            _clear_cell_borders(cell)
    return table


def _clear_cell_borders(cell):
    from pptx.oxml.ns import qn

    tc_pr = cell._tc.get_or_add_tcPr()
    for tag in ("a:lnL", "a:lnR", "a:lnT", "a:lnB"):
        ln = tc_pr.find(qn(tag))
        if ln is not None:
            tc_pr.remove(ln)
        ln = tc_pr.makeelement(qn(tag), {"w": "0"})
        ln.append(ln.makeelement(qn("a:noFill"), {}))
        tc_pr.append(ln)


def add_notes(slide, text: str):
    slide.notes_slide.notes_text_frame.text = text.strip()


def new_slide(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    for shape in list(slide.placeholders):
        shape._element.getparent().remove(shape._element)
    return slide


def move_slide(prs, old_index: int, new_index: int):
    slides = prs.slides._sldIdLst
    items = list(slides)
    item = items[old_index]
    slides.remove(item)
    slides.insert(new_index, item)


# ---------------------------------------------------------------------------
# Portada
# ---------------------------------------------------------------------------
def build_cover(slide):
    # Fondo navy y los dos activos visuales de la portada EP3.
    background = slide.background
    background.fill.solid()
    background.fill.fore_color.rgb = NAVY

    add_image(slide, EVID / "cover_egg.png", 11.86, 1.12, 8.14, 9.0)
    add_image(slide, EVID / "cover_logo.png", 1.35, 0.65, 3.9, 0.96)

    pill(
        slide,
        1.35,
        2.05,
        "EVALUACIÓN FINAL TRANSVERSAL · EFT",
        fill=YELLOW,
        color=NAVY,
        w=5.2,
        h=0.42,
        size=14,
    )
    add_text(
        slide,
        1.35,
        2.75,
        10.3,
        2.9,
        "AgroID Huevos: agente de inventario con RAG híbrido, "
        "planificación adaptativa y observabilidad",
        size=42,
        color=YELLOW,
        bold=True,
        line_spacing=1.02,
    )
    add_text(
        slide,
        1.35,
        6.1,
        10.3,
        0.5,
        "ISY0101 · Ingeniería de Soluciones con IA · Sección 007D",
        size=22,
        color=RGBColor(0xCB, 0xD5, 0xE1),
    )
    add_text(
        slide,
        1.35,
        7.05,
        10.3,
        1.0,
        "Esteban Pacheco Vega\nJavier Perez Mora",
        size=26,
        color=WHITE,
        line_spacing=1.08,
    )
    pill(
        slide,
        1.35,
        8.35,
        "Defensa · 10 minutos",
        fill=RGBColor(0x13, 0x35, 0x5C),
        color=WHITE,
        w=3.3,
        h=0.42,
        size=13,
    )
    add_text(
        slide,
        1.35,
        9.55,
        10.3,
        0.4,
        "DUOC UC · 27 de noviembre de 2026 · Evaluación Final Transversal",
        size=17,
        color=RGBColor(0x94, 0xA3, 0xB8),
    )
    add_notes(
        slide,
        """[ESTEBAN · ~0:15] 
Buenos días. Somos Esteban Pacheco y Javier Perez. Hoy presentamos AgroID Huevos, un agente de inventario con RAG híbrido, planificación adaptativa y observabilidad. La pregunta que guía la defensa es simple: no solo si el agente responde bien, sino cómo lo sabemos y qué haríamos para mejorarlo. Tenemos 10 minutos y 15 láminas; la evidencia está en el informe, el notebook y el dashboard.""",
    )


# ---------------------------------------------------------------------------
# Láminas
# ---------------------------------------------------------------------------
def slide_problem(prs):
    s = new_slide(prs)
    add_header(
        s,
        "El problema: decidir inventario con información dispersa",
        "Caso verosímil, datos simulados. El agente no adivina: consulta, calcula y cita.",
        2,
        "CASO",
    )
    pains = [
        ("1", "Stock, producción y pedidos viven en lugares distintos."),
        ("2", "La priorización depende de la experiencia y no deja traza."),
        ("3", "El conocimiento técnico (FAO, USDA, Codex) queda fuera del flujo."),
    ]
    for index, (number, text) in enumerate(pains):
        y = 2.0 + index * 1.62
        rect(s, 0.9, y, 9.0, 1.38, fill=LIGHT, line=LINE)
        rect(s, 0.9, y, 0.1, 1.38, fill=YELLOW, line=None, radius=0)
        add_text(s, 1.2, y + 0.18, 0.55, 0.55, number, size=28, color=NAVY, bold=True)
        add_text(s, 1.85, y + 0.24, 7.75, 0.9, text, size=19, color=INK)
    # Preguntas clave
    rect(s, 0.9, 7.1, 9.0, 1.55, fill=NAVY, line=None)
    add_text(
        s,
        1.2,
        7.22,
        8.4,
        0.4,
        "Lo que debe decidir cada día",
        size=15,
        color=YELLOW,
        bold=True,
    )
    add_text(
        s,
        1.2,
        7.62,
        8.4,
        0.9,
        "¿Qué pedido priorizar?   ·   ¿cuánto producir?   ·   ¿cómo almacenar?",
        size=18,
        color=WHITE,
        bold=True,
    )
    # Métricas del caso
    cards = [
        ("5", "especies de huevo"),
        ("10", "herramientas"),
        ("24", "fragmentos RAG"),
        ("8", "casos EFT"),
    ]
    for index, (value, label) in enumerate(cards):
        col = index % 2
        row = index // 2
        metric_card(
            s,
            10.2 + col * 4.35,
            2.0 + row * 1.95,
            4.15,
            1.72,
            value,
            label,
            accent=YELLOW,
        )
    rect(s, 10.2, 6.1, 8.5, 2.55, fill=WHITE, line=LINE)
    add_text(s, 10.48, 6.25, 7.95, 0.4, "Alcance de la entrega", size=16, color=NAVY, bold=True)
    add_text(
        s,
        10.48,
        6.7,
        7.95,
        1.75,
        [
            "Inventario, pedidos, déficit y priorización.",
            "RAG interno + externo con citas verificables.",
            "Observabilidad, seguridad y evaluación reproducible.",
        ],
        size=16.5,
        color=INK,
        line_spacing=1.12,
        space_after=4,
    )
    takeaway(s, "El valor no está en responder más rápido: está en decidir con evidencia y dejar rastro.", y=9.35)
    add_notes(
        s,
        """[ESTEBAN · ~0:40] 
El caso es una PYME avícola verosímil. El problema no es solo consultar stock: es decidir qué pedido priorizar, cuánto producir y cómo almacenar con información dispersa. Hoy esa decisión depende de la experiencia y no queda traza. La entrega convierte ese problema en un flujo verificable: 5 especies, 10 herramientas, 24 fragmentos y 8 casos de evaluación. Los datos son simulados; no es un cliente real. 
Transición: para resolverlo, separamos el sistema en capas y pusimos seguridad antes del modelo.""",
    )
    return s


def slide_architecture(prs):
    s = new_slide(prs)
    add_diagram_header(
        s,
        "Arquitectura EFT: cinco capas y una traza por turno",
        "Usuario → seguridad → router → agente → datos → observabilidad → dashboard",
        3,
        "ARQUITECTURA",
    )
    add_diagram_full(s, ROOT / "docs" / "diagramas_eft" / "ejecutivo" / "diagrama_arquitectura.png")
    add_notes(
        s,
        """[ESTEBAN · ~0:45] 
La arquitectura tiene cinco capas. El diagrama muestra control: usuario, seguridad y router. La seguridad redacta PII, detecta inyección y aplica límites antes del LLM. El router decide ReAct o Plan. Orquestación: AgentExecutor con LLM fijo. Conocimiento: 10 herramientas, RAG híbrido, memoria y citas. Persistencia: SQLite, observabilidad y dashboard. Cada turno deja trace_id, spans, tokens, costo, fuentes y decisiones. No leas cada caja: seguí el flujo de izquierda a derecha.
Transición: con esa arquitectura, veamos qué obtuvimos en la corrida real.
""",
    )
    return s


def slide_results(prs):
    s = new_slide(prs)
    add_header(
        s,
        "Resultados reales: 8 casos, 7 éxitos y 1 bloqueo",
        "8 casos reales · nvidia/nemotron-3.5-lightning:free · 27 nov 2026.",
        4,
        "RESULTADOS",
    )
    metrics = [
        ("0,956", "score compuesto"),
        ("0,938", "tool match"),
        ("0,810", "groundedness"),
        ("0,667", "cobertura de citas"),
    ]
    for index, (value, label) in enumerate(metrics):
        metric_card(s, 0.9 + index * 4.55, 1.95, 4.3, 1.78, value, label, accent=YELLOW if index < 3 else RED)
    add_image(s, EVID / "chart_latencia.png", 0.9, 3.9, 12.2)
    # Panel derecho
    rect(s, 13.3, 3.9, 5.8, 4.45, fill=LIGHT, line=LINE)
    add_text(s, 13.55, 4.05, 5.3, 0.35, "Lo que dicen los números", size=16, color=NAVY, bold=True)
    add_text(
        s,
        13.55,
        4.55,
        5.3,
        3.45,
        [
            "40.432 tokens · USD 0,0064 equivalente.",
            "8,1 s de media · 17,1 s P95 · costo real USD 0.",
            "E06 se bloqueó sin herramientas y sin tokens.",
            "E04, la consulta ambigua, se lleva 17,1 s y ejecuta una herramienta extra.",
        ],
        size=16.5,
        color=INK,
        line_spacing=1.12,
        space_after=10,
    )
    add_text(s, 0.9, 8.55, 12.2, 0.5, "E04 y E05 concentran la latencia; E06 se bloqueó antes de llamar al modelo.", size=12.5, color=GRAY)
    takeaway(s, "El score alto no borra las brechas: citas 0,667 y groundedness 0,810 son la agenda.", y=9.35)
    add_notes(
        s,
        """[ESTEBAN · ~0:45] 
La corrida real EFT usó 8 casos y el modelo nemotron free. Obtuvimos score 0,956, tool match 0,938, groundedness 0,810 y cobertura de citas 0,667. Fueron 40.432 tokens, 8,1 segundos de media y 17,1 de P95; el costo real fue cero y el equivalente 0,0064 dólares. Un caso se bloqueó: E06, sin herramientas y sin tokens. La lectura honesta es que el agente usa bien las herramientas, pero todavía cita una fuente aunque recupere tres. 
Transición: ese promedio esconde qué casos explican la pérdida.""",
    )
    return s


def slide_findings(prs):
    s = new_slide(prs)
    add_header(
        s,
        "Hallazgos: el promedio esconde dónde falla el agente",
        "E04 y E07 concentran la pérdida; las citas son la brecha más sistemática.",
        5,
        "HALLAZGOS",
    )
    add_image(s, EVID / "chart_casos.png", 0.9, 2.0, 11.4)
    findings = [
        ("E04 · 0,750", "Consultó stock y pedidos sin aclarar; una herramienta extra.", RED),
        ("E07 · 0,950", "Recuperó la memoria, pero la groundedness fue 0,500.", AMBER),
        ("Citas · 0,667", "Cita una fuente aunque el RAG recupere tres.", PURPLE),
    ]
    for index, (title, text, accent) in enumerate(findings):
        y = 2.0 + index * 1.82
        rect(s, 12.65, y, 6.45, 1.55, fill=WHITE, line=LINE)
        rect(s, 12.65, y, 0.1, 1.55, fill=accent, line=None, radius=0)
        add_text(s, 12.95, y + 0.18, 5.95, 0.4, title, size=19, color=NAVY, bold=True)
        add_text(s, 12.95, y + 0.65, 5.95, 0.75, text, size=16, color=INK)
    rect(s, 12.65, 7.55, 6.45, 1.25, fill=NAVY, line=None)
    add_text(
        s,
        12.95,
        7.64,
        5.9,
        1.05,
        "El caso E08 sí alcanzó citas 1,00: el problema es de prompt y de verificación, no de recuperación.",
        size=14.5,
        color=WHITE,
        line_spacing=1.08,
    )
    takeaway(s, "La calidad se explica caso a caso; un solo promedio no dice qué corregir.", y=9.35)
    add_notes(
        s,
        """[ESTEBAN · ~0:40] 
El promedio de 0,956 esconde dos cosas. E04, la consulta ambigua, bajó a 0,750 porque el agente consultó stock y pedidos sin pedir aclaración. E07, la de memoria, recuperó bien el dato de Hotel Costa, pero la groundedness fue 0,500. Y la brecha sistemática son las citas: 0,667. El caso E08 sí llegó a 1,00, así que el problema no es que el RAG no recupere: es que el prompt no obliga a citar cada afirmación. 
Transición: por eso revisamos los prompts y el RAG por separado.""",
    )
    return s


def slide_prompts(prs):
    s = new_slide(prs)
    add_header(
        s,
        "Prompts versionados: de 0,90 a 1,00 en la rúbrica",
        "System v2 separa rol, jerarquía de fuentes, política de herramientas, formato y seguridad.",
        6,
        "PROMPTS",
    )
    # Comparación v1/v2
    for index, (version, score, detail, fill, accent) in enumerate(
        [
            ("v1", "0,90", "1.431 caracteres · 17 líneas · sin criterios de prueba", LIGHT, GRAY),
            ("v2", "1,00", "2.009 caracteres · 34 líneas · 7 dimensiones", RGBColor(0xFF, 0xF8, 0xE1), YELLOW),
        ]
    ):
        y = 2.0 + index * 1.55
        rect(s, 0.9, y, 8.2, 1.35, fill=fill, line=LINE)
        rect(s, 0.9, y, 0.1, 1.35, fill=accent, line=None, radius=0)
        add_text(s, 1.2, y + 0.12, 1.0, 0.45, version, size=17, color=GRAY, bold=True)
        add_text(s, 2.15, y + 0.08, 2.0, 0.6, score, size=30, color=NAVY, bold=True)
        add_text(s, 4.2, y + 0.3, 4.65, 0.7, detail, size=14, color=INK, line_spacing=1.05)
    # Barras
    for index, (label, value, color) in enumerate(
        [("v1", 0.90, GRAY), ("v2", 1.00, YELLOW)]
    ):
        y = 5.35 + index * 0.85
        add_text(s, 0.9, y, 0.7, 0.4, label, size=15, color=NAVY, bold=True)
        rect(s, 1.55, y + 0.05, 6.8, 0.28, fill=RGBColor(0xED, 0xF1, 0xF7), line=None, radius=0.4)
        rect(s, 1.55, y + 0.05, 6.8 * value, 0.28, fill=color, line=None, radius=0.4)
        add_text(s, 8.45, y - 0.02, 0.7, 0.4, f"{value:.2f}".replace(".", ","), size=15, color=NAVY, bold=True)
    # Cambios clave
    changes = [
        ("Jerarquía de fuentes", "negocio > manual/corpus > conocimiento general"),
        ("Citas obligatorias", "[Mxx] y [Exx] por afirmación técnica"),
        ("Ambigüedad y escritura", "preguntar antes de escribir; no reintentar a ciegas"),
    ]
    for index, (title, text) in enumerate(changes):
        y = 7.05 + index * 0.6
        add_text(s, 0.95, y, 0.28, 0.35, "＋", size=17, color=TEAL, bold=True)
        add_text(s, 1.3, y, 7.6, 0.45, [{"runs": [
            {"text": title + ": ", "size": 14, "color": NAVY, "bold": True},
            {"text": text, "size": 14, "color": INK},
        ]}])
    # Código real
    rect(s, 9.45, 2.0, 9.7, 5.65, fill=NAVY, line=None)
    add_text(s, 9.7, 2.12, 9.2, 0.35, "system_v2 · fragmento real", size=13, color=YELLOW, bold=True, font=MONO)
    code = """## Jerarquía de fuentes
1. Cifras de stock, pedidos y déficit:
   solo desde las herramientas.
2. Recomendaciones técnicas: desde
   buscar_manual; cita [Mxx] o [Exx].
3. Conocimiento general: solo para explicar;
   nunca para inventar cifras.

## Política de herramientas
- Consulta antes de escribir.
- Si falta un dato, pide precisión.
- No repitas una llamada idéntica que falló.
- No ejecutes acciones destructivas.

## Formato
- 1 a 4 frases, cifras y unidades.
- Separa hechos de recomendaciones.
- Si es ambiguo, pregunta antes de escribir."""
    add_text(s, 9.7, 2.55, 9.15, 4.95, code, size=13.5, color=WHITE, font=MONO, line_spacing=1.02)
    rect(s, 9.45, 7.8, 9.7, 0.8, fill=RGBColor(0xF0, 0xFD, 0xF4), line=RGBColor(0xBB, 0xF7, 0xD0))
    add_text(
        s,
        9.7,
        7.87,
        9.2,
        0.62,
        [{"runs": [
            {"text": "Regresión funcional 0,996: ", "size": 14, "color": TEAL, "bold": True},
            {"text": "8/8 casos EFT sin degradación frente a v1.", "size": 14, "color": INK},
        ]}],
        anchor=MSO_ANCHOR.MIDDLE,
    )
    takeaway(s, "Un prompt no se evalúa por lo que dice, sino por lo que el agente deja de hacer mal.", y=9.35)
    add_notes(
        s,
        """[JAVIER · ~0:40] 
El prompt del sistema no es una frase genérica. La v1 tenía 17 líneas y sacó 0,90; la v2 tiene 34 y sacó 1,00 en la rúbrica de siete dimensiones. ¿Qué agregó? Jerarquía de fuentes, citas obligatorias, política de herramientas, manejo de ambigüedad y criterios de prueba. La regresión funcional se mantuvo en 0,996. El fragmento de la derecha es real: no inventar cifras, citar y preguntar antes de escribir. 
Transición: el siguiente componente es el RAG que alimenta esas citas.""",
    )
    return s


def slide_rag(prs):
    s = new_slide(prs)
    add_diagram_header(
        s,
        "RAG híbrido: fuentes, integridad y citas",
        "Fuentes → integridad → índice → recuperación → seguridad → citas → respuesta",
        7,
        "RAG",
    )
    add_diagram_full(s, ROOT / "docs" / "diagramas_eft" / "ejecutivo" / "diagrama_rag_hibrido.png")
    add_notes(
        s,
        """[JAVIER · ~0:40] 
El diagrama muestra el RAG de punta a punta: manual interno (10) y corpus externo (14) pasan por integridad SHA-256/HMAC, índice TF-IDF, recuperación top-k por fuente, seguridad, merge/rerank y citas [Mxx]/[Exx]. La respuesta se evalúa y deja evidencia. En la evaluación obtuvimos recall@3 0,867 y 9 de 10 consultas con fuente externa. La salida citada de E01 se muestra en la demo, lámina 11.
Transición: con ese contexto, el agente puede consultar, escribir y planificar.
""",
    )
    return s


def slide_agent(prs):
    s = new_slide(prs)
    add_diagram_header(
        s,
        "Planificación adaptativa: clasificar, planificar, monitorear",
        "Replanificación acotada; no se reintentan las escrituras exitosas.",
        8,
        "AGENTE",
    )
    add_diagram_full(s, ROOT / "docs" / "diagramas_eft" / "ejecutivo" / "diagrama_planificacion.png")
    add_notes(
        s,
        """[JAVIER · ~0:50] 
El diagrama de planificación muestra el ciclo: clasificador (simple, compuesta, ambigua, riesgosa) → ReAct o Plan → AgentExecutor → herramientas → monitor → decisión → crítico → respuesta → métricas. La regla clave: si una escritura ya salió bien, no se reintenta; la replanificación vuelve al plan, no a la respuesta. La traza E03 con 19,93 s y 9.154 tokens se ve en la lámina 10.
Transición: esa traza se ve en el dashboard y en LangSmith.
""",
    )
    return s


def slide_dashboard(prs):
    s = new_slide(prs)
    add_header(
        s,
        "Dashboard: la evidencia se filtra y se audita",
        "7 pestañas; resumen, calidad, RAG/planificación, costos, trazas y seguridad.",
        9,
        "DASHBOARD",
    )
    add_image(s, EVID / "dashboard_overview.png", 0.9, 2.0, 6.9)
    # Callouts bajo la captura
    callouts = [
        ("8 trazas", "corrida real"),
        ("87,5%", "éxito · 1 bloqueo"),
        ("40.432", "tokens"),
    ]
    for index, (value, label) in enumerate(callouts):
        x = 0.9 + index * 2.35
        rect(s, x, 7.7, 2.15, 1.1, fill=LIGHT, line=LINE)
        add_text(s, x + 0.12, 7.76, 1.9, 0.45, value, size=21, color=NAVY, bold=True)
        add_text(s, x + 0.12, 8.24, 1.9, 0.45, label, size=11.5, color=GRAY)
    # Calidad
    add_text(s, 8.45, 1.98, 9.8, 0.35, "Calidad por grupo · corrida real", size=14, color=NAVY, bold=True)
    add_image(s, EVID / "dashboard_quality_panel.png", 8.45, 2.35, 9.8)
    # RAG/planificación
    rect(s, 8.45, 6.75, 9.8, 2.05, fill=LIGHT, line=LINE)
    add_text(s, 8.7, 6.83, 6.5, 0.35, "RAG y planificación", size=14, color=NAVY, bold=True)
    add_text(s, 15.4, 6.87, 2.5, 0.3, "misma corrida", size=10.5, color=GRAY, align=PP_ALIGN.RIGHT)
    rag_metrics = [
        ("5 / 4", "fragmentos externos / internos"),
        ("66,7%", "cobertura media de citas"),
        ("0,0%", "replanificación"),
    ]
    for index, (value, label) in enumerate(rag_metrics):
        x = 8.7 + index * 3.15
        add_text(s, x, 7.55, 2.9, 0.45, value, size=22, color=NAVY, bold=True)
        add_text(s, x, 8.0, 2.9, 0.45, label, size=11, color=GRAY)
    add_text(s, 8.7, 8.4, 9.3, 0.4, "La pestaña RAG muestra las fuentes recuperadas; la de trazas abre el waterfall de spans.", size=11, color=INK)
    takeaway(s, "El dashboard no es decorativo: permite ver qué modelo se usó, qué falló y cuánto costó.", y=9.35)
    add_notes(
        s,
        """[ESTEBAN · ~0:45] 
El dashboard tiene siete pestañas. A la izquierda, el resumen de la corrida real: 8 trazas, 87,5% de éxito, 40.432 tokens y P95 de 15,7 segundos. A la derecha, la tabla de calidad por grupo: tool match 0,9375, groundedness 0,8099, score 0,956 y citas 0,6667. Abajo, RAG y planificación: 5 fragmentos externos, 4 internos, cobertura de citas 66,7% y cero replanificaciones. Lo importante es que todo se puede filtrar por corrida, grupo, categoría y modo. 
Transición: para entender el tiempo, bajamos a la traza y a LangSmith.""",
    )
    return s


def slide_langsmith(prs):
    s = new_slide(prs)
    add_header(
        s,
        "LangSmith y traza real: el tiempo se va en el LLM",
        "Traza EFT real de E03: 4 llamadas LLM y 2 herramientas. El cuello es el proveedor.",
        10,
        "TRAZAS",
    )
    # Traza real capturada desde LangSmith (proyecto agroid-huevos-ep3).
    add_image(s, EVID / "langsmith_eft_trace_e03.png", 0.9, 2.0, 7.9)
    add_text(
        s,
        0.9,
        7.82,
        7.9,
        0.3,
        "LangSmith · traza real E03",
        size=10.5,
        color=GRAY,
    )
    add_text(
        s,
        0.9,
        8.15,
        7.9,
        0.8,
        "La varianza del modelo free explica por qué el mismo caso puede tardar 10,6 s o 18,4 s.",
        size=12,
        color=GRAY,
        line_spacing=1.08,
    )
    # Waterfall de la misma traza, generado desde spans SQLite.
    add_image(s, EVID / "chart_waterfall_e03.png", 9.0, 2.0, 9.1)
    rect(s, 9.0, 5.35, 9.1, 3.6, fill=NAVY, line=None)
    add_text(s, 9.25, 5.45, 8.6, 0.35, "Lectura de la traza E03", size=14, color=YELLOW, bold=True)
    trace_metrics = [
        ("18,44 s", "total"),
        ("9,94 s", "planificador"),
        ("0,03 s", "tools SQL"),
    ]
    for index, (value, label) in enumerate(trace_metrics):
        x = 9.25 + index * 2.95
        add_text(s, x, 5.85, 2.8, 0.55, value, size=25, color=WHITE, bold=True)
        add_text(s, x, 6.42, 2.8, 0.3, label, size=10.5, color=RGBColor(0xCB, 0xD5, 0xE1))
    add_text(
        s,
        9.25,
        7.05,
        8.6,
        1.7,
        [
            "4 llamadas LLM + 2 herramientas.",
            "La última llamada consume 6,16 s.",
            "El cuello es el modelo, no la base.",
        ],
        size=13.5,
        color=WHITE,
        line_spacing=1.12,
        space_after=4,
    )
    add_text(s, 9.25, 8.25, 8.6, 0.45, "En E05, una sola llamada al LLM se llevó 70,2 s.", size=12, color=RGBColor(0xCB, 0xD5, 0xE1))
    takeaway(s, "El 90% del tiempo está en el LLM; optimizar la base no mueve la aguja.", y=9.35)
    add_notes(
        s,
        """[ESTEBAN · ~0:40] 
Esta es la traza real de E03 en LangSmith. El turno completo dura 18,44 s y consume 9.154 tokens. El planificador se lleva 9,94 s; luego dos tools SQL de 0,03 s y tres llamadas más al LLM, con la última de 6,16 s. En total, cuatro llamadas LLM y dos herramientas. El waterfall confirma que el cuello es el modelo, no SQLite. En E05, una sola llamada se llevó 70,2 s: la varianza del modelo free es parte del hallazgo.
Transición: con esta evidencia, la demo se reemplaza por tres salidas pregrabadas.
""",
    )
    return s


def slide_demo(prs):
    s = new_slide(prs)
    add_header(
        s,
        "Demo pregrabada: 40 segundos, tres evidencias",
        "Sin Colab en vivo. Si piden live: E01 en modo simulado y trace_id, 20 segundos.",
        11,
        "DEMO",
    )
    panels = [
        (
            "1 · RAG",
            TEAL,
            [
                ("Consulta", "¿Qué temperatura recomienda el USDA?", "query"),
                ("Recuperación", "[E05] USDA · [E06] FAO · [M01] manual", "body"),
                (
                    "Respuesta real E01",
                    "Según el USDA [E05], los huevos crudos con cáscara deben refrigerarse a 4,4 °C o menos y duran 3–5 semanas.",
                    "body",
                ),
                ("Verificación", "recall@3 0,867 · cita externa verificada", "small"),
            ],
        ),
        (
            "2 · Plan y tools",
            AMBER,
            [
                ("Consulta", "Revisa el déficit y prioriza los pedidos.", "query"),
                ("Plan (auto)", "1. calcular_deficit\n2. priorizar_pedidos\n3. responder", "body"),
                ("Traza real E03", "mode=plan · 2 tools · 9.154 tokens\ntrace_id=3f31231d", "body"),
                ("Resultado", "Déficit de gallina y codorniz; priorización actualizada.", "small"),
            ],
        ),
        (
            "3 · Memoria y replan",
            PURPLE,
            [
                ("Antes", "Recuerda que Hotel Costa solo acepta pato.", "query"),
                ("Después de reset_memories()", "Hotel Costa solo acepta huevos de pato. ✓", "body"),
                ("Prueba de fallo", "replan_count=1 · error corregido\n0 reintentos de escritura", "body"),
                ("Seguridad", "E06 bloqueado: 0 herramientas, 0 tokens.", "small"),
            ],
        ),
    ]
    for index, (header, accent, sections) in enumerate(panels):
        x = 0.9 + index * 6.2
        rect(s, x, 2.0, 5.9, 5.95, fill=WHITE, line=LINE)
        rect(s, x, 2.0, 5.9, 0.55, fill=accent, line=None, radius=0)
        add_text(s, x + 0.2, 2.05, 5.5, 0.42, header, size=15, color=WHITE, bold=True)
        y_label = 2.72
        y_text = 2.98
        heights = [0.55, 0.7, 0.8, 0.5]
        for (label, text, kind), text_h in zip(sections, heights):
            add_text(s, x + 0.25, y_label, 5.4, 0.25, label, size=10.5, color=GRAY, bold=True)
            if kind == "query":
                add_text(s, x + 0.25, y_text, 5.4, text_h, text, size=14.5, color=NAVY, bold=True, line_spacing=1.04)
            elif kind == "small":
                add_text(s, x + 0.25, y_text, 5.4, text_h, text, size=12.5, color=TEAL, bold=True)
            else:
                add_text(s, x + 0.25, y_text, 5.4, text_h, text, size=13.5, color=INK, line_spacing=1.08)
            y_label += 1.18
            y_text += 1.18
    rect(s, 0.9, 8.15, 18.2, 0.65, fill=NAVY, line=None)
    add_text(
        s,
        1.15,
        8.18,
        17.7,
        0.6,
        "Plan B 20 s: ejecutar E01 en modo simulado, mostrar trace_id y el bloqueo de E06. No depende de internet.",
        size=14,
        color=WHITE,
        bold=True,
        anchor=MSO_ANCHOR.MIDDLE,
    )
    takeaway(s, "La demo muestra el flujo; la evidencia muestra que el flujo es medible.", y=9.0)
    add_notes(
        s,
        """[JAVIER · ~0:40] 
No vamos a ejecutar Colab en vivo: sería muy largo y depende de la cuota. La demo son tres evidencias pregrabadas. Primero, RAG: la consulta al USDA devuelve [E05] y la respuesta correcta. Segundo, plan y tools: E03 muestra calcular_deficit y priorizar_pedidos, con su trace_id. Tercero, memoria y replanificación: Hotel Costa sobrevive al reset y la prueba de fallo deja replan_count=1. Si el docente pide live, hacemos solo E01 en modo simulado y mostramos el trace_id en 20 segundos. 
Transición: la última capa es seguridad y ética.""",
    )
    return s


def slide_security(prs):
    s = new_slide(prs)
    add_header(
        s,
        "Seguridad y ética: los controles también se prueban",
        "PII, inyección, rate limit, integridad del corpus, escrituras y fuga del prompt.",
        12,
        "SEGURIDAD",
    )
    controls = [
        ("PII redactada", "RUT, emails, teléfonos y tarjetas se reemplazan antes del LLM, logs y trazas.", PALE_RED, RED),
        ("Detección de inyección", "Patrones ponderados y delimitación del mensaje del usuario.", PALE_RED, RED),
        ("Rate limiting", "Límites por sesión y globales para contener abuso y cuota.", PALE_AMBER, AMBER),
        ("Integridad del corpus", "SHA-256/HMAC por fragmento; lo alterado se excluye.", PALE_GREEN, TEAL),
        ("Límite de escrituras", "Máximo 3 escrituras por turno; no se reintentan las exitosas.", PALE_BLUE, BLUE),
        ("Fuga del prompt", "Se bloquean respuestas que revelen instrucciones internas.", PALE_PURPLE, PURPLE),
    ]
    for index, (title, text, fill, accent) in enumerate(controls):
        col = index % 3
        row = index // 3
        x = 0.9 + col * 6.15
        y = 2.0 + row * 2.18
        rect(s, x, y, 5.9, 1.98, fill=fill, line=accent, radius=0.06)
        add_text(s, x + 0.22, y + 0.15, 5.45, 0.4, title, size=17, color=NAVY, bold=True)
        add_text(s, x + 0.22, y + 0.62, 5.45, 1.2, text, size=14, color=INK, line_spacing=1.08)
    # Resultados de pruebas
    rect(s, 0.9, 6.55, 8.8, 1.95, fill=NAVY, line=None)
    add_text(s, 1.2, 6.65, 8.2, 0.4, "7/7 pruebas de seguridad", size=18, color=YELLOW, bold=True)
    add_text(s, 1.2, 7.1, 8.2, 1.25, "5 ataques bloqueados · 4 consultas legítimas sin falsos positivos · E06 blocked con 0 herramientas y 0 tokens.", size=14, color=WHITE, line_spacing=1.08)
    rect(s, 10.0, 6.55, 9.1, 1.95, fill=WHITE, line=LINE)
    add_text(s, 10.3, 6.65, 8.5, 0.4, "Limitación reconocida", size=16, color=NAVY, bold=True)
    add_text(s, 10.3, 7.08, 8.5, 1.3, "El detector es heurístico: no cubre paráfrasis nuevas ni ataques multimodales. Marcos: NIST AI RMF 1.0 y OWASP Top 10. Escrituras de alto valor requieren human-in-the-loop.", size=13.5, color=INK, line_spacing=1.08)
    takeaway(s, "La seguridad se demuestra con pruebas y con límites declarados, no con una lista de features.", y=9.35)
    add_notes(
        s,
        """[JAVIER · ~0:40] 
La seguridad tiene seis controles: PII redactada antes del LLM y de la telemetría; detección de inyección; rate limiting; integridad SHA-256/HMAC del corpus; límite de tres escrituras por turno; y bloqueo de fuga del prompt. La suite aprobó 7 de 7 pruebas: 5 ataques bloqueados y 4 consultas legítimas sin falsos positivos. E06 se bloqueó con cero herramientas y cero tokens. La limitación es honesta: el detector es heurístico, no cubre paráfrasis nuevas ni ataques multimodales. Por eso hablamos de NIST y OWASP, y proponemos human-in-the-loop.
Transición: con eso, ¿qué mejoraríamos?
""",
    )
    return s


def slide_improvements(prs):
    s = new_slide(prs)
    add_header(
        s,
        "Mejoras: cada propuesta nace de una observación medida",
        "Roadmap 0–12 meses; prioridad por impacto y esfuerzo.",
        13,
        "MEJORAS",
    )
    rows = [
        ["Observación", "Propuesta", "Métrica de respuesta"],
        ["Citas 0,667", "Cita obligatoria por párrafo + crítico que bloquee sin fuente", "cobertura ≥ 0,95"],
        ["E04 ambiguo (0,750)", "Aclarar antes de consultar; no ejecutar herramientas", "tool match 1,00"],
        ["Router EP3 cambió 7/8", "Modelo fijo o routing por complejidad", "Jaccard ≥ 0,95"],
        ["SQLite WAL 40/5", "PostgreSQL + Redis para estado y rate limit", "P95 < 5 s · 0 bloqueos"],
        ["Escrituras de alto valor", "Human-in-the-loop y confirmación explícita", "0 escrituras no confirmadas"],
    ]
    add_table(s, 0.9, 2.0, 18.2, 4.6, rows, [4.2, 8.4, 5.6], font_size=13.5, header_size=13.5)
    # Roadmap
    phases = [
        ("0–1 mes", "Citas y ambigüedad", "impacto alto · esfuerzo bajo"),
        ("1–3 meses", "Fallback y caché", "impacto alto · esfuerzo medio"),
        ("3–6 meses", "PostgreSQL / Redis", "impacto medio · esfuerzo alto"),
        ("6–12 meses", "Model routing y validación", "impacto alto · esfuerzo alto"),
    ]
    for index, (period, title, note) in enumerate(phases):
        x = 0.9 + index * 4.6
        rect(s, x, 6.9, 4.35, 1.55, fill=LIGHT, line=LINE)
        add_text(s, x + 0.18, 6.98, 4.0, 0.3, period, size=12, color=YELLOW, bold=True)
        add_text(s, x + 0.18, 7.3, 4.0, 0.45, title, size=16, color=NAVY, bold=True)
        add_text(s, x + 0.18, 7.82, 4.0, 0.45, note, size=11.5, color=GRAY)
    takeaway(s, "El roadmap no es una lista de deseos: cada fila responde a una métrica que ya falló.", y=9.35)
    add_notes(
        s,
        """[JAVIER · ~0:35] 
Las mejoras salen de los datos. Primero, citas obligatorias y un crítico que bloquee respuestas sin fuente: hoy 0,667. Segundo, aclarar antes de consultar: E04 («¿Cuánto queda?») ejecutó una herramienta extra. Tercero, modelo fijo o routing por complejidad: en la EP3 el router cambió 7 de 8 veces. Cuarto, PostgreSQL y Redis para producción: SQLite con WAL resistió 40 solicitudes con 5 workers, pero no es para múltiples réplicas. Quinto, human-in-the-loop para escrituras de alto valor. El roadmap va de 0 a 12 meses.
Transición: cierro con la conclusión.
""",
    )
    return s


def slide_conclusion(prs):
    s = new_slide(prs)
    add_header(
        s,
        "Conclusión: observable, corregible y con límites conocidos",
        "No demostramos que el agente funciona; demostramos cómo saberlo.",
        14,
        "CIERRE",
    )
    cards = [
        (
            "Observable",
            [
                "trace_id, spans, tokens y costo por turno.",
                "Dashboard de 7 pestañas con filtros.",
                "8 casos reales y waterfall de E03.",
                "La misma traza alimenta dashboard, LangSmith y evaluación.",
            ],
            PALE_BLUE,
            BLUE,
        ),
        (
            "Corregible",
            [
                "Prompt v1 0,90 · v2 1,00.",
                "RAG con recall@3 0,867 y citas.",
                "react / plan / auto: score 0,994.",
                "La regresión funcional se mantiene en 0,996.",
            ],
            PALE_GREEN,
            TEAL,
        ),
        (
            "Con límites",
            [
                "Citas 0,667 y E04 en 0,750.",
                "Modelo free y cuota variable.",
                "Sin transacción multi-paso ni HITL.",
                "La muestra es de 8 casos: no generaliza.",
            ],
            PALE_RED,
            RED,
        ),
    ]
    for index, (title, bullets, fill, accent) in enumerate(cards):
        x = 0.9 + index * 6.2
        rect(s, x, 2.0, 5.9, 3.95, fill=fill, line=accent, radius=0.06)
        add_text(s, x + 0.3, 2.18, 5.3, 0.6, title, size=25, color=NAVY, bold=True)
        add_text(
            s,
            x + 0.3,
            2.9,
            5.3,
            2.9,
            ["• " + item for item in bullets],
            size=15.5,
            color=INK,
            line_spacing=1.12,
            space_after=6,
        )
    rect(s, 0.9, 6.25, 18.2, 1.45, fill=NAVY, line=None)
    add_text(
        s,
        1.25,
        6.35,
        17.5,
        1.25,
        "“El resultado no es un agente perfecto: es un sistema que deja evidencia para mejorar.”",
        size=23,
        color=YELLOW,
        bold=True,
        anchor=MSO_ANCHOR.MIDDLE,
    )
    add_text(s, 0.9, 7.9, 18.2, 0.5, "Gracias. Quedamos disponibles para preguntas.", size=21, color=NAVY, bold=True)
    add_text(s, 0.9, 8.4, 18.2, 0.4, "Esteban Pacheco Vega · Javier Perez Mora · ISY0101 · Sección 007D", size=13.5, color=GRAY)
    add_text(s, 0.9, 9.45, 18.2, 0.4, "Material: informe 26 pp · notebook · 15 láminas · 8 casos · 7/7 pruebas de seguridad", size=12, color=GRAY)
    add_notes(
        s,
        """[ESTEBAN · ~0:25] 
El proyecto demuestra que un agente de inventario puede ser útil si se lo rodea de ingeniería: herramientas que validan, RAG con citas, memoria con resumen, planificación con replanificación, observabilidad y seguridad. La corrida real EFT de 0,956 y la EP3 de 0,970 muestran un desempeño alto en un escenario acotado; no prueban que sea productivo. Las brechas son claras: citas 0,667, E04 ambiguo, groundedness 0,810 y dependencia de modelos free. La conclusión no es “el agente funciona”, sino “el agente es observable, corregible y tiene límites conocidos”. Gracias; quedamos para preguntas.""",
    )
    return s


def slide_annex(prs):
    s = new_slide(prs)
    add_header(
        s,
        "Anexo: los 8 casos y las preguntas de respaldo",
        "Tabla completa, preguntas de respaldo y límites.",
        15,
        "ANEXO",
    )
    rows = [
        ["Caso", "Categoría", "Estado", "Score", "Tool", "Ground.", "Citas"],
        ["E01", "rag externo", "success", "1,000", "1,000", "1,000", "0,333"],
        ["E02", "rag híbrido", "success", "1,000", "1,000", "1,000", "0,667"],
        ["E03", "complejo", "success", "0,988", "1,000", "0,879", "—"],
        ["E04", "ambiguo", "success", "0,750", "0,500", "0,500", "—"],
        ["E05", "complejo", "success", "1,000", "1,000", "1,000", "—"],
        ["E06", "adversarial", "blocked", "1,000", "1,000", "1,000", "—"],
        ["E07", "memoria", "success", "0,950", "1,000", "0,500", "—"],
        ["E08", "rag externo", "success", "0,960", "1,000", "0,600", "1,000"],
    ]
    add_table(s, 0.9, 2.0, 12.7, 5.6, rows, [1.1, 3.3, 2.0, 1.6, 1.5, 1.3, 1.3], font_size=13, header_size=13)
    # Cómo leer la tabla
    rect(s, 13.9, 2.0, 5.2, 1.55, fill=LIGHT, line=LINE)
    add_text(s, 14.15, 2.08, 4.7, 0.3, "Cómo leer la tabla", size=14, color=NAVY, bold=True)
    add_text(
        s,
        14.15,
        2.42,
        4.7,
        1.05,
        "Estado: success o blocked.\nScore: 0 a 1.\nCitas: solo en los casos con RAG.",
        size=11,
        color=INK,
        line_spacing=1.12,
    )
    # Preguntas de respaldo
    rect(s, 13.9, 3.75, 5.2, 1.75, fill=NAVY, line=None)
    add_text(s, 14.15, 3.83, 4.7, 0.3, "Preguntas de respaldo", size=14, color=YELLOW, bold=True)
    add_text(
        s,
        14.15,
        4.17,
        4.7,
        1.25,
        "¿Por qué citas 0,667?\n¿Por qué E04 baja a 0,750?\n¿Por qué no es production-ready?\n¿Qué pasa si el modelo free falla?",
        size=11,
        color=WHITE,
        line_spacing=1.12,
    )
    # Límites
    rect(s, 13.9, 5.7, 5.2, 1.35, fill=WHITE, line=LINE)
    add_text(s, 14.15, 5.78, 4.7, 0.3, "Límites", size=14, color=NAVY, bold=True)
    add_text(
        s,
        14.15,
        6.12,
        4.7,
        0.85,
        "8 casos · datos simulados · modelo free. La muestra no generaliza a producción.",
        size=11,
        color=INK,
        line_spacing=1.1,
    )
    # Lo que no está resuelto
    rect(s, 13.9, 7.25, 5.2, 1.8, fill=LIGHT, line=None)
    add_text(s, 14.15, 7.33, 4.7, 0.3, "Qué no está resuelto", size=14, color=NAVY, bold=True)
    add_text(
        s,
        14.15,
        7.7,
        4.7,
        1.2,
        [
            "Autenticación y multi-tenant.",
            "Human-in-the-loop en escrituras.",
            "SLA, fallback y transacción multi-paso.",
        ],
        size=11,
        color=INK,
        line_spacing=1.12,
    )
    # Lectura rápida
    rect(s, 0.9, 7.72, 12.7, 0.85, fill=LIGHT, line=LINE)
    add_text(s, 1.15, 7.76, 12.2, 0.28, "Lectura rápida", size=13, color=NAVY, bold=True)
    add_text(
        s,
        1.15,
        8.02,
        12.2,
        0.5,
        "E04 y las citas explican la brecha; E06 demuestra el bloqueo; E08 confirma que el RAG sí puede citar cuando el prompt lo obliga.",
        size=12,
        color=INK,
        line_spacing=1.05,
    )
    takeaway(s, "Los datos son simulados y el prototipo no es production-ready; la corrida sí es reproducible.", y=9.35)
    add_notes(
        s,
        """[ANEXO · sin tiempo asignado] 
Esta lámina no se presenta salvo que sobre tiempo o que pidan el detalle. Contiene los 8 casos, las preguntas de respaldo y los límites. Recordar: 8 casos es una muestra pequeña; no se puede generalizar a producción.""",
    )
    return s


# Main
# ---------------------------------------------------------------------------
def main() -> int:
    prs = Presentation()
    prs.slide_width = Inches(20)
    prs.slide_height = Inches(11.25)
    cover = new_slide(prs)
    build_cover(cover)
    slide_problem(prs)
    slide_architecture(prs)
    slide_results(prs)
    slide_findings(prs)
    slide_prompts(prs)
    slide_rag(prs)
    slide_agent(prs)
    slide_dashboard(prs)
    slide_langsmith(prs)
    slide_demo(prs)
    slide_security(prs)
    slide_improvements(prs)
    slide_conclusion(prs)
    slide_annex(prs)

    prs.save(OUT)
    print(f"PPTX: {OUT} ({len(prs.slides)} láminas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
