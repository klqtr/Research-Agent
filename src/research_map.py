"""Transparent title-word clustering and source-dated timeline, not learned topics."""
import math
from collections import Counter
from .tools import family_representatives,future_work
from .retrieval import terms


def research_map(papers):
    representatives=family_representatives(papers)
    words={p["id"]:Counter(terms(p["title"])) for p in representatives}
    df=Counter(word for counts in words.values() for word in counts)
    vectors={key:{word:count*(1+math.log((1+len(words))/(1+df[word])) ) for word,count in counts.items()} for key,counts in words.items()}
    def cosine(a,b):
        va,vb=vectors[a],vectors[b]
        return sum(value*vb.get(word,0) for word,value in va.items())/max(1e-12,math.sqrt(sum(v*v for v in va.values())*sum(v*v for v in vb.values())))
    clusters=[{p["id"]} for p in representatives]
    while len(clusters)>1:
        best=None
        for i,left in enumerate(clusters):
            for j in range(i+1,len(clusters)):
                right=clusters[j];score=sum(cosine(a,b) for a in left for b in right)/(len(left)*len(right))
                if score>=.24 and (best is None or score>best[0]):best=(score,i,j)
        if best is None:break
        _,i,j=best;clusters[i]|=clusters[j];clusters.pop(j)
    topics=[]
    for index,ids in enumerate(clusters):
        counts=Counter(word for identifier in ids for word in words[identifier])
        topics.append({"id":index+1,"terms":[word for word,_ in counts.most_common(5)],"paper_ids":sorted(ids),"status":"heuristic_title_topic_candidate"})
    timeline=[]
    for paper in representatives:
        metadata=paper.get("arxiv_metadata",{})
        timeline.append({"paper_id":paper["id"],"title":paper["title"],"first_submitted":metadata.get("published") or None,"selected_version_updated":metadata.get("updated") or None,
                         "version":paper.get("version"),"metadata_source":metadata.get("metadata_source","unknown"),"date_status":"source_metadata" if metadata.get("published") else "unknown_not_inferred"})
    return {"topics":topics,"timeline":sorted(timeline,key=lambda item:item["first_submitted"] or "9999"),
            "future_work":[{**item,"category":"source_future_work_candidate","attribution_verified":False,"resolved_by_later_work":None} for item in future_work(representatives)],
            "derived_research_opportunities":[],"model_hypotheses":[],
            "limitations":"标题TF-IDF余弦/平均连接阈值0.24是可解释启发式，未做人工主题质量评测；时间线是首发/选定版更新时间，不证明影响因果。Future Work来源候选不等于仍未解决问题，不生成已证明的新结论。"}
