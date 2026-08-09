---
status: proposed — supersedes the reservation protocol of ADR-0006's spec (handoff item 4)
---

# Artifacts are an append-only log; nothing coordinates writers, because writers do not contend

`video_artifacts` records what was produced. It has **no lease, no token, no attempt counter, and no
free/paid branch in the write path**. Every artifact — paid *and* free — has an immutable address
derived from an immutable generation id. Exclusivity and idempotency for producers come from the job
queue's existing `jobs_idem_active`; the money guard from the job queue's existing `ever_metered` /
`reserved_cents`; "which artifact is current" from the ranking view that already exists.

We decided this because the reservation protocol built alongside ADR-0006 produced a Blocking or High
in **six consecutive adversarial rounds**, and four of those defects were introduced by the previous
round's own fix. Every other component of that spec converged and stayed converged. The problem was
not any of the twelve defects; it was that the mechanism re-solved a problem ADR-0006 had already
dissolved.

## The load-bearing claim

Stated in one sentence so a reviewer can attack it directly rather than hunting for it in prose:

> **A producer and a replicator writing the same slot cannot collide, because the producer writes a
> NEW generation and the replicator copies an EXISTING one, and the address is derived from the
> generation id — so their writes land on different keys and append different rows.**

If that is false, this ADR is wrong and the reservation protocol should be restored. It rests on:

- `[VERIFIED: lib/cloud-sync/sync-run.ts:380-394]` — `transferClassA` copies an existing body between
  replicas. No Gemini call, no payment. Sync **replicates**; it does not produce.
- `[VERIFIED: docs/adr/0006]` + `schema/04_artifacts.sql:147-160` — the blob key is
  `<ws>/videos/<video>/<generation>/…`, derived from the generation id.
- `[VERIFIED: schema/04_artifacts.sql:154]` — `video_artifacts_paid_uq` keys on
  `(workspace, video, slot, generation)`, so two generations of one slot are two rows, never a
  conflict.

## What already serves each concern

This table is the check that was never run. Every concern has exactly one mechanism, and every
mechanism serves exactly one concern.

| Concern | Mechanism | Evidence |
|---|---|---|
| producer exclusivity | `jobs_idem_active` — one non-terminal job per (owner, playlist, video, section, kind, version) | `[VERIFIED: unique partial index on jobs]` |
| producer idempotency | the same index | as above |
| pay at most once | `jobs.ever_metered` + `reserved_cents`, durable across retries | `[VERIFIED: 0020_reservation_release.sql:25-32]` |
| execution liveness | job lease + heartbeat + `sweep_expired_leases` | `[VERIFIED: 0008_jobs_queue.sql:96-130]` |
| stable addressing | generation id → blob key | ADR-0006 |
| which artifact is current | `video_artifacts_current` ranking | `schema/04_artifacts.sql` |
| what may be deleted | `video_generations_collectable` + `body_collected` | round 8 |

The reservation protocol re-implemented rows 1–4 in a second vocabulary — `lease_token`,
`lease_expires_at`, `lease_attempts`, `reserved_by` against `jobs`' `lease_token`,
`lease_expires_at`, `attempts`, `locked_by` — and **every defect of rounds 7–12 lived in the seam
between the two**.

## Considered options

- **Keep patching the reservation (status quo, rejected).** Twelve rounds, five successive
  credentials, none surviving a round. Rejected because the failures were not independent: the fence
  had to be PERMISSIVE so a reclaimed writer could still record its paid work, and STRICT so a
  stranger could not complete a generation. Those are two different coordination philosophies —
  append-only-plus-merge, and mutual exclusion — wired to one SQL predicate. No credential resolves
  that, which is why five did not.

- **Route every write through the job queue (rejected).** Attractive until checked: sync replicates
  rather than produces `[VERIFIED: sync-run.ts:380-394]`, so enqueueing a job would mean *generating*
  something that already exists. The producer/replicator asymmetry is real and must be modelled, not
  flattened.

- **Append-only log, no coordination (chosen).** The writers do not contend (see the load-bearing
  claim), so there is nothing to coordinate. What remains — *which of several appended rows is
  current* — is a merge question, and the ranking view is already the merge function.

## Renders lose their special case too

`generation_id is null` currently encodes **two independent facts**:
`[VERIFIED: schema/04_artifacts.sql:95]`

```sql
constraint art_paid_has_generation check (
  (kind in ('summary','model','dig','digDeeper')) = (generation_id is not null))
```

— "this is free" (a *money* property) and "this address may be overwritten" (an *addressing*
property). That conflation is the same root cause as nullable `corrections_hash` ("no corrections" vs
"never computed") and absent-vs-failed-to-read, and it produced five of the twelve rounds' findings.

**A render therefore gets a derived generation id too:**
`hash(source_generation_ids, GENERATOR_VERSION)` `[VERIFIED: lib/html-doc/constants]`.

- Re-rendering the same source with the same renderer yields the **same** key — idempotent, nothing
  to overwrite.
- Re-rendering after a renderer upgrade yields a **different** key — a new row; the ranking picks it.

Free-ness becomes what it always was: a property of the *kind*, consulted only by the money path.

**Dissolved rather than fixed**, and this is the measure of the decision: round 8's free-render
reconciler; round 8/9's `NULL = NULL` unreachable short-circuit; round 9's tenant-confinement gap;
round 10's free-lease theft; round 11's typed `busy`; round 12's once-in-a-lifetime free reservation.
Plus `video_artifacts_free_uq` and the whole free branch of `record_artifact`.

## Consequences

**Deleted:** `reserve_artifact_slot`, `renew_artifact_lease`, the lease columns on `video_artifacts`,
`reserved_by` on `video_generations`, `video_artifacts_free_uq`, and the `pending` artifact state.
`record_artifact` becomes an append with a typed outcome and no fence.

**Retired:** §12b's caller obligation. It exists to make a fence safe; with no fence, a worker that
loses its token simply appends nothing, and the job queue already governs whether it may run at all.
The contract test stays — it now documents job-queue behaviour rather than propping up a schema
premise.

**Kept, unchanged:** stable addressing, the append-only trigger, the ranking views, tenant
confinement, the GC floor, and every guard that survived its rounds.

**Not addressed here:** direct `service_role` DML can still write these tables. With no fence to
bypass, that stops being a hole in an authorization mechanism and becomes an ordinary "trusted role
can write" property — but the append-only trigger should still be the thing that makes history
immutable, and that is a schema question this ADR does not close.

## Open design question

A render derived from **more than one** generation — a PDF containing the summary *and* its digs —
needs an identity over a **set**, while `source_generation_id` is a single column today. The choice
(a canonical sorted hash, or a join table) is deliberately left to the implementing slice; it does
not change the decision, but it must not be discovered during implementation.

## What would falsify this

- A caller that writes an artifact for a generation it did not create (breaks the disjointness claim).
- A second producer path that does not go through `jobs` (breaks exclusivity).
- A render whose identity cannot be derived deterministically (breaks the uniform-address claim).

Each is a concrete check, not a judgement — which is the point.
