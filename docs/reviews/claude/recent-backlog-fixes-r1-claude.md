# `recent-backlog-fixes` — round 1, Claude adversarial half

**Subject:** `git diff master...HEAD` on `recent-backlog-fixes` (backlog #219, #212, #216).
**Worktree:** `/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/677677e1-1461-4973-8c68-a7a7b2765493/scratchpad/wt-backlog`
**`git rev-parse HEAD` at START:** `cb2681cd708859b485d2c23fee1b6db533a251f3`
**`git rev-parse HEAD` at END:** `cb2681cd708859b485d2c23fee1b6db533a251f3` (no git mutation; every mutation
below was applied to a COPY under the scratchpad).

**Mandate: refute.** Of the eight directions the brief named, five could not be refuted and are
recorded as such with the measurement that failed to break them. Three broke, and four more
findings came from directions the brief did not name.

---

## Verdict first

`NOT CONVERGED: 0 Blocking · 2 High · 4 Medium · 4 Low`

The two High findings are one shape, and it is the shape this branch exists to fix. #216 says *a
comment asserted a defence the code did not implement*. The fix for #212, in the same three
commits, ships **two more comments asserting defences the code does not implement** — one of them
in `.gitignore` itself — and the live half of #212's reconciler can be **deleted entirely** with
the suite still 64/64 green and the live run rc=0. That is `check-surface-recall.py`'s own
documented wiring class, for which this one file already carries three manifest entries, the most
recent of them labelled *"round 8 B1, the FOURTH instance of the wiring class"*.

---

## What I could NOT refute

Recorded because a review that only lists what broke hides how hard the rest was pushed.

### ① The #219 anchor did not move — 1,583 real subjects, and a hostile battery

Reconstructed the old pattern as the brief specified (`\(backlog #(\d+)\)(?:\s*\(#\d+\))?\s*$`) and
diffed it against the shipped `CLOSING` (`scripts/check-backlog-closure.py:131`) over
`git log --format=%s HEAD`, at 300, 500 and the full 1,583 subjects:

```
--- last 1583 subjects: old=12 new=16 ---
  REMOVED: []
  SUBJECT-LEVEL verdict changes: 2
   * ('Self-test debris cannot be committed, and the sweep that removes it is driven (backlog #212, #216)', None, ['212', '216'])
   * ('Settled items look settled, and say who settled them (backlog #83, #87) (#223)', None, ['83', '87'])
```

Nothing is lost (`REMOVED: []` at every window) and the only subjects gained are the two that are
genuinely two-row closures. The second is the branch's own commit — see Low 3.

The negative battery the brief asked for, all run through the shipped `closing_ids`:

```
'fix (backlog #17, #18) then more words'                        -> {}
'docs(backlog #53, #54): filed'                                 -> {}
'see (see (backlog #1, #2))'                                    -> {}
'Unicode comma (backlog #1， #2)'                                -> {}
'The guard ratchet built a table (backlog #29, half one) (#298)'-> {}
'trailing (backlog #1,)'                                        -> {}
'lead comma (backlog #,1)'                                      -> {}
'no hash on second (backlog #1, 2)'                             -> {}
'double hash (backlog #1, ##2)'                                 -> {}
'negative (backlog #-1, #2)'                                    -> {}
'two squash suffixes (backlog #1, #2) (#9) (#10)'               -> {}
'Two rows (backlog #201) (backlog #202) (#362)'                 -> {'202': ...}   (deliberate)
'(backlog #1, …, #10)'                                          -> all ten ids
```

ReDoS probe over a 2,000-element failing list: 0.0009 s. The grammar widened; the anchor did not.

### ② `re.findall(r"\d+", m.group(1))` cannot capture a non-id

Group 1 is `\d+(?:\s*,\s*#\d+)*`, so the only characters it can legally hold are digits,
whitespace, `,` and `#`. `findall(r"\d+")` over that alphabet yields exactly the ids.
One residue, informational only: Python's `\d` is Unicode, so `(backlog #١٢)` matches and files
id `'١٢'`, which no row carries — it surfaces as an *orphan* warning, never a false close, and
`sorted(..., key=int)` does not raise because `int()` accepts Unicode decimals. Not filed.

### ③ The sweep's direction is right — I could not make it over-clean

Probed against hostile filenames in a copy. A symlink named like dead-pid debris removes **the
link only** (`victim survived symlink sweep: True`). `_selftest-0.sh` is kept, because
`kill(0, 0)` addresses the caller's process group and never raises `ProcessLookupError`. A reused
pid reads as alive and is kept. Every failure direction I could construct under-cleans, which is
the direction the comment claims. (It *can* throw — that is Medium 2, a different axis.)

### ④ The fetch half is CI-reachable, and a missing file fails

`.github/workflows/ci.yml:261` runs `python3 scripts/check-surface-recall.py` as its own step,
separate from `:264`'s `--self-test`. Removed `.gitignore` from a copy:

```
FAILED: .gitignore cannot be read (FileNotFoundError), so it cannot be reconciled against FIXTURE_PREFIX. Treat this as NOT RUN.
live rc with NO .gitignore = 2
```

CANNOT RUN, exit 2, not a pass. The block at `scripts/check-surface-recall.py:390-404` is
unconditional inside `main`'s single `try`, so there is no path that skips it quietly: an earlier
`CannotRun` returns 2 before reaching it.

### ⑤ Staging `.gitignore` changes nothing for the other 57 scripts — refutation attempted, failed

This is the one the brief called riskiest, so I measured it rather than reasoned about it. Staged
two complete `HARNESS_TREE` trees with `stage_tree`, deleted `.gitignore` from one, and ran
**every** `scripts/*.py --self-test` in both under `child_env`, comparing rc and full output:

```
staged. with_gi has .gitignore: True | without: False
ran 68 scripts in both trees; 7 behave differently
  brief-compose.py        rc 0 / 0
  check-closing-table.py  rc 0 / 0
  check-plan-code.py      rc 0 / 1
  check-surface-recall.py rc 0 / 1
  codex-review.py         rc 0 / 0
  recall-llm.py           rc 0 / 0
  regen-skills-doc.py     rc 0 / 0
```

Then a noise baseline — the same script twice in the *same* tree:

```
brief-compose.py: self-vs-self identical in SAME tree? False
check-closing-table.py: ... False
codex-review.py: ... False
recall-llm.py: ... False
regen-skills-doc.py: ... True
```

Four of the five rc-0 differences are run-to-run nondeterminism, not a `.gitignore` effect.
`regen-skills-doc.py` is deterministic and differed **only** in the absolute tree path printed in
its two `warn: could not read …/with_gi/…` vs `…/without_gi/…` lines. `check-plan-code.py`'s
difference is its own `HARNESS_TREE` self-test correctly reporting the deleted entry.

So: **only `check-surface-recall.py` reads it.** The claim stands. I also checked
`check-review-recorded.py:149`, whose `PROSE_FILES` names `.gitignore` — that is a rule over a
*list of changed paths*, not a filesystem read, and it did not differ between trees.

`stage_tree`'s new branch (`scripts/check-plan-code.py:244-247`) is correct against the two shapes
asked about: `src.exists()` and `src.is_dir()` both follow symlinks, so a dangling symlink becomes
the named CANNOT RUN rather than a crash, and `dst.parent.mkdir(parents=True, exist_ok=True)`
already precedes the copy, so a missing parent cannot arise.

### ⑥ #216's NEW comment is TRUE — the sever is still live

Derived the value **by running the callee**, never by typing it:

```
>>> _defined_codes()
{'OK': 0, 'CANNOT_RUN': 2, 'STALE_CACHE': 3, 'BAD_RESPONSE': 4, 'UNREADABLE_PLAN': 5, 'UNANSWERABLE': 6}
```

Replaced `scripts/check-surface-recall.py:377`'s `defined = _defined_codes()` with that literal
dict in a copy:

```
severed
64/64 self-test cases passed
selftest rc=0
live rc=0
```

The sever survives. The replacement comment at `:792-803` — *"THE SEVER IS STILL LIVE. It is round
9's H1a"* — is accurate, and the removal of the dead `_saved_m` assignment is clean.

### ⑦ The counts all derive

| Claim | Derived | How |
|---|---|---|
| suite 64 | **64** | `check-surface-recall.py --self-test` → `64/64 self-test cases passed` |
| manifest 20 | **20** | `len(json.load(scripts/mutations/check-surface-recall.json))`; 20 distinct `name`, 20 distinct `edits` |
| declared total 1179 | **1179** | `sum(EXPECTED_MUTATIONS.values())`, and independently `1179` summed from the on-disk manifests, with zero per-file mismatches |
| closure suite 28 | **28** | `check-backlog-closure.py --self-test` → `28/28 passed` |

The new manifest entry also kills via the case it names — anchor binds exactly once in the
delivered file, and applying it gives:

```
MUTATED suite rc= 1
FAIL lines:
   [FAIL] the startup sweep REMOVES debris whose owning pid is gone, and KEEPS a live peer's
expect-case named in manifest is among them: True
63/64 self-test cases passed
```

---

## Findings

### HIGH 1 — Structural. The live half of #212's reconciler is unprotected: delete it and nothing goes red

**Premise** (`scripts/check-surface-recall.py:384-387`):

> `# ⛔ THE FETCH HALF OF THE #212 RECONCILER. Here rather than in the suite because the`
> `# suite must run inside a staged tree that has no .gitignore; this runs in the real`
> `# repo and is its own CI step.`

**Measurement.** Three severances, each applied to a copy of the delivered file in a complete
staged tree:

```
M-A  reconciler result never reaches the verdict   (`if False and not gitignore_covers(...)`)
   suite rc=0 ['64/64 self-test cases passed'] | live rc=0
M-B  gitignore_covers always returns True
   suite rc=1 ['61/64 self-test cases passed'] | live rc=0
M-C  the entire .gitignore fetch DELETED from main (lines 390..404 removed)
   suite rc=0 ['64/64 self-test cases passed'] | live rc=0
```

The **pure rule is defended** (M-B kills three cases). The **wiring is not**: the result can be
severed from the verdict (M-A), and the whole fetch can be deleted (M-C), with the suite fully
green and the live run clean. Twenty manifest entries exist for this file and none of them touches
`gitignore_covers` or its call site:

```
$ grep for 'gitignore' across scripts/mutations/check-surface-recall.json
(no entry)
```

**Severity reasoning — High, not Medium.** This is not a hypothetical class here. Three of this
file's own twenty manifest entries are named for it: *"coverage's result is never READ at the call
site … round 8 B1, the FOURTH instance of the wiring class"*, *"the net's result is never READ at
the call site"*, *"the WITH-DETAIL polarity stops being checked at the call site"*. The author
applied the lesson to the sweep (entry 20 exists and kills) and did not apply it to the rule
shipped twelve lines away. A fold whose subject is *recovery code that nothing drove would be this
repo's wiring class* leaves its sibling undriven.

Not Blocking: the mechanism **works today** — a consistent rename of `FIXTURE_PREFIX` in both
Python files, with `.gitignore` untouched, is caught, measured:

```
live rc=1
  ✗ `.gitignore` no longer ignores `.claude/hooks/_probe-*`, so a self-test killed by SIGKILL
    can leave fixtures a `git add -A` will commit (backlog #212).
```

What is missing is the guard on the guard.

**Proposed fix.** Give the fetch a seam a case can drive — `main(argv, *, gitignore_text=None)`, or
a module-level `_gitignore_text()` a case can patch — add one case that drives `main` over text
missing the line and asserts `(rc, out.count("✗")) == (1, 1)` in the style of the existing
`coverage is WIRED` case at `:806`, then add the 21st manifest entry mutating the call site to
`if False and not …` and expecting that case. `EXPECTED_MUTATIONS["scripts/check-surface-recall.py"]`
19 → 20 → **21**, declared sum 1179 → **1180**.

---

### HIGH 2 — Structural. `.gitignore` asserts a self-test case that does not exist (#216's own class, in #216's own fix)

**Premise** (`.gitignore:170-172`, added by this branch):

> `# ⚠ THE PREFIX IS NOW HELD IN THREE PLACES (here, check-surface-recall.FIXTURE_PREFIX,`
> `# check-ratchet-contract) and a self-test case reconciles this file against the constant, because`
> `# a consistent rename would otherwise orphan this line in silence. Backlog #215.`

**Measurement.** No self-test case reconciles **this file** against the constant. Every
`gitignore_covers` case in `_self_test` is given text the case itself builds
(`scripts/check-surface-recall.py:630-645`):

```
gitignore_covers(f"node_modules\n.claude/hooks/{FIXTURE_PREFIX}*\n.env\n", FIXTURE_PREFIX)
gitignore_covers(".claude/hooks/_SELFTEST-*\n", FIXTURE_PREFIX)
gitignore_covers(f"{FIXTURE_PREFIX}*\n", FIXTURE_PREFIX)
gitignore_covers(".claude/hooks/_other-*\n", "_other-")
gitignore_covers(".claude/hooks/_other-*\n", FIXTURE_PREFIX)
```

Nothing under `_self_test` reads `ROOT / ".gitignore"` — grepped over the whole suite region. The
real file is read only by `main` (`:390`), i.e. by a **CI step**, not by a case. And by HIGH 1 that
reader is removable in silence.

**Severity reasoning — High.** Backlog #216 is *"a comment asserted a defence the code did not
implement"*. This is a new comment asserting a defence the code does not implement, in the commit
that closes #216, and it is the **weakest-layer** comment of the three: `.gitignore` is classed as
prose by `check-review-recorded.py:149`'s `PROSE_FILES`, so a future edit to this very line is the
one change that does not require a review record. A reader who trusts the sentence concludes the
rename is covered by the suite and never asks whether CI still runs the step.

**Proposed fix.** Either make the sentence true (HIGH 1's driven case does exactly that, and then
both comments become accurate), or state what actually holds: *"`check-surface-recall.main`
reconciles this file against the constant, as its own CI step at `ci.yml:261`; the suite cases are
over the rule, not over this file."*

---

### MEDIUM 1 — Structural. `main`'s stated reason is falsified by its sibling change in the same commit

**Premise** (`scripts/check-surface-recall.py:385-386`):

> `# Here rather than in the suite because the`
> `# suite must run inside a staged tree that has no .gitignore;`

**Measurement.** `scripts/check-plan-code.py:203` adds `".gitignore"` to `HARNESS_TREE` **in this
same change**, for the stated purpose of letting the suite-driven `main` read it. Measured:

```
staged. with_gi has .gitignore: True
check-plan-code in STAGED tree rc=0 → 131/131 passed      (case: "every entry actually arrives")
```

The staged tree *has* `.gitignore`. The sentence is false as written, in the present tense.

The near-identical sentence at `:622-624` is fine, because it is explicitly **past tense** about
the first version (*"THE FIRST VERSION OF THIS READ THE REAL `.gitignore` HERE AND BROKE THE
MUTATION HARNESS — `HARNESS_TREE` does not stage `.gitignore`"*) — though even there the
subordinate clause is now stale and would read better as *"did not then stage"*.

**Severity reasoning — Medium.** Third instance of #216's class in #216's own fix, but unlike HIGH
2 it misstates a *reason* rather than claiming a *defence*, and the design it justifies (rule/fetch
split) remains correct for an independent reason the comment does not give: the staged copy is a
**copy**, so a case reading it would measure the harness, not the repo.

**Proposed fix.** Replace the reason with the one that survives: *"Here rather than in the suite
because the staged tree's `.gitignore` is a COPY — a case reading it would measure the harness, not
the repo. `HARNESS_TREE` stages it only so this block does not raise CannotRun under the harness."*

---

### MEDIUM 2 — Structural. Three uncaught exceptions in the new sweep, which is the wrong failure shape by this commit's own standard

**Premise** (`scripts/check-surface-recall.py:465-473`):

```python
for _stale in HOOK.parent.glob(f"{FIXTURE_PREFIX}*"):
    _tail = _stale.name[len(FIXTURE_PREFIX):].split(".", 1)[0]
    if not _tail.isdigit():
        continue
    try:
        _os.kill(int(_tail), 0)
    except ProcessLookupError:
        _stale.unlink(missing_ok=True)       # the owner is gone: this is debris
    except PermissionError:
        pass                                  # alive and not ours — leave it alone
```

**Measurement.** Probed in a copy, each case a single file placed in `.claude/hooks/` before
entering `_fixture_hook`:

```
superscript-digit tail (U+00B2):      ⛔ RAISED ValueError: invalid literal for int() with base 10: '²'
arabic-indic digit tail (U+0661):     NO CRASH | kept (reads as pid 1)
directory named like dead-pid debris: ⛔ RAISED PermissionError: [Errno 1] Operation not permitted: …/_selftest-2601.sh
symlink named like dead-pid debris:   NO CRASH | link removed, victim survived
pid 0:                                NO CRASH | kept
pid far above PID_MAX:                ⛔ RAISED OverflowError: Python int too large to convert to C int
```

Three uncaught paths:

1. **`ValueError`** — `str.isdigit()` is `True` for superscripts (`²`, `³`, `¹`) which `int()`
   refuses. The predicate and the parser disagree; `isdecimal()` is the one that matches `int()`.
2. **`PermissionError` / `IsADirectoryError`** — `unlink()` on a directory. Note the
   `except PermissionError: pass` cannot catch it: that handler is attached to the `kill` try, and
   the `unlink` runs **inside** the `ProcessLookupError` handler, where a sibling `except` has no
   reach. (macOS raises `PermissionError`; Linux raises `IsADirectoryError`.)
3. **`OverflowError`** — `_os.kill()` with an int wider than a C `int`.

Each aborts `_fixture_hook` **before** `path = …` is reached, so it is not a cleanup failure — it
takes down every case that uses the fixture, naming a cause unrelated to the guard's subject.

**Severity reasoning — Medium.** Reachability is low (nothing in the repo writes such a name; it
takes a human or a foreign tool). It is filed at Medium for two reasons. First, it is exactly the
standard this commit applies one file over: `scripts/check-plan-code.py:239-243` adds the
`is_dir()` branch because `copytree` on a file is *"a crash rather than a named CANNOT RUN and
therefore the wrong failure shape for this function"* — the identical argument, unapplied here.
Second, the sibling `.gitignore` entry makes the offending file **invisible to `git status`**
(see LOW 1), so the one artefact that would explain the crash is hidden.

**Proposed fix.** Wrap the per-entry body so one bad name is skipped, not fatal:

```python
for _stale in HOOK.parent.glob(f"{FIXTURE_PREFIX}*"):
    _tail = _stale.name[len(FIXTURE_PREFIX):].split(".", 1)[0]
    if not _tail.isdecimal():            # isdigit() accepts '²', which int() refuses
        continue
    try:
        _os.kill(int(_tail), 0)
    except ProcessLookupError:
        try:
            _stale.unlink(missing_ok=True)
        except OSError:
            pass                          # a directory, or not ours to remove — leave it
    except (PermissionError, OverflowError, ValueError):
        pass
```

and a case over a non-decimal `isdigit()` name, which is the half a reader will not re-derive.

---

### MEDIUM 3 — Transitional. Backlog row #219 does not exist on this branch, or on master

**Premise.** Seven citations in shipped code name it:
`scripts/check-backlog-closure.py:110`, `:128`, `:153`, `:282`, `:283`, `:303`, `:305`.

**Measurement.**

```
$ grep -c '219' docs/backlog.md                 → 0
$ highest row id in docs/backlog.md (HEAD)      → 218
$ git show master:docs/backlog.md | grep -cE '^\| 219 '  → 0
$ git grep -l '^| 219 ' <all refs> -- docs/backlog.md
close-201-202-and-token-adoption:docs/backlog.md
explainer-emphasis-baseline:docs/backlog.md
```

The row exists only on **other branches**. Two consequences, both measured:

- **A behaviour decision rests on an unreadable document.** `:128` refuses the adjacent-group form
  solely because *"#219 carries a live prediction about PR #362's title"*. I verified that claim
  against the row on `close-201-202-and-token-adoption` — it is **true** (the row reads
  *"PREDICTION, testable on this PR: its title ends `(backlog #201) (backlog #202) (#362)`, so after
  merge the guard should report #202 recorded and #201 unseen"*), and the shipped pattern preserves
  it (`'Two rows (backlog #201) (backlog #202) (#362)' -> {'202': …}`). But a reader of *this*
  branch cannot check that, and nothing here says where to look.
- **It is self-inflicting.** If this PR's title uses the convention the change exists to enable,
  this very guard reports the gap. Measured against the branch's own backlog:

```
closes: ['212', '216', '219']
stale, orphan = ([], ['219'])
     → "? #219: a commit closes it, but no row with that id exists"
```

**Severity reasoning — Medium / Transitional.** Nothing is wrong with the code; it is a merge-order
and provenance defect that resolves the moment the row lands, which is why it is Transitional. It
is not Low because the refusal of the adjacent-group form is a *shipped behaviour* whose only
written justification is off-branch, and because the orphan warning is a self-inflicted false
signal on the guard this PR is improving.

**Proposed fix.** Either land `close-201-202-and-token-adoption` first and rebase, or carry row
#219 in this branch's `docs/backlog.md`. Failing both, make the citations self-contained — name the
branch, or inline the one-sentence prediction at `:128` so the decision can be audited here.

---

### MEDIUM 4 — Transitional. The repo's own dashboard gate refuses this branch

**Measurement**, in the worktree:

```
$ python3 scripts/check-dashboard-entry.py   → rc=1
REFUSED — 6 tracked file(s) changed and no entry was added to docs/dashboard-entries.md.
```

Six tracked files change (`.gitignore`, `docs/backlog.md`, three scripts, one manifest) and no
entry is recorded. Per `docs/dev-process.md`'s enforcement table this blocks the branch.

**Proposed fix.** Add the `## YYYY-MM-DD` block, or `NO-ENTRY: <reason>` in the PR body — noting
the gate's own warning that a body edit alone will not re-pass without a push.

---

### LOW 1 — Structural. The sweep's stated cost model is falsified by its sibling `.gitignore` entry

**Premise** (`scripts/check-surface-recall.py:459-461`):

> `# ⚠ A REUSED pid reads as alive, so this UNDER-cleans. That is the correct direction: a stale`
> `# file costs one line of git status, a wrongly-removed live one costs a peer a red nobody`
> `# can explain.`

**Measurement.**

```
$ git check-ignore -v .claude/hooks/_selftest-12345.sh
.gitignore:176:.claude/hooks/_selftest-*	.claude/hooks/_selftest-12345.sh
```

It costs **zero** lines of `git status`, because the other half of this same commit ignores it. The
trade is still the right one — under-cleaning beats deleting a live peer's world — but the residue
is now *invisible*, not *cheap*, and invisible residue is what MEDIUM 2's crash hides behind.

**Proposed fix.** One clause: *"…a stale file is now ignored and therefore silent, which is why the
sweep is the only thing that removes it; a wrongly-removed live one costs a peer a red nobody can
explain."*

---

### LOW 2 — Structural. `_sweep_probe` is pid-reuse flaky, and the harness is where it will bite

**Premise** (`scripts/check-surface-recall.py:655-659`):

```python
_proc = subprocess.Popen([sys.executable, "-c", ""])
_proc.wait()                             # exited AND reaped, so the pid is truly gone
dead_pid = _proc.pid
```

**Reasoning.** Reaping frees the pid for reuse. Between `wait()` and the sweep's `kill()` sit two
`write_text` calls and a context-manager entry. If any concurrently spawned process lands on that
pid in that window, the debris is kept and the case fails with no defect present. Normally
negligible — but `check-plan-code.py --mutate .` spawns a suite per manifest entry across 1,179
entries, which is precisely the high-pid-churn setting, and the probe runs on **every** one of
those spawns of this file's suite.

I did not observe a failure (the case passed in every run here), so this is reasoned, not measured
— filed Low on that basis.

**Proposed fix.** Remove the dependence on a real pid for the *dead* half: patch `_os.kill` for the
duration of the probe to raise `ProcessLookupError` for the debris id and succeed for the peer id.
That also removes the probe's hidden assumption that pid 1 exists and is not ours, which is an
environment property rather than a property of the code.

---

### LOW 3 — Transitional. The "zero other subjects change verdict across those 300" claim is already false on HEAD

**Premise** (`scripts/check-backlog-closure.py:120`):

> `# Both rows happened to be ticked by hand, so nothing went stale; the guard was simply blind to a`
> `# correct statement. Zero other subjects change verdict across those 300 — measured.`

**Measurement.** The claim was exactly right when written, and is wrong now:

```
master: last-300 subjects, verdict changes = 1
   * Settled items look settled, and say who settled them (backlog #83, #87) (#223)
HEAD:   last-300 subjects, verdict changes = 2
   * Self-test debris cannot be committed, and the sweep that removes it is driven (backlog #212, #216)
   * Settled items look settled, and say who settled them (backlog #83, #87) (#223)
```

The second is commit `f429f8c7`, authored on this branch *after* the comment. This is the
*document-inside-the-corpus-it-measures* shape: the statement is stale at commit time, structurally,
and will go further out of date with every two-row closure the change enables.

**Proposed fix.** Date-stamp and scope the sentence to its subject: *"Measured 2026-10-02 against
`master`: exactly one subject changes verdict across the last 300, and none loses an id."* The
`REMOVED: []` half is the durable claim and is worth stating, because it is the one a reader
actually needs.

---

### LOW 4 — Structural. `gitignore_covers` is exact-line equality, and two reasonable `.gitignore` forms are refused

**Premise** (`scripts/check-surface-recall.py:345-346`):

```python
want = f".claude/hooks/{prefix}*"
return any(line.strip() == want for line in text.splitlines())
```

**Reasoning.** `git` ignores the path just as well with a leading `/` (`/.claude/hooks/_selftest-*`,
which is in fact *more* precise since the pattern contains a slash either way), and the reconciler
would report a problem over it. Symmetrically, it cannot see a later negation (`!.claude/hooks/…`)
re-including the path, so it can report *covered* when git does not ignore. Both are small; the
first direction is conservative (it warns), the second is the one that over-trusts.

The docstring explains why a *bare* prefix is refused but says nothing about either of these.

**Proposed fix.** Either accept an optional leading `/`, or add one line to the docstring stating
that the rule is **line equality, not git semantics** — and that a negation elsewhere in the file
is outside what it can see. Stating the bound is enough here; widening it is not obviously worth it.

---

## Could Not Measure

Recorded as failures of reach, never as passes.

| Not run | Why | What it would have told me |
|---|---|---|
| `check-plan-code.py --mutate .` — **the gate CI actually runs** | The worktree has no `node_modules`, so `stage_tree` refuses at `node_modules/typescript`; I staged that directory from the main checkout for the probes above, but a full `--mutate .` from the worktree root cannot run unmodified, and a full sweep of 1,179 entries was out of budget. **TREAT THE MUTATION SWEEP AS NOT RUN.** | Whether any of the other 1,178 entries' anchors were unbound by the `.gitignore`/`stage_tree` edits. I verified the one *new* entry binds and kills (see ⑦). |
| `check-plan-code.py --self-test` and `check-selftest-counts.py` **in the worktree** | Both exit 1 there, solely for the missing `node_modules/typescript` — `[FAIL] every HARNESS_TREE entry is present…: got ['node_modules/typescript']`. In a staged tree that has it: `check-plan-code 131/131 rc=0`, `check-paid-caller-arrival 32/32 rc=0`. **Environmental, not a finding** — but it means I did not see those two gates green against the real repo root. | Nothing further; the staged-tree runs cover the subject. |
| `check-guard-coverage.py` live entry point | Needs the Postgres catalog. `--self-test` is green (37/37). | Whether the two new functions are classified SHAPE/SEQUENCE correctly. |
| The `.gitignore` comment's *"reproduced at 3 of 13 kill offsets"* | Did not re-run the SIGKILL reproduction. | Whether the 3/13 figure still holds. |
| `check-merge-ready.py` | HEAD is detached and there is no PR for this branch. | The PR-only gates. |

Self-tests that **did** run clean in the worktree, for the record: `check-backlog-closure 28/28`,
`check-surface-recall 64/64`, `check-fixture-variation` (754 parameters / 62 files, rc=0),
`check-docs 22/22` + live rc=0, `check-ratchet-contract 56/56`, `check-rc-contract 55/55`,
`check-guard-coverage 37/37`, `check-review-rounds 77/77`, `check-dashboard-entry 13/13`,
`check-anchors 15/15`.

---

## Summary of the shape

The three rows are not equally finished. **#219's grammar change is the cleanest thing here** — the
anchor is intact under a hostile battery and a 1,583-subject diff, the loop cannot capture a
non-id, and the only verdict changes are the two genuine two-row closures. Its defect is
provenance, not code: the row justifying it is on another branch (MEDIUM 3).

**#216 is correct and well-evidenced** — I reproduced the sever by running the callee, and the new
comment is true.

**#212 is where the weight is.** The `.gitignore` line works (`git check-ignore` confirms), the
sweep's direction is right, `HARNESS_TREE`'s widening costs nothing measurable across 68 scripts,
and the new mutation kills via its named case. But the reconciler that keeps the whole thing honest
is wired to the verdict by nothing (HIGH 1), and **two of the three comments written to explain it
describe defences that do not exist** (HIGH 2, MEDIUM 1) — which is #216's class, in #216's fix,
twice. The pattern this repo keeps recording is *the row's own defect, reintroduced by its fix*
(backlog #110, both Blockings). This is that, again.

---

`NOT CONVERGED: 0 Blocking · 2 High · 4 Medium · 4 Low`
