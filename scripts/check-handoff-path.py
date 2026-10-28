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

# The path this guard enforces, and the ONE place the mechanism behind it is described:
#   .agents/skills/shared/handoff-path.md
# ⛔⛔ r7 CLAUDE M3 — WHAT STOOD HERE WAS A FOURTH RECITAL, four lines above the comment below
# that claims the recital moved out. It quoted the symbol, the emission banner and the injection
# order — the same three clauses deleted from the skill, the hook's refusal text and
# `docs/plugins.md` in the commit before this one, and missed by that commit's own sweep.
# ⛔ AND ITS HEADLINE WAS FALSE AS WELL, which is the worse half: it said "the path the hook
# ACTUALLY READS" over ONE of TWO assignments — the vendor's `else` branch (0.33.0 `:1168` is the
# per-session path, `:1171` the shared one), so under `handoff_mode: per_session` the hook reads a
# different path than the line quoted here. The canon states both and their bounds; a citation
# cannot be wrong about which branch it quotes, because it quotes none.
#
# ⟳ 2026-10-14 — WHAT STOOD HERE IS NOW IN ONE PLACE, AND THIS COMMENT CITES IT.
# The vendored-symbol rule, the discovery command, the GNU flag provenance and the corpus
# cross-check were all restated here AND at five other sites. Nothing compared them, and five
# consecutive review rounds each found a copy that had drifted — a withdrawn claim left standing,
# a count with no unit, a qualification applied at one site and not its neighbour.
#
#   .agents/skills/shared/corpus-search.md   — inventorying where a string appears here
#   .agents/skills/shared/handoff-path.md    — the handoff path, and why a hint appears
#
# ⚠ Do not restate either here. `scripts/check-canonical-source.py` refuses it, which is the
# point: a prose rule saying "don't restate it" is the shape this project has measured as
# insufficient — a convention catches what you READ, a script catches what is THERE.
#
# ⚠ No gate in this repo can see a stale figure HERE — this is a code comment and the document
# guards read `docs/`. It was found by searching every mention of the hook ACROSS SYMLINKS:
# `.claude/skills/handoff` is a symlink to `../../.agents/skills/handoff`, one file under two paths,
# and a recursive search that does not follow it misses a FIFTH copy of these locators — which it
# did for half a day (round 1 H1). ⛔ r4: the clause that stood here — "whether your tool follows
# symlinks is tool-specific: check" — was the RETIRED lesson. For this repo's tracked corpus the
# symlink question does not arise (`git grep` searches what git tracks); it arises only for
# content git does not track, which is the case r4 H1 says to name and search separately.
# ⟳ An earlier version named `check-withdrawal` as the guard that cannot see this. That guard does
# not exist in this repo at this commit — it lives only on an unmerged branch — so the sentence
# explaining why nothing caught this named something with no owner here, which is the defect it was
# describing (round 1 M4).
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
    """The suite, inside `fixture_git.isolated()`: every `--self-test` runs isolated (backlog #382)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    failures = 0
    # ⛔ `[FAIL] {name}: got {got} want {want}` IS A CONTRACT, and this file was the
    # NEAR-MISS of the class — which makes it the dangerous one, not the mild one.
    # scripts/check-plan-code.py attributes a killed mutation with
    #     l.strip()[7:].rsplit(": got ", 1)[0].strip()   for lines starting "[FAIL] "
    # This printed `[FAIL] {name}: expected {expected}, got {got}` — note `, got `,
    # not `: got `. It CLEARS the startswith filter, so unlike its 18 siblings it does
    # not fail loudly-and-emptily; `rsplit` on an absent needle returns the WHOLE
    # string, so it yields the case name with `: expected 1, got 0` welded on. A
    # plausible-looking attribution that no `expect` entry can ever match.
    # MEASURED 2026-09-06 before the fix:
    #   'pristine upstream — the reversion this exists to catch: expected 1, got 0'
    # after:
    #   'pristine upstream — the reversion this exists to catch'
    print(f"check-handoff-path --self-test  ({len(CASES)} text cases + 3 file cases)")
    for name, text, expected in CASES:
        got = 1 if check_text(text) else 0
        ok = got == expected
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got} want {expected}")

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        missing = tmp / "nope.md"
        code, _ = check_file(missing)
        ok = code == 2
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] missing file is CANNOT RUN: got {code} want 2")

        empty = tmp / "empty.md"
        empty.write_text("", encoding="utf-8")
        code, _ = check_file(empty)
        ok = code == 2
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] empty file is CANNOT RUN: got {code} want 2")

        good = tmp / "good.md"
        good.write_text(GOOD, encoding="utf-8")
        code, _ = check_file(good)
        ok = code == 0
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] compliant file exits 0: got {code} want 0")

    # ⛔ THE WORD "passed" IS LOAD-BEARING — a SECOND contract with check-plan-code.py, on the
    # SUCCESS side, and it is not the FAIL-line one above. `control_is_green(rc, out)` is
    # literally `rc == 0 and "passed" in out`: the exit code alone cannot distinguish "green"
    # from "never ran", because a script with no `__main__` exits 0 in silence.
    #
    # This printed `PASS` — rc 0, no "passed". MEASURED in CI 2026-09-07, the first run where a
    # manifest pointed here: every case reported `[ok]`, the suite printed PASS, and the harness
    # still refused with *"control run … did not prove the suite works (exit 0)"* and withheld
    # all five verdicts as NOT CHECKED. That refusal is CORRECT — the harness cannot read PASS —
    # and it is the reason this line now carries a ratio and the word, matching every sibling.
    #
    # ⚠ A failing run still contains "passed" (`8/10 … passed`), which is fine: `control_is_green`
    # also requires rc == 0, and a failing suite returns 1 below.
    # backlog #111: THE HOOK ITSELF, run as a real file over a copied tree, under shimmed interpreters.
    # The detector compared a STDOUT string, so a `python3` that prints a banner first (pyenv, conda,
    # a chatty sitecustomize) or exits non-zero yielded neither "yes" nor "no", and the hook exited 0 in
    # silence — disarmed for the session. Same hole, same fix as enforce-selection-card.sh.
    import os, shutil, subprocess
    hook_failures = 0

    def _hook_rc(payload: bytes, skill_text: str, python3: str | None, checker_edit=None) -> int:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".claude/hooks").mkdir(parents=True)
            shutil.copy(REPO_ROOT / ".claude/hooks/enforce-handoff-path.sh", root / ".claude/hooks")
            (root / "scripts").mkdir()
            shutil.copy(Path(__file__), root / "scripts/check-handoff-path.py")
            if checker_edit is not None:
                cp = root / "scripts/check-handoff-path.py"; cp.write_text(checker_edit(cp.read_text()))
            (root / SKILL_REL).parent.mkdir(parents=True)
            (root / SKILL_REL).write_text(skill_text, encoding="utf-8")
            env = dict(os.environ)
            if python3 is not None:
                shim = root / "shim"; shim.mkdir()
                (shim / "python3").write_text(python3); (shim / "python3").chmod(0o755)
                env["PATH"] = str(shim) + os.pathsep + env.get("PATH", "")
            return subprocess.run(["bash", str(root / ".claude/hooks/enforce-handoff-path.sh")],
                                  input=payload, capture_output=True, env=env).returncode

    _HANDOFF = b'{"tool_name": "Skill", "tool_input": {"skill": "handoff"}}'
    _OTHER = b'{"tool_name": "Skill", "tool_input": {"skill": "brief"}}'
    _CHATTY = "#!/bin/sh\necho 'pyenv: shim banner'\nexec %s \"$@\"\n" % sys.executable
    _BROKEN = "#!/bin/sh\nexit 1\n"
    # r1 Codex M3: the detector runs (`python3 - <file>`), but the CHECKER invocation fails — that is not a bad path.
    _CHECKER_DIES = '#!/bin/sh\nif [ "$1" = "-" ]; then exec %s "$@"; fi\nexit 1\n' % sys.executable
    # r2 Codex: a wrapper that exits 0 WITHOUT running the checker — no verdict was produced at all.
    _CHECKER_FAKES_OK = '#!/bin/sh\nif [ "$1" = "-" ]; then exec %s "$@"; fi\nexit 0\n' % sys.executable
    # r2 Codex M: the checker's FINDING reworded — detection, label and exit code untouched.
    _REWORDED = lambda s: s.replace("SKILL.md does not name", "SKILL.md omits")

    def _hook_rc_cat_fails(payload: bytes) -> int:
        with tempfile.TemporaryDirectory() as td:
            shim = Path(td); (shim / "cat").write_text("#!/bin/sh\nexit 1\n"); (shim / "cat").chmod(0o755)
            env = dict(os.environ); env["PATH"] = str(shim) + os.pathsep + env.get("PATH", "")
            return subprocess.run(["bash", str(REPO_ROOT / ".claude/hooks/enforce-handoff-path.sh")],
                                  input=payload, capture_output=True, env=env).returncode
    for name, got, want in (
        ("hook: blocks /handoff when the skill names the wrong path", _hook_rc(_HANDOFF, UPSTREAM, None), 2),
        ("hook: passes /handoff when the skill is intact", _hook_rc(_HANDOFF, GOOD, None), 0),
        ("hook: leaves another skill alone", _hook_rc(_OTHER, UPSTREAM, None), 0),
        ("⭐ hook: a CHATTY interpreter still blocks a broken /handoff (backlog #111)",
         _hook_rc(_HANDOFF, UPSTREAM, _CHATTY), 2),
        ("⭐ hook: a BROKEN interpreter warns and exits 1 — never a silent 0 (backlog #111)",
         _hook_rc(_HANDOFF, UPSTREAM, _BROKEN), 1),
        ("⭐ hook: a payload copy that FAILS warns and exits 1, not 'not mine' (backlog #111 r1)",
         _hook_rc_cat_fails(_HANDOFF), 1),
        ("⭐ hook: a TRUNCATED envelope warns and exits 1, not 'not mine' (backlog #111 r1)",
         _hook_rc(b'{"tool_name": "Skill", "tool_input": {"ski', GOOD, None), 1),
        ("⭐ hook: a checker that fails to RUN warns and exits 1 — it is not reported as a bad path (backlog #111 r1)",
         _hook_rc(_HANDOFF, GOOD, _CHECKER_DIES), 1),
        ("⭐ hook: a REWORDED checker finding still blocks — the verdict travels by receipt, not prose (backlog #111 r2)",
         _hook_rc(_HANDOFF, UPSTREAM, None, _REWORDED), 2),
        ("⭐ hook: a wrapper exiting 0 WITHOUT running the checker warns — no receipt, no pass (backlog #111 r2)",
         _hook_rc(_HANDOFF, UPSTREAM, _CHECKER_FAKES_OK), 1),
    ):
        ok = got == want
        hook_failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got} want {want}")
    failures += hook_failures

    total = len(CASES) + 3 + 10     # 3 file cases and 10 hook cases follow the text cases
    print(f"\n{total - failures}/{total} self-test cases passed")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true", help="run the case suite and exit")
    ap.add_argument("--quiet", action="store_true", help="print only on violation")
    ap.add_argument("--receipt", metavar="FILE",
                    help="write the verdict (0/1/2) to FILE once it is reached — the hook's ONLY verdict channel")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    path = REPO_ROOT / SKILL_REL
    code, messages = check_file(path)
    # ⛔ backlog #111 r2: THE RECEIPT IS THE VERDICT CHANNEL. An exit code cannot tell "checked: REVERTED" from
    # "the interpreter failed", and matching this file's ENGLISH made a rewording a silent downgrade. A receipt
    # exists only if this line ran, so a checker that never ran leaves none and the hook says so.
    if args.receipt:
        Path(args.receipt).write_text(f"{code}\n", encoding="utf-8")

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
