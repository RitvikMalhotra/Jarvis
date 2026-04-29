import tkinter as tk

from config import (
    UI_FADE_INTERVAL_MS,
    UI_FADE_STEP,
    UI_HEIGHT,
    UI_HIDE_DELAY_MS,
    UI_TITLE,
    UI_WIDTH,
)

STATUS_COLORS = {
    "Idle": "#6b6b6b",
    "Listening": "#00d4ff",
    "Processing": "#ffaa00",
    "Executing": "#00ff88",
    "Error": "#ff5555",
}


class JarvisUI:
    def __init__(self, hide_delay_ms=UI_HIDE_DELAY_MS):
        self.root = tk.Tk()
        self.root.title(UI_TITLE)
        self.root.configure(bg="#0a0a0a")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.0)

        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = sw - UI_WIDTH - 30
        y = sh - UI_HEIGHT - 80
        self.root.geometry(f"{UI_WIDTH}x{UI_HEIGHT}+{x}+{y}")

        title = tk.Label(
            self.root,
            text=UI_TITLE,
            font=("Consolas", 24, "bold"),
            fg="#00d4ff",
            bg="#0a0a0a",
        )
        title.pack(pady=(18, 4))

        self._status_var = tk.StringVar(value="Status: Idle")
        self._status_label = tk.Label(
            self.root,
            textvariable=self._status_var,
            font=("Consolas", 13, "bold"),
            fg=STATUS_COLORS["Idle"],
            bg="#0a0a0a",
        )
        self._status_label.pack(pady=4)

        cmd_title = tk.Label(
            self.root,
            text="Last command",
            font=("Consolas", 9),
            fg="#777777",
            bg="#0a0a0a",
        )
        cmd_title.pack(pady=(10, 0))

        self._command_var = tk.StringVar(value="—")
        self._command_label = tk.Label(
            self.root,
            textvariable=self._command_var,
            font=("Consolas", 11),
            fg="#dddddd",
            bg="#0a0a0a",
            wraplength=UI_WIDTH - 40,
            justify="center",
        )
        self._command_label.pack(pady=(2, 10))

        self._hide_delay_ms = hide_delay_ms
        self._hide_after_id = None
        self._fade_after_id = None

        self.root.protocol("WM_DELETE_WINDOW", self.hide)
        self.root.withdraw()

    def _cancel_pending_hide(self):
        if self._hide_after_id is not None:
            try:
                self.root.after_cancel(self._hide_after_id)
            except Exception:
                pass
            self._hide_after_id = None

    def _cancel_pending_fade(self):
        if self._fade_after_id is not None:
            try:
                self.root.after_cancel(self._fade_after_id)
            except Exception:
                pass
            self._fade_after_id = None

    def _set_alpha(self, value):
        try:
            self.root.attributes("-alpha", max(0.0, min(1.0, value)))
        except Exception:
            pass

    def _fade(self, target, on_done=None, step=UI_FADE_STEP):
        try:
            current = float(self.root.attributes("-alpha"))
        except Exception:
            current = 1.0 if target >= 1.0 else 0.0

        if abs(current - target) <= step:
            self._set_alpha(target)
            self._fade_after_id = None
            if on_done is not None:
                on_done()
            return

        new_value = current + step if current < target else current - step
        self._set_alpha(new_value)
        self._fade_after_id = self.root.after(
            UI_FADE_INTERVAL_MS, lambda: self._fade(target, on_done, step)
        )

    def show(self):
        def _apply():
            self._cancel_pending_hide()
            self._cancel_pending_fade()
            self.root.deiconify()
            self.root.lift()
            self.root.attributes("-topmost", True)
            self._fade(1.0)

        self.root.after(0, _apply)

    def hide(self):
        def _apply():
            self._cancel_pending_hide()
            self._cancel_pending_fade()
            self._fade(0.0, on_done=self.root.withdraw)

        self.root.after(0, _apply)

    def schedule_hide(self, delay_ms=None):
        delay = self._hide_delay_ms if delay_ms is None else delay_ms

        def _apply():
            self._cancel_pending_hide()
            self._hide_after_id = self.root.after(delay, self.hide)

        self.root.after(0, _apply)

    def set_status(self, status):
        color = STATUS_COLORS.get(status, "#a0e0ff")

        def _apply():
            self._status_var.set(f"Status: {status}")
            self._status_label.config(fg=color)

        self.root.after(0, _apply)

    def set_command(self, text):
        display = text if text else "—"
        self.root.after(0, lambda: self._command_var.set(display))

    def quit(self):
        self.root.after(0, self.root.destroy)

    def run(self):
        self.root.mainloop()
