# Round 1 — `gates-runner-438` — coordinator — NOT CONVERGED (both halves); fold = REMOVE the skip ledger

```yaml
round: 1
fixes_nontrivial: true
subject: gates-runner-438
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: Blocking, aim: deliverable, fix_induced: false, component: skip-digest, disposition: fixed}
  - {id: X2, severity: Blocking, aim: deliverable, fix_induced: false, component: skip-digest, disposition: fixed}
  - {id: X3, severity: High, aim: deliverable, fix_induced: false, component: skip-digest, disposition: fixed}
  - {id: X4, severity: High, aim: deliverable, fix_induced: false, component: skip-digest, disposition: fixed}
  - {id: X5, severity: Medium, aim: deliverable, fix_induced: false, component: tracer, disposition: fixed}
  - {id: X6, severity: Medium, aim: deliverable, fix_induced: false, component: ledger, disposition: fixed}
  - {id: C1, severity: Blocking, aim: deliverable, fix_induced: false, component: skip-digest, disposition: fixed}
  - {id: C2, severity: Medium, aim: deliverable, fix_induced: false, component: tracer, disposition: fixed}
  - {id: C3, severity: Low, aim: deliverable, fix_induced: false, component: skip-digest, disposition: fixed}
  - {id: C4, severity: Low, aim: deliverable, fix_induced: false, component: gate-set, disposition: fixed}
```

Halves: `docs/reviews/codex/gates-runner-438-r1-codex.md`, `docs/reviews/claude/gates-runner-438-r1-claude.md`,
both on `a09cc99c`. Both reproduced FALSE SKIPS — a gate printed SKIPPED, the battery exited 0, and the same gate run
directly exited 1.

**Decision (coordinator, on the owner's rule that an optimisation's realistic risk must not outweigh its benefit):
the skip ledger is REMOVED, not repaired.** Measured benefit: 8m39s with every gate run against 7m49s with 43 of 80
gates skipped — about 50 s per run (Claude half, *Observation*). Measured risk: a false green that every probe in this
round could produce, by five independent routes. The runner's value is ONE command that runs CI `verify`'s PR-only
gate set before the push; that is kept. Deleted: the audit-hook tracer (`sitecustomize`), the input digest, `World`,
the ledger and every SKIPPED path (`scripts/gates-for-pr.py` 1,088 → ~500 lines). Every gate in the set now runs
every time. "Fixed" below means MOOT BY REMOVAL unless a file:line is given.

| Finding | Disposition |
|---|---|
| X1 / C1 — a helper imported from a warm `.pyc` is not in the input set (quoted false green on `check-guard-coverage self-test`) | MOOT by removal — no input set exists |
| X2 — a symlink outside the repository is not an input (false green on `check-memory-link`) | MOOT by removal |
| X3 / C3 — the branch name is not in a git-reading gate's digest | MOOT by removal |
| X4 — env, a C-level read, the network, the clock and a chained `sitecustomize` are unbounded | MOOT by removal |
| X5 / C2 — nested tracers recurse; the runner's own gate FAILS under the runner | FIXED: the tracer is gone, and a case now runs this self-test UNDER `run_gate`, as the battery does (`scripts/gates-for-pr.py:382-383`; the nested run passes `--nested-self-test`, `:56`, so it recurses once) |
| X6 / C4 (malformed ledger entry) — a structurally bad record crashes instead of running | MOOT by removal — there is no ledger |
| C4 (env bounds) | MOOT by removal |
| C4 (the `mutation-sweep` job is missing from OUT OF SET) | FIXED: every `ci.yml` job other than `verify` is printed OUT OF SET (`:153`), with a named reason for the two sweep jobs (`OTHER_JOBS`, `:64`); the live-ci.yml case asserts the `mutation-sweep` line |

Kept, unchanged in behaviour: the set derived from `ci.yml`'s `verify` job, the `--base` rewrite, OUT OF SET lines with
reasons, the per-gate timeout, one mutation slice per moved manifest. New: `exit_code` (`:191`) — the run is 0 only when
every gate PASSED, 1 on any FAIL, 2 on any other non-pass — so a TIMEOUT, KILLED or CANNOT RUN can never read as green.
No parallelism existed; none was added.

**Evidence on the fold:** `--self-test` 35/35 (was 61: the trace/digest/ledger cases left with their subject). ⟳ Pyright (coordinator) flagged `rc` possibly unbound in `run_gate`: no reachable path left it unset (a wait exception other than the timeout re-raises), but a gate that cannot be STARTED (`Popen` raising `OSError`) crashed the whole run with a traceback. It is now an explicit CANNOT RUN outcome with the reason in its log, and `rc` starts as None; two cases cover a missing gate script (python's exit 2) and an unstartable gate.
`check-plan-code --mutate . --only scripts/gates-for-pr.py`: 10 mutations, 10 killed, 10 attributed. `EXPECTED_MUTATIONS`
23 → 10: 17 retired with their subject, 6 kept, 4 new — recorded at `scripts/check-plan-code.py` (the pin's comment) and in
backlog row 438. `check-fixture-variation` `EXAMINED_KEYS` re-derived by running `analyse()`. `.gitignore`'s ledger line
reverted. No follow-up backlog row: a safe skip would have to be limited to gates that declare their inputs, and 50 s
per run does not pay for it (stated in row 438).

**Not run:** a full real battery on the fold. The nested case runs the runner's own gate under `run_gate`, and the
end-to-end cases run `main()` over a built repository with PASS, FAIL, CANNOT RUN, TIMEOUT and KILLED gates.

**Next:** round 2, Claude half only; its record carries `REVIEW GAP: codex — alternation` (round 1 ran both halves).
