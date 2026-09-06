# Claude adversarial review — banner guard inverse (#95), round 1

**Subject:** `docs/superpowers/specs/2026-09-04-banner-guard-inverse-design.md` (v1, 2026-09-04)
**Reviewer:** Claude half, independent. The Codex half's file exists at
`docs/reviews/coordinator/banner-guard-inverse-r1-codex.md` and was **deliberately not read**.

**Method.** Every quoted line number and behavioural claim was re-read in the file it names. The
predicate was then **executed** against real transcripts: I imported `check-banner-armed.py` and used
its own `_is_tool_result`, `_text_blocks` and `highest_banner` to segment
`~/.claude/projects/-Users-kujinlee-.../12fc2cc2-f073-4ca3-b682-fe9869deae0d.jsonl` — the long
2026-09-04 session in which the user reported the banner lapse, and in which
`.claude/plans/comprehensibility-slice-b.md` was armed — into the guard's own windows, and evaluated
the proposed `edited` term over each. Simulation assumption, stated because it is load-bearing:
**the plan is treated as armed with unticked steps for the whole session.** It was not armed for the
whole session, so the counts below bound the shape, not the exact production rate.

**Count: 3 Blocking, 4 High, 4 Medium, 5 Low.**

---

## BLOCKING

### B1 — The new WARN branch is nearly unreachable in production, and the states where it *is* reachable are the legitimate ones. The spec never analyses the hook's sequencing.

**Claim.** `decide()` is not called on most stops. `block-idle-stop.sh:39-41` runs
`check-plan-progress.py` first and `exit 2`s on its non-zero, so `check-banner-armed.py` at `:54`
**never executes** whenever the plan guard blocks — which is exactly the state the new predicate is
written for.

**Evidence.**

```bash
# .claude/hooks/block-idle-stop.sh:39-41
if ! python3 "$REPO_ROOT/scripts/check-plan-progress.py" "${ARGS[@]}"; then
    exit 2
fi
```

`check-plan-progress.decide()` returns `BLOCK` whenever a plan is armed with unticked steps
(`check-plan-progress.py:133`), so enumerate the ways it can return `ALLOW` and reach line 54:

| `check-plan-progress` ALLOW path | State `check-banner-armed._armed()` then sees |
|---|---|
| no sentinel (`:97-98`) | `armed = False` → new branch cannot fire |
| **`paused:` in the sentinel (`:100-101`)** | **`armed = True`, `unticked > 0` → the new branch fires** |
| `unticked == 0` (`:121-125`), and `run_decide:180-182` **unlinks the sentinel on that same stop** | `armed = False` → cannot fire |
| **anti-nag: `stop_hook_active` and the unticked count did not fall (`:130-131`)** | **`armed = True`, `unticked > 0` → fires** |

So the reachable firing set is exactly: **(a) a paused plan, and (b) a hook-continuation turn that
ticked nothing.** (a) is the documented escape (see B2). (b) is, by the anti-nag's own definition, a
turn where blocking stopped producing progress.

The plain case the spec is written for — "armed, unticked > 0, work done, no banner, ordinary stop" —
**cannot reach the new code**, because the sibling guard blocks first and the hook exits.

**Corollary: F3 is unreachable in production**, for a reason unrelated to the branch. `armed ·
unticked == 0` cannot be observed by `check-banner-armed._armed()` at all, because
`check-plan-progress.run_decide:180-182` has already deleted `.claude/executing-plan` by the time
line 54 runs.

**Smallest fix.** Add a reachability section to the spec that enumerates the table above, and pick
one: move the banner check **above** the `check-plan-progress` call in `block-idle-stop.sh` (it is
warn-only and cannot block, so ordering is free), or scope the predicate deliberately to the two
reachable states and say so. Either way the falsifier table needs a case that exercises the *hook*,
not only `decide()` — every F1–F7 is a unit call on a pure function that production may never invoke.

---

### B2 — `armed` ignores `paused:`, so the guard's principal firing condition is the escape hatch this repo documented four weeks of pain into.

**Claim.** `check-banner-armed._armed()` and `check-plan-progress.decide()` disagree about what
"armed" means, and the spec inherits the wrong one.

**Evidence.**

```python
# scripts/check-banner-armed.py:180-188
def _armed() -> bool:
    ...
    for line in text.splitlines():
        if line.split(":", 1)[0].strip() == "plan" and line.split(":", 1)[-1].strip():
            return True
```

It reads only the `plan:` key. Contrast `check-plan-progress.py:99-101`:

```python
    fields = parse_sentinel(sentinel_text)
    if "paused" in fields:
        return ALLOW, "", None
```

`begin-plan.py:56-61` states what `--pause` is *for*: *"the one that actually arises most — is being
legitimately BLOCKED ON IN-FLIGHT WORK: a dispatched review, a CI run, a background task"*, and
`check-plan-progress.py:28-36` records it firing three times in one session (backlog #94, measured
2026-09-04).

Combine with B1: a paused plan is one of only two states that reach the new code at all. So the
first production firing of this warning is overwhelmingly likely to be *"you paused the plan to wait
for a dispatched Codex reviewer, then folded its findings into a file — where is your banner?"*.
That is the cry-wolf outcome the backlog row says must not ship.

**Smallest fix.** `_armed()` returns `False` when `parse_sentinel` yields a `paused` key — borrowing
`parse_sentinel` from `check-plan-progress` alongside `count_steps`, since the spec already commits
to that import. Add falsifier **F8: armed but `paused:` → QUIET**.

---

### B3 — No firing of the new branch is ever logged, which voids §6's entire justification for shipping without suppression.

**Claim.** §6 asserts *"Every firing is appended to `.claude/banner-warnings.log`. Volume in that log
is what would later justify suppression."* Under the design as written, the new branch logs nothing,
and §7's bookkeeping list does not mention fixing it.

**Evidence.** The log write is gated on a banner existing — and the new case is defined by *zero*
banners:

```python
# scripts/check-banner-armed.py:207-214
    if code == WARN:
        banner = highest_banner(texts or [])
        if banner:                      # ← always None in the new case, by construction
            ...
                    fh.write(log_line(banner[0], banner[1], when, str(...)))
```

`log_line`'s signature (`:173-175`) takes `step: int, total: int` — there is no shape for a
banner-less record, and the spec never proposes one. So the argument "we do not need anti-nag because
the log gives us a number" is self-defeating for precisely the warning it is arguing about; the log
would show 0 firings of the new class forever, and a future reader would conclude it never fires.

**Smallest fix.** Widen `log_line` to take a reason (`"unarmed"` / `"unbannered"`) and drop the
`if banner:` gate; add it to §7's bookkeeping list. Note this also changes the log's column grammar,
so any existing reader of that file must be checked.

---

## HIGH

### H1 — The window means something different for tool use than the spec assumes, because non-user records reset it — including the sibling guard's own block message. MEASURED.

**Claim.** `assistant_texts_since_last_user` treats *any* `type == "user"` record that is not a
`tool_result` as a turn boundary (`:93-98`). Real transcripts contain several kinds of such records
that are not user messages, and each one truncates the window — dropping banners while leaving later
edits inside. For text alone this only under-fires; for the new predicate it **manufactures the exact
warn condition**.

**Evidence — measured on the 2026-09-04 session.** Six non-user boundaries in one session:

```
[6]    META    '<local-command-caveat>Caveat: The messages below were generated by the user…'
[807]  META    '[{"type":"text","text":"Base directory for this skill: …/.claude/skills/dashboard…'
[1008] system  '<task-notification>\n<task-id>b5ncda6cy</task-id>…'          ← background task finished
[1130] META    '[{"type":"text","text":"Base directory for this skill: …superpowers/…/writing-plans…'
[1707] system  '<task-notification>\n<task-id>b0q0w8tqy</task-id>…'
[1988] META    'Stop hook feedback:\n[bash .claude/hooks/block-idle-stop.sh]: ⛔ DO NOT STOP — 2 of 4
                steps are unticked in `.claude/plans/comprehensibility-slice-b.md`.'
       last banner emitted before it: record 1916, `STEP 2 of 4`
```

Across 20 recent transcripts: 622 `user` records are tool results; **15 are `isMeta:true`, 6 are
`promptSource:"system"`, 9 are neither** — 30 non-tool-result `user` records that are not the human
typing.

Boundary **[1988] is the killer**, and it is not incidental — it is *causally coupled* to B1. The
only non-paused way to reach the new code is the anti-nag continuation, and that continuation's
window **begins at the block message**, so the `STEP 2 of 4` banner emitted 72 records earlier for
the step still in progress is out of window by construction. The guard would warn "no banner" at the
one moment it can run, about a turn that emitted a banner.

Simulating the `edited` term over all 23 windows of that session: **5 windows would WARN**, and 1 of
the 5 is a `META`-boundary artefact (the window was cut by a skill injection; the edit was a single
touch of `docs/superpowers/plans/2026-09-04-comprehensibility-bundle.md`).

**Smallest fix.** `records_since_last_user` must skip boundaries where `isMeta` is true or
`promptSource` is `"system"`/`"sdk"`. That is a change to the *shared* windowing helper, so §4.3's
"one windowing implementation" is right but the helper as it stands is wrong — and the spec presents
it as merely relocated, not as needing repair. Falsifiers must include a `Stop hook feedback` record
and a `<task-notification>` record mid-window.

### H2 — Subagent edits are in a different transcript file, so the coordinator turns that do most of this project's work register as `edited = False`. §8 does not mention it.

**Claim.** The spec's §8 admits the `Bash` hole and omits the larger one.

**Evidence (negative claim, established by search not by reading).** Across all 508 transcripts for
this project, `grep -c '"isSidechain":true'` returns **0**; every one of the 118,389 occurrences of
that key is `false`. Subagent work lives in its own session file, so a coordinator turn that
dispatches five reviewers and folds nothing emits `Agent`/`Bash` tool uses only. `docs/dev-process.md`
sets `superpowers:subagent-driven-development` as the **Phase 3 execution default**, so this is the
project's normal mode, not an edge case.

Same session, tool mix in the coordinator's own records over 12 recent transcripts: **Bash 207, Edit
52, Read 50, Write 4**. In the 23-window simulation, **6 windows did work through Bash only** (two of
them beginning at a `<task-notification>` boundary) and would stay QUIET.

**Smallest fix.** §8 gains a bullet naming subagent dispatch explicitly, with the measurement above.
If the intent is to cover it, `Agent`/`Task` tool uses are a candidate signal — but that is a design
change, not a documentation one, and should be decided rather than absorbed.

### H3 — `unticked > 0` disagrees with `check-plan-progress` on the zero-checkbox case, and disagrees in the fail-open direction.

**Claim.** The spec imports `count_steps` to avoid drift, then derives a predicate that contradicts
the importer.

**Evidence.** `count_steps` on a plan with no checkboxes returns `(0, 0)` (`check-plan-progress.py:71-74`),
so `unticked = 0` and §4.1's `if armed and unticked and edited` is **False → QUIET**. The owner of
that rule treats the same input as a failure to measure:

```python
# scripts/check-plan-progress.py:113-118
    if total == 0:
        return BLOCK, ("CANNOT RUN: parsed ZERO step checkboxes from `{plan}`. Either the plan's
        shape changed or this parser is broken. TREAT THIS AS NOT RUN — do not read the absence of
        a warning as 'no work left'.")
```

Importing the function while re-deriving a *different* meaning from its return value reintroduces the
drift the import was chosen to prevent — the shared-function-holding-half-a-contract shape, not the
two-copies shape.

**Smallest fix.** Pass `(done, total)` rather than `unticked`, and map `total == 0` to `CANNOT_RUN`
alongside the unreadable-plan case. Add falsifier **F9: armed · plan parses to zero checkboxes →
CANNOT RUN**.

### H4 — The `CANNOT RUN` branch is nested inside `if banner is None`, so the guard's ability to report its own blindness depends on an unrelated condition.

**Claim.** §4.1 places the unreadable-plan check inside the no-banner arm. An armed sentinel naming a
missing plan, in a turn that *did* emit a banner, falls through to the untouched old branches and
returns QUIET or WARN — never `CANNOT RUN`.

**Evidence.** §4.1 as written:

```python
banner = highest_banner(texts)
if banner is None:
    if armed and unticked is None:
        return CANNOT_RUN, ...
```

`CLAUDE.md`: *"'Cannot run' is a FAILURE, never a pass."* Whether the check can reach what it measures
is a property of the sentinel and the plan file, not of whether the assistant happened to type a
heading. §4.4 argues the failure posture is right and then places it where it is conditional.

**Smallest fix.** Hoist the `armed and unticked is None` test above `banner = highest_banner(texts)`.
Falsifier: same inputs as F6 but **with** a banner present, still `CANNOT RUN`.

---

## MEDIUM

### M1 — Five of the seven falsifiers pass against the UNFIXED code. The table reads as seven tests of the fix; two are.

**Claim.** §5 says *"None of these exist today"* — true, and it invites the reading that all seven
discriminate. Run each against the current `decide()`:

| # | Against today's code | Why |
|---|---|---|
| F1 | **FAILS** (expects WARN, gets QUIET) | the load-bearing one |
| F2 | passes | `:149` returns QUIET for any banner-less turn |
| F3 | passes | `:149`; and unreachable in production (B1) |
| F4 | passes | `:149` |
| F5 | passes | `:149` |
| F6 | **FAILS** (expects CANNOT RUN, gets QUIET) | |
| F7 | passes | `:155` already returns QUIET when armed |

F2–F5 and F7 are useful *mutation* coverage — F2 catches an `edited`-always-true implementation, F5 a
missing path scope, F7 a reordering — but as written they are regression assertions, not falsifiers
of the change. This repo has shipped vacuous falsifiers before and treats the distinction as load-bearing.

Two further defects in the table: **F5 and F6 omit the "zero banners" precondition** that F1–F4 state,
so as specified they do not pin which branch they exercise; and **F6 names `edited` in its condition
while the branch it tests does not consult `edited`**, so it cannot distinguish an implementation that
checks it from one that does not.

**Smallest fix.** Label the table's two columns — *discriminates the fix* vs *pins behaviour a
mutation could break* — and state each QUIET case's mutation. Add the missing preconditions.

### M2 — "Resolves inside `ROOT`" is under-specified in four ways that matter.

**Claim.** §2.2 settles *what* the test is on and never says *how*.

**Evidence / cases.**
1. **String prefix vs `is_relative_to`.** A sibling checkout named
   `…/youtube-playlist-summaries-cloud-old` string-prefix-matches `ROOT`. The spec must mandate
   `Path(p).resolve().is_relative_to(ROOT)`, not `str.startswith`.
2. **Relative `file_path`.** `Path.resolve()` on a relative path resolves against the *hook process's*
   cwd, which is not stated anywhere. Measured: `Write` inputs carry only `('content','file_path')`
   and `Edit` only `('file_path','new_string','old_string','replace_all')` — nothing records the cwd
   the path was relative to. Refuse relative paths (count them as outside) rather than guessing.
3. **macOS case-insensitivity.** Measured: `os.path.exists('/users/kujinlee/code')` is `True` on this
   machine. A path recorded with different case resolves to the same file and fails the comparison —
   under-firing, silently.
4. **Worktrees.** `git worktree list` shows one checkout today, but this project uses throwaway
   worktrees (`superpowers:using-git-worktrees`; the merge-conflict memory mandates one). A worktree
   sits outside `ROOT`, so genuine plan work there reads as "outside the repo" — the same class as
   F5's scratchpad case, but with the opposite correct answer. §8 should say so.

`.git/` and gitignored files are *not* a problem worth solving: `.claude/plans/`, `.claude/executing-plan`
and `.claude/banner-warnings.log` are all inside `ROOT` and all gitignored (`.gitignore:89-102`), and
the guard writes its own log through Python rather than `Edit`, so it cannot self-trigger.

### M3 — A module-level import of `check-plan-progress` couples the *working* half of this guard to a dependency it does not use.

**Claim.** §4.2 adopts `begin-plan.py`'s import-and-assert precedent without noting that the two
scripts have different blast radii. `begin-plan.py` does nothing without `count_steps`;
`check-banner-armed.py`'s existing banner-without-plan rule does not need it at all.

**Evidence.** `begin-plan.py:104-110` raises `ImportError` on a rename. Raised at module scope inside
`check-banner-armed.py`, that traceback exits non-zero, `block-idle-stop.sh:71-73` maps it to exit 1,
and the *existing* rule stops running — reported as a Python traceback rather than in the file's own
`TREAT THIS AS NOT RUN` vocabulary, which is what `:41-43` promises.

No cycle and no meaningful cost, verified: `check-plan-progress.py:44-53` imports only stdlib and
compiles two regexes at module scope, and its `__main__` guard means `exec_module` under the name
`_plan_progress` runs no argparse.

**Smallest fix.** Import inside the I/O shell, catch `ImportError`, and return `CANNOT_RUN` with the
file's own message — so a rename is loud *and* the surviving half still reports in its own terms.

### M4 — §6's premise about the sibling is inaccurate, and the new warning has no acknowledgement path at all.

**Claim.** §6: *"The sibling warn-only half has none [no anti-nag suppression]."*

**Evidence.** `check-ci-watched.py` has a per-SHA acknowledgement that is functionally suppression:

```python
# scripts/check-ci-watched.py:93-94
    if watching_sha == head_sha:
        return QUIET, ""
```

and its message ends *"Already armed one this turn? Run `--watching` so this stops asking about this
commit."* (`:112`). The existing banner-without-plan rule also self-limits — arming the plan makes it
quiet (`check-banner-armed.py:154-155`).

The new warning has neither: in a paused or no-tick-continuation state (B1) there is no action short
of emitting a banner that silences it, and it re-fires on every stop. Combined with **B3** (nothing is
logged), the rate is both unbounded and unmeasurable.

---

## LOW

**L1 — Two different citations for one docstring.** §1 says the gap is stated at `:36-37`; §7.2 says
`:35-37`. Line 35 is the section header `WHAT IT CANNOT SEE, stated rather than hidden:`; 36-37 are
the bullet. Both defensible, but a spec that cites the same lines twice should agree with itself.

**L2 — `begin-plan.py:92-104` is cited for an assertion that lives at `:104-110`.** Lines 92-96 are
the docstring paragraph; `:104` is the `missing = [...]` comprehension; the `raise ImportError` that
makes it "fail loudly" is at `:107-110`, outside the cited range. Substance verified — the claim is
true, the citation stops one line short of the mechanism.

**L3 — "26 in the session where this was checked" names no session.** Unreproducible as written; this
project's rules of evidence would call that unverified. My independent measurement over the 12 most
recent transcripts **corroborates the shape claims**: `Edit` × 52, key set always
`('file_path','new_string','old_string','replace_all')`; `Write` × 4, always `('content','file_path')`;
`NotebookEdit` × 0; `MultiEdit` × 0. So §4.2's substantive claims are **supported**, and its honesty
about `notebook_path` being unverified is **correct** — only the provenance is unciteable.

**L4 — "Seven scripts have one; none of this guard's class does" (§6).** Seven is **verified**:
`scripts/mutations/` holds exactly `check-dashboard-entry`, `check-plan-code`, `check-selftest-counts`,
`check-theme-token-coverage`, `gen-dashboard`, `page_chrome`, `page_markup`. But "class" is undefined,
and under the natural reading (`check-*` guards) the sentence is **false** — four of the seven are
`check-*` guards. It is true only under "the three Stop-hook observers". Say which.

**L5 — §8 is incomplete in four specific ways**, which is the question §8 exists to answer honestly:
subagent-dispatch turns (**H2**), window truncation by meta/system records (**H1**), the paused state
(**B2**), and non-`Edit`/`Write` write paths (`MultiEdit`, MCP file tools). §8's existing two bullets
are accurate; the section understates the gap.

---

## Claims I verified as CORRECT

Recorded so the next round does not re-litigate them:

- §1's `decide()` quotation and every line number in it: `:149`, `:153`, `:155`, `:157` all match
  `scripts/check-banner-armed.py` exactly, including that `armed` is unreachable when `banner is None`.
- The docstring at `:36-37` does state the gap in the words quoted.
- `count_steps` **does** return `(done, total)` over `- [ ]` / `- [x]` (`check-plan-progress.py:71-74`,
  `_STEP_RE` at `:57`).
- No import cycle; import cost is negligible (M3).
- Seven mutation manifests (L4).
- `check-anchors.py:61` is `HEAD_LINES = 10`, so §0's header-order warning is right.
- The declared self-test count is honest today: docstring says `# 25 cases` (`:47`), the suite prints
  `25/25`, and `check-banner-armed.py` **is** pinned in `check-selftest-counts.POPULATION:88` — so
  §7.1's bookkeeping requirement is real and correctly scoped.
- `ci.yml:195-196` runs the self-test, and `:217` runs the count observer — §6.3's rename argument holds.
- `docs/backlog.md` row 95 does say *"edits a **tracked** file"*, so §2.2's ⚠ reword is required.
- §2.2's four reasons for rejecting `git ls-files` are sound; reason 4 (a new file is untracked but is
  still plan work) is the decisive one and is correct.

---

## What would change my verdict

B1 is the finding that makes the rest matter: as specified, this guard would ship, run almost never,
and when it did run would fire on paused plans and post-block continuations whose banners the window
had just discarded. A v2 that (i) enumerates the hook's reachable states, (ii) excludes `paused`,
(iii) repairs the window's boundary rule, and (iv) logs the new firing, would be a different and
defensible design. Nothing here argues against the *goal* — the inverse direction is real and worth
catching.

VERDICT: NOT CONVERGED
