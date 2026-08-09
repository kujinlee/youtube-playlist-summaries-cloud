# Stable Blob Addressing — Design Spec

**Status:** **v1 DRAFT — not reviewed, not approved.** Written 2026-08-03 from the design discussion of
2026-08-01→03. Requires `grill-with-docs` terminology pass + dual adversarial review to convergence
before it becomes a plan. **Supersedes part of [ADR-0002](../../adr/0002-playlist-in-job-identity.md)
— see §12.**

**Roadmap:** not yet filed. Sequenced *behind* the merge of `fix/serial-coherence-sync` —
✅ **that precondition is now met** (PR #42, squash `f8703bc`, 2026-08-03).

**It now also closes a filed defect.** `docs/backlog.md` **#17** (fence the worker persist) was filed
open when #42 merged: a stale worker persist landing after an A3 relocation orphans paid dig blobs,
and only fencing closes it. §5.1.1 and §9 argue this design removes that class outright rather than
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
| A re-summarize orphans a dig **when the heading is reworded too** — see the corrected wording below | `tests/lib/html-doc/section-identity-after-resummarize.test.ts` (5 characterization tests, all passing) |
| The same video in two playlists is summarized and **charged twice** | ADR-0002, accepted as a cost |
| Superseded blobs accumulate forever with no way to identify them | no GC exists anywhere (§8) |

> **Correction, 2026-08-04 — the second row was overstated twice, in opposite directions.**
> An earlier draft claimed a re-summarize orphans *every* dig. A later edit then declared the cited
> test non-existent and downgraded the claim to unverified — checked against `master`, where the file
> genuinely was not, because it sat unmerged on PR #41. Both are now wrong: the test exists
> (merged `2ea5b0d`) and the truth is narrower than the original claim.
>
> **A changed `startSec` alone does NOT orphan a dig.** `mergeDigDoc` matches in two steps —
> `sectionId === startSec`, then an exact **title** fallback — and the fallback rescues it
> (test: *"startSec changed, titles unchanged → step 1 FAILS, rescued only by the TITLE fallback"*).
> Orphaning needs **both** to move (test: *"startSec AND title changed → dug content ORPHANS off its
> section"*), which a re-summarize is free to do since nothing constrains the heading.
>
> That makes the section **title** a load-bearing identity anchor today — the thing standing between
> `startSec` churn and mass orphaning. §4.2 treats it as the third identity dimension.

The `fix/serial-coherence-sync` branch fixes the first symptom correctly. It is nonetheless **the last
fix under the wrong model**: it makes moving a mutable address safe, rather than removing the need to
move it.

**The reframe:** the address should be stable; **the filename is a display name.** `videoId` is
YouTube-assigned and immutable. `serialNumber` and `slug` are *display attributes* — the serial exists
so a human can find a file in Obsidian, which is a presentation concern, not an identity one.

---

## 2. Terminology

New terms introduced by this spec. All must land in `CONTEXT.md`.

| Term | Definition |
|---|---|
| **Tenant** | *Existing term, unchanged.* The per-user isolation boundary the RLS enforces — this app is already multi-tenant. **Not** the name of the path segment: see **Workspace**. |
| **Workspace** | The immutable container a video's blobs are addressed under, and the first path segment. **Its id is opaque — one workspace per user in this slice.** ⟳ *Round 2 correction:* the id **may** coincide with a uid (migrated workspaces are deliberately seeded that way, §5.0.2); what is forbidden is any **predicate** that compares the path segment to `auth.uid()`. A **user-chosen grouping of playlists** — one per playlist, one per user, or anything between (§11.0). Its id **never changes**; what changes is who may access it. Chosen over *tenant* (already means the per-user boundary), *team* and *owner* (both name **who may access**, which is exactly what changes). The revocability that matters comes from `workspaces.owner_id`, not from the id's shape (§11.2). |
| **Generation** | One production run that yields a **new body** — a summarize run, a dig run, a corrections re-application, or a re-render at a bumped format version — **and everything that run produced: for a summary, both the body (the blob) and the card (the scalars), inseparably** (§5.2, decided 2026-08-05). Identified by an opaque, immutable `generationId`. Nothing in a generation is ever overwritten. ⟳ *Invariant evaluation 2026-08-06: this said "a paid artifact", which is too narrow — a corrections re-application (backlog #23) produces new bytes with **no Gemini call**. **Paid is an attribute of the run, not part of the definition**, and it matters: §8's retention keys on paid-vs-free, so the old wording would have retained free re-renders for 90 days.* |
| **Card** | The **document facts** a summarize run produces alongside the body: `tldr`, `takeaways`, `docVersion`, `mdGeneratedAt`, `processedAt`, `mdCorrectionsHash`. An attribute **of the generation**, never of the video — that distinction is the whole of Q8. **Does NOT include the video judgments** (`ratings`, `overallScore`, `videoType`, `audience`, `language`, `tags`): §5.2.1 keeps those on the video, because they describe the *video*, which a regeneration did not change. ⟳ Corrected in the terminology pass — the first draft of this row listed all twelve scalars and contradicted §5.2.1. |
| **Slot** | A *logical* artifact position for a video: `summary`, `model`, `dig:<sectionId>`, `digDeeper`, `pdf:<kind>`. What a reader asks for. ⟳ *Cross-derivation pass: `slide:<id>` was REMOVED — §8 classifies assets as **sources**, which live outside the manifest by design, so there is no slide slot.* Distinct from a **video slot** (`claim_video_slot`), a video's reserved position in a playlist. |
| **Artifact manifest** | The per-video table mapping **slot → blob key**. The single source of truth for which copy is authoritative. ⟳ **Qualified in round 1** — `Manifest` was ALREADY taken: `lib/cloud-sync/manifest.ts:6` is the per-playlist `.cloud-sync-manifest.json` **sync baseline**, with `readManifest`/`writeVideoBaseline`/`manifestPath` and consumers across `sync-run.ts`, `companion.ts` and 7 test files. This was a **fifth** vocabulary collision the terminology pass missed — and it missed it in the one section (§5.3) whose subject is sync, where the unqualified word is genuinely ambiguous. Say **artifact manifest** or **sync baseline**; never a bare *manifest*. |
| **Authoritative** | The blob a slot currently resolves to. A property of the manifest, never of the blob itself. |
| **Display name** | A human-facing filename derived from attributes (`003_alpha.md`), distinct from the address. Local filesystem only. ⟳ **Renamed from "Rendering" in the terminology pass** — `render` is an established term here for *summary → HTML/PDF* (`renderMagazineHtml`, `PDF_RENDER_VERSION`, and the whole source-vs-derived split in `CONTEXT.md`). Reusing it for a filename would overload the word that carries the artifact taxonomy. |

Existing terms kept unchanged: `base`, `serialNumber`, `slug`, `principal`, `indexKey`.

---

## 3. What exists today (verified ground truth)

Load-bearing facts, each verified in-session on 2026-08-03, and **re-verified against live code on
2026-08-05** (§15's re-verify gate). **13 survived; 3 needed correction, all marked ⟳ below.**

> **What the drift was, and why it is worth a sentence.** Every correction has one cause: two PRs
> merged *after* the original verification — #45 (the in-flight-job guard) and #38 (`copy` at the
> BlobStore seam) — inserted code **above** the cited lines. Not one cited *fact* was wrong; three
> cited *locations* were. That is the failure mode a line-number citation has and a symbol name does
> not, so the corrections below cite the **function**, with the line range as a hint.

**Storage.** Supabase Storage, bucket `artifacts`, **private** (`0007_storage_and_rpcs.sql:4`). No
bucket-level size or MIME restriction is set in any migration. Object path is
`<ownerId>/<playlistKey>/<key>` (`supabase-blob-store.ts:17`, `objectKey`). Only five **Storage API**
operations are used — `upload`, `download`, `remove`, `move`, `list`.

> **⟳ Corrected 2026-08-05 — the *seam* has six operations, the *API* still has five, and the gap is
> evidence for this design.** `BlobStore` gained `copy()` (PR #38), and it is deliberately **not**
> built on the bucket's native `copy`/`move`: `SupabaseBlobStore.copy` delegates to the shared
> `copyBlob`, which reads through `tryGet` so the outcome can be classified
> (`supabase-blob-store.ts:68-81`, `blob-store.ts:34-45`). The seam's own doc comment gives the
> reason — *"a multi-blob relocation must be copy → verify → update metadata → delete sources"*, and a
> destructive rename "would bake an unrecoverable ordering into the seam."
>
> **Read that as a finding, not a footnote.** The codebase has already concluded, independently and
> under review, that **relocating a blob address is not a safe primitive**. This spec's §1 says the
> same thing one level up: stop needing to relocate at all.

> **Answering "do we need S3?" — no.** Supabase Storage *is* S3-compatible object storage. The
> `<playlistKey>` segment is **our convention, not a platform constraint**: object stores have a flat
> keyspace and treat `/` purely as naming. Re-shaping the path is a pure code change — no new service,
> no infrastructure, no vendor migration.

**The one hard constraint.** Storage RLS is
`bucket_id = 'artifacts' and split_part(name,'/',1) = auth.uid()::text`
(`0007:12-15`, policy `artifacts_owner_rw` — ⟳ was cited as `12-17`, then miscorrected to `13-16`; round-1 review caught that the *correction* was off by one at both ends). **The first
path segment must equal the caller's uid.** Nothing else is checked — not the playlist segment, not
the extension, not the size.

**Two properties of that predicate are load-bearing and must survive any rewrite** (measured
2026-08-04 against the local stack):

- **It compares text to text.** `split_part` returns whatever text is before the first slash, for any
  name. Casting that segment — `split_part(name,'/',1)::uuid` — raises
  `invalid input syntax for type uuid` on a **single** malformed object name, and inside a policy an
  error does not deny one row, it **fails the whole query for everyone**. Casting the *uid* instead
  (`= auth.uid()::text`) keeps the predicate total. This looks like a style detail and is not.
- **It fails closed on every degenerate input.** A leading slash or an empty name yields `''`, which
  matches no uid; a NULL name, or an unsigned caller whose `auth.uid()` is NULL, yields NULL, and RLS
  requires TRUE. Anonymous isolation therefore needs no separate rule (`0007:9-12` says exactly this).

**The tenant does not have to live in the path.** `storage.objects` also exposes `owner uuid`,
`owner_id text` and `user_metadata jsonb` — any of which a policy can read. This matters only as a
future escape hatch (§11), not for this design, and it is **not usable as-is**: `owner_id` is
populated on **390 of 973** objects in the local stack, because `service_role` writes leave it NULL.
Where it is set it equals path segment 1 in **390/390** cases, so it is backfillable.

**Blob inventory.** Nine kinds — every key shape below re-confirmed by grep on 2026-08-05. The
paid/free split is already written down and load-bearing at **`reconcile-serial.ts:paidKeysUnder`**
(≈88-103) and **`sync-run.ts` behavior #3, "money-safe"** (≈125-128) — ⟳ these were cited as
`reconcile-serial.ts:64-80` and `sync-run.ts:120-124`, which PR #45 pushed down:

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
<workspaceId>/videos/<videoId>/<generationId>/summary.md
<workspaceId>/videos/<videoId>/<generationId>/model.json
<workspaceId>/videos/<videoId>/<generationId>/dig/<sectionId>.md
```

Four properties, each load-bearing:

**`<workspaceId>` stays first** — the RLS predicate requires it.

> **⟳ CORRECTED IN ROUND 1 (Blocking B3).** This previously read *"today it is literally `auth.uid()`, so
> the bytes are unchanged and the predicate needs no edit"* — which contradicted §11.2 ("the predicate
> changes on day one") and §5.1 (whose manifest RLS `workspace_id = auth.uid()` denies every row the
> instant the id stops being a uid). Three sections said three things about one predicate.
>
> **Settled 2026-08-06 by the middle slice (§5.0): the segment is an independent workspace UUID, and
> the storage predicate changes now** — to `workspace_readable(split_part(name,'/',1))`, a single
> `security definer` function, with no teams, no ACL and no roles. Bytes are unchanged in *shape*;
> the value in segment 1 is a workspace id rather than a uid, which is precisely the point.

> **The one deliberate exception to this spec's own thesis — named, not hidden.** Everything else in
> this template is immutable, but **ownership is not**: content can change hands. So `<workspaceId>` is
> a mutable value in the address, which is the very mistake §1 exists to eliminate, one level up.
> Accepted because **teams are not planned** (user decision, 2026-08-04) and no ownership-transfer
> feature exists, so the value is immutable *in practice*. The consequence, spelled out: **if content
> ever moves between tenants, its blobs must move with it.** §11 says what to do instead if that day
> comes — the answer is not "re-key everything."

**`<videoId>` replaces `<playlistKey>`** — this is what un-couples the address from the playlist, and
what makes cross-playlist sharing *possible* (§12). It is also what removes `serial` and `slug` from
the address entirely.

> **⚠ Consequence found 2026-08-05, and it is bigger than it looks: this breaks `Principal.indexKey`,
> and with it playlist hard-delete.**
>
> Every Supabase blob operation composes its root as `${p.id}/${p.indexKey}/…` — `objectKey` (`:15-18`),
> `list` (`:122-125`), and `deletePrefix` (`:110-113`). `indexKey` **is** the playlist segment. Remove
> the segment and that composition addresses nothing.
>
> The sharpest instance is **playlist hard-delete**, which is a *prefix sweep*:
> `DELETE /api/playlists/[id]` calls `blobStore.deletePrefix(principal, '')` (`route.ts:79`) and
> relies entirely on the playlist being a path component to scope the blast radius. Under the new
> template both obvious ports are wrong:
>
> - keep `${p.id}/${p.indexKey}/` → matches **nothing**; every blob survives the delete, and the route
>   already swallows blob-cleanup failures as *"invisible orphans accepted"* (`route.ts:80-82`), so it
>   fails **silently** and returns 200;
> - simplify to `${p.id}/` → deletes **the entire tenant**, every playlist the user owns.
>
> **So deletion must become manifest-driven enumeration, not a prefix sweep** — which is coherent with
> the rest of the design (the manifest is the only thing that knows what a video owns once the path
> stops encoding it), but it is *new work this spec has not costed*, it sits on the delete path, and
> one of its failure modes is silent. Treat as a first-class task at plan time, not a migration detail.
>
> **Where this bites twice:** §8's rule that an explicit delete outranks retention depends on delete
> actually collecting the blobs. If delete degrades to a silent no-op, the 90-day window silently
> becomes forever, for content a user asked to destroy.

**`<generationId>` makes every write create rather than overwrite.** No blob is ever modified in
place, so no writer can destroy another's work, and no reader can observe a half-written artifact.

> **⟳ ROUND 3 (Blocking A-6) — THE ASSET LINE IS REMOVED. No slide asset has ever been written to the
> Supabase bucket, so three rounds designed keys, retention, GC and pruning for an artifact class with
> zero cloud instances.** Verified three ways: the cloud dig path emits `slides: []` and rewrites every
> slide token to a caption-only placeholder (`parse-dig-section-blob.ts:7-17`); `captureSlideFrame`
> shells out to `ffmpeg`, which ADR-0005 deliberately keeps out of the image; and `lib/cloud-sync/`
> contains **zero** references to assets, so sync does not carry them either — it nulls `digDeeperMd` on
> additive create precisely so a receiver never advertises blobs it did not copy.
>
> **Assets are a LOCAL-BACKEND concern, and this spec now says nothing about them.** Note what that
> means for the rules: rule 15 ("assets are sources, outside the manifest, never age-swept, removed by
> explicit delete") described a backend that has **no manifest, no generations, no sweeper and no
> playlist delete**. Every asset finding across three rounds — round-1 H6, round-2 N-B1/N-H9, Codex H3
> and BLOCKING[15,18], my own A2 — is **withdrawn**, not fixed.
>
> **Invalidation condition (ADR-0005 amendment, 2026-08-06):** this holds only while (a) slide capture
> stays off the hosted path, and (b) sync does not copy assets. Uploading locally-captured frames to the
> cloud was proposed and **refused** — it makes our backend a redistribution pipeline for
> YouTube-derived pixels, a different ToS surface from capture. If either fact changes, this section
> reopens in full.
>
> *(Superseded text kept for the trail:)* **Assets sit outside a generation, keyed on absolute video timestamps.** They already are today, and
they are independent of section structure — a frame at 120s is the same frame regardless of which
generation drew a section boundary near it. Keeping them generation-free avoids re-capturing video on
every regeneration.

### 4.0 Every key shape, and what the sweeper does with it — ⟳ ROUND 4 (J1-5, Codex #17; round 3's A3, unfixed for three rounds)

The three-line template above covers **three** of the nine kinds §3 inventories. §8's sweeper decides
whether bytes live or die from the key alone (rule 17), so for the other six that decision was
undefined — and *undefined* on a delete path does not mean "nothing happens", it means whatever the
implementer guesses. This table is the whole domain.

| Key shape | Class | Manifest row? | Sweeper |
|---|---|---|---|
| `<ws>/videos/<vid>/<gen>/summary.md` | paid | `slot='summary'` | keep while any generation row references it; §8's 90-day clock after |
| `<ws>/videos/<vid>/<gen>/model.json` | paid | `slot='model'` | same |
| `<ws>/videos/<vid>/<gen>/dig/<sectionId>.md` | paid | `slot='dig:<sectionId>'` | same, and a **detached** dig keeps its row (§6.2) — the row makes it enumerable and non-orphaned, *not* immortal: its 90-day clock runs from `detached_at` (⟳ round 6) |
| `<ws>/videos/<vid>/<gen>/dig-deeper.md` | paid | `slot='digDeeper'` | same |
| `<ws>/videos/<vid>/renders/<name>.html` | free | `slot='html'` | delete when not current; **never** retained — it re-renders |
| `<ws>/videos/<vid>/renders/<name>.pdf` | free | `slot='pdf:<kind>'` | same |
| `_staging/<uuid>/<finalKey>` | transient | **none, ever** | delete when older than the write timeout. **Not** "unreferenced ⇒ garbage" — see §5.1.1's containment table |
| Anything else | **unknown** | — | **fail closed: never delete, and report.** |
| *(Slide assets)* | *local backend only* | *n/a* | *out of scope — round 3 A-6; no cloud instance exists* |

**The last two rows are the ones that matter.**

*Fail closed* is not a default chosen for tidiness. This classifier's two error directions are not
symmetric: misclassifying garbage as precious wastes storage measured in cents, while misclassifying
precious as garbage destroys paid, unreproducible bytes. An unknown key is exactly what a *legacy* key
looks like during §10's migration, and what a *future* key looks like after someone adds a kind and
forgets this table — so the unknown case is not hypothetical, it is the steady state during every
migration. **Report, never delete**, and treat a non-empty unknown set as a migration that is not
finished rather than as a sweep that found nothing.

*Staging* earns its own row because it is the one shape where "no manifest row" is **correct and
permanent**. A sweeper written from rule 17 alone deletes a live staging blob mid-promote — a
data-loss bug whose window is milliseconds and whose reproduction is a race.

**Why this went unfixed for three rounds, which is the more useful finding.** It was raised in round 1
(M5), not fixed; round 2 did not re-raise it; round 3 recorded it *specifically so it would not be
lost a third time* (A3) — and it was, because recording a finding is not fixing it and the two look
identical in a review document. The countermeasure is not more diligence: it is that a rule with an
enumerable domain should be written **as** the enumeration, where a missing row is visible, rather
than as a sentence that quietly quantifies over a set nobody listed.

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

### 4.2.1 A THIRD identity dimension — the section title (added 2026-08-04)

The split above named two dimensions. There are **three**, and the missing one is the only anchor
that is not a number:

| Where identity is decided | Anchored on | File |
|---|---|---|
| Blob address (`dig/<base>/<sectionId>…`) | `startSec` | `dig-blob-key.ts`, `enqueue-dig-core.ts:34` |
| Job dedupe (`jobs_idem_active`) | `section_id` | `0009:11-13` |
| **Dig→section attach, step-2 fallback** | **exact title string** | `dig-merge.ts:81` |
| **Magazine-model gist trust** | **exact title array, positional** | `sameTitles`, `read-model.ts:12` |

Two of the four are the section **title** — a string the LLM rewrites freely on every re-summarize,
with nothing constraining it. The characterization tests pin what that costs today:

- a single reworded heading **drops the magazine gists for every section**, not just the edited one —
  `sameTitles` is positional and all-or-nothing;
- titles held constant while the prose changes serves **stale gists as fresh** (that one is
  deliberate: `fixSummary`'s prompt pins headings precisely so this holds).

**Does generation-scoping dissolve this one? Yes — but only because §6 exists.** Within a generation,
a dig and its summary come from the same run, so `sectionId` matches exactly and the title fallback
is never reached. Titles stop being identity and go back to being text.

The fallback exists *only* to survive drift between a dig and a summary produced at different times —
and that is exactly the cross-generation case §6 governs. So §6's **span-overlap rule is not optional
decoration: it is the replacement for title matching.** Weaken or drop it and the design has no
cross-generation attach rule at all, which is strictly worse than today, because today at least the
title fallback catches the common case.

The same argument retires `sameTitles`: a model envelope stored under its generation is matched by
`generationId`, not by comparing heading strings.

---

## 5. The workspace and the artifact manifest

> # ⚠ THE DDL IN THIS SECTION IS NO LONGER THE ARTIFACT.
>
> **Executable schema:** [`2026-08-03-stable-blob-addressing/schema/`](2026-08-03-stable-blob-addressing/schema/)
> **Verify:** `./docs/superpowers/specs/2026-08-03-stable-blob-addressing/verify-schema.sh`
> — runs every statement against the **live local Postgres**, against the real populated tables
> (5312 profiles / 4368 playlists / 2902 videos / 101 jobs), inside a transaction that always rolls
> back, then executes behavioural assertions. Exit 0 = verified.
>
> **Why this moved out of prose.** Roughly half of round 4's Blocking findings were *"the SQL in this
> prose block does not execute"* — a physical constraint fixed at one site and recurring at a sibling,
> four rounds running, plus fixes that were **written in prose and never reached the DDL** (three
> columns existed in exactly one sentence each and in no table). Those are **compile errors being
> found by human review**, which is the most expensive possible way to find them.
>
> **It paid immediately.** The first run failed with `column "workspace_id" of relation "playlists"
> contains null values` — the seed ran *after* the backfills that read it, so `UPDATE 0`. An ordering
> defect that four review rounds and a cross-derivation pass had not caught, found in one execution.
>
> **And the assertions catch what mere creation does not.** Round 3's slot guard *created cleanly* and
> then accepted `slot='html', kind='dig'`. `05_assert.sql` now proves each guard **rejects**: an
> incomplete card, a NULL card, a mismatched slot/kind, a paid kind with no generation, and an
> unleased `pending`. Plus that format outranks recency, and that a user typing a correction **does not
> empty the slot** — round 4's A-2 floor, as an executable test rather than a promise.
>
> **§5.1 has been reconciled to the schema** (2026-08-06): the manifest is **append-only** with
> `current` as a **view** (round 4 J2-1 / Codex #6), and `pending` is **leased** (Codex #5). Reconciling
> it meant re-reading the schema, which is how §5.1.3's defect was found — so the reconciliation paid
> for itself before it finished. **Where any remaining prose and the schema disagree, the schema is the
> design**, and that is a standing rule rather than a transitional note.


> **⟳ ROUND 3 (A-5, A-7, A-9, A-10) — SCOPE, stated once because four findings share this root: every
> mechanism in §5 is a POSTGRES SCHEMA PROPERTY, and only one of the two backends has that schema.**
> The local backend is a filesystem (`LocalFsBlobStore` ignores `Principal.id` entirely). It has no
> artifact manifest, no `video_generations`, no sweeper, and no playlist-delete route. So *"a generation
> is body + card inseparably"* (rule 12) and *"`current` is derived"* (rule 13) are **cloud invariants**,
> not system-wide ones.
>
> **This spec designs the CLOUD side. Local keeps its display-name layout (§7's hub-and-spoke), and
> §5.3 is where the two must meet** — which is why §5.3 being three sentences is itself a finding (A-5).
> Sync cannot reconcile generation *sets* when one side stores no generations; it has to translate.
> **Naming the asymmetry is in scope for this spec; resolving it is the sync slice's job**, and that
> slice cannot be planned until this sentence exists.

### 5.0 The workspace table — ⟳ ADDED IN ROUND 1 (Blocking B2), scope settled 2026-08-06

Round 1 found that `<workspaceId>` was the first segment of **every** blob key and the partition key of
both new tables, while **nothing anywhere produced one** — no table, no column, no RPC. A plan could
not have been written.

**Decision (user, 2026-08-06): the middle slice. Ship the table now, one workspace per user, with an
opaque UUID. Defer everything else about teams.**

```sql
create table workspaces (
  id       uuid primary key,   -- NO default: §5.0.2 supplies it, and in this slice it always
                               -- EQUALS owner_id. Opaque regardless — nothing may branch on that.
  owner_id uuid not null references profiles(id) on delete cascade,
  created_at timestamptz not null default now(),
  unique (owner_id),                    -- one workspace per user IS the rule for this slice
  unique (id, owner_id)                 -- round 3 B-6: required as the FK target for the Q6
                                        -- cross-tenant guard. Same shape as `playlists`
                                        -- `unique (id, owner_id)` (0001:18), and the omission was
                                        -- round-2 C2 recurring verbatim inside the fix that closed Q6
);
```

**⟳ ROUND 2 (Blocking) — the migration must be three-phase; the one-liner I wrote does not run.**
`alter table playlists add column workspace_id uuid not null references workspaces(id)` aborts on any
populated table (`ERROR: column "workspace_id" contains null values`), and the ordering problem is
deeper than a default: every existing **owner** needs a workspace row before any playlist can reference
one, and `handle_new_user()` only fires for *future* users.

```sql
-- 1. one workspace per EXISTING profile (the trigger covers only future users)
insert into workspaces (owner_id) select id from profiles;
-- 2. nullable, then backfill from the owner
alter table playlists add column workspace_id uuid references workspaces(id);
update playlists p set workspace_id = w.id from workspaces w where w.owner_id = p.owner_id;
-- 3. only now
alter table playlists alter column workspace_id set not null;
```

> **This is a SCHEMA migration and §10 covers only the BLOB migration.** Both are mandatory and they
> are separate steps; §10 must not be read as covering this.

**Provisioning for new users** goes in the existing `handle_new_user()` trigger (`0003:2-11`), which
already creates the `profiles` row on `auth.users` insert.

> **⟳ ROUND 2 (Medium, Codex) — and it must be SCHEMA-QUALIFIED, or signup breaks.** The trigger is
> declared `security definer set search_path = ''` (`0003:3`) — which is exactly why its existing body
> says `public.profiles`. An unqualified `insert into workspaces …` raises *relation does not exist* and
> **breaks signup for every new user, including anonymous ones on the `/try` path**. It does not fail the
> migration; it fails later, in production, on the account-creation path.
>
> ```sql
> insert into public.workspaces (owner_id) values (new.id);   -- public. is REQUIRED
> ```
>
> Needs a signup regression test for both a registered and an anonymous user. My "two-line addition"
> framing was right about the mechanism and wrong about the one detail that makes it work.

**Why the segment must stop being *interpreted* as a uid — ⟳ RESTATED IN ROUND 2, because the first
version was over-constrained and cost a corpus migration.**

The first version of this paragraph said the id *"must be an independent UUID, never equal to any
user's uid."* **That is the wrong invariant.** The danger was never the segment's *value* — it was the
**predicate**. `split_part(name,'/',1) = auth.uid()::text` is an identity comparison that no membership
clause can revoke, because an `OR` against an unchanging fact cannot be undone. Once authorization goes
through a table, a segment that happens to equal a uid is just an opaque string, and access is revoked
by changing `workspaces.owner_id`.

> **The correct invariant, narrower and testable: NO PREDICATE MAY COMPARE THE PATH SEGMENT TO
> `auth.uid()`.** Exactly one site does today — `0007:14-15`, the policy this slice replaces. Verified
> across all 23 migrations and `lib/`: there is no other. That makes this a *guard with a test*, which
> the old wording was not.

What remains true: the table is cheap to add later and **the value baked into every object path is
not**, so the workspace must exist before the address is restructured. What is no longer true is that
existing objects must be re-keyed to adopt it — see §5.0.2.

**RLS changes now, but only to this** — no teams, no ACL, no roles:

```sql
create function workspace_readable(p_ws text) returns boolean
  language sql security definer set search_path = public stable as $$
  select exists (select 1 from workspaces w
                 where w.id::text = p_ws and w.owner_id = auth.uid());
$$;
revoke all on function workspace_readable(text) from public;
grant execute on function workspace_readable(text) to authenticated, anon;
-- storage policy body: bucket_id = 'artifacts' and workspace_readable(split_part(name,'/',1))
```

Text-to-text, **casting the column and never the segment** (§3). Anon still fails closed: `auth.uid()`
is NULL, so no row matches — the property `0007:9-11` documents is preserved rather than re-derived.

> **The structural payoff: `workspace_readable` becomes the SINGLE place teams are later added.** The
> policy never changes again and no path ever changes. That is §11.2's membership-not-identity rule
> made structural instead of aspirational.

**Explicitly deferred and genuinely deferrable** (none of them change a path): multiple workspaces per
user — the §11.0 grouping knob; teams, `workspace_members`, ACLs; the atomic-creation RPC; admin role
checks on destructive verbs.

**Cross-playlist dedup is NOT deferred.** With one workspace per user, every playlist that user owns
shares the manifest key `(workspace, video, slot)` and therefore one copy of the blobs. What is
deferred is *choosing a boundary smaller than the whole user*.

### 5.0.1 `workspace_videos` — the entity the manifest keys on

**⟳ ROUND 2 (Blocking). Raised in round 1 by the coordinator, found independently by Codex in round 2,
and only HALF closed by §5.0.** Adding `workspaces` gave `<workspaceId>` a source. It did not give
`(workspace_id, video_id)` one — and that is what both new tables are keyed on.

**`videos` has primary key `(playlist_id, video_id)`** (`0001:30`), so a video in two playlists is
**two rows**, while the artifact manifest is keyed per workspace and resolves to **one** blob. Two rows
therefore describe one shared body.

**Failure scenario.** P1 and P2 sit in one workspace and both contain V. The user corrects
*"Clawcode" → "Claude Code"* under P1. Per §5.2.2 the correction is applied before publish, so the
**shared** body changes for both. P2's row still has `corrections = NULL` and an `mdCorrectionsHash`
describing the uncorrected text — `update_video_annotations` is playlist-row scoped (`0021:48-53`). P2
now asserts an uncorrected body while serving a corrected one. The same holds for `ratings`: one body,
two different scores, and no way for a reader to tell which row describes what it is reading.

**This is root-cause shape #4 at the level §5.2 did not reach.** §5.2 bound the card to the generation
and moved the video judgments off it — correct when there is one video row per video, wrong the moment
two rows share a body.

```sql
create table workspace_videos (
  workspace_id uuid not null references workspaces(id) on delete cascade,
  video_id     text not null,
  -- everything that describes the SHARED BODY lives here, not on the per-playlist row
  primary key (workspace_id, video_id)
);
-- videos keeps per-playlist membership and per-playlist presentation only
alter table videos add column workspace_id uuid not null references workspaces(id);
alter table videos add foreign key (workspace_id, video_id)
  references workspace_videos (workspace_id, video_id);
```

`video_artifacts` and `video_generations` both FK to `workspace_videos`, so the manifest finally
references an entity that exists — and a cascade from it reaches them, which is half of B5's problem
solved structurally rather than by convention.

**The split, stated so it is not re-litigated:**

| Stays on `videos` (per playlist) | Moves to `workspace_videos` (per workspace) |
|---|---|
| `position`, `playlistIndex`, `archived` | `corrections`, `mdCorrectionsHash` — they change the shared bytes |
| per-playlist presentation | the video judgments of §5.2.1 — one body, one score |
| — | `personalNote`, `personalScore` — **open question**, see below |

> **Open, and it must be answered before a plan: are `personalNote` and `personalScore` per-playlist or
> per-workspace?** They do not affect the bytes, so either is defensible: per-workspace means "my note
> about this video"; per-playlist means "my note about this video *in this collection*." Unlike the
> others this is a **product** question, not a correctness one. Not choosing means the migration has
> nowhere to put them.

### 5.0.2 Seed migrated workspaces from the owner's uid — ⟳ ROUND 2, closes N-B4

**The problem this removes.** Replacing `artifacts_owner_rw`'s body with
`workspace_readable(split_part(name,'/',1))` denies **every object that exists today**, because every
one of them carries a *uid* in segment 1 and `workspace_readable` would find no workspace with that id.

That is not merely an outage. `SupabaseBlobStore.get` **collapses an RLS denial into `null`**
(`supabase-blob-store.ts:27-37`, `provesAbsence = false`), so the app would not report a failure — it
would report **absent artifacts**, and the serve path would treat paid content that exists as content
needing regeneration. The worker is unaffected (`artifacts_service_all`, `0007:16-17`), so the failure
is **asymmetric and invisible to a smoke test**.

**The fix is one line in the migration:**

```sql
-- EVERY workspace takes its owner's uid as its id, for the life of this slice
insert into workspaces (id, owner_id) select id, id from profiles;          -- migrated users
-- and in handle_new_user(), for new users:
--   insert into public.workspaces (id, owner_id) values (new.id, new.id);
```

> **⟳ ROUND 3 (Blocking B-3 / Codex [10]) — an earlier draft seeded only MIGRATED workspaces and gave
> new ones `gen_random_uuid()`. That fixed existing users by breaking every new one.** `Principal.id`
> is `auth.uid()` (`lib/storage/resolve.ts:93`) and `objectKey` composes `${p.id}/…`
> (`supabase-blob-store.ts:15`), so a post-migration user writes to `<uid>/…` while their workspace has
> a random id — `workspace_readable(uid)` matches nothing and **they cannot read their own blobs**,
> while the `service_role` worker happily keeps writing them. The same asymmetric, smoke-test-invisible
> failure as N-B4, mirrored onto the other population. **Fifth instance of shape #9 this slice.**
>
> **`id = owner_id` for ALL workspaces makes `Principal.id` correct by construction** and needs no
> `Principal` change at all. It is coherent only because rule 24 (one workspace per user) holds for
> this slice. **Its expiry is stated with it:** the day multiple workspaces per user ship, `id` can no
> longer equal `owner_id` for the second one, and `Principal` must become workspace-aware *in that
> slice*. Recorded here so the coupling is visible rather than discovered.

**Why that is safe, and why it is not a retreat to the position §11.2 rejects.** The revocability
problem was never the id's *value* — it was the *predicate*. Under `workspace_readable`, access comes
from `workspaces.owner_id`, so it is revoked by changing a row. A workspace id that happens to equal
some uid grants nothing on its own.

**What it buys — one predicate accepts both layouts at once, so there is no cutover:**

| Path | Segment 1 | `workspace_readable(seg1)` |
|---|---|---|
| Old `<uid>/<playlistKey>/…` | the owner's uid | workspace `id = uid`, `owner_id = auth.uid()` ⇒ **TRUE** |
| New `<workspaceId>/videos/…` | the same value | **TRUE** |
| A new user's workspace | the new user's uid (same rule) | **TRUE** — and they have no old-layout bytes |

Three consequences, each removing work this spec had taken on:

1. **N-B4 does not exist.** There is no window in which blobs are unreadable, so the
   denial-reads-as-absent cascade never fires.
2. **§10 stops being a cutover.** Both layouts are readable under one predicate, so the corpus
   migration becomes **incremental, interruptible and reversible** — which also defuses M9's objection
   that `reconcileCloudBase` cannot serve as a one-shot whole-corpus tool. It no longer has to.
3. **`Principal.id` is a no-op for existing users during the transition.** `p.id` = uid = workspace id,
   so `objectKey` composes byte-identical paths while the migration runs.

**The one cost, stated so nobody reads meaning into it:** every workspace id in this slice *equals* a
uid — migrated and new alike. It is nonetheless **opaque to every consumer**. The equality is a
migration artifact and carries no semantics; nothing may branch on it, and no predicate may compare a
path segment to `auth.uid()` (§5.0).

> **⟳ ROUND 4 (Codex #11) — this paragraph, the table row above it, the §5.0 DDL default and ADR-0006
> all still said new workspaces get a *random* id, thirty lines below the decision that they do not.**
> Round 3 changed the rule at the site where the bug was found and left four sites stating the old
> one. All four now agree.
>
> **Why this is the same failure as §5.1.3 and not a typo.** In both cases the fix was correct and
> *local*, and the sweep for siblings was the step that did not happen. The difference is only in what
> catches it: §5.1.3's sibling was in SQL, so executing the file found it in seconds; this one is in
> English, where the only instrument is `grep` for the shape of the claim — which found all four in
> one command, once someone thought to run it. **An I rule is checked by thinking, a P rule by
> enumerating, and a rule stated in four places is checked by grep.** The inventory records the
> classification; it should record the instrument too.

### 5.1 The artifact manifest

The per-video mapping from **slot → blob key**.

> **The table is [`schema/04_artifacts.sql`](2026-08-03-stable-blob-addressing/schema/04_artifacts.sql).**
> What follows is what it means and why; the file is what it *is*. Everything below was verified by
> executing it, and three claims this section used to make did not survive that.

**It is append-only, and it is not mutable state.** The first version of this section opened *"this is
the only mutable state in the design"* and keyed the table `(workspace_id, video_id, slot)` — one row
per slot, overwritten in place. That is incompatible with two other decisions made later and in other
sections: rule 13 **ranks** many generations for a slot, and §5.1.1's record-first order must insert a
row **before** the bytes exist. A single overwritable row can satisfy neither. So the manifest holds
one row per **(slot, generation)**, nothing is ever overwritten, and `current` is a **view**
(`video_artifacts_current`) rather than a column anyone writes.

**Paid and free are keyed differently, and that is the taxonomy, not a workaround.**

| | Key | Why |
|---|---|---|
| **Paid** (`summary`, `model`, `dig:*`, `digDeeper`) | append-only, one row per generation | the bytes cost money and are unreproducible; every one is kept and ranked |
| **Free** (`pdf:*`, `html`) | one row per slot, overwritable | a deterministic re-render has nothing to preserve |

Expressed as two **partial** unique indexes over a surrogate `artifact_id`, because a primary key
cannot say this. **Measured 2026-08-06:** naming `generation_id` in a primary key makes it `NOT NULL`
— a PK implies it, silently — which makes every free render unrepresentable
(`null value in column "generation_id" … violates not-null constraint`) and makes the
paid-kinds-need-a-generation check unsatisfiable for `render`. That is the **third** appearance of
this exact defect: twice as prose disagreeing with DDL, and the third time as a *side effect of the
fix for something else*. See §5.1.3.

**`state` and the lease.** `pending` is inserted before the bytes (§5.1.1's record-first order) and
only `recorded` is servable — §5.1.1's floor. A `pending` row **must** carry a lease expiry, enforced
by `check ((state = 'pending') = (lease_expires_at is not null))`: without one, a writer that dies
between the record and the bytes leaves a row that is neither servable nor collectable, and every
later reader sees `busy` forever. Record-first converts a double-charge into a lease; it does not
remove the need for one. Same shape as `reserve_serve_model`'s lease and attempt bound
(`0012`/`0014`) — this project has already solved this once.

> **⟳ ROUND 2 (Blocking) — my round-1 constraint made four of the six slot families unrepresentable.**
> I wrote `check (kind = case when slot like 'dig:%' then 'dig' else 'summary' end)` beside a
> **mandatory** generation FK. §2 defines six slot families and the rule was wrong for four:
>
> | Slot | My check forced | Reality |
> |---|---|---|
> | `model` | `kind='summary'` | a **separate paid** Gemini call (`generateMagazineModel`) — its own generation |
> | `digDeeper` | `kind='summary'` | a paid **dig** artifact (`lib/dig/generate.ts`) |
> | `pdf:<kind>` | `kind='summary'` **+ an FK** | a **free deterministic re-render** — no generation exists |
> | `slide:<id>` | `kind='summary'` **+ an FK** | §4 puts assets **outside generations by design** — there is no id to reference |
>
> **So the `slide` slot could not be inserted at all**: the design puts assets outside generations in one
> section and required every manifest row to name one in another. That is shape #9 — I closed Codex B1's
> soundness hole by trading it for an expressiveness hole in the same constraint.
>
> **Corrected.** `kind` is a first-class enum over the artifact taxonomy already in §3, the mapping is a
> function rather than a `case` buried in a constraint, and **the generation FK is nullable** — free
> re-renders and assets have none. Codex B1's actual guard is preserved and narrowed to where it belongs:
> it is the **paid** kinds that must name a generation, which the second `check` enforces.
> (`artifact_kind` and `slot_kind()` now live in `schema/03_generations.sql` and
> `schema/04_artifacts.sql`. `slot_kind` gained an `html%` arm there that this round-2 draft lacked —
> which is precisely how round 3 measured the slot guard failing **open**.)
>
> **And the composite FK needs a target it does not have (round 2, C2).** It references the 4-tuple
> `(workspace_id, video_id, generation_id, kind)`, but `video_generations`' primary key is the 3-tuple —
> Postgres rejects it outright: *"there is no unique constraint matching given keys for referenced
> table."* ✅ **Landed** — `schema/03_generations.sql` carries the `unique (workspace_id, video_id,
> generation_id, kind)`; it is trivially satisfied because `generation_id` is already unique within
> `(workspace, video)`.
>
> **A nullable FK column enforces nothing, which the round-2 fix did not account for.** Postgres FKs
> default to `MATCH SIMPLE`: if *any* column of the tuple is NULL the constraint is **skipped entirely**.
> So making `generation_id` nullable to admit free renders also made free renders unreferenced by any
> FK — a `pdf:*` row could name a video that does not exist in the workspace. The manifest therefore
> carries a **second** FK, on `(workspace_id, video_id)` → `workspace_videos`, which has no nullable
> column and so always fires. The fix that bought expressiveness had to buy back the integrity it spent.
>
> `video_generations.kind` also widens from `summary | dig` to the same enum, so a `model` generation
> can exist — it is a paid call and was never part of the summarize run.

**A table, not a jsonb column**, for one decisive reason: GC must ask *"select every referenced
blob_key"*, which is a query against a table and a full scan of jsonb otherwise.

Four constraints, each closing a round-1 finding:

- **`kind` + the composite FK + the `check` (Codex B1).** Without them a row can assert
  `slot='summary'` over dig bytes and resolve to a generation whose `card` is NULL. The FK carries
  `kind` so the generation must be of the right sort, and the `check` ties `kind` to the slot's shape.
- **`state` (Claude B4).** A `detached` dig keeps a row, so §8's sweeper — which marks from this table
  — sees it as *referenced rather than orphaned*. ⟳ **ROUND 6: this used to read "cannot collect the
  paid content §6.1 promises never to delete", and that promise was retired** (§6.2). The row buys
  enumerability and an orderly 90-day clock from `detached_at`, not permanence. `detached` is also
  restricted to `kind='dig'` and fenced by the append-only trigger in every state — §6.3.
- **`start_sec` / `end_sec` (Claude H4).** §6.1 is a span rule; without stored spans every attach
  decision reads a *superseded* summary blob through a `get()` that collapses 5xx into `null`.
- **`on delete cascade`, from `workspace_videos` rather than `workspaces`.** The round-1 draft cascaded
  from `workspaces`, which is a weaker statement than it looks: it only fires when an entire workspace
  is deleted. Cascading from `workspace_videos` covers the deletion that actually happens — a video
  leaving the workspace — and still reaches workspace deletion transitively, since `workspace_videos`
  itself cascades from `workspaces`. See §8 for the playlist-level unreferencing, which is the case no
  cascade can reach, because a video leaving *one* playlist must not delete a body another still uses.

**RLS — ⟳ NOT the house pattern (M3).** The house pattern (`for all using/with check (… = auth.uid())`
plus a client grant) is what `videos` uses, and a `videos` row is reconstructible. **A manifest row is
not**: deleting it unreferences paid blobs and starts the 90-day clock, with no undo anywhere in §8.
Follow `share_tokens` instead (`0013:16-18`) — the precedent §11.3 already praises: `force row level
security`, **no** anon/authenticated write policy, service_role-only grants, and every write through a
`security definer` RPC:

> **⟳ ROUND 2 (Blocking N-B3) — this RPC was specified BEFORE four other fixes changed the table it
> writes, so it could not set `kind`, `state`, `start_sec` or `end_sec`, and §6.2's "persist spans at
> write time" was unsatisfiable through the only writer the design allowed. Re-specified last, and it
> shrank rather than grew** — because §5.1.1 now *derives* `current` instead of writing it, so this is
> no longer a CAS at all:

> **⟳ ROUND 6 (B5 / Codex B3) — SETTLED, and the block below is now the SCHEMA's signature rather
> than prose.** This RPC was specified-before-the-table-changed a *third* time: round 5 changed the
> manifest under it again, and the round-6 reservation protocol (§9.2) shipped it explicitly
> incomplete. Handoff item 3 closed it, and the rule that finally stopped the cycle was sequencing —
> the payload was specified **last**, after the table had settled across three merges.

```sql
record_artifact(
  p_ws uuid, p_video text, p_slot text, p_generation_id text,
  p_kind artifact_kind, p_blob_key text,
  p_token uuid,                                   -- §9.2's holder identity; never a veto
  p_source_generation_id text default null,
  p_start_sec int default null, p_end_sec int default null,
  -- ⟳ round 6 B5 — THE PAYLOAD. `md_hash` was mandatory and had no producer at all.
  p_md_hash text default null, p_card jsonb default null,
  p_doc_version_major int default null,
  p_produced_at timestamptz default null          -- CARRIED for sync; now() only as a fallback
) returns text                                    -- 'recorded_as_holder' | 'recorded_after_loss'
```

**It completes the generation row and flips the artifact in one transaction, generation first.** The
order is enforced rather than merely intended: `video_artifacts_generation_complete` rejects a
recorded artifact whose generation is still `pending`, so both the in-place flip and the
append-after-loss path depend on the completion having already run.

`kind` is derived inside the RPC by the same `slot_kind()` function the `check` uses — **one
definition, called from both**, rather than the constraint and the procedure drifting apart. `state`
is not a parameter because detachment (§6.2) is a separate verb (`detach_artifact`), and a verb that
changes a row's meaning should not share an entry point with the one that creates it.

> **The `p_expected_key is null` trap, worth keeping even though the CAS is gone.** A conditional
> update spelled `where blob_key = NULL` **never matches**, so an "expect no row" path written that way
> silently records nothing and reports success. Any insert-if-absent must be `insert … on conflict do
> nothing` with a row-count check. This is the same shape as the `is not distinct from` correction the
> conditional-write slice needed (`docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md`),
> and it is why that slice is worth reading before implementing this one.

The client policy is **`select` only**. This also gives §5.2's conditional write a **single owner**
instead of one hand-rolled copy per writer — the exact shape of the 2026-07-30 architecture review's
finding #2.

**Reading the manifest needs the same three-way contract as `BlobRead` (Claude H1).** Today the money
guard is a `tryGet` on the blob, deliberately, because *a failed read must never look like an absent
artifact* — that is the measured 6¢→12¢ defect (`serve-doc.ts:59-71`,
`tests/integration/serve-model-unreadable.test.ts`). Under this design the authority moves to the
manifest, so **the same hazard moves with it**: a PostgREST error, a transient RLS failure, or a
`.maybeSingle()` whose error nobody inspects all produce "no row" → "no model" → a second paid Gemini
call for a model already in the bucket.

```ts
type SlotRead =
  | { ok: true;  key: string; generationId: string }
  | { ok: false; reason: 'absent' }
  | { ok: false; reason: 'unreadable'; cause: unknown };
```

`unreadable` is **required, not optional**, so callers cannot inherit an ambiguous form — the same
argument `blob-store.ts:53-55` makes for `tryGet`.

> **⟳ ROUND 3 (Blocking A-1) — the "both reads" rule was VACUOUS, and the cause is this design's own
> addressing change.** The rule permits a spend only when the slot is `absent` **and** the blob is
> provably absent. But the slot is `absent` exactly when **no generation is recorded** — and with no
> record there is **no key**, because the key needs a `generationId` that lives only inside the record.
> The second read has no argument on 100% of the paths that reach it.
>
> Today's guard works precisely because `MODEL_KEY(base)` is a **pure function of `base`**, so
> `serve-doc.ts:70` can ask *"are the bytes there anyway?"* about a record it does not have — which is
> the only question a money guard ever asks. §4 moved the key from *derivable* to *derivable only from
> a record*, and deleted that ability without noticing.
>
> **Live scenario:** a worker writes `<ws>/videos/V/g7/model.json`, then crashes before recording it.
> Slot absent, no key to probe, serve path spends again, `g8` is minted, and `g7`'s paid bytes sit
> unreferenced. Measured cost of exactly this shape: **6¢ → 12¢** (`serve-model-unreadable.test.ts`).
>
> **Resolution — invert the write order, rather than adding a probe key.** `record_artifact` inserts the
> row in state `pending` **BEFORE** the bytes are written, then flips it to `recorded` after a verified
> write. Then:
> - **bytes ⊆ records** — over the keys this design addresses. "No record" *entails* "no bytes",
>   determinately, with no probe needed, so the vacuous branch stops existing rather than being filled
>   in. **⟳ ROUND 4 (J2-2): "always" was wrong, and the exceptions matter more than the word did.**
>   Two classes of byte are outside the containment, one temporarily and one forever:
>
>   | | Records? | For how long |
>   |---|---|---|
>   | The **existing corpus** — every blob written before this design | no | until §10's migration records it. The set starts at 100% exempt |
>   | **`_staging/<uuid>/<key>`** — the atomic-write temp prefix of all three blob stores (`supabase-blob-store.ts:85`, `local-blob-store.ts:53`, `in-memory-blob-store.ts:152`) | **never** | permanent, by construction: a staged byte exists precisely so that it is *not* yet the artifact |
>
>   **This does not weaken the money guard, and saying why is the point of the row.** The guard needs
>   "no record ⇒ no bytes" **at the key it is about to spend on** — a `<ws>/videos/<v>/<gen>/…` key
>   under a fresh generation id. A staging key is never that key (different prefix, minted per attempt,
>   deleted on promote), and a legacy key is never that key either (old layout, no generation segment).
>   The containment holds exactly where it is load-bearing. **What is not permitted is the unqualified
>   sentence**, because §8's sweeper reads it as *"an unrecorded blob is garbage"* — and under that
>   reading the sweeper would collect a live staging blob mid-promote, and the entire pre-migration
>   corpus on its first run. One rule, two consumers, and only one of them can take it neat.
> - **"Record exists" entails "key known"**, so the blob probe finally has an argument.
> - A crash before recording leaves **nothing** — no bytes, no row, no orphan — so spending again is
>   correct rather than a double-charge.
>
> **Rule 19 restated around DETERMINACY, not absence:** *a spend requires a determinate negative from
> every layer that could hold the artifact; an indeterminate answer from any layer is `busy`.*
>
> **Two knock-ons, recorded rather than left to be discovered.** (a) §8's grace period was justified by
> *"a blob written but not yet published is unreferenced"* — **that state no longer exists**, so the
> grace period now covers only the orphan root set. (b) A generation id must be chosen *before* its
> content, which rules out content-hash ids for anything on a spend path; §4.1 already recommends UUIDs
> there and content hashes only for free re-renders, so the two agree — but §4.1 must say *why*.

> **⟳ ROUND 2 (High, Codex) — `SlotRead` is NECESSARY AND NOT SUFFICIENT, and my round-1 fix RELOCATED
> the guard instead of extending it.** A *present* slot still has to read the blob. If that read 5xxs
> and the caller treats it as absence, the measured 6¢→12¢ defect returns **unchanged** — the manifest
> said the model exists, so the failure moved one layer down rather than away.
>
> **Rule: every billable or source-of-truth serve path requires BOTH reads.** A paid regeneration is
> permitted only when the slot is **`absent`** *and* the blob is **provably absent**
> (`BlobRead.reason === 'absent'`, never a bare `null` — `provesAbsence` is `false` on Supabase). Slot
> `unreadable` **or** blob `unreadable` ⇒ `busy`, never a spend. This is the third time this session a
> fix moved a defect rather than removing it (shape #9); the tell each time was that the *new* layer
> was specified and the *old* one was assumed to have gone away. Write the
assertion in this slice; `serve-model-unreadable.test.ts` is the template and the scaffolding exists.

### 5.1.2 A derived artifact names the generation it came FROM — ⟳ ROUND 2 (High, N-H2)

A magazine model is rendered **from a specific summary body**. Nothing in the manifest recorded that,
and §4.2.1 retires the only drift check that exists today — the model envelope's `sourceSections`
comparison against the MD's section titles (`CONTEXT.md`'s *magazine model* entry). Retiring a check
without replacing it leaves the model free to describe a body it was not built from: root-cause shape
#4, on a **paid** artifact.

> **Rule:** a derived slot carries `source_generation_id` alongside its own `generation_id`. Drift
> becomes an **id comparison** — is my source still the current summary generation? — rather than a
> title-set heuristic.

Strictly simpler than what it replaces: today's check compares parsed section titles and can be fooled
by a reworded heading (the same fragility §4.2.1 documents for dig attachment). An id either matches or
it does not.

> **⟳ ROUND 4 (J2-4) — this paragraph used to end *"a model whose `source_generation_id` is no longer
> the current summary is **ineligible to be current**."* That is a gate, and rule 14 says staleness
> must never gate.**
>
> **Failure:** a summary is regenerated. The existing paid magazine model now points at the previous
> generation, so it is ineligible, so the `model` slot resolves to **nothing** — not "stale, with a
> banner", nothing. The magazine view is empty until somebody pays for `generateMagazineModel` again.
> That is round 4's A-2 with `model` substituted for `summary`, and today's shipped behaviour is the
> opposite: `readTitleStableModel` returns `{status:'ok', stale:true}` and the reader shows the model
> (`serve-doc.ts:90-96`).
>
> **Corrected: source-currency is a RANKING RUNG.** The floor stays `state = 'recorded'` and nothing
> else. `schema/04_artifacts.sql` implements it as the top rung of `video_artifacts_current`, and
> `05_assert.sql` proves the floor holds — *"a model whose SOURCE summary was superseded still serves"*.
> Expressing it needed a **second view** (`video_summary_current`): the summary's own ranking is an
> input to the ranking of everything derived from it, and a view cannot reference itself. Worth noting
> because it is the first place the design's layering shows up as a structural constraint rather than
> a stylistic one.
>
> **Same one-site-only pattern as §5.1.3 and Codex #11 — third instance this round.** Round 3 demoted
> *corrections* from filter to rank and left this sibling, three lines away, still filtering. The fix
> landed exactly where the finding pointed, and the finding pointed at one of two places.

It composes with §5.1.1's derived `current`: source-currency, corrections-currency and format are
three rungs of **one** ordering — one rule, three consumers, and none of them a gate.

### 5.1.1 Why this answers the concurrency problem

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
> **⟳ ROUND 1, Medium M4 — "the loser retries" is asserted three times and has no mechanism.**
> `jobs_idem_active` covers `completed` (`0009:11-13`) and `enqueue_job` **joins** rather than inserting
> on conflict (`0011:83-88`), so a worker whose conditional manifest write lost already holds a
> `completed` job and **nothing re-runs it**. Combined with §5.2.2 the consequence is concrete: if the
> loser is the generation that applied the user's corrections, the published generation is the one
> **without** them, permanently. The claim appears at §5.1.1, §9 row 1 and §9 row 3 as load-bearing.
>
> **⟳ ROUND 2 (High, N-H4) — my fix made it WORSE, and the rule it rested on turned out to be optional.**
> "Re-read and republish your own generation" always succeeds: the CAS was the only thing that could
> refuse it, so the protocol degrades to **last-writer-wins with unbounded flips**. Worker publishes
> *def*; sync loses with *abc*, re-reads, republishes, wins; the worker retries and wins back. Each flip
> changes which body is served and starts a 90-day clock on the generation that just lost.
>
> **The assumption worth questioning: that publication is a WRITE at all.**
>
> Everything else in this design is immutable — generations never collide, blobs are never overwritten.
> The manifest was kept mutable because §5.1.1 framed the problem as "two writers race for a pointer."
> But if *current* is **derived rather than written**, there is no pointer to race for:
>
> > **`current` = the highest-ranked RECORDED generation for that slot**, ordered by
> > `(corrections_current desc, doc_version_major desc, created_at desc, generation_id desc)`.
> > A total order, so no ties. **Ranking, not filtering — see the floor below.**

> **⟳ ROUND 3 (A-4 + my own A1) — flat recency discarded a hierarchy this project already settled.**
> `reconcile-class-a.ts:41-50` is merged and in production, and the Stage 3 spec states it as a
> principle: *"Class A — generated … reconciled by **format**, not recency."* Its rungs are
> **corrections-currency → format (never downgrade) → recency as a tiebreak within one major**. My
> ordering kept only the last rung, so a retry at an older `docVersionMajor` landing five minutes later
> would **silently downgrade the video's format**. `created_at` is also not comparable across replicas —
> a machine with a fast clock wins permanently — which is *why* the existing code ranks format above it.
>
> **And it is what makes sync convergent.** With every rung a replica-independent recorded fact,
> `current` is a deterministic function of the generation *set* — so two replicas that exchange sets
> compute the same answer, and sync needs no tiebreak negotiation at all (§5.3). Flat recency is not a
> function of the set; it depends on clocks. A-4 is therefore not only a correctness fix, it is the
> precondition for that property.

> **⟳ ROUND 3 (Blocking A-2) — THE FLOOR. Eligibility must never empty a non-empty set, and my
> corrections rule did exactly that.** I made "`mdCorrectionsHash` matches the video's current
> corrections" an eligibility *filter*. Corrections are a **free, synchronous, user-typed** field
> (`update_video_annotations`, `0021:19-53`). The instant a user saves one, **every generation ever
> recorded for that video is stale at once** — the newest and all its predecessors — so `current`
> becomes empty, the summary vanishes from the page, §5.1.2 makes the `model` slot ineligible too, and
> it comes back only after a **paid** regeneration. *A free user gesture would destroy visible content
> and create a bill to restore it.*
>
> Today's system does none of that: `reconcileClassA` records staleness as `needsRegen` **beside a body
> that keeps serving**, and `serve-summary-core.ts:47-57` never consults corrections at all.
>
> **Rule: staleness RANKS, it never GATES.** Split the two questions:
> - **eligible to be SERVED** — `state = 'recorded'`. That is the whole test, and it cannot empty a
>   non-empty set. This is the floor.
> - **ranked to be CURRENT** — the ordering above, where corrections-currency and format are the top
>   rungs. A stale generation still serves when it is the best available; it simply loses to a fresh one
>   the moment one exists.
>
> This is the same shape as shape #9 yet again: I converted an advisory signal into a gate, which is
> what turned "stale but serving" into "gone".
>
> **⟳ CROSS-DERIVATION PASS — an earlier draft of this line said "whose body is readable", and that
> reintroduced root-cause shape #1 inside the fix that was removing a different one.** A readability
> check at *resolve* time is a blob read per candidate, and `SupabaseBlobStore.get` cannot prove
> absence — so a transient 5xx would make the newest generation ineligible and **silently demote the
> video to an older body**, with no error surfaced anywhere. The very failure §5.1's `SlotRead`
> contract exists to prevent, arriving through the back door.
>
> **Eligibility is computed from RECORDED FACTS only.** ⟳ ROUND 4 (J2-4) — and it is now **two**
> lists, because collapsing them is what let staleness gate:
>
> | | Test |
> |---|---|
> | **Servable** (the floor) | `state = 'recorded'`, and the generation is not `body_collected`. That is all of it — see the note below on why the second conjunct is not an exception to rule 14 |
> | **Preferred** (the ranking) | source-currency, then corrections-currency, then format, then production time, then id |
>
> `mdCorrectionsHash` and `source_generation_id` used to appear in the first column. They now appear
> only in the second. Card completeness moved out of both — it is a **table constraint**
> (`gen_card_complete`), so an incomplete card cannot exist to be filtered.
>
> > **⟳ ROUND 5 (H3) — the floor said "and it cannot empty a non-empty set", and that was false.**
> > MEASURED: the summary slot went **2 rows → 0** once GC set `body_collected` on both generations
> > — round 3's A-2 failure reached through GC rather than through corrections, and §8 stated no rule
> > protecting the current generation.
> >
> > **`body_collected` is not staleness; it is byte existence.** A collected body has no bytes, so
> > serving it would be shape #4 — a row claiming something the blob does not satisfy. Gating on it is
> > therefore *within* rule 14 rather than an exception to it, and the honest statement of rule 14 is:
> > **no rule that is not about byte existence may gate.**
> >
> > That distinction alone does not save the floor, so the guarantee is now **enforced**:
> > `forbid_collecting_current()` refuses to collect a generation that is current for any slot
> > (asserted, and asserted in both directions — a *superseded* generation must still be collectable,
> > or §8 can never reclaim anything). Written as a §8 sentence it would have been a rule the sweeper
> > must remember, on the one path with no undo.
> >
> > **Still open (cross-derivation C5):** a free render has no generation, so this filter exempts it
> > structurally — the PDF of a collected body keeps serving. §8 needs *"collecting a body collects the
> > renders derived from it."* Recorded as open in `r5-cross-derivation.md`, not fixed.
>
> **Readability is verified once, at record time, by the writer that just wrote the bytes** — never
> re-litigated on the read path. Resolving a slot therefore touches no blob at all.
>
> > **⟳ ROUND 4 (J3-4) — and that verification proves less than the sentence implies, so the limit is
> > now stated rather than left to be discovered.** The writer is the worker, running as
> > `service_role` (`0007:16-17`); the reader is a session client under an entirely different policy.
> > **Record-time verification proves the bytes landed. It does not prove a reader may read them.**
> > The one failure class it structurally cannot see is an **RLS denial** — which
> > `SupabaseBlobStore.get:27-37` converts into `null`, i.e. into *absent*, which is root-cause
> > shape #1 arriving at the one layer this design declared safe from it.
> >
> > **So the migration owes an assertion, not an assumption:** after §10, one **session-client** read
> > per workspace, executed. This is the same demand §8 already makes of the sweeper — *assert the
> > collection, do not assume it* — applied to the reader's context rather than the writer's. It is
> > also the cheap kind: the scaffolding exists, and it either promotes a Blocking bug or retires a
> > finding.
>
> **What dissolves rather than gets patched:** no CAS on the manifest, so no loser, no retry path, no
> flip sequence, no bound to state (this finding); M4's "the loser retries" stops being a claim that
> needs a mechanism; `publish_slot` shrinks to *insert a generation row*, which removes most of N-B3;
> and §5.1.1's concurrency argument gets **shorter** — two concurrent runs simply produce two
> generations and the newer one is current, by definition rather than by protocol.
>
> **What it costs, stated honestly.** You lose the ability to *pin* an older generation as current —
> rollback after a bad regeneration. That is a real capability and §8's 90-day retention exists partly
> to serve it. It is re-addable with one nullable `pinned_generation_id` on `workspace_videos`, where
> `current` = the pin if set, else the derived value. **That is a deliberate override written by a
> human action, not a race**, which is the distinction that matters: the mutable state moves from "every
> writer" to "one explicit user gesture."
>
> **Second cost:** resolving a slot becomes an indexed query over a small per-video set rather than a
> single-row lookup. Cacheable, and cheaper than the protocol it replaces.
>
> **The corrections CAS (§5.2.2) survives and gets simpler.** It stops guarding a *pointer write* and
> becomes a completeness condition on the generation itself: a generation whose `mdCorrectionsHash`
> no longer matches the video's current corrections is **not eligible to be current**. Same effect, no
> race, and it composes with the eligibility rule above instead of sitting beside it.

- **Failure is never destructive.** A loser's blobs still exist, so a wrong pointer is temporary and a
  re-run repairs it. This is what makes "compensate after the cycle" — the user's instinct — actually
  sound: compensation only works if the cycle never destroys anything.

> **Scope of this section — ⟳ RESOLVED 2026-08-05, keep reading to §5.2.** Everything above is about
> **blobs**. The per-video **scalars** (`tldr`, `ratings`, `docVersion`, …) used to live in one
> overwritten slot on `videos.data`, so *"the new run's scalars beside an older generation's body"*
> was expressible — a real, observed failure, and what froze a row permanently in the conditional-write
> slice. **§5.2 closes it** (Q8, decided): the card is an attribute of the generation, so card and body
> are inseparable by construction. This box stays because the *reasoning* is still needed — §5.1.1 alone
> does not solve the concurrency problem, and a reader who stops here will believe it does.
>
> **"Trivially sufficient" is also now contradicted by evidence.** The conditional-write slice was
> built first specifically to test that claim (its §7). Five adversarial review rounds produced
> **26 Blocking findings, none of them in the predicate** — every one was in the protocol around it:
> NULL semantics, payload rebuild, publish semantics, status inheritance, deploy mechanics, address
> adoption, field-omission semantics. The conditional write itself was correct from the first draft.
> The claim should be narrowed to what was actually demonstrated: *the conditional write is simple;
> the publish protocol around it is not.* Trail: `docs/reviews/spec-conditional-write-*.md`.

### 5.1.3 The same defect, three times, the third time caused by its own fix

Worth recording as a shape rather than an incident, because it is the most expensive pattern this
review has produced and the third instance was the cheapest to have prevented.

**The defect:** a free render (`pdf:*`, `html`) has no generation, and something makes
`generation_id` mandatory, so free renders become unrepresentable.

| | How it was written | How it was found |
|---|---|---|
| Round 2 (C1) | prose said *nullable*, the DDL said `not null` | human review, reading both |
| Round 3 (B-2) | fixed in prose; the DDL was never edited | human review, reading both again |
| Round 4 (this) | DDL edited — and a **new PK** silently re-imposed `NOT NULL` | **executing it**, in seconds |

The third one is the interesting one. Nobody wrote `not null`. The fix was *"make the manifest
append-only"*, done by adding `generation_id` to the primary key — and **a primary key implies
`NOT NULL` on every column it names.** The mandatory-ness was a side effect of a correct fix to an
unrelated finding, in a different subsection, defended by no reviewer's attention because no reviewer
was looking at that line.

**Three generalisations, in increasing order of usefulness.**

1. *A physical rule is checked by enumerating, not by thinking* (round 4's method note). "PK implies
   NOT NULL" belongs on the physical list; it was not on it, so the sweep could not have caught it.
2. **A fix must be swept against the rules, exactly as an original is.** Rounds 2–4 each swept the
   artifact and then edited it; nothing swept the edit. Five of the nine root-cause shapes are
   "a fix that moved a defect," and this is why: the fix is the least-reviewed text in the document.
3. **The cheap version of both is to make the artifact executable.** This instance was found in one
   run, by a machine, for no review budget at all — and the two before it each cost a round. What
   changed was not rigour but the *medium*: a design spec looks like the artifact, so schema lived in
   it as illustration, and illustrations do not compile.

**And a guard with no test is why it survived a green run.** `05_assert.sql` said, in a comment,
*"a paid slot with a generation, **and a free render with none**"* — and inserted two paid summaries.
The missing case was not overlooked; it was **named and not written**, which reads as coverage to
every subsequent reader including its author. The assertion file now carries the free-render positive,
and it fails without either half of the fix.

### 5.2 The card joins the generation — **DECIDED 2026-08-05 (user), closes Q8**

A summary is **two** things produced by one Gemini run: a **body** (the blob) and a **card** — the
summary-owned scalars `tldr`, `ratings`, `overallScore`, `takeaways`, `videoType`, `audience`,
`language`, `tags`, `processedAt`, `docVersion`, `mdGeneratedAt`, `mdCorrectionsHash`
(`0021:120-132`). §5.1.1 generation-scoped the body and left the card in one overwritten slot, which is
what kept *"run #2's card beside run #1's body"* expressible.

**Decision: the card is an attribute of the generation, not of the video.** One run produces one
generation carrying both; a reader that resolves a generation gets a card and a body that provably
came from the same run.

#### 5.2.1 The card is not homogeneous — refined 2026-08-05

**Some of those scalars describe the DOCUMENT; others describe the VIDEO.** The first draft moved all
of them, which is more than the problem requires. A judgment about the video does not become wrong
because the document was regenerated — the video did not change.

| Scalar | Describes | Lives on |
|---|---|---|
| `tldr`, `takeaways` | the document's prose | **generation** |
| `docVersion`, `mdGeneratedAt`, `processedAt`, `mdCorrectionsHash` | the run | **generation** |
| `ratings`, `overallScore`, `videoType`, `audience`, `language`, `tags` | the video | **`workspace_videos`** (⟳ cross-derivation pass: "the video" was ambiguous once §5.0.1 split per-playlist rows from the per-workspace entity — one body must not have two scores) — carried forward, stable across regenerations |

**Rule:** only *document facts* must travel with the body — those are the ones that can lie about it.
*Video judgments* stay on the video and are **stable**: the first generation sets them, a later one
does not re-roll them. Rationale: Gemini is non-deterministic, so re-rolling means a video's score
moves for a reason the user did not cause. A user who *wants* fresh judgments can ask for them — a
deliberate action, not a side effect of a doc-version bump.

> **⟳ CORRECTED IN ROUND 1 (Blocking) — the premise "nothing about them is a claim about the body" was
> FALSE, and the rule needs a second half.** Five of the six video judgments are **written into the
> body's own YAML frontmatter** by the generator (`lib/ingestion/summary-core.ts:99-108`):
>
> ```
> `lang: ${language.toUpperCase()}`,
> ...(videoType ? [`type: ${videoType}`] : []),
> ...(audience ? [`audience: ${audience}`] : []),
> `score: ${overallScore}`, '---',
> ```
>
> plus `tags` in both the frontmatter and the quick-view callout (`:121`, `:131`). Every value comes
> from a **fresh Gemini roll** on each run (`:86`).
>
> **So "keep the row's value, let the body get a new one" reproduces exactly the card/body lie §5.2
> exists to remove — on six fields, in the section that claims to remove it.** Generation *abc* scores
> 8; the row says 8 and the body says 8. Regenerate: *def* rolls 6 and writes `score: 6` into its
> frontmatter, the manifest makes *def* authoritative, the row still says 8. The list renders 8; the
> document reads 6.
>
> **And one of them spends money.** `language` flows to `resolveMagazineModel` →
> `generateMagazineModel(sections, language, …)` (`serve-summary-core.ts:110`, `serve-doc.ts:112-116`).
> A row frozen at generation 1's language against generation 2's body prompts a **paid** magazine
> transform in the wrong language.
>
> **Resolution — the writer is authoritative, not the reader.** Generation *N* must be **produced with
> the carried-forward judgments as input**, so the body it writes agrees with the row by construction.
> The reader-side alternative (resolve judgments from the earliest generation) does not work: Obsidian
> indexes the frontmatter directly, so the body is a surface we do not control.
>
> **This is structurally the same rule as §5.2.2's corrections rule**, and it carries the same
> unstated cost, now stated: `summaryCore` gains a parameter for prior judgments, and the Gemini prompt
> contract changes to accept them. §5.2.1 was presented as *reducing* work; it does not.

> **Do not confuse these with the human fields.** `personalNote`, `personalScore` and `corrections`
> (`backfill.ts:19`) were never card fields; they belong to the user and already survive regeneration.
> `overallScore` is *Gemini's* score, distinct from the user's `personalScore`.

#### 5.2.2 A generation is not publishable until corrections are applied

**Corrections must carry forward to every new generation.** A user who corrected *"Clawcode" → "Claude
Code"* must not be asked to type it again after a re-summarize — and today they are.

**The live defect this closes** (verified 2026-08-05): a fresh summarize does **not** apply
corrections. `pipeline.ts:272` stamps `mdCorrectionsHash: mdHash('')`, and the cloud worker
(`summary-handler.ts`) does not mention corrections **at all**. Because the worker never *sets* the
field, `persist_summary`'s layer-2 merge **preserves the old value**. So after a cloud re-summarize the
body has no corrections applied while the row asserts `mdCorrectionsHash = <hash of the user's
corrections>`.

> **That is the same card/body lie as B-R4-1, on the path where the lost content is something the USER
> typed.** The system does not merely drop the correction work — it claims the work is still there.
> Only `/regenerate` applies corrections (`route.ts:63`), and that path edits an existing document
> rather than producing a generation.

**Rule:** a summary generation is not publishable until the current corrections have been applied to
it, and `mdCorrectionsHash` records what was actually applied — never what was merely on file.

> **⟳ ROUND 1, High (Codex) — "current" is a moving target, so the rule needs a CAS.** Corrections are
> mutable while a generation runs (`update_video_annotations`, `0021:19`). A worker starts with C1,
> the user saves C2 during the Gemini call, and the worker publishes a generation stamped C1 — **born
> stale**, and by §5.2's own construction the row now truthfully describes a body the user has already
> superseded.
>
> **Rule:** publish must CAS on the corrections hash (or `annotationsEditedAt.corrections`). If it
> moved, the generation is stored **unpublished** and either retried against C2 or left for the next
> run — never published. Storing rather than discarding matters: the bytes were paid for.
>
> **⟳ ROUND 2 (High, Codex) — "stored unpublished" is a dead end as written, because nothing ever
> picks it up.** A worker that loses the CAS still finishes its job, and a `completed` job is a
> dedup root: `jobs_idem_active` covers `completed` (`0009:10-13`) and `enqueue_job` **joins** rather
> than inserting on conflict, so no re-enqueue is possible. The user's corrections are then
> permanently absent from the published body while a paid, correct generation sits unreferenced.
>
> **Rule: a failed publish CAS is a NON-TERMINAL job outcome.** Either the job requeues (leaving the
> idempotency slot open), or the unpublished generation lands in a `pending_publication` table a
> worker sweeps and republishes idempotently. Naming the CAS without naming the retry path is the
> same defect M4 already had — and M4's fix inherited it, which is why it recurred in the same round.
>
> **⟳ CROSS-DERIVATION PASS — most of this stack no longer applies, because §5.1.1 removed the publish
> CAS entirely.** With `current` **derived** rather than written, there is no pointer to compare, no
> CAS to lose, and therefore no "stored unpublished" limbo and no requeue protocol to specify. Two
> rounds of review, three findings, and a `pending_publication` table all existed to make one mutable
> pointer safe.
>
> **What survives, and it is strictly simpler:** the corrections rule becomes an **eligibility
> condition** evaluated at resolve time from recorded facts — *a generation whose `mdCorrectionsHash`
> does not match the video's current corrections is not eligible to be current.* The worker that raced
> with C2 simply records its generation; it never becomes current, nothing is lost, its bytes stay for
> §8's retention window, and the next run against C2 supersedes it by being newer and eligible.
>
> **Keep the reasoning above** — it is why the eligibility form is required rather than optional, and a
> reader who skips it will re-propose the CAS.

**⚠ This rule depends on corrections being cheap to re-apply, which today they are not.** They are
free-form English handed to `fixSummary` (`gemini.ts:456`), a Gemini pass that returns **the whole
document**, so carrying them forward costs a full-document round trip per generation. That is why the
code does not do it. **Backlog #23** restructures corrections as deterministic `{from, to}` pairs
(LLM-authored so variants are still handled, but never LLM-applied), which makes carry-forward pure
string replacement at zero cost — and keeps a model from rewriting a document whose **headings are an
identity anchor** (§4.2.1). *This spec states the rule; #23 is what makes it affordable.* Sequence #23
first, or this rule ships as an expensive per-generation Gemini call.

**The card must stay queryable without fetching a blob.** Frontmatter inside `summary.md` is
therefore rejected: the playlist list renders ratings and scores for every video, and the quick-view
route serves `tldr`. Neither can afford N blob reads. So the card lives in the database, on a
generation record:

```
video_generations
  workspace_id  uuid  not null
  video_id      text  not null
  generation_id text  not null
  kind          text  not null          -- 'summary' | 'dig' — what run produced it
  card          jsonb                   -- the summary card; NULL for a dig generation
  created_at    timestamptz not null default now()
  primary key (workspace_id, video_id, generation_id)
```

`video_artifacts.generation_id` references it. Resolving *the current card* is then the same join as
resolving *the current body* — `video_artifacts` where `slot = 'summary'`, then its generation — so
the two cannot disagree. Same RLS pattern as §5.

**What this costs, measured 2026-08-05 rather than estimated.** 21 files read card fields off a video
(`lib/html-doc`, `lib/cloud-sync`, `app/api` ×3 each; the rest single files, including 6 components).
**That number overstates the work**, and the reason matters:

> Those 21 are almost all reading a `Video` **object the storage layer assembled**, not querying
> columns. Assembly moves; the read model's shape does not. So the change concentrates in the storage
> and persistence layer, and most of the 21 do not change at all.
>
> **But this is exactly where to be careful, because "the shape is unchanged" is also how the current
> bug hides.** Keeping the shape is acceptable *only because* assembly now resolves card and body from
> **one** generation — coherence enforced once, at assembly, instead of asked for at 21 call sites and
> checked at none. If assembly ever reads the card from one place and the body key from another, the
> defect returns with every reader still looking correct. That invariant belongs in a test, not a
> comment.

**Two things this closes beyond the incoherence itself.**

1. **The idempotency skip gains something truthful to key on.** `summary-handler.ts:86-92` compares a
   stored `docVersion` against the job's. Today that `docVersion` can describe a body it did not come
   from — which is how a row froze permanently in the conditional-write slice (B-R4-1). Against a
   generation, the comparison means what it says.
2. **`persist_summary`'s field-merge whitelist stops being load-bearing — CONDITIONALLY.**
   > **⟳ ROUND 1, High H2.** This is true only if every producer writes a **complete** card, and today
   > the cloud worker writes none of the currency fields: `summary-handler.ts:149-164` carries
   > `docVersion` and `processedAt` but **no `mdGeneratedAt` and no `mdCorrectionsHash`**. §5.2.2 names
   > the second; the first has the identical hole on the identical lines. Under the old merge that
   > silently preserved a stale value; under an immutable generation record it becomes a silent **NULL**,
   > which is worse: `reconcile-class-a.ts:49` tiebreaks on `(a ?? '') > (b ?? '')`, so a NULL cloud
   > `mdGeneratedAt` **loses to local every time, deterministically**, and the next sync overwrites a
   > freshly-paid cloud body with an older local one. Today's stale-but-non-null value loses only
   > sometimes; the §5.2 form loses always.
   >
   > **Rule:** make card completeness a **schema fact, not a convention** — plus a producer-side card
   > type the compiler forces every writer to populate.
   >
   > **⟳ ROUND 2 (High) — my first wording said "every document fact `not null` on
   > `video_generations`", which the schema contradicts.** The card is a single `card jsonb` column,
   > explicitly **NULL for a dig generation** — `not null` cannot constrain members of a jsonb value,
   > and a blanket `not null` on the column makes dig generations uninsertable. So the fix read as
   > closed and enforced nothing. **Corrected — the constraint is conditional on kind:**
   >
   > ```sql
   > check (kind <> 'summary' or card ?& array[
   >   'tldr','takeaways','docVersion','mdGeneratedAt','processedAt','mdCorrectionsHash'])
   > ```
   >
   > A summary generation cannot be inserted with an incomplete card; a dig generation may carry none.
   > Completeness is now enforced by the database rather than promised by prose. Note `as any` on a test double opts out of compiler enforcement, so back it with a
   > behavioural test. And fix `summary-handler.ts` **in this slice** — it is one of the two producers. The three-layer jsonb merge
   at `0021:116-133` exists to avoid dropping summary fields on a status-only persist. With the card
   written once as part of an immutable generation record, there is no partial-update semantics to get
   right — the merge disappears rather than being fixed. That whitelist and its "absent → preserved"
   rule accounted for several of the conditional-write slice's Blocking findings.

**Terminology consequence — feeds the `CONTEXT.md` pass (§15).** *Generation* no longer means "a run
that produced a body." It means **a run that produced a body and its card, which are inseparable.**
Write that definition, not §2's current one.

> **⟳ ROUND 6 (B5) — refine that sentence before writing it into `CONTEXT.md`: they are inseparable
> *once the generation is complete*.** A generation also has a moment of existing before either
> exists, and taking "inseparable" as unconditional is precisely what made the write path
> unsatisfiable. See §5.2.3.

### 5.2.5 Guard classification: SHAPE or SEQUENCE — ⟳ ADDED 2026-08-07, opening round 8

**The question that produced this.** Round 7's `B1` was a decision that had an assertion *and* a
passing mutation and broke anyway. Asking why led one level up: `record_artifact` promises *"never
discards paid work"*, which is a **negative property over 32 independent rejection mechanisms** —
23 on `video_artifacts`, 8 on `video_generations`, plus every one added later. No assertion can hold
that, because each new guard is a new way to break it. Item 3 added one trigger and the promise
broke.

**The rule.** Every guard is one of two kinds, and they want opposite failure behaviour:

| | Asks | A violation means | Must |
|---|---|---|---|
| **SHAPE** | is this row well-formed and referentially sound? | the **caller is wrong** | **reject** |
| **SEQUENCE** | who got here first? has this already happened? is this in flight? | **concurrency** — the caller did nothing wrong and may already have spent money | **reconcile**: upsert, no-op, or typed outcome. Never a raw rejection |

**This generalises the user decision of 2026-08-07** — *"the reservation guards SPENDING, not
RECORDING"* — which was exactly this insight, recorded as a rule about one function instead of as a
property of a class. That is why it broke twice more, in places nobody thought to look.

**Result of the pass: 32 guards, 26 SHAPE, 6 SEQUENCE.** Every CHECK and every FK is SHAPE and
correct. Of the six:

| SEQUENCE guard | Expressed as | Verdict |
|---|---|---|
| `video_artifacts_inflight_uq` | typed `busy` / `exhausted` | ✅ built as a reconciler |
| `video_artifacts_paid_uq` | `on conflict … do update` | ✅ reconciler since round 7 |
| generation-not-complete | raise | ✅ deliberate — it *is* the ownership fence |
| generation CONTENT freeze | raise + caller-side `state='pending'` filter | ⚠️ reconciles on the protocol path only |
| **`video_artifacts_free_uq`** | raw `23505` | ❌ **no reconciler existed** |
| **`forbid_collecting_current`** | raise | ❌ **aborted the caller** |

**Both defects were invisible to seven rounds of adversarial review**, and the reason is instructive:
each guard is *plainly correct*, so a reviewer reads it and moves on. The classification does not ask
whether a guard is right — it asks **what it does when the caller is merely second**, which is a
question nobody asks of a constraint they agree with.

- **The free-render path had no working writer.** `free_uq`'s own comment promises free renders are
  *"overwritable"*; measured, the first render of a slot succeeded and every re-render failed with a
  raw `23505`. `record_artifact` could not write one past the first at all, because one INSERT takes
  one conflict arbiter and its was the **paid** partial index, which a NULL generation can never
  match. Structurally the same defect as handoff item 3 — an entire *kind* of write unreachable —
  surviving for the same reason: every fixture writes a free render **once**.
- **§8's retention sweep could never run.** `forbid_collecting_current` raised, so a batch
  `update … set body_collected = true` died on the first current generation and rolled back the rest.
  Retrying could not help, because a current generation is *permanently* current. A guard that made
  its own purpose unreachable. Fixed by moving the currency test into a predicate the sweeper selects
  **through** (`video_generations_collectable`), keeping the trigger as a backstop — **not** by
  weakening it, and deliberately not by silently suppressing the update, which would be shape #5 on
  the one path with no undo.

**Where this belongs in the process.** It is the same move `dev-process.md` already mandates for
*rules* — classify **P / I / H**, then cross-derive — applied one level down, to **guards**. The
technique existed and was pointed at the wrong layer.

### 5.2.4 What round 7 found — the four items **as a set** — ⟳ ADDED IN ROUND 7

Round 7 was called for one purpose: the four merged items had each been reviewed against *itself* and
none against the others. **Every Blocking and High it returned was an interaction between two of
them, and a defect in none of them individually** — reproducing round 6's cross-derivation verdict
under the same condition.

| | Interaction | What it did |
|---|---|---|
| **B1** | item 4 × item 3 | `record_artifact`'s append was **blind**, so a worker that merely restarted and forgot its token collided with its **own** pending row — `[23505]`, no race required. The function whose comment says it *"never refuses"* discarded paid work through a raw SQLSTATE |
| **B2** | item 1 × item 3 | nothing bounded `produced_at`, a **caller-supplied ranking rung**. A future value made §6.2's detach permanently impossible, and the error blamed the writer for a value it never supplied |
| **H2** | item 3 × item 4 | the generation completion was fenced on **nothing** — a caller could complete another writer's generation, and item 3's freeze then locked the real owner out of its own paid work **forever** |
| **H3** | item 3 × item 4 | a **denied** reservation still left a `pending` generation row that nothing reaches or collects |

**The through-line: item 3 gave the generation a lifecycle and item 4's protocol was never re-derived
against it.** Every fence item 4 established was on the *artifact*; item 3 added a second table to the
write path and no fence followed it there. That is shape #10 — a fix applied at one site with an
identical sibling nearby — at the granularity of a whole table rather than a line.

**B1 is the one worth remembering, because it silently revoked a user decision.** On 2026-08-07 the
`lease_token` veto was **declined** so that a writer which already paid always records. Item 3's
freeze trigger, written a day later in a different file, restored exactly that rejection through
`video_generations` instead of `video_artifacts`. *A rule can be overturned by a change that never
mentions it.*

Two things the fixes taught that no reviewer reported:

- **A CHECK constraint is evaluated on the proposed tuple BEFORE conflict resolution.** The first
  version of B1's fix put `coalesce(excluded.…, …)` in the `DO UPDATE`, and a caller omitting the
  span still got `[23514] art_dig_has_span` from the `VALUES` clause. `excluded.*` is the tuple that
  already had to be legal — **it cannot be used to repair itself.** Added to the physical-rules sweep.
- **The span belongs to the SLOT, the provenance to the GENERATION.** A reclaimed writer's own row is
  gone, so a same-generation lookup finds no span; but `dig:8` means seconds 8–88 in every generation
  of it, so the span is recoverable from any row for the slot. `source_generation_id` is not —
  borrowing it across generations would manufacture a provenance claim.

**And one fix turned out to carry no guard of its own.** B2 had two halves — bound `produced_at`, and
scope the `detached_at` bound to `INSERT`. Mutation shows the second is *subsumed*: once `produced_at`
cannot be in the future, running the bound on `UPDATE` is a guaranteed no-op. It stays because it says
truthfully where the guard lives, and it is recorded as an expected-GREEN mutation — the same status,
and the same treatment, as item 2's rung-1 `=`.

### 5.2.3 A generation has a lifecycle too — ⟳ ADDED IN ROUND 6 (B5 / Codex B3), handoff item 3

**The premise that failed:** *a generation row is only ever complete.*

That was true while the manifest held one row per slot and the generation was written once, after the
fact. Rounds 5 and 6 gave the **artifact** a lifecycle — `pending → recorded → detached` — and a
reservation protocol (§9.2) that must insert a `pending` row **before** the content exists. Its FK
parent never got the matching one. So the child had states and the parent did not, and the two rules
met in the middle:

- the FK requires the generation row to exist **before** the artifact row;
- `gen_card_complete` / `gen_summary_has_hash` / `gen_major_matches_card` require it to be complete,
  which is only knowable **after** the paid call.

Both were measured (§10.0). The honest invariant is narrower than the one that was written:

> **A generation must be complete when something RECORDED points at it** — not from the moment it
> exists.

**Same move as items 1 and 2, and the tell was the same each time.** Item 1 separated *a CHECK governs
states, a trigger governs transitions*; item 2 found the guard living in the `NOT NULL` rather than in
the comparison beside it. All three were an invariant written as *"X is always true"* that meant *"X
must be true when Y observes it"* — and in each case the symptom was an **unsatisfiable ordering**,
never a wrong value. Classified per `dev-process.md`: *knowing `md_hash` requires the Gemini call*
is **P**; *completeness is unconditional* was **I**, and it was the one wearing the costume.

**The shape:**

| | |
|---|---|
| `video_generations.state` | `pending \| complete`, **defaulting to `complete`** |
| The four summary CHECKs | gated on `state = 'complete'` |
| `produced_at` | nullable while pending; required at completion (`gen_complete_has_produced_at`) |
| `video_artifacts_generation_complete` | nothing may be `recorded`/`detached` against a pending generation |
| `video_generations_freeze` | `complete` is terminal and the content freezes with it |
| `reserve_artifact_slot` | lazily inserts the **pending** generation, satisfying the FK |
| `record_artifact` | completes the generation, then flips the artifact — one transaction |

**The default is `complete`, and that is a safety argument rather than a compatibility one.** A
producer that never heard of the column keeps today's behaviour exactly: its incomplete row is still
rejected. Defaulting to `pending` would have made every completeness CHECK optional for anyone who
merely omitted the column — a fail-open default inside the constraints round 4's J1-2 fixed *for
being fail-open*. The relaxation is strictly opt-in and `reserve_artifact_slot` is the only caller
that opts in.

**What makes gating the CHECKs safe is the artifact-side trigger, not the gate.** Relaxing a
constraint to "only while complete" is a bypass unless something guarantees everything observable
reaches complete. With the trigger, every row either ranking view can reach has satisfied all four in
full — which is why the views needed no change at all. Mutation-checked in both directions: removing
the trigger turns the gates into the bypass, and it goes red.

**`complete` is terminal because the artifact's address is frozen.** `video_artifacts` forbids
rewriting `blob_key` on a recorded paid row, and this table describes the bytes that key names.
Rewriting `md_hash` or `doc_version_major` in place would be shape #3 — a mutable value inside an
address — relocated one table up, and `doc_version_major` is the format rung, the one rung rule 13
says must never regress. `body_collected` is deliberately **not** frozen: it is §8's lifecycle
marker, the one thing about a finished generation that is supposed to change.

**Two consequences worth stating rather than discovering:**

- **Task #25 dissolved — `digDeeper` was never bound to one generation.** The FK is on
  `(ws, video, generation_id, kind)`, so a `digDeeper` artifact points at a **`digDeeper` generation**,
  minted per rewrite of the accumulator, not at the summary generation whose sections it contains.
  Those need no card and no `md_hash`; two coexist under append-only and `current` ranks them.
  Verified by execution. The finding came from reasoning about the *name* — the same route by which
  round 2 forced `digDeeper` to `kind='summary'`, and by which item 1's `P9` was reported as a defect
  and was not one. **Third instance: check the constraints, not the noun.**
- **A crashed summary worker now leaves a `pending` generation row as well as an exhausted slot**
  (§9.2's `summary_max_attempts = 1` consequence). It is inert — never ranked, never served, never
  collected — but it is litter, and §8 currently has no sweep for it. Flagged for round 7 rather than
  fixed here, because the retention rule for an abandoned reservation is a decision, not a mechanism.

### 5.3 Sync — ⟳ ROUND 4 (Codex #9, J2-5, and round 3's A-5): rewritten, because all three sentences were wrong

This section previously read, in full: *"Sync stops moving bytes. It compares two artifact manifests
and produces one. Nothing is copied, nothing is deleted, no address changes."* Every clause of that is
false, and the first two are false against **merged, production code** rather than against a later
decision:

| Claim | Reality |
|---|---|
| *"Sync stops moving bytes"* | `reconcileClassA` returns `copyToLocal` / `copyToCloud`, acted on at `lib/cloud-sync/sync-run.ts:780-791`. Copying bytes is what sync **is** |
| *"compares two artifact manifests"* | **Local has no artifact manifest.** The §5 SCOPE box already established this; §5.3 was never updated to agree with it |
| *"produces one"* | Set reconciliation presumes symmetry. One side has generations; the other has a file |

**The asymmetry is the design, not a gap in it.** Cloud stores *n* generations per slot and derives
`current`. Local stores **one file per slot** in a display-name layout (§7), plus a per-playlist **sync
baseline** — the *other* thing called a manifest, in `lib/cloud-sync/manifest.ts` (§2). Local has no
generation set to exchange, so there is nothing for a set union to be commutative over. Sync must
**translate**, not reconcile.

**The translation is a PROJECTION, and it needed a schema change to be possible at all.**

> **⟳ ROUND 5 (B3, Blocking, found by both reviewers) — the previous version of this paragraph claimed
> `ClassASignals` was "field for field" the ranked card fields and that `reconcileClassA` "runs as
> written, unmodified". Both were false, and I wrote them one batch earlier.** The review brief
> flagged this as the highest-stakes claim in the document *because* I had authored it; that
> instruction is the only reason it was checked.

`ClassASignals` (`lib/cloud-sync/types.ts:4-11`) has **six** fields; the old sentence named four.

| `ClassASignals` field | Cloud source | Status |
|---|---|---|
| `docVersionMajor` | `video_generations.doc_version_major` | ✅ ranked, rung 2 |
| `mdCorrectionsHash` | card `mdCorrectionsHash` | ✅ ranked, rung 1 |
| `mdGeneratedAt` | card `mdGeneratedAt` | ⟳ **the view used to rank `produced_at` instead** |
| `mdHash` | **nothing — it did not exist** | ⟳ **now `video_generations.md_hash`** |
| `summaryMdKey` | `video_artifacts.blob_key` | projected, not ranked |
| `backfilled` | no cloud analogue — a local provisional marker (§5.5) | projected as `false` |

**Two of those were load-bearing, and neither was a wording problem.**

**(a) `mdHash` did not exist.** `reconcileClassA` reads it as *presence* (`:17-18`) and as *equality*
(`:32`). Project it as `null` and `:23` returns `copyToCloud` **unconditionally** — every sync appends
a new generation, forever, and every append is a paid slot. Derive it instead by reading the cloud
blob and you have reintroduced shape #1 on the money path, because `SupabaseBlobStore.get` cannot
prove absence. The sharp part: **this document already said so, twice, in other sections** (§9.1's
*"grep for `mdHash` across all 23 migrations returns zero"*, and §15's *"needs a persisted hash of the
body, and none exists"*). §5.3 contradicted its own document, and the contradiction survived because
no one reads a spec front-to-back looking for one section assuming what another disproves.
It is now a recorded fact (`md_hash`, required for summary generations) — which is what "runs
unmodified" always required and never said.

**(b) the recency rung ranked a different value on each side.** The views ordered by `g.produced_at`;
`reconcileClassA:49` orders by `mdGeneratedAt`. **MEASURED: opposite winners on the same pair** — two
replicas, each correct by its own rule. Both views now rank the card's `mdGeneratedAt`, which keeps
round 4's J2-3 property (a recorded fact, not a clock read) *and* matches the merged code.

**(c) ⟳ ROUND 6 — rung 1 diverged too, for the ENTIRE corpus, and the fix for (b) did not sweep to
it.** Round 5 corrected rung 3 and left rung 1 — *one line above it* — broken by two independent
causes, both measured:

- **the migration dropped the data.** `03` seeded `workspace_videos` with `select distinct
  workspace_id, video_id from videos` and nothing else, so `corrections_hash` was **NULL for 2903 of
  2904 rows** while **99 live videos carried real corrections**.
- **the two sides spelled "no corrections" differently.** Both producers emit `mdHash('')` — a real
  64-hex string (`pipeline.ts:272`, `sync-run.ts:651`) — while the schema permitted a JSON `null`.

Consequence on the money path: cloud permanently rung-1-stale against a current local, so
`reconcileClassA` returns `copyToCloud` on **every sync, forever** — verbatim the failure (a) above
was written to remove, one rung higher. Shape #10 (a rule derived at one site and not re-derived at
its sibling), and shape #9's cousin: the round-5 fix was correct and incomplete in the same motion.

> **Rule: "no corrections" is ONE value, it is NOT NULL, and it is DEFINED rather than DERIVED.**
> `no_corrections_hash()` returns a pinned constant which today equals `mdHash('')`, since
> `canonicalizeMd('')` is a lone newline. Defining it is what let this be settled **before**
> backlog #23: when corrections become `{from, to}` pairs, an empty pair list still hashes to this
> constant *by definition* instead of to whatever `mdHash('[]')` happens to be. Re-deriving it is the
> obvious future simplification and it silently re-opens the divergence.

**Why NOT NULL is the actual fix and the backfill is not.** A nullable `corrections_hash` conflates
*"this video has no corrections"* with *"nobody ever computed this"* — shape #1, absent-vs-failed,
sitting on the **top rung of both view orderings**. That conflation is not incidental to the bug; it
is *why the bug was invisible*: 2903 rows meaning "never backfilled" read as "no corrections", and
`is not distinct from` obligingly returned TRUE for two NULLs. Backfilling repairs 2903 rows once;
NOT NULL makes the state unrepresentable. Rung 1 correspondingly drops to a plain `=` — though that
line **carries no guard of its own** while NOT NULL holds, and the schema says so where a reader will
see it rather than letting a tightened-looking comparison pass for a fix.

**`gen_card_complete` now requires `mdCorrectionsHash` as a VALUE**, reversing round 5's
cross-derivation C2. C2 argued a JSON null was *"the correct, meaningful answer for a video with no
corrections"* and that requiring a value would make rung 1 false for every uncorrected video. Checking
the **producers** rather than reasoning about the value showed both halves wrong: no producer has ever
emitted null, and rung 1 becomes *true*, not false, once the uncorrected side also carries the
constant. Third round running where an argument was made about a symbol and the answer lived at the
usage sites — `docs/dev-process.md` already encodes the fix ("at fix time, list the consumers").

**Drift is prevented, not repaired — and this half no reviewer asked for.**
`workspace_videos.corrections_hash` is a **denormalized copy**; the truth lives in `videos.data`. A
backfill fixes today's rows and says nothing about the next write, so B4's fix as proposed would have
been correct and temporary. A trigger on `videos` recomputes the copy whenever the corrections text
changes — chosen over "route the writes through one RPC" because a routing rule holds only until
someone adds a second writer, and there is already more than one (`update_video_annotations` in
`0021`, and `persist_summary`'s layer-2 merge).

**The cross-language agreement is a regression guard, not a one-off check.** The SQL canonicalizer
reproduces `content-hash.ts` (CRLF → LF, strip trailing newlines, NFC, one trailing newline), verified
on four vectors — empty, plain ASCII, CRLF with repeated trailing newlines, and non-ASCII — and those
vectors are **asserted**, because if the two ever diverge the sole symptom is `copyToCloud` on every
sync: a money-path failure that raises no error anywhere.

So the projection is:

- **cloud → signals:** project `current` down to a `ClassASignals` — one row, one tuple, six fields,
  two of which (`summaryMdKey`, `backfilled`) are carried rather than ranked.
- **local → signals:** unchanged; the local file already produces exactly this today.
- **reconcile:** `reconcileClassA` runs unmodified — **now true**, and only because of `md_hash`.
- **cloud ← a local win:** record a *new generation* whose card carries the local tuple, then write the
  bytes (record-first, §5.1.1). A local win is an **append**, never an overwrite.

**This is why round 3's A-1 mattered beyond ranking.** `reconcileClassA` orders by
corrections-currency → format → recency, and the views now order by the same three rungs on the same
values. Had `current` kept flat recency — or kept ranking `produced_at` — the two sides would disagree
about which of two inputs wins and sync would oscillate. **One hierarchy, two implementations, and
they must not drift.** They had already drifted, in the paragraph asserting they had not, which is the
argument for the citation rather than the assurance: `schema/04_artifacts.sql`'s ranking and
`reconcile-class-a.ts:38-50` are one decision written twice, and each must name the other.

**Deliberately not settled here.** Which slots sync at all (§7 says the paid body; `digDeeper` is
scope-blocked, not rule-blocked), what happens when local wins a slot whose cloud generation has
`body_collected`, and whether a local file should mint a generation id or inherit one. **This spec's
job was to name the asymmetry so the sync slice can be planned; the sync slice's job is to resolve
it.** That slice cannot start until this section exists, which is exactly why three sentences was a
Blocking finding rather than a stylistic one.

---

## 6. Cross-generation mixing — the sharpest constraint

The design permits a manifest whose `summary` slot points at generation *def* while `dig:120` points
at generation *abc*. That flexibility is desirable — a dig is expensive and should survive a
regeneration where possible — but **it is not unconditionally safe.**

A dig is generated from a **section span** of a specific summary. A dig from *abc* is servable under a
summary from *def* only if its span still corresponds to a real section in *def*.

**Rule:** cross-generation attachment requires a **span overlap ratio** above a threshold (per the
2026-07-31 decision). Below it, the dig remains stored — ~~never deleted~~ **not deleted *by the
attachment rule* (⟳ round 6: §8's 90-day clock still applies from `detached_at` — see §6.2)** — but is
**not attached** to the current summary and does not render.

**Arbitrary mixing is not safe; validated mixing is.** A wrong attachment silently mislabels paid
content, which is worse than showing none: the user cannot tell it is wrong.

### 6.1 The attachment rule — **DECIDED 2026-08-05 (user), closes Q3**

> **When it is ambiguous, leave it unattached. Never guess.**

**Attach a dig from generation *abc* to a section of summary *def* only when the match is unambiguous
in BOTH directions:**

1. **Exactly one** section of *def* overlaps the dig's span above the threshold — and
2. **exactly one** dig claims that section.

If either count is 0 or >1, the dig stays **stored and unattached**. It is never
attached to a guess and never silently dropped. ⟳ **ROUND 6 — it is NOT "never deleted":** that
phrasing survived here after §6.2 retired it, and the two sentences would have shipped contradicting
each other. Unattached ⇒ detached ⇒ §8's ordinary 90-day paid-retention clock, running from
`detached_at`. What §6.1 guarantees is that *this rule* never deletes it — silence and a guess are the
failures being excluded here, not collection.

**Both directions are required, and §6 as written only described one of them.** Each side catches a
different restructuring:

| Case | Ambiguous from | Caught by |
|---|---|---|
| **Merge** — regeneration combines two sections; two predecessor digs land on one survivor | the **section's** side | clause 2 |
| **Split** — regeneration divides one section; one predecessor dig overlaps two successors | the **dig's** side | clause 1 |

A rule phrased only as *"does this dig match a section?"* passes both digs in the merge case and
notices nothing. **§6 named merge and never named split** — worth recording, because it is the same
defect shape as the merge case and would have been missed by a rule written only against the example
that was in front of us.

**Threshold — ⟳ REWRITTEN IN ROUND 1. The single-ratio version was wrong in BOTH directions, and both
reviewers found a different one.**

The original rule was *"overlap ≥ 0.8 of the dig's own span."* It measures how much of the **dig** the
section covers, and never how much of the **section** the dig covers. Consequences:

- **It attaches wrongly (Claude H3).** *abc* has `[100,200)` and `[200,300)`; only the first was dug.
  *def* merges them into `[90,400)`. The dig's span is entirely inside the section, so the ratio is
  **1.0** and clause 1 passes; clause 2 passes because the second section was never dug. **Attached** —
  and the reader sees a dig covering the first quarter of a section, presented as that section's dig.
  §6 calls this the worst outcome: *"a wrong attachment silently mislabels paid content."*
- **It strands legitimate content (Codex H4).** *abc*'s dig on `[100,200)`; *def* splits into
  `[100,170)` and `[170,200)`. Overlaps are 0.7 and 0.3, so **nothing** clears 0.8 and clause 1 rejects
  — permanently, for an ordinary split rather than a genuine ambiguity.

**Corrected rule — the ratio must hold in BOTH directions:**

> Attach only if `overlap / dig_span ≥ 0.8` **and** `overlap / section_span ≥ 0.8`.

Both ratios stated explicitly so an implementer cannot pick one. Still tunable **upward** only: raising
either can withhold attachments, never create wrong ones.

**Degenerate spans (M8).** `windowForSection` can produce `endSec === startSec` — its own header
documents the collision case, and `allocateSectionStarts`'s clamp (`hi = Math.max(lower, upper)`) lets
the last start reach the duration. **A zero- or negative-length span never auto-attaches**, rather than
dividing by zero.

**The threshold is no longer the only path back to visibility.** Because a correct split now leaves a
dig unattached by design, §6.1 must give it a route back — see the detached-slot rule below.

### 6.2 A detached dig needs a manifest row and a stored span — ⟳ ADDED IN ROUND 1, corrected in ROUND 5

> **⟳ ROUND 5 — the `@<generationId>` suffix is gone, and it dissolved rather than being fixed.**
> Detaching used to **rewrite the slot**, which is an address mutation — shape #3, in the section
> whose entire purpose is to stop paid content being lost. Nobody flagged it for four rounds because
> it looked like a naming convention rather than a write.
>
> It was only ever a workaround for the round-2 `primary key (workspace_id, video_id, slot)`, under
> which a detached row would have collided with the row replacing it. **Append-only keys on
> `(slot, generation_id)`, so two dig rows for one section coexist naturally and the slot never
> changes.** A structural fix from round 4 retired a convention in round 5 that had been invented to
> survive the constraint round 4 removed.
>
> **Found by cross-deriving my own fix, not by a reviewer.** The append-only trigger (round 5 M1)
> initially froze every recorded paid row, which made detaching *impossible* — §6.2 unimplementable.
> Asking why a detach needed to write at all is what surfaced the address rewrite underneath it. The
> trigger now freezes the **address** (`slot`, `generation_id`, `blob_key`) and permits the one
> meaning-change the design needs: `recorded → detached`. Both are asserted.

**Two Blocking findings say "never deleted" and "re-attachable" are not yet rules, only intentions.**

**(a) §8 collects exactly what §6.1 promises to keep (Claude B4).** §6.1 says an unattached dig "is
never deleted." §8 says *"mark and sweep over the artifact manifest; anything not referenced is a
candidate,"* and a detached dig — by §6.1's own construction — **has no manifest row**. So it is
unreferenced, it is paid, and the 90-day clock collects it. Two decisions closed hours apart, and the
one that runs wins.

> **Rule:** a detached dig keeps a manifest row — ~~slot `dig:<sectionId>@<generationId>`~~ **slot
> unchanged (⟳ round 5)**, in state `detached`. It is therefore *referenced*, therefore
> ~~never a sweep candidate~~ **not an ORPHAN — but still a sweep candidate on §8's ordinary clock
> (⟳ round 6, see below)**. This also gives the
> "surface it as detached-but-recoverable" requirement something to **enumerate**, which it had no way
> to do before.

> **⟳ ROUND 6 — "never a sweep candidate" was WRONG, and it contradicted a decision made the day
> before.** §8's retention rule (*"if a blob is not current, delete it — except a paid blob, which is
> retained for 90 days"*) applies to a detached dig **immediately**, because a detached dig is never
> current *by construction* — that is what detaching means. So §6.2 promised permanence in the same
> spec where §8 scheduled collection, and whichever mechanism shipped first would have won.
>
> **USER DECISION 2026-08-06: §8 wins. Detached artifacts are cleared periodically.** A dig whose
> section no longer exists is not content the product owes the user forever; it is content the user can
> re-dig against the new section structure.
>
> **This is the third finding in this section in three rounds** (round 5: the trigger made detaching
> impossible; round 6 B3: detaching stripped every guard; round 6 H1: a detached dig was collectable).
> Per `dev-process.md`'s recurrence trigger, the right response was to ask which rule here was a
> **choice wearing the costume of a constraint** — and "a detached dig is never deleted" was exactly
> that. Retiring it **dissolved round 6 H1's `P9`**, which had been reported as a defect only because
> this sentence claimed otherwise. No code changed; the false premise did.
>
> **What the correction costs, stated explicitly** (a rule whose cost is unwritten cannot be
> re-evaluated): a user who regenerates a summary, leaves a dig detached for 90 days, and then restores
> the original section boundary will find the dig gone and must pay to re-dig it. That is accepted.
> The alternative — paid bytes no sweep may ever touch — is an unbounded, un-auditable retention class,
> and §8's own warning is to *"fail toward collectable rather than toward pinned forever."*
>
> **Rule (added):** the clock starts at **`detached_at`**, not at "stopped being current". A dig can be
> detached while its generation is still current, in which case a not-current clock never starts at
> all. The column is written by the append-only trigger, never by the writer — the party that benefits
> from postponing collection must not set the deadline. Same "cheap now, impossible to retrofit"
> argument this section already makes for the span: once digs detach without a timestamp, when they
> detached is unknowable.

### 6.3 `detached` is a state, so it must be FENCED like one — ⟳ ADDED IN ROUND 6

**The round-5 append-only trigger gated its entire body on `old.state = 'recorded'`, and
`recorded → detached` is the one transition it deliberately permits.** So detaching first stepped
around everything it enforces — in two statements, in the trigger written to make that impossible.
Four bypasses were measured; the two that were real are fixed, and naming why the other two are not is
half the value of the finding.

| | Measured | Disposition |
|---|---|---|
| `P1` | detach → `DELETE` succeeds | **Fixed** — the gate now reads `old.state in ('recorded','detached')`. This is the serial-coherence orphaning defect (PR #42) reachable in two statements |
| `P1b` | detach → rewrite `blob_key` → re-record | **Fixed** — same gate. Shape #3, a mutable value in an address, *inside the trigger that exists to remove shape #3*. Retention is irrelevant to it: it repoints paid content at different bytes while the address column reads as untouched |
| `P10` | detach the current summary → collect → the slot empties | **Closed by `art_detached_is_dig`** — a summary can no longer be detached at all |
| `P9` | collect a generation whose dig row is detached | **Not a defect** — §6.2's retired promise was its only basis |

**Only a dig may be detached** (`art_detached_is_dig`). Detachment means *"this artifact no longer maps
to a section of the summary"*, and `dig:<sectionId>` is the only section-scoped slot. This was verified
against the **producers**, not the slot names, because the names actively mislead: `digDeeper` is not a
section-scoped dig but the **per-video document that accumulates them**
(`companion-doc.ts:4`), and the cloud stores no such blob at all — it assembles the document at serve
time from the individual digs (`app/api/html/[id]/route.ts:46-62`). It was never attached to one
section, so it cannot be detached from one. **Round 2 already made this exact mistake in reverse**,
forcing `digDeeper` to `kind='summary'` by reasoning from the slot name (§5.1's table).

**It is a CHECK and not only a trigger rule, because the trigger is `before update or delete`** — an
`INSERT` written straight to `state='detached'` fires no trigger. A constraint governs *states*; a
trigger governs *transitions*; this design needs both, and `service_role` bypasses RLS but never a
constraint.

**Immutability now covers what a row CLAIMS, not only where it points (Codex H5).** The frozen set was
`slot, generation_id, blob_key` — the address. `source_generation_id` is a **ranking input** to the
source-currency rung, so a stale recorded model could rewrite its provenance to the current summary and
win the rung *without regenerating a byte*; and `start_sec`/`end_sec` are the durable recovery data
§6.2 calls impossible to retrofit. All three are frozen for recorded **and** detached paid rows.

**Re-attachment (`detached → recorded`) stays permitted**, with the address unchanged — §6.1 owes a
correctly-split dig "a route back", and a fence that forecloses recovery would defeat the section it
protects.

> **~~Known gap, not left silent~~ — ⟳ CLOSED BY ITEM 3 (§5.2.3), not carried into round 7.** On
> `INSERT` the writer supplies `detached_at` and nothing overwrites it, because **sync must replicate
> an already-detached dig carrying its original clock** — a receiver that stamped `now()` would reset
> the retention clock on every replica and the bytes would never be collectable. That left a writer
> able to backdate a row it is inserting for the first time, i.e. request earlier collection of its
> own paid content, and it was deferred on the grounds that closing it needed the generation-write API
> **handoff item 3** had to specify regardless.
>
> That API exists now, so it is closed here. **Not by forbidding a supplied value — sync still needs
> one — but by bounding it to the artifact's actual lifetime:** `detached_at` may not precede the
> `produced_at` of the generation that made the bytes, and may not be in the future. What turns that
> into a real bound rather than a speed bump is item 3's freeze trigger: `produced_at` is immutable
> once the generation is complete, so the lower bound cannot be walked back either.
>
> **It also found an illegal value inside an existing test fixture.** The re-detach assertion carried
> `detached_at = 2020-01-01` against a generation produced in `2026-02-01` — a state the system cannot
> reach, sitting in a passing test. The fixture only ever needed a timestamp the *trigger* had not
> written. Same class as round 5 H1: a test can encode an unreachable world and still be green.

**(b) The span exists nowhere durable, so re-attachment depends on a blob §8 deletes (Claude H4).**
§6.1 is a span-overlap rule, but §4's key encodes only the **start** (`sectionId` *is* `startSec`), and
`endSec` is derived at read time from the *whole parsed summary* of the generation that produced the
dig (`lib/dig/section-window.ts:46-48,58`). Two failures follow:

1. **Permanently unattachable.** A later generation restores the original boundary — but *abc*'s
   `summary.md` stopped being current and was collected, so the span is unknowable and the dig can
   never be re-attached.
2. **Absent-vs-failed on the decision path.** Every attach decision reads a *superseded* summary blob,
   and `SupabaseBlobStore.get` collapses 5xx/timeout/RLS into `null` (`provesAbsence = false`). A
   transient blip renders an attachable paid dig as absent — paid content that flickers.

> **Rule:** persist `start_sec` and `end_sec` on the artifact-manifest row **at write time**.
> Attachment becomes a pure database computation: no blob read on the decision path, no dependency on
> a collected summary, and the absent-vs-failed shape cannot reach it. **Cheap now, impossible to
> retrofit after the first sweep runs.**

**What the user sees when a dig is unattached is a product question this spec does not answer, but it
must not be silence.** The dig is paid content that still exists; showing nothing is how content
becomes invisible-and-forgotten, which is the failure mode §1's whole symptom table is about. With the
`detached` slot above it is at least *enumerable*, so a later slice can decide presentation without
first having to find the content.

---

## 7. Local's role — hub-and-spoke

**Cloud is the content hub. Local is authoritative for naming, and holds the materialized
authoritative set.**

This resolves cleanly *because addressing and naming are now separate concerns:*

- **Cloud** stores every generation, addressed by id. Opaque, stable, never renamed.
- **Local** materializes only the authoritative set, named for humans (`003_alpha.md`) so Obsidian
  wiki-links and muscle memory keep working. `serialNumber` becomes purely a display-name input.
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

- **Mark and sweep** over `video_artifacts`. Anything not referenced is a candidate. **Two root sets,
  not one** — see the unreferencing rule below.

> **⟳ ROUND 1, Blocking B5 — as written, an explicit delete INVERTED this rule.** `video_artifacts` has
> no playlist column and no FK to `playlists`; the 0019 cascade reaches `videos`, `jobs` and
> `share_tokens` only. So deleting a playlist left its manifest rows intact, the sweeper saw every blob
> as **referenced**, and nothing was ever collected. §8's headline promise — *collected **immediately**,
> not in 90 days* — became **never**, on the path built to honour an explicit delete. Worse, the blob
> cleanup already runs best-effort and returns 200 on failure (`route.ts:78-82`), so nothing reports it.
>
> **Rule: unreferencing is DB state and belongs inside the commit-point transaction, not on the
> best-effort byte path.** Delete the manifest rows in the same transaction as the playlist, then let
> the sweeper (with its grace period) delete the bytes. **Byte deletion may stay best-effort;
> unreferencing may not.** Order it so a partial failure fails toward *collectable* rather than toward
> *pinned forever*. Only then is §8's "assert the collection, do not assume it" even expressible.
>
> **The sweeper needs a second root set:** objects with **no manifest row at all**. Without it an
> orphan is not merely uncollected, it is *invisible* — which is how the current
> superseded-dig and old-base accumulation already happens.
>
> **⟳ ROUND 2 — bound it, and make a failed listing fail CLOSED.** This root set is a full-bucket
> enumeration differenced against the manifest, over a paginated `list` (`supabase-blob-store.ts:137`;
> the local stack alone holds 973 objects). Scan **by workspace prefix** with a durable cursor, and
> state the rule that matters most: **a `list` page that errors ABORTS the sweep.** Otherwise a
> transient failure returns a short object list, every missing object reads as "no manifest row",
> and the sweeper deletes live paid content — root-cause shape #1 aimed at the delete path.

> **⟳ ROUND 1, High H7 — `video_generations` has no lifecycle, so a card outlives its body.** §8 sweeps
> `video_artifacts` and collects **blobs**; §5.2's generation record is DB state this section never
> mentions. After a body is collected at day 91 its generation row remains, so any reader resolving a
> generation by id — the recovery path this very 90-day window exists to serve, or §6.2's detached-dig
> surface — gets **a card with a 404 body**. That is §5.2's "both or neither" failing across the GC
> boundary, in the mirror direction, on the path built for recovery.
>
> **Rule:** collect the generation row with the last blob of that generation, **or** mark it
> `body_collected` so a reader can tell. And specify the FK from `video_artifacts.generation_id`
> including its `on delete` behaviour — §5.2 said "references it" and declared no constraint at all
> (now fixed in §5.1's composite FK).
- **Grace period — mandatory.** A blob written but not yet published is unreferenced and must never be
  collected. This is the classic GC race; a minimum age (hours, not minutes) is the standard defense.
- **Retention — DECIDED 2026-08-05 (user).** One rule, and it fits in a sentence:

  > **If a blob is not current, delete it — except a paid blob, which is retained for 90 days so it
  > can be recovered.**

  So *free* blobs (`htmls/…`, `pdfs/…`) live exactly as long as they are the authoritative copy of
  their slot. *Paid* blobs (`<base>.md` / `summary.md`, `models/…`, `dig/…`, dig-deeper) survive
  **90 days past the moment they stopped being current**, then are collected. Nothing that is current
  is ever a candidate, whatever its kind.

  **Why 90 days, and why a duration rather than a count** (decided 2026-08-05 after the first draft
  said "retained indefinitely", which was a word rather than a decision):

  - **The recovery scenarios are clocks, not counters.** Both are *someone noticed something went
    wrong*, which elapsed time measures and regeneration count does not.
  - **A count evicts by activity, and bursts of activity are when mistakes happen.** "Keep the last 2
    generations" would let a video regenerated three times in one afternoon evict the good copy from
    *before* the bad run — exactly the copy the rule exists to protect.
  - **90 rather than 30, because the two scenarios have very different clocks.** "This regeneration is
    worse than the old one" is noticed in days. "A bug silently orphaned paid content" is not: the
    promote-divergence defect (backlog #22) went **five weeks** between being confirmed and being
    rediscovered from scratch.
  - **Cost is not the constraint.** Paid artifacts are *text* — summary markdown, dig markdown, model
    JSON. The bulky artifacts are slide assets, which §4 keeps **outside** generations entirely, so
    they are untouched by this rule. Three months of superseded text per video is not a storage
    conversation.

  **Retention is a CEILING, never a floor — an explicit delete outranks it.** This is a correctness
  rule, not a tuning knob, and it is the one part of §8 that needs a test rather than a note. The app
  already has full hard-delete for playlists (`DELETE /api/playlists/[id]`, cascading videos, jobs and
  share tokens via the 0019 FKs). When a user deletes, the superseded paid generations must be
  collected **immediately**, not in 90 days — otherwise "delete" does not delete, and the retention
  window becomes a window during which the system knowingly keeps content someone explicitly asked it
  to destroy. The 90 days bound how long an *unreferenced* paid blob may linger **on its own**; they
  never license retaining anything past an explicit delete.

  > **This rule has a live dependency, not just a test.** Delete only outranks retention if delete
  > still works — and §4 shows it does **not** survive the new path template unchanged: today's
  > hard-delete is a prefix sweep over `${p.id}/${p.indexKey}/`, and `indexKey` is the playlist
  > segment this design removes. Its worst failure mode is silent (the route accepts blob-cleanup
  > failures and returns 200), which would turn the 90-day ceiling into *forever* without anything
  > reporting it. **Assert the collection, do not assume it.**

  > **⟳ ROUND 1, High H6 — assets are misclassified here, and this rule would delete the most expensive
  > artifact in the system.** §3 calls slide assets "free of Gemini", so the paid/free split sends them
  > to *delete when not current*. But `CONTEXT.md:44` classes them **source-of-truth**: they need a video
  > download plus a re-encode, and on a hosted server they **cannot be recaptured at all** (ADR-0005 —
  > the container ships no ffmpeg). **"Free of Gemini" is not "free to recreate", and this rule is
  > written against cost of recreation.** Assets are retained on the paid side.
  >
  > **Second half of the same finding: assets are keyed on a per-generation value while stored
  > generation-free.** §4 argues they may sit outside a generation because "a frame at 120s is the same
  > frame regardless of which generation drew a boundary near it" — yet the key
  > `assets/<videoId>/<sectionId>-<start>-<end>.jpg` leads with `sectionId`, which **is** `startSec`,
  > allocated per generation. `lib/dig/slides.ts:207-231` then prunes every `<sectionId>-*.jpg` the
  > current run did not write, **bypassing the BlobStore seam** (§14 Q7's second writer). So a dig run for
  > generation *def*'s section 120 deletes generation *abc*'s images, and *abc*'s dig — which §6
  > explicitly permits to remain attached — renders broken.
  >
  > **⟳ ROUND 2 (High, Codex) — re-keying assets without a migration makes existing ones INVISIBLE,
  > and they are the one artifact that cannot be recreated on the host at all (ADR-0005).** Bytes
  > already live at `assets/<videoId>/<sectionId>-<start>-<end>.jpg` (`slides.ts:170-188`); readers
  > asking for the new shape find nothing, and §8 now classes them paid, so nothing regenerates them
  > either. **Required:** a dual-read fallback (new key, then old) until a rewrite pass completes, and
  > **`pruneSectionAssets` must be disabled for the duration** — otherwise the transition itself
  > deletes the old-key bytes it is meant to preserve.
  >
  > **⟳ ROUND 2 (Blocking N-B1 + High N-H9) — the fixes above collide, and the rule underneath both is
  > the one to drop.** Round 1 reclassified assets as *paid*, moving them from "deleted immediately" to
  > "deleted at day 90"; the *other* round-1 fix gave the sweeper a root set matching anything with no
  > manifest row. Assets can never hold a manifest row — §4 puts them outside generations by design — so
  > together the two fixes **guarantee** every slide asset is deleted on day 91, and per ADR-0005 the
  > host cannot recapture them. "Repair needed" with no repair available. That is the **fourth**
  > instance this session of a fix moving a defect rather than removing it.
  >
  > **The assumption worth questioning: that every object in the bucket is an ARTIFACT the manifest
  > tracks.** It is not. `CONTEXT.md:42` already classifies a slide screenshot as **source-of-truth** —
  > and a source is not garbage. A transcript is not garbage-collected either.
  >
  > > **Rule: assets are SOURCES, not artifacts. They are outside the manifest by design, and the age
  > > sweeper never collects them.** They are removed only by an explicit delete of the video or
  > > playlist that owns them — the same lifecycle a transcript would have. This is the reviewer's
  > > "third root set", but justified by the artifact taxonomy the project already has rather than
  > > bolted on to stop a symptom.
  >
  > **N-H9 dissolves with it.** `pruneSectionAssets` (`slides.ts:207-231`) deletes every
  > `<sectionId>-*.jpg` the current run did not write, bypassing the BlobStore seam. Under
  > generation-immutability that behaviour is simply **wrong** — assets are shared across generations,
  > so a dig run for *def* must not touch *abc*'s frames. Apply the deletion test: remove the pruner and
  > what reappears? Only unbounded growth of a *source* kind, which is what sources do and what the
  > explicit-delete path already handles. **Delete the pruner rather than re-key it.** That also removes
  > §14 Q7's second seam-bypassing writer, so the question shrinks to one writer.
  >
  > **Rule:** key assets on the timestamp window alone, no `sectionId`. Per §4's own argument they are a
  > function of `(videoId, start, end)`; leading with a per-generation value contradicts the reason they
  > were placed outside generations in the first place.

  **Three further consequences, each load-bearing.**

  1. **The paid/free split must be derivable from the KEY ALONE.** An orphan has no manifest entry —
     that is what makes it an orphan — so the sweeper cannot ask the manifest whether a candidate was
     paid. It has to read the key. That works today, and it promotes key shape from an addressing
     concern to a **money-safety** one: any future key that does not announce its own paid-ness is
     either uncollectable or unsafe to collect. Add that to the review checklist for new key shapes.
  2. **The grace period still applies to free blobs.** A PDF written but not yet published is
     not-current and free, so the naive reading of the rule would sweep it mid-write. Grace period
     first, kind second.
  3. **Verify at plan time that nothing serves a non-current free blob by key.** The rule assumes
     every reader resolves through the manifest and re-renders on miss. Share tokens resolve to
     `(owner, playlist, video)` and re-derive, which is the reassuring case; the PDF and HTML serve
     routes must be checked rather than assumed. This is an *assertion to write*, not a note to
     remember — see the process rule about turning deferrals into tests.

  > **Two facts that shaped this, both checked 2026-08-05.** The saving here is smaller than it looks:
  > the PDF key is `pdfs/<base>.r<V>.<sha256[:16]>.pdf`, hashed on the rendered HTML, so an identical
  > re-render **collapses onto the same key and never accumulates** — copies appear only when content
  > genuinely changed. The HTML key (`htmls/<base>.html`) carries no version or hash and is overwritten
  > in place today, so per-generation HTML is accumulation this design *creates* rather than inherits.
  > The rule above is therefore chosen for **simplicity and a bounded footprint**, not because free
  > re-renders are a storage problem today.

- **Trigger — DECIDED 2026-08-05: scheduled sweep.** Follows from the retention rule: with paid blobs
  never collected and free ones bounded as above, collection is not urgent, so it does not need to be
  on any write path. A periodic sweep also keeps the money-sensitive classification in **one** place
  instead of at every writer.

> **Judgment recorded 2026-08-05 — these are ordinary costs, not a mark against the design.**
> Mark-and-sweep with a grace period is a standard, well-understood pattern, and the two OPEN items
> above are normal design work rather than risks. Noted because a review of the conditional-write
> slice framed them as a *cost* of adopting the manifest; that framing was over-weighted. The
> accurate reading is §8's own opening: the need already exists and is currently **unmet and
> unmeetable** — superseded dig blobs and old-base blobs accumulate today with nothing able to
> identify them. The manifest raises the accumulation rate and, for the first time, makes collection
> possible. Do not re-open this as an objection; close the two OPEN items as design work.

---

## 9. Concurrency scenarios — re-derived against this design

The process requires each gate to re-derive an inherited assumption. These are the exact interleavings
traced on 2026-08-02/03; each must be re-checked at review.

| Scenario | Today | Under this design |
|---|---|---|
| Worker `persist_summary` finishes while sync writes its Class-A block | **Lost update.** Same row fields, same blob key; whichever lands second wins, and a paid generation can be destroyed | Different generations ⇒ **no blob collision**, and card+body are one generation (§5.2) so neither can be torn from the other. Both writers **append**; neither overwrites |
| Dig job pins `base` at start, sync relocates during its Gemini call | Dig writes to a base the relocation **deleted** — orphaned, paid | No relocation exists. The dig publishes under its own generation |
| Two syncs (two machines, one account) | Unconditional writes interleave | Both append. **No CAS, no loser, nothing to re-run** — see the note below |
| ~~Two teammates generate for one video~~ | ~~n/a (no teams)~~ | ⟳ **ROW WITHDRAWN (round 1, M7).** It sold team concurrency that §11.1 disclaims and §13 scopes out. §9.1 retracted it and the table still asserted it — the exact contradiction §9.1's own closing argument warns about. |

> **⟳ ROUND 4 (Codex #12) — the table was still selling a CAS the design had already deleted.** Rows 1
> and 3 said *"the conditional write makes the loser retry"* and *"one manifest row, conditional
> write"*. There is no conditional write on the manifest and there is no one row: §5.1 is
> **append-only** and `current` is a **view**. A planner following the old table would have built a
> CAS-and-retry protocol against a table that cannot lose a write.
>
> **The correction is a dissolution, not a rewording, and it is worth the extra sentence.** Under a
> mutable pointer, two concurrent publishers are genuinely a race: one wins, one loses, and *"what
> re-runs the loser"* is a real question — it was open as **M4**. Under append-only there is no race
> to arbitrate. Both rows land, both are kept, and `current` is computed by ranking them whenever
> anybody asks. The winner stops being the outcome of an interleaving and becomes the result of a
> query, which is a property of the *set* and therefore identical for every reader, on every replica,
> forever. **M4 is not answered; it stops being a question** — the third finding this round to close
> that way rather than by being fixed.

### 9.1 Walk of each row — DONE 2026-08-05

§15 requires walking each row rather than accepting the table. Done. **Row 2 survives; rows 1, 3 and
4 do not, and row 1 is the serious one.**

**⚠ Row 1 — the scenario and the answer are about different things.** The scenario names a collision
on the **Class-A block**, which is `{ docVersionMajor, mdGeneratedAt, mdCorrectionsHash, mdHash }`
(`lib/cloud-sync/types.ts:32`) — **row scalars that describe the body, not the body**. The answer
given is *"different generations ⇒ no blob collision."* Generation-scoping the **body** does nothing
about two writers racing on the **card**. So the row claims a fix for a race it does not touch.

> This is §14 question 8 in concrete form, and it is why that question was a **prerequisite** and not
> a detail.
>
> **⟳ REPAIRED 2026-08-05 — Q8 is closed (§5.2: the card joins the generation), so the row can now say
> something honest.** Corrected reading: the worker and sync each produce a **whole generation** —
> card and body together, neither overwriting anything. ~~Both publish by conditionally updating one
> manifest row; the loser retries.~~ **⟳ ROUND 4:** both **append** a row; there is no loser (see the
> box above the walk). The scenario's actual failure, *a card describing a body it did not
> come from*, is **no longer expressible**, because resolving a generation yields both or neither.
> The row's original wording accidentally described this outcome while the design could not deliver
> it; it can now.
>
> **New measurement, 2026-08-05, and it constrains Q8's option B.** If the card stays on the row, a
> reader needs some way to ask *"does this card describe this body?"* — and **today there is no
> mechanism at all**. `mdHash` looks like one and is not: it is derived at read time from a body the
> caller passes in (`backfill.ts:11`, `deriveClassASignals(video, mdBody)`) and **is never persisted**
> — grep for `mdHash` across all 23 migrations returns **zero**. The durable whitelist
> (`0021:120-132`) stores `mdCorrectionsHash`, which hashes the **corrections**, not the body. So
> **option B is not "cheaper, no migration"** as §14 currently frames it: it requires *adding* a
> persisted body hash before the question it must answer is even expressible.

**✅ Row 2 — survives, with one qualification.** "No relocation exists" is true of *base* relocation,
which is the whole point of §4. Two relocations do survive and should be named rather than left to
contradict the row: the §10 migration is itself a one-time relocation, and §4's tenancy box admits
that an ownership change would move every object.

> **⟳ ROUND 6 — WHAT THIS DOES AND DOES NOT DO TO BACKLOG #17.** Row 2 is the reason the roadmap
> records #17 as possibly dissolved by this design. It is half right, and the halves are worth
> separating because the wrong reading would close a live money-path defect on paper:
>
> - **The ADDRESS race — #17's original shape — IS dissolved.** #17 is *"a stale worker persist lands
>   after an A3 relocation and orphans paid digs."* Under §4 the address is
>   `<ws>/videos/<vid>/<gen>/summary.md`, carrying neither serial nor slug, so there is no relocation
>   for a stale write to race with. Most of `2026-08-04-cas-fence-persist-summary-design.md` — five
>   rounds, 26 Blocking — is genuinely **moot**, not deferred.
> - **The RESERVATION race is NOT, and round 5 made it worse.** Round 6 MEASURED `P22`: a lease
>   expiring under a live worker, a second writer reclaiming, and **two paid Gemini calls in one
>   slot**. That was never about addressing, so nothing in §4 touches it. It is closed by §5.1.2's
>   protocol instead.
>
> **#17 is therefore NARROWED, not closed**, and this box says so rather than letting a checkbox
> claim otherwise. The residue is exactly the part that was never an addressing problem.

### 9.2 The reservation protocol — ⟳ ADDED IN ROUND 6 (H5 / Codex B2)

**Round 5 added a reclaim so a dead writer could not hold a slot forever, and the reclaim was not a
protocol.** Three defects were measured in ten lines: a return value that could not distinguish
*"nothing to reclaim"* from *"reclaimed something with zero attempts"* (shape #1, on the money path); a
terminal bound that was **resettable**, because reclaim and reserve were two round trips with nothing
atomic between them; and no way for a reclaimed writer to find out it had lost.

**The reviewer's fix was declined, deliberately, and the reasoning is the useful part.** H5 proposed a
`lease_token` that the record-flip must *match*, rejecting a reclaimed writer's record. Follow the
money: in `P22` **both** Gemini calls are already paid for by the time the first writer tries to
record. Rejecting it does not prevent the double charge — the charge happened at reserve time — it
discards one of the two things we bought. And under append-only that record is not a defect at all:
`video_artifacts_paid_uq` keys on `(slot, generation_id)`, so two recorded generations in one slot is
precisely what append-only *means*, and `current` ranks them on recorded facts.

> **Rule: the reservation guards SPENDING, not recording.** At most one writer may *start* a paid call
> per slot. A writer that already paid always records. **USER DECISION 2026-08-07.**

So `P22`'s two rows are the designed state, and the real defect is that **the lease expired while the
worker was still alive** — which renewal fixes and rejection does not. Renewal needs the token anyway,
since a reclaimed worker must not be able to renew the *new* holder's lease; so the token identifies
the holder rather than vetoing a record. That also supplies the channel H5 correctly said was missing,
and supplies it **earlier**: a failed renewal tells a worker it lost *while it is still working*, so it
can stop before spending more, instead of learning at record time when the money is gone.

**Three functions replace the reclaim** (`schema/04_artifacts.sql`), modelled on `reserve_serve_model`
(`0014:50-70`), which has been in production in this repo doing exactly this:

| | |
|---|---|
| `reserve_artifact_slot` | **One** upsert on the partial unique index → `reserved(token) \| busy \| exhausted \| already_recorded`. The attempt count is incremented **by the statement that takes the slot**, which is what makes the bound un-resettable |
| `renew_artifact_lease` | Fenced by the **token, not the clock** → `renewed \| lost \| ceiling_exceeded` |
| `record_artifact` | Flips in place when the token matches, otherwise **appends idempotently**. Never discards paid work |

**The round-5 reclaim regressed to `DELETE`-then-`INSERT` on a premise that does not hold.** It assumed
the expired row *"must stop existing before the next can be created"* — true of an INSERT against a
partial unique index, false of an **UPDATE**, which re-points the pending row without ever challenging
uniqueness. The append-only trigger does not fire on a `pending` row, so its `generation_id` is mutable
by design. Every one of the three defects followed from routing around a constraint that never applied.

**Renewal is bounded, or it re-creates the failure the reclaim exists to prevent.** A *hung* worker —
alive but not progressing — would renew forever and the slot would never be reclaimable. The ceiling
measures from a new `reserved_at` column, because `lease_expires_at` moves on every renewal and so
measures "time until I give up", never "how long this attempt has run". It reuses
`guardrail_config.max_duration_seconds` rather than inventing a number, and it is openly a
**heuristic**: a genuinely slow worker past the ceiling can still be reclaimed mid-flight and then we
pay twice. No protocol distinguishes *slow* from *stuck* from outside. What the design can do is make
that rare rather than structural, and never compound it by also discarding paid work.

**Two consequences recorded rather than left to be discovered:**

- **`summary_max_attempts = 1` means a crashed summary worker leaves a slot nobody can retry.** The
  first reserve sets `attempts = 1` and the bound is `< 1`. That is the money guardrail working as
  configured — *pay at most once* — not a protocol defect, and it is **not** overridden here, because
  a crashed worker may well have been billed. It is a product trade-off owned by whoever sets the
  guardrail numbers, `exhausted` is typed so a caller can surface it instead of hanging, and it is
  **asserted**, so raising the knob is a decision rather than an accident.
- **~~`record_artifact`'s signature is not final.~~ ⟳ SETTLED by item 3 — see §5.2.3.** It gained
  `md_hash`, `card`, `doc_version_major` and `p_produced_at`, and now creates the generation row in the same transaction.
  What is settled here is the **fencing semantics** of the flip; the payload belongs to item 3, which
  is sequenced last because it has already been specified-before-the-table-changed twice.

**⚠ Row 3 — inherits a claim this spec has already had to retract.** "One manifest row, conditional
write, loser re-runs" rests on the conditional write being sufficient. The five-round review of
`2026-08-04-cas-fence-persist-summary-design.md` established the opposite, and §5.1.1 already carries
the correction: the *write* is trivial, the **publish protocol around it is not**.

> **⟳ ROUND 4 — and the row is now moot rather than corrected.** This walk concluded *"row 3 must
> point at §5's publish protocol."* It no longer needs to point anywhere: append-only removes the
> conditional write the row was built on. Recording the sequence deliberately, because it is the
> clearest example in this document of the difference between the two kinds of progress — **round 3
> corrected the row (it was pointing at the wrong thing); round 4 deleted the thing it pointed at.**
> A correction that survives one round and is dissolved the next is not wasted work, but it is a
> signal that the premise under it was never examined. That is what the round-3½ classification step
> now exists to catch (`docs/dev-process.md`).

**⚠ Row 4 — describes a feature the spec has since disclaimed.** "Two teammates generate for one
video" sells team concurrency. §11.1 (added 2026-08-04, on the user's decision) says teams are **not
planned** and that naming the tenant buys exactly one narrow transition. Either drop the row or
re-label it explicitly hypothetical — as written it is the strongest team claim left in the document,
sitting in a table a reviewer reads as commitments.

**The pattern across three of four rows:** each was written on 2026-08-02/03 and each was invalidated
by a *later section of this same spec* — Q8, §5.1.1's correction, and §11.1 respectively. Nothing
external changed. That is what makes walking the table a real gate rather than a formality: a spec
edited section-by-section grows internal contradictions, and only a deliberate cross-read finds them.

---

## 10. Migration

### 10.0 Ordering — ⟳ ROUND 4 (J3-3): the producer fix lands BEFORE or WITH the card constraint, never after

**This is a prerequisite task, not a parenthetical**, and getting it backwards costs money on every
cloud summarize.

`gen_card_complete` requires a summary generation's card to carry `tldr`, `takeaways`, `docVersion`,
`mdGeneratedAt`, `processedAt` and `mdCorrectionsHash`. **The producer cannot satisfy it today**:
`lib/job-queue/summary-handler.ts:149-164` builds a `Video` with `docVersion` and `processedAt` and
**no `mdGeneratedAt`, no `mdCorrectionsHash`**. So if the constraint ships first, every cloud
summarize job fails its insert — **after** the Gemini call has been made and paid for. The user is
charged, the bytes are produced, and the row that would have recorded them is rejected.

| Order | Result |
|---|---|
| Constraint, then producer | every summarize pays for a generation it cannot record |
| Producer, then constraint | correct — the producer emits complete cards before anything requires them |
| Same migration | correct |

**⟳ ROUND 6 (B5 / Codex B3) — THIS SECTION LISTED THE CARD FIELDS AND OMITTED `md_hash`, WHICH IS THE
FAILURE IT EXISTS TO PREVENT.** `gen_summary_has_hash` made `md_hash` mandatory for a summary
generation and *nothing anywhere computed it* — the mechanism was sitting unused two files away
(`lib/cloud-sync/content-hash.ts:16` exports `mdHash()`, and `core.mdContent` is in scope at
`summary-handler.ts:172`). The same applied to `doc_version_major`, which `gen_major_matches_card`
ties to the card. A section that enumerates a producer's obligations is only as good as its
enumeration, and the omission survived four review rounds because every reader checked the *ordering
argument* rather than the *list*.

**Measured, and worse than the ordering table describes.** Once the round-6 reservation protocol
landed, the two rules together were not merely mis-ordered — they were **unsatisfiable in both
directions**, so a cloud summarize could not reserve its slot at all:

| Attempt | Result |
|---|---|
| Reserve, then create the generation | `[23503]` — the artifact's FK needs the generation to exist first |
| Create the generation, then reserve | `[23514] gen_card_complete` — it cannot exist before Gemini has run |

The paid call sits between those two. That is a *safer* failure than the one this section predicted
(nothing is charged), but it is a dead feature rather than an expensive one. §5.2.3 is the fix.

**Three producers, not one** — `lib/job-queue/summary-handler.ts`, `lib/cloud-sync/sync-run.ts` and
`lib/storage/worker-persistence.ts`. Each must supply `md_hash`, `card` and `doc_version_major` to
`record_artifact`; sync must additionally carry `p_produced_at` rather than let it default.

**Round 4's J1-2 makes this sharper rather than softer, and that is worth understanding.** The
round-3 constraint failed *open* on `card = NULL` (a `CHECK` passes on NULL), so a producer emitting
no card at all would have slipped through silently — the ordering bug would have been invisible and
the data merely wrong. Fixing J1-2 to fail closed makes the same bug **loud**. Both orders were
always wrong; only fixing the fail-open made the wrongness observable, and only the sequencing
statement makes it safe. **A guard becoming correct can turn a silent data defect into a loud outage
— which is the right trade, and is exactly when a sequencing statement stops being bureaucracy.**

### 10.1 Blob migration

Every existing blob moves exactly once, from `<owner>/<playlist>/<base>.*` to the new layout.

`reconcileCloudBase` (`lib/cloud-sync/reconcile-serial.ts`, built on `fix/serial-coherence-sync`) is
**precisely** the machinery this needs: plan → copy with sources retained → verify → update metadata →
delete best-effort, with fail-closed refusals on ambiguity. It gets **used as the migration tool, then
retired**. This is the concrete reason to merge that branch before starting this work.

Local migration is a rename to the human-readable display name, which
`lib/serial-migrate.ts` / `serial-migrate-exec.ts` already do (two-phase, dry-run default,
clobber-safe).

---

## 11. Workspaces, tenancy and teams

**⟳ Round 2: `workspaceId` is opaque, and no predicate may compare it to `auth.uid()`** — see §5.0, which
settled this. Earlier drafts of this section said the value was `auth.uid()` today; that position was
replaced because it grants the creator unrevocable access and forces a whole-corpus blob migration
later. §11.0 describes the *grouping* concept. **Teams are exploration only** — not on the roadmap (user decision, 2026-08-04). Nothing here is
built; this section exists so a future reader inherits the facts instead of the guesses.

### 11.0 Why the segment is a `workspaceId` — settled 2026-08-05/06

Three candidate names were worked through, and two were rejected for the *same* reason:

| Name | Verdict |
|---|---|
| `workspaceId` | **Ambiguous.** This app is *already* multi-tenant — that is what the RLS is for — so "tenant" already means *the per-user isolation boundary*. `CONTEXT.md` even glossed it that way (*"Owner — the tenant a Principal represents"*). Reusing the word for the path segment gives it two meanings. |
| `teamId` | **Names who may access.** Clearer than `workspaceId`, but a team is exactly the thing that changes, so putting it in the address reproduces §1's bug one level up. |
| `ownerId` | **Names a person.** People are the most mutable thing in the system — they leave, and they delete their accounts. |
| **`workspaceId`** | ✅ **Names the container.** Containers do not change hands; their *membership* does. Immutability becomes true by definition rather than by assumption. |

**The rule this encodes:** the path segment's only job is to be **permanently stable**. Anything that
names *who may access* is unfit for an address, because access is what changes.

**A workspace is a user-chosen grouping of playlists**, not fixed at one-per-user or one-per-playlist.
That single knob decides two things at once, and the design already supports it: the manifest is keyed
`(workspace, video, slot)` with **no playlist**, so **two playlists in the same workspace sharing a
video resolve the same manifest row and therefore one copy of the blobs.**

| Workspace size | Blob dedup | Sharing granularity |
|---|---|---|
| one per playlist | none across playlists | fine |
| one per user | full | all-or-nothing |
| user-chosen grouping | within the workspace | per workspace |

> **The rule in one line: things you share together, you store together.**

Three consequences, stated rather than discovered later:

1. **The dedup boundary and the sharing boundary are the same knob.** You cannot have fine-grained
   sharing *and* dedup across that line. Acceptable, but it is a coupling, not a free lunch.
2. **A workspace changes hands for free; a playlist inside one does not.** Moving a playlist to another
   workspace requires **copying** its videos' blobs — copying, not moving, if another playlist in the
   old workspace still references the same video. A deliberate user action, not a background race.
3. **Deleting a playlist needs a LOCKED, TRANSACTIONAL unreference — reference counting alone is racy.**
   ⟳ *Round 1 (Codex B2 / Claude M2).* Counting references and then deleting is a TOCTOU: the count for
   video V returns zero, an ingest or sync adds V to a sibling playlist in the same workspace, and the
   shared manifest row and blobs are deleted out from under it. The current delete makes this worse —
   `route.ts:73-79` commits the playlist delete and does the blob work **afterwards, unlocked**. And per
   §5.0 the reference source is `videos` rows across the workspace's playlists, which is only
   enumerable now that `playlists.workspace_id` exists.

   **Rule:** never count in the app and delete in the app. Express the unreference as a **single
   transactional statement** alongside the playlist delete — `delete from video_artifacts where … and
   not exists (surviving videos row)` — inside one `security definer` RPC that locks the workspace's
   reference set. Bytes follow later via the sweeper's grace period (§8).

   > **⟳ ROUND 2 (High, Codex) — "locks the reference set" named no lock, so it excluded nothing.**
   > Ingest today locks only its own **playlist** row (`0009:79-96`), so a delete of P1 and an ingest
   > into P2 touch disjoint locks and the TOCTOU survives verbatim. **Both paths must take the SAME
   > lock**, and the only key both share is the video: a transaction-scoped advisory lock on
   > `(workspace_id, video_id)` — `pg_advisory_xact_lock(hashtextextended(workspace_id::text || video_id, 0))`
   > — taken by `claim_video_slot`/ingest **and** by the unreference RPC. A rule that says "lock"
   > without naming the lock is not a rule; it reads as fixed and changes nothing.

   Superseded original wording: **Deleting a playlist needs REFERENCE COUNTING, not just enumeration.** Today
   `DELETE /api/playlists/[id]` ends in `deletePrefix(principal, '')`; in a multi-playlist workspace
   that sweep destroys the other playlists' blobs. This sharpens the §4 finding: the delete path must
   walk the manifest **and** check whether any surviving playlist still references each video.

> **⟳ ROUND 1, High H5 / Codex H2 — there are TWO playlist-keyed money arbiters, and this section named
> only one.** The paragraph below cited `jobs_idem_active`, which is the **queue**. The magazine model is
> charged on the **serve** path by a *different* arbiter, also keyed on playlist:
> `v_doc_key := p_playlist_id::text || '/' || p_video_id` (`0020:213`), against
> `serve_model_charge (owner_id, doc_key, day)` with the K-attempt bound and the per-owner daily cap
> (`serve_owner_budget`, `0014:6-10`) around it. That is the whole of the Stage 1G/G1 fairness cap.
>
> **The failure this design would ship:** one video in N playlists of one workspace resolves **one**
> manifest slot for `model`, but each playlist keeps its own `doc_key`, hence its own daily lease and
> its own `max_serve_attempts` budget against that single shared slot. **G1's cap becomes N times
> looser**, and each attempt mints a new generation and re-points the manifest, so N−1 paid models go
> not-current and start their 90-day clock. Storage dedup and spend dedup must agree or the workspace
> knob is a money regression.
>
> **⟳ ROUND 2 (High, Codex) — re-keying `doc_key` ALONE breaks the serve path completely.**
> `reserve_serve_model` gates on `v.data->'artifacts'->'summaryMd'->>'status' = 'promoted'`
> (`0020:204-207`). Once summary authority moves to the artifact manifest that JSON stops being
> maintained, the check sees nothing promoted, and the RPC returns **`denied` for every model
> generation** — the magazine view dies for all users. The readiness predicate must be re-derived
> against the manifest (a `current` `summary` slot resolving to a readable blob), and the whole
> 0020 reserve/settle protocol re-stated in those terms. Re-keying is the smaller half of this work.
>
> **Rule: enumerate EVERY arbiter keyed on playlist and state what each is re-keyed to.** There are two:
> `jobs_idem_active` (`0009:11-13`) and `serve_model_charge.doc_key` (`0020:213`). Both re-key to
> `(workspace_id, video_id)`. A future arbiter that keys on playlist is a defect by construction, and
> that belongs on the review checklist beside §8's key-shape rule.

**Storage dedup is free; spend dedup is not.** Sharing the bytes falls out of the manifest key. *Not
charging twice* still requires §14 Q6 — `jobs_idem_active` includes `playlist_id` (`0009:11-13`), so a
second playlist enqueues a paid summarize job even when the blob already exists. **This granularity
choice is what actually decides Q6**, which the spec had listed as optional.

### 11.1 What naming the segment buys — corrected twice

An early draft claimed the name makes *"teams later a predicate change instead of a migration of every
object key."* A 2026-08-04 correction withdrew that as too broad, on the grounds that a project joining
an *existing* team still moves every object.

**⟳ That correction was itself wrong, and is now withdrawn (2026-08-06).** It assumed **authorization
must read the path**. It does not. With membership-based authorization (§11.2) the workspace keeps its
id forever and *the team gains access to it* — content never migrates to the team's id. So:

| Transition | Blobs move? |
|---|---|
| A workspace gains members | **No** |
| A workspace joins an existing team | **No** — grant the team access to the workspace |
| A **playlist** moves to a different workspace | **Yes** — see §11.0 consequence 2 |

The residual cost is real but small and bounded, and it lands on a deliberate user action rather than
on a sync race.

### 11.2 If teams ever ship: membership, never identity

**The one rule that survived four rounds of review of this design (external draft + critique, 2026-08-05/06):**

> **Never let *being someone* grant access. Let *membership* — or an explicit, revocable
> *capability* — grant access.**
>
> ⟳ *Invariant evaluation 2026-08-06: the rule previously said "membership" alone, and this project
> already has a third mode in production. A **share token** is a bearer capability: `lib/share/serve.ts:19-24`
> reads `revoked_at` through `serviceClient`, bypassing RLS entirely. It satisfies the rule's spirit
> — **revocability** — while violating its letter. Stating the rule as "membership" makes a correct
> design look like a violation, which invites someone to "fix" it. **The load-bearing property was
> always revocability, not membership specifically.**

Every iteration that tried to solve the creation-bootstrap problem with an identity fallback —
`created_by = auth.uid()`, or `split_part(name,'/',1) = auth.uid()::text` — re-created the same defect:
**an identity-based grant cannot be revoked.** A creator who leaves the team keeps read, write and
delete forever, because removing their membership row does not touch the `OR` clause that names them.

**The resolution is atomic creation, not a fallback clause.** A `security definer` RPC inserts the
artifact *and* its first ACL row in one transaction, so there is never a window in which content has no
grant — which is the gap every fallback was patching. `created_by` reverts to **audit only**, with
`on delete set null` so a user can actually be deleted.

**Consequence for this design:** the **predicate** must stop comparing the path segment to
`auth.uid()`. The existing fast path `split_part(name,'/',1) = auth.uid()::text` grants the creator
their own workspace unconditionally and forever, and no membership clause can undo it — an `OR` cannot
be revoked. **So the RLS predicate changes on day one, not "someday."**

> ⟳ **Round 2 — two corrections, in opposite directions.** An early draft said keeping
> `tenantId == auth.uid()` costs nothing: wrong, the predicate really must change. A later draft then
> said the workspace **id** must never equal a uid: also wrong, and expensive — that version forced a
> whole-corpus re-key. **The id may coincide with a uid; the predicate may not compare to one.**

**Shape** (adapted to `storage.objects`, which has no joinable id — the policy sees only `name`):

```sql
create function workspace_member(p_ws text) returns boolean
  language sql security definer set search_path = public stable as $$
  select exists (select 1 from workspace_grants g
                 join team_members m on m.team_id = g.team_id
                 where g.workspace_id::text = p_ws and m.user_id = auth.uid());
$$;
revoke all on function workspace_member(text) from public;
grant execute on function workspace_member(text) to authenticated, anon;
```

**Four hard-won constraints on that shape:**

- **Never cast the path segment** — `g.workspace_id::text = p_ws`, never `p_ws::uuid`. `uuid::text`
  always succeeds; `text::uuid` raises on one malformed name, and inside a policy an error does not deny
  one row, it **fails the whole query for everyone** (§3). One `_staging/` object is enough.
- **Call the helper; never inline the `exists`.** Inlining re-evaluates the ACL tables under *their*
  RLS, which nests policy evaluation several levels deep per row — the exact fragility `security
  definer` exists to remove.
- **Take no user-id parameter.** A definer function accepting an arbitrary uid lets any caller enumerate
  who can access what. Read `auth.uid()` inside, and `revoke ... from public`.
- **Cover all four verbs.** A `for select` policy alone denies every write — ingest, worker, staging,
  promotion.

**Two facts that make this affordable, measured on the live stack:**

- **Cost is a non-issue.** Name-anchored access measured **0.118 ms** (download one object) and
  **0.234 ms** (list one prefix). The 175 ms parallel seq scan appears only for an unanchored query the
  app never issues. `IN (subquery)` and correlated `EXISTS` plan **identically** — same semi-join, same
  45 buffers. **Therefore path granularity is a domain-architecture choice, not a database constraint**
  — do not justify a path shape by claiming joins are slow.
- **`storage.objects` also carries `owner_id text`** (plus `owner uuid`, `user_metadata jsonb`), so a
  policy can key on a **column** rather than the path. Precondition: `owner_id` is set on only **390 of
  973** objects locally, because `service_role` writes leave it NULL. Where set, it equals path segment
  1 in **390/390** cases, so a backfill is `set owner_id = split_part(name,'/',1)` — but every writer
  must populate it thereafter.

**Precedent already exists in this codebase.** `lib/share/serve.ts:32` reads owner blobs via
`serviceClient` because the equality predicate cannot express "this anonymous visitor may read owner
A's object." Team reads could take the same route, leaving storage RLS as the fast path. The product
already outgrew storage RLS on one path.

### 11.3 What real team support would additionally require

**Explicitly out of scope, recorded so it is not discovered late:**

- **Every RLS predicate converts** from a string comparison to a membership lookup, on
  `storage.objects` *and* on `profiles`, `playlists`, `videos`, `jobs`, `usage_counters`. This changes
  isolation from "by construction" to "by a table that must be correct." On our own tables that is
  clean — they have an owner column to join on.
- **Recursion is a real trap.** `team_members` needs its own policy, and the obvious one queries
  `team_members` (`infinite recursion detected in policy`). The `security definer` helper fixes it and
  thereby *becomes* the security boundary for the whole app, replacing a string equality that cannot be
  wrong with a function that must be audited.
- **Destructive verbs need a role check.** Any-member `delete` on paid Gemini output is the money path.
  Narrow `delete` (rows and ACL entries) to a team admin.
- **Content must stop hanging off a person.** Today `playlists.owner_id → profiles → auth.users` is
  `on delete cascade` (`0001:3`), so **deleting an account destroys its playlists and videos** — live
  today, teams merely make it visible. Under a team model, content hangs off the workspace and survives.
- **Two events, two answers.** *Leaving a team* removes a membership row and touches no content.
  *Deleting an account* must not take the team's content with it. The code currently gives them the same
  answer.
- **The empty team is undecided.** If a team empties — or loses its last admin — its content becomes
  permanently unreachable by anyone: not deleted, just invisible, which under the 90-day clock (§8) is
  worse than deleted because nothing reports it. Three candidates: refuse the last removal, require
  transfer first, or mark the workspace ownerless and start the retention clock. Refusing the last
  removal is the only one that cannot silently lose paid content.
- **Who pays.** `spend_ledger`, `quota_allowance` and `serve_owner_budget` are per-owner, and the entire
  cost-guardrail system (1D, ADR-0004) keys on that identity.
- **Write-sharing is a different problem from read-sharing.** `share_tokens` already solves the latter
  and deliberately never creates a second owner. Worth noting it is **ahead of the standard advice**: it
  has no anon/authenticated policy at all (`0013:18`), goes through `security definer` RPCs, and stores
  a **hash** rather than the token — so the classic "put `expires_at > now()` in the policy and let
  anyone scrape every shared row" trap is avoided by construction.

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

## 12b. The caller's obligation (round 11)

Everything the reservation protocol guarantees rests on **one rule about callers**, and it is stated
here because two rounds tried to enforce it in SQL instead and each attempt was that round's worst
finding.

> **A worker MUST hold its reservation token for the life of the job. A worker that cannot present
> it MUST abandon rather than record.**

There is no fallback, no second credential, and no recovery path. `record_artifact` completes a
generation only for `reserved_by = p_token`.

**Why the rule is safe rather than harsh** — the party that holds paid bytes always still holds the
token, because the two live in the same process memory:

⚠ **Corrected in round 12.** An earlier version of this table said a worker that loses its lease
"stops", full stop. It does not: the runtime *signals*, and a handler is free to ignore the signal
and return. That is safe for two independent reasons, and stating only the first was the same
over-claim this section exists to warn about. A handler that ignores the abort still holds its
artifact token, so it lands on `recorded_after_loss` — the designed path for a writer whose slot was
reclaimed — and its *job* completion is refused by `complete_job`'s own fence. The obligation below
is therefore about the token, not about obedience to a signal.

| Event | What happens to the bytes | What happens to the token |
|---|---|---|
| process crashes | lost with the process | lost with the process — nothing to record |
| lease expires | the handler is **signalled** — `lib/job-queue/worker-runner.ts` heartbeats every third of a lease and calls `leaseLost.abort()` into the handler's `AbortSignal` — and a handler that ignores it cannot land a terminal success anyway, because `complete_job` filters on `locked_by`/`lease_token`/`status='active'` and `sweep_expired_leases` nulls all three | still in hand → records via `recorded_after_loss`, which is the designed outcome |
| slot reclaimed while the worker runs | still in hand | still in hand → records via `recorded_after_loss` |

**The two failed attempts, kept as a warning.** Round 7 accepted *"the slot's pending row names this
generation"*; round 8 measured a stranger satisfying it. Round 9 accepted a durable
`(worker_id, job_id)` pair; round 10 measured a stranger **reading it out of the row it fenced**, and
also that `worker_id` is regenerated per process (`worker/main.ts:69`), so no honest worker could use
it either. Both fallbacks existed for a caller that cannot occur.

**Enforced, not remembered:** `tests/lib/blob-addressing-caller-contract.test.ts` asserts these
premises against `lib/job-queue/worker-runner.ts` in the CI-covered suite. It is mutation-checked —
removing the lease-loss abort turns it red — so a refactor that adds auto-reconnect or job resumption
fails there rather than silently invalidating this section.

Premise tags for this section, per `docs/review-method.md`:
`[VERIFIED: lib/job-queue/worker-runner.ts:47-53]` heartbeat → `leaseLost.abort()` into the handler's
signal · `[VERIFIED: worker/main.ts:69]` `worker_id` is per-process, NOT stable · `[VERIFIED:
supabase/migrations/0008_jobs_queue.sql]` `sweep_expired_leases` nulls `locked_by`/`lease_token`.

**When the cloud caller is written**, extend that contract test to it — that the token is held for the
job's duration, and that a worker which loses it abandons.

## 13. Out of scope

- Actual **team** support (§11) — ⟳ *narrowed in round 1*: the **workspace table itself is IN scope** (§5.0, one per user, opaque id, plus the `workspace_readable` predicate). Out of scope: multiple workspaces per user, `workspace_members`, ACLs, the atomic-creation RPC, and role checks.
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
   **Amended 2026-08-04 (§4.2.1): there are THREE dimensions, not two.** The third is the section
   **title**, used as an identity anchor in `mergeDigDoc`'s step-2 fallback and in `sameTitles`. It
   *does* dissolve under generation-scoping — but only because §6's span-overlap rule replaces it,
   which promotes question 3 from a tuning detail to a **prerequisite**.
3. ~~**Overlap threshold**, and the section-merge ambiguity (§6).~~ — **CLOSED 2026-08-05 (user
   decision, §6.1): when it is ambiguous, leave it unattached; never guess.** Attach only when the
   match is unambiguous in **both** directions — exactly one section overlaps the dig, *and* exactly
   one dig claims that section. Threshold **0.8 in both directions** — `overlap / dig_span ≥ 0.8`
   **and** `overlap / section_span ≥ 0.8` — tunable upward only.
   **Closing it exposed a gap in §6:** the section-**split** case was never named, and it is
   ambiguous from the *dig's* side rather than the section's — a rule written only against the merge
   example would have missed it. This was the last prerequisite; **all three are now closed.**

   > **⟳ ROUND 4 (Codex #13) — this line said "0.8 of the dig's own span", which is the ONE-sided rule
   > §6.1 had already replaced.** One ratio cannot detect a section **merge**: a dig covering
   > `[100,170)` sits entirely inside a merged section `[100,300)`, so `overlap/dig_span = 1.0` and the
   > one-sided test attaches it to a section it describes a third of. An implementer reading the
   > closed-questions list — which is exactly what someone planning the work reads — would have shipped
   > the bug §6.1 exists to prevent.
   >
   > **The shape worth naming: a summary of a decision is a second copy of it.** §6.1 was fixed; this
   > line summarises §6.1 and was not. Every "closed questions" list, ADR consequence and status table
   > in this document is a cache of a decision written elsewhere, and caches go stale silently. Both
   > of round 4's English-only findings (this and Codex #11) are exactly that, and both were found by
   > grepping for the *value* rather than re-reading the prose.
4. ~~**Retention policy and GC trigger** (§8).~~ — **CLOSED 2026-08-05 (user decision, §8).**
   *Not current ⇒ delete, except paid, which is retained **90 days** past the moment it stopped being
   current.* Trigger: scheduled sweep. A duration rather than a generation count, because a count
   evicts by activity and bursts of activity are when mistakes happen. This was one of the three
   **prerequisites**. With Q8 also closed the same day, **Q3 is the only prerequisite left.**

   Four constraints outlive the decision, all recorded in §8:
   - the paid/free split must be readable from the **key alone** (an orphan has no manifest entry);
   - the grace period is checked **before** the kind;
   - the free-blob serve paths must be *asserted*, not assumed;
   - **an explicit delete outranks retention** — a correctness rule, and one that depends on the
     §4 finding below, since today's hard-delete does not survive the new path template.

   **⚠ Surfaced while closing this question — a NEW item, not a sub-question of Q4** (§4): removing
   `<playlistKey>` from the path breaks `Principal.indexKey`, which every `objectKey`, `list` and
   `deletePrefix` composes its root from. Playlist hard-delete is a prefix sweep over exactly that
   root, so it must become **manifest-driven enumeration**. Uncosted work, on the delete path, with a
   silent failure mode. Q4's answer is not blocked on it; the *plan* is.
5. **Offline local generation** — the upload-then-publish path (§7).
6. ~~**Cross-playlist dedup: in or out?**~~ — **CLOSED 2026-08-06 by §11.0's granularity decision.**
   ⟳ *Round 2, High N-H7: this was settled in a §11.0 footnote while §14 still listed it open — and it
   was flagged elsewhere as "the single largest risk", so a footnote is the wrong place.* **It is IN.**
   With one workspace per user (§5.0), every playlist that user owns shares the manifest key, so storage
   dedup is a property of this design and not an option. Spend dedup follows: **both** playlist-keyed
   arbiters re-key to `(workspace_id, video_id)` — `jobs_idem_active` (`0009:11-13`) and
   `serve_model_charge.doc_key` (`0020:213`).

   **§12's replacement cross-tenant guard, still owed and now written.** The existing guard is the
   composite FK `jobs(playlist_id, owner_id) → playlists(id, owner_id)` (`0009:5-6`), which works only
   because `playlists` carries `unique (id, owner_id)` (`0001:18`). Re-keying on workspace needs the
   same shape one level up: `workspaces` carries `unique (id, owner_id)`, and `jobs` gains
   `foreign key (workspace_id, owner_id) references workspaces (id, owner_id)`. That preserves ADR-0002's
   injection guard verbatim — a job can never name a workspace its owner does not own.

   > **⟳ ROUND 3 (B-6 + B-7) — this guard did not create, and its column could not be added. Both are
   > repeats.** B-6: the FK needs `workspaces unique (id, owner_id)`, which I omitted — *round-2 C2
   > verbatim, inside the fix that closed Q6*. B-7: `jobs.workspace_id not null` aborts on a populated
   > table — **physical rule 4, which I fixed for `playlists` in round 2 and never re-derived for its
   > sibling.** Same three-phase shape: add nullable → backfill from
   > `playlists.workspace_id` via `jobs.playlist_id` → set `not null`.
   >
   > **The pattern is worth more than either fix.** A *physical* constraint I had already been bitten
   > by, written down in the rules inventory as rule 4, recurred twice more because I applied it to the
   > table in front of me and not to the class of tables. **A physical rule applies to every site, not
   > to the site where you learned it** — that belongs in the inventory, not in three separate fixes.

   Superseded question text: **Cross-playlist dedup: in or out?** (§12) — determines whether `jobs` and the 1D reservation are
   touched. The spec is coherent either way; the saving only materializes if `playlist_id` leaves the
   job identity.
7. **Do the two seam-bypassing writers get fixed or scoped out?** `companion-doc.ts:448` writes
   dig-deeper markdown with raw `fs`; `slides.ts:221-230` prunes assets with `fs.readdirSync`/
   `unlinkSync`. Both touch blobs the manifest must track.
8. ~~**Do the Class-A scalars become generation-scoped, or stay on the row?**~~ — **CLOSED 2026-08-05
   (user decision): the card joins the generation. Design in §5.2.** The deciding evidence was the
   measurement below — the "cheap" option was not cheap, so both options cost a schema change, and
   only one makes the incoherence *impossible* rather than merely *detectable*. That mattered because
   the readers that currently do not check (`deriveClassASignals`, the quick-view route) are exactly
   the ones that would keep not checking. Knock-on effects: §5.1.1's scope box retired, §9 row 1
   repaired, and §2's definition of *Generation* must change (a run produces a body **and its card**,
   inseparably). Original question retained below for the reasoning trail.

   **Was: added 2026-08-05, surfaced by the conditional-write slice** (`2026-08-04-cas-fence-persist-summary-design.md`, five
   review rounds).

   A summary is **two** things: a **body** (the blob) and a **card** (`tldr`, `ratings`,
   `overallScore`, `takeaways`, `videoType`, `audience`, `docVersion`, `mdGeneratedAt`,
   `mdCorrectionsHash` — the summary-owned whitelist at `0021_cloud_sync_signals.sql:120-132`). Both
   are produced by one Gemini run.

   **This design generation-scopes the body and says nothing about the card.** Blobs become immutable
   per generation and never collide (§5.1.1); the card keeps living in one slot on `videos.data` and is
   still overwritten in place. So **"run #2's card beside run #1's body" remains expressible** — a
   catalogue entry updated to the second edition while the shelf still holds the first. Every field
   reads consistent; the body isn't the one described.

   That is not hypothetical. It is the exact state behind the conditional-write slice's B-R4-1: new
   `tldr` and `docVersion` on the row, old bytes at the key, and **nothing able to tell they came from
   different runs** — which then satisfied the idempotency skip (`summary-handler.ts:86-92`) and froze
   the row permanently. A reader of §5.1.1 would reasonably conclude this design fixes that. **It does
   not.**

   Two defensible answers, and the spec must pick one:
   - **Card joins the generation** — card and body always travel together; the incoherence is gone by
     construction, and the idempotency skip gains a truthful thing to key on. Costs a schema decision
     about where the card lives and how a reader resolves it.
   - **Card stays on the row** — ~~cheaper, no migration of scalar storage~~, but then the spec must
     state what a reader does when the card is **newer** than the authoritative body, and which
     readers are allowed to observe that split (`deriveClassASignals` in `backfill.ts` reads
     `docVersionMajor` independently of body hash; the quick-view route serves `tldr` without checking
     body coherence).

     > **⟳ Measured 2026-08-05 (§9.1) — this option is NOT the cheap one.** Answering *"does this card
     > describe this body?"* needs a persisted hash of the body, and **none exists**: `mdHash` is
     > derived at read time from a body the caller supplies (`backfill.ts:11`) and appears in **zero**
     > of the 23 migrations. The durable whitelist (`0021:120-132`) stores `mdCorrectionsHash` — the
     > **corrections** hash, not the body's. So option B needs a schema addition before its own
     > question is expressible, which removes the main reason to prefer it.

   **Not choosing is the one unacceptable option**, because §5.1.1's *"this answers the concurrency
   problem"* currently implies coverage the design does not provide.

   Related: this question also decides whether §5.1.1's claim that a conditional write is *"trivially
   sufficient"* survives — see §15.

---

## 15. Verification

This spec is verified by review, not by tests. Before it becomes a plan:

- ~~`grill-with-docs` terminology pass~~ — **DONE 2026-08-06.** Nine terms landed in `CONTEXT.md`
  (*tenant, workspace, generation, card, slot, manifest, authoritative, display name, membership-not-
  identity*). **It was not paperwork — it changed the design:**
  - **Five collisions with established vocabulary**, all verified in code. ⟳ The fifth (*manifest* — see §2) was **missed by the pass and found by round-1 review**, which is the honest record: this list previously said four and claimed the pass caught them. *Slot* already meant a
    video's reserved position in a playlist (`claim_video_slot`); *rendering* already meant
    summary→HTML/PDF (`renderMagazineHtml`, `PDF_RENDER_VERSION`, and the whole source-vs-derived split)
    — **renamed to display name**; *tenant* was already `CONTEXT.md`'s gloss for **Owner**; and
    *authoritative* needed separating from *source-of-truth blob*.
  - **One self-contradiction six hours old.** §2's `Card` row listed all twelve scalars while §5.2.1
    had just split them.
  - **The path segment was renamed** `tenantId` → `workspaceId`, and §11.1's pessimism about teams was
    withdrawn as itself wrong (§11.0/§11.2).
  This is why the pass runs **after** the open questions and **before** the review: Q8 changed what
  *Generation* means, and running it earlier would have written the definition wrong.
- Dual adversarial review (Codex + Claude, independent) **to convergence** — mandatory here: this
  touches schema, identity, and the money path.
- ~~**Re-verify every fact in §3 against live code.**~~ — **DONE 2026-08-05.** 16 facts checked
  against `master` @ `7e142f6`; **13 survived verbatim, 3 citations corrected** (marked ⟳ in §3), and
  **zero *facts* were found false — though round 1 showed one of my own *corrections* was wrong** (see the RLS row). Verified this round, each by reading the cited code:

  | Fact | Result |
  |---|---|
  | Bucket `artifacts` private, no size/MIME limit | ✅ `0007:4` |
  | RLS predicate, text-to-text, fails closed on NULL/empty | ✅ ⟳ line range `12-15` (my first correction said `13-16` — wrong at both ends; see below) |
  | Object path `<ownerId>/<playlistKey>/<key>` | ✅ `objectKey`, line 17 |
  | Five Storage API operations | ✅ ⟳ seam now has a 6th, `copy`, not built on the API's |
  | Nine blob kinds, all key shapes | ✅ all nine grep-confirmed |
  | Paid/free split location | ✅ ⟳ moved to `paidKeysUnder` / behavior #3 |
  | Slide assets keyed on `videoId`, not `base` | ✅ `slides.ts:185` |
  | PDF key carries a content hash | ✅ `pdf-render-version.ts:22` |
  | Model envelope overwrites in place | ✅ `model-store.ts:51` — a bare `put`, no versioning |
  | Version constants compared to compile-time values | ✅ `docVersion 3.3`, `DIG_GENERATOR_VERSION 9`, `PDF_RENDER_VERSION 1` |
  | **Zero** team/workspace/org concept in `lib/` + migrations | ✅ grep empty |
  | `share_tokens` never creates a second owner | ✅ `0013` (+`0017`, `0019` cascade — no owner change) |
  | Exactly one row per `(playlist_id, video_id)` | ✅ `0001:30`, the primary key |
  | `jobs_idem_active` carries `playlist_id` (ADR-0002; §14 Q6 depends on it) | ✅ `0009:11-13` |

  **The one methodological lesson, worth keeping past this spec:** all three corrections were stale
  *line numbers*, none were stale *facts*. Cite the symbol; let the line number be a hint.
- ~~Walk each row of §9 explicitly during review rather than accepting the table as written.~~ —
  **DONE 2026-08-05, and it earned its cost: 3 of 4 rows did not survive** (§9.1). Row 1 answers a
  *scalar* race with a *blob* fix and must wait on Q8; row 3 rests on the sufficiency claim §5.1.1
  already retracted; row 4 sells team concurrency §11.1 disclaims. All three were invalidated by
  **later sections of this same spec**, not by anything external.
