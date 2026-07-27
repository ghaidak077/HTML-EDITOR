# Visual HTML Editor — Project Reference

## Purpose
A native Windows desktop app for a designer (non-coder) to visually edit single-file
HTML pages (usually AI-generated) — click text to edit, adjust style, drag elements,
add/delete elements — then export clean, professional-grade HTML. Solo use, local files only.

## Stack (fixed, do not substitute)
- pywebview (Python) — native window + Python<->JS bridge
- GrapesJS core + grapesjs-preset-webpage — editor engine
- PyInstaller — packages to a single .exe
- Storage: local JSON/HTML files only. No DB, no server, no network calls at runtime.
  GrapesJS assets are bundled locally in /assets/grapesjs (not CDN-loaded) so the
  packaged app works fully offline.

## Non-goals
No accounts/login/cloud sync, no multi-user, no in-app AI generation, no React/Vue/build
pipelines, no hosting/deployment features, no mobile/web version.

## Architecture
```
main.py         -> creates the pywebview window, loads editor.html, wires up Api
api.py          -> Api class: open_file, save_draft, export_html, list_components,
                    save_component. Every method returns {"ok": bool, ...} — never
                    raises across the JS bridge.
config.py       -> single source of truth for autosave interval, undo depth,
                    breakpoints, window size, storage paths
editor.html     -> loads local GrapesJS assets + editor.js
editor.js       -> GrapesJS init + (later) toolbar, panels, RTL, pywebview.api calls
/assets/grapesjs -> bundled grapes.min.js/css + preset-webpage, offline
/drafts/current.json -> full GrapesJS component-tree autosave state (Phase 7)
/components/*.html   -> saved custom component library, flat files (Phase 5)
```

## Conventions
- No file over ~200-300 lines; split by concern (rtl.js, components.js, sanitizer.py
  etc. get added as their phases land — don't grow editor.js into a monolith).
- Every Python method exposed to JS must catch its own exceptions and return an
  error dict — a broken import or a bad export must never crash the whole app.
- Config values that might change (autosave interval, undo depth, breakpoints) go in
  config.py, nowhere else.

## Build phase status
- [x] Phase 0 — project setup, blank canvas loads, no console errors (confirmed
      working on Windows by user)
- [x] Phase 1 — core loop: open -> edit -> save draft -> export (api.py logic
      tested for real: save_draft file I/O verified, error handling verified
      for malformed JSON and missing window. Native dialogs + canvas editing
      NOT tested here — needs your run-through on Windows)
- [ ] Phase 2 — export sanitizer
- [x] Phase 3 (pulled forward, expanded scope) — dark Figma-style reskin via
      GrapesJS's documented --gjs-* CSS variables (see theme.css), 12-font
      curated local library (fonts.js + assets/fonts/canvas-fonts.css, all
      bundled offline via @fontsource, no CDN), and a Brand Kit panel
      (brand-kit.js) that sets heading/body font + 4 colors as global
      tag-level rules via editor.Css.setRule. LIMITATION: Brand Kit only
      overrides plain-tag styling (h1-h6, p, a, button) — it does not beat
      inline styles or highly specific selectors on imported pages; this is
      a CSS specificity limit, told to the user. NOT tested visually here —
      no display in this sandbox. Needs your run-through: does the dark
      theme actually render, do fonts show in the dropdown and on canvas,
      does Brand Kit visibly restyle a sample page.
- [ ] Phase 4 — add/delete elements, layers panel (lazy render, 300+ element test)
- [ ] Phase 5 — custom components panel
- [ ] Phase 6 — RTL toggle
- [ ] Phase 7 — autosave + crash recovery
- [ ] Phase 8 — import error handling
- [ ] Phase 9 — PyInstaller packaging, cold-start under 3s

## Real-world import fix #3: sites depending on Tailwind's runtime CDN (external_resources.py)
A THIRD, genuinely different root cause found on a second real file — not
the same bug as fix #1 or #2, correctly diagnosed as different before
touching code:
- This site uses `<script src="https://cdn.tailwindcss.com">` — Tailwind's
  Play/runtime compiler, which scans the live DOM and generates CSS via
  JavaScript. GrapesJS never executes imported `<script>` tags (correctly,
  for safety), so this literally never runs — confirmed as the dominant
  cause of the ENTIRE page rendering unstyled (not just images this time).
  This is one of the few cases where the user's original "no internet
  access" theory was actually half-right, though the more precise problem
  is "no live JS execution environment for the compiler," not the network
  fetch itself.
- Real fix, not a fake: bundled `@tailwindcss/browser` (official, MIT,
  zero deps, 282KB) as assets/tailwindcss-browser.min.js. On open, the
  original CDN script tag is detected, removed from the canvas-bound HTML,
  and its exact original text preserved. A local copy of the real engine is
  injected as an actual executing `<script>` DOM node directly into the
  canvas document (via createElement + textContent + appendChild — this
  executes, unlike innerHTML) — genuinely regenerates accurate Tailwind
  utility CSS from the real classes present, not an approximation.
- Passed as inline JS text from Python, not a src path — fetch()/script-src
  on file:// URLs is often blocked by browser security policy, same reason
  imported_css is passed as text rather than a URL.
- Export restores the ORIGINAL CDN script tag verbatim — the deployed site
  keeps depending on the real cdn.tailwindcss.com exactly as it does today.
  This was an explicit choice: didn't presume to change their deployment
  architecture without being asked.
- Also found and fixed: external stylesheets (Google Fonts `<link
  rel="stylesheet">`) were being silently lost, since only <body> content
  ever reaches GrapesJS's component tree — head-level tags never survive.
  Now extracted and injected as real `<link>` elements into canvas <head>,
  restored verbatim on export too.
- Two real bugs caught by testing against the actual file, not assumed:
  (1) `${imgSrc}` — a JS template literal inside inline gallery code — was
  being misidentified as a broken asset path by the Phase-1 asset resolver,
  because it never excluded `<script>` block contents from its regex scan.
  Fixed by masking script blocks before any rewriting and restoring them
  byte-for-byte after (asset_resolver.py, `_mask_scripts`/`_unmask_scripts`).
  (2) The external-stylesheet regex assumed `rel="stylesheet"` appeared
  before `href=` in the tag — real HTML had them in the opposite order.
  Fixed to match the whole tag first, then check each attribute
  independently regardless of order.
- Verified end-to-end against the real file: extraction correct, script
  masking prevents corruption, full export round-trip restores both the
  Tailwind script and the Google Fonts link byte-for-byte.
- NOT verified here: does the local Tailwind engine actually produce
  matching output to the live site in the real browser — needs Windows.

## Real-world import fix #2: compiled CSS bypasses GrapesJS's parser (style_extractor.py)
Root cause of "site still looks broken after asset fix": found the actual
smoking gun on the real file — `class="select-chevron w-4 h-4"` (meant to
render 16x16px) was rendering at unconstrained native size, meaning
Tailwind's compiled utility classes weren't applying AT ALL. GrapesJS's own
docs (Custom CSS Parser guide) admit its CSSOM-based rule parsing "can't be
relied on" for exactly this kind of complex/compiled CSS output.
- Fix: `<style>` blocks are now extracted out of imported HTML entirely
  (after asset-path resolution, so font/image url() refs inside are already
  fixed) and injected as a raw `<style>` tag directly into the canvas
  document via `editor.Canvas.getDocument()` — bypassing GrapesJS's
  CssComposer, letting the browser's own CSS engine (which handles
  oklch()/escaped selectors/etc. fine) render it with full fidelity.
- Inserted as the FIRST child of canvas `<head>` specifically so GrapesJS's
  own managed stylesheet (Brand Kit rules, new block default styles) —
  added later — still wins the cascade on any shared selector. Verified
  this doesn't break Brand Kit's override behavior.
- Trade-off, stated to the user: this CSS is no longer editable rule-by-rule
  via the Style Manager. Reasonable — nobody hand-edits compiled Tailwind
  output through a GUI panel anyway. Anything the user adds/edits
  themselves still goes through GrapesJS normally.
- Export must fold this back in (export_html gets a 4th param,
  `imported_css`) or the exported file loses the entire original
  stylesheet. Verified end-to-end: open -> extract -> export -> reverse +
  recombine reproduces a complete, correct file with portable paths
  restored AND new GrapesJS-managed CSS (e.g. Brand Kit) included.
- NOT tested here: does the real site actually render correctly now (no
  giant unstyled icons, layout intact) — needs your machine.

## Real-world import fix: local asset resolution (asset_resolver.py)
Root cause of "opens a real hosted site and it looks broken": a real static
site is index.html PLUS a folder of images/fonts next to it, not one
self-contained file. Was NOT a network-access problem (confirmed: this
site's Tailwind/GSAP/Lenis were already inlined, zero CDN dependencies).
- open_file() now rewrites local src/href/srcset/CSS-url() references to
  absolute file:// URIs (via pathlib.Path.as_uri(), not manual string
  concat — handles Windows drive letters/spaces/encoding correctly) so the
  canvas can actually load them.
- Root-relative paths ("/logos/1.svg") are treated as relative to the
  opened HTML's folder — correct for a self-contained static export.
- Files that genuinely aren't there are left untouched and reported back
  as `missing_assets`, shown in the status bar — not guessed at.
- CRITICAL: this rewrite is for local canvas preview ONLY. export_html now
  takes an asset_map (JS tracks it on window.__assetMap across opens) and
  reverses every file:// URI back to its original portable relative path
  before writing. Verified byte-identical round-trip. Without this, an
  exported file would ship with hardcoded file:///C:/Users/... paths and
  break the moment it's deployed anywhere else — caught and fixed before
  shipping, not after.
- Known edge case fixed: url(%23noiseFilter) (percent-encoded SVG
  self-reference, not a file path) was initially mis-flagged as missing —
  found by testing against the user's real file, not assumed. `%23` added
  to the ignore-prefix list alongside `#`.
- Tested against a synthetic mirrored site structure (correct resolution +
  correct round-trip) AND the user's actual real-world file (2850 lines,
  WebGL shaders, heavy inline JS) to confirm no crashes/corruption on real
  complexity, not just a toy example.
- NOT tested here: does the canvas actually render the images/fonts once
  the real asset folder is present next to the HTML — needs your machine
  with the real site folder (index.html + fonts/ + logos/ + clients/ etc.
  all together, not just the HTML alone).

## Phase 4 batch (user-requested, ahead of formal order)
- componentFirst styling fix: `selectorManager: { componentFirst: true }` in
  editor.js — verified against GrapesJS docs. Fixes "editing one quote's
  color changes all quotes" (was default class-based styling behavior).
- Real block library in blocks.js (confirmed via inspecting the bundled
  preset-webpage source that its actual default really is only 3 blocks —
  not a viewport/scroll issue). Default styles for new block classes
  (.btn/.container/.row/.col/.divider) are single-class-selector rules so
  Brand Kit's rules win by source order without !important.
- grapesjs-custom-code plugin bundled (assets/grapesjs/grapesjs-custom-code.min.js)
  for pasting arbitrary HTML/CSS/JS embeds. Registered via direct function
  reference (`window["grapesjs-custom-code"]`) in the plugins array, not by
  string name — safer, doesn't depend on the bundle self-registering.
- Custom Components panel: api.py's list_components/save_component are real
  now (read/write /components/*.html, sanitized filenames — tested against
  path-traversal attempts). Saved components register as GrapesJS blocks
  under "My Components" category (editor.js refreshComponentsLibrary()) —
  reuses GrapesJS's own drag-and-drop rather than custom drag logic.
- Brand Kit's button handling was corrected: primary color fills button
  backgrounds (white text), not just text color — matches how brand colors
  are actually used on buttons, not the naive first pass.
- NOT tested here — needs your run-through: does componentFirst actually
  fix the quote bug, do all the new blocks drag in cleanly, does a pasted
  embed snippet render, does Save as Component + drag-back-in work.

## Design decisions for Phase 3 (for future phases to build on)
- Brand Kit uses direct resolved values (not CSS custom properties/var())
  in the rules it sets — simpler and more robust than needing var()
  indirection to survive GrapesJS's getCss() export path.
- Curated font list lives in fonts.js as CANVAS_FONT_OPTIONS. To add/remove
  fonts: install more @fontsource packages and regenerate, or hand-edit
  fonts.js + assets/fonts/canvas-fonts.css directly for small tweaks.
- GrapesJS canvas fonts load via `canvas: { styles: [...] }` config in
  editor.js, NOT a <link> in editor.html — the canvas renders in an
  isolated iframe, so page-level <link> tags never reach it.
- Watch relative paths inside assets/fonts/canvas-fonts.css: that file lives
  one level inside assets/fonts/, so its own url() refs are relative to
  that folder, not the project root (caught and fixed once already).

## Gotcha: never store the pywebview Window object on the Api instance
pywebview inspects every attribute of the `js_api` object to find bindable JS
functions, recursing into nested objects. Storing the live Window object as
`self.window` causes it to touch an internal DOM property before the page has
loaded, crashing with "Main window failed to start". When a method needs the
window (native file dialogs, Phase 1+), fetch it fresh inside the method:
`import webview; webview.windows[0]` — never cache it as an attribute.

## Known environment limitation
This project was scaffolded in a Linux sandbox with no display and no Windows.
Phases were written and statically checked there but NOT visually/runtime tested.
Every phase needs a real run-through on Windows to actually confirm behavior.
