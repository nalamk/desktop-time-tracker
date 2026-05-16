import tkinter as tk
import atexit
from datetime import datetime

import customtkinter as ctk

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
        self.clock_label = ctk.CTkLabel(
            self.root,
            text=self._format_clock(),
            font=theme.FONT_SMALL,
            text_color=theme.CLOCK_FG,
        )
        self.clock_label.pack(pady=(18, 4))

        self.add_task_btn = ctk.CTkButton(
            self.root,
            text="+ Add Task",
            font=theme.FONT_SMALL_BOLD,
            text_color=theme.FG,
            fg_color=theme.BTN_BG,
            hover_color=theme.BTN_ACTIVE,
            width=110,
            height=28,
            cursor="hand2",
            command=lambda: dialogs.add_task(self),
        )
        self.add_task_btn.pack(pady=(0, 6))

        self.timer_label = ctk.CTkLabel(
            self.root,
            text="00:00:00",
            font=theme.FONT_TIMER_MAIN,
            text_color=theme.FG,
        )
        self.timer_label.pack(pady=(4, 4))

        task_row = ctk.CTkFrame(self.root, fg_color="transparent")
        task_row.pack(fill="x", padx=30, pady=(0, 6))

        self.task_var = tk.StringVar(value="Select task...")
        self.task_dropdown = ctk.CTkComboBox(
            task_row,
            values=["Select task..."],
            variable=self.task_var,
            command=self._select_task,
            state="readonly",
            font=theme.FONT_SMALL_BOLD,
            fg_color=theme.BTN_BG,
            border_color=theme.BTN_BG,
            button_color=theme.BTN_BG,
            button_hover_color=theme.BTN_ACTIVE,
            text_color=theme.FG,
            dropdown_fg_color=theme.BTN_BG,
            dropdown_hover_color=theme.BTN_ACTIVE,
            dropdown_text_color=theme.FG,
            dropdown_font=theme.FONT_SMALL,
            width=160,
            justify="left",
        )
        self.task_dropdown.pack(side="left")

        self.delete_task_btn = ctk.CTkButton(
            task_row,
            text="✕",
            font=theme.FONT_SMALL_BOLD,
            text_color=theme.STOP_COLOR,
            fg_color=theme.BTN_BG,
            hover_color=theme.BTN_ACTIVE,
            width=32,
            height=28,
            cursor="hand2",
            command=lambda: dialogs.delete_task(self),
        )
        Tooltip(self.delete_task_btn, "Delete task")

        task_right = ctk.CTkFrame(task_row, fg_color="transparent")
        task_right.pack(side="right")

        self.task_timer_label = ctk.CTkLabel(
            task_right,
            text="00:00:00",
            font=theme.FONT_TIMER_TASK,
            text_color=theme.FG,
        )
        self.task_timer_label.pack(anchor="e")

        self._refresh_task_dropdown()

        self.status_label = ctk.CTkLabel(
            self.root,
            text="Ready",
            font=theme.FONT_STATUS,
            text_color=theme.ACCENT,
        )
        self.status_label.pack(pady=(0, 10))

        btn_frame = ctk.CTkFrame(self.root, fg_color="transparent")
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

        self.history_btn = ctk.CTkButton(
            self.root,
            text="History",
            font=theme.FONT_SMALL_BOLD,
            text_color=theme.ACCENT,
            fg_color="transparent",
            hover_color=theme.BTN_BG,
            width=70,
            height=24,
            cursor="hand2",
            command=lambda: dialogs.show_history(self),
        )
        self.history_btn.place(relx=1.0, x=-12, y=12, anchor="ne")

        self._history_win = None
        self._update_button_states()

    def _make_button(self, parent, text, color, command):
        return ctk.CTkButton(
            parent,
            text=text,
            font=theme.FONT_BTN_LARGE,
            text_color=theme.BG,
            fg_color=color,
            hover_color=theme.BTN_ACTIVE,
            text_color_disabled=theme.DIM,
            corner_radius=6,
            width=92,
            height=52,
            cursor="hand2",
            command=command,
        )

    def _update_button_states(self):
        running = self.logic.running
        self.start_btn.configure(state="disabled" if running else "normal")
        self.pause_btn.configure(state="normal" if running else "disabled")
        has_time = running or self.logic.elapsed > 0
        self.stop_btn.configure(state="normal" if has_time else "disabled")

    def start(self):
        if not self.logic.start():
            return
        self.status_label.configure(text="Tracking...")
        self._update_button_states()

    def pause(self):
        if not self.logic.pause():
            return
        self.status_label.configure(text="Paused")
        self._update_button_states()

    def stop(self):
        self.logic.stop()
        self._render_task_timer()
        self.status_label.configure(text="Ready")
        self.timer_label.configure(text="00:00:00")
        self._update_button_states()

    def _on_close(self):
        try:
            self.logic.flush_session()
        finally:
            self.root.destroy()

    def _refresh_task_dropdown(self):
        self.task_dropdown.configure(values=["Select task..."] + self.tasks)

    def _select_task(self, value):
        self.task_var.set(value)
        self.logic.select_task(value, self.tasks)

        if self.logic.current_task is None:
            self.task_timer_label.configure(text="00:00:00")
        else:
            self._render_task_timer()

        if self.logic.current_task is not None:
            self.delete_task_btn.pack(side="left", padx=(6, 0))
        else:
            self.delete_task_btn.pack_forget()

    def _render_task_timer(self):
        t = int(self.logic.task_total())
        h, m, s = t // 3600, (t % 3600) // 60, t % 60
        self.task_timer_label.configure(text=f"{h:02d}:{m:02d}:{s:02d}")

    def _format_clock(self):
        return datetime.now().strftime("%a, %d %b %Y  %I:%M %p")

    def _tick(self):
        self.clock_label.configure(text=self._format_clock())
        total = self.logic.current_total()
        hours = int(total // 3600)
        minutes = int((total % 3600) // 60)
        seconds = int(total % 60)
        self.timer_label.configure(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")

        self._render_task_timer()

        self.root.after(1000 if self.logic.running else 200, self._tick)
