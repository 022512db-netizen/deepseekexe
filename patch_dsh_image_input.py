#!/usr/bin/env python3
"""Patch a DSH DeepSeek adapter for mode-aware image fallback workflows.

Injected instruction is chosen by `image-recognition.mode` in $DSH_HOME/settings.yaml:
  subagent (default) -> delegate recognition to a subagent running vision.js
  direct             -> run vision.js directly
  off                -> drop the image without recognition
Usage:
  python patch_dsh_image_input.py [portable_dir]      (patch portable runtime)
  python patch_dsh_image_input.py --target <file.js>  (patch an arbitrary runtime)
"""

import re
import sys
from pathlib import Path

RELATIVE_ADAPTER = Path("runtime/dsh/node_modules/@deepseek-ai/dsh-llm-deepseek/lib/index.js")
BANNER = "// DeepSeekExe mode-aware Vision Skill fallback.\n"

IMPORTS_ANCHOR = 'import z from "@deepseek-ai/schemastery";'
IMPORTS_ADD = ('import fs from "node:fs";\n'
               'import os from "node:os";\n'
               'import path from "node:path";\n')

HELPER = '''function imageRecognitionMode() {
\tconst settingsPath = path.join(process.env.DSH_HOME || path.join(os.homedir(), ".dsh"), "settings.yaml");
\ttry {
\t\tconst text = fs.readFileSync(settingsPath, "utf8");
\t\tconst match = text.match(/^image-recognition:\\s*\\n\\s*mode:\\s*([A-Za-z]+)/m);
\t\tconst mode = match ? match[1] : "subagent";
\t\treturn mode === "direct" || mode === "off" ? mode : "subagent";
\t} catch {
\t\treturn "subagent";
\t}
}'''

NEW_FLATTEN = '''function flattenText(blocks) {
\tconst text = blocks.filter((block) => block.type === "text").map((block) => block.text).join("");
\tif (!contentHasImage(blocks)) return text;
\tconst mode = imageRecognitionMode();
\tif (mode === "off") return `${text}\\n\\n[用户附加了一张图片，但识图模式已关闭，忽略该图片。]`;
\tif (mode === "direct") return `${text}\\n\\n[用户附加了一张图片。当前 DeepSeek 路由不原生识图（识图模式：直接脚本）。请直接运行全局 claude-vision-skill 的 vision.js --clipboard 获取图片的中文描述，再基于描述回答。]`;
\treturn `${text}\\n\\n[用户附加了一张图片。当前 DeepSeek 路由不原生识图（识图模式：子代理，默认）。请创建一个子代理(subagent)执行全局 claude-vision-skill 的 vision.js --clipboard 获取图片的中文描述，子代理返回结果后你再基于描述继续回答。]`;
}'''

NEW_ASSERT = '''function assertTextOnly(_blocks) {
\t// DeepSeekExe mode-aware fallback: attachment bytes remain durable.
}'''

FLATTEN_RE = re.compile(r"function flattenText\(blocks\) \{[\s\S]*?\n\}")
ASSERT_RE = re.compile(r"function assertTextOnly\(_?blocks\) \{[\s\S]*?\n\}")


def apply_patch(target: Path):
    content = target.read_text(encoding="utf-8")
    if "DeepSeekExe mode-aware Vision Skill fallback" in content:
        print("Already mode-aware patched: %s" % target)
        return
    if IMPORTS_ANCHOR in content and 'import fs from "node:fs";' not in content:
        content = content.replace(IMPORTS_ANCHOR, IMPORTS_ADD + IMPORTS_ANCHOR, 1)
    if "imageRecognitionMode" not in content:
        new_flatten = HELPER + "\n" + NEW_FLATTEN
        content, count = FLATTEN_RE.subn(lambda _match: new_flatten, content, count=1)
        if count != 1:
            raise RuntimeError("DSH adapter flattenText not found: %s" % target)
    content, count = ASSERT_RE.subn(lambda _match: NEW_ASSERT, content, count=1)
    if count != 1:
        raise RuntimeError("DSH adapter assertTextOnly not found: %s" % target)
    if 'inputModalities: ["text", "image"]' in content:
        pass  # already image-enabled
    elif content.count('inputModalities: ["text"]') >= 1:
        content = content.replace('inputModalities: ["text"]', 'inputModalities: ["text", "image"]')
    else:
        raise RuntimeError("Expected DeepSeek text-only modality declarations: %s" % target)
    if not content.startswith("// DeepSeekExe"):
        content = BANNER + content
    with open(target, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)
    print("Patched mode-aware image fallback: %s" % target)


def main():
    args = sys.argv[1:]
    if args and args[0] == "--target":
        apply_patch(Path(args[1]))
        return
    portable = Path(args[0]) if args else Path(r"C:\Users\asus\Desktop\DeepSeekExe-portable")
    apply_patch(portable / RELATIVE_ADAPTER)


if __name__ == "__main__":
    main()
