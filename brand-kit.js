/**
 * brand-kit.js — one-click global reskin using the curated font library.
 *
 * How "apply across the site" works: this sets a handful of tag-level CSS
 * rules (h1-h6, body/p/text, links/buttons) via GrapesJS's CssComposer.
 * That reliably restyles elements using normal HTML tags. It does NOT
 * override elements with inline styles or highly specific selectors —
 * that's a CSS specificity limit, not a bug. Told to the user up front.
 *
 * Depends on: fonts.js (CANVAS_FONT_OPTIONS), and is wired up from editor.js
 * after the GrapesJS editor instance exists.
 */

function initBrandKit(editor) {
  const panel = document.getElementById('brand-kit-panel');
  const headingSelect = document.getElementById('bk-heading-font');
  const bodySelect = document.getElementById('bk-body-font');
  const primaryColor = document.getElementById('bk-primary-color');
  const secondaryColor = document.getElementById('bk-secondary-color');
  const textColor = document.getElementById('bk-text-color');
  const bgColor = document.getElementById('bk-bg-color');

  // Populate the two font dropdowns from the curated library
  function populateFontSelect(selectEl, defaultIndex) {
    selectEl.innerHTML = '';
    CANVAS_FONT_OPTIONS.forEach((opt, i) => {
      const option = document.createElement('option');
      option.value = opt.id;
      option.textContent = opt.label;
      if (i === defaultIndex) option.selected = true;
      selectEl.appendChild(option);
    });
  }

  // Sensible defaults: a display/sans for headings, a plain sans for body
  populateFontSelect(headingSelect, 0); // Inter
  populateFontSelect(bodySelect, 0); // Inter

  function applyBrandKit() {
    const headingFont = headingSelect.value;
    const bodyFont = bodySelect.value;
    const primary = primaryColor.value;
    const secondary = secondaryColor.value;
    const text = textColor.value;
    const bg = bgColor.value;

    try {
      editor.Css.setRule('h1, h2, h3, h4, h5, h6', {
        'font-family': headingFont,
        color: text,
      });

      editor.Css.setRule('body, p, span, li, td, div', {
        'font-family': bodyFont,
        color: text,
      });

      editor.Css.setRule('body', {
        'background-color': bg,
      });

      editor.Css.setRule('a', {
        color: primary,
      });

      editor.Css.setRule('.btn, .cta, .button, button', {
        'background-color': primary,
        color: '#ffffff',
      });

      editor.Css.setRule('.btn-secondary, .secondary', {
        'background-color': secondary,
        color: '#ffffff',
      });

      return { ok: true };
    } catch (err) {
      console.error('[Brand Kit] apply failed:', err);
      return { ok: false, error: String(err) };
    }
  }

  document.getElementById('btn-brand-kit').addEventListener('click', () => {
    panel.classList.toggle('open');
  });

  document.getElementById('bk-close').addEventListener('click', () => {
    panel.classList.remove('open');
  });

  document.getElementById('bk-apply').addEventListener('click', () => {
    const result = applyBrandKit();
    const statusEl = document.getElementById('status');
    if (result.ok) {
      statusEl.textContent = 'Brand Kit applied.';
      statusEl.style.color = '#666';
    } else {
      statusEl.textContent = 'Brand Kit failed: ' + result.error;
      statusEl.style.color = '#c0392b';
    }
  });
}
