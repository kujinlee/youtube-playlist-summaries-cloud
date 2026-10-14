#!/usr/bin/env python3
"""A mechanism described in more than one place drifts. This refuses the second copy.

WHY THIS EXISTS
---------------
The handoff-path hint mechanism and the corpus cross-check instruction were each written out at
SIX sites — the vendored skill, the enforcing hook's refusal, this directory's guard comment,
`docs/plugins.md`, `docs/process-rationale.md` and a memory note. Nothing compared them. Across
five consecutive review rounds a reviewer found, every single round, at least one copy that had
drifted: a withdrawn claim left standing as a paragraph's bolded headline, a count with no unit,
a provenance qualification applied at one site and not its neighbour, and — the one that settled
it — a round-5 correction that reached the skill and never reached the hook, so the hook's refusal
printed a claim AND its own withdrawal in the same message.

That is this repository's most-measured defect, `a second implementation of one rule drifts`
(17 recorded instances), applied to prose instead of code. `scripts/check-explainer-delivery.py`
already demonstrates the structural answer for skills; this generalises it to any mechanism and
any kind of citing file.

WHAT IT ACTUALLY ASSERTS (and what it deliberately does not)
------------------------------------------------------------
It flags a RESTATED MECHANISM, not a mention. A retrospective is free to *discuss* the history —
`docs/process-rationale.md` exists to explain why five versions of a sentence were each refuted,
and that history is the most valuable thing on the branch. What a site may not do is hand the
reader the mechanism again: the SYMBOLS for `handoff-path`, the COMMAND FORMS for `corpus-search`.
Counting bare mentions would have forced deleting measured history to satisfy a checker, which is
the check driving the docs rather than the other way round.

⚠ EXEMPTIONS, STATED RATHER THAN HIDDEN. `docs/reviews/**` is frozen testimony and is never
edited. `docs/dashboard-entries.md` holds DATED entries: a record of what was true on a day, not
a rule a reader follows at the moment of need — which is exactly the distinction this branch's own
narrowing turned on. Both are exempt, and that means drift inside them is NOT caught here.

FAILS IF
--------
  * a canonical file is missing, or its `<!-- canon: NAME -->` marker is absent;
  * that marker appears in more than one file (two canons for one mechanism);
  * a declared citing site does not cite the canonical path;
  * any non-exempt file RESTATES a mechanism (carries its tokens) without citing its canon.

  --self-test  runs 15 cases over synthetic trees, including that each failure mode is DETECTED.
"""
from __future__ import annotations
import contextlib
import io
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Hardcoded on purpose, per `hardcode-only-what-fails-loudly`: a missing canonical file is an
# error below, so this list going stale announces itself. A derived list would silently shrink.
CANONS: list[dict] = [
    {
        "name": "handoff-path",
        "file": ".agents/skills/shared/handoff-path.md",
        # Mechanism SYMBOLS. A site carrying these is handing the reader the mechanism again.
        "tokens": ["REMEMBER_ROOT", "PER_SESSION_HANDOFF", "_resolve_memory_project_dir"],
        "cites": [
            ".agents/skills/handoff/SKILL.md",
            ".claude/hooks/enforce-handoff-path.sh",
            "scripts/check-handoff-path.py",
            "docs/plugins.md",
        ],
    },
    {
        "name": "corpus-search",
        "file": ".agents/skills/shared/corpus-search.md",
        # COMMAND FORMS. Prose may name the cross-check; it may not reprint the commands.
        "tokens": ["git grep --cached", "rg --hidden", "-RSl"],
        "cites": [
            ".agents/skills/handoff/SKILL.md",
            ".claude/hooks/enforce-handoff-path.sh",
            "scripts/check-handoff-path.py",
            "docs/process-rationale.md",
            "docs/memory/a-vendored-line-number-has-no-owner.md",
        ],
    },
]

EXEMPT = re.compile(r"^(docs/reviews/|docs/dashboard-entries\.md$|\.remember/)")
SEARCHED = ("*.md", "*.py", "*.sh")
MARKER = "<!-- canon: {} -->"


def _tracked_textfiles(root: Path) -> list[Path]:
    out: list[Path] = []
    for sub in (".agents", ".claude", "docs", "scripts"):
        d = root / sub
        if not d.is_dir():
            continue
        for pat in SEARCHED:
            out += sorted(d.rglob(pat))
    return out


def audit(root: Path, canons: list[dict] | None = None) -> list[str]:
    """Findings; empty means every mechanism is described exactly once and cited elsewhere."""
    canons = CANONS if canons is None else canons
    problems: list[str] = []
    files = _tracked_textfiles(root)

    for canon in canons:
        name, rel = canon["name"], canon["file"]
        path = root / rel
        if not path.is_file():
            problems.append(f"{rel} is MISSING — {name} has no canonical source")
            continue
        # A citation is matched on the `shared/<name>.md` SUFFIX, not the repo-relative path:
        # a markdown link from inside `.agents/skills/handoff/` correctly writes
        # `../shared/handoff-path.md`, and demanding the long form would reject a correct link.
        # Same shape as `check-explainer-delivery.py`, which matches `shared/explainer-delivery.md`.
        cite_token = "/".join(Path(rel).parts[-2:])
        marker = MARKER.format(name)
        if marker not in path.read_text(encoding="utf-8", errors="replace"):
            problems.append(f"{rel} does not carry its marker {marker!r}")

        holders = [
            f for f in files
            if marker in f.read_text(encoding="utf-8", errors="replace")
        ]
        if len(holders) > 1:
            where = ", ".join(sorted(str(f.relative_to(root)) for f in holders))
            problems.append(f"marker {marker!r} appears in {len(holders)} files — {where}")

        for cite_rel in canon["cites"]:
            cp = root / cite_rel
            if not cp.is_file():
                problems.append(f"{cite_rel} is declared a citing site but does not exist")
                continue
            if cite_token not in cp.read_text(encoding="utf-8", errors="replace"):
                problems.append(f"{cite_rel} does not cite {rel}")

        for f in files:
            frel = str(f.relative_to(root))
            if frel == rel or EXEMPT.match(frel):
                continue
            body = f.read_text(encoding="utf-8", errors="replace")
            hit = next((t for t in canon["tokens"] if t in body), None)
            if hit and cite_token not in body:
                problems.append(
                    f"{frel} restates {name} (carries {hit!r}) without citing {rel}"
                )
    return problems


def _built_world(base: Path, complete: bool = True) -> Path:
    """Construct a tree satisfying the LIVE `CANONS`, so a case can drive `main()` over a world it
    built rather than over the real repository. `complete=False` drops one citation, which is the
    failure shape that actually recurred: a fix that reached one site and not its neighbour."""
    for canon in CANONS:
        f = base / canon["file"]
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(MARKER.format(canon["name"]) + "\n" + "\n".join(canon["tokens"]) + "\n")
        token = "/".join(Path(canon["file"]).parts[-2:])
        for i, rel in enumerate(canon["cites"]):
            c = base / rel
            c.parent.mkdir(parents=True, exist_ok=True)
            body = "" if (not complete and i == 0) else f"see {token}\n"
            c.write_text(c.read_text() + body if c.exists() else body)
    return base

# ── self-test ────────────────────────────────────────────────────────────────────────────────
def _tree(base: Path, canon_body: str, sites: dict[str, str]) -> list[str]:
    (base / ".agents/skills/shared").mkdir(parents=True, exist_ok=True)
    (base / "docs").mkdir(parents=True, exist_ok=True)
    if canon_body is not None:
        (base / ".agents/skills/shared/c.md").write_text(canon_body)
    for rel, body in sites.items():
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)
    spec = [{
        "name": "c", "file": ".agents/skills/shared/c.md",
        "tokens": ["MECHTOKEN"], "cites": ["docs/site.md"],
    }]
    return audit(base, spec)


def self_test() -> int:
    passed = failed = 0

    def case(label: str, got, want) -> None:
        nonlocal passed, failed
        if got == want:
            passed += 1
        else:
            failed += 1
            print(f"  [FAIL] {label}: got {got!r} want {want!r}")

    CANON = "<!-- canon: c -->\nMECHTOKEN lives here.\n"
    CITE = "See ../shared/c.md for the mechanism.\n"   # the RELATIVE form a real link uses

    with tempfile.TemporaryDirectory() as td:
        t = Path(td)

        r = _tree(t / "ok", CANON, {"docs/site.md": CITE})
        case("a canon plus a citing site is clean", r, [])

        r = _tree(t / "nocanon", None, {"docs/site.md": CITE})
        case("a MISSING canonical file is detected", any("is MISSING" in x for x in r), True)

        r = _tree(t / "nomark", "no marker here\nMECHTOKEN\n", {"docs/site.md": CITE})
        case("an absent marker is detected", any("does not carry its marker" in x for x in r), True)

        r = _tree(t / "twomark", CANON, {"docs/other.md": CANON, "docs/site.md": CITE})
        case("a SECOND file holding the marker is detected",
             any("appears in 2 files" in x for x in r), True)

        r = _tree(t / "nocite", CANON, {"docs/site.md": "nothing here\n"})
        case("a citing site that does not cite is detected",
             any("does not cite" in x for x in r), True)

        r = _tree(t / "missingsite", CANON, {})
        case("a declared citing site that does not exist is detected",
             any("does not exist" in x for x in r), True)

        r = _tree(t / "restate", CANON, {"docs/site.md": CITE, "docs/sneak.md": "MECHTOKEN again\n"})
        case("a RESTATEMENT without a citation is detected",
             any("restates c" in x for x in r), True)

        r = _tree(t / "quote", CANON,
                  {"docs/site.md": CITE, "docs/sneak.md": "MECHTOKEN " + CITE})
        case("a restatement that DOES cite is allowed", r, [])

        r = _tree(t / "exempt", CANON,
                  {"docs/site.md": CITE, "docs/reviews/r1.md": "MECHTOKEN\n"})
        case("frozen testimony under docs/reviews/ is exempt", r, [])

        r = _tree(t / "dash", CANON,
                  {"docs/site.md": CITE, "docs/dashboard-entries.md": "MECHTOKEN\n"})
        case("the dated dashboard is exempt", r, [])

        r = _tree(t / "self", CANON, {"docs/site.md": CITE})
        case("the canon itself is never flagged for holding its own tokens",
             any("restates" in x for x in r), False)

        # The real tree must pass — the check is pointless if it cannot measure its own subject.
        case("the REAL repository is clean", audit(ROOT), [])

        # ADR-0014: drive `main()` over a world THIS CASE BUILT, in both directions, so no line of
        # it ships unmeasured. ⚠ Driving it over the real repo only is what `check-main-drivable.py`
        # refuses — "2 suite calls to main(), none over a world the case built" — and it said so
        # here before these two worlds existed.
        # ⚠ The world is built by the statement BEFORE the call, and what `main()` receives is
        # `t / "<name>"` — an expression whose LEAF is the temp dir this case bound. Passing
        # `_built_world(...)` directly reads as INERT to `world_class` (a module-level name it
        # cannot resolve), and INERT alone is not evidence that the case built anything.
        _built_world(t / "world-ok", complete=True)
        with contextlib.redirect_stdout(io.StringIO()):
            rc_ok = main([], root=t / "world-ok")
        case("main() returns 0 over a BUILT world that satisfies every canon", rc_ok, 0)
        _built_world(t / "world-nocite", complete=False)
        with contextlib.redirect_stdout(io.StringIO()):
            rc_bad = main([], root=t / "world-nocite")
        case("...and 1 over a BUILT world where one citation is missing", rc_bad, 1)
        # ⚠ argv VARIED, not decorative: an unknown flag is misuse and says so with rc=2, which is
        # what makes this parameter distinguishable from a constant.
        with contextlib.redirect_stdout(io.StringIO()):
            rc_misuse = main(["--bogus"], root=t / "world-ok")
        case("...and 2 when given an argument it does not take", rc_misuse, 2)

    print(f"{passed}/{passed + failed} passed")
    return 0 if failed == 0 else 1


def main(argv: list[str], root: Path = ROOT) -> int:
    # ADR-0014's D1 shape, `def main(argv, root=ROOT)`, and BOTH parameters are load-bearing —
    # three guards each refused a different shortening of this signature, which is why it looks
    # the way it does:
    #   * `check-main-drivable.py` requires the world to be a parameter main DECLARES, and
    #     `_passes_extra_world` reads `positional[1:] | kwonly` — so dropping `argv` and leaving
    #     `main(root=…)` destroyed the PARAM route and sent this guard to identity DEBT;
    #   * `check-fixture-variation.py` requires every parameter to be VARIED by some case, and an
    #     `argv` that only ever receives `[]` is indistinguishable from a constant;
    #   * so `argv` carries real behaviour — this check takes no arguments, and saying so is worth
    #     an exit code rather than silently ignoring a typo'd flag.
    # ⚠ The `--self-test` dispatch lives in `__main__`, not here, so no case re-enters this suite.
    if argv:
        print(f"unexpected argument(s): {' '.join(argv)} — this check takes none, or --self-test")
        return 2
    problems = audit(root)
    if problems:
        print("⛔ a mechanism is described in more than one place, or a citation is missing:")
        for p in problems:
            print(f"  ✗ {p}")
        print("\nEach mechanism lives in ONE file and every other site cites it. See the module")
        print("docstring for why, and `.agents/skills/shared/` for the canonical sources.")
        return 1
    names = ", ".join(c["name"] for c in CANONS)
    print(f"canonical sources OK — {len(CANONS)} mechanism(s) described once each ({names})")
    return 0


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv[1:] else main(sys.argv[1:]))
