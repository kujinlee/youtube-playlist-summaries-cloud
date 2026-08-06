# Adversarial review — Stable Blob Addressing design spec, round 1 (Claude)

**Artifact:** `docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md` (v1 draft, 1140 lines)
**Also read:** `CONTEXT.md` (Storage Seam / Addressing), `docs/adr/0006-stable-blob-addressing.md`
**Branch:** `docs/blob-addressing-decisions`
**Method:** every claim below was checked against code I opened in this session. Where the spec's own
citation was stale or wrong I say so and give the symbol.

**Verdict: NOT converged.** 5 Blocking, 7 High, 9 Medium, 3 Low.

The thesis — remove mutable values from the address — is right, and §1/§4's core argument survives
scrutiny. The defects cluster in the sections closed on 2026-08-05/06 (§5.2, §6.1, §8, §11), which is
what the process would predict: those are the newest, least-reviewed text, and three of them were
written as *refinements* that quietly reintroduce the defect class the spec exists to remove.

---

## BLOCKING

### B1 — §5.2.1 reintroduces the card/body lie for six scalars, because all six are serialized into the body

**Defect.** §5.2.1 assigns `ratings`, `overallScore`, `videoType`, `audience`, `language` and `tags` to
the **video** and declares them stable across regenerations — but every one of them is written into the
body's YAML frontmatter by the generator, so the row and the authoritative body will disagree the
moment a second generation exists.

**Evidence.** `lib/ingestion/summary-core.ts:99-108` builds the frontmatter of every summary:

```
const structuralTags = ['video-summary', language];
const allTags = [...structuralTags, ...(tags ?? [])];
...
`lang: ${language.toUpperCase()}`,
...(videoType ? [`type: ${videoType}`] : []),
...(audience ? [`audience: ${audience}`] : []),
`score: ${overallScore}`, '---',
```

and `:121` / `:131` bake `tags` into the quick-view callout alongside `tldr`/`takeaways`
(`insertQuickViewCallout(baseContent, tldr, takeaways, tags ?? [])`). The values come from
`deps.generateSummary(...)` at `:86` — a fresh Gemini roll on every run.

**Failure scenario.** Generation *abc* returns `overallScore: 8`; the body's frontmatter says
`score: 8` and the video row says 8. The user regenerates. Generation *def* is a fresh Gemini call and
returns `overallScore: 6`, which `summary-core` writes into *def*'s frontmatter. §5.2.1's rule says the
row keeps 8 ("the first generation sets them, a later one does not re-roll them"). The manifest
resolves *def* as authoritative. The playlist list renders 8; opening the document shows 6. This is
exactly B-R4-1's shape — a scalar asserting a property of bytes it is not bound to — on six fields,
introduced by the section that claims to remove it.

It is not only cosmetic. `language` drives a paid call: `lib/html-doc/serve-summary-core.ts:110` passes
`load.video.language` into `resolveMagazineModel`, which passes it to
`generateMagazineModel(sections, language, …)` (`lib/html-doc/serve-doc.ts:112-116`). A row whose
`language` is frozen at generation 1 while generation 2's body is in the other language prompts the
magazine transform in the wrong language — a wrong-output paid call.

**What I would change.** §5.2.1 states a rule about the *row* and says nothing about the *body*, and
`summaryCore` has no parameter through which prior judgments could be carried in. Either:
(a) put the six on the generation as well, and let stability be a *reader* rule (resolve judgments from
the earliest generation) — but then the frontmatter still lies, so this only works if the reader is the
only surface, which it is not (Obsidian indexes the frontmatter directly); or
(b) make the writer authoritative — generation *N* must be produced **with the carried-forward
judgments as input**, so the body it writes matches the row. That is structurally the same rule as
§5.2.2's corrections rule and should be written in the same place and the same shape, including its
cost. Right now §5.2.1 is presented as *reducing* the work and in fact adds an unstated change to
`summary-core`'s signature and to the Gemini prompt contract.

---

### B2 — Nothing defines a workspace, so the first segment of every address has no source

**Defect.** `<workspaceId>` is the first path segment of every blob key and the partition key of both
new tables, and no table, column, or RPC anywhere in the design or the codebase produces one.

**Evidence.** Grep for `workspace|team|org_id|shared_with` across all 23 migrations and `lib/`: zero
hits — §3:172-175 says this itself. `Principal.id` is set from the session
(`lib/storage/resolve.ts:93-100`, `return { id: session.userId, indexKey }`) or from the worker's
`ownerId` (`:83`), and `SupabaseBlobStore.objectKey` composes `${p.id}/${p.indexKey}/${key}`
(`lib/storage/supabase/supabase-blob-store.ts:17`). §5's `video_artifacts` and §5.2's
`video_generations` both take `workspace_id uuid not null` with no FK and no origin. §11.0:802 says "a
workspace is a **user-chosen grouping of playlists**"; §13:985 puts "actual team/workspace support"
out of scope.

**Failure scenario.** A plan cannot be written. There is no `playlists.workspace_id`, no `workspaces`
table, no creation rule, and no answer to "what happens when a user creates their second playlist —
same workspace or a new one?" Every downstream decision depends on it: §11.0's dedup/sharing table,
§11.0 consequence 3's reference counting (which must enumerate the workspace's playlists), §12's job
re-keying, and the object key itself.

**What I would change.** Either add the `workspaces` table + `playlists.workspace_id not null
references workspaces(id)` to §5 with the creation rule and the default grouping, **or** scope this
slice explicitly to one-workspace-per-user with `workspace_id = auth.uid()`, move §11.0's grouping knob
and §11.2's independent-UUID rule to the follow-up ADR, and stop asserting cross-playlist dedup as a
property of *this* design. The second is the smaller, honest slice; either is fine, but the spec must
pick one.

---

### B3 — §11.2 ("the RLS predicate changes on day one") contradicts §4 and §5, and requires infrastructure §13 declares out of scope

**Defect.** Three sections of this spec state mutually exclusive things about the same predicate.

**Evidence.**

- §4:190-192 — "Today it is literally `auth.uid()`, so the bytes are unchanged from the current layout
  and **the predicate needs no edit**."
- §11.2:867-871 — "`workspaceId` must be an **independent UUID, never equal to any user's uid** …
  **So the RLS predicate changes on day one, not 'someday.'**"
- §5:346-347 — the manifest RLS is prescribed as `for all using/with check (workspace_id =
  auth.uid())`, which denies every row the instant `workspace_id` stops being a uid.
- §13:985 — "Actual team/workspace support (§11) — only the naming hook is in scope", while §11.2's
  replacement predicate needs `workspace_grants` and `team_members`.

**Failure scenario.** Implement as §11.2 requires. `artifacts_owner_rw`
(`supabase/migrations/0007_storage_and_rpcs.sql:12-15`) is
`split_part(name, '/', 1) = auth.uid()::text` — with an independent workspace UUID in segment 1 it
matches nothing, so **every authenticated and anon read and write of a blob is denied**. All
session-scoped routes go through a session-client `SupabaseBlobStore`
(`lib/storage/resolve.ts:51-62`), so the app has no working blob path; only `service_role` survives.
Implement as §4 requires instead, and §11.2's own argument applies: `split_part(name,'/',1) =
auth.uid()::text` is an unrevocable identity grant to the creator, which §11.2 says cannot be undone by
any later membership clause.

**What I would change.** Resolve to one position and propagate it to §2's Workspace row, §4, §5, §13
and ADR-0006 (whose Consequences still say "`tenantId` is named now and **equals** `auth.uid()`", the
§4 position, under a spec that now says the opposite). Note this is a *goal-affecting* fork, not a
mechanical choice: it decides whether this slice ships a storage-RLS rewrite.

---

### B4 — §8's GC collects exactly the paid content §6.1 promises never to delete

**Defect.** §6.1 guarantees an unattached dig is "never deleted". §8 defines the sweeper to collect
anything the manifest does not reference. An unattached dig is, by §6.1's own construction, not
referenced.

**Evidence.** §6.1:534-535 — "the dig stays **stored and unattached**. It is never deleted, never
attached to a guess, and never silently dropped." §8:614 — "**Mark and sweep** over `video_artifacts`.
Anything not referenced is a candidate." §8:617-620 — "If a blob is not current, delete it — except a
paid blob, which is retained for 90 days so it can be recovered." A dig is paid
(§3 inventory, `Dig section … PAID`).

**Failure scenario.** A user pays for a dig on section 120 of generation *abc*. A re-summarize produces
*def* which splits that section, so §6.1 clause 1 finds zero candidates ≥0.8 and the dig is left
stored-and-unattached — correct behaviour. It now has no `video_artifacts` row. 91 days later the
scheduled sweep collects it. The design's two most recently closed decisions disagree, and the one that
actually runs wins.

**What I would change.** "Never deleted" needs a manifest representation, or it is not a rule. Give a
detached dig a row — e.g. slot `dig:<sectionId>@<generationId>` with a `detached` state — so it is
referenced and therefore not a GC candidate. That also gives §6.1's "surface it as
detached-but-recoverable" something to enumerate, which it currently does not have.

---

### B5 — After a playlist delete the manifest rows survive, so the blobs become permanently uncollectable

**Defect.** §8's headline correctness rule is "an explicit delete outranks retention." Under §5's schema
a playlist delete *inverts* it: the manifest rows are not reachable by any cascade, so the sweeper sees
every blob as referenced and never collects it. Delete does not shorten the retention window — it pins
the bytes forever.

**Evidence.** §5's `video_artifacts` has columns `(workspace_id, video_id, slot, blob_key,
generation_id, updated_at)` — **no playlist column and no FK to `playlists`**. The 0019 cascade reaches
`videos`, `jobs` and `share_tokens` only. `app/api/playlists/[id]/route.ts:74` is the commit point
(`metadataStore.deletePlaylist`), and `:78-82` is the blob cleanup — wrapped in a try/catch that logs
and returns **200** ("invisible orphan accepted"). §4:221-229 already identifies that the prefix sweep
itself breaks; this is the second half of the same problem and it is worse, because the failure is not
"blobs survive" but "blobs can never be collected."

**Failure scenario.** `DELETE /api/playlists/X`. Cascade removes the `videos` rows. Nothing removes
`video_artifacts` or `video_generations`. The new manifest-driven blob enumeration runs on the
best-effort path and fails (or is skipped, or the process dies between the two) — 200 returned. The
sweeper then reads `video_artifacts`, finds every one of that video's blobs referenced, and marks
nothing. §8:648-651's promise ("collected **immediately**, not in 90 days") becomes "never".

**What I would change.** Unreferencing is DB state and belongs **inside the commit-point transaction**,
not on the best-effort byte path. Order it so a partial failure fails toward *collectable*: delete the
manifest rows transactionally with the playlist, then let the sweeper (with its grace period) delete the
bytes. Byte deletion may stay best-effort; unreferencing may not. §8:655-658's box says "Assert the
collection, do not assume it" — the assertion is impossible until the ordering is specified.

---

## HIGH

### H1 — The "does a paid artifact already exist?" question moves from a seam with an honest read to a manifest read with no stated contract (the 6¢→12¢ shape, one level up)

**Defect.** Today the money guard is a `tryGet` on the blob, deliberately, because a failed read must
never look like an absent artifact. Under §5 the authority moves to the manifest, and §5 specifies the
table, the PK and the RLS but says nothing about what a reader does when the *manifest read* fails.

**Evidence.** `lib/html-doc/serve-doc.ts:59-71`:

```
// ── MONEY GUARD — never spend on an UNPROVABLE read.
const probe = await blobStore.tryGet(principal, MODEL_KEY(base));
if (!probe.ok && probe.reason === 'unreadable') return { status: 'busy' };
```

with the comment citing the measured 6¢→12¢ and `tests/integration/serve-model-unreadable.test.ts`.
`lib/storage/blob-store.ts:46-56` states the rule as a seam obligation ("Use this instead of `get`
before any irreversible or billable decision").

**Failure scenario.** Under §5, "is the model already paid for?" = "is there a `video_artifacts` row
for slot `model`?" A PostgREST/network error, a transient RLS evaluation failure, or a
`.maybeSingle()` whose error the caller does not inspect all produce "no row", which reads as "no
model", which leads to `reserve_serve_model` and a second Gemini call — for a model sitting in the
bucket. The spec has carefully protected the blob read and left the read that supersedes it unspecified.

**What I would change.** §5 must give the manifest read the same three-way contract `BlobRead` has:
`{present, key, generation}` / `absent` / `unreadable`, with `unreadable` a required, non-optional
member so callers cannot inherit the ambiguous form (the same argument `blob-store.ts:53-55` makes for
`tryGet`). State that only `absent` may lead to a spend. Write the assertion in this slice —
`tests/integration/serve-model-unreadable.test.ts` is the template and the scaffolding already exists.

### H2 — §5.2's "the merge disappears rather than being fixed" relocates the field-omission defect; the cloud worker supplies none of the document facts

**Defect.** §5.2 argues the `persist_summary` whitelist "stops being load-bearing" because an immutable
generation record has no partial-update semantics. That is true only if every producer writes a
*complete* card. The cloud worker writes none of the currency fields today, and §5.2 turns "silently
preserves the old value" into "silently NULL" without requiring completeness anywhere.

**Evidence.** `lib/job-queue/summary-handler.ts:149-164` — the persisted `Video` carries `docVersion`
and `processedAt` but **no `mdGeneratedAt` and no `mdCorrectionsHash`**. `0021:120-132`'s
`jsonb_strip_nulls` therefore preserves the previous values. §5.2.2 names this for
`mdCorrectionsHash`; it does **not** name `mdGeneratedAt`, which has the same hole on the same lines.

**Failure scenario under §5.2.** Cloud generation *def* lands with a card whose `mdGeneratedAt` is NULL.
`lib/cloud-sync/reconcile-class-a.ts:49` is the recency tiebreak:

```
const newer = (a: string | null, b: string | null): boolean => (a ?? '') > (b ?? '');
const winnerIsLocal = newer(local.mdGeneratedAt, cloud.mdGeneratedAt);
```

`'' > anything` is false in the cloud's favour only when local is also null. With cloud NULL and local
set, **local wins every tiebreak, deterministically**, and the next sync overwrites a freshly-paid
cloud body with an older local one. Today the same omission produces a stale-but-non-null value, which
loses less often; the §5.2 form loses always.

**What I would change.** Make card completeness a schema fact, not a convention: every document fact
`not null` on `video_generations`, plus a producer-side card type the compiler forces every writer to
populate (`as any` on a test double opts out, so back it with a behavioural test). Say in §5.2 that
"the merge disappears" is conditional on incompleteness becoming *impossible*, and fix
`summary-handler.ts` in the same slice — it is one of the two producers.

### H3 — §6.1's threshold is one-directional: it never measures how much of the *section* the dig covers, so a merge with one dug predecessor attaches silently and wrongly

**Defect.** Both of §6.1's clauses are about *ambiguity* (how many candidates on each side). Neither is
about *fit*. The single stated ratio is "the fraction of the dig's span contained in the candidate
section", which is 1.0 whenever the dig's span is a subset of the section — including when the section
is four times larger.

**Failure scenario.** Generation *abc* has sections `[100,200)` and `[200,300)`; only `[100,200)` was
dug. Generation *def* merges them into one section `[90,400)`.
- Clause 1: exactly one *def* section overlaps ≥0.8 of the dig's span (overlap = 100/100 = 1.0). Passes.
- Clause 2: exactly one dig claims that section (the second was never dug). Passes.
⇒ **Attached.** The reader is shown a dig covering the first quarter of a section, presented as that
section's dig. §6:520 defines this as the worst outcome: "A wrong attachment silently mislabels paid
content, which is worse than showing none: the user cannot tell it is wrong."

Note the shape. §6.1:546-548 congratulates itself for catching what §6 missed — "§6 named merge and
never named split … it is the same defect shape as the merge case and would have been missed by a rule
written only against the example that was in front of us." §6.1 then names both directions of
*ambiguity* and neither direction of *coverage*, for the same reason.

**What I would change.** Add a third clause: the candidate section's span must be covered by the dig's
span above a floor too (or require the ratio to hold in both directions). State both ratios explicitly
so the implementer cannot pick one.

### H4 — A dig's span exists nowhere in the address or the manifest, so §6.1 depends on reading a summary §8 collects

**Defect.** §6.1 is a span-overlap rule. §4's key encodes only the start (`dig/<sectionId>.md`, and
`sectionId` *is* `startSec`), and §5's `video_artifacts` has no span columns. The end is derived at read
time from the summary of the generation that produced the dig.

**Evidence.** §4:184; `lib/dig/section-window.ts:58` returns `{ sectionId: startSec, startSec, endSec, … }`
where `:46-48` computes `endSec` as the *next section's* start — i.e. from the whole parsed summary.
§5:333-341 lists the manifest columns; there is no `start_sec`/`end_sec`.

**Failure scenario, two of them.**
1. *Permanently unattachable.* Dig on `[100,200)` in *abc*; *def* splits into `[100,150)`/`[150,200)`
   so each overlap is 0.5 and the dig is correctly left unattached. A later generation restores the
   original boundary — but by then *abc*'s `summary.md` has stopped being current and, per §8, has been
   collected. The span is unknowable, so the dig can never be re-attached. Combined with B4, it is also
   already deleted.
2. *Absent-vs-failed on the serve path.* Every attach decision requires reading a **superseded**
   summary blob. `blobStore.get` collapses 5xx/timeout/RLS into `null`
   (`lib/storage/supabase/supabase-blob-store.ts:27-37`; `provesAbsence = false` at `:10`). A transient
   Storage blip therefore renders a legitimately-attachable paid dig as *absent* — the user watches
   paid content disappear and reappear.

**What I would change.** Persist the span on the manifest (or generation) row at write time. Attachment
then becomes a pure DB computation with no dependency on a collected blob and no blob read on the
decision path. This is cheap now and impossible to retrofit after the first sweep runs.

### H5 — `serve_model_charge` is a second playlist-keyed money identity §11.0 does not name; the workspace knob loosens the G1 cap by a factor of N

**Defect.** §11.0:827-830 says storage dedup is free but spend dedup "still requires §14 Q6 —
`jobs_idem_active` includes `playlist_id`". That names the *queue*. The magazine model is charged on the
**serve** path by a different arbiter, also keyed on playlist, which the spec never mentions.

**Evidence.** `supabase/migrations/0020_reservation_release.sql:213`:

```
v_doc_key := p_playlist_id::text || '/' || p_video_id;
```

`serve_model_charge` is `(owner_id, doc_key, day)` (0012, extended by 0014/0020), and the K-attempt
bound is `serve_model_charge.attempt_count < v_cfg.max_serve_attempts` (`0020:222-223`). The per-owner
daily cap (`serve_owner_budget`, `0014:6-10`) sits around it. This is the whole of the Stage 1G/G1
fairness cap.

**Failure scenario.** One video in N playlists of one workspace resolves **one** manifest slot for
`model`, per §11.0. But each playlist has its own `doc_key`, so it gets its own daily lease and its own
`max_serve_attempts` budget against that single shared slot. The cap G1 exists to enforce is N times
looser, and each of the N attempts overwrites the previous one's blob
(`writeModelEnvelope` is a plain `put`/upsert — `lib/html-doc/serve-doc.ts:101-104` says so explicitly).
Under the new design each instead mints a *new generation* and re-points the manifest, so N−1 paid
models become not-current and start their 90-day clock.

**What I would change.** §11.0's spend-dedup paragraph must enumerate **every** arbiter keyed on
playlist and say what each is re-keyed to: `jobs_idem_active` (`0009:11-13`) and
`serve_model_charge.doc_key` (`0020:213`). Re-keying `doc_key` to `workspace/video` is what makes
storage dedup and spend dedup agree; leaving it is what makes the workspace knob a money regression.

### H6 — Assets are keyed on a per-generation value but stored generation-free, and §8 classifies them as free — so a re-dig destroys a still-servable dig's images

**Defect.** §4:236-238 argues assets can sit outside a generation because "a frame at 120s is the same
frame regardless of which generation drew a section boundary near it." But the key §4:185 specifies
includes `<sectionId>`, which *is* a per-generation value, and the code prunes by exactly that prefix.

**Evidence.** `lib/dig/section-window.ts:58` — `sectionId` is `startSec`, allocated per generation by
`allocateSectionStarts` (`lib/summary-section-timestamps.ts:12-42`). `lib/dig/slides.ts:185-190` writes
`assets/${videoId}/${assetName}` where `assetName` starts `${sectionId}-`. `lib/dig/slides.ts:207-209`
then calls `pruneSectionAssets(dir, sectionId, written)` — `:219-231` — which `fs.unlinkSync`es every
`<sectionId>-*.jpg` not written by the current run, bypassing the BlobStore seam (this is §14 Q7's
second writer).

**Failure scenario.** Generation *abc*'s dig on section 120 renders `![](assets/<vid>/120-…​.jpg)`. §6
explicitly permits *abc*'s dig to remain attached under summary *def*. A dig run for *def*'s section 120
prunes every `120-*` asset it did not itself write — *abc*'s images — so the still-attached, still-paid
dig renders broken. Separately, §8 classifies assets as free (§3:157 calls them "free of Gemini") and
therefore "not current ⇒ delete immediately", while the same line says they need "a video download +
re-encode". They are the single most expensive artifact to recreate and get the least protection.

**What I would change.** Key assets on the pure timestamp window with no `sectionId` (they are, per §4's
own argument, a function of `(videoId, start, end)` alone), and reclassify them in §8 — "free of Gemini"
is not the same as "free to recreate", and §8's rule is written against cost of recreation, not against
Gemini spend.

### H7 — §5.2's "resolving a generation yields both or neither" fails across the GC boundary; nothing collects `video_generations`

**Defect.** §8 sweeps `video_artifacts` and collects **blobs**. §5.2's `video_generations` row — the
card — is DB state with no stated lifecycle. So the card outlives the body it describes.

**Evidence.** §5.2:456-464 defines the table; §8:602-696 never mentions it. §5.2:466-468 claims
"Resolving *the current card* is then the same join as resolving *the current body* … so the two cannot
disagree" and §9.1:729-730 raises that to "resolving a generation yields **both or neither**."

**Failure scenario.** Generation *abc*'s body is collected at day 91. Its `video_generations` row is
still there. Any reader that resolves a generation by id — the recovery path §8's 90-day window exists
to serve, or the detached-dig surface §6.1 asks for, or a manifest row that was not cleaned up (see B5)
— gets a card with a 404 body. The same class of lie, in the mirror direction, on the path specifically
built for recovery.

**What I would change.** Give the generation record a lifecycle in §8 (collect the row with the last
blob of that generation, or mark it `body_collected` so a reader can distinguish), and specify the FK
between `video_artifacts.generation_id` and `video_generations` including its `on delete` behaviour —
§5.2:468 says "references it" and declares no constraint at all.

---

## MEDIUM

### M1 — "Manifest" already means something else in this codebase, and the terminology pass missed it — including in the one sentence where it matters

`lib/cloud-sync/manifest.ts:6` — `export interface Manifest { version: 1; videos: Record<string,
VideoBaseline>; }` — is the per-playlist `.cloud-sync-manifest.json` sync **baseline** (`:8-9`), with
`readManifest`, `writeVideoBaseline`, `manifestPath`, consumers in `sync-run.ts`, `companion.ts`,
`types.ts`, and 7 test files.

§5.3:503 reads "Sync stops moving bytes. It compares two manifests and produces one." That is a true
sentence about the *existing* manifest and a different true sentence about the new one, in a section
whose whole subject is sync. §15:1099-1103 lists four vocabulary collisions the grill pass found and
explicitly preserves a qualifier for *Slot* ("keep the qualifier"); `CONTEXT.md:60` then defines
*Manifest* with no qualifier and no mention of the existing meaning. **Fix:** qualify one of them
(*artifact manifest* vs *sync baseline*), and correct §15's claim that the pass caught the collisions.

### M2 — §11.0 consequence 3's reference counting has a TOCTOU and no defined reference source

The manifest is keyed `(workspace, video, slot)` with no playlist, so the count must come from `videos`
rows across the workspace's playlists — which, per B2, has no mapping to enumerate. Even granting it:
`app/api/playlists/[id]/route.ts:73-79` deletes the playlist (commit point) and does the blob work
*after*, unlocked, so an ingest or sync adding the same video to a sibling playlist inside that window
makes the count wrong in the destructive direction. **Fix:** express the unreference as a single
transactional statement alongside the playlist delete (`delete from video_artifacts where … and not
exists (surviving videos row)`), and let the sweeper's grace period handle the bytes. Never count in
the app and delete in the app.

### M3 — §5's manifest RLS hands clients DELETE on the only pointer to paid bytes

§5:346-347 prescribes the house pattern — `for all using/with check (workspace_id = auth.uid())` plus a
client grant. That pattern is what `videos` uses, and a `videos` row is reconstructible. A manifest row
is not: deleting it unreferences paid blobs and starts the 90-day clock, with no undo anywhere in §8.
The codebase already has the right precedent and §11.3:945-948 praises it: `share_tokens`
(`0013:16-18`) is `force row level security` with **no** anon/authenticated policy, service_role-only
grants, and all writes through `security definer` RPCs. **Fix:** manifest writes go through a definer
RPC (`publish_slot(workspace, video, slot, expected_key, new_key, generation)`); the client policy is
`select` only. This also gives §5.1's conditional write a single owner instead of one per writer —
the exact shape of the 2026-07-30 architecture review's finding #2.

### M4 — §5.1's "the loser retries" has no mechanism, and `jobs_idem_active` prevents it

`0009:11-13`'s partial unique index covers `completed`, and `enqueue_job` joins rather than inserts on
conflict (`0011:83-88`). A worker whose conditional manifest write lost has a `completed` job; nothing
re-runs it. The claim appears three times as load-bearing: §5.1:365 ("the loser retry"), §9 row 1 and
§9 row 3. Combined with §5.2.2 the consequence is concrete: if the loser is the generation that applied
the user's corrections, the published generation is the one without them, permanently. **Fix:** say
what publishes after a lost CAS — an idempotent re-read-and-republish of the same generation is
probably right — and put it in §5, not in a claim.

### M5 — §8's "paid/free from the key alone" rule is stated for key shapes §4 does not define

§8:662-666 makes key shape a money-safety concern because an orphan has no manifest entry. §4 defines
four shapes and omits four of the nine kinds in §3's inventory: HTML, PDF (cloud and local), dig-deeper
companion, and `_staging`. §8:677-682 even notes per-generation HTML is accumulation *this design
creates*. A classification rule that must hold for keys the spec has not written down cannot be
tested — which is what §8's own "add that to the review checklist for new key shapes" asks for.
**Fix:** extend §4's template to all nine kinds, then re-derive the rule against the full set.

### M6 — §12's cross-tenant injection guard cannot be preserved as stated

The guard is the composite FK `jobs(playlist_id, owner_id) → playlists(id, owner_id)`
(`0009:5-6`), which exists only because `playlists` carries `unique (id, owner_id)` (`0001:18`).
Re-keying the job identity on workspace needs an equivalent `(workspace_id, owner_id)` unique target,
and per B2 there is no workspace table to put it on. §12:975-976 requires "an equivalent guard" without
saying what it is; §11.0:828-830 promotes Q6 from optional to load-bearing ("this granularity choice is
what actually decides Q6") while §14 still lists Q6 open. **Fix:** settle Q6 here and write the
replacement guard as SQL.

### M7 — §9's table still asserts what §9.1 retracts

§9.1:748-758 concludes rows 3 and 4 do not survive, and the table at §9:706-710 still says them
verbatim. The table is the artifact a reviewer scans. §9.1's own closing argument is that "a spec edited
section-by-section grows internal contradictions, and only a deliberate cross-read finds them" — and
then leaves one. **Fix:** rewrite the rows in place; keep §9.1 as the trail.

### M8 — §6.1's ratio is undefined for a zero- or negative-length dig span, which the code can produce

`lib/dig/section-window.ts:46-48` sets the **last** section's `endSec` to `durationSeconds`, not to the
▶ end. `allocateSectionStarts` clamps with `hi = Math.max(lower, upper)`
(`lib/summary-section-timestamps.ts:22-23`), so under pathological input (more sections than seconds)
the last start can land at or past the duration ⇒ `endSec <= startSec`. §6.1's ratio — "the fraction of
the dig's span contained in the candidate section" — then divides by zero or by a negative.
`windowForSection`'s own header comment (`:24-27`) documents the collision case producing
`endSec === startSec` and tells callers to treat an empty window as valid. **Fix:** state the
degenerate case in the rule (zero-length span ⇒ never auto-attach), rather than leaving it to the
implementer to discover.

### M9 — §10 overstates `reconcileCloudBase` as the migration tool; it cannot express the migration

§10:771-774 says `reconcileCloudBase` is "**precisely** the machinery this needs" and "gets used as the
migration tool, then retired". Four things in it are wrong for the job:

- `BlobStore.copy(p, from, to)` takes **one** principal (`lib/storage/blob-store.ts:45`). If §11.2 holds,
  source is under `<ownerId>/<playlistKey>/` and destination under `<workspaceId>/videos/…` — two
  principals. The seam cannot express the copy.
- `remap` (`lib/cloud-sync/reconcile-serial.ts:116-139`) enumerates exactly four old-base shapes and
  **fails closed on anything else**, deliberately. None of them map to `<gen>/summary.md`.
- `paidKeysUnder` (`:95-104`) covers MD, model, digs and dig-deeper only — it explicitly excludes HTML
  and PDF, which the migration must still move or delete.
- The function refuses outright on any record carrying an artifact kind other than `summaryMd`
  (`:212-216`) and on any in-flight job (`:250-251`) — correct for its own job, fatal for a one-shot
  whole-corpus migration.

**Fix:** say what §10 actually inherits (the *protocol* — plan, copy-with-sources-retained, verify,
advance metadata, delete best-effort, refuse on ambiguity) and cost the migration tool as new work.

---

## LOW

### L1 — §3's corrected citation is itself wrong, and §15 certifies it

§3:126 says the storage policy was "cited as `12-17`" and corrects it to `0007:13-16`; §15's table
repeats "✅ ⟳ line range `13-16`" under the claim that "**zero facts were found false**". The policy
`artifacts_owner_rw` spans `supabase/migrations/0007_storage_and_rpcs.sql:12-15` — `create policy` at 12,
`with check` at 15. The corrected citation is off by one at both ends. The fact is right and the
methodological lesson §3:1133-1134 draws ("cite the symbol; let the line number be a hint") is right; the
correction demonstrates it rather than escaping it.

### L2 — "all 21 migrations" is now 23

§3, §5.2 and §14 Q8 all say 21. `supabase/migrations/` holds 23 (`0022_dig_max_attempts.sql`,
`0023_claim_video_slot_desired_serial.sql`). I re-ran the load-bearing grep: `mdHash` still returns
**zero** across all 23, so §14 Q8's conclusion survives. Worth noting because 0023 rewrote
`claim_video_slot`, which §15 cites as the source of the *Slot* terminology collision.

### L3 — §14's header and §14 Q3's closing sentence disagree about what is closed

The header says "Open questions — **must be closed before a plan**"; Q3:1012 says "This was the last
prerequisite; **all three are now closed.**" Four questions remain open — Q1 (`generationId` form,
which §8's dedup reasoning depends on), Q5, Q6 (now load-bearing per §11.0) and Q7. "Three" means the
three *prerequisites*; a reader scanning §14 reads it as all of them. Say "the three prerequisites",
and re-mark Q6 as a prerequisite given §11.0.

---

## What I checked and found correct

Stated so the next round does not re-derive these:

- **§5.2.2's live-defect claim is TRUE and I verified the mechanism.** `lib/job-queue/summary-handler.ts:149-164`
  never sets `mdCorrectionsHash`; `0021:120-132`'s `jsonb_strip_nulls` therefore preserves the previous
  value via layer (2), so a cloud re-summarize does produce a body with no corrections beside a row
  asserting corrections. `app/api/videos/[id]/regenerate/route.ts:63,76-88` is indeed the only path that
  applies them. (H2 extends this to `mdGeneratedAt`, which §5.2.2 does not name.)
- **§4.2's addressing half is confirmed.** `lib/dig/section-window.ts:58` returns `sectionId: startSec`
  literally; `allocateSectionStarts` (`lib/summary-section-timestamps.ts:20-41`) is strictly increasing
  by construction (`prev = s` after each `s >= lower = prev + 1`). Caveat worth stating: the guarantee is
  delivered by `ensureSectionTimestamps`, which **returns early when `sectionStartsComplete` is already
  true** (`:96`) — so it holds for documents the normalizer has passed, not for arbitrary markdown.
- **§4's `indexKey` finding is real and I found all three composition sites**, not just the two cited:
  `objectKey` (`supabase-blob-store.ts:17`), `deletePrefix` (`:112`) and `list` (`:123`), plus the
  in-memory test store (`lib/storage/testing/in-memory-blob-store.ts:94,98`). `deletePrefix(principal,
  '')` at `app/api/playlists/[id]/route.ts:79` is the sharpest instance, as §4 says. `Principal.id`
  itself has only those uses in `lib/`, so §11.2's implicit claim that the *code* change is bounded is
  correct — it is the RLS predicate that is not (B3).
- **§3's two load-bearing RLS properties hold.** `0007:14-15` compares text to text and casts the uid,
  not the segment; a NULL `auth.uid()` yields NULL, and RLS requires TRUE, so anon isolation needs no
  separate rule (`0007:9-11` documents exactly this). §11.2's "never cast the path segment" rule is the
  right direction and its `workspace_member` sketch obeys it (`g.workspace_id::text = p_ws`).
- **§3's claim that `share_tokens` never creates a second owner holds.** `0013:9-11,36-42` and
  `lib/share/serve.ts:31-42` — the playlist is resolved by `(id, owner_id)` from the token row and the
  owner is re-asserted at every hop.
- **§3's "exactly one row per `(playlist_id, video_id)`"** — `0001:30`, the primary key. Correct.
- **`jobs_idem_active` carries `playlist_id` and covers `completed`** — `0009:11-13`. Correct, and it is
  what makes M4 bite.
- **§9 row 2 survives.** I traced it independently: with per-generation keys there is no relocation for
  a pinned base to race with, and the two remaining relocations §9.1 names (the §10 migration, an
  ownership change) are one-shot deliberate actions, not concurrent writers.

---

## Summary

| Severity | Count |
|---|---|
| Blocking | 5 |
| High | 7 |
| Medium | 9 |
| Low | 3 |

**Blocking**
- B1 — §5.2.1 reintroduces the card/body lie for six scalars that `summary-core` writes into the body's frontmatter
- B2 — No table defines a workspace, so the first segment of every address has no source
- B3 — §11.2's "predicate changes on day one" contradicts §4 and §5 and needs infrastructure §13 scopes out
- B4 — §8's GC collects exactly the paid digs §6.1 promises are "never deleted"
- B5 — Playlist delete leaves the manifest rows, so the blobs become permanently uncollectable (delete *inverts* retention)

**High**
- H1 — The paid-artifact-exists check moves from `tryGet` to a manifest read with no absent-vs-unreadable contract (the 6¢→12¢ shape, one level up)
- H2 — §5.2 relocates the field-omission defect: the cloud worker writes no document facts, and NULL loses every Class-A tiebreak
- H3 — §6.1's threshold never measures section coverage, so a merge with one dug predecessor attaches wrongly and silently
- H4 — A dig's span is in neither the address nor the manifest, so §6.1 depends on a summary §8 collects
- H5 — `serve_model_charge.doc_key` is a second playlist-keyed money arbiter §11.0 misses; the workspace knob loosens the G1 cap N-fold
- H6 — Assets are keyed on a per-generation `sectionId` but stored generation-free, and pruning destroys a still-servable dig's images
- H7 — Nothing collects `video_generations`, so a card outlives its body — "both or neither" fails across the GC boundary
