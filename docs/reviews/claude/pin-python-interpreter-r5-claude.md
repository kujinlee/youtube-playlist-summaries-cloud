# pin-python-interpreter — round 5 — Claude half

**Verdict: NOT CONVERGED. 3 Medium.** The r4 High is genuinely fixed and the corpus is unaffected,
but there is an **eighth defect** (same class, new key name), a **regression** against `5206e020`
that hides a real pin, and the **closing half of the new scoping rule has no falsifier** — the two
clauses where both new defects live.

Subject: `pin-python-interpreter` HEAD `020b04ad`, delta `git diff 5206e020..020b04ad -- scripts/`.

```
$ git rev-parse --abbrev-ref HEAD && git rev-parse --short HEAD
pin-python-interpreter
020b04ad
$ git status --porcelain
?? docs/reviews/claude/pin-python-interpreter-r5-claude.md      # only this file
$ (in a mktemp copy) python3 check-python-pin.py --self-test
75/75 passed
```

Constraints honoured: read-only git; every probe on `git show`/`git archive` copies in `mktemp -d`;
`check-plan-code.py --mutate .` never run against the working tree (I imported `run_mutations` and
ran only the two new entries against a copy); `docs/reviews/` top level untouched.

---

## What the fix does deliver — measured first

| check | `5206e020` | `020b04ad` |
|---|---|---|
| Codex's r4 fixture (`strategy.matrix.include` of mappings) | `['9.9']` — false green | **`[]`** ✅ |
| `.github/workflows/ci.yml` | `['3.12']` | `['3.12']` ✅ |
| `.github/workflows/schema-gates.yml` | `['3.12', '3.12']` | `['3.12', '3.12']` ✅ |

No corpus regression, and the defect the round exists for is closed.

---

## F1 — Medium — an EIGHTH defect: the rule keys on the NAME `steps:`, so any other `steps:` key is a steps sequence

```yaml
jobs:
  verify:
    strategy:
      matrix:
        steps:                                   # <- a matrix DIMENSION that happens to be named `steps`
          - uses: actions/setup-python@v5
            with:
              python-version: '9.9'
    steps:
      - run: echo hi
```

`declared_pins → ['9.9']` at **both** commits. The job has no `setup-python` step; the pin is a
matrix value. Same false green, same job shape, same direction as the r4 High — one key name away
from the fixture the fix was written for.

`opens_steps = re.match(r"^(\s*)steps:\s*(#.*)?$", line)` asks *is this line the text `steps:`?*
and has no notion of where in the document it sits. Your own r4 lesson was *"I tested the shape of
the container, not the shape of its contents."* This is that lesson one level out: the new rule
tests the **name** of the container and not its **position**.

**Why Medium and not High, stated so the grade is arguable rather than asserted:** Codex's r4
fixture is an everyday GitHub Actions idiom (`matrix.include` is how most matrices are written);
a matrix dimension *named* `steps` is not. The routes that remain open are narrow — comments are
stripped (`_structural:282`) and block scalars are masked, so a spurious `steps:` must be a real
YAML key with a mapping/sequence value: `strategy.matrix.steps`, or a reusable-workflow input named
`steps` (F2's shape). None occurs in this repository today.

---

## F2 — Medium — REGRESSION against `5206e020`: a nested `steps:` key makes a real pin disappear

```yaml
jobs:
  verify:
    steps:
      - name: odd action
        uses: someone/thing@v1
        with:
          steps:                   # <- an action input that happens to be named `steps`
            - a
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
```

| | `5206e020` | `020b04ad` |
|---|---|---|
| `declared_pins` | `['3.12']` | **`[]`** |

A pin that was visible one commit ago is now invisible, and the job reads UNPINNED — r2 H1's exact
failure mode: the author looks at a pinned step while the guard tells them to add one or to put the
job in `EXEMPT_JOBS`.

**Two compounding causes, traced rather than inferred:**

1. `steps_indent` is (re)assigned by *any* line matching `steps:`, with no notion of nesting — the
   inner key at indent 10 silently replaces the job's `steps:` at indent 4.
2. The dedent-out-of-steps check runs **before** the step-body check:

   ```python
   if line.strip() and indent <= steps_indent and not m:
       steps_indent, cur = None, None      # <- fires on the REAL step's body lines
       continue
   if m and (cur is None or len(m.group(1)) <= cur.indent):
       ...
   if cur is None:
       continue
   if line.strip() and indent <= cur.indent:
   ```

   The real step at indent 6 *is* created (a dash escapes clause 1 via `and not m`), but its body
   lines at indent 8 satisfy `8 <= 10` and are discarded, taking `cur` with them. So a wrong
   `steps_indent` does not merely mis-scope — it **eats the bodies of correctly-identified steps**.

Direction is fail-closed, which is the safer half, and the likelihood is the same low one as F1.
The reason it is worth a finding at that likelihood: it is a *regression*, so it is not the
pre-existing risk being carried forward, and the mechanism (clause ordering) is general.

---

## F3 — Medium — the CLOSING half of the new rule has no falsifier, and both defects above live there

Every clause of the new scoping rule mutated on a copy, control green at 75/75 first:

| mutation | result |
|---|---|
| `opens_steps = None` (the rule never fires) | 33 red ✅ |
| `steps_indent: int \| None = None` → `= -1` at the **initialiser** (*your manifest entry*) | 3 red, attributed ✅ |
| `steps_indent, cur = len(opens_steps.group(1)), None` → `= -1, None` (the **captured value**) | **SURVIVED** |
| delete the whole `if line.strip() and indent <= steps_indent and not m:` block (the **close**) | **SURVIVED** |

So the suite holds *that the rule exists* and *that it starts closed*, and holds nothing about
**what indent it captures** or **when the block ends**. Those are precisely the two clauses F1 and
F2 exploit: F1 is a wrong capture, F2 is a capture plus a premature close.

Two cases would close it, and neither needs a new fixture family:

* a job whose `steps:` block is followed by another job — assert the second job's steps are still
  found *and* that a list after the block (a `strategy.matrix.include`) is not, which fails if the
  close is deleted;
* a step body line at an indent between the job's `steps:` and a deeper `steps:`-named key —
  F2's fixture, which fails if the captured value is wrong.

This is r3 F4 recurring in the new code: the clauses that make the partitioning *work* are again
the ones nothing holds, while the clauses the round is *about* are well covered.

---

## Item 2 — the 22 rewraps: NO silent change found

The hazard is that rewrapping a bare fragment in `    steps:` makes a case pass because the step
became invisible rather than because the rule under test fired. Checked two ways.

**(a) Every negative fixture still yields a step.** For all nine `== []` fixtures, `_steps` returns
exactly **1** step, and the `with:` block is present in the seven fixtures that carry one — so
nothing is passing because there was nothing to examine.

**(b) The rule each case names still reddens THAT case:**

| mutation | reddens |
|---|---|
| `with:` opener widened to any key (`^\s*\w+:`) | `a python-version under env: … is NOT a pin`, `…an env: sibling AFTER with:` — the 2 env cases, nothing else |
| `_BLOCK_SCALAR` never matches | the 4 block-scalar cases (heredoc / folded / `\|-` / heredoc-contains-a-pin) |
| contents regex widened to `actions/` | `a named step around an UNRELATED action is still not a pin` — exactly 1 |

Each family reddens its own members and no neighbours. The rewrap preserved what these cases test.

---

## Item 3 — both new mutations attribute to exactly one case

Run through the real `run_mutations` (imported from the branch's own `check-plan-code.py`, applied
to a `git archive` copy):

```
entries: 33   unique anchors: 33   unique names: 33
ok = True   survivors = []
  caught=True attributed=True  red=5  the block-scalar mask is removed from the SPLITTER …
  caught=True attributed=True  red=3  the steps: scope starts OPEN, so any YAML list … is read as steps
```

Your correction of the failed first attempt is sound: mutating the **initialiser** to `-1`
reproduces the pre-fix state (`steps_indent is None` never short-circuits), and the matrix case
asserting `[]` genuinely reddens — unlike `opens_steps = None`, which made every case return `[]`
and left that assertion trivially satisfied. Arithmetic also derived independently:
`sum(EXPECTED_MUTATIONS.values()) = 862` = the declared `862`; `check-python-pin.py` pinned at
**33** = 33 entries on disk.

---

## Attacks that produced NOTHING — the ones that matter for merge

| probe | result |
|---|---|
| `steps:` inside a `run: \|` block | `[]` — masked by `_structural` ✅ |
| a **comment** at the `steps:` indent, with the real pin after it | `['3.12']` ✅ — I expected this to close the block; comments never reach `_steps` (`_structural:282`, the r3 F4 follow-through). My hypothesis was wrong and the code is right |
| a dash at the **same indent** as `steps:` (legal YAML) | `['3.12']` ✅ — this is what `and not m` is for |
| `steps:` with a trailing comment (`steps:   # the real ones`) | `['3.12']` ✅ |
| CRLF on the `steps:` line | `['3.12']` ✅ |
| two jobs, each with `steps:`, pin in the second | `['3.12']` ✅ |
| blank line inside the steps block | `['3.12']` ✅ |
| `strategy:` written *after* `steps:` in the same job | closes correctly, matrix not read ✅ |

---

## Verdict

| check | result |
|---|---|
| the r4 High is fixed | ✅ `['9.9']` → `[]` |
| no corpus regression | ✅ both real workflows unchanged |
| the new scoping rule holds | ❌ **F1** (eighth defect — any `steps:`-named key) and ❌ **F2** (regression: a nested `steps:` key eats a real step's body) |
| the 22 rewraps kept their meaning | ✅ measured both ways |
| the two new mutations | ✅ both attribute to exactly one case, `ok = True` |
| declared counts (862 / 33) | ✅ derived independently |
| `_steps`' own new clauses | ❌ **F3** — the captured indent and the close both survive mutation |
| control | ✅ 75/75 |

**NOT CONVERGED**, on three Mediums that are cheap to close:

1. scope `steps_indent` to the nesting it was captured at (a deeper `steps:` must not replace an
   outer one, and a `steps:` that is not a job key should not open a block at all — the job-level
   depth is already derivable from `job_blocks`);
2. order the two dedent checks so a wrong `steps_indent` cannot discard a step body;
3. add the two cases in F3 so the closing half is held by something.

⚠ F1 and F2 are both low-likelihood and neither fires on any workflow in this repository — I would
not block a merge on them alone if the structural question were not already open. It is: this is the
eighth defect in one function, all one root cause, and #153 is where "parse or refuse" gets decided.
Nothing here argues with that decision; it supplies two more data points for it.

**REVIEW GAP: none for this half.** Codex is running concurrently on the same delta as round 5's
other half.
