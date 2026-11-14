---
name: backlog-edit-needs-gen-backlog-page-selftest
description: "After editing docs/backlog.md, also run gen-backlog-page.py --self-test — its REAL-backlog cases are a doc guard that no check-* script covers"
metadata:
  node_type: memory
  type: feedback
  originSessionId: f7c144b8-1b6c-4db3-8ef1-932d4e701b12
  modified: 2026-11-09T12:18:55.454Z
---

After ANY edit to `docs/backlog.md`, run `python3 scripts/gen-backlog-page.py --self-test` as well as the `check-*` document guards.

Two of its cases read the REAL backlog:
- every row declares `⟦kind: story|task|defect⟧`;
- every row of 600 or more characters lays out into blocks, using a bold `**Label:**` or an `(a) (b)` run.

**Why:** on 2026-11-09, PR #547 (backlog #586) passed every `check-*` guard locally. CI then went red on 23 sweep shards with CANNOT RUN. The cause: the `gen-backlog-page` control run failed on the real rows, so every shard that selected it could not run. The `docs/CLAUDE.md` rule says "run all the `check-*` steps", and this check is not one of them. The red shows up as a sweep failure, not as a docs failure.

**How to apply:** it is quick (247 cases). For a pinpoint answer, call `g.unlaid_rows(g.parse(lines))` and `g.missing_kind_notes(...)` through importlib, which names the offending row. Related: [[run-pr-only-gates-before-push]], [[a-check-result-is-not-the-claim]].
