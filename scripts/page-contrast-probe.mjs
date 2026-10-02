#!/usr/bin/env node
// The FETCH half of scripts/check-page-contrast.py. Drives Chromium over a list of pages in a
// given colour scheme and emits one JSON object per visible text element on stdout.
//
// ⛔ NODE, NOT PYTHON, AND THE REASON IS A MEASURED FALSE POSITIVE. The first version of the
// harness used playwright's Python binding because `python3 -c "import playwright"` printed OK.
// It was an empty NAMESPACE PACKAGE — `playwright.__file__` was None and `playwright.sync_api`
// did not exist. The import succeeded and the capability was absent. The repo's own rule:
// check a KNOWN POSITIVE before trusting a check. `node require('playwright')` is the real one,
// and `check-paid-caller-arrival` already shells out to a sibling .mjs for the same reason.
//
// ⛔ IT DECIDES NOTHING. No contrast maths, no thresholds, no verdict — those are pure Python and
// cased without a browser. This file only reports what the page computed: colour, background,
// size, weight. Putting a rule here would put it where no self-test can reach it.
//
//   node scripts/page-contrast-probe.mjs <scheme> <page.html> [more.html ...]

import { chromium } from 'playwright';
import { pathToFileURL } from 'node:url';

const PROBE = () => {
  const out = [];
  const opaque = (c) => {
    if (!c) return false;
    const m = c.match(/rgba?\(([^)]+)\)/) || c.match(/color\(\s*srgb\s+([^)]+)\)/);
    if (!m) return false;
    const parts = m[1].split(/[,\s/]+/).filter(Boolean);
    return parts.length < 4 || parseFloat(parts[3]) >= 0.999;
  };
  // The background a reader actually sees behind this text: the nearest ancestor that is opaque.
  // ⚠ NOT the element's own background — most text sits on a transparent element inside a card,
  // and scoring against `transparent` is how a contrast probe reports fiction.
  const bgOf = (el) => {
    let n = el;
    while (n && n !== document.documentElement) {
      const c = getComputedStyle(n).backgroundColor;
      if (opaque(c)) return c;
      n = n.parentElement;
    }
    const hb = getComputedStyle(document.body).backgroundColor;
    if (opaque(hb)) return hb;
    const hr = getComputedStyle(document.documentElement).backgroundColor;
    if (opaque(hr)) return hr;
    // ⛔ NOTHING OPAQUE ANYWHERE — fall back to WHAT THE BROWSER ACTUALLY PAINTS, not to
    // `transparent`. Measured: 316 sites resolved to `rgba(0, 0, 0, 0)` and were scored at
    // 1.00:1 against nothing, which is noise in the absolute count. The UA canvas is white
    // unless the document opts into a dark `color-scheme`, in which case Chromium paints
    // #121212. ⚠ An APPROXIMATION of the UA default, and labelled as one — the alternative is
    // a number computed against a colour no reader ever sees.
    const cs = getComputedStyle(document.documentElement).colorScheme || '';
    const prefersDark = matchMedia('(prefers-color-scheme: dark)').matches;
    const dark = cs.includes('dark') && (!cs.includes('light') || prefersDark);
    return dark ? 'rgb(18, 18, 18)' : 'rgb(255, 255, 255)';
  };
  const sel = (el) => {
    const bits = [];
    let n = el;
    for (let i = 0; n && i < 3; i++, n = n.parentElement) {
      let s = n.tagName.toLowerCase();
      if (n.className && typeof n.className === 'string') {
        const c = n.className.trim().split(/\s+/)[0];
        if (c) s += '.' + c;
      }
      bits.unshift(s);
    }
    return bits.join('>');
  };
  for (const el of document.querySelectorAll('body *')) {
    // Only an element's OWN text nodes, so a container is not scored for its children's text —
    // otherwise one <main> carries the whole page and every real element is diluted away.
    const own = Array.from(el.childNodes)
      .filter((n) => n.nodeType === 3)
      .map((n) => n.textContent.trim())
      .join(' ')
      .trim();
    if (!own) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' || parseFloat(cs.opacity) === 0) continue;
    // ⛔ VISUALLY-HIDDEN TEXT IS NOT A CONTRAST FAILURE, AND THE FIRST RUN SAID IT WAS. Every one
    // of the worst 1.00:1 results was a `span.vh` screen-reader label on a chart bar —
    // `.vh{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}`. WCAG
    // exempts text that is not visible; scoring it inflates the failure count with text nobody
    // can see, and a baseline full of that noise hides the regressions it exists to catch.
    // ⚠ The original filter was `< 1`, and the box is exactly 1px. An off-by-one against a
    // convention that deliberately uses the smallest non-zero box.
    if (cs.clip === 'rect(0px, 0px, 0px, 0px)') continue;
    if (cs.clipPath && /inset\(\s*(50%|100%)/.test(cs.clipPath)) continue;
    const r = el.getBoundingClientRect();
    if (r.width <= 2 || r.height <= 2) continue;
    // Scrolled or positioned entirely out of the viewport's reach.
    if (r.bottom < -2000 || r.right < -2000) continue;
    out.push({
      selector: sel(el),
      text: own.slice(0, 80),
      color: cs.color,
      bg: bgOf(el),
      px: parseFloat(cs.fontSize),
      weight: parseFloat(cs.fontWeight) || 400,
    });
  }
  return out;
};

const [scheme, ...pages] = process.argv.slice(2);
if (!scheme || pages.length === 0) {
  process.stderr.write('usage: page-contrast-probe.mjs <scheme> <page.html> [...]\n');
  process.exit(2);
}

const extraCss = process.env.CONTRAST_EXTRA_CSS || '';
const browser = await chromium.launch();
try {
  const ctx = await browser.newContext({ colorScheme: scheme });
  const page = await ctx.newPage();
  for (const p of pages) {
    await page.goto(pathToFileURL(p).href, { waitUntil: 'load' });
    if (extraCss) await page.addStyleTag({ content: extraCss });
    const rows = await page.evaluate(PROBE);
    for (const r of rows) {
      process.stdout.write(JSON.stringify({ ...r, page: p.split('/').pop(), scheme }) + '\n');
    }
  }
  await ctx.close();
} finally {
  await browser.close();
}
