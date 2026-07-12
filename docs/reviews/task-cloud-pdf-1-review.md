# Task 1 — Claude code review (SDD task-reviewer)

**Target:** `tests/integration/pdf-put-atomicity.test.ts` + `docs/reviews/spec-cloud-pdf-atomicity.md`
**Base:** 629f12e · **Head:** 7d5db26 · **Model:** sonnet · **Date:** 2026-07-11

## Spec Compliance — ✅

Matches the Task 1 brief exactly: verbatim test body; two files changed (test + atomicity review doc), matching the brief's file list.
- Real helpers only (`adminClient`, `newUser`, `signInAs`, `seedPlaylist`, `getStorageBundle`, `getPrincipalFromSession`) — verified against `helpers/clients.ts`, `helpers/seed.ts`, `lib/storage/resolve.ts`. No invented helpers.
- **Session-client-only honored:** `getStorageBundle({ supabaseClient: client })` (test:24) uses the `signInAs`-derived client → `SupabaseBlobStore(session client)`; probe put/get/delete run RLS-scoped. `adminClient()` used only for `seedPlaylist`.
- Genuinely exercises real Supabase Storage (real HTTP round-trips through `SupabaseBlobStore`; inversion sanity-check flipped the final assertion and observed a real failure `Received: true` → proves live bytes, not vacuous).

⚠️ Not independently reproduced: the "3 consecutive clean runs" + inversion output are self-reported (per SDD instructions the reviewer trusts, does not re-run). Evidence trail internally consistent. **Controller resolution:** accepted — evidence consistent, gate verdict trusted.

## Strengths
- Verbatim brief body; no scope creep.
- Correctly resolved the illustrative-CLI ambiguity by adopting the repo's per-file `beforeAll`/`afterAll` `STORAGE_BACKEND` env-restore pattern (grepped sibling `*-cloud` integration tests); documented transparently.
- Non-vacuousness well-addressed: pre-loop `put(A)` guarantees the object exists, so a `null` read reflects `get`'s error→null mapping, not absence; inversion sanity-check rules out the all-nulls vacuous pass.
- Review doc correctly caveats LOCAL Docker Storage vs production S3 semantics.
- Commit scoped to exactly the two intended files.

## Issues
### Critical / Important
None.

### Minor (recorded for whole-branch triage — not fixed this task)
1. **M1 — torn-read-as-error blind spot.** `SupabaseBlobStore.get` collapses every download error to `null`; the test loop `continue`s on `null` (test:35). A torn read that surfaces as a storage-API error (rather than corrupt bytes) would be absorbed as "absent" and pass. Inherited from the brief's mandated verbatim code; inversion check partially mitigates (real non-null data does flow through). Worth a one-line note in the atomicity doc for future readers.
2. **M2 — cosmetic arithmetic.** Review doc's "64 interleavings" framing is loose (8w+8r=16 ops/run×3=48, or 8×8=64 pairwise). Cosmetic; conclusion unaffected.

## Assessment
**Task quality: Approved.** Faithful to the brief, correct client usage, demonstrably non-vacuous, accurate doc with the local-vs-production caveat. Only Minor issues, all pre-existing in the brief's design.

---

## Round 2 (Claude re-review of strengthened fix 5b8fe64)
**CONVERGED.** All five round-1 Codex findings (B1/B2/H1/M1/L1) verified genuinely fixed, not reworded. Independently ran `npm run test:integration -- pdf-put-atomicity` against live local Supabase (1 passed, ~2.1s, no flake) and `npx tsc --noEmit` (clean). No new Critical/Important. Minor design note: concurrency shape changed from many-writers to one-writer-per-round — arguably *more* faithful to ADR 0003's single-overwrite-vs-concurrent-reader scenario, not a regression.

## Final state (after Codex R2/R3 wording convergence, commit 0faa121 + doc:85 nit)
Both passes converged. Codex R2's B2 was adjudicated an overclaim/wording issue (server-side overlap is client-unprovable) and resolved by rewording test comments + doc to frame both-generations as *generation coverage*, naming the per-read homogeneity check as the atomicity oracle. Gate verdict: **PASS on local stack → Task 8 proceeds** (bare-put content-addressed cache), subject to the local-only caveat.
