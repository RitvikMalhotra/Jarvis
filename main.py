import re
import threading
import time

import state
from actions import app_control, app_index, browser, installer
from actions import system as sys_actions
from brain.interpreter import parse
from config import ENABLE_TRAY, MIC_RECOVERY_DELAY, NON_WAKE_HIDE_DELAY_MS, WAKE_WORD
from ui.interface import JarvisUI
from ui.tray import create_tray, is_available as tray_available
from voice.listen import Listener
from voice.speak import Speaker

_YES_PATTERN = re.compile(
    r"\b(yes|yeah|yep|yup|sure|ok|okay|please|alright|fine|do it|go ahead|install)\b"
)
_NO_PATTERN = re.compile(
    r"\b(no|nope|nah|cancel|don'?t|never mind|nevermind|stop|abort)\b"
)


def _is_affirmative(text):
    if not text:
        return False
    text = text.lower()
    if _NO_PATTERN.search(text):
        return False
    return bool(_YES_PATTERN.search(text))


def _handle_open_app(app, speaker, ui, listener):
    path = app_control.find_app(app)
    if path:
        speaker.speak(f"Opening {app}")
        if not app_control.launch(path):
            speaker.speak(f"I couldn't open {app}")
        return

    speaker.speak(f"I couldn't find {app}. Would you like me to install it?")
    ui.set_command(f"Install {app}?")
    ui.set_status("Listening")
    response = listener.listen(timeout=8, phrase_time_limit=4)

    if not _is_affirmative(response):
        speaker.speak("Okay, cancelling installation.")
        return

    speaker.speak(f"Installing {app}. This may take a moment.")
    ui.set_command(f"Installing {app}")
    ui.set_status("Executing")

    result = installer.install(app)

    if result == "installed":
        speaker.speak(f"Installation complete. Opening {app}.")
        app_index.refresh()
        new_path = app_control.find_app(app)
        if new_path:
            app_control.launch(new_path)
        else:
            speaker.speak(f"I installed {app} but couldn't locate its shortcut.")
    elif result == "manual":
        speaker.speak(
            "I've opened the Microsoft Store. Please continue the installation there."
        )
    else:
        speaker.speak("Installation failed. Please try manually.")


def execute_action(action, speaker, ui, stop_event, listener):
    kind = action.get("type")

    if kind == "dev_mode":
        ui.set_status("Idle")
        ui.set_command("Entering development mode")
        speaker.speak("Entering development mode. Shutting down Jarvis.")
        state.enter_development_mode()
        stop_event.set()
        ui.quit()
        return

    if kind == "open_app":
        _handle_open_app(action["app"], speaker, ui, listener)
        return

    if kind == "open_chrome_profile":
        idx = action["index"]
        speaker.speak(f"Opening Chrome profile {idx}")
        if not app_control.open_chrome_with_profile(idx):
            speaker.speak(f"I couldn't find profile {idx}")
        return

    if kind == "youtube_play":
        query = action["query"]
        speaker.speak(f"Playing {query} on YouTube")
        if not browser.youtube_play_first(query):
            speaker.speak("I couldn't find that video")
        return

    if kind == "search":
        query = action["query"]
        speaker.speak(f"Searching for {query}")
        if not browser.google_search(query):
            speaker.speak("I couldn't perform the search")
        return

    if kind == "open_youtube":
        speaker.speak("Opening YouTube")
        browser.open_youtube()
        return

    if kind == "youtube_search":
        query = action["query"]
        speaker.speak(f"Searching YouTube for {query}")
        browser.youtube_search(query)
        return

    if kind == "open_folder":
        folder = action["folder"]
        speaker.speak(f"Opening {folder} folder")
        if not sys_actions.open_folder(folder):
            speaker.speak(f"I couldn't find the {folder} folder")
        return


def handle_command(text, speaker, ui, stop_event, listener):
    ui.set_command(text)
    ui.set_status("Processing")

    actions = parse(text)

    if not actions:
        speaker.speak("I didn't understand that")
        return

    ui.set_status("Executing")
    for action in actions:
        execute_action(action, speaker, ui, stop_event, listener)
        if stop_event.is_set():
            return


def _run_session(ui, stop_event):
    listener = Listener()
    speaker = Speaker()
    speaker.speak("Jarvis online")

    def on_voice_onset():
        if stop_event.is_set():
            return
        ui.show()
        ui.set_status("Listening")

    try:
        while not stop_event.is_set():
            try:
                text = listener.listen(on_speech_start=on_voice_onset)

                if stop_event.is_set():
                    return

                if not text or WAKE_WORD not in text:
                    ui.set_status("Idle")
                    ui.schedule_hide(delay_ms=NON_WAKE_HIDE_DELAY_MS)
                    continue

                stripped = text.replace(WAKE_WORD, "").strip(" ,.!?")

                if not stripped:
                    speaker.speak("Yes?")
                    ui.set_command(text)
                    ui.set_status("Listening")
                    follow_up = listener.listen()
                    if not follow_up:
                        ui.set_status("Idle")
                        ui.schedule_hide()
                        continue
                    handle_command(follow_up, speaker, ui, stop_event, listener)
                else:
                    handle_command(text, speaker, ui, stop_event, listener)

                if stop_event.is_set():
                    return

                ui.set_status("Idle")
                ui.schedule_hide()

            except Exception:
                time.sleep(0.3)
    finally:
        try:
            speaker.close()
        except Exception:
            pass
        try:
            listener.close()
        except Exception:
            pass


def backend_loop(ui, stop_event):
    while not stop_event.is_set():
        try:
            _run_session(ui, stop_event)
        except Exception:
            ui.set_status("Error")
            time.sleep(MIC_RECOVERY_DELAY)
            continue


def main():
    ui = JarvisUI()
    stop_event = threading.Event()

    def on_quit():
        stop_event.set()
        ui.quit()

    worker = threading.Thread(
        target=backend_loop, args=(ui, stop_event), daemon=True
    )
    worker.start()

    icon = None
    if ENABLE_TRAY and tray_available():
        icon = create_tray(on_show=ui.show, on_quit=on_quit)
        if icon is not None:
            threading.Thread(target=icon.run, daemon=True).start()

    try:
        ui.run()
    finally:
        stop_event.set()
        if icon is not None:
            try:
                icon.stop()
            except Exception:
                pass


if __name__ == "__main__":
    main()
