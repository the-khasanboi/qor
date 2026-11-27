import json
from dataclasses import dataclass, asdict
from pathlib import Path

SETTINGS_PATH = Path.home() / ".koiart_py_settings.json"

EFFECTS = [
    ("snow", "Snow", "❄️"),
    ("sakura", "Sakura", "🌸"),
    ("leaves", "Autumn Leaves", "🍂"),
    ("rain", "Rain & Lightning", "🌧️"),
    ("fireflies", "Fireflies", "✨"),
    ("starfall", "Starfall", "🌠"),
]


@dataclass
class AppSettings:
    effect: str = "snow"
    intensity: int = 65        # 10..100
    speed: int = 55            # 10..100
    wind: int = 35             # -100..100
    size: int = 50             # 20..100
    drift_depth: int = 70      # 0..100 (for snow)
    snowflake_shape: str = "mixed"  # "mixed", "round", "star"
    tree_count: int = 5        # 0..12
    snowman_count: int = 3     # 0..10
    bulldozer_count: int = 1   # 0..5
    light_size: int = 50       # 20..100
    pile_on_windows: bool = True
    mouse_interact: bool = True
    holiday_lights: bool = True
    show_trees: bool = True
    show_snowmen: bool = True
    show_bulldozer: bool = True
    pause_fullscreen: bool = True
    battery_saver: bool = True
    paused: bool = False

    def save(self) -> None:
        try:
            SETTINGS_PATH.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        except OSError:
            pass

    @classmethod
    def load(cls) -> "AppSettings":
        if SETTINGS_PATH.exists():
            try:
                data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
                valid = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
                return cls(**valid)
            except (OSError, json.JSONDecodeError, TypeError):
                pass
        return cls()
