<!-- CLAUDE half of review round 2 — branch `budget-slack-warning`, subject `git diff a5837b84..8197d80c` (the fix wave for round 2's Codex half). Written 2026-09-20. -->

# `check-merge-ready.py` — round 2, Claude half

**Verdict: NOT safe to merge.** The commit's central claim — that `unattributed_conditions()` makes
the hand-rolled parser *unable to be silently wrong* — is **false**, and I can demonstrate it two
ways on legal GitHub Actions YAML. Everything else in the commit verified correct, including both
re-anchored mutations, the `MergeStateStatus` enum (checked by live introspection), and the budget
bound.

## Gates run (rc captured before any pipe)

| Command | rc |
|---|---|
| `check-merge-ready.py --self-test` | 0 — 46/46 |
| `check-docs.py` | 0 |
| `check-docs.py --self-test` | 0 — 22/22 |
| `check-plan-code.py --self-test` | 0 — 128/128 |
| `check-ratchet-contract.py` | 0 — 38 guards |
| `check-selftest-counts.py` | 0 — 43 scripts declare a count, each verified by running it |
| `check-fixture-variation.py` | 0 |

---

## 🔴 High — a pull-request gate can be MISSED with the stray list EMPTY, so `CANNOT RUN` never fires

This is the hole the soundness check exists to close. It is open, by two independent mechanisms.

### (a) The detector is WEAKER than the parser it audits

`_cond_at()` joins a folded scalar's continuation lines before matching. `unattributed_conditions()`
does not — it applies the single-line `PR_ONLY_COND` to raw lines. **A condition whose text spans a
line break is therefore invisible to BOTH**: the parser does not claim it, and the auditor sees
nothing to be left over.

```yaml
      - name: x
        if: github.event_name ==
          'pull_request'
        run: y
```

Measured: `pr_only_steps → []`, `job_level_gates → []`, `unattributed_conditions → []`. A real
PR-only gate, silently dropped, with the soundness check reporting clean. That is a plain multi-line
scalar — valid YAML, and Actions evaluates it.

This is the *second implementation of one rule drifts* shape: the auditor re-implements "what is a
condition line" in a weaker form than its subject, so it certifies a parse it could not perform.

### (b) It compares a COUNT, not a SET — and a surplus absorbs a real miss

`claimed = len(steps) + len(jobs)` against `len(present)`, then `present[claimed:]`. Any construct
that produces a **claim without a matching `present` line** creates a surplus that swallows a
genuinely unattributed line. A folded condition split so that no single physical line carries the
substring is exactly that: `_cond_at` joins it and the step is claimed, while `present` gets nothing.

```yaml
jobs:
  a:
    steps:
      - name: folded
        if: >
          github.event_name ==
          'pull_request'
        run: x
      - uses: ./.github/actions/gate
        if: github.event_name == 'pull_request'
```

Measured: `steps → ['folded']`, `jobs → []`, `stray → []`. **The second step is a pull-request gate
in neither list, and nothing is reported.** `claimed=1` (the folded step), `present=1` (the unnamed
step's `if:` line), totals agree, and the `len(present) > claimed` guard short-circuits.

The same cancellation is available from any double-claim: a single `if:` line counted by *both*
`pr_only_steps` and `job_level_gates` (reachable whenever a `- ` sequence sits at indent 2 under a
`  key:`) yields `claimed=2, present=1` and an empty stray by construction.

**Consequence:** the docstring's *"It CAN be made unable to be silently wrong"* and `main()`'s
*"CANNOT RUN … so its list of gates is INCOMPLETE"* both overstate what is implemented. A set
comparison — attribute each condition line to the step or job that claimed it, and report the
unclaimed *lines* — would close (b); running `present` through the same folding reader as `_cond_at`
would close (a). Neither is done.

---

## 🟠 Medium — `unattributed_conditions` fires on ordinary workflows, so `CANNOT RUN` is also wrong in the other direction

Any line carrying the condition that is not an `if:` line and not a whole-line comment is added to
`present` unconditionally. All three of these make the **entire script** return 2:

| Shape | Measured stray |
|---|---|
| `IS_PR: ${{ github.event_name == 'pull_request' }}` in an `env:` block | 1 |
| `run: echo "github.event_name == 'pull_request'"` | 1 |
| `run: echo hi  # github.event_name == 'pull_request'` (trailing comment) | 1 |
| a gated step with `uses:` and no `name:` | 1 |

The first is ordinary GitHub Actions, and `ci.yml:419` already writes
`BODY: ${{ github.event.pull_request.body }}` in an `env:` block — the refusing form is one edit
away, in a file this script parses. A checker that refuses to answer on a normal repository is a
checker nobody keeps, and this one's refusal is global (the loop returns 2 for *any* workflow).

---

## 🟡 Low — `_cond_at` over-reads on `- if: >`, and can invert a step's gate

`indent` is taken from `(\s*)` **before** the optional `- `, so for `      - if: >` it is 6, not the
key indent 8. The continuation loop then collects every following line deeper than 6 — which
includes the step's own `name:` and `run:` keys.

```yaml
      - if: >
          github.event_name == 'push'
        name: x
        run: echo "github.event_name == 'pull_request'"
```

Measured: `pr_only_steps → ['x']`, `stray → []`. A **push**-gated step is reported as PR-only. The
direction is benign (the script runs a gate CI would not), but it is a false claim, and it consumes
a claim slot — i.e. it is a surplus generator feeding the High above.

## 🟡 Low — the relocated `MergeStateStatus` comment points the wrong way

`check-merge-ready.py:83`: *"draftness is its own `isDraft` field and is checked separately above."*
The `isDraft` check is at `:262`, **below**. The sentence was true where the comment used to live
(inside `mergeability()`, after the draft check); the move to module scope broke the referent.

## 🟡 Low — the real-workflow self-test case passes vacuously when there are no workflows

```python
check("the real workflows leave nothing unattributed",
      [...] if WORKFLOW_DIR.is_dir() else [], [])
```

A missing `WORKFLOW_DIR` is CANNOT RUN, not a pass. This is not hypothetical: while applying the two
mutations I first ran the mutant from outside the repo, and this case went green having read zero
workflows. Per the project rule, a check that cannot reach its subject must fail loudly.

---

## Verified correct — no finding

- **Both re-anchored mutations (task item 5).** Each `edits` anchor occurs **exactly once** in
  `check-merge-ready.py`; all 8 entries in the manifest do. Control green (46/46). Applied in-repo:
  `key-indent restriction is dropped` → rc=1, red via *"an `if:` inside a run: body does not shadow
  the step's own condition"*; `a folded scalar stops being followed` → rc=1, red via *"a FOLDED
  condition (`if: >`) is read from its continuation lines"*. Both `expect` strings name a case that
  actually reds. (Both also red a second, related case; the named one is among them.)
- **The `MergeStateStatus` enum comment.** `gh api graphql` introspection returns exactly
  `DIRTY, UNKNOWN, BLOCKED, BEHIND, UNSTABLE, HAS_HOOKS, CLEAN` — seven members, no `DRAFT`. The
  comment's list and its "three of the seven" count are both right.
- **The budget bound.** `budget_verdict(0, b) != "ok"` for exactly `b ∈ {0, 1}` across 0–2000, so
  "ok is reachable for every budget of 2 or more" is exact, and the new self-test case asserts the
  boundary rather than describing it.
- **"Both real workflows leave nothing unattributed."** True today: `ci.yml` has two inline
  step-level conditions (`:417`, `:442`), both claimed; `schema-gates.yml` has none. The only other
  `pull_request` occurrences are `github.event.pull_request.body` and prose, which `PR_ONLY_COND`
  correctly does not match.
- **The v3 account in the `pr_only_steps` docstring.** Checked against `a5837b84`: the old `flush()`
  scanned the whole block and took the first `if:`-shaped line, so a `run: |` body line did shadow
  the step's own condition. The account is accurate.
- **`job_level_gates` is defined once** (`:176`) after the move — no shadowed duplicate survives.
