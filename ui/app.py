import tkinter as tk
import atexit
from datetime import datetime

from ui import theme
from ui import dialogs
from ui.tooltip import Tooltip
from data import storage
from core.timer_logic import TimerLogic


class TimeTracker:
    def __init__(self, root):
        self.root = root
        self.root.title("Time Tracker")
        self.root.geometry(f"{theme.WINDOW_MAIN_W}x{theme.WINDOW_MAIN_H}")
        self.root.minsize(theme.WINDOW_MAIN_MIN_W, theme.WINDOW_MAIN_MIN_H)
        self.root.configure(bg=theme.BG)
        self.root.resizable(True, True)

        storage.ensure_log_dir()
        storage.migrate_legacy_files()

        self.data = storage.load_time_log()
        self.tasks = storage.load_tasks()
        self.task_data = storage.load_task_log()
        self._task_dialog = None
        self.logic = TimerLogic(self)

        self._build_ui()
        self._tick()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        atexit.register(self.logic.flush_session)

    def _build_ui(self):
        clock_row = tk.Frame(self.root, bg=theme.BG)
        clock_row.pack(fill="x", padx=14, pady=(6, 0))

        self.clock_label = tk.Label(
            clock_row,
            text=self._format_clock(),
            font=theme.FONT_SMALL,
            fg=theme.CLOCK_FG,
            bg=theme.BG,
        )
        self.clock_label.pack(side="right")

        title = tk.Label(
            self.root,
            text="TIME TRACKER",
            font=theme.FONT_TITLE,
            fg=theme.ACCENT,
            bg=theme.BG,
        )
        title.pack(pady=(2, 4))

        self.add_task_btn = tk.Button(
            self.root,
            text="+ Add Task",
            font=theme.FONT_SMALL_BOLD,
            fg=theme.FG,
            bg=theme.BTN_BG,
            activebackground=theme.BTN_ACTIVE,
            activeforeground=theme.FG,
            relief=tk.FLAT,
            padx=14,
            pady=3,
            cursor="hand2",
            command=lambda: dialogs.add_task(self),
        )
        self.add_task_btn.pack(pady=(0, 6))

        self.timer_label = tk.Label(
            self.root,
            text="00:00:00",
            font=theme.FONT_TIMER_MAIN,
            fg=theme.FG,
            bg=theme.BG,
        )
        self.timer_label.pack(pady=(4, 4))

        task_row = tk.Frame(self.root, bg=theme.BG)
        task_row.pack(fill="x", padx=30, pady=(0, 6))

        self.task_var = tk.StringVar(value="Select task...")
        self.task_dropdown = tk.OptionMenu(task_row, self.task_var, "")
        self.task_dropdown.config(
            font=theme.FONT_SMALL_BOLD,
            bg=theme.BTN_BG,
            fg=theme.FG,
            activebackground=theme.BTN_ACTIVE,
            activeforeground=theme.FG,
            relief=tk.FLAT,
            highlightthickness=0,
            bd=0,
            width=18,
            anchor="w",
        )
        self.task_dropdown["menu"].config(
            bg=theme.BTN_BG,
            fg=theme.FG,
            activebackground=theme.BTN_ACTIVE,
            activeforeground=theme.FG,
            font=theme.FONT_SMALL,
            bd=0,
        )
        self.task_dropdown.pack(side="left")

        self.delete_task_btn = tk.Button(
            task_row,
            text="✕",
            font=theme.FONT_SMALL_BOLD,
            fg=theme.STOP_COLOR,
            bg=theme.BTN_BG,
            activebackground=theme.BTN_ACTIVE,
            activeforeground=theme.FG,
            disabledforeground=theme.DIM,
            relief=tk.FLAT,
            bd=0,
            padx=8,
            pady=2,
            cursor="hand2",
            command=lambda: dialogs.delete_task(self),
            state=tk.DISABLED,
        )
        self.delete_task_btn.pack(side="left", padx=(6, 0))
        Tooltip(self.delete_task_btn, "Delete task")

        task_right = tk.Frame(task_row, bg=theme.BG)
        task_right.pack(side="right")

        self.task_timer_label = tk.Label(
            task_right,
            text="00:00:00",
            font=theme.FONT_TIMER_TASK,
            fg=theme.MUTED,
            bg=theme.BG,
        )
        self.task_timer_label.pack(anchor="e")

        self._refresh_task_dropdown()

        self.status_label = tk.Label(
            self.root,
            text="Ready",
            font=theme.FONT_STATUS,
            fg=theme.ACCENT,
            bg=theme.BG,
        )
        self.status_label.pack(pady=(0, 10))

        btn_frame = tk.Frame(self.root, bg=theme.BG)
        btn_frame.pack()

        self.start_btn = self._make_button(
            btn_frame, "START", theme.START_COLOR, self.start
        )
        self.start_btn.grid(row=0, column=0, padx=6)

        self.pause_btn = self._make_button(
            btn_frame, "PAUSE", theme.PAUSE_COLOR, self.pause
        )
        self.pause_btn.grid(row=0, column=1, padx=6)

        self.stop_btn = self._make_button(
            btn_frame, "STOP", theme.STOP_COLOR, self.stop
        )
        self.stop_btn.grid(row=0, column=2, padx=6)

        self.history_btn = tk.Button(
            self.root,
            text="HISTORY",
            font=theme.FONT_SMALL_BOLD,
            fg=theme.FG,
            bg=theme.BTN_BG,
            activebackground=theme.BTN_ACTIVE,
            activeforeground=theme.FG,
            relief=tk.FLAT,
            padx=18,
            pady=4,
            cursor="hand2",
            command=lambda: dialogs.show_history(self),
        )
        self.history_btn.pack(pady=(10, 0))

        self._history_win = None
        self._update_button_states()

    def _make_button(self, parent, text, color, command):
        return tk.Button(
            parent,
            text=text,
            font=theme.FONT_BTN_LARGE,
            fg=theme.BG,
            bg=color,
            activebackground=theme.BTN_ACTIVE,
            activeforeground=theme.FG,
            disabledforeground=theme.DIM,
            relief=tk.FLAT,
            width=8,
            height=2,
            cursor="hand2",
            command=command,
        )

    def _update_button_states(self):
        running = self.logic.running
        self.start_btn.config(state=tk.DISABLED if running else tk.NORMAL)
        self.pause_btn.config(state=tk.NORMAL if running else tk.DISABLED)
        has_time = running or self.logic.elapsed > 0
        self.stop_btn.config(state=tk.NORMAL if has_time else tk.DISABLED)

    def start(self):
        if not self.logic.start():
            return
        self.status_label.config(text="Tracking...")
        self._update_button_states()

    def pause(self):
        if not self.logic.pause():
            return
        self.status_label.config(text="Paused")
        self._update_button_states()

    def stop(self):
        self.logic.stop()
        self._render_task_timer()
        self.status_label.config(text="Ready")
        self.timer_label.config(text="00:00:00")
        self._update_button_states()

    def _on_close(self):
        try:
            self.logic.flush_session()
        finally:
            self.root.destroy()

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
        self.logic.select_task(value, self.tasks)

        if self.logic.current_task is None:
            self.task_timer_label.config(text="00:00:00")
        else:
            self._render_task_timer()

        self.delete_task_btn.config(
            state=tk.NORMAL if self.logic.current_task is not None else tk.DISABLED
        )

    def _render_task_timer(self):
        t = int(self.logic.task_total())
        h, m, s = t // 3600, (t % 3600) // 60, t % 60
        self.task_timer_label.config(text=f"{h:02d}:{m:02d}:{s:02d}")

    def _format_clock(self):
        return datetime.now().strftime("%a, %d %b %Y  %I:%M %p")

    def _tick(self):
        self.clock_label.config(text=self._format_clock())
        total = self.logic.current_total()
        hours = int(total // 3600)
        minutes = int((total % 3600) // 60)
        seconds = int(total % 60)
        self.timer_label.config(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")

        self._render_task_timer()

        self.root.after(1000 if self.logic.running else 200, self._tick)
