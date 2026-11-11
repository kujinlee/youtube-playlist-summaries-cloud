#!/usr/bin/env python3
"""A bare `#N` in reader-facing prose resolves to whatever namespace the reader guesses.

WHY THIS EXISTS
---------------
Two sequences share one visual space here: GitHub pull-request numbers and `docs/backlog.md` row
ids. PR numbers grow monotonically and have overtaken the backlog, so **every backlog id below the
current PR ceiling is ambiguous when written bare**. Measured 2026-10-15: `#291` names both backlog
row 291 (the diagnostic-report redesign) and PR 291 (merged five weeks earlier, about something
else). A reader who looks it up on GitHub lands on the wrong one and nothing says so.

The rule itself is older — `docs/process-checklists.md` -> *Qualify every number in prose*, added
2026-08-27: write `backlog #39` or `task #39`, never a bare `#39`.

WHY IT IS A GATE NOW, WHEN 2026-08-27 MEASURED THAT IT COULD NOT BE
-------------------------------------------------------------------
That verdict was right about the predicate it tested, and this is a different predicate. The
rejected one flagged EVERY bare `#N`: 1,556 across `docs/`, and on one branch diff 24 firings of
which ~90% were `Phase 6 #1`, `Architecture Review #2`, `#54(a)` -- ordinals in titles, not
references into a namespace. Its stated conclusion stands: *a syntactic proxy for "is this reference
resolvable?" is the wrong instrument; the property is semantic.*

This predicate narrows on three axes, each chosen BY MEASUREMENT over the last 40 commits of
`origin/master` rather than by taste:

  (1) ADDED LINES ONLY. The corpus is not the subject; new prose is. Nothing migrates.
  (2) AN ADJACENT QUALIFIER PASSES, so `Phase 6 #1` and `backlog #39` are silent. This alone took
      the firing rate from "every bare `#N`" to 39% of them (239 of 397 already qualified).
  (3) READER-FACING SURFACES ONLY -- and this is the axis that decided it. With `scripts/` in
      scope the rule fired 158 times over 40 commits, and **137 of those (87%) were in
      `scripts/`**: code comments and mutation-manifest entry names, read by someone already
      inside the guard, where the number resolves from its surroundings. Dropping `scripts/` leaves
      **20 firings over 40 commits (0.50 per commit; 0.21 over 120)**.

⭐ ONE EXEMPTION, AND THE FIRINGS ASKED FOR IT RATHER THAN ME. Hand-classifying those 21 firings
found exactly one false positive: a bare `` `#39` `` inside backticks in `process-checklists.md`,
quoted AS the wrong form by the rule that forbids it. A bare reference inside inline code is a
QUOTATION, not a reference. With that exemption the sample is 20 true positives and 0 false ones.
⚠ That is a measured 0 over 21, not a guarantee: the honest bound is "no false positive in the 21
firings of the last 40 commits", and the next counter-example is a finding, not a surprise.

WHAT IT ACTUALLY ASSERTS (and what it deliberately does not)
------------------------------------------------------------
It asserts a SHAPE: an added line in a reader-facing file carries no `#N` that lacks both an
adjacent qualifier and inline-code quoting. It does NOT decide which namespace a number belongs to
-- that is the semantic question 2026-08-27 refused, and refusing it is why this can be mechanical.

⛔ OUT OF SCOPE BY CONSTRUCTION, stated rather than discovered later:
  * ⟳ `docs/backlog.md` and `docs/roadmap-to-launch.md` are now IN SCOPE (2026-10-20). The
    exemption claimed the backlog "owns the namespace"; it does not, because PR numbers occupy the
    same integers. Cost, measured the same way the original scoping was: 80 firings over 40 commits
    (2.00 per commit) against the 0.50 accepted for the original scope -- higher, but of a different
    KIND. `scripts/` was rejected at 3.95 because 87% was noise; a hand-classified sample here ran
    8 of 10 genuine. The rate is high because the VIOLATION rate is high, and since only ADDED lines
    are read it falls as soon as it is enforced rather than accumulating.
    ⚠ Closing the same sample's one false-positive class cost one word, not a notch: `deliverable #2`
    was a QUALIFIED reference whose qualifier was missing from the vocabulary (this project has two
    deliverables). That is the failure direction the QUALIFIER comment predicts -- an omission fires
    rather than passing silently -- and it removed 9 of the 89 firings.
  * `docs/reviews/**` -- frozen testimony, never edited.
  * `docs/dashboard-entries.md` -- dated records of what was true on a day.
  * `scripts/**`, `docs/memory/**`, `docs/superpowers/**`, `docs/explainers/**`, `docs/adr/**`,
    `docs/roadmap-to-launch.md` -- measured above, or read by someone already in context.
  * commit messages and PR bodies. GitHub autolinks `#N` there, usefully and correctly, and a
    commit message cannot be amended after the fact. The habit still applies; the gate does not.

⛔ ONE EXEMPTION FOR A MARKER-ONLY EDIT (backlog #394, the owner's decision 2026-10-29)
------------------------------------------------------------------------------------
Backlog #394 put a `⟦kind: …⟧` marker at the end of every backlog row's Item cell, which rewrites
every row's LINE — so 306 bare references ALREADY ON MASTER, across 87 rows, read as "added". The
added-lines axis exists so that NOTHING MIGRATES and only new prose is judged; a line whose only
change is that marker adds no prose. So an added line is NOT judged when, with its kind marker
removed by the parser's own rule (`gen-backlog-page.kind_mark`, never a second regex), it is
BYTE-IDENTICAL to a line of the SAME PATH AT THE BASE (`git show <base>:<path>`, compared as lines).
Everything else is judged exactly as before: a new line, any change of wording, one changed character.
Qualifying the old references by evidence is its own row, backlog #395.
⛔ PR #442 r2 — NO HEADER IS RECOGNISED BY ITS TEXT. Rounds 1 and 2 matched the removed lines of a
diff spanning SEVERAL paths, which meant recognising each file's header by its text; a deleted file
whose content is `-- a/docs/backlog.md` renders as that header, and credited its row to the backlog.
So git runs ONCE PER PATH, where everything after the first hunk header is content of that path; a
path absent at the base (a new file, a rename's target) exempts nothing; and each removed line
exempts as many marked copies as the path loses it, less the copies the path still gains unmarked.
⛔ PR #442 r3 — BOTH SIDES COME FROM THAT ONE DIFF. r2 read the head as raw worktree bytes while the
diff is clean-filtered, so under `.gitattributes text eol=crlf` a kept row ended in `\r` and let its
marked duplicate through. Per line, removed minus added equals base minus head, in git's own view.

FAILS IF
--------
  * an added line in a scoped file carries a bare `#N` with no adjacent qualifier and no inline-code
    quoting;
  * `git diff` cannot be run, or the base ref does not resolve -- which is CANNOT RUN (rc=2), never
    a pass.

  --self-test  runs 49 cases over lines and repositories this file builds, including that each failure mode is
               DETECTED and that both main() worlds are driven.
"""
from __future__ import annotations
import argparse
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OK, VIOLATION, CANNOT_RUN = 0, 1, 2

# Reader-facing surfaces. Hardcoded per `hardcode-only-what-fails-loudly`: a NEW spine document that
# forgets to appear here is exactly what review catches, and a derived list would silently grow to
# include `scripts/`, which is the one thing the measurement said to exclude.
SCOPE: tuple[str, ...] = (
    "CLAUDE.md", "AGENTS.md", "README.md", "CONTEXT.md",
    "docs/CLAUDE.md", "docs/dev-process.md", "docs/process-checklists.md",
    "docs/plugins.md", "docs/portable-practices.md", "docs/process-rationale.md",
    ".agents/skills/", ".claude/hooks/",
    # ⟳ 2026-10-20, AT THE OWNER'S DECISION, AND THE PREMISE THAT EXCLUDED THESE IS FALSIFIED.
    # This list used to exempt `docs/backlog.md` because it "owns the namespace; its own rows cite
    # each other unambiguously". MEASURED: backlog ids run 1..329 and PR numbers run 1..380, so the
    # ranges FULLY OVERLAP and nothing about being inside the file disambiguates a reference. Inside
    # `backlog.md`: 856 bare `#N` (397 already qualified alongside them), of which **19 are PROVABLY
    # not backlog rows** because they exceed the highest row id — `#336`, `#340`, `#341` are pull
    # requests. The remaining ~837 are INDISTINGUISHABLE, which is not the same as safe.
    # ⭐ The owner's own report is what settles it: asked to resolve `#329`, they could not — both a
    # backlog row and a merged PR carry that number.
    "docs/backlog.md",
    "docs/roadmap-to-launch.md",
)

# ⛔ `(?<![\w/#])` is load-bearing three times over: it keeps `v1#2` out, keeps a URL fragment
# `path/page#3` out, and keeps `##4` out. Dropping it is a manifest mutation.
BARE = re.compile(r"(?<![\w/#])#(\d{1,4})\b")

# The qualifier words are the namespaces this repo actually reuses, plus the ORDINAL words whose
# firings were ~90% of the 2026-08-27 sample. ⚠ This list is the "unbounded supply of answers"
# that verdict warned about, and it is tolerable here ONLY because an omission fails toward a
# FIRING (a false positive someone sees and fixes), never toward a silent pass.
QUALIFIER = re.compile(
    r"(backlog|task|pr|pull request|issue|phase|review|section|round|step|item|row|migration|adr"
    r"|finding|question|slice|stage|goal|milestone|shard|rule|case|mutation|deliverable)"
    # ⛔ AN ORDINAL MAY SIT BETWEEN THE QUALIFIER AND THE `#`, and omitting that was a real gap the
    # self-test caught on the first run: `Phase 6 #1` puts "6 " in the way, and it is exactly the
    # shape that was ~90% of the 2026-08-27 sample. `Architecture Review #2` needs no such slack.
    # ⚠ THIS IS THE SECOND SYNTACTIC ALLOWANCE IN THIS PREDICATE, which is the "unbounded supply of
    # answers" that verdict warned about, arriving on schedule. It is tolerable for one reason,
    # stated so a later reader can check it still holds: an omission here fails toward a FIRING —
    # a false positive a human sees and fixes — never toward a silent pass. The moment that
    # direction inverts, this list stops being safe to grow.
    r"[\s`*_\]\)]*(\d+[\s`*_\]\)]*)?$",
    re.I,
)


def in_inline_code(body: str, idx: int) -> bool:
    """True if offset `idx` sits inside inline-code backticks. PURE.

    An odd number of backticks before the offset means we are inside a span. ⭐ This is the one
    exemption the firings asked for: a bare reference shown in backticks is a quoted
    counter-example, which is how the rule's own text states itself.
    """
    return body.count("`", 0, idx) % 2 == 1


def in_scope(path: str, scope: tuple[str, ...] = SCOPE) -> bool:
    """True if `path` is a reader-facing surface. PURE."""
    return any(path == s or path.startswith(s) for s in scope if s)


def added_lines(one_path_diff: str) -> list[str]:
    """The lines a ONE-PATH unified diff adds. PURE."""
    return hunk_lines(one_path_diff, "+")


def removed_lines(one_path_diff: str) -> list[str]:
    """The lines a ONE-PATH unified diff removes. PURE."""
    return hunk_lines(one_path_diff, "-")


def hunk_lines(one_path_diff: str, sign: str) -> list[str]:
    """The lines of a ONE-PATH unified diff that carry `sign` (`+` added, `-` removed). PURE.

    ⛔ PR #442 r2: everything before the first hunk header is the header and everything after it is
    content, so an added line whose text LOOKS like a header (`++ b/scripts/x.py` renders as
    `+++ b/scripts/x.py`) is content of THIS path. A diff spanning several files cannot be split
    that way — its headers are recognised by their text, which the files' content controls — so the
    caller runs git once per path. Split on `\\n` only, as git writes it: `splitlines()` would also
    break a line at a `\\r` or `\\u2028` the base file keeps inside one line."""
    out: list[str] = []
    in_hunk = False
    for line in one_path_diff.split("\n"):
        if line.startswith("@@"):
            in_hunk = True
        elif in_hunk and line.startswith(sign):
            out.append(line[1:])
    return out


def violations(path: str, added: list[str], budget: Counter[str] | None = None,
               scope: tuple[str, ...] = SCOPE) -> list[str]:
    """Findings over the lines `added` to `path`. PURE — no git, no filesystem.

    `budget` is `exemption_budget` for this path; None exempts nothing.

    ⭐ THE RULE IS SEPARATED FROM THE FETCH ON PURPOSE. Three ratchets in this repo were
    untestable for eight days because their only entry point needed Docker; a pure predicate over
    lines can be driven by a case that builds its own world.
    """
    out: list[str] = []
    if not in_scope(path, scope):
        return out
    budget = Counter() if budget is None else budget
    for body in added:
        if marker_only(body, budget):
            continue
        for m in BARE.finditer(body):
            if in_inline_code(body, m.start()):
                continue
            before = re.sub(r"[`*_\[\]]", "", body[max(0, m.start() - 40):m.start()])
            if QUALIFIER.search(before):
                continue
            out.append(
                f"{path}: bare `{m.group(0)}` with no namespace — write `backlog {m.group(0)}`, "
                f"`PR {m.group(0)}`, `task {m.group(0)}` or whichever it is\n"
                f"    {body.strip()[:160]}"
            )
    return out


_BACKLOG_PARSER = None


def _backlog_parser():
    """`gen-backlog-page`, loaded once — it OWNS the kind-marker rule this file must not restate."""
    global _BACKLOG_PARSER
    if _BACKLOG_PARSER is None:
        import importlib.util as _ilu
        spec = _ilu.spec_from_file_location("_gen_backlog_page", Path(__file__).with_name("gen-backlog-page.py"))
        _BACKLOG_PARSER = _ilu.module_from_spec(spec)
        spec.loader.exec_module(_BACKLOG_PARSER)
    return _BACKLOG_PARSER


def without_kind_marker(body: str) -> str | None:
    """The table row `body` with its Item cell's kind marker removed, or None if it carries none (or
    an invalid one, which is then judged like any other line). The marker's trailing whitespace is
    kept as the cell's own, so a marker-only edit reproduces the original line BYTE FOR BYTE."""
    gb = _backlog_parser()
    cells = gb.CELL_SPLIT.split(body)
    if len(cells) < 4 or cells[0].strip():
        return None
    item = cells[2]
    try:
        rest, kind, _ = gb.kind_mark(item, cells[1].strip())
    except gb.ShapeError:
        return None
    if kind is None:
        return None
    cells[2] = rest + item[len(item.rstrip()):]
    return "|".join(cells)


def exemption_budget(base: list[str] | None, head: list[str]) -> Counter[str]:
    """{line: how many marker-only copies of it the head may add}. PURE.

    `base` and `head` are ONE PATH's two sides: its removed and added lines (what `scan` passes), or
    its whole files — per line, `Counter(base) - Counter(head)` is the same number either way. A line
    counts as many times as the base side holds it, LESS the copies the head side still carries
    unmarked: adding a marked duplicate of a row that is still there is a new copy of its references,
    not a marker-only edit. A path absent at the base (`base` None, or a diff that removes nothing:
    a new file, or a rename's target) exempts nothing, so prose moved in from another file is judged.
    ⛔ PR #442 r2: never removed text from a diff of SEVERAL paths — two rounds trusted a header
    recognised by its text, and a deleted file's content can spell one."""
    if base is None:
        return Counter()
    return Counter(base) - Counter(head)


def marker_only(body: str, budget: Counter[str]) -> bool:
    """True if `body`, an added line, is a base line of the same path with a kind marker added — and
    the budget still covers it, which this CONSUMES. PURE apart from loading the parser."""
    stripped = without_kind_marker(body) if "⟦" in body else None
    if stripped is None or budget[stripped] <= 0:
        return False
    budget[stripped] -= 1
    return True


def _git(root: Path, *args: str) -> str:
    """git's stdout as UTF-8 (undecodable bytes kept). Raises on a git failure — never returns ''."""
    r = subprocess.run(["git", "--literal-pathspecs", "-C", str(root), *args],
                       capture_output=True, stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args[:2])} failed: "
                           f"{r.stderr.decode('utf-8', 'replace').strip()[:200]}")
    return r.stdout.decode("utf-8", "surrogateescape")


def changed_paths(root: Path, base: str, head: str | None = None) -> list[str]:
    """Every path `base`..`head` (the worktree when None) adds to or changes. A deletion adds nothing,
    and renames are not followed: a rename's target is a path of its own."""
    out = _git(root, "diff", "--name-only", "-z", "--no-renames", "--no-color", "--diff-filter=d",
               base, *([head] if head else []))
    return [p for p in out.split("\0") if p]


def path_diff(root: Path, base: str, path: str, head: str | None = None) -> str:
    """The unified diff of ONE path, `base`..`head` (the worktree when None)."""
    return _git(root, "diff", "--unified=0", "--no-renames", "--no-color", "--no-ext-diff",
                base, *([head] if head else []), "--", path)


def scan(root: Path, base: str, head: str | None = None,
         scope: tuple[str, ...] = SCOPE) -> list[str]:
    """Every violation `base`..`head` adds, one git diff per path. Raises on a git failure."""
    out: list[str] = []
    for path in changed_paths(root, base, head):
        if not in_scope(path, scope):
            continue
        diff = path_diff(root, base, path, head)
        added = added_lines(diff)
        # ⛔ PR #442 r3: BOTH sides from this one-path diff, so both are git's clean-filtered view. Read
        # from the worktree's raw bytes, an `eol=crlf` row that stays ends in `\r` and cancels nothing.
        budget = exemption_budget(removed_lines(diff), added) if any("⟦" in a for a in added) else None
        out += violations(path, added, budget, scope)
    return out


def main(argv: list[str], root: Path = ROOT) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", default="origin/master",
                    help="ref to diff against (default: origin/master)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    try:
        found = scan(root, args.base)
    except RuntimeError as exc:
        print(f"CANNOT RUN — {exc}. Treat this as NOT RUN, not as a pass.", file=sys.stderr)
        return CANNOT_RUN
    if found:
        print(f"⛔ {len(found)} bare reference(s) added in reader-facing prose:\n", file=sys.stderr)
        for f in found:
            print(f"  ✗ {f}", file=sys.stderr)
        print("\nTwo sequences share this space: PR numbers and `docs/backlog.md` row ids, and the\n"
              "PR numbers have overtaken the backlog — so a bare `#N` below the PR ceiling resolves\n"
              "to whichever the reader guesses. Qualify it. See docs/process-checklists.md ->\n"
              "'Qualify every number in prose'.", file=sys.stderr)
        return VIOLATION
    print(f"reference namespaces OK — no bare `#N` added in {len(SCOPE)} reader-facing surface(s)")
    return OK


def _v(path: str, *lines: str, scope: tuple[str, ...] = SCOPE) -> list[str]:
    """The violations of `lines` added to `path`, with nothing exempt. PURE."""
    return violations(path, list(lines), scope=scope)


def self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: it builds git repositories (backlog #373)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    failed = 0
    cases = 0

    def case(name: str, got, want=True) -> None:
        # ⟳ 2026-10-20: `cases` is COUNTED here now. It used to be a LITERAL in the closing
        # print — `f"{23 - failed}/23 passed"` — so the reported total measured nothing and
        # could not drift, which is worse than drifting: `check-selftest-counts` compares the
        # docstring's declared count against the PRINTED one, so a literal on both sides is
        # green by construction. MEASURED at the moment this was found: 24 cases executed
        # while the suite reported 23, and had done for some time with every gate green.
        nonlocal failed, cases
        cases += 1
        if got != want:
            failed += 1
            print(f"  [FAIL] {name}: got {got!r} want {want!r}")

    SPINE = "docs/dev-process.md"
    # ── the defect this exists for ────────────────────────────────────────────────────────
    case("⭐ a BARE #N added to a spine doc is DETECTED",
         len(_v(SPINE, "see #291 for the redesign")), 1)
    case("...and the finding NAMES the token, so a reader can find it",
         "#291" in _v(SPINE, "see #291 for the redesign")[0])
    case("...and it names the FILE",
         SPINE in _v(SPINE, "see #291 for the redesign")[0])

    # ── every way it must stay SILENT ─────────────────────────────────────────────────────
    case("a QUALIFIED reference passes", _v(SPINE, "see backlog #291"), [])
    case("`PR #N` passes", _v(SPINE, "landed in PR #371"), [])
    case("an ORDINAL in a title passes — the ~90% of the 2026-08-27 sample",
         _v(SPINE, "## Phase 6 #1 — the arming condition"), [])
    case("⭐ a bare #N inside INLINE CODE passes — a quoted counter-example, the one measured FP",
         _v(SPINE, "write `backlog #39`, not a bare `#39`"), [])
    case("a qualifier through MARKUP still passes, because emphasis is not a word",
         _v(SPINE, "see **backlog** #291"), [])
    case("a REMOVED line is not an added line",
         added_lines(f"--- a/{SPINE}\n+++ b/{SPINE}\n@@ -1 +0,0 @@\n-see #291\n"), [])
    case("the +++ header itself is never scanned as content",
         added_lines(f"--- a/{SPINE}\n+++ b/{SPINE}\n@@ -0,0 +1 @@\n+ok\n"), ["ok"])
    # PR #442 r2: an added line `++ b/scripts/x.py` renders as `+++ b/scripts/x.py`. Read as a
    # header it would move the next line out of scope; inside a hunk it is content of this path.
    case("r2: an added line that LOOKS like a header is content, never a new path",
         added_lines(f"--- a/{SPINE}\n+++ b/{SPINE}\n@@ -0,0 +1,2 @@\n+++ b/scripts/x.py\n+see #291\n"),
         ["++ b/scripts/x.py", "see #291"])

    # ── the three things the lookbehind holds, each its own case ──────────────────────────
    case("a URL fragment is not a reference", _v(SPINE, "see docs/page#3 below"), [])
    case("a version-ish `v1#2` is not a reference", _v(SPINE, "the v1#2 form"), [])
    case("a markdown heading `##4` is not a reference", _v(SPINE, "##4 heading"), [])

    # ── SCOPE, in both directions, which is the axis the measurement chose ────────────────
    case("⭐ a bare #N in scripts/ is OUT of scope — 87% of firings lived there",
         _v("scripts/check-docs.py", "# fixes #291"), [])
    # ⟳ 2026-10-20: THIS CASE IS INVERTED, NOT DELETED. It used to assert that `docs/backlog.md`
    # is out of scope because it "OWNS the namespace". That premise is false — backlog ids run
    # 1..329 and PR numbers 1..380, so being inside the file disambiguates nothing, and 19 bare
    # references in it provably point OUTSIDE it (`#336`, `#340`, `#341` are pull requests).
    # Keeping the case and flipping its expectation is what makes the change falsifiable: revert
    # SCOPE and this reddens.
    case("⭐ a bare #N in docs/backlog.md is IN scope — PR numbers occupy the same integers",
         len(_v("docs/backlog.md", "| 291 | see #290 |")), 1)
    case("...and the roadmap too, for the same reason",
         len(_v("docs/roadmap-to-launch.md", "- [ ] blocked on #290")), 1)
    # ⛔ `deliverable` was MISSING from the qualifier vocabulary, so `deliverable #2` — a genuine
    # qualified reference, this project having two deliverables — fired as a violation. That is the
    # failure direction the QUALIFIER comment predicts: an omission fires rather than passing
    # silently. It accounted for 9 of the 89 firings the widening would otherwise have produced.
    case("`deliverable #2` is a QUALIFIED reference, not a bare one",
         _v("docs/backlog.md", "| 47 | ... deliverable #2 (the reusable harness) |"), [])
    case("a bare #N in a frozen review is out of scope",
         _v("docs/reviews/claude/x-r1-claude.md", "see #291"), [])
    case("a bare #N in a HOOK is IN scope — it prints to a reader at the moment of need",
         len(_v(".claude/hooks/enforce-handoff-path.sh", "# see #291")), 1)
    case("a bare #N in a SKILL is IN scope",
         len(_v(".agents/skills/handoff/SKILL.md", "see #291")), 1)
    case("⚠ `scope` is a PARAMETER, so a caller can narrow it — driven at a SECOND value",
         _v(SPINE, "see #291", scope=("docs/other.md",)), [])

    # ── ADR-0014: drive main() over worlds THIS CASE BUILT, in both directions ────────────
    import tempfile
    import fixture_git  # backlog #373: no inherited GIT_DIR or host config reaches a fixture's git
    with tempfile.TemporaryDirectory() as td:
        bad = Path(td) / "bad"
        subprocess.run(["git", "init", "-q", str(bad)], check=True, env=fixture_git.env())
        (bad / "docs").mkdir(parents=True)
        (bad / "docs" / "dev-process.md").write_text("a line with no reference\n")
        subprocess.run(["git", "-C", str(bad), "add", "-A"], check=True,
                       capture_output=True, env=fixture_git.env())
        subprocess.run(["git", "-C", str(bad), "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-qm", "base"], check=True, capture_output=True, env=fixture_git.env())
        base_sha = subprocess.run(["git", "-C", str(bad), "rev-parse", "HEAD"],
                                  capture_output=True, text=True, env=fixture_git.env()).stdout.strip()
        (bad / "docs" / "dev-process.md").write_text("a line with no reference\nsee #291 here\n")
        import contextlib, io
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            rc_bad = main(["--base", base_sha], root=bad)
        case("main() over a world this case built returns VIOLATION", rc_bad, VIOLATION)

        (bad / "docs" / "dev-process.md").write_text("a line with no reference\nsee backlog #291\n")
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            rc_ok = main(["--base", base_sha], root=bad)
        case("...and OK once the same line is qualified — the pair is the point", rc_ok, OK)

        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            rc_cr = main(["--base", "refs/heads/no-such-ref-xyz"], root=bad)
        case("⛔ an unresolvable base is CANNOT RUN, never a pass", rc_cr, CANNOT_RUN)

        # ⛔⛔ A SECOND ROOT, AND `check-fixture-variation` IS WHY — it refused this file until
        # `main(root=…)` took more than one value: "passed the SAME value at every call site (3x
        # `bad`). No case can tell that parameter apart from a constant." ⭐ The second world also
        # varies the SUBJECT, so the pair exercises two distinct scoped surfaces rather than two
        # spellings of one: this one puts the violation in a HOOK, where the earlier world put it
        # in a spine doc.
        hookworld = Path(td) / "hookworld"
        subprocess.run(["git", "init", "-q", str(hookworld)], check=True, env=fixture_git.env())
        (hookworld / ".claude" / "hooks").mkdir(parents=True)
        (hookworld / ".claude" / "hooks" / "x.sh").write_text("# nothing to see\n")
        subprocess.run(["git", "-C", str(hookworld), "add", "-A"], check=True, capture_output=True,
                       env=fixture_git.env())
        subprocess.run(["git", "-C", str(hookworld), "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-qm", "base"], check=True, capture_output=True, env=fixture_git.env())
        hw_base = subprocess.run(["git", "-C", str(hookworld), "rev-parse", "HEAD"],
                                 capture_output=True, text=True, env=fixture_git.env()).stdout.strip()
        (hookworld / ".claude" / "hooks" / "x.sh").write_text("# nothing to see\n# see #291\n")
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            rc_hook = main(["--base", hw_base], root=hookworld)
        case("main() at a SECOND root finds a violation in a HOOK", rc_hook, VIOLATION)
        (hookworld / ".claude" / "hooks" / "x.sh").write_text("# nothing to see\n# see backlog #291\n")
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            rc_hook_ok = main(["--base", hw_base], root=hookworld)
        case("...and OK there once qualified, so the second root is not a one-way fixture",
             rc_hook_ok, OK)

    # ── backlog #394: a MARKER-ONLY edit of an existing row is not new prose ─────────────────
    BL = "docs/backlog.md"
    OLD = "| 31 | **Gate** see #17 and #18 | x | S | (tooling) | open |"
    NEW = "| 31 | **Gate** see #17 and #18 ⟦kind: task⟧ | x | S | (tooling) | open |"

    def _swap(base: list[str] | None, *added: str) -> int:
        # `base` is the path's lines at the base; the head holds only what was added.
        try:
            return len(violations(BL, list(added), exemption_budget(base, list(added))))
        except Exception as exc:                   # noqa: BLE001 - a crash is a wrong answer here
            return f"raised {type(exc).__name__}"
    case("#394: a MARKER-ONLY change to an existing row is exempt", _swap([OLD], NEW), 0)
    case("#394: a marker plus ONE changed word is judged",
         _swap([OLD], NEW.replace("see #17", "per #17")), 2)
    case("#394: a NEW row carrying a marker and a bare #N is judged",
         _swap([], "| 395 | **New** see #17 ⟦kind: task⟧ | x | S | (tooling) | open |"), 1)
    case("#394: an UNMARKED added line is judged even when the base holds it verbatim",
         len(violations(BL, [OLD], exemption_budget([OLD, OLD], [OLD]))), 2)
    case("#394: an INVALID marker on a changed line is still judged, never exempt and never a crash",
         _swap([OLD], OLD.replace(" | x |", " ⟦kind: decision⟧ | x |", 1)), 2)
    # PR #442 r2: the base is read per path. A path absent at the base exempts nothing at all.
    case("r2: a path ABSENT at the base exempts nothing, even a line it would match",
         _swap(None, NEW), 2)
    case("r2: a DUPLICATED marker-only row is exempt ONCE — the copy is new prose",
         _swap([OLD], NEW, NEW), 2)
    case("r2: a base row that STAYS unmarked does not also exempt a marked copy of it",
         len(violations(BL, [NEW], exemption_budget([OLD], [OLD, NEW]))), 2)
    case("r2: a row the base holds TWICE may be marked twice",
         _swap([OLD, OLD], NEW, NEW), 0)

    # ── PR #442 r2: the exemption reads the BASE FILE, never removed diff text ──────────────────
    # Each world is a real repository: diff text is what the input controls, so a diff STRING
    # built by hand cannot show what git renders from a file's content.
    def _world(name: str, base: dict[str, str], head: dict[str, str | None]) -> tuple[Path, str]:
        root = Path(td2) / name
        subprocess.run(["git", "init", "-q", str(root)], check=True, env=fixture_git.env())
        for p, text in base.items():
            (root / p).parent.mkdir(parents=True, exist_ok=True)
            (root / p).write_text(text)
        subprocess.run(["git", "-C", str(root), "add", "-A"], check=True, capture_output=True,
                       env=fixture_git.env())
        subprocess.run(["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-qm", "base"], check=True, capture_output=True, env=fixture_git.env())
        sha = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True,
                             text=True, env=fixture_git.env()).stdout.strip()
        for p, text in head.items():
            if text is None:
                (root / p).unlink()
            else:
                (root / p).parent.mkdir(parents=True, exist_ok=True)
                (root / p).write_text(text)
        # STAGED, so a new file is in `git diff <base>` at all — unstaged, a rename's target is
        # untracked and nothing is judged, which passes X4 for an ambient reason.
        subprocess.run(["git", "-C", str(root), "add", "-A"], check=True, capture_output=True,
                       env=fixture_git.env())
        return root, sha

    def _rc(root: Path, sha: str) -> int:
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            return main(["--base", sha], root=root)

    FILLER = "".join(f"| {n} | filler row {n} | x | S | (t) | open |\n" for n in range(40, 60))
    with tempfile.TemporaryDirectory() as td2:
        # The control: a marker-only edit of a row the base holds is exempt through real git.
        ok = _world("ok", {BL: f"{FILLER}{OLD}\n"}, {BL: f"{FILLER}{NEW}\n"})
        case("r2: through REAL git, a marker-only edit of a base row is exempt", _rc(*ok), OK)
        # X1: a deleted file whose CONTENT is `-- a/docs/backlog.md` renders as a `--- a/` header.
        x1 = _world("x1", {"docs/backlog.old.md": f"-- a/{BL}\n{OLD}\n", BL: "| 7 | unrelated |\n"},
                    {"docs/backlog.old.md": None, BL: f"| 7 | unrelated |\n{NEW}\n"})
        case("r2 X1: a DELETED file's content cannot impersonate a header and exempt a moved row",
             _rc(*x1), VIOLATION)
        case("r2 X1: ...both of the moved row's references are judged", len(scan(*x1)), 2)
        # X4: a rename from backlog.old.md to backlog.md, the moved row changed only by its marker.
        x4 = _world("x4", {"docs/backlog.old.md": f"{FILLER}{OLD}\n"},
                    {"docs/backlog.old.md": None, BL: f"{FILLER}{NEW}\n"})
        case("r2 X4: a RENAME's target exempts nothing — prose moved into the backlog is judged",
             _rc(*x4), VIOLATION)
        case("r2 X4: ...both of the moved row's references are judged", len(scan(*x4)), 2)
        dup = _world("dup", {BL: f"{FILLER}{OLD}\n"}, {BL: f"{FILLER}{NEW}\n{NEW}\n"})
        case("r2: through REAL git, a marked row added TWICE is exempt once", len(scan(*dup)), 2)
        hdr = _world("hdr", {SPINE: "a line\n"}, {SPINE: "a line\n++ b/scripts/x.py\nsee #291\n"})
        case("r2: through REAL git, a line that renders as `+++ b/scripts/…` keeps the next one in scope",
             len(scan(*hdr)), 1)
        case("`scan(scope=…)` narrowed past the file judges nothing — driven at a SECOND value",
             scan(*hdr, scope=("docs/other.md",)), [])
        # `head` names a COMMIT, the leak scan's form: the same X4 world, committed, reads the same.
        subprocess.run(["git", "-C", str(x4[0]), "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-qm", "head"], check=True, capture_output=True, env=fixture_git.env())
        case("r2 X4: `scan(head=<commit>)` reads the committed rename the same way", len(scan(*x4, head="HEAD")), 2)
        subprocess.run(["git", "-C", str(ok[0]), "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-qm", "head"], check=True, capture_output=True, env=fixture_git.env())
        case("...and a committed marker-only edit is exempt there too", scan(*ok, head="HEAD"), [])
        # PR #442 r3 F2: a repo-controlled `eol=crlf` attribute checks the file out with CRLF, while
        # git's diff reads it through the clean filter, as LF. The row that STAYS must be counted in
        # that same view, or it ends in `\r`, cancels nothing, and its marked copy is exempt.
        crlf = _world("crlf", {BL: f"{FILLER}{OLD}\n"},
                      {".gitattributes": f"{BL} text eol=crlf\n",
                       BL: f"{FILLER}{OLD}\n{NEW}\n".replace("\n", "\r\n")})
        case("r3 F2: the eol=crlf world really holds CRLF in the worktree, so the next case is not ambient",
             b"\r\n" in (crlf[0] / BL).read_bytes())
        case("r3 F2: under `eol=crlf`, a row that stays unmarked still does not exempt a marked copy",
             len(scan(*crlf)), 2)
        # PR #442 r3 F3: `\x1c` is a line break to `splitlines()`, not to git. Split there, the text
        # after it loses its `+` and is never read as added.
        fs = _world("fs", {SPINE: "a line\n"}, {SPINE: "a line\nnote\x1cthen see #77\n"})
        case("r3 F3: an added line holding `\\x1c` is ONE line, so the bare #N after it is judged",
             len(scan(*fs)), 1)

    print(f"{cases - failed}/{cases} passed")
    return OK if failed == 0 else VIOLATION


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
