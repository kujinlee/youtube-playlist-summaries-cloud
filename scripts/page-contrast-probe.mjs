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
// ⚠ IT HOLDS DECISION RULES, AND AN EARLIER VERSION OF THIS HEADER SAID "IT DECIDES NOTHING".
// That was false and round 1 (H3) counted them: what is visible, what counts as opaque, which
// ancestor supplies the background, how deep a selector path goes, what a gradient means. The
// selector depth alone is one of the components of `sample_key`. No contrast MATHS and no
// verdict live here — those are pure Python, cased without a browser — but "reports only what
// the page computed" was never true, and a comment asserting a property the code lacks is the
// exact defect backlog #216 is about.
// ⛔ WHAT IS DONE ABOUT IT, STATED EXACTLY: `--self-test` exercises `opaque` — the SAME source
// text the browser runs, not a copy — with no browser. ⚠ It does NOT test `sel`, `bgOf`,
// `hasImage` or the visibility filters; those are DOM walks and only the corpus run touches
// them. ⚠ It is run by CI (`.github/workflows/ci.yml`), NOT by `check-page-contrast.py`. An
// earlier version of this paragraph claimed all three of those things and was wrong about all
// three — round 2's B2.
//
//   node scripts/page-contrast-probe.mjs <scheme> <page.html> [more.html ...]

import { chromium } from 'playwright';
import { pathToFileURL } from 'node:url';

// ⛔ ONE DEFINITION, AS SOURCE TEXT, AND ROUND 2's B2 IS WHY. The first attempt at testing this
// predicate wrote a SECOND copy next to it and tested that: severing the one the browser
// actually runs left the self-test reporting 10/10. A duplicate rule is this repository's
// most-measured failure (17 recorded instances), committed inside the fix for an untested rule.
// ⚠ The duplicate was not laziness — `page.evaluate` SERIALISES the probe, so it cannot close
// over anything in Node scope. The repair is to keep the rule as text, hand it to the browser,
// and build the testable function from the same text. Sever it and BOTH go red.
// ⚠ `String.raw`, AND THE SELF-TEST CAUGHT WHY. A plain template literal treats `\(` as an
// escape and collapses it to `(`, so the regex silently became `/rgba?(([^)]+))/` — unanchored
// and wrong. The case `color(srgb ... / 0.3) is not` went red on the control immediately. A
// rule kept as SOURCE TEXT has to survive its own quoting, and that is a new hazard this
// single-source repair introduced.
const OPAQUE_SRC = String.raw`(c) => {
  if (!c) return false;
  const m = c.match(/rgba?\(([^)]+)\)/) || c.match(/color\(\s*srgb\s+([^)]+)\)/);
  if (!m) return false;
  const parts = m[1].split(/[,\s/]+/).filter(Boolean);
  return parts.length < 4 || parseFloat(parts[3]) >= 0.999;
}`;

const PROBE = ({ opaqueSrc }) => {
  const out = [];
  const opaque = (0, eval)(opaqueSrc);
  // The background a reader actually sees behind this text: the nearest ancestor that is opaque.
  // ⚠ NOT the element's own background — most text sits on a transparent element inside a card,
  // and scoring against `transparent` is how a contrast probe reports fiction.
  // ⛔ A GRADIENT OR IMAGE BACKGROUND HAS NO SINGLE COLOUR, and scoring against the colour
  // UNDERNEATH it is fiction. Round 1 H2: the corpus's published `worst: 1.107` was exactly
  // this — that element sits on a `repeating-linear-gradient` and was scored against the cream
  // beneath, a number no reader could ever experience. Such sites are reported as UNMEASURABLE
  // and excluded from the verdict rather than given a confident wrong answer.
  const hasImage = (el) => {
    let n = el;
    while (n && n !== document.documentElement) {
      const bi = getComputedStyle(n).backgroundImage;
      if (bi && bi !== 'none') return true;
      if (opaque(getComputedStyle(n).backgroundColor)) return false;
      n = n.parentElement;
    }
    return false;
  };
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
      bgImage: hasImage(el),
    });
  }
  return out;
};

// ── the pure predicates, lifted out so they can be tested without a browser (round 1 H3) ──
// Built from OPAQUE_SRC, so the self-test below exercises the EXACT text the browser runs.
// `OPAQUE_RE` was a THIRD copy of the same pattern and is deleted.
export const isOpaque = (0, eval)(OPAQUE_SRC);

if (process.argv[2] === '--self-test') {
  let ok = 0, fail = 0;
  const c = (name, got, want) => {
    if (JSON.stringify(got) === JSON.stringify(want)) ok++;
    else { console.log(`[FAIL] ${name}\n  expected ${JSON.stringify(want)}\n  got      ${JSON.stringify(got)}`); fail++; }
  };
  c('an rgb() colour is opaque', isOpaque('rgb(1, 2, 3)'), true);
  c('rgba with alpha 1 is opaque', isOpaque('rgba(1, 2, 3, 1)'), true);
  c('rgba with alpha 0 is NOT', isOpaque('rgba(0, 0, 0, 0)'), false);
  c('rgba with partial alpha is NOT', isOpaque('rgba(0, 0, 0, 0.5)'), false);
  // ⚠ 0.999 is the floor, because a browser reports 1 as 0.9999999 after a round trip.
  c('alpha 0.9995 counts as opaque', isOpaque('rgba(0, 0, 0, 0.9995)'), true);
  c('alpha 0.99 does not', isOpaque('rgba(0, 0, 0, 0.99)'), false);
  c('color(srgb ...) is opaque', isOpaque('color(srgb 0.1 0.2 0.3)'), true);
  c('color(srgb ... / 0.3) is not', isOpaque('color(srgb 0.1 0.2 0.3 / 0.3)'), false);
  c('the empty string is not', isOpaque(''), false);
  c('a keyword this probe never receives is not', isOpaque('transparent'), false);
  console.log(`\n${ok}/${ok + fail} probe self-test cases passed`);
  process.exit(fail ? 1 : 0);
}

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
    const rows = await page.evaluate(PROBE, { opaqueSrc: OPAQUE_SRC });
    for (const r of rows) {
      process.stdout.write(JSON.stringify({ ...r, page: p.split('/').pop(), scheme }) + '\n');
    }
  }
  await ctx.close();
} finally {
  await browser.close();
}
