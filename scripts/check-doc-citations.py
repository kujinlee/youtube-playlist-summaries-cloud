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
  (3) ⟳ **NEW TO THE DOCUMENT, not "on an added line"** (#291, 2026-10-16). Over the living corpus
      the rule fires **111 times on 895 pathed citations (12.4%)**, reproduced exactly — over a
      whole document both readings examine the same citations, so this figure is unchanged — overwhelmingly historical: ADR-0007 citing `schema/*.sql` files that M4 promoted
      into migrations, and 2026-06 specs citing files that have since shrunk.

⟳ **RE-MEASURED UNDER THE #291 RULE, 2026-10-16: 9 firings over the last 40 commits, 0.23 per
commit, across 3 commits.** The old line-based rule gave 10 at 0.25 across 4.
⭐ **THE FEARED COST DID NOT APPEAR, AND THAT WAS THE OPEN QUESTION.** The round-4 review warned
that a string rule is WIDER — *"a reformatted paragraph re-presents its citations"* — so the scope
decision had to be re-bought. It is narrower instead, because a re-presented citation is the SAME
TEXT and therefore not new. Measured at `b2e10e39`, the commit that stopped firing: in
`docs/backlog.md` the old rule examined SIX citations on added lines, of which **four were already
present in the pre-image** — a rewritten row carrying its existing citations onto new lines. The
string rule examines three: the two genuinely new ones, plus one EXTRA COPY of a citation that went
from one occurrence to two, which is why `citations()` returns a multiset and not a set.
So the firing the old rule lost was a citation its author never introduced.

Over the last 40 commits under the OLD rule: **10 firings, 0.25 per commit**
(`check-reference-namespace` shipped at 0.50). All ten hand-classified as TRUE: eight blank lines, one citation into
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
⟳ **#291, 2026-10-16: for every `path:line` citation a scoped document has GAINED — present in its
post-image and not in its pre-image, counting duplicates — the cited line must exist and carry
content.** Both images come from git (`<base>:<path>` and `:<path>`), so nothing is compared across
a filesystem boundary and no diff is parsed.
It previously read *"for every `path:line` on an ADDED line of a scoped file"*, and that phrasing is
what five fail-open routes lived in: the line numbers came from git and the content from the
filesystem, and nothing checked the two described the same object. It does NOT check that the line declares the symbol named nearby — row 49 describes that,
and it needs a language-aware parser per file type. The blank-line and out-of-range shapes are what
the eight measured instances actually looked like (`:66` was a mid-docstring blank; `:157` likewise),
and they are decidable without one.

WHAT IT IS BLIND TO, STATED RATHER THAN DISCOVERED LATER
--------------------------------------------------------
  * ⚠ **A `clean` FILTER WOULD BREAK "one oracle" (r5 L8).** `git cat-file` returns what git
    STORES, so a `clean` filter that rewrites content on the way in means the stored blob is not
    what the author wrote. Bounded: a filter lives in `.git/config` or is set up by hand, so unlike
    `.gitattributes` it is not committable by one author into everyone's clone — which is what made
    the `textconv` and `working-tree-encoding` routes worth closing and makes this worth stating.
  * ⚠ **A CITATION DIFFERING ONLY IN CASE RESOLVES on a case-insensitive filesystem (r5 L10).**
    `lib/A.ts:1` finds `lib/a.ts` on APFS and would not on Linux, so the guard is QUIETER on a Mac
    than in CI. The direction is safe — CI is the strict one — but the asymmetry is real.
  * ⚠ **`--base` NAMES A TIP, NOT A MERGE BASE (r5 M5).** Given `--base origin/master`, a document
    is compared with that document AT THE TIP. If master has since DELETED a citation this branch
    still carries, the branch is charged for it — the citation is absent from the pre-image and
    present in the post-image, which is what "gained" means. A merge-base comparison would not
    charge it. Pre-existing, not introduced by #291, and not reachable in CI, where the branch is
    rebased or the base is its own ancestor. Recorded because the next reader will hit it locally
    before they hit it anywhere else.
  * **A SYMLINKED DOCUMENT contributes only its LINK TEXT, by construction.** `docs/link.md ->
    ../notes/target.md` is a blob holding the string `../notes/target.md`, so it carries no
    citation, and the citations in the target are out of scope. Measured 2026-10-16 in isolation —
    with the target OUT of scope, rc=0.
    ⚠ This is a blind spot in the SCOPE rule, not in the comparison: one oracle, consistently
    applied — the guard reads exactly what git tracks at that path. Following the link would mean
    reading the filesystem again, which is the two-oracle seam #291 exists to delete, so it is
    recorded rather than closed. ⛔ And the previous design did NOT handle this better: it REFUSED
    a symlinked document (r4 H3) and also refused an ordinary CITED code symlink (r4-codex M2),
    which was a false refusal.
    ⚠⚠ MY FIRST TEST OF THIS PASSED FOR AN AMBIENT REASON — the fixture also created the target
    inside `docs/`, so the rc=1 came from the target being a new in-scope document, not from the
    link. Eleventh such case on this file; found by removing the target from scope.
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
  * a citation NEWLY PRESENT in a scoped document resolves to no tracked file, or to more than
    one by suffix;
  * the cited line number is outside the resolved file;
  * the cited line is blank or whitespace-only;
  * `git` cannot be run, or the base ref does not resolve — which is CANNOT RUN (rc=2), never a pass.

  --self-test  # 78 cases. Most are over DOCUMENTS this file builds with an injected
               resolver, so the rule needs no repository. ⟳ #291: there is no hunk-header reader
               and no diff text in this suite at all; the cases that build a throwaway git
               repository do so because the properties they witness are GIT's — NUL splitting, the
               rename pair's orientation, the index as the post-image, an unmerged path, a
               conflicted merge, `diff.renames=false`, and the blob answers.
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






def citations(text: str) -> "dict[tuple[str, int], int]":
    """Every citation in a document, as a MULTISET of `(path, line)` -> count. PURE.

    A MULTISET, not a set, and that is load-bearing: writing the same citation a second time is a
    new citation of it, so `post - pre` must keep counts. With sets, adding a duplicate of a
    citation already in the document would be invisible.
    """
    out: dict[tuple[str, int], int] = {}
    for match in CITE.finditer(text):
        key = (match.group(1), int(match.group(2)))
        out[key] = out.get(key, 0) + 1
    return out


def added_citations(pre: str, post: str) -> "tuple[tuple[str, int], ...]":
    """The citations POST holds that PRE does not, counting duplicates. PURE.

    ⛔ THIS REPLACES THE ENTIRE DIFF-PARSING HALF OF THIS GUARD (backlog #291), and the reason is
    one sentence: the old rule took line NUMBERS from git and CONTENT from the filesystem, and
    nothing checked the two were describing the same object. Five routes through that seam were
    found — `splitlines()` against git's line rule, a document git calls binary, a symlink, a
    `textconv` driver, `working-tree-encoding` — three of them AFTER the redesign that was supposed
    to close the class, and the patches for them produced three false refusals of their own.

    Here no line number crosses any boundary and there is no diff to parse.
    """
    pre_counts, post_counts = citations(pre), citations(post)
    out: list[tuple[str, int]] = []
    for key, n in post_counts.items():
        for _ in range(n - pre_counts.get(key, 0)):
            out.append(key)
    return tuple(out)


def violations(path: str, added: "tuple[tuple[str, int], ...]",
               tracked: tuple[str, ...], read) -> list[str]:
    """Findings for the citations a document has GAINED. PURE — no git, no filesystem, no diff.

    Takes `(cited_path, line)` pairs from `added_citations`. The three tests are unchanged from the
    rule row 49 was filed for: the path must resolve, the line must be inside the file, and the line
    must carry content.
    """
    found: list[str] = []
    for cited, raw_line in added:
        lines, how = resolve(cited, tracked, read)
        if lines is None:
            found.append(f"{path}: `{cited}:{raw_line}` does not resolve — {how}")
            continue
        # ⚠ `last_line` stays NAMED so the two drift directions keep separate mutation anchors:
        # widening it hides a file that LOST its last line, and tightening the comparison to `>=`
        # rejects a file's genuine last line. Both are real; one line could carry only one entry.
        last_line = len(lines)
        if raw_line < 1 or raw_line > last_line:
            found.append(f"{path}: `{cited}:{raw_line}` is outside the file ({len(lines)} lines)")
            continue
        if not lines[raw_line - 1].strip():
            found.append(f"{path}: `{cited}:{raw_line}` is a blank line — "
                         f"a reader following it lands on nothing")
    return found




def blob(ref_path: str, root: pathlib.Path) -> "str | None":
    """One blob's text, as git holds it, or None when git has no such path.

    `ref_path` is `<base>:<path>` for the pre-image or `:<path>` for the index. Raises on any git
    failure that is NOT "no such path" — an unreadable repository is CANNOT RUN, never an empty
    document, because an empty document would read as "this file had no citations before" and turn
    every citation in it into a new one.

    ⛔ BOTH IMAGES COME FROM GIT, AND THAT IS THE WHOLE POINT OF #291. Reading the post-image from
    the filesystem would keep TWO ORACLES, and two of the five routes through the old seam were
    exactly filesystem-versus-git disagreements: with `working-tree-encoding=UTF-16`, `git show`
    yields git's UTF-8 while the worktree holds UTF-16, so a genuinely NEW citation would not match
    and the guard would MISS it — the same defect with the arrow reversed.

    ⚠ SO THE GUARD EXAMINES WHAT IS STAGED, NOT THE WORKING TREE, and that is a deliberate
    behaviour change. In CI they are identical (a pushed branch against `origin/master` is all
    committed), which is where this gates. Locally an UNSTAGED edit is invisible — `main()` says so
    in its success message rather than leaving it to be discovered.
    """
    # ⛔ ASK GIT STRUCTURALLY, NEVER MATCH ITS PROSE. `cat-file -e` answers "is there an object at
    # this path" with an exit code, and a missing path is an ORDINARY answer here: a document new to
    # the base has no pre-image. Two attempts at matching the message were both wrong, on three
    # different wordings — `does not exist in 'HEAD'` (absent from disk as well),
    # `exists on disk, but not in 'HEAD'` (the actual new-file case), and `does not exist (neither
    # on disk nor in the index)`. The second is the one that matters and neither of my first two
    # string tests contained it.
    # ⚠ The BASE REF is validated before this runs: `changed_files` diffs against it and raises on
    # failure, so a `-e` miss here means "not in that tree" and not "bad ref".
    exists = subprocess.run(["git", "-C", str(root), "cat-file", "-e", ref_path],
                            capture_output=True, text=True)
    if exists.returncode != 0:
        # ⛔ A MISSING PATH AND A BAD REF ARE DIFFERENT ANSWERS AND MUST NOT COLLAPSE. `cat-file -e`
        # fails for both, so the ref is verified separately: a missing path is ORDINARY (a document
        # new to the base has no pre-image) while an unresolvable ref is CANNOT RUN. If they
        # collapsed, a mistyped `--base` would make every pre-image empty, every citation read as
        # newly gained, and the guard fire on the whole corpus.
        # ⚠ The first version relied on `changed_files` having validated the base first. That was
        # TRUE of the pipeline and still wrong to depend on — the witness called `blob` directly and
        # got None for `nosuchref:…`, which is how this was found.
        # ⛔ r5 H2 — A PATH THAT IS UNMERGED IS NOT A PATH THAT IS GONE. During a conflicted merge
        # the index holds stages 1/2/3 and nothing at stage 0, so `:path` does not resolve and this
        # returned None — which the caller reads as "the document was deleted" and passes. Measured:
        # rc=0 over a conflicted scoped document carrying a drifted citation, against rc=1 for the
        # same bytes one `git add` later. A THIRD answer collapsing into one of the two this
        # function already distinguishes.
        # ⚠ Both git answers are rc=128 with different prose, so the question is asked STRUCTURALLY:
        # `ls-files -u` lists unmerged entries and prints nothing when there are none.
        if ref_path.startswith(":"):
            unmerged = subprocess.run(
                ["git", "-C", str(root), "ls-files", "-u", "--", ref_path[1:]],
                capture_output=True, text=True)
            if unmerged.returncode == 0 and unmerged.stdout.strip():
                raise RuntimeError(
                    f"{ref_path[1:]} is UNMERGED — the index holds conflict stages and nothing at "
                    f"stage 0, so its citations cannot be compared. Resolve the conflict first")
        ref = ref_path.split(":", 1)[0]
        if ref:
            ok = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", "--quiet", ref],
                                capture_output=True, text=True)
            if ok.returncode != 0:
                raise RuntimeError(f"git cannot resolve the ref {ref!r} (from {ref_path!r}) — "
                                   f"treat this as NOT RUN, never as a document with no citations")
        return None
    r = subprocess.run(["git", "-C", str(root), "cat-file", "-p", ref_path],
                       capture_output=True, text=True)
    # ⚠ r5 M4, STATED RATHER THAN GIVEN A FAKE CASE: this handler has NO witness, and I could not
    # construct one. `-e` has just answered that the object exists, so `-p` failing means the
    # repository changed or broke between two subprocesses. It is belt-and-braces for a race, not a
    # reachable branch, and a case that forced it would be testing `subprocess` rather than this
    # rule. Recorded as an unwitnessed clause instead of pretending otherwise.
    if r.returncode != 0:
        raise RuntimeError(f"git cat-file -p {ref_path} failed: {r.stderr.strip()[:200]}")
    # ⛔ NUL means the document itself is not text git would diff as text. Matching citations
    # against mojibake is wrong, and a decoded NUL is the tell (r4-codex H1 route 5, kept because
    # the property survives even though its old route does not).
    if "\x00" in r.stdout:
        raise RuntimeError(
            f"{ref_path} holds NUL bytes once decoded as UTF-8 — git does not treat this as text, "
            f"so its citations cannot be read reliably")
    return r.stdout


def findings_for(path: str, source: "str | None", base: str, root: pathlib.Path,
                 tracked: tuple[str, ...], read, fetch_blob) -> list[str]:
    """One document: read both images from git, take the citations it GAINED, apply the rule.

    ⛔ THE PRE-IMAGE OF A PROMOTED DOCUMENT IS NOTHING, AND THAT IS NOW A CHOICE RATHER THAN AN
    ACCIDENT (r4 M1 becomes a decision, as #291 said it would). `source` is used only when it was
    ITSELF in scope: an ordinary in-scope rename was already checked when those lines were written,
    so its citations are not new. A document promoted from `docs/reviews/`, from `scripts/`, or from
    a `.txt` was never checked by any run, so every citation in it IS new.
    """
    # ⚠ TWO DECISIONS, TWO LINES, so each can carry a mutation entry — the fourth time this file has
    # needed the split. `pair` decides WHETHER an out-of-scope pre-image counts as the same document
    # (r4 M1, now a choice rather than an accident); `pre_ref` decides WHICH path is read.
    pair = source is not None and in_scope(source)
    pre_ref = f"{base}:{source}" if pair else f"{base}:{path}"
    # ⛔ THE POST-IMAGE FIRST — r5-codex M1. Reading the pre-image first meant an ordinary STAGED
    # DELETION of a legacy UTF-16 document hit the PRE-image's NUL refusal and returned CANNOT RUN,
    # when the answer is simply that a deleted document can gain nothing. Measured: rc=2 on a
    # deletion, against rc=0 for the same deletion of a plain-text document. A document that is
    # gone needs no pre-image read at all, so the order is not a style choice.
    post = fetch_blob(f":{path}", root)
    if post is None:
        return []
    pre = fetch_blob(pre_ref, root)
    added = added_citations(pre or "", post)
    if not added:
        return []
    return violations(path, added, tracked, read)


def changed_files(base: str, root: pathlib.Path) -> tuple[tuple[str, "str | None"], ...]:
    """(path, source) for each change against `base`. NUL-delimited, so git never quotes.

    `source` is the pre-rename path when git detected one, else None. ⛔ r3-codex: without it a
    pure rename reports every citation in the moved document as NEWLY ADDED, because the per-file
    pathspec excluded the source and git could not match the halves — which contradicts the
    added-lines-only contract this guard rests on.

    This is the half that makes header parsing unnecessary. Raises on a git failure.
    """
    r = subprocess.run(
        # ⚠ `--no-color` and `--literal-pathspecs` BOTH PROTECT NOTHING MEASURABLE HERE, and that is
        # recorded rather than hidden (r5 L2, L3). Measured 2026-10-16 with `color.ui=always` and a
        # glob-shaped filename: the output of `--name-status -z` is byte-identical with and without
        # either flag, because git does not decorate it and this invocation carries no pathspec.
        # Their consumers were the per-file diff and its allow-list, both deleted by #291.
        # ⛔ THEY STAY, and the reason is the cost of being WRONG in each direction: asserting "git
        # never colourises this" from one version and one configuration is the overreach that has
        # already cost this file several rounds, and if it is wrong the failure is a CANNOT RUN on
        # every run. A flag that does nothing costs nothing.
        ["git", "-C", str(root), "--literal-pathspecs",
         "diff", "--cached", "--no-color", "--name-status", "-z", "-M", base],
        capture_output=True,
    )
    if r.returncode != 0:
        raise RuntimeError(f"git diff --name-status {base} failed: "
                           f"{r.stderr.decode('utf-8', 'replace').strip()[:200]}")
    # ⛔ BYTES, NEVER `text=True`, ON A STREAM THAT CARRIES PATHS — r5-codex H1. Python's universal
    # newlines translate a `\r` INSIDE A FILENAME into `\n`, so `docs/a\rb.md` arrived as
    # `docs/a\nb.md`, the blob lookup asked git for a path that does not exist, the answer was None,
    # and the staged document read as DELETED: rc=0 over a drifted citation. Measured, with the
    # newline-named control firing correctly at rc=1.
    # ⚠ This is NOT round 4's carriage returns in document CONTENT. That seam was about two oracles
    # disagreeing; this is one oracle being asked about the wrong object, and `-z` cannot help
    # because the corruption happens after git has written the stream.
    fields = [f for f in r.stdout.decode("utf-8", "replace").split("\0") if f]
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




def tracked_files(root: pathlib.Path) -> tuple[str, ...]:
    """Every tracked path. Raises on a git failure — an empty list would pass about nothing."""
    # ⛔ `-z` AND BYTES, for the same reason as `changed_files` — r5-codex H1, found there and fixed
    # here too because this list is matched against citation SUFFIXES. Without `-z` git C-quotes an
    # unusual name (`"docs/a\rb.md"`), and splitting on a newline breaks on a name containing one;
    # with `text=True` a CR in a name became a newline and split it in two. Neither corruption is
    # visible in the result — it shows up as a citation that silently fails to resolve.
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"], capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git ls-files failed: "
                           f"{result.stderr.decode('utf-8', 'replace').strip()[:200]}")
    files = tuple(f for f in result.stdout.decode("utf-8", "replace").split("\0") if f)
    if not files:
        raise RuntimeError("git ls-files returned nothing — refusing to pass over an empty tree")
    return files


def _reader(root: pathlib.Path):
    """A reader that answers None rather than raising, so a missing file is a FINDING and not a
    traceback out of a pure function. ⛔ It does NOT swallow the distinction: None reaches
    `resolve`, which reports precisely why the path did not resolve."""
    def read(path: str) -> "list[str] | None":
        target = root / path
        # ⛔ r5 M6 — A CITATION MAY NOT ESCAPE THE REPOSITORY ROOT. Measured: `../outside.ts:2`
        # resolved against a file one directory ABOVE the root and fired on it, so the verdict
        # depended on a file no reader of this repository can see — and on another machine the same
        # citation resolves to something else or to nothing. `resolve()` collapses `..` before the
        # containment test, because a string test on the path would miss `a/../../b`.
        try:
            if not target.resolve().is_relative_to(root.resolve()):
                return None
        except OSError:
            return None
        # ⛔ r4 H3 — A SYMLINK IS NOT THE DOCUMENT GIT DIFFED. For `docs/link.md -> target.md` git's
        # hunk header described the LINK TEXT (one line, `target.md`), while `is_file()` followed the
        # link, so `doc_lines` was the TARGET's lines: `added` was `(1,)`, the guard examined
        # `"line1"`, and a drifted citation on line 4 of the resolved document was never read —
        # for a brand-new scoped path whose every line is new. Measured rc=0.
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
        # ⛔ `read_bytes().decode(...)`, NEVER `read_text(...)` — r4-codex H2, AND THIS IS THE SECOND
        # HALF OF A FIX I SHIPPED INCOMPLETE. `split("\n")` alone was not enough: `read_text` applies
        # UNIVERSAL NEWLINES, so a lone `\r` had already become `\n` before any split could see it.
        # Measured on `b"intro\rmore\ntail\n"` — `read_text().split("\n")` gives 3 lines,
        # `read_bytes().decode().split("\n")` gives 2, and git sees 2.
        # ⚠ The form-feed witness PASSED throughout, which is the lesson: it certified the half of
        # the fix I had thought about. A witness narrower than the class it defends is a witness
        # that says a partial fix is complete.
        # ⚠ TWO STATEMENTS, because the fix has TWO INDEPENDENT HALVES and each needs its own
        # mutation anchor: HOW THE BYTES ARE OBTAINED (`read_bytes().decode`, never `read_text`,
        # whose universal newlines translate a lone `\r` first — r4-codex H2) and HOW THEY ARE
        # SPLIT (`split("\n")`, never `splitlines()`, which breaks on seven more characters — r4 H1).
        raw = target.read_bytes().decode("utf-8", errors="replace")
        # ⛔ r4-codex H1, the FIFTH route — `working-tree-encoding=UTF-16`. git stores UTF-8
        # internally, so it emits `@@ -1,0 +2 @@` and the citation as ordinary UTF-8 text; the
        # WORKTREE bytes are UTF-16, and decoding them as UTF-8 leaves interleaved NULs that no
        # citation can match. Measured rc=0 against a plain-UTF-8 control's rc=1.
        # ⚠ A NUL in the decoded text means these bytes are not the text git diffed. Refuse rather
        # than match against mojibake — and note a NUL cannot appear in a document git treats as
        # text, so this cannot fire on an ordinary file.
        if "\x00" in raw:
            raise RuntimeError(
                f"{path} holds NUL bytes once decoded as UTF-8, so these are not the bytes git "
                f"diffed — a re-encoding attribute such as working-tree-encoding is in play")
        lines = raw.split("\n")
        # ⛔ r5 M1 — DROP THE PHANTOM. `split("\n")` leaves a trailing "" on every newline-terminated
        # file, so a 3-line file measured 4: the out-of-range message overstated EVERY file's length
        # by one, and a citation of `:4` landed on the phantom and was reported as "a blank line"
        # rather than "outside the file".
        # ⚠ A COMMENT I WROTE SAID THIS PHANTOM "is never read: `violations` indexes only members of
        # `added`, which git numbers". That was TRUE of the old design and was invalidated by #291 in
        # the same commit that kept it — `added` now carries line numbers an AUTHOR wrote, and an
        # author can write N+1. A caveat survives the design it was true of.
        if lines and lines[-1] == "":
            lines.pop()
        return lines
    return read




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
                                          tracked_files(root), _reader(root), blob))
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
                                              tracked_files(root), _reader(root), blob))
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












def _blob_witness() -> "tuple[object, object, object, object, object]":
    """How `blob()` answers four questions git can be asked about a path.

    `(pre_absent, post_present, nul_refused, bad_ref_raises, bad_root_raises)` ->
    `(None, "see `lib/a.ts:2` here\n", "CANNOT RUN", "CANNOT RUN", "CANNOT RUN")`.

    ⛔ A MISSING PATH IS AN ORDINARY ANSWER (None), A BROKEN REPOSITORY IS NOT. If a missing
    pre-image raised, a brand-new document could not be checked at all; if an unreadable repository
    returned None, every citation in every document would read as newly gained and the guard would
    fire on everything. The two must not be confused, which is why this returns both.
    ⚠ `blob` asks git with `cat-file -e` rather than matching its error prose. Two attempts at
    matching the message were wrong on three different wordings — `invalid object name`,
    `does not exist in 'HEAD'`, and the one that actually matters for a new file,
    `exists on disk, but not in 'HEAD'`.
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
        (root / "docs" / "seed.md").write_text("seed\n", encoding="utf-8")
        run("add", "-A"); run("commit", "-qm", "base")
        (root / "docs" / "x.md").write_text("see `lib/a.ts:2` here\n", encoding="utf-8")
        (root / "docs" / "nul.md").write_bytes(b"cite `lib/a.ts:2`\nbin\x00ary\n")
        run("add", "-A")
        out = [blob("HEAD:docs/x.md", root), blob(":docs/x.md", root)]
        for ref in (":docs/nul.md", "nosuchref:docs/x.md"):
            try:
                out.append(blob(ref, root))
            except RuntimeError:
                out.append("CANNOT RUN")
        # ⚠ A ROOT THAT IS NOT A REPOSITORY is the fifth answer, and it must be CANNOT RUN rather
        # than None — otherwise `--root` pointed at the wrong directory would report every document
        # as having no pre-image. It also varies `blob(root=…)`, which every other call site in this
        # suite passes one value (check-fixture-variation.py).
        try:
            out.append(blob("HEAD:docs/x.md", pathlib.Path("/nonexistent")))
        except RuntimeError:
            out.append("CANNOT RUN")
        return tuple(out)


def _staged_witness() -> "tuple[int, int]":
    """(an UNSTAGED bad citation, the same citation once STAGED) -> `(0, 1)`.

    ⛔ #291 made the guard read git's INDEX for the post-image, which is what gives it ONE oracle —
    and the price is that an unstaged edit is invisible. That is a real behaviour change from
    reading the working tree, so it is asserted rather than left in a docstring: `main()`'s success
    message says `git add` and re-run.
    ⚠ In CI the two are identical, which is where this gates; this case exists because LOCALLY they
    are not.
    """
    import tempfile
    env = {"PATH": os.environ.get("PATH", ""), "HOME": "/nonexistent",
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
           "GIT_AUTHOR_NAME": "s", "GIT_AUTHOR_EMAIL": "s@e.com",
           "GIT_COMMITTER_NAME": "s", "GIT_COMMITTER_EMAIL": "s@e.com"}
    out = []
    for stage in (False, True):
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
            (root / "lib" / "a.ts").write_text("one\n\nthree\n", encoding="utf-8")
            (root / "docs" / "x.md").write_text("intro\n", encoding="utf-8")
            run("add", "-A"); run("commit", "-qm", "base")
            (root / "docs" / "x.md").write_text("intro\nsee `lib/a.ts:2` here\n", encoding="utf-8")
            if stage:
                run("add", "-A")
            found = 0
            for path, source in changed_files("HEAD", root):
                if in_scope(path):
                    found += len(findings_for(path, source, "HEAD", root,
                                              tracked_files(root), _reader(root), blob))
            out.append(found)
    return tuple(out)


def _cited_file_line_rule_witness() -> "tuple[int, int, int, int, object]":
    """The CITED file's line numbering must follow git's rule, not Python's.

    `(ff, ff_control, cr, cr_control, nul)` -> `(1, 1, 1, 1, "CANNOT RUN")`.

    ⛔ r5 H1, AND THE REASON FOUR ENTRIES WERE WRONGLY RETIRED. #291 stopped comparing line numbers
    across the DOCUMENT boundary, so I retired the entries that defended `_reader`'s split rule —
    checking whether each ANCHOR still bound, when the question was whether each PROPERTY still
    existed. They differ exactly where code moves. The property survives on the other half of the
    comparison: a citation names a line IN A CITED FILE, and `_reader` numbers that file. A form
    feed or a lone `\r` in `lib/a.ts` shifts its numbering, so `:2` resolves to the wrong line and
    a blank line reads as populated. Measured: `splitlines()` and `read_text()` each returned
    (0, 1, 0, 1) — missed in the fixture, found in the control, which is a FAIL-OPEN.
    """
    import tempfile
    env = {"PATH": os.environ.get("PATH", ""), "HOME": "/nonexistent",
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
           "GIT_AUTHOR_NAME": "s", "GIT_AUTHOR_EMAIL": "s@e.com",
           "GIT_COMMITTER_NAME": "s", "GIT_COMMITTER_EMAIL": "s@e.com"}
    out = []
    # line 2 of the cited file must be BLANK for the citation to be a finding. With Python's rule
    # the separator splits line 1 in two, so the blank moves to line 3 and `:2` reads as populated.
    for cited_bytes in (b"a\x0cb\n\nthree\n", b"a-b\n\nthree\n",
                        b"a\rb\n\nthree\n", b"a_b\n\nthree\n", b"a\x00b\n\nthree\n"):
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
            (root / "lib" / "a.ts").write_bytes(cited_bytes)
            (root / "docs" / "seed.md").write_text("seed\n", encoding="utf-8")
            run("add", "-A"); run("commit", "-qm", "base")
            (root / "docs" / "x.md").write_text("see `lib/a.ts:2` here\n", encoding="utf-8")
            run("add", "-A")
            try:
                out.append(len(findings_for("docs/x.md", None, "HEAD", root,
                                            tracked_files(root), _reader(root), blob)))
            except (RuntimeError, OSError, ValueError):
                out.append("CANNOT RUN")
    return tuple(out)


def _unmerged_witness() -> "tuple[object, int]":
    """(a conflicted scoped document, the same content resolved and staged) -> `("CANNOT RUN", 1)`.

    ⛔ r5 H2. A conflicted merge leaves the index holding stages 1/2/3 and nothing at stage 0, so
    `:path` does not resolve — and that read as "the document was deleted", which passes. Measured
    rc=0 before this refusal, against rc=1 for the same bytes one `git add` later. The pair is the
    assertion: the second element proves the refusal is not simply refusing everything.
    """
    import tempfile
    env = {"PATH": os.environ.get("PATH", ""), "HOME": "/nonexistent",
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
           "GIT_AUTHOR_NAME": "s", "GIT_AUTHOR_EMAIL": "s@e.com",
           "GIT_COMMITTER_NAME": "s", "GIT_COMMITTER_EMAIL": "s@e.com"}
    out = []
    for resolve_it in (False, True):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)

            def run(*args: str, check: bool = True):
                r = subprocess.run(["git", "-C", tmp, "-c", "commit.gpgsign=false", *args],
                                   capture_output=True, text=True, env=env)
                if check and r.returncode != 0:
                    raise RuntimeError(f"fixture setup failed: git {' '.join(args)} -> "
                                       f"{r.stderr.strip()[:160]}")
                return r

            run("init", "-q", "--template=", "-b", "main")
            (root / "docs").mkdir(); (root / "lib").mkdir()
            (root / "lib" / "a.ts").write_text("one\n\nthree\n", encoding="utf-8")
            (root / "docs" / "x.md").write_text("base\n", encoding="utf-8")
            run("add", "-A"); run("commit", "-qm", "base")
            run("checkout", "-q", "-b", "side")
            (root / "docs" / "x.md").write_text("side `lib/a.ts:2`\n", encoding="utf-8")
            run("add", "-A"); run("commit", "-qm", "side")
            run("checkout", "-q", "main")
            (root / "docs" / "x.md").write_text("main text\n", encoding="utf-8")
            run("add", "-A"); run("commit", "-qm", "main")
            run("merge", "side", check=False)
            if resolve_it:
                (root / "docs" / "x.md").write_text("resolved `lib/a.ts:2`\n", encoding="utf-8")
                run("add", "-A")
            try:
                found = 0
                for path, source in changed_files("HEAD", root):
                    if in_scope(path):
                        found += len(findings_for(path, source, "HEAD", root,
                                                  tracked_files(root), _reader(root), blob))
                out.append(found)
            except (RuntimeError, OSError, ValueError):
                out.append("CANNOT RUN")
    return tuple(out)


def _real_reader_bounds_witness() -> "tuple[int, str, int]":
    """`_reader`'s own line count and message, over a REAL file rather than an injected world.

    `(3, "outside the file (3 lines)", 3)` — the count for a newline-terminated 3-line file, the
    message a citation of `:4` produces, and the count for the same content with NO final newline.

    ⛔ r5 M1, and the reason the existing boundary cases could not see it: they run over an injected
    `read` returning a plain list, which has no trailing phantom. `split("\n")` leaves one on every
    newline-terminated file, so the real reader measured 4 lines where git measures 3 — every
    out-of-range message overstated length by one, and `:4` landed on the phantom and was reported
    as A BLANK LINE rather than outside the file. A fixture that cannot reproduce production is not
    a witness for production.
    """
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "lib").mkdir()
        (root / "lib" / "a.ts").write_text("one\n\nthree\n", encoding="utf-8")
        (root / "lib" / "b.ts").write_text("one\n\nthree", encoding="utf-8")
        read = _reader(root)
        found = violations("docs/x.md", (("lib/a.ts", 4),), ("lib/a.ts",), read)
        msg = found[0].split("` ", 1)[1] if found else "(silent)"
        return (len(read("lib/a.ts")), msg, len(read("lib/b.ts")))


def _escaping_citation_witness() -> "tuple[object, int]":
    """(escaping the repo root, a VALID in-root citation, a BAD in-root citation) -> `(None, 0, 1)`.

    ⛔ r5 M6. `_reader` resolved `../outside.ts` against a file above the root and the guard fired
    on it, so the verdict depended on a file nobody reading the repository can see. The first
    element is the reader's answer for the escaping path — None, meaning "no such file here", which
    `resolve` then reports as unresolvable rather than silently passing.
    ⚠ THE SECOND AND THIRD ELEMENTS ARE THE CONTROL PAIR, and the first version of this witness got
    it wrong (r5-codex M2): it used only a blank-line citation, which fires whether the reader reads
    the blank line or refuses the file, so a reader returning None for everything satisfied it. A
    VALID citation must answer 0 and a BAD one must answer 1 — together they pin that the reader
    reads and the rule runs.
    """
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        base = pathlib.Path(tmp)
        (base / "repo" / "lib").mkdir(parents=True)
        (base / "outside.ts").write_text("one\n\nthree\n", encoding="utf-8")
        (base / "repo" / "lib" / "a.ts").write_text("one\n\nthree\n", encoding="utf-8")
        read = _reader(base / "repo")
        # ⛔ r5-codex M2: THE CONTROL MUST BE A VALID CITATION. The first version used a BLANK-line
        # citation, which produces one finding whether the reader reads the blank line or refuses
        # the file entirely — so a reader returning None for EVERY path satisfied it, and the
        # comment claiming otherwise was false. A populated line answers 0 only when the reader
        # actually read it; the bad one answers 1 only when the rule actually ran.
        good = violations("docs/x.md", (("lib/a.ts", 1),), ("lib/a.ts",), read)
        bad = violations("docs/x.md", (("lib/a.ts", 2),), ("lib/a.ts",), read)
        return (read("../outside.ts"), len(good), len(bad))


def _rename_config_witness() -> "tuple[int, int]":
    """A renamed document's OLD citations stay silent while a NEW one fires, both ways -> `(1, 1)`.

    ⛔ r5 M2. `-M` on both invocations is what makes this hold: with rename detection off, git
    reports a rename as a DELETE plus an ADD, the destination arrives with no source, its pre-image
    is its own path (absent from the base), and every citation in the moved document reads as newly
    gained. Measured before: six findings for a document that only moved.
    ⚠ Every other fixture in this suite NULLS the git configuration, which is why this property was
    unwitnessable — `diff.renames=false` is a setting a developer may genuinely have, and no fixture
    could express it.
    """
    import tempfile
    env = {"PATH": os.environ.get("PATH", ""), "HOME": "/nonexistent",
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
           "GIT_AUTHOR_NAME": "s", "GIT_AUTHOR_EMAIL": "s@e.com",
           "GIT_COMMITTER_NAME": "s", "GIT_COMMITTER_EMAIL": "s@e.com"}
    out = []
    for renames in ("false", "true"):
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
            (root / "lib" / "a.ts").write_text("one\n\nthree\n", encoding="utf-8")
            (root / "docs" / "old.md").write_text("old `lib/a.ts:2` here\n" + "padding\n" * 8,
                                                  encoding="utf-8")
            run("add", "-A"); run("commit", "-qm", "base")
            run("config", "diff.renames", renames)
            run("mv", "docs/old.md", "docs/new.md")
            # ⛔ r5-codex M2: AND A GENUINELY NEW BAD CITATION, so the answer is 1 and not 0. With
            # two pure renames the witness read (0, 0), which a `findings_for` returning `[]`
            # satisfies — it established that nothing fires, not that the pipeline still examines
            # what a document gained.
            (root / "docs" / "new.md").write_text(
                "old `lib/a.ts:2` here\n" + "padding\n" * 8 + "and NEW `lib/gone.ts:1`\n",
                encoding="utf-8")
            run("add", "-A")
            found = 0
            for path, source in changed_files("HEAD", root):
                if in_scope(path):
                    found += len(findings_for(path, source, "HEAD", root,
                                              tracked_files(root), _reader(root), blob))
            out.append(found)
    return tuple(out)


def _deleted_document_witness() -> "tuple[int, int]":
    """Deletion of a plain document, an edit to it, and deletion of a legacy UTF-16 one -> `(0, 1, 0)`.

    ⛔ r5 M3. A document removed from the index has no post-image, so it can gain nothing — and
    that clause had no case: removing it produced an uncaught TypeError rather than a finding.
    Deletion is the exact family r4-codex's M1 regressed, which is why it gets a case rather than
    an argument.
    ⛔ THE THIRD ELEMENT IS r5-codex M1: `findings_for` read the PRE-image first, so deleting a
    legacy UTF-16 document hit that image's NUL refusal and returned CANNOT RUN on an ordinary
    staged deletion. A document that is gone needs no pre-image read at all. ⚠ The original witness
    supplied only a readable text pre-image, which is exactly why it could not see this.
    """
    import tempfile
    env = {"PATH": os.environ.get("PATH", ""), "HOME": "/nonexistent",
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
           "GIT_AUTHOR_NAME": "s", "GIT_AUTHOR_EMAIL": "s@e.com",
           "GIT_COMMITTER_NAME": "s", "GIT_COMMITTER_EMAIL": "s@e.com"}
    out = []
    for delete_it, utf16 in ((True, False), (False, False), (True, True)):
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
            (root / "lib" / "a.ts").write_text("one\n\nthree\n", encoding="utf-8")
            body = "intro\n"
            (root / "docs" / "x.md").write_bytes(
                body.encode("utf-16-le") if utf16 else body.encode("utf-8"))
            (root / "docs" / "keep.md").write_text("keep\n", encoding="utf-8")
            run("add", "-A"); run("commit", "-qm", "base")
            if delete_it:
                (root / "docs" / "x.md").unlink()
            else:
                (root / "docs" / "x.md").write_text("intro\nsee `lib/a.ts:2`\n", encoding="utf-8")
            run("add", "-A")
            found = 0
            for path, source in changed_files("HEAD", root):
                if in_scope(path):
                    found += len(findings_for(path, source, "HEAD", root,
                                              tracked_files(root), _reader(root), blob))
            out.append(found)
    return tuple(out)


def _path_bytes_witness() -> "tuple[int, int, int, int]":
    """One finding for each of four document FILENAMES -> `(1, 1, 1, 1)`.

    `plain.md`, `a\rb.md`, `a\r\nb.md`, `a\nb.md` — each newly citing a path that does not resolve.

    ⛔ r5-codex H1. `changed_files` read git's NUL-delimited path stream with `text=True`, so
    Python's universal newlines translated a `\r` INSIDE A FILENAME into `\n`: `docs/a\rb.md`
    arrived as `docs/a\nb.md`, the blob lookup asked for a path that does not exist, the answer was
    None, and the staged document read as DELETED. Measured (1, 0, 0, 1) before the fix — the
    newline-named control fired while both carriage-return names passed.
    ⚠ The CONTROL here is the pair that always worked: a plain name and a newline-only name. A
    witness with only odd names cannot tell "handles odd names" from "handles nothing".
    """
    import tempfile
    env = {"PATH": os.environ.get("PATH", ""), "HOME": "/nonexistent",
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
           "GIT_AUTHOR_NAME": "s", "GIT_AUTHOR_EMAIL": "s@e.com",
           "GIT_COMMITTER_NAME": "s", "GIT_COMMITTER_EMAIL": "s@e.com"}
    out = []
    for name in ("plain.md", "a\rb.md", "a\r\nb.md", "a\nb.md"):
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
            run("add", "-A"); run("commit", "-qm", "base")
            (root / "docs" / name).write_text("see `lib/missing.ts:2` here\n", encoding="utf-8")
            run("add", "-A")
            found = 0
            for path, source in changed_files("HEAD", root):
                if in_scope(path):
                    found += len(findings_for(path, source, "HEAD", root,
                                              tracked_files(root), _reader(root), blob))
            out.append(found)
    return tuple(out)


def _cited_symlink_witness() -> "tuple[int, int]":
    """(a citation through a valid in-root symlink, the same through a regular path) -> `(0, 0)`.

    ⛔ r5-codex H2, THE SIXTH LIVE RETIREMENT. `lib/link.ts -> a.ts` and `lib/link.ts:1` names a
    POPULATED line, so the answer is silence — and a refusal would be a false one. Codex reinstated
    the retired r4-codex M2 mutation (an `is_symlink()` raise inside `_reader`) and the suite stayed
    at 75/75: the shipped behaviour was right and nothing measured it.
    ⚠ I had assumed the directory-reader mutation covered this. It does not: refusing a DIRECTORY
    and accepting a SYMLINK are different properties of the same `if`, and only one had a case.
    ⚠ The second element is the control — the identical citation through the real path — so "resolves
    nothing" cannot satisfy this pair.
    """
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "lib").mkdir()
        (root / "lib" / "a.ts").write_text("one\n\nthree\n", encoding="utf-8")
        (root / "lib" / "link.ts").symlink_to("a.ts")
        read = _reader(root)
        through_link = violations("docs/x.md", (("lib/link.ts", 1),), ("lib/link.ts", "lib/a.ts"), read)
        direct = violations("docs/x.md", (("lib/a.ts", 1),), ("lib/a.ts",), read)
        return (len(through_link), len(direct))


def self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: it builds git repositories (backlog #373)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    """78 cases. The count is declared in the module docstring and verified by running this."""
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
         lambda: len(violations("docs/x.md", added_citations("", "see `lib/a.ts:2`"), tracked, read)) == 1)
    case("the blank message names the reader's experience",
         lambda: "lands on nothing" in first(violations("docs/x.md", added_citations("", "`lib/a.ts:2`"), tracked, read)))
    case("a line past EOF fires",
         lambda: len(violations("docs/x.md", added_citations("", "`lib/a.ts:99`"), tracked, read)) == 1)
    case("the out-of-range message states the file length",
         lambda: "3 lines" in first(violations("docs/x.md", added_citations("", "`lib/a.ts:99`"), tracked, read)))
    case("an unresolvable path fires",
         lambda: len(violations("docs/x.md", added_citations("", "`lib/gone.ts:1`"), tracked, read)) == 1)
    case("a populated cited line is silent",
         lambda: violations("docs/x.md", added_citations("", "`lib/a.ts:1`"), tracked, read) == [])
    case("line 3 (last line) is in range",
         lambda: violations("docs/x.md", added_citations("", "`lib/a.ts:3`"), tracked, read) == [])
    case("a line number of 0 fires rather than reading the last line",
         lambda: len(violations("docs/x.md", added_citations("", "`lib/a.ts:0`"), tracked, read)) == 1)

    case("a readable file that is NOT in the tracked list still resolves",
         lambda: violations("docs/x.md", added_citations("", "`lib/a.ts:1`"), (), read) == [])
    case("...and the same path with a blank cited line still fires, so it is not passing blindly",
         lambda: len(violations("docs/x.md", added_citations("", "`lib/a.ts:2`"), (), read)) == 1)

    case("a unique multi-segment suffix resolves and is silent",
         lambda: violations("docs/x.md", added_citations("", "`html-doc/ensure.ts:1`"),
                    ("lib/html-doc/ensure.ts",), read) == [])
    case("an AMBIGUOUS suffix FIRES rather than being skipped",
         lambda: len(violations("docs/x.md", added_citations("", "`html-doc/ensure.ts:1`"), tracked, read)) == 1)
    case("the ambiguous message says how many matched",
         lambda: "ambiguous: 2" in first(violations("docs/x.md", added_citations("", "`html-doc/ensure.ts:1`"),
                                            tracked, read)))
    case("a suffix match still range-checks",
         lambda: len(violations("docs/x.md", added_citations("", "`html-doc/ensure.ts:99`"),
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
    # ⛔ r3-codex MEDIUM: a PURE RENAME must add nothing. Without the source path in the pathspec
    # git cannot match the halves, and every citation in the moved document reports as newly
    # added — which contradicts the added-lines-only contract the whole scope argument rests on.
    case("⛔ a pure rename of a document with a BAD citation adds nothing",
         lambda: _rename_witness() == 0)
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
    # ── #291: what git is asked, and what its answers mean ─────────────────────────────────────
    # ⛔ r5 H1 — the CITED file's numbering, which four retired entries used to defend. The pairs are
    # the assertion: each fixture and its one-character control must AGREE, and the fifth element is
    # the NUL refusal. Measured before this case existed: `splitlines()` and `read_text()` each gave
    # (0, 1, 0, 1) — a fail-open with a green suite.
    # ⛔ r5-codex H1 — a CR inside a FILENAME, which `text=True` rewrote before the blob lookup saw
    # it. The plain and newline-only names are the controls: they always worked.
    case("⛔ a carriage return in a document's FILENAME does not lose the document",
         lambda: _path_bytes_witness() == (1, 1, 1, 1))
    # ⛔ r5 H2 — a THIRD git answer that was collapsing into one of the two `blob` distinguishes.
    # ⛔ r5 M1 — the REAL reader, because the injected one has no trailing phantom and so cannot
    # reproduce the defect. Third element: a file with no final newline must be unaffected.
    # ⛔ r5 M2 — `-M` under a developer's own `diff.renames=false`; every other fixture here nulls
    # the git config, which is exactly why this was unwitnessable.
    # ⚠ ONE STRING LITERAL, not a continuation: a case name split across lines is read as only its
    # FIRST fragment by anything that greps `case("…")` — including the manifest validation that
    # caught this — so a split name silently breaks the join between an entry and its case.
    case("⛔ a rename keeps old citations silent with detection OFF; only the new one fires",
         lambda: _rename_config_witness() == (1, 1))
    # ⛔ r5 M3 — the deleted-document clause had no case: removing it raised TypeError.
    case("⛔ a DELETED document gains nothing — even a legacy UTF-16 one — while an edit still fires",
         lambda: _deleted_document_witness() == (0, 1, 0))
    # ⛔ r5-codex H2 — an ordinary cited code symlink must RESOLVE, not be refused. A refusal here
    # was shipped once (r4-codex M2) and its entry was then retired, leaving the property unmeasured.
    case("⛔ a citation through a valid in-root symlink resolves, exactly as the direct path does",
         lambda: _cited_symlink_witness() == (0, 0))
    case("...and the same symlink with a BLANK cited line still fires, so it is really being read",
         lambda: len(violations("docs/x.md", (("lib/a.ts", 2),), ("lib/a.ts",), read)) == 1)
    # ⛔ r5 M6 — a citation may not resolve outside the repository.
    case("⛔ a citation escaping the repository root does not resolve, while in-root ones behave",
         lambda: _escaping_citation_witness() == (None, 0, 1))
    case("⛔ the real reader counts git's lines, and :N+1 is outside the file, not blank",
         lambda: _real_reader_bounds_witness() == (3, "is outside the file (3 lines)", 3))
    case("⛔ a conflicted document is CANNOT RUN, and the same content resolved still fires",
         lambda: _unmerged_witness() == ("CANNOT RUN", 1))
    case("⛔ a form feed or lone CR in the CITED file does not shift its line numbering",
         lambda: _cited_file_line_rule_witness() == (1, 1, 1, 1, "CANNOT RUN"))
    case("⛔ a missing pre-image is None while a broken ref or root is CANNOT RUN — never confused",
         lambda: _blob_witness() == (None, "see `lib/a.ts:2` here\n",
                                     "CANNOT RUN", "CANNOT RUN", "CANNOT RUN"))
    case("⛔ the guard reads the INDEX, so an unstaged edit is invisible and a staged one fires",
         lambda: _staged_witness() == (0, 1))
    # ── #291: `findings_for` driven with NO repository at all, which varies every parameter the
    # ── three repository witnesses pass one value (check-fixture-variation.py)
    case("findings_for is a pure orchestration given an injected blob reader",
         lambda: len(findings_for(
             "docs/y.md", None, "HEAD~4", pathlib.Path("/not-a-repo"), ("lib/a.ts",),
             lambda c: ["one", "", "three"] if c == "lib/a.ts" else None,
             lambda ref, _r: "" if ref.startswith("HEAD~4") else "see `lib/a.ts:2` here")) == 1)
    # ⚠ The pre-image of a PROMOTED document is its OWN path in the base, where it did not exist —
    # so the stub answers None there, which is the shape git reports. My first version of this
    # fixture returned text for every ref, so pre == post, nothing was gained and the case failed
    # for a reason that had nothing to do with the property.
    case("...and a PROMOTED document's pre-image is its own path, never its out-of-scope source",
         lambda: len(findings_for(
             "docs/z.md", "docs/reviews/old.md", "HEAD~5", pathlib.Path("/nor-this"), (),
             lambda c: None,
             lambda ref, _r: "see `lib/gone.ts:1`" if ref == ":docs/z.md" else None)) == 1)
    case("⛔ ...while an IN-SCOPE rename reads the source, so the same citation is not gained",
         lambda: findings_for(
             "docs/new.md", "docs/old.md", "HEAD~6", pathlib.Path("/nope"), (),
             lambda c: None,
             lambda ref, _r: "see `lib/gone.ts:1`") == [])

    case("⛔ changed_files reports (destination, source), not the reverse",
         lambda: _rename_orientation_witness() == ("docs/new.md", "docs/old.md"))
    # ⛔ r4 L3, adjacent to H3 — nothing distinguished the reader's treatment of a non-regular
    # path. A directory must read as None (becoming a finding), never raise out of the reader.
    case("⛔ the reader answers None for a DIRECTORY rather than raising out of itself",
         lambda: _reader(pathlib.Path("."))("docs") is None)
    case("...and still reads a regular file, so it is not answering None to everything",
         lambda: isinstance(_reader(pathlib.Path("."))("scripts/check-doc-citations.py"), list))


    # ── #291: the multiset, which is what makes "gained" mean what it says ──────────────────────
    case("a citation written a SECOND time is gained, so counts matter and not membership",
         lambda: added_citations("see `lib/a.ts:2`", "see `lib/a.ts:2`\nand `lib/a.ts:2` again")
                 == (("lib/a.ts", 2),))
    case("...and writing it once more again gains one more, not two",
         lambda: len(added_citations("a `lib/a.ts:2`\nb `lib/a.ts:2`",
                                    "a `lib/a.ts:2`\nb `lib/a.ts:2`\nc `lib/a.ts:2`")) == 1)
    case("a citation REMOVED is not gained",
         lambda: added_citations("see `lib/a.ts:2` here", "nothing here") == ())
    case("a citation merely MOVED within the document is not gained",
         lambda: added_citations("x\nsee `lib/a.ts:2`\ny", "y\nx\nsee `lib/a.ts:2`") == ())
    case("⛔ ...and that is the whole difference from the old rule, which examined it",
         lambda: added_citations("", "see `lib/a.ts:2`") == (("lib/a.ts", 2),))
    case("an EMPTY pre-image makes every citation in the document gained",
         lambda: len(added_citations("", "a `lib/a.ts:1` b `lib/b.ts:2`")) == 2)
    case("two DIFFERENT citations on one line are both gained",
         lambda: len(added_citations("", "`lib/a.ts:1` and `lib/b.ts:2`")) == 2)

    # ⛔ THE CENTRAL PROPERTY OF #291, and the successor to the old "a line NOT in the added set is
    # never examined": what decides is whether the citation is NEW TO THE DOCUMENT, not where it
    # sits. The pair is the assertion — the same document text, examined against two pre-images.
    case("⛔ a citation present in BOTH images is not examined",
         lambda: violations("docs/x.md",
                            added_citations("old `lib/a.ts:2` here", "old `lib/a.ts:2` here\nnew"),
                            tracked, read) == [])
    case("...and the same text IS examined when the pre-image lacks it",
         lambda: len(violations("docs/x.md",
                                added_citations("nothing here", "old `lib/a.ts:2` here\nnew"),
                                tracked, read)) == 1)
    case("a document line beginning `++` is examined like any other",
         lambda: len(violations("docs/x.md", added_citations("", "++ `lib/a.ts:99`"), tracked, read)) == 1)

    # ⛔ r4 M7 — the out-of-range boundary was tested only 96 lines past the end. `:4` over a
    # 3-line file is the single commonest drift there is: a file that lost its last line. Negatives
    # have to be ADJACENT to be falsifiable.
    case("⛔ the line immediately past the end fires, not only one far past it",
         lambda: len(violations("docs/x.md", added_citations("", "`lib/a.ts:4`"), tracked, read)) == 1)
    case("...and the last line itself does not, so the boundary is pinned from both sides",
         lambda: violations("docs/x.md", added_citations("", "`lib/a.ts:3`"), tracked, read) == [])
    # ⛔ r4 L3 — the suffix match's SEGMENT BOUNDARY had no case: without the leading slash,
    # `c/ensure.ts` would resolve to `lib/html-doc/ensure.ts`, which is a different file.
    case("⛔ a suffix must match at a path SEGMENT boundary, not mid-segment",
         lambda: len(violations("docs/x.md", added_citations("", "`c/ensure.ts:1`"),
                                ("lib/html-doc/ensure.ts",), read)) == 1)
    # ⛔ r4 L3 — `CITE`'s trailing `\b` had no case: without it `lib/a.ts:12abc` becomes a
    # citation of line 12.
    case("⛔ a line number glued to more text is not a citation",
         lambda: violations("docs/x.md", added_citations("", "`lib/a.ts:2abc`"), tracked, read) == [])
    case("backticks are optional",
         lambda: len(violations("docs/x.md", added_citations("", "see lib/a.ts:2 here"), tracked, read)) == 1)
    case("a [param] path segment parses",
         lambda: len(violations("docs/x.md", added_citations("", "`app/[id]/r.ts:1`"), tracked, read)) == 1)
    case("two citations on one line are both examined",
         lambda: len(violations("docs/x.md", added_citations("", "`lib/a.ts:2` and `lib/a.ts:99`"), tracked, read)) == 2)
    case("a bare filename with no directory is NOT a citation",
         lambda: violations("docs/x.md", added_citations("", "`a.ts:2`"), tracked, read) == [])
    case("a docs/*.md target can itself be cited",
         lambda: violations("docs/x.md", added_citations("", "`docs/notes.md:1`"), tracked, read) == [])
    case("...and a BAD markdown target fires, so the form is really examined",
         lambda: len(violations("docs/x.md", added_citations("", "`docs/notes.md:9`"), tracked, read)) == 1)
    case("a URL is not a citation, so its port cannot become a path",
         lambda: violations("docs/x.md", added_citations("", "http://localhost:3000/lib/a.ts:2"), tracked, read) == [])
    case("a citation wrapped in prose parentheses does not capture the bracket",
         lambda: violations("docs/x.md", added_citations("", "(lib/a.ts:1)"), tracked, read) == [])

    # --- main() is DRIVEN over a constructed world (ADR-0014), to every exit code ---------------
    import contextlib
    import io

    seen: dict = {}

    def drive(changed, pre, post, reader, git_ok: bool = True, argv=None,
              root=pathlib.Path("/nonexistent"), blob_fails: bool = False,
              oserror_on_list: bool = False) -> int:
        """`main()` over a constructed world, to every exit code (ADR-0014).

        ⟳ #291: the world is now BLOBS, not a diff — `pre` and `post` are the document's text
        before and after, which is exactly what `blob()` returns from git. There is no diff text in
        this suite at all any more, which is the change this rebuild is for.
        """
        def fetch_changed(base, r):
            seen["base"], seen["root"] = base, r
            if not git_ok:
                raise RuntimeError("git diff --name-status origin/nope failed: unknown revision")
            if oserror_on_list:
                # the FIRST arm's OSError: git is unreachable as a process, not as a repository
                raise OSError("[Errno 2] No such file or directory: 'git'")
            return tuple((c, None) for c in changed)

        def fetch_blob(ref_path, r):
            if blob_fails:
                raise RuntimeError("git cat-file -p failed: unreadable repository")
            return post if ref_path.startswith(":") else pre

        def make_reader(_r):
            def read_one(path):
                return reader(path)
            return read_one

        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return main(argv if argv is not None else [], root=root,
                        fetch_changed=fetch_changed,
                        fetch_blob=fetch_blob,
                        fetch_tracked=lambda _r: tracked,
                        make_reader=make_reader)

    def raises(_p):
        raise PermissionError("fixture is unreadable")

    case("main() returns 0 over a clean world",
         lambda: drive(("docs/x.md",), "", "`lib/a.ts:1`", read) == 0)
    case("main() returns 1 when a citation has drifted",
         lambda: drive(("docs/x.md",), "", "`lib/a.ts:2`", read) == 1)
    case("⛔ main() returns 2 — CANNOT RUN — when git cannot be reached, never 0",
         lambda: drive((), "", "", read, git_ok=False) == 2)
    # ⛔ r2-codex Medium: this handler had NO witness — replacing its `return 2` with `return 0`
    # left 40/40 green. An existing-but-unreadable cited file is CANNOT RUN, never a finding.
    case("⛔ main() returns 2 when a cited file exists but cannot be READ",
         lambda: drive(("docs/x.md",), "", "`lib/a.ts:1`", raises) == 2)
    case("...and an out-of-scope changed file is never diffed at all",
         lambda: drive(("scripts/x.md",), "", "`lib/a.ts:2`", read) == 0)

    # ── the parameters this suite had been passing ONE value, each now varied by a case that
    # ── asserts a real property rather than a cosmetically different argument (11 findings,
    # ── check-fixture-variation.py; an exemption resting on nothing is worse than none)
    case("the finding names the DOCUMENT it was handed, not a path baked into the rule",
         lambda: "docs/adr/0001-x.md:" in first(
             violations("docs/adr/0001-x.md", added_citations("", "`lib/a.ts:2`"), tracked, read)))
    case("⛔ the injected reader IS the existence oracle — nothing resolves without it",
         lambda: len(violations("docs/x.md", added_citations("", "`lib/a.ts:1`"), tracked, lambda _p: None)) == 1)
    case("⛔ changed_files on a path that is no repository is CANNOT RUN, not an empty change set",
         lambda: isinstance(_try(lambda: changed_files("HEAD", pathlib.Path("/nonexistent"))),
                    RuntimeError))
    case("⛔ tracked_files on a path that is no repository RAISES rather than passing over nothing",
         lambda: isinstance(_try(lambda: tracked_files(pathlib.Path("/nonexistent"))), RuntimeError))

    # ⟳ #291 RETIRED TWO CANNOT RUN CASES WITH THEIR SUBJECTS — "a hunk header does not parse" and
    # "git adds lines to a document that cannot be read". There is no hunk header to misparse and no
    # document read from the filesystem. What replaces them is the ONE remaining CANNOT RUN: git
    # itself failing, which must never read as "this document gained no citations".
    # ⛔ r5 H1 — main() has TWO exception arms and the review named one. Measured separately: the
    # FIRST arm's OSError and the SECOND arm's ValueError were both unwitnessed, and the ValueError
    # clause is live — `int()` on an absurd line number raises it (the review's own L9).
    case("⛔ main() returns 2 when the file list itself raises OSError, never 0",
         lambda: drive(("docs/x.md",), "", "`lib/a.ts:2`", read, oserror_on_list=True) == 2)
    case("⛔ main() returns 2 on a line number too large to parse, never a traceback",
         lambda: drive(("docs/x.md",), "", "`lib/a.ts:" + "9" * 4400 + "`", read) == 2)

    case("⛔ main() returns 2 when reading a blob fails, never 0",
         lambda: drive(("docs/x.md",), "", "`lib/a.ts:2`", read, blob_fails=True) == 2)
    # ⛔ check-fixture-variation.py, 11 findings on this file: a parameter every call site passes
    # the same value is indistinguishable from a literal. These two read back what was carried.
    case("--base reaches the fetchers rather than a hardcoded default",
         lambda: drive(("docs/x.md",), "", "`lib/a.ts:1`", read,
               argv=["--base", "HEAD~1"]) == 0 and seen["base"] == "HEAD~1")
    case("...and the default base is origin/master, not whatever ran last",
         lambda: drive(("docs/x.md",), "", "`lib/a.ts:1`", read) == 0 and seen["base"] == "origin/master")
    case("--root reaches the fetchers as the resolved path it names",
         lambda: drive(("docs/x.md",), "", "`lib/a.ts:1`", read,
               argv=["--root", "/tmp"]) == 0 and seen["root"] == pathlib.Path("/tmp").resolve())
    case("...and without --root it is the root main() was handed",
         lambda: drive(("docs/x.md",), "", "`lib/a.ts:1`", read,
               root=pathlib.Path("/elsewhere")) == 0
         and seen["root"] == pathlib.Path("/elsewhere"))

    print(f"{passed}/{passed + failed} passed")
    return 1 if failed else 0


def main(
    argv: list[str],
    root: pathlib.Path = ROOT,
    fetch_changed=changed_files,
    fetch_blob=blob,
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
                                  tracked, read, fetch_blob)
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

    # ⚠ THE MESSAGE NAMES WHAT WAS EXAMINED. Both images come from git (#291), so this reads the
    # INDEX, not the working tree — an unstaged edit is invisible and the reader must not have to
    # discover that. In CI they are the same thing.
    print("doc citations OK — every `path:line` newly cited in a STAGED docs/ change resolves "
          "to a real line\n  (unstaged edits are not examined — `git add` and re-run)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
