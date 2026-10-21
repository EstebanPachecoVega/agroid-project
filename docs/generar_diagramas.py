"""Genera los diagramas del proyecto AgroID Huevos (única fuente editable).

Salidas (en la misma carpeta que este script):
  - diagrama_arquitectura.png : componentes y flujo de datos
  - diagrama_secuencia.png    : un turno completo de chat() en modo plan
  - diagrama_secuencia.mmd    : el mismo diagrama de secuencia en Mermaid (GitHub lo renderiza)

Uso:  python generar_diagramas.py        (requiere matplotlib)
Para cambiar un diagrama, edita las listas BOXES/ARROWS (arquitectura) o EVENTOS (secuencia) y vuelve a ejecutar.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Ellipse, Rectangle

AQUI = os.path.dirname(os.path.abspath(__file__))
GRIS, TXT = "#4a5568", "#1a202c"
AVISOS = []


# ----------------------------------------------------------------------------------------------
# Utilidades de dibujo
# ----------------------------------------------------------------------------------------------
def caja(ax, x, y, w, h, titulo, cuerpo="", fc="#ffffff", ec=GRIS, fs=8.6, lw=1.1, ls="-", forma="round"):
    if forma == "cyl":
        el = h * 0.22
        ax.add_patch(Rectangle((x, y), w, h - el / 2, fc=fc, ec=ec, lw=lw, zorder=2))
        ax.add_patch(Ellipse((x + w / 2, y), w, el, fc=fc, ec=ec, lw=lw, zorder=2))
        ax.add_patch(Ellipse((x + w / 2, y + h - el / 2), w, el, fc=fc, ec=ec, lw=lw, zorder=3))
    else:
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.1", fc=fc, ec=ec, lw=lw,
                                    ls=ls, zorder=2))
    lineas = ([titulo] if titulo else []) + (cuerpo.split("\n") if cuerpo else [])
    paso = fs * 0.0139 / ax.figure.get_size_inches()[0] * 100 * 1.38      # alto de línea en unidades del eje
    cy = y + h / 2 + (len(lineas) - 1) * paso / 2 - (h * 0.04 if forma == "cyl" else 0)
    for i, l in enumerate(lineas):
        t = ax.text(x + w / 2, cy - i * paso, l, ha="center", va="center", fontsize=fs,
                    fontweight="bold" if (i == 0 and titulo) else "normal", color=TXT, zorder=5)
        AVISOS.append((t, x, y, w, h, l))


def flecha(ax, pts, color=GRIS, ls="-", lw=1.2, both=False, texto=None, tpos=None, ha="left", fs=7.6, rot=0, tcolor=None):
    for a, b in zip(pts[:-2], pts[1:-1]):
        ax.plot([a[0], b[0]], [a[1], b[1]], color=color, ls=ls, lw=lw, zorder=1, solid_capstyle="butt")
    (x0, y0), (x1, y1) = pts[-2], pts[-1]
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0), zorder=4,
                arrowprops=dict(arrowstyle="<|-|>" if both and len(pts) == 2 else "-|>", color=color, lw=lw, ls=ls,
                                shrinkA=0, shrinkB=0, mutation_scale=9))
    if both and len(pts) > 2:
        (a0, b0), (a1, b1) = pts[1], pts[0]
        ax.annotate("", xy=(a1, b1), xytext=(a0, b0), zorder=4,
                    arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, ls=ls, shrinkA=0, shrinkB=0, mutation_scale=9))
    if texto:
        ax.text(tpos[0], tpos[1], texto, ha=ha, va="center", fontsize=fs, color=tcolor or GRIS, rotation=rot, zorder=6,
                linespacing=1.15, bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.9))


# ----------------------------------------------------------------------------------------------
# 1) Diagrama de arquitectura
# ----------------------------------------------------------------------------------------------
def arquitectura(ruta):
    fig = plt.figure(figsize=(9.2, 9.34))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 101.6)
    ax.axis("off")

    # contenedores
    ax.add_patch(FancyBboxPatch((0.4, 3.4), 79.2, 96.4, boxstyle="round,pad=0,rounding_size=1.5", fc="#fbfbfd", ec=GRIS, lw=1.2, zorder=0))
    ax.text(1.5, 98.4, "Runtime Python · Google Colab o ejecución local", fontsize=8.4, color=GRIS, va="center", style="italic")
    ax.add_patch(FancyBboxPatch((81.4, 43.2), 18.2, 34.2, boxstyle="round,pad=0,rounding_size=1.2", fc="#fffaf0", ec="#9a6b00", lw=1.2, ls="--", zorder=0))
    ax.text(82.3, 75.6, "OpenRouter (externo)", fontsize=7.6, color="#7a5200", va="center", style="italic")
    ax.add_patch(FancyBboxPatch((25, 23.2), 53.6, 35.2, boxstyle="round,pad=0,rounding_size=1.2", fc="#f0fff4", ec="#38a169", lw=1.2, zorder=0))
    ax.text(26, 57.0, "Herramientas del agente (10) · decorador @tool", fontsize=7.8, color="#276749", va="center", style="italic")

    # nodos
    caja(ax, 38, 91.5, 24, 6, "Usuario", "notebook o chat libre", "#e8f0fe")
    caja(ax, 30, 78.8, 40, 9, "chat(texto, session_id, modo)", "Orquestador: fija SESION, arma el prompt,\nguarda el turno en SQLite", "#ffe08a")
    caja(ax, 2, 83.5, 22, 12, "Colab Secrets / entorno", "LLM_API_KEY\nLLM_BASE_URL · LLM_MODEL\nLLM_EMBED_MODEL", "#f1f5f9", ls="--")
    caja(ax, 2, 62, 22, 11, "Memoria corta", "ConversationBuffer-\nWindowMemory k = 5\n(RAM, por session_id)", "#bfdbfe")
    caja(ax, 2, 5.5, 22, 12.5, "Memoria larga", "tablas historial y datos\npor session_id\n(sobrevive al reinicio)", "#bfdbfe")
    caja(ax, 26, 62.8, 21, 10, "planificar()", "Plan-and-Execute\nplan de 3 a 5 pasos\n(solo modo = plan)", "#fecdd3")
    caja(ax, 50.5, 61.8, 24, 12.4, "AgentExecutor · ReAct", "prompt del sistema\n+ datos de la sesión\nmáx. 8 iteraciones", "#fecdd3")
    caja(ax, 84.2, 62, 14.8, 12, "LLM de chat", "openai/\ngpt-6-luna\ntemp. 0 · 60 s", "#fff0c2", ec="#9a6b00")
    caja(ax, 84.2, 46, 14.8, 10, "API embeddings", "text-embedding-\n3-small", "#fff0c2", ec="#9a6b00")

    caja(ax, 27, 43, 24, 12, "CONSULTA · lectura", "consultar_stock\nconsultar_pedidos", "#c6f6d5")
    caja(ax, 52.6, 43, 24, 12, "RAZONAMIENTO · lectura", "evaluar_cumplimiento\ncalcular_deficit\npriorizar_pedidos", "#c6f6d5")
    caja(ax, 27, 25, 24, 15.6, "ESCRITURA", "registrar_produccion\nregistrar_pedido\ndespachar_pedido\nrecordar_dato", "#fed7aa", ec="#c05621")
    caja(ax, 52.6, 30, 24, 10.6, "RECUPERACIÓN (RAG)", "buscar_manual", "#c6f6d5")

    caja(ax, 82.4, 27.5, 16.6, 11, "Recuperador", "embeddings o\nTF-IDF (respaldo)\nse fija al iniciar", "#e9d8fd")
    caja(ax, 82.4, 11, 16.6, 11, "Manual de huevos", "10 fragmentos\n(texto en el código)", "#e9d8fd", forma="cyl")
    caja(ax, 27, 6.4, 51.6, 11.6, "SQLite · agroid_huevos.db (Drive en Colab)",
         "especies · pedidos · movimientos · historial · datos", "#e9d8fd", forma="cyl")

    # flechas principales
    flecha(ax, [(46, 91.5), (46, 87.8)], texto="1 consulta", tpos=(44.8, 89.7), ha="right")
    flecha(ax, [(54, 87.8), (54, 91.5)], ls=":", texto="6 respuesta", tpos=(55.2, 89.7))
    flecha(ax, [(24, 87), (30, 85)], ls=":", texto="credenciales", tpos=(27, 89.8), ha="center")
    flecha(ax, [(30, 81.5), (13, 81.5), (13, 73)], both=True, texto="load / save", tpos=(21.5, 82.8), ha="center")
    flecha(ax, [(38.5, 78.8), (37, 72.8)], ls="--", texto="2 si modo = plan", tpos=(36, 76), ha="right")
    flecha(ax, [(57, 78.8), (60, 74.2)], texto="3 entrada + plan\n+ historial", tpos=(48, 76.4), ha="center")
    flecha(ax, [(68, 74.2), (66, 78.8)], ls=":", texto="5 respuesta\nfinal", tpos=(70.5, 76.4))
    flecha(ax, [(47, 68), (50.5, 68)], ls="--", texto="plan", tpos=(48.8, 70.3), ha="center", fs=7)
    flecha(ax, [(74.5, 68), (84.2, 68)], both=True, texto="tool calls ⇄\nobservaciones", tpos=(79.3, 71.3), ha="center", fs=7)
    flecha(ax, [(36, 62.8), (36, 60.4), (91.6, 60.4), (91.6, 62)], texto="invoke (plan)", tpos=(46, 59.4), ha="center", fs=7)
    flecha(ax, [(62.5, 61.8), (62.5, 58.4)], texto="4 herramientas", tpos=(64, 59.6))

    flecha(ax, [(40, 23.2), (40, 18)], color="#c05621", lw=1.8, texto="UPDATE / INSERT", tpos=(40.8, 20.5), tcolor="#c05621")
    flecha(ax, [(64, 23.2), (64, 18)], texto="SELECT (consulta y razonamiento)", tpos=(64.8, 20.5))
    flecha(ax, [(76.6, 35.3), (82.4, 33.5)])
    flecha(ax, [(90.7, 27.5), (90.7, 22)], texto="busca", tpos=(91.5, 24.7), fs=7)
    flecha(ax, [(90.7, 38.5), (90.7, 46)], ls="--", texto="si hay\nendpoint", tpos=(89.9, 41.8), ha="right", fs=7)
    flecha(ax, [(13, 62), (13, 18)], both=True, texto="recarga tras reinicio", tpos=(13, 40), ha="center", rot=90)
    flecha(ax, [(24, 11.8), (27, 11.8)], both=True)

    # leyenda
    y0 = 1.6
    for i, (c, t) in enumerate([("#fed7aa", "herramienta que escribe en la BD"), ("#c6f6d5", "herramienta de solo lectura"),
                                ("#fecdd3", "razonamiento del LLM"), ("#fff0c2", "servicio externo")]):
        x = 2 + i * 24.5
        ax.add_patch(Rectangle((x, y0 - 0.7), 2.4, 1.4, fc=c, ec=GRIS, lw=0.8))
        ax.text(x + 3.2, y0, t, fontsize=7.2, va="center", color=GRIS)
    fig.savefig(ruta, dpi=200)
    plt.close(fig)


# ----------------------------------------------------------------------------------------------
# 2) Diagrama de secuencia (un turno de chat en modo plan)
# ----------------------------------------------------------------------------------------------
LANES = [("U", "Usuario", "#e8f0fe"), ("C", "chat()\nOrquestador", "#ffe08a"), ("A", "AgentExecutor\n(ReAct)", "#fecdd3"),
         ("L", "LLM\n(OpenRouter)", "#fff0c2"), ("T", "Herramienta\n(@tool)", "#c6f6d5"), ("D", "SQLite\n(Drive)", "#e9d8fd"),
         ("M", "Recuperador\n(manual)", "#e9d8fd")]

EVENTOS = [
    ("msg", "U", "C", "chat(texto, session_id, modo)"),
    ("self", "C", "SESION[id] = session_id"),
    ("frame", "opt", "memoria RAM aún no cargada para esta session_id", ["C", "D"]),
    ("pair", "C", "D", "SELECT historial (últimos 10 mensajes)", "filas"),
    ("self", "C", "cargar_memoria(): ventana k = 5"),
    ("end",),
    ("pair", "C", "D", "SELECT datos de la sesión", "datos recordados"),
    ("frame", "opt", "modo = plan", ["C", "L"]),
    ("pair", "C", "L", "planificar(): plan de 3 a 5 pasos", "plan numerado"),
    ("self", "C", "entrada = texto + plan sugerido"),
    ("end",),
    ("msg", "C", "A", "invoke(entrada, hoy, datos_sesion, chat_history)"),
    ("frame", "loop", "hasta respuesta final o 8 iteraciones", ["A", "M"]),
    ("msg", "A", "L", "prompt + historial + scratchpad"),
    ("ret", "L", "A", "tool_call(nombre, args)"),
    ("msg", "A", "T", "ejecuta la herramienta con args"),
    ("frame", "alt", "consulta, razonamiento o escritura", ["T", "M"]),
    ("pair", "T", "D", "SELECT / UPDATE / INSERT", "filas o confirmación"),
    ("else", "buscar_manual"),
    ("pair", "T", "M", "buscar(consulta, k = 2)", "fragmentos con puntaje"),
    ("end",),
    ("ret", "T", "A", "observación: JSON o texto (los errores vuelven como texto)"),
    ("end",),
    ("pair", "A", "L", "observaciones acumuladas", "respuesta final"),
    ("ret", "A", "C", "output + intermediate_steps"),
    ("self", "C", "memoria.save_context(entrada, salida)"),
    ("msg", "C", "D", "INSERT historial: mensaje humano y respuesta"),
    ("ret", "C", "U", "respuesta (+ trazas si verbose)"),
    ("note", "C", "A", "Si el LLM o el agente lanzan una excepción: chat() devuelve «⚠ No pude completar la consulta…» y no guarda el turno."),
]


def secuencia(ruta_png, ruta_mmd):
    ancho, paso = 11.4, 2.12
    x_lane = {k: 8.5 + i * 16.3 for i, (k, _, _) in enumerate(LANES)}
    # primero se calcula la altura necesaria
    alto = 9.0
    for e in EVENTOS:
        alto += {"pair": 1.55, "frame": 1.25, "end": 0.75, "else": 1.2, "note": 1.9, "self": 1.4}.get(e[0], 1.0) * paso
    fig = plt.figure(figsize=(ancho, alto / 10 + 0.1))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, ancho * 10)
    ax.set_ylim(0, alto + 1)
    ax.axis("off")
    ax.text(1.5, alto - 0.2, "AgroID Huevos · Diagrama de secuencia: un turno de chat() en modo plan", fontsize=11.5, fontweight="bold", color=TXT, va="center")
    ytop = alto - 2.8
    for k, nombre, color in LANES:
        x = x_lane[k]
        ax.add_patch(FancyBboxPatch((x - 7, ytop - 3.6), 14, 4.6, boxstyle="round,pad=0,rounding_size=0.8", fc=color, ec=GRIS, lw=1.1, zorder=3))
        ax.text(x, ytop - 1.3, nombre, ha="center", va="center", fontsize=8.2, fontweight="bold", color=TXT, zorder=5, linespacing=1.1)
    y = ytop - 5.6
    y_fin = []
    pila = []                       # marcos abiertos: [tipo, etiqueta, lanes, y_inicio]
    marcos = []
    lanes_y = []

    def etiqueta(x0, x1, yy, txt, ls="-", ha="center", fs=7.7):
        ax.text((x0 + x1) / 2 if ha == "center" else x0, yy + 0.5, txt, ha=ha, va="bottom", fontsize=fs, color=TXT, zorder=6)

    def mensaje(a, b, yy, txt, retorno=False):
        xa, xb = x_lane[a], x_lane[b]
        d = 0.6 if xb > xa else -0.6
        ax.annotate("", xy=(xb - d, yy), xytext=(xa + d, yy), zorder=4,
                    arrowprops=dict(arrowstyle="-|>", color=GRIS, lw=1.15, ls="--" if retorno else "-", shrinkA=0, shrinkB=0, mutation_scale=9))
        etiqueta(min(xa, xb), max(xa, xb), yy, txt)

    for e in EVENTOS:
        t = e[0]
        if t in ("msg", "ret"):
            mensaje(e[1], e[2], y, e[3], retorno=(t == "ret"))
            y -= paso
        elif t == "pair":
            mensaje(e[1], e[2], y, e[3])
            mensaje(e[2], e[1], y - paso * 0.95, e[4], retorno=True)
            y -= paso * 1.55
        elif t == "self":
            x = x_lane[e[1]]
            ax.plot([x + 0.5, x + 4.5, x + 4.5], [y, y, y - 1.1], color=GRIS, lw=1.15, zorder=4)
            ax.annotate("", xy=(x + 0.5, y - 1.1), xytext=(x + 4.5, y - 1.1), zorder=4,
                        arrowprops=dict(arrowstyle="-|>", color=GRIS, lw=1.15, shrinkA=0, shrinkB=0, mutation_scale=9))
            ax.text(x + 5.4, y - 0.55, e[2], ha="left", va="center", fontsize=7.7, color=TXT, zorder=6)
            y -= paso * 1.4
        elif t == "frame":
            pila.append([e[1], e[2], e[3], y + 0.45 * paso])
            y -= 1.25 * paso
        elif t == "else":
            pila[-1].append((y + 0.3 * paso, e[1]))
            y -= 1.2 * paso
        elif t == "end":
            tipo, et, ls_, y0, *elses = pila.pop()
            marcos.append((tipo, et, ls_, y0, y + 0.45 * paso, elses, len(pila)))
            y -= 0.75 * paso
        elif t == "note":
            xa, xb = x_lane[e[1]] - 7, x_lane[e[2]] + 7
            ax.add_patch(FancyBboxPatch((xa, y - 2.2), 106 - xa, 3.0, boxstyle="round,pad=0,rounding_size=0.5", fc="#fffbe6", ec="#d69e2e", lw=1, zorder=3))
            ax.text(xa + 1.2, y - 0.7, e[3], ha="left", va="center", fontsize=7.7, color=TXT, zorder=6)
            y -= 1.7 * paso
    y_fin = y + 0.5 * paso
    for k, _, _ in LANES:
        ax.plot([x_lane[k]] * 2, [ytop - 3.6, y_fin], color="#a0aec0", lw=0.9, ls=(0, (4, 3)), zorder=1)
    for tipo, et, ls_, y0, y1, elses, nivel in marcos:
        x0, x1 = x_lane[ls_[0]] - 6.5 + nivel * 1.3, x_lane[ls_[1]] + 6.5 - nivel * 1.3
        ax.add_patch(Rectangle((x0, y1), x1 - x0, y0 - y1, fc="none", ec="#718096", lw=1.1, zorder=2))
        ax.add_patch(Rectangle((x0, y0 - 1.5), 5.6 + len(tipo) * 0.5, 1.5, fc="#edf2f7", ec="#718096", lw=1.1, zorder=3))
        ax.text(x0 + 0.5, y0 - 0.75, tipo, fontsize=7.6, fontweight="bold", va="center", color=TXT, zorder=6)
        ax.text(x0 + 6.4 + len(tipo) * 0.5, y0 - 0.75, f"[{et}]", fontsize=7.5, va="center", color=TXT, zorder=6)
        for ye, ee in elses:
            ax.plot([x0, x1], [ye, ye], color="#718096", lw=1, ls=(0, (5, 3)), zorder=2)
            ax.text(x0 + 0.5, ye - 0.8, f"[{ee}]", fontsize=7.5, va="center", color=TXT, zorder=6)
    fig.savefig(ruta_png, dpi=200)
    plt.close(fig)

    # ---- Mermaid equivalente (se renderiza solo en GitHub/GitLab) ----
    nombres = {"U": "Usuario", "C": "chat · Orquestador", "A": "AgentExecutor · ReAct", "L": "LLM · OpenRouter",
               "T": "Herramienta · tool", "D": "SQLite · Drive", "M": "Recuperador · manual"}
    L = ["sequenceDiagram", "    autonumber"]
    L += [f"    participant {k} as {nombres[k]}" for k, _, _ in LANES]
    sangria = 1
    p = lambda s: L.append("    " * sangria + s)
    for e in EVENTOS:
        t = e[0]
        if t == "msg":
            p(f"{e[1]}->>{e[2]}: {e[3]}")
        elif t == "ret":
            p(f"{e[1]}-->>{e[2]}: {e[3]}")
        elif t == "pair":
            p(f"{e[1]}->>{e[2]}: {e[3]}")
            p(f"{e[2]}-->>{e[1]}: {e[4]}")
        elif t == "self":
            p(f"{e[1]}->>{e[1]}: {e[2]}")
        elif t == "frame":
            p(f"{e[1]} {e[2]}")
            sangria += 1
        elif t == "else":
            sangria -= 1
            p(f"else {e[1]}")
            sangria += 1
        elif t == "end":
            sangria -= 1
            p("end")
        elif t == "note":
            p(f"Note over {e[1]},{e[2]}: {e[3]}")
    with open(ruta_mmd, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")


def revisar_desbordes():
    fig = AVISOS[0][0].figure
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    inv = AVISOS[0][0].axes.transData.inverted()
    for t, x, y, w, h, l in AVISOS:
        bb = t.get_window_extent(r)
        (x0, y0), (x1, y1) = inv.transform((bb.x0, bb.y0)), inv.transform((bb.x1, bb.y1))
        if x0 < x + 0.2 or x1 > x + w - 0.2 or y0 < y - 0.1 or y1 > y + h + 0.1:
            print(f"  ⚠ el texto «{l}» no cabe en su caja ({x1 - x0:.1f} vs {w:.1f} unidades)")


if __name__ == "__main__":
    print("Arquitectura…")
    fig_dummy = None
    arq = os.path.join(AQUI, "diagrama_arquitectura.png")
    # se revisa el desborde antes de guardar, con una figura temporal
    import types
    _orig = plt.close
    plt.close = lambda *a, **k: None
    arquitectura(arq)
    revisar_desbordes()
    plt.close = _orig
    plt.close("all")
    print("Secuencia…")
    secuencia(os.path.join(AQUI, "diagrama_secuencia.png"), os.path.join(AQUI, "diagrama_secuencia.mmd"))
    print("Listo.")
