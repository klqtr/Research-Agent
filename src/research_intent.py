"""Cheap disclosed intent hints; actual native tool decisions remain model-driven."""
import re


def intent_hints(question):
    text=question.casefold();labels=[]
    for name,pattern in (("version_comparison",r"version|revision|版本|修订|\bv[1-9]\b"),("cross_paper_synthesis",r"compare|across|multiple|跨篇|比较"),("translation",r"translat|翻译|译文"),("research_frontier",r"future|open problem|未来|前沿"),("citation_review",r"citation|graph|references|引用|图谱")):
        if re.search(pattern,text):labels.append(name)
    subquestions=[piece.strip() for piece in re.split(r"[?？;；]\s*",question) if piece.strip()][:3]
    return {"labels":labels or ["evidence_question_answering"],"subquestions":subquestions,"provenance":"deterministic_keyword_and_punctuation_hints_not_LLM_reasoning",
            "limitations":"标点拆分最多3项，不是语义完整问题分解；原问题始终保留，真实模型需依据工具结果继续规划。"}
