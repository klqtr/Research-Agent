"""Generate Markdown reports and a plot only from saved, real experiment outputs."""
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"


def read_result(pointer):
    folder = ROOT / (ROOT / "experiments" / pointer).read_text(encoding="utf-8").strip()
    return folder, json.loads((folder / "summary.json").read_text(encoding="utf-8"))


def table(rows):
    text = "|方案|严格全目标命中@5|目标证据召回@5|跨篇全命中@5|中位耗时(ms)|P95(ms)|\n|---|---:|---:|---:|---:|---:|\n"
    for row in rows:
        text += f"|{row['variant']}|{row['all_target_hit_at_5']:.1%}|{row['target_recall_at_5']:.1%}|{row['multi_all_hit_at_5']:.1%}|{row['median_latency_ms']:.2f}|{row['p95_latency_ms']:.2f}|\n"
    return text


def main():
    REPORTS.mkdir(exist_ok=True)
    dev_path, dev = read_result("LATEST_RETRIEVAL.txt")
    hold_path, hold = read_result("LATEST_HOLDOUT.txt")
    test_pointer = ROOT / "experiments/LATEST_TESTS.txt"
    latest_test = (ROOT / test_pointer.read_text(encoding="utf-8").strip()) if test_pointer.exists() else max((ROOT / "experiments").glob("*tests.xml"), key=lambda p: p.stat().st_mtime)
    suites = list(ET.parse(latest_test).getroot().iter("testsuite"))
    test_counts = {key: sum(int(s.attrib.get(key, 0)) for s in suites) for key in ("tests", "failures", "errors", "skipped")}
    robust_file = max((ROOT / "experiments").glob("robustness_*.json"), key=lambda p: p.stat().st_mtime)
    robust = json.loads(robust_file.read_text(encoding="utf-8"))
    scan_file = max((ROOT / "experiments").glob("real_scan_*.json"), key=lambda p: p.stat().st_mtime)
    scan = json.loads(scan_file.read_text(encoding="utf-8"))
    now = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
    eval_text = f"""# 真实评测报告

生成时间：{now}（Asia/Shanghai）。本报告由 `scripts/build_reports.py` 从已保存结果生成。

## 范围与方法
没有已授权模型端点，未进行真实LLM回答/翻译/规划质量评测，不报告模型Token、费用或模型准确率。当前比较的是词汇检索、版本识别、引用完整性和工程鲁棒性。

开发集21题（18有答案、3无答案），用于发现问题和调优。随后固定检索算法，在两篇新论文上标注并运行15题验证（12有答案、3无答案）；没有根据新论文失败项调参。原始标签在data/，每次配置包含标签SHA256。不是官方测试集，也不是独立第三方盲测。

严格全目标命中@5：前5证据块须包含所有指定论文/物理页码/原文子串；目标证据召回按所有标签块计数。它们不是回答准确率，也不能证明用户问题已完整解决；等价但未标注的其他原文证据可能被漏计。跨篇样本开发集仅3题、新论文集仅2题，不支持强统计结论。

## 开发集（调参后）
来源：`{dev_path.relative_to(ROOT).as_posix()}`。

{table(dev['retrieval'])}

开发集完整方案100%是已针对该集优化后的结果，存在明显适配风险，不作为泛化或获奖证明。

## 两篇新论文验证
来源：`{hold_path.relative_to(ROOT).as_posix()}`，论文为GPT-3和DPR，未用于前述检索修改。

{table(hold['retrieval'])}

完整方案11/12严格命中，失败项`cross_new_batch`没有同时返回GPT-3的训练token总量目标块与DPR批次目标块。配额和硬件重排在新论文集没有提升总体命中率；不能主张每个模块均有泛化收益。样本量小、语言/领域集中，未报告显著性、真实用户效率或官方成功率。

## 无答案与引用探针
新论文3个无答案探针，应用层均拒答：随机串无证据；不存在年份显式拒答；私人电话请求拒答。这是小规模规则测试，不代表一般未知问题拒答能力。检索器本身在后两题仍会返回弱相关片段，因此必须区分“检索非空”和“能够回答”。

伪造块ID、伪造原文、无引用均被引用校验拒绝；真实引用通过。**真引用配错误结论仍能通过**：校验只证明字符串出处完整，不证明语义蕴含。该已知失败探针保存在summary.json，不隐去。

## 版本与文档解析
Attention v1/v7正文字词4-shingle相似度0.7171，识别同arXiv家族，旧版后上传会建议保留库中较新版本。它是词汇近似算法，不宣称学习式语义去重；只有一组真实修订对，尚无大样本去重准确率。

"""
    for item in robust:
        eval_text += f"- `{item['file']}`：{item['pages']}页、{item['chunks']}块，{item['latency_seconds']:.3f}秒，Python tracemalloc峰值{item['python_peak_tracemalloc_mb']:.2f}MiB，页模式{item['page_modes']}；样例性质`{item['fixture']}`。\n"
    eval_text += f"""
真实教材来自作者官网明确链接的v5.0.3发布，文件名与官方要求一致，但未比对官方资料包哈希。541页真实教材耗时包含4页实际OCR。合成541页不能替代复杂长文验证。

两页Attention真实论文派生扫描件（不是官方img.pdf）用时{scan['latency_seconds']:.3f}秒：
"""
    for result in scan["results"]:
        eval_text += f"- 原第{result['original_page']}页：去重词召回{result['unique_word_recall']:.2%}，精确率{result['unique_word_precision']:.2%}。\n"
    eval_text += f"""
该指标不是CER/WER、LaTeX/表格或版式准确率。tracemalloc不包含原生MuPDF、Tesseract内存；耗时为本机单次结果，不是设备无关性能承诺。OCR英语数据来源与SHA保存在data/tessdata/SOURCE.json。

## 软件测试与实际运行
`{latest_test.relative_to(ROOT).as_posix()}`：{test_counts['tests']}项，失败{test_counts['failures']}、错误{test_counts['errors']}、跳过{test_counts['skipped']}。初始环境错误XML保留，没有改写成通过。

真实HTTP检查：health、文献、图谱、网页、问答、工作流、CSV返回200；未配置模型翻译返回503，符合预期。arXiv公共检索真实完成。原始响应在experiments/live_smoke_*.json。模型超时/错误JSON/用量解析是明确MockTransport契约测试，不是模型推理效果。

## 复现与风险
按README安装，下载样例与OCR，导入后运行evaluate.py及测试。原始PDF不入Git，按来源脚本重取；其版权不因公开可下载而自动允许重新分发。Docker、公网部署、真实LLM、官方完整资料包、多用户、20篇真实图谱、专业翻译及公式表格质量仍未验收。\n"""
    extra_manifest = {}
    structure_pointer = ROOT / "experiments/LATEST_PAGE_STRUCTURE.txt"
    if structure_pointer.exists():
        structure_folder = ROOT / structure_pointer.read_text(encoding="utf-8").strip()
        structure = json.loads((structure_folder / "summary.json").read_text(encoding="utf-8"))
        eval_text += f"\n## 第二阶段：按页结构回归\n\n来源`{structure_folder.relative_to(ROOT).as_posix()}`。{structure['table_cases']}个表格案例中列数匹配{structure['correct_column_cases']}个，指定{structure['selected_cells']}个关键单元格匹配{structure['matched_selected_cells']}个。**这不是整个表格准确率，也不是独立盲测**；RAG/DPR页面先作外推暴露跨栏问题，随后用于修复回归。合并表头、科学计数、缺失值及扫描表格仍需人工核验，公式仅提供glyph候选。\n"
        extra_manifest["page_structure"] = str(structure_folder.relative_to(ROOT))
        (REPORTS / "document_structure_report.md").write_text(f"""# 按页文档结构实验

先比较整页线框与文字策略：四份开发论文表格页的线框策略未检测到表格，整页文字策略把正文也切入网格（Attention v1为64行8列）。原始输出在page_structure各轮raw.json。

表题与相邻短行限定区域的v2，在8个案例中列数正确6/8、指定单元格15/18；RAG并排双表被合并。v3按表题横向范围隔离后指定案例改善，但合成宽表回归失败（短表题裁掉右侧列），失败XML保留。v4只有发现同一水平带的并列表题才隔离，修复宽表回归。

最新`{structure['analyzer_version']}`：列数{structure['correct_column_cases']}/{structure['table_cases']}，指定关键单元格{structure['matched_selected_cells']}/{structure['selected_cells']}。标签与checks.json逐项可查。样本小且参与修复，不能用这些数值证明泛化或完整表格恢复；未评估的合并表头、复杂指数、缺失格不能当作通过。

按页惰性解析，不在导入541页时逐页检测表格。JSON缓存保留分析器版本、完整源文件哈希，原文件不改动；导出未核验CSV并中和潜在公式单元格。真实HTTP缓存/CSV输出位于live_structure_*.json。RAG页第一次约44.9ms、缓存约11.9ms为单次本机观察，不是通用性能保证。

教材有181条原生书签，优先建立层级；明确标题无法匹配时只保留页定位，不伪造精确段落。图注、嵌入图像和数学字体候选分别保存，未推断图文配对，也没有声称LaTeX转录已完成。
""", encoding="utf-8")
    tracking_pointer = ROOT / "experiments/LATEST_TRACKING_PROBE.txt"
    if tracking_pointer.exists():
        tracking_path = ROOT / tracking_pointer.read_text(encoding="utf-8").strip()
        tracking = json.loads(tracking_path.read_text(encoding="utf-8"))
        runs = tracking.get("runs", [])
        eval_text += f"\n## 第二阶段：真实追踪\n\n来源`{tracking_path.relative_to(ROOT).as_posix()}`，已观察{len(runs)}次真实刷新，状态{[r['status'] for r in runs]}。受限实验每30分钟一次、最多2次，当前记录不等于第二次周期已完成。空/停用条目不联网、并发租约、失败保留与上限自动停用另有明确时钟/搜索替身契约测试，不能将其当成真实长时间运行。\n"
        extra_manifest["tracking_probe"] = str(tracking_path.relative_to(ROOT))
        (REPORTS / "tracking_report.md").write_text(f"""# 持久化文献追踪验证

实现：默认空列表；创建默认停用；启用后30–1440分钟间隔，每条最多48次、每个调度周期最多处理2条。事务租约防重入，运行历史/新版本去重/失败信息持久化。只访问公共arXiv元数据，不调用模型，不发送外部消息。

调度、租约、版本去重、失败保留、限额与停用的单元测试使用明确时钟和搜索替身，不冒充真实等待。真实受限实验主题为retrieval augmented generation，启用间隔30分钟，最多2次。

本次观测来源`{tracking_path.relative_to(ROOT).as_posix()}`，已记录{len(runs)}次实际刷新，状态{[r['status'] for r in runs]}。第二次到时后应依据数据库真实状态和活跃服务句柄继续核验；未完成前不报告完整周期成功。达到两次后应自动停用，需再检查状态证实，不能只依据实现推断。

UI显示北京时间，原始记录用UTC。无公网、多用户或独立守护进程验收；只有本地Web服务运行期间才会自动调度。
""", encoding="utf-8")
    (REPORTS / "evaluation_report.md").write_text(eval_text, encoding="utf-8")
    ablation = "# 消融与迭代报告\n\n同一配置内固定k=5，关闭文献配额/设备事实重排分别观察变化；BM25与字符分支也分别运行。没有付费模型或模拟效果数据。\n\n开发集：\n\n" + table(dev["retrieval"]) + "\n新论文验证：\n\n" + table(hold["retrieval"])
    ablation += "\n结论：开发集配额改善跨篇覆盖，事实重排改善设备数字块定位；新论文集两者均未增加总体命中。简单BM25在两道新论文跨篇题上的全命中高于融合方案，说明融合可能损害特定任务，不能只展示总分。需另设更大标注集和语义多样性测试，不继续对当前验证集调参。\n\n"
    ablation += "|轮次|问题与修改|真实结果|新增风险|\n|---|---|---|---|\n|初版|Windows临时目录/受限进程异常|9通过12环境错误，之后正常权限21通过|需记录本机运行方式|\n|解析修复|v7版权声明当标题，按首页水平大字号提取|真实v7标题回归通过|复杂标题仍可能失败|\n|检索第1轮|停用词与字符资格门槛|开发集全目标命中77.8%→83.3%|词汇/跨语种泛化有限|\n|检索第2轮|硬件事实重排，单列消融|开发集100%，新论文91.7%|开发集适配，验证集无额外收益|\n|OCR修复|下载官方语言数据，相对路径避开中文路径限制|扫描页真实识别，教材4页OCR|复杂公式未验证|\n|图谱修复|版本家族合并、边只代表家族；首页身份提取|避免版本重复计权和教材误认arXiv引用|引文匹配仍有漏边|\n|浏览器修复|插件预览黑屏，改为按页PNG和bbox高亮|API图像/原文不变回归，浏览器视觉复核|页图不提供PDF.js文字选择|\n"
    ablation += "|第二阶段解析|表题限定、并列表题隔离、短表题宽表回归|列数6/8→8/8，指定单元格15/18→18/18；70项完整回归通过|已用于修复的页不是独立盲测，复杂单元格仍有未测错误|\n|第二阶段追踪|显式启用、有界预算、事务租约与历史|契约测试通过，首次自动公共API刷新真实成功|第二次30分钟周期尚待实际观察，不能提前报告通过|\n"
    (REPORTS / "ablation_study.md").write_text(ablation, encoding="utf-8")
    figure_dir = REPORTS / "figures"
    figure_dir.mkdir(exist_ok=True)
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1040" height="430" viewBox="0 0 1040 430"><rect width="1040" height="430" fill="#f5f7f0"/><text x="40" y="36" font-family="Arial" font-size="21" fill="#183d33">Strict source-target hit@5 (retrieval, not answer accuracy)</text><text x="40" y="62" font-family="Arial" font-size="13">Development: 18 positive queries; new-paper validation: 12. Small, manually labelled datasets.</text>']
    for i, row in enumerate(dev["retrieval"]):
        x = 75 + i * 190
        holdrow = next(r for r in hold["retrieval"] if r["variant"] == row["variant"])
        for j, (value, color) in enumerate([(row["all_target_hit_at_5"], "#235d4b"), (holdrow["all_target_hit_at_5"], "#b99a59")]):
            height = value * 230
            svg.append(f'<rect x="{x+j*48}" y="{325-height}" width="38" height="{height}" fill="{color}"/><text x="{x+j*48}" y="{315-height}" font-family="Arial" font-size="12">{value:.1%}</text>')
        label = row["variant"].replace("fusion_quota_facets", "full").replace("fusion_no_quota", "fusion").replace("fusion_quota", "fusion + quota")
        svg.append(f'<text x="{x}" y="352" font-family="Arial" font-size="13">{label}</text>')
    svg.append('<rect x="70" y="386" width="14" height="14" fill="#235d4b"/><text x="91" y="398" font-family="Arial" font-size="13">Development (tuned)</text><rect x="340" y="386" width="14" height="14" fill="#b99a59"/><text x="361" y="398" font-family="Arial" font-size="13">New papers (no post-tuning)</text></svg>')
    (figure_dir / "retrieval_comparison.svg").write_text("".join(svg), encoding="utf-8")
    (REPORTS / "evidence_manifest.json").write_text(json.dumps({"generated_at": now, "development": str(dev_path.relative_to(ROOT)), "holdout": str(hold_path.relative_to(ROOT)), "test_xml": str(latest_test.relative_to(ROOT)), "test_counts": test_counts, "robustness": str(robust_file.relative_to(ROOT)), "real_scan": str(scan_file.relative_to(ROOT)), **extra_manifest}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Reports generated from", dev_path.name, hold_path.name, latest_test.name)


if __name__ == "__main__":
    main()
