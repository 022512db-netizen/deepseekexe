#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DeepSeekExe - embedded DSH desktop application with image fallback setup."""

import html
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

import webview


def _app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


APP_DIR = _app_dir()
WORKSPACE = os.environ.get("DSHEXE_WORKSPACE") or APP_DIR
PORT = int(os.environ.get("DSHEXE_PORT", "3080"))
WEB_URL = "http://127.0.0.1:%d" % PORT
START_TIMEOUT_SEC = 90
WINDOW_W, WINDOW_H = 1280, 860
ICON_PATH = resource_path(os.path.join("assets", "deepseek.ico"))
VISION_SOURCE = resource_path(os.path.join("assets", "vision_skill"))
DEFAULT_SKILLS_SOURCE = resource_path(os.path.join("assets", "default_skills"))
DSH_HOME = os.environ.get("DSH_HOME") or os.path.join(os.path.expanduser("~"), ".dsh")
DSH_SKILLS_HOME = os.path.join(DSH_HOME, "skills")
VISION_HOME = os.path.join(DSH_SKILLS_HOME, "claude-vision-skill")
MAX_SKILL_ARCHIVE_BYTES = 20 * 1024 * 1024
MAX_SKILL_FILES = 200
MAX_SKILL_UNPACKED_BYTES = 50 * 1024 * 1024

SPLASH_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
body{margin:0;height:100vh;display:flex;align-items:center;justify-content:center;background:#1a1a2e;color:#eee;font-family:"Microsoft YaHei",sans-serif}
.box{text-align:center}.spin{width:44px;height:44px;border:5px solid #333;border-top-color:#4CAF50;border-radius:50%;margin:0 auto 18px;animation:r 1s linear infinite}@keyframes r{to{transform:rotate(360deg)}}</style></head><body><div class="box"><div class="spin"></div><h2>正在启动 DeepSeek 引擎...</h2></div></body></html>"""

VISION_CONFIG_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
body{font:14px "Microsoft YaHei",sans-serif;margin:0;background:#f6f7fb;color:#202535}.wrap{padding:24px;max-width:540px}.note{line-height:1.55;color:#5c6478;margin:0 0 18px}label{display:block;font-weight:600;margin:14px 0 6px}input{width:100%;box-sizing:border-box;padding:10px;border:1px solid #c8cede;border-radius:5px;font:14px Consolas,"Microsoft YaHei",sans-serif}button{margin-top:20px;background:#315efb;color:#fff;border:0;border-radius:5px;padding:10px 18px;font:14px "Microsoft YaHei",sans-serif;cursor:pointer}.status{height:20px;color:#b42318;margin-top:12px}.hint{font-size:12px;color:#72798b;margin-top:5px}</style></head><body><div class="wrap"><h2>配置视觉模型</h2><p class="note">图片已允许附加。非视觉模型会使用全局 Vision Skill 识图。请填写一个支持 OpenAI 兼容图片输入的模型和 API Key；信息仅保存在本机。</p><label>API Base URL</label><input id="base" value="https://jojocode.com/v1" placeholder="https://api.example.com/v1"><label>视觉模型</label><input id="model" value="gpt-5.6-terra" placeholder="例如 gpt-5.6-terra"><div class="hint">默认是已接入的 gpt-5.6-terra；可按自己的视觉服务改为其他模型。</div><label>API Key</label><input id="key" type="password" autocomplete="off" placeholder="输入视觉模型的 API Key"><button onclick="save()">保存视觉配置</button><div id="status" class="status"></div></div><script>async function save(){const status=document.getElementById('status');status.textContent='';const r=await window.pywebview.api.save_vision_config(document.getElementById('base').value,document.getElementById('model').value,document.getElementById('key').value);if(r.ok){status.style.color='#087443';status.textContent='已保存。现在可以关闭本窗口。'}else{status.style.color='#b42318';status.textContent=r.error;}}</script></body></html>"""

IMAGE_MODE_CONFIG_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
body{font:14px "Microsoft YaHei",sans-serif;margin:0;background:#f6f7fb;color:#202535}.wrap{padding:24px;max-width:560px}.note{line-height:1.6;color:#5c6478;margin:0 0 18px}.opt{display:flex;gap:10px;align-items:flex-start;margin:14px 0;padding:12px;border:1px solid #dfe3ec;border-radius:8px;background:#fff;cursor:pointer}.opt input{margin-top:3px}.opt b{display:block}.opt small{color:#72798b;display:block;margin-top:3px;line-height:1.5}button{margin-top:20px;background:#315efb;color:#fff;border:0;border-radius:5px;padding:10px 18px;font:14px "Microsoft YaHei",sans-serif;cursor:pointer}.status{height:20px;margin-top:12px}</style></head><body><div class="wrap"><h2>识图模式</h2><p class="note">当使用不支持图片输入的模型时，如何处理用户附加的图片。默认「子代理识图」。</p><label class="opt"><input type="radio" name="mode" value="subagent" checked><span><b>子代理识图（默认）</b><small>自动创建子代理调用 vision.js 识图，把图片转换成文字描述后再由当前模型继续回答。适合无视觉能力的模型。</small></span></label><label class="opt"><input type="radio" name="mode" value="direct"><span><b>直接脚本识图</b><small>模型直接运行全局 claude-vision-skill 的 vision.js 识图，不再额外创建子代理。</small></span></label><label class="opt"><input type="radio" name="mode" value="off"><span><b>关闭识图</b><small>忽略附加的图片，仅继续纯文本对话。</small></span></label><button onclick="save()">保存设置</button><div id="status" class="status"></div></div><script>async function init(){const r=await window.pywebview.api.get_image_mode();if(r&&r.mode){document.querySelectorAll('input[name=mode]').forEach(el=>{el.checked=el.value===r.mode;});}}async function save(){const status=document.getElementById('status');status.textContent='';const mode=document.querySelector('input[name=mode]:checked').value;const r=await window.pywebview.api.save_image_mode(mode);if(r.ok){status.style.color='#087443';status.textContent='已保存：'+({subagent:'子代理识图（默认）',direct:'直接脚本识图',off:'关闭识图'}[mode]);}else{status.style.color='#b42318';status.textContent=r.error;}}init();</script></body></html>"""


def find_engine():
    p_node = os.path.join(APP_DIR, "runtime", "node.exe")
    p_dsh = os.path.join(APP_DIR, "runtime", "dsh", "node_modules", "@deepseek-ai", "dsh", "lib", "bin.js")
    if os.path.isfile(p_node) and os.path.isfile(p_dsh):
        return p_node, p_dsh
    env_entry = os.environ.get("DSHEXE_DSH_ENTRY")
    if env_entry and os.path.isfile(env_entry):
        return shutil.which("node") or "node", env_entry
    import glob
    npx_hits = glob.glob(os.path.join(os.path.expanduser("~"), "AppData", "Local", "npm-cache", "_npx", "*", "node_modules", "@deepseek-ai", "dsh", "lib", "bin.js"))
    if npx_hits:
        return shutil.which("node") or "node", npx_hits[0]
    dsh_cmd = shutil.which("dsh")
    return (shutil.which("node") or "node", dsh_cmd) if dsh_cmd else (None, None)


NODE_BIN, DSH_ENTRY = find_engine()


class VisionConfigApi:
    def __init__(self, app):
        self.app = app

    def save_vision_config(self, base_url, model, api_key):
        base_url, model, api_key = base_url.strip(), model.strip(), api_key.strip()
        if not base_url.startswith(("https://", "http://")):
            return {"ok": False, "error": "API Base URL 必须以 http:// 或 https:// 开头。"}
        if not model:
            return {"ok": False, "error": "请填写视觉模型名称。"}
        if not api_key:
            return {"ok": False, "error": "请填写视觉模型 API Key。"}
        self.app.write_vision_config(base_url, model, api_key)
        return {"ok": True}


class ImageModeApi:
    def __init__(self, app):
        self.app = app

    def get_image_mode(self):
        return {"mode": self.app.read_image_mode()}

    def save_image_mode(self, mode):
        mode = mode.strip().lower()
        if mode not in ("subagent", "direct", "off"):
            return {"ok": False, "error": "无效的识图模式。"}
        self.app.write_image_mode(mode)
        return {"ok": True}


class DeepSeekApp:
    def __init__(self):
        self.window = None
        self.server_proc = None
        self.started_by_us = False
        self.vision_window = None
        self.image_mode_window = None

    def ensure_vision_skill(self):
        os.makedirs(VISION_HOME, exist_ok=True)
        for name in ("SKILL.md", "vision.js", "clipboard.ps1"):
            source = os.path.join(VISION_SOURCE, name)
            target = os.path.join(VISION_HOME, name)
            if os.path.isfile(source) and not os.path.isfile(target):
                shutil.copy2(source, target)
        gitignore = os.path.join(VISION_HOME, ".gitignore")
        with open(gitignore, "w", encoding="utf-8") as handle:
            handle.write(".env\nnode_modules/\npackage.json\npackage-lock.json\n")
        example = os.path.join(VISION_HOME, ".env.example")
        if not os.path.isfile(example):
            with open(example, "w", encoding="utf-8") as handle:
                handle.write("VISION_BASE_URL=https://jojocode.com/v1\nVISION_MODEL=gpt-5.6-terra\nVISION_API_KEY=replace-with-your-key\n")

    def ensure_default_skills(self):
        """Install bundled build/update skills once without overwriting user edits."""
        for skill_name in ("deepseekexe-build", "deepseekexe-update"):
            source_root = os.path.join(DEFAULT_SKILLS_SOURCE, skill_name)
            target_root = os.path.join(DSH_SKILLS_HOME, skill_name)
            if not os.path.isdir(source_root):
                continue
            for root, _dirs, files in os.walk(source_root):
                relative = os.path.relpath(root, source_root)
                target_dir = target_root if relative == "." else os.path.join(target_root, relative)
                os.makedirs(target_dir, exist_ok=True)
                for name in files:
                    source = os.path.join(root, name)
                    target = os.path.join(target_dir, name)
                    if not os.path.isfile(target):
                        shutil.copy2(source, target)

    def vision_configured(self):
        env_path = os.path.join(VISION_HOME, ".env")
        if not os.path.isfile(env_path):
            return False
        try:
            values = dict(line.split("=", 1) for line in open(env_path, encoding="utf-8") if "=" in line)
            return bool(values.get("VISION_BASE_URL", "").strip() and values.get("VISION_MODEL", "").strip() and values.get("VISION_API_KEY", "").strip())
        except OSError:
            return False

    def write_vision_config(self, base_url, model, api_key):
        self.ensure_vision_skill()
        env_path = os.path.join(VISION_HOME, ".env")
        content = "VISION_BASE_URL=%s\nVISION_MODEL=%s\nVISION_API_KEY=%s\n" % (base_url, model, api_key)
        with open(env_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)

    def open_vision_config(self):
        if self.vision_window is not None:
            self.vision_window.show()
            self.vision_window.restore()
            return
        self.vision_window = webview.create_window("DeepSeekExe - 视觉模型配置", html=VISION_CONFIG_HTML, js_api=VisionConfigApi(self), width=610, height=480, resizable=False)
        self.vision_window.events.closed += lambda: setattr(self, "vision_window", None)

    def read_image_mode(self):
        settings_path = os.path.join(DSH_HOME, "settings.yaml")
        try:
            text = open(settings_path, encoding="utf-8").read()
            match = None
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith("mode:"):
                    match = stripped.split(":", 1)[1].strip().strip("'\"")
                    break
            if match in ("direct", "off"):
                return match
            return "subagent"
        except OSError:
            return "subagent"

    def write_image_mode(self, mode):
        settings_path = os.path.join(DSH_HOME, "settings.yaml")
        os.makedirs(DSH_HOME, exist_ok=True)
        text = open(settings_path, encoding="utf-8").read() if os.path.isfile(settings_path) else ""
        if "image-recognition:" in text:
            lines = text.splitlines(True)
            out = []
            in_section = False
            for line in lines:
                if line.strip().startswith("image-recognition:"):
                    in_section = True
                    out.append("image-recognition:\n")
                    continue
                if in_section:
                    if line.strip() and not line.startswith((" ", "\t")):
                        in_section = False
                    else:
                        if line.strip().startswith("mode:"):
                            out.append("  mode: %s\n" % mode)
                            continue
                        if line.strip():
                            continue
                        out.append(line)
                        continue
                out.append(line)
            text = "".join(out)
        else:
            if text and not text.endswith("\n"):
                text += "\n"
            text += "image-recognition:\n  mode: %s\n" % mode
        with open(settings_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)

    def open_image_mode_config(self):
        if self.image_mode_window is not None:
            self.image_mode_window.show()
            self.image_mode_window.restore()
            return
        self.image_mode_window = webview.create_window("DeepSeekExe - 识图模式", html=IMAGE_MODE_CONFIG_HTML, js_api=ImageModeApi(self), width=620, height=430, resizable=False)
        self.image_mode_window.events.closed += lambda: setattr(self, "image_mode_window", None)

    def import_skill_zip(self):
        selected = self.window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False, file_types=("Skill ZIP (*.zip)", "All files (*.*)"))
        if not selected:
            return
        try:
            skill_name = self._install_skill_archive(selected[0])
            self.window.create_confirmation_dialog("Skill 导入完成", "已导入 Skill：%s\n新建对话后即可使用。" % skill_name)
        except (OSError, ValueError, zipfile.BadZipFile) as error:
            self.window.create_confirmation_dialog("Skill 导入失败", str(error))

    def _install_skill_archive(self, archive_path):
        if not archive_path.lower().endswith(".zip"):
            raise ValueError("请选择 .zip 格式的 Skill 包。")
        if os.path.getsize(archive_path) > MAX_SKILL_ARCHIVE_BYTES:
            raise ValueError("Skill ZIP 不能超过 20 MB。")
        with zipfile.ZipFile(archive_path) as archive:
            entries = [entry for entry in archive.infolist() if not entry.is_dir()]
            if not entries:
                raise ValueError("ZIP 中没有文件。")
            if len(entries) > MAX_SKILL_FILES:
                raise ValueError("Skill ZIP 包含过多文件。")
            if sum(entry.file_size for entry in entries) > MAX_SKILL_UNPACKED_BYTES:
                raise ValueError("Skill 解压后不能超过 50 MB。")
            paths = []
            for entry in entries:
                normalized = entry.filename.replace("\\", "/").strip("/")
                parts = normalized.split("/")
                if not normalized or any(part in ("", ".", "..") for part in parts):
                    raise ValueError("Skill ZIP 包含不安全的文件路径。")
                if entry.external_attr >> 16 & 0o170000 == 0o120000:
                    raise ValueError("Skill ZIP 不能包含符号链接。")
                paths.append(parts)
            roots = {parts[0] for parts in paths}
            if len(roots) != 1:
                raise ValueError("ZIP 必须只包含一个 Skill 根目录。")
            skill_name = roots.pop()
            if skill_name.startswith(".") or not all(char.isalnum() or char in "_-" for char in skill_name):
                raise ValueError("Skill 目录名只能使用字母、数字、下划线或连字符。")
            if ["SKILL.md"] not in [parts[1:] for parts in paths]:
                raise ValueError("Skill 根目录必须包含 SKILL.md。")
            target_root = os.path.join(DSH_SKILLS_HOME, skill_name)
            if os.path.exists(target_root):
                raise ValueError("同名 Skill 已存在：%s。请先改名打包或移除旧版本。" % skill_name)
            os.makedirs(DSH_SKILLS_HOME, exist_ok=True)
            staging_root = tempfile.mkdtemp(prefix="skill-import-", dir=DSH_SKILLS_HOME)
            try:
                for entry, parts in zip(entries, paths):
                    destination = os.path.join(staging_root, *parts[1:])
                    os.makedirs(os.path.dirname(destination), exist_ok=True)
                    with archive.open(entry) as source, open(destination, "wb") as target:
                        shutil.copyfileobj(source, target)
                os.replace(staging_root, target_root)
            except Exception:
                shutil.rmtree(staging_root, ignore_errors=True)
                raise
        return skill_name

    def start_server(self):
        self.ensure_vision_skill()
        self.ensure_default_skills()
        if not os.path.isfile(os.path.join(DSH_HOME, "settings.yaml")) or "image-recognition:" not in open(os.path.join(DSH_HOME, "settings.yaml"), encoding="utf-8").read():
            self.write_image_mode("subagent")
        if self._is_web_up():
            self.started_by_us = False
            return
        if DSH_ENTRY is None:
            print("未找到 dsh 引擎: 请将 App 放入便携包或安装 dsh", file=sys.stderr)
            return
        try:
            cmd = [NODE_BIN, DSH_ENTRY, "web", "--port", str(PORT)] if DSH_ENTRY.lower().endswith((".js", ".cjs", ".mjs")) else ["cmd", "/c", DSH_ENTRY, "web", "--port", str(PORT)]
            self.server_proc = subprocess.Popen(cmd, cwd=WORKSPACE, creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP)
            self.started_by_us = True
        except Exception as error:
            self.server_proc = None
            self.started_by_us = False
            print("启动服务器失败: %s" % error, file=sys.stderr)

    def wait_ready(self):
        import time
        deadline = time.time() + START_TIMEOUT_SEC
        while time.time() < deadline:
            if self._is_web_up():
                return True
            time.sleep(1)
        return False

    def stop_server(self):
        if self.started_by_us and self.server_proc and self.server_proc.poll() is None:
            try:
                subprocess.run(["taskkill", "/PID", str(self.server_proc.pid), "/T", "/F"], capture_output=True, timeout=15)
            except Exception:
                try:
                    self.server_proc.kill()
                except Exception:
                    pass
            self.started_by_us = False

    def _is_web_up(self):
        import urllib.request
        try:
            with urllib.request.urlopen(WEB_URL, timeout=2) as response:
                return response.status == 200
        except Exception:
            return False

    def on_started(self):
        if DSH_ENTRY is None:
            self.window.load_html("<h2>未找到 dsh 引擎</h2><p>请把 App 放到便携包中运行。</p>")
            return
        if not self._is_web_up():
            self.wait_ready()
        if self._is_web_up():
            self.window.load_url(WEB_URL)
        else:
            self.window.load_html("<h2>引擎启动超时</h2><p>请重新启动 App。</p>")

    def on_closing(self):
        self.stop_server()
        return True


def main():
    app = DeepSeekApp()
    app.start_server()
    window = webview.create_window("DeepSeekExe", SPLASH_HTML, width=WINDOW_W, height=WINDOW_H, resizable=True, min_size=(800, 600))
    app.window = window
    window.events.closing += app.on_closing
    menu = [webview.menu.Menu("文件", [webview.menu.MenuAction("导入 Skill ZIP", app.import_skill_zip), webview.menu.MenuSeparator(), webview.menu.MenuAction("识图模式设置", app.open_image_mode_config), webview.menu.MenuAction("视觉模型配置", app.open_vision_config), webview.menu.MenuSeparator(), webview.menu.MenuAction("退出", lambda: window.destroy())])]
    webview.start(func=app.on_started, menu=menu, debug=False, icon=ICON_PATH if os.path.isfile(ICON_PATH) else None)


if __name__ == "__main__":
    main()
