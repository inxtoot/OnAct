# updater.py
# 自动更新检查与下载管理

import tkinter as tk
import threading
import requests
import webbrowser
import tkinter.messagebox as msgbox
import ssl
import urllib3
from tkinter import ttk

# ==================== 彻底禁用 SSL 验证 ====================
try:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass

# ==================== 版本与镜像配置 ====================
VERSION = "v1.1.7"   # 当前程序版本号（每次发版手动更新）

# 可用的镜像下载地址（按优先级排列，包含应急网盘）
MIRROR_URLS = [
    ("ghproxy.net", "https://ghproxy.net/https://github.com/inxtoot/OnAct/releases/download/{}/main.exe"),
    ("ghproxy.com", "https://ghproxy.com/https://github.com/inxtoot/OnAct/releases/download/{}/main.exe"),
    ("gitclone.com", "https://gitclone.com/inxtoot/OnAct/releases/download/{}/main.exe"),
    ("GitHub 官方", "https://github.com/inxtoot/OnAct/releases/download/{}/main.exe"),
    ("百度网盘（备用）", "https://pan.baidu.com/s/xxxx"),
]

# ==================== 核心更新函数 ====================
def check_update(show_if_no_update=False):
    """
    检查 GitHub 上的最新版本
    show_if_no_update: True 时，即使没有新版本也弹窗提示
    """
    try:
        url = "https://api.github.com/repos/inxtoot/OnAct/releases/latest"
        response = requests.get(url, timeout=5, verify=False)
        if response.status_code == 200:
            data = response.json()
            latest_version = data.get("tag_name", "")
            if latest_version and latest_version != VERSION:
                show_update_dialog(latest_version)
                return
            elif show_if_no_update:
                msgbox.showinfo("更新检查", f"当前已是最新版本（{VERSION}）")
                return
        else:
            if show_if_no_update:
                msgbox.showwarning("更新检查", "无法获取更新信息，请稍后重试。")
    except Exception as e:
        if show_if_no_update:
            msgbox.showerror("更新检查失败", f"网络连接异常：{e}\n请检查网络或手动访问 GitHub 查看更新。")
        else:
            print(f"检查更新失败: {e}")

def show_update_dialog(latest_version):
    """显示多镜像下载窗口"""
    win = tk.Toplevel()
    win.title("发现新版本")
    win.geometry("450x280")
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
        btn = ttk.Button(row1 if i < 3 else row2, text=name, width=18,
                         command=lambda u=download_url: open_download(u, win))
        btn.pack(side=tk.LEFT, padx=5, pady=3)

    ttk.Button(win, text="暂不更新", command=win.destroy).pack(pady=10)

def open_download(url, window):
    """打开下载链接并关闭窗口"""
    webbrowser.open(url)
    window.destroy()
