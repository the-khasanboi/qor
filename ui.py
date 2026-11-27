from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QColor, QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSlider,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from settings import EFFECTS, AppSettings


def create_snowflake_icon() -> QIcon:
    ico_path = Path(__file__).resolve().parent / "koiart_py.ico"
    if ico_path.exists():
        return QIcon(str(ico_path))
    pm = QPixmap(64, 64)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setBrush(QColor(35, 130, 246))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(4, 4, 56, 56, 14, 14)

    p.setPen(QColor(255, 255, 255))
    font = p.font()
    font.setPointSize(28)
    p.setFont(font)
    p.drawText(pm.rect(), Qt.AlignCenter, "❄")
    p.end()
    return QIcon(pm)


class SettingsWindow(QWidget):
    settings_changed = Signal()

    def __init__(self, settings: AppSettings):
        super().__init__()
        self.settings = settings
        self.setWindowTitle("KoiArt Python — Settings")
        self.setWindowIcon(create_snowflake_icon())
        self.setFixedWidth(440)
        self.setStyleSheet(
            """
            QWidget {
                background-color: #161922;
                color: #eaeef7;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            QLabel#title {
                font-size: 18px;
                font-weight: 700;
                color: #ffffff;
            }
            QLabel#section {
                font-size: 12px;
                font-weight: 600;
                color: #8b95ad;
                margin-top: 6px;
            }
            QPushButton.effectBtn {
                background-color: #212634;
                border: 1px solid #2e3548;
                border-radius: 10px;
                padding: 10px 8px;
                font-weight: 600;
                color: #cfd8ea;
            }
            QPushButton.effectBtn:hover {
                background-color: #293044;
                border-color: #4b7bec;
            }
            QPushButton.effectBtn[active="true"] {
                background-color: #24406e;
                border: 1.5px solid #4fa3ff;
                color: #ffffff;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #282e3f;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #4fa3ff;
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QSlider::sub-page:horizontal {
                background: #3b82f6;
                border-radius: 3px;
            }
            QCheckBox {
                spacing: 8px;
                padding: 3px 0;
            }
            QPushButton#actionBtn {
                background-color: #262c3d;
                border: 1px solid #353e56;
                border-radius: 8px;
                padding: 8px 14px;
                font-weight: 600;
            }
            QPushButton#actionBtn:hover {
                background-color: #323a50;
            }
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("KoiArt Python")
        title.setObjectName("title")
        header.addWidget(title)
        header.addStretch()
        self.pause_btn = QPushButton("Pause" if not settings.paused else "Resume")
        self.pause_btn.setObjectName("actionBtn")
        self.pause_btn.clicked.connect(self._toggle_pause)
        header.addWidget(self.pause_btn)
        root.addLayout(header)

        sec1 = QLabel("WEATHER & SEASONAL EFFECT")
        sec1.setObjectName("section")
        root.addWidget(sec1)

        grid = QGridLayout()
        grid.setSpacing(8)
        self.effect_buttons: dict[str, QPushButton] = {}
        for idx, (key, label, icon) in enumerate(EFFECTS):
            btn = QPushButton(f"{icon}  {label}")
            btn.setProperty("class", "effectBtn")
            btn.setProperty("active", key == settings.effect)
            btn.clicked.connect(lambda _, k=key: self._select_effect(k))
            self.effect_buttons[key] = btn
            grid.addWidget(btn, idx // 2, idx % 2)
        root.addLayout(grid)

        sec2 = QLabel("TUNING")
        sec2.setObjectName("section")
        root.addWidget(sec2)

        self.sliders: dict[str, tuple[QSlider, QLabel]] = {}
        self._add_slider(root, "intensity", "Intensity", 10, 100, settings.intensity)
        self._add_slider(root, "speed", "Speed", 10, 100, settings.speed)
        self._add_slider(root, "wind", "Wind", -100, 100, settings.wind)
        self._add_slider(root, "size", "Particle Size", 20, 100, settings.size)
        self._add_slider(root, "drift_depth", "Snow Drift Depth", 0, 100, settings.drift_depth)
        self._add_slider(root, "tree_count", "Trees (Archalar soni)", 0, 12, settings.tree_count)
        self._add_slider(root, "snowman_count", "Snowmen (Qorbobolar soni)", 0, 10, settings.snowman_count)
        self._add_slider(root, "bulldozer_count", "Bulldozers (Buldozerlar soni)", 0, 5, settings.bulldozer_count)
        self._add_slider(root, "light_size", "Light Size (Chiroqlar kattaligi)", 20, 100, settings.light_size)

        shape_row = QHBoxLayout()
        shape_row.addWidget(QLabel("Snowflake Shape (Qor shakli)"))
        self.shape_combo = QComboBox()
        self.shape_combo.setStyleSheet(
            "QComboBox { background-color: #212634; border: 1px solid #353e56; border-radius: 6px; padding: 4px 10px; color: #eaeef7; }"
        )
        self.shape_combo.addItem("Mixed (Aralash)", "mixed")
        self.shape_combo.addItem("Round (Yumaloq)", "round")
        self.shape_combo.addItem("Star (Yulduzcha)", "star")
        idx = self.shape_combo.findData(settings.snowflake_shape)
        self.shape_combo.setCurrentIndex(max(0, idx))
        self.shape_combo.currentIndexChanged.connect(self._on_shape_changed)
        shape_row.addWidget(self.shape_combo)
        root.addLayout(shape_row)

        sec3 = QLabel("BEHAVIOR & PERFORMANCE")
        sec3.setObjectName("section")
        root.addWidget(sec3)

        self.chk_windows = self._add_check(root, "pile_on_windows", "Pile snow on open windows & taskbar")
        self.chk_mouse = self._add_check(root, "mouse_interact", "Mouse interaction (scatter & plow snow)")
        self.chk_lights = self._add_check(root, "holiday_lights", "Holiday lights across top of screen")
        self.chk_trees = self._add_check(root, "show_trees", "Christmas trees & ornaments (Archa va qo'g'irchoqlar)")
        self.chk_snowmen = self._add_check(root, "show_snowmen", "Snowmen (Qorbobolar)")
        self.chk_bulldozer = self._add_check(root, "show_bulldozer", "Bulldozer snowplow (Buldozer)")
        self.chk_fullscreen = self._add_check(root, "pause_fullscreen", "Pause automatically in fullscreen apps")
        self.chk_battery = self._add_check(root, "battery_saver", "Battery saver (halve FPS on battery)")

        footer = QHBoxLayout()
        reset_btn = QPushButton("Reset Defaults")
        reset_btn.setObjectName("actionBtn")
        reset_btn.clicked.connect(self._reset_defaults)
        footer.addWidget(reset_btn)
        footer.addStretch()
        hide_btn = QPushButton("Hide to Tray")
        hide_btn.setObjectName("actionBtn")
        hide_btn.clicked.connect(self.hide)
        footer.addWidget(hide_btn)
        root.addLayout(footer)

    def _add_slider(self, layout: QVBoxLayout, attr: str, label: str, lo: int, hi: int, val: int) -> None:
        row = QHBoxLayout()
        lbl = QLabel(label)
        val_lbl = QLabel(str(val))
        val_lbl.setMinimumWidth(36)
        val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        slider = QSlider(Qt.Horizontal)
        slider.setRange(lo, hi)
        slider.setValue(val)

        def on_change(v: int) -> None:
            setattr(self.settings, attr, v)
            val_lbl.setText(str(v))
            self.settings.save()
            self.settings_changed.emit()

        slider.valueChanged.connect(on_change)
        row.addWidget(lbl)
        row.addWidget(slider, 1)
        row.addWidget(val_lbl)
        layout.addLayout(row)
        self.sliders[attr] = (slider, val_lbl)

    def _add_check(self, layout: QVBoxLayout, attr: str, label: str) -> QCheckBox:
        chk = QCheckBox(label)
        chk.setChecked(bool(getattr(self.settings, attr)))

        def on_toggle(state: bool) -> None:
            setattr(self.settings, attr, state)
            self.settings.save()
            self.settings_changed.emit()

        chk.toggled.connect(on_toggle)
        layout.addWidget(chk)
        return chk

    def _select_effect(self, key: str) -> None:
        self.settings.effect = key
        for k, btn in self.effect_buttons.items():
            btn.setProperty("active", k == key)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.settings.save()
        self.settings_changed.emit()

    def _on_shape_changed(self) -> None:
        self.settings.snowflake_shape = self.shape_combo.currentData()
        self.settings.save()
        self.settings_changed.emit()

    def _toggle_pause(self) -> None:
        self.settings.paused = not self.settings.paused
        self.pause_btn.setText("Resume" if self.settings.paused else "Pause")
        self.settings.save()
        self.settings_changed.emit()

    def _reset_defaults(self) -> None:
        defaults = AppSettings()
        for field in defaults.__dataclass_fields__:
            setattr(self.settings, field, getattr(defaults, field))
        self.sync_from_settings()
        self.settings.save()
        self.settings_changed.emit()

    def sync_from_settings(self) -> None:
        for k, btn in self.effect_buttons.items():
            btn.setProperty("active", k == self.settings.effect)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        for attr, (slider, val_lbl) in self.sliders.items():
            v = getattr(self.settings, attr)
            slider.blockSignals(True)
            slider.setValue(v)
            slider.blockSignals(False)
            val_lbl.setText(str(v))
        self.chk_windows.setChecked(self.settings.pile_on_windows)
        self.chk_mouse.setChecked(self.settings.mouse_interact)
        self.chk_lights.setChecked(self.settings.holiday_lights)
        self.chk_trees.setChecked(self.settings.show_trees)
        self.chk_snowmen.setChecked(self.settings.show_snowmen)
        self.chk_bulldozer.setChecked(self.settings.show_bulldozer)
        self.chk_fullscreen.setChecked(self.settings.pause_fullscreen)
        self.chk_battery.setChecked(self.settings.battery_saver)
        idx = self.shape_combo.findData(self.settings.snowflake_shape)
        self.shape_combo.blockSignals(True)
        self.shape_combo.setCurrentIndex(max(0, idx))
        self.shape_combo.blockSignals(False)
        self.pause_btn.setText("Resume" if self.settings.paused else "Pause")

    def closeEvent(self, event) -> None:
        event.ignore()
        self.hide()


class TrayController:
    def __init__(self, settings: AppSettings, win: SettingsWindow, on_quit):
        self.settings = settings
        self.win = win
        self.tray = QSystemTrayIcon(create_snowflake_icon())
        self.tray.setToolTip("KoiArt Python")

        menu = QMenu()
        open_act = QAction("Open Settings", menu)
        open_act.triggered.connect(self._show_settings)
        menu.addAction(open_act)

        self.pause_act = QAction("Pause", menu)
        self.pause_act.triggered.connect(self.win._toggle_pause)
        menu.addAction(self.pause_act)

        menu.addSeparator()
        eff_menu = menu.addMenu("Effects")
        self.eff_actions: dict[str, QAction] = {}
        for key, label, icon in EFFECTS:
            act = QAction(f"{icon} {label}", eff_menu, checkable=True)
            act.setChecked(key == settings.effect)
            act.triggered.connect(lambda _, k=key: self._set_effect(k))
            eff_menu.addAction(act)
            self.eff_actions[key] = act

        menu.addSeparator()
        quit_act = QAction("Exit", menu)
        quit_act.triggered.connect(on_quit)
        menu.addAction(quit_act)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_activated)
        self.win.settings_changed.connect(self.refresh_menu)
        self.tray.show()

    def _show_settings(self) -> None:
        self.win.sync_from_settings()
        self.win.show()
        self.win.raise_()
        self.win.activateWindow()

    def _set_effect(self, key: str) -> None:
        self.win._select_effect(key)

    def refresh_menu(self) -> None:
        self.pause_act.setText("Resume" if self.settings.paused else "Pause")
        for k, act in self.eff_actions.items():
            act.setChecked(k == self.settings.effect)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self._show_settings()


class FloatingPauseBar(QWidget):
    """Always-visible compact Pause/Resume pill at the bottom-right above the taskbar."""

    def __init__(self, settings: AppSettings, win: SettingsWindow):
        super().__init__()
        self.settings = settings
        self.win = win
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        self.pause_btn = QPushButton()
        self.pause_btn.setCursor(Qt.PointingHandCursor)
        self.pause_btn.clicked.connect(self.win._toggle_pause)

        self.cfg_btn = QPushButton("⚙")
        self.cfg_btn.setCursor(Qt.PointingHandCursor)
        self.cfg_btn.setToolTip("Settings")
        self.cfg_btn.clicked.connect(self._open_settings)

        self.setStyleSheet(
            """
            QPushButton {
                background-color: rgba(22, 25, 34, 215);
                color: #eaeef7;
                border: 1px solid rgba(96, 165, 250, 140);
                border-radius: 14px;
                padding: 5px 12px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(36, 64, 110, 235);
                border-color: #60a5fa;
            }
            """
        )

        layout.addWidget(self.pause_btn)
        layout.addWidget(self.cfg_btn)

        self.win.settings_changed.connect(self.refresh)
        self.refresh()
        self._position_bottom_right()

    def _position_bottom_right(self) -> None:
        self.adjustSize()
        screen = QGuiApplication.primaryScreen()
        avail = screen.availableGeometry() if screen else self.geometry()
        x = avail.right() - self.width() - 14
        y = avail.bottom() - self.height() - 10
        self.move(x, y)

    def _open_settings(self) -> None:
        self.win.sync_from_settings()
        self.win.show()
        self.win.raise_()
        self.win.activateWindow()

    def refresh(self) -> None:
        if self.settings.paused:
            self.pause_btn.setText("▶ Resume")
        else:
            self.pause_btn.setText("⏸ Pause")
        self._position_bottom_right()
