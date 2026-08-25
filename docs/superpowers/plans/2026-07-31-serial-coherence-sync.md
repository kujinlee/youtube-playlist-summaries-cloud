# Serial coherence in cloud-sync — Implementation Plan

> **Anchor:** `cloud-sync` — **ADR:** 0002
> **Goal:** The same video has the same serial number on both replicas, so both derive the same blob address.

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

### A4 — `copy` at the BlobStore seam

> **Revised after Codex review** (`docs/reviews/task-A0-serial-coherence-behaviors-codex.md`,
> High #3 + Medium #10). The original design added `rename`. That is the **wrong primitive**:
> Supabase `move()` is copy+delete and non-atomic (`supabase-blob-store.ts:75`), and
> `fs.renameSync` is atomic per object but not across N objects. A multi-blob relocation must be
> **copy → verify → update metadata → delete sources (best-effort)**, so the source must survive
> until the metadata is coherent. A destructive rename encodes the unsafe ordering into the seam.
> We add **`copy`** and compose with the existing `delete`.

`copy` returns a **discriminated union** matching the existing `BlobRead` discipline. Reasons are
granular because a caller must never collapse "could not read" into "absent" — the conflation that
produced a Blocking, three Highs, and a live 6¢→12¢ double charge in the Stage 3 review.

```ts
export type CopyResult =
  | { ok: true; already: boolean }              // already=true ⇒ destination held identical bytes
  | { ok: false; reason: 'source-absent' }
  | { ok: false; reason: 'source-unreadable'; cause: unknown }
  | { ok: false; reason: 'destination-exists' }        // occupied by DIFFERENT bytes
  | { ok: false; reason: 'destination-unreadable'; cause: unknown }
  | { ok: false; reason: 'failed'; phase: 'write' | 'verify'; cause: unknown };
```

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Happy path | `copy(p,'a.md','b.md')`, `a` exists, `b` absent | `{ok:true, already:false}`; bytes at both keys — **source retained** |
| 2 | Source absent | `a.md` does not exist | `{ok:false, reason:'source-absent'}` — never a silent success |
| 3 | **Destination occupied, DIFFERENT bytes** | `b.md` holds other content | `{ok:false, reason:'destination-exists'}`; both untouched. Fail-closed — this is the promote divergence's shape, and overwriting destroys paid content |
| 3b | **Destination occupied, IDENTICAL bytes** | retry after a partial run | `{ok:true, already:true}` — continue. *Codex Medium #9: strict fail-closed here would deadlock every retry after a partial success, forever* |
| 4 | Backend failure | 5xx / network / RLS denial | `{ok:false, reason:'failed', phase, cause}` — `phase` prevents collapsing a write failure into a precondition failure |
| 4b | **Precondition unreadable** | source or destination probe fails transiently | `source-unreadable` / `destination-unreadable`, **never** `source-absent`. *Codex Medium #7* |
| 5 | Uniform across adapters | same call on local FS / Supabase / in-memory | identical result for identical state — no adapter-specific semantics (the finding-#2 rule) |
| 5b | **Supabase classifies via `tryGet`** | any Supabase `copy` | preflight uses `tryGet`, **not** `exists()`/`get()` (which swallow every failure into `null`, `supabase-blob-store.ts:27,59`), and **not** `promote()`'s destination-presence-means-success rule, which is the opposite of row 3. *Codex Medium #8* |
| 6 | Invalid key | leading `/`, `..` segment, or `\0` | throws via `assertLogicalKey` before any I/O |
| 7 | Same key | `from === to` after validation **and** logical normalization | `{ok:true, already:true}`, no I/O. *Codex Low #12: compare normalized forms, so `a/./b` cannot alias* |
| 8 | Owner scoping | any call | resolves under `<owner>/<indexKey>/` only; cannot cross principals |
| 8b | Verify-after-write | every successful copy | destination bytes are read back and compared before `{ok:true}` — a copy that cannot be proven is `failed:'verify'`, never success |

### A1 — Adopt the sender's serial on additive create

`claimVideoSlot(p, videoId, desiredSerial?)` — the new parameter is **optional at the call site but
its absence is meaningful**: "no preference, allocate one."

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 9 | Adopt when free | sender serial `S`; no receiver video holds `S` | receiver row gets `serialNumber = S`; `base` matches the sender's |
| 9a | **Local-only → cloud** (upload) | local sender has serial `S`, `summaryMd` base `S` | cloud claims `S` if free. If occupied by another video ⇒ **abort this video and report** (row 21). **Never** write row serial `K` alongside `summaryMd` base `S` — that is today's bug. *Codex High #6* |
| 9b | **Cloud-only → local** (hydrate) | cloud sender has serial `S`, `summaryMd` base `S` | local claims `S` if free. If occupied ⇒ **abort and report**; local is never renumbered, because these filenames are the user's Obsidian notes. *Codex High #6 — the directions are materially different and row 9 alone hid that* |
| 10 | Collision on additive | another receiver video already holds `S` | **abort this video, report, do not advance its baseline.** No row is written and no blob is copied, so nothing is orphaned |
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
| 18b | Slot position is storage ordering only | additive sync, sender `playlistIndex` present or absent | the claim may still allocate a DB `position`, but the synced record must preserve the sender's `playlistIndex` (or its absence). **Test asserts `slot.position` is never read for `playlistIndex`.** *Codex Low #11* |

### A3 — Reconcile diverged serials (two-sided path)

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 19 | Equal | `local.serial === cloud.serial` | no copy, no writes — the common case |
| 20 | Differ, target free → cloud renumbers | `local=3`, `cloud=7`, nothing on cloud holds `3` | cloud relocates to `3` via the row-26 protocol; local untouched; both derive `base = 003_<slug>` |
| 21 | **Target occupied → ABORT** | cloud already holds a *different* video at `3` | **abort this video: no row write, no blob copy, no baseline advance; report a serial collision.** *Codex Blocking #1 — the previous expectation ("cloud takes K, local stays 3") violated this plan's own invariant and guaranteed permanent divergence. Aborting is not merely cautious: it stops `transferClassA` writing the winner's key onto the loser, so **the orphaning cannot occur** for this video. Local is never renumbered, per the Obsidian-links constraint.* |
| 21b | **Swap / cycle** | `A: local=3,cloud=7` and `B: local=7,cloud=3` | every video in the cycle hits row 21 ⇒ **the whole cycle aborts**, reported. Per-video partial success is forbidden — no single "cloud renumbers" move makes a cycle coherent. *Codex Blocking #2* |
| 21c | **Corrections-unresolved override** | both sides hold MD and corrections conflict, so Class A is skipped (`sync-run.ts:608-614`) | serial reconciliation is **also** skipped — but the divergence is **reported**, not silent. Safe because that path performs no transfer, so nothing is orphaned; unsafe only if it were hidden. *Codex High #5 — reconciliation must not be invisible behind the Class-A copy decision* |
| 22 | No derived blobs | video has only `summaryMd` | copy exactly one blob |
| 23 | With derived blobs | `models/<base>.json` + N `dig/<base>/*` | **all known existing blobs are present at the new base before metadata advances**; old-base cleanup is best-effort *after* metadata is verified. Steady state has no old-base blobs, but a cleanup failure reports and must never make row/base incoherent. *Codex Medium #10 — the old "nothing remains under the old base" post-condition contradicted keeping sources until metadata is safe* |
| 24 | Failure **before** metadata advances | copy N of M blobs, then a backend failure | abort; baseline not advanced; **sources still intact and still serving the current row.** With copy-first there is no destructive half-state to roll back. *Codex High #4* |
| 24b | Failure **after** metadata advances | metadata points at the new base, source cleanup fails | retry-cleanup only, **not** data loss: every blob already exists at the new base (row 23 verified it). Re-run deletes the leftovers |
| 25 | Destination occupied mid-move | a dig blob already exists at the new base | identical bytes ⇒ continue (row 3b); different bytes ⇒ abort (row 3). Never overwrite paid content |
| 26 | **Metadata/blob ordering — chosen protocol** | any serial/base change | **copy all destination blobs (sources retained) → verify destination bytes → update metadata → delete old blobs best-effort.** Any failure before the metadata write leaves old blobs intact and the baseline unadvanced; any failure after it is cleanup, not loss. *Codex High #3 — the previous row offered two alternatives and picked neither, and the "metadata first" variant is unsafe under non-atomic multi-object moves* |
| 27 | Idempotent re-run | sync runs twice with no change between | second run is a no-op (#19); a re-run after a partial copy resumes via row 3b rather than deadlocking |

### Which faults abort vs are swallowed

| Fault | Abort or swallow | Why |
|---|---|---|
| `copy` → `failed` (any phase) | **abort** the video, don't advance its baseline | a transient blip must not look like a completed reconcile |
| `copy` → `source-unreadable` / `destination-unreadable` | **abort** | fail-closed: an unprovable precondition is not permission to move paid content |
| `copy` → `destination-exists` (different bytes) | **abort** | paid content at the destination |
| `copy` → `{ok:true, already:true}` | **continue** | proven-identical bytes; this is what makes a retry after a partial run resumable |
| `copy` → `source-absent` for `summaryMd` | **abort** | the row advertises a blob that isn't there |
| `copy` → `source-absent` for a *dig* blob | **swallow + report** | dig is out of M2a sync scope; a missing dig is not corruption |
| metadata write failure | **abort**, baseline not advanced | matches the existing round-4 H1 rule (`sync-run.ts:228-234`) |
| old-blob cleanup failure (post-metadata) | **swallow + report** | row 24b — every blob already verified at the new base, so this is litter, not loss |
| serial collision (rows 21 / 21b) | **abort + report**, re-reported every run | visible divergence beats a silent half-fix |

---

## Tasks

- [x] **A0** Enumerate behaviors (this table) → **Codex adversarial review done**
      (`docs/reviews/task-A0-serial-coherence-behaviors-codex.md`, model `gpt-5.5`; the wrapper
      fell through three HTTP-400 models to reach it). 2 Blocking, 4 High, 4 Medium, 2 Low —
      **all adopted**, including two that overturned my own design:
      *Blocking #1* row 21 encoded permanent divergence and would have shipped as a passing test;
      *High #3 + Medium #10* showed `rename` is the wrong primitive, so A4 became `copy`.
- [ ] **A4** `copy` at the seam + 3 adapters (TDD; blocks A3)
- [ ] **A1** Adopt sender serial on additive create + `claim_video_slot` migration
- [ ] **A2** Stop clobbering `playlistIndex`; correct spec §4.1
- [ ] **A3** Reconcile diverged serials on the two-sided path
- [ ] **A5** Regression guard + mutation-check
- [ ] **A-review** Claude + Codex adversarial review, iterated to convergence
- [ ] **A6** Delete the vestigial `position` column (separable; may ship as its own PR)

## Files

`lib/storage/blob-store.ts` (add `copy` + `CopyResult`) · `lib/storage/{supabase,local,testing}/*-blob-store.ts` ·
`lib/storage/metadata-store.ts` + both adapters · `lib/cloud-sync/sync-run.ts` ·
`lib/serial-migrate*.ts` (reuse) · new `supabase/migrations/00NN_serial_sync.sql` ·
`docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md` §4.1

## Verification

1. Unit: `npx jest blob-store cloud-sync serial`
2. Unit via `InMemoryBlobStore`: local serial 3 / cloud serial 7 → same `base` after reconcile, digs resolve
3. Integration (live Supabase stack, not in CI): extend `tests/integration/cloud-sync/e2e.int.test.ts` near `:520-542`
4. Dry run on real data: `npx ts-node scripts/backfill-serial-prefix.ts --folder <path>`
5. Gates: `npx tsc --noEmit`, `npm test -- --ci`, `python3 scripts/check-docs.py`, `python3 scripts/check-arch-findings.py`
