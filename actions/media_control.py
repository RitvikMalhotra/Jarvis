"""
media_control.py
----------------
Sends keyboard shortcuts to the active/foreground browser window to control
YouTube (or any browser-based) video playback.

Shortcuts used (standard YouTube bindings):
  k / space  → play / pause toggle
  shift+n    → next video
  shift+p    → previous video
  j          → rewind 10 s
  l          → forward 10 s

The module tries to focus a browser window first so keys land in the right
place even if Jarvis has focus.
"""

import time
import logging

import pyautogui
import pygetwindow as gw

log = logging.getLogger(__name__)

# Browser window title substrings to look for (case-insensitive)
_BROWSER_TITLES = ["chrome", "firefox", "brave", "edge", "opera", "youtube"]

# Map action names → pyautogui key sequences
# Each entry is either a single key string or a tuple (modifier, key)
_ACTION_KEYS = {
    "play":      "k",
    "pause":     "k",
    "stop":      "k",
    "next":      ("shift", "n"),
    "previous":  ("shift", "p"),
    "rewind":    "j",
    "forward":   "l",
}


def _find_browser_window():
    """Return the first matching browser window, or None."""
    try:
        all_windows = gw.getAllWindows()
    except Exception as e:
        log.warning(f"media_control: could not list windows: {e}")
        return None

    for win in all_windows:
        title = (win.title or "").lower()
        if any(b in title for b in _BROWSER_TITLES):
            return win

    return None


def _focus_browser():
    """
    Try to bring a browser window to the foreground.
    Returns True if a browser window was found and focused.
    """
    win = _find_browser_window()
    if win is None:
        return False

    try:
        win.activate()
        time.sleep(0.4)   # let the OS finish raising the window
        return True
    except Exception as e:
        log.warning(f"media_control: could not activate browser window: {e}")
        return False


def send_media_key(action: str) -> bool:
    """
    Focus the browser and send the keyboard shortcut for *action*.

    Parameters
    ----------
    action : str
        One of 'play', 'pause', 'stop', 'next', 'previous', 'rewind', 'forward'.

    Returns
    -------
    bool
        True if the key was sent, False if no browser was found.
    """
    action = action.lower().strip()
    key_spec = _ACTION_KEYS.get(action)

    if key_spec is None:
        log.warning(f"media_control: unknown action '{action}'")
        return False

    if not _focus_browser():
        log.info("media_control: no browser window found")
        return False

    log.info(f"Media control: {action}")
    print(f"Media control: {action}", flush=True)

    if isinstance(key_spec, tuple):
        pyautogui.hotkey(*key_spec)
    else:
        pyautogui.press(key_spec)

    return True
