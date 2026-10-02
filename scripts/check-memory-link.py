#!/usr/bin/env python3
"""The tracked memory corpus is the one the harness actually reads — enforced, not assumed.

WHY THIS EXISTS. The corpus moved into `docs/memory/` on 2026-09-30 so teammates could obtain it
(the user's ruling: anything needed for team-work belongs inside the repo). The harness still reads
a DERIVED path — `~/.claude/projects/<slug>/memory`, slug = the absolute repo path with every
non-alphanumeric replaced by `-` — so `scripts/bootstrap-memory.sh` symlinks that path at the repo.

⛔ THE FAILURE THIS CATCHES IS SILENT, WHICH IS WHY IT NEEDS A MACHINE. If the symlink is missing,
nothing errors: the harness creates a fresh empty directory at that path, the corpus stops being
shared, and every recall silently reads a corpus of zero entries. "Nothing fires" and "there is no
corpus" then look identical — the exact defect `recall-llm.py`'s own `corpus_verdict` exists to
refuse, one layer up.

⚠ ADVISORY BY DEFAULT, because a guard that goes red from birth on every teammate's first clone
gets switched off (#56's measured verdict). It exits 0 with a WARNING when the link is simply
absent — that is a fresh clone, and the remedy is one command. It exits 1 only when the link exists
and points somewhere WRONG, which is a misconfiguration no one intended.

    python3 scripts/check-memory-link.py
    python3 scripts/check-memory-link.py --self-test  # 15 cases
"""
from __future__ import annotations

import pathlib
import re
import sys

OK, MISCONFIGURED = 0, 1
ROOT = pathlib.Path(__file__).resolve().parent.parent
TRACKED = ROOT / "docs" / "memory"


def slug_for(repo: pathlib.Path) -> str:
    """PURE. -> the harness's project slug: the absolute path, non-alphanumerics replaced by `-`.

    ⛔ THIS RULE IS OWNED BY `recall-llm.py:memory_dir` AND IS RESTATED HERE, WHICH IS A SECOND
    IMPLEMENTATION AND THEREFORE A DRIFT RISK — `check-vocabulary-collisions.py` exists for exactly
    this. It is written out rather than imported because this guard must run on a clone where the
    matcher may not import cleanly, and because a bootstrap SHELL script owns a third copy. The
    mitigation is a case below that pins the two Python copies to the same output.
    """
    return re.sub(r"[^A-Za-z0-9]", "-", str(repo))


def link_verdict(link_exists: bool, is_symlink: bool, target: str | None,
                 tracked: str, n_entries: int) -> tuple[int, str]:
    """PURE. -> (rc, message). Three outcomes, because they need three different responses.

    A missing link is a FRESH CLONE (advisory, one command to fix). A link to the wrong place is a
    MISCONFIGURATION (rc 1). A real directory sitting there is ALSO advisory but names the risk:
    it may hold entries that were never committed, and the bootstrap preserves rather than deletes.
    """
    if not link_exists:
        return OK, ("WARNING: the harness memory path does not exist, so the assistant reads NO "
                    "corpus here. Run `./scripts/bootstrap-memory.sh`. (Advisory: this is the "
                    "normal state of a fresh clone.)")
    if not is_symlink:
        return OK, ("WARNING: a REAL directory sits at the harness memory path, so the assistant is "
                    "reading a LOCAL corpus and not the one tracked in this repo. Its contents may "
                    "never have been committed. Run `./scripts/bootstrap-memory.sh` — it preserves "
                    "the directory rather than deleting it.")
    if target != tracked:
        return MISCONFIGURED, (f"MISCONFIGURED: the harness memory path is a symlink to {target!r}, "
                               f"not to this repo's {tracked!r}. Recall is reading another corpus.")
    if n_entries == 0:
        return MISCONFIGURED, ("MISCONFIGURED: the link is correct but resolves to ZERO entries. An "
                               "empty corpus is not 'nothing fires' — it is a corpus that cannot fire.")
    return OK, f"memory link OK — {n_entries} entries, tracked in this repo at docs/memory/"


def main() -> int:
    link = pathlib.Path.home() / ".claude" / "projects" / slug_for(ROOT) / "memory"
    exists = link.exists() or link.is_symlink()
    is_link = link.is_symlink()
    target = str(pathlib.Path(link).readlink()) if is_link else None
    n = len([p for p in link.glob("*.md") if p.name != "MEMORY.md"]) if exists else 0
    rc, msg = link_verdict(exists, is_link, target, str(TRACKED), n)
    print(msg)
    return rc


def _self_test() -> int:
    ok = fail = 0

    def check(label, thunk, want):
        nonlocal ok, fail
        try:
            got = thunk()
        except Exception as exc:  # noqa: BLE001 - a raise IS the failure here
            fail += 1
            print(f"[FAIL] {label}: got {f'raised {type(exc).__name__}: {exc}'!r} want {want!r}")
            return
        if got == want:
            ok += 1
        else:
            fail += 1
            print(f"[FAIL] {label}: got {got!r} want {want!r}")

    T = "/repo/docs/memory"
    check("a correct link with entries is OK", lambda: link_verdict(True, True, T, T, 145)[0], OK)
    check("...and it says how many entries it found",
          lambda: "145 entries" in link_verdict(True, True, T, T, 145)[1], True)
    check("a MISSING link is advisory, not a failure",
          lambda: link_verdict(False, False, None, T, 0)[0], OK)
    check("...and it names the one command that fixes it",
          lambda: "bootstrap-memory.sh" in link_verdict(False, False, None, T, 0)[1], True)
    # ⛔ BOTH advisory clauses return OK and BOTH name the bootstrap script, so every case above
    # passes with the first clause DELETED — measured: that mutation SURVIVED the sweep. Only the
    # message distinguishes them, so this case asserts the phrase unique to a missing path.
    check("a MISSING link says the path does not EXIST, not that a directory is in the way",
          lambda: ("does not exist" in link_verdict(False, False, None, T, 0)[1]
                   and "REAL directory" not in link_verdict(False, False, None, T, 0)[1]), True)
    check("a REAL directory in the way is advisory",
          lambda: link_verdict(True, False, None, T, 12)[0], OK)
    check("...and it warns the local corpus may never have been committed",
          lambda: "never have been committed" in link_verdict(True, False, None, T, 12)[1], True)
    check("a link to the WRONG place is a failure",
          lambda: link_verdict(True, True, "/somewhere/else", T, 145)[0], MISCONFIGURED)
    check("...and it quotes BOTH paths, so the reader sees which side moved",
          lambda: ("/somewhere/else" in link_verdict(True, True, "/somewhere/else", T, 145)[1]
                   and T in link_verdict(True, True, "/somewhere/else", T, 145)[1]), True)
    check("a correct link resolving to ZERO entries is a failure, not silence",
          lambda: link_verdict(True, True, T, T, 0)[0], MISCONFIGURED)
    check("...and it says an empty corpus is not 'nothing fires'",
          lambda: "cannot fire" in link_verdict(True, True, T, T, 0)[1], True)
    check("slug_for replaces every non-alphanumeric, including dots and slashes",
          lambda: slug_for(pathlib.Path("/a/b.c-d")), "-a-b-c-d")
    # ⛔ `tracked` was passed the SAME value by all eleven cases above, so nothing could tell it
    # apart from a constant and the comparison that reads it was unguarded. Found by
    # `check-fixture-variation.py`, not by review. These two vary it in both directions.
    U = "/other-repo/docs/memory"
    check("the comparison reads `tracked`, not a constant: a link to U is OK when U is tracked",
          lambda: link_verdict(True, True, U, U, 7)[0], OK)
    check("...and the SAME link is MISCONFIGURED when a different path is tracked",
          lambda: link_verdict(True, True, U, T, 7)[0], MISCONFIGURED)
    # ⛔ The drift falsifier for the second implementation named in slug_for's docstring.
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("rl", ROOT / "scripts" / "recall-llm.py")
        rl = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rl)
        want = str(rl.memory_dir.__globals__["Path"].home() / ".claude" / "projects"
                   / slug_for(ROOT) / "memory")
        check("this guard's slug agrees with recall-llm's own memory_dir",
              lambda: str(rl.memory_dir(ROOT)) if rl.memory_dir(ROOT) else want, want)
    except Exception as exc:  # noqa: BLE001
        fail += 1
        print(f"[FAIL] this guard's slug agrees with recall-llm's own memory_dir: "
              f"got {f'raised {type(exc).__name__}: {exc}'!r} want agreement")

    if fail:
        print(f"\n{ok} passed, {fail} FAILED")
        return 1
    print(f"\n{ok}/{ok + fail} self-test cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(_self_test() if "--self-test" in sys.argv else main())
