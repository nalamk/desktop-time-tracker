import tkinter as tk
from datetime import datetime, timedelta

import theme
import storage


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

    win = tk.Toplevel(tracker.root)
    tracker._task_dialog = win
    win.title("Add Task")
    win.configure(bg=theme.BG)
    win.resizable(False, False)
    center_popup(tracker.root, win, theme.DIALOG_ADDTASK_W, theme.DIALOG_ADDTASK_H)

    tk.Label(
        win, text="Task name",
        font=theme.FONT_DIALOG_LABEL,
        fg=theme.ACCENT, bg=theme.BG,
    ).pack(pady=(22, 10))

    entry = tk.Entry(
        win,
        font=theme.FONT_INPUT,
        bg=theme.BTN_BG,
        fg=theme.FG,
        insertbackground=theme.FG,
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
        tracker.tasks.append(name)
        storage.save_tasks(tracker.tasks)
        tracker._refresh_task_dropdown()
        win.destroy()

    save_btn = tk.Button(
        win, text="Save",
        font=theme.FONT_BTN_DIALOG,
        fg=theme.BG, bg=theme.START_COLOR,
        activebackground=theme.BTN_ACTIVE,
        activeforeground=theme.FG,
        relief=tk.FLAT, cursor="hand2",
        padx=24, pady=6,
        command=save,
    )
    save_btn.pack(pady=20)

    entry.bind("<Return>", save)
    win.bind("<Escape>", lambda e: win.destroy())


def delete_task(tracker):
    if tracker.logic.current_task is None or tracker.logic.current_task not in tracker.tasks:
        return
    task_name = tracker.logic.current_task

    win = tk.Toplevel(tracker.root)
    win.title("Confirm Delete")
    win.configure(bg=theme.BG)
    win.resizable(False, False)
    center_popup(tracker.root, win, theme.DIALOG_CONFIRM_W, theme.DIALOG_CONFIRM_H)

    tk.Label(
        win,
        text=f"Delete task '{task_name}'?",
        font=theme.FONT_BTN_DIALOG,
        fg=theme.FG, bg=theme.BG,
    ).pack(pady=(28, 6), padx=20)

    tk.Label(
        win,
        text="This will also remove its time logs.",
        font=theme.FONT_SMALL,
        fg=theme.MUTED, bg=theme.BG,
    ).pack(pady=(0, 18), padx=20)

    btn_frame = tk.Frame(win, bg=theme.BG)
    btn_frame.pack()

    def do_delete():
        win.destroy()
        perform_task_delete(tracker, task_name)

    delete_btn = tk.Button(
        btn_frame, text="Delete",
        font=theme.FONT_BTN_CONFIRM,
        fg=theme.BG, bg=theme.STOP_COLOR,
        activebackground=theme.BTN_ACTIVE, activeforeground=theme.FG,
        relief=tk.FLAT, cursor="hand2",
        padx=22, pady=6,
        command=do_delete,
    )
    delete_btn.grid(row=0, column=0, padx=8)

    cancel_btn = tk.Button(
        btn_frame, text="Cancel",
        font=theme.FONT_BTN_CONFIRM,
        fg=theme.FG, bg=theme.BTN_BG,
        activebackground=theme.BTN_ACTIVE, activeforeground=theme.FG,
        relief=tk.FLAT, cursor="hand2",
        padx=22, pady=6,
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
        tracker.task_timer_label.config(text="00:00:00")
        tracker.delete_task_btn.config(state=tk.DISABLED)

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

    win = tk.Toplevel(tracker.root)
    tracker._history_win = win
    win.title("History")
    win.configure(bg=theme.BG)
    win.resizable(False, False)
    center_popup(tracker.root, win, theme.WINDOW_HISTORY_W, theme.WINDOW_HISTORY_H)

    header = tk.Label(
        win,
        text="Last 14 Days",
        font=theme.FONT_TITLE,
        fg=theme.ACCENT,
        bg=theme.BG,
    )
    header.pack(pady=(20, 5))

    subhead_row = tk.Frame(win, bg=theme.BG)
    subhead_row.pack(fill="x", padx=25, pady=(10, 5))
    tk.Label(
        subhead_row, text="Date",
        font=theme.FONT_SMALL_BOLD,
        fg=theme.MUTED, bg=theme.BG,
    ).pack(side="left")
    tk.Label(
        subhead_row, text="Time",
        font=theme.FONT_SMALL_BOLD,
        fg=theme.MUTED, bg=theme.BG,
    ).pack(side="right")

    sep = tk.Frame(win, bg=theme.BTN_ACTIVE, height=1)
    sep.pack(fill="x", padx=25)

    container = tk.Frame(win, bg=theme.BG)
    container.pack(fill="both", expand=True, padx=(25, 8), pady=(8, 16))

    canvas = tk.Canvas(
        container, bg=theme.BG, highlightthickness=0, bd=0
    )
    scrollbar = tk.Scrollbar(
        container, orient="vertical", command=canvas.yview,
        bg=theme.BTN_BG, activebackground=theme.BTN_ACTIVE,
        troughcolor=theme.BG, bd=0, relief=tk.FLAT, width=theme.SCROLLBAR_WIDTH,
    )
    canvas.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    list_frame = tk.Frame(canvas, bg=theme.BG)
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
        total = int(tracker.data.get(date_key, {}).get("total_seconds", 0))
        if i == 0:
            total += int(tracker.logic.current_total())
        h, m = total // 3600, (total % 3600) // 60

        day_frame = tk.Frame(list_frame, bg=theme.BG)
        day_frame.pack(fill="x", pady=(8, 2))

        date_row = tk.Frame(day_frame, bg=theme.BG)
        date_row.pack(fill="x")

        date_text = d.strftime("%a  %Y-%m-%d")
        if i == 0:
            date_text += "  (today)"
        tk.Label(
            date_row, text=date_text,
            font=theme.FONT_MONO_DATE,
            fg=theme.FG, bg=theme.BG, anchor="w",
        ).pack(side="left")

        time_color = theme.ACCENT if total > 0 else theme.DIM
        tk.Label(
            date_row, text=f"{h}h {m:02d}m",
            font=theme.FONT_MONO_DATE,
            fg=time_color, bg=theme.BG, anchor="e",
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
            trow = tk.Frame(day_frame, bg=theme.BG)
            trow.pack(fill="x", padx=(20, 0), pady=1)
            tk.Label(
                trow, text=f"•  {name}",
                font=theme.FONT_SMALL,
                fg=theme.MUTED, bg=theme.BG, anchor="w",
            ).pack(side="left")
            tk.Label(
                trow, text=f"{th}h {tm:02d}m",
                font=theme.FONT_MONO_SMALL,
                fg=theme.MUTED, bg=theme.BG, anchor="e",
            ).pack(side="right")
