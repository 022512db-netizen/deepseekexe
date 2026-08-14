# DeepSeekExe

DeepSeek 独立桌面 App(类似 Codex 的独立运行形态)——把 DeepSeek 代理的网页界面直接嵌进原生窗口,不用打开浏览器。

## 功能

1. **独立窗口运行** — 用 pywebview(Edge WebView2)内嵌 dsh web 界面,UI 与功能跟网页版完全一致;引擎随 App 启动,关闭窗口即自动停止内部服务器
2. **保存并推送** — 菜单「文件 → 保存并推送」(或手动触发),把以下内容 commit 并 push 到远程仓库:
   - 会话记录(`%USERPROFILE%\.dsh\sessions` → 本仓库 `sessions/` 目录)
   - 工作目录中的全部文件

## 目录结构

```
deepseek/
├── DeepSeekExe.py     # 应用源码(Python 3 + pywebview)
├── sessions/          # 会话记录镜像(保存时自动同步)
├── dist/              # 打包产物 DeepSeekExe.exe(不提交到仓库)
└── .gitignore
```

## 使用方式

### 方式一:运行源码

```powershell
python DeepSeekExe.py
```

### 方式二:运行打包好的 exe

双击 `dist\DeepSeekExe.exe` 即可(单文件,无控制台窗口)。

### 保存并推送

在 App 菜单「文件 → 保存并推送」,执行:

1. 把会话记录同步到 `sessions/` 目录
2. 检查/初始化 git 仓库
3. 提交全部改动(提交信息:自动保存 <时间>)
4. 推送到 `https://github.com/022512db-netizen/deepseekexe.git` 的 `main` 分支
5. 弹出提示框显示结果

## 重新打包

```powershell
python -m PyInstaller --onefile --windowed --name DeepSeekExe ^
  --collect-all webview --collect-all pythonnet --collect-all clr_loader ^
  --distpath dist --workpath build --specpath . DeepSeekExe.py
```

产物在 `dist\DeepSeekExe.exe`。

## 依赖

- `dsh`(`@deepseek-ai/dsh`,引擎,随 App 内嵌启动)
- `git` + GitHub 凭据(`git config --global credential.helper store`)
- Python 3.8+ 与 `pywebview`(仅运行源码时需要;exe 不需要)
- Windows 10/11 自带 Edge WebView2 运行时(Windows 11 已内置)

## 配置

修改 `DeepSeekExe.py` 顶部「配置区」即可调整:

| 配置项 | 默认值 | 说明 |
|---|---|---|
| `WORKSPACE` | `C:\Users\asus\Desktop\deepseek` | 工作目录 = 本地 git 仓库 |
| `REMOTE_URL` | `https://github.com/022512db-netizen/deepseekexe.git` | 远程仓库地址 |
| `PORT` | `3080` | 内嵌服务器端口(可用环境变量 `DSHEXE_PORT` 覆盖) |
| `BRANCH` | `main` | 推送分支 |
