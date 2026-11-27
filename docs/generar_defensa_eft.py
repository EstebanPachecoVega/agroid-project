"""Genera las diapositivas PDF de la defensa EFT (11 slides, horizontal).

Uso:
    python docs/generar_defensa_eft.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "defensa_eft" / "diapositivas.pdf"
W, H = landscape(A4)
M = 1.4 * cm
NAVY = colors.HexColor("#0f172a")
BLUE = colors.HexColor("#1d4ed8")
GREEN = colors.HexColor("#059669")
AMBER = colors.HexColor("#d97706")
RED = colors.HexColor("#dc2626")
GRAY = colors.HexColor("#64748b")
LIGHT = colors.HexColor("#f1f5f9")


def wrap(text, font, size, width):
    return simpleSplit(text, font, size, width)


def title(c, text, subtitle=""):
    c.setFillColor(NAVY)
    c.rect(0, H - 2.4 * cm, W, 2.4 * cm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(M, H - 1.55 * cm, text)
    if subtitle:
        c.setFont("Helvetica", 9.5)
        c.setFillColor(colors.HexColor("#cbd5e1"))
        c.drawRightString(W - M, H - 1.55 * cm, subtitle)
    c.setFillColor(BLUE)
    c.rect(0, H - 2.5 * cm, W, 0.12 * cm, fill=1, stroke=0)


def footer(c, number):
    c.setFont("Helvetica", 7.5)
    c.setFillColor(GRAY)
    c.drawString(M, 0.7 * cm, "AgroID Huevos · EFT ISY0101 · Esteban Pacheco y Javier Perez")
    c.drawRightString(W - M, 0.7 * cm, f"{number}/11")


def bullets(c, items, x, y, width, size=12, leading=17, color=NAVY):
    c.setFillColor(color)
    for item in items:
        lines = wrap("• " + item, "Helvetica", size, width)
        for line in lines:
            c.setFont("Helvetica", size)
            c.drawString(x, y, line)
            y -= leading
        y -= 3
    return y


def image_fit(c, path, x, y, max_w, max_h, center=False):
    path = Path(path)
    if not path.exists():
        c.setFont("Helvetica-Oblique", 9)
        c.setFillColor(GRAY)
        c.drawString(x, y, f"[Imagen no disponible: {path.name}]")
        return
    with PILImage.open(path) as im:
        iw, ih = im.size
    ratio = ih / iw
    w = max_w
    h = w * ratio
    if h > max_h:
        h = max_h
        w = h / ratio
    if center:
        x = (W - w) / 2
    c.drawImage(
        str(path),
        x,
        y + (max_h - h) / 2,
        width=w,
        height=h,
        preserveAspectRatio=True,
        mask="auto",
    )


def slide_cover(c):
    c.setFillColor(NAVY)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(BLUE)
    c.rect(0, 0, 0.35 * cm, H, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 34)
    c.drawString(2.2 * cm, H - 4.2 * cm, "AgroID Huevos")
    c.setFont("Helvetica", 20)
    c.setFillColor(colors.HexColor("#93c5fd"))
    c.drawString(2.2 * cm, H - 5.4 * cm, "Agente de inventario con RAG híbrido,")
    c.drawString(2.2 * cm, H - 6.3 * cm, "planificación adaptativa y observabilidad")
    c.setFont("Helvetica", 12)
    c.setFillColor(colors.HexColor("#e2e8f0"))
    c.drawString(2.2 * cm, H - 8.0 * cm, "Evaluación Final Transversal · ISY0101 Ingeniería de Soluciones con IA")
    c.drawString(2.2 * cm, H - 8.7 * cm, "Esteban Pacheco Vega · Javier Perez Mora · Sección 007D")
    c.setFont("Helvetica-Oblique", 10)
    c.setFillColor(colors.HexColor("#94a3b8"))
    c.drawString(2.2 * cm, 2.0 * cm, "Caso verosímil con datos simulados · Defensa individual · 10 minutos")


def slide_case(c):
    title(c, "1. Caso y problema", "Dónde duele")
    bullets(
        c,
        [
            "PYME avícola con 5 especies, pedidos con fecha límite y producción diaria.",
            "La decisión real no es “cuánto stock hay”, sino qué pedido priorizar y cómo almacenar.",
            "Información dispersa: base SQLite, manual de 10 fragmentos y experiencia del encargado.",
            "Riesgo: prometer un pedido mirando solo stock, sin proyectar producción ni déficit.",
            "Datos simulados; el caso es verosímil, no un cliente real.",
        ],
        1.2 * cm,
        H - 4.0 * cm,
        W - 2.4 * cm,
        size=12.5,
        leading=18,
    )
    c.setFillColor(LIGHT)
    c.roundRect(W - 7.2 * cm, 2.0 * cm, 5.8 * cm, 4.6 * cm, 0.25 * cm, fill=1, stroke=0)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(W - 6.8 * cm, 6.0 * cm, "KPIs del caso")
    c.setFont("Helvetica", 9.5)
    for i, line in enumerate(
        [
            "Cumplimiento de pedidos",
            "Déficit proyectado",
            "Tool match ≥ 0,90",
            "Groundedness ≥ 0,85",
            "Citas ≥ 0,80",
        ]
    ):
        c.drawString(W - 6.8 * cm, 5.3 * cm - i * 0.65 * cm, "• " + line)
    footer(c, 2)


def slide_architecture(c):
    title(c, "2. Solución y arquitectura", "Cuatro capas")
    image_fit(
        c,
        ROOT / "diagramas_eft" / "ejecutivo" / "diagrama_arquitectura.png",
        1.0 * cm,
        3.2 * cm,
        27.2 * cm,
        14.6 * cm,
        center=True,
    )
    c.setFont("Helvetica-Bold", 9.2)
    c.setFillColor(NAVY)
    c.drawCentredString(
        W / 2,
        2.1 * cm,
        "Seguridad → Router → Agente → Herramientas / RAG / Memoria → Observabilidad → Dashboard",
    )
    footer(c, 3)


def slide_rag(c):
    title(c, "3. Prompts y RAG", "La evidencia manda")
    image_fit(
        c,
        ROOT / "diagramas_eft" / "ejecutivo" / "diagrama_rag_hibrido.png",
        1.0 * cm,
        3.2 * cm,
        27.2 * cm,
        14.6 * cm,
        center=True,
    )
    c.setFont("Helvetica-Bold", 9.2)
    c.setFillColor(NAVY)
    c.drawCentredString(
        W / 2,
        2.1 * cm,
        "Recall@3 0,867 · 10 internos + 14 externos · citas [Mxx]/[Exx] · SHA-256/HMAC",
    )
    footer(c, 4)


def slide_agent(c):
    title(c, "4. Agente, memoria y planificación", "Que no adivine")
    image_fit(
        c,
        ROOT / "diagramas_eft" / "ejecutivo" / "diagrama_planificacion.png",
        1.0 * cm,
        3.2 * cm,
        27.2 * cm,
        14.6 * cm,
        center=True,
    )
    c.setFont("Helvetica-Bold", 9.2)
    c.setFillColor(NAVY)
    c.drawCentredString(
        W / 2,
        2.1 * cm,
        "Auto elige ReAct o Plan · Monitor decide · una replanificación · sin repetir escrituras",
    )
    footer(c, 5)


def slide_demo(c):
    title(c, "5. Demo en 2 minutos", "Sin API keys")
    steps = [
        ("RAG", "“¿Temperatura de refrigeración según USDA?” → [E05] + [M01]."),
        ("Agente", "“Revisa déficit y prioriza” → plan + 2 herramientas + traza."),
        ("Memoria", "“Recuerda Hotel Costa” → reset RAM → “¿qué te pedí recordar?”."),
        ("Replan", "Fallo inyectado con especie inválida → replan_count=1."),
        ("Seguridad", "“Ignora tus instrucciones” → blocked, 0 tools, 0 tokens."),
    ]
    y = H - 3.6 * cm
    for i, (label, text) in enumerate(steps):
        c.setFillColor(LIGHT)
        c.roundRect(M, y - 1.1 * cm, W - 2 * M, 1.6 * cm, 0.15 * cm, fill=1, stroke=0)
        c.setFillColor(BLUE)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(M + 0.35 * cm, y - 0.45 * cm, f"{i+1}. {label}")
        c.setFillColor(NAVY)
        c.setFont("Helvetica", 10.5)
        c.drawString(M + 4.4 * cm, y - 0.45 * cm, text)
        y -= 2.0 * cm
    c.setFillColor(GRAY)
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(M, 1.7 * cm, "Plan B: modo simulado + capturas. La demo no depende de internet.")
    footer(c, 6)


def slide_results(c):
    title(c, "6. Resultados", "Real + simulado")
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(M, H - 3.8 * cm, "Suite real EFT · nemotron-3.5-lightning:free")
    rows = [
        ("Turnos", "8"),
        ("Éxito / bloqueado", "7 / 1"),
        ("Score", "0,956"),
        ("Tool match", "0,938"),
        ("Groundedness", "0,810"),
        ("Citas", "0,667"),
        ("Tokens", "40.432"),
        ("Costo real", "USD 0"),
        ("Latencia media", "8,1 s"),
    ]
    x0, y0 = M, H - 4.8 * cm
    for i, (label, value) in enumerate(rows):
        col = i % 3
        row = i // 3
        x = x0 + col * 5.6 * cm
        y = y0 - row * 1.75 * cm
        c.setFillColor(LIGHT)
        c.roundRect(x, y - 1.2 * cm, 5.1 * cm, 1.45 * cm, 0.12 * cm, fill=1, stroke=0)
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 8)
        c.drawString(x + 0.25 * cm, y - 0.05 * cm, label)
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 15)
        c.drawString(x + 0.25 * cm, y - 0.75 * cm, value)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(W - 8.4 * cm, H - 3.8 * cm, "Línea base EP3")
    c.setFont("Helvetica", 10)
    c.drawString(W - 8.4 * cm, H - 4.6 * cm, "29 turnos reales")
    c.drawString(W - 8.4 * cm, H - 5.3 * cm, "Score 0,970")
    c.drawString(W - 8.4 * cm, H - 6.0 * cm, "Tool 0,943")
    c.drawString(W - 8.4 * cm, H - 6.7 * cm, "Grounded 0,926")
    c.drawString(W - 8.4 * cm, H - 7.4 * cm, "139.773 tokens")
    c.setFillColor(AMBER)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(W - 8.4 * cm, H - 8.5 * cm, "Hallazgo: citas 0,667")
    c.setFont("Helvetica", 9)
    c.drawString(W - 8.4 * cm, H - 9.2 * cm, "El modelo cita 1 de 3 fuentes.")
    footer(c, 7)


def slide_traces(c):
    title(c, "7. Trazas y hallazgos", "Qué dicen los datos")
    image_fit(c, ROOT / "evidencias" / "captura_dashboard_traza_router.jpeg", 0.9 * cm, 2.1 * cm, 13.8 * cm, 12.0 * cm)
    c.setFont("Helvetica-Oblique", 7.5)
    c.setFillColor(GRAY)
    c.drawString(0.9 * cm, 1.75 * cm, "Captura histórica EP3; la versión EFT agrega RAG y planificación.")
    bullets(
        c,
        [
            "Router: 7/8 trazas con cambio de modelo; 10 modelos distintos.",
            "Modelo fijado: consistencia Jaccard 1,0; latencia más estable.",
            "Falsos negativos del evaluador: N05/N06 corregidos.",
            "Groundedness post-fix 0,779: cifra “4–7 °C” no respaldada.",
            "Carga 40/5: 0 errores, P95 921 ms; SQLite WAL resiste.",
        ],
        W - 10.2 * cm,
        H - 4.1 * cm,
        9.0 * cm,
        size=9.8,
        leading=13.8,
    )
    footer(c, 8)


def slide_security(c):
    title(c, "8. Seguridad y ética", "No es opcional")
    left = [
        "PII redactada antes de LLM, LangSmith, logs e historial.",
        "Inyección: patrones + delimitadores + política de herramientas.",
        "Rate limit por sesión/global; 3 escrituras y 8 iteraciones.",
        "Integridad SHA-256/HMAC; fragmentos alterados se excluyen.",
        "Bloqueo de fuga del prompt y de respuestas inseguras.",
    ]
    right = [
        "El agente no reemplaza la decisión humana en despachos de alto valor.",
        "No presenta una recomendación técnica como verdad absoluta.",
        "Datos simulados declarados; no es asesoría legal ni sanitaria.",
        "Ley 19.628 y Ley 21.719: privacidad, finalidad, retención.",
        "Riesgo residual: paráfrasis nuevas, PII en adjuntos, sesgo.",
    ]
    bullets(c, left, M, H - 4.0 * cm, 12.2 * cm, size=10.5, leading=15)
    bullets(c, right, W / 2 + 0.3 * cm, H - 4.0 * cm, 12.2 * cm, size=10.5, leading=15)
    c.setFillColor(GREEN)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(M, 2.4 * cm, "7/7 pruebas de seguridad · 0 escrituras no autorizadas")
    footer(c, 9)


def slide_improvements(c):
    title(c, "9. Mejoras y escalabilidad", "Basadas en datos")
    items = [
        ("Citas 0,667", "Cita por párrafo + crítico que bloquea sin fuente."),
        ("E04 ambiguo", "Aclarar antes de consultar; no escribir sin especie/cantidad."),
        ("Router 7/8", "Fijar modelo o routing por complejidad."),
        ("SQLite", "PostgreSQL + Redis para estado, rate limit y caché."),
        ("Escrituras", "Human-in-the-loop para pedidos > 1.000 unidades."),
        ("Costo", "Model routing, caché semántica y prompts compactos."),
    ]
    y = H - 4.0 * cm
    for i, (problem, action) in enumerate(items):
        c.setFillColor(LIGHT if i % 2 == 0 else colors.white)
        c.roundRect(M, y - 1.2 * cm, W - 2 * M, 1.55 * cm, 0.1 * cm, fill=1, stroke=0)
        c.setFillColor(AMBER)
        c.setFont("Helvetica-Bold", 10.5)
        c.drawString(M + 0.3 * cm, y - 0.45 * cm, problem)
        c.setFillColor(NAVY)
        c.setFont("Helvetica", 10.5)
        c.drawString(M + 5.0 * cm, y - 0.45 * cm, action)
        y -= 1.85 * cm
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(M, 1.9 * cm, "Roadmap: 0–1 mes citas/ambigüedad · 1–3 meses fallback/caché · 3–6 meses Postgres/Redis · 6–12 meses routing")
    footer(c, 10)


def slide_close(c):
    c.setFillColor(NAVY)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 30)
    c.drawString(2.0 * cm, H - 4.0 * cm, "El agente es observable,")
    c.drawString(2.0 * cm, H - 5.2 * cm, "corregible y tiene límites conocidos.")
    c.setFont("Helvetica", 13)
    c.setFillColor(colors.HexColor("#cbd5e1"))
    c.drawString(2.0 * cm, H - 6.8 * cm, "No decimos “funciona”: decimos qué mide, qué falla y qué sigue.")
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.HexColor("#93c5fd"))
    c.drawString(2.0 * cm, 3.4 * cm, "Gracias · ¿Preguntas?")
    c.setFont("Helvetica", 9.5)
    c.setFillColor(colors.HexColor("#94a3b8"))
    c.drawString(2.0 * cm, 2.2 * cm, "Evidencia: docs/INFORME_EFT.pdf · docs/evidencias_eft/ · AgroID_Huevos_EFT.ipynb")


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT), pagesize=landscape(A4))
    for fn in [
        slide_cover,
        slide_case,
        slide_architecture,
        slide_rag,
        slide_agent,
        slide_demo,
        slide_results,
        slide_traces,
        slide_security,
        slide_improvements,
        slide_close,
    ]:
        fn(c)
        c.showPage()
    c.save()
    print(f"PDF: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
