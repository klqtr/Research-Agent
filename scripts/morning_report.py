"""Write a timestamped, honest morning/checkpoint summary from saved evidence."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TZ = timezone(timedelta(hours=8))
START = datetime(2026, 10, 16, 0, 35, 23, tzinfo=TZ)


def main():
    now = datetime.now(TZ)
    elapsed = (now - START).total_seconds() / 60
    evidence = json.loads((ROOT / "reports/evidence_manifest.json").read_text(encoding="utf-8"))
    robustness = json.loads((ROOT / evidence["robustness"]).read_text(encoding="utf-8"))
    book = next(row for row in robustness if row["file"] == "UnderstandingDeepLearning_02_09_26_C.pdf")
    structure = json.loads((ROOT / evidence["page_structure"] / "summary.json").read_text(encoding="utf-8")) if evidence.get("page_structure") else None
    tracking = json.loads((ROOT / evidence["tracking_probe"]).read_text(encoding="utf-8")) if evidence.get("tracking_probe") else None
    tracking_note = (f"已观察{len(tracking['runs'])}次真实快照，状态{[r['status'] for r in tracking['runs']]}；是否达到刷新上限停用以原始watch字段为准。" if tracking else "未执行真实追踪实验。")
    paths = []
    for name in ("src", "tests", "scripts", "docs", "reports", "experiments", "output"):
        for path in (ROOT / name).rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts and not (path.parent == ROOT / "docs/sources" and path.suffix == ".js"):
                paths.append(path.relative_to(ROOT).as_posix())
    (ROOT / "reports/file_inventory.txt").write_text("\n".join(sorted(paths)) + "\n", encoding="utf-8")
    report = f"""# 晨间报告 / 当前可恢复检查点

> 生成：{now.isoformat(timespec='seconds')}（Asia/Shanghai）。这是持续研发检查点，不表示已经连续运行了7-8小时，也不表示比赛作品已全部完成。后续继续研发时应更新本文件。

## 1. 实际执行窗口
2026-10-16 00:35:23 至本报告生成时，墙钟约{elapsed:.1f}分钟，包含工具等待。真实起始目录为空，无现有成果被删除或推倒。没有付费API、云资源采购、大型模型下载、远程推送或赛事提交。

## 2. 已完成的主要功能
- 官方命题核验：必须做六模块全流程科研助手，35%技术深度/25%科研创新为最高权重；公开接口原始规则存档，冲突和待确认事项分列。
- 模块化Python/FastAPI/SQLite后端与真实Web工作台；可导入、管理和保留原始PDF，移除索引不删原文。
- 正文版本近似检测、v1/v7确认、逐块diff；首页标题/身份修复。
- 页/块/bbox证据、混合词汇检索、文献配额、设备数字事实重排、部分拒答、引用原文核验。
- 英语本地OCR、真实目录层级、按页表格候选/缓存/CSV、图注和数学glyph候选、541页真实作者版教材解析、服务端页图和证据框高亮、数字引用往返。
- 版本家族PageRank、Future Work待验证原文、真实arXiv搜索/受限下载API、反馈驱动词汇兴趣排序、显式启用的有界自动追踪和历史。
- CSV描述统计/SVG、可信写作模板/精确修订版参考条目、Mermaid脚本。
- 可选真实LLM问答/翻译与原生Function Calling工具往返适配；真实模型未配置，效果未验收。默认只运行披露清楚的确定性工作流。

## 3. 新增和修改的文件
初始为空，所有项目文件均为本轮新增，之后按测试迭代修改。完整清单见`reports/file_inventory.txt`。重点：
- `src/`：config、parsing、store、retrieval、model、planner、agent、tools、app及web。
- `data/`：开发/新论文验证标签、论文来源文件与英语OCR来源。原PDF/语言权重不入Git。
- `tests/`：核心边界、API、Mock模型契约、规划/工具协议、兴趣反馈。
- `scripts/`：获取/导入、评测/OCR/长文/HTTP、报告/PDF、检查点与本报告再生成。
- `docs/`：官方规则、技术方案、创新、架构、AI协同、模型状态。
- `reports/`：评测、消融、严格评审、视频脚本、答辩、提交清单、真实浏览器截图。
- `output/pdf/ResearchTrace_technical_report.pdf`：9页研发稿，已渲染检查。
- 根目录README、依赖锁、环境模板、Dockerfile、进度/恢复日志。

## 4. 已执行的测试
最新`{evidence['test_xml']}`：{evidence['test_counts']['tests']}项，失败{evidence['test_counts']['failures']}、错误{evidence['test_counts']['errors']}、跳过{evidence['test_counts']['skipped']}。一个上游AnyIO弃用警告保留。
初始9通过/12环境错误的XML未改写；修复临时目录/进程权限后分阶段通过。真实HTTP及公共arXiv检索已运行；未配置模型翻译503是预期结果。
真实浏览器验证：卡片、页图、引文往返、图谱、版本diff、工作流、真实数值绘图、证据框。初版PDF黑屏已修复，截图在reports/screenshots。

## 5. 实验结果与发现
- 开发集18正题：BM25严格全目标证据命中@5 66.7%，完整方案100%。此为调参后结果，不当作泛化证明。
- 两篇新论文12正题：BM25 75.0%，完整方案91.7%（11/12）。`cross_new_batch`失败；配额/设备重排在新论文集无额外总分收益，BM25在两道跨篇题均命中而融合只命中一道。
- 新论文3个负题应用层均拒答，只是有限规则探针，不是通用未知问题拒答能力。
- 真实Attention v1/v7正文相似度0.7171，旧版后上传有提醒；不宣称深层语义去重准确率。
- 真实同名作者版教材541页/7190块，最近一次约{book['latency_seconds']:.2f}秒，Python tracemalloc峰值{book['python_peak_tracemalloc_mb']:.2f}MiB，4页走OCR；不含原生引擎内存，未与官方包哈希核对。
- Attention两页派生扫描去重词召回约93.1%/95.8%，不是CER/WER、LaTeX或版式准确率，不是官方img.pdf。
- 真引用假结论仍可能通过原文匹配。引用完整性不等于语义蕴含，已保存失败探针。
- 真实LLM准确率、Token/费用、翻译质量和自主工具效果均未测，未填写模拟数字。

原始证据：`{evidence['development']}`、`{evidence['holdout']}`、`{evidence['robustness']}`、`{evidence['real_scan']}`；解释见reports/evaluation_report.md。

## 6. 当前运行方式
```powershell
.venv/Scripts/python.exe -m uvicorn src.app:app --host 127.0.0.1 --port 8000
```
本机地址http://127.0.0.1:8000，接口文档/docs。也可执行scripts/run.ps1。退出或中断后按README重启；运行中不代表公网演示已经完成。

## 7. 创新及其证据
版本家族与源头证据统一、跨篇检索配额、设备数字重排、引用完整性校验均有实现及明确对照；不宣称基础算法首创或SOTA。家族PageRank避免把多版本重复计权，边不声称旧论文引用了未来修订版。消融同时保留无收益结论。

## 第二阶段新增证据
表格开发/回归案例列数匹配{structure['correct_column_cases'] if structure else '未测'}/{structure['table_cases'] if structure else '未测'}，指定关键单元格匹配{structure['matched_selected_cells'] if structure else '未测'}/{structure['selected_cells'] if structure else '未测'}；不代表整个表格准确率。v2跨栏合并、v3短表题宽表丢列的失败记录均保留。{tracking_note}契约替身不冒充真实调度等待。

## 8. 未解决的技术问题
真实模型端点和调用预算缺失；无语义蕴含验证或神经Dense检索；复杂表格/公式/机构元数据不足；专业划词翻译和非数字引文联动不足；定时追踪长周期稳定性待验证/训练式多用户推荐未完成；尚无20篇真实图谱质量标注；Docker/公网/并发未验收。

## 9. 完整竞赛提交还缺什么
真实LLM核心能力及实验、官方全部资料包验收、六模块高级功能补齐；参赛者/学校/组别/报名信息；依赖与文献模型许可最终核验；GitHub/Gitee评审权限、公网服务和5-8分钟1080p普通话MP4。PDF当前是研发稿，需随最终实现更新，不能直接宣称完成参赛。严格内部成熟度43/100，不是官方评分或获奖预测。

## 10. 明天优先三件事
1. 提供已授权模型端点和明确调用预算；在保留原始输出的前提下验证真实规划、工具、问答和翻译，不把Mock契约当效果。
2. 取得官方资料包，重点补复杂PDF、公式表格、阅读翻译及更大盲测；保留当前新论文验证集，不对其反复调参。
3. 亲自理解架构并复现，再准备有访问控制的公网部署、评审仓库与正式视频，逐项完成提交清单。

## 后续自主研发恢复
先读NEXT_STEPS与RUN_LOG。现有Git保留真实阶段提交，另有checkpoints/LATEST.json指向可恢复源码/结果ZIP；ZIP不含密钥、原PDF、venv和数据库，公开演示数据按README下载重建。原始文件留在工作目录，不被检查点排除规则删除。
"""
    (ROOT / "MORNING_REPORT.md").write_text(report, encoding="utf-8")
    print("Morning/checkpoint report written; elapsed", round(elapsed, 1), "minutes")


if __name__ == "__main__":
    main()
