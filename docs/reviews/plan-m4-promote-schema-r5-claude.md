# M4 plan (v5) — round 5, CLAUDE half of the dual adversarial review

**Target:** `docs/superpowers/plans/2026-08-25-m4-promote-the-schema.md` (v5, `6bf3726`)
**Branch:** `docs/m4-plan` · **Date:** 2026-08-25
**Partner this round:** `plan-m4-promote-schema-r5-codex.md` (dispatched independently; not read before writing this)
**Prior rounds read in full:** r1-codex, r2-codex, r3-claude, r4-codex, r4-claude, r4-coordinator.

**What I EXECUTED** (all against the local stack, every statement inside a transaction that was
`rollback`-ed; cleanup verified after each — see *Cleanup* at the end):

- concatenated `01_workspaces.sql` + `03_generations.sql` + `04_artifacts.sql` into a 1,869-line
  `0027` and applied it. It applies cleanly, in one transaction.
- **wrote the `0028` T9 asks for** and applied it after `0027`, in strict reverse order, with **no
  `cascade` anywhere**. It applies cleanly, first attempt.
- ran the corrections **deletion** scenario end to end against real local rows.
- ran `claim_video_slot` and `update_video_annotations` under a real owner JWT, post-`0027`.
- **mutation-tested** the two corrections-sync triggers by dropping them and re-running the RPCs.
- executed T4's seeding instruction literally, then `0027`, then `05_assert.sql`'s backfill assertion.
- shadowed `digest()` in `public` and re-ran T1's CASE expression.
- ran `scripts/check-guard-coverage.py` and `scripts/check-anon-exposure.py --local`.

**What I could NOT run — and this is a FAILURE, not a pass:** production. `CLAUDE_RO_DATABASE_URL`
is **absent** from this environment (`env | grep -c CLAUDE_RO_DATABASE_URL` → `0`). Every production
figure below is therefore **NOT VERIFIED by me**, including the `anon=arwdDxtm` default ACL, which I
do not repeat as fact anywhere in this document.

---

## ⭐ THE PRIMARY QUESTION, ANSWERED FIRST

### DID v5's OWN FIXES INTRODUCE DEFECTS? **YES — three Blocking, all in text that is new in v5.**

| # | v5's own new text | What it broke |
|---|---|---|
| **B1** | T9's lossless property (`:308-311`) | **MEASURED FALSE.** An ordinary playlist deletion makes an orphaned `workspace_videos` row the *only* copy of paid corrections; `0028` then destroys it |
| **B2** | T9's gate (`:318-320`) | **MEASURED INVERTED.** The six schema gates go RED after `0027` and GREEN after `0028` — the exact opposite of what the gate asserts |
| **B3** | T4's seeding instruction (`:231-233`) | **Mutually exclusive with T2's own abort guard (`:149-151`), and it does not achieve its stated purpose anyway** — measured |

The standing condition written into the plan at `:28-29` — *"if round 5 returns new Blockings caused
by v5's own fixes, Phase 6 fires and is not argued again"* — is **satisfied three times over.**

I want to be fair about what this is *not*. v5's fixes are not sloppy; two of the three defects arise
because v5 wrote down something true (the deletion asymmetry, the vacuous assertion) in one section
and then wrote a task in another section that the first section falsifies. That is precisely the
*composition* failure per-task review is structurally blind to, which is the argument for Phase 6
rather than against it.

---

## Blocking

### B1 — T9's lossless property is FALSE, and the thing it loses is paid content. v5 documents the mechanism itself, four sections earlier.

T9 (`:308-311`) states the property as a falsifiable sentence:

> *every column and row `0027` creates is a function of state that predates it, and nothing in
> `lib/ app/ worker/` writes any of it.*

The second clause is **true** — I verified it with the grep the property actually needs (not T7's;
see H1): `grep -rln "workspace_id\|workspaceId" lib/ app/ worker/ tests/ components/` returns
**nothing**, and `workspace_videos` appears nowhere outside the spec directory and three ratchet
scripts.

**The first clause is false, and the plan's own item 4 (`:61-76`) is the proof.** The chain, every
link cited:

| Step | Evidence |
|---|---|
| `videos` cascades from `playlists` | `0001_core_schema.sql:32` |
| `workspace_videos` cascades **only** from `workspaces` | `03_generations.sql:49` |
| deleting a playlist is a button | `DeletePlaylistDialog.tsx` → `app/api/playlists/[id]/route.ts:74` → `supabase-metadata-store.ts:301-305` (`.from('playlists').delete()`) |
| corrections are paid since M2 slice A | `0026_record_correction_spend.sql` |

So after a playlist delete, `workspace_videos.corrections` is the **sole surviving copy**. `0028`
drops that table. **MEASURED**, on a real local row, inside one rolled-back transaction:

```
SUBJECT playlist=337d076f-… video=v-72e5c731-… corr_len=23
wv_corrections_before=23
=== playlist deleted ===
videos_rows_left_for_subject=0
any_other_copy_of_the_corrections_in_videos=0
workspace_videos_row_survives=1
=== now apply the T9 rollback ===
corrections_recoverable_anywhere=0
```

**The stated expiry is also wrong.** `:312-313` says the property *"EXPIRES AT M5, the moment
`record_artifact` gets a caller"* and instructs that sentence to be written into `0028`'s header —
where the person at 2am will read it and believe it. It expires at the **first playlist or video
deletion after M4-β**, which is minutes, not a milestone. A `0028` header carrying "safe until M5" is
worse than no header: it is a false reassurance at the exact moment nobody re-checks.

*Bounding it honestly:* production carries **1** video with non-empty corrections (T1, `:138`), so
today's blast radius is one paid correction. That bounds the *quantity*, not the *class*, and T1's
own `:145-148` makes the argument for me — the number is a function of a corpus that grows with every
ingest, and T9 is the artifact you reach for later, not on the day you write it. A cloud-only user
has no local vault to re-supply from.

**Required:** either (a) `0028` copies each orphaned `workspace_videos.corrections` back into a place
that survives it — there is no such place today, which is itself the finding — or (b) the property is
restated as the narrower thing that is actually true (*"lossless only if no `videos` or `playlists`
row has been deleted since `0027` applied"*), with a **query** in `0028`'s header that a person can
run to check it: `select count(*) from workspace_videos wv where not exists (select 1 from videos v
where v.workspace_id = wv.workspace_id and v.video_id = wv.video_id) and wv.corrections is not null;`
— non-zero means `0028` destroys paid content. That query is one line and it is the falsifier T9
currently does not have.

---

### B2 — T9's gate measures the world BACKWARDS. After `0027` the schema gates are RED; after `0028` they are GREEN.

T9's gate (`:318-320`), repeated as milestone gate 2c (`:372-373`):

> `0028` applies cleanly to the M4-α stack **after** `0027`, and the six schema gates go **red**
> afterwards — proving it actually removed the schema rather than reporting success over an empty set.

**Five of the six gates never read the applied schema at all.** They *build* it from the spec files
inside their own rolled-back transaction:

| Gate | How it gets the schema | Evidence |
|---|---|---|
| 1 `verify-schema.sh` | `SQL=$(printf 'begin;\n'; cat "$DIR"/0*.sql; …'rollback;\n')` | `verify-schema.sh:10` |
| 2 `mutate-schema.py` | copies gate 1 into temp and runs the copy | `mutate-schema.py:875-884` (r3 B2, re-confirmed) |
| 3 `check-guard-coverage.py` | `sql = "begin;\n"` + every `SCHEMA.glob("0*.sql")` + catalog query + `rollback;` | `check-guard-coverage.py:195-206` |
| 4 `check-sentinel-meanings.py` | identical shape | `:106-115` |
| 5 `check-vocabulary-collisions.py` | identical shape | `:95-103` |
| 6 `check-docs.py` | no database | — |

Consequence, **MEASURED**: with `0027` applied, re-executing the spec DDL — which is what gates 1–5
do on every run — fails immediately:

```
=== 0027 applied (simulating the post-M4-alpha local stack) ===
=== now run gate 1's inner SQL against that stack ===
ERROR:  relation "workspaces" already exists
```

So the true polarity is: **`0027` applied → gates RED. `0028` applied → gates GREEN.** T9 asserts the
reverse. The gate cannot report the observation it names, and if run literally it reports the
*opposite* of the fact it is meant to establish — which is worse than an unfalsifiable gate, because
a red result would be read as success.

T3 (`:191-193`) does budget a **rewrite** of gates 1 and 2 rather than a re-point, so a fix is in
scope. But the plan never says what the rewrite must *become*, and re-pointing gate 1 at
`supabase/migrations/0027…sql` changes nothing: the method is still "concatenate the file, execute
it, roll back", which still errors on an applied schema. What T9's gate needs is a gate that
**introspects the live catalog** — a third axis, after r3 B2's *path* and *transport*. Nobody has
named it.

**Required:** T9's gate must name an observation that can actually be made. The honest one is
mechanical and needs no rewrite: *after `0028`, `select count(*) from pg_class c join pg_namespace n
on n.oid=c.relnamespace where n.nspname='public' and c.relname in ('workspaces','workspace_videos',
'video_generations','video_artifacts','video_artifact_sources')` returns **0**, and
`information_schema.columns` has no `workspace_id` on `playlists`/`videos`/`jobs`* — which is what I
asserted in my own run (`ws_col_after=0`). Either that, or T3's rewrite is respecified to read the
live catalog and T9 is stated in terms of the rewritten gate.

---

### B3 — T4's seeding instruction and T2's abort guard are MUTUALLY EXCLUSIVE, and the assertion T4 wants to un-vacuum passes on the seeded data anyway.

Two v5 sentences, in the same document:

- **T1/T2 (`:149-151`)** — *"the migration asserts the count is still zero inside the same
  transaction, immediately before the `workspace_videos` backfill, and **aborts if it is not**."*
- **T4 (`:231-233`)** — *"**T4's seeding must CONSTRUCT that case deliberately** — two `videos` rows,
  one `owner_id`, one `video_id`, two different non-empty corrections — or M4-α will report a green
  assertion that never evaluated anything."*

If T4 seeds it, T2's guard aborts `0027`, so M4-α never applies and **no** assertion runs. If T4 does
not seed it, T4's own complaint stands. There is no state satisfying both.

**MEASURED**, executing T4's instruction literally against the local stack:

```
--- T1/T2 GUARD: conflicting-corrections groups (the migration ABORTS if this is not 0) ---
CONFLICTING_GROUPS=1
--- now apply 0027 WITHOUT the guard, and ask 05_assert.sql's backfill assertion ---
workspace_videos.corrections kept = BETA  - the user paid for this too
NOTICE:  ASSERTION PASSES (wv=109 videos=109) -- and one paid correction was just discarded
```

**And the third line is the part that matters most.** Suppose the guard were removed to let the seed
through. The backfill silently discards `ALPHA` — and `05_assert.sql:65-70`'s assertion **still
passes**, because both sides count *videos that have some corrections* (r3 H3 said so; this is the
first time it has been executed against a constructed collision). So T4's seeding does not convert a
vacuous assertion into a live one. It converts it into an **actively false-negative** one: green,
evaluated, and wrong. T4's stated rationale — *"or M4-α will report a green assertion that never
evaluated anything"* — is answered by an assertion that evaluates and reports green regardless.

**Required:** pick one and say which. Either (a) the guard aborts and T4 seeds only *non-conflicting*
production-shaped data, dropping the sentence at `:231-233`; or (b) the assertion is rewritten to
compare **values**, not counts — e.g. every `workspace_videos.corrections` must equal *some*
`videos.data->>'corrections'` for the same key **and** the number of distinct non-empty values per
key must be 1 — at which point seeding the collision is meaningful and the guard becomes redundant.
(b) is the better answer and it is the fix r3 H3 asked for two rounds ago; v5 added a guard and a
seed instead, and the two collide.

---

## High

### H1 — T9 names the WRONG command as its falsifier. T7's grep tests a different proposition.

T9 (`:310-311`): *"**T7's repo-wide grep is already the command that tests it** — reuse it, do not
write a second one."*

T7's grep is for **`record_artifact`** (`:292-294`). I ran it:

```
$ grep -rlE "record_artifact" --include=*.ts --include=*.tsx --include=*.sql . | grep -v node_modules
tests/lib/blob-addressing-caller-contract.test.ts
…/schema/05_assert.sql   …/schema/04_artifacts.sql   …/schema/03_generations.sql
```

Zero hits under `lib/ app/ worker/ components/` — T7's claim is green. But `record_artifact` is the
write path for **`video_artifacts` / `video_generations`**, which M4 ships **empty**. The property
T9 states ranges over *"every column and row `0027` creates"*, which includes `workspaces`, the three
`workspace_id` columns, and `workspace_videos` — none of which `record_artifact` touches. A grep for
`record_artifact` cannot go red for any of them.

The command that actually tests T9's second clause is the one I ran in B1:
`grep -rln "workspace_id\|workspaceId" lib/ app/ worker/ tests/ components/` → **no output**. That
one is green today and will go red at M5, which is exactly the expiry behaviour T9 wants.

This is `CLAUDE.md`'s *"a script beats a claim only when it reads the thing the claim is about"*,
committed inside the fix for a finding about missing falsifiers. Severity High rather than Medium
because the instruction is *"reuse it, do not write a second one"* — it actively forbids writing the
check that would work.

---

### H2 — T10's gate and milestone gates 1–2 cannot both be green on the same machine, and running T10 is what breaks them.

T10 (`:333`) adds `npm run test:integration` as an M4-α gate. T2 (`:177-183`) already establishes why
that is more than a test run: `tests/integration/global-setup.ts:43-51` shells out to
`npx supabase migration up`, which applies `0027` to the local stack **permanently** — not inside a
transaction, not rolled back, and it *throws rather than skip* (`:51-59`).

Compose that with B2's measurement: once `0027` is applied, gates 1–5 fail with
`relation "workspaces" already exists`. So on any machine that has run T10's gate, milestone gate 1
(`:367`, *"six green against the migration"*) is unreachable, and the only supported ways back are
`0028` (whose own gate is B2's inverted one) or `supabase db reset` — which `docs/deploy.md:36`
records as the command you must never confuse with `db push`.

The plan draws the unseeded auto-apply as a branch in the Order block (`:345-347`) and says *"Anyone
running the suite on this branch should expect it"* — that is honest about the **apply** and silent
about its effect on the **other five gates in the same gate list**. `true-about-the-name-silent-about-
the-layer`.

**Required:** state the required post-rewrite semantics of gates 1–3 (build-from-file vs read-live-
catalog), and order T10 relative to them, or the gate list is unsatisfiable as written.

---

### H3 — Two of the nine triggers have ZERO behavioural coverage, and I mutation-tested it. T10 is presented as the answer to r4 B2; for the money-path pair it is not.

T10's implicit promise is that `test:integration` is *"the only thing standing between [the unseeded
auto-apply] and a silent break"* (`:335-336`). For seven of the nine triggers that is broadly right:
the six `resolve_workspace_*` triggers are covered *by NOT NULL*, because if one stops deriving,
`videos.workspace_id`/`jobs.workspace_id` violate their constraints and the insert fails loudly. I
verified the happy path executes post-`0027` under a real owner JWT:

```
claim_video_slot -> (2,9991)
videos.workspace_id derived = e41c3eda-…
update_video_annotations -> 1
workspace_videos parent exists = 1
workspace_videos.corrections synced = R5 PROBE CORRECTION
```

**The two `videos_corrections_sync_*` triggers are different, and I mutated them out to prove it:**

```
--- MUTATION: drop the two corrections-sync triggers, then run the corrections write path ---
claim_video_slot -> (2,9993)
update_video_annotations -> 1
videos.data corrections = MUTANT
workspace_videos.corrections after mutation = <NULL - DRIFTED, and every RPC above returned SUCCESS>
workspace_videos.corrections_hash = no_corrections_hash? true
```

Every RPC succeeds. Nothing observes the drift, because **nothing in the repo reads
`workspace_videos`** — `grep -rn "workspace_videos" --include=*.ts --include=*.tsx --include=*.sql
--include=*.py --include=*.sh .` (excluding the spec dir and `docs/reviews/`) returns only three
ratchet scripts, no application code and no test.

That silent drift is not cosmetic. `03_generations.sql:53-59` records the measured consequence of
exactly this state: *"cloud permanently rung-1-stale, local current, so `reconcileClassA` returned
`copyToCloud` on EVERY sync, forever"* — **and every append is a paid slot.**

**Required:** T10 must say which of the nine triggers the suite covers and which it does not, and
add the one missing assertion (write corrections through `update_video_annotations`, then assert
`workspace_videos.corrections_hash` matches). A gate list that names a suite without naming its
coverage boundary is the defect class v5 accuses v4 of at `:322-324`.

---

## Medium

### M1 — T1's rewritten pgcrypto CASE has a hole: it cannot see a `digest()` that SHADOWS pgcrypto's. Measured.

`t1-blast-radius.sql:69-81` allow-lists `('public','extensions')` because `corrections_hash_of` pins
`set search_path = public, extensions` (`03_generations.sql:39`). **`public` is searched FIRST.** So a
`public.digest(text,text)` wins over `extensions.digest(text,text)`, and the CASE cannot tell:

```
HONEST hash   = f6c83e3641a08ec21aebc01296ff12f5a46780f0fbadb1c8101309123b95d2c6
SHADOWED hash = 00
t1_verdict    = PASS: pgcrypto resolvable from corrections_hash_of
```

Two further gaps in the same expression, both from reading `:72-79`:

- it matches on **`p.proname='digest'` only** — never on the signature. `corrections_hash_of` calls
  `digest(<text>, 'sha256')`, so it needs the `digest(text,text)` overload specifically; local carries
  both `extensions.digest(text,text)` and `extensions.digest(bytea,text)`. If only the `bytea` form
  were present the CASE still says PASS and the function raises at runtime. The comment at `:56`
  claims the assertion *"FAILS IF … either `digest` overload is in a schema outside that pinned
  search_path"*, which the expression does not test.
- the effective path also includes `pg_catalog`, searched first unless listed; a `digest` there would
  be reachable and the CASE would call it a FAIL. Opposite direction, minor.

**REFUTED, and recorded so round 6 does not pay for it:** `pg_temp` is *not* a hole. A
`pg_temp.digest(text,text)` left a pinned-path function's answer unchanged
(`baseline = a860b858… ; with pg_temp.digest present = a860b858…`) — Postgres never searches the
temporary schema for function names.

**Required:** the direct falsifier is one line and reads the thing the claim is about:
`select corrections_hash_of('café') = '<pinned 64-hex constant>'`. Keep the catalog query as context;
make the *assertion* a call.

### M2 — T3's inventory of gate 3's breakage is itself incomplete: 10 problems, of which the plan names 3.

T3 (`:186-190`) names `art_pending_is_leased`, `art_pending_has_token`, `art_pending_has_reserved_at`
and "zero entries for `video_artifact_sources`". I **ran** it:

```
❌ UNCLASSIFIED  gen_card_is_summary_only
❌ UNCLASSIFIED  gen_major_is_summary_only
❌ UNCLASSIFIED  video_artifacts_identity_uq
❌ STALE  art_pending_has_reserved_at · art_pending_has_token · art_pending_is_leased
❌ STALE  art_summary_has_no_source · video_artifacts_inflight_uq
❌ STALE  video_artifacts_workspace_id_video_id_source_generation_id_fkey
❌ UNMUTATED  video_artifacts_paid_uq
10 problem(s) — guard coverage NOT met   (exit 1)
```

The claim's **direction** is confirmed (gate 3 is red before any re-pointing). Its **inventory** is
not: three UNCLASSIFIED entries and one UNMUTATED reconciler appear nowhere in the plan, and
`video_artifacts_paid_uq`'s "UNMUTATED" is a different repair from a stale-entry deletion — it needs a
new mutation in `mutate-schema.py`. T3 says *"Estimate accordingly"*; the estimate is against a
subset. Same shape as B3: a finding cites where the reviewer saw it, not where it lives.

### M3 — The `Dxtm` sentence sits at TWO sites in the file being promoted, and v5 gives no task for either.

`04_artifacts.sql:253` **and** `:650` both carry *"`pg_default_acl` carries `anon=Dxtm/postgres` for
every table `postgres` creates in `public`"*. r4-claude H2 asked for that sentence to be corrected
before it becomes a migration; v5 records the finding in T3 (`:207-210`) and adds **no task** to
touch the file, so both copies ship verbatim under T2's *"removing nothing else"*.

⚠ I could not re-measure production (`CLAUDE_RO_DATABASE_URL` absent), so I am **NOT** asserting
`arwdDxtm` and I am not claiming the sentence is wrong. What I can assert: v5 itself says *"the
production half is the reviewer's figure and was NOT independently re-measured … **Re-measure before
this drives work**"* (`:208-210`) — and then lets it drive T3's severity framing without the
re-measurement having happened. Either re-measure, or drop the prod figure from the plan.

### M4 — T9's gate needs an "M4-α stack" that the Order block places after T9.

`:318` — *"`0028` applies cleanly to the **M4-α stack** after `0027`"*. The Order block (`:343`) is
`… ─▶ T9 ─▶ T10 ─▶ T5 ─▶ M4-α(deliberate, seeded)`. T9 precedes the thing its gate names. The
unseeded branch at `:345-347` probably supplies a stack in practice, but the gate says *M4-α*, and
which one it means changes what the gate proves (a seeded stack with T4's collision cannot exist —
see B3). Name the stack.

### M5 — the reorder puts T2 behind a decision the plan explicitly does not settle.

`:343` reads `T0 ─▶ T1 ─▶ T4(seeding decision) ─▶ T2`. But T4 is not decomposed anywhere, and its
own gate (`:244-245`) belongs to the *other* half of T4 (the `05_assert.sql` home) — which
Open Questions (`:413`) says *"depends on whether CI gets a Postgres, a dev-infrastructure decision
with its own cost."* A subagent executing top-down under `subagent-driven-development` sees "T4
before T2", opens T4, and finds a task half-blocked on an unsettled infrastructure decision, standing
in front of the milestone's only deliverable. Split T4 into T4a (seeding decision, unblocked) and T4b
(the home, blocked), or say plainly that only the seeding half gates T2.

---

## Low

### L1 — REFUTED: the `0028` drop order IS expressible, without `cascade`, first attempt.

The obvious worry about T9 — that FK and trigger dependencies make a reverse-order drop
unwritable — is wrong, and I established it by writing the file rather than reasoning about it.
Strict reverse order (04 → 03 → 01), no `cascade` anywhere, 45 statements, applies cleanly:
`=== 0027 APPLIED === / === 0028 APPLIED === / ws_col_after=0`. Two orderings are load-bearing and a
naive attempt would get them wrong: `video_artifact_sources` before `video_artifacts`, and
`alter table videos drop constraint videos_workspace_video_fk` **before** `drop table
workspace_videos`. Worth putting in T9 so the implementer does not rediscover them.

### L2 — REFUTED: `0027` does not break the existing write paths. Measured, not predicted.

r4-claude B2 flagged that its own reasoning about the triggers was *"a prediction, not a result"*.
It is now a result: post-`0027`, under a real owner JWT, `claim_video_slot` returned `(2,9991)`,
`videos.workspace_id` derived, the `workspace_videos` parent was created, and
`update_video_annotations` synced corrections. (`enqueue_job` I could not exercise cleanly — it
rejected my synthetic arguments with `too_long` from its own guard at `0018`, unrelated to `0027`;
**NOT VERIFIED** for `jobs`.) This does not retire T10 — B2's point was the absence of a *gate*, and
one reviewer's rolled-back probe is not one.

### L3 — the coordinator's own r4 open finding is not folded, and it is one line of script.

`r4-coordinator.md:101-105`: *"`05_assert.sql` is NEVER a migration"* is **prose only**;
`grep -rn "05_assert" scripts/ .github/ .claude/hooks/` returns comments, nothing asserting
`supabase/migrations/` is free of `execute p_sql` or `delete from profiles`. v5 restates the rule
three times (`:93-94`, `:56-60`, `:167-168`) and still gives it no falsifier. Given the payload, a
one-line ratchet (`grep -L` over `supabase/migrations/*.sql` for those two strings) closes it.

### L4 — r3 L4 is fixed. `- [ ]` checkbox syntax now present (10 steps), so `check-plan-progress.py` will not fail closed.

### L5 — T6's named command is CORRECT for this repo today. Verified.

`supabase db push --linked` matches `docs/roadmap-to-launch.md:162` (the last real prod apply) and
`docs/deploy.md:30-31`. Installed CLI is **2.115.0** (`npx supabase --version`), the version the plan
pins. The plan's claim that the one-transaction guarantee is void for `psql -f` without
`--single-transaction` or a dashboard paste is correct as a matter of Postgres semantics. ⚠ I did
**not** re-verify r4-claude's byte-level reading of the CLI binary's `transactionMode`; that premise
is inherited, not re-measured here.

---

## Disposition of what v5 claims to have fixed

| Prior finding | v5's fix | This round |
|---|---|---|
| r4-claude B1 — no rollback | T9 | **Task added; its property, its expiry and its falsifier are all wrong** — B1, B2, H1 |
| r4-claude B2 — no behavioural gate | T10 | **Added, and it is the right instrument** — but its coverage boundary is unstated (H3) and it disables gates 1–5 (H2) |
| r4-claude H1 — the order is fiction | T2's ⛔ block + redrawn Order | **Honest about the auto-apply. The reorder introduced M5, and the branch is silent about the effect on the other gates** |
| r4-claude H2 — name all five tables | T3 (`:198-199`) | **CONFIRMED FIXED.** I counted independently: `grep -niE "^ *create table"` over `01/03/04` returns exactly 5, and they are the 5 named. `MONEY_TABLES` → RULE 2 mechanism verified at `check-anon-exposure.py:186-191` + `:158-168`; `--local` runs green (5/5, baseline 5, exit 0). ⚠ Note RULE 2 is **two-sided** — it also fails if the count *drops* below baseline |
| r4-claude M3 — name the apply command | T6 | **CONFIRMED FIXED** (L5) |
| r4-claude M4 — pgcrypto counts, cannot fail | T1's CASE | **Improved, still holed** (M1) |
| r4-coordinator — `supabase migration down` exists but resets | `:81-83`, `:314-317` | **Characterisation is accurate as far as `--help` goes.** Like the coordinator, I did **NOT execute it** — that is the one command nobody should run to find out. Labelled UNVERIFIED-BY-EXECUTION, correctly, in the plan |
| r4-coordinator — the duplicated maintenance-window claim | `:160-163` | **CONFIRMED FIXED.** `grep -n "maintenance window"` returns 4 hits, all consistent |
| r4-codex Low — T1 SQL not in a file | `docs/superpowers/specs/m4/t1-blast-radius.sql` | **CONFIRMED FIXED**; committed and re-runnable |

---

## Cleanup — the local stack was NOT mutated

Every probe ran inside `begin; … rollback;`. Verified after the last one:

```
FINAL ws_col=0 workspaces_tbl=0 playlists=5124 videos=3547 jobs=87 r5rows=0
```

— identical to the pre-review reading (`ws_col=0 … playlists=5124 videos=3547 jobs=87
corrected_videos=108`). The two scratch files I copied into the container (`/tmp/m4r5/`) were removed
with `docker exec … rm -rf /tmp/m4r5`. No repo file was modified except this review.
`an-instrument-that-edits-the-repo-corrupts-its-peers` — observed.

---

## Verdict

**3 Blocking · 3 High · 5 Medium · 5 Low.**

**The single most important finding is B1.** Not because it is the largest, but because of what it
is made of: v5 wrote down the deletion asymmetry correctly, in bold, as one of the five things a
reader must not skip (`:61-76`), and then two hundred lines later wrote a task whose load-bearing
property that same paragraph falsifies — and named an expiry (*"at M5"*) that is off by a user
gesture. Nobody was careless. The document is simply large enough that its own sections no longer
constrain each other, and the review method that produced it inspects one task at a time. That is the
definition of a composition defect, and it is the argument the overruling of Phase 6 turned on:
round 4's findings were called *"missing paperwork, not composition defects"*. Round 5's are not
missing paperwork. Three of them are the paperwork **contradicting itself**.

The plan's own standing condition (`:28-29`) is met: **Phase 6 fires, and per the plan's own words it
is not argued again.**

**NOT CONVERGED**
