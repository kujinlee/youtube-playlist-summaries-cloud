# Round 3 — `derived-mutation-total` (PR #455, backlog #359) — coordinator — NOT CONVERGED (Claude); the r2 REDESIGN's witness moves to where the pins are used; ladder: SPLIT

REVIEW GAP: codex — round 3 alternates to the Claude half alone (rounds 2+ alternate, `review-method.md` → *Round topology*; backlog #339).

Claude half: `docs/reviews/claude/derived-mutation-total-r3-claude.md`, which reviewed `e777d546`.

```yaml
round: 3
fixes_nontrivial: true
subject: derived-mutation-total
halves:
  codex: gap
  claude: ran
findings:
  - {id: F1, severity: High, aim: instrument, fix_induced: true, component: pin-witness, disposition: fixed}
  - {id: F2, severity: Low, aim: instrument, fix_induced: true, component: pin-witness, disposition: fixed}
```

**What Claude found.**
- **F1 (High):** a write conditioned on how the process was started lowers the pins the harness uses while
  `--print-pins` reports the old ones. Examples: `if "--print-pins" not in sys.argv: ...-= 5`, and the same gated on
  `CI=true`. Measured: `--print-pins` printed 87, the harness held 82, `hold_reasons` returned `[]`, and both the head's
  self-test and CI's `pin_drift` stayed green. Master went red on the same input. r2 split the two witnesses across
  two invocations, and nothing checked that the module evaluates to the same dict in both.
- **F2 (Low):** `effective_pins`' docstring said a tree with no `PINS_SCRIPT` pins `{}`, but a tree with no
  `scripts/` was CANNOT RUN.

**Route taken: the reviewer's structural fix.** The display is the source of truth, and the harness proves in its
OWN process that the display is what it uses.
- `check-plan-code.pin_display(src)` reads the ONE module-level `EXPECTED_MUTATIONS = {...}` display as data. It
  raises `PinDisplayError` unless there is exactly one module-level assignment to the name, every key is a string
  literal, every value is an int literal, and no key is repeated. Python keeps the last duplicate, so a display
  carrying one is refused explicitly.
- `pin_display_problems(src, effective)` names every key whose display value differs from the held value.
- `--mutate` asserts it first, before any mutation runs. `--self-test` asserts it at the top of its body, as a named
  case, and then returns rc 2. Either refusal prints `PINS_REFUSAL` and the differing keys.
- The suite's own synthetic `--mutate` runs rewrite the pins on purpose. They stand the assertion down through
  `_suite_owns_the_pins()`. The assertion itself is proved on a real copy of the file.
- `check-merge-ready.pins_at(run, rev)` runs `git ls-tree --name-only` and then `git show rev:scripts/check-plan-code.py`
  at the merge base and at HEAD. It applies `pin_display`, imported from check-plan-code (one owner), and executes
  nothing. An absent file pins `{}`; this covers a base with no `scripts/` at all, which closes F2. A failing `git`
  call or a refused display is CANNOT RUN.

**Deleted:**
- In `check-merge-ready`: the `git archive` + `tarfile` materialisation, the subprocess, `PINS_TIMEOUT`, the
  base-only import fallback (`PINS_PROBE`), `PINS_FLAG` and `parse_pins`. The `io` and `tarfile` imports went with
  them, and `_run`'s `cwd` change was reverted to master's form.
- In `check-plan-code`: the `--print-pins` mode, its argparse flag and its docstring line, plus the `importlib.util`
  import that only r2 used. Nothing else in the repository invoked `--print-pins`; checked with `grep -rn` across
  `*.py`, `*.md`, `*.yml`, `*.sh` and `*.json`.

**What is left, stated as a bound:** a write made inside the harness's own functions after the assertion (in
`mutate_delivered`, say), or one that rebinds the checker's own names (`own_pin_problems`, `pin_display`), is an
edit to the checker. That is the class master had as well: beating master's typed total meant rewriting the cases
that observed it.

**Red before green.**
- **`check-plan-code`**, against stubs (`pin_display` returning `{}`, `pin_display_problems` returning `[]`, no
  wiring): 13 cases were red at 265/278.
  - The four r1/r2 runtime writes (`-= 4`, default argument, decorator, shadowed `dict`) and a runtime `del` were
    red with `got []`.
  - The duplicate key, the non-literal displays and the no-display/two-display sources were red.
  - r3's argv-gated, CI-gated and not-`--self-test` writes were red under `--mutate` with `got (1, False)`, and the
    argv write under `--self-test` timed out.
  - All are green after the change: 279/279.
- **`check-merge-ready`**, against a `pins_at` stub returning `{}`: 14 cases were red at 213/227.
  - The display fall, r2 H2's string-hidden pin, the duplicate key, a removed key and the unreadable display (head
    and base) were red.
  - So were the absent-file cases (base `{}` and head), the failing `git` calls, the real-file case, the real-git
    case and both `main()` cases.
  - The adjacent negatives (unchanged, raised, a head that would raise at import) stayed green.
  - All are green after the change: 227/227.

**Counts:**
- `check-merge-ready`: 230 → 227 cases; pin 87 → 87. Two entries were retired with their subject (non-JSON
  `--print-pins`, the base-only fallback) and two were added (a refused display read as `{}`, a failing `ls-tree`
  read as an answer). Three were rebound to renamed cases.
- `check-plan-code`: 265 → 279 cases; pin 147 → 149. Two entries were retired with `--print-pins`, and four were
  added: the assertion removed from `--mutate`, the assertion removed from `--self-test`, the duplicate-key refusal
  removed, and the display-versus-held comparison inverted.
- Derived total: 2989 → 2991.

**Sweeps** (`--mutate . --only <file> --allow-long-local`, diagnostic slices; the full sweep is CI's):
- `check-merge-ready.py`: 87 mutations, 87 killed, 87 attributed to the case each names, 0 survivors.
- `check-plan-code.py`: 149 mutations, 149 killed, 149 attributed to the case each names, 0 survivors.

**Two defects in this fold's own first draft, found by its first `check-plan-code` sweep (both fixed before commit):**
- **A recursion.** The wiring cases run a COPY of this file. Without the self-test refusal, that copy's suite reaches
  the same case and spawns another copy. The guard was an environment marker, and `fixture_git.isolated()` replaces
  the environment, so the guard never fired: the mutant that dropped the refusal recursed about 25 levels deep before
  the sweep was killed. Now each copy carries `_PINS_COPY = True` in its SOURCE, runs in its own session, and has
  its whole process group killed at a 30s timeout. Checked by hand on that mutant: the named case went red in 10s,
  and no process was left behind.
- **An unattributable mutant.** The planned "comparison inverted" (`!=` → `==`) makes AGREEING pins refused. The
  top-of-suite refusal then stops the suite as CANNOT RUN, which the harness correctly reports as *not a catch*. The
  sweep went NOT MEASURED on that one entry. The entry now inverts the comparison to refuse only a RISE
  (`(display or 0) < (held or 0)`), so a pin LOWERED at runtime passes. It goes red via the `-= 4` case.

**Ladder (decision log).** The coordinator first tried to record this round as COMPLETING the r2 REDESIGN, which
would mean a second `redesign` row on the same unit. `check-decision-scheme` refuses that form:
*"route 'redesign' is not the next route for ('derived-mutation-total', …): tried ['accrete', 'redesign'], so the only route left to bet on is 'split' — and 'redesign' is ALREADY TRIED, so this is a RETRY, not a skip"* (CANNOT RUN, rc 2; the attempt was reverted). A route is never retried on a unit. The honest reading of the log is the literal one: the
redesign's failure observation ("the unit still carried findings after a restructuring fold") WAS seen, because F1 is
a High. So the r2 row is scored `continued`, and the next rung is **SPLIT**:
- **Held as is:** the derived total, `pin_drift`, `typed_total_sites` and `pin_falls`. None drew a finding in r3.
- **Split off:** the subprocess witness (`--print-pins` + `effective_pins`). It is DELETED, not continued.
- **Continues:** the falling-pin witness, now the display read plus the harness-side assertion.

**The reviewer's judgments, recorded:**
- **No separate Phase 6 architecture review is necessary.** The reviewer gave three reasons:
  - the thrashing component (`pin-shape`) was deleted, not patched, and no r3 finding lives in it;
  - F1 is a sibling class that the redesign introduced, which "a redesign removes" (`review-method.md`, *Can a
    redesign remove it?*);
  - F1's remedy is concrete and structural, and its feasibility was measured: the display equals the effective dict
    under `--mutate .` and `CI=true`, and the three attacks differ by `(87, 82)`, `(87, 82)` and `(85, 80)` where the
    harness runs.
- **Their trigger for round 4:** "if round 4 finds a further gap between the effective dict and the harness's dict after
  that fix, the redesign route is exhausted." The split row carries the next step as its named failure observation:
  ship the derived total with the HOLD's bound stated, and give the falling-pin witness its own subject (DEFER).
