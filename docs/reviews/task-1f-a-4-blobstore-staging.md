# Task 4 review — SupabaseBlobStore uuid-prefixed staging + hardened `promote` (worker MD path)

**Commit:** `ccaf5c1`
**Gate:** single round Claude + Codex (not a §8 trigger). Execution: SDD.

## Reviews
**Codex adversarial — SOUND** (no Critical/Important). Verified: `promote` rechecks a **fresh post-error** `exists(ref.finalKey)` (`supabase-blob-store.ts:57`) and **throws if final remains absent** (`:61`) — no silent MD data loss; race tests cover absent→present (resolve) and absent→absent (throw); regex assertions pin `_staging/<uuid>/<logical key>`, not `.*`; model path uses plain `put` (untouched); tsc clean.

**Claude task-review — Approved** (no Critical/Important). Independently confirmed (tsc + `jest supabase-blob-store` 21 tests green, grep-scoped): uuid-prefixed `_staging/${crypto.randomUUID()}/${key}`; the swallow-as-success branch calls a **fresh** `exists()` (new `download()`), not the precheck boolean; a real move failure with the final absent falls through to `throw`; only `consistency.ts` ← `summary-handler.ts` (worker MD) call `putStaged`/`promote`; the F5 race test (`download` `mockResolvedValueOnce(absent)`→present, `move` errors, `expect(move).toHaveBeenCalledTimes(1)`) genuinely proves the post-error recheck path (a precheck-only impl fails it). Adapted regex assertions genuinely pin the new format, not loosened.

## Minor findings — DEFERRED to Task 9 whole-branch triage
1. **[should-fix-before-merge]** `tests/lib/supabase-blob-store-staging.test.ts:16` (uuid staging) calls `putStaged` once, so it doesn't *prove* per-attempt uniqueness (a constant uuid-shaped prefix would pass). Impl is correct (`crypto.randomUUID()`), but the test should call twice and assert distinct `tempKey`s — this proves the change's core purpose. (Codex)
2. `tests/lib/supabase-blob-store-staging.test.ts:38-45` — the "swallows move error" test's `download` mock reports final present on *every* call, so the precheck short-circuits and `move()` is never invoked; the name overstates what it verifies (the real path is covered by the F5 test 4). Rename or make it seed absent→present. Both reviewers note it's from the brief's Step 1 verbatim, not implementer-introduced; non-blocking. (Codex + Claude)

## Result
Tests: RED 2/4→GREEN 4/4, full suite 1714/1714, tsc clean. Critical silent-data-loss path correctly handled. **Task 4 COMPLETE.**
