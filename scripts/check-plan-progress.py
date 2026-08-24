#!/usr/bin/env python3
"""Decide whether the session may STOP while a plan is still being executed.

WHY THIS EXISTS (measured 2026-08-24, third occurrence). The failure is not forgetting the plan —
it is that a *reporting boundary* gets treated as a *turn boundary*. A summary is written, its last
sentence names the next task, and the turn ends: the intention to do that task exists only in prose
that was just emitted, and nothing carries it across the boundary. The memory
`act-then-report-never-close-with-a-promise` recorded exactly this on 2026-08-19/20 and it recurred.
A third prose rule is definitionally the wrong fix — a convention catches what you read; a script
catches what is there.

The mechanism is copied from a gate this repo already proved: `.claude/hooks/check-plan-gate.sh`
arms `.claude/plan-gate-pending`, and a PreToolUse hook refuses to dispatch implementation while it
exists. This is the same shape one phase later, on Stop.

GROUND TRUTH IS THE PLAN'S OWN CHECKBOXES, not a self-reported progress note. The plan header says
"Steps use checkbox (`- [ ]`) syntax for tracking"; this makes that load-bearing instead of
decorative. Nothing here trusts a summary.

FAILS CLOSED. A missing plan, or a plan that parses to zero steps, BLOCKS with "TREAT THIS AS NOT
RUN" rather than allowing the stop — a check that cannot reach what it measures is a failure, never
a pass (CLAUDE.md). The cost of that choice is one nagging block, and the escape is one command.

IT CANNOT TRAP THE SESSION. It blocks only while blocking is *producing progress*: if a block goes
by and the unticked count has not fallen, the next stop is allowed. Deleting the sentinel, or adding
a `paused:` line to it, also allows it immediately.

Usage (the hook calls form 1; a human can call form 2 to see where things stand):
    python3 scripts/check-plan-progress.py --decide [--stop-hook-active]
    python3 scripts/check-plan-progress.py --status
    python3 scripts/check-plan-progress.py --self-test
Exit codes for --decide:  0 = allow the stop   2 = block it (message on stderr)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SENTINEL = ROOT / ".claude/executing-plan"
STATE = ROOT / ".claude/executing-plan.state"

ALLOW, BLOCK = 0, 2

_STEP_RE = re.compile(r"^- \[( |x)\] ", re.M)
_TASK_RE = re.compile(r"^### (Task \d+:.*)$", re.M)


def parse_sentinel(text: str) -> dict[str, str]:
    """`key: value` lines. Unknown keys are kept — the file is also read by humans."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def count_steps(plan_text: str) -> tuple[int, int]:
    """-> (done, total) over `- [ ]` / `- [x]` step checkboxes."""
    marks = _STEP_RE.findall(plan_text)
    return sum(1 for m in marks if m == "x"), len(marks)


def next_pending_task(plan_text: str) -> str:
    """The `### Task N:` heading that owns the first unticked step, for a useful message."""
    current = "(before the first task heading)"
    for line in plan_text.splitlines():
        m = _TASK_RE.match(line)
        if m:
            current = m.group(1)
        elif line.startswith("- [ ] "):
            return current
    return "(none)"


def decide(
    sentinel_text: str | None,
    plan_text: str | None,
    prev_unticked: int | None,
    stop_hook_active: bool,
) -> tuple[int, str, int | None]:
    """-> (exit_code, message, unticked_to_record). Pure: every input is passed in."""
    if sentinel_text is None:
        return ALLOW, "", None

    fields = parse_sentinel(sentinel_text)
    if "paused" in fields:
        return ALLOW, "", None

    plan = fields.get("plan", "(no `plan:` line in the sentinel)")

    if plan_text is None:
        return BLOCK, (
            f"CANNOT RUN: the executing-plan sentinel names `{plan}`, which does not exist. "
            "TREAT THIS AS NOT RUN — this check cannot tell you whether work remains. "
            f"Fix the path or delete {SENTINEL.relative_to(ROOT)}."
        ), None

    done, total = count_steps(plan_text)
    if total == 0:
        return BLOCK, (
            f"CANNOT RUN: parsed ZERO step checkboxes from `{plan}`. Either the plan's shape "
            "changed or this parser is broken. TREAT THIS AS NOT RUN — do not read the absence of "
            "a warning as 'no work left'."
        ), None

    unticked = total - done
    if unticked == 0:
        return ALLOW, (
            f"✅ every step in `{plan}` is ticked ({done}/{total}). "
            f"Clearing {SENTINEL.relative_to(ROOT)}."
        ), 0

    # Anti-nag: only keep blocking while blocking is producing progress. If a block has already
    # fired and the unticked count has not fallen since, let the stop through — a hook that can
    # trap a session gets disabled, and a disabled hook protects nothing.
    if stop_hook_active and prev_unticked is not None and unticked >= prev_unticked:
        return ALLOW, "", unticked

    return BLOCK, (
        f"⛔ DO NOT STOP — {unticked} of {total} steps are unticked in `{plan}`.\n"
        f"   Next: {next_pending_task(plan_text)}\n"
        "\n"
        "   You are mid-plan. Continue with the next task rather than ending the turn on a\n"
        "   summary — a summary is not a stopping condition, and the intention to 'do X next'\n"
        "   does not survive the turn boundary (measured three times; see this script's docstring).\n"
        "   Tick each `- [ ]` as you complete it: those checkboxes are what this check reads.\n"
        "\n"
        "   Legitimately need to stop? Do ONE of:\n"
        f"     • the plan is finished          → tick the remaining steps\n"
        f"     • handing back to the human     → add a line `paused: <why>` to "
        f"{SENTINEL.relative_to(ROOT)}\n"
        f"     • the plan is abandoned         → rm {SENTINEL.relative_to(ROOT)}"
    ), unticked


# ── I/O shell around the pure decision ────────────────────────────────────────────────────────

def _read(p: Path) -> str | None:
    try:
        return p.read_text()
    except OSError:
        return None


def run_decide(stop_hook_active: bool) -> int:
    sentinel_text = _read(SENTINEL)
    plan_text = None
    if sentinel_text is not None:
        plan_rel = parse_sentinel(sentinel_text).get("plan", "")
        if plan_rel:
            plan_text = _read(ROOT / plan_rel)

    prev = None
    prev_raw = _read(STATE)
    if prev_raw and prev_raw.strip().isdigit():
        prev = int(prev_raw.strip())

    code, message, unticked = decide(sentinel_text, plan_text, prev, stop_hook_active)

    if unticked == 0:
        SENTINEL.unlink(missing_ok=True)
        STATE.unlink(missing_ok=True)
    elif unticked is not None:
        STATE.write_text(str(unticked))

    if message:
        print(message, file=sys.stderr if code == BLOCK else sys.stdout)
    return code


def run_status() -> int:
    sentinel_text = _read(SENTINEL)
    if sentinel_text is None:
        print("no plan is being executed (no .claude/executing-plan)")
        return 0
    fields = parse_sentinel(sentinel_text)
    plan_rel = fields.get("plan", "")
    plan_text = _read(ROOT / plan_rel) if plan_rel else None
    if plan_text is None:
        print(f"CANNOT RUN: sentinel names `{plan_rel}`, which does not exist.")
        return 2
    done, total = count_steps(plan_text)
    print(f"{plan_rel}: {done}/{total} steps ticked, {total - done} remaining")
    if total - done:
        print(f"next: {next_pending_task(plan_text)}")
    if "paused" in fields:
        print(f"PAUSED: {fields['paused']}")
    return 0


# ── Self-test ─────────────────────────────────────────────────────────────────────────────────

def _self_test() -> int:
    cases: list[tuple[str, bool]] = []

    def case(name: str, ok: bool) -> None:
        cases.append((name, ok))
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")

    PLAN = (
        "### Task 1: A\n\n- [x] **Step 1**\n\n- [x] **Step 2**\n\n"
        "### Task 2: B\n\n- [x] **Step 1**\n\n- [ ] **Step 2**\n\n"
        "### Task 3: C\n\n- [ ] **Step 1**\n"
    )
    SENT = "plan: docs/superpowers/plans/p.md\narmed: 2026-08-24T00:00:00Z\n"

    case("no sentinel -> allow", decide(None, PLAN, None, False)[0] == ALLOW)
    case("paused sentinel -> allow", decide(SENT + "paused: waiting on the user\n", PLAN, None, False)[0] == ALLOW)

    code, msg, _ = decide(SENT, None, None, False)
    case("missing plan -> BLOCK, fails closed", code == BLOCK and "TREAT THIS AS NOT RUN" in msg)

    code, msg, _ = decide(SENT, "# a plan with no checkboxes at all\n", None, False)
    case("zero steps parsed -> BLOCK, fails closed", code == BLOCK and "TREAT THIS AS NOT RUN" in msg)

    code, msg, unticked = decide(SENT, PLAN, None, False)
    case("unticked steps -> BLOCK", code == BLOCK)
    case("block message counts correctly (2 of 5)", "2 of 5 steps are unticked" in msg)
    case("block message names the NEXT task, not the first", "Task 2: B" in msg)
    case("block records the unticked count", unticked == 2)
    case("block message states all three escapes",
         "paused:" in msg and "rm " in msg and "tick the remaining steps" in msg)

    all_done = PLAN.replace("- [ ]", "- [x]")
    code, msg, unticked = decide(SENT, all_done, None, False)
    case("all steps ticked -> allow and clear", code == ALLOW and unticked == 0 and "Clearing" in msg)

    # Anti-nag: a block that produced no progress must not block again.
    case("no progress since the last block + stop_hook_active -> allow",
         decide(SENT, PLAN, 2, True)[0] == ALLOW)
    case("PROGRESS since the last block -> block again (the loop continues)",
         decide(SENT, PLAN, 3, True)[0] == BLOCK)
    case("stop_hook_active alone does NOT disarm it on a first block",
         decide(SENT, PLAN, None, True)[0] == BLOCK)

    case("count_steps counts both marks", count_steps(PLAN) == (3, 5))
    case("a `- [ ]` inside prose still counts (deliberate: no false ALLOW)",
         count_steps("- [ ] stray\n")[1] == 1)
    case("next_pending_task before any heading is labelled, not crashed",
         next_pending_task("- [ ] orphan\n").startswith("(before"))
    case("parse_sentinel keeps unknown keys",
         parse_sentinel("plan: x\nfoo: bar\n") == {"plan": "x", "foo": "bar"})

    passed = sum(1 for _, ok in cases if ok)
    print(f"\n{passed}/{len(cases)} self-test cases passed")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--decide", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--stop-hook-active", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(_self_test())
    if a.status:
        sys.exit(run_status())
    if a.decide:
        sys.exit(run_decide(a.stop_hook_active))
    sys.exit(run_status())
