"""Quick visual smoke-test — cycles through all Jarvis UI states."""
import sys, time, threading
sys.path.insert(0, "d:/Jarvis")

from ui.interface import JarvisUI

ui = JarvisUI()

def cycle():
    time.sleep(1)
    ui.show()
    states = [
        ("Idle",       "—"),
        ("Listening",  "jarvis open chrome"),
        ("Processing", "jarvis open chrome"),
        ("Executing",  "open_app: chrome"),
        ("Error",      "Command not recognized"),
    ]
    for status, cmd in states:
        ui.set_status(status)
        ui.set_command(cmd)
        time.sleep(2)
    ui.schedule_hide(delay_ms=1500)
    time.sleep(2)
    ui.quit()

threading.Thread(target=cycle, daemon=True).start()
ui.run()
