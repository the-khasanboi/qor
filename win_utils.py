import ctypes
from ctypes import wintypes
import psutil
import win32api
import win32con
import win32gui


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


def make_window_click_through(hwnd: int) -> None:
    """Apply Win32 extended styles so all mouse/keyboard input passes through."""
    ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    ex_style |= (
        win32con.WS_EX_LAYERED
        | win32con.WS_EX_TRANSPARENT
        | win32con.WS_EX_TOOLWINDOW
        | win32con.WS_EX_NOACTIVATE
    )
    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)


def get_cursor_pos() -> tuple[int, int]:
    try:
        return win32gui.GetCursorPos()
    except Exception:
        return (-10000, -10000)


def get_taskbar_top(screen_height: int) -> int:
    """Return the Y coordinate of the top edge of the primary Windows taskbar."""
    try:
        hwnd = win32gui.FindWindow("Shell_TrayWnd", None)
        if hwnd:
            rect = win32gui.GetWindowRect(hwnd)
            # Bottom-docked taskbar
            if rect[1] > screen_height * 0.5 and rect[3] >= screen_height - 4:
                return rect[1]
    except Exception:
        pass
    return screen_height - 48


def get_visible_window_tops(exclude_hwnd: int, screen_w: int, screen_h: int) -> list[tuple[int, int, int]]:
    """
    Return a list of (left, right, top_y) for visible, non-minimized top-level windows
    so snow can pile up along their top edges, just like KoiArt.
    """
    surfaces: list[tuple[int, int, int]] = []
    dwm = ctypes.windll.dwmapi
    DWMWA_CLOAKED = 14

    def enum_cb(hwnd: int, _):
        if hwnd == exclude_hwnd:
            return True
        if not win32gui.IsWindowVisible(hwnd) or win32gui.IsIconic(hwnd):
            return True
        # Skip tool windows / invisible cloaked UWP windows
        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        if ex_style & win32con.WS_EX_TOOLWINDOW:
            return True
        cloaked = ctypes.c_int(0)
        if dwm.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked)) == 0:
            if cloaked.value != 0:
                return True
        cls_name = win32gui.GetClassName(hwnd)
        if cls_name in ("Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"):
            return True
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return True
        try:
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        except Exception:
            return True
        if right - left < 120 or bottom - top < 80:
            return True
        if top < 20 or top > screen_h - 60:
            return True
        if right <= 0 or left >= screen_w:
            return True
        # Clamp horizontally
        l_clamped = max(0, left)
        r_clamped = min(screen_w, right)
        if r_clamped - l_clamped >= 80:
            surfaces.append((l_clamped, r_clamped, top))
        return True

    try:
        win32gui.EnumWindows(enum_cb, None)
    except Exception:
        pass
    # Keep top few windows to avoid clutter
    return surfaces[:8]


def is_fullscreen_active(exclude_hwnd: int) -> bool:
    """Detect if the foreground window covers the entire monitor."""
    try:
        fg = win32gui.GetForegroundWindow()
        if not fg or fg == exclude_hwnd:
            return False
        cls_name = win32gui.GetClassName(fg)
        if cls_name in ("Progman", "WorkerW", "Shell_TrayWnd"):
            return False
        rect = win32gui.GetWindowRect(fg)
        mon = win32api.MonitorFromWindow(fg, win32con.MONITOR_DEFAULTTONEAREST)
        mon_info = win32api.GetMonitorInfo(mon)
        m_rect = mon_info["Monitor"]
        return (
            rect[0] <= m_rect[0]
            and rect[1] <= m_rect[1]
            and rect[2] >= m_rect[2]
            and rect[3] >= m_rect[3]
        )
    except Exception:
        return False


def is_on_battery() -> bool:
    try:
        bat = psutil.sensors_battery()
        if bat is not None:
            return not bat.power_plugged
    except Exception:
        pass
    return False
