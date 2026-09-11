# Adversarial review — `harness-progress-output`, round 7 (Claude half)

**Verdict: NOT CONVERGED.** One Blocking, three High, one Medium, two Low.

The Blocking is not a regression from r6's fixes — I checked each of those and all three are
sound. It is the new guard itself: `check-fixture-variation.py` ships with its entire
decision path uncovered, and **its own rule, run on itself, names the parameter that causes
it.** The chain r6 broke stays broken; this is new surface arriving with the fix.

---

## Proof of subject

```
$ git log --oneline origin/master..HEAD
48d8cabb Round 6: ask the fixture question with a script, not with a reviewer   <-- SUBJECT
6a660454 Round 5: a fixture must differ from itself along the axis it tests
d6f55881 Round 4: an input far inside the boundary pins nothing, a third time
c3d53a70 Round 3: the want was not the only thing deriving from its subject
5e4bd163 Round 2: a guard whose want moves with its subject has no ceiling
b64b4cbc Round 1: inject the reporter, instead of emitting progress
915dfa67 File the review round for the progress change — both halves NOT CONVERGED
7ae516fc The mutation harness says where it is, instead of going silent for minutes

$ git rev-parse HEAD
48d8cabba11fd341134719349f27c57b5d2cca39        (working tree clean)

$ git show --stat 48d8cabb
 .github/workflows/ci.yml                                       |  12 +
 docs/dashboard-entries.md                                      |  31 +-
 docs/reviews/claude/harness-progress-r6-claude.md              | 653 +++++
 docs/reviews/coordinator/harness-progress-r6-coordinator.md    | 481 +++++
 docs/reviews/verdicts/harness-progress-r6-codex.verdict.json   |  16 +
 scripts/check-fixture-variation.py                             | 336 +++++
 scripts/check-plan-code.py                                     | 104 +-
 scripts/check-selftest-counts.py                               |   7 +-
 scripts/mutations/check-fixture-variation.json                 |  80 +
 scripts/mutations/check-plan-code.json                         |  68 +-
 10 files changed, 1763 insertions(+), 25 deletions(-)
```

## Controls, proved green BEFORE any mutation

```
$ python3 scripts/check-fixture-variation.py --self-test
21/21 passed                                                                    rc=0
$ python3 scripts/check-fixture-variation.py
fixture variation OK — 29 parameter(s) examined across 1 file(s), 3 exempt      rc=0
$ python3 scripts/check-plan-code.py --self-test          # in the staged tree
128/128 passed                                                                  rc=0
```

⚠ **One control of mine started RED and the finding it produced was mine, not the code's.**
My first attempt at the `main()` mutations copied `check-fixture-variation.py` to a bare
scratch directory; `root = …parent.parent` (`:145`) then pointed outside any repo-shaped
tree and three cases failed environmentally at **18/21**. Every `main()` measurement below
was re-taken inside a staged tree whose control is **21/21**. Recording it because a red
control is contamination until re-measured alone, and the first numbers would have read as
findings.

---

## BLOCKING

### B1 — the new guard can report OK while holding findings, and nothing in the repo notices

`scripts/check-fixture-variation.py:162-169`

```python
    if all_findings:
        print(f"FAILED — {len(all_findings)} parameter(s) never varied by any case:")
        for x in all_findings:
            print(f"  ✗ {x}")
        return 1
    print(f"fixture variation OK — {examined} parameter(s) examined across {len(targets)} "
          f"file(s), {len(EXEMPT)} exempt with a written reason")
    return 0
```

**Measured**, four independent mutations of `main`, each over the 21/21 control:

| mutation | suite | rc |
|---|---|---|
| `if all_findings:` → `if False:` — prints OK, exits 0, findings discarded | `21/21 passed` | 0 |
| the FAILED branch returns `0` instead of `1` | `21/21 passed` | 0 |
| the clean branch returns `1` instead of `0` | `21/21 passed` | 0 |
| the CANNOT-RUN aggregation (`:158-161`) returns `1` instead of `2` | `21/21 passed` | 0 |

All four survive. The first is the live harm: a guard wired into CI at
`.github/workflows/ci.yml:287` that prints `fixture variation OK` and exits 0 **with a
non-empty finding list in hand**. Both CI steps — the bare run at `:287` and `--self-test`
at `:290` — stay green. `--mutate .` cannot see it either: all six entries in
`scripts/mutations/check-fixture-variation.json` anchor inside `analyse`
(`:6-7`, `:19-20`, `:32-33`, `:45-46`, `:58-59`, `:71-72`); **not one touches `main`**.

⭐ **And the guard's own rule predicts exactly this.** Run it on itself:

```
$ python3 scripts/check-fixture-variation.py scripts/check-fixture-variation.py
FAILED — 1 parameter(s) never varied by any case:
  ✗ check-fixture-variation.py: `main(argv=…)` is passed the SAME value at every call site
    in the suite (1x `['/nonexistent/nope.py']`). …                              rc=1
```

One call site (`:326`), one value, and therefore no case reaching rc 0 or rc 1. The
unvaried parameter and the four surviving mutations are the same fact seen twice. The
guard is not in its own `POPULATION` (`:53`), and it could not be added without CI going
red — which is the honest summary of this finding.

This is the shape the file's own docstring is most careful about: a check whose *rule* is
sound and whose *verdict path* is unguarded. `check-ratchet-contract.py` passes it
(rc 0) because its fail-open detector looks for swallowed exceptions, not for a gate
returning the wrong code.

**What would close it:** cases that drive `main` over a temp tree to rc 0 (clean subject)
and rc 1 (subject with a finding), the way `:325` already drives the rc-2 refusal; plus
manifest entries for the `if all_findings` gate and both returns. Then `main.argv` varies
and the guard can join its own population.

---

## HIGH

### H1 — the guard is loudest at ONE call site and silent at ZERO

`scripts/check-fixture-variation.py:85` (`not node.name.startswith("_")`),
`:99-101` (`defs.get(node.func.id)` → a name the suite never calls is never entered into
`seen`), `:167` (the count is printed and pinned by nothing).

A parameter with one call site is reported (`1x …`). A parameter with **zero** call sites
is not examined at all, so removing the last case *upgrades* the file from FAILED to OK.
The severity is non-monotonic in coverage.

**Measured**, both against the 29-parameter green control:

```
# delete both stderr_progress(...) call sites from the suite — the three parameters r6 just fixed
fixture variation OK — 26 parameter(s) examined across 1 file(s), 3 exempt        rc=0

# rename progress_line -> _progress_line (one token; 14 occurrences) — the r6 B1 subject
fixture variation OK — 26 parameter(s) examined across 1 file(s), 3 exempt        rc=0
```

The rename path is not exotic: the guard *itself* treats a leading underscore as "test
plumbing, not a subject" (`:296-305`), so any refactor that marks a function module-private
removes it from the audited population silently. Nothing ratchets `examined`; the only
assertion on it is `n11 > 0` at `:321`, which one surviving parameter satisfies.

The blind spot is deliberate and cased (`:285-293`), and the docstring says a reader should
not assume full coverage. What is missing is the *denominator at runtime*: the green line
states 29 and never states 29 **of what**.

**What would close it:** print and pin the denominator — public functions defined vs
public functions driven — so a fall is visible the way `EXPECTED_MUTATIONS` makes one
visible.

⚠ Related, and worth stating because it bounds the guard's claim: r6's B2 was a defect in
`_mini`, a **private** fixture builder. This guard cannot examine `_mini` by construction.
It found B2's symptom in `progress_line`/`stderr_progress` because those are public; it
would not have found B2's cause.

### H2 — the silence case is an absence assertion satisfied by the exact failure r6 just fixed; the instance was fixed and the class was not

`scripts/check-plan-code.py:2051`

```python
            case("...and the whole path is silent when nobody asked", _me.getvalue(), "")
```

r6's last finding was that `EXPECTED_MUTATIONS["scripts/other.py"]` (set at `:2015`) leaked
into this block, so `mutate_delivered` refused on a count mismatch and returned **before the
control loop ran** — the case passed for the wrong reason and its mutation stopped being
attributable (476 killed / 475 attributed). The fix was to move the `pop` up to `:2040`.

**Measured** — I put the `pop` back below the silence block, i.e. reproduced r6's own bug:

```
$ python3 scripts/check-plan-code.py --self-test
128/128 passed                                                                   rc=0
```

The suite is completely blind to it. An empty `_me.getvalue()` is produced identically by
"ran all three phases and said nothing" and by "refused at the door and did nothing at all",
and the case asserts only the former's *shadow*. The relocated `pop` carries no case and no
manifest entry; the only instrument that can see it is the full-run attribution shortfall,
which reports an unattributable mutation elsewhere rather than naming this.

Contrast the sibling absence assertion at `:2804` (`run_mutations` silent), which is
**safe**: its presence partner at `:2790-2791` drives the same fixture with the same
arguments and proves the call does real work. The `:2051` partner at `:2027` uses a
*different* fixture (`_mini(_r, second=True)` plus the extra declaration), so it proves
nothing about this block.

**What would close it:** assert `mutate_delivered`'s return value alongside the empty
stream, so "it was silent" and "it ran" are two claims rather than one.

### H3 — POPULATION of one is narrower than the rule can already read, and the defect class is live in the files it omits

`scripts/check-fixture-variation.py:53` — `POPULATION = ("scripts/check-plan-code.py",)`

**Measured** over all 54 `scripts/*.py`:

| | files |
|---|---|
| define `_self_test` — readable by the guard **today** | **16** |
| define `self_test` (no underscore) — guard returns CANNOT RUN rc 2 | 32 |
| neither | 6 |

Running the guard's own rule over all 16 readable files: **11 report findings, 38 in total.**
The declared population covers **1 of 16**.

The findings are not noise. Spot-checked:

* `scripts/check-dashboard-entry.py` — `fence_closes(open_run=…)` passed ``` `'```'` ``` at
  **4 of 4** sites. A fence-matching function whose *fence length* is the entire subject,
  with the length constant in every case. This is r6's class exactly.
* `scripts/gen-dashboard.py` — `contrast_failures(minimum=…)` `<omitted, default>` at **5 of
  5** sites: a WCAG contrast threshold no case varies, in the subsystem whose own slice
  history is about a contrast fence.
* `scripts/gen-dashboard.py` — `commit_dates(window=…)` `14` at 2 of 2 sites.

Also worth recording: the suite-detector at `:88-89` matches the literal name `_self_test`,
which is the **minority** convention in this repo (16 files) against `self_test` (32). A
naive widening turns 32 files rc 2. That is honest behaviour, not a bug, but it means
"widen the population" is a slice, not a one-line edit — and it is the reason a green tick
here says much less than the guard's docstring's ambition.

I am not asking for the widening on this branch. I am asking that the ceiling be stated
where the *verdict* is read: "across 1 file(s)" at `:167` is the only place it appears, and
the CI step is named `check-fixture-variation` with no qualifier.

---

## MEDIUM

### M1 — one of the three exemptions forgives nothing, and pre-forgives the parameter two rounds were spent on

`scripts/check-fixture-variation.py:60-62`

```python
    "progress_line.label": "varied on magnitude AND position by the r3/r5 cases; the axes are "
                           "the point, not the count of distinct literals",
```

**Measured** — each exemption removed in turn, guard re-run on the live population:

| exemption removed | result |
|---|---|
| `progress_line.label` | `fixture variation OK — 29 parameter(s) examined, 2 exempt` **rc=0** |
| `diagnostic_tail.window` | `FAILED — 1 parameter(s) never varied` rc=1 |
| `run_suite_parts.d` | `FAILED — 1 parameter(s) never varied` rc=1 |

`progress_line.label` has 8 call sites and **7 distinct values**, so the rule never reaches
the exemption. Its only effect is prospective: a future edit that collapses `label` to one
value is accepted in silence — on the exact parameter r3 (magnitude) and r5 (position) each
spent a full round on. An exemption that is unnecessary today is a pre-authorised regression
tomorrow, and its written reason reads as an answer to a question nobody asked.

The cases at `:307-311` check that each exemption has a non-empty reason and a dotted key.
Nothing checks that an exemption is **needed**.

**What would close it:** a case asserting every `EXEMPT` key produces a finding when
removed — which also makes the EXEMPT list self-pruning.

---

## LOW

### L1 — keyword-only parameters re-introduce the false positive the omitted-default clause exists to remove

`:102` (`names = [a.arg for a in fn.args.args]`) and `:117`
(`defaulted = names[len(names) - len(fn.args.defaults):]`) read `fn.args.args` only.
`fn.args.kwonlyargs` never enter `names`, so the `<omitted, default>` synthesis at `:117-120`
cannot cover them. A keyword-only parameter given at one site and omitted at another records
a single value and is reported as unvaried — the precise false positive the comment at
`:112-116` says the clause exists to prevent, on the other half of the signature grammar.

**Latent only, and I measured that:** no public function in `scripts/check-plan-code.py` has
a keyword-only, `*args` or `**kwargs` parameter. It bites when the population widens or the
subject grows one.

### L2 — a subject that does not parse is a traceback, not CANNOT RUN

`:82` (`ast.parse`) is unguarded and `:155` calls it directly. **Measured** on a file
containing `def f(`:

```
rc=1
SyntaxError: '(' was never closed
```

Every other unreadable-population path in this file is careful to return **2** and say
`NOT CHECKED` (`:91-92`, `:149-151`, `:158-161`), because §21 keeps the rule and the
population failing separately. A syntax error takes the rule's exit code. CI still goes red,
so the cost is a misleading signal rather than a missed one.

---

## What I verified and found SOUND — r6's own fixes

Each reverted individually against the 128/128 control, in a staged tree:

| revert | result |
|---|---|
| B1: `room = PROGRESS_WIDTH - len(head)` → `- 10` | **126/128**, red via *both* new head-width cases |
| B2: `progress(position, len(targets), f"control {name}")` → `(position, position, …)` | **127/128**, red via the 6-tuple case |
| `_mini(_r, second=True)` → `_mini(_r)` | **127/128**, red |

B1's pair is genuinely two-sided: at head width 6 the frozen `room` truncates a label that
should fit; at head width 12 it fails to truncate one that should not. Both wants are
literal strings, not derived. B2's assertion is a full 6-tuple sequence, and every row has a
position differing from its total. `_mini(second=…)` is varied (one site `True`, twenty
`False` by omission), and `val` is varied too (`1`, `2`, `99`).

The B1 manifest entry names one case while **two** go red. That is correct under the rule at
`:1165-1168` — each `expect` **name** must match exactly one red case; extra red cases are
permitted and the code says so explicitly.

## Full-harness re-run

`python3 scripts/check-plan-code.py --mutate .` in a staged tree (`scripts` copied,
`supabase`/`docs`/`node_modules/typescript`/`.claude/hooks` symlinked) under a redirected
`$HOME`:

```
OK — delivered scripts mutated: 39 file(s), 476 mutation(s), 476 killed,
     476 attributed to the case each names, 0 survivor(s)                        rc=0
```

The commit's claim reproduces exactly — 476/476/476/0. **All six
`check-fixture-variation.json` entries are attributable** under the exact-one rule; the
`476 attributed` total leaves no room for an unattributed one. The guard's manifest is
sound as far as it reaches, which is the point of B1: it reaches `analyse` and stops.

## Observation, not a finding

Seven manifest entries in `scripts/mutations/check-plan-code.json` name the same single case
(`every phase of --mutate reports its position when a caller asks`); the next most concentrated
is three. Weakening that one case makes seven entries unattributable — which the harness
reports loudly, so the risk is contained rather than silent. Recording the concentration
because it is where a future "simplify this assertion" edit would cost the most.

## What I did NOT measure

* **Whether the 38 findings a widened population would raise are all true.** I spot-checked
  three by reading the call sites; the remaining 35 are unverified, and H3's argument needs
  only that *some* are real.
* **Whether `main()`'s uncovered branches in `check-fixture-variation.py` could be reached by
  a mutation the manifest does not declare but should.** I mutated four lines by hand; I did
  not enumerate the function's full mutation space.
* **The 32 `self_test` files** — I confirmed the guard returns CANNOT RUN on them, not what
  its rule would find if the detector accepted both names.
* **Timing/behaviour of the guard on a very large subject.** `ast.walk` over the suite is
  quadratic in nesting; irrelevant at 2,900 lines, unmeasured beyond that.
* **Codex's half.** This is the Claude half only.
