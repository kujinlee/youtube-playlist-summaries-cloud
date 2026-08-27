# M4 round 12 — Claude half

Subject: `974f6ec` (merged unreviewed via PR #155; its `0027` is LIVE in production) and `959811f`
(round-12 fixes written from the Codex half). Branch `fix/m4-instrument-hardening`.

**Control run first, before any probe.** Unmutated, in place, at the real repo path:

```
python3 scripts/check-paid-caller-arrival.py --self-test   ->  32 of 32, rc 0
python3 scripts/check-paid-caller-arrival.py               ->  DORMANT, rc 0,
                                                               0 production callers, 2 test comments
python3 scripts/check-docs.py                              ->  rc 0
```

No repo-tracked file was edited. Every fixture below lives in a `tempfile.TemporaryDirectory()` and
is driven through the real `report()` / `ledger_net_effect()` / `strip_sql_noise()` imported from the
committed script, so the "20 failures that were a path artifact" trap is structurally avoided: the
code under test is loaded from `/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-paid-caller-arrival.py`,
only its *inputs* are synthetic. `mutate-schema.py` and `mutate-live-schema-check.sh` were not run;
production was not touched.

---

## BLOCKING — the money guard has NO CALLER. Twelve rounds have hardened a script that nothing runs, and `dev-process.md` lists it under "What is mechanically enforced"

`scripts/check-paid-caller-arrival.py:1-585` · claimed as enforced at `docs/dev-process.md:142`

**FAILING OBSERVATION.** Plant `await sb.rpc('record_artifact')` in `lib/`. Then:
`.github/workflows/ci.yml` is green, `npm test` is green, `./scripts/check-schema-gates.sh`
(all 14 gates) is green, every `.claude/hooks/*` is green. Nothing anywhere goes red. The verdict
this guard computes reaches a decision only if a human remembers to type the command — which is the
*exact* property the script's own docstring was written to destroy:

> `check-paid-caller-arrival.py:18-23` — *"Its trigger was prose … `docs/dev-process.md` says the
> same thing generally: **before adding a rule, ask whether it can be a script.** This one can."*

It became a script and stopped there. A script with no caller is not a gate, and this repo has
already paid for that sentence — `scripts/check-schema-gates.sh:47-51` records it as a **round-4
BLOCKING** in this same plan:

> *"⟳ r4 BLOCKING (codex + claude): the live gate existed for a whole day and NOTHING CALLED IT. Not
> this suite, not CI, not a hook, not package.json. Every claim that the promotion gate verifies the
> deployed catalog was true only for a human who typed the command. **A gate with no caller is a
> script, not a gate.**"*

That paragraph is 130 lines above the gate list that does not contain
`check-paid-caller-arrival.py`. The r4 finding was fixed at the site it named and never swept —
defect class 4, at the two sites this repo files under
`a-convention-catches-what-you-read` / `true-about-the-name-silent-about-the-layer`.

**Why this outranks everything else in this round.** `0027` is live in production *today*. Backlog
26's row (`docs/backlog.md:55`) says **"OPEN — blocks T5 (task #44)"** and calls this script the
mechanised trigger; `docs/roadmap-to-launch.md:748` says *"the second half is now a command, not a
judgement"*. The next milestone (M5 — write-path cutover) is the milestone whose entire job is to
put the first caller on `record_artifact`. The one moment this guard exists for is the one moment
nothing will run it.

**HOW VERIFIED.**
```
grep -n "check-paid\|paid-caller" .github/workflows/*.yml   -> no match
grep -n "paid-caller" package.json                          -> no match
grep -rn "paid-caller" .claude/                             -> no match
grep -n "paid-caller" scripts/check-schema-gates.sh         -> line 175 only, inside a COMMENT
                                                               ("That is the same rot
                                                                `check-paid-caller-arrival.py`
                                                                builds an anti-rot check for")
grep -rn "paid-caller" --include=*.sh --include=*.py --include=*.json --include=*.toml --include=*.yml .
   -> 3 hits: the script's own usage lines (:4, :5) and that one comment. NO executable caller.
```
The only mention of the script in the 14-gate suite is prose *praising its design*.

**The narrow objection, stated so it can be rejected on purpose.** One could argue the guard is
meant to be hand-run at a milestone boundary. Then the row at `docs/dev-process.md:142` is in the
wrong table — that table's header (`dev-process.md:120`) reads *"What is mechanically enforced …
The script is the truth"* — and per `CLAUDE.md`'s Gates rule it is *"a decision or an investigation
wearing a checkbox: rename it, don't tick it."* Either wiring or the row is wrong; both cannot stand.

---

## HIGH — `strip_sql_noise()` desynchronises on `E'…\'…'`, blanks the rest of the ledger file, and reports EXISTS over a real DROP. New in `959811f`, and it is r11 H1's defect class one language over

`scripts/check-paid-caller-arrival.py:233-250` (the `'` branch)

The `'` branch treats `''` as the only escape. That is correct for ordinary Postgres strings
(`standard_conforming_strings = on`, so a backslash is literal) — and **wrong for `E'…'` strings,
where `\'` *is* an escape.** The scanner ends the string at the escaped quote, the following `'`
opens a phantom string, and because `blank(start, i)` runs to `n` when no closing quote is found,
**everything after it in the file is blanked** — silently, with no diagnostic. `stop = n if end < 0`
at line 256 gives the dollar-quote branch the identical fail-silent property.

The direction matters: a blanked **CREATE** yields exit 2 (loud, safe); a blanked **DROP** yields
`exists = True` → `report()` proceeds → **`DORMANT`, rc 0, for a symbol that no longer exists.** That
is the single verdict `check-paid-caller-arrival.py:27-28` names as the one that lets the money
defect ship.

**FAILING OBSERVATION** — `0027` creates the function, `0028` really drops it:

```sql
-- 0028_y.sql
select E'don\'t';
drop function record_artifact(uuid);
```
```
ledger_net_effect() -> (True, '0027_x.sql (creates it)')
report()            -> DORMANT, rc 0          [truth: the symbol is GONE; want rc 2]
strip_sql_noise()   -> "select E      t  \n                                    \n"
                       ^ the entire `drop function` line blanked
```

**This is not a hypothetical dialect.** `supabase/migrations/0027_stable_blob_addressing.sql:109-110`
already uses E-strings on the money path:
`regexp_replace(regexp_replace(p_corrections, E'\r\n?', E'\n', 'g'), E'\n+$', '')`. Today none of
them contains `\'`, which is the only reason the corpus is clean (measured below). The guard's whole
purpose is to survive a **future** `0028`.

**Note the shape.** r11 H1's finding was *"a hand-written scanner desynchronised on quoting"*, and
its fix (`ts-comment-spans.mjs:25-33`) is an explicit, dated commitment: *"stop proxying … a degraded
hand-rolled answer is what the two rounds above were. **NO FALLBACK.**"* `959811f` then hand-rolled a
SQL lexer in the same file, forty lines below a docstring that cites that very lesson
(`check-paid-caller-arrival.py:217-220`: *"half a lexer is worse than none"*). Fourth consecutive
round whose worst finding is the previous round's fix.

**HOW VERIFIED.** `scratchpad/probe3.py` and `probe4.py` — import the committed module, build the
two-file ledger in a tempdir, call the real `ledger_net_effect` / `report`. Output above verbatim.
Controls in the same run: bare `drop function record_artifact(uuid);` → rc 2 ✅;
`drop` then a real `create` → EXISTS ✅ (so the stripper is not simply blanking everything).

**And the corpus control, which is the reason this is HIGH and not BLOCKING.** I re-lexed all 27
migrations plus the 5 spec `schema/*.sql` files and counted every column-0 `create function`,
`create table`, `create policy`, `create trigger`, `drop function`, `alter table`, `grant` before and
after stripping: **zero lost, in every file** (`scratchpad/probe2.py`). `ledger_net_effect` on the
real tree returns `(True, '0027_stable_blob_addressing.sql (creates it)')` and the single real
`DEFINES` hit survives at the identical offset 72482. The defect is armed for the next migration,
not firing on this one.

---

## HIGH — `DROPS` cannot see a quoted identifier or `ALTER FUNCTION … SET SCHEMA`, and every miss lands in the DORMANT direction. r11 H3 swept two rename spellings and left three

`scripts/check-paid-caller-arrival.py:88-90`

r11 H3 widened `DROPS` because *"the docstring named a rename and the pattern could not see one"*
(`:82-87`). It added `drop routine` and `alter … rename to`. Three equally standard spellings of
"this function is gone" still match neither pattern, and — unlike a missed CREATE — a missed DROP is
silent and fatal: `exists` stays `True`, the guard scans, and prints `DORMANT`.

**FAILING OBSERVATION** — each is a valid `0028` after a `0027` that creates the function:

| `0028_y.sql` | truth | `report()` |
|---|---|---|
| `drop function record_artifact(uuid);` | gone | rc **2** ✅ control |
| `drop function "record_artifact"(uuid);` | gone | rc **0 — DORMANT** ⛔ |
| `drop function public."record_artifact"(uuid);` | gone | rc **0 — DORMANT** ⛔ |
| `alter function public.record_artifact(uuid) set schema archive;` | gone from `public` | rc **0 — DORMANT** ⛔ |

`set schema` is the one that matters most: the live-catalog arm at `:322-324` filters on
`n.nspname = 'public'`, so the *catalog* would correctly say absent — and `report():346`
(`exists = ledger or bool(live)`) lets the blind ledger overrule it. The two authorities were split
deliberately in r11 M4; this is the case where the ledger being wrong cannot be corrected by the
authority that is right.

**HOW VERIFIED.** `scratchpad/probe4.py`, real `report()` on tempdir fixtures, table transcribed
verbatim from its output. `drop function record_artifact;` (no arg list) → rc 2 ✅, included as a
second control so the table is not four unrelated reds.

**Not a "widen the regex a fifth time" recommendation.** The repo has already measured where that
ends (`a-privilege-is-not-a-capability`: *"round 7 wanted to widen the fingerprint a FIFTH time"*).
The generalisable observation is that `DEFINES`/`DROPS` are an open-ended enumeration of SQL
spellings — the same unbounded-counter-example question r11 H1 escaped by asking the compiler. The
authority that cannot be spelled around is `pg_proc`, which this script already queries.

---

## MEDIUM — verify-schema.sh's new "transport" branch is a list of Docker message wordings, and its own comment says it is not. Six realistic unreached-subject cases — including the database this script itself creates — still report "❌ schema FAILED"

`docs/superpowers/specs/2026-08-03-stable-blob-addressing/verify-schema.sh:153-162`

The comment at `:153-154` states the contract:

> *"⚠ The test is the TRANSPORT, not the wording of any one Docker message. If nothing that looks
> like psql output came back, we did not reach the database, whatever the reason."*

The implementation at `:155` is seven fixed substrings: five Docker phrasings plus
`connection refused` and `could not connect to server`. It covers the Docker layer and nothing
below it. Everything libpq says when the *server* is reachable but the *subject* is not falls
through to `echo "❌ schema FAILED"; exit 1` at `:163`.

**FAILING OBSERVATION** — verdict logic copied byte-for-byte from `:131-164` into a harness and fed
synthetic `$OUT` (no Docker, no database touched):

| `$OUT` | want | got |
|---|---|---|
| `Error response from daemon: No such container: x` | CANNOT RUN | rc 2 ✅ |
| `Error response from daemon: Container abc is not running` | CANNOT RUN | rc 2 ✅ |
| `Cannot connect to the Docker daemon … Is the docker daemon running?` | CANNOT RUN | rc 2 ✅ |
| `psql: error: connection to server … failed: FATAL:  database "m4_verify_base_9" does not exist` | CANNOT RUN | **rc 1 "schema FAILED"** ⛔ |
| `psql: … FATAL:  role "postgres" does not exist` | CANNOT RUN | **rc 1** ⛔ |
| `psql: … FATAL:  the database system is starting up` | CANNOT RUN | **rc 1** ⛔ |
| `psql: … FATAL:  sorry, too many clients already` | CANNOT RUN | **rc 1** ⛔ |
| `psql:<stdin>:900: server closed the connection unexpectedly` | CANNOT RUN | **rc 1** ⛔ |
| `verify-schema.sh: line 128: docker: command not found` | CANNOT RUN | **rc 1** ⛔ |
| `psql:<stdin>:12: ERROR:  relation "workspaces" already exists` | schema FAILED | rc 1 ✅ |
| `psql:<stdin>:800: ERROR:  artifact_key not unique` | schema FAILED | rc 1 ✅ |
| `""` / whitespace only | CANNOT RUN | rc 2 ✅ |

Row 4 is not decoration. `verify-schema.sh:94-102` **creates `m4_verify_base_$$` itself** and drops
it from an `EXIT` trap; `:87-89` documents that `mutate-schema.py` supplies its own via `M4_DB` and
reuses it across 58 mutations. A half-failed `m4-base-db.sh`, a trap that fired early, or a stale
`M4_DB` export produces exactly `FATAL: database "…" does not exist` — the script's most likely
unreached-subject failure is the one its new branch cannot see. Row 9 is the plain "Docker isn't
installed" case: bash's own `command not found`, not Docker's `executable file not found`.

**And the verification recorded in the commit message tested only the direction that could not
fail.** `959811f` says: *"Verified BOTH ways: four realistic psql errors (missing relation, RLS
denial, assertion raise, unique violation) still exit 1, so the new branch cannot launder a real
failure."* All four are rows 10–11's class — real failures staying rc 1. The direction the fix
*claims* is the direction it was never swept in: unreached subjects were tested with **one** input,
the Docker one that motivated it. Instance, not class.

**Blast radius is bounded, which is why this is MEDIUM not HIGH.** `scripts/check-schema-gates.sh:26`
(`if "$@"; then :; else fail=1; fi`) treats 1 and 2 identically, so the suite still goes red; and
`mutate-schema.py:885-886` classifies an output with no `ERROR:` as `INVALID`, not as caught. The
damage is the headline a human triages on — a red build that names the schema as guilty when the
schema was never read. That is precisely the defect r11 M3 fixed one layer in, restated at `:149-151`
by this very commit.

**HOW VERIFIED.** `scratchpad/branch.sh` — `verify-schema.sh:131-164` verbatim with `OUT="$1"`, run
under `set -uo pipefail`. Twelve inputs, table transcribed from its output. The empty-output test
`[ -z "${OUT//[[:space:]]/}" ]` was checked directly and is reachable and correct (rows 12); bash
does honour `[[:space:]]` inside `${var//…}`. It is, however, close to unfalsifiable in practice —
`docker exec` writes *something* on every failure path I could construct, so the branch that fires
is always the substring list.

---

## MEDIUM — `PRODUCTION_DIRS` misses `middleware.ts` and `types/`, `SUFFIXES` misses `.mjs`, and nothing checks that the list covers the TypeScript surface

`scripts/check-paid-caller-arrival.py:98-100`

`PRODUCTION_DIRS = ("lib", "app", "worker", "components", "scripts")`, `SUFFIXES = (".ts", ".tsx")`.

**FAILING OBSERVATION.** `middleware.ts` lives at the **repo root**, not under any listed directory.
It is real Next.js production code that runs on every request —
`middleware.ts:1-12` imports `createServerClient` from `@supabase/ssr` and builds a live Supabase
client. A `record_artifact` call placed there is invisible to the guard: not a caller, not a comment,
not printed. `types/index.ts` (7.1 KB, tracked) is equally invisible, and `scripts/` holds **3
`.mjs` files** that the suffix filter excludes even though `scripts/` was deliberately added as
production surface by r10 M1.

**HOW VERIFIED.**
```
find . -name '*.ts' -not -path './node_modules/*' -not -path './.next/*' | sed 's#^\./##; s#/.*##' | sort -u
  -> app  lib  scripts  tests  types  worker  middleware.ts  next.config.ts  jest.*.config.ts  …
find scripts -name '*.mjs' | wc -l   -> 3
head -12 middleware.ts               -> live @supabase/ssr client, per-request
```

**Same class as the finding that produced the list.** `check-paid-caller-arrival.py:93-97` records
r10 M1 adding `scripts/` with the reasoning *"a backfill … is the most plausible FIRST caller … and
the directory was invisible to this guard."* The fix added the one directory that had been noticed.
`a-convention-catches-what-you-read`: a hand pass fixes what you looked at; the list is still
hand-maintained and there is no check that it equals the tracked TypeScript surface minus `tests/`.

---

## LOW — `entry not in bucket` makes the headline count a count of LINES, and a line in both buckets is printed under "comments, not callers" while firing

`scripts/check-paid-caller-arrival.py:196-199`, printed at `:376-379`

`entry` is `f"{path}:{line}: {text[:120]}"` — identical for every occurrence on one line — so the
dedupe collapses distinct calls.

**FAILING OBSERVATION.**
```
lib/x.ts:  await sb.rpc('record_artifact'); await sb.rpc('record_artifact'); await sb.rpc('record_artifact');
  ->  production callers: 1   (comments, not callers: 0)          [three callers]

lib/x.ts:  /* record_artifact note */ await sb.rpc('record_artifact');
  ->  production callers: 1   (comments, not callers: 1)
      · lib/x.ts:1: /* record_artifact note */ await sb.rpc('record_artifact');   <- listed as a COMMENT
      ⛔ BACKLOG 26 HAS FIRED — 1 production caller(s) reach `record_artifact`:   <- and as a CALLER
```

The verdict is right in both cases (`if code:` at `:381` is the decision, and `959811f` says the
double-listing is intentional). The defect is that `docs/backlog.md:55` quotes these two numbers as
measurements — *"0 production callers, 0 test callers, and TWO comment lines"* — under a ⟳ note
saying the count is now *"computed rather than quoted, because a hand-written count of a grep is a
second representation of the grep."* The computed number is a line count wearing a caller count's
label. Today it is 0/0/2 either way; the day it fires, "1 production caller" can mean three.

**HOW VERIFIED.** `scratchpad/probe4.py`, real `report()` on tempdir fixtures, output verbatim.

---

## LOW — `dev-process.md:142` says this script has 9 self-test cases; it has 32, and `check-docs.py` is green over the gap

`docs/dev-process.md:142` vs `scripts/check-paid-caller-arrival.py --self-test`

**FAILING OBSERVATION.** The row reads *"(`--self-test`: 9 cases)"*. Measured: **32 of 32**. The
count went 9 → 18 (r10) → 24 (r11) → 32 (r12) and the spine was never updated; `959811f`'s own commit
message records *"Self-test 24 → 32 cases"* in the same commit that leaves the row at 9.

**It is isolated, not systemic — which is what makes it a real drift rather than a convention gap.**
Every sibling row I measured is correct:

| row | claimed | actual |
|---|---|---|
| `check-review-rounds.py` | 14 | 14 ✅ |
| `check-anchors.py` | 15 | 15 ✅ |
| `check-explainer-delivery.py` | 8 | 8 ✅ |
| **`check-paid-caller-arrival.py`** | **9** | **32** ⛔ |

The one row that drifted is the row for the script the last three rounds changed. `check-docs.py`
returns rc 0, so nothing mechanical covers a self-test count quoted in the enforcement table — the
`check-test-counts.py` ratchet named at `dev-process.md:147` covers the roadmap's suite counts, not
these. Per HEAD's own standing rule (`7c95059`, *"qualify every number in prose"*), this is the
shape that rule exists for.

**HOW VERIFIED.** `python3 scripts/check-paid-caller-arrival.py --self-test | tail -1` → `32 of 32
self-test cases passed`; the three sibling scripts run the same way; `python3 scripts/check-docs.py`
→ rc 0.

---

## What I checked and did NOT find a defect in

Recorded so the next round does not re-spend it, and so a green here is attributable.

- **`scan()`'s UTF-16 offsets after the new loop.** `starts[]` is built from `splitlines(keepends=True)`
  and indexed by the `splitlines()` line index; `u16(line[:col])` is recomputed per occurrence from
  the same code-point string. The two stay consistent, and `col + len(SYMBOL)` cannot re-find an
  overlapping match (`record_artifact` does not self-overlap). All 5 r11-H1 and 3 r12-B1 fixtures
  pass. No defect.
- **Double-counting / a line in both buckets misleading `report()`.** `report()` decides on
  `if code:` — a commented twin cannot mask a caller. Confirmed by fixture (LOW above is cosmetic).
- **`strip_sql_noise` eating a legitimate `create function`.** Measured across all 27 migrations and
  all 5 spec `schema/*.sql`: every column-0 `create function` / `create table` / `create policy` /
  `create trigger` / `drop function` / `alter table` / `grant` survives stripping, count-for-count
  (`probe2.py`). `create function f() … as $$ body $$` is safe because the name precedes the body.
  A `do $$ … execute 'create function …' … $$` block *would* be blanked, but
  `grep -rniE "execute .*create (or replace )?function" supabase/migrations/` returns only a comment
  in `0026`.
- **`$` that is not a dollar-quote.** `$1` params and `'$5.00'` money literals: the regex at `:252`
  requires `[A-Za-z_]` after `$`, and both are inside already-blanked bodies/strings anyway.
  Dollar-tags containing digits (`$tag1$`) match correctly. No defect.
- **Nesting / ordering in the stripper.** `$$` inside `--`, inside `/* */`, and inside `'…'` are all
  reached by the left-to-right scan in the right order and skipped correctly. Nested block comments
  count depth as documented.
- **Plain `'…\'` strings.** With `standard_conforming_strings = on` the backslash is literal, so
  Postgres and the stripper agree. Only `E'…'` diverges (HIGH above). `U&'…'` is unused
  (`grep -rn "U&'" supabase/migrations/` → no match).
- **The new exit 2 laundering a real failure.** Both real-failure inputs stay rc 1; the substring
  list contains nothing that appears anywhere in `supabase/migrations/` or
  `schema/` (`grep -rniE "connection refused|could not connect|docker daemon|…"` → no match), so
  psql cannot echo a corpus line into a false CANNOT RUN.
- **`$?` after a pipe (defect class 6).** `verify-schema.sh` reads no exit status after any pipe;
  `:141` and `:158` pipe into `head`/`sed` but exit immediately after on a literal code. `:195`
  uses a here-string, not a pipe. The r11 B1 `grep -q`-closes-the-pipe shape is absent from the
  r12 diff.
- **Empty-set-passes (defect class 2).** `comment_spans` returns `{}` only for an empty file list,
  which cannot coexist with a non-empty candidate list; `ledger_net_effect` on a missing or empty
  ledger returns `False` → exit 2 (both covered by self-test cases 31–32);
  `verify-schema.sh:117-121` still refuses an empty source file.
- **`ts-comment-spans.mjs`.** `959811f` changed only the header sentence. The claim it now makes
  ("UTF-16 code-unit spans") matches the code and matches the consumer's
  `len(t.encode("utf-16-le")) // 2`. Self-test 9/9. No defect.
- **Sibling sites for the `strip_sql_noise` fix (defect class 4).** Of the six scripts that read
  `supabase/migrations/`, only `check-storage-grant-pin.py` regexes DDL out of it, and it pins a
  SHA-256 of a normalised policy statement in the append-only `0007` — a comment inside that
  statement changes the digest rather than the verdict. Different shape; not a second site.

---

## Verdict

Round 12's four fixes are each correct about the case they name. Three of the six findings above are
the same shape the last four rounds have produced — *"correct about the object named, silent about
the layer beside it"* — and the Blocking is worse than that: it is a guard that, wired as it is
today, has **no observation that can make any pipeline fail**, which is the first defect class on
this repo's own list and the one `CLAUDE.md` opens with.

The Blocking must be fixed before this branch opens a PR. `0027` is already live and M5 is the
milestone that lands the first caller.

NOT CONVERGED
