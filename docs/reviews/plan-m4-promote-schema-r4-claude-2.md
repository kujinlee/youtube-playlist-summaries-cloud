# M4 plan — round 4, SECOND independent CLAUDE half

**Target:** `docs/superpowers/plans/2026-08-25-m4-promote-the-schema.md`
**Reviewed at commit:** `ae995f1`. ⚠ The file changed during this review (`3f634bb` → `ae995f1`);
every line number below is against `ae995f1`.
**Branch:** `docs/m4-plan` · **Date:** 2026-08-25
**Codex half:** `plan-m4-promote-schema-r4-codex.md` — returned **CONVERGED** (0 Blocking, 0 High).
**Prior rounds read in full:** `-r1-codex.md`, `-r2-codex.md`, `-r3-claude.md`, `-r4-codex.md`.

⚠ **This is a SECOND Claude half, run in parallel and blind to the first.**
`plan-m4-promote-schema-r4-claude.md` was written and committed (`ae995f1`) by another agent while
this review was in progress; I read it only after finishing. The two took different angles and
overlap in one place — the transaction question — where they inspected **different binaries** and
should be read together. See *Reconciliation with the first Claude half* at the end.

**Method note — this half EXECUTED.** The Codex half states it reviewed by reading plus one re-run of
the T1 measurement. This half ran all six schema gates against the live local Supabase container, and
disassembled the installed Supabase CLI to settle the plan's central premise. Three of the findings
below are not visible without doing that. Everything I could **not** run is labelled **NOT VERIFIED**.

**One trail-integrity note, not a finding.** `ae995f1` added a block at `:118-124` attributed
`⟳ r4-claude:` — a correction this review did not make and had not reported when the commit landed.
The correction itself is right. But an attribution written before the reviewer speaks is the same
shape as a gate written before its subject exists, and this repo's review trail is load-bearing.

---

## Blocking

### B1 — T2 writes the migration and never mentions the corrections-collision assertion. The only guard against silently destroying paid user content lives in the prose of a task already ticked `[x]`.

The plan's ⛔ #2 (`:26-38`) is explicit that the destruction risk is **not closed as a property**:

> `:109-111` — *"So H3 is closed for a migration run TODAY and is not closed as a property. **T2 keeps
> a guard:** the migration asserts the count is still zero **inside the same transaction**, immediately
> before the `workspace_videos` backfill, and aborts if it is not."*

That sentence is at `:109-111`, inside **T1**, which is ticked `[x]` at `:88`.

T2 — `:126-134`, the task that actually writes `0027_stable_blob_addressing.sql` — says in full:
promote the three files "in dependency order, removing nothing else"; splitting it is an outage; and

> `:131` — **"Add the missing guard:** `revoke all on workspaces from anon, authenticated`."

**T2 names exactly one addition to the promoted SQL, and it is not the assertion.** The word
"assertion", the word "collision", and the string `raise exception` do not appear in T2.

Why this is Blocking and not bookkeeping:

- The plan's own execution contract is `superpowers:subagent-driven-development` (`:6-7`;
  `docs/dev-process.md` Phase 3 default) — **a fresh subagent per task.** The T2 subagent reads T2.
  T1 above it is ticked and reads as the record of a finished measurement, not as an instruction.
- The assertion has **no task, no gate and no falsifier.** T3's gate (`:145-147`) is about the
  rewritten ratchets; T6's (`:178-182`) is "run all six gates"; none of the six inspects `0027`'s text.
- Nothing mechanical would notice. **SEARCHED:**
  ```
  grep -rln "2026-08-25-m4-promote-the-schema\|m4-promote" scripts/ .claude/hooks/ .github/
  → (no matches)
  ```
  No script in the repo reads this plan.

The assertion is *correct* where it is specified — see L5, which sets out why it is not merely
helpful but exactly sufficient. That is what makes its homelessness Blocking rather than High: it is
the whole residual control on a path the plan says can destroy paid content.

**Required.** Move it into T2 as a numbered sub-step carrying the literal SQL, placed after the last
statement of `01_workspaces.sql` and before `03_generations.sql:89`. Give it a falsifier T3 or T6 can
run: `0027` must contain a `raise exception` between those two points, and deleting it must turn a
gate red.

---

### B2 — T0's gate greps three strings, and the destructive sentence in the spine is not one of them.

The spine, `docs/superpowers/plans/2026-08-22-append-only-generations-roadmap.md:215-217`:

> **The four spec `schema/*.sql` files become migrations `0027+`** (⟳ was `0026+`; `0026` was taken by
> `record_correction_spend` in M2 slice A). `05_assert.sql` gets a home in CI or
> `scripts/check-schema-gates.sh`. No application caller yet — the schema lands inert.

T0's gate, `:84-86`:

> The gate for T0 is therefore a **quoted diff**: the spine's M4 entry must contain the words
> *one transaction* and *not inert*, and must not contain *lands inert*. Grep for those three strings.

An implementer who edits only the final sentence — `the schema lands inert` → `not inert; one
transaction` — makes all three greps pass while **`The four spec schema/*.sql files become migrations
0027+` survives verbatim on `master`.**

That sentence is r3 B1's Blocking. It is the instruction that puts
`delete from profiles where id = p;` (`schema/05_assert.sql:2207`) and `execute p_sql;` (`:37`) into
`supabase/migrations/`. r3 B1 said so in terms — `plan-m4-promote-schema-r3-claude.md:46-48`:

> The spine has the same contradiction in the same sentence … so T0 — which corrects the spine —
> must correct **this** sentence too, **and the plan does not say so.**

v4 rewrote T0's gate in response to r3 M1 and r4-codex, and still does not say so. The plan's own
⛔ #3 records the lesson one screen above — `:43-44`, *"'Four files' was a count written without
asking what the fourth one does"* — and the gate written to enforce ⛔ #3 cannot see the count.

**Required.** Add to T0's gate: the spine's M4 entry must **not** contain `four spec` (nor any
four-file count), and **must** contain a sentence naming `05_assert.sql` as never a migration. Three
more greps, same cost as the three already there.

---

## High

### H1 — "`05_assert.sql` is NEVER a migration" is prose in three places and mechanical in none. SEARCHED.

The prompt for this round asked specifically whether the exclusion is mechanical. It is not.

```
grep -rn "05_assert" scripts/ .github/ tests/ docs/superpowers/specs/2026-08-03-stable-blob-addressing/*.sh
→ scripts/check-schema-gates.sh:13   (comment)
→ scripts/check-schema-gates.sh:14   (comment)
```

Two hits, both inside the comment block at `check-schema-gates.sh:13-17` explaining that `05` cannot
run standalone. No executable line anywhere names it. And nothing inspects the migrations directory
at all:

```
grep -rln "supabase/migrations\|MIGRATIONS" scripts/ .claude/hooks/ .github/workflows/
→ scripts/subject_status.py
```

`subject_status.py` is the subject-banner helper. **No check reads the contents of
`supabase/migrations/`.**

What the plan offers instead is three prose statements — `:40-44`, `:54-55`, `:127-128` — plus the
spine sentence B2 leaves standing. T4's gate (`:159-160`) gates the **home** ("`check-schema-gates.sh`
runs it, and the cannot-run case exits non-zero"). It does not gate the **exclusion**: nothing there
fails if `05_assert.sql` is *also* copied into `supabase/migrations/0028_assert.sql`.

State the observation that would make "05 is never a migration" FAIL. There is none. Per `CLAUDE.md`,
that makes it a decision wearing a checkbox — the exact phrase the plan uses about T8 at `:194`.

The mechanical form is five lines and the repo has eleven siblings for it
(`check-ratchet-contract.py` discovers 11, executed below): fail if any file under
`supabase/migrations/` matches `execute p_sql`, `delete from profiles`, `assert_raises`, `\set`, or
`\echo`. The last two are decisive on their own — `05_assert.sql:15` and `:2239` are psql
meta-commands and r3 verified they are the only backslash lines in all four spec files.

---

### H2 — `./scripts/check-schema-gates.sh` is RED **today** in TWO gates. T3 budgets repair for one, and the four costliest items are in neither round's inventory. MEASURED.

Executed on this machine, 2026-08-25, branch `docs/m4-plan`, against the live local stack
(`docker ps` → `supabase_db_youtube-playlist-summaries-cloud` up). No schema change applied.

| Gate | Command | Result |
|---|---|---|
| 1/6 | `docs/superpowers/specs/.../verify-schema.sh` | ✅ exit 0 — `ASSERTIONS_OK`, `ALL_STATEMENTS_OK`, `ROLLBACK` |
| 2/6 | `docs/superpowers/specs/.../mutate-schema.py` | ✅ `63/63 mutations behaved as expected`, `baseline restored: GREEN` |
| 3/6 | `scripts/check-guard-coverage.py` | ❌ **exit 1 — 10 problem(s)** |
| 4/6 | `scripts/check-sentinel-meanings.py` | ❌ **exit 1 — 5 problem(s)** |
| 5/6 | `scripts/check-vocabulary-collisions.py` | ✅ exit 0 |
| 6/6 | `scripts/check-docs.py` | ✅ exit 0 |

**Gate 3 — CONFIRM r3 B3 by execution, and extend it.** r3 reached its verdict statically and said so
(`-r3-claude.md:122-125`: *"a live run would confirm the count, not the fact"*). The count is 10, not
6, and the extra four are a different **kind** of work:

```
❌ STALE         art_pending_is_leased / art_pending_has_token / art_pending_has_reserved_at
❌ STALE         art_summary_has_no_source
❌ STALE         video_artifacts_inflight_uq
❌ STALE         video_artifacts_workspace_id_video_id_source_generation_id_fkey
❌ UNCLASSIFIED  gen_card_is_summary_only
❌ UNCLASSIFIED  gen_major_is_summary_only
❌ UNCLASSIFIED  video_artifacts_identity_uq
❌ UNMUTATED     video_artifacts_paid_uq
```

- **STALE** (6) = delete a dict entry. This is what T3 `:138-141` describes and budgets.
- **UNCLASSIFIED** (3) = make a SHAPE/SEQUENCE **design decision** about a live guard — the question
  `check-guard-coverage.py` exists to force (*"what does this guard do when the caller is merely
  SECOND?"*). Not a deletion.
- **UNMUTATED** (1) = write a new mutation in `mutate-schema.py`; the tool's own message is *"Its
  reconciler is a claim, not a tested behaviour."*

T3 then says `:144` "Estimate accordingly." The estimate is built on 6 of 10 items, and the 4 it
omits are the expensive ones.

**Gate 4 — the plan carries NO task for it at all.**

```
❌ STALE  video_artifacts.lease_expires_at
❌ STALE  video_artifacts.lease_token
❌ STALE  video_artifacts.reserved_at
❌ STALE  video_artifacts.source_generation_id
❌ STALE  video_generations.reserved_by
5 problem(s) — sentinel meanings NOT met
```

r3 L2 flagged this and could not resolve it — *"Whether that makes gate 4 red or merely blind depends
on how the script treats a `MEANINGS` key with no live column — **UNVERIFIED**, needs a live run."*
It is **red**. T3 (`:136-150`) names gates 1, 2, 3 and `check-anon-exposure.py`. It never names
`check-sentinel-meanings.py`.

So milestone gate 1 (`:212`, *"six green **against the migration**"*) starts from four green, and the
plan funds one of the two repairs. Per `CLAUDE.md`, a gate that is red before the first task and
recorded as the milestone's acceptance criterion is the shape this plan keeps writing.

---

### H3 — "one file, ONE transaction" is a property of the FILE'S CONTENTS, not of the runner. Nothing gates the condition, and the plan has filed the question as closed. MEASURED by disassembling the installed CLI.

This is the plan's central Blocking premise — `:129-130`:

> ⛔ **Splitting it is an outage** (r2): columns, backfills, `NOT NULL` promotions, both FKs and all
> nine triggers **commit together or not at all**.

r3 L1 recorded the runner half as **UNVERIFIED** and asked for a one-line executable proof
(`-r3-claude.md:380-386`). v4's answer is `:227-228`, under *Open questions this plan does NOT settle*:

> ⟳ *r3 L1 **REFUTED** the "can this run in one transaction?" worry in advance — `01/03/04` contain no
> statement that cannot. **Recorded so it is not re-raised.***

That files the **statement-level** half (which r3 did verify) as settling the **runner-level** half
(which r3 explicitly did not), and marks the whole thing do-not-re-raise. True about the statements,
silent about the runner — the defect shape the plan itself names three lines earlier at `:123`.

**Measured.** `supabase` is installed at `/usr/local/bin/supabase`, version `2.109.1`
(`supabase --version`). The migration-apply routine, reconstructed from the binary's strings:

```js
let G = pK(U);                                 // SPLIT the migration file into statements
yield* H.exec("RESET ALL");
yield* Lz(H);                                  // bootstrap supabase_migrations.schema_migrations
let $ = function*(){                           // flush the buffered batch
   yield* H.exec("BEGIN");
   for (const F of V) yield* H.exec(F.sql);    // or query(B1H) for the version row
   yield* H.exec("COMMIT");
   ... .pipe(tapError(() => H.exec("ROLLBACK")))
};
for (const V of G)
   if (EEL(V)) { yield* $; yield* H.exec(V); } // COMMIT the buffer, run OUTSIDE, reopen
   else Y = [...Y, {kind:"exec", sql:V}];
if (K.length > 0) Y = [...Y, {kind:"version"}];
yield* $;                                      // final flush
```

with the split predicate:

```js
EEL = s => KEL.test(s) || WEL.test(s) || QEL.test(s) || ZEL.test(s) || YEL.test(s)
KEL = /^CREATE\s+(?:UNIQUE\s+)?INDEX\s+CONCURRENTLY(?:\s|$)/u
WEL = /^REINDEX(?:\s|\().*\sCONCURRENTLY(?:\s|$)/u
QEL = /^VACUUM(?:\s|\(|$)/u
ZEL = /^ALTER\s+SYSTEM(?:\s|$)/u
YEL = /^CLUSTER(?:\s|$)/u
```

Three consequences the plan does not carry:

**(a) One file can be many transactions.** The guarantee holds for `01/03/04` *only because* r3 L1
verified none of those five forms appears in them. That is a property of the SQL text, and the plan
states it as a property of "one migration file" (`:126`, `:129-130`). Add `create index concurrently`
to the promoted DDL later — the obvious optimisation the day `videos` is not 12 rows — and the file
silently becomes ≥2 transactions, reopening exactly r2 B2's outage window, with no gate that would
notice. The condition is checkable in one line and belongs in T2's gate.

**(b) The half-apply case the prompt asks about, and the plan does not answer.** The version row is
appended **last** (`if (K.length > 0) Y = [...Y, {kind:"version"}]`) and commits with the final flush,
so today it is genuinely all-or-nothing. But in the split case an earlier batch **commits**, a later
one fails, and `supabase_migrations.schema_migrations` never receives the row — the schema is half
applied and a re-run replays committed DDL, dying on `already exists`. The plan has no rollback
section, no down migration, and no stated recovery path. It relies entirely on (a) holding.

**(c) `RESET ALL` runs first**, discarding any `lock_timeout` set on the role or the database. So
T5's `lock_timeout`/`statement_timeout` (`:167-169`) has exactly one place it can live: as
`set local lock_timeout = '5s';` — the **first statement inside the migration file**, which is T2's
artifact. T5 does not say that, and T5 runs **after** T2 in the plan's own order (`:203`). See M4.

*(The CLI's bootstrap `Lz` does contain `SET LOCAL lock_timeout = '4s'`, but it is `SET LOCAL` inside
that bootstrap's own `BEGIN … COMMIT` for creating `schema_migrations`, so it does not carry into the
migration transaction.)*

---

## Medium

### M1 — the plan lists `check-gate-falsifiability` as a milestone gate. It cannot read anything M4 writes. EXECUTED.

`:216` puts `check-gate-falsifiability` in the "all 0" list. `scripts/check-gate-falsifiability.py:55-58`:

```python
GATE_SCOPES: dict[str, list[str] | None] = {
    "docs/m1.4-finishup-checklist.md": None,
    "docs/roadmap-to-launch.md": ["## M1", "## M2", "## M3"],
}
```

Neither the M4 plan nor the M4 spine (`2026-08-22-append-only-generations-roadmap.md`) is in scope,
and `roadmap-to-launch.md` is scoped to M1–M3. Executed with the plan in its current state:

```
python3 scripts/check-gate-falsifiability.py
→ gate falsifiability OK — every unticked gate item names what would fail it     exit=0
```

It is green now and would be green if **every** gate in this plan were unfalsifiable. This is r3 M1 /
r4-codex's finding one layer out: the plan repaired T0's gate and left, in the milestone list, a
second gate that cannot fail for its own subject.

For completeness — the rest of `:214-216` executed today: `check-docs` 0, `check-anchors` 0
(*"every spec/plan dated >= 2026-08-25 declares one"* — it does read this plan, for its anchor
header), `check-review-rounds` 0, `check-roadmap-consistency` 0, `check-test-counts` 0,
`check-arch-findings` 0, `check-ratchet-contract` 0.

### M2 — T1's pgcrypto measurement does not read the namespace, which is the only part that can fail.

`docs/superpowers/specs/m4/t1-blast-radius.sql:47-52`:

```sql
\echo === pgcrypto digest available? (M4 introduces prod's first dependency) ===
select 'pgcrypto_installed=' || (select count(*) from pg_extension where extname='pgcrypto')::text
    || ' digest_callable='  || (select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace
                                 where p.proname='digest')::text as pgcrypto;
```

The `join pg_namespace n` is **dead** — `n` appears in no projection and no predicate. The query
counts `digest` overloads in *any* schema and reports 2, which the plan's T1 table records at `:103`
as `installed=1, callable=2`.

The property M4 depends on is that `digest` resolves under `set search_path = public, extensions`
(`03_generations.sql:39`), and `03_generations.sql:31-34` is emphatic that this exact resolution has
already failed once:

> `digest` is pgcrypto's and Supabase installs pgcrypto into the `extensions` schema, NOT `public` —
> so every unqualified name here is a latent version of the same bug.

r3 M4 asked for `select extname, extnamespace::regnamespace from pg_extension` **and** the server
version (`normalize(…, NFC)` needs PG13+). The committed file has neither: `:1-5` prints db, user,
server address and `now()`, and no `version()`.

Failure mode is loud — the backfill at `03_generations.sql:89-95` calls `corrections_hash_of`, so the
migration aborts — which is why this is Medium. But `digest_callable=2` in the row whose entire job
is retiring this risk is a green check over the wrong subject.

### M3 — T4 is an unmade decision, and T6 assumes one of its two branches.

T4 `:156-158`: *"state which assertions are vacuous on an unseeded database and what covers them
instead — **or** seed M4-α with production-shaped data."* T6 `:179`: *"apply `0027` to the **local**
Supabase stack, **seeded per T4**."* If T4 takes the first branch there is no seeding and T6's
instruction has no referent; the order (`:203`) puts T4 before T6, so the fork is live at execution
time.

The fork may already be closed by the environment change v4 made: the local stack carries a dev
corpus (`05_assert.sql:58` records `2903 of 2904`), and I measured gate 1 green against it today
(H2), including `ASSERTIONS_OK`. Saying that plainly is cheaper than leaving the "or" open.

### M4 — T5's decision cannot be executed where the plan puts it, and the runbook it adds has no falsifier.

Order `:203`: `T2 ─▶ T3 ─▶ T4 ─▶ T5`. T2 writes `0027`; T5 decides the `lock_timeout`, which by
H3(c) must be a statement *inside* `0027`. Either T5 moves before T2, or T2 must be told to leave a
placeholder T5 fills.

Separately: the r4-codex Medium **is** correctly folded in — `:170-176` now reads *"try without a
maintenance window, abort safely, and have a pause-the-worker runbook … **not** 'a maintenance window
is unnecessary'"*, and the T1 block at `:120-123` no longer contradicts it. **CONFIRM as fixed.**
But *"Write that runbook as part of T5"* (`:174-175`) states no observation that would make T5 fail,
and `statement_timeout` (`:168`) is named with no value. Suggested falsifier: `0027`'s first statement
is `set local lock_timeout`, and a named file under `docs/` contains the exact commands to stop and
restart the Fly worker machine.

### M5 — the plan never names the binary that will apply M4-β, and it is not pinned.

Two Supabase CLI builds are reachable on this machine at different versions (2.109.1 global, 2.115.0
in the npx cache), the repo pins neither, and the recorded prod applications and the test harness use
different invocation styles. Since H3 makes the one-transaction guarantee a property of the runner's
statement-splitting behaviour, the plan should record the exact binary and version M4-β uses, the way
T1 records its database subject. Full evidence in *Reconciliation with the first Claude half* below.

---

## Low

### L1 — REFUTE, by execution, my own hypothesis about T1's re-run recipe.

`t1-blast-radius.sql:57-58` documents the run as
`docker exec -i -e PGU="$CLAUDE_RO_DATABASE_URL" … psql "$PGU"`. I expected an unset credential to
fall through to the container's local Postgres and print plausible local numbers. It does not:

```
docker exec -i -e PGU="" supabase_db_youtube-playlist-summaries-cloud \
  bash -c 'psql "$PGU" -tAq -v ON_ERROR_STOP=1' < docs/superpowers/specs/m4/t1-blast-radius.sql
psql: error: connection to server on socket "/run/postgresql/.s.PGSQL.5432" failed:
      FATAL:  Peer authentication failed for user "root"      exit=2
```

**It fails closed.** What remains is smaller: the file *prints* its subject (`:1-5`) and asserts
nothing about it, so a `CLAUDE_RO_DATABASE_URL` pointed at the wrong project still produces a
green-looking run — the shape recorded in `discover-the-target-and-read-it-back-uncached`. The plan
says "Re-measure before M4-β" (`:123-124`); one `do $$ … raise` on `current_user`/`inet_server_addr()`
would close it.

### L2 — CONFIRM: the trigger count is right; `0027` is genuinely free; nothing else non-inert hides in `04`.

Counted from the DDL, not from the plan:

```
grep -n -A3 "^create trigger" 01_workspaces.sql 03_generations.sql 04_artifacts.sql
```
Nine on **live** tables — `03:152` (`profiles`), `03:198`, `03:201` (`playlists`), `03:204`, `03:207`,
`03:253`, `03:258` (`videos`), `03:210`, `03:213` (`jobs`). Six on **new** tables — `03:557`,
`04:809`, `04:1046`, `04:1085`, `04:1124`, `04:1237`. **No live-table trigger hides in `04`.** ✓ `:23`

Also checked for other non-inert forms and found none beyond what the plan names:
`create policy` — five, all on new tables (`01:22`, `03:78`, `03:565`, `04:266`, `04:663`);
`create index` — three, all on new tables (`04:189`, `04:191`, `04:247`); no `create or replace`
anywhere in the three files; no `grant`/`revoke` naming `playlists`/`videos`/`jobs`/`profiles`; and no
function-name collision with the 30 functions the shipped migrations define (compared both lists).
`ls supabase/migrations/` ends at `0026_record_correction_spend.sql`, so **`0027` is free.** ✓

### L3 — the FK count at `:23` is wrong: five FK constraints land on live tables, not two.

```
01_workspaces.sql:36  alter table playlists add column workspace_id uuid references workspaces(id);
01_workspaces.sql:41  alter table videos    add column workspace_id uuid references workspaces(id);
01_workspaces.sql:46  alter table jobs      add column workspace_id uuid references workspaces(id);
01_workspaces.sql:50-51  jobs_workspace_owner_fk  (workspace_id, owner_id) -> workspaces(id, owner_id)
03_generations.sql:96-97 videos_workspace_video_fk (workspace_id, video_id) -> workspace_videos
```

r1-codex's Medium already said the plan cited one of two; v4 still says two and there are five. The
three inline ones validate trivially (the column is all-NULL at `add column` time) but they are
permanent RI checks on every future insert into the three busiest tables, and they change DELETE
semantics — which is precisely what the "not inert" section exists to enumerate.

On DELETE specifically: the three inline FKs are `NO ACTION` while `workspaces.owner_id` is
`on delete cascade` (`01:13`), so `delete from profiles` survives only because `playlists.owner_id`
and `jobs.owner_id` cascade from `profiles` (`0001_core_schema.sql:12`, `0008_jobs_queue.sql:4`) and
`videos` cascades from `playlists` (`0001_core_schema.sql:32`), removing the referencing rows within
the same statement. **This is covered by the assertion suite and I saw it pass** — gate 1's live run
emitted `NOTICE: ok (T3 cascade): account erasure carries provenance away with it; the delete guard
does not block it`, from `05_assert.sql:2207-2210`. So: REFUTED as a risk, but the plan does not make
the argument and the count at `:23` is still wrong.

### L4 — CONFIRM r4-codex's T1-grouping verdict, independently.

`0001_core_schema.sql:32` — `foreign key (playlist_id, owner_id) references playlists(id, owner_id)`
— forces `videos.owner_id` to equal its playlist's owner; `01_workspaces.sql:33` seeds
`workspaces.id = profiles.id`; `01_workspaces.sql:37, :42` derive playlist and video workspace by
that chain. So `(owner_id, video_id)` is the exact pre-M4 image of post-M4 `(workspace_id, video_id)`.
The T1 falsifier query (`t1-blast-radius.sql:26-32`) asks the right question of the right key. ✓

### L5 — the `distinct on` ordering is non-deterministic among ties, and the assertion makes it exactly sufficient. Worth writing down, because it is why B1 is Blocking.

`03_generations.sql:89-95` orders by
`workspace_id, video_id, (coalesce(data->>'corrections','') <> '') desc` — ties broken arbitrarily.
But the projection is only four columns: the two group keys, `nullif(data->>'corrections','')`, and
`corrections_hash_of(data->>'corrections')` — the last two both pure functions of the same text.

So once *"no group holds two distinct non-empty corrections"* is asserted, every row that could win a
tie projects **identical** values and the arbitrary tie-break cannot change the result. Enumerating
the cases: `('A','')` → the filter leaves one row, non-empty wins, no loss. `('A','A')` → one distinct
value, no loss. `('A','B')` → flagged, abort. The assertion is not a partial mitigation; it converts
a coin toss over paid content into a proof. **Which is exactly why it having no task (B1) is Blocking
rather than High.**

### L6 — `jobs_workspace_owner_fk` is safe, but not for a reason T1 gives.

`01_workspaces.sql:50-51` validates `(workspace_id, owner_id)` against existing rows, and T1's
falsifier list (`:101`) contains no check for `jobs.owner_id` disagreeing with its playlist's owner.
It cannot: `0009_job_playlist_identity_and_worker_persistence.sql:5-6` already constrains
`(playlist_id, owner_id) → playlists(id, owner_id)`. One line in T1's table, because "0 orphans" is
not the property this FK needs.

### L7 — r3 L4 is fixed; `check-producer-enumeration.py` is still absent from the gate list.

The plan now uses `- [ ]` syntax (`:77`, `:126`, `:136`, `:152`, `:162`, `:178`, `:184`, `:193`), so
`check-plan-progress.py`'s fail-closed path is no longer self-inflicted. ✓
`check-producer-enumeration.py` remains outside `:212-216`, as r3 H1 noted in passing — M4 makes
`videos.workspace_id` and `jobs.workspace_id` single-producer guarded values
(`03_generations.sql:198-215`). Executed today: exit 0.

---

## What I could NOT verify

- **Prod state.** No `psql` on this machine and `CLAUDE_RO_DATABASE_URL` is unset in my environment,
  so I did not re-run T1 against production. r4-codex did, via Node `pg`, and matched every figure.
  T1's *numbers* are therefore twice-measured; T1's *SQL* is what M2 faults.
- **The half-apply recovery path (H3(b)) empirically.** The CLI's behaviour is read from the binary,
  not exercised. The proof r3 L1 asked for — a throwaway migration failing at its last statement —
  is cheap and now clearly worth its price, since the CLI is installed locally and the stack is up.
- **Whether `supabase db push --linked` shares the `Jz` apply routine with `migration up`.** The
  roadmap records prod applications via `db push --linked`
  (`docs/roadmap-to-launch.md:88`, `:162`). I located one apply routine in the binary and did not
  prove it is the only one. **NOT VERIFIED** — and it is the routine M4-β actually runs, so T5 should
  establish it rather than inherit my inference.

---

## Disposition of the prior rounds

| Round | Finding | This round |
|---|---|---|
| r1 B1–B4 | the M4a/M4b split | CONFIRM as resolved |
| r2 B1 | "re-point" hides a rewrite | CONFIRM as carried into T3 `:142-144` — but see H2: the *inventory* is bigger than r3 measured and gate 4 is unbudgeted |
| r2 B2 | committed-file chain → enqueue outage | CONFIRM as resolved **conditionally** — see H3(a). The condition is unstated and ungated |
| r2 H1 / r3 H2 | lock strategy | CONFIRM as resolved at `:170-176`. Residue in M4: placement and falsifier |
| r3 B1 | v3 ships `05_assert.sql` | **PARTLY resolved.** Fixed in the plan (`:54-55`, `:127-128`); NOT fixed in the spine, and T0's gate cannot see it — **B2**. Never mechanical — **H1** |
| r3 B2 | M4-α unreachable by the gates | CONFIRM as resolved by the move to local |
| r3 B3 | gate 3 red before re-pointing | **CONFIRM by execution and EXTEND** — 10 problems, not 6 — **H2** |
| r3 B4 | assertions vacuous on an empty DB | **PARTLY resolved** — the local corpus probably closes it (gate 1 green here today), but T4 still states it as an open fork — **M3** |
| r3 H1 | `workspaces` revoke + `MONEY_TABLES` | CONFIRM as resolved at `:131-134`, `:148-150` |
| r3 H3 | backfill destroys paid corrections | **Measured (T1) but NOT guarded** — the assertion has no task — **B1** |
| r3 M1 / r4-codex | T0's gate cannot fail | **PARTLY resolved** — the new gate is falsifiable but under-scoped (**B2**), and the same defect recurs at the milestone level (**M1**) |
| r3 M2 / M3 | T7/T8 gates | CONFIRM as resolved at `:188-196` |
| r3 M4 | pgcrypto dependency | **NOT resolved** — the query added does not read the namespace — **M2** |
| r3 M5 | read-only contradiction | CONFIRM as resolved |
| r3 L1 | one-transaction premise | **REGRESSED.** The verified half is now filed as settling the unverified half, marked do-not-re-raise — **H3** |
| r3 L2 | gate 4 stale | **UNVERIFIED half now resolved: gate 4 is RED** — **H2** |
| r3 L4 | checkbox syntax | CONFIRM as resolved |
| r4-codex Medium | lock inference overstated | CONFIRM as resolved at `:170-176` and `:120-123` |
| r4-codex Low | T1 SQL in `/tmp` | CONFIRM as resolved — the file is committed. Its *contents* are M2 |

## Reconciliation with the first Claude half — the two reads inspected DIFFERENT binaries

`plan-m4-promote-schema-r4-claude.md` also went after the transaction premise, and reports it under
its B1 as **verified to hold**, citing *"Supabase CLI 2.115.0, `@supabase/cli-darwin-x64/bin/supabase`"*
and *"the pinned Supabase CLI binary"*. My H3 reports the same routine from a **different build**.
Both reads are of real binaries and neither is wrong about what it opened. What is wrong is the word
**pinned**, and that matters here:

```
grep -rn "supabase" package.json
→ package.json:32    "@supabase/ssr": "^0.12.0",
→ package.json:33    "@supabase/supabase-js": "^2.109.0",

ls node_modules/@supabase/
→ auth-js  functions-js  phoenix  postgrest-js  realtime-js  ssr  storage-js  supabase-js
```

**The repo does not depend on the Supabase CLI at all.** `@supabase/cli-darwin-x64` is not in
`node_modules`; it exists only in this machine's npx cache. Two builds are reachable, and they are
different versions:

```
/Users/kujinlee/.npm/_npx/aa8e5c70f9d8d161/node_modules/@supabase/cli-darwin-x64/bin/supabase --version
→ 2.115.0                                        # what `npx supabase …` resolves to TODAY
/usr/local/bin/supabase --version
→ 2.109.1                                        # what a bare `supabase …` runs
```

And the repo uses **both** invocation styles:

- `docs/roadmap-to-launch.md:88` — *"Migrations 0001–0021 applied + verified (`supabase db push`…)"*
- `docs/roadmap-to-launch.md:162` — *"`0023`/`0024`/`0025` applied 2026-08-11 (`supabase db push --linked`)"*
- `tests/integration/global-setup.ts` / `docs/roadmap-to-launch.md:667` — *"`npx supabase migration up`"*

So M4-β's transaction semantics depend on which of two unpinned, differently-versioned binaries the
operator happens to invoke, and the prod applications on record used the bare form — 2.109.1, the
one I read. My H3 stands as written for that path; the first half's B1 stands for the `npx` path.
The two agree on the substance (the split predicate is the same five statement forms in both builds)
and the divergence adds a finding neither half had alone:

**The plan should name the exact binary and version M4-β will be applied with, and record it the way
T1 records its database subject.** *"One transaction"* is currently a property of an unpinned tool
that the npx cache silently upgrades between runs — which is the same class as the plan's own
`videos.workspace_id_exists=0` subject line, applied to the instrument instead of the data.

## On the Codex half's CONVERGED

Not adjudicated by preference. Of the nine findings above, the three heaviest — B1, H2, H3 — turn on
things a reading pass cannot reach: which task a sentence lives under when a fresh subagent executes
it, the live exit status of two ratchets, and the apply routine inside a binary. r4-codex's own
"Assertion verdict: sufficient and expressible" is correct about the assertion and silent about
whether any task writes it, which is the same layer error B1 is about. Per
`dual-review-halves-are-not-redundant`, a single CONVERGED is not proof; here the two halves disagree
and the finding-reviewer has executed evidence.

---

## Verdict

**2 Blocking · 3 High · 5 Medium · 7 Low.**

**The single most important finding is B1.** The plan's own ⛔ #2 says the backfill can silently
destroy paid user content and that the risk is *"not closed as a property"*. The entire residual
control is one in-transaction assertion — correct, sufficient (L5), and specified only in the prose
of a task ticked `[x]`. The task that writes the migration names one addition and it is a different
one. Under the plan's own fresh-subagent-per-task execution contract, and with no script in the repo
reading this plan, the most likely outcome of executing v4 as written is a `0027` without the
assertion — and the gate that would notice does not exist.

**⚠ This is the fourth non-converging round on this subject** (r1, r2, r3, r4-claude). Per
`docs/dev-process.md` Phase 6, the four-round trigger fires: a Phase 6 architecture review is now due
alongside the fixes, not after them. Note the shape the four rounds share, which is what Phase 6 is
for: r1→r2→r3→r4 each fixed the *instance* a gate named and left the *class* — T0's gate fixed while
the milestone gate list carries the identical defect (M1); gate 3 budgeted while gate 4 is red and
unnamed (H2); the statement-level transaction question answered and filed as closing the runner-level
one (H3). Six of nine findings here are a previous round's fix applied at one site with a sibling
untouched — `shape #10`, which this spec has now recorded ten times.

NOT CONVERGED
