<!-- codex-review: model=gpt-6.1-sol -->

- **Minor — docs/backlog.md:248:** Row **#222** has `⟦kind: defect⟧`, although its text explicitly says D2’s narrow coverage shipped deliberately and requests widening it to other entry points. This conflicts with #394’s ruling (3): adding missing coverage is a **task** unless the gap falsifies a claim. Concrete correction: `⟦kind: task⟧`.

- **Minor — scripts/check-reference-namespace.py:218–219:** Invalid-marker fallback has no regression coverage. Changing:
  ```python
  except gb.ShapeError:
      return None
  ```
  to `except gb.ShapeError: raise` survives **31/31 self-tests**. Concrete input:
  ```diff
  -| 31 | see #17 | x | S | (tooling) | open |
  +| 31 | see #17 ⟦kind: decision⟧ | x | S | (tooling) | open |
  ```
  The shipped code reports the bare reference; the surviving mutant crashes instead. Add a case asserting that an invalid marker remains subject to namespace checking.

No new-prose bypass found through changed words, whitespace, invalid markers, markers in another cell, or cross-file matching. Duplicate additions can reuse one removed line, but each stripped addition remains byte-identical, consistent with the approved exemption.

An ambient pass exists: a syntactically valid marker naming parent `backlog #999999` passes the namespace exemption; the separate parent validator rejects it. Namespace success alone does not establish marker validity.

Compared ten seeded-random rows: **191, 233, 362, 236, 222, 215, 260, 200, 77, 340**. The classification conflict above was the mismatch found. All existing rows retain identical parsed prose, severity, closure, status, bundle, size and touches. Inspected backlog readers; closure, feature-page, goal-tree and grouping self-tests passed.

Required checks:

- Passed: backlog **200/200**, features **54/54**, namespace **31/31** self-tests; live `check-features`; `check-docs`.
- Mutation slices passed: features **32/32**, namespace **14/14**.
- Mutation gates for **gen-backlog-page.py** and **check-plan-code.py did NOT run**: both commands exited 2 after local runtime-budget refusal, explicitly reporting “NOTHING WAS MEASURED.”

Read #394/#395 and their FAILS IF clauses. No files written; no `.claude/plans/` files accessed.

**NOT CONVERGED**
