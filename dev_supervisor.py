import re
import subprocess
import sys
import time
from pathlib import Path

import single_instance
from logger import log
from voice.listen import Listener

PROJECT_DIR = Path(__file__).resolve().parent
MAIN_PATH = PROJECT_DIR / "main.py"

_EXIT_PATTERN = re.compile(
    r"\bexit\b[^.]*\b(dev|developer|development)\s+mode\b", re.IGNORECASE
)


def _is_exit_command(text):
    if not text:
        return False
    return bool(_EXIT_PATTERN.search(text))


def _relaunch_main():
    try:
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        if not pythonw.exists():
            pythonw = Path(sys.executable)

        DETACHED_PROCESS = 0x00000008
        CREATE_NEW_PROCESS_GROUP = 0x00000200

        subprocess.Popen(
            [str(pythonw), str(MAIN_PATH), "--resumed"],
            cwd=str(PROJECT_DIR),
            creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
            close_fds=True,
        )
        return True
    except Exception as e:
        log(f"Relaunch failed: {e}")
        return False


def main():
    log("Dev supervisor started")

    if not single_instance.acquire_with_retry(timeout=15):
        log("Supervisor: couldn't acquire singleton, exiting")
        return

    try:
        listener = Listener()
    except Exception as e:
        log(f"Supervisor listener init failed: {e}")
        single_instance.release()
        return

    try:
        while True:
            try:
                text = listener.listen()
                if not text:
                    continue
                log(f"Supervisor heard: {text}")
                if _is_exit_command(text):
                    log("Restarting Jarvis")
                    break
            except Exception as e:
                log(f"Supervisor loop error: {e}")
                time.sleep(1)
    finally:
        try:
            listener.close()
        except Exception:
            pass

    single_instance.release()
    time.sleep(0.3)

    if not _relaunch_main():
        log("Retrying relaunch once...")
        time.sleep(1)
        if not _relaunch_main():
            log("Relaunch failed twice — giving up")


if __name__ == "__main__":
    main()
