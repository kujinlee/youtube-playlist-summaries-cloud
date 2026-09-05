# Banner Guard Inverse Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them —
> without reading the chat transcript.

**Goal:** Teach `scripts/check-banner-armed.py` to detect *plan armed, work done, no banner emitted*, and make that branch reachable by moving the guard ahead of the blocking check in `.claude/hooks/block-idle-stop.sh`.

**Architecture:** Extend the existing pure core (`decide()`) with two new inputs supplied by the I/O shell; split the transcript windowing helper so one implementation serves both text and tool-use extraction; move one line in the Stop hook. No new files.

**Tech Stack:** Python 3 stdlib only (`json`, `re`, `pathlib`, `importlib.util`), bash. Self-tests are inline via `--self-test`, run in CI at `.github/workflows/ci.yml:195-196`.

**Spec:** `docs/superpowers/specs/2026-09-04-banner-guard-inverse-design.md` (v3, approved).

## Global Constraints

- **`decide()` is PURE** — its docstring says *"Pure: every input is passed in."* No new I/O inside it.
- **The guard must NEVER return 2 to the session.** `block-idle-stop.sh:66-73` maps observers to exit 1. `CANNOT_RUN` (2) from `--decide` is surfaced by the hook as exit 1.
- **`REPO_ROOT`, not `ROOT`** — `block-idle-stop.sh:23`. There is no `set -u`; `$ROOT` expands to empty and every stop would block.
- **The declared `--self-test` count must equal the printed count.** Declared at `:47` (`# 25 cases`), pinned in `scripts/check-selftest-counts.py` `POPULATION:88`. **Read the printed number and copy it — never guess.** This drifted three times on 2026-09-04.
- **Never re-implement `count_steps`.** Borrow it from `check-plan-progress.py` by path import.
- **No test expecting `QUIET` discriminates a fix** — today's `decide()` returns `QUIET` for every banner-less turn. Only `WARN`, `CANNOT RUN`, or a side effect can.

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `scripts/check-banner-armed.py` | the guard: window, predicate, message, log | Modify — all of Tasks 1-5, 7 |
| `.claude/hooks/block-idle-stop.sh` | Stop-hook wiring and exit-code mapping | Modify — Task 6 |
| `docs/backlog.md` | row 95's falsifier wording | Modify — Task 7 |
| `docs/dashboard-entries.md` | the dashboard entry | Modify — Task 7 |

## ⚠ Two traps found by reading the file. Both bite silently.

**Trap 1 — a new required parameter breaks all 25 existing self-test calls.** They call `decide([...], armed=False)` positionally with no plan info. Adding `steps` with a default of `None` is worse than useless: §4.4 makes `armed and steps is None` mean *CANNOT RUN*, so the existing case at `:257-258` (`decide([B], armed=True)`) would flip from QUIET to CANNOT RUN. **Use a distinct `_UNSET` sentinel** so three states are separable:

| `steps` value | meaning |
|---|---|
| `_UNSET` (default) | the caller did not consult a plan — behave exactly as before |
| `None` | consulted, and the plan is **unreadable or has zero checkboxes** → `CANNOT_RUN` |
| `(done, total)` | consulted successfully |

**Trap 2 — Task 7's wording fix breaks an existing self-test case, by design.** `:255-256` asserts `"Nothing is blocked" in decide(...)[1]`. §2 of the spec requires that string to go. That case must be *rewritten*, not deleted, and its replacement must assert the new wording.

---

### Task 1: One window, two extractors, and `isMeta` stops being a turn boundary

**Files:**
- Modify: `scripts/check-banner-armed.py:73-121` (split the helper), `:288-308` (windowing self-tests)

**Interfaces:**
- Consumes: nothing.
- Produces: `records_since_last_user(lines: list[str]) -> list[dict] | None`, `texts_of(records: list[dict]) -> list[str]`, `edited_paths_of(records: list[dict]) -> list[str]`. `assistant_texts_since_last_user(lines)` is kept as a thin wrapper so existing callers and self-tests are untouched.

- [ ] **Step 1: Write the failing tests**

Add to `_self_test()` in the windowing section (after `:308`):

```python
    def meta(text: str) -> str:
        return json.dumps({"type": "user", "isMeta": True,
                           "message": {"content": text}})

    def notif(text: str) -> str:
        return json.dumps({"type": "user", "promptSource": "system",
                           "message": {"content": text}})

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

    def edit(path: str) -> str:
        return json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Edit", "input": {"file_path": path}}]}})

    case("edited_paths_of finds an Edit's file_path in the window",
         edited_paths_of(records_since_last_user([user("go"), edit("/a/b.py")]) or [])
         == ["/a/b.py"])
    case("edited_paths_of ignores a non-editing tool",
         edited_paths_of([{"type": "assistant", "message": {"content": [
             {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}}]}}]) == [])
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 scripts/check-banner-armed.py --self-test`
Expected: FAIL — `NameError: name 'records_since_last_user' is not defined`.

- [ ] **Step 3: Split the helper and add the isMeta rule**

Replace `assistant_texts_since_last_user` (`:73-104`) with:

```python
def records_since_last_user(lines: list[str]) -> list[dict] | None:
    """Records emitted after the most recent REAL user message. None if unparseable.

    Two kinds of `user` record are not the human typing, and treating them as turn
    boundaries truncates the window:
      * a tool RESULT — already handled; without this, the window is cut at the last tool call.
      * an `isMeta` record — a skill injection, or THIS HOOK's own `⛔ DO NOT STOP` feedback.
        Measured 2026-09-04: the block message sat 72 records after the `STEP 2 of 4` banner
        for the step still in progress, so the banner fell out of window by construction.

    ⚠ `promptSource` is deliberately NOT part of this rule. Measured over 30 transcripts:
    skipping it too collapses 142 windows to 70, and 52 of the 72 removed boundaries begin a
    GENUINELY NEW turn — 27 are `<task-notification>` records, which check-plan-progress.py:28-36
    calls "a FRESH turn" in its own words. A window that never resets is as wrong as one that
    resets too often.
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
    reviewers measured, so its key name is a guess and is labelled as one. `MultiEdit` is
    absent from this list because it does not exist in this runtime (measured x0 by both
    halves of round 1); adding it would be dead code with a self-test asserting behaviour
    nothing can emit.
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
    """Back-compat wrapper: the text half of the window. Kept so existing callers are unchanged."""
    records = records_since_last_user(lines)
    return None if records is None else texts_of(records)
```

- [ ] **Step 4: Run to verify they pass**

Run: `python3 scripts/check-banner-armed.py --self-test`
Expected: all cases PASS. The 25 pre-existing cases must still pass — the wrapper preserves their behaviour.

- [ ] **Step 5: Commit**

```bash
git add scripts/check-banner-armed.py
git commit -m "One transcript window, two extractors, and the hook's own block message stops truncating it"
```

---

### Task 2: A paused plan is not armed

**Files:**
- Modify: `scripts/check-banner-armed.py:180-188` (`_armed`)

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `_armed()` returns `False` when the sentinel carries a `paused:` key.

- [ ] **Step 1: Write the failing test**

`_armed()` reads a real file, so test the parsing rule directly. Add a pure helper and test it:

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
Expected: FAIL — `NameError: name '_armed_from_text' is not defined`.

- [ ] **Step 3: Extract the rule and add the paused clause**

```python
def _armed_from_text(text: str) -> bool:
    """PURE. True iff the sentinel names a plan AND has not been stood down.

    `paused:` is honoured because check-plan-progress.decide() honours it — the two must agree
    about what "armed" means, or this guard's principal firing state becomes the one documented
    escape. begin-plan.py:56-61: --pause is for being legitimately BLOCKED ON IN-FLIGHT WORK,
    a dispatched review or a CI run. It fired three times in one session (backlog #94).
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
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/check-banner-armed.py
git commit -m "A paused plan stands down here too, not only in the guard that blocks"
```

---

### Task 3: Borrow the plan decision by path, and report blindness unconditionally

**Files:**
- Modify: `scripts/check-banner-armed.py` — add `_load_plan_progress()` + `_plan_steps()` near the I/O shell; add the `CANNOT_RUN` hoist to `decide()` (`:139-155`)

**Interfaces:**
- Consumes: `_armed()` from Task 2.
- Produces: `decide(texts, armed, steps=_UNSET, edited=False)`; `_plan_steps() -> tuple[int,int] | None`.

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
    case("the default _UNSET means 'not consulted' and changes nothing",
         decide([B.format(2, 5)], armed=True)[0] == QUIET)
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 scripts/check-banner-armed.py --self-test`
Expected: FAIL — `decide() got an unexpected keyword argument 'steps'`.

- [ ] **Step 3: Add the loader, the sentinel, and the hoist**

Add near the top, after `QUIET, WARN, CANNOT_RUN = 0, 1, 2`:

```python
_UNSET = object()   # `steps` was not consulted. Distinct from None, which means "unreadable".
```

Add to the I/O shell:

```python
def _load_plan_progress():
    """Import check-plan-progress.py BY PATH — the hyphen makes it un-importable by name.

    ⚠ Called from the I/O SHELL, not module scope. begin-plan.py raises at import because it
    does nothing without these names; this guard's banner-without-plan rule needs them not at
    all, so a rename must not kill the working half with a traceback instead of this file's own
    TREAT THIS AS NOT RUN vocabulary (see the module docstring).

    ⚠ A second small loader now exists (begin-plan.py:89-103 has the first). That is accepted:
    a loader cannot drift SILENTLY — it either loads or raises. The rule worth protecting from
    duplication is count_steps' SEMANTICS, which drift quietly and yield two different counts.
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
    """-> (done, total), or None if the plan cannot be measured. Never raises.

    None covers BOTH "no readable plan file" and "zero checkboxes parsed". The owning guard
    treats zero checkboxes as CANNOT RUN (check-plan-progress.py:113-118), not as "finished",
    and this guard must agree — importing the counter while re-deriving a different meaning
    from its return value is the shared-function-holding-half-a-contract shape.

    A path import of a renamed file raises FileNotFoundError, not ImportError, and exec_module
    can surface SyntaxError — so the catch is deliberately wide.
    """
    try:
        mod = _load_plan_progress()
        fields = mod.parse_sentinel(SENTINEL.read_text())
        plan = (ROOT / fields["plan"]).resolve()
        done, total = mod.count_steps(plan.read_text())
        return None if total == 0 else (done, total)
    except (ImportError, OSError, SyntaxError, KeyError, AttributeError, ValueError):
        return None
```

Add `import importlib.util` to the imports. Then change `decide`'s signature and add the hoist as its **second** statement, immediately after the `texts is None` check:

```python
def decide(texts, armed, steps=_UNSET, edited=False):
    """-> (exit_code, message). Pure: every input is passed in."""
    if texts is None:
        return CANNOT_RUN, (...)                    # unchanged

    # Blindness is a property of the sentinel and the plan file, NOT of whether the assistant
    # happened to type a heading — so it is answered before the banner is even looked at.
    if armed and steps is None:
        return CANNOT_RUN, (
            "CANNOT RUN: .claude/executing-plan names a plan this check could not measure — "
            "missing, unreadable, or containing zero `- [ ]` step checkboxes. TREAT THIS AS "
            "NOT RUN — do not read the absence of a warning as 'a banner was not owed'.")
```

- [ ] **Step 4: Run to verify they pass**

Run: `python3 scripts/check-banner-armed.py --self-test`
Expected: all PASS, including all 25 originals — `_UNSET` keeps them on the old path.

- [ ] **Step 5: Commit**

```bash
git add scripts/check-banner-armed.py
git commit -m "Borrow the plan DECISION, not just its counter, and answer blindness first"
```

---

### Task 4: The branch that was the point

**Files:**
- Modify: `scripts/check-banner-armed.py` — `decide()`'s `banner is None` arm; add `_edit_inside_repo()`

**Interfaces:**
- Consumes: `_UNSET`/`steps` from Task 3, `edited_paths_of` from Task 1.
- Produces: the WARN branch; `_edit_inside_repo(paths: list[str], root: Path) -> bool`.

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

    # R1-R4 — regression guards, each naming the mutation it catches
    case("R1 armed + work left + NO edit -> quiet (catches `edited` hardcoded true)",
         decide([], armed=True, steps=S, edited=False)[0] == QUIET)
    case("R2 not armed + an edit -> quiet (catches dropping the armed term)",
         decide([], armed=False, steps=S, edited=True)[0] == QUIET)
    case("R4 a banner IS present -> the existing branches decide (catches a reorder)",
         decide([B.format(2, 4)], armed=True, steps=S, edited=True)[0] == QUIET)
    case("a finished plan (0 unticked) + an edit -> quiet",
         decide([], armed=True, steps=(4, 4), edited=True)[0] == QUIET)

    # R3 — the path scope
    root = Path("/repo")
    case("R3 an edit outside the repo does not count (the scratchpad case)",
         _edit_inside_repo(["/tmp/scratch/x.md"], root) is False)
    case("a relative path is REFUSED — nothing records the cwd it was relative to",
         _edit_inside_repo(["docs/x.md"], root) is False)
    case("a sibling checkout does not prefix-match (/repo-old is not inside /repo)",
         _edit_inside_repo(["/repo-old/x.md"], root) is False)
    case("a .git write is not plan work",
         _edit_inside_repo(["/repo/.git/COMMIT_EDITMSG"], root) is False)
    case("an ordinary repo file counts",
         _edit_inside_repo(["/repo/scripts/x.py"], root) is True)
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 scripts/check-banner-armed.py --self-test`
Expected: FAIL — `_edit_inside_repo` undefined; F1 returns QUIET, not WARN.

- [ ] **Step 3: Implement**

```python
def _edit_inside_repo(paths: list[str], root: Path) -> bool:
    """PURE. True iff any path is a file inside `root` that counts as plan work.

    `is_relative_to`, never str.startswith: a sibling checkout named `<root>-old` prefix-matches.
    Relative paths are REFUSED rather than resolved against this process's cwd — measured, the
    Edit/Write tool inputs record only file_path, never the cwd it was relative to, so resolving
    one would be a guess.

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
        if ".git" in resolved.relative_to(root).parts[:1]:
            continue
        return True
    return False
```

In `decide()`, replace the `banner is None` arm:

```python
    banner = highest_banner(texts)
    if banner is None:
        unticked = 0 if steps in (_UNSET, None) else steps[1] - steps[0]
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

Wire the shell — in `run_decide`, replace the `decide(texts, _armed())` call:

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
    code, message = decide(
        texts, armed,
        steps=_plan_steps() if armed else _UNSET,
        edited=_edit_inside_repo(edited_paths_of(records or []), ROOT))
```

- [ ] **Step 4: Run to verify they pass**

Run: `python3 scripts/check-banner-armed.py --self-test`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/check-banner-armed.py
git commit -m "The direction that actually failed: a plan armed, work done, and no banner"
```

---

### Task 5: The new class must reach the log

**Files:**
- Modify: `scripts/check-banner-armed.py:173-175` (`log_line`), `:207-219` (the gate), `:311-313` (its self-test)

**Interfaces:**
- Consumes: the WARN branch from Task 4.
- Produces: `log_line(reason: str, detail: str, when: str, session: str) -> str`.

- [ ] **Step 1: Write the failing tests**

Replace the existing log case at `:311-313` and add:

```python
    case("the log line is tab-separated and states the state and the detail",
         log_line("unarmed", "STEP 2 of 5", "2026-09-04T07:00:00-07:00", "sess").split("\t")[1:]
         == ["sess", "unarmed", "STEP 2 of 5\n"])
    # F4 — discriminating: the new class is recordable at all
    case("F4 the banner-less class has a log shape — 3 unticked, no banner",
         log_line("unbannered", "3 unticked", "2026-09-04T07:00:00-07:00", "s").split("\t")[2]
         == "unbannered")
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 scripts/check-banner-armed.py --self-test`
Expected: FAIL — `log_line()` takes `(step, total, when, session)`.

- [ ] **Step 3: Widen the log and drop the `if banner:` gate**

```python
def log_line(reason: str, detail: str, when: str, session: str) -> str:
    """One appended record. Tab-separated so the log stays greppable and countable.

    `reason` discriminates the two warning classes. The banner-less class has NO banner by
    construction, so the previous shape — which took (step, total) and was written only when a
    banner existed — could never record it. The log is the evidence for whether this should
    ever block, so a class it cannot express is a class that reads as never having fired.

    Nothing parses this file (searched 2026-09-04: the only references are this module, its
    self-test, a comment in block-idle-stop.sh, and prose in docs/dashboard-entries.md), so the
    column change breaks no reader.
    """
    return f"{when}\t{session or '-'}\t{reason}\t{detail}\n"
```

In `run_decide`, replace the logging block:

```python
    if code == WARN:
        banner = highest_banner(texts or [])
        if banner:
            reason, detail = "unarmed", f"STEP {banner[0]} of {banner[1]}"
        else:
            unticked = 0 if steps in (_UNSET, None) else steps[1] - steps[0]
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

⚠ `steps` must be in scope here — hoist it to a local in `run_decide` before the `decide()` call.

- [ ] **Step 4: Run to verify they pass**

Run: `python3 scripts/check-banner-armed.py --self-test`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/check-banner-armed.py
git commit -m "The log learns a second class, so 'it never fires' stops being unfalsifiable"
```

---

### Task 6: Make it reachable — move ONE observer

**Files:**
- Modify: `.claude/hooks/block-idle-stop.sh:39-73`
- Modify: `scripts/check-banner-armed.py` — add the F6 structural test

**Interfaces:**
- Consumes: everything above.
- Produces: `check-banner-armed.py` runs before the blocking check.

- [ ] **Step 1: Write the failing test (F6)**

```python
    # F6 — REACHABILITY. v1 shipped an unreachable branch and every falsifier passed, because a
    # suite over a pure core cannot see its own unreachability.
    #
    # ⚠ THIS IS A STRUCTURAL TEST, NOT AN EXECUTION TEST. Nothing here executes a shell hook:
    # running block-idle-stop.sh would unlink the live sentinel, write the live state file, make
    # a live `gh` call and append to the real warnings log, and REPO_ROOT comes from BASH_SOURCE
    # so it cannot be pointed at a fixture. F6 proves ORDER IN THE FILE and nothing more — it
    # would not catch the hook being unreadable, python3 being absent, or stdin not arriving.
    hook = (ROOT / ".claude/hooks/block-idle-stop.sh").read_text()
    case("F6 the banner guard is invoked BEFORE the blocking check's exit 2",
         hook.index("check-banner-armed.py") < hook.index("exit 2"))
    case("F6b the hook uses REPO_ROOT — $ROOT is empty and would block every stop",
         "$ROOT/scripts" not in hook)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 scripts/check-banner-armed.py --self-test`
Expected: F6 FAILS — today `check-banner-armed.py` appears at `:54`, after the `exit 2` at `:40`.

- [ ] **Step 3: Move the invocation**

In `.claude/hooks/block-idle-stop.sh`, move the banner block to **before** the `check-plan-progress` call and capture its code:

```bash
# ── Observer, deliberately AHEAD of the blocking check ───────────────────────────────────────
# It must run in the very state that check REFUSES: armed with unticked steps. Ordering is free
# because it cannot block — and it is REQUIRED, because check-plan-progress.run_decide UNLINKS
# .claude/executing-plan when the last step is ticked, so running after it reads a deleted
# sentinel. Who reads this warning depends on the exit code, and both readers are correct:
# a blocked stop exits 2 and Claude reads it (the actor, when the next banner is due); an
# unblocked stop exits 1 and the human reads it (the auditor, when nothing is left to correct).
printf '%s' "$INPUT" | python3 "$REPO_ROOT/scripts/check-banner-armed.py" --decide
BANNER_RC=$?

if ! python3 "$REPO_ROOT/scripts/check-plan-progress.py" "${ARGS[@]}"; then
    exit 2
fi
```

Leave the `check-ci-watched.py` block exactly where it is, and delete the now-duplicated banner block from its old position. The final exit arithmetic is unchanged.

- [ ] **Step 4: Run to verify it passes**

Run: `python3 scripts/check-banner-armed.py --self-test`
Expected: all PASS.
Then: `bash -n .claude/hooks/block-idle-stop.sh` — Expected: no output (syntax OK).

- [ ] **Step 5: Commit**

```bash
git add .claude/hooks/block-idle-stop.sh scripts/check-banner-armed.py
git commit -m "The observer runs in the state the blocking check refuses, which is the only state it is for"
```

---

### Task 7: The four things that become false, and the entry

**Files:**
- Modify: `scripts/check-banner-armed.py:30-48` (docstring + declared count), `:255-256` (the wording case)
- Modify: `docs/backlog.md` row 95; `docs/dashboard-entries.md`

- [ ] **Step 1: Fix the "Nothing is blocked" claim in the OLD message and its test**

The existing message at `:161` says *"Nothing is blocked."* That can be false: a sentinel with **no `plan:` line** makes `_armed()` return `False` (so this branch fires) while `check-plan-progress` takes its CANNOT-RUN path and blocks. Replace the sentence with `"This does not block your stop by itself."` and rewrite the case at `:255-256`:

```python
    case("...and it does not claim nothing is blocked — another check may be blocking",
         "does not block your stop by itself" in decide([B.format(2, 5)], armed=False)[1])
```

- [ ] **Step 2: Rewrite the docstring's WHAT IT CANNOT SEE block**

Lines `:35-37` currently state this gap as a known limitation, which is now false. Replace with the §9 list: subagent edits (0 `isSidechain:true` across 508 transcripts, and subagent-driven development is the Phase 3 default), `Bash`-only work, worktrees, F6 being structural, banner quality, and work with no plan armed.

- [ ] **Step 3: Update the declared self-test count**

Run: `python3 scripts/check-banner-armed.py --self-test`
**Read the printed `N/N` and copy that number** into the usage line at `:47` (`# 25 cases`). Do **not** compute it by adding — the declared count drifted three separate times on 2026-09-04, and `scripts/check-selftest-counts.py` will fail CI on a mismatch.

Then: `python3 scripts/check-selftest-counts.py` — Expected: PASS.

- [ ] **Step 4: Reword the backlog falsifier and add the dashboard entry**

In `docs/backlog.md` row 95, change *"edits a **tracked** file"* to *"edits a file inside the repo"* — the predicate and its falsifier must not disagree. Mark the row ✅ with how it was settled.

Add a dashboard entry recording: the two review rounds, the unreachability that killed v1, the two-reader decision, and that **`check-ci-watched.py` was deliberately left unreachable on blocked stops** with the measured reason — a reader would not infer that from the row title.

- [ ] **Step 5: Run every gate, then commit**

```bash
python3 scripts/check-banner-armed.py --self-test
python3 scripts/check-selftest-counts.py
python3 scripts/check-docs.py
python3 scripts/check-anchors.py
python3 scripts/check-dashboard-entry.py
python3 scripts/check-ratchet-contract.py
git add -A && git commit -m "Close backlog #95: the guard, the reachability, and the four claims that went stale"
```

## Self-Review

**Spec coverage:** §2 two-reader contract → T6 comment + T4 message + T7 wording. §4.1 hook → T6. §4.2 paused → T2. §4.3 borrow/import → T3. §4.4 hoist → T3. §4.5 window → T1. §4.6 inputs → T1 + T4. §4.7 path → T4. §5 F1-F6/R1-R6 → T1-T6. §7 log → T5. §8 bookkeeping → T7. §9 blind spots → T7 Step 2. **No gaps.**

**Placeholder scan:** every code step carries real code; no TBD, no "similar to Task N".

**Type consistency:** `steps` is `tuple[int,int] | None | _UNSET` in T3, T4, T5 — consistent. `log_line(reason, detail, when, session)` defined in T5 and used only there. `records_since_last_user`/`texts_of`/`edited_paths_of` defined in T1, consumed in T4's `run_decide`. `_edit_inside_repo(paths, root)` defined and used in T4.

**Known ordering constraint:** T4 depends on T1 and T3; T5 depends on T4 (and needs `steps` hoisted into `run_decide`'s scope); T6 depends on nothing but is placed last so the guard is correct before it becomes reachable.
