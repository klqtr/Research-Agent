# 研证 ResearchTrace

面向第九届传智杯 AI 大模型创新应用挑战赛的“版本感知、证据约束科研助手”研发原型。官方赛题要求的是全流程科研助手，不是自由选题。规则证据见 [规则核验](docs/competition_requirements.md)。

**当前可以真实运行文献解析、英语 OCR、版本检查、证据检索、引用图谱与 CSV 分析。当前没有已授权的真实大模型，所以不能声称完成了 LLM 推理、翻译或全流程科研 Agent。** 模型网络契约采用显式 Mock 测试；它们不属于模型效果实验。

## 快速运行

Python 3.12（Windows / Linux）。普通 Python 安装：

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-dev.txt
.venv/Scripts/python.exe -m uvicorn src.app:app --host 127.0.0.1 --port 8000
```

打开 <http://127.0.0.1:8000>，接口文档 <http://127.0.0.1:8000/docs>。Linux 把 `.venv/Scripts/python.exe` 改成 `.venv/bin/python`。

本机已创建 `.venv`，可直接执行 `scripts/run.ps1`。Codex 捆绑 Python 创建 venv 时 ensurepip 曾失败，已用宿主 `python -m pip --python .venv/Scripts/python.exe install ...` 修复；这个特殊环境的受限进程可能挂起，经工具批准正常执行权限时已完成真实测试。不要将此环境问题误记为业务测试通过。

## 导入真实演示材料

以下脚本会显式联网下载公开材料，不使用付费 API；原 PDF 不进入 Git，重新分发前需核验原作者许可。

```powershell
.venv/Scripts/python.exe scripts/fetch_papers.py
.venv/Scripts/python.exe scripts/fetch_papers.py 2005.14165v4 2004.04906v2
.venv/Scripts/python.exe scripts/fetch_book.py
.venv/Scripts/python.exe scripts/fetch_ocr_data.py
.venv/Scripts/python.exe scripts/import_papers.py
```

OCR 使用 PyMuPDF 内置引擎和官方 Tesseract 英语语言数据，位于 `data/tessdata`。Windows 下请使用相对英文路径；中文绝对路径曾导致引擎初始化失败。没有语言数据时明确报告扫描页不可读，不会编造解析文字。中文 OCR 语言包尚未配置。

## 模型与环境

复制 `.env.example` 为 `.env`，按需配置。只加载 `RESEARCHTRACE_` 前缀的变量，系统环境变量优先。默认 `RESEARCHTRACE_MODEL_ENABLED=false`，模型任务会明确返回不可用；抽取式模式仍可检索原文。

只有在确认端点、模型许可、调用授权及费用预算后，才设置 `RESEARCHTRACE_MODEL_ENABLED=true`、`RESEARCHTRACE_MODEL_NAME`、`RESEARCHTRACE_MODEL_BASE_URL`、必要密钥。支持 OpenAI 兼容的 `/chat/completions`；远程接口要求 HTTPS，本机可用 HTTP。默认45秒超时、最多两次尝试、最多1600输出token/次；工作流最多4个本地工具步骤。该版本无累计费用预算器，不能在无人值守时随意启用商业端点。

`/api/ask`：真实模型综合为显式 `use_model=true`；`/api/workflow`：可选真实模型原生工具调用 → 白名单执行 → tool消息返回 → 引用核验。**原生 Function Calling 适配已实现，仅通过模拟传输契约测试，尚未真实模型验收**，未配置模型时只是已披露的确定性工作流。翻译 `/api/translate` 需要真实模型。输出中的原文匹配仅验证引用完整性，不证明语义蕴含。

## 实际实现与差距

|官方模块|已实现且可运行|仍缺少|
|---|---|---|
|PDF 管理解析|批量上传、保留原PDF、页码/bbox、原生目录层级、原文OCR、按页表格候选/缓存/CSV、图注/图像/数学glyph候选、内容shingle去重、版本确认/diff|可靠作者/机构、完整复杂单元格与合并表头、扫描表格结构、公式LaTeX、学习式语义去重|
|抗幻觉问答|BM25+字符RRF、文献配额、硬件事实重排、证据跳转、引用约束、部分拒答|真实模型效果实验、Dense/Rerank模型、语义蕴含验证|
|联动阅读翻译|原始版式页图、bbox高亮/原PDF链接、数字引文跳转返回、按页正文/译文同步滚动、翻译接口及不可用提示|划词/悬停、PDF像素级双向联动、作者年份等完整引文无损跳转、真实翻译质量验证|
|搜索追踪推荐|真实arXiv检索/下载API、持久兴趣排序、显式启用的定时追踪/租约/限额/版本去重/运行历史|长周期稳定性、训练式多用户推荐、PubMed、引用含金量可靠判定|
|图谱综述前沿|引用标题/标识匹配、版本家族合并、PageRank、Future Work原文候选|真实LLM综述、时间线证伪旧Idea、20篇真实图谱质量标注|
|写作可视化|可信文献库参考列表、写作模板、Mermaid脚本、CSV统计/SVG图表|真实LLM论文框架与图注、TikZ等完整脚本、多类型图表、一键全文学术翻译|

## 评测复现

```powershell
.venv/Scripts/python.exe -m pytest -q --junitxml=experiments/reproduced_tests.xml
.venv/Scripts/python.exe scripts/run_tests.py
.venv/Scripts/python.exe scripts/evaluate.py
.venv/Scripts/python.exe scripts/evaluate.py data/holdout_cases.json
.venv/Scripts/python.exe scripts/robustness.py
.venv/Scripts/python.exe scripts/scan_real_sample.py
.venv/Scripts/python.exe scripts/evaluate_page_structure.py
# 服务启动后：
.venv/Scripts/python.exe scripts/live_smoke.py
```

每次检索评测生成独立时间戳目录，含配置、数据哈希、逐题原文证据和汇总。开发集21题（18正/3负），新论文验证15题（12正/3负）；指标是**严格原文目标证据命中@5**，不是回答准确率。先用开发集发现问题并修改，再冻结检索算法跑新论文验证；不能把开发集改善宣称为无偏泛化性能。详细结论见 `reports/evaluation_report.md`、`reports/ablation_study.md`。

`scripts/run_tests.py`只运行完整测试集并保存stdout、XML、命令和退出码；报告优先使用LATEST_TESTS指针，局部模块测试不会覆盖完整回归的证据。

文献追踪在“检索与追踪”中显式保存/启用，默认空/停用。30–1440分钟间隔，每条最多48次刷新、每60秒调度最多2条，次数到上限自动停用；只访问公共arXiv元数据。调度仅随本地Web服务运行。真实实验两次刷新于01:55:39与02:26:07成功，第二条为scheduled，随后达到两次预算自动停用，原始状态已保存；这不代表长期稳定性。详情见reports/tracking_report.md。`scripts/tracking_probe.py`默认只读，`--create`才创建有界条目。

引用图现有21份PDF/20家族、71条边，点击节点或排序条目聚焦邻居，引用证据按钮回到真实参考页/块，可导出带编号图例SVG。同库同元数据旧匹配64条，新增7条经原PDF逐块复核；71条只通过锚点完整性检查，不能称为引用精确率100%。PageRank不代表论文质量，版本家族边不推断引用最新修订版。

扩展库来源：`scripts/expand_references.py`默认仅列候选，`--download --limit 14`才按原文arXiv标识受限下载；现有库已经扩展，重复执行会选择其他候选，不能用于重现同一21份库。原始manifest见experiments/LATEST_REFERENCE_EXPANSION.txt。`scripts/enrich_metadata.py`只对精确ID+版本补齐公开元数据，原始Atom留存；机构缺失不猜测。图谱复核入口为`scripts/evaluate_graph.py`，需同一文献ID集合，详见reports/citation_graph_report.md。

精确重建21份演示文献库：
```powershell
# 默认只校验；--download-missing 才下载锁定来源，不覆盖不匹配文件
.venv/Scripts/python.exe scripts/replay_library_sources.py --download-missing
.venv/Scripts/python.exe scripts/fetch_ocr_data.py
.venv/Scripts/python.exe scripts/import_papers.py
.venv/Scripts/python.exe scripts/enrich_metadata.py --from-atom experiments/metadata_20261016_022037/raw.atom
.venv/Scripts/python.exe scripts/evaluate_graph.py
```
`data/library_sources.json`锁定精确版本、原文件名和SHA256。未来上游文件哈希改变会报错，不冒称同源复现；缺失文件联网恢复路径尚未重新下载验收。本机已将21份PDF重新解析到隔离临时库、离线恢复20份元数据，完整20节点/71边锚点及排名一致（6.69秒、零联网），原库未修改；记录见experiments/LATEST_REBUILD.txt。可运行`scripts/rebuild_library_probe.py`复核。

真实教材为作者官网发布的同名541页版本，未取得官方资料包哈希；扫描件是由真实论文两页派生，不是官方 `1706.03762v1_img.pdf`。合成541页样例单独标记。

## 结构

`src/parsing.py` 文档感知，`store.py` SQLite，`retrieval.py` 检索/引用校验，`model.py` 真实模型适配，`planner.py` 有界计划，`agent.py` 证据工作流，`tools.py` 研究工具，`app.py` API，`src/web` 原生 Web 前端，`scripts` 复现入口，`tests` 边界/契约回归，`experiments` 原始结果，`docs` 规则/方案，`reports` 报告/答辩。

报告再生成：可在额外安装`requirements-report.txt`并提供中文TrueType字体的环境执行`scripts/build_reports.py`、`scripts/build_pdf_report.py`。本次使用Windows系统宋体，其他系统可设置`RESEARCHTRACE_REPORT_FONT`为可用中文TrueType字体路径。PDF需渲染检查后再交付。

## 部署

提供 Dockerfile（尚未在本机安装/运行 Docker 验证）：

```sh
docker build -t researchtrace .
docker run --rm -p 127.0.0.1:8000:8000 -v researchtrace-data:/app/data researchtrace
```

容器镜像不会携带论文、密钥和 OCR 语言数据；按需挂载。当前为本地单用户原型，没有公网认证/配额/运维方案，尚未公开发布。正式参赛还需要公网演示、仓库评审权限、5–8分钟1080p普通话视频和≤30页PDF。

## 开发真实性与团队

参赛者姓名、学校、组别、指导教师：**待用户填写，不虚构**。代码与文档由本次 AI 辅助研发生成并通过所列实际测试，AI 协同说明见 `docs/ai_collaboration.md`。保留真实阶段 Git 历史，不回填虚构提交。没有推送远程、购买云资源或调用付费模型。

源代码公开许可证尚待用户决定；依赖及论文许可需按上游声明核验。PyMuPDF 有其上游许可证约束，不能因为本项目自研就忽略依赖许可。
