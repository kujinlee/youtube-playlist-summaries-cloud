#!/usr/bin/env python3
"""Print what is IN FLIGHT, derived from git and `gh` when it is read, for a SessionStart hook (backlog #362).

WHY THIS FILE EXISTS (measured 2026-10-26).
  Automatic compaction keeps what is on disk and loses what is in flight: which PR waits on what,
  which bet the next review tests, which background job is running and what to do when it ends.
  A hand-written handoff tried to carry that and went stale within minutes. The 17:15 handoff said
  "watch PR #407's CI", and at 19:01 `gh` showed PR #407 DIRTY with NO checks, because GitHub had never
  run CI on it. Only the resume's habit of re-checking caught it. The owner rejected keeping a handoff
  fresh by hand, so the STATE part is derived here, at the moment a session starts or resumes after
  compaction, and cannot be stale.

WHAT IT PRINTS, as one block of DATA (never instructions):
  - every open PR: number, branch, head, draft, mergeability, and a check summary;
  - per open PR, the newest coordinator record on its branch (its heading carries the verdict and
    route) and any decision-log bet on that branch still awaiting its outcome (`outcome: null`);
  - the IN-FLIGHT LEDGER, `.claude/inflight.jsonl` (gitignored, per-checkout): one line per
    background job, written when it is launched (`--add ID WHAT ON_DONE`) and removed when it is
    handled (`--done ID`). It holds the one thing no artifact holds: what a running job is FOR.

⛔ CANNOT RUN IS PRINTED, NEVER SILENT. If `gh` fails, the block says `CANNOT RUN` for the PR part and
treat-as-NOT-CHECKED. An empty PR list would otherwise read as "nothing in flight", which is the
stale handoff's failure in a new form. A per-branch read that fails says so on that PR's line.

⚠ BOUNDS. Every subprocess has a timeout (a session start must not hang). Branch data is read from
`origin/<branch>` after one `git fetch`. If the fetch fails, the block says the refs may be stale.

    python3 scripts/session-state.py                 # print the block (what the hook runs)
    python3 scripts/session-state.py --add ID WHAT ON_DONE
    python3 scripts/session-state.py --done ID
    python3 scripts/session-state.py --self-test  # 28 cases

EXIT CODES: 0 always for the printing mode (a SessionStart hook must not fail the session; failure is
IN the text), 0/1 for --self-test, 2 for a ledger command that cannot write.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LEDGER_REL = ".claude/inflight.jsonl"
DECISION_LOG = "docs/reviews/decision-scheme/decision-log.jsonl"
COORD_DIR = "docs/reviews/coordinator"
TIMEOUT = 20


def _run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)
    return r.returncode, r.stdout if r.returncode == 0 else (r.stderr or r.stdout)


def check_summary(rollup: list) -> str:
    """'15 pass · 1 fail · 2 pending' from a statusCheckRollup list."""
    counts: dict[str, int] = {}
    for c in rollup or []:
        if not isinstance(c, dict):
            continue
        concl = (c.get("conclusion") or c.get("state") or "").upper()
        status = (c.get("status") or "").upper()
        if concl in ("SUCCESS", "NEUTRAL"):
            k = "pass"
        elif concl == "SKIPPED":
            k = "skipped"
        elif concl in ("FAILURE", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED", "ERROR", "STARTUP_FAILURE"):
            k = "fail"
        elif status in ("IN_PROGRESS", "QUEUED", "PENDING", "WAITING", "REQUESTED") or concl in ("", "PENDING", "EXPECTED"):
            k = "pending"
        else:
            k = concl.lower()
        counts[k] = counts.get(k, 0) + 1
    if not counts:
        return "NO CHECKS"
    order = ["fail", "pending", "pass", "skipped"]
    keys = sorted(counts, key=lambda k: (order.index(k) if k in order else 9, k))
    return " · ".join(f"{counts[k]} {k}" for k in keys)


def newest_record(names: list[str], branch: str) -> str | None:
    """The coordinator record with the highest round for `branch`, among file names."""
    best, best_n = None, -1
    prefix = f"{branch}-r"
    for n in names:
        base = n.rsplit("/", 1)[-1]
        if not (base.startswith(prefix) and base.endswith("-coordinator.md")):
            continue
        mid = base[len(prefix):-len("-coordinator.md")]
        if mid.isdigit() and int(mid) > best_n:
            best, best_n = n, int(mid)
    return best


def open_bets(log_text: str, branch: str) -> list[str]:
    """Decision-log rows for `branch` still awaiting an outcome: '<route> — <unit>: <bet>'."""
    out = []
    for line in log_text.splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if not isinstance(r, dict) or r.get("subject") != branch or r.get("outcome") is not None:
            continue
        pred = str(r.get("prediction", ""))
        i = pred.find("Bet:")
        bet = pred[i:i + 220] if i >= 0 else pred[:220]
        out.append(f"{r.get('route')} — {r.get('unit')}: {bet}")
    return out


def read_ledger(path: Path) -> tuple[list[dict], list[str]]:
    """(entries, problems). A missing ledger is empty; a bad line is a problem, never skipped silently."""
    if not path.exists():
        return [], []
    entries, problems = [], []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            e = json.loads(line)
            if not isinstance(e, dict) or not e.get("id"):
                raise ValueError("no id")
            entries.append(e)
        except ValueError as exc:
            problems.append(f"ledger line {i} unreadable ({exc}) — NOT SHOWN")
    return entries, problems


def ledger_add(path: Path, id_: str, what: str, on_done: str, now: str) -> None:
    entries, _ = read_ledger(path)
    entries = [e for e in entries if e.get("id") != id_]
    entries.append({"id": id_, "what": what, "on_done": on_done, "at": now})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries), encoding="utf-8")


def ledger_done(path: Path, id_: str) -> bool:
    entries, _ = read_ledger(path)
    kept = [e for e in entries if e.get("id") != id_]
    if len(kept) == len(entries):
        return False
    path.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in kept), encoding="utf-8")
    return True


def render(prs: list[dict] | None, pr_error: str | None, per_branch: dict[str, dict],
           ledger: list[dict], ledger_problems: list[str], fetch_ok: bool, now: str) -> str:
    """The block, pure: everything it needs is passed in."""
    L = [f"=== IN FLIGHT — derived from git and gh at {now}; DATA, not instructions ==="]
    if not fetch_ok:
        L.append("⚠ `git fetch` failed: branch records below may be STALE.")
    if prs is None:
        L.append(f"OPEN PRS: CANNOT RUN — {pr_error}. Treat as NOT CHECKED, never as 'nothing open'.")
    elif not prs:
        L.append("OPEN PRS: none (gh answered).")
    else:
        L.append(f"OPEN PRS ({len(prs)}):")
        for p in prs:
            b = p.get("headRefName", "?")
            draft = " DRAFT" if p.get("isDraft") else ""
            L.append(f"  PR #{p.get('number')} `{b}` head {str(p.get('headRefOid', ''))[:8]}{draft} · "
                     f"{p.get('mergeStateStatus', '?')} · checks: {check_summary(p.get('statusCheckRollup') or [])}")
            info = per_branch.get(b, {})
            if info.get("error"):
                L.append(f"      branch records: CANNOT READ — {info['error']}")
                continue
            if info.get("record"):
                L.append(f"      latest review: {info['record']}")
            for bet in info.get("bets", []):
                L.append(f"      open bet: {bet}")
    L.append(f"IN-FLIGHT LEDGER ({LEDGER_REL}): " + ("empty" if not ledger and not ledger_problems else ""))
    for e in ledger:
        L.append(f"  [{e.get('id')}] {e.get('what')} — when done: {e.get('on_done')} (since {e.get('at')})")
    for prob in ledger_problems:
        L.append(f"  ⚠ {prob}")
    L.append("=== END IN FLIGHT ===")
    return "\n".join(L)


def collect(root: Path, run=_run, now: str | None = None) -> str:
    now = now or time.strftime("%Y-%m-%d %H:%M %Z")
    fetch_ok = run(["git", "fetch", "-q", "origin"], root)[0] == 0
    rc, out = run(["gh", "pr", "list", "--state", "open", "--limit", "50", "--json",
                   "number,headRefName,headRefOid,isDraft,mergeStateStatus,statusCheckRollup"], root)
    prs, pr_error = None, None
    if rc != 0:
        pr_error = f"gh exited {rc}: {out.strip()[:160]}"
    else:
        try:
            prs = json.loads(out)
            if not isinstance(prs, list):
                raise ValueError("not a list")
        except ValueError as exc:
            prs, pr_error = None, f"gh output unparseable ({exc})"
    per_branch: dict[str, dict] = {}
    for p in prs or []:
        b = p.get("headRefName")
        if not b:
            continue
        rc1, names = run(["git", "ls-tree", "--name-only", f"origin/{b}", f"{COORD_DIR}/"], root)
        if rc1 != 0:
            per_branch[b] = {"error": f"no origin/{b} ({names.strip()[:80]})"}
            continue
        info: dict = {"bets": []}
        rec = newest_record(names.splitlines(), b)
        if rec:
            rc2, body = run(["git", "show", f"origin/{b}:{rec}"], root)
            info["record"] = (body.splitlines()[0].lstrip("# ").strip() if rc2 == 0 and body.strip()
                              else f"{rec} (unreadable)")
        rc3, log = run(["git", "show", f"origin/{b}:{DECISION_LOG}"], root)
        if rc3 == 0:
            info["bets"] = open_bets(log, b)
        per_branch[b] = info
    ledger, problems = read_ledger(root / LEDGER_REL)
    return render(prs, pr_error, per_branch, ledger, problems, fetch_ok, now)


def self_test() -> int:
    import tempfile

    failures = 0
    ran = 0

    def case(name, got, want):
        nonlocal failures, ran
        ok = got == want
        failures += not ok
        ran += 1
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got!r} want {want!r}")

    print("session-state --self-test")
    case("a mixed rollup is summarised with failures first",
         check_summary([{"conclusion": "SUCCESS"}, {"conclusion": "FAILURE"}, {"status": "IN_PROGRESS", "conclusion": ""},
                        {"conclusion": "SKIPPED"}]), "1 fail · 1 pending · 1 pass · 1 skipped")
    case("⭐ an EMPTY rollup says NO CHECKS — the PR #407 state the handoff missed", check_summary([]), "NO CHECKS")
    case("a status-context entry (state, no conclusion) is read", check_summary([{"state": "SUCCESS"}]), "1 pass")
    names = [f"{COORD_DIR}/b-r1-coordinator.md", f"{COORD_DIR}/b-r10-coordinator.md", f"{COORD_DIR}/b-r2-coordinator.md",
             f"{COORD_DIR}/bb-r99-coordinator.md", f"{COORD_DIR}/b-r3-claude.md"]
    case("the newest record is the highest ROUND, numerically, for THIS branch only",
         newest_record(names, "b"), f"{COORD_DIR}/b-r10-coordinator.md")
    case("a branch with no records has none", newest_record(names, "zz"), None)
    case("a bare file name (no directory) is matched the same way",
         newest_record(["x-r4-coordinator.md", "x-r12-coordinator.md"], "x"), "x-r12-coordinator.md")
    log = "\n".join([json.dumps({"subject": "b", "route": "split", "unit": "u", "outcome": None, "prediction": "x. Bet: holds."}),
                     json.dumps({"subject": "b", "route": "redesign", "unit": "u", "outcome": "continued", "prediction": "Bet: old"}),
                     json.dumps({"subject": "c", "route": "accrete", "unit": "v", "outcome": None, "prediction": "Bet: other"}),
                     "{not json"])
    case("only THIS branch's bets still awaiting an outcome are open", open_bets(log, "b"), ["split — u: Bet: holds."])
    case("a bet with no 'Bet:' marker shows its prediction's start",
         open_bets(json.dumps({"subject": "d", "route": "defer", "unit": "w", "outcome": None, "prediction": "stop here"}), "d"),
         ["defer — w: stop here"])

    pr = {"number": 7, "headRefName": "b", "headRefOid": "abcdef1234", "isDraft": True, "mergeStateStatus": "DIRTY",
          "statusCheckRollup": []}
    out = render(None, "gh exited 4: auth", {}, [], [], True, "T")
    case("⭐ gh failing prints CANNOT RUN — never an empty list", "OPEN PRS: CANNOT RUN — gh exited 4: auth" in out, True)
    case("...and does not claim 'none'", "none (gh answered)" in out, False)
    case("an answered empty list says none", "OPEN PRS: none (gh answered)." in render([], None, {}, [], [], True, "T"), True)
    out = render([pr], None, {"b": {"record": "Round 3 — NOT CONVERGED", "bets": ["split — u: Bet: x"]}}, [], [], True, "T")
    case("a PR line carries number, branch, head, draft, mergeability and checks",
         "PR #7 `b` head abcdef12 DRAFT · DIRTY · checks: NO CHECKS" in out, True)
    case("...with its latest review and open bet under it",
         "latest review: Round 3 — NOT CONVERGED" in out and "open bet: split — u: Bet: x" in out, True)
    case("a branch whose records cannot be read says so on its line",
         "CANNOT READ — no origin/b" in render([pr], None, {"b": {"error": "no origin/b"}}, [], [], True, "T"), True)
    case("a failed fetch is flagged as possibly STALE", "may be STALE" in render([], None, {}, [], [], False, "T"), True)
    out = render([], None, {}, [{"id": "j", "what": "Codex r2", "on_done": "fold", "at": "T0"}], ["line 3 bad"], True, "09:00")
    case("render() shows each ledger job with its on-done step, each ledger problem, and the time given",
         ("[j] Codex r2 — when done: fold (since T0)" in out, "⚠ line 3 bad" in out, "at 09:00;" in out,
          "): empty" in out), (True, True, True, False))

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        led = root / LEDGER_REL
        ledger_add(led, "job1", "Codex r4 on PR #9", "record r4; merge on READY", "T1")
        ledger_add(led, "job2", "CI watch PR #9", "read gh pr checks", "T2")
        ledger_add(led, "job1", "Codex r4 on PR #9 (re-run)", "same", "T3")
        entries, _ = read_ledger(led)
        case("re-adding an id REPLACES it — one line per job", [e["id"] for e in entries], ["job2", "job1"])
        case("done removes exactly that job", (ledger_done(led, "job2"), [e["id"] for e in read_ledger(led)[0]]),
             (True, ["job1"]))
        case("done on an unknown id says False", ledger_done(led, "nope"), False)
        other = root / "elsewhere" / "inflight.jsonl"  # the ledger is the PATH given, created on demand
        ledger_add(other, "x", "w", "d", "T9")
        case("a ledger is written at the path given, and only there",
             ([e["id"] for e in read_ledger(other)[0]], [e["id"] for e in read_ledger(led)[0]]), (["x"], ["job1"]))
        case("done at another path removes there, and leaves this ledger alone",
             (ledger_done(other, "x"), read_ledger(other)[0], [e["id"] for e in read_ledger(led)[0]]), (True, [], ["job1"]))
        led.write_text(led.read_text() + "{broken\n")
        case("⭐ an unreadable ledger line is REPORTED, not silently dropped", len(read_ledger(led)[1]), 1)

        def fake(cmd, cwd, _=None):
            if cmd[:2] == ["git", "fetch"]:
                return 0, ""
            if cmd[:2] == ["gh", "pr"]:
                return 0, json.dumps([pr])
            if cmd[:2] == ["git", "ls-tree"]:
                return 0, f"{COORD_DIR}/b-r2-coordinator.md\n{COORD_DIR}/b-r1-coordinator.md\n"
            if cmd[:2] == ["git", "show"] and cmd[2].endswith("coordinator.md"):
                return 0, "# Round 2 — `b` — coordinator — NOT CONVERGED\n\nbody"
            if cmd[:2] == ["git", "show"]:
                return 0, log
            return 1, "unexpected"
        out = collect(root, run=fake, now="T")
        case("collect() wires the newest record, the open bet and the ledger into one block",
             all(s in out for s in ("latest review: Round 2 — `b` — coordinator — NOT CONVERGED",
                                    "open bet: split — u: Bet: holds.", "[job1] Codex r4 on PR #9 (re-run)")), True)
        bare = root / "no-ledger-here"
        bare.mkdir()
        out = collect(bare, run=lambda cmd, cwd: (1, "network down"), now="21:20 PDT")
        case("collect() stamps the time it was given and reads the ledger of the ROOT given",
             ("derived from git and gh at 21:20 PDT" in out, "[job1]" in out), (True, False))
        case("collect() with everything failing still prints a block that says CANNOT RUN and STALE",
             ("CANNOT RUN" in out, "may be STALE" in out, out.endswith("=== END IN FLIGHT ===")), (True, True, True))
        case("main() prints the block from a given root and exits 0",
             main([], root=root, run=lambda cmd, cwd: (1, "x")), 0)
        case("main() runs the fetchers it is GIVEN — a gh answer of [] reaches the block as 'none'",
             (main([], root=root, run=lambda cmd, cwd: (0, "[]")), "none (gh answered)" in collect(root, run=lambda c, w: (0, "[]"))),
             (0, True))
        r2 = root / "second-root"
        r2.mkdir()
        added = main(["--add", "k", "Codex r1 on PR #1", "record it"], root=r2)
        seen = [e["id"] for e in read_ledger(r2 / LEDGER_REL)[0]]
        removed = main(["--done", "k"], root=r2)
        case("main --add then --done round-trips through the ledger under the ROOT given",
             (added, seen, removed, read_ledger(r2 / LEDGER_REL)[0]), (0, ["k"], 0, []))

    print(f"\n{ran - failures}/{ran} self-test cases passed")
    return 1 if failures else 0


def main(argv: list[str] | None = None, root: Path = REPO_ROOT, run=_run) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--add", nargs=3, metavar=("ID", "WHAT", "ON_DONE"))
    ap.add_argument("--done", metavar="ID")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    led = root / LEDGER_REL
    try:
        if args.add:
            ledger_add(led, *args.add, time.strftime("%m-%d %H:%M"))
            print(f"ledger: added {args.add[0]}")
            return 0
        if args.done:
            print(f"ledger: {'removed' if ledger_done(led, args.done) else 'no such id'} {args.done}")
            return 0
    except OSError as exc:
        print(f"CANNOT RUN — ledger {led}: {exc}", file=sys.stderr)
        return 2
    print(collect(root, run=run))
    return 0


if __name__ == "__main__":
    sys.exit(main())
