# main.py
# 程序入口

import tkinter as tk
import threading
import requests
import webbrowser
import tkinter.messagebox as msgbox

from ui import RecorderUI

# 当前程序版本号（每次发布新版本时手动更新此处）
VERSION = "v1.1.1"

def check_update():
    """检查 GitHub 上的最新版本，如有更新则提示用户下载"""
    try:
        # 获取最新 Release 信息（公开仓库无需认证）
        url = "https://api.github.com/repos/inxtoot/OnAct/releases/latest"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            latest_version = data.get("tag_name", "")
            if latest_version and latest_version != VERSION:
                # 发现新版本，弹窗询问
                result = msgbox.askyesno(
                    "发现新版本",
                    f"检测到新版本 {latest_version}（当前版本 {VERSION}）\n\n是否立即前往下载？"
                )
                if result:
                    # 使用 gitclone.com 镜像加速国内下载
                    download_url = f"https://gitclone.com/inxtoot/OnAct/releases/download/{latest_version}/main.exe"
                    webbrowser.open(download_url)
        # 无新版本或请求失败时静默忽略
    except Exception as e:
        # 网络异常等不干扰主程序
        print(f"检查更新失败: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    # 启动后台线程检查更新（不阻塞界面）
    threading.Thread(target=check_update, daemon=True).start()
    app = RecorderUI(root)
    root.mainloop()
