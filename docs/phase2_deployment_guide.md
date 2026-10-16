# 本地运行、状态恢复与后续部署边界

## 已实际验收的本地路径
Python3.12安装requirements-dev.txt；从README下载原演示论文/OCR，导入原库；`uvicorn src.app:app --host 127.0.0.1 --port 8000`。本轮真实开发服务与HTTP响应已记录，本地浏览器验证不等于公网可用。

默认model_enabled=false，启动/刷新页面不发推理。模型授权后在本地.env配置，密钥不经Web返回。GET模型状态不发推理；显式能力探测会计入预算，不应被监控轮询自动触发。

## 状态与预算恢复
data_dir/research_runs.sqlite3保存原始响应、消息和工具完成ID；model_budget.sqlite3保存累计尝试、预留、使用量和每次单价快照。原PDF/主library.sqlite3继续由原模块维护。备份这些本地私有运行数据时与源码分开，不提交密钥/数据库或重新分发PDF。

同一个run_id恢复前校验目标、文献源指纹、版本和联网权限；完成记录直接读取，不增加推理。崩溃租约未过期会拒绝并发恢复；超过预算不会自动删除/清零账本。新增预算需用户确认后调整设置，原历史保留。执行与落盘间崩溃的只读工具可能重读；失败请求可能已经产生供应商费用，因此不自动退款预留。

## 评测恢复
data/phase2_qa_tasks.lock.json校验冻结数据。默认evaluate_phase2_qa.py只生成计划；--execute-models要求已授权配置和足够累计额度。原始JSONL逐条落盘，失败和降级单列。人工填写实际运行目录的human_review_template.json后，`score_phase2_qa.py 运行目录 审阅文件`生成新的scored文件，不覆盖原始输出；AI标签不能作为人工指标。

## 未验收路径
Dockerfile仍未在本机运行Docker验证；没有公网、登录鉴权、并发多用户隔离、按用户费用配额或正式MP4。不得把绑定localhost的原型直接暴露公网。正式部署前应由选手明确资源/预算，补认证、TLS、请求限速、数据隔离/留存策略、费用硬限额和评审账号，之后另做真实验收；本轮没有执行这些外部操作。

## 恢复检查点
checkpoints/LATEST.json指向源码/文档/原始实验ZIP与SHA，ZIP内CHECKPOINT_MANIFEST包含逐文件哈希，排除.env、数据库、PDF原文、OCR权重、venv、Git。原文件未删；来源脚本/锁和元数据保留。第二阶段新增三PDF的公开下载脚本固定版本，实际下载记录含SHA；发生上游变更应报错而不是伪称同源复现。
