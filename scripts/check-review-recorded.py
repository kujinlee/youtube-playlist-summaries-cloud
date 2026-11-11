#!/usr/bin/env python3
"""A branch that changes CODE records a review round, or says in writing why it did not.

    python3 scripts/check-review-recorded.py --base origin/master --pr-body-file /tmp/pr-body.md
    python3 scripts/check-review-recorded.py --self-test  # 285 cases

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
  * ⟳ 2026-10-31: BOTH halves can leave a verdict. `codex-review.py` writes one at dispatch; a
    Claude half's is written after it is filed, by `record-review-verdict.py`, as the same record
    (`writer: claude`, `dirty: {}`, a head the review itself names). Nothing here reads the writer,
    so the rule is unchanged. A round with NO verdict cannot answer this question at all — which
    is CANNOT RUN, cleared by a `REVIEW GAP:` naming **codex** (a gap about the other half explains
    a different absence). ⚠ Like the recorded-review question,
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
  * ⛔ AND MASTER'S CHANGES ARE SUBTRACTED PER FILE, NOT JUST PER PATH (backlog #426). The path
    scope above misses a file BOTH sides touched: the branch reviewed `ci.yml` at round 2, master
    then changed `ci.yml` too, and re-merging master charged the round for master's hunk — PR #487
    paid an extra round for exactly that. So a path the round's own commit did not hand over dirty
    is cleared when HEAD's entry equals `merge-tree(round's commit, merge-base(base, HEAD))`: what
    the reviewed tree becomes when master's changes since are added and NOTHING else. A TREE
    comparison, not a commit walk, because a walk has to decide what a merge commit "did" — and a
    conflict resolution or an evil merge lives inside one, invisible to any rule that skips merges.
    Comparing against the synthesised merge catches both with no special case. A path that merge
    CONFLICTED is never cleared, a dirty-overlay path keeps the strict rule (its blobs are not in
    CI's object store), and if the merge cannot be built the rule falls back to strict — every
    failure leaves a round REQUIRED, never cleared.
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
import ast
import contextlib
import importlib.util
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Callable

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
# `(entries, conflicted)` of `merge-tree(<round's commit>, merge-base(base, HEAD))`, or `None` when
# that merge could not be built — see `master_explains` (backlog #426).
MasterSide = "tuple[dict[str, str], frozenset[str]] | None"


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

# ⛔ `docs/` IS NOT PROSE IN THIS REPOSITORY, AND THE PARAGRAPH ABOVE ARGUES FROM A PREMISE THAT IS
# FALSE HERE — r15 High, measured. *"A denylist of PROSE can be completed, because prose is the small
# set: `docs/`"* was never completed. Two of the FIFTEEN schema gates are files under `docs/`:
#
#     docs/superpowers/specs/2026-08-03-stable-blob-addressing/verify-schema.sh   gate 1/15
#     docs/superpowers/specs/2026-08-03-stable-blob-addressing/mutate-schema.py   gate 2/15
#     docs/superpowers/specs/m4/{live-manifest,accepted-additions}.txt, *.sql     gates 10 and 14
#
# `scripts/check-schema-gates.sh:19` resolves `SPEC` to that directory and executes them, and both
# are mode `755` — measured, the ONLY two mode-755 files tracked anywhere under `docs/`.
# ⟳ 2026-09-16 (#137): this used to cite `schema-gates.yml`'s PATH FILTERS as a third witness.
# That file HAS no path filters now, and the cited line numbers point at unrelated prose — a stale
# citation is worse than none, because it reads as corroboration.
#
# Measured before the fix: `is_prose` said True for all of them, `guarded_changes` returned `[]`,
# `verdict` returned *"no guarded path changed — a review round is not required"*, and because
# `second_question` short-circuits on `not guarded_changes(changed)` the final-tree question was
# never asked either. **BOTH HALVES OF THIS GATE WENT SILENT OVER EXECUTABLE CI GATE CODE** — a
# branch weakening a mutation in `mutate-schema.py`, or relaxing a line in `live-manifest.txt` so a
# gate stops noticing a schema object, merged with no round and no declaration. That is the
# 2026-09-09 night in WHY THIS EXISTS, reached through the classifier instead of through the diff.
#
# ⚠ IT ALSO FALSIFIES A RECORDED REVIEW CLAIM, which is why it is here and not a footnote. The r11
# Claude half states it *"searched `docs/` for executable or consumed artefacts that would be
# wrongly exempt: everything found is `*.md` and `docs/reviews/verdicts/*.json`."* Two exist, both
# are gates, both are named in a CI path filter. r15 found them by RE-DERIVING that claim instead of
# inheriting it — the same move that found r14's rename fail-open one round earlier.
#
# ⚠ STATED LIMIT, NOT PAPERED OVER — AND ⟳ 2026-09-16 (#137) THE AUTHORITY IT DRIFTS FROM MOVED.
# This tuple was a second copy of `schema-gates.yml`'s path filters; those are deleted, so it is
# now a DECLARATION checked against what the gate scripts themselves read. TWO falsifiers keep it
# honest and they run in this order, which is load-bearing:
#   1. `declared_not_derived()` — does the derivation still FIND everything declared here? Asked
#      FIRST, because a broken derivation makes question 2 EASIER to pass. ⟳ r1 High 2 (claude):
#      without it, deleting the gate-script discovery loop left the suite green at 153/153 while
#      two of three directories vanished and the gate reported success.
#   2. `prose_exceptions_cover()` — is everything derived also exempt from the prose classifier?
# ⛔ NEITHER catches a BRAND-NEW `docs/` gate directory nobody has declared. This tuple is the
# FLOOR, not the ceiling, and no predicate can close that: measured 2026-09-16, accepting bound
# DIRECTORIES admits `docs/adr`, `docs/reviews` and `docs/superpowers`, and no content rule
# excludes them either, because `docs/superpowers` CONTAINS the gate directories.
CODE_UNDER_PROSE = (
    "docs/superpowers/specs/2026-08-03-stable-blob-addressing/",
    "docs/superpowers/specs/m4/",
)


def is_prose(path: str) -> bool:
    """PURE. Whether `path` is prose, and therefore owes no review round."""
    # CODE first: a gate script does not stop being code by living in a documentation directory.
    #
    # ⚠ EXCEPT `.md`, AND THE CARVE-OUT IS PROSPECTIVE — r16 Medium corrected the justification that
    # stood here. It said *"the spec's own prose lives beside its gate scripts"*, present tense.
    # Re-derived: **zero `.md` files are tracked under either exempted directory today**, so the
    # carve-out protects nothing yet and the case that pins it uses a path that does not exist. It
    # stays anyway, as policy for the first `.md` anyone writes there: removing it would oblige a
    # review round for a design-document edit, which is how backlog #56 measured a gate getting
    # switched off. What the gates actually consume from those two directories was
    # enumerated from `check-schema-gates.sh` — `helper*.sh`, `mutate-schema.py`,
    # `verify-schema.sh`, `live-manifest.txt`, `accepted-additions.txt`, `*.sql`. **No `.md` is read
    # by any gate.** ⚠ The limit that leaves: a `.md` in one of these directories that LATER becomes
    # a gate input would be wrongly prose again, and `prose_exceptions_cover` cannot see that — it
    # compares directories, not file roles.
    if any(path.startswith(d) for d in CODE_UNDER_PROSE):
        return path.endswith(".md")
    if path in PROSE_FILES:
        return True
    if any(path.startswith(d) for d in PROSE_DIRS):
        return True
    # a Markdown file at the repository ROOT is prose; one inside a package is not necessarily
    # ⚠ Two lines so the two DIRECTIONS carry separate anchors: "prose swallows everything"
    # (too permissive) and "the fallback goes" (too restrictive, r4 Low 4) are different
    # defects and a single expression cannot hold both entries.
    is_root_md = path.endswith(".md") and "/" not in path
    return is_root_md


def prose_exceptions_cover(gate_dirs: list[str], declared: "tuple[str, ...]") -> list[str]:
    """PURE. The `docs/` gate directories that `CODE_UNDER_PROSE` does NOT cover — empty is correct.

    The COVERAGE half of the anti-drift pair (`declared_not_derived` is the completeness half, and
    runs first). Every `docs/` directory holding gate machinery must also be exempt from the prose
    classifier, or CI runs the gates on a change this file just waved through as documentation.

    ⟳ r3 Low 7 (claude): `declared` IS A PARAMETER NOW. It used to read the module constant while
    its sibling `declared_not_derived` took the tuple as an argument, so `antidrift_verdict`'s
    `declared` governed only ONE of its two prongs — and a future case passing a fixture tuple to
    drive this rule would silently have exercised the real one. That is the "a case can pass for an
    AMBIENT reason" shape, pre-installed in the fix written to remove it.

    ⟳ 2026-09-16 (#137): the argument used to be `schema-gates.yml`'s path-filter GLOBS. That file
    has no path filters now — a workflow-level filter is what made the `schema-gates` check
    unrequireable — so it is passed DERIVED directories instead. The rule is unchanged and
    deliberately so: it still accepts a glob's `*` prefix and a directory written without its
    trailing slash, and its three mutation entries anchor on this body by text.

    Given the directories rather than reading them, so the rule stays pure and a case can drive it
    with the real ones — the same shape as `first_codex_gap(docs, parse)` elsewhere in this file.
    """
    missing = []
    for g in gate_dirs:
        # ⚠ INERT TODAY, AND KEPT AS PROSPECTIVE — r3 Low 8 (claude), measured: dropping the
        # glob-star split leaves the suite green, because `gate_code_dirs` can no longer produce a
        # `*`. Prong 1's regex is `[\w./-]+` (no `*`) and prong 2 requires the path to EXIST as a
        # file. The authority this was written for — `schema-gates.yml`'s globs — is what #137
        # deleted, so it has been dead since `839bc738`. It stays because the rule is still
        # documented as glob-tolerant and a future caller may pass one; it carries no mutation
        # entry, because a clause that cannot receive its input cannot have a falsifier.
        prefix = g.split("*")[0]
        # ⛔ `docs` WITHOUT A TRAILING SLASH IS STILL A `docs/` SUBJECT — r2 Medium 2 (claude).
        # `"docs".startswith("docs/")` is False, so a derived bare `docs` was SKIPPED rather than
        # reported, and `gate_code_dirs` produces exactly that for any bound path one level deep
        # (`p.rsplit("/", 1)[0]` of `docs/gate-rules.sql`). Both prongs then reported success over a
        # directory neither had examined — the r16 High shape this rule's docstring records, whose
        # fix closed the broader-glob route and left the bare-directory route open.
        if prefix != "docs" and not prefix.startswith("docs/"):
            continue
        # ⛔ `e.startswith(prefix)` USED TO BE THE SECOND DISJUNCT, AND IT CLEARED EVERY BROADER
        # GLOB — r16 High. `docs/**` in the path filter made this report FULL COVERAGE while
        # `is_prose("docs/gate.sh")` was still True, and broadening a filter to a parent directory
        # is the ordinary way that file grows. The clause was also unfalsifiable: all three cases
        # fed globs equal to or under an exemption, so only `prefix.startswith(e)` was ever
        # exercised, and DELETING the disjunct left the suite at 134/134.
        # What it legitimately absorbed is a glob written without its trailing slash, and only
        # that survives.
        if not any(prefix.startswith(e) or e == prefix.rstrip("/") + "/"
                   for e in declared):
            missing.append(g)
    return missing


# The ONE suffix that keeps a `docs/` file prose even when a gate reads it. This is not a new rule:
# `is_prose` above already treats a `.md` under an exempted directory as prose, and says why. A gate
# that READS prose does not make that prose into gate code — `check-docs.py` binds `docs/backlog.md`,
# `docs/plugins.md` and `docs/dev-process.md`, all of which this gate is supposed to wave through.
#
# ⟳ 2026-09-16, r1 High (codex): THIS WAS AN ALLOW-LIST — `(".sql", ".txt")` — AND IT FAIL-OPEN'd
# BY OMISSION. Reproduced by the reviewer rather than argued: a new gate reading
# `docs/superpowers/specs/new-gate/rules.json` is invisible to the derivation, the CURRENT gates keep
# the result non-empty so the CANNOT-RUN guard is satisfied, and a later PR editing that gate's
# rules classifies as PROSE and owes no review round. JSON/YAML config is an ordinary shape for a new
# checker, so the omission was not exotic. ⚠ Inverting it to "any suffix but `.md`" FAILS TODAY, and
# measuring that is what produced the shape below: `check-docs.py` binds a REGEX
# (`docs/adr/(\d{4})…`) and `check-sentinel-meanings.py` binds a PROSE MESSAGE containing a path —
# neither is a path, both would be reported as uncovered gate directories, and the gate would go red
# over nothing. The old allow-list was accidentally doing two jobs: excluding prose AND excluding
# strings that are not paths. Those are now separated — `.md` answers *is it prose*, and EXISTENCE
# answers *is it a path* — which closes the reviewer's finding as a CLASS rather than by adding
# `.json` and waiting for the next suffix.
PROSE_SUFFIX = ".md"

# The per-component byte limit on both Linux and macOS. ⚠ A NAME, not an inline literal, so the
# byte-width rule and the limit itself carry SEPARATE mutation anchors — sharing one anchor is
# exactly what made `--mutate .` refuse the entire manifest in r1 Blocking 1.
COMPONENT_LIMIT = 255

# The TOTAL path byte limit — ⟳ r2 Medium 4 (claude). `ENAMETOOLONG` is raised for
# `strlen(path) > PATH_MAX` as well as for an over-long component, and PATH_MAX is 1024 on macOS /
# 4096 on Linux; the reviewer RAN both interpreters and showed a 1200-byte path whose every
# component is 100 bytes still raising on 3.12. The first version of this guard bounded only the
# component while its docstring claimed "no python version can crash it". Conservative bound.
PATH_LIMIT = 1024


def _joined_path(node: "ast.AST") -> "str | None":
    """PURE. A `/`-operator chain of string constants reassembled, or None if it is not one.

    `pathlib`'s `Path("a") / "b" / "c.json"` is an `ast.BinOp` tree of `Div` nodes whose leaves
    include string constants; joining them in source order reconstructs the path. Non-string leaves
    (`ROOT`, a call, a variable) contribute nothing, so `DOCSDIR / name` yields no parts at all.

    ⚠ `len(parts) > 1` IS INERT AND IS SAID SO RATHER THAN DEFENDED — measured 2026-09-16 by
    mutating it to `> 0` and watching the suite stay GREEN. A join with exactly ONE string constant
    returns that constant, which the per-constant scan in `bound_docs_paths` finds anyway, and the
    result is added to a `set`, so the two paths cannot disagree. It is kept as a cheap statement of
    intent (*a join means two or more segments*) and carries NO mutation entry, because a clause
    whose removal changes no observable behaviour cannot have one — claiming otherwise would be the
    unfalsifiable-guard shape this repository files findings about.
    """
    parts: list[str] = []

    def walk(n: "ast.AST") -> None:
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div):
            walk(n.left)
            walk(n.right)
        elif isinstance(n, ast.Constant) and isinstance(n.value, str):
            parts.append(n.value)

    walk(node)
    return "/".join(parts) if len(parts) > 1 else None


def bound_docs_paths(text: str, python: bool) -> list[str]:
    """PURE. `docs/…` paths BOUND TO A NAME in `text` — assignments only, never comments.

    ⛔⛔ THE PREDICATE IS THE WHOLE DIFFICULTY, AND A GREP GETS IT WRONG — this is the failure
    `schema-gates.yml`'s header records against its own first version: *"it cannot tell a path the
    code OPENS from one a comment MENTIONS (13 of its 14 hits were prose)"*. MEASURED 2026-09-16 on
    this repository: a plain grep for the m4 spec directory hits `check-live-schema.py:29`,
    `check-storage-independence.py:96,132,471` and `check-review-recorded.py:155` — **five hits, all
    of them prose about the path**. This function returns none of them.

    For Python that is `ast` over ASSIGNMENT VALUES, the precedent being
    `check-storage-independence.py`, which parses with `ast` and derives its file set *because the
    grep it replaced survived 3 of 5 mutations*. ⚠ `ast` alone is NOT enough and the reason is
    subtle: a DOCSTRING is also an `ast.Constant`, so walking every string would re-admit
    `check-live-schema.py:29`, which is a docstring line. Restricting to `Assign`/`AnnAssign` values
    excludes docstrings structurally, because a docstring is an `ast.Expr`.

    For shell there is no `ast`, so it is a line scan restricted to `NAME=` lines with any `#`
    comment stripped first — enough for the two real cases (`SPEC=`, `SEED=`) and honest about being
    a scan rather than a parse.

    Pure, and given the TEXT rather than reading it, for the same reason as `readable_docs(docs,
    read)` and `first_codex_gap(docs, parse)` elsewhere in this file: so a case can drive it.
    """
    out: set[str] = set()
    if python:
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
                # ⟳ 2026-09-16, r1 High (codex): A `pathlib` JOIN CONTAINS NO `docs/…` LITERAL AT
                # ALL, so the per-constant scan below could not see it and the reviewer demonstrated
                # the miss: `ROOT / "docs" / "superpowers" / "specs" / "new-gate" / "rules.json"` is
                # five separate one-word strings. `_joined_path` reassembles a `/` chain so that
                # shape reads the same as the equivalent single literal. This is the ordinary way a
                # path is written in the Python gates, which is what made the gap load-bearing.
                joined = _joined_path(node.value)
                if joined and "docs/" in joined:
                    out.add(joined[joined.index("docs/"):])
                for sub in ast.walk(node.value):
                    if isinstance(sub, ast.Constant) and isinstance(sub.value, str) \
                            and "docs/" in sub.value:
                        out.add(sub.value[sub.value.index("docs/"):])
    else:
        for line in text.splitlines():
            line = line.split("#")[0]
            if not re.match(r"\s*[A-Za-z_]\w*=", line):
                continue
            out.update(re.findall(r"(docs/[\w./-]+)", line))
    return sorted(out)


def gate_code_dirs(runner: str, gate_sources: dict[str, str],
                   is_file: "Callable[[str], bool]") -> list[str]:
    """PURE. The `docs/` directories holding GATE MACHINERY, derived from the gates themselves.

    ⭐ WHY THIS REPLACED A READ OF `schema-gates.yml` — backlog #137, 2026-09-16. The previous
    version took the workflow's `docs/` path-filter globs as the authority for this question. That
    filter is GONE: it made the `schema-gates` check unrequireable, because a workflow-level
    `paths:` filter means the context never reports on a docs-only PR and a required check that
    never reports leaves a pull request pending forever.

    ⚠ AND THE OBVIOUS REPLACEMENT IS WRONG IN THE NOISY DIRECTION — MEASURED, not reasoned.
    *"Which `docs/` paths do the gate scripts bind?"* is NOT this question. Run that and it returns
    `docs`, `docs/adr`, `docs/reviews` and `docs/superpowers` as well, because `check-docs.py` binds
    `docs/backlog.md` and friends — so the gate would demand that the WHOLE documentation tree be
    added to `CODE_UNDER_PROSE`, i.e. that nothing under `docs/` is ever prose again. That is this
    file's own recorded lesson (*the lesson is the PREDICATE, not the list*) reproduced one level
    over, and it was caught by running the derivation before trusting it.

    The two prongs, each reading a property that is TRUE rather than a proxy for one:
      1. EXECUTED — a file the runner invokes as a gate out of a spec directory (`$SPEC/…`).
         Measured: the only mode-755 files tracked anywhere under `docs/` are exactly those two
         (`mutate-schema.py`, `verify-schema.sh`), so this prong has no false positives tree-wide.
      2. GATE DATA — a `docs/` path a gate binds that SHAPE accepts, is not `.md`, and EXISTS as
         a file. ⟳ r3 Low (codex): this said *"whose suffix is in `GATE_DATA_SUFFIXES`"*, and
         there is no such allow-list any more — r1's codex High retired it and r2's Medium 3
         deleted the extension-less rule that survived with it. A maintainer reading the stale
         sentence would think the deletion had not broadened the predicate. It has: an
         extension-less gate input now counts. This is
         what recovers `docs/superpowers/specs/m4/`, whose four files are mode 644 and therefore
         invisible to prong 1, while excluding every `.md` a gate merely reads as prose.

    ⚠ `is_file` IS INJECTED, and it is what makes prong 2 safe — ⟳ r1 High (codex). It answers *is
    this string a path at all*, which the suffix allow-list it replaced was answering by accident.
    Passed in rather than called directly so the rule stays pure and a case can drive it with a
    fixture, the same shape as `readable_docs(docs, read)` elsewhere in this file.

    ⚠ STATED LIMIT, NARROWED BUT NOT GONE: a gate that reads a `docs/` file through a path this
    cannot reconstruct — built in a loop, returned by a function, assembled with `os.path.join`,
    or `.format()`ted — is still invisible. `_joined_path` covers the `pathlib` `/` chain because
    that is how these gates actually write paths; the others are not currently used by any gate and
    would be a real miss if one adopted them. The failure is silent, which is the wrong direction,
    and it is the reason this rule is worth attacking again in a later round.
    """
    dirs: set[str] = set()
    # ⚠ The dot filter is inert today — r3 Low 8. The runner binds exactly one `docs/` path and it
    # has no dot, so nothing is ever excluded. ⚠ Its direction if it ever fired is NOISY (bogus
    # `$SPEC`-joined directories would be reported as uncovered, turning the gate red over
    # nothing), which is the safe direction for an unfalsified clause but is why it is recorded
    # rather than trusted.
    spec_dirs = [p for p in bound_docs_paths(runner, python=False)
                 if "." not in p.rsplit("/", 1)[-1]]
    for rel in re.findall(r"\$SPEC/([\w./-]+)", "\n".join(
            l.split("#")[0] for l in runner.splitlines())):
        for spec in spec_dirs:
            joined = f"{spec.rstrip('/')}/{rel}"
            dirs.add(joined.rsplit("/", 1)[0])
    for name, text in gate_sources.items():
        for p in bound_docs_paths(text, python=name.endswith(".py")):
            if is_gate_data(p, is_file):
                dirs.add(p.rsplit("/", 1)[0])
    return sorted(dirs)


def is_gate_data(path: str, is_file: "Callable[[str], bool]") -> bool:
    """PURE given `is_file`. Whether a bound `docs/` path is a gate INPUT rather than prose.

    ⛔ SPLIT OUT OF ONE `if` LINE — r1 BLOCKING 1 (claude), and the reason is mechanical rather than
    stylistic. Three manifest entries mutated three different clauses of a single line, so all three
    shared ONE ANCHOR. `check-plan-code.py:1019` keys its duplicate-anchor refusal on the `old` half
    alone, so it refused two of them and `--mutate .` then returned BEFORE STAGING ANYTHING —
    measured, `rc=1`, *"NOT MEASURED … Treat this as NOT CHECKED"*, with **zero of 719 mutations
    across every target executed**, inside the required `verify` job. The branch whose whole purpose
    is making a gate's answer consumable had turned the repository's largest gate off.
    ⚠ It got there because each mutation was verified INDIVIDUALLY and `--mutate .` was skipped
    locally: a collision is invisible one entry at a time, and visible only to the run that loads
    the whole manifest. One clause per line so each has its own anchor.

    ⚠ `"/" in p` was also dropped, not relocated — r1 Low 12 measured it TAUTOLOGICAL. Every path
    reaching here begins `docs/`, so it always contains a slash and no case could distinguish it.
    """
    if not looks_like_path(path):
        return False
    tail = path.rsplit("/", 1)[-1]
    suffix = tail[tail.rindex("."):] if "." in tail else ""
    # ⛔ THE "NO EXTENSION MEANS NOT GATE DATA" RULE IS GONE — r2 Medium 3 (claude). r1's codex High
    # retired a suffix ALLOW-LIST and this was described as closing it "as a CLASS"; a THIRD suffix
    # rule survived the split, deciding membership on the shape of a filename rather than on
    # anything true. Measured: it was unfalsified (deleting it left the suite green at 166/166) and
    # it hid a gate reading `docs/…/<new>/manifest`, a `Makefile` or a `Dockerfile` — the r1 finding
    # one convention over. `is_file` answers instead, and it is the better answer: a bound
    # DIRECTORY (`docs/reviews`, `docs/adr`) is not a FILE, so the shape the suffix rule was really
    # excluding is excluded by the property rather than by the name.
    # ⚠ Two separable lines, not one condition — so the PROSE rule and the (retired)
    # extension-less rule can carry distinct mutation anchors. Sharing one anchor is what made
    # `--mutate .` refuse the whole manifest in r1 Blocking 1, twice.
    is_prose_name = suffix == PROSE_SUFFIX
    if is_prose_name:
        return False
    return is_file(path)


def looks_like_path(path: str) -> bool:
    """PURE. Whether `path` can be a real path AT ALL, decided without touching the filesystem.

    ⛔⛔ THIS EXISTS BECAUSE `is_file` WAS BEING HANDED PROSE, AND WHETHER THAT CRASHES DEPENDS ON
    THE PYTHON VERSION — found 2026-09-16 by CI disagreeing with this machine on the same commit
    (`99f4da56`): locally `723 killed, 723 attributed`, in CI `722 attributed` with one mutation
    reported as *"went RED but printed no `[FAIL] <case>` line, so NOTHING COULD SEE THE KILL"*.
    A suite that CRASHES is unattributable, and this file's own note two functions down says it:
    *"A case must FAIL, not crash."*

    ⚠ THE CAUSE, MEASURED RATHER THAN GUESSED. A gate script's DOCSTRING that merely mentions a
    `docs/` path yields a multi-thousand-character blob, and six of them have path components up to
    **1450 bytes**. `Path.is_file()` raises `OSError` (ENAMETOOLONG) for those — except on Python
    3.13+, which widened the errno set it swallows. This machine runs 3.14 and returned False; the
    runner's older Python raised, and the raise happened while BUILDING the case list, before a
    single line was printed.
    ⚠ AND THE UNMUTATED CODE WAS SAFE ONLY BY LUCK: the longest component a real gate script binds
    today is **129 bytes**, 126 short of the limit. `check-sentinel-meanings.py` binds a multi-line
    prose message containing a path, so this is not a shape only a mutation can produce.

    So the question *is this a path* is answered by SHAPE first and the disk second.

    ⚠ WHICH CLAUSE ACTUALLY REJECTS THE MEASURED BLOB — r2 Low 8 (claude), because the first version
    of this docstring credited the wrong one. **The 1450-byte component contains WHITESPACE**, so
    the whitespace rule alone rejects it, and measured over the real corpus NO string has an
    over-255-byte component WITHOUT whitespace. Whitespace is the tell that a string is prose — no
    path in this repository contains any. The byte limits are PROSPECTIVE cover for a long
    no-whitespace path, not the thing that fixed the CI crash.
    ⚠ AND BOTH LIMITS ARE NEEDED — r2 Medium 4. An earlier version bounded the COMPONENT only while
    claiming *"no python version can crash it"*, which was false: `ENAMETOOLONG` is raised for
    `strlen(path) > PATH_MAX` as well, and the reviewer RAN 3.12 to show a 1200-byte path whose
    every component is 100 bytes still raising. ⚠ The supporting measurement was wrong in the same
    direction — *"the longest string reaching `is_file` is 38 bytes"* was the longest COMPONENT; the
    longest STRING is 77. Conflating the two is exactly what leaves the total unbounded.

    ⚠ ONE CLAUSE PER LINE, AND THAT IS r1's BLOCKING BEING OBEYED RATHER THAN RE-LEARNED. Written
    as a single `all(len(c.encode(...)) <= 255 ...)` expression, the byte-width mutation and the
    limit mutation share ONE ANCHOR — and `check-plan-code` then refuses the whole manifest and
    runs NOTHING. Caught here by the duplicate-anchor check before it could reach CI a second time.
    """
    if not path or any(c.isspace() for c in path):
        return False
    if len(path.encode("utf-8", "replace")) > PATH_LIMIT:
        return False
    for component in path.split("/"):
        width = len(component.encode("utf-8", "replace"))
        if width > COMPONENT_LIMIT:
            return False
    return True


def declared_not_derived(derived: list[str], declared: "tuple[str, ...]") -> list[str]:
    """PURE. Declared gate directories the derivation FAILED TO FIND — empty is correct.

    ⭐⭐ THE COMPLETENESS FALSIFIER, AND IT EXISTS BECAUSE NOTHING COULD SEE UNDER-COVERAGE —
    r1 HIGH 2 (claude), measured. The two live cases for the derivation were structurally blind to
    the failure that matters: one asserts the derived set is NON-EMPTY (prong 1 alone satisfies
    that), and the other asserts `prose_exceptions_cover` finds nothing uncovered — which
    under-coverage makes MORE likely to pass, not less. So the reviewer deleted `_gate_sources`'
    entire gate-script discovery loop, and **the suite stayed green at 153/153** while two of the
    three directories vanished, the result stayed non-empty so the CANNOT-RUN guard was satisfied,
    and the gate reported success.

    ⚠ THIS DOES NOT MAKE THE DERIVATION SOUND, AND SAYING SO IS THE POINT. Measured 2026-09-16, no
    predicate over a `docs/` directory can separate gate machinery from prose: accepting bound
    DIRECTORIES (the dominant shape in this repo) admits `docs/adr`, `docs/reviews` and
    `docs/superpowers`, and no content rule excludes them either, because `docs/superpowers`
    CONTAINS the gate directories. The old `paths:` filter worked only because a HUMAN curated it.
    So this asserts the PROPERTY instead of the mechanism — *the derivation finds at least what we
    already know* — which is falsifiable in the under-coverage direction without needing soundness.

    ⛔ WHAT IT STILL CANNOT SEE, stated rather than left implied: a BRAND-NEW `docs/` gate
    directory nobody has declared yet. `CODE_UNDER_PROSE` is the floor, not the ceiling, so this
    catches the derivation BREAKING and not the derivation being INCOMPLETE for a new subject.
    Filed with the measurements rather than hidden here.

    ⛔ A DERIVED CHILD IS NOT EVIDENCE OF ITS PARENT — r2 MEDIUM (codex), and the first version of
    this function accepted one. It matched a declared directory if ANY derived path was equal to it
    OR UNDER it, so `docs/…/stable-blob-addressing/schema` alone made
    `docs/…/stable-blob-addressing` count as found. Executed by the reviewer: with only the GATE
    DATA prong live, the EXECUTED prong could stop deriving the spec root entirely — losing both
    mode-755 gate executables — and this still returned `[]`. ⚠ WORSE, A SELF-TEST CASE BLESSED IT
    (*"a derived path UNDER a declared directory still counts as finding it"*), so the hole was
    pinned as intended behaviour rather than merely unnoticed. The match is now EXACT: each declared
    directory must itself be derived, and that case is inverted below.
    """
    # ⚠ The `rstrip` on the DERIVED side is inert — r3 Low 8. Derived directories come from
    # `rsplit("/", 1)[0]` and never carry a trailing slash. The DECLARED-side `rstrip` below IS
    # load-bearing (the reviewer confirmed by removing it: red via two cases), because
    # `CODE_UNDER_PROSE` writes its entries WITH one. Kept for symmetry, not for effect.
    stems = {x.rstrip("/") for x in derived}
    missing = []
    for d in declared:
        if d.rstrip("/") not in stems:
            missing.append(d)
    return missing


def antidrift_verdict(derived: list[str], declared: "tuple[str, ...]") -> "tuple[int, str]":
    """PURE. The anti-drift answer: `(0, "")`, or a non-zero code with the message to print.

    ⛔ EXTRACTED FROM `main` BECAUSE THE ORDER WAS UNFALSIFIABLE — r2 Medium 6 (claude). The three
    questions were asked inline, so no case could drive them and the manifest entry written to
    cover the ordering SURVIVED: setting `_undiscovered = []` in `main` changed nothing any case
    could see. A rule nobody can drive is documentation. This is the same rule/caller split the rest
    of the file uses.

    ⭐ THE ORDER IS THE CONTENT, and it is r1 High 2. Asking *"does the tuple cover the derivation?"*
    before *"did the derivation work?"* gets a PASS from a broken derivation, because a smaller
    derived set is easier to cover. Completeness must come first, and the cases below pin exactly
    that by constructing a state where BOTH would fire and asserting which one answers.
    """
    if not derived:
        # ⚠ A ZERO OVER NOTHING IS NOT A FINDING — the rule check-plan-file-tags records for an empty
        # corpus. Two of the fifteen gates have lived under `docs/` since 2026-08, so zero is never
        # the truth here; if the derivation found nothing, the derivation is what broke.
        return 2, ("CANNOT RUN — no `docs/` gate directories could be derived from the gate "
                   "scripts. Either\n  check-schema-gates.sh changed shape or the derivation is "
                   "broken; a zero here is not a pass. NOT CHECKED.")
    undiscovered = declared_not_derived(derived, declared)
    if undiscovered:
        return 2, ("CANNOT RUN — the derivation did not find "
                   f"{len(undiscovered)} directory(ies) already DECLARED as gate code:\n    "
                   + ", ".join(undiscovered)
                   + "\n  The gate scripts are the authority and they no longer yield these, so "
                     "the derivation is broken\n  or a gate stopped reading its own subject. A "
                     "smaller answer here is not a cleaner repo.\n  NOT CHECKED.")
    uncovered = prose_exceptions_cover(derived, declared)
    if uncovered:
        return 1, (f"FAILED — the schema gates treat {len(uncovered)} `docs/` director(ies) as "
                   f"gate machinery that this gate still classifies as PROSE:\n    "
                   f"{', '.join(uncovered)}\n  Add them to CODE_UNDER_PROSE in "
                   f"scripts/check-review-recorded.py, or a branch changing that gate code\n  "
                   f"owes no review round and skips the final-tree question — measured twice on this branch.")
    return 0, ""


def _gate_sources() -> "tuple[str, dict[str, str]] | None":
    """IMPURE. The gate runner's text, plus the text of every gate script it invokes.

    `check-schema-gates.sh` is the single authority for what a gate IS — its own header says so
    (*"One entry point, and it is what the hook and the docs both name"*), so the script list is
    derived from it rather than kept as a second copy here.
    """
    runner_path = ROOT / "scripts" / "check-schema-gates.sh"
    if not runner_path.is_file():
        return None
    runner = runner_path.read_text(encoding="utf-8", errors="replace")
    uncommented = "\n".join(l.split("#")[0] for l in runner.splitlines())
    sources: dict[str, str] = {"scripts/check-schema-gates.sh": runner}
    for rel in sorted(set(re.findall(r"(?:\./)?(scripts/[\w.-]+\.(?:py|sh))", uncommented))):
        p = ROOT / rel
        if p.is_file():
            sources[rel] = p.read_text(encoding="utf-8", errors="replace")
    return runner, sources


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
    #   ⛔ **`is not True`, NOT TRUTHINESS — backlog #176, r3 Claude half, H2.** This read
    #   `if not rec.get("gate_ran")`, so `"false"`, `"no"`, `"0"` and `1` — every truthy non-bool —
    #   returned `(head, USABLE)`, CREDITING A GATE THAT DID NOT RUN WITH HAVING SEEN THE FINAL
    #   TREE. Measured by driving this function: `True`/`False` classified correctly, all four of
    #   those read as usable. That is the fail-open this function's own docstring says was worth
    #   extracting it for. The sibling `check-review-rounds` removed the identical idiom in round
    #   2, from `refused` at two sites and from `gate_ran` at one; this is the fourth and last
    #   site of that one rule, and the only one outside that file — in the other consumer of the
    #   same records. The two scripts already share a grammar (`_load_gap_line_parser` below
    #   imports `has_gap_line`), so the seam exists and this rule is the one not on it. ⚠ The mitigation that a non-bool `gate_ran` makes `check-review-rounds`
    #   exit 2 anyway is an UNDECLARED CROSS-FILE INVARIANT — that script is not PR-only while this
    #   one is (`ci.yml`) — and is not relied on here.
    #   ⚠ SKIP, not UNUSABLE, deliberately: an unreadable field is not testimony that a round saw
    #   the tree, and with no usable round `tail_verdict` returns CANNOT RUN (2), never a pass, so
    #   skipping does not reopen the hole in the aggregate.
    #   ⤳ **AND THIS IS A PATCH OF A CLASS, NOT THE END OF IT.** The review that found
    #   it (`docs/reviews/claude/review-identity-176-r3-claude.md`) answers that the set closes in
    #   ONE move — a validating reader in `check-review-rounds.read_verdicts` that states the type
    #   of every field, which this file would import the way it already imports `has_gap_line`.
    #   That is a seam change with no design and is filed as its own backlog row.
    if rec.get("gate_ran") is not True:
        return None, SKIP
    head = rec.get("head")
    if not isinstance(head, str) or not head.strip():
        return None, UNUSABLE           # schema 1: no commit recorded at all
    # ⛔ **ANY NON-`dict`, NOT JUST `None` — r3 Claude half, H2, AND THIS ONE IS REACHABLE ON
    # DISK.** `rec["dirty"] is None` let `"oops"`, `[]` and `42` through as USABLE while
    # `reviewed_map` below independently returns `{}` for them — a real head with an empty overlay,
    # which is byte-identical to a round dispatched against a clean tree and is exactly the vacuous
    # comparison r11 Medium closed for the `{}`-vs-`None` pair. Unlike every other shape this slice
    # has closed, this one is NOT hypothetical: derived over the committed verdict corpus,
    # `docs/reviews/verdicts/record-review-topology-r1-codex.verdict.json` carries `"dirty": []`
    # with `gate_ran: true` — a schema-2 record from before the producer wrote `dict(dirty)`. It is
    # not in this branch's added set, so nothing changes for this run; it is what makes the class
    # a fact rather than an argument. `isinstance` is also the same question `reviewed_map` asks,
    # so the two ends now agree instead of one passing what the other empties.
    if "dirty" in rec and not isinstance(rec["dirty"], dict):
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
    # ⛔ AN EMPTY DECLARATION IS NOT A DECLARATION, AND THIS ARM USED TO DISAGREE WITH `verdict()`
    # ABOUT THAT — r15 Medium, measured end to end. `verdict` refuses a bare `NO-REVIEW:` with no
    # reason (`"was declared with no reason after it"`, pinned by a case AND a mutation); this arm
    # tested `waiver is not None`, and `reason_of` returns `''` — not `None` — for a bare marker.
    # The two rules only ever met when a review document was ALSO added, because then `verdict`
    # returns 0 at its review-document branch and never reaches its own refusal. So the empty
    # declaration was rejected nowhere, and it turned the final-tree gate from CANNOT RUN into a
    # pass: measured `rc=2` -> `rc=0`, with a log line reading `NO-REVIEW:  — the final-tree
    # question is WAIVED` where only a double space betrays it.
    #
    # An author who writes `NO-REVIEW:` with the reason on the NEXT line, or leaves a PR-template
    # stub, is the likely case — not an evasion. One marker, one meaning, in both questions.
    if waiver is not None and waiver.strip():
        return False, f"{NO_REVIEW} {waiver} — the final-tree question is WAIVED, not passed"
    return True, None


def round_tail(after: list[str], reviewed: dict[str, str], final: dict[str, str],
               master: "MasterSide" = None) -> list[str]:
    """PURE. The guarded paths one round cannot have seen.

    `after`    — paths changed between that round's commit and HEAD
    `reviewed` — path -> `"<mode> <object-id>"` the reviewer was handed UNCOMMITTED
    `final`    — path -> `"<mode> <object-id>"` in the tree that will merge
    `master`   — the round's commit merged with master, for `master_explains` (backlog #426);
                 `None` (no merge built) leaves the strict rule

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
            return master_explains(p, master, now)
        return (is_absent(seen) and is_absent(now)) or now == seen

    missed = [p for p in guarded_changes(after) if not same(p)]
    return sorted(set(missed))


def master_explains(p: str, master: "MasterSide", now: str) -> bool:
    """PURE. Is HEAD's entry for `p` exactly what the reviewed commit plus master's changes give?

    `master` is `(entries, conflicted)` from `merge-tree(<round's commit>, merge-base(base, HEAD))`
    — the reviewed tree with master's changes since added and nothing else (backlog #426). Equal
    means everything in `p` after the round came from master or from a clean textual merge of the
    two. ⚠ STATED BOUND: when both touched `p`, the COMPOSITION was reviewed by nobody (master's
    reviewer never saw the branch's hunk, the round never saw master's) — the same semantic waiver
    `tail_candidates` states across files, here within one file.

    ⛔ EVERY UNKNOWN IS "NOT EXPLAINED", i.e. a round stays required: no merge could be built
    (`None`), or the merge CONFLICTED on `p` — the resolution is the branch's own code even when it
    happens to equal what the synthesised tree holds (a modify/delete conflict keeps the modified
    side, so equality there would credit the author's choice to keep it).

    ⛔ AND ABSENT NEVER EXPLAINS — merge-delta r4, from the thrashing architecture review. "Both
    absent" is unreachable for an honest lookup: `p` is here only if it changed since the round
    (so the round's commit or HEAD holds it) and is in the branch delta (so `onto` differs from
    HEAD); if HEAD lacks `p`, both merge sides hold it, and a clean merge of two sides that both
    hold a path cannot drop it. So absent == absent only ever came from a lookup that LIED — r1's
    failed `ls-tree`, r3's pathspec miss — and each read as a clear. Now any such lie charges.
    """
    if master is None:
        return False
    entries, conflicted = master
    if p in conflicted:
        return False
    want = entries.get(p, ABSENT_ENTRY)
    return not is_absent(now) and now == want


def parse_merge_tree(out: str, rc: int) -> "tuple[str, frozenset[str]] | None":
    """PURE. `git merge-tree --write-tree --name-only --no-messages -z` -> `(tree, conflicted)`.

    rc 0 is a clean merge, rc 1 a conflicted one (the tree still exists, with markers in it);
    anything else means the merge was NOT computed, and that is `None` — never an empty conflict
    set, which would read as "clean".
    """
    if rc not in (0, 1):
        return None
    tree, *rest = out.split("\0")
    if not tree.strip():
        return None
    return tree.strip(), frozenset(p for p in rest if p)


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
               if unusable else "no review verdict was added by this branch")
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
                   f"  Treat this as NOT CHECKED, never as reviewed. Either record a round against "
                   f"the current tree (codex-review.py, or record-review-verdict.py for a Claude "
                   f"half),\n"
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


def git_text(raw: bytes) -> str:
    """PURE. Git's output bytes -> str, with every byte kept: a CR stays a CR, a non-UTF-8 byte
    becomes the same lone surrogate in every reader, so two listings compare byte for byte."""
    return raw.decode("utf-8", "surrogateescape")


def _run_git(argv: list[str], **kw) -> subprocess.CompletedProcess:
    """Run git and capture BYTES, decoded by `git_text`. EVERY git read in this file goes here.

    ⛔ NEVER `text=True` — merge-delta r4 Codex BLOCKER, measured end to end. Text mode applies
    universal newlines, so `lib/a\\r.py` came back as `lib/a\\n.py`; in a whole-tree listing the
    unchanged CR-named entry then OVERWROTE the edited LF-named one under the same key, HEAD and the
    synthetic merge agreed on the wrong entry, and the full CLI said `ok`, rc 0. `encoding=` and
    `errors=` do not turn that translation off; only bytes do. Strict decoding was the second half
    of the class (r4 Codex M2): `changed_paths`/`added_paths` raised on a `0xe9` path name.
    """
    p = subprocess.run(argv, capture_output=True, **kw)
    return subprocess.CompletedProcess(p.args, p.returncode, git_text(p.stdout), git_text(p.stderr))


def _git(*args: str) -> subprocess.CompletedProcess:
    return _run_git(["git", "-C", str(ROOT), *args])


def _final_entries(paths: list[str], git=None) -> dict[str, str]:
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

    ⛔ A FAILED LOOKUP RAISES — merge-delta r1 Codex High. It returned `{}`, i.e. "every path is
    absent from HEAD", and since backlog #426 an absent path EQUALS a deletion master made: the
    reviewer injected a failure into this one call and a branch's unreviewed re-add of a file
    master deleted was cleared, rc 0. An unknown HEAD is CANNOT RUN, never an empty tree.
    """
    git = git or _git
    if not paths:
        return {}
    got = git(*ls_tree_argv("HEAD"))
    if got.returncode != 0:
        raise RuntimeError(f"CANNOT RUN — git ls-tree HEAD failed ({got.stderr.strip()}), so "
                           f"what is about to merge is UNKNOWN. Treat this as NOT CHECKED.")
    return select_entries(parse_ls_tree(got.stdout), paths)


def ls_tree_argv(tree: str) -> list[str]:
    """PURE. List the WHOLE tree, NUL-separated, with no path argument at all.

    ⛔ merge-delta r3 Claude M1. Both lookups passed the changed paths after `--`, and git reads
    that as a PATHSPEC: `:/evil.sh`, `:(top)evil.sh` and `:(literal)x/evil.sh` were looked up
    under ANOTHER name, missing from HEAD and from the merge alike, and absent == absent CLEARED an
    unreviewed file. A decomposed-Unicode name did the same under `core.precomposeunicode=true`
    (the macOS default), because git precomposes its argv and not a tree's names. With no path in
    the argv there is nothing for git to reinterpret; `select_entries` matches exact names.
    `-r -t` lists every leaf AND the trees on the way, so a path that is a directory in the tree
    still has an entry, as the pathspec form gave it. The `-c` is a belt: nothing here is argv.
    """
    return ["-c", "core.precomposeunicode=false",
            "ls-tree", "-r", "-t", "-z", "--full-tree", tree]


def select_entries(listing: dict[str, str], paths: list[str]) -> dict[str, str]:
    """PURE. The entries of `listing` whose name is EXACTLY one of `paths` — no pattern, no magic."""
    return {p: listing[p] for p in paths if p in listing}


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


def merge_onto(base: str, git=None) -> "str | None":
    """`merge-base(base, HEAD)` — the master commit HEAD already contains — or `None`.

    ⛔ ONE HELPER FOR `main` AND THE REAL-GIT FIXTURE — merge-delta r1 Claude M2. The fixture
    recomputed this itself, so `main`'s copy was never run by any case: `rev-parse HEAD` in its
    place left 217/217 green, and `merge-tree(round, HEAD)` is HEAD's own tree, which clears EVERY
    post-review commit. Both now call this, so the fixture's red is `main`'s red.
    """
    git = git or _git
    mb = git("merge-base", base, "HEAD")
    return mb.stdout.strip() if mb.returncode == 0 else None


def merge_tree_argv(empty_tree: str, head: str, onto: str) -> list[str]:
    """PURE. The `merge-tree` call. It runs ONLY inside `isolated_env` — see `_isolated_git`.

    `--attr-source=<empty tree>` stays even there: a bare repository reads `HEAD:.gitattributes`,
    and the flag says "no tree attributes" whatever HEAD becomes. Git older than 2.42 does not know
    it and exits 129, which `parse_merge_tree` reads as `None`, the strict rule.
    """
    return [f"--attr-source={empty_tree}",
            "merge-tree", "--write-tree", "--name-only", "--no-messages", "-z", head, onto]


def isolated_env(git_dir: str, home: str, path: "str | None") -> dict[str, str]:
    """PURE. The WHOLE environment of the synthetic merge — built, never filtered from `os.environ`.

    ⛔ merge-delta r1 Claude M1, r2 Codex M1 + M2: a merge driver reached `merge-tree` from the
    branch's `.gitattributes`, then from `info/attributes`, then from a configured
    `merge.text.driver` (repository config, an include, `GIT_CONFIG_COUNT`) and the SYSTEM
    `gitattributes` — one more source per round, each closed by one more `-c`. The class is "git
    reads configuration and attributes the branch, the host or the caller can set", so the merge
    runs in a repository with NONE of its own: an empty `GIT_DIR` (see `_isolated_git`), no
    inherited variable at all (`GIT_CONFIG_COUNT`, `GIT_CONFIG_PARAMETERS`, `XDG_CONFIG_HOME`, ...),
    no system or global config, no system attributes, and a `HOME` with nothing in it.
    """
    env = {"GIT_DIR": git_dir, "HOME": home, "GIT_CONFIG_NOSYSTEM": "1",
           "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_ATTR_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"}
    if path:
        env["PATH"] = path
    return env


@contextlib.contextmanager
def _isolated_git(git):
    """Yield a `git` runner over an EMPTY repository that borrows the real one's objects, or `None`.

    The temp `GIT_DIR` has no config, no attributes, no hooks (`--template=`) and NO REFS, and its
    `objects/info/alternates` names the real object store, so every commit and blob is readable and
    nothing else is. `merge-tree --write-tree` writes its result into the temp store, which is
    deleted on exit. ⚠ NO REFS MEANS NO REPLACE REFS AND NO GRAFTS: the merge is of the objects the
    SHAs name, not of what `refs/replace/` substitutes — measured in the self-test. Any failure to
    build it (no temp dir, no common dir, init refused) is `None`, which `_master_side` reads as the
    strict rule.
    """
    common = git("rev-parse", "--path-format=absolute", "--git-common-dir")
    objects = pathlib.Path(common.stdout.strip(), "objects") if common.returncode == 0 else None
    # ⚠ The empty-answer and `is_dir` checks, and `init`'s rc below, are SECOND LOCKS, not mutation
    # targets: without them the alternates name nothing (or no repository exists), the merge cannot
    # find the round's commit, and `parse_merge_tree` reads the failure as `None` — measured.
    if objects is None or not common.stdout.strip() or not objects.is_dir():
        yield None
        return
    try:
        tmp = tempfile.mkdtemp(prefix="crr-merge-")
    except OSError:
        yield None
        return
    # ⛔ THE `finally` OPENS RIGHT AFTER `mkdtemp` — merge-delta r3 Claude L1. The setup used to sit
    # before it, so any exception but `OSError` (a missing `git` under a mutant, an interrupt)
    # left `crr-merge-*/home` behind in `$TMPDIR`; the mutation sweep leaked one per run.
    try:
        ok = False
        try:
            git_dir, home = os.path.join(tmp, "repo.git"), os.path.join(tmp, "home")
            os.mkdir(home)
            env = isolated_env(git_dir, home, os.environ.get("PATH"))

            def run(*args: str) -> subprocess.CompletedProcess:
                return _run_git(["git", *args], cwd=tmp, env=env)

            ok = run("init", "-q", "--bare", "--template=", git_dir).returncode == 0
            if ok:
                info = pathlib.Path(git_dir, "objects", "info")
                info.mkdir(parents=True, exist_ok=True)
                (info / "alternates").write_text(f"{objects}\n", encoding="utf-8")
        except OSError:
            ok = False
        yield run if ok else None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _master_side(head: str, onto: "str | None", paths: list[str],
                 git=None, isolate=None) -> "tuple[dict[str, str], frozenset[str]] | None":
    """`(entries, conflicted)` of the round's commit merged with `onto`; `None` on ANY failure.

    `None` is the strict rule, so a merge that cannot be built leaves a round required (backlog
    #426, the fail direction). `git` (the real repository) and `isolate` (the isolated runner's
    factory, `_isolated_git`) are injectable so a case can drive it over a real fixture repository
    and inject a failure into either. The merge and the `ls-tree` of its result run ISOLATED — see
    `isolated_env`; the real repository is only asked where its objects are.
    """
    git = git or _git
    isolate = isolate or _isolated_git
    if not onto or not paths:
        return None
    with isolate(git) as iso:
        if iso is None:
            return None
        empty = iso("hash-object", "-t", "tree", "/dev/null")
        if empty.returncode != 0 or not empty.stdout.strip():
            return None
        mt = iso(*merge_tree_argv(empty.stdout.strip(), head, onto))
        parsed = parse_merge_tree(mt.stdout, mt.returncode)
        if parsed is None:
            return None
        tree, conflicted = parsed
        ls = iso(*ls_tree_argv(tree))
        if ls.returncode != 0:
            return None
        return select_entries(parse_ls_tree(ls.stdout), paths), conflicted


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
    # ⛔ THE SAME ARGV AS THE OTHER TWO QUESTIONS, BUILT IN ONE PLACE — r14 exhaustiveness pass.
    # This function already had `--no-renames` and the other two did not, and that DISAGREEMENT was
    # the fail-open: `tail_candidates` intersects this list with `changed_paths`', so a renamed path
    # present in one and absent from the other was silently dropped. Fixing both to agree left the
    # agreement as a CONVENTION — three call sites that happen to match. Now there is one builder,
    # so they cannot drift apart again, and the cases on `diff_argv` cover all three.
    diff = _git(*diff_argv(head))
    if diff.returncode != 0:
        raise RuntimeError(f"CANNOT RUN — git diff against {head[:12]} failed: "
                           f"{diff.stderr.strip()}")
    return [ln for ln in diff.stdout.split("\0") if ln]


def round_tails(verdict_files: list[str], branch_delta: list[str], *,
                load=None, is_ancestor=None, changed_since=None,
                final_entries=None, onto: "str | None" = None,
                master_side=None) -> tuple[dict[str, list[str]], int]:
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
    so scoping the candidate set costs no extra git call. `onto` is `merge-base(base, HEAD)` — the
    master commit HEAD already contains — and `master_side` builds what the round's commit becomes
    when merged with it (backlog #426); `onto=None` means it could not be resolved, so no round is
    cleared by it.
    """
    load = load or _load_verdict
    is_ancestor = is_ancestor or _is_ancestor
    changed_since = changed_since or _changed_since
    final_entries = final_entries or _final_entries
    master_side = master_side or _master_side
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
        guarded = guarded_changes(cands)
        tails[pathlib.PurePosixPath(rel).name] = round_tail(
            cands, reviewed, final_entries(guarded), master_side(head, onto, guarded))
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
    shallow = _git("rev-parse", "--is-shallow-repository")
    if shallow.stdout.strip() == "true":
        raise RuntimeError("CANNOT RUN — shallow clone; the diff would be confidently short.")
    merge_base = _git("merge-base", base, "HEAD")
    if merge_base.returncode != 0:
        raise RuntimeError(f"CANNOT RUN — cannot resolve a merge base with {base!r}: "
                           f"{merge_base.stderr.strip()}")
    diff = _git(*diff_argv(merge_base.stdout.strip()))
    if diff.returncode != 0:
        raise RuntimeError(f"CANNOT RUN — git diff failed: {diff.stderr.strip()}")
    return split_nul(diff.stdout)


def split_nul(out: str) -> list[str]:
    """PURE. `git … -z` output -> paths. The falsifier for the `-z` repair above."""
    return [ln for ln in out.split("\0") if ln.strip()]


def diff_argv(base_sha: str, *, added_only: bool = False) -> list[str]:
    """PURE. The `git diff` argv BOTH branch-scoped questions use, so they cannot disagree.

    ⛔ `--no-renames` IS A FAIL-OPEN FIX, NOT TIDINESS — r14 High, measured end to end with a control.
    Git's rename detection is ON by default (`diff.renames` unset -> true), and `--name-only` then
    prints ONLY the destination of a rename. So moving a guarded file to a prose path — `lib/x.ts`
    into `docs/` — deleted a code file from the tree while this gate reported:

        ok — no guarded path changed — a review round is not required          rc=0

    No review document, no `NO-REVIEW:` declaration, exit 0. That is the exact outcome the
    WHY THIS EXISTS section at the top of this file was written against.

    ⛔ AND IT DEFEATED THE SECOND QUESTION TOO, which is worse because that half is new here.
    `tail_candidates` intersects `after` with `branch_delta`. `after` comes from `_changed_since`,
    which passes `--no-renames` and therefore DOES contain the renamed-away path; `branch_delta`
    came from `changed_paths`, which did not. The intersection silently dropped the path and the
    round was credited with having seen a file it never could have.

    ⚠ THE SAME TWO LINES WERE EDITED ONE ROUND EARLIER, FOR THE SAME CLASS OF DEFECT. r11 added `-z`
    to both because a C-quoted path stopped being the path, and its docstring says the sibling was
    *"fixed there as an INSTANCE, not searched for as a class, which is this project's own recorded
    failure shape."* `--no-renames` is one flag over, in the same three functions, and the function
    written in that same round has it. Thirteen rounds attacked the mutation harness and none asked
    whether this gate's own `git diff` is the diff it reasons about.

    ⚠ IT ALSO CAUSED A FALSE FAIL in the other direction (r14 Medium): with `--diff-filter=A`, a
    review document MOVED into `docs/reviews/` is classified `R` and never reaches `review_added` —
    so a branch performing the `docs/reviews/<writer>/` relocation this project actually mandates was
    told no review round was recorded. A gate that fires on a branch doing the right thing is how
    backlog #56 measured gates getting switched off. One flag closes both directions.

    The policy now matches the producer: `codex-review.py` already passes `--no-renames` on its
    `diff-index`, so this is agreement rather than an invented rule.
    """
    args = ["diff", "--name-only", "-z", "--no-renames"]
    if added_only:
        args.append("--diff-filter=A")
    return args + [base_sha, "HEAD"]


def added_paths(base: str) -> list[str]:
    """Paths ADDED against `base` (status A). RAISES like `changed_paths`; shares `diff_argv`."""
    mb = _git("merge-base", base, "HEAD")
    if mb.returncode != 0:
        raise RuntimeError(f"CANNOT RUN — cannot resolve a merge base with {base!r}")
    out = _git(*diff_argv(mb.stdout.strip(), added_only=True))
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
        # ⛔ INSIDE ITS OWN CANNOT-RUN, and it was OUTSIDE the one below — r15 Low. A missing
        # `--pr-body-file` raised `FileNotFoundError` straight out of `main`: rc=1 with a traceback,
        # where the docstring's FAILS IF list promises exit 2. That is exactly the r1 Major recorded
        # twelve lines down — *"'Cannot run' collapsing into an ordinary failure is the exact shape
        # this repo refuses"* — fixed there for the git calls and not searched for as a class, one
        # statement short. Not reachable from CI (the workflow `printf`s the file in the same step),
        # and it failed loud rather than open, which is why it is Low and not higher.
        try:
            body = pathlib.Path(args.pr_body_file).read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            print(f"CANNOT RUN — the PR body file {args.pr_body_file!r} could not be read ({exc}), "
                  f"so a `{NO_REVIEW}` declaration in it cannot be seen. Treat this as NOT CHECKED.",
                  file=sys.stderr)
            return 2

    # ⚠ THE DOCSTRING PROMISES EXIT 2, and the first version raised `RuntimeError` straight out of
    # `main` — rc=1 with a traceback (r1 review, Major). "Cannot run" collapsing into an ordinary
    # failure is the exact shape this repo refuses: a gate that could not reach its subject must
    # say so in its own exit code, not look like a finding.
    # ⛔ THE ANTI-DRIFT CHECK, WITH A CALLER — r16 High. `prose_exceptions_cover` existed and was
    # returned to nobody; a rule whose result no one reads is not a gate. It is asked HERE, against
    # the real workflow, before either question, because a classifier that disagrees with what CI
    # treats as gate code cannot answer either question correctly.
    _gs = _gate_sources()
    if _gs is None:
        print("CANNOT RUN — scripts/check-schema-gates.sh is missing, so the `docs/` directories "
              "holding gate machinery cannot be compared against CODE_UNDER_PROSE. NOT CHECKED.",
              file=sys.stderr)
        return 2
    # ⛔ THE BOUNDARY CANNOT RAISE — r3 Medium 5b (claude). `looks_like_path` bounds `rel`, but the
    # OS receives `ROOT/rel`, which is `len(str(ROOT)) + 1` bytes longer than the string the pure
    # rule measured; the reviewer executed a path the shape guard ACCEPTS and showed the real
    # `is_file` still raising on 3.12. The shape guard stays as a cheap pre-filter with its bounds
    # pinned, but correctness lives HERE: an unstattable string is not a gate file, and saying so
    # is not "cannot run reporting success" — we are rejecting a non-path, not failing to read a
    # known one.
    def _is_file(rel: str) -> bool:
        try:
            return (ROOT / rel).is_file()
        except (OSError, ValueError):
            return False

    _dirs = gate_code_dirs(*_gs, is_file=_is_file)
    _rc, _msg = antidrift_verdict(_dirs, CODE_UNDER_PROSE)
    if _rc:
        print(_msg, file=sys.stderr)
        return _rc
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
        # ⛔ an unresolvable merge base is `None`, which clears nothing — backlog #426's fail
        # direction. `changed_paths` above has already refused that case; this is the second lock.
        tails, unusable = round_tails(branch_verdicts(added), changed,
                                      onto=merge_onto(args.base))
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
    """The suite, inside `fixture_git.isolated()`: every `--self-test` runs isolated (backlog #382)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    cases: list[tuple[str, object, object]] = []

    def case(name: str, got, want) -> None:
        cases.append((name, got, want))

    none_reason = lambda _b: None
    # reads the marker out of the body it is GIVEN, so `pr_body` reaching `reason_of` is
    # observable — the point of r4 Low 1.
    _declared_reason = lambda b: (b.split("NO-REVIEW:", 1)[1].strip()
                                  if "NO-REVIEW:" in b else None)
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
    # ⛔ r3 LOW 6 — r2's Low 7 was REPORTED FIXED AND WAS NOT, and the two prose branches mutually
    # mask: each survives alone and only dies together, because every `.md` member of PROSE_FILES is
    # also caught by the root-`.md` fallback. `.gitignore` is the ONLY member that is not, so it is
    # the one input that separates them.
    case(".gitignore is prose — the only PROSE_FILES member the root-.md fallback cannot catch",
         guarded_changes([".gitignore"]), [])
    # ⛔ r4 LOW 4 — THE OTHER HALF OF THE MUTUAL MASK, and this lineage is now three rounds long
    # (r2 Low 7 -> r3 Low 6 -> here). `.gitignore` falsifies the PROSE_FILES branch; nothing
    # falsified the root-`.md` FALLBACK, because every `.md` reaching it was also a PROSE_FILES
    # member. A root `.md` that is NOT named in the tuple is the input that separates them.
    case("a root .md NOT named in PROSE_FILES is still prose, via the fallback",
         guarded_changes(["NOTES.md"]), [])
    # ⛔ r4 LOW 1 — `verdict.pr_body` was the SAME "constant wearing a signature" shape this branch
    # closed for `prose_exceptions_cover.declared`, still live in the same file: all eight call
    # sites passed `""`, so `reason_of(pr_body)` -> `reason_of("")` survived. Closing one instance
    # and leaving the file's only other one is instance-not-class.
    case("the pr_body is a real PARAMETER: a NO-REVIEW marker in it waives the round",
         verdict(CODE, [], "NO-REVIEW: infrastructure only", _declared_reason)[0], 0)
    case("...while the same branch with an EMPTY body does not",
         verdict(CODE, [], "", _declared_reason)[0], 1)
    # ⚠ a Markdown file INSIDE a package is not automatically prose — only a root one is
    case("a .md inside a package is still guarded",
         guarded_changes(["lib/README.md"]), ["lib/README.md"])
    # ⛔ r15 HIGH, as cases. `docs/` holds TWO OF THE FIFTEEN SCHEMA GATES, both mode 755, both
    # executed by `check-schema-gates.sh` (whose path filters are gone — #137) — and
    # every one of these was classified PROSE, so a branch changing them owed no round AND skipped
    # the final-tree question. Seventeen `is_prose` cases existed and not one reached inside `docs/`.
    _SPEC = "docs/superpowers/specs/2026-08-03-stable-blob-addressing/"
    for _p in (_SPEC + "mutate-schema.py", _SPEC + "verify-schema.sh",
               "docs/superpowers/specs/m4/live-manifest.txt",
               "docs/superpowers/specs/m4/t1-blast-radius.sql",
               "docs/superpowers/specs/m4/accepted-additions.txt"):
        case(f"gate code at {_p.split('/')[-1]} is GUARDED, though it lives under docs/",
             guarded_changes([_p]), [_p])
    # ⚠ HYPOTHETICAL PATH, SAID SO IN THE NAME — r16 Medium. No `.md` is tracked under either
    # exempted directory today; this pins the policy for the first one, not an existing file.
    case("...and a hypothetical .md beside them would still be prose (none exists there today)",
         guarded_changes([_SPEC + "spec.md"]), [])
    case("...while ordinary docs are untouched by the exception",
         guarded_changes(["docs/superpowers/specs/other/notes.md"]), [])
    # ⛔ AND THE EXCEPTION MUST COVER WHAT THE GATES GUARD. ⚠ THE DIRECTORIES ARE DERIVED FROM THE
    # REAL GATE SCRIPTS, not transcribed here — r16 High, preserved through #137's change of
    # authority. The pre-r16 version typed the list into the case, so the check compared a copy
    # against a copy and a new gate directory was invisible: measured, suite green at 134/134 while
    # the new gate's code classified as prose.
    _GS = _gate_sources()
    _real_file = lambda rel: (ROOT / rel).is_file()
    _all_exist = lambda rel: True      # fixture: every derived path is a real file
    case("the docs/ gate directories are DERIVED from the real gate scripts, not transcribed here",
         bool(_GS) and gate_code_dirs(*_GS, is_file=_real_file) != [], True)
    case("...and every one of them is exempt from the prose classifier",
         prose_exceptions_cover(gate_code_dirs(*_GS, is_file=_real_file), CODE_UNDER_PROSE) if _GS else [], [])
    # ⭐⭐ THE CASE r1 HIGH 2 SAID DID NOT EXIST, AND IT IS THE ONE THAT CAN FAIL. Both cases above
    # are blind to UNDER-coverage: the first is satisfied by prong 1 alone, and the second gets
    # EASIER to pass as the derived set shrinks. Deleting `_gate_sources`' discovery loop left the
    # suite green at 153/153 while two of three directories vanished. This one goes red for it.
    case("...and the derivation FINDS every directory already declared as gate code",
         declared_not_derived(gate_code_dirs(*_GS, is_file=_real_file), CODE_UNDER_PROSE)
         if _GS else [], [])
    # ⭐⭐ r2 MEDIUM 6 — THE ORDER, DRIVEN. A state where BOTH questions would fire: the derivation
    # lost a DECLARED directory (completeness) AND what it did derive is uncovered (coverage).
    # Completeness must answer, because a broken derivation is easier to "cover".
    _both = ["docs/superpowers/specs/m5-newgate"]
    case("when BOTH would fire, COMPLETENESS answers — a broken derivation is not a coverage pass",
         antidrift_verdict(_both, CODE_UNDER_PROSE)[0], 2)
    case("...and it says CANNOT RUN, not FAILED, because nothing was actually checked",
         "CANNOT RUN" in antidrift_verdict(_both, CODE_UNDER_PROSE)[1], True)
    case("...while an uncovered directory with completeness INTACT is a FAILED, code 1",
         antidrift_verdict(["docs/superpowers/specs/2026-08-03-stable-blob-addressing",
                            "docs/superpowers/specs/m4", "docs/newgate"], CODE_UNDER_PROSE)[0], 1)
    case("an empty derivation is CANNOT RUN before either question is asked",
         antidrift_verdict([], CODE_UNDER_PROSE)[0], 2)
    # ⛔ r3 MEDIUM 2 — THE CASE ABOVE CANNOT SEE ITS OWN CLAUSE. Delete `if not derived:` and it
    # still passes, because the COMPLETENESS prong returns the same code by another route. This one
    # empties the declaration too, so only the guard can answer: with it, 2; without it, 0 — a gate
    # reporting a pass over a derivation that found nothing.
    case("...and it refuses even with NOTHING declared, so it is not standing on the other prong",
         antidrift_verdict([], ())[0], 2)
    case("...and the healthy real derivation answers 0 with nothing to say",
         antidrift_verdict(["docs/superpowers/specs/2026-08-03-stable-blob-addressing",
                            "docs/superpowers/specs/m4"], CODE_UNDER_PROSE), (0, ""))
    case("a declared directory the derivation missed is REPORTED, which main treats as CANNOT RUN",
         declared_not_derived(["docs/superpowers/specs/m4"], CODE_UNDER_PROSE),
         ["docs/superpowers/specs/2026-08-03-stable-blob-addressing/"])
    # ⛔ INVERTED — r2 Medium (codex). This case used to assert a derived CHILD counted as finding
    # its declared parent, which pinned the hole as INTENDED behaviour: with only the GATE DATA
    # prong live, `.../schema` alone vouched for the spec root, so the EXECUTED prong could stop
    # deriving both mode-755 gate executables and this still returned [].
    case("a derived CHILD is NOT evidence its declared parent was found",
         declared_not_derived(["docs/superpowers/specs/m4/sub",
                               "docs/superpowers/specs/2026-08-03-stable-blob-addressing"],
                              CODE_UNDER_PROSE), ["docs/superpowers/specs/m4/"])
    # ⛔⛔ THE CASES FOR THE CRASH CI SAW AND THIS MACHINE DID NOT. Same commit, same manifest:
    # locally 723 attributed, in CI 722, with one mutation "RED but printed no `[FAIL]` line".
    # Cause, measured: a gate script's DOCSTRING mentioning a `docs/` path yields a multi-thousand
    # character blob with components up to 1450 bytes, and `Path.is_file()` RAISES ENAMETOOLONG on
    # it — except on Python 3.13+, which swallows that errno. The raise happened while BUILDING the
    # case list, so nothing was printed at all. Shape is now decided before the disk is touched.
    case("a real repo path looks like a path",
         looks_like_path("docs/superpowers/specs/m4/live-manifest.txt"), True)
    case("...but prose containing a path does not, because no path here has WHITESPACE",
         looks_like_path("docs/dev-process.md` says the same thing generally: before adding"), False)
    case("...nor does anything carrying a NEWLINE, which is how the bound prose blobs present",
         looks_like_path("docs/adr/`, which is read by the review, and\nunreferenced"), False)
    case("...nor a component over the 255-byte filesystem limit, the shape that actually RAISED",
         looks_like_path("docs/" + "a" * 256), False)
    case("...while 255 bytes exactly is still a path, so the bound is not off by one",
         looks_like_path("docs/" + "a" * 255), True)
    case("...and multi-byte characters are counted as BYTES, not code points",
         looks_like_path("docs/" + "é" * 128), False)
    case("an empty string is not a path", looks_like_path(""), False)
    # ⛔ AND THE GUARD IS LOAD-BEARING THROUGH `is_gate_data`: prose must never reach `is_file`.
    # ⚠ THE FAKE READER RECORDS, IT DOES NOT RAISE — and that distinction cost a measurement. The
    # first version threw from the lambda to prove the call never happens; removing the guard then
    # made the suite CRASH while building the case list, so it went red with NO `[FAIL]` line and
    # BOTH of these mutations came back unattributable. That is the same report-format defect CI
    # had just caught one fix earlier, reintroduced by the case written to cover it. Recording the
    # call and asserting on the record makes the case FAIL instead.
    _probe: list[str] = []
    case("prose never reaches the filesystem at all",
         (is_gate_data("docs/x.md` and some prose\nwith a newline",
                       lambda p: bool(_probe.append(p)) or True), _probe), (False, []))
    case("...while a real gate data path does reach it",
         is_gate_data("docs/superpowers/specs/m4/live-manifest.txt", lambda p: True), True)
    # ⛔ r2 MEDIUM 3 — an EXTENSION-LESS gate input is gate data. The retired allow-list left a
    # third suffix rule behind ("no extension means not gate data"), unfalsified, hiding a gate
    # reading a `manifest`, a `Makefile` or a `Dockerfile`.
    case("an extension-less gate FILE is gate data — the filename shape does not decide",
         is_gate_data("docs/superpowers/specs/newgate/manifest", lambda p: True), True)
    case("...and a bound DIRECTORY is still excluded, by not being a FILE rather than by its name",
         is_gate_data("docs/reviews", lambda p: False), False)
    # ⛔ r2 MEDIUM 4 — ENAMETOOLONG fires on the TOTAL as well as the component. Measured by the
    # reviewer on 3.12: a 1200-byte path whose every component is 100 bytes still RAISES.
    case("a path over the TOTAL byte limit is rejected, not just one with a long component",
         looks_like_path("docs/" + "/".join(["a" * 100] * 50)), False)
    case("...while a long path that stays under the total is still a path",
         looks_like_path("docs/" + "/".join(["a" * 100] * 5)), True)
    # ⛔ r3 MEDIUM 5a — THE VALUE, PINNED EXACTLY. The two cases above bracket it between 509 and
    # 5054 bytes, so `PATH_LIMIT = 4096` — Linux's PATH_MAX, precisely the wrong value for the
    # platform this fix was about — left the suite at 178/178. `COMPONENT_LIMIT` is the model these
    # failed to follow: 256 rejected, 255 accepted, value pinned to the byte.
    # ⚠ Built with LEGAL components, because the first version of these two cases used one long
    # component and was therefore testing COMPONENT_LIMIT — the wrong clause, and it failed.
    def _path_of(total: int) -> str:
        whole, rest = divmod(total + 1, 101)       # 100-byte parts joined by "/"
        parts = ["a" * 100] * whole + ([("a" * (rest - 1))] if rest > 1 else [])
        return "/".join(parts)
    # ⛔⛔ LITERAL LENGTHS, NOT `PATH_LIMIT + 1` — and the first version of these two cases made
    # exactly that mistake. Built from the constant, the INPUT moves with the mutation, so
    # `PATH_LIMIT = 4096` still rejected 4097 and accepted 4096 and the suite stayed green: a case
    # that can never pin the value it is named for. Hardcoding is correct here precisely because
    # pinning the value IS the point.
    case("one byte over the TOTAL limit of 1024 is rejected",
         looks_like_path(_path_of(1025)), False)
    case("...and exactly 1024 is accepted, so the bound is pinned to the byte",
         looks_like_path(_path_of(1024)), True)
    case("...while a derived path that merely shares a PREFIX does not",
         declared_not_derived(["docs/superpowers/specs/m4-other"],
                              ("docs/superpowers/specs/m4/",)),
         ["docs/superpowers/specs/m4/"])
    # The pure rule, driven with literals — the reader above proves it sees the real file.
    case("a NEW docs/ gate directory the tuple does not know about is REPORTED",
         prose_exceptions_cover(["docs/superpowers/specs/m5/**"], CODE_UNDER_PROSE),
         ["docs/superpowers/specs/m5/**"])
    # ⛔ r16: a BROADER glob must be reported too. `e.startswith(prefix)` cleared all of these, and
    # deleting that clause changed no case — the one clause making the hole was unfalsifiable.
    case("...as is a glob BROADER than an exemption, which used to be silently cleared",
         prose_exceptions_cover(["docs/**", "docs/superpowers/**",
                                 "docs/superpowers/specs/**"], CODE_UNDER_PROSE),
         ["docs/**", "docs/superpowers/**", "docs/superpowers/specs/**"])
    # ...while the one thing that clause legitimately absorbed still passes:
    case("...but a glob written without its trailing slash still matches its exemption",
         prose_exceptions_cover(["docs/superpowers/specs/m4"], CODE_UNDER_PROSE), [])
    case("...while a non-docs glob is not this rule's business",
         prose_exceptions_cover(["supabase/migrations/**"], CODE_UNDER_PROSE), [])
    # ⛔⛔ THE PARAMETER MUST BE VARIED, OR IT IS A CONSTANT WEARING A SIGNATURE. r3's Low 7 fix made
    # `declared` a parameter; every call site then passed `CODE_UNDER_PROSE`, so no case could tell
    # it from the module global and the fix was COSMETIC. Caught by `check-fixture-variation.py` in
    # CI — not by round 4's reviewer, which tested the FUNCTION's sensitivity (a different question
    # from whether the SUITE varies it) and reported it working. These two drive the same input
    # against two different declarations.
    case("the exemption tuple is a real PARAMETER: a fixture declaration covers its own directory",
         prose_exceptions_cover(["docs/x"], ("docs/x/",)), [])
    case("...while the same input against an EMPTY declaration is uncovered",
         prose_exceptions_cover(["docs/x"], ()), ["docs/x"])
    # ⛔ r2 MEDIUM 2 — a bare `docs` used to be SKIPPED, so both prongs reported success over a
    # directory neither had examined. The exemption tuple can never legitimately contain `docs/`,
    # so REPORTING it is correct: it turns a silent pass into a human decision.
    case("a derived bare `docs` is REPORTED, not silently skipped for lacking a slash",
         prose_exceptions_cover(["docs"], CODE_UNDER_PROSE), ["docs"])
    # ⛔⛔ THE CASES THAT WOULD HAVE CAUGHT A GREP. Each of these is a real shape taken from this
    # repository, and a substring scan passes NONE of the negative ones — measured 2026-09-16: a
    # plain grep for the m4 spec directory returns five hits and all five are prose about the path.
    case("a docs/ path bound to a NAME in python is found",
         bound_docs_paths('MANIFEST = ROOT / "docs/superpowers/specs/m4/live-manifest.txt"\n',
                          python=True), ["docs/superpowers/specs/m4/live-manifest.txt"])
    case("...but one that appears only in a COMMENT is NOT",
         bound_docs_paths("# docs/superpowers/specs/m4/live-manifest.txt   gates 10 and 14\n",
                          python=True), [])
    case("...nor one that appears only in a DOCSTRING, which ast.Constant alone would re-admit",
         bound_docs_paths('"""It compares against docs/superpowers/specs/m4/live-manifest.txt."""\n',
                          python=True), [])
    case("a docs/ path bound in SHELL is found",
         bound_docs_paths('SPEC="docs/superpowers/specs/x"\n', python=False),
         ["docs/superpowers/specs/x"])
    case("...but a shell COMMENT mentioning one is not",
         bound_docs_paths('# SPEC="docs/superpowers/specs/x"\n', python=False), [])
    # ⛔⛔ THIS CASE EXISTS BECAUSE THE ONE ABOVE IS VACUOUS FOR THE CLAUSE IT LOOKS LIKE IT TESTS —
    # measured 2026-09-16 by mutating `line.split("#")[0]` away and watching the suite stay GREEN at
    # 147/147. A whole-line comment is rejected by the `NAME=` match, not by the comment strip, so
    # the case passed for an AMBIENT reason. The strip is load-bearing for exactly one shape: a real
    # assignment with a TRAILING comment that mentions a path. That is this case, and the mutation
    # dies on it.
    case("...and a TRAILING comment on a real assignment does not smuggle a path in",
         bound_docs_paths('SPEC="docs/a"  # unlike docs/superpowers/specs/m4/live-manifest.txt\n',
                          python=False), ["docs/a"])
    case("...and a shell line that is not an assignment at all is not",
         bound_docs_paths('run "1/15" "docs/superpowers/specs/x/verify.sh"\n', python=False), [])
    # ⛔ THE NOISY-DIRECTION CASE, AND IT IS THE ONE THAT KILLED THE FIRST DESIGN. `check-docs.py`
    # binds `docs/backlog.md`; taking every bound docs/ path would have returned `docs` itself and
    # demanded the whole tree be exempted from the prose classifier.
    case("a .md a gate merely READS is not gate machinery, so docs/ itself is never derived",
         gate_code_dirs('SPEC="docs/superpowers/specs/x"\n',
                        {"scripts/check-docs.py": 'BACKLOG = "docs/backlog.md"\n'},
                        is_file=_all_exist), [])
    case("...while a gate DATA file under docs/ yields its directory",
         gate_code_dirs("", {"scripts/g.py": 'M = "docs/superpowers/specs/m4/live-manifest.txt"\n'},
                        is_file=_all_exist), ["docs/superpowers/specs/m4"])
    case("...and a file the runner EXECUTES from its spec dir yields that dir",
         gate_code_dirs('SPEC="docs/superpowers/specs/x"\nrun "1/15" "$SPEC/verify-schema.sh"\n',
                        {}, is_file=_all_exist), ["docs/superpowers/specs/x"])
    case("...and nothing at all is derived from nothing, which main treats as CANNOT RUN",
         gate_code_dirs("", {}, is_file=_all_exist), [])
    # ⛔⛔ r1 HIGH (codex), AS CASES — BOTH SHAPES THE REVIEWER EXECUTED. The suffix ALLOW-LIST
    # `(".sql", ".txt")` fail-open'd by omission: a new gate reading a `.json` policy file was
    # invisible, the existing gates kept the result non-empty so the CANNOT-RUN guard passed, and a
    # later PR editing that gate's rules classified as PROSE. `.json` is the reviewer's own example.
    case("a gate input under docs/ with ANY non-prose suffix is gate machinery, not just .sql/.txt",
         gate_code_dirs("", {"scripts/check-new-docs-gate.py":
                             'RULES = "docs/superpowers/specs/new-gate/rules.json"\n'},
                        is_file=_all_exist), ["docs/superpowers/specs/new-gate"])
    # ⛔ ...AND THE SECOND SHAPE, WHICH NO SUFFIX LIST COULD EVER HAVE FIXED: a pathlib join holds
    # no `docs/…` literal at all, so the per-constant scan saw nothing to classify.
    case("...and a pathlib / join is reassembled, so it reads like the same path written whole",
         gate_code_dirs("", {"scripts/g.py":
                             'RULES = ROOT / "docs" / "superpowers" / "specs" / "new-gate"'
                             ' / "rules.json"\n'},
                        is_file=_all_exist), ["docs/superpowers/specs/new-gate"])
    # ⚠ THIS CASE IS NARROWER THAN ITS FIRST NAME CLAIMED. It said the join "rejects a single
    # trailing constant", which is FALSE — `DOCSDIR / name` contains no string constants at all, so
    # there is nothing to reject. What it really pins is that a join built entirely from VARIABLES
    # invents no path. The `len(parts) > 1` clause is inert and carries no mutation; see the
    # docstring.
    case("...while a join built only from variables invents no path",
         bound_docs_paths('P = DOCSDIR / name\n', python=True), [])
    # ⛔ THE REGRESSION THAT INVERTING THE ALLOW-LIST WOULD HAVE CAUSED, measured on the real file:
    # `check-docs.py` binds a REGEX beginning `docs/adr/`. It is not a path, it does not exist, and
    # reporting `docs/adr` as an uncovered gate directory would turn this gate red over nothing.
    # EXISTENCE is what rejects it — the job the suffix list had been doing by accident.
    case("a bound string that is a REGEX, not a path, is rejected because it does not exist",
         gate_code_dirs("", {"scripts/check-docs.py":
                             'ADR = r"docs/adr/(\\d{4})(?:[-\\w]*\\.md)?"\n'},
                        is_file=lambda rel: False), [])
    case("...while the same shape with a real file behind it IS derived",
         gate_code_dirs("", {"scripts/g.py": 'M = "docs/superpowers/specs/m4/live-manifest.txt"\n'},
                        is_file=lambda rel: rel == "docs/superpowers/specs/m4/live-manifest.txt"),
         ["docs/superpowers/specs/m4"])
    # ⛔⛔ r2 HIGH 1 — `review_added` has TWO clauses and only the suffix one was falsified. The
    # case that appeared to cover the DIRECTORY test fed a path that is also a `.md`, so it passed
    # for the suffix reason alone: measured, dropping `p.startswith(REVIEW_DIR)` left the suite
    # green at 166/166. This is the function answering "was a review round recorded?" — the very
    # question whose absence let five PRs merge unreviewed in one night.
    case("a .md OUTSIDE docs/reviews/ is NOT a review document",
         review_added(["docs/notes.md"]), [])
    case("...so a code branch adding one still owes a round",
         verdict(CODE, ["docs/notes.md"], "", none_reason)[0], 1)
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
    # ⟳ 2026-10-31: a CLAUDE half's record (`record-review-verdict.py`) is the wrapper's schema plus
    # `writer`/`tool`, with a clean overlay — and it is read exactly like a Codex one.
    case("a Claude half's verdict is usable like a Codex one — the writer is not read",
         classify_verdict({"schema": 3, "gate_ran": True, "head": "abc123", "dirty": {},
                           "tool": "record-review-verdict", "writer": "claude"}),
         ("abc123", USABLE))
    case("a verdict saying the gate did NOT run is skipped, never read as testimony",
         classify_verdict({"gate_ran": False, "head": "abc123"}), (None, SKIP))
    case("...and that rule is the one whose deletion turned exit 2 into exit 0",
         classify_verdict({"gate_ran": False, "head": "abc123"})[1] == USABLE, False)
    # ⛔ **r3 Claude half, H2 — AND THE TRUTHY VALUES ARE THE CASE.** The two above are both bools
    # and PASSED under the defect: `if not rec.get("gate_ran")` classified `"false"`, `"no"`, `"0"`
    # and `1` as USABLE, crediting a gate that did not run with having seen the final tree. A suite
    # asserting only True/False cannot tell `not x` from `x is not True`, which is this repo's
    # *a test that cannot fail* shape applied to a High's own fix — measured twice in this slice.
    case("a TRUTHY NON-BOOL `gate_ran` does NOT read as `the gate ran` — the string \"false\" is "
         "truthy, and reading it that way credited a gate that never ran with the final tree",
         classify_verdict({"gate_ran": "false", "head": "abc123"}), (None, SKIP))
    case("...at a second distinct truthy non-bool, so this is not a special case for one value",
         classify_verdict({"gate_ran": 1, "head": "abc123"}), (None, SKIP))
    case("...and a real `gate_ran: True` is still usable, so reading it by identity did not turn "
         "the honest record into a skip", classify_verdict({"gate_ran": True, "head": "abc123"}),
         ("abc123", USABLE))
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
    # ⛔ **r3 Claude half, H2 — `is None` WAS NOT THE RULE, `isinstance(dict)` IS.** A non-dict
    # `dirty` classified USABLE while `reviewed_map` returned `{}` for it: a real head with an
    # empty overlay, byte-identical to the clean tree r11 Medium closed for the `{}`/`None` pair.
    # ⚠ The `[]` case is not hypothetical — a committed schema-2 verdict carries it; see the
    # comment on the rule. `{}` above is the control that keeps these three from passing vacuously.
    case("a LIST dirty is unusable too — a real head with an overlay nothing can read is the same "
         "vacuous comparison a NULL one is, and one record on disk actually carries it",
         classify_verdict({"gate_ran": True, "head": "abc", "dirty": []}), (None, UNUSABLE))
    case("...as is a STRING dirty, so the rule is the TYPE and not a list of bad values",
         classify_verdict({"gate_ran": True, "head": "abc", "dirty": "oops"}), (None, UNUSABLE))
    case("...and a NUMBER, at a second scalar, so it is not a special case for one of them",
         classify_verdict({"gate_ran": True, "head": "abc", "dirty": 42}), (None, UNUSABLE))
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
    case("...and so does a LIST one — the shape that makes the overlay vacuous, which is why "
         "classify_verdict now asks the same isinstance question this end already asked",
         reviewed_map({"dirty": []}), {})
    # ── r11: the second question is a rule, not a line. `if True:` in its place left the suite at
    # 77/77 — the entire subsystem detachable with no red anywhere. ──
    case("guarded code and no waiver: the question is asked",
         second_question(["lib/x.ts"], None), (True, None))
    case("nothing guarded changed: the question is moot, and says nothing",
         second_question(["docs/backlog.md"], None), (False, None))
    # ⛔ r15 Medium: an EMPTY declaration is not a declaration, and this arm disagreed with
    # `verdict()` about it. `reason_of` returns `''` for a bare marker, not None.
    case("a bare NO-REVIEW with no reason does NOT waive the final-tree question",
         second_question(["lib/x.ts"], ""), (True, None))
    case("...nor does one that is only whitespace",
         second_question(["lib/x.ts"], "   \n"), (True, None))
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
    # ── r14: the diff argv both branch-scoped questions use. The rename policy was unreachable from
    # any case, which is how it stayed wrong through thirteen rounds. ──
    # ⛔ WITHOUT `--no-renames` A GUARDED FILE MOVED TO A PROSE PATH VANISHES from the diff, and the
    # gate reports "no guarded path changed" over a DELETED code file. Measured, with a control.
    case("the diff asks git NOT to pair a deletion with an addition",
         "--no-renames" in diff_argv("abc123"), True)
    case("...which is what stops a guarded file renamed into docs/ from disappearing entirely",
         diff_argv("abc123"),
         ["diff", "--name-only", "-z", "--no-renames", "abc123", "HEAD"])
    case("the ADDED-only question asks the same way, plus the status filter",
         diff_argv("abc123", added_only=True),
         ["diff", "--name-only", "-z", "--no-renames", "--diff-filter=A", "abc123", "HEAD"])
    case("...so the two questions cannot disagree about what a rename is",
         diff_argv("abc123")[:4], diff_argv("abc123", added_only=True)[:4])
    case("the base sha is passed through, not interpolated into a flag",
         diff_argv("deadbeef")[-2:], ["deadbeef", "HEAD"])
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

    # ── backlog #426: master's changes since a round are subtracted per FILE, by a tree comparison ──
    _M = "100644 " + "m" * 40
    _B = "100644 " + "b" * 40
    case("#426: no merge could be built -> NOT explained, the round stays required",
         master_explains("lib/x.ts", None, _M), False)
    case("#426: HEAD equal to the reviewed commit merged with master IS explained",
         master_explains("lib/x.ts", ({"lib/x.ts": _M}, frozenset()), _M), True)
    case("#426: a branch edit on top of master's IS NOT explained",
         master_explains("lib/x.ts", ({"lib/x.ts": _M}, frozenset()), _B), False)
    case("#426 trap 1: a CONFLICTED path is never explained, even when HEAD equals the merge",
         master_explains("lib/x.ts", ({"lib/x.ts": _M}, frozenset({"lib/x.ts"})), _M), False)
    case("#426: a conflict on ANOTHER path does not block this one",
         master_explains("lib/y.ts", ({"lib/y.ts": _M}, frozenset({"lib/x.ts"})), _M), True)
    case("merge-delta r4: absent in HEAD AND in the merge is charged (only a lying lookup gives it)",
         master_explains("lib/z.ts", ({}, frozenset()), ABSENT_ENTRY), False)
    case("merge-delta r4 control: ...while a present HEAD equal to the merge is still explained",
         master_explains("lib/z.ts", ({"lib/z.ts": _B}, frozenset()), _B), True)
    case("#426: a file HEAD deleted that the merge keeps is NOT explained",
         master_explains("lib/x.ts", ({"lib/x.ts": _M}, frozenset()), ABSENT_ENTRY), False)
    case("#426: a clean merge-tree is its tree and no conflicts",
         parse_merge_tree("t1\0", 0), ("t1", frozenset()))
    case("#426: a conflicted merge-tree still has a tree, and NAMES the conflicts",
         parse_merge_tree("t2\0lib/a.ts\0lib/b.ts\0", 1),
         ("t2", frozenset({"lib/a.ts", "lib/b.ts"})))
    case("#426 trap 3: a merge-tree that did not run is None, never 'clean'",
         parse_merge_tree("fatal: bad object\0", 128), None)
    case("#426 trap 3: ...and empty output on rc 0 is None, not a tree named ''",
         parse_merge_tree("", 0), None)
    case("#426 FAILS IF (pure): a path whose only post-round change is master's is not charged",
         round_tail(["lib/x.ts"], {}, {"lib/x.ts": _M}, ({"lib/x.ts": _M}, frozenset())), [])
    case("#426: ...while one carrying a branch edit too still is",
         round_tail(["lib/x.ts"], {}, {"lib/x.ts": _B}, ({"lib/x.ts": _M}, frozenset())),
         ["lib/x.ts"])
    case("#426: a DIRTY-overlay path keeps the strict rule — master cannot clear it",
         round_tail(["lib/x.ts"], {"lib/x.ts": "100644 aaa"}, {"lib/x.ts": _M},
                    ({"lib/x.ts": _M}, frozenset())), ["lib/x.ts"])
    _onto_seen: list = []
    _t9, _ = round_tails(_V, ["lib/x.ts"], load=lambda r: _CLEAN, is_ancestor=lambda h: True,
                         changed_since=lambda h: ["lib/x.ts"],
                         final_entries=lambda p: {"lib/x.ts": _M}, onto="m1",
                         master_side=lambda h, o, p: (_onto_seen.append((h, o, p)) or
                                                      ({"lib/x.ts": _M}, frozenset())))
    case("#426 through the gatherer: a master-only change clears the round",
         _t9["a.verdict.json"], [])
    case("#426 through the gatherer: the round's head, `onto` and the guarded paths are passed",
         _onto_seen, [("h1", "m1", ["lib/x.ts"])])
    _t10, _ = round_tails(_V, ["lib/x.ts"], load=lambda r: _CLEAN, is_ancestor=lambda h: True,
                          changed_since=lambda h: ["lib/x.ts"],
                          final_entries=lambda p: {"lib/x.ts": _M}, onto=None)
    case("#426 trap 3 through the gatherer: no merge base -> the round is charged",
         _t10["a.verdict.json"], ["lib/x.ts"])

    # ── #426 over a REAL repository: PR #487's shape, a conflict resolution, an evil merge ──
    _tmp = tempfile.mkdtemp(prefix="crr426-")

    # BYTES, decoded here and NOT through `_run_git`: this runner feeds the production parsers in
    # `_tails_at`, so it must keep a CR too, and a mutant of `_run_git` must not reach the fixture
    def _g(*a: str) -> subprocess.CompletedProcess:
        p = subprocess.run(["git", "-C", _tmp, "-c", "user.name=t", "-c",
                            "user.email=t@example.com", "-c", "commit.gpgsign=false", *a],
                           capture_output=True)
        return subprocess.CompletedProcess(p.args, p.returncode,
                                           p.stdout.decode("utf-8", "surrogateescape"),
                                           p.stderr.decode("utf-8", "surrogateescape"))

    def _w(rel: str, text: str) -> None:
        f = pathlib.Path(_tmp, rel)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")

    def _commit(msg: str) -> str:
        _g("add", "--", ".")
        _g("commit", "-q", "-m", msg)
        return _g("rev-parse", "HEAD").stdout.strip()

    # the fixture's own `-z` split, NOT `split_nul`: a mutant of that rule must red ITS case, not
    # crash this one with a NUL inside an argv
    def _nul(out: str) -> list[str]:
        return [x for x in out.split("\0") if x]

    # ⛔ `onto` and HEAD's entries come from the SAME helpers `main` calls (`merge_onto`,
    # `_final_entries`), never a copy — r1 Claude M2: a copy here left `main`'s line unexercised.
    def _tails_at(review: str, git=None) -> list[str]:
        git = git or _g
        onto = merge_onto("master", git=git)
        delta = _nul(git(*diff_argv(onto)).stdout)
        t, _u = round_tails(
            ["docs/reviews/verdicts/r.verdict.json"], delta,
            load=lambda r: {"gate_ran": True, "head": review, "dirty": {}},
            is_ancestor=lambda h: git("merge-base", "--is-ancestor", h, "HEAD").returncode == 0,
            changed_since=lambda h: _nul(git(*diff_argv(h)).stdout),
            final_entries=lambda p: _final_entries(p, git=git),
            onto=onto, master_side=lambda h, o, p: _master_side(h, o, p, git=git))
        return t.get("r.verdict.json", ["<no usable round>"])

    # a `git` that answers exactly ONE call itself, so a case can inject a failure into a real repo
    def _failing(prefix: tuple, rc: int = 128, out: str = "") -> object:
        def g(*a: str) -> subprocess.CompletedProcess:
            if a[:len(prefix)] == prefix:
                return subprocess.CompletedProcess(["git", *a], rc, out, "fatal: injected")
            return _g(*a)
        return g

    # an `isolate` that answers exactly ONE call on the ISOLATED runner itself (the merge runs there)
    def _iso_failing(prefix: tuple, rc: int = 128, out: str = "") -> object:
        @contextlib.contextmanager
        def iso(g):
            with _isolated_git(g) as run:
                def r(*a: str) -> subprocess.CompletedProcess:
                    if a[:len(prefix)] == prefix:
                        return subprocess.CompletedProcess(["git", *a], rc, out, "fatal: injected")
                    return run(*a)
                yield r if run else None
        return iso

    # a crash is a `[FAIL]` line naming this case, never a traceback the harness cannot attribute
    def _or_raised(fn) -> object:
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 — the case reports it
            return f"raised {type(exc).__name__}"

    def _raises(fn) -> str:
        try:
            fn()
        except RuntimeError as exc:
            return "CANNOT RUN" if str(exc).startswith("CANNOT RUN") else f"raised {exc}"
        return "did not raise"

    _g("init", "-q", "-b", "master")
    _LINES = "".join(f"line {i}\n" for i in range(1, 21))
    _GATE = "docs/superpowers/specs/m4/gate.sql"     # guarded code under a prose directory
    for _f in (".github/workflows/ci.yml", "scripts/plan.py", "scripts/drivable.py",
               "scripts/solo.py", "scripts/gone.py", _GATE):
        _w(_f, _LINES)
    _base = _commit("base")
    _g("checkout", "-q", "-b", "br")
    _w(".github/workflows/ci.yml", _LINES.replace("line 2\n", "BRANCH 2\n"))
    _w("scripts/plan.py", _LINES.replace("line 2\n", "BRANCH 2\n"))
    _w(_GATE, _LINES.replace("line 2\n", "BRANCH 2\n"))
    _review = _commit("branch work, then the final review round")
    _g("checkout", "-q", "master")
    _w(".github/workflows/ci.yml", _LINES.replace("line 18\n", "MASTER 18\n"))
    _w("scripts/plan.py", _LINES.replace("line 18\n", "MASTER 18\n"))
    _commit("master moves on")
    _g("checkout", "-q", "br")
    _g("merge", "-q", "--no-edit", "master")
    case("#426 FAILS IF, real git: a round followed ONLY by a merge of master is not charged",
         _tails_at(_review), [])
    _w("scripts/drivable.py", _LINES.replace("line 9\n", "BRANCH 9\n"))
    _commit("a genuine branch change after the round")
    case("#426, PR #487's shape: the genuine change is charged, master's two files are not",
         _tails_at(_review), ["scripts/drivable.py"])
    # trap 2 — an EVIL MERGE: master's merge commit also carries a branch edit nobody reviewed
    _g("reset", "-q", "--hard", _review)
    _g("checkout", "-q", "master")
    _w("scripts/solo.py", _LINES.replace("line 5\n", "MASTER 5\n"))
    _commit("master again")
    _g("checkout", "-q", "br")
    _g("merge", "-q", "--no-commit", "master")
    _w("scripts/plan.py", _LINES.replace("line 2\n", "BRANCH 2\n").replace(
        "line 18\n", "MASTER 18\n").replace("line 10\n", "EVIL 10\n"))
    _commit("merge master (evil)")
    case("#426 trap 2: a branch edit hidden inside a merge commit is charged",
         _tails_at(_review), ["scripts/plan.py"])
    # trap 1 — a CONFLICT whose resolution is the branch's own code
    _g("reset", "-q", "--hard", _review)
    _g("checkout", "-q", "master")
    _w(".github/workflows/ci.yml", _LINES.replace("line 18\n", "MASTER 18\n").replace("line 2\n", "MASTER 2\n"))
    _commit("master edits the branch's line")
    _g("checkout", "-q", "br")
    _g("merge", "-q", "--no-edit", "master")          # conflicts on ci.yml; resolve by hand
    _w(".github/workflows/ci.yml", _LINES.replace("line 18\n", "MASTER 18\n").replace("line 2\n", "RESOLVED 2\n"))
    _commit("merge master, resolving the conflict")
    case("#426 trap 1: a merge whose conflict RESOLUTION edits a guarded file is charged",
         _tails_at(_review), [".github/workflows/ci.yml"])
    case("#426 trap 3, real git: an unknown commit to merge with builds no master side",
         _master_side(_review, "f" * 40, [".github/workflows/ci.yml"], git=_g), None)
    case("merge-delta r1 Claude M2: an unresolvable base has no `onto`, never an empty one",
         merge_onto("no-such-ref", git=_g), None)
    _onto_good = merge_onto("master", git=_g)
    case("merge-delta r2 control: the isolated merge of this conflict IS built, and names it",
         (_master_side(_review, _onto_good, [".github/workflows/ci.yml"], git=_g) or (None, None))[1],
         frozenset({".github/workflows/ci.yml"}))
    case("merge-delta r1 Codex M2 / Claude L1: a failed `ls-tree` of the merged tree is None",
         _master_side(_review, _onto_good, [".github/workflows/ci.yml"], git=_g,
                      isolate=_iso_failing(tuple(ls_tree_argv("")[:3]))), None)
    case("merge-delta r1 Claude M1: no empty tree to read attributes from builds no master side",
         _master_side(_review, _onto_good, [".github/workflows/ci.yml"], git=_g,
                      isolate=_iso_failing(("hash-object",))), None)
    # ⚠ A SECOND LOCK, NOT A MUTATION TARGET: git 2.49 itself refuses `--attr-source=` with an
    # empty value (rc 128, "bad --attr-source") once a content merge reads attributes, and a merge
    # that reads none cannot be steered by them — so removing this check stays green (measured).
    case("merge-delta r1 Claude M1: ...nor does an empty answer with rc 0",
         _master_side(_review, _onto_good, [".github/workflows/ci.yml"], git=_g,
                      isolate=_iso_failing(("hash-object",), rc=0)), None)
    case("merge-delta r2: an unresolvable object store builds no master side",
         _or_raised(lambda: _master_side(
             _review, _onto_good, [".github/workflows/ci.yml"],
             git=_failing(("rev-parse", "--path-format=absolute", "--git-common-dir")))), None)
    case("merge-delta r2: a common dir with no object store builds no master side",
         _or_raised(lambda: _master_side(
             _review, _onto_good, [".github/workflows/ci.yml"],
             git=_failing(("rev-parse", "--path-format=absolute", "--git-common-dir"),
                          rc=0, out=str(pathlib.Path(_tmp, "nowhere")) + "\n"))), None)
    # the isolated repository's own `git` is reached through PATH, so a PATH holding a `git` that
    # refuses everything fails `init`, and an empty one fails to launch it at all
    _common = _g("rev-parse", "--path-format=absolute", "--git-common-dir").stdout
    _bin = pathlib.Path(tempfile.mkdtemp(prefix="crr426-bin-"))    # outside the fixture's tree
    _saved_path = os.environ["PATH"]
    try:
        os.environ["PATH"] = str(_bin)
        _known = _failing(("rev-parse", "--path-format=absolute", "--git-common-dir"), rc=0,
                          out=_common)
        case("merge-delta r2: no `git` to build the isolated repository builds no master side",
             _or_raised(lambda: _master_side(_review, _onto_good, [".github/workflows/ci.yml"],
                                             git=_known)), None)
        (_bin / "git").write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        (_bin / "git").chmod(0o755)
        case("merge-delta r2: an isolated repository whose `init` fails builds no master side",
             _or_raised(lambda: _master_side(_review, _onto_good, [".github/workflows/ci.yml"],
                                             git=_known)), None)
    finally:
        os.environ["PATH"] = _saved_path
        shutil.rmtree(_bin, ignore_errors=True)

    # merge-delta r1 Codex H1 — master DELETES a file; the branch re-adds it after the round
    _g("reset", "-q", "--hard", _review)
    _g("checkout", "-q", "master")
    _g("reset", "-q", "--hard", _base)
    _g("rm", "-q", "--", "scripts/gone.py")
    _g("commit", "-q", "-m", "master deletes gone.py")
    _g("checkout", "-q", "br")
    _g("merge", "-q", "--no-edit", "master")
    _w("scripts/gone.py", _LINES.replace("line 7\n", "UNREVIEWED 7\n"))
    _commit("the branch brings gone.py back, unreviewed")
    case("merge-delta r1 Codex H1 control: a re-add of a file master deleted is charged",
         _tails_at(_review), ["scripts/gone.py"])
    case("merge-delta r1 Codex H1: a failed HEAD `ls-tree` is CANNOT RUN, never 'all absent'",
         _raises(lambda: _tails_at(_review, git=_failing(tuple(ls_tree_argv("HEAD"))))),
         "CANNOT RUN")

    # ⛔ merge-delta r3 Claude M1 — a NAME git would read as a pathspec, or normalise. Each file is
    # added after the round through the index alone (no checkout: some of these names cannot exist
    # on this filesystem), and the round's own commit stays the reviewed head. The CONTROL is the
    # pathspec form both lookups used, which misses the name in this very repository.
    _blob = _g("rev-parse", f"{_review}:scripts/solo.py").stdout.strip()
    _ENTRY = f"100644 {_blob}"

    def _add_raw(name: str) -> str:
        _g("reset", "-q", "--hard", _review)
        _g("-c", "core.precomposeunicode=false", "update-index", "--add", "--cacheinfo",
           f"100644,{_blob},{name}")
        _g("commit", "-q", "-m", "a post-round file under an odd name")
        return _g("rev-parse", "HEAD").stdout.strip()

    def _lookups(name: str) -> tuple:
        head = _add_raw(name)
        ms = _or_raised(lambda: _master_side(head, merge_onto("master", git=_g), [name], git=_g))
        return (_or_raised(lambda: _final_entries([name], git=_g)),
                ms[0] if isinstance(ms, tuple) else ms,
                _or_raised(lambda: _tails_at(_review)))

    for _name, _tag in ((":/evil.sh", "`:/`"), (":(top)evil.sh", "`:(top)`")):
        _fe, _ms, _tl = _lookups(_name)
        case(f"merge-delta r3 M1 control: the pathspec lookup misses a {_tag} name",
             _g("ls-tree", "-z", "HEAD", "--", _name).stdout, "")
        case(f"merge-delta r3 M1: HEAD's lookup finds a {_tag} name by its exact bytes",
             _fe, {_name: _ENTRY})
        case(f"merge-delta r3 M1: the merged tree's lookup finds a {_tag} name too",
             _ms, {_name: _ENTRY})
        case(f"merge-delta r3 M1: an unreviewed {_tag} file is charged, never absent == absent",
             _tl, [_name])
    # a DECOMPOSED name under `core.precomposeunicode=true`, the macOS default. Git precomposes its
    # argv only on macOS, so the control's want is the platform's own answer.
    _nfd = "scripts/cafe\u0301.py"
    _g("config", "core.precomposeunicode", "true")
    _fe, _ms, _tl = _lookups(_nfd)
    case("merge-delta r3 M1 control: under precomposition the pathspec lookup of an NFD name",
         bool(_g("ls-tree", "-z", "HEAD", "--", _nfd).stdout), sys.platform != "darwin")
    case("merge-delta r3 M1: HEAD's lookup finds a decomposed name", _fe, {_nfd: _ENTRY})
    case("merge-delta r3 M1: the merged tree's lookup finds a decomposed name", _ms, {_nfd: _ENTRY})
    case("merge-delta r3 M1: an unreviewed decomposed-name file is charged", _tl, [_nfd])
    _g("config", "--unset", "core.precomposeunicode")
    for _name, _tag in (("scripts/a\nb.py", "a newline"), ("scripts/caf\udce9.py", "non-UTF-8 bytes"),
                        ("scripts/a\rb.py", "a carriage return")):
        _fe, _ms, _tl = _lookups(_name)
        case(f"merge-delta r3 M1: HEAD's lookup finds a name holding {_tag}", _fe, {_name: _ENTRY})
        case(f"merge-delta r3 M1: the merged tree's lookup finds a name holding {_tag}",
             _ms, {_name: _ENTRY})
        case(f"merge-delta r3 M1: an unreviewed file whose name holds {_tag} is charged",
             _tl, [_name])
    _g("reset", "-q", "--hard", _review)
    case("merge-delta r3 M1: a path that is a DIRECTORY in HEAD still has an entry, as before",
         _final_entries(["scripts"], git=_g).get("scripts", "").split()[:1], ["040000"])
    case("merge-delta r3 M1 (pure): the lookup lists the whole tree, with no path in its argv",
         ls_tree_argv("t1"),
         ["-c", "core.precomposeunicode=false", "ls-tree", "-r", "-t", "-z", "--full-tree", "t1"])
    case("merge-delta r3 M1 (pure): only the EXACT names asked for are selected",
         select_entries({":/a": "e1", "a": "e2", "b": "e3"}, [":/a", "c"]), {":/a": "e1"})
    # ⛔ merge-delta r3 Claude L1 — a crash inside the isolated repository's setup leaves NO temp
    # dir. Counted in a PRIVATE `TMPDIR`, so another run's leftovers cannot answer for this one.
    _priv = tempfile.mkdtemp(prefix="crr426-tmpdir-")
    _saved_tempdir, _saved_env = tempfile.tempdir, isolated_env
    try:
        tempfile.tempdir = _priv

        def _crash(*_a, **_k):
            raise ValueError("injected")
        globals()["isolated_env"] = _crash
        _r = _or_raised(lambda: _master_side(_review, _onto_good, [".github/workflows/ci.yml"],
                                             git=_g))
        case("merge-delta r3 L1: a crash in the isolated setup leaves no `crr-merge-*` dir",
             (_r, sorted(x.name for x in pathlib.Path(_priv).glob("crr-merge-*"))),
             ("raised ValueError", []))
    finally:
        globals()["isolated_env"] = _saved_env
        tempfile.tempdir = _saved_tempdir
        shutil.rmtree(_priv, ignore_errors=True)

    # merge-delta r1 Claude M1 — a merge DRIVER the branch chose resolves a real conflict
    _g("reset", "-q", "--hard", _review)
    _g("checkout", "-q", "master")
    _g("reset", "-q", "--hard", _base)
    _w(_GATE, _LINES.replace("line 2\n", "MASTER 2\n"))
    _commit("master edits the gate's line 2 too")
    _g("checkout", "-q", "br")
    _w("docs/.gitattributes", "** merge=union\n")    # prose: committing it is never charged
    _commit("a prose-path attributes file")
    _g("merge", "-q", "--no-edit", "master")          # clean, under the union driver
    _union = pathlib.Path(_tmp, _GATE).read_text(encoding="utf-8")
    case("merge-delta r1 Claude M1: a committed `merge=union` cannot turn a conflict into a clear",
         _tails_at(_review), [_GATE])
    # the same union content, typed by hand with no committed attributes, under each LOCAL source
    _g("reset", "-q", "--hard", _review)
    _g("merge", "-q", "--no-edit", "master")          # conflicts on the gate
    _w(_GATE, _union)
    _commit("merge master, resolving the gate by hand to the union")
    case("merge-delta r1 Claude M1 control: the hand-typed union with no attributes is charged",
         _tails_at(_review), [_GATE])
    # Claude L2 — the shape where ONLY the conflict exclusion charges: HEAD commits the synthesised
    # conflicted blob itself, markers and all, so HEAD's entry EQUALS the master side's
    _ms_tree = _g(*merge_tree_argv(_g("hash-object", "-t", "tree", "/dev/null").stdout.strip(),
                                   _review, merge_onto("master", git=_g))).stdout.split("\0")[0]
    _w(_GATE, _g("cat-file", "-p", f"{_ms_tree}:{_GATE}").stdout)
    _commit("the branch commits the conflicted blob as it stands")
    case("merge-delta r1 Claude L2: HEAD EQUAL to a conflicted merge is still charged",
         _tails_at(_review), [_GATE])
    _g("reset", "-q", "--hard", "HEAD~1")             # back to the hand-typed union for the rest
    _w("docs/.gitattributes", "** merge=union\n")    # uncommitted, in the working tree
    case("merge-delta r1 Claude M1: a WORKTREE `.gitattributes` does not clear it",
         _tails_at(_review), [_GATE])
    pathlib.Path(_tmp, "docs/.gitattributes").unlink()
    _w(".union-attrs", "* merge=union\n")
    _g("config", "core.attributesFile", str(pathlib.Path(_tmp, ".union-attrs")))
    case("merge-delta r1 Claude M1: a `core.attributesFile` does not clear it",
         _tails_at(_review), [_GATE])
    _g("config", "--unset", "core.attributesFile")
    _g("config", "merge.default", "union")
    case("merge-delta r1 Claude M1: a repository `merge.default` does not clear it",
         _tails_at(_review), [_GATE])
    _g("config", "--unset", "merge.default")
    # ⛔ merge-delta r2: an `info/attributes` is no longer REFUSED (r1's fallback) — the isolated
    # repository has its own, empty one, so the real one is simply not read: the conflict is BUILT
    # and named, which is stronger than a `None`.
    _w(".git/info/attributes", "* merge=union\n")
    _onto_m = merge_onto("master", git=_g)
    # the CONTROL is r1's own command, in the real repository: what each source fooled before
    _empty_t = _g("hash-object", "-t", "tree", "/dev/null").stdout.strip()
    _real_mt = lambda: _g(f"--attr-source={_empty_t}", "-c", "core.attributesFile=/dev/null",
                          "-c", "merge.default=text", "merge-tree", "--write-tree", "--name-only",
                          "--no-messages", "-z", _review, _onto_m).returncode
    case("merge-delta r2 control: r1's merge in the real repository honours its `info/attributes`",
         _real_mt(), 0)
    case("merge-delta r1 Claude M1: an `info/attributes` in force still names the conflict",
         (_master_side(_review, _onto_m, [_GATE], git=_g) or ({}, frozenset()))[1], frozenset({_GATE}))
    case("merge-delta r1 Claude M1: ...and through the gatherer it is charged",
         _tails_at(_review), [_GATE])
    pathlib.Path(_tmp, ".git/info/attributes").unlink()
    # merge-delta r2 Codex M1 — the `text` driver itself, redefined in every config layer git reads.
    # The driver copies the hand-typed union over the merge result, so the merge comes out EQUAL.
    # Each layer sets `merge.default=text` TOO: r2 dropped that `-c`, and a driver nothing selects
    # would leave these cases green with the isolation removed.
    _drv = f"cp {pathlib.Path(_tmp, _GATE)} %A"
    case("merge-delta r2 Codex M1 control: with no driver configured the real merge conflicts",
         _real_mt(), 1)
    _g("config", "merge.text.driver", _drv)
    _g("config", "merge.default", "text")
    case("merge-delta r2 Codex M1 control: the real merge honours a configured `merge.text.driver`",
         _real_mt(), 0)
    case("merge-delta r2 Codex M1: a repository `merge.text.driver` does not clear it",
         _tails_at(_review), [_GATE])
    _g("config", "--unset", "merge.text.driver")
    _g("config", "--unset", "merge.default")
    _w(".inc-driver", f"[merge]\n\tdefault = text\n[merge \"text\"]\n\tdriver = {_drv}\n")
    # an `include.path`, not the review's `includeIf.gitdir:` — that condition did not match under
    # this suite's temp path on git 2.49 (measured), and the layer is the same: an included file
    _g("config", "include.path", str(pathlib.Path(_tmp, ".inc-driver")))
    case("merge-delta r2 Codex M1 control: r1's merge honours a driver from an INCLUDED file",
         _real_mt(), 0)
    case("merge-delta r2 Codex M1: an included driver does not clear it", _tails_at(_review), [_GATE])
    _g("config", "--unset", "include.path")
    _saved = dict(os.environ)
    try:
        os.environ.update({"GIT_CONFIG_COUNT": "2", "GIT_CONFIG_KEY_0": "merge.text.driver",
                           "GIT_CONFIG_VALUE_0": _drv, "GIT_CONFIG_KEY_1": "merge.default",
                           "GIT_CONFIG_VALUE_1": "text"})
        case("merge-delta r2 Codex M1 control: the real merge honours a driver injected by env",
             _real_mt(), 0)
        case("merge-delta r2 Codex M1: a `GIT_CONFIG_COUNT` driver does not clear it",
             _tails_at(_review), [_GATE])
        os.environ.clear()
        os.environ.update(_saved)
        os.environ.pop("GIT_CONFIG_NOSYSTEM", None)       # the fixture turns the system layer off
        os.environ["GIT_CONFIG_SYSTEM"] = str(pathlib.Path(_tmp, ".inc-driver"))
        case("merge-delta r2 control: the real merge honours a SYSTEM-config driver",
             _real_mt(), 0)
        case("merge-delta r2: a system-config driver does not clear it", _tails_at(_review), [_GATE])
    finally:
        os.environ.clear()
        os.environ.update(_saved)
    case("merge-delta r2 control: every layer removed, the real merge conflicts again", _real_mt(), 1)
    # ⚠ merge-delta r2 — REPLACE REFS. The isolated repository has NO refs, so `refs/replace/` is
    # not read: the merge is of the objects the SHAs name. Replacing the round's commit by HEAD
    # makes the REAL merge HEAD's own tree (clean); the isolated one still names the conflict.
    _g("replace", _review, "HEAD")
    case("merge-delta r2 control: a replace ref makes the real merge clean", _real_mt(), 0)
    case("merge-delta r2: a replace ref of the round's commit is not read by the isolated merge",
         (_master_side(_review, _onto_m, [_GATE], git=_g) or ({}, frozenset()))[1], frozenset({_GATE}))
    _g("replace", "-d", _review)
    # merge-delta r2 Codex M2 — the SYSTEM gitattributes is `$(prefix)/etc/gitattributes`, a path no
    # environment variable relocates, and this suite does not write outside its temp dir; so the
    # system ATTRIBUTES layer is pinned here by the environment, and its live effect was measured by
    # the review (`GIT_ATTR_NOSYSTEM=1` restored the conflict).
    _env = isolated_env("/g", "/h", "/bin")
    case("merge-delta r2 Codex M2 (pure): the isolated merge reads no system attributes",
         _env.get("GIT_ATTR_NOSYSTEM"), "1")
    case("merge-delta r2 (pure): the isolated environment inherits nothing from the caller",
         sorted(_env), sorted(["GIT_DIR", "HOME", "GIT_CONFIG_NOSYSTEM", "GIT_CONFIG_GLOBAL",
                               "GIT_ATTR_NOSYSTEM", "GIT_TERMINAL_PROMPT", "PATH"]))
    case("merge-delta r2 (pure): ...and no PATH is no PATH, never the caller's",
         "PATH" in isolated_env("/g", "/h", None), False)
    case("merge-delta r1 Claude M1 (pure): merge-tree runs with no tree attribute source",
         merge_tree_argv("e0", "h1", "o1"),
         ["--attr-source=e0",
          "merge-tree", "--write-tree", "--name-only", "--no-messages", "-z", "h1", "o1"])

    # ⛔ merge-delta r4 Codex BLOCKER — the FULL CLI over a repository holding `lib/a\n.ts` AND
    # `lib/a\r.ts`, only the LF one edited after the round. Text-mode capture read both as
    # `lib/a\n.ts`, the unchanged CR entry won, and `main` said ok, rc 0. `main` runs in-process with
    # `ROOT` pointed at the fixture; the gate's own inputs (`scripts/`, `docs/superpowers/`) are
    # UNTRACKED links to this checkout's, so no diff the gate reads contains them. `lib/caf\xe9.ts`
    # rides along for r4 Codex M2: the branch-level readers raised on it.
    _cli = tempfile.mkdtemp(prefix="crr426-cli-")
    _real_root = ROOT
    _LF, _CR, _E9 = "lib/a\n.ts", "lib/a\r.ts", "lib/caf\udce9.ts"

    def _c(*a: str) -> subprocess.CompletedProcess:
        return _g("-C", _cli, *a)

    def _blob_of(text: str) -> str:
        return subprocess.run(["git", "-C", _cli, "hash-object", "-w", "--stdin"], input=text.encode(),
                              capture_output=True).stdout.decode().strip()

    def _verdict_at(head: str) -> None:
        _vd = pathlib.Path(_cli, "docs/reviews/verdicts")
        _vd.mkdir(parents=True, exist_ok=True)
        pathlib.Path(_cli, "docs/reviews/codex").mkdir(parents=True, exist_ok=True)
        pathlib.Path(_cli, "docs/reviews/codex/m-r1-codex.md").write_text("VERDICT\n", encoding="utf-8")
        (_vd / "m-r1-codex.verdict.json").write_text(
            json.dumps({"gate_ran": True, "head": head, "dirty": {}}), encoding="utf-8")
        _c("add", "--", "docs/reviews")
        _c("commit", "-q", "-m", "the review round's record")

    def _quiet(fn) -> object:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return _or_raised(fn)

    try:
        _c("init", "-q", "-b", "master")
        pathlib.Path(_cli, "README.md").write_text("prose\n", encoding="utf-8")
        _c("add", "--", "README.md")
        _c("commit", "-q", "-m", "base")
        _cli_base = _c("rev-parse", "HEAD").stdout.strip()
        _c("checkout", "-q", "-b", "br")
        os.symlink(_real_root / "scripts", pathlib.Path(_cli, "scripts"))
        pathlib.Path(_cli, "docs").mkdir()
        os.symlink(_real_root / "docs" / "superpowers", pathlib.Path(_cli, "docs", "superpowers"))
        _ok = _blob_of("reviewed\n")
        for _n in (_LF, _CR, _E9):
            _c("update-index", "--add", "--cacheinfo", f"100644,{_ok},{_n}")
        _c("commit", "-q", "-m", "the reviewed commit")
        _cli_r = _c("rev-parse", "HEAD").stdout.strip()
        _c("update-index", "--cacheinfo", f"100644,{_blob_of('UNREVIEWED')},{_LF}")
        _c("commit", "-q", "-m", "an unreviewed edit to the LF-named file only")
        _cli_e = _c("rev-parse", "HEAD").stdout.strip()
        globals()["ROOT"] = pathlib.Path(_cli)
        case("merge-delta r4 M2: `changed_paths` keeps a CR, an LF and a raw 0xe9 byte apart",
             _or_raised(lambda: sorted(p for p in changed_paths(_cli_base) if p.startswith("lib/"))),
             sorted([_LF, _CR, _E9]))
        case("merge-delta r4 M2: ...and against the reviewed commit, only the edited LF name",
             _or_raised(lambda: changed_paths(_cli_r)), [_LF])
        case("merge-delta r4 M2: `added_paths` keeps a CR, an LF and a raw 0xe9 byte apart",
             _or_raised(lambda: sorted(p for p in added_paths("master") if p.startswith("lib/"))),
             sorted([_LF, _CR, _E9]))
        case("merge-delta r4 M2: ...and against the reviewed commit, nothing was added",
             _or_raised(lambda: added_paths(_cli_r)), [])
        case("merge-delta r4 BLOCKER: the full CLI charges the edited LF name beside a CR twin",
             _verdict_at(_cli_r) or _quiet(lambda: main(["--base", "master"])), 1)
        case("merge-delta r4 BLOCKER control: a round at the edited commit clears the same tree",
             _verdict_at(_cli_e) or _quiet(lambda: main(["--base", _cli_base])), 0)
    finally:
        globals()["ROOT"] = _real_root
        shutil.rmtree(_cli, ignore_errors=True)
    shutil.rmtree(_tmp, ignore_errors=True)

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
