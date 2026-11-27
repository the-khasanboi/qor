import time
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication, QPainter
from PySide6.QtWidgets import QWidget

from effects import WeatherEngine
from settings import AppSettings
from win_utils import (
    get_cursor_pos,
    get_taskbar_top,
    get_visible_window_tops,
    is_fullscreen_active,
    is_on_battery,
    make_window_click_through,
)


class OverlayWindow(QWidget):
    def __init__(self, settings: AppSettings):
        super().__init__()
        self.settings = settings
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowTransparentForInput
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        screen = QGuiApplication.primaryScreen()
        geo = screen.geometry() if screen else self.geometry()
        self.setGeometry(geo)

        self.engine = WeatherEngine(geo.width(), geo.height())
        self.last_tick = time.perf_counter()
        self.env_timer = 0.0
        self.taskbar_y = geo.height() - 48
        self.window_tops: list[tuple[int, int, int]] = []
        self.paused_by_fullscreen = False
        self.battery_mode = False
        self._click_through_applied = False

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_frame)
        self.timer.start(16)  # ~60 FPS

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._click_through_applied:
            make_window_click_through(int(self.winId()))
            self._click_through_applied = True

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.engine.resize(self.width(), self.height())

    def _on_frame(self) -> None:
        now = time.perf_counter()
        dt = min(0.05, max(0.001, now - self.last_tick))
        self.last_tick = now

        hwnd = int(self.winId())
        self.env_timer += dt
        if self.env_timer >= 0.45:
            self.env_timer = 0.0
            self.taskbar_y = get_taskbar_top(self.height())
            if self.settings.pile_on_windows and self.settings.effect == "snow":
                self.window_tops = get_visible_window_tops(hwnd, self.width(), self.height())
            else:
                self.window_tops = []

            self.paused_by_fullscreen = (
                self.settings.pause_fullscreen and is_fullscreen_active(hwnd)
            )
            on_bat = self.settings.battery_saver and is_on_battery()
            if on_bat != self.battery_mode:
                self.battery_mode = on_bat
                self.timer.setInterval(33 if on_bat else 16)

        if self.settings.paused or self.paused_by_fullscreen:
            if self.isVisible():
                self.update()
            return

        cursor = get_cursor_pos()
        # Convert global cursor to local widget coordinates
        origin = self.geometry().topLeft()
        local_cursor = (cursor[0] - origin.x(), cursor[1] - origin.y())

        self.engine.update(dt, self.settings, self.taskbar_y, self.window_tops, local_cursor)
        self.update()

    def paintEvent(self, event) -> None:
        if self.settings.paused or self.paused_by_fullscreen:
            return
        painter = QPainter(self)
        self.engine.render(painter, self.settings)
        painter.end()
