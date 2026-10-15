"""Transparent lexical fusion; deliberately not called neural dense retrieval."""
import math
import re
from collections import Counter
from .parsing import tokens

ALIASES = {"参数": "parameters parameter", "显卡": "gpu gpus", "硬件": "gpu hardware",
           "训练": "training trained", "注意力": "attention", "层数": "layers layer",
           "批次": "batch", "学习率": "learning rate", "窗口": "context window",
           "作者": "author", "机构": "university google", "未来": "future work"}

STOPWORDS = set("a an the of in on at for to from by with and or is are was were be been this that these those what which who how many much does do did used use using across compare versus as it its each can has have had into than all we our their paper model models".split())


def terms(query):
    expanded = query + " " + " ".join(value for key, value in ALIASES.items() if key in query)
    return [term for term in tokens(expanded) if term not in STOPWORDS and len(term) > 1]


def chargrams(text):
    text = re.sub(r"\s+", " ", text.lower())
    return {text[i:i + 3] for i in range(max(0, len(text) - 2))}


def retrieve(query, papers, k=8, strategy="fusion", diversify=True, facet_rerank=False):
    chunks = [{**c, "title": p["title"]} for p in papers for c in p["chunks"] if c.get("mode") != "unreadable"]
    if not chunks:
        return []
    q = terms(query)
    counts = [Counter(tokens(c["text"])) for c in chunks]
    df = Counter(t for count in counts for t in count)
    avgdl = sum(sum(c.values()) for c in counts) / len(counts) or 1
    bm, cg = [], []
    grams = chargrams(query)
    for i, count in enumerate(counts):
        length = sum(count.values())
        score = 0.0
        for term in set(q):
            freq = count[term]
            score += math.log(1 + (len(chunks) - df[term] + .5) / (df[term] + .5)) * (freq * 2.2) / (freq + 1.2 * (.25 + .75 * length / avgdl))
        bm.append((i, score))
        other = chargrams(chunks[i]["text"])
        # A shared trigram alone is not evidence relevance (e.g. random strings).
        overlap = bool(set(q) & set(count))
        cg.append((i, len(grams & other) / max(1, len(grams)) if overlap else 0))
    scores = Counter()
    rankings = [bm] if strategy == "bm25" else [cg] if strategy == "char" else [bm, cg]
    for ranked in rankings:
        for rank, (idx, score) in enumerate(sorted(ranked, key=lambda x: x[1], reverse=True)):
            if score > 0:
                scores[idx] += 1 / (60 + rank)
    if facet_rerank and re.search(r"gpu|tpu|hardware|显卡|硬件", query, re.I):
        for idx in list(scores):
            text = chunks[idx]["text"]
            # Numeric equipment details matter more than incidental model mentions.
            # This transparent feature is evaluated separately from lexical fusion.
            if re.search(r"\b(?:\d+|eight|four|sixteen)\b.{0,30}\b(?:GPUs?|TPUs?|TPU chips)\b", text, re.I):
                scores[idx] += .007
                if "NVIDIA" in text or "TPU chips" in text:
                    scores[idx] += .004
    order = sorted(scores, key=lambda i: scores[i], reverse=True)
    selected = []
    if diversify and len(papers) > 1:
        for paper in papers:
            match = next((idx for idx in order if chunks[idx]["paper_id"] == paper["id"]), None)
            if match is not None:
                selected.append(match)
            if len(selected) >= k:
                break
    selected.extend(i for i in order if i not in selected)
    return [{**chunks[i], "score": round(scores[i], 6)} for i in selected[:k]]


def validate_claims(payload, evidence):
    """Citation integrity only. Exact quotes cannot establish semantic entailment."""
    if not isinstance(payload, dict) or not isinstance(payload.get("claims"), list):
        raise ValueError("模型输出必须包含 claims 数组")
    lookup = {e["id"]: e for e in evidence}
    accepted, rejected = [], []
    for claim in payload["claims"][:30]:
        if not isinstance(claim, dict):
            rejected.append({"reason": "invalid_structure"})
            continue
        refs = claim.get("citations")
        if not isinstance(claim.get("text"), str) or not isinstance(refs, list) or not refs:
            rejected.append({"reason": "missing_claim_or_citation"})
            continue
        valid = True
        for ref in refs:
            if not isinstance(ref, dict):
                valid = False
                break
            source = lookup.get(ref.get("chunk_id"))
            quote = ref.get("quote")
            if not source or not isinstance(quote, str) or len(quote.strip()) < 8 or quote not in source["text"]:
                valid = False
                break
        (accepted if valid else rejected).append(claim if valid else {"reason": "unverifiable_quote", "claim": claim})
    return {"claims": accepted, "rejected": rejected, "semantic_entailment_verified": False}
