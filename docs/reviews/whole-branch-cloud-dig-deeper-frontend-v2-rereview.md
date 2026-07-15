# Whole-Branch Re-Review — feat/cloud-dig-deeper-frontend — Round 2 (convergence)

**Range:** `8c4b316..e2ffc8f` (7 commits: 6 impl + 1 Blocking-fix) · **Date:** 2026-07-14
**Reviewers:** Codex (gpt-5.5) + independent Claude — both scoped to (a) verify the two round-1 Blocking fixes are genuine, (b) hunt for defects the fixes introduced.
**Verdict:** **CONVERGED — 0 Blocking / 0 High from both.** Both fixes verified genuine; no new Blocking/High; all round-1 clean items still hold. This round is the merge gate.

---

## Round-1 Blocking fixes — both reviewers: VERIFIED-GENUINE

**Fix B (CSP `connect-src`) — GENUINE (both).**
- `buildDigCsp` (`csp.ts:31`) = summary CSP **+ `connect-src 'self'`** only; dig branch uses it (`route.ts:62`).
- Both confirmed `connect-src` (not `form-action`) governs the shipped script's three same-origin `fetch`es (POST `/dig`, GET `/dig-state`, GET `location.href`) → all permitted by `'self'`.
- `buildSummaryCsp` byte-unchanged; its only two callers (summary branch `route.ts:91`, share route `app/s/[token]/route.ts:92`) were **not** switched; `buildDigCsp` has exactly one caller. `'self'` is minimal (doc never fetches cross-origin); `img-src 'none'` correctly retained (cloud dig bodies emit caption text, never `<img>`).

**Fix A (zero-dug → 200 interactive) — GENUINE (both).**
- `loadDigForServe` (`load-dig-for-serve.ts:49`) now returns `ok, dug:[]` at zero current-version digs.
- Owner-assert + promoted-status gate still enforced upstream: `loadSummaryForServe` runs first and `if (!load.ok) return load` short-circuits — zero-dug 200 only reachable for an owned, promoted video; anon still gets pre-disabled `<span>` triggers (profiles fail-closed, after the loader).
- `renderDigDeeperDoc({dug:[]})` → every section un-dug trigger (or anon span); no crash.
- **Single production caller** (the html dig route); `dig-state` uses `loadSummaryForServe`. Localized.
- Flipped unit test (stale `.r{V-1}` blob → genuine zero-current path → `ok dug:[]`) + new route test (200 + `dig-trigger` + `connect-src`) are non-vacuous.

## New-defect hunt — nothing Blocking/High
- **Fix interaction / anon leak:** none. Zero-dug + owner → first-dig POST permitted; zero-dug + anon → disabled spans (not `a.dig-trigger`) → no fetch, no charge. Fail-closed profile path tested.
- **No stale/contradictory test:** the two surviving 404 tests both drive an upstream `loadSummaryForServe` failure (valid 404 propagation). Zero-dug→404 assertions removed.
- **Round-1 clean items hold:** the fix commit touched only csp.ts/route.ts/load-dig-for-serve.ts + tests — `nav.ts` (NAV_SCRIPT/DIG_CLOUD_SCRIPT) and `render-dig-deeper.ts` untouched → byte-identity, poll termination, inline↔helper parity, anon inert span all unchanged. Money invariant intact (zero-dug path does strictly *less* free I/O than the tested non-zero serve; render pure; integration asserts `spend_ledger` unchanged).

## Residual (accepted, follow-up — not a merge blocker)
- **No browser-level e2e** loads the cloud dig doc under a real CSP engine and clicks a trigger; browser enforcement of `connect-src` is proven only by header-presence assertions (unit + integration `.toContain("connect-src 'self'")`) plus the jsdom execution of the shipped inline script. Since the bug was a missing directive in a static header and the script's only network ops are same-origin `fetch`, this is a reasonable guard. A Playwright cloud-scope test (load dig doc → click trigger → assert POST leaves the page) is a worthwhile follow-up.
- Content-dependent Lows (external `![img]` in a dig body would be CSP-blocked → broken image; a malformed current-version blob leaves its section un-diggable via UI — degraded, no charge/crash).

## Bottom line
Merge-ready. Full suite **2298/2298**, golden snapshot intact (local byte-identity), `tsc` EXIT 0, integration green. The dual whole-branch review converged after one fix round (2 Blocking → 0). **Push/PR/merge remains the human gate.**
