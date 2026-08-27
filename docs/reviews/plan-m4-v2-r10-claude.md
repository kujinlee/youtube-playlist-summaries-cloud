# M4 v2 — round 10, CLAUDE half

**Subject:** branch `docs/m4-round7`, HEAD `0e64ce2`, `git diff fe966e4..HEAD` (14 commits, 24 files, +4050/−384).
**Reviewer:** Claude, independent. Codex half not read.
**Date:** 2026-08-26.

**Counts: 0 Blocking · 5 High · 4 Medium · 3 Low.**

## What I executed (not read)

Everything below that says MEASURED was run on this checkout, alone on the local Postgres.

| Command | Result |
|---|---|
| `M4_PHASE=post ./scripts/check-schema-gates.sh` | **exit 0, 14/14 green** (gate 1 emitted 119 `ok` notices; gate 8 119; gate 9/10 161 objects) |
| `./scripts/m4-base-db.sh --self-test` | 10/10 |
| `./scripts/run-schema-assertions.sh --self-test` | 15/15 |
| `python3 scripts/check-paid-caller-arrival.py --self-test` | 9/9 |
| mutation suite (via gate 2) | control green, 58 mutations, all as expected |
| **the base-fidelity probe I wrote for this round** | see below |
| gate-14 empty-input probe | 3 cases, all fail-OPEN — H2 |
| gate-1 gutted-assertions probe | reports `✅ schema verified` over zero assertions — H5 |
| `check-paid-caller-arrival` `//`-in-string probe | real `.rpc('record_artifact', …)` reads DORMANT — H4 |
| 58-anchor uniqueness in `0027` | **0 anchors occur ≠ 1 time — the author's claim is TRUE today** |

Environment left clean: no `m4_*` / `xr_*` / `mls_*` databases survive, working tree unmodified.

---

## The highest-value question, answered: did the NEW SUBJECT weaken the seven gates?

**No — and I have an execution, not an argument.** I built a base and rebuilt M4 onto it, then asked
the production-polarity gate whether the result is the same schema `0027` produced on `postgres`:

```
./scripts/m4-base-db.sh m4_r10_probe                                  -> rc 0
python3 scripts/check-live-schema.py --database m4_r10_probe --expect-absent   -> rc 0
docker exec … psql -d m4_r10_probe < (build-m4-schema.py output)      -> rc 0
python3 scripts/check-live-schema.py --database m4_r10_probe --expect-present  -> rc 0
  "M4 is PRESENT as expected — checked all 161 objects, BY DEFINITION not just by name
   (5 tables · 3 views · 70 columns · 14 triggers · 13 functions · 1 type · 12 indexes
    · 5 policies · 38 constraints)"
```

That is the strongest statement available with the instruments in the repo: the rebuilt base is
**definitionally identical** to the applied `0027`, across every catalog the digest reads. The seven
gates' subject moved and their *conclusion* did not.

### The three sub-questions

**(a) Is any assertion in `05_assert.sql` now VACUOUS on the new base?** No. MEASURED: gate 1 (base,
no seed) emits **119** `ok` notices and gate 8 (`postgres`, with seed) emits **119** — the same
count, both green. Every block scopes its reads to fixture ids it creates in the same transaction
(`vidA`, `vidB`, `vidC`, `vidF`, `vidSVC`, `vidT3`, `vidT4`, `vidH2`, `vidH3`). I grepped for counts
over M4 relations with no fixture scope and checked each of the 13 hits by hand: five are privilege
probes where the count is discarded (`05_assert.sql:999`, `:1009`, `:987`) and the rest have their
`where` on the following line. **The one real difference is recorded as M3 below** — `t_ws` is a
*different tenant* in the two gates, and nothing says so.

**(b) Can the rollback leave residue the manifest cannot see?** Not from `0027`. I enumerated every
statement in the migration that touches a pre-M4 object (non-comment lines, `alter table` /
`create trigger` / `create policy` / `grant` / `revoke` / `update` / `insert` / `create index`) —
the whole footprint is 3 columns, 2 FKs and 7 triggers on `profiles`/`playlists`/`videos`/`jobs`,
and **every one of them is in `live-manifest.txt`** (`col:jobs.workspace_id`,
`col:playlists.workspace_id`, `col:videos.workspace_id`, `con:jobs.jobs_workspace_owner_fk`,
`con:videos.videos_workspace_video_fk`, and the seven `trg:` rows at :161–174). `0027` creates no
index, policy, grant or rule on a pre-M4 relation. The digest reads 12 catalogs; the only relevant
one it does **not** read is `pg_rewrite`, and `0027` creates no rule.
One residue channel does exist and is invisible: `alter table videos drop column workspace_id`
leaves an `attisdropped` tombstone, so the rebuilt column lands at a higher `attnum` than on
`postgres`. It is harmless *here* because `m4_catalog.py:365-366` uses `attnum` only as a join key
and filters `not a.attisdropped` — I checked, because if the digest had included ordinal position
the probe above would have gone red and the seven gates would have been comparing a different shape.

**(c) `drop database` call sites.** Six, all safe against `postgres`:
`m4_base_db.py:81` `m4_subject_{pid}`, `mutate-schema.py:961` `m4_mutate_base_{pid}`,
`verify-schema.sh:94` `m4_verify_base_$$`, `gen-m4-manifest.py:263` `m4_manifest_base_{pid}`,
`run-schema-assertions.sh:150` `m4_assert_selftest_$$`, `m4-base-db.sh:150` `m4_base_selftest_$$`.
Distinct prefixes plus a live PID make a concurrent collision unreachable, `valid_name()`
(`m4-base-db.sh:60-66`) refuses anything that is not `m4_`/`xr_`/`mls_`, and `build()` drops before
creating so a stale same-PID leak is reclaimed. **The `M4_DB` override does bypass `valid_name`** —
I tried to turn it into a fail-open and could not: `M4_DB=postgres ./scripts/check-guard-coverage.py`
→ `CANNOT RUN … relation "workspaces" already exists`, **exit 2**;
`M4_DB=nonexistent_db_xyz ./scripts/check-sentinel-meanings.py` → **exit 2**. Fail-closed both ways.
Leak-on-kill is real but small — L2.

---

# Findings

## H1 — `mutate-schema.py:936` promises an anchor-count guard that does not exist

The single largest change in the branch redirects **both** mutation targets at one file, and rests
its safety on a property it says is mechanically enforced. `mutate-schema.py:933-940`:

```python
    # ⚠ WHY REDIRECTING BOTH TARGETS AT ONE FILE IS SAFE: `target` existed to disambiguate two
    # files; the migration is one. VERIFIED before doing it — all 58 anchors occur in 0027, and
    # every one occurs EXACTLY ONCE, so `replace(find, repl, 1)` cannot hit the wrong region.
    # If a future anchor appears twice, the count check below turns it into a loud INVALID.
```

**There is no count check below.** The only check is a zero-count test —
`mutate-schema.py:995-997`:

```python
    for label, find, repl, expect, target in MUTATIONS:
        original = originals[target]
        if find not in original:
            results.append((label, "INVALID", "anchor not found — mutation never applied"))
            continue
```

and then `mutate-schema.py:1001`:

```python
        copy_of[target].write_text(original.replace(find, repl, 1))
```

`str.replace(old, new, 1)` replaces the **first** occurrence and returns silently. An anchor
occurring twice is not INVALID; it is a mutation applied to the wrong region.

**Failure scenario.** `0027` is a concatenation of `01_workspaces.sql`, `03_generations.sql` and
`04_artifacts.sql`. Before this commit, `target` kept a `03`-anchor away from `04`'s text. Now both
resolve to `mig_copy` (`:938-940`). Add a rule to `03` whose anchor line already exists verbatim in
`04` — e.g. the two-line `on conflict … do update set` shapes, or any repeated
`revoke all on function …` idiom — and the `04` mutation edits the `03` copy. The verifier then
fails for an *unrelated* reason and `classify()` scores it `RED(other)` or, if the assertion
substring happens to match, plain `RED` — which the summary counts as ✅. A guard is then reported
mutation-covered while its own anchor was never touched. That is coverage laundering, in the gate
whose whole purpose is to prove guards are load-bearing.

**MEASURED:** the premise holds today. I loaded `MUTATIONS` and counted each `find` in `0027`:
`total mutations: 58 / anchors not exactly once in 0027: 0`. So this is a latent defect, not a live
one — which is exactly why it should be closed now rather than after it fires.

**What would prove me wrong:** show me the code that counts occurrences and emits INVALID on ≥2.
I read `run_suite()` end to end (`:900-1024`) and there is none.

**Fix:** three lines at `:995` — `n = original.count(find); if n != 1: results.append((label,
"INVALID", f"anchor occurs {n} times — ambiguous target"))`.

---

## H2 — gate 14 PASSES over zero input, and it is the only mechanical proof that the arbitrary-SQL executor never ships

`check-schema-gates.sh:159-161`:

```bash
run "14/14 05_assert.sql is NOT in any migration (arbitrary-SQL executor + profile deleter)" \
    bash -c '! grep -hv "^[[:space:]]*--" supabase/migrations/*.sql \
               | grep -qE "execute p_sql|delete from profiles|assert_raises|ASSERTION FAILED"'
```

If the glob matches nothing, `grep` writes `No such file or directory` to stderr, the second `grep`
gets empty input and exits 1, `!` inverts it, and the gate reports green having read nothing.

**MEASURED, three ways:**

```
--- case 1: migrations dir EMPTY (glob does not match) ---
grep: supabase/migrations/*.sql: No such file or directory
gate14 rc=0  (0 = PASSES)
--- case 2: migrations dir MISSING entirely ---
gate14 rc=0  (0 = PASSES)
--- case 3: 05_assert.sql copied to supabase/migrations/pending/0028_x.sql ---
gate14 rc=0  (0 = PASSES)
```

Case 3 is the weakest of the three — the Supabase CLI applies only top-level
`supabase/migrations/*.sql`, so a subdirectory is not a real ship path today. Cases 1 and 2 are the
serious ones, and they are **reachable in this very script**: `check-schema-gates.sh:18` is

```bash
cd "$(dirname "$0")/.."
```

under `set -uo pipefail` — **no `-e`**. A failed `cd` does not stop the script; it runs the
remaining thirteen gates from the wrong directory, and gate 14 is the one that answers *green*
rather than red. Same for anyone invoking the suite from a worktree or a copied tree.

This is the shape the branch's own sibling gate names in capitals — `verify-schema.sh:116`:
`# ⛔ A GATE THAT READS AN EMPTY SET PASSES — measured twice in this repo`. The lesson was applied
at one site in this commit and not at the other, which is `docs/plugins.md`'s recorded failure mode
verbatim.

**What would prove me wrong:** a run of `check-schema-gates.sh` from a directory without
`supabase/migrations/` that exits non-zero on gate 14. It does not; I ran the pipeline verbatim.

**Fix:** `shopt -s nullglob failglob`, or a precondition — `n=$(ls supabase/migrations/*.sql | wc
-l); [ "$n" -ge 27 ] || { echo "CANNOT RUN — read $n migrations"; exit 2; }`.

---

## H3 — `check-paid-caller-arrival.py`'s anti-rot falsifier can never fire, because its subject is an immutable file

The script's own docstring (`:25-30`) states the failure it exists to prevent:

```
⛔⛔ THE FAILURE MODE THIS GUARD HAS TO SURVIVE IS ITS OWN VOCABULARY GOING STALE.
A grep for a symbol reports "no callers" just as happily when the symbol has been RENAMED as when it
genuinely has none — and it would then read DORMANT forever, which is the one answer that lets the
money defect ship.
```

The guard it builds (`check-paid-caller-arrival.py:53-58, 108-110`):

```python
DEFINITION_SOURCES = (
    ROOT / "supabase/migrations/0027_stable_blob_addressing.sql",
    ROOT / "docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql",
)
...
def definition_present(sources: tuple[Path, ...]) -> bool:
    """True when at least one shipped source still DEFINES the symbol."""
    return any(p.is_file() and DEFINES.search(p.read_text(encoding="utf-8")) for p in sources)
```

Two problems, both in the same three lines.

1. **`0027` is an applied migration, and applied migrations are never edited.** The 27 files in
   `supabase/migrations/` are an append-only ledger — `rollback_0027…sql:9-16` is a whole essay on
   why a correction must not be filed as a later migration precisely because the ledger is
   append-only. So `DEFINES.search` over `0027` is **true forever**, whatever the live schema does.
   A future `0028` that renames or drops `record_artifact` leaves this check green and the script
   reports DORMANT for a symbol the database no longer has. The stated falsifier is unreachable.
2. **`any()` over two sources.** `04_artifacts.sql` is a spec file, not a shipped one, despite the
   docstring saying "shipped". Either source alone satisfies the check, so a rename in the migration
   is masked by a stale spec, and vice versa.

MEASURED: both files currently define the symbol exactly once, so the check passes for the right
reason **today** — the defect is that it will keep passing for the wrong reason.

**What would prove me wrong:** a repo convention under which `0027_stable_blob_addressing.sql` is
edited when the function is renamed. I found none — `docs/dev-process.md`, `rollback_0027…sql` and
the 27-file ledger all say the opposite.

**Fix:** ask the **live catalog** (`select 1 from pg_proc where proname='record_artifact'` against
the subject database, CANNOT RUN if unreachable), or the *newest* migration mentioning the symbol,
not the oldest. The `--self-test` case at `:194-198` will still pass — it uses a synthetic source.

---

## H4 — `//` inside a string literal blanks a real `record_artifact` call, and the guard reports DORMANT

`check-paid-caller-arrival.py:65-66, 79`:

```python
LINE_COMMENT = re.compile(r"//.*$", re.MULTILINE)
BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
...
    return LINE_COMMENT.sub(blank, BLOCK_COMMENT.sub(blank, src))
```

and the classifier at `:99-104`:

```python
            for n, (raw, bare) in enumerate(zip(src.splitlines(), stripped.splitlines()), 1):
                if SYMBOL not in raw:
                    continue
                ...
                (code if SYMBOL in bare else commented).append(entry)
```

The docstring at `:72-75` deliberately does not strip string literals — correct, since the call is
`supabase.rpc('record_artifact', …)`. But comment-stripping is applied to a line that may contain
`//` *inside* a string, and everything after it is blanked.

**MEASURED**, one file, one line:

```ts
const base = 'https://example.com/api'; const o = await sb.rpc('record_artifact', { p_ws: ws });
```

```
production callers: 0   (comments, not callers: 1)
DORMANT — no production caller. Backlog 26 may remain open; it costs nothing today.
exit: 0
```

A live production caller of the money path, classified as a comment. Any URL, protocol-relative
path, or `//`-containing literal earlier on the line does it; so does a `/*` in a string opening a
DOTALL block comment that swallows the call. This is the exact answer the docstring calls "the one
answer that lets backlog 26's money defect ship".

**What would prove me wrong:** nothing — I ran it. The output above is verbatim.

**Fix:** strip `//` only when it is not inside a string. A cheap sufficient version: find the symbol
first, and only consult `bare` when the raw line has no quote character before the `//`. Add the
line above as a `--self-test` case; the current 9 cases all put the `//` at column 0.

---

## H5 — gate 1 has no assertion floor, and reports `✅ schema verified` over ZERO assertions

`verify-schema.sh:127-131`:

```bash
SQL=$(printf 'begin;\n'; cat "${SRC_FILES[@]}"; printf '\n\\echo ALL_STATEMENTS_OK\nrollback;\n')
OUT=$(printf '%s' "$SQL" | docker exec -i "$CONTAINER" \
        psql -U postgres -d "$DB" -v ON_ERROR_STOP=1 2>&1)
echo "$OUT"
if grep -q ALL_STATEMENTS_OK <<<"$OUT"; then echo "✅ schema verified (rolled back)"; exit 0; fi
```

The marker is `printf`'d unconditionally after the `cat`, so it proves nothing **raised**. It cannot
prove anything **ran** — which is the sentence the sibling script in this same commit wrote a floor
for (`run-schema-assertions.sh:314`):

> `⭐ THE FLOOR. ASSERTIONS_OK proves nothing RAISED; it cannot prove anything RAN.`

**MEASURED.** I copied the spec tree, replaced `05_assert.sql` with two lines
(`-- gutted` / `select 1;`) and ran the gate:

```
ALL_STATEMENTS_OK
ROLLBACK
✅ schema verified (rolled back)
verify-schema rc=0
```

This matters more than it looks, for two reasons the branch itself states:

- `verify-schema.sh:23` — *"gate 1 … runs all 122, and is the ONLY thing that does"*. It runs the
  **largest** assertion corpus in the suite (119 `ok` notices, measured) and is the only gate with
  no count check on it.
- In `M4_PHASE=pre`, gate 8 is skipped by design (`check-schema-gates.sh:89-95`), so **in the pre
  phase there is no floor on the assertion corpus anywhere in the suite.**
- `verify-schema.sh:32-33` says *"`run-schema-assertions.sh` now carries a floor that fails when the
  count drops, which is the mechanical half of this note."* That sentence is written in gate 1's
  header and describes a mechanism that does not cover gate 1.

Gate 1 also lacks the leftover-row check its sibling has (`run-schema-assertions.sh:331-336`), so a
`commit;` reaching the middle of the concatenation would persist fixtures. Harmless today only
because the subject is a throwaway base — but that is an accident of the new subject, not a guard.

**What would prove me wrong:** a floor, a count, or any assertion in `verify-schema.sh` about how
much of `05_assert.sql` executed. There is none; the file's only quantitative check is `[ ! -s "$f" ]`
at `:118`.

**Fix:** the mechanism already exists — `RAN=$(grep -cE 'NOTICE:.*\bok\b' <<<"$OUT")` and the same
floor constant. One line, and it is measured at 119 in both gates today.

---

## M1 — `scripts/` holds production-touching TypeScript and the paid-caller guard neither scans nor reports it

`check-paid-caller-arrival.py:60-63`:

```python
PRODUCTION_DIRS = ("lib", "app", "worker", "components")
TEST_DIRS = ("tests",)
SUFFIXES = (".ts", ".tsx")
```

`scripts/` is in neither list, so its files are invisible — not counted as callers, not counted as
comments, not printed. It contains, among others, `scripts/cloud-sync.ts`, `scripts/rerender-html.ts`,
`scripts/repair-timestamps.ts`, `scripts/backfill-serial-prefix.ts` and
`scripts/fix-duplicate-summaries.ts` — operational scripts that run against **production** data.
A backfill that calls `record_artifact` to populate the manifest for existing videos is a plausible
first caller, and it would be the *first* thing written, before any `lib/` path exists.

The docstring says comments are "reported rather than dropped … silently discarding them would hide
the day one of them becomes a call". The same argument applies with more force to a whole directory.

**What would prove me wrong:** a rule that `scripts/*.ts` may not reach production data. There is
none; `scripts/cloud-sync.ts` is the documented sync entry point.

**Fix:** add `"scripts"` to `PRODUCTION_DIRS`, or a third bucket printed like the test bucket.

---

## M2 — gate 14's discriminating power is a property of a file it never checks

`check-schema-gates.sh:154-158` records the mutation test that justifies the signature:

```
#       0027 as built .................. 0     (control — must pass)
#       05_assert.sql alone ............ 164
#       0027 with 05 appended .......... 164   (must catch it)
```

MEASURED, and I reproduce those numbers exactly. But the 164 decomposes as:

| token | matches on non-comment lines of `05_assert.sql` |
|---|---|
| `execute p_sql` | 1 |
| `delete from profiles` | 1 |
| `assert_raises` | 62 |
| `ASSERTION FAILED` | **100** |

**162 of the 164 come from the assertion vocabulary, and nothing asserts that vocabulary still
exists.** Rename `assert_raises` → `expect_raises` and the message prefix → `INVARIANT VIOLATED` —
both ordinary refactors, neither touching the two dangerous constructs — and the gate's margin drops
from 164 to 2. The mutation test in the comment is a one-time measurement against the current file,
not a ratchet.

This is precisely the class `check-paid-caller-arrival.py` builds an anti-rot check for, **in this
same commit** ("a grep for a symbol reports no callers just as happily when the symbol has been
RENAMED"). Applied at one site, not at the sibling.

**What would prove me wrong:** a check anywhere that reads `05_assert.sql` and asserts the signature
still matches it. `grep -rn "05_assert" scripts/ | grep -i signature` returns nothing.

**Fix:** one line before the gate — `[ "$(grep -hv '^[[:space:]]*--' "$SPEC/schema/05_assert.sql" |
grep -cE "$SIG")" -ge 100 ] || { echo "CANNOT RUN — the signature no longer matches its subject";
exit 2; }` with `$SIG` named once and used by both.

---

## M3 — `t_ws` and `t_w2` are asserted to be two tenants and nothing checks that they are, and they are a *different* tenant in gate 1 than in gate 8

`05_assert.sql:146-147`:

```sql
create temp table t_ws as select id from workspaces order by id limit 1;
create temp table t_w2 as select id from workspaces order by id desc limit 1;   -- a SECOND tenant, for RLS
```

Two facts, both MEASURED, neither written down anywhere:

1. **On a single-workspace database, `t_ws` and `t_w2` are the same row.** Ten blocks then treat one
   tenant as two — `:735-746` ("another tenant sees 0 rows"), `:1107-1123` (the six-object sweep),
   `:463`, `:736`, `:1108`, `:1961`. They go RED, with a message that says *"cross-tenant leak"*,
   which is a false accusation against the schema. This is fail-loud, so it is Medium not High — but
   the failure names the wrong subject, and this repo has measured what a wrong-subject red costs.
   A `db reset` plus one signup produces exactly this state.
2. **The two gates run this file against different tenants and nothing says so.** The seed inserts
   `auth.users` id `00000000-0000-0000-0000-0000000000a1` (`seed-assertion-corpus.sql:32-34`), and
   `workspaces.id = owner_id` (`0027:48`), so that workspace **sorts first**:

   ```
   t_ws on postgres WITHOUT the seed:  00091597-f29d-49da-8f82-b6b25cd3c8d5
   t_ws WITH the seed applied:         00000000-0000-0000-0000-0000000000a1
   ```

   Gate 8 (`postgres` + seed) runs every assertion as the **seed** tenant; gate 1 (base, no seed —
   `verify-schema.sh:107` lists only the migration and `05_assert.sql`) runs them as a **real**
   tenant. Both are green, and I could not find an assertion whose meaning changes. But the
   difference was introduced silently by this commit, and the deleted anti-drift block
   (`05_assert.sql`, old :1155) is on record measuring the opposite property of the same variable:
   *"t_ws is `workspaces order by id limit 1` and that workspace holds no videos"*. A variable that
   already caused one measured defect changed meaning between two gates with no note.

**What would prove me wrong:** an assertion that `t_ws <> t_w2`, or a comment stating which tenant
each gate resolves to. Neither exists — `grep -n "t_w2" 05_assert.sql` returns 9 lines, none of them
a check.

**Fix:** two lines after `:147` — `if (select id from t_ws) = (select id from t_w2) then raise
exception 'CANNOT RUN — only one workspace; the cross-tenant assertions would be vacuous'; end if;`
plus a `raise notice` naming the resolved tenant so the two gates' subjects are visible in the log.

---

## M4 — `read_catalog` returns the WHOLE output when its marker is missing

`m4_base_db.py:114`:

```python
            return p.stdout.split(marker, 1)[-1]
```

`str.split` with no match returns `[whole]`, and `[-1]` is that whole string. A missing marker
therefore hands the caller every line psql printed, including the DDL echo, instead of failing.

Reachability is genuinely low: the marker is `\echo`'d unconditionally and `ON_ERROR_STOP=1` plus
the `rc != 0` branch above catches the error path. It matters because it is the *third* copy of the
"a parse that found nothing must fail loudly" rule in this repo (`CLAUDE.md`:
*"a parse that found nothing … must fail loudly"*), and this function was extracted specifically so
there is one place to put such a rule.

Downstream it is fail-closed by luck: `check-guard-coverage.py:227` filters on `check:`/`fk:`/
`index:`/`trigger:` prefixes, so a whole-output parse yields an empty set and every entry reports
STALE. `check-sentinel-meanings.py` and `check-vocabulary-collisions.py` filter similarly.

**What would prove me wrong:** a caller that treats an empty result as CANNOT RUN before parsing.
None does.

**Fix:** `if marker not in p.stdout: print("CANNOT RUN — marker not found; TREAT AS NOT RUN");
raise SystemExit(2)`.

---

## L1 — a base leaks on SIGTERM/SIGKILL, and nothing sweeps orphans

`verify-schema.sh:101-102` uses `trap … EXIT`, `mutate-schema.py:1000` uses `atexit`,
`m4_base_db.py:87-90` uses `try/finally`. All three cover normal exit and SIGINT; none covers
SIGTERM or SIGKILL. A killed run leaves a 21–49 MB database on the shared local cluster
(my own probe measured 49 MB), and there is no sweeper: `m4-base-db.sh` has `--self-test` and a
build mode only.

MEASURED after this review: zero orphans on the cluster, so nothing has leaked in practice yet.
This is task #145's shape one layer out, which the module header at `m4_base_db.py:23-25` names.

**Fix:** `./scripts/m4-base-db.sh --sweep` dropping `m4_%` databases whose PID suffix has no live
process, called at the top of `check-schema-gates.sh`.

## L2 — the re-runnability measurement was made against an EMPTY M4 corpus

`05_assert.sql:39-40` and `run-schema-assertions.sh:56-58` both rest on:

> MEASURED 2026-08-26 against the applied 0027 … 119 assertions reported ok, none raised, identical
> on three consecutive runs.

MEASURED by me on the same database:

```
video_artifacts=0    video_generations=0    workspaces=8384    workspace_videos=4674
```

The claim *"no migration-only assertion remains … none of them can be invalidated by a later write"*
is therefore verified in the one state where it is easiest to be true: the two tables the assertions
mostly read hold **zero real rows**, because backlog 26 is DORMANT and `record_artifact` has no
caller. The blocks are all fixture-scoped and I expect them to survive a populated corpus — but the
sentence claims a property of every future state and was measured on the empty one. That is worth
one line of honesty in the header, in a file whose whole discipline is bounding its own claims.

**Fix:** append to `05_assert.sql:40` — *"…measured while `video_artifacts` and `video_generations`
held 0 rows; re-measure the day a caller lands (see `check-paid-caller-arrival.py`)."*

## L3 — the assertion floor is a lower bound and 119 is partly loop-derived

`05_assert.sql` contains **59** static `raise notice '… ok …'` sites but produces **119** runtime
notices (both MEASURED), because the population-coverage instrument loops over `artifact_kind` ×
free/paid. So `ASSERTION_FLOOR=119` moves if the enum gains a value — upward, harmlessly — and the
floor cannot distinguish "an assertion was deleted" from "the enum shrank and a loop ran fewer
times". Not a defect; worth a sentence at `run-schema-assertions.sh:68` so the next person to see the
number move looks in the right place.

---

# Claims I tried to falsify and could NOT

Recorded because a round that only lists what it found overstates its own coverage.

1. **The 58 anchors occur exactly once in `0027`.** TRUE — loaded `MUTATIONS`, counted every `find`
   against the migration text: 0 anchors with a count other than 1. (The *guard* on it is H1.)
2. **`0027`'s three backfills cannot abort on production data.** TRUE, and this was my best
   candidate for a Blocking. `0027:52-53, 57-58, 62-63` each do backfill → `set not null`, which
   aborts the whole migration if one row is unreachable. All three are FK-protected upstream:
   `playlists.owner_id uuid not null references profiles(id)` (`0001:12`),
   `videos.playlist_id uuid not null` + `foreign key (playlist_id, owner_id) references playlists`
   (`0001:24,31`), `alter table jobs add column playlist_id uuid not null` + the same composite FK
   (`0009:4-6`). `workspaces` is seeded from **every** profile (`0027:48`) before any backfill reads
   it. No row can be left NULL.
3. **`M4_DB` is a fail-open escape hatch.** FALSE — exit 2 in both directions, measured above.
4. **The base's missing privileges make an ACL assertion vacuous.** FALSE. `m4-base-db.sh:97-98`
   clones with `--no-privileges`, but the ACL assertions at `05_assert.sql:1774-1806` read
   `video_generations` and `video_generations_collectable` — M4 relations whose grants come from the
   rebuild SQL, not from the clone.
5. **The rollback's `skipping`-NOTICE check misses a class of silent no-op.** FALSE as far as I can
   reach: `drop trigger/table/function/type if exists`, `drop column if exists` and
   `drop constraint if exists` all emit `NOTICE: … skipping`, and `m4-base-db.sh:114-119` fails on
   any of them.
6. **`--expect-absent` is blind to something `0027` creates.** FALSE for this migration — footprint
   enumerated above, all of it in the manifest.
7. **Gate 14 can be evaded by renaming within the assertion vocabulary.** Partly — see M2. A full
   copy of `05_assert.sql` still matches on `execute p_sql` and `delete from profiles` even after a
   total vocabulary rename, so the gate degrades from 164 to 2 rather than to 0.

# Known-and-excluded, per the brief

Not re-reported: the `--expect-present` added-column asymmetry, and the un-re-run `pre` phase.
I found nothing showing the first is worse than `mutate-live-schema-check.sh` mutation 3 already
states. On the second: gate 1 is the pre phase's only assertion gate and it has no floor (H5), which
makes the argued greenness of `pre` weaker than the argued greenness of `post` — worth folding into
whatever decides when `pre` is re-run.

# Verdict

Nothing here blocks the migration. `0027` reads correctly against real data, the backfills cannot
abort, and the new base is definitionally faithful — I proved that by executing, not by reading.

But five of the findings are the same shape, and it is the shape this branch exists to remove: **a
guard that cannot fail.** H1 documents a count check that was never written; H2 passes over zero
input; H3's stated falsifier is unreachable by construction; H5 reports success over zero assertions;
M2's discriminating power rests on a property nothing checks. Four of the five sit *beside* a sibling
in the same commit that got the discipline right — `run-schema-assertions.sh` has a floor and gate 1
does not; `check-paid-caller-arrival.py` has an anti-rot canary and gate 14 does not;
`verify-schema.sh` refuses an empty source and gate 14 does not. That is the repo's own recorded
failure mode — *a fix applied to the one place someone noticed while a sibling kept the defect* — and
it is now the dominant defect shape of this round.

Each fix is one to three lines and every one of them is a line the branch has already written
somewhere else.

**NOT CONVERGED**
