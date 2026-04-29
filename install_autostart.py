import os
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.resolve()
VBS_NAME = "Jarvis.vbs"


def _startup_dir():
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA env var not set; cannot locate Startup folder")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def _vbs_content():
    return (
        'Set WshShell = CreateObject("WScript.Shell")\r\n'
        f'WshShell.CurrentDirectory = "{PROJECT_DIR}"\r\n'
        f'WshShell.Run "pythonw.exe ""{PROJECT_DIR}\\main.py""", 0, False\r\n'
    )


def install():
    startup = _startup_dir()
    startup.mkdir(parents=True, exist_ok=True)
    target = startup / VBS_NAME
    target.write_text(_vbs_content(), encoding="utf-8")
    print(f"Installed autostart entry: {target}")
    print("Jarvis will now start silently on every login.")


def uninstall():
    target = _startup_dir() / VBS_NAME
    if target.exists():
        target.unlink()
        print(f"Removed autostart entry: {target}")
    else:
        print("No autostart entry found — nothing to remove.")


def status():
    target = _startup_dir() / VBS_NAME
    if target.exists():
        print(f"Autostart ENABLED — {target}")
    else:
        print("Autostart DISABLED")


if __name__ == "__main__":
    cmd = sys.argv[1].lower() if len(sys.argv) > 1 else "install"
    if cmd in ("install", "enable"):
        install()
    elif cmd in ("uninstall", "remove", "disable"):
        uninstall()
    elif cmd == "status":
        status()
    else:
        print("Usage: python install_autostart.py [install|uninstall|status]")
        sys.exit(1)
