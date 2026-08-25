# M4 plan (v4) — round 4, CLAUDE half of the dual adversarial review

**Target:** `docs/superpowers/plans/2026-08-25-m4-promote-the-schema.md` (v4, with the round-4 Codex
fold-in at `3f634bb`)
**Branch:** `docs/m4-plan` · **Date:** 2026-08-25
**Partner this round:** `plan-m4-promote-schema-r4-codex.md` (0B/0H/1M/2L, **CONVERGED**)
**Prior rounds read in full:** r1-codex (4B/3H/2M/1L), r2-codex (2B/2H/2M/1L), r3-claude (4B/3H/5M/4L).

**Angles, chosen to not overlap r4-codex** (which took the measurement's arithmetic and the lock
inference): rollback and recovery · the integration/E2E suites · the second home for `corrections` ·
what the plan does not mention at all · re-verification of `[VERIFIED]` tags and T1.

Every claim below is cited `file:line`, EXECUTED, or labelled **UNVERIFIED**. Where I formed a
hypothesis and the measurement killed it, the refutation is recorded (L2) rather than dropped —
this is round four, and a round that reports only its hits is not evidence about the plan.

**What I executed** (all read-only): the prod database as `claude_ro` via Node `pg` with the repo's
pinned CA (`tests/e2e/supabase-prod-ca-2021.crt`, `rejectUnauthorized: true` — the URL's
`?sslmode=require` was stripped first because in `pg` 8.23 it silently overrides the `ssl` object);
the local container via `docker exec psql`; `scripts/check-anon-exposure.py` at both `--local` and
`--prod`; and a byte-level read of the pinned Supabase CLI binary (2.115.0).

---

## Blocking

### B1 — There is no rollback. The "one transaction" property is real (I verified it) and it covers the wrong failure.

The plan has no rollback, recovery, or backup section — not a heading, not a sentence. Its entire
recovery argument is T2's *"commit together or not at all"* (`:118-120`).

I verified that property rather than assuming it, because r3 L1 left it **UNVERIFIED** and v4 did
not close it. It holds, at the wire level, for the pinned CLI:

| Evidence (Supabase CLI 2.115.0, `@supabase/cli-darwin-x64/bin/supabase`) | What it establishes |
|---|---|
| `transactionMode` defaults to `"transactional"`; it is `"none"` only when the file's first line is exactly `-- pg-delta: transaction=false` | a plain migration file is transactional |
| the batch is split only for `CREATE INDEX CONCURRENTLY` / `REINDEX … CONCURRENTLY` / `VACUUM` / `ALTER SYSTEM` / `CLUSTER`, or an explicit `BEGIN`/`COMMIT`/`ABORT` | `01/03/04` contain none of these (r3 L1, re-checked) |
| `class bAH.submit()` issues `parse`/`bind`/`describe`/`execute` for **every** statement and exactly **one** `sync()` | a single extended-protocol pipeline = one implicit transaction; any error discards all of it |
| the `INSERT INTO supabase_migrations.schema_migrations(version, name, statements)` is **pushed into the same batch** | there is no "applied but unrecorded" state to reconcile |

So the half-applied case is genuinely closed. **The case the plan needs is the other one**, and the
plan does not name it: *0027 applies cleanly, and is then found wrong.*

That is not hypothetical for this schema. Its own comment records the outcome, twice, from executing it:

> `03_generations.sql:98-107` — *"⟳ ROUND 8 B3 — THE MIGRATION HAD NO PRODUCER FOR EITHER VALUE IT
> MADE MANDATORY, so after it ran, NOTHING COULD INGEST A NEW VIDEO. MEASURED … `[23502] null value
> in column "workspace_id"` … `[23503] … violates foreign key constraint` … Two independent
> breakages, one behind the other."*

Both were found by execution, not review, and both leave production unable to ingest. There is no
tooling path back. Measured: `npx supabase migration --help` lists exactly `list`, `new`, `repair`,
`squash`, `up`. **There is no `down`.** `repair` edits the history table, not the schema. A reversal
is a hand-written `0028` that nobody has written, reviewed, or gated — while the app is down.

**And the plan is one step away from being able to make this cheap, which is why this is Blocking
rather than a note.** Every object M4 creates is *derived*: `workspaces` from `profiles`
(`01_workspaces.sql:33`), the three `workspace_id` columns from `playlists`/`videos`
(`01:36-48`), `workspace_videos` from `videos.data` (`03:89-95`), and `video_generations` /
`video_artifacts` / `video_artifact_sources` are empty because M4 ships no caller (plan `:50-51`).
So a down-migration at M4 **loses no user-authored fact** — it is a pure `drop`. That is true on the
day M4-β lands and stops being true at M5, the moment `record_artifact` has a caller.

**Required:** a rollback task that (a) ships `0028_rollback_stable_blob_addressing.sql` alongside
0027 in the same PR, (b) states the falsifiable property that makes it lossless — *"every column and
row 0027 creates is a function of state that predates it; nothing in `lib/ app/ worker/` writes any
of it"* — and (c) records that this property expires at M5. T7's grep is already the command for (b).

---

### B2 — The milestone gate list contains no behavioural test suite, for a migration that attaches nine triggers to live tables.

Plan `:193-201` enumerates the gates: the six schema gates, `check-anon-exposure`, seven doc
ratchets, and dual review. **`npm run test:integration` is not among them. Neither is `npm test` nor
`test:e2e`.** The words "integration", "e2e" and "test suite" do not appear anywhere in the plan.

What that leaves uncovered:

- 0027 attaches nine triggers to `profiles`, `playlists`, `videos` and `jobs`
  (`03_generations.sql:152-154`, `:198-215`, `:253-262`) and makes three columns `NOT NULL`
  (`01_workspaces.sql:38`, `:43`, `:48`). Measured in prod today, `videos` has **one** trigger
  (`trg_videos_updated_at`), `profiles` has one, and `playlists` and `jobs` have **none**. M4 takes
  that from 2 triggers to 11 across the four tables.
- Those triggers sit on the insert path of every RPC the app and worker use — `claim_video_slot`
  (`0023:87`), `persist_summary` (`0009:94`), `reserve_video_slot` (`0009:94-96`), `enqueue_job`
  (`0009:26-27`), and the direct PostgREST writes at `supabase-metadata-store.ts:183-191` and
  `summary-handler.ts:132-134`.
- `tests/integration/` is the only suite that exercises any of that. It is 60+ files and is **not in
  CI** — `.github/workflows/ci.yml:6-10` says so explicitly (*"NOT here: `npm run test:integration`
  needs a live Supabase stack"*), and `docs/dev-process.md` repeats it under *"Not yet in CI"*.

So after 0027 the repo has **no gate, anywhere, that would notice the triggers breaking an existing
write path** — and the schema's own comments record that exact failure happening twice (B1). The
six schema gates test the schema against itself; they do not call an application RPC.

*What a green suite would and would not prove:* I did not run `test:integration` against 0027 (that
is M4-α, and applying DDL to the shared local stack is outside a reviewer's remit —
`an-instrument-that-edits-the-repo-corrupts-its-peers`). Statically I found no test that must fail:
`jobs` has an FK to `playlists` (`0009:5-6`) so the derive trigger always finds a parent; `profiles`
rows are created by `handle_new_user` (`0003:2-11`) so `profiles_ensure_workspace_trg` chains
correctly; and prod's `postgres` role carries `rolbypassrls = true` (measured), so the
`SECURITY DEFINER` trigger's write into `force row level security`-protected `workspace_videos`
is not blocked. **That is a prediction, not a result** — which is the point: nothing in the plan
converts it into one.

**Required:** add `npm run test:integration` (and, if the cloud e2e can be run, `test:e2e:cloud`) to
the milestone gate list as an M4-α gate, with the run recorded against a named commit. Per
`CLAUDE.md`, if the stack is unavailable the gate must exit non-zero saying *treat this as NOT RUN*.

---

## High

### H1 — Committing 0027 (T2) **is** M4-α, for every developer, unseeded — so the plan's order T2 → T3 → T4 → T5 → T6 is fiction.

`tests/integration/global-setup.ts:43-50`:

```ts
export default function globalSetup(): void {
  stdout = execFileSync('npx', ['supabase', 'migration', 'up'], { … });
```

with the header stating why (`:16-17`): *"A migration is precisely when the suite matters most, and
precisely when it silently stopped applying. Hence: apply first, every run."* It refuses to run
rather than skip (`:51-59`).

The consequence for this plan: **the moment `supabase/migrations/0027_stable_blob_addressing.sql`
exists on the branch, the next `npm run test:integration` on any machine applies the whole of M4 to
that machine's stack.** Not at T6. Not gated. Not seeded.

The plan's Order block (`:186`) reads `T2 ─▶ T3 ─▶ T4 ─▶ T5 ─▶ M4-α`, and T6 defines M4-α as *"apply
`0027` to the **local** Supabase stack, **seeded per T4**"* (`:162`). But T4's seeding decision is
still open — it is one of the plan's own Open Questions (`:209`, *"T4's answer depends on whether CI
gets a Postgres"*) — and r3 B4 established that three of `05_assert.sql`'s most M4-β-relevant
assertions are either hard-red or vacuous on an unseeded database (`05_assert.sql:896`, `:1843-1859`,
`:61-71`). So the first apply that actually happens is the one the plan has no design for.

This is not the same finding as r3 B4. r3 asked *what does M4-α prove on an unseeded database*; this
is *M4-α happens before you decide, whether or not you schedule it.*

**Required:** T2 must say that writing the file starts M4-α, and either move T4's seeding decision
before T2 or state explicitly that the auto-applied local run is unseeded and what it is allowed to
conclude.

---

### H2 — The production default ACL is `arwdDxtm`, not `Dxtm`. The local stack says `Dxtm`, the spec being promoted says `Dxtm`, and M4-α cannot tell the difference.

r3 H1's fix — `revoke all on workspaces from anon, authenticated`, now T2 (`:120-123`) — is
**correct and sufficient**, and I confirm it. The finding is about the *measurement it rests on*,
which is being promoted verbatim into a production migration.

`04_artifacts.sql:649-654`, quoted by r3 H1 and carried unchanged into 0027:

> ⚠ ROUND 6 H4 — REVOKE FIRST. MEASURED: `anon` TRUNCATEd this table to 0 rows. `pg_default_acl`
> carries `anon=Dxtm/postgres` for every table `postgres` creates in `public` (D=TRUNCATE,
> x=REFERENCES, t=TRIGGER)

Measured today, `select defaclrole::regrole, defaclnamespace::regnamespace, defaclobjtype,
defaclacl from pg_default_acl`:

| Environment | `postgres` / `public` / relations |
|---|---|
| **LOCAL** `supabase_db_youtube-playlist-summaries-cloud` | `anon=Dxtm/postgres` · `authenticated=Dxtm/postgres` · `service_role=Dxtm/postgres` |
| **PRODUCTION** `uykwcybxqgewmbltroxf` (read as `claude_ro`) | `anon=arwdDxtm/postgres` · `authenticated=arwdDxtm/postgres` · `service_role=arwdDxtm/postgres` · `claude_ro=r/postgres` |

The prod default also carries **a** (INSERT), **r** (SELECT), **w** (UPDATE) and **d** (DELETE). The
sentence being shipped states the local number as the production fact. Two consequences:

1. **M4-α cannot falsify a missing revoke at prod's severity.** The plan adds
   `check-anon-exposure.py --local` as the M4-α gate and `--prod` at M4-β (`:138-139`) as if they
   were one check at two times. They are not — the script's own docstring already records the class
   (`:27-33`: *"The local stack and production DISAGREE about this … definer + anon-executable local
   5 prod 10"*), and I re-measured it: `--local` reports **5** anon-executable definer functions,
   `--prod` reports **10**, from the same 12. The default-ACL gap is a second, unrecorded instance.
2. **T3's wording may exclude the very table the finding was about.** `:138` says *"extend its
   `MONEY_TABLES` to the new **manifest** tables"*. `workspaces` is not a manifest table — it is the
   tenancy root — and it is the **only** one of the five new tables with no revoke in the spec
   (`01_workspaces.sql:18-22`, against `03:68`, `03:562`, `04:257`, `04:655`). Read literally, the
   instruction adds the four that are already safe and omits the one that is not.

*Bounding the exposure honestly:* `workspaces` carries `enable`+`force row level security` with a
SELECT-only policy (`01:18-22`), so RLS blocks anon INSERT/UPDATE/DELETE/SELECT at the row level
regardless. TRUNCATE bypasses RLS, and a bare TRUNCATE errors on the FK references from
`playlists`/`videos`/`jobs`/`workspace_videos`. I did not build an exploit — **UNVERIFIED beyond the
grant state.** The severity is High because of what the *gate* can see, not what an attacker can do.

*One thing I checked and can CONFIRM works:* `MONEY_TABLES` feeds RULE 2, which measures only
`has_table_privilege(…, 'TRUNCATE')` (`check-anon-exposure.py:186-191`). That is nonetheless a sound
proxy for "no revoke was applied", because all eight verbs arrive together from `pg_default_acl` and
`revoke all` removes them together — in **both** environments. And setting the baseline pre-M4-β
works mechanically: `c.relname = any(…)` returns no rows for tables that do not exist yet, so the
count stays 5 and the gate passes, then goes to 6+ if any new table ships unrevoked. The plan's
instruction is right; only its table list is wrong.

**Required:** name all five new tables (including `workspaces`); correct the `Dxtm` sentence in
`04_artifacts.sql` before it becomes a migration; and state that `--local` is the weaker
measurement, so `--prod` at M4-β is the gate and `--local` is a smoke test.

---

## Medium

### M1 — T4 gives `05_assert.sql` a home the file's own comment says it cannot have, and its first failure will be a false accusation of data loss.

T4 (`:148-149`): *"whichever home is chosen, `./scripts/check-schema-gates.sh` runs it"* — i.e.
repeatedly, on demand, against whatever state the local database is in.

The backfill assertion's precondition, in the file, three lines above the assertion
(`05_assert.sql:56-58`):

> The subject here is the MIGRATION'S OUTPUT, **so nothing may have touched the table yet.**

And the assertion (`05_assert.sql:65-70`):

```sql
select count(*) into n_corr_wv from workspace_videos where corrections_hash <> no_corrections_hash();
select count(distinct (workspace_id, video_id)) into n_corr_v
  from videos where coalesce(data->>'corrections','') <> '';
if n_corr_wv <> n_corr_v then
  raise exception 'ASSERTION FAILED — backfill lost corrections: wv has %, videos has %', …
```

The two sides diverge permanently after any ordinary deletion, because the FK runs the other way:
`videos` is the **child** of `workspace_videos` (`03_generations.sql:96-97`), and
`workspace_videos` cascades only from `workspaces` (`03:49`). So deleting a playlist —
`deletePlaylist` at `lib/storage/supabase/supabase-metadata-store.ts:297-307`, which cascades to
`videos` via `0001_core_schema.sql:31` — removes the `videos` rows and leaves the
`workspace_videos` rows. `n_corr_wv > n_corr_v`, and the gate raises **"backfill lost corrections"**
about a backfill that ran correctly weeks earlier.

`check-schema-gates.sh:12-16` already records that `05` cannot run standalone. T4 is asking for a
third mode the file was not written for.

**Required:** T4 must state which assertions are safe to re-run outside the migration transaction,
or scope the re-runnable home to those. This is the same question r3 B4 asked about an *empty*
database; the answer has to cover a *drifted* one too.

### M2 — The deletion asymmetry is a live behaviour change with no caller, and it silently resurrects paid corrections.

Same mechanism as M1, different consequence. After M4-β:

1. A user deletes a playlist. The `videos` rows go; the `workspace_videos` rows — including
   `corrections`, which since M2 slice A is content a **paid** Gemini call produced
   (`0026_record_correction_spend.sql`) — survive, unreferenced and unreachable by any query the app
   makes.
2. The same video is later ingested into any playlist in that workspace. The derive trigger runs
   `insert into public.workspace_videos … on conflict (workspace_id, video_id) do nothing`
   (`03_generations.sql:180-188`), finds the orphan, and keeps it. The user's *old* corrections are
   silently reattached to a video they just re-added.

The plan's central claim about blast radius is that M4 has *"No application caller"* (`:50-51`).
That is true and it is not the property that matters — which is the plan's own argument, made in its
own §1 about the word "inert" (`:20-24`). The DDL alone changes what `DELETE` and re-ingest mean on
a paid-content path, and no gate in the plan's list compares corrections *values* across that
sequence (r3 H3 established that `05`'s assertion compares counts).

I am flagging this as **transitional vs structural**: the shared-body semantics are ADR-0006/0007's,
accepted at M3, and I am not re-litigating them. What is M4's is that this behaviour arrives with
the migration, unmentioned, on the paid path.

### M3 — The plan never names the command that applies 0027 to production, and the atomicity it depends on is a property of that command, not of SQL.

`supabase migration up` is documented by the CLI as *"Apply pending migrations to **local**
database"*. The repo's production path is different: `docs/deploy.md:30-31` —
*"`supabase login` → `supabase link --project-ref <ref>` → **`supabase db push --dry-run`** (read it)
→ `supabase db push`"* — and `docs/roadmap-to-launch.md:162` records the last prod apply as
`supabase db push --linked`.

T6 says only *"the same migration against production"* (`:164`). B1's verification of one-file =
one-transaction was done against the CLI's migration apply path; **`psql -f 0027.sql` without
`--single-transaction`, or a paste into the Supabase dashboard SQL editor, does not have those
semantics** — and both are natural things to reach for on a hosted project at 2am. The plan's single
strongest safety property is therefore conditional on a command it never writes down.

**Required:** T6 names the exact command and the CLI version, and states that the atomicity claim is
void for any other apply method.

### M4 — T1's pgcrypto query answers with a count where the namespace is the load-bearing fact, and cannot fail if the answer is wrong.

`docs/superpowers/specs/m4/t1-blast-radius.sql:47-52`:

```sql
select 'pgcrypto_installed=' || (select count(*) from pg_extension where extname='pgcrypto')::text
    || ' digest_callable='  || (select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace
                                 where p.proname='digest')::text as pgcrypto;
```

`n` is joined and never used. The query counts `digest` functions in **any** schema and would print
`digest_callable=2` identically whether pgcrypto sits somewhere resolvable or somewhere it is not.

The namespace is the whole question, and the schema says so in its own voice
(`03_generations.sql:30-35`): *"`digest` is pgcrypto's and Supabase installs pgcrypto into the
`extensions` schema, NOT `public` — so every unqualified name here is a latent version of the same
bug."* `corrections_hash_of` resolves it through `set search_path = public, extensions`
(`03:39`), and that function is on the ingest path of every `insert into videos` (`03:185`) and on
the post-payment corrections write (`03:232`). r3 M4 asked for exactly this —
*"Add: `select extname, extnamespace::regnamespace from pg_extension`"* — and got a count.

I ran the query r3 asked for, against prod: **`pgcrypto` is in `extensions`, and both `digest`
functions are in `extensions`.** So the answer is fine and the risk is closed by measurement. The
check is not: per `CLAUDE.md`, state the observation that would make it FAIL, and for this query
there isn't one.

**Required:** replace the count with the namespace, and assert it — `pgcrypto` in a schema that is
not on `corrections_hash_of`'s pinned `search_path` must make T1 red.

---

## Low

### L1 — r3 L1's UNVERIFIED premise is now VERIFIED, and it should be recorded in the plan rather than re-derived by round 5.

r3 L1 flagged that *"the Supabase migration runner gives one file one transaction"* was asserted
without citation and asked for an executable proof; v4 did not add one, and r4-codex did not touch
it. The evidence is in B1's table. Worth folding into T2 as a `[VERIFIED: supabase CLI 2.115.0,
single-`sync()` pipeline]` tag with the version pinned — the guarantee is a property of the binary,
so it needs the version the way a manual check needs a build (`CLAUDE.md`, Gates).

### L2 — Four hypotheses I formed and the measurement killed. Recorded so round 5 does not pay for them again.

| Hypothesis | Refuted by |
|---|---|
| Hosted `postgres` is not a superuser, so the `SECURITY DEFINER` trigger's write into `force row level security` `workspace_videos` would be denied in prod but not locally | prod `postgres`: `rolsuper=false`, **`rolbypassrls=true`**. Local: identical. No divergence |
| Prod and local Postgres differ enough for M4-α to be the wrong rehearsal | both are **17.6**. `normalize(…, NFC)` needs PG13+; satisfied everywhere |
| `check-anon-exposure.py --local` is red before M4 starts (its docstring says local is 4/5 money tables against a baseline of 5, and the script fails on a count *below* baseline too, `:163-169`) | **Ran it.** `--local` exit 0, 5/5. `--prod` exit 0, 5/5. The docstring's local figure is stale; the gate is green |
| `sync_corrections_to_workspace_video` (`03:225-236`) fails silently open when its `UPDATE` matches no row | it cannot: `videos_workspace_video_fk` (`03:96-97`) makes the `workspace_videos` row a mandatory parent of the `videos` row being updated |
| Some `SECURITY DEFINER` function in 01/03/04 lacks a revoke, so `check-anon-exposure` RULE 1a goes red at M4-α | enumerated all 14 functions across the three files: **14/14 revoked**, 11 of them `security definer`. RULE 1a stays green. (This matters: it is the live-database cover for the `pg_proc` sweep assertion that lives in `05_assert.sql`, which T4 removes from the migration path) |
| Trigger-name ordering on `videos` collides — `trg_videos_updated_at` (BEFORE UPDATE, `0015`) vs `videos_resolve_workspace_upd_trg` | both BEFORE ROW, alphabetical order puts `trg_…` first, and they write disjoint columns |

### L3 — Production already contains an arbitrary-SQL executor, which narrows (does not refute) r3 B1's framing.

r3 B1 lists *"an unrevoked arbitrary-SQL executor"* (`05_assert.sql:32-55`) among the reasons
`05_assert.sql` must never be a migration, and the plan carries it forward as one of its three
unskippable warnings (`:40-44`). The reasoning is right and the conclusion is right. For accuracy:
`supabase/migrations/0004_test_exec_sql.sql:3-11` already ships `exec_sql(text)` as
`SECURITY DEFINER`, and I confirmed it in prod — `prosecdef = true`, ACL
`postgres=X/postgres | service_role=X/postgres`. So the *distinguishing* hazard of `assert_raises`
is that it is **unrevoked** (public EXECUTE, and `pg_default_acl` grants `anon=X` on every new
function in `public` — measured in both environments), not that an executor would be novel.

### L4 — Sample re-verification of v4's `[VERIFIED]` tags: 14 checked, 14 resolve.

`05_assert.sql:37` = `execute p_sql;` ✓ · `:2207` = `delete from profiles where id = p;` ✓ ·
`:893-911` ✓ · `:1843-1859` ✓ · `01_workspaces.sql:33` (`select id, id from profiles`) ✓ ·
`:36-48` ✓ · `:37` ✓ · `:42` ✓ · `:50-51` ✓ · `03_generations.sql:89-95` ✓ · `:96-97` ✓ ·
`04_artifacts.sql:269-288` ✓ · `:354-360` ✓ · `:628-633` ✓ · `check-schema-gates.sh:14-16` ✓.
The pattern r3 L3 found (good citation hygiene, defects elsewhere) recurs. The one citation problem
this round is not a wrong line number — it is M4, a query that cites itself correctly and measures
the wrong thing.

---

## Disposition of round 4's Codex half

| r4-codex finding | This round |
|---|---|
| **Medium** — the row counts bound the rewrite, not lock *acquisition*; want a "try, abort safely, fallback/pause-worker runbook" rather than "no maintenance window needed" | **CONFIRM, and here is the artifact it asks for and does not name.** The pause lever exists: `fly.toml:33-35` declares `[processes] web = "node server.js"` / `worker = "node worker.js"`, so the worker is independently scalable to zero. Two pieces of evidence narrow the risk further: (a) measured on prod at review time, `pg_stat_activity` showed **1 active transaction, longest 0 s** — the worker holds no long transactions, because every step is a separate PostgREST RPC (`claim_next_job`, lease heartbeats, `spend_ledger` reserve/release, complete, per `fly.toml:8-11`); (b) a *waiting* `ACCESS EXCLUSIVE` request blocks everything queued behind it, so the window is bounded by the longest statement already running, not by arrival rate. The inference "abort rather than queue" is sound; the runbook line is still missing |
| **Low** — the T1 SQL is claimed to be "in a file" but `find` located none | **RESOLVED, and the resolution post-dates the finding.** `docs/superpowers/specs/m4/t1-blast-radius.sql` exists, committed in `3f634bb` (*"round 4 Codex half — CONVERGED, and its three findings folded in"*). I read it in full; it is 0 write statements, and its queries match the plan's table. Its defect is M4 above, not its absence |
| **Low** — T0 still uses `check-docs` as its gate; `check-docs.py:447-472` does not read the M4 spine (r3 M1, unfixed in v4) | **CONFIRM, unfixed.** Independently: `grep -rn "append-only-generations-roadmap\|lands inert" scripts/ .github/workflows/` returns exactly one line, `scripts/check-anchors.py:10`, and only for the anchor header. There is no observation that makes T0's gate fail |
| **"T1 query verdict: correct"** — grouping pre-M4 by `(owner_id, video_id)` reproduces post-M4 `(workspace_id, video_id)` | **CONFIRM, independently.** `0001_core_schema.sql:23-32` — `videos.owner_id` is `not null` and `foreign key (playlist_id, owner_id) references playlists(id, owner_id)`, so a video's owner is its playlist's owner by constraint; `01_workspaces.sql:33` seeds `workspaces.id = profiles.id`; `01:37` and `:42` derive by owner then by playlist. The translation is exact |
| **"Assertion verdict: sufficient and expressible"** — a `DO $$ … RAISE EXCEPTION … $$` between `01` and `03:89-95` | **CONFIRM.** One addition it does not state: the placement is also required for a reason it gets for free — the nine triggers are created at `03:152-215` and `:253-262`, *after* the backfill at `:89-95`, so no trigger can fire during the backfill or during `01`'s three `UPDATE`s. That closes the "can a trigger fire during the backfill" question the lead raised, and the plan should say it rather than leave it to be re-derived |
| **Verdict: CONVERGED** | **DISAGREE.** See below |

---

## Verdict

**NOT CONVERGED.**

2 Blocking · 2 High · 4 Medium · 4 Low.

**On disagreeing with my partner.** r4-codex reviewed v4 as a *schema* change and found it sound —
and on that subject I largely agree with it: the SQL is right, the measurement is right, the lock
decision is right, and I could not break the one-transaction premise. Its CONVERGED is a defensible
verdict about the migration. It is not a verdict about the plan, because both of my Blockings are
about what happens *around* the DDL — recovery, and the suite that would notice the DDL breaking
something. Neither was in its scope this round, and a plan for an irreversible production change
cannot converge with the reversal step and the regression suite both unwritten. Per
`dual-review-halves-are-not-redundant`, a single CONVERGED is not proof, and this is the fourth
round: `docs/dev-process.md`'s Phase 6 trigger fires here regardless of my verdict.

**The single most important finding is B1.** Everything else in this document, and most of what
rounds 1–3 found, is a defect in a step. B1 is the absence of the step you need when one of those
defects survives every gate — which this schema has already done twice, both times discovered by
running it in an environment where discovering it was cheap. M4-β is the first environment where it
is not. The plan is one paragraph away from closing it, because M4 is the last moment at which the
answer is simply *drop everything it made* — every object 0027 creates is derived from state that
predates it, and no line of `lib/ app/ worker/` writes any of it. At M5 that stops being true. A
rollback written now costs an hour; the same rollback written at 2am with ingest down costs the
thing the whole schema exists to protect.
