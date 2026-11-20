#!/usr/bin/env python3
"""Wake the orchestrator when a builder it spawned goes quiet (backlog #657).

    python3 scripts/agent-watchdog.py QUIET_MIN name=worktree[:transcript] [name=worktree[:transcript] ...]
    python3 scripts/agent-watchdog.py --self-test  # 79 cases

WHY THIS EXISTS. The owner, 2026-11-15: "It seems that orchestrator need to actively check progress of
subagents periodically." An orchestrator that only waits for a builder's report learns nothing from a builder
that has stalled, and asking the builder costs model tokens on both sides. This script is started as a
BACKGROUND Bash job when a builder is spawned. It polls every 60 s, spends no model tokens while it polls, and
EXITS when a builder has shown no activity for QUIET_MIN minutes. A background job that exits wakes the session
that started it, and what this prints is what the orchestrator reads on waking.

WHAT COUNTS AS ACTIVITY, for one builder: ANY CHANGE, between two polls, in the FINGERPRINT of what it observes.
The fingerprint is a hash over the name, modification time (ns) and size of
  * every file and directory in its worktree, not descending into `.git`, `node_modules` or `.next`; a symlink
    is read by `lstat`, never followed, so a looping or dangling one is an entry and not an error;
  * `HEAD`, `index` and `logs/HEAD` in the worktree's git directory (a linked worktree's `.git` is a FILE that
    names it; a main checkout's `.git` is the directory itself), so a commit or a `git add` counts;
  * the transcript, when one is given after a colon (a regular file; a builder subagent's lives at
    `~/.claude/projects/<project-slug>/<session-id>/subagents/agent-<name>-<hash>.jsonl`, known only after the
    spawn returns, so find it with `ls -t` there).
A write, a delete, a rename, a file appearing, a time moving in EITHER direction and a size change each alter it
(r2: the r1 design compared only the NEWEST time, so every write below a retained maximum, a file stamped in the
future for one, and every deletion went unseen). No modification time is ever compared with a clock. The window
restarts at the poll that saw the fingerprint change (the first poll, at arming, starts it) and is measured on
`time.monotonic`, so a step of the wall clock neither shortens nor extends it, and a worktree that was already
quiet when the watchdog started gets a full window.

OPEN QUESTION (a) OF THE ROW — a long foreground call that writes nothing. Two answers, both in the code:
  1. Such a call is BOUNDED. `scripts/check-agent-long-call.py` denies a subagent's foreground Bash call whose
     effective timeout is over 270 s, so one silent call cannot last longer than that. QUIET_MIN must therefore
     be MORE than 270 s (`LONGEST_SILENT_CALL_S`, checked against that script's own constant by a case); a
     shorter window is refused as CANNOT RUN, because it would report a builder that is inside one legal call.
     The floor is NECESSARY, not sufficient: silence also includes the model's own generation between calls (a
     long thinking turn, one large write) and waits that are not foreground Bash (a Monitor, a background job
     the builder waits on). A window just over 270 s can report a working builder; use 30, as the checklist does.
  2. A builder that READS for a long stretch (many short calls, no write) may change nothing it meant to change
     in its worktree (hooks may still write under `.claude/`, see BOUNDS). Its transcript does change on every
     turn. Give it as `name=worktree:transcript` and reading counts as progress.
     Without a transcript the watchdog sees files and git only, and its report says which signals it read.
  Bound: a path that contains a colon cannot be given (the first colon after `=` ends the worktree path).

OPEN QUESTION (b) — several builders. One watchdog takes any number of `name=...` pairs and judges each one
separately at every poll. It exits at the first poll where ANY builder is quiet, reports EVERY quiet one, lists
the ones still active with their age, and prints the command that re-arms the watchdog for those.

EXIT CODES. Watching never exits 0.
    1  at least one builder is quiet: look at it
    2  CANNOT RUN: bad arguments, a worktree that is missing, a git directory, `.git` file, worktree entry or
       transcript that cannot be read (any OSError but a file that vanished mid-walk), a `.git` that is neither a
       directory nor a regular file (decided on the OPENED descriptor, opened non-blocking, so a FIFO swapped in
       after any check cannot block the poll), and any OSError or ValueError raised while observing one builder
       (a `gitdir:` pointer holding a NUL). Treat the builder it names as NOT WATCHED; the other builders are
       still judged in the same poll. Never skipped in silence: it is checked at arming and at every poll, and a
       builder that is quiet in the same poll is still reported.

WHAT WOULD MAKE THIS FAIL (the row's falsifier): a builder worktree shows no activity for QUIET_MIN minutes
and this process is still running, or it exits without naming that builder.

BOUNDS. It observes names, modification times and sizes, never the agent or a file's content: a builder that
writes one file a minute in a loop looks active, and a rewrite that leaves a file's name, time (to the
filesystem's resolution) and size all the same is not seen. A change made and exactly undone between two polls
is not seen either. ANYTHING writing in the worktree counts, not only the builder: this repo's hooks write under
`.claude/` on every turn, a self-test writes `__pycache__`, and a review round run in a builder's worktree keeps
it active. They are not excluded, since a hook firing on the builder's own turns IS its activity. It does not
know that a builder FINISHED; a finished builder goes quiet and is reported, unless something else (a review)
then works in its worktree. An orchestrator's own `git status` there can rewrite `index` and so
restart the window once. A symlink to a DIRECTORY is not an entry (the walk lists it among directories and
does not descend): its creation or retargeting is seen only through its parent directory's time. A worktree nested inside a watched directory counts as that directory's
activity, so watch builder worktrees, not the main checkout that holds them. The wake depends on the caller
starting this as a background job; started in the foreground it blocks the caller.

NO-CALLER: the orchestrator starts this by hand as a background job each time it spawns a builder (`docs/process-checklists.md`, *Agent lifetime*); CI has no builder to watch, and the row keeps a hook in reserve if the convention lapses.
"""
from __future__ import annotations

import hashlib
import math
import os
import shlex
import stat
import sys
import time
from dataclasses import dataclass
from typing import NamedTuple

POLL_S = 60
# One silent foreground call of a subagent cannot outlast this (`check-agent-long-call.LIMIT_S`). DEFINED here,
# not imported, so a lone copy of this file still runs; a self-test case reads the sibling and refuses a drift.
LONGEST_SILENT_CALL_S = 270
# The window the checklist arms this watchdog with (`docs/process-checklists.md`, *Agent lifetime*:
# `agent-watchdog.py 30 ...`). The goal tree reads it (backlog #672), so the page's `building` / `quiet` turn at the
# same minute the watchdog would wake the orchestrator. A self-test case reads the checklist and refuses a drift.
QUIET_MIN = 30
EXCLUDED_DIRS = (".git", "node_modules", ".next")
GIT_REQUIRED = "HEAD"
GIT_OPTIONAL = ("index", "logs/HEAD")
GITFILE_MAX = 1 << 16  # a `.git` pointer file is one short line; never read more of whatever sits there
USAGE = "usage: agent-watchdog.py QUIET_MIN name=worktree[:transcript] [...]  |  --self-test"


class CannotRun(Exception):
    """The watchdog cannot observe what it was asked to watch."""


@dataclass(frozen=True)
class Watch:
    name: str
    worktree: str
    transcript: "str | None" = None

    def spec(self) -> str:
        return f"{self.name}={self.worktree}" + (f":{self.transcript}" if self.transcript else "")


def parse_args(argv: list[str]) -> "tuple[float, list[Watch]]":
    """-> (the quiet window in SECONDS, the watches). Anything it cannot read is CANNOT RUN, never a default."""
    if len(argv) < 2:
        raise CannotRun("it needs QUIET_MIN and at least one name=worktree pair")
    try:
        quiet_s = float(argv[0]) * 60
    except ValueError:
        raise CannotRun(f"QUIET_MIN {argv[0]!r} is not a number of minutes") from None
    if not math.isfinite(quiet_s):
        raise CannotRun(f"QUIET_MIN {argv[0]!r} is not a finite number of minutes")
    if quiet_s <= LONGEST_SILENT_CALL_S:
        raise CannotRun(f"QUIET_MIN {argv[0]} is {quiet_s:.0f} s, not more than the {LONGEST_SILENT_CALL_S} s one "
                        f"silent foreground call may legally last (backlog #455): it would report a working builder")
    watches: list[Watch] = []
    for pair in argv[1:]:
        name, eq, value = pair.partition("=")
        worktree, colon, transcript = value.partition(":")
        if not name or not worktree:
            raise CannotRun(f"{pair!r} is not name=worktree[:transcript]")
        if colon and not transcript:
            raise CannotRun(f"{pair!r} ends in a colon with no transcript path after it")
        if any(w.name == name for w in watches):
            raise CannotRun(f"the name {name!r} is given twice")
        watches.append(Watch(name, worktree, transcript if colon else None))
    return quiet_s, watches


def gitdir_of(worktree: str) -> str:
    """The directory that holds this worktree's HEAD and index."""
    dot = os.path.join(worktree, ".git")
    # Opened ONCE, non-blocking, and judged by the descriptor's own fstat. A path check before the open (r1) left a
    # window in which a regular file could become a FIFO, whose blocking open stalls every builder's poll (r2).
    try:
        fd = os.open(dot, os.O_RDONLY | os.O_NONBLOCK)
    except OSError as exc:
        raise CannotRun(f"{dot} cannot be opened ({exc}): {worktree} is not a git worktree") from None
    try:
        mode = os.fstat(fd).st_mode
        if stat.S_ISDIR(mode):
            return dot
        if not stat.S_ISREG(mode):
            raise CannotRun(f"{dot} is neither a directory nor a regular file: {worktree} is not a git worktree")
        text = os.read(fd, GITFILE_MAX).decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CannotRun(f"{worktree} has no readable .git ({exc}): it is not a git worktree") from None
    finally:
        os.close(fd)
    if not text.startswith("gitdir:"):
        raise CannotRun(f"{dot} does not name a git directory (no `gitdir:` line)")
    return os.path.normpath(os.path.join(worktree, text[len("gitdir:"):].strip()))


def _walk_error(exc: OSError) -> None:
    """`os.walk`'s default is to skip a directory it cannot list, in silence. A directory that VANISHED between
    two steps of the walk is ordinary (a builder deletes things); any other failure is a part of the worktree
    that was not observed."""
    if isinstance(exc, FileNotFoundError):
        return None
    raise CannotRun(f"cannot list {exc.filename}: {exc.strerror}")


class Entry(NamedTuple):
    """One observed thing. Every field has a self-test witness that changes it ALONE (r3, Phase 6): a field no
    input can change is not evidence, so the r2 `kind` field, which no two entries could differ in alone, is gone."""
    name: str
    mtime_ns: int
    size: int


def _entry(name: str, st: os.stat_result) -> Entry:
    return Entry(name, st.st_mtime_ns, st.st_size)


def observe(w: Watch) -> "list[Entry]":
    """One Entry for everything that counts as this builder's activity."""
    if not os.path.isdir(w.worktree):
        raise CannotRun(f"the worktree {w.worktree} is missing")
    gd = gitdir_of(w.worktree)
    try:
        head = os.stat(os.path.join(gd, GIT_REQUIRED))
    except OSError as exc:
        raise CannotRun(f"the git directory {gd} is unreadable ({exc})") from None
    entries = [_entry(GIT_REQUIRED, head)]
    for f in GIT_OPTIONAL:
        try:
            entries.append(_entry(f, os.stat(os.path.join(gd, f))))
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise CannotRun(f"the git file {os.path.join(gd, f)} is unreadable ({exc})") from None
    for root, dirs, files in os.walk(w.worktree, onerror=_walk_error):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for path in [root] + [os.path.join(root, f) for f in files]:
            try:
                entries.append(_entry(path, os.lstat(path)))
            except FileNotFoundError:
                continue
            except OSError as exc:
                raise CannotRun(f"cannot read {path} ({exc})") from None
    if w.transcript is not None:
        try:
            tst = os.stat(w.transcript)
        except OSError as exc:
            raise CannotRun(f"the transcript {w.transcript} is unreadable ({exc})") from None
        if not stat.S_ISREG(tst.st_mode):
            raise CannotRun(f"the transcript {w.transcript} is not a regular file")
        entries.append(_entry("", tst))
    return entries


def newest_change_ns(worktree: str) -> int:
    """backlog #672: the newest modification time (ns) of everything `observe` reads for this worktree, no transcript
    -- the watchdog's own measure read ONCE, by a page that renders once and has no earlier poll to compare with (the
    goal tree's *Running now*). It is CannotRun exactly when `observe` is: a missing worktree, an unreadable git
    directory. ⚠ Unlike `main`, its caller DOES compare this time with a clock, so a file stamped in the future reads
    as a change made now (a bound the page states); every other bound of the module docstring applies as it is."""
    return max(e.mtime_ns for e in observe(Watch("worktree", worktree)))


def fingerprint(entries: "list[Entry]") -> str:
    """One value for an observation, the same whatever order the walk listed it in. ANY difference between two
    polls' fingerprints is activity; nothing in it is ever compared with a clock."""
    return hashlib.sha256(repr(sorted(entries)).encode("utf-8", "backslashreplace")).hexdigest()


def report(wall_now: float, quiet_s: float, quiet: dict, active: dict, broken: dict, watches: "list[Watch]") -> str:
    """What the orchestrator reads on waking: every quiet builder, every unwatchable one, the rest, the re-arm."""
    lines = [f"{time.strftime('%m-%d %H:%M', time.localtime(wall_now))} AGENT WATCHDOG (backlog #657): "
             f"{len(quiet)} quiet, {len(broken)} CANNOT RUN, {len(active)} active."]
    for w in watches:
        signals = "file, git or transcript" if w.transcript else "file or git"
        if w.name in quiet:
            lines.append(f"  QUIET  {w.name}: no {signals} activity for {quiet[w.name] / 60:.0f} min "
                         f"in {w.worktree}")
        elif w.name in broken:
            lines.append(f"  CANNOT RUN {w.name}: {broken[w.name]}. Treat it as NOT WATCHED.")
        else:
            lines.append(f"  active {w.name}: last activity {active[w.name] / 60:.0f} min ago")
    rest = [shlex.quote(w.spec()) for w in watches if w.name in active]
    if rest:
        lines.append(f"  This watchdog has EXITED. To keep watching the active ones: "
                     f"python3 scripts/agent-watchdog.py {quiet_s / 60:g} {' '.join(rest)}")
    return "\n".join(lines)


def main(argv: "list[str] | None" = None, clock=time.monotonic, sleep=time.sleep, wall=time.time) -> int:
    """`clock` measures ELAPSED time and must be monotonic; `wall` only dates the report."""
    argv = sys.argv[1:] if argv is None else argv
    try:
        quiet_s, watches = parse_args(argv)
    except CannotRun as exc:
        print(f"⛔ agent-watchdog CANNOT RUN: {exc}. Nothing is being watched.\n{USAGE}", file=sys.stderr)
        return 2
    # name -> (the fingerprint last observed, the MONOTONIC clock when it last changed). The window restarts when
    # the fingerprint changes at all; no modification time is compared with any clock (r2).
    seen: dict = {}
    while True:
        now = clock()
        quiet: dict = {}
        active: dict = {}
        broken: dict = {}
        for w in watches:
            try:
                mark = fingerprint(observe(w))
            except CannotRun as exc:
                broken[w.name] = str(exc)
                continue
            except (OSError, ValueError) as exc:  # nothing observing ONE builder may end the poll for the rest (r2)
                broken[w.name] = f"observing it raised {type(exc).__name__}: {exc}"
                continue
            if w.name not in seen or seen[w.name][0] != mark:
                seen[w.name] = (mark, now)
            idle = now - seen[w.name][1]
            if idle >= quiet_s:
                quiet[w.name] = idle
            else:
                active[w.name] = idle
        if quiet or broken:
            print(report(wall(), quiet_s, quiet, active, broken, watches))
            return 2 if broken else 1
        sleep(POLL_S)


def _self_test() -> int:
    """The suite, inside `fixture_git.isolated()` (backlog #382): the repo's rule for every suite, though this one
    runs no git. Every temp directory it makes lands in the block's own scratch and is removed with it."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    import contextlib
    import io
    import re
    import shutil
    import tempfile
    ok = fail = 0

    def case(name, got, want):
        nonlocal ok, fail
        if got == want:
            ok += 1
        else:
            fail += 1
            print(f"[FAIL] {name}: got {got!r}, want {want!r}")

    class World:
        """A temp directory of worktree-shaped dirs and two FAKE clocks. `sleep` advances both and runs what the
        case scheduled for that minute; nothing here waits. `t` is the wall clock (it stamps files and dates the
        report) and starts in 2096; `mono` is the elapsed-time clock and starts at 1000, so the two can never be
        mistaken for each other."""

        def __init__(self):
            self.root = tempfile.mkdtemp(prefix="watchdog-")
            self.t = self.t0 = 4_000_000_000.0
            self.mono = 1000.0
            self.sleeps: list = []
            self.at: dict = {}
            self.every: list = []
            self.clock_calls = 0

        def stamp(self, path, when=None):
            when = self.t if when is None else when
            if not os.path.lexists(path):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w") as fh:
                    fh.write("x")
            os.utime(path, (when, when))
            return path

        def wt(self, name, linked=True, relative=False):
            """A worktree `name` with one source file, and its git directory. Everything a day old."""
            w = os.path.join(self.root, name)
            gd = os.path.join(self.root, "gitdirs", name) if linked else os.path.join(w, ".git")
            old = self.t0 - 86400
            for f in ("HEAD", "index", "logs/HEAD"):
                self.stamp(os.path.join(gd, f), old)
            self.stamp(os.path.join(w, "src", "a.py"), old)
            if linked:
                pointer = os.path.relpath(gd, w) if relative else gd
                with open(os.path.join(w, ".git"), "w") as fh:
                    fh.write(f"gitdir: {pointer}\n")
            for d in (w, os.path.join(w, "src"), os.path.join(w, ".git")):
                os.utime(d, (old, old))
            return w, gd

        def clock(self):
            self.clock_calls += 1
            if self.clock_calls > 2000:
                raise RuntimeError("the clock was read 2000 times: the loop is not sleeping")
            return self.mono

        def sleep(self, s):
            self.sleeps.append(s)
            if len(self.sleeps) > 200:
                raise RuntimeError("slept 200 times and never exited")
            self.t += s
            self.mono += s
            for fn in self.at.pop(len(self.sleeps), []) + self.every:
                fn()

        def on(self, minute, fn):
            self.at.setdefault(minute, []).append(fn)

        def run(self, *argv):
            """-> (exit code, minutes polled, stdout, stderr); a raise is returned as the exit code."""
            out, err = io.StringIO(), io.StringIO()
            try:
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    rc = main(list(argv), clock=self.clock, sleep=self.sleep, wall=lambda: self.t)
            except Exception as exc:  # noqa: BLE001 - the raise IS the observation
                rc = f"raised {type(exc).__name__}: {exc}"
            return rc, len(self.sleeps), out.getvalue(), err.getvalue()

    def refused(fn, *a):
        """-> the result, a `CANNOT RUN: ...` string, or `raised ...` for any OTHER exception (never a refusal)."""
        try:
            return fn(*a)
        except CannotRun as exc:
            return f"CANNOT RUN: {exc}"
        except Exception as exc:  # noqa: BLE001 - an escape IS the observation (r1 F3)
            return f"raised {type(exc).__name__}: {exc}"

    def is_refusal(v):
        return isinstance(v, str) and v.startswith("CANNOT RUN: ")

    # --- the arguments -------------------------------------------------------------------------------------
    case("arguments: QUIET_MIN is minutes, and name=worktree is one watch with no transcript",
         refused(parse_args, ["10", "a=/w/a"]), (600.0, [Watch("a", "/w/a", None)]))
    case("arguments: name=worktree:transcript carries the transcript",
         refused(parse_args, ["10", "a=/w/a:/t/a.jsonl"]), (600.0, [Watch("a", "/w/a", "/t/a.jsonl")]))
    case("arguments: several pairs are several watches, in order",
         refused(parse_args, ["30", "a=/w/a", "b=/w/b:/t/b"]),
         (1800.0, [Watch("a", "/w/a", None), Watch("b", "/w/b", "/t/b")]))
    case("arguments: no QUIET_MIN and no pair is CANNOT RUN", is_refusal(refused(parse_args, [])), True)
    case("arguments: a QUIET_MIN with no pair is CANNOT RUN", is_refusal(refused(parse_args, ["10"])), True)
    case("arguments: a QUIET_MIN that is not a number is CANNOT RUN",
         is_refusal(refused(parse_args, ["soon", "a=/w/a"])), True)
    case("arguments: a QUIET_MIN that is not finite is CANNOT RUN",
         [is_refusal(refused(parse_args, [q, "a=/w/a"])) for q in ("nan", "inf")], [True, True])
    case("arguments: a window of exactly 270 s is refused, one silent legal call would trip it",
         is_refusal(refused(parse_args, ["4.5", "a=/w/a"])), True)
    case("arguments: a window just over 270 s is accepted",
         refused(parse_args, ["4.6", "a=/w/a"]), (4.6 * 60, [Watch("a", "/w/a", None)]))
    case("arguments: a pair with no = is CANNOT RUN", is_refusal(refused(parse_args, ["10", "/w/a"])), True)
    case("arguments: an empty name is CANNOT RUN", is_refusal(refused(parse_args, ["10", "=/w/a"])), True)
    case("arguments: an empty worktree path is CANNOT RUN",
         [is_refusal(refused(parse_args, ["10", s])) for s in ("a=", "a=:/t/a")], [True, True])
    case("arguments: an empty transcript after the colon is CANNOT RUN",
         is_refusal(refused(parse_args, ["10", "a=/w/a:"])), True)
    case("arguments: the same name twice is CANNOT RUN",
         is_refusal(refused(parse_args, ["10", "a=/w/a", "a=/w/b"])), True)
    _here = os.path.dirname(os.path.abspath(__file__))
    try:
        with open(os.path.join(_here, "check-agent-long-call.py"), encoding="utf-8") as fh:
            _m = re.search(r"^LIMIT_S = (\d+)$", fh.read(), re.M)
        _limit = int(_m.group(1)) if _m else "no `LIMIT_S = <int>` line"
    except OSError as exc:
        _limit = f"unreadable: {exc}"
    case("the silent-call bound equals check-agent-long-call's LIMIT_S", LONGEST_SILENT_CALL_S, _limit)
    try:
        with open(os.path.join(_here, os.pardir, "docs", "process-checklists.md"), encoding="utf-8") as fh:
            _armed = sorted(set(re.findall(r"agent-watchdog\.py (\d+) ", fh.read())))
    except OSError as exc:
        _armed = f"unreadable: {exc}"
    case("backlog #672: QUIET_MIN is the window the checklist arms the watchdog with", _armed, [str(QUIET_MIN)])

    # --- backlog #672: the measure read ONCE, for a page that renders once (the goal tree) -------------------
    w = World()
    wn, gn = w.wt("n")
    _newest = []
    for file_at, head_at in ((w.t0 - 60, w.t0 - 600), (w.t0 - 900, w.t0 - 120)):
        w.stamp(os.path.join(wn, "src", "a.py"), file_at)
        w.stamp(os.path.join(gn, "HEAD"), head_at)
        _newest.append(refused(newest_change_ns, wn))
    case("⭐ backlog #672: newest_change_ns is the NEWEST time among everything `observe` reads -- a file newer than "
         "HEAD, then a commit (HEAD) newer than the file, in ONE case",
         _newest, [int(w.t0 - 60) * 10**9, int(w.t0 - 120) * 10**9])
    case("backlog #672: newest_change_ns of a missing worktree is CANNOT RUN, never a time",
         is_refusal(refused(newest_change_ns, os.path.join(w.root, "gone"))), True)

    # --- the git directory ---------------------------------------------------------------------------------
    w = World()
    wa, ga = w.wt("a")
    case("git directory: a linked worktree's .git FILE names it", refused(gitdir_of, wa), ga)
    wr, gr = w.wt("r", relative=True)
    case("git directory: a relative gitdir is resolved against the worktree", refused(gitdir_of, wr), gr)
    wm, gm = w.wt("m", linked=False)
    case("git directory: a .git DIRECTORY is the git directory", refused(gitdir_of, wm), gm)
    bare = os.path.join(w.root, "bare")
    os.makedirs(bare)
    case("git directory: a directory with no .git is CANNOT RUN", is_refusal(refused(gitdir_of, bare)), True)
    with open(os.path.join(bare, ".git"), "w") as fh:
        fh.write("not a pointer\n")
    case("git directory: a .git file that names no gitdir is CANNOT RUN", is_refusal(refused(gitdir_of, bare)), True)

    # --- what counts as activity (each case changes ONE thing between two observations) -------------------------
    def changed(act, setup=lambda w, wt, gd, tr: None, transcript=False, linked=True):
        """-> does the fingerprint differ after `act`? (or the refusal / the raise, as a string)"""
        w = World()
        wt, gd = w.wt("a", linked=linked)
        tr = w.stamp(os.path.join(w.root, "a.jsonl"), w.t0 - 86400)
        watch = Watch("a", wt, tr if transcript else None)
        setup(w, wt, gd, tr)
        before = refused(observe, watch)
        act(w, wt, gd, tr)
        after = refused(observe, watch)
        if isinstance(before, str) or isinstance(after, str):
            return before, after
        return fingerprint(after) != fingerprint(before)

    case("activity: with nothing touched two observations have the same fingerprint",
         changed(lambda w, wt, gd, tr: None), False)
    case("activity: an existing file deep in the worktree, rewritten, counts (no directory changes with it)",
         changed(lambda w, wt, gd, tr: w.stamp(os.path.join(wt, "lib", "x", "y.ts"), w.t0 + 5),
                 setup=lambda w, wt, gd, tr: w.stamp(os.path.join(wt, "lib", "x", "y.ts"), w.t0 - 86400)), True)
    case("activity: a NEW file deep in the worktree counts",
         changed(lambda w, wt, gd, tr: w.stamp(os.path.join(wt, "lib", "x", "z.ts"), w.t0 + 5)), True)
    case("activity: a directory's own time counts",
         changed(lambda w, wt, gd, tr: os.utime(os.path.join(wt, "src"), (w.t0 + 6, w.t0 + 6))), True)
    case("activity: the worktree root's own time counts",
         changed(lambda w, wt, gd, tr: os.utime(wt, (w.t0 + 7, w.t0 + 7))), True)
    case("activity: the git HEAD, index and logs/HEAD each count",
         [changed(lambda w, wt, gd, tr, f=f: w.stamp(os.path.join(gd, f), w.t0 + 8))
          for f in ("HEAD", "index", "logs/HEAD")], [True, True, True])
    case("activity: node_modules and .next, at any depth, do not count",
         [changed(lambda w, wt, gd, tr, d=d: w.stamp(os.path.join(wt, d, "f"), w.t0 + 9),
                  setup=lambda w, wt, gd, tr, d=d: w.stamp(os.path.join(wt, d, "f"), w.t0 - 86400))
          for d in ("node_modules", ".next", "lib/node_modules")], [False] * 3)
    case("activity: a .git directory's objects do not count, only its HEAD, index and logs/HEAD",
         changed(lambda w, wt, gd, tr: w.stamp(os.path.join(gd, "objects", "ab", "f"), w.t0 + 9),
                 setup=lambda w, wt, gd, tr: w.stamp(os.path.join(gd, "objects", "ab", "f"), w.t0 - 86400),
                 linked=False), False)
    case("activity: the transcript counts when given, and is not read when it is not",
         (changed(lambda w, wt, gd, tr: w.stamp(tr, w.t0 + 3), transcript=True),
          changed(lambda w, wt, gd, tr: w.stamp(tr, w.t0 + 3))), (True, False))
    case("activity: a missing index does not hide a fresh logs/HEAD (the loop goes on past it)",
         changed(lambda w, wt, gd, tr: w.stamp(os.path.join(gd, "logs", "HEAD"), w.t0 + 8),
                 setup=lambda w, wt, gd, tr: os.remove(os.path.join(gd, "index"))), True)
    case("activity: an index or logs/HEAD that goes missing is not an error, and is itself a change",
         changed(lambda w, wt, gd, tr: (os.remove(os.path.join(gd, "index")),
                                        shutil.rmtree(os.path.join(gd, "logs")))), True)
    _e1, _e2 = Entry("/w/a", 1, 2), Entry("/w/b", 3, 4)
    case("fingerprint: the same entries in another order are the same observation, and one fewer is not",
         (fingerprint([_e1, _e2]) == fingerprint([_e2, _e1]), fingerprint([_e1, _e2]) == fingerprint([_e1])),
         (True, False))

    # --- r3 (Phase 6): EVERY field of an entry has a witness that changes that field ALONE -------------------
    # The class case, not one case per field written as it occurs to someone (R3m1: the name had none). FIELDS is
    # an INDEPENDENT literal, never read from the code: a field added to `Entry` with no witness here is red.
    FIELDS = ("name", "mtime_ns", "size")

    def field_world():
        """A worktree holding, in EACH of `src` and `lib`, two files `p` and `q` of different (time, size)."""
        w = World()
        wt, _ = w.wt("a")
        for d, (n1, n2) in (("src", (1, 2)), ("lib", (2, 1))):
            for f, n in (("p", n1), ("q", n2)):
                p = os.path.join(wt, d, f)
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with open(p, "w") as fh:
                    fh.write("x" * n)
                os.utime(p, ns=(n, n))
        return wt

    def times_put_back(paths, fn):
        sts = {p: os.lstat(p) for p in paths}
        fn()
        for p, st in sts.items():
            os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))

    def only_name(wt):
        """In both directories `p` and `q` exchange names, directory times put back: the basenames, the
        directories and the (time, size) pairs are each the same set before and after; only which FULL path
        carries which (time, size) changes."""
        def swap():
            for d in ("src", "lib"):
                base = os.path.join(wt, d)
                os.rename(os.path.join(base, "p"), os.path.join(base, "t"))
                os.rename(os.path.join(base, "q"), os.path.join(base, "p"))
                os.rename(os.path.join(base, "t"), os.path.join(base, "q"))
        times_put_back([os.path.join(wt, "src"), os.path.join(wt, "lib")], swap)

    def only_time(wt):
        os.utime(os.path.join(wt, "src", "a.py"), ns=(1, 1))

    def only_size(wt):
        f = os.path.join(wt, "src", "a.py")

        def grow():
            with open(f, "a") as fh:
                fh.write("more")
        times_put_back([f], grow)

    def field_witnesses():
        declared = getattr(globals().get("Entry"), "_fields", None)
        got: dict = {"declared fields": declared}
        for field, act in (("name", only_name), ("mtime_ns", only_time), ("size", only_size),
                           ("identity", lambda wt: None)):
            if declared != FIELDS:
                got[field] = "no Entry whose fields are exactly the literal"
                continue
            watch = Watch("a", field_world())
            before = refused(observe, watch)
            act(watch.worktree)
            after = refused(observe, watch)
            if isinstance(before, str) or isinstance(after, str):
                got[field] = (before, after)
                continue
            i = FIELDS.index(field) if field in FIELDS else None

            def without(es):
                return sorted(tuple(v for j, v in enumerate(e) if j != i) for e in es)
            # CONTROL: the fixture changed this field and nothing else (equal with it projected out, different
            # with it in). PROPERTY: the fingerprint saw it. The identity row: nothing changed, nothing seen.
            control = without(before) == without(after) and (i is None or sorted(before) != sorted(after))
            got[field] = (control, fingerprint(before) != fingerprint(after))
        return got

    case("activity: every field of an entry, changed ALONE, changes the fingerprint, and nothing changed does not",
         field_witnesses(), {"declared fields": FIELDS, "name": (True, True), "mtime_ns": (True, True),
                             "size": (True, True), "identity": (True, False)})

    def links_observed():
        """R3m2: a looping and a dangling symlink inside the worktree are each observed (by `lstat`, never followed)
        and each an entry. A symlink to a DIRECTORY is not an entry: the walk lists it among directories and does
        not descend, so it is seen only through its parent's time (BOUNDS)."""
        w = World()
        wt, _ = w.wt("a")
        os.makedirs(os.path.join(w.root, "elsewhere"))
        src = os.path.join(wt, "src")
        os.symlink("loop", os.path.join(src, "loop"))
        os.symlink("nowhere", os.path.join(src, "dangling"))
        os.symlink(os.path.join(w.root, "elsewhere"), os.path.join(src, "dirlink"))
        got = refused(observe, Watch("a", wt))
        if isinstance(got, str):
            return got
        names = {getattr(e, "name", None) for e in got}
        return tuple(os.path.join(src, n) in names for n in ("loop", "dangling", "dirlink"))

    case("activity: a looping and a dangling symlink in the worktree are observed without CANNOT RUN and are each "
         "an entry; a symlink to a directory is not", links_observed(), (True, True, False))

    def newest_refusal(make):
        w = World()
        wt, gd = w.wt("a")
        return refused(observe, make(w, wt, gd))

    case("CANNOT RUN: a worktree that does not exist",
         is_refusal(newest_refusal(lambda w, wt, gd: Watch("a", wt + "-gone"))), True)
    case("CANNOT RUN: a git directory with no HEAD",
         is_refusal(newest_refusal(lambda w, wt, gd: (os.remove(os.path.join(gd, "HEAD")), Watch("a", wt))[1])),
         True)
    case("CANNOT RUN: a transcript that does not exist",
         is_refusal(newest_refusal(lambda w, wt, gd: Watch("a", wt, os.path.join(w.root, "none.jsonl")))), True)
    case("CANNOT RUN: a directory the walk cannot list, but one that vanished mid-walk is skipped",
         (is_refusal(refused(_walk_error, PermissionError(13, "denied", "/w/a/x"))),
          refused(_walk_error, FileNotFoundError(2, "gone", "/w/a/x"))), (True, None))

    def git_file_refusal(break_it):
        w = World()
        wt, gd = w.wt("a")
        break_it(gd)
        return is_refusal(refused(observe, Watch("a", wt)))

    def loop_index(gd):
        os.remove(os.path.join(gd, "index"))
        os.symlink("index", os.path.join(gd, "index"))

    def logs_a_file(gd):
        shutil.rmtree(os.path.join(gd, "logs"))
        with open(os.path.join(gd, "logs"), "w") as fh:
            fh.write("x")

    case("CANNOT RUN: an index that is a symlink loop, and a logs that is a FILE (any OSError, not only a missing "
         "file)", (git_file_refusal(loop_index), git_file_refusal(logs_a_file)), (True, True))

    def unreadable_dir(mode):
        """A worktree with a subdirectory of `mode`, read through the REAL walk; the mode is restored after."""
        if os.geteuid() == 0:
            return "CANNOT RUN this case: running as root, where chmod does not deny"
        w = World()
        wt, _ = w.wt("a")
        locked = os.path.join(wt, "locked")
        w.stamp(os.path.join(locked, "f"), w.t0 - 86400)
        os.chmod(locked, mode)
        try:
            return is_refusal(refused(observe, Watch("a", wt)))
        finally:
            os.chmod(locked, 0o755)

    case("CANNOT RUN: a directory the walk cannot LIST (mode 000), through observe() and the real walk",
         unreadable_dir(0o000), True)
    case("CANNOT RUN: a directory that lists but cannot be SEARCHED (mode r--), its child unreadable",
         unreadable_dir(0o444), True)
    w = World()
    wa, _ = w.wt("a")
    os.makedirs(os.path.join(w.root, "tdir"))
    case("CANNOT RUN: a transcript that is a DIRECTORY is not a transcript",
         is_refusal(refused(observe, Watch("a", wa, os.path.join(w.root, "tdir")))), True)

    def fifo_git():
        """A FIFO named `.git` with no writer: opening it to read would block forever. Run in a thread with a 5 s
        bound; on a timeout the case unblocks the reader itself, so a regression fails here and never hangs."""
        import threading
        w = World()
        b = os.path.join(w.root, "fifo")
        os.makedirs(b)
        os.mkfifo(os.path.join(b, ".git"))
        got: list = []
        t = threading.Thread(target=lambda: got.append(refused(gitdir_of, b)), daemon=True)
        t.start()
        t.join(5)
        if t.is_alive():
            fd = os.open(os.path.join(b, ".git"), os.O_WRONLY | os.O_NONBLOCK)
            os.close(fd)
            t.join(5)
            return "BLOCKED: gitdir_of opened a FIFO .git and waited for a writer"
        return is_refusal(got[0])

    case("CANNOT RUN: a .git that is a FIFO is refused without opening it (it would block)", fifo_git(), True)
    w = World()
    bad = os.path.join(w.root, "badutf")
    os.makedirs(bad)
    with open(os.path.join(bad, ".git"), "wb") as fh:
        fh.write(b"gitdir: \xff\xfe\n")
    case("CANNOT RUN: a .git file that is not UTF-8", is_refusal(refused(gitdir_of, bad)), True)

    # --- the watch loop, on the fake clock --------------------------------------------------------------------
    w = World()
    wa, ga = w.wt("a")
    w.stamp(os.path.join(wa, "src", "a.py"))          # written at the arming moment
    rc, minutes, out, err = w.run("10", f"a={wa}")
    case("a builder quiet for 10 minutes wakes the orchestrator at minute 10, exit 1, named QUIET",
         (rc, minutes, "QUIET  a:" in out), (1, 10, True))
    case("every wait between polls is 60 s", set(w.sleeps), {60})
    case("the report says how long and which signals it read",
         ("for 10 min" in out, "no file or git activity" in out, "transcript" in out), (True, True, False))

    w = World()
    wa, ga = w.wt("a")
    case("a worktree already quiet for a day gets a full window from arming", w.run("10", f"a={wa}")[:2], (1, 10))

    w = World()
    wa, ga = w.wt("a")
    w.stamp(os.path.join(wa, "src", "future.json"), w.t0 + 365 * 86400)
    case("a file stamped a YEAR in the future does not keep a builder active: woken at minute 10",
         w.run("10", f"a={wa}")[:2], (1, 10))

    w = World()
    wa, ga = w.wt("a")
    w.on(4, lambda: w.stamp(os.path.join(wa, "src", "b.py")))
    case("a file written at minute 4 restarts the window: woken at minute 14", w.run("10", f"a={wa}")[:2], (1, 14))

    w = World()
    wa, ga = w.wt("a")
    w.on(4, lambda: w.stamp(os.path.join(ga, "index")))
    case("git activity alone (the index, minute 4) restarts the window", w.run("10", f"a={wa}")[:2], (1, 14))

    w = World()
    wm, gm = w.wt("m", linked=False)
    w.on(4, lambda: w.stamp(os.path.join(gm, "logs", "HEAD")))
    case("a main-checkout-shaped worktree (.git directory) is watched the same way",
         w.run("10", f"m={wm}")[:2], (1, 14))

    def with_transcript(given):
        w = World()
        wa, ga = w.wt("a")
        tr = w.stamp(os.path.join(w.root, "a.jsonl"), w.t0 - 86400)
        w.on(4, lambda: w.stamp(tr))
        rc, minutes, out, _ = w.run("10", f"a={wa}:{tr}" if given else f"a={wa}")
        return rc, minutes, "no file, git or transcript activity" in out

    case("a builder that only READS: transcript activity at minute 4 restarts the window when it is given, "
         "and is invisible when it is not", (with_transcript(True), with_transcript(False)),
         ((1, 14, True), (1, 10, False)))

    def two(first_active, second_active):
        w = World()
        wa, _ = w.wt("a")
        wb, _ = w.wt("b")
        if first_active:
            w.every.append(lambda: w.stamp(os.path.join(wa, "src", "a.py")))
        if second_active:
            w.every.append(lambda: w.stamp(os.path.join(wb, "src", "a.py")))
        rc, minutes, out, _ = w.run("10", f"a={wa}", f"b={wb}")
        rearm = [l for l in out.split("\n") if "agent-watchdog.py" in l]
        return (rc, minutes, "QUIET  a:" in out, "QUIET  b:" in out, "active a:" in out, "active b:" in out,
                [(f"a={wa}" in l, f"b={wb}" in l) for l in rearm])

    case("two builders, the first quiet: it is reported, the second is listed active with its re-arm command",
         two(False, True), (1, 10, True, False, False, True, [(False, True)]))
    case("two builders, the SECOND quiet: it is reported, the first is listed active with its re-arm command",
         two(True, False), (1, 10, False, True, True, False, [(True, False)]))
    case("two builders quiet in the same poll are BOTH reported, and there is nothing to re-arm",
         two(False, False), (1, 10, True, True, False, False, []))

    w = World()
    wa, _ = w.wt("a")
    wb, _ = w.wt("b")
    w.every.append(lambda: w.stamp(os.path.join(wb, "src", "a.py")))
    tr = w.stamp(os.path.join(w.root, "b.jsonl"), w.t0 - 86400)
    rc, minutes, out, _ = w.run("10", f"a={wa}", f"b={wb}:{tr}")
    case("the re-arm command keeps the quiet window and the transcript, and the active builder's age is in minutes",
         (f"agent-watchdog.py 10 b={wb}:{tr}" in out, "active b: last activity 0 min ago" in out), (True, True))

    def rearm_round_trip(out):
        """R3m3: the printed re-arm command, split as a shell splits it, gives back the same watches, even for a
        path holding a space and a quote."""
        import shlex
        line = [l for l in out.split("\n") if "agent-watchdog.py" in l]
        if len(line) != 1:
            return f"{len(line)} re-arm lines"
        try:
            argv = shlex.split(line[0].split(": ", 1)[1])
        except ValueError as exc:
            return f"the shell cannot split it: {exc}"
        return argv[:2], refused(parse_args, argv[2:])

    _spaced = Watch("b", "/w/My Worktrees/b'657", "/t/t one.jsonl")
    _dollar = Watch("c", "/w/$HOME and `x`")
    case("the re-arm command is shell-quoted: split as a shell splits it, a path with a space gives the same watch",
         (rearm_round_trip(report(0, 1800, {"a": 1800}, {"b": 60}, {}, [Watch("a", "/tmp/x"), _spaced])),
          rearm_round_trip(report(86400, 600, {"a": 600}, {"b": 60, "c": 120}, {"d": "gone"},
                                  [_dollar, Watch("a", "/tmp/y"), _spaced, Watch("d", "/tmp/d")]))),
         ((["python3", "scripts/agent-watchdog.py"], (1800.0, [_spaced])),
          (["python3", "scripts/agent-watchdog.py"], (600.0, [_dollar, _spaced]))))

    w = World()
    wa, _ = w.wt("a")
    rc, minutes, out, err = w.run("10", f"a={wa}", f"gone={os.path.join(w.root, 'gone')}")
    case("a worktree missing at arming is CANNOT RUN at once: exit 2, no poll, the builder named",
         (rc, minutes, "CANNOT RUN gone:" in out, "NOT WATCHED" in out), (2, 0, True, True))

    w = World()
    wa, _ = w.wt("a")
    wb, _ = w.wt("b")
    w.every.append(lambda: w.stamp(os.path.join(wa, "src", "a.py")))
    w.on(3, lambda: shutil.rmtree(wb))
    rc, minutes, out, err = w.run("10", f"a={wa}", f"b={wb}")
    case("a worktree removed at minute 3 is CANNOT RUN at that poll, and the other is listed active",
         (rc, minutes, "CANNOT RUN b:" in out, "active a:" in out, "QUIET" in out), (2, 3, True, True, False))

    w = World()
    wa, _ = w.wt("a")
    wb, gb = w.wt("b")
    w.on(10, lambda: os.remove(os.path.join(gb, "HEAD")))
    rc, minutes, out, err = w.run("10", f"a={wa}", f"b={wb}")
    case("a quiet builder and an unreadable one in the same poll are BOTH reported, exit 2",
         (rc, minutes, "QUIET  a:" in out, "CANNOT RUN b:" in out), (2, 10, True, True))

    w = World()
    wa, _ = w.wt("a")
    wb, gb = w.wt("b")
    loop_index(gb)
    rc, minutes, out, err = w.run("10", f"a={wa}", f"b={wb}")
    case("a git file that raises a non-missing OSError is CANNOT RUN for THAT builder, and the other is still judged",
         (rc, minutes, "CANNOT RUN b:" in out, "active a:" in out), (2, 0, True, True))

    # --- r2: ANY change is activity, whatever the retained maximum; elapsed time is monotonic ------------------
    def below_a_future_stamp(change):
        """A file stamped a year ahead stays put; `change(w, wa)` then runs at the minutes it schedules. The r1
        design compared only the NEWEST time, so nothing below that stamp was ever seen."""
        w = World()
        wa, _ = w.wt("a")
        w.stamp(os.path.join(wa, "src", "future.json"), w.t0 + 365 * 86400)
        change(w, wa)
        return w.run("10", f"a={wa}")[:2]

    def writes_until_7(w, wa):
        for minute in range(1, 8):
            w.on(minute, lambda: w.stamp(os.path.join(wa, "src", "b.py")))

    case("ordinary writes BELOW a retained future stamp are activity: written each minute to 7, woken at minute 17",
         below_a_future_stamp(writes_until_7), (1, 17))

    def older_at_4(w, wa):
        w.on(4, lambda: w.stamp(os.path.join(wa, "src", "a.py"), w.t0 - 2 * 86400))

    case("a file whose time moves BACKWARDS at minute 4 is activity: woken at minute 14",
         below_a_future_stamp(older_at_4), (1, 14))

    def put_back(d, fn):
        """Run `fn`, then give directory `d` its old times back: the change must be seen in the entry itself."""
        st = os.stat(d)
        fn()
        os.utime(d, ns=(st.st_atime_ns, st.st_mtime_ns))

    def delete_at_4(w, wa):
        src = os.path.join(wa, "src")
        w.stamp(os.path.join(src, "gone.py"), w.t0 - 86400)
        os.utime(src, (w.t0 - 86400,) * 2)
        w.on(4, lambda: put_back(src, lambda: os.remove(os.path.join(src, "gone.py"))))

    case("a DELETION at minute 4 is activity even with its directory's time put back: woken at minute 14",
         below_a_future_stamp(delete_at_4), (1, 14))

    def grow_at_4(w, wa):
        f = os.path.join(wa, "src", "a.py")

        def grow():
            st = os.stat(f)
            with open(f, "a") as fh:
                fh.write("more")
            os.utime(f, ns=(st.st_atime_ns, st.st_mtime_ns))
        w.on(4, grow)

    case("a file that changes SIZE at minute 4 with its time put back is activity: woken at minute 14",
         below_a_future_stamp(grow_at_4), (1, 14))

    import inspect
    case("the DEFAULT clock is time.monotonic (a wall-clock step neither shortens nor extends the window), and the "
         "default sleep is time.sleep",
         (inspect.signature(main).parameters["clock"].default is time.monotonic,
          inspect.signature(main).parameters["sleep"].default is time.sleep), (True, True))

    def wall_step(seconds):
        w = World()
        wa, _ = w.wt("a")
        w.on(1, lambda: setattr(w, "t", w.t + seconds))
        rc, minutes, out, _ = w.run("10", f"a={wa}")
        return rc, minutes, "for 10 min" in out

    case("a wall clock that steps an HOUR forward or back at minute 1 changes nothing: woken at minute 10, "
         "10 min quiet", (wall_step(3600), wall_step(-3600)), ((1, 10, True), (1, 10, True)))
    w = World()
    wa, _ = w.wt("a")
    rc, minutes, out, _ = w.run("10", f"a={wa}")
    case("the report is DATED by the wall clock, not by the elapsed-time clock",
         out.split(" AGENT WATCHDOG")[0], time.strftime("%m-%d %H:%M", time.localtime(w.t0 + 600)))

    def walk_raises():
        """`os.walk` itself raises an OSError for builder b: a failure no rule in observe() anticipated."""
        w = World()
        wa, _ = w.wt("a")
        wb, _ = w.wt("b")
        real = os.walk

        def walk(top, **kw):
            if top == wb:
                raise PermissionError(13, "staged", top)
            return real(top, **kw)
        os.walk = walk
        try:
            rc, minutes, out, _ = w.run("10", f"b={wb}", f"a={wa}")
        finally:
            os.walk = real
        return rc, minutes, "CANNOT RUN b:" in out, "active a:" in out

    case("an OSError that no rule anticipated, raised while observing one builder, is CANNOT RUN for THAT builder "
         "and the one after it is still judged", walk_raises(), (2, 0, True, True))

    w = World()
    wa, _ = w.wt("a")
    wb, _ = w.wt("b")
    with open(os.path.join(wb, ".git"), "wb") as fh:
        fh.write(b"gitdir: bad\x00path\n")
    rc, minutes, out, err = w.run("10", f"b={wb}", f"a={wa}")
    case("a gitdir pointer with an embedded NUL (a ValueError, not an OSError) is CANNOT RUN for THAT builder, and "
         "the one after it is still judged", (rc, minutes, "CANNOT RUN b:" in out, "active a:" in out),
         (2, 0, True, True))

    def fifo_after_check():
        """The race of r2: `.git` was a regular file when a path check looked, and is a FIFO when it is opened.
        Staged by making every PATH check answer "regular file, not a directory"; only the opened descriptor's
        own fstat can then tell. Bounded like the case above."""
        import threading
        w = World()
        b = os.path.join(w.root, "race")
        os.makedirs(b)
        os.mkfifo(os.path.join(b, ".git"))
        real = os.path.isfile, os.path.isdir
        os.path.isfile, os.path.isdir = (lambda p: True), (lambda p: False)
        try:
            got: list = []
            t = threading.Thread(target=lambda: got.append(refused(gitdir_of, b)), daemon=True)
            t.start()
            t.join(5)
            if t.is_alive():
                os.close(os.open(os.path.join(b, ".git"), os.O_WRONLY | os.O_NONBLOCK))
                t.join(5)
                return "BLOCKED: gitdir_of trusted a path check and opened a FIFO .git"
            return is_refusal(got[0])
        finally:
            os.path.isfile, os.path.isdir = real

    case("CANNOT RUN: a .git that became a FIFO AFTER a path check is refused from the descriptor, not blocked on",
         fifo_after_check(), True)

    def fifo_with_a_pointer():
        """A FIFO `.git` that DOES deliver a valid `gitdir:` line (the case holds it open for writing): still
        refused, since what the descriptor is decides, never what it happens to deliver."""
        import threading
        w = World()
        _, ga = w.wt("a")
        b = os.path.join(w.root, "fed")
        os.makedirs(b)
        os.mkfifo(os.path.join(b, ".git"))
        fd = os.open(os.path.join(b, ".git"), os.O_RDWR | os.O_NONBLOCK)
        try:
            os.write(fd, f"gitdir: {ga}\n".encode())
            real = os.path.isfile, os.path.isdir
            os.path.isfile, os.path.isdir = (lambda p: True), (lambda p: False)
            try:
                got: list = []
                t = threading.Thread(target=lambda: got.append(refused(gitdir_of, b)), daemon=True)
                t.start()
                t.join(5)
                if t.is_alive():
                    os.close(fd)        # the last writer gone: the blocked read sees end-of-file and returns
                    fd = None
                    t.join(5)
                    return "BLOCKED: gitdir_of read a FIFO .git to its end"
                return got[0] if got[0] == ga else is_refusal(got[0])
            finally:
                os.path.isfile, os.path.isdir = real
        finally:
            if fd is not None:
                os.close(fd)

    case("CANNOT RUN: a FIFO .git that delivers a valid gitdir line is still refused", fifo_with_a_pointer(), True)

    w = World()
    rc, minutes, out, err = w.run("10")
    case("main: bad arguments are CANNOT RUN on stderr with the usage, exit 2, nothing polled",
         (rc, minutes, out, "CANNOT RUN" in err, "usage:" in err), (2, 0, "", True, True))

    def never(*_a):
        raise RuntimeError("a clock was read or a poll slept")

    with contextlib.redirect_stderr(io.StringIO()):
        try:
            rc = main(["10", "/w/a"], clock=never, sleep=never, wall=never)
        except RuntimeError as exc:
            rc = f"raised: {exc}"
    case("main: bad arguments are refused before either clock is read or anything sleeps", rc, 2)
    rc, minutes, out, err = World().run("4", "a=/w/a")
    case("main: a window under the silent-call bound never starts watching",
         (rc, minutes, "270" in err), (2, 0, True))

    print(f"\n{ok}/{ok + fail} self-test cases passed")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(_self_test() if "--self-test" in sys.argv else main())
