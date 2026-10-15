import pytest
from scripts.replay_library_sources import BOOK_URL, validate_record


def record():
    return {"filename":"1706.03762v1.pdf","url":"https://arxiv.org/pdf/1706.03762v1","sha256":"a"*64,"bytes":100}


@pytest.mark.parametrize("field,value",[("filename","../other.pdf"),("filename","C:stream.pdf"),("url","https://example.org/private.pdf"),("url","https://arxiv.org/pdf/1706.03762"),("sha256","bad"),("bytes",81*1024*1024)])
def test_invalid_replay_record_rejected_before_network(field,value):
    row=record();row[field]=value
    with pytest.raises(ValueError): validate_record(row)


def test_exact_version_and_fixed_author_release_are_allowed():
    validate_record(record())
    row=record();row.update(filename="UnderstandingDeepLearning_02_09_26_C.pdf",url=BOOK_URL)
    validate_record(row)
