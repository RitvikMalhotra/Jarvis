import re
import shutil
import subprocess
import urllib.parse
from difflib import SequenceMatcher


def is_winget_available():
    return shutil.which("winget") is not None


def _parse_winget_search(stdout):
    lines = stdout.splitlines()
    sep_idx = None
    for i, line in enumerate(lines):
        if re.match(r"^-{3,}\s+-{3,}", line):
            sep_idx = i
            break
    if sep_idx is None:
        return []

    results = []
    for line in lines[sep_idx + 1:]:
        line = line.rstrip()
        if not line.strip():
            continue
        parts = re.split(r"\s{2,}", line)
        if len(parts) >= 2:
            name = parts[0].strip()
            pkg_id = parts[1].strip()
            if name and pkg_id and not pkg_id.startswith("-"):
                results.append((name, pkg_id))
    return results


def winget_search(query):
    if not is_winget_available():
        return []
    try:
        result = subprocess.run(
            [
                "winget", "search", "--query", query,
                "--accept-source-agreements",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception:
        return []
    if result.returncode != 0:
        return []
    return _parse_winget_search(result.stdout)


def _best_winget_match(query, results, threshold=0.5):
    if not results:
        return None
    q = query.lower()
    scored = []
    for name, pkg_id in results:
        ratio = SequenceMatcher(None, q, name.lower()).ratio()
        if q in name.lower():
            ratio = max(ratio, 0.9)
        scored.append((ratio, name, pkg_id))
    scored.sort(reverse=True)
    if scored[0][0] >= threshold:
        return scored[0][1], scored[0][2]
    return None


def winget_install(pkg_id):
    if not is_winget_available():
        return False
    try:
        result = subprocess.run(
            [
                "winget", "install",
                "--id", pkg_id,
                "--exact",
                "--silent",
                "--accept-source-agreements",
                "--accept-package-agreements",
            ],
            capture_output=True,
            text=True,
            timeout=600,
        )
        return result.returncode == 0
    except Exception:
        return False


def open_microsoft_store(query):
    try:
        url = f"ms-windows-store://search/?query={urllib.parse.quote(query)}"
        subprocess.Popen(
            ["cmd", "/c", "start", "", url],
            shell=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


def install(app_name):
    """Returns one of: 'installed', 'manual', 'failed'."""
    if is_winget_available():
        results = winget_search(app_name)
        match = _best_winget_match(app_name, results)
        if match is not None:
            _, pkg_id = match
            if winget_install(pkg_id):
                return "installed"

    if open_microsoft_store(app_name):
        return "manual"

    return "failed"
