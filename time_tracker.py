import tkinter as tk
from tkinter import ttk
import time
import json
import os
import shutil
import atexit
from datetime import datetime, timedelta


class Tooltip:
    def __init__(self, widget, text, delay=400):
        self.widget = widget
        self.text = text
        self.delay = delay
        self._tipwin = None
        self._after_id = None
        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        widget.bind("<ButtonPress>", self._on_leave, add="+")

    def _on_enter(self, _e=None):
        self._unschedule()
        self._after_id = self.widget.after(self.delay, self._show)

    def _on_leave(self, _e=None):
        self._unschedule()
        self._hide()

    def _unschedule(self):
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _show(self):
        if self._tipwin is not None:
            return
        try:
            x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
            tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")
            tk.Label(
                tw,
                text=self.text,
                font=("Segoe UI", 9),
                fg="#cdd6f4",
                bg="#313244",
                relief=tk.SOLID,
                bd=1,
                padx=8,
                pady=3,
            ).pack()
            self._tipwin = tw
        except Exception:
            self._tipwin = None

    def _hide(self):
        if self._tipwin is not None:
            try:
                self._tipwin.destroy()
            except Exception:
                pass
            self._tipwin = None


class TimeTracker:
    BG = "#1e1e2e"
    FG = "#cdd6f4"
    ACCENT = "#89b4fa"
    BTN_BG = "#313244"
    BTN_ACTIVE = "#45475a"
    START_COLOR = "#a6e3a1"
    PAUSE_COLOR = "#f9e2af"
    STOP_COLOR = "#f38ba8"

    LOG_DIR = r"C:\time_tracker\logs"
    LOG_FILE = r"C:\time_tracker\logs\time_log.json"
    TASKS_FILE = r"C:\time_tracker\logs\tasks.json"
    TASK_LOG_FILE = r"C:\time_tracker\logs\task_log.json"
    LEGACY_DIRS = (r"C:\WINDOWS\system32", r"C:\Windows\System32")
    LEGACY_FILES = ("time_log.json", "tasks.json", "task_log.json")

    def __init__(self, root):
        self.root = root
        self.root.title("Time Tracker")
        self.root.geometry("520x500")
        self.root.minsize(520, 480)
        self.root.configure(bg=self.BG)
        self.root.resizable(True, True)

        try:
            os.makedirs(self.LOG_DIR, exist_ok=True)
        except OSError:
            pass

        self._migrate_legacy_files()

        self.running = False
        self.start_time = 0.0
        self.elapsed = 0.0
        self.session_start = None

        self.data = self._load_data()
        self.tasks = self._load_tasks()
        self._task_dialog = None
        self.current_task = None
        self.task_start_time = 0.0
        self.task_elapsed = 0.0
        self.task_baseline = 0
        self.task_session_start = None
        self.task_data = self._load_task_data()

        self._build_ui()
        self._tick()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        atexit.register(self._flush_session)

    def _build_ui(self):
        clock_row = tk.Frame(self.root, bg=self.BG)
        clock_row.pack(fill="x", padx=14, pady=(6, 0))

        self.clock_label = tk.Label(
            clock_row,
            text=self._format_clock(),
            font=("Segoe UI", 10),
            fg="#bac2de",
            bg=self.BG,
        )
        self.clock_label.pack(side="right")

        title = tk.Label(
            self.root,
            text="TIME TRACKER",
            font=("Segoe UI", 18, "bold"),
            fg=self.ACCENT,
            bg=self.BG,
        )
        title.pack(pady=(2, 4))

        self.add_task_btn = tk.Button(
            self.root,
            text="+ Add Task",
            font=("Segoe UI", 10, "bold"),
            fg=self.FG,
            bg=self.BTN_BG,
            activebackground=self.BTN_ACTIVE,
            activeforeground=self.FG,
            relief=tk.FLAT,
            padx=14,
            pady=3,
            cursor="hand2",
            command=self._add_task_dialog,
        )
        self.add_task_btn.pack(pady=(0, 6))

        self.timer_label = tk.Label(
            self.root,
            text="00:00:00",
            font=("Consolas", 64, "bold"),
            fg=self.FG,
            bg=self.BG,
        )
        self.timer_label.pack(pady=(4, 4))

        task_row = tk.Frame(self.root, bg=self.BG)
        task_row.pack(fill="x", padx=30, pady=(0, 6))

        self.task_var = tk.StringVar(value="Select task...")
        self.task_dropdown = tk.OptionMenu(task_row, self.task_var, "")
        self.task_dropdown.config(
            font=("Segoe UI", 10, "bold"),
            bg=self.BTN_BG,
            fg=self.FG,
            activebackground=self.BTN_ACTIVE,
            activeforeground=self.FG,
            relief=tk.FLAT,
            highlightthickness=0,
            bd=0,
            width=18,
            anchor="w",
        )
        self.task_dropdown["menu"].config(
            bg=self.BTN_BG,
            fg=self.FG,
            activebackground=self.BTN_ACTIVE,
            activeforeground=self.FG,
            font=("Segoe UI", 10),
            bd=0,
        )
        self.task_dropdown.pack(side="left")

        self.delete_task_btn = tk.Button(
            task_row,
            text="✕",
            font=("Segoe UI", 10, "bold"),
            fg=self.STOP_COLOR,
            bg=self.BTN_BG,
            activebackground=self.BTN_ACTIVE,
            activeforeground=self.FG,
            disabledforeground="#6c7086",
            relief=tk.FLAT,
            bd=0,
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._delete_current_task,
            state=tk.DISABLED,
        )
        self.delete_task_btn.pack(side="left", padx=(6, 0))
        Tooltip(self.delete_task_btn, "Delete task")

        task_right = tk.Frame(task_row, bg=self.BG)
        task_right.pack(side="right")

        self.task_timer_label = tk.Label(
            task_right,
            text="00:00:00",
            font=("Consolas", 20, "bold"),
            fg="#a6adc8",
            bg=self.BG,
        )
        self.task_timer_label.pack(anchor="e")

        self._refresh_task_dropdown()

        self.status_label = tk.Label(
            self.root,
            text="Ready",
            font=("Segoe UI", 12),
            fg=self.ACCENT,
            bg=self.BG,
        )
        self.status_label.pack(pady=(0, 10))

        btn_frame = tk.Frame(self.root, bg=self.BG)
        btn_frame.pack()

        self.start_btn = self._make_button(
            btn_frame, "START", self.START_COLOR, self.start
        )
        self.start_btn.grid(row=0, column=0, padx=6)

        self.pause_btn = self._make_button(
            btn_frame, "PAUSE", self.PAUSE_COLOR, self.pause
        )
        self.pause_btn.grid(row=0, column=1, padx=6)

        self.stop_btn = self._make_button(
            btn_frame, "STOP", self.STOP_COLOR, self.stop
        )
        self.stop_btn.grid(row=0, column=2, padx=6)

        self.history_btn = tk.Button(
            self.root,
            text="HISTORY",
            font=("Segoe UI", 10, "bold"),
            fg=self.FG,
            bg=self.BTN_BG,
            activebackground=self.BTN_ACTIVE,
            activeforeground=self.FG,
            relief=tk.FLAT,
            padx=18,
            pady=4,
            cursor="hand2",
            command=self._show_history,
        )
        self.history_btn.pack(pady=(10, 0))

        self._history_win = None
        self._update_button_states()

    def _make_button(self, parent, text, color, command):
        return tk.Button(
            parent,
            text=text,
            font=("Segoe UI", 16, "bold"),
            fg=self.BG,
            bg=color,
            activebackground=self.BTN_ACTIVE,
            activeforeground=self.FG,
            disabledforeground="#6c7086",
            relief=tk.FLAT,
            width=8,
            height=2,
            cursor="hand2",
            command=command,
        )

    def _current_total(self):
        return self.elapsed + (time.time() - self.start_time if self.running else 0)

    def _update_button_states(self):
        self.start_btn.config(state=tk.DISABLED if self.running else tk.NORMAL)
        self.pause_btn.config(state=tk.NORMAL if self.running else tk.DISABLED)
        has_time = self.running or self.elapsed > 0
        self.stop_btn.config(state=tk.NORMAL if has_time else tk.DISABLED)

    def start(self):
        if self.running:
            return
        if self.session_start is None:
            self.session_start = datetime.now()
        self.start_time = time.time()
        self.running = True
        if self.current_task is not None:
            self.task_start_time = time.time()
            if self.task_session_start is None:
                self.task_session_start = datetime.now()
        self.status_label.config(text="Tracking...")
        self._update_button_states()

    def pause(self):
        if not self.running:
            return
        self.elapsed += time.time() - self.start_time
        if self.current_task is not None:
            self.task_elapsed += time.time() - self.task_start_time
            self.task_start_time = 0.0
        self.running = False
        self.status_label.config(text="Paused")
        self._update_button_states()

    def stop(self):
        if self.running:
            self.elapsed += time.time() - self.start_time
            if self.current_task is not None and self.task_start_time > 0:
                self.task_elapsed += time.time() - self.task_start_time
            self.running = False
        self._record_session()
        self._record_task_session()
        self.elapsed = 0.0
        self.start_time = 0.0
        self.task_elapsed = 0.0
        self.task_start_time = 0.0
        if self.current_task is not None:
            self.task_baseline = self._saved_today_for(self.current_task)
        else:
            self.task_baseline = 0
        self._render_task_timer()
        self.status_label.config(text="Ready")
        self.timer_label.config(text="00:00:00")
        self._update_button_states()

    def _on_close(self):
        try:
            self._flush_session()
        finally:
            self.root.destroy()

    def _flush_session(self):
        try:
            if self.session_start is None and self.task_session_start is None:
                return
            if self.running:
                self.elapsed += time.time() - self.start_time
                if self.current_task is not None and self.task_start_time > 0:
                    self.task_elapsed += time.time() - self.task_start_time
                self.running = False
            self._record_session()
            self._record_task_session()
        except Exception:
            pass

    def _migrate_legacy_files(self):
        try:
            for legacy_dir in self.LEGACY_DIRS:
                if not os.path.isdir(legacy_dir):
                    continue
                if os.path.normcase(os.path.abspath(legacy_dir)) == os.path.normcase(
                    os.path.abspath(self.LOG_DIR)
                ):
                    continue
                for name in self.LEGACY_FILES:
                    src = os.path.join(legacy_dir, name)
                    dst = os.path.join(self.LOG_DIR, name)
                    if os.path.isfile(src) and not os.path.exists(dst):
                        try:
                            shutil.move(src, dst)
                        except (OSError, shutil.Error):
                            pass
        except OSError:
            pass

    def _load_data(self):
        try:
            with open(self.LOG_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    return loaded
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            pass
        return {}

    def _save_data(self):
        try:
            with open(self.LOG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except OSError:
            pass

    def _load_task_data(self):
        try:
            with open(self.TASK_LOG_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    return loaded
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            pass
        return {}

    def _save_task_data(self):
        try:
            with open(self.TASK_LOG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.task_data, f, indent=2)
        except OSError:
            pass

    def _record_task_session(self):
        if self.task_session_start is None or self.current_task is None:
            self.task_session_start = None
            return
        duration = int(self.task_elapsed)
        if duration <= 0:
            self.task_session_start = None
            return
        end_dt = datetime.now()
        date_key = self.task_session_start.strftime("%Y-%m-%d")
        day = self.task_data.setdefault(date_key, {})
        entry = day.setdefault(
            self.current_task, {"total_seconds": 0, "sessions": []}
        )
        entry.setdefault("sessions", []).append(
            {
                "start": self.task_session_start.isoformat(timespec="seconds"),
                "end": end_dt.isoformat(timespec="seconds"),
                "duration_seconds": duration,
            }
        )
        entry["total_seconds"] = int(entry.get("total_seconds", 0)) + duration
        self._save_task_data()
        self.task_session_start = None

    def _record_session(self):
        if self.session_start is None:
            self.session_start = None
            return
        duration = int(self.elapsed)
        if duration <= 0:
            self.session_start = None
            return
        end_dt = datetime.now()
        date_key = self.session_start.strftime("%Y-%m-%d")
        day = self.data.setdefault(
            date_key, {"total_seconds": 0, "sessions": []}
        )
        day.setdefault("sessions", []).append(
            {
                "start": self.session_start.isoformat(timespec="seconds"),
                "end": end_dt.isoformat(timespec="seconds"),
                "duration_seconds": duration,
            }
        )
        day["total_seconds"] = int(day.get("total_seconds", 0)) + duration
        self._save_data()
        self.session_start = None

    def _refresh_task_dropdown(self):
        menu = self.task_dropdown["menu"]
        menu.delete(0, "end")
        for option in ["Select task..."] + self.tasks:
            menu.add_command(
                label=option,
                command=lambda val=option: self._select_task(val),
            )

    def _select_task(self, value):
        self.task_var.set(value)

        if self.current_task is not None:
            if self.running and self.task_start_time > 0:
                self.task_elapsed += time.time() - self.task_start_time
            self._record_task_session()

        if value == "Select task..." or value not in self.tasks:
            self.current_task = None
            self.task_start_time = 0.0
            self.task_elapsed = 0.0
            self.task_baseline = 0
            self.task_session_start = None
            self.task_timer_label.config(text="00:00:00")
        else:
            self.current_task = value
            self.task_elapsed = 0.0
            self.task_baseline = self._saved_today_for(value)
            if self.running:
                self.task_start_time = time.time()
                self.task_session_start = datetime.now()
            else:
                self.task_start_time = 0.0
                self.task_session_start = None
            self._render_task_timer()

        self.delete_task_btn.config(
            state=tk.NORMAL if self.current_task is not None else tk.DISABLED
        )

    def _saved_today_for(self, task_name):
        if not task_name:
            return 0
        date_key = datetime.now().strftime("%Y-%m-%d")
        return int(
            self.task_data.get(date_key, {})
            .get(task_name, {})
            .get("total_seconds", 0)
        )

    def _task_live_session(self):
        if self.current_task is None:
            return 0
        active = (
            time.time() - self.task_start_time
            if self.running and self.task_start_time > 0
            else 0
        )
        return self.task_elapsed + active

    def _task_total(self):
        if self.current_task is None:
            return 0
        return self.task_baseline + self._task_live_session()

    def _render_task_timer(self):
        t = int(self._task_total())
        h, m, s = t // 3600, (t % 3600) // 60, t % 60
        self.task_timer_label.config(text=f"{h:02d}:{m:02d}:{s:02d}")

    def _load_tasks(self):
        try:
            with open(self.TASKS_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, list):
                    return [str(t) for t in loaded]
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            pass
        return []

    def _save_tasks(self):
        try:
            with open(self.TASKS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.tasks, f, indent=2)
        except OSError:
            pass

    def _center_popup(self, win, width, height):
        win.transient(self.root)
        self.root.update_idletasks()
        rx = self.root.winfo_x()
        ry = self.root.winfo_y()
        rw = self.root.winfo_width()
        rh = self.root.winfo_height()
        x = max(0, rx + (rw - width) // 2)
        y = max(0, ry + (rh - height) // 2)
        win.geometry(f"{width}x{height}+{x}+{y}")
        win.grab_set()

    def _delete_current_task(self):
        if self.current_task is None or self.current_task not in self.tasks:
            return
        task_name = self.current_task

        win = tk.Toplevel(self.root)
        win.title("Confirm Delete")
        win.configure(bg=self.BG)
        win.resizable(False, False)
        self._center_popup(win, 400, 190)

        tk.Label(
            win,
            text=f"Delete task '{task_name}'?",
            font=("Segoe UI", 12, "bold"),
            fg=self.FG, bg=self.BG,
        ).pack(pady=(28, 6), padx=20)

        tk.Label(
            win,
            text="This will also remove its time logs.",
            font=("Segoe UI", 10),
            fg="#a6adc8", bg=self.BG,
        ).pack(pady=(0, 18), padx=20)

        btn_frame = tk.Frame(win, bg=self.BG)
        btn_frame.pack()

        def do_delete():
            win.destroy()
            self._perform_task_delete(task_name)

        delete_btn = tk.Button(
            btn_frame, text="Delete",
            font=("Segoe UI", 11, "bold"),
            fg=self.BG, bg=self.STOP_COLOR,
            activebackground=self.BTN_ACTIVE, activeforeground=self.FG,
            relief=tk.FLAT, cursor="hand2",
            padx=22, pady=6,
            command=do_delete,
        )
        delete_btn.grid(row=0, column=0, padx=8)

        cancel_btn = tk.Button(
            btn_frame, text="Cancel",
            font=("Segoe UI", 11, "bold"),
            fg=self.FG, bg=self.BTN_BG,
            activebackground=self.BTN_ACTIVE, activeforeground=self.FG,
            relief=tk.FLAT, cursor="hand2",
            padx=22, pady=6,
            command=win.destroy,
        )
        cancel_btn.grid(row=0, column=1, padx=8)

        win.bind("<Escape>", lambda _e: win.destroy())
        cancel_btn.focus_set()

    def _perform_task_delete(self, task_name):
        if self.current_task == task_name:
            self.task_session_start = None
            self.current_task = None
            self.task_elapsed = 0.0
            self.task_start_time = 0.0
            self.task_baseline = 0
            self.task_var.set("Select task...")
            self.task_timer_label.config(text="00:00:00")
            self.delete_task_btn.config(state=tk.DISABLED)

        if task_name in self.tasks:
            self.tasks = [t for t in self.tasks if t != task_name]
            self._save_tasks()

        changed = False
        for date_key in list(self.task_data.keys()):
            day = self.task_data.get(date_key, {})
            if task_name in day:
                del day[task_name]
                changed = True
                if not day:
                    del self.task_data[date_key]
        if changed:
            self._save_task_data()

        self._refresh_task_dropdown()

    def _add_task_dialog(self):
        if self._task_dialog is not None and self._task_dialog.winfo_exists():
            self._task_dialog.lift()
            self._task_dialog.focus_force()
            return

        win = tk.Toplevel(self.root)
        self._task_dialog = win
        win.title("Add Task")
        win.configure(bg=self.BG)
        win.resizable(False, False)
        self._center_popup(win, 360, 200)

        tk.Label(
            win, text="Task name",
            font=("Segoe UI", 14, "bold"),
            fg=self.ACCENT, bg=self.BG,
        ).pack(pady=(22, 10))

        entry = tk.Entry(
            win,
            font=("Segoe UI", 13),
            bg=self.BTN_BG,
            fg=self.FG,
            insertbackground=self.FG,
            relief=tk.FLAT,
            width=28,
            justify="center",
        )
        entry.pack(ipady=8, padx=20)
        entry.focus_set()

        def save(_event=None):
            name = entry.get().strip()
            if not name:
                return
            self.tasks.append(name)
            self._save_tasks()
            self._refresh_task_dropdown()
            win.destroy()

        save_btn = tk.Button(
            win, text="Save",
            font=("Segoe UI", 12, "bold"),
            fg=self.BG, bg=self.START_COLOR,
            activebackground=self.BTN_ACTIVE,
            activeforeground=self.FG,
            relief=tk.FLAT, cursor="hand2",
            padx=24, pady=6,
            command=save,
        )
        save_btn.pack(pady=20)

        entry.bind("<Return>", save)
        win.bind("<Escape>", lambda e: win.destroy())

    def _show_history(self):
        if self._history_win is not None and self._history_win.winfo_exists():
            self._history_win.lift()
            self._history_win.focus_force()
            return

        win = tk.Toplevel(self.root)
        self._history_win = win
        win.title("History")
        win.configure(bg=self.BG)
        win.resizable(False, False)
        self._center_popup(win, 420, 560)

        header = tk.Label(
            win,
            text="Last 14 Days",
            font=("Segoe UI", 18, "bold"),
            fg=self.ACCENT,
            bg=self.BG,
        )
        header.pack(pady=(20, 5))

        subhead_row = tk.Frame(win, bg=self.BG)
        subhead_row.pack(fill="x", padx=25, pady=(10, 5))
        tk.Label(
            subhead_row, text="Date",
            font=("Segoe UI", 10, "bold"),
            fg="#a6adc8", bg=self.BG,
        ).pack(side="left")
        tk.Label(
            subhead_row, text="Time",
            font=("Segoe UI", 10, "bold"),
            fg="#a6adc8", bg=self.BG,
        ).pack(side="right")

        sep = tk.Frame(win, bg="#45475a", height=1)
        sep.pack(fill="x", padx=25)

        container = tk.Frame(win, bg=self.BG)
        container.pack(fill="both", expand=True, padx=(25, 8), pady=(8, 16))

        canvas = tk.Canvas(
            container, bg=self.BG, highlightthickness=0, bd=0
        )
        scrollbar = tk.Scrollbar(
            container, orient="vertical", command=canvas.yview,
            bg=self.BTN_BG, activebackground=self.BTN_ACTIVE,
            troughcolor=self.BG, bd=0, relief=tk.FLAT, width=12,
        )
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        list_frame = tk.Frame(canvas, bg=self.BG)
        canvas_window = canvas.create_window(
            (0, 0), window=list_frame, anchor="nw"
        )

        def _on_frame_config(_e):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_config(e):
            canvas.itemconfig(canvas_window, width=e.width)

        list_frame.bind("<Configure>", _on_frame_config)
        canvas.bind("<Configure>", _on_canvas_config)

        def _on_wheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

        canvas.bind("<Enter>", lambda _e: canvas.bind_all("<MouseWheel>", _on_wheel))
        canvas.bind("<Leave>", lambda _e: canvas.unbind_all("<MouseWheel>"))

        def _on_close():
            try:
                canvas.unbind_all("<MouseWheel>")
            except Exception:
                pass
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", _on_close)

        today = datetime.now().date()
        for i in range(14):
            d = today - timedelta(days=i)
            date_key = d.strftime("%Y-%m-%d")
            total = int(self.data.get(date_key, {}).get("total_seconds", 0))
            if i == 0:
                total += int(self._current_total())
            h, m = total // 3600, (total % 3600) // 60

            day_frame = tk.Frame(list_frame, bg=self.BG)
            day_frame.pack(fill="x", pady=(8, 2))

            date_row = tk.Frame(day_frame, bg=self.BG)
            date_row.pack(fill="x")

            date_text = d.strftime("%a  %Y-%m-%d")
            if i == 0:
                date_text += "  (today)"
            tk.Label(
                date_row, text=date_text,
                font=("Consolas", 11, "bold"),
                fg=self.FG, bg=self.BG, anchor="w",
            ).pack(side="left")

            time_color = self.ACCENT if total > 0 else "#6c7086"
            tk.Label(
                date_row, text=f"{h}h {m:02d}m",
                font=("Consolas", 11, "bold"),
                fg=time_color, bg=self.BG, anchor="e",
            ).pack(side="right")

            day_tasks = {
                name: int(e.get("total_seconds", 0))
                for name, e in self.task_data.get(date_key, {}).items()
            }
            if i == 0 and self.current_task is not None:
                live = int(self._task_live_session())
                if live > 0:
                    day_tasks[self.current_task] = (
                        day_tasks.get(self.current_task, 0) + live
                    )

            items = sorted(
                ((n, s) for n, s in day_tasks.items() if s > 0),
                key=lambda x: -x[1],
            )
            for name, secs in items:
                th, tm = secs // 3600, (secs % 3600) // 60
                trow = tk.Frame(day_frame, bg=self.BG)
                trow.pack(fill="x", padx=(20, 0), pady=1)
                tk.Label(
                    trow, text=f"•  {name}",
                    font=("Segoe UI", 10),
                    fg="#a6adc8", bg=self.BG, anchor="w",
                ).pack(side="left")
                tk.Label(
                    trow, text=f"{th}h {tm:02d}m",
                    font=("Consolas", 10),
                    fg="#a6adc8", bg=self.BG, anchor="e",
                ).pack(side="right")

    def _format_clock(self):
        return datetime.now().strftime("%a, %d %b %Y  %I:%M %p")

    def _tick(self):
        self.clock_label.config(text=self._format_clock())
        total = self._current_total()
        hours = int(total // 3600)
        minutes = int((total % 3600) // 60)
        seconds = int(total % 60)
        self.timer_label.config(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")

        self._render_task_timer()

        self.root.after(1000 if self.running else 200, self._tick)


if __name__ == "__main__":
    root = tk.Tk()
    TimeTracker(root)
    root.mainloop()
