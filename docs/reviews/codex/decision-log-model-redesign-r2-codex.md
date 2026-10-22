<!-- codex-review: model=gpt-6.1-sol -->

**NOT CONVERGED — 6 High / 3 Medium.** Round 2 introduces new defects in `log-schema`, satisfying §5’s own condition for **DEFER**, rather than a third redesign.

I read both r1 halves and the coordinator record before reviewing the rewrite. Verification used read-only inspection and pure-function probes; no repository files were written, no git writes occurred, and no test or mutation sweep ran.

1. **High — #324 remains open: one attempt still hides every other missing unit.**  
   `component: starvation-ratchet` · `fix_induced: true`  
   **Location:** §2.4 RULE; §8 XH2 closure.

   The new rule fires when a pair has **“no attempt rows.”** It does not fire when the component-derived unit set contains uncovered units.

   Construction: an eligible round names seven components, has one attempt for A, and has no `units_not_logged` declaration. The stated predicate returns false; B–G disappear. My literal predicate probe printed:

   ```
   literal ratchet fires False
   uncovered {'B', 'C', 'D', 'E', 'F', 'G'}
   ```

   Dropping `units_decided` removes the incorrect arithmetic but restores the original existential test at round granularity. §8’s “counts attempt rows per pair” does not close XH2. The required quantity is the **set difference** between component obligations and attempted or explicitly excused units.

2. **High — `ratchet_epoch` is activated by the evidence whose absence it must detect.**  
   `component: starvation-ratchet` · `fix_induced: true`  
   **Location:** §2.4’s final paragraph; T4/T6.

   The epoch is defined as **“the first round for which epoch-2 rows exist.”** Construct a new, post-`armed_at` subject with findings but no epoch-2 rows. There is no first expressible round, so the design supplies no boundary against which starvation can fire.

   The same problem persists if this is a global boundary: delay the first epoch-2 row until round 10, and rounds 1–9 become pre-epoch by definition. T6 additionally appends retrospective epoch-2 attempts, making “first” ambiguous between historical round and append order.

   CH6’s domain ambiguity has moved into a new name. The activation boundary must exist independently of whether anybody feeds the log.

3. **High — Observation references do not uniquely identify attempts.**  
   `component: log-schema` · `fix_induced: true`  
   **Location:** §2.1; T2.

   An observation identifies its target by `{unit, round}` within its subject. Nothing prohibits two strictly increasing attempts for that unit in the same round.

   Construction:

   ```
   attempt S/U, round 1, accrete
   attempt S/U, round 1, redesign
   observation S/U, attempt={unit: U, round: 1}
   ```

   Both attempts satisfy §2.2. Both match the observation reference; my identity probe returned **2 matches**. “Must exist and be unscored” cannot resolve which prediction, route or bet is being scored.

   The split closes the original rung-consumption collision, but its replacement needs a unique attempt identity—or an explicit uniqueness restriction. Without that, the claimed one-observation-per-attempt bound is not enforceable unambiguously.

4. **High — The row-kind fix breaks t3, which §3 declares unchanged.**  
   `component: log-schema` · `fix_induced: true`  
   **Location:** §2.1; §3 t3.

   The real `t3_routes_collapsed` selects rows carrying outcomes, then reads their `route`. New observation rows carry the outcomes; attempt rows carry the routes.

   I passed five attempt/observation pairs to the unchanged function, with attempted routes:

   ```
   ['accrete', 'redesign', 'split', 'defer', 'accrete']
   ```

   Its actual output was:

   ```
   all 5 scored rows took route None — the routes are not discriminating,
   so this is a conveyor wearing a decision's clothes
   ```

   This is a false FAIL over deliberately varied routes. A resolved attempt/observation projection must feed t3; leaving it unchanged is incorrect. This is the trigger missed by the second “all seven re-derived” claim.

5. **High — t4’s subject-termination defect is explicitly deferred, not closed.**  
   `component: log-schema` · `fix_induced: false`  
   **Location:** §3 t4; T5; §8 XH5 closure.

   The rewrite itself says **“terminated subject” is still undefined** and T5 says its definition is **“owed.”** That acknowledges XH5 without resolving it.

   The r1 counterexample therefore remains: five subjects each have one stopped unit and another pending unit. The design still provides no predicate distinguishing those subjects from terminated subjects.

   Excluding skip-bearing subjects answers a separate comparability problem. It does not establish that the remaining subjects terminated. §8 cannot claim XH5 closed while the governing definition remains an implementation task.

6. **High — The t2 repair makes identical terminal decisions pass or fail according to attempt count.**  
   `component: log-schema` · `fix_induced: true`  
   **Location:** §3 t2; T3.

   The document explains the exemption semantically: **DEFER means stop and file; `continued` is expected.** But it implements that explanation as **≥2 attempts**.

   Construction under the stated predicate:

   ```
   [defer]          + continued → quiet
   [accrete,defer]  + continued → FAIL
   ```

   Both finish with exactly the terminal action the document says legitimately leaves findings. The second merely has prior history. Conversely, direct DEFER now avoids the primary falsifier permanently, regardless of subsequent findings.

   CM4 has been replaced with a history-length exception. The design must decide what constitutes failed termination after DEFER and test that property consistently.

7. **Medium — Skip exclusion leaves t4 without an effectiveness test for the population the redesign enables.**  
   `component: log-schema` · `fix_induced: true`  
   **Location:** §2.3.

   The proposed falsifier demonstrates this limitation: five skipped subjects produce **“0 comparable subjects, 5 excluded.”** That prevents a false improvement claim, but supplies no effectiveness verdict.

   Extend the construction to every future subject using at least one skip. Whether those subjects finish in one round or remain costly for twenty rounds, none contributes to t4. The diagnostic count is visible; the failure trigger has lost its sample indefinitely.

   CH2 is partially addressed, but the design needs an explicit insufficient-evidence consequence or a comparable measure for the new regime. Reporting exclusions alone does not preserve the instrument’s ability to reject ineffective ceremony.

8. **Medium — §7’s replacement falsifier has no established reference answer for one case and an ambiguous answer for the other.**  
   `component: ranker-caller` · `fix_induced: true`  
   **Location:** §7 “FALSIFIER THAT CAN FAIL.”

   `rounds_for("ship-src-root-alone")` genuinely raises on `L4`’s `disposition='refuted'`; that correction is confirmed.

   The replacement test is not yet operational:

   - Searching the architecture reviews found no review convened on `peer-sites`. Its appearance in the decision-family review concerns round-one flags, not a choice between `activation` and `parse-hunks`.
   - The decision-route architecture review explicitly names displaced `corpus-cannot-run` in its arming, while its findings table puts `log-schema` first by volume. “If either names the component the tuple displaces” literally rejects the tuple; interpreting “names” as “endorses as the appropriate focus” requires a criterion the design never states.

   The test can fail literally, but does not yet discriminate ranking quality. CH1 needs identified reference passages and a defined comparison, rather than an instruction to discover labels during evaluation.

9. **Medium — The gap-derivation owner is named incorrectly, preserving the ownership defect.**  
   `component: ranker-caller` · `fix_induced: true`  
   **Location:** T7; §8 CM6 closure.

   T7 names **`check-review-decision.component_rounds`** as the existing owner. Inspection and an import probe establish:

   ```
   check-review-decision: component_rounds absent
   check-decision-scheme.py:312: def component_rounds(...)
   ```

   CM6 specifically required identifying the owner so the ranking change imports rather than duplicates the derivation. The closure points at a nonexistent function and specifies no relocation. It is not an implementable ownership decision.

The remaining r1 closure audit is as follows. “Closed” here means the design states the necessary correction, not that unimplemented code has passed verification.

| R1 findings | Round 2 assessment |
|---|---|
| XB1, CB1 | Original lifecycle and legacy-field collisions addressed by row kinds and epoch rules; replacement identity defect is finding 3. |
| CB2, XM8 | Noise-safety claim withdrawn; saturation reporting specified. Replacement evaluation defect is finding 8. |
| CB3 | Correct component source and corrected population adopted; starvation behavior remains defective, findings 1–2. |
| XH2, CH3 | Bad denominator removed; omission detection remains open, finding 1. |
| XH3 | Closed for explicitly clean, component-free rounds. |
| XH4 | Record ordering addressed; imports explicitly excluded from t5/t7. This establishes recorded prospectivity only, as the rewrite acknowledges. |
| XH5 | Open, finding 5. |
| CH1 | Replacement remains inadequate, finding 8. |
| CH2 | Partial; exclusion introduces finding 7. |
| CH4 | Closed: inequality is placed in `validate_row`, empty history defined, advice separated. |
| CH5 | Closed: abstentions explicitly **break** miss runs; they are not filtered away. |
| CH6 | Partial; activation remains circular, finding 2. |
| XM6 | Wrong-population figures corrected. |
| XM7, CM1, CM5 | False measurement claims corrected; prose `ranker` preserved. |
| CM2 | Closed: `(subject, unit)` explicitly remains the ladder key. |
| CM3 | Caller-level regression construction specified through real `main()`. |
| CM4 | Replaced by inconsistent attempt-count exception, finding 6. |
| CM6 | Open, finding 9. |
| CM7 | Correct escalation table explicitly targeted. |
| CL1 | Deletion explicitly specified. |

The **3-of-4 grouping remains useful**, but its causal slogan is broader than its evidence. #324 is a subject-to-unit coverage defect; #325 loses abstention state. #321 is a route-admissibility restriction: the existing log already has unit identity, and the proposed repair changes the validator’s ordering policy. It belongs in the same workstream, but does not independently establish that `(subject, prediction)` projection caused all three.

`i(∅) = -1` correctly admits first-row skips under the chosen policy. A first-row DEFER with an unfalsifiable citation is consequently permitted; §2.2 expressly bounds validation to citation presence. The consequential defects are how t2 and t4 interpret that permission, not the arithmetic of the empty-history index.

**NOT CONVERGED.** New fix-induced `log-schema` findings satisfy this document’s stated **DEFER** condition.
