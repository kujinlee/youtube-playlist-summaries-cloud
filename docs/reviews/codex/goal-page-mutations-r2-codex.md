# Codex adversarial review — branch `goal-page-mutations`, round 2

**Subject:** `git diff 2246ed6d..HEAD` — the round-1 fixes (the `run=` seam on `git_pr_history` /
`git_show_files`, 10 new mutation entries, 10 new cases, three fixture repairs, and the corrected
provenance comments), with `git diff 58d82658..HEAD` for whole-branch context.

**Gate provenance:** `scripts/codex-review.py`, model `gpt-5.5`, 3489 chars, `gate_ran: true`,
`exit_code: 0` — testimony at `docs/reviews/verdicts/goal-page-mutations-r2-codex.verdict.json`.
One intrusion was recorded and is benign: the coordinator wrote `pr-body-new.md` into the scratchpad
directory holding `--out` while the run was in flight. It is not under `docs/reviews/`.

**Verdict: NOT-CONVERGED** — 1 Blocking, 1 Medium. Both were independently reproduced by the
coordinator before any code changed; the Blocking's repro is recorded in the round-2 fix commit.

---


"the file list is read from a FIXED commit, not the one it was given" — `scripts/mutations/gen-goals-page.json` now has 24 entries.

**Blocking**

Where: `scripts/gen-goals-page.py:944-953`, `scripts/gen-goals-page.py:980-984`, manifest entries at `scripts/mutations/gen-goals-page.json:244-264`.

What: the two new “fixed path / fixed sha” cases do not actually prove the parameter is used. They only prove it is not replaced with the particular manifest constants `docs/x.md` and `HEAD`.

Concrete failing scenario: if production is changed to hardcode the first fixture value, the suite stays green:

```python
# line 345 mutant
"--follow", "--", "docs/superpowers/specs/a-design.md"]

# line 364 mutant
"-1", "abc1234"]
```

That is still the real defect: every document would inherit one document’s PR history, and every PR would inherit one commit’s file list. The varied later calls do not guard this because `_run_rc1` and `_run_boom` never record or assert their argv; only `_run_ok` / `_show_ok` do, and those use the same values the mutant hardcodes.

Evidence run in a temp copy:

```text
path hardcoded to first fixture rc= 0
75/75 self-test cases passed
sha hardcoded to first fixture rc= 0
75/75 self-test cases passed
```

And through `check-plan-code.run_mutations` with probe entries:

```text
survivors= ['PROBE path hardcoded to first fixture path',
            'PROBE sha hardcoded to first fixture sha']
```

So `check-fixture-variation.py` forced cosmetic variation here: it sees multiple call-site values, but the cases still cannot distinguish “uses the parameter” from “hardcodes the first fixture”.

**Medium**

Where: `scripts/check-plan-code.py:563-566` and `scripts/check-plan-code.py:2908-2911`.

What: the old claim remains false: “gen-goals-page.py was the ONE sibling generator with no manifest”. `scripts/gen-m4-manifest.py` is also a `gen-*` script, has a self-test / check mode, and has no mutation manifest. Round 1 already called this out; round 2 did not repair it.

Concrete failing scenario: a reader sizing manifest debt from `EXPECTED_MUTATIONS` believes `gen-goals-page.py` was the only generator-class omission, when `gen-m4-manifest.py` is still outside `scripts/mutations/`.

Evidence: `rg gen-m4-manifest` shows the generator and `scripts/check-schema-gates.sh` runs `python3 ./scripts/gen-m4-manifest.py --check`; there is no `scripts/mutations/gen-m4-manifest.json`.

**Checked And Found Sound**

`python3 scripts/gen-goals-page.py --self-test` passes `75/75`.

`python3 scripts/check-plan-code.py --self-test` passes `128/128`.

`python3 scripts/check-fixture-variation.py` passes: `453 parameter(s) examined across 49 file(s)`.

The 10 new manifest entries themselves kill and attribute through the harness when applied as written; none crash-kill. All 24 `before` anchors match exactly once in `scripts/gen-goals-page.py`.

The seam does not change normal production calls I found: production still calls `git_pr_history(ROOT / rel)` and `annotate_code(got)`, while tests pass `run=...`. `rg` found no other callers outside `scripts/gen-goals-page.py`.

The `portable-practices` §22 sample checks out: commit `050913f6` changed `docs/portable-practices.md`, `scripts/gen-backlog-page.py`, and `scripts/mutations/gen-backlog-page.json` together.

Ratchet arithmetic is consistent on disk: `EXPECTED_MUTATIONS["scripts/gen-goals-page.py"] == 24`, total is `548`, and the docstring’s `75 cases` matches the executed suite.

NOT-CONVERGED.
