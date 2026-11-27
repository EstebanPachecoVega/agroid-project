"""Genera los diagramas EFT de AgroID Huevos.

Salidas:
- diagrama_arquitectura_eft.png
- diagrama_rag_hibrido.png
- diagrama_planificacion.png
- diagrama_trazas_eft.png

Uso: python docs/generar_diagramas_eft.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parent
GRIS = "#4a5568"
TXT = "#1a202c"


def caja(ax, x, y, w, h, titulo, cuerpo="", fc="#ffffff", ec=GRIS, fs=8.4):
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0,rounding_size=1.0",
            fc=fc,
            ec=ec,
            lw=1.1,
            zorder=2,
        )
    )
    lines = [titulo] + (cuerpo.split("\n") if cuerpo else [])
    step = 2.6
    cy = y + h / 2 + (len(lines) - 1) * step / 2
    for index, line in enumerate(lines):
        ax.text(
            x + w / 2,
            cy - index * step,
            line,
            ha="center",
            va="center",
            fontsize=fs,
            fontweight="bold" if index == 0 else "normal",
            color=TXT,
            zorder=4,
        )


def flecha(ax, pts, color=GRIS, texto=None, tpos=None, ls="-", lw=1.2, fs=7.4):
    for a, b in zip(pts[:-1], pts[1:]):
        ax.annotate(
            "",
            xy=b,
            xytext=a,
            arrowprops=dict(
                arrowstyle="-|>",
                color=color,
                lw=lw,
                ls=ls,
                shrinkA=2,
                shrinkB=2,
                mutation_scale=9,
            ),
            zorder=1,
        )
    if texto:
        ax.text(
            tpos[0],
            tpos[1],
            texto,
            ha="center",
            va="center",
            fontsize=fs,
            color=color,
            bbox=dict(fc="white", ec="none", pad=0.5, alpha=0.9),
            zorder=5,
        )


def base(figsize):
    fig = plt.figure(figsize=figsize)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    return fig, ax


def arquitectura():
    fig, ax = base((11, 6.6))
    caja(ax, 2, 86, 18, 9, "Usuario", "chat / dashboard", "#e8f0fe")
    caja(ax, 24, 85, 24, 11, "Interfaz", "Notebook Colab\nStreamlit", "#e8f0fe")
    caja(ax, 52, 84, 22, 12, "Seguridad", "PII · inyección\nmoderación · rate limit", "#fed7d7")
    caja(ax, 78, 85, 19, 10, "LangSmith", "trazas nativas", "#fff0c2")
    caja(ax, 24, 66, 26, 11, "Router / planificador", "clasifica y elige\nreact · plan · auto", "#fefcbf")
    caja(ax, 54, 65, 24, 12, "AgentExecutor", "ReAct + Plan-and-Execute\nmáx. 8 iteraciones", "#fecdd3")
    caja(ax, 82, 66, 15, 10, "LLM", "OpenRouter\nmodelo fijado", "#fff0c2")
    caja(ax, 4, 44, 22, 13, "Herramientas", "consulta · escritura\nrazonamiento", "#c6f6d5")
    caja(ax, 30, 44, 22, 13, "RAG híbrido", "manual interno +\ncorpus externo", "#c6f6d5")
    caja(ax, 56, 44, 22, 13, "Memoria", "ventana + resumen\n+ datos por sesión", "#bfdbfe")
    caja(ax, 82, 44, 15, 13, "Integridad", "SHA-256\nHMAC", "#e9d8fd")
    caja(ax, 4, 22, 28, 13, "SQLite negocio", "especies · pedidos\nmovimientos · historial", "#e9d8fd")
    caja(ax, 36, 22, 30, 13, "SQLite observabilidad", "traces · spans · llm_calls\ntool_calls · evaluations", "#e9d8fd")
    caja(ax, 70, 22, 26, 13, "Logs JSONL", "eventos, latencia,\ntokens y seguridad", "#e9d8fd")
    caja(ax, 30, 4, 40, 11, "Dashboard Streamlit", "calidad · RAG · planificación\ncostos · trazas · seguridad", "#fbd38d")

    flecha(ax, [(20, 90.5), (24, 90.5)], texto="1", tpos=(22, 92.5))
    flecha(ax, [(48, 90.5), (52, 90.5)], texto="2", tpos=(50, 92.5))
    flecha(ax, [(63, 84), (60, 77)], texto="3", tpos=(58.5, 80.5))
    flecha(ax, [(50, 71.5), (54, 71.5)], texto="4", tpos=(52, 73.5))
    flecha(ax, [(78, 71), (82, 71)], texto="5", tpos=(80, 73))
    flecha(ax, [(66, 65), (58, 57)], texto="tool calls", tpos=(66, 61.5))
    flecha(ax, [(58, 65), (48, 57)], texto="RAG", tpos=(49, 61.5))
    flecha(ax, [(70, 65), (66, 57)], texto="memoria", tpos=(71, 61.5))
    flecha(ax, [(26, 50.5), (26, 35)], texto="SQL", tpos=(27.5, 42))
    flecha(ax, [(41, 44), (41, 35)], texto="RAG", tpos=(42.5, 39))
    flecha(ax, [(67, 44), (66, 35)], texto="contexto", tpos=(69, 39))
    flecha(ax, [(90, 44), (85, 35)], texto="verifica", tpos=(92, 39))
    flecha(ax, [(92, 66), (92, 74)], texto="traza", tpos=(94, 70))
    flecha(ax, [(50, 22), (50, 15)], texto="consulta", tpos=(51.5, 18.5))
    flecha(ax, [(30, 8), (30, 20)], ls="--", texto="evidencia", tpos=(28, 14))
    fig.savefig(ROOT / "diagrama_arquitectura_eft.png", dpi=200)
    plt.close(fig)


def rag_hibrido():
    fig, ax = base((11, 5.8))
    caja(ax, 3, 78, 20, 12, "Manual interno", "10 fragmentos\ntema + texto", "#c6f6d5")
    caja(ax, 3, 60, 20, 12, "Corpus externo", "14 fragmentos\nFAO · USDA · Codex\nINIA · extensión", "#c6f6d5")
    caja(ax, 28, 69, 18, 20, "Integridad", "manifiesto SHA-256\nHMAC opcional\nexcluye alterados", "#e9d8fd")
    caja(ax, 51, 69, 20, 20, "Índice", "embeddings\n(coseno)\no TF-IDF", "#bfdbfe")
    caja(ax, 76, 78, 20, 12, "Consulta", "pregunta del\nusuario", "#e8f0fe")
    caja(ax, 76, 60, 20, 12, "Recuperación", "top-k por fuente\nbalance interna/externa", "#fefcbf")
    caja(ax, 51, 39, 20, 15, "Merge / rerank", "score + fuente\ndeduplicación", "#fbd38d")
    caja(ax, 28, 39, 18, 15, "Citas", "[Mxx] interno\n[Exx] externo\ntítulo · URL · año", "#fbd38d")
    caja(ax, 3, 39, 20, 15, "Seguridad", "scan_untrusted\ninyección en\ndocumentos", "#fed7d7")
    caja(ax, 28, 12, 43, 16, "Respuesta del agente", "síntesis con fuentes\n+ evidencia en la traza", "#fecdd3")
    caja(ax, 78, 39, 18, 15, "Evaluación", "recall@k\ncitation coverage\ngroundedness", "#e9d8fd")
    caja(ax, 78, 12, 18, 16, "Evidencia", "rag_eval_*.csv\nresultados_eft.json", "#e9d8fd")

    flecha(ax, [(13, 78), (13, 72)], texto="texto", tpos=(15, 75))
    flecha(ax, [(23, 72), (28, 76)], texto="verifica", tpos=(24, 77))
    flecha(ax, [(37, 79), (51, 79)], texto="indexa", tpos=(44, 81.5))
    flecha(ax, [(23, 84), (51, 84)], ls="--", texto="interno", tpos=(37, 86))
    flecha(ax, [(86, 78), (86, 72)], texto="1", tpos=(88, 75))
    flecha(ax, [(76, 66), (71, 66)], texto="2", tpos=(73.5, 68))
    flecha(ax, [(61, 69), (61, 54)], texto="3", tpos=(63, 61.5))
    flecha(ax, [(51, 46.5), (46, 46.5)], texto="4", tpos=(48.5, 48.5))
    flecha(ax, [(28, 46.5), (23, 46.5)], texto="5", tpos=(25.5, 48.5))
    flecha(ax, [(46, 39), (46, 28)], texto="6", tpos=(48, 33.5))
    flecha(ax, [(78, 46.5), (78, 28)], ls="--", texto="mide", tpos=(80, 37))
    flecha(ax, [(78, 20), (71, 20)], ls="--", texto="7", tpos=(74.5, 22))
    fig.savefig(ROOT / "diagrama_rag_hibrido.png", dpi=200)
    plt.close(fig)


def planificacion():
    fig, ax = base((11, 5.6))
    caja(ax, 2, 80, 18, 10, "Consulta", "texto del usuario", "#e8f0fe")
    caja(ax, 26, 78, 20, 14, "Clasificador", "simple · compuesta\nambigua · riesgosa", "#fefcbf")
    caja(ax, 52, 80, 20, 10, "ReAct", "una acción\npor iteración", "#c6f6d5")
    caja(ax, 52, 62, 20, 12, "Plan", "objetivo + pasos\ncriterios + fallback", "#fecdd3")
    caja(ax, 78, 70, 18, 16, "Herramientas", "consulta · escritura\nrazonamiento · RAG", "#c6f6d5")
    caja(ax, 26, 48, 20, 13, "Monitor", "errores · pasos\nfaltantes · riesgo", "#fbd38d")
    caja(ax, 52, 48, 20, 13, "Decisión", "continuar\nreplanificar\ncerrar", "#fbd38d")
    caja(ax, 78, 48, 18, 13, "Crítico", "cifras\ncitas\nproblemas", "#fed7d7")
    caja(ax, 26, 20, 20, 13, "Replanificar", "máx. 1 vez\nsin repetir\nescrituras", "#fed7d7")
    caja(ax, 52, 20, 20, 13, "Respuesta", "texto + traza\n+ fuentes", "#c6f6d5")
    caja(ax, 78, 20, 18, 13, "Métricas", "iteraciones\ntokens · latencia\nreplans", "#e9d8fd")

    flecha(ax, [(20, 85), (26, 85)], texto="1", tpos=(23, 87))
    flecha(ax, [(36, 78), (36, 61)], texto="2", tpos=(38, 70))
    flecha(ax, [(46, 85), (52, 85)], texto="simple", tpos=(49, 87))
    flecha(ax, [(46, 76), (52, 68)], texto="compleja", tpos=(47, 72))
    flecha(ax, [(72, 85), (78, 82)], texto="3", tpos=(75, 85))
    flecha(ax, [(72, 68), (78, 74)], texto="4", tpos=(75, 70))
    flecha(ax, [(46, 54.5), (52, 54.5)], texto="5", tpos=(49, 56.5))
    flecha(ax, [(62, 48), (62, 39)], texto="cerrar", tpos=(64, 43.5))
    flecha(ax, [(52, 52), (46, 52)], ls="--", texto="replanificar", tpos=(49, 50))
    flecha(ax, [(36, 48), (36, 33)], texto="6", tpos=(38, 40))
    flecha(ax, [(46, 26.5), (52, 26.5)], texto="7", tpos=(49, 28.5))
    flecha(ax, [(72, 54.5), (78, 54.5)], texto="8", tpos=(75, 56.5))
    flecha(ax, [(78, 48), (78, 33)], ls="--", texto="evalúa", tpos=(80, 40))
    fig.savefig(ROOT / "diagrama_planificacion.png", dpi=200)
    plt.close(fig)


def trazas():
    fig, ax = base((10, 5.6))
    caja(ax, 35, 86, 30, 9, "Session ID", "usuario / sesión", "#e8f0fe")
    caja(ax, 35, 70, 30, 10, "Trace ID", "un turno completo", "#fefcbf")
    caja(ax, 35, 54, 30, 10, "Span raíz: chat", "prompt · plan · estado", "#fecdd3")
    caja(ax, 3, 36, 20, 10, "LLM", "modelo · tokens\nlatencia · costo", "#fff0c2")
    caja(ax, 26, 36, 20, 10, "Tool", "args · resultado\nestado · duración", "#c6f6d5")
    caja(ax, 49, 36, 20, 10, "Retriever", "fuente · score\ncitas", "#c6f6d5")
    caja(ax, 72, 36, 25, 10, "Plan / monitor", "pasos · decisión\nreplans", "#fbd38d")
    caja(ax, 3, 16, 20, 10, "JSONL", "eventos", "#e9d8fd")
    caja(ax, 26, 16, 20, 10, "SQLite obs.", "traces · spans", "#e9d8fd")
    caja(ax, 49, 16, 20, 10, "LangSmith", "árbol nativo", "#e9d8fd")
    caja(ax, 72, 16, 25, 10, "Dashboard", "KPIs · waterfall", "#fbd38d")

    flecha(ax, [(50, 86), (50, 80)])
    flecha(ax, [(50, 70), (50, 64)])
    flecha(ax, [(35, 59), (33, 46)])
    flecha(ax, [(45, 59), (36, 46)])
    flecha(ax, [(55, 59), (59, 46)])
    flecha(ax, [(65, 59), (75, 46)])
    flecha(ax, [(13, 36), (13, 26)], ls="--")
    flecha(ax, [(36, 36), (36, 26)], ls="--")
    flecha(ax, [(59, 36), (59, 26)], ls="--")
    flecha(ax, [(75, 36), (75, 26)], ls="--")
    fig.savefig(ROOT / "diagrama_trazas_eft.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    arquitectura()
    rag_hibrido()
    planificacion()
    trazas()
    print("Diagramas EFT generados en", ROOT)
