"""
main.py — app entry point.

Run with:  python main.py
Packaged later (Phase 9) into a single .exe via PyInstaller.
"""

import os
import sys
import webview

from api import Api
import config


def resource_path(relative_path):
    """
    Resolves a path that works both in dev (running main.py directly)
    and inside a PyInstaller-frozen .exe (where files are unpacked to sys._MEIPASS).
    """
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def main():
    api = Api()

    webview.create_window(
        config.APP_TITLE,
        resource_path("editor.html"),
        js_api=api,
        width=config.WINDOW_WIDTH,
        height=config.WINDOW_HEIGHT,
        min_size=(config.WINDOW_MIN_WIDTH, config.WINDOW_MIN_HEIGHT),
    )

    # Ensure drafts/components dirs exist next to the app
    os.makedirs(config.DRAFTS_DIR, exist_ok=True)
    os.makedirs(config.COMPONENTS_DIR, exist_ok=True)

    webview.start(debug=False)


if __name__ == "__main__":
    main()
