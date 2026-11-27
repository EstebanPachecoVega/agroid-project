"""CLI de AgroID Huevos EP3."""

from __future__ import annotations

import argparse
import json
import os
import sys

try:  # consola Windows: evita que los acentos se vean como caracteres raros
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AgroID Huevos EP3")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Muestra configuración y estado")
    sub.add_parser("smoke", help="Verifica dependencias, base y RAG")
    sub.add_parser("demo", help="Demo con LLM simulado (sin red)")
    sub.add_parser("eft", help="Demo EFT con LLM simulado (sin red)")
    sub.add_parser("manifest", help="Regenera el manifiesto del manual")

    chat = sub.add_parser("chat", help="Chat interactivo con el agente real")
    chat.add_argument("--session", default="cli")
    chat.add_argument("--mode", choices=["react", "plan"], default="react")

    return parser.parse_args()


def cmd_status() -> int:
    from agroid.config import get_settings

    settings = get_settings()
    settings.configure_langsmith()
    print(json.dumps(settings.safe_summary(), indent=2, ensure_ascii=False))
    return 0


def cmd_smoke() -> int:
    from agroid.agent import get_rate_limiter
    from agroid.config import get_settings
    from agroid.db import healthcheck, inicializar_bd
    from agroid.observability import store

    settings = get_settings()
    settings.configure_langsmith()
    store.init_store()
    if not healthcheck().get("ok"):
        inicializar_bd()
    report = {
        "settings": settings.safe_summary(),
        "db": healthcheck(),
        "rate_limiter": get_rate_limiter().stats(),
    }
    try:
        from agroid.rag import get_rag

        report["rag"] = get_rag().status()
    except Exception as exc:
        report["rag"] = {"error": f"{type(exc).__name__}: {exc}"}
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def cmd_manifest() -> int:
    from agroid.config import get_settings
    from agroid.security.integrity import write_manifest_for_file

    settings = get_settings()
    manifest = write_manifest_for_file(
        settings.manual_path,
        settings.manifest_path,
        hmac_key=settings.manifest_hmac_key,
    )
    print(
        json.dumps(
            {
                "manifest": str(settings.manifest_path),
                "fragments": len(manifest["fragments"]),
                "hmac": bool(manifest.get("hmac")),
            },
            indent=2,
        )
    )
    return 0


def cmd_demo() -> int:
    os.environ["LANGSMITH_TRACING"] = "false"
    from agroid.config import reload_settings

    reload_settings()
    from agroid.agent import reset_memories, run_turn
    from agroid.benchmarks.sim_llm import SimulatedLLM
    from agroid.db import inicializar_bd
    from agroid.observability import store

    store.init_store()
    inicializar_bd(reset=True)
    reset_memories()
    llm = SimulatedLLM()
    prompts = [
        (
            "Tenemos un pedido grande este mes: necesito 1800 huevos entre "
            "codorniz y pato en 5 días. Revisa si con el stock de ambos "
            "podemos cumplir la demanda.",
            "react",
        ),
        ("Acabo de recolectar 500 huevos de gallina.", "react"),
        (
            "Prioriza los pedidos pendientes y dime cómo conviene almacenar "
            "los huevos de codorniz.",
            "plan",
        ),
    ]
    for prompt, mode in prompts:
        result = run_turn(
            prompt,
            session_id="demo",
            modo=mode,
            category="demo",
            experiment_group="demo",
            model="simulado",
            llm=llm,
        )
        print("\n" + "=" * 70)
        print("Usuario:", prompt)
        print("Agente:", result.response)
        print(
            f"[trace={result.trace_id} status={result.status} "
            f"latency={result.duration_ms} ms tokens={result.total_tokens}]"
        )
    return 0


def cmd_eft() -> int:
    os.environ["LANGSMITH_TRACING"] = "false"
    from agroid.config import reload_settings

    reload_settings()
    from agroid.agent import reset_memories, run_turn
    from agroid.benchmarks.cases import EFT_CASES
    from agroid.benchmarks.sim_llm import SimulatedLLM
    from agroid.db import inicializar_bd
    from agroid.observability import store

    store.init_store()
    inicializar_bd(reset=True)
    reset_memories()
    llm = SimulatedLLM()
    for case in EFT_CASES:
        result = run_turn(
            case.input,
            session_id=f"eft-{case.id}",
            modo=case.mode,
            category=case.category,
            experiment_group="eft_demo",
            model="simulado",
            llm=llm,
        )
        print("\n" + "=" * 72)
        print(f"{case.id} · {case.category} · modo solicitado={case.mode} "
              f"efectivo={result.mode}")
        print("Usuario:", case.input)
        print("Agente:", result.response)
        print(
            f"[trace={result.trace_id} status={result.status} "
            f"tokens={result.total_tokens} replans={result.replan_count} "
            f"citas={result.citation_coverage}]"
        )
        if result.rag_sources:
            print(
                "Fuentes:",
                ", ".join(
                    f"{item.get('fragment_id')}({item.get('source_type')})"
                    for item in result.rag_sources
                ),
            )
    return 0


def cmd_chat(session: str, mode: str) -> int:
    from agroid.agent import run_turn
    from agroid.config import get_settings
    from agroid.db import inicializar_bd

    settings = get_settings()
    settings.configure_langsmith()
    if not settings.llm_api_key:
        print("Falta LLM_API_KEY. Configúrala en .env.")
        return 1
    inicializar_bd()
    print("Chat AgroID. Escribe 'salir' para terminar.")
    while True:
        try:
            text = input("Tú: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if text.lower() in {"", "salir", "exit"}:
            break
        result = run_turn(text, session_id=session, modo=mode)
        print("Agente:", result.response)
        print(
            f"[trace={result.trace_id} langsmith={result.langsmith_trace_id or '-'} "
            f"status={result.status} {result.duration_ms/1000:.1f}s]"
        )
    return 0


def main() -> int:
    args = parse_args()
    if args.command == "status":
        return cmd_status()
    if args.command == "smoke":
        return cmd_smoke()
    if args.command == "manifest":
        return cmd_manifest()
    if args.command == "demo":
        return cmd_demo()
    if args.command == "eft":
        return cmd_eft()
    if args.command == "chat":
        return cmd_chat(args.session, args.mode)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
