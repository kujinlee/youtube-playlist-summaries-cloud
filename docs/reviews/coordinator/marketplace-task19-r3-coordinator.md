# Round 3 — `marketplace-task19` — coordinator — deep JSON still reaches a traceback through the error messages; THRASHING arms Phase 6

```yaml
round: 3
fixes_nontrivial: false
subject: marketplace-task19
halves:
  codex: "GAP: alternation"
  claude: ran
findings:
  - {id: C1, severity: Major, aim: deliverable, fix_induced: true, component: shape, disposition: phase6}
  - {id: C2, severity: Low, aim: deliverable, fix_induced: false, component: shape, disposition: phase6}
```

The Claude half reviewed b6110b2d, the round 2 fold of plan Task 19 (PR #618): [`claude/marketplace-task19-r3-claude.md`](../claude/marketplace-task19-r3-claude.md). Verdict NOT CONVERGED.

REVIEW GAP: codex — alternation

What held in round 3:
- No over-refusal. The live tree gives rc 1 with 34 `[missing]` errors. 34 plausible Task 20 rows give rc 0, or rc 3 when the checkpoint fires.
- These numeric edge cases are all handled: `-0.0`, `True`, `int(sys.float_info.max)` against `2**1024-1`, and subnormals.
- 124 of 124 mutations were killed and attributed in a full clone, 9 of them also checked by hand.
- The pins of 124 mutations and 267 cases are honest.
- No input that used to fail now passes.

## Is this thrashing? YES — Phase 6 arms

Thrashing means two consecutive rounds whose findings came from the previous round's own fix, in one component.
- **Round 2's X1:** the round 1 shape pass's `_finite` overflowed on `10**400`.
- **Round 3's C1:** round 2's new `_check_inputs` error messages call `repr`. JSON nested about 87,000 to 116,000 deep parses but cannot be `repr`'d, so it raises `RecursionError`. The round 2 fold claimed to close deep nesting, but it closed only the depth at which `json.loads` itself fails.

**One component.** Round 1's coordinator called the scan check "the same idea at the input level" as the shape pass. They are one job: validate the content before any rule reads it. The round 2 doc labelled them `shape` and `inputs`, but that is a split I made, not one the code has. Two labels must not be used to dodge the arming condition (see the memory on self-authored retreats), so both findings here are filed under `shape`.

**Can a redesign remove it?** Probably yes, and that is the question for the Phase 6 review:
- Each round found a new input that the hand-written validation missed: shape, then types, then depth.
- C2 shows the second cost of hand-writing it. `_check_inputs` is a weaker second copy of the map rules that `check-shipping-sets.py`'s `load_map` already enforces, which refuses an unknown package and a duplicate id.
- The candidates: one bounded reader for every input, reusing `load_map` rather than restating it, and a declarative schema for each file, read by one walker.

## Dispositions

- **C1 (MAJOR, fix-induced): deep nesting reaches `RecursionError` via `repr` in a message. Sent to Phase 6.** It fails closed (rc 1 with a traceback, never rc 0), so it is not a BLOCKER. The reviewer's proposed fix is a depth bound in `_read_json`; the committed files nest at most 7 levels deep.
  **Fixed in 4f31d00b.** This is the Phase 6 fold. `_read_json` refuses nesting past `MAX_DEPTH = 32`, checked by an iterative walk; the committed inputs measure at most 6 deep. No message prints an input value except through `_show`, and `main` is a net (INTERNAL ERROR, rc 2). The evidence:
  - Self-test 296/296. "an inventory.json nested 33 deep is refused" sits beside "32 is read".
  - The permanent fuzz case: 2,054 edits of the fixture inputs, with no escape and no INTERNAL ERROR.
  - The thin fuzz through the real reader: 54,235 runs over the Task-20-shaped tree and 29,337 over the live tree. No exception escaped and none reached the net.
  - attack.py on the folded script: 66 cases, 0 TRACEBACK, 0 FAIL-OPEN. The one WRONG is P9, which is now rc 2 where the corpus expected rc 1. That is the intended refusal; see C2.
  - Mutations in a full `git clone`: 136 of 136 killed, each attributed to the case it names. All 6,497 manifest anchors resolve.
  - The live tree is rc 1 with exactly 34 `[missing]` errors. The two Task-20-shaped trees are rc 0.
- **C2 (MINOR): an unknown `package` skips the SHIP rule (rc 0), and duplicate component ids are not refused. Sent to Phase 6.** This one is fail-OPEN, so whatever the redesign, it must be closed before merge.
  **Fixed in 4f31d00b.** `_reference_errors` refuses, at rc 2:
  - a component whose `package` names no package;
  - two components with one id.

  Each has a case and an adjacent negative, and each has a mutation that is killed by the case it names. The coordinator's addition is closed too: a map component `phase` outside `MAP_PHASES` is rc 2 (corpus P9, which was fail-open under the prototype), with `1-if-feasible` as its negative. The map channel and the pass condition are type-strict `_one_of` vocabularies. `CHANNELS` and `MAP_PHASES` equal `check-shipping-sets`' own, which is asserted by import.

The Phase 6 review is filed as backlog #699 and convened at once. Its recommendation is folded on this branch, and the merge waits for it, because `check-merge-ready.py` HOLDs a thrashing PR with no architecture review in range (backlog #680, part 2).
