# main.py
# 程序入口

import tkinter as tk
import threading
from ui import RecorderUI
from updater import check_update

if __name__ == "__main__":
    root = tk.Tk()
    # 后台检查更新（不阻塞界面）
    threading.Thread(target=check_update, daemon=True).start()
    app = RecorderUI(root)
    root.mainloop()
