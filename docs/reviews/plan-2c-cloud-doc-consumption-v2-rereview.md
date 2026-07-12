# Claude Adversarial Re-Review — Stage 2c Plan (round 2)

**Reviewer:** Claude (independent subagent). **Date:** 2026-07-11. **Artifact:** plan v2 (`2b6b24f`).
**Verdict: NOT converged at v2 — 1 new High + 2 Medium; all fixed in v2.1.**

## Part A — round-1 findings verified GENUINE (not reworded)
H1 dead tokens ✅ · Claude M1 role=menuitem ✅ · Claude M2 stripComputed ✅ · Claude M3 mock name/shape ✅ (see M-a) · Claude M4 modal self-restore drop ✅ (ShareDialog is a separate new file — no edit to the 2b modal) · Codex H2 in-flight tests ✅ added (see L-a) · Codex H3 deploy note ✅ · caller audit ✅ · non-null expiry ✅ · TTL-7d ✅ · a11y initial-focus ✅ / Tab-trap ⚠️ (see M-b) · encode test ✅ correct.

## Part B — new-defect hunt
- stripComputed `Omit<T,'updatedAt'|'summaryReady'>` + `v as any` destructure — valid TS, strip tests fine. **But surfaced H-new below.**
- Encode assertion CORRECT: `new URL('/api/html/a%2Fb%3Fc%23d?…').pathname` keeps `%2F/%3F/%23` encoded (WHATWG doesn't re-decode), query survives — `pathname` + `format=md` both hold.
- Dropping modal self-restore: no impact on NewPlaylistModal (drop lives only in the ShareDialog copy).

## BLOCKING — none.

## HIGH
**H-new — Task 2 `summaryReady` derivation breaks a currently-green test the plan claims stays green.**
`tests/lib/storage/supabase-metadata-store.test.ts:159` asserts `idx.videos` `toEqual([{id:'v1'},{id:'v2'}])` with artifacts-absent rows. Today passes (`updatedAt: undefined` ignored by toEqual). After the mapping, absent artifacts → `undefined === 'promoted'` → **`false`** (defined boolean, not undefined) → each item `{id, summaryReady:false}` → `toEqual` rejects. Task 2 Step 7 claims "full suite green … pass unchanged" — false. Same break-class the plan documented for the route test (M3) but missed for the store's own test. **Fix:** enumerate updating `:159` to `[{id:'v1',summaryReady:false},{id:'v2',summaryReady:false}]`; do NOT change the derivation to yield undefined (Step 1 intentionally asserts `false`).

## MEDIUM
**M-a — Task 1 route-test note falsehood.** v2's "if any assertion reads expiresAt as a string it still holds (null here)" is false with an `expires_at:null` default — `share-mint-route.test.ts:37` `typeof body.expiresAt==='string'` would FAIL. Also the replacement snippet risked dropping the `p_token_hash` 64-hex assertions (`:40-48`). **Fix:** keep `expires_at` a string in the default mock; add `id` assertion without replacing the block (keep the hash asserts).

**M-b — a11y Tab-trap assertion vacuous.** jsdom doesn't move focus on a Tab keydown; with initial focus already inside the dialog, `dialog.contains(activeElement)` is trivially true — passes even with no trap. **Fix:** focus the LAST focusable, fire Tab, assert focus wrapped to the FIRST (the handler's `preventDefault()+focus()` is what jsdom can observe).

## LOW
**L-a — double-click tests weakly discriminating.** `act()` flushes the first click's state-disable before the 2nd click, so they pass for state-disable alone, not specifically the synchronous ref. Keep them (RED vs zero guard) but annotate honestly; keep the ref as correctness-by-construction (2b precedent). Share-create doesn't charge → defense-in-depth, not a money-gate.

## Convergence verdict
NOT converged at v2 (one new High). All fixes are one-to-few-line mechanical plan edits, no design reopened. Both reviewers recommend: apply the edits, then a single confirmation pass suffices — a full round-3 is diminishing returns.

## Resolution (v2.1)
All addressed: Task 2 Step 7 migrates the `:159` exact-shape assertion (+ grep for others); Task 1 Step 5 keeps a string expiry and adds `id` without replacing the block; a11y test rewritten to exercise the wrap (focus last → Tab → assert first); double-click honest note added. Confirmed by a focused Codex pass on the changed sections.
