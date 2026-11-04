#!/usr/bin/env python3
"""Open, comment on, or close the `sweep-red` issue after a FULL mutation sweep on master (backlog #330).

    python3 scripts/sweep-red-alert.py              # in CI: reads SWEEP, SHA, EVENT, RUN_URL; acts via gh and git
    python3 scripts/sweep-red-alert.py --self-test  # 22 cases

WHY THIS EXISTS. A pull request's sweep is diff-scoped, so what it does not select is measured only by the full
sweep on master, AFTER merge. A red full sweep therefore opens an issue labelled `sweep-red` (or comments on the
open one), and `session-state.py` lists the open ones at every SessionStart (PR #496 r1 C4). A green full sweep
closes it, so a later red opens a FRESH issue rather than commenting on a stale one.

⛔ WHAT A GREEN MAY CLOSE (PR #496 r2 X1). A green RERUN of an older master commit A keeps A's SHA, so when its
descendant B went red, "the sweep is green" says nothing about B. The red path therefore RECORDS the failing SHA
in the issue body and in every comment (`MARKER`), and the green path closes an issue only when the green SHA
EQUALS or DESCENDS FROM every failing SHA recorded on it (`git merge-base --is-ancestor`). Otherwise it comments
that an older or unrelated commit went green and leaves the issue OPEN. A SHA it cannot read — no marker, a
malformed one, a commit git cannot find even after a fetch — also leaves it open: closing on evidence it could
not read is the failure this file exists to prevent.

THE DECISION, for each OPEN `sweep-red` issue on a green run (`green_actions`):

    comment, leave open   no failing SHA is recorded on it (an issue opened before r2 X1, or a hand-edited one)
    comment, leave open   some recorded SHA's ancestry is unreadable
    comment, leave open   some recorded SHA is NOT an ancestor of (or equal to) the green SHA
    close                 every recorded SHA is an ancestor of, or equal to, the green SHA

A `gh` or `git` call that fails outright raises, so the CI step goes red and the run says so — never a silent pass.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

LABEL = "sweep-red"
MARKER = "<!-- sweep-red-sha: {sha} -->"
MARKER_RE = re.compile(r"<!-- sweep-red-sha: ([0-9a-f]{40}) -->")
SHA_RE = re.compile(r"[0-9a-f]{40}")
ROOT = pathlib.Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
STEP_NAME = "- name: The FULL sweep on master opens, comments on, or closes the sweep-red issue"


def recorded_shas(issue: dict) -> "list[str] | None":
    """PURE. The failing SHAs recorded on `issue` (body, then each comment), in order, de-duplicated; None
    when there are none — an issue whose failing commit cannot be read."""
    texts = [issue.get("body") or ""] + [(c or {}).get("body") or "" for c in issue.get("comments") or []]
    out: list[str] = []
    for t in texts:
        for s in MARKER_RE.findall(t):
            if s not in out:
                out.append(s)
    return out or None


def green_actions(green_sha: str, issues: list, covers) -> list:
    """PURE but for `covers(failing, green) -> True | False | None` (None: unreadable). -> one
    (verb, number, text) per open issue, verb `close` or `comment`."""
    out = []
    for issue in issues:
        n, shas = issue["number"], recorded_shas(issue)
        if not SHA_RE.fullmatch(green_sha or ""):
            out.append(("comment", n, f"A FULL mutation sweep went green, but its SHA ({green_sha!r}) is "
                                      f"unreadable, so it cannot be shown to cover this issue. Left OPEN."))
            continue
        if shas is None:
            out.append(("comment", n, f"The FULL mutation sweep is green at {green_sha}, but no failing SHA is "
                                      f"recorded on this issue, so that green cannot be shown to cover it. Left "
                                      f"OPEN — close it by hand once a green covers the red."))
            continue
        verdicts = {s: covers(s, green_sha) for s in shas}
        unread = [s for s, v in verdicts.items() if v is None]
        older = [s for s, v in verdicts.items() if v is False]
        if unread:
            out.append(("comment", n, f"The FULL mutation sweep is green at {green_sha}, but the ancestry of "
                                      f"{', '.join(unread)} could not be read. Left OPEN."))
        elif older:
            out.append(("comment", n, f"An older or unrelated commit went green ({green_sha}): it does not "
                                      f"descend from the failing {', '.join(older)}. Left OPEN until a green "
                                      f"sweep covers that commit."))
        else:
            out.append(("close", n, f"The FULL mutation sweep is green at {green_sha}, which equals or descends "
                                    f"from every failing commit recorded here ({', '.join(shas)}). Closed by that "
                                    f"run. A later red opens a fresh issue."))
    return out


def red_body(sweep: str, event: str, sha: str, run_url: str) -> str:
    """PURE. The issue body or comment for a red run — it CARRIES the failing SHA (`MARKER`)."""
    return (f"The FULL mutation sweep reported '{sweep}' on master ({event}, {sha}): {run_url}\n"
            f"Pull requests run only the manifests their diff selects (backlog #330), so this run is where\n"
            f"a defect in an unselected manifest surfaces. Read the red shard's log for the survivor or the\n"
            f"CANNOT RUN line; treat the mutation evidence for this commit as NOT CHECKED until it is green.\n"
            f"{MARKER.format(sha=sha)}")


def git_covers(failing: str, green: str, run=subprocess.run) -> "bool | None":
    """IO. Is `failing` an ancestor of (or equal to) `green` in the current repository? One fetch of a commit
    this clone lacks, then None if git still cannot answer (exit status other than 0 or 1)."""
    for attempt in (0, 1):
        r = run(["git", "merge-base", "--is-ancestor", failing, green], capture_output=True, text=True)
        if r.returncode in (0, 1):
            return r.returncode == 0
        if attempt == 0:
            run(["git", "fetch", "--quiet", "origin", failing, green], capture_output=True, text=True)
    return None


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
    if sweep == "success":
        issues = json.loads(gh("issue", "list", "--label", LABEL, "--state", "open",
                               "--json", "number,body,comments", "--limit", "100"))
        if not issues:
            print(f"the full sweep is green and no {LABEL} issue is open")
            return 0
        for verb, n, text in green_actions(sha, issues, git_covers):
            if verb == "close":
                gh("issue", "close", str(n), "--comment", text)
                print(f"closed the {LABEL} issue #{n}")
            else:
                gh("issue", "comment", str(n), "--body", text)
                print(f"left the {LABEL} issue #{n} open: {text}")
        return 0
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
    return 0


# ── the self-test: the workflow step's REAL `run:` block, a fake `gh`, a real local git history ──────────────

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

    A, B, C = "a" * 40, "b" * 40, "c" * 40
    anc = {(A, A), (A, B), (A, C), (B, B), (B, C), (C, C)}            # A <- B <- C
    cov = lambda f, g: (f, g) in anc                                     # noqa: E731
    one = lambda body, *cs: [{"number": 7, "body": body, "comments": [{"body": c} for c in cs]}]  # noqa: E731
    mark = MARKER.format

    # ── the pure decision ──
    case("the failing SHA is read from the body and from every comment, in order, once each",
         recorded_shas(one(mark(sha=B), "x " + mark(sha=C), mark(sha=B))[0]), [B, C])
    case("an issue with no marker records NO failing SHA", recorded_shas(one("SHA " + B)[0]), None)
    case("⭐ r2 X1: an OLDER green (A, after descendant B went red) leaves the issue open, with a comment",
         [v for v, _, _ in green_actions(A, one(mark(sha=B)), cov)], ["comment"])
    case("⭐ r2 X1: a green that DESCENDS from the failing commit closes it",
         [v for v, _, _ in green_actions(C, one(mark(sha=B)), cov)], ["close"])
    case("...and a green AT the failing commit closes it", [v for v, _, _ in green_actions(B, one(mark(sha=B)), cov)],
         ["close"])
    case("...but only when it covers EVERY failing commit recorded on the issue",
         [v for v, _, _ in green_actions(B, one(mark(sha=B), mark(sha=C)), cov)], ["comment"])
    case("an issue with no recorded SHA is left open", [v for v, _, _ in green_actions(C, one("old body"), cov)],
         ["comment"])
    case("an unreadable ancestry is left open",
         [v for v, _, _ in green_actions(C, one(mark(sha=B)), lambda f, g: None)], ["comment"])
    case("an unreadable GREEN sha is left open", [v for v, _, _ in green_actions("", one(mark(sha=B)), cov)],
         ["comment"])
    r1, r2 = red_body("failure", "push", B, "https://run/1"), red_body("timed_out", "schedule", C, "https://run/2")
    case("the red body carries ITS OWN failing SHA as a marker", (recorded_shas({"body": r1}), recorded_shas({"body": r2})),
         ([B], [C]))
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

    # ── the workflow step's real `run:` block, a fake gh, a real git history ──
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
        g = lambda *a: subprocess.run(["git", *a], cwd=repo, capture_output=True, text=True,  # noqa: E731
                                      check=True).stdout.strip()
        g("init", "-q", "-b", "master")
        g("config", "user.email", "t@example.com")
        g("config", "user.name", "t")
        sha = {}
        for c in ("a", "b", "c"):
            g("commit", "-q", "--allow-empty", "-m", c)
            sha[c] = g("rev-parse", "HEAD")
        state = pathlib.Path(td) / "gh.json"

        def step(sweep: str, at: str) -> tuple[int, str]:
            e = dict(os.environ, PATH=f"{bin_}{os.pathsep}{os.environ.get('PATH', '')}", FAKE_GH_STATE=str(state),
                     SWEEP=sweep, SHA=sha.get(at, at), EVENT="push", RUN_URL=f"https://run/{sweep}/{at}")
            r = subprocess.run(["bash", "-c", "set -eu\n" + run_block], cwd=repo, env=e, capture_output=True,
                               text=True)
            return r.returncode, r.stdout + r.stderr

        def issues():
            return json.loads(state.read_text())["issues"]

        state.write_text(json.dumps({"issues": [], "calls": []}))
        rc, out = step("failure", "b")
        case("a red run at B opens ONE issue recording B", (rc, [recorded_shas(i) for i in issues()]),
             (0, [[sha["b"]]]))
        rc, out = step("success", "a")
        case("⭐ r2 X1 (Codex's input): a green RERUN of A after descendant B went red leaves the issue OPEN",
             (rc, [i["state"] for i in issues()]), (0, ["open"]))
        case("...and says so in a comment naming the older green",
             "older or unrelated commit went green (" + sha["a"] in (issues()[0]["comments"] or [{}])[-1].get("body", ""),
             True)
        rc, out = step("failure", "c")
        case("a second red comments on the open issue and records its own SHA",
             (rc, len(issues()), recorded_shas(issues()[0])), (0, 1, [sha["b"], sha["c"]]))
        rc, out = step("success", "b")
        case("...a green at B does not cover C, so it stays open", (rc, issues()[0]["state"]), (0, "open"))
        rc, out = step("success", "c")
        case("⭐ r2 X1: a green that descends from every failing SHA closes it", (rc, issues()[0]["state"]),
             (0, "closed"))
        state.write_text(json.dumps({"issues": [{"number": 9, "state": "open", "labels": [LABEL],
                                                 "body": mark(sha="d" * 40), "comments": []}], "calls": []}))
        rc, out = step("success", "c")
        case("a recorded SHA git cannot find, even after a fetch, leaves the issue open",
             (rc, issues()[0]["state"]), (0, "open"))
        state.write_text(json.dumps({"issues": [], "calls": [], "fail": True}))
        (bin_ / "gh").write_text("#!/bin/sh\necho 'HTTP 502' >&2\nexit 1\n")
        rc, out = step("success", "c")
        case("a gh failure makes the step RED, never a silent pass", (rc != 0, "HTTP 502" in out), (True, True))

    if fail:
        print(f"\n{ok} passed, {fail} FAILED")
        return 1
    print(f"\n{ok}/{ok + fail} self-test cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(_self_test() if "--self-test" in sys.argv else main())
