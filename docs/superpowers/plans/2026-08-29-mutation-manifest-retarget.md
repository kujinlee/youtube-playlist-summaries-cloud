# Mutation Manifest Retarget — Implementation Plan

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them — without reading the chat transcript.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Spec:** [`docs/superpowers/specs/2026-08-29-mutation-manifest-retarget-design.md`](../specs/2026-08-29-mutation-manifest-retarget-design.md) · **Closes:** backlog #70

**Goal:** Move the 43-entry mutation manifest out of a planning document and onto the delivered
scripts, so CI mutation-tests the code that ships and the plan stops being a CI dependency.

**Architecture:** `scripts/check-plan-code.py` keeps its mutation engine verbatim; the engine is
extracted into a reusable function and given a second caller that mutates a copy of the **delivered**
`scripts/` tree instead of a copy assembled from the plan. The manifest becomes two JSON data files
under `scripts/mutations/`. The plan's `--compare --verify-evidence` CI step is deleted and its
1,401 lines of duplicated source are replaced with pointers.

**Tech Stack:** Python 3 stdlib only (`argparse`, `json`, `pathlib`, `shutil`, `subprocess`,
`tempfile`). No new dependencies. No TypeScript touched.

---

## Global Constraints

- **This plan contains NO `<!-- file: -->` blocks and must never gain one.** Reintroducing one
  recreates the exact coupling this work removes. **Verified, not asserted** — running the tool's own
  parser over this document reports `files parsed: {}`:

  ```bash
  python3 - <<'EOF'
  import importlib.util, pathlib, sys
  s = importlib.util.spec_from_file_location("cpc", "scripts/check-plan-code.py")
  m = importlib.util.module_from_spec(s); sys.modules["cpc"] = m; s.loader.exec_module(m)
  f, mu, _, _ = m.extract(pathlib.Path(
      "docs/superpowers/plans/2026-08-29-mutation-manifest-retarget.md").read_text())
  assert not f and not mu, f"THIS PLAN GREW A CODE BLOCK: {list(f)}, {len(mu)} mutations"
  print("clean: no assembled files, no mutations")
  EOF
  ```

  (The four `<!-- file: … -->` strings in this document are prose mentions inside backticks or code
  lines. `FILE_TAG` is anchored to a whole line, so none of them parse as tags — which is why the
  check above is run rather than reasoned about.)
- **`scripts/check-plan-code.py`'s docstring declares its case count** — line 8,
  `# 121 cases`. `_drift_rc` fails the suite when the count disagrees. **Every task that adds
  self-test cases MUST update that number in the same commit**, or the suite goes red for a reason
  unrelated to the task.
- **Existing mutation-engine behaviour is not to be changed.** Refuse-on-missing-anchor,
  refuse-on-ambiguous-anchor, rc=2-is-CANNOT-RUN, and red-via-the-exactly-named-case were each
  bought with a review round. Task 1 moves them; no task alters them.
- **Never mutate a repo-tracked file.** All mutation work happens on a copy in a temp directory.
- **No mutation table is reported without a green control first.** A harness whose unmutated copy
  fails proves nothing.
- Python version floor: whatever CI uses (Node 22 job; `python3` is the system interpreter).
- The 43 manifest entries are **moved verbatim**. No entry is re-authored, re-worded, or re-ordered.

---

## File Structure

| File | Responsibility |
|---|---|
| `scripts/check-plan-code.py` | **Modify.** Extract the mutation loop; add `--mutate ROOT`; add the count ratchet; add self-test cases. |
| `scripts/mutations/gen-dashboard.json` | **Create.** 32 entries, verbatim from the plan. |
| `scripts/mutations/check-dashboard-entry.json` | **Create.** 11 entries, verbatim from the plan. |
| `.github/workflows/ci.yml` | **Modify.** Replace the plan step with the mutation run. |
| `docs/superpowers/plans/2026-08-28-project-dashboard-plan.md` | **Modify.** Delete 12 code blocks + the mutations block + the evidence block; add pointers. |
| `docs/backlog.md` | **Modify.** Close #70. |
| `docs/roadmap-to-launch.md` | **Modify.** Tick the step. |
| `docs/dashboard-entries.md` | **Modify.** One entry. |

---

## Task 1: Extract the mutation loop so it has two callers

**Why first:** every later task needs a mutation runner that is not welded to plan assembly. This is
a pure refactor — same behaviour, same 121 cases, new seam.

**Files:**
- Modify: `scripts/check-plan-code.py` (`check()` at `:288-430`)

**Interfaces:**
- Produces: `run_mutations(d: pathlib.Path, muts: list[dict], known: set[str]) -> tuple[bool, list[str], list[dict], list[str]]`
  returning `(ok, report, ev_mutations, ev_survivors)`. `d` is a directory holding runnable scripts;
  `known` is the set of file paths that exist in `d` and may be targeted.

- [ ] **Step 1: Record the pre-refactor baseline, so "unchanged" is a measurement**

```bash
cd /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
python3 scripts/check-plan-code.py --self-test | tail -1
python3 scripts/check-plan-code.py docs/superpowers/plans/2026-08-28-project-dashboard-plan.md \
        --compare . --verify-evidence | tail -1
```

Expected, and both must be copied into the Task 1 commit message:
```
121/121 passed
OK — compared + evidence-verified: 2 file(s), 43 mutation(s), 0 survivor(s)
```

- [ ] **Step 2: Write the failing test for the new seam**

Add to `_self_test()` in `scripts/check-plan-code.py`, immediately before the final
`return _drift_rc(__doc__, ok, fail)`:

```python
    # ⟲ Task 1. The mutation loop gained a second caller (--mutate). These cases pin the
    # EXTRACTED function directly, so a later change to --mutate cannot quietly alter the
    # behaviour the plan path depends on.
    with tempfile.TemporaryDirectory() as _td:
        _d = pathlib.Path(_td)
        (_d / "m.py").write_text(
            'def f():\n    return 1\n\n\n'
            'def _self_test():\n'
            '    if f() != 1:\n'
            '        print("  [FAIL] f returns one: got %r" % f())\n'
            '        return 1\n'
            '    print("1/1 passed")\n'
            '    return 0\n\n\n'
            'import sys\n'
            'if __name__ == "__main__":\n'
            '    sys.exit(_self_test())\n')
        _mut = [{"name": "f returns two", "file": "m.py",
                 "edits": [["return 1", "return 2"]],
                 "expect": "f returns one"}]
        _ok, _rep, _evm, _evs = run_mutations(_d, _mut, {"m.py"})
        case("run_mutations catches a real mutation", (_ok, _evs), (True, []))
        case("run_mutations records the caught mutation", len(_evm), 1)
        _bad = [{"name": "anchor not there", "file": "m.py",
                 "edits": [["return 99", "return 2"]], "expect": "f returns one"}]
        _ok2, _rep2, _, _ = run_mutations(_d, _bad, {"m.py"})
        case("run_mutations refuses a missing anchor",
             (_ok2, any("anchor NOT FOUND" in r for r in _rep2)), (False, True))
        _unknown = [{"name": "elsewhere", "file": "nope.py",
                     "edits": [["a", "b"]], "expect": "x"}]
        _ok3, _rep3, _, _ = run_mutations(_d, _unknown, {"m.py"})
        case("run_mutations refuses an unknown target file",
             (_ok3, any("unknown file" in r for r in _rep3)), (False, True))
```

- [ ] **Step 3: Run it and confirm it fails for the right reason**

```bash
python3 scripts/check-plan-code.py --self-test 2>&1 | tail -5
```

Expected: `NameError: name 'run_mutations' is not defined`. **If it fails any other way, stop** —
the test is not testing what it claims.

- [ ] **Step 4: Extract the function**

Cut the block in `check()` that begins `for mut in muts:` (currently `:324`) and ends at the close of
the `elif unnamed:` arm (currently `:429`). Move it verbatim into a new module-level function placed
immediately **above** `def check(`:

```python
def run_mutations(d: pathlib.Path, muts: list[dict],
                  known: set[str]) -> tuple[bool, list[str], list[dict], list[str]]:
    """Apply each mutation to a file in `d`, run its suite, require red via the named case.

    `d` holds runnable scripts — assembled from a plan, or copied from the delivered tree.
    This function does not care which, and that indifference is the whole point of Task 1:
    the guarantee is about the mutation discipline, not about where the code came from.

    Returns (ok, report, ev_mutations, ev_survivors). NOTHING here changed when it was
    extracted; every guard below was bought with a review round, so a diff that alters
    behaviour is a defect in the refactor, not an improvement.
    """
    ok, report, ev_muts, ev_survivors = True, [], [], []
    for mut in muts:
        ...  # the moved body, with the substitutions in Step 5
    return ok, report, ev_muts, ev_survivors
```

- [ ] **Step 5: Rewire the moved body's four references**

Inside the moved body, make exactly these substitutions and no others:

| Was | Becomes |
|---|---|
| `if fname not in files:` | `if fname not in known:` |
| `ev["mutations"].append(...)` | `ev_muts.append(...)` |
| `ev["survivors"].append(name)` | `ev_survivors.append(name)` |
| `ok = False` | `ok = False` (unchanged — `ok` is now local) |

In `check()`, replace the removed block with:

```python
        m_ok, m_report, m_muts, m_survivors = run_mutations(d, muts, set(files))
        if not m_ok:
            ok = False
        report.extend(m_report)
        ev["mutations"].extend(m_muts)
        ev["survivors"].extend(m_survivors)
```

- [ ] **Step 6: Bump the declared case count**

`scripts/check-plan-code.py` line 8: `# 121 cases` → `# 125 cases` (four cases added in Step 2).

- [ ] **Step 7: Prove the refactor changed nothing**

```bash
python3 scripts/check-plan-code.py --self-test | tail -1
python3 scripts/check-plan-code.py docs/superpowers/plans/2026-08-28-project-dashboard-plan.md \
        --compare . --verify-evidence | tail -1
```

Expected: `125/125 passed` and the **identical** `OK — compared + evidence-verified: 2 file(s),
43 mutation(s), 0 survivor(s)` from Step 1. A different mutation or survivor count means the
extraction changed behaviour — revert and redo.

⚠ The evidence block in the plan records `121/121`-era output for the two *dashboard* scripts, not
for `check-plan-code.py`, so it does **not** need regenerating here. If `--verify-evidence` reports
staleness at this step, that is a real finding: stop and report it.

- [ ] **Step 8: Commit**

```bash
git add scripts/check-plan-code.py
git commit -m "refactor(#70): give the mutation loop a second caller, changing nothing else

Pure extraction. run_mutations() takes a directory of runnable scripts and is
indifferent to whether they were assembled from a plan or copied from the
delivered tree — which is the seam --mutate needs.

Behaviour pinned by measurement, not inspection: 43 mutations / 0 survivors
before and after, and four new cases exercise the extracted function directly
so a later --mutate change cannot silently alter the plan path.

121 -> 125 cases."
```

---

## Task 2: The manifests become data files beside the code

**Files:**
- Create: `scripts/mutations/gen-dashboard.json`, `scripts/mutations/check-dashboard-entry.json`
- Modify: `scripts/check-plan-code.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `load_manifests(root: pathlib.Path) -> tuple[list[dict], list[str]]` returning
  `(mutations, problems)`. `problems` non-empty means CANNOT RUN.

- [ ] **Step 1: Generate the manifests from the plan — by script, never by hand**

The entries must be byte-faithful. Hand-copying 43 JSON objects containing exact source strings is
how anchors get corrupted.

```bash
cd /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
mkdir -p scripts/mutations
python3 - <<'PYEOF'
import importlib.util, json, pathlib, sys
s = importlib.util.spec_from_file_location("cpc", "scripts/check-plan-code.py")
m = importlib.util.module_from_spec(s); sys.modules["cpc"] = m; s.loader.exec_module(m)
plan = pathlib.Path("docs/superpowers/plans/2026-08-28-project-dashboard-plan.md")
_, muts, problems, _ = m.extract(plan.read_text())
assert not problems, f"plan does not parse cleanly, refusing: {problems}"
assert len(muts) == 43, f"expected 43 entries, found {len(muts)} — refusing"
by = {}
for x in muts:
    by.setdefault(x["file"], []).append(x)
for target, entries in sorted(by.items()):
    stem = pathlib.Path(target).stem
    out = pathlib.Path(f"scripts/mutations/{stem}.json")
    out.write_text(json.dumps(entries, indent=1, ensure_ascii=False) + "\n")
    print(f"  {out}  {len(entries)} entries")
PYEOF
```

Expected:
```
  scripts/mutations/check-dashboard-entry.json  11 entries
  scripts/mutations/gen-dashboard.json  32 entries
```

- [ ] **Step 2: Prove the round-trip is lossless**

```bash
python3 - <<'PYEOF'
import importlib.util, json, pathlib, sys
s = importlib.util.spec_from_file_location("cpc", "scripts/check-plan-code.py")
m = importlib.util.module_from_spec(s); sys.modules["cpc"] = m; s.loader.exec_module(m)
_, muts, _, _ = m.extract(pathlib.Path("docs/superpowers/plans/2026-08-28-project-dashboard-plan.md").read_text())
from_files = []
for p in sorted(pathlib.Path("scripts/mutations").glob("*.json")):
    from_files.extend(json.loads(p.read_text()))
key = lambda x: (x["file"], x["name"])
assert sorted(muts, key=key) == sorted(from_files, key=key), "ROUND TRIP LOST DATA — refusing"
print(f"round-trip lossless: {len(from_files)} entries identical to the plan's")
PYEOF
```

Expected: `round-trip lossless: 43 entries identical to the plan's`. **A mismatch stops the task.**

- [ ] **Step 3: Write the failing test for `load_manifests`**

Add to `_self_test()` before `return _drift_rc(...)`:

```python
    # ⟲ Task 2. The manifest FILENAME names the target script, and an entry whose `file`
    # key disagrees is refused rather than silently believed — a redundancy that fails
    # loudly instead of drifting.
    with tempfile.TemporaryDirectory() as _td:
        _r = pathlib.Path(_td)
        (_r / "scripts" / "mutations").mkdir(parents=True)
        (_r / "scripts" / "thing.py").write_text("x = 1\n")
        _man = _r / "scripts" / "mutations" / "thing.json"
        _man.write_text(json.dumps([{"name": "n", "file": "scripts/thing.py",
                                     "edits": [["x = 1", "x = 2"]], "expect": "e"}]))
        _m, _p = load_manifests(_r)
        case("load_manifests reads a well-formed manifest", (len(_m), _p), (1, []))

        _man.write_text(json.dumps([{"name": "n", "file": "scripts/OTHER.py",
                                     "edits": [["a", "b"]], "expect": "e"}]))
        _m, _p = load_manifests(_r)
        case("a `file` key disagreeing with the manifest NAME is refused",
             any("disagrees" in x for x in _p), True)

        _man.write_text(json.dumps([]))
        _m, _p = load_manifests(_r)
        case("an EMPTY manifest is a refusal, not zero work",
             any("no entries" in x for x in _p), True)

        (_r / "scripts" / "mutations" / "ghost.json").write_text(
            json.dumps([{"name": "n", "file": "scripts/ghost.py",
                         "edits": [["a", "b"]], "expect": "e"}]))
        _m, _p = load_manifests(_r)
        case("a manifest naming a script that does not exist is refused",
             any("does not exist" in x for x in _p), True)

    with tempfile.TemporaryDirectory() as _td:
        _r = pathlib.Path(_td)
        (_r / "scripts" / "mutations").mkdir(parents=True)
        _m, _p = load_manifests(_r)
        case("NO manifests at all is CANNOT RUN, never a silent pass",
             any("no manifests" in x for x in _p), True)
```

- [ ] **Step 4: Run it and confirm it fails**

```bash
python3 scripts/check-plan-code.py --self-test 2>&1 | tail -5
```

Expected: `NameError: name 'load_manifests' is not defined`.

- [ ] **Step 5: Implement `load_manifests`**

Add `import json` to the imports if absent, and place this immediately above `run_mutations`:

```python
MANIFEST_DIR = "scripts/mutations"


def load_manifests(root: pathlib.Path) -> tuple[list[dict], list[str]]:
    """Read every `scripts/mutations/<stem>.json` under `root`.

    The FILENAME is the authority on which script an entry targets; each entry's `file`
    key must agree with it. Two statements of one fact, checked against each other — a
    copy-paste that retargets an entry is caught, where a single unchecked statement
    would be believed.

    An empty manifest, a missing target, or no manifests at all are all REFUSALS. A
    mutation run that measured nothing must not be readable as a run that found nothing.
    """
    d = root / MANIFEST_DIR
    if not d.is_dir():
        return [], [f"CANNOT RUN — no manifests: {d} is not a directory"]
    out, problems = [], []
    files = sorted(d.glob("*.json"))
    if not files:
        return [], [f"CANNOT RUN — no manifests found in {d}"]
    for man in files:
        target = f"scripts/{man.stem}.py"
        if not (root / target).is_file():
            problems.append(f"{man.name}: target {target} does not exist under {root}")
            continue
        try:
            entries = json.loads(man.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            problems.append(f"{man.name}: not valid JSON — {exc}")
            continue
        if not isinstance(entries, list) or not entries:
            problems.append(f"{man.name}: no entries — an empty manifest measures nothing")
            continue
        for e in entries:
            if e.get("file") != target:
                problems.append(f"{man.name}: entry {e.get('name')!r} has file "
                                f"{e.get('file')!r}, which disagrees with the manifest "
                                f"name (expected {target!r})")
                continue
            out.append(e)
    return out, problems
```

- [ ] **Step 6: Bump the count and run**

Line 8: `# 125 cases` → `# 130 cases`.

```bash
python3 scripts/check-plan-code.py --self-test | tail -1
```

Expected: `130/130 passed`.

- [ ] **Step 7: Commit**

```bash
git add scripts/check-plan-code.py scripts/mutations/
git commit -m "feat(#70): the mutation manifest becomes data beside the code it mutates

43 entries moved verbatim from the plan by script, never by hand — these are
exact source strings and hand-copying is how anchors get corrupted. Round-trip
proved lossless against the plan's own parser before committing.

The manifest FILENAME is the authority on the target script and each entry's
file key must agree, so a copy-paste that retargets an entry is caught rather
than believed. An empty manifest, a missing target and no manifests at all are
all refusals: a run that measured nothing must not read as a run that found
nothing.

125 -> 130 cases."
```

---

## Task 3: `--mutate ROOT` runs the manifest against the delivered scripts

**Files:**
- Modify: `scripts/check-plan-code.py`

**Interfaces:**
- Consumes: `run_mutations` (Task 1), `load_manifests` (Task 2).
- Produces: `mutate_delivered(root: pathlib.Path) -> tuple[bool, list[str], dict]`, and the
  `--mutate ROOT` CLI flag.

- [ ] **Step 1: Write the failing test, including the control falsifier**

```python
    # ⟲ Task 3. The WHOLE scripts/ tree is copied, not the targeted files: gen-dashboard.py
    # loads check-dashboard-entry.py as a sibling at import time, and generators here resolve
    # a repo root from their own path. MEASURED 2026-08-29 — three separate hand-run mutation
    # harnesses reported a red or meaningless control on first use for exactly this reason.
    with tempfile.TemporaryDirectory() as _td:
        _r = pathlib.Path(_td)
        (_r / "scripts" / "mutations").mkdir(parents=True)
        (_r / "scripts" / "helper.py").write_text("VALUE = 1\n")
        (_r / "scripts" / "thing.py").write_text(
            'import pathlib, sys\n'
            'VALUE = int((pathlib.Path(__file__).parent / "helper.py")\n'
            '            .read_text().split("=")[1])\n'
            'def _self_test():\n'
            '    if VALUE != 1:\n'
            '        print("  [FAIL] value is one: got %r" % VALUE)\n'
            '        return 1\n'
            '    print("1/1 passed")\n'
            '    return 0\n'
            'if __name__ == "__main__":\n'
            '    sys.exit(_self_test())\n')
        (_r / "scripts" / "mutations" / "thing.json").write_text(json.dumps(
            [{"name": "value is two", "file": "scripts/thing.py",
              "edits": [["VALUE != 1", "VALUE != 2"]], "expect": "value is one"}]))
        _ok, _rep, _ev = mutate_delivered(_r)
        case("--mutate catches a mutation in the DELIVERED tree", _ok, True)
        case("...and the sibling import survived the copy, so the control was green",
             any("control" in r.lower() for r in _rep), False)

        # The falsifier for the instrument itself: break the UNMUTATED script. Every
        # mutation would then 'go red', and a harness without a control check would
        # report a full table of catches over a suite that never worked.
        (_r / "scripts" / "helper.py").write_text("VALUE = 99\n")
        _ok2, _rep2, _ = mutate_delivered(_r)
        case("a RED control is refused, not reported as 43 catches",
             (_ok2, any("control" in r.lower() for r in _rep2)), (False, True))
```

- [ ] **Step 2: Run it and confirm it fails**

```bash
python3 scripts/check-plan-code.py --self-test 2>&1 | tail -5
```

Expected: `NameError: name 'mutate_delivered' is not defined`.

- [ ] **Step 3: Implement `mutate_delivered`**

Add `import shutil` to the imports. Place below `load_manifests`:

```python
def mutate_delivered(root: pathlib.Path) -> tuple[bool, list[str], dict]:
    """Mutate the DELIVERED scripts, not a copy assembled from a document.

    The whole `scripts/` tree is copied because these scripts import each other as
    siblings and resolve a repo root from their own path; copying only the targeted
    files gives a red control, and a mutation table over a red control is not evidence.
    """
    muts, problems = load_manifests(root)
    ev = {"files": {}, "mutations": [], "survivors": [], "tally": {}, "compared": None}
    if problems:
        return False, problems, ev
    targets = sorted({m["file"] for m in muts})
    with tempfile.TemporaryDirectory() as td:
        d = pathlib.Path(td)
        shutil.copytree(root / "scripts", d / "scripts")
        report = []
        # THE CONTROL, FIRST. Every 'caught' below is a claim that the suite went red
        # BECAUSE of the mutation; that claim is empty unless the suite is green without it.
        for name in targets:
            rc, out = run_suite(d, name)
            ev["files"][name] = {"rc": rc, "tail": (out.split("\n")[-1] if out else ""),
                                 "blocks": None}
            if rc != 0:
                report.append(f"CANNOT RUN — control run of {name} exited {rc} BEFORE any "
                              f"mutation was applied. Every verdict below would be an "
                              f"artefact. Treat this as NOT CHECKED.\n    {out[-400:]}")
        if report:
            return False, report, ev
        ok, m_report, m_muts, m_survivors = run_mutations(d, muts, set(targets))
        ev["mutations"], ev["survivors"] = m_muts, m_survivors
        return ok, m_report, ev
```

⚠ `run_suite(d, name)` runs `[sys.executable, name, "--self-test"]` with `cwd=d`, so `name` must be
the repo-relative path (`scripts/gen-dashboard.py`) — which is exactly what the manifest's `file`
key holds. Do not strip it to a basename.

- [ ] **Step 4: Wire up the CLI**

In `main()`, add after the `--compare` argument:

```python
    ap.add_argument("--mutate", metavar="ROOT",
                    help="Mutate the DELIVERED scripts under ROOT, reading manifests from "
                         "ROOT/scripts/mutations/<script>.json. No plan is involved: this is "
                         "the mode that makes the evidence about the code that ships.")
```

And immediately after `if a.self_test: return _self_test()`:

```python
    if a.mutate:
        mroot = pathlib.Path(a.mutate)
        if not mroot.is_dir():
            print(f"CANNOT RUN — --mutate {mroot} is not a directory. NOT CHECKED.",
                  file=sys.stderr)
            return 2
        ok, report, ev = mutate_delivered(mroot)
        for r in report:
            print(f"  ✗ {r}")
        print(("OK — " if ok else "FAILED — ")
              + f"delivered scripts mutated: {len(ev['files'])} file(s), "
                f"{len(ev['mutations'])} mutation(s), {len(ev['survivors'])} survivor(s)")
        return 0 if ok else 1
```

⚠ Place this **before** the `if not a.plan:` guard, or `--mutate` with no plan argument exits 2.

- [ ] **Step 5: Bump the count and run the suite**

Line 8: `# 130 cases` → `# 133 cases`.

```bash
python3 scripts/check-plan-code.py --self-test | tail -1
```

Expected: `133/133 passed`.

- [ ] **Step 6: Run it against the real repo — the first time this measures the shipped code**

```bash
python3 scripts/check-plan-code.py --mutate .
```

Expected: `OK — delivered scripts mutated: 2 file(s), 43 mutation(s), 0 survivor(s)`

**If any mutation SURVIVES here, that is a real finding about the delivered scripts, not a bug in
this task.** It would mean the plan's copy and the delivered file differ in a way `--compare` did not
catch, or a guard covers the assembled form only. Stop and report it.

- [ ] **Step 7: Commit**

```bash
git add scripts/check-plan-code.py
git commit -m "feat(#70): --mutate runs the manifest against the code that actually ships

The mutation target stops being a copy assembled from a document and becomes the
delivered scripts/ tree. Same engine, different subject — which is the whole
guarantee: the evidence now describes the files CI runs.

The entire scripts/ tree is copied, not the two targets: these scripts import
each other as siblings and resolve a repo root from their own path. Measured
2026-08-29 — three separate hand-run harnesses reported a red or meaningless
control on first use for exactly that reason.

The control runs FIRST and a red one is refused. A mutation table over a suite
that was already failing is a full page of artefacts that reads like proof, and
that failure mode is now unreachable rather than merely unlikely.

130 -> 133 cases."
```

---

## Task 4: The coverage ratchet — deleting an entry must not be silent

**Files:**
- Modify: `scripts/check-plan-code.py`

**Interfaces:**
- Consumes: `load_manifests` (Task 2), `mutate_delivered` (Task 3).
- Produces: `EXPECTED_MUTATIONS: dict[str, int]` and a check inside `mutate_delivered`.

- [ ] **Step 1: Write the failing test**

```python
    # ⟲ Task 4. Once the manifest is a data file, deleting an entry narrows coverage while
    # CI stays green — a guard whose own removal is invisible (backlog #69's class, and the
    # exact shape found in CONTRAST_MIN on 2026-08-29, where one token disabled a whole
    # check at 111/111). The expected count lives in the RUNNER, not the manifest, so
    # shrinking coverage requires editing a second file that a reviewer will see.
    case("the declared counts name every manifest that ships",
         sorted(EXPECTED_MUTATIONS), ["scripts/check-dashboard-entry.py",
                                      "scripts/gen-dashboard.py"])
    case("the declared counts are the real ones", sum(EXPECTED_MUTATIONS.values()), 43)
    with tempfile.TemporaryDirectory() as _td:
        _r = pathlib.Path(_td)
        (_r / "scripts" / "mutations").mkdir(parents=True)
        (_r / "scripts" / "gen-dashboard.py").write_text(
            'def _self_test():\n    print("1/1 passed")\n    return 0\n'
            'import sys\n'
            'if __name__ == "__main__":\n    sys.exit(_self_test())\n')
        (_r / "scripts" / "mutations" / "gen-dashboard.json").write_text(json.dumps(
            [{"name": "only one", "file": "scripts/gen-dashboard.py",
              "edits": [["print", "print"]], "expect": "x"}]))
        _ok, _rep, _ = mutate_delivered(_r)
        case("a SHRUNKEN manifest is refused by name and number",
             (_ok, any("expected 32" in r for r in _rep)), (False, True))
```

- [ ] **Step 2: Run it and confirm it fails**

```bash
python3 scripts/check-plan-code.py --self-test 2>&1 | tail -5
```

Expected: `NameError: name 'EXPECTED_MUTATIONS' is not defined`.

- [ ] **Step 3: Implement the ratchet**

Place beside `MANIFEST_DIR`:

```python
# How many mutations each delivered script is covered by. EXACT, not a floor: adding a
# mutation should also be a visible act, and a floor drifts downward the moment somebody
# adds one without saying so.
#
# ⚠ This lives in the RUNNER, deliberately, not in the manifest. A count stored beside the
# entries it counts is edited in the same breath as deleting one, which is no guard at all.
EXPECTED_MUTATIONS = {
    "scripts/gen-dashboard.py": 32,
    "scripts/check-dashboard-entry.py": 11,
}
```

In `mutate_delivered`, immediately after the `if problems:` early return:

```python
    counts = {}
    for m in muts:
        counts[m["file"]] = counts.get(m["file"], 0) + 1
    drift = []
    for target, want in sorted(EXPECTED_MUTATIONS.items()):
        got = counts.get(target, 0)
        if got != want:
            drift.append(f"{target}: manifest holds {got} mutation(s), expected {want}. "
                         f"Coverage cannot change silently — if this is deliberate, change "
                         f"EXPECTED_MUTATIONS in {pathlib.Path(__file__).name} in the same "
                         f"commit and say why in the message")
    for target in sorted(set(counts) - set(EXPECTED_MUTATIONS)):
        drift.append(f"{target}: {counts[target]} mutation(s) but no declared count — add "
                     f"it to EXPECTED_MUTATIONS so its coverage cannot shrink unnoticed")
    if drift:
        return False, drift, ev
```

- [ ] **Step 4: Bump the count and verify both directions**

Line 8: `# 133 cases` → `# 136 cases`.

```bash
python3 scripts/check-plan-code.py --self-test | tail -1
python3 scripts/check-plan-code.py --mutate . | tail -1
```

Expected: `136/136 passed` and `OK — delivered scripts mutated: 2 file(s), 43 mutation(s), 0 survivor(s)`.

- [ ] **Step 5: Mutation-test the ratchet by hand — on a copy, never the repo**

```bash
S=$(mktemp -d); cp -R scripts "$S/scripts"; cp -R docs "$S/docs" 2>/dev/null || true
python3 - "$S" <<'PYEOF'
import json, pathlib, sys
p = pathlib.Path(sys.argv[1]) / "scripts/mutations/gen-dashboard.json"
e = json.loads(p.read_text())
assert len(e) == 32, f"expected 32, got {len(e)} — refusing"
p.write_text(json.dumps(e[:-1], indent=1, ensure_ascii=False) + "\n")
print("  [deleted one entry from the copy]")
PYEOF
python3 scripts/check-plan-code.py --mutate "$S"; echo "rc=$?  (expect rc=1 and 'expected 32')"
rm -rf "$S"
```

Expected: the run FAILS naming `scripts/gen-dashboard.py: manifest holds 31 mutation(s), expected 32`.
**A green result here means the ratchet does not work — stop.**

- [ ] **Step 6: Commit**

```bash
git add scripts/check-plan-code.py
git commit -m "feat(#70): coverage cannot shrink silently now that the manifest is data

Moving the manifest out of the plan opened a hole the plan had closed by accident:
delete an entry and CI stays green with less coverage. That is backlog #69's class,
and the same shape as CONTRAST_MIN the same day — one token, whole check off, 111/111.

EXPECTED_MUTATIONS is exact rather than a floor (adding should also be visible) and
lives in the RUNNER rather than beside the entries, because a count stored next to
what it counts gets edited in the same breath and guards nothing.

Mutation-tested by hand on a copy: deleting one entry fails naming the file and both
numbers. 133 -> 136 cases."
```

---

## Task 5: Demonstrate equivalence before removing anything

**No files change.** This task produces evidence, and it is the gate for Task 6.

- [ ] **Step 1: Run both paths at the same commit**

```bash
cd /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
git rev-parse --short HEAD
echo "--- OLD PATH: mutations against the plan's assembled copy ---"
python3 scripts/check-plan-code.py docs/superpowers/plans/2026-08-28-project-dashboard-plan.md \
        --compare . --verify-evidence | tail -1
echo "--- NEW PATH: mutations against the delivered scripts ---"
python3 scripts/check-plan-code.py --mutate . | tail -1
```

- [ ] **Step 2: Require the two to agree**

Both must report **43 mutation(s), 0 survivor(s)**. Record both lines verbatim in the Task 5 commit
message and in the PR body.

**If they disagree, the retarget did not preserve the guarantee.** Do not proceed to Task 6 — the
difference is the finding.

- [ ] **Step 3: Prove each path is individually falsifiable, not merely agreeing**

Two green runs could both be measuring nothing. Break one thing and confirm **both** notice:

```bash
S=$(mktemp -d); cp -R scripts "$S/scripts"
python3 - "$S" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1]) / "scripts/gen-dashboard.py"
s = p.read_text()
old = "a{{color:var(--link)}}"
assert s.count(old) == 1, f"anchor matched {s.count(old)}x, refusing"
p.write_text(s.replace(old, "a{{color:var(--nope)}}", 1))
print("  [broke the link rule in the copy]")
PYEOF
python3 scripts/check-plan-code.py --mutate "$S" | tail -2
echo "^ expect FAILED: the control is red, so the run refuses"
rm -rf "$S"
```

Expected: a `CANNOT RUN — control run of scripts/gen-dashboard.py exited 1` refusal. This proves the
new path is measuring the delivered file rather than reporting green regardless.

- [ ] **Step 4: Commit the evidence**

```bash
git commit --allow-empty -F - <<'MSG'
test(#70): both paths green at the same commit — equivalence demonstrated, not asserted

OLD  OK — compared + evidence-verified: 2 file(s), 43 mutation(s), 0 survivor(s)
NEW  OK — delivered scripts mutated:    2 file(s), 43 mutation(s), 0 survivor(s)

Agreement alone would be satisfied by two runs that both measure nothing, so the
new path was also shown to FAIL: breaking the link rule in a copied tree makes the
control red and the run refuses rather than reporting 43 catches over a broken suite.

The old step can now be removed against evidence rather than confidence.
MSG
```

---

## Task 6: Retire the step, delete the duplicated source, close the item

**Files:**
- Modify: `.github/workflows/ci.yml`, `docs/superpowers/plans/2026-08-28-project-dashboard-plan.md`,
  `docs/backlog.md`, `docs/roadmap-to-launch.md`, `docs/dashboard-entries.md`

- [ ] **Step 1: Swap the CI step**

In `.github/workflows/ci.yml`, delete **lines 182–223 inclusive** — the comment block *and* the step
it documents. Quoted rather than described, because the step's name is long and easy to get wrong:

```yaml
      - name: the plan's code and the DELIVERED scripts are the same, its mutations are caught, and its evidence is fresh
        run: |
          python3 scripts/check-plan-code.py \
            docs/superpowers/plans/2026-08-28-project-dashboard-plan.md \
            --compare . --verify-evidence
```

⚠ **The whole comment block goes with it**, including the ⛔ `RETIRES ONLY WHEN, AND NOT BEFORE`
section at `:205` and the `STATUS TODAY: NOT RETIRED, AND THE REPLACEMENT DOES NOT EXIST YET`
paragraph at `:199-203`. That text asserts a live tax and a non-existent replacement; leaving it
after this plan lands makes the file state something false in the most emphatic voice in the repo.

⚠ **Line numbers drift.** Before deleting, confirm the range still bounds exactly that step:

```bash
sed -n '182p;219p;223p' .github/workflows/ci.yml
```

Expected: line 182 begins `# --compare is what makes this step`, 219 is the `- name:` above, 223 is
`--compare . --verify-evidence`. **If they do not match, find the step by name and adjust** — do not
delete a range on faith.

Replace with:

```yaml
      # The mutation manifest runs against the DELIVERED scripts. It replaced a step that
      # required byte-identity between these files and a 3,170-line planning document —
      # backlog #70, retired 2026-08-29 once this existed and both paths were shown green
      # at 43 mutations / 0 survivors at the same commit.
      #
      # What this protects, unchanged from the step it replaces: the mutation evidence
      # describes the code that ships. It is now literally true rather than true-by-copy.
      #
      # FAILS IF: a mutation survives · an anchor is missing or ambiguous · a suite times
      # out (CANNOT RUN, never a catch) · the control is red before any mutation · a
      # manifest shrinks below its declared count in EXPECTED_MUTATIONS.
      - name: Mutation manifest against the delivered scripts
        run: python3 scripts/check-plan-code.py --mutate .
```

- [ ] **Step 2: Confirm the plan is no longer a CI dependency — by observation**

```bash
grep -c "2026-08-28-project-dashboard-plan" .github/workflows/ci.yml
```

Expected: `0`. This is the spec's last falsifier — *"`git rm` the plan and CI goes red"* — now
answered the other way: nothing in CI names it.

- [ ] **Step 3: Delete the duplicated source from the plan**

```bash
python3 - <<'PYEOF'
import pathlib, re
p = pathlib.Path("docs/superpowers/plans/2026-08-28-project-dashboard-plan.md")
s = p.read_text()
before = len(s.splitlines())
# Remove every `<!-- file: … -->` + fenced block pair, the mutations block, and the
# evidence block. Assert a plausible reduction rather than trusting the regex.
s = re.sub(r"<!-- file: [^>]+ -->\n```python\n.*?\n```\n", "", s, flags=re.S)
s = re.sub(r"<!-- mutations -->\n```json\n.*?\n```\n", "", s, flags=re.S)
s = re.sub(r"```\nGENERATED by scripts/check-plan-code\.py.*?\n```\n", "", s, flags=re.S)
after = len(s.splitlines())
assert before - after > 1300, f"only removed {before-after} lines — refusing, check the regex"
assert "<!-- file:" not in s and "<!-- mutations -->" not in s, "blocks remain — refusing"
p.write_text(s)
print(f"  removed {before-after} lines ({before} -> {after})")
PYEOF
```

- [ ] **Step 4: Add the pointer that replaces them**

Insert immediately after the plan's `**Status:**` line:

```markdown
> ⚠ **THE CODE BLOCKS THAT WERE HERE ARE GONE — read `scripts/` instead.**
> This document held byte-identical copies of `scripts/gen-dashboard.py` and
> `scripts/check-dashboard-entry.py`, kept in step by a CI check. That check was retired
> 2026-08-29 (backlog #70) and the copies were deleted rather than left to rot: code in a
> document that nothing validates stops being true quietly, and creates a belief that
> something is covered.
>
> **The delivered scripts are the only source:** [`scripts/gen-dashboard.py`](../../../scripts/gen-dashboard.py),
> [`scripts/check-dashboard-entry.py`](../../../scripts/check-dashboard-entry.py).
> Their 43 mutations now live in [`scripts/mutations/`](../../../scripts/mutations/) and run
> against the delivered files in CI.
>
> What remains below is the **reasoning and the task breakdown** — the part that was ever
> worth reading, and the part that is allowed to go stale.
```

- [ ] **Step 5: Close the backlog item and tick the roadmap**

In `docs/backlog.md`, change item #70's status cell from `**OPEN — filed 2026-08-29…**` to:

```
✅ **DONE 2026-08-29.** Manifest moved to `scripts/mutations/` (43 entries, verbatim);
`check-plan-code.py --mutate .` runs them against the delivered scripts; the plan step is
gone and its 1,401 duplicated lines with it. ⚠ Coupling REDUCED, not eliminated: 1,551
lines → 45 anchors (~3%), inherent to anchor-based mutation testing and left deliberately.
```

Add the matching roadmap tick in `docs/roadmap-to-launch.md` under the process-integrity section.

- [ ] **Step 6: Record a dashboard entry**

Append to `docs/dashboard-entries.md` a `## 2026-08-29` entry, plain language first, then a
`<!--tech-->` half. State the residual 3% coupling explicitly — an entry that claims the tax is gone
is the same overclaim this whole slice exists to remove.

- [ ] **Step 7: Run every gate**

```bash
for c in "scripts/check-plan-code.py --self-test" "scripts/gen-dashboard.py --self-test" \
         "scripts/check-dashboard-entry.py --self-test" "scripts/check-docs.py" \
         "scripts/check-anchors.py" "scripts/check-review-rounds.py" \
         "scripts/check-dashboard-entry.py"; do
  printf "%-44s %s\n" "$c" "$(python3 $c 2>&1 | tail -1)"
done
python3 scripts/check-plan-code.py --mutate . | tail -1
```

All must pass, and the last line must read
`OK — delivered scripts mutated: 2 file(s), 43 mutation(s), 0 survivor(s)`.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat(#70): retire the plan-as-CI-dependency and delete the code it duplicated

The CI step that required byte-identity between two production scripts and a
3,170-line planning document is gone, replaced by --mutate . against the delivered
files. Both paths were shown green at 43/0 at the same commit first (Task 5).

The plan's 1,401 lines of duplicated source are DELETED, not banner-warned. Once
nothing validates them they rot, and this project's own rule is that an unread rule
is worse than none because it creates a belief something is covered. The prose —
reasoning, tasks, review history — stays, and is now free to go stale honestly.

⚠ The tax is REDUCED, not removed: 1,551 coupled lines -> 45 anchors, ~3%, inherent
to anchor-based mutation testing. Recorded that way in the backlog and the dashboard
entry rather than claimed as a clean dissolve."
```

---

## Self-Review

**Spec coverage.** §3.1 manifests → T2. §3.2 runner + whole-tree copy + green control → T1, T3.
§3.3 evidence deleted → T6 Step 3 (removes the block) and T3 (the new mode stores none). §3.4 count
ratchet → T4. §3.5 plan blocks deleted → T6 Steps 3–4. §3.6 CI table → T6 Step 1. §4 equivalence →
T5. All seven falsifiers in §4 have a step that exercises them: mutates-shipped-code → T3 S6 + T5 S3;
anchor missing/ambiguous → T1 S2 (inherited, pinned); rc=2 → unchanged engine, pinned by the existing
121 cases; coverage-cannot-narrow → T4 S5; honest control → T3 S1 second case; equivalence → T5 S2;
plan has no mechanical role → T6 S2.

**Placeholders.** None. Every code step carries the code; every check step carries the command and
its expected output.

**Type consistency.** `run_mutations(d, muts, known) -> (ok, report, ev_muts, ev_survivors)` is
defined in T1 and called with that arity in T1 S5 and T3 S3. `load_manifests(root) -> (mutations,
problems)` defined T2 S5, called T3 S3 and T4 S3. `mutate_delivered(root) -> (ok, report, ev)`
defined T3 S3, called T3 S4 and T4 S1/S5. `EXPECTED_MUTATIONS` defined T4 S3, read T4 S1.
Case-count chain: **counted, not assumed** — T1 adds 4, T2 adds 5, T3 adds 3, T4 adds 3, giving
121 → 125 → 130 → 133 → 136, each bumped in the task that adds them. ⚠ The first draft of this plan
asserted 134 and 138 here without counting, which would have reddened every task from T3 onward on
the docstring drift check — for a reason unrelated to the task. Counted with
`grep -c '^\s*case('` per task before this line was rewritten.

**Known risk, stated not hidden.** Task 1 moves ~100 lines of six-rounds-hardened code. Its only
proof of innocence is that the 43/0 verdict is identical before and after, plus four new cases on the
extracted seam. If the extraction is wrong in a way both miss, the failure is silent. A reviewer
should diff the moved block against `git show HEAD~1` character by character rather than reading it.
