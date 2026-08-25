# M4 plan (v3) — round 3, CLAUDE half of the dual adversarial review

**REVIEW GAP:** codex — not run for this round. Round 3 was dispatched specifically to supply the Claude half that rounds 1 and 2 lacked; it is a single-reviewer round by construction, and saying so is the point of this line.

**Target:** `docs/superpowers/plans/2026-08-25-m4-promote-the-schema.md` (v3)
**Branch:** `docs/m4-plan` · **Date:** 2026-08-25
**Prior rounds:** `plan-m4-promote-schema-r1-codex.md` (4B/3H/2M/1L), `plan-m4-promote-schema-r2-codex.md` (2B/2H/2M/1L) — both read in full before starting.

**Why this half exists:** the memory `dual-review-halves-are-not-redundant` — Codex-only rounds once
cleared a live money guard that the skipped Claude half caught in one pass. Deliberately different
angles: money, RLS/grants, the plan's own gates' falsifiability, absences, and executability.

Every claim below is either cited `file:line` or labelled **UNVERIFIED**. Nothing here repeats a
Codex finding without saying CONFIRM or REFUTE.

---

## Blocking

### B1 — T2 instructs promoting `05_assert.sql` into production. It contains `truncate`, `delete from profiles`, an unrevoked arbitrary-SQL executor, and two statements that are not SQL.

Plan `:120`:

> Promote **all four spec files** as migrations starting at **`0027`** … **without removing anything**.

The four spec files are `01_workspaces.sql`, `03_generations.sql`, `04_artifacts.sql`,
`05_assert.sql` (there is no `02` — `01_workspaces.sql:11-12` explains why). So the sentence an
implementing subagent executes says: make `05_assert.sql` a committed migration.

What that migration would do, against production data holding paid content:

| Evidence | What it is |
|---|---|
| `schema/05_assert.sql:757` | `execute 'truncate video_artifacts'` |
| `schema/05_assert.sql:2207` | `delete from profiles where id = p` |
| `schema/05_assert.sql:32-55` | `create function assert_raises(p_sql text, …)` — `execute p_sql`, **deliberately with no pinned `search_path`** (`:28-31`) and **no `revoke`**. It is the only function in the four files with neither. Every other one of the 13 is revoked from `public, anon, authenticated` |
| `schema/05_assert.sql:15`, `:2239` | `\set ON_ERROR_STOP on` and `\echo ASSERTIONS_OK` — **psql meta-commands, not SQL.** Verified by grep: these are the only two backslash lines in all four files; `01/03/04` contain zero |
| 64 `insert into` fixture statements | committed rather than rolled back |

`05` is safe today for exactly one reason: `verify-schema.sh:10` concatenates it between
`begin;` and `rollback;`. A migration commits.

T4 (`:178-187`) says the opposite of T2 — `05_assert.sql` "gets a home in CI or
`check-schema-gates.sh`". The plan contradicts itself in the one place where the wrong reading is
destructive. The spine has the same contradiction in the same sentence
(`2026-08-22-append-only-generations-roadmap.md:215-217`: *"The four spec `schema/*.sql` files
become migrations `0027+`. `05_assert.sql` gets a home in CI…"*), so T0 — which corrects the spine —
must correct **this** sentence too, and the plan does not say so.

**Required:** T2 must name the three files it promotes (`01`, `03`, `04`) and state explicitly that
`05_assert.sql` is never a migration. "Without removing anything" must be scoped to those three.

---

### B2 — M4-α is not executable. Five of the six gates reach their database only by `docker exec` into a hardcoded local container name; a throwaway Supabase **project** has no container.

Plan `:64` and `:137-139`: the complete promotion is *"applied to a **throwaway Supabase project**,
with all six gates run against it"*, pointing at the `staging-supabase-project` memory — which names
a **hosted** project (`neeufoxdbgbpkjukzzuc`).

Measured, one per gate:

| Gate | How it reaches Postgres |
|---|---|
| 1 `verify-schema.sh` | `verify-schema.sh:9-12` — `CONTAINER="${PGCONTAINER:-supabase_db_youtube-playlist-summaries-cloud}"`, then `docker exec -i "$CONTAINER" psql`. `PGCONTAINER` re-points to a *different container*, never to a hosted project |
| 2 `mutate-schema.py` | `mutate-schema.py:881-883` copies `verify-schema.sh` into a temp dir and runs the copy (`:807`) — inherits gate 1's transport |
| 3 `check-guard-coverage.py` | `:47` `CONTAINER = "supabase_db_youtube-playlist-summaries-cloud"`; `:203` `["docker","exec","-i",CONTAINER,"psql",…]` |
| 4 `check-sentinel-meanings.py` | `:44`, `:117` — identical |
| 5 `check-vocabulary-collisions.py` | `:47`, `:105` — identical |
| 6 `check-docs.py` | no database — unaffected |

T3's table (`:150-157`) frames the work as changing which **files** each gate reads. That is one of
two independent rewrites; the second — changing how each gate **connects** — is not mentioned
anywhere in the plan. Note `check-anon-exposure.py` already solved this problem in this repo (it
takes `CLAUDE_RO_DATABASE_URL` and has a `--local` flag, `check-anon-exposure.py:36-40`), so the
shape of the fix exists and is simply unbudgeted here.

This CONFIRMS and extends Codex r2's Blocking #1 ("re-point" hides a rewrite): the rewrite is larger
than r2 said, because the transport is a second axis r2 did not name.

---

### B3 — Gate 3 is RED against the schema M4 promotes, *before* any re-pointing — and it is blind to `video_artifact_sources` entirely.

`check-guard-coverage.py:243-270` (`evaluate`) reports `set(guards) - live` as **STALE** and that is
a failure. Six entries in `GUARDS` name objects the current schema does not create:

| `GUARDS` entry | Why it is gone |
|---|---|
| `art_pending_is_leased` (`:70`) | deleted by ADR-0007 — `04_artifacts.sql:121-124` names all three as `⛔ … STOOD HERE … ARE DELETED`. Verified: the string occurs in the schema **only inside comments** |
| `art_pending_has_token` (`:71`) | same |
| `art_pending_has_reserved_at` (`:72`) | same |
| `video_artifacts_inflight_uq` (`:91-93`) | deleted by ADR-0007 — `04_artifacts.sql:269-288` |
| `video_artifacts_workspace_id_video_id_source_generation_id_fkey` (`:141`) | the source FK moved off `video_artifacts` — `04_artifacts.sql:112-117` |
| `art_summary_has_no_source` (`:73`) | classified as a CHECK on `video_artifacts`; it is now a **constraint trigger on `video_artifact_sources`** (`04_artifacts.sql:1149-1151`), which is outside both catalog queries below |

And the enumerated whole excludes the T3 table outright:

```
check-guard-coverage.py:48   TABLES = ("video_artifacts", "video_generations")
check-guard-coverage.py:58   TRIGGER_TABLES = TABLES + ("videos","jobs","workspace_videos","playlists","profiles")
check-guard-coverage.py:174  where conrelid = any (array{TABLES}::regclass[]) and contype = 'c'
check-guard-coverage.py:191  where t.tgrelid = any (array{TRIGGER_TABLES}::regclass[]) and not t.tgisinternal
```

`video_artifact_sources` is in neither tuple. Invisible to the ratchet: `vas_artifact_fk`,
`vas_source_generation_fk` (`04_artifacts.sql:239-243`), and the three triggers
`video_artifact_sources_append_only`, `video_artifact_sources_insert_once`,
`art_summary_has_no_source` (`04_artifacts.sql:1085-1087`, `:1124-1127`, `:1149-1151`).

This is the *exact* failure `check-guard-coverage.py:50-57` records about itself in round 9 —
*"this ratchet enumerated triggers on TWO tables, so it reported ✅ … with a brand-new guard sitting
outside its query"* — committed again for the table ADR-0007's T3 added.

**Why this is Blocking for the plan and not just for the script:** T2's gate is
*"`./scripts/check-schema-gates.sh` green against that project"* (`:139`) and T3 budgets a
**path** change for gate 3 (`:154`: "Today reads `:44` the spec dir | Must read: the migrations").
Neither is achievable, because the broken part is the **inventory**, not the path. A plan whose
central gate is red before the first task and whose author records it as green is the precise shape
of "a green check over the wrong subject" (`CLAUDE.md`).

*Method note:* this is a static determination — the constraint/index names are provably absent from
the DDL, so applying the schema cannot create them. I did not run the ratchet (it needs the docker
stack, which per B2 it can only reach locally); a live run would confirm the count, not the fact.

---

### B4 — Gate 1's assertions require a POPULATED corpus. On an empty throwaway project they either hard-fail or pass vacuously — so M4-α cannot prove what the plan says it proves.

Plan `:67-69` claims M4-α *"proves the DDL executes and the assertions hold"*. Three of `05`'s
assertions read the **live corpus of whatever database they run in**:

```
05_assert.sql:893   create temp table t_real as select workspace_id, video_id from videos limit 1;
05_assert.sql:896   if n <> 1 then raise exception 'ASSERTION FAILED — no real video to test the trigger against';
```
→ against an empty project this **hard-fails**, and the failure has nothing to do with the schema.

```
05_assert.sql:1843  select id, workspace_id into v_pl, v_ws from playlists limit 1;
05_assert.sql:1847  if (select workspace_id from videos where playlist_id=v_pl and video_id='ingestNew') <> v_ws then
```
→ with zero playlists, `v_pl` is NULL, the insert at `:1844-1846` selects zero rows, the comparison
is `NULL <> NULL` = NULL, and `if NULL` is false. The assertion **passes without executing its
subject** — the single most M4-β-relevant assertion in the suite (does an unchanged writer still
ingest a video after the promotion?).

```
05_assert.sql:61-71  -- the backfill assertion
   n_corr_wv  = count of workspace_videos rows whose corrections_hash <> no_corrections_hash()
   n_corr_v   = count(distinct (workspace_id, video_id)) from videos with non-empty corrections
   if n_corr_wv <> n_corr_v then raise 'backfill lost corrections'
```
→ `0 <> 0` is false on an empty project. Vacuous.

Gate 1 passes today only because the local container carries the dev corpus (`05_assert.sql:58`
records `2903 of 2904`). Move it and it silently changes meaning in both directions.

So M4-α is not "zero blast radius, high confidence" — it is **either red for an irrelevant reason or
green for no reason**. The plan's own warning at `:67-69` ("do not read M4-α as a rehearsal that
makes M4-β safe") is directionally right and understates it: M4-α as scoped does not even establish
the first half.

**Required:** either M4-α runs against a project seeded with production-shaped data, or the plan
states which assertions are known-vacuous there and what covers them instead.

---

## High

### H1 — `workspaces` is the ONLY new table with no `revoke all … from anon, authenticated`, and nothing in the plan's gate list can see it.

```
01_workspaces.sql:18  alter table workspaces enable row level security;
01_workspaces.sql:19  alter table workspaces force row level security;
01_workspaces.sql:20  grant select, insert, update, delete on workspaces to service_role;
01_workspaces.sql:21  grant select on workspaces to authenticated, anon;
01_workspaces.sql:22  create policy workspaces_owner_read on workspaces for select using (owner_id = auth.uid());
```

There is no `revoke`. Its four siblings all have one:

| Table | Revoke |
|---|---|
| `workspace_videos` | `03_generations.sql:68` |
| `video_generations` | `03_generations.sql:562` |
| `video_artifact_sources` | `04_artifacts.sql:257` |
| `video_artifacts` | `04_artifacts.sql:655` |

The spec states the hazard itself, as a measurement, at `04_artifacts.sql:649-654`:

> ⚠ ROUND 6 H4 — REVOKE FIRST. MEASURED: `anon` TRUNCATEd this table to 0 rows. `pg_default_acl`
> carries `anon=Dxtm/postgres` for every table `postgres` creates in `public` (D=TRUNCATE,
> x=REFERENCES, t=TRIGGER) … TRUNCATE fires neither RLS nor a ROW trigger.

`grant select` is additive and narrows nothing (same comment). So after M4-β, `anon` holds
`TRUNCATE`, `REFERENCES` and `TRIGGER` on `workspaces` in production. This is shape #10 — a fix
applied at four sites with an identical fifth — for the ninth recorded time in this spec, and the
plan promotes it verbatim under *"without removing anything"* (`:121`).

**What makes it High rather than Medium: nothing in M4 would notice.**

- `05_assert.sql:754-762` asserts `anon` cannot `truncate video_artifacts`. There is **no equivalent
  assertion for `workspaces`** — grep confirms `truncate` appears once in the whole file.
- `scripts/check-anon-exposure.py:68-73` — the ratchet purpose-built for this class, defaulting to
  **prod** — hardcodes `MONEY_TABLES = ("spend_ledger","ledger_audit","serve_owner_budget",
  "serve_model_charge","guardrail_config")`. **None of M4's five new tables is in it**, including
  `video_artifacts`, the manifest of paid content. RULE 2's baseline can therefore not grow when
  five new tables arrive.
- **The plan's milestone gate list (`:248-250`) does not name `check-anon-exposure.py` at all** — nor
  `check-producer-enumeration.py`, which is directly relevant (M4 makes `videos.workspace_id` and
  `jobs.workspace_id` guarded values with exactly one producer each, `03_generations.sql:198-215`).

**Required:** add the `revoke` to `workspaces`; extend `MONEY_TABLES` to cover the new manifest
tables *before* M4-β so the baseline is set against the pre-M4 world; and add
`check-anon-exposure.py --local` and `--prod` to the plan's gate list as M4-α and M4-β gates
respectively.

*(Exploitability of the TRUNCATE specifically is bounded — `workspaces` is FK-referenced by
`playlists`, `videos`, `jobs` and `workspace_videos`, so a bare `TRUNCATE` errors and `CASCADE`
needs TRUNCATE on `workspace_videos`, which is revoked. The `TRIGGER` and `REFERENCES` bits are not
bounded that way. I did not attempt to build an exploit — **UNVERIFIED** beyond the grant state.)*

---

### H2 — Codex r2's High on lock strategy survived into v3 UNADDRESSED, and the plan still never states the consequence: the app and worker stall for the whole M4-β window.

Codex r2 (`:9`) said *"Either write quiescence or a re-check is too weak"* and asked for a single
production strategy. Plan `:110-114` is **unchanged from v2**:

> …and either write quiescence or a re-check inside the same transaction.

CONFIRM. And the physical fact neither round states: `alter table … add column`, `update …`,
`alter … set not null` and `add constraint` each take **ACCESS EXCLUSIVE**, which blocks `SELECT`,
not merely writes. Held to commit across `playlists`, `videos` **and** `jobs`
(`01_workspaces.sql:36-51`), that is a full read-and-write outage of the queue and the app for the
duration — not a write-quiescence question.

The interaction the plan gets exactly backwards: `lock_timeout` (`:113`, `:197`) does not protect
the app. It protects the *migration* from waiting, by aborting it. Combined with v3's mandatory
single transaction (`:124-135`), the realistic outcome is repeated aborted attempts against a live
worker queue, and the plan specifies no abort/retry/backoff protocol and no upper bound on the
window.

**Required:** pick one — (a) stop the worker and put the app in maintenance for a measured window,
or (b) prove the migration completes inside a stated `lock_timeout` against T1's measured row
counts. "Either/or" is not a strategy an agent can execute.

---

### H3 — T1's falsifier list misses the one that silently destroys user content, and the assertion that would catch it counts instead of comparing.

T1 (`:100-109`) asks for orphaned `videos`/`playlists`/`jobs` — i.e. falsifiers for the migration
**aborting**. It asks for no falsifier for the migration **succeeding while losing data**.

The seed picks one corrections value per `(workspace, video)`:

```
03_generations.sql:89-95
insert into workspace_videos (workspace_id, video_id, corrections, corrections_hash)
  select distinct on (workspace_id, video_id) …
   from videos
  order by workspace_id, video_id, (coalesce(data->>'corrections','') <> '') desc;
```

`distinct on` resolves *has-corrections vs hasn't*. It does **not** resolve *two different
non-empty corrections*: the same video in two playlists is two `videos` rows
(`03_generations.sql:84-86` says so), and if both carry corrections, one set is silently discarded.
This is user content, and after M2 slice A it is content a paid Gemini call produced
(`0026_record_correction_spend.sql`).

The suite cannot see it, because it compares **counts**, not values:

```
05_assert.sql:65-68
  select count(*) into n_corr_wv from workspace_videos where corrections_hash <> no_corrections_hash();
  select count(distinct (workspace_id, video_id)) into n_corr_v from videos where …
  if n_corr_wv <> n_corr_v then raise 'backfill lost corrections'
```

Both sides count *videos that have some corrections*. Picking the wrong one of two leaves both
counts identical. And `resolve_workspace_from_playlist`'s runtime half has the same bias by design
(`03_generations.sql:186` `on conflict … do nothing`).

**Required T1 measurement (read-only, one query):** how many `(workspace_id, video_id)` groups in
prod have more than one distinct non-empty `data->>'corrections'`? If it is zero, the risk is closed
by measurement. If it is not, M4-β destroys paid content and the plan currently has no gate that
would report it.

---

## Medium

### M1 — T0's gate cannot fail for T0's subject.

Plan `:92`: *"**Gate:** `check-docs` 0. No code."*

`check-docs.py` reads `docs/roadmap-to-launch.md` for one thing — the *"Triage the N spec docs"*
advisory count (`check-docs.py:448-471`). It does not read
`2026-08-22-append-only-generations-roadmap.md` at all. The only script that opens that file is
`check-anchors.py`, and only for its anchor header (verified: `grep -rln
"append-only-generations-roadmap" scripts/ .github/` → `scripts/check-anchors.py` only).

So `check-docs` returns 0 whether or not the M4 sentence at
`2026-08-22-append-only-generations-roadmap.md:215-217` is corrected. **State the observation that
would make this gate FAIL: there isn't one.** Per `CLAUDE.md`, rename it or give it a falsifier —
e.g. a grep asserting the string *"lands inert"* no longer appears in that file.

### M2 — T7's gate is a decision wearing a checkbox, and the plan says so in the same paragraph.

Plan `:226-228`: the gate is that #26's row *"states the trigger in terms of an observable … and, if
it is cheap, a check script that greps for exactly that."* The conditional makes the only mechanical
half optional, leaving "a backlog row contains a sentence" — which no script reads. The next line
("A trigger nobody can observe is a decision wearing a checkbox") is the rule this gate breaks.

Make the script mandatory. It is one line, and I ran it: `grep -rlE "record_artifact" --include=*.ts
--include=*.tsx --include=*.sql .` returns `tests/lib/blob-addressing-caller-contract.test.ts` plus
the three spec SQL files, and **zero** files under `lib/ app/ worker/ components/`.

### M3 — CONFIRM Codex r2's Medium on T6, and here is the artifact it should require.

r2 (`:14`) said reading `lib/html-doc/serve-doc.ts` proves the serve path calls `reserve_serve_model`
(`serve-doc.ts:122-127`, verified) and not `record_artifact`, but does not prove "no caller can
reach `record_artifact`" repo-wide. Confirmed, and v3's T6 (`:215-218`) still specifies only *"by
reading the live serve path"*.

The repo-wide check is cheap and currently green — see M2's grep. It should be **in** T6 as the
falsifier, phrased so it fails the moment a `.ts`/`.tsx` file under `lib/ app/ worker/ components/`
names `record_artifact`.

### M4 — M4 introduces production's first dependency on pgcrypto's `digest`, on the ingest path and on a post-payment write. T1 measures no environment facts.

```
03_generations.sql:37-45
create function corrections_hash_of(p_corrections text) returns text
  language sql immutable
  set search_path = public, extensions
  as $$ … encode(digest(normalize(…, NFC) || E'\n', 'sha256'), 'hex') … $$;
```

Reached from `resolve_workspace_from_playlist` on **every** `insert into videos`
(`03_generations.sql:185`) — i.e. `claim_video_slot` (`0023:87`), `persist_summary`'s ingest
(`0009:94`), `0007:35` — and from `sync_corrections_to_workspace_video`
(`03_generations.sql:232`) on the corrections write, which in M2 slice A happens *after* a paid
Gemini call.

Verified: `grep -rn "pgcrypto|digest\(|extensions\." supabase/migrations/*.sql` returns **nothing**.
No shipped migration installs pgcrypto or calls `digest`. M4 is the first. If prod's pgcrypto is not
resolvable at `extensions.digest`, ingest stops and paid corrections raise after payment.

Hosted Supabase installs pgcrypto into `extensions` by default, so the probability is low — but T1's
job is measuring, and the plan's T1 measures only row counts. Add: `select extname, extnamespace::regnamespace
from pg_extension` and the server version (`normalize(…, NFC)` needs PG13+), both read-only.

### M5 — the plan contradicts itself on whether M4 writes to production.

`:117` — *"⚠ **Read-only. No writes to prod in M4 at all.**"* (under T1, but stated as a rule about
M4, not about T1)
`:65` — M4-β is *"The same migrations, applied to **production**. … Every row of `playlists`,
`videos`, `jobs`."*
`:252` — *"Applying M4b to production is a SECOND human gate."*

Scope the `:117` warning to T1 explicitly, or an agent reading top-down stops at M4-α.

---

## Low

### L1 — REFUTE, in advance, the "can this run in one transaction?" worry, for `01/03/04`.

I checked for every statement class Postgres refuses inside a transaction block. `01`, `03` and `04`
contain **no** `CREATE INDEX CONCURRENTLY`, no `ALTER TYPE … ADD VALUE`, no `VACUUM`, no
`CREATE DATABASE`, no `ALTER SYSTEM`, no `REINDEX`, no explicit `begin`/`commit`. The one `create
type` (`03_generations.sql:264`) is transactional and its first use is in the same transaction
(`:270`), which Postgres permits. `verify-schema.sh:10` already runs all four in one transaction
daily, which is the empirical proof.

So v3's "ONE FILE, ONE TRANSACTION" is achievable for the three files that should be migrations. The
only transactionality blocker in the set is `05_assert.sql`'s two psql meta-commands — see B1.

*One thing the plan asserts without citation:* that the Supabase migration runner gives one file one
transaction. `tests/integration/global-setup.ts:46` shells out to `npx supabase migration up`, which
is the runner in question. I did not verify its transaction semantics — **UNVERIFIED**. Given the
whole of v3's central Blocking rests on it, the plan should carry a one-line executable proof
(deliberately fail a statement at the end of a throwaway migration and observe whether the earlier
statements survive) rather than the assertion.

### L2 — the same stale-inventory class as B3, in gate 4.

`check-sentinel-meanings.py:48` — `TABLES` includes `workspaces` and `workspace_videos` but **not**
`video_artifact_sources`. And `MEANINGS` (`:56`) still carries
`("video_artifacts", "source_generation_id")`, a column ADR-0007 deleted
(`04_artifacts.sql:50-56`). Whether that makes gate 4 red or merely blind depends on how the script
treats a `MEANINGS` key with no live column — **UNVERIFIED**, needs a live run. Either way T3's
"re-point" budget is wrong for this gate too.

### L3 — the plan's `[VERIFIED]` tags: I re-checked twelve; all twelve resolve.

Including the three round-2 corrected ones: `check-vocabulary-collisions.py:46` is `SCHEMA = …` and
`:96` is `for f in sorted(SCHEMA.glob("0*.sql")):` ✓; `check-guard-coverage.py:44` ✓;
`check-sentinel-meanings.py:43` ✓; `0009…:26-27` is the `insert into jobs` with no `workspace_id` ✓;
`01_workspaces.sql:50-51` ✓; `03_generations.sql:96-97` ✓, `:89` ✓, `:152-215` + `:253-262` = exactly
9 triggers ✓; `04_artifacts.sql:269-288` ✓, `:354-360` ✓, `:628-633` ✓;
`05_assert.sql:893-911` ✓ and `:1843-1859` ✓; `check-schema-gates.sh:14-16` ✓.

v3's citation hygiene is good. The defects are elsewhere.

### L4 — the plan declares a syntax it does not use, and a live ratchet fails closed on that.

`:7` — *"Steps use checkbox (`- [ ]`) syntax."* The file contains **zero** `- [ ]` lines.
`scripts/check-plan-progress.py:20-23` — *"FAILS CLOSED. A missing plan, or a plan that parses to
zero steps, BLOCKS with 'TREAT THIS AS NOT RUN'"*. Cosmetic until the plan is executed under the
sentinel, at which point it is a self-inflicted block.

---

## Disposition of the prior rounds

| Round | Finding | This round |
|---|---|---|
| r1 B1-B4, H1-H3, M1-M2, L1 | the M4a/M4b split | **CONFIRM as resolved.** v3's "you can only split the environments" is correct and I found no way to reintroduce a split |
| r2 B1 | "re-point" hides a rewrite | **CONFIRM and EXTEND** — see B2. The transport axis is a second rewrite r2 did not name |
| r2 B2 | committed-file chain → enqueue outage | **CONFIRM as resolved** by v3's `:124-135`. Independently verified at `0009…:26-27` and `03_generations.sql:210-215` |
| r2 H1 | lock strategy too weak | **CONFIRM — NOT ADDRESSED in v3.** See H2 |
| r2 H2 | `serve_model_charge` allowlist deferral | **CONFIRM as resolved** — `:174-176` now requires an artifact with no third option |
| r2 M1 | T6 measurement too narrow | **CONFIRM — NOT ADDRESSED in v3.** See M3 |
| r2 M2 | `check-vocabulary-collisions.py:44,88` wrong | **CONFIRM as resolved** — `:46`/`:96` verified correct |
| r2 L1 | M4-α buys little over `verify-schema.sh` | **STRENGTHEN to Blocking** — see B2 and B4. It buys *less*, not little |

## On the money question specifically

Asked directly, and the answer is narrower than the plan's T6 section implies:

- `record_artifact` is revoked from `public, anon, authenticated` and granted only to `service_role`
  (`04_artifacts.sql:628-633`), and **no `.ts`/`.tsx` file in the repo names it** (M2's grep). M4
  ships no path to it. The plan is right that #26 is armed, not fired.
- `serve_model_charge`'s `max_serve_attempts = 5` bound (`0012:21`, `:59-65`) and the `doc_key`
  playlist-scoping (`0020:213`) are untouched by M4 — no code change reaches them.
- **The baseline the plan never states:** `video_artifacts_inflight_uq` has never existed in
  production. `04_artifacts.sql:276-281`'s "`paid_model_rows_in_one_slot` goes 1 → 2" is a
  regression relative to the *spec's earlier design*, not relative to prod, where one video in N
  playlists already holds N independent leases. M4 neither improves nor worsens it. T6 (`:209-218`)
  reads as though a live bound is at stake; it is not, and saying so plainly is cheaper than the
  measurement it currently asks for.
- The genuine money exposures M4 *does* open are H3 (paid corrections silently discarded by the
  backfill, with no gate that compares values) and M4 (a post-payment write path acquiring a new
  extension dependency). Neither appears in the plan.

---

## Verdict

**NOT CONVERGED.**

4 Blocking · 3 High · 5 Medium · 4 Low.

**The single most important finding is B4** — M4-α, the entire safety argument for touching
production, runs three of its most production-relevant assertions against a database that will not
have the rows they need. On an empty throwaway project gate 1 either dies at `05_assert.sql:896`
for a reason unrelated to the schema, or reports green on `:1843-1859` and `:61-71` without
executing their subject. The plan's one-line disclaimer at `:67-69` says M4-α "proves the DDL
executes and the assertions hold"; measured, it proves neither. Every other finding here is a defect
in a step; this one is a defect in the step that exists to make the irreversible step safe.
