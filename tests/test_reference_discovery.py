from src.references import reference_candidates
from src.arxiv_metadata import parse_metadata,fetch_metadata
import pytest


def test_reference_identity_anchor_and_family_dedup():
    old={"id":"old","arxiv_id":"1706.03762","version":1,"title":"Attention","references":[{"text":"[1] Layer norm arXiv:1607.06450v1.","page":3,"chunk_id":"wrong"}],"chunks":[]}
    new={**old,"id":"new","version":7,"chunks":[{"id":"body","page":1,"text":"As in [1], we use [1]."},{"id":"source","page":3,"text":"[1] Layer norm arXiv:1607.06450v1."}]}
    result=reference_candidates([old,new])
    assert len(result)==1 and result[0]["citing_paper_count"]==1
    assert result[0]["explicit_versions"]==[1] and result[0]["numeric_citation_mentions"]==2
    assert result[0]["anchors"][0]["chunk_id"]=="source"


def test_not_harvested_from_arbitrary_body_or_invalid_id():
    paper={"id":"x","title":"Test","references":[{"page":2,"text":"Malformed arXiv:2002.089099 and http://localhost/secret"}],
           "chunks":[{"id":"body","page":1,"text":"arXiv:1706.03762v1 is mentioned in body only"}]}
    assert reference_candidates([paper])==[]


def test_metadata_leaves_missing_affiliations_empty():
    raw=b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/abs/1706.03762v7</id><title>Attention\n Is All You Need</title><author><name>Public Author</name></author><published>2017-06-12T00:00:00Z</published></entry></feed>'''
    record=parse_metadata(raw)[0]
    assert record["title"]=="Attention Is All You Need"
    assert record["authors"]==[{"name":"Public Author","affiliations":[]}]
    assert record["doi"]=="" and record["version"]==7


@pytest.mark.parametrize("ids",[[],["http://localhost/secret"],["../file"],["1706.03762"]*31])
def test_invalid_metadata_batch_never_opens_client(ids):
    with pytest.raises(ValueError): fetch_metadata(ids)
