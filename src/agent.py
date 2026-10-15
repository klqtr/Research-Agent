"""Evidence-first workflow. Deterministic routing is disclosed as such."""
import json
import re
import time
from .model import ModelClient, ModelUnavailable
from .retrieval import retrieve, validate_claims


def answer(question, papers, settings, strategy="fusion", diversify=True, use_model=False):
    if not question.strip() or len(question) > settings.max_question_chars:
        raise ValueError("问题不能为空且不得超过配置长度")
    started = time.perf_counter()
    trace = [{"step": "plan", "status": "ok", "detail": "确定性工作流：检索 → 文献配额 → 证据输出/可选模型 → 引用校验"}]
    evidence = retrieve(question, papers, strategy=strategy, diversify=diversify, facet_rerank=True)
    trace.append({"step": "retrieve", "status": "ok", "evidence_count": len(evidence)})
    result = {"question": question, "evidence": evidence, "trace": trace, "claims": [], "mode": "extractive",
              "disclaimer": "当前为真实文档抽取式检索，未进行大模型推理。引用匹配不等于语义蕴含验证。"}
    # Reject sensitive personal-data requests and explicit absent years rather than
    # turn generic keyword matches into apparent answers. This is not an entailment model.
    private = bool(re.search(r"bank account|private (?:address|phone|email)|银行账号|身份证|私人住址", question, re.I))
    years = set(re.findall(r"\b(?:19|20)\d{2}\b", question))
    corpus = " ".join(c["text"] for p in papers for c in p["chunks"])
    absent_years = [year for year in years if year not in corpus]
    if private or absent_years:
        result.update(abstained=True, refusal_reason="不提供私人敏感信息" if private else "文献中没有问题指定年份的证据", latency_ms=round((time.perf_counter()-started)*1000, 2))
        trace.append({"step": "guard", "status": "abstained", "reason": result["refusal_reason"]})
        return result
    if use_model:
        try:
            model = ModelClient(settings).complete(json.dumps({"question": question, "evidence": evidence}, ensure_ascii=False))
            checked = validate_claims(model["output"], evidence)
            result.update(checked)
            result.update({k: v for k, v in model.items() if k != "output"})
            result["disclaimer"] = "真实模型生成；仅通过引用完整性校验，主张仍需科研人员复核。"
            trace.append({"step": "validate", "status": "ok", "accepted": len(checked["claims"]), "rejected": len(checked["rejected"])})
        except (ModelUnavailable, ValueError) as exc:
            result.update(mode="model_unavailable", error=str(exc))
            trace.append({"step": "model", "status": "unavailable"})
    elif evidence:
        result["claims"] = [{"text": e["text"], "citations": [{"chunk_id": e["id"], "quote": e["text"]}]} for e in evidence[:4]]
    result["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
    result["abstained"] = not bool(result["claims"])
    return result
