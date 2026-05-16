from datetime import datetime, timedelta

import customtkinter as ctk

from ui import theme
from data import storage


def center_popup(root, win, width, height):
    win.transient(root)
    root.update_idletasks()
    rx = root.winfo_x()
    ry = root.winfo_y()
    rw = root.winfo_width()
    rh = root.winfo_height()
    x = max(0, rx + (rw - width) // 2)
    y = max(0, ry + (rh - height) // 2)
    win.geometry(f"{width}x{height}+{x}+{y}")
    win.grab_set()


def add_task(tracker):
    if tracker._task_dialog is not None and tracker._task_dialog.winfo_exists():
        tracker._task_dialog.lift()
        tracker._task_dialog.focus_force()
        return

    win = ctk.CTkToplevel(tracker.root)
    tracker._task_dialog = win
    win.title("Add Task")
    win.configure(fg_color=theme.BG)
    win.resizable(False, False)
    center_popup(tracker.root, win, theme.DIALOG_ADDTASK_W, theme.DIALOG_ADDTASK_H)

    ctk.CTkLabel(
        win, text="Task name",
        font=theme.FONT_DIALOG_LABEL,
        text_color=theme.ACCENT,
    ).pack(pady=(22, 10))

    entry = ctk.CTkEntry(
        win,
        font=theme.FONT_INPUT,
        fg_color=theme.BTN_BG,
        text_color=theme.FG,
        border_color=theme.BTN_BG,
        border_width=0,
        width=280,
        height=40,
        justify="center",
    )
    entry.pack(padx=20)
    entry.focus_set()

    def save(_event=None):
        name = entry.get().strip()
        if not name:
            return
        tracker.tasks.append(name)
        storage.save_tasks(tracker.tasks)
        tracker._refresh_task_dropdown()
        win.destroy()

    save_btn = ctk.CTkButton(
        win, text="Save",
        font=theme.FONT_BTN_DIALOG,
        text_color=theme.BG,
        fg_color=theme.START_COLOR,
        hover_color=theme.BTN_ACTIVE,
        cursor="hand2",
        width=120, height=36,
        command=save,
    )
    save_btn.pack(pady=20)

    entry.bind("<Return>", save)
    win.bind("<Escape>", lambda e: win.destroy())


def delete_task(tracker):
    if tracker.logic.current_task is None or tracker.logic.current_task not in tracker.tasks:
        return
    task_name = tracker.logic.current_task

    win = ctk.CTkToplevel(tracker.root)
    win.title("Confirm Delete")
    win.configure(fg_color=theme.BG)
    win.resizable(False, False)
    center_popup(tracker.root, win, theme.DIALOG_CONFIRM_W, theme.DIALOG_CONFIRM_H)

    ctk.CTkLabel(
        win,
        text=f"Delete task '{task_name}'?",
        font=theme.FONT_BTN_DIALOG,
        text_color=theme.FG,
    ).pack(pady=(28, 6), padx=20)

    ctk.CTkLabel(
        win,
        text="This will also remove its time logs.",
        font=theme.FONT_SMALL,
        text_color=theme.MUTED,
    ).pack(pady=(0, 18), padx=20)

    btn_frame = ctk.CTkFrame(win, fg_color="transparent")
    btn_frame.pack()

    def do_delete():
        win.destroy()
        perform_task_delete(tracker, task_name)

    delete_btn = ctk.CTkButton(
        btn_frame, text="Delete",
        font=theme.FONT_BTN_CONFIRM,
        text_color=theme.BG,
        fg_color=theme.STOP_COLOR,
        hover_color=theme.BTN_ACTIVE,
        cursor="hand2",
        width=110, height=36,
        command=do_delete,
    )
    delete_btn.grid(row=0, column=0, padx=8)

    cancel_btn = ctk.CTkButton(
        btn_frame, text="Cancel",
        font=theme.FONT_BTN_CONFIRM,
        text_color=theme.FG,
        fg_color=theme.BTN_BG,
        hover_color=theme.BTN_ACTIVE,
        cursor="hand2",
        width=110, height=36,
        command=win.destroy,
    )
    cancel_btn.grid(row=0, column=1, padx=8)

    win.bind("<Escape>", lambda _e: win.destroy())
    cancel_btn.focus_set()


def perform_task_delete(tracker, task_name):
    if tracker.logic.current_task == task_name:
        tracker.logic.task_session_start = None
        tracker.logic.current_task = None
        tracker.logic.task_elapsed = 0.0
        tracker.logic.task_start_time = 0.0
        tracker.logic.task_baseline = 0
        tracker.task_var.set("Select task...")
        tracker.task_timer_label.configure(text="00:00:00")
        tracker.delete_task_btn.pack_forget()

    if task_name in tracker.tasks:
        tracker.tasks = [t for t in tracker.tasks if t != task_name]
        storage.save_tasks(tracker.tasks)

    changed = False
    for date_key in list(tracker.task_data.keys()):
        day = tracker.task_data.get(date_key, {})
        if task_name in day:
            del day[task_name]
            changed = True
            if not day:
                del tracker.task_data[date_key]
    if changed:
        storage.save_task_log(tracker.task_data)

    tracker._refresh_task_dropdown()


def show_history(tracker):
    if tracker._history_win is not None and tracker._history_win.winfo_exists():
        tracker._history_win.lift()
        tracker._history_win.focus_force()
        return

    win = ctk.CTkToplevel(tracker.root)
    tracker._history_win = win
    win.title("History")
    win.configure(fg_color=theme.BG)
    win.resizable(False, False)
    center_popup(tracker.root, win, theme.WINDOW_HISTORY_W, theme.WINDOW_HISTORY_H)

    ctk.CTkLabel(
        win,
        text="Last 14 Days",
        font=theme.FONT_TITLE,
        text_color=theme.ACCENT,
    ).pack(pady=(20, 5))

    subhead_row = ctk.CTkFrame(win, fg_color="transparent")
    subhead_row.pack(fill="x", padx=25, pady=(10, 5))
    ctk.CTkLabel(
        subhead_row, text="Date",
        font=theme.FONT_SMALL_BOLD,
        text_color=theme.MUTED,
    ).pack(side="left")
    ctk.CTkLabel(
        subhead_row, text="Time",
        font=theme.FONT_SMALL_BOLD,
        text_color=theme.MUTED,
    ).pack(side="right")

    sep = ctk.CTkFrame(win, fg_color=theme.BTN_ACTIVE, height=1, corner_radius=0)
    sep.pack(fill="x", padx=25)

    scroll = ctk.CTkScrollableFrame(
        win,
        fg_color="transparent",
        scrollbar_fg_color="transparent",
        scrollbar_button_color=theme.BTN_BG,
        scrollbar_button_hover_color=theme.BTN_ACTIVE,
    )
    scroll.pack(fill="both", expand=True, padx=(20, 4), pady=(8, 16))

    today = datetime.now().date()
    for i in range(14):
        d = today - timedelta(days=i)
        date_key = d.strftime("%Y-%m-%d")
        total = int(tracker.data.get(date_key, {}).get("total_seconds", 0))
        if i == 0:
            total += int(tracker.logic.current_total())
        h, m = total // 3600, (total % 3600) // 60

        day_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        day_frame.pack(fill="x", pady=(8, 2))

        date_row = ctk.CTkFrame(day_frame, fg_color="transparent")
        date_row.pack(fill="x")

        date_text = d.strftime("%a  %Y-%m-%d")
        if i == 0:
            date_text += "  (today)"
        ctk.CTkLabel(
            date_row, text=date_text,
            font=theme.FONT_MONO_DATE,
            text_color=theme.FG,
            anchor="w",
        ).pack(side="left")

        time_color = theme.ACCENT if total > 0 else theme.DIM
        ctk.CTkLabel(
            date_row, text=f"{h}h {m:02d}m",
            font=theme.FONT_MONO_DATE,
            text_color=time_color,
            anchor="e",
        ).pack(side="right")

        day_tasks = {
            name: int(e.get("total_seconds", 0))
            for name, e in tracker.task_data.get(date_key, {}).items()
        }
        if i == 0 and tracker.logic.current_task is not None:
            live = int(tracker.logic.task_live_session())
            if live > 0:
                day_tasks[tracker.logic.current_task] = (
                    day_tasks.get(tracker.logic.current_task, 0) + live
                )

        items = sorted(
            ((n, s) for n, s in day_tasks.items() if s > 0),
            key=lambda x: -x[1],
        )
        for name, secs in items:
            th, tm = secs // 3600, (secs % 3600) // 60
            trow = ctk.CTkFrame(day_frame, fg_color="transparent")
            trow.pack(fill="x", padx=(20, 0), pady=1)
            ctk.CTkLabel(
                trow, text=f"•  {name}",
                font=theme.FONT_SMALL,
                text_color=theme.MUTED,
                anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(
                trow, text=f"{th}h {tm:02d}m",
                font=theme.FONT_MONO_SMALL,
                text_color=theme.MUTED,
                anchor="e",
            ).pack(side="right")
