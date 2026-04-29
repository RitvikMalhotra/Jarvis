import os
from pathlib import Path


def _resolve_folder(name):
    if not name:
        return None
    home = Path.home()
    mapping = {
        "documents": home / "Documents",
        "downloads": home / "Downloads",
        "desktop": home / "Desktop",
        "music": home / "Music",
        "pictures": home / "Pictures",
        "videos": home / "Videos",
    }
    path = mapping.get(name.lower().strip())
    if path and path.exists():
        return str(path)
    return None


def open_folder(name):
    path = _resolve_folder(name)
    if not path:
        return False
    try:
        os.startfile(path)
        return True
    except Exception:
        return False
