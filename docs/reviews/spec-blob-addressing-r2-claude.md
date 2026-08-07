# Adversarial review — Stable Blob Addressing design spec, ROUND 2 (Claude)

**Artifact:** `docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md` @ `f2d4d3a`
(branch `docs/blob-addressing-decisions`), plus `CONTEXT.md` and `docs/adr/0006-stable-blob-addressing.md`
**Round-1 inputs:** `spec-blob-addressing-r1-{claude,codex,coordinator}.md`
**Method:** every judgment below was checked against code or SQL I opened in this session. Where the
spec's fix is only a claim, I say what the code says instead.

**Verdict: NOT CONVERGED.** 4 new Blocking, 8 new High, 6 Medium, 3 Low — plus **two round-1
Blocking findings that were never addressed at all** (coordinator B1 and B2; see the last section).

The round-1 fixes are individually thoughtful and most of them land. They fail *as a set*: five of them
(§5.0's workspace, §5.1's `kind`/`state`/spans, §5.1's `publish_slot`, §5.2.2's corrections CAS, §8's
second GC root set) were written independently into different sections and **none of them was
re-derived against the others**. Every Blocking below is an interaction between two fixes, not a defect
in either one.

---

## JOB A — verdict on each of the 14 round-1 fixes

| # | Finding | Verdict |
|---|---|---|
| 1 | B1 — video judgments vs frontmatter | **Fixed but incomplete** — see A1 |
| 2 | B2 — nothing produced a `workspaceId` | **Fixed but incomplete** — see N-B4, N-H6 |
| 3 | B3 — three predicates | **Actually fixed** (§4:192-200, §5.0:369-378, §11.2:1194-1198 and §2:77 now all say the same thing) |
| 4 | B5 — playlist delete pinned blobs | **Reworded; the defect moved** — see N-B1 |
| 5 | Codex B1 — slot over wrong bytes | **Reworded but the defect survives** — see N-H1 |
| 6 | Codex B2 — refcount TOCTOU | **Fixed but incomplete** — see A6 |
| 7 | H1 — absent vs unreadable on the manifest | **Fixed but incomplete** — see N-H5 |
| 8 | H2 — card completeness | **Reworded; not a schema fact** — see N-H3 |
| 9 | H5 — two playlist-keyed money arbiters | **Fixed but incomplete** — see N-H7, N-H8 |
| 10 | H6 — assets misclassified / per-generation key | **Reworded; the defect moved** — see N-B1, N-H9 |
| 11 | H7 — nothing collected `video_generations` | **Actually fixed** (§8:879-889 gives it a lifecycle and names the FK) |
| 12 | Codex H1 — corrections change mid-flight | **Reworded but unimplementable** — see N-B2 |
| 13 | M4 — "the loser retries" | **Reworded; the defect moved** — see N-H4 |
| 14 | §6.1/§6.2 — threshold, detached, spans | **Fixed but incomplete** — see A14 |

Detail on the ones whose verdict is not self-evident from the new findings:

**A1 (B1).** The writer-authoritative rule (§5.2.1:573-580) is the right shape and it does close the
frontmatter lie for generations ≥ 2. Two gaps remain. (a) *First generation:* there are no prior
judgments, so generation 1 rolls them fresh — correct, and the spec should say so, because "the first
generation sets them" (§5.2.1:543) now means something different from "the writer is given them".
(b) *A user who edits a judgment directly:* nothing can edit them today (`update_video_annotations`'s
allowlist is `{personalScore, personalNote, corrections, archived}` — `0021:24`), so the hole is not
live. But §5.2.1:545-546 explicitly promises *"a user who wants fresh judgments can ask for them"* —
that path, when built, must feed the writer, not the row, and the spec does not say so. **And the
judgments live on a per-playlist row** — see coordinator B1, unfixed.

**A6 (Codex B2).** §11.0:1125-1128 correctly makes the unreference a single transactional statement
inside a definer RPC. What it locks is still unstated: *"locks the workspace's reference set"* names no
row and no lock mode. `delete from video_artifacts where … and not exists (surviving videos row)` does
**not** exclude a concurrent ingest — a concurrent `insert into videos` takes no lock the `not exists`
subquery can see, so under READ COMMITTED the delete and the insert both succeed and the new
membership references deleted rows. Excluding it needs an explicit `select … for update` on
`playlists`/`workspaces` **taken by both writers**, or `serializable`. Naming the RPC is not the same as
specifying the lock, and the ingest side is not mentioned at all.

**A14 (§6.1/§6.2).** The both-directions ratio (§6.1:754-756) is correct and closes H3 and Codex H4;
the degenerate-span rule (§6.1:760-763) closes M8. The `detached` state and persisted spans are the
right mechanisms. Incomplete on three points: (a) `start_sec`/`end_sec` are nullable with no check
tying them to dig slots — *"dig slots only; §6.2(b)"* is a comment, and §6.2:796-799's "persist at write
time" is unenforceable (see N-B3, which is why nothing can write them); (b) transitioning a dig from
`dig:120` to `dig:120@abc` is a **primary-key change**, i.e. a delete+insert, and `publish_slot` has no
verb for it; (c) a detached row is referenced forever, so §8 can never collect it — which is the
decision, but it means paid blobs no reader can reach accumulate without bound and without a surface,
and §8:984-991 explicitly forecloses re-opening accumulation as an objection.

---

## BLOCKING

### N-B1 — Slide assets can never hold a manifest row, so §8's NEW second root set collects them — the exact bytes the H6 fix just reclassified as unrecreatable

**This is the fourth instance of root-cause shape 9 the prompt asked for.** Round 1 said assets were
misclassified as free and would be deleted when not current. The fix (§8:935-953) reclassified them as
paid — moving them from "deleted immediately" to "deleted at day 90" — and the *other* round-1 fix
(§8:875-877, the sweeper's second root set) is what now guarantees the deletion happens.

**Defect.** `video_artifacts.generation_id text not null` plus the composite FK to `video_generations`
(§5.1:408, 413-414) means **every manifest row must belong to a generation**. §4:243-246 places assets
*outside* every generation, deliberately. So an asset cannot be represented in the manifest. §8's second
root set — *"objects with no manifest row at all"* (§8:875-877) — therefore matches **every slide asset
ever written**, and §8:892-900's retention rule ("not current ⇒ delete; paid ⇒ 90 days") sweeps them at
day 90. There is no state in which an asset is "current".

**Failure scenario.** A user digs section 120 in March; slides are captured (a video download plus a
re-encode) and embedded in the dig-deeper doc. The dig stays attached and servable for a year. On day
91 the scheduled sweep lists the bucket, finds `W/videos/V/assets/900-905.jpg` with no manifest row,
classifies it paid from the key, sees it 90 days old, and deletes it. The dig now renders broken images
and **the bytes cannot be recreated**: `CONTEXT.md:44` classes a slide screenshot source-of-truth
because it "cannot be recaptured at all on a hosted server" (ADR-0005 — the container ships no ffmpeg).
The system enters "repair needed" with no repair available.

**Evidence.** Spec §4:185, §4:243-246; §5.1:399-416 (`generation_id … not null`, FK, `check`);
§8:875-877; §8:892-900; §8:935-940; `CONTEXT.md:44`; `lib/dig/slides.ts:185` (`blobStore.put` of
`assets/${videoId}/${assetName}`).

**Change.** Assets need a root of their own — either a manifest row shape that does not require a
generation (`generation_id` nullable with a check keyed on `kind='asset'`, and a `kind` domain that
admits it), or an explicit rule that `assets/` is a *third* root set the sweeper never collects except
under an explicit video/playlist delete. Whichever is chosen, §2's slot list and §5.1's `check` must
agree with it. Do not leave "assets are paid" as the only protection: paid means 90 days, and 90 days
means deleted.

---

### N-B2 — The corrections CAS is unimplementable: corrections are per-playlist, publication is per-workspace

**Defect.** §5.2.2:606-614 requires publish to compare-and-swap on "the current corrections hash". Under
§11.0/§5.0 a video shared by N playlists in one workspace resolves **one** manifest row and **one**
body, but corrections are stored on the **per-playlist `videos` row** and written by an RPC that takes a
playlist id. There is no such thing as "the current corrections" for a `(workspace, video)` pair.

**Evidence.** `supabase/migrations/0001_core_schema.sql:23-30` — `videos` primary key is
`(playlist_id, video_id)`. `supabase/migrations/0021_cloud_sync_signals.sql:19-24` —
`update_video_annotations(p_playlist_id uuid, p_video_id text, …)` with allowlist
`{personalScore, personalNote, corrections, archived}`; corrections are Class-B, stamped per field into
`annotationsEditedAt`. Spec §5.1:444-448 — `publish_slot(p_workspace uuid, p_video text, …)` has no
playlist parameter and no corrections parameter.

**Failure scenario.** Playlists P1 and P2 in workspace W both contain V. The user corrects
*"Clawcode" → "Claude Code"* under P1. A worker generates a new summary for V. Which hash does publish
CAS against — P1's, P2's (`NULL`), or the newest of the two? If P1's: the shared body now contains a
correction P2's row says was never applied, and P2's `mdCorrectionsHash` describes text that no longer
exists. If P2's: the correction the user typed and paid a Gemini pass for is silently dropped, which is
the precise defect §5.2.2 exists to close. There is no third answer, and the spec picks none.

**This is coordinator-B1 arriving through a different door**, and it is why that finding cannot be left
unaddressed: §5.2 bound the *card* to the generation and left the video-scoped scalars on a
**playlist-scoped row**. Every fix layered on top of §5.2 inherits the ambiguity.

**Change.** Settle where the human/video-scoped fields live before the CAS can be written. Either
introduce the workspace-scoped video record coordinator B2 asked for and move corrections + judgments
onto it, or state that dedup applies to the body only and name which playlist's row a publisher CASes
against. The CAS rule cannot be specified before that.

---

### N-B3 — `publish_slot` cannot write the columns three other round-1 fixes added, and it is declared the only writer

**Defect.** §5.1:434-448 makes `publish_slot` the *single* writer (`force row level security`,
service-role-only grants, client policy `select` only). Its signature is
`publish_slot(p_workspace uuid, p_video text, p_slot text, p_expected_key text, p_new_key text,
p_generation text) returns text`. The table it writes has `kind not null` **with no default**,
`state not null default 'current'`, `start_sec`, `end_sec`. Three of those are round-1 fixes added in
the same edit, and **none is a parameter**. The corrections CAS (§5.2.2) also has to happen "at
publish", and has no parameter either.

**Failure scenario.** A plan cannot be written for the publish path. An implementer must either (a) add
parameters the spec does not have — at which point the `check` in §5.1:415 and the FK in §5.1:413-414
have to be re-derived against them, or (b) derive `kind` inside the RPC from `p_slot`, which duplicates
the `check` in procedural code, or (c) let a second writer set `state`/`start_sec`/`end_sec`, which
destroys the single-writer property that M3's fix exists to establish. §6.2:796-799's "persist
`start_sec`/`end_sec` **at write time**" is unsatisfiable through the only writer the design allows.

**Evidence.** Spec §5.1:399-416 (table), 434-448 (RPC + RLS), §5.2.2:606-614 (CAS at publish),
§6.2:796-799 (spans at write time). Precedent for how much protocol lives in a definer writer:
`0020:186-260`, where `reserve_serve_model` carries every arbiter it needs as an explicit parameter or
derives it from `auth.uid()` and never from a caller-supplied owner.

**Change.** Re-specify `publish_slot` after the other four fixes, not before: it needs `kind`,
`state`, the optional span pair, the expected corrections hash, and a **typed three-way return**
(`published` / `lost` / error) rather than `returns text`. Also specify the detach verb (a PK change,
per A14b) and the `p_expected_key is null` case — `where blob_key = NULL` never matches, so the
"expect no row" path must be `insert … on conflict do nothing` with a row-count check, not a
conditional update.

---

### N-B4 — Replacing the storage predicate makes every existing blob unreadable to session clients, and nothing sequences that against the §10 corpus migration

**Defect.** §5.0:369-378 replaces `artifacts_owner_rw`'s body with
`workspace_readable(split_part(name,'/',1))`, and §5.0:361-365 requires the workspace id to be an
**independent UUID, never equal to a uid**. Every object in the bucket today has a **uid** in segment 1.
`workspace_readable` returns `exists (select 1 from workspaces where id::text = p_ws and owner_id =
auth.uid())` — for a uid-valued segment that is **false for every row**. The moment the migration
applies, every pre-existing object is denied to every session client. §10 then moves the corpus — but a
whole-corpus copy of paid content is not instantaneous and is not in the same transaction.

**Failure scenario.** Deploy the migration at 09:00. Every authenticated read of a summary, model, HTML
or PDF returns denied until the last byte of the migration lands. `SupabaseBlobStore.get` **collapses
an RLS denial into `null`** (`lib/storage/supabase/supabase-blob-store.ts:27-37`, `provesAbsence =
false`), so the app does not report an outage — it reports *absent artifacts*. On the serve path that
is worse than an outage: `serve-doc.ts:69-71`'s money guard only catches `unreadable` from `tryGet`;
`readFreshMagazineModel` runs first and its miss is indistinguishable from "not yet materialized", so
users see "repair needed" and regeneration pressure against paid content that exists. The worker is
unaffected (`artifacts_service_all`, `0007:16-17`), which means the failure is asymmetric and easy to
miss in a smoke test.

**Evidence.** `supabase/migrations/0007_storage_and_rpcs.sql:12-15` (current policy),
`:16-17` (service_role policy); spec §5.0:361-378; §10:1064-1069;
`lib/storage/supabase/supabase-blob-store.ts:27-37`.

**Change.** Specify the cutover, and note that the obvious bridge — `or split_part(name,'/',1) =
auth.uid()::text` during the migration window — is the **unrevocable identity grant** §11.2:1185-1198
forbids, so it must be removed on a deadline and that removal must be a migration, not a note. The
alternative (move bytes first under service_role, flip the predicate last) needs §10 to be a real,
costed, resumable tool — which Claude M9 said it is not and which is still unaddressed (§10 is
unchanged since round 1).

---

## HIGH

### N-H1 — The composite FK cannot be created, and the `check` is wrong for four of the six slot shapes §2 defines

**Defect (two parts, one block of DDL).**

1. `foreign key (workspace_id, video_id, generation_id, kind) references video_generations
   (workspace_id, video_id, generation_id, kind)` — `video_generations`' primary key is the **three**
   columns `(workspace_id, video_id, generation_id)` (§5.2:638). Postgres requires a unique constraint
   or index **matching the referenced column list exactly**; a 4-column FK against a 3-column PK raises
   *"there is no unique constraint matching given keys for referenced table"*. The migration does not
   apply.
2. `check (kind = case when slot like 'dig:%' then 'dig' else 'summary' end)` forces `kind='summary'`
   for **every** non-dig slot. §2:80 defines six slot shapes: `summary`, `model`, `dig:<sectionId>`,
   `digDeeper`, `pdf:<kind>`, `slide:<id>`. Four of them (`model`, `digDeeper`, `pdf:*`, `slide:*`) are
   therefore required to reference a **summary generation** — and by the H2 fix (§5.2:677-681) a summary
   generation must carry a complete, non-null card. So a PDF re-render or a dig-deeper companion has to
   borrow or fabricate a summarize run's card. `slide:*` cannot satisfy it at all (N-B1).

**Failure scenario.** The magazine model is produced by a *different* paid run from the summary
(`serve-doc.ts:108-116`, `generateMagazineModel` under `reserve_serve_model`). Attributing it to the
summary's generation makes `video_generations.kind` a lie about what run produced the bytes — the
`kind` column exists precisely to stop that (Codex B1). Minting a `kind='model'` generation instead
violates the `check`.

**Change.** Add `unique (workspace_id, video_id, generation_id, kind)` to `video_generations`, and
replace the `case` expression with an explicit slot-prefix → kind mapping over all six shapes, with
`kind` a domain/enum that includes at least `summary | dig | model | render | asset`. Then re-derive
which kinds require a non-null card.

### N-H2 — Nothing binds the `model` slot to the *current* summary generation, and §4.2.1 retires the only drift check that exists

**Defect.** §4.2.1:333-334 retires `sameTitles` on the grounds that *"a model envelope stored under its
generation is matched by `generationId`, not by comparing heading strings."* No constraint, rule or RPC
anywhere in the spec requires the `model` slot's `generation_id` to equal the `summary` slot's.

**Failure scenario.** Summary is republished as generation *def*. The `model` slot still points at
*abc*'s `model.json`. Today `readFreshMagazineModel` would catch this — the envelope's `sourceSections`
no longer match the parsed body's titles, so it re-materializes (`CONTEXT.md:47`, "regenerated on view
whenever it is absent, unparseable, or **drifted**"). With `sameTitles` retired and no replacement, the
reader serves *abc*'s magazine model over *def*'s body: a row claiming something the blob does not
satisfy (shape 4), on the surface the user actually reads, and **silently** — the whole point of the
drift check was that a restyle of the wrong body is not visibly wrong.

**Evidence.** Spec §4.2.1:333-334; §5.1:399-416 (no cross-slot constraint); `CONTEXT.md:47`;
`lib/html-doc/serve-doc.ts:55-57, 108-116`.

**Change.** State the rule: resolving `model` requires `model.generation_id = summary.generation_id`,
else treat as absent-and-rematerialize. That is a *reader* rule and a *publish* rule (republishing
`summary` must detach or invalidate `model`), and neither exists. Note this also decides whether a
summary republish silently voids a paid model — a money consequence §11.0's H5 box does not cover.

### N-H3 — H2's fix is stated as a schema fact and the schema cannot express it

**Defect.** §5.2:677-681 rules that card completeness must be *"a **schema fact**, not a convention —
every document fact `not null` on `video_generations`"*. The table two paragraphs earlier stores the
card as a **single nullable jsonb column**: `card jsonb -- the summary card; NULL for a dig generation`
(§5.2:636). `not null` on a jsonb key is not expressible as a column constraint, and the column itself
must stay nullable for dig generations.

**Failure scenario.** The implementer writes `card jsonb` as specified, the compiler-side card type
catches the two producers the reviewer named, and a third producer (or a `as any` test double, which
§5.2:679-680 itself warns about) writes `{"tldr": …}` with no `mdGeneratedAt`. Nothing rejects it.
`reconcile-class-a.ts:49`'s `(a ?? '') > (b ?? '')` then makes the cloud generation lose **every**
tiebreak deterministically, and the next sync overwrites a freshly-paid cloud body with an older local
one — exactly the failure H2 identified, with the fix in place.

**Change.** Either promote the document facts to real columns with `not null`, or add a check
constraint that is the schema fact: `check ((kind = 'summary') = (card is not null))` plus
`check (kind <> 'summary' or (card ? 'mdGeneratedAt' and card ? 'mdCorrectionsHash' and card ?
'docVersion' and card ? 'processedAt' and card ? 'tldr' and card ? 'takeaways'))`. A rule that the
schema does not carry is the convention H2 rejected.

### N-H4 — "The loser re-reads and republishes" turns CAS into last-writer-wins with no ordering rule

**Defect.** M4's fix (§5.1.1:487-496) says *"An idempotent re-read-and-republish of the **same**
generation is the right shape."* Re-reading the manifest and republishing your own generation against
whatever key you now observe **always succeeds** — the CAS was the only thing that could refuse it. So
the protocol degrades to last-writer-wins, and the design has no rule for which generation *should*
win.

**Failure scenario.** Worker publishes *def*; sync's Class-A transfer publishes *abc* and loses; sync
re-reads and republishes *abc*, which now wins; the worker's own retry path re-reads and republishes
*def*. Each flip changes which card is authoritative, changes which body is served, and starts a
90-day retention clock on the generation that just lost (§8:892-900). Nothing bounds the number of
flips, and §9's row 1 and row 3 both rest on this mechanism (§9:1002, §9:1004, §9.1:1043-1047).

**Evidence.** Spec §5.1.1:487-496; §9:1000-1005; §9.1:1043-1047. Today's analogue does have an
ordering rule — `lib/cloud-sync/reconcile-class-a.ts:49` tiebreaks on `mdGeneratedAt` — and it is not
carried into the publish protocol.

**Change.** Give publication a total order and put it in the RPC predicate, not in the retry loop:
publish succeeds only if the incoming generation is newer than the resident one by a stated key
(`created_at`, or the card's `mdGeneratedAt`). Then "the loser retries" becomes "the loser retries and
correctly loses again", which terminates. Also state the retry bound.

### N-H5 — H1 *moved* the honest-read obligation to the manifest; the blob read is still on the spend path and is still dishonest

**Defect.** §5.1:453-468 says *"the authority moves to the manifest, so the same hazard moves with
it"*, and specifies `SlotRead`. It never says the existing blob-level `tryGet` guard stays. It does
have to stay: a manifest row proves a key was *published*, not that the bytes are *readable*.

**Failure scenario.** `SlotRead` returns `{ok:true, key, generationId}`. The reader downloads the key
and Storage 5xxs. `SupabaseBlobStore.get` returns `null` for a 5xx exactly as for a 404
(`supabase-blob-store.ts:27-37`), the reader concludes the artifact is missing, and the serve path
reserves and regenerates a model that is sitting in the bucket — the measured 6¢→12¢ defect, reached
through the manifest instead of around it.

**Evidence.** `lib/html-doc/serve-doc.ts:59-71` (the guard and its comment citing the measurement);
`lib/storage/blob-store.ts:46-56`; `lib/storage/supabase/supabase-blob-store.ts:27-37`;
spec §5.1:453-468.

**Change.** State that **both** reads are on the spend path and both must be honest: only
`SlotRead.absent` **and** `BlobRead.absent` together may lead to a spend; either `unreadable` yields
`busy`. Add it to the assertion §5.1:468 already promises to write, so the test covers the composed
path rather than the manifest alone.

### N-H6 — The workspace migration has no backfill, so it cannot apply to any existing database

**Defect.** §5.0:349-355 does `alter table playlists add column workspace_id uuid not null references
workspaces(id)`, and provisions workspaces **only** inside `handle_new_user()`, which fires on
`insert on auth.users` (`0003_provisioning.sql:9-10`). Existing users have no workspace and existing
playlists have no value for a `not null` column. The `alter table` fails on any non-empty `playlists`.

**Failure scenario.** The migration aborts in CI/staging/production against real data. Nothing in
§5.0, §10 or §15 mentions backfilling existing users or playlists, and §5.0:387-389's "explicitly
deferred" list does not cover it.

**Evidence.** `supabase/migrations/0003_provisioning.sql:2-11`; spec §5.0:348-359.

**Change.** Specify the three-step migration: `insert into workspaces (owner_id) select id from
profiles;` → add the column nullable and backfill from `playlists.owner_id` → `set not null`. Also say
what happens for a user whose `profiles` row exists but whose `auth.users` row predates the trigger,
and confirm the anon path: `handle_new_user` **does** fire for anonymous sign-ins
(`0003:5`, `coalesce(new.is_anonymous, false)`), so anonymous users are covered — that part is correct
and should be stated rather than left to be re-derived.

### N-H7 — The H5 fix silently closes Q6, the "single largest risk", in a footnote — while §14 still lists it open and §12's replacement guard is still unwritten

**Defect.** §11.0:1149-1152 states as a **Rule** that both playlist-keyed arbiters *"re-key to
`(workspace_id, video_id)`"* — including `jobs_idem_active`. §5.0:391-393 says *"Cross-playlist dedup
is **NOT** deferred."* But §14 Q6:1359-1361 still lists cross-playlist dedup as **open** ("the spec is
coherent either way"), and §12:1294-1306 calls re-keying job identity *"the single largest risk in the
work"*, requiring (a) the 1D spend-reservation FK re-pointed and (b) an equivalent of the composite
`(playlist_id, owner_id) → playlists(id, owner_id)` cross-tenant injection guard. Neither is written.
Claude M6 raised exactly this in round 1 and it is unaddressed.

**Failure scenario.** An implementer reading §11.0 drops `playlist_id` from `jobs_idem_active` and the
FK `jobs(playlist_id, owner_id) → playlists(id, owner_id)` (`0009:5-6`, which exists only because
`playlists` carries `unique (id, owner_id)`, `0001:18`) has no replacement — because there is no
`(workspace_id, owner_id)` unique target to point at. The guard that stops a caller enqueueing paid
work against another tenant's identity is removed by a rule stated in a review-response box.

**Evidence.** Spec §5.0:391-393, §11.0:1149-1152, §12:1294-1306, §14:1359-1361;
`0009_job_playlist_identity_and_worker_persistence.sql:5-6, 11-13`; `0001_core_schema.sql:18`.
`CONTEXT.md:8` still states the opposite as domain law: *"The **playlist** coordinate is load-bearing …
each playlist stores its **own** copy of that video's summary."*

**Change.** Either mark Q6 closed and write the replacement guard as SQL in §12, or restrict §11.0's
rule to `serve_model_charge.doc_key` and say job dedup is unchanged in this slice. The current text
decides it in one place and leaves it open in two others.

### N-H8 — Re-keying `serve_model_charge` leaves its *authorization* per-playlist, and that authorization reads a promotion record the manifest supersedes

**Defect.** `reserve_serve_model` does two playlist-keyed things, and §11.0's fix re-keys only one.
The charge key becomes `(workspace, video)`; the **gate** stays
`select (v.data->'artifacts'->'summaryMd'->>'status') = 'promoted' from videos v join playlists p …
where v.playlist_id = p_playlist_id and p.owner_id = v_owner` (`0020:196-206`). That is a *third*
record of "which copy is authoritative", per playlist, in jsonb — and the spec never mentions
`artifacts.summaryMd.status` at all.

**Failure scenario, both directions.** If the manifest becomes the source of truth and
`artifacts.summaryMd` stops being written, `v_promoted` is never `true` and `reserve_serve_model`
returns `'denied'` for every video — the magazine model can never be generated, on a path whose only
other outcome is a 503. If it keeps being written, there are two records of authority for the same
question, per playlist, and a video promoted in P1 but not P2 gets a different answer for the same
shared blob — while the charge, now workspace-keyed, is shared between them.

**Evidence.** `supabase/migrations/0020_reservation_release.sql:196-206` (gate), `:213` (doc_key),
`:250-256` (token mint, "single live attempt"); `0021:116-133` (the `artifacts.summaryMd` key-scoped
monotonic status that `persist_summary` maintains); spec §11.0:1135-1152, §5.2:660-684.

**Change.** §11.0's rule must say what `artifacts.summaryMd.{key,status}` becomes under the manifest —
retired, mirrored, or authoritative — and re-key `reserve_serve_model`'s **gate**, not only its
`doc_key`. Add the deploy note: on cutover day, rows keyed `<playlist>/<video>` and `<workspace>/<video>`
coexist, so each owner gets one extra set of K attempts that day. Bounded, but it is a real
loosening of the G1 cap and should be recorded rather than discovered.

### N-H9 — Dropping `sectionId` from the asset key breaks the pruner, and the vanished playlist segment lets one playlist prune another's assets

**Defect.** §8:951-953 re-keys assets to the timestamp window alone. The code that actually deletes
assets identifies them **by the `sectionId` prefix** — `pruneSectionAssets(dir, sectionId, written)`
walks `fs.readdirSync` and unlinks every `${sectionId}-*.jpg` not written by the current run
(`lib/dig/slides.ts:207-209, 219-231`). With `sectionId` gone from the name, that function cannot
identify a section's assets at all. The fix changes the key and says nothing about the destroyer,
which is still §14 Q7's open second seam-bypassing writer.

**Failure scenario.** Two ways to get it wrong and the spec forecloses neither. (a) The pruner is
rewritten to prune by *window* — then a re-dig of section 120 in generation *def* deletes the assets of
*abc*'s dig that §6 explicitly permits to stay attached, which is the H6 defect unchanged. (b) The
pruner is dropped — then stale assets accumulate with no manifest row, and N-B1's sweeper deletes them
at day 90. Separately: assets today are isolated by the playlist path segment
(`objectKey` = `${p.id}/${p.indexKey}/assets/…`, `supabase-blob-store.ts:17`). §4 removes that segment,
so under one workspace **a re-dig of V in playlist P2 prunes V's assets written under P1** — a
cross-playlist deletion of source-of-truth bytes that cannot happen today.

**Evidence.** `lib/dig/slides.ts:171` (`assetName = ${sectionId}-${token.sec}-${endComponent}.jpg`),
`:185-186`, `:207-209`, `:219-231`; `lib/storage/supabase/supabase-blob-store.ts:17`;
spec §4:185, §8:942-953, §14:1362-1364.

**Change.** Specify the pruning rule together with the key change — the two are one decision. State the
attach-aware rule ("never delete an asset referenced by an attached dig of any generation"), and note
that this makes assets *referenced* state, which is another reason they need a root of their own
(N-B1). Also update §4:185, which still shows `assets/<sectionId>-<start>-<end>.jpg`.

---

## MEDIUM

**M-R2-1 — §4's canonical address template still contradicts §8's asset rule.** §4:185 is
`<workspaceId>/videos/<videoId>/assets/<sectionId>-<start>-<end>.jpg`; §8:951-953 rules `sectionId`
out. §4 is the template an implementer copies. Fix §4.

**M-R2-2 — `CONTEXT.md` now contradicts itself about whether artifacts are per-playlist.** `:8`
(*Work target*) states as domain law that *"each playlist stores its **own** copy of that video's
summary (artifacts are addressed per playlist — `owner/playlist/…`)"* and that omitting the playlist
coordinate means *"only one playlist would ever receive its artifact"*. `:60` (*Artifact manifest*),
added by the same terminology pass, says *"Keyed by workspace and video, **never** by playlist — which
is why playlists in one workspace share artifacts."* The grill pass added new terms without
re-deriving the entries they invalidate — the same failure mode §9.1:1055-1058 diagnoses for the spec.

**M-R2-3 — ADR-0006 still leads with `<tenantId>` and re-asserts a claim the spec has withdrawn.**
`:7` still writes the address as `<tenantId>/videos/…`; `:30` still says the conditional write is
*"trivially sufficient"*, which §5.1.1:510-516 explicitly retracts on the evidence of five review
rounds; `:68-72` says a workspace joining an existing team *"still move[s] every object"*, which
§11.1:1168-1173 withdrew as *"itself wrong"* on 2026-08-06. Codex L1 asked for the ADR to be updated;
a superseded box was added at `:54-82` and the surrounding text was not reconciled. An implementer who
reads the ADR instead of the 1466-line spec gets three retracted positions.

**M-R2-4 — `p_expected_key`'s NULL semantics are unspecified and race.** §5.1:445 says NULL means
"expect no row". In SQL `where blob_key = NULL` matches nothing, so the first publish of a slot can
never succeed as an update; and two concurrent first-publishers both see no row. Specify
`insert … on conflict (workspace_id, video_id, slot) do nothing` with a row-count check, and
`is not distinct from` if the update form is kept.

**M-R2-5 — Detached digs are pinned forever with no surface and no bound.** §6.2:779-782 gives a
detached dig a manifest row precisely so the sweeper can never collect it; §6.2:801-805 leaves
presentation to "a later slice". The result is paid content that is permanently retained, permanently
invisible, and permanently un-collectable — and §8:984-991 forecloses re-opening accumulation as an
objection. At minimum state the expected growth and that a detached row is *deliberately* exempt from
the 90-day ceiling, so the exemption is a decision rather than an emergent property.

**M-R2-6 — The unreference RPC's lock is named, not specified; the ingest side takes no lock.** See
A6 above. `delete … where not exists (surviving videos row)` under READ COMMITTED does not exclude a
concurrent `insert into videos`. Name the lock (a `select … for update` on `workspaces`/`playlists`)
and say that **the ingest path must take it too** — a lock only one side takes is not a lock.

---

## LOW

**L-R2-1 — `video_generations`' DDL block is not valid SQL** (§5.2:630-639: no `create table`, no
commas, no types-with-constraints punctuation), while `video_artifacts`' block is. It reads as a
sketch beside a schema, which invites the impression that only one of them is decided.

**L-R2-2 — §14 Q1 (`generationId` form) is still open but is now load-bearing for §8.** §4.1:258-260
recommends content-hash ids for free re-renders; §8:971-977's footprint argument depends on that
choice, and the `pdf:*` slot's interaction with the `kind` check (N-H1) depends on it too. Q1 should be
promoted to a prerequisite or closed.

**L-R2-3 — §13 says the workspace table is in scope but not the migration that fills it.** §13:1312
enumerates what is deferred (multiple workspaces, members, ACLs, the atomic-creation RPC, role checks)
and does not mention the backfill (N-H6) or the storage-policy cutover (N-B4), which are the two pieces
of §5.0 that actually touch production data.

---

## Round-1 findings NOT genuinely fixed

Ordered by severity of what survives.

1. **Coordinator B1 — a shared video is two rows, so it has two cards for one body. NEVER ADDRESSED.**
   Not in the prompt's list of 14, and nothing in the spec mentions it. `videos` PK is
   `(playlist_id, video_id)` (`0001:30`); §5.2.1:537-540 places the video judgments there and
   §5.2.2 places corrections there implicitly; §11.0 makes both playlists share one body. N-B2 shows
   this now blocks the corrections CAS outright. **Still Blocking.**
2. **Coordinator B2 — the manifest key names an entity that does not exist. PARTIALLY ADDRESSED.**
   §5.0 supplies `workspaces` and `playlists.workspace_id`, which closes the *first segment has no
   source* half. It does **not** supply a workspace-scoped video record, so `video_artifacts` and
   `video_generations` still carry no FK to anything representing "video V in workspace W", and
   referential integrity between the manifest and the rows it describes remains
   application-maintained. **Still Blocking**, and it is the natural home for the fix to B1.
3. **Codex B1 — reworded, defect survives.** `kind` + FK + check are the right idea; the FK cannot be
   created and the check is wrong for four of six slot shapes (N-H1).
4. **Codex H3 (asset deletion undesigned) — moved, not removed.** Round 1: assets survive an explicit
   delete forever. Now: assets are deleted at day 90 by the new second root set (N-B1). The direction
   reversed; the design gap did not close.
5. **Claude M6 (cross-tenant injection guard) — unaddressed.** §12:1302-1303 still says "any re-keying
   must preserve an equivalent guard" without saying what it is, while §11.0 now mandates the re-keying
   (N-H7).
6. **Claude M9 (§10 overstates `reconcileCloudBase`) — unaddressed.** §10:1062-1074 is unchanged and
   still calls it *"**precisely** the machinery this needs"*. N-B4 makes this load-bearing: the
   predicate cutover is only safe if the corpus migration is a real, resumable tool.
7. **Codex M2 (GC has no audit invariant) — unaddressed.** §8 still assigns correctness to a scheduled
   best-effort sweep with no work table, no attempt/last_error record, and no "delete requested but
   bytes remain" assertion. §8:933's *"Assert the collection, do not assume it"* remains a slogan.
8. **Claude M5 (paid/free from the key alone, for keys §4 does not define) — unaddressed.** §4 still
   defines four key shapes out of nine; §8:957-961 still makes classification-from-key a money-safety
   rule. N-B1 is what happens when an undefined shape meets the rule.

Genuinely fixed and I could not break them: B3 (the three-predicate contradiction — §2:77, §4:192-200,
§5.0:369-378 and §11.2 now agree, and the text-not-cast property is correctly preserved); H7 (the
generation lifecycle); §6.1's both-directions ratio and the degenerate-span rule; M3's move to a
definer-RPC writer with `select`-only client RLS (the *pattern* is right — only the signature is
wrong); M7 (§9's withdrawn row); L1 (`0007:12-15` is now cited correctly — I re-read it).

---

## Verdict

**NOT CONVERGED.** 4 new Blocking and 8 new High, plus two round-1 Blocking findings never addressed.

The gate is not close. The productive next move is **not** another round of independent fixes — that is
what produced these interactions. Fix in this order, re-deriving each against the previous:

1. Coordinator B2 (the workspace-scoped video record) — B1, N-B2 and the referential-integrity gap all
   collapse into it.
2. The `video_artifacts` DDL as a whole: kind domain, unique target for the FK, the slot→kind map, and
   where assets live (N-B1, N-H1).
3. `publish_slot` last, once it knows every column and every CAS it must carry (N-B3, N-H4, M-R2-4).
4. The cutover (N-B4, N-H6) and the arbiter re-keying (N-H7, N-H8) as one deploy story.
