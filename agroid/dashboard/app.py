"""Dashboard Streamlit de observabilidad AgroID EP3."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Streamlit ejecuta el script con su propio sys.path; añadimos la raíz del repo.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from agroid.config import get_settings
from agroid.observability import metrics
from agroid.observability import store

st.set_page_config(
    page_title="AgroID · Observabilidad EP3",
    page_icon="🥚",
    layout="wide",
)

settings = get_settings()


@st.cache_data(ttl=15)
def load_data(db_path: str) -> dict[str, pd.DataFrame]:
    return metrics.load_frames(path=db_path)


def _dt(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce", utc=True)


def _json(value: Any, default: Any = None) -> Any:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def filter_frames(
    frames: dict[str, pd.DataFrame],
    run_id: str,
    groups: list[str],
    categories: list[str],
    modes: list[str] | None = None,
    real_only: bool = False,
    exclude_errors: bool = False,
) -> dict[str, pd.DataFrame]:
    traces = frames["traces"].copy()
    runs = frames.get("runs", pd.DataFrame())
    if not traces.empty:
        # ``mode`` en traces es react/plan; el tipo de corrida vive en runs.
        if not runs.empty and {"run_id", "mode"}.issubset(runs.columns):
            run_modes = runs[["run_id", "mode"]].rename(
                columns={"mode": "bench_mode"}
            )
            traces = traces.merge(run_modes, on="run_id", how="left")
            traces["bench_mode"] = traces["bench_mode"].fillna("otro")
        if run_id != "Todos" and "run_id" in traces.columns:
            traces = traces[traces["run_id"] == run_id]
        if groups and "experiment_group" in traces.columns:
            traces = traces[traces["experiment_group"].isin(groups)]
        if categories and "category" in traces.columns:
            traces = traces[traces["category"].isin(categories)]
        if modes and "mode" in traces.columns:
            traces = traces[traces["mode"].isin(modes)]
        if real_only and "bench_mode" in traces.columns:
            traces = traces[traces["bench_mode"] == "real"]
        if exclude_errors and "status" in traces.columns:
            traces = traces[traces["status"] == "success"]
    trace_ids = set(traces["trace_id"]) if not traces.empty else set()
    filtered: dict[str, pd.DataFrame] = {"traces": traces}
    for key in ("spans", "llm_calls", "tool_calls", "evaluations"):
        frame = frames.get(key, pd.DataFrame())
        if not frame.empty and "trace_id" in frame.columns:
            frame = frame[frame["trace_id"].isin(trace_ids)]
        filtered[key] = frame
    filtered["security_events"] = frames.get(
        "security_events", pd.DataFrame()
    )
    filtered["manual_integrity"] = frames.get(
        "manual_integrity", pd.DataFrame()
    )
    filtered["runs"] = frames.get("runs", pd.DataFrame())
    filtered["langsmith_runs"] = frames.get("langsmith_runs", pd.DataFrame())
    filtered["ttft"] = frames.get("ttft", pd.DataFrame())
    return filtered


def render_overview(frames: dict[str, pd.DataFrame]) -> None:
    kpis = metrics.kpis(frames)
    first = st.columns(3)
    first[0].metric("Trazas", kpis["traces"])
    first[1].metric(
        "Éxito",
        f"{kpis['success_rate']*100:.1f}%"
        if kpis["success_rate"] is not None
        else "-",
    )
    first[2].metric(
        "Error",
        f"{kpis['error_rate']*100:.1f}%"
        if kpis["error_rate"] is not None
        else "-",
    )
    second = st.columns(3)
    second[0].metric(
        "P95",
        f"{kpis['latency_p95_ms']/1000:.1f} s"
        if kpis["latency_p95_ms"] is not None
        else "-",
    )
    second[1].metric("Tokens", f"{kpis['total_tokens']:,}")
    second[2].metric(
        "Costo equiv.",
        f"${kpis['cost_equivalent_usd']:.4f}",
    )

    traces = frames["traces"]
    if traces.empty:
        st.info(
            "Aún no hay trazas. Ejecuta `python -m agroid.benchmarks.run "
            "--mode sim --suite golden` o una corrida real."
        )
        return

    traces = traces.copy()
    traces["started"] = _dt(traces["started_at"])
    left, right = st.columns([2, 1])
    with left:
        fig = px.line(
            traces.sort_values("started"),
            x="started",
            y="duration_ms",
            color="experiment_group",
            markers=True,
            labels={
                "started": "Inicio",
                "duration_ms": "Duración (ms)",
                "experiment_group": "Grupo",
            },
            title="Latencia por turno",
        )
        st.plotly_chart(fig, width="stretch")
    with right:
        status = traces["status"].fillna("desconocido").value_counts()
        fig = px.pie(
            values=status.values,
            names=status.index,
            title="Distribución de estados",
            hole=0.45,
        )
        st.plotly_chart(fig, width="stretch")

    st.subheader("Trazas recientes")
    display = traces[
        [
            "started_at",
            "session_id",
            "experiment_group",
            "category",
            "status",
            "iterations",
            "total_tokens",
            "duration_ms",
            "model_actual",
            "trace_id",
        ]
    ].sort_values("started_at", ascending=False).head(30)
    st.dataframe(display, width="stretch", hide_index=True)


def render_performance(frames: dict[str, pd.DataFrame]) -> None:
    traces = frames["traces"]
    spans = frames["spans"]
    if traces.empty:
        st.info("Sin datos de rendimiento todavía.")
        return
    left, right = st.columns(2)
    with left:
        by_kind = metrics.latency_by_kind(frames)
        if not by_kind.empty:
            fig = px.bar(
                by_kind,
                x="kind",
                y=["p50_ms", "p95_ms"],
                barmode="group",
                title="Latencia por tipo de span",
                labels={"value": "ms", "kind": "Tipo"},
            )
            st.plotly_chart(fig, width="stretch")
    with right:
        ttft = frames.get("ttft", pd.DataFrame())
        if not ttft.empty:
            ttft = ttft[ttft["status"] == "success"].copy()
            if not ttft.empty:
                fig = px.scatter(
                    ttft,
                    x="ttft_ms",
                    y="tokens_per_second",
                    color="model",
                    size="completion_tokens",
                    title="TTFT vs throughput (streaming real)",
                    labels={
                        "ttft_ms": "TTFT (ms)",
                        "tokens_per_second": "tokens/s",
                    },
                )
                st.plotly_chart(fig, width="stretch")
            else:
                st.info("No hay mediciones TTFT exitosas.")
        else:
            st.info(
                "Sin mediciones TTFT. Ejecuta "
                "`python -m agroid.benchmarks.ttft`."
            )

    st.subheader("Spans más lentos")
    if not spans.empty:
        top = spans.sort_values("duration_ms", ascending=False).head(20)
        st.dataframe(
            top[
                [
                    "trace_id",
                    "name",
                    "kind",
                    "status",
                    "duration_ms",
                    "langsmith_run_id",
                ]
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("Sin spans registrados.")

    st.subheader("Llamadas LLM")
    llm = frames["llm_calls"]
    if not llm.empty:
        st.dataframe(
            llm.sort_values("latency_ms", ascending=False).head(50)[
                [
                    "trace_id",
                    "model_requested",
                    "model_actual",
                    "prompt_tokens",
                    "completion_tokens",
                    "latency_ms",
                    "tokens_per_second",
                    "status",
                ]
            ],
            width="stretch",
            hide_index=True,
        )


def render_quality(frames: dict[str, pd.DataFrame]) -> None:
    traces = frames["traces"]
    if traces.empty:
        st.info("Sin evaluaciones todavía.")
        return
    summary = metrics.evaluations_summary(frames)
    if not summary.empty:
        st.subheader("Métricas por grupo")
        st.dataframe(summary, width="stretch", hide_index=True)
        numeric = summary.select_dtypes("number")
        if not numeric.empty:
            fig = px.bar(
                summary,
                x="experiment_group",
                y=[
                    column
                    for column in (
                        "tool_match",
                        "args_match",
                        "facts_match",
                        "groundedness",
                    )
                    if column in summary.columns
                ],
                barmode="group",
                title="Precisión, argumentos, hechos y groundedness",
                range_y=[0, 1],
            )
            st.plotly_chart(fig, width="stretch")

    consistency = metrics.consistency_summary(frames)
    if not consistency.empty:
        st.subheader("Consistencia por grupo de reformulaciones")
        st.dataframe(consistency, width="stretch", hide_index=True)

    left, right = st.columns(2)
    with left:
        tools = metrics.tool_frequency(frames)
        if not tools.empty:
            fig = px.bar(
                tools,
                x="tool_name",
                y="count",
                color="error_rate",
                title="Frecuencia de uso por herramienta",
                labels={"tool_name": "Herramienta", "count": "Llamadas"},
            )
            st.plotly_chart(fig, width="stretch")
    with right:
        errors = metrics.error_breakdown(frames)
        if not errors.empty:
            fig = px.bar(
                errors,
                x="error_type",
                y="count",
                title="Errores por tipo",
            )
            st.plotly_chart(fig, width="stretch")

    st.subheader("Anomalías detectadas")
    rows = []
    for _, trace in traces.iterrows():
        anomalies = _json(trace.get("anomalies_json"), {}) or {}
        flags = anomalies.get("flags", {}) if isinstance(anomalies, dict) else {}
        active = [key for key, value in flags.items() if value is True]
        if active:
            rows.append(
                {
                    "trace_id": trace.get("trace_id"),
                    "session_id": trace.get("session_id"),
                    "flags": ", ".join(active),
                    "details": json.dumps(
                        anomalies.get("details", {}),
                        ensure_ascii=False,
                        default=str,
                    )[:500],
                }
            )
    if rows:
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    else:
        st.success("No se detectaron bucles, deriva ni saturación de iteraciones.")


def render_costs(frames: dict[str, pd.DataFrame]) -> None:
    traces = frames["traces"]
    if traces.empty:
        st.info("Sin datos de costo.")
        return
    kpis = metrics.kpis(frames)
    projection = metrics.cost_projection(frames)
    left, right, third = st.columns(3)
    left.metric("Costo real", f"${kpis['cost_usd']:.6f}")
    right.metric("Costo equivalente", f"${kpis['cost_equivalent_usd']:.6f}")
    third.metric(
        "Proyección / 1.000",
        f"${projection['projected_equivalent']:.4f}",
    )
    st.caption(
        "El costo real es $0 cuando se usan modelos gratuitos. El costo "
        "equivalente usa un modelo pagado de referencia para comparar."
    )

    usage = metrics.model_usage(frames)
    if not usage.empty:
        fig = px.bar(
            usage,
            x="model_actual",
            y=["prompt_tokens", "completion_tokens"],
            barmode="stack",
            title="Tokens por modelo",
        )
        st.plotly_chart(fig, width="stretch")
        st.dataframe(usage, width="stretch", hide_index=True)

    traces = traces.copy()
    traces["started"] = _dt(traces["started_at"])
    traces = traces.sort_values("started")
    traces["costo_acumulado"] = traces[
        "cost_equivalent_usd"
    ].fillna(0).cumsum()
    fig = px.area(
        traces,
        x="started",
        y="costo_acumulado",
        color="experiment_group",
        title="Costo equivalente acumulado",
        labels={"started": "Inicio", "costo_acumulado": "USD"},
    )
    st.plotly_chart(fig, width="stretch")
    st.info(
        f"Tasa de entradas duplicadas: "
        f"{projection['duplicate_input_rate']*100:.1f}%. "
        "Es la base para estimar el ahorro de una caché semántica."
    )


def render_trace_explorer(frames: dict[str, pd.DataFrame]) -> None:
    traces = frames["traces"]
    if traces.empty:
        st.info("Sin trazas para explorar.")
        return
    traces = traces.sort_values("started_at", ascending=False)
    options = {
        f"{row['started_at']} · {row['experiment_group']} · "
        f"{row['trace_id'][:8]} · {row['status']}": row["trace_id"]
        for _, row in traces.iterrows()
    }
    selected = st.selectbox("Selecciona una traza", list(options.keys()))
    trace_id = options[selected]
    trace = traces[traces["trace_id"] == trace_id].iloc[0]

    first = st.columns(3)
    first[0].metric("Estado", trace.get("status", "-"))
    first[1].metric(
        "Duración", f"{float(trace.get('duration_ms') or 0)/1000:.2f} s"
    )
    first[2].metric("Iteraciones", int(trace.get("iterations") or 0))
    second = st.columns(2)
    second[0].metric("Tokens", int(trace.get("total_tokens") or 0))
    second[1].metric(
        "Costo equiv.",
        f"${float(trace.get('cost_equivalent_usd') or 0):.6f}",
    )

    st.caption(
        f"Session ID: {trace.get('session_id')} · "
        f"Trace ID interno: {trace.get('trace_id')} · "
        f"LangSmith trace: {trace.get('langsmith_trace_id') or '-'} · "
        f"Modelo: {trace.get('model_actual') or trace.get('model_requested')}"
    )

    spans = frames["spans"]
    spans = spans[spans["trace_id"] == trace_id].copy()
    if not spans.empty:
        spans["inicio"] = _dt(spans["started_at"])
        base = spans["inicio"].min()
        spans["offset_ms"] = (
            (spans["inicio"] - base).dt.total_seconds() * 1000
        ).fillna(0)
        colors = {
            "chain": "#6b7280",
            "llm": "#2563eb",
            "tool": "#ea580c",
            "retriever": "#059669",
        }
        fig = go.Figure()
        for _, span in spans.sort_values("offset_ms").iterrows():
            fig.add_trace(
                go.Bar(
                    x=[max(1.0, float(span["duration_ms"] or 0))],
                    y=[span["name"]],
                    base=[float(span["offset_ms"] or 0)],
                    orientation="h",
                    marker_color=colors.get(span["kind"], "#7c3aed"),
                    text=[
                        f"{span['kind']} · {span['duration_ms']:.0f} ms · "
                        f"{span['status']}"
                    ],
                    textposition="inside",
                    hovertemplate=(
                        f"<b>{span['name']}</b><br>"
                        f"Tipo: {span['kind']}<br>"
                        f"Duración: {span['duration_ms']:.2f} ms<br>"
                        f"Estado: {span['status']}<br>"
                        f"Span ID: {span['span_id']}<br>"
                        f"Parent: {span['parent_span_id']}<extra></extra>"
                    ),
                )
            )
        fig.update_layout(
            title="Waterfall de spans",
            xaxis_title="Tiempo desde el inicio del turno (ms)",
            yaxis_title="",
            showlegend=False,
            height=max(320, 34 * len(spans)),
            margin=dict(l=10, r=10, t=40, b=10),
        )
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, width="stretch")

        st.subheader("Árbol de spans")
        span_table = spans.sort_values("offset_ms")[
            [
                "span_id",
                "parent_span_id",
                "name",
                "kind",
                "status",
                "duration_ms",
                "langsmith_run_id",
            ]
        ]
        st.dataframe(
            span_table,
            width="stretch",
            hide_index=True,
        )

    left, right = st.columns(2)
    with left:
        st.subheader("Entrada redactada")
        st.code(str(trace.get("input_redacted") or ""), language="text")
        st.subheader("Salida redactada")
        st.code(str(trace.get("output_redacted") or ""), language="text")
    with right:
        st.subheader("Seguridad")
        st.json(_json(trace.get("security_json"), {}) or {})
        st.subheader("Anomalías")
        st.json(_json(trace.get("anomalies_json"), {}) or {})

    llm = frames["llm_calls"]
    llm = llm[llm["trace_id"] == trace_id]
    if not llm.empty:
        st.subheader("Llamadas LLM del turno")
        st.dataframe(llm, width="stretch", hide_index=True)

    tools = frames["tool_calls"]
    tools = tools[tools["trace_id"] == trace_id]
    if not tools.empty:
        st.subheader("Herramientas del turno")
        st.dataframe(tools, width="stretch", hide_index=True)


def render_security(frames: dict[str, pd.DataFrame]) -> None:
    events = frames.get("security_events", pd.DataFrame())
    integrity = frames.get("manual_integrity", pd.DataFrame())
    traces = frames.get("traces", pd.DataFrame())

    left, right = st.columns(2)
    with left:
        st.subheader("Eventos de seguridad")
        if not events.empty:
            summary = metrics.security_summary(frames)
            st.dataframe(summary, width="stretch", hide_index=True)
            st.dataframe(
                events.sort_values("created_at", ascending=False).head(50),
                width="stretch",
                hide_index=True,
            )
        else:
            st.info("Sin eventos de seguridad registrados.")
    with right:
        st.subheader("Integridad del manual")
        if not integrity.empty:
            last = integrity.sort_values("checked_at").iloc[-1]
            if int(last.get("ok") or 0) == 1:
                st.success(
                    f"Manual verificado: {last.get('checked_at')} "
                    f"({last.get('reason') or 'sin cambios'})"
                )
            else:
                st.error(
                    f"Falló la verificación: {last.get('reason')} "
                    f"({last.get('checked_at')})"
                )
            st.dataframe(
                integrity.sort_values("checked_at", ascending=False).head(20),
                width="stretch",
                hide_index=True,
            )
        else:
            st.info("Aún no se ha verificado el manual.")

    st.subheader("Redacciones de PII por turno")
    if not traces.empty:
        rows = []
        for _, trace in traces.iterrows():
            security = _json(trace.get("security_json"), {}) or {}
            pii = security.get("pii") if isinstance(security, dict) else None
            injection = (
                security.get("injection") if isinstance(security, dict) else None
            )
            if pii or injection:
                rows.append(
                    {
                        "trace_id": trace.get("trace_id"),
                        "pii": json.dumps(pii, ensure_ascii=False)
                        if pii
                        else "",
                        "injection_score": (injection or {}).get("score"),
                        "injection_matches": ", ".join(
                            (injection or {}).get("matches", [])
                        ),
                        "status": trace.get("status"),
                    }
                )
        if rows:
            st.dataframe(
                pd.DataFrame(rows), width="stretch", hide_index=True
            )
        else:
            st.info("No se registraron redacciones de PII ni intentos de inyección.")


def main() -> None:
    st.title("🥚 AgroID Huevos · Observabilidad EP3")
    st.caption(
        f"LangSmith: {settings.langsmith_project} · "
        f"SQLite: {settings.obs_db_path}"
    )

    if st.sidebar.button("Refrescar datos"):
        st.cache_data.clear()
    frames = load_data(str(settings.obs_db_path))

    runs = frames.get("runs", pd.DataFrame())
    run_options = ["Todos"]
    if not runs.empty and "run_id" in runs.columns:
        run_options += sorted(
            str(value) for value in runs["run_id"].dropna().unique()
        )
    run_id = st.sidebar.selectbox("Run", run_options)

    traces = frames.get("traces", pd.DataFrame())
    groups = sorted(
        str(value)
        for value in traces.get("experiment_group", pd.Series()).dropna().unique()
        if value
    ) if not traces.empty else []
    categories = sorted(
        str(value)
        for value in traces.get("category", pd.Series()).dropna().unique()
        if value
    ) if not traces.empty else []
    modes = sorted(
        str(value)
        for value in traces.get("mode", pd.Series()).dropna().unique()
        if value
    ) if not traces.empty else []
    selected_groups = st.sidebar.multiselect("Grupo experimental", groups)
    selected_categories = st.sidebar.multiselect("Categoría", categories)
    selected_modes = st.sidebar.multiselect("Modo del agente", modes)
    # Permite abrir una vista limpia por URL, útil para capturas y revisión:
    # ?solo_reales=1&sin_errores=1
    default_real = str(
        st.query_params.get("solo_reales", "")
    ).lower() in {"1", "true", "si", "sí"}
    default_errors = str(
        st.query_params.get("sin_errores", "")
    ).lower() in {"1", "true", "si", "sí"}
    real_only = st.sidebar.checkbox(
        "Solo corridas reales", value=default_real
    )
    exclude_errors = st.sidebar.checkbox(
        "Excluir intentos con error", value=default_errors
    )

    filtered = filter_frames(
        frames,
        run_id,
        selected_groups,
        selected_categories,
        selected_modes,
        real_only,
        exclude_errors,
    )

    tabs = st.tabs(
        [
            "Resumen",
            "Rendimiento",
            "Calidad y consistencia",
            "Costos y tokens",
            "Explorador de trazas",
            "Seguridad",
        ]
    )
    with tabs[0]:
        render_overview(filtered)
    with tabs[1]:
        render_performance(filtered)
    with tabs[2]:
        render_quality(filtered)
    with tabs[3]:
        render_costs(filtered)
    with tabs[4]:
        render_trace_explorer(filtered)
    with tabs[5]:
        render_security(filtered)

    st.sidebar.caption(
        "Los datos se leen de SQLite. Para traer trazas nuevas de LangSmith, "
        "ejecuta `python -m agroid.benchmarks.export`."
    )


if __name__ == "__main__":
    main()
