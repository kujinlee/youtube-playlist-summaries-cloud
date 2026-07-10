# Task 5 — Nonce + dig + print-listener in shared render (Claude adversarial review)

Scope: `lib/html-doc/csp.ts` (new), `theme.ts`, `nav.ts`, `render.ts`, and the SECOND shared
consumer `render-dig-deeper.ts`, plus the four test files. Reviewed after GREEN (all suites pass,
`tsc --noEmit` clean).

## Critical framing
Lib-layer **capability-only** change. `generateNonce`/`buildSummaryCsp` are called **only from tests** —
grep confirms **no production route sets a CSP header or passes a nonce**. Both production callers
(`lib/html-doc/generate.ts:58`, `lib/html-doc/rerender.ts:71`) call `renderMagazineHtml(parsed, model)`
with no opts, so live output is behavior-identical to pre-refactor (no nonce attrs, `dig` defaults true).
The "cloud path" is dormant until a future wiring task.

## Blocking
None.

## High (all forward-looking constraints for the future wiring task — NOT defects in this diff)
- **CSP must be scoped strictly to `type==='summary'` + `dig:false`.** `render-dig-deeper.ts` emits many
  bare `<script>`/`<style>` tags and inline `style=` attributes; applying `buildSummaryCsp` to a
  dig-deeper response would brick that page. This diff does not wire any route, but it creates the
  footgun. The wiring task (Task 7+) must carry an explicit test that dig-deeper is served WITHOUT
  `buildSummaryCsp`. Recorded as a deferred constraint; owner = wiring task.

## Medium (latent, forward-looking)
- **`connect-src` omitted → `default-src 'none'` blocks fetch/EventSource.** Correct and harmless for the
  intended cloud path (`dig:false`, no network calls). But the summary is only CSP-safe *because* dig is
  suppressed; nothing documents/tests that invariant. If a maintainer ever renders `{nonce, dig:true}`,
  `navScript`'s `fetch(...)` (nav.ts) is silently CSP-blocked. Suggest an inline comment tying "no
  `connect-src`" to "summary emits no fetch (dig suppressed)". Deferred.
- **`navScript` (hash `#t=` deep-link scroll + cross-doc nav) is dropped when `dig:false`.** `render.ts`
  gates the whole `navScript` on `showDig`, so a cloud summary opened at `…#t=120` won't auto-scroll.
  Likely acceptable for a static authorized view; confirm intended in the wiring task. Deferred.

## Low / Nits (confirmations)
- **Nonce coherence (intended cloud path) is fully correct.** For `{nonce, dig:false}` the only inline
  blocks are `themeHeadScript(nonce)`, `<style${nonceAttr(nonce)}>`, `themeToggleScript(nonce)`,
  `printListenerScript(nonce)` — all nonce'd; `navScript` suppressed. No `style=` attributes in the
  summary output, so `style-src 'nonce-…'` without `unsafe-inline` is safe. `render-nonce.test.ts`'s
  `/<script[^>]*>/g` sweep guards against a stray bare tag.
- **`navScript`'s single `NAV_SCRIPT.replace('<script>', …)` is correct.** Grep confirms exactly one
  literal `<script>` and one `</script>` in the body; `.replace` (first occurrence) stamps the right tag.
  Guarded by a comment; the `dig:true`+nonce path that would exercise this is not the intended cloud path.
- **CSP strength is strong.** No `unsafe-inline/eval/hashes`; all of
  `default-src/script-src/style-src/img-src/base-uri/object-src/frame-ancestors/form-action` locked.
  Nonce is `randomBytes(16)` = 128-bit base64; alphabet has no CSP-delimiter or attr-breaking char, so raw
  interpolation into header and `nonce="…"` is safe. Server-generated → no attacker-controlled-nonce path.
- **Dead-export migration clean.** `PRINT_BUTTON` has zero references; `THEME_HEAD_SCRIPT`/
  `THEME_TOGGLE_SCRIPT`/`NAV_SCRIPT` no longer exported; no production consumer references old names
  (`tsc` green confirms). No missed consumers.
- **Local parity confirmed on BOTH renderers.** `render-dig-deeper.ts` passes NO nonce everywhere and
  DOES emit `printListenerScript()` (line 479); print button now listener-wired for both renderers (D11
  intended). `render-dig-deeper-parity.test.ts` executes the inline scripts (per-script try/catch
  isolation) and asserts `window.print()` fires for both the summary and dig-deeper docs.
- **`NAV_CSS` still emitted in `<style>` when `dig:false`** — harmless dead `.dig{…}` rules. Cosmetic.

## Verdict
In-scope diff is correct and parity-safe; the strict-CSP capability is sound as designed for
`summary`+`dig:false`. No in-scope Blocking/High. The real risk lives entirely in the not-yet-written
wiring task; the High + Mediums are recorded as explicit constraints (with owner) for that task.

Per §8 iterative re-review: this round returned **no new in-scope Blocking/High** (the High is a deferred,
known-and-accepted constraint for a future task) → convergence gate reached for this contained,
capability-only shared change.
