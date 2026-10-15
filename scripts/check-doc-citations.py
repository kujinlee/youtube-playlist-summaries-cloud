#!/usr/bin/env python3
"""A `path:line` citation that has drifted sends the reader into a different function.

WHY THIS EXISTS
---------------
`docs/backlog.md` row 49, filed 2026-08-17 with the measurement that argues it. One document,
`docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md`, carried EIGHT wrong citations:

  * round 3 (Codex) found one — `helpers/cloud.ts:132`, actually `:131`;
  * v4 fixed that one and rechecked none of its neighbours;
  * a mechanical sweep of all 19 citations then found SIX more (`spendLedgerTotal` 157->153,
    `cloudVideoRecord` 468->471, `localVideoRecord` 473->476, `seedVideo` 378->296,
    `seedFreshModel` 78->79, `putBudget` 21->18);
  * the round-4 Claude half found a seventh the sweep missed, and round 5 an eighth.

⭐ **Two independent sweeps each missed what the other caught.** That is the argument: this is not
a care problem, and more review does not fix it. `seedVideo` shows the cost — 82 lines off lands an
implementer inside a different function, and nothing about the wrong number looks wrong.

The eight instances were corrected by hand when they were found. This ratchet is what stops the
ninth.

WHY IT CAN BE A GATE, AND ON WHICH CORPUS
-----------------------------------------
Scope was chosen BY MEASUREMENT over the last 40 commits of `origin/master`, not by taste. Each
axis below was measured before it was adopted:

  (1) `docs/reviews/` IS EXCLUDED. It holds **32,004 of the 32,901** citations in `docs/` — 97.3%.
      Reviews are point-in-time artifacts; they deliberately carry no anchor header and nobody
      navigates *to* a goal through them. A citation inside one is a record of what was true that
      day, not a pointer someone is meant to follow.
  (2) `*.md` ONLY, which is row 49's own wording. Generated explainer pages under
      `docs/explainers/*.html` are dated snapshots, and six of the seventeen raw firings were in
      them.
  (3) ADDED LINES ONLY. Over the living corpus the rule fires **110 times on 897 pathed
      citations (12.3%)** — overwhelmingly historical: ADR-0007 citing `schema/*.sql` files that
      M4 promoted into migrations, and 2026-06 specs citing files that have since shrunk. A
      blocking gate over that corpus is unusable, and row 49 does not ask for it.

With all three: **9 firings over 40 commits, 0.23 per commit.** (`check-reference-namespace`
shipped at 0.50.) All nine were hand-classified as TRUE positives — six blank lines in
`check-ci-watched.py`, `gen-backlog-page.py`, `portable-practices.md` and `dev-process.md`, and one
citation into `development-velocity.md:262`, a file that is now a 70-line tombstone.

⛔ **EVERY FIGURE ABOVE WAS RE-DERIVED BY IMPORTING THIS MODULE, after r1 H2 found that none of the
first three reproduced.** They had been measured against an earlier rule and never re-taken when the
rule changed — `md` joined the extension list and the suffix exemption arrived after the numbers
were written. The conclusions all survived; not one of the numbers did. Re-measure here by running
the module, never by copying its regex into a scratch script, which is how they drifted.

THE ONE EXEMPTION, DERIVED FROM THE FIRINGS RATHER THAN IMAGINED
-----------------------------------------------------------------
Five of the seventeen raw firings were a single false-positive class: documents cite a path
SUFFIX — `html-doc/ensure.ts:66`, `dig/[sectionId]/route.ts:47` — not a repo-relative path. Each
of those five resolved to **exactly one** tracked file (`lib/html-doc/ensure.ts`,
`app/api/videos/[id]/dig/[sectionId]/route.ts`, ...). So a citation that is not a path from the
repo root is resolved as a suffix, and passes when exactly one tracked file ends with it.

⛔ **An AMBIGUOUS suffix FIRES — it is not skipped.** Two files ending the same way means the
reader cannot tell which was meant, which is the defect this guard exists for, in its purest form.
Per `CLAUDE.md`: *"cannot run" is a FAILURE, never a pass.*

WHAT IT ASSERTS
---------------
For every `path:line` on an ADDED line of a scoped file, the cited line must exist and carry
content. It does NOT check that the line declares the symbol named nearby — row 49 describes that,
and it needs a language-aware parser per file type. The blank-line and out-of-range shapes are what
the eight measured instances actually looked like (`:66` was a mid-docstring blank; `:157` likewise),
and they are decidable without one.

WHAT IT IS BLIND TO, STATED RATHER THAN DISCOVERED LATER
--------------------------------------------------------
  * **RANGES.** `file.ts:10-20` is read as a citation of line 10; the end of the range is never
    checked. 372 of 897 living citations carry a range (r1 L1), so this is the larger half of the
    corpus by count, and a range whose END has drifted passes silently.
  * **FENCED CODE BLOCKS are invisible BY CONSTRUCTION.** The diff is read at `--unified=0`, which
    carries no context lines, so there is no way to know whether an added line sits inside a fence.
    A document quoting example output containing `path.ts:12` fires. Measured latent rate: 40 of 896
    (4.5%) — none in the 40-commit window, which is why it is recorded rather than worked around.
    Fixing it means reading the file rather than the diff, which is a different guard.

FAILS IF
--------
  * an added line in a scoped file cites a path that resolves to no tracked file, or to more than
    one by suffix;
  * the cited line number is outside the resolved file;
  * the cited line is blank or whitespace-only;
  * `git` cannot be run, or the base ref does not resolve — which is CANNOT RUN (rc=2), never a pass.

  --self-test  runs 32 cases over diff texts this file builds, with an injected resolver, so the
               rule is exercised with no repository present.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# A citation carries at least one directory separator — a bare `route.ts:12` names no path and is
# measured at 1,266 occurrences in living docs, none of them resolvable by construction.
CITE = re.compile(
    r"`?((?:[A-Za-z0-9_.@\[\]-]+/)+[A-Za-z0-9_.@\[\]-]+"
    r"\.(?:ts|tsx|js|py|sh|sql|yml|yaml|json|md))`?:(\d+)\b"
)

SCOPE_PREFIX = "docs/"
EXCLUDED_PREFIX = "docs/reviews/"


def in_scope(path: str) -> bool:
    """A scoped file is a living Markdown document under docs/, reviews excluded."""
    return (
        path.startswith(SCOPE_PREFIX)
        and path.endswith(".md")
        and not path.startswith(EXCLUDED_PREFIX)
    )


def resolve(path: str, tracked: tuple[str, ...], read):
    """Resolve a cited path to (lines, how) or (None, why).

    PURE given `tracked` and `read` — both injected, so the rule runs with no repository.

    ⛔ THE FILESYSTEM IS THE EXISTENCE ORACLE, NOT `git ls-files`. r1 H1: an earlier version asked
    `path in tracked`, so a citation into a real, readable but UNTRACKED file was reported
    unresolvable — reproduced against `.claude/skills/shared/explainer-delivery.md`, 346 lines, which
    is where this project's own harness lives. `tracked` is used ONLY to search for a suffix match,
    which is a search problem and genuinely needs a file list.

    `read` returns None for a path it cannot produce lines for, which is also why a tracked-but-
    deleted file now FIRES instead of raising FileNotFoundError out of a pure function (r1 M1).
    """
    lines = read(path)
    if lines is not None:
        return lines, "exact"
    suffix_matches = [f for f in tracked if f.endswith("/" + path)]
    if len(suffix_matches) > 1:
        return None, f"ambiguous: {len(suffix_matches)} tracked files end with it"
    if len(suffix_matches) == 1:
        lines = read(suffix_matches[0])
        if lines is not None:
            return lines, "suffix"
        return None, f"the one suffix match ({suffix_matches[0]}) could not be read"
    return None, "no such file, and no tracked file ends with it"


def violations(diff_text: str, tracked: tuple[str, ...], read) -> list[str]:
    """Findings over a unified diff. PURE — no git, no filesystem.

    `tracked` is the tracked-file list and `read` maps a path to its lines, so a case can build
    its own world and the rule is testable without a repository.
    """
    found: list[str] = []
    current: str | None = None
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        if current is None or not in_scope(current):
            continue
        for match in CITE.finditer(line[1:]):
            path, raw_line = match.group(1), int(match.group(2))
            lines, how = resolve(path, tracked, read)
            if lines is None:
                found.append(f"{current}: `{path}:{raw_line}` does not resolve — {how}")
                continue
            if raw_line < 1 or raw_line > len(lines):
                found.append(
                    f"{current}: `{path}:{raw_line}` is outside the file "
                    f"({len(lines)} lines)"
                )
                continue
            if not lines[raw_line - 1].strip():
                found.append(
                    f"{current}: `{path}:{raw_line}` is a blank line — "
                    f"a reader following it lands on nothing"
                )
    return found


def added_diff(base: str, root: pathlib.Path) -> str:
    """The unified diff of `base`..worktree. Raises on a git failure — never returns ''."""
    result = subprocess.run(
        ["git", "-C", str(root), "diff", "--unified=0", base],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git diff {base} failed: {result.stderr.strip()[:200]}")
    return result.stdout


def tracked_files(root: pathlib.Path) -> tuple[str, ...]:
    """Every tracked path. Raises on a git failure — an empty list would pass about nothing."""
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files"], capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git ls-files failed: {result.stderr.strip()[:200]}")
    files = tuple(f for f in result.stdout.split("\n") if f)
    if not files:
        raise RuntimeError("git ls-files returned nothing — refusing to pass over an empty tree")
    return files


def _reader(root: pathlib.Path):
    """A reader that answers None rather than raising, so a missing file is a FINDING and not a
    traceback out of a pure function. ⛔ It does NOT swallow the distinction: None reaches
    `resolve`, which reports precisely why the path did not resolve."""
    def read(path: str) -> "list[str] | None":
        target = root / path
        if not target.is_file():
            return None
        return target.read_text(encoding="utf-8", errors="replace").splitlines()
    return read


def self_test() -> int:
    """32 cases. The count is declared in the module docstring and verified by running this."""
    passed = failed = 0

    def case(name: str, got, want=True) -> None:
        nonlocal passed, failed
        if got == want:
            passed += 1
        else:
            failed += 1
            # ⛔ COLUMN 0, NO INDENT. `check-plan-code`'s `parse_fail_names` reads a red case
            # with startswith("[FAIL] ") and slices [7:]; an indented line attributes to
            # nothing, and the whole manifest for this file reads as unattributable.
            print(f"[FAIL] {name}: got {got!r} want {want!r}", file=sys.stderr)

    world = {
        "lib/a.ts": ["const a = 1", "", "export default a"],
        "lib/html-doc/ensure.ts": ["x", "y", "z"],
        "app/api/html-doc/ensure.ts": ["x", "y", "z"],
        "docs/notes.md": ["# notes", "body"],
    }
    tracked = tuple(world)
    # answers None for a path the world does not hold — the same contract as `_reader`, so the
    # cases exercise the shape the shipped reader actually has (r1 H1/M1).
    read = lambda p: world.get(p)  # noqa: E731
    def diff(path: str, *added: str) -> str:
        return "\n".join([f"+++ b/{path}", *[f"+{a}" for a in added]])

    # --- the three failure shapes -------------------------------------------------------------
    case("a blank cited line fires",
         len(violations(diff("docs/x.md", "see `lib/a.ts:2`"), tracked, read)) == 1)
    # ⛔ r1 M2: NEVER index [0] here. Under the mutation that removes the blank clause this list is
    # empty, and an IndexError kills the whole suite at case 2 — cases 3-32 never run, so that
    # mutation's "exclusive" attribution was an artifact of the crash rather than evidence.
    def first(findings: list[str]) -> str:
        return findings[0] if findings else ""

    case("the blank message names the reader's experience",
         "lands on nothing" in first(violations(diff("docs/x.md", "`lib/a.ts:2`"), tracked, read)))
    case("a line past EOF fires",
         len(violations(diff("docs/x.md", "`lib/a.ts:99`"), tracked, read)) == 1)
    case("the out-of-range message states the file length",
         "3 lines" in first(violations(diff("docs/x.md", "`lib/a.ts:99`"), tracked, read)))
    case("an unresolvable path fires",
         len(violations(diff("docs/x.md", "`lib/gone.ts:1`"), tracked, read)) == 1)
    # ⛔ r1 H1: the filesystem is the oracle. A real, readable file that git does not track must
    # resolve — `.claude/` is where this project's harness lives and none of it is tracked.
    case("a readable file that is NOT in the tracked list still resolves",
         violations(diff("docs/x.md", "`lib/a.ts:1`"), (), read) == [])
    case("...and the same path with a blank cited line still fires, so it is not passing blindly",
         len(violations(diff("docs/x.md", "`lib/a.ts:2`"), (), read)) == 1)
    case("a populated cited line is silent",
         violations(diff("docs/x.md", "`lib/a.ts:1`"), tracked, read) == [])
    case("line 3 (last line) is in range",
         violations(diff("docs/x.md", "`lib/a.ts:3`"), tracked, read) == [])
    # ⚠ without the lower bound, `:0` indexes lines[-1] and silently reports the LAST line as the
    # cited one — silent and wrong, which is worse than the drift this guard exists for.
    case("a line number of 0 fires rather than reading the last line",
         len(violations(diff("docs/x.md", "`lib/a.ts:0`"), tracked, read)) == 1)

    # --- the suffix exemption, and its refusal -------------------------------------------------
    # ⚠ the suffix MUST carry a directory separator, or it is not a citation at all and the case
    # passes for an ambient reason. The first version of this case used `a.ts:1` and tested nothing.
    case("a unique multi-segment suffix resolves and is silent",
         violations(diff("docs/x.md", "`html-doc/ensure.ts:1`"),
                    ("lib/html-doc/ensure.ts",), read) == [])
    case("⛔ an AMBIGUOUS suffix FIRES rather than being skipped",
         len(violations(diff("docs/x.md", "`html-doc/ensure.ts:1`"), tracked, read)) == 1)
    case("the ambiguous message says how many matched",
         "ambiguous: 2" in first(violations(diff("docs/x.md", "`html-doc/ensure.ts:1`"), tracked, read)))
    case("a suffix match still range-checks",
         len(violations(diff("docs/x.md", "`html-doc/ensure.ts:99`"),
                        ("lib/html-doc/ensure.ts",), read)) == 1)

    # --- scope ---------------------------------------------------------------------------------
    case("docs/reviews/ is excluded",
         violations(diff("docs/reviews/r.md", "`lib/a.ts:2`"), tracked, read) == [])
    case("a generated .html page is excluded",
         violations(diff("docs/explainers/p.html", "`lib/a.ts:2`"), tracked, read) == [])
    case("a non-docs path is excluded",
         violations(diff("scripts/x.md", "`lib/a.ts:2`"), tracked, read) == [])
    case("a docs/ root .md IS in scope",
         len(violations(diff("docs/backlog.md", "`lib/a.ts:2`"), tracked, read)) == 1)
    case("a nested docs .md IS in scope",
         len(violations(diff("docs/adr/0001-x.md", "`lib/a.ts:2`"), tracked, read)) == 1)
    case("a REMOVED line is not examined",
         violations("+++ b/docs/x.md\n-see `lib/a.ts:2`", tracked, read) == [])
    case("a context line is not examined",
         violations("+++ b/docs/x.md\n see `lib/a.ts:2`", tracked, read) == [])
    case("the +++ header itself is never treated as an added line",
         violations("+++ b/docs/x.md", tracked, read) == [])

    # --- the citation grammar ------------------------------------------------------------------
    case("backticks are optional",
         len(violations(diff("docs/x.md", "see lib/a.ts:2 here"), tracked, read)) == 1)
    case("a [param] path segment parses",
         len(violations(diff("docs/x.md", "`app/[id]/r.ts:1`"), tracked, read)) == 1)
    case("two citations on one line are both examined",
         len(violations(diff("docs/x.md", "`lib/a.ts:2` and `lib/a.ts:99`"), tracked, read)) == 2)
    case("a bare filename with no directory is NOT a citation",
         violations(diff("docs/x.md", "`a.ts:2`"), tracked, read) == [])
    case("a docs/*.md target can itself be cited",
         violations(diff("docs/x.md", "`docs/notes.md:1`"), tracked, read) == [])

    # --- `read` is CONSULTED, not captured ------------------------------------------------------
    # ⛔ check-fixture-variation refused this suite until these existed: every other case passes the
    # same `read`, so none of them could tell it from a constant, and any clause reading it was
    # unguarded. These two differ ONLY in the injected reader, at one identical citation.
    _blank_at_1 = lambda p: ["", "content"]   # noqa: E731
    _content_at_1 = lambda p: ["content", ""]  # noqa: E731
    case("the verdict follows the INJECTED reader — blank at line 1 fires",
         len(violations(diff("docs/x.md", "`lib/a.ts:1`"), ("lib/a.ts",), _blank_at_1)) == 1)
    case("...and the SAME citation is silent under a reader whose line 1 has content",
         violations(diff("docs/x.md", "`lib/a.ts:1`"), ("lib/a.ts",), _content_at_1) == [])

    # --- main() is DRIVEN over a constructed world (ADR-0014) ----------------------------------
    # ⛔ Not pinned as identity debt: 28 guards already are, and a new one should not join them.
    # These three reach every exit code main() can return, with no git binary and no repository.
    import contextlib
    import io

    def drive(diff_text: str, tracked_files_, reader_, base_ok: bool = True) -> int:
        def fetch_diff(_base, _root):
            if not base_ok:
                raise RuntimeError("git diff origin/nope failed: unknown revision")
            return diff_text
        buf_out, buf_err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
            return main([], root=pathlib.Path("/nonexistent"),
                        fetch_diff=fetch_diff,
                        fetch_tracked=lambda _root: tracked_files_,
                        make_reader=lambda _root: reader_)

    case("main() returns 0 over a clean world",
         drive(diff("docs/x.md", "`lib/a.ts:1`"), tracked, read) == 0)
    case("main() returns 1 when a citation has drifted",
         drive(diff("docs/x.md", "`lib/a.ts:2`"), tracked, read) == 1)
    case("⛔ main() returns 2 — CANNOT RUN — when git cannot be reached, never 0",
         drive("", tracked, read, base_ok=False) == 2)

    print(f"{passed}/{passed + failed} passed")
    return 1 if failed else 0


def main(
    argv: list[str],
    root: pathlib.Path = ROOT,
    fetch_diff=added_diff,
    fetch_tracked=tracked_files,
    make_reader=_reader,
) -> int:
    """ADR-0014: the world arrives as defaulted parameters, so a case can drive this whole
    function — CANNOT RUN included — without a repository or a git binary."""
    parser = argparse.ArgumentParser(
        description="A drifted `path:line` citation sends the reader into different code.")
    parser.add_argument("--base", default="origin/master",
                        help="ref to diff against (default: origin/master)")
    parser.add_argument("--self-test", action="store_true", help="run the cases and exit")
    # r1 L3: without this the guard resolves ROOT from __file__ and silently audits its OWN
    # repository whatever directory it is invoked from — which cost the reviewer one invalid
    # experiment before they noticed the subject was not the tree they had built.
    parser.add_argument("--root", default=None,
                        help="repository to audit (default: the one this script lives in)")
    args = parser.parse_args(argv)
    if args.root:
        root = pathlib.Path(args.root).resolve()

    if args.self_test:
        return self_test()

    try:
        diff_text = fetch_diff(args.base, root)
        tracked = fetch_tracked(root)
    except (RuntimeError, OSError) as exc:
        print(f"CANNOT RUN — {exc}\n  Treat this as NOT RUN, never as a pass.", file=sys.stderr)
        return 2

    found = violations(diff_text, tracked, make_reader(root))
    if found:
        print(f"⛔ {len(found)} drifted citation(s) added:\n", file=sys.stderr)
        for item in found:
            print(f"  {item}", file=sys.stderr)
        print(
            "\nA `path:line` that has drifted sends a reader into different code, and nothing "
            "about the wrong number looks wrong. Re-read the file and correct the line, or drop "
            "the line number.",
            file=sys.stderr,
        )
        return 1

    print("doc citations OK — every `path:line` added under docs/ resolves to a real line")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
