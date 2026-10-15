# 下一步与恢复入口（晨间最新交付）

截至约07:45：89项完整测试通过，21份真实PDF/20家族/71边；两次真实追踪及预算停用、20精确版本公共元数据、71条锚点完整性与7条原页修复回归、隔离离线重建均已完成。10页PDF已全部渲染检查。先读MORNING_REPORT、RUN_LOG和reports/evidence_manifest.json。

约02:40至07:39一次浏览器导出验证调用异常等待约299.5分钟，没有新增研发产出。SVG最终已实际下载并验证20节点/9条RAG邻接边/20项图例。原因未确诊；后续下载等待应设置短超时，不继续无界等待。总墙钟不等于有效工时。

## 当前优先三件事
1. **真实模型与最高权重效果**：需要已授权端点、模型及费用/次数预算。11434/1234此前不可用，无凭据。先小规模真实规划→工具→证据回答/翻译，保存失败和成本，再比较直接LLM/检索LLM/完整工作流。Mock协议不等于真实效果；不无预算启用商业接口或下载大权重。
2. **官方难例与独立标注**：取得官方扫描PDF/资料包哈希，补复杂公式表格、专业翻译/非数字引文、Dense与语义蕴含。8表18格、7条新增引用均为修复回归，不能充当独立盲测。另建新金标；不对现有holdout继续调参。
3. **提交闭环**：选手理解并复现代码，核对学校/组别/许可，明确评审仓库和公网资源，再补认证/预算/正式视频。Docker未运行，未推送/部署/赛事提交。10页PDF是研发稿，不宣称正式作品完成或获奖水平。

## 已完成的事项，不要按下方旧历史重做
- 追踪01:55:39与02:26:07已两次成功，第二条scheduled，达到2次预算停用。不要再创建/续费次数；第一条unspecified不回填。30分钟实验不代表长期稳定性。
- 图谱扩展与交互完成20家族/71边，RAG聚焦9条；当前缺完整独立金标/引用质量过滤、真实LLM综述和Future Work后续解决判定，而非缺20篇样例。
- 锁定21份原PDF共48,165,754字节，SHA256全通过；隔离库离线重建21身份/20节点/71边锚点与排名一致，6.69秒、零联网、原库不改。这不是新机器安装/公网重下载验收。
- scripts/replay_library_sources.py默认只读，--download-missing才会访问锁定来源；哈希不符不覆盖。scripts/expand_references.py在现有库会选择新候选，不用于同库复现。完整命令见README。

## 当前恢复命令与服务
```powershell
# 先确认8000是否仍运行，避免重复启动
.venv/Scripts/python.exe -m uvicorn src.app:app --host 127.0.0.1 --port 8000
.venv/Scripts/python.exe scripts/run_tests.py
.venv/Scripts/python.exe scripts/replay_library_sources.py
.venv/Scripts/python.exe scripts/rebuild_library_probe.py
.venv/Scripts/python.exe scripts/phase3_live_probe.py
.venv/Scripts/python.exe scripts/tracking_probe.py
```
最后确认服务session1315、PID31012，约02:33启动，07:40只读HTTP正常；文字不是进程存活证明。只监听127.0.0.1:8000。报告生成额外需要requirements-report.txt与中文字体，本机依赖在捆绑宿主Python而非项目venv。

ZIP见checkpoints/LATEST.json，含SHA256/逐文件清单，不含密钥、原PDF、数据库、OCR权重、venv或Git。原PDF保留于data/papers和data/library；来源锁和保存Atom随源码。Git只保留真实本地历史，无remote。

---
# 第二阶段历史记录（下列旧状态已过期，仅保留过程；以上当前状态优先）

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
