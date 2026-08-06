# Adversarial review — Stable Blob Addressing design spec, ROUND 4 (Claude)

**Artifact:** `docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md` @ `51bb71b`
(branch `docs/blob-addressing-decisions`), plus `CONTEXT.md`, `docs/adr/0006-stable-blob-addressing.md`,
`docs/reviews/spec-blob-addressing-rules-inventory.md`.
**Prior rounds read:** r1/r2/r3 × {claude, codex, coordinator}, and the rules inventory.

**Method.** Every DDL block the spec now contains was **executed** against the live local Postgres 17
stack (`supabase_db_…`, 5312 profiles / 4368 playlists / 2902 videos / 101 jobs / 1485 storage objects)
— populated-table migrations inside `begin … rollback` against the **real** schema, new-table DDL in a
scratch schema `r4`, dropped afterwards. The live schema was verified unmodified at the end
(`playlists.workspace_id` absent, `videos` still 2902 rows, both original storage policies present).
Where a finding says **MEASURED**, the quoted text is real psql output.

**Verdict: NOT CONVERGED.** 6 Blocking, 8 High, 6 Medium, 2 Low.

**Slide assets:** treated as withdrawn per the mandate. Nothing below concerns cloud asset keys, asset
GC or asset retention.

**What I could NOT break — recorded first, because it is most of round 3's work and it holds.**
Executed and confirmed genuine: **B-2** (`generation_id` nullable; one positive insert succeeded for
each of `summary`, `model`, `dig:120`, `digDeeper`, `pdf:summary`, and the §6.2 detached form
`dig:120@g3`); **B-5** (the fail-closed slot check now *rejects* `slot='html'` under both `kind='dig'`
and `kind='render'`); **B-6** (`workspaces unique (id, owner_id)` present, and §14 Q6's
`jobs (workspace_id, owner_id) → workspaces (id, owner_id)` FK creates); **B-7 for `jobs`** (add
nullable → backfill via `playlist_id` → `set not null`: `UPDATE 101`, 0 remaining NULLs, `ALTER TABLE`
succeeded); and **§5.0's whole predicate replacement**, which is the strongest thing in the document —
`workspace_readable` created, the storage policy swapped, and a session client with a real `sub` claim
saw **exactly the same 14 objects** the old `split_part(name,'/',1) = auth.uid()::text` predicate
showed, while `anon`, `'_staging'`, `''` and `'not-a-uuid'` all returned `f` **without raising**.
Physical rules 1, 2 and 5 are satisfied at that site, measured, not argued.

---

# JOB 1 — the physical-rule sweep across every site

I took each of the 8 physical rules and enumerated every place in the spec where its shape occurs.
**Four sites fail, and three of the four are a rule that was fixed at a sibling site in an earlier
round.** The sweep table is at the end of this section.

## BLOCKING

### J1-1 — MEASURED. Rules 3 **and** 8 both recur at `video_generations`: §5.1's `video_artifacts` still does not create. Fourth consecutive round.

**Defect.** Round 3's B-1 (`kind` must be the enum) and round 2's C2 (a composite FK needs a unique
constraint on the exact tuple) were both fixed **in §5.1's prose only**. §5.1:660-664 says *"Add
`unique (workspace_id, video_id, generation_id, kind)` to `video_generations`"* and *"`video_generations.kind`
also widens … to the same enum."* The DDL an implementer copies is **§5.2:1070-1078**, and it still
declares `kind text not null` with `primary key (workspace_id, video_id, generation_id)` and no unique
constraint at all.

**MEASURED — §5.1's `video_artifacts` DDL verbatim against §5.2's `video_generations` as written:**

```
ERROR:  there is no unique constraint matching given keys for referenced table "video_generations"
```

**MEASURED — with the unique constraint added but `kind` left as `text` (rule 8 in isolation):**

```
ERROR:  foreign key constraint "va_x_workspace_id_video_id_generation_id_kind_fkey"
        cannot be implemented
DETAIL:  Key columns "kind" and "kind" are of incompatible types: artifact_kind and text.
```

Applying **both** prose fixes (`alter … type artifact_kind`, `add unique (…, kind)`) makes
`video_artifacts` create on the first try. So the fixes are right and are simply not in the DDL.

**Evidence.** Spec §5.1:613-614 (the FK), §5.1:660-664 (the prose fix), §5.2:1070-1078 (the DDL).

**Change.** Rewrite §5.2's block as executable DDL carrying `kind artifact_kind not null` and
`unique (workspace_id, video_id, generation_id, kind)`. **The prose fix must be deleted once applied** —
leaving it is what made three reviewers read the constraint as present.

### J1-2 — MEASURED. Rule 6 recurs at the card-completeness check: it **fails open on `card = NULL`**, which is the exact value round-1 H2 was about.

**Defect.** §5.2:1126-1128 enforces card completeness with
`check (kind <> 'summary' or card ?& array['tldr','takeaways','docVersion','mdGeneratedAt','processedAt','mdCorrectionsHash'])`.
When `card` is NULL, `card ?& array[…]` is NULL, the whole disjunction is NULL, and **a CHECK is
satisfied by NULL**. This is B-5's shape (`slot_kind` returning NULL) at the sibling site, one section
away, and it was not swept.

**MEASURED:**

```
insert into vg_check values ('…0001','V','g1','summary', NULL);
INSERT 0 1
--- did a SUMMARY generation with a NULL card get in? ---
 generation_id |  kind   | card
---------------+---------+------
 g1            | summary |
(1 row)

insert into vg_check values ('…0001','V','g2','summary', '{"tldr":1}'::jsonb);
ERROR:  new row for relation "vg_check" violates check constraint "vg_check_check"
```

Note what that pair means: the guard **works for an incomplete card and fails for an absent one**, so
it looks correct in any test that supplies a card. H2's finding was specifically about the absent case
— *"under an immutable generation record it becomes a silent NULL, which is worse … `reconcile-class-a.ts:49`
tiebreaks on `(a ?? '') > (b ?? '')`, so a NULL cloud `mdGeneratedAt` **loses to local every time,
deterministically**"* (§5.2:1110-1114). The constraint written to make that impossible admits it.

**It compounds with the ranking.** §5.1.1:838 ranks on `doc_version_major desc`, and in Postgres
`desc` is **NULLS FIRST**:

```
 generation_id | doc_version_major
---------------+-------------------
 g_null        |
 g_good        |                 4
```

So a card-NULL summary generation is not merely insertable — it **outranks every properly-versioned
generation** and becomes `current`, silently downgrading the video. That is A-4's failure scenario
arriving through A-4's own fix.

**Change.** `check (kind <> 'summary' or (card is not null and card ?& array[…]))`, and specify
`nulls last` on every `desc` rung of the ordering. Mutation-test both: insert a NULL card and require
rejection; rank a NULL rung and require it to lose.

### J1-3 — MEASURED. Rule 4 recurs at `videos`: still a bare `add column … not null` on a populated table. Round 3 named this site and the fix went to a different one.

**Defect.** §5.0.1:504 reads, verbatim:
`alter table videos add column workspace_id uuid not null references workspaces(id);`

**MEASURED** (after the §5.0 three-phase `playlists` migration succeeded, so this is the *only* failure
in the sequence):

```
--- playlists OK. Now §5.0.1 videos ALTER, VERBATIM (spec line 504) ---
ERROR:  column "workspace_id" of relation "videos" contains null values
```

**Why it survived round 3.** B-7 named `videos` explicitly (*"§5.0.1:468 adds the column to `videos` —
also as a bare `alter table videos add column workspace_id uuid not null …`"*). The round-3 fix note
(§14 Q6:1897-1907) records the recurrence as *"`workspace_videos` **and** `jobs`"* and gives the
three-phase shape for `jobs` only. `workspace_videos` is a **new** table and never had the problem.
The rules inventory repeats the mis-attribution at `:213`. So the round that wrote *"a physical rule
applies to every SITE"* mis-identified one of the two sites it was writing about, and the real one is
untouched.

**Change.** Three-phase for `videos` too (`add nullable → update videos v set workspace_id = v.owner_id
→ set not null`, verified working in T3), and correct the inventory's `:213` entry to name `videos`.

### J1-4 — MEASURED. Rule 3's other form: §5.0.1's composite FK on `videos` cannot be added, because `workspace_videos` is never populated.

**Defect.** §5.0.1:505-506 adds
`alter table videos add foreign key (workspace_id, video_id) references workspace_videos (workspace_id, video_id);`
with no step that inserts the referenced rows. §5.0.1 contains no migration phases at all.

**MEASURED** (with `videos.workspace_id` given the three-phase treatment J1-3 asks for, so this is the
next failure and not a cascade of it):

```
ERROR:  insert or update on table "videos" violates foreign key constraint
        "videos_workspace_id_video_id_fkey"
DETAIL:  Key (workspace_id, video_id)=(6133e2e0-…, fefdf88e-…) is not present in table
         "workspace_videos".
```

This is **Codex round-3 JOB B BLOCKING verbatim** (*"missing the populated-table backfill before adding
the FK from existing `videos`"*). It received no fix.

**Change.** Between the two statements:
`insert into workspace_videos (workspace_id, video_id) select distinct workspace_id, video_id from videos;`
State it as a phase, in §5.0.1, beside the DDL — not as prose elsewhere.

## HIGH

### J1-5 — Rules 1 + 17: §4 still defines **three** key shapes for **nine** blob kinds, so the sweeper's classifier cannot be written. Third round, three reviewers.

§4:182-184 gives `summary.md`, `model.json`, `dig/<sectionId>.md`. §3:146-161 lists nine kinds. HTML,
cloud PDF, local PDF, the dig-deeper companion and `_staging/<uuid>/…` have **no shape under the new
template**. Rule 17 ("paid/free derivable from the key alone") is the sweeper's only classifier for an
orphan — an orphan has no row by definition — so for five of nine kinds the money-safety decision is
unspecified. Raised as coordinator A3, my A-11, and Codex HIGH[17] in round 3; unchanged.

It is now sharper than it was, because of J2-2: the fail-closed slot check **rejects `html` entirely**
(measured, both kinds), so HTML bytes cannot hold a manifest row at all and are permanently in the
sweeper's no-row root set.

**Change.** Extend §4's template to all nine kinds and specify a total `classify_blob_key()` that
**fails closed** (unknown shape ⇒ never a sweep candidate, and alert).

## The sweep table

| # | Rule | Sites in the spec | Status |
|---|---|---|---|
| 1 | RLS sees only `name` | storage policy §5.0 | **OK** (measured T10) |
| 2 | A raising policy fails the whole query | `workspace_readable` §5.0; `workspace_member` §11.2 | **OK** — column cast, not segment (measured: `''`, `'_staging'`, `'not-a-uuid'` all `f`, no error) |
| 3 | FK needs a unique on the exact tuple | `video_artifacts→video_generations`; `jobs→workspaces`; `videos→workspace_videos`; `workspace_videos→workspaces`; `video_artifacts→workspaces` | **J1-1 fails**; **J1-4 fails** (target rows absent); others OK |
| 4 | `add column … not null` on a populated table | `playlists`; **`videos`**; `jobs` | **J1-3 fails** (`videos`); `playlists`/`jobs` OK (measured) |
| 5 | `security definer` + `search_path=''` | `handle_new_user`; `workspace_readable`; `record_artifact`; `detach_artifact`; the unreference RPC | `handle_new_user` fixed; `workspace_readable` OK; **the three new RPCs declare no `search_path`** (M-R4-3) |
| 6 | `= NULL` never matches; a CHECK passes on NULL | slot check §5.1; **card check §5.2**; `generation_id` check §5.1; the `desc` ranking §5.1.1 | slot check fixed (measured); **J1-2 fails** at the card check **and** at the ranking |
| 7 | Supabase `get` cannot prove absence | `SlotRead` §5.1; attach path §6.2; sweeper `list` §8; **record-time verification §5.1.1** | first three OK; **J3-4 open** (verification runs as `service_role`) |
| 8 | enum ≠ text | `video_artifacts.kind`; **`video_generations.kind`**; `slot_kind` return; `artifact_record_result` | **J1-1 fails** at `video_generations`; `artifact_record_result` is never defined (M-R4-4) |

---

# JOB 2 — attacking the twelve chosen invariants

## BLOCKING

### J2-1 — MEASURED. `primary key (workspace_id, video_id, slot)` admits **one** row per slot, while rule 13 ranks **many** and A-1's record-first order must insert one **before** the bytes. All three ways out fail. **Sixth instance of shape #9.**

**Invariants attacked:** 13 (`current` is derived), 14 (the `state='recorded'` floor), 19 (determinacy).

**Defect.** §5.1:612 declares `primary key (workspace_id, video_id, slot)`. §5.1.1:838 defines
*"`current` = the highest-ranked **RECORDED** generation for that slot"* — a ranking over a set that
the primary key permits to have at most one member. Round 3's A-1 then adds the record-first order:
*"`record_artifact` inserts the row in state `pending` **BEFORE** the bytes are written."* A regeneration
must therefore write a second row for a slot that already has one.

**MEASURED — all three resolutions, against a live `summary` slot in state `recorded`:**

```
--- record-first: insert the g9 summary row in state pending, BEFORE its bytes ---
ERROR:  duplicate key value violates unique constraint "video_artifacts_pkey"
DETAIL:  Key (workspace_id, video_id, slot)=(…0001, V, summary) already exists.

--- and the on-conflict form the RPC implies (it returns 'duplicate') ---
INSERT 0 0
  slot   |  state   | generation_id | blob_key
---------+----------+---------------+----------
 summary | recorded | g1            | k

--- the only other option: UPDATE the row to pending ---
  slot   |  state  | generation_id | blob_key | servable_per_a2_floor
---------+---------+---------------+----------+-----------------------
 summary | pending | g9            | k9       | f
```

Read the three outcomes in order:

1. **Insert** — the PK rejects it. Record-first is unimplementable as specified.
2. **Insert … on conflict do nothing** — which is what `record_artifact`'s `'duplicate'` return value
   implies, and what §5.1's own trap box prescribes (*"Any insert-if-absent must be `insert … on
   conflict do nothing` with a row-count check"*, :709-712). The second generation is **never
   recorded**. A regeneration can therefore never become current, ever: rule 13's ranking has a
   permanent single candidate, and `docVersion` bumps, corrections re-applications and drift repairs
   all silently do nothing after paying Gemini.
3. **Update the live row to `pending`** — the row leaves `recorded`, and per A-2's floor
   (*"eligible to be SERVED — `state = 'recorded'`. That is the whole test"*, §5.1.1:868-870) the
   summary **is not servable for the duration of the Gemini call**. `servable_per_a2_floor` = `f`,
   measured. That is precisely A-2's failure — an eligibility predicate emptying a non-empty set,
   visible content disappearing on a routine action — reintroduced by the fix for A-1, in the same
   round, one screen apart.

**This is the sixth instance of "a fix that moved a defect rather than removing it,"** and it is the
first where the two fixes were written in the *same batch* after a cross-derivation pass. The pass
checks rules against rules; both rules are individually fine. The contradiction is between a rule
(13/A-1) and a **schema decision** (the PK) that no rule states.

**Change.** The artifact manifest must be **per generation**, not per slot:
`primary key (workspace_id, video_id, slot, generation_id)` — with a partial unique index if you want
at most one non-terminal `pending` per slot — and `current` then genuinely ranks a set. Say explicitly
what a `pending` row does to serving (it must not participate; the previous `recorded` row keeps
serving until the new one flips). Then re-derive: §8's sweeper root sets, §6.2's `detached` slot
naming (`dig:120@g3` becomes unnecessary — the generation is a key column), and `detach_artifact`'s
PK-change problem (M-R3-1) all change shape, most of them for the better.

### J2-2 — Rule 19's determinacy premise, *"bytes ⊆ records"*, is **false for the entire existing corpus** for the whole duration of §10's now-incremental migration — and permanently false for `html` and `_staging`.

**Invariant attacked:** 19, as restated in round 3.

**Defect.** A-1's resolution is that record-first makes *bytes ⊆ records* hold **by construction**, so
*"'No record' now **entails** 'no bytes', determinately, with no probe needed — so the vacuous branch
stops existing"* (§5.1.1:756-758). The entailment holds only for blobs written **after** the manifest
exists and **through** `record_artifact`. Three populations violate it:

1. **The whole existing corpus.** §5.0.2's biggest win is that *"§10 stops being a cutover … the corpus
   migration becomes **incremental, interruptible and reversible**"* (:579-581). While it runs, every
   un-migrated video has paid bytes at `<uid>/<playlistKey>/<base>.md` and **no manifest row**. Rule 19
   reads "no record" as a determinate negative and permits the spend. The measured cost of exactly this
   shape is 6¢→12¢ (`serve-model-unreadable.test.ts`), and it applies to every un-migrated video that
   anyone opens — which is the entire corpus on day one of an *incremental* migration whose whole
   selling point is that it may take as long as it likes.
2. **HTML.** MEASURED: the fail-closed slot check now rejects `slot='html'` under both `kind='dig'` and
   `kind='render'`, and §2's slot vocabulary has no `html` slot. `htmls/<base>.html` bytes therefore
   **cannot** hold a record, so "no record" does not entail "no bytes" for that kind. §8 nonetheless
   reasons about HTML retention as *"free blobs live exactly as long as they are the authoritative copy
   of their slot"* — of a slot that cannot exist.
3. **`_staging/<uuid>/<finalKey>`.** Unreferenced by construction; that is its purpose.

**Why this is the invariant and not a migration detail.** Round 3 chose determinacy over absence
precisely so the rule would be checkable. The check is `select` on the manifest — and its answer is only
meaningful where the manifest is complete. **Completeness is now a load-bearing precondition of the
money guard, and nothing in the spec states it, tests it, or gates spending on it.**

**Change.** State the precondition as a rule: *rule 19's "no record ⇒ no bytes" holds only for
(workspace, video) pairs marked migration-complete.* Add a per-video migration-state flag, make the
spend path treat "not yet migrated" as **indeterminate ⇒ `busy`** (never as absent), and keep the
legacy `MODEL_KEY(base)` probe alive for exactly those pairs. Then either give `html` a slot or state
in §8 that HTML is never in the manifest and is collected as a no-row orphan — which is what the
fail-closed check has already decided by accident.

## HIGH

### J2-3 — Rule 13's top rung, `corrections_current`, is **not a replica-independent recorded fact**, so §5.1.1's convergence claim is false — and the paragraph making it says why in its own next sentence.

**Invariant attacked:** 13's ordering, `(corrections_current desc, doc_version_major desc, created_at desc, generation_id desc)`.

§5.1.1:849-853 claims: *"With every rung a replica-independent recorded fact, `current` is a
deterministic function of the generation *set* — so two replicas that exchange sets compute the same
answer, and sync needs no tiebreak negotiation at all."* Rung by rung:

- **`corrections_current`** is not a recorded fact and not a column. It is a **comparison** —
  §5.2.2:1047-1049, *"a generation whose `mdCorrectionsHash` does not match **the video's current
  corrections**"*. Corrections are mutable, per-replica, and free to edit offline
  (`update_video_annotations`, `0021:19-53`). Replica A holding C2 and replica B still holding C1
  classify the **same** generation differently. The top rung is a function of local mutable state, not
  of the set. Convergence fails at rung 1.
- **`doc_version_major`** is not a column either (J3-2), and where it would be derived from
  `card->>'docVersion'` it is NULL for every dig generation and for any card-NULL summary generation —
  which `desc` ranks **first** (J1-2, measured).
- **`created_at`** is retained as rung 3 while the same fix says *"`created_at` is also not comparable
  across replicas — a machine with a fast clock wins permanently"* (§5.1.1:846-847). Within one
  `(corrections, major)` class — the common case, since most regenerations are same-format — the clock
  still decides. So the rung the paragraph disqualifies is the one that actually adjudicates.
- **`generation_id`** is replica-independent and arbitrary. It is the only rung that is what the claim
  needs, and it is the last resort.

**Change.** Either drop the convergence claim (and say §5.3 owes a tiebreak protocol), or make the top
rung a recorded fact: store `mdCorrectionsHash` on the generation (which §5.2.1 already does) and rank
on **hash equality against a corrections value that is itself synced and versioned**, not against
"current". State `nulls last` throughout. This is Codex round-3 BLOCKING[13] with a mechanism attached;
it was answered with an assertion rather than a change.

### J2-4 — Rule 14's floor was applied at one site. §5.1.2's `source_generation_id` gate is still a filter with no floor, and it can empty the `model` slot.

**Invariant attacked:** 14 (staleness ranks, never gates).

A-2's fix is explicit and correct: *"eligible to be SERVED — `state = 'recorded'`. That is the whole
test, and it cannot empty a non-empty set."* But §5.1.2:797-799 still says *"a model whose
`source_generation_id` is no longer the current summary generation is **ineligible to be current**"*,
and §5.1.1:884-887's eligibility list still carries *"`source_generation_id` (if any) is still
current"* as a member alongside the corrections condition A-2 demoted.

**Failure scenario.** A summary is regenerated (new `current` summary generation). The existing paid
magazine model's `source_generation_id` now points at the previous generation, so it is ineligible. The
`model` slot resolves to **nothing** — not "stale, showing a banner", nothing — and the magazine view
is empty until a **paid** `generateMagazineModel` run. That is A-2's scenario with `model` substituted
for `summary`, and the drift signal it replaces is advisory today (`readTitleStableModel` →
`{status:'ok', stale:true}`, `serve-doc.ts:90-96`), exactly the precedent A-2 cited.

It is also the same one-site-only pattern as J1-3: the round-3 fix moved corrections from filter to
rank and left the sibling condition, three lines away, as a filter.

**Change.** Apply the floor uniformly: `state='recorded'` is the only gate; `source_generation_id`
currency becomes a rung in the ordering and a staleness flag on the response.

### J2-5 — §5.3 is unchanged at three sentences, while §5.1.1 asserts the convergence result §5.3 was declared out of scope to produce.

**Invariants attacked:** 12 and 13 as *cloud-only* invariants.

The round-3 scope box (§5:357-369) is a good answer to A-5/A-7: *"Naming the asymmetry is in scope for
this spec; resolving it is the sync slice's job."* But §5.3 (:1142-1145) is byte-for-byte the same three
sentences as before, still framed as *"compares two artifact manifests and produces one"* — the
pointer-reconciliation framing rule 13 retired — and it does not name the asymmetry the scope box
promises it names. Meanwhile §5.1.1:849-853 **does** make a resolution claim about sync ("needs no
tiebreak negotiation at all"), which J2-3 shows is false. So the spec declares the question deferred in
one section and answers it wrongly in another.

The concrete unhandled case is unchanged: the sync baseline is per `(playlist, video)`
(`lib/cloud-sync/manifest.ts:8-9`) while the artifact manifest is per `(workspace, video)`, so under
one-workspace-per-user dedup one shared body is reconciled **twice per sync run**, once per playlist,
each pass free to reach a different decision.

**Change.** Two sentences in §5.3 discharge the scope box honestly: (a) *local has no generations and
no manifest; sync must translate, not compare*; (b) *the per-playlist baseline and the per-workspace
manifest are different keys, and reconciling one from the other is the sync slice's first problem.*
Then delete the convergence claim from §5.1.1, or move it to §5.3 as an open question.

---

# JOB 3 — are round 3's fixes genuine, and what did they introduce?

Round-3 fixes I executed and judged **genuine**: B-2, B-5, B-6, B-7-for-`jobs`, and §5.0's predicate
replacement (all measured; see the preamble). Below are the ones that are reworded, partial, or absent.

## HIGH

### J3-1 — MEASURED. §5.0's migration block still mints **random** workspace ids, contradicting §5.0.2's `id = owner_id` seeding. Running the spec's two seeding statements in order errors.

**Defect.** B-3's fix landed in §5.0.2 (`insert into workspaces (id, owner_id) select id, id from
profiles;`, :543). §5.0's own three-phase migration block — the one headed *"the migration must be
three-phase"*, which is where a migration author reads the phases — still has step 1 as
`insert into workspaces (owner_id) select id from profiles;` (:401), i.e. `gen_random_uuid()` ids.
That is the **exact defect B-3 identified**, left in place at the site that looks like the migration.

**MEASURED — the two statements the spec contains, in document order:**

```
--- T1b: §5.0 migration step 1 VERBATIM (line 401) ---
INSERT 0 5312
--- T1c: §5.0.2 seeding VERBATIM (line 543) — both are in the spec ---
ERROR:  duplicate key value violates unique constraint "workspaces_owner_id_key"
DETAIL:  Key (owner_id)=(38081599-9ff6-4390-a04f-84b6637f013e) already exists.
```

A migration author who follows §5.0 and never reaches §5.0.2 ships random ids, `workspace_readable(uid)`
matches nothing, and — per §5.0.2's own analysis — `SupabaseBlobStore.get` collapses the denial into
`null`, so **every user reads their own paid content as absent** while the `service_role` worker keeps
writing it. Smoke-test-invisible, asymmetric, exactly as documented at :529-537.

**Change.** Replace §5.0:401 with the §5.0.2 form and add a one-line pointer. This is the prose-vs-DDL
pattern the mandate asked about, with the roles reversed: here two *DDL* blocks disagree, and the one an
implementer reads first is the wrong one.

### J3-2 — Three columns that round-3 fixes are built on exist **only in prose**. `grep` finds each exactly once in the document, and never in DDL.

| Column | Required by | Appearances in the spec |
|---|---|---|
| `source_generation_id` | §5.1.2's rule (*"a derived slot carries `source_generation_id` alongside its own `generation_id`"*), and §5.1.1's eligibility list | **:791 and :797 only** — prose |
| `doc_version_major` | A-4's ordering, rung 2 | **:838 only** — inside the ordering expression |
| `corrections_current` | A-4's ordering, rung 1 | **:838 only** — same |

MEASURED — the columns of `video_artifacts` and `video_generations` as the spec's DDL creates them:

```
video_artifacts:      workspace_id, video_id, slot, kind, state, blob_key,
                      generation_id, start_sec, end_sec, updated_at
video_generations:    workspace_id, video_id, generation_id, kind, card, created_at
```

A-4's change text said the fix *"costs one column on `video_generations`"* and the column was not added.
§5.1.2 is a **round-2 High** whose entire mechanism is a column that does not exist — two rounds now.
Without them, §5.1.1's ordering is not executable and §5.1.2's drift check has nothing to compare, so
the retirement of `sameTitles` (§4.2.1:352) leaves no replacement at all.

**Change.** Add all three to the DDL, with `doc_version_major int` and `mdCorrections_hash` recorded on
`video_generations` (not derived from `card` at read time — a jsonb extraction is not a rung you can
index or reason about across replicas).

### J3-3 — B-11 unaddressed: the card-completeness constraint and the producer that cannot satisfy it still have no stated ordering, and the producer is unchanged in code.

Verified in code today, `lib/job-queue/summary-handler.ts:149-164`: the `Video` it builds carries
`docVersion: CURRENT_DOC_VERSION` and `processedAt` and **no `mdGeneratedAt`, no `mdCorrectionsHash`**.
The spec's response remains the parenthetical at §5.2:1131-1132 (*"And fix `summary-handler.ts` **in this
slice** — it is one of the two producers"*). B-11 asked for the **ordering** statement, and it is not
there: if the constraint lands before the producer fix, every cloud summarize job fails its insert
**after** the Gemini call is paid for.

Note J1-2 changes the shape of this rather than removing it: as written the constraint does not reject
a NULL card, so the producer failure is *silent* rather than loud. Fixing J1-2 makes it loud. Both
orders are wrong; only the sequencing statement makes it safe.

**Change.** One sentence in §5.2 and again in §10: *the producer fix lands before or with the
constraint, never after* — and list it as a prerequisite task, not a parenthetical.

### J3-4 — A-8 unaddressed: rule 14 retires resolve-time readability on a verification performed in an authorization context no reader has.

§5.1.1:886-888 still reads *"Readability is verified once, at record time, by the writer that just wrote
the bytes — never re-litigated on the read path"*, with no statement of what that verification does and
does not prove. The writer is the worker, running as `service_role` under `artifacts_service_all`
(`0007:16-17`); readers are session clients under the policy §5.0 replaces. **The one failure class the
verification cannot see is an RLS denial** — which is the failure `SupabaseBlobStore.get:27-37` turns
into `null`, i.e. into *absent*.

I re-verified the deployment property B-9 raised: `postgres` carries `rolbypassrls = t` locally, so
`workspace_readable` reads `workspaces` correctly. That closes B-9's failure mode but not A-8's, which
is about the **reader's** context, not the definer's. Neither B-9's one-sentence ownership requirement
nor A-8's post-migration assertion appears in §5.0.

**Change.** State the limit in the rule (*record-time verification proves the bytes landed, not that a
reader may read them*), and add the post-migration assertion: one session-client read per workspace,
executed, not assumed — the same *"assert the collection, do not assume it"* §8:1392 already demands of
the sweeper.

## MEDIUM

**M-R4-1 — `mdCorrectionsHash` is assigned two different homes, and the eligibility rule depends on
which.** §5.0.1:517 puts *"`corrections`, `mdCorrectionsHash` — they change the shared bytes"* on
`workspace_videos`; §5.2.1:952 puts `mdCorrectionsHash` on the **generation**. The whole corrections
eligibility rule is *"the **generation's** `mdCorrectionsHash` vs the **video's** current corrections"*,
which requires the §5.2.1 placement and is unstatable under the §5.0.1 one. §5.2.1 is right; §5.0.1's
row must move `mdCorrectionsHash` out and keep only `corrections`.

**M-R4-2 — §5.0.1's structural claim is false against its own DDL.** :509-511 states *"`video_artifacts`
and `video_generations` both FK to `workspace_videos`, so … a cascade from it reaches them, which is
half of B5's problem solved structurally rather than by convention."* In the DDL, `video_artifacts.workspace_id`
references **`workspaces(id)`** (:596) and `video_generations` declares no FK at all. The cascade the
section credits itself with does not exist, so B5's unreferencing is entirely on §8's transactional
rule with no structural backstop.

**M-R4-3 — the three new `security definer` RPCs declare no `search_path`** (physical rule 5's site
list). `record_artifact` (:695-701), `detach_artifact` (:705, named only) and §11.0's unreference RPC
(:1620-1623) are all specified as `security definer` with no `set search_path`, in a schema where the
one existing definer function uses `search_path = ''` and had to be corrected for exactly this in round
2 (Codex M2). State the setting and the qualification convention once, in §5.1, and apply it to all
three.

**M-R4-4 — `artifact_record_result` is never defined.** `record_artifact` returns
`artifact_record_result -- typed: 'recorded' | 'duplicate' | 'ineligible'` (:700). Whether that is an
enum, a domain or a composite decides whether callers can compare it to a literal (physical rule 8's
site list). Given J2-1, the `'duplicate'` member is also the wrong outcome for the case it will actually
hit.

**M-R4-5 — M-R3-1 still open, and J2-1 makes it worse.** `detach_artifact` is named and unspecified.
Under the current PK the `dig:120 → dig:120@abc` transition is a primary-key change (delete+insert);
under the per-generation PK J2-1 proposes, the whole `@<generationId>` slot-naming convention becomes
unnecessary. Specify the verb *after* deciding J2-1, not before.

**M-R4-6 — M-R3-4 and M-R3-5 are live for the third consecutive round.** `CONTEXT.md:8` still states as
domain law that *"each playlist stores its **own** copy of that video's summary (artifacts are addressed
per playlist)"* while `CONTEXT.md`'s *Artifact manifest* entry states it is *"Keyed by workspace and
video, never by playlist."* `docs/adr/0006:7` still says `<tenantId>`; `:30` still says the conditional
write is *"trivially sufficient"*, which §5.1.1:924-929 retracts on the evidence of five review rounds;
`:68-72` still carries the *"still moves every object"* claim §11.1:1676-1684 withdrew. `CONTEXT.md` and
the ADR are what a plan author reads instead of a 2016-line spec, and both currently hand them the
retracted position. Three rounds of asking makes this a process observation as much as a finding.

## LOW

**L-R4-1 — MEASURED. §5.2's `video_generations` block is still not valid SQL.** Run verbatim:
`ERROR: syntax error at or near "video_generations"` — no `create table`, no commas, no semicolon
placement. Round-2 L-R2-1, round-3 L-R3-3. It matters more than a nit now that J1-1 shows this block is
where two physical-rule fixes failed to land: an unparseable block is a block nobody executes.

**L-R4-2 — §2's slot vocabulary still omits `html`, and the (correct) fail-closed check has now turned
that omission into a hard rejection** — measured under both `kind='dig'` and `kind='render'`. Either add
the slot or state the exclusion in §8; see J2-2, which is the consequence.

---

## Verdict

**NOT CONVERGED.** 6 Blocking, 8 High, 6 Medium, 2 Low.

Three observations for whoever sequences the fixes.

1. **Executing the DDL found four Blocking in about ten minutes, and three of the four are a physical
   rule recurring at a sibling site — the exact failure JOB 1 was created to catch.** Round 3 wrote *"a
   physical rule applies to every SITE, not to the site where you learned it"* and then mis-identified
   one of the two sites it was writing about (J1-3). Classification did not help; a **sweep** did, and
   only when the sweep was *executed*. The plan's acceptance criteria should carry a literal gate:
   *every DDL block in this document runs, in document order, against a scratch schema on a populated
   copy — and every constraint is mutation-tested by an insert that must fail.* J1-2 is the argument
   for the second half: that check passes every test that supplies a card.
2. **The one-row-per-slot primary key (J2-1) is the finding to fix first, because it is upstream of
   four others.** It decides `record_artifact`'s shape, `detach_artifact`'s existence, §6.2's slot
   naming, and whether rule 13 has a set to rank at all. It is also the sixth instance of shape #9, and
   the first to survive a cross-derivation pass — because the pass checks rules against rules, and this
   contradiction is between a rule and a **schema decision no rule states**. Worth adding to the
   inventory's method: *cross-derive rules against the DDL, not only against each other.*
3. **The prose/DDL split is now the document's dominant defect mode, and it is directional.** Every
   instance found this round has the fix in prose and the defect in DDL (J1-1, J3-2), or the fix in one
   DDL block and the defect in the one an implementer reads first (J3-1). The mandate's rule — *where
   prose and DDL disagree, the DDL is the fix and the prose is a claim* — held in every case. The cheap
   structural remedy is to **delete a prose fix once it is applied to the DDL**; leaving both is what let
   three reviewers read J1-1's constraints as present.
