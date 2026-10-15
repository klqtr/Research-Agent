# 下一步
1. 修复Attention v7标题提取（首页最大水平字号，排除侧边arXiv与版权声明），增加真实回归。
2. 建立真实论文问答标注集，运行BM25/字符/融合/无配额消融及引用防护实验。
3. 启动本地Web并检查界面；完善OCR/长文鲁棒性、图谱/版本处理交互与端点。
4. 完成README、技术报告PDF、评审/演示材料、晨间报告，诚实列出六模块差距。
恢复命令：`.venv/Scripts/python.exe -m pytest -q`、`.venv/Scripts/python.exe scripts/import_papers.py`、`.venv/Scripts/python.exe -m uvicorn src.app:app --host 127.0.0.1 --port 8000`。
