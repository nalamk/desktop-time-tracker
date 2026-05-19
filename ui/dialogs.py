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


def _reveal_popup(win):
    win.update_idletasks()
    win.deiconify()
    win.attributes("-alpha", 1.0)
    win.lift()
    win.focus_force()
    win.grab_set()


def add_task(tracker):
    if tracker._task_dialog is not None and tracker._task_dialog.winfo_exists():
        tracker._task_dialog.lift()
        tracker._task_dialog.focus_force()
        return

    win = ctk.CTkToplevel(tracker.root)
    win.withdraw()
    win.attributes("-alpha", 0.0)
    tracker._task_dialog = win
    win.title("Add Task")
    win.configure(fg_color=theme.BG)
    win.resizable(False, False)

    ctk.CTkLabel(
        win, text="Task name",
        font=theme.FONT_DIALOG_LABEL,
        text_color=theme.ACCENT,
    ).pack(pady=(30, 14))

    entry = ctk.CTkEntry(
        win,
        font=theme.FONT_INPUT,
        fg_color=theme.BTN_BG,
        text_color=theme.FG,
        border_color=theme.BTN_BG,
        border_width=0,
        width=340,
        height=44,
        justify="center",
    )
    entry.pack(padx=30)
    entry.focus_set()

    def save(_event=None):
        name = entry.get().strip()
        if not name:
            return
        tracker.tasks.append(name)
        storage.save_tasks_doc(tracker.tasks, tracker.last_selected)
        tracker._refresh_task_dropdown()
        win.destroy()

    save_btn = ctk.CTkButton(
        win, text="Save",
        font=theme.FONT_BTN_DIALOG,
        text_color=theme.BG,
        fg_color=theme.START_COLOR,
        hover_color=theme.BTN_ACTIVE,
        cursor="hand2",
        width=130, height=38,
        command=save,
    )
    save_btn.pack(pady=24)

    entry.bind("<Return>", save)
    win.bind("<Escape>", lambda e: win.destroy())

    center_popup(tracker.root, win, theme.DIALOG_ADDTASK_W, theme.DIALOG_ADDTASK_H)
    _reveal_popup(win)


def delete_task(tracker):
    if tracker.logic.current_task is None or tracker.logic.current_task not in tracker.tasks:
        return
    task_name = tracker.logic.current_task

    win = ctk.CTkToplevel(tracker.root)
    win.withdraw()
    win.attributes("-alpha", 0.0)
    win.title("Confirm Delete")
    win.configure(fg_color=theme.BG)
    win.resizable(False, False)

    ctk.CTkLabel(
        win,
        text=f"Delete task '{task_name}'?",
        font=theme.FONT_BTN_DIALOG,
        text_color=theme.FG,
    ).pack(pady=(32, 8), padx=30)

    ctk.CTkLabel(
        win,
        text="This will also remove its time logs.",
        font=theme.FONT_SMALL,
        text_color=theme.MUTED,
    ).pack(pady=(0, 22), padx=30)

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
        width=120, height=38,
        command=do_delete,
    )
    delete_btn.grid(row=0, column=0, padx=10)

    cancel_btn = ctk.CTkButton(
        btn_frame, text="Cancel",
        font=theme.FONT_BTN_CONFIRM,
        text_color=theme.FG,
        fg_color=theme.BTN_BG,
        hover_color=theme.BTN_ACTIVE,
        cursor="hand2",
        width=120, height=38,
        command=win.destroy,
    )
    cancel_btn.grid(row=0, column=1, padx=10)

    win.bind("<Escape>", lambda _e: win.destroy())

    center_popup(tracker.root, win, theme.DIALOG_CONFIRM_W, theme.DIALOG_CONFIRM_H)
    _reveal_popup(win)
    cancel_btn.focus_set()


def perform_task_delete(tracker, task_name):
    if tracker.logic.current_task == task_name:
        tracker.logic.current_task = None
        tracker.logic.task_elapsed = 0.0
        tracker.logic.task_start_time = 0.0
        tracker.task_var.set("Select task...")
        tracker.task_timer_label.configure(text="00:00:00")
        tracker.delete_task_btn.pack_forget()
        tracker.reset_task_btn.pack_forget()

    tracker.logic.task_accumulated.pop(task_name, None)
    tracker.logic.task_session_starts.pop(task_name, None)

    if task_name in tracker.tasks:
        tracker.tasks = [t for t in tracker.tasks if t != task_name]
        if tracker.last_selected == task_name:
            tracker.last_selected = None
        storage.save_tasks_doc(tracker.tasks, tracker.last_selected)

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


def reset_main_dialog(tracker):
    _confirm_reset(
        tracker,
        target_name="main",
        on_confirm=lambda: _perform_reset_main(tracker),
    )


def reset_task_dialog(tracker):
    if tracker.logic.current_task is None:
        return
    name = tracker.logic.current_task
    _confirm_reset(
        tracker,
        target_name=name,
        on_confirm=lambda: _perform_reset_task(tracker),
    )


def _perform_reset_main(tracker):
    tracker.logic.reset_today_main()
    tracker._render_main_timer()


def _perform_reset_task(tracker):
    tracker.logic.reset_today_task()
    tracker._render_task_timer()


def _confirm_reset(tracker, target_name, on_confirm):
    win = ctk.CTkToplevel(tracker.root)
    win.withdraw()
    win.attributes("-alpha", 0.0)
    win.title("Confirm Reset")
    win.configure(fg_color=theme.BG)
    win.resizable(False, False)

    ctk.CTkLabel(
        win,
        text=f"Reset today's time for {target_name}?",
        font=theme.FONT_BTN_DIALOG,
        text_color=theme.FG,
    ).pack(pady=(32, 8), padx=30)

    ctk.CTkLabel(
        win,
        text="This cannot be undone.",
        font=theme.FONT_SMALL,
        text_color=theme.MUTED,
    ).pack(pady=(0, 22), padx=30)

    btn_frame = ctk.CTkFrame(win, fg_color="transparent")
    btn_frame.pack()

    def do_reset():
        win.destroy()
        on_confirm()

    reset_btn = ctk.CTkButton(
        btn_frame, text="Reset",
        font=theme.FONT_BTN_CONFIRM,
        text_color=theme.BG, fg_color=theme.STOP_COLOR,
        hover_color=theme.BTN_ACTIVE,
        cursor="hand2",
        width=120, height=38,
        command=do_reset,
    )
    reset_btn.grid(row=0, column=0, padx=10)

    cancel_btn = ctk.CTkButton(
        btn_frame, text="Cancel",
        font=theme.FONT_BTN_CONFIRM,
        text_color=theme.FG, fg_color=theme.BTN_BG,
        hover_color=theme.BTN_ACTIVE,
        cursor="hand2",
        width=120, height=38,
        command=win.destroy,
    )
    cancel_btn.grid(row=0, column=1, padx=10)

    win.bind("<Escape>", lambda _e: win.destroy())

    center_popup(tracker.root, win, theme.DIALOG_CONFIRM_W, theme.DIALOG_CONFIRM_H)
    _reveal_popup(win)
    cancel_btn.focus_set()


def show_history(tracker):
    if tracker._history_win is not None and tracker._history_win.winfo_exists():
        tracker._history_win.lift()
        tracker._history_win.focus_force()
        return

    win = ctk.CTkToplevel(tracker.root)
    win.withdraw()
    win.attributes("-alpha", 0.0)
    tracker._history_win = win
    win.title("History")
    win.configure(fg_color=theme.BG)
    win.resizable(False, False)

    ctk.CTkLabel(
        win,
        text="Last 14 Days",
        font=theme.FONT_TITLE,
        text_color=theme.ACCENT,
    ).pack(pady=(24, 6))

    subhead_row = ctk.CTkFrame(win, fg_color="transparent")
    subhead_row.pack(fill="x", padx=30, pady=(14, 6))
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
    sep.pack(fill="x", padx=30)

    scroll = ctk.CTkScrollableFrame(
        win,
        fg_color="transparent",
        scrollbar_fg_color="transparent",
        scrollbar_button_color=theme.BTN_BG,
        scrollbar_button_hover_color=theme.BTN_ACTIVE,
    )
    scroll.pack(fill="both", expand=True, padx=(28, 8), pady=(12, 22))

    today = datetime.now().date()
    for i in range(14):
        d = today - timedelta(days=i)
        date_key = d.strftime("%Y-%m-%d")
        total = int(tracker.data.get(date_key, {}).get("total_seconds", 0))
        if i == 0:
            total += int(tracker.logic.session_only())
        h, m = total // 3600, (total % 3600) // 60

        day_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        day_frame.pack(fill="x", pady=(10, 3))

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
        if i == 0:
            if tracker.logic.current_task is not None:
                live = int(tracker.logic.task_live_session())
                if live > 0:
                    day_tasks[tracker.logic.current_task] = (
                        day_tasks.get(tracker.logic.current_task, 0) + live
                    )
            for name, accumulated in tracker.logic.task_accumulated.items():
                if accumulated > 0:
                    day_tasks[name] = (
                        day_tasks.get(name, 0) + int(accumulated)
                    )

        items = sorted(
            ((n, s) for n, s in day_tasks.items() if s > 0),
            key=lambda x: -x[1],
        )
        for name, secs in items:
            th, tm = secs // 3600, (secs % 3600) // 60
            trow = ctk.CTkFrame(day_frame, fg_color="transparent")
            trow.pack(fill="x", padx=(28, 0), pady=2)
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

    center_popup(tracker.root, win, theme.WINDOW_HISTORY_W, theme.WINDOW_HISTORY_H)
    _reveal_popup(win)
