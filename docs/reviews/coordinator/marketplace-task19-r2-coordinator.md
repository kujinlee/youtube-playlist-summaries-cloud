# Round 2 — `marketplace-task19` — coordinator — two inputs still reach a traceback: a huge integer cost, and a scan finding whose id is not a string

```yaml
round: 2
fixes_nontrivial: true
subject: marketplace-task19
halves:
  codex: ran
  claude: "GAP: alternation"
findings:
  - {id: X1, severity: Major, aim: deliverable, fix_induced: true, component: shape, disposition: fixed}
  - {id: X2, severity: Major, aim: deliverable, fix_induced: false, component: inputs, disposition: fixed}
```

Codex reviewed 63d5b48e, the round 1 fold of plan Task 19 (PR #618): [`codex/marketplace-task19-r2-codex.md`](../codex/marketplace-task19-r2-codex.md). Verdict NOT CONVERGED. Loosening answer: "not a loosening".

REVIEW GAP: claude — alternation

What held in round 2:
- self-test 215/215;
- 8 sampled mutations (6 of them new in the fold), each killed by its named case in a full clone;
- NaN, Infinity and -Infinity are rc 2 in all four input files.

## Is this thrashing?

Not yet. Round 1's findings were all `fix_induced: false`, so this is the first fix-induced round for this subject. If round 3 again finds a defect caused by this fold, in the same component, Phase 6 arms for `check-inventory.py`'s shape pass. Round 3 is the round cap's last full round (`review-method.md` §0 Q4c).

## Dispositions

- **X1 (MAJOR, fix-induced): `10**400` as a cost estimate raises `OverflowError` inside `_finite`. ACCEPT.**
  - Python's `math.isfinite` converts its argument to a float, and an integer too large for a float raises instead of returning False.
  - Fix: `_finite` returns False for such an integer, so the row gets a `[shape]` error. The exception class goes; nothing is caught around the whole pass.
  - Check the same thing against every numeric field in `ROW_SCHEMA`, not only the cost estimates.
  - **Fixed in d56f267c.** `_finite` answers an integer by `abs(v) <= sys.float_info.max` before any float conversion. The class check covers the three numeric fields `_finite` guards (`cost.public_bar_hours`, `cost.next_project_hours`, `route.cost_hours`), each at `10**400` and `-10**400` (`[shape]`), with `10**300` as the adjacent negative (clean). The fourth numeric field, `effort`, is an integer compared by `!=`, so `10**400` there is a `[map]` error, not a traceback. One CLI case puts a 401-digit cost into `inventory.json` and gets rc 1 with `ep: [shape]`; the 301-digit negative gets rc 0. Of the new X1 cases, 8 are red against c9228bbf's code with `RAISED OverflowError`. Mutations "an integer past the float range reaches math.isfinite" and "an integer is never finite" are each killed by the case they name.
- **X2 (MAJOR): a scan finding `{"id": []}` raises `TypeError` in `row_errors`. ACCEPT.**
  - Round 1's input validation checked that each finding is an object, but never checked its `id`.
  - Fix: the scan validation requires every finding's `id` to be a string, else rc 2 CANNOT RUN.
  - The class check: every field of a scan, sidecar or map entry that a rule later reads is validated at load time. List the fields the rules read and confirm each one is.
  - **Fixed in d56f267c.** `_check_inputs` runs at load and gives rc 2 CANNOT RUN on the first wrong-typed field. The fields come from reading every `ctx.`, `scan`, `sidecar` and `recall` access in `row_errors`, `_backs`, `_named_entry_point`, `inventory_errors` and `load`, and its docstring lists them:
    - `components.json`: each component an object, with `id` a non-empty string, `effort` an integer, `roles` a list of strings, and `phase` and `package` strings; each package an object with a string `channel`.
    - `shipping-sets.json`: each package an object with a `components` object.
    - The scan: EVERY entry, not only the map's, because a row whose id is outside the map still reads `scan.get(rid)`. Each entry is an object whose `findings` is a list of objects, each with a string `id`.
    - The sidecar: every entry an object with boolean `exercised` and `operation_ok`, `scenario` a string or null, and `pass_conditions` an object of strings.
    - `inventory.json`: `recall` an object.

    There are 26 bad-input cases at rc 2 and 9 same-type negatives that stay readable. Of these, 24 are red against c9228bbf's code. Two are not: a component id that is a list, and a component id that is missing. The old map-coverage loop already refused both, and they stay as regression cases. The blank-id case is red only with a scan entry under the blank id, which is how it is built. All 124 mutations, 26 of them new, are killed and attributed to the case they name in a full clone with `node_modules` (`check-plan-code.py --mutate . --only scripts/check-inventory.py`: "124 killed, 124 attributed, 0 survivor(s)").
- **Fuzz pass (r2 fold).** Every node, at every level, of all five JSON inputs was replaced by 21 fixed wrong-typed values (including `10**400`, `[{"id": []}]`, `{}` and `[]`), by 6 seeded random nested values, and by deletion. This ran over the live tree and two fixture worlds: the self-test's clean CLI tree, and a variant that adds an effort-1 phase-1 row, a row outside the map, and experiment, spec and c5 grounds. In the scan, list items past the second, and entries no row names, were sampled out. Before the fold there were 11 distinct crash sites, X1 and X2 among them. The others were a non-object component, an unhashable component package (two sites), non-list component roles, a non-object map package or shipping-set package, a non-iterable shipping-set `components`, and a non-object sidecar entry or `pass_conditions`. Two crashes that do not come from JSON values were found by hand: JSON nested 200000 deep (`RecursionError`) and a spec or practices file that is not UTF-8 (`UnicodeDecodeError`). After the fold there were 0 crash sites in 83,727 runs, and every exit was rc 0 to 3.

Each fix gets a case that goes red before the fix, an adjacent negative, and a mutation killed by that case, verified in a full clone with `node_modules` present (Codex's clone lacked `typescript`, so its sweep could not run).
