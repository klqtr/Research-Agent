"""Freeze AI-assisted source-grounded task proposals; no fake human gold labels."""
import hashlib
import json
from pathlib import Path
from phase2_corpus import load_corpus

ROOT=Path(__file__).resolve().parents[1]


def main():
    output=ROOT/"data/phase2_qa_tasks.json"
    if output.exists():raise ValueError("已冻结任务，不覆盖；需要新增数据版本时另建文件")
    papers=load_corpus();by_name={p["filename"]:p for p in papers}
    original=json.loads((ROOT/"data/evaluation_cases.json").read_text(encoding="utf-8"))["cases"]
    cases=[{**case,"id":"dev_"+case["id"],"split":"development","application_domain":"NLP","version_policy":"all","gold_reviewed_by_human":False} for case in original[:4]]
    def add(identifier,question,files,targets,domain,policy="latest",explicit=None):
        anchors=[]
        for filename,needle in targets:
            source=next(c for c in by_name[filename]["chunks"] if needle in c["text"])
            anchors.append({"paper":filename,"paper_id":by_name[filename]["id"],"version":by_name[filename].get("version"),"page":source["page"],"chunk_id":source["id"],"needle":needle,"source_quote":source["text"]})
        cases.append({"id":identifier,"question":question,"papers":files,"targets":anchors,"split":"development" if identifier.startswith("dev_") else "frozen_test_proposal",
                      "version_policy":policy,"explicit_version":explicit,"application_domain":domain,"gold_reviewed_by_human":False})
    add("dev_latest","Using the latest locally available Attention Is All You Need version, quote its training GPU hardware.",["1706.03762v1.pdf","1706.03762v7.pdf"],[("1706.03762v7.pdf","8 NVIDIA P100 GPUs")],"NLP")
    add("dev_explicit_old","Quote the GPU hardware in Attention v1; retain the requested old version explicitly.",["1706.03762v1.pdf","1706.03762v7.pdf"],[("1706.03762v1.pdf","8 NVIDIA P100 GPUs")],"NLP","explicit",1)
    fno="2010.08895v3.pdf";fno_old="2010.08895v1.pdf";molecule="1703.00564v3.pdf"
    add("test_fno_equations","In FNO v3, which differential equations were used in experiments? Attribute the claim to the paper.",[fno_old,fno],[(fno,"We perform experiments on Burgers")],"scientific_computing")
    add("test_fno_runtime","Quote FNO v3 inference time and pseudo-spectral solver time on the 256 by 256 grid. Do not generalize to all PDEs.",[fno],[(fno,"0.005s")],"scientific_computing")
    add("test_fno_resolution","What training and evaluation resolutions are reported for the FNO v3 zero-shot super-resolution example?",[fno],[(fno,"trained on 64")],"scientific_computing")
    add("test_fno_parameters","According to FNO v3, are learned network parameters shared across discretizations?",[fno],[(fno,"shares the same learned network parameters")],"scientific_computing")
    add("test_fno_grid_tradeoff","Quote the grid resolution speed/accuracy trade-off described for traditional PDE solvers in FNO v3.",[fno],[(fno,"coarse grids are fast but less accurate")],"scientific_computing")
    add("test_fno_old","Use FNO v1 specifically and quote its abstract's comparison against traditional PDE solvers.",[fno_old,fno],[(fno_old,"three orders of magnitude")],"scientific_computing","explicit",1)
    add("test_molecule_scale","How many compounds does MoleculeNet say it contains? Quote the source without claiming clinical efficacy.",[molecule],[(molecule,"over 700,000 compounds")],"molecular_learning")
    add("test_molecule_package","Which open source package integrates all MoleculeNet datasets?",[molecule],[(molecule,"All datasets have been curated")],"molecular_learning")
    add("test_molecule_limit","What difficulty is stated for learnable representations under scarce and imbalanced molecular data? Return source context rather than an unsupported universal claim.",[molecule],[(molecule,"under data scarcity")],"molecular_learning")
    add("test_molecule_script","What choices are demonstrated in MoleculeNet's benchmark evaluation code figure?",[molecule],[(molecule,"Figure 1: Example code for benchmark evaluation")],"molecular_learning")
    add("test_cross_domain","Separately quote FNO v3 solver timing and MoleculeNet dataset scale, keeping each fact attached to its own paper.",[fno,molecule],[(fno,"0.005s"),(molecule,"over 700,000 compounds")],"cross_application_domain")
    add("test_unanswerable","What randomized clinical-trial survival benefit is proven by MoleculeNet? Abstain if this source does not establish it.",[molecule],[],"molecular_learning")
    cases[-1]["expected_behavior"]="abstain"
    for case in cases:
        for target in case["targets"]:
            if "source_quote" not in target:
                paper=by_name[target["paper"]];chunk=next(c for c in paper["chunks"] if c["page"]==target["page"] and target["needle"] in c["text"])
                target.update(paper_id=paper["id"],version=paper.get("version"),chunk_id=chunk["id"],source_quote=chunk["text"])
    data={"version":"phase2_tasks_v1","label_provenance":"AI-assisted proposals checked against stored source strings; no external human annotation performed",
          "training_data":"none","test_policy":"New FNO/MoleculeNet application-domain tasks were not used to modify the frozen lexical retriever. Not an independent third-party blind test; human correctness/support labels pending.",
          "retriever_sha256":hashlib.sha256((ROOT/"src/retrieval.py").read_bytes()).hexdigest(),"cases":cases}
    output.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    lock={"path":str(output.relative_to(ROOT)),"sha256":hashlib.sha256(output.read_bytes()).hexdigest(),"cases":len(cases),"test_cases":sum(c["split"]=="frozen_test_proposal" for c in cases),"gold_reviewed_by_human":False}
    (ROOT/"data/phase2_qa_tasks.lock.json").write_text(json.dumps(lock,indent=2),encoding="utf-8")
    print(json.dumps(lock))


if __name__=="__main__":main()
