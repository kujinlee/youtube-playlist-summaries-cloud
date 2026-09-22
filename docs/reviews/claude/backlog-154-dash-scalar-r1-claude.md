# backlog #154 — a block scalar opened on the DASH line — review round 1, Claude half

**Subject:** branch `backlog-154-dash-block-scalar` @ `42aa336b`, off master `b184bbbc`, PR #331 (OPEN).
**Files:** `scripts/check-python-pin.py`, `scripts/mutations/check-python-pin.json`,
`scripts/check-plan-code.py` (two counts), `docs/backlog.md`, `docs/roadmap-to-launch.md`,
`docs/dashboard-entries.md`.

**Verdict: the fix is correct and the bookkeeping is right. 1 High, 3 Medium, 3 Low — none of them
says the fix is wrong.** The High is that *the fix's own stated invariant cannot fail*: the obvious
alternative spelling of the same repair loses a real pin and the suite stays 86/86 green.

**How this half was run.** Everything below was measured on temp copies under a redirected `HOME`;
nothing in the repo was modified except this file. Where a question was about YAML rather than about
the guard, the oracle is **libyaml via ruby's Psych** (`/usr/bin/ruby`, PyYAML is not installed here),
used as a differential oracle against `declared_pins`.

---

## Findings

### H1 — Blocking? No. **High:** the non-capturing group is load-bearing, correct, and **unfalsifiable**

The fix's own ⚠ comment (`scripts/check-python-pin.py:308-310`) says:

> `(?:-\s+)?` is NON-capturing on purpose: `group(1)` must stay the text before the KEY, because
> `_structural` uses its length as the scalar's indent and compares body lines against it.

**That claim is true and it matters.** The obvious alternative spelling of the same repair —
capturing only the whitespace, leaving the dash outside, which is what a reader "simplifying" the
regex would write —

```python
_BLOCK_SCALAR = re.compile(r"^(\s*)(?:-\s+)?[\w.\-]+:\s*[|>][-+0-9]*\s*(#.*)?$")
```

makes `group(1)` the **dash** column instead of the **key** column, so `_structural:366`
(`scalar_indent = len(m.group(1))`) sets the scalar two columns too shallow and then swallows the
step's own sibling keys. Measured, on this fixture (dash at 6, keys at 8):

```yaml
jobs:
  verify:
    steps:
      - run: |
          echo hi
        name: real
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
```

| reader | `declared_pins` |
|---|---|
| libyaml (ruby Psych) — the truth | `["3.12"]` |
| HEAD (`42aa336b`) | `['3.12']` ✅ |
| dash-column variant | `[]` ❌ **a real pin lost — the MISS direction, r2 H1's failure mode** |

**And the suite does not notice:** with that variant applied, `python3 check-python-pin.py --self-test`
prints **`86/86 passed`, rc 0**. No case and no manifest entry distinguishes the key column from the
dash column, so the invariant the comment goes out of its way to state is guarded only by the
comment. This is the file's own most-repeated lesson (*a stated bound with no falsifier*; *assert the
property, not the mechanism*), applied to the fix for it.

**Concrete repair — one case and one manifest entry:**

* case: the fixture above, `declared_pins(...) == ["3.12"]`, named something like
  *"a sibling key at the KEY column ends a dash-opened scalar, so the step's real pin survives"*.
  Verified: green on HEAD, red under the variant.
* manifest entry anchoring `"^(\\s*(?:-\\s+)?)[\\w.\\-]+:"` → `"^(\\s*)(?:-\\s+)?[\\w.\\-]+:"`,
  `expect` naming that case. Anchor is unique in the file today (checked).

This also matters beyond this branch: **#155 moves this regex and this comment into
`scripts/workflow_structure.py`**, and a transferred mutation has to exist before it can be
transferred.

---

### M1 — the comment's causal story is **inverted**, and the same sentence is in backlog row 154

`:303-306` (and, verbatim in substance, the `| 154 |` row body) asserts:

> inside `_steps` this shape cannot occur — `Step.body` blanks the dash before `_structural` ever
> sees the line (`:264`) — so the function was CORRECT about a step's lines and silently weaker
> about a whole file's

Measured:

* `_structural` has **exactly one call site in the repository**: `check-python-pin.py:232`,
  `structural = _structural(text.split("\n"))`, on the **whole file**. `grep -n "_structural("` →
  `:232` (call), `:314` (def). It has never had another: `git log -L 232,232:scripts/check-python-pin.py`
  shows the line born in `e7ed8c1a` already in that form.
* `:264` (`cur = Step(len(m.group(1)), [" " + m.group(2)])`) sits **inside the loop over
  `_structural`'s output**. So the blanking happens strictly *after* masking, not "before
  `_structural` ever sees the line". The ordering in the sentence is backwards.
* **"Inside `_steps()` this never bites" is false** — the live defect goes *through* `_steps`.
  `declared_pins:392` iterates `_steps(text)`, and `_steps:232` is what calls `_structural`.
  Reproduced end-to-end on a two-job fixture with a real `cat <<'EOF'` heredoc:

  | | `declared_pins` | `unpinned_jobs` | `verdict(in_ci=True)` |
  |---|---|---|---|
  | pre-fix regex | `['3.12', '3.12']` | `[]` | `(0, 'python pin OK — every job pins 3.12, …')` |
  | HEAD | `['3.12']` | `['ci.yml:schema-gates']` | `(1, 'FAILED — 1 job(s) pin no Python version…')` |

The **true** statement is narrower: the shape cannot appear *in a `Step.body`*, because the dash is
blanked there — so a hypothetical consumer that re-masked a step body would be unaffected. **No such
consumer exists.** The "correct at the level it was built for" framing rests on a level that exists
only in the docstring's wording (*"the lines of a step"*), not in any call site.

Why this is a Medium rather than a Low: the sentence is the rationale that will be **carried into the
shared library by #155**, and the row an implementer reads carries it too. A wrong mechanism in a
comment is how the previous four `declared_pins` defects each survived a round.

---

### M2 — the second half of the same ⚠ is simply not true

> Capturing the dash separately would renumber the trailing comment group, **which two callers read**.

`_BLOCK_SCALAR` has **one** consumer — `:364-366` — and it reads **only `group(1)`**. The
trailing-comment group has **zero** readers (`grep -n "group(" check-python-pin.py` →
`:263`, `:264` are `_steps`' own dash regex; `:366` is `m.group(1)`; `:444`, `:488-489` are other
functions). `_STEPS_KEY`'s comment group is likewise unread (`:255`, `:257` read `group(1)`).

So the renumbering argument is invented; the real reason is the indent semantics stated in the first
half, which H1 shows is worth a case. Suggest deleting the clause rather than fixing it — a
justification that does not hold is what H1's missing case had to stand in for.

---

### M3 — the class was not swept: three sibling spellings still manufacture a phantom pin

Differential run against libyaml, all fixtures a single job whose only step is a dash-opened scalar
quoting `uses: actions/setup-python@v5` + `python-version: '9.9'`:

| fixture | libyaml truth | pre-fix | HEAD |
|---|---|---|---|
| `- run: \|` | `[]` | `['9.9']` | `[]` ✅ |
| `- run: >` / `\|-` / `\|+` / `>-` / `\| # note` | `[]` | `['9.9']` | `[]` ✅ |
| `- run: \|2` (explicit indent indicator) | `["9.9"]` (the scalar is empty; the lines **are** structure) | `['9.9']` | `['9.9']` ✅ agrees |
| `-\trun: \|` (tab after dash) | **INVALID YAML** (`Psych::SyntaxError`) | `['9.9']` | `[]` — harmless over-acceptance |
| **`- - run: \|`** (nested sequence) | `[]` | `['9.9']` | **`['9.9']` ❌ false pin** |
| **`- "run": \|`** (quoted key) | `[]` | `['9.9']` | **`['9.9']` ❌ false pin** |
| **`- run: &a \|`** (anchor on the value) | `[]` | `['9.9']` | **`['9.9']` ❌ false pin** |

All three survivors are the **same false-green direction as #154**, unchanged by this fix, and none
occurs in this repository's workflows today. Two things make this worth filing rather than shrugging
at:

1. **The anchor case has an in-file precedent 13 lines above.** `_STEPS_KEY` was widened to
   `(?:[&!]\S+\s*)*` in r5 (codex Medium) for exactly this — *"an anchor (`&name`) or a tag is node
   METADATA, not a value"* (`:284-295`). The sibling pattern in the same paragraph of code did not
   get the same treatment, which is *after fixing, search for the class*.
2. **`_structural`'s docstring keeps an explicit KNOWN BOUND list** (flow mappings, escaped
   newlines) precisely because *"that is exactly the kind of sentence that has been wrong twice on
   this branch"*. These three shapes belong on that list if they are not being closed — and #155
   promotes this reader into `check-ratchet-contract.py`, so an unstated bound travels with it.

Cheapest closure if wanted now: `(?:[&!]\S+\s*)*` before `[|>]`, and `["']?[\w.\-]+["']?` for the
key. Either way, state it or close it.

---

### M4 — the repair's *non-vacuity* is not pinned, which is the defect this row exists to end

The repaired case (`:899-903`) is genuinely load-bearing **today**: revert the regex and it reds
(measured, below). But nothing pins the property that makes it load-bearing — the `uses:` line in
its fixture. Measured on temp copies:

| edit | suite |
|---|---|
| remove `"          uses: actions/setup-python@v5\n"` from the repaired case's fixture only | **86/86 green** |
| …the same removal **plus** the regex reverted | **84/86** — only the two *new* cases red; **the repaired case passes** |

So the exact regression #154 is a row about — this case quietly going vacuous — is still invisible to
every guard. That is why the coordinator's deleted third mutation could not work (see S8: deleting it
was right), but **a defence does exist and costs no new mutation**: `expect` accepts a **list**, and
every entry must resolve to exactly one *red* case (`check-plan-code.py:1419-1443`, `:1481-1483`).
Adding `"...and a job holding only those still reports as unpinned"` to entry 29's `expect` makes the
vacuity edit a **harness failure** (the second row above shows that case is not red under it), while
costing nothing today (it *is* red under the mutation as shipped — measured, 3 reds).

---

### L1 — 9 manifest entries of pure escaping churn, in a file where the diff is the review surface

`scripts/mutations/check-python-pin.json` was re-emitted with `ensure_ascii=True`: nine entries
change only `—` → `—` and `⚠` → `⚠`, in `name`, `expect` **and `edits` anchor strings**.
Semantics are unaffected (verified: all 40 anchors still match exactly once and all 40 still kill),
but it triples the diff of the one file where an unnoticed anchor change is the known failure mode.
Re-emit with `ensure_ascii=False` so the next reader sees the two real changes.

### L2 — the tick's mutation arithmetic does not reconcile as written

`docs/backlog.md` row 154 and the roadmap both say *"mutations 39 → 40 (one retargeted …, one added,
**one deleted as unkillable**)"*. Read literally that is 39 + 1 − 1 = 39. Measured against
`master:scripts/mutations/check-python-pin.json`: **one entry added, one retargeted, zero removed** —
the deleted candidate never existed on master; it was authored and dropped inside this branch.
Suggest: *"one added; a third was written and dropped as unkillable before commit"*.

### L3 — a line reference in the tick points at the pre-fix file

The ✅ cell says *"The vacuous case at `:880-882` is repaired"*. In the fixed file that case is at
`:899-903`; `:880-882` is where it was when the row was filed. Correct as history, wrong as a
locator — worth the four extra characters ("was at").

---

## Checked and SOUND

**S1 — step splitting is unchanged, proven rather than asserted.** Loaded HEAD's module and a
dash-reverted copy side by side and compared on the real corpus:

| file | `_structural` lines | `_steps` | `declared_pins` | `job_names` | identical |
|---|---|---|---|---|---|
| `.github/workflows/ci.yml` | 196 → 196 | 57 → 57 | `['3.12']` → `['3.12']` | 1 → 1 | **True** |
| `.github/workflows/schema-gates.yml` | 86 → 86 | 15 → 15 | `['3.12','3.12']` → same | 2 → 2 | **True** |

Outputs are equal element-for-element, not merely equal in count. Consistent with the row's
"latent today" claim: `grep -nE "^\s*-\s+[-\w.]+:\s*[|>]" .github/workflows/*.yml` → no matches.

**S2 — the live path is real and is closed.** See the M1 table: pre-fix `(0, 'python pin OK — every
job pins 3.12…')` over a job with **no** `setup-python`; HEAD `(1, 'FAILED — 1 job(s) pin no Python
version: ci.yml:schema-gates')`. Reproduced independently of the row, with a `cat <<'EOF'` heredoc
rather than bare quoted lines.

**S3 — `group(1)` = the KEY column is the right indent, per libyaml.** Content at exactly the key
column is a **syntax error** (`could not find expected ':' while scanning a simple key at line 5
column 9`), so a scalar's content is always strictly deeper than the key — which is precisely the
comparison `_structural:350` makes. An explicit indicator (`|2`) can only push content *deeper*, so
the numeric suffix cannot defeat it (measured: HEAD agrees with libyaml on `|2`).

**S4 — every one of the three new/repaired cases is honest.** Regex reverted on a temp copy:

```
  [FAIL] ...and a job holding only those still reports as unpinned: got [] want ['w.yml:verify']
  [FAIL] a pin quoted inside a DASH-opened block scalar is not a pin: got ['9.9'] want []
  [FAIL] ...so a SIBLING job pinned only by heredoc text is still unpinned: got [] want ['ci.yml:schema-gates']
  83/86 passed
```

The two-job case does exercise what it claims: its `verify` job is a *genuine* `- name:` +
`uses: actions/setup-python` + `with:` step, so the fixture really is "job A pinned, job B pinned
only by heredoc text", and it is `unpinned_jobs`, not `declared_pins`, that reads it — the asymmetry
the row is about. (It does not call `pin_took_effect`; nothing in the case claims it does.)

**S5 — all 40 mutations kill, each via the case it names.** Re-derived rather than taken from the
coordinator's harness run: green control first (`86/86`), then each entry applied to a fresh temp
copy, `[FAIL] <case>` names parsed and compared to `expect` by **equality**, HOME redirected.
Result: **0 survivors, 0 unattributed, 40/40**. Notable: entry 29 (the new one) reds **three** cases
and entry 27 reds the repaired case too — attribution is still unambiguous because `expect` matches
one name exactly.

**S6 — deleting the third mutation was RIGHT, and the reason is measurable.** A mutation that
strips the `uses:` line from the repaired fixture leaves the suite **86/86 green** — it removes the
case's teeth instead of breaking behaviour, so no case can red for it. Unkillable by construction, as
claimed. (What *is* possible is M4's list-`expect`, which is a different mechanism, not that
mutation.)

**S7 — bookkeeping re-derived by running, not reading.**

| figure | claimed | measured |
|---|---|---|
| suite cases | `# 86 cases` in the docstring | `86/86 passed`; `check-selftest-counts.py` → 45 scripts, every count verified by running |
| manifest entries | 40 | `len(json.load(...))` = **40** |
| `EXPECTED_MUTATIONS["scripts/check-python-pin.py"]` | 40 | `check-plan-code.py:813` = **40** |
| declared sum | 869 | `check-plan-code.py --self-test` → **128/128**, which includes that case |
| duplicate names / duplicate anchor sets | none | **0** / **0** |
| every anchor's occurrence count in the target | 1 | **1 for all 40** |
| every `expect` is an exact existing case name | yes | **40/40 matched against the 86 case names** |

Neighbouring guards green on the branch: `check-docs.py`, `check-selftest-counts.py`,
`check-dashboard-entry.py` ("ok — an entry block was added"), `check-ratchet-contract.py`.

**S8 — the ticks are in order.** `docs/backlog.md` row 154 → `✅ (was 🟠)` + status cell citing
**PR #331**; `docs/roadmap-to-launch.md:1953` → `- [x]` + "✅ **PR #331** (open, not merged)". PR #331
is OPEN with head `backlog-154-dash-block-scalar` — so the merge tick was written **before** the
merge, per `docs/dev-process.md` Phase 5, not chased afterwards. Dashboard entry for 2026-09-21 is
present and prose-only, and reads correctly to someone who was away.

**S9 — nothing further is owed in `docs/dev-process.md`.** Its `check-python-pin.py` row states the
rule (*every job pins or is exempt with a reason*), the CI-vs-local asymmetry, and #137's history.
Nothing in it is falsified by this change and the change adds no new rule a reader must know — the
guard's contract is identical, it is merely no longer wrong about one spelling. A pointer row is not
owed.

---

## CANNOT VERIFY

* **The coordinator's `--mutate .` figure (869/869 killed, 0 survivors).** Not re-run — `--mutate`
  has no per-file switch and the full harness is ~13 minutes. S5 substitutes a per-file equivalent
  (all 40 entries, green control, attribution by equality, redirected `HOME`) which is stronger
  evidence *for this file* and silent about the other 51 entries. The two counts that changed in
  `check-plan-code.py` are pinned by its own 128-case suite, which is green.
* **Whether any real workflow in the wild uses the three M3 shapes.** Only this repository's two
  workflow files were read; both are free of all of them.

## Owed before merge (process, not a defect)

`python3 scripts/check-review-rounds.py` now reports:

```
✗ backlog-154-dash-scalar round 1: only claude — codex neither ran nor recorded a `REVIEW GAP:` line
```

This half creates that obligation. Either the Codex half lands at
`docs/reviews/codex/backlog-154-dash-scalar-r1-codex.md`, or a `REVIEW GAP:` line records why it
could not run.
