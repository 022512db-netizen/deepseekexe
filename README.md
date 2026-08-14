# DeepSeekExe

DeepSeek 独立桌面 App(类似 Codex 的独立运行形态)——把 DeepSeek 代理的网页界面直接嵌进原生窗口,不用打开浏览器。

## 功能

1. **独立窗口运行** — 用 pywebview(Edge WebView2)内嵌 dsh web 界面,UI 与功能跟网页版完全一致;引擎随 App 启动,关闭窗口即自动停止内部服务器
2. **纯本地运行** — App 不联网、不上传任何数据;会话记录与 API Key 只保存在本机
3. **更新方式** — App 自身不更新;源码在本仓库维护,重新打包后分发(替换 `DeepSeekExe.exe` 即可)

> 🔒 **安全说明**:App 内**没有**推送/上传功能(历史版本曾有"保存并推送",因会话日志含密钥曾泄露,已移除)。

## 目录结构

```
deepseek/
├── DeepSeekExe.py       # 应用源码(Python 3 + pywebview)
├── build_portable.ps1   # 便携版构建脚本
├── assets/deepseek.ico  # 鲸鱼图标
├── dist/                # 打包产物 DeepSeekExe.exe(不提交到仓库)
└── .gitignore
```

## 便携版(可拷贝到其他电脑)

`build_portable.ps1` 生成 `C:\Users\asus\Desktop\DeepSeekExe-portable\`(约 350MB):

```
DeepSeekExe-portable/
├── DeepSeekExe.exe    # 双击运行
├── runtime/           # 内置 node + dsh 引擎(255MB)
└── 使用说明.txt
```

把整个文件夹拷到任何 Windows 10/11 电脑双击即用——**无需安装 Node.js、dsh、git**。
新版分发:替换 `DeepSeekExe.exe` 一个文件即可(runtime 不用动)。

## 使用方式

### 方式一:运行源码

```powershell
python DeepSeekExe.py
```

### 方式二:运行打包好的 exe

双击 `dist\DeepSeekExe.exe` 即可(单文件,无控制台窗口)。

## 重新打包

```powershell
# 单 exe
python -m PyInstaller --onefile --windowed --name DeepSeekExe ^
  --collect-all webview --collect-all pythonnet --collect-all clr_loader ^
  --icon assets\deepseek.ico --add-data "assets\deepseek.ico;assets" ^
  --distpath dist --workpath build --specpath . DeepSeekExe.py

# 便携版(打包 + 组装 runtime)
powershell -ExecutionPolicy Bypass -File build_portable.ps1
```

产物在 `dist\DeepSeekExe.exe`。图标使用官方 DeepSeek 鲸鱼(`assets\deepseek.ico`)。

## 依赖

- 便携模式:内置 `runtime/`(node + dsh),零外部依赖
- 源码模式:`dsh`(`@deepseek-ai/dsh`) + Python 3.8+ 与 `pywebview`
- Windows 10/11 自带 Edge WebView2 运行时(Windows 11 已内置)

## 配置

修改 `DeepSeekExe.py` 顶部「配置区」即可调整:

| 配置项 | 默认值 | 说明 |
|---|---|---|
| `WORKSPACE` | App 所在目录 | 工作区(可用环境变量 `DSHEXE_WORKSPACE` 覆盖) |
| `PORT` | `3080` | 内嵌服务器端口(可用环境变量 `DSHEXE_PORT` 覆盖) |
| `DSHEXE_DSH_ENTRY` | 自动查找 | 手动指定 dsh 的 lib/bin.js 路径 |
