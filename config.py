# config.py
# 配置和数据的读写（JSON 格式），所有文件保存在 data/ 目录下

import json
import os

# 数据目录
DATA_DIR = "data"

def _ensure_data_dir():
    """确保数据目录存在"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def _get_path(filename):
    """获取数据目录下的完整路径"""
    _ensure_data_dir()
    return os.path.join(DATA_DIR, filename)

def load_settings(settings_file="settings.json"):
    full_path = _get_path(settings_file)
    if os.path.exists(full_path):
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_settings(settings, settings_file="settings.json"):
    full_path = _get_path(settings_file)
    try:
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        print(f"保存设置失败: {e}")

def load_recordings(data_file="recordings.json"):
    full_path = _get_path(data_file)
    if os.path.exists(full_path):
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    return []

def save_recordings(recordings, data_file="recordings.json"):
    full_path = _get_path(data_file)
    try:
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(recordings, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"保存录制失败: {e}")

def load_window_geometry(geometry_file="window_geometry.json"):
    full_path = _get_path(geometry_file)
    if os.path.exists(full_path):
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception:
            pass
    return None

def save_window_geometry(geometry, geometry_file="window_geometry.json"):
    full_path = _get_path(geometry_file)
    try:
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(geometry)
    except Exception as e:
        print(f"保存窗口位置失败: {e}")
