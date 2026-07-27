# main.py
# 程序入口

import tkinter as tk
from ui import RecorderUI

if __name__ == "__main__":
    root = tk.Tk()
    app = RecorderUI(root)
    root.mainloop()
