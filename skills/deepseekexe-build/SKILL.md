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

### 1. 编译 exe

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_exe.ps1
```

### 2. 组装便携版

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_portable.ps1
```

(内部会自动先执行 build_exe.ps1)

### 3. 生成 zip(UTF-8 文件名安全)

```powershell
python scripts\build_zip.py
```

### 4. 验证(必做, 见 references\验证清单.md)

- 启动测试: 窗口出现 + 端口 3080 响应 + 优雅退出无残留进程
- 引擎来源: 确认 node 进程命令行指向 `runtime\` 而非系统路径
- zip 校验: exe 哈希一致、中文文件名 UTF-8 flag 正确

## 注意事项

- 打包前先结束残留的 DeepSeekExe 进程, 否则 `dist\DeepSeekExe.exe` 被占用导致失败(脚本已内置处理)
- 便携版更新: 目标机只需替换 `DeepSeekExe.exe`, `runtime\` 不用动
- 若 dsh 引擎升级, 需重新运行 build_portable.ps1 更新 `runtime\dsh\`
