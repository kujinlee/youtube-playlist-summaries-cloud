#!/usr/bin/env python3
"""The per-PR gate battery in ONE call, one line per gate. Every gate in the set runs, every time.

    python3 scripts/gates-for-pr.py                 # run the battery
    python3 scripts/gates-for-pr.py --list          # the gate set and where each came from; runs nothing
    python3 scripts/gates-for-pr.py --self-test  # 37 cases

    0 = every gate in the set PASSED   1 = a gate FAILED
    2 = CANNOT RUN — the set could not be derived, or a gate ended CANNOT RUN / TIMEOUT / KILLED

WHY THIS EXISTS (backlog #438). The 2026-10-30 usage study measured 1,306 gate commands that finished in
under 10 s, each issued as its own Bash call. One call per battery removes them: the gates CI's `verify`
job runs on a pull request, run locally before the push, with one line each.

THE GATE SET IS DERIVED, NEVER LISTED BY HAND:
  * every step of `ci.yml`'s `verify` job whose `run:` is ONE `python3 scripts/<x>.py …` line. A PR-only
    step's `"origin/$GITHUB_BASE_REF"` becomes `origin/<--base>`. Everything else in the job (node, a
    multi-line block, another CI variable, `NOT_LOCAL`) is printed as OUT OF SET with its reason, and so
    is every OTHER job in `ci.yml` and `schema-gates.yml`, so the reader sees what this run does NOT claim.
  * one `check-plan-code.py --mutate . --only <script>` per script a moved file touches (the script, or
    a manifest naming it) — the owner's LOCAL rule, partial here, the full sweep in CI's shards.

NOTHING IS SKIPPED. ⟳ PR #465 r1: a last-green ledger skipped a gate whose measured inputs were unchanged;
both review halves reproduced FALSE GREENS through it (a helper imported from a warm `.pyc`, a symlink
outside the repository, the branch name, the environment, the clock), and it saved about 50 s of an
8m39s run. It was removed on that risk-against-benefit, not repaired. Only a clean exit 0 is PASS.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import NamedTuple

import fixture_git

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = Path(".github/workflows/ci.yml")
CI_JOB = "verify"
DEFAULT_TIMEOUT = 300
BASE_REF = '"origin/$GITHUB_BASE_REF"'
PY_RUN = re.compile(r"^python3\s+(scripts/[\w.-]+\.py)(.*)$")
NESTED = "--nested-self-test"     # the self-test runs ITSELF under `run_gate` with this, so it recurses once

# CI steps that pass the `python3 scripts/…` shape but read something only an EARLIER CI step produces.
# A name here that no longer matches a step REFUSES the run, so the list cannot silently go stale.
NOT_LOCAL: dict[str, str] = {
    "Roadmap test counts match the suite": "reads jest-results.json, which only CI's `npm test` step writes",
}
# CI steps that run FULL in CI and SCOPED locally (backlog #402): the step's name -> the local arguments, `{base}`
# filled with `--base`. The full run is ~6 min under load and CI runs it on every PR anyway. A name here that no
# longer matches a step REFUSES the run, like NOT_LOCAL.
SCOPED_LOCALLY: dict[str, tuple[str, ...]] = {
    "Declared self-test counts match the suites": ("--changed", "--base", "origin/{base}"),
}
# The reason printed for a ci.yml job other than `verify`. A job not named here still prints, generically.
OTHER_JOBS: dict[str, str] = {
    "mutation-sweep": "the FULL mutation sweep, on CI's shards; locally only the slices for moved files run",
    "mutation-sweep-complete": "joins the sweep's shards into one required check",
}


def _load(alias: str, filename: str):
    spec = importlib.util.spec_from_file_location(alias, Path(__file__).with_name(filename))
    if spec is None or spec.loader is None:
        raise ImportError(f"{filename} cannot be loaded beside {Path(__file__).name}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[alias] = mod
    spec.loader.exec_module(mod)
    return mod


def _pin():
    return sys.modules.get("_g4pr_pin") or _load("_g4pr_pin", "check-python-pin.py")


def _merge_ready():
    return sys.modules.get("_g4pr_mr") or _load("_g4pr_mr", "check-merge-ready.py")


# ── the gate set ──────────────────────────────────────────────────────────────────────────────────


class Gate(NamedTuple):
    name: str                    # the CI step's name, or the mutation slice's
    script: str                  # repository-relative
    args: tuple[str, ...]
    source: str

    @property
    def mode(self) -> str:
        return " ".join(self.args) or "(no arguments)"


def step_keys(step) -> dict[str, str]:
    """PURE. A step's OWN keys — the dash line and the lines at its key indent, never a `run: |` body."""
    keys: dict[str, str] = {}
    lines = [step.body[0]] + [ln for ln in step.body[1:]
                             if len(ln) - len(ln.lstrip()) == step.indent + 2]
    for ln in lines:
        m = re.match(r"^\s*([A-Za-z_][\w-]*):\s*(.*?)\s*$", ln)
        if m and m.group(1) not in keys:
            keys[m.group(1)] = m.group(2)
    return keys


def ci_gates(workflow: str, base: str) -> tuple[list[Gate], list[tuple[str, str]], str | None]:
    """PURE. (gates, out-of-set steps and jobs with the reason, an error that makes the set underivable)."""
    blocks = _pin().job_blocks(workflow)
    if CI_JOB not in blocks:
        return [], [], f"the workflow has no `{CI_JOB}` job"
    pr_only = _merge_ready().PR_ONLY_COND
    gates: list[Gate] = []
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for step in _pin()._steps(blocks[CI_JOB]):
        keys = step_keys(step)
        run = keys.get("run")
        if run is None:
            continue                       # a `uses:` action — setup, not a gate
        name = keys.get("name") or run
        seen.add(name)
        if name in NOT_LOCAL:
            out.append((name, NOT_LOCAL[name]))
            continue
        cond = keys.get("if", "")
        if cond and not pr_only.search(cond):
            out.append((name, f"runs only when `{cond}`"))
            continue
        if run[:1] in ("|", ">"):
            out.append((name, "a multi-line CI step: it needs CI's own context (the PR body, step outputs)"))
            continue
        line = run.replace(BASE_REF, f"origin/{base}")
        m = PY_RUN.match(line)
        if not m:
            out.append((name, f"not a Python gate: `{run}`"))
            continue
        if "$" in line:
            out.append((name, "reads a variable only CI sets"))
            continue
        if name in SCOPED_LOCALLY:
            args = tuple(a.format(base=base) for a in SCOPED_LOCALLY[name])
            gates.append(Gate(name, m.group(1), args, f"ci.yml job {CI_JOB}, SCOPED locally"))
            out.append((f"{name} (full run)", "the FULL count check is CI's; locally only `--changed` runs"))
            continue
        gates.append(Gate(name, m.group(1), tuple(shlex.split(m.group(2))), f"ci.yml job {CI_JOB}"))
    if not gates:
        return [], out, f"the `{CI_JOB}` job yielded no Python gate — a parse that finds nothing is not a pass"
    stale = sorted(set(NOT_LOCAL) - seen)
    if stale:
        return [], [], f"NOT_LOCAL names a step the `{CI_JOB}` job no longer has: {', '.join(stale)}"
    stale = sorted(set(SCOPED_LOCALLY) - seen)
    if stale:
        return [], [], f"SCOPED_LOCALLY names a step the `{CI_JOB}` job no longer has: {', '.join(stale)}"
    for job in blocks:
        if job != CI_JOB:
            out.append((f"ci.yml job {job}", OTHER_JOBS.get(job, f"another CI job; this runner derives only `{CI_JOB}`")))
    return gates, out, None


def mutation_targets(changed: set[str], manifests: dict[str, set[str]]) -> list[str]:
    """PURE. Scripts whose mutation slice must run: named by a moved manifest, or moved themselves."""
    out: set[str] = set()
    for manifest, files in manifests.items():
        if manifest in changed:
            out |= files
        out |= files & changed
    return sorted(out)


def mutation_gates(targets: list[str]) -> list[Gate]:
    return [Gate(f"mutations of {t}", "scripts/check-plan-code.py", ("--mutate", ".", "--only", t),
                 "the local partial sweep (moved manifests only; CI runs them all)") for t in targets]


# ── running a gate ────────────────────────────────────────────────────────────────────────────────


class Outcome(NamedTuple):
    status: str                  # PASS | FAIL | CANNOT RUN | TIMEOUT | KILLED
    rc: int | None
    secs: float


def status_of(rc: int | None, timed_out: bool) -> str:
    """PURE. Only a clean exit 0 is a PASS; the repo's exit 2 is CANNOT RUN, never a pass."""
    if timed_out:
        return "TIMEOUT"
    if rc is None or rc < 0:
        return "KILLED"
    return {0: "PASS", 2: "CANNOT RUN"}.get(rc, "FAIL")


def exit_code(tally: dict[str, int]) -> int:
    """PURE. 1 if any gate FAILED; else 2 if any did not finish clean; 0 only when every gate PASSED."""
    if tally.get("FAIL"):
        return 1
    if any(n for s, n in tally.items() if s != "PASS"):
        return 2
    return 0


def run_gate(gate: Gate, root: Path, timeout: float, log: Path) -> Outcome:
    """Every path out is a status: a gate that cannot even be started is CANNOT RUN, never an unset exit."""
    start = time.monotonic()
    timed_out = False
    rc: int | None = None
    with open(log, "wb") as out:
        try:
            p = subprocess.Popen([sys.executable, gate.script, *gate.args], cwd=root, stdout=out,
                                 stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
        except OSError as e:
            out.write(f"gates-for-pr: the gate could not be started: {e}\n".encode())
            return Outcome("CANNOT RUN", None, time.monotonic() - start)
        try:
            rc = p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
        except BaseException:
            _kill(p)
            raise
        if timed_out:
            _kill(p)
            rc = p.returncode
    return Outcome(status_of(rc, timed_out), rc, time.monotonic() - start)


def _kill(p: subprocess.Popen) -> None:
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(p.pid, signal.SIGKILL)
    p.wait()


# ── the run ───────────────────────────────────────────────────────────────────────────────────────


def changed_paths(root: Path, base: str) -> tuple[set[str] | None, str]:
    def git(*a: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(root), *a], capture_output=True, text=True, timeout=120)
    mb = git("merge-base", f"origin/{base}", "HEAD")
    if mb.returncode != 0:
        return None, f"origin/{base} does not resolve here ({mb.stderr.strip()[:120]})"
    diff = git("diff", "--name-only", mb.stdout.strip())
    new = git("ls-files", "-o", "--exclude-standard")
    if diff.returncode or new.returncode:
        return None, "git could not list the moved files"
    return set(diff.stdout.split()) | set(new.stdout.split()), ""


def manifest_files(root: Path) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for m in sorted((root / "scripts" / "mutations").glob("*.json")):
        entries = json.loads(m.read_text())
        out[str(m.relative_to(root))] = {e["file"] for e in entries if isinstance(e, dict) and "file" in e}
    return out


def gate_set(root: Path, base: str) -> tuple[list[Gate], list[tuple[str, str]], str | None]:
    wf = root / WORKFLOW
    if not wf.is_file():
        return [], [], f"{WORKFLOW} is missing"
    gates, out, err = ci_gates(wf.read_text(), base)
    if err:
        return gates, out, err
    out.append(("schema-gates.yml", "needs CI's Postgres container — run scripts/check-schema-gates.sh"))
    changed, why = changed_paths(root, base)
    if changed is None:
        return gates, out, f"the mutation slices cannot be chosen: {why}"
    try:
        manifests = manifest_files(root)
    except (OSError, ValueError) as e:
        return gates, out, f"a mutation manifest is unreadable: {e}"
    return gates + mutation_gates(mutation_targets(changed, manifests)), out, None


def line(status: str, name: str, detail: str) -> str:
    return f"{status:<11} {name}  {detail}".rstrip()


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "gates-for-pr").split("\n")[0])
    ap.add_argument("--base", default="master")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="seconds per gate")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument(NESTED, action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    if a.self_test or a.nested_self_test:
        return self_test(a.nested_self_test)
    gates, out, err = gate_set(root, a.base)
    if err:
        print(f"CANNOT RUN — {err}. Treat this as NOT RUN.")
        return 2
    if a.list:
        for g in gates:
            print(line("GATE", g.name, f"{g.script} {g.mode} · {g.source}"))
        for name, why in out:
            print(line("OUT OF SET", name, f"— {why}"))
        return 0
    logs = Path(tempfile.mkdtemp(prefix="gates-for-pr-logs-"))
    print(f"gates-for-pr: {len(gates)} gates · logs {logs}", flush=True)
    tally: dict[str, int] = {}
    for i, g in enumerate(gates):
        log = logs / f"{i:03d}-{re.sub(r'[^A-Za-z0-9]+', '-', g.name)[:60]}.log"
        o = run_gate(g, root, a.timeout, log)
        tally[o.status] = tally.get(o.status, 0) + 1
        detail = f"({o.secs:.1f}s)" if o.status == "PASS" else \
            f"rc={o.rc} ({o.secs:.1f}s) · {log}" if o.status != "TIMEOUT" else \
            f"killed at {a.timeout:.0f}s · {log}"
        print(line(o.status, g.name, detail), flush=True)
    for name, why in out:
        print(line("OUT OF SET", name, f"— {why}"))
    order = ("PASS", "FAIL", "CANNOT RUN", "TIMEOUT", "KILLED")
    print("summary: " + " · ".join(f"{tally[s]} {s.lower()}" for s in order if tally.get(s))
          + f" · {len(out)} CI steps and jobs out of set (above)")
    return exit_code(tally)


# ── self-test ─────────────────────────────────────────────────────────────────────────────────────


def self_test(nested: bool = False) -> int:
    with fixture_git.isolated():
        return _self_test_body(nested)


def _self_test_body(nested: bool) -> int:
    results: list[tuple[str, bool]] = []

    def case(name: str, got, want) -> None:
        ok = got == want
        results.append((name, ok))
        if not ok:
            print(f"  [FAIL] {name}\n       got:  {got!r}\n       want: {want!r}")

    # ── the derivation, over a workflow text ──
    wf = WF_FIXTURE
    gates, out, err = ci_gates(wf, "master")
    case("a one-line python step is a gate, with its arguments",
         [(g.name, g.script, g.args) for g in gates][:2],
         [("gate a", "scripts/a.py", ("--self-test",)), ("gate b", "scripts/b.py", ())])
    case("a PR-only step is IN the set, its base ref rewritten to --base",
         [g.args for g in gates if g.name == "pr only"], [("--base", "origin/master")])
    case("...and to a different --base when one is given",
         [g.args for g in ci_gates(wf, "main")[0] if g.name == "pr only"], [("--base", "origin/main")])
    case("node, a multi-line block, another CI variable, a non-PR condition and every other job are OUT OF SET",
         sorted(n for n, _ in out), ["Declared self-test counts match the suites (full run)",
                                     "Roadmap test counts match the suite", "ci var", "ci.yml job mutation-sweep",
                                     "ci.yml job other-job", "multi", "node tests", "push only"])
    case("...the mutation-sweep job says it is the FULL sweep; an unnamed job says only verify is derived",
         [dict(out)["ci.yml job mutation-sweep"], dict(out)["ci.yml job other-job"]],
         [OTHER_JOBS["mutation-sweep"], "another CI job; this runner derives only `verify`"])
    case("...and a `uses:` action is neither", any(n.startswith("actions/") for n, _ in out), False)
    case("a step NOT_LOCAL names is out of set with that reason",
         "jest-results" in dict(out).get("Roadmap test counts match the suite", ""), True)
    case("a NOT_LOCAL name that no longer matches a step REFUSES the set (it cannot go stale silently)",
         ci_gates(wf.replace("name: Roadmap test counts", "name: Renamed test counts"), "master")[2],
         "NOT_LOCAL names a step the `verify` job no longer has: Roadmap test counts match the suite")
    case("the count-check step runs SCOPED locally (--changed against --base); its full run is out of set as CI's",
         ([(g.args, g.source) for g in gates if g.name == "Declared self-test counts match the suites"],
          dict(out)["Declared self-test counts match the suites (full run)"]),
         ([(("--changed", "--base", "origin/master"), "ci.yml job verify, SCOPED locally")],
          "the FULL count check is CI's; locally only `--changed` runs"))
    case("a SCOPED_LOCALLY name that no longer matches a step REFUSES the set",
         ci_gates(wf.replace("name: Declared self-test counts", "name: Renamed counts"), "master")[2],
         "SCOPED_LOCALLY names a step the `verify` job no longer has: Declared self-test counts match the suites")
    case("a workflow with no verify job cannot yield a set", ci_gates("jobs:\n  other:\n    steps: []\n", "m")[2],
         "the workflow has no `verify` job")
    case("a verify job with no python gate is CANNOT RUN, never an empty pass",
         "yielded no Python gate" in (ci_gates(WF_HEAD + "      - name: n\n        run: npm test\n", "m")[2] or ""),
         True)
    live = ci_gates((ROOT / WORKFLOW).read_text(), "master")
    case("the live ci.yml yields the namespace and fixture-variation gates, and prints its mutation-sweep job",
         ({"scripts/check-reference-namespace.py", "scripts/check-fixture-variation.py"} <= {g.script for g in live[0]},
          "ci.yml job mutation-sweep" in dict(live[1])), (True, True))
    # ── which mutation slices run ──
    mf = {"scripts/mutations/a.json": {"scripts/a.py"}, "scripts/mutations/b.json": {"scripts/b.py", "scripts/c.py"}}
    case("a moved script with a manifest gets its slice", mutation_targets({"scripts/a.py"}, mf), ["scripts/a.py"])
    case("a moved MANIFEST runs every script it names", mutation_targets({"scripts/mutations/b.json"}, mf),
         ["scripts/b.py", "scripts/c.py"])
    case("nothing moved, nothing runs", mutation_targets({"docs/x.md"}, {}), [])
    case("a slice is check-plan-code --mutate . --only <script>", mutation_gates(["scripts/a.py"])[0].args,
         ("--mutate", ".", "--only", "scripts/a.py"))
    case("...one slice per target, in order", [g.name for g in mutation_gates(["scripts/x.py", "scripts/y.py"])],
         ["mutations of scripts/x.py", "mutations of scripts/y.py"])
    # ── the status of an exit, and of a run ──
    case("exit 0 is the only PASS", [status_of(rc, False) for rc in (0, 1, 2, 3, -9, None)],
         ["PASS", "FAIL", "CANNOT RUN", "FAIL", "KILLED", "KILLED"])
    case("a timeout is TIMEOUT whatever the exit code", status_of(0, True), "TIMEOUT")
    case("the run is 0 only when every gate PASSED; a FAIL is 1; any other non-pass is 2",
         [exit_code({"PASS": 3}), exit_code({"PASS": 1, "FAIL": 1, "TIMEOUT": 1}), exit_code({"PASS": 1, "TIMEOUT": 1}),
          exit_code({"KILLED": 1}), exit_code({"CANNOT RUN": 1}), exit_code({})],
         [0, 1, 2, 2, 2, 0])
    # ── end to end: main() over a repository this case builds ──
    results.extend(_end_to_end())
    # ── the runner's own gate, run BY the runner (PR #465 r1: a nested tracer made this fail every time) ──
    if not nested:
        logd = Path(tempfile.mkdtemp(prefix="gates-for-pr-nest-"))
        me = Gate("gates-for-pr self-test", "scripts/gates-for-pr.py", (NESTED,), "self")
        o = run_gate(me, ROOT, 120, logd / "nested.log")
        case("this self-test PASSES when run_gate runs it, as the battery does", o.status, "PASS")
        if o.status == "PASS":
            shutil.rmtree(logd, ignore_errors=True)
        else:                              # a pointer, not the child's own [FAIL] lines: a case is named once
            print(f"       the nested run's output: {logd / 'nested.log'}")
    passed = sum(ok for _, ok in results)
    print(f"{passed}/{len(results)} cases passed")
    return 0 if passed == len(results) else 1


WF_HEAD = "on: [pull_request]\njobs:\n  verify:\n    runs-on: ubuntu-latest\n    steps:\n"
WF_FIXTURE = WF_HEAD + """\
      - uses: actions/checkout@v4
      - name: gate a
        run: python3 scripts/a.py --self-test
      - name: gate b
        run: python3 scripts/b.py
      - name: fails
        run: python3 scripts/h.py
      - name: cannot
        run: python3 scripts/d.py
      - name: slow
        run: python3 scripts/e.py
      - name: dies
        run: python3 scripts/k.py
      - name: pr only
        if: github.event_name == 'pull_request'
        run: python3 scripts/f.py --base "origin/$GITHUB_BASE_REF"
      - name: Declared self-test counts match the suites
        run: python3 scripts/c.py
      - name: node tests
        run: npm test
      - name: multi
        run: |
          python3 scripts/a.py
      - name: ci var
        run: python3 scripts/a.py --sha $GITHUB_SHA
      - name: push only
        if: github.event_name == 'push'
        run: python3 scripts/a.py
      - name: Roadmap test counts match the suite
        run: python3 scripts/a.py --results jest-results.json
  mutation-sweep:
    runs-on: ubuntu-latest
    steps:
      - name: sweep
        run: python3 scripts/check-plan-code.py --mutate .
  other-job:
    runs-on: ubuntu-latest
    steps:
      - run: true
"""

GATE_SCRIPTS = {
    "a.py": "from pathlib import Path\nPath({log!r}).open('a').write('a\\n')\n",
    "b.py": "from pathlib import Path\nPath({log!r}).open('a').write('b\\n')\n",
    "h.py": "import sys\nfrom pathlib import Path\nPath({log!r}).open('a').write('h\\n')\nsys.exit(1)\n",
    "d.py": "import sys\nfrom pathlib import Path\nPath({log!r}).open('a').write('d\\n')\nsys.exit(2)\n",
    "e.py": "import time\nfrom pathlib import Path\nPath({log!r}).open('a').write('e\\n')\ntime.sleep(30)\n",
    "k.py": "import os, signal\nfrom pathlib import Path\nPath({log!r}).open('a').write('k\\n')\n"
            "os.kill(os.getpid(), signal.SIGKILL)\n",
    "f.py": "from pathlib import Path\nPath({log!r}).open('a').write('f\\n')\n",
    "c.py": "from pathlib import Path\nPath({log!r}).open('a').write('c\\n')\n",
}


def _end_to_end() -> list[tuple[str, bool]]:
    res: list[tuple[str, bool]] = []

    def case(name: str, got, want) -> None:
        ok = got == want
        res.append((name, ok))
        if not ok:
            print(f"  [FAIL] {name}\n       got:  {got!r}\n       want: {want!r}")

    tmp = Path(tempfile.mkdtemp(prefix="gates-for-pr-st-"))
    try:
        repo, runs, empty = tmp / "repo", tmp / "runs.log", tmp / "empty"
        (repo / "scripts" / "mutations").mkdir(parents=True)
        (repo / ".github" / "workflows").mkdir(parents=True)
        (repo / WORKFLOW).write_text(WF_FIXTURE)
        for n, body in GATE_SCRIPTS.items():
            (repo / "scripts" / n).write_text(body.format(log=str(runs)))
        empty.mkdir()

        def git(*a: str) -> None:
            subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True,
                           env=fixture_git.env(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@e",
                                               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@e"))
        git("init", "-q", "-b", "master")
        git("add", "-A")
        git("commit", "-q", "-m", "one")
        git("update-ref", "refs/remotes/origin/master", "HEAD")

        def run(*extra: str) -> tuple[int, str, list[str]]:
            runs.write_text("")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = main(["--timeout", "1.5", *extra], root=repo)
            return rc, buf.getvalue(), runs.read_text().split()

        def listing(*extra: str) -> tuple[int, str]:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = main(["--list", *extra], root=repo)
            return rc, buf.getvalue()

        def status(out: str, name: str) -> str:
            for ln in out.splitlines():
                if re.match(rf"^\S+(?: RUN| OF SET)?\s+{re.escape(name)}(\s|$)", ln):
                    return ln.split("  ")[0].strip()
            return "MISSING"

        rc, out = listing()
        case("--list names the gates and runs nothing",
             (rc, "GATE        gate a  scripts/a.py --self-test" in out, runs.exists()), (0, True, False))
        case("...and nothing moved, so no mutation slice is in the set", "mutations of" in out, False)

        rc, out, ran = run()
        case("every gate in the set executes once", sorted(ran), ["a", "b", "c", "d", "e", "f", "h", "k"])
        case("...a and b PASS, h FAIL, d CANNOT RUN, e TIMEOUT, k KILLED",
             [status(out, n) for n in ("gate a", "gate b", "fails", "cannot", "slow", "dies")],
             ["PASS", "PASS", "FAIL", "CANNOT RUN", "TIMEOUT", "KILLED"])
        case("...a FAIL makes the run 1", rc, 1)
        case("...the summary counts every non-pass by its own name, never as a pass",
             re.search(r"^summary: 4 pass · 1 fail · 1 cannot run · 1 timeout · 1 killed · ", out, re.M) is not None,
             True)
        case("...out-of-set steps and jobs are printed, not hidden",
             [status(out, n) for n in ("node tests", "ci.yml job mutation-sweep", "schema-gates.yml")],
             ["OUT OF SET"] * 3)

        rc, out, ran = run()
        case("a second run over an unchanged tree runs every gate AGAIN — nothing is skipped",
             (sorted(ran), "SKIPPED" in out), (["a", "b", "c", "d", "e", "f", "h", "k"], False))

        (repo / WORKFLOW).write_text(WF_FIXTURE.replace("        run: python3 scripts/h.py\n", "        run: python3 scripts/a.py\n"))
        rc, out, ran = run()
        case("with no FAIL, a TIMEOUT, a KILLED or a CANNOT RUN makes the run 2, not green", rc, 2)

        (repo / "scripts" / "mutations" / "a.json").write_text(json.dumps([{"file": "scripts/a.py"}]))
        rc, out = listing()
        case("a moved (untracked) manifest puts its script's mutation slice in the set",
             "GATE        mutations of scripts/a.py  scripts/check-plan-code.py --mutate . --only scripts/a.py" in out,
             True)

        o = run_gate(Gate("fails", "scripts/h.py", (), "t"), repo, 5, tmp / "h.log")
        case("run_gate alone: exit 1 is FAIL, and the gate's output is in its log",
             (o.status, o.rc, (tmp / "h.log").exists()), ("FAIL", 1, True))
        o = run_gate(Gate("missing", "scripts/no-such.py", (), "t"), repo, 5, tmp / "m.log")
        case("a gate script that does not exist is CANNOT RUN (python's exit 2), never green",
             (o.status, o.rc), ("CANNOT RUN", 2))
        o = run_gate(Gate("unstartable", "scripts/a.py", (), "t"), tmp / "no-such-dir", 5, tmp / "u.log")
        case("a gate that cannot even be STARTED is CANNOT RUN with no exit code, and the log says why",
             (o.status, o.rc, "could not be started" in (tmp / "u.log").read_text()), ("CANNOT RUN", None, True))

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main(["--timeout", "1.5", "--base", "no-such-base"], root=repo)
        case("a --base that does not resolve is CANNOT RUN, and nothing runs",
             (rc, buf.getvalue().startswith("CANNOT RUN")), (2, True))

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main(["--timeout", "1.5"], root=empty)
        case("a root with no workflow is CANNOT RUN, and nothing runs", (rc, buf.getvalue().startswith("CANNOT RUN")),
             (2, True))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return res


if __name__ == "__main__":
    sys.exit(main())
