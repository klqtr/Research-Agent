# 第二阶段回答评测协议 v1

## 数据、泄漏与来源
data/phase2_qa_tasks.json共18任务：6开发、12冻结新应用领域草案。精确SHA在同名lock文件；运行器拒绝不匹配文件。开发任务复用已调试NLP来源，不当作泛化数据。新增FNO v1/v3与MoleculeNet v3来自原始arXiv，覆盖科学计算/分子性质；仍属机器学习交叉应用，不宣称全学科覆盖。

任务由AI辅助选择并按实际页/块/子串核对，**没有外部人工金标，也不是第三方盲测**。这些PDF曾用于解析/工程检查；不得把它们对整个系统称为完全未见数据。词汇检索器沿用原冻结实现；没有使用旧holdout失败题调参，没有训练/微调模型或用真实测试回答调Prompt。未来真实模型调优仅限development，冻结任务只在冻结Prompt/代码/模型/预算后运行，若看过失败并改代码必须另建最终测试集。

## 对照与消融
|方案|证据与处理|不能隐去的差异|
|---|---|---|
|direct_llm|无RAG上下文，允许知识回答或拒答|无来源时引用精确率分母可为0，记NA|
|conventional_rag|相同BM25+字符检索6块+基础模型|无发布校验，保留原输出|
|citation_integrity_rag|常规RAG+原有quote/ID完整性校验|不能证明蕴含|
|proposed_agent|版本策略+结果驱动工具+独立保守发布关卡|最多4模型轮/6工具，额外计算须报告|
|without_version|新Agent中改为all版本|显式旧版任务的版本意图仍须人工评分|
|without_verifier|新Agent关闭独立支持关卡，仍保留基本引用完整性|无任意无来源发布接口，消融仅在运行器内部|
|without_facet_rerank|新Agent关闭现有硬件事实重排|非神经Reranker消融|
|without_agent_planning|同版本策略、相同检索/关卡，一次模型回答|不称为等计算量|

相同任务、配置模型、temperature=0、每请求输出1600默认上限；共享账本默认8请求/100000预留单位，Agent最多4回合。实际计算量不相同，必须同时报告请求/Token/延迟/费用，不能声称公平等成本。计划完整对比需要用户确认足够预算，不能自动提高上限。建议按任务配对评价并单独报告成本归一化视角。

## 指标定义
|指标|单位/计算|真值及边界|
|---|---|---|
|Answer Correctness|人工整体正确且覆盖任务必要事实的回答数/已完成整体审阅回答数|不能用source substring或模型自评分替代；缺人工记null|
|Citation Precision|人工认为来源相关且支持所附断言的引文数/已审阅引文数|需同时检查出处及含义，无引文分母0记NA|
|Citation Recall|被答案充分引用覆盖的必要证据单元数/人工确定必要证据单元数|草案targets只是候选，需真实审阅；不是检索Recall@k|
|Evidence Support Rate|fully_supported事实数/已判定支持状态的事实数|unknown排除并另报；partial单列，不视为充分支持|
|Hallucination Rate|evidence_conflict或insufficient_evidence事实数/已判定事实数|partial单列，unknown排除；不得把规则拒绝率当此指标|
|Version Consistency|所有事实正确附着任务所需版本的回答数/适用且审阅回答数|不是“选择最新就是正确”；用户指定旧版应尊重|
|Task Success Rate|全部必要事实+引用+版本+适当拒答均满足的任务数/已审阅任务数|保守空回答不自动成功，回答率须报告|
|Latency|真实端点完整任务墙钟，median/P95/失败分列|计划检查或Mock延迟不当模型性能|
|Token Cost|实际provider prompt/completion usage；按用户给定单价计算|缺usage/单价记null；UTF8预算预留非真实Token和账单保证|

每条事实须原子化；同一句多事实先拆分，人工标fully/partial/conflict/insufficient/unknown，并保存原始回答、源页/块、引用与理由。至少双人抽查一部分、记录分歧；本轮实际人工人数0，不填一致性系数。reviewer_type=human只是数据字段，不能证明审阅真实，必须由真实选手/审阅者执行。图谱另有380对全矩阵空标注，不能拿算法输出作为金标。

## 统计与失败处理
二元指标可附Wilson95%区间（qa_metrics.wilson），样本少/相同论文内相关性限制推断；不能凭区间宣布显著获胜。真实模型可在固定任务集重复3次，单独报告波动；未运行重复不填标准差。错误、超时、预算停止和抽取降级单列，不伪装成成功真实Agent回答，也不静默删除困难样本。

运行器默认仅计划。未授权模型或未显式--execute-models时生成not_run记录与null指标。外部人工完成后可调用qa_metrics.summarize(records,annotations)汇总；AI标签不进入human指标。保留原始JSONL、config、模型实际返回名、数据/检索代码SHA、时间、温度、限额、工具轨迹和人工审阅文件。

命令行汇总：`scripts/score_phase2_qa.py 运行目录 审阅JSON文件`。拒绝未知/重复记录ID、给未执行记录填完整评分、用AI审阅冒充human，以及缺少整体正确/成功标签的完整审阅；结果另存带时间戳文件，原始回答不改。无需模型时空标注汇总仍为null，不填0准确率。
