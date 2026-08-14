#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeekExe — DeepSeek 代理独立启动器

功能:
  1. [启动 DeepSeek]  一键启动 dsh web 代理,自动打开浏览器访问网页版界面
  2. [保存并推送]     手动触发:将会话记录(.dsh/sessions)同步到工作目录,
                     连同工作目录文件一起 commit 并 push 到远程 GitHub 仓库

依赖:
  - 本机已安装 dsh (@deepseek-ai/dsh) 与 git
  - 已配置 GitHub 凭据 (git credential)
"""

import os
import shutil
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime
import tkinter as tk
from tkinter import scrolledtext, messagebox

# ==================== 配置区(可按需修改) ====================
WORKSPACE = r"C:\Users\asus\Desktop\deepseek"                    # 工作目录 = 本地 git 仓库
SESSIONS_SRC = os.path.join(os.environ.get("USERPROFILE", ""), ".dsh", "sessions")
SESSIONS_DST = os.path.join(WORKSPACE, "sessions")               # 仓库内的会话镜像目录
REMOTE_URL = "https://github.com/022512db-netizen/deepseekexe.git"
WEB_URL = "http://127.0.0.1:3080"
BRANCH = "main"
# dsh 的 node 入口(优先使用绝对路径,失败则回退到 PATH 上的 dsh 命令)
DSH_ENTRY = r"C:\Users\asus\AppData\Local\npm-cache\_npx\1e7f6d9597241db0\node_modules\@deepseek-ai\dsh\lib\bin.js"
NODE_BIN = shutil.which("node") or "node"
START_TIMEOUT_SEC = 60
# ============================================================


class DeepSeekExeApp:
    def __init__(self, root):
        self.root = root
        root.title("DeepSeekExe — DeepSeek 代理启动器")
        root.geometry("680x520")
        root.minsize(560, 420)

        # 顶部按钮区
        btn_frame = tk.Frame(root, padx=10, pady=8)
        btn_frame.pack(fill=tk.X)

        self.start_btn = tk.Button(
            btn_frame, text="🚀 启动 DeepSeek", command=self.start_agent,
            font=("Microsoft YaHei", 11), bg="#4CAF50", fg="white",
            padx=16, pady=6, cursor="hand2")
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.save_btn = tk.Button(
            btn_frame, text="💾 保存并推送到 GitHub", command=self.save_and_push,
            font=("Microsoft YaHei", 11), bg="#2196F3", fg="white",
            padx=16, pady=6, cursor="hand2")
        self.save_btn.pack(side=tk.LEFT, padx=(0, 10))

        # 状态栏
        self.status_var = tk.StringVar(value="正在检测环境…")
        status_lbl = tk.Label(root, textvariable=self.status_var, anchor="w",
                              font=("Microsoft YaHei", 9), fg="#555", padx=12)
        status_lbl.pack(fill=tk.X)

        # 日志区
        log_frame = tk.Frame(root, padx=10, pady=(0, 10))
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log_text = scrolledtext.ScrolledText(
            log_frame, font=("Consolas", 9), state=tk.DISABLED, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self.log("DeepSeekExe 已启动")
        self.log("工作目录: %s" % WORKSPACE)
        self.log("远程仓库: %s" % REMOTE_URL)
        self.log("会话来源: %s" % SESSIONS_SRC)
        self.log("")

        self.refresh_status()

    # ---------- 工具方法 ----------
    def log(self, msg):
        """主线程安全地追加日志"""
        def _append():
            self.log_text.configure(state=tk.NORMAL)
            self.log_text.insert(tk.END, msg + "\n")
            self.log_text.see(tk.END)
            self.log_text.configure(state=tk.DISABLED)
        self.root.after(0, _append)

    def run_cmd(self, args, cwd=None, timeout=300):
        """运行命令并捕获输出;返回 (returncode, 合并输出)"""
        self.log("$ " + " ".join(args))
        try:
            proc = subprocess.run(
                args, cwd=cwd, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=timeout)
            output = (proc.stdout or "") + (proc.stderr or "")
            if output.strip():
                for line in output.rstrip().splitlines():
                    self.log("  | " + line)
            return proc.returncode, output
        except subprocess.TimeoutExpired:
            self.log("  !! 命令超时")
            return -1, "timeout"
        except Exception as e:  # noqa: BLE001
            self.log("  !! 命令执行失败: %s" % e)
            return -1, str(e)

    def set_status(self, text):
        self.root.after(0, lambda: self.status_var.set(text))

    def busy(self, busy):
        """切换按钮可用状态,防止并发操作"""
        state = tk.DISABLED if busy else tk.NORMAL
        self.root.after(0, lambda: (self.start_btn.configure(state=state),
                                    self.save_btn.configure(state=state)))

    # ---------- 环境检测 ----------
    def refresh_status(self):
        def _work():
            lines = []
            if os.path.isdir(os.path.join(WORKSPACE, ".git")):
                rc, out = self.run_cmd(["git", "-C", WORKSPACE, "status", "-sb"], timeout=30)
                lines.append(out.strip().splitlines()[0] if out.strip() else "git 仓库已就绪")
            else:
                lines.append("工作目录还不是 git 仓库")
            if os.path.isfile(DSH_ENTRY):
                lines.append("dsh 引擎: 可用")
            else:
                lines.append("dsh 引擎: 未找到(%s)" % DSH_ENTRY)
            self.set_status(" | ".join(lines))
        threading.Thread(target=_work, daemon=True).start()

    # ---------- 功能 1: 启动代理 ----------
    def start_agent(self):
        self.busy(True)
        threading.Thread(target=self._start_agent_work, daemon=True).start()

    def _start_agent_work(self):
        try:
            self.log("")
            self.log("== 检查网页界面是否已在运行 ==")
            if self._is_web_up():
                self.log("网页界面已在运行: %s" % WEB_URL)
                webbrowser.open(WEB_URL)
                self.set_status("网页界面已在运行,已打开浏览器")
                return

            self.log("== 启动 dsh web 引擎 ==")
            if not os.path.isfile(DSH_ENTRY):
                self.log("找不到 dsh 入口,尝试使用 PATH 上的 dsh 命令…")
                proc = subprocess.Popen(
                    ["dsh", "web"],
                    cwd=WORKSPACE, creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                proc = subprocess.Popen(
                    [NODE_BIN, DSH_ENTRY, "web"],
                    cwd=WORKSPACE, creationflags=subprocess.CREATE_NEW_CONSOLE)
            self.log("引擎已启动 (进程 PID %d),等待就绪…" % proc.pid)

            deadline = time.time() + START_TIMEOUT_SEC
            while time.time() < deadline:
                if self._is_web_up():
                    self.log("✅ 网页界面就绪: %s" % WEB_URL)
                    webbrowser.open(WEB_URL)
                    self.set_status("DeepSeek 已启动 ✓")
                    return
                time.sleep(1)
            self.log("!! 等待超时(%ds),请稍后手动访问 %s" % (START_TIMEOUT_SEC, WEB_URL))
            self.log("   注意:引擎在独立控制台窗口中运行,关闭该窗口即停止服务")
            self.set_status("启动超时,请手动访问 " + WEB_URL)
        finally:
            self.busy(False)

    def _is_web_up(self):
        try:
            import urllib.request
            with urllib.request.urlopen(WEB_URL, timeout=2) as resp:
                return resp.status == 200
        except Exception:  # noqa: BLE001
            return False

    # ---------- 功能 2: 保存并推送 ----------
    def save_and_push(self):
        self.busy(True)
        threading.Thread(target=self._save_and_push_work, daemon=True).start()

    def _save_and_push_work(self):
        try:
            self.log("")
            self.log("== 1/4 同步会话记录 ==")
            if os.path.isdir(SESSIONS_SRC):
                if os.path.isdir(SESSIONS_DST):
                    shutil.rmtree(SESSIONS_DST)
                shutil.copytree(SESSIONS_SRC, SESSIONS_DST)
                self.log("已同步会话目录: %s → %s" % (SESSIONS_SRC, SESSIONS_DST))
            else:
                self.log("会话目录不存在,跳过: %s" % SESSIONS_SRC)

            self.log("== 2/4 确保 git 仓库就绪 ==")
            if not os.path.isdir(os.path.join(WORKSPACE, ".git")):
                self.log("工作目录还不是 git 仓库,正在初始化…")
                self.run_cmd(["git", "init", "-b", BRANCH], cwd=WORKSPACE)
                self.run_cmd(["git", "remote", "add", "origin", REMOTE_URL], cwd=WORKSPACE)

            rc, _ = self.run_cmd(["git", "-C", WORKSPACE, "remote", "get-url", "origin"], timeout=30)
            if rc != 0:
                self.run_cmd(["git", "remote", "add", "origin", REMOTE_URL], cwd=WORKSPACE)

            self.log("== 3/4 提交改动 ==")
            self.run_cmd(["git", "-C", WORKSPACE, "add", "-A"], timeout=60)
            rc, _ = self.run_cmd(["git", "-C", WORKSPACE, "diff", "--cached", "--quiet"], timeout=30)
            if rc == 0:
                self.log("没有新的改动,无需提交")
            else:
                stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.run_cmd(["git", "-C", WORKSPACE, "commit", "-m",
                              "自动保存 %s" % stamp], timeout=60)

            self.log("== 4/4 推送到 GitHub ==")
            rc, out = self.run_cmd(["git", "-C", WORKSPACE, "push", "-u", "origin", BRANCH], timeout=180)
            if rc == 0:
                self.log("✅ 已推送到 %s (%s)" % (REMOTE_URL, BRANCH))
                self.set_status("已保存并推送到 GitHub ✓  " + datetime.now().strftime("%H:%M:%S"))
            else:
                self.log("!! 推送失败,请检查网络或 GitHub 凭据")
                self.set_status("推送失败 ✗ 详见日志")
        finally:
            self.busy(False)


def main():
    root = tk.Tk()
    try:
        root.tk.call("tk", "scaling", 1.2)
    except Exception:  # noqa: BLE001
        pass
    DeepSeekExeApp(root)
    root.mainloop()


if __name__ == "__main__":
    # 冻结为 exe 时,避免把 exe 所在目录当工作目录
    if getattr(sys, "frozen", False):
        os.chdir(os.path.dirname(sys.executable))
    main()
