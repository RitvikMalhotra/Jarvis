import audioop
import collections
import math
import time

import speech_recognition as sr

from config import (
    AMBIENT_DURATION,
    LISTEN_TIMEOUT,
    MIC_RECOVERY_DELAY,
    PAUSE_THRESHOLD,
    PHRASE_TIME_LIMIT,
)
from logger import log


class _OnsetRecognizer(sr.Recognizer):
    """Recognizer that fires a callback the instant audio energy crosses the
    speech threshold, before phrase capture and STT complete."""

    def listen_with_onset(self, source, on_speech_start=None, timeout=None, phrase_time_limit=None):
        seconds_per_buffer = float(source.CHUNK) / source.SAMPLE_RATE
        pause_buffer_count = int(math.ceil(self.pause_threshold / seconds_per_buffer))
        phrase_buffer_count = int(math.ceil(self.phrase_threshold / seconds_per_buffer))
        non_speaking_buffer_count = int(math.ceil(self.non_speaking_duration / seconds_per_buffer))

        elapsed_time = 0.0
        buffer = b""

        while True:
            frames = collections.deque()

            while True:
                elapsed_time += seconds_per_buffer
                if timeout and elapsed_time > timeout:
                    raise sr.WaitTimeoutError("listening timed out")

                buffer = source.stream.read(source.CHUNK)
                if len(buffer) == 0:
                    break

                frames.append(buffer)
                if len(frames) > non_speaking_buffer_count:
                    frames.popleft()

                energy = audioop.rms(buffer, source.SAMPLE_WIDTH)
                if energy > self.energy_threshold:
                    break

                if self.dynamic_energy_threshold:
                    damping = self.dynamic_energy_adjustment_damping ** seconds_per_buffer
                    target_energy = energy * self.dynamic_energy_ratio
                    self.energy_threshold = (
                        self.energy_threshold * damping + target_energy * (1 - damping)
                    )

            if on_speech_start is not None:
                try:
                    on_speech_start()
                except Exception:
                    pass

            pause_count, phrase_count = 0, 0
            phrase_start_time = elapsed_time

            while True:
                elapsed_time += seconds_per_buffer
                if phrase_time_limit and elapsed_time - phrase_start_time > phrase_time_limit:
                    break

                buffer = source.stream.read(source.CHUNK)
                if len(buffer) == 0:
                    break

                frames.append(buffer)
                phrase_count += 1

                energy = audioop.rms(buffer, source.SAMPLE_WIDTH)
                if energy > self.energy_threshold:
                    pause_count = 0
                else:
                    pause_count += 1

                if pause_count > pause_buffer_count:
                    break

            phrase_count -= pause_count
            if phrase_count >= phrase_buffer_count or len(buffer) == 0:
                break

        for _ in range(pause_count - non_speaking_buffer_count):
            if frames:
                frames.pop()

        frame_data = b"".join(frames)
        return sr.AudioData(frame_data, source.SAMPLE_RATE, source.SAMPLE_WIDTH)


class Listener:
    def __init__(self):
        self.recognizer = _OnsetRecognizer()
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = PAUSE_THRESHOLD
        self.microphone = None
        self._init_microphone()

    def _init_microphone(self):
        try:
            self.microphone = sr.Microphone()
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=AMBIENT_DURATION)
            return True
        except Exception:
            self.microphone = None
            return False

    def _ensure_microphone(self):
        if self.microphone is not None:
            return True
        if self._init_microphone():
            return True
        log("Microphone retry...")
        time.sleep(MIC_RECOVERY_DELAY)
        return False

    def listen(self, on_speech_start=None, timeout=LISTEN_TIMEOUT, phrase_time_limit=PHRASE_TIME_LIMIT):
        if not self._ensure_microphone():
            return ""

        try:
            with self.microphone as source:
                audio = self.recognizer.listen_with_onset(
                    source,
                    on_speech_start=on_speech_start,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit,
                )
        except sr.WaitTimeoutError:
            return ""
        except OSError:
            self.microphone = None
            return ""
        except Exception:
            self.microphone = None
            return ""

        try:
            text = self.recognizer.recognize_google(audio)
            return text.lower().strip()
        except sr.UnknownValueError:
            return ""
        except sr.RequestError:
            return ""
        except Exception:
            return ""

    def close(self):
        self.microphone = None
