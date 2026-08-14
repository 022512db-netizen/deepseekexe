---
name: "deepseekexe-update"
description: "DeepSeekExe 应用更新流程: 修改源码、重新构建、分发新版本、安全红线。当需要给 DeepSeekExe 发布新版本时使用。"
---

# DeepSeekExe 更新流程

## 更新原则

- App 自身不联网更新；所有改动在开发机完成，重新打包后分发。
- 目标电脑更新：替换 `DeepSeekExe.exe`；引擎升级才需整体替换 `runtime\`。
- 本 skill 由使用者维护，修改流程后请同步更新 `references\` 下的清单。

## 更新步骤

1. 修改源码 `DeepSeekExe.py`
2. 使用 `deepseekexe-build` skill 重新构建 exe、便携版和 zip
3. 按 build skill 的验证清单检查
4. 分发新 exe 或 zip

## 安全红线

见 `references\安全红线.md`。
