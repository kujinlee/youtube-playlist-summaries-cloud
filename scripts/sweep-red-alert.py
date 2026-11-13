#!/usr/bin/env python3
"""Open or comment on the `sweep-red` issue after a FULL mutation sweep on master (backlog #330). It NEVER closes one.

    python3 scripts/sweep-red-alert.py              # in CI: reads SWEEP, SHA, EVENT, RUN_URL, FLAKY_DIR; acts via gh
    python3 scripts/sweep-red-alert.py --self-test  # 52 cases

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
an issue labelled `sweep-flaky` listing them (or comments on the open one). It never closes one either.
⟳ r2 Codex 2: a `FLAKY_DIR` that is unset, or lacks ANY shard's `shard-<i>.txt` (one per entry of `ci.yml`'s
`shard:` matrix, `shard_count`), RAISES: a scan that did not run is NOT a scan that found nothing.
⟳ r3 Claude M1: a missing shard file no longer DISCARDS the names the present files hold — those are FILED first,
and THEN the step raises, naming the missing files as NOT RUN (the "file first, then go red" order of the red alert).
⟳ r2 Codex 3: a name runs to the harness's FIXED tail (`FLAKY_TAIL`), never to the first `: ` — real names hold one.

A `gh` call that fails raises, so the CI step goes red and the run says so — never a silent pass.
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
FLAKY_LABEL = "sweep-flaky"
FLAKY_LINE = "mutation FLAKY — "
FLAKY_TAIL = ": SURVIVED its first run, then KILLED on its one re-run"   # what `check-plan-code` prints after <name>
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
    """PURE. The mutation names on the harness's `mutation FLAKY — <name>: SURVIVED its first run, then KILLED ...`
    lines in `text`, first seen first, each once. A line may carry a log prefix (a timestamp, `✗`).
    ⛔ r2 Codex 3: the name runs from the marker to the LAST `FLAKY_TAIL` — never to the first `: `, which real
    manifest names contain (`#495: a survivor is never re-run` read as `#495`). A marker line WITHOUT the tail
    RAISES: the harness's line changed shape, and a name cut at a guess is a wrong name filed as right."""
    names: list[str] = []
    for line in text.split("\n"):
        if FLAKY_LINE in line:
            name, tail, _ = line.split(FLAKY_LINE, 1)[1].rpartition(FLAKY_TAIL)
            if not tail:
                raise RuntimeError(f"a FLAKY line without the harness's tail {FLAKY_TAIL!r}: {line.strip()[:200]!r} "
                                   f"— its name cannot be read, so the FLAKY scan did NOT RUN")
            name = name.strip()
            if name and name not in names:
                names.append(name)
    return names


def flaky_body(names: list[str], event: str, sha: str, run_url: str) -> str:
    """PURE. The issue body or comment for FLAKY mutants: each NAMED, with the commit and run they were seen in."""
    return (f"The mutation sweep on master ({event}, {sha}) reported {len(names)} FLAKY mutation(s): each SURVIVED "
            f"its first run and was KILLED on its one re-run (backlog #495). Not red, and NOT counted as killed: a "
            f"kill case that works only sometimes is a weak test — make it deterministic. Run: {run_url}\n"
            + "".join(f"- {n}\n" for n in names))


def shard_count(workflow_text: str) -> int:
    """PURE. How many shards the sweep runs: the entries of the ONE `shard: [...]` matrix line in `ci.yml`. RAISES
    unless there is exactly one such line with at least one entry — a count guessed is a scan bounded by a guess."""
    rows = [l for l in workflow_text.splitlines() if re.match(r"\s*shard:\s*\[", l)]
    if len(rows) != 1:
        raise ValueError(f"{len(rows)} `shard: [...]` matrix lines in the workflow, not one: the shard count is unknown")
    n = len([x for x in rows[0].split("[", 1)[1].split("]", 1)[0].split(",") if x.strip()])
    if n < 1:
        raise ValueError("the `shard: [...]` matrix is empty: the shard count is unknown")
    return n


SHARD_FILE = "shard-{}.txt"   # `read_flaky`'s per-shard file; `ci_flaky_contract` proves `ci.yml` writes the same
DOWNLOAD_STEP = "- name: Download every shard's FLAKY mutation names"


def ci_flaky_contract(workflow_text: str) -> None:
    """PURE. RAISES unless two links between `ci.yml` and `read_flaky` hold (backlog #617 part 1, PR #564 r3 m2). It
    checks ONLY these two; a drifted download `path:` or artifact `pattern:` is still red, through `read_flaky`'s
    missing-file report (r1 Claude m1).
    Two copies with no case between them before: (a) the shard step writes `sweep-flaky/shard-$V.txt` with exactly one
    such line, and `V` is `${{ strategy.job-index }}` (0-based, as `range(shards)` reads) — `$SHARD_TOTAL` there
    writes one file N times; (b) the download step merges every artifact into ONE directory (`merge-multiple: true`)
    — without it each shard lands in its own subdirectory. Either drift makes every master FLAKY scan NOT RUN."""
    # ⛔ r1 Codex M1/m: comments never count — a `#` line, or a ` #` tail, is dropped before any match.
    lines = [_uncomment(l) for l in workflow_text.splitlines()]
    writes = [(i, m.group(1)) for i, l in enumerate(lines)
              for m in re.finditer(r'>\s*"?[^"\s>]*sweep-flaky/shard-"?\$\{?([A-Za-z_]+)\}?"?\.txt"?(?=[\s;|&)]|$)', l)]   # r2 Codex m1: not `.txt.bak`
    if len(writes) != 1:
        raise ValueError(f"{len(writes)} redirects to `sweep-flaky/shard-$<VAR>.txt` in the workflow, not one: "
                         f"the FLAKY file name `read_flaky` reads ({SHARD_FILE!r}) is not proven")
    wi, var = writes[0]
    # ⛔ r1 Claude m3: the variable is read from the step that WRITES the file, never from anywhere in the workflow.
    # r3 Claude m3: the step's own `- ` line is indented LESS than its script — a `- ` line inside a heredoc is not.
    st = max([i for i in range(wi) if lines[i].lstrip().startswith("- ") and _indent(lines[i]) < _indent(lines[wi])],
             default=0)
    # r2 Codex m2: the WHOLE step, so an `env:` written below `run:` still counts.
    end = next((i for i in range(st + 1, len(lines)) if lines[i].strip() and _indent(lines[i]) <= _indent(lines[st])),
               len(lines))
    # ⛔ r2 Codex M1, r3 Claude M1/m2: `env:` names the value only while the script never touches it. An ALLOW-list,
    # not a list of reassignment spellings (`=`, `+=`, `++`, `let`, `read`, `unset` — r2+r3 thrashed on that list): in
    # the step, the name may appear only as an expansion `$V` / `${V`, or as its own `V:` key. Any other mention RAISES,
    # a harmless `echo "V=$V"` included — a deliberate, named red.
    if any(re.search(rf"(?<!\$)(?<!\$\{{)\b{var}\b(?!:\s)", l) for l in lines[st:end]):
        raise ValueError(f"the step that writes the shard file mentions `{var}` other than as `${var}`: only an "
                         f"expansion keeps the `env:` value the file name, and `read_flaky` reads {SHARD_FILE.format(0)} ..")
    if not any(re.fullmatch(rf"\s*{var}:\s*([\"']?)\$\{{\{{\s*strategy\.job-index\s*\}}\}}\1\s*", l)
               for l in lines[st:end]):
        raise ValueError(f"the shard file is named by `${var}`, which is not `${{{{ strategy.job-index }}}}`: "
                         f"`read_flaky` reads {SHARD_FILE.format(0)} .. per 0-based index, so the names would not match")
    starts = [i for i, l in enumerate(lines) if l.strip() == DOWNLOAD_STEP]
    if len(starts) != 1:
        raise ValueError(f"{len(starts)} `{DOWNLOAD_STEP}` steps in the workflow, not one")
    step = _children(lines, starts[0], _indent(lines[starts[0]]) + 2)   # `- name:` puts the keys 2 to the right
    withs = [i for i in step if lines[i].strip() == "with:"]
    # ⛔ r1 Codex M2: `merge-multiple` counts only as a DIRECT child of the step's `with:`, never under `env:`.
    if len(withs) != 1 or not any(re.fullmatch(r"merge-multiple:\s*([\"']?)true\1", lines[i].strip())
                                  for i in _children(lines, withs[0], None)):
        raise ValueError(f"the `{DOWNLOAD_STEP[8:]}` step does not set `with: merge-multiple: true`: each shard's "
                         f"file would land in its own subdirectory, and `read_flaky` reads one directory")


def _uncomment(line: str) -> str:
    """PURE. `line` without a YAML/shell comment: '' for a `#` line, else the text before the first ` #`."""
    return "" if line.lstrip().startswith("#") else re.sub(r"\s+#.*$", "", line)


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _children(lines: list[str], head: int, depth: int | None) -> list[int]:
    """PURE. Indices of the non-blank lines in `lines[head]`'s indented block whose indent is `depth` (None: the
    first child's) — the block ends at the first non-blank line indented no deeper than the head."""
    out, ind = [], _indent(lines[head])
    for i in range(head + 1, len(lines)):
        if not lines[i].strip():
            continue
        if _indent(lines[i]) <= ind:
            break
        if depth is None:
            depth = _indent(lines[i])
        if _indent(lines[i]) == depth:
            out.append(i)
    return out


def read_flaky(flaky_dir: str, shards: int) -> tuple[list[str], list[str]]:
    """IO. `(names, missing)`: every FLAKY name in the PRESENT files of `shard-0.txt` .. `shard-<shards-1>.txt` under
    `flaky_dir` (`ci.yml` names each shard's file by its 0-based `strategy.job-index`), and the names of the ABSENT
    ones. ⛔ r2 Codex 2: an absent file is never read as "no FLAKY" — `main` raises on a non-empty `missing`.
    ⛔ r3 Claude M1: but only AFTER filing `names`, so one missing file never discards the others' names. RAISES
    when `flaky_dir` is unset."""
    if not flaky_dir:
        raise RuntimeError("FLAKY_DIR is unset: the FLAKY scan did NOT RUN — treat the sweep's FLAKY results as "
                           "NOT CHECKED")
    files = [pathlib.Path(flaky_dir) / SHARD_FILE.format(i) for i in range(shards)]
    missing = [f.name for f in files if not f.is_file()]
    return flaky_names("\n".join(f.read_text(encoding="utf-8") for f in files if f.is_file())), missing


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
    workflow = WORKFLOW.read_text(encoding="utf-8")
    ci_flaky_contract(workflow)   # backlog #617: a drifted `ci.yml` is NOT RUN here, not "files missing"
    shards = shard_count(workflow)
    names, missing = read_flaky(env.get("FLAKY_DIR", ""), shards)
    # ⛔ r3 Claude M1: the names the PRESENT files hold are FILED first; only THEN does a missing file go red. With
    # files missing and no name read, nothing is filed — "no FLAKY mutation" would be a claim about unread shards.
    if names or not missing:
        file_flaky(names, event, sha, run_url)
    if missing:
        raise RuntimeError(f"FLAKY_DIR {env.get('FLAKY_DIR', '')!r} lacks {len(missing)} of {shards} shard files "
                           f"({', '.join(missing[:5])}{', ...' if len(missing) > 5 else ''}): the FLAKY scan did NOT "
                           f"RUN for them — treat THOSE shards' FLAKY results as NOT CHECKED ({len(names)} FLAKY "
                           f"name(s) read from the other shards were filed above)")
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
    # ⛔ r2 Codex 3: REAL manifest names (`scripts/mutations/check-plan-code.json`), each holding `: `, in the line
    # shape the harness prints (`  ✗ ` + its report line, a log timestamp before it).
    _n1, _n2, _n3 = ("#495: a survivor is never re-run", "#495: a FLAKY mutant turns the run red",
                     "#495 r1 B1: a re-run kill is accepted without the case it names")
    _t = FLAKY_TAIL + " in a fresh tree (by 'f returns one: got 2'). Not red, and NOT counted as killed: x\n"
    _log = (f"2026-11-11T01:02:03Z   ✗ {FLAKY_LINE}{_n1}{_t}"
            "mutation SURVIVED — real one: the suite stayed green\n"
            f"  ✗ {FLAKY_LINE}{_n2}{_t}{FLAKY_LINE}{_n3}{_t}{FLAKY_LINE}{_n1}{_t}")
    case("⭐ #495 r2 Codex 3: `flaky_names` reads each REAL name WHOLE (`: ` inside it), once each, never a SURVIVED one",
         (flaky_names(_log), flaky_names("mutation SURVIVED — real one: x\n")), ([_n1, _n2, _n3], []))
    try:
        flaky_names(f"{FLAKY_LINE}{_n1}: KILLED somehow\n")
        _raised_t = False
    except RuntimeError as e:
        _raised_t = "did NOT RUN" in str(e)
    case("...a FLAKY line WITHOUT the harness's tail RAISES — never a name cut at a guess", _raised_t, True)
    case("...and the harness prints exactly `FLAKY_LINE` + name + `FLAKY_TAIL`, so the tail read here is the one made",
         f'f"{FLAKY_LINE}{{name}}{FLAKY_TAIL}' in (ROOT / "scripts" / "check-plan-code.py").read_text(encoding="utf-8"),
         True)
    _b1, _b2 = flaky_body(["m one", "m two"], "push", B, "https://run/1"), flaky_body(["m three"], "schedule", C,
                                                                                      "https://run/2")
    case("...and `flaky_body` NAMES every FLAKY mutation, with its own event, SHA and run",
         [all(t in b for t in ts) for b, ts in ((_b1, ("- m one\n", "- m two\n", "push", B, "https://run/1",
                                                      "2 FLAKY")),
                                                (_b2, ("- m three\n", "schedule", C, "https://run/2", "1 FLAKY")))]
         + ["m one" in _b2], [True, True, False])
    try:
        read_flaky("", 1)
        _raised_f = False
    except RuntimeError as e:
        _raised_f = "did NOT RUN" in str(e)
    case("...an unset FLAKY_DIR RAISES — a scan that did not run is never a scan that found nothing", _raised_f, True)
    with tempfile.TemporaryDirectory() as _fd:
        case("⭐ #495 r2 Codex 2: an EMPTY FLAKY_DIR reports every shard's file missing, and no name",
             read_flaky(_fd, 2), ([], ["shard-0.txt", "shard-1.txt"]))
        pathlib.Path(_fd, "shard-0.txt").write_text(f"Z {FLAKY_LINE}a{_t}", encoding="utf-8")
        case("...a PARTIAL download (shard-0 of 2) reports the missing shard and only it — and the present one's names",
             read_flaky(_fd, 2), (["a"], ["shard-1.txt"]))
        pathlib.Path(_fd, "shard-1.txt").write_text(f"Z {FLAKY_LINE}b{_t}Z {FLAKY_LINE}a{_t}", encoding="utf-8")
        pathlib.Path(_fd, "notes.txt").write_text(f"Z {FLAKY_LINE}not a shard file{_t}", encoding="utf-8")
        case("...`read_flaky` reads EVERY shard's file (each name once), and only the shards' files",
             read_flaky(_fd, 2), (["a", "b"], []))
    _wf3 = "jobs:\n  s:\n    strategy:\n      matrix:\n        # shard: [not, this]\n        shard: [1, 2, 3]\n"
    case("⭐ #495 r2 Codex 2: `shard_count` is the entries of the ONE `shard:` matrix line", shard_count(_wf3), 3)
    _bad = []
    for _w in (_wf3 + "        shard: [1]\n", "jobs: {}\n", "        shard: []\n"):
        try:
            shard_count(_w)
            _bad.append(False)
        except ValueError:
            _bad.append(True)
    case("...two matrix lines, none, or an empty one RAISE — the count is never guessed", _bad, [True, True, True])

    # ── backlog #617 part 1 (PR #564 r3 m2): `ci.yml` writes and merges the files `read_flaky` reads ──
    _real = WORKFLOW.read_text(encoding="utf-8")
    def _contract(text):
        try:
            ci_flaky_contract(text)
            return "ok"
        except ValueError as e:
            return "raised"
    case("⭐ #617: the REAL `ci.yml` writes `shard-$<job-index>.txt` and merges with `merge-multiple: true`",
         ci_flaky_contract(_real), None)
    case("⭐ #617: `ci.yml` writing `shard-$SHARD_TOTAL.txt` (not the 0-based job index) RAISES",
         _contract(_real.replace("sweep-flaky/shard-$SHARD_INDEX.txt", "sweep-flaky/shard-$SHARD_TOTAL.txt")), "raised")
    case("⭐ #617: `ci.yml` downloading with `merge-multiple: false` RAISES",
         _contract(_real.replace("merge-multiple: true", "merge-multiple: false")), "raised")
    case("...a SECOND `merge-multiple: true` elsewhere does not rescue the download step's `false`",
         _contract(_real.replace("merge-multiple: true", "merge-multiple: false")
                   + "\n  later:\n    steps:\n      - uses: x\n        with:\n          merge-multiple: true\n"),
         "raised")
    case("...no shard-file write at all RAISES, and so does a second one",
         (_contract(_real.replace("sweep-flaky/shard-", "sweep-flaky/part-")),
          _contract(_real + '\n          echo x > "$RUNNER_TEMP/sweep-flaky/shard-$SHARD_INDEX.txt"\n')),
         ("raised", "raised"))
    _m1 = _real.replace('> "$RUNNER_TEMP/sweep-flaky/shard-$SHARD_INDEX.txt"',
                        '> "$RUNNER_TEMP/sweep-flaky/part-$SHARD_INDEX.txt"  # was > "$RUNNER_TEMP/sweep-flaky/shard-$SHARD_INDEX.txt"')
    case("⭐ r1 Codex M1: a COMMENT naming the shard file is not the write — the real redirect renamed RAISES",
         (_m1 != _real, _contract(_m1),
          _contract(_real.replace('> "$RUNNER_TEMP/sweep-flaky/shard-$SHARD_INDEX.txt"\n',
                                  '> "$RUNNER_TEMP/sweep-flaky/part-$SHARD_INDEX.txt"\n'
                                  '          # > "$RUNNER_TEMP/sweep-flaky/shard-$SHARD_INDEX.txt"\n'))),
         (True, "raised", "raised"))
    _m2 = _real.replace("          merge-multiple: true\n",
                        "          merge-multiple: false\n        env:\n          merge-multiple: true\n")
    case("⭐ r1 Codex M2: `merge-multiple: true` under the step's `env:` (with `with:` false) RAISES",
         (_m2 != _real, _contract(_m2)), (True, "raised"))
    case("...r1 Codex m: quoting the job index, quoting `true`, or an inline comment is NOT a false red",
         _contract(_real.replace("SHARD_INDEX: ${{ strategy.job-index }}", 'SHARD_INDEX: "${{ strategy.job-index }}"')
                   .replace("merge-multiple: true", "merge-multiple: 'true'   # one directory")
                   .replace("shard-$SHARD_INDEX.txt", 'shard-"$SHARD_INDEX".txt')), "ok")
    _path = "          path: ${{ runner.temp }}/sweep-flaky\n"
    _wr = 'grep -F x f > "$RUNNER_TEMP/sweep-flaky/shard-$SHARD_INDEX.txt"'
    case("⭐ r2 Codex M1: the writing step's script REASSIGNING the index (`SHARD_INDEX=$SHARD_TOTAL`) RAISES",
         (_real.count('          grep -F \'mutation FLAKY — \''),
          _contract(_real.replace("          grep -F 'mutation FLAKY — '",
                                  "          SHARD_INDEX=$SHARD_TOTAL\n          grep -F 'mutation FLAKY — '"))),
         (1, "raised"))
    case("...r2 Codex m1: a redirect to `shard-$SHARD_INDEX.txt.bak` (or `\"...txt\".bak`) is not the shard file",
         (_contract(_real.replace('/sweep-flaky/shard-$SHARD_INDEX.txt"', '/sweep-flaky/shard-$SHARD_INDEX.txt".bak')),
          _contract(_real.replace('/sweep-flaky/shard-$SHARD_INDEX.txt"', '/sweep-flaky/shard-$SHARD_INDEX.txt.bak"'))),
         ("raised", "raised"))
    _grep = "          grep -F 'mutation FLAKY — '"
    case("⭐ r3 Claude M1: `((V++))`, `let V++`, `V+=1`, `read V`, `unset V` in the writing step each RAISE",
         [_contract(_real.replace(_grep, "          " + x + "\n" + _grep))
          for x in ("((SHARD_INDEX++))", "let SHARD_INDEX++", "SHARD_INDEX+=1", "read SHARD_INDEX", "unset SHARD_INDEX")],
         ["raised"] * 5)
    case("...r3: the allow-list is deliberate — `echo \"SHARD_INDEX=$SHARD_INDEX\"` RAISES; `echo \"$SHARD_INDEX\"` does not",
         (_contract(_real.replace(_grep, '          echo "SHARD_INDEX=$SHARD_INDEX"\n' + _grep)),
          _contract(_real.replace(_grep, '          echo "${SHARD_INDEX}"\n' + _grep))), ("raised", "ok"))
    case("...r3 Claude m3: a `- ` line inside the writing step's script does not move the step start",
         _contract(_real.replace(_grep, "          cat <<'MD'\n          - shard summary\n          MD\n" + _grep)), "ok")
    _syn = ("jobs:\n  sweep:\n    steps:\n      - name: shard\n        run: |\n          " + _wr + "\n"
            "        env:\n          SHARD_INDEX: ${{ strategy.job-index }}\n  alert:\n    steps:\n      - " + DOWNLOAD_STEP[2:]
            + "\n        uses: actions/download-artifact@v4\n        with:\n          merge-multiple: true\n")
    case("...r2 Codex m2: the writing step's `env:` BELOW its `run:` is not a false red",
         (_contract(_syn), _contract(_syn.replace("job-index", "job-total"))), ("ok", "raised"))
    case("...r1 Claude m4: the download step ENDS at the next step — a later step's `with:` is not read as its own",
         (_real.count(_path), _contract(_real.replace(_path, _path + "      - name: later\n        uses: x\n"
                                                      "        with:\n          merge-multiple: true\n"))), (1, "ok"))
    case("...r1 Claude m4: a SECOND download step of that name RAISES — which one is read is never guessed",
         _contract(_real + "\n      " + DOWNLOAD_STEP + "\n        uses: x\n        with:\n          merge-multiple: false\n"),
         "raised")
    case("⭐ r1 Claude m3: the job index set in ANOTHER step does not vouch for the writing step's 1-based variable",
         _contract(_real.replace("SHARD_INDEX: ${{ strategy.job-index }}", "SHARD_INDEX: ${{ matrix.shard }}")
                   + "\n  other:\n    steps:\n      - name: y\n        env:\n          SHARD_INDEX: ${{ strategy.job-index }}\n"),
         "raised")
    case("...`read_flaky` reads the file name the contract proved", SHARD_FILE.format(3), "shard-3.txt")

    # ── the workflow step's real `run:` block, against a fake gh ──
    wf = WORKFLOW.read_text(encoding="utf-8")
    run_block = step_run_block(wf)
    case("the alert step's run block runs this helper", "python3 scripts/sweep-red-alert.py" in run_block, True)
    _dl = wf.split("- name: Download every shard's FLAKY mutation names", 1)[-1].split("- name:", 1)[0]
    case("⭐ #495 r2 Codex 2: the download step exists and is NOT continue-on-error — a failed download is a red step",
         ("actions/download-artifact" in _dl, "continue-on-error" in _dl), (True, False))
    with tempfile.TemporaryDirectory() as td:
        repo, bin_ = pathlib.Path(td) / "repo", pathlib.Path(td) / "bin"
        (repo / "scripts").mkdir(parents=True)
        bin_.mkdir()
        shutil.copy(__file__, repo / "scripts" / "sweep-red-alert.py")
        (repo / ".github" / "workflows").mkdir(parents=True)   # r2 Codex 2: the helper reads the REAL shard count
        shutil.copy(WORKFLOW, repo / ".github" / "workflows" / "ci.yml")
        n_shards = shard_count(wf)
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

        def step(sweep: str, at: str, flaky: "dict | None" = None, flaky_dir: "str | None" = None,
                 drop: tuple = ()) -> tuple[int, str]:
            """`flaky`: {shard file: its FLAKY lines} written to a FRESH FLAKY_DIR holding EVERY shard's file (an
            empty one by default) except those named in `drop`; `flaky_dir` overrides the path."""
            fd = pathlib.Path(tempfile.mkdtemp(dir=td))
            for fname, text in {**{f"shard-{i}.txt": "" for i in range(n_shards)}, **(flaky or {})}.items():
                if fname not in drop:
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
        _fa = {"shard-0.txt": f"Z {FLAKY_LINE}alpha{_t}", "shard-3.txt": f"Z {FLAKY_LINE}beta{_t}"}
        state.write_text(json.dumps({"issues": [], "calls": []}))
        rc, out = step("success", "c", _fa)
        _fi = [i for i in st()["issues"] if i["labels"] == [FLAKY_LABEL]]
        case("⭐ #495 r1: a GREEN sweep with FLAKY mutants in two shards OPENS one sweep-flaky issue naming BOTH",
             (rc, len(_fi), [n in (_fi or [{}])[0].get("body", "") for n in ("- alpha\n", "- beta\n")],
              [i for i in st()["issues"] if LABEL in i["labels"]]), (0, 1, [True, True], []))
        rc, out = step("success", "c", {"shard-2.txt": f"Z {FLAKY_LINE}gamma{_t}"})
        case("...a second one COMMENTS on the open sweep-flaky issue, naming its own, and opens no second issue",
             (rc, len(st()["issues"]), "- gamma\n" in (st()["issues"][0]["comments"] or [{}])[-1].get("body", "")),
             (0, 1, True))
        rc, out = step("failure", "c", {"shard-0.txt": f"Z {FLAKY_LINE}delta{_t}"})
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
        state.write_text(json.dumps({"issues": [], "calls": []}))
        rc, out = step("success", "c", {"shard-0.txt": ""}, drop=(f"shard-{n_shards - 1}.txt",))
        case("⭐ #495 r2 Codex 2: the REAL step with ONE of the matrix's shard files missing is RED, NOT RUN — never "
             "'no FLAKY'", (rc != 0, f"shard-{n_shards - 1}.txt" in out, "no FLAKY mutation" in out), (True, True, False))
        # ⛔ r3 Claude M1: the review's own run — every shard file but one present, a FLAKY name in shard-0.
        state.write_text(json.dumps({"issues": [], "calls": []}))
        rc, out = step("success", "c", {"shard-0.txt": f"Z {FLAKY_LINE}{_n1}{_t}"}, drop=("shard-5.txt",))
        _fi = [i for i in st()["issues"] if i["labels"] == [FLAKY_LABEL]]
        case("⭐ #495 r3 M1: a shard file MISSING still FILES the names the others hold, THEN goes red naming it NOT RUN",
             (rc != 0, f"- {_n1}\n" in (_fi or [{}])[0].get("body", ""), "shard-5.txt" in out, "NOT RUN" in out,
              f"1 of {n_shards} shard files" in out), (True, True, True, True, True))
        # backlog #617: the REAL step, run against a `ci.yml` whose download step lost `merge-multiple: true`.
        _ci = repo / ".github" / "workflows" / "ci.yml"
        _ci.write_text(wf.replace("merge-multiple: true", "merge-multiple: false"), encoding="utf-8")
        rc, out = step("success", "c")
        _ci.write_text(wf, encoding="utf-8")
        case("⭐ #617: the REAL step under a `ci.yml` without `merge-multiple: true` is RED naming it, never 'no FLAKY'",
             (rc != 0, "merge-multiple: true" in out, "no FLAKY mutation" in out), (True, True, False))
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
