# Plan Review — Cloud Dig-Deeper Frontend — Round 1

**Artifact:** `docs/superpowers/plans/2026-07-14-cloud-dig-deeper-frontend.md` (+ spec)
**Date:** 2026-07-14
**Reviewers:** Codex (gpt-5.5, via coordinator) + independent Claude subagent — both adversarial, scoped to byte-identity-when-off, money invariant, poll correctness, anon handling, test validity, coverage.
**Verdict:** **1 Blocking + 3 High + Mediums — all confirmed against ground truth and fixed.** Round 2 (re-review) required (Blocking fix + shared-code + non-trivial changes).

Mandatory re-review trigger: the plan changes already-merged shared `lib/html-doc/nav.ts` + `render-dig-deeper.ts`.

---

## Findings & dispositions

| # | Sev | Finding | Ground-truth confirmation | Fix applied |
|---|---|---|---|---|
| B1 | **Blocking** (both reviewers, + independently confirmed by coordinator) | Task 5 resolved `isAnonymous` from `user.is_anonymous` — unreliable AND fail-open. Anon pre-disable would silently never fire (behavior 7 / D3 violated); both its tests were vacuous. | POST route `app/api/videos/[id]/dig/[sectionId]/route.ts:47-61` has an explicit comment forbidding `user.is_anonymous`, reads `profiles.is_anonymous` fail-closed (`!== false`). | Task 5 now reads `profiles.is_anonymous` fail-closed (mirrors POST); `mockAuth` widened to stub `.from`; added a null-row fail-closed test. Spec §7.1 updated. |
| H1 | **High** (Claude) | Task 4 test `not.toContain('dg-expand-all')` can never pass — the token lives in always-emitted `DIG_DOC_CSS` (`render-dig-deeper.ts:163`, style block at :489). | Existing `render-dig-deeper-readonly.test.ts:35-38` uses element markers for exactly this reason. | Changed to `not.toContain('class="dg-expand-all"')` + `not.toContain('⤢ expand all')`. |
| H2 | **High** (Codex) | `swapDugSection` treated a missing/not-dug re-fetched section as success → if dig-state over-reports (malformed blob), trigger stuck at ⏳ forever. | dig-state is presence-based (`dig-state/route.ts`), can over-report vs the parsing serve loader (known M1 from the serving slice). | `swapDugSection` now throws unless the re-fetched section exists AND `data-dug="true"` → maps to `⚠ retry`. Inline `_swap` mirrors. Added over-report test. |
| H3 | **High** (Codex; Claude L1/M4) | Tests exercised only the TS mirror helpers, not the shipped inline `DIG_CLOUD_SCRIPT` (substring check only). A broken POST URL / status branch / toggle in the shipped string would pass. | The inline string is what the browser runs; repo accepts a DRIFT WARNING for `NAV_SCRIPT`. | Added `nav-cloud-dig-inline.test.ts` that **executes** the shipped `digCloudScript()` body in jsdom (200-ready swap, 429 + re-POST, toggle) — covers behaviors 9/14/15 at the real code. |
| M1 | Medium (Codex) | `pollUntilDug` off-by-one: checked deadline before sleep, so a fetch could fire past the 180 s ceiling. | — | Loop restructured to check `now() > deadline` **after** the sleep. Inline `_poll` already checked post-sleep (unchanged). |
| M2 | Medium (Codex) | Loading text `⏳` vs spec's `⏳ generating…` (§4/§7). | spec §4, §7. | Helper + inline set `⏳ generating…`; added a synchronous-loading-copy test. |
| M3 | Medium (Codex) | Byte-identity test compared two post-change calls, not pre-slice output — can't catch an unrelated local byte change. | — | Added `render-dig-deeper.golden.test.ts` — a committed snapshot captured from the pre-change renderer; the change must keep it matching. |
| M4 | Medium (Codex) | Stale dug section still emits `.dig-refresh` with no cloud handler → dead `↻ outdated`. Spec §12 wording contradicted the renderer. | `render-dig-deeper.ts:296-297` emits `dig-refresh` under `!readOnly`; cloud script handles only toggle+trigger. | Render suppresses `dig-refresh` when `cloud` set (byte-identical when off); added a stale-section cloud test; spec §12 rewritten. |
| M5 | Medium (Codex) | Spec §7.2 said "one navScript with a branch"; plan uses a separate script → conflict. | Editing `NAV_SCRIPT` would break byte-identity-when-off. | Spec §7.2 rewritten to justify the separate `digCloudScript` (byte-identity) with the drift mitigations. |
| M6 | Medium (Claude) | Behaviors 12 (404/409/network) & 14 (retry re-POST) under-tested. | spec §9. | Added 404/409, network-reject, over-report (→retry) helper tests + inline re-POST test. |
| L1 | Low (Codex) | Money-invariant proof (T6) didn't poll dig-state. | — | T6 now also calls `dig-state` and asserts `spend_ledger` unchanged. |
| L2 | Low (Claude) | T6 blob must be written at `DIG_GENERATOR_VERSION` or the section renders un-dug. | `dig-state/route.ts:46` filters `.r{V}`. | Added an explicit note to T6. |

**Cleared by both (no defect):** render byte-identity when `cloud` absent (`(readOnly||cloud)`, `cloud?.isAnonymous`, `nav` ternary all collapse identically); `NAV_SCRIPT` untouched (separate constant); money invariant (serve/poll are read-only, no `reserve_serve_model`/generation reachable, no auto-trigger on open); test paths under `testMatch`; delegate selector `a.dig-trigger[data-section]` excludes the anon `<span>`; poll terminates.

Round 2 re-review dispatched to verify each fix is genuine and hunt for defects the fixes introduced.
