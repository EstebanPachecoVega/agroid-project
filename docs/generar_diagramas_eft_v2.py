"""Genera dos familias de diagramas EFT: técnica y ejecutiva.

Salidas en docs/diagramas_eft/:
- tecnico/diagrama_arquitectura.png|.svg
- tecnico/diagrama_rag_hibrido.png|.svg
- tecnico/diagrama_planificacion.png|.svg
- tecnico/diagrama_trazas.png|.svg
- ejecutivo/... (mismos nombres)
- index.html (galería comparativa)

El objetivo es que las flechas nazcan y terminen en los bordes correctos, con
routing ortogonal, etiquetas sin superposición y una leyenda consistente.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "diagramas_eft"

INK = "#0f172a"
MUTED = "#475569"
GRID = "#cbd5e1"
ARROW = "#334155"
WHITE = "#ffffff"

BLUE_FILL = "#dbeafe"
BLUE_EDGE = "#2563eb"
GREEN_FILL = "#dcfce7"
GREEN_EDGE = "#16a34a"
AMBER_FILL = "#fef3c7"
AMBER_EDGE = "#d97706"
PURPLE_FILL = "#f3e8ff"
PURPLE_EDGE = "#7c3aed"
RED_FILL = "#fee2e2"
RED_EDGE = "#dc2626"
CYAN_FILL = "#cffafe"
CYAN_EDGE = "#0891b2"
SLATE_FILL = "#f1f5f9"
SLATE_EDGE = "#64748b"

FILLS = {
    "blue": (BLUE_FILL, BLUE_EDGE),
    "green": (GREEN_FILL, GREEN_EDGE),
    "amber": (AMBER_FILL, AMBER_EDGE),
    "purple": (PURPLE_FILL, PURPLE_EDGE),
    "red": (RED_FILL, RED_EDGE),
    "cyan": (CYAN_FILL, CYAN_EDGE),
    "slate": (SLATE_FILL, SLATE_EDGE),
}


@dataclass
class Box:
    key: str
    x: float
    y: float
    w: float
    h: float
    title: str
    body: str = ""
    color: str = "slate"
    title_size: float = 8.8
    body_size: float = 7.2

    def port(self, side: str, frac: float = 0.5) -> tuple[float, float]:
        side = side.lower()
        if side == "left":
            return (self.x, self.y + self.h * frac)
        if side == "right":
            return (self.x + self.w, self.y + self.h * frac)
        if side == "top":
            return (self.x + self.w * frac, self.y + self.h)
        if side == "bottom":
            return (self.x + self.w * frac, self.y)
        raise ValueError(f"Lado inválido: {side}")

    def center(self) -> tuple[float, float]:
        return (self.x + self.w / 2, self.y + self.h / 2)


@dataclass
class Conn:
    a: str
    sa: str
    b: str
    sb: str
    label: str = ""
    via: list[tuple[float, float]] = field(default_factory=list)
    style: str = "solid"
    both: bool = False
    color: str = ARROW
    label_pos: tuple[float, float] | None = None
    lw: float = 1.25
    sa_frac: float = 0.5
    sb_frac: float = 0.5
    ms: float = 0.0
    label_rotation: float = 0.0


@dataclass
class Diagram:
    key: str
    title: str
    subtitle: str
    boxes: dict[str, Box]
    conns: list[Conn]
    lanes: list[tuple[float, float, str]] = field(default_factory=list)
    note: str = ""


# ----------------------------------------------------------------------
# Utilidades de dibujo
# ----------------------------------------------------------------------
def draw_box(ax, box: Box, style: str, font_scale: float = 1.0) -> None:
    fill, edge = FILLS[box.color]
    lw = 1.35 if style == "ejecutivo" else 1.0
    box_patch = FancyBboxPatch(
        (box.x, box.y),
        box.w,
        box.h,
        boxstyle="round,pad=0,rounding_size=0.75",
        facecolor=fill,
        edgecolor=edge,
        linewidth=lw,
        zorder=2,
    )
    ax.add_patch(box_patch)
    if style == "ejecutivo":
        ax.add_patch(
            Rectangle(
                (box.x, box.y + 0.45),
                0.28,
                box.h - 0.9,
                facecolor=edge,
                edgecolor="none",
                zorder=3,
            )
        )
    title_y = box.y + box.h * (0.64 if box.body else 0.5)
    ax.text(
        box.x + box.w / 2,
        title_y,
        box.title,
        ha="center",
        va="center",
        fontsize=(box.title_size + (0.6 if style == "ejecutivo" else 0.0)) * font_scale,
        fontweight="bold",
        color=INK,
        zorder=5,
    )
    if box.body:
        ax.text(
            box.x + box.w / 2,
            box.y + box.h * 0.33,
            box.body,
            ha="center",
            va="center",
            fontsize=(box.body_size + (0.2 if style == "ejecutivo" else 0.0)) * font_scale,
            color=MUTED,
            linespacing=1.25,
            zorder=5,
        )


def _style_kwargs(style: str) -> dict[str, Any]:
    if style == "ejecutivo":
        return {"lw": 1.55, "ms": 11}
    return {"lw": 1.25, "ms": 9}


def draw_conn(ax, conn: Conn, boxes: dict[str, Box], style: str, font_scale: float = 1.0) -> None:
    a, b = boxes[conn.a], boxes[conn.b]
    p1 = a.port(conn.sa, conn.sa_frac)
    p2 = b.port(conn.sb, conn.sb_frac)
    pts: list[tuple[float, float]] = [p1]
    if conn.via:
        pts.extend(conn.via)
    else:
        if conn.sa in {"left", "right"} and conn.sb in {"left", "right"}:
            midx = (p1[0] + p2[0]) / 2
            pts.extend([(midx, p1[1]), (midx, p2[1])])
        elif conn.sa in {"top", "bottom"} and conn.sb in {"top", "bottom"}:
            midy = (p1[1] + p2[1]) / 2
            pts.extend([(p1[0], midy), (p2[0], midy)])
        elif conn.sa in {"left", "right"}:
            pts.append((p2[0], p1[1]))
        else:
            pts.append((p1[0], p2[1]))
    pts.append(p2)

    base = _style_kwargs(style)
    lw = conn.lw if style != "ejecutivo" else max(conn.lw, 1.45)
    ms = conn.ms or base["ms"]
    linestyle = (0, (4, 3)) if conn.style == "dashed" else "-"
    for start, end in zip(pts[:-1], pts[1:]):
        ax.plot(
            [start[0], end[0]],
            [start[1], end[1]],
            color=conn.color,
            lw=lw,
            linestyle=linestyle,
            solid_capstyle="round",
            dash_capstyle="round",
            zorder=1,
        )
    ax.add_patch(
        FancyArrowPatch(
            pts[-2],
            pts[-1],
            arrowstyle="-|>",
            mutation_scale=ms,
            color=conn.color,
            lw=lw,
            linestyle=linestyle,
            shrinkA=0,
            shrinkB=2,
            zorder=4,
        )
    )
    if conn.both:
        ax.add_patch(
            FancyArrowPatch(
                pts[1],
                pts[0],
                arrowstyle="-|>",
                mutation_scale=ms,
                color=conn.color,
                lw=lw,
                linestyle=linestyle,
                shrinkA=0,
                shrinkB=2,
                zorder=4,
            )
        )
    if conn.label:
        if conn.label_pos:
            lx, ly = conn.label_pos
            ha, va = "center", "center"
        else:
            # Etiqueta en el segmento más largo, con offset perpendicular.
            best = max(
                zip(pts[:-1], pts[1:]),
                key=lambda pair: abs(pair[1][0] - pair[0][0])
                + abs(pair[1][1] - pair[0][1]),
            )
            (x1, y1), (x2, y2) = best
            lx, ly = (x1 + x2) / 2, (y1 + y2) / 2
            if abs(x2 - x1) >= abs(y2 - y1):
                ly += 1.45
                ha, va = "center", "center"
            else:
                lx += 1.45
                ha, va = "left", "center"
        ax.text(
            lx,
            ly,
            conn.label,
            ha=ha,
            va=va,
            fontsize=(6.9 if style == "tecnico" else 7.2) * font_scale,
            color=conn.color,
            bbox=dict(
                facecolor=WHITE,
                edgecolor="none",
                pad=0.9,
                alpha=0.94,
            ),
            rotation=conn.label_rotation,
            zorder=6,
        )


def draw_lane(ax, y: float, h: float, label: str, fill: str, font_scale: float = 1.0) -> None:
    ax.add_patch(
        Rectangle(
            (2, y),
            96,
            h,
            facecolor=fill,
            edgecolor="none",
            zorder=0,
        )
    )
    ax.plot([2, 98], [y, y], color=GRID, lw=0.55, zorder=0)
    ax.text(
        3.2,
        y + h - 1.55,
        label.upper(),
        ha="left",
        va="center",
        fontsize=6.9 * font_scale,
        fontweight="bold",
        color=MUTED,
        zorder=6,
    )


def draw_header(ax, diagram: Diagram, style: str) -> None:
    ax.text(
        2,
        102.7,
        diagram.title,
        ha="left",
        va="center",
        fontsize=17 if style == "ejecutivo" else 15,
        fontweight="bold",
        color=INK,
    )
    ax.text(
        98,
        102.7,
        diagram.subtitle,
        ha="right",
        va="center",
        fontsize=8.2,
        color=MUTED,
    )
    ax.plot([2, 98], [100.3, 100.3], color=GRID, lw=0.8)


def draw_legend(ax, style: str, note: str = "", font_scale: float = 1.0) -> None:
    y = 2.2
    ax.plot([2, 7], [y, y], color=ARROW, lw=1.4)
    ax.text(7.8, y, "flujo principal", fontsize=6.8 * font_scale, color=MUTED, va="center")
    ax.plot([24, 29], [y, y], color=ARROW, lw=1.4, linestyle=(0, (4, 3)))
    ax.text(29.8, y, "telemetría / verificación", fontsize=6.8 * font_scale, color=MUTED, va="center")
    ax.add_patch(
        Rectangle((51, y - 0.7), 2.6, 1.4, facecolor=BLUE_FILL, edgecolor=BLUE_EDGE, lw=0.8)
    )
    ax.text(54.4, y, "color = capa", fontsize=6.8 * font_scale, color=MUTED, va="center")
    if style == "ejecutivo":
        ax.text(
            72,
            y,
            "swimlanes = responsabilidad",
            fontsize=6.8 * font_scale,
            color=MUTED,
            va="center",
        )
    if note:
        ax.text(2, 5.2, note, fontsize=6.8 * font_scale, color=MUTED, va="center", style="italic")


def render(diagram: Diagram, style: str, out_dir: Path, font_scale: float = 1.0, figsize=(14.2, 8.6)) -> None:
    fig = plt.figure(figsize=figsize, dpi=120)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 105)
    ax.axis("off")
    fig.patch.set_facecolor(WHITE)

    if style == "ejecutivo":
        for y, h, label in diagram.lanes:
            draw_lane(ax, y, h, label, "#f8fafc" if int(y) % 2 == 0 else "#eef2f7", font_scale)

    for box in diagram.boxes.values():
        draw_box(ax, box, style, font_scale)
    for conn in diagram.conns:
        draw_conn(ax, conn, diagram.boxes, style, font_scale)

    draw_header(ax, diagram, style)
    draw_legend(ax, style, diagram.note, font_scale)

    out_dir.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "svg"):
        path = out_dir / f"{diagram.key}.{suffix}"
        fig.savefig(
            path,
            dpi=250,
            bbox_inches="tight",
            pad_inches=0.12,
            facecolor=WHITE,
        )
    plt.close(fig)


# ----------------------------------------------------------------------
# Arquitectura
# ----------------------------------------------------------------------
def build_architecture() -> Diagram:
    boxes = {
        "usuario": Box("usuario", 3, 84, 14, 8, "Usuario", "consulta", "blue"),
        "interfaz": Box("interfaz", 22, 84, 18, 8, "Interfaz", "Notebook / dashboard", "blue"),
        "seguridad": Box("seguridad", 45, 84, 18, 8, "Seguridad", "PII · inyección · límites", "red"),
        "router": Box("router", 68, 84, 18, 8, "Router", "react · plan · auto", "amber"),
        "agent": Box("agent", 45, 62, 22, 10, "AgentExecutor", "ReAct / Plan", "amber"),
        "llm": Box("llm", 73, 62, 20, 10, "LLM", "OpenRouter fijo", "cyan"),
        "tools": Box("tools", 3, 40, 20, 10, "Herramientas", "consulta · escritura", "green"),
        "rag": Box("rag", 27, 40, 20, 10, "RAG híbrido", "manual + externo", "green"),
        "memoria": Box("memoria", 73, 40, 18, 10, "Memoria", "ventana · resumen", "blue"),
        "corpus": Box("corpus", 51, 40, 20, 10, "Corpus verificado", "SHA-256 / HMAC", "purple"),
        "sql_negocio": Box("sql_negocio", 3, 16, 22, 9, "SQLite negocio", "especies · pedidos", "purple"),
        "obs": Box("obs", 31, 16, 30, 9, "Observabilidad", "LangSmith · JSONL · SQLite", "purple"),
        "dashboard": Box("dashboard", 67, 16, 26, 9, "Dashboard", "calidad · RAG · costos", "amber"),
    }
    conns = [
        Conn("usuario", "right", "interfaz", "left", "consulta"),
        Conn("interfaz", "right", "seguridad", "left", "request"),
        Conn("seguridad", "right", "router", "left", "texto"),
        Conn(
            "router",
            "bottom",
            "agent",
            "top",
            "react / plan / auto",
            via=[(77, 78), (56, 78)],
        ),
        Conn(
            "agent",
            "right",
            "llm",
            "left",
            "tools ⇄ LLM",
            both=True,
        ),
        Conn(
            "agent",
            "bottom",
            "tools",
            "top",
            "tool calls",
            via=[(50, 56), (13, 56)],
        ),
        Conn(
            "agent",
            "bottom",
            "rag",
            "top",
            "recupera",
            via=[(56, 56), (37, 56)],
        ),
        Conn(
            "agent",
            "bottom",
            "memoria",
            "top",
            "contexto",
            via=[(62, 56), (82, 56)],
        ),
        Conn("tools", "bottom", "sql_negocio", "top", "SQL"),
        Conn(
            "memoria",
            "bottom",
            "sql_negocio",
            "top",
            "historial / datos",
            via=[(82, 30), (14, 30)],
        ),
        Conn(
            "rag",
            "right",
            "corpus",
            "left",
            "",
            both=True,
        ),
        Conn(
            "agent",
            "top",
            "obs",
            "top",
            "spans + métricas",
            style="dashed",
            via=[(60, 76), (97, 76), (97, 27), (46, 27)],
            sa_frac=0.6818,
            sb_frac=0.5,
            label_pos=(95.2, 50),
            label_rotation=90,
            color="#64748b",
            lw=1.05,
        ),
        Conn("obs", "right", "dashboard", "left", "consulta"),
    ]
    lanes = [
        (80, 17, "Entrada y control"),
        (56, 22, "Orquestación"),
        (34, 20, "Datos y conocimiento"),
        (10, 20, "Persistencia y observabilidad"),
    ]
    return Diagram(
        "diagrama_arquitectura",
        "Arquitectura EFT",
        "Usuario → seguridad → router → agente → datos → observabilidad → dashboard",
        boxes,
        conns,
        lanes,
        "El dashboard lee la base de observabilidad; no escribe en la base de negocio.",
    )


# ----------------------------------------------------------------------
# RAG híbrido
# ----------------------------------------------------------------------
def build_rag() -> Diagram:
    boxes = {
        "manual": Box("manual", 3, 82, 20, 8, "Manual interno", "10 fragmentos", "green"),
        "externo": Box("externo", 3, 68, 20, 8, "Corpus externo", "14 fragmentos citados", "green"),
        "integridad": Box("integridad", 30, 75, 18, 12, "Integridad", "SHA / HMAC\nfiltra alterados", "purple"),
        "indice": Box("indice", 55, 75, 18, 12, "Índice", "embeddings\nTF-IDF", "blue"),
        "query": Box("query", 80, 90, 15, 6, "Consulta", "pregunta", "blue"),
        "retriever": Box("retriever", 80, 68, 15, 10, "Recuperación", "top-k por fuente\nbalance", "amber"),
        "security": Box("security", 55, 50, 18, 10, "Seguridad", "scan_untrusted\ninyección", "red"),
        "merge": Box("merge", 30, 50, 18, 10, "Merge / rerank", "score · fuente\ndeduplicación", "amber"),
        "citas": Box("citas", 5, 50, 18, 10, "Citas", "[Mxx] / [Exx]\ntítulo · URL · año", "amber"),
        "respuesta": Box("respuesta", 25, 25, 28, 9, "Respuesta", "síntesis con fuentes", "red"),
        "evaluacion": Box("evaluacion", 60, 25, 18, 9, "Evaluación", "recall@k\ncitas · groundedness", "purple"),
        "evidencia": Box("evidencia", 84, 25, 13, 9, "Evidencia", "CSV / JSON", "purple"),
    }
    conns = [
        Conn(
            "manual",
            "right",
            "integridad",
            "left",
            "texto",
            via=[(26, 86), (26, 83.4)],
            sb_frac=0.7,
        ),
        Conn(
            "externo",
            "right",
            "integridad",
            "left",
            "texto",
            via=[(26, 72), (26, 78.6)],
            sb_frac=0.3,
        ),
        Conn("integridad", "right", "indice", "left", "valida + indexa"),
        Conn("query", "bottom", "retriever", "top", "consulta"),
        Conn(
            "indice",
            "right",
            "retriever",
            "left",
            "índice",
            via=[(77, 81), (77, 73)],
        ),
        Conn(
            "retriever",
            "bottom",
            "security",
            "top",
            "top-k",
            via=[(87.5, 63), (64, 63)],
        ),
        Conn("security", "left", "merge", "right", "seguros"),
        Conn("merge", "left", "citas", "right", "score + fuente"),
        Conn(
            "citas",
            "bottom",
            "respuesta",
            "top",
            "[Mxx] / [Exx]",
            via=[(14, 44), (39, 44)],
        ),
        Conn("respuesta", "right", "evaluacion", "left", "mide"),
        Conn("evaluacion", "right", "evidencia", "left", "datos"),
        Conn(
            "security",
            "bottom",
            "evidencia",
            "top",
            "incidente bloqueado",
            style="dashed",
            via=[(64, 44), (90.5, 44)],
        ),
    ]
    lanes = [
        (66, 29, "Fuentes e integridad"),
        (40, 23, "Recuperación y control"),
        (18, 19, "Generación y evidencia"),
    ]
    return Diagram(
        "diagrama_rag_hibrido",
        "RAG híbrido interno + externo",
        "Fuentes → integridad → índice → recuperación → seguridad → citas → respuesta → evidencia",
        boxes,
        conns,
        lanes,
        "La seguridad escanea los fragmentos antes del merge; la evidencia es un sumidero, no alimenta la respuesta.",
    )


# ----------------------------------------------------------------------
# Planificación
# ----------------------------------------------------------------------
def build_planning() -> Diagram:
    boxes = {
        "consulta": Box("consulta", 3, 70, 14, 8, "Consulta", "texto", "blue"),
        "clasificador": Box("clasificador", 22, 70, 18, 8, "Clasificador", "simple · compuesta\nambigua · riesgosa", "amber"),
        "react": Box("react", 47, 82, 14, 7, "ReAct", "una acción", "green"),
        "plan": Box("plan", 47, 66, 14, 7, "Plan", "pasos + fallback", "red"),
        "agent": Box("agent", 68, 70, 18, 10, "AgentExecutor", "orquesta tools", "amber"),
        "tools": Box("tools", 68, 48, 18, 8, "Herramientas", "10 tools", "green"),
        "monitor": Box("monitor", 43, 48, 16, 8, "Monitor", "errores · pasos", "amber"),
        "decision": Box("decision", 20, 48, 16, 8, "Decisión", "continuar\nreplanificar · cerrar", "amber"),
        "critico": Box("critico", 20, 22, 16, 8, "Crítico", "cifras · citas", "red"),
        "respuesta": Box("respuesta", 43, 22, 18, 8, "Respuesta", "texto + traza", "green"),
        "metricas": Box("metricas", 68, 22, 18, 8, "Métricas", "tokens · latencia", "purple"),
    }
    conns = [
        Conn("consulta", "right", "clasificador", "left", "texto"),
        Conn(
            "clasificador",
            "top",
            "react",
            "left",
            "simple",
            via=[(31, 85.5)],
        ),
        Conn(
            "clasificador",
            "right",
            "plan",
            "left",
            "compleja",
            via=[(43, 74), (43, 69.5)],
        ),
        Conn(
            "react",
            "right",
            "agent",
            "left",
            "acción",
            via=[(64, 85.5), (64, 75)],
        ),
        Conn(
            "plan",
            "right",
            "agent",
            "left",
            "plan",
            via=[(64, 69.5), (64, 72.5)],
            sb_frac=0.25,
        ),
        Conn(
            "agent",
            "bottom",
            "tools",
            "top",
            "tool calls",
            sa_frac=0.7,
            sb_frac=0.7,
        ),
        Conn("tools", "left", "monitor", "right", "observaciones"),
        Conn("monitor", "left", "decision", "right", "evalúa"),
        Conn(
            "decision",
            "top",
            "agent",
            "bottom",
            "continuar",
            style="dashed",
            via=[(28, 60), (74, 60)],
            sb_frac=0.333,
        ),
        Conn(
            "decision",
            "top",
            "plan",
            "bottom",
            "replanificar (máx. 1)",
            style="dashed",
            via=[(22, 63), (54, 63)],
            sa_frac=0.125,
        ),
        Conn("decision", "bottom", "critico", "top", "cerrar"),
        Conn("critico", "right", "respuesta", "left", "valida"),
        Conn("respuesta", "right", "metricas", "left", "registra"),
    ]
    lanes = [
        (64, 28, "Estrategia y orquestación"),
        (40, 20, "Ejecución y control"),
        (16, 20, "Salida"),
    ]
    return Diagram(
        "diagrama_planificacion",
        "Planificación adaptativa",
        "Clasificación → estrategia → ejecución → monitor → decisión → respuesta",
        boxes,
        conns,
        lanes,
        "La replanificación vuelve al plan, no a la respuesta; no reintenta escrituras exitosas.",
    )


# ----------------------------------------------------------------------
# Trazas
# ----------------------------------------------------------------------
def build_traces() -> Diagram:
    boxes = {
        "session": Box("session", 40, 90, 20, 6, "Session ID", "usuario / sesión", "blue"),
        "trace": Box("trace", 40, 80, 20, 6, "Trace ID", "un turno", "amber"),
        "chat": Box("chat", 40, 70, 20, 6, "Span raíz: chat", "prompt · plan · estado", "red"),
        "llm": Box("llm", 5, 52, 18, 7, "Span LLM", "modelo · tokens", "cyan"),
        "tool": Box("tool", 27, 52, 18, 7, "Span Tool", "args · resultado", "green"),
        "retriever": Box("retriever", 49, 52, 18, 7, "Span Retriever", "fuente · score", "green"),
        "plan": Box("plan", 71, 52, 18, 7, "Span Plan / monitor", "decisión · replans", "amber"),
        "bus": Box("bus", 5, 38, 90, 6, "Bus de observabilidad", "trace_id · span_id · parent_span_id", "purple"),
        "jsonl": Box("jsonl", 5, 17, 18, 7, "JSONL", "eventos", "purple"),
        "sqlite": Box("sqlite", 27, 17, 18, 7, "SQLite obs.", "traces · spans", "purple"),
        "langsmith": Box("langsmith", 49, 17, 18, 7, "LangSmith", "árbol nativo", "purple"),
        "dashboard": Box("dashboard", 27, 4, 40, 7, "Dashboard", "KPIs · waterfall · fuentes", "amber"),
    }
    conns = [
        Conn("session", "bottom", "trace", "top", "session_id"),
        Conn("trace", "bottom", "chat", "top", "trace_id"),
        Conn("chat", "bottom", "llm", "top", "span", via=[(50, 64), (14, 64)]),
        Conn("chat", "bottom", "tool", "top", "span", via=[(50, 64), (36, 64)]),
        Conn("chat", "bottom", "retriever", "top", "span", via=[(50, 64), (58, 64)]),
        Conn("chat", "bottom", "plan", "top", "span", via=[(50, 64), (80, 64)]),
        Conn("llm", "bottom", "bus", "top", "", via=[(14, 46.5)], sb_frac=0.1),
        Conn("tool", "bottom", "bus", "top", "", via=[(36, 46.5)], sb_frac=0.3444),
        Conn("retriever", "bottom", "bus", "top", "", via=[(58, 46.5)], sb_frac=0.5889),
        Conn("plan", "bottom", "bus", "top", "", via=[(80, 46.5)], sb_frac=0.8333),
        Conn("bus", "bottom", "jsonl", "top", "", via=[(14, 33)], sa_frac=0.1),
        Conn("bus", "bottom", "sqlite", "top", "", via=[(36, 33)], sa_frac=0.3444),
        Conn("bus", "bottom", "langsmith", "top", "", via=[(58, 33)], sa_frac=0.5889),
        Conn("sqlite", "bottom", "dashboard", "top", "consulta"),
    ]
    lanes = [
        (48, 48, "Jerarquía de spans"),
        (30, 17, "Bus de observabilidad"),
        (4, 25, "Sinks y visualización"),
    ]
    for conn in conns:
        conn.ms = 11.5
        conn.lw = 1.4
    return Diagram(
        "diagrama_trazas",
        "Trazas y observabilidad",
        "Jerarquía de spans → bus → JSONL / SQLite / LangSmith → dashboard",
        boxes,
        conns,
        lanes,
        "",
    )


# ----------------------------------------------------------------------
# Galería
# ----------------------------------------------------------------------
def gallery() -> None:
    rows = [
        ("Arquitectura", "diagrama_arquitectura"),
        ("RAG híbrido", "diagrama_rag_hibrido"),
        ("Planificación", "diagrama_planificacion"),
        ("Trazas", "diagrama_trazas"),
    ]
    cards = []
    for title, stem in rows:
        cards.append(
            f"""
            <section class="pair">
              <h2>{title}</h2>
              <div class="grid">
                <figure>
                  <a href="tecnico/{stem}.png"><img src="tecnico/{stem}.png" alt="{title} técnico"></a>
                  <figcaption><b>Técnico minimalista</b><br>Líneas finas, sin números, foco en el flujo.</figcaption>
                </figure>
                <figure>
                  <a href="ejecutivo/{stem}.png"><img src="ejecutivo/{stem}.png" alt="{title} ejecutivo"></a>
                  <figcaption><b>Ejecutivo con swimlanes</b><br>Bandas de responsabilidad, cajas más grandes, lectura para presentación.</figcaption>
                </figure>
              </div>
            </section>
            """
        )
    html = f"""<!doctype html>
<html lang="es">
<meta charset="utf-8">
<title>Diagramas EFT · comparación</title>
<style>
  :root {{ --ink:#0f172a; --muted:#475569; --line:#cbd5e1; --bg:#f8fafc; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:Segoe UI, Arial, sans-serif; color:var(--ink); background:var(--bg); }}
  header {{ padding:28px 32px 10px; }}
  h1 {{ margin:0 0 6px; font-size:26px; }}
  p {{ margin:0; color:var(--muted); max-width:1100px; line-height:1.45; }}
  main {{ padding:18px 32px 40px; }}
  .pair {{ background:white; border:1px solid var(--line); border-radius:14px; padding:18px 20px 22px; margin:18px 0; }}
  h2 {{ margin:0 0 12px; font-size:19px; }}
  .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; }}
  figure {{ margin:0; }}
  img {{ width:100%; height:auto; border:1px solid var(--line); border-radius:8px; background:white; }}
  figcaption {{ margin-top:8px; font-size:13px; color:var(--muted); line-height:1.4; }}
  .hint {{ margin-top:12px; padding:12px 14px; background:#fff7ed; border-left:4px solid #d97706; border-radius:6px; color:#7c2d12; }}
  @media (max-width:1000px) {{ .grid {{ grid-template-columns:1fr; }} }}
</style>
<header>
  <h1>Diagramas EFT · comparación de estilos</h1>
  <p>Dos familias generadas desde el mismo modelo lógico. Abre cada imagen en tamaño completo para revisar las puntas de flecha, etiquetas y conexiones. El informe ya usa la versi?n t?cnica y la defensa usa la ejecutiva. Puedes cambiar la combinaci?n cuando quieras.</p>
  <div class="hint">Recomendación: usa <b>técnico minimalista</b> en el informe y <b>ejecutivo con swimlanes</b> en la defensa. Si prefieres uno solo, el ejecutivo se lee mejor proyectado. <a href="comparacion.png">Ver contact sheet</a>.</div>
</header>
<main>
{''.join(cards)}
</main>
</html>
"""
    (OUT / "index.html").write_text(html, encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    diagrams = [
        build_architecture(),
        build_rag(),
        build_planning(),
        build_traces(),
    ]
    for style in ("tecnico", "ejecutivo"):
        for diagram in diagrams:
            if style == "tecnico":
                render(diagram, style, OUT / style, font_scale=1.3, figsize=(14.2, 8.6))
            else:
                render(diagram, style, OUT / style, font_scale=1.2)
    gallery()
    print(f"Diagramas generados en {OUT}")
    for style in ("tecnico", "ejecutivo"):
        for diagram in diagrams:
            print(f"  {style}/{diagram.key}.png")
    print(f"  index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
