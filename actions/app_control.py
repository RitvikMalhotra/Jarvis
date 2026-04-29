import json
import os
import subprocess
from pathlib import Path

from actions import app_index

_CHROME_LOCAL_STATE_CANDIDATES = [
    Path.home() / "AppData/Local/Google/Chrome/User Data/Local State",
    Path.home() / "AppData/Local/Google/Chrome Beta/User Data/Local State",
    Path.home() / "AppData/Local/Chromium/User Data/Local State",
]


def find_app(name):
    if not name:
        return None
    return app_index.find(name)


def launch(path):
    if not path:
        return False
    try:
        os.startfile(path)
        return True
    except Exception:
        try:
            subprocess.Popen(
                ["cmd", "/c", "start", "", path],
                shell=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception:
            return False


def open_app(name):
    if not name:
        return False
    path = find_app(name)
    if not path:
        return False
    return launch(path)


def _read_chrome_local_state():
    for path in _CHROME_LOCAL_STATE_CANDIDATES:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                continue
    return None


def list_chrome_profiles():
    state = _read_chrome_local_state()
    if not state:
        return []

    profile = state.get("profile", {})
    info_cache = profile.get("info_cache", {})
    order = profile.get("profiles_order") or []

    if not order:
        keys = list(info_cache.keys())
        if "Default" in keys:
            keys.remove("Default")
            keys.sort()
            order = ["Default"] + keys
        else:
            order = sorted(keys)

    result = []
    for directory in order:
        meta = info_cache.get(directory, {})
        name = meta.get("name") or directory
        result.append({"directory": directory, "name": name})
    return result


def get_chrome_profile_dir_by_index(index):
    if not isinstance(index, int) or index < 1:
        return None
    profiles = list_chrome_profiles()
    if index <= len(profiles):
        return profiles[index - 1]["directory"]
    return None


def open_chrome_with_profile(index, url=None):
    profile_dir = get_chrome_profile_dir_by_index(index)
    if not profile_dir:
        return False

    args = ["chrome", f"--profile-directory={profile_dir}"]
    if url:
        args.append(url)

    try:
        subprocess.Popen(
            ["cmd", "/c", "start", "", *args],
            shell=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False
