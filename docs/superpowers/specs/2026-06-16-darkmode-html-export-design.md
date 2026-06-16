# Dark-Mode Toggle for HTML Exports — Design Spec

**Date:** 2026-06-16
**Status:** Approved (architecture) — pending written-spec review
**Scope:** Add a light/dark theme toggle to both HTML export documents (magazine-skim summary and deep-dive).

---

## 1. Goal

Each exported HTML document is a standalone, self-contained file the reader opens in a
browser or Obsidian preview (typically over `file://`). Today both render light-only with
hardcoded colors. This feature adds:

- A fixed top-right ☀/🌙 toggle that flips the document between light and dark.
- **System default:** on first open the document follows the OS `prefers-color-scheme`.
- **Remembered override:** a manual toggle is saved and wins on later opens/reloads.
- Faithful warm/cool dark palettes that each extend the document's own light identity.

Non-goals: per-document theme memory (see §6), user-selectable multiple dark palettes,
theming any in-app UI (this is export-only), changing the light appearance.

---

## 2. Decisions (locked during brainstorming)

| # | Decision | Choice |
|---|----------|--------|
| D1 | Magazine dark palette | **Dark A — warm** (paper/gold identity preserved) |
| D2 | Deep-dive dark palette | **Cool/purple dark** (extends its cool white/purple light identity) |
| D3 | Default theme | **System** (`prefers-color-scheme`) on first open |
| D4 | Override persistence | **Remembered** via `localStorage`, with graceful fallback |
| D5 | Scope | **Both** exports (summary + deep-dive) |
| D6 | Dark consistency | **Each true to itself** — palettes differ per document |
| D7 | Module shape | **Palette-generator** module (mechanism shared, palette data per renderer) |

---

## 3. Key Constraint: System-Following Must Not Pin `data-theme`

Both throwaway prototypes hardcode `<html data-theme="light">`, which can never follow the
OS. The real feature must leave `data-theme` **unset** by default so a CSS media query can
drive the unset state. JavaScript sets `data-theme` **only** when an explicit saved override
exists. This makes the default path FOUC-free with no JS, and the document still follows the
system theme with JS disabled.

CSS selector matrix emitted per document:

| Selector | Applies | Palette |
|----------|---------|---------|
| `:root` | base / default | light |
| `[data-theme="light"]` | explicit light override | light |
| `[data-theme="dark"]` | explicit dark override | dark |
| `@media(prefers-color-scheme:dark){:root:not([data-theme])}` | system dark, no override | dark |

The dark palette therefore appears in **two** selectors. Writing that by hand twice invites
drift, so the CSS is **generated** from a palette object rather than hand-authored (D7).

---

## 4. Architecture

### 4.1 New module: `lib/html-doc/theme.ts`

Pure functions and constants. No I/O. Emits only static developer-defined strings (palette
hex values are constants, never user data) → no HTML-escaping concerns.

```ts
type Palette = Record<string, string>; // e.g. { page: '#1a1714', card: '#221d18', ... }

// Generates the full variable + toggle CSS block (the four selectors of §3 + toggle button
// styling + transitions + print rules for the toggle).
export function themeStyleBlock(light: Palette, dark: Palette): string;

// Inline <head> script — runs before first paint. Applies a saved override only.
export const THEME_HEAD_SCRIPT: string;

// Toggle button markup, injected right after <body>.
export const THEME_TOGGLE_BUTTON: string;

// End-of-<body> script — click handler + on-load icon sync.
export const THEME_TOGGLE_SCRIPT: string;
```

**`THEME_HEAD_SCRIPT` behavior** (before paint, in `<head>`):
```js
try {
  var t = localStorage.getItem('html-doc-theme');
  if (t === 'dark' || t === 'light') document.documentElement.setAttribute('data-theme', t);
} catch (e) {}
```
- Accepts only `'dark'` / `'light'`; any other stored value is ignored.
- `localStorage` access wrapped in try/catch → throw or unavailability is a silent no-op,
  and the document falls back to system preference via CSS.

**`THEME_TOGGLE_SCRIPT` behavior** (end of `<body>`):
- Effective theme = explicit `data-theme` if set, else `matchMedia('(prefers-color-scheme: dark)').matches`.
- Click: flip effective → set `data-theme` to the new value → write `localStorage` in try/catch → sync icon.
- On load: compute effective theme, set the ☀/🌙 icon accordingly (icon reflects system state even with no override).

**`themeStyleBlock` output** includes:
- `:root` and `[data-theme="light"]` → light vars.
- `[data-theme="dark"]` and `@media(prefers-color-scheme:dark){:root:not([data-theme])}` → dark vars.
- `#theme-toggle` button styling (fixed, top-right, circular, uses theme vars).
- `body` / card `transition: background .2s, color .2s`.
- `@media print { #theme-toggle { display:none } body { background:#fff } <card> { box-shadow:none } }`.

### 4.2 Callers

**`lib/html-doc/render.ts`** (magazine-skim) and **`lib/html-doc/render-deep-dive.ts`**:

1. **Refactor** existing hardcoded hex in their structural CSS to `var(--…)` references.
   The light palette object reuses the *exact* current hex values → zero visual change to light mode.
2. Define two palette objects:
   - Magazine `light` = current values; `dark` = warm Dark A (from prototype `magazine.html` `[data-theme="darkA"]`).
   - Deep-dive `light` = current values; `dark` = cool/purple (from prototype `deepdive.html` `[data-theme="dark"]`).
3. Inject into the existing HTML template string:
   - `THEME_HEAD_SCRIPT` inside `<head>` (before `<style>`).
   - `<style>${themeStyleBlock(light, dark)}${structuralCss}</style>`.
   - `THEME_TOGGLE_BUTTON` immediately after `<body>`.
   - `THEME_TOGGLE_SCRIPT` immediately before `</body>`.

No changes to `parse.ts`, `generate.ts`, `generate-deep-dive.ts`, or the serve route — the
rendered HTML string simply gains the theming.

### Palette values (lifted verbatim from the reviewed prototypes)

Magazine warm dark (Dark A):
```
page #1a1714  card #221d18  ink #e8e2d6  meta #9a9082  rule #332c24
ghost #2e2820  gold #e6b54d  goldline #e0a800  li #cfc8ba  foot #8a8174
shadow 0 1px 3px rgba(0,0,0,.5)
```
Deep-dive cool dark:
```
page #0f1115  card #16181d  ink #d8dbe0  h1 #f2f3f5  h2 #a99bf0  h3 #cfc9ec  h4 #b9b4dc
link #a99bf0  hr #2a2d34  strong #f2f3f5  codebg #20222a  preborder #2a2d34
quote #9aa0ab  shadow 0 1px 3px rgba(0,0,0,.5)
```

---

## 5. Data Flow

```
renderMagazineHtml(parsed, model)
  └─ light/dark Palette consts (local)
       └─ themeStyleBlock(light, dark)   ─┐
       └─ THEME_HEAD_SCRIPT              ─┤→ assembled HTML string (now themed)
       └─ THEME_TOGGLE_BUTTON            ─┤
       └─ THEME_TOGGLE_SCRIPT            ─┘
renderDeepDiveHtml(md, sourceMd)   … identical wiring, different palette consts
```

Runtime in the browser:
```
page load → THEME_HEAD_SCRIPT reads localStorage
            ├─ saved 'dark'|'light' → set data-theme  (explicit override path)
            └─ nothing / throws     → no attribute → CSS @media follows OS
        → first paint already correct (no FOUC)
        → THEME_TOGGLE_SCRIPT syncs icon to effective theme
click toggle → flip → set data-theme → save localStorage (try/catch) → sync icon
```

---

## 6. Persistence Semantics (by design, not a bug)

Single global key: `html-doc-theme`. On `file://`, browsers treat the origin as opaque/`null`,
so **all** exported documents share one `localStorage` bucket. The remembered choice is
therefore **global across every exported doc**, not per-document. Intended behavior: set dark
once and every exported document honors it. This is documented here so it is not later mistaken
for a leak/bug.

---

## 7. Error Handling

| Condition | Behavior |
|-----------|----------|
| `localStorage` throws (sandboxed / disabled) | try/catch → no-op → system default via CSS |
| Stored value not `'dark'`/`'light'` | Ignored; treated as no override |
| JavaScript disabled entirely | Default path still works: system theme via CSS `@media`; toggle inert |
| Printing | Toggle hidden; light card forced |

---

## 8. Testing

**Unit — `tests/lib/html-doc/theme.test.ts`:**
- `themeStyleBlock` emits all four selector blocks of §3; dark vars present in both
  `[data-theme="dark"]` and the `prefers-color-scheme` media query.
- Toggle button CSS + `transition` rules present; print rule hides `#theme-toggle`.
- `THEME_HEAD_SCRIPT` contains the `'dark'/'light'` guard and a try/catch.
- `THEME_TOGGLE_BUTTON` / `THEME_TOGGLE_SCRIPT` present and well-formed.

**Component — `tests/lib/html-doc/render.test.ts`, `render-deep-dive.test.ts`:**
- **No light-mode regression:** every light variable value equals the previously-hardcoded
  hex; body/`.dd` structural rules now reference `var(--…)`.
- Head script injected in `<head>`; toggle button after `<body>`; toggle script before `</body>`.
- `data-theme` is NOT hardcoded on `<html>` (must be unset by default).

**E2E — Playwright (over the serve route, http):**
- Default follows emulated `prefers-color-scheme: dark` → document renders dark.
- Click toggle → flips light↔dark.
- Reload → remembers the override (localStorage over http).
- `@media print` emulation → toggle hidden.
- **Known gap:** E2E runs over http, so it cannot exercise the `file://` null-origin quirk.
  The try/catch fallback (§7) covers failure; **Phase 4 manual verification opens a real
  `file://` document** to confirm system-following + remembered override on disk.

---

## 9. Out of Scope / YAGNI

- Multiple user-selectable dark palettes (the `proto-bar` switcher was prototype-only).
- Per-document theme memory.
- Theming the Next.js app UI.
- Animations beyond the existing 0.2s color transition.
