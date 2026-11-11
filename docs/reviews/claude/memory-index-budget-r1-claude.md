# memory-index-budget — round 1, CLAUDE half

Primary subject: `0cb448cb` ("The index overflow now has a machine, because the cleanup recurs
every time history accumulates") and its parent `dff6a3f0` ("The memory index was being truncated
in silence…"), on branch `baseline-surveys`.

⚠ **THE WORKING TREE MOVED UNDER THIS REVIEW, AND UNLIKE THE USUAL CASE IT MOVED ON MY SUBJECT.**
Partway through, `scripts/check-memory-index-budget.py` changed on disk — the Codex half is
editing it live (`git diff --stat 0cb448cb` showed `+28/-9`, a docstring correction labelled
`r1 CODEX #4`, and the two memory entries have since been amended too). Every measurement below
was therefore re-taken against a clean worktree checked out at `0cb448cb`
(`git worktree add --detach … 0cb448cb`, `git rev-parse HEAD` = `0cb448cb60fd…`), and the blob I
reviewed is `81258f8429eff4ad93146219758e51a9c5edbe2e`. Said rather than assumed: this repository's
recorded hazard is exactly a live agent's file read as static. Where a finding of mine has already
been partly addressed in the working tree, I say so under the finding.

Instrument, all of it run:

- the guard's own suite (26/26 green at `0cb448cb`) and its live run;
- the **7 declared mutations**, applied from the shipped manifest to an isolated tree with a
  proved-green control — 7 killed, 7 correctly attributed;
- **8 mutations of my own** against the same control, of which **6 survive all 26 cases**;
- `check-plan-code.py --self-test`, `check-selftest-counts.py`, `check-ratchet-contract.py`,
  `check-guard-coverage.py`, `check-rc-contract.py`, `check-main-drivable.py`,
  `check-gate-falsifiability.py`, `check-fixture-variation.py`, `check-docs.py`;
- `recall-llm.py`'s own `memory_files`, `load_triggers`, `corpus_verdict` and `build_prompt`
  symbols, driven over both `23e5a349` and `0cb448cb` worktrees — not a re-implementation of their
  rules;
- `git ls-remote`/`cat-file` against `refs/pull/376/head` and `origin/master` for the citation claims;
- and **this agent's own injected context**, which turns out to be a live observation of the
  harness truncating the pre-fix index. That is the one instrument the author believed did not
  exist ("nothing in the repo can interrogate the harness", `:37`), and it settles two claims.

**NOT RUN, stated loudly:** the full repo mutation sweep (`check-plan-code.py --mutate .`, 1,552
entries). It has no `--only` and the recorded local experience is that shards time out. My scoped
run is a substitute for the new manifest only; I make no claim about the other 63 manifests.

> **The guard is worth having and the defect it names was real. But the headline number is wrong,
> the unit is wrong, six mutations survive, and the branch as committed puts TWO red steps into the
> required `verify` job.** The two reds are mechanical. The unit finding is not: measured twice over,
> the harness's limit is in CHARACTERS, and one shipped mutation entry currently defends the wrong
> unit as if it were the invariant.

---

## Blocking

### B1 — Blocking. `check-plan-code.py --self-test` is RED at this tip, and it is a step in the required `verify` job. The new manifest was registered at one of three sites; the comment describing the second change is there, the change is not

Measured in a clean worktree at `0cb448cb`:

```
$ python3 scripts/check-plan-code.py --self-test
  [FAIL] the declared counts name every manifest that ships: got [… 'scripts/check-memory-index-budget.py' …] want [… no such entry …]
  [FAIL] the declared counts are the real ones: got 1552 want 1545
176/178 passed        (rc=1)
```

A new guard's manifest must be named in **three** places in that file. One was done:

- `scripts/check-plan-code.py:1558` — `"scripts/check-memory-index-budget.py": 7,` ✅

Two were not:

- `scripts/check-plan-code.py:3461` — the LIVE INVENTORY list inside
  `case("the declared counts name every manifest that ships", sorted(EXPECTED_MUTATIONS), [...])`.
  Its own comment at `:3476-3480` says *"This list is a **LIVE** inventory, so it grows with each
  guard paid off"* — it was not grown. ❌
- `scripts/check-plan-code.py:5185` —
  `case("the declared counts are the real ones", sum(EXPECTED_MUTATIONS.values()), 1545)`.
  The sum is now 1552. ❌

What makes this more than an oversight is `scripts/check-plan-code.py:1552`:

```python
    # ⟳ 2026-10-19: check-memory-index-budget joins at 7, declared sum 1545 -> 1552. It guards the
```

The comment **describes the edit at `:5185` that was never made**. The record says the ratchet was
raised; the assertion still pins the pre-change number. (The working tree has since been corrected
to `1552` — i.e. someone is already repairing this — but `:3461` is still short one entry there,
so the suite does not go green on that fix alone.)

`.github/workflows/ci.yml:539-540` runs this:

```yaml
      - name: check-plan-code self-test
        run: python3 scripts/check-plan-code.py --self-test
```

and that step is inside the job named `verify` (`ci.yml:26`), which this project's record has as a
required check alongside `schema-gates`.

**OBSERVATION THAT WOULD MAKE THIS FAIL:** `python3 scripts/check-plan-code.py --self-test` exits 0
at the branch tip, from inside a tree where `scripts/` and `scripts/mutations/` are both present.
Today it exits 1 with those two named cases red.

### B2 — Blocking. `check-selftest-counts.py` exits 1: the new guard declares a case count that nothing verifies. A fourth registration site, also in `verify`

```
$ python3 scripts/check-selftest-counts.py        # rc=1
declared self-test counts disagree with what the suites printed:
  ✗ check-memory-index-budget.py: declares a case count but is not in POPULATION, so nothing checks it. Add it.
  ✗ check-plan-code.py: --self-test exited 1 — its own cases are red, so its declared count proves nothing. Fix the suite first.
```

The guard declares its count at `scripts/check-memory-index-budget.py:46`:

```
    python3 scripts/check-memory-index-budget.py --self-test  # 26 cases
```

…and `scripts/check-selftest-counts.py:83` (`POPULATION: frozenset[str] = frozenset({…})`) does
not contain it — `grep -c check-memory-index-budget scripts/check-selftest-counts.py` → `0`. Its own
message at `:327` is the one that fired. `.github/workflows/ci.yml:399` runs it, in `verify`.

⚠ **I nearly recorded this as rc=0.** My first measurement was
`python3 scripts/check-selftest-counts.py | tail -5; echo "rc=$?"`, which reads `tail`'s status, not
the guard's — this repo's recorded `a-check-result-is-not-the-claim` trap. Re-run without the pipe,
the real code is **1**. The second ✗ line is B1 showing through: the two reds are not independent,
but they are two separate steps and both block.

**OBSERVATION THAT WOULD MAKE THIS FAIL:** `python3 scripts/check-selftest-counts.py` exits 0, with
the exit status read directly and not through a pipe.

**Registration tally for one new guard, measured:** 4 sites needed, 2 done.
`check-plan-code.EXPECTED_MUTATIONS` ✅, `check-fixture-variation.py:441` ✅,
`check-plan-code` inventory ❌, `check-selftest-counts.POPULATION` ❌. Three sibling guards
(`check-rc-contract`, `check-main-drivable`, `check-gate-falsifiability`) return rc=0 while naming
the new guard **zero** times — they are green because they are not looking, which is not the same
as green.

---

## High

### H1 — High. The harness's limit is in CHARACTERS, not bytes. I measured it two independent ways. `index_size`'s stated reason for choosing bytes is arithmetically false, and shipped mutation entry #4 now defends the wrong unit

`scripts/check-memory-index-budget.py:123-132`:

```python
def index_size(path: pathlib.Path) -> int | None:
    """-> the file's size in BYTES, or None when it cannot be read.

    Bytes, not characters: the index is dense with multi-byte glyphs (⭐ ⛔ ⟳) and the two counts
    differ by nearly a kilobyte at this size — measured 27,805 bytes against 26,930 characters.
    A character count would have reported this index as fitting when it did not.
    """
```

The last sentence is false on its own numbers: **26,930 > 24,985**. A character count would have
caught this instance too. That much the Codex half has already found and corrected in the working
tree (`r1 CODEX #4`). What follows is the part their correction does not establish — *which* unit
the harness actually uses — and it inverts the argument rather than narrowing it.

**Measurement 1 — the harness's own reported figure matches the character count to the decimal.**
The warning quoted verbatim at `:62` says `MEMORY.md is 26.3KB`. Derived from the file that warning
was emitted about (`23e5a349:docs/memory/MEMORY.md`):

| quantity | value | ÷1024 | rendered |
|---|---|---|---|
| bytes | 27,805 | 27.153 | **27.2KB** |
| characters | 26,930 | 26.302 | **26.3KB** ← what the harness printed |

**Measurement 2 — the truncation point itself, taken from this agent's own context.** The MEMORY.md
injected into this session is the **pre-fix, 145-row** file (it still carries the `## Slice history`
section, and the harness's truncation warning). The last row delivered is
`- [Retire plan mode — #270+#271](retire-plan-mode-merged.md)`, row **137 of 145**. In the source
file the cut falls at:

| | offset at the cut | vs the declared 24,985 limit |
|---|---|---|
| characters | **24,958** | 27 **under** — i.e. the next row would not fit |
| bytes | **25,771** | 786 **over** |

A byte limit of 24,985 cannot produce a cut at byte 25,771. A character limit of 24,985 produces
exactly this cut, to within one row. Two independent measurements, same answer.

**The consequence, stated precisely, including the half that is harmless.** In UTF-8
`len(bytes) >= len(chars)` always, so the guard over-counts and therefore fires *early*: guard green
⇒ bytes ≤ 24,985 ⇒ chars ≤ 24,985 ⇒ the harness is genuinely fine. **This cannot produce a false
green.** It is the safe direction, and I am not claiming a live miss. What is wrong is the record and
the test:

1. Three documents assert the false reason (`:128`, and the mutation entry's own name).
2. `:215` pins the wrong unit as the invariant to protect:
   `check("index_size counts BYTES, not characters (multi-byte glyphs)", index_size(f), 10)`.
3. `scripts/mutations/check-memory-index-budget.json`, entry 4 —
   *"the size is counted in CHARACTERS, which under-reports a glyph-dense index by ~1KB"* — mutates
   `read_bytes()` → `read_text()` and the suite reddens. That mutation **kills the correct
   behaviour.** A manifest entry whose job is to forbid the right answer is the
   `a-guard-can-mandate-the-duplication-it-audits` shape: no number of future rounds can reword its
   way out, because the case and the manifest both have to move.
4. The guard's effective threshold is ~3.0% tighter than the harness's (measured on the live file:
   22,333 bytes vs 21,688 chars), so the `OVER BUDGET` message's arithmetic at `:107-111` —
   *"roughly the last {n_bytes - limit:,} bytes of rows never arrive"* — is wrong in units as well
   as (see H2) in magnitude.

**OBSERVATION THAT WOULD MAKE THIS FAIL:** a harness truncation whose cut point sits at
byte ≈ 24,985 rather than character ≈ 24,985; or a reported "KB" figure that matches bytes/1024
rather than chars/1024. Both are directly measurable from any session that gets the warning, as
this one did.

### H2 — High. "roughly 30 of its 118 rows" is wrong on the numerator AND the denominator, and that figure is now copied verbatim into four places

`scripts/check-memory-index-budget.py:7-8`:

```
The index reached **27,805 bytes against the harness's 24,985-byte limit**, so roughly 30 of its
118 rows were dropped before any of it was read.
```

Measured:

| | claimed | measured |
|---|---|---|
| rows in the overflowing index | 118 | **145** (118 is the count *after* the fix) |
| rows dropped, live (this session's own context) | ~30 | **8** |
| rows dropped, modelled as a 24,985-**char** prefix | — | 7 |
| rows dropped, modelled as a 24,985-**byte** prefix | — | 13 |

The denominator is taken from after the change while the numerator describes before it. "~30" looks
like `(27,805 − 24,985) / ~94 bytes-per-row` — a mean-row-size estimate — but the overflow falls in
the slice-history tail, whose rows are the longest in the file, so the true count is 8. The
`a-retrospective-number-needs-provenance` tell is present: a round figure supporting a sound
argument.

The argument survives intact — 8 rows silently dropped is still the defect, and the rule that
mattered most was still "the one furthest down" (`:16-17`). Only the number is wrong. But it has
already propagated to four sites plus the commit message and dashboard entry:

- `scripts/check-memory-index-budget.py:7-8`
- `.github/workflows/ci.yml:246` — *"~30 of its 118 rows were silently dropped"*
- `docs/memory/MEMORY.md:140` — *"it stood at 27,805 and ~30 rows had stopped arriving"*
- `docs/memory/slice-history.md:9-10` — *"roughly 30 index rows were dropped"*

Four copies of one unmeasured figure, in a repo whose most-cited lesson is that a second copy of a
rule drifts. The two in `docs/memory/` are the costly ones: they are corpus content, so they will be
recalled and believed.

**OBSERVATION THAT WOULD MAKE THIS FAIL:** counting the rows absent from a session that received the
truncated pre-fix index and finding ~30. This session received exactly that index; the count is 8.

### H3 — High. Six mutations survive all 26 cases, over a proved-green control. The worst retargets `INDEX` so the guard measures a different file and prints a confident "Every row arrives"

I built an isolated tree (`scripts/` + `docs/memory/` only, so `ROOT` resolves and the repo is never
touched), proved the control green, then mutated one anchor at a time. The author's 7 all behave as
claimed — **7 killed, 7 attributed to the case each names**, control green. C4's stated half is true.
Its implied half is not:

| # | mutation | result |
|---|---|---|
| A | `INDEX` → `ROOT / "docs" / "memory" / "slice-history.md"` | **SURVIVED** 26/26 |
| B | `:151` `shown = str(index.relative_to(ROOT))` → `str(index)` | **SURVIVED** 26/26 |
| C | `:130` `if not path.is_file():` → `if not path.exists():` | **SURVIVED** 26/26 |
| D | `:145` `a.startswith("-")` → `a.startswith("--")` | **SURVIVED** 26/26 |
| E | `WARN_FRACTION = 0.90` → `0.9004` | **SURVIVED** 26/26 |
| F | `WARN_FRACTION = 0.90` → `0.99` | killed (1 case) |
| G | `:95` `if n_bytes is None:` → `if n_bytes is None or n_bytes == 0:` | **SURVIVED** 26/26 |
| H | unknown-flag arm severed (`if unknown:` → `if False:`) | killed (1 case) |

**A is the mutation you did not write, and it is the one that matters.** With `INDEX` pointing at a
sibling file, the guard reports:

```
ok — the always-loaded index is 7,386 bytes, 17,599 under the harness's 24,985-byte limit. Every row arrives.
```

rc=0, suite 26/26 green. Nothing measured the index; the sentence "Every row arrives" is asserted
about a file that is not loaded at all. The reason is `:243-246`, the only case that touches `INDEX`:

```python
    live = index_size(INDEX)
    check("the LIVE index is measurable and within budget "
          f"(it is {live if live is not None else 'UNREADABLE'} bytes)",
          budget_verdict(live, LIMIT_BYTES)[0], OK)
```

The assertion is `verdict == OK`, which **any** under-budget file in the repo satisfies. This is
`a-case-can-pass-for-an-ambient-reason` precisely: the case's NAME says *the live index*, its BODY
says *some file that is small*. It catches `INDEX` being pointed at something absent (verdict
becomes 2) and misses `INDEX` being pointed at something merely wrong — which is the likelier edit,
since `OVERFLOW_TARGET` at `:58` names the sibling two lines below.

G deserves a note because it is subtler than the manifest's entry 2. That entry severs
`if n_bytes == 0:` → `if False:` and is correctly killed, because `0` then falls through to OK. G
instead lets the `None` arm swallow `0`: the exit code stays 2 and the string
`"NOT RUN, never as a pass"` is still present, so cases `:196`, `:197` and `:200` all still pass —
while the EMPTY-specific diagnosis at `:101-103` (*"That is not a small index, it is a missing
one"*) becomes unreachable. The docstring at `:90-93` calls that distinction load-bearing; no case
witnesses it.

B and D and E are Low on their own and are listed in L3; C is M1.

**OBSERVATION THAT WOULD MAKE THIS FAIL:** mutation A applied to the shipped file and the suite
going red. It does not; I ran it against both the working-tree copy and the committed blob, with a
green control proved first in each.

### H4 — High. `ci.yml:248-249` claims CI measures the file a session loads. It does not — a session loads the WORKING TREE, and this guard has no local caller at all. Backlog #309's blind spot is inherited in full

`.github/workflows/ci.yml:248-250`:

```
      # the link, this one is NOT advisory on a runner: `docs/memory/MEMORY.md` is committed, so
      # CI measures exactly the file a session loads. A CANNOT RUN here (rc 2) means the index is
      # missing or empty, which is never a pass.
```

The lead asked whether the guard inherits #309's blind spot, whether CI measuring the committed file
makes it useless for the live failure, or both. Measured answer: **both, and they are two different
holes.**

What a session actually loads:

```
$ ls -la ~/.claude/projects/-Users-…-cloud/memory
… memory -> /Users/…/youtube-playlist-summaries-cloud/docs/memory
$ stat -f '%i %N' docs/memory/MEMORY.md ~/.claude/projects/…/memory/MEMORY.md
191911617 docs/memory/MEMORY.md
191911617 /Users/…/memory/MEMORY.md          # same inode
```

The injected file **is** the working-tree file, through a directory symlink. So:

1. **Run locally**, the guard reads `ROOT/docs/memory/MEMORY.md` (`:57`, `:154`) — the working tree,
   the live file. Locally it does *not* inherit #309's blind spot. Good.
2. **But nothing runs it locally.** `grep -rln memory-index-budget .claude/` → no match; it is in
   neither `scripts/check-schema-gates.sh` nor `scripts/check-merge-ready.py`. Its only two callers
   are the CI steps at `ci.yml:252` and `:255`.
3. **In CI the checkout is the committed tree**, so the only automatic execution measures the one
   version a session never reads. An uncommitted index that overflows — the exact working-tree-only
   shape backlog #309 was filed for, and that commit `23e5a349` describes as *"WORKING-TREE ONLY,
   which is why no git-shaped guard can catch it"* — is invisible.

The comment's premise ("`MEMORY.md` is committed") is a statement about today's `git status`, not a
property. It is true at this moment (`git diff HEAD -- docs/memory/MEMORY.md` is empty) and was
false for the entire window in which the defect was being fixed.

**OBSERVATION THAT WOULD MAKE THIS FAIL:** a caller for this guard outside `.github/workflows/`
— a hook, or a line in an aggregate local runner. There is none.

---

## Medium

### M1 — Medium. `index_size` promises `None` "when it cannot be read" and does not deliver it for a file that is present and unreadable; the process then exits 1, which the contract defines as OVER_BUDGET

`:124` says *"-> the file's size in BYTES, or None when it cannot be read"*, but `:130-132` only
tests `is_file()`:

```python
    if not path.is_file():
        return None
    return len(path.read_bytes())
```

Measured on a `chmod 000` file:

```
index_size -> RAISED PermissionError  -- docstring promised None
main       -> RAISED PermissionError  -> interpreter exits 1 == OVER_BUDGET, not 2 == CANNOT_RUN
```

`budget_verdict`'s docstring at `:93` states the invariant this breaks: *"'Cannot measure' and
'measured, and it is fine' must never share an exit code."* The real collapse is adjacent and worse
in effect — *cannot measure* and *over budget* share rc=1, so an unreadable index is reported as an
oversized one and the reader is sent to the remedy at `:110` (move history rows) for a permissions
problem. A directory is handled correctly (`is_file()` → False → `None` → rc 2).

⚠ **The working tree makes this worse, not better.** The concurrent edit rewrites the `None` message
to *"could not be READ — it is absent, or present and unreadable"* — asserting the capability the
code still does not have, since `PermissionError` is caught nowhere. At `0cb448cb` the message says
*"does not exist"*, which is at least honest about what the code detects.

**OBSERVATION THAT WOULD MAKE THIS FAIL:** `main([], index=<a chmod-000 file>, limit=1000)`
returning 2.

### M2 — Medium. `budget_verdict`'s `label` default is a second expression of `INDEX`'s path, and no guard in this repo can see it

`:57` builds the path; `:81` restates it as a literal:

```python
INDEX = ROOT / "docs" / "memory" / "MEMORY.md"
...
def budget_verdict(n_bytes: int | None, limit: int, label: str = "docs/memory/MEMORY.md",
```

Two expressions of one path, agreeing only until someone edits one — the defect class
`warn_threshold`'s own docstring at `:75-76` cites as *"this repo's most-measured defect class"*,
reproduced eight lines below it. It is not reachable from `main` (which always passes `shown`), so
the live path is unaffected; it is reached by case `:238`, which asserts the literal against itself.
Mutation A above is the demonstration that the two can disagree without anything noticing.

To the lead's framing: `check-vocabulary-collisions.py` cannot see it, and the reason is categorical
— it audits duplicate *coordination vocabulary*, one mechanism per concern. This is a duplicated
*value*, in two different syntactic forms (a `/`-composed `Path` and a string literal), inside one
function signature. Deriving the default (`str(INDEX.relative_to(ROOT))`) removes it.

**OBSERVATION THAT WOULD MAKE THIS FAIL:** editing `:57`'s path and seeing any case redden on the
`:81` default. Mutation A edits exactly that and 26/26 stay green.

### M3 — Medium. A positional argument is silently ignored, and `--self-test` plus an unknown flag takes the self-test path and exits 0

`:143-149`:

```python
    if "--self-test" in argv:
        return _self_test()
    unknown = [a for a in argv if a.startswith("-")]
```

The docstring at `:139-141` claims *"`argv` carries real behaviour on purpose — an unknown flag
exits CANNOT RUN rather than being ignored."* Two gaps, both measured:

```
$ python3 scripts/check-memory-index-budget.py garbage
ok — the always-loaded index is 22,333 bytes, 2,652 under … Every row arrives.     rc=0
$ python3 scripts/check-memory-index-budget.py --self-test --bogus
… self-test: 26/26 cases passed                                                     rc=0
```

The first is the likelier mistake now that `main` takes an `index` parameter: a caller who passes a
path gets a confident verdict about a *different* file and rc=0. The second orders the self-test
short-circuit before the validation, so any mistyped companion flag is swallowed. It is made
genuinely confusing by case `:235` (`main(["--bogus"])`), which prints a real `CANNOT RUN —
unrecognised flag(s) ['--bogus']` line from *inside* the self-test — so the output of the ignored-flag
run is byte-similar to the output of the rejected-flag run, and only the exit code differs.

On the lead's specific probe: a bare `-` **is** rejected (rc=2), and that is correct, not a defect —
this guard reads no stdin, so there is nothing for `-` to mean.

**OBSERVATION THAT WOULD MAKE THIS FAIL:** either invocation above returning 2.

### M4 — Medium. C5's corpus arithmetic is wrong: 159 triggered and 4 trigger-less, not 161 and 2 — and "the same as before" is the only part that holds

Derived by importing `recall-llm.py` and calling its own `memory_files`, `load_triggers` and
`corpus_verdict`, over worktrees at both commits — not by re-implementing the `FIRES-WHEN:` rule
(my first attempt did re-implement it, looked for `FIRES-WHEN` anywhere in the file rather than
`TRIGGER_PREFIX` in the frontmatter `description`, and got a different number; the figures below are
the code's):

| | claimed | `23e5a349` | `0cb448cb` |
|---|---|---|---|
| corpus files | 163 | 162 | **163** ✅ |
| with a trigger | 161 | 158 | **159** ❌ |
| without a trigger | "the same 2 as before" | 4 | **4** ❌ (but unchanged ✅) |

The trigger-less four are `a-harness-cannot-read-a-cause-from-a-childs-text`,
`a-vendored-line-number-has-no-owner`, `cannot-die-may-mean-a-second-clause`,
`the-apparatus-outgrew-its-subject` — identical before and after, so the *claim that the move
changed nothing* is true. `163 − 2 = 161` is how the triggered count was reached: derived from a
believed trigger-less figure instead of measured. The move itself is clean; only the census is off,
and it understates an open gap (four entries outside the matcher, not two).

For completeness on C3: `corpus_verdict` (`recall-llm.py:481-494`) is a floor check — it fails only
when `n_files == 0` or `n_triggers == 0`. It returns `(0, '')` before and after and is structurally
incapable of noticing this change, or the overflow. That corroborates C1's "every signal was green"
rather than refuting it.

**OBSERVATION THAT WOULD MAKE THIS FAIL:** `len(load_triggers(docs/memory))` returning 161.

### M5 — Medium. No pointer row in `docs/dev-process.md`, which is the project's declared registry of what is mechanically enforced

`grep -c check-memory-index-budget docs/dev-process.md` → **0**. That file's own rule, under
*Keeping this file short*, is: *"Before adding a rule here, ask whether it can be a script. If it
can, write the script and add a pointer row above."* The script was written; the row was not added.
`check-docs.py` passes (rc=0) — it enforces the line budget and marker integrity, not registry
completeness, so nothing mechanical covers this.

**OBSERVATION THAT WOULD MAKE THIS FAIL:** a row for this guard in that table.

### M6 — Medium. C6 is true today and unsound as a mechanism: `refs/pull/376/head` is a moving ref that happens to still hold the cited blob

`docs/memory/a-guard-can-mandate-the-duplication-it-audits.md:15-16` at `0cb448cb`:

```
LOCATOR and this one is still open (PR #376). Durable:
`refs/pull/376/head:scripts/check-claim-propagation.py` — the script is NOT on `master`.
```

Verified, each half:

- `d06da80c` is **not reachable from `master`** — `git merge-base --is-ancestor d06da80c master`
  fails. ✅ The claim holds.
- `refs/pull/376/head` resolves (`git ls-remote` → `2e0ad1ef`) and contains the path. ✅
- `scripts/check-claim-propagation.py` is **absent from `origin/master`**. ✅
- PR #376 is **OPEN**, `mergedAt: null`.

And the part that refutes "durable": the ref has **already moved past** the SHA the finding was
measured on — `d06da80c` is an ancestor of `2e0ad1ef`. So the locator is a branch head, not a pin.
It happens to still name the right content (`git diff d06da80c refs/pull/376/head --
scripts/check-claim-propagation.py` is **empty**; no commit in that range touches the file), so the
citation is *correct today* — by luck, not by construction. One more push to that branch touching
that file and the citation silently names different evidence.

To the lead's question about a squash merge: GitHub retains `refs/pull/N/head` after merge and after
branch deletion, so the citation keeps **resolving**; it would then point at the pre-merge copy while
a live one exists on `master`, and nothing in the repo would notice. The durable locator is the SHA
plus the pull ref as a *retrieval route* — which is exactly what the working-tree amendment now
says. I reached it independently; recording the agreement, and recording that the amendment's
implication that the ref names *already-wrong* evidence is **not** established: the blob is identical.

**OBSERVATION THAT WOULD MAKE THIS FAIL:** `git rev-parse refs/pull/376/head` equalling `d06da80c`.

---

## Low

### L1 — Low. The row-length exclusion is measured in BYTES against a rule the harness states in CHARS. Same unit error as H1, so it is a class, not an instance

`:31-32` — *"**32 of 118 rows (27%) already exceed 200 bytes and the longest is 620**"* — while
`:30` quotes the harness as saying *"keep index entries to one line under ~200 **chars**"*.

Both figures reproduce, but only in bytes, and only on the post-fix file:

| | chars | bytes |
|---|---|---|
| rows over 200, `0cb448cb` (118 rows) | 29 (24.6%) | **32 (27%)** ← quoted |
| longest row | 602 | **620** ← quoted |
| rows over 200, `23e5a349` (145 rows) | 35 (24%) | 38 |

The conclusion is unaffected — 24.6% is as red-from-birth as 27%, so #56's verdict stands and
excluding the length rule is right. Low because only the arithmetic is wrong, and flagged at all
because it is the *same* substitution as H1 in a second place, which is what makes H1 a class.

### L2 — Low. "6,232 of the 27,805 bytes" attributes a whole section's cost to 28 rows; the rows are 5,162 bytes

`docs/memory/MEMORY.md:144` — *"28 rows, MOVED OUT of this index 2026-10-19: it was 6,232 of the
27,805 bytes that overflowed"*. Traced:

| quantity | bytes |
|---|---|
| the 28 row lines themselves | **5,162** |
| the whole `## Slice history` block to EOF in the pre-fix index | **6,232** ← the figure used |
| net shrink of `MEMORY.md`, `23e5a349` → `0cb448cb` | 5,472 |

So 6,232 is real and reproducible — it is just not what the sentence says it is. The heading and
surrounding prose are counted as part of "28 rows", overstating them by 21%.

### L3 — Low. Three further survivors that are each individually cheap

- `:151` `shown = str(index.relative_to(ROOT))` → `str(index)`: survives, because every case that
  reaches `main` passes a tempdir path (the `except ValueError` arm at `:152`). **No case drives
  `main` with an index inside `ROOT`**, so the relative-path form — the whole point of the try — is
  unwitnessed.
- `:145` `startswith("-")` → `startswith("--")`: survives, because case `:235` passes `--bogus`.
- `WARN_FRACTION = 0.90` → `0.9004`: survives `int()` truncation at both inputs of case `:205`
  (`900`, `1800`). Semantically negligible; recorded only because `0.99` *is* killed, so the band is
  pinned loosely rather than not at all.

---

## Refuted — what I attacked and could not break

- **C1's substance.** The defect was real and every named signal was green. `check-memory-link.py`
  checks reachability, `corpus_verdict` is a zero-floor, `check-docs.py` is a line budget; none reads
  the byte or character size of the always-loaded file. I looked for an existing signal that would
  make the guard redundant and found none — `check-docs.py` passes rc=0 on both commits. The
  magnitude is wrong (H2); the finding is not.
- **C3, in full, including the cost question.** The destination choice is right and I could not find
  the unaccounted cost. `recall-llm.py:431-432` is exactly as described —
  `[p for p in sorted(d.glob("*.md")) if p.name != "MEMORY.md"]` — so outside `docs/memory/` the rows
  are invisible to recall, and inside it without frontmatter they are #309 again. `slice-history.md`
  has valid frontmatter and a `FIRES-WHEN:` description, and `load_triggers` picks it up (159 vs
  158). A fire costs **four lines**, not the file: `render()` at `:845-854` emits the entry name and
  trigger only, and there is no per-injection size cap anywhere in the recall path. The matcher prompt
  grows **17,238 → 17,342 bytes** (+104, the trigger's 82-byte description plus framing). No declared
  corpus count elsewhere in the repo moved.
- **C4's stated half.** 7 declared mutations, 7 killed, 7 attributed to the case each names, over a
  control proved green on the isolated tree first. The two mutations added after surviving a first
  run (`CANNOT_RUN = 0`; `read_bytes` → `read_text`) do now kill — though see H1 for why the second
  one kills the wrong thing.
- **C5's preservation claim, which I tried hard to break.** All **28** rows removed from
  `MEMORY.md` are present **verbatim** in `slice-history.md` (28/28, set comparison on exact line
  text). Link integrity both directions: `MEMORY.md` 118 markdown links, 0 broken;
  `slice-history.md` 45 links and 3 wikilinks, 0 broken, 0 unresolved. The net row count reconciles
  (145 − 28 + 1 pointer = 118). Nothing anywhere in the repo cites a `MEMORY.md#` anchor. The
  harness symlink resolves (same inode, H4). ⚠ My first link run printed `md-links=0`, which was my
  own escaping bug, not a clean result; I re-ran it from a file with a known-positive probe
  (`definitely-not-a-file-xyz.md` must be *found* by the regex and *absent* on disk) before believing
  the zero.
- **The WARN band's defensibility (C2's second half).** 90% of 24,985 is 22,486, leaving 2,499 bytes
  of headroom against a limit known to ~51 bytes — about 49× the rounding uncertainty, and
  comfortably more than the ~3% byte/char excess from H1 (≈750 bytes at this size). The band absorbs
  both. It is advisory, which `:189` pins and manifest entry 6 defends. I could not construct a case
  where 90% is too tight or too loose.
- **The sibling-redundancy argument.** `check-memory-link.py` asks whether the corpus is reachable;
  this asks whether the index arrives. Different questions, and the second genuinely had no owner.

---

## The seven claims, as they stand

| | claim | verdict |
|---|---|---|
| C1 | the defect was real and silent | **TRUE in substance; the magnitude is wrong (H2)** |
| C2 | the limit is honestly sourced, bound complete, 90% defensible | **90% defensible; the bound is INCOMPLETE — it admits a lowered limit and not a wrong UNIT (H1)** |
| C3 | the destination choice is load-bearing and correct, at no unaccounted cost | **TRUE, verified in full** |
| C4 | the suite would notice the guard breaking | **REFUTED — 6 survivors, incl. `INDEX` retargeting (H3)** |
| C5 | nothing was lost in the move | **TRUE on rows and links; the corpus census is wrong (M4)** |
| C6 | the citation repair is durable | **True today, by luck; the ref is a moving locator (M6)** |
| C7 | row length is correctly excluded | **TRUE as a conclusion; measured in the wrong unit (L1)** |

On C7's falsifiability, which the prompt flagged as possibly unanswerable: it is **answerable, and I
answered it**. The harness truncates a **prefix**, not per row — this session's injected index stops
mid-file after row 137 of 145 with every delivered row intact and nothing elided inside them. So
total size is indeed the quantity that decides truncation, and C7's premise holds. The unit is
characters (H1).

---

## Verdict

**NOT CONVERGED.**

Two steps in the required `verify` job are red at the reviewed tip (B1, B2), which settles the
verdict on its own and is mechanical to fix: one list entry at `check-plan-code.py:3461`, one
literal at `:5185`, one entry in `check-selftest-counts.POPULATION`.

The findings that need a decision rather than a keystroke are H1 and H3. **H1 is the one I would not
let through**, because it is not a wrong sentence but a wrong invariant with a test and a mutation
entry holding it in place: fixing the docstring (as the working tree is doing) while `:215` still
asserts *"index_size counts BYTES, not characters"* and manifest entry 4 still reddens on
`read_text()` leaves the guard measuring the wrong quantity with two artefacts defending it. The
direction is safe — this cannot produce a false green — so it is High and not Blocking, and the
repair is a judgement about which unit to enforce, not a correction of prose. H3's mutation A is one
manifest entry and one case that names the *path* rather than the size.

H2 is cheap per site and expensive to leave: four copies, two of them inside the recall corpus, of a
figure that is wrong by a factor of about four in the numerator and takes its denominator from after
the change. This repository's own measured lesson about second copies applies to numbers as well as
rules, and the correct figure — **8 rows**, measured from a session that actually received the
truncated index — is now on the record here.

Nothing I found undermines the decision to build this guard, or the choice of destination for the
rows. The index really was being truncated in silence, and this session is the proof: I was handed
the pre-fix index, 137 rows of 145, with the harness's warning attached and eight rules I never saw.

---

# Postscript — re-measured after the Codex fold

Everything above is pinned to `0cb448cb`, as briefed. The branch has since gained two commits and
an uncommitted fold:

- `bc165e93` — *"The mutation count is declared TWICE on purpose, and I updated only one of them"*
- `9e3dbe62` — *"Round 1's Codex half: the guard could have measured the WRONG FILE with every case
  green, and my citation fix was the same bug again"*
- **and, while I was re-measuring, the working tree switched the guard from BYTES to CHARACTERS**,
  with the reasoning at `:166` citing `26,930/1024 = 26.30 -> "26.3KB"` — H1's measurement, landing
  as I wrote it up.

So B1, B2, M1, M2, M3, M4, H3's mutation A and the bytes-vs-chars half of H1 are all **FIXED**, each
found independently of me. Recording that as corroboration, not priority.

## ⛔ Three rows of my own earlier postscript were WRONG, and the error is this repo's named one

I reported H2 and M1 as still live at `9e3dbe62` on the strength of `grep -c`. Both counts were
right and both conclusions were wrong, because I counted occurrences of a string without reading
them — `measure-the-population-the-code-actually-sees`, with the known-positive check I had applied
to the link sweep and not to this.

| I said | actually |
|---|---|
| H2 live in the guard file | **FIXED** — `:13-17` *retracts* it: *"This said 'roughly 30 of its 118 rows'. **146** lines began `- `…"*. My grep matched the retraction |
| M1 (`PermissionError` → rc 1) live | **FIXED** — `except OSError: return None` at `:179` |
| `is_file()` → `exists()` a surviving defect | **not a defect** — with `OSError` caught, a directory raises `IsADirectoryError` (an `OSError`) → `None` → rc 2. Behaviour-preserving; surviving is correct |

## N1 — High. A mutation that leaves all 40 cases green, in BOTH the committed and the uncommitted version — and it survives because of a FIXTURE VALUE, not a missing case

This is the one you asked for. `budget_verdict`'s overage arithmetic:

```python
            f"{n_bytes - limit:,} bytes of rows never arrive. …"      # 9e3dbe62
            f"{n_chars - limit:,} characters of its tail never arrive. …"   # working tree
```

Replace the subtraction with the bare total — `{n_bytes - limit:,}` → `{n_bytes:,}` — and the suite
stays **40/40 green**, over a control proved green first, in *both* versions.

There **is** a case for it, at `:253-254`:

```python
    check("the OVER message states the overage, not just the size",
          "1 bytes of rows never arrive" in budget_verdict(L + 1, L)[1], True)
```

It passes vacuously. With `L = 1000` the fixture makes `n_bytes = 1001`, so the mutant renders
`"1,001 bytes of rows never arrive"` — and `"...001 bytes of rows never arrive"` **contains** the
needle `"1 bytes of rows never arrive"`. The overage is a decimal suffix of the total, so a
substring assertion cannot tell them apart. Measured:

```
L=1000  n_bytes=1001
  original message fragment : '1 bytes of rows never arrive'
  mutated  message fragment : '1,001 bytes of rows never arrive'
  -> original passes : True
  -> MUTANT  passes  : True   <-- '001 bytes' ends in '1 bytes'
```

The repair is a **fixture value, not a new case** — and the failure generalises to every round limit
anyone would pick:

| `L` | mutant renders | vacuous? |
|---|---|---|
| 1000 | `1,001 bytes …` | **yes** |
| 2000 | `2,001 bytes …` | **yes** |
| 500 | `501 bytes …` | **yes** |
| **1234** | `1,235 bytes …` | no — reddens |

Any `L` ending in `0` hides the mutation. This is
`exercise-the-producer-at-two-distinct-inputs` — *"a case is satisfied by the CONSTANT its own
fixture supplies"* — and `a-case-can-pass-for-an-ambient-reason`, whose tell is NAME vs BODY: the
name says *the overage, not just the size*; the body cannot distinguish them.

**OBSERVATION THAT WOULD MAKE THIS FAIL:** that mutation reddening any of the 40 cases. It does not.
Changing `L` to `1234` (or asserting on the whole fragment with a non-suffix overage) makes it red.

### The other survivors at the tip, same control

| mutation | `9e3dbe62` (bytes) | working tree (chars) |
|---|---|---|
| overage → total (N1) | **SURVIVED** | **SURVIVED** |
| `if n_… is None:` → `… is None or … == 0:` | **SURVIVED** | **SURVIVED** |
| `except OSError: return None` → `return 0` | **SURVIVED** | anchor gone |
| `unknown_args` → `not a.startswith("--self-test")` | **SURVIVED** | **SURVIVED** |
| `WARN_FRACTION 0.90` → `0.9004` | **SURVIVED** | **SURVIVED** |
| `100 * n // limit` → `round(100 * n / limit)` | **SURVIVED** | — |
| `read_bytes()` → `stat().st_size` | killed | — |
| `int(24.4 * 1024)` → `int(24.4 * 1000)` | killed | — |
| `shown` → `INDEX_LABEL` | killed | — |
| `INDEX` → sibling file | killed (36/40) | — |
| `>= warn_at` → `>= limit` | killed | — |

Two are worth more than their size. `except OSError: return 0` makes an **unreadable** index report
*"is EMPTY. That is not a small index, it is a missing one"* — so the r1 CODEX #6 fix's own
distinguishing behaviour is unwitnessed; rc stays 2, and the suite cannot tell the two diagnoses
apart even though `:122-124` calls them distinct. And `is None or == 0` leaves the EMPTY arm
unreachable for the same reason. Both are message-identity gaps, which is the class N1 belongs to.

## N2 — High. The working-tree/committed split: the guard CAN catch the live failure and is NOT WIRED TO. Demonstrated with two worktrees at one commit

Your question was whether the split makes the guard unable to catch what it was built for. Measured
answer: **the capability is real; the wiring is the hole.** Two worktrees, same HEAD `9e3dbe62`,
same guard, differing only in whether the overflow is committed:

| | index the guard read | verdict |
|---|---|---|
| **A** — working tree grown past the limit, **nothing committed** | 26,535 bytes | **rc=1, `OVER BUDGET`** |
| **B** — fresh checkout of the *same HEAD* (what CI sees) | 22,333 bytes | **rc=0, `ok`** |

In state A the harness is truncating the index *at that moment*. The guard detects it — because
`INDEX` is `ROOT / "docs" / "memory" / "MEMORY.md"` (`:85`) and a session loads that same path
(same inode, via the directory symlink `~/.claude/projects/<slug>/memory → docs/memory`). So the
guard is **not** structurally blind the way every git-shaped check in `23e5a349` was.

But nothing runs state A:

```
$ grep -rl memory-index-budget .claude/hooks/      ->  nothing
$ grep -l  memory-index-budget scripts/check-schema-gates.sh scripts/check-merge-ready.py  ->  nothing
$ grep -rn check-memory-index-budget.py .github/workflows/*.yml
    ci.yml:252   run: python3 scripts/check-memory-index-budget.py
    ci.yml:255   run: python3 scripts/check-memory-index-budget.py --self-test
```

Two callers, both CI, both measuring the committed tree. And `.github/workflows/ci.yml:248-249`
still says:

```
      # the link, this one is NOT advisory on a runner: `docs/memory/MEMORY.md` is committed, so
      # CI measures exactly the file a session loads.
```

State B is that sentence being false while the guard says `ok`. "`MEMORY.md` is committed" is an
observation about one moment's `git status`, not a property — and it was false for the whole window
in which this very defect was being fixed.

**This is backlog #309's class exactly**, and `23e5a349`'s own commit subject is the statement of it:
*"the corruption was WORKING-TREE ONLY, which is why no git-shaped guard can catch it."* The repair
is one line of wiring (a hook, or a line in an aggregate local runner), plus deleting a claim that
is not true.

⚠ **I caused a real hazard establishing this.** My first attempt grew `docs/memory/MEMORY.md` **in
the main working tree** — the live injected memory index, with other agents active in this repo. I
restored it immediately (`git checkout --`, verified 22,333 bytes and a clean diff) and redid the
experiment in throwaway worktrees, which is where it should have been from the start.
`an-instrument-that-edits-the-repo-corrupts-its-peers` is the memory, and I read it after the fact
rather than before.

## N3 — High. The NOT VERIFIED caveat does NOT make the gate unfalsifiable. The problem is the opposite: the sentence two lines above it states a byte-prefix figure as measured, and that figure is wrong

Your third question. Taking the two halves separately.

**Is the central claim unfalsifiable?** No. The gate's rule is *size > limit → fail*, and its pass
direction is sound: guard-green ⇒ chars ≤ bytes ≤ limit ⇒ no truncation. `:62-66`'s revised
falsifier list (harness warning while green · a controlled boundary experiment · a published
producer spec) is a genuine improvement over the earlier "the ONLY" overclaim. The caveat bounds the
*message*, not the verdict.

**But the caveat now disclaims a model that the docstring is still using.** `:19-24` says it is not
established *"that the cut is a byte prefix rather than per-row, nor where it lands."* Five lines
above, `:15-17` asserts:

```
And the dropped amount is **2,820 bytes = 24 newlines of tail, beginning
MID-ROW** — so "30 rows" was never established by anything.
```

`2,820` is exactly `27,805 − 24,985`: a byte-prefix-at-the-limit calculation. The correction replaced
one unmeasured figure with three more, all derived from the model the next paragraph declines to
assert. And **I can measure the cut**, from this session's own truncated context:

| | docstring (r1 CODEX #4) | measured |
|---|---|---|
| bytes that did not arrive | 2,820 | **2,034** |
| newlines in the dropped tail | 24 | **19** |
| where the cut lands | **MID-ROW** | **a clean row boundary** — the delivered text ends with the complete row `…The only sanctioned ratchet FALL` |
| cut offset | implied byte 24,985 | **char 24,958 / byte 25,771** |
| rows not delivered | — | **8** (row 137 of 145 was the last) |

So the truncation algorithm is *not* unverifiable — it is **verified, and it is a character prefix
at a row boundary**. The caveat is too pessimistic about what is knowable and too permissive about
what the file already asserts. The honest form is to record the measurement and keep the caveat only
for what remains open (whether the cut is pre- or post-framing, and whether KB is 1000 or 1024).

This also lands on the shipped message. `budget_verdict` still renders
*"roughly the last {n − limit:,} … never arrive"* — which for the index that actually overflowed
would have printed **2,820** against a true **2,034**, a 39% overstatement, in the one sentence a
reader acts on. N1 is why no case notices.

## N4 — Medium. The retracted `~30` figure is still asserted at three sites, two of them inside the recall corpus — so the branch now contradicts itself

`:13-17` retracts it. These three still state it, in the latest working tree:

- `.github/workflows/ci.yml:246` — *"~30 of its 118 rows were silently dropped before any of it was read"*
- `docs/memory/MEMORY.md:140` — *"it stood at 27,805 and ~30 rows had stopped arriving"*
- `docs/memory/slice-history.md:9` — *"roughly 30 index rows were dropped"*

This is worse than the stale number I filed as H2, because the guard now explicitly says the figure
*"was never established by anything"* while three siblings assert it — and the two in `docs/memory/`
are corpus content, so they will be recalled and believed. The measured figure is **8 rows / 2,034
bytes**. `a-second-implementation-of-one-rule-drifts`, applied to a number: the fix reached the
file under review and none of its copies, which is `after-fixing-search-for-the-class`.

M5 also stands unchanged: `grep -c check-memory-index-budget docs/dev-process.md` → **0**.

## Verdict

**NOT CONVERGED.**

The two Blocking findings are gone and the fold is real — eight of my twelve `0cb448cb` findings are
fixed, and the bytes-vs-characters question is being settled correctly as I write. What is left is
four things, none of them mechanical:

1. **N1** — a mutation leaving all 40 green in both versions, surviving on a fixture coincidence. The
   repair is one constant (`L = 1234`), but the class matters more than the instance: two further
   survivors are the same message-identity gap, and the manifest's 12/12 is measured against a suite
   that cannot distinguish a total from a difference.
2. **N3** — the replacement figure for the retracted one is itself wrong (2,820/24/mid-row vs a
   measured 2,034/19/row-boundary), and the caveat that should have caught it instead licenses it.
   The truncation algorithm is verified; the file says it is not.
3. **N2** — the guard can see the live failure and nothing runs it where that failure lives, while
   `ci.yml:248-249` asserts the opposite. One line of wiring, one false sentence.
4. **N4 / M5** — three uncorrected copies of a figure the guard itself retracts, and no pointer row.

Of these, **N3 is the one I would hold the round for**, because it is the second round in a row in
which the correction of a number introduced a new unmeasured number, in the same paragraph, from the
same byte-prefix assumption. That is a fix-created-next-finding pair on one component. It is not yet
`dev-process.md`'s thrashing condition — the arming condition needs **two consecutive** rounds whose
findings came from the previous round's own fix, and this is the first — but it is the first half of
one, and the answer if round 2 produces another is Phase 6 rather than a third correction of the
same sentence.

Nothing in this postscript undermines the guard. It is measuring the right file, it now measures the
right unit, and the defect it was built for was real: I was handed the truncated index myself, 137
rows of 145, and the eight I never saw are the evidence.

---

# Final re-measure — the fold caught up mid-postscript

The tree moved twice more while the postscript above was being written. Re-measured against the
files as they now stand (suite **42 cases**, control green):

| finding | status | evidence |
|---|---|---|
| N3 | **FIXED** | the `2,820 bytes = 24 newlines … MID-ROW` sentence is gone; the docstring now reads *"**Measured, 8 rows**"* and narrows the caveat to *"the UNIT is established and the ALGORITHM is not"* |
| N4 | **FIXED** | all three sites now carry retractions; `ci.yml:248` cites *"and all three numbers were wrong. The 8 was counted out of…"* |
| **N1** | **STILL LIVE** | `L = 1000` at `:253`, case at `:260`; overage → total still **SURVIVES 42/42** |
| **N2** | **STILL LIVE** | `ci.yml:251-252` unchanged; `.claude/hooks/` and both aggregate runners still name the guard **zero** times |
| M5 | **STILL LIVE** | `grep -c check-memory-index-budget docs/dev-process.md` → 0 |

⛔ **And N3's final wording corrects an over-reach of mine, which I accept.** I wrote that the
truncation algorithm is *"verified, and it is a character prefix at a row boundary"*. The docstring's
version is more careful and is right: the observed cut sat 27 characters under the declared limit,
i.e. one row short of it, and that is **consistent with a prefix cut and a row-wise cut alike**. My
measurement establishes the **unit** (characters, not bytes — byte offset 25,771 cannot be a cut at
24,985) and the **magnitude** (8 rows, 2,034 bytes). It does not discriminate the algorithm, and
saying it did was the same shape as the thing I was filing: a measurement whose conclusion reached
past its evidence.

## Verdict

**NOT CONVERGED** — on two findings, both open, neither mechanical.

**N1** is the answer to *"find the mutation I did not write"*: replacing the overage with the bare
total leaves **42/42 green**, in all three versions of this file I have measured (bytes at
`9e3dbe62`, characters uncommitted, and the current 42-case tree). The case for it exists and passes
vacuously, because `L = 1000` makes the overage a decimal suffix of the total. `L = 1234` reddens it.
The instance is one constant; the class is that the manifest's 12/12-killed is measured against a
suite that cannot distinguish a total from a difference — two other survivors
(`is None or == 0`, `except OSError: return 0`) are the same message-identity gap.

**N2** is the answer to *"does the working-tree/committed split defeat it"*: **no, and that is the
problem** — the guard detects a working-tree-only overflow (rc=1 at 26,535 bytes) and nothing runs it
there, while CI, its only caller, reads the committed blob and says `ok` at the same HEAD. One line
of wiring, and one sentence at `ci.yml:251-252` that asserts the opposite of what I measured.

The guard is sound and the defect was real. Eleven of my thirteen findings were fixed inside the
round, most of them before I could file them, and the two that remain are the two that no reviewer
on this round had yet looked for.
