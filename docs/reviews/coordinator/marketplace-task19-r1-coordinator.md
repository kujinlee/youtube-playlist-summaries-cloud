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
  - **Fixed in 96ac3fbd** (anchors d28ee4b0). Cases (each rc 2, CANNOT RUN): a scan `{}`, `{"components": {}}`, a scan without `lib` (the output names it), `lib`'s findings an object, `lib`'s findings `[42]`. The adjacent negative is "a clean inventory below the threshold exits 0", whose scan covers the map. Mutations: an empty scan read as no findings, a missing component read as no findings, a findings object read as a list, a non-object finding accepted. Live run on `docs/marketplace/inventory.json`: rc 1, 34 errors, all `[missing]`, zero on the 12 existing rows. Mutations verified in a full `git clone` at d28ee4b0: 98 of 98 killed, each attributed to the case it names; the all-manifest anchor resolve gives 0 unresolved over 107 manifests.
- **X2 / C2 (MAJOR): a row missing `criteria` or `harvest`, or with an out-of-vocabulary `harvest`, passes. ACCEPT.** Fixed by the shape pass. `harvest` is one of `practice` or `none` (spec D6, §4c). A memory-corpus row with no C5 key is refused there.
  - **Fixed in 96ac3fbd** (anchors d28ee4b0). Cases: missing `harvest`, `bogus`, `Practice`; missing `criteria`, a list, missing C5 on a corpus SHIP, an extra C6, a value `bogus`, with the negative "every criterion value in the vocabulary is clean"; a data row with no criteria reports ONLY `[shape]`. Mutations: harvest vocabulary, criteria may omit / carry an extra key, criterion value vocabulary, a malformed row handed to the rules. Live run on `docs/marketplace/inventory.json`: rc 1, 34 errors, all `[missing]`, zero on the 12 existing rows. Mutations verified in a full `git clone` at d28ee4b0: 98 of 98 killed, each attributed to the case it names; the all-manifest anchor resolve gives 0 unresolved over 107 manifests.
- **C1 (MAJOR): a NaN, Infinity or negative cost passes and suppresses the checkpoint. ACCEPT.** Fixed by the shape pass: both estimates must be finite and positive. `next_project_hours` ≤ 0 stays its own named rule from the plan. The loader also refuses JSON's `NaN` and `Infinity` literals (`parse_constant`), so they cannot enter at all.
  - **Fixed in 96ac3fbd** (anchors d28ee4b0). Cases: public_bar_hours NaN, inf, -9, 0 (negatives 0.5 and int 6 clean); next_project_hours inf, NaN, True; route cost_hours missing, inf, 0; the JSON constants NaN, Infinity, -Infinity exit 2; `1e999` exits 1 with `[shape]`. Mutations: `_finite` reduced to `_num`, infinite public bar, public bar 0, infinite next-project, infinite route cost, route cost 0, `parse_constant` removed. `[next-project]` (≤ 0) is unchanged. Live run on `docs/marketplace/inventory.json`: rc 1, 34 errors, all `[missing]`, zero on the 12 existing rows. Mutations verified in a full `git clone` at d28ee4b0: 98 of 98 killed, each attributed to the case it names; the all-manifest anchor resolve gives 0 unresolved over 107 manifests.
- **C3 (MINOR): a non-dict row, or a list where a string is expected, crashes. ACCEPT.** Fixed by the shape pass.
  - **Fixed in 96ac3fbd** (anchors d28ee4b0). Cases: a row that is 42 or a list; id, scenario, practice_entry, roles, rests_on, route kind as the wrong type; a finding id that is an object is `[ground-finding]`; a non-object row and two rows sharing an unhashable id are no inventory error; at the CLI a non-object row exits 1 with `?: [shape]` and the other rows still checked. Mutations: non-object row, missing key, the row's id/`?` naming, the fid string check, and the two `inventory_errors` guards. Live run on `docs/marketplace/inventory.json`: rc 1, 34 errors, all `[missing]`, zero on the 12 existing rows. Mutations verified in a full `git clone` at d28ee4b0: 98 of 98 killed, each attributed to the case it names; the all-manifest anchor resolve gives 0 unresolved over 107 manifests.
- **C4 (MINOR): the scenario's entry-point is the text before the first `:`. ACCEPT, narrowed.**
  - Keep the `<entry-point id>: <description>` convention, which both live library rows use.
  - Write it into the plan's Task 19 refusal list, so the row author can know it.
  - Also require the named entry-point to be in the library's own package, as §4 says C4 is inherited from the entry-point that uses the library.
  - **Fixed in 96ac3fbd** (anchors d28ee4b0). Case: a SHIP library naming a passing entry-point of ANOTHER package is `[ship-experiment]`; adjacent negative: the same entry-point moved into the library's package is clean. Mutation: "a library may name another package's entry-point". The convention is one added line in the plan's Task 19 refusal list (docs/superpowers/plans/2026-11-11-marketplace-inventory.md), and the docstring's `[ship-experiment]` entry. Live run on `docs/marketplace/inventory.json`: rc 1, 34 errors, all `[missing]`, zero on the 12 existing rows. Mutations verified in a full `git clone` at d28ee4b0: 98 of 98 killed, each attributed to the case it names; the all-manifest anchor resolve gives 0 unresolved over 107 manifests.
- **C5 (MINOR): the `sweep-costs.json` note says 144 cases. ACCEPT.** Drop the number, so the note cannot go stale again.
  - **Fixed in 96ac3fbd.** The note now reads "(self-test 0.13 s locally; priced 0.5 s, no CI sample yet)"; 215 cases run in 0.19 s locally, still under the price.
- **X3 (MINOR): the edge pin moved 358 → 360. REJECT as a loosening.** The pin is an equality on the import graph, and the graph gained two edges, each diffed against the base and named: `check-selftest-counts` → `check-inventory`, and `check-inventory` → `fixture_git`. No edge was lost. Raising an equality pin to the new true value is how the pin is meant to be maintained.

After the fold, every new rule gets a self-test case with an adjacent negative and a mutation killed by it, verified in a full clone. The live inventory must still show zero errors on the 12 existing rows.
