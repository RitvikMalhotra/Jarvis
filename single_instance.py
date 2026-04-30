import ctypes
import sys
import time

_handle = None
_MUTEX_NAME = r"Local\JarvisVoiceAssistant_Singleton"
_ERROR_ALREADY_EXISTS = 183


def release():
    global _handle
    if _handle is None:
        return
    try:
        ctypes.windll.kernel32.CloseHandle(_handle)
    except Exception:
        pass
    _handle = None


def acquire_with_retry(timeout=10.0, interval=0.4):
    deadline = time.time() + timeout
    if acquire():
        return True
    while time.time() < deadline:
        time.sleep(interval)
        if acquire():
            return True
    return False


def acquire():
    """Try to acquire a per-session named mutex. Returns True if this process
    is the sole instance, False if another instance is already running."""
    global _handle

    if not sys.platform.startswith("win"):
        return True

    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        kernel32.CreateMutexW.argtypes = [
            ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p
        ]
        kernel32.GetLastError.restype = ctypes.c_uint32
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel32.CloseHandle.restype = ctypes.c_int

        handle = kernel32.CreateMutexW(None, 0, _MUTEX_NAME)
        last_error = kernel32.GetLastError()

        if last_error == _ERROR_ALREADY_EXISTS:
            if handle:
                kernel32.CloseHandle(handle)
            return False

        _handle = handle
        return True
    except Exception:
        return True
