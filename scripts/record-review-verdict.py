#!/usr/bin/env python3
"""Record the verdict a CLAUDE review half leaves — the same record a Codex run leaves.

    python3 scripts/record-review-verdict.py --review-id <subject>-r<N>-claude --head <sha> [--prompt <brief>]
    python3 scripts/record-review-verdict.py --self-test  # 98 cases

Run by the COORDINATOR after a Claude half is filed at `docs/reviews/claude/<review-id>.md`.

WHY THIS EXISTS (the owner's review-budget decision, 2026-10-31)
----------------------------------------------------------------
`check-review-recorded.py` asks whether any round saw the code about to merge, and it answers from
`docs/reviews/verdicts/*.verdict.json`. Only `codex-review.py` wrote one, so a branch whose last
round was a Claude half could not answer at all — and the measured response was to spend a Codex
run for no reason except to leave a verdict file: 31 such rounds in the 14 days to 2026-10-31,
about 7.4% of the Codex weekly limit. The round cap in `docs/review-method.md` (§0 Q4) leaves
rounds 2-3 to ONE half each, so a Claude round must be able to testify for itself.

THE DESIGN, AND WHY IT IS THIS SMALL
------------------------------------
The consumers already accept the record. `check-review-recorded.branch_verdicts` reads every
`.json` the branch ADDED under `docs/reviews/verdicts/` and never asks who wrote it;
`check-review-rounds.verdict_problems` joins `review` to the filenames on disk. So the only thing
missing was a PRODUCER, and the producer's one job is to write the record `codex-review.py` would
have written. It therefore owns no schema of its own: the record is `codex-review.verdict_record`,
the path is `codex-review.verdict_path`, the filed review is `codex-review.promotion_path`, the id
grammar is `codex-review.review_identity`, the overwrite rule is `codex-review.overwrite_refusal`
and the write is `codex-review.write_verdict` — all IMPORTED. A second copy of any of them would
be a second implementation of one join, this repo's most-repeated defect. It adds two fields,
`tool` (who wrote it) and `writer: claude`, which no consumer reads.

WHAT MAKES IT NOT A RUBBER STAMP
--------------------------------
A Codex verdict is written by the process that ran the review, at dispatch. This one is written
afterwards by the coordinator, so `head` is the coordinator's statement — and the defence is that
every way of stating it wrongly fails CLOSED or is refused:

  * `head` must resolve to a COMMIT here, and is recorded as the full sha.
  * ⟳ PR #457 r1 (H1, both halves): THE TREE IS OBSERVED, NOT ASSERTED. `head` and `dirty` are what
    `codex-review.reviewed_state` reads from the checkout, and `--head` must EQUAL the HEAD it reads.
    The first version wrote a literal `dirty: {}` — which `reviewed_state` defines as *the tree WAS
    clean* — without looking. Reproduced end to end: a reviewer handed an uncommitted `GOOD`, the
    fix then reverted and `BAD` merged, and `check-review-recorded` passed. That is the r11 Blocking
    `tail_candidates` exists to close, reopened by the producer: the union it relies on is empty
    when the overlay is. A `None` overlay (the tree could not be described) is recorded as `None`,
    exactly as the wrapper records it, and the consumer counts it UNUSABLE.
  * the filed review must DECLARE that commit, and state its verdict, at two FIXED POSITIONS:
    its FIRST line is exactly `Reviewed head: <full sha>` and must equal `head`, and its LAST
    non-empty line is exactly `VERDICT: CONVERGED` or `VERDICT: NOT CONVERGED`, RECORDED as
    `verdict`. Each line is matched whole, and nothing else in the file is read for either.
    ⟳ r1 (Codex High, Claude M1): any hex token anywhere used to count, so a review naming the head
    only to DISPUTE it was recorded against it. ⟳⟳ r2 (Codex H1, M2, M3): r1's repair then searched
    free Markdown for "the reviewer's own line", and an HTML comment, an indented block, a lazy quote
    continuation, a nested fence and a verdict PREFIX each beat it. A parser of hostile Markdown
    keeps losing; a position does not parse, so the class is gone rather than patched. The position
    is the contract, not the rendering: a review is read by this tool, and a reviewer who wants its
    last line read as its verdict writes it there. No other script parses a review's verdict word
    (searched: `scripts/*.py` for `CONVERGED`), so this is the one rule.
  * no symlink is followed, at the review or at the verdict (r1 L3, both halves): a link let a file
    outside `docs/reviews/` be testified to, and a dangling one let the verdict be written outside
    `docs/reviews/verdicts/`.
  * a later commit cannot forge it: `check-review-recorded.round_tail` compares every guarded path
    changed after `head` against the merging tree, as it always has for Codex.
  * an existing verdict is never overwritten — there is no `--allow-overwrite`; delete it in a
    commit someone can see.
  * the review must be substantive (`codex-review.MIN_REVIEW_CHARS`) and state a verdict
    (`CONVERGED` / `NOT CONVERGED`): a file with no verdict is a failed run, as `docs/plugins.md`
    says of a review doc with no findings section.
  * the id must name a CLAUDE half. A Codex verdict through this door would testify that Codex ran
    when nothing ran it.

⚠ BOUNDS, STATED. A coordinator who edits the review document to name a later commit, then records
it, defeats this; that is a deliberate act in a reviewable diff, not an accident this can see. And
like the Codex record, it says what was IN the tree at `head`, not what the reviewer READ.
⚠ THE TREE IS OBSERVED AT RECORD TIME, NOT AT REVIEW TIME — the one place this is weaker than the
wrapper, which observes at dispatch. A fix the reviewer saw and the coordinator reverted BEFORE
recording is not in the overlay, so record as soon as the half is filed, in the tree it reviewed,
before any fold edit. Closing it needs a dispatch-time snapshot — a new mechanism, filed as
backlog #435.

Exit codes: 0 = recorded   1 = REFUSED, nothing written   2 = CANNOT RUN (the write failed)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from importlib import import_module

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_cx = import_module("codex-review")

REPO_ROOT = _cx.REPO_ROOT
WRITER = "claude"
TOOL = "record-review-verdict"
RC_WRITTEN, RC_REFUSED, RC_CANNOT_RUN = 0, 1, 2
# ⟳ PR #457 r2: the declaration and the verdict live at FIXED POSITIONS — the first line and the last
# non-empty line — matched WHOLE, and nothing else in the file is read for either. The r1 rule looked
# for "the reviewer's own line" in free Markdown, and lost to an HTML comment, an indented block, a
# lazy quote continuation, a nested fence and a prefix: each a construct it did not model. A position
# needs no model of Markdown, so no Markdown construct can move it.
HEAD_LINE = re.compile(r"Reviewed head: ([0-9a-f]{40}|[0-9a-f]{64})")
VERDICT_LINE = re.compile(r"VERDICT: (NOT CONVERGED|CONVERGED)")


def _lines(text: str) -> "list[str]":
    """PURE. The file's lines, split on `\n` only (a CRLF's `\r` dropped). Not `splitlines()`,
    which also splits on separators Markdown renders inside one line."""
    return [line[:-1] if line.endswith("\r") else line for line in text.split("\n")]


def declared_head(text: str) -> "str | None":
    """PURE. The full sha the FIRST line declares — exactly `Reviewed head: <sha>` — or None."""
    m = HEAD_LINE.fullmatch(_lines(text)[0])
    return m.group(1) if m else None


def review_verdict(text: str) -> "str | None":
    """PURE. The verdict the LAST non-empty line states — exactly `VERDICT: CONVERGED` or
    `VERDICT: NOT CONVERGED` — or None."""
    last = next((line for line in reversed(_lines(text)) if line.strip()), "")
    m = VERDICT_LINE.fullmatch(last)
    return m.group(1) if m else None


def link_problem(path: str, root: str) -> "str | None":
    """Why `path` cannot be read or written without following a symlink, or None. Reads the fs."""
    real = os.path.join(os.path.realpath(root), os.path.relpath(path, root))
    if os.path.realpath(path) != real:
        return (f"SYMLINK — {path} resolves through a link to {os.path.realpath(path)}; a review "
                f"or verdict is testified to only where it is, never through a link")
    return None


def review_problem(body: "str | None", head: str) -> "str | None":
    """PURE. Why this filed review cannot be testified to, or None. The first word is the rule."""
    if body is None:
        return "MISSING — the review is not filed where check-review-rounds pairs it"
    text = body.strip()
    if len(text) < _cx.MIN_REVIEW_CHARS:
        return (f"EMPTY — {len(text)} characters, under the {_cx.MIN_REVIEW_CHARS} below which "
                f"codex-review.py refuses to call a message a review")
    if review_verdict(body) is None:
        return ("NO VERDICT — the last non-empty line is not exactly `VERDICT: CONVERGED` or "
                "`VERDICT: NOT CONVERGED`")
    # The UNSTRIPPED body: the first line is line 1 of the file, not the first line with text.
    declared = declared_head(body)
    if declared is None:
        return (f"HEAD NOT NAMED — the first line is not exactly `Reviewed head: <full sha>`, so "
                f"the review cannot be recorded as having seen {head[:12]}")
    if declared != head:
        return f"HEAD MISMATCH — the review declares {declared}, which is not {head} here"
    return None


def writer_problem(review_id: str) -> "str | None":
    """PURE. Why this id cannot be recorded HERE, or None. The grammar is codex-review's."""
    who, refusal = _cx.review_identity(review_id)
    # ONE clause: an id the grammar refuses has `who is None`, so it is answered here too — with the
    # grammar's own sentence when there is one. Two clauses would mask each other under mutation.
    if who != WRITER:
        return refusal or (f"REFUSED — {review_id!r} names the `{who}` half. Its verdict is written by "
                f"codex-review.py, the process that ran it; recording one here would testify "
                f"that a gate ran when nothing ran it")
    return None


def resolve_head(root: str, head: str) -> "str | None":
    """The full sha `head` names in the repository at `root`, or None if it is not a commit."""
    try:
        p = subprocess.run(["git", "-C", root, "rev-parse", "--verify", "--quiet",
                            f"{head}^{{commit}}"], capture_output=True, text=True, timeout=60,
                           env=_cx.unredirected())
    except (OSError, subprocess.SubprocessError):
        return None
    out = p.stdout.strip()
    return out if p.returncode == 0 and out else None


def claude_record(*, review_id: str, head: str, dirty: "dict[str, str] | None", tree: str,
                  prompt: "str | None", chars: int, verdict: str) -> dict:
    """PURE. `codex-review.verdict_record`, with the fields that say a Claude half left it.

    `dirty` is what `reviewed_state` OBSERVED, passed through unchanged — `None` stays `None`."""
    rec = _cx.verdict_record(gate_ran=True, exit_code=0, review_id=review_id,
                             reason=f"claude half filed: {chars} chars, names {head[:12]}",
                             head=head, dirty=dirty, prompt=prompt, tree=tree)
    rec["tool"] = TOOL
    rec["writer"] = WRITER
    rec["verdict"] = verdict
    return rec


def _in_root(path: str, root: str) -> str:
    """`codex-review`'s path for this id, moved from its checkout to `root`."""
    return os.path.join(root, os.path.relpath(path, REPO_ROOT))


def main(argv: "list[str]", root: "str | None" = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--review-id", required=True, help="<subject>-r<N>-claude, no .md")
    ap.add_argument("--head", required=True, help="the commit the half was handed")
    ap.add_argument("--prompt", help="the brief the half was dispatched with (recorded, not read)")
    if argv == ["--self-test"]:
        return self_test()
    args = ap.parse_args(argv)
    root = root or REPO_ROOT

    def refuse(why: str) -> int:
        print(f"{why}\n  Nothing was written. TREAT THIS ROUND AS HAVING NO VERDICT.",
              file=sys.stderr)
        return RC_REFUSED

    problem = writer_problem(args.review_id)
    if problem:
        return refuse(problem)
    vpath = _in_root(_cx.verdict_path(args.review_id), root)
    rpath = _in_root(_cx.promotion_path(args.review_id, WRITER), root)
    for path in (vpath, rpath):
        linked = link_problem(path, root)
        if linked:
            return refuse(linked)
    # `lexists`: a dangling link EXISTS. (It is refused above; this is the overwrite rule's input.)
    exists = _cx.overwrite_refusal(vpath, exists=os.path.lexists(vpath), allow_overwrite=False,
                                   what="the verdict")
    if exists:
        return refuse(exists)
    head = resolve_head(root, args.head)
    if head is None:
        return refuse(f"REFUSED — {args.head!r} is not a commit in {root}")
    seen, dirty = _cx.reviewed_state(root)
    if seen != head:
        return refuse(f"TREE MOVED — {root} is at {seen or 'no readable HEAD'}, not {head[:12]}. "
                      f"Record in the tree the half reviewed, before any fold edit or commit")
    try:
        with open(rpath, encoding="utf-8", errors="replace") as f:
            body: "str | None" = f.read()
    except OSError:
        body = None
    problem = review_problem(body, head)
    if problem:
        return refuse(f"{problem}\n  review: {rpath}")
    rec = claude_record(review_id=args.review_id, head=head, dirty=dirty, tree=root,
                        prompt=args.prompt, chars=len((body or "").strip()),
                        verdict=review_verdict(body or "") or "")
    err = _cx.write_verdict(vpath, rec)
    if err:
        print(f"CANNOT RUN — the verdict could not be written ({err}). TREAT THIS AS NOT RUN.",
              file=sys.stderr)
        return RC_CANNOT_RUN
    print(f"[record-review-verdict] gate_ran=true head={head[:12]} -> {vpath}")
    return RC_WRITTEN


def self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: every `--self-test` runs isolated (backlog #382)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    import contextlib
    import io
    import pathlib
    import tempfile
    import fixture_git

    cases: list[tuple[str, object, object]] = []

    def case(name: str, got, want) -> None:
        cases.append((name, got, want))

    def first(problem) -> str:
        return (problem or "").split(" — ")[0]

    H = "0123456789abcdef0123456789abcdef01234567"
    OTHER = "fedcba9876543210fedcba9876543210fedcba98"
    PAD = "x" * _cx.MIN_REVIEW_CHARS
    GOOD = f"Reviewed head: {H}\n\n# x — round 1 — Claude half\n\n{PAD}\n\nVERDICT: CONVERGED\n"

    # ── the review-file rule, pure ──
    case("a missing review file is refused", first(review_problem(None, H)), "MISSING")
    case("an empty review file is refused", first(review_problem("", H)), "EMPTY")
    case("...and so is a whitespace-only one, which is empty after strip",
         first(review_problem("   \n\t\n", H)), "EMPTY")
    case("a stub under the minimum length is refused",
         first(review_problem(f"Reviewed head: {H}\nVERDICT: CONVERGED\n", H)), "EMPTY")
    case("a review stating no verdict is refused — a finding-less file is a failed run",
         first(review_problem(GOOD.replace("VERDICT: CONVERGED", "done"), H)), "NO VERDICT")
    case("...and `NOT CONVERGED` is a verdict, not its absence",
         review_problem(GOOD.replace("CONVERGED", "NOT CONVERGED"), H), None)
    case("a review that never names the head it was handed is refused",
         first(review_problem(GOOD.replace(f"Reviewed head: {H}", "Reviewed."), H)), "HEAD NOT NAMED")
    case("...and naming a DIFFERENT commit does not count as naming this one",
         first(review_problem(GOOD.replace(H, OTHER), H)), "HEAD MISMATCH")
    case("...nor does an abbreviation, however long — the first line carries the FULL sha",
         first(review_problem(GOOD.replace(H, H[:39]), H)), "HEAD NOT NAMED")
    case("...nor an upper-case sha, which is not how git prints one",
         first(review_problem(GOOD.replace(H, H.upper()), H)), "HEAD NOT NAMED")
    case("a review that names the head and states a verdict is accepted", review_problem(GOOD, H), None)
    case("...and the head is the one ASKED about: the same review against another head is refused",
         first(review_problem(GOOD, OTHER)), "HEAD MISMATCH")
    case("...while a review naming that other head is accepted for it",
         review_problem(GOOD.replace(H, OTHER), OTHER), None)
    case("a head named in prose but not on the first line is not declared",
         first(review_problem(f"Looked at {H}\n" + GOOD, H)), "HEAD NOT NAMED")
    case("...the declaration form anywhere BUT the first line is not declared",
         first(review_problem("# x\n" + GOOD, H)), "HEAD NOT NAMED")
    case("...nor is the first line read after the body is stripped: line 1 is line 1",
         first(review_problem("\n" + GOOD, H)), "HEAD NOT NAMED")
    case("a SHA-256 repository's head is declared in full too",
         declared_head(f"Reviewed head: {H}{H[:24]}\n"), H + H[:24])
    case("...and a CRLF first line reads the same", declared_head(f"Reviewed head: {H}\r\nx"), H)
    case("...but a Unicode line separator does not end the first line",
         declared_head(f"Reviewed head: {H}\u2028x\n"), None)
    case("the verdict is the last non-empty line", review_verdict("x\nVERDICT: CONVERGED\n"),
         "CONVERGED")
    case("...and NOT CONVERGED is never read as CONVERGED",
         review_verdict("x\nVERDICT: NOT CONVERGED\n"), "NOT CONVERGED")
    case("...prose that contains the word is no verdict",
         review_verdict("I could not tell whether it CONVERGED.\n"), None)
    case("...nor is the bare word", review_verdict("CONVERGED\n"), None)
    case("...nor an r1-style heading", review_verdict("## Verdict\n\nCONVERGED\n"), None)
    case("...and a verdict line ABOVE the last line is not the verdict",
         review_verdict("VERDICT: CONVERGED\nmore findings below\n"), None)

    # ── the writer rule, pure ──
    case("a Claude half id is accepted", writer_problem("x-r1-claude"), None)
    case("...in the other shape too", writer_problem("x-claude-r2"), None)
    case("a CODEX id is refused — its verdict is written by the wrapper that ran it",
         "codex-review.py" in (writer_problem("x-r1-codex") or ""), True)
    case("a coordinator id is refused", writer_problem("x-r1-coordinator") is not None, True)
    case("a path is refused, not filed somewhere else",
         writer_problem("../x-r1-claude") is not None, True)

    # ── the record, pure ──
    _rec = claude_record(review_id="x-r1-claude", head=H, dirty={}, tree="/t", prompt="brief.md",
                         chars=900, verdict="CONVERGED")
    case("the record is the wrapper's schema", _rec.get("schema"), 3)
    case("...says the gate ran", _rec.get("gate_ran"), True)
    case("...and was not a refusal", _rec.get("refused"), False)
    case("...names the writer", _rec.get("writer"), "claude")
    case("...names the tool that wrote it, not codex-review", _rec.get("tool"), "record-review-verdict")
    case("...joins on the filed review's name", _rec.get("review"), "x-r1-claude.md")
    case("...carries the head", _rec.get("head"), H)
    case("...and the overlay it was GIVEN, here a clean one", _rec.get("dirty"), {})
    case("...and the verdict the review states", _rec.get("verdict"), "CONVERGED")
    case("...and the prompt", _rec.get("prompt"), "brief.md")
    _rec2 = claude_record(review_id="y-claude-r3", head=OTHER, dirty={"lib/a.ts": "100644 ab"},
                          tree="/u", prompt=None, chars=4321, verdict="NOT CONVERGED")
    case("every field comes from the arguments, not a constant",
         (_rec2["review"], _rec2["head"], _rec2["tree"], _rec2["prompt"], "4321" in _rec2["reason"],
          _rec2["dirty"], _rec2.get("verdict")),
         ("y-claude-r3.md", OTHER, "/u", None, True, {"lib/a.ts": "100644 ab"}, "NOT CONVERGED"))
    case("...and an overlay that could not be read stays None — UNUSABLE, never clean",
         claude_record(review_id="z-r1-claude", head=H, dirty=None, tree="/t", prompt=None,
                       chars=1, verdict="CONVERGED")["dirty"], None)

    # ── end to end, over a repository the case built ──
    crr = _load("check-review-recorded")
    crd = _load("check-review-rounds")
    with tempfile.TemporaryDirectory() as td:
        root = os.path.join(td, "repo")
        os.makedirs(root)
        env = fixture_git.env(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@e", GIT_COMMITTER_NAME="t",
                              GIT_COMMITTER_EMAIL="t@e")

        def git(*a: str) -> str:
            p = subprocess.run(["git", "-C", root, *a], capture_output=True, text=True, env=env)
            if p.returncode:
                raise RuntimeError(f"fixture git {a}: {p.stderr}")
            return p.stdout.strip()

        def write(rel: str, text: str) -> None:
            p = pathlib.Path(root, rel)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")

        def run(*a: str) -> "tuple[int, str]":
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                rc = main(list(a), root=root)
            return rc, buf.getvalue()

        def gate() -> "tuple[int, str]":
            saved = crr.ROOT
            crr.ROOT = pathlib.Path(root)
            try:
                changed, added = crr.changed_paths("base"), crr.added_paths("base")
                tails, unusable = crr.round_tails(crr.branch_verdicts(added), changed)
                return crr.tail_verdict(tails, unusable, None)
            finally:
                crr.ROOT = saved

        # A root that is not a repository: nothing there is a commit, so nothing can be recorded.
        _bare = os.path.join(td, "not-a-repo")
        os.makedirs(os.path.join(_bare, "docs", "reviews", "claude"))
        pathlib.Path(_bare, "docs/reviews/claude/z-r1-claude.md").write_text(GOOD, encoding="utf-8")
        with contextlib.redirect_stderr(io.StringIO()):
            case("outside a repository the head resolves to nothing: refused, nothing written",
                 (main(["--review-id", "z-r1-claude", "--head", H], root=_bare),
                  os.path.exists(os.path.join(_bare, "docs/reviews/verdicts"))), (RC_REFUSED, False))
        git("init", "-q", "-b", "main")
        write("lib/a.ts", "v1\n")
        git("add", "-A"); git("commit", "-q", "-m", "base"); git("branch", "base")
        write("lib/a.ts", "v2\n")
        git("add", "-A"); git("commit", "-q", "-m", "work")
        h1 = git("rev-parse", "HEAD")
        rid = "x-r1-claude"
        review = f"docs/reviews/claude/{rid}.md"
        verdict = f"docs/reviews/verdicts/{rid}.verdict.json"

        rc, out = run("--review-id", rid, "--head", h1)
        case("no review filed yet: refused, nothing written",
             (rc, os.path.exists(os.path.join(root, verdict))), (RC_REFUSED, False))
        write(review, "")
        rc, out = run("--review-id", rid, "--head", h1)
        case("an EMPTY filed review: refused, nothing written",
             (rc, os.path.exists(os.path.join(root, verdict))), (RC_REFUSED, False))
        # The review NAMES the bogus head, so only the is-it-a-commit rule can refuse this one.
        BOGUS = "deadbeef" * 5
        write(review, GOOD.replace(H, BOGUS))
        rc, out = run("--review-id", rid, "--head", BOGUS)
        case("a head that is not a commit here: refused, nothing written",
             (rc, os.path.exists(os.path.join(root, verdict))), (RC_REFUSED, False))
        case("...and says it is not a commit", "is not a commit" in out, True)
        write(review, GOOD.replace(H, h1))
        # A good review filed where this tool would look for it, so ONLY the writer rule can refuse.
        write("docs/reviews/claude/x-r1-codex.md", GOOD.replace(H, h1))
        rc, out = run("--review-id", "x-r1-codex", "--head", h1)
        case("a Codex id through this door: refused", rc, RC_REFUSED)
        os.remove(os.path.join(root, "docs/reviews/claude/x-r1-codex.md"))

        rc, out = run("--review-id", rid, "--head", h1[:8])
        case("a Claude half that names its head is RECORDED", rc, RC_WRITTEN)
        _v = json.loads(pathlib.Path(root, verdict).read_text(encoding="utf-8")) \
            if os.path.exists(os.path.join(root, verdict)) else {}
        case("...under the FULL sha, though it was handed an abbreviation", _v.get("head"), h1)
        case("...as the claude writer", _v.get("writer"), "claude")
        before = pathlib.Path(root, verdict).read_bytes() if _v else b""
        rc, out = run("--review-id", rid, "--head", h1)
        case("an existing verdict is NOT overwritten", rc, RC_REFUSED)
        case("...and its bytes are untouched", pathlib.Path(root, verdict).read_bytes()
             if _v else None, before or None)

        git("add", "-A"); git("commit", "-q", "-m", "review r1")
        records, bad = crd.read_verdicts(pathlib.Path(root, "docs/reviews/verdicts"))
        names = {p.name for p in pathlib.Path(root, "docs/reviews").rglob("*.md")}
        case("check-review-rounds reads the Claude verdict as well-formed", (len(records), bad), (1, []))
        case("...and its join finds the filed review", crd.verdict_problems(records, names), [])
        g = gate()
        case("check-review-recorded: a Claude verdict on the FINAL tree satisfies it", g[0], 0)
        case("...and names that round as the one that saw it", f"{rid}.verdict.json" in g[1], True)

        write("lib/a.ts", "v3\n")
        git("add", "-A"); git("commit", "-q", "-m", "fix after r1")
        h3 = git("rev-parse", "HEAD")
        g = gate()
        case("a Claude verdict on an OLDER head does not satisfy it", g[0], 1)
        case("...and the failure names the file that round never saw", "lib/a.ts" in g[1], True)

        rid2 = "x-r2-claude"
        write(f"docs/reviews/claude/{rid2}.md", GOOD.replace(H, h1))
        rc, out = run("--review-id", rid2, "--head", h3)
        case("a review naming an older head cannot be RECORDED against a later one", rc, RC_REFUSED)
        case("...and says why", "HEAD MISMATCH" in out, True)

        # Codex verdicts exactly as before: the wrapper's own record, written by its own writer.
        _cxrec = _cx.verdict_record(gate_ran=True, exit_code=0, review_id="x-r2-codex", reason="r",
                                    head=h3, dirty={}, prompt="p", tree=root)
        write("docs/reviews/codex/x-r2-codex.md", "codex review\n")
        _err = _cx.write_verdict(os.path.join(root, "docs/reviews/verdicts/x-r2-codex.verdict.json"),
                                 _cxrec)
        git("add", "-A"); git("commit", "-q", "-m", "codex r2")
        g = gate()
        case("a CODEX verdict on the final tree still satisfies it, unchanged",
             (_err, g[0], "x-r2-codex.verdict.json" in g[1]), (None, 0, True))
        case("...and the codex record still says codex-review wrote it", _cxrec["tool"], "codex-review")

    # ── the tree the review SAW, end to end (round 1 of PR #457: H1, M1, L3) ──
    with tempfile.TemporaryDirectory() as td:
        root = os.path.join(td, "repo")
        os.makedirs(root)
        env = fixture_git.env(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@e", GIT_COMMITTER_NAME="t",
                              GIT_COMMITTER_EMAIL="t@e")

        def git(*a: str) -> str:
            p = subprocess.run(["git", "-C", root, *a], capture_output=True, text=True, env=env)
            if p.returncode:
                raise RuntimeError(f"fixture git {a}: {p.stderr}")
            return p.stdout.strip()

        def write(rel: str, text: str) -> None:
            p = pathlib.Path(root, rel)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")

        def run(*a: str) -> "tuple[int, str]":
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                rc = main(list(a), root=root)
            return rc, buf.getvalue()

        def gate() -> "tuple[int, str]":
            saved = crr.ROOT
            crr.ROOT = pathlib.Path(root)
            try:
                changed, added = crr.changed_paths("base"), crr.added_paths("base")
                tails, unusable = crr.round_tails(crr.branch_verdicts(added), changed)
                return crr.tail_verdict(tails, unusable, None)
            finally:
                crr.ROOT = saved

        def recorded(rid: str) -> dict:
            p = pathlib.Path(root, f"docs/reviews/verdicts/{rid}.verdict.json")
            return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}

        git("init", "-q", "-b", "main")
        write("lib/a.ts", "v1\n")
        git("add", "-A"); git("commit", "-q", "-m", "base"); git("branch", "base")
        write("lib/a.ts", "BAD\n")
        git("add", "-A"); git("commit", "-q", "-m", "work")
        h1 = git("rev-parse", "HEAD")

        # H1, the r11 Blocking reopened: a reviewer handed an UNCOMMITTED fix, the fix then reverted.
        write("lib/a.ts", "GOOD\n")
        write("docs/reviews/claude/t-r1-claude.md", GOOD.replace(H, h1))
        rc, out = run("--review-id", "t-r1-claude", "--head", h1)
        case("a half handed an uncommitted fix is recorded WITH that fix in its overlay",
             (rc, "lib/a.ts" in (recorded("t-r1-claude").get("dirty") or {})), (RC_WRITTEN, True))
        git("checkout", "--", "lib/a.ts")
        git("add", "docs"); git("commit", "-q", "-m", "review r1")
        case("...so a fix reviewed and then REVERTED does not pass the final-tree gate",
             gate()[0], 1)

        # M1: the coordinator's --head is checked against the tree, not only against the text.
        write("lib/a.ts", "v3\n")
        git("add", "-A"); git("commit", "-q", "-m", "fix after r1")
        h3 = git("rev-parse", "HEAD")
        write("docs/reviews/claude/t-r2-claude.md", GOOD.replace(H, h1))
        rc, out = run("--review-id", "t-r2-claude", "--head", h1)
        case("a head the tree is NOT at is refused, though the review names it",
             (rc, recorded("t-r2-claude")), (RC_REFUSED, {}))
        case("...and says the tree moved", "TREE MOVED" in out, True)

        # M1: a head named only to dispute it, in a quoted line, is not a declaration.
        write("docs/reviews/claude/t-r3-claude.md",
              GOOD.replace(f"Reviewed head: {H}", f"> Reviewed head: {h3}\n\nThe brief "
                           f"above is quoted; my tree was at an earlier commit."))
        rc, out = run("--review-id", "t-r3-claude", "--head", h3)
        case("a head named only inside a QUOTED line is refused", rc, RC_REFUSED)
        write("docs/reviews/claude/t-r4-claude.md",
              GOOD.replace(f"Reviewed head: {H}", f"Reviewed head: {h3}, not {h1}"))
        rc, out = run("--review-id", "t-r4-claude", "--head", h3)
        case("a declaration that ALSO names another commit is refused", rc, RC_REFUSED)

        # M1b: `NOT CONVERGED` is never read as CONVERGED, and prose is not a verdict.
        write("docs/reviews/claude/t-r5-claude.md",
              GOOD.replace(H, h3).replace("CONVERGED", "NOT CONVERGED"))
        rc, out = run("--review-id", "t-r5-claude", "--head", h3)
        case("a NOT CONVERGED review is recorded as NOT CONVERGED",
             (rc, recorded("t-r5-claude").get("verdict")), (RC_WRITTEN, "NOT CONVERGED"))
        write("docs/reviews/claude/t-r6-claude.md",
              GOOD.replace(H, h3).replace("VERDICT: CONVERGED",
                                                  "I could not tell whether it CONVERGED."))
        rc, out = run("--review-id", "t-r6-claude", "--head", h3)
        case("prose that merely CONTAINS the word is not a verdict", rc, RC_REFUSED)

        # L3: no symlink is followed, on either path.
        outside = os.path.join(td, "elsewhere.md")
        pathlib.Path(outside).write_text(GOOD.replace(H, h3), encoding="utf-8")
        os.symlink(outside, os.path.join(root, "docs/reviews/claude/t-r7-claude.md"))
        rc, out = run("--review-id", "t-r7-claude", "--head", h3)
        case("a review that is a SYMLINK is refused", (rc, recorded("t-r7-claude")), (RC_REFUSED, {}))
        write("docs/reviews/claude/t-r8-claude.md", GOOD.replace(H, h3))
        target = os.path.join(td, "planted.json")
        os.symlink(target, os.path.join(root, "docs/reviews/verdicts/t-r8-claude.verdict.json"))
        rc, out = run("--review-id", "t-r8-claude", "--head", h3)
        case("a DANGLING symlink at the verdict path is refused, and nothing is written through it",
             (rc, os.path.exists(target)), (RC_REFUSED, False))
        # A linked DIRECTORY: the verdict file itself does not exist, so only the link rule refuses.
        elsewhere = os.path.join(td, "verdicts-elsewhere")
        os.makedirs(elsewhere)
        os.rename(os.path.join(root, "docs/reviews/verdicts"), os.path.join(td, "verdicts-real"))
        os.symlink(elsewhere, os.path.join(root, "docs/reviews/verdicts"))
        write("docs/reviews/claude/t-r9-claude.md", GOOD.replace(H, h3))
        rc, out = run("--review-id", "t-r9-claude", "--head", h3)
        case("a verdicts DIRECTORY that is a symlink is refused, and nothing is written there",
             (rc, os.listdir(elsewhere)), (RC_REFUSED, []))

    # ── round 2 of PR #457 (Codex H1, M2, M3): every repro, refused or read right ──
    # The r1 rule looked for "the reviewer's own line" in free Markdown, and each repro below is a
    # Markdown construct it did not model. The rule now reads two FIXED POSITIONS and nothing else.
    _V = "VERDICT: CONVERGED"
    case("r2 M2: an example verdict inside a nested fence is not the verdict",
         review_verdict("````markdown\n```\n## Verdict\nCONVERGED\n````\n## Verdict\nNOT CONVERGED\n"),
         None)
    case("...and with the declaration form, the LAST line is the verdict, not the fenced example",
         review_verdict(f"````markdown\n```\n{_V}\n````\nVERDICT: NOT CONVERGED\n"), "NOT CONVERGED")
    case("...nor with a `~~~` inner fence",
         review_verdict(f"````\n~~~\n{_V}\n````\nVERDICT: NOT CONVERGED\n"), "NOT CONVERGED")
    case("...and a file that ENDS in a fence around an example states no verdict",
         review_verdict(f"VERDICT: NOT CONVERGED\n```\n{_V}\n```\n"), None)
    case("r2 M2 sibling: a verdict inside an HTML comment is not the verdict",
         review_verdict("<!--\n## Verdict\nCONVERGED\n-->\n"), None)
    case("...nor in the declaration form", review_verdict(f"<!--\n{_V}\n-->\n"), None)
    case("r2 M3: a verdict PREFIX is not a verdict",
         review_verdict("## Verdict\nCONVERGEDNESS is not a verdict.\n"), None)
    case("...nor on the declaration line", review_verdict("VERDICT: CONVERGEDNESS\n"), None)
    case("...nor with anything after the word", review_verdict(f"{_V}.\n"), None)
    case("the last non-empty line is the verdict, trailing blank lines aside",
         review_verdict(f"x\n{_V}\n\n  \n"), "CONVERGED")
    case("...and a CRLF file reads the same", review_verdict(f"x\r\n{_V}\r\n"), "CONVERGED")
    case("...but a Unicode line separator does not make a new line",
         review_verdict(f"x {_V}\n"), None)

    with tempfile.TemporaryDirectory() as td:
        root = os.path.join(td, "repo")
        os.makedirs(root)
        env = fixture_git.env(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@e", GIT_COMMITTER_NAME="t",
                              GIT_COMMITTER_EMAIL="t@e")

        def git(*a: str) -> str:
            p = subprocess.run(["git", "-C", root, *a], capture_output=True, text=True, env=env)
            if p.returncode:
                raise RuntimeError(f"fixture git {a}: {p.stderr}")
            return p.stdout.strip()

        def write(rel: str, text: str) -> None:
            p = pathlib.Path(root, rel)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")

        def run(*a: str) -> "tuple[int, str]":
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                rc = main(list(a), root=root)
            return rc, buf.getvalue()

        git("init", "-q", "-b", "main")
        write("lib/a.ts", "A\n")
        git("add", "-A"); git("commit", "-q", "-m", "A")
        hA = git("rev-parse", "HEAD")
        write("lib/a.ts", "B\n")
        git("add", "-A"); git("commit", "-q", "-m", "B")
        hB = git("rev-parse", "HEAD")
        _tail = f"\n\n{PAD}\n\n## Verdict\nCONVERGED\n\n{_V}\n"
        hostile = [
            ("r2 H1: a declaration inside an HTML comment",
             f"I reviewed commit {hA}, not the current checkout.\n\n<!--\nReviewed head {hB}\n-->{_tail}"),
            ("...an HTML comment in the declaration form too",
             f"I reviewed commit {hA}.\n\n<!--\nReviewed head: {hB}\n-->{_tail}"),
            ("r2 H1: a declaration in an INDENTED code block",
             f"Example of a declaration, not mine:\n\n    Reviewed head {hB}{_tail}"),
            ("...an indented block in the declaration form too",
             f"Example of a declaration, not mine:\n\n    Reviewed head: {hB}{_tail}"),
            ("r2 H1: a declaration as a LAZY blockquote continuation",
             f"> The brief instructed this declaration:\nReviewed head {hB}{_tail}"),
            ("...a lazy continuation in the declaration form too",
             f"> The brief instructed this declaration:\nReviewed head: {hB}{_tail}"),
            ("a declaration under a blank first line", f"\nReviewed head: {hB}{_tail}"),
            ("a declaration with a prefix", f"**Reviewed head: {hB}**{_tail}"),
            ("a declaration of an ABBREVIATED head", f"Reviewed head: {hB[:12]}{_tail}"),
            ("a declaration with anything after the sha", f"Reviewed head: {hB} (and {hA}){_tail}"),
        ]
        for i, (name, text) in enumerate(hostile):
            rid = f"h-r{i + 1}-claude"
            write(f"docs/reviews/claude/{rid}.md", text)
            rc, out = run("--review-id", rid, "--head", hB)
            case(f"{name}: refused as HEAD NOT NAMED, nothing written",
                 (rc, "HEAD NOT NAMED" in out,
                  os.path.lexists(os.path.join(root, f"docs/reviews/verdicts/{rid}.verdict.json"))),
                 (RC_REFUSED, True, False))
        write("docs/reviews/claude/h-r20-claude.md", f"Reviewed head: {hB}\n{_tail}")
        rc, out = run("--review-id", "h-r20-claude", "--head", hB)
        case("...while the same review with the declaration on its FIRST line is recorded", rc,
             RC_WRITTEN)
        write("docs/reviews/claude/h-r21-claude.md", f"Reviewed head: {hA}\n{_tail}")
        rc, out = run("--review-id", "h-r21-claude", "--head", hB)
        case("...and a first line naming the OTHER full sha is a HEAD MISMATCH",
             (rc, "HEAD MISMATCH" in out), (RC_REFUSED, True))

    failed = 0
    for name, got, want in cases:
        ok = got == want
        failed += not ok
        print(f"  ok     {name}" if ok else f"  [FAIL] {name}: got {got!r} want {want!r}")
    print(f"\n{len(cases) - failed}/{len(cases)} passed")
    return 1 if failed else 0


def _load(stem: str):
    return import_module(stem)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
