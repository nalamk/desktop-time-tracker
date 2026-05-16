import tkinter as tk

import theme


class Tooltip:
    def __init__(self, widget, text, delay=theme.TOOLTIP_DELAY):
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
                font=theme.FONT_TOOLTIP,
                fg=theme.FG,
                bg=theme.BTN_BG,
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
