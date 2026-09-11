# harness-progress-output — round 1, Claude half

**Subject.** Branch `harness-progress-output`, stacked on `backlog-106-compose-idempotence` (PR #288).
`git log --oneline origin/master..HEAD` returns seven commits; six (`370144b1`..`28de2088`) belong to
#288 and are out of scope. **Reviewed: `e017b163` alone**, "The mutation harness says where it is,
instead of going silent for minutes". `git status --porcelain` empty.
`git diff backlog-106-compose-idempotence...HEAD --stat` = 3 files, +172/-9:
`docs/dashboard-entries.md`, `scripts/check-plan-code.py`, `scripts/mutations/check-plan-code.json`.

**Verdict: NOT CONVERGED.** One Blocking, two High, two Medium, two Low.

Every premise below was produced by running something, over a proven-green control. Working copies
were staged under `/tmp` with the full `HARNESS_TREE` symlinked; `~/explainers/` was never touched.

---

## Blocking

### B1 — The case that guards the nested-run hazard cannot fail. It is the sixth instance.

The brief names the nested-run leak as "⛔ the real risk", and `:2256-2258` says so in the code. The
case that defends it is `:2279-2281`:

```python
_quiet: list = []
run_mutations(_dpp, _pm, {"p.py"})
case("...and says NOTHING when no caller asked", _quiet, [])
```

`_quiet` is bound to `[]` at `:2279`, the call at `:2280` **is passed no reporter and its return value
is discarded**, and `:2281` asserts that the untouched list is empty. Nothing in the program can ever
append to it. Compare `:2275-2276`, where `_seen` is wired through `progress=lambda *a: _seen.append(a)` —
the sibling case is wired, this one is not.

**Measured, over a green control.** Staged copy, full `HARNESS_TREE`, control `105/105 passed`. Then the
exact defect the case names — `run_mutations` reporting when no caller asked:

```python
if progress is not None:
    progress(position, len(muts), name)
else:                                             # the mutation
    stderr_progress(position, len(muts), name)
```

Result: `rc=0`, **`105/105 passed`**. The defect is real and visible — the suite's own stderr grows
542 B → 766 B, i.e. nested runs now leak progress unconditionally — and the suite does not notice.
The silence case did not fire.

The count was itself the tell: this commit adds **four** cases and **three** manifest entries
(`EXPECTED_MUTATIONS` 431→434 at `:589`, self-test 101→105 at `:5`). The case with no mutation is
precisely the vacuous one. A mutation could not be written for it because there is no production edit
it can detect.

**Fix, verified both directions.** Capture the stream instead of an unwired list:

```python
_qe = io.StringIO()
with contextlib.redirect_stderr(_qe):
    run_mutations(_dpp, _pm, {"p.py"})
case("...and says NOTHING when no caller asked", _qe.getvalue(), "")
```

- applied to clean code → `105/105 passed` (still green);
- applied with the defect → `rc=1`, `104/105`, red **via the named case**:
  `[FAIL] ...and says NOTHING when no caller asked: got '[1/2] m1\n[2/2] m2\n' want ''`.

`contextlib.redirect_stderr` is sound here: `stderr_progress` resolves `sys.stderr` at call time
(`:1195`), and child stderr is captured by `subprocess` inside `run_suite`, so only the parent's own
writes are seen. It also needs a manifest entry, making it 4 cases / 4 mutations.

---

## High

### H1 — The harness's own control-failure diagnostic now contains none of the failure.

`run_suite:396` returns `(r.stdout + r.stderr).strip()`. That merge is deliberate and one day old —
`:1283-1288` (round 1 F7, 2026-09-09) records that dropping the stderr half survived at 78/78 and was
restored because "every CANNOT RUN message prints an `out[-400:]` tail, and a control that dies on a
TRACEBACK says so only on stderr".

This commit puts 542 B of progress into that same stream, because the two control loops at `:877` and
`:905` call `stderr_progress` **unconditionally**, and `_self_test` drives `mutate_delivered` fourteen
times (`:1797, 1808, 1816, 1834, 1845, 1874, 1888, 1900, 1921, 2024, 2047, 2064`, plus `main(["--mutate"…])`
at `:1955, 1980`).

`case()` writes `[FAIL]` to **stdout**; progress goes to **stderr**; `out = stdout + stderr`. So failures
are pushed out of the 400-char window that `:885` and `:916` print.

**A/B, same environment, same class of break:**

| | stderr | `ev_files["tail"]` (`:879`) | `[FAIL]` in `out[-400:]` |
|---|---|---|---|
| base `backlog-106…` | **0 B** | `'97/101 passed'` | **yes** |
| HEAD | **542 B / 19 lines** | `'[1/1] re-control scripts/thing.py'` | **no** |

On HEAD the entire diagnostic a reviewer would see is nineteen lines of `[1/1] control scripts/thing.py`
and zero characters of the failure — `"[FAIL]" in out[-400:]` is `False`, while `"[FAIL]" in out` is
`True`. Clean-worktree baseline with `HARNESS_TREE` staged: base `rc=0, 101/101, stdout 16 B, stderr 0 B`.

This bites exactly when the control is red, which is the only moment the message exists for, and it
undoes F7 for the one target that matters most — the harness itself. Attribution is **not** affected:
`parse_fail_names` requires a line *starting* with `[FAIL] ` (`:1214`), and progress lines are `[1/1] …`,
so they cannot be misread as case names. Verified.

### H2 — The two control-loop call sites have no case and no mutation.

`:877` and `:905` are the half the dashboard entry advertises ("Both control phases and the mutation
loop report"). **Measured:** control `105/105`; delete `:877` → `105/105 passed`; delete `:905` as well →
`105/105 passed`. The whole control-phase feature is deletable with nothing going red. The three new
manifest entries cover the stream, the `run_mutations` wiring, and the format — none covers these.

H1 and H2 have one fix. Give `mutate_delivered` the same optional reporter `run_mutations` already has,
and let the top-level caller supply it:

```python
def mutate_delivered(root: pathlib.Path, progress=None) -> ...
    ...
    if progress is not None:
        progress(position, len(targets), f"control {name}")
    ...
    ok, ... = run_mutations(d, muts, set(targets), progress=progress)
# and at :2445
ok, report, verdict = mutate_delivered(mroot, progress=stderr_progress)
```

**Measured:** suite stays `105/105 passed`, and nested stderr falls 542 B → 228 B. The residue is the
two self-test cases that drive `main(["--mutate"…])` at `:1955`/`:1980`; both redirect **stdout only**
(`:1953`, `:1978`), so wrapping them in `redirect_stderr` takes it to zero. That also gives `:877`/`:905`
a falsifiable surface to hang a case and a mutation on.

---

## Medium

### M1 — Label text now enters the stream whose substring decides "green". Latent, not live.

`control_is_green:314` is `rc == 0 and "passed" in out`, and `out` now carries author-written labels.
Across all 434 manifest names, **two contain `"passed"`**:
`'unparseable source is passed instead of scanned raw'` (`check-plan-code.json`) and
`'the `passed` requirement is dropped, so any ratio counts'` (`check-selftest-counts.json`).

**Not reachable today**, and I want that stated rather than dressed up: the labels a *nested* run emits
are the self-test's own fixtures (`control scripts/thing.py`, `value is two`, `anchor absent one/two`),
none containing `"passed"`; and the documented rc-0-with-no-output route (`:304-307`, a script with no
`__main__`) emits no progress either, because nothing executes. The finding is that a greenness
predicate which substring-matches one word now reads a stream carrying arbitrary prose, so the
separation is held by a coincidence of naming rather than by anything. The H1/H2 fix removes it
entirely, which is a further reason to prefer that fix over patching the case alone.

### M2 — The label is unbounded, and it compounds H1.

Measured over all 434 names: longest label **232 chars**, worst-case progress line **242 chars**;
**81 labels exceed 100 chars**, 127 exceed 80. One such line consumes ~60% of the 400-char diagnostic
window in H1, and wraps to three lines on an 80-column terminal — which degrades the one property the
feature is for, a line that visibly stops advancing. No label contains a newline and none starts with
`[FAIL] ` (one contains it mid-string, harmless given `parse_fail_names`' start-anchor). Suggest
truncating the label in `progress_line` to a fixed width; that is also a pure, easily-cased change.

---

## Low

### L1 — `flush=True` is not load-bearing, and the docstring states the opposite as fact.

`:1192-1194` says "without `flush`, a pipe buffers this into oblivion and the whole point is lost".
**Measured on this machine (Python 3.14.4):** `sys.stderr.line_buffering` is `True` when piped to a file
and when captured by a child under `capture_output=True` — stderr has been line-buffered by default
since 3.9. Constructing the case the docstring describes: two `print(..., file=sys.stderr)` calls
*without* flush followed by `SIGKILL` — **both lines survived**, identically to the flushed variant.

Keeping `flush=True` is harmless and I would keep it. The defect is the claim: this branch's own
dashboard entry makes a virtue of deleting an unmeasured "~25 minutes", and the adjacent docstring
asserts an unmeasured buffering mechanism in the same breath. Reword to "belt-and-braces; stderr is
line-buffered by default since 3.9" or measure it.

### L2 — `:64`'s guarantee is now false under `2>&1`.

"The final line names the mode, so a CI log cannot be read as the wrong subject." Under
`--mutate . 2>&1`, the final line is a progress line. Nothing in-repo does this — `ci.yml:359` runs the
command bare and reads only the exit code, and no `.claude/hooks/` file references `check-plan-code`
(grepped) — so no consumer breaks today. But the sentence is a stated invariant and is no longer true
for a reader who merges the streams, which is the ordinary way to read a CI log. Either qualify it or
have the tally re-emit on stderr at exit.

---

## Attack-list answers

1. **The stream.** No path puts progress on stdout: `:1195` is the only writer of `progress_line` to a
   stream and it is unconditionally `file=sys.stderr`. `--mutate .` stdout stays 128 B. CI (`ci.yml:359`)
   is exit-code only; no hook consumes it. `2>&1` → L2 only.
2. **The nested-run hazard.** Confirmed and worse than framed: the author's mitigation covers
   `run_mutations` but not `mutate_delivered`, whose two calls are unconditional. Self-test stderr
   0 B → 542 B. Consequence is H1 (diagnostic), not a wrong verdict — `control_is_green` still sees
   `"passed"` on stdout, and attribution is start-anchored. Latent fail-open in M1.
3. **`flush=True`.** Cargo. L1 — I could not construct a case where removing it loses output.
4. **Coverage.** All three manifest entries verified red **via the named case** by applying the edits
   directly (`progress is written to stdout…` → `progress goes to stderr…`; `the progress reporter is
   accepted and never called` → `the caller is told once per mutation…`; `…position without its total` →
   `a progress line states position…`). The sixth instance of the recurring defect is B1, and the
   uncovered surface is H2.
5. **The label.** M2 — 232 chars max, 81 over 100.
6. **What the author did not measure.** The measurement taken (outer run: stdout 128 B unchanged,
   510 stderr lines) is structurally incapable of seeing the hazard flagged as the main risk — the outer
   run's *stdout* is unaffected by a nested run's *stderr* by construction. Not measured: the self-test's
   own stderr (0 → 542 B), the `out[-400:]` window, `ev_files["tail"]`, whether `flush` was load-bearing,
   and label lengths. The arithmetic that was quoted is correct: 38 + 434 + 38 = 510, and 434 manifest
   names match `sum(EXPECTED_MUTATIONS.values())`.

## Not findings

The design call — position over a spinner — is right and the reasoning at `:1165-1168` holds. Declining
to quote a duration (`:1175-1181`) is correct and well argued. `progress_line` being pure and separate
from `stderr_progress` is the right seam. The stacking note in the dashboard entry is accurate.

**The single most important thing to fix: B1** — wire `_quiet` to the stream so the case defending the
nested-run contract can fail, then fix H1/H2 with the `mutate_delivered(progress=…)` change, which also
closes M1.
