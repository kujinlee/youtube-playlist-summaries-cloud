# Post-Plan Gate — round 3 — Claude half

**Subject:** `docs/superpowers/plans/2026-09-02-guard-inventory-population.md` **v3** (`d4b6de6a`),
implementing `docs/superpowers/specs/2026-09-02-guard-inventory-population-design.md` v4.
Branch `fix/guard-inventory-population`. **Backlog:** #72, #73. **Date:** 2026-09-03.

**Method — BUILT AND RUN, not read.** T1–T7 were implemented verbatim from the plan into a temp tree
at `/Users/kujinlee/.claude-tmp/r3tree` (`scripts/ .github/ .claude/ docs/` copied; no repo-tracked
file touched) and executed. Every finding and every clean claim below cites either a command I ran or
a `file:line` I read.

**VERDICT: NOT CONVERGED** — 2 High, 6 Medium, 2 Low. **Zero Blocking.**

> ⚠ **This round covers TWO.** Round 2's Claude half never ran (`REVIEW GAP: claude`, both attempts
> died on API 529), so v2 shipped one-sided. Priority 6 below re-examines v2's own fixes as if they
> had never been independently reviewed.

> ⛔ **The headline is that the mechanism WORKS.** The plan's central claim — that T1–T7 as written
> produce a 28-guard inventory with four mutations that go red via the cases they name — **was
> reproduced end to end**: `guards discovered (28)`, `ratchet contract OK`, rc 0, and
> `check-plan-code.py --mutate .` → **8 file(s), 166 mutation(s), 0 survivor(s), rc=0**. No finding
> below disputes that. What the findings are about is the plan's *prose around* the code: **five of
> the eight are statements that were true of v2 and were not re-derived when v3 moved the work.**
> That is the sixth consecutive round in which the defects live in the previous round's own fixes.

---

## High 1 — T9 Step 2's `GROUPS` premise is FALSE, and the row T9 files lands undescribed

**Where:** plan Task 9 Step 2 (`:774-778`) vs `scripts/gen-backlog-page.py:775-790`.

The plan says:

> `GROUPS` coverage is **bidirectional**: it refuses an open item with no prose *and* prose describing
> a now-closed item. Closing a row means deleting its tuple.

**The first half stopped being true on 2026-09-02**, in `d39fa658` — which `git merge-base
--is-ancestor d39fa658 HEAD` confirms is an ancestor of this branch. `coverage_errors`' own docstring
now reads:

```python
def coverage_errors(groups: list, open_nums: set[int]) -> list[str]:
    """PURE. The grouping is prose; this is the part that cannot be wrong silently.

    ⚠ NO LONGER REPORTS MISSING ITEMS — see `undescribed`. What remains here is the
    set of shapes that would make the page ASSERT something false, which is why these
    still refuse rather than render.
    """
```
(`scripts/gen-backlog-page.py:775-781`)

**OBSERVATION — executed against T9's end state** (#72/#73 tuples deleted, a new open #88 added):

```
coverage_errors (refusals): []
undescribed (rendered w/ warning): [88]
```

**What breaks.** T9 Step 3 files a **new open row** and **no step in the plan adds a `GROUPS`
sentence for it**. The omission is coherent only under the plan's stated (false) rule — if coverage
really were bidirectional, T9 as written would refuse the build. Under the real code it does not
refuse; it renders #88 into the group titled *"Filed, but nobody has described them yet"* and emits a
⚠, which `.claude/hooks/regen-backlog-page.sh` fires on any edit to `docs/backlog.md` or
`gen-backlog-page.py` — i.e. on T9 itself. That hook's own message (`:45`, *"If this is a coverage
refusal, add the item to GROUPS"*) carries the same stale belief, which is why the premise looked
safe.

⚠ **Not CI-red**, and I am not calling it Blocking for that reason. The cost is a reader-facing page
that this PR silently makes worse, and `d39fa658` exists precisely because that page going quietly
stale had already cost the user four items over two days.

**Fix:** correct the sentence (only the `extra`/`dupes` direction still refuses), and add a `GROUPS`
tuple for the new row in T9 Step 3, in the same commit.

## High 2 — T4's CANNOT-RUN exit ships with NO case, NO mutation and NO falsifier

**Where:** plan Task 4 Step 2 (`:480-491`); spec §3.4 (`:181-184`).

The spec promises a test: *"Today an unparseable `scripts/*.py` ends the run with a raw traceback …
Fail-closed, so not a false green, but **repaired here with a case**."* v3's T4 delivers the repair
and **not the case**. Search the plan: the new `return 2` branch is named by no `case(...)`, by no
entry in T7's manifest, and by none of F1–F9 (T10 Step 2's `zz-probe.py` is a *parseable* file).

**OBSERVATION — the branch is live and unguarded.** Built T1–T4, then dropped `def broken(:` into
`scripts/`:

```
$ python3 scripts/check-ratchet-contract.py
CANNOT RUN — a script under scripts/ does not parse: invalid syntax (<unknown>, line 1)
Treat this as NOT RUN.
rc=2
```

The code is correct. Nothing would notice if it were deleted, or if the `return 2` became `return 0`.

⚠ **The plan already contains the argument against this, and applied it one function over.** T1's
whole justification is *"every self-test case drives `discover_guards`/`check_contract`/`check_caller`
directly, so **`main()` is driven by nothing**"* (`:84-86`). The new branch is in `main()`. The
identical extraction that made the glob reachable would make this reachable, and was not proposed.

**Fix:** either extract the try/except into a function a case can drive and give it a mutation, or
state in T4 that this branch is knowingly uncovered and why — but the spec's *"repaired here with a
case"* must then be corrected, because it is the sentence that makes the gap invisible.

---

## Medium 1 — T1 Step 5's "count rises by 3"; measured **2**

**Where:** plan `:218` — *"Expected: PASS, count rises by 3."*

T1 Step 2 adds exactly two `case(...)` calls. **The plan says so itself 59 lines earlier** (`:159`:
*"a step adds a case outside a table (T1 Step 2 adds two)"*), so v3 contradicts itself within one task.

**OBSERVATION:**
```
after T1 Step 1 :  self-test: 21/21 passed
after T1 Step 4 :  self-test: 23/23 passed
```

An implementer who trusts `:218` reads a correct green build as a failure, or invents a third case to
reach 24. This is the eighth instance in this slice of a count stated from a prior state.

## Medium 2 — T4's "By the time this task runs it is THREE"; measured **ZERO**

**Where:** plan `:461-464`.

> ⚠ **The plan previously said "five failure prints". By the time this task runs it is THREE** — T3
> deleted the `DISCOVERY_CASES` loop and its print, and T3 rewrote the `POPULATION_CASES` loop to use
> `case()`.

That arithmetic is v2's. In **v3**, T1 Step 1 converts *"every existing comparison loop"* (`:142-143`),
so nothing is left for T3 to convert and nothing is left for T4 to count.

**OBSERVATION**, on the file produced by T1 Step 1 + T2 + T3:
```
$ grep -c 'print(f"  FAIL' scripts/check-ratchet-contract.py
0
```

T4 **Step 1** expects exactly this (`exit=1`, no matches), so T4 contradicts its own preamble. Harmless
to execution, but it is the same shape as the round-2 Blocking: a sentence describing v2's structure
survived the edit that removed that structure. The plan's own hedge (*"Count them in the file rather
than trusting this sentence"*) mitigates it and does not make it true.

## Medium 3 — the "T4 → T7" ordering constraint is stated for a reason that no longer holds

**Where:** plan `:904` in the table headed *"Known ordering constraints — **all five**, after the
Post-Plan Gate"*:

> | **T4 → T7** | without the `[FAIL] ` format every `expect` resolves to 0 red cases and is rejected |

The `[FAIL] ` format is delivered by **T1 Step 1** in v3, not by T4 (`:107-126`). T4's only remaining
code change is the CANNOT-RUN exit, which no mutation targets and no case reaches (High 2). So **T4 →
T7 is not a constraint at all**, and the reason given for it is false.

**OBSERVATION:** `--mutate .` went 166/0 with all four ratchet-contract mutations caught via the cases
they name, and the format they depend on came from T1. The row is decoration over a coupling that
moved. A constraint table whose entries are not individually true is how a real ordering hazard gets
skimmed past.

## Medium 4 — spec §7's `docs/backlog.md` row is covered by no task, and the Self-Review says otherwise

**Where:** spec §7 last row (`:378`); plan Task 8 Files list (`:713-717`); plan Self-Review (`:885`).

Spec §7's table ends with:

> | `docs/backlog.md` rows #72/#73 | edited by this PR anyway; **must not be left describing the old mechanism** |

T8's Files list does not contain `docs/backlog.md`. T9 Step 1 changes only the severity/status markers.
So nothing rewrites the row bodies — and `docs/backlog.md:101` currently reads
*"`scripts/check-ratchet-contract.py:67` still carries the full CI-step-plus-docstring discovery
implementation"*, describing a function T3 deletes.

The plan's Self-Review asserts *"§7 → T8"* and *"**No spec section is without a task.**"* (`:885-886`).
That is a completeness claim over an incomplete mapping — the shape spec §12 flags four times.

## Medium 5 — the guard's OWN error message asserts the mechanism T3 deletes, and no task lists it

**Where:** `scripts/check-ratchet-contract.py:390`.

```python
        print("FAILED: .github/workflows/ci.yml not found — ratchets could not be discovered.")
```

After T3, nothing is *discovered* from `ci.yml`; it survives only as a caller source
(`:413`, `caller_sources: list[Path] = [ci_path]`). The message asserts a deleted mechanism, at the
source, in the file this whole change is about — spec §1.2's exact class.

It is missing from §7 because §7's sweep keyed on the tokens *"discover_ratchets"*, *"check-*.py"*,
*"two independent sources"*, *"two ways"*, *"the population is the FILESYSTEM"*,
*"RATCHET_DOCSTRING_RE"* (spec `:359-362`) — **and this line contains none of them.** The sweep is not
wrong; its dimension list was enumerated from the claims already known, not from the rule.

## Medium 6 — T6 makes a MEASURED comment in `check-selftest-counts.py` false, and nothing corrects it

**Where:** `scripts/check-selftest-counts.py:78-80`.

```python
# MEASURED 2026-09-01: of 38 scripts accepting --self-test, 8 declared a count canonically; this
# file is the ninth, so the set below is 9. Pinned, not derived — see the docstring. Add a name
# here when a script starts declaring, or the run fails naming it.
```

T6 Step 2 adds a tenth. **OBSERVATION**, after applying T6:

```
$ python3 scripts/check-selftest-counts.py
self-test counts: 10 script(s) declare a count, every one verified by running it   (rc=0)
```

Nothing fails, so the comment rots silently. One line, in T6's own commit.

---

## Low 1 — `population_paths` hardcodes the `scripts/` prefix it claims to derive

`return sorted(f"scripts/{p.name}" for p in scripts_dir.glob(pattern))` (plan `:211`). The returned
path is independent of `scripts_dir`, so `population_paths(ROOT / "anything")` returns paths asserting
`scripts/`. T1 Step 2's case cannot see this: it passes a tmpdir *named* `scripts`. Deriving from
`scripts_dir.name` costs one expression and makes the docstring's *"repo-relative POSIX paths"* true.
Not a live defect — `main` has exactly one call site.

## Low 2 — T10 Step 2's `exit 2` kills an interactive shell

`cp -R scripts .github .claude "$T"/ || { echo "CANNOT RUN — copy failed"; exit 2; }` (plan `:842`).
Pasted into a terminal rather than run as a script, the failure path exits the operator's shell. The
guard itself is right and I verified `cp -R` fails loudly on a missing source; only the exit verb is
wrong for the context. `return 2`/`{ …; false; }` or wrapping the block in `bash -c` fixes it.

---

## What I checked and found CLEAN

Built into `/Users/kujinlee/.claude-tmp/r3tree` and executed. No repo-tracked file was modified.

**Priority 1 — T1's whole-accounting conversion.**
- The conversion is complete: no surviving `failures` local, no surviving unconverted loop. All five
  loops (`CASES`, `DISCOVERY_CASES`, `CALLER_CASES`, `POPULATION_CASES`, `wiring`) route through
  `case()`, and the tally/return read `state`.
- **Step 1b's deliberate probe exits 1**, which is the whole point of the round-2 Blocking:
  ```
  [FAIL] probe: got 1
         expected 2
  self-test: 21/22 passed
  rc=1
  ```
- Step 3's expected failure is a `NameError` on `population_paths`, **not** on `case` — confirmed
  verbatim. Step 7: still `guards discovered (26)`, rc 0.
- `_make_case`'s docstring contains the literal `` `  FAIL {name}` ``; it does **not** match T4 Step 1's
  grep (`print(f"  FAIL`). No false positive.

**The contract ends at exactly 28.** After T5:
```
guards discovered (28): … scripts/gen-m4-manifest.py, scripts/verify-exclusion-reasons.py
ratchet contract OK      rc=0
```
`build-m4-schema.py` absent (spec §4.1). Every `scripts/*.py` still compiles (T5 Step 3, no output).

**T3's intermediate state matches the plan.** `guards discovered (45)`; 14 violations over exactly
**10 distinct scripts** — `brief-compose`, `codex-frontier-model`, `codex-review`, `m4_base_db`,
`m4_catalog`, `prior-art`, `regen-skills-doc`, `session-skill-report`, `skill-usage-audit`,
`subject_status` — **all 10 in the OUT set**, which independently reproduces spec §4.4.

**T2:** all 13 `NOT_A_GUARD` cases pass against the given implementation, including `AnnAssign`,
`Final[str]`, implicit concatenation, both docstring shapes, and `before __future__` (which needs the
`compile()`).

**Priority 2 — every T7 anchor, character by character, against the code T1–T4 actually write.**
All four match **exactly once** (the harness refuses `>1`, `run_mutations` `:695-702`):
```
1x  'def population_paths(scripts_dir: Path, pattern: str = "*.py'
1x  '    for node in tree.body:'
1x  'and value.value.strip()'
1x  '        compile(src, "<inventory>", "exec")\n'
```
`expect` semantics verified at the source: equality, not substring (`check-plan-code.py:757` region,
`unnamed = [(w, [f for f in fails if w == f]) …]`), and the red-case parser is
`l.strip()[7:].rsplit(": got ", 1)[0]` — which `_make_case`'s format satisfies.

**T7 Step 2's three edits, all correct as written:** the key; the inventory oracle's sorted position
(`check-plan-code.py` < `check-ratchet-contract.py` < `check-selftest-counts.py`); and the sum literal
— the real current sum is `70+14+34+21+11+4+8 = 162`, so **166** is right.
`python3 scripts/check-plan-code.py --self-test` → **158/158 passed** with no `[DRIFT]` line.

**THE DECISIVE RUN:**
```
$ python3 scripts/check-plan-code.py --mutate .
OK — delivered scripts mutated: 8 file(s), 166 mutation(s), 0 survivor(s)     rc=0
```
Run **with all 17 T5 declarations in place**, which also proves spec §10's claim empirically: the
declarations orphan no existing anchor in `gen-dashboard.py`, `page_chrome.py` or `page_markup.py`.

**T6:** `# 34 cases` matches `count_drift`'s regex `r"--self-test\s+#\s*(\d+) cases"`
(`check-plan-code.py:933`); the declaration sits inside the module docstring where `declares()`
(`ast.get_docstring`) reads it; `printed_total`'s last-match rule finds exactly one
`self-test: 34/34 passed`. Gate green, 10 members.

**Priority 3 — T9's counts, recomputed through the owning parser.**
```
NOW: TOTAL 87  OPEN 59  CLOSED 28
after T9 (close 2, add 1 open): 88 58 30
```
**88/58/30 is correct.** The closed-marker instruction is also correct against the real predicate
(`check-docs.py:456`, `num, item, status = cells[1], cells[2], cells[-2]`; `if "✅" in status and
item[:1] in severity`): ✅ goes in the **Status** cell and the **Item** cell must stop leading with a
bare marker. Row #72 is 🟠 and #73 is 🟢, so `✅ (was 🟠)` / `✅ (was 🟢)` are the right strings. Both
`GROUPS` tuples exist (`gen-backlog-page.py:239` and `:242`) and deleting them is required — that
direction (`extra`) **does** still refuse.

**Priority 4 — T4's reshuffle.** Nothing was dropped that lands elsewhere: Step 1's grep, Step 2's
exit, Step 3's parser probe (`parsed red cases: []` on a green suite). The one thing that *was* dropped
is the spec's promised case — High 2.

**Priority 5 — the other four ordering constraints and both same-commit couplings** hold as stated,
and I drove each: T1→T7 (the mutation needs the extracted default), T1 Step 1→everything (`case` is
otherwise a `NameError`), T2/T3→T7 (three of four anchors do not exist before T2/T3), T3→T5 (45 until
the declarations land). T6's coupling is real (`check-selftest-counts.py:176-179`); T7 Step 2's is real
(a red `check-plan-code --self-test` makes the control refuse before any mutation runs,
`mutate_delivered:640-648`).

**Priority 6 — v2's own fixes, re-examined as never independently reviewed.** The signature-default
mutation, the `!= ""` whitespace mutation, and T7 Step 2's three edits are all **correct and executed
green**. The T10 copy guard is correct: `cp -R` does fail non-zero on a missing source and the plan
explicitly forbids the `2>/dev/null` that would hide it. v2's fixes are sound; what v2 left behind are
Mediums 2 and 3 — sentences it did not re-derive.

**Also clean:** T8's F8 grep returns exactly three hits — `page_markup.py:45` and the contract's own
`:67`/`:346` — **all inside T8's declared file set**, so F8 is satisfiable, not aspirational. T8's edit
sites collide with nothing: no `page_markup.json` anchor sits in that file's docstring head, and
`explainer-serve.py`'s `--self-test   # 81 cases` line is at `:66`, outside the `:68-73` block T8 edits.
`check-vocabulary-collisions.py` and `check-guard-coverage.py` are schema/table-scoped, so
`NOT_A_GUARD` introduces no vocabulary collision.

---

## Gaps in my coverage — read these before treating the clean list as complete

1. **`check-guard-coverage.py` and `check-vocabulary-collisions.py` returned rc=2, CANNOT RUN** (no
   Postgres). **Treat them as NOT RUN, not as clean.** I bounded the risk by reading their scope, not
   by executing them.
2. **`check-docs.py` (rc=1), `check-producer-enumeration.py` (rc=1) and `check-gate-falsifiability.py`
   (rc=1) failed in my temp tree** for missing-`lib/`/`package.json`/`.claude/skills` reasons. I did
   **not** isolate whether the plan's edits would independently affect them. T10 Step 4's sweep is
   therefore unverified for `check-docs.py`.
3. **I did not execute T8's or T9's edits end to end** — they are prose rewrites that do not exist yet.
   I tested their *predicates* (`check-docs.py:456`, `coverage_errors`, `undescribed`, the F8 grep) and
   their *collision surface*, not the resulting text. High 1 was established by direct calls into
   `gen-backlog-page`, because my first attempt to simulate the whole T9 edit hung on a regex of my own
   and I abandoned it rather than trust a partial run.
4. **`--mutate .` ran ONCE.** One green run is one observation. It does not establish that the four
   mutations are the *right* four, only that each is caught by the case it names.
5. **I did not attempt the 45→28 transition on a dirty or partially-applied tree**, so I cannot speak
   to what an implementer sees if T5 is committed before T3.
6. I built T1–T7 but **not T8, T9 or T10**, so the plan is proven runnable only through Task 7.

---

## Disposition

Nothing here challenges the design, the AST mechanism, the 28, or the task decomposition — all of
which I reproduced. The two Highs are a false premise with a missing step (H1) and a promised test
that was not written (H2). The six Mediums are, with one exception, **stale sentences left by v3's own
reshuffle** — which is the same verdict every prior round of this slice reached, now at instance six.

⚠ **The pattern is worth naming rather than fixing case by case.** Five of eight findings are prose
that was true of the previous version. The plan's counts and constraint reasons are re-derived only
when a reviewer runs them. The cheap structural answer is to stop writing derivable numbers into the
plan at all — `:218`'s "rises by 3", `:461`'s "THREE", and `:904`'s reason are three literals that a
single `grep -c` or a single run would have settled, and all three were authored.

Codex half: [`plan-guard-inventory-population-r3-codex.md`](plan-guard-inventory-population-r3-codex.md).

**VERDICT: NOT CONVERGED**
