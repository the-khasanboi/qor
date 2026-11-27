import sys
from PySide6.QtWidgets import QApplication

from overlay import OverlayWindow
from settings import AppSettings
from ui import FloatingPauseBar, SettingsWindow, TrayController


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    settings = AppSettings.load()
    overlay = OverlayWindow(settings)
    overlay.show()

    win = SettingsWindow(settings)
    # Show settings on first launch so user immediately sees controls
    win.show()

    pause_bar = FloatingPauseBar(settings, win)
    pause_bar.show()

    def quit_app() -> None:
        settings.save()
        pause_bar.close()
        overlay.close()
        app.quit()

    tray = TrayController(settings, win, quit_app)
    _ = tray  # keep reference alive
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
