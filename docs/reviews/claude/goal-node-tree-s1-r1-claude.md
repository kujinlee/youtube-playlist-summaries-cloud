# Goal node tree S1 — round 1, Claude half (adversarial)

Subject: `git diff 561379e6 HEAD` in worktree `node-tree-s1`, head `2f8c8d9d` (PR #631). Plan
`docs/superpowers/plans/2026-11-24-goal-node-tree.md`, Tasks 1–4; spec
`docs/superpowers/specs/2026-11-23-goal-node-tree-design.md` §2.2, §2.4, §2.5 (G6, G9), §3.2.
Method: `superpowers:requesting-code-review`, with the goal of refuting the slice.

## What was run (against head 2f8c8d9d)

| Command | Result |
|---|---|
| `python3 scripts/check-features.py --self-test` | rc 0, 90/90 |
| `python3 scripts/gen-features-page.py --self-test` | rc 0, 48/48 |
| `python3 scripts/goal-tree.py --self-test` | rc 0, 593/593 |
| `python3 scripts/check-features.py` (live tree) | rc 0, `35 nodes (31 built, 4 absent, 0 stateless)`: the same node count as the base |
| `python3 scripts/check-plan-code.py --mutate . --only scripts/check-features.py` | 51/51 killed, each by the case it names |
| `python3 scripts/check-plan-code.py --mutate . --only scripts/gen-features-page.py` | 53/53 killed, each by the case it names |
| `check-main-drivable.py`, `check-fixture-variation.py`, `check-ratchet-contract.py`, `check-selftest-counts.py --changed`, `check-page-links.py` | all OK |
| `check-shipping-sets.py --self-test` (the 363 edge re-pin) | **NOT OBSERVED**: still running when this review was written, so treat it as NOT RUN by this half |
| Live `/features` rendered at base (`git archive 561379e6`) and at head, then diffed | the only structural change is 4 nodes (8 lines, index plus card) moving from `0 gaps` to `claims no area — gaps not counted`. The other differences are git-derived bands, because the archive has no `.git` |
| `index: today's two levels render unchanged`: the literal re-derived by running the BASE's `render_index` on the same fixture | byte-identical, so the literal really is the base's output |

The probes below were run through `parse_features` + `check_nodes` + `slug_problems`, the same three that
`main` calls, and through `gen-features-page.render`.

## Findings

### F1 — Medium — `/features` drops a trunk node when two trunks share a display name

`scripts/gen-features-page.py` `group_tree`: `entry[1] = n` in the `n.level == 2` branch. `by_trunk` is
keyed by the trunk's DISPLAY text, so a second `## ` section with the same text overwrites the first
section's trunk node.

Failing input. `check-features` passes it with no problem:

```
## T
slug: a
for: A.
### c1
for: C.
## T
slug: b
for: B.
### c2
for: D.
```

Measured: `render(...)` emits `id="f-a"` **0 times** (`b`, `c1` and `c2` once each). Node `a` has no
card and no index line, and the trunk heading links to `b`. That is the "a view that drops a node"
failure this page exists to prevent. The live tree has three distinct trunk names, so nothing breaks
today. S3 Task 12 gives trunks slugs, and then the hole is open. Fix one of two ways. Either
`check-features` refuses two `## ` trunks that share display text when either carries a `slug:`, or
`group_tree` keys a slugged trunk by its slug. Add a case with two inputs: two slugged same-name trunks,
and one slugged plus one slugless.

### F2 — Medium — a trunk `slug:` value is never checked against the slug grammar

`scripts/check-features.py` `parse_features`, the `m.group(1) == "slug"` branch: `Node(slug=m.group(2).strip(), …)`
has no shape test. Spec §2.2 defines a slug as "lowercase words joined by `-`". The same branch's
neighbours shape-check every `was:` entry (`ENTRY_SHAPE["was"]`), so a CURRENT slug is held to a
weaker grammar than a FORMER one.

Failing inputs. Each passes `parse_features` + `check_nodes` + `slug_problems` with **zero problems**:

- `## T\nslug: Not A Slug\nfor: x.\n### a\nstate: built\nfor: A.\nareas: (x)\n` gives node `Not A Slug`,
  and `a.parent == "Not A Slug"`.
- `## T\nslug:\nfor: x.\n` gives a node with slug `""`, whose page ids are `f-` and `goal-`.

A consequence: such a node can never be renamed, because `was: Not A Slug` would be refused as "not a
slug". Heading slugs have the same gap (`### Foo Bar` passes). That gap predates the slice, but the same
one-line check closes it. Today 0 live headings fail the pattern, measured with `grep` over
`docs/features.md`. Fix: test every node's slug against `ENTRY_SHAPE["was"][0]` (the trunk `slug:` value
and the `###` heading text), in one place, with a case that loops `Not A Slug`, empty, and
`Upper-case`.

### F3 — Low — a stateless node may carry `expected-because:`

`scripts/check-features.py` `check_nodes`: the built arm refuses an `expected-because:` as "the argument
for an ABSENCE". The stateless (`state is None`) arm has no such test.

Failing input: `## T\n### x\nfor: X.\nexpected-because: e.\n` gives no problem. The line argues for an
absence on a node that does not claim one, and `render_node` does not show it, because it renders
`.why` only for `absent`. So the line is invisible, and the checker accepts it. Fix: refuse
`expected-because:` unless `state == "absent"`.

### F4 — Low — a threads file that reads but holds no `## GOAL` heading gives FAILED with the wrong cause

`scripts/check-features.py` `done_problems` and `main`: only an `OSError` becomes CANNOT RUN. Suppose the
file reads but `requests_by_goal` finds nothing: an empty file, a truncation, or a heading format
change. Every `done:` line is then reported as "docs/goal-threads.md records no such request under …
naming this node — copy the request line exactly". The gate is still red, so this does not fail open.
But it sends the author to re-copy a request that is in fact recorded. By the house rule, a parse that
found nothing is CANNOT RUN.

Failing input: `done_problems(nodes, lambda: requests_by_goal(""))` with one valid `done:` gives the
"copy the request line exactly" problem, measured. Fix: when `done_problems` would run and the table has
no headings, return CANNOT RUN from `main`.

### F5 — Low — no mutation pins the CANNOT RUN arm of G9

`scripts/mutations/check-features.json` has no entry whose `expect` is
`G9: an unreadable threads file is CANNOT RUN`. A mutation `except OSError: … return 2` → `pass`
(continue with no G9 problems) is a fail-open edit, and the case would catch it. But nothing proves the
case catches it, so the mutation sweep never exercises it. The plan's Step 5 for Task 3 does not list one,
so this is a gap in coverage, not a deviation. Fix: add the mutation.

### F6 — Low — the real-tree gap case derives its expectation with the code under test

`scripts/gen-features-page.py` `_self_test_body`, case `over the REAL tree, every index line's count is
the card's own open-row count, by severity`. The expected text of `_bad` is chosen by
`n.areas or inherits_area(n, _rby)`. That is the same predicate `gaps_html` uses, so a wrong inheritance
decision changes the rendered line and the expectation together, and the case passes. The dedicated case
`index: an inherited area still counts` does cover `inherits_area` on a fixture, so this is not a hole in
the rule's coverage. The gap is that no case pins WHICH live nodes carry the sentence. Fix: pin the live
set as a literal: `share-and-download`, `shared-dig-deeper`, `cloud-sync`, `serve-path-bounding`.

### F7 — Low (documentation) — the spec's example of an area-less node and the plan's behaviour 1 are both false on the live file

Spec §3.2 says the nodes that "today" claim and inherit no area are `token-usage` and `memory-recall`.
Neither is a node in `docs/features.md`: both are goal names that S3 brings in. Plan Task 4, behaviour 1,
says of "today's file" that "the index HTML is byte-identical to the base's". Measured, it is not: the 4
nodes in F6 change, in the index line and in the card heading. The implementation follows the RULE in
§3.2 (claims no area, inherits none). It tested behaviour 1 on a synthetic fixture, whose literal I
re-derived from the base and found byte-identical. The dashboard entry already says "Four features show
that today". Fix: name the 4 nodes in the PR body, and note that the spec's example names post-S3 nodes.
The goal does not move, so no owner decision is needed.

## The builder's stated deviations

| # | Deviation | Verdict | Why |
|---|---|---|---|
| 1 | Two fixtures moved to `areas:` | **Acceptable** | Plan Task 2 (r1 F2) and behaviours 13–15: the `absent` arm now counts `areas` only, so the old `absent` + `anchors:` fixtures (base `check-features.py` self-test, the `cloud-publishing` lines) would have stopped exercising the refusal. Moving them to `areas:` keeps "flip it to `built`" under test |
| 2 | `done_problems` takes a callable reader | **Acceptable** | It is required by the plan, not a departure from it. Task 3 behaviour 8 and Step 1 say "it passes a reader that raises if called". A reader that is called lazily is the only way `G9: no done line needs no threads file` can fail. The `any(n.done …)` guard is mutation-killed |
| 3 | Three cases passed before implementation | **Acceptable** | Cases that pin today's behaviour (the refusals that predate the slice) cannot be red first. Every new guard clause that the plan's Step 5 lists has a manifest entry killed by its named case (51/51, 53/53). Not covered: F5 |
| 4 | Existing gen-features cases changed (`dig-job-recovery` → `wake-on-visit`; real tree expects NO_AREA) | **Acceptable**, see F6 | `dig-job-recovery` claims no area and inherits none, so §3.2 requires the sentence. `wake-on-visit` inherits `job-queue`'s area, which keeps the `0 gaps` path under test. The real-tree rewrite is correct but circular (F6) |
| 5 | The "no fragment" note shows only for `built` | **Acceptable** | The note says "check-features.py should have refused this node". For a stateless node, which check-features permits bare (Task 2 behaviour 1), that statement would be false. A stateless card still shows its `for:` line |
| 6 | 4 live nodes show "claims no area", not `token-usage`/`memory-recall` | **Acceptable**, with F7 | The rule is applied as written, and the spec's example names nodes that do not exist yet |
| 7 | MAIN_DEBT removal and edge re-pin in separate commits | **Acceptable** | `check-main-drivable.py`'s `D2_pin_paid` message asks for the removal "in the same commit" as the payment, so that a paid debt cannot be re-accrued unseen. The PR squash-merges, so master receives payment, removal and re-pin as ONE commit, and the final tree is green (`check-main-drivable.py` D2 OK). Only the branch's intermediate commits `a21b0679`..`7344cdb9` would be red on it, and nothing runs per commit |

## Probes that did not find a defect

- Skipped level: `####` directly under a slugged trunk, and `######` under `###`, are both refused. An
  orphan `####` first under a slugless trunk stays top-level, and its `#####` child gets
  `parent == "a"`.
- A `#######` heading is refused. A second `slug:` line, a `slug:` after a field, a `slug:` under a
  `###`, and a `slug:` before any trunk are each refused. A `slug:` after a blank line under `##` is
  accepted, which is the plan's "directly under", read as "first non-blank line".
- `was:` listing the node's own slug is refused. `was: (b)` and `adrs: 12345` are refused entry by entry.
  `done:` with trailing text after the quote is refused.
- G6 page-id pairs: I enumerated the id sets the plan gives each view. Collisions are possible only as
  `f-`+current and `goal-`+current/former, and all three are refused, while `goal-tree` passes.
- G9: a request under a `was:` heading counts. A request after a non-GOAL `## ` heading does not count.
  `goal-tree.py` holds no second `re.compile` of either pattern (the Task 3 FAILS-IF holds).

VERDICT: NOT CONVERGED
