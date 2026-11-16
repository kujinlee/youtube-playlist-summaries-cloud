#!/usr/bin/env python3
"""Wake the orchestrator when a builder it spawned goes quiet (backlog #657).

    python3 scripts/agent-watchdog.py QUIET_MIN name=worktree[:transcript] [name=worktree[:transcript] ...]
    python3 scripts/agent-watchdog.py --self-test  # 51 cases

WHY THIS EXISTS. The owner, 2026-11-15: "It seems that orchestrator need to actively check progress of
subagents periodically." An orchestrator that only waits for a builder's report learns nothing from a builder
that has stalled, and asking the builder costs model tokens on both sides. This script is started as a
BACKGROUND Bash job when a builder is spawned. It polls every 60 s, spends no model tokens while it polls, and
EXITS when a builder has shown no activity for QUIET_MIN minutes. A background job that exits wakes the session
that started it, and what this prints is what the orchestrator reads on waking.

WHAT COUNTS AS ACTIVITY, for one builder: the NEWEST modification time among
  * every file and directory in its worktree (a delete or a rename shows only in a directory's time),
    not descending into `.git`, `node_modules` or `.next`;
  * `HEAD`, `index` and `logs/HEAD` in the worktree's git directory (a linked worktree's `.git` is a FILE that
    names it; a main checkout's `.git` is the directory itself), so a commit or a `git add` counts;
  * the transcript, when one is given after a colon.
The quiet window is counted from the later of that time and the moment the watchdog was ARMED, so a worktree
that was already quiet when the watchdog started gets a full window.

OPEN QUESTION (a) OF THE ROW — a long foreground call that writes nothing. Two answers, both in the code:
  1. Such a call is BOUNDED. `scripts/check-agent-long-call.py` denies a subagent's foreground Bash call whose
     effective timeout is over 270 s, so one silent call cannot last longer than that. QUIET_MIN must therefore
     be MORE than 270 s (`LONGEST_SILENT_CALL_S`, checked against that script's own constant by a case); a
     shorter window is refused as CANNOT RUN, because it would report a builder that is inside one legal call.
  2. A builder that READS for a long stretch (many short calls, no write) changes nothing in its worktree. Its
     transcript does change on every turn. Give it as `name=worktree:transcript` and reading counts as progress.
     Without a transcript the watchdog sees files and git only, and its report says which signals it read.
  Bound: a path that contains a colon cannot be given (the first colon after `=` ends the worktree path).

OPEN QUESTION (b) — several builders. One watchdog takes any number of `name=...` pairs and judges each one
separately at every poll. It exits at the first poll where ANY builder is quiet, reports EVERY quiet one, lists
the ones still active with their age, and prints the command that re-arms the watchdog for those.

EXIT CODES. Watching never exits 0.
    1  at least one builder is quiet: look at it
    2  CANNOT RUN: bad arguments, a worktree that is missing, a git directory or transcript that cannot be
       read. Treat the builder it names as NOT WATCHED. Never skipped in silence: it is checked at arming and at
       every poll, and a builder that is quiet in the same poll is still reported.

WHAT WOULD MAKE THIS FAIL (the row's falsifier): a builder worktree shows no activity for QUIET_MIN minutes
and this process is still running, or it exits without naming that builder.

BOUNDS. It observes modification times, never the agent: a builder that writes one file a minute in a loop
looks active. It does not know that a builder FINISHED; a finished builder goes quiet and is reported, and the
orchestrator reads the report. A worktree nested inside a watched directory counts as that directory's
activity, so watch builder worktrees, not the main checkout that holds them. The wake depends on the caller
starting this as a background job; started in the foreground it blocks the caller.

NO-CALLER: the orchestrator starts this by hand as a background job each time it spawns a builder (`docs/process-checklists.md`, *Agent lifetime*); CI has no builder to watch, and the row keeps a hook in reserve if the convention lapses.
"""
from __future__ import annotations

import math
import os
import sys
import time
from dataclasses import dataclass

POLL_S = 60
# One silent foreground call of a subagent cannot outlast this (`check-agent-long-call.LIMIT_S`). DEFINED here,
# not imported, so a lone copy of this file still runs; a self-test case reads the sibling and refuses a drift.
LONGEST_SILENT_CALL_S = 270
EXCLUDED_DIRS = (".git", "node_modules", ".next")
GIT_REQUIRED = "HEAD"
GIT_OPTIONAL = ("index", "logs/HEAD")
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
    if os.path.isdir(dot):
        return dot
    try:
        with open(dot, encoding="utf-8") as fh:
            text = fh.read()
    except (OSError, UnicodeDecodeError) as exc:
        raise CannotRun(f"{worktree} has no readable .git ({exc}): it is not a git worktree") from None
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


def newest(w: Watch) -> float:
    """The newest modification time among everything that counts as this builder's activity."""
    if not os.path.isdir(w.worktree):
        raise CannotRun(f"the worktree {w.worktree} is missing")
    gd = gitdir_of(w.worktree)
    try:
        best = os.stat(os.path.join(gd, GIT_REQUIRED)).st_mtime
    except OSError as exc:
        raise CannotRun(f"the git directory {gd} is unreadable ({exc})") from None
    for f in GIT_OPTIONAL:
        try:
            best = max(best, os.stat(os.path.join(gd, f)).st_mtime)
        except FileNotFoundError:
            continue
    for root, dirs, files in os.walk(w.worktree, onerror=_walk_error):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for path in [root] + [os.path.join(root, f) for f in files]:
            try:
                best = max(best, os.lstat(path).st_mtime)
            except FileNotFoundError:
                continue
    if w.transcript is not None:
        try:
            best = max(best, os.stat(w.transcript).st_mtime)
        except OSError as exc:
            raise CannotRun(f"the transcript {w.transcript} is unreadable ({exc})") from None
    return best


def report(now: float, quiet_s: float, quiet: dict, active: dict, broken: dict, watches: "list[Watch]") -> str:
    """What the orchestrator reads on waking: every quiet builder, every unwatchable one, the rest, the re-arm."""
    lines = [f"{time.strftime('%m-%d %H:%M', time.localtime(now))} AGENT WATCHDOG (backlog #657): "
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
    rest = [w.spec() for w in watches if w.name in active]
    if rest:
        lines.append(f"  This watchdog has EXITED. To keep watching the active ones: "
                     f"python3 scripts/agent-watchdog.py {quiet_s / 60:g} {' '.join(rest)}")
    return "\n".join(lines)


def main(argv: "list[str] | None" = None, clock=time.time, sleep=time.sleep) -> int:
    argv = sys.argv[1:] if argv is None else argv
    try:
        quiet_s, watches = parse_args(argv)
    except CannotRun as exc:
        print(f"⛔ agent-watchdog CANNOT RUN: {exc}. Nothing is being watched.\n{USAGE}", file=sys.stderr)
        return 2
    armed = clock()
    while True:
        now = clock()
        quiet: dict = {}
        active: dict = {}
        broken: dict = {}
        for w in watches:
            try:
                last = newest(w)
            except CannotRun as exc:
                broken[w.name] = str(exc)
                continue
            idle = now - max(last, armed)
            if idle >= quiet_s:
                quiet[w.name] = idle
            else:
                active[w.name] = max(0.0, now - last)
        if quiet or broken:
            print(report(now, quiet_s, quiet, active, broken, watches))
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
        """A temp directory of worktree-shaped dirs and a FAKE clock. `sleep` advances the clock and runs what
        the case scheduled for that minute; nothing here waits. The clock starts in 2096, so a file the suite
        creates (stamped with the real time) is older than the arming moment unless a case stamps it."""

        def __init__(self):
            self.root = tempfile.mkdtemp(prefix="watchdog-")
            self.t = self.t0 = 4_000_000_000.0
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
            return self.t

        def sleep(self, s):
            self.sleeps.append(s)
            if len(self.sleeps) > 200:
                raise RuntimeError("slept 200 times and never exited")
            self.t += s
            for fn in self.at.pop(len(self.sleeps), []) + self.every:
                fn()

        def on(self, minute, fn):
            self.at.setdefault(minute, []).append(fn)

        def run(self, *argv):
            """-> (exit code, minutes polled, stdout, stderr); a raise is returned as the exit code."""
            out, err = io.StringIO(), io.StringIO()
            try:
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    rc = main(list(argv), clock=self.clock, sleep=self.sleep)
            except Exception as exc:  # noqa: BLE001 - the raise IS the observation
                rc = f"raised {type(exc).__name__}: {exc}"
            return rc, len(self.sleeps), out.getvalue(), err.getvalue()

    def refused(fn, *a):
        try:
            return fn(*a)
        except CannotRun as exc:
            return f"CANNOT RUN: {exc}"

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

    # --- what counts as activity (each case stamps ONE thing newest and reads it back) ------------------------
    def newest_after(make):
        w = World()
        wt, gd = w.wt("a")
        tr = w.stamp(os.path.join(w.root, "a.jsonl"), w.t0 - 86400)
        got = refused(newest, make(w, wt, gd, tr))
        return got if isinstance(got, str) else got - w.t0

    case("activity: with nothing touched the newest time is the day-old fixture",
         newest_after(lambda w, wt, gd, tr: Watch("a", wt)), -86400.0)
    case("activity: a file deep in the worktree counts",
         newest_after(lambda w, wt, gd, tr: (w.stamp(os.path.join(wt, "lib", "x", "y.ts"), w.t0 + 5),
                                             Watch("a", wt))[1]), 5.0)
    case("activity: a directory's own time counts (a delete shows only there)",
         newest_after(lambda w, wt, gd, tr: (os.utime(os.path.join(wt, "src"), (w.t0 + 6, w.t0 + 6)),
                                             Watch("a", wt))[1]), 6.0)
    case("activity: the worktree root's own time counts",
         newest_after(lambda w, wt, gd, tr: (os.utime(wt, (w.t0 + 7, w.t0 + 7)), Watch("a", wt))[1]), 7.0)
    case("activity: the git HEAD, index and logs/HEAD each count",
         [newest_after(lambda w, wt, gd, tr, f=f: (w.stamp(os.path.join(gd, f), w.t0 + 8), Watch("a", wt))[1])
          for f in ("HEAD", "index", "logs/HEAD")], [8.0, 8.0, 8.0])
    case("activity: node_modules and .next, at any depth, do not count",
         [newest_after(lambda w, wt, gd, tr, d=d: (w.stamp(os.path.join(wt, d, "f"), w.t0 + 9),
                                                   os.utime(wt, (w.t0 - 86400,) * 2), Watch("a", wt))[2])
          for d in ("node_modules", ".next", "lib/node_modules")], [-86400.0] * 3)
    w = World()
    wm, gm = w.wt("m", linked=False)
    w.stamp(os.path.join(gm, "objects", "ab", "f"), w.t0 + 9)
    got = refused(newest, Watch("m", wm))
    case("activity: a .git directory's objects do not count, only its HEAD, index and logs/HEAD",
         got if isinstance(got, str) else got - w.t0, -86400.0)
    case("activity: the transcript counts when given, and is not read when it is not",
         (newest_after(lambda w, wt, gd, tr: (w.stamp(tr, w.t0 + 3), Watch("a", wt, tr))[1]),
          newest_after(lambda w, wt, gd, tr: (w.stamp(tr, w.t0 + 3), Watch("a", wt))[1])), (3.0, -86400.0))
    case("activity: a missing index or logs/HEAD is not an error",
         newest_after(lambda w, wt, gd, tr: (os.remove(os.path.join(gd, "index")),
                                             shutil.rmtree(os.path.join(gd, "logs")), Watch("a", wt))[2]), -86400.0)

    def newest_refusal(make):
        w = World()
        wt, gd = w.wt("a")
        return refused(newest, make(w, wt, gd))

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
    rc, minutes, out, err = w.run("10")
    case("main: bad arguments are CANNOT RUN on stderr with the usage, exit 2, nothing polled",
         (rc, minutes, out, "CANNOT RUN" in err, "usage:" in err), (2, 0, "", True, True))

    def never(*_a):
        raise RuntimeError("the clock was read or a poll slept")

    with contextlib.redirect_stderr(io.StringIO()):
        try:
            rc = main(["10", "/w/a"], clock=never, sleep=never)
        except RuntimeError as exc:
            rc = f"raised: {exc}"
    case("main: bad arguments are refused before the clock is read or anything sleeps", rc, 2)
    rc, minutes, out, err = World().run("4", "a=/w/a")
    case("main: a window under the silent-call bound never starts watching",
         (rc, minutes, "270" in err), (2, 0, True))

    print(f"\n{ok}/{ok + fail} self-test cases passed")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(_self_test() if "--self-test" in sys.argv else main())
