"""
external_resources.py — handles resources GrapesJS's static parser can
never make work, because they require live JS execution or a network
fetch GrapesJS doesn't perform during import.

Two known cases, found on a real file:

1. Tailwind's Play/runtime CDN (<script src="...cdn.tailwindcss.com...">).
   This isn't pre-built CSS — it's a script that scans the live DOM and
   generates utility CSS on the fly. GrapesJS never executes imported
   <script> tags (reasonably — arbitrary script execution during editing
   would be unsafe), so this style generation simply never happens, and
   the ENTIRE page renders unstyled. Confirmed as the dominant cause on a
   real file, not guessed.

   Fix: detect it, strip it from the canvas-bound HTML, and separately
   inject a locally-bundled copy of Tailwind's real, official browser
   engine (@tailwindcss/browser, MIT, zero deps) as an actual live <script>
   DOM node in the canvas iframe — not parsed by GrapesJS, so it genuinely
   executes and generates real, accurate utility CSS from the real classes
   present. The ORIGINAL script tag is preserved separately so export can
   restore it byte-for-byte — the live site keeps depending on the real
   CDN exactly as it does today; only the local editor preview substitutes
   a local copy of the same engine.

2. External stylesheets (<link rel="stylesheet" href="https://...">, e.g.
   Google Fonts). These aren't dropped deliberately anywhere in this
   pipeline, but a full HTML document handed to GrapesJS only keeps <body>
   content — head-level <link> tags never reach the canvas at all. Fix:
   extract them and inject real <link> elements directly into the canvas
   iframe's <head>, so the browser's normal network stack can fetch them
   (this only requires the user's own internet access, not the app's
   offline-by-default UI — the app's own chrome never depends on this).
"""

import re

_TAILWIND_CDN_SCRIPT_RE = re.compile(
    r"<script\b[^>]*\bsrc=[\"'][^\"']*cdn\.tailwindcss\.com[^\"']*[\"'][^>]*>\s*</script>",
    re.IGNORECASE,
)

_LINK_TAG_RE = re.compile(r"<link\b[^>]*>", re.IGNORECASE)
_REL_STYLESHEET_RE = re.compile(r'\brel=["\']stylesheet["\']', re.IGNORECASE)
_HREF_RE = re.compile(r'\bhref=["\'](https?://[^"\']+)["\']', re.IGNORECASE)


def extract_tailwind_cdn_script(html):
    """
    Returns (html_without_it, original_script_tag_or_None).
    original_script_tag is preserved verbatim so export can restore it —
    the deployed site should keep depending on the real CDN unchanged.
    """
    match = _TAILWIND_CDN_SCRIPT_RE.search(html)
    if not match:
        return html, None
    original_tag = match.group(0)
    html = _TAILWIND_CDN_SCRIPT_RE.sub("", html, count=1)
    return html, original_tag


def extract_external_stylesheets(html):
    """
    Returns (html_without_them, list_of_hrefs). The <link> tags are removed
    from the HTML handed to GrapesJS (they'd be dropped anyway once only
    <body> is kept, and leaving them in body-adjacent markup is pointless)
    — the caller injects real <link> elements into the canvas directly.

    Attribute order in real HTML is arbitrary (found a real tag with href
    BEFORE rel) — matches the whole tag first, then checks each attribute
    independently rather than assuming an order.
    """
    hrefs = []

    def repl(m):
        tag = m.group(0)
        if not _REL_STYLESHEET_RE.search(tag):
            return tag
        href_match = _HREF_RE.search(tag)
        if not href_match:
            return tag
        hrefs.append(href_match.group(1))
        return ""

    html = _LINK_TAG_RE.sub(repl, html)
    return html, hrefs
