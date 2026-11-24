# Round 1 — `goal-node-tree-s1` (PR #631) — coordinator — fold

```yaml
round: 1
fixes_nontrivial: true
subject: goal-node-tree-s1
halves:
  codex: ran
  claude: ran
findings:
  - {id: XH1, severity: High, aim: deliverable, fix_induced: false, component: tree-grouping, disposition: fixed}
  - {id: XH2, severity: High, aim: deliverable, fix_induced: false, component: slug-grammar, disposition: fixed}
  - {id: XM3, severity: Medium, aim: deliverable, fix_induced: false, component: threads-read, disposition: fixed}
  - {id: CF1, severity: Medium, aim: deliverable, fix_induced: false, component: tree-grouping, disposition: fixed}
  - {id: CF2, severity: Medium, aim: deliverable, fix_induced: false, component: slug-grammar, disposition: fixed}
  - {id: CF3, severity: Low, aim: deliverable, fix_induced: false, component: node-rules, disposition: fixed}
  - {id: CF4, severity: Low, aim: deliverable, fix_induced: false, component: threads-read, disposition: fixed}
  - {id: CF5, severity: Low, aim: instrument, fix_induced: false, component: threads-read, disposition: fixed}
  - {id: CF6, severity: Low, aim: instrument, fix_induced: false, component: gap-pin, disposition: fixed}
  - {id: CF7, severity: Low, aim: deliverable, fix_induced: false, component: docs, disposition: declined}
```

Reviewed head `2f8c8d9d` (both halves). Halves: `docs/reviews/codex/goal-node-tree-s1-r1-codex.md` (verdict NOT
CONVERGED, `docs/reviews/verdicts/goal-node-tree-s1-r1-codex.verdict.json`) and
`docs/reviews/claude/goal-node-tree-s1-r1-claude.md` (NOT CONVERGED). XH1 and CF1 describe one defect, fixed
once. XH2 and CF2 are also one defect, fixed once. Every fix was made test-first: the case was written, seen red
against the unfixed code, and then made green.

## Findings

**XH1 = CF1 — two trunks sharing a display heading lose a node on `/features`. FIXED, keyed by slug.**
The spec supports the slug key: §2.2's table says the slug is "lowercase words joined by `-`; unique across the
WHOLE tree", and "a trunk is a node with a slug". That makes the slug the identity, and the `## ` text only its
label. Refusing a duplicate heading would have made the label part of the identity, which the spec does not say.
`group_tree` (`scripts/gen-features-page.py`) now opens one group per level-2 node and files a child under its
parent's `(trunk, slug)` slot. Parentless nodes go to a per-trunk slugless group, created when first needed. The
new case `two trunks sharing a display name keep every node` runs two inputs: both trunks slugged, and slugless
then slugged. It asserts that every node has exactly one card and one index line, and pins the groups
`group_tree` returns. A new mutation restores keying by display text, and the case kills it.

**XH2 = CF2 — a current slug is never held to the slug grammar. FIXED.**
There is now one grammar, `SLUG = ^[a-z0-9]+(?:-[a-z0-9]+)*$`, used by both `was:` (whose `ENTRY_SHAPE` now
reads it) and every current slug in `check_nodes`. This covers heading text and a trunk's `slug:` value,
including an empty `slug:`. The case `rules: every current slug follows the slug grammar` loops an independent
literal list of 7 bad shapes and 3 good ones. It also asserts that the LIVE `docs/features.md` raises no slug
problem. **Measured on the live file: 35 slugs, 0 fail the grammar**, so the STOP condition did not arise. A
mutation turns the check into `if False`, and the case kills it.

**XM3 — an undecodable threads file crashes with UnicodeDecodeError. FIXED.**
**CF4 — a threads file with no `## GOAL` heading reports FAILED with the wrong cause. FIXED.**
Both are one read path now, `read_threads(path)` in `scripts/check-features.py`. It raises `ThreadsUnreadable`
on OSError, on UnicodeDecodeError, and on a parse that found no goal table. `main` turns that into
`CANNOT RUN … Treat this as NOT RUN.` and exit 2. The read still happens only when some node carries `done:`.
Two new cases drive the REAL `main` over a constructed world:
- `G9: an undecodable threads file is CANNOT RUN` uses a lone `\xff` and a GOAL file holding a `\xfe`.
- `G9: a threads file with no goal heading is CANNOT RUN` uses an empty file and a `## Notes`-only file. It has
  a control: a GOAL heading whose request does not match must still be `(1, no CANNOT RUN)`. The control stops
  the fix from turning every mismatch into NOT RUN.

**CF3 — a stateless node may carry `expected-because:`. FIXED (refused).**
That line is the argument for an ABSENCE, and spec §2.2 ties it to `absent` ("mandatory when `absent`",
unchanged). On a node with no `state:` nobody reads it, so it is refused, with the remedy "remove it, or set
`state: absent`". The case uses two failing inputs and an `absent` control. A mutation is added.

**CF5 — no mutation pins the CANNOT RUN arm of G9. FIXED.** Four mutations were added to
`scripts/mutations/check-features.json`:
- `return 2` becomes `pass` (fail-open).
- The call site is reverted to the raw `GOAL_THREADS.read_text()`.
- `except (OSError, UnicodeDecodeError)` is narrowed to `except OSError`.
- The empty-table refusal is disabled.

Each names the case it must redden.

**CF6 — the real-tree gap case derives its expectation with the code under test. FIXED.**
The new case `over the REAL tree, the nodes that claim no area are exactly these four` compares the rendered index
against the independent literal `cloud-sync`, `serve-path-bounding`, `share-and-download`, `shared-dig-deeper`.
⚠ It passed on its first run, because it pins today's correct behaviour rather than a defect. To show it is not
vacuous, `inherits_area` was severed to `return True`. The OLD case stayed green under that sever, which confirms
the circularity CF6 named. The NEW case went red.

**CF7 — spec §3.2's example and plan Task 4 behaviour 1 are false on the live file. DECLINED on this branch
(recorded only).** Spec §3.2 names `token-usage` and `memory-recall` as today's area-less nodes. Both are goal
names that S3 brings in, so neither is in `docs/features.md` today. Plan Task 4 behaviour 1 says the index is
"byte-identical" on today's file, but the 4 nodes above change. The implementation follows §3.2's RULE, not its
example. The goal does not move. Per the coordinator's instruction, the PR body names the 4 nodes, and no spec or
plan edit rides in S1.

## Loosening answers (Codex)

- **9a6218192351 / c5f9105b20f3** — duplicate slugs, omitted state, ADR-only built nodes, and absent nodes with
  anchors. **Not a loosening; each is intended.**
  - *Omitted state:* spec §2.2, `state:` "OPTIONAL: `built`, `absent`, or omitted … Omitted means the node is a
    name only".
  - *ADR-only built node:* the S1 row of the slicing table, "A `built` node's fragment may be `areas:`, `adrs:` OR
    an anchored document (§2.2)".
  - *Absent with anchors:* the plan, "The `absent` arm counts `areas` ONLY: a backlog row is shipped work, which
    contradicts an absence; an ADR or a spec describes a gap and may sit under an absent node". The spec also
    marks `anchors:` "REMOVED (S2)".
  - *Duplicate slugs:* see bfad4ea759d8.
- **1772e62bc392** — absent nodes with anchors now pass. **Not a loosening; it is the same plan sentence** (the
  absent arm counts areas only, plan r1 F2), and spec §4 row 4.45 keeps `harness-ships-elsewhere` absent while it
  carries evidence of the gap.
- **bfad4ea759d8** — `check_nodes` no longer refuses duplicate slugs. **Not a loosening; the refusal was MOVED.**
  G6 in `slug_problems` refuses a duplicate. `main` calls it (`problems += slug_problems(nodes)`), and the case at
  `scripts/check-features.py` `any("duplicate" in p for p in slug_problems(...))` plus mutation 8 ("a repeated node
  slug stops being reported as a duplicate (G6 …)") pin it. The refusal is now WIDER, because it also covers
  former slugs and id collisions.

## Is the fold non-trivial?

**Yes.** It adds new refusals (the slug grammar and the stateless `expected-because:`), a rewritten `group_tree`,
and a new CANNOT RUN path. Each is new code no reviewer has seen, so round 2 is owed.

## Deviations, and what the gates caught during the fold

- Three gen-features mutations were REBOUND onto the rewritten `group_tree`. They are the orphan entry and the two
  `####` nesting entries, whose anchors named the deleted `entries` local. The first sweep showed the two nesting
  ones killed but UNATTRIBUTED (the suite failed without printing a `[FAIL]` line). They now inject at `n.level`.
- `check-main-drivable` flagged `_drive` because the rebind of `FEATURES`/`GOAL_THREADS` had moved into a nested
  function while `_g` was bound in the outer one. `_g = globals()` is now bound inside `_drive`.
- `check-fixture-variation` flagged `group_tree(nodes=…)` as called with one value at every site. The case now
  also asserts `group_tree([]) == []`.
- Pins in `scripts/mutations/expected_mutations.py` are check-features 51 → 57 and gen-features-page 53 → 54.
  Both equal the manifest lengths.
