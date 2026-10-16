"""Independent conservative release gate, not a general semantic-entailment model.

Only complete source quotations are releasable automatically. Numeric/partial
signals identify review candidates; paraphrases remain unknown rather than being
approved by a model's self-rating. Source support does not establish world truth.
"""
import re
from .retrieval import validate_claims, terms

WORD_NUMBERS={"one":"1","two":"2","four":"4","eight":"8","sixteen":"16"}
STATUSES=("fully_supported","partially_supported","evidence_conflict","insufficient_evidence","cannot_judge")


def normalized(text):
    return re.sub(r"\s+"," ",text).strip().casefold().rstrip(".。")


def quantities(text):
    text=text.casefold().replace(",","")
    for word,value in WORD_NUMBERS.items(): text=re.sub(r"\b"+word+r"\b",value,text)
    patterns={"gpu":r"\b(\d+(?:\.\d+)?)\s+(?:nvidia\s+)?(?:[a-z]\d+\s+)?gpus?\b",
              "tpu":r"\b(\d+(?:\.\d+)?)\s+tpus?(?:\s+chips)?\b",
              "layers":r"\b(\d+)\s+(?:transformer\s+)?layers?\b",
              "batch_size":r"batch\s+size(?:\s+of|\s+is|\s*=|:)?\s*(\d+)\b"}
    return {unit:sorted(set(re.findall(pattern,text))) for unit,pattern in patterns.items() if re.search(pattern,text)}


def verify_claims(payload, evidence):
    integrity=validate_claims(payload,evidence)
    lookup={item["id"]:item for item in evidence}
    audits=[];released=[]
    for rejected in integrity["rejected"]:
        audits.append({"claim":rejected.get("claim"),"status":"insufficient_evidence","release":False,"reason":rejected["reason"]})
    for claim in integrity["claims"]:
        text=claim["text"].strip()
        refs=claim["citations"]
        quotes=[reference["quote"].strip() for reference in refs]
        source_mismatch=any((ref.get("paper_id") is not None and ref["paper_id"]!=lookup[ref["chunk_id"]].get("paper_id")) or
                            (ref.get("version") is not None and ref["version"]!=lookup[ref["chunk_id"]].get("source_version")) for ref in refs)
        reason="paraphrase_not_independently_verified";status="cannot_judge"
        sources=[lookup[ref["chunk_id"]] for ref in refs]
        same_family_versions=len({s.get("source_family") for s in sources})==1 and len({s.get("source_version") for s in sources})>1
        quote_values=[quantities(quote) for quote in quotes]
        version_discrepancy=same_family_versions and any(set(left[unit]).isdisjoint(right[unit]) for i,left in enumerate(quote_values) for right in quote_values[i+1:] for unit in left.keys()&right.keys())
        if not text or len(text)>6000 or source_mismatch:
            status,reason="insufficient_evidence","invalid_claim_or_citation_version"
        elif version_discrepancy:
            status,reason="evidence_conflict","cross_version_quantity_discrepancy_requires_review"
        elif any(normalized(text)==normalized(quote) for quote in quotes):
            if re.search(r"[.!?。！？][\d\]\s]*$",text) and not text.endswith("-"):
                status,reason="fully_supported","complete_source_quotation_only"
            else:
                status,reason="cannot_judge","source_fragment_or_heading_not_complete_statement"
        else:
            claim_quantities=quantities(text)
            cited_quantities=quantities(" ".join(quotes))
            discrepancy=any(unit in cited_quantities and set(values).isdisjoint(cited_quantities[unit]) for unit,values in claim_quantities.items())
            atoms=[atom.strip() for atom in re.split(r"\s+and\s+|[;；]",text) if atom.strip()]
            partial=len(atoms)>1 and any(normalized(atom)==normalized(quote) for atom in atoms for quote in quotes)
            if discrepancy:
                status,reason="evidence_conflict","numeric_discrepancy_candidate_not_general_contradiction_proof"
            elif partial:
                status,reason="partially_supported","only_some_claim_atoms_are_complete_quotes"
            elif not set(terms(text)) & set(terms(" ".join(quotes))):
                status,reason="insufficient_evidence","no_lexical_support_signal"
        release=status=="fully_supported"
        audit={"claim":claim,"status":status,"reason":reason,"release":release,
               "source_versions":[{"paper_id":lookup[r["chunk_id"]].get("paper_id"),"version":lookup[r["chunk_id"]].get("source_version")} for r in refs]}
        audits.append(audit)
        if release: released.append(claim)
    return {"claims":released,"audit":audits,"rejected":[item for item in audits if not item["release"]],
            "semantic_entailment_verified":False,"verification_scope":"conservative_source_quotation_release_gate",
            "disclaimer":"完整引文只支持来源表述，不证明现实事实或普适语义蕴含。数值冲突/部分支持为人工复核线索；未验证改写默认不发布。未把模型自评分当真值。"}
