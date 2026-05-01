"""
ui/interface.py
---------------
Jarvis desktop overlay – visual design based on the Stitch "JARVIS_OS" screen.

Design language (from Stitch design system "Aether Intelligence"):
  • Void-black background (#0a0a0f) with radial cyan glow blobs
  • Glassmorphic inner-orb with electric-cyan (#00f0ff) glow
  • Rotating dashed HUD ring
  • Radial equalizer pillars arranged in a circle
  • Space Grotesk typography (loaded from Google Fonts via tkinter web trick;
    falls back to Helvetica Neue / Segoe UI)
  • Status chip + large headline text

Public API (unchanged from original interface.py):
  JarvisUI()
    .show()
    .hide()
    .schedule_hide(delay_ms=None)
    .set_status(status)   # "Idle" | "Listening" | "Processing" | "Executing" | "Error"
    .set_command(text)
    .quit()
    .run()
"""

import math
import tkinter as tk

from config import (
    UI_FADE_INTERVAL_MS,
    UI_FADE_STEP,
    UI_HEIGHT,
    UI_HIDE_DELAY_MS,
    UI_TITLE,
    UI_WIDTH,
)

# ---------------------------------------------------------------------------
# Design tokens (from Stitch project)
# ---------------------------------------------------------------------------
BG_DARKEST   = "#0a0a0f"
BG_DEEP      = "#050505"
CYAN_BRIGHT  = "#00f0ff"
CYAN_DIM     = "#00dbe9"
CYAN_FAINT   = "#7df4ff"
PRIMARY_TEXT = "#dbfcff"
DIM_TEXT     = "#b9cacb"
SURFACE      = "#1f1f23"
GLASS_BG     = "#1a1a1e"

STATUS_CONFIG = {
    "Idle":       {"label": "SYSTEM ACTIVE",  "headline": "Idle",        "glow": "#006970", "orb": CYAN_DIM},
    "Listening":  {"label": "VOICE ACTIVE",   "headline": "Listening...", "glow": CYAN_BRIGHT, "orb": CYAN_BRIGHT},
    "Processing": {"label": "PROCESSING",     "headline": "Processing…",  "glow": "#ffaa00", "orb": "#ffc400"},
    "Executing":  {"label": "EXECUTING",      "headline": "Executing…",   "glow": "#00ff88", "orb": "#00ff88"},
    "Error":      {"label": "FAULT DETECTED", "headline": "Error",        "glow": "#ff5555", "orb": "#ff5555"},
}
DEFAULT_STATUS = STATUS_CONFIG["Idle"]

PILLAR_ANGLES = [10, 35, 70, 110, 150, 190, 240, 300]  # degrees, from Stitch HTML
PILLAR_LENGTHS = [128, 144, 112, 160, 120, 136, 152, 128]  # px (visual variation)
PILLAR_OPACITIES = [0.40, 0.20, 0.30, 0.50, 0.20, 0.40, 0.30, 0.20]


def _hex_lerp(c1: str, c2: str, t: float) -> str:
    """Linear interpolation between two hex colours."""
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def _dim_color(hex_color: str, factor: float) -> str:
    """Return a dimmed (darkened) version of a hex colour."""
    return _hex_lerp(hex_color, "#000000", 1.0 - factor)


class JarvisUI:
    """Jarvis floating overlay window – Stitch JARVIS_OS aesthetic."""

    def __init__(self, hide_delay_ms: int = UI_HIDE_DELAY_MS):
        self._hide_delay_ms = hide_delay_ms
        self._hide_after_id = None
        self._fade_after_id = None
        self._spin_after_id = None
        self._pulse_after_id = None

        self._status = "Idle"
        self._command_text = "—"
        self._spin_angle = 0.0
        self._pulse_phase = 0.0

        # ------------------------------------------------------------------ window
        self.root = tk.Tk()
        self.root.title(UI_TITLE)
        self.root.configure(bg=BG_DARKEST)
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.0)
        self.root.overrideredirect(True)   # frameless

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        W, H = UI_WIDTH, UI_HEIGHT
        x = sw - W - 30
        y = sh - H - 80
        self.root.geometry(f"{W}x{H}+{x}+{y}")

        # Allow dragging the frameless window
        self.root.bind("<ButtonPress-1>", self._start_drag)
        self.root.bind("<B1-Motion>", self._do_drag)

        # ------------------------------------------------------------------ canvas
        self.canvas = tk.Canvas(
            self.root,
            width=W, height=H,
            bg=BG_DARKEST,
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)

        self._build_static_chrome(W, H)
        self._draw_dynamic(W, H)

        self.root.protocol("WM_DELETE_WINDOW", self.hide)
        self.root.withdraw()

        # start animation loops
        self._animate_spin()
        self._animate_pulse()

    # ------------------------------------------------------------------ drag
    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _do_drag(self, event):
        dx = event.x - self._drag_x
        dy = event.y - self._drag_y
        x = self.root.winfo_x() + dx
        y = self.root.winfo_y() + dy
        self.root.geometry(f"+{x}+{y}")

    # ------------------------------------------------------------------ static chrome
    def _build_static_chrome(self, W: int, H: int):
        """Draw the elements that don't change: background, border, title."""
        c = self.canvas

        # Outer border (simulates glass edge)
        c.create_rectangle(
            2, 2, W - 2, H - 2,
            outline=CYAN_BRIGHT, width=1,
            stipple="gray25",          # dashed appearance
            tags="chrome",
        )

        # Top header band
        c.create_rectangle(0, 0, W, 36, fill="#0d0d12", outline="", tags="chrome")
        c.create_line(0, 36, W, 36, fill=CYAN_BRIGHT, width=1, tags="chrome")

        # JARVIS_OS title (top-left)
        c.create_text(
            16, 18,
            text="JARVIS_OS",
            anchor="w",
            font=("Helvetica Neue", 11, "bold"),
            fill=CYAN_BRIGHT,
            tags="chrome",
        )

        # Close button (top-right)
        btn = c.create_text(
            W - 16, 18,
            text="✕",
            anchor="e",
            font=("Helvetica Neue", 11),
            fill=DIM_TEXT,
            tags="close_btn",
        )
        c.tag_bind("close_btn", "<Button-1>", lambda e: self.hide())
        c.tag_bind("close_btn", "<Enter>",    lambda e: c.itemconfig("close_btn", fill=CYAN_BRIGHT))
        c.tag_bind("close_btn", "<Leave>",    lambda e: c.itemconfig("close_btn", fill=DIM_TEXT))

    # ------------------------------------------------------------------ dynamic draw
    def _draw_dynamic(self, W: int, H: int):
        """Draw / redraw all state-dependent elements."""
        c = self.canvas
        c.delete("dynamic")

        cfg = STATUS_CONFIG.get(self._status, DEFAULT_STATUS)
        orb_color = cfg["orb"]
        glow_color = cfg["glow"]

        # Centre of the orb area (below header)
        cx = W // 2
        cy = 36 + (H - 36) // 2 - 24   # shift up a bit to leave room for text

        # ---- ambient glow blob -------------------------------------------------
        glow_r = 90
        steps = 10
        for i in range(steps, 0, -1):
            t = i / steps
            r = int(glow_r * t)
            alpha_color = _dim_color(glow_color, t * 0.25)
            c.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                fill=alpha_color, outline="",
                tags="dynamic",
            )

        # ---- radial equalizer pillars ------------------------------------------
        orb_radius = 58   # pillar starts here (edge of outer orb ring)
        for angle_deg, length, opacity in zip(PILLAR_ANGLES, PILLAR_LENGTHS, PILLAR_OPACITIES):
            rad = math.radians(angle_deg)
            x1 = cx + orb_radius * math.sin(rad)
            y1 = cy - orb_radius * math.cos(rad)
            x2 = cx + (orb_radius + length * 0.5) * math.sin(rad)
            y2 = cy - (orb_radius + length * 0.5) * math.cos(rad)
            pillar_color = _dim_color(orb_color, opacity)
            c.create_line(x1, y1, x2, y2, fill=pillar_color, width=2, tags="dynamic")

        # ---- outer radial wave rings -------------------------------------------
        for scale, op in [(1.10, 0.20), (1.25, 0.10), (1.45, 0.05)]:
            r = int(orb_radius * scale)
            ring_color = _dim_color(orb_color, op)
            c.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                outline=ring_color, width=1,
                tags="dynamic",
            )

        # ---- spinning dashed HUD ring ------------------------------------------
        hud_r = orb_radius + 10
        # Draw as 36 small arcs to fake a dashed circle
        seg = 360 // 36
        for i in range(36):
            start = self._spin_angle + i * seg
            if (i % 3) == 0:
                continue    # gap every 3rd segment → dashed look
            self._arc_segment(c, cx, cy, hud_r, start, seg - 2, _dim_color(CYAN_BRIGHT, 0.3))

        # ---- inner orb glass shell --------------------------------------------
        glass_r = orb_radius - 8
        # glass pane (dark fill)
        c.create_oval(
            cx - glass_r, cy - glass_r,
            cx + glass_r, cy + glass_r,
            fill="#0d0d18", outline=_dim_color(orb_color, 0.4), width=1,
            tags="dynamic",
        )

        # ---- glowing core (gradient-ish via stacked circles) ------------------
        core_r = glass_r - 14
        pulse = abs(math.sin(self._pulse_phase))   # 0..1 breathing factor
        extra_r = int(8 * pulse)

        core_steps = 12
        for i in range(core_steps, 0, -1):
            t = i / core_steps
            r = int((core_r + extra_r) * t)
            bright = _dim_color(orb_color, 0.4 + 0.6 * t)
            c.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                fill=bright, outline="",
                tags="dynamic",
            )

        # core highlight dot
        c.create_oval(
            cx - 6, cy - 10, cx + 6, cy + 2,
            fill="#ffffff", outline="",
            tags="dynamic",
        )

        # ---- status label (CAPS chip) -----------------------------------------
        label_y = cy + orb_radius + 24
        c.create_text(
            cx, label_y,
            text=cfg["label"],
            font=("Helvetica Neue", 8, "bold"),
            fill=_dim_color(CYAN_BRIGHT, 0.7),
            tags="dynamic",
        )

        # ---- headline (state text) -------------------------------------------
        headline_y = label_y + 20
        c.create_text(
            cx, headline_y,
            text=cfg["headline"],
            font=("Helvetica Neue", 18, "bold"),
            fill=PRIMARY_TEXT,
            tags="dynamic",
        )

        # ---- last command label ------------------------------------------------
        cmd_label_y = H - 42
        c.create_text(
            cx, cmd_label_y,
            text="Last command",
            font=("Helvetica Neue", 8),
            fill=_dim_color(DIM_TEXT, 0.5),
            tags="dynamic",
        )

        cmd_y = H - 26
        # Truncate long commands
        cmd = self._command_text
        if len(cmd) > 38:
            cmd = cmd[:35] + "…"
        c.create_text(
            cx, cmd_y,
            text=cmd,
            font=("Helvetica Neue", 10),
            fill=DIM_TEXT,
            tags="dynamic",
        )

        # ---- bottom footer line -----------------------------------------------
        c.create_line(W // 4, H - 8, 3 * W // 4, H - 8,
                      fill=_dim_color("#ffffff", 0.12), tags="dynamic")
        c.create_text(
            cx, H - 8,
            text="STARK_INDUSTRIES // HUD_v4.2.0",
            font=("Helvetica Neue", 6),
            fill=_dim_color("#ffffff", 0.25),
            tags="dynamic",
        )

    def _arc_segment(self, canvas, cx, cy, r, start_deg, sweep_deg, color):
        """Draw a short arc segment as a chord (approximation of a dashed ring)."""
        segments = max(2, sweep_deg)
        points = []
        for i in range(segments + 1):
            a = math.radians(start_deg + i)
            points.append(cx + r * math.cos(a))
            points.append(cy + r * math.sin(a))
        if len(points) >= 4:
            canvas.create_line(*points, fill=color, width=1, smooth=True, tags="dynamic")

    # ------------------------------------------------------------------ animations
    def _animate_spin(self):
        self._spin_angle = (self._spin_angle + 1.0) % 360
        W, H = UI_WIDTH, UI_HEIGHT
        self._draw_dynamic(W, H)
        self._spin_after_id = self.root.after(40, self._animate_spin)   # ~25 fps

    def _animate_pulse(self):
        self._pulse_phase += 0.06
        self._pulse_after_id = self.root.after(50, self._animate_pulse)

    # ------------------------------------------------------------------ fade helpers
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

    def _set_alpha(self, value: float):
        try:
            self.root.attributes("-alpha", max(0.0, min(1.0, value)))
        except Exception:
            pass

    def _fade(self, target: float, on_done=None, step: float = UI_FADE_STEP):
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

    # ------------------------------------------------------------------ public API
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

    def schedule_hide(self, delay_ms: int = None):
        delay = self._hide_delay_ms if delay_ms is None else delay_ms
        def _apply():
            self._cancel_pending_hide()
            self._hide_after_id = self.root.after(delay, self.hide)
        self.root.after(0, _apply)

    def set_status(self, status: str):
        def _apply():
            self._status = status if status in STATUS_CONFIG else "Idle"
        self.root.after(0, _apply)
        # redraw will happen naturally via _animate_spin

    def set_command(self, text: str):
        def _apply():
            self._command_text = text if text else "—"
        self.root.after(0, _apply)

    def quit(self):
        self.root.after(0, self.root.destroy)

    def run(self):
        self.root.mainloop()
