#!/usr/bin/env python3
"""A branch that changes CODE records a review round, or says in writing why it did not.

    python3 scripts/check-review-recorded.py --base origin/master --pr-body-file /tmp/pr-body.md
    python3 scripts/check-review-recorded.py --self-test

WHY THIS EXISTS
---------------
MEASURED 2026-09-09/10. Six pull requests merged in one night. FIVE of them had no review at all —
no review document, no verdict file, nothing — and nobody noticed until the human asked
"had PR 283 done dual adversarial review?". The sixth was reviewed only because of that question,
and three rounds then found **43 defects, 8 of them Blocking**, including a live regression that had
already shipped: the backlog page lost its Ask tray and the generator reported exit 0.

⛔ THE GATE FOR THIS ALREADY EXISTED AND COULD NOT SEE IT. `check-review-rounds.py` audits the
rounds that EXIST — that each has both halves, or a written `REVIEW GAP:`. A branch with ZERO rounds
contributes zero rounds and passes vacuously; it returned **rc=0** across all six. Its own docstring
says *"The absence of a reviewer looks exactly like the presence of a clean one"* — and it closed
the one-half case while leaving the zero-half case open. This file is that missing half.

WHAT IT ASKS, AND WHY IT IS THE DIFF AND NOT A NAMING CONVENTION
----------------------------------------------------------------
"Did this branch ADD a file under `docs/reviews/`?" — asked of the diff against the base, exactly as
`check-dashboard-entry.py` asks whether an entry was added to the store. Not "is there a review doc
whose stem matches the branch name": a subject is named by a human and drifts from the branch, and a
guard keyed on that would fail for the wrong reason. Adding a review document is the observable act.

SCOPE IS BLAST RADIUS, which is the user's decision of 2026-09-10 and the same axis
`docs/dev-process.md` already uses to decide branch-plus-PR. Code obliges a review; a docs-only
branch does not. Five of the six unreviewed PRs were docs, and requiring a round for those is how a
gate earns the reputation that gets it switched off — backlog #56 measured exactly that.

FAILS IF
--------
  * a guarded path changed, no review document was added, and the PR body carries no `NO-REVIEW:`
    reason -> exit 1, naming the files.
  * git is absent, the base cannot be resolved, or the clone is SHALLOW -> exit **2**, CANNOT RUN.
    A shallow clone sees fewer commits and would report a confident, smaller diff.

⚠ THE DECLARATION IS NOT A RUBBER STAMP. `NO-REVIEW:` takes a reason, and an empty one is refused —
the same posture as `NO-ENTRY:`. The marker is parsed by `check-dashboard-entry._declaration_reason`
via a `marker` parameter, NOT by a second copy: which contexts are inert (fenced, indented,
commented, blockquoted) and which are not (emphasis) cost measured escapes there, and a sibling
re-deriving them would drift.
"""
from __future__ import annotations

import argparse
import importlib.util
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
NO_REVIEW = "NO-REVIEW:"
REVIEW_DIR = "docs/reviews/"

# ⛔ A DENYLIST OF PROSE, NOT AN ALLOWLIST OF CODE — and the first version got this backwards.
# It enumerated `lib/ app/ components/ worker/ supabase/ scripts/ tests/ .github/ .claude/hooks/`
# plus five root files, and the r1 review walked straight through it: `middleware.ts` is
# request-path code, `package-lock.json` fixes the dependency graph CI and production run, and
# `Dockerfile`, `jest.config.ts`, `playwright.config.ts`, `postcss.config.mjs`,
# `tsconfig.worker.json`, `.claude/settings.json` and `.claude/commands/` were all "unguarded" too.
#
# An allowlist of everything that can change behaviour cannot be completed — every new top-level
# file starts outside it, silently. A denylist of PROSE can be completed, because prose is the
# small set: `docs/`, and the handful of Markdown files at the root. So the default is GUARDED, a
# new path is obliged from the day it appears, and the failure direction is a review someone did
# not strictly need rather than a change nobody looked at.
#
# ⚠ `docs/` covers `docs/reviews/` for free, which is why there is no separate exemption: adding a
# review document cannot itself oblige a review. The first version had that as its own constant and
# the mutation deleting it SURVIVED, because the constant could not change an outcome.
PROSE_DIRS = ("docs/",)
PROSE_FILES = ("README.md", "CLAUDE.md", "AGENTS.md", "CONTEXT.md", ".gitignore")


def is_prose(path: str) -> bool:
    """PURE. Whether `path` is prose, and therefore owes no review round."""
    if path in PROSE_FILES:
        return True
    if any(path.startswith(d) for d in PROSE_DIRS):
        return True
    # a Markdown file at the repository ROOT is prose; one inside a package is not necessarily
    return path.endswith(".md") and "/" not in path


def _load_declaration_parser():
    """`exemption_reason` from check-dashboard-entry, so both markers share one parser.

    RAISES if it cannot be loaded — a gate that silently fell back to its own parser would be the
    duplicate this docstring exists to prevent, and it would look green while doing it.
    """
    path = ROOT / "scripts" / "check-dashboard-entry.py"
    spec = importlib.util.spec_from_file_location("_cde", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"CANNOT RUN — cannot load the declaration parser from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_cde"] = mod
    spec.loader.exec_module(mod)
    return mod.exemption_reason


def guarded_changes(paths: list[str]) -> list[str]:
    """PURE. The changed paths that oblige a review round, in order."""
    return [p for p in paths if not is_prose(p)]


def review_added(paths: list[str]) -> list[str]:
    """PURE. Review documents this branch ADDED."""
    return [p for p in paths if p.startswith(REVIEW_DIR) and p.endswith(".md")]


def verdict(changed: list[str], added: list[str], pr_body: str,
            reason_of=None) -> tuple[int, str]:
    """PURE given `reason_of`. `(exit_code, message)`.

    The three outcomes, in the order they are decided:
      * nothing guarded changed          -> 0, and the declaration is not even read
      * a review document was added      -> 0
      * a `NO-REVIEW:` reason was given  -> 0, and the reason is ECHOED so it lands in the log
      * otherwise                        -> 1, naming the files
    """
    reason_of = reason_of or (lambda body: None)
    obliged = guarded_changes(changed)
    if not obliged:
        return 0, "no guarded path changed — a review round is not required"
    docs = review_added(added)
    if docs:
        # ⚠ THE HONEST CONTRACT IS "a review document was added SOMEWHERE IN THIS RANGE", not "this
        # branch was reviewed", and those differ for a stacked branch. MEASURED: branch B based on
        # branch A, opened against master, is cleared by A's review document. CI passes
        # `--base origin/$GITHUB_BASE_REF`, so this is right whenever the PR targets its true
        # parent — and this project has already shipped a PR that "silently carried a whole other
        # PR". So the pass NAMES the documents it relied on; a stacked pass is then visible in the
        # log rather than indistinguishable from a branch that reviewed itself.
        return 0, ("review recorded in this range: " + ", ".join(sorted(docs))
                   + "\n  (if this branch is stacked, check these belong to IT: "
                     "git log --oneline $(git merge-base HEAD @{u} 2>/dev/null || echo HEAD~1)..HEAD)")
    reason = reason_of(pr_body)
    if reason:
        return 0, f"{NO_REVIEW} {reason}"
    if reason is not None:      # present but empty
        return 1, f"{NO_REVIEW} was declared with no reason after it"
    shown = ", ".join(obliged[:6]) + (f" (+{len(obliged) - 6} more)" if len(obliged) > 6 else "")
    return 1, (f"{len(obliged)} guarded path(s) changed and no review round was recorded:\n"
               f"    {shown}\n"
               f"  Add a review document under {REVIEW_DIR} (both halves — see docs/plugins.md),\n"
               f"  or put `{NO_REVIEW} <reason>` in the pull-request body.\n"
               f"  MEASURED 2026-09-09: five PRs merged unreviewed in one night and nothing saw it.")


def changed_paths(base: str) -> list[str]:
    """Paths changed against `base`. RAISES on anything that would understate the answer."""
    if not (ROOT / ".git").exists():
        raise RuntimeError("CANNOT RUN — no .git directory. Treat this as NOT CHECKED.")
    shallow = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--is-shallow-repository"],
                             capture_output=True, text=True)
    if shallow.stdout.strip() == "true":
        raise RuntimeError("CANNOT RUN — shallow clone; the diff would be confidently short.")
    merge_base = subprocess.run(["git", "-C", str(ROOT), "merge-base", base, "HEAD"],
                                capture_output=True, text=True)
    if merge_base.returncode != 0:
        raise RuntimeError(f"CANNOT RUN — cannot resolve a merge base with {base!r}: "
                           f"{merge_base.stderr.strip()}")
    diff = subprocess.run(["git", "-C", str(ROOT), "diff", "--name-only",
                           merge_base.stdout.strip(), "HEAD"], capture_output=True, text=True)
    if diff.returncode != 0:
        raise RuntimeError(f"CANNOT RUN — git diff failed: {diff.stderr.strip()}")
    return [ln for ln in diff.stdout.splitlines() if ln.strip()]


def added_paths(base: str) -> list[str]:
    """Paths ADDED against `base` (status A). RAISES like `changed_paths`."""
    mb = subprocess.run(["git", "-C", str(ROOT), "merge-base", base, "HEAD"],
                        capture_output=True, text=True)
    if mb.returncode != 0:
        raise RuntimeError(f"CANNOT RUN — cannot resolve a merge base with {base!r}")
    out = subprocess.run(["git", "-C", str(ROOT), "diff", "--name-only", "--diff-filter=A",
                          mb.stdout.strip(), "HEAD"], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"CANNOT RUN — git diff failed: {out.stderr.strip()}")
    return [ln for ln in out.stdout.splitlines() if ln.strip()]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="origin/master")
    ap.add_argument("--pr-body-file")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()

    body = ""
    if args.pr_body_file:
        body = pathlib.Path(args.pr_body_file).read_text(encoding="utf-8", errors="replace")

    # ⚠ THE DOCSTRING PROMISES EXIT 2, and the first version raised `RuntimeError` straight out of
    # `main` — rc=1 with a traceback (r1 review, Major). "Cannot run" collapsing into an ordinary
    # failure is the exact shape this repo refuses: a gate that could not reach its subject must
    # say so in its own exit code, not look like a finding.
    try:
        changed = changed_paths(args.base)
        added = added_paths(args.base)
        reason_of = _load_declaration_parser()
    except (RuntimeError, OSError) as exc:
        print(str(exc) if str(exc).startswith("CANNOT RUN") else f"CANNOT RUN — {exc}",
              file=sys.stderr)
        return 2
    code, message = verdict(changed, added, body, lambda b: reason_of(b, NO_REVIEW))
    print(("FAILED — " if code else "ok — ") + message, file=sys.stderr if code else sys.stdout)
    return code


def self_test() -> int:
    cases: list[tuple[str, object, object]] = []

    def case(name: str, got, want) -> None:
        cases.append((name, got, want))

    none_reason = lambda _b: None
    def reason(r):
        return lambda _b: r

    CODE = ["scripts/x.py"]
    DOCS = ["docs/roadmap-to-launch.md", "docs/backlog.md"]

    case("a docs-only branch owes nothing", verdict(DOCS, [], "", none_reason)[0], 0)
    case("a code branch with no review FAILS", verdict(CODE, [], "", none_reason)[0], 1)
    case("...and the failure names the file", "scripts/x.py" in verdict(CODE, [], "", none_reason)[1], True)
    case("a code branch that ADDED a review passes",
         verdict(CODE, ["docs/reviews/claude/x-r1-claude.md"], "", none_reason)[0], 0)
    case("a NO-REVIEW: reason passes and is echoed",
         verdict(CODE, [], "", reason("typo in a comment")), (0, "NO-REVIEW: typo in a comment"))
    # ⚠ an EMPTY declaration is not a declaration — same posture as NO-ENTRY:
    case("an EMPTY NO-REVIEW: is refused", verdict(CODE, [], "", reason(""))[0], 1)
    # ⚠ the MESSAGE too — pinned by exit code alone it could become the generic "no review recorded"
    # text, which would send an author who DID declare one to add a review instead of a reason.
    case("...and says so, rather than falling back to the generic refusal",
         "no reason after it" in verdict(CODE, [], "", reason(""))[1], True)
    # ⚠ adding a review doc must not itself oblige a review, or a review-only branch loops
    case("a review-only branch owes nothing",
         verdict(["docs/reviews/claude/x-r1-claude.md"], ["docs/reviews/claude/x-r1-claude.md"],
                 "", none_reason)[0], 0)
    # ⛔ THE r1 BLOCKING, pinned. Every one of these walked through the first version's allowlist.
    for _p in ("middleware.ts", "package-lock.json", "Dockerfile", "jest.config.ts",
               "playwright.config.ts", "postcss.config.mjs", "tsconfig.worker.json",
               ".claude/settings.json", ".claude/commands/clean_gone.md", "lib/x.ts",
               "supabase/migrations/0001_x.sql", "a/new/top-level/thing.rs"):
        case(f"{_p} is guarded", guarded_changes([_p]), [_p])
    for _p in ("docs/backlog.md", "docs/reviews/claude/x-r1-claude.md", "README.md",
               "CLAUDE.md", "AGENTS.md"):
        case(f"{_p} is prose", guarded_changes([_p]), [])
    # ⚠ a Markdown file INSIDE a package is not automatically prose — only a root one is
    case("a .md inside a package is still guarded",
         guarded_changes(["lib/README.md"]), ["lib/README.md"])
    case("only .md counts as a review document",
         review_added(["docs/reviews/verdicts/x.json"]), [])
    # ⭐ THE LIVE CASE: the parser is SHARED, not copied. If check-dashboard-entry stops exporting
    # `exemption_reason`, or its signature loses the marker, this fails here rather than silently
    # falling back to a second implementation.
    _reason_of = _load_declaration_parser()
    case("the shared parser reads NO-REVIEW: through the same rules",
         _reason_of("NO-REVIEW: docs only", NO_REVIEW), "docs only")
    case("...and still refuses an inert one", _reason_of("```\nNO-REVIEW: x\n```", NO_REVIEW), None)
    case("...and does not confuse the two markers",
         _reason_of("NO-ENTRY: x", NO_REVIEW), None)
    # ⛔ THE SECOND SCAN POINT. `exemption_reason` tests the marker twice — the bare line, and the
    # text BEFORE an inline `<!--`. Reverting the comment-head one to a hardcoded NO_ENTRY left
    # check-dashboard-entry at 146/146 AND this suite at 14/14, while
    # `NO-REVIEW: docs only <!-- agreed -->` silently lost its declaration and `NO-ENTRY:` kept
    # working — a baffling asymmetry, invisible to both suites. That file's own docstring records
    # this divergence as one it "has already paid for twice"; this is the case that sees it.
    case("the marker is honoured on the pre-comment head too",
         _reason_of("NO-REVIEW: docs only <!-- agreed with the lead -->", NO_REVIEW), "docs only")

    failed = 0
    for name, got, want in cases:
        ok = got == want
        failed += not ok
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + ("" if ok else f"\n        got {got!r} want {want!r}"))
    print(f"\n{len(cases) - failed}/{len(cases)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
