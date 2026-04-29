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


def _scan():
    apps = {}
    for root in _start_menu_dirs():
        if not root.exists():
            continue
        for path in root.rglob("*.lnk"):
            name = path.stem.lower().strip()
            if not name:
                continue
            apps.setdefault(name, str(path))
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
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(apps, f, indent=2)
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


def _score(query, name):
    seq = SequenceMatcher(None, query, name).ratio()

    sub = 0.0
    if query in name:
        sub = 1.0
    elif name in query:
        sub = 0.7

    q_tokens = set(re.findall(r"\w+", query))
    n_tokens = set(re.findall(r"\w+", name))
    if q_tokens and n_tokens:
        tok = len(q_tokens & n_tokens) / len(q_tokens) * 0.9
    else:
        tok = 0.0

    return max(seq, sub, tok)


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


def find(query, threshold=0.55):
    global _refreshed_this_session
    index = get_index()
    result = _find_in(query, index, threshold)
    if result:
        return result

    if not _refreshed_this_session:
        fresh = refresh()
        return _find_in(query, fresh, threshold)
    return None
