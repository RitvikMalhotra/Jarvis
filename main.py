import re
import subprocess
import sys
import threading
import time
from pathlib import Path

import single_instance
import state
from actions import app_control, app_index, browser, installer, media_control
from actions import system as sys_actions
from brain import ai_engine, wake_word
from brain.interpreter import parse
from config import ENABLE_TRAY, MIC_RECOVERY_DELAY, NON_WAKE_HIDE_DELAY_MS
from logger import log
from ui.interface import JarvisUI
from ui.tray import create_tray, is_available as tray_available
from voice.listen import Listener
from voice.speak import Speaker

SESSION_TIMEOUT_S = 60
PROJECT_DIR = Path(__file__).resolve().parent
SUPERVISOR_PATH = PROJECT_DIR / "dev_supervisor.py"

_YES_PATTERN = re.compile(
    r"\b(yes|yeah|yep|yup|sure|ok|okay|please|alright|fine|do it|go ahead|install)\b"
)
_NO_PATTERN = re.compile(
    r"\b(no|nope|nah|cancel|don'?t|never mind|nevermind|stop|abort)\b"
)
_GO_IDLE_PATTERN = re.compile(r"\b(go\s+idle|goodbye|stop\s+listening|that'?s\s+all)\b")


def _is_affirmative(text):
    if not text:
        return False
    text = text.lower()
    if _NO_PATTERN.search(text):
        return False
    return bool(_YES_PATTERN.search(text))


def _save_for_dev_mode():
    try:
        app_index.refresh()
        log("State saved for development mode")
    except Exception as e:
        log(f"Save before dev mode failed: {e}")


def _spawn_supervisor():
    try:
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        if not pythonw.exists():
            pythonw = Path(sys.executable)

        DETACHED_PROCESS = 0x00000008
        CREATE_NEW_PROCESS_GROUP = 0x00000200

        subprocess.Popen(
            [str(pythonw), str(SUPERVISOR_PATH)],
            cwd=str(PROJECT_DIR),
            creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
            close_fds=True,
        )
        log("Spawned dev supervisor")
        return True
    except Exception as e:
        log(f"Failed to spawn supervisor: {e}")
        return False


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
        speaker.speak("Entering development mode")
        log("Entering development mode")
        state.enter_development_mode()
        _save_for_dev_mode()
        _spawn_supervisor()
        single_instance.release()
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

    if kind == "media_control":
        media_action = action.get("action", "pause")
        speaker.speak(f"Media {media_action}")
        ok = media_control.send_media_key(media_action)
        if not ok:
            speaker.speak("No active media found")
        return


def _execute_actions(actions, speaker, ui, stop_event, listener):
    ui.set_status("Executing")
    for action in actions:
        execute_action(action, speaker, ui, stop_event, listener)
        if stop_event.is_set():
            return


def handle_command(text, speaker, ui, stop_event, listener):
    ui.set_command(text)
    ui.set_status("Processing")

    decision = ai_engine.decide(text)

    if decision is not None:
        mode = decision.get("mode")

        if mode == "chat":
            response = (decision.get("response") or "").strip()
            if response:
                speaker.speak(response)
            else:
                speaker.speak("I'm not sure what to say to that.")
            return

        if mode == "action":
            actions = decision.get("actions") or []
            if not actions:
                speaker.speak("I'm not sure what you'd like me to do.")
                return
            _execute_actions(actions, speaker, ui, stop_event, listener)
            return

    actions = parse(text)
    if not actions:
        speaker.speak("I didn't understand that")
        return
    _execute_actions(actions, speaker, ui, stop_event, listener)


def _run_session(ui, stop_event, listener, speaker, was_resumed=False):
    is_active = bool(was_resumed)
    last_command_time = time.time() if is_active else 0.0

    if is_active:
        ui.show()
        ui.set_status("Listening")
        log("Active mode")

    def on_voice_onset():
        if stop_event.is_set():
            return
        ui.show()
        ui.set_status("Listening")

    while not stop_event.is_set():
        try:
            if is_active and last_command_time > 0:
                if time.time() - last_command_time > SESSION_TIMEOUT_S:
                    speaker.speak("Going idle")
                    log("Session timeout")
                    is_active = False
                    last_command_time = 0.0
                    ui.set_status("Idle")
                    ui.schedule_hide()

            text = listener.listen(
                on_speech_start=on_voice_onset if not is_active else None
            )

            if stop_event.is_set():
                return

            if not text:
                if not is_active:
                    ui.set_status("Idle")
                    ui.schedule_hide(delay_ms=NON_WAKE_HIDE_DELAY_MS)
                continue

            print(f"Heard: {text}", flush=True)

            if not is_active:
                if not wake_word.is_wake_word_present(text):
                    print("No wake word detected", flush=True)
                    ui.set_status("Idle")
                    ui.schedule_hide(delay_ms=NON_WAKE_HIDE_DELAY_MS)
                    continue

                print("Wake word detected", flush=True)
                log("Session started")
                is_active = True
                last_command_time = time.time()

                command = wake_word.strip_wake_word(text)
                ui.show()

                if not command:
                    speaker.speak("Yes?")
                    ui.set_command(text)
                    ui.set_status("Listening")
                    continue

                handle_command(text, speaker, ui, stop_event, listener)
            else:
                ui.show()
                last_command_time = time.time()

                if _GO_IDLE_PATTERN.search(text.lower()):
                    speaker.speak("Going idle")
                    log("Session ended by command")
                    is_active = False
                    last_command_time = 0.0
                    ui.set_status("Idle")
                    ui.schedule_hide()
                    continue

                handle_command(text, speaker, ui, stop_event, listener)

            if stop_event.is_set():
                return

            if is_active:
                ui.set_status("Listening")
            else:
                ui.set_status("Idle")
                ui.schedule_hide()

        except Exception as e:
            log(f"Loop iteration error, continuing: {e}")
            time.sleep(0.3)


def backend_loop(ui, stop_event, resumed=False):
    listener = Listener()
    speaker = Speaker()

    if resumed:
        speaker.speak("Development mode exited. I'm back.")
        log("Resumed from development mode")
    else:
        speaker.speak("Jarvis online")

    first_run = True
    try:
        while not stop_event.is_set():
            try:
                _run_session(
                    ui, stop_event, listener, speaker,
                    was_resumed=resumed and first_run,
                )
                first_run = False
            except Exception as e:
                log(f"Error occurred, retrying... ({e})")
                ui.set_status("Error")
                time.sleep(MIC_RECOVERY_DELAY)
    finally:
        try:
            speaker.close()
        except Exception:
            pass
        try:
            listener.close()
        except Exception:
            pass


def main():
    resumed = "--resumed" in sys.argv

    log("Starting Jarvis" + (" (resumed)" if resumed else ""))

    timeout = 10.0 if resumed else 0.5
    if not single_instance.acquire_with_retry(timeout=timeout):
        log("Instance already running")
        return

    log("Jarvis started")

    try:
        ui = JarvisUI()
        stop_event = threading.Event()

        def on_quit():
            stop_event.set()
            ui.quit()

        worker = threading.Thread(
            target=backend_loop, args=(ui, stop_event, resumed), daemon=True
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

        log("Jarvis stopped")
    except Exception as e:
        log(f"Fatal error in main: {e}")


if __name__ == "__main__":
    main()
