<!-- codex-review: model=gpt-6.1-sol -->

1. **Blocking — The model cannot append an outcome without consuming another route.**  
   **Component:** row lifecycle / migration (§2.1, §4, T6). **fix_induced:** true.

   The existing log has two pending REDESIGN rows. T6 preserves them and appends successors, while §4 requires every successive row for a unit to increase its route index. How does the REDESIGN attempt subsequently become `stopped` or `continued`?

   Appending its result at REDESIGN is a forbidden retry. Appending at SPLIT records an attempt that need not have happened. Editing the pending row violates append-only. Moreover, the existing rows lack the newly required fields; adding successors does not make those earlier rows validate.

   This is the missing distinction between an **attempt** and an **observation about that attempt**. Define their identities, update semantics, and legacy interpretation before claiming the new model can record the truth.

2. **High — The starvation arithmetic still counts a projection rather than decided units.**  
   **Component:** `t1_not_fed` (§2.4). **fix_induced:** true.

   The denominator is units, but the numerator explicitly counts rows. The proposed rules permit several increasing route attempts for one unit in the same round; no uniqueness constraint on `(subject, round, unit)` is stated.

   Construct seven rows in one round: four increasing routes for unit A and three for unit B, with truthful skip citations where needed. Declare `units_decided: 7`. The arithmetic passes although five decided units remain absent. Even without this construction, different rows can declare inconsistent denominators; the design specifies no authoritative declaration.

   `2 rows < 7 declared` is constructible, but it does not establish the intended invariant. Count distinct decided-unit identities and define denominator consistency. An authored declaration can provide attribution, but this arithmetic currently attributes the wrong quantity.

3. **High — The rule cannot represent a round that legitimately decides zero routes.**  
   **Component:** starvation eligibility (§2.4, T4). **fix_induced:** true.

   A clean final review round can contain no findings and require no route decision. The proposed rule nevertheless fires whenever a corpus `(subject, round)` has no rows. Its row schema requires a unit and a route, so recording an honest zero-decision round is impossible.

   Filename readability establishes that a round exists; it does not establish that the round owes a route decision. Specify an explicit zero-decision record or an eligibility rule. Otherwise “works on 100% of the corpus” means every filename can be enumerated, while some valid rounds cannot satisfy the gate.

4. **High — The claimed prospective bet is still writable only with hindsight.**  
   **Component:** bet lifecycle (§2.1, §2.2, §2.5). **fix_induced:** true.

   `bet` becomes mandatory only when `outcome` is set. A pending row can therefore omit it, and the eventual scored record can introduce both the prediction and its result together. Nothing establishes that `bet.named` existed before observation.

   Likewise, append-only does not prove that `skipped.observation` preceded the outcome: a complete historical row can be appended after both are known. T6 expressly imports historical decisions.

   The stated benefit—citation and betting **before** outcome—does not follow from this schema. Separate prospective records from retrospective imports and require scoring to reference an already recorded bet.

5. **High — The “all seven triggers re-derived” claim leaves the same projection error in t4.**  
   **Component:** `t4_no_improvement` (§3). **fix_induced:** true, inherited from the earlier row-to-subject aggregation fix.

   Collapsing stopped rows by subject does not establish that their subjects terminated. I probed five subjects, each with one unit marked `stopped` at round 1 and another unit still pending. `t4_no_improvement(..., 4)` returned `None`: those partial unit successes populate its five-subject sample.

   With the proposed broader unit coverage, this discrepancy becomes more consequential. The unchanged `len(per_subject) < 5` guard and sampling logic still concern subjects with **a stopped unit**, rather than terminated subjects.

   This is a fifth instance predicted by the unification claim and missed by the redesign itself. Subject termination needs its own definition and evidence.

6. **Medium — The load-bearing readability measurement uses the explicitly rejected population.**  
   **Component:** corpus measurement (§2.4, §5). **fix_induced:** false.

   `baseline.json` explicitly preserves **57** under `corpus_ORIGINAL_WRONG`; the corrected baseline has **81** eligible subjects. On the current disk, `_round_docs()` yields **105 subjects, 82 with at least two rounds**. Calling `rounds_for()` across that eligible population yields **11 nonempty, fully readable subjects**: approximately **13.4%**, not 18%.

   Poor readability remains real, but the document repeats the exact wrong-population measurement it invokes as a warning. Its corpus-wide percentage, retirement threshold, and ranking evaluation need a named, reproducible population.

   The same probe found **6 abstentions among 11 readable subjects** under the existing ranker and **2 under the proposed tuple**. The three named calibration winners remain first. Those results support the proposed fit check, but they are not the document’s stated 5-of-10 experiment.

7. **Medium — Today’s t5 falsifier is reachable; the central diagnosis overstates #325.**  
   **Component:** unification / bet measurement (§1, §2.5). **fix_induced:** false.

   Two rows on distinct units, each with `route: "accrete"`, `outcome: "continued"`, and `ranker_hit: false`, both pass `validate_row(row, [])`. Driving the real `main()` over that temporary log returns **`rc=1`, FAIL trigger 5**.

   Therefore “two consecutive misses are … inexpressible,” “the trigger has no falsifier,” and “Today no log can do that” are false. Missing bets evade scoring; explicit misses are already expressible.

   Explicit abstention is still a worthwhile repair, and the zero-bet t7 output reproduced exactly. But #325 combines ambiguous missingness and an incorrect scoring denominator—not an inability to express misses. The unification must survive that corrected diagnosis.

8. **Medium — Equal recurrence does not make finding volume noise-safe.**  
   **Component:** ranking evidence (§2.3). **fix_induced:** true.

   Construct two components appearing in the same three rounds with equal findings. Add several findings for one component in just one round. Recurrence and gap structure remain identical, but `total_findings` now produces a unique lead.

   The tuple preserves recurrence’s priority; it does not preserve immunity to noisy-round volume when recurrence ties. That is precisely the saturated case this redesign targets. Reducing abstentions can therefore mean manufacturing confidence from the previously rejected signal.

   The 3-of-3 fit and lower abstention count do not falsify this failure. State the tradeoff and test whether volume-driven leads are useful rather than treating fewer abstentions as sufficient evidence.

The independent probes **confirmed** the seven-unit-history refusal (`rc=2`, no triggers evaluated), t1’s identical response to one versus two logged units, the malformed abstention refusal text, the zero-bet t7 warning, and t2’s skipped exhaustion case.

Strict increase does prove at most four **route attempts per stable unit identity**. It does not prove eventual observation, subject termination, or completion of the review loop. Its overall simplicity claim also omits the new skip-validation and lifecycle obligations.

**NOT CONVERGED**
