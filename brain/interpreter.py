import re

from config import WAKE_WORD

NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
    "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
}


def _to_int(token):
    if not token:
        return None
    token = token.lower().strip()
    if token.isdigit():
        return int(token)
    return NUMBER_WORDS.get(token)


def parse(command):
    if not command:
        return []

    text = command.lower().strip()
    text = re.sub(rf"\b{re.escape(WAKE_WORD)}\b", " ", text)
    text = text.strip(" ,.!?")

    if not text:
        return []

    parts = re.split(r"\s+(?:and then|then|and|also)\s+", text)

    actions = []
    for part in parts:
        part = part.strip(" ,.!?")
        if not part:
            continue
        action = _interpret(part)
        if action:
            actions.append(action)

    return actions


def _interpret(text):
    if re.search(
        r"\b(?:enter|enable|activate|go to|switch to|start)\s+(?:dev|developer|development)\s+mode\b",
        text,
    ):
        return {"type": "dev_mode"}

    if re.search(r"\b(?:dev|developer|development)\s+mode\b", text):
        return {"type": "dev_mode"}

    m = re.search(
        r"\b(?:open|launch|start)\s+chrome\s+(?:with\s+)?profile\s+(?:number\s+)?(\w+)",
        text,
    )
    if m:
        n = _to_int(m.group(1))
        if n:
            return {"type": "open_chrome_profile", "index": n}

    m = re.search(
        r"\b(?:select|choose|pick|use|switch to|go to)\s+(?:chrome\s+)?profile\s+(?:number\s+)?(\w+)",
        text,
    )
    if m:
        n = _to_int(m.group(1))
        if n:
            return {"type": "open_chrome_profile", "index": n}

    m = re.search(r"\bopen\s+profile\s+(?:number\s+)?(\w+)", text)
    if m:
        n = _to_int(m.group(1))
        if n:
            return {"type": "open_chrome_profile", "index": n}

    m = re.search(r"\bplay\s+(.+?)\s+on\s+youtube", text)
    if m:
        return {"type": "youtube_play", "query": m.group(1).strip()}

    m = re.search(r"(?:search|find|look up)\s+(.+?)\s+on\s+youtube", text)
    if m:
        return {"type": "youtube_search", "query": m.group(1).strip()}

    m = re.search(r"(?:search|find|look up)\s+(.+?)\s+on\s+google", text)
    if m:
        return {"type": "search", "query": m.group(1).strip()}

    if re.search(r"\b(?:open|launch|go to|start)\s+youtube\b", text):
        return {"type": "open_youtube"}

    m = re.search(
        r"\b(?:open|launch|go to)\s+(?:the\s+)?(documents|downloads|desktop|music|pictures|videos)(?:\s+folder)?\b",
        text,
    )
    if m:
        return {"type": "open_folder", "folder": m.group(1)}

    m = re.match(r"play\s+(.+)", text)
    if m:
        query = m.group(1).strip()
        if query:
            return {"type": "youtube_play", "query": query}

    m = re.search(r"\b(?:search|google)(?:\s+for)?\s+(.+)", text)
    if m:
        query = m.group(1).strip()
        query = re.sub(r"\s+on\s+google$", "", query).strip()
        if query:
            return {"type": "search", "query": query}

    m = re.match(r"(?:open|launch|start|run)\s+(.+)", text)
    if m:
        app = m.group(1).strip()
        app = re.sub(r"^(the\s+|a\s+|an\s+)", "", app)
        if app:
            return {"type": "open_app", "app": app}

    return None
