<!-- codex-review: model=gpt-5.5 -->

# Codex adversarial review — feature hub PLAN — round 1
## Verdict: FINDINGS

## Did the plan's code run? (what you extracted, what you ran, what it printed)

I extracted and ran the Task 1 `parse_features` / `check_nodes` implementation plus its self-test harness from `docs/superpowers/plans/2026-09-19-feature-hub.md:60-238`.

It did not pass:

```text
  ✗ clean tree passes the rules
      got  ['features.md:8: `rate-limiting-per-account` has no `for:` line — every node says what it is for']
      want []

11/12 self-test cases passed
```

I then added the Task 3 `backlog_areas` / `check_cross` code and the six new cases from `docs/superpowers/plans/2026-09-19-feature-hub.md:376-490`.

It also did not pass:

```text
  ✗ clean tree passes the rules
      got  ['features.md:8: `rate-limiting-per-account` has no `for:` line — every node says what it is for']
      want []

17/18 self-test cases passed
```

I also ran the Task 4 importlib snippet against a temp hyphenated `check-features.py` containing the planned dataclass. It worked:

```text
import ok <class 'check_features.Node'>
```

I checked the four Task 6 mutation edit anchors against the planned source text. Each exact anchor matched once.

## Findings

### [Blocking] 1 — Task 1 and Task 3 self-tests are red as written
**Evidence:** `docs/superpowers/plans/2026-09-19-feature-hub.md:102-112` defines the “clean” fixture’s absent node without a `for:` line. `check_nodes` requires purpose prose for every node at `docs/superpowers/plans/2026-09-19-feature-hub.md:216-217`.

Real output from extracted Task 1 code:

```text
✗ clean tree passes the rules
got ['features.md:8: `rate-limiting-per-account` has no `for:` line — every node says what it is for']
11/12 self-test cases passed
```

Real output after Task 3 cases:

```text
17/18 self-test cases passed
```

**Why it matters:** The plan’s claimed `12/12` and `18/18` are false. An executor following it cannot get the first guard green.

**Fix:** Add a `for:` line to the absent node in the `TREE` fixture and to the Task 2 absent example at `docs/superpowers/plans/2026-09-19-feature-hub.md:341-345`, or deliberately change the rule. The spec supports adding purpose prose: `docs/superpowers/specs/2026-09-19-feature-hub-design.md:131-134`.

### [Blocking] 2 — The `Feature` column is added but never parsed, rendered, or validated
**Evidence:** The spec says specs/plans attach through `Anchor:` header → anchor registry `Feature:` at `docs/superpowers/specs/2026-09-19-feature-hub-design.md:113-116`, and enforcement requires every `Feature:` in `anchors.md` to resolve to a node at `docs/superpowers/specs/2026-09-19-feature-hub-design.md:163-166`.

The plan adds the column at `docs/superpowers/plans/2026-09-19-feature-hub.md:321-331`, but Task 3 only validates node-local `anchors:` values against registry slugs at `docs/superpowers/plans/2026-09-19-feature-hub.md:430-455`. Task 4 then resolves ADRs/specs “via the anchors named on the node” at `docs/superpowers/plans/2026-09-19-feature-hub.md:546-549`.

**Why it matters:** A wrong or stale `Feature` cell in `docs/anchors.md` can pass every planned check. More importantly, the implementation does not build the spec’s declared attachment path; it creates a second hand-maintained mapping in `docs/features.md`.

**Fix:** Parse the `Feature` column from `docs/anchors.md`, enforce every non-empty feature slug resolves to exactly one node, and make spec/plan/ADR attachment derive from document `Anchor:` → registry `Feature`. If node-local `anchors:` remain, define whether they are aliases or redundant declarations and validate both directions.

### [High] 3 — `gen-features-page.py` will fail the ratchet contract’s widened R4
**Evidence:** The plan creates `scripts/gen-features-page.py` with `--self-test` at `docs/superpowers/plans/2026-09-19-feature-hub.md:504-557`, but only creates `scripts/mutations/check-features.json` at `docs/superpowers/plans/2026-09-19-feature-hub.md:631-662`.

This repo’s ratchet contract applies R4 to self-tested non-guard scripts too: `scripts/check-ratchet-contract.py:402-411`, with failures emitted at `scripts/check-ratchet-contract.py:430-436`.

I ran `evaluate()` with a synthetic `scripts/gen-features-page.py` that has a self-test and no manifest:

```text
scripts/gen-features-page.py R4W_no_mutation_manifest: a self-tested script outside the guard population has no scripts/mutations/<name>.json, and no NO-MUTATIONS escape in its DOCSTRING ...
```

**Why it matters:** Task 6’s claim that `check-ratchet-contract.py` will exit 0 is false unless the page generator also gets a mutation manifest, a docstring `NO-MUTATIONS:` reason, or is explicitly added to widened debt.

**Fix:** Add `scripts/mutations/gen-features-page.json` or a real `NO-MUTATIONS:` docstring reason. A manifest is more consistent with `gen-goals-page.py`, which already has one.

### [High] 4 — Task 6 omits the required `EXPECTED_MUTATIONS` update
**Evidence:** The plan adds `scripts/mutations/check-features.json` at `docs/superpowers/plans/2026-09-19-feature-hub.md:631-662` and then runs `python3 scripts/check-plan-code.py --mutate .` at `docs/superpowers/plans/2026-09-19-feature-hub.md:664-669`.

But `scripts/check-plan-code.py` requires every manifest target to have an exact declared count in `EXPECTED_MUTATIONS`: `scripts/check-plan-code.py:1145-1154`.

**Why it matters:** A new manifest for `scripts/check-features.py` will be refused as “mutation(s) but no declared count” unless the dict is updated in the same change.

**Fix:** Add `scripts/check-features.py: 4` to `EXPECTED_MUTATIONS` in `scripts/check-plan-code.py`. If `gen-features-page.py` gets a manifest too, add that count as well.

### [High] 5 — New declared self-test counts are not pinned in `check-selftest-counts.py`
**Evidence:** The plan’s docstrings declare counts for `check-features.py` and `gen-features-page.py`: `docs/superpowers/plans/2026-09-19-feature-hub.md:64-65`, `docs/superpowers/plans/2026-09-19-feature-hub.md:516`.

`check-selftest-counts.py` says declaring-but-not-pinned fails at `scripts/check-selftest-counts.py:33-39`, and its pinned population is explicit at `scripts/check-selftest-counts.py:83-182`.

The plan only says to run the checker and fix the docstring if it drifts: `docs/superpowers/plans/2026-09-19-feature-hub.md:677-680`.

**Why it matters:** Once these files exist with canonical count declarations, `check-selftest-counts.py` will fail unless the population is updated.

**Fix:** Add `check-features.py` and `gen-features-page.py` to `POPULATION` in `scripts/check-selftest-counts.py`.

### [High] 6 — `backlog.md` “unparseable → exit 2” is not actually implemented
**Evidence:** The spec requires corrupt backlog input to exit 2: `docs/superpowers/specs/2026-09-19-feature-hub-design.md:169-170`. The plan repeats that at `docs/superpowers/plans/2026-09-19-feature-hub.md:22`.

But `backlog_areas` only skips lines that do not look like rows and reads `line.split("|")[-3]`: `docs/superpowers/plans/2026-09-19-feature-hub.md:418-427`. `main()` only exits 2 if no areas at all were parsed: `docs/superpowers/plans/2026-09-19-feature-hub.md:468-471`.

**Why it matters:** A partially malformed backlog with at least one parseable area is treated as runnable. That violates the “cannot run is failure” rule and can silently drop rows from `/features`.

**Fix:** Make the backlog parser validate the table shape for every item row, or reuse the existing backlog table shape rule. Return parse problems separately from areas and make `main()` return 2 on any structural parse failure.

### [Medium] 7 — The status-token rule is obeyable but broad enough to reject plausible purpose prose
**Evidence:** The regex is at `docs/superpowers/plans/2026-09-19-feature-hub.md:74-77`; the spec defines the same token list at `docs/superpowers/specs/2026-09-19-feature-hub-design.md:140-144`.

I tested the two purpose lines the plan proposes; both pass. Plausible feature-purpose prose for process/dev-infra nodes mostly passed, but this legitimate sentence failed:

```text
HIT 'planned' Records planned absences so necessary missing features are visible.
```

**Why it matters:** The word `planned` is not always status. The first executor trying to describe absence tracking can hit this and either contort the prose or delete the rule.

**Fix:** Keep the rule if desired, but add examples/guidance for acceptable alternatives, or narrow `planned` to status-shaped phrases such as “planned for”, “planned work”, or a status field, rather than every word-boundary occurrence.

## Things I checked and found correct

`backlog_areas` uses the right cell for today’s `docs/backlog.md`. The real header is `| # | Item | Touches | Size | Bundle | Status |` at `docs/backlog.md:30`, and a real row splits with `[-3] == '(process)'`, the Bundle/area cell.

Adding a final `Feature` column does not break `check-anchors.py`; its registry parser only matches the first cell: `scripts/check-anchors.py:71-77`. It also does not obviously break `gen-goals-page.py`; its registry row regex reads the first three cells and is not end-anchored: `scripts/gen-goals-page.py:64`, `scripts/gen-goals-page.py:80-87`.

The Task 4 hyphenated-file import snippet works for the planned `check-features.py` shape.

The four Task 6 mutation edit anchors match the planned `check-features.py` text exactly once, including indentation. `expect` as a list is supported by `check-plan-code.py`: `scripts/check-plan-code.py:1352-1370`.

## What I could not run

I could not run a completed `scripts/gen-features-page.py --self-test` because Task 4 only gives test cases and import code, not a full `render()` implementation.

I did not run the real `python3 scripts/check-features.py` or `python3 scripts/gen-features-page.py` because those files are not implemented in the checkout; I ran the extracted plan code in an isolated Python harness instead.
