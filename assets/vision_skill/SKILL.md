---
name: claude-vision-skill
description: 当用户分享、粘贴或引用图片（本地路径、URL 或剪贴板）且当前模型需要识图、描述、分析或识别图片内容时使用。运行随附 vision.js，将图片交给用户配置的视觉模型并返回中文文字结果。
---

# Vision Helper

当前模型可能不具备原生识图能力。用户提供图片时，使用本 skill 将图片转换为文字描述。

本地图片：

```powershell
node "$env:USERPROFILE\.dsh\skills\claude-vision-skill\vision.js" "C:\absolute\image.png" "请详细描述这张图片"
```

图片 URL：

```powershell
node "$env:USERPROFILE\.dsh\skills\claude-vision-skill\vision.js" --url "https://example.com/image.png" "请分析图片内容"
```

用户粘贴图片但没有可用路径时：

```powershell
node "$env:USERPROFILE\.dsh\skills\claude-vision-skill\vision.js" --clipboard "请用中文详细描述这张图片"
```

规则：

- 用户给出图片路径、URL 或粘贴图片时，优先调用本 skill。
- 本地文件使用绝对路径；远程图片使用 `--url`。
- 没有可用路径时使用 `--clipboard`；剪贴板读取失败时请用户保存图片并给出路径。
- 默认用中文输出；按用户问题调整识别或分析重点。
- 配置位于同目录 `.env`，不要输出、回显或提交 API Key。
- 如果调用失败，报告简短错误并提醒用户检查视觉模型配置。
