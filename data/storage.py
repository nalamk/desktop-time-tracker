import json
import os
import shutil


LOG_DIR = r"C:\time_tracker\logs"
LOG_FILE = r"C:\time_tracker\logs\time_log.json"
TASKS_FILE = r"C:\time_tracker\logs\tasks.json"
TASK_LOG_FILE = r"C:\time_tracker\logs\task_log.json"
LEGACY_DIRS = (r"C:\WINDOWS\system32", r"C:\Windows\System32")
LEGACY_FILES = ("time_log.json", "tasks.json", "task_log.json")


def ensure_log_dir():
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
    except OSError:
        pass


def migrate_legacy_files():
    try:
        for legacy_dir in LEGACY_DIRS:
            if not os.path.isdir(legacy_dir):
                continue
            if os.path.normcase(os.path.abspath(legacy_dir)) == os.path.normcase(
                os.path.abspath(LOG_DIR)
            ):
                continue
            for name in LEGACY_FILES:
                src = os.path.join(legacy_dir, name)
                dst = os.path.join(LOG_DIR, name)
                if os.path.isfile(src) and not os.path.exists(dst):
                    try:
                        shutil.move(src, dst)
                    except (OSError, shutil.Error):
                        pass
    except OSError:
        pass


def load_time_log():
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)
            if isinstance(loaded, dict):
                return loaded
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return {}


def save_time_log(data):
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError:
        pass


def load_task_log():
    try:
        with open(TASK_LOG_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)
            if isinstance(loaded, dict):
                return loaded
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return {}


def save_task_log(data):
    try:
        with open(TASK_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError:
        pass


def load_tasks_doc():
    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)
            if isinstance(loaded, list):
                return [str(t) for t in loaded], None
            if isinstance(loaded, dict):
                raw_tasks = loaded.get("tasks", [])
                if not isinstance(raw_tasks, list):
                    raw_tasks = []
                last = loaded.get("last_selected")
                if not isinstance(last, str):
                    last = None
                return [str(t) for t in raw_tasks], last
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return [], None


def save_tasks_doc(tasks, last_selected):
    try:
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {"tasks": tasks, "last_selected": last_selected},
                f,
                indent=2,
            )
    except OSError:
        pass
