#!/usr/bin/env python3
"""Every declared `--self-test` case count is checked by an OUTSIDE observer.

WHY THIS EXISTS (backlog #69)
------------------------------
`check-plan-code.py` ends its suite with `return _drift_rc(__doc__, ok, fail)` — the docstring's
declared count is compared against the number of cases that actually ran. Replacing that line with
`return 1 if fail else 0` deletes the check and **nothing notices**, because observing it requires
observing the suite's own exit code from inside the suite.

That is not a false green: the counts are correct today. The gap is that the guard's own REMOVAL is
invisible. Round 5 had already lifted `count_drift` to module level so cases could reach it, and
three cases do — but the CALL inherited the blind spot the inline version had. A fix that corrects
the verdict without covering the mechanism.

So this runs each `--self-test` as a SUBPROCESS and compares what it printed with what its docstring
declares. Same shape as `scripts/check-test-counts.py`, which does exactly this for the jest suite,
and for the same reason: a number a program reports about itself is not evidence.

⚠ IT CHECKS ITSELF. This script is in `POPULATION`, so its own declared count is verified by the
same external run. That is the whole point — the thing that could not be self-checked now has an
outside observer, including for the observer.

ONE CONVENTION, NOT A SECOND ONE
---------------------------------
The declaration form `--self-test  # N cases` and the regex that reads it ALREADY EXIST, in
`check-plan-code.count_drift`. This imports that function rather than re-implementing the rule.
This project has measured what a second implementation of one rule does: it drifts, and the two
copies then disagree about a live page. Re-deriving the regex here would be that defect on purpose.

WHAT IS IN SCOPE, MEASURED NOT GUESSED
---------------------------------------
38 scripts under `scripts/` accept `--self-test`; only **8** declared a count in the canonical form
before this one existed (measured 2026-09-01), and this script is the ninth. Declaring is voluntary
— a script that never claimed a number is not lying — so the population is PINNED rather than
derived, and the ratchet runs both ways:

  * a pinned script stops declaring   -> FAIL. Coverage cannot shrink by deleting a claim.
  * a script declares but is unpinned -> FAIL. A new declaration cannot arrive unmeasured.

HOME IS REDIRECTED FOR EVERY CHILD, AND THAT IS STRUCTURAL
-----------------------------------------------------------
Six delivered scripts resolve `pathlib.Path.home()` at MODULE level, so under the real home their
constants name the reader's LIVE pages under `~/explainers/`. `check-plan-code.child_env` exists
because that hazard has already fired once — a destructive mutation was promoted without the
redirect. A new spawner inherits none of that protection unless it asks for it, which is exactly how
the first incident happened. So this imports `child_env` too, rather than trusting that the eight
scripts it runs happen not to write today.

FAILS IF
--------
  * a declared count disagrees with the count the suite printed;
  * a pinned script no longer declares a count, or an unpinned script starts to;
  * a child suite exits non-zero (its own cases are red — the count means nothing);
  * a child prints no parseable `N/M … passed` line  -> exit 2, CANNOT RUN, never a pass;
  * a child times out (its whole process group is killed), is killed by a signal even after
    printing a passing count, or the check of one crashes inside the pool -> exit 2, CANNOT RUN;
    the red suites are still printed alongside.

SCOPED MODE — THE LOCAL GATE (backlog #402)
--------------------------------------------
The full run starts every pinned suite, about 351 s under load. Agents ran it 366 times locally in
eight days, while CI runs it on every PR anyway. So locally the gate is SCOPED:

  * `--only <script>…` checks the named pinned suites. A name not in POPULATION is an ERROR (rc 2),
    never skipped: a typo that checks nothing would read as a pass.
  * `--changed [--base origin/master]` checks the suites the branch can have moved: the files in
    `git diff --name-only <base>...HEAD`, plus uncommitted and untracked edits (a local gate runs
    before the commit as often as after it), CLOSED, to a fixed point, over a dependency rule — a script is reached
    when its CODE imports a reached module by name, or a non-docstring string constant in it holds a
    reached file's basename; a rename counts BOTH names (how `spec_from_file_location(SCRIPTS / "check-plan-code.py")`,
    `LAUNCHER_REL` and every `docs/…` path constant name what they read). Read with `ast`, so a
    comment or a docstring mentioning a file is not a dependency; a string in an error message is,
    which over-selects — the safe direction. A dependency built at runtime from pieces is NOT seen.
  * an empty scope prints `nothing to check` and exits 0 — said, never a silent pass.
  * the POPULATION ratchet is never scoped: it only parses, so it always covers every script.

The unscoped run stays CI's (`.github/workflows/ci.yml`), unchanged.

THE SUITES RUN IN A POOL (backlog #487)
----------------------------------------
Measured on docs-only CI runs, the serial loop took 167 s and 197 s of a 6–7 min `verify` job. The
suites are independent subprocesses, so `--jobs N` (default 4, capped at the host's cores) runs them
at once. It still RE-RUNS every suite — reusing `verify`'s results would cost the independence this
script exists for (backlog #69). Each suite gets its OWN temp HOME, the report is in name order
whatever finished first, and a worker that raises or a suite that times out is CANNOT RUN.

Usage:
    python3 scripts/check-selftest-counts.py                       # every pinned suite (CI)
    python3 scripts/check-selftest-counts.py --changed             # the local gate
    python3 scripts/check-selftest-counts.py --changed --base <ref>
    python3 scripts/check-selftest-counts.py --only check-run-hook.py fixture_git.py
    python3 scripts/check-selftest-counts.py --jobs 1                # serially
    python3 scripts/check-selftest-counts.py --self-test  # 60 cases
"""
from __future__ import annotations

import argparse
import ast
import concurrent.futures
import importlib.util
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"

# MEASURED 2026-09-01: of 38 scripts accepting --self-test, 8 declared a count canonically; this
# file is the ninth, so the set below is 10. Pinned, not derived — see the docstring. Add a name
# here when a script starts declaring, or the run fails naming it.
#
# ⚠ FIVE OF THESE WERE STALE ON THE FIRST RUN, which is the debt backlog #69 predicted:
# check-anchors 14->15, check-test-counts 12->27, explainer-serve 47->71, gen-goals-page 16->15,
# page_chrome 35->47. Corrected in the same commit. `dev-process.md`'s eight quoted counts were
# separately verified against the real suites and were all ACCURATE — including the two that print
# no total at all, whose case lines were counted by hand (10 and 11).
POPULATION: frozenset[str] = frozenset({
    # ⟳ 2026-11-12, backlog #586 slice 2: pinned in the commit that creates it (a library, no caller yet).
    "strace_reads.py",
    # ⟳ 2026-10-16, pinned in the commit that creates it. Its suite went 23 → 25 → 27 → 30
    # while it was being written — twice because a mutation proved a case was missing — so a
    # docstring count with no reader would have been wrong three times in one hour. ⚠ Backlog
    # #291's branch shipped exactly this defect (`check-doc-citations.py` declared a count and
    # was absent here), which is why this entry lands with the guard rather than after it.
    "check-claim-propagation.py",
    # ⟳ 2026-10-07: gained a `--self-test`, so its declared count needs a reader.
    "codex-frontier-model.py",
    # ⟳ 2026-10-31: pinned in the commit that creates it (the review-round cap's Claude verdict).
    "record-review-verdict.py",
    # ⟳ 2026-10-02, ADR-0014's rule D2: pinned in the commit that creates it. Its suite went
    # 46 → 73 → 74 → 76 → 79 while it was being written, each step for a real reason, so a
    # docstring count nothing verifies would have been wrong four times in one evening.
    "check-main-drivable.py",
    # ⟳ 2026-10-26 (backlog #251): pinned in the commit that creates it.
    "check-diff-coverage.py",
    # ⟳ 2026-10-26 (backlog #362): pinned in the commit that creates it.
    "session-state.py",
    # ⟳ 2026-10-28 (backlog #361): pinned in the commit that creates it.
    "compaction-state.py",
    # ⟳ 2026-11-04 (PR #496 r2 X1): the sweep-red alert helper, pinned in the commit that creates it.
    "sweep-red-alert.py",
    # ⟳ 2026-11-06 (backlog #534): the batch full sweep, pinned in the commit that creates it.
    "batch-ci.py",
    # ⟳ 2026-11-09 (backlog #397): the CI-duration tripwire, pinned in the commit that creates it.
    "ci-durations.py",
    # ⟳ 2026-10-30 (backlog #410): pinned in the commit that creates it.
    "check-stalled-work.py",
    # ⟳ 2026-11-01 (backlog #440): pinned in the commit that creates it.
    "check-compaction-boundary.py",
    # ⟳ 2026-11-01 (backlog #455): pinned in the commit that creates it.
    "check-agent-long-call.py",
    # ⟳ 2026-11-01 (backlog #457): pinned in the commit that creates it.
    "check-agent-large-read.py",
    # ⟳ 2026-10-26 (backlog #223): pinned in the commit that creates it.
    "check-hook-commands.py",
    # ⟳ 2026-10-27 (backlog #364): pinned in the commit that creates it.
    "check-run-hook.py",
    # ⟳ 2026-10-27 (backlog #373): the fixture-git guard and its helper, pinned in the commit that creates them.
    "check-fixture-git-isolation.py",
    "fixture_git.py",
    # ⟳ 2026-10-19: pinned in the commit that creates it, because this guard REFUSED it until
    # it was — a declared count with no reader is exactly `a-count-with-no-owner`. Earned:
    # its suite went 16 → 18 → 19 → 24 → 26 → 37 → 39 while being written, each step for a
    # real reason (a surviving mutation, ADR-0014 D2, then five r1 CODEX findings), so an
    # unverified docstring number would have been wrong SIX times in one evening.
    "check-memory-index-budget.py",
    # ⟳ 2026-10-20: pinned in the commit that creates it, for the reason the two entries above
    # record — this guard REFUSED it otherwise ("declares a case count but is not in POPULATION,
    # so nothing checks it"). Earned the same way: its suite went 13 → 17 → 18 while it was being
    # written, each step forced by another guard rather than chosen — ADR-0014's drivable `main`,
    # then `check-fixture-variation` finding four parameters no case could tell from a constant.
    # A docstring count nothing verified would have been wrong three times in twenty minutes.
    "check-transcript-references.py",
    "check-memory-link.py",
    # ⟳ 2026-11-01 (backlog #438): the per-PR battery runner, pinned in the commit that creates it.
    "gates-for-pr.py",
    # ⟳ 2026-10-29 (backlog #393): the plan-leak push gate, pinned in the commit that creates it.
    "check-plan-leak.py",
    # ⟳ 2026-11-08 (backlog #428): the push gate's detection, pinned in the commit that creates it.
    "push-command.py",
    # ⟳ 2026-09-29, backlog #191: pinned in the commit that creates `recall-llm.py`. Its own
    # docstring is the only place its case count is stated, and a count nothing verifies is the
    # drift this file exists to refuse — doing that on a brand-new file would be that shape one
    # remove away.
    "recall-llm.py",
    "check-python-pin.py",
"check-backlog-closure.py",   # backlog #98 — the inverted row-vs-git check
    "begin-plan.py",                 # ⟳ 2026-09-04, task #224. Not a `check-*` guard, so the
                                     # ratchet contract's population never sees it — this is the
                                     # only outside observer of its declared count.
    "check-anchors.py",
    # ⟳ 2026-09-20, the closing-table guard. Pinned in the SAME commit that creates it —
    # a script that declares a count nothing verifies is exactly the drift this file refuses.
    "check-closing-table.py",
    # ⟳ 2026-09-19, the feature hub. Both pinned in the commit that wires them into CI — a script
    # that declares a count nothing verifies is the drift this file exists to refuse, and doing it
    # on a NEW file would be that shape at one remove. ⚠ BARE NAMES here and FULL PATHS in
    # `check-plan-code.EXPECTED_MUTATIONS`: the same two scripts are registered under two
    # different string shapes, which is a trap worth naming rather than rediscovering.
    "check-features.py",
    "gen-features-page.py",          # not a `check-*` guard, so the ratchet contract's population
                                     # never sees it — this is its only outside observer.
    # ⟳ 2026-09-12: gained a declared count when it gained its own manifest — the guard that
    # enforces R4 had exempted itself from it, because the escape regex matched its own docstring.
    # ⟳ 2026-09-30, backlog #201/#202. Pinned in the SAME commit that creates it — a script
    # declaring a count nothing verifies is the drift this file exists to refuse, and doing that on
    # a brand-new guard would be the shape at one remove. This guard REFUSED it until it was pinned.
    "check-rc-contract.py",
    # ⟳ 2026-10-01, backlog #196. The HOOK'S own guard, pinned in the commit that creates it — for
    # the reason this file keeps restating, and because #196's finding was that
    # `.claude/hooks/surface-recall.sh` had NO self-test, NO mutation entry and NO reader. This
    # gives it a suite and a reader; mutating the hook ITSELF still cannot be expressed, because
    # `run_mutations` runs a mutation's `file` AS the suite (`check-plan-code.py`, `run_suite(d,
    # fname)`), so a non-suite subject has no home. Filed rather than left implied.
    "check-surface-recall.py",
    "check-ratchet-contract.py",
    "check-banner-armed.py",
    # ⟳ 2026-09-23, backlog #166 + #170. The ONE owner of the observer-log record, pinned in the
    # same commit that creates it — for the reason this file keeps restating, and because it is a
    # LIBRARY: `check-ratchet-contract`'s population is `check-*` guards, so nothing else observes
    # its declared count at all. Its own first run printed 37 against a docstring saying 34.
    "observer_log.py",
    # ⟳ PR #440 r2: the ONE bounded reader of the five guards' untrusted input — a LIBRARY, pinned in the commit
    # that creates it, so this list is the outside observer of its declared count.
    "bounded_read.py",
    "check-ci-watched.py",           # ⟳ 2026-09-04: CI ran unwatched on 2 of 3 pushes
    "check-group-claims.py",         # ⟳ 2026-09-11. Pinned in the commit that creates it:
                                     # a guard declaring a count nothing verifies is the
                                     # drift this file exists to refuse.
    "check-fixture-variation.py",    # ⟳ 2026-09-11. Pinned in the same commit that creates
                                     # it, for the reason given on check-selection-card
                                     # below — and this guard REFUSED the file until it was,
                                     # which is the population half of §21 doing its job on
                                     # a file added an hour earlier.         # ⟳ 2026-09-04, task #224 residue (warn-only detector)
    "check-plan-code.py",
    "check-selection-card.py",       # ⟳ 2026-09-10. Pinned in the same commit that creates it —
                                     # shipping a declared count nothing verifies is the drift this
                                     # script exists to stop, and doing it on a NEW file would be
                                     # that shape at one remove.
    "gen-backlog-page.py",           # ⟳ 2026-09-10, backlog #110 r2 finding L-4. Not a `check-*`
                                     # guard, so nothing else observes its number, and it moved
                                     # 86 → 124 in one branch while the docstring said nothing.
    "brief-compose.py",              # ⟳ 2026-09-10, backlog #106. Not a `check-*` guard, so the
                                     # ratchet contract never sees it, and until now it declared
                                     # no count at all — the only numbers anywhere were in
                                     # `.agents/skills/brief/SKILL.md`, which handled it honestly
                                     # (a dated "14 on that day", then "since grown to 30") and
                                     # still went stale at 30 against a suite of 102. Honest prose
                                     # about a moving number still drifts; the script declares it
                                     # now and the skill cites the script.
    "check-plan-file-tags.py",       # ⟳ 2026-09-08, plan-mode retirement. It fences a rule that
                                     # NOTHING else reads any more, so an unpinned count is how
                                     # its cases would leave without a gate noticing.
    "check-plan-progress.py",        # ⟳ 2026-09-04, architecture review #5 finding E. The Stop
                                     # hook's comment declared a count NOTHING checked, and it had
                                     # drifted (said 18, suite ran 17). The number is now declared
                                     # by the script and verified here; the hook cites the script
                                     # instead of restating it, so there is one copy, not three.
    "codex-review.py",              # ⟳ 2026-09-04, task #222: docs/plugins.md claimed 35
                                    # while the suite ran 51. Now declared AND externally observed.
    "check-plan-task-order.py",
    "check-doc-citations.py",        # ⟳ 2026-10-16, r5 M7. Its declaration had said
                                    # "--self-test runs N cases" since the day it was written —
                                    # no `#`, so `count_drift`'s canonical form did not match, so
                                    # `declares()` was False and the file was never in population.
                                    # Its declared count was therefore NEVER verified while being
                                    # rewritten four times in one day (41 -> 58 -> 74 -> 64 -> 72),
                                    # and 64 was committed against a suite running 67.
                                    # ⚠ The guard's own rule — "a script declares but is unpinned
                                    # -> FAIL" — could not fire, because the near-miss declaration
                                    # meant it did not count as declaring at all. A detector that
                                    # recognises only the canonical form is silent, not loud, about
                                    # the near-miss; that is the gap this row closes.
    "check-review-rounds.py",
    "check-review-decision.py",
    "check-decision-scheme.py",   # NEW 2026-10-20 — pinned on arrival, because its
                                  # sibling above drifted 61 -> 68 -> 80 in two days

    "check-review-recorded.py",      # ⟳ 2026-09-14, r11 Medium. It had a `--self-test`, declared no
                                     # count, and was in neither direction this file reports:
                                     # `population_errors` catches pinned-but-no-longer-declaring
                                     # and declaring-but-not-pinned, and a script that does NEITHER
                                     # is reported by neither. Its suite went 31 → 113 across one
                                     # branch — while it acquired the zero-round gate AND the
                                     # final-tree rule — with nothing anywhere observing the number.
                                     # Its two closest siblings were both already pinned, and
                                     # `codex-review.py` was pinned for exactly this drift.
    "check-selftest-counts.py",      # this file — the observer observes itself
    "coverage_verdict.py",           # ⟳ 2026-09-08, backlog #91. Not a `check-*` guard, so
                                     # the ratchet contract never sees it; its cases ARE the
                                     # union's falsifiers F1-F3, and an unpinned count is how
                                     # a falsifier leaves without anyone noticing.
    "check-test-counts.py",
    "explainer-serve.py",
    "gen-goals-page.py",
    "gen-work-lines.py",
    "backfill-work-lines.py",
    "goal-tree.py",               # backlog #363, pinned on arrival
    "check-page-links.py",        # backlog #470, pinned on arrival
    "regen-pages.py",             # backlog #363 / owner decision D3, pinned on arrival
    "page_chrome.py",
    "peer-sites.py",
    # ⟳ 2026-09-07 — THE FOURTEEN, added together, and the reason is worth more than the names.
    # Paying down the R4 mutation-manifest debt kept hitting output contracts with
    # check-plan-code that bind only when a manifest first points at a file. One of them is
    # `control_is_green(rc, out)` == `rc == 0 and "passed" in out` — an exit code alone cannot
    # tell "green" from "never ran", since a script with no __main__ exits 0 in silence.
    #
    # ⛔ MEMBERSHIP HERE ALREADY ENFORCES THAT, as a side effect of running each suite and
    # parsing `N/M … passed`. MEASURED 2026-09-07: of the unpaid guards, 5 were already in this
    # set and 5 of 5 satisfied the contract; of the 14 outside it, ONE (check-producer-enumeration,
    # printing `PASS`) did not. So the enforcement was never missing — it was pointed at 14 too
    # few files. Widening an existing, mutation-tested guard beat writing a new one, which would
    # have added to the very manifest debt it existed to pay down.
    #
    # ⚠ The three catalog-reading guards are in DELIBERATELY. Their ENTRY POINT needs a live
    # Postgres; their `--self-test` rules are pure and run here in ~0.1s. Conflating those two is
    # what left three ratchets untestable for eight days once already.
    "check-anon-exposure.py",
    "check-arch-findings.py",
    "check-catalog-coverage.py",     # entry point needs the catalog; its self-test does not
    "check-docs.py",
    "check-function-revokes.py",
    "check-gate-falsifiability.py",
    "check-goal-status.py",
    "check-guard-coverage.py",
    "check-live-schema.py",          # ⟳ its summary moved to LAST in the same commit: it sat
                                     # before a multi-line epilogue, and `printed_total` reads the
                                     # LAST ratio line
    "check-merge-ready.py",
    "check-paid-caller-arrival.py",  # ~12s, the slowest member; still well inside the timeout
    "check-producer-enumeration.py",  # ⟳ printed `PASS`, so it failed control_is_green outright
    "check-roadmap-consistency.py",
    "check-sentinel-meanings.py",
    "check-storage-grant-pin.py",
    "check-vocabulary-collisions.py",
    "check-usage-pace.py",           # backlog #399 — pinned in the commit that creates it.
})

# The denominator is the total, read from the suite's summary LINE. ⟳ 2026-11-06 (backlog #506 r2 Codex M1): the
# rule that recognises that line is `check-plan-code.py`'s `summary_total` — ONE definition, borrowed below, because
# the mutation harness asks the same question ("did this suite print its summary?") and its own copy, a substring
# test for `passed`, read a case NAME as a summary. This script's copy was the RATIO plus the word `passed` anywhere on
# a line; a whole-line match over the enumerated shapes (including the `N of M` arm that
# `check-paid-caller-arrival.py`'s "32 of 32 self-test cases passed" needs) replaced both.


BORROWED = ("count_drift", "child_env", "summary_total")


def borrow_errors(mod) -> list[str]:
    """The borrowed names `mod` does NOT provide, in BORROWED order.

    ⚠ A FUNCTION RATHER THAN AN INLINE COMPREHENSION, and a mutation run is why. The rule used to
    live inside `_load_plan_code`, and the case asserting it re-derived the same comprehension over
    `pc` — a SECOND implementation of one rule, so deleting the real one left the case green. It
    was testing its own copy. Now the case calls this, and the refusal below calls this, so there
    is one rule and the case reaches it.
    """
    return [n for n in BORROWED if not hasattr(mod, n)]


def _load_plan_code():
    """Import `check-plan-code.py` by path — a hyphen makes it un-importable by name.

    Its module body is guarded by `if __name__ == "__main__"`, so importing runs no work.

    ⚠ THE BORROWED NAMES ARE CHECKED HERE, and a mutation run is why. Renaming `count_drift`
    upstream previously got past the import and died on attribute access — an uncaught
    AttributeError with rc=1, which reads as "a declared count disagrees" when the truth is
    "the instrument is broken". Borrowing a function instead of copying it is still the right
    trade, but it makes THIS script's health depend on a name in another file, so the dependency
    is asserted rather than assumed.
    """
    spec = importlib.util.spec_from_file_location(
        "_plan_code", SCRIPTS / "check-plan-code.py")
    if spec is None or spec.loader is None:
        raise ImportError("cannot load scripts/check-plan-code.py")
    mod = importlib.util.module_from_spec(spec)
    # ⚠ REGISTER IT BEFORE EXECUTING. `check-plan-code.py` uses `from __future__ import
    # annotations`, so every annotation is a STRING, and `@dataclass` resolves
    # InitVar/ClassVar by looking the module up in `sys.modules`. Without this line the
    # exec raises `AttributeError: 'NoneType' object has no attribute '__dict__'` from
    # inside dataclasses — a crash that names neither this file nor the real cause.
    # MEASURED 2026-09-08 (backlog #91): green before the module gained a dataclass, red
    # the moment it did, with nothing about the loader having changed.
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    missing = borrow_errors(mod)
    if missing:
        raise ImportError(
            f"scripts/check-plan-code.py no longer defines {', '.join(missing)} — this script "
            f"borrows them rather than copying the rule. Re-point it, or the counts go unchecked")
    return mod


def declares(src: str, count_drift) -> bool:
    """True when the module docstring carries a canonical count declaration.

    Asks `count_drift` rather than re-matching the regex: passing an actual it cannot equal
    means a MISSING declaration is the only way to get the CANNOT RUN answer back.
    """
    try:
        doc = ast.get_docstring(ast.parse(src)) or ""
    except SyntaxError:
        return False
    return "CANNOT RUN" not in (count_drift(doc, -1) or "")


def declaring_scripts(root: Path, count_drift) -> set[str]:
    found = set()
    for p in sorted((root / "scripts").glob("*.py")):
        src = p.read_text(encoding="utf-8")
        if "--self-test" in src and declares(src, count_drift):
            found.add(p.name)
    return found


def population_errors(found: set[str], pinned: frozenset[str]) -> list[str]:
    out = []
    for name in sorted(pinned - found):
        out.append(f"{name}: pinned in POPULATION but no longer declares a case count. "
                   f"Restore the `--self-test  # N cases` line, or remove it from POPULATION "
                   f"and say why — coverage cannot shrink silently.")
    for name in sorted(found - pinned):
        out.append(f"{name}: declares a case count but is not in POPULATION, so nothing checks "
                   f"it. Add it.")
    return out


def run_self_test(script: Path, env: dict[str, str], timeout: float = 600,
                  grace: float = 2.0) -> tuple[int, str]:
    """`script --self-test` in its OWN session, so a timeout reaches every process it started.

    ⛔ `subprocess.run(timeout=…)` kills only the direct child. A suite that started a helper and
    hung left that helper running after CANNOT RUN — holding a core the pool's other slots wanted,
    and writing into a temp HOME that was being deleted (PR #487 r1). So the whole group gets
    SIGTERM, then SIGKILL after `grace`. A descendant that leaves the group (`setsid`) is not
    reached — the same stated bound as the repo's hooks."""
    proc = subprocess.Popen([sys.executable, str(script), "--self-test"], cwd=str(ROOT), env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            start_new_session=True)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        kill_group(proc, grace)
        raise
    return proc.returncode, out + err


def kill_group(proc: subprocess.Popen, grace: float) -> None:
    """SIGTERM to `proc`'s process group, SIGKILL to it after `grace`, then reap `proc`.

    The leader is NOT reaped until after the SIGKILL, so the group id cannot be reused by an
    unrelated process in between."""
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(proc.pid, sig)
        except ProcessLookupError:
            break
        if sig == signal.SIGTERM:
            time.sleep(grace)
    try:
        proc.communicate(timeout=grace)
    except subprocess.TimeoutExpired:   # a pipe held by a process that escaped the group
        proc.kill()
        proc.wait()


def printed_total(out: str) -> int | None:
    """The denominator of the LAST summary line, or None if there is none — `check-plan-code`'s `summary_total`.

    ⚠ LAST, NOT FIRST, and this script is why. The first version took the first match and was
    wrong on its OWN suite: the case labels here quote example summaries (`` `12/12 … passed` ``),
    which match the pattern, so it read 12 while the suite printed 13. A guard whose test data
    looks like its input is exactly where a first-match parser breaks — and only putting this
    script in POPULATION surfaced it. Summary lines are last by convention in every member.

    ⚠ STATED LIMIT: a script printing a SECOND summary after the main one — `check-dashboard-entry`
    ends with `6/6 cannot-run cases passed` — would have that trailing number read as its total.
    It declares no count today so it is out of population; if it ever declares one, the mismatch
    surfaces as a loud DRIFT (77 vs 6), not a silent pass. The case below pins that behaviour so
    it is a known shape rather than a surprise.
    """
    return _summary_total()(out)


_SUMMARY: list = []


def _summary_total():
    """`check-plan-code.py`'s `summary_total`, loaded once. `main` primes it before the pool starts, so the suites'
    threads never race to load it."""
    if not _SUMMARY:
        _SUMMARY.append(_load_plan_code().summary_total)
    return _SUMMARY[0]


# ── the pool (backlog #487) ─────────────────────────────────────────────────────────────────────
# MEASURED on docs-only CI runs: this step took 167 s and 197 s of a 6–7 min `verify` job, because it
# ran every pinned suite ONE AFTER ANOTHER. The suites are independent subprocesses, so they now run
# in a bounded pool. ⛔ It still RE-RUNS every suite; reusing `verify`'s own results would make this
# a less independent observer, which is the whole of backlog #69.
DEFAULT_JOBS = 4   # ubuntu-latest has 4 vCPUs; capped below by the host's count either way


def pool_size(requested: int | None, cpus: int | None) -> int:
    """How many suites run at once: the request (default DEFAULT_JOBS), never more than the host's
    cores, never fewer than one. An UNKNOWN core count (`os.cpu_count()` is None) is one — serial is
    slower, never wrong."""
    want = DEFAULT_JOBS if requested is None else requested
    return max(1, min(want, cpus or 1))


def run_suites(names: list[str], job, jobs: int) -> list[tuple[str, str] | None]:
    """`job(name)` for every name, at most `jobs` at once; the outcomes IN THE ORDER OF `names`.

    ⚠ ORDER IS THE GIVEN ORDER, NEVER COMPLETION ORDER — so a report reads the same on every run
    and a diff of two reports shows a real change, not a scheduling accident.

    ⛔ A WORKER THAT RAISES IS CANNOT RUN, NEVER A PASS. Before the pool an exception in the loop
    crashed the whole script loudly; inside a pool a future's exception is only seen if someone
    asks for it, so a dropped one would read as a suite with nothing wrong."""
    outcomes: dict[str, tuple[str, str] | None] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = {pool.submit(job, name): name for name in names}
        for fut in concurrent.futures.as_completed(futures):
            name = futures[fut]
            try:
                outcomes[name] = fut.result()
            except Exception as exc:  # noqa: BLE001 — reported as CANNOT RUN, by name
                outcomes[name] = ("cannot", f"{name}: the check itself crashed "
                                            f"({type(exc).__name__}: {exc}). NOT CHECKED.")
    return [outcomes[name] for name in names]


def check_one(script: Path, env: dict[str, str], count_drift, run=None) -> tuple[str, str] | None:
    """One suite's verdict: None (its count agrees), ("problem", why) or ("cannot", why)."""
    name = script.name
    try:
        rc, out = (run or run_self_test)(script, env)
    except subprocess.TimeoutExpired:
        return ("cannot", f"{name}: --self-test did not finish. NOT CHECKED.")
    if rc < 0:
        return ("cannot", f"{name}: --self-test was killed by signal {-rc} before it finished, "
                          f"so whatever count it printed is not a verdict. NOT CHECKED.")
    if rc != 0:
        return ("problem", f"{name}: --self-test exited {rc} — its own cases are red, so its "
                           f"declared count proves nothing. Fix the suite first.")
    total = printed_total(out)
    if total is None:
        return ("cannot", f"{name}: --self-test printed no `N/M … passed` line, so the count "
                          f"could not be read. NOT CHECKED.")
    doc = ast.get_docstring(ast.parse(script.read_text(encoding="utf-8"))) or ""
    why = count_drift(doc, total)
    return ("problem", f"{name}: {why}") if why else None


def audit(root: Path, pinned: frozenset[str], count_drift, child_env,
          only: frozenset[str] | None = None, jobs: int = 1, run=None) -> tuple[list[str], list[str]]:
    """(problems, cannot_run). Kept separate so a cannot-run is never reported as a pass.

    `only` scopes which suites RUN; the population ratchet always covers every script. `jobs`
    suites run at once (`run_suites`); `run` replaces `run_self_test`, for the self-test.

    ⛔ EVERY SUITE GETS ITS OWN HOME. Serially, one shared temp HOME was harmless — one suite at a
    time. Concurrently, two suites writing the same `~/…` path would collide, which is the
    shared-directory shape backlog #388's flake had. This parent does not redirect TMPDIR itself:
    each suite's `fixture_git.isolated()` nests its own `fixture-tmp-*` scratch directory under it and
    removes it on exit (backlog #512), so two concurrent suites never share one. That keeps
    `check-run-hook.world_base`'s ancestors (backlog #388) the same, plus one sparse directory."""
    problems: list[str] = []
    cannot: list[str] = []

    found = declaring_scripts(root, count_drift)
    problems.extend(population_errors(found, pinned))

    def job(name: str) -> tuple[str, str] | None:
        with tempfile.TemporaryDirectory() as td:
            return check_one(root / "scripts" / name, child_env(Path(td)), count_drift, run)

    names = sorted(pinned & found if only is None else pinned & found & only)
    for outcome in run_suites(names, job, jobs):
        if outcome is not None:
            (problems if outcome[0] == "problem" else cannot).append(outcome[1])
    return problems, cannot


# ── scoped mode (backlog #402) ──────────────────────────────────────────────────────────────────
class CannotScope(Exception):
    """The scope could not be computed (git failed, a name is unknown): rc 2, never a pass."""


def code_refs(src: str) -> tuple[frozenset[str], tuple[str, ...]]:
    """(module names imported, non-docstring string constants) of `src`. Unparseable -> nothing.

    Comments never reach the AST, and docstrings are dropped by position, so PROSE naming a file is
    not a dependency — only code that imports it or holds its name in a string."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return frozenset(), ()
    docs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                docs.add(id(body[0].value))
    imports, strings = set(), []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            imports.add(node.module.split(".")[0])
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docs:
            strings.append(node.value)
    return frozenset(imports), tuple(strings)


def depends_on(refs: tuple[frozenset[str], tuple[str, ...]], path: str) -> bool:
    """True when code with `refs` imports `path` (a `.py` by its stem) or holds its basename."""
    imports, strings = refs
    p = Path(path)
    if p.suffix == ".py" and p.stem in imports:
        return True
    return any(p.name in s for s in strings)


def reached(changed: set[str], sources: dict[str, str]) -> set[str]:
    """`changed`, plus — to a FIXED POINT — every `scripts/<name>` that imports a reached module by
    stem or holds a reached path's basename in a non-docstring string.

    `sources` maps a script's basename to its text. Both edges are transitive: a helper that a pinned
    suite loads BY FILE NAME (`spec_from_file_location`) puts that helper's own imports inside the
    suite exactly as an `import` would, so a one-hop string edge left helper -> (import) -> loaded
    script -> suite unreached (PR #450 r1, Codex finding 2, constructed). The cost of closing the
    string edge is real and accepted: any script that names many others in a string reaches every one
    of them, and through it whatever loads or names it. (⟳ backlog #533: the largest such list, the
    `EXPECTED_MUTATIONS` pins keyed by every script's path, moved out of `check-plan-code.py` into
    `scripts/mutations/expected_mutations.py`, which is not a `scripts/*.py` source here, so that cost
    shrank.) Over-selecting is the safe direction; the full run is CI's."""
    refs = {name: code_refs(src) for name, src in sources.items()}
    reach = set(changed)
    grew = True
    while grew:
        grew = False
        for name, r in refs.items():
            key = f"scripts/{name}"
            if key not in reach and any(depends_on(r, p) for p in reach):
                reach.add(key)
                grew = True
    return reach


def git_lines(root: Path, *args: str) -> list[str]:
    proc = subprocess.run(["git", *args], cwd=str(root), capture_output=True, text=True)
    if proc.returncode != 0:
        raise CannotScope(f"`git {' '.join(args)}` exited {proc.returncode}: {proc.stderr.strip()}")
    return [ln for ln in proc.stdout.split("\n") if ln]


def changed_paths(root: Path, base: str) -> set[str]:
    """What the branch moved: committed since the merge base, plus uncommitted and untracked edits."""
    # `--no-renames`: by default `--name-only` prints a rename's NEW name only, and a suite that names the
    # OLD one (a launcher it runs) would then be unreached — a false green (PR #450 r1, both halves).
    return (set(git_lines(root, "diff", "--name-only", "--no-renames", f"{base}...HEAD"))
            | set(git_lines(root, "diff", "--name-only", "--no-renames", "HEAD"))
            | set(git_lines(root, "ls-files", "--others", "--exclude-standard")))


def only_names(names: list[str], pinned: frozenset[str]) -> frozenset[str]:
    """`--only`'s names as POPULATION basenames. An unknown name RAISES — a typo must not check nothing."""
    picked = {n[len("scripts/"):] if n.startswith("scripts/") else n for n in names}
    unknown = sorted(picked - pinned)
    if unknown:
        raise CannotScope(f"not in POPULATION: {', '.join(unknown)} — no declared count to check "
                          f"(a name, e.g. check-run-hook.py)")
    return frozenset(picked)


def changed_scope(root: Path, pinned: frozenset[str], base: str) -> frozenset[str]:
    """The pinned suites `--changed` runs: the branch's changed paths, closed over the dependency rule."""
    sources = {p.name: p.read_text(encoding="utf-8") for p in sorted((root / "scripts").glob("*.py"))}
    reach = reached(changed_paths(root, base), sources)
    return frozenset(n for n in pinned if f"scripts/{n}" in reach)


def _positive(text: str) -> int:
    n = int(text)
    if n < 1:
        raise argparse.ArgumentTypeError(f"--jobs must be at least 1, got {n}")
    return n


def report(problems: list[str], cannot: list[str]) -> int:
    """Print every failure, and return 2 if any suite is CANNOT RUN, else 1 if any is red, else 0.

    ⚠ BOTH LISTS ARE PRINTED. Returning after the CANNOT RUN list hid the red suites until the
    CANNOT RUN was fixed and the run repeated (PR #487 r1)."""
    if problems:
        print("declared self-test counts disagree with what the suites printed:\n")
        for p in problems:
            print(f"  ✗ {p}")
    if cannot:
        print("CANNOT RUN — a declared count could not be read. Treat these as NOT CHECKED:\n",
              file=sys.stderr)
        for c in cannot:
            print(f"  ? {c}", file=sys.stderr)
        return 2
    return 1 if problems else 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--self-test" in argv:
        return self_test()
    ap = argparse.ArgumentParser(description="Every declared --self-test case count, checked by running it.")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--only", nargs="+", metavar="SCRIPT", help="check only these pinned suites")
    mode.add_argument("--changed", action="store_true", help="check only the suites this branch can move")
    ap.add_argument("--base", default="origin/master", help="the ref --changed diffs against")
    ap.add_argument("--jobs", type=_positive, default=None, metavar="N",
                    help=f"suites run at once (default {DEFAULT_JOBS}, capped at the host's cores)")
    args = ap.parse_args(argv)
    jobs = pool_size(args.jobs, os.cpu_count())

    try:
        pc = _load_plan_code()
    except (ImportError, OSError) as exc:
        print(f"CANNOT RUN — {exc}. Treat this as NOT RUN.", file=sys.stderr)
        return 2
    _SUMMARY[:] = [pc.summary_total]

    only = None
    try:
        if args.only:
            only = only_names(args.only, POPULATION)
        elif args.changed:
            only = changed_scope(ROOT, POPULATION, args.base)
    except CannotScope as exc:
        print(f"CANNOT RUN — {exc}. Treat this as NOT RUN.", file=sys.stderr)
        return 2
    scope = ("" if only is None else
             " (scope: --only)" if args.only else f" (scope: --changed against {args.base})")

    problems, cannot = audit(ROOT, POPULATION, pc.count_drift, pc.child_env, only, jobs)

    rc = report(problems, cannot)
    if rc:
        return rc

    if only is None:
        print(f"self-test counts: {len(POPULATION)} script(s) declare a count, "
              f"every one verified by running it ({jobs} at a time)")
    elif not only:
        print(f"self-test counts: nothing to check{scope} — no changed file reaches a pinned suite; "
              f"the population ratchet passed over all {len(POPULATION)}. The full run is CI's.")
    else:
        print(f"self-test counts: {len(only)} of {len(POPULATION)} pinned suite(s) verified by running "
              f"them{scope}: {', '.join(sorted(only))}. The full run is CI's.")
    return 0


# ── self-test ───────────────────────────────────────────────────────────────────────────────────
# ⚠ THE FAILURE LINE IS A CONTRACT. `check-plan-code.py` reads red cases from lines that START WITH
# `[FAIL] `, split on the LAST ": got ". A prettier form parses as ZERO red cases, which reads as a
# broken manifest rather than a working guard. Measured once before, over 12 mutations.
def self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: every `--self-test` runs isolated (backlog #382)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    cases, failures = 0, 0

    def check(label: str, got, want) -> None:
        nonlocal cases, failures
        cases += 1
        if got == want:
            print(f"  ✓ {label}")
        else:
            failures += 1
            print(f"  [FAIL] {label}: got {got!r} want {want!r}")

    pc = _load_plan_code()
    cd = pc.count_drift

    # ── the borrowed convention still behaves as this script assumes ──
    check("a canonical declaration is detected",
          declares('"""x\n\n    --self-test  # 7 cases\n"""', cd), True)
    check("a bare `7 cases` mention is NOT a declaration",
          declares('"""x\n\n    runs 7 cases\n"""', cd), False)
    check("no docstring is not a declaration", declares("x = 1", cd), False)
    check("unparseable source is not a declaration", declares("def (:", cd), False)

    # ── the printed-total parser ──
    check("a `12/12 self-test cases passed` summary reads 12",
          printed_total("\n12/12 self-test cases passed"), 12)
    check("a `self-test: 9/9 passed` summary reads 9", printed_total("self-test: 9/9 passed"), 9)
    # ⚠ THE BARE RATIO MUST COME AFTER THE SUMMARY. Written the other way round this case was
    # VACUOUS — measured 2026-09-01 by deleting the `passed` filter, which still returned 8,
    # because last-match-wins discards an extra match that appears EARLIER. The `passed`
    # requirement can only be observed by a stray ratio that would otherwise win.
    check("a ratio on a line without the word is ignored",
          printed_total("8/8 passed\nscanned 3/4 files"), 8)
    check("no parseable line -> None, never 0",
          printed_total("everything is fine"), None)
    # THE DEFECT THIS SCRIPT FOUND IN ITSELF. A case label that quotes an example summary matches
    # the pattern; taking the first match read the label instead of the suite's real total.
    check("an earlier quoted summary does not win over the real one",
          printed_total("  ok `12/12 cases passed` -> 12\n\n13/13 self-test cases passed"), 13)
    # The stated limit, pinned so it is a known shape rather than a surprise.
    check("a trailing SECOND summary is what gets read (known limit)",
          printed_total("77/77 passed\n6/6 cannot-run cases passed"), 6)
    # check-paid-caller-arrival.py really prints this shape.
    check("`32 of 32 … passed` reads 32",
          printed_total("32 of 32 self-test cases passed"), 32)
    # Found by mutating this script: a renamed upstream helper used to crash with rc=1, which is
    # the code for "a count disagrees" — the opposite of what happened.
    check("every borrowed name is present upstream", borrow_errors(pc), [])
    # …and the rule itself reports a missing name rather than swallowing it. Without this the
    # refusal in `_load_plan_code` has no case at all: the line above passes on a HEALTHY module
    # whether the rule works or returns [] unconditionally.
    check("a missing borrowed name is named, not swallowed",
          borrow_errors(object()), list(BORROWED))

    # ── the population ratchet, both directions ──
    pinned = frozenset({"a.py", "b.py"})
    check("a fully declared population is clean",
          population_errors({"a.py", "b.py"}, pinned), [])
    check("a pinned script that stopped declaring fails",
          len(population_errors({"a.py"}, pinned)), 1)
    # `any(...)` rather than `[0]`. Indexing RAISES when the list is empty, and an uncaught
    # exception kills the suite — every later case then prints nothing, so a mutation that
    # emptied this list would be scored on a truncated `[FAIL]` list rather than a red case.
    check("…and it names the script",
          any("b.py" in e for e in population_errors({"a.py"}, pinned)), True)
    check("a new declaration outside POPULATION fails",
          len(population_errors({"a.py", "b.py", "c.py"}, pinned)), 1)
    # A drifted count must be reported THROUGH the borrowed function, not a local copy.
    check("a drifted count is reported by count_drift",
          "[DRIFT]" in (cd('"""x\n\n    --self-test  # 5 cases\n"""', 6) or ""), True)

    # ── scoped mode (backlog #402): the dependency rule ──
    # A refusal comes back as TEXT, never as an exception: an uncaught one would end the suite and
    # leave a mutation run with no `[FAIL]` line to attribute.
    def result(fn):
        try:
            return fn()
        except CannotScope as exc:
            return f"CannotScope: {exc}"

    check("a docstring or a comment naming a file is NOT a reference",
          depends_on(code_refs('"""reads a.py"""\n# a.py\ndef f():\n    """a.py"""\n'), "scripts/a.py"), False)
    check("a string constant holding the basename IS a reference",
          depends_on(code_refs('X = "scripts/a.py"\n'), "scripts/a.py"), True)
    check("an import of the stem IS a reference",
          depends_on(code_refs("import fixture_git\n"), "scripts/fixture_git.py"), True)
    check("an import matches a .py only — `import backlog` does not reach docs/backlog.md",
          depends_on(code_refs("import backlog\n"), "docs/backlog.md"), False)
    srcs = {"a.py": "", "b.py": 'P = "a.py"\n', "c.py": 'P = "b.py"\n', "d.py": "import b\n",
            "e.py": "import d\n", "f.py": ""}
    check("a changed script is reached, an unrelated one is not",
          sorted(reached({"scripts/f.py"}, srcs)), ["scripts/f.py"])
    check("an unparseable script reaches nothing, and is not itself reached",
          sorted(reached({"scripts/a.py"}, {"a.py": "", "x.py": "def (: a.py"})), ["scripts/a.py"])
    check("string and import edges are BOTH closed to a fixpoint",
          sorted(reached({"scripts/a.py"}, srcs)),
          ["scripts/a.py", "scripts/b.py", "scripts/c.py", "scripts/d.py", "scripts/e.py"])
    check("helper -> (import) -> script loaded by path -> suite is reached",
          sorted(reached({"scripts/h.py"}, {"h.py": "", "m.py": "import h\n",
                                            "suite.py": 'M = "m.py"\n', "other.py": ""})),
          ["scripts/h.py", "scripts/m.py", "scripts/suite.py"])
    check("--only accepts a bare name or a scripts/ path",
          result(lambda: only_names(["a.py", "scripts/b.py"], frozenset({"a.py", "b.py", "c.py"}))),
          frozenset({"a.py", "b.py"}))
    check("--only with a name outside POPULATION is an ERROR, never a skip",
          str(result(lambda: only_names(["a.py", "nope.py"], frozenset({"a.py"})))).startswith(
              "CannotScope: not in POPULATION: nope.py"), True)

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "scripts").mkdir()

        def git(*args: str) -> None:
            subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=str(root),
                           check=True, capture_output=True)

        for n, body in (("a.py", "A = 1\n"), ("b.py", "import a\n"), ("c.py", "C = 1\n")):
            (root / "scripts" / n).write_text(body)
        git("init", "-q")
        git("add", "-A")
        git("commit", "-q", "-m", "base")
        git("branch", "base")
        pinned = frozenset({"a.py", "b.py", "c.py", "d.py"})
        check("a clean branch with no commits is an EMPTY scope", changed_scope(root, pinned, "base"), frozenset())
        (root / "scripts/c.py").write_text("C = 2\n")
        git("commit", "-qam", "c moves")
        # The BASE moves after the fork: three dots diff from the merge base, so its own later
        # commit is not the branch's change. Two dots would put a.py in scope.
        git("checkout", "-q", "base")
        (root / "scripts/a.py").write_text("A = 9\n")
        git("commit", "-qam", "the base moves on")
        git("checkout", "-q", "-")
        check("--changed reaches a script committed since the base",
              changed_scope(root, pinned, "base"), frozenset({"c.py"}))
        check("…and against HEAD the committed change is out of scope", changed_scope(root, pinned, "HEAD"),
              frozenset())
        (root / "scripts/a.py").write_text("A = 2\n")
        check("an UNCOMMITTED edit is in scope, with its importer",
              changed_scope(root, pinned, "base"), frozenset({"a.py", "b.py", "c.py"}))
        git("checkout", "-q", "--", "scripts/a.py")
        (root / "scripts/r.py").write_text('R = "launcher.sh"\n')
        (root / "launcher.sh").write_text("#!/bin/sh\n")
        git("add", "-A")
        git("commit", "-qm", "r reads the launcher")
        git("branch", "-f", "base2", "HEAD")
        git("mv", "launcher.sh", "launcher-v2.sh")
        check("a STAGED rename reaches the suite that names the OLD name",
              "r.py" in changed_scope(root, frozenset({"r.py"}), "base2"), True)
        git("commit", "-qm", "rename the launcher")
        check("a COMMITTED rename reaches the suite that names the OLD name",
              "r.py" in changed_scope(root, frozenset({"r.py"}), "base2"), True)
        git("reset", "-q", "--hard", "HEAD~1")
        (root / "scripts/a.py").write_text("A = 2\n")
        (root / "scripts/d.py").write_text("D = 1\n")
        check("an UNTRACKED script is in scope", "d.py" in changed_scope(root, pinned, "base"), True)
        check("an unknown base is CANNOT RUN, never an empty scope",
              str(result(lambda: changed_scope(root, pinned, "no-such-ref"))).startswith("CannotScope: `git diff"), True)

    # ── scoped mode: `only` scopes which suites RUN, never the population ratchet ──
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "scripts").mkdir()
        decl = '"""x\n\n    --self-test  # 1 cases\n"""\nimport sys\n'
        (root / "scripts/ok.py").write_text(decl + 'print("1/1 passed")\n')
        (root / "scripts/red.py").write_text(decl + 'print("0/1 passed")\nsys.exit(1)\n')
        pinned = frozenset({"ok.py", "red.py"})
        check("unscoped, the red suite is reported",
              [p.split(":")[0] for p in audit(root, pinned, cd, pc.child_env)[0]], ["red.py"])
        check("scoped to the green one, the red suite does not run", audit(root, pinned, cd, pc.child_env,
                                                                        frozenset({"ok.py"})), ([], []))
    with tempfile.TemporaryDirectory() as td:
        other = Path(td)
        (other / "scripts").mkdir()
        (other / "scripts/ok.py").write_text(decl + 'print("1/1 passed")\n')
        (other / "scripts/new.py").write_text(decl + 'print("1/1 passed")\n')
        check("…but the population ratchet is never scoped",
              any("new.py" in p for p in audit(other, frozenset({"ok.py"}), cd, pc.child_env, frozenset())[0]), True)
        check("--changed outside a git checkout is CANNOT RUN, never an empty scope",
              str(result(lambda: changed_scope(other, frozenset({"ok.py"}), "HEAD"))).startswith(
                  "CannotScope: `git diff"), True)

    # ── the pool (backlog #487) ──
    check("the pool defaults to DEFAULT_JOBS on a host with more cores", pool_size(None, 16), DEFAULT_JOBS)
    check("the pool never exceeds the host's cores", pool_size(8, 2), 2)
    check("an unknown core count runs serially, never zero workers", pool_size(None, None), 1)

    # `a` waits until the COLLECTOR has consumed `b`'s result, so `a` can only see it if both run AT ONCE,
    # and `b` is always COLLECTED FIRST. The wait is bounded: a serial pool makes `a` report the miss, never hang.
    # ⛔ backlog #495: `a` used to wait only for `b` to START (an event `b` set). `as_completed` yields futures that
    # are ALREADY done in no defined order, so when the main thread reached the loop late both were done and
    # `b` was collected first only by luck — the completion-order mutant SURVIVED two CI runs of PR #489. Now the event
    # is set by the collector itself (`collecting`, wrapping `as_completed`), AFTER it has taken `b`, so `a`
    # cannot finish before `b` is collected: the completion order is b, a on every run.
    import threading

    def ordered(wait: float):
        consumed = threading.Event()

        def job(name: str):
            if name == "a":
                return ("problem", "a saw b") if consumed.wait(wait) else ("problem", "a ran alone")
            return ("problem", "b")
        return job, consumed

    def collected(names, wait: float, jobs: int):
        """`run_suites` with `ordered(wait)`, its `as_completed` wrapped to set the event once the collector
        has taken a result — the generator resumes only when the loop asks for the NEXT future."""
        job, consumed = ordered(wait)
        real = concurrent.futures.as_completed

        def collecting(fs, timeout=None):
            for fut in real(fs, timeout=timeout):
                yield fut
                consumed.set()
        concurrent.futures.as_completed = collecting
        try:
            return run_suites(names, job, jobs)
        finally:
            concurrent.futures.as_completed = real

    got = collected(["a", "b"], 10, 2)
    check("two suites run AT ONCE in a pool of two", got[0], ("problem", "a saw b"))
    check("outcomes come back in the given order, not completion order", [g[1] for g in got],
          ["a saw b", "b"])
    # backlog #506 (1): the case above once saw `b` finish first only when the scheduler let it (fixed by #495, above).
    # Here the completion order is FORCED a second way: `as_completed` yields the futures in reverse, so an
    # implementation returning completion order fails on every run, over THREE suites.
    _real_as_completed = concurrent.futures.as_completed

    def _reversed_completion(fs, timeout=None):
        concurrent.futures.wait(list(fs), timeout=timeout)
        return list(reversed(list(fs)))
    concurrent.futures.as_completed = _reversed_completion
    try:
        _forced = run_suites(["a", "b", "c"], lambda n: ("problem", n), 3)
    finally:
        concurrent.futures.as_completed = _real_as_completed
    check("backlog #506: outcomes come back in the given order when completion is forced to the reverse",
          [g[1] for g in _forced], ["a", "b", "c"])
    # The other value of `jobs`: a pool of one is serial, so `a` finishes before `b` starts.
    check("a pool of one runs the suites one at a time",
          [g[1] for g in collected(["a", "b"], 0.3, 1)], ["a ran alone", "b"])

    def crashing_job(name: str):
        if name == "boom":
            raise RuntimeError("worker died")
        return None

    got = run_suites(["boom", "fine"], crashing_job, 2)
    check("a worker that RAISES is CANNOT RUN, never a pass",
          got[0] is not None and got[0][0] == "cannot" and "worker died" in got[0][1], True)
    check("…and the other suites are still checked", got[1], None)

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "scripts").mkdir()
        decl = '"""x\n\n    --self-test  # 1 cases\n"""\nimport os, sys\n'
        homes = root / "homes"
        homes.mkdir()
        for n in ("h1.py", "h2.py"):
            (root / "scripts" / n).write_text(
                decl + f'open({str(homes / n)!r}, "w").write(os.environ["HOME"])\nprint("1/1 passed")\n')
        pinned = frozenset({"h1.py", "h2.py"})
        audit(root, pinned, cd, pc.child_env, jobs=2)
        seen = {n: (homes / n).read_text() if (homes / n).exists() else None for n in pinned}
        check("every suite runs under its OWN home, never a shared one",
              None not in seen.values() and seen["h1.py"] != seen["h2.py"], True)

        def fake(script: Path, env):
            if script.name == "h1.py":
                raise subprocess.TimeoutExpired("x", 600)
            raise OSError("cannot start")
        problems, cannot = audit(root, pinned, cd, pc.child_env, jobs=2, run=fake)
        check("a TIMED-OUT suite in the pool is CANNOT RUN, never a pass",
              problems == [] and any(c.startswith("h1.py: --self-test did not finish") for c in cannot), True)
        check("a suite that cannot START is CANNOT RUN, never a pass",
              any(c.startswith("h2.py: the check itself crashed") for c in cannot), True)

    # ── PR #487 r1: a run that could not complete, and what `main` reports ──
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        # The helper IGNORES SIGTERM, so only the SIGKILL that follows it can remove the helper.
        pidfile = root / "helper.pid"
        (root / "hangs.py").write_text(
            "import subprocess, sys, time\n"
            "h = subprocess.Popen([sys.executable, '-c', 'import signal, time; "
            "signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)'])\n"
            f"open({str(pidfile)!r}, 'w').write(str(h.pid))\n"
            "time.sleep(60)\n")
        timed_out = False
        try:
            run_self_test(root / "hangs.py", dict(os.environ), timeout=3, grace=0.2)
        except subprocess.TimeoutExpired:
            timed_out = True
        helper = int(pidfile.read_text()) if pidfile.exists() else None
        gone = False
        for _ in range(40):
            try:
                os.kill(helper, 0) if helper else None
            except ProcessLookupError:
                gone = True
                break
            time.sleep(0.05)
        if helper and not gone:
            os.kill(helper, signal.SIGKILL)   # never leave the probe's own helper behind
        check("a TIMED-OUT suite's descendants are killed with it, never left running",
              (timed_out, helper is not None, gone), (True, True, True))

        (root / "dies.py").write_text(
            "import os, signal\nprint('1/1 passed', flush=True)\nos.kill(os.getpid(), signal.SIGKILL)\n")
        got = check_one(root / "dies.py", dict(os.environ), cd)
        check("a suite KILLED BY A SIGNAL is CANNOT RUN even after printing a passing count",
              got is not None and got[0] == "cannot" and got[1].startswith(
                  "dies.py: --self-test was killed by signal 9"), True)

        # The contrasting inputs: a suite that FINISHES returns its own rc and output, under the env
        # it was given; and a count the docstring disagrees with is a named problem.
        (root / "echo.py").write_text("import os, sys\nprint(os.environ['MARK'])\nsys.exit(3)\n")
        check("a suite that finishes in time returns its rc and output, under the env it was given",
              run_self_test(root / "echo.py", {**os.environ, "MARK": "m7"}, timeout=60, grace=1.0),
              (3, "m7\n"))
        (root / "drifts.py").write_text('"""x"""\n')
        check("a printed count the docstring disagrees with is a problem, by name",
              check_one(root / "drifts.py", {}, lambda doc, total: f"declares 2, printed {total}",
                        run=lambda script, env: (0, "1/1 passed")),
              ("problem", "drifts.py: declares 2, printed 1"))

    import contextlib
    import io
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = report(["red.py: drift"], ["hung.py: did not finish"])
    check("with a CANNOT RUN suite the red suites are STILL printed, and rc is 2",
          (rc, "red.py: drift" in out.getvalue(), "hung.py" in err.getvalue()), (2, True, True))
    with contextlib.redirect_stdout(io.StringIO()):
        alone = (report(["red.py: drift"], []), report([], []))
    check("red suites alone are rc 1, nothing wrong is rc 0", alone, (1, 0))

    # `main`'s own wiring: the audit and the plan-code import are replaced, the core count fixed.
    seen_jobs: list[int] = []

    def fake_audit(root, pinned, count_drift, child_env, only=None, jobs=1, run=None):
        seen_jobs.append(jobs)
        return [], []
    import types
    saved = (globals()["audit"], globals()["_load_plan_code"], os.cpu_count)
    globals()["audit"] = fake_audit
    globals()["_load_plan_code"] = lambda: types.SimpleNamespace(count_drift=cd, child_env=pc.child_env,
                                                                      summary_total=pc.summary_total)
    os.cpu_count = lambda: 8
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            rc = main(["--jobs", "3"])
        check("`main` passes --jobs through to the pool", (rc, seen_jobs), (0, [3]))
        seen_jobs.clear()
        code = None
        with contextlib.redirect_stderr(io.StringIO()):
            try:
                main(["--jobs", "0"])
            except SystemExit as exc:
                code = exc.code
        check("--jobs 0 is refused before anything runs", (code, seen_jobs), (2, []))
    finally:
        globals()["audit"], globals()["_load_plan_code"], os.cpu_count = saved

    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
