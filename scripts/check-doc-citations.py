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
    ⟳ RE-TAKEN 2026-10-15 after the r4 redesign, the same way. Every figure reproduced — four
    exactly and the fifth within the corpus's own movement — which is the first time these numbers
    have survived a change to the rule, because the half they depend on (`CITE` and `resolve`) is
    the half the redesign did not touch.
    ⛔ AND THE HISTORICAL FIGURE NEEDS TWO INJECTIONS, NOT ONE. `violations` takes the document,
    not the diff, so a retrospective run cannot read content out of a historical patch any more.
    ⟳ r4 L2 CORRECTED THIS PARAGRAPH, which recorded the method as *"injecting a
    `git show <commit>:<path>` reader — no checkout"*. That recipe does NOT reproduce its own
    number: measured, it gives **6 firings across 2 commits and 78 RuntimeErrors**, because
    `file_diff` and `changed_files` take a single `base` and always diff it against the WORKTREE —
    they cannot express a commit-to-parent diff at all. The second injection is mandatory: a
    two-ref diff AND the blob reader. With both, the figure is EXACT — 10 firings over 40 commits,
    the same four commits — and reproduces under `rev-list -n 40`, `--no-merges` and
    `--first-parent` alike. ⚠ A recipe that under-reports by 4 while converting most of the corpus
    to CANNOT RUN is worse than no recipe, because the next reader trusts it and sees a smaller
    number.

⚠ **THE CORPUS FIGURES CANNOT BE EXACT, AND THE REASON IS STRUCTURAL rather than fixable.** The
backlog row and dashboard entry that quote these same numbers live *inside* `docs/`, so every commit
that records them adds citations to the corpus being counted. r2 found the absolute counts had already moved by 12 between being measured and being
written down. They are therefore stated as *approximately*, with the shape they establish — that
reviews dominate the corpus by an order of magnitude, and that the living-corpus rate is far too
high for a blocking gate — which is what the scope decision actually rests on. The PR-window
figure does NOT have this property and reproduces exactly.

  (1) `docs/reviews/` IS EXCLUDED — **26,375 of 27,270** citations under `docs/`, **96.7%**
      (re-measured 2026-10-15; the ratio is stable, the absolute counts move every commit).
      Reviews are point-in-time artifacts; they deliberately carry no anchor header and nobody
      navigates *to* a goal through them.
  (2) `*.md` ONLY, which is row 49's own wording. Generated explainer pages under
      `docs/explainers/*.html` are dated snapshots of the same kind.
  (3) ADDED LINES ONLY. Over the living corpus the rule fires **111 times on 895 pathed
      citations (12.4%)** — reproduced exactly after the r4 redesign — overwhelmingly historical: ADR-0007 citing `schema/*.sql` files that M4 promoted
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
    checked. **369 of 895** living citations carry a range (41.2%; r1 L1 measured 372 of 897), so
    this is the larger half of the corpus by count, and a range whose END has drifted passes
    silently. ⚠ Re-derive this by walking `CITE.finditer` and testing whether each match is
    followed by `-<digit>`, NEVER with a range regex of your own: an independent one written while
    re-taking these figures returned **858 of 895 (95.9%)**, and the warning above says why — a
    copy of this grammar is how these numbers drifted the first time.
  * **FENCED CODE BLOCKS are not exempted — and as of the r4 redesign that is a CHOICE, not a
    constraint.** A document quoting example output containing `path.ts:12` fires. Measured latent
    rate 2026-10-15: **41 of 879 (4.7%)** over fence-BALANCED living documents, which is the
    population the original 40-of-896 figure used; over ALL living documents it is **56 of 895
    (6.3%)**, the difference being two documents with an odd number of fences. ⚠ The qualifier is
    not decoration — reading that 6.3% as drift from 4.5% was a method error made while re-taking
    these numbers, and caught only by measuring both. None in the 40-commit window either way.
    ⟳ The reason recorded here until 2026-10-15 was *"the diff is read at `--unified=0`, which
    carries no context lines, so there is no way to know whether an added line sits inside a
    fence — fixing it means reading the file rather than the diff, which is a different guard."*
    **The r4 redesign reads the file.** `violations()` now receives the whole document, so a fence
    scan is reachable right here. It is deliberately not implemented: it changes what the gate
    ASSERTS, and r4 was authorised as a redesign, not a scope change. Filed, with the measurement
    above as its argument. ⛔ Do not re-derive the old reason — it is no longer true of this code.

FAILS IF
--------
  * an added line in a scoped file cites a path that resolves to no tracked file, or to more than
    one by suffix;
  * the cited line number is outside the resolved file;
  * the cited line is blank or whitespace-only;
  * `git` cannot be run, or the base ref does not resolve — which is CANNOT RUN (rc=2), never a pass.

  --self-test  runs 74 cases. Most are over DOCUMENTS this file builds with an injected
               resolver, so the rule needs no repository; the hunk-header reader is exercised on
               diff texts, and four cases build a throwaway git repository because the properties
               they witness (NUL splitting, literal pathspecs, rename pairing) are git's.
"""
from __future__ import annotations

import argparse
import os
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


# ⛔ THE ONLY THING READ OUT OF A DIFF. Every content line in a unified diff carries a one-character
# prefix (`+`, `-`, or a space), so NO content line can begin at column 0 with `@@`. That makes
# header-versus-content a question of POSITION, which git guarantees, rather than a guess from a
# PREFIX, which it does not — and the prefix guess is what produced a High in all three rounds
# (`+++` the header against `+` plus an added line beginning `++` are the same four characters).
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


# Lines a unified diff emits that carry NO content. Measured 2026-10-15 against git by building
# each shape: a pure rename emits `similarity index` + `rename from/to`, a mode change emits
# `old mode` + `new mode`, and BOTH legitimately have no `@@` at all. Everything outside this list
# in a hunkless diff is output this function does not understand — see `added_lines`.
NO_CONTENT_LINE = (
    "diff --git", "index ", "old mode ", "new mode ", "similarity index ",
    "dissimilarity index ", "rename from ", "rename to ", "copy from ", "copy to ",
    "new file mode ", "deleted file mode ", "--- ", "+++ ", "\\ No newline",
)


def added_lines(diff_text: str) -> tuple[int, ...]:
    """The post-image line numbers this diff ADDS. PURE — no git, no filesystem, no content.

    ⛔ RAISES ValueError on a line that begins `@@` and does not parse, and the caller turns that
    into CANNOT RUN. Returning `()` there would read as "nothing to check" — the same fail-open
    direction as the three header defects this function exists to make impossible. Named as the new
    risk in the round-3 coordinator document BEFORE this was written, and case 1 of the suite.

    `@@ -a,b +c,d @@` adds c .. c+d-1. An omitted count means 1 (git's own default); `d == 0` is a
    pure deletion hunk and adds nothing, so `c` must NOT be included.
    """
    out: list[int] = []
    unexplained: list[str] = []
    for line in diff_text.splitlines():
        if not line.startswith("@@"):
            # ⛔ r4 H2 — A HUNKLESS DIFF OF A CHANGED FILE IS CANNOT RUN, NOT AN EMPTY CHANGE SET.
            # `git diff` reports `Binary files a/docs/x.md and b/docs/x.md differ` — with no `@@` at
            # all — for a document holding a single NUL byte, AND for a plain-ASCII document under a
            # one-line `docs/** -diff` in `.gitattributes` that anybody can commit. The caller's
            # `if not added: return []` then read that as nothing to check: rc=0 over a drifted
            # citation, with `docs/** text` as the adjacent control giving rc=1 on the same bytes.
            # ⚠ ALLOW-LIST, NOT A BLACKLIST OF `Binary files`: two no-hunk shapes are LEGITIMATE
            # (a pure rename, a mode change) and were measured, so anything OUTSIDE the measured
            # set is refused rather than anything inside a guessed set. An output shape nobody has
            # seen yet fails CLOSED.
            if line and not line.startswith(NO_CONTENT_LINE):
                unexplained.append(line)
            continue
        m = HUNK.match(line)
        if m is None:
            raise ValueError(f"unparsable hunk header: {line[:80]!r}")
        start = int(m.group(1))
        # ⚠ TWO PROPERTIES SHARE THIS LINE AND A MANIFEST ANCHOR CAN BE OCCUPIED ONCE. The entry
        # on it is `max(1, …)`, measured to redden exactly the two deletion-hunk cases. The
        # OMITTED-count property ("an OMITTED count means one line, not zero" — a single-line
        # addition is the commonest shape there is, so defaulting to 0 would skip almost
        # everything) is falsified by `0 if m.group(2) is None`, measured 2026-10-15 to redden 6
        # cases including its own. Stated here because the manifest cannot carry both.
        count = 1 if m.group(2) is None else int(m.group(2))
        out.extend(range(start, start + count))
    if not out and unexplained:
        raise ValueError(
            f"a diff with no hunk headers and {len(unexplained)} line(s) this rule does not "
            f"understand: {unexplained[0][:80]!r}")
    return tuple(out)


def violations(path: str, added: tuple[int, ...], doc_lines: list[str],
               tracked: tuple[str, ...], read) -> list[str]:
    """Findings over ONE document. PURE — no git, no filesystem, AND NO DIFF TEXT.

    THE PATH IS GIVEN AND SO IS THE CONTENT. Neither is parsed out of a diff, and that is the whole
    point. Four consecutive rounds produced a defect in code that read one or the other out of diff
    text, each introduced by the previous round's fix:

      * a C-quoted non-ASCII path judged the file under the PREVIOUS scope (r1-codex HIGH);
      * the `---` boundary added to fix that also matched `----`, a REMOVED markdown rule (r2 HIGH);
      * decoding C-quotes strictly then rejected the literal UTF-8 git emits under
        `core.quotePath=false` and skipped the file entirely (r2-codex HIGH);
      * `startswith("+++")` discarded an added markdown line beginning `++` (r3-codex HIGH).

    All four were FAIL-OPEN. The first three were answered by taking the path from
    `git diff --name-status -z`; the fourth is answered here, by taking the content from the
    DOCUMENT. `added` carries post-image line numbers from `added_lines()`, which reads only `@@`
    headers; `doc_lines` is the document itself, through the same reader the resolver uses.

    ⛔ A line number past the end of the document is CANNOT RUN, not a skip: git said that line was
    added and the document disagrees, so the two sources are not describing the same tree.
    """
    found: list[str] = []
    for n in added:
        if n < 1 or n > len(doc_lines):
            raise RuntimeError(
                f"{path}: git reports line {n} as added and the document has {len(doc_lines)} "
                f"lines — the diff and the file are not the same tree")
        for match in CITE.finditer(doc_lines[n - 1]):
            cited, raw_line = match.group(1), int(match.group(2))
            lines, how = resolve(cited, tracked, read)
            if lines is None:
                found.append(f"{path}: `{cited}:{raw_line}` does not resolve — {how}")
                continue
            # ⚠ `last_line` is NAMED so the two drift directions have separate anchors: widening
            # it hides a file that LOST its last line (r4 M7), and tightening the comparison below
            # to `>=` rejects a file's genuine last line. Both are real, both need an entry.
            last_line = len(lines)
            if raw_line < 1 or raw_line > last_line:
                found.append(f"{path}: `{cited}:{raw_line}` is outside the file ({len(lines)} lines)")
                continue
            if not lines[raw_line - 1].strip():
                found.append(f"{path}: `{cited}:{raw_line}` is a blank line — "
                             f"a reader following it lands on nothing")
    return found


def findings_for(path: str, source: "str | None", base: str, root: pathlib.Path,
                 tracked: tuple[str, ...], read, fetch_file_diff) -> list[str]:
    """One document: diff it, take the added line numbers, read the document, apply the rule.

    ONE orchestrator, called by `main()` and by both repository witnesses. A second copy of this
    sequence is how `check-vocabulary-collisions.py` describes this repository's most-measured
    defect — seventeen instances of one rule implemented twice and drifting.

    ⛔ A document with added lines that cannot be READ raises rather than returning no findings:
    git says the file has new content and the filesystem says there is no file, and "no findings"
    would report that disagreement as a pass.
    """
    added = added_lines(fetch_file_diff(base, root, path, source))
    if not added:
        return []
    doc_lines = read(path)
    if doc_lines is None:
        raise RuntimeError(
            f"{path}: git reports {len(added)} added line(s) and the document cannot be read")
    return violations(path, added, doc_lines, tracked, read)


def changed_files(base: str, root: pathlib.Path) -> tuple[tuple[str, "str | None"], ...]:
    """(path, source) for each change against `base`. NUL-delimited, so git never quotes.

    `source` is the pre-rename path when git detected one, else None. ⛔ r3-codex: without it a
    pure rename reports every citation in the moved document as NEWLY ADDED, because the per-file
    pathspec excluded the source and git could not match the halves — which contradicts the
    added-lines-only contract this guard rests on.

    This is the half that makes header parsing unnecessary. Raises on a git failure.
    """
    r = subprocess.run(
        ["git", "-C", str(root), "--literal-pathspecs",
         "diff", "--name-status", "-z", "-M", base],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(f"git diff --name-status {base} failed: {r.stderr.strip()[:200]}")
    fields = [f for f in r.stdout.split("\0") if f]
    out: list[tuple[str, "str | None"]] = []
    i = 0
    while i < len(fields):
        status = fields[i]
        if status[0] in ("R", "C") and i + 2 < len(fields):
            out.append((fields[i + 2], fields[i + 1]))   # (destination, source)
            i += 3
        elif i + 1 < len(fields):
            out.append((fields[i + 1], None))
            i += 2
        else:
            break
    return tuple(out)


def file_diff(base: str, root: pathlib.Path, path: str, source: "str | None" = None) -> str:
    """One file's unified diff against `base`. Raises on a git failure.

    Passing `source` alongside the destination lets git match the halves of a rename, so a moved
    document's existing citations are context rather than additions (r3-codex Medium).
    """
    # ⛔ r4 M1 — THE SOURCE IS PAIRED ONLY IF IT WAS ITSELF IN SCOPE. Pairing the halves of a
    # rename makes a moved document add nothing (r3-codex CM1), which is right when an earlier run
    # already checked those lines. It is WRONG when the pre-image was never scoped — measured,
    # `docs/reviews/old.md`, `scripts/notes.md` and `docs/notes.txt` each promoted to a scoped
    # `.md` carried a blank-line citation and all three passed rc=0. Those lines had been seen by
    # no run and, being "not added" forever after, never would be. Dropping the source for an
    # out-of-scope pre-image makes git treat the destination as wholly new, which it is to this
    # guard. ⚠ This is fix-induced from round 3, which is the thrashing pattern continuing.
    # ⚠ TWO DECISIONS, TWO LINES, DELIBERATELY. They are separately load-bearing and a mutation
    # anchor can be occupied once: `pair_source` decides WHETHER an out-of-scope pre-image counts
    # as the same document (r4 M1), and `paths` decides whether a paired source is handed to git at
    # all (r3-codex CM1). Written on one line, only one of the two could carry a manifest entry.
    pair_source = source if source is not None and in_scope(source) else None
    paths = [path] if pair_source is None else [path, pair_source]
    # ⛔ `--no-ext-diff` — A FAIL-OPEN FOUND BY THE COORDINATOR AFTER THE r4 REDESIGN, and the
    # FIFTH in this family. `diff.external` or `GIT_EXTERNAL_DIFF` replaces git's output WHOLESALE;
    # the replacement need not contain a single `@@`, so `added_lines` returned `()` and the run
    # printed "doc citations OK" over a drifted citation. Measured as a PAIR against the same
    # fixtures: without the flag rc=0, with it rc=1.
    # ⭐ A `textconv` driver, which rewrites the diff's CONTENT, does NOT break this shape at all —
    # measured rc=1 — because content comes from the document now. That is the honest statement of
    # what the redesign achieved: the content half of the class is closed by construction, and the
    # output-PROVENANCE half needed this flag.
    r = subprocess.run(["git", "-C", str(root), "--literal-pathspecs",
                        "diff", "--no-ext-diff", "--unified=0", "-M", base, "--", *paths],
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
        # ⛔ r4 H3 — A SYMLINK IS NOT THE DOCUMENT GIT DIFFED. For `docs/link.md -> target.md` git's
        # hunk header describes the LINK TEXT (one line, `target.md`), while `is_file()` follows the
        # link, so `doc_lines` was the TARGET's lines: `added` was `(1,)`, the guard examined
        # `"line1"`, and a drifted citation on line 4 of the resolved document was never read —
        # for a brand-new scoped path whose every line is new. Measured rc=0.
        # ⚠ `is_symlink()` BEFORE `is_file()`, because `is_file()` follows the link and answers
        # True. The adjacent survivor the reviewer's sweep found was `is_file -> exists`: nothing
        # in the suite distinguished a non-regular file at all.
        if target.is_symlink():
            raise RuntimeError(
                f"{path} is a symlink; git diffs the link text and this would read its target, "
                f"so the two would not describe the same document")
        if not target.is_file():
            return None
        # ⛔ `split("\n")`, NEVER `splitlines()` — r4 H1, a FAIL-OPEN AND a false positive from one
        # line. Python's `str.splitlines()` breaks on `\v \f \x1c \x1d \x1e \x85 U+2028 U+2029`
        # and a lone `\r`; git ends a line only at `\n`. One of those characters anywhere in a
        # document shifts every later line number by one, so `doc_lines[n - 1]` is NOT the line git
        # said was added. Measured BOTH directions: a form feed let a drifted citation pass
        # (rc=0 against an adjacent control's rc=1), and a U+2028 made an innocent append inherit
        # last year's stale citation (rc=1) — which breaks the ADDED-LINES-ONLY contract the whole
        # scope argument rests on. Four tracked documents already disagree with git's line count,
        # and the producer of U+2028 here is this project's own review agents.
        # ⚠ The trailing phantom element `split("\n")` leaves on a newline-terminated file is never
        # read: `violations` indexes only members of `added`, which git numbers.
        return target.read_text(encoding="utf-8", errors="replace").split("\n")
    return read


def _pathspec_witness() -> int:
    """Findings for one glob-shaped document name. One is the answer ONLY with literal pathspecs.

    `docs/[id].md` is a valid filename and a valid glob. Without `--literal-pathspecs` the per-file
    diff also matches `docs/i.md` and reports that file's citations under the wrong name, so this
    returns 2 (r3-codex Medium).
    """
    import tempfile
    env = {"PATH": os.environ.get("PATH", ""), "HOME": "/nonexistent",
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
           "GIT_AUTHOR_NAME": "s", "GIT_AUTHOR_EMAIL": "s@e.com",
           "GIT_COMMITTER_NAME": "s", "GIT_COMMITTER_EMAIL": "s@e.com"}
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)

        def run(*args: str) -> None:
            r = subprocess.run(["git", "-C", tmp, "-c", "commit.gpgsign=false", *args],
                               capture_output=True, text=True, env=env)
            if r.returncode != 0:
                raise RuntimeError(f"fixture setup failed: git {' '.join(args)} -> "
                                   f"{r.stderr.strip()[:160]}")

        run("init", "-q", "--template=")
        (root / "docs").mkdir(); (root / "lib").mkdir()
        (root / "lib" / "a.ts").write_text("one line\n", encoding="utf-8")
        (root / "docs" / "seed.md").write_text("seed\n", encoding="utf-8")
        run("add", "-A"); run("commit", "-qm", "base")
        (root / "docs" / "i.md").write_text("`lib/a.ts:777`\n", encoding="utf-8")
        (root / "docs" / "[id].md").write_text("`lib/a.ts:888`\n", encoding="utf-8")
        run("add", "-A")
        return len(findings_for("docs/[id].md", None, "HEAD", root,
                                tracked_files(root), _reader(root), file_diff))


def _rename_witness() -> int:
    """Findings when a document carrying an ALREADY-BAD citation is purely renamed.

    Zero is the answer: a rename adds nothing. Without the source path in the pathspec git cannot
    pair the halves and reports the whole file as additions (r3-codex Medium).
    """
    import tempfile
    env = {"PATH": os.environ.get("PATH", ""), "HOME": "/nonexistent",
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
           "GIT_AUTHOR_NAME": "s", "GIT_AUTHOR_EMAIL": "s@e.com",
           "GIT_COMMITTER_NAME": "s", "GIT_COMMITTER_EMAIL": "s@e.com"}
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)

        def run(*args: str) -> None:
            r = subprocess.run(["git", "-C", tmp, "-c", "commit.gpgsign=false", *args],
                               capture_output=True, text=True, env=env)
            if r.returncode != 0:
                raise RuntimeError(f"fixture setup failed: git {' '.join(args)} -> "
                                   f"{r.stderr.strip()[:160]}")

        run("init", "-q", "--template=")
        (root / "docs").mkdir(); (root / "lib").mkdir()
        (root / "lib" / "a.ts").write_text("one line\n", encoding="utf-8")
        (root / "docs" / "old.md").write_text("`lib/a.ts:777` and padding\n" * 6, encoding="utf-8")
        run("add", "-A"); run("commit", "-qm", "base")
        run("mv", "docs/old.md", "docs/new.md")
        # COMMITTED, and diffed against its parent, so the base is a real second value rather than
        # the `HEAD` every other call site passes (check-fixture-variation.py), and so the fixture
        # is the shape a rename actually arrives in.
        run("commit", "-qm", "rename")
        found = 0
        for path, source in changed_files("HEAD~1", root):
            if in_scope(path):
                found += len(findings_for(path, source, "HEAD~1", root,
                                          tracked_files(root), _reader(root), file_diff))
        return found


def _nul_witness() -> int:
    """Build a throwaway repo with two changed docs and count what `changed_files` returns.

    Two is the answer ONLY if the NUL split works: without `-z`, git joins the names with newlines
    and `split("\0")` yields one blob, which `in_scope` rejects — emptying the scoped list and
    silently disabling the guard (r3 High).

    ⛔ r3-codex: the fixture is ISOLATED from ambient git state and every setup command is checked.
    The first version inherited the caller's configuration, so an ordinary `commit.gpgsign=true`
    made the commit fail, left no HEAD, and surfaced as a misleading traceback about file listing.
    """
    import tempfile
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": "/nonexistent",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_AUTHOR_NAME": "selftest", "GIT_AUTHOR_EMAIL": "selftest@example.com",
        "GIT_COMMITTER_NAME": "selftest", "GIT_COMMITTER_EMAIL": "selftest@example.com",
    }
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)

        def run(*args: str) -> None:
            r = subprocess.run(["git", "-C", tmp, "-c", "commit.gpgsign=false", *args],
                               capture_output=True, text=True, env=env)
            if r.returncode != 0:
                raise RuntimeError(f"fixture setup failed: git {' '.join(args)} -> "
                                   f"{r.stderr.strip()[:160]}")

        run("init", "-q", "--template=")
        (root / "docs").mkdir()
        (root / "docs" / "seed.md").write_text("seed\n", encoding="utf-8")
        run("add", "-A")
        run("commit", "-qm", "base")
        (root / "docs" / "one.md").write_text("one\n", encoding="utf-8")
        (root / "docs" / "two.md").write_text("two\n", encoding="utf-8")
        run("add", "-A")
        return len([p for p, _src in changed_files("HEAD", root) if in_scope(p)])


def _line_rule_witness() -> "tuple[int, int]":
    """(findings with a form feed, findings without it). (1, 1) is the answer — they must AGREE.

    ⛔ r4 H1. git ends a line at `\n` and nothing else; Python's `splitlines()` also breaks on
    `\v \f \x1c \x1d \x1e \x85 U+2028 U+2029` and a lone `\r`. Under `splitlines()` the form-feed
    document returned (0, 1): the SAME citation on the SAME added line was found in the control and
    missed in the fixture, because every later line number was shifted by one.

    The control is ADJACENT by construction — one character differs, a form feed against a space —
    so this cannot pass for an ambient reason. The pair is the assertion; either number alone is
    satisfied by a guard that does nothing.
    """
    import tempfile
    env = {"PATH": os.environ.get("PATH", ""), "HOME": "/nonexistent",
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
           "GIT_AUTHOR_NAME": "s", "GIT_AUTHOR_EMAIL": "s@e.com",
           "GIT_COMMITTER_NAME": "s", "GIT_COMMITTER_EMAIL": "s@e.com"}
    out = []
    for first_line in ("intro\x0cmore", "intro more"):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)

            def run(*args: str) -> None:
                r = subprocess.run(["git", "-C", tmp, "-c", "commit.gpgsign=false", *args],
                                   capture_output=True, text=True, env=env)
                if r.returncode != 0:
                    raise RuntimeError(f"fixture setup failed: git {' '.join(args)} -> "
                                       f"{r.stderr.strip()[:160]}")

            run("init", "-q", "--template=")
            (root / "docs").mkdir(); (root / "lib").mkdir()
            # line 2 is BLANK, so a citation of it is a finding
            (root / "lib" / "a.ts").write_text("const a = 1\n\nexport default a\n", encoding="utf-8")
            (root / "docs" / "x.md").write_text(first_line + "\n", encoding="utf-8")
            run("add", "-A"); run("commit", "-qm", "base")
            (root / "docs" / "x.md").write_text(
                first_line + "\nsee `lib/a.ts:2` here\n", encoding="utf-8")
            run("add", "-A")
            out.append(len(findings_for("docs/x.md", None, "HEAD", root,
                                        tracked_files(root), _reader(root), file_diff)))
    return tuple(out)


def _binary_witness() -> "tuple[str, str, int]":
    """How the guard treats a scoped document git calls BINARY, three ways.

    Returns `(nul_route, attribute_route, control_findings)`:
      * `nul_route`        — a document holding one NUL byte            -> "CANNOT RUN"
      * `attribute_route`  — plain ASCII under `docs/** -diff`          -> "CANNOT RUN"
      * `control_findings` — the SAME bytes under `docs/** text`        -> 1

    ⛔ r4 H2. `git diff` emits `Binary files … differ` and NO `@@` for both routes, so
    `added_lines` returned `()` and `findings_for`'s `if not added: return []` read it as nothing
    to check — rc=0 over a drifted citation. The attribute route needs no unusual content at all,
    only a line anybody can commit, which is what makes it realistic rather than exotic.

    ⚠ THE CONTROL IS THE THIRD ELEMENT, and it is adjacent: identical document bytes, one
    `.gitattributes` word different. Without it, "CANNOT RUN" twice is also what a guard that
    refuses everything would return.
    """
    import tempfile
    env = {"PATH": os.environ.get("PATH", ""), "HOME": "/nonexistent",
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
           "GIT_AUTHOR_NAME": "s", "GIT_AUTHOR_EMAIL": "s@e.com",
           "GIT_COMMITTER_NAME": "s", "GIT_COMMITTER_EMAIL": "s@e.com"}
    results = []
    for attrs, body in (
            (None, b"see `lib/a.ts:2` here\nbin\x00ary\n"),     # NUL route
            ("docs/** -diff\n", b"see `lib/a.ts:2` here\n"),      # attribute route
            ("docs/** text\n", b"see `lib/a.ts:2` here\n")):      # the adjacent CONTROL
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)

            def run(*args: str) -> None:
                r = subprocess.run(["git", "-C", tmp, "-c", "commit.gpgsign=false", *args],
                                   capture_output=True, text=True, env=env)
                if r.returncode != 0:
                    raise RuntimeError(f"fixture setup failed: git {' '.join(args)} -> "
                                       f"{r.stderr.strip()[:160]}")

            run("init", "-q", "--template=")
            (root / "docs").mkdir(); (root / "lib").mkdir()
            (root / "lib" / "a.ts").write_text("const a = 1\n\nexport default a\n", encoding="utf-8")
            (root / "docs" / "seed.md").write_text("seed\n", encoding="utf-8")
            if attrs:
                (root / ".gitattributes").write_text(attrs, encoding="utf-8")
            run("add", "-A"); run("commit", "-qm", "base")
            (root / "docs" / "b.md").write_bytes(body)
            run("add", "-A")
            try:
                results.append(len(findings_for("docs/b.md", None, "HEAD", root,
                                                tracked_files(root), _reader(root), file_diff)))
            except (ValueError, RuntimeError):
                results.append("CANNOT RUN")
    return tuple(results)


def _symlink_witness() -> "tuple[str, int]":
    """(what a SYMLINKED scoped document does, what a REGULAR one with the same content does).

    `("CANNOT RUN", 1)` is the answer. ⛔ r4 H3: git's hunk header describes the link TEXT, one
    line long, while a reader that follows the link numbers the target's lines — two oracles, one
    of them silently describing a different object. Measured rc=0 before this refusal existed.

    ⚠ The second element is the ADJACENT control: the same citation in a regular file must still
    fire, so "refuses everything" cannot satisfy this case.
    """
    import tempfile
    env = {"PATH": os.environ.get("PATH", ""), "HOME": "/nonexistent",
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
           "GIT_AUTHOR_NAME": "s", "GIT_AUTHOR_EMAIL": "s@e.com",
           "GIT_COMMITTER_NAME": "s", "GIT_COMMITTER_EMAIL": "s@e.com"}
    out = []
    for as_symlink in (True, False):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)

            def run(*args: str) -> None:
                r = subprocess.run(["git", "-C", tmp, "-c", "commit.gpgsign=false", *args],
                                   capture_output=True, text=True, env=env)
                if r.returncode != 0:
                    raise RuntimeError(f"fixture setup failed: git {' '.join(args)} -> "
                                       f"{r.stderr.strip()[:160]}")

            run("init", "-q", "--template=")
            (root / "docs").mkdir(); (root / "lib").mkdir()
            (root / "lib" / "a.ts").write_text("const a = 1\n\nexport default a\n", encoding="utf-8")
            (root / "docs" / "seed.md").write_text("seed\n", encoding="utf-8")
            run("add", "-A"); run("commit", "-qm", "base")
            body = "line1\nline2\nline3\nsee `lib/a.ts:2` here\n"
            if as_symlink:
                (root / "docs" / "target.md").write_text(body, encoding="utf-8")
                (root / "docs" / "link.md").symlink_to("target.md")
                path = "docs/link.md"
            else:
                (root / "docs" / "link.md").write_text(body, encoding="utf-8")
                path = "docs/link.md"
            run("add", "-A")
            try:
                out.append(len(findings_for(path, None, "HEAD", root,
                                            tracked_files(root), _reader(root), file_diff)))
            except (ValueError, RuntimeError):
                out.append("CANNOT RUN")
    return tuple(out)


def _promotion_witness() -> "tuple[int, int, int, int]":
    """Findings when a document ENTERS scope by rename, three ways, plus the in-scope control.

    `(1, 1, 1, 0)` is the answer:
      * `docs/reviews/old.md -> docs/promoted.md`  — the exclusion made the source unscoped
      * `scripts/notes.md    -> docs/notes.md`     — the `docs/` prefix did
      * `docs/notes.txt      -> docs/notes.md`     — the `.md` test did
      * `docs/old.md         -> docs/new.md`       — CONTROL: both in scope, so 0 is correct

    ⛔ r4 M1, and the fourth element is what makes this a finding rather than a contract
    restatement: for the control an earlier run DID examine those lines, so adding nothing is
    right. For the first three `in_scope(source)` is False, so no run ever saw them.
    """
    import tempfile
    env = {"PATH": os.environ.get("PATH", ""), "HOME": "/nonexistent",
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
           "GIT_AUTHOR_NAME": "s", "GIT_AUTHOR_EMAIL": "s@e.com",
           "GIT_COMMITTER_NAME": "s", "GIT_COMMITTER_EMAIL": "s@e.com"}
    out = []
    for src_path, dest in (("docs/reviews/old.md", "docs/promoted.md"),
                           ("scripts/notes.md", "docs/notes.md"),
                           ("docs/notes.txt", "docs/notes.md"),
                           ("docs/old.md", "docs/new.md")):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)

            def run(*args: str) -> None:
                r = subprocess.run(["git", "-C", tmp, "-c", "commit.gpgsign=false", *args],
                                   capture_output=True, text=True, env=env)
                if r.returncode != 0:
                    raise RuntimeError(f"fixture setup failed: git {' '.join(args)} -> "
                                       f"{r.stderr.strip()[:160]}")

            run("init", "-q", "--template=")
            (root / "lib").mkdir()
            (root / "lib" / "a.ts").write_text("const a = 1\n\nexport default a\n", encoding="utf-8")
            (root / src_path).parent.mkdir(parents=True, exist_ok=True)
            (root / "docs").mkdir(exist_ok=True)
            # padding so git scores it a rename rather than add+delete
            (root / src_path).write_text("see `lib/a.ts:2` here\n" + "padding\n" * 8,
                                         encoding="utf-8")
            run("add", "-A"); run("commit", "-qm", "base")
            run("mv", src_path, dest)
            run("commit", "-qm", "promote")
            found = 0
            for path, source in changed_files("HEAD~1", root):
                if in_scope(path):
                    found += len(findings_for(path, source, "HEAD~1", root,
                                              tracked_files(root), _reader(root), file_diff))
            out.append(found)
    return tuple(out)


def _empty_tree_witness() -> str:
    """Which of `tracked_files`' TWO raises a freshly initialised repository reaches.

    `"empty tree"` is the answer. ⛔ r4 M6: that function raises twice — once when git fails, once
    when `ls-files` returns nothing — and the case claiming the second ("RAISES rather than passing
    over nothing") used `/nonexistent`, which reaches the FIRST. Deleting the empty-tree refusal
    left the suite at 58/58. This fixture is a real repository with no files in it, which is the
    only input that distinguishes them.
    """
    import tempfile
    env = {"PATH": os.environ.get("PATH", ""), "HOME": "/nonexistent",
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"}
    with tempfile.TemporaryDirectory() as tmp:
        r = subprocess.run(["git", "-C", tmp, "init", "-q", "--template="],
                           capture_output=True, text=True, env=env)
        if r.returncode != 0:
            raise RuntimeError(f"fixture setup failed: {r.stderr.strip()[:160]}")
        try:
            tracked_files(pathlib.Path(tmp))
        except RuntimeError as exc:
            return "empty tree" if "empty tree" in str(exc) else f"other: {exc}"
    return "no raise at all"


def _rename_orientation_witness() -> "tuple[str, str]":
    """`changed_files` must report (DESTINATION, source) and not the reverse.

    ⛔ r4 L1: swapping the two left the suite at 58/58, because the rename case asserts a COUNT
    that both orientations produce and both paths were in scope. A count cannot see an ordering;
    this reads the pair directly.
    """
    import tempfile
    env = {"PATH": os.environ.get("PATH", ""), "HOME": "/nonexistent",
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
           "GIT_AUTHOR_NAME": "s", "GIT_AUTHOR_EMAIL": "s@e.com",
           "GIT_COMMITTER_NAME": "s", "GIT_COMMITTER_EMAIL": "s@e.com"}
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)

        def run(*args: str) -> None:
            r = subprocess.run(["git", "-C", tmp, "-c", "commit.gpgsign=false", *args],
                               capture_output=True, text=True, env=env)
            if r.returncode != 0:
                raise RuntimeError(f"fixture setup failed: git {' '.join(args)} -> "
                                   f"{r.stderr.strip()[:160]}")

        run("init", "-q", "--template=")
        (root / "docs").mkdir()
        (root / "docs" / "old.md").write_text("padding\n" * 9, encoding="utf-8")
        run("add", "-A"); run("commit", "-qm", "base")
        run("mv", "docs/old.md", "docs/new.md")
        run("commit", "-qm", "rename")
        entries = changed_files("HEAD~1", root)
        path, source = entries[0]
        return (path, source or "")


def _unified_zero_witness() -> "tuple[int, int]":
    """(findings for an innocent append, findings when the appended line itself cites badly).

    `(0, 1)` is the answer. ⛔ r4 M3, AND MY OWN TENTH AMBIENT CASE ON THIS FILE. The first case
    written for this finding asserted `added_lines("@@ -2,3 +2,4 @@ ctx1") == (2, 3, 4, 5)` — pure
    arithmetic over a literal, which CANNOT notice that `--unified=0` was dropped from `file_diff`,
    because the pure function never sees the flag. Measured: the mutation survived at 72/72.

    At the default `-U3` a one-line append emits `@@ -2,3 +2,4 @@`, whose `+c,d` range spans the
    three CONTEXT lines, so `added` picks up a citation three lines above the edit that the author
    never touched — the added-lines-only contract broken by a second route (H1's direction 2 is the
    first). With the flag, only line 5 is added and the stale citation on line 2 is invisible.

    ⚠ The second element is the control: the same repository with the citation ON the appended line
    must fire, so "finds nothing" cannot satisfy this case.
    """
    import tempfile
    env = {"PATH": os.environ.get("PATH", ""), "HOME": "/nonexistent",
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
           "GIT_AUTHOR_NAME": "s", "GIT_AUTHOR_EMAIL": "s@e.com",
           "GIT_COMMITTER_NAME": "s", "GIT_COMMITTER_EMAIL": "s@e.com"}
    out = []
    for appended in ("a harmless new sentence", "and see `lib/a.ts:2` too"):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)

            def run(*args: str) -> None:
                r = subprocess.run(["git", "-C", tmp, "-c", "commit.gpgsign=false", *args],
                                   capture_output=True, text=True, env=env)
                if r.returncode != 0:
                    raise RuntimeError(f"fixture setup failed: git {' '.join(args)} -> "
                                       f"{r.stderr.strip()[:160]}")

            run("init", "-q", "--template=")
            (root / "docs").mkdir(); (root / "lib").mkdir()
            (root / "lib" / "a.ts").write_text("const a = 1\n\nexport default a\n", encoding="utf-8")
            # the STALE citation is on line 2, three lines above where the append lands
            base_doc = "intro\nold `lib/a.ts:2` from last year\nmiddle\ntail\n"
            (root / "docs" / "x.md").write_text(base_doc, encoding="utf-8")
            run("add", "-A"); run("commit", "-qm", "base")
            (root / "docs" / "x.md").write_text(base_doc + appended + "\n", encoding="utf-8")
            run("add", "-A")
            out.append(len(findings_for("docs/x.md", None, "HEAD", root,
                                        tracked_files(root), _reader(root), file_diff)))
    return tuple(out)


def _ext_diff_witness() -> int:
    """Findings when an EXTERNAL DIFF DRIVER is configured. One is the answer.

    ⛔ `git diff` output can be replaced WHOLESALE by `diff.external` or `GIT_EXTERNAL_DIFF`. The
    replacement need not contain a single `@@` line, so `added_lines()` returns `()`,
    `findings_for` short-circuits on `if not added`, and the run prints "doc citations OK" over a
    document whose citation does not resolve. MEASURED 2026-10-15 before `--no-ext-diff` was added:
    rc=0 with the driver set, rc=1 without it — a FAIL-OPEN, and the fifth in this family.

    ⚠ `changed_files()` is NOT affected: `--name-status` output is not produced by a diff driver,
    which is why the failure appeared as "no added lines" and not as "no changed files".
    """
    import tempfile
    env = {"PATH": os.environ.get("PATH", ""), "HOME": "/nonexistent",
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
           "GIT_AUTHOR_NAME": "s", "GIT_AUTHOR_EMAIL": "s@e.com",
           "GIT_COMMITTER_NAME": "s", "GIT_COMMITTER_EMAIL": "s@e.com"}
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)

        def run(*args: str) -> None:
            r = subprocess.run(["git", "-C", tmp, "-c", "commit.gpgsign=false", *args],
                               capture_output=True, text=True, env=env)
            if r.returncode != 0:
                raise RuntimeError(f"fixture setup failed: git {' '.join(args)} -> "
                                   f"{r.stderr.strip()[:160]}")

        run("init", "-q", "--template=")
        (root / "docs").mkdir(); (root / "lib").mkdir()
        (root / "lib" / "a.ts").write_text("one line\n", encoding="utf-8")
        (root / "docs" / "seed.md").write_text("seed\n", encoding="utf-8")
        run("add", "-A"); run("commit", "-qm", "base")
        run("config", "diff.external", "/bin/echo")
        (root / "docs" / "bad.md").write_text("see `lib/a.ts:999`\n", encoding="utf-8")
        run("add", "-A")
        return len(findings_for("docs/bad.md", None, "HEAD", root,
                                tracked_files(root), _reader(root), file_diff))


def self_test() -> int:
    """74 cases. The count is declared in the module docstring and verified by running this."""
    passed = failed = 0

    def case(name: str, got, want=True) -> None:
        """⛔ `got` IS A THUNK, AND THAT IS STRUCTURAL RATHER THAN STYLE.

        A mutation that makes the subject RAISE used to kill the whole run: the harness counts
        `[FAIL]` lines (`parse_fail_names`) and a traceback produces none, so such a mutation
        scored ZERO red cases and read as a SURVIVOR — or worse, as coverage. MEASURED 2026-10-15
        over this file: a mechanical sweep of 88 condition-and-operator mutants produced **19 that
        crashed the suite**, among them forcing `len(suffix_matches) == 1` true (IndexError) and
        dropping the hunk-header position test (ValueError). Evaluating here turns every one of
        them into a red case carrying the name of the property it broke.
        """
        nonlocal passed, failed
        if callable(got):
            try:
                got = got()
            except BaseException as exc:            # noqa: BLE001 - REPORTED as the case's value
                got = exc
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
        """A unified diff adding these lines — for driving `main()`, which still sees a diff."""
        return f"@@ -0,0 +1,{len(added)} @@\n" + "\n".join(f"+{a}" for a in added)

    # ⛔ NO FIXTURE HELPER FOR `violations` ARGUMENTS, AND THAT IS DELIBERATE. A `doc()` helper
    # splatted at the call site (`violations(path, *doc("…"), tracked, read)`) was written here
    # first and made 23 call sites INVISIBLE to `check-fixture-variation.py`: `analyse()` matches
    # positional arguments by index and abandons that matching when a site contains a `*starred`
    # argument (its r10 L2 clause). The tidy helper reduced what a guard could audit, so every
    # case states its added set and its document outright.

    def first(f: list[str]) -> str:
        # r1 M2: never index [0] — a mutation that empties this must FAIL a case, not crash the suite.
        return f[0] if f else ""

    def _try(fn):
        """The value, or the EXCEPTION INSTANCE if it raised.

        ⛔ A case that raises kills the suite and reports NOTHING — the runner counts `[FAIL]`
        lines and a traceback produces none, so a mutation that genuinely broke the parser would
        score "0 cases red". The two CANNOT RUN properties are asserted through this, never with a
        bare call.
        """
        try:
            return fn()
        except Exception as exc:                   # noqa: BLE001 - returned, not swallowed
            return exc

    case("a blank cited line fires",
         lambda: len(violations("docs/x.md", (1,), ["see `lib/a.ts:2`"], tracked, read)) == 1)
    case("the blank message names the reader's experience",
         lambda: "lands on nothing" in first(violations("docs/x.md", (1,), ["`lib/a.ts:2`"], tracked, read)))
    case("a line past EOF fires",
         lambda: len(violations("docs/x.md", (1,), ["`lib/a.ts:99`"], tracked, read)) == 1)
    case("the out-of-range message states the file length",
         lambda: "3 lines" in first(violations("docs/x.md", (1,), ["`lib/a.ts:99`"], tracked, read)))
    case("an unresolvable path fires",
         lambda: len(violations("docs/x.md", (1,), ["`lib/gone.ts:1`"], tracked, read)) == 1)
    case("a populated cited line is silent",
         lambda: violations("docs/x.md", (1,), ["`lib/a.ts:1`"], tracked, read) == [])
    case("line 3 (last line) is in range",
         lambda: violations("docs/x.md", (1,), ["`lib/a.ts:3`"], tracked, read) == [])
    case("a line number of 0 fires rather than reading the last line",
         lambda: len(violations("docs/x.md", (1,), ["`lib/a.ts:0`"], tracked, read)) == 1)

    case("a readable file that is NOT in the tracked list still resolves",
         lambda: violations("docs/x.md", (1,), ["`lib/a.ts:1`"], (), read) == [])
    case("...and the same path with a blank cited line still fires, so it is not passing blindly",
         lambda: len(violations("docs/x.md", (1,), ["`lib/a.ts:2`"], (), read)) == 1)

    case("a unique multi-segment suffix resolves and is silent",
         lambda: violations("docs/x.md", (1,), ["`html-doc/ensure.ts:1`"],
                    ("lib/html-doc/ensure.ts",), read) == [])
    case("an AMBIGUOUS suffix FIRES rather than being skipped",
         lambda: len(violations("docs/x.md", (1,), ["`html-doc/ensure.ts:1`"], tracked, read)) == 1)
    case("the ambiguous message says how many matched",
         lambda: "ambiguous: 2" in first(violations("docs/x.md", (1,), ["`html-doc/ensure.ts:1`"],
                                            tracked, read)))
    case("a suffix match still range-checks",
         lambda: len(violations("docs/x.md", (1,), ["`html-doc/ensure.ts:99`"],
                        ("lib/html-doc/ensure.ts",), read)) == 1)

    # scope is a predicate the caller applies to git's own NUL-delimited file list, so a scope leak
    # is impossible by construction and these assert the predicate directly.
    case("docs/reviews/ is out of scope", lambda: in_scope("docs/reviews/r.md"), False)
    case("a generated .html page is out of scope", lambda: in_scope("docs/explainers/p.html"), False)
    case("a non-docs path is out of scope", lambda: in_scope("scripts/x.md"), False)
    case("a docs/ root .md IS in scope", lambda: in_scope("docs/backlog.md"), True)
    case("a nested docs .md IS in scope", lambda: in_scope("docs/adr/0001-x.md"), True)
    # ⛔ r3 HIGH, AND IT IS THE FOURTH AMBIENT CASE THIS GUARD HAS PRODUCED. The case that stood
    # here was named "git hands it over unquoted via -z" and called `in_scope` on a Python string —
    # it never touched git, so deleting `-z` failed ZERO cases while silently disabling the whole
    # guard (`split("\0")` returns one newline-joined blob, `in_scope` rejects it, `scoped=[]`,
    # rc=0 over a repo full of bad citations). Every safety property rests on that one flag, so the
    # witness has to RUN git. This case builds a repository to do it.
    # ⚠ THESE THREE RAISE ON THE CANNOT RUN INVARIANTS, and `case` reports that as the case's own
    # value rather than a dead run — the reason it takes a thunk. MEASURED 2026-10-15: the
    # candidate mutation `range(start, start + count + 1)` made `_pathspec_witness` raise, and the
    # run reported ZERO red cases while the guard was broken. No `_try` is needed here; `_try` is
    # for the cases that ASSERT a raise, which is a different question from surviving one.
    case("⛔ changed_files() splits on NUL — the one flag every safety property rests on",
         lambda: _nul_witness() == 2)
    # ⛔ r3-codex MEDIUM, and it corrects a claim I made in a commit message: `_nul_witness()`
    # never calls `file_diff`, so it could NOT catch a dropped `--literal-pathspecs`. It has an
    # isolating witness after all, and here it is.
    case("⛔ a glob-shaped document name does not over-match its neighbours",
         lambda: _pathspec_witness() == 1)
    # ⛔ r3-codex MEDIUM: a PURE RENAME must add nothing. Without the source path in the pathspec
    # git cannot match the halves, and every citation in the moved document reports as newly
    # added — which contradicts the added-lines-only contract the whole scope argument rests on.
    case("⛔ a pure rename of a document with a BAD citation adds nothing",
         lambda: _rename_witness() == 0)
    # ⛔ r4 H1 — the reader and git must agree on what a LINE is. The pair is the assertion: the
    # fixture and its one-character-different control must return the SAME count. Under
    # `splitlines()` this returned (0, 1) — missed in the fixture, found in the control.
    case("⛔ a form feed does not shift the document's line numbering away from git's",
         lambda: _line_rule_witness() == (1, 1))
    # ⛔ r4 H2 — a scoped document git calls BINARY must not pass silently. Both routes refuse, and
    # the third element is the ADJACENT control: same bytes, `docs/** text` instead of `-diff`.
    case("⛔ a document git reports as binary is CANNOT RUN, and the same bytes still fire",
         lambda: _binary_witness() == ("CANNOT RUN", "CANNOT RUN", 1))
    # ⛔ r4 H3 — the third route into the two-oracle seam. The control is the same content in a
    # REGULAR file, which must still fire.
    case("⛔ a symlinked document is refused, not read through to its target",
         lambda: _symlink_witness() == ("CANNOT RUN", 1))
    # ⛔ r4 M1 — a document PROMOTED into scope has never been checked, so it is not "unchanged".
    # The fourth element is the in-scope control, where adding nothing remains correct.
    case("⛔ a rename from an out-of-scope source IS examined; an in-scope rename still is not",
         lambda: _promotion_witness() == (1, 1, 1, 0))
    # ⛔ r4 M6 — the empty-tree refusal is a SECOND raise in `tracked_files`, and the case that
    # named it reached the first one instead. Only a real repository with no files tells them apart.
    case("⛔ an EMPTY repository reaches the empty-tree refusal, not the git-failure raise",
         lambda: _empty_tree_witness() == "empty tree")
    # ⛔ r4 L1 — a COUNT cannot see an ordering: swapping destination and source left the suite
    # green. This reads the pair.
    case("⛔ changed_files reports (destination, source), not the reverse",
         lambda: _rename_orientation_witness() == ("docs/new.md", "docs/old.md"))
    # ⛔ THE FIFTH FAIL-OPEN IN THIS FAMILY, found by the coordinator AFTER the r4 redesign and not
    # removed by it: git's output can be REPLACED WHOLESALE by a configured driver, and output with
    # no `@@` reads as "nothing was added". `--no-ext-diff` is what makes this 1.
    case("⛔ a configured external diff driver cannot silence the guard",
         lambda: _ext_diff_witness() == 1)
    # ⛔ r4 L3, adjacent to H3 — nothing distinguished the reader's treatment of a non-regular
    # path. A directory must read as None (becoming a finding), never raise out of the reader.
    case("⛔ the reader answers None for a DIRECTORY rather than raising out of itself",
         lambda: _reader(pathlib.Path("."))("docs") is None)
    case("...and still reads a regular file, so it is not answering None to everything",
         lambda: isinstance(_reader(pathlib.Path("."))("scripts/check-doc-citations.py"), list))

    # ── what `added_lines` reads, and what it REFUSES ──────────────────────────────────────────
    # ⛔ THE SIX CASES BELOW REPLACE A MARKER PARSER AND THE TWO AMBIENT CASES THAT GUARDED IT.
    # Measured 2026-10-15, before this redesign: deleting the marker filter outright left the suite
    # at 41/41 green, because the two cases that named it ("a REMOVED line is not examined", "a
    # context line is not examined") handed `violations` a fixture with NO hunk header, so the
    # filter was never reached. Ambient cases six and seven on this one file. The property is now
    # structural — a line that is not in `added` is not read — and case "a line NOT in the added
    # set is never examined" below is falsifiable: widen the set and it reddens.
    case("a count of 3 yields exactly those three lines",
         lambda: added_lines("@@ -1,0 +2,3 @@") == (2, 3, 4))
    case("an OMITTED count means one line, not zero",
         lambda: added_lines("@@ -1 +2 @@") == (2,))
    case("a pure DELETION hunk (+c,0) adds nothing",
         lambda: added_lines("@@ -5,2 +7,0 @@") == ())
    case("several hunks accumulate",
         lambda: added_lines("@@ -1,0 +2 @@\n@@ -9,0 +10,2 @@") == (2, 10, 11))
    # ⛔ THE SUCCESSOR OF r3-codex's HIGH, and the reason this shape cannot repeat it. Every content
    # line in a unified diff carries a one-character prefix, so an added line beginning `@@` arrives
    # as `+@@` and can never be mistaken for a header at column 0. The old shape had to tell `+++`
    # from `+` plus `++`, which are the same four characters.
    case("⛔ an added line beginning `@@` is content, never a header",
         lambda: added_lines("@@ -1,0 +2 @@\n+@@ -9,0 +99 @@") == (2,))
    case("a `---` line, removed rule or file header alike, is simply not a hunk header",
         lambda: added_lines("----\n--- a/docs/x.md\n+++ b/docs/x.md\n@@ -1,0 +2 @@") == (2,))
    # ⛔ THE ONE NEW FAIL-OPEN, NAMED IN THE ROUND DOCUMENT BEFORE THIS CODE EXISTED. Returning ()
    # for a header it did not understand would read as "nothing to check" — the direction all four
    # header defects failed in. It raises, and main() turns that into CANNOT RUN.
    case("⛔ a line that begins @@ and does not parse RAISES, it does not yield nothing",
         lambda: isinstance(_try(lambda: added_lines("@@ garbled @@")), ValueError))

    # ── and what `violations` examines, now that content comes from the document ───────────────
    case("⛔ a line NOT in the added set is never examined",
         lambda: violations("docs/x.md", (1,), ["ok", "`lib/a.ts:99`"], tracked, read) == [])
    case("...and the very same document DOES fire when that line is added",
         lambda: len(violations("docs/x.md", (1, 2), ["ok", "`lib/a.ts:99`"], tracked, read)) == 1)
    case("a document line beginning `++` is examined like any other",
         lambda: len(violations("docs/x.md", (1,), ["++ `lib/a.ts:99`"], tracked, read)) == 1)
    case("⛔ an added line past the document's end RAISES — the diff and the file disagree",
         lambda: isinstance(_try(lambda: violations("docs/x.md", (3,), ["only one line"], tracked, read)),
                    RuntimeError))

    # ── r4 L3: clauses the reviewer's 53-mutant sweep found SURVIVING the whole suite. Each is
    # ── correct in the shipped code and was defended by nothing, so a later edit removes it
    # ── silently. Every case below was accepted only after its own falsifier was measured.
    # ⛔ r4 M2 — `.match`, not `.fullmatch`, is what lets REAL output parse: git appends the
    # enclosing function's text to nearly every hunk header. Pinning the pattern's end left the
    # suite completely green.
    case("⛔ a hunk header carrying git's function-context suffix still parses",
         lambda: added_lines("@@ -1,0 +2,2 @@ ## Some heading") == (2, 3))
    # ⛔ r4 M3 — `--unified=0` is load-bearing and had ZERO cases. ⚠ THE FIRST CASE WRITTEN HERE WAS
    # AMBIENT, MY TENTH ON THIS FILE: it asserted `added_lines("@@ -2,3 +2,4 @@ ctx1")`, pure
    # arithmetic over a literal, which cannot see a flag the pure function never receives — the
    # mutation survived at 72/72. The arithmetic assertion is KEPT below, because it is a true
    # property worth pinning; what it is not is a witness for the flag.
    case("a -U3-shaped header's range does cover four lines, as arithmetic",
         lambda: added_lines("@@ -2,3 +2,4 @@ ctx1") == (2, 3, 4, 5))
    case("⛔ ...and `--unified=0` keeps a stale citation three lines above an append out of scope",
         lambda: _unified_zero_witness() == (0, 1))
    # ⛔ r4 M7 — the out-of-range boundary was tested only 96 lines past the end. `:4` over a
    # 3-line file is the single commonest drift there is: a file that lost its last line. Negatives
    # have to be ADJACENT to be falsifiable.
    case("⛔ the line immediately past the end fires, not only one far past it",
         lambda: len(violations("docs/x.md", (1,), ["`lib/a.ts:4`"], tracked, read)) == 1)
    case("...and the last line itself does not, so the boundary is pinned from both sides",
         lambda: violations("docs/x.md", (1,), ["`lib/a.ts:3`"], tracked, read) == [])
    # ⛔ r4 L3 — the suffix match's SEGMENT BOUNDARY had no case: without the leading slash,
    # `c/ensure.ts` would resolve to `lib/html-doc/ensure.ts`, which is a different file.
    case("⛔ a suffix must match at a path SEGMENT boundary, not mid-segment",
         lambda: len(violations("docs/x.md", (1,), ["`c/ensure.ts:1`"],
                                ("lib/html-doc/ensure.ts",), read)) == 1)
    # ⛔ r4 L3 — `CITE`'s trailing `\b` had no case: without it `lib/a.ts:12abc` becomes a
    # citation of line 12.
    case("⛔ a line number glued to more text is not a citation",
         lambda: violations("docs/x.md", (1,), ["`lib/a.ts:2abc`"], tracked, read) == [])
    case("backticks are optional",
         lambda: len(violations("docs/x.md", (1,), ["see lib/a.ts:2 here"], tracked, read)) == 1)
    case("a [param] path segment parses",
         lambda: len(violations("docs/x.md", (1,), ["`app/[id]/r.ts:1`"], tracked, read)) == 1)
    case("two citations on one line are both examined",
         lambda: len(violations("docs/x.md", (1,), ["`lib/a.ts:2` and `lib/a.ts:99`"], tracked, read)) == 2)
    case("a bare filename with no directory is NOT a citation",
         lambda: violations("docs/x.md", (1,), ["`a.ts:2`"], tracked, read) == [])
    case("a docs/*.md target can itself be cited",
         lambda: violations("docs/x.md", (1,), ["`docs/notes.md:1`"], tracked, read) == [])
    case("...and a BAD markdown target fires, so the form is really examined",
         lambda: len(violations("docs/x.md", (1,), ["`docs/notes.md:9`"], tracked, read)) == 1)
    case("a URL is not a citation, so its port cannot become a path",
         lambda: violations("docs/x.md", (1,), ["http://localhost:3000/lib/a.ts:2"], tracked, read) == [])
    case("a citation wrapped in prose parentheses does not capture the bracket",
         lambda: violations("docs/x.md", (1,), ["(lib/a.ts:1)"], tracked, read) == [])

    # --- main() is DRIVEN over a constructed world (ADR-0014), to every exit code ---------------
    import contextlib
    import io

    seen: dict = {}

    def drive(changed, lines, reader, git_ok: bool = True, argv=None,
              root=pathlib.Path("/nonexistent"), doc_readable: bool = True,
              diff_override=None) -> int:
        """`main()` over a constructed world, to every exit code (ADR-0014).

        ⛔ THE DIFF AND THE DOCUMENT ARE BUILT FROM ONE SOURCE, `lines`, so they cannot disagree.
        The previous fixture passed a diff text and a reader that knew nothing about the document,
        which was harmless while content came out of the diff and is a contradiction now.

        `seen` records the base and root the parameters actually carried, because
        `check-fixture-variation.py` is right that a parameter passed one constant value is
        indistinguishable from a literal — and on this file it had ELEVEN such findings.
        """
        def fetch_changed(base, r):
            seen["base"], seen["root"] = base, r
            if not git_ok:
                raise RuntimeError("git diff --name-status origin/nope failed: unknown revision")
            return tuple((c, None) for c in changed)

        def make_reader(_r):
            def read_one(path):
                if path in changed:
                    return list(lines) if doc_readable else None
                return reader(path)
            return read_one

        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return main(argv if argv is not None else [], root=root,
                        fetch_changed=fetch_changed,
                        fetch_file_diff=lambda _b, _r, _p, _s=None: (
                            body(*lines) if diff_override is None else diff_override),
                        fetch_tracked=lambda _r: tracked,
                        make_reader=make_reader)

    def raises(_p):
        raise PermissionError("fixture is unreadable")

    case("main() returns 0 over a clean world",
         lambda: drive(("docs/x.md",), ("`lib/a.ts:1`",), read) == 0)
    case("main() returns 1 when a citation has drifted",
         lambda: drive(("docs/x.md",), ("`lib/a.ts:2`",), read) == 1)
    case("⛔ main() returns 2 — CANNOT RUN — when git cannot be reached, never 0",
         lambda: drive((), (), read, git_ok=False) == 2)
    # ⛔ r2-codex Medium: this handler had NO witness — replacing its `return 2` with `return 0`
    # left 40/40 green. An existing-but-unreadable cited file is CANNOT RUN, never a finding.
    case("⛔ main() returns 2 when a cited file exists but cannot be READ",
         lambda: drive(("docs/x.md",), ("`lib/a.ts:1`",), raises) == 2)
    case("...and an out-of-scope changed file is never diffed at all",
         lambda: drive(("scripts/x.md",), ("`lib/a.ts:2`",), read) == 0)

    # ── the parameters this suite had been passing ONE value, each now varied by a case that
    # ── asserts a real property rather than a cosmetically different argument (11 findings,
    # ── check-fixture-variation.py; an exemption resting on nothing is worse than none)
    case("the finding names the DOCUMENT it was handed, not a path baked into the rule",
         lambda: "docs/adr/0001-x.md:" in first(
             violations("docs/adr/0001-x.md", (1,), ["`lib/a.ts:2`"], tracked, read)))
    case("⛔ the injected reader IS the existence oracle — nothing resolves without it",
         lambda: len(violations("docs/x.md", (1,), ["`lib/a.ts:1`"], tracked, lambda _p: None)) == 1)
    case("⛔ changed_files on a path that is no repository is CANNOT RUN, not an empty change set",
         lambda: isinstance(_try(lambda: changed_files("HEAD", pathlib.Path("/nonexistent"))),
                    RuntimeError))
    case("⛔ tracked_files on a path that is no repository RAISES rather than passing over nothing",
         lambda: isinstance(_try(lambda: tracked_files(pathlib.Path("/nonexistent"))), RuntimeError))
    case("findings_for RAISES when git adds lines to a document that cannot be read",
         lambda: isinstance(_try(lambda: findings_for(
             "docs/y.md", None, "HEAD~2", pathlib.Path("/not-a-repo"), (),
             lambda _p: None,
             lambda _b, _r, _p, _s=None: "@@ -0,0 +1 @@\n+`lib/a.ts:1`")), RuntimeError))
    case("...and a deletion-only diff reads the document NOT AT ALL, so it cannot raise",
         lambda: _try(lambda: findings_for(
             "docs/z.md", "docs/y.md", "HEAD~3", pathlib.Path("/nor-this"), ("lib/a.ts",),
             lambda _p: (_ for _ in ()).throw(AssertionError("the document must not be read")),
             lambda _b, _r, _p, _s=None: "@@ -5,2 +7,0 @@")) == [])

    # ⛔ THE TWO CANNOT RUN PATHS THE REDESIGN CREATES, driven to rc=2 through main() rather than
    # asserted on the pure function alone — a raise that main() swallowed would be a fail-open.
    case("⛔ main() returns 2 when a hunk header does not parse, never 0",
         lambda: drive(("docs/x.md",), ("`lib/a.ts:1`",), read,
                       diff_override="@@ garbled @@") == 2)
    case("⛔ main() returns 2 when git adds lines to a document that cannot be read",
         lambda: drive(("docs/x.md",), ("`lib/a.ts:1`",), read, doc_readable=False) == 2)
    # ⛔ check-fixture-variation.py, 11 findings on this file: a parameter every call site passes
    # the same value is indistinguishable from a literal. These two read back what was carried.
    case("--base reaches the fetchers rather than a hardcoded default",
         lambda: drive(("docs/x.md",), ("`lib/a.ts:1`",), read,
               argv=["--base", "HEAD~1"]) == 0 and seen["base"] == "HEAD~1")
    case("...and the default base is origin/master, not whatever ran last",
         lambda: drive(("docs/x.md",), ("`lib/a.ts:1`",), read) == 0 and seen["base"] == "origin/master")
    case("--root reaches the fetchers as the resolved path it names",
         lambda: drive(("docs/x.md",), ("`lib/a.ts:1`",), read,
               argv=["--root", "/tmp"]) == 0 and seen["root"] == pathlib.Path("/tmp").resolve())
    case("...and without --root it is the root main() was handed",
         lambda: drive(("docs/x.md",), ("`lib/a.ts:1`",), read,
               root=pathlib.Path("/elsewhere")) == 0
         and seen["root"] == pathlib.Path("/elsewhere"))

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
        scoped = [(p, s) for p, s in fetch_changed(args.base, root) if in_scope(p)]
        tracked = fetch_tracked(root)
    except (RuntimeError, OSError) as exc:
        print(f"CANNOT RUN — {exc}\n  Treat this as NOT RUN, never as a pass.", file=sys.stderr)
        return 2

    read = make_reader(root)
    found: list[str] = []
    try:
        for scoped_path, scoped_source in scoped:
            found += findings_for(scoped_path, scoped_source, args.base, root,
                                  tracked, read, fetch_file_diff)
    except (RuntimeError, OSError, ValueError) as exc:
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
