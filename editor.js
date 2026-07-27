/**
 * editor.js — GrapesJS instance setup + toolbar/Brand Kit wiring.
 *
 * Depends on fonts.js and brand-kit.js being loaded first (see editor.html).
 */

(function () {
  const editor = grapesjs.init({
    container: "#gjs",
    height: "100%",
    width: "auto",
    fromElement: false,
    storageManager: false, // Phase 7 wires real autosave
    plugins: ["grapesjs-preset-webpage", window["grapesjs-custom-code"]],
    pluginsOpts: {
      "grapesjs-preset-webpage": {},
      "grapesjs-custom-code": {
        blockCustomCode: { label: "Embed / Custom Code", category: "Media" },
      },
    },
    canvas: {
      // Loads the bundled, offline font-face declarations into the canvas
      // iframe so the curated font library actually renders while editing.
      styles: ["./assets/fonts/canvas-fonts.css"],
    },
    selectorManager: {
      // Without this, editing a style (e.g. text color) applies to every
      // element sharing that component's class — one quote's color change
      // would recolor every quote. componentFirst makes edits target only
      // the selected instance by default. Confirmed against GrapesJS docs.
      componentFirst: true,
    },
  });

  window.__editor = editor;

  // Register the curated font library as the font-family dropdown options,
  // replacing GrapesJS's small default web-safe list. Defensive: if the
  // property/sector id ever changes upstream, this logs a warning instead
  // of crashing the whole editor (per the "never fully crash" requirement).
  try {
    const fontProp = editor.StyleManager.getProperty("typography", "font-family");
    if (fontProp && typeof fontProp.setOptions === "function") {
      fontProp.setOptions(CANVAS_FONT_OPTIONS.map((f) => ({ id: f.id, label: f.label })));
    } else {
      console.warn("[fonts] typography/font-family property not found — default font list still active");
    }
  } catch (err) {
    console.warn("[fonts] failed to register curated font list:", err);
  }

  initBlocks(editor);
  initBrandKit(editor);

  // Injects the imported page's original CSS directly into the canvas
  // iframe as a plain stylesheet, bypassing GrapesJS's CssComposer entirely.
  // Why: GrapesJS's rule-based CSS parsing can silently fail on complex,
  // build-tool-compiled CSS (confirmed on a real file — Tailwind's `w-4 h-4`
  // sizing classes weren't applying at all). The browser's own CSS engine
  // handles this fine, so let it. Inserted FIRST in <head> so GrapesJS's own
  // managed stylesheet (Brand Kit, new blocks, etc.), which is added after,
  // still wins the cascade on any selector both define.
  function injectRawCss(css) {
    const doc = editor.Canvas.getDocument();
    if (!doc) return;
    const existing = doc.getElementById("imported-raw-css");
    if (existing) existing.remove();
    if (!css) return;
    const tag = doc.createElement("style");
    tag.id = "imported-raw-css";
    tag.textContent = css;
    doc.head.insertBefore(tag, doc.head.firstChild);
  }

  // Injects real <link rel="stylesheet"> elements into the canvas so
  // external stylesheets (e.g. Google Fonts) the imported page depends on
  // actually get a chance to load — these would otherwise be silently lost,
  // since only <body> content ever reaches GrapesJS's component tree.
  // Requires the user's own internet access; the app's own UI never depends
  // on this.
  function injectExternalStylesheets(hrefs) {
    const doc = editor.Canvas.getDocument();
    if (!doc) return;
    doc.querySelectorAll('link[data-imported-stylesheet]').forEach((el) => el.remove());
    (hrefs || []).forEach((href) => {
      const link = doc.createElement("link");
      link.rel = "stylesheet";
      link.href = href;
      link.setAttribute("data-imported-stylesheet", "true");
      doc.head.appendChild(link);
    });
  }

  // Runs a locally-bundled copy of Tailwind's real browser engine directly
  // inside the canvas document. GrapesJS never executes imported <script>
  // tags (reasonably — arbitrary script execution during editing would be
  // unsafe), so a page relying on Tailwind's CDN runtime compiler would
  // otherwise render completely unstyled — confirmed as the actual cause on
  // a real file. Injected as inline text (not a src path) since
  // fetch()/script-src on file:// URLs is often blocked by browser security
  // policy.
  function runTailwindEngine(engineJs) {
    const doc = editor.Canvas.getDocument();
    if (!doc || !engineJs) return;
    const existing = doc.getElementById("tailwind-engine");
    if (existing) existing.remove();
    const script = doc.createElement("script");
    script.id = "tailwind-engine";
    script.textContent = engineJs;
    doc.body.appendChild(script);
  }

  const statusEl = document.getElementById("status");
  const btnOpen = document.getElementById("btn-open");
  const btnSave = document.getElementById("btn-save");
  const btnExport = document.getElementById("btn-export");
  const btnSaveComponent = document.getElementById("btn-save-component");

  function setStatus(msg, isError) {
    statusEl.textContent = msg;
    statusEl.style.color = isError ? "#c0392b" : "#666";
    console.log("[status]", msg);
  }

  // ---- Custom Components library ----
  // Saved components are registered as ordinary GrapesJS blocks under "My
  // Components" — reuses GrapesJS's existing drag-and-drop instead of
  // hand-building separate drag logic.
  let myComponentBlockIds = [];

  async function refreshComponentsLibrary() {
    try {
      const result = await window.pywebview.api.list_components();
      if (!result.ok) {
        console.warn("[components] list failed:", result.error);
        return;
      }
      // Remove previously-registered component blocks before re-adding,
      // so saving a new one doesn't duplicate the whole list.
      myComponentBlockIds.forEach((id) => editor.BlockManager.remove(id));
      myComponentBlockIds = [];

      result.components.forEach((comp) => {
        const blockId = "my-component-" + comp.name;
        editor.BlockManager.add(blockId, {
          label: comp.name,
          category: "My Components",
          content: comp.html,
        });
        myComponentBlockIds.push(blockId);
      });
    } catch (err) {
      console.warn("[components] refresh failed:", err);
    }
  }

  // Save-as-Component button only makes sense with something selected.
  editor.on("component:selected", () => (btnSaveComponent.disabled = false));
  editor.on("component:deselected", () => (btnSaveComponent.disabled = true));

  btnSaveComponent.addEventListener("click", async () => {
    const selected = editor.getSelected();
    if (!selected) return;

    const name = prompt("Name this component:");
    if (!name || !name.trim()) return;

    setStatus("Saving component...");
    try {
      const html = selected.toHTML();
      const result = await window.pywebview.api.save_component(name, html);
      if (!result.ok) {
        setStatus("Save component failed: " + result.error, true);
        return;
      }
      setStatus('Component "' + result.name + '" saved.');
      await refreshComponentsLibrary();
    } catch (err) {
      setStatus("Save component failed: " + err, true);
    }
  });

  // Buttons stay disabled until pywebview has actually injected window.pywebview.api.
  // Calling the bridge before it's ready throws "pywebview is not defined".
  [btnOpen, btnSave, btnExport].forEach((b) => (b.disabled = true));

  window.addEventListener("pywebviewready", () => {
    [btnOpen, btnSave, btnExport].forEach((b) => (b.disabled = false));
    setStatus("Ready.");
    refreshComponentsLibrary();
  });

  btnOpen.addEventListener("click", async () => {
    setStatus("Opening...");
    try {
      const result = await window.pywebview.api.open_file();
      if (!result.ok) {
        if (result.error === "cancelled") {
          setStatus("Open cancelled.");
        } else {
          setStatus("Open failed: " + result.error, true);
        }
        return;
      }
      editor.setComponents(result.html);
      injectRawCss(result.imported_css);
      injectExternalStylesheets(result.external_stylesheets);
      runTailwindEngine(result.tailwind_engine_js);

      window.__importedCss = result.imported_css || "";
      window.__tailwindCdnScript = result.tailwind_cdn_script || "";
      window.__externalStylesheets = result.external_stylesheets || [];

      // Track file:// -> original-path mappings across opens so export can
      // reverse the local-preview rewrite and keep the file portable.
      window.__assetMap = window.__assetMap || {};
      Object.assign(window.__assetMap, result.asset_map || {});

      if (result.missing_assets && result.missing_assets.length > 0) {
        setStatus(
          "Opened: " + result.path + " — " + result.missing_assets.length + " asset(s) not found (check they're in the same folder): " +
          result.missing_assets.slice(0, 5).join(", ") + (result.missing_assets.length > 5 ? "…" : ""),
          true
        );
      } else if (result.tailwind_cdn_script) {
        setStatus("Opened: " + result.path + " — Tailwind CDN detected, running local engine for preview.");
      } else {
        setStatus("Opened: " + result.path);
      }
    } catch (err) {
      setStatus("Open failed: " + err, true);
    }
  });

  btnSave.addEventListener("click", async () => {
    setStatus("Saving draft...");
    try {
      const projectData = editor.getProjectData();
      const result = await window.pywebview.api.save_draft(JSON.stringify(projectData));
      if (!result.ok) {
        setStatus("Save failed: " + result.error, true);
        return;
      }
      setStatus("Draft saved: " + result.path);
    } catch (err) {
      setStatus("Save failed: " + err, true);
    }
  });

  btnExport.addEventListener("click", async () => {
    setStatus("Exporting...");
    try {
      const html = editor.getHtml();
      const css = editor.getCss();
      console.log("[export] html length:", html.length, " css length:", css.length);
      const result = await window.pywebview.api.export_html(
        html,
        css,
        JSON.stringify(window.__assetMap || {}),
        window.__importedCss || "",
        window.__tailwindCdnScript || "",
        JSON.stringify(window.__externalStylesheets || [])
      );
      if (!result.ok) {
        if (result.error === "cancelled") {
          setStatus("Export cancelled.");
        } else {
          setStatus("Export failed: " + result.error, true);
        }
        return;
      }
      setStatus("Exported: " + result.path);
    } catch (err) {
      setStatus("Export failed: " + err, true);
    }
  });

  console.log("[editor] GrapesJS initialized:", !!editor);
})();
