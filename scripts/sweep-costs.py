#!/usr/bin/env python3
"""Build `scripts/sweep-costs.json` — the mutation sweep's per-target COST TABLE — from CI shard logs.

backlog #588. `check-plan-code.py --mutate --shard I/N` cuts the sorted mutation list into N contiguous
runs of equal ESTIMATED cost (`sweep_partition`). The estimate is this table: per target, the median
control seconds, the median re-control seconds and the mean seconds per mutation, measured from the
progress lines of real CI shard logs, plus two defaults for a target the table has never seen. ⟳ r1
(Claude M1): the defaults are the 90th percentile OVER TARGETS (nearest rank) of the per-mutation mean
and of control + re-control — a median was the optimistic guess for exactly the target that matters, a
big suite that is new or was renamed. check-plan-code also refuses a table that no longer covers the
manifest (`cost_coverage`), so the defaults only ever price a small remainder.

usage:
  python3 scripts/sweep-costs.py --run LABEL TREE LOGDIR [--run ...] [--out scripts/sweep-costs.json]
                                 [--predict N]
  python3 scripts/sweep-costs.py --self-test  # 28 cases

  LABEL   names the run in the table's `sources` (e.g. `43662666915@033fe20c`: run id @ commit).
  TREE    a checkout of the repository AT THE RUN'S COMMIT (`git worktree add --detach <dir> <sha>`).
  LOGDIR  that run's shard job logs, one `shard*.log` per job (`gh run view <id> --log` split per job,
          or `gh api repos/<o>/<r>/actions/jobs/<job>/logs`).
  --predict N   print each shard's estimate under the NEW table for the CURRENT tree's manifest.

⛔ ATTRIBUTION IS THE RUN'S OWN. Which mutations a shard held is decided by the partition function of
the tree that ran it — `sweep_shard` with that tree's own table where it exists, else `shard_slice`
(the round-robin of every run before backlog #588) — imported from TREE, never re-implemented here.
So is the text of each progress line: it must equal what that tree's `progress_line` writes for the
expected subject, exactly (⟳ r1, Codex 2 — a prefix match accepted a first character, an empty label
or a bare `…`). A log that does not match that attribution exactly (counts, order, text) is REFUSED,
never averaged: a cost assigned to the wrong target would skew every later partition in silence.
⛔ A RUN IS ITS SHARDS' IDENTITIES (⟳ r1, Codex 1): every index 1..total exactly once, one total, one
event, checked before any row is accumulated — a count let a duplicate stand in for a missing shard.
⛔ ONE SEED: a `schedule` run sweeps every suite under two hash seeds, so its times are not a shard's.
⛔ NEVER WRITES A TABLE check-plan-code WOULD REFUSE (⟳ r1, Codex 3): the output is parsed by that
reader first, so a bad run can never replace a usable table on disk.

Exit: 0 written; 1 a log REFUSED (its reason printed); 2 CANNOT RUN (bad arguments, unreadable input).

NO-CALLER: run by hand when the sweep's shard times drift — it reads downloaded CI logs, which no hook or
workflow step has; `check-plan-code` reads the table it writes, and falls back to round-robin, LOUDLY,
when that table is missing, unusable, or no longer covers the manifest.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import importlib.util
import io
import json
import math
import pathlib
import re
import statistics
import sys

HERE = pathlib.Path(__file__).resolve().parent
TABLE = "scripts/sweep-costs.json"
SCHEMA = 1

# `2026-11-15T01:21:33.2365152Z <body>` — the runner's timestamp, 7 fractional digits, then the line.
LINE = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d+))?Z (.*)$")
PROG = re.compile(r"^\[(\d+)/(\d+)\] (.*)$")
VERDICT = re.compile(r"^(OK|FAIL|NOT MEASURED|CANNOT RUN)\b.*\bmeasured over shard (\d+) of (\d+)")
# The event whose sweep runs more than one hash seed (ci.yml's `--seeds`, backlog #506).
MULTI_SEED_EVENT = "schedule"


class Refused(ValueError):
    """A log that cannot be attributed exactly. Its message is the reason."""


def _secs(stamp: str, frac: "str | None") -> float:
    try:
        t = dt.datetime.fromisoformat(stamp + "+00:00").timestamp()
    except ValueError as exc:   # r1 (Codex 4): `2026-13-15…` matches LINE and is no date
        raise Refused(f"timestamp {stamp!r} is not a date ({exc})") from None
    return t + (float("0." + frac) if frac else 0.0)


# r2 (Codex 3): a count is at most this many ASCII digits. `\d+` bounded the ALPHABET and not the LENGTH, and
# past 4,300 digits `int()` raises a plain ValueError (Python's digit limit) — a crash where a reason was owed.
COUNT_DIGITS = 9


def _count(v: str, what: str) -> int:
    """PURE. A shard count read from a log -> int, else `Refused`. ⛔ THE ONE PLACE A LOG'S DIGITS BECOME AN
    INT: the env block's two counts AND the verdict line's two go through it (r2: the verdict's did not, and
    4,301 digits there crashed the same way). The refusal never echoes an over-long value."""
    if not re.fullmatch(r"[0-9]+", v):
        raise Refused(f"{what} is {v[:40]!r}, not a non-negative integer")
    if len(v) > COUNT_DIGITS:
        raise Refused(f"{what} is {len(v)} digits long, over {COUNT_DIGITS}: not a shard count")
    return int(v)


def _env_count(env: str, key: str) -> int:
    """`KEY: 12` -> 12. r1 (Codex 4): anything but a non-negative integer is a refusal, not a ValueError."""
    return _count(env.split(":", 1)[1].strip(), key)


def parse_log(text: str) -> dict:
    """PURE. One shard job's log -> `{index, total, event, prog: [(t, line)], end, verdict}`.

    `index` is 1-based (the env block's `SHARD_INDEX` is the 0-based `--shard0`). `end` is the verdict
    line's time, so the last re-control has a cost. Raises `Refused` when any of them is missing or
    malformed, when the index is outside the total, when the run swept more than one seed, when the
    verdict is a selection (a PR run sweeps a DIFF-SCOPED subset, so its shards are not the table's
    partition), or when the run did not finish (NOT MEASURED / CANNOT RUN)."""
    idx = tot = end = verdict = event = None
    prog = []
    for raw in text.splitlines():
        m = LINE.match(raw.lstrip("\ufeff"))
        if not m:
            continue
        t, body = _secs(m.group(1), m.group(2)), m.group(3)
        env = body.strip()
        if env.startswith("SHARD_INDEX:") and idx is None:
            idx = _env_count(env, "SHARD_INDEX") + 1
        elif env.startswith("SHARD_TOTAL:") and tot is None:
            tot = _env_count(env, "SHARD_TOTAL")
        elif env.startswith("EVENT:") and event is None:
            event = env.split(":", 1)[1].strip()
        if PROG.match(body) and end is None:
            prog.append((t, body))
            continue
        v = VERDICT.match(body)
        if v and prog and end is None:
            end, verdict = t, body
    if idx is None or tot is None:
        raise Refused("no SHARD_INDEX / SHARD_TOTAL in the job's env block")
    if not 1 <= idx <= tot:   # r1 (Codex 1): index 0 was read by Python's negative indexing as the LAST shard
        raise Refused(f"SHARD_INDEX {idx - 1} is outside 0..{tot - 1} (SHARD_TOTAL {tot})")
    if event is None:
        raise Refused("no EVENT in the job's env block, so the number of hash seeds the run swept is unknown")
    if event == MULTI_SEED_EVENT:   # r1 (Claude M4)
        raise Refused(f"a {event!r} run sweeps every suite under two hash seeds (`--seeds`): its times are "
                      f"not one seed's shard")
    if end is None:
        raise Refused("no verdict line (`OK|FAIL ... measured over shard I of N`) after the progress lines")
    if not verdict.startswith(("OK", "FAIL")):
        raise Refused(f"the shard did not finish: {verdict[:80]}")
    if "DIFF-SCOPED" in verdict or "ONLY" in verdict:
        raise Refused("a SELECTED run (a PR's diff-scoped sweep) is not the full partition")
    vm = VERDICT.match(verdict)
    v_idx, v_tot = _count(vm.group(2), "the verdict's shard"), _count(vm.group(3), "the verdict's total")
    if (v_idx, v_tot) != (idx, tot):
        raise Refused(f"the verdict names shard {vm.group(2)} of {vm.group(3)}, the env {idx} of {tot}")
    return {"index": idx, "total": tot, "event": event, "prog": prog, "end": end, "verdict": verdict}


def attribute(parsed: dict, mine: list, render) -> list:
    """PURE. `(kind, target, seconds)` for every progress line, given the mutations the shard HELD and
    the run tree's own `progress_line` (`render(done, total, label)`).

    The layout is exact: one `control <t>` per touched target in sorted order, then one line per
    mutation `[k/len(mine)]` naming it, then one `re-control <t>` per target — each line EQUAL to what
    `render` writes for it (a long name cut with `…` exactly where `progress_line` cuts it, nowhere
    else). A line's cost is the gap to the next line; the last one's is the gap to the verdict; a
    negative gap is a clock running backwards. Anything else is `Refused` — never skipped, never
    re-ordered to fit."""
    targets = sorted({m["file"] for m in mine})
    prog, n, k = parsed["prog"], len(targets), len(mine)
    if len(prog) != 2 * n + k:
        raise Refused(f"{len(prog)} progress line(s), expected {2 * n + k} "
                      f"({n} control + {k} mutation + {n} re-control)")
    out = []
    for j, (t, body) in enumerate(prog):
        cost = (prog[j + 1][0] if j + 1 < len(prog) else parsed["end"]) - t
        if cost < 0:   # r1 (Codex 3)
            raise Refused(f"line {j + 1}: {body[:60]!r} is followed by a line {-cost:.3f} s EARLIER — the "
                          f"log's clock runs BACKWARDS, so no cost can be read from it")
        if j < n:
            kind, target = "control", targets[j]
            want = render(j + 1, n, f"control {target}")
        elif j < n + k:
            kind, target = "mutation", mine[j - n]["file"]
            want = render(j - n + 1, k, mine[j - n]["name"])
        else:
            kind, target = "recontrol", targets[j - n - k]
            want = render(j - n - k + 1, n, f"re-control {target}")
        if body != want:
            raise Refused(f"line {j + 1}: {body[:80]!r} is not {kind} line {want[:80]!r}")
        out.append((kind, target, cost))
    return out


def _p90(xs: list) -> float:
    """PURE. The NEAREST-RANK 90th percentile: the smallest value with at least 90% of `xs` at or below it."""
    s = sorted(xs)
    return s[max(0, math.ceil(0.9 * len(s)) - 1)]


def build_table(records: list, sources: list) -> dict:
    """PURE. Attributed `(kind, target, seconds)` rows, pooled across every shard of every run -> the
    table. Per target: MEDIAN control, MEDIAN re-control (one sample per shard that touched it — a
    median, since a cold runner's first suite is an outlier), MEAN per-mutation (the quantity a
    partition SUMS). Defaults (⟳ r1, Claude M1): the p90 OVER TARGETS of the per-mutation mean and of
    control + re-control — conservative, so a target the table has never seen is spread, not packed.
    Seconds, to the millisecond."""
    by = {}
    for kind, target, cost in records:
        by.setdefault(target, {"control": [], "recontrol": [], "mutation": []})[kind].append(cost)
    r3 = lambda x: round(x, 3)
    targets = {}
    for t in sorted(by):
        b = by[t]
        if not (b["control"] and b["recontrol"] and b["mutation"]):
            continue   # a target seen without all three is costed at the defaults
        targets[t] = {"control": r3(statistics.median(b["control"])),
                      "recontrol": r3(statistics.median(b["recontrol"])),
                      "mutation": r3(statistics.fmean(b["mutation"])),
                      "samples": len(b["control"]), "mutations": len(b["mutation"])}
    if not targets:
        raise Refused("no target had a control, a re-control and a mutation: nothing to tabulate")
    return {"schema": SCHEMA, "sources": list(sources),
            "defaults": {"mutation": _p90([v["mutation"] for v in targets.values()]),
                         "fixed": r3(_p90([v["control"] + v["recontrol"] for v in targets.values()]))},
            "targets": targets}


def _load_cpc(tree: pathlib.Path):
    path = tree / "scripts" / "check-plan-code.py"
    spec = importlib.util.spec_from_file_location(f"cpc_{abs(hash(str(tree)))}", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def shard_holding(cpc, tree: pathlib.Path, muts: list, index: int, total: int) -> list:
    """IO. The mutations shard `index` of `total` held, by the run tree's OWN partition function and its
    OWN rule for whether its table was usable (`sweep_costs_for`, r1; `load_sweep_costs` before it)."""
    if hasattr(cpc, "sweep_costs_for"):
        return cpc.sweep_shard(muts, index, total, cpc.sweep_costs_for(tree, muts, total)[0])
    if hasattr(cpc, "sweep_shard"):
        return cpc.sweep_shard(muts, index, total, cpc.load_sweep_costs(tree)[0])
    return cpc.shard_slice(muts, index, total)


def run_identity(logs: list) -> int:
    """PURE. `[(file name, parsed)]` of ONE run -> its shard total, or `Refused`. ⟳ r1 (Codex 1, Claude M4):
    a run is every shard 1..total EXACTLY ONCE, under one total and one event — checked by IDENTITY, before
    any row is accumulated. Counting distinct shards let a duplicate log (a re-run attempt downloaded beside
    the first) be pooled twice, and let index 0 (read as the last shard) stand in for a missing one."""
    totals = sorted({pa["total"] for _, pa in logs})
    if len(totals) != 1:
        raise Refused(f"two totals or more in one run ({totals}): a run is ONE partition")
    events = sorted({pa["event"] for _, pa in logs})
    if len(events) != 1:
        raise Refused(f"two events or more in one run ({events}): one run is one event")
    total, seen = totals[0], {}
    for name, pa in logs:
        if pa["index"] in seen:
            raise Refused(f"a duplicate: {seen[pa['index']]} and {name} are both shard {pa['index']} of {total} "
                          f"— its targets would be counted twice")
        seen[pa["index"]] = name
    missing = sorted(set(range(1, total + 1)) - set(seen))
    if missing:
        raise Refused(f"missing shard(s) {missing[:5]} of {total}: a run is ALL its shards")
    return total


def tabulate(runs: list) -> "tuple[dict, list]":
    """IO. `[(label, tree, logdir)]` -> (table, per-run notes). Raises `Refused` on the first bad log."""
    records, notes = [], []
    for label, tree, logdir in runs:
        cpc = _load_cpc(tree)
        if not hasattr(cpc, "progress_line"):
            raise Refused(f"{label}: the run tree has no progress_line, so its log lines cannot be matched")
        muts, problems = cpc.load_manifests(tree)
        if problems:
            raise Refused(f"{label}: the run tree's manifests do not load: {problems[:2]}")
        logs = sorted(logdir.glob("shard*.log"))
        if not logs:
            raise Refused(f"{label}: no shard*.log in {logdir}")
        parsed = []
        for f in logs:
            try:
                text = f.read_text(encoding="utf-8")
                parsed.append((f.name, parse_log(text)))
            except Refused as exc:
                raise Refused(f"{label}: {f.name}: {exc}") from None
            except (OSError, UnicodeDecodeError) as exc:
                raise Refused(f"{label}: {f.name} is unreadable ({exc})") from None
        try:
            total = run_identity(parsed)
        except Refused as exc:
            raise Refused(f"{label}: {exc}") from None
        for name, pa in parsed:
            try:
                records += attribute(pa, shard_holding(cpc, tree, muts, pa["index"], total), cpc.progress_line)
            except Refused as exc:
                raise Refused(f"{label}: {name}: {exc}") from None
        notes.append(f"{label}: {total} shards, {len(muts)} mutations attributed")
    return build_table(records, [r[0] for r in runs]), notes


def write_table(table: dict, out: pathlib.Path, cpc) -> None:
    """IO. Write `table` to `out` ONLY if check-plan-code's own parser accepts it; else `Refused`, and the
    file on disk is untouched. ⟳ r1 (Codex 3): a table the reader refuses would silently demote every
    later sweep to round-robin — and replace the usable table it overwrote."""
    costs, why = cpc.parse_sweep_costs(json.dumps(table))
    if costs is None:
        raise Refused(f"the table just built does not parse as check-plan-code reads it: {why}")
    out.write_text(json.dumps(table, indent=1, sort_keys=False) + "\n", encoding="utf-8")


def predict(table: dict, n: int) -> list:
    """IO. Each shard's estimate (seconds) under `table` for the CURRENT tree's manifest."""
    cpc = _load_cpc(HERE.parent)
    muts, problems = cpc.load_manifests(HERE.parent)
    if problems:
        raise Refused(f"the current manifests do not load: {problems[:2]}")
    costs, why = cpc.parse_sweep_costs(json.dumps(table))
    if costs is None:
        raise Refused(f"the table just built does not parse: {why}")
    return [cpc.shard_estimate(p, costs) / 1000 for p in cpc.sweep_partition(muts, n, costs)]


# ── self-test ────────────────────────────────────────────────────────────────────────────────────
FIXTURE = HERE / "fixtures" / "sweep-costs" / "shard-excerpt.log"


def _self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: every `--self-test` runs isolated (backlog #382)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    passed = failed = 0

    def case(name, got, want):
        nonlocal passed, failed
        if got == want:
            passed += 1
        else:
            failed += 1
            print(f"  [FAIL] {name}: got {got!r} want {want!r}")

    def refusal(fn, *a):
        try:
            fn(*a)
        except Refused as exc:
            return str(exc)
        except Exception as exc:   # a crash is a FAIL line naming the case, never a traceback
            return f"RAISED {exc!r}"
        return None

    # A REAL log excerpt (scripts/fixtures/sweep-costs/shard-excerpt.log — its header says what was trimmed):
    # shard 5 of 38 of run 43662666915 at 033fe20c, two targets, five mutations, timestamps verbatim.
    text = FIXTURE.read_text(encoding="utf-8")
    # ⚠ The two calls every later case reads are GUARDED: a raise there must print a `[FAIL] <case>` line
    # (the mutation harness attributes a kill by it), never a traceback, and the rest are skipped.
    try:
        p, why = parse_log(text), None
    except Exception as exc:
        p, why = None, f"RAISED {exc!r}"
    case("the real excerpt parses: shard 5 of 38 (SHARD_INDEX 4 is 0-based), 9 progress lines, an OK verdict",
         why or (p["index"], p["total"], len(p["prog"]), p["verdict"][:4]), (5, 38, 9, "OK —"))
    if p is None:
        print(f"{passed}/{passed + failed} passed (the rest skipped: the fixture did not parse)")
        return 1
    case("...with the runner's 7-digit fractional seconds kept (control 1 -> control 2 is 9.887793 s)",
         round(p["prog"][1][0] - p["prog"][0][0], 6), 9.887793)
    case("...and the env block's EVENT read (push: one hash seed)", p.get("event"), "push")
    cpc = _load_cpc(HERE.parent)
    render = cpc.progress_line
    A, B = "scripts/ask_answerer.py", "scripts/backfill-work-lines.py"
    mine = [{"file": A, "name": "a claim counts as a run, so a question refused by the cap spends the cap"},
            {"file": A, "name": "a run that reported no usage counts as zero tokens"},
            {"file": B, "name": "the banner need not name the cleared plan"},
            {"file": B, "name": "a clean heredoc on stdin is still opaque"},
            {"file": B, "name": "--backup copies nothing"}]

    def attr(parsed, held):
        return attribute(parsed, held, render)
    try:
        rows, why = attr(p, mine), None
    except Exception as exc:
        rows, why = [], f"RAISED {exc!r}"
    case("⭐ every line is attributed to its target and kind; cost = gap to the next line (the last: to the verdict)",
         why or [(k, t[8:13], round(c, 3)) for k, t, c in rows],
         [("control", "ask_a", 9.888), ("control", "backf", 283.114),
          ("mutation", "ask_a", 9.353), ("mutation", "ask_a", 9.352), ("mutation", "backf", 0.64),
          ("mutation", "backf", 0.6), ("mutation", "backf", 832.999),
          ("recontrol", "ask_a", 9.37), ("recontrol", "backf", 279.123)])
    # Each REFUSAL, by its sentence — a log attributed to the wrong shard must never be averaged in.
    case("⛔ a wrong NAME at a mutation line is refused",
         "is not mutation line" in (refusal(attr, p, [dict(mine[0], name="a claim counts as a RUN")]
                                            + mine[1:]) or ""), True)

    def _relabel(j, body):   # the parsed log with progress line j's text replaced, its time kept
        return dict(p, prog=p["prog"][:j] + [(p["prog"][j][0], body)] + p["prog"][j + 1:])
    # r1 (Codex 2, Claude M4): a label was matched as a PREFIX, so its first character, an empty label or a
    # bare `…` matched any name at that position. The line must be EXACTLY what `progress_line` writes.
    case("⛔ r1: a mutation label that is only a PREFIX of its name (first character, empty, a bare `…`) is refused",
         {k: "is not mutation line" in (refusal(attr, _relabel(2, b), mine) or "")
          for k, b in {"first char": "[1/5] a", "empty": "[1/5] ", "ellipsis": "[1/5] …"}.items()},
         {"first char": True, "empty": True, "ellipsis": True})
    _long = "x" * 120
    case("...and a LONG name is matched cut exactly the way progress_line cuts it — that cut, and only that",
         (refusal(attr, _relabel(2, render(1, 5, _long)), [dict(mine[0], name=_long)] + mine[1:]),
          "is not mutation line" in (refusal(attr, _relabel(2, render(1, 5, _long)[:-2] + "…"),
                                             [dict(mine[0], name=_long)] + mine[1:]) or "")),
         (None, True))
    case("⛔ a wrong COUNT (the shard held one more mutation than the log ran) is refused",
         "expected 10" in (refusal(attr, p, mine + [dict(mine[4], name="x")]) or ""), True)
    case("⛔ a wrong TARGET order (the shard's targets are not the controls the log ran) is refused",
         "is not control line '[1/2] control scripts/aa.py'" in (
             refusal(attr, p, [dict(m, file="scripts/aa.py") if m["file"] == B else m for m in mine]) or ""),
         True)
    case("⛔ ...and a re-control naming another target is refused",
         "is not recontrol line" in (refusal(attr, _relabel(7, "[1/2] re-control scripts/zz.py"), mine) or ""),
         True)
    # r1 (Codex 3): a timestamp earlier than the line before it made a NEGATIVE cost, accepted here and only
    # rejected later by check-plan-code's parser — after the table was written.
    case("⛔ r1: a log whose clock runs BACKWARDS (a negative cost) is refused",
         "BACKWARDS" in (refusal(attr, dict(p, prog=[p["prog"][0], (p["prog"][0][0] - 1, p["prog"][1][1])]
                                             + p["prog"][2:]), mine) or ""), True)
    sel = text.replace("measured over shard 5 of 38", "measured over shard 5 of 38 of the DIFF-SCOPED selection")
    case("⛔ a DIFF-SCOPED (PR) run is refused: its shards are not the full partition",
         "SELECTED run" in (refusal(parse_log, sel) or ""), True)
    case("⛔ an unfinished shard (NOT MEASURED) is refused",
         "did not finish" in (refusal(parse_log, re.sub(r"Z OK — ", "Z NOT MEASURED — ", text)) or ""), True)
    case("⛔ a log with no env block is refused",
         "SHARD_INDEX" in (refusal(parse_log, re.sub(r"SHARD_INDEX: 4", "X: 4", text)) or ""), True)
    case("⛔ a verdict naming another shard than the env block is refused",
         "the env 5 of 38" in (refusal(parse_log, text.replace("shard 5 of 38", "shard 6 of 38")) or ""), True)
    # r1 (Codex 4, Claude M3): malformed values the line regexes accept crashed with a ValueError, not a reason.
    # (Codex 1): `SHARD_INDEX: -1` became shard 0, which Python's negative indexing read as the LAST shard.
    _bad_env = {"not a number": text.replace("SHARD_INDEX: 4", "SHARD_INDEX: nope"),
                # the verdict re-labelled to agree, as a log of that shard would be (Codex 1's input)
                "negative": text.replace("SHARD_INDEX: 4", "SHARD_INDEX: -1").replace(
                    "shard 5 of 38", "shard 0 of 38"),
                "past the total": text.replace("SHARD_INDEX: 4", "SHARD_INDEX: 38").replace(
                    "shard 5 of 38", "shard 39 of 38"),
                "zero shards": text.replace("SHARD_TOTAL: 38", "SHARD_TOTAL: 0"),
                "month 13": text.replace("2026-11-15T01:21:33", "2026-13-15T01:21:33")}
    case("⛔ r1: a malformed SHARD_INDEX / SHARD_TOTAL or timestamp is a REFUSAL with a reason, never a crash",
         {k: (lambda r: bool(r) and not r.startswith("RAISED"))(refusal(parse_log, v)) for k, v in _bad_env.items()},
         {k: True for k in _bad_env})
    # r2 (Codex 3): `\d+` admits any LENGTH, and past 4,300 digits `int()` raises Python's digit-limit ValueError —
    # a crash where a reason was owed. Codex's input (4,301 digits in SHARD_INDEX), and the same class in the
    # VERDICT line's own two counts, which the env block's bound does not reach.
    _long = {"SHARD_INDEX": text.replace("SHARD_INDEX: 4", "SHARD_INDEX: " + "1" * 4301),
             "SHARD_TOTAL": text.replace("SHARD_TOTAL: 38", "SHARD_TOTAL: " + "1" * 4301),
             "the verdict's shard": text.replace("shard 5 of 38", "shard " + "5" * 4301 + " of 38"),
             "the verdict's total": text.replace("shard 5 of 38", "shard 5 of " + "3" * 4301)}
    case("⛔ r2: a 4,301-digit count — env block or verdict line — is a REFUSAL naming the count, never a crash",
         {k: (lambda r: "RAISED" if (r or "").startswith("RAISED") else f"{k} is" in (r or "") and "digits" in r)(
             refusal(parse_log, v)) for k, v in _long.items()}, {k: True for k in _long})
    case("...and the longest count allowed, 9 digits, is READ as a number — refused only for disagreeing with the "
         "verdict, which names it",
         refusal(parse_log, text.replace("SHARD_TOTAL: 38", "SHARD_TOTAL: 123456789")),
         "the verdict names shard 5 of 38, the env 5 of 123456789")
    case("...and an index outside 1..total says so", "outside 0.." in (refusal(parse_log, _bad_env["past the total"]) or ""),
         True)
    # r1 (Claude M4): a SCHEDULE run sweeps every suite under two hash seeds, so its shard does ~twice a push's work.
    case("⛔ r1: a SCHEDULE run (two hash seeds) is refused, and so is a log that does not say its event",
         ("two hash seeds" in (refusal(parse_log, text.replace("EVENT: push", "EVENT: schedule")) or ""),
          "no EVENT" in (refusal(parse_log, text.replace("EVENT: push", "X: push")) or "")), (True, True))

    # r1 (Codex 1, Claude M4): a run is its shards' IDENTITIES, not their count — every one of 1..total exactly
    # once, one total, one event. Checked before any log's rows are accumulated.
    def _ids(*xs):
        return [(f"shard{i}.log", {"index": i, "total": t, "event": e}) for i, t, e in xs]
    _runs = {"complete": _ids((1, 2, "push"), (2, 2, "push")),
             "duplicate": _ids((1, 2, "push"), (1, 2, "push")),
             "missing": _ids((2, 2, "push")),
             "two totals": _ids((1, 2, "push"), (2, 3, "push")),
             "two events": _ids((1, 2, "push"), (2, 2, "workflow_dispatch"))}
    case("⭐ r1: a run must hold shards 1..total exactly once — a duplicate, a gap, two totals or two events are refused",
         {k: (lambda r: r if r is None else r.split(":")[0][:9])(refusal(run_identity, v)) for k, v in _runs.items()},
         {"complete": None, "duplicate": "a duplica", "missing": "missing s", "two totals": "two total",
          "two events": "two event"})

    # build_table: medians for the fixed costs, MEAN for the per-mutation cost — values chosen so a
    # median and a mean of each list DIFFER, so swapping them goes red.
    recs = ([("control", "scripts/a.py", c) for c in (1.0, 2.0, 9.0)]
            + [("recontrol", "scripts/a.py", c) for c in (3.0, 4.0, 11.0)]
            + [("mutation", "scripts/a.py", c) for c in (1.0, 1.0, 7.0)]
            + [("control", "scripts/b.py", 5.0), ("recontrol", "scripts/b.py", 6.0),
               ("mutation", "scripts/b.py", 2.0)]
            + [("control", "scripts/c.py", 8.0)])   # c: no mutation seen -> defaults
    tab = build_table(recs, ["run@sha"])
    case("⭐ control and re-control are MEDIANS, per-mutation the MEAN; a partial target is left to the defaults",
         {t: (v["control"], v["recontrol"], v["mutation"]) for t, v in tab["targets"].items()},
         {"scripts/a.py": (2.0, 4.0, 3.0), "scripts/b.py": (5.0, 6.0, 2.0)})
    # r1 (Claude M1): the defaults were MEDIANS — the optimistic guess for exactly the target that matters, a
    # big new or renamed suite. They are now the 90th percentile OVER TARGETS of the per-mutation mean and of
    # control + re-control: a: (3.0, 6.0), b: (2.0, 11.0) -> nearest-rank p90 of two is the larger.
    case("⭐ r1: the defaults are the p90 over targets of the per-mutation mean and of control + re-control",
         tab["defaults"], {"mutation": 3.0, "fixed": 11.0})
    case("...p90 is NEAREST-RANK: over 1..20 it is 18 (the median is 10.5, the max 20)",
         _p90(list(range(20, 0, -1))), 18)
    case("⛔ nothing to tabulate is refused, not written as an empty table",
         "nothing to tabulate" in (refusal(build_table, [("mutation", "scripts/c.py", 1.0)], ["x"]) or ""), True)
    # The table this writes is the one check-plan-code reads: round-trip through ITS parser.
    case("⭐ the table it builds is one check-plan-code's parse_sweep_costs ACCEPTS",
         cpc.parse_sweep_costs(json.dumps(tab))[1], None)
    # r1 (Codex 3): the output was written WITHOUT that parse, so an invalid table could replace a usable one.
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        out = pathlib.Path(td) / "t.json"
        out.write_text("OLD", encoding="utf-8")
        _neg = json.loads(json.dumps(tab))
        _neg["targets"]["scripts/a.py"]["control"] = -1.0
        _wr_bad = refusal(write_table, _neg, out, cpc)
        _kept = out.read_text(encoding="utf-8")
        _wr_good = refusal(write_table, tab, out, cpc)
        _good = json.loads(out.read_text(encoding="utf-8")) == tab
    case("⛔ r1: a table check-plan-code would REFUSE is never written — the usable one on disk is kept",
         ("does not parse" in (_wr_bad or ""), _kept, _wr_good, _good), (True, "OLD", None, True))
    with contextlib.redirect_stderr(io.StringIO()) as _err:
        rc = main(["--run", "x", "/nonexistent-tree", "/nonexistent-logs"])
    case("a missing run tree is CANNOT RUN (rc 2), saying so, not a crash",
         (rc, _err.getvalue().startswith("CANNOT RUN")), (2, True))
    print(f"{passed}/{passed + failed} passed")
    return 1 if failed else 0


def main(argv: "list | None" = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--run", nargs=3, action="append", metavar=("LABEL", "TREE", "LOGDIR"))
    ap.add_argument("--out", default=str(HERE.parent / TABLE))
    ap.add_argument("--predict", type=int, metavar="N")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return _self_test()
    if not a.run:
        print("CANNOT RUN — give at least one --run LABEL TREE LOGDIR", file=sys.stderr)
        return 2
    runs = [(lab, pathlib.Path(t), pathlib.Path(d)) for lab, t, d in a.run]
    for lab, t, d in runs:
        if not (t / "scripts" / "check-plan-code.py").is_file() or not d.is_dir():
            print(f"CANNOT RUN — {lab}: {t} is not a run tree, or {d} is not a log directory", file=sys.stderr)
            return 2
    try:
        table, notes = tabulate(runs)
    except Refused as exc:
        print(f"REFUSED — {exc}", file=sys.stderr)
        return 1
    try:   # r1 (Codex 3): through the reader's own parser, so a bad table never replaces a usable one
        write_table(table, pathlib.Path(a.out), _load_cpc(HERE.parent))
    except Refused as exc:
        print(f"REFUSED — {exc}", file=sys.stderr)
        return 1
    for n in notes:
        print(n)
    print(f"wrote {a.out}: {len(table['targets'])} target(s), defaults {table['defaults']}")
    if a.predict:
        try:
            est = predict(table, a.predict)
        except Refused as exc:
            print(f"REFUSED — {exc}", file=sys.stderr)
            return 1
        print(f"predicted at N={a.predict}: slowest shard {max(est):.0f} s, fastest {min(est):.0f} s, "
              f"mean {statistics.fmean(est):.0f} s (control + mutations + re-control; startup not included)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
