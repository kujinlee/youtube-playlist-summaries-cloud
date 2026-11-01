#!/usr/bin/env python3
"""Record the verdict a CLAUDE review half leaves — the same record a Codex run leaves.

    python3 scripts/record-review-verdict.py --review-id <subject>-r<N>-claude --head <sha> [--prompt <brief>]
    python3 scripts/record-review-verdict.py --self-test  # 48 cases

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
  * the filed review must NAME that commit (a hex prefix of 7+ characters, git's own minimum
    abbreviation). The coordinator cannot record a head the review document does not itself claim
    to have seen, so a verdict cannot be moved forward onto a later commit by re-running this.
  * `dirty` is `{}`: the half is credited with the COMMITTED tree at `head` and nothing else. A
    reviewer who was handed uncommitted fixes therefore has those paths read as UNSEEN once they
    are committed, and `check-review-recorded` fails the branch — the wrong answer is a false red,
    never a false green.
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
# git's own minimum abbreviation; a shorter prefix names too many commits to be a claim about one.
MIN_HEX = 7
HEX_TOKEN = re.compile(r"\b[0-9a-f]{%d,64}\b" % MIN_HEX)
VERDICT_WORD = re.compile(r"\bCONVERGED\b")


def review_problem(body: "str | None", head: str) -> "str | None":
    """PURE. Why this filed review cannot be testified to, or None. The first word is the rule."""
    if body is None:
        return "MISSING — the review is not filed where check-review-rounds pairs it"
    text = body.strip()
    if len(text) < _cx.MIN_REVIEW_CHARS:
        return (f"EMPTY — {len(text)} characters, under the {_cx.MIN_REVIEW_CHARS} below which "
                f"codex-review.py refuses to call a message a review")
    if not VERDICT_WORD.search(text):
        return "NO VERDICT — the review states neither CONVERGED nor NOT CONVERGED"
    if not any(head.lower().startswith(t) for t in HEX_TOKEN.findall(text.lower())):
        return (f"HEAD NOT NAMED — the review never names {head[:12]}, so it cannot be recorded "
                f"as having seen it. Name the commit the half was handed in the review itself")
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


def claude_record(*, review_id: str, head: str, tree: str, prompt: "str | None",
                  chars: int) -> dict:
    """PURE. `codex-review.verdict_record`, with the two fields that say a Claude half left it."""
    rec = _cx.verdict_record(gate_ran=True, exit_code=0, review_id=review_id,
                             reason=f"claude half filed: {chars} chars, names {head[:12]}",
                             head=head, dirty={}, prompt=prompt, tree=tree)
    rec["tool"] = TOOL
    rec["writer"] = WRITER
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
    exists = _cx.overwrite_refusal(vpath, exists=os.path.exists(vpath), allow_overwrite=False,
                                   what="the verdict")
    if exists:
        return refuse(exists)
    head = resolve_head(root, args.head)
    if head is None:
        return refuse(f"REFUSED — {args.head!r} is not a commit in {root}")
    try:
        with open(rpath, encoding="utf-8", errors="replace") as f:
            body: "str | None" = f.read()
    except OSError:
        body = None
    problem = review_problem(body, head)
    if problem:
        return refuse(f"{problem}\n  review: {rpath}")
    rec = claude_record(review_id=args.review_id, head=head, tree=root, prompt=args.prompt,
                        chars=len((body or "").strip()))
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
    GOOD = f"# x — round 1 — Claude half\n\nReviewed at `{H[:8]}`.\n\n## Verdict\n\nCONVERGED\n{PAD}\n"

    # ── the review-file rule, pure ──
    case("a missing review file is refused", first(review_problem(None, H)), "MISSING")
    case("an empty review file is refused", first(review_problem("", H)), "EMPTY")
    case("...and so is a whitespace-only one, which is empty after strip",
         first(review_problem("   \n\t\n", H)), "EMPTY")
    case("a stub under the minimum length is refused",
         first(review_problem(f"CONVERGED {H[:8]}", H)), "EMPTY")
    case("a review stating no verdict is refused — a finding-less file is a failed run",
         first(review_problem(GOOD.replace("CONVERGED", "done"), H)), "NO VERDICT")
    case("...and `NOT CONVERGED` is a verdict, not its absence",
         review_problem(GOOD.replace("CONVERGED", "NOT CONVERGED"), H), None)
    case("a review that never names the head it was handed is refused",
         first(review_problem(GOOD.replace(H[:8], "zzzzzzzz"), H)), "HEAD NOT NAMED")
    case("...and naming a DIFFERENT commit does not count as naming this one",
         first(review_problem(GOOD.replace(H[:8], OTHER[:8]), H)), "HEAD NOT NAMED")
    case("...nor does a six-character prefix, which is shorter than git's own abbreviation",
         first(review_problem(GOOD.replace(H[:8], H[:6]), H)), "HEAD NOT NAMED")
    case("...while the full sha names it", review_problem(GOOD.replace(H[:8], H), H), None)
    case("a review that names the head and states a verdict is accepted", review_problem(GOOD, H), None)
    case("...and the head is the one ASKED about: the same review against another head is refused",
         first(review_problem(GOOD, OTHER)), "HEAD NOT NAMED")
    case("...while a review naming that other head is accepted for it",
         review_problem(GOOD.replace(H[:8], OTHER[:10]), OTHER), None)

    # ── the writer rule, pure ──
    case("a Claude half id is accepted", writer_problem("x-r1-claude"), None)
    case("...in the other shape too", writer_problem("x-claude-r2"), None)
    case("a CODEX id is refused — its verdict is written by the wrapper that ran it",
         "codex-review.py" in (writer_problem("x-r1-codex") or ""), True)
    case("a coordinator id is refused", writer_problem("x-r1-coordinator") is not None, True)
    case("a path is refused, not filed somewhere else",
         writer_problem("../x-r1-claude") is not None, True)

    # ── the record, pure ──
    _rec = claude_record(review_id="x-r1-claude", head=H, tree="/t", prompt="brief.md", chars=900)
    case("the record is the wrapper's schema", _rec.get("schema"), 3)
    case("...says the gate ran", _rec.get("gate_ran"), True)
    case("...and was not a refusal", _rec.get("refused"), False)
    case("...names the writer", _rec.get("writer"), "claude")
    case("...names the tool that wrote it, not codex-review", _rec.get("tool"), "record-review-verdict")
    case("...joins on the filed review's name", _rec.get("review"), "x-r1-claude.md")
    case("...carries the head", _rec.get("head"), H)
    case("...and a CLEAN overlay, so uncommitted fixes read as unseen", _rec.get("dirty"), {})
    case("...and the prompt", _rec.get("prompt"), "brief.md")
    _rec2 = claude_record(review_id="y-claude-r3", head=OTHER, tree="/u", prompt=None, chars=4321)
    case("every field comes from the arguments, not a constant",
         (_rec2["review"], _rec2["head"], _rec2["tree"], _rec2["prompt"], "4321" in _rec2["reason"]),
         ("y-claude-r3.md", OTHER, "/u", None, True))

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
        write(review, GOOD.replace(H[:8], BOGUS))
        rc, out = run("--review-id", rid, "--head", BOGUS)
        case("a head that is not a commit here: refused, nothing written",
             (rc, os.path.exists(os.path.join(root, verdict))), (RC_REFUSED, False))
        write(review, GOOD.replace(H[:8], h1[:8]))
        # A good review filed where this tool would look for it, so ONLY the writer rule can refuse.
        write("docs/reviews/claude/x-r1-codex.md", GOOD.replace(H[:8], h1[:8]))
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
        write(f"docs/reviews/claude/{rid2}.md", GOOD.replace(H[:8], h1[:8]))
        rc, out = run("--review-id", rid2, "--head", h3)
        case("a review naming an older head cannot be RECORDED against a later one", rc, RC_REFUSED)
        case("...and says why", "HEAD NOT NAMED" in out, True)

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
