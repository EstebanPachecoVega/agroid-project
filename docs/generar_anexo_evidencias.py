"""Genera un anexo PDF con las capturas del dashboard y el resumen de resultados.

Uso:
    python docs/generar_anexo_evidencias.py
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs" / "evidencias"
OUTPUT = EVIDENCE / "ANEXO_EVIDENCIAS.pdf"
RESULTS = EVIDENCE / "resultados_consolidados.json"

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 1.5 * cm
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN

CAPTIONS = [
    (
        "captura_dashboard_resumen.jpeg",
        "Resumen general: 126 trazas acumuladas, tasa de éxito, P95, tokens y costo equivalente.",
    ),
    (
        "captura_dashboard_rendimiento.jpeg",
        "Rendimiento: latencia por tipo de span y TTFT real frente a throughput.",
    ),
    (
        "captura_dashboard_calidad.jpeg",
        "Calidad y consistencia por grupo experimental, con filtros de corridas reales y éxito.",
    ),
    (
        "captura_dashboard_costos.jpeg",
        "Costos y tokens: costo real $0 en modelos gratuitos, costo equivalente y proyección.",
    ),
    (
        "captura_dashboard_traza_router.jpeg",
        "Explorador de trazas: waterfall de un turno real con cinco modelos distintos.",
    ),
    (
        "captura_dashboard_seguridad.jpeg",
        "Seguridad: eventos de inyección bloqueados e integridad verificada del manual.",
    ),
    (
        "captura_langsmith_01_overview.png",
        "LangSmith · Overview: actividad de 7 días, trazas exitosas/fallidas, latencia P50/P99, costo y uso por modelo y herramienta.",
    ),
    (
        "captura_langsmith_02_tracing.png",
        "LangSmith · Tracing: listado de trazas reales con entrada, salida, latencia, tokens y metadatos de sesión.",
    ),
    (
        "captura_langsmith_03_monitoring.png",
        "LangSmith · Monitoring: evolución temporal de trazas, latencia y tasa de error.",
    ),
]


def _styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            alignment=1,
            spaceAfter=10,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["Normal"],
            fontSize=9,
            leading=12,
            alignment=1,
            textColor=colors.HexColor("#374151"),
            spaceAfter=14,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            spaceBefore=8,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            spaceAfter=4,
        ),
        "caption": ParagraphStyle(
            "Caption",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#374151"),
            spaceBefore=6,
        ),
        "table": ParagraphStyle(
            "Table",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=7.2,
            leading=8.6,
        ),
    }


def _summary_table(payload: dict, style: ParagraphStyle) -> Table:
    rows = [["Corrida", "Turnos", "Éxito", "Score", "Tool", "Grounded", "Tokens"]]
    for item in payload.get("summaries", []):
        rows.append(
            [
                item["label"],
                str(item["turns"]),
                f"{item['success']}/{item['turns']}",
                f"{item['score']:.3f}",
                f"{item['tool_match']:.3f}",
                f"{item['groundedness']:.3f}",
                f"{item['tokens']:,}",
            ]
        )
    overall = payload.get("overall", {})
    rows.append(
        [
            "Total real",
            str(overall.get("turns", "")),
            f"{overall.get('success', '')}/{overall.get('turns', '')}",
            f"{float(overall.get('score', 0)):.3f}",
            f"{float(overall.get('tool_match', 0)):.3f}",
            f"{float(overall.get('groundedness', 0)):.3f}",
            f"{int(overall.get('tokens', 0)):,}",
        ]
    )
    data = [
        [Paragraph(cell, style) for cell in row]
        for row in rows
    ]
    widths = [5.2 * cm, 1.5 * cm, 1.6 * cm, 1.5 * cm, 1.5 * cm, 1.8 * cm, 2.2 * cm]
    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#9ca3af")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
            ]
        )
    )
    return table


def build() -> int:
    payload = json.loads(RESULTS.read_text(encoding="utf-8"))
    styles = _styles()
    story: list = [
        Paragraph("Anexo de evidencias — EP3 Observabilidad", styles["title"]),
        Paragraph(
            "AgroID Huevos · ISY0101 · Esteban Pacheco Vega y Javier Perez Mora · "
            "Sección 007D",
            styles["subtitle"],
        ),
        Paragraph(
            "Este anexo reúne el resumen de las 29 corridas reales y las capturas "
            "del dashboard. Los datos por turno están en "
            "<font name='Courier'>resultados_turnos.csv</font> y el detalle "
            "estructurado en <font name='Courier'>resultados_consolidados.json</font>.",
            styles["body"],
        ),
        Paragraph("Resumen de corridas reales", styles["h2"]),
        _summary_table(payload, styles["table"]),
        Spacer(1, 8),
    ]
    ttft = payload.get("ttft", {})
    load = payload.get("load", {})
    story.extend(
        [
            Paragraph("TTFT y carga", styles["h2"]),
            Paragraph(
                f"TTFT real: {ttft.get('ttft_min_ms')}–{ttft.get('ttft_max_ms')} ms; "
                f"{ttft.get('tokens_per_second_min')}–{ttft.get('tokens_per_second_max')} "
                f"tokens/s; {ttft.get('samples')} muestras exitosas y "
                f"{ttft.get('failed')} fallidas registradas. "
                f"Carga simulada: {load.get('requests')} solicitudes, "
                f"{load.get('workers')} workers, P95 "
                f"{load.get('p95_ms')} ms, {load.get('exceptions')} errores.",
                styles["body"],
            ),
            Paragraph(
                "El intento de consistencia con 429 del proveedor se conserva en "
                "SQLite y se excluye del resumen; la corrida canónica es "
                "<font name='Courier'>real-consistency-20261123b</font>.",
                styles["body"],
            ),
        ]
    )

    for filename, caption in CAPTIONS:
        path = EVIDENCE / filename
        if not path.exists():
            continue
        story.append(PageBreak())
        story.append(Paragraph(caption.split(":")[0], styles["h2"]))
        with PILImage.open(path) as image:
            width, height = image.size
        max_width = CONTENT_WIDTH
        max_height = PAGE_HEIGHT - 2 * MARGIN - 3.2 * cm
        scale = min(max_width / width, max_height / height)
        story.append(
            Image(
                str(path),
                width=width * scale,
                height=height * scale,
            )
        )
        story.append(Paragraph(caption, styles["caption"]))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#6b7280"))
        canvas.drawString(MARGIN, 1.0 * cm, "AgroID Huevos · Anexo de evidencias EP3")
        canvas.drawRightString(
            PAGE_WIDTH - MARGIN, 1.0 * cm, f"Página {doc.page}"
        )
        canvas.restoreState()

    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=1.4 * cm,
        bottomMargin=1.4 * cm,
        title="Anexo de evidencias - AgroID EP3",
        author="Esteban Pacheco Vega y Javier Perez Mora",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(f"PDF: {OUTPUT}")
    print(f"Páginas: {doc.page}")
    return doc.page


if __name__ == "__main__":
    build()
