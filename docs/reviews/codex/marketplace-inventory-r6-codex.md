<!-- codex-review: model=gpt-6-astra -->

**NOT CONVERGED: one Medium, one Low. No Blocking or High findings.** No implementation changes made.

1. **Medium — the root-file predicate still disagrees with its consumer.** `scripts/check-canonical-source.py:294–295`

   From a checkout named `live`, `../live/CONTEXT.md` names an existing root file through `root / cite_rel`, but `root_level_cites()` returns `[]`. Absolute paths to that file also escape.

   Executed `python3 /tmp/r6-extra.py`, using production functions and separate live/staged trees:

   ```text
   PARENT ROUNDTRIP predicate [] live audit []
   staged audit ['../live/CONTEXT.md is declared a citing site but does not exist']
   ABSOLUTE synthetic existing root file: [] True
   ```

   I also injected `../wt-marketplace/CONTEXT.md` into the actual live CANONS table in memory and executed its suite:

   ```text
   parent-roundtrip LIVE table self-test rc 0
   29/29 passed
   live audit []
   ```

   Thus the new invariant still permits the staged-control failure it exists to prevent. Absolute registrations can instead read the original checkout from inside the staged tree.

   Classify paths against the consumer’s root and reject nonportable registrations. Add parent-roundtrip and absolute-path cases.

2. **Low — the new ratchet history incorrectly claims `18 -> 19`.** `scripts/check-plan-code.py:652–655`

   The fix extended an existing mutation’s expectations; it added no nineteenth mutation. The later comment correctly says `18 -> 18`.

   Executed `python3 /tmp/r6-account.py`, comparing mutation identities against `8a583f7c^`:

   ```text
   old 32 retained 15 retired 17 added 3 retargeted 4
   TOTAL 8a583f7c^ 1489 claim 32 canon 6
   TOTAL HEAD 1477 claim 18 canon 8
   ```

   The executable counts are correct: `32 - 17 + 3 = 18`, and `1489 - 17 + 3 + (8 - 6) = 1477`. Correct the comment, not the ratchet.

**Executed verification**

| Command/check | Result |
|---|---|
| `check-claim-propagation.py --self-test` | 58/58 |
| `check-canonical-source.py --self-test` | 29/29 |
| `check-plan-code.py --self-test` | 178/178 |
| `check-docs.py --self-test` | 22/22 |
| `check-selftest-counts.py` | All 54 declared script counts verified by executing their suites |
| Scoped `check-plan-code.py --mutate .` | 26 mutations, 26 killed, 26 attributed, 0 survivors; green controls and re-controls |
| Production claim/canonical guards | Green: two derived figures, three mechanisms |

The mutation run used production `stage_tree()` with **all seven HARNESS_TREE paths**, retaining only the two scoped manifests and adjusting the temporary runner’s count registry.

Additional executed adversarial checks:

- **Every expectation is red** for all eight canonical mutations and the extended VOID mutation, verified individually with `python3 /tmp/r6-expects.py`. The retargeted normpath mutation kills; none of the other canonical entries was unfalsifiable.
- Removing each of the **14 VOID members** independently fails its tests. Deriving the loop from `VOID`, without the independent identity case, reproduces **57/57 → 56/56 green** after removing `area`. The coordinator’s objection is valid; no escaping vocabulary divergence found.
- The spelling fixture is independent of CANONS and demonstrably discriminates against removing normalization. Its defect is incomplete input coverage, not an ambient pass.
- The strip mutation produces identical extracted values and audit results on today’s pages. Through a synthetic split-node path carrier, actual `audit()` changes from `([], [])` to a mismatch for `'docs/ file.md'`. The documented distinction holds.
- The renamed workflow step accurately describes its execution. Older comments at `.github/workflows/ci.yml:330–335` still misidentify the preceding guard and say three searched extensions instead of four. `git blame` places those statements before this range.

**“Document guards 54/54” needs qualification.** The 54 verified items are declared self-test counts. My separate production sweep executed 30 single-line workflow invocations: **28 green, two red**—missing `jest-results.json` and the pending round-6 review record. This was not a full CI run or an unqualified 54/54 production-guard pass.

**Thrashing or prose floor?** `review-method.md:525–526` defines:

> **Thrashing:** findings are **introduced by the previous round's own fix**; severity stays put

> **Prose floor:** findings shift from *"this cannot work"* to *"this is under-specified"*; each round is right and the artifact keeps improving

Per finding: **Medium—yes**, round 5 introduced the incomplete invariant; normalization preserved its gap rather than introducing a consumer regression. **Low—yes**, the inaccurate history was added by that fold. These are fix-induced findings against executable work, not a prose floor. Severity has fallen, so this pass alone does not establish the full “severity stays put” pattern.

**Was scoping wrong?** No demonstrated defect in the excluded documents. Both findings are within the six scoped files. That is not a clean verdict on excluded material, and it does not alter the owner’s pre-committed final-review decision.
