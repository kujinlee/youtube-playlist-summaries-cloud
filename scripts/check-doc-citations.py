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
⛔ **EVERY FIGURE BELOW IS DATED AND CARRIES THE COMMAND THAT PRODUCED IT. Re-derive; do not trust.**
These numbers have now been wrong TWICE for the same reason — measured, then the rule changed
underneath them (`md` joined the extensions; the suffix exemption arrived; then r1-codex widened the
grammar again) and nobody re-took them. Both times every CONCLUSION survived and not one NUMBER did.
Re-derive by IMPORTING this module, never by copying its regex into a scratch script: that copy is
how they drifted the first time.

    measured 2026-10-15 against this module, over `docs/**/*.md` and the last 40 commits of
    origin/master, by importing `CITE`, `in_scope`, `resolve` and `violations` directly.

⚠ **THE CORPUS FIGURES CANNOT BE EXACT, AND THE REASON IS STRUCTURAL rather than fixable.** The
backlog row and dashboard entry that quote these same numbers live *inside* `docs/`, so every commit
that records them adds citations to the corpus being counted. r2 found the absolute counts had already moved by 12 between being measured and being
written down. They are therefore stated as *approximately*, with the shape they establish — that
reviews dominate the corpus by an order of magnitude, and that the living-corpus rate is far too
high for a blocking gate — which is what the scope decision actually rests on. The PR-window
figure does NOT have this property and reproduces exactly.

  (1) `docs/reviews/` IS EXCLUDED — **~26,350 of ~27,250** citations under `docs/`, **96.7%**.
      Reviews are point-in-time artifacts; they deliberately carry no anchor header and nobody
      navigates *to* a goal through them.
  (2) `*.md` ONLY, which is row 49's own wording. Generated explainer pages under
      `docs/explainers/*.html` are dated snapshots of the same kind.
  (3) ADDED LINES ONLY. Over the living corpus the rule fires **~111 times on ~895 pathed
      citations (12.4%)** — overwhelmingly historical: ADR-0007 citing `schema/*.sql` files that M4 promoted
      into migrations, and 2026-06 specs citing files that have since shrunk.

Over the last 40 commits: **10 firings, 0.25 per commit** (`check-reference-namespace` shipped at
0.50). All ten hand-classified as TRUE: eight blank lines, one citation into
`development-velocity.md:262` which is now a 70-line tombstone, and one `dist/index.mjs:145` whose
remedy is to write a path that resolves.

⚠ **WHAT THAT 0.25 IS NOT, and r1-codex was right to refuse the stronger claim.** Those ten are
resolved against TODAY's tree, so they measure *drift since the line was written*. Some of the cited
lines held content at the revision that introduced them — `git show 5128b99b:scripts/check-ci-watched.py | sed -n '860p'`
returns a `def main(...)` — so the gate would NOT have blocked those commits at the time. **0.25 is
the rate at which citations in the recent window are wrong NOW; it is not a prediction of how often
this gate refuses a pull request.** What the measurement establishes is the SCOPE decision — that
the whole corpus is unusable and added-lines-only is not — which is what it is used for here.

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

  --self-test  runs 37 cases over diff texts this file builds, with an injected resolver, so the
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
# ⛔ r1-codex LOW: the leading lookbehind is what stops a URL becoming a citation.
# `http://localhost:3000/lib/a.ts:2` previously matched `3000/lib/a.ts:2` — a nonexistent repo path
# beginning with a port number, which then FIRED. A citation may not continue a `:` or `/`.
# ⟳ r1-codex MEDIUM: `()` joins the path class for Next.js route groups (`app/(auth)/page.tsx`) and
# css/scss/mjs/cjs/toml join the extensions. Both were silent false NEGATIVES, which are invisible
# and which the success message was overstating.
CITE = re.compile(
    r"(?<![:/\w.-])`?([A-Za-z0-9_.@\[][A-Za-z0-9_.@()\[\]-]*/"
    r"(?:[A-Za-z0-9_.@()\[\]-]+/)*[A-Za-z0-9_.@()\[\]-]+"
    r"\.(?:ts|tsx|js|mjs|cjs|py|sh|sql|yml|yaml|json|toml|css|scss|md))`?:(\d+)\b"
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


def violations(path: str, diff_text: str, tracked: tuple[str, ...], read) -> list[str]:
    """Findings over ONE file's unified diff. PURE — no git, no filesystem.

    THE PATH IS GIVEN, NEVER PARSED, AND THAT IS THE WHOLE POINT. Three consecutive rounds produced
    a header-parsing defect, each introduced by the previous round's fix: a C-quoted non-ASCII path
    judged the file under the PREVIOUS scope (r1-codex); the `---` boundary added to fix that also
    matched `----`, which is a REMOVED markdown rule (r2); decoding C-quotes strictly, to make an
    unreachable branch reachable, then rejected the literal UTF-8 git emits under
    `core.quotePath=false` and skipped the file entirely (r2-codex). All three were FAIL-OPEN.

    That is this project's THRASHING signal, and its rule is to ask whether a redesign removes the
    class rather than fix a fourth instance. It does: `git diff --name-only -z` emits paths
    NUL-delimited and never quoted, so the caller knows each path exactly and hands it in. There is
    no header to misparse and no scope to leak.
    """
    found: list[str] = []
    for line in diff_text.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        for match in CITE.finditer(line[1:]):
            cited, raw_line = match.group(1), int(match.group(2))
            lines, how = resolve(cited, tracked, read)
            if lines is None:
                found.append(f"{path}: `{cited}:{raw_line}` does not resolve — {how}")
                continue
            if raw_line < 1 or raw_line > len(lines):
                found.append(f"{path}: `{cited}:{raw_line}` is outside the file ({len(lines)} lines)")
                continue
            if not lines[raw_line - 1].strip():
                found.append(f"{path}: `{cited}:{raw_line}` is a blank line — "
                             f"a reader following it lands on nothing")
    return found


def changed_files(base: str, root: pathlib.Path) -> tuple[str, ...]:
    """Paths changed against `base`, NUL-delimited so git never quotes or escapes them.

    This is the half that makes header parsing unnecessary. Raises on a git failure.
    """
    r = subprocess.run(["git", "-C", str(root), "diff", "--name-only", "-z", base],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git diff --name-only {base} failed: {r.stderr.strip()[:200]}")
    return tuple(f for f in r.stdout.split("\0") if f)


def file_diff(base: str, root: pathlib.Path, path: str) -> str:
    """One file's unified diff against `base`. Raises on a git failure."""
    r = subprocess.run(["git", "-C", str(root), "diff", "--unified=0", base, "--", path],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git diff for {path} failed: {r.stderr.strip()[:200]}")
    return r.stdout


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
    """37 cases. The count is declared in the module docstring and verified by running this."""
    passed = failed = 0

    def case(name: str, got, want=True) -> None:
        nonlocal passed, failed
        if got == want:
            passed += 1
        else:
            failed += 1
            # COLUMN 0, NO INDENT: `parse_fail_names` reads startswith("[FAIL] ") and slices [7:].
            print(f"[FAIL] {name}: got {got!r} want {want!r}", file=sys.stderr)

    world = {
        "lib/a.ts": ["const a = 1", "", "export default a"],
        "lib/html-doc/ensure.ts": ["x", "y", "z"],
        "app/api/html-doc/ensure.ts": ["x", "y", "z"],
        "docs/notes.md": ["# notes", "body"],
    }
    tracked = tuple(world)
    read = lambda p: world.get(p)  # noqa: E731
    def body(*added: str) -> str:
        return "\n".join(f"+{a}" for a in added)

    def first(f: list[str]) -> str:
        # r1 M2: never index [0] — a mutation that empties this must FAIL a case, not crash the suite.
        return f[0] if f else ""

    case("a blank cited line fires",
         len(violations("docs/x.md", body("see `lib/a.ts:2`"), tracked, read)) == 1)
    case("the blank message names the reader's experience",
         "lands on nothing" in first(violations("docs/x.md", body("`lib/a.ts:2`"), tracked, read)))
    case("a line past EOF fires",
         len(violations("docs/x.md", body("`lib/a.ts:99`"), tracked, read)) == 1)
    case("the out-of-range message states the file length",
         "3 lines" in first(violations("docs/x.md", body("`lib/a.ts:99`"), tracked, read)))
    case("an unresolvable path fires",
         len(violations("docs/x.md", body("`lib/gone.ts:1`"), tracked, read)) == 1)
    case("a populated cited line is silent",
         violations("docs/x.md", body("`lib/a.ts:1`"), tracked, read) == [])
    case("line 3 (last line) is in range",
         violations("docs/x.md", body("`lib/a.ts:3`"), tracked, read) == [])
    case("a line number of 0 fires rather than reading the last line",
         len(violations("docs/x.md", body("`lib/a.ts:0`"), tracked, read)) == 1)

    case("a readable file that is NOT in the tracked list still resolves",
         violations("docs/x.md", body("`lib/a.ts:1`"), (), read) == [])
    case("...and the same path with a blank cited line still fires, so it is not passing blindly",
         len(violations("docs/x.md", body("`lib/a.ts:2`"), (), read)) == 1)

    case("a unique multi-segment suffix resolves and is silent",
         violations("docs/x.md", body("`html-doc/ensure.ts:1`"),
                    ("lib/html-doc/ensure.ts",), read) == [])
    case("an AMBIGUOUS suffix FIRES rather than being skipped",
         len(violations("docs/x.md", body("`html-doc/ensure.ts:1`"), tracked, read)) == 1)
    case("the ambiguous message says how many matched",
         "ambiguous: 2" in first(violations("docs/x.md", body("`html-doc/ensure.ts:1`"),
                                            tracked, read)))
    case("a suffix match still range-checks",
         len(violations("docs/x.md", body("`html-doc/ensure.ts:99`"),
                        ("lib/html-doc/ensure.ts",), read)) == 1)

    # scope is a predicate the caller applies to git's own NUL-delimited file list, so a scope leak
    # is impossible by construction and these assert the predicate directly.
    case("docs/reviews/ is out of scope", in_scope("docs/reviews/r.md"), False)
    case("a generated .html page is out of scope", in_scope("docs/explainers/p.html"), False)
    case("a non-docs path is out of scope", in_scope("scripts/x.md"), False)
    case("a docs/ root .md IS in scope", in_scope("docs/backlog.md"), True)
    case("a nested docs .md IS in scope", in_scope("docs/adr/0001-x.md"), True)
    case("a unicode docs path IS in scope — git hands it over unquoted via -z",
         in_scope("docs/e\u0301\t.md"), True)

    case("a REMOVED line is not examined",
         violations("docs/x.md", "-see `lib/a.ts:2`", tracked, read) == [])
    case("a context line is not examined",
         violations("docs/x.md", " see `lib/a.ts:2`", tracked, read) == [])
    case("a +++ header inside the body is never read as content",
         violations("docs/x.md", "+++ b/lib/a.ts:2", tracked, read) == [])
    case("a removed `---` horizontal rule is inert, not a boundary",
         len(violations("docs/x.md", "----\n" + body("`lib/a.ts:99`"), tracked, read)) == 1)

    case("backticks are optional",
         len(violations("docs/x.md", body("see lib/a.ts:2 here"), tracked, read)) == 1)
    case("a [param] path segment parses",
         len(violations("docs/x.md", body("`app/[id]/r.ts:1`"), tracked, read)) == 1)
    case("two citations on one line are both examined",
         len(violations("docs/x.md", body("`lib/a.ts:2` and `lib/a.ts:99`"), tracked, read)) == 2)
    case("a bare filename with no directory is NOT a citation",
         violations("docs/x.md", body("`a.ts:2`"), tracked, read) == [])
    case("a docs/*.md target can itself be cited",
         violations("docs/x.md", body("`docs/notes.md:1`"), tracked, read) == [])
    case("...and a BAD markdown target fires, so the form is really examined",
         len(violations("docs/x.md", body("`docs/notes.md:9`"), tracked, read)) == 1)
    case("a URL is not a citation, so its port cannot become a path",
         violations("docs/x.md", body("http://localhost:3000/lib/a.ts:2"), tracked, read) == [])
    case("a citation wrapped in prose parentheses does not capture the bracket",
         violations("docs/x.md", body("(lib/a.ts:1)"), tracked, read) == [])

    # --- main() is DRIVEN over a constructed world (ADR-0014), to every exit code ---------------
    import contextlib
    import io

    def drive(changed, diff_text, reader, git_ok: bool = True) -> int:
        def fetch_changed(_b, _r):
            if not git_ok:
                raise RuntimeError("git diff --name-only origin/nope failed: unknown revision")
            return changed
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return main([], root=pathlib.Path("/nonexistent"),
                        fetch_changed=fetch_changed,
                        fetch_file_diff=lambda _b, _r, _p: diff_text,
                        fetch_tracked=lambda _r: tracked,
                        make_reader=lambda _r: reader)

    def raises(_p):
        raise PermissionError("fixture is unreadable")

    case("main() returns 0 over a clean world",
         drive(("docs/x.md",), body("`lib/a.ts:1`"), read) == 0)
    case("main() returns 1 when a citation has drifted",
         drive(("docs/x.md",), body("`lib/a.ts:2`"), read) == 1)
    case("⛔ main() returns 2 — CANNOT RUN — when git cannot be reached, never 0",
         drive((), "", read, git_ok=False) == 2)
    # ⛔ r2-codex Medium: this handler had NO witness — replacing its `return 2` with `return 0`
    # left 40/40 green. An existing-but-unreadable cited file is CANNOT RUN, never a finding.
    case("⛔ main() returns 2 when a cited file exists but cannot be READ",
         drive(("docs/x.md",), body("`lib/a.ts:1`"), raises) == 2)
    case("...and an out-of-scope changed file is never diffed at all",
         drive(("scripts/x.md",), body("`lib/a.ts:2`"), read) == 0)

    print(f"{passed}/{passed + failed} passed")
    return 1 if failed else 0


def main(
    argv: list[str],
    root: pathlib.Path = ROOT,
    fetch_changed=changed_files,
    fetch_file_diff=file_diff,
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
        scoped = [f for f in fetch_changed(args.base, root) if in_scope(f)]
        tracked = fetch_tracked(root)
    except (RuntimeError, OSError) as exc:
        print(f"CANNOT RUN — {exc}\n  Treat this as NOT RUN, never as a pass.", file=sys.stderr)
        return 2

    read = make_reader(root)
    found: list[str] = []
    try:
        for scoped_path in scoped:
            found += violations(scoped_path,
                                fetch_file_diff(args.base, root, scoped_path), tracked, read)
    except (RuntimeError, OSError) as exc:
        print(f"CANNOT RUN — {exc}\n  Treat this as NOT RUN, never as a pass.", file=sys.stderr)
        return 2

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
