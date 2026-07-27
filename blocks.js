/**
 * blocks.js — the real block library.
 *
 * grapesjs-preset-webpage's built-in default is only 3 blocks (Link Block,
 * Quote, Text section) — confirmed by inspecting its bundled source, not
 * assumed. This adds the actual set from the spec: heading, paragraph,
 * image, button, container/div, link, plus columns/divider/video for real
 * layout work.
 *
 * Default styles for the new block classes (.btn, .container, .row, .col,
 * .divider) are added via editor.Css.setRule with LOW specificity (single
 * class selectors) so Brand Kit's rules — set later, when the user clicks
 * Apply — win by source order without needing !important anywhere.
 */

function initBlocks(editor) {
  const bm = editor.BlockManager;

  // ---- Layout ----
  bm.add("container", {
    label: "Container",
    category: "Layout",
    content: '<div class="container" data-gjs-droppable="true"></div>',
  });

  bm.add("row-1col", {
    label: "1 Column",
    category: "Layout",
    content: '<div class="row"><div class="col"></div></div>',
  });

  bm.add("row-2col", {
    label: "2 Columns",
    category: "Layout",
    content: '<div class="row"><div class="col"></div><div class="col"></div></div>',
  });

  bm.add("row-3col", {
    label: "3 Columns",
    category: "Layout",
    content:
      '<div class="row"><div class="col"></div><div class="col"></div><div class="col"></div></div>',
  });

  bm.add("divider", {
    label: "Divider",
    category: "Layout",
    content: '<hr class="divider" />',
  });

  // ---- Basic ----
  bm.add("heading-h1", {
    label: "Heading (H1)",
    category: "Basic",
    content: "<h1>Heading</h1>",
  });

  bm.add("heading-h2", {
    label: "Subheading (H2)",
    category: "Basic",
    content: "<h2>Subheading</h2>",
  });

  bm.add("paragraph", {
    label: "Paragraph",
    category: "Basic",
    content: "<p>Paragraph text. Click to edit.</p>",
  });

  bm.add("button", {
    label: "Button",
    category: "Basic",
    content: '<a href="#" class="btn">Click Me</a>',
  });

  bm.add("link", {
    label: "Link",
    category: "Basic",
    content: '<a href="#">Link text</a>',
  });

  // ---- Media ----
  // Local SVG data-URI placeholder — no network call, works fully offline.
  const PLACEHOLDER_IMG =
    "data:image/svg+xml;utf8," +
    encodeURIComponent(
      '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200">' +
        '<rect width="300" height="200" fill="#3a3a3a"/>' +
        '<text x="150" y="105" font-family="sans-serif" font-size="16" fill="#999" text-anchor="middle">Image</text>' +
        "</svg>"
    );

  bm.add("image", {
    label: "Image",
    category: "Media",
    content: { type: "image", src: PLACEHOLDER_IMG, style: { "max-width": "100%" } },
  });

  bm.add("video", {
    label: "Video",
    category: "Media",
    content: '<video controls style="max-width:100%;"></video>',
  });

  // ---- Default styles for the new block classes ----
  // Single-class selectors only, so Brand Kit's later rules (set on Apply)
  // win cleanly by source order — no specificity fights.
  editor.Css.setRule(".container", {
    padding: "20px",
    "min-height": "60px",
  });

  editor.Css.setRule(".row", {
    display: "flex",
    "flex-wrap": "wrap",
    gap: "16px",
  });

  editor.Css.setRule(".col", {
    flex: "1",
    "min-height": "80px",
    padding: "12px",
    border: "1px dashed rgba(0,0,0,0.15)",
  });

  editor.Css.setRule(".divider", {
    border: "none",
    "border-top": "1px solid rgba(0,0,0,0.15)",
    margin: "20px 0",
  });

  editor.Css.setRule(".btn", {
    display: "inline-block",
    padding: "10px 22px",
    "background-color": "#2f8ff0",
    color: "#ffffff",
    "text-decoration": "none",
    "border-radius": "6px",
    "font-family": "sans-serif",
  });
}
