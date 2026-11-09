#!/usr/bin/env python3
"""A tripwire for dev speed: record each merged PR's per-job CI durations, warn on a weekly rise.

WHY THIS EXISTS (backlog #397, slice 1)
---------------------------------------
Measured 2026-10-29: CI's median per run went from 4.5 to 25.4 minutes over seven weeks (W36->W43).
The mutation sweep grew inside one job and nothing flagged it, because each week's step looked
small. This script makes the step visible in the week it lands.

TWO HALVES, AND THE RULE IS KEPT APART FROM THE FETCH (the repo's `separate-the-rule-from-the-fetch`)
  * RECORD — for each PR merged since `--since`, read the `CI` workflow run on the PR's FINAL head
    (read-only `gh api`), and append one row per JOB (`started_at` -> `completed_at`, whole seconds)
    to a JSON-lines log. A matrix job (`mutation-sweep (N)`) is recorded per shard AND as one
    derived group row, `mutation-sweep [slowest shard]`: the slowest shard is what wall-clock waits
    on. The append is idempotent — a row's key is (pr, head sha, job), and a key already in the
    log is never written twice.
  * A PR IS A SNAPSHOT, WRITTEN WHOLE (r2 R2-F2, R2-F5). Every row of one (pr, head sha) carries the
    same `run`, `attempt`, `n_rows` and `unmeasured` (the jobs that ran but could not be timed: a
    shard cancelled for a reason other than its timeout, a job with no timestamps, and the group
    rows those make unknown). A snapshot is written in ONE locked write (`fcntl.flock` on a
    sibling `.lock` file, held across read -> check -> write, so concurrent worktrees cannot both
    append it). Only a snapshot that is whole and has nothing unmeasured is skipped by a later
    record; any other is fetched again and REPLACED when the fetch differs. On read, a snapshot
    whose rows disagree, or whose row count is not its `n_rows`, is TORN: the report refuses a
    torn snapshot in the weeks it compares, and the next record repairs it.
  * WARN — group the log by the ISO week of each PR's MERGE date. For each job and job group,
    compare the evaluated week's median with the previous ISO week's, and WARN when it rose 25% or
    more. A job with fewer than `MIN_SAMPLES` rows in EITHER week is NOT MEASURED, never "fine",
    and so is a job that ANY snapshot of either week lists as unmeasured: a missing sample could
    move the median (r2 R2-F1, R2-F4). The week of a row is checked against its merge date on read
    (r2 R2-F6).
    The evaluated week defaults to the last COMPLETE ISO week before today (UTC), never the latest
    week in the log: a partial week is too thin to measure, and a stale log must not be read as
    current (r1 R1-F2, R1-F3). A log with no merge in that week is CANNOT RUN, naming its latest.

⚠ WHAT A DURATION HERE IS, AND IS NOT. `started_at` -> `completed_at` is a job's EXECUTION time. It
excludes the time a job waited in the queue for a runner, so the slowest shard is a floor on the
run's wall-clock, not the wall-clock itself. Skipped jobs are not recorded: a skipped job takes
~0 s and would drag a median down for a reason that is not speed.

⚠ A CANCELLED JOB IS TWO DIFFERENT THINGS (r1 R1-F1). A shard KILLED BY ITS `timeout-minutes` is
reported `cancelled`, and it is the slowest shard there is — measured on CI run 42432602877, where
three sweep shards ran 30-35 min and came back `cancelled`. A job cancelled by anything else (a
newer push, a manual cancel) says nothing about speed. The two are told apart by the REASON GitHub
records, not by a duration guess: a timeout kill carries the failure annotation "The job has exceeded
the maximum execution time of …" on its check run. A timed-out job is recorded (`timed_out: true`)
and counts toward its group's slowest shard; any other cancelled shard makes its group's slowest
shard UNKNOWN, so that group gets NO derived row — never the maximum of the shards that survived.

⚠ THE SHARD COUNT IS NOT CONSTANT. The sweep selects manifests per PR, so a docs PR may run a few
shards and a harness PR the full set; per-shard rows are therefore noisy across PRs, and the group
row is the comparable one. Recorded as stated, not corrected for.

WHERE THE LOG LIVES, AND WHY
----------------------------
Default: `<main checkout>/.claude/ci-durations.jsonl`, resolved through `git rev-parse
--git-common-dir`, so every worktree reads and appends ONE log. The file is git-ignored by its own
`.gitignore` entry, added with this script. It is NOT tracked under `docs/`, for two reasons: every row is
re-derivable from GitHub at any time (losing the log costs one re-run), and a tracked append-only
log is the repo's recorded parallel-branch conflict — three same-day PRs, the first clean, the rest
conflicting on one log. `--log PATH` overrides.

EXIT CODES (the repo's convention)
    0  no rise in the evaluated week (NOT MEASURED jobs are listed, never counted as fine)
    1  a rise of 25% or more was found
    2  CANNOT RUN — no `gh`, no network, nothing parsed, ANY listed PR not recorded (no `CI` run on
       its head, the run not complete, or no job measurable — r2 R2-F1, R2-F3), a list that
       may be truncated, a malformed log or a torn snapshot in the compared weeks, an invalid --week, the time budget ran out before every
       PR was read (re-run: the append is idempotent), NO job could be measured, or ANY unexpected
       error (an uncaught crash would exit 1, which is the RISE code — r1 R1-F4)
    Record + report (the default): a measured RISE is rc 1 even beside a PARTIAL record — it was
    measured on the rows already logged; otherwise either half's CANNOT RUN is rc 2 (r1 R1-F6).

NO-CALLER: slice 1 builds the instrument and its rule; which loop runs it weekly (a scheduled CI job
that opens an issue on rc 1, or the SessionStart path) is backlog #584, filed with this slice. Until
then the row's FAILS IF ("nothing reports it in that week") is NOT met by this script alone.

Usage:
    python3 scripts/ci-durations.py                      # record the last 21 days, then report
    python3 scripts/ci-durations.py --record --since 2026-10-26
    python3 scripts/ci-durations.py --report [--week 2026-W45]   # default: the last complete week
    python3 scripts/ci-durations.py --self-test  # 93 cases
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as _dt
import fcntl
import fractions
import json
import math
import os
import pathlib
import re
import shutil
import statistics
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
NO_RISE, RISE_FOUND, CANNOT_RUN = 0, 1, 2
MIN_SAMPLES = 3
WORKFLOW = "CI"
RECORDED_CONCLUSIONS = ("success", "failure")
MATRIX = re.compile(r"^(?P<base>.+) \((?P<idx>\d+)\)$")
GROUP_SUFFIX = " [slowest shard]"
DEFAULT_BUDGET_S = 200   # under the 270 s cap an agent's tool call has; the append resumes
GH_TIMEOUT_S = 60        # each call's timeout is ALSO capped by the budget left (r1 R1-F8)
TIMEOUT_MARK = "exceeded the maximum execution time"   # the check-run annotation of a timeout kill
PR_LIMIT = 500           # `gh pr list --limit`; a full page may be truncated, so it is refused (R1-F9)
LOG_FIELDS = {"pr": int, "sha": str, "merged_at": str, "week": str, "job": str, "seconds": int,
              "run": int, "attempt": int, "n_rows": int, "unmeasured": list}
SNAPSHOT_FIELDS = ("merged_at", "run", "attempt", "n_rows", "unmeasured")   # equal on every row of a PR


class CannotRun(Exception):
    """A reason the measurement could not be taken. Always rc 2, never a pass."""


# ---------------------------------------------------------------- the RULE: pure, fixture-tested

def _ts(s: str) -> _dt.datetime:
    return _dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def iso_week(merged_at: str) -> str:
    """PURE. An ISO-8601 timestamp -> its ISO week, `YYYY-Www` (UTC)."""
    y, w, _ = _ts(merged_at).astimezone(_dt.timezone.utc).isocalendar()
    return f"{y}-W{w:02d}"


def previous_week(week: str) -> str:
    """PURE. `2026-W01` -> `2025-W53` where that week exists; a calendar step, not a list lookup."""
    y, w = week.split("-W")
    monday = _dt.date.fromisocalendar(int(y), int(w), 1)
    py, pw, _ = (monday - _dt.timedelta(days=7)).isocalendar()
    return f"{py}-W{pw:02d}"


def valid_week(week: str) -> bool:
    """PURE. True only for a `YYYY-Www` that names a real ISO week (2025-W53 does not exist)."""
    if not re.fullmatch(r"\d{4}-W\d{2}", week):
        return False
    try:
        _dt.date.fromisocalendar(int(week[:4]), int(week[6:]), 1)
    except ValueError:
        return False
    return True


def last_complete_week(today: _dt.date) -> str:
    """PURE. The ISO week before the one `today` falls in — the last week that can no longer grow."""
    y, w, _ = today.isocalendar()
    return previous_week(f"{y}-W{w:02d}")


def is_timeout_kill(annotations) -> bool:
    """PURE. True when a cancelled job's check-run annotations record a `timeout-minutes` kill."""
    if not isinstance(annotations, list):
        raise CannotRun("a check run's annotations were not a list")
    return any(TIMEOUT_MARK in (a.get("message") or "") for a in annotations)


def job_rows(pr: int, sha: str, merged_at: str, jobs: list[dict], run: int = 0,
             attempt: int = 1) -> list[dict]:
    """PURE. The GitHub jobs list of one run -> the PR's SNAPSHOT: one row per recorded job, plus
    group rows, every row stamped with the snapshot's run, attempt, row count and unmeasured jobs.

    A job is recorded only if it concluded `success` or `failure`, or was cancelled by its timeout
    (`timed_out`, set by the fetch from the check run's annotations), and has both timestamps. A
    skipped job did not run and is ignored. ANY other job ran but cannot be timed: it is listed in
    `unmeasured`. Each matrix group (`base (N)`) gains ONE derived row holding its slowest shard's
    seconds — unless one of its shards is unmeasured, which makes the slowest shard unknown: no group
    row, and the group is listed unmeasured too (r2 R2-F4: a shard with no timestamps counts).
    """
    rows = []
    unknown: set[str] = set()
    unmeasured: set[str] = set()
    for j in jobs:
        concl = j.get("conclusion")
        name = j.get("name") or ""
        m = MATRIX.match(name)
        timed_out = concl == "cancelled" and j.get("timed_out") is True
        if concl not in RECORDED_CONCLUSIONS and not timed_out:
            if concl != "skipped":
                unmeasured.add(name)
                if m:
                    unknown.add(m.group("base"))
            continue
        if not j.get("started_at") or not j.get("completed_at"):
            unmeasured.add(name)
            if m:
                unknown.add(m.group("base"))
            continue
        secs = int((_ts(j["completed_at"]) - _ts(j["started_at"])).total_seconds())
        rows.append({"pr": pr, "sha": sha, "merged_at": merged_at, "week": iso_week(merged_at),
                     "job": name, "seconds": secs, "derived": False, "timed_out": timed_out})
    groups: dict[str, int] = {}
    for r in rows:
        m = MATRIX.match(r["job"])
        if m:
            base = m.group("base")
            groups[base] = max(groups.get(base, -1), r["seconds"])
    for base, secs in sorted(groups.items()):
        if base in unknown:
            continue
        rows.append({"pr": pr, "sha": sha, "merged_at": merged_at, "week": iso_week(merged_at),
                     "job": base + GROUP_SUFFIX, "seconds": secs, "derived": True})
    unmeasured |= {base + GROUP_SUFFIX for base in unknown}
    snap = {"run": run, "attempt": attempt, "n_rows": len(rows), "unmeasured": sorted(unmeasured)}
    return [dict(r, **snap) for r in rows]


def row_key(r: dict) -> tuple:
    return (r["pr"], r["sha"], r["job"])


def new_rows(existing: list[dict], fetched: list[dict]) -> list[dict]:
    """PURE. The fetched rows whose key is not already in `existing` — the idempotent append."""
    seen = {row_key(r) for r in existing}
    out = []
    for r in fetched:
        if row_key(r) not in seen:
            seen.add(row_key(r))
            out.append(r)
    return out


def snapshot_states(rows: list[dict]) -> dict[tuple, str]:
    """PURE. {(pr, sha): "complete" | "incomplete" | "torn"} — the read-side check of a snapshot.

    TORN: its rows disagree on a snapshot field, repeat a job, or number other than `n_rows` (an
    interrupted or duplicated write). INCOMPLETE: whole, but some job ran unmeasured. Only a
    COMPLETE snapshot is never fetched again (r2 R2-F2: one logged row no longer means "known").
    """
    by: dict[tuple, list[dict]] = {}
    for r in rows:
        by.setdefault((r["pr"], r["sha"]), []).append(r)
    out = {}
    for k, rs in by.items():
        heads = {json.dumps([r[f] for f in SNAPSHOT_FIELDS]) for r in rs}
        jobs = [r["job"] for r in rs]
        if len(heads) != 1 or len(rs) != rs[0]["n_rows"] or len(set(jobs)) != len(jobs):
            out[k] = "torn"
        elif rs[0]["unmeasured"]:
            out[k] = "incomplete"
        else:
            out[k] = "complete"
    return out


def pick_ci_run(runs: list[dict], sha: str) -> dict | None:
    """PURE. The newest `CI` run on exactly `sha`, or None. Another workflow is never chosen."""
    mine = [r for r in runs if r.get("name") == WORKFLOW and r.get("head_sha") == sha]
    if not mine:
        return None
    return max(mine, key=lambda r: (r.get("created_at") or "", r.get("id") or 0))


def unmeasured_by_job(rows: list[dict], week: str) -> dict[str, int]:
    """PURE. {job: a PR whose snapshot in `week` ran the job but could not time it}."""
    out: dict[str, int] = {}
    for r in rows:
        if r["week"] == week:
            for job in r["unmeasured"]:
                out.setdefault(job, r["pr"])
    return out


def samples_by_job(rows: list[dict], week: str) -> dict[str, list[int]]:
    """PURE. {job: [seconds…]} for the rows of one ISO week, deduplicated by key."""
    out: dict[str, list[int]] = {}
    seen = set()
    for r in rows:
        if r["week"] != week or row_key(r) in seen:
            continue
        seen.add(row_key(r))
        out.setdefault(r["job"], []).append(r["seconds"])
    return out


def is_rise(prev_median: float, cur_median: float) -> bool:
    """PURE. True when `cur` is 25% or more above `prev`. Exact: 4*cur >= 5*prev, no float ratio."""
    return 4 * cur_median >= 5 * prev_median


def compare_weeks(rows: list[dict], week: str, min_samples: int = MIN_SAMPLES) -> list[dict]:
    """PURE. One verdict per job seen in `week` or the week before it.

    status is RISE, OK, or NOT MEASURED — the last whenever a snapshot of either week lists the job
    unmeasured (a missing sample could move the median: r2 R2-F1, R2-F4), either week has fewer than
    `min_samples` rows for the job, or the previous median is zero (no percentage exists).
    """
    prev = previous_week(week)
    cur_s, prev_s = samples_by_job(rows, week), samples_by_job(rows, prev)
    gaps = {**unmeasured_by_job(rows, prev), **unmeasured_by_job(rows, week)}
    out = []
    for job in sorted(set(cur_s) | set(prev_s) | set(gaps)):
        c, p = cur_s.get(job, []), prev_s.get(job, [])
        v = {"job": job, "week": week, "prev_week": prev, "n_cur": len(c), "n_prev": len(p),
             "cur": statistics.median(c) if c else None,
             "prev": statistics.median(p) if p else None}
        if job in gaps:
            v["status"] = "NOT MEASURED"
            v["why"] = f"PR {gaps[job]}'s run did not measure it"
        elif len(c) < min_samples or len(p) < min_samples:
            v["status"] = "NOT MEASURED"
            v["why"] = (f"{len(p)} sample(s) in {prev} and {len(c)} in {week}; "
                        f"needs {min_samples} in each")
        elif v["prev"] <= 0:
            v["status"] = "NOT MEASURED"
            v["why"] = f"the {prev} median is 0 s, so no percentage rise exists"
        else:
            v["status"] = "RISE" if is_rise(v["prev"], v["cur"]) else "OK"
        out.append(v)
    return out


def pct_text(prev: float, cur: float) -> str:
    """PURE. The rise as a signed percentage, one decimal, TRUNCATED toward zero in exact arithmetic,
    so the text never crosses the 25% line the verdict did not (r1 R1-F7: `round` printed +25% by OK).
    """
    p, c = fractions.Fraction(prev), fractions.Fraction(cur)
    tenths = math.trunc((c - p) * 1000 / p)
    sign = "-" if tenths < 0 else "+"
    return f"{sign}{abs(tenths) // 10}.{abs(tenths) % 10}%"


def combine_rc(rc_rec: int, rc_rep: int) -> int:
    """PURE. Record + report -> one rc. A measured RISE dominates (it was measured on the rows
    already logged); otherwise either half's CANNOT RUN is CANNOT RUN; else no rise (r1 R1-F6)."""
    if rc_rep == RISE_FOUND:
        return RISE_FOUND
    if CANNOT_RUN in (rc_rec, rc_rep):
        return CANNOT_RUN
    return NO_RISE


def verdict_rc(verdicts: list[dict]) -> int:
    """PURE. 1 if any RISE; 2 if nothing at all was measured; else 0."""
    if any(v["status"] == "RISE" for v in verdicts):
        return RISE_FOUND
    if not any(v["status"] == "OK" for v in verdicts):
        return CANNOT_RUN
    return NO_RISE


def _fmt_secs(x) -> str:
    return "-" if x is None else f"{x:g}s"


def format_report(verdicts: list[dict], week: str, min_samples: int = MIN_SAMPLES) -> str:
    """PURE. The human report. Every RISE line names the job and both medians."""
    lines = [f"CI job durations — {week} vs {previous_week(week)} (median of execution seconds "
             f"per job, merge-date ISO weeks; WARN at a rise of 25% or more; "
             f"min {min_samples} samples per week)"]
    order = {"RISE": 0, "OK": 1, "NOT MEASURED": 2}
    for v in sorted(verdicts, key=lambda v: (order[v["status"]], v["job"])):
        head = f"  {v['status']:<12} {v['job']}"
        meds = (f"{v['prev_week']} {_fmt_secs(v['prev'])} (n={v['n_prev']}) -> "
                f"{v['week']} {_fmt_secs(v['cur'])} (n={v['n_cur']})")
        if v["status"] == "NOT MEASURED":
            lines.append(f"{head} — NOT MEASURED: {v['why']}. {meds}")
        else:
            lines.append(f"{head} — {meds}, {pct_text(v['prev'], v['cur'])}")
    rc = verdict_rc(verdicts)
    if rc == RISE_FOUND:
        n = sum(v["status"] == "RISE" for v in verdicts)
        lines.append(f"WARN: {n} job(s) rose 25% or more in {week}.")
    elif rc == CANNOT_RUN:
        lines.append(f"CANNOT RUN — no job had {min_samples} samples in both {week} and "
                     f"{previous_week(week)}. TREAT THIS AS NOT MEASURED, never as no rise.")
    else:
        lines.append(f"no measured job rose 25% or more in {week}.")
    return "\n".join(lines)


def parse_log(text: str) -> list[dict]:
    """PURE. JSON-lines -> rows. A malformed, incomplete or mistyped line is CANNOT RUN, never
    skipped — and never a crash later, whose exit 1 is the RISE code (r1 R1-F4)."""
    rows = []
    for i, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CannotRun(f"log line {i} is not JSON ({exc})") from None
        if not isinstance(r, dict):
            raise CannotRun(f"log line {i} is not a JSON object")
        missing = [k for k in LOG_FIELDS if k not in r]
        if missing:
            raise CannotRun(f"log line {i} lacks {', '.join(missing)}")
        # Each later check reads only the fields PRESENT, so the missing-field refusal above is the
        # ONLY thing that refuses a short line — its mutant then accepts the line, never crashes (R1-F5).
        bad = [k for k, t in LOG_FIELDS.items() if k in r and type(r[k]) is not t]
        if bad:
            raise CannotRun(f"log line {i} has the wrong type for {', '.join(bad)}")
        try:
            _ts(r.get("merged_at") or "2000-01-01T00:00:00Z")
        except ValueError:
            raise CannotRun(f"log line {i} has merged_at {r['merged_at']!r}, not an ISO time") from None
        if "week" in r and not valid_week(r["week"]):
            raise CannotRun(f"log line {i} has week {r['week']!r}, not a real ISO week")
        if "week" in r and "merged_at" in r and r["week"] != iso_week(r["merged_at"]):
            raise CannotRun(f"log line {i} has week {r['week']}, but its merge is in "
                            f"{iso_week(r['merged_at'])}")   # r2 R2-F6: the bucket is the merge's
        if any(type(x) is not str for x in r.get("unmeasured") or []):
            raise CannotRun(f"log line {i} has an unmeasured job that is not a string")
        rows.append(r)
    return rows


def latest_week(rows: list[dict]) -> str:
    """PURE. The ISO week of the latest merge in the log."""
    return iso_week(max(r["merged_at"] for r in rows))


# ---------------------------------------------------------------- file I/O: thin, temp-dir tested

def read_log(path: pathlib.Path) -> list[dict]:
    return parse_log(path.read_text()) if path.exists() else []


@contextlib.contextmanager
def _locked(path: pathlib.Path):
    """An exclusive `flock` on `<log>.lock`, shared by every worktree (r2 R2-F5). A sibling file, not
    the log itself: a rewrite replaces the log's inode, and a lock on the old inode would not hold."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(f"{path}.lock", "a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def _canon(rows: list[dict]) -> list[str]:
    return sorted(json.dumps(r, sort_keys=True) for r in rows)


def append_log(path: pathlib.Path, fetched: list[dict], after_read=None) -> int:
    """Write the fetched snapshots. -> how many rows were written.

    Under the lock, read -> check -> write: a snapshot already logged EXACTLY is not written again; a
    logged snapshot that differs (incomplete, torn, or a newer attempt) is REPLACED whole, by an
    atomic rewrite. `after_read` is a test seam, called with the lock held after the read.
    """
    with _locked(path):
        existing = read_log(path)
        if after_read:
            after_read()
        fetched_by: dict[tuple, list[dict]] = {}
        for r in fetched:
            fetched_by.setdefault((r["pr"], r["sha"]), []).append(r)
        stored_by: dict[tuple, list[dict]] = {}
        for r in existing:
            stored_by.setdefault((r["pr"], r["sha"]), []).append(r)
        replace = {k for k, rs in fetched_by.items()
                   if k in stored_by and _canon(stored_by[k]) != _canon(new_rows([], rs))}
        kept = [r for r in existing if (r["pr"], r["sha"]) not in replace]
        add = new_rows(kept, fetched)
        if replace:
            tmp = path.with_name(path.name + ".tmp")
            tmp.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in kept + add))
            os.replace(tmp, path)
        elif add:
            with path.open("a") as fh:
                fh.write("".join(json.dumps(r, sort_keys=True) + "\n" for r in add))
    return len(add)


def utc_today() -> _dt.date:
    return _dt.datetime.now(_dt.timezone.utc).date()


def report_main(path: pathlib.Path, week: str | None, min_samples: int = MIN_SAMPLES,
                today: _dt.date | None = None) -> int:
    """Read the log, evaluate one week against the week before it, print, return the rc.

    The week defaults to the last COMPLETE ISO week before `today` (UTC), never the log's latest.
    """
    try:
        rows = read_log(path)
    except CannotRun as exc:
        print(f"CANNOT RUN — {path}: {exc}. TREAT THIS AS NOT MEASURED.")
        return CANNOT_RUN
    if not rows:
        print(f"CANNOT RUN — the log {path} holds no rows. Run --record first. "
              f"TREAT THIS AS NOT MEASURED.")
        return CANNOT_RUN
    wk = week or last_complete_week(today or utc_today())
    if not any(r["week"] == wk for r in rows):
        print(f"CANNOT RUN — the log {path} holds no merge in {wk}; its latest merge is in "
              f"{latest_week(rows)}. Run --record. TREAT THIS AS NOT MEASURED, never as no rise.")
        return CANNOT_RUN
    pair = {wk, previous_week(wk)}
    torn = sorted(k for k, st in snapshot_states(rows).items()
                  if st == "torn" and any(r["week"] in pair for r in rows if (r["pr"], r["sha"]) == k))
    if torn:
        print(f"CANNOT RUN — the log {path} holds a TORN snapshot in {sorted(pair)}: PR "
              f"{', '.join(str(k[0]) for k in torn)} (rows that disagree or miscount). Run --record "
              f"to repair it. TREAT THIS AS NOT MEASURED.")
        return CANNOT_RUN
    verdicts = compare_weeks(rows, wk, min_samples)
    print(format_report(verdicts, wk, min_samples))
    return verdict_rc(verdicts)


# ---------------------------------------------------------------- the FETCH: read-only `gh`

def _gh(args: list[str], timeout: float = GH_TIMEOUT_S) -> str:
    """Run read-only `gh`. -> stdout. Any failure is CannotRun, never an empty answer."""
    if not shutil.which("gh"):
        raise CannotRun("`gh` is not on PATH")
    try:
        p = subprocess.run(["gh", *args], cwd=ROOT, capture_output=True, text=True,
                           timeout=timeout)
    except subprocess.TimeoutExpired:
        raise CannotRun(f"`gh {' '.join(args[:2])}` timed out after {timeout:g}s") from None
    if p.returncode != 0:
        raise CannotRun(f"`gh {' '.join(args[:2])}` exited {p.returncode}: "
                        f"{p.stderr.strip()[:300]}")
    return p.stdout


def _gh_json(gh, args: list[str], timeout: float):
    out = gh(args, timeout=timeout)
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        raise CannotRun(f"`gh {' '.join(args[:2])}` returned no JSON: {out[:200]!r}") from None


def page_is_whole(payload, key: str) -> bool:
    """PURE. True only when a list response holds every item: its `total_count` is present and no
    larger than the items on the page. A truncated page is refused, never read as whole (R1-F9)."""
    if not isinstance(payload, dict) or not isinstance(payload.get(key), list):
        return False
    tc = payload.get("total_count")
    return isinstance(tc, int) and tc <= len(payload[key])


class _OutOfBudget(Exception):
    """The time budget would be exceeded by the next `gh` call."""


def fetch(since: str, skip: set[tuple], gh=_gh, budget_s: float = DEFAULT_BUDGET_S,
          clock=time.monotonic) -> tuple[list[dict], dict]:
    """Read every PR merged on or after `since` -> (rows, stats). `gh` is injectable for tests.

    A PR whose (number, head sha) is in `skip` is not fetched again. EVERY `gh` call is bounded by
    the budget left — checked before the call, and passed as its timeout — so the whole fetch ends
    within the budget (r1 R1-F8). When it runs out, the PR being read and the rest are counted in
    stats["unread"], and the caller must say PARTIAL.
    """
    t0 = clock()

    def call(args):
        left = budget_s - (clock() - t0)
        if left <= 0:
            raise _OutOfBudget
        return _gh_json(gh, args, min(GH_TIMEOUT_S, left))

    try:
        repo = call(["repo", "view", "--json", "nameWithOwner"]).get("nameWithOwner")
        if not repo:
            raise CannotRun("`gh repo view` named no repository")
        prs = call(["pr", "list", "--state", "merged", "--search", f"merged:>={since}",
                    "--limit", str(PR_LIMIT), "--json", "number,headRefOid,mergedAt"])
    except _OutOfBudget:
        raise CannotRun(f"the {budget_s:g}s budget ran out before the merged PRs were listed") from None
    if not isinstance(prs, list):
        raise CannotRun("`gh pr list` did not return a list")
    if len(prs) >= PR_LIMIT:
        raise CannotRun(f"`gh pr list` returned {len(prs)} PRs, its --limit, so the list may be "
                        f"truncated; use a later --since")
    stats = {"prs": len(prs), "skipped_known": 0, "no_ci_run": 0, "incomplete": 0,
             "unmeasured": 0, "recorded": 0, "unread": 0}
    rows: list[dict] = []
    ordered = sorted(prs, key=lambda p: p["mergedAt"])
    for i, pr in enumerate(ordered):
        if (pr["number"], pr["headRefOid"]) in skip:
            stats["skipped_known"] += 1
            continue
        try:
            got = _read_pr(call, repo, pr)
        except _OutOfBudget:
            rest = [(q["number"], q["headRefOid"]) in skip for q in ordered[i:]]
            stats["unread"] = rest.count(False)
            stats["skipped_known"] += rest.count(True)
            break
        if isinstance(got, str):
            stats[got] += 1
            continue
        rows.extend(got)
        stats["recorded"] += 1
    return rows, stats


def _read_pr(call, repo: str, pr: dict):
    """One PR -> its rows, or the stats key that says why it has none."""
    sha = pr["headRefOid"]
    runs = call(["api", f"repos/{repo}/actions/runs?head_sha={sha}&per_page=50"])
    if not page_is_whole(runs, "workflow_runs"):
        raise CannotRun(f"the runs list for {sha[:12]} is incomplete or truncated")
    run = pick_ci_run(runs["workflow_runs"], sha)
    if run is None:
        return "no_ci_run"
    if run.get("status") != "completed":
        return "incomplete"
    attempt = run.get("run_attempt") or 1
    if not isinstance(run.get("id"), int) or not isinstance(attempt, int):
        raise CannotRun(f"the CI run on {sha[:12]} has no integer id or attempt")
    jobs = call(["api", f"repos/{repo}/actions/runs/{run['id']}/jobs?filter=latest&per_page=100"])
    if not page_is_whole(jobs, "jobs"):
        raise CannotRun(f"the jobs list of run {run['id']} is incomplete or truncated")
    for j in jobs["jobs"]:
        if j.get("conclusion") == "cancelled" and j.get("check_run_url"):
            path = j["check_run_url"].split("api.github.com/", 1)[-1] + "/annotations"
            j["timed_out"] = is_timeout_kill(call(["api", path]))
    rows = job_rows(pr["number"], sha, pr["mergedAt"], jobs["jobs"], run["id"], attempt)
    return rows or "unmeasured"   # r2 R2-F3: a run with no timeable job recorded nothing


def default_log() -> pathlib.Path:
    """`<main checkout>/.claude/ci-durations.jsonl`, shared by every worktree (see the docstring)."""
    try:
        p = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=ROOT,
                           capture_output=True, text=True, timeout=10)
        common = p.stdout.strip() if p.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        common = ""
    if not common:
        return ROOT / ".claude" / "ci-durations.jsonl"
    c = pathlib.Path(common)
    c = c if c.is_absolute() else (ROOT / c).resolve()
    return c.parent / ".claude" / "ci-durations.jsonl"


def record_main(path: pathlib.Path, since: str, gh=_gh, budget_s: float = DEFAULT_BUDGET_S,
                clock=time.monotonic) -> int:
    try:
        known = {k for k, st in snapshot_states(read_log(path)).items() if st == "complete"}
        rows, st = fetch(since, known, gh=gh, budget_s=budget_s, clock=clock)
    except CannotRun as exc:
        print(f"CANNOT RUN — {exc}. TREAT THIS AS NOT RECORDED.")
        return CANNOT_RUN
    except Exception as exc:  # noqa: BLE001 - an unexpected gh payload shape is CANNOT RUN, not rc 1
        print(f"CANNOT RUN — an unexpected gh answer ({type(exc).__name__}: {exc}). "
              f"TREAT THIS AS NOT RECORDED.")
        return CANNOT_RUN
    if st["prs"] == 0:
        print(f"CANNOT RUN — nothing parsed: 0 merged PRs since {since}. "
              f"TREAT THIS AS NOT RECORDED.")
        return CANNOT_RUN
    why = (f"{st['no_ci_run']} without a `{WORKFLOW}` run on their head, {st['incomplete']} with "
           f"the run not yet complete, {st['unmeasured']} with no job measurable")
    if st["recorded"] == 0 and st["prs"] > st["skipped_known"] + st["unread"]:
        print(f"CANNOT RUN — nothing recorded: {st['prs'] - st['skipped_known']} PR(s) needed reading "
              f"and none was ({why}). TREAT THIS AS NOT RECORDED.")
        return CANNOT_RUN
    added = append_log(path, rows)
    print(f"recorded {st['recorded']} PR(s), {added} new row(s) -> {path}; "
          f"{st['skipped_known']} already in the log, {why} "
          f"({st['prs']} merged since {since}).")
    failed = st["no_ci_run"] + st["incomplete"] + st["unmeasured"]
    if failed:
        # r2 R2-F1: ONE recorded PR must not hide the rest — any of them could move a median.
        print(f"CANNOT RUN — {failed} PR(s) not recorded ({why}). Re-run once their runs complete. "
              f"TREAT THE LOG AS INCOMPLETE.")
        return CANNOT_RUN
    if st["unread"]:
        print(f"PARTIAL — the {budget_s:g}s budget ran out with {st['unread']} PR(s) unread. "
              f"Re-run: the append is idempotent and resumes. TREAT THE LOG AS INCOMPLETE.")
        return CANNOT_RUN
    return NO_RISE


# ---------------------------------------------------------------- self-test

def _self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: every `--self-test` runs isolated (backlog #382)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _rows(job: str, week_day: str, secs: list[int], pr0: int = 1) -> list[dict]:
    """Fixture: one row per duration, each its own one-row snapshot (the sha names the job, so two
    calls never share a snapshot), all merged on `week_day`."""
    at = f"{week_day}T12:00:00Z"
    return [{"pr": pr0 + i, "sha": f"s{pr0 + i}-{job}", "merged_at": at, "week": iso_week(at),
             "job": job, "seconds": s, "derived": False, "run": 0, "attempt": 1, "n_rows": 1,
             "unmeasured": []} for i, s in enumerate(secs)]


def _job(name, start, end, conclusion="success"):
    return {"name": name, "started_at": start, "completed_at": end, "conclusion": conclusion}


def _self_test_body() -> int:
    import contextlib
    import io
    import tempfile
    ok = fail = 0

    def check(label, thunk, want):
        nonlocal ok, fail
        try:
            got = thunk()
        except Exception as exc:  # noqa: BLE001 - a raise IS the failure here
            got = f"raised {type(exc).__name__}: {exc}"
        if got == want:
            ok += 1
        else:
            fail += 1
            print(f"[FAIL] {label}: got {got!r} want {want!r}")

    def check_raise(thunk):
        try:
            return f"returned {thunk()!r}"
        except CannotRun as exc:
            return str(exc)

    def status(rows, week, job, n=MIN_SAMPLES):
        return {v["job"]: v["status"] for v in compare_weeks(rows, week, n)}.get(job)

    # W45 = 2026-11-02..08, W44 = 2026-10-26..11-01; W40 = 2026-09-28.., W39 = 2026-09-21..
    A, B = "2026-10-28", "2026-11-04"     # W44 -> W45
    C, D = "2026-09-23", "2026-09-30"     # W39 -> W40

    # --- weeks
    check("iso_week reads the merge date's ISO week", lambda: iso_week("2026-11-09T01:00:00Z"),
          "2026-W46")
    check("...at a second input, across a year boundary", lambda: iso_week("2027-01-01T00:00:00Z"),
          "2026-W53")
    check("previous_week steps back one calendar week", lambda: previous_week("2026-W46"),
          "2026-W45")
    check("...and across a year boundary", lambda: previous_week("2027-W01"), "2026-W53")

    # --- THE FAILS IF: a weekly median rises 25% or more and nothing reports it in that week
    rise1 = _rows("verify", A, [100, 100, 100]) + _rows("verify", B, [125, 125, 125], 10)
    rise2 = _rows("mutation-sweep [slowest shard]", C, [600, 610, 590]) \
        + _rows("mutation-sweep [slowest shard]", D, [800, 790, 900], 10)
    check("⭐ FAILS IF: a 25% rise in the median is reported as RISE in that week",
          lambda: status(rise1, "2026-W45", "verify"), "RISE")
    check("⭐ ...at a second job and baseline (600s -> 800s)",
          lambda: status(rise2, "2026-W40", "mutation-sweep [slowest shard]"), "RISE")
    check("⭐ ...and the rise drives rc 1", lambda: verdict_rc(compare_weeks(rise1, "2026-W45")),
          RISE_FOUND)
    check("⭐ ...and the report names the job and both medians",
          lambda: ("RISE" in format_report(compare_weeks(rise2, "2026-W40"), "2026-W40")
                   and "mutation-sweep [slowest shard] — 2026-W39 600s (n=3) -> 2026-W40 800s (n=3), +33.3%"
                   in format_report(compare_weeks(rise2, "2026-W40"), "2026-W40")), True)

    # --- adjacent negatives: 24% does not warn, 25% does — at two baselines
    check("a 24% rise (100 -> 124) is not a rise", lambda: is_rise(100, 124), False)
    check("a 25% rise (100 -> 125) is a rise", lambda: is_rise(100, 125), True)
    check("a 24% rise at a second baseline (200 -> 248) is not a rise", lambda: is_rise(200, 248),
          False)
    check("a 25% rise at a second baseline (200 -> 250) is a rise", lambda: is_rise(200, 250), True)
    flat1 = _rows("verify", A, [100, 100, 100]) + _rows("verify", B, [124, 124, 124], 10)
    flat2 = _rows("lint", C, [200, 210, 190]) + _rows("lint", D, [248, 240, 250], 10)
    check("a 24% median rise in a week is OK, not RISE", lambda: status(flat1, "2026-W45", "verify"),
          "OK")
    check("...at a second job and baseline", lambda: status(flat2, "2026-W40", "lint"), "OK")
    check("...and no rise is rc 0", lambda: verdict_rc(compare_weeks(flat2, "2026-W40")), NO_RISE)
    check("a FALL is OK, not RISE (the comparison is directional)",
          lambda: status(_rows("verify", A, [300] * 3) + _rows("verify", B, [100] * 3, 10),
                         "2026-W45", "verify"), "OK")

    # --- the MEDIAN, not the mean or the max: one outlier must not warn
    out1 = _rows("verify", A, [100, 100, 100]) + _rows("verify", B, [100, 101, 900], 10)
    out2 = _rows("verify", C, [50, 50, 50, 50]) + _rows("verify", D, [40, 50, 60, 5000], 10)
    check("one slow outlier does not move the median into a RISE",
          lambda: status(out1, "2026-W45", "verify"), "OK")
    check("...at a second input with an even sample count",
          lambda: status(out2, "2026-W40", "verify"), "OK")

    # --- too few samples is NOT MEASURED, never fine — and it is not RISE either
    few1 = _rows("verify", A, [100, 100]) + _rows("verify", B, [900, 900, 900], 10)
    few2 = _rows("lint", C, [100, 100, 100]) + _rows("lint", D, [900, 900], 10)
    check("2 samples in the previous week is NOT MEASURED, even over a 9x rise",
          lambda: status(few1, "2026-W45", "verify"), "NOT MEASURED")
    check("2 samples in the evaluated week is NOT MEASURED",
          lambda: status(few2, "2026-W40", "lint"), "NOT MEASURED")
    check("the minimum is a parameter: at min 2, the first is a RISE",
          lambda: status(few1, "2026-W45", "verify", 2), "RISE")
    check("a job absent from the previous week is NOT MEASURED",
          lambda: status(_rows("new-job", B, [10, 10, 10]), "2026-W45", "new-job"),
          "NOT MEASURED")
    check("a 0 s previous median is NOT MEASURED (no percentage exists)",
          lambda: status(_rows("j", C, [0, 0, 0]) + _rows("j", D, [5, 5, 5], 10), "2026-W40", "j"),
          "NOT MEASURED")
    check("nothing measured at all is rc 2, never rc 0",
          lambda: verdict_rc(compare_weeks(few1, "2026-W45")), CANNOT_RUN)
    check("...and the report says NOT MEASURED, not 'no rise', naming its own week and minimum",
          lambda: ("no job had 4 samples in both 2026-W45 and 2026-W44. TREAT THIS AS NOT MEASURED"
                   in format_report(compare_weeks(few1, "2026-W45", 4), "2026-W45", 4)), True)
    check("a measured OK beside an unmeasured job is rc 0",
          lambda: verdict_rc(compare_weeks(flat1 + few2, "2026-W45")), NO_RISE)
    check("a RISE beside an unmeasured job is still rc 1",
          lambda: verdict_rc(compare_weeks(rise1 + _rows("x", B, [1], 50), "2026-W45")),
          RISE_FOUND)
    check("only the evaluated week and the week before it are compared, not older weeks",
          lambda: status(_rows("verify", "2026-10-21", [10] * 3)
                         + _rows("verify", B, [100] * 3, 10), "2026-W45", "verify"),
          "NOT MEASURED")

    # --- recording: job rows, matrix groups, filters
    jobs1 = [_job("verify", "2026-11-08T21:41:42Z", "2026-11-08T21:46:29Z"),
             _job("mutation-sweep (1)", "2026-11-08T21:41:00Z", "2026-11-08T21:51:00Z"),
             _job("mutation-sweep (2)", "2026-11-08T21:41:00Z", "2026-11-08T21:56:30Z"),
             _job("lint", "2026-11-08T21:41:00Z", "2026-11-08T21:41:00Z", "skipped"),
             _job("e2e", "2026-11-08T21:41:00Z", None)]
    r1 = job_rows(543, "abc", "2026-11-08T22:11:59Z", jobs1)
    secs1 = {r["job"]: r["seconds"] for r in r1}
    check("a job's duration is completed_at - started_at, in whole seconds", lambda: secs1["verify"],
          287)
    check("a matrix group gains ONE derived row holding its SLOWEST shard",
          lambda: (secs1.get("mutation-sweep [slowest shard]"),
                   [r["derived"] for r in r1 if r["job"].endswith(GROUP_SUFFIX)]), (930, [True]))
    check("each shard is ALSO recorded on its own", lambda: (secs1["mutation-sweep (1)"],
                                                            secs1["mutation-sweep (2)"]), (600, 930))
    check("a skipped job and a job with no completed_at are not recorded",
          lambda: ("lint" in secs1, "e2e" in secs1), (False, False))
    jobs2 = [_job("build (3)", "2026-10-01T00:00:00Z", "2026-10-01T00:20:00Z", "failure"),
             _job("build (10)", "2026-10-01T00:00:00Z", "2026-10-01T00:05:00Z"),
             _job("tsc", "2026-10-01T00:00:00Z", "2026-10-01T00:01:00Z", "cancelled")]
    r2 = job_rows(7, "def", "2026-10-01T03:00:00Z", jobs2)
    check("...at a second input: the slowest shard is not the last listed, and a red job counts",
          lambda: {r["job"]: r["seconds"] for r in r2}, {"build (3)": 1200, "build (10)": 300,
                                                         "build [slowest shard]": 1200})
    check("a row carries the PR, the head sha, the merge week and the job",
          lambda: {k: r2[0][k] for k in ("pr", "sha", "week", "job")},
          {"pr": 7, "sha": "def", "week": "2026-W40", "job": "build (3)"})

    # --- the idempotent append
    check("new_rows drops a row whose (pr, sha, job) is already logged",
          lambda: len(new_rows(r1, r1 + r2)), len(r2))
    check("...and a duplicate inside one fetch is written once",
          lambda: len(new_rows([], r2 + r2)), len(r2))
    with tempfile.TemporaryDirectory() as td:
        lp = pathlib.Path(td) / "sub" / "log.jsonl"
        first = append_log(lp, r1)
        again = append_log(lp, r1 + r2)
        check("appending the same rows twice writes them once (re-running never duplicates)",
              lambda: (first, again, len(read_log(lp))), (len(r1), len(r2), len(r1) + len(r2)))

    # --- run selection
    runs = [{"name": "Schema gates", "head_sha": "abc", "created_at": "2026-11-08T22:00:00Z", "id": 9},
            {"name": "CI", "head_sha": "abc", "created_at": "2026-11-08T21:00:00Z", "id": 5},
            {"name": "CI", "head_sha": "abc", "created_at": "2026-11-08T21:30:00Z", "id": 6},
            {"name": "CI", "head_sha": "zzz", "created_at": "2026-11-09T00:00:00Z", "id": 7}]
    check("pick_ci_run takes the newest CI run on exactly that sha, never another workflow",
          lambda: pick_ci_run(runs, "abc")["id"], 6)
    check("...and None when the only run on that sha is another workflow's",
          lambda: pick_ci_run(runs[:1], "abc"), None)
    check("...and None when no run at all is on that sha", lambda: pick_ci_run(runs, "nope"), None)

    # --- R1-F1: a cancelled job is two things — a timeout kill (kept, the slowest) or not (dropped)
    jobs3 = [_job("mutation-sweep (1)", "2026-11-08T01:05:53Z", "2026-11-08T01:10:53Z"),
             dict(_job("mutation-sweep (2)", "2026-11-08T01:05:53Z", "2026-11-08T01:35:55Z", "cancelled"),
                  timed_out=True)]
    r3 = {r["job"]: r["seconds"] for r in job_rows(9, "t1", "2026-11-08T02:00:00Z", jobs3)}
    check("⭐ R1-F1: a shard KILLED BY ITS TIMEOUT is recorded, and is the group's slowest shard",
          lambda: (r3.get("mutation-sweep (2)"), r3.get("mutation-sweep [slowest shard]")), (1802, 1802))
    jobs4 = [_job("sweep (1)", "2026-11-08T01:00:00Z", "2026-11-08T01:05:00Z"),
             dict(_job("sweep (2)", "2026-11-08T01:00:00Z", "2026-11-08T01:20:00Z", "cancelled"),
                  timed_out=False)]
    r4 = {r["job"]: r["seconds"] for r in job_rows(10, "t2", "2026-11-08T02:00:00Z", jobs4)}
    check("⭐ R1-F1: a shard cancelled for another reason is dropped, and its group gets NO row "
          "(never the max of the survivors)", lambda: sorted(r4), ["sweep (1)"])
    check("is_timeout_kill reads the timeout annotation GitHub records on the check run",
          lambda: is_timeout_kill([{"message": "Node.js 20 is deprecated"},
                                   {"message": "The job has exceeded the maximum execution time of 30m0s"}]),
          True)
    check("...and another cancel reason is not a timeout kill",
          lambda: is_timeout_kill([{"message": "The operation was canceled."}]), False)

    # --- the log parser refuses, never skips (R1-F5: each input's ONLY defect is the one named)
    good = {"pr": 1, "sha": "a", "merged_at": "2026-11-04T00:00:00Z", "week": "2026-W45", "job": "j",
            "seconds": 1, "run": 5, "attempt": 1, "n_rows": 1, "unmeasured": []}
    check("a log line missing a field is CANNOT RUN, not read as data",
          lambda: parse_log('{"pr": 1}\n'),
          "raised CannotRun: log line 1 lacks sha, merged_at, week, job, seconds, run, attempt, n_rows, unmeasured")
    check("...and a line lacking ONLY merged_at is refused too (R1-F4: it crashed the default week)",
          lambda: parse_log(json.dumps({k: v for k, v in good.items() if k != "merged_at"})),
          "raised CannotRun: log line 1 lacks merged_at")
    check("...and a line that is not JSON names its line number",
          lambda: parse_log("\n" + json.dumps(good) + "\n{oops"),
          "raised CannotRun: log line 3 is not JSON (Expecting property name enclosed in double quotes: line 1 column 2 (char 1))")
    check("R1-F4: seconds as a STRING is refused, never a crash in the report",
          lambda: parse_log(json.dumps(dict(good, seconds="12"))),
          "raised CannotRun: log line 1 has the wrong type for seconds")
    check("...and a week that is not a real ISO week is refused",
          lambda: parse_log(json.dumps(dict(good, week="2025-W53"))),
          "raised CannotRun: log line 1 has week '2025-W53', not a real ISO week")
    check("...and a well-formed line is read", lambda: parse_log(json.dumps(good)), [good])
    check("valid_week refuses a week that does not exist (2025 has 52)",
          lambda: (valid_week("2026-W53"), valid_week("2025-W53"), valid_week("2026-W00"),
                   valid_week("2026-W5")), (True, False, False, False))
    check("last_complete_week is the ISO week BEFORE today's, at two dates",
          lambda: (last_complete_week(_dt.date(2026, 11, 9)), last_complete_week(_dt.date(2027, 1, 6))),
          ("2026-W45", "2026-W53"))

    # --- R1-F7: the printed percentage never contradicts the verdict
    edge = _rows("verify", A, [1000] * 3) + _rows("verify", B, [1249, 1249, 1250, 1250], 10)
    check("R1-F7: a 24.95% rise prints as OK with +24.9%, never a rounded +25%",
          lambda: [ln.strip() for ln in format_report(compare_weeks(edge, "2026-W45"), "2026-W45")
                   .splitlines() if " verify " in ln],
          ["OK           verify — 2026-W44 1000s (n=3) -> 2026-W45 1249.5s (n=4), +24.9%"])
    check("pct_text truncates toward zero, at a fall and an exact rise",
          lambda: (pct_text(300, 100), pct_text(100, 125)), ("-66.6%", "+25.0%"))

    # --- the FETCH, through an injected gh: the wiring from PR list to rows
    gh_calls: list[list[str]] = []
    timeouts: list[float] = []
    now = [0.0]

    def fake_gh(prs, runs_by_sha, jobs_by_run, notes=None, step=0.0, short=()):
        def gh(args, timeout):
            gh_calls.append(list(args))
            timeouts.append(timeout)
            now[0] += step
            if args[0] == "repo":
                return json.dumps({"nameWithOwner": "o/r"})
            if args[0] == "pr":
                return json.dumps(prs)
            path = args[1]
            if path.endswith("/annotations"):
                return json.dumps((notes or {})[int(path.split("/check-runs/")[1].split("/")[0])])
            if "head_sha=" in path:
                wr = runs_by_sha[path.split("head_sha=")[1].split("&")[0]]
                return json.dumps({"total_count": len(wr) + ("runs" in short), "workflow_runs": wr})
            js = jobs_by_run[int(path.split("/runs/")[1].split("/")[0])]
            return json.dumps({"total_count": len(js) + ("jobs" in short), "jobs": js})
        return gh

    pr543 = {"number": 543, "headRefOid": "abc", "mergedAt": "2026-11-08T22:11:59Z"}
    pr544 = {"number": 544, "headRefOid": "ghi", "mergedAt": "2026-11-09T05:38:06Z"}
    runs543 = {"abc": [dict(runs[2], status="completed")],
               "ghi": [{"name": "CI", "head_sha": "ghi", "id": 8, "status": "in_progress"}]}
    gh1 = fake_gh([pr543, pr544], runs543, {6: jobs1, 8: jobs2})

    def fetched(skip=frozenset(), **kw):
        rows, st = fetch("2026-11-01", set(skip), gh=gh1, **kw)
        return sorted({r["pr"] for r in rows}), st

    # ⚠ Every fetch runs INSIDE a case's thunk: a mutant that raises must produce a `[FAIL]` line,
    # never kill the suite before the case that names it is reached.
    check("fetch reads each merged PR's CI run on its head and records its jobs",
          lambda: (fetched()[0], fetched()[1]["recorded"]), ([543], 1))
    def searched(since):
        gh_calls.clear()
        fetch(since, set(), gh=gh1)
        return [c for c in gh_calls if c[0] == "pr"][0][5]
    check("fetch asks gh only for PRs merged on or after --since (R2-F7: at two distinct dates)",
          lambda: (searched("2026-11-01"), searched("2026-10-20")),
          ("merged:>=2026-11-01", "merged:>=2026-10-20"))
    check("...and a run not yet complete is counted, not recorded",
          lambda: fetched()[1]["incomplete"], 1)
    check("...and a PR already in the log is not fetched again",
          lambda: (fetched({(543, "abc")})[1]["skipped_known"],
                   fetched({(543, "abc")})[1]["recorded"]), (1, 0))

    def timeout_fetch():
        tjobs = [_job("mutation-sweep (1)", "2026-11-08T01:05:53Z", "2026-11-08T01:10:53Z"),
                 dict(_job("mutation-sweep (2)", "2026-11-08T01:05:53Z", "2026-11-08T01:35:55Z", "cancelled"),
                      check_run_url="https://api.github.com/repos/o/r/check-runs/77"),
                 dict(_job("verify", "2026-11-08T01:05:53Z", "2026-11-08T01:06:53Z", "cancelled"),
                      check_run_url="https://api.github.com/repos/o/r/check-runs/78")]
        g = fake_gh([pr543], {"abc": [dict(runs[2], status="completed")]}, {6: tjobs},
                    {77: [{"message": "The job has exceeded the maximum execution time of 30m0s"}],
                     78: [{"message": "The operation was canceled."}]})
        rows, _ = fetch("2026-11-05", set(), gh=g)
        return {r["job"]: r["seconds"] for r in rows}
    check("⭐ R1-F1 wiring: fetch reads each cancelled job's annotations — a timeout kill is the "
          "slowest shard, another cancel is dropped",
          timeout_fetch, {"mutation-sweep (1)": 300, "mutation-sweep (2)": 1802,
                          "mutation-sweep [slowest shard]": 1802})

    def budget_run():
        # Each gh call takes 10 s on the fake clock; the budget is 35 s. PR 543 needs two calls
        # (runs, jobs) and ends at 40 s, so PR 544 is unread. Every call's timeout is the budget LEFT.
        now[0] = 0.0
        timeouts.clear()
        g = fake_gh([pr543, pr544], runs543, {6: jobs1, 8: jobs2}, step=10.0)
        _, st = fetch("2026-11-01", set(), gh=g, budget_s=35, clock=lambda: now[0])
        return st["recorded"], st["unread"], timeouts
    check("⭐ R1-F8: every gh call is bounded by the budget left, and an exhausted budget leaves "
          "the PR unread, never silently dropped", budget_run, (1, 1, [35, 25, 15, 5]))

    def refused(prs, short=()):
        try:
            fetch("2026-11-01", set(), gh=fake_gh(prs, runs543, {6: jobs1, 8: jobs2}, short=short))
        except CannotRun as exc:
            return str(exc).split(",")[0].split(" is ")[0]
        return "read"
    check("R1-F9: a PR list as long as its --limit may be truncated, and is refused",
          lambda: refused([dict(pr543, number=n) for n in range(PR_LIMIT)]),
          f"`gh pr list` returned {PR_LIMIT} PRs")
    check("R1-F9: a jobs page smaller than its total_count is refused",
          lambda: refused([pr543], ("jobs",)), "the jobs list of run 6")
    check("R1-F9: a runs page smaller than its total_count is refused",
          lambda: refused([pr543], ("runs",)), "the runs list for abc")
    check("...and whole pages are read", lambda: refused([pr543]), "read")

    def broken_gh(args, timeout):
        raise CannotRun("`gh api` exited 1: HTTP 401")

    def rec(gh, since="2026-11-01", **kw):
        with tempfile.TemporaryDirectory() as td:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = record_main(pathlib.Path(td) / "log.jsonl", since, gh=gh, **kw)
            return rc, buf.getvalue()
    check("a gh failure while recording is rc 2 and says NOT RECORDED",
          lambda: (lambda r: (r[0], "TREAT THIS AS NOT RECORDED" in r[1]))(rec(broken_gh)), (CANNOT_RUN, True))
    check("0 merged PRs parsed is rc 2 (nothing parsed), never a quiet success",
          lambda: (lambda r: (r[0], "nothing parsed: 0 merged PRs since 2026-10-15" in r[1]))(
              rec(fake_gh([], {}, {}), "2026-10-15")), (CANNOT_RUN, True))
    def partial():
        now[0] = 0.0
        g = fake_gh([pr543, pr544], runs543, {6: jobs1, 8: jobs2}, step=10.0)
        return rec(g, budget_s=35, clock=lambda: now[0])
    check("a record cut short by the budget is rc 2 and says PARTIAL",
          lambda: (lambda r: (r[0], "PARTIAL — the 35s budget ran out with 1 PR(s) unread" in r[1]))(partial()),
          (CANNOT_RUN, True))
    check("...and a budget spent before the PRs are even listed is rc 2, NOT RECORDED",
          lambda: (lambda r: (r[0], "budget ran out before the merged PRs were listed" in r[1]))(
              rec(gh1, budget_s=-1)), (CANNOT_RUN, True))
    renamed = fake_gh([pr543, pr544], {"abc": [dict(runs[2], name="CI v2", status="completed")],
                                       "ghi": [dict(runs543["ghi"][0], name="CI v2")]}, {})
    check("⭐ R1-F2: PRs listed but NONE recorded (the CI workflow renamed) is rc 2, never rc 0",
          lambda: (lambda r: (r[0], "nothing recorded: 2 PR(s) needed reading" in r[1]))(rec(renamed)),
          (CANNOT_RUN, True))
    check("R1-F4: an unexpected gh payload shape (a PR without mergedAt) is rc 2, never a crash",
          lambda: (lambda r: (r[0], "unexpected gh answer (KeyError" in r[1]))(
              rec(fake_gh([{"number": 1, "headRefOid": "x"}, pr543], runs543, {6: jobs1}))),
          (CANNOT_RUN, True))

    # --- r2: a PR is a SNAPSHOT — recorded whole, validated on read, retried until complete
    jobs_full = [_job("verify", "2026-11-08T21:41:42Z", "2026-11-08T21:46:29Z"),
                 _job("mutation-sweep (1)", "2026-11-08T21:41:00Z", "2026-11-08T21:51:00Z"),
                 _job("mutation-sweep (2)", "2026-11-08T21:41:00Z", "2026-11-08T21:56:30Z")]
    full = job_rows(543, "abc", pr543["mergedAt"], jobs_full, 6, 2)
    runs_a2 = {"abc": [dict(runs[2], status="completed", run_attempt=2)]}

    def r4b(jobs):
        rs = job_rows(11, "u", "2026-11-08T02:00:00Z", jobs)
        return sorted(r["job"] for r in rs), rs[0]["unmeasured"] if rs else None
    check("⭐ R2-F4: a timed-out shard with NO completed_at leaves its group unknown — no survivor-only "
          "max — and both are listed unmeasured; at a second input, a success with no started_at",
          lambda: (r4b([_job("sweep (1)", "2026-11-08T01:00:00Z", "2026-11-08T01:01:00Z"),
                        dict(_job("sweep (2)", "2026-11-08T01:00:00Z", None, "cancelled"), timed_out=True)]),
                   r4b([_job("b (1)", "2026-11-08T01:00:00Z", "2026-11-08T01:09:00Z"),
                        _job("b (2)", None, "2026-11-08T01:02:00Z"), _job("lint", None, None, "skipped")])),
          ((["sweep (1)"], ["sweep (2)", "sweep [slowest shard]"]),
           (["b (1)"], ["b (2)", "b [slowest shard]"])))

    def states():
        inc = job_rows(1, "i", "2026-11-04T00:00:00Z", jobs4)          # a shard cancelled -> incomplete
        dis = [dict(full[0], run=99)] + full[1:]                        # rows disagree on the run
        dup = [dict(full[0], n_rows=2), dict(full[0], n_rows=2)]
        dup = [dict(r, sha="dup") for r in dup]                         # a job repeated
        return (snapshot_states(full + inc + [dict(r, sha="cut") for r in full[:1]]
                                + [dict(r, sha="dis") for r in dis] + dup),
                snapshot_states(full[:2]))
    check("⭐ R2-F2: snapshot_states — whole and timed is complete, an unmeasured job is incomplete, "
          "and a short, disagreeing or repeated snapshot is TORN (at a second input, 2 of 4 rows)",
          states, ({(543, "abc"): "complete", (1, "i"): "incomplete", (543, "cut"): "torn",
                    (543, "dis"): "torn", (543, "dup"): "torn"}, {(543, "abc"): "torn"}))

    def retry():
        # The log holds ONLY `verify` for PR 543 — its sweep shard was cancelled — and GitHub now
        # offers a newer attempt with the sweep. The record must fetch it and REPLACE the snapshot.
        with tempfile.TemporaryDirectory() as td:
            lp = pathlib.Path(td) / "log.jsonl"
            append_log(lp, job_rows(543, "abc", pr543["mergedAt"],
                                    [jobs_full[0], dict(jobs_full[1], conclusion="cancelled")], 6, 1))
            gh_calls.clear()
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = record_main(lp, "2026-11-01", gh=fake_gh([pr543], runs_a2, {6: jobs_full}))
            rows = read_log(lp)
            return (rc, sum(c[0] == "api" for c in gh_calls) > 0,
                    sorted({(r["run"], r["attempt"]) for r in rows}), sorted(r["job"] for r in rows))
    check("⭐ R2-F2: a logged snapshot with an unmeasured job is fetched again and REPLACED by the "
          "newer attempt, never treated as known", retry,
          (NO_RISE, True, [(6, 2)], ["mutation-sweep (1)", "mutation-sweep (2)",
                                     "mutation-sweep [slowest shard]", "verify"]))

    def torn():
        with tempfile.TemporaryDirectory() as td:
            lp = pathlib.Path(td) / "log.jsonl"
            lp.write_text(json.dumps(full[0], sort_keys=True) + "\n")   # 1 of 4 rows: interrupted
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc_rep = report_main(lp, "2026-W45")
                rc_rec = record_main(lp, "2026-11-01", gh=fake_gh([pr543], runs_a2, {6: jobs_full}))
            return (rc_rep, "holds a TORN snapshot in ['2026-W44', '2026-W45']: PR 543" in buf.getvalue(),
                    rc_rec, _canon(read_log(lp)) == _canon(full))
    check("⭐ R2-F2: a TORN snapshot in the compared weeks is CANNOT RUN for the report, and the next "
          "record repairs it whole", torn, (CANNOT_RUN, True, NO_RISE, True))

    def mixed():
        nci = {"number": 545, "headRefOid": "nnn", "mergedAt": "2026-11-09T06:00:00Z"}
        out = []
        for g in (gh1, fake_gh([pr543, nci], dict(runs543, nnn=[]), {6: jobs1})):
            with tempfile.TemporaryDirectory() as td:
                lp = pathlib.Path(td) / "log.jsonl"
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    rc = record_main(lp, "2026-11-01", gh=g)
                line = [ln for ln in buf.getvalue().splitlines() if ln.startswith("CANNOT RUN")]
                out.append((rc, line[0].split(" (")[0] if line else None, len(read_log(lp))))
        return out
    check("⭐ R2-F1: ONE recorded PR does not hide another that was not (a run not complete; at a "
          "second input, no CI run) — rc 2, and what WAS measured is still logged", mixed,
          [(CANNOT_RUN, "CANNOT RUN — 1 PR(s) not recorded", len(r1))] * 2)

    def gap_status(week_day):
        gap = [dict(_rows("lint", week_day, [5], 70)[0], unmeasured=["verify"])]
        v = {v["job"]: v for v in compare_weeks(rise1 + gap, "2026-W45")}["verify"]
        return v["status"], v["why"]
    check("⭐ R2-F1: a job a snapshot of either week ran but could not time is NOT MEASURED, even "
          "over a measured rise (in the evaluated week; at a second input, the previous week)",
          lambda: (gap_status(B), gap_status(A)),
          (("NOT MEASURED", "PR 70's run did not measure it"),) * 2)

    check("⭐ R2-F3: a completed run whose jobs list is EMPTY records nothing, and is rc 2",
          lambda: (lambda r: (r[0], "1 with no job measurable" in r[1]))(
              rec(fake_gh([pr543], runs_a2, {6: []}))), (CANNOT_RUN, True))

    def race():
        import threading
        with tempfile.TemporaryDirectory() as td:
            lp = pathlib.Path(td) / "race.jsonl"
            read_done, go, out = threading.Event(), threading.Event(), {}

            def first():
                out["a"] = append_log(lp, r2, after_read=lambda: (read_done.set(), go.wait(10)))

            def second():
                out["b"] = append_log(lp, r2)
            t1 = threading.Thread(target=first)
            t1.start()
            read_done.wait(10)
            t2 = threading.Thread(target=second)
            t2.start()
            time.sleep(0.5)    # unlocked, the second writer reads the still-empty log in this window
            go.set()
            t1.join(20)
            t2.join(20)
            return out.get("a"), out.get("b"), len(read_log(lp))
    check("⭐ R2-F5: two writers of one snapshot, the second reading while the first holds its read, "
          "write it ONCE — the read -> check -> write is locked", race, (len(r2), 0, len(r2)))

    check("⭐ R2-F6: a row whose week is not its merge's ISO week is refused, at two inputs",
          lambda: [check_raise(lambda x=x: parse_log(json.dumps(x)))
                   for x in (dict(good, merged_at="2026-09-01T00:00:00Z"), dict(good, week="2026-W44"))],
          ["log line 1 has week 2026-W45, but its merge is in 2026-W36",
           "log line 1 has week 2026-W44, but its merge is in 2026-W45"])
    check("...and an unmeasured job that is not a string is refused",
          lambda: check_raise(lambda: parse_log(json.dumps(dict(good, unmeasured=[1])))),
          "log line 1 has an unmeasured job that is not a string")

    # --- the WIRING: report_main over a log file, the path a caller takes
    T46, T41 = _dt.date(2026, 11, 10), _dt.date(2026, 10, 6)   # in W46 and W41
    with tempfile.TemporaryDirectory() as td:
        lp = pathlib.Path(td) / "log.jsonl"
        append_log(lp, rise1 + flat2)

        def rep(week, n=MIN_SAMPLES, today=T46, path=lp):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = report_main(path, week, n, today)
            return rc, buf.getvalue()
        check("⭐ report_main over a logged rise exits 1 and WARNs for the last COMPLETE week (W45)",
              lambda: (lambda r: (r[0], "WARN: 1 job(s) rose 25% or more in 2026-W45" in r[1]))(rep(None)),
              (RISE_FOUND, True))
        check("⭐ R1-F3: ...at a second today, the default is THAT today's last complete week (W40)",
              lambda: (lambda r: (r[0], "no measured job rose 25% or more in 2026-W40" in r[1]))(
                  rep(None, today=T41)), (NO_RISE, True))
        check("⭐ ...and with --week it evaluates THAT week: W40's 24% is no rise, rc 0",
              lambda: (lambda r: (r[0], "no measured job rose 25% or more in 2026-W40" in r[1]))(
                  rep("2026-W40")), (NO_RISE, True))
        check("report_main passes its minimum to the rule: at min 4, W45's 3 samples are NOT MEASURED",
              lambda: (lambda r: (r[0], "min 4 samples per week" in r[1]))(rep("2026-W45", 4)),
              (CANNOT_RUN, True))
        check("⭐ R1-F2: a STALE log (no merge in the evaluated week) is rc 2 and names its latest week",
              lambda: (lambda r: (r[0], "holds no merge in 2026-W48; its latest merge is in 2026-W45"
                                  in r[1]))(rep(None, today=_dt.date(2026, 12, 1))), (CANNOT_RUN, True))
        check("an empty or absent log is rc 2, never rc 0",
              lambda: (lambda r: (r[0], "holds no rows" in r[1]))(rep(None, path=pathlib.Path(td) / "absent.jsonl")),
              (CANNOT_RUN, True))

        def cli(argv, gh=broken_gh, today=T46):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = main(argv, gh=gh, today=today)
            return rc, buf.getvalue()
        check("⭐ the CLI's --report path reaches the rule: rc 1 and the WARN line",
              lambda: (lambda r: (r[0], "WARN: 1 job(s) rose 25% or more in 2026-W45" in r[1]))(
                  cli(["--report", "--log", str(lp), "--week", "2026-W45"])), (RISE_FOUND, True))
        check("R1-F4: --week 2025-W53 (no such week) is rc 2 with a reason, never a crash's rc 1",
              lambda: (lambda r: (r[0], "is not a real ISO week" in r[1]))(
                  cli(["--report", "--log", str(lp), "--week", "2025-W53"])), (CANNOT_RUN, True))
        check("R1-F4: ANY uncaught error in the CLI is rc 2, never rc 1 (the RISE code)",
              lambda: (lambda r: (r[0], "CANNOT RUN — an unexpected error: TypeError" in r[1]))(
                  cli(["--report", "--log", str(lp)], today="not-a-date")), (CANNOT_RUN, True))

        # R1-F6: record + report through main with an injected gh — the combined rc.
        known = fake_gh([pr543], runs543, {6: jobs1})
        # The record half is rc 2 here because its budget is spent (`--budget-s -1`); the same rc as PARTIAL.
        check("⭐ R1-F6: a record that is rc 2 beside a measured RISE is rc 1 — the rise is not masked",
              lambda: cli(["--log", str(lp), "--budget-s", "-1"], gh=known)[0], RISE_FOUND)
        lp2 = pathlib.Path(td) / "flat.jsonl"
        append_log(lp2, flat1)
        check("⭐ R1-F6: a record that is rc 2 beside a report of no rise is rc 2, never rc 0",
              lambda: cli(["--log", str(lp2), "--budget-s", "-1"], gh=known)[0], CANNOT_RUN)
        append_log(lp2, job_rows(543, "abc", "2026-11-08T22:11:59Z", jobs1))
        check("...and a complete record beside a report of no rise is rc 0",
              lambda: cli(["--log", str(lp2)], gh=known)[0], NO_RISE)
        check("combine_rc: RISE dominates, then CANNOT RUN from either half, at every pair",
              lambda: [combine_rc(0, 0), combine_rc(0, 1), combine_rc(0, 2),
                       combine_rc(2, 0), combine_rc(2, 1), combine_rc(2, 2)], [0, 1, 2, 2, 1, 2])

    print(f"{ok}/{ok + fail} self-test cases passed")
    drift = _count_drift(ok + fail)
    if drift:
        print(f"  {drift}")
        return 1
    return 1 if fail else 0


def _count_drift(actual: int) -> str | None:
    """The declared `--self-test  # N cases` against the cases that ran (`check-plan-code.count_drift`'s rule)."""
    m = re.search(r"--self-test\s+#\s*(\d+) cases", __doc__ or "")
    if not m:
        return "CANNOT RUN — the docstring no longer declares a case count."
    if int(m.group(1)) != actual:
        return f"[DRIFT] the docstring declares {m.group(1)} cases; the suite ran {actual}"
    return None


def main(argv: list[str] | None = None, gh=_gh, today: _dt.date | None = None) -> int:
    """The CLI. `gh` and `today` are injectable so the record + report path is cased offline."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--record", action="store_true", help="fetch and append only")
    ap.add_argument("--report", action="store_true", help="evaluate the log only")
    ap.add_argument("--since", help="record PRs merged on or after this date (default: 21 days ago)")
    ap.add_argument("--week", help="the ISO week to evaluate, YYYY-Www (default: the last complete week)")
    ap.add_argument("--min-samples", type=int, default=MIN_SAMPLES)
    ap.add_argument("--budget-s", type=float, default=DEFAULT_BUDGET_S)
    ap.add_argument("--log", type=pathlib.Path)
    a = ap.parse_args(argv)
    if a.self_test:
        return _self_test()
    # ⚠ Every other path is wrapped: an uncaught exception exits 1, which is the RISE code, so a
    # crash would be filed as a rise by a caller keyed on rc 1 (r1 R1-F4).
    try:
        return _run(a, gh, today)
    except Exception as exc:  # noqa: BLE001 - any crash is CANNOT RUN, never rc 1
        print(f"CANNOT RUN — an unexpected error: {type(exc).__name__}: {exc}. "
              f"TREAT THIS AS NOT MEASURED.")
        return CANNOT_RUN


def _run(a, gh, today: _dt.date | None) -> int:
    if a.week and not valid_week(a.week):
        print(f"CANNOT RUN — --week {a.week!r} is not a real ISO week (YYYY-Www).")
        return CANNOT_RUN
    log = a.log or default_log()
    since = a.since or ((today or utc_today()) - _dt.timedelta(days=21)).isoformat()
    do_record = a.record or not a.report
    do_report = a.report or not a.record
    rc_rec = record_main(log, since, gh=gh, budget_s=a.budget_s) if do_record else NO_RISE
    if not do_report:
        return rc_rec
    rc_rep = report_main(log, a.week, a.min_samples, today)
    return combine_rc(rc_rec, rc_rep)


if __name__ == "__main__":
    sys.exit(main())
