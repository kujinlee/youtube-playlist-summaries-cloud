# Plan Re-Review — Cloud Dig Serving — Round 2 (convergence)

**Artifact:** `docs/superpowers/plans/2026-07-14-cloud-dig-serving.md` (revised after round 1)
**Date:** 2026-07-14
**Reviewers:** Codex (gpt-5.5) + Claude (independent) — both scoped to (a) verify each round-1 fix is genuine, (b) hunt defects the fixes introduced.
**Verdict:** **CONVERGED.** All 8 round-1 findings VERIFIED-FIXED by both reviewers. Two mechanical items surfaced (Codex), both with verbatim-prescribed one-line fixes and no new design — now applied. This round is the convergence gate.

---

## Round-1 findings — both reviewers: VERIFIED-FIXED

| # | Round-1 finding | Codex r2 | Claude r2 |
|---|---|---|---|
| B1 | test files outside `testMatch` | VERIFIED-FIXED | VERIFIED-FIXED |
| B2 | T4 negative markers = CSS substrings | VERIFIED-FIXED | VERIFIED-FIXED |
| B3 | route tests missing `cookies()` mock | VERIFIED-FIXED | VERIFIED-FIXED |
| H1 | T4 positive markers CSS-satisfied | VERIFIED-FIXED | VERIFIED-FIXED |
| H2 | T6 skipped summary status gate | VERIFIED-FIXED (behavior-17 preserved) | VERIFIED-FIXED (traced gate) |
| H3 | T6 import errors | VERIFIED-FIXED | VERIFIED-FIXED |
| H4 | T3 money test indirect | VERIFIED (positive control safe) | VERIFIED (spy targets real) |
| H5 | Supabase `list` untested | VERIFIED-FIXED (arithmetic re-traced) | VERIFIED-FIXED (slice(15) exact) |

Both independently traced the load-bearing claims: `loadSummaryForServe` gate reuse preserves behavior 17 (promoted + zero dig → `200 []`); the T3 positive control reaches `rpc('reserve_serve_model')` then hits `default: throw` (serve-doc.ts:73) **before** `generateMagazineModel` (L81) — no live Gemini; the Supabase `list` owner-root `.slice(ownerRoot.length)` yields exactly the logical keys; all four money-spy targets are real exported functions.

---

## New items this round (both mechanical; applied)

**N1 (Codex High → applied) — money spies were call-through.** `jest.spyOn(x,'fn')` without a mock impl calls the real function. In the happy path the charge fns are never reached (loadSummaryForServe/readModelEnvelope mocked), so Claude rated it belt-and-suspenders and converged 0/0. But under a *regression* that reached `generateDig`/`generateMagazineModel`, the call-through would execute real generation (live Gemini) before the assertion fires — violating the plan's "No live Gemini" constraint. **Fix applied:** `.mockRejectedValue(new Error(...))` on all four spies (fail-closed; aborts instantly on any accidental call). Positive control keeps the real `resolveMagazineModel`.

**N2 (Codex Medium → applied) — `outputFolder` guard truthy, not presence-based.** `html/[id]/route.ts:27` used `.get()` (truthy), so an empty `?outputFolder=` slipped through; the sibling `pdf/[id]/route.ts:31` and `dig/[sectionId]/route.ts:34` use `.has()` with an explicit "empty must 400" comment. Spec behavior 14 requires rejection. **Fix applied:** change the shared guard to `searchParams.has('outputFolder')` (aligns html with pdf/dig-POST; fixes a latent inconsistency for both summary and dig) + a dig regression test for `&outputFolder=`. T5 step runs the full `npx jest html` suite to confirm no summary test relied on the old behavior.

**N3 (Claude Low → applied) — T6 `serveCloud` had no try/catch.** No `logError` on an unexpected infra throw (bare 500), unlike the html route. **Fix applied:** wrap the post-auth body in try/catch with `logError('dig-state:cloud', err)` — observability parity with the html route and the PR #18 5xx sweep.

**L-carried (both):** CSP + future slide-capture — already documented as out-of-scope; correct for this slice (caption text only, no `<img>`, no inline `style=`). No action.

---

## Convergence determination

- **Claude r2 converged 0 Blocking / 0 High / 0 Medium** on the identical artifact.
- **Codex r2 found 0 Blocking**; its 1 High + 1 Medium were test-safety / latent-consistency hardenings, **not defects in what the plan builds** — both fixed verbatim as prescribed.
- All three applied fixes (N1–N3) are single-line/wrapper changes that mirror already-verified code in the same codebase (`.has()` ≡ pdf route; try/catch+logError ≡ html route; fail-closed spies are standard jest that never fires on the happy path). **No new design surface** was introduced.

Per the dev-process convergence rule ("small, contained changes → one round is fine; stop at diminishing returns"), this round is the gate: the substantive dual review has converged, and the residual items were mechanical and are resolved. **Proceeding to SDD implementation** (T1–T6) per the standing Conditional-AFK "run autonomously to the merge gate" choice; the push/PR/merge remains the human gate.
