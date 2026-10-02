---
name: worker-vs-sync-fencing-gap
description: "FIRES-WHEN: needing the worker-versus-sync fencing state (backlog #17) — Backlog #17 — sync has no mutual exclusion vs the worker. PARTIAL mitigation merged (PR #45); the durable CAS fence is still open and is the FIRST piece of the stable-blob-addressing architecture"
metadata: 
  node_type: memory
  type: project
  originSessionId: 18820d36-e0cd-46c7-945b-e5f3417ebb5f
  modified: 2026-08-04T22:20:20.995Z
---

**Status: partially mitigated, still open.** `docs/backlog.md` #17.

**The race.** `summary-handler.ts:95-96` pins `baseName` from the serial it reserved, then spends
**minutes** in transcript + Gemini before persisting at `:156` (`dig-handler.ts:51-57` pins `base` the
same way). If a sync relocates that base inside the window, the stale persist lands afterwards and
**wins on the key** — `persist_summary` resolves it as
`coalesce(p_video->>'summaryMd', v.data->>'summaryMd')` (`0021:135`) while `serialNumber` is restored
from the row. Result: row at `007_alpha.md`, serial 3, paid digs stranded at `dig/003_alpha/` with
`dig/007_alpha/*` already deleted by cleanup.

**✅ Merged mitigation — PR #45 (`0ff3b3b`, 2026-08-04).** `reconcileCloudBase` refuses to relocate
while a job that may still write is pending. Closes the **wide** window only.

**Three facts from that work worth keeping:**
1. **Lease-fencing does NOT fix this.** The worker's lease stays valid and A3 never touches the job;
   what goes stale is the **serial**. The backlog title said "fence the worker persist", which points
   at the wrong mechanism.
2. **`sweep_expired_leases` (0008:167-181) can mark a job `dead_letter`/`cancelled` while its worker
   is still running** and about to write — it clears `locked_by`/`lease_token` on an expired *active*
   job. Any fence must handle this; the guard's first version missed it (Codex Blocking).
3. **The selection rule** is not "has this job written?" but **"can it write AFTER the relocation
   enumerated the old base?"** That is why `completed`/`failed` are safe — whatever they wrote is
   already under the old base and `paidKeysUnder` moves it.

**Still open — the durable fix: a compare-and-swap on the serial in `persist_summary`.** The residual
window is NOT milliseconds: the copy phase between probe and metadata write is N sequential blob
round-trips, so a job enqueued and claimed inside it still reads the pre-relocation serial.

**Why to build it before more spec work:** it is the **first piece of the stable-blob-addressing
architecture**, not throwaway. That design rests on the claim *"a conditional write on one small row
is trivially sufficient"* (spec §5.1) — and **nothing in this codebase does a conditional publish
today**, so the claim is untested. Only the column it keys on changes later (`serialNumber` →
manifest `blob_key`). Contrast PR #45's guard, which is fully obsoleted by that design.

**Precondition before starting:** fix [[integration-suite-does-not-apply-migrations]] first — the CAS
adds a migration, and that gap already hid two real failures once.

Related: [[serial-coherence-slice-state]], [[dual-review-what-it-catches]].

**⟳ 2026-08-07 — NARROWED, not closed (PR #54).** The **address** half is dissolved by ADR-0006: the key is `<ws>/videos/<vid>/<gen>/summary.md`, carrying neither serial nor slug, so there is no relocation for a stale write to race with — most of the five-round CAS spec is **moot rather than deferred**. The **reservation** half was never about addressing and is closed by the protocol in [[reservation-guards-spending-not-recording]]. Residue: anything depending on `persist_summary`'s merge semantics, which ADR-0006 replaces but which has not been cut over. Re-read the CAS spec against the manifest rather than assuming a given finding survived — the halves failed differently.
