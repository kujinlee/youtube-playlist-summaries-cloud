#!/usr/bin/env python3
"""Guard the handoff skill's SAVE PATH against a vendor update that silently reverts it.

WHY THIS FILE EXISTS (measured 2026-08-27).
  `/handoff` upstream saves to `mktemp -t handoff-XXXXXX.md`. That path is unreachable on resume:
  random suffix, outside the repo, unindexed. THREE such files accumulated in $TMPDIR and NOT ONE
  was ever read by a resuming session. The documents were good; they had no consumer — the same
  defect class as the "live gate with NO CALLER" this repo has now hit four times.

  The fix pointed the skill at `.remember/remember.md`, which the `remember` plugin's SessionStart
  hook already injects as `=== LAST HANDOFF ===`, ahead of identity and memory.

  ⚠ THAT FIX LIVES IN A VENDORED FILE. `npx skills@latest add mattpocock/skills` overwrites it.
  The first version of this guard was a SENTENCE in docs/plugins.md saying "if a resume ever finds a
  handoff-XXXXXX.md in $TMPDIR, the skill was overwritten". That is a LAGGING falsifier: it fires
  only after a session has already lost its handoff. This script is the LEADING one — it fires at
  the moment `/handoff` is invoked, before anything is written.

WHAT WOULD MAKE THIS FAIL (the gate's own falsifier, per CLAUDE.md):
  `.agents/skills/handoff/SKILL.md` stops naming `.remember/remember.md`.

WHY THE RULE IS "MUST NAME THE PATH" AND NOT "MUST NOT MENTION mktemp":
  The repaired skill mentions `mktemp` twice on purpose — once naming what upstream does and why it
  is wrong, once preserving it for the legitimate mid-task-subagent case. A "no mktemp" rule would
  fire on the corrected file. The presence of the consumed path is the property that matters, and a
  reverted vendor file cannot have it.

EXIT CODES (repo convention): 0 = compliant · 1 = REVERTED · 2 = CANNOT RUN (never a pass).
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_REL = ".agents/skills/handoff/SKILL.md"

# The path the remember plugin's SessionStart hook actually reads:
#   session-start-hook.sh:795  REMEMBER_HANDOFF="$REMEMBER_DIR/remember.md"
# Verified by EXECUTING that hook, not by reading it — the `=== LAST HANDOFF ===` block came out
# first, ahead of `=== REMEMBER ===` and `=== MEMORY ===`.
CONSUMED_PATH = ".remember/remember.md"


def check_text(text: str) -> list[str]:
    """Return a list of violations for the given SKILL.md body. Empty list == compliant."""
    violations: list[str] = []
    if CONSUMED_PATH not in text:
        violations.append(
            f"SKILL.md does not name {CONSUMED_PATH} — the only path the SessionStart hook reads. "
            f"A handoff written anywhere else has no consumer."
        )
    return violations


def check_file(path: Path) -> tuple[int, list[str]]:
    """Return (exit_code, messages). Missing/unreadable is CANNOT RUN, never a pass."""
    if not path.exists():
        return 2, [f"CANNOT RUN — {path} does not exist. Treat this as NOT RUN, not as a pass."]
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return 2, [f"CANNOT RUN — cannot read {path}: {exc}. Treat this as NOT RUN."]
    if not text.strip():
        return 2, [f"CANNOT RUN — {path} is empty. Treat this as NOT RUN."]

    violations = check_text(text)
    return (1 if violations else 0), violations


# ── self-test ────────────────────────────────────────────────────────────────
GOOD = f"Save it to `{CONSUMED_PATH}` in the project root.\nException: use `mktemp` for subagents.\n"
UPSTREAM = "Save it to a path produced by `mktemp -t handoff-XXXXXX.md`.\n"

CASES = [
    ("repaired skill (names the path)", GOOD, 0),
    ("repaired skill also mentioning mktemp twice", GOOD + UPSTREAM, 0),
    ("pristine upstream — the reversion this exists to catch", UPSTREAM, 1),
    ("path mentioned with no mktemp at all", f"Write to {CONSUMED_PATH}\n", 0),
    ("near-miss: .remember/handoff.md (nothing reads it)", "Save to `.remember/handoff.md`\n", 1),
    ("near-miss: remember.md without the directory", "Save to `remember.md`\n", 1),
    ("empty body", "", 1),
]


def self_test() -> int:
    failures = 0
    print(f"check-handoff-path --self-test  ({len(CASES)} text cases + 3 file cases)")
    for name, text, expected in CASES:
        got = 1 if check_text(text) else 0
        ok = got == expected
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: expected {expected}, got {got}")

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        missing = tmp / "nope.md"
        code, _ = check_file(missing)
        ok = code == 2
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] missing file is CANNOT RUN (2), got {code}")

        empty = tmp / "empty.md"
        empty.write_text("", encoding="utf-8")
        code, _ = check_file(empty)
        ok = code == 2
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] empty file is CANNOT RUN (2), got {code}")

        good = tmp / "good.md"
        good.write_text(GOOD, encoding="utf-8")
        code, _ = check_file(good)
        ok = code == 0
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] compliant file exits 0, got {code}")

    print("PASS" if not failures else f"FAIL — {failures} case(s)")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true", help="run the case suite and exit")
    ap.add_argument("--quiet", action="store_true", help="print only on violation")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    path = REPO_ROOT / SKILL_REL
    code, messages = check_file(path)

    if code == 0:
        if not args.quiet:
            print(f"ok — {SKILL_REL} names {CONSUMED_PATH}")
        return 0

    label = "CANNOT RUN" if code == 2 else "REVERTED"
    print(f"{label} — {SKILL_REL}", file=sys.stderr)
    for m in messages:
        print(f"  {m}", file=sys.stderr)
    if code == 1:
        print(
            "\nA vendor update (`npx skills@latest add mattpocock/skills`) most likely overwrote it.\n"
            "Re-apply: the skill must save to .remember/remember.md, keeping mktemp only for the\n"
            "mid-task-subagent case. See docs/plugins.md → Session Handoff.",
            file=sys.stderr,
        )
    return code


if __name__ == "__main__":
    sys.exit(main())
