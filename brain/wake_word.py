import re
from difflib import SequenceMatcher

WAKE_WORD = "jarvis"
FUZZY_THRESHOLD = 0.78

WAKE_VARIANTS = {
    "jarvis", "jarviss", "jarvi", "jarvy",
    "jervis", "javis", "javus", "harvis", "carvis",
    "jervois", "jarvey",
    "service", "services", "drives", "harvest",
}


def _normalise(text):
    return re.sub(r"[^\w\s]", " ", text.lower()).strip()


def _matches_wake(token):
    if not token:
        return False
    if token in WAKE_VARIANTS:
        return True
    return SequenceMatcher(None, WAKE_WORD, token).ratio() >= FUZZY_THRESHOLD


def is_wake_word_present(text):
    if not text:
        return False

    cleaned = _normalise(text)
    if not cleaned:
        return False

    if WAKE_WORD in cleaned:
        return True

    tokens = cleaned.split()

    for token in tokens:
        if _matches_wake(token):
            return True

    for i in range(len(tokens) - 1):
        bigram = tokens[i] + tokens[i + 1]
        if _matches_wake(bigram):
            return True

    return False


def strip_wake_word(text):
    if not text:
        return ""

    cleaned = _normalise(text)
    tokens = cleaned.split()

    result = []
    i = 0
    while i < len(tokens):
        if i + 1 < len(tokens):
            bigram = tokens[i] + tokens[i + 1]
            if _matches_wake(bigram):
                i += 2
                continue
        if _matches_wake(tokens[i]):
            i += 1
            continue
        result.append(tokens[i])
        i += 1

    return " ".join(result).strip()
