# main.py
# 程序入口

import tkinter as tk
import threading
import requests
import webbrowser
import tkinter.messagebox as msgbox
import certifi
from tkinter import ttk

from ui import RecorderUI

# 当前程序版本号（每次发布新版本时手动更新此处）
VERSION = "v1.1.0"

# 可用的镜像下载地址（按优先级排列，包含应急网盘）
MIRROR_URLS = [
    ("ghproxy.net", "https://ghproxy.net/https://github.com/inxtoot/OnAct/releases/download/{}/main.exe"),
    ("ghproxy.cxkpro.top", "https://ghproxy.cxkpro.top/https://github.com/inxtoot/OnAct/releases/download/{}/main.exe"),
    ("gitclone.com", "https://gitclone.com/inxtoot/OnAct/releases/download/{}/main.exe"),
    # 应急网盘地址（请替换为真实共享链接）
    ("百度网盘（备用）", "https://pan.baidu.com/s/xxxx"),
]

def check_update():
    """检查 GitHub 上的最新版本，如有更新则弹窗让用户选择镜像下载"""
    try:
        url = "https://api.github.com/repos/inxtoot/OnAct/releases/latest"
        response = requests.get(url, timeout=5, verify=certifi.where())
        if response.status_code == 200:
            data = response.json()
            latest_version = data.get("tag_name", "")
            if latest_version and latest_version != VERSION:
                show_update_dialog(latest_version)
    except Exception as e:
        # 静默失败，不干扰主程序
        print(f"检查更新失败: {e}")

def show_update_dialog(latest_version):
    """显示更新提示和镜像选择窗口（已移除用户交流群按钮）"""
    win = tk.Toplevel()
    win.title("发现新版本")
    win.geometry("450x250")
    win.resizable(False, False)
    win.attributes('-topmost', True)

    ttk.Label(win, text=f"检测到新版本 {latest_version}（当前版本 {VERSION}）", font=('Arial', 10)).pack(pady=10)
    ttk.Label(win, text="请选择下载镜像（若镜像失效请换另一个）：", font=('Arial', 9)).pack(pady=5)

    btn_frame = ttk.Frame(win)
    btn_frame.pack(pady=10)

    row1 = ttk.Frame(btn_frame)
    row1.pack()
    row2 = ttk.Frame(btn_frame)
    row2.pack()

    for i, (name, url_template) in enumerate(MIRROR_URLS):
        if url_template == "https://pan.baidu.com/s/xxxx":
            download_url = url_template
        else:
            download_url = url_template.format(latest_version)
        btn = ttk.Button(row1 if i < 2 else row2, text=name, width=18,
                         command=lambda u=download_url: open_download(u, win))
        btn.pack(side=tk.LEFT, padx=5, pady=3)

    ttk.Button(win, text="暂不更新", command=win.destroy).pack(pady=10)

def open_download(url, window):
    """打开下载链接并关闭提示窗口"""
    webbrowser.open(url)
    window.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    threading.Thread(target=check_update, daemon=True).start()
    app = RecorderUI(root)
    root.mainloop()
