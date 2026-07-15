# Whole-Branch Review — feat/cloud-dig-deeper-frontend — Round 1

**Range:** `8c4b316..be18af6` (6 impl commits) · **Date:** 2026-07-14
**Reviewers:** Codex (gpt-5.5) + independent Claude — both scoped to emergent/integration/cross-file defects the per-task reviews could not see.
**Verdict:** **2 Blocking (one from EACH reviewer, different defects), 0 High.** Both fixed in `e2ffc8f`. NOT convergence — round 2 mandatory (new Blockings + the CSP fix is a new surface).

This is the re-review loop earning its cost: both Blockings are emergent — invisible to the per-task reviews because every unit/inline test runs in jsdom (mocks `fetch`, ignores CSP) and the per-task reviews mocked `loadDigForServe`.

---

## B1 (Claude) — CSP forbids every fetch the interactive doc makes → feature inert in a real browser

`app/api/html/[id]/route.ts` served the now-**interactive** dig doc with `buildSummaryCsp(nonce)`, which is `default-src 'none'` with **no `connect-src`** (`csp.ts`). The injected `DIG_CLOUD_SCRIPT` drives the whole feature via same-origin `fetch`: POST `/dig/<sec>`, GET `/dig-state`, GET `location.href` (swap). Under `default-src 'none'` + no `connect-src`, the browser blocks all three → clicking `dig deeper ▶` → `⏳ generating…` → CSP-blocked POST → `.catch` → `⚠ retry` forever. No dig ever runs.

Invisible because: jsdom mocks `global.fetch` and does not enforce CSP; the integration test only string-checks the CSP header + HTML; the local e2e serves the local doc with **no CSP header at all**.

**Fix (e2ffc8f):** new `buildDigCsp(nonce)` = summary CSP **+ `connect-src 'self'`** (same-origin only; the doc never fetches cross-origin). Dig branch uses `buildDigCsp`; `buildSummaryCsp` (static summary/share docs) unchanged. Tests: `csp.test.ts` (dig has connect-src, summary does not), dig-serve route asserts `connect-src 'self'`, integration asserts it on the real header.

## B2 (Codex) — zero-dug serve → 404 → primary entry path dead

`load-dig-for-serve.ts:49` returned `404` when zero current-version dig blobs existed. But the menu enables `Dig deeper ↗` for **any** `summaryReady` video, and the spec's core path is "enabled even when zero sections are dug — the user opens the doc **to start** digging." So a promoted video with no digs yet → click → `404` → the user can never trigger a first dig.

Invisible because: per-task reviews mocked `loadDigForServe`; no test opened the route with a zero-dug promoted video.

**Fix (e2ffc8f):** `loadDigForServe` returns `ok` with `dug: []` at zero digs (the owner-assert + promoted-status gate already ran upstream in `loadSummaryForServe`, so this is only reachable for an owned, promoted video; renders all sections as un-dug triggers). `loadDigForServe` has no other caller; `dig-state` independently returns `{sectionIds: []}` for the same case. Tests: flipped the `load-dig-for-serve` zero-dug unit test to `ok dug:[]`; added a route test (zero-dug → 200 with `dig-trigger`). Kept the upstream-404 propagation test.

---

## Confirmed clean by BOTH reviewers (held up under attack)
- **Money invariant end-to-end:** serve + poll + the new `profiles` read reach no charge path; **no `?dig=N` auto-trigger** so opening never POSTs; integration test's `spend_ledger` before/after (admin read) is real. Charge is confined to `enqueueDig`.
- **NAV_SCRIPT byte-identity** (pure append) and **local render byte-identity** (Claude verified by static reduction; T4 reviewer regenerated the golden from merge-base == committed).
- **Anon parity:** serve + POST both read `profiles.is_anonymous !== false`; pre-disabled `<span>` (no `data-section`) is inert against the `a.dig-trigger[data-section]` delegate.
- **Inline↔helper parity** (URL/status/swap-guard/loading copy/toggle) and **poll termination** (deadline-after-sleep, ceiling 180000, backoff 2s→10s).
- **XSS/swap:** same-origin re-fetch, inert DOMParser, `adoptNode`+`replaceChild` runs no scripts; nonce carried.

## Mediums/Lows (deferred / accepted)
- M (both, roughly): the integration test proves the route injects the script + no-charge but does not execute the shipped inline against the served HTML in a browser; the jsdom inline test executes the shipped string separately. Residual: no browser-level cloud e2e under real CSP. Recorded as a follow-up; the CSP header-presence assertions are the load-bearing guard for the specific bug.
- L (Codex): integration `spend_ledger` sum is branch-wide not user-scoped (mitigated by `--runInBand`).
- L (Claude): content-dependent — an external `![img]` in a dig body would be CSP-blocked (broken image, not a hole); malformed-blob section is permanently un-diggable via UI (degraded, no charge/crash).

Round 2 dispatched to verify both fixes and hunt for defects they introduced.
