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
  * WARN — group the log by the ISO week of each PR's MERGE date. For each job and job group,
    compare the evaluated week's median with the previous ISO week's, and WARN when it rose 25% or
    more. A job with fewer than `MIN_SAMPLES` rows in EITHER week is NOT MEASURED, never "fine".

⚠ WHAT A DURATION HERE IS, AND IS NOT. `started_at` -> `completed_at` is a job's EXECUTION time. It
excludes the time a job waited in the queue for a runner, so the slowest shard is a floor on the
run's wall-clock, not the wall-clock itself. Skipped and cancelled jobs are not recorded: a skipped
job takes ~0 s and would drag a median down for a reason that is not speed.

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
    2  CANNOT RUN — no `gh`, no network, nothing parsed, a malformed log, the time budget ran out
       before every PR was read (re-run: the append is idempotent), or NO job could be measured

NO-CALLER: slice 1 builds the instrument and its rule; which loop runs it weekly (a scheduled CI job
that opens an issue on rc 1, or the SessionStart path) is backlog #584, filed with this slice. Until
then the row's FAILS IF ("nothing reports it in that week") is NOT met by this script alone.

Usage:
    python3 scripts/ci-durations.py                      # record the last 21 days, then report
    python3 scripts/ci-durations.py --record --since 2026-10-26
    python3 scripts/ci-durations.py --report [--week 2026-W45]
    python3 scripts/ci-durations.py --self-test  # 55 cases
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
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
GH_TIMEOUT_S = 60


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


def job_rows(pr: int, sha: str, merged_at: str, jobs: list[dict]) -> list[dict]:
    """PURE. The GitHub jobs list of one run -> one log row per recorded job, plus group rows.

    A job is recorded only if it concluded `success` or `failure` and has both timestamps. Each
    matrix group (`base (N)`) gains ONE derived row holding its slowest shard's seconds.
    """
    rows = []
    for j in jobs:
        if j.get("conclusion") not in RECORDED_CONCLUSIONS:
            continue
        if not j.get("started_at") or not j.get("completed_at"):
            continue
        secs = int((_ts(j["completed_at"]) - _ts(j["started_at"])).total_seconds())
        rows.append({"pr": pr, "sha": sha, "merged_at": merged_at, "week": iso_week(merged_at),
                     "job": j["name"], "seconds": secs, "derived": False})
    groups: dict[str, int] = {}
    for r in rows:
        m = MATRIX.match(r["job"])
        if m:
            base = m.group("base")
            groups[base] = max(groups.get(base, -1), r["seconds"])
    for base, secs in sorted(groups.items()):
        rows.append({"pr": pr, "sha": sha, "merged_at": merged_at, "week": iso_week(merged_at),
                     "job": base + GROUP_SUFFIX, "seconds": secs, "derived": True})
    return rows


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


def pick_ci_run(runs: list[dict], sha: str) -> dict | None:
    """PURE. The newest `CI` run on exactly `sha`, or None. Another workflow is never chosen."""
    mine = [r for r in runs if r.get("name") == WORKFLOW and r.get("head_sha") == sha]
    if not mine:
        return None
    return max(mine, key=lambda r: (r.get("created_at") or "", r.get("id") or 0))


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

    status is RISE, OK, or NOT MEASURED — the last whenever either week has fewer than
    `min_samples` rows for the job, or the previous median is zero (no percentage exists).
    """
    prev = previous_week(week)
    cur_s, prev_s = samples_by_job(rows, week), samples_by_job(rows, prev)
    out = []
    for job in sorted(set(cur_s) | set(prev_s)):
        c, p = cur_s.get(job, []), prev_s.get(job, [])
        v = {"job": job, "week": week, "prev_week": prev, "n_cur": len(c), "n_prev": len(p),
             "cur": statistics.median(c) if c else None,
             "prev": statistics.median(p) if p else None}
        if len(c) < min_samples or len(p) < min_samples:
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
            pct = round((v["cur"] - v["prev"]) / v["prev"] * 100)
            lines.append(f"{head} — {meds}, {pct:+d}%")
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
    """PURE. JSON-lines -> rows. A malformed or incomplete line is CANNOT RUN, never skipped."""
    rows = []
    for i, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CannotRun(f"log line {i} is not JSON ({exc})") from None
        missing = [k for k in ("pr", "sha", "week", "job", "seconds") if k not in r]
        if missing:
            raise CannotRun(f"log line {i} lacks {', '.join(missing)}")
        rows.append(r)
    return rows


def latest_week(rows: list[dict]) -> str:
    """PURE. The ISO week of the latest merge in the log."""
    return iso_week(max(r["merged_at"] for r in rows))


# ---------------------------------------------------------------- file I/O: thin, temp-dir tested

def read_log(path: pathlib.Path) -> list[dict]:
    return parse_log(path.read_text()) if path.exists() else []


def append_log(path: pathlib.Path, fetched: list[dict]) -> int:
    """Append the rows not already in the log. -> how many were written."""
    add = new_rows(read_log(path), fetched)
    if add:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as fh:
            for r in add:
                fh.write(json.dumps(r, sort_keys=True) + "\n")
    return len(add)


def report_main(path: pathlib.Path, week: str | None, min_samples: int = MIN_SAMPLES) -> int:
    """Read the log, evaluate one week against the week before it, print, return the rc."""
    try:
        rows = read_log(path)
    except CannotRun as exc:
        print(f"CANNOT RUN — {path}: {exc}. TREAT THIS AS NOT MEASURED.")
        return CANNOT_RUN
    if not rows:
        print(f"CANNOT RUN — the log {path} holds no rows. Run --record first. "
              f"TREAT THIS AS NOT MEASURED.")
        return CANNOT_RUN
    wk = week or latest_week(rows)
    verdicts = compare_weeks(rows, wk, min_samples)
    print(format_report(verdicts, wk, min_samples))
    return verdict_rc(verdicts)


# ---------------------------------------------------------------- the FETCH: read-only `gh`

def _gh(args: list[str]) -> str:
    """Run read-only `gh`. -> stdout. Any failure is CannotRun, never an empty answer."""
    if not shutil.which("gh"):
        raise CannotRun("`gh` is not on PATH")
    try:
        p = subprocess.run(["gh", *args], cwd=ROOT, capture_output=True, text=True,
                           timeout=GH_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        raise CannotRun(f"`gh {' '.join(args[:2])}` timed out after {GH_TIMEOUT_S}s") from None
    if p.returncode != 0:
        raise CannotRun(f"`gh {' '.join(args[:2])}` exited {p.returncode}: "
                        f"{p.stderr.strip()[:300]}")
    return p.stdout


def _gh_json(gh, args: list[str]):
    out = gh(args)
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        raise CannotRun(f"`gh {' '.join(args[:2])}` returned no JSON: {out[:200]!r}") from None


def fetch(since: str, skip: set[tuple], gh=_gh, budget_s: float = DEFAULT_BUDGET_S,
          clock=time.monotonic) -> tuple[list[dict], dict]:
    """Read every PR merged on or after `since` -> (rows, stats). `gh` is injectable for tests.

    A PR whose (number, head sha) is in `skip` is not fetched again. When the time budget runs
    out, the remaining PRs are counted in stats["unread"] and the caller must say PARTIAL.
    """
    t0 = clock()
    repo = _gh_json(gh, ["repo", "view", "--json", "nameWithOwner"]).get("nameWithOwner")
    if not repo:
        raise CannotRun("`gh repo view` named no repository")
    prs = _gh_json(gh, ["pr", "list", "--state", "merged", "--search", f"merged:>={since}",
                        "--limit", "500", "--json", "number,headRefOid,mergedAt"])
    if not isinstance(prs, list):
        raise CannotRun("`gh pr list` did not return a list")
    stats = {"prs": len(prs), "skipped_known": 0, "no_ci_run": 0, "incomplete": 0,
             "recorded": 0, "unread": 0}
    rows: list[dict] = []
    for i, pr in enumerate(sorted(prs, key=lambda p: p["mergedAt"])):
        if (pr["number"], pr["headRefOid"]) in skip:
            stats["skipped_known"] += 1
            continue
        if clock() - t0 > budget_s:
            stats["unread"] = len(prs) - i
            break
        sha = pr["headRefOid"]
        runs = _gh_json(gh, ["api", f"repos/{repo}/actions/runs?head_sha={sha}&per_page=50"])
        run = pick_ci_run(runs.get("workflow_runs", []), sha)
        if run is None:
            stats["no_ci_run"] += 1
            continue
        if run.get("status") != "completed":
            stats["incomplete"] += 1
            continue
        jobs = _gh_json(gh, ["api", f"repos/{repo}/actions/runs/{run['id']}/jobs"
                                    f"?filter=latest&per_page=100"])
        rows.extend(job_rows(pr["number"], sha, pr["mergedAt"], jobs.get("jobs", [])))
        stats["recorded"] += 1
    return rows, stats


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


def record_main(path: pathlib.Path, since: str, gh=_gh, budget_s: float = DEFAULT_BUDGET_S) -> int:
    try:
        known = {(r["pr"], r["sha"]) for r in read_log(path)}
        rows, st = fetch(since, known, gh=gh, budget_s=budget_s)
    except CannotRun as exc:
        print(f"CANNOT RUN — {exc}. TREAT THIS AS NOT RECORDED.")
        return CANNOT_RUN
    if st["prs"] == 0:
        print(f"CANNOT RUN — nothing parsed: 0 merged PRs since {since}. "
              f"TREAT THIS AS NOT RECORDED.")
        return CANNOT_RUN
    added = append_log(path, rows)
    print(f"recorded {st['recorded']} PR(s), {added} new row(s) -> {path}; "
          f"{st['skipped_known']} already in the log, {st['no_ci_run']} without a CI run on "
          f"their head, {st['incomplete']} with the run not yet complete "
          f"({st['prs']} merged since {since}).")
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
    """Fixture: one row per duration, on distinct PRs, all merged on `week_day`."""
    at = f"{week_day}T12:00:00Z"
    return [{"pr": pr0 + i, "sha": f"s{pr0 + i}", "merged_at": at, "week": iso_week(at),
             "job": job, "seconds": s, "derived": False} for i, s in enumerate(secs)]


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
                   and "mutation-sweep [slowest shard] — 2026-W39 600s (n=3) -> 2026-W40 800s (n=3), +33%"
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

    # --- the log parser refuses, never skips
    check("a malformed log line is CANNOT RUN, not skipped",
          lambda: parse_log('{"pr": 1}\nnot json\n'), "raised CannotRun: log line 1 lacks sha, week, job, seconds")
    check("...and a line that is not JSON names its line number",
          lambda: str(parse_log('\n{"pr": 1, "sha": "a", "week": "w", "job": "j", "seconds": 1}\n{oops')[0]),
          "raised CannotRun: log line 3 is not JSON (Expecting property name enclosed in double quotes: line 1 column 2 (char 1))")

    # --- the FETCH, through an injected gh: the wiring from PR list to rows
    gh_calls: list[list[str]] = []

    def fake_gh(prs, runs_by_sha, jobs_by_run):
        def gh(args):
            gh_calls.append(list(args))
            if args[0] == "repo":
                return json.dumps({"nameWithOwner": "o/r"})
            if args[0] == "pr":
                return json.dumps(prs)
            path = args[1]
            if "head_sha=" in path:
                return json.dumps({"workflow_runs": runs_by_sha[path.split("head_sha=")[1].split("&")[0]]})
            return json.dumps({"jobs": jobs_by_run[int(path.split("/runs/")[1].split("/")[0])]})
        return gh

    gh1 = fake_gh([{"number": 543, "headRefOid": "abc", "mergedAt": "2026-11-08T22:11:59Z"},
                   {"number": 544, "headRefOid": "ghi", "mergedAt": "2026-11-09T05:38:06Z"}],
                  {"abc": [dict(runs[2], status="completed")],
                   "ghi": [{"name": "CI", "head_sha": "ghi", "id": 8, "status": "in_progress"}]},
                  {6: jobs1, 8: jobs2})

    def fetched(skip=frozenset(), **kw):
        rows, st = fetch("2026-11-01", set(skip), gh=gh1, **kw)
        return sorted({r["pr"] for r in rows}), st

    # ⚠ Every fetch runs INSIDE a case's thunk: a mutant that raises must produce a `[FAIL]` line,
    # never kill the suite before the case that names it is reached.
    check("fetch reads each merged PR's CI run on its head and records its jobs",
          lambda: (fetched()[0], fetched()[1]["recorded"]), ([543], 1))
    check("fetch asks gh only for PRs merged on or after --since",
          lambda: (gh_calls.clear(), fetched(), [c for c in gh_calls if c[0] == "pr"][0][5])[2],
          "merged:>=2026-11-01")
    check("...and a run not yet complete is counted, not recorded",
          lambda: fetched()[1]["incomplete"], 1)
    check("...and a PR already in the log is not fetched again",
          lambda: (fetched({(543, "abc")})[1]["skipped_known"],
                   fetched({(543, "abc")})[1]["recorded"]), (1, 0))

    def budget_run():
        ticks = iter([0, 0, 500, 500, 500])
        st = fetched(budget_s=100, clock=lambda: next(ticks))[1]
        return st["recorded"], st["unread"]
    check("an exhausted time budget leaves PRs counted as unread, never silently dropped",
          budget_run, (1, 1))

    def broken_gh(args):
        raise CannotRun("`gh api` exited 1: HTTP 401")
    with tempfile.TemporaryDirectory() as td:
        lp = pathlib.Path(td) / "log.jsonl"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc_b = record_main(lp, "2026-11-01", gh=broken_gh)
        check("a gh failure while recording is rc 2 and says NOT RECORDED",
              lambda: (rc_b, "TREAT THIS AS NOT RECORDED" in buf.getvalue()), (CANNOT_RUN, True))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc_e = record_main(lp, "2026-10-15", gh=fake_gh([], {}, {}))
        check("0 merged PRs parsed is rc 2 (nothing parsed), never a quiet success",
              lambda: (rc_e, "nothing parsed: 0 merged PRs since 2026-10-15" in buf.getvalue()),
              (CANNOT_RUN, True))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc_p = record_main(pathlib.Path(td) / "p.jsonl", "2026-11-01", gh=gh1, budget_s=-1)
        check("a record cut short by the budget is rc 2 and says PARTIAL",
              lambda: (rc_p, "PARTIAL" in buf.getvalue()), (CANNOT_RUN, True))

    # --- the WIRING: report_main over a log file, the path a caller takes
    with tempfile.TemporaryDirectory() as td:
        lp = pathlib.Path(td) / "log.jsonl"
        append_log(lp, rise1 + flat2)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc_w = report_main(lp, None)
        check("⭐ report_main over a logged rise exits 1 and WARNs for the LATEST week (W45)",
              lambda: (rc_w, "WARN: 1 job(s) rose 25% or more in 2026-W45" in buf.getvalue()),
              (RISE_FOUND, True))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc_w2 = report_main(lp, "2026-W40")
        check("⭐ ...and with --week it evaluates THAT week: W40's 24% is no rise, rc 0",
              lambda: (rc_w2, "no measured job rose 25% or more in 2026-W40" in buf.getvalue()),
              (NO_RISE, True))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc_n = report_main(lp, "2026-W45", 4)
        check("report_main passes its minimum to the rule: at min 4, W45's 3 samples are NOT MEASURED",
              lambda: (rc_n, "min 4 samples per week" in buf.getvalue()), (CANNOT_RUN, True))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc_m = report_main(pathlib.Path(td) / "absent.jsonl", None)
        check("an empty or absent log is rc 2, never rc 0",
              lambda: (rc_m, "holds no rows" in buf.getvalue()), (CANNOT_RUN, True))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc_cli = main(["--report", "--log", str(lp), "--week", "2026-W45"])
        check("⭐ the CLI's --report path reaches the rule: rc 1 and the WARN line",
              lambda: (rc_cli, "WARN: 1 job(s) rose 25% or more in 2026-W45" in buf.getvalue()),
              (RISE_FOUND, True))

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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--record", action="store_true", help="fetch and append only")
    ap.add_argument("--report", action="store_true", help="evaluate the log only")
    ap.add_argument("--since", help="record PRs merged on or after this date (default: 21 days ago)")
    ap.add_argument("--week", help="the ISO week to evaluate, YYYY-Www (default: the latest merge's)")
    ap.add_argument("--min-samples", type=int, default=MIN_SAMPLES)
    ap.add_argument("--budget-s", type=float, default=DEFAULT_BUDGET_S)
    ap.add_argument("--log", type=pathlib.Path)
    a = ap.parse_args(argv)
    if a.self_test:
        return _self_test()
    log = a.log or default_log()
    since = a.since or (_dt.date.today() - _dt.timedelta(days=21)).isoformat()
    if a.week and not re.fullmatch(r"\d{4}-W\d{2}", a.week):
        print(f"CANNOT RUN — --week {a.week!r} is not YYYY-Www.")
        return CANNOT_RUN
    do_record = a.record or not a.report
    do_report = a.report or not a.record
    rc_rec = record_main(log, since, budget_s=a.budget_s) if do_record else NO_RISE
    if not do_report:
        return rc_rec
    rc_rep = report_main(log, a.week, a.min_samples)
    return CANNOT_RUN if CANNOT_RUN in (rc_rec, rc_rep) else rc_rep


if __name__ == "__main__":
    sys.exit(main())
