#!/usr/bin/env python3
"""RATCHET: the explain-diff retire decision has a deadline, and this is what makes it arrive.

WHY THIS EXISTS — round-2 Blocking, 2026-08-12.

`docs/explainer-spec.md` ships a skill on an admittedly UNMEASURED premise, and the only thing making
that defensible is a retire condition: re-examine by a date, delete the skill unless it has earned its
keep. A reviewer called that condition **decorative**, correctly: nothing counted the explainers and
nothing fired on the date. A dated promise with no alarm is not a gate, it is a note.

WHAT WAS CONSIDERED AND REJECTED. A scheduled cloud agent. Rejected on two measured grounds: cloud
routines run in Anthropic's cloud with no access to the user's machine, so one could never see
`~/explainers/`; and repo access for the routine was unverified at setup time. An alarm whose ability
to run is unproven is the fail-open shape this project keeps finding.

THE DATE IS PARSED, NOT HARDCODED — deliberately.
The deadline lives in `docs/roadmap-to-launch.md`, in the checkbox a human ticks to record the
decision. Hardcoding a copy here would create two dates that can drift, and a checker asserting a
deadline the roadmap no longer states is worse than no checker. So the date is read from the line, and
if the line stops matching, that is a FAILURE (below) rather than a silent pass. Sort a check's config
by what happens when it goes stale: hardcode what announces its own wrongness, derive the rest.

WHAT THIS CAN AND CANNOT DO — read before trusting a green run.
It checks ONE thing: has the deadline arrived with the decision still unrecorded? It CANNOT count the
explainers in `~/explainers/` — CI has no access to that directory, and neither would any cloud agent.
It therefore cannot evaluate the "5 explainers" half of the condition, and cannot judge whether the
four criteria were met. **That judgement is the human's, and this only guarantees they are asked.**

Exit semantics:
    0  decision recorded (checkbox ticked), or the deadline is still in the future
    0  + a warning, inside the notice window before the deadline
    1  deadline reached and the checkbox is still unticked
    1  cannot find or parse the checkbox — treat this as NOT RUN

Usage:
    python3 scripts/check-explainer-retire-due.py
    python3 scripts/check-explainer-retire-due.py --today 2026-10-01   # simulate a date
    python3 scripts/check-explainer-retire-due.py --self-test
"""
from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROADMAP = ROOT / "docs" / "roadmap-to-launch.md"
SPEC = "docs/explainer-spec.md"
NOTICE_DAYS = 7  # nag before it blocks, so the deadline is never a surprise

# The checkbox that records the decision. Matches ticked or unticked, and captures both.
RETIRE_RE = re.compile(
    r"^- \[( |x|X)\] \*\*Re-examine after .*?on (\d{4}-\d{2}-\d{2})", re.M
)


def find_retire_item(text: str) -> tuple[bool, dt.date] | None:
    m = RETIRE_RE.search(text)
    if not m:
        return None
    return (m.group(1).lower() == "x", dt.date.fromisoformat(m.group(2)))


def run(today: dt.date) -> int:
    if not ROADMAP.exists():
        print(f"❌ {ROADMAP.relative_to(ROOT)} is missing — treat this as NOT RUN.")
        return 1

    found = find_retire_item(ROADMAP.read_text(encoding="utf-8"))
    if found is None:
        print(
            "❌ could not find the explain-diff retire checkbox in "
            f"{ROADMAP.relative_to(ROOT)} — treat this as NOT RUN.\n"
            "   Expected a line of the form:\n"
            "     - [ ] **Re-examine after N explainers or on YYYY-MM-DD, …**\n"
            f"   If the experiment was retired, delete this checker too. If it was renamed, fix the\n"
            f"   pattern here. Do not leave a checker that cannot see its own subject. See {SPEC}."
        )
        return 1

    decided, deadline = found

    if decided:
        print(f"ok  explain-diff retire decision recorded (deadline was {deadline})")
        return 0

    days = (deadline - today).days
    if days > NOTICE_DAYS:
        print(f"ok  explain-diff retire decision due {deadline} ({days} days away)")
        return 0

    if days >= 0:
        print(
            f"⚠️  explain-diff retire decision due in {days} day(s) — {deadline}.\n"
            f"   Not failing yet. It fails on the day. See {SPEC}."
        )
        return 0

    print(
        f"❌ the explain-diff retire decision is {abs(days)} day(s) OVERDUE (deadline {deadline}) "
        f"and the checkbox is still unticked.\n\n"
        f"   The skill shipped on an unmeasured premise, and this deadline is the whole reason that\n"
        f"   was acceptable. Decide now — RETIRE it unless at least one explainer produced:\n"
        f"     • a boundary nobody had written down\n"
        f"     • a decision that became an ADR\n"
        f"     • a corrected belief — something believed about the system that wasn't true\n"
        f"     • a defect the dual review missed\n\n"
        f"   Count them yourself: `ls ~/explainers | wc -l`. THIS CHECK CANNOT — CI has no access to\n"
        f"   that directory, which is exactly why the decision is yours and not this script's.\n\n"
        f"   Then tick the checkbox in {ROADMAP.relative_to(ROOT)} and record what you decided.\n"
        f"   Ticking it without deciding is available and is the one failure nothing here can catch.\n"
    )
    return 1


def self_test() -> int:
    ticked = "- [x] **Re-examine after 5 explainers or on 2026-09-30, whichever comes first.** blah"
    unticked = "- [ ] **Re-examine after 5 explainers or on 2026-09-30, whichever comes first.** blah"
    cases: list[tuple[str, bool]] = [
        ("unticked line parses as undecided", find_retire_item(unticked) == (False, dt.date(2026, 9, 30))),
        ("ticked line parses as decided", find_retire_item(ticked) == (True, dt.date(2026, 9, 30))),
        ("absent line is None, not a silent pass", find_retire_item("- [ ] something else") is None),
        ("a reworded heading breaks the parse (so it fails loudly)",
         find_retire_item("- [ ] **Revisit after 5 explainers or on 2026-09-30**") is None),
        ("the real roadmap still matches the pattern",
         find_retire_item(ROADMAP.read_text(encoding="utf-8")) is not None),
    ]
    # Date-behaviour cases exercised through run() against the REAL file, which is currently unticked.
    real = find_retire_item(ROADMAP.read_text(encoding="utf-8"))
    if real and not real[0]:
        deadline = real[1]
        cases += [
            ("far before the deadline → 0", run(deadline - dt.timedelta(days=60)) == 0),
            ("inside the notice window → 0 (warns)", run(deadline - dt.timedelta(days=2)) == 0),
            ("on the deadline → 0 (last quiet day)", run(deadline) == 0),
            ("the day after → 1  ← the case this script exists for",
             run(deadline + dt.timedelta(days=1)) == 1),
        ]

    failed = [n for n, ok in cases if not ok]
    print()
    for name, ok in cases:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    print(f"\n{len(cases) - len(failed)}/{len(cases)} self-test cases passed")
    return 1 if failed else 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    today = dt.date.today()
    if "--today" in sys.argv:
        today = dt.date.fromisoformat(sys.argv[sys.argv.index("--today") + 1])
    sys.exit(run(today))
