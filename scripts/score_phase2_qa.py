"""Score externally supplied reviews separately; never overwrite raw model runs."""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.qa_metrics import summarize


def validate_reviews(records,reviews):
    if not isinstance(reviews,list):raise ValueError("审阅文件须为数组")
    identifiers={row["record_id"]:row for row in records};seen=set()
    for review in reviews:
        if not isinstance(review,dict):raise ValueError("每条审阅须为对象")
        identifier=review.get("record_id")
        if not isinstance(identifier,str) or identifier not in identifiers or identifier in seen:raise ValueError("未知或重复审阅record_id")
        seen.add(identifier)
        if review.get("complete") is not None and type(review["complete"]) is not bool:raise ValueError("complete须为布尔值")
        if not review.get("complete"):continue
        if identifiers[identifier]["status"]!="completed_real_endpoint":raise ValueError("未运行/失败记录不能填完整人工效果标签")
        if review.get("reviewer_type")!="human" or not isinstance(review.get("reviewer_id"),str) or not review["reviewer_id"].strip():raise ValueError("效果分须由真实人工审阅，AI草稿不能伪装人工")
        for key in ("answer_correct","task_success"):
            if type(review.get(key)) is not bool:raise ValueError("完整审阅缺少整体正确/成功二元标签")
        if review.get("version_consistent") is not None and type(review["version_consistent"]) is not bool:raise ValueError("版本标签须为布尔或不适用null")


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("run_folder");parser.add_argument("annotations");args=parser.parse_args()
    folder=Path(args.run_folder);annotation_path=Path(args.annotations)
    records=[json.loads(line) for line in (folder/"raw.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    reviews=json.loads(annotation_path.read_text(encoding="utf-8"));validate_reviews(records,reviews)
    results={variant:summarize([r for r in records if r["variant"]==variant],reviews) for variant in sorted({r["variant"] for r in records})}
    output=folder/("scored_"+time.strftime("%Y%m%d_%H%M%S")+".json")
    output.write_text(json.dumps({"annotation_sha256":hashlib.sha256(annotation_path.read_bytes()).hexdigest(),"results":results,
                                  "caveat":"human字段不是人工行为证明；真实性由实际审阅过程/身份/记录核验。未标注保持null。"},ensure_ascii=False,indent=2),encoding="utf-8")
    print(str(output))
