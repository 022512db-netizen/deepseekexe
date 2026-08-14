#!/usr/bin/env python3
"""Patch a bundled DSH DeepSeek adapter for attachment-aware fallback workflows."""

import sys
from pathlib import Path

RELATIVE_ADAPTER = Path("runtime/dsh/node_modules/@deepseek-ai/dsh-llm-deepseek/lib/index.js")
OLD_ASSERT = '''function assertTextOnly(blocks) {
\tif (contentHasImage(blocks)) throw new LlmError("The DeepSeek chat-completions adapter does not support image content.", "UNSUPPORTED_CONTENT");
}'''
NEW_ASSERT = '''function assertTextOnly(_blocks) {
\t// Image bytes remain in the durable attachment store. The text-only DeepSeek
\t// route receives a Vision Skill fallback instruction from flattenText below.
}'''
OLD_FLATTEN = '''function flattenText(blocks) {
\treturn blocks.filter((block) => block.type === "text").map((block) => block.text).join("");
}'''
NEW_FLATTEN = '''function flattenText(blocks) {
\tconst text = blocks.filter((block) => block.type === "text").map((block) => block.text).join("");
\tif (!contentHasImage(blocks)) return text;
\treturn `${text}\\n\\n[用户附加了一张图片。当前 DeepSeek 路由不原生识图。请调用全局 claude-vision-skill 的 vision.js --clipboard 获取图片的中文描述，再基于描述回答。]`;
}'''


def replace_once(content, old, new, label):
    if old not in content:
        raise RuntimeError("DSH adapter patch point not found: %s" % label)
    return content.replace(old, new, 1)


def main():
    portable = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:\Users\asus\Desktop\DeepSeekExe-portable")
    target = portable / RELATIVE_ADAPTER
    if not target.is_file():
        raise FileNotFoundError("Bundled DSH adapter not found: %s" % target)
    content = target.read_text(encoding="utf-8")
    if "DeepSeekExe Vision Skill fallback" in content:
        print("DSH image fallback patch already applied")
        return
    content = replace_once(content, OLD_FLATTEN, NEW_FLATTEN, "flattenText")
    content = replace_once(content, OLD_ASSERT, NEW_ASSERT, "image rejection")
    if content.count('inputModalities: ["text"]') != 2:
        raise RuntimeError("Expected two DeepSeek text-only modality declarations")
    content = content.replace('inputModalities: ["text"]', 'inputModalities: ["text", "image"]')
    banner = "// DeepSeekExe Vision Skill fallback: attachment-aware text route.\n"
    with open(target, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(banner + content)
    print("Patched bundled DSH image fallback: %s" % target)


if __name__ == "__main__":
    main()
