# DeepSeekExe

DeepSeek 代理独立启动器(Windows 桌面应用)。

## 功能

1. **🚀 启动 DeepSeek** — 一键启动 `dsh web` 代理引擎,自动打开浏览器访问网页版界面
2. **💾 保存并推送到 GitHub** — 手动触发,将以下内容 commit 并 push 到远程仓库:
   - 会话记录(`%USERPROFILE%\.dsh\sessions` → 本仓库 `sessions/` 目录)
   - 工作目录中的全部文件

## 目录结构

```
deepseek/
├── DeepSeekExe.py     # 应用源码(Python 3 + tkinter)
├── sessions/          # 会话记录镜像(由"保存并推送"自动同步)
├── dist/              # 打包产物 DeepSeekExe.exe(不提交到仓库)
└── .gitignore
```

## 使用方式

### 方式一:直接运行源码

```powershell
python DeepSeekExe.py
```

### 方式二:运行打包好的 exe

双击 `dist\DeepSeekExe.exe` 即可。

### 保存并推送

点击「保存并推送到 GitHub」按钮,应用会:

1. 把会话记录同步到 `sessions/` 目录
2. 检查/初始化 git 仓库
3. 提交全部改动(提交信息:自动保存 <时间>)
4. 推送到 `https://github.com/022512db-netizen/deepseekexe.git` 的 `main` 分支

## 重新打包

```powershell
pip install pyinstaller
pyinstaller --onefile --windowed --name DeepSeekExe DeepSeekExe.py
```

产物在 `dist\DeepSeekExe.exe`。

## 依赖

- 本机已安装 `dsh`(`@deepseek-ai/dsh`,用于启动引擎)
- 本机已安装 `git`,并配置了 GitHub 凭据(`git config --global credential.helper store`)
- Python 3.8+ 与 tkinter(仅运行源码时需要;exe 不需要)

## 配置

修改 `DeepSeekExe.py` 顶部「配置区」即可调整:

| 配置项 | 默认值 | 说明 |
|---|---|---|
| `WORKSPACE` | `C:\Users\asus\Desktop\deepseek` | 工作目录 = 本地 git 仓库 |
| `REMOTE_URL` | `https://github.com/022512db-netizen/deepseekexe.git` | 远程仓库地址 |
| `WEB_URL` | `http://127.0.0.1:3080` | 网页界面地址 |
| `BRANCH` | `main` | 推送分支 |
