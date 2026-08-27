# M4 v2 — round 11, CLAUDE half

**Subject:** `14341cf` alone (`git diff c4ba104..HEAD`), 7 files. Branch `docs/m4-round7`.
**Mandate:** adversarial. Independent of the Codex half (`plan-m4-v2-r11-codex.md`, not read).
**Method:** every finding below was **executed**, not read. Commands and outputs are quoted.
**Round 10's premise under test:** `docs/portable-practices.md` §12 — *late-round defects are mostly
caused by the previous round's own fix*. **It held.** The Blocking finding is caused by round 10's
fix, in the gate round 10 was fixing, and the repo already carried a ⛔ warning against the exact
construct — in a sibling file, written before this commit.

**Counts: 1 Blocking · 3 High · 4 Medium · 3 Low.**

**Baseline (so the findings are not confused with a broken tree):** `M4_PHASE=post
./scripts/check-schema-gates.sh` → `✅ all schema gates green`, rc 0. `--self-test`: paid-caller
18/18, run-schema-assertions 15/15, m4-base-db 10/10. **Everything below is green today.** That is
the problem with most of it.

---

## BLOCKING

### B1 — gate 14 now passes over the violation it exists to detect. Round 10's own fix caused it.

`scripts/check-schema-gates.sh:201` (the fix is `scripts/check-schema-gates.sh:183`,
`set -uo pipefail`).

The gate body ends:

```bash
      shopt -s nullglob
      migs=(supabase/migrations/*.sql)
      …
      ! grep -hv "^[[:space:]]*--" "${migs[@]}" | grep -qE "$M4_ASSERT_SIG"'
```

and line 183, added by this commit, is `set -uo pipefail`.

`grep -q` exits on the **first** match and closes the pipe. The producer `grep -hv`, still writing,
dies of **SIGPIPE → 141**. `pipefail` reports the producer, so the pipeline status is **141, not 0**,
and `!` inverts a non-zero into **success**. A detected violation reports GREEN.

**Measured, with the script's actual bytes** — `sed -n '179,201p' scripts/check-schema-gates.sh`
spliced into a driver carrying the real `run()`, against a tree where `05_assert.sql` has been
appended to `supabase/migrations/0027_stable_blob_addressing.sql`:

```
═══ 14/14 05_assert.sql is NOT in any migration (arbitrary-SQL executor + profile deleter) ═══
SUITE fail=0
DRIVER rc=0
```

No `❌ FAILED`. The gate is green while a migration queued for **production** contains
`execute p_sql` (an arbitrary-SQL executor) and `delete from profiles`.

Direct status trace on the same tree:

```
  raw pipeline rc=141
  negated rc=0
SCRIPT rc=0
```

**`pipefail` is the cause, not a coincidence** — same tree, same corpus, 8 runs each:

```
== WITH pipefail (r10's committed shape) — 8 runs
0 0 0 0 0 0 0 0    <- 0 = FALSE GREEN
== WITHOUT pipefail (the pre-r10 shape) — 8 runs
1 1 1 1 1 1 1 1    <- 1 = correct FAIL
```

**Which violations now escape** (each = one mutation of the real migration corpus, gate rc):

| mutation | rc | verdict |
|---|---|---|
| clean tree (control) | 0 | pass — correct |
| **full `05_assert.sql` appended to `0027`** | **0** | **MISSED** |
| **one `assert_raises` line added to `0001_core_schema.sql`** | **0** | **MISSED** |
| one `assert_raises` line added to `0027` (last file) | 1 | caught |
| `delete from profiles;` added to `0027` (last file) | 1 | caught |

It catches only violations near the **end** of the corpus. The more of `05_assert.sql` leaks, and the
earlier it lands, the more certain the gate is to pass. The gate's own header at
`scripts/check-schema-gates.sh:157` still records `0027 with 05 appended .......... 164 (must catch
it)` — that documented mutation control **no longer holds against the committed code**, and nothing
re-ran it.

**⛔ The repo had already measured this exact failure and written it down.**
`scripts/run-schema-assertions.sh:112-122`, present at `c4ba104` (line 103), **before** this commit:

```
  # ⛔ AND DO NOT REINTRODUCE `printf … | grep -q` HERE. MEASURED 2026-08-26:
  #
  #     set -o pipefail; printf '%s' "$big" | grep -Eqi 'raise exception'   ->  rc 141
  #     set -o pipefail; printf '%s' "$small" | grep -Eqi 'raise exception' ->  rc 0
  #
  # `grep -q` exits on the FIRST match; once the block exceeds the pipe buffer, `printf` is still
  # writing and dies of SIGPIPE (141), and `pipefail` reports the PRODUCER. So the check inverted
  # on SIZE ALONE … `grep -c` reads all of its input, so there is no early exit to race.
```

Round 10's fix added `set -o pipefail` to a `grep … | grep -q` pipeline in the sibling file. This is
the repo's signature shape — *a physical rule fixed at one site and recurring at a sibling* — and
here the rule was not merely un-generalised, it was **written down, dated the same day, and violated
in the next commit**.

**Fix:** `grep -c`, capture first and match second, exactly as the sibling does:
`hits=$(grep -hv … "${migs[@]}" | grep -cE "$M4_ASSERT_SIG"); [ "$hits" -eq 0 ]`. Do **not** just
drop `pipefail` — that restores the correct verdict by removing the guard that was added for other
reasons. Then re-run the header's own mutation table and record the new numbers.

**What would prove me wrong:** running the spliced real bytes of lines 179–201 against a tree with
`05_assert.sql` concatenated into `0027` and observing `❌ FAILED` / non-zero. I observed
`SUITE fail=0` on every attempt.

---

## HIGH

### H1 — the hand-written comment scanner desyncs on a regex literal containing a quote. Both directions measured, and it is live in the tree today.

`scripts/check-paid-caller-arrival.py:116-147` (`strip_comments`).

The scanner treats `'`, `"` and `` ` `` as string delimiters wherever they appear outside a string:

```python
        if c in "'\"`":
            quote = c
            i += 1
            continue
```

A **regex literal** containing a quote therefore opens a phantom string that runs to the next
matching quote character anywhere in the file, and from that point the scanner's idea of
inside/outside is inverted. r10 H4 fixed the regex's blindness to strings; the replacement is blind
to regexes.

**This construct is in production code right now** — `lib/html-doc/file-response.ts:8`:

```ts
    .replace(/["\\/;]/g, '_')       // quote, backslash, slash, semicolon → _
```

**Direction 1 — FALSE FIRE (a comment reported as a money caller).** The real repo file, plus one
ordinary comment inserted at line 15:

```
⛔ BACKLOG 26 HAS FIRED — 1 production caller(s) reach `record_artifact`:
     lib/file-response.ts:15: // TODO: once record_artifact lands, encode the manifest key here
>>> exit 1
```

This file's own docstring (line 38) says *"a guard that is red when nothing is wrong gets disabled."*

**Direction 2 — FALSE DORMANT over a real call**, i.e. r10 H4's failure class, reintroduced:

```
CASE: JSX apostrophe + glob string '/*' then a REAL call
const label = <p>Don't</p>;
const GLOB = 'src/*';
await sb.rpc('record_artifact');

         production callers: 0   (comments, not callers: 1)
           · lib/x.ts:3: await sb.rpc('record_artifact');
DORMANT — no production caller.
>>> exit 0
```

Line 3 is a live `.rpc('record_artifact')` on the money path, filed as a comment. Both constructs are
ordinary: JSX apostrophes are everywhere in `components/`, and `'src/*'`-shaped glob strings are
everywhere in `scripts/` — the directory **this same commit added** to `PRODUCTION_DIRS`.

**Reachability, measured over the real tree** (not a fixture):

- **14 files** finish the scan **inside a string** — `lib/dig/cloud/parse-dig-section-blob.ts`,
  `lib/dig/companion-doc.ts`, `lib/html-doc/build-doc-html.ts`, `lib/html-doc/file-response.ts`,
  `lib/html-doc/parse.ts`, `lib/html-doc/render.ts`, `lib/markdown-dividers.ts`,
  `lib/summary-completeness.ts`, `lib/transcript-timestamps.ts`, plus 5 under `tests/`.
- **240 real comment lines** across 12 production files are **not stripped**, i.e. are already being
  classified as code. Worst offenders: `lib/dig/companion-doc.ts` (79),
  `lib/html-doc/render-dig-deeper.ts` (56), `lib/html-doc/nav.ts` (29),
  `lib/transcript-timestamps.ts` (19), `lib/html-doc/parse.ts` (17),
  `scripts/check-service-confinement.ts` (7).

The guard reports DORMANT today only because none of those 240 lines happens to contain
`record_artifact`. That is luck, not discipline — and the 18/18 self-test certifies it, because every
fixture is a two-line file with no regex literal, exactly the shape r10 H4 blamed for certifying the
previous version.

**Fix options, in order of preference:** (a) delegate to a real tokenizer — this repo already ships
TypeScript, so `ts.createSourceFile(...).getFullText()` with `ts.forEachChild` / comment ranges gives
the answer for free; (b) if a scanner must stay, add regex-literal state (a `/` is a regex start when
the previous non-space token is an operator, `(`, `,`, `=`, `:`, `[`, `!`, `&`, `|`, `?`, `{`, `}`,
`;`, `return`) and **assert the file ends with `quote is None`**, failing CANNOT RUN if not. That
assertion alone converts all 14 files above from silent misreads into loud refusals.

**What would prove me wrong:** a run of `strip_comments` over `lib/` and `components/` in which zero
files end with a non-`None` quote state and zero `//`-prefixed lines survive stripping. I measured 14
and 240 respectively.

### H2 — `mutate-schema.py` reports SUCCESS over an empty mutation inventory. Same "empty set passes" class as r10 H2, at the sibling in the same commit.

`docs/superpowers/specs/2026-08-03-stable-blob-addressing/mutate-schema.py:997-1035`.

Round 10 H2's finding was *"this gate passed over ZERO input"*, and the fix gave gate 14 a corpus
floor (`[ "${#migs[@]}" -lt 27 ]`). The mutation gate — the one whose entire purpose is proving
guards load-bearing — got the per-anchor count check and **no inventory floor**:

```python
    print(f"{len(results) - bad}/{len(results)} mutations behaved as expected "
```

`grep -n "len(MUTATIONS)|EXPECTED_MUTATIONS|MUTATION_FLOOR"` → nothing but that one line.

**Measured**, real script, `MUTATIONS` monkey-patched to `[]`:

```
real MUTATIONS: 58
control: unmutated schema verifies ✅
0/0 mutations behaved as expected (RED, or GREEN where documented as subsumed)
baseline restored: GREEN ✅
EMPTY-INVENTORY RUN rc = 0
```

Exit 0 — gate 2 of 14 reports green having tested nothing. A truncated `MUTATIONS` literal (a bad
merge, a stray `]`, an editor accident) is silent. Note this is *not* protected by the count check
that round 10 added: `n != 1 → INVALID` only fires for anchors that are *present in the list*.

**Fix:** `MUTATION_FLOOR = 58` beside the list, with the same "raising is routine, lowering is
deliberate" note the two assertion floors already carry, and `return 2` below it.

**What would prove me wrong:** an empty-inventory run exiting non-zero. It exits 0.

### H3 — the anti-rot ledger cannot see the rename its own docstring names.

`scripts/check-paid-caller-arrival.py:79-80`.

```python
DEFINES = re.compile(rf"create\s+(or\s+replace\s+)?function\s+(public\.)?{SYMBOL}\b", re.IGNORECASE)
DROPS   = re.compile(rf"drop\s+function\s+(if\s+exists\s+)?(public\.)?{SYMBOL}\b", re.IGNORECASE)
```

The docstring at line 70 states the failure being guarded: *"a future `0028` **renaming** or dropping
the function leaves it green and the script reports DORMANT for a symbol that no longer exists."*
`ALTER FUNCTION … RENAME TO` is the canonical rename and matches neither regex.

**Measured**, `ledger_net_effect` against a two-file fixture ledger:

| `0028` contains | verdict |
|---|---|
| `alter function public.record_artifact(uuid, text) rename to record_artifact_v2;` | **exists=True → guard proceeds, can report DORMANT** |
| `drop routine if exists public.record_artifact(uuid);` | **exists=True → guard proceeds, can report DORMANT** |
| `do $$ begin execute 'drop function public.record_artifact(uuid)'; end $$;` | exists=False → CANNOT RUN (correct, by luck — the string matched) |
| `drop function record_artifact(uuid);` (control) | exists=False → CANNOT RUN (correct) |

The live catalog covers this **when Docker is reachable**, which is the mitigation and the reason
this is High rather than Blocking — but the ledger is the authority in CI, where Docker is not up,
and CI is where an unnoticed rename would sit longest.

**Fix:** add `alter\s+(function|routine)\s+(public\.)?{SYMBOL}\b[^;]*\brename\s+to\b` to `DROPS`, add
`routine` as an alternative to `function` in both patterns, and add both as self-test cases.

**What would prove me wrong:** `ledger_net_effect` returning `exists=False` for an `ALTER … RENAME
TO` ledger. It returns `True`.

---

## MEDIUM

### M1 — gate 14's `>= 27` floor is pinned to this branch; it is a hard CANNOT RUN on `master`.

`scripts/check-schema-gates.sh:196`. Measured:

```
migrations on master: 26
migrations on HEAD:   27
```

The floor is `27` and today's count is exactly `27` — zero margin in the only direction that can
move. Any pre-`0027` checkout, `master` included, gets
`CANNOT RUN — read 26 migration(s) … expected at least 27`, and `run()` turns that into
`fail=1`. The script has an explicit `M4_PHASE=pre` branch and a documented pre-promotion phase;
this floor makes gate 14 unrunnable in any tree where `0027` is not yet committed. `supabase
migration squash` would do the same thing on any branch.

**Fix:** derive the floor rather than hardcode it — the failure to guard against is *an unmatched
glob*, so `[ "${#migs[@]}" -eq 0 ]` is the honest test, plus a `[ -f supabase/migrations/0001_core_schema.sql ]`
sentinel to prove the directory is the real one. See `hardcode-only-what-fails-loudly`: hardcode what
announces its own wrongness; a count that legitimately changes is not that.

**What would prove me wrong:** the gate exiting 0 from a `master` checkout. It exits 2.

### M2 — `read_catalog` now refuses a MISSING marker but still accepts an EMPTY parse, and its own comment names the rule it does not enforce.

`scripts/m4_base_db.py:114-125`. The added comment cites CLAUDE.md — *"a parse that found nothing …
must fail loudly"* — and then guards only `marker not in p.stdout`. A query that emits the marker and
**zero rows** still returns an empty string, and none of the three callers has a row floor:

- `scripts/check-guard-coverage.py:228-230` — `return {ln.split(":",1)[1] for ln in out.splitlines() if …}`
- `scripts/check-sentinel-meanings.py:139-146` — `cols = set()` … then filters
- `scripts/check-vocabulary-collisions.py:110-117` — `cols = []` … then filters

Zero rows ⇒ empty set ⇒ "0 guards, all classified" ⇒ **green**. Reachable whenever the catalog query
narrows without noticing (a `table_name in (…)` list that drifts from the schema is the obvious
route). This is the same class as B1 and r10 H2, in gates 3, 4 and 5.

**Fix:** the floor belongs in the one place the function was extracted to be — after the marker
check, `body = p.stdout.split(marker, 1)[-1]`, and refuse with exit 2 when
`not body.strip()`, plus a per-caller minimum row count.

**What would prove me wrong:** any of the three ratchets exiting non-zero when handed a marker
followed by no rows. All three report a clean pass over the empty set.

### M3 — the new fixtures guard raises CANNOT RUN and `verify-schema.sh` reports it as `❌ schema FAILED`, exit 1 — against its own documented contract.

`docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/05_assert.sql:170-181` raises

```
'CANNOT RUN — only % workspace(s); t_ws and t_w2 are the SAME row (%)…'
```

`verify-schema.sh:8` documents `exit 2 = CANNOT RUN (never a pass)`. But an exception inside the
transaction suppresses `ALL_STATEMENTS_OK`, and `verify-schema.sh:131` answers:

```bash
if ! grep -q ALL_STATEMENTS_OK <<<"$OUT"; then echo "❌ schema FAILED"; exit 1; fi
```

**Measured** against a one-workspace fixture built the same way the file builds `t_ws`/`t_w2`:

```
ERROR:  CANNOT RUN — only 1 workspace(s); t_ws and t_w2 are the SAME row (…0000a1), so the
        cross-tenant assertions would be vacuous. Seed a second workspace.
--- would verify-schema.sh see ALL_STATEMENTS_OK? ---
NO -> verify-schema.sh prints '❌ schema FAILED' and exits 1
```

The block's own comment says the state is reachable on any fresh machine (*"a `db reset` plus one
signup produces exactly that state"*). r10 M3 correctly replaced a false *cross-tenant leak*
accusation with a true diagnosis — and then routed it through a headline that names the wrong
subject again, one layer out. The raised text is visible in the output, which is the mitigation.

**Fix:** have `verify-schema.sh` grep `$OUT` for `CANNOT RUN` before the generic branch, and exit 2
with the raised message.

**What would prove me wrong:** `verify-schema.sh` exiting 2 on a one-workspace database. It exits 1
under the headline `❌ schema FAILED`.

### M4 — `check-paid-caller-arrival.py`'s answer depends on whether Docker happens to be running, and a missing `docker` binary reports the money defect as FIRED.

`scripts/check-paid-caller-arrival.py:196-219`.

`live` is preferred unconditionally, and `live_catalog_has` returns `False` — not `None` — when the
query **succeeds** and finds nothing. Measured against the live container for an absent symbol:

```
0
psql rc=0  -> live_catalog_has returns False -> report() prints CANNOT RUN, exit 2
```

So on any machine where the stack is up and `0027` is **not applied** — every developer before
promotion, and production today — this guard is a permanent CANNOT RUN, and the ledger's correct
answer (`0027 creates it`) is discarded. With Docker down it falls to the ledger and answers
DORMANT. Same repo, same commit, two different verdicts decided by whether a container is running.

Second, `subprocess.run(["docker", …])` is unguarded. Measured with an empty `PATH` prefix:

```
REAL exit code with no docker on PATH: 1
FileNotFoundError: [Errno 2] No such file or directory: 'docker'
```

Exit 1 is documented at line 8 as `FIRED — a production caller exists. Backlog 26 must be closed
FIRST.` A missing binary is loud (a traceback), so this will not be believed silently — but the
script's contract is violated, and any caller reading only the exit code gets the wrong answer.

**Fix:** wrap the `subprocess.run` in `except (FileNotFoundError, OSError): return None`; and treat
"live says absent while the ledger says present" as the **pending-migration** case it is — print the
disagreement (the code already does) and use the ledger, reserving CANNOT RUN for the case where both
agree the symbol is gone.

**What would prove me wrong:** the script exiting 2 with no `docker` on PATH. It exits 1.

---

## LOW

### L1 — a `119` left behind by the `119 → 120` change.
`scripts/run-schema-assertions.sh:316`: *"`$OUT` is ~15 KB today because the corpus emits 119
notices."* The commit updated the floor and three other `119`s and missed this one. Both gates
measured **120** today (quoted below).

### L2 — one env var now disarms both assertion floors, and this commit created the sharing.
`verify-schema.sh:151` newly adopts `ASSERTION_FLOOR="${M4_ASSERTION_FLOOR:-120}"`, the same name
`run-schema-assertions.sh:77` already used. An ambient `M4_ASSERTION_FLOOR=0` disables the floor in
gate 1 **and** gate 8 — i.e. every assertion floor in either phase — from a single export.
`check-schema-gates.sh` does not pin it. Both do announce the floor they used, which is the
mitigation. If the two floors are meant to be independently settable they need distinct names; if
they are meant to move together, say so where they are defined.

### L3 — the CANNOT-RUN health check is counted as one of the "120 assertions".
The fixtures guard's `raise notice 'ok (fixtures): …'` matches `NOTICE:.*\bok\b`, which is precisely
why the floors moved 119 → 120. It is a *precondition check*, not an assertion, so the floor's
subject is now "119 assertions plus one fixture health check". Harmless today; it means a future
author who converts the guard to a silent form will see the floor fail with the message *"assertions
STOPPED EXECUTING"*, pointing at the wrong file. One sentence beside the floor fixes it.

---

## Verified and clean — the nine fixes, item by item

The lead asked nine specific questions. Eight got a measurement; the answers that are **not**
findings are recorded here so the next round does not re-derive them.

1. **`mutate-schema.py` count check** — sound. `n = original.count(find); if n != 1: INVALID` makes
   an ambiguous `replace(…, 1)` unreachable: `originals[target]` is the same text that is written
   back (`copy_of[target].write_text(original.replace(find, repl, 1))`), and in the post-`0027`
   redirect both `GEN` and `ART` map to the same `mig_text`, so the count's subject is the file that
   is actually mutated. **All-INVALID does not report success** — `INVALID` is absent from
   `ok = {"RED", "RED(constraint)", "RED(trigger)", "GREEN(expected)"}`, so every INVALID increments
   `bad` and the run exits 1. *Zero*-length does — see **H2**.
2. **gate 14 quoting** — the `'"$SPEC"'` splice is safe: `$SPEC` is expanded by the outer shell
   inside double quotes and contains no whitespace or metacharacters, so the inner text is a literal
   `assert_src="docs/…/schema/05_assert.sql"`. The subject check and the corpus check use different
   files **by design** (margin vs. corpus) and both are relative to `pwd`, so a failed `cd` fails
   both closed. **`export M4_ASSERT_SIG` does not leak into other gates** — it is assigned at line
   179, after gates 1–13 have already run, and nothing else reads the name. The signature matches
   **164 lines** of `05_assert.sql` (`execute p_sql` 1 + `delete from profiles` 1 + `assert_raises`
   62 + `ASSERTION FAILED` 100 — line count and occurrence count coincide), so the `>= 100` floor
   has real margin. `27` does rot — **M1**.
3. **anti-rot subject** — `sorted()` matches Supabase's apply order for both the `0001…0027` and the
   timestamp naming conventions (`0001…` sorts before `2026…`). Create-and-drop on one line is
   handled correctly, because the comparison is on **character offsets** (`m.start()`), not lines;
   `create or replace` after a drop likewise. The live/ledger disagreement path prints and trusts
   live. The vocabulary is the gap — **H3**; the live-preference and the missing-Docker path are
   **M4**.
4. **`strip_comments`** — **H1**.
5. **`scripts/` in `PRODUCTION_DIRS`** — fires on nothing today (real run: `production callers: 0`,
   `tests: 0 caller(s), 2 comment(s)`). It does **not** scan itself: `SUFFIXES = (".ts", ".tsx")`
   excludes every `.py` in `scripts/`. The two comment hits are the two documented lines in
   `tests/lib/blob-addressing-caller-contract.test.ts:16,22`, matching the docstring's claim of TWO
   (not backlog 26's prose claim of one).
6. **`verify-schema.sh` floor** — ⚠ **I RAN THE PRE-0027 PATH THE LEAD FLAGGED AS UN-RUN.**
   `M4_MIGRATION=/nonexistent/0027.sql ./verify-schema.sh` →
   `✅ schema verified (rolled back) — 120 assertions ran (floor 120)`, rc 0. The floor is **not**
   unsatisfiable on the spec-file corpus. Post path: identical, `120`, rc 0. `$OUT` carries no
   ok-notices from anything but `raise notice` — `RAN` uses `grep -c` over a here-string, so it is
   not exposed to B1's SIGPIPE race.
7. **`05_assert.sql` fixtures block** — **ordering is correct**: the guard is lines 170–181
   (`do $$ declare a uuid; …` through `end $$;`) and the first `t_ws`/`t_w2` consumer is line 185
   (`insert into workspace_videos (workspace_id, video_id) select id, 'vidA' from t_ws;`), so it runs
   before every one of them. Its `raise notice 'ok (fixtures): …'` does match `NOTICE:.*\bok\b`, and
   that is load-bearing: the commit claims it is the entire 119 → 120 delta and I verified the
   `120` end of that (both gates, both source paths) but not the `119` end. Noted as **L3**; the refusal path is
   **M3**.
8. **`m4_base_db.read_catalog` exit 2** — **no caller depended on the old behaviour.** All three
   (`check-guard-coverage.py:228`, `check-sentinel-meanings.py:139`,
   `check-vocabulary-collisions.py:110`) discard lines lacking their prefix, so the old whole-output
   parse produced an empty set. Exiting 2 is strictly better. The residue is **M2**.
9. **Both floors 119 → 120** — **120 is right, and confirmed on both gates and both source paths**:
   gate 1 post `120`, gate 1 pre `120`, gate 8 `120 assertions passed against the live schema (floor
   120)`. Margin is exactly zero in both, which is the intended ratchet. No path produced a different
   count.

**Not re-reported, per the brief:** the SIGTERM/SIGKILL base leak (task #145 — I checked and no base
leaked from any of my runs: `select datname from pg_database where datname like 'm4_%'` returned
nothing), the `--expect-present` added-column asymmetry.

---

## The shape of this round

Round 10's verdict was *"a guard that cannot fail, and four of five sat beside a sibling in the same
commit that got the discipline right."* Round 11 finds the same sentence, one turn later:

- **B1** — the sibling (`run-schema-assertions.sh:112`) carries a ⛔ warning, measured on the same
  date, naming this construct and this exit code. The fix walked into it.
- **H2** — the sibling (gate 14) got a corpus floor in this commit; the mutation gate did not.
- **M2** — the marker guard was added to the shared function and the emptiness rule it cites was not.
- **H3** — the docstring names "renaming" as the failure; the regex covers dropping.
- **H1** — one class of literal (strings) learned about; the neighbouring class (regexes) not.

Five of eight findings are *"the rule was applied at the site that was being looked at, and not one
step further."* §12's claim is confirmed for `14341cf`, and I would add a sharper version worth
carrying into `portable-practices.md`: **when a round's fix introduces a construct, grep the repo for
an existing ⛔ about that construct before committing.** B1 would have cost one `grep -rn 'grep -q'`.

---

## NOT CONVERGED
