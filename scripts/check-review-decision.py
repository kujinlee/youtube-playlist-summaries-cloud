#!/usr/bin/env python3
"""What does the review loop do next? — answered from recorded evidence, not recall.

    python3 scripts/check-review-decision.py              # decide for the current branch
    python3 scripts/check-review-decision.py --self-test  # 23 cases

WHY THIS EXISTS
---------------
Measured 2026-09-14 on PR #302: a contained single-file change ran FOUR adversarial review
rounds. Two were owed. Rounds 3 and 4 each returned a single Low in the coordinator's own
test code — exactly the case `review-method.md` names when it says *"one round is fine, do
not over-apply this"*.

Every rule was already written down. The failure was a CONFLATION of two questions:

    convergence    has defect discovery dried up?
    tree identity  did a round see the code that MERGES?

Rounds 3 and 4 were spent on tree identity while being narrated as unmet convergence — and
tree identity has four answers, of which "run another round" is the most expensive and the
last. This script keeps them apart so they cannot be merged again.

⚠ IT CONSUMES JUDGEMENTS, IT DOES NOT MAKE THEM. `aim` and `fix_induced` are recorded by
the agent in each round document's header (docs/reviews/ROUND-HEADER-TEMPLATE.md). A header
filled in dishonestly produces a confident wrong answer and nothing here detects it.

NO-CALLER: an instrument the coordinator consults at a decision point; CI has no decision to
make about whether to run a review round. Its protection is that `review-method.md`'s
decision card names running it as the step — which is precisely the protection that FAILED
on PR #302 when the step was prose. If it is skipped again, the remedy is not better prose;
it is making this a step nobody can skip.
"""
from __future__ import annotations

import argparse
import sys

# ---------------------------------------------------------------- Q1: scope
# review-method.md's own trigger list, expressed as PATH PREFIXES so the answer is
# observable rather than argued. Anything not named here is a contained change.
RISK_PREFIXES = (
    "supabase/",                                   # schema, migrations, RLS policies
    "lib/spend", "lib/quota", "lib/ledger",        # money, irreversible paths
    "lib/lease", "lib/queue", "lib/reservation",   # concurrency, leasing, locking
    "middleware", "lib/auth",                      # auth / multi-tenant isolation
)


def scope_for(paths: list[str]) -> str:
    """PURE. `full-loop` if any changed path is risky, else `one-round`."""
    for p in paths:
        if any(p.startswith(pre) for pre in RISK_PREFIXES):
            return "full-loop"
    return "one-round"


# ----------------------------------------------------------- Q5: thrashing
def thrashing_component(rounds: list[dict]) -> str | None:
    """PURE. The component carrying fix-induced findings in BOTH of the last two rounds.

    ⚠ Deliberately the LAST TWO, not any two. "Two consecutive rounds" is the arming
    condition; a component that thrashed early and was then fixed must not arm it forever.
    """
    if len(rounds) < 2:
        return None

    def induced(r: dict) -> set:
        return {f.get("component") for f in r.get("findings", []) if f.get("fix_induced")}

    shared = induced(rounds[-2]) & induced(rounds[-1])
    return sorted(c for c in shared if c)[0] if any(shared) else None


# --------------------------------------------------------- Q4a: convergence
def converged(rounds: list[dict], scope: str) -> tuple[bool, str]:
    """PURE. Judged by AIM, not severity.

    `review-method.md` already says a clean severity column is a statement about the
    REVIEWERS, not the design. PR #302 measured the same thing from the other side:
    severity read "converged" from round 1 and was useless, while aim separated the rounds.
    """
    if not rounds:
        return False, "no round recorded"
    need = 1 if scope == "one-round" else 2
    if len(rounds) < need:
        return False, f"{len(rounds)} round(s) recorded; a {scope} change needs {need}"
    for r in rounds[-need:]:
        for f in r.get("findings", []):
            if f.get("severity") in ("Blocking", "High"):
                return False, f"r{r.get('round')} produced a {f.get('severity')}"
            if f.get("aim") == "deliverable":
                return False, f"r{r.get('round')} found a defect in the deliverable"
    return True, (f"{need} round(s) with no Blocking/High and nothing in the deliverable")


# ------------------------------------------------------- Q4b: tree identity
TREE_ANSWERS = (
    "land the editorial fixes AHEAD of the final round",
    "keep the last fixes uncommitted so the reviewer sees what ships",
    "declare NO-REVIEW: <reason> in the PR body",
    "run another round — LAST resort, never first",
)


def decide(rounds: list[dict], scope: str, tree_reviewed: bool) -> tuple[str, str]:
    """PURE. One decision and the reason for it.

    ⚠ ORDER IS LOAD-BEARING. Thrashing outranks convergence, because a design fighting
    itself converges on nothing worth having. And tree identity is checked LAST and
    answered as TREE — never as ROUND_OWED — so the two questions PR #302 merged stay apart.
    """
    if not rounds:
        return "ROUND_OWED", f"no round recorded; a {scope} change needs at least one"
    th = thrashing_component(rounds)
    if th:
        return ("ARCHITECTURE_REVIEW",
                f"thrashing: '{th}' carried fix-induced findings in "
                f"r{rounds[-2].get('round')} and r{rounds[-1].get('round')}")
    ok, why = converged(rounds, scope)
    if not ok:
        return "ROUND_OWED", why
    if not tree_reviewed:
        return "TREE", "converged, but no round saw the merging tree; cheapest first: " + \
                       "; ".join(f"({i}) {a}" for i, a in enumerate(TREE_ANSWERS, 1))
    return "STOP", f"converged — {why} — and a round saw the merging tree"


# ------------------------------------------------------------------ self-test
def _self_test() -> int:
    cases = failures = 0

    def case(name, got, want):
        nonlocal cases, failures
        cases += 1
        if got != want:
            failures += 1
            print(f"  [FAIL] {name}\n    got:  {got!r}\n    want: {want!r}")

    # --- Q1 scope ---------------------------------------------------------
    case("a migration needs the full loop",
         scope_for(["supabase/migrations/0028_x.sql"]), "full-loop")
    case("a money path needs the full loop",
         scope_for(["lib/spend-ledger.ts"]), "full-loop")
    case("a page generator alone is one round",
         scope_for(["scripts/gen-dashboard.py"]), "one-round")
    case("docs alone are one round",
         scope_for(["docs/review-method.md"]), "one-round")
    case("one risky path in a mixed set still forces the full loop",
         scope_for(["docs/x.md", "lib/auth/session.ts"]), "full-loop")
    case("an empty diff is one round, not a crash",
         scope_for([]), "one-round")

    # --- Q5 thrashing -----------------------------------------------------
    fix_a1 = {"round": 1, "findings": [{"fix_induced": True, "component": "a"}]}
    fix_a2 = {"round": 2, "findings": [{"fix_induced": True, "component": "a"}]}
    fix_b2 = {"round": 2, "findings": [{"fix_induced": True, "component": "b"}]}
    clean3 = {"round": 3, "findings": [{"fix_induced": False, "component": "a"}]}
    case("two consecutive fix-induced rounds in ONE component is thrashing",
         thrashing_component([fix_a1, fix_a2]), "a")
    case("two fix-induced rounds in DIFFERENT components is not thrashing",
         thrashing_component([fix_a1, fix_b2]), None)
    case("one fix-induced round is not thrashing",
         thrashing_component([fix_a1, clean3]), None)
    case("thrashing reads the LAST two rounds, not any two",
         thrashing_component([fix_a1, fix_a2, clean3]), None)
    case("a single round can never be thrashing",
         thrashing_component([fix_a1]), None)

    # --- Q4a convergence --------------------------------------------------
    inst = {"severity": "Low", "aim": "instrument", "fix_induced": False, "component": "t"}
    deliv = {"severity": "Low", "aim": "deliverable", "fix_induced": False, "component": "d"}
    high = {"severity": "High", "aim": "instrument", "fix_induced": False, "component": "t"}
    two_inst = [{"round": 1, "findings": [inst]}, {"round": 2, "findings": [inst]}]
    case("two consecutive instrument-only rounds converge",
         converged(two_inst, "full-loop")[0], True)
    case("a High blocks convergence even when aimed at the instrument",
         converged([{"round": 1, "findings": [inst]},
                    {"round": 2, "findings": [high]}], "full-loop")[0], False)
    case("a deliverable finding blocks convergence",
         converged([{"round": 1, "findings": [inst]},
                    {"round": 2, "findings": [deliv]}], "full-loop")[0], False)
    case("one clean round is NOT convergence on the full loop",
         converged([{"round": 1, "findings": []}], "full-loop")[0], False)
    case("one clean round IS convergence when the scope is one-round",
         converged([{"round": 1, "findings": []}], "one-round")[0], True)
    case("no rounds never converges",
         converged([], "one-round")[0], False)

    # --- decide -----------------------------------------------------------
    case("no round recorded owes a round",
         decide([], "one-round", False)[0], "ROUND_OWED")
    case("thrashing outranks convergence",
         decide([fix_a1, fix_a2], "full-loop", True)[0], "ARCHITECTURE_REVIEW")
    case("converged but an unreviewed merging tree asks for TREE, never a round",
         decide(two_inst, "full-loop", False)[0], "TREE")
    case("converged and the tree was reviewed is STOP",
         decide(two_inst, "full-loop", True)[0], "STOP")
    case("not converged owes a round",
         decide([{"round": 1, "findings": [high]}], "full-loop", True)[0], "ROUND_OWED")
    case("every decision carries a non-empty reason",
         all(decide(*a)[1] for a in [([], "one-round", False),
                                     ([fix_a1, fix_a2], "full-loop", True),
                                     (two_inst, "full-loop", False),
                                     (two_inst, "full-loop", True)]), True)

    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)
    if args.self_test:
        return _self_test()
    print("CANNOT RUN — the live path is not wired yet")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
