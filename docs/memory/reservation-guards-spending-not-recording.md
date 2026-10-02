---
name: reservation-guards-spending-not-recording
description: "FIRES-WHEN: designing a lease or reservation, or rejecting a record after paid work — A lease guards STARTING a paid call, never recording its result — declining the reviewer's fence kept paid work that rejecting it would have discarded without preventing the charge"
metadata: 
  node_type: memory
  type: project
  originSessionId: 562085d6-32ed-48ac-9814-b2f5e07b1cfe
  modified: 2026-08-07T23:36:24.941Z
---

**Decided 2026-08-07** while closing blob-addressing handoff item 4 (PR #54, `ccc7eb7`).

The reviewer (r6 Claude H5) proposed a `lease_token` that the record-flip must **match**, so a writer
whose lease had been reclaimed would be **rejected**. Declined, and the reasoning generalises:

> **A reservation guards SPENDING, not RECORDING.** At most one writer may *start* a paid call per
> slot. A writer that already paid always records.

**Why.** In the measured race (`P22`) both Gemini calls are already paid for by the time the first
writer tries to record — the charge happened at *reserve* time. Rejecting the loser does not prevent
the double charge; it discards one of the two things we bought. And under append-only the loser's row
is the **designed state**: `video_artifacts_paid_uq` keys on `(slot, generation_id)`, so two recorded
generations in one slot is what append-only *means*, and `current` ranks them.

The actual defect was that **the lease expired while the worker was still alive**. That is fixed by
**renewal**, not rejection. Renewal still needs the token (a reclaimed worker must not renew the *new*
holder's lease), so the token identifies the holder rather than vetoing a record — and a failed
renewal tells the loser *while it is still working*, which is strictly better than learning at record
time when the money is gone.

**Generalisable test when a reviewer proposes a fence: follow the money and ask WHEN the cost is
incurred.** If the spend already happened upstream of the thing being rejected, the fence adds a
second loss instead of preventing the first.

**Bounding renewal is mandatory**, or it re-creates the failure the reclaim exists to prevent: a
*hung* worker (alive, not progressing) would renew forever. The ceiling measures from a separate
`reserved_at`, because `lease_expires_at` moves on every renewal. It is openly a heuristic — a
genuinely slow worker past the ceiling can still be reclaimed and then we pay twice, and no protocol
can tell *slow* from *stuck* from outside.

Precedent worth reusing: `reserve_serve_model` (`0014:50-70`) already does reclaim-and-reserve as ONE
upsert with a typed outcome, and orders **live-lease-first, exhaustion-second** — `busy` means come
back, `exhausted` means never retry, and only the second is terminal.

See [[blob-addressing-spec-state]], [[worker-vs-sync-fencing-gap]] (backlog #17, now narrowed: the
address half dissolved, the reservation half closed here).
