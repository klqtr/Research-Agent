"""Metrics from complete human annotations; missing labels stay null, never zero."""
import math
import statistics


def wilson(successes,total,z=1.96):
    if not total:return None
    probability=successes/total;denominator=1+z*z/total
    center=(probability+z*z/(2*total))/denominator
    margin=z*math.sqrt(probability*(1-probability)/total+z*z/(4*total*total))/denominator
    return [max(0,center-margin),min(1,center+margin)]


def summarize(records,annotations=None):
    annotations=annotations or []
    reviewed={row["record_id"]:row for row in annotations if row.get("reviewer_type")=="human" and row.get("reviewer_id") and row.get("complete") is True}
    completed=[row for row in records if row.get("status")=="completed_real_endpoint"]
    labels=[reviewed[row["record_id"]] for row in completed if row["record_id"] in reviewed]
    def binary(key):
        values=[row[key] for row in labels if type(row.get(key)) is bool]
        return {"value":sum(values)/len(values) if values else None,"n":len(values),"wilson95":wilson(sum(values),len(values))}
    claims=[claim for row in labels for claim in row.get("claims",[]) if claim.get("support") in ("fully_supported","partially_supported","evidence_conflict","insufficient_evidence","cannot_judge")]
    resolved=[claim for claim in claims if claim["support"]!="cannot_judge"]
    citations=[citation for row in labels for citation in row.get("citations",[]) if type(citation.get("relevant_and_supporting")) is bool]
    required=[unit for row in labels for unit in row.get("required_evidence_units",[]) if type(unit.get("covered")) is bool]
    latencies=[row["latency_ms"] for row in completed if isinstance(row.get("latency_ms"),(int,float))]
    costs=[row.get("cost_usd") for row in completed]
    return {"completed_real_endpoint":len(completed),"human_reviewed_answers":len(labels),
            "answer_correctness":binary("answer_correct"),"task_success_rate":binary("task_success"),"version_consistency":binary("version_consistent"),
            "citation_precision":sum(c["relevant_and_supporting"] for c in citations)/len(citations) if citations else None,
            "citation_recall":sum(unit["covered"] for unit in required)/len(required) if required else None,
            "evidence_support_rate":sum(c["support"]=="fully_supported" for c in resolved)/len(resolved) if resolved else None,
            "hallucination_rate":sum(c["support"] in ("evidence_conflict","insufficient_evidence") for c in resolved)/len(resolved) if resolved else None,
            "unknown_support_count":sum(c["support"]=="cannot_judge" for c in claims),
            "partial_support_count":sum(c["support"]=="partially_supported" for c in claims),
            "latency_median_ms":statistics.median(latencies) if latencies else None,
            "total_cost_usd":sum(costs) if costs and all(type(c) in (int,float) and math.isfinite(c) for c in costs) else None,
            "note":"人工标签缺失/分母为零记null；支持度无法判断单列。Wilson仅适用于已标注二元样本，非独立性/小样本不允许强统计结论。"}
