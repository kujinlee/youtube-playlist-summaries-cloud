#!/usr/bin/env python3
"""Every unticked gate item must name what would make it FAIL.

WHY THIS EXISTS — measured 2026-08-11.

`docs/m1.4-finishup-checklist.md` B5 read: "`npm run check:confinement` passes against the real
deployed environment, not just local." That script is static — no env, no fetch, no network — so it
emits byte-identical output everywhere and CANNOT observe a deployment. The item could only ever
pass. Someone runs it, sees OK, ticks the box, and now believes production was verified.

That is this project's familiar "guard that passes in both worlds", except the guard is a SENTENCE.
Every instrument built for that shape — check-guard-coverage.py, SHAPE/SEQUENCE classification,
mutate-schema.py, the ratchets — inspects CODE. None inspects a gate description, which is exactly
where an unfalsifiable guard hides best, because nobody asks a sentence "what would make you fail?"

WHAT THIS CAN AND CANNOT DO — read this before trusting a green run.

It CANNOT tell whether an instrument can observe its subject. That is human judgment. Rewriting B5
as a crisp predicate ("check:confinement exits 0 against prod") would look perfectly falsifiable and
still be meaningless.

What it does instead is force the human to look, at write time, in a place a script can verify they
did not skip: to write `FAILS IF:` you must name a concrete observation, and the moment you try for
B5 you have to ask what that command actually reads — and discover it takes no URL. The clause does
not DETECT the mismatch; it surfaces it. Same move as SHAPE/SEQUENCE: the value is not the label,
it is that assigning one makes the guard's nature unavoidable.

So this catches SHAPE, not TRUTH. A wrong `FAILS IF:` still passes. It shrinks the class.

Usage:
    python3 scripts/check-gate-falsifiability.py            # check the gate docs
    python3 scripts/check-gate-falsifiability.py --report    # list findings, always exit 0
    python3 scripts/check-gate-falsifiability.py --self-test
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Which checkboxes are GATES. Not every checkbox is one, and this distinction cost a sweep to learn.
#
# MEASURED 2026-08-11: scanning all of `roadmap-to-launch.md` produced 21 findings of which almost
# none were gates — they were historical review narrative ("Round 7 — NOT CONVERGED…"), Parking Lot
# items nobody promised, and state notes. **That document overloads `- [ ]` for three different
# meanings**: a gate that blocks a milestone, a backlog wish, and a record of something that already
# happened. No syntactic checker can separate those, which is also why a human skimming it cannot.
#
# So scope is explicit: whole-file where every checkbox really is a gate, section-scoped where the
# gates live under known milestone headings. A `None` section list means "the whole file".
GATE_SCOPES: dict[str, list[str] | None] = {
    "docs/m1.4-finishup-checklist.md": None,
    "docs/roadmap-to-launch.md": ["## M1", "## M2", "## M3"],
}

# Existing debt. See the ratchet in main() for why this is a number and not zero.
#   13 → 2026-08-11, first measurement
#    8 → 2026-08-11, after the A/B rewrite (PR #69) and B5's resolution (PR #70)
#    4 → 2026-08-11, after de-duplicating the roadmap's copy of the B-group and deciding B4
# The five duplicated B-group items are gone: the roadmap now points at the checklist instead of
# restating it. That was not cosmetic — the duplicate copy had the serve-doc money item ticked
# `[x] CONFIRMED and FIXED` while the checklist's B3 was failing against hosted infra, so the two
# copies disagreed about whether a money gate had passed. The `investigation_phrasing` finding is
# also gone: it was B4, which could not be phrased as a gate until somebody decided what version
# skew SHOULD do (decided 2026-08-11 — tolerate).
#    3 → 2026-08-11, after A1/A2 were re-verified against v6 and M1.4 was closed
# Remaining 3: M3.1/3.2/3.3 acceptance, which are not yet written as gates.
BASELINE = 3

FALSIFIER_RE = re.compile(r"\bFAILS?\s+IF\b", re.IGNORECASE)
# An item phrased as an investigation has no pass condition by construction. B4 is the live example:
# "check whether a rendering share starts returning 503" — an action, not an assertion.
INVESTIGATION_RE = re.compile(
    r"\b(check whether|see if|investigate|find out|determine whether|evaluate whether|explore whether)\b",
    re.IGNORECASE,
)
NPM_RUN_RE = re.compile(r"npm run ([A-Za-z0-9:_-]+)")
# A tick records THAT something was verified and never WHAT AGAINST. Measured 2026-08-11: A1 and A2
# are ticked from 2026-07-22/23 (the v3/v4 era) and two releases have shipped since, so both are
# claims about code that no longer runs. Same shape as the migration drift found the same morning:
# the record captured a claim without capturing its subject.
VERIFIED_AGAINST_RE = re.compile(r"VERIFIED\s+AGAINST:\s*v(\d+)", re.IGNORECASE)
CHECKBOX_RE = re.compile(r"^(\s*)- \[([ xX~])\]\s*(.*)$")


@dataclass
class Finding:
    path: str
    line: int
    kind: str          # missing_falsifier | investigation_phrasing | unknown_command | stale_verification
    excerpt: str
    detail: str


def _blocks(text: str, sections: list[str] | None = None):
    """Yield (line_no, checked_char, body_text) per checkbox, body including its
    indented continuation lines. Fenced code is skipped: a ``` block may legitimately SHOW an
    example gate item, and flagging documentation of the format would be self-defeating."""
    lines = text.splitlines()
    out = []
    in_fence = False
    in_scope = sections is None
    i = 0
    while i < len(lines):
        line = lines[i]
        if not in_fence and line.startswith("## ") and sections is not None:
            in_scope = any(line.startswith(pfx) for pfx in sections)
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            i += 1
            continue
        if in_fence:
            i += 1
            continue
        m = CHECKBOX_RE.match(line)
        if not m or not in_scope:
            i += 1
            continue
        indent, mark, first = m.group(1), m.group(2), m.group(3)
        body = [first]
        j = i + 1
        while j < len(lines):
            nxt = lines[j]
            if nxt.lstrip().startswith("```"):
                break
            if not nxt.strip():
                break
            if CHECKBOX_RE.match(nxt):
                break
            if len(nxt) - len(nxt.lstrip()) <= len(indent) and nxt.strip():
                break
            body.append(nxt.strip())
            j += 1
        out.append((i + 1, mark, " ".join(body)))
        i = j if j > i else i + 1
    return out


def find_gate_defects(text: str, path: str, known_scripts: set[str],
                      sections: list[str] | None = None,
                      current_release: int | None = None) -> list[Finding]:
    findings: list[Finding] = []
    for line_no, mark, body in _blocks(text, sections):
        excerpt = (body[:80] + "…") if len(body) > 80 else body

        for m in NPM_RUN_RE.finditer(body):
            if m.group(1) not in known_scripts:
                findings.append(Finding(path, line_no, "unknown_command", excerpt,
                                        f"names `npm run {m.group(1)}`, which is not in package.json"))

        # Ticked items are out of scope FOR FALSIFIERS — a done item carries its evidence and
        # retro-fitting clauses to history is churn. They are NOT out of scope for STALENESS: a tick
        # whose subject has been replaced is worse than an untied box, because it reads as covered.
        if mark in ("x", "X"):
            if current_release is not None:
                m = VERIFIED_AGAINST_RE.search(body)
                if m is None:
                    # NOT silently skipped. Saying "nothing is stale" while being unable to judge
                    # most items is the fail-open this whole exercise is about.
                    findings.append(Finding(path, line_no, "unversioned_tick", excerpt,
                                            "ticked with no `VERIFIED AGAINST:` — staleness cannot be judged"))
                elif int(m.group(1)) < current_release:
                    findings.append(Finding(path, line_no, "stale_verification", excerpt,
                                            f"verified against v{m.group(1)}, deployed is v{current_release}"))
            continue

        has_falsifier = bool(FALSIFIER_RE.search(body))
        if has_falsifier:
            continue

        if INVESTIGATION_RE.search(body):
            findings.append(Finding(path, line_no, "investigation_phrasing", excerpt,
                                    "phrased as an investigation, so it has no pass condition"))
        else:
            findings.append(Finding(path, line_no, "missing_falsifier", excerpt,
                                    "no `FAILS IF:` — nothing states what observation would fail it"))
    return findings


def deployed_release() -> int | None:
    """Highest release version currently deployed, or None if it cannot be determined.

    Callers MUST treat None as "not checked", never as "nothing is stale" — see main()."""
    import subprocess
    try:
        app = re.search(r'^app\s*=\s*"([^"]+)"',
                        (ROOT / "fly.toml").read_text(), re.MULTILINE)
        if not app:
            return None
        out = subprocess.run(["fly", "releases", "-a", app.group(1), "--json"],
                             capture_output=True, text=True, timeout=60)
        if out.returncode != 0:
            return None
        vers = [int(str(r.get("Version", r.get("version", ""))).lstrip("v"))
                for r in json.loads(out.stdout) if str(r.get("Version", r.get("version", ""))).lstrip("v").isdigit()]
        return max(vers) if vers else None
    except Exception:
        return None


def known_npm_scripts() -> set[str]:
    pkg = json.loads((ROOT / "package.json").read_text())
    return set(pkg.get("scripts", {}))


# ── self-test ────────────────────────────────────────────────────────────────────────────────
CASES: list[tuple[str, str, list[str]]] = [
    ("unticked with no falsifier is flagged",
     "- [ ] **X** do the thing.", ["missing_falsifier"]),
    ("unticked with a falsifier is clean",
     "- [ ] **X** do the thing. FAILS IF: the thing returns 500.", []),
    ("ticked items are out of scope",
     "- [x] **X** did the thing.", []),
    ("partial [~] counts as unticked",
     "- [~] **X** partly done.", ["missing_falsifier"]),
    ("investigation phrasing is called out specifically",
     "- [ ] **B4** check whether a share starts returning 503.", ["investigation_phrasing"]),
    ("a falsifier resolves investigation phrasing",
     "- [ ] **B4** check whether it 503s. FAILS IF: the share returns 503.", []),
    ("falsifier on a continuation line still counts",
     "- [ ] **X** do the thing\n      FAILS IF: it returns 500.", []),
    ("an unknown npm script is flagged",
     "- [ ] **X** run `npm run totally-made-up`. FAILS IF: it exits non-zero.",
     ["unknown_command"]),
    ("a known npm script is not flagged",
     "- [ ] **X** run `npm run test`. FAILS IF: it exits non-zero.", []),
    # Documenting the format must not trip the checker that enforces it.
    ("checkboxes inside a fenced block are ignored",
     "```markdown\n- [ ] **example** with no falsifier\n```", []),
    # Learned from the first sweep: roadmap-to-launch.md uses `- [ ]` for gates, backlog wishes AND
    # historical narrative. Scoping to milestone sections is what separates them.
    ("a checkbox outside the scoped sections is ignored",
     "## Parking Lot\n- [ ] **X** someday.", []),
    ("a checkbox inside a scoped section is checked",
     "## M3 — Acceptance\n- [ ] **3.1** do it.", ["missing_falsifier"]),
    ("scope re-closes when a later heading is out of scope",
     "## M3 — Acceptance\n- [ ] **3.1** do it.\n\n## Parking Lot\n- [ ] **Y** someday.",
     ["missing_falsifier"]),
    ("two bad items yield two findings",
     "- [ ] **A** one.\n- [ ] **B** two.", ["missing_falsifier", "missing_falsifier"]),
]


# Staleness cases carry a deployed-release number; (name, text, current_release, expected).
STALENESS_CASES: list[tuple[str, str, int, list[str]]] = [
    ("a tick verified against an older release is stale",
     "- [x] **A1** done. VERIFIED AGAINST: v4", 6, ["stale_verification"]),
    ("a tick verified against the current release is clean",
     "- [x] **A1** done. VERIFIED AGAINST: v6", 6, []),
    ("a tick with no VERIFIED AGAINST is reported, never silently skipped",
     "- [x] **A1** done.", 6, ["unversioned_tick"]),
    ("an UNticked item is not a staleness concern",
     "- [ ] **A1** todo. FAILS IF: it 500s.", 6, []),
    ("a newer verification than the deployed release is not flagged stale",
     "- [x] **A1** done. VERIFIED AGAINST: v7", 6, []),
]


def self_test() -> int:
    failures = 0
    scripts = {"test", "check:confinement"}
    for name, text, release, expected in STALENESS_CASES:
        got = [f.kind for f in find_gate_defects(text, "t.md", scripts, None, release)]
        if got != expected:
            print(f"  FAIL {name}\n       expected {expected}\n       got      {got}")
            failures += 1
    for name, text, expected in CASES:
        sections = ["## M1", "## M2", "## M3"] if text.startswith("## ") else None
        got = [f.kind for f in find_gate_defects(text, "t.md", scripts, sections)]
        if got != expected:
            print(f"  FAIL {name}\n       expected {expected}\n       got      {got}")
            failures += 1
    total = len(CASES) + len(STALENESS_CASES)
    print(f"self-test: {total - failures}/{total} passed")
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()

    report_only = "--report" in argv
    staleness = "--staleness" in argv

    current_release: int | None = None
    if staleness:
        explicit = [a for a in argv if a.startswith("--current-release=")]
        if explicit:
            raw = explicit[0].split("=", 1)[1].lstrip("vV")
            if not raw.isdigit():
                print(f"FAILED: --current-release must be a version number like v6, got '{raw}'.")
                return 1
            current_release = int(raw)
        else:
            current_release = deployed_release()
        if current_release is None:
            # FAIL CLOSED. "Could not determine the deployed release" is NOT "nothing is stale".
            print("FAILED: could not determine the deployed release (fly unavailable/unauthenticated).")
            print("Staleness was NOT checked — treat this as not run, and pass --current-release=vN.")
            return 1
        print(f"deployed release: v{current_release}")

    scripts = known_npm_scripts()
    findings: list[Finding] = []
    for rel, sections in GATE_SCOPES.items():
        p = ROOT / rel
        if not p.exists():
            print(f"gate doc missing: {rel}")
            return 1
        findings.extend(find_gate_defects(p.read_text(errors="ignore"), rel, scripts, sections,
                                          current_release))

    if not findings:
        print("gate falsifiability OK — every unticked gate item names what would fail it")
        return 0

    # RATCHET, not a big-bang. Same shape as scripts/check-arch-findings.py: the existing debt is
    # recorded as a number and the build fails only if it GROWS. A hard failure today would just be
    # switched off, and the point is to stop the NEXT unfalsifiable gate from being written.
    #
    # LOWER THIS as gates gain `FAILS IF:` clauses. Raising it should appear in a diff, in a PR,
    # where someone can ask why a new gate shipped without a stated failure condition.
    #
    # 13 as measured 2026-08-11: 5 in the M1.4 checklist (B1–B5) and 8 in the roadmap — of which 4
    # are the SAME B-group items duplicated across both docs, each file naming the other as
    # canonical. B4 is flagged twice for that reason.
    by_kind: dict[str, int] = {}
    for f in findings:
        by_kind[f.kind] = by_kind.get(f.kind, 0) + 1

    print(f"{len(findings)} gate item(s) with no stated failure condition:\n")
    for f in findings:
        print(f"  {f.path}:{f.line}  [{f.kind}]")
        print(f"      {f.excerpt}")
        print(f"      → {f.detail}")
    print("\nsummary: " + ", ".join(f"{k}={v}" for k, v in sorted(by_kind.items())))

    if len(findings) > BASELINE:
        print(f"\nRATCHET FAILED: {len(findings)} findings, baseline is {BASELINE}.")
        print("A new gate shipped with no `FAILS IF:`. Add one, or justify raising the baseline in the diff.")
        return 0 if report_only else 1

    if len(findings) < BASELINE:
        print(f"\nBaseline is {BASELINE} but only {len(findings)} remain — LOWER IT to lock the gain in.")
    else:
        print(f"\nat baseline ({BASELINE}) — not growing. Lower it as gates gain `FAILS IF:` clauses.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
