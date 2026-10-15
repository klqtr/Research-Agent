# 下一步与恢复入口（首轮检查点后继续）

## 已完成，不要重做或覆盖原始结果
官方规则已核验；七份真实文献已导入；开发集/新论文验证、真实541页与OCR已运行；70项完整测试通过；页图、引文往返、工作流、diff、CSV、证据框、结构候选与追踪快照已通过浏览器验证。报告9页已渲染检查。先读MORNING_REPORT、RUN_LOG与reports/evidence_manifest.json。

## 无需用户输入即可继续的研发
1. 已完成第二阶段按页惰性结构/缓存/CSV、181条教材原生目录、显式有界追踪。不要重做；8个表格案例和18个关键单元格是开发/修复回归，不能宣称全表准确率或独立盲测；LaTeX与扫描表结构仍未完成。
2. 继续核验真实追踪：watch id=1、主题retrieval augmented generation，30分钟/最多2次，首个实际快照01:55:39北京时间完成，第二次预计02:25:39后由60秒调度扫描触发。原始状态见LATEST_TRACKING_PROBE；截至02:11只观察1次，不能提前报告完成或停止。先确认现有服务/任务状态，不因一次观测超时重建任务。
3. 改进真实图谱交互与来源边定位，并通过已有参考文献里的实际arXiv标识受限扩展到20个文献家族验证；每批限定数量/文件大小/下载间隔，不重新分发原PDF。至少单独人工核验若干引用边/非引用边，不用算法自己的输出当金标。版本家族边不代表引用了最新修订版。
4. 将真实实验对比CSV、架构图与导出接入；不要针对data/holdout_cases.json继续调参。
5. 新改动后先相关回归，必要时完整回归；更新报告、日志、快照和真实Git提交，不伪造历史。

## 需要用户/外部条件
- 真实LLM：本机11434/1234服务不可用，没有配置授权端点/模型/调用预算。原生Function Calling的Mock契约不等于真实效果。未获得条件前，不运行付费API或下载大权重。
- 官方资料包/报名：缺官方扫描PDF与包哈希，学校/组别/个人信息待用户。
- 公网/评审仓库/视频：已有Dockerfile和脚本，未验证Docker、未推送/部署/提交。需要明确目标和资源，不擅自采购。

## 恢复命令
```powershell
.venv/Scripts/python.exe -m uvicorn src.app:app --host 127.0.0.1 --port 8000
.venv/Scripts/python.exe scripts/run_tests.py
.venv/Scripts/python.exe scripts/tracking_probe.py
.venv/Scripts/python.exe scripts/build_reports.py
.venv/Scripts/python.exe scripts/morning_report.py
.venv/Scripts/python.exe scripts/checkpoint.py
```

当前本地服务端口8000，先检查是否仍运行，不要重复占用。沙箱内部分Python进程曾挂起，正常执行权限下已真实通过；先分析错误再决定工具审批，不绕过权限。

本阶段最后工具服务句柄为session 9767（仅供本聊天恢复定位，不能凭此文本假定进程仍活着）；启动日志PID16000。重启前确认真实状态，数据库保存下一次追踪时间与租约。第一份追踪记录早于trigger_kind字段，迁移后为unspecified；新记录会明确区分scheduled/manual，不回填历史触发类型。

ZIP在checkpoints，LATEST.json含SHA256；不含密钥、数据库、原PDF、OCR权重、venv或Git，源码/结果可恢复。原PDF仍在工作目录data/papers和data/library，重建按README。Git保留真实提交，未添加remote。

检索在新论文验证后冻结。若连续两轮无明显收益，转向新数据/真实模型/官方解析用例，不重复同一实验制造工作量。
