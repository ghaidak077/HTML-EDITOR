"""
api.py — the Python <-> JS bridge exposed to editor.js as `pywebview.api.*`

Every method here follows the same contract:
    - always returns a dict: {"ok": True, ...} or {"ok": False, "error": "..."}
    - never raises an exception across the JS bridge (JS side gets a clean error object, not a crash)

Phase 1: open_file, save_draft, export_html are real. export_html writes RAW
html/css with no cleanup yet — the sanitizer lands in Phase 2.
"""

import os
import re
import json
import traceback

import webview

import config
from asset_resolver import resolve_local_assets, reverse_asset_rewrite
from style_extractor import extract_and_strip_styles
from external_resources import extract_tailwind_cdn_script, extract_external_stylesheets

# pywebview renamed its dialog-type constants across versions:
# older releases: webview.OPEN_DIALOG / webview.SAVE_DIALOG
# newer releases: webview.FileDialog.OPEN / webview.FileDialog.SAVE
# Resolve whichever is actually available instead of hardcoding one.
try:
    _DIALOG_OPEN = webview.FileDialog.OPEN
    _DIALOG_SAVE = webview.FileDialog.SAVE
except AttributeError:
    _DIALOG_OPEN = webview.OPEN_DIALOG
    _DIALOG_SAVE = webview.SAVE_DIALOG


def _unwrap_dialog_path(result):
    """
    create_file_dialog's return type is inconsistent across pywebview versions:
    some return a list/tuple of paths, others return a bare string. Indexing a
    bare string with [0] silently grabs its first CHARACTER, not the path —
    that bug produced a 1-letter file named after the path's drive letter.
    This normalizes both cases to a plain path string.
    """
    if isinstance(result, (list, tuple)):
        return result[0]
    return result


class Api:
    # Note: do NOT store the pywebview window object as an attribute here.
    # pywebview inspects every attribute of this class to find bindable JS
    # functions, and recursing into a live Window object touches an internal
    # DOM property before the page has loaded, which crashes the app.
    # When a method needs the window (native dialogs), fetch it fresh with
    # webview.windows[0] inside the method — never cache it.

    # ---- Phase 1 ----

    def open_file(self):
        """Opens a native file dialog, reads the chosen .html file, returns its contents."""
        try:
            window = webview.windows[0]
            result = window.create_file_dialog(
                _DIALOG_OPEN,
                allow_multiple=False,
                file_types=("HTML Files (*.html;*.htm)", "All files (*.*)"),
            )
            if not result:
                return {"ok": False, "error": "cancelled"}

            path = _unwrap_dialog_path(result)
            with open(path, "r", encoding="utf-8") as f:
                html = f.read()

            html, missing_assets, asset_map = resolve_local_assets(html, path)
            html, imported_css = extract_and_strip_styles(html)
            html, tailwind_cdn_script = extract_tailwind_cdn_script(html)
            html, external_stylesheets = extract_external_stylesheets(html)

            # Only read the (282KB) bundled Tailwind engine when actually needed.
            # Passed as text, not a src path — fetch()/script-src on file://
            # URLs is often blocked by browser security policy; inline text
            # sidesteps that entirely, same approach as imported_css.
            tailwind_engine_js = None
            if tailwind_cdn_script:
                engine_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), "assets", "tailwindcss-browser.min.js"
                )
                try:
                    with open(engine_path, "r", encoding="utf-8") as f:
                        tailwind_engine_js = f.read()
                except OSError:
                    tailwind_engine_js = None

            return {
                "ok": True,
                "html": html,
                "imported_css": imported_css,
                "path": path,
                "missing_assets": missing_assets,
                "asset_map": asset_map,
                "tailwind_cdn_script": tailwind_cdn_script,
                "tailwind_engine_js": tailwind_engine_js,
                "external_stylesheets": external_stylesheets,
            }
        except Exception as e:
            traceback.print_exc()
            return {"ok": False, "error": str(e)}

    def save_draft(self, project_data_json):
        """Writes the full GrapesJS component-tree state (JSON string from JS) to drafts/current.json."""
        try:
            os.makedirs(config.DRAFTS_DIR, exist_ok=True)
            path = os.path.join(config.DRAFTS_DIR, config.CURRENT_DRAFT_FILE)

            # project_data_json arrives as a JSON string from JS. Validate before writing
            # so a malformed draft never silently corrupts the save file.
            parsed = json.loads(project_data_json)

            with open(path, "w", encoding="utf-8") as f:
                json.dump(parsed, f, indent=2)

            return {"ok": True, "path": path}
        except Exception as e:
            traceback.print_exc()
            return {"ok": False, "error": str(e)}

    def export_html(self, html, css, asset_map_json="{}", imported_css="", tailwind_cdn_script="", external_stylesheets_json="[]"):
        """
        Assembles a standalone HTML document from the canvas's html/css and writes it
        via a native save dialog. NO SANITIZING YET (Phase 2) — this is raw output.

        tailwind_cdn_script and external_stylesheets_json restore exactly what
        was pulled out on open (see external_resources.py) — the exported file
        must keep depending on the real CDN/fonts exactly as the original did,
        unaffected by the local-preview substitution used for canvas editing.
        """
        try:
            asset_map = json.loads(asset_map_json) if asset_map_json else {}
            external_stylesheets = json.loads(external_stylesheets_json) if external_stylesheets_json else []

            full_css = (imported_css + "\n\n" + css) if imported_css else css
            full_css = reverse_asset_rewrite(full_css, asset_map)
            html = reverse_asset_rewrite(html, asset_map)

            window = webview.windows[0]
            result = window.create_file_dialog(
                _DIALOG_SAVE,
                save_filename="export.html",
                file_types=("HTML Files (*.html)",),
            )
            if not result:
                return {"ok": False, "error": "cancelled"}

            path = _unwrap_dialog_path(result)

            stylesheet_links = "\n".join(
                f'  <link rel="stylesheet" href="{href}">' for href in external_stylesheets
            )
            tailwind_tag = f"  {tailwind_cdn_script}\n" if tailwind_cdn_script else ""

            full_html = (
                "<!DOCTYPE html>\n"
                '<html lang="en">\n'
                "<head>\n"
                '  <meta charset="UTF-8" />\n'
                f"{stylesheet_links}\n"
                f"{tailwind_tag}"
                "  <style>\n"
                f"{full_css}\n"
                "  </style>\n"
                "</head>\n"
                "<body>\n"
                f"{html}\n"
                "</body>\n"
                "</html>\n"
            )

            with open(path, "w", encoding="utf-8") as f:
                f.write(full_html)

            return {"ok": True, "path": path}
        except Exception as e:
            traceback.print_exc()
            return {"ok": False, "error": str(e)}

    # ---- Phase 5 (pulled forward) ----

    def list_components(self):
        """Lists saved component files from /components/*.html, with their content."""
        try:
            os.makedirs(config.COMPONENTS_DIR, exist_ok=True)
            components = []
            for filename in sorted(os.listdir(config.COMPONENTS_DIR)):
                if not filename.lower().endswith(".html"):
                    continue
                path = os.path.join(config.COMPONENTS_DIR, filename)
                with open(path, "r", encoding="utf-8") as f:
                    html = f.read()
                name = filename[: -len(".html")]
                components.append({"name": name, "html": html})
            return {"ok": True, "components": components}
        except Exception as e:
            traceback.print_exc()
            return {"ok": False, "error": str(e)}

    def save_component(self, name, html):
        """Saves a selected element/section as a new named component file (flat, no folders)."""
        try:
            if not name or not name.strip():
                return {"ok": False, "error": "Component name cannot be empty"}

            # Sanitize: strip anything that isn't alphanumeric/space/dash/underscore,
            # so a name can never escape the components directory (no path traversal).
            safe_name = re.sub(r"[^A-Za-z0-9 _-]", "", name).strip()
            if not safe_name:
                return {"ok": False, "error": "Component name must contain at least one letter or number"}

            os.makedirs(config.COMPONENTS_DIR, exist_ok=True)
            path = os.path.join(config.COMPONENTS_DIR, f"{safe_name}.html")

            with open(path, "w", encoding="utf-8") as f:
                f.write(html)

            return {"ok": True, "name": safe_name, "path": path}
        except Exception as e:
            traceback.print_exc()
            return {"ok": False, "error": str(e)}
