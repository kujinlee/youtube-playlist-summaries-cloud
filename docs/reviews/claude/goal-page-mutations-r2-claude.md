# Claude adversarial review — branch `goal-page-mutations`, round 2

PROOF OF SUBJECT
----------------

Subject: `git diff 2246ed6d..HEAD` at `e3e44637` (*"Round 1 files both halves, and the rule this file
argues hardest for becomes reachable"*). Working tree clean apart from a concurrent
`docs/reviews/verdicts/goal-page-mutations-r2-codex.verdict.json`, which is not mine and which I did
not touch.

**(1) The `name` field of the LAST entry in `scripts/mutations/gen-goals-page.json`**, verbatim:

```
the file list is read from a FIXED commit, not the one it was given
```

**(2) That file now holds 24 entries** — `len(json.load(...)) == 24`, zero duplicate names, and
`src.count(before) == 1` for all 24 anchors against `scripts/gen-goals-page.py` at HEAD.

**(3) The current body of `git_show_files`** (`scripts/gen-goals-page.py:354-368`), verbatim:

```python
def git_show_files(sha: str, run=subprocess.run) -> list[str] | None:
    """The file list of one commit, or None when git cannot answer.

    ⚠ `.splitlines()`, NOT `.split()`. `git show --name-only` emits one path per line, and
    a path containing a space would split into two entries whose tail matches no DOC_PATH
    branch — turning a documentation PR into a `code` one. No such path exists in this
    repo today; the plan review caught the two halves of one insertion disagreeing, with
    the sibling above already correct.
    """
    try:
        r = run(["git", "show", "--name-only", "--format=", "-1", sha],
                cwd=ROOT, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.splitlines() if r.returncode == 0 else None
```

STATUS: COMPLETE

**Method.** Everything below was run, never reasoned about. `scripts/` staged with
`git archive HEAD scripts` into a scratch tree (byte-identical to `HEAD:scripts/gen-goals-page.py`,
checked with `diff`); mutations applied there through `check-plan-code.py`'s own `run_suite`,
`child_env` and `parse_fail_names`, imported rather than re-implemented. `--mutate .` not run, per
the brief. I wrote nothing into the repository except this file.

---

## Findings

### Blocking — the two argv cases are satisfied by the mutation's choice of literal, not by the code being right

**Where:** `scripts/gen-goals-page.py:951-952` and `:981-982`; manifest entries 22 and 23

**Attribution:** raised by the coordinator and by the Codex half first. Reproduced here independently
rather than taken on report, because it inverts my own Medium below.

**What:** both cases compare ONE recorded argv element against ONE literal:

```python
    eq("the history is asked for the document it was given, not a fixed one",
       _argv[0][-1], "docs/superpowers/specs/a-design.md")
    eq("the file list is asked for the commit it was given, not a fixed one",
       _show_argv[0][-1], "abc1234")
```

`_argv[0]` is the argv of the *first* call, and the first call is the only one whose path is ever
read back. So the case does not assert that the argument TRACKS the parameter — it asserts that one
recorded value equals one constant. A production line hardcoded to **that same constant** satisfies
it exactly.

**Failing scenario:** every document on the goals page inherits one document's PR history, and every
PR inherits one commit's file list — the precise defect the comment at `:946-949` says these cases
exist to prevent — with the suite green and both manifest entries still reporting `caught`.

**Evidence:** four probes against the proved-green control, in the staged tree:

```
CONTROL                                                  rc=0  75/75

"--follow", "--", str(path)]
   -> "--follow", "--", "docs/superpowers/specs/a-design.md"]   SURVIVED  rc=0  fails=[]
"-1", sha]
   -> "-1", "abc1234"]                                          SURVIVED  rc=0  fails=[]

(shipped entry 22)  -> "--follow", "--", "docs/x.md"]           KILLED    rc=1
(shipped entry 23)  -> "-1", "HEAD"]                            KILLED    rc=1
```

The shipped entries kill only because they happen to pick a literal *different from* the fixture's.
The mutation is doing the case's work. Change the mutation's literal and the same defect walks
through.

**⚠ This makes the two `check-fixture-variation` entries the weakest pair on the branch, not the
strongest — and it inverts the story told about them.** The dashboard entry and
`check-plan-code.py:2922-2928` present these two as the round's best catch (*"Both halves read those
cases; a guard caught it in one run"*). Measured, the guard's demand produced a case that cannot
fail for the property it names. See the Medium below, whose Probe B is the other half of the same
picture: delete these two cases and the shipped mutations 22/23 survive; keep them and hardcode
production to the fixture value and they survive too. The pair is falsifiable only against an
arbitrary choice of replacement text.

**Fix:** assert that the argv TRACKS two distinct inputs — call the function twice with different
paths and compare `_argv[0][-1]` and `_argv[1][-1]` against *each other's* inputs, so no single
constant in production can satisfy both. Same for `sha`. That also makes the parameter genuinely
varied in the sense `check-fixture-variation` is reaching for, rather than incidentally.

---

### High — round 1's High is OPEN, and the commit message's account of it is what makes that invisible

**Where:** `scripts/gen-goals-page.py:111` (the rule), `:822-823` (the blind case); commit message
of `e3e44637`

**What:** the r1 Claude review's single High was that `parse_adr`'s front-matter/in-body split — the
rule its own docstring calls *"the point"* — has no manifest entry and a case that cannot fail for
it. It closed with an explicit minimum: *"an entry (or a written seed declaration) for `parse_adr`,
and the two stale counts in `check-plan-code.py` moved to three."* The second half was done. The
first was not done and is not declared.

The fixture is unchanged:

```python
    eq("front matter is NOT counted as an amendment",
       parse_adr("---\nstatus: accepted — supersedes ADR-0002\n---\n\nbody\n")["amendments"], [])
```

`AMENDMENT` requires a `⟳`; the fixture's front matter has none, so both the real and the gutted
`parse_adr` return `[]`.

**Failing scenario:** an ADR whose front matter carries `⟳ SUPERSEDED 2026-08-06` — the shape the
docstring says ADR-0006 actually had. Real code reports `amendments == []`; with the split removed it
reports `['SUPERSEDED']`, and the goals page shows a decision as amended on the strength of its front
matter alone. Nothing on the branch observes the difference.

**Evidence:** deleted the line in the staged tree and ran the suite through `run_suite`:

```
CONTROL                75/75 self-test cases passed   rc=0
`body = text` (split deleted)  rc=0   75/75   fails=[]
```

`git diff 2246ed6d..HEAD | grep -i parse_adr` matches only inside the committed review document
itself. No entry, no seed sentence, no `EXPECTED_MUTATIONS` note.

**And this is the part that makes it a High rather than a repeat Medium.** The commit message says:

> Both reviewers returned NOT-CONVERGED with a High each, and reached the same structural cause from
> opposite directions. Codex read the manifest and saw that the CANNOT-RUN producer was not on it.
> Claude staged the tree, applied 24 candidate weakenings and measured 11 SURVIVING.

The committed `docs/reviews/claude/goal-page-mutations-r1-claude.md` contains no such measurement —
`grep -i "24 candidate\|11 SURVIV"` returns nothing — and its High is `parse_adr`, which has nothing
to do with the seam. So the sentence "both reached the same structural cause" is false, and the
effect of it is that the one High the branch did not close is recorded as having been closed by the
seam. The same substitution appears at `scripts/check-plan-code.py:568-570`
(*"Claude staged the tree, applied 24 candidate weakenings and measured 11 SURVIVING"*), where it is
load-bearing: it is the stated justification for moving the ratchet 14 → 24.

**Fix:** either an entry for the split (the r1 review measured that comparable probes on
`parse_header` and the `ADR none` collapse both killed and attributed on the first try, so this is
cheap), or a seed sentence in `EXPECTED_MUTATIONS` in the shape `gen-backlog-page.py`'s already uses.
And the commit-message paragraph should say which High it closed and which it did not.

---

### Medium — the corrected provenance is wrong again, in the same direction, at three sites

**Where:** `scripts/gen-goals-page.py:774-775`, `scripts/check-plan-code.py:2958-2960`,
`docs/dashboard-entries.md` (the new `⟳ CORRECTED in review r1` paragraph)

**What (a) — the second name is simply not that shape.** All three sites say:

```
# THIRD with this exact `  ✗ {label}` shape, after `check-explainer-delivery.py`
# and `check-gate-falsifiability.py`, both of which paid it five days earlier:
```

`check-gate-falsifiability.py` never had that printer. Its self-test case printer immediately before
its fix commit `9681aa61` was:

```python
            print(f"  FAIL {name}\n       expected {expected}\n       got      {got}")
```

(`9681aa61^:scripts/check-gate-falsifiability.py:290`). Of the eight predecessors the branch
enumerates, exactly one — `check-explainer-delivery.py`, `  ✗ {label}: got {got!r}` at
`c7e53c98^:125` — carried a `✗` case printer. The others: `begin-plan.py`, `check-plan-progress.py`,
`check-banner-armed.py` and `gen-backlog-page.py` printed a `FAIL` word; `check-function-revokes.py`
(`  {'✅' if ok else '❌'}  {label}`, `a6554450^:120`) and `brief-compose.py`
(`  {'✅' if ok else '❌'}  {n}`, `f6c03fd8^:1225`) printed `❌`. So **`gen-goals-page.py` is the
SECOND with that shape, not the third**, and one of the two files named as precedent is wrong.

**What (b) — NINE undercounts, and the missing file is named in the subject line of a commit the
enumeration already cites.** `c7e53c98` is *"Two guards paid off the mutation-manifest debt, and
**both** could not have reported it (21 → 19)"*. The enumeration takes `check-explainer-delivery.py`
from it and drops `check-handoff-path.py`, whose printer was

```python
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: expected {expected}, got {got}")
```

— a near-miss that *clears* `startswith("[FAIL] ")` and then yields a garbage case name, because
`rsplit(": got ", 1)` finds `, got ` and returns the whole string. That commit's own message spells
it out: *"A wrong attribution wearing the shape of a right one."* That is ten, not nine.

**What (c) — and "this exact shape" has a larger population than three even so.** Four further files
carried the byte-exact `print(f"  {'✓' if ok else '✗'} {name}")`: `check-guard-coverage.py`
(`465dc436^:379`), `check-sentinel-meanings.py`, `check-vocabulary-collisions.py`,
`check-arch-findings.py`. They are correctly absent from a list of *payers* — `465dc436`'s message
says *"Contract (1) fixed first (✓/✗)"*, i.e. they fixed it before running mutations. But that is a
distinction the three sites never state, and it is the only thing keeping the number at nine.

**Failing scenario:** the same one the branch itself argues. A reader deciding whether to build the
pre-flight guard at `check-plan-code.py:2943-2982` reads "NINE FILES" and "the third with this exact
shape", and is deciding against a number that is wrong in the direction that weakens the case for
building it — which is precisely the sentence the branch added at `:2962` (*"The number matters in
the direction that argues for BUILDING the guard below"*).

**Evidence:** `git log -S'[FAIL] ' --reverse --format='%h %as %s'` per file reproduces all nine dates
exactly as claimed (so the dates are sound); `git show <fix>^:<file> | grep print` for each gives the
prior printers quoted above; `git log -1 --format=%B c7e53c98` gives the two-guard account. §22's
introducing commit **is** `050913f6` — `git log -S'## 22. A kill that attributes to nothing is a
pass' -- docs/portable-practices.md` returns exactly that one commit, and `git show --stat 050913f6`
confirms it is the `gen-backlog-page.py` fix. **That half of the correction is right**, and it is
the half round 1 asked for.

---

### Medium — `check-plan-code.py:2956` says "The five this paragraph never named" and then names six

**Where:** `scripts/check-plan-code.py:2956-2961` vs `scripts/gen-goals-page.py:784`

```python
    # file, after that branch copied the same under-count into its own source. The five this
    # paragraph never named all predate §22: `begin-plan.py` and `check-plan-progress.py`
    # (2026-09-06), `check-banner-armed.py` (2026-09-06), `check-explainer-delivery.py` and
    # `check-gate-falsifiability.py` (2026-09-07, both with the IDENTICAL `  ✗ {label}`
    # printer `gen-goals-page.py` would arrive with five days later), `check-function-revokes.py`
    # (2026-09-07).
```

Six filenames follow the word "five". `gen-goals-page.py:784` and the commit message both say
**six** of the eight predate §22, which is the correct figure. Two statements of one fact, written in
the same change, disagreeing by one — in the paragraph whose subject is a number that was wrong.

---

### Medium — the source cites five numbered round-1 findings that exist in neither filed review

**Where:** `scripts/gen-goals-page.py:915` (`HIGH-1 and MEDIUM-4`), `:996` (`MEDIUM-3`), `:1054`
(`MEDIUM-2`), `:1071` (`MEDIUM-5`)

**What:** neither `docs/reviews/claude/goal-page-mutations-r1-claude.md` nor
`docs/reviews/codex/goal-page-mutations-r1-codex.md` numbers its findings —
`grep -n "MEDIUM-\|HIGH-\|LOW-"` over both returns nothing. Nor does either mention the subjects
three of those citations name: `grep -in 'class="tag\|fan-out threshold\|n > 1\|n > 2'` over both
returns nothing. Codex has three Mediums total, so `MEDIUM-4` and `MEDIUM-5` cannot resolve there
under any numbering; Claude has two, neither about these subjects. The IDs evidently come from a
third artifact that is not in the repository.

**Failing scenario:** three of the ten new entries — the `tag` class capture, the fan-out boundary,
and the dead-`or` fixture repair — are justified in source by findings a reader cannot open.
`check-review-rounds.py` exists to make a round's record auditable, and it passes here (both halves
are filed); what it cannot see is a source comment pointing at a finding inside them that is not
there. The same gap shows up in the coordinator's own round-2 brief, which refers to r1 lows
"LOW-7 … LOW-11" that likewise do not appear in either file.

⚠ **The underlying measurements are sound — this is a citation defect, not a coverage one.** I
verified the sharpest of the three by running it (see *Checked and found sound*): at `2246ed6d`,
deleting only the production-dead `or [spec, plan]` fallback reddened exactly the two cases the
comment names; at HEAD it leaves the suite green. The claim is true. It is the attribution to
"review r1 (MEDIUM-3)" that cannot be checked.

**Fix:** cite the artifact that holds them, or restate the finding in one clause instead of an ID.

---

### Medium — `check-fixture-variation`'s verdict on `path`/`sha` is anti-correlated with the coverage, and both comments written about it are refuted by running it

**Where:** `scripts/gen-goals-page.py:944-949` and `:980-982`; `scripts/check-plan-code.py:2922-2928`;
the dashboard entry's ⭐ paragraph

**What:** the branch credits the guard with finding a real gap:

```python
    # ⚠ THE PATH VARIES ACROSS THESE CASES, AND THAT IS NOT COSMETIC. The first draft passed
    # `Path("x")` to all three, and `check-fixture-variation.py` refused it: a parameter
    # given one constant everywhere is one no case can tell apart FROM a constant, so the
    # clause that reads it is unguarded.
```

and, at `check-plan-code.py:2927`, *"Both halves of the round read those cases and neither saw it; a
guard did, in one run."*

Measured, the guard's demand is neither necessary nor sufficient for the coverage that was added.
Only three of the six new call sites ever observe the parameter at all — `_run_ok` and `_show_ok`
append to `_argv` / `_show_argv`; `_run_rc1` and `_run_boom` discard their arguments — so the
variation in those cases cannot decide anything.

**Evidence — two probes, each against the proved-green control:**

*Probe A: collapse the variation, keep the assertions.* All three `path` values set to
`docs/superpowers/specs/a-design.md`, all three `sha` values to `abc1234`:

```
check-fixture-variation:  FAILED — `git_pr_history(path=…)` … `git_show_files(sha=…)` never varied
control                   75/75, rc=0
mutation 22 (fixed path)  rc=1  attributed=True
mutation 23 (fixed sha)   rc=1  attributed=True
```

*Probe B: keep the variation, delete only the two `_argv[0][-1]` / `_show_argv[0][-1]` cases:*

```
check-fixture-variation:  PASSES on git_pr_history.path and git_show_files.sha
control                   73/73, rc=0
mutation 22 (fixed path)  rc=0  SURVIVED  fails=[]
mutation 23 (fixed sha)   rc=0  SURVIVED  fails=[]
```

So the guard reports a gap where none exists and reports none where the clause is genuinely
unguarded. What produced entries 22 and 23 was the author's *response* to the refusal — adding two
argv assertions — not the property the refusal is about. The guard's own docstring says as much
(*"it is a floor — it proves a parameter was thought about, never that the values chosen are good
ones"*), and the branch's comments assert the opposite.

**Why this matters beyond wording.** The sentence *"a parameter given one constant everywhere is one
no case can tell apart FROM a constant, so the clause that reads it is unguarded"* is written as a
transferable rule, in a file other suites are read against. A reader following it will vary fixtures
rather than assert arguments, and Probe B is what that produces: a green guard over a surviving
mutation. This repo's own record on this shape is *"the CONTROL refuted the premise — red → fix →
green is NOT a cause."*

---

### Medium — the `--follow` case's stated impossibility is false, measured through the shipped seam

**Where:** `scripts/gen-goals-page.py:961-966`

```python
    # ⚠ THIS ASSERTS THE FLAG, NOT THE BEHAVIOUR, and the limit is stated rather than
    # implied: proving renames are followed needs a repository containing a rename, and
    # this seam hands the stand-in a hard-coded `cwd=ROOT` it cannot redirect. What the
    # case catches is the flag's DELETION. The docstring already records that today's
    # corpus adds PRs for 0 of 47 documents, so nothing stronger is observable here.
```

**What:** the admission that the case asserts the flag is honest and welcome. The *reason* given for
settling there is not true. `cwd=ROOT` is passed to `run` as a keyword argument
(`gen-goals-page.py:344-345`), and every stand-in has signature `(cmd, **kw)` — it receives `cwd` and
may overwrite it in one line. The behaviour is observable through the seam exactly as shipped, with
no change to production code.

**Evidence:** built a repo with a rename (`docs/old.md` → `docs/new.md`, PRs #100 and #101), then
called the shipped `git_pr_history` with a stand-in that sets `kw["cwd"] = REPO`:

```
REAL git through the seam, --follow present: ['101', '100']
same seam, --follow removed:                 ['101']
```

The real constraint is a different one, and it is a good one: the docstring declares the suite
*"75 cases, pure functions only"* (`:6`), and a case that launches git would break that. Say that
instead. As written, "nothing stronger is observable here" is a claim of impossibility that one run
refutes, and it is the justification for keeping a case that — by this project's own recorded rule —
*"defends only that fix's DELETION"*.

**Calibration:** this costs no coverage today. Mutation 16 is the flag's deletion and the case kills
it via its own name (verified). The finding is that the stated limit is wrong, in a comment whose
whole purpose is to state a limit accurately.

---

### Low — `brief-compose.py paid 8` survives at `check-plan-code.py:2951`, and is reinstated in the dashboard entry

r1 filed this: the figure is uncheckable, and the only committed observables disagree.
`scripts/mutations/brief-compose.json` holds **16**,
`EXPECTED_MUTATIONS["scripts/brief-compose.py"]` is **16**, and
`git log -S'"scripts/brief-compose.py": 8'` returns nothing. The branch removed the parenthetical
from `gen-goals-page.py` — good — and left it at `check-plan-code.py:2951` and re-added it to
`docs/dashboard-entries.md` (*"`brief-compose.py` (8)"*) in the new correction paragraph. Either say
*"the 8 entries it had when the trap fired"* or drop the number.

### Low — two r1 items in the same comment block are untouched

Both at the `EXPECTED_MUTATIONS` entry the branch edited, so the lines were on screen:

* `check-plan-code.py:563` still reads *"gen-goals-page.py was the ONE sibling generator with no
  manifest"*. `scripts/gen-m4-manifest.py` is a `gen-*` script with a self-test and
  `scripts/mutations/gen-m4-manifest.json` does not exist. The claim is true of *page* producers and
  is written as a claim about generators. **Independently confirmed by the coordinator this round**
  — three reviewers have now landed on the same sentence, which is the argument for fixing it rather
  than re-filing it.
* `check-plan-code.py:565` and `:2911` still read *"~540 lines of new rules"*.
  `git show --numstat 58d82658 -- scripts/gen-goals-page.py` is `532  8`, i.e. net **524**.

---

## Round 1 findings — closed or not

| # | Finding | Status |
|---|---|---|
| Claude High | `parse_adr` front-matter split: no entry, blind case | **OPEN** — measured: split deleted → 75/75 green, rc=0. No entry, no seed declaration. See High above |
| Claude Medium | "cost TWO BRANCHES" left standing in the contract's own file | **CLOSED** — `check-plan-code.py:2946` now reads "NINE FILES"; `:1224` diagnostic renamed. New errors in the replacement are filed above |
| Claude Medium | "the ONE sibling generator with no manifest" is false (`gen-m4-manifest.py`) | **OPEN** — `:563` unchanged; `gen-m4-manifest.json` still absent |
| Claude Low | `brief-compose.py (8)` unsupported by any artifact | **PARTIAL** — removed from `gen-goals-page.py`, retained at `check-plan-code.py:2951`, re-added to the dashboard entry |
| Claude Low | "~540 lines" overstates the measured 524 | **OPEN** — `:565` and `:2911` unchanged |
| Claude Low | entry 9's `expect` names a crash-safety case | **CLOSED** — `expect` is now *"a rel-less extra is identified by identity, not collapsed into the spec"* and the case is renamed to match its assertion (`:1116`). Verified: mutation reddens that case by name |
| Claude Low | three entries kill two cases each and name one | **OPEN, and correctly so** — entries 7, 8, 9, 10 still produce 2 fails each (measured). `expect` accepts a list; the harness permits one name. Not a defect |
| Codex High | `git_pr_history`'s CANNOT-RUN predicate unmutated | **CLOSED** — seam added, entries 14/15, both kill and attribute |
| Codex Medium | mutation 9 attributed to the wrong rule | **CLOSED** — same as Claude Low above |
| Codex Medium | `--follow` untested | **CLOSED mechanically** — entry 16 kills via its named case. The case asserts the flag and its stated reason for doing so is false; filed as Medium above |
| Codex Medium | `git_show_files`' `.splitlines()` unmutated | **CLOSED, and well** — entry 17 plus a fixture with a real space-containing path (`"docs/a b.md\nscripts/x.py\n"`). The strongest of the ten |
| Codex Low | `check-plan-code.attribute` does not exist | **CLOSED** — renamed at all four sites; `grep "^def attribute"` confirms no such function; the only surviving mention is `brief-compose.py:953`'s deliberate historical note |
| Codex Low | "both paid AFTER a convention was written" is false | **PARTIAL** — the §22 half is right and verified (`050913f6` introduced §22 *and* fixed `gen-backlog-page.py`). The replacement introduces the shape/count errors filed above |

---

## Checked and found sound

**All 24 entries KILL and ATTRIBUTE over a proved-green control, and none kills by crashing.** Run
through `check-plan-code.py`'s own `child_env` / `run_suite` / `parse_fail_names` against a
`git archive HEAD scripts` tree:

```
CONTROL rc=0  tail=75/75 self-test cases passed
0..23   KILLED+ATTRIBUTED   rc=1   SURVIVORS: []
nfails: 1,1,1,1,1,1,1,2,2,2,2,1,1,1,1,1,1,1,1,1,1,1,1,1
```

Every mutated run reached a `74/75`- or `73/75`-shaped summary line, so no mutation aborted the
suite before its named case ran — checked explicitly, because a crash-kill surfaces as
`caught=True, fails=[]`, which is the report-format disease this branch exists to pay off.

* **The ten new entries all fail by REPORTING.** Each produces a parseable `[FAIL] <case>` line for
  the case its `expect` names, by string equality including the unicode and the apostrophes.
* **Anchors.** All 24 `before` strings occur exactly once in the target; no duplicate names, no
  duplicate anchor tuples, so `load_manifests`' two refusals are satisfied. The three overlapping
  pairs the brief flagged — (9, 21) over the `fan = …` line, (16, 22) over the `git log` argv, and
  (17, 18) over `if r.returncode == 0 else None` — are safe because `run_mutations` restores the
  file between entries (`:1133-1136`): each mutation is applied to a fresh copy. A later edit that
  duplicated any of those short anchors would make the entry *ambiguous*, which `:1116-1121` refuses
  loudly rather than mis-attributing. Entries 18, 21, 22 and 23 are short substrings and so are
  reformatting-fragile, but they fail closed.
* **No `home_escapes` route in any replacement text.** Entries 22 and 23 substitute `"docs/x.md"` and
  `"HEAD"`; no `~`, no home resolution, so `mutate_delivered`'s replacement scan stays clean.
* **The seam changes no production behaviour.** `run=subprocess.run` and `show=git_show_files` are
  bound once at import to stable function objects; `collect`'s `history()` closure still calls
  `git_pr_history(ROOT / rel)` positionally (`:429`) and `annotate_code(got)` with its default. I ran
  `collect()` over the real repository under both `2246ed6d:scripts/gen-goals-page.py` and HEAD with
  `ROOT`/`DOCS` pointed at the live tree: **identical output**, 11 anchors, 41 threads, 96 PRs, 0
  `pr_error`. These are the only two call sites in the repo; `grep -rn` finds no others outside the
  file and the plan document.
* **The `tag` CLASS repair is robust, not just sufficient for its own entry.** I probed four
  weakenings of `cls` at `:625`, including ones weaker than the shipped entry — unknown painted as
  `docs`, unknown painted as `code`, and code/docs swapped. All four are killed by
  `"only the three measured tags can be rendered, each in its OWN class"`. The pre-fix regex
  (capture on the text alone) would have survived all of them.
* **The dead-`or` fixture repair is real, and I measured both arms.** Deleting only
  `or [x for x in (thread.get("spec"), thread.get("plan")) if x]` at `:262`:
  at `2246ed6d` → `rc=1`, reddening exactly *"a thread's PRs are the union over its documents,
  deduped, NEWEST FIRST"* and *"one unreadable document poisons the thread's verdict"* — proof those
  two cases ran through production-dead code; at HEAD → `rc=0`, green, because `_t` now carries
  `"docs": [_sp, _pl]`. The claim at `:996` is exactly right.
* **The two CANNOT-RUN sentinels are paired, so neither case is vacuous.** `git_pr_history`'s
  `is None` assertions sit beside *"a readable git log becomes PRs"*, which forbids a function that
  returns `None` unconditionally; same for `git_show_files` and `_show_ok`. This is the shape r1's
  High was about, and the new cases do not repeat it.
* **Ratchets balance, all three of them.** `EXPECTED_MUTATIONS["scripts/gen-goals-page.py"] == 24 ==
  len(manifest)`; `sum(EXPECTED_MUTATIONS.values()) == 548`; 41 dict keys ↔ 41 files in
  `scripts/mutations/`; and *every* declared count equals its on-disk manifest length (checked across
  all 41, not just this one). The docstring declares 75 cases and the suite runs 75.
* **Gates, run here rather than quoted from the commit message.** `gen-goals-page.py --self-test`
  75/75 · `check-plan-code.py --self-test` 128/128 · `check-fixture-variation` rc=0 (453 parameters
  across 49 files) and `--self-test` 60/60 · `check-selftest-counts` rc=0 (36 scripts, each verified
  by running it) · `check-review-rounds` rc=0 · `check-docs` rc=0 · `check-anchors` rc=0 ·
  `check-ratchet-contract` rc=0 · `check-dashboard-entry` rc=0 · `check-gate-falsifiability` rc=0 ·
  `check-review-recorded` rc=0. I did not run `--mutate .`, so the dashboard's
  `548 killed / 548 attributed` line is unverified by me; my 24/24 on this file is consistent with it.
* **The `[FAIL]` printer is the only failure channel.** `eq()` remains the sole failure printer in
  `self_test`; the got/want detail is on a continuation line beginning `    got `, which
  `parse_fail_names`' `startswith` clause never selects. No live case name contains `": got "`, so no
  entry is at risk of the truncation hazard the new comment correctly documents. The comment's
  self-correction here — that the canonical single-line form *does* parse and it was the
  two-space-no-colon separator that did not — is accurate against `parse_fail_names:1412-1413`.
* **§22's provenance, the half of the correction round 1 asked for, is verified.**
  `git log -S'## 22. A kill that attributes to nothing is a pass' -- docs/portable-practices.md`
  returns exactly `050913f6`, and `git show --stat 050913f6` is the `gen-backlog-page.py` fix. So
  §22 was introduced by the commit that fixed the first payer, and "both paid after a convention was
  written" was indeed false. All nine enumerated dates reproduce exactly under
  `git log -S'[FAIL] ' --reverse` per file.

---

## Verdict

**NOT-CONVERGED.** 1 Blocking, 1 High, 5 Medium, 2 Low.

**Twenty-two of the twenty-four entries are in good shape and I could not break one:** they kill and
attribute over a green control, every anchor is unique, every kill is a report rather than a crash,
production behaviour is unchanged, and three ratchets balance. The two fixture repairs I could test
are genuine — I reproduced the dead-`or` measurement in both directions, and the `tag`-class repair
catches weakenings weaker than the entry that names it. Nothing blocks on coverage of the seam
itself: the CANNOT-RUN branches and `.splitlines()` are now properly guarded, which was Codex's
round-1 High and its two Mediums.

**The two that are not in good shape are entries 22 and 23**, and they are the pair the branch
presents as its best result. Hardcoding production to the first fixture's literal leaves the suite
75/75 green in both cases — the entries kill only because their replacement text happens to differ
from the fixture. That is Blocking on its own, and it also means the round's headline claim (*"a
guard caught it in one run"*) is backwards: what the guard produced is the one pair of cases here
that cannot fail for the property it names.

Beyond that, the branch does not converge on the same axis as round 1, and it has got worse.

1. **Round 1's High is open and the commit message reads as though it were closed.** Deleting
   `parse_adr`'s split leaves the suite 75/75 green, measured. The r1 reviewer named an entry or a
   written seed declaration as the minimum for this round; neither exists, and the commit message
   substitutes a different, unfiled measurement for that reviewer's High.
2. **The provenance correction is wrong again.** One of the two precedent files never had the printer
   it is cited for; a tenth payer is named in the subject line of a commit the enumeration already
   cites; and the two sites of the §22 arithmetic disagree ("five" over a list of six). Round 1's
   finding was *a count written from memory in the file whose purpose is to be the record*. The
   replacement is longer, more emphatic, claims a method (`git log -S'[FAIL] '` per file) — and a
   per-file sweep is exactly what would have caught `check-handoff-path.py`.
3. **Two comments make claims that one run refutes** — that varying a fixture parameter is what
   guards the clause reading it (Probe B: guard green, mutation survives), and that rename behaviour
   is not observable through the seam (measured: `['101','100']` vs `['101']`).

Minimum for round 3: entries 22 and 23 re-cased so the argv is asserted to TRACK two distinct inputs
(the Blocking); an entry or a written seed declaration for `parse_adr`; the `✗`-shape claim
corrected or dropped at all three sites; `check-handoff-path.py` added or the criterion for "paid"
stated; "five" reconciled with its list; and the two refuted sentences rewritten to say the true
reason (the suite is pure-functions-only; the argv assertions, not the variation, are the guard).
