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
| **Workspace** | The immutable container a video's blobs are addressed under, and the first path segment. A **user-chosen grouping of playlists** — one per playlist, one per user, or anything between (§11.0). Its id **never changes**; what changes is who may access it. Chosen over *tenant* (already means the per-user boundary), *team* and *owner* (both name **who may access**, which is exactly what changes). Today its value is `auth.uid()`, but if teams ever ship it must become an independent UUID — an id equal to a uid grants its creator unrevocable access (§11.2). |
| **Generation** | One production run of a paid artifact — a summarize run, or a dig run — **and everything that run produced: for a summary, both the body (the blob) and the card (the scalars), inseparably** (§5.2, decided 2026-08-05). Identified by an opaque, immutable `generationId`. Nothing in a generation is ever overwritten. |
| **Card** | The **document facts** a summarize run produces alongside the body: `tldr`, `takeaways`, `docVersion`, `mdGeneratedAt`, `processedAt`, `mdCorrectionsHash`. An attribute **of the generation**, never of the video — that distinction is the whole of Q8. **Does NOT include the video judgments** (`ratings`, `overallScore`, `videoType`, `audience`, `language`, `tags`): §5.2.1 keeps those on the video, because they describe the *video*, which a regeneration did not change. ⟳ Corrected in the terminology pass — the first draft of this row listed all twelve scalars and contradicted §5.2.1. |
| **Slot** | A *logical* artifact position for a video: `summary`, `model`, `dig:<sectionId>`, `digDeeper`, `pdf:<kind>`, `slide:<id>`. What a reader asks for. |
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
<workspaceId>/videos/<videoId>/assets/<sectionId>-<start>-<end>.jpg
```

Four properties, each load-bearing:

**`<workspaceId>` stays first** — the RLS predicate requires it. Today it is literally `auth.uid()`, so
the bytes are unchanged from the current layout and **the predicate needs no edit**.

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

## 5. The manifest

The per-video mapping from **slot → blob key**. This is the only mutable state in the design.

```
video_artifacts
  workspace_id  uuid    not null
  video_id      text    not null
  slot          text    not null        -- 'summary' | 'model' | 'dig:120' | 'digDeeper' | ...
  blob_key      text    not null
  generation_id text    not null
  updated_at    timestamptz not null default now()
  primary key (workspace_id, video_id, slot)
```

A **table, not a jsonb column**, for one decisive reason: GC must ask *"select every referenced
blob_key"*, which is a query against a table and a full scan of jsonb otherwise.

RLS follows the house pattern exactly (`enable` + `force row level security`, a
`for all using/with check (workspace_id = auth.uid())` policy, an explicit grant, an index on the FK).

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

> **Scope of this section — ⟳ RESOLVED 2026-08-05, keep reading to §5.2.** Everything above is about
> **blobs**. The per-video **scalars** (`tldr`, `ratings`, `docVersion`, …) used to live in one
> overwritten slot on `videos.data`, so *"the new run's scalars beside an older generation's body"*
> was expressible — a real, observed failure, and what froze a row permanently in the conditional-write
> slice. **§5.2 closes it** (Q8, decided): the card is an attribute of the generation, so card and body
> are inseparable by construction. This box stays because the *reasoning* is still needed — §5.1 alone
> does not solve the concurrency problem, and a reader who stops here will believe it does.
>
> **"Trivially sufficient" is also now contradicted by evidence.** The conditional-write slice was
> built first specifically to test that claim (its §7). Five adversarial review rounds produced
> **26 Blocking findings, none of them in the predicate** — every one was in the protocol around it:
> NULL semantics, payload rebuild, publish semantics, status inheritance, deploy mechanics, address
> adoption, field-omission semantics. The conditional write itself was correct from the first draft.
> The claim should be narrowed to what was actually demonstrated: *the conditional write is simple;
> the publish protocol around it is not.* Trail: `docs/reviews/spec-conditional-write-*.md`.

### 5.2 The card joins the generation — **DECIDED 2026-08-05 (user), closes Q8**

A summary is **two** things produced by one Gemini run: a **body** (the blob) and a **card** — the
summary-owned scalars `tldr`, `ratings`, `overallScore`, `takeaways`, `videoType`, `audience`,
`language`, `tags`, `processedAt`, `docVersion`, `mdGeneratedAt`, `mdCorrectionsHash`
(`0021:120-132`). §5.1 generation-scoped the body and left the card in one overwritten slot, which is
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
| `ratings`, `overallScore`, `videoType`, `audience`, `language`, `tags` | the video | **video** — carried forward, stable across regenerations |

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
2. **`persist_summary`'s field-merge whitelist stops being load-bearing.** The three-layer jsonb merge
   at `0021:116-133` exists to avoid dropping summary fields on a status-only persist. With the card
   written once as part of an immutable generation record, there is no partial-update semantics to get
   right — the merge disappears rather than being fixed. That whitelist and its "absent → preserved"
   rule accounted for several of the conditional-write slice's Blocking findings.

**Terminology consequence — feeds the `CONTEXT.md` pass (§15).** *Generation* no longer means "a run
that produced a body." It means **a run that produced a body and its card, which are inseparable.**
Write that definition, not §2's current one.

### 5.3 Sync becomes a manifest reconciliation

Sync stops moving bytes. It compares two **artifact manifests** and produces one. (Not to be confused with the existing per-playlist **sync baseline**, also called a manifest in `lib/cloud-sync/manifest.ts` — see §2.) Nothing is copied, nothing is
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

### 6.1 The attachment rule — **DECIDED 2026-08-05 (user), closes Q3**

> **When it is ambiguous, leave it unattached. Never guess.**

**Attach a dig from generation *abc* to a section of summary *def* only when the match is unambiguous
in BOTH directions:**

1. **Exactly one** section of *def* overlaps the dig's span above the threshold — and
2. **exactly one** dig claims that section.

If either count is 0 or >1, the dig stays **stored and unattached**. It is never deleted, never
attached to a guess, and never silently dropped.

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

### 6.2 A detached dig needs a manifest row and a stored span — ⟳ ADDED IN ROUND 1

**Two Blocking findings say "never deleted" and "re-attachable" are not yet rules, only intentions.**

**(a) §8 collects exactly what §6.1 promises to keep (Claude B4).** §6.1 says an unattached dig "is
never deleted." §8 says *"mark and sweep over the artifact manifest; anything not referenced is a
candidate,"* and a detached dig — by §6.1's own construction — **has no manifest row**. So it is
unreferenced, it is paid, and the 90-day clock collects it. Two decisions closed hours apart, and the
one that runs wins.

> **Rule:** a detached dig keeps a manifest row — slot `dig:<sectionId>@<generationId>` in state
> `detached`. It is therefore *referenced*, therefore never a sweep candidate. This also gives the
> "surface it as detached-but-recoverable" requirement something to **enumerate**, which it had no way
> to do before.

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

- **Mark and sweep** over `video_artifacts`. Anything not referenced is a candidate.
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
| Worker `persist_summary` finishes while sync writes its Class-A block | **Lost update.** Same row fields, same blob key; whichever lands second wins, and a paid generation can be destroyed | Different generations ⇒ **no blob collision.** Both publish to the manifest; the conditional write makes the loser retry. No paid work lost |
| Dig job pins `base` at start, sync relocates during its Gemini call | Dig writes to a base the relocation **deleted** — orphaned, paid | No relocation exists. The dig publishes under its own generation |
| Two syncs (two machines, one account) | Unconditional writes interleave | One manifest row, conditional write, loser re-runs |
| Two teammates generate for one video | n/a (no teams) | Two generations, both retained; manifest picks one; neither is destroyed |

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
> card and body together, neither overwriting anything. Both publish by conditionally updating one
> manifest row; the loser retries. The scenario's actual failure, *a card describing a body it did not
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

**⚠ Row 3 — inherits a claim this spec has already had to retract.** "One manifest row, conditional
write, loser re-runs" rests on the conditional write being sufficient. The five-round review of
`2026-08-04-cas-fence-persist-summary-design.md` established the opposite, and §5.1 already carries
the correction: the *write* is trivial, the **publish protocol around it is not**. Row 3 must point at
§5's publish protocol, not at the conditional write alone.

**⚠ Row 4 — describes a feature the spec has since disclaimed.** "Two teammates generate for one
video" sells team concurrency. §11.1 (added 2026-08-04, on the user's decision) says teams are **not
planned** and that naming the tenant buys exactly one narrow transition. Either drop the row or
re-label it explicitly hypothetical — as written it is the strongest team claim left in the document,
sitting in a table a reviewer reads as commitments.

**The pattern across three of four rows:** each was written on 2026-08-02/03 and each was invalidated
by a *later section of this same spec* — Q8, §5.1's correction, and §11.1 respectively. Nothing
external changed. That is what makes walking the table a real gate rather than a formality: a spec
edited section-by-section grows internal contradictions, and only a deliberate cross-read finds them.

---

## 10. Migration

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

`workspaceId == auth.uid()`'s value today, **but the two are deliberately different concepts** — see
§11.0. **Teams are exploration only** — not on the roadmap (user decision, 2026-08-04). Nothing here is
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
3. **Deleting a playlist needs REFERENCE COUNTING, not just enumeration.** Today
   `DELETE /api/playlists/[id]` ends in `deletePrefix(principal, '')`; in a multi-playlist workspace
   that sweep destroys the other playlists' blobs. This sharpens the §4 finding: the delete path must
   walk the manifest **and** check whether any surviving playlist still references each video.

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

> **Never let *being someone* grant access. Let *membership* grant access.**

Every iteration that tried to solve the creation-bootstrap problem with an identity fallback —
`created_by = auth.uid()`, or `split_part(name,'/',1) = auth.uid()::text` — re-created the same defect:
**an identity-based grant cannot be revoked.** A creator who leaves the team keeps read, write and
delete forever, because removing their membership row does not touch the `OR` clause that names them.

**The resolution is atomic creation, not a fallback clause.** A `security definer` RPC inserts the
artifact *and* its first ACL row in one transaction, so there is never a window in which content has no
grant — which is the gap every fallback was patching. `created_by` reverts to **audit only**, with
`on delete set null` so a user can actually be deleted.

**Consequence for this design, and it is not free:** `workspaceId` must be an **independent UUID, never
equal to any user's uid**. Otherwise the existing fast path `split_part(name,'/',1) = auth.uid()::text`
grants the creator their own workspace unconditionally and forever, and no membership clause can undo
it — an `OR` cannot be revoked. **So the RLS predicate changes on day one, not "someday."** An earlier
draft of this section said keeping `tenantId == auth.uid()` costs nothing; that was wrong.

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
   **Amended 2026-08-04 (§4.2.1): there are THREE dimensions, not two.** The third is the section
   **title**, used as an identity anchor in `mergeDigDoc`'s step-2 fallback and in `sameTitles`. It
   *does* dissolve under generation-scoping — but only because §6's span-overlap rule replaces it,
   which promotes question 3 from a tuning detail to a **prerequisite**.
3. ~~**Overlap threshold**, and the section-merge ambiguity (§6).~~ — **CLOSED 2026-08-05 (user
   decision, §6.1): when it is ambiguous, leave it unattached; never guess.** Attach only when the
   match is unambiguous in **both** directions — exactly one section overlaps the dig, *and* exactly
   one dig claims that section. Threshold **0.8** of the dig's own span, tunable upward only.
   **Closing it exposed a gap in §6:** the section-**split** case was never named, and it is
   ambiguous from the *dig's* side rather than the section's — a rule written only against the merge
   example would have missed it. This was the last prerequisite; **all three are now closed.**
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
6. **Cross-playlist dedup: in or out?** (§12) — determines whether `jobs` and the 1D reservation are
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
   the ones that would keep not checking. Knock-on effects: §5.1's scope box retired, §9 row 1
   repaired, and §2's definition of *Generation* must change (a run produces a body **and its card**,
   inseparably). Original question retained below for the reasoning trail.

   **Was: added 2026-08-05, surfaced by the conditional-write slice** (`2026-08-04-cas-fence-persist-summary-design.md`, five
   review rounds).

   A summary is **two** things: a **body** (the blob) and a **card** (`tldr`, `ratings`,
   `overallScore`, `takeaways`, `videoType`, `audience`, `docVersion`, `mdGeneratedAt`,
   `mdCorrectionsHash` — the summary-owned whitelist at `0021_cloud_sync_signals.sql:120-132`). Both
   are produced by one Gemini run.

   **This design generation-scopes the body and says nothing about the card.** Blobs become immutable
   per generation and never collide (§5.1); the card keeps living in one slot on `videos.data` and is
   still overwritten in place. So **"run #2's card beside run #1's body" remains expressible** — a
   catalogue entry updated to the second edition while the shelf still holds the first. Every field
   reads consistent; the body isn't the one described.

   That is not hypothetical. It is the exact state behind the conditional-write slice's B-R4-1: new
   `tldr` and `docVersion` on the row, old bytes at the key, and **nothing able to tell they came from
   different runs** — which then satisfied the idempotency skip (`summary-handler.ts:86-92`) and froze
   the row permanently. A reader of §5.1 would reasonably conclude this design fixes that. **It does
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

   **Not choosing is the one unacceptable option**, because §5.1's *"this answers the concurrency
   problem"* currently implies coverage the design does not provide.

   Related: this question also decides whether §5.1's claim that a conditional write is *"trivially
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
  *scalar* race with a *blob* fix and must wait on Q8; row 3 rests on the sufficiency claim §5.1
  already retracted; row 4 sells team concurrency §11.1 disclaims. All three were invalidated by
  **later sections of this same spec**, not by anything external.
