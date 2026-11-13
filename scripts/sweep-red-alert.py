#!/usr/bin/env python3
"""Read every mutation-sweep shard's RECORD; on master, open or comment on the `sweep-red` and `sweep-flaky` issues
(backlog #330, #495, #619). It NEVER closes one.

    python3 scripts/sweep-red-alert.py              # in CI: reads SWEEP, SHA, EVENT, RUN_URL, RECORD_DIR; acts via gh
    python3 scripts/sweep-red-alert.py --self-test  # 41 cases

WHY THIS EXISTS. A pull request's sweep is diff-scoped, so what it does not select is measured only by the full
sweep on master, AFTER merge. A red full sweep therefore opens an issue labelled `sweep-red` (or comments on the
open one), recording the failing SHA (`MARKER`) for whoever reads it, and `session-state.py` lists every open one
at every SessionStart (PR #496 r1 C4).

⛔ A GREEN NEVER CLOSES (PR #496 r3, a redesign by removal). Rounds 1-3 each found a way for a green run to close
an alert it did not cover: a rerun of an older commit (r2 X1), a SHA record hidden past `gh`'s first 100 comments
(r3 X1), an unreadable record dropped beside a valid one (r3 X2). Every one was a rule deciding, from issue history,
that a green covers every recorded red. So there is no such rule: a green full sweep only COMMENTS "full sweep green
at <sha>, run <url>" on each open `sweep-red` issue, and with none open it writes nothing. Closing one is a person's
act after reading it. A stale open alert fails toward MORE alarm, the direction the owner's approval asked for.

⟳ backlog #495 r1 (Codex 4 / Claude M1): A FLAKY MUTANT IS FILED. The harness re-runs a survivor once, and one
killed on that re-run is FLAKY — GREEN, so the sweep is `success` and nothing above would ever write. The owner's
rule (11-11 19:25) is "named AND FILED": ANY FLAKY name, on a green sweep or a red one, opens an issue labelled
`sweep-flaky` listing them (or comments on the open one). It never closes one either.

⟳ backlog #619 R1 (architecture review 2026-11-13, #629): THE HANDOFF IS A STRUCTURED RECORD, NOT A LOG GREP. Each
shard's `check-plan-code.py --mutate ... --record <path>` writes ONE JSON record — `schema`, the `shard` and `total`
it parsed from `--shard0` and sliced by, whether its run was `complete`, and its `flaky` names — and each record is
its own artifact, downloaded into its own subdirectory of `RECORD_DIR`. This script reads only those records (it
walks the subdirectories, and reads a record's identity from its CONTENT, never its path) and never reads `ci.yml`:
the shard count is the records' own `total`. It replaces a grep of the log for the harness's report line, a file
per 0-based job index, and `ci_flaky_contract`, a text parser of `ci.yml` that proved two links between them and
thrashed through three review rounds (backlog #617, #629). Any record missing, malformed, duplicated, out of range,
disagreeing on the total or INCOMPLETE is a problem; the names the valid records hold are FILED first, and THEN the
step raises — "file first, then go red", as the red alert does (#495 r3 Claude M1).
⛔ ON A PULL REQUEST IT ONLY VALIDATES (`EVENT` is `pull_request`): the same upload, download and read run, any
problem is red, and NOTHING is filed — so a pull request that breaks the record path is red on its own CI, not on
master after merge.

A `gh` call that fails raises, so the CI step goes red and the run says so — never a silent pass.
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

LABEL = "sweep-red"
MARKER = "<!-- sweep-red-sha: {sha} -->"
FLAKY_LABEL = "sweep-flaky"
ROOT = pathlib.Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
STEP_NAME = ("- name: Read every shard's record; on master open or comment on the sweep-red and sweep-flaky issues, "
             "never closing one")
RECORD_SCHEMA = 1   # `check-plan-code.shard_record` writes this; a record of any other schema is a problem
RECORD_KEYS = ("complete", "flaky", "schema", "shard", "total")


def red_body(sweep: str, event: str, sha: str, run_url: str) -> str:
    """PURE. The issue body or comment for a red run — it CARRIES the failing SHA (`MARKER`)."""
    return (f"The FULL mutation sweep reported '{sweep}' on master ({event}, {sha}): {run_url}\n"
            f"Pull requests run only the manifests their diff selects (backlog #330), so this run is where\n"
            f"a defect in an unselected manifest surfaces. Read the red shard's log for the survivor or the\n"
            f"CANNOT RUN line; treat the mutation evidence for this commit as NOT CHECKED until it is green.\n"
            f"{MARKER.format(sha=sha)}")


def flaky_body(names: list[str], event: str, sha: str, run_url: str) -> str:
    """PURE. The issue body or comment for FLAKY mutants: each NAMED, with the commit and run they were seen in."""
    return (f"The mutation sweep on master ({event}, {sha}) reported {len(names)} FLAKY mutation(s): each SURVIVED "
            f"its first run and was KILLED on its one re-run (backlog #495). Not red, and NOT counted as killed: a "
            f"kill case that works only sometimes is a weak test — make it deterministic. Run: {run_url}\n"
            + "".join(f"- {n}\n" for n in names))


def _is_int(v) -> bool:
    return type(v) is int   # ⛔ not `isinstance`: `True` is an int, and a shard numbered `true` is not shard 1


def record_problem(record) -> "str | None":
    """PURE. Why `record` is not a shard record of `RECORD_SCHEMA`, or None. Exactly the five keys; `shard` and
    `total` integers with 1 <= shard <= total; `complete` a bool; `flaky` a list of non-empty strings."""
    if not isinstance(record, dict) or tuple(sorted(record)) != RECORD_KEYS:
        return f"not a shard record: its keys are {sorted(record) if isinstance(record, dict) else type(record).__name__}, not {list(RECORD_KEYS)}"
    if record["schema"] != RECORD_SCHEMA or not _is_int(record["schema"]):
        return f"schema {record['schema']!r}, not {RECORD_SCHEMA}"
    if not (_is_int(record["shard"]) and _is_int(record["total"]) and 1 <= record["shard"] <= record["total"]):
        return f"shard {record['shard']!r} of {record['total']!r} is not 1 <= shard <= total"
    if type(record["complete"]) is not bool:
        return f"`complete` is {record['complete']!r}, not true or false"
    if not isinstance(record["flaky"], list) or not all(isinstance(n, str) and n.strip() for n in record["flaky"]):
        return f"`flaky` is {record['flaky']!r}, not a list of mutation names"
    return None


def check_records(records: list) -> tuple[list[str], list[str]]:
    """PURE. `(names, problems)` over `records`, a list of `(where, parsed JSON)` — `where` is used ONLY to name a
    problem, never to identify a shard. `names`: every valid record's FLAKY names, in shard order, each once.
    `problems`: no record at all; a malformed one; records that disagree on `total`; two records for one shard;
    a shard of 1..total with no record; a record whose run was not `complete` (its names are still in `names`)."""
    valid, problems = [], []
    for where, rec in records:
        why = record_problem(rec)
        if why:
            problems.append(f"{where}: {why}")
        else:
            valid.append((where, rec))
    if not records:
        problems.append("no shard record at all: the shard count is unknown and NO shard's FLAKY results were read")
    totals = sorted({r["total"] for _, r in valid})
    if len(totals) > 1:
        problems.append(f"the records disagree on the shard total ({', '.join(map(str, totals))}): which shards "
                        f"exist is unknown")
    seen: dict = {}
    for where, rec in sorted(valid, key=lambda wr: (wr[1]["shard"], wr[0])):
        if rec["shard"] in seen:
            problems.append(f"two records claim shard {rec['shard']}: {seen[rec['shard']]} and {where}")
        seen.setdefault(rec["shard"], where)
        if not rec["complete"]:
            problems.append(f"shard {rec['shard']} of {rec['total']} ({where}) did not complete its run: its FLAKY "
                            f"results cover only the mutations it reached")
    if len(totals) == 1:
        missing = [i for i in range(1, totals[0] + 1) if i not in seen]
        if missing:
            problems.append(f"{len(missing)} of {totals[0]} shards have no record (shard "
                            f"{', '.join(map(str, missing[:8]))}{', ...' if len(missing) > 8 else ''})")
    names: list[str] = []
    for _, rec in sorted(valid, key=lambda wr: (wr[1]["shard"], wr[0])):
        names.extend(n for n in rec["flaky"] if n not in names)
    return names, problems


def read_records(record_dir: str) -> tuple[list[str], list[str]]:
    """IO. `check_records` over every `*.json` file under `record_dir`, at ANY depth (each artifact downloads into a
    subdirectory of its own name, backlog #619 R1 (b)). A file that does not parse is a problem, never skipped.
    RAISES when `record_dir` is unset."""
    if not record_dir:
        raise RuntimeError("RECORD_DIR is unset: the shard records were NOT READ — treat the sweep's FLAKY results "
                           "as NOT CHECKED")
    root, records = pathlib.Path(record_dir), []
    for f in sorted(root.rglob("*.json")) if root.is_dir() else []:
        where = f.relative_to(root).as_posix()
        try:
            records.append((where, json.loads(f.read_text(encoding="utf-8"))))
        except (OSError, ValueError) as e:
            records.append((where, f"unreadable: {e}"))
    return check_records(records)


def file_flaky(names: list[str], event: str, sha: str, run_url: str) -> None:
    """IO. Open a `sweep-flaky` issue naming `names`, or comment on the open one. Never closes one."""
    if not names:
        print("no FLAKY mutation in this sweep")
        return
    body = flaky_body(names, event, sha, run_url)
    gh("label", "create", FLAKY_LABEL, "--color", "FBCA04", "--force",
       "--description", "A mutation killed only on its re-run: a weak kill case (backlog #495)")
    flaky_open = json.loads(gh("issue", "list", "--label", FLAKY_LABEL, "--state", "open", "--json", "number",
                               "--limit", "1"))
    if flaky_open:
        gh("issue", "comment", str(flaky_open[0]["number"]), "--body", body)
        print(f"commented on the open {FLAKY_LABEL} issue #{flaky_open[0]['number']}: {len(names)} FLAKY")
    else:
        gh("issue", "create", "--label", FLAKY_LABEL, "--body", body,
           "--title", f"FLAKY mutation(s) in the sweep on master ({event}, {sha[:8]})")
        print(f"opened a {FLAKY_LABEL} issue: {len(names)} FLAKY")


def gh(*args: str, run=subprocess.run) -> str:
    """IO. One `gh` call; a failure RAISES, so the step goes red rather than passing silently."""
    r = run(["gh", *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:3])} exited {r.returncode}: {(r.stderr or r.stdout).strip()}")
    return r.stdout


def main(env=None) -> int:
    env = os.environ if env is None else env
    sweep, sha = env.get("SWEEP", ""), env.get("SHA", "")
    event, run_url = env.get("EVENT", ""), env.get("RUN_URL", "")
    record_dir = env.get("RECORD_DIR", "")
    # ⛔ backlog #619 R1 (c): a pull request VALIDATES the records and files nothing — its red is on the PR itself.
    if event == "pull_request":
        names, problems = read_records(record_dir)
        if problems:
            raise RuntimeError(f"the shard records under RECORD_DIR {record_dir!r} are NOT VALID — the handoff master "
                               f"files FLAKY mutants from is broken on this branch: " + "; ".join(problems))
        print(f"the shard records are valid ({len(names)} FLAKY name(s)); a pull request files nothing")
        return 0
    alert_red(sweep, event, sha, run_url)
    # backlog #495 r1: AFTER the red alert, so a missing RECORD_DIR (which raises) can never cost a red its issue.
    names, problems = read_records(record_dir)
    # ⛔ #495 r3 Claude M1: the names the valid records hold are FILED first; only THEN does a problem go red. With
    # problems and no name read, nothing is filed — "no FLAKY mutation" would be a claim about unread shards.
    if names or not problems:
        file_flaky(names, event, sha, run_url)
    if problems:
        raise RuntimeError(f"the shard records under RECORD_DIR {record_dir!r} have {len(problems)} problem(s): "
                           + "; ".join(problems) + f" — treat THOSE shards' FLAKY results as NOT CHECKED "
                           f"({len(names)} FLAKY name(s) read from the valid records were filed above)")
    return 0


def alert_red(sweep: str, event: str, sha: str, run_url: str) -> None:
    """IO. The `sweep-red` half: a red opens or comments; a green only comments on each open one."""
    if sweep == "success":
        issues = json.loads(gh("issue", "list", "--label", LABEL, "--state", "open", "--json", "number",
                               "--limit", "100"))
        if not issues:
            print(f"the full sweep is green and no {LABEL} issue is open")
            return
        for i in issues:
            gh("issue", "comment", str(i["number"]), "--body",
               f"full sweep green at {sha}, run {run_url}. This does not close the issue: read it, and close it "
               f"by hand once the red it records is understood.")
            print(f"commented on the open {LABEL} issue #{i['number']}; it stays open")
        return
    body = red_body(sweep, event, sha, run_url)
    gh("label", "create", LABEL, "--color", "B60205", "--force",
       "--description", "The full mutation sweep went red on master (backlog #330)")
    issues = json.loads(gh("issue", "list", "--label", LABEL, "--state", "open", "--json", "number", "--limit", "1"))
    if issues:
        gh("issue", "comment", str(issues[0]["number"]), "--body", body)
        print(f"commented on the open {LABEL} issue #{issues[0]['number']}")
    else:
        gh("issue", "create", "--label", LABEL, "--body", body,
           "--title", f"Full mutation sweep red on master ({event}, {sha[:8]})")
        print(f"opened a {LABEL} issue")


# ── the self-test: the workflow step's REAL `run:` block and a fake `gh` ──────────────────────────────────

FAKE_GH = r'''#!/usr/bin/env python3
import json, os, sys
p = os.environ["FAKE_GH_STATE"]
st = json.load(open(p))
a = sys.argv[1:]
st["calls"].append(a)
def opt(k):
    return a[a.index(k) + 1] if k in a else None
def save():
    json.dump(st, open(p, "w"))
if a[:2] == ["label", "create"]:
    st["label"] = True
elif a[:2] == ["issue", "list"]:
    rows = [i for i in st["issues"] if i["state"] == "open" and opt("--label") in i["labels"]]
    keys = opt("--json").split(",")
    rows = [{k: i[k] for k in keys} for i in rows][: int(opt("--limit") or 30)]
    jq = opt("--jq")   # the two filters the pre-r2 shell step used, so that step can be run here too
    if jq == ".[].number":
        print("\n".join(str(r["number"]) for r in rows))
    elif jq == ".[0].number // empty":
        print(rows[0]["number"] if rows else "")
    else:
        print(json.dumps(rows))
elif a[:2] == ["issue", "create"]:
    if not st.get("label"):
        save(); sys.exit("label not found")
    st["issues"].append({"number": 500 + len(st["issues"]), "state": "open", "labels": [opt("--label")],
                         "body": opt("--body"), "comments": []})
elif a[:2] == ["issue", "comment"]:
    next(i for i in st["issues"] if i["number"] == int(a[2]))["comments"].append({"body": opt("--body")})
elif a[:2] == ["issue", "close"]:
    i = next(i for i in st["issues"] if i["number"] == int(a[2]))
    i["state"] = "closed"; i["comments"].append({"body": opt("--comment")})
else:
    save(); sys.exit("fake gh: unknown call " + " ".join(a))
save()
'''


def step_run_block(workflow_text: str) -> str:
    """PURE. The `run:` block of the alert step in the workflow text, dedented. Raises when absent, so a
    renamed step is a red self-test, never a case that silently ran nothing."""
    lines = workflow_text.splitlines()
    start = next(i for i, l in enumerate(lines) if l.strip() == STEP_NAME)
    step_indent = len(lines[start]) - len(lines[start].lstrip())
    for j in range(start + 1, len(lines)):
        l = lines[j]
        if l.strip() and len(l) - len(l.lstrip()) <= step_indent:
            raise ValueError("the alert step has no `run:` key")
        if l.strip().startswith("run:"):
            rest = l.split("run:", 1)[1].strip()
            if rest and rest not in ("|", "|-", ">"):
                return rest + "\n"
            ind = len(l) - len(l.lstrip())
            body = []
            for b in lines[j + 1:]:
                if b.strip() and len(b) - len(b.lstrip()) <= ind:
                    break
                body.append(b)
            cut = min(len(b) - len(b.lstrip()) for b in body if b.strip())
            return "\n".join(b[cut:] for b in body).rstrip() + "\n"
    raise ValueError("the alert step has no `run:` key")


def _self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: every `--self-test` runs isolated (backlog #382)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _rec(shard: int, total: int, flaky=(), complete=True) -> dict:
    """A shard record spelled with LITERAL keys — never `RECORD_KEYS` — so a renamed key in the reader is red here."""
    return {"schema": 1, "shard": shard, "total": total, "complete": complete, "flaky": list(flaky)}


def _writer():
    """`check-plan-code.py`, loaded: the WRITER of the records this script reads (backlog #619 R1)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("check_plan_code_619", ROOT / "scripts" / "check-plan-code.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod   # a dataclass resolves its module through `sys.modules`
    spec.loader.exec_module(mod)
    return mod


def _self_test_body() -> int:
    ok = fail = 0

    def case(label, got, want):
        nonlocal ok, fail
        if got == want:
            ok += 1
        else:
            fail += 1
            print(f"[FAIL] {label}: got {got!r} want {want!r}")

    B, C = "b" * 40, "c" * 40

    # ── the pure parts ──
    r1, r2 = red_body("failure", "push", B, "https://run/1"), red_body("timed_out", "schedule", C, "https://run/2")
    case("the red body carries ITS OWN failing SHA as a marker",
         (MARKER.format(sha=B) in r1, MARKER.format(sha=C) in r2, MARKER.format(sha=C) in r1), (True, True, False))
    case("...and names its own result, event and run",
         [all(t in r for t in ts) for r, ts in ((r1, ("'failure'", "push", "https://run/1")),
                                                (r2, ("'timed_out'", "schedule", "https://run/2")))], [True, True])
    _wf = ("jobs:\n  j:\n    steps:\n      " + STEP_NAME + "\n        env:\n          A: 1\n"
           "        run: |\n          echo one\n            echo two\n      - name: next\n        run: echo no\n")
    case("the step's `run:` block is read dedented, and stops at the next step",
         (step_run_block(_wf), step_run_block(_wf.replace("run: |\n          echo one\n            echo two\n",
                                                          "run: echo inline\n"))),
         ("echo one\n  echo two\n", "echo inline\n"))
    try:
        step_run_block("      " + STEP_NAME + "\n        env:\n          A: 1\n      - name: next\n        run: x\n")
        _raised = False
    except ValueError:
        _raised = True
    case("a step with no `run:` of its own RAISES — the next step's is never borrowed", _raised, True)
    _b1, _b2 = flaky_body(["m one", "m two"], "push", B, "https://run/1"), flaky_body(["m three"], "schedule", C,
                                                                                      "https://run/2")
    case("`flaky_body` NAMES every FLAKY mutation, with its own event, SHA and run",
         [all(t in b for t in ts) for b, ts in ((_b1, ("- m one\n", "- m two\n", "push", B, "https://run/1",
                                                      "2 FLAKY")),
                                                (_b2, ("- m three\n", "schedule", C, "https://run/2", "1 FLAKY")))]
         + ["m one" in _b2], [True, True, False])

    # ── backlog #619 R1: the records, pure ──
    # ⛔ REAL manifest names (`scripts/mutations/check-plan-code.json`), each holding `: ` — the log grep this replaces
    # cut a name at a guess (#495 r2 Codex 3); a record carries it whole.
    _n1, _n2, _n3 = ("#495: a survivor is never re-run", "#495: a FLAKY mutant turns the run red",
                     "#495 r1 B1: a re-run kill is accepted without the case it names")
    _all3 = [("a", _rec(2, 3, [_n2, _n1])), ("b", _rec(1, 3, [_n1, _n3])), ("c", _rec(3, 3))]
    case("⭐ #619: every shard's record present — the FLAKY names WHOLE, in SHARD order, each once; no problem",
         check_records(_all3), ([_n1, _n3, _n2], []))
    case("⭐ #619: one shard of three with no record is a problem NAMING it — and the others' names are kept",
         check_records(_all3[:2]), ([_n1, _n3, _n2], ["1 of 3 shards have no record (shard 3)"]))
    case("...no record at all is a problem, never 'no FLAKY'",
         check_records([]), ([], ["no shard record at all: the shard count is unknown and NO shard's FLAKY "
                                  "results were read"]))
    case("⭐ #619 (b): TWO records claiming one shard is a problem naming both — never one read over the other",
         [p for p in check_records(_all3 + [("d", _rec(2, 3, ["x"]))])[1]], ["two records claim shard 2: a and d"])
    case("...records that DISAGREE on the total are a problem — which shards exist is unknown",
         check_records([("a", _rec(1, 2)), ("b", _rec(2, 3))])[1][:1],
         ["the records disagree on the shard total (2, 3): which shards exist is unknown"])
    case("⭐ #619: an INCOMPLETE shard is a problem, and its FLAKY names are STILL read",
         check_records([("a", _rec(1, 2, ["m"], complete=False)), ("b", _rec(2, 2))]),
         (["m"], ["shard 1 of 2 (a) did not complete its run: its FLAKY results cover only the mutations it reached"]))
    _bad = [("keys", {**_rec(1, 1), "extra": 1}), ("nokey", {k: v for k, v in _rec(1, 1).items() if k != "complete"}),
            ("list", [1]), ("schema", {**_rec(1, 1), "schema": 2}), ("bool", {**_rec(1, 1), "shard": True}),
            ("zero", _rec(0, 1)), ("over", _rec(3, 2)), ("str", {**_rec(1, 1), "total": "1"}),
            ("cmp", {**_rec(1, 1), "complete": 1}), ("names", _rec(1, 1, [""])), ("nlist", {**_rec(1, 1), "flaky": "m"}),
            ("sbool", {**_rec(1, 1), "schema": True}), ("txt", "unreadable: x")]
    case("⭐ #619: each malformed record is a problem of its own — wrong keys, schema, range, types, names",
         [p.split(":", 1)[0] for p in check_records(_bad)[1] if not p.startswith(("no shard", "1 of"))],
         [w for w, _ in _bad])
    case("...and a malformed record holds no names that are read", check_records([("x", {**_rec(1, 1, ["m"]),
                                                                                      "schema": 2})])[0], [])
    case("...a valid record's identity is its CONTENT: shard 1 of 1 at a path naming shard 5 is shard 1",
         check_records([("sweep-record-5/record.json", _rec(1, 1, ["m"]))]), (["m"], []))
    try:
        read_records("")
        _raised_f = False
    except RuntimeError as e:
        _raised_f = "NOT READ" in str(e)
    case("an unset RECORD_DIR RAISES — a read that did not run is never a read that found nothing", _raised_f, True)
    with tempfile.TemporaryDirectory() as _fd:
        _d = pathlib.Path(_fd)
        case("an EMPTY RECORD_DIR is the no-record problem", read_records(_fd)[1][:1],
             ["no shard record at all: the shard count is unknown and NO shard's FLAKY results were read"])
        for _i, _r in ((0, _rec(1, 2, ["a"])), (1, _rec(2, 2, ["b"]))):
            (_d / f"sweep-record-{_i}").mkdir()
            (_d / f"sweep-record-{_i}" / "record.json").write_text(json.dumps(_r), encoding="utf-8")
        (_d / "notes.txt").write_text(json.dumps(_rec(9, 9)), encoding="utf-8")
        case("⭐ #619 (b): `read_records` walks every artifact's SUBDIRECTORY, and reads only `*.json`",
             read_records(_fd), (["a", "b"], []))
        (_d / "sweep-record-1" / "record.json").write_text('{"schema": 1,', encoding="utf-8")
        _nm, _pr = read_records(_fd)
        case("...a record that does not PARSE is a problem naming its file, and its shard is then missing",
             (_nm, [p.split(":", 1)[0] for p in _pr], any("no record (shard 2)" in p for p in _pr)),
             (["a"], ["sweep-record-1/record.json", "1 of 2 shards have no record (shard 2)"], True))

    # ── backlog #619 R1: the REAL writer's records, read here — one schema, two scripts, a case between them ──
    _w = _writer()
    import coverage_verdict as _cv
    _m = _cv.Measured(files={}, declared=2, mutations=[{"name": _n1, "measured": True, "flaky": True},
                                                         {"name": "k", "measured": True}], survivors=[_n1],
                      controls_green=True)
    _nmv = _cv.NotMeasured.from_counts([{"name": _n3, "measured": True, "flaky": True}], 4)
    _recs = [("w1", _w.shard_record((1, 2), _m)), ("w2", _w.shard_record((2, 2), _nmv))]
    case("⭐ #619: `check-plan-code.shard_record`'s records READ here: both shards, their FLAKY names, the "
         "not-measured one INCOMPLETE",
         check_records(_recs), ([_n1, _n3], ["shard 2 of 2 (w2) did not complete its run: its FLAKY results "
                                             "cover only the mutations it reached"]))
    case("...and an unsharded run's record is shard 1 of 1", check_records([("w", _w.shard_record(None, _m))]),
         ([_n1], []))

    # ── the workflow step's real `run:` block, against a fake gh ──
    wf = WORKFLOW.read_text(encoding="utf-8")
    run_block = step_run_block(wf)
    case("the alert step's run block runs this helper", "python3 scripts/sweep-red-alert.py" in run_block, True)
    _dl = wf.split("- name: Download every shard's sweep record", 1)[-1].split("- name:", 1)[0]
    case("⭐ #619 (b): the download step exists, is NOT continue-on-error, and does NOT merge the artifacts",
         ("actions/download-artifact" in _dl, "continue-on-error" in _dl, "merge-multiple" in _dl), (True, False, False))
    with tempfile.TemporaryDirectory() as td:
        repo, bin_ = pathlib.Path(td) / "repo", pathlib.Path(td) / "bin"
        (repo / "scripts").mkdir(parents=True)
        bin_.mkdir()
        shutil.copy(__file__, repo / "scripts" / "sweep-red-alert.py")
        (bin_ / "gh").write_text(FAKE_GH)
        (bin_ / "gh").chmod(0o755)
        # A REAL commit, so a green AT the failing commit is a green any coverage rule would accept: the strongest
        # input for "a green never closes" (the pre-r3 helper closed on exactly this).
        g = lambda *a: subprocess.run(["git", *a], cwd=repo, capture_output=True, text=True,  # noqa: E731
                                      check=True).stdout.strip()
        g("init", "-q", "-b", "master")
        g("config", "user.email", "t@example.com")
        g("config", "user.name", "t")
        sha = {}
        for c in ("b", "c"):
            g("commit", "-q", "--allow-empty", "-m", c)
            sha[c] = g("rev-parse", "HEAD")
        state = pathlib.Path(td) / "gh.json"
        n_shards = 6

        def step(sweep: str, at: str, flaky: "dict | None" = None, record_dir: "str | None" = None,
                 drop: tuple = (), event: str = "push") -> tuple[int, str]:
            """`flaky`: {shard: its FLAKY names}, written as a FRESH RECORD_DIR holding EVERY shard's record, each in
            its own artifact subdirectory as `download-artifact` lays them out, except the shards in `drop`."""
            fd = pathlib.Path(tempfile.mkdtemp(dir=td))
            for i in range(1, n_shards + 1):
                if i not in drop:
                    (fd / f"sweep-record-{i - 1}").mkdir()
                    (fd / f"sweep-record-{i - 1}" / "record.json").write_text(
                        json.dumps(_rec(i, n_shards, (flaky or {}).get(i, ()))), encoding="utf-8")
            e = dict(os.environ, PATH=f"{bin_}{os.pathsep}{os.environ.get('PATH', '')}", FAKE_GH_STATE=str(state),
                     SWEEP=sweep, SHA=sha.get(at, at), EVENT=event, RUN_URL=f"https://run/{sweep}/{at}",
                     RECORD_DIR=str(fd) if record_dir is None else record_dir)
            r = subprocess.run(["bash", "-c", "set -eu\n" + run_block], cwd=repo, env=e, capture_output=True,
                               text=True)
            return r.returncode, r.stdout + r.stderr

        def st():
            return json.loads(state.read_text())

        def writes(calls):
            """the calls that change GitHub — everything but `issue list`."""
            return [c for c in calls if c[:2] != ["issue", "list"]]

        state.write_text(json.dumps({"issues": [], "calls": []}))
        rc, out = step("failure", "b")
        case("a red run with none open CREATES one issue, recording its failing SHA",
             (rc, len(st()["issues"]), MARKER.format(sha=sha["b"]) in st()["issues"][0]["body"]), (0, 1, True))
        rc, out = step("success", "b")
        last = (st()["issues"][0]["comments"] or [{}])[-1].get("body") or ""
        case("⭐ r3: a green AT the failing commit, with the issue open, COMMENTS and leaves it OPEN",
             (rc, st()["issues"][0]["state"], len(st()["issues"][0]["comments"])), (0, "open", 1))
        case("...and the comment names the green SHA and its run",
             (f"full sweep green at {sha['b']}" in last, "https://run/success/b" in last), (True, True))
        rc, out = step("failure", "c")
        case("a second red COMMENTS on the open issue, recording its own SHA, and opens no second issue",
             (rc, len(st()["issues"]), MARKER.format(sha=sha["c"]) in st()["issues"][0]["comments"][-1]["body"]),
             (0, 1, True))
        rc, out = step("success", "c")
        case("...a green that descends from every failing SHA still leaves it OPEN", (rc, st()["issues"][0]["state"]),
             (0, "open"))
        case("⭐ r3: `gh issue close` is never invoked, over a whole red/green/red/green history",
             [c for c in st()["calls"] if c[:2] == ["issue", "close"]], [])
        two = [{"number": n, "state": "open", "labels": [LABEL], "body": "x", "comments": []} for n in (8, 9)]
        state.write_text(json.dumps({"issues": two, "calls": []}))
        rc, out = step("success", "c")
        case("a green comments on EACH open sweep-red issue, and closes neither",
             (rc, [(i["state"], len(i["comments"])) for i in st()["issues"]]), (0, [("open", 1), ("open", 1)]))
        state.write_text(json.dumps({"issues": [], "calls": []}))
        rc, out = step("success", "c")
        case("a green with NO issue open writes nothing to GitHub", (rc, writes(st()["calls"]), st()["issues"]),
             (0, [], []))
        # ── backlog #495 r1 (Codex 4 / Claude M1): a FLAKY mutant is FILED, on a green sweep too ──
        state.write_text(json.dumps({"issues": [], "calls": []}))
        rc, out = step("success", "c", {1: ["alpha"], 4: [_n1]})
        _fi = [i for i in st()["issues"] if i["labels"] == [FLAKY_LABEL]]
        case("⭐ #495 r1: a GREEN sweep with FLAKY mutants in two shards OPENS one sweep-flaky issue naming BOTH",
             (rc, len(_fi), [n in (_fi or [{}])[0].get("body", "") for n in ("- alpha\n", f"- {_n1}\n")],
              [i for i in st()["issues"] if LABEL in i["labels"]]), (0, 1, [True, True], []))
        rc, out = step("success", "c", {3: ["gamma"]})
        case("...a second one COMMENTS on the open sweep-flaky issue, naming its own, and opens no second issue",
             (rc, len(st()["issues"]), "- gamma\n" in (st()["issues"][0]["comments"] or [{}])[-1].get("body", "")),
             (0, 1, True))
        rc, out = step("failure", "c", {1: ["delta"]})
        case("...a RED sweep with a FLAKY mutant files BOTH: a sweep-red issue and the FLAKY names",
             (rc, sorted(i["labels"][0] for i in st()["issues"]),
              "- delta\n" in (st()["issues"][0]["comments"] or [{}])[-1].get("body", "")),
             (0, sorted([LABEL, FLAKY_LABEL]), True))
        state.write_text(json.dumps({"issues": [], "calls": []}))
        rc, out = step("success", "c")
        case("...a green sweep with NO FLAKY mutant writes nothing to GitHub", (rc, writes(st()["calls"])), (0, []))
        rc, out = step("failure", "c", record_dir="")
        case("⭐ #495 r1: an unset RECORD_DIR makes the step RED — and only AFTER the red sweep got its issue",
             (rc != 0, "NOT READ" in out, [i["labels"] for i in st()["issues"]]), (True, True, [[LABEL]]))
        state.write_text(json.dumps({"issues": [], "calls": []}))
        rc, out = step("success", "c", record_dir=str(pathlib.Path(td) / "never-downloaded"))
        case("⭐ #619: a RECORD_DIR that was never downloaded is RED, NOT CHECKED — never 'no FLAKY'",
             (rc != 0, "no shard record at all" in out, "no FLAKY mutation" in out, writes(st()["calls"])),
             (True, True, False, []))
        # ⛔ #495 r3 Claude M1: every shard's record but one present, a FLAKY name in shard 1.
        state.write_text(json.dumps({"issues": [], "calls": []}))
        rc, out = step("success", "c", {1: [_n1]}, drop=(5,))
        _fi = [i for i in st()["issues"] if i["labels"] == [FLAKY_LABEL]]
        case("⭐ #495 r3 M1: a shard's record MISSING still FILES the names the others hold, THEN goes red naming it",
             (rc != 0, f"- {_n1}\n" in (_fi or [{}])[0].get("body", ""), f"1 of {n_shards} shards have no record "
              "(shard 5)" in out, "NOT CHECKED" in out), (True, True, True, True))
        # ── backlog #619 R1 (c): a PULL REQUEST validates the same records and files NOTHING ──
        state.write_text(json.dumps({"issues": [], "calls": []}))
        _pr = [step("failure", "c", {2: ["eps"]}, event="pull_request"), step("success", "c", event="pull_request")]
        case("⭐ #619 (c): on a PULL REQUEST, valid records pass and NOTHING reaches GitHub — red sweep or green",
             ([rc for rc, _ in _pr], st()["calls"]), ([0, 0], []))
        _prb = [step("success", "c", drop=(6,), event="pull_request"),
                step("success", "c", record_dir=str(pathlib.Path(td) / "never-downloaded"), event="pull_request")]
        case("⭐ #619 (c): on a PULL REQUEST a missing record, or none, is RED naming it — still with no gh call",
             ([(rc != 0, "NOT VALID" in out) for rc, out in _prb], "shard 6" in _prb[0][1], st()["calls"]),
             ([(True, True), (True, True)], True, []))
        (bin_ / "gh").write_text("#!/bin/sh\necho 'HTTP 502' >&2\nexit 1\n")
        for sweep in ("success", "failure"):
            rc, out = step(sweep, "c")
            case(f"a gh failure makes the step RED, never a silent pass ({sweep})", (rc != 0, "HTTP 502" in out),
                 (True, True))

    if fail:
        print(f"\n{ok} passed, {fail} FAILED")
        return 1
    print(f"\n{ok}/{ok + fail} self-test cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(_self_test() if "--self-test" in sys.argv else main())
