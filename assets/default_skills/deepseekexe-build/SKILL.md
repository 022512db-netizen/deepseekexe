---
name: "deepseekexe-build"
description: "构建打包 DeepSeekExe 桌面应用: 编译 exe、组装便携版(内置 node+dsh 引擎)、生成 UTF-8 安全的 zip 分发包。当需要重新打包 DeepSeekExe 或制作分发版本时使用。"
---

# DeepSeekExe 构建打包

## 前置条件(必须在开发机上执行)

- 源码目录: `C:\Users\asus\Desktop\deepseek`(可用 `-Workspace` 参数覆盖)
- Python 3.8+ 及 pyinstaller、pywebview、zstandard 等依赖
- Node.js(便携版引擎拷贝用)
- dsh 引擎已在 npx 缓存中安装

## 三个产物

| 产物 | 位置 | 说明 |
|---|---|---|
| 单 exe | `deepseek\dist\DeepSeekExe.exe` | 目标机替换这一个文件即完成更新 |
| 便携文件夹 | `C:\Users\asus\Desktop\DeepSeekExe-portable\` | 免安装运行(含 runtime 约 255MB) |
| zip 分发包 | `C:\Users\asus\Desktop\DeepSeekExe-portable.zip` | 拷贝分发用 |

## 构建步骤

1. `powershell -ExecutionPolicy Bypass -File scripts\build_exe.ps1`
2. `powershell -ExecutionPolicy Bypass -File scripts\build_portable.ps1`
3. `python scripts\build_zip.py`

详见 `references\验证清单.md`。

## 注意事项

- 打包前先结束残留的 DeepSeekExe 进程。
- 目标机更新通常只需替换 `DeepSeekExe.exe`；引擎升级才需更新 `runtime\`。
