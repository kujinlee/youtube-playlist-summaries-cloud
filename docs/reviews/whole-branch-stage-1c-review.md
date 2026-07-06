# Whole-Branch Final Review — Stage 1C (Supabase MetadataStore + BlobStore Adapters)

**Reviewer:** Claude (Opus), cross-cutting whole-branch pass (SDD final review)
**Range:** 9a7886d..109e310 (23 commits) | **Method:** by-eye cross-cutting pass over the async seam + both Supabase adapters + migration 0007, against a live local Supabase stack.
**Verdict:** CHANGES NEEDED → resolved (see Resolution). READY TO MERGE.

> Note: this doc was written up in the Phase-5 finish (2026-07-06) from the C-1 commit
> record and a full re-verification; the whole-branch pass itself ran at the end of the
> implementation session (its sole surviving finding, C-1, was fixed in `109e310`). The
> Codex-specific adversarial pass over the whole branch may be re-attempted before merge
> if access returns — per `docs/plugins.md`, the Claude adversarial review satisfies the gate.

## Blocking / High

- **C-1 — `reconcile_membership` RPC did not preserve manual-archive intent (sticky parity gap).**
  The Postgres `reconcile_membership` RPC used a single blanket `UPDATE` to set membership
  state from the incoming playlist snapshot. That silently **un-archived a video the user had
  manually archived** while it was still present in the playlist — diverging from the local
  `MetadataStore`'s three-way reconcile logic, which leaves such rows untouched. Because the
  cloud and local stores must be behaviorally interchangeable behind the seam, this was a
  correctness divergence at the DB↔store boundary, not a cosmetic one.
  → **RESOLVED (`109e310`)**: replaced the blanket `UPDATE` with two guarded `UPDATE`s that
  mirror the local three-way logic exactly:
    - absent + not-yet-removed → `archived=true,  removedFromPlaylist=true`  (auto-archive on removal)
    - present + was-removed    → `archived=false, removedFromPlaylist=false` (restore on return)
    - otherwise                → untouched (manual archive preserved; idempotent)
  Added four parity integration tests: manual-archive preserved, auto-archive on removal,
  restore on return, idempotent absent-and-already-removed.

## Cross-cutting checks that PASSED

- **DB↔blob ordered-write protocol:** blobs are written and durable **before** the metadata row
  commits; `SupabaseBlobStore` + the ordered-write consistency helper (`0bae0a3`) enforce this so
  a crash never leaves a metadata row pointing at a missing blob. Promote is idempotent.
- **Local ↔ cloud store parity:** both `MetadataStore` impls are async + transactional over the
  same contract; consumers were awaited across the whole codebase (`6592f50`). The C-1 fix closed
  the last behavioral divergence (reconcile stickiness); no other blanket-vs-guarded gaps remain.
- **RLS owner-scoping / isolation:** storage RLS + owner-scoped keys confine both stores to
  `owner_id = auth.uid()`; the blob + storage-RLS integration suite (`7296fbe`) confirms no
  cross-owner leak and correct null-coercion. Metadata RLS + write-once verified in `26a839a`.
- **Concurrency:** `claimVideoSlot` allocates distinct slots under parallel contention
  (`d62eda9`) — no double-allocation; the transactional RPC holds under `--runInBand` load.
- **Migration 0007 apply-order:** artifacts bucket + storage RLS + claim/reconcile/merge RPCs
  apply cleanly via `db reset`; no forward references.

## Verification (re-run 2026-07-06, at `109e310`)

| Check | Result |
|---|---|
| `tsc --noEmit` | clean |
| Unit (`jest`) | 1578 / 1578 pass (135 suites) |
| Integration (live local Supabase stack) | 41 / 41 pass (9 suites) |

**Verdict after resolution: READY TO MERGE.** All 13 Stage 1C tasks complete; the sole
whole-branch finding (C-1) is fixed and covered by parity tests; full suite green on a real stack.
