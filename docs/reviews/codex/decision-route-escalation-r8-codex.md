<!-- codex-review: model=gpt-6.1-sol -->

Found **3 Medium and 1 Low** issues. No Blocking or High runtime defect demonstrated in the submitted fold.

1. **Medium — both new WARNs can be disconnected while 201/201 stays green.**  
   At `scripts/check-decision-scheme.py:1095` and `:1096`, independently replace the t8 or t9 call with `None`. **Observed:** each mutation passes all 201 cases. The pure-function cases therefore do not prove either warning reaches the CLI.

   Fix: add `main()` cases asserting the emitted warning and rc=0 for hindsight-only use and for five prospective terminations with a deferral-composed improving median. Add separate mutations severing both call sites.

2. **Medium — t9’s duplicated recency decision is unprotected, permitting the exact two-guard silence hazard.**  
   At `scripts/check-decision-scheme.py:389`, delete t9’s `per_subject.pop(...)`. **Observed:** 201/201 still passes.

   Concrete input, in row order, with baseline 4:
   ```
   subject: a b c d e f a
   rounds:  9 9 9 1 1 9 1
   route:   accrete throughout, except final a = defer
   ```
   All rows are prospective stopped terminations.

   **Submitted code:** t4 returns `None`; t9 reports median 1 with one deferral.  
   **Mutated code:** both return `None`. t9 retains first-insertion order, computes median 9, and incorrectly assumes t4 owns the window.

   Fix: exercise repeated subjects in t9’s tests and mutate its recency update independently. Sharing the window producer would also remove this duplicated decision.

3. **Medium — one of the seven manifest re-points changes the decision being measured.**  
   `scripts/mutations/check-decision-scheme.json:450` claims to restore ordering “by FIRST insertion.” Its replacement at `:454` instead changes `[-5:]` to `[:5]`, leaving the pop/reinsert logic intact.

   **Input:** execute that manifest entry.  
   **Observed:** it kills the named case, but measures **first five versus last five**, not **first insertion versus latest occurrence**. Those are different defects. Independently removing t4’s pop does fail the existing named case, so the original decision remains testable.

   Fix: restore a uniquely anchored deletion of t4’s pop. Keep the first-five mutation separately if desired. The other six re-points retain their stated decision.

4. **Low — the published fold measurement understates the final suite.**  
   `docs/dashboard-entries.md:16433` and `docs/roadmap-to-launch.md:2525` say **179 → 200 cases**. **Observed:** the delivered suite reports **201/201**; the commit message correctly says 201.

   Fix: update both records to the final measured count.

Verification and limits:

- Normal invocation: **rc=0**, exactly WARNs **6 and 8**.
- Self-test: **201/201**, rc=0.
- Fixture variation: **rc=0**, 960 parameters across 70 files.
- Parsed declarations: **80** for this file; **1696** total.
- An additional **in-memory** sweep over the 80 entries had a green 201-case control and **80/80 kills, 79/80 named attributions**. The unmatched attribution was the pre-existing repository-redirection mutation; this run used the real repository rather than the harness’s staged environment. This does **not** disprove the recorded 80/80 attribution.
- **Official scoped harness sweep with both control pins adjusted: NOT RUN.** The “56 scripts verified by running them” and historical CI claims were not independently reproduced.

For the submitted code, t4 and t9 use identical population, ordering, and median calculations; I found no uncovered handoff window. Missing/null subject rows do not satisfy a named armed subject in t8, and subjects outside `subjects_since_arming` are excluded consistently from its numerator and denominator. H3’s malformed-history examples produce false refusal or a crash for direct callers, but are unreachable through `main()`’s validated, per-`(subject, unit)` history. Likewise, non-boolean `ranker_hit` changes t5’s direct-call behavior as intended; validation rejects it before CLI trigger evaluation, and `--rederive` never evaluates t5.
