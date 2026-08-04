# Stable Blob Addressing — Design Spec

**Status:** **v1 DRAFT — not reviewed, not approved.** Written 2026-08-03 from the design discussion of
2026-08-01→03. Requires `grill-with-docs` terminology pass + dual adversarial review to convergence
before it becomes a plan. **Supersedes part of [ADR-0002](../../adr/0002-playlist-in-job-identity.md)
— see §12.**

**Roadmap:** not yet filed. Sequenced *behind* the merge of `fix/serial-coherence-sync` —
✅ **that precondition is now met** (PR #42, squash `f8703bc`, 2026-08-03).

**It now also closes a filed defect.** `docs/backlog.md` **#17** (fence the worker persist) was filed
open when #42 merged: a stale worker persist landing after an A3 relocation orphans paid dig blobs,
and only fencing closes it. §5.1 and §9 argue this design removes that class outright rather than
fencing it — the manifest collapses the race to one small row, and no relocation exists to race with.
**If that argument survives review, #17 should be solved here rather than fenced separately.** Weigh
it against the delay: #17 is live today.

**Goal:** make the blob-orphaning bug class **impossible** rather than guarded-against, by deriving
every blob address from values that never change, and moving the "which copy counts" decision into a
small, explicit, atomically-writable manifest.

---

## 1. The problem — one root cause, many symptoms

Every hard defect of the last three weeks reduces to a single sentence:

> **The blob address is derived from mutable data.**

`base = <serial>_<slug>` is the address of `<base>.md`, `models/<base>.json`,
`dig/<base>/<sectionId>.r<V>.md` and `<base>-dig-deeper.md`. **Both halves move.** `serialNumber` is
allocated per-replica (`max + 1`, scoped to one playlist); `slug` comes from a YouTube title that can
change between ingests. When either moves, every derived blob's address moves with it — but the blobs
do not, and nothing points at them any more.

Symptoms this produced, all already diagnosed:

| Symptom | Where |
|---|---|
| Cloud-sync silently orphaned paid dig/model blobs on serial divergence | `fix/serial-coherence-sync` (4 review rounds) |
| A re-summarize orphans every dig, because section `startSec` values are re-minted | **CITATION WAS WRONG** — `tests/lib/html-doc/section-identity-after-resummarize.test.ts` **does not exist** (checked 2026-08-03; no test matching `section-identity`/`resummariz` exists anywhere). The *claim* is plausible but is now **unverified** and must be proven — ideally by writing that test — before it is used as evidence for anything. |
| The same video in two playlists is summarized and **charged twice** | ADR-0002, accepted as a cost |
| Superseded blobs accumulate forever with no way to identify them | no GC exists anywhere (§8) |

The `fix/serial-coherence-sync` branch fixes the first symptom correctly. It is nonetheless **the last
fix under the wrong model**: it makes moving a mutable address safe, rather than removing the need to
move it.

**The reframe:** the address should be stable; **the filename is a rendering.** `videoId` is
YouTube-assigned and immutable. `serialNumber` and `slug` are *display attributes* — the serial exists
so a human can find a file in Obsidian, which is a presentation concern, not an identity one.

---

## 2. Terminology

New terms introduced by this spec. All must land in `CONTEXT.md`.

| Term | Definition |
|---|---|
| **Tenant** | The isolation boundary that owns blobs. **Today `tenantId == auth.uid()`** — one user, one tenant. Named separately so a future team/workspace becomes an RLS predicate change, not a re-keying of every object. |
| **Generation** | One production run of a paid artifact — a summarize run, or a dig run. Identified by an opaque, immutable `generationId`. Nothing in a generation is ever overwritten. |
| **Slot** | A *logical* artifact position for a video: `summary`, `model`, `dig:<sectionId>`, `digDeeper`, `pdf:<kind>`, `slide:<id>`. What a reader asks for. |
| **Manifest** | The per-video table mapping **slot → blob key**. The single source of truth for which copy is authoritative. |
| **Authoritative** | The blob a slot currently resolves to. A property of the manifest, never of the blob itself. |
| **Rendering** | A human-facing name derived from attributes (`003_alpha.md`), distinct from the address. Local filesystem only. |

Existing terms kept unchanged: `base`, `serialNumber`, `slug`, `principal`, `indexKey`.

---

## 3. What exists today (verified ground truth)

Load-bearing facts, each verified in-session on 2026-08-03. **Re-verify before approval.**

**Storage.** Supabase Storage, bucket `artifacts`, **private** (`0007_storage_and_rpcs.sql:4`). No
bucket-level size or MIME restriction is set in any migration. Object path is
`<ownerId>/<playlistKey>/<key>` (`supabase-blob-store.ts:17`). Only five operations are used —
`upload`, `download`, `remove`, `move`, `list`.

> **Answering "do we need S3?" — no.** Supabase Storage *is* S3-compatible object storage. The
> `<playlistKey>` segment is **our convention, not a platform constraint**: object stores have a flat
> keyspace and treat `/` purely as naming. Re-shaping the path is a pure code change — no new service,
> no infrastructure, no vendor migration.

**The one hard constraint.** Storage RLS is
`bucket_id = 'artifacts' and split_part(name,'/',1) = auth.uid()::text` (`0007:12-17`). **The first
path segment must equal the caller's uid.** Nothing else is checked — not the playlist segment, not
the extension, not the size.

**Blob inventory.** Nine kinds. The paid/free split is already written down and load-bearing at
`reconcile-serial.ts:64-80` and `sync-run.ts:120-124`:

| Kind | Key today | Paid? |
|---|---|---|
| Summary MD | `<base>.md` | **PAID** (Gemini) |
| Magazine model | `models/<base>.json` | **PAID** (Gemini) |
| Dig section | `dig/<base>/<sectionId>.r<V>.md` | **PAID** (Gemini) |
| Dig-deeper companion | `<base>-dig-deeper.md` | **PAID** |
| Slide asset | `assets/<videoId>/<sectionId>-<start>-<end>.jpg` | free of Gemini, but needs a video download + re-encode; classified a **source** kind |
| HTML | `htmls/<base>.html` | free (deterministic re-render) |
| PDF (cloud) | `pdfs/<base>.r<V>.<sha256[:16]>.pdf` | free |
| PDF (local) | `pdfs/<base>.pdf` | free |
| Staging | `_staging/<uuid>/<finalKey>` | transient |

**Video-id addressing already exists here.** Slide assets are keyed on `videoId`, not `base`
(`lib/dig/slides.ts:185-188`). This spec **generalizes an existing pattern**, it does not import one.

**Nothing models "which of several copies is current."** Every existing versioning mechanism either
makes the current version the only addressable key (dig `.r<V>`, PDF hash), overwrites in place (model
envelope), compares one stored value against a compile-time constant (`docVersion`,
`GENERATOR_VERSION`), or partitions a dedupe namespace (`job_version`). There is exactly one row per
`(playlist_id, video_id)` and one `artifacts.summaryMd` record on it.

**No team concept exists.** Grep for team|workspace|organization|org_id|shared_with|collaborat across
migrations and `lib/`: **zero hits**. The only sharing primitive is `share_tokens` (`0013`) — an
unauthenticated read-only capability URL that resolves to one `(owner, playlist, video)` and
re-asserts the owner at every hop. It **never creates a second owner**.

---

## 4. Addressing

```
<tenantId>/videos/<videoId>/<generationId>/summary.md
<tenantId>/videos/<videoId>/<generationId>/model.json
<tenantId>/videos/<videoId>/<generationId>/dig/<sectionId>.md
<tenantId>/videos/<videoId>/assets/<sectionId>-<start>-<end>.jpg
```

Four properties, each load-bearing:

**`<tenantId>` stays first** — the RLS predicate requires it. Today it is literally `auth.uid()`, so
the bytes are unchanged from the current layout and **the predicate needs no edit**. Naming it
`tenantId` is free forward-compatibility (§11).

**`<videoId>` replaces `<playlistKey>`** — this is what un-couples the address from the playlist, and
what makes cross-playlist sharing *possible* (§12). It is also what removes `serial` and `slug` from
the address entirely.

**`<generationId>` makes every write create rather than overwrite.** No blob is ever modified in
place, so no writer can destroy another's work, and no reader can observe a half-written artifact.

**Assets sit outside a generation, keyed on absolute video timestamps.** They already are today, and
they are independent of section structure — a frame at 120s is the same frame regardless of which
generation drew a section boundary near it. Keeping them generation-free avoids re-capturing video on
every regeneration.

### 4.1 What is a `generationId`? — **OPEN**

Three candidates, listed with their consequences:

| Option | Property | Cost |
|---|---|---|
| **UUID per run** | simplest; guaranteed unique; no coordination | no natural dedup — regenerating identical content stores it twice |
| **Timestamp + random** | sortable, aiding retention policy ("keep newest N") | same as above; clock skew across replicas |
| **Content hash** | identical content collapses automatically; already used for PDFs (`pdf-render-version.ts:22`) | the id is unknown until the content exists, so the write path must stage-then-address |

**Recommendation to review:** UUID per run for paid artifacts (a summarize/dig run is inherently
unique — it consumed money), content hash for free re-renders (HTML/PDF, where dedup is pure win and
the pattern already exists).

### 4.2 Section ids — TESTED 2026-08-03: **half true**, and the other half merges into §12

The claim was that generation-scoping **dissolves** the stable-section-identity problem rather than
depending on it. Tested against live code. The verdict splits cleanly, and the split matters.

**The addressing half — CONFIRMED.**
- `sectionId` *is* `startSec`, literally: `section-window.ts:58` returns
  `{ sectionId: startSec, startSec, endSec, … }`.
- `allocateSectionStarts` (`lib/summary-section-timestamps.ts:12`) guarantees **unique and strictly
  increasing** values within one allocation — every `out[i] >= prev + 1`, including under
  pathological input (fewer seconds than sections).

So within a generation, section ids are already unique and ordered. A dig scoped to its own
generation never needs an id that is stable *across* generations. **For blob addressing, the problem
does dissolve.**

**The job-identity half — DOES NOT DISSOLVE.** `section_id` is not only a blob coordinate; it is part
of the job dedupe key:

```
jobs_idem_active on jobs (owner_id, playlist_id, video_id, section_id, job_kind, job_version)
  where status in ('queued','active','completed')          -- 0009:11-13
```

**There is no generation dimension here.** Two generations whose sections happen to share a
`startSec` — likely, since `allocateSectionStarts` *keeps* a model-supplied timestamp when it fits —
are one job. Because the partial index includes `completed`, a finished dig for section 120 in
generation *abc* **suppresses** a dig for section 120 in generation *def*. Generation-scoping the
address does not touch that; it makes it *more* visible, because the two digs would now be
legitimately distinct artifacts that the queue still refuses to distinguish.

**Consequence for sequencing — two open questions collapse into one.** The residue of the old "B
slice" is not a separate stable-section-identity project; it is the **job-identity re-keying already
identified as the largest risk in §12** (open question 6). Both are the same question: *what tuple
identifies a unit of paid work?* Answer it once, in the ADR that supersedes 0002.

**Still open:** whether `generationId` joins `jobs_idem_active`, or `section_id` becomes
generation-qualified, or the dedupe window stops including `completed`. Each has a different blast
radius on the 1D spend-reservation FK, which anchors to this identity.

---

## 5. The manifest

The per-video mapping from **slot → blob key**. This is the only mutable state in the design.

```
video_artifacts
  tenant_id     uuid    not null
  video_id      text    not null
  slot          text    not null        -- 'summary' | 'model' | 'dig:120' | 'digDeeper' | ...
  blob_key      text    not null
  generation_id text    not null
  updated_at    timestamptz not null default now()
  primary key (tenant_id, video_id, slot)
```

A **table, not a jsonb column**, for one decisive reason: GC must ask *"select every referenced
blob_key"*, which is a query against a table and a full scan of jsonb otherwise.

RLS follows the house pattern exactly (`enable` + `force row level security`, a
`for all using/with check (tenant_id = auth.uid())` policy, an explicit grant, an index on the FK).

### 5.1 Why this answers the concurrency problem

This is the payoff, and it is the reason the design started.

Today, two writers race on **blobs and row fields simultaneously**: the worker's `persist_summary` and
sync's Class-A transfer both write `summaryMd` plus the whole Class-A scalar block, and separately
both write bytes to the same object key. Neither checks what it read. We traced two live interleavings
(worker vs sync lost update; dig job pinning a base that a relocation then deletes) and concluded that
the fix needed either locks — with an unbounded drain wait — or compare-and-swap on every write path.

Under this design:

- **Blobs never collide.** Different generations, different keys. Two writers *cannot* overwrite each
  other, so no blob-level protocol is needed at all.
- **The metadata race collapses to one small row.** Publishing means updating one manifest row. A
  conditional write (`update … where blob_key = <what I read>`, check affected rows) is then
  *trivially sufficient* — no locks, no leases, no draining, nobody waits.
- **Failure is never destructive.** A loser's blobs still exist, so a wrong pointer is temporary and a
  re-run repairs it. This is what makes "compensate after the cycle" — the user's instinct — actually
  sound: compensation only works if the cycle never destroys anything.

### 5.2 Sync becomes a manifest reconciliation

Sync stops moving bytes. It compares two manifests and produces one. Nothing is copied, nothing is
deleted, no address changes. Per-video, the result is a set of slot decisions.

---

## 6. Cross-generation mixing — the sharpest constraint

The design permits a manifest whose `summary` slot points at generation *def* while `dig:120` points
at generation *abc*. That flexibility is desirable — a dig is expensive and should survive a
regeneration where possible — but **it is not unconditionally safe.**

A dig is generated from a **section span** of a specific summary. A dig from *abc* is servable under a
summary from *def* only if its span still corresponds to a real section in *def*.

**Rule:** cross-generation attachment requires a **span overlap ratio** above a threshold (per the
2026-07-31 decision). Below it, the dig remains stored — never deleted — but is **not attached** to
the current summary and does not render.

**Arbitrary mixing is not safe; validated mixing is.** A wrong attachment silently mislabels paid
content, which is worse than showing none: the user cannot tell it is wrong.

**Open:** the threshold value; and what to do when a regeneration *merges* two sections, so two
predecessor digs both overlap one successor heavily. Options: attach both, keep the higher overlap, or
treat the ambiguity as grounds to leave unattached.

---

## 7. Local's role — hub-and-spoke

**Cloud is the content hub. Local is authoritative for naming, and holds the materialized
authoritative set.**

This resolves cleanly *because addressing and naming are now separate concerns:*

- **Cloud** stores every generation, addressed by id. Opaque, stable, never renamed.
- **Local** materializes only the authoritative set, named for humans (`003_alpha.md`) so Obsidian
  wiki-links and muscle memory keep working. `serialNumber` becomes purely a rendering input.
- The manifest is the mapping between them.

This also explains a real asymmetry already in the code: `LocalFsBlobStore` **ignores `Principal.id`
entirely** (`local-blob-store.ts:12`) — there is no owner segment on disk at all. Tenant is a
*cloud-only* coordinate. The current design pretends the two layouts are the same and pays for it.

**Open — offline local generation.** Local can produce content the cloud cannot (ADR-0005: the hosted
deployment never downloads YouTube video, so slide capture is local-only). Hub-and-spoke needs an
explicit upload-then-publish path so local-generated artifacts enter the hub as a generation like any
other. This must not become "local is a read-only cache."

### 7.1 The coupling being removed is already broken

Today the sender's `summaryMd` string is used verbatim as a key against the *receiver's* store
(`sync-run.ts:258, 284, 376-389`, `companionTransfer:455-470`). Three failures of that assumption are
already documented in-repo:

- The cloud **rejects** a `raw/…` local key — `assert-cloud-summary-md-key.ts:14` demands a single
  path component, while `reconcile-serial.ts:104-107` confirms the `raw/` layout is real and supported.
- Local `path.join` **normalizes** (`a//b` → `a/b`) where Supabase takes the key literally —
  called out at `pdf-render-version.ts:16-18` as collapsing cache identities on one backend only.
- Filenames may be NFD/NFC-mixed on disk and resolve via a normalization-tolerant fallback
  (`serial-migrate-exec.ts:30-45`); Storage keys are byte-exact.

**Decoupling is therefore a fix, not merely a refactor.**

---

## 8. Garbage collection

**GC is already required today — this design does not introduce the need, it introduces the
capability.**

There is no GC of superseded blobs anywhere. `loadDigForServe` lists `dig/<base>/` and filters on
`.r<DIG_GENERATOR_VERSION>.md` (`load-dig-for-serve.ts:33-35`); blobs from an older generator version
accumulate forever and are silently skipped at read time. Old-base blobs from a relocation are the
same. Without a manifest **nothing can tell you what is unreferenced**, so GC is currently impossible.

Design:

- **Mark and sweep** over `video_artifacts`. Anything not referenced is a candidate.
- **Grace period — mandatory.** A blob written but not yet published is unreferenced and must never be
  collected. This is the classic GC race; a minimum age (hours, not minutes) is the standard defense.
- **Retention — OPEN.** Keep authoritative only? Authoritative + last N? Keep all paid, GC only free
  re-renders? The last is attractive: paid artifacts are the ones users would mourn, and HTML/PDF
  regenerate for nothing.
- **Trigger — OPEN.** Worker job, scheduled sweep, or on-demand.

---

## 9. Concurrency scenarios — re-derived against this design

The process requires each gate to re-derive an inherited assumption. These are the exact interleavings
traced on 2026-08-02/03; each must be re-checked at review.

| Scenario | Today | Under this design |
|---|---|---|
| Worker `persist_summary` finishes while sync writes its Class-A block | **Lost update.** Same row fields, same blob key; whichever lands second wins, and a paid generation can be destroyed | Different generations ⇒ **no blob collision.** Both publish to the manifest; the conditional write makes the loser retry. No paid work lost |
| Dig job pins `base` at start, sync relocates during its Gemini call | Dig writes to a base the relocation **deleted** — orphaned, paid | No relocation exists. The dig publishes under its own generation |
| Two syncs (two machines, one account) | Unconditional writes interleave | One manifest row, conditional write, loser re-runs |
| Two teammates generate for one video | n/a (no teams) | Two generations, both retained; manifest picks one; neither is destroyed |

---

## 10. Migration

Every existing blob moves exactly once, from `<owner>/<playlist>/<base>.*` to the new layout.

`reconcileCloudBase` (`lib/cloud-sync/reconcile-serial.ts`, built on `fix/serial-coherence-sync`) is
**precisely** the machinery this needs: plan → copy with sources retained → verify → update metadata →
delete best-effort, with fail-closed refusals on ambiguity. It gets **used as the migration tool, then
retired**. This is the concrete reason to merge that branch before starting this work.

Local migration is a rename to the human-readable rendering, which
`lib/serial-migrate.ts` / `serial-migrate-exec.ts` already do (two-phase, dry-run default,
clobber-safe).

---

## 11. Tenancy and teams

`tenantId == auth.uid()` today. The segment is *named* for a future that does not exist yet, because
naming it is free now and re-keying every object later is not.

What real team support would additionally require — **explicitly out of scope, recorded so it is not
discovered late:**

- **Every RLS predicate converts** from a string comparison to a membership lookup —
  `split_part(name,'/',1) in (select team_id from team_members where user_id = auth.uid())` — on
  `storage.objects` *and* on `profiles`, `playlists`, `videos`, `jobs`, `usage_counters`. This changes
  isolation from "by construction" to "by a table that must be correct," and runs per access.
- **Who pays.** `spend_ledger`, `quota_allowance` and `serve_owner_budget` are per-owner, and the
  entire cost-guardrail system (1D, ADR-0004) keys on that identity.
- **Write-sharing is a different problem from read-sharing.** `share_tokens` already solves the latter
  and deliberately never creates a second owner.

---

## 12. Relationship to ADR-0002

[ADR-0002](../../adr/0002-playlist-in-job-identity.md) (accepted) **explicitly considered and
rejected** video-level shared summaries:

> *"Video-level shared summary (rejected). Generate a video's summary once and reference it from every
> playlist that contains it — cheaper (no duplicate Gemini spend). Rejected because it contradicts the
> just-merged 1C storage model: it would require shared blobs across index keys, a video→playlists
> membership table, and cross-index reference reads — a fundamental storage re-architecture."*

**The rejection was on cost, not correctness** — and that objection no longer holds, because the
re-architecture is now on the table for independent reasons (a live data-loss bug class, plus
duplicate charging). That is a legitimate basis for revisiting an ADR rather than silently
contradicting it.

**This spec therefore requires a superseding ADR**, which must budget for exactly what 0002 lists as
consequences:

- **`jobs` identity** — `jobs_idem_active` is `(owner_id, playlist_id, video_id, section_id, job_kind,
  job_version)`. Removing `playlist_id` re-keys the dedupe index; keeping it means the same video in
  two playlists is still charged twice, which forfeits the saving.
- **The 1D spend reservation FK** anchors to that identity and must be re-pointed.
- **1C storage** is the layout this spec changes.
- The composite FK `(playlist_id, owner_id) → playlists(id, owner_id)` exists as a **cross-tenant
  injection guard** (0002 Consequences). Any re-keying must preserve an equivalent guard.

**This is the single largest risk in the work.** It must be settled in the plan, not discovered during
implementation.

---

## 13. Out of scope

- Actual team/workspace support (§11) — only the naming hook is in scope.
- Changing what the summary or dig *contains*.
- Background/automatic sync.
- Any change to the Gemini prompts, cost caps, or the spend ledger's accounting rules.

---

## 14. Open questions — must be closed before a plan

1. **`generationId` form** — uuid, timestamp, or content hash, per artifact class (§4.1).
2. ~~**Does generation-scoping dissolve stable section identity?**~~ — **ANSWERED 2026-08-03 (§4.2):
   half. It dissolves the *addressing* half (confirmed: `sectionId == startSec`, and
   `allocateSectionStarts` is unique + strictly increasing within a generation). It does **not**
   dissolve the *job-identity* half — `jobs_idem_active` includes `section_id` with **no generation
   dimension**, and its partial index covers `completed`, so a finished dig suppresses the same
   `startSec` in a later generation. **The remainder is now folded into question 6**, which is the
   same question wearing a different hat: what tuple identifies a unit of paid work?
3. **Overlap threshold**, and the section-merge ambiguity (§6).
4. **Retention policy and GC trigger** (§8).
5. **Offline local generation** — the upload-then-publish path (§7).
6. **Cross-playlist dedup: in or out?** (§12) — determines whether `jobs` and the 1D reservation are
   touched. The spec is coherent either way; the saving only materializes if `playlist_id` leaves the
   job identity.
7. **Do the two seam-bypassing writers get fixed or scoped out?** `companion-doc.ts:448` writes
   dig-deeper markdown with raw `fs`; `slides.ts:221-230` prunes assets with `fs.readdirSync`/
   `unlinkSync`. Both touch blobs the manifest must track.

---

## 15. Verification

This spec is verified by review, not by tests. Before it becomes a plan:

- `grill-with-docs` terminology pass — *tenant, generation, slot, manifest, authoritative, rendering*
  are all new and must land in `CONTEXT.md`.
- Dual adversarial review (Codex + Claude, independent) **to convergence** — mandatory here: this
  touches schema, identity, and the money path.
- **Re-verify every fact in §3 against live code.** They were verified on 2026-08-03 and are
  load-bearing; a stale premise invalidates the design.
- Walk each row of §9 explicitly during review rather than accepting the table as written.
