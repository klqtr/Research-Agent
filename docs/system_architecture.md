# 系统架构

```mermaid
flowchart LR
 UI[Web 工作台] --> API[HTTP API]
 API --> ING[文档导入与版本确认]
 API --> PAGE[按页结构分析与页图高亮]
 PAGE --> PCACHE[(版本化JSON缓存/原PDF)]
 ING --> PARSE[逐页 PDF 解析与可选 OCR]
 PARSE --> DB[(SQLite 文献/块/版本)]
 API --> AG[意图路由与工作流轨迹]
 AG --> RET[多文配额混合词汇检索]
 DB --> RET
 RET --> LLM[可选真实 LLM 接口]
 LLM --> CHECK[引用原文与结构校验]
 RET --> EX[无模型抽取式证据]
 AG --> TOOLS[检索 API/图谱/CSV统计/写作]
 DB --> TOOLS
 CHECK --> UI
 EX --> UI
 TOOLS --> UI
 UI --> WATCH[显式追踪配置]
 WATCH --> DB
 SCHED[有界调度/租约/限额] --> DB
 SCHED --> ARXIV[公开arXiv元数据]
 ARXIV --> SNAP[(真实快照/版本去重/错误历史)]
 SNAP --> UI
```

数据与模型提示不具有工具权限；工具为白名单。PDF 原文保留，块含 page/bbox/标题信息。用户明确确认版本处理。模型密钥只来自环境变量，不进数据库和客户端。完整实现范围以 README 与验收矩阵为准。

第二阶段加入原生目录层级与按页表格候选、图注/图片/数学glyph索引；表格分析按需运行，缓存带源哈希和分析器版本，不把整页正文当表格。合并单元格/LaTeX未完整解决。追踪创建默认停用，每项最多48次，空列表无网络请求；真实模型不会由追踪器自动调用。
