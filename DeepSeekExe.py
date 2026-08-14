#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DeepSeekExe - embedded DSH desktop application with image fallback setup."""

import html
import os
import shutil
import subprocess
import sys

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
VISION_HOME = os.path.join(os.path.expanduser("~"), ".dsh", "skills", "claude-vision-skill")
DSH_SKILLS_HOME = os.path.join(os.path.expanduser("~"), ".dsh", "skills")

SPLASH_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
body{margin:0;height:100vh;display:flex;align-items:center;justify-content:center;background:#1a1a2e;color:#eee;font-family:"Microsoft YaHei",sans-serif}
.box{text-align:center}.spin{width:44px;height:44px;border:5px solid #333;border-top-color:#4CAF50;border-radius:50%;margin:0 auto 18px;animation:r 1s linear infinite}@keyframes r{to{transform:rotate(360deg)}}</style></head><body><div class="box"><div class="spin"></div><h2>正在启动 DeepSeek 引擎...</h2></div></body></html>"""

VISION_CONFIG_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
body{font:14px "Microsoft YaHei",sans-serif;margin:0;background:#f6f7fb;color:#202535}.wrap{padding:24px;max-width:540px}.note{line-height:1.55;color:#5c6478;margin:0 0 18px}label{display:block;font-weight:600;margin:14px 0 6px}input{width:100%;box-sizing:border-box;padding:10px;border:1px solid #c8cede;border-radius:5px;font:14px Consolas,"Microsoft YaHei",sans-serif}button{margin-top:20px;background:#315efb;color:#fff;border:0;border-radius:5px;padding:10px 18px;font:14px "Microsoft YaHei",sans-serif;cursor:pointer}.status{height:20px;color:#b42318;margin-top:12px}.hint{font-size:12px;color:#72798b;margin-top:5px}</style></head><body><div class="wrap"><h2>配置视觉模型</h2><p class="note">图片已允许附加。非视觉模型会使用全局 Vision Skill 识图。请填写一个支持 OpenAI 兼容图片输入的模型和 API Key；信息仅保存在本机。</p><label>API Base URL</label><input id="base" value="https://jojocode.com/v1" placeholder="https://api.example.com/v1"><label>视觉模型</label><input id="model" value="gpt-5.6-terra" placeholder="例如 gpt-5.6-terra"><div class="hint">默认是已接入的 gpt-5.6-terra；可按自己的视觉服务改为其他模型。</div><label>API Key</label><input id="key" type="password" autocomplete="off" placeholder="输入视觉模型的 API Key"><button onclick="save()">保存视觉配置</button><div id="status" class="status"></div></div><script>async function save(){const status=document.getElementById('status');status.textContent='';const r=await window.pywebview.api.save_vision_config(document.getElementById('base').value,document.getElementById('model').value,document.getElementById('key').value);if(r.ok){status.style.color='#087443';status.textContent='已保存。现在可以关闭本窗口。'}else{status.style.color='#b42318';status.textContent=r.error;}}</script></body></html>"""


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


class DeepSeekApp:
    def __init__(self):
        self.window = None
        self.server_proc = None
        self.started_by_us = False
        self.vision_window = None

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

    def start_server(self):
        self.ensure_vision_skill()
        self.ensure_default_skills()
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
    menu = [webview.menu.Menu("文件", [webview.menu.MenuAction("视觉模型配置", app.open_vision_config), webview.menu.MenuSeparator(), webview.menu.MenuAction("退出", lambda: window.destroy())])]
    webview.start(func=app.on_started, menu=menu, debug=False, icon=ICON_PATH if os.path.isfile(ICON_PATH) else None)


if __name__ == "__main__":
    main()
