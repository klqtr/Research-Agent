"""Create the submission-draft PDF from recorded evidence; never invent metrics."""
import json
import os
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/pdf"
OUT.mkdir(parents=True, exist_ok=True)
font_candidates = ([Path(os.environ["RESEARCHTRACE_REPORT_FONT"])] if os.getenv("RESEARCHTRACE_REPORT_FONT") else []) + [Path(os.environ.get("WINDIR", "Windows")) / "Fonts" / "simsun.ttc", Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc")]
font_path = next((p for p in font_candidates if p.exists()), None)
if font_path is None:
    raise RuntimeError("需要可用的中文TrueType字体；请配置字体后再生成PDF")
pdfmetrics.registerFont(TTFont("ResearchBody", str(font_path)))
INK = colors.HexColor("#183d33")
MUTED = colors.HexColor("#607466")
GOLD = colors.HexColor("#b99a59")
styles = getSampleStyleSheet()
styles.add(ParagraphStyle("BodyCN", fontName="ResearchBody", fontSize=10.2, leading=17.2, textColor=INK, spaceAfter=8, wordWrap="CJK", splitLongWords=True))
styles.add(ParagraphStyle("TitleCN", parent=styles["BodyCN"], fontSize=29, leading=38, spaceAfter=18))
styles.add(ParagraphStyle("H1CN", parent=styles["BodyCN"], fontSize=19, leading=26, spaceAfter=14))
styles.add(ParagraphStyle("H2CN", parent=styles["BodyCN"], fontSize=13.5, leading=21, spaceBefore=12, spaceAfter=7))
styles.add(ParagraphStyle("SmallCN", parent=styles["BodyCN"], fontSize=8.4, leading=13))
styles.add(ParagraphStyle("CellCN", parent=styles["BodyCN"], fontSize=8.2, leading=12.5, spaceAfter=0))
story = []


def para(text, style="BodyCN"):
    text = text.replace("–", "-").replace("—", "-").replace("‑", "-")
    return Paragraph(escape(str(text)).replace("\n", "<br/>"), styles[style])


def p(text, style="BodyCN"):
    story.append(para(text, style))


def table(rows, widths):
    content = [[para(str(cell), "CellCN") for cell in row] for row in rows]
    t = Table(content, colWidths=widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#e7eddd")), ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f6f8f1")]), ("VALIGN", (0,0), (-1,-1), "TOP"), ("BOX", (0,0), (-1,-1), .5, colors.HexColor("#d3decb")), ("INNERGRID", (0,0), (-1,-1), .25, colors.HexColor("#dce4d6")), ("LEFTPADDING", (0,0), (-1,-1), 9), ("RIGHTPADDING", (0,0), (-1,-1), 9), ("TOPPADDING", (0,0), (-1,-1), 8), ("BOTTOMPADDING", (0,0), (-1,-1), 8)]))
    story.append(t)
    story.append(Spacer(1, 10))


def page(title):
    story.append(PageBreak())
    p(title, "H1CN")


def metrics(rows):
    result = [["方案", "全目标@5", "目标召回@5", "跨篇全命中", "中位ms"]]
    for row in rows:
        name = row["variant"].replace("fusion_quota_facets", "完整方案").replace("fusion_no_quota", "融合无配额").replace("fusion_quota", "融合有配额")
        result.append([name, f"{row['all_target_hit_at_5']:.1%}", f"{row['target_recall_at_5']:.1%}", f"{row['multi_all_hit_at_5']:.1%}", f"{row['median_latency_ms']:.2f}"])
    return result


manifest = json.loads((ROOT / "reports/evidence_manifest.json").read_text(encoding="utf-8"))
dev = json.loads((ROOT / manifest["development"] / "summary.json").read_text(encoding="utf-8"))
hold = json.loads((ROOT / manifest["holdout"] / "summary.json").read_text(encoding="utf-8"))
robust = json.loads((ROOT / manifest["robustness"]).read_text(encoding="utf-8"))
scan = json.loads((ROOT / manifest["real_scan"]).read_text(encoding="utf-8"))

p("RESEARCHTRACE / 研证", "SmallCN")
story.append(Spacer(1, 17))
p("版本感知、证据约束的\n科研助手", "TitleCN")
p("传智杯 AI 大模型创新应用挑战赛\n技术报告 · 研发原型与真实实验", "H2CN")
p("报告状态：可运行研发稿，尚未达到完整竞赛提交状态。\n没有真实大模型推理结果，不宣称一等奖水平。")
shot = ROOT / "reports/screenshots/library.jpg"
if shot.exists():
    story.append(Image(str(shot), width=170*mm, height=95.7*mm))
    story.append(Spacer(1, 12))
p("已完成：PDF/OCR、版本检查、证据检索、图谱、CSV与本地工作台。\n主要缺项：真实LLM、复杂公式表格、专业翻译联动、定时推荐与公网部署。")
p("参赛者、学校、组别、指导教师：待用户填写。\nAI协同研发，真实阶段记录与复现命令随项目提供。", "SmallCN")
p("证据生成时间：" + manifest["generated_at"], "SmallCN")

page("01 / 命题、需求与场景")
p("官方要求一款融合大语言模型与Agent架构的全流程科研助手，全面覆盖六模块：PDF细粒度解析、抗幻觉问答、联动翻译阅读、检索追踪推荐、引用图谱与综述、写作可视化。官方允许第三方API和AI辅助编程，不强制本地模型。")
table([["维度", "权重", "本项目关注"], ["Agent与大模型深度", "35%", "证据检索、受限规划、原生工具协议、引用核验、OCR"], ["科研场景创新", "25%", "版本家族、跨篇配额、细粒度硬件事实定位"], ["工程、实用、UI、学术价值", "各10%", "可运行、可追溯、可恢复及真实验证"]], [115,60,307])
p("真实问题", "H2CN")
p("研究者要比对论文训练设备和超参数时，搜索结果常混入摘要、修订版本和邻近主题；通用生成又可能把记忆当作正文证据。研证把论文版本、页/块坐标、检索结果与引用校验关联起来，让用户回到原文核验。")
p("大模型的必要性与边界", "H2CN")
p("LLM适合自然语言意图拆解、跨文综合、翻译与写作；数字统计、引用字符串校验和图算法由确定性程序负责。缺少已授权模型时，系统仅显示抽取证据和模板，不把它们包装为LLM回答。")
p("选择依据", "H2CN")
p("同一官方命题下比较了通用论文聊天、全自动科研假设代理、版本证据助手三个侧重方向。选择第三种，是因为它的差异可以通过版本误认、证据覆盖和引用伪造实验核验；没有宣称基础算法首创。")
p("提交与合规", "H2CN")
p("官方要求源码托管及真实Git历史、环境说明、5-8分钟1080p普通话MP4、最多30页PDF、公网演示。当前只有本地Git，未推送、未发布、未购买云资源。页面中部分日期/奖项比例存在内部矛盾，已在规则文档列待确认。")

page("02 / 系统架构与工程实现")
p("Web工作台 → FastAPI → 文档导入/有界工作流 → SQLite与原始PDF → 检索/图谱/CSV工具 → 证据输出或可选模型 → 引用校验 → 页图定位。", "H2CN")
table([["模块", "真实职责"], ["parsing.py", "逐页提取文本/bbox/标题/参考文献；无文本时英语OCR；首页识别arXiv身份。"], ["store.py", "SQLite存储文献、块与反馈；删除索引保留原PDF。"], ["retrieval.py", "BM25、字符三元组、RRF、文献配额与设备事实重排；引用原文子串验证。"], ["model.py / planner.py", "默认关闭的真实接口适配；原生工具调用白名单，最多4步；超时和有限重试。"], ["agent.py / tools.py", "确定性流程轨迹、部分拒答、家族PageRank、Future Work、arXiv、CSV与写作模板。"], ["app.py / web", "API、上传、原文下载、服务端页图与证据框、联动正文/译文工作台。"]], [122,360])
p("可靠性与资源控制", "H2CN")
p("单文件默认32MiB、最多1200页、问题最多6000字符；模型45秒超时与最多2次尝试；不接受任意URL下载或执行生成代码。密钥只来自环境。默认仅监听127.0.0.1。")
p("文档保真策略", "H2CN")
p("原PDF保留，页图只是交互渲染结果。证据块含物理页码和bbox，定位时可绘制高亮框。发现内置浏览器PDF插件黑屏后改为页图预览；这不等于PDF.js原生文字选择，也不等于公式/表格语义还原。")

page("03 / 算法设计与创新边界")
table([["设计", "机制", "不可夸大的边界"], ["版本感知", "正文4-shingle Jaccard与首页arXiv标识；版本确认与差异比较", "词汇近似并非学习式语义；不能仅一对版本报告去重准确率"], ["跨文检索", "BM25与字符RRF；每篇至少一个候选；设备数字信息重排", "没有神经Dense模型；配额可能损害全局相关性"], ["证据约束", "块ID存在性、原文quote子串、输出结构与部分拒答", "真引用仍可能支撑假结论，尚未验证语义蕴含"], ["版本家族图谱", "同论文多版合并代表节点，标题/标识匹配引用并计算PageRank", "边只指论文家族，不能当作引用了最新修订版"], ["Future Work线索", "原文候选提取与词汇去重", "不自动断言问题仍未解决或想法具有原创性"]], [85,185,212])
p("LLM规划状态", "H2CN")
p("已实现原生Function Calling、白名单工具执行和tool消息返回综合，但无已授权端点，实际运行仍是明确披露的确定性流程。原生协议仅通过Mock传输测试。模型MockTransport只测试网络契约，不产生科研效果数据。")
p("为何比普通API包装更可审查", "H2CN")
p("系统有可重算算法、真实PDF版本来源、逐页证据与坐标、错误引用拒绝探针、独立保存的基线/消融、旧版防静默覆盖和可恢复日志。它仍是研发原型，不能因这些工程机制就宣称已完成科研自主推理。")

page("04 / 检索实验与消融")
p("固定k=5。严格全目标命中要求选中指定论文、页码和原文子串；目标召回按标签计。该指标不是回答准确率；其他等价证据可能未被标签覆盖。开发集用于调参，另用两篇新论文验证，不混为盲测。")
p("开发集：18个有答案问题", "H2CN")
table(metrics(dev["retrieval"]), [137,84,88,92,81])
p("新论文验证：12个有答案问题", "H2CN")
table(metrics(hold["retrieval"]), [137,84,88,92,81])
p("开发集完整方案100%是适配后结果。新论文完整方案11/12；cross_new_batch未完整命中。配额与设备事实重排在新论文上没有增加总体命中；BM25在两道跨篇题均命中，而融合完整方案只命中一道。不能声称所有模块均有泛化收益。", "SmallCN")
p("开发集跨篇仅3题，新论文跨篇仅2题；没有显著性结论、真实用户效率或官方通过率。未进行LLM回答基线/消融，Token与费用记为未测，而不是0成本性能证明。", "SmallCN")

page("05 / OCR、长文与鲁棒性")
rows = [["文档", "页/块", "用时秒", "Python峰值MiB"]]
for item in robust:
    label = "真实同名作者版教材" if item["pages"] == 541 and item["chunks"] > 1000 else "合成541页压力样例" if item["pages"] == 541 else "合成扫描样例"
    rows.append([label, f"{item['pages']}/{item['chunks']}", f"{item['latency_seconds']:.3f}", f"{item['python_peak_tracemalloc_mb']:.2f}"])
table(rows, [200,90,92,100])
p("真实教材从作者官网链接的v5.0.3发布下载，文件名与赛题相同，541页、7190块，其中4页真实OCR。但未对照官方资料包哈希。峰值只计Python tracemalloc，不包括原生PDF/OCR内存，不能当作系统总内存。")
p("真实论文派生扫描（原第1和7页）", "H2CN")
table([["原页", "去重词召回", "去重词精确率"]] + [[str(r["original_page"]), f"{r['unique_word_recall']:.2%}", f"{r['unique_word_precision']:.2%}"] for r in scan["results"]], [100,191,191])
p("该扫描由真实PDF栅格化产生，不是官方img.pdf。去重词指标不是字符准确率、WER或公式/版式识别准确率；扫描OCR可以运行，不等于复杂学术PDF全面通过。")
p("自动化与失效探针", "H2CN")
counts = manifest["test_counts"]
p(f"最新自动化：{counts['tests']}项，失败{counts['failures']}，错误{counts['errors']}，跳过{counts['skipped']}。覆盖无效PDF、随机改名版本、来源锚点、图谱版本、私密/年份拒答、非法参数、CSV边界、超时与JSON契约。初始失败日志仍保留。")
p("真引用假结论探针仍通过：这是已确认的语义漏洞。新论文3个无答案探针在应用层均拒答，但不能推导一般未知问题拒答率。英语OCR路径需相对英文目录；中文语言数据与复杂表格公式尚未验收。")

page("06 / 六模块验收与严格内部评审")
table([["官方模块", "当前证据", "主要缺项"], ["PDF解析", "真实版本与541页/OCR", "表格结构、公式LaTeX、机构元数据"], ["RAG多文问答", "真实检索与引用锚点", "真实LLM、Dense、语义蕴含"], ["联动阅读翻译", "页图与正文译文滚动机制", "真实翻译、划词、非数字引文无损跳转"], ["追踪推荐", "真实arXiv、下载API和本地兴趣排序", "定时刷新、训练式推荐、多用户"], ["引用图谱与前沿", "家族PageRank与原文候选", "大规模标注、LLM综述、后续解决验证"], ["写作可视化", "模板、真实条目、CSV和Mermaid", "真实生成质量、多图形/全文翻译"]], [100,150,232])
p("内部成熟度39/100（非官方评分、非获奖预测）", "H2CN")
p("Agent深度10/35、创新10/25、工程6/10、实用4/10、UI5/10、学术价值4/10。没有真实模型效果与完整六模块的证据，不给完成度或模型效果虚高分。")
p("已经修复的高优先问题：PDF插件黑屏、v7标题误提取、教材身份被参考文献污染、版本重复计权、随机字符弱相关、私密信息与不存在年份拒答。")
p("下一步前三项：1）由用户配置并授权模型与调用预算，执行真实规划/综合/翻译和安全实验；2）取得官方资料包，完善公式表格与翻译阅读，再进行更广盲测；3）经人工理解复现后准备受保护公网服务、评审仓库与正式视频。")

page("07 / 复现、来源与提交状态")
p("最小复现", "H2CN")
p("Python 3.12创建venv并安装requirements-dev.txt；下载公开论文、作者版教材及英语OCR数据；scripts/import_papers.py导入；uvicorn src.app:app --host 127.0.0.1 --port 8000启动。逐条命令见README。")
p("pytest；scripts/evaluate.py；scripts/evaluate.py data/holdout_cases.json；scripts/robustness.py；scripts/scan_real_sample.py；启动服务后scripts/live_smoke.py。每轮保留时间戳原始证据、配置、数据哈希与汇总。", "SmallCN")
p("实验来源目录", "H2CN")
for name in ("development", "holdout", "test_xml", "robustness", "real_scan"):
    p(name + ": " + manifest[name], "SmallCN")
p("公开原始来源", "H2CN")
p("官方赛道：https://www.boxuegu.com/matchTrack/detail/?id=10040\n规则原始接口与正文：docs/sources/official_track_raw.json、official_rules.txt。\n真实论文：arxiv.org 的 1706.03762v1/v7、1810.04805v2、2005.11401v4、2005.14165v4、2004.04906v2。\n教材作者：https://udlbook.github.io/udlbook/，v5.0.3同名教材。\nOCR数据：github.com/tesseract-ocr/tessdata_fast，来源与哈希随附。", "SmallCN")
p("提交与原创性声明", "H2CN")
p("AI协同说明与Prompt位于docs/ai_collaboration.md及源代码。原PDF不随Git分发，依赖/模型/文献许可按上游核验，项目源码公开许可待用户决定。Dockerfile已写但未运行验收；公网、正式MP4、评审仓库权限、团队信息、官方完整测试尚未完成。")
p("所有结论仅基于列明的真实运行证据。没有调用付费模型，没有擅自推送、提交比赛、购买资源或虚构测试。")


def decorate(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#d4decb"))
    canvas.line(20*mm, 17*mm, 190*mm, 17*mm)
    canvas.setFont("ResearchBody", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(20*mm, 11*mm, "研证 / ResearchTrace · 技术报告研发稿")
    canvas.drawRightString(190*mm, 11*mm, str(doc.page))
    canvas.restoreState()


doc = SimpleDocTemplate(str(OUT / "ResearchTrace_technical_report.pdf"), pagesize=(210*mm, 297*mm), rightMargin=20*mm, leftMargin=20*mm, topMargin=19*mm, bottomMargin=23*mm, title="研证 ResearchTrace 技术报告", author="ResearchTrace AI-assisted development", pageCompression=1)
doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
print(OUT / "ResearchTrace_technical_report.pdf")
