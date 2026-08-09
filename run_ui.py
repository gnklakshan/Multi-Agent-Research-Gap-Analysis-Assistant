from __future__ import annotations

import sys
from pathlib import Path

# Ensure src package is discoverable
sys.path.insert(0, str(Path(__file__).parent))

from src.ui.app import create_ui
from nicegui import ui

if __name__ in {"__main__", "__mp_main__"}:
    print("\n" + "="*60)
    print("Launching PaperGap AI - Research Gap Assistant UI...")
    print("Open http://localhost:8085 in your browser")
    print("="*60 + "\n")
    create_ui()
    ui.run(title="PaperGap AI - Research Gap Assistant", dark=True, port=8085, reload=False)
