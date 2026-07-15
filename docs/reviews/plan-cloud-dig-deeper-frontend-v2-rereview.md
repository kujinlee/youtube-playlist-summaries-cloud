# Plan Re-Review — Cloud Dig-Deeper Frontend — Round 2 (convergence)

**Artifact:** `docs/superpowers/plans/2026-07-14-cloud-dig-deeper-frontend.md` (+ spec), revised after round 1
**Date:** 2026-07-14
**Reviewers:** Codex (gpt-5.5) + independent Claude — both scoped to (a) verify each round-1 fix is genuine, (b) hunt defects the fixes introduced.
**Verdict:** **CONVERGED — 0 Blocking / 0 High from both.** All six round-1 fixes verified genuine against ground truth. Only doc-consistency Medium/Low items surfaced; all applied. This round is the gate.

---

## Round-1 fixes — both reviewers: VERIFIED-GENUINE

| # | Round-1 fix | Codex r2 | Claude r2 |
|---|---|---|---|
| B1 | isAnonymous ← `profiles.is_anonymous` fail-closed | GENUINE (supabase+user in scope; mockAuth widening safe) | GENUINE (traced all 4 pre-existing tests still pass; null-row test real) |
| H2 | `swapDugSection` throws unless section exists AND `data-dug="true"` | GENUINE (caught on both ready+poll paths; inline mirrors) | GENUINE |
| H3 | inline-execution test of shipped `digCloudScript` | GENUINE (`new Function` boots, 200-ready no timers, 429 re-POST holds) | GENUINE (DOMParser/adoptNode/URLSearchParams/location all in jsdom env) |
| M1 | poll deadline checked after sleep | GENUINE (no fetch past ceiling) | GENUINE |
| M3 | pre-change byte golden | SOUND if ordering followed | GENUINE + well-designed (genVersion:3 < DIG_GENERATOR_VERSION=9 ⇒ golden locks the exact `dig-refresh` line M4 edits) |
| M4 | `dig-refresh` gated off in cloud (`&& !cloud`) | GENUINE (byte-identical when off) | GENUINE (stale-section cloud test asserts absence) |

Both independently re-confirmed the load-bearing invariants: **byte-identity when `cloud` undefined** (every touched expression collapses to today's output; the stale-section golden pins the one non-obvious case), **`NAV_SCRIPT` untouched** (separate `DIG_CLOUD_SCRIPT` + diff guard), **money invariant** (dig branch = `loadDigForServe` + render + `fileResponse`; the added `profiles` read is a free select; dig-state is blob-presence only; T6 asserts `spend_ledger` unchanged across serve + poll), **anon defense-in-depth** (inert `<span>` + server 403 fallback), and **all §9 behaviors 1–15 have a test**.

---

## New items this round (doc-consistency only; all applied)

- **M5-incomplete (Medium, both):** spec still described the old "branch inside `navScript`" model in four places (§7.2 intro line 96, §9 behavior 5 line 137, §10 render-mode line 156, §11 files table line 172), contradicting the fixed separate-`digCloudScript` architecture and the plan's own tests. **Applied:** all four reworded to "separate `digCloudScript` injected in place of `navScript`; `NAV_SCRIPT` untouched; no SSE."
- **L (Codex):** plan comment "not covered by jsdom tests" was stale (the inline is now smoke-executed). **Applied:** reworded to note the inline is executed for ready/error/toggle, poll-timer path via TS mirror.
- **L (Codex):** plan `mockAuth` comment falsely said "undefined ⇒ null row ⇒ fail-closed anon" (helper returns `is_anonymous:false`). **Applied:** corrected — undefined defaults to registered for back-compat; the dedicated null-row test exercises fail-closed.
- **L-a (Claude):** golden capture-order trap — already mitigated by Step 1b being its own commit before the renderer edit (+ `git stash` guidance). No further change.
- **L-b (Claude):** profiles hard-network-reject → 500 (not fail-closed) — verified this exactly mirrors the POST route precedent (no try/catch there either) and is not a money-path change. No action.

---

## Convergence determination

Both reviewers returned **0 Blocking / 0 High** on the revised artifact and verified every round-1 fix is genuine (not reworded). The only residuals were spec/plan wording contradictions, now fixed with **no new design surface** and no code-behavior change. Per the dev-process Iterative Re-Review rule, a full dual re-review round with no new Blocking/High is the convergence gate. **Plan gate satisfied — proceeding to SDD implementation (T1–T6);** push/PR/merge remains the human gate.
