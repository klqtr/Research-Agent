# ResearchTrace Git 与运行指南

用户指定仓库：https://github.com/klqtr/Research-Assistant-Agent

Git 保存本地版本；GitHub 保存上传后的远程版本。网站服务与 GitHub 仓库分别运行，上传代码不会自动部署 Python 网站。

## 本次历史合并

保留本地六次开发提交 ade3312、e170801、1944a72、50428c5、d008162、d0c594e，以及用户仓库的初始化提交 ae3d31e。通过合并提交连接历史，不强推、不删除旧提交、不伪造时间。README 保留完整项目说明，.gitignore 合并双方规则，保留远程 MIT LICENSE；第三方依赖和论文许可单独适用。

## 后续正常开发

在项目根目录打开 PowerShell。先查看改动，再只暂存本次需要提交的文件：

```powershell
git status
git diff
git add README.md src/本次修改的文件.py
git commit -m "说明本次具体修改和目的"
git push origin HEAD:main
```

示例文件名须替换为真实路径。每次有意义的修改并通过必要检查后提交，不需要为凑数量提交。首次配置个人作者信息时，在本仓库使用 `git config user.name` 和 `git config user.email` 设置自己的姓名和 GitHub 隐私邮箱；不要把示例邮箱当作个人账号。既有 AI 辅助开发署名保留。

查看真实记录：`git log --graph --oneline --all`。比较同步状态先运行 `git fetch origin`，再运行 `git log --oneline origin/main..HEAD`（待上传）与 `git log --oneline HEAD..origin/main`（远程新增）。不要使用强制推送覆盖他人提交。

.env、数据库、原始论文、虚拟环境、OCR 数据与本地服务日志不上传。环境模板 .env.example 保留。上传前检查暂存内容，不在聊天或提交中填写 API 密钥。历史中的敏感信息无法仅靠后续删除清除。

## 打开网站

本机已有虚拟环境时，在项目目录运行：

```powershell
.\.venv\Scripts\python.exe -m uvicorn src.app:app --host 127.0.0.1 --port 8000
```

看到 `Uvicorn running` 后打开 http://127.0.0.1:8000 。该终端保持运行，Ctrl+C 停止；电脑重启后重新启动。其他电脑不能使用你的 127.0.0.1 地址访问。当前服务仅供本机使用，公开部署尚未完成。

服务健康检查：http://127.0.0.1:8000/api/health 。`model_enabled=false` 表示未启用真实模型，并非网站运行失败。真实模型仍需授权端点、密钥和调用预算。
