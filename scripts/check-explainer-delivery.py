#!/usr/bin/env python3
"""The explainer delivery loop must be described in exactly ONE place.

WHY THIS EXISTS
---------------
Three skills produce a served HTML page: `explain-diff`, `brief`, `explain-findings`. Before
2026-08-24 the delivery loop — where the file goes, `explainer-serve.py`, the Ask tray, arming the
Monitor, delivering the URL — was written out in full in `explain-diff` AND again in `brief`.
Adding a third page-producing skill would have made three copies of a procedure that cost four
rounds of shipped defects to get right.

It is now in `.agents/skills/shared/explainer-delivery.md`, and every page-producing skill cites it.
This check is what keeps that true, because a prose rule saying "don't restate it" is exactly the
shape this project has measured as insufficient: a convention catches what you READ, a script
catches what is THERE.

WHAT IT ACTUALLY ASSERTS (and what it deliberately does not)
------------------------------------------------------------
It flags RESTATED PROCEDURE, not mentions. A skill is free to *talk about* `brief-compose.py` in its
own retrospective — `brief` does, and that history is worth keeping. What it may not do is tell the
reader to RUN the loop again:

  * a fenced code block containing a delivery command, or
  * a `Monitor({` block (the push-loop arming snippet).

Those are the forms a second copy actually takes. Counting bare mentions would have forced deleting
`brief`'s measured history to satisfy a checker, which is the check driving the docs rather than the
other way round.

FAILS IF
--------
  * the shared file is missing;
  * a page-producing skill does not cite it;
  * any SKILL.md restates the procedure (fenced delivery command, or a Monitor arming block);
  * a skill claims to produce a page but is not in PAGE_SKILLS (add it, or it escapes the check).

  --self-test  runs 8 cases against synthetic trees, including that each failure mode is DETECTED.
"""
from __future__ import annotations
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / ".agents" / "skills"
SHARED_REL = "shared/explainer-delivery.md"

# Skills whose output is a served explainer page. Hardcoded on purpose: a NEW page-producing skill
# that forgets to cite the shared file is exactly what this check is for, and a derived list would
# silently grow to include it. Per `hardcode-only-what-fails-loudly` — this list going stale
# announces itself (a missing directory is an error below), a derived one would not.
PAGE_SKILLS = ["explain-diff", "brief", "explain-findings", "explain-topic", "dashboard"]

DELIVERY_CMD = re.compile(r"explainer-serve\.py|brief-compose\.py|tail -n 0 -F.*questions\.md")
FENCE = re.compile(r"```[^\n]*\n(.*?)```", re.S)


def audit(skills_dir: Path, page_skills: list[str], shared_rel: str = SHARED_REL) -> list[str]:
    """Findings; empty means the constraint holds."""
    problems: list[str] = []

    shared = skills_dir / shared_rel
    if not shared.is_file():
        problems.append(f"the shared delivery reference is MISSING: {shared_rel}")
        return problems  # nothing else is meaningful without it

    if not DELIVERY_CMD.search(shared.read_text()):
        problems.append(
            f"{shared_rel} does not describe the delivery commands — it is the ONE place that must"
        )

    for name in page_skills:
        d = skills_dir / name
        f = d / "SKILL.md"
        if not f.is_file():
            problems.append(f"{name}/SKILL.md is missing (renamed or deleted? update PAGE_SKILLS)")
            continue
        text = f.read_text()
        if shared_rel not in text:
            problems.append(f"{name} produces a page but does not cite {shared_rel}")

    # Restatement can appear in ANY skill, not only the three.
    for f in sorted(skills_dir.glob("*/SKILL.md")):
        text = f.read_text()
        name = f.parent.name
        for body in FENCE.findall(text):
            if DELIVERY_CMD.search(body):
                problems.append(
                    f"{name} restates the delivery procedure in a code block — cite {shared_rel}"
                )
                break
        if "Monitor({" in text:
            problems.append(
                f"{name} contains a Monitor arming block — that snippet lives in {shared_rel}"
            )
    return problems


# ---------------------------------------------------------------- self-test
CITE = f"See ../{SHARED_REL} for delivery."
SHARED_BODY = "run python3 scripts/explainer-serve.py\n"


def _tree(tmp: Path, skills: dict[str, str], shared: str | None = SHARED_BODY) -> Path:
    root = tmp / "skills"
    for name, body in skills.items():
        (root / name).mkdir(parents=True, exist_ok=True)
        (root / name / "SKILL.md").write_text(body)
    if shared is not None:
        (root / "shared").mkdir(parents=True, exist_ok=True)
        (root / "shared" / "explainer-delivery.md").write_text(shared)
    return root


def self_test() -> int:
    cases, failures = 0, 0

    def check(label: str, got: list[str], want_problem: bool, needle: str = "") -> None:
        nonlocal cases, failures
        cases += 1
        ok = (len(got) > 0) == want_problem and (not needle or any(needle in g for g in got))
        if not ok:
            failures += 1
            print(f"  ✗ {label}: got {got!r}")
        else:
            print(f"  ✓ {label}")

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        r = _tree(tmp / "a", {"explain-diff": CITE, "brief": CITE})
        check("clean tree passes", audit(r, ["explain-diff", "brief"]), False)

        r = _tree(tmp / "b", {"explain-diff": "no citation here", "brief": CITE})
        check("missing citation caught", audit(r, ["explain-diff", "brief"]), True, "does not cite")

        r = _tree(tmp / "c", {"explain-diff": CITE}, shared=None)
        check("missing shared file caught", audit(r, ["explain-diff"]), True, "MISSING")

        r = _tree(tmp / "d", {"explain-diff": CITE + "\n```bash\npython3 scripts/explainer-serve.py\n```\n"})
        check("restated command caught", audit(r, ["explain-diff"]), True, "restates")

        r = _tree(tmp / "e", {"explain-diff": CITE + '\nMonitor({\n  command: "tail",\n})\n'})
        check("Monitor block caught", audit(r, ["explain-diff"]), True, "Monitor arming")

        # A NON-page skill restating the loop is still a second copy.
        r = _tree(tmp / "f", {"explain-diff": CITE, "zoom-out": "```\nbrief-compose.py --content x\n```"})
        check("restatement in another skill caught", audit(r, ["explain-diff"]), True, "restates")

        # Historical MENTION outside a fence is allowed — this is what protects brief's retrospective.
        r = _tree(tmp / "g", {"explain-diff": CITE + "\nHistory: brief-compose.py gained a --self-test.\n"})
        check("prose mention allowed", audit(r, ["explain-diff"]), False)

        r = _tree(tmp / "h", {"explain-diff": CITE}, shared="nothing about commands")
        check("hollow shared file caught", audit(r, ["explain-diff"]), True, "does not describe")

    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()

    if not SKILLS.is_dir():
        print(f"CANNOT RUN — no skills directory at {SKILLS}. Treat this as NOT RUN.", file=sys.stderr)
        return 2

    problems = audit(SKILLS, PAGE_SKILLS)
    if problems:
        print("the explainer delivery loop is described in more than one place:\n")
        for p in problems:
            print(f"  ✗ {p}")
        print(f"\nThe one description is .agents/skills/{SHARED_REL}. Cite it; do not restate it.")
        return 1

    print(f"explainer delivery: 1 shared description, {len(PAGE_SKILLS)} skills cite it, 0 restatements")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
