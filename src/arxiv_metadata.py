"""Read public arXiv Atom metadata, keeping source versions and provenance explicit."""
import re
import xml.etree.ElementTree as ET
import httpx

NS = {"a": "http://www.w3.org/2005/Atom", "x": "http://arxiv.org/schemas/atom"}


def parse_metadata(raw):
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ValueError("arXiv元数据不是有效XML") from exc
    records = []
    for entry in root.findall("a:entry", NS):
        url = entry.findtext("a:id", "", NS).strip()
        match = re.search(r"arxiv\.org/abs/(\d{4}\.\d{4,5})(?:v(\d+))?$", url)
        if not match:
            continue
        authors = []
        for author in entry.findall("a:author", NS):
            name = author.findtext("a:name", "", NS).strip()
            if name:
                authors.append({"name": name, "affiliations": [item.text for item in author.findall("x:affiliation", NS) if item.text]})
        records.append({"arxiv_id": match.group(1), "version": int(match.group(2)) if match.group(2) else None,
                        "title": " ".join(entry.findtext("a:title", "", NS).split()), "authors": authors,
                        "abstract": " ".join(entry.findtext("a:summary", "", NS).split()),
                        "published": entry.findtext("a:published", "", NS), "updated": entry.findtext("a:updated", "", NS),
                        "doi": entry.findtext("x:doi", "", NS), "journal_ref": entry.findtext("x:journal_ref", "", NS),
                        "url": url, "metadata_source": "public_arxiv_atom_api",
                        "limitations": "作者/日期来自arXiv元数据；未提供的机构/DOI留空，不代表同行评议或重新分发许可。"})
    return records


def fetch_metadata(identifiers):
    if not 1 <= len(identifiers) <= 30 or any(not re.fullmatch(r"\d{4}\.\d{4,5}(?:v\d+)?", identifier) for identifier in identifiers):
        raise ValueError("每批需1–30个有效arXiv标识")
    with httpx.Client(timeout=25, trust_env=False, follow_redirects=False) as client:
        response = client.get("https://export.arxiv.org/api/query", params={"id_list": ",".join(identifiers), "max_results": len(identifiers)})
        response.raise_for_status()
    return parse_metadata(response.content), response.content
