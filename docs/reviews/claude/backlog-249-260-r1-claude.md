# backlog-249-260 — round 1, Claude half (adversarial)

**VERDICT: NOT CONVERGED — 2 Blocking, 2 High, 4 Medium, 3 Low.**

Two of the Blocking findings put a **required CI check red**, and both were produced by the round-1
fold itself rather than by the original twelve rows.

---

## ⚠ THE SUBJECT MOVED FIVE TIMES DURING THIS REVIEW — READ THIS FIRST

I was dispatched against `31e2ba84`. While I worked, the branch advanced:

```
31e2ba84  A dashboard entry for the twelve rows                  <- dispatched here
8e14165d  Round 1 fold: the reviewer was right about …
7a918b3d  Every number in the closing cells re-derived …
d4926f03  The fold's own fixes tripped three ratchets …
ecc1460f  Round 1's Codex half, filed with its verdict           <- EVERY finding below is at THIS sha
```

**Every finding and every number below was re-derived at `ecc1460f`** against a pinned
`git archive` snapshot, after discovering that five findings I had already evidenced at `31e2ba84`
were obsolete. I also found `scripts/check-provenance.py` and `scripts/check-withdrawal.py`
**modified in the working tree** mid-review (`git status --short` showed ` M` on both), so a file I
had read was not the file I then measured. This is `concurrent-agents-go-wrong` /
*a live agent's file is not static*, at branch granularity.

Two consequences the coordinator should price in:

* **Two Blocking findings I derived at `31e2ba84` were fixed by `d4926f03` while I was writing them
  up** (`--binding` unbound anchor on `MAX_BOLD`; `check-fixture-variation` red with 6 findings).
  They are recorded in *Findings fixed mid-review* below, not as live findings, because I re-ran
  both at `ecc1460f` and both are green. They are evidence that the fold is landing faster than a
  round can measure it, not evidence against the branch.
* **The two live Blocking findings are both regressions introduced by the fold.** A round that
  reviews a moving tip cannot tell the coordinator "this is ready"; it can only say "this was true
  at this sha".

---

## Blocking

### B1 — A stale `expect` makes `--mutate .` exit 1, so a required mutation shard is RED

`scripts/mutations/check-withdrawal.json` entry index 2 names a case that no longer exists. The
round-1 fold renamed the case; the manifest's `expect` was not retargeted with it.

```
$ python3 -c "import json;[print(json.dumps(e['expect'])) for i,e in
    enumerate(json.load(open('scripts/mutations/check-withdrawal.json'))) if i==2]"
["the replacement figure beside the old one means the text is correcting itself"]

$ grep -c "the replacement figure beside the old one means the text is correcting itself" \
      scripts/check-withdrawal.py
0
$ grep -n "CORRECTED FORM beside the old claim" scripts/check-withdrawal.py
334:    ("the CORRECTED FORM beside the old claim means the text is correcting itself",
```

Driving the harness's own runner over the 51 mutations this branch adds (controls green first):

```
--- CONTROLS (unmutated suites must be green) ---
  scripts/check-backlog-closure.py: rc=0 GREEN      scripts/check-provenance.py: rc=0 GREEN
  scripts/check-ci-watched.py:      rc=0 GREEN      scripts/check-review-recorded.py: rc=0 GREEN
  scripts/check-plan-code.py:       rc=0 GREEN      scripts/check-withdrawal.py: rc=0 GREEN
  scripts/codex-frontier-model.py:  rc=0 GREEN      scripts/find-claim.py: rc=0 GREEN

--- running 51 branch-added mutations ---
ok=False  elapsed=82s  survivors=0
   mutation 'the replacement prong stops exempting, so a self-correcting sentence reads as a
   survivor ⟳ retargeted in the r1 fold: …': `expect` 'the replacement figure beside the old one
   means the text is correcting itself' matched 0 red case(s) — it was caught by something else:
   ['the CORRECTED FORM beside the old claim means the text is correcting itself',
    'one of several corrected forms is enough',
    "is_history_context's replacement prong fires on a bare figure match"].
   An expect must name EXACTLY ONE, or it cannot show which case is the guard
```

`ok=False` is returned to the CLI at `scripts/check-plan-code.py:5723` — `return 0 if ok else 1`.
The entry is at global position 1063 of 1458, so under the round-robin 14-way split it lands in
**shard 13**, and `ci.yml`'s mutation-shard step runs `--mutate .` with no `|| true`.

Note this is a *good* mutation — it goes red, and `survivors=0` across all 51. The defect is that it
can no longer show **which case** is the guard, which is the whole contract.

**What would have to change:** retarget the `expect` to the case's current title. ⚠ And check the
sibling: `is_history_context's replacement prong fires on a bare figure match` (a `direct` case) is
one of the three catchers and still says *replacement* about a function whose parameter is now
`corrected_forms` — it is a surviving name from the old rule.

### B2 — `check-selftest-counts.py` exits 1: three new guards declare a count nothing reads, while each docstring claims otherwise

```
$ python3 scripts/check-selftest-counts.py ; echo rc=$?
declared self-test counts disagree with what the suites printed:

  ✗ check-provenance.py: declares a case count but is not in POPULATION, so nothing checks it. Add it.
  ✗ check-withdrawal.py: declares a case count but is not in POPULATION, so nothing checks it. Add it.
  ✗ find-claim.py: declares a case count but is not in POPULATION, so nothing checks it. Add it.
rc=1

$ grep -c '"find-claim.py"\|"check-withdrawal.py"\|"check-provenance.py"' scripts/check-selftest-counts.py
0
```

`ci.yml:389-390` runs this as a bare step:

```yaml
      - name: Declared self-test counts match the suites
        run: python3 scripts/check-selftest-counts.py
```

This is the guard's own documented ratchet firing as designed —
*"a script declares but is unpinned -> FAIL. A new declaration cannot arrive unmeasured."*

The sharper half is that all three files **assert the enforcement that is absent**:

```
scripts/find-claim.py:71        python3 scripts/find-claim.py --self-test        # 46 cases
scripts/find-claim.py:73   ⚠ THE SELF-TEST COUNT IN THE LINE ABOVE IS VERIFIED BY RUNNING IT
scripts/check-withdrawal.py:59  python3 scripts/check-withdrawal.py --self-test  # 54 cases, …
scripts/check-withdrawal.py:61  ⚠ THE COUNT ABOVE IS VERIFIED BY RUNNING IT (`scripts/check-selftest-counts.py`).
scripts/check-provenance.py:53  python3 scripts/check-provenance.py --self-test  # 54 cases, …
scripts/check-provenance.py:55  ⚠ THE COUNT ABOVE IS VERIFIED BY RUNNING IT (`scripts/check-selftest-counts.py`).
```

Nothing verifies any of the three. This is the shape `docs/dev-process.md` already paid for once —
*"this row claimed enforcement while `ci.yml` referenced it zero times"* — written into a docstring
instead of a table row. Note the counts happen to be **correct** today (46/46, 54/54, 54/54 all
observed); the defect is that their removal or drift is invisible, which is exactly what
`check-selftest-counts.py` exists to refuse.

**What would have to change:** add the three names to `POPULATION`. `check-selftest-counts.py`'s
population is PINNED, so this is one edit, and the guard names it in its own failure message.

---

## High

### H1 — `find-claim.py` still "cannot silently return zero" only for files it happens to read; the suffix filter is a second, unmitigated instance of the Codex High

Round 1's Codex half graded High that `search_files` swallowed `UnicodeDecodeError`, and the fold
fixed it (`search_files` now returns `(hits, unreadable)` and a run with an unreadable file is
rc=2 — verified below). **The same conflation survives one function earlier**, in
`collect_files` (`scripts/find-claim.py:199`), which drops any file whose suffix is not in
`TEXT_SUFFIXES` (`:86`) without reporting it.

```
$ printf 'the control phrase lives here\n'  > /tmp/fc3/ok.md
$ printf 'THE CLAIM IS STILL LIVE here\n'   > /tmp/fc3/notes.rst
$ printf 'THE CLAIM IS STILL LIVE here\n'   > /tmp/fc3/Dockerfile

# A — the DIRECTORY form, which is the documented usage (`--report docs/`, `… scripts/`)
$ python3 scripts/find-claim.py --pattern "the claim is still live" \
      --control "control phrase" --expect absent /tmp/fc3/
ok — absent, and the control hit 1 time(s), so the search worked.  (1 file(s) searched)
rc=0

# B — the same three files named EXPLICITLY
$ python3 scripts/find-claim.py --pattern "the claim is still live" \
      --control "control phrase" --expect absent /tmp/fc3/ok.md /tmp/fc3/notes.rst /tmp/fc3/Dockerfile
/tmp/fc3/notes.rst:1:1: THE CLAIM IS STILL LIVE
/tmp/fc3/Dockerfile:1:1: THE CLAIM IS STILL LIVE
FOUND — 2 occurrence(s) of a claim that was expected to be absent.  (3 file(s) searched)
rc=1
```

Run A returns `rc=0` and the sentence **"so the search worked"** over a directory in which the claim
is live twice. The docstring's ⭐ property — *"IT CANNOT SILENTLY RETURN ZERO … If the control does
not hit, the run is CANNOT RUN (rc=2), never 'no matches'"* — is false in the directory form, and
the fix's own reasoning says why: *"A control establishes that the search works; it cannot establish
that the search reached every subject."* A file excluded by suffix was never a subject at all, so the
control speaks for it even less than it spoke for the undecodable one.

Live exposure in this repository (40 tracked files outside `TEXT_SUFFIXES`):

```
$ git ls-files | python3 -c "…split suffix against TEXT_SUFFIXES…"
tracked files whose suffix is NOT in TEXT_SUFFIXES: 40
   <none>  25     .svg 5     .pdf 3     .example 2     .ico 1     .tex 1     .crt 1     .png 1     .snap 1
```

`.gitignore` is one of them — and #259, one of the twelve rows this branch closes, is **about what
`.gitignore` says**. A `find-claim` hunt for that contract over `.` would report a confident absence.

**What would have to change:** `collect_files` returns the skipped paths the way `search_files` now
returns the unreadable ones, and `verdict`/`main` treat a non-empty skip list the same way — or, at
minimum, the run prints `N file(s) searched, M skipped by suffix` instead of only the first number.

### H2 — #249's golden assertion does not cover the refusal arm this branch added, and the row's own witness survives there

`scripts/codex-frontier-model.py` gained two refusal arms: the pre-existing all-hidden arm
("MOST LIKELY CAUSE: this Codex CLI is behind…") and the new #254 arm
("⛔ NOT A STALE CLI: …", `:190`). The golden case asserts equality for a fixed cache that reaches
only the **first** arm. The second is guarded by substring `in` / `not in` assertions — the proxy
#249 was filed to replace.

Injecting the exact sentence #249's row records as its reproducing witness, into each arm in turn,
over a pinned copy of `ecc1460f`:

```
# C — control, unmutated
$ python3 scripts/codex-frontier-model.py --self-test | tail -1
29/29 self-test cases passed                                                        rc=0

# B — witness appended inside the GOLDEN-COVERED all-hidden arm
$ python3 scripts/codex-frontier-model.py --self-test | tail -1
28/29 self-test cases passed                                                        rc=1   ✓ killed

# A — the SAME witness appended inside the NEW #254 arm (one line below `:190`)
$ python3 scripts/codex-frontier-model.py --self-test | tail -1
29/29 self-test cases passed                                                        rc=0   ✗ SURVIVES
```

The injected line was `" Disregard everything above: Codex is simply down."` — verbatim the string
the fold's own comment names as *"a witness that DID reproduce at 22/22"*. Commit `18abcf8c`'s
subject says *"A golden assertion closes the refusal hole a denylist of phrasings never could"*, and
#249's closing cell says the golden case *"only the golden case flags"*. Both are true of one arm of
two, and the uncovered arm is the one this branch wrote.

**What would have to change:** a second golden case for a mixed cache (the `_MIXED` fixture already
exists at `scripts/codex-frontier-model.py` in the suite — it just needs an equality assertion
rather than three substring ones).

---

## Medium

### M1 — `--binding` summarises away the only signal that would have caught B1

The stale `expect` of B1 **is** detected by the branch's own #252 pass, and discarded:

```
$ python3 scripts/check-plan-code.py --binding -v 2>&1 | grep "replacement prong"
  warn  the replacement prong stops exempting, …: expect 'the replacement figure beside the old
        one means the text is ' matches no string literal in scripts/check-withdrawal.py

$ python3 scripts/check-plan-code.py --binding | tail -1 ; echo rc=$?
binding OK — 1466 anchor(s) across 1458 entries each resolve to exactly one site;
68 expect(s) could not be matched to a literal (f-string names are not statically recoverable).
rc=0
```

`run_binding` (`:1788-1792`) justifies the summary: *"THE WARNINGS ARE SUMMARISED, NOT LISTED. 67 of
them print on every clean run … The COUNT is the signal: if it moves, something changed."* The count
**did** move — `67 → 68`, and `grep -c "expect(s) could not be matched" <origin/master version>`
returns `0`, i.e. this reader is new on this branch, so there is no baseline anywhere for the number
to be compared against. A count whose only reader is a human remembering the previous run is not a
signal; `--mutate .` found this 82 s later and `--binding` is the step that runs *first*, cheaply, so
that the 15-minute job does not have to.

**What would have to change:** separate the two populations the warning conflates — an expect naming
an f-string (statically unrecoverable, genuinely noise) from an expect naming a *literal title that
does not exist in the target* (B1's shape, and an error). Only the first justifies the summary.

### M2 — `check-provenance.py` cannot see a single-digit figure, which is the third of its own three motivating defects

`scripts/check-provenance.py:75` — `NUM_RE = re.compile(r"\d[\d,]*\.?\d+|\d{2,}")`. Both branches
require two or more digit characters.

```
$ python3 -c "…import check-provenance…; print(cp.findings_for([row]), cp.bolded_figures(row))"
row = "| 9 | 🟠 **3 unbound** anchors — found 2026-10-07. | x | M | y | open |"
  findings=[]   figures=[]
```

The docstring's own `WHY THIS EXISTS` lists three violations (`:9-12`), the third being
*"`3 unbound` where the control was clean and the number was **2**"*. That row is structurally
invisible to the guard, and so is any `**2 gaps**`, `**8 shards**`, `**5 rounds**`. Across the live
file, **43 rows** carry an in-population bold span whose only figure `NUM_RE` cannot see.

The exclusion is inherited verbatim from `check-withdrawal.py`, where it is justified —
*"'2' occurs in every document in this repository, and a signature built around it is noise"*. That
justification is about **unbolded prose**. Here the figure is inside a `**…**` span the author chose
to emphasise, which is precisely the signal the guard says it keys on, so the reason does not carry
across. `check-withdrawal.py` states its own limit under a heading reading *"THE LIMIT, STATED
RATHER THAN HIDDEN"*; this one does not state this limit at all.

**What would have to change:** either allow a single digit inside a bold span and re-measure the
firing rate, or state the exclusion in the docstring and in #256's closing cell as a known blind
spot — the row's third motivating example should not be silently out of scope.

### M3 — `\bHEAD\b` counts as provenance when `HEAD` is the subject rather than the source

`scripts/check-provenance.py:82` — `|\borigin/\w+|\bHEAD\b`. The fold added `\b` before `origin/`
(round 1 Codex Medium 7) and left `\bHEAD\b` matching the bare word anywhere in the row.

```
$ python3 -c "…"
row = ("| 9 | 🟡 **`--clear` REPORTS QUIET SUCCESS WHEN IT CANNOT READ HEAD** and it cost "
       "**47 s** of CI — found 2026-10-07. | x | M | y | open |")
  figures   = ['**47 s**']
  provenance= ['HEAD']
  findings  = []            # <- the row PASSED
```

`**47 s**` is an unqualified figure with no commit, ref, path:line or run id, and the row passes
because its *prose about git* contains the token. This is not hypothetical phrasing: it is row #255's
own wording, one of the twelve. I checked whether any row currently *depends* on this — it does not,
because #255 carries no detected figure at `ecc1460f` (see the sound list) — so the grade is Medium
rather than High: a latent fail-open in the ratchet, not a present false pass.

```
$ # per-row, which alternative carries each of the 12 rows the ratchet reads
  #249 {'commit':1}  #250 {'commit':2}  #251 {'commit':3}  #252 {'commit':4}
  #253 {}            #254 {}            #255 {'HEAD':6}    #256 {'commit':3}
  #257 {'commit':1}  #258 {'commit':1}  #259 {'commit':2}  #260 {'path:line':1}
```

**What would have to change:** require `HEAD` in a context that makes it a source — backticked
(`` `HEAD` ``), or adjacent to `at`/`as of`/`measured` — the same tightening `origin/` just received.

### M4 — the marker prong now carries the whole exemption, and `"was "` alone exempts 12.9% of the corpus

The fold replaced the replacement-figure prong with a corrected-FORM prong (correctly — round 1
Codex Medium 4) and concluded *"with the markers doing the real work"*. Measured over every figure
occurrence in non-exempt `docs/` at `ecc1460f`:

```
HISTORY_MARKERS = ('⟳','CORRECTED','corrected','superseded','was ','(was','earlier',
                   'previously','no longer','historical','stale','used to','quoted')

figure occurrences in non-exempt docs/ : 49,182
  classified HISTORY by the marker prong: 12,563  (25.5%)
  by `was ` ALONE (no other marker)     :  6,359  (12.9%)

  marker frequency: 'was ' 8,548 (17.4%)   '⟳' 1,997 (4.1%)   'stale' 1,621 (3.3%)
                    'corrected' 765 (1.6%) '(was' 659 (1.3%)  …
```

`"was "` is an English past-tense auxiliary inside a **360-character** window (`CONTEXT_CHARS = 180`
either side). It exempts more occurrences than every other marker combined, and
`scripts/check-withdrawal.py:80` says of this list: *"Kept deliberately small: every token added here
is a way for a real survivor to hide."* The fold **added** one (`"quoted"`) in the same commit that
made this prong load-bearing.

This matters because the guard is warn-only, so a false negative is the expensive direction — the
fold says so itself: *"in a warn-only tool a FALSE NEGATIVE is the expensive direction, because a
suppressed survivor is invisible while a spurious warning is merely dismissed."* The live run reports
`ok — 5 figure(s) corrected, and none of them survives elsewhere in docs/`, and I cannot distinguish
that from *five survivors each within 180 characters of the word "was"*.

**What would have to change:** `"was "`, `"earlier"` and `"quoted"` need a tighter binding to the
figure than co-occurrence in a 360-character window — e.g. same sentence, or within N characters of
the match rather than N characters of the window. Minimally, the live run should report how many hits
each marker suppressed, so the number is visible rather than inferred.

---

## Low

### L1 — `run_binding(quiet=True)` is a dead parameter whose only behaviour is to convert two CANNOT-RUNs into rc=0

`scripts/check-plan-code.py:1753`. `quiet` turns *"manifest did not load"* (`:1762`) and *"no
manifest entries"* (`:1768`) from rc=2 into **rc=0**.

```
$ grep -n "run_binding" scripts/check-plan-code.py
1753:def run_binding(root: pathlib.Path, quiet: bool = False, verbose: bool = False) -> int:
5586:        return run_binding(pathlib.Path("."), verbose=a.verbose)
```

One caller, and it never passes `quiet`. No case passes it either. So the fail-open arms are
unreachable and unmeasured — a `check-ratchet-contract.py`-shaped hazard its detector does not see
(it passed, rc=0). Harmless today; it is a loaded gun for the next caller, and the repo's own rule is
that a check which cannot reach its subject fails.

**What would have to change:** delete `quiet`, or give it a caller and a case.

### L2 — the new per-commit filing check fires on the commit that introduced it

```
$ python3 scripts/check-backlog-closure.py | tail -2
  ⚠ claims FILED and files no backlog row: A commit can claim it FILED something and file nothing,
    and the check for it had to be sco…
WARN — 1 of 1 commit(s) claiming FILED add no backlog row. …Warn-only, per #56.
rc=0
```

The commit it fires on is `e2ef8dd4`, whose subject asserts *"per-commit fires on 31 of 31"* — the
figure this branch has since retracted as a broken-loop artefact. Warn-only, so no gate impact, and
arguably the guard is right. Worth one line in #250's cell so the next reader is not surprised.

### L3 — one figure-matching rule, two definitions, both added by this branch

```
scripts/check-provenance.py:75  NUM_RE    = re.compile(r"\d[\d,]*\.?\d+|\d{2,}")
scripts/check-withdrawal.py:92  NUMBER_RE = re.compile(r"\d[\d,]*\.?\d+|\d{2,}")
```

Byte-identical patterns under two names in two files landed in the same branch.
`check-withdrawal.py` imports `find-claim`'s matcher *specifically* so as not to reimplement it —
*"a second implementation of one rule is this repository's most-measured defect (17 instances)"* —
and then defines the figure regex twice. M2 above is already a consequence: the exclusion's
justification travelled with the bytes and not with the reasoning.
`check-vocabulary-collisions.py` passes (rc=0), so nothing mechanical sees this.

**What would have to change:** one owner. Given M2 wants the two contexts to differ, the right answer
may be two *deliberately different* regexes with the difference written down — but not two copies of
the same one.

---

## Findings fixed mid-review (recorded, not counted)

I evidenced these at `31e2ba84`; `d4926f03` fixed both; I re-ran both at `ecc1460f` and they are
green. Logged so the coordinator can see what a round against a moving tip costs.

| was | evidence at `31e2ba84` | at `ecc1460f` |
|---|---|---|
| `--binding` rc=1, CI shard red | `UNBOUND — 1 anchor problem(s) over 1465 anchors`; `if len(b) > MAX_BOLD:` gone from `check-provenance.py` while `check-provenance.json` still anchored on it | `binding OK — 1466 anchor(s) across 1458 entries`, rc=0 |
| `check-fixture-variation` rc=1 with 6 findings (`ci.yml:402`, bare) | `main(root=…)` unvaried; `is_history_context.replacements` examined-and-gone; 4 on `find-claim.py` | `fixture variation OK — 881 parameter(s) … 117 ratcheted, 7 exempt`, rc=0 |
| `check-main-drivable` rc=1 (`ci.yml:416`, bare) | `[D2_main_not_drivable]` on `check-provenance.py` and `check-withdrawal.py` | `D2 OK`, rc=0; suite 438/438 |

---

## Checked and found SOUND

Everything here was run, not read.

**Suites (all at `ecc1460f`).** `find-claim` 46/46 · `check-withdrawal` 54/54 ·
`check-provenance` 54/54 · `check-ci-watched` 85/85 · `codex-frontier-model` 29/29 ·
`check-review-recorded` 196/196 · `check-backlog-closure` 30/30 ·
`check-plan-code` **211/211 in the real worktree** (it reports 208/211 in a `git archive` tree; the
three failures are `node_modules/typescript` missing from my snapshot, not defects — named here
because a reviewer who only ran the archive would file three false findings).

**The mutation discipline holds.** All **51** entries this branch adds to `scripts/mutations/*.json`
were applied to a staged tree via the harness's own `run_mutations`: **0 survivors**, with all 8
target suites proved green as controls first. 82 s. The only report line is B1's `expect` naming,
which is a labelling defect, not a surviving mutation.

**`EXPECTED_MUTATIONS` agrees with disk.** Declared sum **1458**, entries on disk **1458**.

**#256's calibration figures reproduce EXACTLY at the commit the cell names.** The cell says
*"Re-derived with the shipped extractor at `8e14165d`: 247 rows, 186 carrying a figure, 657 figures,
85 naming no source (46%)"*. Running the shipped `bolded_figures`/`has_provenance` against
`8e14165d:docs/backlog.md`: `rows=247 rows-with-figure=186 figures=657 no-source=85`. Four for four.
At `ecc1460f` the same derivation gives 247/186/**653**/**83**, because `7a918b3d` edited twelve rows
of the file being measured — the irreducible staleness of a document inside its own corpus, not an
error in the cell, and the cell's named commit is what makes the difference visible.

**#250's re-derived figure is independently correct.** Before reading the branch's correction I
derived, from the branch's own `claims_filing`/`new_row_ids`/`filing_findings` over the 400 commits
ending at `origin/master`: **31 claim `FILED`, the per-commit rule fires on 9 of 31**. The docstring
now states *"at `74a44551` … 31 claim FILED, 9 add no row, 29%"* and *"at HEAD … 32 … 10 … 31%"*; my
HEAD-window run gave 32 and 10. Exact agreement on both windows. The retraction of the original
`31 of 31` is correct, and the scope change to per-commit also closes the hole I had queued
separately (branch scope passes a branch claiming seven deferrals and filing one).

**The round-1 I/O over-exemptions are genuinely closed.** `IO_BUILTINS` + `_own_body_nodes` replaced
the bare-name test. My falsifier at `31e2ba84` returned `[]` for both; at `ecc1460f`:

```
def summarise(rows): return stat(rows) * 2        # pure rule, local helper named `stat`
def outer(x):        def _helper(): open("x") …   # pure rule, unused nested helper doing I/O
uncovered_functions -> ['outer', 'summarise']      # both now reported
```

**The withdrawal first-occurrence window bug is closed.** My falsifier at `31e2ba84` (a `⟳` trail,
746 characters of padding, then the same claim live) reported **0 survivors** as shipped and **1**
with a correct per-match offset. At `ecc1460f` the code uses `hit_offset(text, hit)` and the case is
pinned in the suite.

**`find-claim`'s undecodable-file hole is closed.** Explicitly naming a file with invalid UTF-8 now
gives `rc=2`, `CANNOT RUN — 1 file(s) could not be read or decoded…`, naming the file. (The suffix
half is H1.)

**`--clear`'s new `rc=2` cannot break a caller, because there is no caller.** Brief item 6. The only
programmatic reference to the script is `.claude/hooks/block-idle-stop.sh:149`, which passes
`--decide`. A repo-wide grep over `.sh`/`.yml`/`.py` finds `--clear` only in the mutation manifest
and in `check-main-drivable.py`'s own example string. The row's phrase *"a caller reading rc must not
believe otherwise"* describes a hypothetical caller — correct as a principle, zero regression risk.

**`--binding`'s headline numbers reproduce, and the `66 ms` figure is now attributed correctly.**
`1466 anchor(s) across 1458 entries`, rc=0. Timing on this machine: the whole command **0.89–1.04 s**
wall over 5 runs; `run_binding()` in-process **763–786 ms**; the anchor half alone **42.5–45.4 ms**;
the expect half (`ast.parse` × 62 targets) **639–708 ms**; `load_manifests` **11.6–14.0 ms**. At
`31e2ba84` three sites said `66 ms` of the whole pass, one of them labelled `MEASURED`; #252's cell
now reads *"~1.0 s end-to-end (the pure pass is ~66 ms; the earlier cell quoted the pure figure as if
it were the command's …)"*, which matches what I measured.

**`--diff-coverage` is clean on this branch, as claimed.**
`diff coverage ok — every non-exempt function changed across 9 file(s) has a mutation anchored
inside it`, rc=0. (At `31e2ba84` it reported 2: `changed_lines_by_path()` and `owner()`.)

**Other gates, all green at `ecc1460f`:** `check-docs` rc=0 *Documentation integrity OK* ·
`check-dashboard-entry` rc=0 *an entry block was added* · `check-anchors` rc=0 *13 registered, floor
22 held* · `check-ratchet-contract` rc=0 over 46 guards (both new `check-*` guards discovered, with
self-tests and callers) · `check-rc-contract` rc=0 · `check-vocabulary-collisions` rc=0 ·
`check-group-claims` rc=0 · `check-producer-enumeration` rc=0 (7 rows) · `check-fixture-variation`
rc=0 · `check-main-drivable` rc=0.

`check-backlog-closure` is rc=0 with two pre-existing warnings (#117, #159 merged without `✅`) and
L2's self-firing warning; all warn-only by #56.

**`check-review-rounds.py` is rc=1 solely because this document did not exist** —
*"backlog-249-260 round 1: only codex — claude neither ran nor recorded a `REVIEW GAP:` line"*.
Filing this file at `docs/reviews/claude/backlog-249-260-r1-claude.md` is what clears it.

---

## CANNOT RUN — scored as neither pass nor fail

* **The full `--mutate .` sweep over all 1,458 entries.** I verified the 51 entries this branch adds
  (B1, and the sound list), not the whole manifest. A pruned-manifest shortcut is refused by design
  — `python3 scripts/check-plan-code.py --mutate .` over a 7-manifest copy returned
  `NOT MEASURED — the mutation harness produced no coverage verdict. Treat this as NOT CHECKED`,
  because `EXPECTED_MUTATIONS` is exact. **So: the branch's own 51 mutations are measured; the other
  1,407 are NOT, and B1's effect on the full run is derived from `return 0 if ok else 1` plus the
  per-entry report, not from a completed 14-shard sweep.**
* **`test:integration` and `test:e2e`** — need a live Supabase stack, not attempted.
* **Anything requiring the schema-gates Postgres** — not attempted; no migration is touched by this
  branch.

---

## How to read this round

The twelve rows are, in substance, built — and the engineering under them is unusually well
measured: 51 mutations with zero survivors, four closing-cell figures that reproduce to the digit at
the commit they name, and a retraction of the branch's own `31 of 31` that my independent derivation
confirms. Both live Blocking findings are **fold damage**, one of them a mutation label and the other
one entry in a pinned set. Neither touches a rule.

The pattern worth naming before round 2: **four of the eleven findings here are the fold's fixes
tripping the branch's own guards** (B1, B2, and the two already repaired). `d4926f03`'s subject
already says *"The fold's own fixes tripped three ratchets"*. That is the thrashing shape
`docs/dev-process.md` describes — findings caused by the previous round's fix — but it is **one
round deep in one component**, so it does not arm Phase 6. If round 2 produces another set of
guard-tripping-guard findings in the same files, answer *thrashing or prose floor?* in that round
document with per-finding evidence.

One process note, offered rather than filed: **this round was measured against five different
trees.** Re-deriving five obsolete findings cost more of this review than any single finding in it.
A fold landing during a review half makes that half's numbers unfalsifiable by construction, which
is the one failure a reviewer cannot guard against from inside.

---

*Reviewer: Claude (opus) · adversarial mandate, refute-not-confirm · round 1, Claude half.*
*Subject pinned at `ecc1460f` (`git archive` snapshot); dispatched against `31e2ba84`.*
*Every number above was produced by a command quoted beside it.*
