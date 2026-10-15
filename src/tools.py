"""Whitelisted research tools; no execution of model-generated Python."""
import csv
import io
import math
import re
import statistics
import xml.etree.ElementTree as ET
from difflib import unified_diff
import httpx
from .parsing import similarity, tokens


def family_representatives(papers):
    families = {}
    for paper in papers:
        family = paper.get("arxiv_id") or paper["id"]
        families.setdefault(family, []).append(paper)
    representatives = []
    for versions in families.values():
        representative = max(versions, key=lambda p: p.get("version") or 0)
        representatives.append({**representative, "versions": [{"id": p["id"], "version": p.get("version")} for p in versions]})
    return representatives


def graph(papers):
    papers = family_representatives(papers)
    edges = []
    for src in papers:
        reftext = " ".join(r["text"] for r in src["references"]).lower()
        for dst in papers:
            if src["id"] == dst["id"]:
                continue
            title = re.sub(r"\s+", " ", dst["title"]).strip().lower()
            id_match = dst.get("arxiv_id") and dst["arxiv_id"] in reftext
            if id_match or (len(title) > 15 and title in reftext):
                matching_ref = next((r for r in src["references"] if title in r["text"].lower() or (dst.get("arxiv_id") and dst["arxiv_id"] in r["text"])), {})
                edges.append({"source": src["id"], "target": dst["id"], "basis": "reference_text_match",
                              "cited_version": "unspecified_family", "target_family": dst.get("arxiv_id") or dst["id"],
                              "source_page": matching_ref.get("page"), "source_chunk_id": matching_ref.get("chunk_id")})
    n = len(papers)
    ranks = {p["id"]: 1 / n for p in papers} if n else {}
    outgoing = {key: [e["target"] for e in edges if e["source"] == key] for key in ranks}
    for _ in range(60):
        dangling = sum(ranks[k] for k, out in outgoing.items() if not out)
        updated = {key: .15 / n + .85 * dangling / n for key in ranks}
        for source, targets in outgoing.items():
            for target in targets:
                updated[target] += .85 * ranks[source] / len(targets)
        if sum(abs(updated[k] - ranks[k]) for k in ranks) < 1e-10:
            ranks = updated
            break
        ranks = updated
    nodes = [{"id": p["id"], "title": p["title"], "pagerank": round(ranks[p["id"]], 6),
              "arxiv_id": p.get("arxiv_id"), "version": p.get("version"), "versions": p["versions"]} for p in papers]
    return {"nodes": sorted(nodes, key=lambda p: p["pagerank"], reverse=True), "edges": edges,
            "limitations": "同arXiv家族合并，节点用最新版本代表；边仅表示引用论文家族，不表示引用了该最新版本。仅参考文献标题/标识匹配，缺边不等于未引用；PageRank 高不等于研究质量高。"}


def future_work(papers):
    candidates = []
    for paper in papers:
        for chunk in paper["chunks"]:
            if re.search(r"future work|future research|we plan|remain[s]? (?:an? )?(?:open|challenge)", chunk["text"], re.I):
                if any(similarity(chunk["text"], c["text"]) > .6 for c in candidates):
                    continue
                candidates.append({"paper_id": paper["id"], "chunk_id": chunk["id"], "page": chunk["page"],
                                   "text": chunk["text"], "status": "待检索后续文献核验，不能视为未解决或原创 idea"})
    return candidates


def diff_versions(first, second):
    a = [c["text"] for c in first["chunks"]]
    b = [c["text"] for c in second["chunks"]]
    return {"from": first["id"], "to": second["id"], "diff": "\n".join(list(unified_diff(a, b, fromfile=first["filename"], tofile=second["filename"], lineterm=""))[:500]),
            "truncated_at_lines": 500, "method": "逐块文本差异，非模型语义总结"}


def csv_analysis(text):
    if len(text) > 2_000_000:
        raise ValueError("CSV 超过 2MB")
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    if not reader.fieldnames or len(reader.fieldnames) < 2 or len(reader.fieldnames) > 40:
        raise ValueError("CSV 需要 2–40 列及表头")
    rows = []
    for row in reader:
        rows.append(row)
        if len(rows) > 10000:
            raise ValueError("CSV 最多 10000 行")
    if not rows:
        raise ValueError("CSV 不能为空")
    numeric = {}
    for name in reader.fieldnames:
        try:
            values = [float(row[name]) for row in rows]
        except (ValueError, TypeError, KeyError):
            continue
        if not all(math.isfinite(x) for x in values):
            raise ValueError("CSV 数值必须有限，不能含 NaN/Inf")
        numeric[name] = {"values": values, "min": min(values), "max": max(values), "mean": statistics.mean(values)}
    if not numeric:
        raise ValueError("CSV 未找到完整数值列")
    labels = [row[reader.fieldnames[0]] for row in rows]
    caption = "描述性统计（未执行显著性检验）：" + "；".join(f"{key} 范围 {value['min']:.4g}–{value['max']:.4g}，均值 {value['mean']:.4g}" for key, value in numeric.items())
    return {"labels": labels, "series": numeric, "rows": len(rows), "caption": caption, "mode": "deterministic_statistics"}


def writing_outline(idea, papers):
    if not idea.strip() or len(idea) > 6000:
        raise ValueError("Idea 不能为空且最多6000字符")
    refs = [{"paper_id": p["id"], "title": p["title"], "author": p.get("author", ""), "version": p.get("version"),
             "source": (f"https://arxiv.org/abs/{p['arxiv_id']}" + (f"v{p['version']}" if p.get("version") else "")) if p.get("arxiv_id") else "本地上传文献，出版元数据待核验"} for p in family_representatives(papers)]
    return {"mode": "template", "idea": idea,
            "sections": [{"title": name, "instruction": instruction} for name, instruction in [
                ("Abstract", "描述问题、方法及真实实验结果；没有结果时明确写待验证。"),
                ("Introduction", "说明真实痛点及可检验的研究假设。"),
                ("Related Work", "只引用文献库内已核实条目，逐条检查论述与原文。"),
                ("Method", "描述可复现步骤及失效条件。"),
                ("Experiments", "报告真实数据、基线、消融与限制。")]],
            "references": refs, "mermaid": "flowchart LR\n  Input[Research question] --> Evidence[Source evidence]\n  Evidence --> Method[Proposed method]\n  Method --> Evaluation[Reproducible evaluation]",
            "disclaimer": "确定性写作模板，不是 LLM 自动撰写或新颖性证明；引用元数据需人工复核。"}


def search_arxiv(query, limit=5):
    if not query.strip() or len(query) > 300:
        raise ValueError("检索词长度须为1–300")
    with httpx.Client(timeout=20, follow_redirects=False, trust_env=False) as client:
        # Quote ordinary multi-word topics as a phrase; passing bare words makes
        # arXiv interpret later words broadly and returned unrelated recent papers.
        cleaned = query.replace('"', ' ').strip()
        response = client.get("https://export.arxiv.org/api/query", params={"search_query": 'all:"' + cleaned + '"', "max_results": min(limit, 10), "sortBy": "submittedDate", "sortOrder": "descending"})
        response.raise_for_status()
    try:
        root = ET.fromstring(response.content)
    except ET.ParseError as exc:
        raise ValueError("arXiv返回的元数据不是有效XML") from exc
    ns = {"a": "http://www.w3.org/2005/Atom"}
    results = []
    for entry in root.findall("a:entry", ns):
        abstract = entry.findtext("a:summary", "", ns)
        results.append({"title": entry.findtext("a:title", "", ns).strip(), "url": entry.findtext("a:id", "", ns),
                        "published": entry.findtext("a:published", "", ns), "abstract": abstract.strip(),
                        "code_available": "github.com" in abstract.lower(),
                        "reason": "按最新提交排序；摘要含 GitHub 链接时标记代码线索，尚未核验仓库可运行性。"})
    return results


def download_arxiv_pdf(identifier, max_bytes):
    if not re.fullmatch(r"\d{4}\.\d{4,5}(?:v\d+)?", identifier):
        raise ValueError("需要有效arXiv数字标识，不接受任意URL")
    url = "https://arxiv.org/pdf/" + identifier
    raw = bytearray()
    with httpx.Client(timeout=35, follow_redirects=False, trust_env=False) as client:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            if 300 <= response.status_code < 400:
                raise ValueError("arXiv重定向未自动跟随，请从来源手动下载后导入")
            for block in response.iter_bytes():
                raw.extend(block)
                if len(raw) > max_bytes:
                    raise ValueError("文献超过上传限制")
    if not raw.startswith(b"%PDF-"):
        raise ValueError("arXiv未返回有效PDF")
    return bytes(raw), url


def recommend_results(query, results, local_papers, profile):
    qwords = set(tokens(query))
    library_words = set(tokens(" ".join(p["title"] for p in local_papers)))
    scored = []
    for result in results:
        words = set(tokens(result["title"] + " " + result["abstract"]))
        query_match = len(qwords & words) / max(1, len(qwords))
        local_match = len(library_words & words) / max(1, len(library_words))
        preference = sum(item["weight"] * len(set(tokens(item["title"])) & words) / max(1, len(set(tokens(item["title"])))) for item in profile)
        code_signal = .1 if result.get("code_available") else 0
        score = .6 * query_match + .2 * local_match + .1 * preference + code_signal
        scored.append({**result, "recommendation_score": round(score, 4),
                       "recommendation_components": {"query_overlap": query_match, "library_overlap": local_match, "feedback_overlap": preference, "code_link_signal": code_signal},
                       "recommendation_note": "可解释词汇兴趣排序；不是训练出的推荐模型。代码链接仅为可复现性线索，未实际运行仓库。"})
    return sorted(scored, key=lambda item: item["recommendation_score"], reverse=True)
