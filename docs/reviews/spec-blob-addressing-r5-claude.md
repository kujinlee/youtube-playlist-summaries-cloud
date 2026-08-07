# Adversarial review — ROUND 5 (Claude) — stable blob addressing

Artifact: `docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md` +
`docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/{01,03,04,05}*.sql`,
branch `docs/blob-addressing-decisions` @ `35bd156` (worktree: `05_assert.sql` modified).

Everything marked **MEASURED** was executed against the live Postgres in
`supabase_db_youtube-playlist-summaries-cloud` inside `begin … rollback`. Mutation testing was run
against an **isolated copy** at `HEAD` (the worktree baseline is red — see B4 — so worktree mutations
report the wrong cause; my first pass was invalid for exactly that reason and was discarded).

---

## BLOCKING

### B1 — `gen_card_complete` fails OPEN on JSON nulls, and the resulting placeholder card **wins the ranking and becomes the served summary**

`03_generations.sql:42-44` uses `card ?& array[...]`. `?&` tests **key existence, not value**. Round
4's J1-2 hardened this against `card = NULL` (SQL null) and left `{"tldr":null, …}` (JSON nulls)
wide open — the same defect one level down. Root-cause shape #9, seventh instance.

It does not stop at "an incomplete card is accepted". The top ranking rung in **both** views
(`04_artifacts.sql:92`, `:116`) is
`(g.card->>'mdCorrectionsHash' is not distinct from wv.corrections_hash)`. `->>` on a JSON null
yields SQL `NULL`, and for a video with **no corrections** — the common case — `wv.corrections_hash`
is also `NULL`, so `NULL is not distinct from NULL` is **TRUE**. The empty card is the *only*
candidate that ranks corrections-current, and rung 1 outranks format and recency entirely.

**MEASURED** (all-null card vs a complete `docVersion 4.0 / produced 2026-05-01` generation `gREAL`,
and a `doc_version_major = 99` generation `gLIE`):

```
###### Q1: does gen_card_complete reject a card of JSON NULLs?
INSERT 0 1                      <- accepted
 card ?& array[...] on an all-null card | t

###### Q2 corrections-current?  gNULLS | t
                                gREAL  | f
###### Q3 served summary | gNULLS | kNULLS      <- the empty card beats major-4 AND major-99
```

**Failure scenario, and it is not hypothetical.** `lib/cloud-sync/sync-run.ts:534-542` explicitly
constructs `{ docVersionMajor: 0, mdGeneratedAt: null, mdCorrectionsHash: null, mdHash: null }` and
calls it *"an HONEST unresolved placeholder"*. §5.3 (`:1362-1363`) says a local win **records a new
generation whose card carries the local tuple**. That tuple, recorded as a card, passes
`gen_card_complete` and then permanently outranks every real, paid generation for every video with no
corrections. Paid content becomes unreachable behind an empty row.

**Change:** require non-null *values*, not keys —
`check (kind <> 'summary' or (card is not null and (select bool_and(card ->> k is not null) from unnest(array['tldr','takeaways','docVersion','mdGeneratedAt','processedAt','mdCorrectionsHash']) k)))`
— and make rung 1 absence-explicit so a generation that recorded *no* corrections hash is not treated
as agreeing with a video that has *no* corrections (`card->>'mdCorrectionsHash' is not null and … is not distinct from …`).
Add a negative assertion for the all-null card and a positive one for the ranking outcome.

### B2 — the two views bypass RLS; the grant they are missing is one every maintainer will add, and adding it leaks every tenant's manifest

Two composing defects in `04_artifacts.sql:62-119`:

1. **No grant on either view.** `grant select on video_artifacts to authenticated, anon` (`:65`)
   covers the raw table; nothing grants anything on `video_summary_current` /
   `video_artifacts_current`. **MEASURED** as `service_role`:
   `ERROR:  permission denied for view video_artifacts_current`. The serve path cannot read the object
   the design says it resolves `current` from, so this grant *must* be added.
2. **Neither view sets `security_invoker=true`.** **MEASURED** `pg_class.reloptions` → empty for both.
   A Postgres view defaults to the **view owner's** privileges, so it bypasses RLS on
   `video_artifacts` — which has `force row level security` and (**MEASURED**) **0 policies**.

Add the grant from (1) — exactly as a maintainer fixing the permission error would — and:

```
###### RLS-2: impersonate user #1 (authenticated), two tenants seeded
 rows visible via the RAW table (RLS enforced)      |     0
 rows visible via the VIEW (security_invoker unset) |     2
 other tenants blob_keys leaked through the view | secret-000651f8-f83e-4fe6-8921-42dda98fe9e6
                                                 | secret-00071506-c654-40aa-952a-adf7e43ec37d
```

Every workspace's artifact manifest and blob keys, readable by any authenticated user. Root-cause
shape #2 (IDENTITY AS GRANT), and shape #10 — RLS + an explicit policy were written for `workspaces`
(`01_workspaces.sql:18-22`) and for both tables, and not re-derived for the views three files later.

**Change:** `create view … with (security_invoker = true)` on both, add the missing
`grant select … to authenticated, anon, service_role`, add a policy on `video_artifacts`
(`using (workspace_id in (select id from workspaces where owner_id = auth.uid()))`), and add an
assertion that impersonates a second tenant and asserts **0** rows through the *view*.

### B3 — §5.3's load-bearing "field for field / runs unmodified" claim is false in two places, and the oscillation it claims to prevent is reproducible

§5.3 (`:1355-1357`) asserts `ClassASignals` *"is `mdHash`, `docVersionMajor`, `mdGeneratedAt`,
`mdCorrectionsHash` — and those are, field for field, the card fields that `video_artifacts_current`
ranks on"*, and (`:1361`) that `reconcileClassA` *"runs as written, unmodified."* Compared field by
field against `lib/cloud-sync/types.ts:4-11` and `lib/cloud-sync/reconcile-class-a.ts`:

| `ClassASignals` field | Cloud source | Ranked on by the view? |
|---|---|---|
| `summaryMdKey` (`types.ts:5`) | `video_artifacts.blob_key`, not the card | no |
| `mdHash` (`types.ts:6`) | **does not exist** | no |
| `docVersionMajor` (`types.ts:7`) | column `doc_version_major` (card holds `docVersion`, a string) | yes — rung 2 |
| `mdGeneratedAt` (`types.ts:8`) | card `mdGeneratedAt` | **NO — the view ranks `g.produced_at`** |
| `mdCorrectionsHash` (`types.ts:9`) | card `mdCorrectionsHash` | yes — rung 1 |
| `backfilled` (`types.ts:10`) | **does not exist** | no |

Six fields; the sentence names four. Two breaks are load-bearing:

**(a) `mdHash` is not in the card and not a column.** `gen_card_complete`
(`03_generations.sql:43-44`) requires `tldr, takeaways, docVersion, mdGeneratedAt, processedAt,
mdCorrectionsHash` — no `mdHash`; §5.2's card list (`:1128`) does not contain it either. The spec
**already knows this** and says so twice: `:1773-1775` *"`mdHash` looks like one and is not … grep for
`mdHash` across all 23 migrations returns **zero**"*, and `:2254` *"needs a persisted hash of the body,
and **none exists**"*. §5.3 contradicts §9.1 and §15 of its own document. `reconcileClassA` reads
`mdHash` at `:17-18` as **presence** and at `:32` as **equality**; project it as `null` and `:23`
returns `copyToCloud` unconditionally — every sync appends a new generation, forever, and each append
is a paid slot. Derive it instead by reading the cloud blob and you have reintroduced shape #1 on the
money path (`SupabaseBlobStore.get` cannot prove absence); `sync-run.ts:697` guards exactly this today
via `cv.summaryMd`, a `videos`-row column this design replaces, so the existing guard does not carry
over.

**(b) the recency rung ranks a different value on each side.** The view orders by `g.produced_at`
(`04_artifacts.sql:94`, `:118`); `reconcileClassA:49` orders by `mdGeneratedAt`. Nothing ties them,
and §5.3's own local-win protocol (`:1362-1363`) guarantees they diverge: an appended generation has
`produced_at = now()` and a card `mdGeneratedAt` inherited from the old local file.

**MEASURED** — `gA` (produced 2026-01-01, card mdGeneratedAt 2026-05-01) vs `gB` (produced
2026-05-01, card mdGeneratedAt 2026-01-01), same major, both stale:

```
 view picks                                          | gB | kB
 reconcileClassA would pick (max card mdGeneratedAt) | gA
```

Two replicas, opposite winners, each correct by its own rule — the exact oscillation §5.3 `:1365-1369`
claims round 3's A-1 eliminated (*"One hierarchy, two implementations, and they must not drift"*).
They have already drifted, in the section that asserts they have not.

**Change:** rank the view on the card's `mdGeneratedAt` (or add a `md_generated_at` column and
constrain it `= card->>'mdGeneratedAt'`), and either persist `md_hash` on `video_generations` or
replace §5.3's "runs unmodified" with the actual projection and the honest statement that `mdHash`
requires a schema addition. Do not ship §5.3 as written.

### B4 — MONEY: two writers can both hold an in-flight reservation on one slot, and the artifact's own gate is currently RED

`04_artifacts.sql:57-60` has partial uniques for **paid** (`…, generation_id`) and **free**
(`… where generation_id is null`). Neither constrains **`state`**. Two writers racing the same slot
mint different `generation_id`s, so both `pending` rows are unique and both insert.

**MEASURED** against `HEAD`:

```
###### P7 MONEY: two concurrent writers, both reserve the same slot
 in-flight reservations on ONE slot |     2
```

Both writers proceed to call Gemini. This is the 6¢→12¢ shape (§rule 19, `:842`) reappearing at the
reservation rather than the probe: rule 19's record-first order makes *"no record ⇒ no bytes"* true,
but nothing makes *"a record ⇒ only one writer"* true, so the guard's `busy` branch is never reached.

The coordinator added an assertion for this to the worktree (`05_assert.sql:102-115`) referencing
`video_artifacts_inflight_uq` — an index that **exists nowhere in the schema** (grep across the whole
spec directory returns only that comment). **MEASURED, worktree, at the time of writing:**

```
ERROR:  ASSERTION FAILED — should have been rejected: a SECOND in-flight reservation on one slot (both writers would pay Gemini)
❌ schema FAILED     (exit 1)
```

**Change:** add `create unique index video_artifacts_inflight_uq on video_artifacts (workspace_id, video_id, slot) where state = 'pending';`
— and read H4 before doing so, because that index turns a dead lease into a permanent slot block.

---

## HIGH

### H1 — 15 of 25 schema guards are untested; two of them are the ones the assertions explicitly name

Method: delete one guard, re-run `verify-schema.sh` against the `HEAD` assertion file, check whether
any assertion goes red. **All MEASURED.**

| Guard | Removal → | |
|---|---|---|
| `art_slot_kind` (`04:52`) | **GREEN** | untested |
| `art_pending_is_leased` (`04:55`) | **GREEN** | untested |
| `state in (…)` (`04:27`) | **GREEN** | untested |
| FK → `video_generations` (`04:50-51`) | **GREEN** | untested |
| `blob_key not null` (`04:31`) | **GREEN** | untested |
| summary view `state='recorded'` (`04:90`) | **GREEN** | untested |
| summary view `not g.body_collected` (`04:90`) | **GREEN** | untested |
| current view `state='recorded'` (`04:107`) | **GREEN** | untested |
| current view `not coalesce(g.body_collected,false)` (`04:107`) | **GREEN** | untested |
| rank rung: source-currency (`04:114-115`) | **GREEN** | untested |
| rank rung: `doc_version_major`, summary view (`04:93`) | **GREEN** | untested |
| rank rung: corrections, summary view (`04:92`) | **GREEN** | untested |
| `left join video_summary_current` → inner (`04:105`) | **GREEN** | untested |
| `gen_summary_has_format` (`03:45`) | **GREEN** | untested |
| gen FK → `workspace_videos` (`03:38-39`) | **GREEN** | untested |
| `produced_at not null` (`03:32`) | **GREEN** | untested |
| *(tested: `art_paid_has_generation`, both unique indexes, FK→`workspace_videos`, `gen_card_complete`, gen `unique(…,kind)`, current-view corrections rung, `left join video_generations`)* | red | ok |

**The two that matter most are masked by each other.** `05_assert.sql:62-65` is labelled *"slot=html
declared kind=dig (round 3 B-5 failed OPEN on exactly this)"* and `:70-73` *"pending row with NO LEASE
(round 4 Codex #5)"*. Both fixture rows are **also FK-invalid** — they cite `gNEW`, which is
`kind='summary'`, against `slot`/`kind` of `dig`. So each assertion is satisfied by a *disjunction*:
remove the CHECK and the FK rejects it; remove the FK and the CHECK rejects it. **MEASURED** with a
double mutation:

```
DOUBLE MUTANT (art_slot_kind + gen FK removed): red -> ASSERTION FAILED — should have been rejected: slot=html declared kind=dig
```

Red only when **both** are gone. Round 3's B-5 fix and round 4's Codex #5 fix are each still
unverified, in the file written to verify them. Shape #6, and the same "named in a comment, not
written" pattern `05_assert.sql:28-31` calls out about the free render.

Four view filters and four ranking rungs having **zero** coverage is the larger half: `body_collected`
(round 1 H7's lifecycle marker) is never set to `true` anywhere in the suite, and
`video_summary_current`'s ranking — the input to everything derived — is never asserted at all
(every `select … from` in the assertions reads `video_artifacts_current`).

**Change:** make each negative fixture violate **exactly one** guard (use an FK-valid generation of
the right kind); add positives for `body_collected = true`, a `pending` row, `gen_summary_has_format`,
an invalid `state`, and a second competing model to exercise the source-currency rung.

### H2 — the two views disagree on `slot='summary'`, which is cross-generation mixing by construction

`video_artifacts_current` (`04:114-115`) ranks on source-currency *against `video_summary_current`*,
and applies that rung to **every** slot — including `summary` itself, which is therefore ranked
against its own output. Nothing constrains `source_generation_id` on a summary row (no FK at all, and
no `check (kind <> 'summary' or source_generation_id is null)`).

**MEASURED** — one summary row given `source_generation_id='gGHOST'`:

```
 video_summary_current   | gB
 video_artifacts_current | gA
```

The summary the user is **served** (`gA`, via `video_artifacts_current`) is not the summary every
derived artifact is **ranked against** (`gB`). A `model` whose `source_generation_id='gB'` is scored
"source-current" while the reader sees `gA`'s body — §6's *"sharpest constraint"* violated by the view
pair that was added to enforce ranking.

**Change:** exclude `slot='summary'` from the source-currency rung
(`(a.slot = 'summary' or a.source_generation_id is null or …)`), add
`check (kind <> 'summary' or source_generation_id is null)`, and assert the two views agree on
`slot='summary'` for every row.

### H3 — the floor's stated guarantee ("cannot empty a non-empty set") is false, and nothing stops GC emptying it

`§5.1.1:1021` — *"**Servable** (the floor) | `state = 'recorded'`, and the generation is not
`body_collected`. That is all of it, **and it cannot empty a non-empty set**"* — and the inventory
repeats it (`spec-blob-addressing-rules-inventory.md:190-193`). The second conjunct empties it.

**MEASURED** — two recorded summary generations, then `body_collected = true` on both:

```
 artifacts_current rows after ALL summaries collected | pdf:summary | kPDF
```

Summary slot: 2 rows → **0**. Exactly round 3's A-2 failure mode (*"the summary vanishes from the
page"*), reached through GC instead of through corrections. §8 never mentions `body_collected` (grep:
only `:1021`, `:1375`, `:1579`) and states no rule that GC must never collect the **current**
generation — §8's retention rule (`:1586-1591`) is written purely in terms of "not current", which is
the right rule for *blobs* and says nothing about the marker on the *generation row*.

Note also the asymmetry the same line creates: a free render has no generation, so
`not coalesce(g.body_collected,false)` is **always true** for it — free renders are structurally
exempt from body collection and keep advertising a rendered copy of a body that was collected
(shape #4). Confirmed by the same measurement: `pdf:summary` survived while every summary vanished.

**Change:** either restate the floor honestly ("no rule that is not about byte existence may gate"),
or drop `body_collected` from the filter and let it rank. Either way add the explicit §8 rule
*GC never collects the generation that is current*, and assert it.

### H4 — the lease is written and never read: no reclaim path, so the money guard's safe branch has no exit

`art_pending_is_leased` (`04:55`) and `lease_attempts` (`04:33`) were added by round 4 Codex #5
because *"a writer that dies leaves a permanent `busy`"* (`:708`). The columns exist; **nothing acts on
expiry**. Grepping the whole spec for `lease_expires|lease_attempts|reclaim|expired lease` returns a
single hit — the sentence that motivates the column (`:708`). There is no reclaim RPC, no
`where lease_expires_at < now()` anywhere, and `lease_attempts` has no bound and no reader despite the
comment citing `reserve_serve_model`'s attempt bound (`0012/0014`) as its model.

Consequence: record-first (rule 19) plus a crash between `pending` and the bytes leaves a `pending`
row forever. The slot reads `busy`, so nobody re-spends — safe — but nobody can ever produce it
either. Adding B4's `inflight_uq` makes this strictly worse: it converts the dead lease from "the
guard says busy" into a **hard uniqueness violation** on every future attempt.

**Change:** specify the reclaim (a `pending` row with `lease_expires_at < now()` is stealable, bumping
`lease_attempts`, with a terminal state past N), and make B4's index
`where state='pending' and lease_expires_at > now()` — or take the reclaim through an RPC that deletes
the expired row first. Assert both the steal and the attempt bound.

### H5 — `doc_version_major` (the format rung) is unconstrained against the `docVersion` the body carries

`03_generations.sql:31` is a bare `int`; the card holds `docVersion` as a string (`"3.3"`). Nothing
ties them, so the column the ranking trusts can contradict the card that travels with the body — which
is the "card/body lie" §5.2 exists to remove, moved into the ranking key.

**MEASURED:** a generation with `card->>'docVersion' = '3.3'` and `doc_version_major = 99` inserts
cleanly. (It lost only because B1's empty card outranks everything; with B1 fixed it wins.)

**Change:** `check (kind <> 'summary' or doc_version_major = split_part(card->>'docVersion','.',1)::int)`,
or derive the column as `generated always as (…) stored` and delete the input.

### H6 — §6.2's `start_sec`/`end_sec` are nullable and unenforced, and §6.2 says that is unrecoverable

§6.2 (`:1478-1481`): *"persist `start_sec` and `end_sec` on the artifact-manifest row **at write
time** … **Cheap now, impossible to retrofit after the first sweep runs.**"* `04_artifacts.sql:30-31`
declares both `int`, nullable, with no constraint requiring them for `kind='dig'`.

**MEASURED:** `dig:120` row accepted with `start_sec` and `end_sec` both NULL.

By §6.2's own reasoning, every dig written before someone notices is permanently unattachable — the
span is recoverable only from a `summary.md` that §8 collects. This is the one finding in the set
where the cost of missing it is *irreversible*.

**Change:** `check ((kind = 'dig') <= (start_sec is not null and end_sec is not null))` (matching the
biconditional style of `art_paid_has_generation`), plus a negative assertion.

---

## MEDIUM

- **M1 — "APPEND-ONLY" is enforced by nothing.** `04:36` and `:44-45` assert it; the table has no
  trigger and no rule, and `04:64` grants `update, delete` to `service_role`. The partial unique
  stops a *duplicate* `(slot, generation)` — it does not stop `update … set blob_key = …` on a
  recorded paid row (shape #3, a mutable value in an address, the defect this design exists to remove)
  or a `delete` that orphans paid bytes (the serial-coherence defect). Add a
  `before update or delete` trigger rejecting changes to recorded paid rows, or state plainly that
  append-only is a convention.
- **M2 — §4.0 and §6.2 give different slot formats for the same artifact.** `:278` says
  `slot='dig:<sectionId>'`; `:1466` says `dig:<sectionId>@<generationId>` for a detached dig. If
  detaching *changes* the slot, that is an UPDATE to an address on an "append-only" table (M1); if it
  does not, §6.2's row is not distinguishable. Pick one and state the transition.
- **M3 — a nested `relDir` key can enter the bucket by a sync path that skips the guard the serve path
  has (shape #10, fourth instance).** The worker/serve path enforces a single-segment logical key
  (`lib/html-doc/assert-cloud-summary-md-key.ts:14-19`); `lib/cloud-sync/sync-run.ts:263` and `:381`
  call `putStaged(toP, video.summaryMd, …)` with no such assertion, and nested keys are documented as
  "real and supported" (`lib/cloud-sync/reconcile-serial.ts:128-131`). §4.0 classifies the result as
  **unknown → fail closed, report**, so a routine sync permanently signals "a migration that is not
  finished" (`:293-294`). Apply the same assertion at both `putStaged` sites.
- **M4 — the content-addressed PDF cache cannot be represented.** `lib/pdf/pdf-render-version.ts:22`
  mints `pdfs/${base}.r${V}.${sha256(html).slice(0,16)}.pdf` — deliberately many concurrent variants
  per video — and §4.0 maps all of them to one `slot='pdf:<kind>'`, which
  `video_artifacts_free_uq` (`04:59-60`) caps at one row. Either the manifest loses rows (making them
  §8 root-set-2 candidates) or the cache loses its point. Decide whether the render hash belongs in
  the slot.
- **M5 — `source_generation_id` has no FK.** `04:29` is bare `text`. It is compared against
  `s.generation_id` (`04:115`) and silently never matches when stale or mistyped, which reads as
  "source-stale" rather than as an error. Add the composite FK (accepting `MATCH SIMPLE` disables it
  when null, which is the wanted behaviour here).
- **M6 — the `anon`/`authenticated` grant on the raw table is inert and misleading.** `04:65` grants
  SELECT, but `force row level security` with **0 policies** (MEASURED) means it returns nothing. It
  reads like an intentional client-read surface and is not one; combined with B2 it points a future
  maintainer at the *unfiltered* manifest (pending rows, superseded generations, detached digs) rather
  than at `current`.

---

## LOW

- **L1** — `slot_kind` (`04:9-18`) is a plain function used inside a CHECK. `create or replace`
  changes the constraint's meaning without revalidating existing rows, and it has no pinned
  `search_path`. Mark it `immutable` (it is) *and* schema-qualify, or inline the predicate.
- **L2** — `ClassASignals.summaryMdKey` and `.backfilled` (`types.ts:5,10`) have no cloud source
  (B3). `reconcileClassA` never reads either, but `sync-run.ts:694` reads the key equivalent and
  `reconcile-class-b.ts:43` reads `backfilled`, so the projection cannot simply invent them.
- **L3** — `slot like 'html%'` (`04:17`) matches `htmlFoo`/`htmlish`, unlike the anchored `pdf:%`.
  Use `'html'` or `'html:%'` for symmetry with the other free slot.
- **L4** — `lib/storage/supabase/consistency.ts:17-42` (`writeArtifact`) accepts an arbitrary
  caller-supplied key with no shape validation. Zero production callers today, but it is an open hole
  in §4.0's totality claim.

---

## Notes on the review itself

- §4.0's classifier **is** total, because of the `Anything else → fail closed` row — that row does its
  job, and the only shapes I found outside the eight named families (M3, M4, `_staging`) land on it
  safely. §10.0's producer claim **is** still true in code (`lib/job-queue/summary-handler.ts:149-165`
  builds `docVersion` + `processedAt` and neither `mdGeneratedAt` nor `mdCorrectionsHash`); the gap is
  that it names one producer while `lib/pipeline.ts:271-272` and `lib/cloud-sync/sync-run.ts:316-317`
  are two more, and only the local one is already compliant. Rule 19's rescoping (`:849-864`)
  survives scrutiny: the money guard needs containment only at a fresh `<ws>/videos/<v>/<gen>/…` key,
  and neither exception can be that key. B4/H4 are failures of a *different* premise (that a record
  implies a single writer), not of the rescoping.
- Slide assets were treated as withdrawn per the brief and are not reported.
- The mutation harness, all probes and the isolated schema copy are under
  `…/scratchpad/{mutations.py,mut/}`. No file in the repo was modified by this review; `04` and `03`
  were restored to `HEAD` byte-for-byte after each mutation (verified: `git diff HEAD` clean for both).

---

**VERDICT: NOT CONVERGED** — 4 Blocking, 6 High.
