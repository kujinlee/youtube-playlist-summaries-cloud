---
name: serial-coherence-slice-state
description: "FIRES-WHEN: citing PR #42 or serial coherence — Serial-coherence cloud-sync slice — MERGED to master (PR #42, squash f8703bc, 2026-08-03) after 5 review rounds; one High deliberately deferred to backlog #17"
metadata:
  node_type: memory
  type: project
  originSessionId: 18820d36-e0cd-46c7-945b-e5f3417ebb5f
  modified: 2026-08-04T00:50:18.901Z
---

✅ **MERGED to master — PR #42, squash `f8703bc`, 2026-08-03.** Branch deleted. CI green.

Fixed a **live data-loss bug**: `base` = `<serial>_<slug>` addresses every derived blob
(`models/<base>.json`, `dig/<base>/<sectionId>.r<V>.md`) and dig content is **paid Gemini output**,
but sync recomputed `serialNumber` on the receiver while copying the sender's `summaryMd` key
verbatim — silently orphaning the paid blobs on every sync.

**Shipped:** A1 receiver adopts the sender's serial (+ migration 0023, which also fixed a **phantom
serial** — the old RPC returned a value computed *before* an idempotent insert) · A2 stop clobbering
`playlistIndex` with a storage row ordinal · A3 `lib/cloud-sync/reconcile-serial.ts` repairs an
already-diverged base (plan → copy sources-retained → verify → advance metadata → delete
best-effort) · A4 `copy` at the BlobStore seam · A6a `claimVideoSlot` returns the serial only.

**Merged with one High knowingly open — `docs/backlog.md` #17, "fence the worker persist."** The
user decided explicitly: merge now, fence as its own slice, because the gap predates the branch and
the branch is strictly better than the status quo. See [[worker-vs-sync-fencing-gap]].

**A6b (drop the `position` COLUMN) is still open** and is NOT what the original A6 assumed — see
[[position-column-is-not-vestigial]].

**The process lesson from this slice is the bigger takeaway:** two integration tests were found to
be *pinning bugs rather than guarding against them*, and that was invisible because the integration
suite had been running against a stale schema — see
[[integration-suite-does-not-apply-migrations]].

Review trail: `docs/reviews/task-A-serial-coherence-branch{,-v2,-v3,-v4,-v5}-*.md`, each with a
coordinator adjudication section. Plan:
`docs/superpowers/plans/2026-07-31-serial-coherence-sync.md`.

**Sequenced behind this** (each needs its own spec + merge gate): **B** stable section identity,
**C** authority + divergence detection, **D** cloud rebuild parity — plus the proposed ADR-0006
stable-blob-addressing re-architecture, which may dissolve B entirely.

Related: [[dual-review-what-it-catches]], [[stage3-cloud-sync-branch-state]],
[[process-conventions]], [[feedback-agree-before-filing]].
