import threading

import pyttsx3

from config import VOICE_RATE, VOICE_VOLUME


class Speaker:
    def __init__(self, rate=VOICE_RATE, volume=VOICE_VOLUME):
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", rate)
        self.engine.setProperty("volume", volume)
        self._lock = threading.Lock()

    def speak(self, text):
        if not text:
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
        with self._lock:
            try:
                self.engine.stop()
            except Exception:
                pass
