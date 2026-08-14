---
name: "deepseekexe-update"
description: "DeepSeekExe 应用更新流程: 修改源码、重新构建、分发新版本、安全红线。当需要给 DeepSeekExe 发布新版本时使用。"
---

# DeepSeekExe 更新流程

## 更新原则

- App 自身**不联网更新**; 所有改动在开发机完成, 重新打包后分发
- 目标电脑更新: **替换 `DeepSeekExe.exe` 一个文件即可**; 引擎升级才需要整体替换 `runtime\`
- 本 skill 由使用者维护, 修改流程后请同步更新 references\ 下的清单

## 更新步骤

1. **修改源码**: 编辑 `C:\Users\asus\Desktop\deepseek\DeepSeekExe.py`
   - 功能变更 / 配置调整(端口、窗口大小、引擎查找等)
2. **重新构建**: 调用 `deepseekexe-build` skill
   - exe → 便携版 → zip(三步脚本)
3. **验证**: 按 build skill 的「验证清单」逐项检查
4. **分发**: 拷贝新 `DeepSeekExe.exe` 或整个 zip 给目标电脑, 说明替换方式
5. **记录**: 在 `references\更新记录.md` 追加版本说明(可选)

## 安全红线(必读, 曾因此泄露过密钥)

见 `references\安全红线.md`

## 常见修改点速查

| 想改什么 | 改哪里 |
|---|---|
| 端口 | `DeepSeekExe.py` 中 `PORT`(或环境变量 `DSHEXE_PORT`) |
| 窗口大小 | `WINDOW_W` / `WINDOW_H` |
| 图标 | `assets\deepseek.ico`(改后重新打包) |
| 工作区位置 | `WORKSPACE` 默认值(或环境变量 `DSHEXE_WORKSPACE`) |
| 引擎查找顺序 | `find_engine()` 函数 |
| 启动超时 | `START_TIMEOUT_SEC` |
