---
name: claude-vision-skill
description: 当用户分享、粘贴或引用图片（本地路径、URL 或剪贴板）且当前模型需要识图、描述、分析或识别图片内容时使用。运行随附 vision.js，将图片交给用户配置的视觉模型并返回中文文字结果。
---

# Vision Helper

当前模型可能不具备原生识图能力。用户提供图片时，使用本 skill 将图片转换为文字描述。

## 默认方式：子代理识图（推荐）

当「识图模式」为默认的「子代理」时，当前模型不要自行运行脚本，而是：

1. 创建一个子代理（subagent）。
2. 让子代理执行以下命令之一：
   - 剪贴板图片：`node "$env:USERPROFILE\.dsh\skills\claude-vision-skill\vision.js" --clipboard "请用中文详细描述这张图片"`
   - 本地图片：`node "$env:USERPROFILE\.dsh\skills\claude-vision-skill\vision.js" "C:\absolute\image.png" "请详细描述这张图片"`
   - 图片 URL：`node "$env:USERPROFILE\.dsh\skills\claude-vision-skill\vision.js" --url "https://example.com/image.png" "请分析图片内容"`
3. 子代理返回视觉模型的中文描述后，当前模型再基于描述继续回答。

## 直接脚本方式

当「识图模式」为「直接脚本」时，当前模型可直接运行 vision.js（命令同上），不再额外创建子代理。

## 识图模式设置

- 在 App 菜单「文件 → 识图模式设置」中切换：子代理（默认）/ 直接脚本 / 关闭。
- 设置保存在 `%USERPROFILE%\.dsh\settings.yaml` 的 `image-recognition.mode`。
- 「关闭」时忽略图片，仅继续纯文本对话。

## 通用规则

- 用户给出图片路径、URL 或粘贴图片时，优先调用本 skill。
- 本地文件使用绝对路径；远程图片使用 `--url`。
- 没有可用路径时使用 `--clipboard`；剪贴板读取失败时请用户保存图片并给出路径。
- 默认用中文输出；按用户问题调整识别或分析重点。
- 配置位于同目录 `.env`，不要输出、回显或提交 API Key。
- 如果调用失败，报告简短错误并提醒用户检查视觉模型配置。
