#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeekExe — DeepSeek 独立桌面 App(类似 Codex 的独立运行形态)

- 用 pywebview(Edge WebView2)把 dsh web 的界面直接嵌入原生窗口,不打开浏览器
- 引擎随 App 启动/关闭:窗口关闭即停止内部服务器
- 菜单「保存并推送」:把会话记录(.dsh/sessions)与工作目录文件
  commit 并 push 到远程 GitHub 仓库(手动触发)

依赖: 本机已安装 dsh(@deepseek-ai/dsh)、git、GitHub 凭据
"""

import os
import shutil
import subprocess
import sys
import threading
from datetime import datetime

import webview

# ==================== 配置区(可按需修改) ====================
WORKSPACE = r"C:\Users\asus\Desktop\deepseek"                    # 工作目录 = 本地 git 仓库
SESSIONS_SRC = os.path.join(os.environ.get("USERPROFILE", ""), ".dsh", "sessions")
SESSIONS_DST = os.path.join(WORKSPACE, "sessions")               # 仓库内的会话镜像目录
REMOTE_URL = "https://github.com/022512db-netizen/deepseekexe.git"
PORT = int(os.environ.get("DSHEXE_PORT", "3080"))                # 可用环境变量覆盖(测试用)
WEB_URL = "http://127.0.0.1:%d" % PORT
BRANCH = "main"
DSH_ENTRY = r"C:\Users\asus\AppData\Local\npm-cache\_npx\1e7f6d9597241db0\node_modules\@deepseek-ai\dsh\lib\bin.js"
NODE_BIN = shutil.which("node") or "node"
START_TIMEOUT_SEC = 90
WINDOW_W, WINDOW_H = 1280, 860
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
        self._save_lock = threading.Lock()

    # ---------- 服务器管理 ----------
    def start_server(self):
        """启动 dsh web 服务器(隐藏窗口)。若端口已被占用则直接复用。"""
        if self._is_web_up():
            self.started_by_us = False
            return
        try:
            self.server_proc = subprocess.Popen(
                [NODE_BIN, DSH_ENTRY, "web", "--port", str(PORT)],
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

    # ---------- 保存并推送 ----------
    def save_and_push(self):
        """把会话记录与工作目录文件 commit 并 push 到远程仓库。"""
        with self._save_lock:
            lines = []

            def run(args):
                try:
                    p = subprocess.run(args, cwd=WORKSPACE, capture_output=True,
                                       text=True, encoding="utf-8", errors="replace",
                                       timeout=300)
                    out = ((p.stdout or "") + (p.stderr or "")).strip()
                    return p.returncode, out
                except Exception as e:  # noqa: BLE001
                    return -1, str(e)

            # 1. 同步会话记录
            if os.path.isdir(SESSIONS_SRC):
                if os.path.isdir(SESSIONS_DST):
                    shutil.rmtree(SESSIONS_DST)
                shutil.copytree(SESSIONS_SRC, SESSIONS_DST)
                lines.append("会话已同步")
            else:
                lines.append("会话目录不存在,已跳过")

            # 2. 确保 git 仓库与远程
            if not os.path.isdir(os.path.join(WORKSPACE, ".git")):
                run(["git", "init", "-b", BRANCH])
            rc, _ = run(["git", "remote", "get-url", "origin"])
            if rc != 0:
                run(["git", "remote", "add", "origin", REMOTE_URL])

            # 3. 提交
            run(["git", "add", "-A"])
            rc, _ = run(["git", "diff", "--cached", "--quiet"])
            if rc == 0:
                lines.append("没有新的改动")
            else:
                stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                rc, out = run(["git", "commit", "-m", "自动保存 %s" % stamp])
                lines.append("已提交: %s" % (out.splitlines()[-1] if out else "ok"))

            # 4. 推送
            rc, out = run(["git", "push", "-u", "origin", BRANCH])
            if rc == 0:
                lines.append("✅ 已推送到 %s (%s)" % (REMOTE_URL, BRANCH))
            else:
                lines.append("❌ 推送失败: %s" % (out[-400:] if out else "未知错误"))
            return "\n".join(lines)

    # ---------- 事件 ----------
    def on_started(self):
        """GUI 主线程启动后:等待服务器就绪并加载界面。"""
        if not self._is_web_up():
            self.wait_ready()
        if self._is_web_up():
            self.window.load_url(WEB_URL)
        else:
            self.window.load_html("<!DOCTYPE html><html><body style='background:#1a1a2e;color:#eee;"
                                  "font-family:sans-serif;display:flex;align-items:center;"
                                  "justify-content:center;height:100vh'><h2>引擎启动超时,请手动启动"
                                  "<code>dsh web</code> 后重试</h2></body></html>")

    def on_save(self):
        # 菜单回调运行在 GUI 线程:同步执行,保证 evaluate_js 线程安全
        try:
            self.window.evaluate_js("document.title='DeepSeekExe(保存中…)';")
        except Exception:  # noqa: BLE001
            pass
        result = self.save_and_push()
        try:
            self.window.evaluate_js("alert(%s);" % json_dumps(result))
        except Exception as e:  # noqa: BLE001
            print("通知失败: %s" % e, file=sys.stderr)

    def on_closing(self):
        self.stop_server()
        return True  # 允许关闭


def json_dumps(text):
    """把文本安全地嵌进 JS alert 字符串。"""
    import json
    return json.dumps(str(text), ensure_ascii=False)


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
            webview.menu.MenuAction("保存并推送", app.on_save),
            webview.menu.MenuSeparator(),
            webview.menu.MenuAction("退出", lambda: window.destroy()),
        ]),
    ]

    webview.start(func=app.on_started, menu=menu, debug=False,
                  icon=ICON_PATH if os.path.isfile(ICON_PATH) else None)


if __name__ == "__main__":
    main()
