# Adversarial review — Stable Blob Addressing design spec, ROUND 3 (Claude)

**Artifact:** `docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md` (branch
`docs/blob-addressing-decisions`), plus `CONTEXT.md`, `docs/adr/0006-stable-blob-addressing.md`,
`docs/reviews/spec-blob-addressing-rules-inventory.md`.
**Prior rounds read:** `spec-blob-addressing-r1-{claude,codex,coordinator}.md`,
`spec-blob-addressing-r2-{claude,codex,coordinator}.md`.

**Method note.** Three of the JOB B findings below were **executed against the live local Postgres 17
stack**, not argued from reading. The spec's `video_artifacts` DDL, the `check (kind = slot_kind(slot))`
guard, and §14 Q6's replacement cross-tenant FK were each run verbatim in a scratch schema
(dropped afterwards). Two of the three do not create; the third creates and does not guard. Where a
finding says MEASURED, the quoted error is real output.

**Verdict: NOT CONVERGED.** 6 Blocking, 9 High, 5 Medium, 3 Low.

**Which invariants I judge too restrictive, or restrictive in the wrong shape:** **19** (the binding
one — it forbids the spends the system must make and cannot perform the check it exists to perform),
**13/14** as a *pair* (eligibility-as-filter has no floor, so a free user action can empty a slot),
**15** (sound rule, but its stated justification is about bytes that do not exist where it says they
do), **12** (enforced by a schema that only one of the two backends has). Rules 9, 10, 11, 16, 17, 18,
20 I attacked and could not break — notes at the end of JOB A.

---

# JOB A — attacking the twelve chosen invariants

## BLOCKING

### A-1 — [invariant 19, with 13 + 14] The "both reads before a spend" rule is unsatisfiable by construction: on the only path that reaches a spend, there is no key to probe

**Defect.** Rule 19 (§5.1:684-688) permits a paid regeneration only when the slot is `absent` **and**
the blob is `provably absent`. Under rule 13 (§5.1.1:745-747) the slot is `absent` exactly when **no
eligible generation is recorded** — and when no generation is recorded there is **no blob key**. The
second read has no argument. Rule 19's protective half is therefore vacuous on 100% of the paths that
reach it, and the 6¢→12¢ defect returns through the hole.

**Why this is a premise problem and not a wording problem.** The guard works today *because the key is
derivable without any record*: `MODEL_KEY(base)` is a pure function of `base`, so `serve-doc.ts:70`
can probe for bytes it has no row for. That is the whole point — the failure being guarded is
"the record is lost/unreadable while the bytes exist." Rule 9 moved the key from *derivable from a
display attribute* to *derivable only from a `generationId`*, and a `generationId` exists only inside
the record. **The design removed the ability to ask "are the bytes there anyway?", which is the only
question the money guard ever asks.**

**Failure scenario (live, not hypothetical).** §8:1219-1220 explicitly contemplates the window: "a blob
written but not yet published is unreferenced." A worker writes `<ws>/videos/V/g7/model.json`, then
crashes before `record_artifact`. Slot = `absent` (no row). Rule 19's blob half: no key to check.
Serve path spends again. Second run mints `g8`, writes a second paid model, and `g7`'s bytes sit
unreferenced for their grace period and then 90 days. Measured cost of exactly this shape:
6¢ → 12¢, `attempt_count` 1 → 2 (`tests/integration/serve-model-unreadable.test.ts`).

**Evidence.** Spec §5.1:667-688 (`SlotRead` + the both-reads rule); §5.1.1:745-758 (derived `current`,
eligibility from recorded facts); §8:1219-1220 (the grace-period window);
`lib/html-doc/serve-doc.ts:56-76` (today's guard: `readFreshMagazineModel` → `tryGet(MODEL_KEY(base))`
→ `busy` on unreadable → only then `reserve_serve_model`);
`lib/html-doc/model-store.ts` `MODEL_KEY` (a pure function of `base`);
`lib/storage/supabase/supabase-blob-store.ts:27-37` (`get` collapses everything to `null`), `:44-57`
(`tryGet`, the honest probe).

**Change.** Restate rule 19 around **determinacy, not absence**: *a spend requires a determinate
negative answer from every layer that could hold the artifact; an indeterminate answer from any layer
is `busy`.* Then give the "slot absent" branch something determinate to probe — the cheapest option is
to keep a **derivable probe key per (workspace, video, slot)** alongside the generation-scoped ones
(e.g. a `latest/` alias or a per-slot content-addressed key), so "no record" can still be
distinguished from "no bytes." Without that, state explicitly that a lost manifest row is an
*accepted double-charge*, and cost it — do not leave the rule reading as if it were covered.

---

### A-2 — [invariants 13 + 14] Eligibility is a filter with no floor: one free, synchronous user write makes **every** generation ineligible at once, and the video's summary disappears

**Defect.** Eligibility (§5.1.1:754-758, restated §5.2.2:916-920) requires
`mdCorrectionsHash` **matches the video's current corrections**. Corrections are a *user-typed field*
changed by an ordinary allowlisted RPC (`0021:19-53`, `update_video_annotations`, `security invoker`,
allowlist `{personalScore, personalNote, corrections, archived}`). The moment a user saves a
correction, **every generation ever recorded for that video** has a stale `mdCorrectionsHash` — the
newest and all of its predecessors, simultaneously. `current` for the `summary` slot becomes **empty**.

**Failure scenario.** A user reading a summary spots "Clawcode", types the correction, and hits save.
The write is instantaneous and free. Their summary now resolves to nothing. Per §5.1.2:697-706 the
`model` slot's `source_generation_id` "is no longer the current summary generation," so the magazine
model is ineligible too — the rendered document, not just the markdown. The content returns only after
a **paid** regeneration, and per §5.2.2:925-932 that regeneration is a full-document `fixSummary`
Gemini round trip until backlog #23 lands. **A free user gesture destroys visible content and creates
a bill to get it back.**

Today the same gesture does none of that: `serve-summary-core.ts:47-57` gates on
`artifacts.summaryMd.status === 'promoted'` and never looks at corrections; `reconcileClassA` records
staleness as `needsRegen` (`reconcile-class-a.ts:22-23, 45, 50`) **beside** a body that keeps serving.

**Why this is the invariant, not a bug in it.** Rule 14's benefit is "resolving touches no blob," and
the invariant-evaluation doc defends it with *"a missing body now surfaces as a loud 404 at serve time
instead of a silent demotion. Louder is better"* (rules-inventory:125). That reasoning covers the
*blob-missing* case. It does not cover this one: nothing is missing, and there is no 404-with-a-repair
— the eligibility predicate is doing the deleting. **A predicate that can evaluate to "none" over a
non-empty set needs a floor**, and today's design has one (`needsRegen` is advisory, not a gate).

**Evidence.** Spec §5.1.1:754-758; §5.2.2:916-920 ("*a generation whose `mdCorrectionsHash` does not
match the video's current corrections is not eligible to be current*"); §5.1.2:697-706;
§5.2.2:925-932; `supabase/migrations/0021_cloud_sync_signals.sql:19-53`;
`lib/html-doc/serve-summary-core.ts:47-57`; `lib/cloud-sync/reconcile-class-a.ts:8, 22-23, 38-50`.

**Change.** Split eligibility into **eligible-to-be-current** and **eligible-to-be-served**, and give
the second a floor: *if no generation is eligible, the newest recorded generation is served, flagged
stale.* That is exactly the shape `resolveMagazineModel` already ships for the budget path
(`serve-doc.ts:90-96`, `readTitleStableModel` → `{status:'ok', stale:true}`), so the precedent and the
UI affordance both exist. Corrections-staleness becomes a **banner**, not a deletion.

---

## HIGH

### A-3 — [invariant 19] "Spend only when the slot is absent" forbids the two regenerations the code exists to perform: drift and a generator-version bump

**Defect.** Rule 19 makes slot-absence a **precondition** of any spend. But the two cases that
legitimately require a paid re-materialize both have a *present*, *readable* artifact:

- **drift** — the model no longer matches the body it is rendered against;
- **version bump** — `isFresh` requires `envelope.generatorVersion === GENERATOR_VERSION`
  (`read-model.ts:20-25`), so bumping `GENERATOR_VERSION` makes every existing model stale by design.

Under rule 19 neither can ever be regenerated: the slot is present, so no spend is permitted, forever.
`serve-doc.ts:73` names all three in one line — *"Absent / drifted / stale-version → materialize under
the reserve RPC"* — and rule 19 admits only the first.

**Failure scenario.** A `GENERATOR_VERSION` bump ships. Every video in the corpus is now serving a
model the new renderer considers stale, and the mechanism that has always repaired that
(regenerate → `writeModelEnvelope` overwrites → self-heal) is closed by rule 19. The version constant
becomes inert, which is worse than a broken deploy because nothing reports it.

**Evidence.** Spec §5.1:684-688; `lib/html-doc/read-model.ts:20-25, 29-39`;
`lib/html-doc/serve-doc.ts:56-57, 73, 101-104` (the comment on why the model uses an overwriting `put`
rather than staged→promote: *"a regenerated model on drift / version-bump must OVERWRITE the stale
blob so the doc self-heals"*).

**Change.** Same fix as A-1 — re-shape rule 19 as *never spend on an **indeterminate** read* rather
than *only spend when absent*. `drifted` and `stale-version` are determinate negatives and must be
spendable. Note the collision with rule 9 while you are there: §4:240-241 says no blob is ever
modified in place, and the model's self-heal is an in-place overwrite; under generation-scoping a
version bump mints a new generation instead, which is fine — but that is a *spend*, so it needs rule
19 to permit it.

### A-4 — [invariant 13] The total order `(created_at, generation_id)` throws away the "never downgrade the format" rung that today's reconciler has, so an older `docVersionMajor` can supersede a newer one

**Defect.** Rule 13 orders by recency alone; eligibility is a *filter*, and `docVersionMajor` is in
neither. Today's equivalent decision is a three-rung ladder, and recency is the **last** rung:
corrections-currency first (`reconcile-class-a.ts:38-40`), **format never downgrades**
(`:43-46`), recency only as the tiebreak within one major (`:49-50`).

Rule 13 preserves rung 1 (as eligibility) and rung 3 (as the order). **Rung 2 is dropped silently.**

**Failure scenario.** A replica pinned to an older build (or a rollback, or a local install a user has
not updated) produces a generation at `docVersion 3.2` after the cloud produced `3.3`. It is newer by
`created_at`, it is eligible, so it becomes `current` — and the user's document silently regresses to
the older format. `reconcileClassA` refuses precisely this today, and its comment says so:
*"format (never downgrade)."* This is the prompt's *"a cheaper or worse regeneration silently
supersedes a better one"* in its concrete form.

Second, smaller edge in the same rule: `created_at` is a **wall clock**, and the design has two
replicas. Today clock skew can only affect rung 3; under rule 13 it decides everything.

**Evidence.** Spec §5.1.1:745-747, 754-758; `lib/cloud-sync/reconcile-class-a.ts:38-50`.

**Change.** Make the derivation a **ranking, not a filter plus a timestamp**: order by
`(docVersionMajor desc, created_at desc, generation_id desc)`, i.e. port the existing ladder verbatim.
It costs one column on `video_generations` and it retires an argument that has already been reviewed
to convergence once.

### A-5 — [invariant 13 + sync] §5.3 is three sentences, and it is where every per-playlist/per-workspace mismatch in the design has to land. Local has no generation store at all

**Defect.** §5.3:1012-1015 says sync "compares two **artifact manifests** and produces one." Three
things make that sentence unimplementable as written, and none is a spec-versus-spec contradiction —
they are all spec-versus-code:

1. **The local backend has no manifest and no generations.** Local metadata is a per-playlist JSON
   `PlaylistIndex` file (`lib/storage/local/local-metadata-store.ts:10-13`,
   `lib/index-store.ts`). Every guarantee the manifest design rests on — the composite FK, the
   `check` constraints, the `security definer` single writer, `on delete cascade` — is a **Postgres**
   guarantee with no local counterpart. So there are not two manifests to compare; there is one, and
   §7:1131-1141's "local holds the materialized authoritative set" does not say what enforces it.
2. **The sync baseline is per (playlist, video); the manifest is per (workspace, video).**
   `manifest.ts:8-9` → `<dataRoot>/<playlistKey>/.cloud-sync-manifest.json`, keyed by `videoId`. Under
   §11.0's one-workspace-per-user dedup, one shared body is covered by **two** baselines and
   reconciled **twice per sync run**, once per playlist, each pass free to reach a different decision.
3. **`current` derived per replica cannot converge without exchanging generation *sets*.** Rule 13
   makes `current` a function of the local set. Two replicas with different sets derive different
   `current` values and *neither is wrong*. Reconciliation therefore has to be set union plus a
   re-derivation — which is a different algorithm from anything `sync-run.ts` does today, and §5.3
   does not name it.

**Evidence.** Spec §5.3:1012-1015; §7:1131-1145; §11.0:1462-1471;
`lib/cloud-sync/manifest.ts:6-29`; `lib/storage/local/local-metadata-store.ts:10-13, 92-102`;
`lib/cloud-sync/sync-run.ts:127-136` (sync keeps only `artifacts.summaryMd` and drops every other
artifact pointer).

**Change.** §5.3 needs to be a section, not a paragraph, and it is the natural home for the decision
the spec has been deferring: **does the local backend get a manifest, or is local a materialization
target with no authority?** §7 says the second; §5.3 says the first. Pick, then say what a sync run
exchanges (generation sets) and what it materializes (display names for the derived `current`).

### A-6 — [invariants 15 + 17] Rule 15's justification is about bytes that are not where it says they are: **no slide asset has ever been written to the Supabase bucket**

**Defect.** Rule 15 ("assets are SOURCES, not artifacts … the age sweeper never collects them",
§8:1300-1304) was adopted to dissolve N-B1 — the finding that the sweeper's second root set would
delete slide assets on day 91, unrecreatable per ADR-0005. It cost the `slide:` slot (§2:80), the
`'asset'` enum member (§5.1:584-585), and the deletion of `pruneSectionAssets` (§8:1306-1312).

**The cloud never writes a slide asset.** `lib/job-queue/dig-handler.ts:115` —
*"resolveSlideTokens intentionally SKIPPED — text-only slice; `[[SLIDE:...]]` tokens preserved
verbatim"* — and `lib/dig/cloud/write-dig-section-blob.ts:26, 39` hardcodes `slides: []`. Sync never
uploads them either (`sync-run.ts:134-136` drops every artifact pointer except `summaryMd`).
The reader is a plain filesystem read inside markdown-it (`render-dig-deeper.ts:104-118`,
`fs.readFileSync`), not a BlobStore call at all.

So the bucket contains **zero** `assets/…` objects. The scheduled cloud sweep could not have deleted
them; ADR-0005's "cannot be recaptured on the host" is true and beside the point, because nothing
captures on the host.

**What this actually changes.** The rule is still *directionally* right — assets are sources. But:
- its **stated justification** does not hold, so nobody can tell whether the rule survives when
  cloud slide capture ships (which is the state it was written for);
- its accepted cost — *"a user who digs a hundred sections and abandons them keeps those frames until
  they delete the video"* (rules-inventory:155-160) — lands on **local disk**, where this design
  specifies no sweeper at all, and where the thing it deletes (`pruneSectionAssets`,
  `slides.ts:207-231`) was the only bound that existed;
- deleting the pruner is therefore not free. §8:1309-1311 applies the deletion test and answers
  *"only unbounded growth of a source kind, which is what sources do and what the explicit-delete path
  already handles."* See A-10: on local, **`deletePlaylist` throws `'cloud-only (unsupported on the
  local backend)'`** (`local-metadata-store.ts:101-102`). There is no explicit-delete path on the
  backend where the bytes are.

**Evidence.** `lib/job-queue/dig-handler.ts:115`; `lib/dig/cloud/write-dig-section-blob.ts:26, 39`;
`lib/dig/slides.ts:170-190` (the only writer, `blobStore.put` of `assets/${videoId}/${assetName}`),
`:207-231` (the pruner, local `fs` only); `lib/html-doc/render-dig-deeper.ts:104-118`;
`lib/cloud-sync/sync-run.ts:127-136`; `lib/storage/local/local-metadata-store.ts:101-102`;
spec §8:1264-1316; `CONTEXT.md:42-44`; ADR-0005.

**Change.** Keep rule 15, re-justify it, and re-scope it: state that assets are a **local-only source
kind today**, that the cloud sweeper's root sets need no asset carve-out *yet*, and that the carve-out
becomes load-bearing the day cloud slide capture ships. Then decide the local bound explicitly —
either keep the pruner (with the attach-aware rule N-H9 asked for) or state that local asset growth
is unbounded until an explicit local delete exists, which today it does not.

### A-7 — [invariant 12] "A generation is body + card, inseparably" is a Postgres schema property, and only one of the two backends has that schema

**Defect.** Rule 12's whole force is *by construction*: `video_generations` carries the card, the
artifact row FKs to it, so "resolving a generation yields both or neither" (§5.2:809-812, §9.1:1384-1390).
That construction is a table, two constraints and an FK. The **local backend has none of them** — the
card fields live as plain keys on the `Video` object inside the per-playlist JSON index, and the body
is a file next to it (`local-metadata-store.ts:10-13`; `lib/pipeline.ts` writes both).

So on the backend where the original pipeline runs, "run #2's card beside run #1's body" — the exact
state Q8 was opened to make inexpressible (§14:1790-1800) — remains **fully expressible**, with no
constraint, no FK and no reader-side check.

**Failure scenario.** A local re-summarize writes the new card into the JSON index and the new body to
disk as two unrelated operations; a crash, an EACCES, or a partial write between them leaves the
catalogue describing an edition the shelf does not hold. Then sync reads `deriveClassASignals`
(`backfill.ts:11`) off that row and propagates the lie to the cloud, where the schema will happily
record it as a complete, constraint-satisfying generation.

**Evidence.** Spec §5.2:801-812, §5.2:934-952 (the `video_generations` DDL); §14:1773-1800;
`lib/storage/local/local-metadata-store.ts:10-13`; `lib/cloud-sync/backfill.ts:11`.

**Change.** Either say rule 12 is **cloud-only in this slice** and name what local does instead (an
honest answer, and it makes §5.3's job clear), or specify the local enforcement — the minimum is a
single atomic write of `{card, bodyKey, generationId}` and a reader that rejects a mismatch. What the
spec must not do is keep asserting "inseparable by construction" without saying which construction.

### A-8 — [invariant 14] "Readability verified once, at record time, by the writer" is verified under `service_role`, which is not the authorization context of any reader

**Defect.** §5.1.1:756-758 retires resolve-time readability on the grounds that the writer verified it.
The writer is the worker, and the worker is `service_role`
(`summary-handler.ts:78` → `getWorkerStorageBundle(serviceClient, …)`), covered by
`artifacts_service_all` (`0007:16-17`). Readers are session clients, covered by the policy this slice
replaces with `workspace_readable(split_part(name,'/',1))` (§5.0:413-422). **The one failure class the
verification cannot see is an RLS denial** — and per `supabase-blob-store.ts:27-37` an RLS denial is
the failure that `get` turns into `null`, i.e. into *absent*.

That is not a hypothetical pairing: it is the exact cascade §5.0.2:496-501 documents as the reason
N-B4 mattered, and B-3 below shows it is still live for a whole class of user.

**Evidence.** Spec §5.1.1:754-758; §5.0:413-422; §5.0.2:496-501;
`lib/job-queue/summary-handler.ts:78`; `supabase/migrations/0007_storage_and_rpcs.sql:12-17`;
`lib/storage/supabase/supabase-blob-store.ts:27-37`.

**Change.** State the limit of the record-time verification in the rule itself — it proves the bytes
landed, not that the reader may read them — and put the reader-context check where it can only run
once: a **post-migration assertion** that a session client can read one object per workspace. That is
the assertion §8:1262 already asks for ("assert the collection, do not assume it") applied to the
predicate instead of the sweeper.

## MEDIUM

### A-9 — [invariant 9] `blob_key` is a stored pointer that is derivable for four of the five slot families, and storing it is what forces local and cloud to agree on one key string

`video_artifacts.blob_key text not null` (§5.1:552). For `summary`, `model`, `dig:*` and `digDeeper`
the key is *fully determined* by `(workspace_id, video_id, generation_id, slot)` via §4:182-186. A
stored copy of a derivable value is a second source of truth for the same fact — the shape rule 9
exists to remove, one level down. It is also what makes §5.3 hard: one column cannot hold both the
cloud key and the local display path, and §7.1:1152-1165 documents three ways that assumption already
fails today (`raw/` prefixes, `path.join` normalization, NFD/NFC). Free re-renders (`pdf:*`, hashed
key) genuinely need a stored value; the generation-scoped families do not.

**Change.** Say whether `blob_key` is authoritative or a cache. If derivable, drop it for the four
generation-scoped kinds and keep it only where the key carries a content hash.

### A-10 — [invariant 18] "An explicit delete outranks retention" has no reachable trigger for most content: there is no per-video delete, and playlist delete does not exist on the local backend

The app has exactly **one** DELETE route: `app/api/playlists/[id]/route.ts:33`. There is no video
delete API — `MetadataStore.deleteVideo` exists but its only caller is an ingest rollback
(`lib/pipeline.ts:311`). And `LocalFsMetadataStore.deletePlaylist` **throws**
(`local-metadata-store.ts:101-102`, *"cloud-only (unsupported on the local backend)"*).

Consequences for rules 15 and 18: rule 15 says assets "are removed only by an explicit delete of the
video or playlist that owns them" — on the backend where assets exist, neither verb exists. Rule 18
says delete outranks the 90-day ceiling — but under §11.0 dedup, a video in two playlists is
unreachable by delete until *every* playlist containing it is deleted, so the ceiling is the only
mechanism for that content and rule 18 never fires.

**Change.** State the reachability precondition as part of rule 18: *the rule is only a correctness
rule where an explicit delete exists.* Then either add a per-video delete to this slice or record that
deduped and local content is governed by retention alone.

### A-11 — [invariant 17] The rule now has to carry two bits, and §3's inventory still does not give all nine kinds one of them

Rule 17 was widened by rule 15 (rules-inventory:127): the key must reveal **paid/free** *and*
**artifact/source**. §3:146-161 lists nine kinds; §4:182-186 defines four shapes. `_staging/<uuid>/…`
announces neither bit and is swept as an orphan under §8's second root set — its whole point is that
it is unreferenced. The grace period is what saves it, which means the grace period is now
load-bearing for correctness rather than for a race, and §8:1325-1327 states it as a *sequencing* rule
("grace period first, kind second") rather than as the guard for an unclassifiable key shape.

**Change.** Add `_staging/` as an explicit third exclusion (never a sweep candidate regardless of age,
collected by its own writer or by an age rule specific to it), rather than relying on the grace period
to cover a key that rule 17 cannot classify.

## Invariants I attacked and could not break

- **9** — I found only A-9 (the stored `blob_key`), which is an application of the rule, not a case
  against it. The workspace-segment exception is already named at §4:202-208 and is correctly reasoned.
- **10** — the restatement from *"the id must never equal a uid"* to *"no predicate may compare the
  segment to `auth.uid()`"* is the best move in the document. It is testable, it has exactly one
  current violation site, and the cost is measured (0.118 ms). Keep. One caveat is B-9 below.
- **11** — the round-2 refinement to "membership **or an explicit revocable capability**" is correct
  and I verified the third mode is real (`lib/share/serve.ts:19-24`, `revoked_at` read through
  `serviceClient`). Nothing further.
- **16** — attacked from the direction of "can unreferencing itself fail toward *pinned*?" It cannot,
  as specified; the transaction boundary is right.
- **18** — the rule is right; A-10 is about reachability, not about the rule.
- **20** — the invariant-evaluation doc already flags the "attached with provenance" relaxation
  (rules-inventory:164-177) and declines to change it unilaterally. I agree with both halves, and add
  one supporting fact: §6.2:1101-1104's `detached` state already makes the set **enumerable**, so the
  provenance UI has a data source the moment someone wants to build it. The decision can stay as it is
  without closing the door.

---

# JOB B — are the round-2 fixes genuine, and what did they introduce?

## BLOCKING

### B-1 — MEASURED: the `video_artifacts` DDL does not create. `operator does not exist: text = artifact_kind`

**Defect.** §5.1:542-560 declares `kind text not null` and constrains it with
`check (kind = slot_kind(slot))`, while the round-2 fix (§5.1:584-594) makes `slot_kind` return the
new `artifact_kind` **enum**. Postgres has no implicit enum↔text equality operator.

**Measured**, running §5.1's DDL verbatim against the local stack (Postgres 17):

```
ERROR:  operator does not exist: text = artifact_kind
LINE 15:   check (kind = r3test.slot_kind(slot)),
HINT:  No operator matches the given name and argument types.
```

The composite FK has the same type problem: it references `video_generations.kind`, which the same fix
widened to the enum (§5.1:603-604), from a `text` column.

**Change.** `kind artifact_kind not null` on both tables. This is the third round in a row in which the
`video_artifacts` DDL has not been executable (C2 round 2, C3 round 2, this). **Run the DDL** before
round 4 — it takes under a minute against `supabase start`, and it would have caught all three.

### B-2 — MEASURED: even with the type fixed, `pdf:*` is still unrepresentable. Round-2 C1 was reworded, not made — the prose says the generation FK is nullable and the DDL says `not null`

**Defect.** The round-2 correction states plainly: *"**the generation FK is nullable** — free re-renders
and assets have none"* (§5.1:581-582). The DDL two paragraphs above still declares
`generation_id text not null` (§5.1:553), and the accompanying
`check ((kind in ('summary','model','dig','digDeeper')) = (generation_id is not null))` (§5.1:559)
then reads *"kind must be one of the four paid kinds"* — because the right-hand side is a tautology
when the column is `not null`. `render` is excluded, so the `pdf:<kind>` slot cannot be inserted.

**Measured**, with `kind` corrected to the enum so the table creates:

```
ERROR:  new row for relation "va2" violates check constraint "va2_check1"
DETAIL:  Failing row contains (…, V, pdf:summary, render, current, k, g1, null, null).
```

**This is the fifth instance of shape #9 the prompt asked for**, and it is the cleanest one yet,
because the fix text and the artifact it fixes are 30 lines apart and disagree: round 2 found four of
six slot families unrepresentable, the correction removed two of the four (`model`, `digDeeper`, by
widening the enum) and left `render` exactly as broken, while asserting all four were closed.

**Change.** `generation_id text` (nullable). Then the second `check` becomes meaningful and the
composite FK must be `match simple` (its default), which correctly skips the check when
`generation_id` is NULL. Add a positive test per slot family — one insert each for `summary`, `model`,
`dig:120`, `digDeeper`, `pdf:summary` — as the acceptance criterion for this DDL.

### B-3 — §5.0.2's seeding fixes existing users by **breaking every new one**: N-B4 moved, it did not go away

**Defect.** §5.0.2:505-521 closes N-B4 by seeding migrated workspaces with the owner's uid
(`insert into workspaces (id, owner_id) select id, id from profiles;`) so one predicate accepts both
layouts. Its table's third row claims a new user is safe: *"A new user's workspace: random UUID —
**TRUE** — and they have no old-layout bytes."*

**They do.** Provisioning for new users goes in `handle_new_user()` (§5.0:376-390), which mints
`gen_random_uuid()`. But `Principal.id` is still `session.userId` — `lib/storage/resolve.ts:93-100`
returns `{ id: session.userId, indexKey }` unconditionally on the supabase backend — and every blob
operation composes `${p.id}/${p.indexKey}/…` (`supabase-blob-store.ts:15-18`). So a user who signs up
**after the schema+policy migration and before the addressing code ships** writes to
`<uid>/<playlistKey>/…` while their workspace id is an unrelated UUID.
`workspace_readable('<uid>')` finds no workspace → denied.

And §5.0.2 is precisely the section that argues this window does not exist: *"**N-B4 does not exist.**
There is no window in which blobs are unreadable, so the denial-reads-as-absent cascade never fires"*
(§5.0.2:523-525), and *"§10 stops being a cutover … incremental, interruptible and reversible"*
(:526-529). Both claims are false for this cohort, and the incrementality argument is what makes the
cohort exist: the longer the migration runs, the more users sign up into it.

**Failure scenario, both verbs.** *Read:* `SupabaseBlobStore.get` collapses the denial into `null`
(`:27-37`), so `serve-summary-core.ts:66-67` returns **409 "repair needed"** for content that is
present, and `readFreshMagazineModel` reports `not_ready` — the asymmetric, smoke-test-invisible
failure §5.0.2:498-501 describes. *Write:* the policy is `for all` with a `with check`, so the session
client's `writeModelEnvelope` `put` throws (`:22-25`) — a 500 on the serve path. The worker is
unaffected (`artifacts_service_all`), so a worker-only smoke test passes.

**Evidence.** Spec §5.0:376-390, §5.0.2:505-536; `lib/storage/resolve.ts:93-100`;
`lib/storage/supabase/supabase-blob-store.ts:15-18, 22-25, 27-37`;
`supabase/migrations/0003_provisioning.sql:2-11`; `supabase/migrations/0007_storage_and_rpcs.sql:12-17`;
`lib/html-doc/serve-summary-core.ts:66-67`.

**Change.** `handle_new_user()` must seed `id = new.id` too, for as long as `Principal.id` is the uid:
`insert into public.workspaces (id, owner_id) values (new.id, new.id);`. Switching to
`gen_random_uuid()` becomes a **later migration**, gated on the addressing code being live — and that
gating is the thing to write down, because §5.0.2's whole argument is that no gate is needed.

### B-4 — The "which record says a summary is authoritative" migration list is incomplete: share-token **minting** and every **live share link** also read `artifacts.summaryMd`, and neither is named

**Defect.** N-H8 (round 2) established that `reserve_serve_model`'s readiness gate reads
`v.data->'artifacts'->'summaryMd'->>'status' = 'promoted'` and must be re-derived against the manifest.
§11.0:1522-1528 records that as the rule. It names **one** consumer. There are more, and two are on
the anonymous share path:

| Consumer | Site | What breaks when `artifacts.summaryMd` stops being written |
|---|---|---|
| `reserve_serve_model` | `0020:204-207` | every model generation returns `denied` (already recorded) |
| **`create_share_token`** | **`0017:23-28`** | **`raise exception 'create_share_token: denied'` — nobody can mint a share link** |
| **`getShareServeContext`** | **`lib/share/serve.ts:44-48`** | **every already-minted, unexpired, unrevoked link returns `denied`** |
| `summary-handler`'s idempotency skip | `lib/job-queue/summary-handler.ts:84-90` | the skip stops firing → **re-runs and re-bills Gemini** for an already-promoted summary |
| `SupabaseMetadataStore.summaryReady` | `lib/storage/supabase/supabase-metadata-store.ts:54-55` | the playlist list shows every video as not-ready |
| `resolveSummaryKey` (dig) | `lib/dig/cloud/resolve-summary-key.ts:13-14` | dig enqueue cannot find the summary |
| `reconcileCloudBase` | `lib/cloud-sync/reconcile-serial.ts:296` | writes the JSON the design retired |

The share pair is the sharpest: `create_share_token` **raises**, so minting fails loudly, while
`getShareServeContext` returns the deliberately coarse `denied` — so existing links die **silently and
indistinguishably from revocation**. And the idempotency row is a *money* row: `summary-handler.ts:84-90`
is the only thing standing between a re-delivered job and a second paid Gemini summarize.

**Evidence.** `supabase/migrations/0017_share_token_id_return.sql:23-28`;
`supabase/migrations/0020_reservation_release.sql:204-207`; `lib/share/serve.ts:44-48`;
`lib/job-queue/summary-handler.ts:84-90`; `lib/storage/supabase/supabase-metadata-store.ts:54-55`;
`lib/dig/cloud/resolve-summary-key.ts:13-14`; `lib/cloud-sync/reconcile-serial.ts:296`;
spec §11.0:1522-1528.

**Change.** §11.0's rule must be *"enumerate every reader of `artifacts.summaryMd.{key,status}` and
state what each becomes"*, with the table above (or a fresh grep — `grep -rn "summaryMd" lib app
supabase` returns 39 files) as the checklist. This is the same *"at fix time, list the consumers"*
rule `dev-process.md` already carries, applied to a jsonb key instead of a column.

### B-5 — MEASURED: `check (kind = slot_kind(slot))` fails **open**. `slot='html'`, `kind='dig'` is accepted

**Defect.** `slot_kind` (§5.1:586-594) is a `case` with **no `else`**, so it returns NULL for any slot
it does not enumerate. `kind = NULL` evaluates to UNKNOWN, and a CHECK constraint is satisfied by
UNKNOWN. The guard Codex B1 asked for — *"without them a row can assert `slot='summary'` over dig
bytes"* — does not guard.

**Measured:**

```
insert into va2 (…, slot, kind, …) values (…, 'html', 'dig', …);
INSERT 0 1
 slot | kind | computed
------+------+----------
 html | dig  |            ← slot_kind('html') is NULL, so the check passed
```

**And there is a real unenumerated slot family.** §3:146-161 lists HTML as one of the nine blob kinds
and §8:1226-1229 reasons about `htmls/…` retention ("free blobs live exactly as long as they are the
authoritative copy of their slot") — but §2:80's slot vocabulary has **no `html` slot**, so HTML has no
slot to be the authoritative copy of. Either it gets a slot (and `slot_kind` must map it) or §8 must
say HTML is never in the manifest and is always collected as a no-row orphan.

**Change.** `else raise exception` in `slot_kind` (it can stay `immutable`), or
`check (kind = slot_kind(slot) and slot_kind(slot) is not null)`. Mutation-test it: insert an
unrecognized slot and require rejection. Add the `html` slot or state its exclusion.

### B-6 — MEASURED: §14 Q6's replacement cross-tenant guard cannot be created. This is round-2 C2 verbatim, in the fix that closed Q6

**Defect.** §14 Q6:1760-1765 writes the replacement for ADR-0002's injection guard as:
*"`workspaces` carries `unique (id, owner_id)`, and `jobs` gains
`foreign key (workspace_id, owner_id) references workspaces (id, owner_id)`."* §5.0's `workspaces` DDL
(:348-355) declares `id uuid primary key` and `unique (owner_id)` — **not** `unique (id, owner_id)`.
Physical rule 3 (rules-inventory:28) applies exactly as it did to the 4-tuple FK in round 2.

**Measured**, with §5.0's `workspaces` DDL verbatim:

```
ERROR:  there is no unique constraint matching given keys for referenced table "workspaces"
```

`playlists` shows the pattern the spec should have copied: `unique (id, owner_id)` with the comment
*"enables the composite FK below"* (`0001:18`).

**Change.** Add `unique (id, owner_id)` to §5.0's `workspaces` DDL. It is trivially satisfied given the
PK on `id`. Note that this is the second recurrence of the same physical rule in the same document —
worth one line in the plan's acceptance criteria: *every composite FK names a unique constraint that
exists in this spec's own DDL.*

## HIGH

### B-7 — The same Q6 fix requires `jobs.workspace_id not null` on a populated table — physical rule 4, fixed for `playlists` in round 2 and never re-derived for `jobs`

§14 Q6:1760-1765 needs `jobs` to carry `workspace_id`. §5.0's three-phase migration (:363-371) covers
`playlists` only; §5.0.1:468 adds the column to `videos` — also as a bare
`alter table videos add column workspace_id uuid not null references workspaces(id)`, which fails on a
populated table for the identical reason C3 identified. Neither `jobs` nor `videos` gets a
create→backfill→`set not null` sequence.

`0009` is instructive here, because its own comment records the escape hatch that no longer exists:
*"jobs is created fresh by 0008 on every `db reset` (empty at this point) → **safe re-key**"*
(`0009:2`). Production `jobs` is not empty, and the terminal-status rows are what
`jobs_idem_active` dedupes against.

**Change.** Give **every** new `not null` FK column the three-phase treatment — `playlists`, `videos`,
`jobs` — and say what `workspace_id` is backfilled *from* in each case (`owner_id` for the first two;
for `jobs`, via `playlist_id → playlists.workspace_id`). State whether the old
`jobs(playlist_id, owner_id) → playlists(id, owner_id)` FK is kept alongside the new one or replaced.

### B-8 — Re-keying assets breaks image references baked into immutable dig-markdown blobs, and the round-2 "dual-read fallback" cannot reach the reader that resolves them

**Defect.** §8:1314-1316 re-keys assets to the timestamp window alone. The round-2 fix (§8:1280-1286)
prescribes *"a dual-read fallback (new key, then old) until a rewrite pass completes."* Two problems:

1. **The reference lives inside a paid blob.** `slides.ts:190` writes
   `![caption](assets/${videoId}/${assetName})` **into the dig markdown**. Under §4:240-241 no blob is
   ever modified in place, so the "rewrite pass" either violates generation-immutability or mints a new
   generation for every dug section ever produced. The fallback is not transitional; it is permanent.
2. **The reader is not the BlobStore.** Resolution happens inside markdown-it's image rule —
   `render-dig-deeper.ts:104-118`, `fs.readFileSync(absPath)` against a filesystem path derived from
   `path.dirname(mdPath)`. A dual read added at the store seam never runs. And the miss is **silent**:
   `catch → return '<span class="missing-slide">…'` — a visible placeholder, no error, no log.

**Change.** Specify the fallback at the point that resolves the reference (the markdown-it rule), or
do not re-key at all. Given A-6 (assets are local-only and the bucket holds none), *not re-keying* is
now the cheaper answer: the stated reason for dropping `sectionId` was that it is a per-generation
value in a generation-free key, which is a purity argument, not a defect report.

### B-9 — `workspace_readable`'s correctness depends on an ownership property the spec never states, and the failure mode is "everything reads as absent"

`workspace_readable` is `security definer` reading `public.workspaces` (§5.0:413-422). §5.0 never says
whether `workspaces` has RLS, and every other table in this schema is created with
`enable` + **`force`** row level security (`0001:7-8, 20-21`). `force` applies RLS to the table owner
as well, so a definer function owned by a non-`BYPASSRLS` role would see zero rows and return **false
for every caller** — every object denied, and per `get`'s collapse, every artifact reads as *absent*.

I verified this does **not** fire on Supabase: `postgres` carries `rolbypassrls = t`
(`select rolname, rolsuper, rolbypassrls from pg_roles` on the local stack →
`postgres | f | t`, `authenticated | f | f`, `anon | f | f`). So the design is correct *as deployed*.
That is exactly why it belongs in the spec: the property is load-bearing, invisible at the call site,
and silent when violated — the same reachability failure ADR-0005 had (`dev-process.md` §6:
*"anchor every ADR where the question arises"*).

**Change.** One sentence in §5.0: *`workspace_readable` must be owned by a role with `BYPASSRLS`
(`postgres` on Supabase), or `workspaces` must carry a policy the definer's role satisfies.* Plus the
assertion from A-8 — one session-client read per workspace, post-migration.

### B-10 — The sweeper's second root set is a recursive per-directory walk, and the new template multiplies the node count by the generation count

§8:1201-1206 bounds the full-bucket root set by "workspace prefix with a durable cursor." The
implementation it will use is `collectObjectPaths` (`supabase-blob-store.ts:132-152`): a **recursive**
walk issuing one paginated `list` per pseudo-directory, with the cursor (`offset`) scoped to a single
directory. Under `<ws>/videos/<vid>/<gen>/…` the node count is
`workspaces × videos × (generations + 1)`, and §8's 90-day retention is what makes `generations`
grow. A durable cursor across a depth-first recursion is not the same object as the per-directory
offset that exists.

**One thing to record as already satisfied**, because it is the half that matters most and the spec
should not re-specify it: `collectObjectPaths` **throws** on a list error (`:138`, `if (error) throw
error`). §8:1204-1206's rule — *"a `list` page that errors ABORTS the sweep"* — is already the
behaviour of the code the sweeper will call. Say so, and pin it with a test, rather than describing it
as new work.

**Change.** Specify the cursor as a **key-ordered resume point** (last object path processed) rather
than a per-directory offset, or add a flat `list` at the seam. State the expected node count so the
sweep's cost is a number rather than "bounded."

### B-11 — §5.2's `card` completeness check is the right shape but does not cover the two fields the finding was about, on the producer the finding named

The round-2 correction (§5.2:995-998) enforces card completeness with
`check (kind <> 'summary' or card ?& array['tldr','takeaways','docVersion','mdGeneratedAt','processedAt','mdCorrectionsHash'])`.
That is a genuine improvement over "every document fact `not null`" and it *is* a schema fact. It is
also, as written, a constraint the **live producer cannot satisfy**: `summary-handler.ts:145-164`
builds its `Video` with `docVersion` and `processedAt` and **no `mdGeneratedAt`, no
`mdCorrectionsHash`** — verified again this round, unchanged.

So the constraint converts H2's silent-NULL failure into a **hard insert rejection on the worker's
persist path**, i.e. every cloud summarize job fails after the Gemini call has been paid for. The spec
does say *"fix `summary-handler.ts` **in this slice** — it is one of the two producers"* (§5.2:1002),
which is right; what is missing is the **ordering** statement: the producer fix must land **before or
with** the constraint, never after, and the failure mode if it does not is a paid-then-discarded run.

**Change.** Name the ordering explicitly in §5.2 and again in §10, and add the producer fix as a
prerequisite task rather than a parenthetical. Note `as any` on a test double opts out of the
compiler check (§5.2:1001 already says this) — so the acceptance test must be a real insert.

## MEDIUM

**M-R3-1 — `record_artifact` still cannot write `state`, so §6.2's detached row has no writer.**
§5.1:634-641 explains that `state` is not a parameter because detachment is a separate verb
(`detach_artifact`) — a reasonable answer. But `detach_artifact` is named and never specified, and per
round-2 A14(b) the transition `dig:120 → dig:120@abc` is a **primary-key change**, i.e. a delete+insert,
not an update. §6.2:1101-1104 depends on that row existing. Specify the verb, its return type, and
whether the old row is removed in the same statement.

**M-R3-2 — `SlotRead` has no variant for "recorded but not eligible."** The type (§5.1:667-672) is
`ok | absent | unreadable`. Under rule 13 a fourth state exists and is common: generations are
recorded but none is eligible (A-2's corrections case, §5.1.2's stale `source_generation_id`).
Collapsing it into `absent` is what makes A-1's spend reachable and A-2's disappearance silent.
Add `{ ok: false; reason: 'ineligible'; newestGenerationId: string; why: … }` — **required, not
optional**, per the cross-module nullable rule in `dev-process.md`.

**M-R3-3 — §5.0.1's `workspace_videos` gives `personalNote`/`personalScore` no home, and the spec
says a plan cannot be written without one.** §5.0.1:486-489 states this openly and correctly. Flagging
it only to note it is still open going into round 3 and is a **product** question, so it is one of the
few things here that genuinely needs the human rather than another review round.

**M-R3-4 — `CONTEXT.md` self-contradiction (round-2 M-R2-2) is still live.** `:8` states as domain law
that *"each playlist stores its **own** copy of that video's summary (artifacts are addressed per
playlist)"*; `:60` states the manifest is *"keyed by workspace and video, **never** by playlist."* An
implementer reading `CONTEXT.md` — which is the file the process says to read first — gets the
retracted position.

**M-R3-5 — ADR-0006 (round-2 M-R2-3) is still unreconciled.** `:7` `<tenantId>`; `:30` "trivially
sufficient", which §5.1.1:794-799 retracts on the evidence of five review rounds; `:68-72` the
withdrawn "still moves every object" claim. Two rounds have asked; it is cheap and it is what a plan
author will read instead of a 1875-line spec.

## LOW

**L-R3-1 — §2:80's slot vocabulary and §3:146-161's nine kinds still do not line up.** `html` and
`_staging` have no slot; `pdf (local)` and `pdf (cloud)` are one slot with two key shapes. Rule 17
needs the mapping to be total.

**L-R3-2 — §4:185 still shows `assets/<sectionId>-<start>-<end>.jpg`** while §8:1314-1316 removes
`sectionId`. Round-2 M-R2-1 asked for this; §4 is the template an implementer copies. (If B-8's advice
is taken and the re-key is dropped, fix §8 instead.)

**L-R3-3 — `video_generations`' DDL block is still not valid SQL** (§5.2:939-948: no `create table`, no
commas), while `video_artifacts`' block is. Round-2 L-R2-1. It matters slightly more now that B-1/B-2
show the *valid-looking* block is the one that does not run.

---

## Verdict

**NOT CONVERGED.** 6 Blocking, 9 High, 5 Medium, 3 Low.

Three observations for whoever sequences the fixes:

1. **The DDL has now failed to create in three consecutive rounds.** Round 2 found C2 and C3 by
   reading; this round found B-1, B-2 and B-6 by **running it**, in about a minute against
   `supabase start`. Executing the spec's SQL should be a gate, not a review technique.
2. **The invariant attack was worth more than the consistency pass.** A-1, A-2 and A-6 are not
   internal contradictions and no amount of cross-derivation would have surfaced them: each is a rule
   that is coherent with every other rule and wrong against the code. A-6 in particular retires a
   Blocking from round 2 and the three fixes built on it.
3. **Fix order.** A-1/A-2/M-R3-2 are one decision (what `SlotRead` returns and when a spend is
   allowed) and they gate the money path — do them first. B-1/B-2/B-5/B-6/B-7 are one DDL pass. B-3
   and B-4 are one deploy story with N-B4 and N-H8. A-5 (§5.3) and A-7 (rule 12 on local) are one
   question — *does the local backend get a manifest?* — and it is the largest thing still unanswered.
