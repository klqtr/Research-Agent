"""Run real retrieval baselines, quota ablation and citation-integrity probes."""
import hashlib
import json
import platform
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.config import Settings
from src.parsing import duplicates
from src.retrieval import retrieve, validate_claims
from src.store import Store
from src.agent import answer


def run():
    settings = Settings()
    papers = Store(settings.data_dir).papers()
    by_name = {p["filename"]: p for p in papers}
    dataset_path = ROOT / (sys.argv[1] if len(sys.argv) > 1 else "data/evaluation_cases.json")
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    cases = dataset["cases"]
    folder = ROOT / "experiments" / ("retrieval_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    folder.mkdir(parents=True)
    records, summaries = [], []
    variants = [("bm25", "bm25", False, False), ("char", "char", False, False), ("fusion_no_quota", "fusion", False, False), ("fusion_quota", "fusion", True, False), ("fusion_quota_facets", "fusion", True, True)]
    for name, strategy, diversify, facets in variants:
        rows = []
        for case in cases:
            selected = [by_name[p] for p in case["papers"]]
            start = time.perf_counter()
            evidence = retrieve(case["question"], selected, k=5, strategy=strategy, diversify=diversify, facet_rerank=facets)
            elapsed = (time.perf_counter() - start) * 1000
            hits = []
            for target in case["targets"]:
                pid = by_name[target["paper"]]["id"]
                hits.append(any(e["paper_id"] == pid and e["page"] == target["page"] and target["needle"] in e["text"] for e in evidence))
            row = {"variant": name, "case_id": case["id"], "question": case["question"], "target_hits": hits,
                   "all_targets_found": all(hits) if hits else None, "latency_ms": elapsed,
                   "multi_paper": len(selected) > 1, "unanswerable": case.get("unanswerable", False),
                   "retrieval_empty": not evidence, "evidence": evidence}
            rows.append(row)
            records.append(row)
        positives = [r for r in rows if not r["unanswerable"]]
        multi = [r for r in positives if r["multi_paper"]]
        negatives = [r for r in rows if r["unanswerable"]]
        summaries.append({"variant": name, "positive_queries": len(positives),
                          "all_target_hit_at_5": statistics.mean(r["all_targets_found"] for r in positives),
                          "target_recall_at_5": sum(sum(r["target_hits"]) for r in positives) / sum(len(r["target_hits"]) for r in positives),
                          "multi_all_hit_at_5": statistics.mean(r["all_targets_found"] for r in multi),
                          "negative_empty_retrieval_rate": statistics.mean(r["retrieval_empty"] for r in negatives),
                          "median_latency_ms": statistics.median(r["latency_ms"] for r in rows),
                          "p95_latency_ms": sorted(r["latency_ms"] for r in rows)[int(.95 * (len(rows) - 1))]})
        print(json.dumps(summaries[-1], ensure_ascii=False), flush=True)
    e = next(c for c in papers[0]["chunks"] if len(c["text"]) > 40)
    probes = [
        {"name": "real_quote", "claim": {"text": "Direct quotation", "citations": [{"chunk_id": e["id"], "quote": e["text"]}]}, "expected": True},
        {"name": "fake_chunk", "claim": {"text": "A fake claim", "citations": [{"chunk_id": "nonexistent", "quote": e["text"]}]}, "expected": False},
        {"name": "fake_quote", "claim": {"text": "A fake number", "citations": [{"chunk_id": e["id"], "quote": "The model used 99999 GPUs."}]}, "expected": False},
        {"name": "missing_citation", "claim": {"text": "No sources", "citations": []}, "expected": False},
        {"name": "wrong_entailment_real_quote", "claim": {"text": "The paper proves that all vaccines are ineffective.", "citations": [{"chunk_id": e["id"], "quote": e["text"]}]}, "expected": True}
    ]
    for probe in probes:
        probe["accepted"] = bool(validate_claims({"claims": [probe["claim"]]}, [e])["claims"])
    v1, v7 = by_name["1706.03762v1.pdf"], by_name["1706.03762v7.pdf"]
    dupe = duplicates(v1, [v7])
    negative_probes = []
    for case in cases:
        if case.get("unanswerable"):
            result = answer(case["question"], [by_name[name] for name in case["papers"]], settings)
            negative_probes.append({"id": case["id"], "abstained": result["abstained"], "refusal_reason": result.get("refusal_reason"), "mode": result["mode"], "claims": result["claims"]})
    config = {"at": datetime.now(timezone.utc).isoformat(), "python": sys.version, "platform": platform.platform(),
              "k": 5, "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
              "paper_ids": {name: paper["id"] for name, paper in by_name.items()},
              "llm_experiments": "not_run_no_authorized_model", "split": dataset.get("split", "development_only_no_holdout"), "dataset": str(dataset_path.relative_to(ROOT))}
    (folder / "config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    (folder / "raw.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records), encoding="utf-8")
    (folder / "summary.json").write_text(json.dumps({"retrieval": summaries, "citation_probes": probes, "negative_answer_probes": negative_probes, "older_version_uploaded_after_newer": dupe}, ensure_ascii=False, indent=2), encoding="utf-8")
    pointer = "LATEST_HOLDOUT.txt" if dataset.get("split") else "LATEST_RETRIEVAL.txt"
    (ROOT / "experiments" / pointer).write_text(str(folder.relative_to(ROOT)), encoding="utf-8")
    print("Saved:", folder, flush=True)


if __name__ == "__main__":
    run()
