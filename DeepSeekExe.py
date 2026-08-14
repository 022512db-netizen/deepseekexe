#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeekExe — DeepSeek 独立桌面 App(类似 Codex 的独立运行形态)

- 用 pywebview(Edge WebView2)把 dsh web 的界面直接嵌入原生窗口,不打开浏览器
- 引擎随 App 启动/关闭:窗口关闭即停止内部服务器
- 仅负责运行;源码更新在开发机完成,重新打包分发

依赖:
  - 便携模式: App 同级 runtime/node.exe + runtime/dsh/ 引擎(免安装)
  - 或本机已安装 dsh(@deepseek-ai/dsh)
"""

import os
import shutil
import subprocess
import sys

import webview

# ==================== 配置区(可按需修改) ====================
def _app_dir():
    """exe 所在目录(打包后)或脚本所在目录(源码运行)。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


APP_DIR = _app_dir()
# 工作目录: 默认跟随 App 所在目录(便携模式,拷到哪哪就是工作区);
# 可用环境变量 DSHEXE_WORKSPACE 指定。
WORKSPACE = os.environ.get("DSHEXE_WORKSPACE") or APP_DIR
PORT = int(os.environ.get("DSHEXE_PORT", "3080"))                # 可用环境变量覆盖(测试用)
WEB_URL = "http://127.0.0.1:%d" % PORT
START_TIMEOUT_SEC = 90
WINDOW_W, WINDOW_H = 1280, 860


def find_engine():
    """定位 dsh 引擎,返回 (node可执行, dsh入口js)。

    查找顺序:
      1. 便携包: App 同级 runtime/node.exe + runtime/dsh/(引擎拷贝)
      2. 环境变量 DSHEXE_DSH_ENTRY 指向 dsh 的 lib/bin.js
      3. 本机 npx 缓存(@deepseek-ai/dsh)
      4. PATH 上的 dsh 命令(返回其 .cmd 路径,启动时用 cmd /c)
    """
    # 1. 便携包
    p_node = os.path.join(APP_DIR, "runtime", "node.exe")
    p_dsh = os.path.join(APP_DIR, "runtime", "dsh", "node_modules",
                         "@deepseek-ai", "dsh", "lib", "bin.js")
    if os.path.isfile(p_node) and os.path.isfile(p_dsh):
        return p_node, p_dsh
    # 2. 环境变量
    env_entry = os.environ.get("DSHEXE_DSH_ENTRY")
    if env_entry and os.path.isfile(env_entry):
        return shutil.which("node") or "node", env_entry
    # 3. 本机 npx 缓存
    import glob
    npx_hits = glob.glob(os.path.join(
        os.path.expanduser("~"), "AppData", "Local", "npm-cache",
        "_npx", "*", "node_modules", "@deepseek-ai", "dsh", "lib", "bin.js"))
    if npx_hits:
        return shutil.which("node") or "node", npx_hits[0]
    # 4. PATH 上的 dsh 命令
    dsh_cmd = shutil.which("dsh")
    if dsh_cmd:
        return shutil.which("node") or "node", dsh_cmd
    return None, None


NODE_BIN, DSH_ENTRY = find_engine()
# ============================================================

SPLASH_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
body{margin:0;height:100vh;display:flex;align-items:center;justify-content:center;
background:#1a1a2e;color:#eee;font-family:"Microsoft YaHei",sans-serif}
.box{text-align:center}.spin{width:44px;height:44px;border:5px solid #333;border-top-color:#4CAF50;
border-radius:50%;margin:0 auto 18px;animation:r 1s linear infinite}
@keyframes r{to{transform:rotate(360deg)}}</style></head><body>
<div class="box"><div class="spin"></div><h2>正在启动 DeepSeek 引擎…</h2></div></body></html>"""


class DeepSeekApp:
    def __init__(self):
        self.window = None
        self.server_proc = None      # 本 App 启动的服务器进程
        self.started_by_us = False   # 服务器是否由本 App 启动

    # ---------- 服务器管理 ----------
    def start_server(self):
        """启动 dsh web 服务器(隐藏窗口)。若端口已被占用则直接复用。"""
        if self._is_web_up():
            self.started_by_us = False
            return
        if DSH_ENTRY is None:
            print("未找到 dsh 引擎: 请将 App 放入便携包或安装 dsh", file=sys.stderr)
            return
        try:
            if DSH_ENTRY.lower().endswith((".js", ".cjs", ".mjs")):
                cmd = [NODE_BIN, DSH_ENTRY, "web", "--port", str(PORT)]
            else:
                # PATH 上的 dsh 命令(.cmd/.ps1), 经 cmd /c 启动
                cmd = ["cmd", "/c", DSH_ENTRY, "web", "--port", str(PORT)]
            self.server_proc = subprocess.Popen(
                cmd,
                cwd=WORKSPACE,
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP,
            )
            self.started_by_us = True
        except Exception as e:  # noqa: BLE001
            self.server_proc = None
            self.started_by_us = False
            print("启动服务器失败: %s" % e, file=sys.stderr)

    def wait_ready(self):
        """等待网页界面就绪(阻塞)。"""
        import time
        deadline = time.time() + START_TIMEOUT_SEC
        while time.time() < deadline:
            if self._is_web_up():
                return True
            time.sleep(1)
        return False

    def stop_server(self):
        """关闭本 App 启动的服务器(含子进程)。"""
        if self.started_by_us and self.server_proc and self.server_proc.poll() is None:
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(self.server_proc.pid), "/T", "/F"],
                    capture_output=True, timeout=15)
            except Exception:  # noqa: BLE001
                try:
                    self.server_proc.kill()
                except Exception:  # noqa: BLE001
                    pass
            self.started_by_us = False

    def _is_web_up(self):
        import urllib.request
        try:
            with urllib.request.urlopen(WEB_URL, timeout=2) as resp:
                return resp.status == 200
        except Exception:  # noqa: BLE001
            return False

    # ---------- 事件 ----------
    def on_started(self):
        """GUI 主线程启动后:等待服务器就绪并加载界面。"""
        if DSH_ENTRY is None:
            self.window.load_html("<!DOCTYPE html><html><body style='background:#1a1a2e;color:#eee;"
                                  "font-family:sans-serif;display:flex;align-items:center;"
                                  "justify-content:center;height:100vh'><h2>未找到 dsh 引擎<br>"
                                  "<small>请把 App 放到便携包(含 runtime\\ 目录)中,或用 "
                                  "DSHEXE_DSH_ENTRY 指定 dsh 入口</small></h2></body></html>")
            return
        if not self._is_web_up():
            self.wait_ready()
        if self._is_web_up():
            self.window.load_url(WEB_URL)
        else:
            self.window.load_html("<!DOCTYPE html><html><body style='background:#1a1a2e;color:#eee;"
                                  "font-family:sans-serif;display:flex;align-items:center;"
                                  "justify-content:center;height:100vh'><h2>引擎启动超时,请手动启动"
                                  "<code>dsh web</code> 后重试</h2></body></html>")

    def on_closing(self):
        self.stop_server()
        return True  # 允许关闭


def resource_path(name):
    """兼容打包(exe)与源码运行两种模式的资源路径。"""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


ICON_PATH = resource_path(os.path.join("assets", "deepseek.ico"))


def main():
    app = DeepSeekApp()
    app.start_server()

    window = webview.create_window(
        "DeepSeekExe",
        SPLASH_HTML,
        width=WINDOW_W, height=WINDOW_H,
        resizable=True, min_size=(800, 600),
    )
    app.window = window
    window.events.closing += app.on_closing

    menu = [
        webview.menu.Menu("文件", [
            webview.menu.MenuAction("退出", lambda: window.destroy()),
        ]),
    ]

    webview.start(func=app.on_started, menu=menu, debug=False,
                  icon=ICON_PATH if os.path.isfile(ICON_PATH) else None)


if __name__ == "__main__":
    main()
