"""
asset_resolver.py — fixes "broken" imports of real, already-hosted websites.

The problem this solves: a real static site is normally index.html PLUS a
folder of images/fonts/logos next to it (not one single self-contained
file). When only the HTML text is read and handed to the canvas, every
relative image/font reference points at nothing — the canvas has no way to
know those files exist right next to the HTML on disk. That's not a "no
internet access" problem (most real sites don't load fonts/images from a
CDN at all) — it's a missing-local-file-context problem.

Fix: rewrite every local asset reference to an absolute file:// URI pointing
at the real file next to the opened HTML, using pathlib for correct
cross-platform URI encoding (handles Windows drive letters, spaces, and
special characters correctly — manual string concatenation would not).
"""

import os
import re
import secrets
from pathlib import Path

_ATTR_RE = re.compile(r'\b(src|href)="([^"]*)"')
_SRCSET_RE = re.compile(r'\bsrcset="([^"]*)"')
_CSS_URL_RE = re.compile(r"url\((['\"]?)([^'\")]+)\1\)")
_SCRIPT_BLOCK_RE = re.compile(r"<script\b[^>]*>.*?</script>", re.DOTALL | re.IGNORECASE)

_IGNORE_PREFIXES = ("http://", "https://", "data:", "mailto:", "tel:", "javascript:", "file:", "#", "%23")


def _mask_scripts(html):
    """
    <script> blocks can contain JS that looks like an HTML attribute (e.g. a
    template literal `src="${imgSrc}"` inside dynamic gallery code) — found
    on a real file, where it got misidentified as a broken asset reference.
    Masking script contents before any regex rewriting means nothing inside
    <script> tags is ever touched, regardless of what it happens to contain.
    """
    token = secrets.token_hex(8)
    scripts = []

    def repl(m):
        scripts.append(m.group(0))
        return f"@@SCRIPT_{token}_{len(scripts) - 1}@@"

    masked = _SCRIPT_BLOCK_RE.sub(repl, html)
    return masked, scripts, token


def _unmask_scripts(html, scripts, token):
    for i, original in enumerate(scripts):
        html = html.replace(f"@@SCRIPT_{token}_{i}@@", original)
    return html


def _is_local_asset_path(value):
    value = value.strip()
    if not value:
        return False
    return not value.startswith(_IGNORE_PREFIXES)


def _resolve_to_file_uri(folder, rel_path, missing_list):
    """
    Root-relative paths (leading '/') are treated as relative to the site's
    folder, not the OS filesystem root — that's the only interpretation that
    makes sense for a self-contained static export sitting in one folder.
    Returns None (and records it) if the file genuinely isn't there, so the
    original reference is left untouched rather than pointed at a guess.
    """
    cleaned = rel_path.lstrip("/")
    full_path = os.path.normpath(os.path.join(folder, cleaned))
    if os.path.isfile(full_path):
        return Path(full_path).as_uri()
    missing_list.append(rel_path)
    return None


def resolve_local_assets(html, html_file_path):
    """
    Returns (rewritten_html, missing_assets, asset_map).

    missing_assets lists any local references that couldn't be found next to
    the HTML file. asset_map is {file_uri: original_value} for everything
    that WAS rewritten — this must be kept and used to reverse the rewrite
    before final export. Without reversing it, an exported file would ship
    with hardcoded file:///C:/Users/... paths baked in instead of the
    original portable relative paths, breaking the moment it's deployed
    anywhere other than this machine. This rewrite is for local canvas
    preview only, never for the final exported artifact.
    """
    folder = os.path.dirname(os.path.abspath(html_file_path))
    missing = []
    asset_map = {}

    def _resolve(value):
        uri = _resolve_to_file_uri(folder, value, missing)
        if uri:
            asset_map[uri] = value
        return uri

    def repl_attr(m):
        attr, value = m.group(1), m.group(2)
        if not _is_local_asset_path(value):
            return m.group(0)
        uri = _resolve(value)
        if uri is None:
            return m.group(0)
        return f'{attr}="{uri}"'

    def repl_srcset(m):
        candidates = [c.strip() for c in m.group(1).split(",") if c.strip()]
        rewritten = []
        for candidate in candidates:
            parts = candidate.split()
            url, descriptor = parts[0], " ".join(parts[1:])
            if _is_local_asset_path(url):
                uri = _resolve(url)
                if uri:
                    url = uri
            rewritten.append(url + (f" {descriptor}" if descriptor else ""))
        return 'srcset="' + ", ".join(rewritten) + '"'

    def repl_css_url(m):
        quote, value = m.group(1), m.group(2)
        if not _is_local_asset_path(value):
            return m.group(0)
        uri = _resolve(value)
        if uri is None:
            return m.group(0)
        return f"url({quote}{uri}{quote})"

    html, scripts, token = _mask_scripts(html)

    html = _ATTR_RE.sub(repl_attr, html)
    html = _SRCSET_RE.sub(repl_srcset, html)
    html = _CSS_URL_RE.sub(repl_css_url, html)

    html = _unmask_scripts(html, scripts, token)

    # Dedupe the missing list while preserving order (the same missing asset
    # may appear multiple times, e.g. used in both <img> and CSS background).
    seen = set()
    unique_missing = []
    for item in missing:
        if item not in seen:
            seen.add(item)
            unique_missing.append(item)

    return html, unique_missing, asset_map


def reverse_asset_rewrite(html_or_css, asset_map):
    """
    Undoes resolve_local_assets' rewrite before final export — swaps every
    file:// URI back to its original portable relative path. Call this on
    both the html and css strings at export time.
    """
    for file_uri, original_value in asset_map.items():
        html_or_css = html_or_css.replace(file_uri, original_value)
    return html_or_css
