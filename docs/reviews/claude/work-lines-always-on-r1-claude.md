# work-lines-always-on — round 1 — Claude half

Reviewed range: `3a2795d1..0197b844` (branch `feat/work-lines-page`, PR #384).

Method: read the full diff of `begin-plan.py`, `check-plan-progress.py`, `explainer-serve.py`,
`gen-work-lines.py` and the mutation manifests, plus the Stop-hook wrapper
`.claude/hooks/block-idle-stop.sh`. Every scenario below was run in a temp copy of `scripts/`
under a temp `git init` repo
(`<scratchpad>/r1/repo`), with `HOME` pointed at a temp dir and a fake `gh` first on `PATH`.
`~/explainers/work-lines.html` was checked before and after: mtime `Oct 22 12:11` both times,
so it was not touched. All four `--self-test`s pass (104/104, 54/54, 40/40, 203/203) with
`HOME` redirected. Real `gh` was used read-only, only to check the output shape and how long PRs stay open.

---

## F1 — Major — an open PR attaches UNRELATED later work to the finished plan

`scripts/begin-plan.py` `_parent_from_last_finished` (the `return slug if state == "open" else STARTED` line)

**Input.** A plan finishes on `feat/a` and its PR opens. Merging is a human gate here, so that
PR stays open for hours or days. Real `gh`, last 40 PRs: 0.2h to 80.8h open, and six PRs are
open right now (#364, #371, #376 have been open for days). During that window the coordinator
starts something unrelated, with nothing armed.

**What happens (executed).**
```
$ git checkout master
$ GH_MODE=open python3 scripts/begin-plan.py unrelated-next-week "One|d|w"
> **Line:** _(no objective recorded)_ `plan-a` → `unrelated-next-week`
$ grep parent .claude/plans/unrelated-next-week.md
<!-- parent: plan-a -->
```
The only evidence used is "some PR for the recorded branch is open". That does not tell apart
"this side job branched off plan-a while its PR was in CI", which is the case the feature is for,
from "plan-a's PR is waiting for the owner to merge and I started the next unrelated thing". In
this repo the second case is the common one. Nothing compares the branch being armed on with
the recorded one, and nothing bounds `finished:` by time. `.claude/last-plan` is never deleted,
and it is overwritten only when the next plan is fully ticked, so each new plan becomes the child
of the previous one for as long as PRs stay open. The result is one long invented chain, which
is the "wrong, worse than absent" outcome the docstring says it never produces. There is also no
escape: `main`'s argparse has no flag to declare a fresh line (`parent` is "derived …
and never passed"), so a human who sees the wrong `Line:` cannot fix it.

Knock-on (deterministic from `work_line`, not run at scale): the banner's `Line:` row joins every
chain member with no cap. If the chain grows with every plan, so does every banner.

**Suggested fix.** Require evidence about the CURRENT moment as well as the old PR. For example:
continue only when `finished:` is within a short window (the "armed while the PR was in CI" case
is minutes, not days), or when the current branch is the recorded branch or was created from its
tip (`git merge-base --is-ancestor`). Either way, add a `--fresh` / `--continues <slug>`
override, and cap the `Line:` row (root … last k).

## F2 — Major — the branch is read when the sentinel CLEARS, not the branch the plan ran on

`scripts/check-plan-progress.py` `run_decide`: `record_last_plan(..., branch=current_branch(ROOT))`;
`scripts/begin-plan.py` `cmd_finish`: `branch=pp.current_branch(ROOT)`

**Input.** The coordinator ticks the last step, then switches branch in the same turn, for
example `git checkout -b` for the next job or `git checkout master`. The Stop hook only clears at
the end of the turn.

**What happens (executed).**
```
$ python3 scripts/begin-plan.py plan-a "One|d|w"; python3 scripts/begin-plan.py --tick   # on feat/a
$ git checkout -q -b feat/b
$ echo '{}' | python3 scripts/check-plan-progress.py --decide
✅ every step in `.claude/plans/plan-a.md` is ticked (1/1). Clearing .claude/executing-plan.
$ cat .claude/last-plan
plan: .claude/plans/plan-a.md
branch: feat/b
```
`plan-a` is now tied to `feat/b`'s PR state. If `feat/b` has an open PR, later plans become
`plan-a`'s children because of some other PR (wrong lineage). If it is `master`, they get
"no PR exists" (absent lineage). `render_sentinel` records no branch when the plan is armed, so
the plan's real branch is never written down anywhere.

**Suggested fix.** Write `branch:` into the sentinel in `_arm`/`render_sentinel`, which is the
moment the plan starts on a known branch. Have `record_last_plan` copy it from `sentinel_text`
rather than ask git at clear time. Fall back to `current_branch` only for a sentinel that
predates the field.

## F3 — Major — no test covers the branch wiring; three mutations that turn Option A off all survive

`scripts/check-plan-progress.py` `current_branch`, `run_decide`; `scripts/begin-plan.py` `cmd_finish`

The wiring cases build their root with `tempfile.TemporaryDirectory()`, and that directory is not
a git repo. So `current_branch(ROOT)` is `None` at both clear sites, and every record those cases
produce has no branch. The unmutated suite already says so on stderr:
`⚠ no parent recorded: the last finished plan `parked` has no branch on record …`. The one
`current_branch` case only asserts `None` outside a repo. I applied each mutation below to a temp
copy and ran both suites:

| mutation | check-plan-progress | begin-plan |
|---|---|---|
| `run_decide`: `branch=current_branch(ROOT)` → `branch=None` | **54/54 pass** | **104/104 pass** |
| `current_branch`: `return b if … else None` → `return None` | **54/54 pass** | **104/104 pass** |
| `cmd_finish`: `branch=pp.current_branch(ROOT))` → `branch=None)` | — | **104/104 pass** |

In production each of these turns Option A off completely. Every record would have no branch, so
every fresh plan would get "no branch on record" and no parent. The suites stay green. The cases
that do check `branch:` (`render_last_plan`, and `record_last_plan` called directly with
`branch="feat/one"`) get the value from the fixture. The code that supplies the value at the call
sites is never exercised. No manifest entry covers it either: grepping
`scripts/mutations/{check-plan-progress,begin-plan}.json` for `branch` finds deletions of the whole
`record_last_plan` call, but nothing that keeps the call and drops its branch.

**Suggested fix.** `git init` the temp root in both suites and check out a named branch, with a
different name in each suite so neither can pass on a constant. Assert that the recorded `branch:`
equals that name at both clear sites. Add a positive `current_branch` case, and add the three rows
above to the manifests. If F2's fix lands, assert instead that the branch comes from the sentinel
and not from HEAD at clear time: arm on `x`, switch to `y`, clear, expect `x`.

## F4 — Minor — one record with no usable answer stops later fresh plans from recording `-`, with no end

`scripts/begin-plan.py` `_parent_from_last_finished`. Its `none`, no-branch and `_plan_slug` arms
all return `None`.

**Input.** The last fully-ticked plan finished on `master` (no PR). The same happens for a
detached HEAD, or a `--plan docs/…` plan outside `.claude/plans/`.

**What happens (executed).** Three fresh plans armed after that, each `--finish`ed half-done:
```
⚠ no parent recorded: no PR exists for branch `master`, so whether this continues `timing` cannot be told.
0      (no parent: line in fresh-1.md)
… identical for fresh-2, fresh-3; .claude/last-plan still names timing.md
```
On the page these show as "no parent recorded, and no stated objective". Before this range they
would have been `-` (started a line). The record never expires, and `--finish` on a half-done
plan never replaces it. So one PR-less finish makes every later fresh start "unknown", until some
plan is fully ticked on a branch that has a PR.

**Suggested fix.** Once the record has been asked about and gave no usable answer (`none`, no
branch, not a plan file), delete or mark it consumed and print the stderr line once. Or let it
expire using `finished:` (which also helps with F1).

## F5 — Minor — the Stop path's "ONE stderr line says so" reaches nobody

`scripts/check-plan-progress.py` `run_decide` → `refresh_work_lines` / `record_last_plan` warnings;
`.claude/hooks/block-idle-stop.sh` exit arithmetic

**What happens.** Executed: with `~/explainers` made a file, `--decide` returns `rc=0`
and prints `⚠ work-lines page NOT rebuilt — FileExistsError …` on stderr. From the
wrapper's code (not run end to end): `PROGRESS_RC=0`, and the final `exit 1` only fires on an
observer rc or `PROGRESS_RC == 3`. The wrapper's own header says `exit 0 — allows the stop
silently`. So in the usual quiet stop, both the "page NOT rebuilt" line and the "was NOT
recorded as the last plan" line are dropped. The docstring says "every one is still SAID", which
is only true on the `begin-plan.py` path. The verdict itself does not change, which is correct.

**Suggested fix.** Return WARN (3) from `run_decide` when either side effect failed, or reword the
docstring to say this path is silent.

## F6 — Minor — every fresh `begin` makes a network call that can block for 30s

`scripts/begin-plan.py` `gh_pr_line_state` (`timeout=30`)

`.claude/last-plan` is never deleted, so after the first finished plan every `begin` with nothing
armed calls `gh`. Executed, with a fake `gh` that hangs:
`real 0m30.241s`, ending in `⚠ no parent recorded: … could not be decided — `gh` could not be
run (TimeoutExpired)`. The result is correct (no marker, reason given), but 30s is a long block
on a command run before every job. **Fix:** a 5–10s timeout. F4's "consume the record" would also
remove the call after a final answer (`ended`/`none`).

---

## Checked and found sound

- **Argument injection / special branch names.** `gh` gets an argv list (`shell=False`). git
  refuses `a:b` and `-x` as branch names (`git check-ref-format --branch` → refused), so neither
  can reach `--head`.
- **Real `gh` output shape.** It matches the `_gh_world` fake: `[{"state":"OPEN"}]` for this
  branch, `[]` for `master`, `[]` with rc 0 for a branch that does not exist.
- **Self-parent.** Not reachable. `cmd_begin` keeps an existing file's parent. A deleted-then-re-armed
  slug fails `_plan_slug`'s `is_file()` check, because `_derive_parent` runs before the write.
- **Rebuild cost.** No `gh` in the rebuild. With 126 plans, `--tick` takes 0.32s wall and
  `--banner` 0.12s. A missing `~/explainers` is created, and an unwritable one is reported (F5).
  Neither changes the rc.
- **Self-tests.** No self-test wrote the real `~/explainers/work-lines.html` (mtime unchanged
  across all four runs with `HOME` redirected). The `begin-plan` cases that reach `main()`
  redirect `WORK_LINES_OUT`.
- **Stop verdict.** Allow/deny, rc and stdout message are unchanged in every path I traced. The
  new calls run only on `unticked == 0`, and both catch their own failures. That leaves one
  uncaught route, a non-OSError such as `ValueError` from `read_text`, which needs a hand-made
  sentinel.
- **`explainer-serve.py`.** `STALE_EXEMPT` is used only by the self-test, which keeps the
  empty-list set equal to it, so it is not a hole. `/_stale` answers `fresh` through the existing
  `not sources` arm. The Refresh button runs `gen-work-lines.py` with no arguments, which writes
  `Path.home()/explainers`, the directory the server serves.
- **`work_line`.** Cycle cut, missing parent, plan outside `.claude/plans/` and truncation all
  behave as their cases claim. Slugs are normalised, so they cannot break the backticks.

VERDICT: NOT CONVERGED
