"""
style_extractor.py — pulls <style> blocks out of imported HTML.

Why: GrapesJS models embedded CSS as editable rules via its CssComposer,
which (per GrapesJS's own docs on custom CSS parsers) can't fully trust
standard CSS parsing — browsers and parsers disagree on serialization, and
build-tool-compiled CSS (Tailwind's purged output, escaped arbitrary-value
selectors, oklch() colors, etc.) is exactly the kind of complex real-world
CSS this breaks on. Confirmed root cause on a real file: Tailwind's `w-4
h-4` sizing classes silently failed to apply, causing an icon meant to be
16x16px to render at unconstrained native size.

Fix: don't ask GrapesJS to parse/model this CSS as rules at all. Extract it
and inject it as a plain <style> tag directly into the canvas — the
browser's own CSS engine (which handles all of this correctly) renders it,
full fidelity, no parsing losses. Trade-off, stated plainly: this CSS is no
longer editable rule-by-rule through the Style Manager (nobody hand-edits
compiled Tailwind output through a GUI panel anyway) — but GrapesJS's own
Style Manager and Brand Kit still work normally for anything the user adds
or edits themselves, since those go through GrapesJS's CssComposer as a
separate, later stylesheet that still cascades on top correctly.
"""

import re

_STYLE_BLOCK_RE = re.compile(r"<style[^>]*>(.*?)</style>", re.DOTALL | re.IGNORECASE)


def extract_and_strip_styles(html):
    """
    Returns (html_without_style_blocks, combined_raw_css).
    Run this AFTER asset path resolution, so any font/image url()
    references inside the extracted CSS are already fixed to real paths.
    """
    blocks = _STYLE_BLOCK_RE.findall(html)
    combined_css = "\n\n".join(b.strip() for b in blocks if b.strip())
    html_without_styles = _STYLE_BLOCK_RE.sub("", html)
    return html_without_styles, combined_css
