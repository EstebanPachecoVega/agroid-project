"""Genera los gráficos de evidencia para el deck PPTX EFT.

Salidas en ``docs/defensa_eft/evidencias``:
- ``chart_casos.png``: score por caso de la corrida real.
- ``chart_rag.png``: recall@3 por consulta RAG.
- ``chart_latencia.png``: latencia por caso.
- ``chart_waterfall_e03.png``: waterfall real de spans E03.

Uso:
    python docs/generar_graficos_defensa.py
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter

ROOT = Path(__file__).resolve().parents[1]
EVID = ROOT / "docs" / "defensa_eft" / "evidencias"
EVID.mkdir(parents=True, exist_ok=True)

NAVY = "#0B2545"
YELLOW = "#FDB913"
BLUE = "#1D4ED8"
TEAL = "#0F766E"
AMBER = "#B45309"
RED = "#B91C1C"
GRAY = "#64748B"
LIGHT = "#E2E8F0"
PURPLE = "#6D28D9"

CATEGORY_COLORS = {
    "rag_externo": BLUE,
    "rag_hibrido": TEAL,
    "complejo": AMBER,
    "ambiguo": RED,
    "adversarial": GRAY,
    "memoria": PURPLE,
}

plt.rcParams.update(
    {
        "font.family": "Arial",
        "font.size": 11,
        "axes.edgecolor": LIGHT,
        "axes.labelcolor": NAVY,
        "xtick.color": GRAY,
        "ytick.color": NAVY,
        "text.color": NAVY,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    }
)


def _clean(ax, grid_axis: str = "x") -> None:
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.grid(axis=grid_axis, color="#EDF1F7", linewidth=1)
    ax.set_axisbelow(True)


def chart_cases() -> None:
    payload = json.loads(
        (ROOT / "docs" / "evidencias_eft" / "resultados_eft.json").read_text(
            encoding="utf-8"
        )
    )
    rows = payload["rows"]
    labels = [
        f"{row['case_id']} · {row['category'].replace('_', ' ')}" for row in rows
    ]
    scores = [row["score"] for row in rows]
    colors = [CATEGORY_COLORS.get(row["category"], GRAY) for row in rows]

    fig, ax = plt.subplots(figsize=(13.2, 6.2), dpi=240)
    bars = ax.barh(labels, scores, color=colors, height=0.62)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.04)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:.2f}"))
    ax.axvline(0.956, color=NAVY, linestyle=(0, (4, 3)), linewidth=1.2)
    ax.text(
        0.961,
        -0.72,
        "media 0,956",
        color=NAVY,
        fontsize=10.5,
        fontweight="bold",
        va="bottom",
    )
    for bar, row in zip(bars, rows):
        score = row["score"]
        ax.text(
            min(score + 0.012, 1.005),
            bar.get_y() + bar.get_height() / 2,
            f"{score:.3f}".replace(".", ","),
            va="center",
            fontsize=10.5,
            color=NAVY,
            fontweight="bold",
        )
    ax.set_xlabel("Score compuesto (0 a 1)", fontsize=11.5, labelpad=8)
    _clean(ax, "x")
    ax.tick_params(axis="y", length=0, labelsize=11)
    ax.tick_params(axis="x", labelsize=10)
    fig.tight_layout(pad=0.7)
    fig.savefig(EVID / "chart_casos.png", bbox_inches="tight")
    plt.close(fig)


def chart_rag() -> None:
    payload = json.loads(
        (ROOT / "docs" / "evidencias_eft" / "rag_eval_20261127-125855.json").read_text(
            encoding="utf-8"
        )
    )
    rows = payload["rows"]
    labels = [f"{row['id']} · {row['category']}" for row in rows]
    values = [row["recall_at_k"] for row in rows]
    colors = [TEAL if value >= 0.999 else AMBER for value in values]

    fig, ax = plt.subplots(figsize=(12.6, 5.4), dpi=240)
    bars = ax.barh(labels, values, color=colors, height=0.62)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.08)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:.1f}"))
    ax.axvline(0.8667, color=NAVY, linestyle=(0, (4, 3)), linewidth=1.2)
    ax.text(
        0.872,
        -0.7,
        "recall@3 0,867",
        color=NAVY,
        fontsize=10.5,
        fontweight="bold",
        va="bottom",
    )
    for bar, value in zip(bars, values):
        ax.text(
            min(value + 0.015, 1.04),
            bar.get_y() + bar.get_height() / 2,
            f"{value:.2f}".replace(".", ","),
            va="center",
            fontsize=10,
            color=NAVY,
            fontweight="bold",
        )
    ax.set_xlabel("Recall@3 por consulta", fontsize=11.5, labelpad=8)
    _clean(ax, "x")
    ax.tick_params(axis="y", length=0, labelsize=9.5)
    ax.tick_params(axis="x", labelsize=10)
    fig.tight_layout(pad=0.7)
    fig.savefig(EVID / "chart_rag.png", bbox_inches="tight")
    plt.close(fig)


def chart_latency() -> None:
    payload = json.loads(
        (ROOT / "docs" / "evidencias_eft" / "resultados_eft.json").read_text(
            encoding="utf-8"
        )
    )
    rows = payload["rows"]
    labels = [row["case_id"] for row in rows]
    values = [row["duration_ms"] / 1000 for row in rows]
    colors = [RED if row["case_id"] == "E04" else (GRAY if row["case_id"] == "E06" else BLUE) for row in rows]
    fig, ax = plt.subplots(figsize=(12.6, 4.6), dpi=240)
    bars = ax.bar(labels, values, color=colors, width=0.58)
    for bar, value, row in zip(bars, values, rows):
        label = "bloqueado" if row["case_id"] == "E06" else f"{value:.1f} s"
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + (0.35 if value else 0.4),
            label,
            ha="center",
            fontsize=10.5,
            color=NAVY,
            fontweight="bold",
        )
    ax.set_ylim(0, max(values) * 1.18)
    ax.set_ylabel("Segundos", fontsize=10.5)
    _clean(ax, "y")
    ax.tick_params(axis="x", length=0, labelsize=11)
    ax.tick_params(axis="y", labelsize=10)
    fig.tight_layout(pad=0.5)
    fig.savefig(EVID / "chart_latencia.png", bbox_inches="tight")
    plt.close(fig)


def chart_waterfall() -> None:
    con = sqlite3.connect(ROOT / "data" / "observability.db")
    con.row_factory = sqlite3.Row
    trace = con.execute(
        "select trace_id, duration_ms from traces "
        "where session_id='visual-E03' order by started_at desc limit 1"
    ).fetchone()
    if trace is None:
        print("No hay traza visual-E03; se omite el waterfall.")
        return
    spans = con.execute(
        "select name, kind, started_at, duration_ms from spans "
        "where trace_id=? order by started_at",
        (trace["trace_id"],),
    ).fetchall()
    con.close()

    def parse(value: str) -> float:
        from datetime import datetime

        return datetime.fromisoformat(value).timestamp() * 1000

    base = min(parse(span["started_at"]) for span in spans)
    rows = [
        {
            "name": span["name"],
            "kind": span["kind"],
            "start": parse(span["started_at"]) - base,
            "duration": max(float(span["duration_ms"]), 1.0),
        }
        for span in spans
        if span["kind"] != "chain"
    ]
    rows.sort(key=lambda item: item["start"], reverse=True)

    colors = {
        "llm": BLUE,
        "tool": AMBER,
        "retriever": TEAL,
        "chain": GRAY,
    }
    fig, ax = plt.subplots(figsize=(13.2, 4.6), dpi=240)
    for index, row in enumerate(rows):
        ax.broken_barh(
            [(row["start"], max(row["duration"], 45.0))],
            (index - 0.32, 0.64),
            facecolors=colors.get(row["kind"], PURPLE),
            edgecolor="white",
            linewidth=1.2,
        )
        ax.text(
            row["start"] + max(row["duration"], 45.0) + 120,
            index,
            f"{row['duration']/1000:.2f} s",
            va="center",
            fontsize=9.5,
            color=NAVY,
            fontweight="bold",
        )
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(
        [
            row["name"]
            .replace("llm.nvidia/nemotron-3.5-lightning:free", "LLM · nemotron free")
            .replace("tool.", "Tool · ")
            .replace("retriever.", "RAG · ")
            for row in rows
        ],
        fontsize=10,
    )
    ax.set_xlabel("Tiempo desde el inicio del turno (ms)", fontsize=10.5)
    ax.set_xlim(0, max(row["start"] + row["duration"] for row in rows) * 1.25)
    _clean(ax, "x")
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", labelsize=9.5)
    handles = [
        Patch(color=BLUE, label="LLM"),
        Patch(color=AMBER, label="herramienta"),
        Patch(color=TEAL, label="retriever"),
    ]
    ax.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.16),
        frameon=False,
        fontsize=9.5,
        ncol=3,
        handlelength=1.2,
    )
    fig.tight_layout(pad=0.6)
    fig.savefig(EVID / "chart_waterfall_e03.png", bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    chart_cases()
    chart_rag()
    chart_latency()
    chart_waterfall()
    print("Gráficos generados en", EVID)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
