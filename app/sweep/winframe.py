"""Window frame in Sweep's own colours: the title bar follows the dark or light theme of the app,
not the Windows setting, so a dark Sweep never gets a white strip on top."""
from __future__ import annotations

from . import platform as P

# caption and border colour, caption text colour (Theme.side and Theme.text in Theme.qml)
COLORS = {"dark": ("#110E24", "#EDE9FE"), "light": ("#ECE8FB", "#1E1B3A")}
DWMWA_USE_IMMERSIVE_DARK_MODE = 20          # Windows 10 20H1 and later, Windows 11
DWMWA_USE_IMMERSIVE_DARK_MODE_OLD = 19      # Windows 10 1809 to 1909
DWMWA_BORDER_COLOR = 34                     # Windows 11
DWMWA_CAPTION_COLOR = 35                    # Windows 11
DWMWA_TEXT_COLOR = 36                       # Windows 11


def colorref(hex_color: str) -> int:
    """#RRGGBB -> COLORREF (0x00BBGGRR)."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return r | (g << 8) | (b << 16)


def apply(hwnd: int, theme: str) -> dict:
    """Paint the title bar of the window. Returns the HRESULT of every call (0 means done);
    on Windows 10 only the dark mode switch works, the exact colours need Windows 11."""
    if not P.IS_WINDOWS or not hwnd:
        return {}
    import ctypes
    from ctypes import wintypes
    fn = ctypes.windll.dwmapi.DwmSetWindowAttribute
    fn.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
    fn.restype = ctypes.c_long

    def put(attr: int, value: int) -> int:
        v = ctypes.c_uint(value)
        return fn(hwnd, attr, ctypes.byref(v), ctypes.sizeof(v)) & 0xFFFFFFFF

    dark = theme != "light"
    caption, text = COLORS["dark" if dark else "light"]
    res = {"dark": put(DWMWA_USE_IMMERSIVE_DARK_MODE, int(dark))}
    if res["dark"]:
        res["dark"] = put(DWMWA_USE_IMMERSIVE_DARK_MODE_OLD, int(dark))
    res["caption"] = put(DWMWA_CAPTION_COLOR, colorref(caption))
    res["border"] = put(DWMWA_BORDER_COLOR, colorref(caption))
    res["text"] = put(DWMWA_TEXT_COLOR, colorref(text))
    return res
