# peer-sites — round 2, Claude half

**Subject:** `71378cd3` (parent `52010914`). `git status` was **clean at start and at end**; nothing
moved under this round. `scripts/peer-sites.py` md5 `cd72ee4fa28a334896a551c20720fe5d` — byte-identical
to the `T1030` snapshot I pinned at the end of r1, so those measurements carry without re-running.
Every finding below names the commit it was measured against; all of them are `71378cd3` unless said
otherwise.

**Verdict: NOT CONVERGED.** 4 High, 4 Medium, 4 Low. **The r1 fixes are real** — I verified all 16
manifest entries myself rather than taking them, and every one is honest. But you were right about
where to look: **10 of the 12 findings are in the hook or in decisions nobody cased**, and the
single sharpest one is that `peer-sites-advisory.sh` reproduces, in its own suite, the exact defect
it was built to fix.

**Anchoring check, stated so you can audit it.** Three r1 findings I expected to confirm closed are
closed and I say so (H4, M1, M3). Two I expected to confirm are **not** what I expected: H2's
divergence survives attack and I now think your version is better than the neighbours' (R-H2 below),
and the M2 fix reintroduced its own named class one level down (R5). The four "carried" items are
carried because I re-ran the mutations against this commit, not because I filed them before.

---

## Answers to your three questions

### 1 · `_if_chain`'s `else` arm — **not correct. It re-creates the tiling problem for exactly one arm.**

Measured on `71378cd3`:

```
 3:     if x == 1:          members [(3,3), (6,9)]
 4:         a()
 5:     else:
 6:         result = compute(          touch  3 (the `if` TEST)              -> SPEAKS
 7:             alpha,                 touch  4 (INSIDE the if arm)          -> SILENT
 8:             beta,                  touch  6 (the else's 1st stmt head)   -> SPEAKS
 9:         )                          touch  7 (INSIDE the else's 1st stmt) -> SPEAKS
10:         cleanup()                  touch 10 (the else's 2nd statement)   -> SILENT
```

Three different rules for "I edited this arm" inside one container. The docstring rejects whole-arm
members *because* they tile — then makes one arm whole, and it is the arm with no test, therefore
the one most likely to hold a large statement.

**On your own fixture it is worse than a miscount.** Touching line 8 (`elif y == 2:`, the *inner*
chain's test) yields two reports, and the outer one is:

```
if/elif chain: you changed 1 of 2 branches
    :3        if x:
  > :6-9      if y == 1:      <- marked touched; prints a line the user did not change
```

That is **B1 arriving through the range instead of through the AST** — the outer `if x:` offered as
a peer of an edit belonging entirely to the nested chain, which is what `_is_elif` was written to
stop. The printed body text is the member's *first* line, so the reader is shown `if y == 1:` for an
edit to `elif y == 2:`.

**And it can silence the outer container.** Touching `{3, 6}` — outer test plus inner test — puts
line 6 inside `(6,9)`, so both outer members read as touched, the container is filtered as "fully
touched", and only the inner chain reports. The docstring's stated fear is realised, confined to the
else arm.

Options, my order: **(a)** represent `else` by its head keyword line, restoring symmetry with the
tests and giving the reader a line they can point at; **(b)** every arm by its full body, accepting
that "all arms touched" means "you rewrote the statement" — measured on `52010914`, 16
partially-touched vs 1, costing 44 silences; **(c)** keep the span and state the asymmetry. What is
not defensible is (b) for one arm while the docstring argues against (b).

### 2 · the `main`-driving machinery — **sound, with one caveat that turns out to matter**

I went looking for "asserts the world it builds" and did not find it. What I checked:

| risk | measured |
|---|---|
| the fake result object lacks `.stderr` | **no risk** — all 5 `.stderr` occurrences in the module are `file=sys.stderr` print destinations; nothing reads `r.stderr` |
| `try/finally` restores both globals | yes, both `subprocess.run` and `REPO`, on both helpers |
| *"the BASE reaches the diffs, never the ref"* could pass vacuously | it can if the diff calls vanish — but the sibling case *"a partially-touched container is still advised on"* requires them, so the pair is jointly sound |
| the assertions are about the fake, not the code | **no** — they assert which argv the code produced and what it printed. That is testing the code through a boundary, not testing the boundary |
| the `SystemExit` catch hides a real failure | it converts an abort into an attributable `[FAIL]`, which is the same fix as r1's thunk-passing for `containers("def (")`. Correct, and the reason is now written down |

**The caveat.** `fake_run` returns a bare `"@@ -3 +3 @@\n+…"` with **no `diff --git` / `index` /
`---` / `+++` preamble**. Real `git diff` always emits one. For a single-file diff that is harmless
(the preamble precedes the first `@@`, so `cursor` is still 0). But it means the fixture's contract
is narrower than git's actual output — and R5 below is precisely a defect that lives in the part of
git's output the fake omits. The machinery is sound; its *corpus* is not the real thing.

### 3 · `main`'s population — **genuinely satisfied.** Measured on `71378cd3`:

```
check-fixture-variation.py                       rc=0
  539 parameters across 52 files; 7 exempt (was 9)
analyse(peer-sites.py, exempt=EXEMPT)            -> no findings
analyse(peer-sites.py, exempt={})                -> no findings      <- not resting on an exemption
EXAMINED keys now include                        -> main.argv
call sites                                       -> main(["--diff","master"])  and  main([arg])
```

Two call sites, genuinely different argv *shapes* (flag form and positional form), and the guard is
clean with the exemption dict emptied for this file. Nothing to add.

---

## Your C1 and C2

### C1 — **you did not just add cases that pass.** Verified independently on `71378cd3`.

All **16** manifest entries: anchor occurs exactly once, mutation goes red, and the red arrives
**via the case the entry names**. Control proved green first (59/59), each mutation applied to a
copy outside the repo.

```
16 entries, 0 problematic
```

Including the four that close B1 and H1 (`else:` + indented `if`; head LINE rather than RANGE) and
the six that close the r1 H5 survivors. I also probed the *other* direction on `_is_elif`
(`return False`, splitting a genuine `elif` chain into singletons) — also dies. Both directions
covered.

### C2 — **you were right to point me here, and the answer is worse than you think.**

See R1 and R2. The short version: the hook's `--self-test` covers `_wants_check` and nothing else,
and **the exact rc=1 fail-open you found by live-firing is still unfalsifiable** — reintroducing it
leaves the suite green.

---

## High

### R1 · the hook's self-test covers one of its eight behaviours, and the C2 regression goes green

`.claude/hooks/peer-sites-advisory.sh` `--self-test` exits at `:69`. Everything from `:71` down —
payload parsing, base resolution, the timeout choice, the rc contract, the grep, the output — has no
case. Mutated a copy **outside** the repo, control `9 cases: 9 passed, 0 failed`:

```
SURVIVED  the C2 REGRESSION: rc=1 accepted as success (`-ne 0` -> `-gt 1`)
SURVIVED  the CANNOT-RUN note is swallowed entirely
SURVIVED  the advisory never prints (grep looks for a string report never emits)
SURVIVED  the timeout wrapper is dropped entirely
SURVIVED  the base-unresolvable CANNOT RUN is swallowed
SURVIVED  running ON the base branch no longer short-circuits
SURVIVED  stdout becomes stderr (the channel changes silently)
KILLED    [control-positive] the --dry-run guard is removed        9 cases: 8 passed, 1 failed
KILLED    [control-positive] _wants_check matches everything       9 cases: 6 passed, 3 failed
```

**7 of 7 body mutations survive; both control-positives die**, so the suite works — for the one
function it covers. Your own header at `:34-36` says the rule was separated from the fetch
*"because three ratchets in this repo went eight days untestable"*. The separation happened; the
second half never got cases. **C2's two lessons are recorded as comments, not as falsifiers**, which
is this project's *a convention catches what you READ; a script catches what is THERE* — and the
comment at `:106-111` is a 6-line account of a defect that can be reintroduced under a green suite.

*Falsifier:* a case that feeds the hook a payload and asserts it speaks on rc=1.
*Siblings — searched.* I asked whether the repo's other hooks are in the same state. They are not
comparable: `block-default-branch-push.sh` carries a 9-case `--self-test` that CLAUDE.md records as
mutation-killed, and `enforce-handoff-path.sh`/`enforce-selection-card.sh` delegate their rule to a
`scripts/check-*.py` with its own suite *and manifest entries*. `peer-sites-advisory.sh` is the only
message-bearing hook whose logic lives entirely in bash with no ratcheted guard behind it.

### R2 · nothing runs the hook's self-test — the P2 fix reproduced P2

```
grep -rn "peer-sites-advisory" (excluding docs/reviews/):
  .claude/settings.json:21        the PreToolUse wiring
  scripts/peer-sites.py:78        prose
```

No CI step, no script, no gate invokes `--self-test`. And nothing discovers it:
`check-selftest-counts.py`'s population is `glob("*.py")`; `check-ratchet-contract.py:869` globs
`scripts/*.sh` **as callers**, not `.claude/hooks/*.sh` as subjects.

r1 P2 was *"`peer-sites.py` shipped with no caller at all"*. The fix gave the script a caller and
shipped **127 lines of bash with a 9-case suite that nothing runs** — the same defect, one layer
out, in the fix for it. That is this branch's own subject matter.

*Falsifier:* a caller for `bash .claude/hooks/peer-sites-advisory.sh --self-test`.
*Siblings — searched.* I checked every `.claude/hooks/*.sh` for a `--self-test` and for a runner.
`block-default-branch-push.sh` has one and CLAUDE.md names its mutation coverage;
`enforce-handoff-path.sh` is covered through `check-handoff-path.py`. So the population of
hook-suites-with-no-runner is **one**, and it is this one — not a pre-existing repo-wide gap.

### R3 · the hook's cost claim is measured on a different question than the hook asks

`:19-20`: *"the script is silent on ~70% of python-touching commits (measured over 200 master
commits), so the cost is bounded."* That figure is the **per-commit** replay — the form I measured in
r1 and the form your six-miss experiment used. The hook runs `--diff "$base"` where `$base` is the
**branch's merge base**, so the window grows with every commit on the branch.

Measured on `71378cd3` over 120 master commits, using `sha~k..sha` as the proxy for a k-commit branch:

| window | commits | silent | max lines | commits printing ≥20 lines |
|---|---|---|---|---|
| **~1 — per-commit, what was measured** | 88 | **58 (65%)** | 30 | 3 |
| ~5 | 117 | 37 (31%) | 47 | 25 |
| **~10 — a normal branch here** | 120 | **18 (15%)** | **76** | **54 (45%)** |

By commit 10 of a branch the hook prints on 85% of commits, up to 76 lines, and **the same advisory
repeats on every commit until the members are all touched**. That is the "scrolled past, which is
worse than silence because it looks like coverage" failure the module docstring warns about,
arriving through the caller instead of the detector.

**The fix is one token, and it makes the caller ask the question the experiment measured:**
`--diff HEAD` at commit time is "what am I about to commit" — `_merge_base("HEAD")` resolves to
`HEAD`, and I confirmed it works through the existing entry point (sandbox, uncommitted edit:
`f(): you changed 1 of 2 exits  > :3  return 777`).

*Falsifier:* re-run the table with the hook's actual base and get 65% silence at window ~10.
*Siblings — searched.* `suggest-explainer.sh` uses a merge-base window too, but its subject is a
finished branch (`gh pr create`), so cumulative is the right question there. This is the only hook
whose question is per-change while its window is per-branch.

### R4 · the hook is unbounded on macOS, and the comment says the opposite

`:96-102` chooses `timeout 20`, else `gtimeout 20`, else **bare** — justified by
*"`peer-sites.py` already bounds its own `subprocess.run` at 30s."* Measured on `71378cd3`:

```
peer-sites.py subprocess.run call sites:
  :296  changed_lines  timeout=30   YES
  :315  _merge_base    timeout=30   YES
  :389  main --name-only            NO   <-- UNBOUNDED

this machine:  timeout: ABSENT    gtimeout: ABSENT   ->  _tmo=(), the bare path is live
```

The one call `main` makes **unconditionally, first, on every commit** is the unbounded one, so the
sentence justifying the bare fallback is false about the code. And `_merge_base`'s timeout is itself
unfalsified — removing it **survives 59/59**.

*Falsifier:* `timeout=30` on `:389`, plus a case that would redden its removal.
*Siblings — searched.* I enumerated every `subprocess.run` in the module by AST rather than by
grep: three call sites, one unbounded. No other module in the hook's path shells out.

---

## Medium

### R5 · `parse_hunks` invents line numbers on a multi-file diff — the M2 fix reintroduced its own named class

The fix's comment at `:209-214` says: *"a pure parser whose contract holds only for its current
caller is a landmine for the next one, and this one was split out precisely to be reusable."* The
body-walk it introduced holds only for **single-file** diffs, because `cursor` stays armed across the
file boundary and the next file's `+++ b/…` header is counted as an added line.

Measured against a **real** `git diff -U0 52010914 71378cd3 -- check-plan-code.py check-fixture-variation.py`:

```
parse_hunks(two-file diff)        -> 11 lines  [542…549, 552, 840, 3187]
union of the two single-file runs -> 10 lines  [542…549, 840, 3187]
SPURIOUS                          -> [552]
```

Minimal repro: `…@@ -1,0 +5,1 @@\n+first\ndiff --git a/y.py b/y.py\nindex …\n--- a/y.py\n+++ b/y.py\n@@ -1,0 +50,1 @@\n+second\n`
→ `[5, 8, 50]`, where **8** is the `+++ b/y.py` line.

The live path is single-file (`changed_lines` passes `-- path`), exactly as the old `-U3` issue was,
so nothing is wrong today — but this is strictly worse than what it replaced: `-U3` over-reported
*within* the right file, this invents a line number in file A that came from file B's header. And
Q2's fixture cannot see it, because the fake omits the preamble.

*Falsifier:* `parse_hunks(two_file_diff) == {5, 50}`.
*Siblings — searched.* Every line-shape the body-walk can meet after a hunk: `+++` (broken),
`---` (harmless, treated as old-side), `diff --git`/`index`/`new file mode` (each advances `cursor`
by one as "context"), `\ No newline at end of file` (advances). So the boundary problem is not one
line — **every preamble line of every file after the first** shifts the cursor.

### R6 · `main` crashes on a non-UTF-8 `.py`, and the comment claims otherwise

`:421` — *"`examined`, NOT `len(paths)` — deleted and unreadable files are skipped above"*. Only
deleted ones are: the guard is `if not f.is_file(): continue`, and `f.read_text()` at `:414` is
unguarded. Measured in a throwaway repo:

```
$ python3 scripts/peer-sites.py --diff master        # one edited .py + one non-UTF-8 .py
── ok.py ───  f(): you changed 1 of 2 exits   > :3  return 11
Traceback (most recent call last): … UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff
[rc=1]
```

**The hook handles it correctly** — rc=1 → `ℹ️ peer-sites: exited 1 — treat this as NOT CHECKED`.
That is the C2 fix working on a real crash, and worth recording as a pass. But a crash is not a
CANNOT RUN: a genuine advisory for `ok.py` was printed and then buried under a traceback, and the
docstring's *"always exits 0 on a well-formed run"* meets an ill-formed one through an exception
rather than through the `unchecked` path built for exactly this.

*Falsifier:* `errors="replace"` or a `try/except (UnicodeDecodeError, OSError)` that appends to
`unchecked`, plus a case.
*Siblings — searched.* Other unguarded filesystem reads in the module: `:434` (`--site` mode,
`f.read_text()`) has the same exposure and the same missing guard. Two sites, one fix.

### R7 (carried from r1, re-measured on `71378cd3`) · the `except` shape is inert, and the decision causing it has no case

`containers` records a handler as its head. Mutating it to the handler's full body **survives
59/59**, so the decision is unfalsifiable in either direction. Replayed over 200 master commits (362
python file-diffs), `except` produced **0** containers on every subject I have measured —
`52010914`, T1000, T1015, and `71378cd3` — while `exits` went 61 → 67. A handler fix lands in the
handler body; it never touches `except X:`.

### R8 (carried) · four r1 survivors still survive on `71378cd3`

Control 59/59, each mutation on a copy outside the repo:

```
SURVIVED  parse_hunks' zero-count guard removed        (dead since the body-walk: a deletion
                                                        hunk has no `+` lines either way)
SURVIVED  a malformed header leaves the cursor armed   ('@@ -1,0 +10,2 @@\n+a\n+b\n@@ garbage @@\n+c\n+d\n'
                                                        -> [10,11] shipped, [10,11,12,13] mutated)
SURVIVED  the `>` marker reverts to exact-line equality (header says "1 of 2", nothing marked)
SURVIVED  `_span`'s None fallback removed              (`end_lineno` is None on 0 of 128,887 nodes)
```

---

## Low

- **R9 · a staged-then-reverted edit is invisible at the moment of commit.** `git diff <base>`
  compares base to the **worktree**; `git commit` commits the **index**. Measured: index holds
  `return 777`, worktree reverted → `git diff $BASE --name-only` is empty while
  `git diff --cached $BASE` lists the file. Narrow (needs stage-then-revert), but the hook fires
  exactly where the two diverge. *Siblings:* brand-new staged `.py` files **are** seen — I checked.
- **R10 · `_wants_check`'s second pattern is broader than its first.** `*"git"*"commit"*` matches
  any command with `git` before `commit` anywhere — `git log --grep commit`, `git show HEAD; echo
  commit`. Your own case *"a commit named inside a MESSAGE still checks — a false positive costs a
  nudge"* accepts this deliberately, and I agree the cost is a nudge; but combined with R11 the
  false positive is not free.
- **R11 · 64 ms added to every Bash tool call.** Measured, 20 runs each: the hook on `ls -la`
  costs **69 ms** against a **6 ms** `bash -c true` baseline. The cost is a `python3` spawn at `:72`
  to parse the payload JSON, which happens **before** `_wants_check` filters. A `case "$payload" in
  *commit*)` pre-filter would skip the interpreter for everything that is not a commit.
- **R12 · stdout-only delivery — a class, not a new defect.** The hook uses plain stdout: 0 stderr
  redirects, 0 `systemMessage`/`hookSpecificOutput`, 0 `exit 2`. This repo's backlog #90 and #95 both
  record the cost of that channel — *"the gate fired every time and printed only to hook stdout,
  which CLAUDE.md states is 'shown to the assistant and not reliably to the user'"* and *"the gate's
  strength was never the problem; its CHANNEL was."* ⚠ **I am not filing this as introduced here:**
  `suggest-explainer.sh`, the precedent this hook explicitly cites, uses the identical `note()`
  stdout idiom. The blocking hooks use the structured channel because they block. So the honest
  finding is that **both advisory hooks share a channel the repo has twice recorded as weak**, and
  whether that matters depends on whether the reader is the assistant (who does see it) or the human
  (who may not). I could not observe the UI, so I am not claiming which.

---

## Verified green on `71378cd3`

| check | result |
|---|---|
| `peer-sites.py --self-test` | **59/59**, rc=0 |
| all 16 manifest entries | anchor ×1, red, via the named case — **0 problematic** |
| `check-fixture-variation.py` | rc=0 — 539 parameters / 52 files, 7 exempt (was 9); `main.argv` examined and satisfied |
| `check-selftest-counts.py` | rc=0 — 40 scripts, every count verified by running it |
| `check-docs.py` | rc=0 |
| `check-ratchet-contract.py` | rc=0 |
| `check-plan-code.py --self-test` | **128/128**, rc=0 |
| hook `--self-test` | 9/9, rc=0 (and see R1 for what that covers) |
| hook live-fired end to end | speaks on a real edit, and reports rc≠0 as NOT CHECKED on a real crash |

I did **not** re-run a full `--mutate .`; yours is in flight and the branch-specific half of it —
the 16 peer-sites entries — I verified directly above, which is the stronger measurement for this
subject.

## R-H2 · your divergence from the neighbours — **I attacked it and it holds. Keep it.**

You use two-dot against the *resolved* base rather than `{base}...HEAD`. Measured in a throwaway
repo with an uncommitted edit:

```
git diff master...            -> commit-to-commit; cannot see the worktree
git diff $MERGE_BASE          -> sees it
peer-sites --diff master      -> f(): you changed 1 of 2 exits   > :3  return 999
```

`A...B` is defined as `A..B` from the merge base **between two commits**; with `B` defaulting to
`HEAD` it is structurally blind to uncommitted work. A tool that runs before `git commit` and
advises on the edit in your hands must see the worktree, so three-dot would be silent on its own
subject. `check-dashboard-entry.py` and `check-review-decision.py` ask *what will this PR merge?*,
which is a question about commits — different question, correctly different answer. **The comment at
`:376-380` explaining this is one of the better things on the branch; it should survive verbatim.**

The only residue is R9, and it is an edge of the worktree choice rather than an argument against it.

---

## Verdict

**NOT CONVERGED**, and the boundary is clean: **the python is close to done, the bash is not.**

- `scripts/peer-sites.py` has one open design question — **what does it mean to touch a member?**
  `exits` says the whole statement, `except` says the head, `branches` says the test for three arms
  and the whole first statement for the fourth. Q1, R7 and backlog #131 are that one question from
  three sides, and it wants a single decision applied to all three shapes with a case per shape.
  Everything else there is R5, R6 and four unfalsified guards.
- `.claude/hooks/peer-sites-advisory.sh` is where the round's weight is. R1 and R2 together mean the
  file built to stop *fix the instance, miss the sibling* currently ships a suite that covers one
  function, run by nobody, with the author's two live-fired lessons written down as prose. R3 means
  it asks a measurably different question from the one the design was justified by, and R4 means its
  own timeout reasoning does not match the code it defends.

None of that argues against the branch. The r1 fixes were real and I could not find one that was
merely made green — C1 in particular is clean. What the round found is that the fix for "no
mechanism" introduced a second, unmeasured mechanism, and it deserves the same treatment the first
one got.
