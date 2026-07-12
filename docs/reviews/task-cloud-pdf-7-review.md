# Task 7 — refactor `serveCloud` through helpers (characterization) — dual review trail

**File:** `app/api/html/[id]/route.ts` (serveCloud rewired). Base 84fd581 → head 121b2af. **CLEAN — no fixes.**

## Both passes: 0 Blocking / High / Medium / Low — Approved
Faithful behavior-preserving refactor; the route core shrank ~95→~30 lines with no observable behavior change.

**Codex (gpt-5.5)** — verified against the old code (`84fd581:route.ts`):
- Money invariant: `format=md` short-circuits (route.ts:46-52) BEFORE `resolveAndParse` (:55); loadSummaryForServe never calls resolveMagazineModel.
- Outer try/catch: identical `statusCode===400→400 / else→500` mapping (:65-68 vs old :116-119).
- Status/string parity across ALL branches (unowned/unknown/committed/absent/missing-blob/denied/busy/attempts_exhausted/at_capacity/over_budget/ok).
- Only new behavior = benign 409 (assertCloudSummaryMdKey); safe for worker keys `${padSerial}_${slugify}.md`.
- CSP nonce fresh per request; `{nonce, dig:false}`; stale marker propagated; md headers/title unchanged. assertVideoId still pre-auth.

**Claude (sonnet)** — corroborated all of the above branch-by-branch; additionally verified `serve-summary-core.ts` is **byte-identical** base→head (this diff is pure route-wiring — no unreviewed logic), so the 409 was already reviewed in Task 6, not introduced here. Retained imports still used by untouched `serveLocal`. The mid-helper-throw→outer-catch path confirmed by the existing `html-serve-cloud` test.

**Test evidence (implementer):** html-serve-cloud 16/16 + html-download 12/12 IDENTICAL before/after (no test edits); full suite 2050/2050; tsc clean. md path confirmed no `reserve_serve_model` / unchanged `spend_ledger`.

**Final:** Both converged CLEAN with zero findings. No fix cycle needed. The T6 try/catch-parity watch-item was satisfied (outer catch preserved); the new-409 watch-item confirmed safe.
