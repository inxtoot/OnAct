# core.py
# 核心逻辑：录制、回放、监听器管理、事件执行

import time
import threading
from datetime import datetime
from pynput import keyboard, mouse
from pynput.keyboard import Key, KeyCode
from pynput.mouse import Button

class RecorderCore:
    def __init__(self, ui_callback):
        """
        ui_callback 必须提供以下方法：
            - log(message)
            - update_status(status, event_count=None)
            - update_event_count(count)
            - hide_window()
            - show_window()
            - on_recording_stopped(events, start_time)   # 新增，用于保存录制
            - set_recording_button_state(is_recording)   # 新增，更新按钮文字
        """
        self.ui = ui_callback

        # 状态变量
        self.recording = False
        self.events = []
        self.start_time = None
        self.playback_active = False
        self.stop_playback_flag = False
        self.sample_thread_running = False
        self.sample_interval = 10  # 由UI设置

        # 鼠标事件监控
        self.last_mouse_event_time = 0
        self.mouse_check_interval = 5

        # 控制器
        self.keyboard_controller = keyboard.Controller()
        self.mouse_controller = mouse.Controller()

        # 监听器
        self.keyboard_listener = None
        self.mouse_listener = None
        self.mouse_monitor_running = True

        # 启动监听器
        self.start_listeners()
        threading.Thread(target=self._mouse_health_monitor, daemon=True).start()

    # -------------------- 监听器管理 --------------------
    def start_listeners(self):
        self.keyboard_listener = keyboard.Listener(on_press=self.on_key_press, on_release=self.on_key_release)
        self.mouse_listener = mouse.Listener(on_move=self.on_mouse_move, on_click=self.on_mouse_click, on_scroll=self.on_mouse_scroll)
        self.keyboard_listener.daemon = True
        self.mouse_listener.daemon = True
        self.keyboard_listener.start()
        self.mouse_listener.start()

    def restart_mouse_listener(self):
        if self.mouse_listener and self.mouse_listener.running:
            self.mouse_listener.stop()
            time.sleep(0.5)
        self.mouse_listener = mouse.Listener(on_move=self.on_mouse_move, on_click=self.on_mouse_click, on_scroll=self.on_mouse_scroll)
        self.mouse_listener.daemon = True
        self.mouse_listener.start()
        self.ui.log("已尝试重启鼠标监听器")

    def check_listeners(self):
        if not self.mouse_listener.running:
            self.ui.log("⚠️ 鼠标监听器未启动！可能无法录制鼠标事件。")
        if not self.keyboard_listener.running:
            self.ui.log("⚠️ 键盘监听器未启动！可能无法录制键盘事件。")

    # -------------------- 健康监控 --------------------
    def _mouse_health_monitor(self):
        while self.mouse_monitor_running:
            time.sleep(self.mouse_check_interval)
            if self.recording and self.mouse_listener.running:
                now = time.time()
                if self.last_mouse_event_time == 0:
                    continue
                elapsed = now - self.last_mouse_event_time
                if elapsed > self.mouse_check_interval * 1.5:
                    self.ui.log(f"⚠️ 鼠标监听器可能被拦截：已 {elapsed:.1f} 秒未收到鼠标事件")
                    if self.recording:
                        self.ui.log("尝试重启鼠标监听器...")
                        self.restart_mouse_listener()

    # -------------------- 录制控制 --------------------
    def toggle_recording(self, hide=True):
        """切换录制状态，hide 控制是否隐藏窗口（True=隐藏）"""
        if self.playback_active:
            self.ui.log("回放进行中，无法录制")
            return
        if self.recording:
            self.stop_recording()
        else:
            self.start_recording(hide)

    def start_recording(self, hide=True):
        if not self.mouse_listener.running:
            self.ui.log("鼠标监听器未启动，无法录制鼠标操作！")
            self.restart_mouse_listener()
            if not self.mouse_listener.running:
                return

        self.last_mouse_event_time = 0
        self.recording = True
        self.events.clear()
        self.start_time = time.time()
        self.ui.update_status("录制中", 0)
        self.ui.log("开始录制")
        self.ui.set_recording_button_state(True)   # 按钮文字改为“停止”
        if hide:
            self.ui.hide_window()

        # 采样线程（如果启用）
        if self.ui.sample_enabled.get():
            self.sample_thread_running = True
            self.sample_interval = self.ui.sample_interval.get()
            threading.Thread(target=self._mouse_sample_thread, daemon=True).start()

    def stop_recording(self):
        self.recording = False
        self.sample_thread_running = False
        count = len(self.events)
        self.ui.update_status("空闲", count)
        self.ui.log(f"录制停止，共 {count} 个事件")
        self.ui.set_recording_button_state(False)  # 按钮文字恢复“录制”
        # 回调UI进行保存
        if count > 0:
            self.ui.on_recording_stopped(self.events.copy(), self.start_time)
        else:
            self.ui.on_recording_stopped([], None)
        # 显示窗口（因为录制时可能隐藏了）
        self.ui.show_window()

    def _mouse_sample_thread(self):
        interval = self.sample_interval / 1000.0
        while self.sample_thread_running and self.recording:
            try:
                x, y = self.mouse_controller.position
                rel_time = time.time() - self.start_time
                self.events.append((rel_time, 'mm', (x, y)))
                self.ui.update_event_count(len(self.events))
                time.sleep(interval)
            except Exception as e:
                self.ui.log(f"采样线程错误: {e}")
                break

    # -------------------- 回放控制 --------------------
    def start_playback(self, events, loop_count, hide_callback=None):
        if self.playback_active:
            self.ui.log("已经在回放中")
            return
        if not events:
            self.ui.log("该录制没有事件")
            return

        if self.recording:
            self.stop_recording()

        self.playback_active = True
        self.stop_playback_flag = False
        self.ui.update_status("回放中")
        self.ui.log(f"开始回放，循环次数: {loop_count}")
        if hide_callback:
            hide_callback()

        threading.Thread(target=self._playback_thread, args=(events, loop_count), daemon=True).start()

    def stop_playback(self):
        if self.playback_active:
            self.stop_playback_flag = True
            self.ui.log("正在停止回放...")

    # ================== 回放线程 ==================
    def _playback_thread(self, events, loop_count):
        try:
            total_events = len(events)
            min_delay = 0.005
            key_stable_delay = 0.003

            for i in range(loop_count):
                if self.stop_playback_flag:
                    self.ui.log("回放被中断")
                    break

                self.ui.log(f"执行第 {i+1} 次循环（共 {total_events} 个事件）")
                if i > 0:
                    time.sleep(1)

                start_playback_time = time.perf_counter()
                executed = 0

                for rel_time, etype, data in events:
                    if self.stop_playback_flag:
                        break

                    target_time = start_playback_time + rel_time
                    current_time = time.perf_counter()
                    dt = target_time - current_time

                    if dt > 0:
                        if self.ui.precision_mode.get() and dt < 0.01:
                            while time.perf_counter() < target_time:
                                pass
                        else:
                            sleep_time = max(dt, min_delay)
                            time.sleep(sleep_time)
                    else:
                        time.sleep(min_delay)

                    self._execute_event_with_retry(etype, data)

                    if etype in ('kp', 'kr'):
                        time.sleep(key_stable_delay)

                    executed += 1

                if executed != total_events:
                    self.ui.log(f"⚠️ 第 {i+1} 次循环丢帧：录制 {total_events} 个事件，实际执行 {executed} 个")
                else:
                    self.ui.log(f"✓ 第 {i+1} 次循环完整执行 {executed}/{total_events} 个事件")

                self._reset_input_state()

        except Exception as e:
            self.ui.log(f"回放线程异常: {e}")
        finally:
            self.playback_active = False
            self.stop_playback_flag = False
            self.ui.log("回放结束")
            self.ui.update_status("空闲")
            self.ui.playback_finished()   # UI恢复按钮状态并显示窗口

    # -------------------- 事件执行 --------------------
    def _execute_event_with_retry(self, etype, data, retries=2):
        for attempt in range(retries):
            try:
                if etype == 'kp':
                    key = self.data_to_key(data)
                    if key:
                        self.keyboard_controller.press(key)
                        if not isinstance(key, Key) or key not in [Key.ctrl, Key.ctrl_l, Key.ctrl_r,
                                                                    Key.alt, Key.alt_l, Key.alt_r,
                                                                    Key.shift, Key.shift_l, Key.shift_r,
                                                                    Key.cmd]:
                            time.sleep(0.005)
                elif etype == 'kr':
                    key = self.data_to_key(data)
                    if key:
                        self.keyboard_controller.release(key)
                elif etype == 'mm':
                    x, y = data
                    self.mouse_controller.position = (x, y)
                elif etype == 'mc':
                    x, y, button_str, pressed = data
                    button = getattr(Button, button_str)
                    self.mouse_controller.position = (x, y)
                    if pressed:
                        self.mouse_controller.press(button)
                    else:
                        self.mouse_controller.release(button)
                elif etype == 'ms':
                    x, y, dx, dy = data
                    self.mouse_controller.position = (x, y)
                    self.mouse_controller.scroll(dx, dy)
                return
            except Exception as e:
                if attempt == retries - 1:
                    self.ui.log(f"执行事件出错（已重试{retries}次）{etype}: {e}")
                else:
                    time.sleep(0.005)

    def _reset_input_state(self):
        try:
            for key in [Key.shift, Key.shift_l, Key.shift_r, Key.ctrl, Key.ctrl_l, Key.ctrl_r,
                        Key.alt, Key.alt_l, Key.alt_r, Key.cmd, Key.cmd_l, Key.cmd_r]:
                try:
                    self.keyboard_controller.release(key)
                except:
                    pass
            for btn in [Button.left, Button.middle, Button.right]:
                try:
                    self.mouse_controller.release(btn)
                except:
                    pass
        except Exception as e:
            self.ui.log(f"重置输入状态失败: {e}")

    # -------------------- 按键转换 --------------------
    def data_to_key(self, key_info):
        typ, val = key_info
        try:
            if typ == 'special':
                try:
                    return getattr(Key, val)
                except AttributeError:
                    for k in Key:
                        if k.name == val:
                            return k
                    self.ui.log(f"警告: 无法转换特殊键 '{val}'")
                    return None
            elif typ == 'vk':
                try:
                    return KeyCode.from_vk(val)
                except Exception:
                    self.ui.log(f"通过 vk 转换失败: {val}")
                    return None
            else:
                if val is None:
                    return None
                return KeyCode.from_char(val)
        except Exception as e:
            self.ui.log(f"键转换异常: {e}")
            return None

    # -------------------- 监听器回调（录制） --------------------
    def on_key_press(self, key):
        try:
            if key == Key.esc:
                if self.playback_active:
                    self.stop_playback_flag = True
                    self.ui.log("用户按下ESC，停止回放")
                else:
                    if self.recording:
                        self.stop_recording()
                    self.ui.on_closing()
                return
            if key == Key.f9:
                if self.playback_active:
                    return
                # 快捷键按下默认隐藏窗口（与原始行为一致）
                self.toggle_recording(hide=True)
                return
            if key == Key.f10:
                if self.playback_active:
                    return
                self.ui.start_playback_from_selected()
                return
            if key == Key.f11:
                self.ui.show_log_window()
                return
        except AttributeError:
            pass

        if self.recording and not self.playback_active:
            rel_time = time.time() - self.start_time
            if isinstance(key, Key):
                key_info = ('special', key.name)
            else:
                if hasattr(key, 'vk') and key.vk is not None:
                    key_info = ('vk', key.vk)
                elif key.char is not None:
                    key_info = ('char', key.char)
                else:
                    return
            self.events.append((rel_time, 'kp', key_info))
            self.ui.update_event_count(len(self.events))

    def on_key_release(self, key):
        if key in [Key.esc, Key.f9, Key.f10, Key.f11]:
            return
        if self.recording and not self.playback_active:
            rel_time = time.time() - self.start_time
            if isinstance(key, Key):
                key_info = ('special', key.name)
            else:
                if hasattr(key, 'vk') and key.vk is not None:
                    key_info = ('vk', key.vk)
                elif key.char is not None:
                    key_info = ('char', key.char)
                else:
                    return
            self.events.append((rel_time, 'kr', key_info))
            self.ui.update_event_count(len(self.events))

    def on_mouse_move(self, x, y):
        self.last_mouse_event_time = time.time()
        if self.recording and not self.playback_active:
            try:
                rel_time = time.time() - self.start_time
                self.events.append((rel_time, 'mm', (x, y)))
                self.ui.update_event_count(len(self.events))
            except Exception as e:
                self.ui.log(f"鼠标移动录制错误: {e}")

    def on_mouse_click(self, x, y, button, pressed):
        self.last_mouse_event_time = time.time()
        if self.recording and not self.playback_active:
            try:
                rel_time = time.time() - self.start_time
                button_str = button.name
                self.events.append((rel_time, 'mc', (x, y, button_str, pressed)))
                self.ui.update_event_count(len(self.events))
            except Exception as e:
                self.ui.log(f"鼠标点击录制错误: {e}")

    def on_mouse_scroll(self, x, y, dx, dy):
        self.last_mouse_event_time = time.time()
        if self.recording and not self.playback_active:
            try:
                rel_time = time.time() - self.start_time
                self.events.append((rel_time, 'ms', (x, y, dx, dy)))
                self.ui.update_event_count(len(self.events))
            except Exception as e:
                self.ui.log(f"鼠标滚动录制错误: {e}")

    # -------------------- 清理 --------------------
    def stop_listeners(self):
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        if self.mouse_listener:
            self.mouse_listener.stop()
        self.mouse_monitor_running = False
