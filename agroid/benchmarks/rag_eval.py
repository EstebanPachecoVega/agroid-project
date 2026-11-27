"""Evaluación del RAG híbrido interno + externo.

Mide recuperación (recall@k), mezcla de fuentes, integridad y latencia. Se
puede ejecutar sin red forzando TF-IDF. No evalúa la calidad redaccional del
LLM; para eso está la suite EFT y la revisión humana.

Uso:
    python -m agroid.benchmarks.rag_eval
    python -m agroid.benchmarks.rag_eval --k 4
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from ..config import get_settings
from ..rag import Recuperador


CASES: list[dict[str, Any]] = [
    {
        "id": "R01",
        "query": "¿Qué temperatura de refrigeración recomienda el USDA?",
        "expected": ["E04", "E05"],
        "category": "externo",
    },
    {
        "id": "R02",
        "query": "¿Cuánto duran los huevos crudos en refrigeración?",
        "expected": ["E05", "M01"],
        "category": "hibrido",
    },
    {
        "id": "R03",
        "query": "¿Cómo almacenar huevos de codorniz?",
        "expected": ["M02", "E01", "E10"],
        "category": "hibrido",
    },
    {
        "id": "R04",
        "query": "¿Qué dice el Codex sobre huevos rotos y trazabilidad?",
        "expected": ["E07", "E08"],
        "category": "externo",
    },
    {
        "id": "R05",
        "query": "¿Cómo se clasifican los huevos por calidad y ovoscopía?",
        "expected": ["E02", "M08"],
        "category": "hibrido",
    },
    {
        "id": "R06",
        "query": "¿Cuál es la tasa de postura de la codorniz?",
        "expected": ["M04"],
        "category": "interno",
    },
    {
        "id": "R07",
        "query": "¿Cómo priorizar pedidos grandes con poco stock?",
        "expected": ["M05", "M06"],
        "category": "interno",
    },
    {
        "id": "R08",
        "query": "¿Qué cuidados requieren los huevos de pato y ganso?",
        "expected": ["M07", "M08", "E13"],
        "category": "hibrido",
    },
    {
        "id": "R09",
        "query": "¿Cómo se almacenan los huevos fértiles de incubación?",
        "expected": ["E11", "M09"],
        "category": "hibrido",
    },
    {
        "id": "R10",
        "query": "¿Qué recomienda la FDA sobre la temperatura de transporte?",
        "expected": ["E06"],
        "category": "externo",
    },
]


def evaluate(k: int = 3) -> dict[str, Any]:
    settings = get_settings()
    rag = Recuperador(force_tfidf=True)
    rows: list[dict[str, Any]] = []
    for case in CASES:
        start = perf_counter()
        hits = rag.buscar_detallado(case["query"], k=k, balance=True)
        latency_ms = round((perf_counter() - start) * 1000, 2)
        hit_ids = [hit.fragment_id for hit in hits]
        expected = set(case["expected"])
        found = expected & set(hit_ids)
        recall = len(found) / len(expected) if expected else 0.0
        rows.append(
            {
                "id": case["id"],
                "category": case["category"],
                "query": case["query"],
                "expected": ", ".join(sorted(expected)),
                "hits": ", ".join(hit_ids),
                "recall_at_k": round(recall, 4),
                "has_internal": any(hit.source_type == "interno" for hit in hits),
                "has_external": any(hit.source_type == "externo" for hit in hits),
                "latency_ms": latency_ms,
                "integrity_ok": all(
                    report.ok for report in rag.integrity.values()
                ),
            }
        )
    mean_recall = (
        sum(row["recall_at_k"] for row in rows) / len(rows) if rows else 0.0
    )
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "k": k,
        "mode": rag.modo,
        "cases": len(rows),
        "recall_at_k": round(mean_recall, 4),
        "cases_with_internal": sum(1 for row in rows if row["has_internal"]),
        "cases_with_external": sum(1 for row in rows if row["has_external"]),
        "integrity_ok": all(row["integrity_ok"] for row in rows),
        "latency_p50_ms": round(
            sorted(row["latency_ms"] for row in rows)[len(rows) // 2], 2
        )
        if rows
        else 0.0,
        "source_mix": rag.source_mix(),
        "corpora": [status.as_dict() for status in rag._corpus_status],
    }
    evidence_dir = settings.eft_evidence_dir
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    json_path = evidence_dir / f"rag_eval_{stamp}.json"
    csv_path = evidence_dir / f"rag_eval_{stamp}.csv"
    json_path.write_text(
        json.dumps(
            {"summary": summary, "rows": rows},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return {
        "summary": summary,
        "rows": rows,
        "json": str(json_path),
        "csv": str(csv_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluación RAG híbrido")
    parser.add_argument("--k", type=int, default=3)
    args = parser.parse_args()
    result = evaluate(k=args.k)
    print(json.dumps(result["summary"], indent=2, ensure_ascii=False))
    print("\nCasos:")
    for row in result["rows"]:
        print(
            f"  {row['id']} recall={row['recall_at_k']:.2f} "
            f"hits={row['hits']} ({row['latency_ms']} ms)"
        )
    print(f"\nJSON: {result['json']}\nCSV: {result['csv']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
