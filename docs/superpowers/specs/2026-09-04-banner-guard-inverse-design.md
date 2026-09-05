# The banner guard learns the direction that actually failed

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them —
> without reading the chat transcript.

**Backlog #95.** **v3, 2026-09-04** — folds round 2 (both halves NOT CONVERGED: 2 Blocking, 7 High,
8 Medium, 4 Low). v1 was unreachable; v2 was reachable and delivered to the wrong reader. Round
files: `docs/reviews/{coordinator,claude}/banner-guard-inverse-r{1,2}-*.md`.

⚠ **Header order is load-bearing** — `check-anchors.py:61` sets `HEAD_LINES = 10`.

---

## 1. The problem, measured

`scripts/check-banner-armed.py` warns on **banner without a plan**. The inverse — **a plan armed,
work done, and no banner emitted** — is what failed on 2026-09-04, and the guard cannot see it:

```python
banner = highest_banner(texts)
if banner is None:
    return QUIET, ""          # :149 — returns BEFORE `armed` is consulted
```

**The cause was a SUBSTITUTION, not forgetfulness.** `begin-plan.py` prints a banner, so arming a
plan *felt* like satisfying the rule — but it prints to the **stdout of a Bash call**, which
`CLAUDE.md` says is shown to the assistant and *not reliably to the user*. The banner existed on
every armed step and reached nobody.

**Severity 🟡.** Nothing broken, no money. A stated comprehensibility affordance lapsed for most of a
session and **the human, not the harness, noticed**.

## 2. Who this warning is FOR — decided, and it is the crux

**Reader: the assistant, not the human.** *The human reads BANNERS; the assistant emits them.*

This matters because the hook routes by exit code, in its own words:

| line | contract |
|---|---|
| `block-idle-stop.sh:15` | *"exit 2 blocks the stop and feeds stderr back to **Claude**"* |
| `block-idle-stop.sh:48-49` | *"Exit 1 is Claude Code's non-blocking error: stderr is shown to **the user**"* |

In the target state — armed, unticked steps — `check-plan-progress` returns `BLOCK`, so the stop
exits 2 and the warning reaches **the assistant**. Round 2 filed that as Blocking on the assumption
the human was the intended reader. **The assumption is what was wrong, not the routing:** a nudge
that arrives as the assistant is told *"⛔ DO NOT STOP"* lands exactly when the next banner is due,
and the assistant is the only party who can act on it.

**The resulting two-reader contract, stated rather than accidental:**

| stop | exit | who reads the warning | why that is right |
|---|---|---|---|
| blocked (armed, work left) | 2 | **the assistant** | the actor, at the moment the next banner is due |
| not blocked (paused, finished, unarmed) | 1 | **the human** | the auditor, when there is nothing left to correct |

`.claude/banner-warnings.log` (§7) accumulates both, so the rate is a number regardless of reader.

⚠ **This makes two existing messages false, and both are fixed.** `check-banner-armed.py:161` says
*"Nothing is blocked."* — untrue on an exit-2 stop. The **new** message must never say it. The
**existing** banner-without-plan message can also hit it: a sentinel with no `plan:` line makes
`_armed()` return `False` (so that branch fires) while `check-plan-progress` takes its CANNOT-RUN
path and blocks. Rare, real, same defect.

## 3. Decisions carried forward (not reopened)

| Question | Decision | Round |
|---|---|---|
| Clause keys on ticking or editing? | **Editing** — a step spans turns without ticking | v1 |
| What does "tracked" mean? | **Path inside the repo, no git call** | v1, user |
| New script or extend? | **Extend** | v1 |
| Who reads the warning? | **The assistant** (§2) | v3, user |
| Does the CI watcher move too? | **No** (§4.1) | v3, user |

⚠ The backlog row's falsifier says *"edits a **tracked** file"* and **must be reworded** to "a file
inside the repo".

## 4. The design

### 4.1 The hook: move ONE observer, not two

v2 moved both warn-only observers ahead of the blocking check. **Round 2 measured the cost:**
`check-ci-watched._skip_reason()` returns `None` — meaning it *does* hit the network — on any
non-default branch with an upstream, then runs `gh pr view --json statusCheckRollup` with a **25 s
timeout**. Moving it would buy a network call on every blocked stop attempt mid-plan.

**Only `check-banner-armed.py` moves.** `check-ci-watched.py` stays exactly where it is.

```bash
# Observer, moved AHEAD of the blocking check: it must run in the very state that check
# refuses, and it cannot block, so its position is free. See the spec's §2 for who reads it.
printf '%s' "$INPUT" | python3 "$REPO_ROOT/scripts/check-banner-armed.py" --decide
BANNER_RC=$?

if ! python3 "$REPO_ROOT/scripts/check-plan-progress.py" "${ARGS[@]}"; then
    exit 2            # blocked: BANNER_RC's stderr has already printed, and Claude reads it
fi

printf '%s' "$INPUT" | python3 "$REPO_ROOT/scripts/check-ci-watched.py" --decide
CI_RC=$?

if [[ "$BANNER_RC" != "0" || "$CI_RC" != "0" ]]; then exit 1; fi
exit 0
```

⚠ **`REPO_ROOT`, not `ROOT`** (`block-idle-stop.sh:23`). Both round-2 halves caught v2 writing
`$ROOT`; the Claude half traced the consequence — there is **no `set -u`**, so `$ROOT` expands to
empty, `python3` on a missing file exits **2**, `PLAN_RC` becomes 2, and **every stop blocks** with
the anti-nag unable to clear it because `run_decide` never ran to write the state file. A wedged
session from one missing prefix.

⚠ **Ordering is load-bearing beyond reachability:** `check-plan-progress.run_decide:180-182`
**unlinks `.claude/executing-plan`** when `unticked == 0`. The observer must run upstream of that
mutation or it reads a sentinel that no longer exists.

### 4.2 `armed` must mean "currently obligates a banner"

`_armed()` (`:180-188`) reads only the `plan:` key. `check-plan-progress.decide()` stands a plan
down first:

```python
fields = parse_sentinel(sentinel_text)
if "paused" in fields:
    return ALLOW, "", None
```

`begin-plan.py:56-61` says `--pause` is for being **legitimately blocked on in-flight work** — a
dispatched review, a CI run — and it fired three times in one session (backlog #94). **`_armed()`
returns `False` when `paused` is present.**

### 4.3 Borrow the decision, not just the counter

v1 imported `count_steps()` then re-derived a *different* meaning from its return value — the
shared-function-holding-half-a-contract shape. `count_steps` returns `(0, 0)` for a plan with no
checkboxes, and its owner calls that failure, not completion (`check-plan-progress.py:113-118`:
*"CANNOT RUN: parsed ZERO step checkboxes … TREAT THIS AS NOT RUN"*).

**Pass `(done, total)`, not `unticked`.** Map `total == 0` to `CANNOT_RUN`. Borrow `parse_sentinel`
alongside `count_steps`.

**The import is BY PATH — the filename's hyphen makes it un-importable by name.** Use the mechanism
`begin-plan.py:89-103` already proves:
`importlib.util.spec_from_file_location("_plan_progress", SCRIPTS / "check-plan-progress.py")`,
then assert the borrowed names.

**Do it inside the I/O shell and catch more than `ImportError`.** `begin-plan.py` dies without these
names, so a module-scope raise is right *there*. This guard's *existing* rule needs them not at all,
and a rename would otherwise kill the working half with a traceback instead of this file's own
`TREAT THIS AS NOT RUN` vocabulary (`:41-43`). Catch **`ImportError`, `OSError`/`FileNotFoundError`,
`SyntaxError`, and missing attributes** — a path import of a renamed file raises `FileNotFoundError`,
not `ImportError`, and `exec_module` can surface anything.

**On duplicating the loader — accepted, with the reason.** A second ~8-line loader now exists.
That is tolerable *because a loader cannot drift silently*: it either loads or raises. The rule
worth protecting from duplication is `count_steps`' **semantics**, which drift quietly and produce
two different counts. Extracting a shared loader module is a third file for no safety gain.

### 4.4 Blindness is reported unconditionally

`CANNOT RUN` is a property of the sentinel and the plan file, not of whether the assistant typed a
heading, so it is hoisted above the banner test:

```python
if armed and steps is None:            # unreadable plan, or zero checkboxes
    return CANNOT_RUN, ...
banner = highest_banner(texts)
if banner is None:
    if armed and unticked > 0 and edited:
        return WARN, <plan without a banner>
    return QUIET, ""
# ... the three existing branches, untouched
```

### 4.5 The window: skip `isMeta` ONLY

`assistant_texts_since_last_user` treats **any** non-`tool_result` `user` record as a turn boundary
(`:93-98`). Some are not the human typing — including the sibling guard's own block message:

```
[1988] META  'Stop hook feedback: … ⛔ DO NOT STOP — 2 of 4 steps are unticked'
       last banner before it: record 1916, `STEP 2 of 4`
```

⚠ **Round 1 proposed skipping `isMeta` AND `promptSource` in `{system, sdk}`. That over-corrects,
and round 2 measured it:** across 30 transcripts the two-field rule collapses **142 windows to 70**,
and **52 of the 72 removed boundaries begin a genuinely new turn** — 27 `<task-notification>`
records, which `check-plan-progress.py:28-36` calls *"a FRESH turn"* in its own words, and 25
`promptSource:"sdk"`, the only real boundary in a subagent session. Only 20 are same-turn injections.

**The rule is `isMeta` only.** A window that never resets is as wrong as one that resets too often.

### 4.6 The two new inputs

**`steps: tuple[int,int] | None`** — `count_steps()` output; `None` when unreadable.
**`edited: bool`** — an `Edit`/`Write`/`NotebookEdit` tool use with a path inside the repo.

*Measured independently by both reviewers:* `Edit` ×52 always carries
`('file_path','new_string','old_string','replace_all')`; `Write` ×4 always `('content','file_path')`;
**`NotebookEdit` ×0 and `MultiEdit` ×0** — `MultiEdit` **does not exist in this runtime**, and a
round-1 finding asking for coverage of it is rejected on that evidence. Read `file_path` or
`notebook_path`; the latter stays labelled unverified.

### 4.7 The path test

`Path(p).resolve().is_relative_to(ROOT)` — **not** `str.startswith`: a sibling checkout named
`…-cloud-old` string-prefix-matches. **Relative paths are refused** rather than resolved against the
hook process's cwd, which nothing records. `.git/` excluded.

**Gitignored paths inside `ROOT` are deliberately NOT excluded — and this is now measured, not
argued.** The two round-1 halves disagreed; round 2 settled it by enumerating every `Edit`/`Write`
`file_path` under `.claude/` across all **508 transcripts**: **17 writes, all to tracked files, zero
to any gitignored path.** An exclusion list would be a second copy of `.gitignore` to keep in sync.

## 5. Falsifiers

**THE RULE THAT SORTS THIS TABLE, which v1 and v2 both got wrong:** today's `decide()` returns
`QUIET` for any banner-less turn, so **no test expecting `QUIET` can discriminate a fix.** Only
`WARN`, `CANNOT RUN`, or a side effect can. v2 labelled two `QUIET` cases "discriminating"; they
were not.

**Discriminating — each FAILS against today's code:**

| # | Condition | Expected |
|---|---|---|
| F1 | armed · unticked > 0 · edited · zero banners | **WARN** — the measured failure |
| F2 | armed · plan unreadable · **banner present** | **CANNOT RUN** — §4.4's hoist |
| F3 | armed · plan parses to **zero checkboxes** · edited | **CANNOT RUN** — §4.3 |
| F4 | a WARN of the new class | **a line appears in the log** — §7 |
| F5 | `records_since_last_user` given a window whose boundary is an `isMeta` record | **the boundary is NOT a turn start** — §4.5, at the helper, where it discriminates |

**Regression — each pins behaviour a mutation could break:**

| # | Condition | Expected | catches |
|---|---|---|---|
| R1 | armed · unticked > 0 · **not** edited · zero banners | QUIET | `edited` hardcoded true |
| R2 | **not** armed · edited · zero banners | QUIET | dropping the `armed` term |
| R3 | armed · unticked > 0 · edit **outside** the repo | QUIET | a missing path scope |
| R4 | armed · edited · banner present, `i < N` | QUIET | reordering the existing branches |
| R5 | armed · **`paused:`** · edited · zero banners | QUIET | §4.2 removed |
| R6 | boundary is a `<task-notification>` record | **IS** a turn start | §4.5 over-widened again |

**Reachability — F6, and an honest statement of what it is.** v1 shipped an unreachable branch and
every falsifier passed, because a suite over a pure core cannot see its own unreachability.

> **F6:** a test parses `.claude/hooks/block-idle-stop.sh` and asserts `check-banner-armed.py` is
> invoked **before** the `exit 2`. It fails today.

⚠ **F6 is a STRUCTURAL test, not an execution test, and must be labelled so in the code.** Round 2
established that no harness executes a shell hook here: running it unlinks the live sentinel, writes
the live state file, makes a live `gh` call, appends to the real warnings log, and `REPO_ROOT` comes
from `BASH_SOURCE` so it cannot be pointed at a fixture. F6 therefore proves **order in the file**,
not runtime behaviour — it would not catch the hook being unreadable, `python3` being absent, or the
payload failing to reach stdin. Building a real hook harness is out of scope (§6).

## 6. Deliberately out of scope

- **The CI watcher's reachability.** It remains skipped on blocked stops. §4.1 records the measured
  network cost that decided this; it is a separate change wearing this one's clothes.
- **A shell-hook execution harness.** Real, and larger than this row (§5, F6).
- **An acknowledgement path.** v2 claimed *"the sibling warn-only half has no suppression"* —
  **false**: `check-ci-watched.py:93-94` has a per-SHA acknowledgement. The corrected argument is
  that after §4.2 and §4.5 the natural actions already silence this — emit a banner, or pause the
  plan — and §7 makes the rate measurable before anyone designs more.
- **A mutation manifest for this guard.** None of the **three Stop-hook observers** has one.
- **A rename**, despite the name now covering both directions: `block-idle-stop.sh`, `ci.yml:195-196`
  and `check-selftest-counts.POPULATION:88` reference it by name.

## 7. The log must record the new class

The write is gated on a banner existing, and the new case has **zero** banners by construction:

```python
if code == WARN:
    banner = highest_banner(texts or [])
    if banner:                      # ← always None in the new case
```

v1 argued "no suppression needed, the log gives us a number" for a warning that would have logged
nothing forever. **Widen `log_line` with a reason column (`unarmed` / `unbannered`) and drop the
`if banner:` gate.**

**Nothing reads this log — searched, not assumed.** The only references are the writer
(`check-banner-armed.py:61`, `:173-175`, `:207-214`), its own self-test, a hook comment, and prose in
`docs/dashboard-entries.md`. No script parses it, so the grammar change breaks no reader.

## 8. Bookkeeping

1. **The declared `--self-test` count moves** — `# 25 cases` (`:47`), pinned in
   `check-selftest-counts.POPULATION:88`. Drift was caught three times on 2026-09-04.
2. **The docstring at `:35-37` becomes false** and is rewritten in the same commit.
3. **The backlog row's falsifier is reworded** to "a file inside the repo".
4. **Both "Nothing is blocked" messages are corrected** (§2).
5. **A dashboard entry is required.**

## 9. What this still cannot see

- **Subagent edits.** `grep -c '"isSidechain":true'` returns **0** across all 508 transcripts;
  subagent work lives in its own session file. A coordinator turn dispatching five reviewers reads
  as `edited = False`, and `superpowers:subagent-driven-development` is the **Phase 3 default**. In a
  23-window simulation, **6 windows did work through `Bash` only** and stay quiet.
- **Work done entirely through `Bash`.** Widening to any mutating tool was rejected: a turn running
  `gh pr view` to answer a question would warn.
- **Work in a git worktree** — outside `ROOT`, so it reads as outside the repo (same mechanism as
  R3, opposite correct answer).
- **Runtime behaviour of the hook** — F6 is structural (§5).
- **Whether the banner was any good.** Presence, not quality.
- **Work with no plan armed.** Nothing to compare against.

## 10. Round disposition

| Finding | Disposition |
|---|---|
| r1 Cx/Cl — `paused` false-positives | **Fixed** §4.2, R5 |
| r1 Cx/Cl — `total == 0` is CANNOT RUN | **Fixed** §4.3, F3 |
| r1 Cl B1 — branch unreachable | **Fixed** §4.1, F6 |
| r1 Cl B3 — firing never logged | **Fixed** §7, F4 |
| r1 Cl H1 — window truncated | **Fixed** §4.5, F5 — *narrowed by r2* |
| r1 Cl H4 — CANNOT RUN nested | **Fixed** §4.4, F2 |
| r1 Cl M3 — module-scope import | **Fixed** §4.3 |
| r1 Cx H — gitignored paths | **Rejected**, §4.7 — r2 measured 17 writes, 0 gitignored |
| r1 Cx H — `MultiEdit` | **Rejected**, §4.6 — tool does not exist; both halves measured ×0 |
| **r2 Cl B1 — wrong reader on a blocked stop** | **Reframed by decision**, §2 — the assistant is the reader; two messages corrected |
| **r2 Cx B / Cl H2 — `$ROOT` undefined** | **Fixed** §4.1 |
| **r2 Cx H — CI network cost** | **Fixed by scope**, §4.1 + §6 — only one observer moves |
| **r2 Cx H / Cl H3 — window over-widens** | **Fixed** §4.5 — `isMeta` only, R6 guards it |
| **r2 Cx H / Cl H4 — F4/F5 vacuous** | **Fixed** §5 — the sorting rule is now stated |
| **r2 Cl H5 — F7 has no harness** | **Fixed by honesty**, §5 F6 — structural, labelled, limits stated |
| **r2 Cx M — import catches wrong failures** | **Fixed** §4.3 |
| **r2 Cx L — record the log-reader search** | **Fixed** §7 |
