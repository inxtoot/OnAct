# log_window.py
# 独立日志窗口，按 F11 打开/关闭

import tkinter as tk
from tkinter import ttk

class LogWindow:
    def __init__(self, parent):
        self.parent = parent          # 传入 UI 实例（用于获取日志列表）
        self.window = None
        self.text_widget = None

    def show(self):
        if self.window is None or not self.window.winfo_exists():
            self.window = tk.Toplevel(self.parent.root)
            self.window.title("OnAct 日志")
            self.window.geometry("500x300")
            self.window.protocol("WM_DELETE_WINDOW", self.hide)
            self.window.attributes('-topmost', True)

            frame = ttk.Frame(self.window)
            frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

            self.text_widget = tk.Text(frame, wrap='word', font=('Consolas', 9))
            scrollbar = ttk.Scrollbar(frame, orient='vertical', command=self.text_widget.yview)
            self.text_widget.configure(yscrollcommand=scrollbar.set)
            self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            self.text_widget.config(state=tk.DISABLED)
            self._display_existing_logs()
        else:
            self.window.deiconify()
            self.window.lift()

    def hide(self):
        if self.window and self.window.winfo_exists():
            self.window.withdraw()

    def _display_existing_logs(self):
        if not self.text_widget:
            return
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.delete(1.0, tk.END)
        for msg in self.parent.log_messages:
            self.text_widget.insert(tk.END, msg + '\n')
        self.text_widget.see(tk.END)
        self.text_widget.config(state=tk.DISABLED)

    def add_log(self, msg):
        if self.text_widget and self.window and self.window.winfo_exists():
            self.text_widget.config(state=tk.NORMAL)
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.see(tk.END)
            self.text_widget.config(state=tk.DISABLED)
