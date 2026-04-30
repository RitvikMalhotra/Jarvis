import json
import os
import re
from difflib import SequenceMatcher
from pathlib import Path

CACHE_PATH = Path(__file__).resolve().parent.parent / "cache" / "app_index.json"

_cached_index = None
_refreshed_this_session = False


def _start_menu_dirs():
    dirs = []
    appdata = os.environ.get("APPDATA")
    if appdata:
        dirs.append(Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs")
    programdata = os.environ.get("PROGRAMDATA")
    if programdata:
        dirs.append(Path(programdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs")
    return dirs


def _scan_start_menu():
    apps = {}
    for root in _start_menu_dirs():
        if not root.exists():
            continue
        for path in root.rglob("*.lnk"):
            name = path.stem.lower().strip()
            if name:
                apps.setdefault(name, str(path))
    return apps


def _scan_app_paths():
    apps = {}
    try:
        import winreg
    except ImportError:
        return apps

    sub_path = r"Software\Microsoft\Windows\CurrentVersion\App Paths"
    for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            key = winreg.OpenKey(root, sub_path)
        except OSError:
            continue
        try:
            i = 0
            while True:
                try:
                    sub_name = winreg.EnumKey(key, i)
                except OSError:
                    break
                i += 1

                bare = sub_name[:-4] if sub_name.lower().endswith(".exe") else sub_name
                bare = bare.lower().strip()
                if not bare:
                    continue

                try:
                    sub_key = winreg.OpenKey(key, sub_name)
                    try:
                        path, _ = winreg.QueryValueEx(sub_key, "")
                    finally:
                        winreg.CloseKey(sub_key)
                except OSError:
                    continue

                if path:
                    apps.setdefault(bare, path)
        finally:
            winreg.CloseKey(key)
    return apps


def _scan():
    apps = {}
    for name, path in _scan_start_menu().items():
        apps.setdefault(name, path)
    for name, path in _scan_app_paths().items():
        apps.setdefault(name, path)
    return apps


def _load_cache():
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return None


def _save_cache(apps):
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = CACHE_PATH.with_suffix(CACHE_PATH.suffix + ".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(apps, f, indent=2)
        tmp_path.replace(CACHE_PATH)
    except Exception:
        pass


def get_index():
    global _cached_index
    if _cached_index is not None:
        return _cached_index
    cached = _load_cache()
    if cached is None:
        _cached_index = _scan()
        _save_cache(_cached_index)
    else:
        _cached_index = cached
    return _cached_index


def refresh():
    global _cached_index, _refreshed_this_session
    _cached_index = _scan()
    _save_cache(_cached_index)
    _refreshed_this_session = True
    return _cached_index


def _tokens(s):
    return set(re.findall(r"\w+", s.lower()))


def _score(query, name):
    q = query.lower().strip()
    n = name.lower().strip()

    if q == n:
        return 2.0

    q_set = _tokens(q)
    n_set = _tokens(n)

    if q_set and n_set and q_set.issubset(n_set):
        if q_set == n_set:
            return 1.5
        extra = len(n_set - q_set)
        return max(0.6, 1.0 - 0.05 * extra)

    if len(q) >= 3 and q in n:
        return 0.7 + 0.3 * (len(q) / max(len(n), 1))

    return SequenceMatcher(None, q, n).ratio() * 0.7


def _find_in(query, index, threshold):
    query = query.lower().strip()
    if not query:
        return None
    if query in index:
        return index[query]

    best_score = 0.0
    best_path = None
    for name, path in index.items():
        score = _score(query, name)
        if score > best_score:
            best_score = score
            best_path = path

    if best_score >= threshold:
        return best_path
    return None


def find(query, threshold=0.7):
    global _refreshed_this_session
    index = get_index()
    result = _find_in(query, index, threshold)
    if result:
        return result

    if not _refreshed_this_session:
        fresh = refresh()
        return _find_in(query, fresh, threshold)
    return None
