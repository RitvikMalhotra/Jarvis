import threading

import pyttsx3

from config import VOICE_RATE, VOICE_VOLUME


class Speaker:
    def __init__(self, rate=VOICE_RATE, volume=VOICE_VOLUME):
        self.engine = None
        self._lock = threading.Lock()
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", rate)
            engine.setProperty("volume", volume)
            self.engine = engine
        except Exception:
            self.engine = None

    def speak(self, text):
        if not text or self.engine is None:
            return
        with self._lock:
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except RuntimeError:
                try:
                    self.engine.stop()
                except Exception:
                    pass
            except Exception:
                pass

    def close(self):
        if self.engine is None:
            return
        with self._lock:
            try:
                self.engine.stop()
            except Exception:
                pass
