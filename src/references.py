"""Source-anchored reference discovery, not a scholarly-quality classifier."""
import re
from collections import Counter
from .tools import family_representatives

ARXIV_REF = re.compile(r"(?:arxiv\s*:\s*|arxiv\.org/(?:abs|pdf)/|abs/)(\d{4}\.\d{4,5})(?:v(\d+))?\b", re.I)


def reference_candidates(papers):
    local_ids = {p.get("arxiv_id") for p in papers if p.get("arxiv_id")}
    candidates = {}
    for paper in family_representatives(papers):
        start_refs = min((r["page"] for r in paper.get("references", []) if r.get("page")), default=10**8)
        mentions = Counter()
        for chunk in paper.get("chunks", []):
            if chunk["page"] >= start_refs:
                continue
            for label in re.findall(r"\[([0-9,\s]+)\]", chunk["text"]):
                mentions.update(value.strip() for value in label.split(",") if value.strip().isdigit())
        for reference in paper.get("references", []):
            for match in ARXIV_REF.finditer(reference["text"]):
                identifier = match.group(1)
                if identifier == paper.get("arxiv_id"):
                    continue
                item = candidates.setdefault(identifier, {"arxiv_id": identifier, "citing_papers": {}, "explicit_versions": set(), "anchors": []})
                label = re.match(r"^\[(\d+)\]", reference["text"])
                frequency = mentions[label.group(1)] if label else None
                item["citing_papers"][paper["id"]] = max(frequency or 0, item["citing_papers"].get(paper["id"], 0))
                if match.group(2):
                    item["explicit_versions"].add(int(match.group(2)))
                chunk = next((c for c in paper.get("chunks", []) if c["page"] == reference.get("page") and identifier in c["text"]), None)
                if len(item["anchors"]) < 8:
                    item["anchors"].append({"source_paper_id": paper["id"], "source_title": paper["title"],
                                            "page": reference.get("page"), "chunk_id": chunk["id"] if chunk else None,
                                            "reference_text": reference["text"], "numeric_citation_mentions": frequency})
    results = []
    for item in candidates.values():
        results.append({"arxiv_id": item["arxiv_id"], "explicit_versions": sorted(item["explicit_versions"]),
                        "citing_paper_count": len(item["citing_papers"]), "numeric_citation_mentions": sum(item["citing_papers"].values()),
                        "already_in_library": item["arxiv_id"] in local_ids, "anchors": item["anchors"],
                        "limitations": "引用频次仅用于可解释优先级；不能识别应付式引用或断言论文质量/相关性。作者年份引文频次未统计。"})
    return sorted(results, key=lambda item: (-item["citing_paper_count"], -item["numeric_citation_mentions"], item["arxiv_id"]))
