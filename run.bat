@echo off
cd /d "%~dp0"
python -c "import PySide6, win32gui, psutil, PIL" 2>nul
if errorlevel 1 (
    echo Installing required Python packages...
    pip install -r requirements.txt
)
start "" pythonw main.py
