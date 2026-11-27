# KoiArt Python

Desktop weather, snow drifts, holiday lights, Christmas trees, snowmen, and snowplow bulldozer overlay for Windows — built in Python with `PySide6` and Win32 APIs.

## Features

- **6 Weather & Seasonal Effects:** Snow (round, 6-pointed star crystals, or mixed), Sakura, Autumn Leaves, Rain & Lightning, Fireflies, Starfall.
- **Snow Drifts & Window Piling:** Snow accumulates along the top of the Windows taskbar and open window titlebars.
- **Interactive Scenery:**
  - Animated **Bulldozers** (0–5) driving along the taskbar and plowing snow.
  - **Christmas Trees** (0–12) with glowing ornaments and golden stars.
  - **Snowmen** (0–10) with fluttering scarves.
  - **Holiday Lights** across the top of the screen with adjustable bulb size.
- **Mouse Interaction:** Sweep your cursor to scatter snowflakes, plow drifts, and wobble trees/snowmen.
- **Smart Performance:** Click-through transparent overlay (`WS_EX_TRANSPARENT`), automatic pause in fullscreen apps, and FPS halving on battery.

## Quick Start (Windows 10/11)

```bash
git clone https://github.com/the-khasanboi/qor.git
cd qor
pip install -r requirements.txt
pythonw main.py
```

Or run with console output:

```bash
python main.py
```

## Build Standalone `.exe` (Optional)

```bash
pip install pyinstaller
pyinstaller --noconsole --onefile --icon=koiart_py.ico --add-data "koiart_py.ico;." --name "KoiArtPy" main.py
```
