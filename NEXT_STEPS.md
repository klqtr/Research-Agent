# 下一步与恢复入口（首轮检查点后继续）

## 已完成，不要重做或覆盖原始结果
官方规则已核验；七份真实文献已导入；开发集/新论文验证、真实541页与OCR已运行；54项测试通过；页图、引文往返、工作流、diff、CSV和证据框已通过浏览器验证。报告8页已重新渲染检查。先读MORNING_REPORT、RUN_LOG与reports/evidence_manifest.json。

## 无需用户输入即可继续的研发
1. 按官方高权重解析模块，增加按页惰性表格/图表结构提取与缓存，在真实样例验证，明确公式LaTeX未完成，不能把候选区域当作正确结构。
2. 增加用户显式启用的文献追踪配置与有界刷新任务（默认空/关闭），保存真实arXiv快照和失败日志；不自动启用商业模型或外部账户。
3. 改进图谱交互与来源边定位，扩展更多公开文献的质量验证；版本家族边不代表引用了最新修订版。
4. 将真实实验对比CSV、架构图与导出接入；不要针对data/holdout_cases.json继续调参。
5. 新改动后先相关回归，必要时完整回归；更新报告、日志、快照和真实Git提交，不伪造历史。

## 需要用户/外部条件
- 真实LLM：本机11434/1234服务不可用，没有配置授权端点/模型/调用预算。原生Function Calling的Mock契约不等于真实效果。未获得条件前，不运行付费API或下载大权重。
- 官方资料包/报名：缺官方扫描PDF与包哈希，学校/组别/个人信息待用户。
- 公网/评审仓库/视频：已有Dockerfile和脚本，未验证Docker、未推送/部署/提交。需要明确目标和资源，不擅自采购。

## 恢复命令
```powershell
.venv/Scripts/python.exe -m uvicorn src.app:app --host 127.0.0.1 --port 8000
.venv/Scripts/python.exe -m pytest -q --junitxml=experiments/recovery_tests.xml
.venv/Scripts/python.exe scripts/build_reports.py
.venv/Scripts/python.exe scripts/morning_report.py
.venv/Scripts/python.exe scripts/checkpoint.py
```

当前本地服务端口8000，先检查是否仍运行，不要重复占用。沙箱内部分Python进程曾挂起，正常执行权限下已真实通过；先分析错误再决定工具审批，不绕过权限。

ZIP在checkpoints，LATEST.json含SHA256；不含密钥、数据库、原PDF、OCR权重、venv或Git，源码/结果可恢复。原PDF仍在工作目录data/papers和data/library，重建按README。Git保留真实提交，未添加remote。

检索在新论文验证后冻结。若连续两轮无明显收益，转向新数据/真实模型/官方解析用例，不重复同一实验制造工作量。
