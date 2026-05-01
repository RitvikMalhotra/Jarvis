"""
brain/ai_engine.py
------------------
AI brain for Jarvis. Sends the user's utterance to Claude and returns either:
  {"mode": "action", "actions": [...]}     — execute these structured actions
  {"mode": "chat",   "response": "..."}    — speak this conversational reply

Returns None if the AI is unavailable (missing SDK, missing API key, network
failure, malformed response). The caller falls back to the rule-based
interpreter in brain/interpreter.py.

Uses Claude Sonnet 4.6 via the Anthropic SDK with structured outputs
(Pydantic schema) and prompt caching on the system prompt.
"""

import os

from logger import log

try:
    import anthropic
    _HAS_SDK = True
except ImportError:
    anthropic = None
    _HAS_SDK = False

try:
    from typing import List, Literal, Optional
    from pydantic import BaseModel
    _HAS_PYDANTIC = True
except ImportError:
    _HAS_PYDANTIC = False

from config import AI_API_KEY_ENV, AI_MAX_TOKENS, AI_MODEL


_ACTION_TYPES = (
    "open_app",
    "open_chrome_profile",
    "youtube_play",
    "youtube_search",
    "search",
    "open_youtube",
    "open_folder",
    "media_control",
    "dev_mode",
)


if _HAS_PYDANTIC:

    class Action(BaseModel):
        type: Literal[
            "open_app",
            "open_chrome_profile",
            "youtube_play",
            "youtube_search",
            "search",
            "open_youtube",
            "open_folder",
            "media_control",
            "dev_mode",
        ]
        app: Optional[str] = None
        index: Optional[int] = None
        query: Optional[str] = None
        folder: Optional[str] = None
        action: Optional[str] = None

    class Decision(BaseModel):
        mode: Literal["action", "chat"]
        actions: Optional[List[Action]] = None
        response: Optional[str] = None


_SYSTEM_PROMPT = """You are the brain of Jarvis, a voice-controlled desktop assistant on Windows. The user speaks to you; your job is to decide if their utterance is a COMMAND for the assistant to execute, or just CONVERSATION.

Output exactly one of:
1. {"mode": "action", "actions": [...]} — when the utterance maps to one or more concrete actions.
2. {"mode": "chat",   "response": "..."} — when it's a question, greeting, small talk, or anything that doesn't map to an action.

Available action types and their fields:

- open_app
  Launch an installed application by natural name.
  Fields: app (string, required) — e.g. "chrome", "spotify", "vs code", "notepad"

- open_chrome_profile
  Open Google Chrome with a specific profile (1-indexed, counted from the picker order).
  Fields: index (int, required, >= 1)

- youtube_play
  Search YouTube and auto-play the first result. Use for "play X" / "play X on YouTube".
  Fields: query (string, required)

- youtube_search
  Open YouTube search results page WITHOUT auto-playing. Use for "search X on YouTube".
  Fields: query (string, required)

- search
  Open Google web search.
  Fields: query (string, required)

- open_youtube
  Open YouTube homepage.
  Fields: (none)

- open_folder
  Open a Windows shell folder.
  Fields: folder (string, required) — must be one of: documents, downloads, desktop, music, pictures, videos

- media_control
  Control currently-playing browser media (YouTube, Spotify Web, etc.).
  Fields: action (string, required) — one of: play, pause, next, previous, rewind, forward

- dev_mode
  Shut down Jarvis and enter development mode. ONLY emit when the user explicitly says some form of "enter development mode" / "developer mode" / "dev mode".
  Fields: (none)

Rules:
- For multi-step requests like "open Chrome and search football news", emit one element per step in actions[], in execution order.
- If the utterance is ambiguous about whether it's a command, prefer "chat" and ask a short clarifying question.
- For chat responses, keep them short and natural (1-2 sentences). They will be spoken aloud, so no markdown, code blocks, or long lists.
- Never invent action types not in the list above.
- Never include both actions and response — exactly one of them.
- Never put the wake word "jarvis" inside an action field.
- For open_app, prefer common names ("chrome", "vs code", "spotify") rather than full executable names ("chrome.exe").

Examples:

User: "what's the weather like?"
Output: {"mode": "chat", "response": "I don't have weather data hooked up yet, but I can search the web for it if you'd like."}

User: "open chrome and search football news"
Output: {"mode": "action", "actions": [{"type": "open_app", "app": "chrome"}, {"type": "search", "query": "football news"}]}

User: "play despacito on youtube"
Output: {"mode": "action", "actions": [{"type": "youtube_play", "query": "despacito"}]}

User: "pause the music"
Output: {"mode": "action", "actions": [{"type": "media_control", "action": "pause"}]}

User: "open chrome with profile 2 and play taylor swift"
Output: {"mode": "action", "actions": [{"type": "open_chrome_profile", "index": 2}, {"type": "youtube_play", "query": "taylor swift"}]}

User: "how are you?"
Output: {"mode": "chat", "response": "I'm doing great. What can I help you with?"}

User: "enter development mode"
Output: {"mode": "action", "actions": [{"type": "dev_mode"}]}"""


_client = None
_init_attempted = False


def _get_client():
    global _client, _init_attempted
    if _client is not None:
        return _client
    if _init_attempted:
        return None
    _init_attempted = True

    if not _HAS_SDK:
        log("AI engine: anthropic SDK not installed")
        return None
    if not _HAS_PYDANTIC:
        log("AI engine: pydantic not installed")
        return None
    if not os.environ.get(AI_API_KEY_ENV):
        log(f"AI engine: {AI_API_KEY_ENV} not set — falling back to rule-based")
        return None

    try:
        _client = anthropic.Anthropic()
        log(f"AI engine ready (model={AI_MODEL})")
        return _client
    except Exception as e:
        log(f"AI engine init failed: {e}")
        return None


def is_available():
    return _get_client() is not None


def decide(user_input):
    """Send the utterance to Claude and return a decision dict.

    Returns:
        {"mode": "action", "actions": [...]} or {"mode": "chat", "response": "..."}
        or None if the AI is unavailable / failed (caller should fall back).
    """
    if not user_input or not user_input.strip():
        return None

    client = _get_client()
    if client is None:
        return None

    try:
        response = client.messages.parse(
            model=AI_MODEL,
            max_tokens=AI_MAX_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                },
            ],
            messages=[
                {"role": "user", "content": user_input.strip()},
            ],
            output_format=Decision,
        )
    except anthropic.APIConnectionError as e:
        log(f"AI engine: network error — {e}")
        return None
    except anthropic.APIStatusError as e:
        log(f"AI engine: API error {getattr(e, 'status_code', '?')} — {e}")
        return None
    except Exception as e:
        log(f"AI engine: unexpected error — {e}")
        return None

    decision = getattr(response, "parsed_output", None)
    if decision is None:
        log("AI engine: no parsed_output on response")
        return None

    return decision.model_dump(exclude_none=True)
