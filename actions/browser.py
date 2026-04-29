import re
import urllib.parse
import urllib.request
import webbrowser

_YT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def google_search(query):
    if not query:
        return False
    try:
        url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
        webbrowser.open(url, new=2)
        return True
    except Exception:
        return False


def open_youtube():
    try:
        webbrowser.open("https://www.youtube.com", new=2)
        return True
    except Exception:
        return False


def youtube_search(query):
    if not query:
        return open_youtube()
    try:
        url = (
            "https://www.youtube.com/results?search_query="
            + urllib.parse.quote_plus(query)
        )
        webbrowser.open(url, new=2)
        return True
    except Exception:
        return False


def _fetch_first_video_id(query):
    url = (
        "https://www.youtube.com/results?search_query="
        + urllib.parse.quote_plus(query)
    )
    req = urllib.request.Request(url, headers=_YT_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return None

    m = re.search(r'"videoRenderer":\{"videoId":"([A-Za-z0-9_-]{11})"', html)
    if m:
        return m.group(1)

    m = re.search(r'"compactVideoRenderer":\{"videoId":"([A-Za-z0-9_-]{11})"', html)
    if m:
        return m.group(1)

    m = re.search(r'"videoId":"([A-Za-z0-9_-]{11})"', html)
    if m:
        return m.group(1)

    return None


def youtube_play_first(query):
    if not query:
        return False

    video_id = _fetch_first_video_id(query)
    if not video_id:
        return youtube_search(query)

    try:
        webbrowser.open(f"https://www.youtube.com/watch?v={video_id}", new=2)
        return True
    except Exception:
        return False
