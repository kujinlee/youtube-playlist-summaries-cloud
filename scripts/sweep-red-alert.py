#!/usr/bin/env python3
"""Open or comment on the `sweep-red` issue after a FULL mutation sweep on master (backlog #330). It NEVER closes one.

    python3 scripts/sweep-red-alert.py              # in CI: reads SWEEP, SHA, EVENT, RUN_URL, FLAKY_DIR; acts via gh
    python3 scripts/sweep-red-alert.py --self-test  # 24 cases

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
rule (11-11 19:25) is "named AND FILED". So each shard writes its `mutation FLAKY — <name>: ` lines to a file,
the files reach this job as artifacts in `FLAKY_DIR`, and ANY FLAKY name — on a green sweep or a red one — opens
an issue labelled `sweep-flaky` listing them (or comments on the open one). It never closes one either. A
`FLAKY_DIR` that is unset or missing RAISES: a scan that did not run is NOT a scan that found nothing.

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
FLAKY_LINE = "mutation FLAKY — "
ROOT = pathlib.Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
STEP_NAME = "- name: The FULL sweep on master opens or comments on the sweep-red issue, and never closes one"


def red_body(sweep: str, event: str, sha: str, run_url: str) -> str:
    """PURE. The issue body or comment for a red run — it CARRIES the failing SHA (`MARKER`)."""
    return (f"The FULL mutation sweep reported '{sweep}' on master ({event}, {sha}): {run_url}\n"
            f"Pull requests run only the manifests their diff selects (backlog #330), so this run is where\n"
            f"a defect in an unselected manifest surfaces. Read the red shard's log for the survivor or the\n"
            f"CANNOT RUN line; treat the mutation evidence for this commit as NOT CHECKED until it is green.\n"
            f"{MARKER.format(sha=sha)}")


def flaky_names(text: str) -> list[str]:
    """PURE. The mutation names on the harness's `mutation FLAKY — <name>: ...` lines in `text`, first seen first,
    each once. A line may carry a log prefix (a timestamp); the name runs to the FIRST `: ` after the marker."""
    names: list[str] = []
    for line in text.split("\n"):
        if FLAKY_LINE in line:
            name = line.split(FLAKY_LINE, 1)[1].split(": ", 1)[0].strip()
            if name and name not in names:
                names.append(name)
    return names


def flaky_body(names: list[str], event: str, sha: str, run_url: str) -> str:
    """PURE. The issue body or comment for FLAKY mutants: each NAMED, with the commit and run they were seen in."""
    return (f"The mutation sweep on master ({event}, {sha}) reported {len(names)} FLAKY mutation(s): each SURVIVED "
            f"its first run and was KILLED on its one re-run (backlog #495). Not red, and NOT counted as killed: a "
            f"kill case that works only sometimes is a weak test — make it deterministic. Run: {run_url}\n"
            + "".join(f"- {n}\n" for n in names))


def read_flaky(flaky_dir: str) -> list[str]:
    """IO. Every FLAKY name in the shards' files under `flaky_dir`. RAISES when it is unset or not a directory."""
    if not flaky_dir or not pathlib.Path(flaky_dir).is_dir():
        raise RuntimeError(f"FLAKY_DIR {flaky_dir!r} is not a directory: the FLAKY scan did NOT RUN — treat the "
                           f"sweep's FLAKY results as NOT CHECKED")
    return flaky_names("\n".join(f.read_text(encoding="utf-8") for f in sorted(pathlib.Path(flaky_dir).glob("*.txt"))))


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
    alert_red(sweep, event, sha, run_url)
    # backlog #495 r1: AFTER the red alert, so a missing FLAKY_DIR (which raises) can never cost a red its issue.
    file_flaky(read_flaky(env.get("FLAKY_DIR", "")), event, sha, run_url)
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
    _log = ("2026-11-11T01:02:03Z mutation FLAKY — drop a guard: SURVIVED its first run, then KILLED (by 'x: y')\n"
            "mutation SURVIVED — real one: the suite stayed green\n"
            "Z mutation FLAKY — flip: a sign: SURVIVED its first run\n"
            "mutation FLAKY — drop a guard: again\n")
    case("⭐ #495 r1: `flaky_names` reads each FLAKY line's name (log prefix allowed), once each, never a SURVIVED one",
         (flaky_names(_log), flaky_names("mutation SURVIVED — real one: x\n")), (["drop a guard", "flip"], []))
    _b1, _b2 = flaky_body(["m one", "m two"], "push", B, "https://run/1"), flaky_body(["m three"], "schedule", C,
                                                                                      "https://run/2")
    case("...and `flaky_body` NAMES every FLAKY mutation, with its own event, SHA and run",
         [all(t in b for t in ts) for b, ts in ((_b1, ("- m one\n", "- m two\n", "push", B, "https://run/1",
                                                      "2 FLAKY")),
                                                (_b2, ("- m three\n", "schedule", C, "https://run/2", "1 FLAKY")))]
         + ["m one" in _b2], [True, True, False])
    try:
        read_flaky("")
        _raised_f = False
    except RuntimeError as e:
        _raised_f = "did NOT RUN" in str(e)
    case("...an unset FLAKY_DIR RAISES — a scan that did not run is never a scan that found nothing", _raised_f, True)
    with tempfile.TemporaryDirectory() as _fd:
        pathlib.Path(_fd, "shard-1.txt").write_text("Z mutation FLAKY — b: x\nZ mutation FLAKY — a: y\n",
                                                    encoding="utf-8")
        pathlib.Path(_fd, "shard-0.txt").write_text("Z mutation FLAKY — a: x\n", encoding="utf-8")
        pathlib.Path(_fd, "notes.log").write_text("Z mutation FLAKY — not a shard file: x\n", encoding="utf-8")
        case("...`read_flaky` reads EVERY shard file in the directory (each name once), and only `*.txt`",
             read_flaky(_fd), ["a", "b"])

    # ── the workflow step's real `run:` block, against a fake gh ──
    wf = WORKFLOW.read_text(encoding="utf-8")
    run_block = step_run_block(wf)
    case("the alert step's run block runs this helper", "python3 scripts/sweep-red-alert.py" in run_block, True)
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

        def step(sweep: str, at: str, flaky: "dict | None" = None, flaky_dir: "str | None" = None) -> tuple[int, str]:
            """`flaky`: {shard file: its FLAKY lines} written to a FRESH FLAKY_DIR; `flaky_dir` overrides the path."""
            fd = pathlib.Path(tempfile.mkdtemp(dir=td))
            for fname, text in (flaky or {}).items():
                (fd / fname).write_text(text, encoding="utf-8")
            e = dict(os.environ, PATH=f"{bin_}{os.pathsep}{os.environ.get('PATH', '')}", FAKE_GH_STATE=str(state),
                     SWEEP=sweep, SHA=sha.get(at, at), EVENT="push", RUN_URL=f"https://run/{sweep}/{at}",
                     FLAKY_DIR=str(fd) if flaky_dir is None else flaky_dir)
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
        _fa = {"shard-0.txt": "Z mutation FLAKY — alpha: SURVIVED its first run\n",
               "shard-3.txt": "Z mutation FLAKY — beta: SURVIVED its first run\n", "shard-1.txt": ""}
        state.write_text(json.dumps({"issues": [], "calls": []}))
        rc, out = step("success", "c", _fa)
        _fi = [i for i in st()["issues"] if i["labels"] == [FLAKY_LABEL]]
        case("⭐ #495 r1: a GREEN sweep with FLAKY mutants in two shards OPENS one sweep-flaky issue naming BOTH",
             (rc, len(_fi), [n in (_fi or [{}])[0].get("body", "") for n in ("- alpha\n", "- beta\n")],
              [i for i in st()["issues"] if LABEL in i["labels"]]), (0, 1, [True, True], []))
        rc, out = step("success", "c", {"shard-2.txt": "Z mutation FLAKY — gamma: x\n"})
        case("...a second one COMMENTS on the open sweep-flaky issue, naming its own, and opens no second issue",
             (rc, len(st()["issues"]), "- gamma\n" in (st()["issues"][0]["comments"] or [{}])[-1].get("body", "")),
             (0, 1, True))
        rc, out = step("failure", "c", {"shard-0.txt": "Z mutation FLAKY — delta: x\n"})
        case("...a RED sweep with a FLAKY mutant files BOTH: a sweep-red issue and the FLAKY names",
             (rc, sorted(i["labels"][0] for i in st()["issues"]),
              "- delta\n" in (st()["issues"][0]["comments"] or [{}])[-1].get("body", "")),
             (0, sorted([LABEL, FLAKY_LABEL]), True))
        state.write_text(json.dumps({"issues": [], "calls": []}))
        rc, out = step("success", "c", {"shard-0.txt": ""})
        case("...a green sweep with NO FLAKY mutant writes nothing to GitHub", (rc, writes(st()["calls"])), (0, []))
        rc, out = step("failure", "c", flaky_dir=str(pathlib.Path(td) / "never-downloaded"))
        case("⭐ #495 r1: a MISSING FLAKY_DIR makes the step RED — and only AFTER the red sweep got its issue",
             (rc != 0, "did NOT RUN" in out, [i["labels"] for i in st()["issues"]]), (True, True, [[LABEL]]))
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
