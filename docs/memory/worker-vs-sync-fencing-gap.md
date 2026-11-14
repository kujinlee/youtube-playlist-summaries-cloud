---
name: worker-vs-sync-fencing-gap
description: "FIRES-WHEN: touching backlog #17 (worker persist vs sync relocation), persist_summary's merge semantics, or a CAS-on-serial idea — the ADDRESS half is dissolved by ADR-0006, the reservation half closed; residue is persist_summary's merge semantics until the cutover"
metadata: 
  node_type: memory
  type: project
  originSessionId: 18820d36-e0cd-46c7-945b-e5f3417ebb5f
  modified: 2026-08-04T22:20:20.995Z
---

**Current state (since 2026-08-07, PR #54; `docs/backlog.md` #17 still open as of 2026-11-14): NARROWED, not closed.**
- The **address** half is dissolved by ADR-0006 (`docs/adr/0006-stable-blob-addressing.md`): the key is
  `<ws>/videos/<vid>/<gen>/summary.md`, carrying neither serial nor slug, so there is no relocation for a stale write
  to race with. Most of the five-round CAS spec is **moot rather than deferred**.
- The **reservation** half is closed by the protocol in [[reservation-guards-spending-not-recording]].
- **Residue:** anything depending on `persist_summary`'s merge semantics, which ADR-0006 replaces but which has not been
  cut over. Re-read the CAS spec against the manifest rather than assuming a given finding survived — the halves
  failed differently.

**Facts still worth keeping:**
1. **Lease-fencing does NOT fix this class.** The worker's lease stays valid; what goes stale is the **serial**.
2. **`sweep_expired_leases` (0008:167-181) can mark a job `dead_letter`/`cancelled` while its worker is still running**
   and about to write (it clears `locked_by`/`lease_token` on an expired *active* job). Any fence must handle it.
3. **The selection rule** is not "has this job written?" but **"can it write AFTER the relocation enumerated the old
   base?"** — why `completed`/`failed` are safe.
4. Before any work adding a migration here, [[integration-suite-does-not-apply-migrations]] mattered (it once hid two
   real failures).

## History
- **The race (2026-08-04):** `summary-handler.ts:95-96` pinned `baseName` from the reserved serial, then spent minutes
  in transcript + Gemini before persisting at `:156` (`dig-handler.ts:51-57` the same). A sync relocating that base
  inside the window lost to the stale persist (`persist_summary` coalesces `p_video->>'summaryMd'`, `0021:135`): row at
  `007_alpha.md`, serial 3, paid digs stranded at `dig/003_alpha/`. Line numbers are as of that date.
- **PR #45 (`0ff3b3b`, 2026-08-04):** `reconcileCloudBase` refuses to relocate while a job that may still write is
  pending — closes the wide window only; its first version missed fact 2 (Codex Blocking). Fully obsoleted by ADR-0006.
- The planned durable fix was a CAS on the serial in `persist_summary`, argued as the first piece of stable-blob
  addressing; ADR-0006 replaced it.

Related: [[serial-coherence-slice-state]], [[dual-review-what-it-catches]].
