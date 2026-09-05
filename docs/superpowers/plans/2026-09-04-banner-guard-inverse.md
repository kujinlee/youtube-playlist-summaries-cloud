# Banner Guard Inverse Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them —
> without reading the chat transcript.

**Goal:** Teach `scripts/check-banner-armed.py` to detect *plan armed, work done, no banner emitted*, and make that branch reachable by moving the guard ahead of the blocking check in `.claude/hooks/block-idle-stop.sh`.

**Architecture:** Extend the existing pure core (`decide()`) with two new inputs supplied by the I/O shell; split the transcript windowing helper so one implementation serves both text and tool-use extraction; move one line in the Stop hook. No new files.

**Tech Stack:** Python 3 stdlib only (`json`, `re`, `pathlib`, `importlib.util`, `tempfile`), bash. Self-tests are inline via `--self-test`, run in CI at `.github/workflows/ci.yml:195-196`.

**Spec:** `docs/superpowers/specs/2026-09-04-banner-guard-inverse-design.md` (v3, approved).

**v2, 2026-09-04** — folds the Post-Plan Gate (both halves NOT CONVERGED: 5 Blocking, 4 High, 6 Medium). Reviews: `docs/reviews/{claude,coordinator}/plan-banner-guard-inverse-r1-*.md`. **v1 would have crashed on its first real firing.** See *What round 1 found* below.

## Global Constraints

- **`decide()` is PURE** — *"Pure: every input is passed in."* No new I/O inside it.
- **The guard must NEVER return 2 to the session.** `block-idle-stop.sh:66-73` maps observers to exit 1.
- **`REPO_ROOT`, not `ROOT`** — `block-idle-stop.sh:23`. There is no `set -u`; `$ROOT` expands to empty and every stop would block.
- **Never re-implement `count_steps`.** Borrow it from `check-plan-progress.py` by path import.
- **No test expecting `QUIET` discriminates a fix** — today's `decide()` returns `QUIET` for every banner-less turn. Only `WARN`, `CANNOT RUN`, or **a side effect** can.
- ⚠ **`scripts/check-selftest-counts.py` IS RED FROM TASK 1 UNTIL TASK 7, BY DESIGN.** The declared count at `:47` (`# 25 cases`) is updated once, in Task 7. That command is a CI step (`.github/workflows/ci.yml:217`), so **do not push an intermediate commit alone** — push the branch only after Task 7. Each task's Step 4 asserts `--self-test` passes, which is a different question from whether the declared number matches.
- ⚠ **Three red steps are CRASHES, not failures.** `case(...)` evaluates its argument eagerly, so a `NameError` or a bad keyword aborts `_self_test()` before any line prints. "Expected: FAIL" in Tasks 1, 2 and 3 means *the suite aborts with that traceback*, not that a case prints `FAIL`. That is acceptable for a signature-introducing step and is called out per task; it is **not** acceptable as the only red for a behavioural claim — see Task 3, which is split for exactly that reason.

## What round 1 of the Post-Plan Gate found

Both halves executed rather than read. Every finding was an **instrumentation** defect; the design held.

| | defect | fixed in |
|---|---|---|
| **B1** | `steps` passed as a keyword *argument* in T4, read as a *local* in T5 → `NameError` on every firing of the new class, before the message printed and before the log was written | T4 Step 3 |
| **B2** | F6's `hook.index("exit 2")` matches the **header comment at `:15`**, so it is red *after* the move too. Measured: 51/52 | T6 Step 1 |
| **H1** | F4 was downgraded from a side-effect test to a `log_line` string-format assertion — **this is why B1 got through**. Nothing in v1 executed `run_decide` | T5 Step 1 |
| **H2** | `_plan_steps`' `except` list cannot hold what `exec_module` throws. Measured escape: an undefined name at module scope in the borrowed file produced a traceback and exit 1 | T3 Step 3 |
| **M1** | the declared count is stale across six of seven commits | Global Constraints |
| **M2** | Task 7 quoted a string that does not exist, and there are **two** occurrences | T7 Step 4 |
| **M3** | §2's two-reader table has a third state — the anti-nag ALLOW | T6 Step 3 |
| **M4** | Task 1's Files range `:73-121` **deletes `_is_tool_result` and `_text_blocks`**, which the new code calls | T1 Files |
| **Cx-M** | `_edit_inside_repo` accepts the repo root itself (`parts` is empty, so the `.git` guard passes vacuously) | T4 Step 3 |

**Refuted — do NOT "fix" these.** `steps in (_UNSET, None)` is **safe** for tuples (`tuple.__eq__` returns `NotImplemented` against `object()`, identity fallback gives `False`) — measured twice independently. `Path.resolve()` on non-existent paths behaves as assumed on darwin. `parts[:1]` does test the first component. `ROOT / "scripts" / …` is the right base. And `check-ci-watched.py:107`'s *"Nothing is blocked"* is **accurate** — that script stays *after* the blocking check and only runs on allowed stops; the defect is the spec's §8 wording, not that file.

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `scripts/check-banner-armed.py` | the guard: window, predicate, message, log | Modify — Tasks 1-5, 7 |
| `.claude/hooks/block-idle-stop.sh` | Stop-hook wiring and exit-code mapping | Modify — Task 6 |
| `docs/backlog.md` | row 95's two `tracked` occurrences | Modify — Task 7 |
| `docs/dashboard-entries.md` | the dashboard entry | Modify — Task 7 |

## ⚠ The `_UNSET` sentinel, and why a plain default is wrong

The 25 existing self-test calls are `decide([...], armed=False)` with no plan info. A default of `None` is worse than useless: §4.4 makes `armed and steps is None` mean *CANNOT RUN*, so the existing case at `:257-258` would flip from QUIET. Three states must stay separable:

| `steps` | meaning |
|---|---|
| `_UNSET` (default) | the caller did not consult a plan — behave exactly as before |
| `None` | consulted; the plan is **unreadable or has zero checkboxes** → `CANNOT_RUN` |
| `(done, total)` | consulted successfully |

---

### Task 1: One window, two extractors, and `isMeta` stops being a turn boundary

**Files:**
- Modify: `scripts/check-banner-armed.py:73-104` (replace `assistant_texts_since_last_user` only — ⚠ **NOT `:73-121`**: `:107-121` is `_is_tool_result` and `_text_blocks`, both **called** by the replacement code. Deleting them kills the suite at import), `:288-308` (windowing self-tests)

**Interfaces:**
- Produces: `records_since_last_user(lines) -> list[dict] | None`, `texts_of(records) -> list[str]`, `edited_paths_of(records) -> list[str]`. `assistant_texts_since_last_user(lines)` is kept as a thin wrapper so existing callers and self-tests are untouched.

- [ ] **Step 1: Write the failing tests**

Add after `:308`:

```python
    def meta(text: str) -> str:
        return json.dumps({"type": "user", "isMeta": True, "message": {"content": text}})

    def notif(text: str) -> str:
        return json.dumps({"type": "user", "promptSource": "system",
                           "message": {"content": text}})

    def edit(path: str) -> str:
        return json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Edit", "input": {"file_path": path}}]}})

    # F5 — discriminating: an isMeta record must NOT start a new turn
    lines_meta = [user("go"), asst(B.format(2, 4)),
                  meta("Stop hook feedback: DO NOT STOP"), asst("kept working")]
    case("F5 an isMeta record is NOT a turn boundary — the banner stays in window",
         highest_banner(texts_of(records_since_last_user(lines_meta) or [])) == (2, 4))

    # R6 — regression: a task notification IS a fresh turn (check-plan-progress.py:28-36)
    lines_notif = [user("go"), asst(B.format(2, 4)),
                   notif("<task-notification>done</task-notification>"), asst("new turn")]
    case("R6 a task notification IS a turn boundary — 52 of 72 such records begin a real turn",
         highest_banner(texts_of(records_since_last_user(lines_notif) or [])) is None)

    case("edited_paths_of finds an Edit's file_path in the window",
         edited_paths_of(records_since_last_user([user("go"), edit("/a/b.py")]) or [])
         == ["/a/b.py"])
    case("edited_paths_of ignores a non-editing tool",
         edited_paths_of([{"type": "assistant", "message": {"content": [
             {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}}]}}]) == [])
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 scripts/check-banner-armed.py --self-test`
Expected: **the suite ABORTS** with `NameError: name 'records_since_last_user' is not defined` before printing any case. That is the red — `case()` evaluates eagerly.

- [ ] **Step 3: Split the helper and add the isMeta rule**

Replace **only** `assistant_texts_since_last_user` (`:73-104`), leaving `_is_tool_result` and `_text_blocks` in place:

```python
def records_since_last_user(lines: list[str]) -> list[dict] | None:
    """Records emitted after the most recent REAL user message. None if unparseable.

    Two kinds of `user` record are not the human typing, and treating them as turn boundaries
    truncates the window:
      * a tool RESULT — without this, the window is cut at the last tool call.
      * an `isMeta` record — a skill injection, or THIS HOOK's own `⛔ DO NOT STOP` feedback.
        Measured 2026-09-04: the block message sat 72 records after the `STEP 2 of 4` banner for
        the step still in progress, so the banner fell out of window by construction.

    ⚠ `promptSource` is deliberately NOT part of this rule. Measured over 30 transcripts: skipping
    it too collapses 142 windows to 70, and 52 of the 72 removed boundaries begin a GENUINELY NEW
    turn — 27 are `<task-notification>` records, which check-plan-progress.py:28-36 calls "a FRESH
    turn" in its own words. A window that never resets is as wrong as one that resets too often.
    """
    records = []
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            records.append(json.loads(raw))
        except (ValueError, TypeError):
            continue
    if not records:
        return None

    start = 0
    for i, rec in enumerate(records):
        if rec.get("type") != "user":
            continue
        if _is_tool_result(rec) or rec.get("isMeta") is True:
            continue
        start = i + 1
    return records[start:]


def texts_of(records: list[dict]) -> list[str]:
    out: list[str] = []
    for rec in records:
        if rec.get("type") == "assistant":
            out.extend(_text_blocks(rec))
    return out


_EDIT_TOOLS = ("Edit", "Write", "NotebookEdit")


def edited_paths_of(records: list[dict]) -> list[str]:
    """Every file path an editing tool touched in this window.

    ⚠ `notebook_path` is UNVERIFIED — NotebookEdit appeared 0 times across the corpus both
    reviewers measured. `MultiEdit` is absent because it does not exist in this runtime (measured
    x0 by three independent reviewers); adding it would be dead code with a self-test asserting
    behaviour nothing can emit.
    """
    out: list[str] = []
    for rec in records:
        if rec.get("type") != "assistant":
            continue
        content = (rec.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for b in content:
            if not isinstance(b, dict) or b.get("type") != "tool_use":
                continue
            if b.get("name") not in _EDIT_TOOLS:
                continue
            inp = b.get("input") or {}
            p = inp.get("file_path") or inp.get("notebook_path")
            if isinstance(p, str) and p:
                out.append(p)
    return out


def assistant_texts_since_last_user(lines: list[str]) -> list[str] | None:
    """Back-compat wrapper: the text half of the window. Existing callers are unchanged."""
    records = records_since_last_user(lines)
    return None if records is None else texts_of(records)
```

- [ ] **Step 4: Run to verify they pass**

Run: `python3 scripts/check-banner-armed.py --self-test`
Expected: every case PASSES. **Read the printed `N/N` rather than checking it against a number written here** — a predicted count is a second copy that drifts, which is the defect Task 7 Step 3 exists to prevent. All 25 originals still pass — the wrapper preserves them.

- [ ] **Step 5: Commit** (do not push — see Global Constraints)

```bash
git add scripts/check-banner-armed.py
git commit -m "One transcript window, two extractors, and the hook's own block message stops truncating it"
```

---

### Task 2: A paused plan is not armed

**Files:** Modify `scripts/check-banner-armed.py:180-188` (`_armed`)

**Interfaces:** Produces `_armed_from_text(text: str) -> bool`, used by `_armed()`.

- [ ] **Step 1: Write the failing test**

```python
    case("R5 a paused sentinel is NOT armed — pause is the documented in-flight-work escape",
         _armed_from_text("plan: x.md\narmed: t\npaused: waiting on CI\n") is False)
    case("...but a plain armed sentinel still is",
         _armed_from_text("plan: x.md\narmed: t\n") is True)
    case("...and a sentinel with no plan value is not armed",
         _armed_from_text("armed: t\n") is False)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 scripts/check-banner-armed.py --self-test`
Expected: **the suite ABORTS** with `NameError: name '_armed_from_text' is not defined`.

- [ ] **Step 3: Extract the rule and add the paused clause**

```python
def _armed_from_text(text: str) -> bool:
    """PURE. True iff the sentinel names a plan AND has not been stood down.

    `paused:` is honoured because check-plan-progress.decide() honours it — the two must agree
    about what "armed" means, or this guard's principal firing state becomes the one documented
    escape. begin-plan.py:56-61: --pause is for being legitimately BLOCKED ON IN-FLIGHT WORK, a
    dispatched review or a CI run. It fired three times in one session (backlog #94).
    """
    named = False
    for line in text.splitlines():
        key = line.split(":", 1)[0].strip()
        if key == "paused":
            return False
        if key == "plan" and line.split(":", 1)[-1].strip():
            named = True
    return named


def _armed() -> bool:
    try:
        return _armed_from_text(SENTINEL.read_text())
    except OSError:
        return False
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3 scripts/check-banner-armed.py --self-test`
Expected: every case PASSES. **Read the printed `N/N` rather than checking it against a number written here** — a predicted count is a second copy that drifts, which is the defect Task 7 Step 3 exists to prevent.

- [ ] **Step 5: Commit**

```bash
git add scripts/check-banner-armed.py
git commit -m "A paused plan stands down here too, not only in the guard that blocks"
```

---

### Task 3: Borrow the plan decision by path, and report blindness unconditionally

⚠ **Split into 3a and 3b.** Round 1 found that v1's only red for this task was *"unexpected keyword argument"* — which proves the signature is old, **not** that the hoist is missing. 3a introduces the signature with behaviour unchanged; 3b makes the behavioural claim, and its red is a real `FAIL` line.

**Files:** Modify `scripts/check-banner-armed.py` — add `import importlib.util`, `_UNSET`, `_load_plan_progress()`, `_plan_steps()`; change `decide()`'s signature and add the hoist.

#### Task 3a — the signature alone, behaviour unchanged

- [ ] **Step 1: Write the test that pins "nothing changed"**

```python
    case("the default _UNSET means 'not consulted' and changes nothing",
         decide([B.format(2, 5)], armed=True)[0] == QUIET)
    case("passing steps explicitly with a banner present is still the old path",
         decide([B.format(2, 5)], armed=True, steps=(1, 4))[0] == QUIET)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 scripts/check-banner-armed.py --self-test`
Expected: **suite ABORTS** — `decide() got an unexpected keyword argument 'steps'`.

- [ ] **Step 3: Add `_UNSET` and widen the signature only**

After `QUIET, WARN, CANNOT_RUN = 0, 1, 2`:

```python
_UNSET = object()   # `steps` was not consulted. Distinct from None, which means "unreadable".
```

Change `def decide(texts, armed):` to `def decide(texts, armed, steps=_UNSET, edited=False):`. **Add no new logic.**

- [ ] **Step 4: Run** → `python3 scripts/check-banner-armed.py --self-test`

Expected: every case PASSES. **Read the printed `N/N` rather than checking it against a number written here** — a predicted count is a second copy that drifts, which is the defect Task 7 Step 3 exists to prevent.

#### Task 3b — the hoist, with a behavioural red

- [ ] **Step 1: Write the failing tests**

```python
    # F2 — discriminating: blindness is reported even when a banner exists
    case("F2 armed + unreadable plan + a banner present is still CANNOT RUN",
         decide([B.format(2, 5)], armed=True, steps=None)[0] == CANNOT_RUN)
    # F3 — discriminating: zero checkboxes is CANNOT RUN, not "finished"
    case("F3 armed + a plan parsing to zero checkboxes is CANNOT RUN, never quiet",
         decide([], armed=True, steps=None)[0] == CANNOT_RUN)
    case("...and it says TREAT THIS AS NOT RUN",
         "TREAT THIS AS NOT RUN" in decide([], armed=True, steps=None)[1])
    case("a PAUSED plan with an unreadable file is quiet, not CANNOT RUN — stood down",
         decide([], armed=False, steps=None)[0] == QUIET)
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 scripts/check-banner-armed.py --self-test`
Expected: the suite **runs to completion** and prints `FAIL` for F2 and F3 (they return QUIET). This is a behavioural red, not a crash — that is the point of the split.

- [ ] **Step 3: Add the loader and the hoist**

```python
def _load_plan_progress():
    """Import check-plan-progress.py BY PATH — the hyphen makes it un-importable by name.

    ⚠ Called from the I/O SHELL, not module scope. begin-plan.py raises at import because it does
    nothing without these names; this guard's banner-without-plan rule needs them not at all, so a
    rename must not kill the working half with a traceback instead of this file's own TREAT THIS
    AS NOT RUN vocabulary.

    ⚠ A second small loader now exists (begin-plan.py:89-103 has the first). Accepted: a loader
    cannot drift SILENTLY — it either loads or raises. The rule worth protecting from duplication
    is count_steps' SEMANTICS, which drift quietly and yield two different counts.
    """
    spec = importlib.util.spec_from_file_location(
        "_plan_progress", ROOT / "scripts" / "check-plan-progress.py")
    if spec is None or spec.loader is None:
        raise ImportError("cannot load scripts/check-plan-progress.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for n in ("count_steps", "parse_sentinel"):
        if not hasattr(mod, n):
            raise ImportError(
                f"scripts/check-plan-progress.py no longer defines {n} — this guard borrows the "
                f"checkbox rule rather than copying it. Re-point it, or this guard and the Stop "
                f"guard will count different things.")
    return mod


def _plan_steps():
    """-> (done, total), or None if the plan cannot be measured. NEVER raises.

    None covers BOTH "no readable plan file" and "zero checkboxes parsed". The owning guard treats
    zero checkboxes as CANNOT RUN (check-plan-progress.py:113-118), not as "finished", and this
    guard must agree — importing the counter while re-deriving a different meaning from its return
    value is the shared-function-holding-half-a-contract shape.

    ⚠ `except Exception`, deliberately. `exec_module` runs arbitrary module-level code and can
    raise ANYTHING: measured 2026-09-04, one undefined name at module scope in the borrowed file
    produced a NameError that escaped a narrow (ImportError, OSError, SyntaxError, KeyError,
    AttributeError, ValueError) list — a traceback and exit 1, indistinguishable at the hook from
    a genuine warning. A partially-edited sibling guard is the realistic trigger, and this repo
    edits that file. Every caught exception maps to the same `return None`, so widening changes no
    behaviour except the one that currently escapes.
    """
    try:
        mod = _load_plan_progress()
        fields = mod.parse_sentinel(SENTINEL.read_text())
        plan = (ROOT / fields["plan"]).resolve()
        done, total = mod.count_steps(plan.read_text())
        return None if total == 0 else (done, total)
    except Exception:
        return None
```

Add `import importlib.util`. Then, in `decide()`, immediately after the `texts is None` check:

```python
    # Blindness is a property of the sentinel and the plan file, NOT of whether the assistant
    # happened to type a heading — so it is answered before the banner is even looked at.
    if armed and steps is None:
        return CANNOT_RUN, (
            "CANNOT RUN: .claude/executing-plan names a plan this check could not measure — "
            "missing, unreadable, or containing zero `- [ ]` step checkboxes. TREAT THIS AS "
            "NOT RUN — do not read the absence of a warning as 'a banner was not owed'.")
```

- [ ] **Step 4: Run to verify they pass**

Expected: every case PASSES. **Read the printed `N/N` rather than checking it against a number written here** — a predicted count is a second copy that drifts, which is the defect Task 7 Step 3 exists to prevent.

- [ ] **Step 5: Commit**

```bash
git add scripts/check-banner-armed.py
git commit -m "Borrow the plan DECISION, not just its counter, and answer blindness first"
```

---

### Task 4: The branch that was the point

**Files:** Modify `scripts/check-banner-armed.py` — `decide()`'s `banner is None` arm; add `_edit_inside_repo()`; rewire `run_decide`.

- [ ] **Step 1: Write the failing tests**

```python
    S = (1, 4)   # one of four steps done -> three unticked

    # F1 — THE discriminating case: the measured failure
    case("F1 armed + work left + an edit + NO banner WARNS — the direction that failed",
         decide([], armed=True, steps=S, edited=True)[0] == WARN)
    case("...and the message does NOT claim nothing is blocked",
         "Nothing is blocked" not in decide([], armed=True, steps=S, edited=True)[1])
    case("...and it names the plan-without-banner direction",
         "PLAN WITHOUT A BANNER" in decide([], armed=True, steps=S, edited=True)[1])

    case("R1 armed + work left + NO edit -> quiet (catches `edited` hardcoded true)",
         decide([], armed=True, steps=S, edited=False)[0] == QUIET)
    case("R2 not armed + an edit -> quiet (catches dropping the armed term)",
         decide([], armed=False, steps=S, edited=True)[0] == QUIET)
    case("R4 a banner IS present -> the existing branches decide (catches a reorder)",
         decide([B.format(2, 4)], armed=True, steps=S, edited=True)[0] == QUIET)
    case("a finished plan (0 unticked) + an edit -> quiet",
         decide([], armed=True, steps=(4, 4), edited=True)[0] == QUIET)

    root = Path("/repo")
    case("R3 an edit outside the repo does not count (the scratchpad case)",
         _edit_inside_repo(["/tmp/scratch/x.md"], root) is False)
    case("a relative path is REFUSED — nothing records the cwd it was relative to",
         _edit_inside_repo(["docs/x.md"], root) is False)
    case("a sibling checkout does not prefix-match (/repo-old is not inside /repo)",
         _edit_inside_repo(["/repo-old/x.md"], root) is False)
    case("a .git write is not plan work",
         _edit_inside_repo(["/repo/.git/COMMIT_EDITMSG"], root) is False)
    case("the repo ROOT ITSELF is not a file inside the repo (parts is empty)",
         _edit_inside_repo(["/repo"], root) is False)
    case("...but .github IS ordinary work, not a .git write",
         _edit_inside_repo(["/repo/.github/workflows/ci.yml"], root) is True)
    case("an ordinary repo file counts",
         _edit_inside_repo(["/repo/scripts/x.py"], root) is True)
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 scripts/check-banner-armed.py --self-test`
Expected: **suite ABORTS** — `_edit_inside_repo` is not defined.

- [ ] **Step 3: Implement**

```python
def _edit_inside_repo(paths: list[str], root: Path) -> bool:
    """PURE. True iff any path is a FILE inside `root` that counts as plan work.

    `is_relative_to`, never str.startswith: a sibling checkout named `<root>-old` prefix-matches.
    Relative paths are REFUSED rather than resolved against this process's cwd — measured, the
    Edit/Write tool inputs record only file_path, never the cwd it was relative to.

    ⚠ `parts` must be NON-EMPTY: `Path("/repo").relative_to(Path("/repo")).parts` is `()`, so
    without this the `.git` test passes vacuously and the repo root itself reads as an edit.

    Gitignored paths inside the repo are deliberately NOT excluded. Measured across all 508
    transcripts: 17 Edit/Write calls landed under .claude/, ALL to tracked files, ZERO to any
    gitignored path. An exclusion list would be a second copy of .gitignore to keep in sync.
    """
    for p in paths:
        candidate = Path(p)
        if not candidate.is_absolute():
            continue
        resolved = candidate.resolve()
        if not resolved.is_relative_to(root):
            continue
        parts = resolved.relative_to(root).parts
        if not parts or parts[0] == ".git":
            continue
        return True
    return False
```

In `decide()`, replace the `banner is None` arm:

```python
    banner = highest_banner(texts)
    if banner is None:
        unticked = 0 if steps is _UNSET or steps is None else steps[1] - steps[0]
        if armed and unticked > 0 and edited:
            return WARN, (
                f"⚠ PLAN WITHOUT A BANNER — this turn edited a file in the repo with "
                f"{unticked} step(s) still unticked, and emitted no `## ▶ STEP i of N`.\n"
                "\n"
                "   The banner is the affordance: a reader who was away cannot tell what you\n"
                "   are doing from a wall of tool calls. begin-plan.py prints one to the STDOUT\n"
                "   of a Bash call, which is shown to you and NOT reliably to the human — so\n"
                "   printing it there is not emitting it. It must be in your own visible text.\n"
                "\n"
                "   If this stop is being blocked, you are reading this mid-plan: emit the\n"
                "   banner for the step you are on before continuing. If the plan is genuinely\n"
                "   waiting on in-flight work, `begin-plan.py --pause <why>` stands it down.\n"
                f"   Logged to {WARN_LOG.relative_to(ROOT)}.")
        return QUIET, ""
```

⚠ Note `steps is _UNSET or steps is None`, **not** `steps in (_UNSET, None)`. The `in` form was measured safe, but identity checks state the intent and cannot be broken by a future `__eq__`.

Rewire `run_decide` — ⚠ **`steps` MUST be bound as a local. Task 5 reads it.** Round 1 measured that passing it inline produces `NameError` on every firing of the new class:

```python
    records = None
    path = data.get("transcript_path")
    if isinstance(path, str) and path:
        try:
            records = records_since_last_user(Path(path).read_text().splitlines())
        except OSError:
            records = None
    texts = None if records is None else texts_of(records)
    armed = _armed()
    steps = _plan_steps() if armed else _UNSET          # ← local; Task 5's log block reads it
    edited = _edit_inside_repo(edited_paths_of(records or []), ROOT)
    code, message = decide(texts, armed, steps=steps, edited=edited)
```

- [ ] **Step 4: Run to verify they pass**

Expected: every case PASSES. **Read the printed `N/N` rather than checking it against a number written here** — a predicted count is a second copy that drifts, which is the defect Task 7 Step 3 exists to prevent.

- [ ] **Step 5: Commit**

```bash
git add scripts/check-banner-armed.py
git commit -m "The direction that actually failed: a plan armed, work done, and no banner"
```

---

### Task 5: The new class must reach the log — and F4 must be a SIDE-EFFECT test

⚠ **This task carries round 1's most important lesson.** v1 implemented F4 as an assertion about `log_line`'s string format. That is a pure function, so **nothing in the plan ever executed `run_decide`** — and B1, a `NameError` on the only code path the feature takes, went undetected. Spec §5's own rule says only `WARN`, `CANNOT RUN`, or **a side effect** discriminates. F4 is the side-effect one.

**Files:** Modify `scripts/check-banner-armed.py:173-175` (`log_line`), `:207-219` (the gate), `:311-313` (its self-test)

- [ ] **Step 1: Write the failing tests**

Replace the existing log case at `:311-313`, and add the real F4:

```python
    case("the log line is tab-separated and states the state and the detail",
         log_line("unarmed", "STEP 2 of 5", "2026-09-04T07:00:00-07:00", "sess").split("\t")[1:]
         == ["sess", "unarmed", "STEP 2 of 5\n"])

    # F4 — DISCRIMINATING, and it is a SIDE-EFFECT test on purpose. This is the smallest thing
    # that could have caught round 1's B1 (a NameError in run_decide that no pure test could see).
    import tempfile as _tf
    with _tf.TemporaryDirectory() as _d:
        _root = Path(_d)
        (_root / ".claude").mkdir()
        (_root / "plans").mkdir()
        (_root / "plans" / "p.md").write_text("- [x] one\n- [ ] two\n- [ ] three\n- [ ] four\n")
        (_root / ".claude" / "executing-plan").write_text("plan: plans/p.md\narmed: t\n")
        _tr = _root / "t.jsonl"
        _tr.write_text("\n".join([
            json.dumps({"type": "user", "message": {"content": "go"}}),
            json.dumps({"type": "assistant", "message": {"content": [
                {"type": "tool_use", "name": "Edit",
                 "input": {"file_path": str(_root / "scripts" / "x.py")}}]}}),
        ]))
        _saved = (ROOT, SENTINEL, WARN_LOG)
        globals()["ROOT"] = _root
        globals()["SENTINEL"] = _root / ".claude/executing-plan"
        globals()["WARN_LOG"] = _root / ".claude/banner-warnings.log"
        try:
            _rc = run_decide(json.dumps({"transcript_path": str(_tr), "session_id": "s"}))
            _logged = (_root / ".claude/banner-warnings.log")
            case("F4 run_decide WARNS on the new class and APPENDS a line — the side effect",
                 _rc == WARN and _logged.exists()
                 and _logged.read_text().rstrip("\n").endswith("\tunbannered\t3 unticked"))
        finally:
            globals()["ROOT"], globals()["SENTINEL"], globals()["WARN_LOG"] = _saved
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 scripts/check-banner-armed.py --self-test`
Expected: the log-shape case prints `FAIL` (old signature), and F4 prints `FAIL` — `run_decide` does not yet write for a banner-less WARN.

- [ ] **Step 3: Widen the log and drop the `if banner:` gate**

```python
def log_line(reason: str, detail: str, when: str, session: str) -> str:
    """One appended record. Tab-separated so the log stays greppable and countable.

    `reason` discriminates the two warning classes. The banner-less class has NO banner by
    construction, so the previous shape — which took (step, total) and was written only when a
    banner existed — could never record it. The log is the evidence for whether this should ever
    block, so a class it cannot express reads as never having fired.

    Nothing parses this file (searched 2026-09-04: the only references are this module, its
    self-test, a comment in block-idle-stop.sh, and prose in docs/dashboard-entries.md).
    """
    return f"{when}\t{session or '-'}\t{reason}\t{detail}\n"
```

Replace the logging block in `run_decide` (`steps` is in scope — Task 4 bound it):

```python
    if code == WARN:
        banner = highest_banner(texts or [])
        if banner:
            reason, detail = "unarmed", f"STEP {banner[0]} of {banner[1]}"
        else:
            unticked = 0 if steps is _UNSET or steps is None else steps[1] - steps[0]
            reason, detail = "unbannered", f"{unticked} unticked"
        when = _dt.datetime.now().astimezone().replace(microsecond=0).isoformat()
        try:
            WARN_LOG.parent.mkdir(parents=True, exist_ok=True)
            with WARN_LOG.open("a") as fh:
                fh.write(log_line(reason, detail, when, str(data.get("session_id", ""))))
        except OSError as e:
            message += (f"\n\n   ⚠ AND THE LOG COULD NOT BE WRITTEN ({e}) — the false-alarm "
                        f"rate is not being recorded.")
```

- [ ] **Step 4: Run to verify they pass**

Expected: every case PASSES. **Read the printed `N/N` rather than checking it against a number written here** — a predicted count is a second copy that drifts, which is the defect Task 7 Step 3 exists to prevent.

- [ ] **Step 5: Commit**

```bash
git add scripts/check-banner-armed.py
git commit -m "The log learns a second class, and F4 finally executes the path it is about"
```

---

### Task 6: Make it reachable — move ONE observer

**Files:** Modify `.claude/hooks/block-idle-stop.sh`; add F6 to `scripts/check-banner-armed.py`.

- [ ] **Step 1: Write the failing test (F6) — anchored to the EXECUTABLE line**

⚠ Round 1 measured that `hook.index("exit 2")` matches the **header comment at `:15`** (char 925), so v1's F6 was red *after* the move too. Anchor on the blocking invocation instead:

```python
    # F6 — REACHABILITY. v1 shipped an unreachable branch and every falsifier passed, because a
    # suite over a pure core cannot see its own unreachability.
    #
    # ⚠ ANCHOR ON THE EXECUTABLE LINE. `hook.index("exit 2")` matches the header COMMENT at :15
    # ("# Contract: exit 2 blocks the stop..."), which sits above every line the invocation could
    # move to — so that form is red before AND after the fix. Measured, round 1.
    #
    # ⚠ THIS IS A STRUCTURAL TEST, NOT AN EXECUTION TEST. Nothing here executes a shell hook:
    # running it would unlink the live sentinel, write the live state file, make a live `gh` call
    # and append to the real warnings log, and REPO_ROOT comes from BASH_SOURCE so it cannot be
    # pointed at a fixture. F6 proves ORDER IN THE FILE and nothing more — it would not catch the
    # hook being unreadable, python3 being absent, or stdin not arriving.
    hook = (ROOT / ".claude/hooks/block-idle-stop.sh").read_text()
    case("F6 the banner guard is invoked BEFORE the blocking check that can exit early",
         hook.index("check-banner-armed.py")
         < hook.index('check-plan-progress.py "${ARGS[@]}"'))
    case("F6b the hook uses REPO_ROOT — $ROOT is empty and would block every stop",
         "$ROOT/scripts" not in hook)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 scripts/check-banner-armed.py --self-test`
Expected: F6 prints `FAIL`. Today `check-banner-armed.py` is at `:54`, after the `check-plan-progress.py "${ARGS[@]}"` invocation at `:39`. F6b passes already — it guards the fix, it does not drive it.

- [ ] **Step 3: Move the invocation**

Insert **before** the `check-plan-progress` call, and delete the old banner block at `:43-57`:

```bash
# ── Observer, deliberately AHEAD of the blocking check ───────────────────────────────────────
# It must run in the very state that check REFUSES: armed with unticked steps. Ordering is free
# because it cannot block — and it is REQUIRED, because check-plan-progress.run_decide UNLINKS
# .claude/executing-plan when the last step is ticked, so running after it reads a deleted
# sentinel.
#
# WHO READS THIS depends on the exit code, and all three states are intended:
#   * a blocked stop exits 2 and CLAUDE reads it — the actor, when the next banner is due;
#   * an ordinary unblocked stop exits 1 and the HUMAN reads it — the auditor, when there is
#     nothing left to correct;
#   * or it exits 1 because the ANTI-NAG let a no-progress stop through, in which case the human
#     sees a message addressed to the assistant. The message hedges for exactly that reason.
printf '%s' "$INPUT" | python3 "$REPO_ROOT/scripts/check-banner-armed.py" --decide
BANNER_RC=$?

if ! python3 "$REPO_ROOT/scripts/check-plan-progress.py" "${ARGS[@]}"; then
    exit 2
fi
```

Leave the `check-ci-watched.py` block exactly where it is. The final exit arithmetic is unchanged.

- [ ] **Step 4: Run to verify it passes**

Run: `python3 scripts/check-banner-armed.py --self-test`
Expected: every case PASSES. **Read the printed `N/N` rather than checking it against a number written here** — a predicted count is a second copy that drifts, which is the defect Task 7 Step 3 exists to prevent.
Then: `bash -n .claude/hooks/block-idle-stop.sh` → Expected: no output.

- [ ] **Step 5: Commit**

```bash
git add .claude/hooks/block-idle-stop.sh scripts/check-banner-armed.py
git commit -m "The observer runs in the state the blocking check refuses, which is the only state it is for"
```

---

### Task 7: The claims that go stale, the count, and the entry

**Files:** `scripts/check-banner-armed.py:30-48`, `:255-256`; `docs/backlog.md`; `docs/dashboard-entries.md`

- [ ] **Step 1: Fix the "Nothing is blocked" claim and its test**

`:161` says *"Nothing is blocked."* That can be false: a sentinel with **no `plan:` line** makes `_armed()` return `False` (so this branch fires) while `check-plan-progress` takes its CANNOT-RUN path and blocks. Replace with `"This does not block your stop by itself."` and rewrite `:255-256`:

```python
    case("...and it does not claim nothing is blocked — another check may be blocking",
         "does not block your stop by itself" in decide([B.format(2, 5)], armed=False)[1])
```

⚠ **Do NOT touch `scripts/check-ci-watched.py:107`.** It carries the same sentence, and there it is **accurate**: that script stays *after* the blocking check and only runs on allowed stops. Round 1 raised it; the defect is the spec's §8 wording, which means the two messages *in this file*.

- [ ] **Step 2: Rewrite the docstring's WHAT IT CANNOT SEE block**

`:35-37` states this gap as a known limitation, now false. Replace with spec §9: subagent edits (0 `isSidechain:true` across 508 transcripts; `subagent-driven-development` is the Phase 3 default), `Bash`-only work, git worktrees, **F6 being structural**, banner quality, work with no plan armed — and add:

> **macOS case-insensitivity.** `Path.resolve()` does not canonicalise case on darwin (measured: `/users/...` and `/Users/...` resolve to different strings), so a `file_path` recorded with different case fails `is_relative_to(ROOT)` and the edit is silently unseen. Low probability — tool paths are absolute and consistently cased — but it under-fires *silently*, which is the dangerous direction.

- [ ] **Step 3: Update the declared self-test count**

Run: `python3 scripts/check-banner-armed.py --self-test`
**Read the printed `N/N` and copy that number** into `:47` (`# 25 cases`). Do **not** compute it by adding — the declared count drifted three separate times on 2026-09-04.

Then: `python3 scripts/check-selftest-counts.py` → Expected: PASS. This is the first point in the branch where it is green (Global Constraints).

- [ ] **Step 4: Reword BOTH `tracked` occurrences in backlog row 95**

⚠ Round 1 measured that v1 quoted a string that does not exist: `**tracked**` appears **zero** times; `tracked` appears **twice**, neither bolded. Both must change, identified by their surrounding words:

1. `…the predicate needs a second clause — most plausibly *the turn edited a tracked file*.`
   → `…most plausibly *the turn edited a file inside the repo*.`
2. `**FALSIFIER FOR ANY FIX:** a session that arms a plan, edits a tracked file and emits no banner must WARN…`
   → `…arms a plan, edits a file inside the repo and emits no banner must WARN…`

Then mark the row ✅ with how it was settled.

- [ ] **Step 5: Add the dashboard entry, then run every gate and commit**

The entry must record: the two spec rounds and the plan gate; that v1 of the spec was unreachable and v1 of the plan would have crashed on first firing; the two-reader decision; and that **`check-ci-watched.py` remains deliberately unreachable on blocked stops**, with the measured `gh pr view` cost as the reason — a reader would not infer that from the row title.

```bash
python3 scripts/check-banner-armed.py --self-test
python3 scripts/check-selftest-counts.py
python3 scripts/check-docs.py
python3 scripts/check-anchors.py
python3 scripts/check-dashboard-entry.py
python3 scripts/check-ratchet-contract.py
python3 scripts/check-review-rounds.py
bash -n .claude/hooks/block-idle-stop.sh
git add -A && git commit -m "Close backlog #95: the guard, the reachability, and the claims that went stale"
```

## Self-Review

**Spec coverage:** §2 → T4 message + T6 comment + T7 Step 1. §4.1 → T6. §4.2 → T2. §4.3 → T3a/T3b. §4.4 → T3b. §4.5 → T1. §4.6 → T1 + T4. §4.7 → T4. §5 F1→T4, F2/F3→T3b, F4→T5, F5→T1, F6→T6, R1-R4→T4, R5→T2, R6→T1. §7 → T5. §8 → T7. §9 → T7 Step 2. **No gaps.**

**Round-1 coverage:** B1→T4 Step 3 (bound local, aside deleted). B2→T6 Step 1 (executable anchor). H1→T5 Step 1 (side-effect F4). H2→T3b Step 3 (`except Exception`). M1→Global Constraints. M2→T7 Step 4 (both occurrences). M3→T6 Step 3 (third state). M4→T1 Files (`:73-104`). Cx-M→T4 (`parts` non-empty). Cx-M2→T3 split. L1→Global Constraints (crash reds named).

**Type consistency:** `steps` is `tuple[int,int] | None | _UNSET` in T3, T4, T5, and is a **bound local** in `run_decide`. `log_line(reason, detail, when, session)` defined in T5, used in T5. `records_since_last_user`/`texts_of`/`edited_paths_of` defined in T1, consumed in T4's `run_decide` and T1's tests. `_edit_inside_repo(paths, root)` defined and used in T4.

**Ordering:** T4 depends on T1 and T3b. T5 depends on T4 (it reads the `steps` local T4 binds). T6 depends on nothing but is last so the guard is correct before it becomes reachable.
