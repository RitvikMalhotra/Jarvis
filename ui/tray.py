try:
    import pystray
    from PIL import Image, ImageDraw

    _TRAY_AVAILABLE = True
except ImportError:
    _TRAY_AVAILABLE = False


def _build_image():
    img = Image.new("RGB", (64, 64), color="#0a0a0a")
    draw = ImageDraw.Draw(img)
    draw.ellipse((6, 6, 58, 58), fill="#00d4ff")
    draw.ellipse((22, 22, 42, 42), fill="#0a0a0a")
    return img


def create_tray(on_show, on_quit):
    if not _TRAY_AVAILABLE:
        return None

    icon = pystray.Icon(
        "jarvis",
        _build_image(),
        "Jarvis",
        menu=pystray.Menu(
            pystray.MenuItem("Show", lambda icon, item: on_show()),
            pystray.MenuItem("Exit", lambda icon, item: (on_quit(), icon.stop())),
        ),
    )
    return icon


def is_available():
    return _TRAY_AVAILABLE
