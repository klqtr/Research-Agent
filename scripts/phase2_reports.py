"""Generate phase-two narratives from saved evidence; no invented model scores."""
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime,timedelta,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MARKER="\n<!-- PHASE2_CURRENT -->\n"


def context():
    folder=ROOT/(ROOT/"experiments/LATEST_PHASE2_OFFLINE.txt").read_text(encoding="utf-8").strip()
    offline=json.loads((folder/"summary.json").read_text(encoding="utf-8"))
    qa=ROOT/(ROOT/"experiments/LATEST_PHASE2_QA.txt").read_text(encoding="utf-8").strip()
    qa_config=json.loads((qa/"config.json").read_text(encoding="utf-8"))
    qa_rows=[json.loads(line) for line in (qa/"raw.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    # This is an explicitly scoped offline handoff report. Refuse to recycle
    # its 'not run' narrative after real experiments/annotations are supplied.
    if len(qa_rows)!=96 or any(row["status"]!="not_run_no_explicit_execution_or_authorized_model" for row in qa_rows) or (qa_config.get("execute_requested") and qa_config.get("model_enabled")):
        raise ValueError("当前报告模板仅适用于96项无推理计划；检测到范围变化，需先更新报告以纳入新真实证据，不能沿用未运行叙述")
    review_path=ROOT/"data/phase2_graph_review.json"
    if review_path.exists() and any(row.get("is_citation_human_gold") is not None for row in json.loads(review_path.read_text(encoding="utf-8"))["pairs"]):
        raise ValueError("图谱已有标注，须重新核验并更新人工指标，不再输出零标注模板")
    if any(row["count"]!=0 for row in offline["numeric_change_candidates"]):
        raise ValueError("版本变化候选已更新，须重写本阶段零候选限制叙述，不能输出过时结果")
    tests=ROOT/(ROOT/"experiments/LATEST_TESTS.txt").read_text(encoding="utf-8").strip()
    suites=list(ET.parse(tests).getroot().iter("testsuite"))
    counts={key:sum(int(s.attrib.get(key,0)) for s in suites) for key in ("tests","failures","errors","skipped")}
    return folder,offline,qa,tests,counts


def append_phase2_reports():
    if not (ROOT/"experiments/LATEST_PHASE2_OFFLINE.txt").exists():return
    folder,offline,qa,tests,counts=context()
    relative=folder.relative_to(ROOT).as_posix()
    text=f"""# 第二阶段深度研发与验收（当前）

证据：`{relative}`，完整回归`{tests.relative_to(ROOT).as_posix()}`：{counts['tests']}项，失败{counts['failures']}、错误{counts['errors']}、跳过{counts['skipped']}。此前第一阶段数字是历史记录，不能视为新增模型结果。

|实际运行项目|观测|指标边界|
|---|---|---|
|真实来源中注入合成错误断言|{offline['synthetic_assertion_count']}条；旧quote关卡放行{offline['quote_only_synthetic_accepted']}，新关卡发布{offline['guard_synthetic_released']}|不是LLM幻觉率或通用NLI准确率|
|原文摘录|{offline['verbatim_count']}条，新关卡发布{offline['verbatim_released']}|保守门槛会拒绝片段，不能只展示拦截收益|
|版本数值变化候选|Attention v1/v7=0；FNO v1/v3=0|不是结论未变证明；当前规则只覆盖少数单位|
|主题/时间线|{offline['topic_clusters']}个启发式簇，{offline['timeline_source_dated']}来源日期、{offline['timeline_unknown']}未知|主题质量未人工评测|
|图谱人工配对|20家族380对模板，已标注0|71算法匹配与7项来源回归不是人工金标|
|真实LLM回答/翻译|未运行|授权/模型缺失，质量/Token/费用不填模拟值|

四基线和四消融运行器已执行12任务×8方案的96条计划检查，真实模型完成0。原始计划`{qa.relative_to(ROOT).as_posix()}`；Answer Correctness、Citation Precision/Recall、Evidence Support、Hallucination、Version Consistency、Task Success和费用均为null。不是96次推理。定义与人工审阅流程见docs/phase2_evaluation_protocol.md。

真实应用接口验证见experiments/phase2_live_*.json：模型状态、研究图、版本工作流、状态读取/恢复正常，无模型翻译503符合预期；本机11434/1234不可达。112/119等测试中的原生工具与翻译使用明确MockTransport，只是协议与完整性契约，不代表模型规划或翻译能力。

新增机制是可证伪的工程方案：同源版本策略、严格来源约束、失败/预算也可恢复的有界工具循环与保守发布关卡。没有证明真实回答质量优势、基础算法首创、SOTA或一等奖水平。下一步需授权模型和真实人工审阅，保留当前拒答代价与零数值变化候选结果。
"""
    for name in ("evaluation_report.md","ablation_study.md"):
        path=ROOT/"reports"/name
        original=path.read_text(encoding="utf-8").split(MARKER)[0]
        path.write_text(original+MARKER+text,encoding="utf-8")
    return text


def build_deliverables():
    folder,offline,qa,tests,counts=context()
    now=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
    elapsed=(datetime.now(timezone(timedelta(hours=8)))-datetime(2026,10,16,15,32,tzinfo=timezone(timedelta(hours=8)))).total_seconds()/60
    append_phase2_reports()
    report=f"""# ResearchTrace 技术报告 - 第二阶段研发稿

版本：{now}。依据本地官方规则存档，供选手理解、复现和继续完善；不是已完成全部六模块的最终参赛声明。

## 1. 概述与实际问题
科研助手常把不同修订版本混为一个来源，给真实引文配上不受支持的结论，或在工具失败后仍输出似是而非的答案。研证以Version-Aware Evidence-Grounded Research Agent为工程假设：文献身份、版本、页块证据、工具状态与断言支持状态必须能逐项检查。

沿用第一阶段FastAPI/SQLite/PyMuPDF/OCR、BM25+字符RRF、家族PageRank与arXiv追踪，不重新选题、不训练新基础模型。LLM适合意图理解、多步工具选择、改写综合和翻译；版本过滤、引用定位、数值线索与预算由确定性模块处理。当前无授权模型，所以本轮没有真实LLM效果结论。

## 2. 官方需求与范围
官方要求基于LLM+Agent的科研助手，涵盖PDF解析、RAG、联动翻译、搜索追踪、图谱综述、写作可视化。Agent与模型深度35%、科研创新25%，其余四项各10%；详细出处见docs/competition_requirements.md及原始接口存档。可用第三方API，不强制本地；禁止把Mock或合成样例冒称真实推理/官方测试。

提交要求包括真实Git历史、可复现源码/README/配置、5-8分钟1080p普通话MP4、30页以内技术PDF和公网演示。现在没有公网、正式视频、官方扫描包全量验收或真实模型结果，不能宣称提交完备。参赛个人信息与许可仍需选手核对。

## 3. 架构与数据流
Web → app.py → ResearchAgent → 来源版本策略 → 白名单工具 → 模型消息历史 → 引用完整性 → 独立保守支持关卡 → 原文锚点。model.py负责OpenAI兼容消息/显式探测；model_budget.py跨客户端/进程累计预留；run_state.py持久状态/租约；translation.py处理段落对齐与保护标记；research_map.py提供启发式主题与来源日期。

底层retrieval.py继续冻结，新增策略通过独立模块复用检索结果，不把词汇方法叫Dense。原21份演示PDF不改；另有FNO v1/v3和MoleculeNet v3的独立评测缓存，原始作者页/版本/文件哈希存档。系统架构与算法Mermaid见docs/system_architecture.md及docs/phase2_evidence_flow.md。

## 4. 结果驱动、有界且可恢复的Agent
显式请求真实模型后，模型看到用户目标、规则意图提示和当前版本策略，可调用search_library、retrieve、versions、graph、future_work、outline。arXiv元数据工具默认不可用，只有用户勾选允许向arXiv发送本问题主题词才开放，且不允许发送文档中新增词汇。元数据不是全文证据，自动下载/导入不在模型白名单内。

工具参数使用严格Pydantic类型、extra=forbid，paper_ids只能来自当前选定且未被版本策略排除的文献。结果通过原生tool消息返回，模型可修正失败参数或继续检索；最多4模型回合/6工具。非法标识、重复调用ID、格式截断与上下文超限均明确处理。未支持断言最多一次修复；无效循环达到上限后仅返回允许的原文摘录或拒答。

端点拒绝工具请求时可退为确定性检索+一次真实JSON回答，标记real_llm_rag_compatibility；这不是原生规划。模型不可用则extractive_fallback，不把抽取模式当真实Agent。初版两次固定请求已由新循环替代，旧确定性兼容入口保留。

每个模型响应、工具调用及完成ID写本地状态。崩溃租约过期后，同目标/同源指纹/同版本及联网权限才能恢复；完成记录读取缓存不追加费用。工具尝试在执行前记数，模型尝试先作预算预留；崩溃/超时不自动返还，以避免隐性重复消费。读工具在执行与状态落盘之间崩溃仍可能重读，不宣称分布式恰好一次。

## 5. 证据支持与版本创新
原有quote+chunk_id校验仍作为低层完整性条件。新增独立关卡区分fully_supported、partially_supported、evidence_conflict、insufficient_evidence、cannot_judge。只自动放行完整来源摘录；不完整PDF行、未知改写和不匹配版本拒收。数值不一致、同家族不同版本单位值差异只作为冲突候选，可能是实验配置不同，需要科研人员复核。

这不是通用语义蕴含，也不证明现实事实。只有“文献这样表述”的窄支持范围；模型自评分不作为真值。保守策略有明显覆盖损失，真实多篇综合改写质量仍待授权模型/外部人工验证。未经校验的断言不会因引文真实而自动发布。

版本策略latest/all/explicit基于本次文献集合，不声称已知全网最新。较旧来源提示与精确版本URL随证据保存；用户明确旧版时应尊重。原文diff继续可用；字词段落对齐只提取GPU/TPU/层数/批次等数值变化候选，不把排版变化当结论改变。当前两组真实修订版均未找到该规则覆盖的数值变化，不能展示虚构“新旧结论冲突”。

## 6. 实验设计、结果与代价
第一阶段开发/新论文检索指标保留为历史检索对照：开发调优后全目标命中100%，两篇新论文11/12；不当作回答准确率。第二阶段完整回归{counts['tests']}通过，失败{counts['failures']}、错误{counts['errors']}、跳过{counts['skipped']}；1条上游AnyIO弃用警告。XML来源`{tests.relative_to(ROOT).as_posix()}`。

本轮真实运行的离线策略实验：{offline['synthetic_assertion_count']}条错误合成断言绑定真实来源，旧完整性校验放行{offline['quote_only_synthetic_accepted']}，保守关卡发布{offline['guard_synthetic_released']}；{offline['verbatim_count']}条原文摘录仅{offline['verbatim_released']}通过。它们是来源约束策略探针，不是模型幻觉率、回答正确率或无偏NLI准确率。误拒/片段风险保留，不只报告收益。原始payload/evidence/audit见`{folder.relative_to(ROOT).as_posix()}`。

18任务草案含6开发与12冻结新应用任务，均AI辅助来源核对，无外部人工金标。新PDF曾用于工程解析检查，不称作整个系统完全未见数据。无真实模型输出可供调Prompt；未来必须只在开发集调优，若观察冻结集失败后修改则另建最终集。数据SHA锁与检索SHA随运行配置保存。

四基线direct_llm/conventional_rag/citation_integrity_rag/proposed_agent，以及去版本、去关卡、去事实重排、去模型规划四消融，已实际完成96条计划检查，真实模型完成0。质量/Token/费用值均null。相同模型/任务/温度/每次输出限额，但Agent计算量可能更多，不能称等成本。指标分母、Wilson区间、部分/未知支持的处理详见docs/phase2_evaluation_protocol.md。

## 7. 阅读、翻译、图谱与科研发现
按页真实版式图与原文bbox定位、数字引用往返保留。新增翻译段落ID/bbox对齐、术语表与所识别公式/数字/Greek符号/引文保护；缺失/重复标记、缺段落会拒收。切页后旧翻译响应不覆盖新页。真实模型未配置返回503，完整性替身测试不等于翻译正确性。

图谱沿用20家族71边与来源锚点/聚焦/SVG。新增标题TF-IDF启发式聚类{offline['topic_clusters']}簇、公开首发日期{offline['timeline_source_dated']}条与未知{offline['timeline_unknown']}条；没有人工主题质量分。380有向配对标注表全部为空，算法候选不是人工真值。Future Work只列来源候选，归属/后续解决状态未确认；证据归纳机会与模型假设分开，当前两者为空，不能凭猜想宣布已证明方向。

## 8. 工程、预算与复现
依赖保持现有固定版本，配置来自RESEARCHTRACE环境变量，密钥不进源码、SQLite或Web。模型默认禁用；当前.env缺失，两个本机模型服务不可达。默认最多8累计请求、100000保守预留单位、每请求1600输出Token，失败/重试计入共享账本。美元上限需要用户提供两种单价；缺失实际usage/单价时费用null，不把估算当账单保证。

按README使用Python3.12与requirements-dev.txt启动127.0.0.1:8000，运行scripts/run_tests.py、phase2_offline_experiments.py、evaluate_phase2_qa.py默认计划、phase2_live_probe.py。模型授权后按docs/phase2_model_acceptance.md小批验收，再显式--execute-models；预算不足明确停止，不自动提额。恢复ZIP排除密钥、原PDF、数据库、权重和venv，来源锁与实际实验仍保留。

## 9. 真实边界、AI协作与下一步
本轮由AI辅助审计、实现、构造来源任务与测试；没有外部人工标注、真实LLM推理或翻译实验，没有远程推送/付费调用/购买/公网部署。选手应亲自理解和复现核心算法，不能把自动生成材料当人工研究贡献。创新是可检验的应用工程组合，未证明基础算法原创或性能优势。

优先补授权模型与足够预算，真实运行四基线/四消融及双人抽查；补官方扫描包和复杂段落/表格/公式、真实翻译及通用语义支持验证；最后完善访问控制/评审仓库/普通话MP4。内部成熟度不替代官方评分，也不宣称一等奖水平。
"""
    report=re.sub(r"(?m)^(#{1,6} [^\n]+)\n(?!\n)",r"\1\n\n",report)
    (ROOT/"reports/technical_report.md").write_text(report,encoding="utf-8")
    final=f"""# ResearchTrace 第二阶段交付报告

生成：{now}。本轮基线d008162，保留已有系统。本报告是当前授权/环境下的交付，不代表已补齐真实大模型或完整竞赛提交。

执行窗口约15:32至本报告，墙钟约{elapsed:.1f}分钟，含工具/审批等待，不是精确有效编码工时。没有付费推理、资源购买、远程推送或公网发布。

## 实际完成
模型端点校验、健康/显式能力探测、共享预算/分组用量、上下文限制；4回合6工具结果驱动Agent、参数白名单、失败反馈/修复、兼容与抽取降级、租约与同源恢复；五类保守支持关卡、版本策略/来源版本及变化候选；段落翻译保护与对齐、主题候选/来源时间线。已接入Web与API。

## 测试与真实证据
- 完整{counts['tests']}项，失败{counts['failures']}、错误{counts['errors']}、跳过{counts['skipped']}；XML `{tests.relative_to(ROOT).as_posix()}`。初始两项旧行为差异失败保留，随后更新为新协议/明确降级断言。
- 离线真实来源+合成错误断言：{offline['synthetic_assertion_count']}条，旧关卡放行{offline['quote_only_synthetic_accepted']}，新发布{offline['guard_synthetic_released']}；原文{offline['verbatim_released']}/{offline['verbatim_count']}发布，覆盖代价明确。不是LLM效果。
- 两组真实版本数值变化候选均0，未虚构结论变化；图谱380对人工标签为0。
- 三份新增PDF共13,040,090字节，独立缓存，不改变原21份库；18任务草案/12新应用任务已冻结，96条计划检查、0真实推理。
- 本地API和浏览器验证另存experiments/phase2_live_*与reports/screenshots/phase2_*；真实翻译不可用503是预期。

## 文件与复现
README、docs/innovation_points.md/system_architecture.md/phase2_*、reports/evaluation_report.md/ablation_study.md/technical_report.md/demo_script.md/defense_questions.md/defense_slides.md、src新模块、tests与experiments均更新。精确本阶段改动清单见reports/phase2_changed_files.txt；全文件目录见reports/phase2_file_inventory.txt。恢复入口PHASE2_PROGRESS.md与README；最终源码/结果快照见checkpoints/LATEST.json，原PDF和本地状态仍在原目录。第二阶段10页独立PDF已渲染，原第一阶段PDF保留；版式/文件SHA记录为reports/phase2_pdf_validation.json。

## 尚未完成（不能以Mock替代）
真实授权模型、能力/多轮Agent/回答/翻译质量、真实四基线和四消融、真实人工支持/引用/图谱标签、通用语义蕴含、深层版本结论识别、官方扫描资料包/复杂解析、公网/Docker验收/正式MP4/个人信息及许可核对。质量和费用缺实测就保留null，未声称一等奖竞争力已达成。

## 下一步三件事
1. 用户提供已授权模型/端点及费用/次数预算，按模型验收清单先开发集小批运行；密钥只填本地.env。
2. 固定代码/Prompt再运行冻结任务、四基线/四消融，安排真实人工审阅；若根据该集失败改动，另建最终测试。
3. 完成官方难例与真实翻译/语义验证，再由选手理解复现、核许可和公网/评审仓库/正式视频。
"""
    final=re.sub(r"(?m)^(#{1,6} [^\n]+)\n(?!\n)",r"\1\n\n",final)
    (ROOT/"PHASE2_FINAL_REPORT.md").write_text(final,encoding="utf-8")
    # State matrix honestly displays absence; zero-height quality bars would lie.
    variants=("Direct LLM","Conventional RAG","Citation integrity RAG","Proposed Agent","Without version policy","Without support gate","Without facet rerank","Without Agent planning")
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1060" height="550"><rect width="1060" height="550" fill="#f4f5ef"/><text x="35" y="42" font-family="Arial" font-size="23" fill="#183d33">Phase 2: real model baselines and ablations</text><text x="35" y="72" font-family="Arial" font-size="14">96 plan records, 0 inference runs. Quality metrics are null, not zero accuracy.</text>']
    for index,name in enumerate(variants):
        y=110+index*48;svg.append(f'<text x="35" y="{y+22}" font-family="Arial" font-size="15">{name}</text><rect x="300" y="{y}" width="690" height="33" rx="5" fill="#e0e5dc"/><text x="325" y="{y+22}" font-family="Arial" font-size="14" fill="#536554">NOT RUN - authorized model and human labels missing</text>')
    svg.append('</svg>');(ROOT/"reports/figures/phase2_ablation_status.svg").write_text("".join(svg),encoding="utf-8")
    paths=[]
    for root in ("src","tests","scripts","docs","reports","experiments"):
        paths.extend(p.relative_to(ROOT).as_posix() for p in (ROOT/root).rglob("*") if p.is_file() and "__pycache__" not in p.parts and not (p.parent==ROOT/"docs/sources" and p.suffix==".js"))
    (ROOT/"reports/phase2_file_inventory.txt").write_text("\n".join(sorted(paths)),encoding="utf-8")
    changed=set()
    for command in (["git","diff","--name-only","d008162"],["git","ls-files","--others","--exclude-standard"]):
        run=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding="utf-8",errors="replace",check=True)
        changed.update(line for line in run.stdout.splitlines() if line)
    (ROOT/"reports/phase2_changed_files.txt").write_text("\n".join(sorted(changed))+"\n",encoding="utf-8")
    print("Phase 2 reports generated from",folder.name,qa.name,tests.name)


if __name__=="__main__":build_deliverables()
