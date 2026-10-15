from src.citation_graph import complete_title_match
from src.tools import graph


def test_title_prefix_does_not_create_book_edge():
    assert not complete_title_match("Understanding Deep Learning", "[1] Zhang et al. Understanding deep learning requires rethinking generalization. ICLR, 2017.")
    assert complete_title_match("Understanding Deep Learning", "[1] Simon Prince. Understanding Deep Learning. MIT Press, 2023.")


def test_hyphenation_ligature_and_small_caps():
    assert complete_title_match("Outrageously Large Neural Networks", "[1] Author. O UTRAGEOUSLY L ARGE N EURAL N ETWORKS. 2017.")
    assert complete_title_match("Efficient pre-training of language models", "Author. Efﬁcient pre- training of language models. 2020.")


def test_do_not_join_distinct_references_into_title():
    source={"id":"source","title":"Source","references":[{"text":"A long title beginning"},{"text":"and ending in another reference."}],"chunks":[]}
    target={"id":"target","title":"A long title beginning and ending in another reference","references":[],"chunks":[]}
    assert graph([source,target])["edges"]==[]


def test_source_anchor_and_exact_identifier_boundary():
    source={"id":"s","title":"Source","references":[{"text":"[1] A real arXiv:1706.03762v1 paper.","page":2,"chunk_id":"bad"}],
            "chunks":[{"id":"body","page":1,"text":"As described in [1]."},{"id":"verified","page":2,"text":"[1] A real arXiv:1706.03762v1 paper."}]}
    target={"id":"t","arxiv_id":"1706.03762","title":"Attention Is All You Need","version":7,"references":[],"chunks":[]}
    edge=graph([source,target])["edges"][0]
    assert edge["source_chunk_id"]=="verified" and edge["numeric_body_mentions"]==1
    assert edge["cited_version"]=="unspecified_family"
    source["references"][0]["text"]="arXiv:1706.037620 is not that identifier."
    assert graph([source,target])["edges"]==[]


def test_pagerank_probability_and_direction_for_twenty_nodes():
    papers=[{"id":str(i),"title":f"Distinct scientific research paper number {i}","references":[],"chunks":[]} for i in range(20)]
    for p in papers[1:]: p["references"]=[{"text":papers[0]["title"]+". Venue, 2020."}]
    result=graph(papers)
    assert len(result["nodes"])==20 and len(result["edges"])==19
    assert result["nodes"][0]["id"]=="0"
    assert abs(sum(n["pagerank"] for n in result["nodes"])-1)<1e-6
    assert result["algorithm"]["residual_l1"]<1e-10
