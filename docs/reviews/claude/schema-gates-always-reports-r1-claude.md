# Claude adversarial review — `schema-gates-always-reports`, round 1

**Subject pinned by execution.** Commit reviewed: **`3a2fc5e3`** (`3a2fc5e399939e9c54568fdf6f43eb283b85e21f`),
branch `schema-gates-always-reports`, PR #315, base `master` = `93c815c8`.

```
$ git log --oneline -3
3a2fc5e3 Round 1 found the fail-open this branch had only declared, and the fix is a class fix (backlog #137)
839bc738 Fifteen schema gates reported red into a void, and the filter protecting them was buying nothing (backlog #137)
93c815c8 File #137: schema-gates can report red and the PR merges anyway (#314)

$ git diff 93c815c8..3a2fc5e3 --stat
 .github/workflows/schema-gates.yml                 | 134 ++++-----
 docs/backlog.md                                    |   2 +-
 docs/dashboard-entries.md                          |  96 ++++++
 docs/dev-process.md                                |   2 +-
 .../codex/schema-gates-always-reports-r1-codex.md  |  33 ++
 ...hema-gates-always-reports-r1-codex.verdict.json |  16 +
 scripts/check-plan-code.py                         |  52 +++-
 scripts/check-review-recorded.py                   | 332 ++++++++++++++++++---
 scripts/mutations/check-review-recorded.json       | 133 +++++++--
 9 files changed, 639 insertions(+), 161 deletions(-)

$ git rev-parse HEAD
3a2fc5e399939e9c54568fdf6f43eb283b85e21f
$ git status --short        # empty — nothing in this review modified a tracked file
```

All mutation work was done on a symlink mirror under the session scratchpad
(`scratchpad/mirror`, `scratchpad/m2`), never in the repository. ⚠ Note for anyone repeating
this: in such a mirror only the file you *copy* resolves `ROOT` to the mirror; every
*symlinked* script resolves `__file__` through the link and measures the real repo. That
invalidated my first attempt at Finding 10 and is why `m2` exists.

Counts: **1 Blocking · 4 High · 6 Medium · 3 Low.** Verdict at the end.

---

## BLOCKING 1 — `--mutate .` REFUSES this branch: three mutation entries share one anchor, and the whole 719-entry harness goes dark (VERIFIED)

`scripts/mutations/check-review-recorded.json` — the three entries named
*"the gate-data suffix filter goes…"*, *"the EXISTENCE filter goes…"* and *"the prose-suffix
rule goes…"* all anchor on the **same single line**, `scripts/check-review-recorded.py:397`:

```py
            if suffix and suffix != PROSE_SUFFIX and "/" in p and is_file(p):
```

`scripts/check-plan-code.py:1019` keys the duplicate-anchor refusal on the `old` half only —
`anchors = tuple(f for f, _ in e.get("edits", []))` — so all three collide, and
`:1047` refuses the second and third. `:1098` then returns before any mutation runs:

```py
    if problems:
        return False, problems, NotMeasured.from_counts([], None, ev_files)
```

**Executed, on the real repository:**

```
$ python3 scripts/check-plan-code.py --mutate .
  ✗ check-review-recorded.json: entry 'the EXISTENCE filter goes, so a bound REGEX is reported as an uncovered gate directory' repeats the edit anchors of an earlier entry — it measures nothing new
  ✗ check-review-recorded.json: entry 'the prose-suffix rule goes, so a .md a gate merely reads becomes gate machinery' repeats the edit anchors of an earlier entry — it measures nothing new
NOT MEASURED — the mutation harness produced no coverage verdict. Treat this as NOT CHECKED.
EXIT=1
```

And driving `load_manifests` directly (compiled out of `check-plan-code.py` by `ast`, so this is
the shipped function, not a re-implementation):

```
entries accepted: 719
problems: 2
accepted entries for check-review-recorded.py: 48
declared EXPECTED_MUTATIONS for it: 50
```

**Why this is Blocking, not Medium.** `.github/workflows/ci.yml:390` runs
`python3 scripts/check-plan-code.py --mutate .` inside `verify` — the **one required status
check**. So:

1. `verify` goes **red** on this branch. Under this repo's own rule (*a red check is a STOP*)
   the branch is not mergeable as it stands.
2. The failure is **global**, not local: `--mutate .` refuses before staging, so **zero of the
   719 mutations across every target run**. The branch whose entire purpose is making a gate's
   answer consumable ships a state in which the repository's largest gate measures nothing.
3. It is inside the round-1 fix. `839bc738` had 47 entries; `3a2fc5e3` added three, two of which
   are the collision. The Codex half's High was repaired by adding entries that turn the harness
   off — this project's recorded pattern of the fix carrying the next defect.

Note the second-order damage: even after the collision is broken up, `EXPECTED_MUTATIONS
["scripts/check-review-recorded.py"] = 50` (`check-plan-code.py:820`) and the declared sum
`721` (`:3217`) were both set against a manifest that the loader reduces to 48. They have never
been checked against the *accepted* population.

**Also substantive, not just mechanical.** Compare the two colliding replacements:

| entry | replacement | removes |
|---|---|---|
| "the gate-data suffix filter goes" | `if "/" in p and is_file(p):` | `suffix and` **and** `suffix != PROSE_SUFFIX` |
| "the prose-suffix rule goes" | `if suffix and "/" in p and is_file(p):` | `suffix != PROSE_SUFFIX` only |

Both name the **same** `expect` case. The first is strictly weaker than the second — it is killed
entirely by the half the second already covers — so it adds no coverage even if the anchors were
split. Measured: removing **only** `suffix and` leaves the suite green (see Finding 3), so the
clause the first entry appears to defend is in fact unfalsified. The count 50 overstates distinct
coverage.

**Observation that proves it fixed:** `python3 scripts/check-plan-code.py --mutate .` exits 0 with
a coverage verdict, and `load_manifests(ROOT)[1]` is `[]`.

---

## HIGH 2 — the gate-script discovery the whole redesign rests on has NO falsifier: delete it entirely and the suite stays 153/153 (VERIFIED)

`scripts/check-review-recorded.py:415`, inside `_gate_sources`:

```py
    for rel in sorted(set(re.findall(r"(?:\./)?(scripts/[\w.-]+\.(?:py|sh))", uncommented))):
```

This loop is the branch's central claim. `schema-gates.yml:70` says *"The falsifier now derives
those directories from the scripts that actually EXECUTE the files"*, and `gate_code_dirs`'s
docstring calls prong 2 *"what recovers `docs/superpowers/specs/m4/`"*.

**Mutation, executed on the mirror (control green at 153/153 first):**

```
  *** SURVIVED ***   rc=0  sources: only the runner (no gate scripts)
       153/153 passed
```

(the mutation replaces the `for rel in sorted(set(re.findall(...)))` iterable with `[]`, so
`_gate_sources` returns the runner alone.)

What that costs, measured against the live tree:

```
=== derivation if _gate_sources returned ONLY the runner ===
  derived: ['docs/superpowers/specs/2026-08-03-stable-blob-addressing']
  non-empty (CANNOT-RUN guard satisfied)? True
  prose_exceptions_cover -> []   => main prints nothing, rc continues
  lost vs full: ['docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema',
                 'docs/superpowers/specs/m4']
```

**Two of the three directories vanish, the result stays non-empty so the CANNOT-RUN guard at
`:1049` is satisfied, `prose_exceptions_cover` returns `[]`, and the gate reports success.**

**The root cause is that neither live case can see under-coverage.** `self_test` has exactly two
live cases for this mechanism (`:1171`, `:1173`):

```py
    case("the docs/ gate directories are DERIVED from the real gate scripts, not transcribed here",
         bool(_GS) and gate_code_dirs(*_GS, is_file=_real_file) != [], True)
    case("...and every one of them is exempt from the prose classifier",
         prose_exceptions_cover(gate_code_dirs(*_GS, is_file=_real_file)) if _GS else [], [])
```

The first asserts **non-empty** — prong 1 alone satisfies it. The second asserts **nothing
uncovered** — and under-coverage makes that *more* likely to pass, not less. So the property the
mechanism exists for ("the derivation sees every `docs/` directory holding gate machinery") is
asserted by no case at all, and no manifest entry targets `_gate_sources` either (I enumerated all
50: the only entries touching the new code are the three colliding suffix/existence ones plus
`_joined_path`, the two readers and prong 1).

This is **r16's High reproduced inside the mechanism built to prevent it**. r16 found the falsifier
was *"fed a transcription, not the workflow"*. The authority has moved from a transcription to a
derivation — and the derivation's completeness is now the unchecked copy. The header at `:245-247`
still claims the r16 lesson is discharged.

**Observation that would prove it fixed:** a case that pins the derived set against an
independently-stated expectation (e.g. *the derived set contains every directory in
`CODE_UNDER_PROSE`*, which is falsifiable in the under-coverage direction), such that emptying
`_gate_sources`' discovery loop turns the suite red.

---

## HIGH 3 — a `docs/` directory BOUND by a gate is invisible; today's coverage of `.../schema` is an accident of one shell line (VERIFIED)

`scripts/check-review-recorded.py:395-397`. A bound path with no file suffix is rejected by
`if suffix and …`, and `is_file` is False for a directory, so **prong 2 cannot see a gate that
binds a directory and globs inside it.** That is not a hypothetical shape — it is the *dominant*
shape in this repository. Measured, per source:

```
scripts/check-anon-exposure.py
   binds ['docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema', 'docs/superpowers/specs/m4/live-manifest.txt']
   alone derives -> ['docs/superpowers/specs/m4']
scripts/check-sentinel-meanings.py
   binds ['docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema', ...]
   alone derives -> []
scripts/check-vocabulary-collisions.py
   binds ['docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema']
   alone derives -> []
scripts/mutate-live-schema-check.sh
   binds ['docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema']
   alone derives -> []
scripts/check-guard-coverage.py
   binds ['docs/superpowers/specs/2026-08-03-stable-blob-addressing']
   alone derives -> []
```

**Five gate sources bind those two directories and not one of them derives either.** The
`.../schema` directory is in the derived set solely because `run-schema-assertions.sh:46` happens
to bind one `.sql` file *inside* it. Remove that single source and the directory disappears while
five gates still execute code out of it:

```
=== drop run-schema-assertions.sh (the ONE .sql binding) ===
  derived: ['docs/superpowers/specs/2026-08-03-stable-blob-addressing', 'docs/superpowers/specs/m4']
  '.../schema' still there? False
```

And the direct shape, driven with a fixture:

```
=== C: gate binds a DIRECTORY and globs inside it ===
  gate_code_dirs -> []  <-- INVISIBLE
  is_prose('docs/newgate/rules/01.sql') -> True
  guarded_changes(['docs/newgate/rules/01.sql']) -> []
```

Worse, `run-schema-assertions.sh:46` is itself fragile — the binding the whole directory hangs on
is a **default inside a parameter expansion**:

```sh
ASSERT="${ASSERT_FILE:-$REPO/docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/05_assert.sql}"
```

Make `ASSERT_FILE` mandatory, or move the literal into a `local`, and `.../schema` silently leaves
the derived set. This is the *case can pass for an AMBIENT reason* shape at the derivation level:
the coverage is real today and rests on nothing that says so.

The clause is also unfalsified — see Finding 12 (`dirs: \`suffix and\` removed` SURVIVED).

**Fix direction:** `is_file` answers *is this a path*, and the author's own docstring says so. A
directory is a path. The predicate wants `exists`, not `is_file` — and the self-test case that
motivates the injection (*"a bound string that is a REGEX … is rejected because it does not
exist"*, `is_file=lambda rel: False`) is satisfied identically by `exists`.

---

## HIGH 4 — Codex's r1 High is NOT closed as a class: gate data one level under `docs/` is still silently prose (VERIFIED)

The fix separated two axes — `.md` answers *is it prose*, existence answers *is it a path*. It did
not touch a third: **depth**. `prose_exceptions_cover:228`

```py
        if not prefix.startswith("docs/"):
            continue
```

A derived directory of exactly `docs` does not start with `docs/`, so it is **silently skipped** —
not reported, not refused. Meanwhile `PROSE_DIRS = ("docs/",)` (`:148`) makes anything directly
under `docs/` prose. Executed:

```
=== A: gate data file directly under docs/ (depth 1) ===
  gate_code_dirs -> ['docs']
  prose_exceptions_cover -> []          <-- [] means NO RED
  is_prose('docs/gate-rules.json') -> True
  guarded_changes(['docs/gate-rules.json']) -> []

=== B: the same thing one level deeper (the shape that DOES work) ===
  gate_code_dirs -> ['docs/newgate']
  prose_exceptions_cover -> ['docs/newgate']   <-- RED, correct
```

This is **exactly the Codex finding's structure**: a non-empty derived set satisfies the CANNOT-RUN
guard while the new gate's directory is invisible, `CODE_UNDER_PROSE` is never forced to grow, and
a later PR editing that gate's data classifies as prose and owes no review round. Only the axis
changed — suffix → depth.

It is reachable by three independent routes, so it is not a corner:

1. a new gate binding `docs/<something>.json` / `.txt` / `.sql` directly;
2. `_joined_path` collapsing a variable segment (Finding 5): `ROOT / "docs" / sub / "rules.json"`
   → `docs/rules.json` → dir `docs`;
3. it already happens in the wider corpus — `scripts/publish-arch-page.sh` yields `docs` under the
   same rule:
   ```
   Dirs the wide corpus finds that the 13-source corpus does NOT: ['docs']
   ```

`839bc738`'s own commit message and the workflow header claim this was fixed *"as a CLASS rather
than by adding `.json` and waiting for the next suffix."* That claim is too strong: one axis of the
class was fixed.

---

## HIGH 5 — `_joined_path` splices across variable segments: it FABRICATES paths and loses real ones (VERIFIED)

`scripts/check-review-recorded.py:283-290`. `walk` appends every string constant in the `/` chain
and ignores non-string leaves, then joins. The docstring says *"Non-string leaves (`ROOT`, a call, a
variable) contribute nothing, so `DOCSDIR / name` yields no parts at all"* — true when the variable
is at the **end**, and wrong in both directions when it is in the **middle**:

```
=== E: _joined_path with a VARIABLE segment in the middle ===
 P = ROOT / "docs" / "superpowers" / "specs" / name / "live-manifest.txt"
     _joined_path -> 'docs/superpowers/specs/live-manifest.txt'
 P = ROOT / "docs" / sub / "rules.json"
     _joined_path -> 'docs/rules.json'
```

Both directions are defects:

* **silent miss** — the real directory (`docs/superpowers/specs/<name>`) is never derived; the
  fabricated path does not exist, `is_file` drops it, and the gate reports success. A gate
  parameterised by spec name is ordinary.
* **wrong attribution** — a fabrication that *does* exist is accepted. `ROOT / "docs" /
  "superpowers" / "specs" / v / "m4" / "live-manifest.txt"` collapses to the real
  `docs/superpowers/specs/m4/live-manifest.txt`, attributing a gate to a directory it does not
  read. `is_file` cannot distinguish that from a true binding.
* **route into Finding 4** — `docs/rules.json` yields the depth-1 dir `docs`, which is skipped.

A variable segment means *unknown*, and the function should return `None` rather than splice. The
self-test pins only the all-variable case (`:1253`, *"a join built only from variables invents no
path"*), and its own comment records that the case's first name was wrong — the author corrected the
**name** and never added the **mixed** case, which is where the behaviour is actually wrong.

**Observation:** `_joined_path` on `ROOT / "docs" / "a" / v / "r.json"` returns `None`.

---

## MEDIUM 6 — `_gate_sources` is one level deep, and its regex cannot match a script in a subdirectory (VERIFIED)

`:415`'s regex is `scripts/[\w.-]+\.(py|sh)` — `[\w.-]` excludes `/`, and it is applied to the
**runner only**, never transitively. Three concrete consequences:

* **helpers four gates delegate to are not authorities.** `scripts/build-m4-schema.py` and
  `scripts/m4-base-db.sh` are invoked by `run-schema-assertions.sh:263`,
  `mutate-live-schema-check.sh:183,191`, `gen-m4-manifest.py:263,274` and
  `verify-exclusion-reasons.py:279,285`. Neither is in `sources` (verified: `'build-m4-schema.py'
  in sources` → `False`). They bind no `docs/` path today, so this is latent, not live.
* **a helper that DOES bind one is already invisible.** `scripts/subject_status.py:163` binds
  `docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema`
  (`bound_docs_paths(...)` → `['docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema']`)
  and is not in `sources`.
* **making it transitive would not be enough.** `gen-m4-manifest.py:194,274` and
  `verify-exclusion-reasons.py:285` invoke helpers via `os.path.join(REPO, "scripts",
  "build-m4-schema.py")`, which contains no `scripts/…py` substring at all. And
  `scripts/ci/start-schema-db.sh` — which builds the database all fifteen gates run against, named
  at `schema-gates.yml:186` — can never match, because of the `/`.

A missed source is a missed authority, and the failure is silent.

## MEDIUM 7 — the shell reader misses `export`, `local`, `declare`, `readonly`, `+=` (VERIFIED)

`:341`'s `re.match(r"\s*[A-Za-z_]\w*=", line)`:

```
  export X=    -> []
  local X=     -> []
  X+=          -> []
  declare      -> []
  readonly     -> []
  array        -> ['docs/superpowers/specs/x/r.sql']
  indented     -> ['docs/superpowers/specs/x/r.sql']
```

The docstring calls this *"enough for the two real cases (`SPEC=`, `SEED=`) and honest about being a
scan rather than a parse"*. `local` and `export` are not exotic shell — `run-schema-assertions.sh`
is 300+ lines with functions, and one refactor moving `SEED=` inside a function as `local SEED=`
silently removes `docs/superpowers/specs/m4` from the derivation. Given Finding 2 (no case sees
under-coverage) nothing would report it.

Separately, `line.split("#")[0]` mangles a `#` inside quotes — `SPEC="docs/…/x#1/r.sql"` truncates
to `docs/superpowers/specs/x`. No current gate has one; noted as Low-value.

## MEDIUM 8 — `bound_docs_paths` fails open on an unparseable gate script (VERIFIED)

`:320-322` returns `[]` on `SyntaxError`:

```
=== a gate script the falsifier cannot parse ===
  bound_docs_paths -> []      (silent [] -- no CANNOT RUN, no warning)
```

The file applies *a zero over nothing is not a pass* to the **aggregate** (`:1046-1054`) but not
**per source**: one unparseable gate contributes zero while the others keep the total non-empty.
Realistic trigger: a gate script using syntax newer than the interpreter running the falsifier
(`ci.yml` pins 3.12 for one job; a contributor's local run may be older). A per-source
`SyntaxError` should be a refusal or at minimum a warning, not silence.

## MEDIUM 9 — four surviving claims in the shipped file still assert the deleted path filter is the authority

The workflow header is emphatic that the filter must not be rebuilt for this reader
(`schema-gates.yml:67`: *"DO NOT SOLVE THAT BY LEAVING A DECORATIVE PATH LIST HERE FOR IT TO
READ"*). The code it guards still tells the next reader to do exactly that:

* `check-review-recorded.py:160` — *"`.github/workflows/schema-gates.yml:80-81,103-104` lists both
  directories as PATH-FILTER TRIGGERS — the workflow itself declares them gate subjects."* Verified:
  the file has no path filters, and those lines are now unrelated prose (`:80-81` is the historical
  account of r1 BLOCKING 2; `:103-104` is schedule prose). A stale line-citation pointing at
  different content.
* `:177-182` — *"this tuple can drift from `schema-gates.yml`… `prose_exceptions_cover()` below is
  the falsifier… it takes the workflow's globs as an argument, and its case feeds it the real
  ones."* None of that is true any more.
* `:215-224` — `prose_exceptions_cover`'s signature is still `workflow_globs`, and its docstring
  still says *"`schema-gates.yml` path-filters on the directories whose contents are gate
  subjects"*. This is the function `main` now calls with derived directories.
* `:1147` — *"both executed by `check-schema-gates.sh` and both named in `schema-gates.yml`'s path
  filters"*.

Not cosmetic in this repo: `CLAUDE.md` imports `dev-process.md`, whose own budget note says a
restatement is *"a second copy that drifts"*, and these four are the drifted copies of the authority
this branch moved.

## MEDIUM 10 — the workflow's justification for requiring the context rests on a false premise, and the counterexample has ZERO slack (VERIFIED)

`.github/workflows/schema-gates.yml:58-60`:

> *"The job's verdict does not depend on the diff (it rebuilds the same database from the same
> migrations), which is why the record is expected to transfer."*

False for three of the fifteen gates, which read the **tree**, not the database: gate 3
(`check-guard-coverage.py`), gate 6 (`check-docs.py`, *documentation integrity*), gate 15
(`check-paid-caller-arrival.py`, whose subject is `PRODUCTION_DIRS` — which the *same file* states
19 lines later). Gate 6's subjects are docs:

```
scripts/check-docs.py binds ['docs/adr', 'docs/backlog.md', 'docs/dev-process.md',
                             'docs/plugins.md', 'docs/reviews/', 'docs/roadmap-to-launch.md', ...]
```

And the margin is **zero**. `check-docs.py:191-194` budgets `docs/dev-process.md` at 220 and
`docs/plugins.md` at 260; both sit exactly at the limit. Executed on a real copy of the tree (`m2`,
with `check-docs.py` copied rather than symlinked so `ROOT` resolves to the copy):

```
--- CONTROL (untouched docs copy) ---
rc=0
budget docs/dev-process.md         :  220 / 220  ok
budget docs/plugins.md             :  260 / 260  ok
--- ONE blank line appended to docs/dev-process.md ---
rc=1
budget docs/dev-process.md         :  221 / 220  OVER
FAILED — 1 documentation integrity error(s):
  ✗ docs/dev-process.md is 221 lines, over its 220-line budget by 1.
```

So a **one-line docs-only edit** — which is what *this branch did to that very file* — turns
`schema-gates` red. Blast radius is contained, because `ci.yml:109` runs the same script inside the
required `verify`, so no PR is newly blocked. But the sentence used to justify requiring the context
is wrong, and the correct justification is a different one: *the only tree-reading gate a docs-only
diff can flip is gate 6, which is already required via `verify`.* Under this project's standard
(*record which build a manual check was verified against*; *a measurement needs its CONTEXT*) the
stated reason should be the true one.

## MEDIUM 11 — `docs/backlog.md:165` ships the pre-fix numbers (VERIFIED)

```
--- numbers in the backlog row ---   1 139→148     1 43→47      1 714→718
--- numbers in the dashboard entry --- 1 47→50     1 153
=== SHIPPED truth ===
manifest entries: 50
scripts/check-review-recorded.py:5:  --self-test  # 153 cases
scripts/check-plan-code.py:3217: ... 721
scripts/check-plan-code.py:820:  "scripts/check-review-recorded.py": 50,
```

The backlog row was written in `839bc738` and states the branch's outcome as manifest 43→47, total
714→718, self-test 139→148. `3a2fc5e3` moved them to 50 / 721 / 153 and updated
`docs/dashboard-entries.md` but not the backlog row, so a reader of the row gets the wrong figures
for the branch. Task #18 (*"Update the docs that assert the filter exists"*) is marked completed.
`check-selftest-counts.py` reads only `scripts/*.py`, so no gate sees this — the same blind spot
`docs/plugins.md` records against itself ("a count with no owner drifts again").

## LOW 12 — inert and unfalsified clauses beyond the one declared (VERIFIED)

The docstring at `:272-281` declares `len(parts) > 1` inert and, correctly, gives it no mutation
entry. Mutation-testing every new clause on the mirror (control green at 153/153 first) found the
declaration incomplete — **12 of 21 mutations survived**:

```
  *** SURVIVED ***  joined: len(parts)>1 -> >0            (declared inert — fine)
  *** SURVIVED ***  joined: Div check removed
  *** SURVIVED ***  py: SyntaxError returns garbage instead of []
  *** SURVIVED ***  sh: NAME= anchored at col 0 only
  *** SURVIVED ***  dirs: spec_dirs dot filter removed
  *** SURVIVED ***  dirs: $SPEC comment strip removed
  *** SURVIVED ***  dirs: `suffix and` removed (no-suffix admitted)
  *** SURVIVED ***  dirs: '/' in p removed
  *** SURVIVED ***  sources: regex misses nothing (any path)
  *** SURVIVED ***  sources: only the runner (no gate scripts)      <-- Finding 2
  *** SURVIVED ***  sources: uncommented -> raw runner
  *** SURVIVED ***  cover: docs/ prefix gate -> no skip
  KILLED (9 others, incl. every clause the manifest names)
```

Of these, `"/" in p` at `:397` is **tautological**, not merely untested: `p` is constructed as
`p[p.index("docs/"):]` at `:333`/`:337`, so it always begins `docs/` and always contains `/`.
Verified over the 18 bound paths the live corpus produces — `any without '/': []`. By the author's
own stated rule a clause whose removal changes nothing cannot carry a mutation entry, so it should
be removed or declared like `len(parts) > 1`. `suffix and` is Finding 3; `sources: only the runner`
is Finding 2. The rest (`Div`, the `spec_dirs` dot filter, both comment strips) are unfalsified but
low value.

## LOW 13 — prong 1 fabricates, hardcodes one variable name, and misses `${SPEC}` (VERIFIED)

`:386-392`. `spec_dirs` accepts **any** directory-valued binding while the regex hardcodes the
name `SPEC`, and every `$SPEC/…` relative path is joined against **every** spec dir:

```
  two dir bindings, one $SPEC use -> ['docs/superpowers/specs/alpha', 'docs/superpowers/specs/beta']
  (expected just .../alpha)
  ${SPEC} brace form -> []
  prong 1 with a NONEXISTENT file -> ['docs/superpowers/specs/alpha/nope']   (prong 1 never calls is_file)
```

Three separate problems: a cross-product fabrication the moment the runner gains a second
directory-valued binding (noisy → false red); total blindness to `${SPEC}/`, which is ordinary shell
(silent → fail-open); and no existence check at all, which is inconsistent with prong 2's entire
premise that existence is what distinguishes a path from a string. Latent today — the runner has
exactly one binding (`check-schema-gates.sh:19`) and uses the bare `$SPEC/` form twice.

## LOW 14 — removing the `push:` filter lets a docs-only merge cancel a code merge's gate run

`schema-gates.yml:151-153` is `group: schema-gates-${{ github.workflow }}-${{ github.event_name
}}-${{ github.ref }}` with `cancel-in-progress: true`. Because `github.event_name` is in the key,
`pull_request` and `push` and `schedule` cannot cancel each other — that part is sound, and the
file already discusses the 08:59/cron collision at `:148`. What is new and undiscussed: **every**
push to master now starts a run, so a docs-only merge landing shortly after a code merge cancels
the code merge's `push` run. Benign in verdict terms (the later commit contains the earlier
changes and the gates do not read the diff for gates 1-2/4-5/7-14), but per-commit attribution is
lost, and the file's *"what is lost, said plainly"* paragraph at `:74-76` does not mention it.

---

## Arguing against the whole change

Asked for, so stated plainly: **the deletion is right and the measurements behind it hold.** I
re-derived the two I could reach.

* *"the only mode-755 files tracked anywhere under `docs/` are exactly those two"* — **confirmed**:
  ```
  $ git ls-files -s docs/ | awk '$1=="100755"{print $4}'
  docs/superpowers/specs/2026-08-03-stable-blob-addressing/mutate-schema.py
  docs/superpowers/specs/2026-08-03-stable-blob-addressing/verify-schema.sh
  ```
* *"the real derivation yields exactly three directories with zero uncovered"* — **confirmed**:
  `['docs/superpowers/specs/2026-08-03-stable-blob-addressing', '.../schema',
  'docs/superpowers/specs/m4']`, `prose_exceptions_cover(...) == []`. I also ran the same rule over
  all 65 tracked scripts and found **no live under-coverage** today.
* the *noisy-direction* claim that killed the first design — **confirmed**: `check-docs.py` binds
  `docs/backlog.md`, `docs/adr`, `docs/reviews/`, `docs/superpowers/`, and
  `check-sentinel-meanings.py` binds a **prose message** containing a path; existence rejects all
  of them.
* the reader is genuinely better than a grep — **confirmed**: a comment-only and a docstring-only
  mention both return `[]`, and the `Assign`-restriction mutation (admitting `Expr`) is killed by
  the docstring case.

The case against requiring the context is weaker than the case for it, with one correction: the
justification at `:58-60` is factually wrong (Finding 10) and the true risk is narrower than the
file states. `verify` already runs `check-docs.py` with zero budget slack, so a docs-only PR that
would red `schema-gates` is already blocked. The remaining exposure is the declared one — an infra
failure (image pull, `npm ci`, docker) blocking a docs-only PR — and that is honestly recorded.

**Ordering is correct and worth restating:** the workflow change must merge *before*
`required_status_checks.contexts` gains `schema-gates`. Reverse order blocks every docs-only PR.

---

## Summary

| # | Sev | Finding | Verified? |
|---|---|---|---|
| 1 | **Blocking** | Three mutation entries share one anchor; `--mutate .` refuses and ALL 719 mutations go unmeasured; required `verify` goes red | executed (`rc=1`) |
| 2 | High | `_gate_sources`' gate-script discovery has no falsifier — delete it and 153/153 stays green while 2 of 3 dirs vanish | executed (mutation) |
| 3 | High | A gate that binds a `docs/` DIRECTORY is invisible; 5 sources do this and `.../schema` survives only via one `.sql` line | executed |
| 4 | High | Codex's r1 High not closed as a class — depth-1 `docs/` gate data is silently skipped and classified prose | executed |
| 5 | High | `_joined_path` splices across variable segments: fabricates paths, loses real ones | executed |
| 6 | Medium | `_gate_sources` is one level deep and cannot match a script in a subdirectory | executed |
| 7 | Medium | Shell reader misses `export`/`local`/`declare`/`readonly`/`+=` | executed |
| 8 | Medium | `bound_docs_paths` returns `[]` on `SyntaxError` — silent per-source fail-open | executed |
| 9 | Medium | Four surviving claims in the shipped file assert the deleted filter is the authority | executed (line check) |
| 10 | Medium | The workflow's diff-independence premise is false; gate 6's budget has zero slack | executed |
| 11 | Medium | `docs/backlog.md:165` ships the pre-fix counts (43→47 / 714→718 / 139→148) | executed |
| 12 | Low | 12 of 21 new clauses unfalsified; `"/" in p` is tautological | executed (mutation) |
| 13 | Low | Prong 1: cross-product fabrication, hardcoded `SPEC`, `${SPEC}` blind, no existence check | executed |
| 14 | Low | A docs-only master merge can now cancel a code merge's gate run | reasoned (workflow read) |

Nothing in this review is reasoned-only except Finding 14's cancellation consequence and the
latent halves of Findings 6 and 13, each labelled where it appears.

**The three I would not merge without:** 1 (the branch is CI-red and the mutation gate is dark),
2 (the branch's central claim is defended by no case), and 4 (the round-1 fix is described as a
class fix and one axis of the class is still open).

## VERDICT: NOT CONVERGED
