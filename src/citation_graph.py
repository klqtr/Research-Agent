"""Reference-local citation matching and transparent family-level PageRank."""
import re
import unicodedata
from collections import Counter


def compact(text):
    return "".join(c for c in unicodedata.normalize("NFKC", text).casefold() if c.isalnum())


def complete_title_match(title, reference, needle=None, haystack=None):
    needle, haystack = needle or compact(title), haystack or compact(reference)
    if len(needle) < 18 or needle not in haystack:
        return False
    # Preserve a map back to raw characters so a title prefix does not point to a
    # different work (e.g. Understanding Deep Learning Requires Rethinking ...).
    positions, normalized = [], []
    for index, char in enumerate(reference):
        for unit in unicodedata.normalize("NFKC", char).casefold():
            if unit.isalnum():
                normalized.append(unit)
                positions.append(index)
    start = "".join(normalized).find(needle)
    if start < 0:
        return False
    tail = reference[positions[start + len(needle) - 1] + 1:].lstrip()
    return not tail or tail[0] in ".?!;,\"”’"


def numeric_citation_counts(paper):
    first_reference_page = min((r.get("page", 10**8) for r in paper.get("references", [])), default=10**8)
    counts = Counter()
    for chunk in paper.get("chunks", []):
        if chunk["page"] >= first_reference_page:
            continue
        for label in re.findall(r"\[([0-9,\s]+)\]", chunk["text"]):
            counts.update(value.strip() for value in label.split(",") if value.strip().isdigit())
    return counts


def year_metadata(paper):
    metadata = paper.get("arxiv_metadata", {})
    match = re.match(r"^(\d{4})-", metadata.get("published", ""))
    if match:
        return int(match.group(1)), "arxiv_published_metadata"
    identifier = paper.get("arxiv_id") or ""
    if re.fullmatch(r"\d{4}\.\d{4,5}", identifier):
        year = int(identifier[:2])
        return (1900 if year >= 91 else 2000) + year, "arxiv_identifier_first_submission_year_only"
    return None, "unknown_not_inferred_from_pdf_creation_date"


def build_graph(papers):
    edges = []
    titles = {p["id"]: p["title"] for p in papers}
    normalized_titles = {key: compact(value) for key, value in titles.items()}
    patterns = {p["id"]: re.compile(r"(?<!\d)" + re.escape(p["arxiv_id"]) + r"(?!\d)") if p.get("arxiv_id") else None for p in papers}
    for source in papers:
        mentions = numeric_citation_counts(source)
        references = [(reference, compact(reference["text"])) for reference in source.get("references", [])]
        for target in papers:
            if source["id"] == target["id"]:
                continue
            matched, basis = None, None
            for reference, normalized in references:
                if patterns[target["id"]] and patterns[target["id"]].search(reference["text"]):
                    matched, basis = reference, "explicit_arxiv_identifier_in_reference"
                    break
                if complete_title_match(titles[target["id"]], reference["text"], normalized_titles[target["id"]], normalized):
                    matched, basis = reference, "complete_normalized_title_in_reference"
                    break
            if matched is None:
                continue
            anchor = next((c for c in source.get("chunks", []) if c["page"] == matched.get("page") and
                           ((patterns[target["id"]] and patterns[target["id"]].search(c["text"])) or complete_title_match(target["title"], c["text"]))), None)
            label = re.match(r"^\[(\d+)\]", matched["text"])
            edges.append({"source": source["id"], "target": target["id"], "basis": basis,
                          "cited_version": "unspecified_family", "target_family": target.get("arxiv_id") or target["id"],
                          "source_page": matched.get("page"), "source_chunk_id": anchor["id"] if anchor else None,
                          "reference_quote": matched["text"], "numeric_body_mentions": mentions[label.group(1)] if label else None,
                          "anchor_status": "reference_chunk_verified" if anchor else "reference_page_only",
                          "quality_inference": "none_citation_frequency_is_not_scholarly_quality"})
    n = len(papers)
    ranks = {p["id"]: 1/n for p in papers} if n else {}
    outgoing = {key: [edge["target"] for edge in edges if edge["source"] == key] for key in ranks}
    residual, iterations = 0.0, 0
    for step in range(200):
        dangling = sum(ranks[key] for key, targets in outgoing.items() if not targets)
        updated = {key: .15/n + .85*dangling/n for key in ranks}
        for source, targets in outgoing.items():
            for target in targets:
                updated[target] += .85*ranks[source]/len(targets)
        residual = sum(abs(updated[key]-ranks[key]) for key in ranks)
        ranks = updated
        iterations = step+1
        if residual < 1e-10:
            break
    nodes = []
    for paper in papers:
        year, year_basis = year_metadata(paper)
        nodes.append({"id": paper["id"], "title": paper["title"], "pagerank": round(ranks[paper["id"]], 8),
                      "arxiv_id": paper.get("arxiv_id"), "version": paper.get("version"), "versions": paper.get("versions", []),
                      "authors": paper.get("authors", []), "first_submission_year": year, "year_basis": year_basis})
    return {"nodes": sorted(nodes, key=lambda node: node["pagerank"], reverse=True), "edges": edges,
            "algorithm": {"name": "PageRank", "damping": .85, "max_iterations": 200, "iterations": iterations, "residual_l1": residual, "converged": residual<1e-10,
                          "weights": "unweighted_unique_family_edges", "citation_direction": "citing_paper_to_cited_paper"},
            "limitations": "同arXiv家族合并，节点用当前库内最新版本代表；边只表示论文家族引用，不表示引用了最新修订版。引用匹配/原文锚点可复核，但没有证明引用质量或完整性；PageRank不代表论文质量。"}
