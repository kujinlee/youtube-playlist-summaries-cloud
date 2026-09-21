# pin-python-interpreter — round 5 — Codex half (scoped to the r4-fix delta)

Subject: `git diff 5206e020..020b04ad -- scripts/`. `gpt-5.5`; `docs/reviews/verdicts/pin-r5-codex.verdict.json` records `gate_ran=true`. Ran concurrently with the Claude half on the same delta.

<!-- codex-review: model=gpt-5.5 -->

VERDICT: NOT CONVERGED

Findings:

High: `020b04ad:scripts/check-python-pin.py:200-203` still treats any nested key literally named `steps:` as the job’s step list. This refutes the new scoping rule. A valid matrix dimension named `steps` is inside the job block but is not `jobs.<job>.steps`; at `020b04ad`, this probe returned `declared_pins == ['9.9']` and `unpinned_jobs == []` for a job whose real steps are only `- run: echo hi`:

```yaml
jobs:
  verify:
    strategy:
      matrix:
        steps:
          - uses: actions/setup-python@v5
            with:
              python-version: '9.9'
    steps:
      - run: echo hi
```

That is the same false-green class as r4: a non-step list pins an unpinned job.

Medium: `steps:` with same-line YAML metadata is now missed. The opener regex at `020b04ad:scripts/check-python-pin.py:200` only accepts `steps:` plus an optional comment. A pinned job using a YAML anchor is read as unpinned:

```yaml
jobs:
  verify:
    steps: &py
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
```

Measured against `020b04ad`: `declared_pins == []`, `unpinned_jobs == ['w.yml:verify']`. `steps: !!seq` has the same failure. This is fail-closed, but it is a real regression in the new scoping rule.

Medium: the two repaired mutation entries do not attribute to exactly one case. Running the `020b04ad` source in memory with the manifest edits:

- r3 block-scalar mask removal at `scripts/mutations/check-python-pin.json:300-308` failed 5 cases, not exactly the re-pointed expect.
- r4 `steps_indent = -1` at `scripts/mutations/check-python-pin.json:355-363` failed 3 cases:
  - `a matrix.include entry is NOT a step, so its pin does not count`
  - `...and the job around it reads UNPINNED`
  - `a real step still counts when a matrix.include sits beside it`

So the specific “exactly one case” claim is not true for either entry.

What I ran:

- Pinned review target to `020b04ad` explicitly because the local branch advanced during review.
- Executed `020b04ad:scripts/check-python-pin.py` in memory: `75/75 passed`.
- Ran targeted in-memory probes and mutations above.
- Started full `python3 scripts/check-plan-code.py --mutate .`, but interrupted it after it ran too long without a summary; full mutation run is NOT RUN from this review.

---

## Coordinator disposition

### High — CONFIRMED, and BOTH HALVES FOUND IT INDEPENDENTLY

Identical fixture to the Claude half's F1, reached separately: a matrix dimension named `steps`. Already closed in `7156721a` by the shallowest-`steps:` invariant — a job's step list is the shallowest `steps:` in the file, so a matrix dimension is necessarily deeper. Verified `[]` at HEAD.

⚠ **Two independent reviewers converging on one fixture is the strongest signal this round produced**, and it is worth recording that neither the coordinator's r4 probe nor its r5 probe found it: both tested a matrix whose dimension was a list of SCALARS.

### Medium (node properties) — CONFIRMED and FIXED. A regression the scoping rule introduced.

`steps: &py` and `steps: !!seq` — an anchor or tag is node METADATA, not a value, and the opener accepted only a bare key plus a comment. Measured: a PINNED job read as UNPINNED. Fixed by `_STEPS_KEY`, which accepts `(?:[&!]\\S+\\s*)*` before the optional comment. ⚠ The widening is kept honest by a negative case: a real scalar (`steps: '3'`) still does NOT open a scope, which is what stops an unrelated key named `steps` from re-scoping.

### Medium (attribution) — ⛔ REFUTED, with evidence, and the distinction matters

Codex reports the two repaired entries fail 5 and 3 cases and concludes the "exactly one" claim is untrue. **That is a misreading of the rule.** `check-plan-code.py:1479-1484` iterates `for w, m in unnamed` where `m` is *the set of red cases the EXPECT matches* — the requirement is that an `expect` **identifies** exactly one case, not that only one case reddens. A mutation legitimately breaking several behaviours is expected and common.

Decisive evidence rather than argument: a full `--mutate .` run against `5206e020` reported **861 killed, 860 attributed** — exactly ONE unattributed entry, the stale expect Codex itself found in r4. Under Codex's reading, dozens would have been unattributed. Re-verified at HEAD with the same check the harness performs: **37 mutations, 0 problems.**

⚠ Codex states the full mutation run is **NOT RUN** from this review — it interrupted it. Its targeted probes stand; its coverage claim does not.

REVIEW GAP: none for this half — the Claude half ran concurrently and is filed at `docs/reviews/claude/pin-python-interpreter-r5-claude.md`.
