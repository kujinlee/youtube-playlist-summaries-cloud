# Round 1 — `marketplace-task19` — coordinator — the guard checks every rule it names but never a row's SHAPE; one fold validates the shape first

```yaml
round: 1
fixes_nontrivial: true
subject: marketplace-task19
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: Major, aim: deliverable, fix_induced: false, component: inputs, disposition: fixed}
  - {id: X2, severity: Major, aim: deliverable, fix_induced: false, component: shape, disposition: fixed}
  - {id: X3, severity: Low, aim: deliverable, fix_induced: false, component: pins, disposition: rejected}
  - {id: C1, severity: Major, aim: deliverable, fix_induced: false, component: shape, disposition: fixed}
  - {id: C2, severity: Major, aim: deliverable, fix_induced: false, component: shape, disposition: fixed}
  - {id: C3, severity: Low, aim: deliverable, fix_induced: false, component: shape, disposition: fixed}
  - {id: C4, severity: Low, aim: deliverable, fix_induced: false, component: roles, disposition: fixed}
  - {id: C5, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
```

Reviewed: PR #618 (plan Task 19, `scripts/check-inventory.py`) at 19ce4ac2. Halves:
[`codex/marketplace-task19-r1-codex.md`](../codex/marketplace-task19-r1-codex.md) (2 MAJOR, 1 MINOR),
[`claude/marketplace-task19-r1-claude.md`](../claude/marketplace-task19-r1-claude.md) (2 MAJOR, 3 MINOR).

Both halves agree on what held:
- self-test 149/149;
- the mutations they sampled were each killed by their named case (Codex 7, Claude 61 of 61, in full clones);
- the exit codes rank as the plan states;
- the CI step is `--self-test` only.

## The class

X2, C1, C2 and C3 are one defect. The guard enforces each rule it names, but it never checks that a row has the SHAPE those rules assume:
- a missing field is read as `{}`;
- a NaN or Infinity cost compares false;
- an unknown `harvest` value skips the rule keyed on the right one;
- a non-dict row crashes.

So the fix is **a shape pass that runs before the rules**, not four patches. It covers every field of the plan's row schema: presence, type, finite and positive numbers, and enum membership (`verdict`, `grade`, `phase`, `harvest`, `roles`, the criteria keys C1–C5 and their values, `cost.grade`, `route.kind`). Each failure is a named `[shape]` error. A row that fails the shape pass is not handed to the rules, so no traceback is reachable from row content. X1 is the same idea at the input level.

## Dispositions

- **X1 (MAJOR): an empty scan passes. ACCEPT.** The committed scan has an entry for all 46 components in the map, each with `findings`, `mentions` and `status`. Fix: a scan missing an entry for any component in the map is unreadable input, so **rc 2 CANNOT RUN**. A scan with no `components` at all is the same.
- **X2 / C2 (MAJOR): a row missing `criteria` or `harvest`, or with an out-of-vocabulary `harvest`, passes. ACCEPT.** Fixed by the shape pass. `harvest` is one of `practice` or `none` (spec D6, §4c). A memory-corpus row with no C5 key is refused there.
- **C1 (MAJOR): a NaN, Infinity or negative cost passes and suppresses the checkpoint. ACCEPT.** Fixed by the shape pass: both estimates must be finite and positive. `next_project_hours` ≤ 0 stays its own named rule from the plan. The loader also refuses JSON's `NaN` and `Infinity` literals (`parse_constant`), so they cannot enter at all.
- **C3 (MINOR): a non-dict row, or a list where a string is expected, crashes. ACCEPT.** Fixed by the shape pass.
- **C4 (MINOR): the scenario's entry-point is the text before the first `:`. ACCEPT, narrowed.**
  - Keep the `<entry-point id>: <description>` convention, which both live library rows use.
  - Write it into the plan's Task 19 refusal list, so the row author can know it.
  - Also require the named entry-point to be in the library's own package, as §4 says C4 is inherited from the entry-point that uses the library.
- **C5 (MINOR): the `sweep-costs.json` note says 144 cases. ACCEPT.** Drop the number, so the note cannot go stale again.
- **X3 (MINOR): the edge pin moved 358 → 360. REJECT as a loosening.** The pin is an equality on the import graph, and the graph gained two edges, each diffed against the base and named: `check-selftest-counts` → `check-inventory`, and `check-inventory` → `fixture_git`. No edge was lost. Raising an equality pin to the new true value is how the pin is meant to be maintained.

After the fold, every new rule gets a self-test case with an adjacent negative and a mutation killed by it, verified in a full clone. The live inventory must still show zero errors on the 12 existing rows.
