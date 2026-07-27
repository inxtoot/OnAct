# ui.py
# 用户界面构建、事件绑定、与核心交互

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import time
import os
from datetime import datetime

from core import RecorderCore
from log_window import LogWindow
from config import (
    load_settings, save_settings,
    load_recordings, save_recordings,
    load_window_geometry, save_window_geometry
)

class RecorderUI:
    def __init__(self, root):
        self.root = root
        self.root.title("OnAct v1.0.3 - 键鼠录播机")
        self.root.geometry("320x450")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        if os.path.exists("001.ico"):
            try:
                self.root.iconbitmap("001.ico")
            except:
                pass

        self.sample_enabled = tk.BooleanVar(value=False)
        self.sample_interval = tk.IntVar(value=10)
        self.precision_mode = tk.BooleanVar(value=False)
        self.max_log_size_kb = 1024

        self.log_messages = []
        self.log_window = LogWindow(self)

        self.recordings = []
        self.next_id = 1
        self.data_file = "recordings.json"
        self.geometry_file = "window_geometry.json"
        self.settings_file = "settings.json"
        self.log_file = os.path.join("data", "log.txt")

        self.load_settings()
        self.load_recordings()

        self.core = RecorderCore(self)

        self._build_ui()
        self.load_window_geometry()

        self.root.after(1000, self.core.check_listeners)

        self.log("OnAct v1.0.3 已启动。使用 F9 录制/停止，F10 回放选中脚本，F11 查看日志，ESC 停止回放/退出。")

    # -------------------- UI 构建 --------------------
    def _build_ui(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="必读", menu=help_menu)
        help_menu.add_command(label="关于", command=self.show_about)
        help_menu.add_command(label="快捷键说明", command=self.show_shortcuts)

        status_frame = ttk.Frame(self.root, padding="5")
        status_frame.pack(fill=tk.X)

        ttk.Label(status_frame, text="状态:").grid(row=0, column=0, sticky=tk.W)
        self.status_var = tk.StringVar(value="空闲")
        ttk.Label(status_frame, textvariable=self.status_var, foreground="blue").grid(row=0, column=1, sticky=tk.W)

        ttk.Label(status_frame, text="事件数:").grid(row=0, column=2, padx=(20,0), sticky=tk.W)
        self.event_count_var = tk.StringVar(value="0")
        ttk.Label(status_frame, textvariable=self.event_count_var).grid(row=0, column=3, sticky=tk.W)

        control_frame1 = ttk.Frame(self.root, padding="5")
        control_frame1.pack(fill=tk.X)

        ttk.Label(control_frame1, text="循环:").grid(row=0, column=0, sticky=tk.W)
        self.loop_entry = ttk.Entry(control_frame1, width=4)
        self.loop_entry.insert(0, "1")
        self.loop_entry.grid(row=0, column=1, padx=2)

        self.record_btn = ttk.Button(control_frame1, text="录制", width=8,
                                     command=lambda: self.core.toggle_recording(hide=False))
        self.record_btn.grid(row=0, column=2, padx=2)

        self.playback_btn = ttk.Button(control_frame1, text="回放", width=8,
                                       command=self.start_playback_from_selected)
        self.playback_btn.grid(row=0, column=3, padx=2)

        self.stop_playback_btn = ttk.Button(control_frame1, text="停止", width=6,
                                            command=self.core.stop_playback, state=tk.DISABLED)
        self.stop_playback_btn.grid(row=0, column=4, padx=2)

        control_frame2 = ttk.Frame(self.root, padding="5")
        control_frame2.pack(fill=tk.X)

        ttk.Checkbutton(control_frame2, text="采样", variable=self.sample_enabled).grid(row=0, column=0, sticky=tk.W)
        ttk.Label(control_frame2, text="间隔(ms):").grid(row=0, column=1, padx=(5,0))
        ttk.Spinbox(control_frame2, from_=1, to=100, textvariable=self.sample_interval, width=4).grid(row=0, column=2, padx=2)
        ttk.Checkbutton(control_frame2, text="高精度", variable=self.precision_mode).grid(row=0, column=3, padx=(10,0))

        control_frame3 = ttk.Frame(self.root, padding="5")
        control_frame3.pack(fill=tk.X)

        self.delete_btn = ttk.Button(control_frame3, text="删除", width=6, command=self.delete_selected)
        self.delete_btn.grid(row=0, column=0, padx=2)

        self.export_btn = ttk.Button(control_frame3, text="导出", width=6, command=self.export_selected)
        self.export_btn.grid(row=0, column=1, padx=2)

        self.import_btn = ttk.Button(control_frame3, text="导入", width=6, command=self.import_recording)
        self.import_btn.grid(row=0, column=2, padx=2)

        self.diagnose_btn = ttk.Button(control_frame3, text="诊断", width=6, command=self.diagnose_listener)
        self.diagnose_btn.grid(row=0, column=3, padx=2)

        table_frame = ttk.Frame(self.root, padding="5")
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ('#', '文件名', '秒', '录制时间')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=10)
        self.tree.heading('#', text='#')
        self.tree.heading('文件名', text='文件名')
        self.tree.heading('秒', text='秒')
        self.tree.heading('录制时间', text='录制时间')
        self.tree.column('#', width=30, anchor='center')
        self.tree.column('文件名', width=120)
        self.tree.column('秒', width=50, anchor='center')
        self.tree.column('录制时间', width=90, anchor='center')

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="重命名", command=self.rename_selected)
        self.tree.bind("<Button-3>", self.show_context_menu)

        for rec in self.recordings:
            if isinstance(rec, dict) and 'id' in rec:
                self.tree.insert('', tk.END, iid=str(rec['id']), values=(
                    0,
                    rec.get('name', '未知'),
                    rec.get('duration_str', '0'),
                    rec.get('timestamp', '')[11:19] if rec.get('timestamp') else ''
                ))
        self.refresh_row_numbers()

        if self.recordings:
            valid_ids = [r['id'] for r in self.recordings if isinstance(r, dict) and 'id' in r]
            if valid_ids:
                self.next_id = max(valid_ids) + 1
            else:
                self.next_id = 1

    # -------------------- 菜单功能 --------------------
    def show_about(self):
        about_text = (
            "OnAct v1.0.3 - 键鼠录播机\n"
            "版权归属：onno1.com\n\n"
            "本软件使用 MIT 许可证开源。\n"
            "允许自由使用、修改、分发和商业销售，\n"
            "但必须保留本版权声明和许可声明。\n\n"
            "使用的开源组件：\n"
            "• pynput (LGPLv3) - https://github.com/moses-palmer/pynput"
        )
        messagebox.showinfo("关于 OnAct", about_text)

    def show_shortcuts(self):
        shortcuts = (
            "快捷键列表：\n\n"
            "F9  - 开始/停止录制\n"
            "F10 - 回放选中的脚本\n"
            "F11 - 打开/关闭日志窗口\n"
            "ESC - 停止回放（或退出程序）"
        )
        messagebox.showinfo("快捷键说明", shortcuts)

    def show_log_window(self):
        self.log_window.show()

    # -------------------- 诊断 --------------------
    def diagnose_listener(self):
        mouse_status = "运行中" if self.core.mouse_listener.running else "未运行"
        keyboard_status = "运行中" if self.core.keyboard_listener.running else "未运行"
        
        status = f"鼠标监听器运行状态: {mouse_status} （需运行）\n"
        if self.core.mouse_listener.running:
            status += f"最近收到鼠标事件时间: {datetime.fromtimestamp(self.core.last_mouse_event_time).strftime('%H:%M:%S') if self.core.last_mouse_event_time else '无'}\n"
            if self.core.last_mouse_event_time:
                elapsed = time.time() - self.core.last_mouse_event_time
                status += f"距上次鼠标事件已过: {elapsed:.1f} 秒\n"
            else:
                status += "尚未收到任何鼠标事件，可能被其他软件拦截。\n"
        status += f"键盘监听器运行状态: {keyboard_status} （需运行）\n"
        status += "\n建议：以管理员身份运行本程序，或关闭可能占用鼠标钩子的软件后重试。"
        messagebox.showinfo("诊断信息", status)

    # -------------------- 表格操作 --------------------
    def refresh_row_numbers(self):
        for index, item in enumerate(self.tree.get_children(), start=1):
            self.tree.set(item, '#', str(index))

    def on_tree_select(self, event):
        selected = self.tree.selection()
        if selected:
            rec_id = int(selected[0])
            for rec in self.recordings:
                if rec.get('id') == rec_id:
                    self.event_count_var.set(str(len(rec.get('events', []))))
                    break
        else:
            self.event_count_var.set("0")

    def show_context_menu(self, event):
        iid = self.tree.identify_row(event.y)
        if iid:
            self.tree.selection_set(iid)
            self.context_menu.post(event.x_root, event.y_root)

    def rename_selected(self):
        selected = self.tree.selection()
        if not selected:
            return
        item = selected[0]
        current_name = self.tree.item(item, 'values')[1]
        rec_id = int(item)

        while True:
            new_name = simpledialog.askstring("重命名", "输入新文件名:", initialvalue=current_name, parent=self.root)
            if new_name is None:
                return
            if new_name == current_name:
                return
            if not new_name.strip():
                messagebox.showwarning("警告", "文件名不能为空")
                continue
            if any(r.get('name') == new_name for r in self.recordings if r.get('id') != rec_id):
                messagebox.showerror("重名错误", f"文件名 '{new_name}' 已存在")
                continue

            self.tree.set(item, '文件名', new_name)
            for rec in self.recordings:
                if rec.get('id') == rec_id:
                    rec['name'] = new_name
                    break
            self.save_recordings()
            self.log(f"已重命名为: {new_name}")
            break

    def delete_selected(self):
        if self.core.playback_active or self.core.recording:
            messagebox.showwarning("操作禁止", "请先停止录制或回放")
            return
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("提示", "请先选中要删除的脚本")
            return
        item = selected[0]
        rec_id = int(item)
        self.recordings = [r for r in self.recordings if r.get('id') != rec_id]
        self.tree.delete(item)
        self.event_count_var.set("0")
        self.refresh_row_numbers()
        self.save_recordings()
        self.log(f"已删除录制 ID={rec_id}")

    # ================== 修改：导出默认定位到 data/ ==================
    def export_selected(self):
        if self.core.playback_active or self.core.recording:
            messagebox.showwarning("操作禁止", "请先停止录制或回放")
            return
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("提示", "请先选中要导出的脚本")
            return
        item = selected[0]
        rec_id = int(item)
        recording = next((r for r in self.recordings if r.get('id') == rec_id), None)
        if not recording:
            return

        data_dir = os.path.join(os.getcwd(), "data")
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="保存录制文件",
            initialfile=recording.get('name', '录制') + ".json",
            initialdir=data_dir  # 新增
        )
        if not file_path:
            return
        try:
            import json
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(recording.get('events', []), f, indent=2, ensure_ascii=False)
            self.log(f"已导出: {file_path}")
        except Exception as e:
            messagebox.showerror("导出失败", str(e))
            self.log(f"导出失败: {e}")

    # ================== 修改：导入默认定位到 data/ ==================
    def import_recording(self):
        if self.core.playback_active or self.core.recording:
            messagebox.showwarning("操作禁止", "请先停止录制或回放")
            return

        data_dir = os.path.join(os.getcwd(), "data")
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="选择录制文件",
            initialdir=data_dir  # 新增
        )
        if not file_path:
            return
        try:
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                events = json.load(f)
            if not isinstance(events, list):
                raise ValueError("文件内容不是事件列表")
            duration = max((e[0] for e in events), default=0)
            duration_str = f"{duration:.2f}"
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            name = base_name
            counter = 1
            while any(r.get('name') == name for r in self.recordings):
                name = f"{base_name}_{counter}"
                counter += 1
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            recording = {
                'id': self.next_id,
                'name': name,
                'duration': duration,
                'duration_str': duration_str,
                'timestamp': timestamp,
                'events': events
            }
            self.recordings.append(recording)
            self.add_recording_to_table(recording)
            self.next_id += 1
            self.save_recordings()
            self.log(f"已导入 {name}，事件数 {len(events)}")
        except Exception as e:
            messagebox.showerror("导入失败", str(e))
            self.log(f"导入失败: {e}")

    def add_recording_to_table(self, recording):
        def _add():
            self.tree.insert('', tk.END, iid=str(recording['id']), values=(
                0,
                recording['name'],
                recording['duration_str'],
                recording['timestamp'][11:19]
            ))
            self.refresh_row_numbers()
        self.root.after(0, _add)

    # -------------------- 回放触发 --------------------
    def start_playback_from_selected(self):
        if self.core.playback_active:
            self.log("已经在回放中")
            return
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("提示", "请先在表格中选中要回放的脚本")
            return
        item = selected[0]
        rec_id = int(item)
        recording = next((r for r in self.recordings if r.get('id') == rec_id), None)
        if not recording:
            return
        events = recording.get('events', [])
        if not events:
            self.log("该录制没有事件")
            return
        try:
            loop_count = int(self.loop_entry.get())
        except ValueError:
            loop_count = 1

        self.record_btn.config(state=tk.DISABLED)
        self.playback_btn.config(state=tk.DISABLED)
        self.stop_playback_btn.config(state=tk.NORMAL)
        self.delete_btn.config(state=tk.DISABLED)
        self.export_btn.config(state=tk.DISABLED)
        self.import_btn.config(state=tk.DISABLED)

        self.core.start_playback(events, loop_count, hide_callback=self.hide_window)

    def playback_finished(self):
        self.record_btn.config(state=tk.NORMAL)
        self.playback_btn.config(state=tk.NORMAL)
        self.stop_playback_btn.config(state=tk.DISABLED)
        self.delete_btn.config(state=tk.NORMAL)
        self.export_btn.config(state=tk.NORMAL)
        self.import_btn.config(state=tk.NORMAL)
        self.show_window()
        self.on_tree_select(None)

    # -------------------- 录制停止后的保存 --------------------
    def on_recording_stopped(self, events, start_time):
        if not events:
            return
        last_time = events[-1][0] if events else 0
        duration_str = f"{last_time:.2f}"
        name = time.strftime("%Y%m%d", time.localtime(start_time))
        base_name = name
        counter = 1
        while any(r.get('name') == name for r in self.recordings):
            name = f"{base_name}_{counter}"
            counter += 1
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time))
        recording = {
            'id': self.next_id,
            'name': name,
            'duration': last_time,
            'duration_str': duration_str,
            'timestamp': timestamp,
            'events': events
        }
        self.recordings.append(recording)
        self.add_recording_to_table(recording)
        self.next_id += 1
        self.save_recordings()
        self.log(f"已添加录制: {name}")

    def set_recording_button_state(self, is_recording):
        if is_recording:
            self.record_btn.config(text="停止")
        else:
            self.record_btn.config(text="录制")

    # -------------------- 窗口控制 --------------------
    def hide_window(self):
        self.root.after(0, self.root.withdraw)

    def show_window(self):
        def _show():
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
        self.root.after(0, _show)

    # -------------------- 状态更新 --------------------
    def update_status(self, status, event_count=None):
        def _update():
            self.status_var.set(status)
            if event_count is not None:
                self.event_count_var.set(str(event_count))
        self.root.after(0, _update)

    def update_event_count(self, count):
        self.root.after(0, lambda: self.event_count_var.set(str(count)))

    # -------------------- 日志 --------------------
    def log(self, message):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"{timestamp} - {message}"
        self.log_messages.append(log_line)
        self.log_window.add_log(log_line)

        log_path = self.log_file
        max_bytes = self.max_log_size_kb * 1024
        try:
            if os.path.exists(log_path) and os.path.getsize(log_path) >= max_bytes:
                backup_path = log_path.replace('.txt', '_old.txt')
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                os.rename(log_path, backup_path)
                backup_msg = f"{timestamp} - 日志文件超过 {self.max_log_size_kb} KB，已备份"
                self.log_messages.append(backup_msg)
                self.log_window.add_log(backup_msg)
        except Exception as e:
            print(f"日志备份失败: {e}")

        try:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(log_line + '\n')
        except Exception as e:
            print(f"写入日志文件失败: {e}")

    # -------------------- 配置读写 --------------------
    def load_settings(self):
        settings = load_settings(self.settings_file)
        self.sample_enabled.set(settings.get('sample_enabled', False))
        self.sample_interval.set(settings.get('sample_interval', 10))
        self.precision_mode.set(settings.get('precision_mode', False))
        self.max_log_size_kb = settings.get('max_log_size_kb', 1024)

    def save_settings(self):
        settings = {
            'sample_enabled': self.sample_enabled.get(),
            'sample_interval': self.sample_interval.get(),
            'precision_mode': self.precision_mode.get(),
            'max_log_size_kb': self.max_log_size_kb,
        }
        save_settings(settings, self.settings_file)

    def load_window_geometry(self):
        geom = load_window_geometry(self.geometry_file)
        if geom:
            try:
                self.root.geometry(geom)
            except:
                pass

    def save_window_geometry(self):
        geom = self.root.geometry()
        save_window_geometry(geom, self.geometry_file)

    def load_recordings(self):
        self.recordings = load_recordings(self.data_file)
        self.log(f"已加载 {len(self.recordings)} 个录制")

    def save_recordings(self):
        save_recordings(self.recordings, self.data_file)
        self.log("已保存录制文件")

    # -------------------- 退出 --------------------
    def on_closing(self):
        self.core.stop_listeners()
        self.save_settings()
        self.save_window_geometry()
        self.log("正在退出程序...")
        self.root.destroy()
