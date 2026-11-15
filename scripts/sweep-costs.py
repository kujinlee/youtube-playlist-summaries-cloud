#!/usr/bin/env python3
"""Build `scripts/sweep-costs.json` — the mutation sweep's per-target COST TABLE — from CI shard logs.

backlog #588. `check-plan-code.py --mutate --shard I/N` cuts the sorted mutation list into N contiguous
runs of equal ESTIMATED cost (`sweep_partition`). The estimate is this table: per target, the median
control seconds, the median re-control seconds and the mean seconds per mutation, measured from the
progress lines of real CI shard logs, plus two defaults for a target the table has never seen (the
global median per-mutation cost, and the median control + re-control).

usage:
  python3 scripts/sweep-costs.py --run LABEL TREE LOGDIR [--run ...] [--out scripts/sweep-costs.json]
                                 [--predict N]
  python3 scripts/sweep-costs.py --self-test

  LABEL   names the run in the table's `sources` (e.g. `43662666915@033fe20c`: run id @ commit).
  TREE    a checkout of the repository AT THE RUN'S COMMIT (`git worktree add --detach <dir> <sha>`).
  LOGDIR  that run's shard job logs, one `shard*.log` per job (`gh run view <id> --log` split per job,
          or `gh api repos/<o>/<r>/actions/jobs/<job>/logs`).
  --predict N   print each shard's estimate under the NEW table for the CURRENT tree's manifest.

⛔ ATTRIBUTION IS THE RUN'S OWN. Which mutations a shard held is decided by the partition function of
the tree that ran it — `sweep_shard` with that tree's own table where it exists, else `shard_slice`
(the round-robin of every run before backlog #588) — imported from TREE, never re-implemented here.
A log whose progress lines do not match that attribution exactly (counts, order, names) is REFUSED,
never averaged: a cost assigned to the wrong target would skew every later partition in silence.

Exit: 0 written; 1 a log REFUSED (its reason printed); 2 CANNOT RUN (bad arguments, unreadable input).

NO-CALLER: run by hand when the sweep's shard times drift — it reads downloaded CI logs, which no hook or
workflow step has; `check-plan-code` reads the table it writes, and falls back to round-robin, LOUDLY,
when that table is missing or unusable.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import importlib.util
import io
import json
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


class Refused(ValueError):
    """A log that cannot be attributed exactly. Its message is the reason."""


def _secs(stamp: str, frac: "str | None") -> float:
    t = dt.datetime.fromisoformat(stamp + "+00:00").timestamp()
    return t + (float("0." + frac) if frac else 0.0)


def parse_log(text: str) -> dict:
    """PURE. One shard job's log -> `{index, total, prog: [(t, k, M, label)], end, verdict}`.

    `index` is 1-based (the env block's `SHARD_INDEX` is the 0-based `--shard0`). `end` is the verdict
    line's time, so the last re-control has a cost. Raises `Refused` when any of them is missing, when
    the verdict is a selection (a PR run sweeps a DIFF-SCOPED subset, so its shards are not the table's
    partition), or when the run did not finish (NOT MEASURED / CANNOT RUN)."""
    idx = tot = end = verdict = None
    prog = []
    for raw in text.splitlines():
        m = LINE.match(raw.lstrip("\ufeff"))
        if not m:
            continue
        t, body = _secs(m.group(1), m.group(2)), m.group(3)
        env = body.strip()
        if env.startswith("SHARD_INDEX:") and idx is None:
            idx = int(env.split(":", 1)[1]) + 1
        elif env.startswith("SHARD_TOTAL:") and tot is None:
            tot = int(env.split(":", 1)[1])
        p = PROG.match(body)
        if p and end is None:
            prog.append((t, int(p.group(1)), int(p.group(2)), p.group(3)))
            continue
        v = VERDICT.match(body)
        if v and prog and end is None:
            end, verdict = t, body
    if idx is None or tot is None:
        raise Refused("no SHARD_INDEX / SHARD_TOTAL in the job's env block")
    if end is None:
        raise Refused("no verdict line (`OK|FAIL ... measured over shard I of N`) after the progress lines")
    if not verdict.startswith(("OK", "FAIL")):
        raise Refused(f"the shard did not finish: {verdict[:80]}")
    if "DIFF-SCOPED" in verdict or "ONLY" in verdict:
        raise Refused("a SELECTED run (a PR's diff-scoped sweep) is not the full partition")
    vm = VERDICT.match(verdict)
    if (int(vm.group(2)), int(vm.group(3))) != (idx, tot):
        raise Refused(f"the verdict names shard {vm.group(2)} of {vm.group(3)}, the env {idx} of {tot}")
    return {"index": idx, "total": tot, "prog": prog, "end": end, "verdict": verdict}


def attribute(parsed: dict, mine: list) -> list:
    """PURE. `(kind, target, seconds)` for every progress line, given the mutations the shard HELD.

    The layout is exact: one `control <t>` per touched target in sorted order, then one line per
    mutation `[k/len(mine)]` whose label is a prefix of its name (a long name is cut with `…`), then
    one `re-control <t>` per target. A line's cost is the gap to the next line; the last one's is the
    gap to the verdict. Anything else is `Refused` — never skipped, never re-ordered to fit."""
    targets = sorted({m["file"] for m in mine})
    prog, n, k = parsed["prog"], len(targets), len(mine)
    if len(prog) != 2 * n + k:
        raise Refused(f"{len(prog)} progress line(s), expected {2 * n + k} "
                      f"({n} control + {k} mutation + {n} re-control)")
    out = []
    for j, (t, done, tot, label) in enumerate(prog):
        cost = (prog[j + 1][0] if j + 1 < len(prog) else parsed["end"]) - t
        if j < n:
            want, kind, target = (j + 1, n, f"control {targets[j]}"), "control", targets[j]
            if (done, tot, label) != want:
                raise Refused(f"line {j + 1}: {label!r} [{done}/{tot}], expected {want[2]!r} [{want[0]}/{n}]")
        elif j < n + k:
            mu, kind = mine[j - n], "mutation"
            target = mu["file"]
            if (done, tot) != (j - n + 1, k) or not mu["name"].startswith(label.rstrip("…")):
                raise Refused(f"line {j + 1}: {label!r} [{done}/{tot}] is not mutation {j - n + 1}/{k} "
                              f"{mu['name'][:60]!r}")
        else:
            i = j - n - k
            kind, target = "recontrol", targets[i]
            if (done, tot, label) != (i + 1, n, f"re-control {targets[i]}"):
                raise Refused(f"line {j + 1}: {label!r}, expected 're-control {targets[i]}' [{i + 1}/{n}]")
        out.append((kind, target, cost))
    return out


def build_table(records: list, sources: list) -> dict:
    """PURE. Attributed `(kind, target, seconds)` rows, pooled across every shard of every run -> the
    table. Per target: MEDIAN control, MEDIAN re-control (one sample per shard that touched it — a
    median, since a cold runner's first suite is an outlier), MEAN per-mutation (the quantity a
    partition SUMS). Defaults: the median of every mutation's cost, and the median control + re-control
    over targets. Seconds, to the millisecond."""
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
    allmut = [c for k, _, c in records if k == "mutation"]
    if not targets or not allmut:
        raise Refused("no target had a control, a re-control and a mutation: nothing to tabulate")
    return {"schema": SCHEMA, "sources": list(sources),
            "defaults": {"mutation": r3(statistics.median(allmut)),
                         "fixed": r3(statistics.median(v["control"] + v["recontrol"]
                                                       for v in targets.values()))},
            "targets": targets}


def _load_cpc(tree: pathlib.Path):
    path = tree / "scripts" / "check-plan-code.py"
    spec = importlib.util.spec_from_file_location(f"cpc_{abs(hash(str(tree)))}", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def shard_holding(cpc, tree: pathlib.Path, muts: list, index: int, total: int) -> list:
    """IO. The mutations shard `index` of `total` held, by the run tree's OWN partition function."""
    if hasattr(cpc, "sweep_shard"):
        return cpc.sweep_shard(muts, index, total, cpc.load_sweep_costs(tree)[0])
    return cpc.shard_slice(muts, index, total)


def tabulate(runs: list) -> "tuple[dict, list]":
    """IO. `[(label, tree, logdir)]` -> (table, per-run notes). Raises `Refused` on the first bad log."""
    records, notes = [], []
    for label, tree, logdir in runs:
        cpc = _load_cpc(tree)
        muts, problems = cpc.load_manifests(tree)
        if problems:
            raise Refused(f"{label}: the run tree's manifests do not load: {problems[:2]}")
        logs = sorted(logdir.glob("shard*.log"))
        if not logs:
            raise Refused(f"{label}: no shard*.log in {logdir}")
        seen = set()
        for f in logs:
            try:
                parsed = parse_log(f.read_text(encoding="utf-8", errors="replace"))
                rows = attribute(parsed, shard_holding(cpc, tree, muts, parsed["index"], parsed["total"]))
            except Refused as exc:
                raise Refused(f"{label}: {f.name}: {exc}") from None
            seen.add((parsed["index"], parsed["total"]))
            records += rows
        totals = {t for _, t in seen}
        if len(totals) != 1 or len(seen) != next(iter(totals)):
            raise Refused(f"{label}: {len(seen)} distinct shard(s) of {sorted(totals)}: a run is ALL its shards")
        notes.append(f"{label}: {len(seen)} shards, {len(muts)} mutations attributed")
    return build_table(records, [r[0] for r in runs]), notes


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
    A, B = "scripts/ask_answerer.py", "scripts/backfill-work-lines.py"
    mine = [{"file": A, "name": "a claim counts as a run, so a question refused by the cap spends the cap"},
            {"file": A, "name": "a run that reported no usage counts as zero tokens"},
            {"file": B, "name": "the banner need not name the cleared plan"},
            {"file": B, "name": "a clean heredoc on stdin is still opaque"},
            {"file": B, "name": "--backup copies nothing"}]
    try:
        rows, why = attribute(p, mine), None
    except Exception as exc:
        rows, why = [], f"RAISED {exc!r}"
    case("⭐ every line is attributed to its target and kind; cost = gap to the next line (the last: to the verdict)",
         why or [(k, t[8:13], round(c, 3)) for k, t, c in rows],
         [("control", "ask_a", 9.888), ("control", "backf", 283.114),
          ("mutation", "ask_a", 9.353), ("mutation", "ask_a", 9.352), ("mutation", "backf", 0.64),
          ("mutation", "backf", 0.6), ("mutation", "backf", 832.999),
          ("recontrol", "ask_a", 9.37), ("recontrol", "backf", 279.123)])
    # Each REFUSAL, by its sentence — a log attributed to the wrong shard must never be averaged in.
    case("⛔ a wrong NAME at a mutation line is refused (the `…`-cut label is a prefix of the right one only)",
         "is not mutation 1/5" in (refusal(attribute, p, [dict(mine[0], name="a claim counts as a RUN")]
                                           + mine[1:]) or ""), True)
    case("⛔ a wrong COUNT (the shard held one more mutation than the log ran) is refused",
         "expected 10" in (refusal(attribute, p, mine + [dict(mine[4], name="x")]) or ""), True)
    case("⛔ a wrong TARGET order (the shard's targets are not the controls the log ran) is refused",
         "expected 'control scripts/aa.py'" in (refusal(attribute, p, [dict(m, file="scripts/aa.py")
                                                                       if m["file"] == B else m for m in mine]) or ""),
         True)
    case("⛔ ...and a re-control naming another target is refused",
         "expected 're-control" in (refusal(attribute, dict(p, prog=p["prog"][:7] + [
             (p["prog"][7][0], 1, 2, "re-control scripts/zz.py")] + p["prog"][8:]), mine) or ""), True)
    sel = text.replace("measured over shard 5 of 38", "measured over shard 5 of 38 of the DIFF-SCOPED selection")
    case("⛔ a DIFF-SCOPED (PR) run is refused: its shards are not the full partition",
         "SELECTED run" in (refusal(parse_log, sel) or ""), True)
    case("⛔ an unfinished shard (NOT MEASURED) is refused",
         "did not finish" in (refusal(parse_log, re.sub(r"Z OK — ", "Z NOT MEASURED — ", text)) or ""), True)
    case("⛔ a log with no env block is refused",
         "SHARD_INDEX" in (refusal(parse_log, re.sub(r"SHARD_INDEX: 4", "X: 4", text)) or ""), True)
    case("⛔ a verdict naming another shard than the env block is refused",
         "the env 5 of 38" in (refusal(parse_log, text.replace("shard 5 of 38", "shard 6 of 38")) or ""), True)

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
    case("...the defaults are the median mutation cost and the median control + re-control",
         tab["defaults"], {"mutation": 1.5, "fixed": 8.5})
    case("⛔ nothing to tabulate is refused, not written as an empty table",
         "nothing to tabulate" in (refusal(build_table, [("mutation", "scripts/c.py", 1.0)], ["x"]) or ""), True)
    # The table this writes is the one check-plan-code reads: round-trip through ITS parser.
    cpc = _load_cpc(HERE.parent)
    case("⭐ the table it builds is one check-plan-code's parse_sweep_costs ACCEPTS",
         cpc.parse_sweep_costs(json.dumps(tab))[1], None)
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
    pathlib.Path(a.out).write_text(json.dumps(table, indent=1, sort_keys=False) + "\n", encoding="utf-8")
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
