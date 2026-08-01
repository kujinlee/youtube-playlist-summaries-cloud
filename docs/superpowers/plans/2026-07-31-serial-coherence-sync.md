# Serial coherence in cloud-sync — Implementation Plan

**Goal:** the same video has the same `serialNumber` on both replicas, so both derive the same
`base` (`<serial>_<slug>`) and no derived blob is ever orphaned by a sync.

**The bug being fixed.** `base` is the address of every derived blob (`models/<base>.json`,
`dig/<base>/<sectionId>.r<V>.md`). Sync treats `serialNumber` as replica-local and recomputes it on
the receiver, while separately copying the sender's `summaryMd` **key**. When the replicas' serials
differ, the loser's dig and model blobs are **silently orphaned** — no error, no report, no cleanup.
Dig content costs real Gemini spend.

**Why it is a bug, not a decision** — three independent proofs:

1. `docs/superpowers/plans/2026-06-25-serial-number-filename-prefix.md` states *"`serialNumber` is
   **write-once**. Never recompute for a video that already has one."* Sync recomputes it.
2. The code contradicts itself: `sanitizeAdditiveVideo` (`sync-run.ts:123-140`) deletes
   `serialNumber` but **keeps `summaryMd`**, then `copyAdditiveVideo` sets
   `sanitized.serialNumber = slot.serialNumber` (`:216`) while writing the sender's key (`:220`).
   The receiver row says `serialNumber: 7` with its file named `003_alpha.md`.
3. The sync spec §4.1 groups it with `position`/`playlistIndex` as *"replica-local ordering"* — but
   `serialNumber` is a **UI sort column** (`app/api/videos/route.ts:18-22`) and `playlistIndex` is
   **absent** from that set.

**Design decision (user, 2026-07-31):** local numbering is authoritative; the cloud renumbers. Local
filenames live in the user's Obsidian vault where a rename breaks hand-made wiki-links; cloud blob
keys are invisible. New serials come from a shared high-water mark `max(maxLocal, maxCloud)`; **gaps
are acceptable** (`nextSerial` is `max + 1`; nothing requires density).

---

## Enumerated Behaviors

Written **before any test code**, per `docs/dev-process.md`. This table is the contract the tests are
written against.

### A4 — `rename` at the BlobStore seam

`rename` returns a **discriminated union**, not `void` — matching the existing `BlobRead` discipline
(`lib/storage/blob-store.ts`). A `void` return would force every caller to re-derive "did the source
exist?" from a second read, which is exactly the `absent`-vs-`unreadable` conflation that produced a
Blocking, three Highs, and a live 6¢→12¢ double charge in the Stage 3 review.

```ts
export type RenameResult =
  | { ok: true }
  | { ok: false; reason: 'source-absent' }
  | { ok: false; reason: 'destination-exists' }
  | { ok: false; reason: 'failed'; cause: unknown };
```

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Happy path | `rename(p, 'a.md', 'b.md')`, `a.md` exists, `b.md` absent | `{ok:true}`; bytes at `b.md`, nothing at `a.md` |
| 2 | Source absent | `a.md` does not exist | `{ok:false, reason:'source-absent'}` — **never** a silent success |
| 3 | **Destination occupied** | `b.md` already exists | `{ok:false, reason:'destination-exists'}`; **both blobs untouched**. Fail-closed: this is the promote divergence's exact shape, and an overwrite here would destroy a paid artifact |
| 4 | Backend failure | 5xx / network / RLS denial | `{ok:false, reason:'failed', cause}` — distinguishable from `source-absent`, so callers never treat a blip as absence |
| 5 | Uniform across adapters | same call on local FS / Supabase / in-memory | identical result for identical state — **no adapter-specific semantics** (the finding-#2 rule) |
| 6 | Invalid key | `from`/`to` with leading `/`, `..`, or `\0` | throws via `assertLogicalKey`, before any I/O |
| 7 | Same key | `from === to` | `{ok:true}`, no I/O — idempotent |
| 8 | Owner scoping | any call | resolves under `<owner>/<indexKey>/` only; cannot move across principals |

### A1 — Adopt the sender's serial on additive create

`claimVideoSlot(p, videoId, desiredSerial?)` — the new parameter is **optional at the call site but
its absence is meaningful**: "no preference, allocate one."

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 9 | Adopt when free | sender serial `S`; no receiver video holds `S` | receiver row gets `serialNumber = S`; `base` matches the sender's |
| 10 | Collision → allocate | another receiver video already holds `S` | receiver gets `max + 1`; **the sender is unaffected** |
| 11 | Sender has no serial | legacy row, `serialNumber` undefined | allocate `max + 1` (current behavior preserved) |
| 12 | **Row already exists** | claim called for a video already in the index | return the **persisted** serial, not a freshly computed one. *Today `claim_video_slot` computes `v_serial` before its idempotent insert and returns it even when the insert no-ops — a phantom serial that was never stored. Follow `reserve_video_slot` (`0009:88-99`), which re-selects after insert.* |
| 13 | Invalid desired serial | `≤ 0`, non-integer, `NaN` | reject before any write; do **not** silently fall back |
| 14 | Concurrency | two claims race for the same desired serial | resolved under the existing playlist row-lock; exactly one wins, the other allocates `max + 1` |
| 15 | `sanitizeAdditiveVideo` | any additive create | **keeps** `serialNumber`; still drops `position`-derived and DB-computed fields |
| 16 | Record coherence (the bug) | after any additive create | `row.serialNumber` and the serial embedded in `row.summaryMd` **agree**. This is the assertion that fails today |

### A2 — `playlistIndex`

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 17 | Carry, don't derive | additive create | receiver's `playlistIndex` = the sender's value, **not** `slot.position + 1` |
| 18 | Absent on sender | sender has no `playlistIndex` | leave absent; the next ingest re-derives it (`pipeline.ts:322-334`) |

### A3 — Reconcile diverged serials (two-sided path)

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 19 | Equal | `local.serial === cloud.serial` | no rename, no writes — the common case |
| 20 | Differ → cloud renumbers | `local=3`, `cloud=7` | cloud moves to `3`; local untouched; both derive `base = 003_<slug>` |
| 21 | Target taken on cloud | cloud already has a *different* video at `3` | cloud takes `max(maxLocal, maxCloud) + 1`; **local still untouched**, so the two disagree — record it and report rather than renaming local |
| 22 | No derived blobs | video has only `summaryMd` | rename exactly one blob |
| 23 | With derived blobs | `models/<base>.json` + N `dig/<base>/*` | **all** move; a post-condition asserts nothing remains under the old base |
| 24 | Partial-rename failure | rename N of M blobs, then a backend failure | **abort without advancing the manifest baseline**, so a re-run heals. Never leave a row pointing at a base whose blobs are split across two prefixes |
| 25 | Destination occupied mid-move | a dig blob already exists at the new base | abort (behavior #3); do not overwrite paid content |
| 26 | Metadata/blob ordering | rename succeeds, metadata write fails | the row still points at the **old** base ⇒ orphaned-forward. Blobs move **last**, after the row is updated, or the move is verified before the row advances |
| 27 | Idempotent re-run | sync runs twice with no change between | second run is a no-op (#19) |

### Which faults abort vs are swallowed

| Fault | Abort or swallow | Why |
|---|---|---|
| `rename` → `failed` | **abort** the video, don't advance its baseline | a transient blip must not look like a completed reconcile |
| `rename` → `destination-exists` | **abort** | paid content at the destination |
| `rename` → `source-absent` for `summaryMd` | **abort** | the row advertises a blob that isn't there |
| `rename` → `source-absent` for a *dig* blob | **swallow + report** | dig is out of M2a sync scope; a missing dig is not corruption |
| metadata write failure | **abort**, baseline not advanced | matches the existing round-4 H1 rule (`sync-run.ts:228-234`) |

---

## Tasks

- [ ] **A0** Enumerate behaviors (this table) → Codex adversarial review of the table (>8 behaviors, multiple error paths ⇒ required)
- [ ] **A4** `rename` at the seam + 3 adapters (TDD; blocks A3)
- [ ] **A1** Adopt sender serial on additive create + `claim_video_slot` migration
- [ ] **A2** Stop clobbering `playlistIndex`; correct spec §4.1
- [ ] **A3** Reconcile diverged serials on the two-sided path
- [ ] **A5** Regression guard + mutation-check
- [ ] **A-review** Claude + Codex adversarial review, iterated to convergence
- [ ] **A6** Delete the vestigial `position` column (separable; may ship as its own PR)

## Files

`lib/storage/blob-store.ts` · `lib/storage/{supabase,local,testing}/*-blob-store.ts` ·
`lib/storage/metadata-store.ts` + both adapters · `lib/cloud-sync/sync-run.ts` ·
`lib/serial-migrate*.ts` (reuse) · new `supabase/migrations/00NN_serial_sync.sql` ·
`docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md` §4.1

## Verification

1. Unit: `npx jest blob-store cloud-sync serial`
2. Unit via `InMemoryBlobStore`: local serial 3 / cloud serial 7 → same `base` after reconcile, digs resolve
3. Integration (live Supabase stack, not in CI): extend `tests/integration/cloud-sync/e2e.int.test.ts` near `:520-542`
4. Dry run on real data: `npx ts-node scripts/backfill-serial-prefix.ts --folder <path>`
5. Gates: `npx tsc --noEmit`, `npm test -- --ci`, `python3 scripts/check-docs.py`, `python3 scripts/check-arch-findings.py`
