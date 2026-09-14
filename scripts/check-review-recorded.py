#!/usr/bin/env python3
"""A branch that changes CODE records a review round, or says in writing why it did not.

    python3 scripts/check-review-recorded.py --base origin/master --pr-body-file /tmp/pr-body.md
    python3 scripts/check-review-recorded.py --self-test  # 117 cases

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

THE SECOND QUESTION: DID ANY ROUND SEE THE CODE THAT IS ABOUT TO MERGE? (added 2026-09-13)
-------------------------------------------------------------------------------------------
"A review was recorded" and "the reviewed code is the code that merges" are different claims, and
the gap between them is where this project's late defects actually live. MEASURED across three
rounds on two consecutive branches (backlog #296, #297): the two review halves produced **zero**
overlapping findings, so neither was wasted effort — but the two defects that survived furthest were
both introduced by a FIX, in code no round had ever seen. A concurrent pair reviewing one frozen
tree cannot find those by construction: nobody is looking at the repair.

⛔ COMMIT ORDER CANNOT ANSWER IT, and that is why `codex-review.py` had to change. "Was the review
document committed after the last code commit?" is defeated by the ordinary workflow of committing
the fixes and the review document together — the most likely accident, not an exotic evasion. Only
the commit recorded by the wrapper AT DISPATCH says what the reviewer was handed, so verdict schema
2 carries `head` and `dirty`.

`dirty` is load-bearing in the other direction. The documented practice is to hold a round's fixes
UNCOMMITTED so the reviewer sees the state that will merge; under it `head` is the commit BEFORE
those fixes, and a check reading `head` alone would accuse the author who did the careful thing.

SCOPE, STATED RATHER THAN IMPLIED
----------------------------------
  * Only verdicts THIS branch ADDED are considered. On `master` the range is empty, so the rule
    correctly says nothing; a MODIFIED historical verdict is not testimony about this branch.
  * Only the Codex half leaves a verdict. A round that ran as Claude because Codex was down cannot
    answer this question at all — which is CANNOT RUN, cleared by a `REVIEW GAP:` naming **codex**
    (a gap about the other half explains a different absence). ⚠ Like the recorded-review question,
    the gap is read over the whole RANGE, so a stacked child is cleared by its parent's
    declaration — measured r3. The pass names the document it relied on rather than hiding it.
  * A verdict older than schema 2 carries no `head`, and one whose head was rebased or squashed
    away cannot be diffed. Both are counted as unusable, never quietly dropped.
  * `NO-REVIEW:` waives BOTH questions. One declaration per concern, deliberately — a second marker
    for "yes it is stale and that is fine" is the duplicate-vocabulary shape
    `check-vocabulary-collisions.py` exists to refuse. ⚠ The waiver is now ECHOED (r11 High); it
    used to clear the second question silently while the log named the review documents, so exit 0
    was attributed to evidence that had not cleared it.
  * ⚠ "WAS HANDED", NOT "WAS READ" — r11 High, and the limit this rule's own framing kept omitting.
    `reviewed_state` stages the whole working tree, so the record says what was IN the tree at
    dispatch, not what the round's prompt covered. A guarded file merely dirty at dispatch is
    credited. Each verdict now records the `prompt` it was dispatched with so a human can see the
    scope; no mechanism can close the rest, and the message says "was in the tree handed to".
  * THE TAIL IS SCOPED TO THE BRANCH (r11 High) — `merge-base(base, HEAD)`, the same scope the other
    two questions have always used. Code the merge took verbatim from the base is the base's gate's
    question, asked on the base's own PR; re-asking it here fired on every upstream pickup, with no
    merge action by the author under CI's synthesised merge ref. A clean-merge SEMANTIC conflict is
    given up knowingly — `tsc --noEmit` and the unit suite are the instruments for that, and CI runs
    both on the same ref.
  * ⚠ IT RUNS ON `pull_request` ONLY (r1 High). The workflow also runs on push to `master`, where
    this step is skipped and neither question is asked. Direct pushes to the default branch are
    refused by `.claude/hooks/block-default-branch-push.sh`, so the path is closed by a different
    mechanism — but it is closed THERE, not here, and this line exists so nobody reads CI green on
    master as this gate having spoken.

FAILS IF
--------
  * a guarded path changed, no review document was added, and the PR body carries no `NO-REVIEW:`
    reason -> exit 1, naming the files.
  * every round this branch recorded has guarded code committed after it -> exit 1, naming the
    files the closest round did not see.
  * the question applies and NO round can answer it -> exit **2**, CANNOT RUN, unless a review
    document of this branch carries a `REVIEW GAP:` reason.
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
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
NO_REVIEW = "NO-REVIEW:"
REVIEW_DIR = "docs/reviews/"
VERDICT_DIR = "docs/reviews/verdicts/"
# What a path absent from the tree looks like as an entry. NOT an invented sentinel: it is the
# all-zero destination `git diff-index` itself writes for a deletion, which is what the wrapper
# records when a reviewer is handed a deleted file (r3 Medium). One spelling, both ends.
# ⚠ THE WIDTH IS NOT PART OF THE MEANING — r4 Medium. A SHA-256 repository writes 64 zeros, not 40,
# and comparing against this literal made a reviewed deletion falsely FAIL there. `is_absent` reads
# the shape instead, so the constant stays a readable spelling rather than a hidden width check.
ABSENT_ENTRY = "000000 " + "0" * 40


def is_absent(entry: "str | None") -> bool:
    """PURE. Does this entry mean `the path is not in the tree`? Any sha width."""
    parts = (entry or "").split()
    return len(parts) == 2 and bool(parts[1]) and set(parts[1]) == {"0"}

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


# ── THE SECOND QUESTION, as a pure rule ───────────────────────────────────────────────────────
def branch_verdicts(added: list[str]) -> list[str]:
    """PURE. The Codex verdicts THIS branch ADDED — the rounds that are about this work.

    ⛔ ADDED, NOT CHANGED, and the first version said changed — r1 Medium. A branch could then MODIFY
    a historical verdict so its `head` cleared the tail, and the rule would read a rewritten record
    of somebody else's round as testimony about this one. `review_added` already decides the
    recorded-review question on the ADDED set; these two answers must come from the same kind of
    observation or they are about different branches.

    Not "every verdict on disk" either: 82 predate this branch, and a rule reading those would spend
    every run reporting that history cannot be placed — how a gate earns the reputation that gets it
    switched off (backlog #56, measured).
    """
    return [p for p in added if p.startswith(VERDICT_DIR) and p.endswith(".json")]


# A verdict record is one of three things, and the first version could only tell two apart.
USABLE, UNUSABLE, SKIP = "usable", "unusable", "skip"


def classify_verdict(rec: "object | None") -> "tuple[str | None, str]":
    """PURE. One verdict record -> `(head, USABLE | UNUSABLE | SKIP)`.

    ⛔ EXTRACTED FROM THE GATHERER — r11 High (lens 3). These four rules lived inside `round_tails`
    where nothing could reach them, and mutating any of them left the suite at 77/77. Two were live
    fail-opens: deleting the `gate_ran` test turned a verdict reading `"gate_ran": false` into
    testimony that a round saw the final tree (exit 2 -> exit 0), and dropping the schema-1 arm
    stopped counting rounds that cannot answer. This is the r1 Low one instance later — the file
    already says `guarded_changes` is called in the pure layer *"so this rule … is pure and
    reachable from a case"*, and the gatherer still held seven more rules when r11 looked.

    `None` means the file named by the diff is not on disk: added in the range and deleted again. It
    cannot testify, so it is UNUSABLE rather than skipped — silence is what `tail_verdict` refuses
    to pass.

    ⚠ `dirty is None` IS NOT `dirty == {}` — r11 Medium, found independently by two lenses. Three of
    `reviewed_state`'s failure paths used to return a real head with an empty map, byte-identical to
    a round dispatched against a genuinely clean tree, so a FAILED MEASUREMENT read as "nothing was
    uncommitted" and produced a false accusation aimed at the author who held their fixes back. The
    producer now writes `null` when it could not look; this is the end that refuses to guess.
    """
    if not isinstance(rec, dict):
        return None, UNUSABLE
    # A gate that did not run reviewed nothing. The CONTRADICTION of filing its artifact anyway
    # belongs to check-review-rounds.py and is not re-decided here.
    if not rec.get("gate_ran"):
        return None, SKIP
    head = rec.get("head")
    if not isinstance(head, str) or not head.strip():
        return None, UNUSABLE           # schema 1: no commit recorded at all
    if "dirty" in rec and rec["dirty"] is None:
        return None, UNUSABLE           # the wrapper could not describe the tree; NOT a clean tree
    return head.strip(), USABLE


def reviewed_map(rec: object) -> dict[str, str]:
    """PURE. The `path -> "<mode> <object-id>"` map a verdict says the reviewer was handed.

    Extracted for the same reason as `classify_verdict`: r11 measured that replacing this with an
    empty map inside the gatherer left the suite green, and an empty map is exactly the shape that
    makes every dirty-overlay comparison vacuous.
    """
    d = rec.get("dirty") if isinstance(rec, dict) else None
    if not isinstance(d, dict):
        return {}
    return {k: v for k, v in d.items() if isinstance(k, str) and isinstance(v, str)}


def tail_candidates(after: list[str], reviewed: dict[str, str],
                    branch_delta: list[str]) -> list[str]:
    """PURE. The paths one round's testimony has to account for.

    ⛔ TWO r11 findings live in this one expression, and they pull in OPPOSITE directions.

    **The union closes r11 Blocking.** The first version asked only about `after` — the paths that
    changed between the round's commit and HEAD. But `reviewed`'s keys are by construction the paths
    where the reviewer's view DIFFERED from that commit, so for every one of them "unchanged since
    `head`" means "NOT what the reviewer read". Reverting a dirty overlay therefore dropped the path
    out of the compared set entirely and the round was credited with having seen the final tree.
    Reproduced end to end: a file reviewed as `GOOD`, reverted, merged as `BAD`, exit 0 under the
    line *"the final tree was reviewed by"*. This is not r1's finding — r1 was *edit it AGAIN and
    commit*, where the path STAYS in `after` and the entry comparison handles it. Here no comparison
    happened at all.

    **The intersection closes r11 High.** `after` is a raw two-tree diff, so every commit the BASE
    made since the branch forked was charged against this branch's rounds — and in CI `HEAD` is
    GitHub's synthesised merge ref, so it fired with no merge action by the author whatsoever.
    Measured on this branch: five files named, three of them `origin/master`'s own, already reviewed
    on their own PR. The two sibling questions have always scoped to the branch via
    `merge-base(base, HEAD)`; the tail was the one place that did not. A path the merge took
    VERBATIM from the base has an entry identical to the base's and is absent from the branch delta;
    a path whose merge resolution invented content is present. That is blob-and-mode identity
    against the base, computed by git, with no new concept.

    ⚠ WHAT THE INTERSECTION GIVES UP, STATED: a clean-merge SEMANTIC conflict — master changes a
    signature, the branch changes a caller, no file carries a resolution — is no longer charged. It
    was never really caught, only carpeted: the unscoped rule fired on every upstream pickup, so its
    output could not distinguish "master moved" from "your resolution invented code". `tsc --noEmit`
    and the unit suite are the instruments for "these two changes do not compose", and CI already
    runs both on the same merge ref.
    """
    return sorted((set(after) | set(reviewed)) & set(branch_delta))


def second_question(changed: list[str], waiver: "str | None") -> "tuple[bool, str | None]":
    """PURE. `(ask_the_final_tree_question, line_to_print_when_not)`.

    ⛔ r11 High: `NO-REVIEW:` waived this question SILENTLY, and the pass then named the review
    documents — attributing exit 0 to evidence that had not cleared it. `verdict()` returns at its
    review-document branch, so the echo it promises at its own `NO-REVIEW:` arm never ran, while the
    docstring says *"the reason is ECHOED so it lands in the log"*. Anyone auditing a merge from CI
    output saw a green final-tree gate that never ran. It compounds with the scoping finding above:
    the livelock's predictable escape was this waiver, and the escape left no trace.

    ⛔ AND IT IS A RULE, NOT A LINE IN `main` — r11 measured `if True:` in its place leaving the
    suite at 77/77. `tail_verdict` and `round_tail` are exhaustively cased and manifested; the one
    line that CALLED them was not, so the whole subsystem was detachable without a red anywhere.
    """
    if not guarded_changes(changed):
        return False, None
    if waiver is not None:
        return False, f"{NO_REVIEW} {waiver} — the final-tree question is WAIVED, not passed"
    return True, None


def round_tail(after: list[str], reviewed: dict[str, str], final: dict[str, str]) -> list[str]:
    """PURE. The guarded paths one round cannot have seen.

    `after`    — paths changed between that round's commit and HEAD
    `reviewed` — path -> `"<mode> <object-id>"` the reviewer was handed UNCOMMITTED
    `final`    — path -> `"<mode> <object-id>"` in the tree that will merge

    ⛔ THE COMPARISON IS THE TREE ENTRY, and it took two rounds to get there. r1: subtracting dirty
    PATHS let "review `lib/x.py` at v2, then edit it to v3 and commit" pass, because the name still
    matched. r2: comparing CONTENT alone let a mode-only change pass — same bytes, newly executable,
    credited as reviewed. Equal entries mean the reviewer saw what is merging; nothing weaker does.

    `guarded_changes` is CALLED here rather than upstream so this rule — the one a mutation must be
    able to break — is pure and reachable from a case. r1 Low: the previous wiring lived inside the
    git-reading gatherer, and deleting the call left the suite at 45/45.
    """
    def same(p: str) -> bool:
        seen, now = reviewed.get(p), final.get(p, ABSENT_ENTRY)
        if not seen:
            return False
        return (is_absent(seen) and is_absent(now)) or now == seen

    missed = [p for p in guarded_changes(after) if not same(p)]
    return sorted(set(missed))


def tail_verdict(tails: dict[str, list[str]], unusable: int = 0,
                 gap: "str | None" = None) -> tuple[int, str]:
    """PURE. `(exit_code, message)` for "did any round see the code that is about to merge?".

    `tails` maps a round's verdict filename to the guarded paths it cannot have reviewed. An EMPTY
    list is the pass: that round saw everything.

    ⚠ ANY round clears it, not the latest. Two rounds can each be the last to see a different file
    only if a third thing changed between them, and requiring the newest specifically would make
    the answer depend on an ordering the verdicts do not record.

    ⛔ NO USABLE ROUND IS **CANNOT RUN (2)**, NOT A PASS — r1 High. The first version returned 0 with
    an honest NOT CHECKED line, and CI consumes the exit code, not the line. `CLAUDE.md` is
    unambiguous: *"'Cannot run' is a FAILURE, never a pass."* The escape is the marker that already
    exists for a half that could not run — `REVIEW GAP:` in one of this branch's review documents,
    parsed by `check-review-rounds.has_gap_line`, never by a second copy. So a Codex-down round
    says so once, in the place the other gate already reads, and is not asked to say it twice.
    """
    if not tails:
        why = (f"{unusable} round(s) recorded no commit (verdicts written before schema 2)"
               if unusable else "no Codex verdict was added by this branch")
        if gap:
            # ⚠ THE RANGE, NOT THE BRANCH — r3 High, and the same honest contract `verdict()` states
            # six lines up: a stacked child is cleared by its PARENT's declaration. Not silently:
            # the pass NAMES the document, so a stacked pass is visible in the log instead of being
            # indistinguishable from a branch that declared for itself. Closing it properly needs
            # the true parent, which CI does not know; inventing half a mechanism would be worse.
            return 0, (f"final-tree rule NOT CHECKED — {why}; declared in this range by "
                       f"{gap}")
        return 2, (f"CANNOT RUN — {why}, so whether any round saw the code about to merge is "
                   f"UNKNOWN.\n"
                   f"  Treat this as NOT CHECKED, never as reviewed. Either run a Codex round "
                   f"against the current tree,\n"
                   f"  or record `REVIEW GAP: codex — <reason>` in a review document of this "
                   f"branch (docs/plugins.md).")
    clean = sorted(n for n, paths in tails.items() if not paths)
    if clean:
        extra = f"; {unusable} other round(s) recorded no commit" if unusable else ""
        # ⛔ "WAS IN THE TREE HANDED TO", NOT "WAS REVIEWED BY" — r11 High. `reviewed_state` stages
        # the whole working tree with no scope (`git add -A`, no pathspec), so a guarded file that
        # was merely dirty at dispatch and never in the round's subject is recorded as handed over.
        # Reproduced: an unrelated dirty file, in no prompt, cleared the gate under the old wording.
        # The wrapper cannot know what a reviewer READ and no representation can; the defect was a
        # green line claiming more than its evidence, in a gate whose whole selling point is stating
        # its own limits. The `prompt` field each verdict now carries is what a human reads to see
        # the scope those entries were taken under.
        return 0, f"the final tree was in the tree handed to {', '.join(clean)}{extra}"
    name, missed = min(tails.items(), key=lambda kv: (len(kv[1]), kv[0]))
    shown = ", ".join(missed[:6]) + (f" (+{len(missed) - 6} more)" if len(missed) > 6 else "")
    return 1, (f"{len(tails)} round(s) ran and guarded code was committed after every one of them.\n"
               f"  The closest ({name}) never saw:\n"
               f"    {shown}\n"
               f"  Run one more round against the current tree, or put `{NO_REVIEW} <reason>` in "
               f"the pull-request body.\n"
               f"  MEASURED 2026-09-13 over three rounds on two branches: the two review halves\n"
               f"  produced ZERO overlapping findings, and both defects that survived furthest were\n"
               f"  introduced by a FIX — code no round had seen.")


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)


def _final_entries(paths: list[str]) -> dict[str, str]:
    """path -> `"<mode> <object-id>"` in the tree that will merge. Absent means it is not in HEAD.

    ⚠ MODE IS PART OF IT — r2 Blocking. `git rev-parse HEAD:<path>` answers with the object id
    alone, so a change that flips ONLY the executable bit left the recorded and final shas equal and
    the file was credited as reviewed. `ls-tree` answers with the ENTRY, which is what a reviewer
    sees and what a commit stores.

    ⚠ EVERY ENTRY, NO TYPE FILTER — r4 Blocking. An earlier version kept only `blob` entries, to
    stop a gitlink's commit sha being compared against a blob's. That made a path holding a
    SUBMODULE read as absent, so a reviewer who saw the path deleted credited a merge that puts a
    gitlink there. The mode already separates them (`160000` gitlink, `120000` symlink,
    `100644`/`100755` file), so the filter bought nothing and cost a false pass.
    """
    if not paths:
        return {}
    got = _git("ls-tree", "-z", "HEAD", "--", *paths)
    return parse_ls_tree(got.stdout) if got.returncode == 0 else {}


def parse_ls_tree(out: str) -> dict[str, str]:
    """PURE. `git ls-tree -z` output -> `{path: "<mode> <object-id>"}`.

    ⚠ SPLIT FROM THE FETCH DELIBERATELY. The first version read git inline and its case did too —
    which went red the moment the mutation harness ran the suite inside its STAGED TREE, a copytree
    that is not a git checkout. A rule reachable only through a live repository is a rule the
    harness cannot measure, and a red control names the guard when the harness was what failed.
    """
    entries: dict[str, str] = {}
    for rec in out.split("\0"):
        meta, _, name = rec.partition("\t")
        parts = meta.split()
        # ⛔ NO TYPE FILTER — r4 Blocking, and it fired the REDESIGN falsifier r3's adjudication
        # wrote down. Keeping only `blob` entries made a SUBMODULE read as absent, so a reviewer
        # who saw a path deleted credited a merge that puts a gitlink there. The mode already
        # carries the type (`160000` gitlink, `120000` symlink, `100644`/`100755` file), so
        # comparing `"<mode> <sha>"` over EVERY entry cannot confuse a commit sha with a blob's —
        # which is the only thing the filter was there to prevent.
        if name and len(parts) >= 3:
            entries[name] = f"{parts[0]} {parts[2]}"
    return entries


def _load_verdict(rel: str) -> "object | None":
    """Read one verdict record. `None` if the file is gone; RAISES if it is there and unreadable."""
    p = ROOT / rel
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"CANNOT RUN — {rel} is unreadable ({exc}), so whether that round "
                           f"saw the final tree is UNKNOWN.")


def _is_ancestor(head: str) -> bool:
    return _git("merge-base", "--is-ancestor", head, "HEAD").returncode == 0


def _changed_since(head: str) -> list[str]:
    diff = _git("diff", "--name-only", "-z", "--no-renames", head, "HEAD")
    if diff.returncode != 0:
        raise RuntimeError(f"CANNOT RUN — git diff against {head[:12]} failed: "
                           f"{diff.stderr.strip()}")
    return [ln for ln in diff.stdout.split("\0") if ln]


def round_tails(verdict_files: list[str], branch_delta: list[str], *,
                load=None, is_ancestor=None, changed_since=None,
                final_entries=None) -> tuple[dict[str, list[str]], int]:
    """`(tails, unusable)` for `tail_verdict`. **I/O ONLY** — every decision here is a pure rule.

    ⚠ NO MERGE-BASE SKIP — r1 High. The first version also skipped a verdict whose head is an
    ancestor of the merge base, which silently discarded the round taken BEFORE the branch's first
    commit — precisely what the hold-fixes-uncommitted practice produces, and the case r1
    reproduced. Membership is now decided entirely by `branch_verdicts` (this branch ADDED the
    file), so reachability from HEAD is the only remaining question: a head we cannot diff against
    is a head we cannot reason about.

    ⛔ THE FOUR SEAMS ARE INJECTABLE BECAUSE r11 MEASURED THE ALTERNATIVE. Eight decision points
    lived in this function's body and none was reachable from any case; all eight survived mutation
    with the suite at 77/77, and two of them turned a live refusal into a live pass. The rules are
    now `classify_verdict`, `reviewed_map`, `tail_candidates` and `round_tail`; the callables below
    exist so a case can drive this loop without a repository, which is the same idiom
    `first_codex_gap(docs, parse)` already uses in this file — and r11 confirmed those stub cases
    are real, not decorative.

    `branch_delta` is `changed_paths(base)`, threaded in from `main` where it is already computed,
    so scoping the candidate set costs no extra git call.
    """
    load = load or _load_verdict
    is_ancestor = is_ancestor or _is_ancestor
    changed_since = changed_since or _changed_since
    final_entries = final_entries or _final_entries
    tails: dict[str, list[str]] = {}
    unusable = 0
    for rel in verdict_files:
        rec = load(rel)
        head, kind = classify_verdict(rec)
        if kind == SKIP:
            continue
        if kind != USABLE or head is None:
            unusable += 1
            continue
        if not is_ancestor(head):
            unusable += 1                   # unreachable: squashed, rebased or rewritten away
            continue
        reviewed = reviewed_map(rec)
        cands = tail_candidates(changed_since(head), reviewed, branch_delta)
        tails[pathlib.PurePosixPath(rel).name] = round_tail(
            cands, reviewed, final_entries(guarded_changes(cands)))
    return tails, unusable


def gap_names_codex(reason: "str | None") -> bool:
    """PURE. Is this `REVIEW GAP:` about the half that leaves a verdict?

    ⛔ r2 High. `has_gap_line` returns `"<who>: <reason>"` for EITHER half, and the first version
    accepted both. A branch could then declare `REVIEW GAP: claude — not invoked` and clear a
    missing CODEX verdict — an explanation of one absence excusing a different one. Only the Codex
    half writes the testimony this rule reads, so only a Codex gap explains its absence.
    """
    return bool(reason) and reason.split(":", 1)[0].strip().lower() == "codex"


def _load_gap_line_parser():
    """`has_gap_line` from check-review-rounds, so both gates read one grammar.

    RAISES if it cannot be loaded. A gate that quietly fell back to its own regex is the duplicate
    this import exists to prevent, and it would look green while the two disagreed about one line.
    """
    path = ROOT / "scripts" / "check-review-rounds.py"
    spec = importlib.util.spec_from_file_location("_crr", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"CANNOT RUN — cannot load the REVIEW GAP parser from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_crr"] = mod
    spec.loader.exec_module(mod)
    return mod.has_gap_line


def first_codex_gap(docs: "list[tuple[str, str]]", parse) -> "str | None":
    """PURE given `parse`. `"<path> — <who>: <reason>"` for the first Codex gap, or None.

    ⛔ IT CARRIES THE PATH — r4 High, and the finding was against my own adjudication rather than
    the code: r3 accepted that a stacked child is cleared by its parent's declaration ON CONDITION
    that the pass NAMES the document, and then the message printed only the reason. A claim in a
    review record that the code does not deliver is worse than the gap it excused.

    Split out from the file reading so the RULE — which gaps count — is driven by cases holding the
    real parser and literal text. r2's High lived exactly here, and a rule reachable only through
    the filesystem is a rule a mutation cannot be aimed at.
    """
    for path, text in docs:
        reason = parse(text)
        if gap_names_codex(reason):
            return f"{path} — {reason}"
    return None


def readable_docs(review_docs: list[str], read) -> list[tuple[str, str]]:
    """PURE given `read`. `(path, text)` for the documents that are actually on disk.

    ⛔ r11 High (lens 3): this filter lived inside `declared_gap` and deleting it left the suite at
    77/77. A document named by the diff but absent now — added in the range and deleted again —
    must not be read, and must not be able to declare a gap on this branch's behalf. `read` returns
    `None` for a path that is gone, which is the one thing a case cannot arrange without a
    filesystem.
    """
    out = []
    for rel in review_docs:
        text = read(rel)
        if text is not None:
            out.append((rel, text))
    return out


def _read_doc(rel: str) -> "str | None":
    p = ROOT / rel
    return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else None


def declared_gap(review_docs: list[str], read=_read_doc) -> "str | None":
    """The Codex `REVIEW GAP:` reason recorded in one of this branch's review documents, or None.

    The parser is `check-review-rounds.has_gap_line`, IMPORTED. Which emphasis wraps the marker and
    what counts as a stated reason cost that file measured escapes; a sibling re-deriving them would
    drift, and the two gates would then disagree about the same line in the same file.
    """
    mod_parse = _load_gap_line_parser()
    docs = readable_docs(review_docs, read)
    return first_codex_gap(docs, mod_parse)
    # ⚠ `review_docs` is every review document ADDED IN THE RANGE, which for a stacked branch
    # includes its parent's. Stated in the docstring, named in the message, not papered over.


def changed_paths(base: str) -> list[str]:
    """Paths changed against `base`. RAISES on anything that would understate the answer.

    ⚠ `-z`, NOT `splitlines()` — r11 Medium. With the default `core.quotePath`, any non-ASCII path
    comes back C-quoted (`"lib/na\\303\\257ve.ts"`) and is no longer the path, so a branch adding a
    review document whose subject carries an accent was told *"no review round was recorded"* and
    its verdict was invisible. `round_tails` already used `-z`; these two did not. It is the same
    defect class r1's Medium #6 fixed in the sibling gatherer — fixed there as an INSTANCE, not
    searched for as a class, which is this project's own recorded failure shape. Every direction
    failed closed, which is why it was Medium and not higher.
    """
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
    diff = subprocess.run(["git", "-C", str(ROOT), "diff", "--name-only", "-z",
                           merge_base.stdout.strip(), "HEAD"], capture_output=True, text=True)
    if diff.returncode != 0:
        raise RuntimeError(f"CANNOT RUN — git diff failed: {diff.stderr.strip()}")
    return split_nul(diff.stdout)


def split_nul(out: str) -> list[str]:
    """PURE. `git … -z` output -> paths. The falsifier for the `-z` repair above."""
    return [ln for ln in out.split("\0") if ln.strip()]


def added_paths(base: str) -> list[str]:
    """Paths ADDED against `base` (status A). RAISES like `changed_paths`; `-z` for the same reason."""
    mb = subprocess.run(["git", "-C", str(ROOT), "merge-base", base, "HEAD"],
                        capture_output=True, text=True)
    if mb.returncode != 0:
        raise RuntimeError(f"CANNOT RUN — cannot resolve a merge base with {base!r}")
    out = subprocess.run(["git", "-C", str(ROOT), "diff", "--name-only", "-z", "--diff-filter=A",
                          mb.stdout.strip(), "HEAD"], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"CANNOT RUN — git diff failed: {out.stderr.strip()}")
    return split_nul(out.stdout)


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
    if code:
        return code

    # ── the second question ──
    # Asked only when the first was answered by a REVIEW. If nothing guarded changed the question
    # is moot; if the author declared `NO-REVIEW:` it is waived by the same declaration, which is
    # why there is no second marker to write. `reason_of` is called again rather than threaded out
    # of `verdict()` — it is pure, and widening that function's return would break the tuple its
    # cases pin. The DECISION is `second_question`, which is pure and cased: r11 measured `if True:`
    # here leaving the suite green, i.e. this whole subsystem detachable with no red anywhere.
    ask, waived = second_question(changed, reason_of(body, NO_REVIEW))
    if not ask:
        if waived:
            print("ok — " + waived)
        return 0
    try:
        tails, unusable = round_tails(branch_verdicts(added), changed)
        gap = declared_gap(review_added(added))
    except (RuntimeError, OSError) as exc:
        print(str(exc) if str(exc).startswith("CANNOT RUN") else f"CANNOT RUN — {exc}",
              file=sys.stderr)
        return 2
    tcode, tmessage = tail_verdict(tails, unusable, gap)
    print(("FAILED — " if tcode else "ok — ") + tmessage,
          file=sys.stderr if tcode else sys.stdout)
    return tcode


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

    # ── THE SECOND QUESTION: did any round see the code that is about to merge? ──
    V = "docs/reviews/verdicts/x-r1-codex.verdict.json"
    case("a verdict this branch ADDED is one of its rounds", branch_verdicts([V]), [V])
    case("a review document is not a verdict",
         branch_verdicts(["docs/reviews/codex/x-r1-codex.md"]), [])
    case("a JSON file elsewhere under docs/ is not a verdict",
         branch_verdicts(["docs/anchors.json"]), [])
    # ⛔ THE PASS. A round with nothing committed after it saw the tree that will merge.
    case("a round with an empty tail passes", tail_verdict({"a.json": []})[0], 0)
    case("...and the pass NAMES the round that saw it, so a stacked pass is visible in the log",
         "a.json" in tail_verdict({"a.json": []})[1], True)
    # ⛔ THE FAILURE THIS EXISTS FOR: every round is stale, so the fixes merged unreviewed.
    case("code committed after EVERY round FAILS", tail_verdict({"a.json": ["lib/x.ts"]})[0], 1)
    case("...and the failure names the file no round saw",
         "lib/x.ts" in tail_verdict({"a.json": ["lib/x.ts"]})[1], True)
    # ⚠ ANY round clears it. Requiring the NEWEST would need an ordering the verdicts do not carry.
    case("one clean round among stale ones is enough",
         tail_verdict({"a.json": ["lib/x.ts"], "b.json": []})[0], 0)
    # ⚠ The report points at the round that missed LEAST — the shortest way back to green.
    case("the failure reports the CLOSEST round, not an arbitrary one",
         "b.json" in tail_verdict({"a.json": ["lib/x.ts", "lib/y.ts"], "b.json": ["lib/y.ts"]})[1],
         True)
    # ⛔ "CANNOT RUN" IS NOT A PASS — r1 High. The first version returned 0 here with an honest
    # NOT CHECKED line, and CI reads the exit code, not the line. `CLAUDE.md`: *"'Cannot run' is a
    # FAILURE, never a pass."* Exit 2 is the project's CANNOT RUN code, distinct from a finding.
    case("no round that can answer is CANNOT RUN, not a pass", tail_verdict({})[0], 2)
    case("...and says so in the project's words, so nobody reads it as reviewed",
         "CANNOT RUN" in tail_verdict({})[1], True)
    case("pre-schema-2 verdicts are counted and named, not silently dropped",
         "recorded no commit" in tail_verdict({}, unusable=3)[1], True)
    # ⚠ THE ESCAPE IS THE MARKER THAT ALREADY EXISTS. A Codex-down round genuinely cannot answer
    # this, and `docs/plugins.md` already requires it to say `REVIEW GAP:` in the review document.
    # Asking for a SECOND declaration of the same fact is the duplicate-vocabulary shape.
    case("a declared REVIEW GAP clears it", tail_verdict({}, gap="codex — usage limit")[0], 0)
    case("...and the pass repeats the declared reason into the log",
         "usage limit" in tail_verdict({}, gap="codex — usage limit")[1], True)
    # ⛔ AND THE GAP MUST NOT EXCUSE A STALE ROUND. It says "no Codex half ran", not "the code you
    # committed afterwards is fine" — if a round DID run and is stale, the gap is irrelevant.
    case("a declared gap does NOT excuse a round that exists and is stale",
         tail_verdict({"a.json": ["lib/x.ts"]}, gap="codex — usage limit")[0], 1)
    # ⚠ A clean round does not excuse silence about the others: the pass still reports what it
    # could not place, or "reviewed" would cover rounds nobody checked.
    case("...including alongside a clean round",
         "1 other round(s) recorded no commit" in tail_verdict({"a.json": []}, unusable=1)[1], True)
    # ── round_tail: the per-round rule, PURE so a mutation can reach it ──
    # ⭐ r1 Low: this used to assert on `guarded_changes` directly while the live call sat inside
    # the git-reading gatherer. Deleting that call left the suite at 45/45 — a case that named the
    # wiring and never touched it. The rule now lives HERE, and these cases drive it.
    case("the tail rule and the review obligation share one idea of `guarded`",
         round_tail(["docs/reviews/codex/x-r1-codex.md", "lib/x.ts"], {}, {}), ["lib/x.ts"])
    # ⛔ THE r1 BLOCKING, as a case. Same PATH, DIFFERENT CONTENT: the reviewer saw blob `aaa`, the
    # tree that merges holds `bbb`. Reproduced live before the fix — it passed, certifying code no
    # reviewer had seen, because subtraction was by name.
    case("a file edited AGAIN after the round is still missed, though its path matches",
         round_tail(["lib/x.ts"], {"lib/x.ts": "aaa"}, {"lib/x.ts": "bbb"}), ["lib/x.ts"])
    case("...and the SAME content the reviewer was handed is not missed",
         round_tail(["lib/x.ts"], {"lib/x.ts": "aaa"}, {"lib/x.ts": "aaa"}), [])
    # A path the reviewer saw uncommitted and that is NOT in the merging tree — deleted since — has
    # no final blob to equal, so it counts as missed. The safe direction.
    # ⛔ A REVIEWED DELETION IS A REVIEWED STATE — r3 Medium. The reviewer was handed a tree with
    # `lib/x.ts` gone; the merging tree also lacks it. Dropping deletions made that read as unseen
    # and failed the careful path for the crime of deleting code.
    #
    # ⚠ THE LITERAL, NOT THE CONSTANT, AND THAT IS NOT PEDANTRY. Written as
    # `{"lib/x.ts": ABSENT_ENTRY}` this case took its value from the same constant the rule
    # defaults to, so a mutation redefining `ABSENT_ENTRY` moved BOTH sides and the comparison
    # stayed true — the mutation SURVIVED, measured. The spelling is a wire format shared with
    # whatever the wrapper records, so the case pins it independently, the way an outside observer
    # must.
    _GIT_DELETION = "000000 " + "0" * 40      # what `git diff-index` writes; verified live
    case("the absent entry is spelled the way git spells a deletion", ABSENT_ENTRY, _GIT_DELETION)
    case("a deletion the reviewer saw is credited, because absence is a tree state too",
         round_tail(["lib/x.ts"], {"lib/x.ts": _GIT_DELETION}, {}), [])
    case("...while a path the reviewer saw PRESENT and that is now gone is still missed",
         round_tail(["lib/x.ts"], {"lib/x.ts": "100644 aaa"}, {}), ["lib/x.ts"])
    case("...and a path nobody reviewed is missed whether or not it is absent",
         round_tail(["lib/x.ts"], {}, {}), ["lib/x.ts"])
    case("a clean round after which nothing guarded changed has an empty tail",
         round_tail(["docs/backlog.md"], {}, {}), [])
    # ⛔ THE r2 BLOCKING, as a case. SAME BYTES, NEW MODE: `bin/t.sh` reviewed at 100644 and merged
    # at 100755 is a change the reviewer did not see, and comparing content alone credited it.
    case("a mode-only change after the round is still missed, though the blob matches",
         round_tail(["bin/t.sh"], {"bin/t.sh": "100644 aaa"}, {"bin/t.sh": "100755 aaa"}),
         ["bin/t.sh"])
    case("...and an identical tree entry — same mode, same blob — is not missed",
         round_tail(["bin/t.sh"], {"bin/t.sh": "100755 aaa"}, {"bin/t.sh": "100755 aaa"}), [])
    # ── r11: the candidate set. TWO findings in one expression, pulling opposite ways ──
    _DELTA = ["lib/x.ts", "lib/y.ts", "docs/backlog.md"]
    case("a path that changed since the round is a candidate",
         tail_candidates(["lib/x.ts"], {}, _DELTA), ["lib/x.ts"])
    # ⛔ THE r11 BLOCKING. `reviewed`'s keys are the paths where the reviewer's view DIFFERED from
    # the round's commit, so "unchanged since head" means "not what the reviewer read". Reverting an
    # overlay used to drop the path out of the compared set and the round was credited with the
    # final tree — reproduced end to end as GOOD reviewed, BAD merged, exit 0.
    case("a REVERTED dirty overlay is STILL a candidate, though nothing changed since the round",
         tail_candidates([], {"lib/x.ts": "100644 aaa"}, _DELTA), ["lib/x.ts"])
    case("...and without the union nobody compares it at all",
         tail_candidates([], {"lib/x.ts": "100644 aaa"}, _DELTA) == [], False)
    # ⛔ THE r11 HIGH, the other direction. Under CI's synthesised merge ref the base's whole
    # movement landed in `after`, so the branch was charged for code it never touched.
    case("a path the BASE changed, outside this branch's delta, is not charged",
         tail_candidates(["scripts/newguard.py"], {}, _DELTA), [])
    case("...while one in both the diff and the branch delta still is",
         tail_candidates(["scripts/newguard.py", "lib/y.ts"], {}, _DELTA), ["lib/y.ts"])
    case("an untracked scratch file dirty at dispatch is not charged forever either",
         tail_candidates([], {"scratch.tmp": "100644 aaa"}, _DELTA), [])
    case("the answer is sorted and deduplicated, so one path cannot be charged twice",
         tail_candidates(["lib/y.ts", "lib/x.ts"], {"lib/x.ts": "100644 aaa"}, _DELTA),
         ["lib/x.ts", "lib/y.ts"])
    # ⚠ `branch_delta` IS VARIED, not passed one constant — `check-fixture-variation` refused the
    # first draft of these cases for exactly that, which is the ratchet doing its job on the repair
    # for a finding about unreachable rules.
    case("an EMPTY branch delta charges nothing at all",
         tail_candidates(["lib/x.ts"], {"lib/y.ts": "100644 aaa"}, []), [])
    case("...and a delta naming a different file charges that one instead",
         tail_candidates(["lib/x.ts", "lib/z.ts"], {}, ["lib/z.ts"]), ["lib/z.ts"])
    # ── r11: classifying one verdict record. Extracted from the gatherer, where all four rules
    # survived mutation with the suite green and two of them were live fail-opens. ──
    case("a schema-2 verdict whose gate RAN is usable, and the head comes back stripped",
         classify_verdict({"gate_ran": True, "head": " abc123 \n"}), ("abc123", USABLE))
    case("a verdict saying the gate did NOT run is skipped, never read as testimony",
         classify_verdict({"gate_ran": False, "head": "abc123"}), (None, SKIP))
    case("...and that rule is the one whose deletion turned exit 2 into exit 0",
         classify_verdict({"gate_ran": False, "head": "abc123"})[1] == USABLE, False)
    case("a schema-1 verdict carries no head: UNUSABLE, not skipped",
         classify_verdict({"gate_ran": True}), (None, UNUSABLE))
    case("...as is one whose head is blank",
         classify_verdict({"gate_ran": True, "head": "   "}), (None, UNUSABLE))
    # ⛔ r11 Medium, found by two lenses independently: a FAILED snapshot used to be byte-identical
    # to a genuinely clean tree, so it accused the author who held their fixes back.
    case("a verdict whose dirty map is NULL could not look — unusable, not a clean tree",
         classify_verdict({"gate_ran": True, "head": "abc", "dirty": None}), (None, UNUSABLE))
    case("...while an EMPTY map is a real answer: the tree WAS clean",
         classify_verdict({"gate_ran": True, "head": "abc", "dirty": {}}), ("abc", USABLE))
    case("a verdict added in the range and deleted again cannot testify",
         classify_verdict(None), (None, UNUSABLE))
    case("...and neither can a record that is not an object at all",
         classify_verdict(["not", "a", "record"]), (None, UNUSABLE))
    # ── r11: the dirty map, extracted for the same reason — emptying it made every overlay
    # comparison vacuous and the suite did not notice. ──
    case("the dirty map is read from the verdict",
         reviewed_map({"dirty": {"a": "100644 aa"}}), {"a": "100644 aa"})
    case("...and entries that are not string -> string are dropped rather than trusted",
         reviewed_map({"dirty": {"a": 1, "c": "100644 cc"}}), {"c": "100644 cc"})
    case("a null dirty map reads as empty HERE; classify_verdict is what refuses it",
         reviewed_map({"dirty": None}), {})
    # ── r11: the second question is a rule, not a line. `if True:` in its place left the suite at
    # 77/77 — the entire subsystem detachable with no red anywhere. ──
    case("guarded code and no waiver: the question is asked",
         second_question(["lib/x.ts"], None), (True, None))
    case("nothing guarded changed: the question is moot, and says nothing",
         second_question(["docs/backlog.md"], None), (False, None))
    case("a NO-REVIEW waiver skips the question",
         second_question(["lib/x.ts"], "master moved")[0], False)
    case("...and ECHOES the reason, so exit 0 is not attributed to the review documents",
         "master moved" in (second_question(["lib/x.ts"], "master moved")[1] or ""), True)
    case("...saying WAIVED, not passed",
         "WAIVED" in (second_question(["lib/x.ts"], "master moved")[1] or ""), True)
    # ── r11: `-z` parsing, the repair for C-quoted paths ──
    case("NUL-separated output splits on NUL, so an accented path survives whole",
         split_nul("lib/naïve.ts\0lib/b.ts\0"), ["lib/naïve.ts", "lib/b.ts"])
    case("...and a newline inside a path does not split it",
         split_nul("lib/od\nd.ts\0"), ["lib/od\nd.ts"])
    # ── r11: a review document named by the diff but gone from disk must not be read ──
    case("a review document that is gone is not read and cannot declare a gap",
         readable_docs(["gone.md", "here.md"],
                       lambda r: None if r == "gone.md" else "text"), [("here.md", "text")])
    case("...and the reader argument is the one used",
         readable_docs(["here.md"], lambda r: "REVIEW GAP: codex — x"),
         [("here.md", "REVIEW GAP: codex — x")])
    # ── r11: the gatherer itself, driven with stubs so every seam is varied without a repository ──
    _V = ["docs/reviews/verdicts/a.verdict.json"]
    _CLEAN = {"gate_ran": True, "head": "h1", "dirty": {}}
    _HELD = {"gate_ran": True, "head": "h1", "dirty": {"lib/x.ts": "100644 aaa"}}
    _t, _u = round_tails(_V, ["lib/x.ts"], load=lambda r: _CLEAN, is_ancestor=lambda h: True,
                         changed_since=lambda h: ["lib/x.ts"], final_entries=lambda p: {})
    case("the gatherer builds one tail per usable verdict", sorted(_t), ["a.verdict.json"])
    case("...charging a round for a guarded file that changed after it", _t["a.verdict.json"],
         ["lib/x.ts"])
    case("...and counts nothing unusable when the verdict is fine", _u, 0)
    _t2, _u2 = round_tails(_V, ["lib/x.ts"], load=lambda r: _CLEAN, is_ancestor=lambda h: False,
                           changed_since=lambda h: ["lib/x.ts"], final_entries=lambda p: {})
    case("a head no longer reachable — rebased or squashed — is UNUSABLE, never a pass",
         (_t2, _u2), ({}, 1))
    _t3, _u3 = round_tails(_V, ["lib/x.ts"], load=lambda r: None, is_ancestor=lambda h: True,
                           changed_since=lambda h: [], final_entries=lambda p: {})
    case("a verdict file that is gone leaves no tail and is counted", (_t3, _u3), ({}, 1))
    _t4, _u4 = round_tails(_V, ["lib/x.ts"], load=lambda r: _HELD, is_ancestor=lambda h: True,
                           changed_since=lambda h: ["lib/x.ts"],
                           final_entries=lambda p: {"lib/x.ts": "100644 aaa"})
    case("a round handed the entry that finally merges has an empty tail",
         _t4["a.verdict.json"], [])
    _t5, _u5 = round_tails(_V, ["lib/x.ts"], load=lambda r: _HELD, is_ancestor=lambda h: True,
                           changed_since=lambda h: [],          # the overlay was REVERTED
                           final_entries=lambda p: {"lib/x.ts": "100644 bbb"})
    case("THE BLOCKING through the gatherer: a reverted overlay is charged, not silently cleared",
         _t5["a.verdict.json"], ["lib/x.ts"])
    _t6, _u6 = round_tails(_V, ["lib/x.ts"], load=lambda r: _CLEAN,
                           is_ancestor=lambda h: True,
                           changed_since=lambda h: ["scripts/newguard.py"],
                           final_entries=lambda p: {})
    case("THE HIGH through the gatherer: a file only the base changed is not charged",
         _t6["a.verdict.json"], [])
    # ⚠ `verdict_files` and `branch_delta` VARIED here for the same reason as above.
    _t7, _u7 = round_tails([], ["lib/x.ts"], load=lambda r: _CLEAN, is_ancestor=lambda h: True,
                           changed_since=lambda h: ["lib/x.ts"], final_entries=lambda p: {})
    case("no verdicts at all leaves an empty map, for tail_verdict to turn into CANNOT RUN",
         (_t7, _u7), ({}, 0))
    _t8, _u8 = round_tails(_V + ["docs/reviews/verdicts/b.verdict.json"], ["lib/y.ts"],
                           load=lambda r: _CLEAN, is_ancestor=lambda h: True,
                           changed_since=lambda h: ["lib/y.ts"], final_entries=lambda p: {})
    case("every verdict gets its own tail, each judged against the same branch delta",
         (sorted(_t8), _t8["b.verdict.json"]),
         (["a.verdict.json", "b.verdict.json"], ["lib/y.ts"]))
    # ⛔ THE r2 HIGH. A gap about the CLAUDE half explains a different absence: only the Codex half
    # writes the verdict this rule reads, so only a Codex gap can excuse its absence.
    case("a REVIEW GAP naming codex explains a missing verdict",
         gap_names_codex("codex: usage limit"), True)
    case("...one naming claude does NOT — it explains a different absence",
         gap_names_codex("claude: not invoked; ran as r2"), False)
    case("...and no gap line at all is not a declaration",
         gap_names_codex(None), False)
    # The parser hands back `<who>: <reason>`; matching must not be fooled by the reason's text.
    case("the WHO is read, not the reason — a claude gap mentioning codex stays a claude gap",
         gap_names_codex("claude: codex ran instead"), False)
    # ⭐ THE REAL PARSER over literal text: `first_codex_gap` is handed `has_gap_line` itself, so
    # these exercise the rule the live path uses, not a stand-in weaker than its subject.
    _parse = _load_gap_line_parser()
    _D = "docs/reviews/codex/x-r1-codex.md"
    case("a codex gap in a review document is accepted",
         first_codex_gap([(_D, "**REVIEW GAP:** codex — usage limit")], _parse),
         f"{_D} — codex: usage limit")
    # ⛔ r4 High: the pass must NAME the document. A stacked branch is cleared by its parent's
    # declaration — an accepted limit — and the only thing that keeps that from being invisible is
    # printing which file said it. The adjudication claimed this before the code did it.
    case("...and the answer NAMES the document, so a stacked pass is visible in the log",
         _D in (first_codex_gap([(_D, "REVIEW GAP: codex — usage limit")], _parse) or ""), True)
    case("...a claude-only gap is NOT accepted, however emphatic",
         first_codex_gap([(_D, "**REVIEW GAP:** claude — not invoked; ran as r2")], _parse), None)
    case("...and a codex gap is found past a claude one",
         first_codex_gap([("a.md", "REVIEW GAP: claude — not invoked"),
                          (_D, "REVIEW GAP: codex — usage limit")], _parse),
         f"{_D} — codex: usage limit")
    # ⚠ `parse` IS CALLED, not decorative — every case above passes the real parser, so none of them
    # could tell the difference between using the argument and importing one. Surfaced by
    # check-fixture-variation: a parameter no case varies is a clause no case guards.
    case("the parser argument is the one used — a stub that sees a codex gap in anything wins",
         first_codex_gap([("z.md", "no marker here at all")], lambda _t: "codex: stubbed"),
         "z.md — codex: stubbed")
    case("...and a stub that sees nothing finds nothing, in text that really has a gap",
         first_codex_gap([(_D, "REVIEW GAP: codex — usage limit")], lambda _t: None), None)
    # ⛔ THE FINAL-TREE LOOKUP. The mode half of the r2 Blocking lives HERE, not in `round_tail` —
    # a case feeding `round_tail` literal strings can never see it. Driven by real `ls-tree -z`
    # output rather than a live repository, because the mutation harness runs this suite inside a
    # staged copy that is not a git checkout (measured: the first version's control went red).
    # ⛔ ONE SHA ACROSS ALL THREE — r11 Medium, and the reason is that the cases below are NAMED for
    # collisions they could not have. With three different shas, "two files with identical content
    # but different modes do not collide" compared entries differing in BOTH, and "...it cannot
    # compare equal to a blob with the same sha" held under the very mutation it guards: dropping
    # the mode from `parse_ls_tree` (the r2 Blocking, restored) reds three sibling cases and left
    # that one green. Sharing the sha is what makes the scenario each case names actually present —
    # measured: with it, the same mutation takes the case from 74/77 to 73/77.
    _SHA = "1111111111111111111111111111111111111111"
    _LS = (f"100644 blob {_SHA}\tlib/a.ts\0"
           f"100755 blob {_SHA}\tbin/t.sh\0"
           f"160000 commit {_SHA}\tvendor/sub\0")
    # ⚠ `.get`, NOT `[...]`, AND THAT IS A CONTRACT NOT A STYLE CHOICE. Written with subscripts,
    # the mutation that restores the blob filter raised KeyError — the suite went RED and printed
    # no `[FAIL] <case>` line, so the harness could not see WHICH case killed it and reported every
    # entry for this file as unattributable. A case must FAIL, not crash.
    _tree = parse_ls_tree(_LS)
    case("the lookup answers with an ENTRY — mode and object id, not a bare sha",
         _tree.get("lib/a.ts"), f"100644 {_SHA}")
    case("...so two files with identical content but different modes do not collide",
         _tree.get("bin/t.sh", "").split()[:1], ["100755"])
    # ⛔ r4 BLOCKING, inverted into a case. The gitlink used to be FILTERED OUT, so a path holding a
    # submodule looked absent — and a reviewer who saw that path DELETED was credited for a merge
    # that puts a gitlink there. Every entry is kept; the mode is what stops a commit sha from ever
    # equalling a blob's.
    case("a submodule gitlink is KEPT, so a path holding one can never read as absent",
         _tree.get("vendor/sub"), f"160000 {_SHA}")
    case("...and its mode marks it, so it cannot compare equal to a blob with the same sha",
         _tree.get("vendor/sub", "x").split()[:1] == _tree.get("lib/a.ts", "y").split()[:1], False)
    # ⚠ ABSENCE IS A SHAPE, NOT A WIDTH — r4 Medium. A SHA-256 repository writes 64 zeros.
    case("a 40-zero deletion is absence", is_absent("000000 " + "0" * 40), True)
    case("...and so is a 64-zero one, because the width is not the meaning",
         is_absent("000000 " + "0" * 64), True)
    case("...while a real entry is not absence", is_absent("100644 " + "a" * 40), False)
    case("...and neither is nothing at all", is_absent(None), False)
    case("a deletion recorded at one sha width matches an absence at another",
         round_tail(["lib/x.ts"], {"lib/x.ts": "000000 " + "0" * 64}, {}), [])
    case("empty output is an empty answer, not an invented one", parse_ls_tree(""), {})

    # ⛔ THE FAILURE LINE IS A CONTRACT, NOT A STYLE CHOICE. `check-plan-code`'s mutation harness
    # attributes a kill by reading `l.strip().startswith("[FAIL] ")`, slicing `[7:]`, then
    # `rsplit(": got ", 1)[0]` for the case name. This suite first printed `  FAIL  <name>` with the
    # values on a second line, so ALL SIX mutations reported *"matched 0 red case(s) — caught by
    # something else: []"* while every one of them was in fact being killed by the case it named.
    # "The guard did not fire" and "nothing could see it fire" look identical from here.
    failed = 0
    for name, got, want in cases:
        ok = got == want
        failed += not ok
        print(f"  ok     {name}" if ok else f"  [FAIL] {name}: got {got!r} want {want!r}")
    print(f"\n{len(cases) - failed}/{len(cases)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
