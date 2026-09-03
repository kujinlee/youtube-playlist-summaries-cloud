# Guard Inventory Population Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them — without reading the chat transcript.

**Goal:** Make `scripts/check-ratchet-contract.py` police every `scripts/*.py`, with a file leaving
the inventory only by a module-level `NOT_A_GUARD = "<reason>"` assignment — so a guard can no longer
escape by being named unconventionally.

**Architecture:** The population moves from `glob("check-*.py")` to `glob("*.py")`. Exclusion becomes
an **AST** fact, not a text match: two failed text grammars proved a declaration and a demonstration
of one can be byte-identical after `ast.get_docstring` cleaning. The glob is extracted out of `main()`
first, because a mutation cannot go red against a line no test case drives.

**Tech Stack:** Python 3.14, `ast`, the repo's own `--self-test` convention,
`scripts/check-plan-code.py --mutate .` for mutation coverage.

**Spec:** [`docs/superpowers/specs/2026-09-02-guard-inventory-population-design.md`](../specs/2026-09-02-guard-inventory-population-design.md) **v4**.
**Backlog:** closes #72 and #73.

**Status: v2 — Post-Plan Gate round 1 folded in, BOTH halves.** Codex 2 Blocking, 1 High, 1 Low;
Claude **4 Blocking**, 2 High, 4 Medium, 2 Low; overlapping on two. Reviews:
[`plan-guard-inventory-population-r1-{codex,claude}.md`](../../reviews/plan-guard-inventory-population-r1-codex.md).

> ⛔ **Every Blocking would have surfaced as a CI failure or a SILENT NO-OP, after an implementation
> subagent had already written code.** `case()` did not exist (a `NameError` on the first task);
> T7's first mutation survived because v1 mutated a call site inside undriven `main()`; an `expect`
> was short by the prefix its own loop prints, and the matcher is equality by design; and adding a
> manifest turned two hand-written oracles in `check-plan-code.py` red, so its control run refused
> and **zero mutations executed** while the process still looked like it ran.
>
> ⚠ **The surviving mutation was v1's own T1 fix failing one joint further along** — T1 made the
> *function* reachable and then mutated an *argument at a call site that still was not*. Fourth
> instance in this slice of "a fix is where the next defect lives"; it is why every round is scoped
> at the previous round's fixes.

## Global Constraints

- **The count after the change is exactly 28** — 26 `check-*.py` plus `gen-m4-manifest.py` and
  `verify-exclusion-reasons.py`. `build-m4-schema.py` is **OUT** (spec §4.1).
- **`BASELINE` stays `0`.** It is a hard floor. Raising it to absorb a failure is forbidden.
- **Zero code repairs are expected.** All 10 currently-failing non-`check-*` scripts are in the OUT
  set; each resolves to a declaration, not a fix. If any repair becomes necessary, STOP and report.
- **Every `NOT_A_GUARD` assignment goes AFTER the file's `from __future__ import` line.** Placed
  before it, the file parses but does not compile (spec §3.4a). All 17 target files have one.
- **The reason string must contain a non-whitespace character** (`\S`), matching `NO_CALLER_RE`.
- **Do not change `NO_CALLER_RE`.** Its text-matching weakness is recorded in spec §3.3 as a stated
  limit and belongs in the backlog, not this PR.
- **`--mutate .` needs a DIRECTORY**, and each `expect` entry must name **exactly one** red case.
- **Anything longer than a line goes in a file** — `git commit -F`, `gh pr --body-file`. A backtick
  inside a double-quoted bash string is command substitution.

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `scripts/check-ratchet-contract.py` | the guard inventory | the whole mechanism (T1–T4) |
| 17 × `scripts/<non-check>.py` | declare themselves out | one line each (T5) |
| `scripts/check-selftest-counts.py` | ratchets self-test counts | add the contract to `POPULATION` (T6) |
| `scripts/mutations/check-ratchet-contract.json` | mutation coverage | **new** (T7) |
| `scripts/check-plan-code.py` | `EXPECTED_MUTATIONS` | new key (T7) |
| 8 prose/config sites | stop asserting the old population | text (T8) |
| `docs/backlog.md`, `scripts/gen-backlog-page.py` | close #72/#73 | rows + `GROUPS` (T9) |

---

## Task 1: Extract the population glob so a mutation can reach it

**Why first:** spec §5 item 1. The glob is inline in `main()`; every self-test case drives
`discover_guards` / `check_contract` / `check_caller` directly, so **`main()` is driven by nothing**.
Narrowing the glob back would leave the suite green, `check-plan-code.py:747` would record
`caught = False`, and `--mutate .` would fail with *"mutation SURVIVED"*. This is verbatim the lesson
already at `check-ratchet-contract.py:163-171`.

**No behaviour change in this task** — the pattern stays `check-*.py`. That is deliberate: it gives
Task 3 a green control to mutate against.

**Files:**
- Modify: `scripts/check-ratchet-contract.py` (`main`, around `:395`)
- Test: `scripts/check-ratchet-contract.py` (its own `--self-test`)

**Interfaces:**
- Produces: `population_paths(scripts_dir: Path, pattern: str = "check-*.py") -> list[str]` —
  repo-relative POSIX paths, sorted. Task 3 changes the default pattern.

- [ ] **Step 1: Add the `case()` helper and the missing import — this is a PREREQUISITE**

⛔ **The Post-Plan Gate found there is no `case()` helper in this file.** `self_test()` (`:338`)
repeats the same four-line compare-and-print block five times. Every later step in this plan writes
cases as `case(...)`, so the helper is built first — and because it owns the failure format in ONE
place, it also delivers what the mutation harness needs (see T4). Two findings, one fix.

Add `import tempfile` to the imports, then above `self_test()`:

```python
def _make_case(state: dict[str, int]):
    """One comparison, one place that decides how a failure PRINTS.

    ⚠ The `[FAIL] ` prefix and the `: got ` separator are a CONTRACT with
    `scripts/check-plan-code.py:723`, which recovers red case names with
    `l.strip()[7:].rsplit(": got ", 1)[0]` and reads NOTHING else. While this
    file printed `  FAIL {name}`, every mutation `expect` resolved to zero red
    cases and was rejected as "caught by something else" — a mutation harness
    reporting nothing, indistinguishable from a guard that holds.
    """
    def case(name: str, got, expected) -> None:
        state["total"] += 1
        if got != expected:
            state["failures"] += 1
            print(f"[FAIL] {name}: got {got}\n       expected {expected}")
    return case
```

and at the top of `self_test()`:

```python
    state = {"total": 0, "failures": 0}
    case = _make_case(state)
```

- [ ] **Step 2: Write the failing case — the DEFAULT pattern is what the case exercises**

⛔ **Call `population_paths(scripts)` with no pattern argument.** The gate showed that mutating the
*call-site argument* in `main()` survives, because no case drives `main()`. The mutation in T7
therefore targets the **signature default**, and only a case that relies on the default can catch it.

```python
    # ── population_paths: the glob is a FUNCTION, and its DEFAULT is load-bearing ──
    with tempfile.TemporaryDirectory() as d:
        scripts = Path(d) / "scripts"
        scripts.mkdir()
        for name in ("check-a.py", "gen-b.py", "notes.txt"):
            (scripts / name).write_text('"""x."""\n')
        got = population_paths(scripts)          # NO pattern argument — the default decides
        case("population_paths uses its default pattern",
             got, ["scripts/check-a.py"])
        case("population_paths excludes a non-.py file",
             any("notes.txt" in p for p in got), False)
```

⚠ At this point the default is still `check-*.py`, so `gen-b.py` is correctly absent. **T3 changes
the default to `*.py` and updates the first expectation to include `scripts/gen-b.py`** — that is the
case T7's first mutation drives red.

- [ ] **Step 3: Run it to make sure it fails**

Run: `python3 scripts/check-ratchet-contract.py --self-test`
Expected: FAIL — `NameError: name 'population_paths' is not defined`
⚠ Not a `case` NameError: Step 1 defined it.

- [ ] **Step 3: Write the minimal implementation**

Add above `discover_guards`:

```python
def population_paths(scripts_dir: Path, pattern: str = "check-*.py") -> list[str]:
    """The FILES offered to the inventory, as repo-relative POSIX paths.

    ⚠ EXTRACTED FOR THE WIRING, not for tidiness — the same reason `evaluate`
    was extracted (see below). While this glob lived inline in `main()`, no
    self-test case drove it, so narrowing it back to `check-*.py` left the whole
    suite green and `--mutate .` reported the mutation as SURVIVED. A line the
    suite cannot reach cannot be guarded.
    """
    return sorted(f"scripts/{p.name}" for p in scripts_dir.glob(pattern))
```

- [ ] **Step 4: Run the tests and make sure they pass**

Run: `python3 scripts/check-ratchet-contract.py --self-test`
Expected: PASS, count rises by 3.

- [ ] **Step 5: Rewire `main()` to use it, with the pattern unchanged**

Replace the loop at `:394-401`:

```python
    texts = {}
    for rel in population_paths(ROOT / "scripts"):
        try:
            texts[rel] = (ROOT / rel).read_text(errors="ignore")
        except OSError:
            print(f"FAILED: could not read {rel} — treat this as NOT RUN.")
            return 1
```

- [ ] **Step 6: Prove behaviour is unchanged**

Run: `python3 scripts/check-ratchet-contract.py`
Expected: `guards discovered (26)` … `ratchet contract OK`, exit 0. **Still 26.**

- [ ] **Step 7: Commit**

```bash
git add scripts/check-ratchet-contract.py
git commit -F .git/COMMIT_MSG_T1
```
(Write the message to that file first: `refactor: extract population_paths so its glob is reachable by a test`.)

---

## Task 2: The `NOT_A_GUARD` detector

**Files:**
- Modify: `scripts/check-ratchet-contract.py`
- Test: its own `--self-test`

**Interfaces:**
- Produces: `not_a_guard_reason(src: str) -> str | None` — the declared reason, or `None` when the
  file stays IN. Task 3 consumes it.

- [ ] **Step 1: Write the failing cases**

```python
NOT_A_GUARD_CASES: list[tuple[str, str, bool]] = [
    # (label, source, expected-EXCLUDED)
    ("plain assignment",        'NOT_A_GUARD = "a generator"', True),
    ("annotated assignment",    'NOT_A_GUARD: str = "a generator"', True),
    ("Final annotation",        'from typing import Final\nNOT_A_GUARD: Final[str] = "a gen"', True),
    ("implicit concatenation",  'NOT_A_GUARD = ("a gen" "erator")', True),
    ("docstring DOCUMENTS it",  '"""Leave by setting NOT_A_GUARD = \\"why\\" at module level."""', False),
    ("docstring DEMONSTRATES",  '"""Doc.\n    Example::\n    NOT_A_GUARD = "sample"\n    """', False),
    ("a comment",               '# NOT_A_GUARD = "sneaky"\nx = 1', False),
    ("nested in a function",    'def f():\n    NOT_A_GUARD = "nested"', False),
    ("empty reason",            'NOT_A_GUARD = ""', False),
    ("whitespace-only reason",  'NOT_A_GUARD = "   "', False),
    ("non-string value",        'NOT_A_GUARD = True', False),
    ("unparseable file",        'def main(:', False),
    ("before __future__",       '"""D."""\nNOT_A_GUARD = "x"\nfrom __future__ import annotations', False),
]
```

```python
    for label, src, expected in NOT_A_GUARD_CASES:
        case(f"NOT_A_GUARD: {label}", not_a_guard_reason(src) is not None, expected)
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `python3 scripts/check-ratchet-contract.py --self-test`
Expected: FAIL — `NameError: name 'not_a_guard_reason' is not defined`

- [ ] **Step 3: Write the minimal implementation**

```python
def not_a_guard_reason(src: str) -> str | None:
    """The written reason a file gives for leaving the inventory, or None.

    ⚠ AN AST FACT, NEVER A TEXT MATCH. Two text grammars were tried and both
    failed: `ast.get_docstring(clean=True)` dedents by the MINIMUM body indent,
    so after cleaning a declaration and a DEMONSTRATION of a declaration can be
    byte-identical. Prose cannot forge an assignment node.

    ⚠ COMPILES AS WELL AS PARSES. `NOT_A_GUARD` written before a `__future__`
    import parses fine and does not compile, so reading it with `ast.parse`
    alone would drop a file that Python cannot even import — excluded from
    policing AND broken. A module that parses but will not compile stays IN.
    """
    try:
        tree = ast.parse(src)
        compile(src, "<inventory>", "exec")
    except (SyntaxError, ValueError):
        return None
    for node in tree.body:                      # MODULE level only
        target = None
        if isinstance(node, ast.AnnAssign):     # NOT_A_GUARD: Final[str] = "..."
            target = node.target
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
        if not (isinstance(target, ast.Name) and target.id == "NOT_A_GUARD"):
            continue
        value = node.value
        if isinstance(value, ast.Constant) and isinstance(value.value, str) \
                and value.value.strip():
            return value.value
    return None
```

- [ ] **Step 4: Run the tests and make sure they pass**

Run: `python3 scripts/check-ratchet-contract.py --self-test`
Expected: PASS — all 13 `NOT_A_GUARD` cases green.

- [ ] **Step 5: Commit**

```bash
git add scripts/check-ratchet-contract.py
git commit -F .git/COMMIT_MSG_T2
```

---

## Task 3: Widen the population and delete the dead discovery

**Files:**
- Modify: `scripts/check-ratchet-contract.py`

**Interfaces:**
- Consumes: `population_paths` (T1), `not_a_guard_reason` (T2)
- Produces: `discover_guards(texts: dict[str, str]) -> list[str]`

- [ ] **Step 1: Write the failing cases — replace `POPULATION_CASES` entirely**

⚠ The existing third case asserts the **opposite** of the payload case and must go:

```python
POPULATION_CASES: list[tuple[str, dict[str, str], list[str]]] = [
    ("a check-* script is in the population",
     {"scripts/check-a.py": '"""x."""'}, ["scripts/check-a.py"]),
    ("a NON-check script with no declaration is IN — the payload case",
     {"scripts/gen-b.py": '"""x."""'}, ["scripts/gen-b.py"]),
    ("a declared non-guard is OUT",
     {"scripts/gen-b.py": '"""x."""\nNOT_A_GUARD = "a generator"'}, []),
    ("a non-.py path is never offered",
     {"scripts/notes.md": "x"}, []),
]
```

```python
    for label, texts, expected in POPULATION_CASES:
        case(f"discover_guards: {label}", discover_guards(texts), expected)
    case("the contract is in its OWN population",
         "scripts/check-ratchet-contract.py" in
         discover_guards({p: (ROOT / p).read_text() for p in population_paths(ROOT / "scripts")}),
         True)
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `python3 scripts/check-ratchet-contract.py --self-test`
Expected: FAIL — `discover_guards` still takes a path list, and the payload case returns `[]`.

- [ ] **Step 3: Rewrite `discover_guards`**

```python
GUARD_PATH_RE = re.compile(r"scripts/[\w.-]+\.py")


def discover_guards(texts: dict[str, str]) -> list[str]:
    """EVERY guard on disk. The population IS the filesystem.

    ⚠ This finally matches what this docstring has claimed since 2026-08-30.
    Until then both callers narrowed the list to `glob("check-*.py")` before
    handing it over, so the sentence was true of the filter and false of the
    population — the exact shape of defect this inventory exists to catch,
    inside the inventory. Backlog #72.

    A file leaves by declaring `NOT_A_GUARD = "<reason>"` at module level. There
    is no way to leave by silence: an undeclared script is IN.
    """
    return sorted(p for p, src in texts.items()
                  if GUARD_PATH_RE.fullmatch(p) and not_a_guard_reason(src) is None)
```

- [ ] **Step 4: Update both callers**

`evaluate` (`:174`) and `main` (`:403`) both pass the mapping, not its keys:

```python
    for rel in discover_guards(texts):
```
```python
    ratchets = discover_guards(texts)
```

- [ ] **Step 5: Widen the DEFAULT (not the call site) and delete the dead discovery**

⛔ **Change the signature default, and leave `main`'s call bare.**

```python
def population_paths(scripts_dir: Path, pattern: str = "*.py") -> list[str]:
```

`main` keeps calling `population_paths(ROOT / "scripts")`. A pattern passed at the call site would
put the live behaviour back inside `main()`, where no case can reach it — the exact defect the gate
found. Update T1's first case to expect the widened result:

```python
        case("population_paths uses its default pattern",
             got, ["scripts/check-a.py", "scripts/gen-b.py"])
```

Delete `discover_ratchets` (`:67`), `RATCHET_DOCSTRING_RE` (`:55`), `CI_RATCHET_STEP_RE`, and
`DISCOVERY_CASES` — **including the `for name, ci, scripts, expected in DISCOVERY_CASES:` loop inside
`self_test()`**, not just the constant. Update the sanity comment at `:404` to a magnitude, not a
count:

```python
    if not ratchets:
        # Dozens are expected. Zero means discovery broke, not that all is well.
        print("FAILED: discovered ZERO guards, which cannot be right. Treat this as NOT RUN.")
        return 1
```

- [ ] **Step 6: Run both, and check the count**

Run: `python3 scripts/check-ratchet-contract.py --self-test` → PASS
Run: `python3 scripts/check-ratchet-contract.py`
Expected: **`guards discovered (45)`** and a wall of violations — the 17 declarations do not exist
yet. **This is correct at this point.** Task 5 brings it to 28.

- [ ] **Step 7: Commit**

```bash
git add scripts/check-ratchet-contract.py
git commit -F .git/COMMIT_MSG_T3
```

---

## Task 4: Route every comparison through `case()`, and add the CANNOT-RUN exit

**Why:** T1 Step 1 put the `[FAIL] ` contract in one function. This task retires the remaining
hand-rolled compare-and-print blocks so no second format can drift back in.

⚠ **The plan previously said "five failure prints". By the time this task runs it is THREE** — T3
deleted the `DISCOVERY_CASES` loop and its print, and T3 rewrote the `POPULATION_CASES` loop to use
`case()`. Count them in the file rather than trusting this sentence.

**Files:**
- Modify: `scripts/check-ratchet-contract.py` (the remaining `print(f"  FAIL …")` sites, and `main`)

- [ ] **Step 1: Convert each remaining block**

```python
    for name, text, expected in CASES:
        got = sorted({v.rule for v in check_contract("t.py", text)})
        case(name, got, sorted(expected))
```

Then replace the trailing tally with the helper's state:

```python
    print(f"self-test: {state['total'] - state['failures']}/{state['total']} passed")
    return 1 if state["failures"] else 0
```

- [ ] **Step 1b: Prove no `  FAIL` print survives**

```bash
grep -n 'print(f"  FAIL' scripts/check-ratchet-contract.py; echo "exit=$?"
```
Expected: no matches (`exit=1`). A survivor is a second format that `check-plan-code.py` cannot read.

- [ ] **Step 2: Replace the unparseable-file traceback with a CANNOT-RUN exit**

`fail_open_handlers` currently raises `SyntaxError` out of `main`. Wrap it:

```python
    try:
        violations = evaluate(texts, blob_for)
    except SyntaxError as e:
        print(f"CANNOT RUN — a script under scripts/ does not parse: {e}")
        print("Treat this as NOT RUN.")
        return 2
```

- [ ] **Step 3: Prove the parser can now read a red run**

```bash
python3 - <<'PY'
import subprocess, sys
out = subprocess.run([sys.executable, "scripts/check-ratchet-contract.py", "--self-test"],
                     capture_output=True, text=True).stdout
fails = [l.strip()[7:].rsplit(": got ", 1)[0].strip()
         for l in out.split("\n") if l.strip().startswith("[FAIL] ")]
print("parsed red cases:", fails)
PY
```
Expected: `[]` on a green suite. Temporarily break one case and re-run; expected: exactly that case's
name. **Restore the case before continuing.**

- [ ] **Step 4: Commit**

```bash
git add scripts/check-ratchet-contract.py
git commit -F .git/COMMIT_MSG_T4
```

---

## Task 5: The 17 declarations

**Files (Modify, one line each):** `gen-backlog-page.py`, `gen-dashboard.py`, `gen-goals-page.py`,
`brief-compose.py`, `regen-skills-doc.py`, `page_markup.py`, `page_chrome.py`, `subject_status.py`,
`m4_catalog.py`, `m4_base_db.py`, `explainer-serve.py`, `prior-art.py`, `codex-review.py`,
`codex-frontier-model.py`, `session-skill-report.py`, `skill-usage-audit.py`, `build-m4-schema.py` —
all under `scripts/`.

⚠ **Placement: immediately AFTER the `from __future__ import` line.** All 17 have one. Before it, the
file parses but does not compile.

- [ ] **Step 1: Add each declaration, with a reason derived from the criterion**

The reason states the file's **product**, because that is what the criterion turns on:

```python
from __future__ import annotations

NOT_A_GUARD = "renders a page; its product is an artefact, not a verdict"
```

| File | Reason |
|---|---|
| `gen-backlog-page.py`, `gen-dashboard.py`, `gen-goals-page.py`, `brief-compose.py`, `regen-skills-doc.py` | `"renders a page; its product is an artefact, not a verdict"` |
| `page_markup.py`, `page_chrome.py`, `subject_status.py`, `m4_catalog.py`, `m4_base_db.py` | `"a library; its product is functions for other code, not a verdict"` |
| `explainer-serve.py`, `prior-art.py` | `"a tool; its product is information for a human, not a verdict"` |
| `codex-review.py` | `"runs a gate rather than being one; its product is a review file"` |
| `codex-frontier-model.py` | `"a tool; resolves a model name for a human or a caller"` |
| `session-skill-report.py`, `skill-usage-audit.py` | `"a reporter; its product is information for a human"` |
| `build-m4-schema.py` | `"builds SQL; its assertions protect its own output, which is self-protection, not policing"` |

- [ ] **Step 2: Run the inventory and check the count**

Run: `python3 scripts/check-ratchet-contract.py`
Expected: **`guards discovered (28)`**, `ratchet contract OK`, exit 0.

⚠ If the number is not 28, STOP. 29 means `build-m4-schema.py` was left IN (spec §4.1 puts it OUT).
27 means a declaration landed on an IN file.

- [ ] **Step 3: Prove no file was broken by its declaration**

```bash
for f in scripts/*.py; do python3 -c "import sys,py_compile; py_compile.compile('$f', doraise=True)" \
  || echo "BROKEN: $f"; done
```
Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add scripts/
git commit -F .git/COMMIT_MSG_T5
```

---

## Task 6: Make the self-inclusion case actually run

**Why:** nothing executes this script's `--self-test` — `.github/workflows/ci.yml:144` runs the bare
script. `check-selftest-counts.run_self_test` (`:183-186`) spawns every `POPULATION` member with
`--self-test`, wired at `ci.yml:178`. Without this task, Task 3's self-inclusion case runs nowhere.

**Files:**
- Modify: `scripts/check-selftest-counts.py` (`POPULATION`, `:83-93`)
- Modify: `scripts/check-ratchet-contract.py` (usage block, `:23-26`)

- [ ] **Step 1: Add the case-count declaration — MODIFY the existing usage line, do not add a second**

`scripts/check-ratchet-contract.py:25` already reads
`    python3 scripts/check-ratchet-contract.py --self-test`. Append the count to **that** line:

```
    python3 scripts/check-ratchet-contract.py --self-test   # N cases
```
where `N` is the number the suite actually prints. **Read it from a run; do not recall it** — it
moves as T1–T4 add and delete cases. A second usage line would leave two candidates for the parser.

- [ ] **Step 2: Add the file to `POPULATION`**

```python
    "check-ratchet-contract.py",
```

⚠ Both steps in the same commit. One without the other trips
`check-selftest-counts.py:176-179` (*"declares a case count but is not in POPULATION"*).

- [ ] **Step 3: Run the observer**

Run: `python3 scripts/check-selftest-counts.py`
Expected: exit 0, the contract listed among the declaring scripts.

- [ ] **Step 4: Commit**

```bash
git add scripts/check-selftest-counts.py scripts/check-ratchet-contract.py
git commit -F .git/COMMIT_MSG_T6
```

---

## Task 7: Mutation coverage — the file's first ever

**Files:**
- Create: `scripts/mutations/check-ratchet-contract.json`
- Modify: `scripts/check-plan-code.py` (`EXPECTED_MUTATIONS`, `:432-497`)

- [ ] **Step 1: Write the manifest**

⛔ **Two Blockings from the gate live in this block. Read both before writing it.**
① The mutation must target the **signature default**, not `main`'s call site — a call-site mutation
survives because no case drives `main()`. ② An `expect` is matched by **equality**
(`check-plan-code.py:757`), and T3's loop prints `f"discover_guards: {label}"`, so an expect naming a
case from that loop **must carry the prefix**. Round 6 replaced substring matching on purpose.

```json
[
  {
    "name": "the population default narrows back to check-*.py",
    "file": "scripts/check-ratchet-contract.py",
    "edits": [["def population_paths(scripts_dir: Path, pattern: str = \"*.py\")",
               "def population_paths(scripts_dir: Path, pattern: str = \"check-*.py\")"]],
    "expect": ["population_paths uses its default pattern"]
  },
  {
    "name": "an assignment nested in a function counts as a declaration",
    "file": "scripts/check-ratchet-contract.py",
    "edits": [["    for node in tree.body:", "    for node in ast.walk(tree):"]],
    "expect": ["NOT_A_GUARD: nested in a function"]
  },
  {
    "name": "a whitespace-only reason counts as a declaration",
    "file": "scripts/check-ratchet-contract.py",
    "edits": [["and value.value.strip()", "and value.value != \"\""]],
    "expect": ["NOT_A_GUARD: whitespace-only reason"]
  },
  {
    "name": "the detector stops compiling and only parses",
    "file": "scripts/check-ratchet-contract.py",
    "edits": [["        compile(src, \"<inventory>\", \"exec\")\n", ""]],
    "expect": ["NOT_A_GUARD: before __future__"]
  }
]
```

- [ ] **Step 2: Add the key AND update BOTH hardcoded oracles — three edits, one commit**

⛔ **`check-plan-code.py` asserts its own manifest inventory TWICE, by hand.** Adding a manifest
without updating both turns them red; its `--mutate .` **control** run then refuses, and **zero
mutations execute** — so Step 3's expectation never happens and its two ⚠ notes never fire. A
mutation harness that runs nothing looks exactly like one where everything passed.

**(a)** the key, in `EXPECTED_MUTATIONS`:
```python
    "scripts/check-ratchet-contract.py": 4,
```

**(b)** the inventory oracle at `:1948-1956` — insert in **sorted** position, between
`scripts/check-plan-code.py` and `scripts/check-selftest-counts.py`:
```python
                                      "scripts/check-plan-code.py",
                                      "scripts/check-ratchet-contract.py",
                                      "scripts/check-selftest-counts.py",
```

**(c)** the sum oracle at `:2021` — **`162` becomes `166`.** A literal on purpose; the comment above
it says its whole job is that the total cannot move without someone deciding it should. Write the
number, not "rise by 4".

- [ ] **Step 2b: Prove the harness's own suite is green BEFORE mutating**

Run: `python3 scripts/check-plan-code.py --self-test`
Expected: all pass. ⚠ A red here means the control run will refuse and every verdict in Step 3 would
be an artefact — `mutate_delivered:643-648` says so in as many words.

- [ ] **Step 3: Run the mutation suite**

Run: `python3 scripts/check-plan-code.py --mutate .`
Expected: control green first, then **4 mutations, 0 survivors**, each red via the case it names.

⚠ If any reports *"matched 0 red case(s)"*, the `[FAIL] ` format from Task 4 did not land.
⚠ If any reports *"mutation SURVIVED"*, the extraction from Task 1 did not land.

- [ ] **Step 4: Commit**

```bash
git add scripts/mutations/check-ratchet-contract.json scripts/check-plan-code.py
git commit -F .git/COMMIT_MSG_T7
```

---

## Task 8: Correct every site that states the old population as fact

**Why:** spec §7 and §1.2 — a true statement in a neighbour's comment did not correct the false one at
the source. Leaving these reproduces the defect the change fixes.

**Files (Modify):** `docs/process-checklists.md` (3 spots), `docs/dev-process.md:145`,
`docs/roadmap-to-launch.md` (3 spots), `scripts/check-test-counts.py:31-33`,
`scripts/check-review-rounds.py:46-48`, `scripts/page_markup.py:42-45`,
`scripts/explainer-serve.py:68-73`, `.github/workflows/ci.yml:212-215` and `:220-223`,
`docs/superpowers/specs/2026-08-30-inline-renderer-seam-design.md:176,183`.

- [ ] **Step 1: Rewrite each claim to describe the new mechanism**

Two shapes recur. Where a file says *"the population is `glob("check-*.py")`, so this file is not
seen"* → *"the population is every `scripts/*.py`; this file declares `NOT_A_GUARD` and is therefore
out."* Where a doc says *"two independent sources"* → *"one source: the filesystem. A file leaves only
by declaring `NOT_A_GUARD`."*

⚠ `scripts/check-review-rounds.py:46-48` currently ends *"Both are now true."* — that sentence
becomes false and must go.
⚠ `docs/dev-process.md:145` also quotes a self-test case count that moves.

- [ ] **Step 2: Run F8 — the grep, EXECUTED not authored**

```bash
grep -rn --binary-files=without-match --exclude-dir=__pycache__ discover_ratchets \
  scripts/ .github/ .claude/ docs/process-checklists.md docs/dev-process.md docs/roadmap-to-launch.md
```
Expected: **no output.** (`--binary-files` and `--exclude-dir` are load-bearing: `.pyc` files match
the old symbol, and that made this falsifier wrong in three consecutive spec versions.)

- [ ] **Step 3: Run the doc gates**

Run: `python3 scripts/check-docs.py && python3 scripts/check-anchors.py`
Expected: both exit 0. ⚠ `docs/plugins.md` sits at its line budget; do not add lines there.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -F .git/COMMIT_MSG_T8
```

---

## Task 9: Close both backlog rows, and record the entry

**Files:**
- Modify: `docs/backlog.md` (rows #72, #73)
- Modify: `scripts/gen-backlog-page.py` (`GROUPS`)
- Modify: `docs/dashboard-entries.md`

- [ ] **Step 1: Close the rows**

Each closed row's status cell must **lead** `✅ (was 🟠)` / `✅ (was 🟢)` — a severity scan counts a
trailing marker as open, and `check-docs.py` refuses it by name.

- [ ] **Step 2: Delete both `GROUPS` tuples**

`GROUPS` coverage is **bidirectional**: it refuses an open item with no prose *and* prose describing a
now-closed item. Closing a row means deleting its tuple.

- [ ] **Step 3: File the `NO-CALLER:` row the spec twice promises**

Spec §3.3 and §6 both say `NO_CALLER_RE`'s text weakness *"belongs in the backlog, not this PR"* — a
docstring example showing `NO-CALLER: <reason>` would opt a guard out of R3. **Measured: zero of the
26 guards carry such a declaration and none has such an example, so nothing is broken today.**
Add the row 🟢, with that measurement, and note it is the same class the AST declaration solved one
level up.

⚠ **Filing to `docs/backlog.md` is normally the user's step.** This one is different: the spec
promises it twice, so shipping without it makes the spec's own limits section false.

- [ ] **Step 4: Write the dashboard entry**

The branch changes tracked files, so an entry is required or the gate refuses it.

- [ ] **Step 5: Verify the counts through the owning parser**

```bash
python3 - <<'PY'
import importlib.util, pathlib
spec = importlib.util.spec_from_file_location("gb", pathlib.Path("scripts/gen-backlog-page.py"))
gb = importlib.util.module_from_spec(spec); spec.loader.exec_module(gb)
rows = gb.parse(open("docs/backlog.md").read().splitlines())
opens = [r for r in rows if not r["closed"]]
assert rows and opens, "empty — refuse to report it"
print(f"TOTAL {len(rows)}  OPEN {len(opens)}  CLOSED {len(rows)-len(opens)}")
PY
```
Expected: 87 total, **57 open**, 30 closed (was 59/28). ⚠ Never hand-roll this count.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -F .git/COMMIT_MSG_T9
```

---

## Task 10: Run every falsifier

**Files:** none modified. This task produces evidence.

- [ ] **Step 1: F1, F2, F9 — against the live tree**

Run: `python3 scripts/check-ratchet-contract.py`
Expected: `guards discovered (28)`, includes `gen-m4-manifest.py` and `verify-exclusion-reasons.py`,
excludes `build-m4-schema.py`; `ratchet contract OK`; `BASELINE` still `0`.

- [ ] **Step 2: F3–F7 — against a TEMP COPY, never the live tree**

⚠ The copy must include `.github/workflows/ci.yml` and the full caller sources, or F3 passes for the
wrong reason (`main` returns 1 on a missing `ci.yml`, which looks identical to the intended failure).

⚠ **The copy must not swallow its own failure.** `2>/dev/null` on the `cp` would hide a missing
source and leave F3 passing because `main` returned 1 for the wrong reason.

```bash
T=$(mktemp -d); cp -R scripts .github .claude "$T"/ || { echo "CANNOT RUN — copy failed"; exit 2; }
test -f "$T/.github/workflows/ci.yml" || { echo "CANNOT RUN — no ci.yml in the copy"; exit 2; }
printf '"""A probe."""\nfrom __future__ import annotations\n' > "$T/scripts/zz-probe.py"
( cd "$T" && python3 scripts/check-ratchet-contract.py | tee /dev/stderr | grep -q "zz-probe" ) \
  && echo "F3 present-in-list ✓"
( cd "$T" && python3 scripts/check-ratchet-contract.py >/dev/null; [ $? -eq 1 ] ) && echo "F3 exit-1 ✓"
```

Then append `NOT_A_GUARD = "a probe"` **after** the `__future__` line → expect exit 0 and
`zz-probe` absent (**F4**). Then the whitespace/nested/non-string variants → expect the file stays IN
(**F5**). Then a docstring that documents and one that demonstrates the rule → both stay IN (**F6**).
Then a docstring carrying the **old** `NOT-A-GUARD:` text marker → stays IN (**F6b**). Then confirm
`check-ratchet-contract.py` is in its own discovered list (**F7**).

- [ ] **Step 3: F8**

The Task 8 grep. Expected: no output.

- [ ] **Step 4: The full local gate sweep**

```bash
python3 scripts/check-ratchet-contract.py --self-test
python3 scripts/check-selftest-counts.py
python3 scripts/check-docs.py
python3 scripts/check-anchors.py
python3 scripts/check-review-rounds.py
python3 scripts/check-dashboard-entry.py
python3 scripts/check-plan-code.py --mutate .
```
Expected: all exit 0. ⚠ A "cannot run" is a FAILURE, not a pass — say *treat this as NOT RUN*.

- [ ] **Step 5: Record the evidence and commit**

```bash
git add -A
git commit -F .git/COMMIT_MSG_T10
```

---

## Self-Review

**Spec coverage.** §3.2 → T2. §3.4/§3.4a → T2 (compile + placement). §3.5 → T3 case + T6 wiring.
§4 (28, the 17 declarations) → T5. §5 items 1–4 → T1, T3. Item 5 → T3. Items 6, 10 → T3, T8. Item 7 →
T3. Item 8 → T4. Item 9 → T4. §7 → T8. §8 → T3 (delete) + T9 (rows). §9 → T10. §10 → T4, T6, T7.
§11 → T9. **No spec section is without a task.**

**Placeholder scan.** No TBD/TODO. Every code step carries the actual code. Reasons for all 17
declarations are written out rather than described.

**Type consistency.** `population_paths(scripts_dir, pattern="check-*.py") -> list[str]` (T1) is
called with `"*.py"` in T3. `not_a_guard_reason(src) -> str | None` (T2) is consumed by
`discover_guards(texts) -> list[str]` (T3), whose callers in T3 pass the mapping. The mutation
`expect` strings in T7 are copied verbatim from the case labels in T1/T2/T3.

**Known ordering constraints — all five, after the Post-Plan Gate.**

| Constraint | Why, in one line |
|---|---|
| **T1 → T7** | a mutation on a line no case drives SURVIVES. T1 makes the *default* load-bearing |
| **T1 Step 1 → everything** | `case()` does not exist in the file; every later snippet calls it |
| **T2, T3 → T7** | T7's anchors (`tree.body`, `value.value.strip()`, `compile(…)`, the signature default) and its `expect` names do not exist until T2 and T3 land |
| **T4 → T7** | without the `[FAIL] ` format every `expect` resolves to 0 red cases and is rejected |
| **T3 → T5** | the count is 45 until the declarations land |

**Same-commit couplings.** T6's two edits (`# N cases` + `POPULATION`) — one without the other trips
`check-selftest-counts.py:176-179`. T7 Step 2's three edits (key + both oracles) — one without the
others makes the control run refuse and **zero** mutations execute.

**`expect` strings are matched by EQUALITY** (`check-plan-code.py:757`, deliberately, since round 6).
An expect naming a case from T3's loop must carry the `discover_guards: ` prefix that loop prints;
one naming a T2 case must carry `NOT_A_GUARD: `. A prefix-short string matches nothing.
