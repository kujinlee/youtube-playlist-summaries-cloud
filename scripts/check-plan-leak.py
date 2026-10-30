#!/usr/bin/env python3
"""No commit a push sends adds a line that quotes a private plan — git's own pre-push hook, standing.

    .githooks/pre-push                                  # git runs it: `--pre-push <remote> <url>`, refs on stdin
    scripts/install-git-hooks.sh [--status]             # enable it once per clone (`core.hooksPath .githooks`)
    python3 scripts/check-plan-leak.py [--base B] [--head H]   # by hand: the commits in H not in B
    python3 scripts/check-plan-leak.py --show           # by hand, in a TERMINAL: also print the matched words
    python3 scripts/check-plan-leak.py --self-test      # 105 cases

WHY THIS EXISTS (backlog #393). The repo is PUBLIC and the session plans under `.claude/plans/` are
gitignored, which the owner decided on 2026-10-29 they STAY (backlog #194). Measured 2026-10-28 on PR #434:
a review document quoted a plan's objective, and a whole-string comparison missed it. A scan of every
6-word run of plan text against every ADDED tracked line found it.

⛔ WHY GIT'S PRE-PUSH HOOK, AND NOT A CLAUDE CODE HOOK OR A CI STEP (PR #443 round 1, a redesign). The first
version was a PreToolUse hook that read the shell COMMAND and diffed HEAD against `origin/master`. A command's
text cannot say what a push sends: history, not the endpoint tree (r1 X1); refs other than HEAD (X2); `git -C`,
`-c` and aliases (X3); an escape word in a comment (X4). Git itself tells a pre-push hook, on stdin, exactly
which local and remote objects each ref update carries, whatever the command, alias or directory. So:
  * EVERY COMMIT the remote lacks is scanned — `local_sha --not <every remote tip present here>` — each one
    diffed against its first parent, with `--text` (X6) and C-quoted paths decoded (X5). Deletions send nothing.
  * "PUBLIC" IS THE REMOTE'S OWN STATE: `git ls-remote <url>` heads and tags plus the remote shas on stdin,
    never a local `origin/master` anyone can `update-ref` (X7).
  * CI has no `.claude/plans/` (gitignored), so a CI scan would be a zero over nothing; CI runs the
    `--self-test`, which builds bare remotes and drives REAL `git push` through the shipped hook.

THE RULE:
  * PLAN TEXT is every `<!-- serving: … -->` objective (`gen-work-lines.SERVING`) and every LIST ITEM of every
    plan in EVERY checkout (`gen-work-lines.plan_dirs`). If that discovery reports anything it could not read,
    the push is BLOCKED (X8): a partial plan set is not a scan.
  * Words are runs of `\\w` after `str.casefold()`, so markup and punctuation between words cannot hide a match.
  * A HIT is a run of CONSECUTIVE added lines in one hunk (joined, X9) holding `--window` (default 8)
    consecutive words of one plan string, reported at the line where the run of words starts.
  * A MARKER-ONLY line is judged on its marker alone: an added line equal to a line the same commit REMOVES
    from the same file once one `⟦…⟧` kind marker is stripped (backlog #394).
  * METADATA is pushed text too: every scanned commit's full message (`%B`), every pushed ANNOTATED TAG
    object, PEELED through a tag of a tag (`git cat-file tag`), and every ADDED file's path, empty files
    included (`--diff-filter=A`; two security passes over the redesign, 2026-10-29).
  * A run ALREADY PUBLIC is not a hit: one present in a file at a remote tip, found with THE SAME
    normalisation as the matcher, in Python (X10; `git grep -i` does not fold `ß` to `ss`).

OUTPUT: `path:line`, the commit and the plan FILE, never the matched words, in EVERY channel the hook or a
by-hand run writes (X11: stderr is captured by tools and redirects too). `--show` prints the words, and only
to a terminal: it refuses when stdout is not a TTY.

ESCAPE: `ALLOW_PLAN_LEAK=1` in the push's real ENVIRONMENT (`ALLOW_PLAN_LEAK=1 git push …`), for a judged
coincidence. It skips THIS check only and says so. Chosen over `git push --no-verify`, which also works, because
`--no-verify` skips every pre-push check and the agent push hook refuses it (it needs `ALLOW_DANGEROUS_PUSH=1`);
a judged false positive should not need the dangerous-push decision. Text in a command is no longer read at all.

EXIT CODES: 0 = no hit (or escaped, or no plan text at all — see below) · 1 = hits · 2 = CANNOT RUN, no plan
text in any checkout (BY HAND; the hook ALLOWS this one, loudly, so a fresh clone is not blocked) · 3 = CANNOT
RUN, git failed, a plan could not be read or plan discovery was incomplete (the hook BLOCKS) · 4 = refused
(`--show` without a terminal; installing over a different hooks path).

BOUNDS, stated: ⛔ A PLAN FRAGMENT SHORTER THAN 8 CONSECUTIVE WORDS IS NOT CAUGHT (the owner's window,
2026-10-29: over the last 40 merged commits 8 words gave 1 false hit against 3 at 6, with the same 4 lines on
the bulk-leak commit `f8e974a4`). A generic phrase can match by coincidence, so a hit needs READING. The hook
runs only where `core.hooksPath` is `.githooks` AND the checkout holds `.githooks/pre-push` — a worktree on a
branch older than this file pushes UNCHECKED, and `--status` says so. A plan's headings and paragraphs are
not plan text. A remote tip this clone has never fetched cannot be read, so its content is not counted public
(a false hit, never a missed one).

⚠ THE GATE IS OPT-IN PER CLONE, and two things keep it on: `.claude/hooks/ensure-plan-leak-hook.sh` runs
`--session-start` at every Claude Code session (enables it when `core.hooksPath` is unset; warns LOUDLY and
changes nothing when it points elsewhere), and `.claude/hooks/block-default-branch-push.sh` refuses an agent's
push that mentions `hookspath` or `ALLOW_PLAN_LEAK` anywhere in its raw text without `ALLOW_DANGEROUS_PUSH=1`. That one reads command
TEXT, so it is defence in depth only; this hook owns the decision.
⛔ THE GATE PREVENTS *ACCIDENTAL* PUBLICATION. It is not a boundary against a determined agent: anything with a
shell can bypass git hooks (`--no-verify`, another clone, plumbing such as `git send-pack`).

WHAT WOULD MAKE THIS FAIL (its falsifier): a push whose commits add an 8-word run of plan text succeeds through
the installed hook, or the hook allows a push when it could not read the plans or the remote.
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

CLEAN, HITS, NO_PLANS, CANNOT, REFUSED = 0, 1, 2, 3, 4
ROOT = pathlib.Path(__file__).resolve().parent.parent
WINDOW = 8   # the owner's decision 2026-10-29 — see BOUNDS
ESCAPE = "ALLOW_PLAN_LEAK"
HOOKS_PATH = ".githooks"
GIT_TIMEOUT = 60   # seconds per git call; a timeout is CANNOT RUN, never a pass
ZERO = "0" * 40
COMMIT_TAG = "plan-leak-commit "   # the `--format` line that opens each commit in `pushed_log`

WORD = re.compile(r"\w+")
LIST_ITEM = re.compile(r"^\s*[-*+]\s+(.+?)\s*$", re.M)
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
# ⚠ A MINIMAL LOCAL COPY of backlog #394's marker rule. Its owner is `check-reference-namespace.marker_only`
# (via `gen-backlog-page.kind_mark`), which had NOT landed on master when this guard was written. When it
# lands, import it from there and delete this copy — one rule, one place.
MARKER = re.compile(r"\s*⟦[^⟦⟧]*⟧")
C_ESCAPES = {"n": 10, "t": 9, '"': 34, "\\": 92, "a": 7, "b": 8, "f": 12, "r": 13, "v": 11}


def _plan_reader():
    """`scripts/gen-work-lines.py`, by path (its name has a hyphen). Raises ImportError if it cannot load."""
    spec = importlib.util.spec_from_file_location(
        "_gen_work_lines_for_plan_leak", pathlib.Path(__file__).resolve().parent / "gen-work-lines.py")
    if spec is None or spec.loader is None:
        raise ImportError("cannot load scripts/gen-work-lines.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── the rules (pure) ─────────────────────────────────────────────────────────────────────────────────

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


def unquote_path(raw: str) -> str:
    """PURE. A diff-header path as git wrote it, C-quoted (`"b/a\\"b.md"`) or not, with its `a/`/`b/` kept."""
    if not (len(raw) >= 2 and raw.startswith('"') and raw.endswith('"')):
        return raw
    body, out, i = raw[1:-1], bytearray(), 0
    while i < len(body):
        c = body[i]
        if c == "\\" and i + 1 < len(body):
            nxt = body[i + 1]
            if nxt in "01234567":
                out.append(int(body[i + 1:i + 4], 8))
                i += 4
                continue
            out.append(C_ESCAPES.get(nxt, ord(nxt)))
            i += 2
            continue
        out += c.encode()
        i += 1
    return out.decode("utf-8", "replace")


def parse_log(log_text: str):
    """PURE. `pushed_log`'s text -> (runs, removed).

    runs: [(commit, path, [(new line number, body)…])] — each a maximal run of CONSECUTIVE added lines in one
    hunk. (A new file's NAME is read by `parse_added_paths`, which also sees an EMPTY file with no hunk.) removed: {(commit, path): every line that commit removes from that path}. A `---`/`+++` pair is a
    header only between `diff --git` and the first hunk, so an added line whose text starts `++ ` is content.
    A deleted file has no `b/` side: its lines are removed, never added."""
    runs: list = []
    removed: dict[tuple[str, str], set[str]] = {}
    commit, path, old, header, n, run = "", None, None, False, 0, None
    for line in log_text.split("\n"):
        if line.startswith(COMMIT_TAG):
            commit, path, old, header, run = line[len(COMMIT_TAG):].strip(), None, None, False, None
        elif line.startswith("diff --git "):
            header, path, old, run = True, None, None, None
        elif header and line.startswith("--- "):
            p = unquote_path(line[4:])
            old = p[2:] if p.startswith("a/") else None
        elif header and line.startswith("+++ "):
            p = unquote_path(line[4:])
            path = p[2:] if p.startswith("b/") else None
        elif line.startswith("@@"):
            header, run = False, None
            m = HUNK.match(line)
            n = int(m.group(1)) if m else 0
        elif header:
            continue
        elif line.startswith("+") and path:
            if run is None:
                run = (commit, path, [])
                runs.append(run)
            run[2].append((n, line[1:]))
            n += 1
        elif line.startswith("-") and (path or old):
            removed.setdefault((commit, path or old), set()).add(line[1:])
            run = None
        else:
            run = None
    return runs, removed


def parse_messages(text: str) -> list:
    """PURE. `pushed_messages`' text (NUL-separated `<sha>\x01<full message>` records) -> one run per commit:
    (commit, "<commit message>", [(line number, line)…]). A message is pushed text exactly as a file is."""
    out = []
    for rec in text.split("\0"):
        sha, sep, body = rec.lstrip("\n").partition("\x01")
        if sep and sha.strip():
            out.append((sha.strip(), "<commit message>", list(enumerate(body.split("\n"), 1))))
    return out


def parse_added_paths(text: str) -> list:
    """PURE. `added_paths`' text (`\x01<sha>\0` then NUL-separated paths, per commit) -> a run per ADDED file
    holding its path at line 0. Taken from `--diff-filter=A`, not from diff headers: an EMPTY new file has
    no hunk and no `+++` line worth trusting, and its NAME is pushed text all the same."""
    out = []
    for rec in text.split("\x01"):
        sha, _, rest = rec.partition("\0")
        for name in rest.split("\0"):
            name = name.lstrip("\n")
            if sha.strip() and name:
                out.append((sha.strip(), name, [(0, name)]))
    return out


def tag_run(sha: str, tag_text: str) -> tuple:
    """PURE. One annotated tag object's whole text (header and message) as a run."""
    return (sha, "<annotated tag>", list(enumerate(tag_text.split("\n"), 1)))


def judged_text(key: tuple[str, str], body: str, removed: dict[tuple[str, str], set[str]]) -> str:
    """PURE. The part of added line `body` that is judged: its marker alone when stripping one `⟦…⟧` marker
    reproduces a line the same commit removes from the same file (`key`), else the whole line."""
    m = MARKER.search(body)
    if m and body[:m.start()] + body[m.end():] in removed.get(key, set()):
        return m.group(0)
    return body


def run_windows(runs, removed: dict[tuple[str, str], set[str]], n: int):
    """PURE. Yield (commit, path, [(line where the window starts, window)…]) per run, its lines JOINED."""
    for commit, path, lines in runs:
        flat: list[tuple[int, str]] = []
        for ln, body in lines:
            flat += [(ln, w) for w in words(judged_text((commit, path), body, removed))]
        yield commit, path, [(flat[i][0], tuple(w for _, w in flat[i:i + n])) for i in range(len(flat) - n + 1)]


def candidate_windows(win: dict[tuple[str, ...], str], runs, removed, n: int) -> set[tuple[str, ...]]:
    """PURE. Every plan window some pushed run carries — the only ones worth asking `public_windows`."""
    return {t for _, _, ts in run_windows(runs, removed, n) for _, t in ts if t in win}


def leak_hits(win: dict[tuple[str, ...], str], runs, removed, n: int,
              public: set[tuple[str, ...]]) -> list[tuple[str, int, str, str, str]]:
    """PURE. [(path, line, commit, plan file, phrase)] — one per (commit, path, line) where a run of plan text
    that is NOT `public` starts. The phrase is for `show_lines` ONLY."""
    out, seen = [], set()
    for commit, path, ts in run_windows(runs, removed, n):
        for ln, t in ts:
            src = win.get(t)
            if src is not None and t not in public and (commit, path, ln) not in seen:
                seen.add((commit, path, ln))
                out.append((path, ln, commit, src, " ".join(t)))
    return out


def public_in(texts, cands: set[tuple[str, ...]]) -> set[tuple[str, ...]]:
    """PURE. The candidates that occur in any of `texts`, under the matcher's own normalisation. A text is
    tokenised only when its casefolded form holds every word of some candidate (a cheap, exact superset)."""
    out: set[tuple[str, ...]] = set()
    for text in texts:
        folded = text.casefold()
        live = [t for t in cands - out if all(w in folded for w in t)]
        if not live:
            continue
        w = WORD.findall(folded)
        k = len(live[0])
        have = {tuple(w[i:i + k]) for i in range(len(w) - k + 1)}
        out |= {t for t in live if t in have}
    return out


def report(hits, n_strings: int, n_windows: int, n_runs: int, n: int) -> str:
    """PURE. The verdict text: counts, then `path:line`, the commit and the plan FILE per hit — never the words."""
    head = (f"plan-leak: plan strings {n_strings} · {n}-word windows {n_windows} · "
            f"added runs {n_runs} · hits {len(hits)}")
    return "\n".join([head] + [f"  HIT {_where(p, ln)} in {c[:10]}  (a run of plan text from {src})"
                               for p, ln, c, src, _ in hits])


def _where(path: str, ln: int) -> str:
    """PURE. `path:line`, or the file's NAME when the hit is in the path itself (line 0)."""
    return f"{path}:{ln}" if ln else f"{path} (its file NAME)"


def show_lines(hits) -> str:
    """PURE. The matched phrase per hit — `--show` ONLY, and `main` writes it only to a terminal."""
    return "\n".join(f"  {_where(p, ln)} in {c[:10]}: '{phrase}'" for p, ln, c, _, phrase in hits)


def parse_updates(stdin_text: str) -> list[tuple[str, str]]:
    """PURE. git's pre-push stdin -> [(local_sha, remote_sha)]. A deletion (local all zeros) sends nothing and
    is dropped. ⛔ A malformed line RAISES ValueError — a guess about what a push sends is not a scan."""
    out = []
    for line in stdin_text.splitlines():
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) != 4 or not all(re.fullmatch(r"[0-9a-f]{40,64}", p) for p in (parts[1], parts[3])):
            raise ValueError(f"unreadable pre-push line: {line[:120]!r}")
        if set(parts[1]) != {"0"}:
            out.append((parts[1], parts[3]))
    return out


# ── the fetch (git, the plan files) ──────────────────────────────────────────────────────────────────

def _git(root: pathlib.Path, *args: str, ok=(0,), data: bytes | None = None) -> bytes:
    """The ONE git runner. Raises RuntimeError on any failure — never returns b'' for one."""
    try:
        # ⛔ Inherited GIT_* are dropped: a git HOOK exports `GIT_DIR`, which `-C` does not override.
        r = subprocess.run(["git", "-C", str(root), "-c", "core.quotePath=false", *args],
                           capture_output=True, timeout=GIT_TIMEOUT, input=data,
                           stdin=None if data is not None else subprocess.DEVNULL,
                           env={k: v for k, v in os.environ.items() if not k.startswith("GIT_")})
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"git {args[0]} could not run ({type(exc).__name__})") from exc
    if r.returncode not in ok:
        raise RuntimeError(f"git {args[0]} failed: {r.stderr.decode('utf-8', 'replace').strip()[:200]}")
    return r.stdout


def read_plan_sources(root: pathlib.Path) -> list[tuple[str, str]]:
    """-> [(plan label, plan string)] over every checkout. ⛔ RAISES when discovery was incomplete (X8)."""
    gwl = _plan_reader()
    dirs, notes = gwl.plan_dirs(root)
    if notes:
        raise RuntimeError("plan discovery was incomplete: " + "; ".join(notes))
    sources: list[tuple[str, str]] = []
    for checkout, d in dirs:
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.md")):
            if f.is_file():
                text = f.read_text(errors="replace")
                sources += [(f"{checkout.name}/.claude/plans/{f.name}", s) for s in plan_strings(text, gwl.SERVING)]
    return sources


def remote_tips(root: pathlib.Path, url: str) -> list[str]:
    """Every head and tag sha the REMOTE reports now (`git ls-remote`). Raises when it cannot be asked."""
    out = _git(root, "ls-remote", "--heads", "--tags", url).decode()
    return sorted({line.split()[0] for line in out.splitlines() if line.strip()})


def local_commits(root: pathlib.Path, shas: list[str]) -> list[str]:
    """The `shas` that name a commit (or a tag of one) this clone HOLDS. One `cat-file --batch-check` call."""
    if not shas:
        return []
    out = _git(root, "cat-file", "--batch-check=%(objectname) %(objecttype)",
               data="".join(f"{s}^{{commit}}\n" for s in shas).encode()).decode().splitlines()
    return sorted({line.split()[0] for line in out if line.endswith(" commit")})


def pushed_log(root: pathlib.Path, heads: list[str], exclude: list[str]) -> str:
    """Every commit in `heads` and not in `exclude`, each diffed against its FIRST parent: `-U0`, `--text`,
    no renames, no external diff or textconv. Decoded with replacement, so binary content is still read."""
    out = _git(root, "log", "-p", "--text", "-U0", "--no-color", "--no-ext-diff", "--no-textconv",
               "--no-renames", "--diff-merges=first-parent", f"--format={COMMIT_TAG}%H",
               *heads, "--not", *exclude, "--")
    return out.decode("utf-8", "replace")


def pushed_messages(root: pathlib.Path, heads: list[str], exclude: list[str]) -> str:
    """The full message (`%B`) of every commit `pushed_log` scans, NUL-separated."""
    return _git(root, "log", "-z", "--format=%H%x01%B", *heads, "--not", *exclude, "--").decode("utf-8", "replace")


def added_paths(root: pathlib.Path, heads: list[str], exclude: list[str]) -> str:
    """Every file ADDED by a commit `pushed_log` scans (renames count as adds), NUL-separated, unquoted."""
    return _git(root, "log", "--diff-filter=A", "--name-only", "-z", "--no-renames",
                "--diff-merges=first-parent", "--format=%x01%H", *heads, "--not", *exclude, "--"
                ).decode("utf-8", "replace")


def tag_target(tag_text: str) -> str:
    """PURE. The `object <sha>` a tag object points at ('' if none)."""
    m = re.match(r"object ([0-9a-f]{40,64})\n", tag_text)
    return m.group(1) if m else ""


def tag_runs(root: pathlib.Path, heads: list[str]) -> list:
    """A run per ANNOTATED TAG object reachable from `heads` by PEELING: while an object is a tag, its whole
    text is a run and its target is examined next — a tag of a tag carries two messages."""
    out, seen, todo = [], set(), list(heads)
    while todo:
        sha = todo.pop()
        if sha in seen:
            continue
        seen.add(sha)
        kind = _git(root, "cat-file", "-t", sha).decode().strip()
        if kind == "tag":
            text = _git(root, "cat-file", "tag", sha).decode("utf-8", "replace")
            out.append(tag_run(sha, text))
            todo.append(tag_target(text))
    return out


def public_texts(root: pathlib.Path, tips: list[str]):
    """Yield the text of every distinct blob at every tip in `tips` (binary content included, decoded)."""
    blobs: set[str] = set()
    for tip in tips:
        for line in _git(root, "ls-tree", "-r", "-z", tip).split(b"\0"):
            meta = line.split(b"\t", 1)[0].split()
            if len(meta) == 3 and meta[1] == b"blob":
                blobs.add(meta[2].decode())
    if not blobs:
        return
    data = _git(root, "cat-file", "--batch", data=("\n".join(sorted(blobs)) + "\n").encode())
    i = 0
    while i < len(data):
        j = data.index(b"\n", i)
        size = int(data[i:j].split()[2])
        yield data[j + 1:j + 1 + size].decode("utf-8", "replace")
        i = j + 1 + size + 1


def scan(root: pathlib.Path, heads: list[str], exclude: list[str], public_tips: list[str], n: int):
    """-> (exit code, message, hits). Every CANNOT RUN says so in words; none of them is a pass."""
    try:
        sources = read_plan_sources(root)
    except Exception as exc:  # noqa: BLE001 — any failure to read the plans is CANNOT RUN (3)
        return CANNOT, (f"plan-leak: CANNOT RUN — the plans could not be read ({type(exc).__name__}: {exc}). "
                        f"Treat this as NOT RUN."), []
    win = windows(sources, n)
    if not win:
        return NO_PLANS, (f"plan-leak: CANNOT RUN — no plan text in any checkout's .claude/plans/ "
                          f"({len(sources)} plan strings, none of {n} words or more). Nothing was compared, so "
                          f"treat this as NOT RUN."), []
    try:
        runs, removed = parse_log(pushed_log(root, heads, exclude)) if heads else ([], {})
        if heads:
            runs += (parse_messages(pushed_messages(root, heads, exclude))
                     + parse_added_paths(added_paths(root, heads, exclude)) + tag_runs(root, heads))
        cands = candidate_windows(win, runs, removed, n)
        public = public_in(public_texts(root, public_tips), cands) if cands else set()
    except Exception as exc:  # noqa: BLE001 — any git or decode failure is CANNOT RUN (3)
        return CANNOT, f"plan-leak: CANNOT RUN — {exc}. Treat this as NOT RUN.", []
    hits = leak_hits(win, runs, removed, n, public)
    return (HITS if hits else CLEAN), report(hits, len(sources), len(win), len(runs), n), hits


# ── the hooks path ───────────────────────────────────────────────────────────────────────────────────

def hooks_status(root: pathlib.Path) -> tuple[bool, str]:
    """-> (active, message) for the checkout at `root`. Active iff `core.hooksPath` is `.githooks` AND this
    checkout holds an executable `.githooks/pre-push`."""
    cur = _git(root, "config", "--get", "core.hooksPath", ok=(0, 1)).decode().strip()
    hook = root / HOOKS_PATH / "pre-push"
    if cur != HOOKS_PATH:
        return False, (f"plan-leak hook NOT ACTIVE: core.hooksPath is {cur or 'unset'!r}, not {HOOKS_PATH!r}. "
                       f"Run scripts/install-git-hooks.sh")
    if not (hook.is_file() and os.access(hook, os.X_OK)):
        return False, (f"plan-leak hook NOT ACTIVE in this checkout: {HOOKS_PATH}/pre-push is missing or not "
                       f"executable here (a branch older than the hook) — pushes from here are UNCHECKED")
    return True, "plan-leak hook ACTIVE — every push from this checkout runs .githooks/pre-push"


def install_hooks(root: pathlib.Path) -> tuple[int, str]:
    """Set `core.hooksPath` to `.githooks`. Idempotent. ⛔ REFUSES a different existing hooks path, and live
    hooks in the git dir — setting the path would silently switch those off."""
    cur = _git(root, "config", "--get", "core.hooksPath", ok=(0, 1)).decode().strip()
    if cur == HOOKS_PATH:
        return CLEAN, f"already installed: core.hooksPath is {HOOKS_PATH!r}"
    if cur:
        return REFUSED, (f"REFUSED: core.hooksPath is already {cur!r}. Setting it to {HOOKS_PATH!r} would switch "
                         f"those hooks off; merge them by hand, then re-run.")
    common = pathlib.Path(_git(root, "rev-parse", "--path-format=absolute", "--git-common-dir").decode().strip())
    live = sorted(p.name for p in (common / "hooks").glob("*") if p.is_file() and not p.name.endswith(".sample"))
    if live:
        return REFUSED, (f"REFUSED: {common / 'hooks'} holds live hooks ({', '.join(live)}), which "
                         f"core.hooksPath would switch off. Move them into {HOOKS_PATH}/ first.")
    _git(root, "config", "core.hooksPath", HOOKS_PATH)
    return CLEAN, f"installed: core.hooksPath = {HOOKS_PATH!r} (shared by every worktree of this clone)"


def session_start(root: pathlib.Path) -> tuple[bool, str]:
    """-> (loud, message) for a Claude Code session starting in `root`. ACTIVE: one quiet line. Not active
    and `core.hooksPath` UNSET: install (idempotent, local config only). `core.hooksPath` pointing ELSEWHERE,
    an install refused, or a checkout without the hook file: a LOUD warning that the gate is OFF — never an
    overwrite. Never raises: a session must start."""
    try:
        active, msg = hooks_status(root)
        if active:
            return False, msg
        cur = _git(root, "config", "--get", "core.hooksPath", ok=(0, 1)).decode().strip()
        if not cur:
            rc, imsg = install_hooks(root)
            if rc == CLEAN and hooks_status(root)[0]:
                return False, f"plan-leak hook was not enabled in this clone; {imsg}"
            return True, f"⚠ THE PLAN-LEAK PUSH GATE IS OFF in this clone — {imsg}"
        return True, (f"⚠ THE PLAN-LEAK PUSH GATE IS OFF — {msg}. Pushes are NOT checked for quoted plan text. "
                      f"Nothing was changed; fix core.hooksPath by hand.")
    except Exception as exc:  # noqa: BLE001 — a session must start; the failure is reported, loudly
        return True, f"⚠ THE PLAN-LEAK PUSH GATE could not be checked ({type(exc).__name__}: {exc}) — treat it as OFF."


# ── entry points ─────────────────────────────────────────────────────────────────────────────────────

def pre_push(root: pathlib.Path, url: str, stdin_text: str, n: int, err) -> int:
    """git's pre-push hook. Non-zero aborts the push. Writes ONLY to `err` (git shows it to the pusher)."""
    if os.environ.get(ESCAPE) == "1":
        print(f"plan-leak: {ESCAPE}=1 is set in this push's environment — the plan-leak scan was SKIPPED.",
              file=err)
        return CLEAN
    try:
        updates = parse_updates(stdin_text)
        tips = local_commits(root, remote_tips(root, url) + [r for _, r in updates if r != ZERO])
    except Exception as exc:  # noqa: BLE001 — not knowing what is pushed, or what is public, blocks
        print(f"plan-leak: CANNOT RUN — {exc}. The push is BLOCKED; fix it, or set {ESCAPE}=1.", file=err)
        return CANNOT
    if not updates:
        return CLEAN   # only deletions: nothing is sent
    rc, msg, _ = scan(root, [l for l, _ in updates], tips, tips, n)
    print(msg, file=err)
    if rc == NO_PLANS:
        print("⚠ plan-leak NOT RUN: no plan files were found, so this push was NOT checked for plan text. "
              "Allowed (a fresh clone has none).", file=err)
        return CLEAN
    if rc == HITS:
        print(f"Blocked: the commits above add lines quoting a PRIVATE plan (the repo is public). Reword them "
              f"(`git commit --amend` / rebase), or for a judged coincidence push with {ESCAPE}=1. "
              f"`python3 scripts/check-plan-leak.py --show` in a terminal prints the matched words.", file=err)
    elif rc != CLEAN:
        print(f"The push is BLOCKED; fix what is named, or set {ESCAPE}=1.", file=err)
    return rc


def main(argv: list[str], root: pathlib.Path = ROOT, stdin=None, out=None, err=None, tty=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", default="origin/master")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--window", type=int, default=WINDOW)
    ap.add_argument("--show", action="store_true", help="also print the matched words — to a terminal only")
    ap.add_argument("--pre-push", nargs=2, metavar=("REMOTE", "URL"), help="run as git's pre-push hook")
    ap.add_argument("--install-hooks", action="store_true")
    ap.add_argument("--hooks-status", action="store_true")
    ap.add_argument("--session-start", action="store_true", help="the SessionStart hook: enable or warn")
    a = ap.parse_args(argv)
    out, err = out or sys.stdout, err or sys.stderr
    if a.window < 1:
        ap.error("--window must be at least 1")
    if a.pre_push:
        return pre_push(root, a.pre_push[1], (stdin or sys.stdin).read(), a.window, err)
    if a.session_start:
        loud, msg = session_start(root)
        if loud:
            print(json.dumps({"systemMessage": msg, "hookSpecificOutput": {
                "hookEventName": "SessionStart", "additionalContext": msg}}), file=out)
        else:
            print(msg, file=out)
        return CLEAN
    if a.install_hooks or a.hooks_status:
        try:
            rc, msg = install_hooks(root) if a.install_hooks else ((lambda s: (CLEAN if s[0] else HITS, s[1]))
                                                                   (hooks_status(root)))
        except RuntimeError as exc:
            rc, msg = CANNOT, f"CANNOT RUN — {exc}"
        print(msg, file=out)
        return rc
    if a.show and not (out.isatty() if tty is None else tty):
        print("REFUSED: --show prints private plan words and writes only to a terminal; stdout is not one "
              "(a tool capture or a redirect would keep them).", file=err)
        return REFUSED
    try:
        base = _git(root, "rev-parse", "--verify", f"{a.base}^{{commit}}").decode().strip()
        head = _git(root, "rev-parse", "--verify", f"{a.head}^{{commit}}").decode().strip()
    except RuntimeError as exc:
        print(f"plan-leak: CANNOT RUN — {exc}. Treat this as NOT RUN.", file=out)
        return CANNOT
    rc, msg, hits = scan(root, [head], [base], [base], a.window)
    print(msg, file=out)
    if a.show and hits:
        print(show_lines(hits), file=out)
    return rc


def _self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: it builds git repositories (backlog #373)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
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
    UML = "the Straße beside the old mill floods every spring"                     # 9 words, a ß
    NEAR = "we calibrate the walrus engine before teatime tomorrow lunch"            # 7 words of STEP
    PLAN = (f"# a plan\n\n<!-- serving: {OBJ} -->\n\n### Task 1\n\n- [ ] **Step 1** — {STEP}\n"
            f"  - **Why:** {SUB}\n  - {UML}\n\nplain prose about seven quiet harbour lanterns glowing late\n")
    src = [("p.md", s) for s in plan_strings(PLAN, SERVING)]
    W8 = windows(src, 8)
    C = "c0ffee"

    def log_of(path, plus, minus=(), start=1, commit=C, qpath=None):
        q = qpath or f"b/{path}"
        body = "".join(f"-{x}\n" for x in minus) + "".join(f"+{x}\n" for x in plus)
        return (f"{COMMIT_TAG}{commit}\n\ndiff --git a/{path} b/{path}\n--- a/{path}\n+++ {q}\n"
                f"@@ -{start},{len(minus)} +{start},{len(plus)} @@\n{body}")

    def hits_of(log, n=8, win=None, public=frozenset()):
        runs, removed = parse_log(log)
        return [(p, ln) for p, ln, _, _, _ in leak_hits(W8 if win is None else win, runs, removed, n, set(public))]

    # ── the plan text ────────────────────────────────────────────────────────────────────────────────
    check("plan_strings reads the objective, the step and its indented sub-bullets",
          lambda: plan_strings(PLAN, SERVING), [OBJ, f"[ ] **Step 1** — {STEP}", f"**Why:** {SUB}", UML])
    check("...and NOT a plain prose line, which is outside plan text by the stated bound",
          lambda: any("lanterns" in s for s in plan_strings(PLAN, SERVING)), False)
    check("the objective is read through the serving pattern it is GIVEN, not a constant",
          lambda: plan_strings("<!-- goal: a b -->\n", re.compile(r"<!--\s*goal:\s*(.+?)\s*-->")), ["a b"])
    check("words casefolds (ß to ss) and drops markup and punctuation",
          lambda: words("**Calibrate** the `walrus`, STRAßE!"), ["calibrate", "the", "walrus", "strasse"])
    check("windows of 8 over a 10-word string are 3, each labelled with its plan file",
          lambda: sorted(set(windows([("a.md", STEP)], 8).values())) + [len(windows([("a.md", STEP)], 8))],
          ["a.md", 3])
    check("windows of 10 over the same string are ONE run of 10 words — the size is the one GIVEN",
          lambda: [len(t) for t in windows([("a.md", STEP)], 10)], [10])
    check("a plan string shorter than the window yields no window",
          lambda: windows([("a.md", "only seven words are written right here")], 8), {})

    # ── reading what a push sends ────────────────────────────────────────────────────────────────────
    two_hunks = (log_of("docs/a.md", ["harmless line"], start=3)
                 + f"@@ -10,0 +12,2 @@\n+another harmless line\n+we must {STEP} ok\n")
    check("⭐ KNOWN POSITIVE: an 8-word run of a plan step in an added line is a hit, at the right line",
          lambda: hits_of(two_hunks), [("docs/a.md", 13)])
    check("the objective is plan text too", lambda: hits_of(log_of("README.md", [f"note: {OBJ}."])),
          [("README.md", 1)])
    check("an indented sub-bullet is plan text too", lambda: hits_of(log_of("README.md", [f"x {SUB}"])),
          [("README.md", 1)])
    check("a 7-word NEAR MISS is not a hit at the default 8", lambda: hits_of(log_of("docs/a.md", [NEAR])), [])
    check("⭐ a MARKUP-SPLIT match is still a hit: casefold, bold, code and commas do not hide it",
          lambda: hits_of(log_of("docs/a.md", ["**CALIBRATE** the `walrus`, engine — before teatime, "
                                               "*tomorrow* EVENING"])), [("docs/a.md", 1)])
    check("the window size is the one GIVEN: the 7-word run hits at --window 7",
          lambda: hits_of(log_of("docs/a.md", [NEAR]), 7, windows(src, 7)), [("docs/a.md", 1)])
    half = words(STEP)
    check("⭐ X9: a run WRAPPED across two consecutive added lines is joined, and hits where it starts",
          lambda: hits_of(log_of("docs/a.md", ["intro " + " ".join(half[:5]), " ".join(half[5:]) + " end"])),
          [("docs/a.md", 1)])
    check("...but two added lines in DIFFERENT hunks are not joined",
          lambda: hits_of(log_of("docs/a.md", [" ".join(half[:5])]) + f"@@ -9,0 +9 @@\n+{' '.join(half[5:])}\n"), [])
    check("...nor two separated by a removed line",
          lambda: hits_of(f"{COMMIT_TAG}{C}\ndiff --git a/a b/a\n--- a/a\n+++ b/a\n@@ -1,1 +1,2 @@\n"
                          f"+{' '.join(half[:5])}\n-gone\n+{' '.join(half[5:])}\n"), [])
    check("a REMOVED line carrying plan text is not judged",
          lambda: hits_of(log_of("docs/a.md", ["harmless"], [f"old {STEP}"])), [])
    check("an added line whose own text starts `++ ` is content, not a file header",
          lambda: hits_of(log_of("docs/a.md", [f"++ {STEP}"])), [("docs/a.md", 1)])
    check("⭐ X5: a C-QUOTED path is decoded, not dropped",
          lambda: hits_of(log_of('q"n.md', [STEP], qpath='"b/q\\"n.md"')), [('q"n.md', 1)])
    check("unquote_path decodes octal escapes to UTF-8 and leaves a plain path alone",
          lambda: (unquote_path('"b/caf\\303\\251.md"'), unquote_path("b/plain.md")), ("b/café.md", "b/plain.md"))
    check("a deleted file's lines are removed, not added",
          lambda: parse_log(f"{COMMIT_TAG}{C}\ndiff --git a/x.md b/x.md\ndeleted file mode 100644\n--- a/x.md\n"
                            f"+++ /dev/null\n@@ -1 +0,0 @@\n-{STEP}\n"), ([], {(C, "x.md"): {STEP}}))
    check("each commit's lines are keyed to THAT commit",
          lambda: [r[0] for r in parse_log(log_of("a.md", ["x"], commit="aaa") + log_of("a.md", ["y"], commit="bbb"))[0]],
          ["aaa", "bbb"])
    check("parse_added_paths: each ADDED file's path is a run of its own, at line 0, under its commit",
          lambda: parse_added_paths('\x01aaa\0\nd/z\0\x01bbb\0\ne mpty.md\0q"x\0'),
          [("aaa", "d/z", [(0, "d/z")]), ("bbb", "e mpty.md", [(0, "e mpty.md")]), ("bbb", 'q"x', [(0, 'q"x')])])
    check("parse_added_paths of no added file is no runs", lambda: parse_added_paths(""), [])
    check("tag_target reads the object a tag points at",
          lambda: (tag_target("object " + "a" * 40 + "\ntype tag\n"), tag_target("garbage")), ("a" * 40, ""))
    check("parse_messages reads each commit's full message as one run",
          lambda: parse_messages(f"aaa\x01subject\n\nbody line\n\0bbb\x01other\0"),
          [("aaa", "<commit message>", [(1, "subject"), (2, ""), (3, "body line"), (4, "")]),
           ("bbb", "<commit message>", [(1, "other")])])
    check("tag_run reads a tag object's whole text",
          lambda: tag_run("t1", "object x\ntag v1\n\nmsg"), ("t1", "<annotated tag>",
                                                               [(1, "object x"), (2, "tag v1"), (3, ""), (4, "msg")]))
    check("parse_messages of an empty log is no runs", lambda: parse_messages(""), [])
    check("tag_run keeps the tag's own sha", lambda: tag_run("t2", "x")[0], "t2")
    check("a hit in a path itself is reported as the file NAME, not line 0",
          lambda: report([("n.md", 0, "abc", "p.md", "x")], 1, 1, 1, 8).splitlines()[1].split(" in ")[0],
          "  HIT n.md (its file NAME)")
    row = "| 7 | the item text | x |"
    marked = "| 7 | the item text ⟦kind: defect⟧ | x |"
    check("⭐ a MARKER-ONLY line (equal to a removed line once its ⟦…⟧ marker is stripped) is not judged",
          lambda: judged_text((C, "docs/backlog.md"), marked, {(C, "docs/backlog.md"): {row}}), " ⟦kind: defect⟧")
    plan_row = f"| 7 | {STEP} | x |"
    check("...so a marker added to a line ALREADY quoting plan text in the base is not a new hit",
          lambda: hits_of(log_of("docs/backlog.md", [f"| 7 | {STEP} ⟦kind: defect⟧ | x |"], [plan_row])), [])
    check("⭐ a marker PLUS a changed word is judged whole, and hits",
          lambda: hits_of(log_of("docs/backlog.md", [f"| 7 | now {STEP} ⟦kind: defect⟧ | x |"], [plan_row])),
          [("docs/backlog.md", 1)])
    check("the marker itself is still judged — a plan run inside a marker hits",
          lambda: hits_of(log_of("docs/backlog.md", [f"| 7 | the item text ⟦kind: {STEP}⟧ | x |"], [row])),
          [("docs/backlog.md", 1)])
    check("the exemption is per FILE: the same removed line in another file exempts nothing",
          lambda: judged_text((C, "docs/other.md"), marked, {(C, "docs/backlog.md"): {row}}), marked)
    check("...and per COMMIT: a line removed by another commit exempts nothing",
          lambda: judged_text(("other", "docs/backlog.md"), marked, {(C, "docs/backlog.md"): {row}}), marked)

    check("judged_text returns an unmarked line whole",
          lambda: judged_text((C, "docs/a.md"), f"plain {STEP}", {(C, "docs/a.md"): {"plain"}}), f"plain {STEP}")
    runs1, rem1 = parse_log(log_of("docs/a.md", [f"we {STEP} ok"]))
    first = tuple(words(STEP)[:8])
    check("candidate_windows lists exactly the plan windows the pushed runs carry",
          lambda: sorted(candidate_windows(W8, runs1, rem1, 8)), sorted(windows([("p.md", STEP)], 8)))
    check("candidate_windows reads the window size GIVEN: at 10 there is one",
          lambda: len(candidate_windows(windows(src, 10), runs1, rem1, 10)), 1)
    runs2, rem2 = parse_log(log_of("docs/backlog.md", [f"| 7 | {STEP} ⟦kind: defect⟧ | x |"], [plan_row]))
    check("candidate_windows reads the JUDGED text: a marker-only line offers no candidate",
          lambda: candidate_windows(W8, runs2, rem2, 8), set())
    check("⭐ a window ALREADY PUBLIC is not a hit",
          lambda: leak_hits(W8, runs1, rem1, 8, set(windows([("p.md", STEP)], 8))), [])
    check("...but one private window left on the run still hits",
          lambda: [(p, ln) for p, ln, _, _, _ in leak_hits(W8, runs1, rem1, 8, {first})], [("docs/a.md", 1)])
    check("public_in finds a candidate in a text, under casefold",
          lambda: public_in([f"Old copy: {STEP.upper()}."], {first}), {first})
    check("⭐ X10: public_in folds ß the way the matcher does — `STRASSE` text makes a `Straße` run public",
          lambda: public_in([UML.upper().replace("ß", "SS")], set(windows([("p.md", UML)], 8))),
          set(windows([("p.md", UML)], 8)))
    check("public_in does not count the words in another ORDER",
          lambda: public_in([" ".join(reversed(first))], {first}), set())

    hit1 = [("docs/a.md", 13, "abcdef0123456789", "main/.claude/plans/p.md", " ".join(first))]
    rep = report(hit1, 3, 9, 4, 8)
    check("the report names the file, the line, the commit and the plan FILE",
          lambda: ("docs/a.md:13" in rep, "abcdef0123" in rep, "main/.claude/plans/p.md" in rep, "hits 1" in rep),
          (True, True, True, True))
    check("⛔ the report never carries the matched phrase", lambda: " ".join(first) in rep, False)
    check("the report's counts are the ones GIVEN", lambda: report([], 5, 2, 7, 4).splitlines(),
          ["plan-leak: plan strings 5 · 4-word windows 2 · added runs 7 · hits 0"])
    check("show_lines carries the matched phrase at its path:line",
          lambda: f"docs/a.md:13 in abcdef0123: '{' '.join(first)}'" in show_lines(hit1), True)
    check("show_lines of no hits is empty", lambda: show_lines([]), "")
    Z, A, B = ZERO, "a" * 40, "b" * 40
    check("parse_updates reads a ref update and DROPS a deletion",
          lambda: parse_updates(f"refs/heads/x {A} refs/heads/x {B}\n(delete) {Z} refs/heads/y {A}\n"), [(A, B)])
    check("parse_updates keeps a NEW ref, whose remote sha is all zeros",
          lambda: parse_updates(f"refs/tags/t {B} refs/tags/t {Z}\n"), [(B, Z)])
    check("⛔ parse_updates REFUSES a line it cannot read",
          lambda: _raises(lambda: parse_updates("garbage\n")),
          "ValueError")

    # ── REAL `git push` through the SHIPPED hook, into bare remotes the cases build ─────────────────
    td = pathlib.Path(tempfile.mkdtemp(prefix="plan-leak-"))
    real_git = shutil.which("git")
    try:
        def git(repo, *args, env=None, check_rc=True):
            r = subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.com",
                                *args], capture_output=True, text=True, env=env)
            if check_rc and r.returncode != 0:
                raise RuntimeError(f"git {args}: {r.stderr}")
            return r

        def world(name, plan=PLAN, base_files=None):
            """A bare remote and a clone with the hook INSTALLED. The guard's own files are untracked and
            excluded, so the remote never holds the synthetic phrases in this source."""
            bare, w = td / f"{name}.git", td / name
            subprocess.run(["git", "init", "-q", "--bare", "-b", "master", str(bare)], check=True)
            subprocess.run(["git", "clone", "-q", str(bare), str(w)], check=True, capture_output=True)
            git(w, "checkout", "-q", "-b", "master")
            (w / ".git" / "info" / "exclude").write_text(".claude/\nscripts/\n.githooks/\n")
            for rel in ("scripts/check-plan-leak.py", "scripts/gen-work-lines.py", "scripts/install-git-hooks.sh",
                        ".githooks/pre-push"):
                (w / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / rel, w / rel)
            for rel, text in (base_files or {"README.md": "base\n"}).items():
                (w / rel).write_text(text)
            git(w, "add", "-A")
            git(w, "commit", "-q", "-m", "base")
            git(w, "push", "-q", "origin", "master")
            if plan is not None:
                (w / ".claude" / "plans").mkdir(parents=True)
                (w / ".claude" / "plans" / "fx.md").write_text(plan)
            r = subprocess.run(["bash", str(w / "scripts" / "install-git-hooks.sh")], cwd=w, capture_output=True,
                               text=True)
            if r.returncode != 0:
                raise RuntimeError(f"install: {r.stdout}{r.stderr}")
            return w

        def commit(w, rel, text, msg="c"):
            (w / rel).parent.mkdir(parents=True, exist_ok=True)
            (w / rel).write_bytes(text.encode() if isinstance(text, str) else text)
            git(w, "add", "--", rel)
            git(w, "commit", "-q", "-m", msg)

        def push(w, *args, env=None, cwd=None):
            r = subprocess.run(["git", *args], cwd=cwd or w, capture_output=True, text=True,
                               env={**os.environ, **(env or {})})
            return r.returncode, r.stdout + r.stderr

        def remote_has(w, ref):
            return git(w, "ls-remote", "origin", ref).stdout.strip() != ""

        w = world("plain")
        commit(w, "README.md", f"base\nwe {STEP} now\n")
        rc, out = push(w, "push", "origin", "master")
        check("⭐ REAL PUSH: a commit adding plan text is REFUSED by the installed hook, and named at README.md:2",
              lambda: (rc != 0, "README.md:2" in out, "HIT" in out), (True, True, True))
        check("⛔ ...and nothing the push printed carries the matched words",
              lambda: any(" ".join(words(STEP)[i:i + 3]) in " ".join(words(out)) for i in range(8)), False)
        check("...and the remote did not move", lambda: git(w, "rev-parse", "origin/master").stdout ==
              git(w, "ls-remote", "origin", "refs/heads/master").stdout.split()[0] + "\n", True)
        rc, out = push(w, "push", "origin", "master", env={ESCAPE: "1"})
        check("⭐ the escape is the push's real ENVIRONMENT: ALLOW_PLAN_LEAK=1 lets it through, and says so",
              lambda: (rc, "SKIPPED" in out), (0, True))

        w = world("history")
        commit(w, "a.md", f"{STEP}\n")
        commit(w, "a.md", "clean again\n")
        rc, out = push(w, "push", "origin", "master")
        check("⭐ X1: a leak committed and then removed is still REFUSED — history is pushed, not the tree",
              lambda: (rc != 0, "a.md:1" in out), (True, True))

        w = world("refs")
        git(w, "checkout", "-q", "-b", "secret")
        commit(w, "s.md", f"{OBJ}\n")
        git(w, "checkout", "-q", "master")
        rc, out = push(w, "push", "origin", "secret")
        check("⭐ X2: pushing a leaking branch from a clean HEAD is REFUSED",
              lambda: (rc != 0, "s.md:1" in out, remote_has(w, "refs/heads/secret")), (True, True, False))
        git(w, "tag", "t1", "secret")
        rc, out = push(w, "push", "origin", "t1")
        check("X2: so is a TAG pointing at a leaking commit", lambda: (rc != 0, remote_has(w, "refs/tags/t1")),
              (True, False))
        rc, out = push(w, "push", "origin", "--all")
        check("X2: and `--all`", lambda: (rc != 0, remote_has(w, "refs/heads/secret")), (True, False))
        rc, out = push(w, "-C", str(w), "-c", "x.y=z", "push", "origin", "secret", cwd=td)
        check("⭐ X3: `git -C <repo> -c x.y=z push` from ANOTHER directory is REFUSED",
              lambda: (rc != 0, "s.md:1" in out), (True, True))
        git(w, "config", "alias.ship", "push origin secret")
        rc, out = push(w, "ship")
        check("X3: so is an ALIAS for push", lambda: (rc != 0, "s.md:1" in out), (True, True))
        rc, out = push(w, "push", "origin", "secret", env={ESCAPE: "0"})
        check("X4: an escape variable set to anything but 1 does not escape", lambda: rc != 0, True)
        git(w, "push", "-q", "origin", "master:refs/heads/master-copy")
        rc, out = push(w, "push", "origin", ":refs/heads/master-copy")
        check("a DELETION sends nothing and is not scanned — no plan-leak verdict line at all",
              lambda: "plan-leak:" in out, False)

        w = world("meta")
        commit(w, "ok.md", "harmless\n", msg=f"subject\n\nbody: {STEP}")
        rc, out = push(w, "push", "origin", "master")
        check("⭐ METADATA: plan text in a pushed COMMIT MESSAGE is REFUSED",
              lambda: (rc != 0, "<commit message>:3" in out), (True, True))
        git(w, "reset", "-q", "--hard", "origin/master")
        git(w, "tag", "-a", "v1", "-m", f"release: {OBJ}")
        rc, out = push(w, "push", "origin", "v1")
        check("⭐ METADATA: plan text in a pushed ANNOTATED TAG's message is REFUSED",
              lambda: (rc != 0, "<annotated tag>" in out, remote_has(w, "refs/tags/v1")), (True, True, False))
        commit(w, "-".join(words(SUB)) + ".md", "harmless\n")
        rc, out = push(w, "push", "origin", "master")
        check("⭐ METADATA: a NEW FILE NAMED with plan words is REFUSED, though its content is clean",
              lambda: (rc != 0, "(its file NAME)" in out), (True, True))
        git(w, "reset", "-q", "--hard", "origin/master")
        commit(w, "-".join(words(OBJ)) + ".md", "")
        rc, out = push(w, "push", "origin", "master")
        check("⭐ METADATA: an EMPTY new file (no hunk at all) NAMED with plan words is REFUSED",
              lambda: (rc != 0, "(its file NAME)" in out), (True, True))
        git(w, "reset", "-q", "--hard", "origin/master")
        git(w, "tag", "-a", "inner", "-m", "a plain inner tag")
        git(w, "tag", "-a", "outer", "inner", "-m", f"outer: {SUB}")
        git(w, "tag", "-a", "outer2", "outer", "-m", "a plain outermost tag")
        rc, out = push(w, "push", "origin", "outer2")
        check("⭐ METADATA: a tag of a tag is PEELED — plan text in the MIDDLE tag's message is REFUSED",
              lambda: (rc != 0, "<annotated tag>" in out, remote_has(w, "refs/tags/outer2")), (True, True, False))

        w = world("quoted")
        commit(w, 'q"n.md', f"{STEP}\n")
        rc, out = push(w, "push", "origin", "master")
        check("⭐ X5 REAL PUSH: a leak in a file whose name git QUOTES is REFUSED, named unquoted",
              lambda: (rc != 0, 'q"n.md:1' in out), (True, True))

        w = world("binary")
        commit(w, "b.bin", b"\x00\x01binary " + STEP.encode() + b"\n")
        rc, out = push(w, "push", "origin", "master")
        check("⭐ X6 REAL PUSH: plan text in a BINARY file is REFUSED", lambda: (rc != 0, "b.bin:1" in out), (True, True))

        w = world("fakebase")
        commit(w, "x.md", f"{STEP}\n")
        git(w, "update-ref", "refs/remotes/origin/master", "HEAD")
        commit(w, "y.md", f"again {STEP}\n")
        rc, out = push(w, "push", "origin", "master")
        check("⭐ X7: a leak placed in a LOCAL origin/master by update-ref is not 'public' — REFUSED",
              lambda: (rc != 0, "x.md:1" in out, "y.md:1" in out), (True, True, True))

        w = world("public", base_files={"README.md": "base\n", "old.md": f"already said: {STEP}\n"})
        commit(w, "new.md", f"said again: {STEP}\n")
        rc, out = push(w, "push", "origin", "master")
        check("a phrase ALREADY ON THE REMOTE is public: the push is allowed", lambda: (rc, "hits 0" in out), (0, True))

        w = world("umlaut", base_files={"README.md": "base\n", "old.md": f"{UML}\n"})
        commit(w, "new.md", UML.upper().replace("ß", "SS") + "\n")
        rc, out = push(w, "push", "origin", "master")
        check("⭐ X10 REAL PUSH: an upper-cased `STRASSE` copy of a public `Straße` run is allowed",
              lambda: rc, 0)

        w = world("wrap")
        commit(w, "w.md", "intro " + " ".join(half[:5]) + "\n" + " ".join(half[5:]) + " end\n")
        rc, out = push(w, "push", "origin", "master")
        check("⭐ X9 REAL PUSH: a run wrapped across two lines is REFUSED", lambda: (rc != 0, "w.md:1" in out),
              (True, True))

        w = world("newref")
        git(w, "checkout", "-q", "-b", "fresh")
        rc, out = push(w, "push", "origin", "fresh")
        check("a NEW branch whose commits the remote already has is allowed", lambda: rc, 0)

        w = world("worktree")
        (w / ".claude").rename(td / "moved-claude")
        wt = td / "worktree-side"
        git(w, "worktree", "add", "-q", "-b", "side", str(wt))
        (wt / ".claude").mkdir()
        (td / "moved-claude" / "plans").rename(wt / ".claude" / "plans")
        commit(w, "m.md", f"{SUB}\n")
        rc, out = push(w, "push", "origin", "master")
        check("⭐ a plan held only in ANOTHER worktree is read: the push is REFUSED", lambda: (rc != 0, "m.md:1" in out),
              (True, True))
        # X8 is driven through the hook's own entry point with the stdin git sends, not through `git push`:
        # measured, git PREPENDS its exec-path (which holds a real `git`) to a hook's PATH, so a PATH shim
        # cannot reach the hook's git calls. In-process, the shim is first on PATH for every git it runs.
        shim = td / "shim"
        shim.mkdir()
        (shim / "git").write_text(f'#!/bin/sh\nfor a in "$@"; do [ "$a" = worktree ] && exit 128; done\n'
                                  f'exec "{real_git}" "$@"\n')
        (shim / "git").chmod(0o755)
        x8_head = git(w, "rev-parse", "HEAD").stdout.strip()
        x8_base = git(w, "rev-parse", "origin/master").stdout.strip()
        saved_path = os.environ["PATH"]
        os.environ["PATH"] = f"{shim}:{saved_path}"
        try:
            o8, e8 = io.StringIO(), io.StringIO()
            rc = main(["--pre-push", "origin", str(td / "worktree.git")], root=w,
                      stdin=io.StringIO(f"refs/heads/master {x8_head} refs/heads/master {x8_base}\n"), out=o8, err=e8)
        finally:
            os.environ["PATH"] = saved_path
        check("⭐ X8: when `git worktree list` FAILS the push is BLOCKED, not scanned with fewer plans",
              lambda: (rc, "CANNOT RUN" in e8.getvalue(), "incomplete" in e8.getvalue()), (CANNOT, True, True))

        w = world("noplans", plan=None)
        commit(w, "n.md", f"{STEP}\n")
        rc, out = push(w, "push", "origin", "master")
        check("with NO plan files the push is ALLOWED, loudly NOT RUN", lambda: (rc, "NOT RUN" in out), (0, True))

        w = world("crash")
        commit(w, "c.md", "harmless\n")
        (w / "scripts" / "check-plan-leak.py").write_text("raise SystemExit(5)\n")
        rc, out = push(w, "push", "origin", "master")
        check("⛔ a CRASHED checker aborts the push — git refuses on any non-zero hook", lambda: rc != 0, True)

        # main, driven directly over the worlds above
        def drive(argv, root, stdin_text="", tty=None):
            o, e = io.StringIO(), io.StringIO()
            rc = main(argv, root=root, stdin=io.StringIO(stdin_text), out=o, err=e, tty=tty)
            return rc, o.getvalue(), e.getvalue()

        p = td / "plain"
        head = git(p, "rev-parse", "HEAD").stdout.strip()
        rc, o, e = drive(["--pre-push", "origin", str(td / "no-such.git")], p,
                         f"refs/heads/master {head} refs/heads/master {ZERO}\n")
        check("⭐ the remote cannot be asked (ls-remote fails): CANNOT RUN, BLOCKED", lambda: (rc, "CANNOT RUN" in e),
              (CANNOT, True))
        rc, o, e = drive(["--pre-push", "origin", str(td / "plain.git")], p, "not a ref line\n")
        check("an unreadable pre-push stdin BLOCKS", lambda: rc, CANNOT)
        rc, o, e = drive(["--base", "HEAD~1", "--head", "HEAD"], p)
        check("by hand: --base/--head scans the commits between, exit 1, path:line on stdout",
              lambda: (rc, "README.md:2" in o), (HITS, True))
        check("⛔ ...and without --show the words appear in NEITHER stream",
              lambda: " ".join(first) in o + e, False)
        rc, o, e = drive(["--base", "HEAD~1", "--show"], p, tty=False)
        check("⭐ X11: --show REFUSES when stdout is not a terminal, and prints no words",
              lambda: (rc, " ".join(first) in o + e), (REFUSED, False))
        rc, o, e = drive(["--base", "HEAD~1", "--show"], p, tty=True)
        check("--show on a terminal prints the matched words", lambda: (rc, " ".join(first) in o), (HITS, True))
        rc, o, e = drive(["--base", "HEAD~1", "--window", "11"], p)
        check("--window is read: at 11 words no 10-word plan string can hit", lambda: rc, CLEAN)
        rc, o, e = drive(["--base", "no-such-ref"], p)
        check("by hand with a base that does not exist: CANNOT RUN (3)", lambda: rc, CANNOT)
        rc, o, e = drive(["--base", "origin/master"], td / "noplans")
        check("by hand with no plans: CANNOT RUN (2), never a pass", lambda: (rc, "NOT RUN" in o), (NO_PLANS, True))

        # the installer and --status
        check("--hooks-status: ACTIVE in an installed world", lambda: drive(["--hooks-status"], p)[0], CLEAN)
        rc, o, e = drive(["--install-hooks"], p)
        check("--install-hooks is idempotent", lambda: (rc, "already" in o), (CLEAN, True))
        fresh = td / "fresh"
        subprocess.run(["git", "init", "-q", str(fresh)], check=True)
        # The hook FILE is present first, so this case can only pass on the hooks-path check itself (the
        # sweep measured it passing on the missing-file check instead, with the hooks-path check deleted).
        (fresh / ".githooks").mkdir()
        shutil.copy2(ROOT / ".githooks" / "pre-push", fresh / ".githooks" / "pre-push")
        rc, o, e = drive(["--hooks-status"], fresh)
        check("--hooks-status: NOT ACTIVE before installing", lambda: (rc, "core.hooksPath is" in o), (HITS, True))
        rc, o, e = drive(["--install-hooks"], fresh)
        check("--install-hooks sets core.hooksPath, and --status then says ACTIVE",
              lambda: (rc, git(fresh, "config", "core.hooksPath").stdout.strip(), drive(["--hooks-status"], fresh)[0]),
              (CLEAN, HOOKS_PATH, CLEAN))
        (fresh / ".githooks" / "pre-push").unlink()
        rc, o, e = drive(["--hooks-status"], fresh)
        check("--hooks-status: NOT ACTIVE in a checkout without the hook file (an older branch)",
              lambda: (rc, "UNCHECKED" in o), (HITS, True))
        git(fresh, "config", "core.hooksPath", "elsewhere")
        rc, o, e = drive(["--install-hooks"], fresh)
        check("⛔ --install-hooks REFUSES to overwrite a different core.hooksPath",
              lambda: (rc, git(fresh, "config", "core.hooksPath").stdout.strip()), (REFUSED, "elsewhere"))
        git(fresh, "config", "--unset", "core.hooksPath")
        (fresh / ".git" / "hooks" / "pre-commit").write_text("#!/bin/sh\n")
        rc, o, e = drive(["--install-hooks"], fresh)
        check("⛔ --install-hooks REFUSES while live hooks in .git/hooks would be switched off",
              lambda: (rc, "pre-commit" in o), (REFUSED, True))

        # the SessionStart hook: enable when unset, warn LOUDLY and change nothing when pointed elsewhere
        ss = td / "ss"
        subprocess.run(["git", "init", "-q", str(ss)], check=True)
        for rel in ("scripts/check-plan-leak.py", "scripts/gen-work-lines.py", ".githooks/pre-push",
                    ".claude/hooks/ensure-plan-leak-hook.sh"):
            (ss / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, ss / rel)
        check("session_start with core.hooksPath UNSET enables the hook, quietly",
              lambda: (session_start(ss)[0], git(ss, "config", "core.hooksPath").stdout.strip(),
                       hooks_status(ss)[0]), (False, HOOKS_PATH, True))
        check("hooks_status reads the checkout it is GIVEN: the installed plain world is ACTIVE too",
              lambda: hooks_status(td / "plain")[0], True)
        check("session_start reads the checkout it is GIVEN: the installed plain world is quiet",
              lambda: session_start(td / "plain")[0], False)
        check("session_start when already ACTIVE is quiet and says so",
              lambda: (session_start(ss)[0], "ACTIVE" in session_start(ss)[1]), (False, True))
        git(ss, "config", "core.hooksPath", "/dev/null")
        check("⛔ session_start with core.hooksPath ELSEWHERE warns LOUDLY and does NOT overwrite it",
              lambda: (session_start(ss)[0], "OFF" in session_start(ss)[1],
                       git(ss, "config", "core.hooksPath").stdout.strip()), (True, True, "/dev/null"))
        r = subprocess.run(["bash", str(ss / ".claude" / "hooks" / "ensure-plan-leak-hook.sh")], cwd=ss,
                           capture_output=True, text=True)
        check("the SHIPPED SessionStart hook prints the loud warning as JSON, to the user and the model",
              lambda: (r.returncode, "OFF" in json.loads(r.stdout)["systemMessage"],
                       "OFF" in json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]), (0, True, True))
        git(ss, "config", "--unset", "core.hooksPath")
        r = subprocess.run(["bash", str(ss / ".claude" / "hooks" / "ensure-plan-leak-hook.sh")], cwd=ss,
                           capture_output=True, text=True)
        check("...and the SHIPPED hook enables the gate when the path is unset",
              lambda: (r.returncode, git(ss, "config", "core.hooksPath").stdout.strip()), (0, HOOKS_PATH))
        (ss / ".git" / "hooks" / "pre-commit").write_text("#!/bin/sh\n")
        git(ss, "config", "--unset", "core.hooksPath")
        check("session_start warns LOUDLY when the install is refused (live hooks would be switched off)",
              lambda: (session_start(ss)[0], "OFF" in session_start(ss)[1]), (True, True))
    finally:
        shutil.rmtree(td, ignore_errors=True)

    if fail:
        print(f"\n{ok} passed, {fail} FAILED")
        return 1
    print(f"\n{ok}/{ok + fail} self-test cases passed")
    return 0


def _raises(thunk) -> str:
    """The name of the exception `thunk` raises, or 'no raise'."""
    try:
        thunk()
    except Exception as exc:  # noqa: BLE001
        return type(exc).__name__
    return "no raise"


if __name__ == "__main__":
    sys.exit(_self_test() if "--self-test" in sys.argv[1:] else main(sys.argv[1:]))
