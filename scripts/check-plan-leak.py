#!/usr/bin/env python3
"""No line this branch adds to a TRACKED file quotes a private plan — the plan-content leak scan, standing.

    python3 scripts/check-plan-leak.py                      # this checkout's branch against origin/master
    python3 scripts/check-plan-leak.py --base B --head H --window 6
    python3 scripts/check-plan-leak.py --hook               # PreToolUse: the hook JSON on stdin
    python3 scripts/check-plan-leak.py --self-test          # 63 cases

WHY THIS EXISTS (backlog #393). The repo is PUBLIC and the session plans under `.claude/plans/` are
gitignored, which the owner decided on 2026-10-29 they STAY (backlog #194). Measured 2026-10-28 on PR #434:
a review document quoted a plan's objective, and a whole-string comparison missed it. A scan of every
6-word run of plan text against every ADDED tracked line found it (5 hits on the pre-redaction commit, 0
at its head). It lived in a session scratchpad; this is that scan made permanent.

⛔ WHY IT RUNS BEFORE A PUSH AND NOT IN CI. CI checks out the repo WITHOUT `.claude/plans/` — they are
gitignored — so a CI run would compare the diff against nothing and report a zero over nothing, which this
repo counts as CANNOT RUN, never a pass. The plans exist only where the work is done, so the gate is a
PreToolUse hook on `git push` (`.claude/hooks/check-plan-leak.sh`, which only launches `--hook` here). CI
runs the `--self-test`, which builds its own synthetic plans and needs none of the real ones.

THE RULE, which is the scratchpad scan's, kept:
  * PLAN TEXT is every `<!-- serving: … -->` objective (`gen-work-lines.SERVING`, the plan reader's own
    grammar) and every LIST ITEM of every plan in EVERY checkout (`gen-work-lines.plan_dirs`, the one place
    that answers which plan directories exist). ⟳ Widened from the scratchpad's `- [ ]` steps to every list
    item, because a step's indented `Doing:`/`Why:` lines are the most prose-like text a plan holds.
  * Words are runs of `\\w` after casefolding, so markup and punctuation between words cannot hide a match.
  * A HIT is an added line holding any `--window` (default 8) consecutive words of one plan string.
  * A MARKER-ONLY line is not judged whole: an added line that equals a line the same diff REMOVES from
    the same file once one trailing `⟦…⟧` kind marker is stripped (backlog #394) is judged on its MARKER
    ALONE — the rest of it was already in the base, so only the marker is new.
  * ⟳ A run ALREADY PUBLIC is not a hit: a window that occurs in a tracked file at `--base` reveals
    nothing new (`public_windows`). Without this the widened plan text matched cited paths and repo
    vocabulary on 3 of 4 merged PRs at a 6-word window (#435, #434, #433, #425: 0, 1, 6 and 6 lines, none
    a leak); with it, 0. Measured on
    PR #434's pre-redaction commit `e58364f9cd`, it still reports (at 6 words and at 8) the one line in the file
    where the scratchpad scan found its matches.

THE OUTPUT NAMES THE FILE AND LINE AND THE PLAN FILE, NEVER THE MATCHED WORDS: stdout and the deny reason
reach logs and the model's context, and quoting the leak there would be the leak. ⟳ The owner, 2026-10-29:
the matched phrase IS shown on the LOCAL terminal (stderr by hand; the deny's user-facing `systemMessage`
in the hook), never in `additionalContext` or any file, so a false positive takes seconds to judge.

EXIT CODES: 0 = no hit · 1 = hits (each `path:line` listed) · 2 = CANNOT RUN, no plan text found in any
checkout (the hook FAILS OPEN on this one, loudly, so a fresh clone is not blocked) · 3 = CANNOT RUN, git
failed or a plan could not be read (the hook fails CLOSED).

BOUNDS, stated: ⛔ A PLAN FRAGMENT SHORTER THAN 8 CONSECUTIVE WORDS IS NOT CAUGHT (the default window, set
by the owner 2026-10-29: over the last 40 merged commits 8 words gave 1 false hit against 3 at 6, and the
same 4 lines on the bulk-leak commit `f8e974a4`), nor one wrapped across two lines; a generic phrase can
match a plan step by coincidence, so a hit needs READING, and `ALLOW_PLAN_LEAK=1` is the escape for a judged
coincidence. The diff is `base...head` of COMMITTED work in the checkout the hook
runs in: a push naming another ref, or `git -C <elsewhere> push`, is judged by this checkout's HEAD.
Prose outside list items and objectives (a plan's headings, paragraphs and blockquotes) is not plan text.

WHAT WOULD MAKE THIS FAIL (its falsifier): an 8-word run of plan text in an added tracked line exits 0, or
the scan exits 0 when no plan could be read.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys

CLEAN, HITS, NO_PLANS, CANNOT = 0, 1, 2, 3
ROOT = pathlib.Path(__file__).resolve().parent.parent
WINDOW = 8   # the owner's decision 2026-10-29 — see BOUNDS
ESCAPE = "ALLOW_PLAN_LEAK=1"
GIT_TIMEOUT = 30   # seconds for `git diff`; a timeout is CANNOT RUN, never a pass

WORD = re.compile(r"\w+")
LIST_ITEM = re.compile(r"^\s*[-*+]\s+(.+?)\s*$", re.M)
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
# A `git push` invocation. The same shape `.claude/hooks/block-default-branch-push.sh` greps for; the
# settings `if: Bash(git push*)` filter is the first line of defence, and this is the second.
PUSH = re.compile(r"(^|[;&|\s])git\s+(-\S+\s+)*push(\s|$)")
# ⚠ A MINIMAL LOCAL COPY of backlog #394's marker rule. Its owner is `check-reference-namespace.marker_only`
# (via `gen-backlog-page.kind_mark`), which had NOT landed on master when this guard was written. When it
# lands, import it from there and delete this copy — one rule, one place.
MARKER = re.compile(r"\s*⟦[^⟦⟧]*⟧")


def _plan_reader():
    """`scripts/gen-work-lines.py`, by path (its name has a hyphen). Raises ImportError if it cannot load."""
    spec = importlib.util.spec_from_file_location(
        "_gen_work_lines_for_plan_leak", pathlib.Path(__file__).resolve().parent / "gen-work-lines.py")
    if spec is None or spec.loader is None:
        raise ImportError("cannot load scripts/gen-work-lines.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def words(s: str) -> list[str]:
    """PURE. The casefolded word runs of `s`."""
    return WORD.findall(s.casefold())


def plan_strings(text: str, serving: re.Pattern) -> list[str]:
    """PURE. Every objective (`serving`) and every list item of one plan file's `text`."""
    return [m.group(1) for m in serving.finditer(text)] + [m.group(1) for m in LIST_ITEM.finditer(text)]


def windows(sources: list[tuple[str, str]], n: int) -> dict[tuple[str, ...], str]:
    """PURE. {every n-word run of a plan string: the plan file it came from}."""
    out: dict[tuple[str, ...], str] = {}
    for label, s in sources:
        w = words(s)
        for i in range(len(w) - n + 1):
            out.setdefault(tuple(w[i:i + n]), label)
    return out


def diff_lines(diff_text: str) -> tuple[list[tuple[str, int, str]], dict[str, set[str]]]:
    """PURE. -> ([(path, new line number, body) per ADDED line], {path: every line REMOVED from it}).

    A `---`/`+++` pair is a file header only between `diff --git` and the first hunk, so an added line
    whose own text starts `++ ` is content, not a header. A deleted file has no `b/` side: its lines
    are removed, never added."""
    added: list[tuple[str, int, str]] = []
    removed: dict[str, set[str]] = {}
    path: str | None = None
    old: str | None = None
    header = False
    n = 0
    for line in diff_text.split("\n"):
        if line.startswith("diff --git "):
            header, path, old = True, None, None
        elif header and line.startswith("--- "):
            old = line[6:] if line.startswith("--- a/") else None
        elif header and line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else None
        elif line.startswith("@@"):
            header = False
            m = HUNK.match(line)
            n = int(m.group(1)) if m else 0
        elif header:
            continue
        elif line.startswith("+") and path:
            added.append((path, n, line[1:]))
            n += 1
        elif line.startswith("-") and (path or old):
            removed.setdefault(path or old, set()).add(line[1:])
    return added, removed


def judged_text(path: str, body: str, removed: dict[str, set[str]]) -> str:
    """PURE. The part of added line `body` (of `path`) that is judged: its marker alone when stripping one
    `⟦…⟧` marker reproduces a line this diff removes from the SAME file, else the whole line."""
    m = MARKER.search(body)
    if m and body[:m.start()] + body[m.end():] in removed.get(path, set()):
        return m.group(0)
    return body


def line_windows(added: list[tuple[str, int, str]], removed: dict[str, set[str]], n: int):
    """PURE. Yield (path, line, [every n-word run of the line's JUDGED text]) per added line."""
    for path, ln, body in added:
        w = words(judged_text(path, body, removed))
        yield path, ln, [tuple(w[i:i + n]) for i in range(len(w) - n + 1)]


def candidate_windows(win: dict[tuple[str, ...], str], added: list[tuple[str, int, str]],
                      removed: dict[str, set[str]], n: int) -> set[tuple[str, ...]]:
    """PURE. Every plan window that some added line carries — the only ones worth asking `public_windows`."""
    return {t for _, _, ts in line_windows(added, removed, n) for t in ts if t in win}


def leak_hits(win: dict[tuple[str, ...], str], added: list[tuple[str, int, str]],
              removed: dict[str, set[str]], n: int,
              public: set[tuple[str, ...]]) -> list[tuple[str, int, str, str]]:
    """PURE. [(path, line, plan file, matched phrase)] — one per added line carrying an n-word run of plan
    text that is NOT already `public` (present in the base tree). The phrase is for `local_lines` ONLY."""
    out = []
    for path, ln, ts in line_windows(added, removed, n):
        for t in ts:
            src = win.get(t)
            if src is not None and t not in public:
                out.append((path, ln, src, " ".join(t)))
                break
    return out


def report(hits: list[tuple[str, int, str, str]], n_strings: int, n_windows: int, n_added: int, n: int) -> str:
    """PURE. The verdict text: counts, then `path:line` and the plan FILE per hit — never the words."""
    head = (f"plan-leak: plan strings {n_strings} · {n}-word windows {n_windows} · "
            f"added tracked lines {n_added} · hits {len(hits)}")
    return "\n".join([head] + [f"  HIT {p}:{ln}  (a run of plan text from {src})" for p, ln, src, _ in hits])


def local_lines(hits: list[tuple[str, int, str, str]]) -> str:
    """PURE. The matched phrase per hit, for the LOCAL TERMINAL ONLY — stderr, or the hook's user-facing
    `systemMessage`. ⛔ Never stdout, `permissionDecisionReason` or `additionalContext`: those reach a log or
    the model's context, from which a phrase can be pasted into a tracked file — the leak this gate stops."""
    if not hits:
        return ""
    return "\n".join(["plan-leak, LOCAL ONLY — the matched words, so a false positive can be judged in "
                      "seconds. Never paste them into a tracked file, a commit or a PR:"]
                     + [f"  {p}:{ln}: '{phrase}'" for p, ln, _, phrase in hits])


def read_plan_sources(root: pathlib.Path) -> tuple[list[tuple[str, str]], list[str]]:
    """The FETCH. -> ([(plan label, plan string)], notes) over every checkout. Raises on an unreadable plan."""
    gwl = _plan_reader()
    dirs, notes = gwl.plan_dirs(root)
    sources: list[tuple[str, str]] = []
    for checkout, d in dirs:
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.md")):
            if not f.is_file():
                continue
            text = f.read_text(errors="replace")
            label = f"{checkout.name}/.claude/plans/{f.name}"
            sources += [(label, s) for s in plan_strings(text, gwl.SERVING)]
    return sources, notes


def _git(root: pathlib.Path, *args: str, ok=(0,)) -> str:
    """The FETCH's one git runner. Raises RuntimeError on any failure — never returns '' for one."""
    try:
        # ⛔ Inherited GIT_* are dropped, as `gen-work-lines.plan_dirs` does: a hook context can export
        # `GIT_DIR`, which `-C` does not override.
        r = subprocess.run(["git", "-C", str(root), "-c", "core.quotePath=false", *args],
                           capture_output=True, text=True, timeout=GIT_TIMEOUT, stdin=subprocess.DEVNULL,
                           env={k: v for k, v in os.environ.items() if not k.startswith("GIT_")})
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"git {args[0]} could not run ({type(exc).__name__})") from exc
    if r.returncode not in ok:
        raise RuntimeError(f"git {args[0]} failed: {r.stderr.strip()[:200]}")
    return r.stdout


def branch_diff(root: pathlib.Path, base: str, head: str) -> str:
    """The FETCH. The `-U0` diff of `base...head`; external diff drivers and textconv are refused."""
    return _git(root, "diff", "--no-color", "--no-ext-diff", "--no-textconv", "-U0", f"{base}...{head}")


def public_windows(root: pathlib.Path, base: str, cands: set[tuple[str, ...]]) -> set[tuple[str, ...]]:
    """The FETCH. The candidates that ALREADY occur in a tracked file at `base` — public before this branch.

    ⭐ WHY THIS EXISTS, MEASURED 2026-10-29: plan text includes the paths and repo vocabulary a plan cites
    (`docs/reviews/architecture-review-2026-10-…` is six words), so on PRs #435, #434, #433 and #425 the
    scan without it hit 0, 1, 6 and 6 lines — every one a phrase already in the repo, none a leak. A
    run already public before the branch reveals nothing new. Only candidates are looked up: `git grep`
    narrows to files holding all of a window's words, and only those are tokenised."""
    out: set[tuple[str, ...]] = set()
    cache: dict[str, set[tuple[str, ...]]] = {}
    for t in sorted(cands):
        pats = [a for w in sorted(set(t)) for a in ("-e", w)]
        hits = _git(root, "grep", "-l", "-I", "-i", "-F", "--all-match", *pats, base, "--", ok=(0, 1))
        for spec in hits.splitlines():
            if spec not in cache:
                w = words(_git(root, "show", spec))
                cache[spec] = {tuple(w[i:i + len(t)]) for i in range(len(w) - len(t) + 1)} & cands
            if t in cache[spec]:
                out.add(t)
                break
    return out


def scan(root: pathlib.Path, base: str, head: str, n: int) -> tuple[int, str, str]:
    """-> (exit code, message, LOCAL-only text). Every CANNOT RUN says so in words; none of them is a pass.
    The third element carries matched phrases and must only ever reach the local terminal."""
    try:
        sources, notes = read_plan_sources(root)
    except Exception as exc:  # noqa: BLE001 — any failure to read the plans is CANNOT RUN (3)
        return CANNOT, (f"plan-leak: CANNOT RUN — the plans could not be read ({type(exc).__name__}: {exc}). "
                        f"Treat this as NOT RUN."), ""
    win = windows(sources, n)
    if not win:
        return NO_PLANS, (f"plan-leak: CANNOT RUN — no plan text found in any checkout's .claude/plans/ "
                          f"({len(sources)} plan strings, none of {n} words or more). Nothing was compared, "
                          f"so treat this as NOT RUN." + "".join(f"\n  note: {x}" for x in notes)), ""
    try:
        added, removed = diff_lines(branch_diff(root, base, head))
        cands = candidate_windows(win, added, removed, n)
        public = public_windows(root, base, cands) if cands else set()
    except RuntimeError as exc:
        return CANNOT, f"plan-leak: CANNOT RUN — {exc}. Treat this as NOT RUN.", ""
    hits = leak_hits(win, added, removed, n, public)
    msg = report(hits, len(sources), len(win), len(added), n) + "".join(f"\n  note: {x}" for x in notes)
    return (HITS if hits else CLEAN), msg, local_lines(hits)


def _deny(reason: str) -> dict:
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                   "permissionDecisionReason": reason}}


def decide(rc: int, msg: str, local: str = "") -> dict | None:
    """PURE. The hook's reply for a scan's (rc, msg, local); None is silence, which allows the push.
    `local` (the matched phrases) goes ONLY into the user-facing `systemMessage` of a deny.

    Only NO_PLANS fails open, and loudly: a fresh clone has no plans and must still be able to push.
    Any other code — CANNOT, or one this function has never heard of — fails CLOSED."""
    if rc == CLEAN:
        return None
    if rc == HITS:
        reply = _deny("Blocked: this push adds tracked lines that quote a PRIVATE plan (.claude/plans/ is "
                      "gitignored and the repo is public).\n\n" + msg + "\n\nReword each line named above so "
                      "it no longer carries the plan's words. If a hit is a coincidental generic phrase, "
                      f"re-run prefixed with {ESCAPE}")
        if local:
            reply["systemMessage"] = local
        return reply
    if rc == NO_PLANS:
        warn = ("⚠ plan-leak push gate NOT RUN — no plan files were found, so nothing was compared and this "
                "push was NOT checked for quoted plan text.\n" + msg)
        return {"systemMessage": warn,
                "hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": warn}}
    return _deny(f"Blocked: the plan-leak push gate could not run (rc {rc}), so this push is unchecked.\n\n"
                 f"{msg}\n\nFix what it names, or re-run prefixed with {ESCAPE}")


def hook_reply(payload: str, run) -> dict | None:
    """The hook's reply to one PreToolUse `payload`. `run` performs the scan; it is called only for a push
    that is not escaped."""
    try:
        cmd = json.loads(payload).get("tool_input", {}).get("command") or ""
    except (ValueError, AttributeError):
        return _deny("Blocked: the plan-leak push gate could not read the hook payload, so this push is "
                     f"unchecked. Re-run prefixed with {ESCAPE} to push anyway.")
    if not PUSH.search(cmd) or ESCAPE in cmd:
        return None
    rc, msg, local = run()
    return decide(rc, msg, local)


def main(argv: list[str], root: pathlib.Path = ROOT, stdin=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", default="origin/master")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--window", type=int, default=WINDOW)
    ap.add_argument("--hook", action="store_true", help="read the PreToolUse JSON on stdin, reply in JSON")
    a = ap.parse_args(argv)
    if a.window < 1:
        ap.error("--window must be at least 1")
    if a.hook:
        reply = hook_reply((stdin or sys.stdin).read(), lambda: scan(root, a.base, a.head, a.window))
        if reply is not None:
            print(json.dumps(reply))
        return 0
    rc, msg, local = scan(root, a.base, a.head, a.window)
    print(msg)
    if local:
        print(local, file=sys.stderr)
    return rc


def _self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: it builds git repositories (backlog #373)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    import contextlib
    import io
    import shutil
    import tempfile

    ok = fail = 0

    def check(label, thunk, want):
        nonlocal ok, fail
        try:
            got = thunk()
        except Exception as exc:  # noqa: BLE001 - a raise IS the failure here
            fail += 1
            print(f"[FAIL] {label}: got {f'raised {type(exc).__name__}: {exc}'!r} want {want!r}")
            return
        if got == want:
            ok += 1
        else:
            fail += 1
            print(f"[FAIL] {label}: got {got!r} want {want!r}")

    gwl = _plan_reader()
    SERVING = gwl.SERVING
    # SYNTHETIC plan text only — the repo is public, and no real plan's words may appear here.
    STEP = "calibrate the walrus engine before teatime tomorrow evening near Dover"  # 10 words
    OBJ = "teach the lighthouse keeper to juggle seven turnips every winter"       # 10 words
    SUB = "because the parrot refuses every second Tuesday morning without fail"   # 10 words
    NEAR = "we calibrate the walrus engine before teatime tomorrow lunch"            # 7 words of STEP
    PLAN = (f"# a plan\n\n<!-- serving: {OBJ} -->\n\n### Task 1\n\n- [ ] **Step 1** — {STEP}\n"
            f"  - **Why:** {SUB}\n\nplain prose about seven quiet harbour lanterns glowing late\n")
    src = [("p.md", s) for s in plan_strings(PLAN, SERVING)]
    W8 = windows(src, 8)

    def hits_of(diff, n=8, win=None):
        added, removed = diff_lines(diff)
        return [(p, ln) for p, ln, _, _ in leak_hits(W8 if win is None else win, added, removed, n, set())]

    def one_file(path, plus, minus=(), start=1):
        body = "".join(f"-{x}\n" for x in minus) + "".join(f"+{x}\n" for x in plus)
        return (f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n"
                f"@@ -{start},{len(minus)} +{start},{len(plus)} @@\n{body}")

    # ── the plan text ────────────────────────────────────────────────────────────────────────────────
    check("plan_strings reads the objective, the step and its indented sub-bullet",
          lambda: [s for s in plan_strings(PLAN, SERVING)],
          [OBJ, f"[ ] **Step 1** — {STEP}", f"**Why:** {SUB}"])
    check("...and NOT a plain prose line, which is outside plan text by the stated bound",
          lambda: any("lanterns" in s for s in plan_strings(PLAN, SERVING)), False)
    check("the objective is read through the serving pattern it is GIVEN, not a constant",
          lambda: plan_strings("<!-- goal: a b -->\n", re.compile(r"<!--\s*goal:\s*(.+?)\s*-->")), ["a b"])
    check("words casefolds and drops markup and punctuation",
          lambda: words("**Calibrate** the `walrus`, ENGINE!"), ["calibrate", "the", "walrus", "engine"])
    check("windows of 8 over a 10-word string are 3, each labelled with its plan file",
          lambda: sorted(set(windows([("a.md", STEP)], 8).values())) + [len(windows([("a.md", STEP)], 8))],
          ["a.md", 3])
    check("windows of 10 over the same string are ONE run of 10 words — the size is the one GIVEN",
          lambda: [len(t) for t in windows([("a.md", STEP)], 10)], [10])
    check("a plan string shorter than the window yields no window",
          lambda: windows([("a.md", "only seven words are written right here")], 8), {})

    # ── the diff ─────────────────────────────────────────────────────────────────────────────────────
    two_hunks = (one_file("docs/a.md", ["harmless line"], start=3)
                 + f"@@ -10,0 +12,2 @@\n+another harmless line\n+we must {STEP} ok\n")
    check("⭐ KNOWN POSITIVE: an 8-word run of a plan step in an added line is a hit, at the right line",
          lambda: hits_of(two_hunks), [("docs/a.md", 13)])
    check("the objective is plan text too",
          lambda: hits_of(one_file("README.md", [f"note: {OBJ}."])), [("README.md", 1)])
    check("an indented sub-bullet is plan text too",
          lambda: hits_of(one_file("README.md", [f"x {SUB}"])), [("README.md", 1)])
    check("a 7-word NEAR MISS is not a hit at the default 8",
          lambda: hits_of(one_file("docs/a.md", [NEAR])), [])
    check("⭐ a MARKUP-SPLIT match is still a hit: casefold, bold, code and commas do not hide it",
          lambda: hits_of(one_file("docs/a.md", ["**CALIBRATE** the `walrus`, engine — before teatime, "
                                                 "*tomorrow* EVENING"])), [("docs/a.md", 1)])
    check("the window size is the one GIVEN: the 7-word run hits at --window 7",
          lambda: hits_of(one_file("docs/a.md", [NEAR]), 7, windows(src, 7)), [("docs/a.md", 1)])
    check("a REMOVED line carrying plan text is not judged",
          lambda: hits_of(one_file("docs/a.md", ["harmless"], [f"old {STEP}"])), [])
    check("an added line whose own text starts `++ ` is content, not a file header",
          lambda: hits_of(one_file("docs/a.md", [f"++ {STEP}"])), [("docs/a.md", 1)])
    check("a deleted file's lines are removed, not added",
          lambda: diff_lines("diff --git a/x.md b/x.md\ndeleted file mode 100644\n--- a/x.md\n+++ /dev/null\n"
                             f"@@ -1 +0,0 @@\n-{STEP}\n"), ([], {"x.md": {STEP}}))
    row = "| 7 | the item text | x |"
    marked = "| 7 | the item text ⟦kind: defect⟧ | x |"
    check("⭐ a MARKER-ONLY line (equal to a removed line once its ⟦…⟧ marker is stripped) is not judged",
          lambda: judged_text("docs/backlog.md", marked, {"docs/backlog.md": {row}}), " ⟦kind: defect⟧")
    plan_row = f"| 7 | {STEP} | x |"
    check("...so a marker added to a line ALREADY quoting plan text in the base is not a new hit",
          lambda: hits_of(one_file("docs/backlog.md", [f"| 7 | {STEP} ⟦kind: defect⟧ | x |"], [plan_row])), [])
    check("⭐ a marker PLUS a changed word is judged whole, and hits",
          lambda: hits_of(one_file("docs/backlog.md", [f"| 7 | now {STEP} ⟦kind: defect⟧ | x |"], [plan_row])),
          [("docs/backlog.md", 1)])
    check("the marker itself is still judged — a plan run inside a marker hits",
          lambda: hits_of(one_file("docs/backlog.md", [f"| 7 | the item text ⟦kind: {STEP}⟧ | x |"], [row])),
          [("docs/backlog.md", 1)])
    check("the exemption is per FILE: the same removed line in another file exempts nothing",
          lambda: judged_text("docs/other.md", marked, {"docs/backlog.md": {row}}), marked)

    one = one_file("docs/a.md", [f"we {STEP} ok"])
    a1, r1 = diff_lines(one)
    first = tuple(words(STEP)[:8])
    check("candidate_windows lists exactly the plan windows the added lines carry",
          lambda: sorted(candidate_windows(W8, a1, r1, 8)), sorted(windows([("p.md", STEP)], 8)))
    check("candidate_windows reads the window size GIVEN: at 10 there is one",
          lambda: len(candidate_windows(windows(src, 10), a1, r1, 10)), 1)
    check("⭐ a window ALREADY PUBLIC at the base is not a hit",
          lambda: leak_hits(W8, a1, r1, 8, set(windows([("p.md", STEP)], 8))), [])
    check("...but one private window left on the line still hits",
          lambda: [(p, ln) for p, ln, _, _ in leak_hits(W8, a1, r1, 8, {first})], [("docs/a.md", 1)])

    a2, r2 = diff_lines(one_file("docs/backlog.md", [f"| 7 | {STEP} ⟦kind: defect⟧ | x |"], [plan_row]))
    check("candidate_windows reads the JUDGED text: a marker-only line offers no candidate",
          lambda: candidate_windows(W8, a2, r2, 8), set())
    check("judged_text returns an unmarked line whole",
          lambda: judged_text("docs/a.md", f"plain {STEP}", {"docs/a.md": {"plain"}}), f"plain {STEP}")

    # ── the report and the hook decision ─────────────────────────────────────────────────────────────
    hit1 = [("docs/a.md", 13, "main/.claude/plans/p.md", " ".join(first))]
    rep = report(hit1, 3, 9, 4, 8)
    loc = local_lines(hit1)
    check("⛔ the report never carries the matched phrase", lambda: " ".join(first) in rep, False)
    check("⭐ local_lines carries the matched phrase, at its path:line",
          lambda: f"docs/a.md:13: '{' '.join(first)}'" in loc, True)
    check("local_lines of no hits is empty", lambda: local_lines([]), "")
    check("the report names the file, the line and the plan FILE",
          lambda: ("docs/a.md:13" in rep, "main/.claude/plans/p.md" in rep, "hits 1" in rep), (True, True, True))
    check("the report's counts are the ones GIVEN",
          lambda: report([], 5, 2, 7, 4).splitlines(),
          ["plan-leak: plan strings 5 · 4-word windows 2 · added tracked lines 7 · hits 0"])
    check("decide: a clean scan is silence", lambda: decide(CLEAN, "x"), None)
    check("⭐ decide: the phrase goes to the user-facing systemMessage of a deny and NOWHERE persisted",
          lambda: (" ".join(first) in decide(HITS, rep, loc)["systemMessage"],
                   " ".join(first) in decide(HITS, rep, loc)["hookSpecificOutput"]["permissionDecisionReason"],
                   "additionalContext" in decide(HITS, rep, loc)["hookSpecificOutput"]),
          (True, False, False))
    check("decide: hits DENY, carrying the scan's message and the escape",
          lambda: (decide(HITS, rep)["hookSpecificOutput"]["permissionDecision"],
                   "docs/a.md:13" in decide(HITS, rep)["hookSpecificOutput"]["permissionDecisionReason"],
                   ESCAPE in decide(HITS, rep)["hookSpecificOutput"]["permissionDecisionReason"]),
          ("deny", True, True))
    check("decide: NO PLANS fails OPEN — no permission decision — but loudly, to the user AND the model",
          lambda: ("permissionDecision" in decide(NO_PLANS, "m")["hookSpecificOutput"],
                   "NOT RUN" in decide(NO_PLANS, "m")["systemMessage"],
                   "NOT RUN" in decide(NO_PLANS, "m")["hookSpecificOutput"]["additionalContext"]),
          (False, True, True))
    check("decide: CANNOT RUN fails CLOSED", lambda: decide(CANNOT, "m")["hookSpecificOutput"]["permissionDecision"],
          "deny")
    check("decide: a code it has never heard of fails CLOSED too",
          lambda: decide(9, "m")["hookSpecificOutput"]["permissionDecision"], "deny")

    def payload(cmd):
        return json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})

    calls = []

    def fake_run():
        calls.append(1)
        return HITS, rep, loc

    check("hook_reply: a push is scanned and denied on hits",
          lambda: hook_reply(payload("git push -u origin feat/x"), fake_run)["hookSpecificOutput"]
          ["permissionDecision"], "deny")
    check("hook_reply: the escape is honoured and the scan is not even run",
          lambda: (hook_reply(payload(f"{ESCAPE} git push origin feat/x"), fake_run), len(calls)), (None, 1))
    check("hook_reply: a command that is not a push is untouched",
          lambda: (hook_reply(payload("git status && echo push"), fake_run), len(calls)), (None, 1))
    check("hook_reply: a clean scan of a push is silence",
          lambda: hook_reply(payload("git push origin feat/x"), lambda: (CLEAN, "c", "")), None)
    check("hook_reply: a push with no plans is ALLOWED with a warning",
          lambda: "NOT RUN" in hook_reply(payload("git push"), lambda: (NO_PLANS, "n", ""))["systemMessage"], True)
    check("hook_reply: an unreadable payload fails CLOSED",
          lambda: hook_reply("not json", fake_run)["hookSpecificOutput"]["permissionDecision"], "deny")

    # ── main, over worlds a case BUILT ───────────────────────────────────────────────────────────────
    td = pathlib.Path(tempfile.mkdtemp(prefix="plan-leak-"))
    try:
        def git(repo, *args):
            r = subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.com",
                                *args], capture_output=True, text=True)
            if r.returncode != 0:
                raise RuntimeError(f"git {args}: {r.stderr}")
            return r.stdout

        def world(name, plan, added_text):
            r = td / name
            r.mkdir()
            git(r, "init", "-q", "-b", "master")
            (r / ".gitignore").write_text(".claude/plans/\n")
            (r / "README.md").write_text("base\n")
            git(r, "add", "-A")
            git(r, "commit", "-q", "-m", "base")
            git(r, "branch", "base")
            if plan is not None:
                (r / ".claude" / "plans").mkdir(parents=True)
                (r / ".claude" / "plans" / "fx.md").write_text(plan)
            (r / "README.md").write_text(f"base\n{added_text}\n")
            git(r, "commit", "-q", "-am", "head")
            return r

        def captured(thunk):
            buf, ebuf = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(ebuf):
                rc = thunk()
            return rc, buf.getvalue(), ebuf.getvalue()

        leak = world("leak", PLAN, f"we {STEP} now")
        rc, out, err = captured(lambda: main(["--base", "base"], root=leak))
        check("⭐ main over a built world: a leaked step exits 1 and names README.md:2",
              lambda: (rc, "README.md:2" in out), (HITS, True))
        check("⛔ ...and its STDOUT NEVER contains the matched plan words",
              lambda: any(" ".join(words(STEP)[i:i + 3]) in " ".join(words(out)) for i in range(8)), False)
        check("⭐ ...while the LOCAL stderr shows the matched phrase at its path:line",
              lambda: f"README.md:2: '{' '.join(first)}'" in err, True)
        clean = world("clean", PLAN, "nothing private here at all, just six or more words")
        check("main over a clean world exits 0",
              lambda: captured(lambda: main(["--base", "base"], root=clean))[0], CLEAN)
        bare = world("bare", None, f"we {STEP} now")
        check("⭐ main with NO plan file is CANNOT RUN (2), never a pass",
              lambda: (lambda r: (r[0], "NOT RUN" in r[1]))(captured(lambda: main(["--base", "base"], root=bare))), (NO_PLANS, True))
        check("main with a base that does not exist is CANNOT RUN (3)",
              lambda: captured(lambda: main(["--base", "no-such-ref"], root=leak))[0], CANNOT)
        check("--window is read: at 11 words no 10-word plan string can hit",
              lambda: captured(lambda: main(["--base", "base", "--window", "11"], root=leak))[0], CLEAN)
        pub = world("pub", PLAN, f"again: {STEP}")
        (pub / "OLD.md").write_text(f"an older public copy: {STEP}\n")
        git(pub, "add", "OLD.md")
        git(pub, "commit", "-q", "-m", "public")
        git(pub, "branch", "-f", "base")
        (pub / "README.md").write_text(f"base\nand again: {STEP}\n")
        git(pub, "commit", "-q", "-am", "head2")
        check("⭐ public_windows finds a window already in a tracked file at the base",
              lambda: public_windows(pub, "base", {first}), {first})
        check("...and not one that the base does not hold",
              lambda: public_windows(leak, "base", {first}), set())
        scrambled = tuple(reversed(first))
        check("public_windows reads the base it is GIVEN: at the first commit nothing is public",
              lambda: public_windows(pub, "master~3", {first}), set())
        check("...nor one whose words are all at the base but not as that run",
              lambda: public_windows(pub, "base", {scrambled}), set())
        check("main: re-adding a phrase already public at the base is CLEAN",
              lambda: captured(lambda: main(["--base", "base"], root=pub))[0], CLEAN)
        wt = td / "wt"
        git(bare, "worktree", "add", "-q", "-b", "side", str(wt), "base")
        (bare / ".claude" / "plans").mkdir(parents=True)
        (bare / ".claude" / "plans" / "main-plan.md").write_text(PLAN)
        (wt / "notes.md").write_text(f"see: {OBJ}\n")
        git(wt, "add", "notes.md")
        git(wt, "commit", "-q", "-m", "side")
        check("⭐ a plan held in ANOTHER checkout is read: pushing from a worktree sees the main checkout's plan",
              lambda: (lambda r: (r[0], "notes.md:1" in r[1]))(captured(lambda: main(["--base", "base"], root=wt))), (HITS, True))
        rc, out, err = captured(lambda: main(["--hook", "--base", "base"], root=leak,
                                            stdin=io.StringIO(payload("git push origin master"))))
        check("main --hook over the leak world prints a DENY and exits 0",
              lambda: (rc, json.loads(out)["hookSpecificOutput"]["permissionDecision"]), (0, "deny"))
        check("⛔ main --hook: the phrase is in the systemMessage only — not the reason, not stderr",
              lambda: (" ".join(first) in json.loads(out)["systemMessage"],
                       " ".join(first) in json.dumps(json.loads(out)["hookSpecificOutput"]),
                       " ".join(first) in err), (True, False, False))

        # The SHIPPED shim, run as the harness runs it, over a copy of this world.
        shim_src = ROOT / ".claude" / "hooks" / "check-plan-leak.sh"
        nop = world("nop", None, f"we {STEP} now")
        for d in (leak, nop):
            (d / ".claude" / "hooks").mkdir(parents=True, exist_ok=True)
            shutil.copy(shim_src, d / ".claude" / "hooks" / shim_src.name)
            (d / "scripts").mkdir(exist_ok=True)
            for s in ("check-plan-leak.py", "gen-work-lines.py"):
                shutil.copy(ROOT / "scripts" / s, d / "scripts" / s)
            git(d, "update-ref", "refs/remotes/origin/master", "base")   # the hook's default base

        def shim(repo, cmd):
            r = subprocess.run(["bash", str(repo / ".claude" / "hooks" / shim_src.name)], cwd=repo,
                               input=payload(cmd), capture_output=True, text=True)
            return r.returncode, r.stdout, r.stderr

        rc, out, _ = shim(leak, "git push origin feat/x")
        check("⭐ the SHIPPED hook denies a push from the leak world",
              lambda: (rc, '"permissionDecision": "deny"' in out), (0, True))
        rc, out, _ = shim(nop, "git push origin feat/x")
        check("the shipped hook FAILS OPEN, loudly, in a world with no plans",
              lambda: (rc, "permissionDecision" in out, "NOT RUN" in out), (0, False, True))
        (leak / "scripts" / "check-plan-leak.py").write_text("raise SystemExit(1)\n")
        rc, out, err = shim(leak, "git push origin feat/x")
        check("⛔ a CRASHED checker blocks the push (exit 2), it does not wave it through",
              lambda: (rc, "did not run" in err), (2, True))
        check("...and the escape still lets a deliberate push through a crashed checker",
              lambda: shim(leak, f"{ESCAPE} git push origin feat/x")[0], 0)
    finally:
        shutil.rmtree(td, ignore_errors=True)

    if fail:
        print(f"\n{ok} passed, {fail} FAILED")
        return 1
    print(f"\n{ok}/{ok + fail} self-test cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(_self_test() if "--self-test" in sys.argv[1:] else main(sys.argv[1:]))
