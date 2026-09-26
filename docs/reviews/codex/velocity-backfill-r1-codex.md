<!-- codex-review: model=gpt-5.5 -->

**Blocking**

None.

**High**

severity: High  
component: backfill-label-surface  
aim: deliverable  
fix_induced: false  
evidence: The rendered goals page makes #177 visible without carrying the backfill warning. It shows `review-decides-itself`, `2026-09-25-development-velocity`, and links to the spec/plan, but no “retrospective”, “reconstructed”, “backfill”, or “not planned here” caveat: `/Users/kujinlee/explainers/goals.html:187`, `/Users/kujinlee/explainers/goals.html:199`, `/Users/kujinlee/explainers/goals.html:204`, `/Users/kujinlee/explainers/goals.html:205`, `/Users/kujinlee/explainers/goals.html:206`. The plan itself says the label is “the whole mitigation” and that removing it makes the document the thing #119 refused: `docs/superpowers/plans/2026-09-25-development-velocity.md:26`–`31`. This fails the central labeling claim on the exact surface these files were created to reach.

**Medium**

severity: Medium  
component: derived-measurement-copy  
aim: deliverable  
fix_induced: false  
evidence: The spec says its job is design and `development-velocity.md` owns measurements/history, then immediately re-copies live derived measurements: sweeps, rework rounds, gate counts, token estimates, CI timings, mutation count, and `check-plan-code.py:501`: `docs/superpowers/specs/2026-09-25-development-velocity-design.md:63`–`67`, `:71`–`83`, `:184`–`186`. That duplicates `docs/development-velocity.md:40`–`52` and violates the repo’s own derived-value rule: `docs/portable-practices.md:1265`–`1305`, especially “A document cannot hold a derived value honestly.” Command reproduction confirms at least one copied datapoint is a live API observation rather than design: `gh api repos/kujinlee/youtube-playlist-summaries-cloud/actions/jobs/107877398501` returned `verify` `2026-09-24T23:27:35Z`→`23:38:55Z` = 680s, mutation step `23:29:35Z`→`23:38:49Z` = 554s, tests `23:28:27Z`→`23:28:54Z` = 27s.

severity: Medium  
component: concern-mechanism-table  
aim: deliverable  
fix_induced: false  
evidence: The table claims “One mechanism per concern; no mechanism appears twice,” but Q0 appears in three mechanisms: whole Q0 at `docs/superpowers/specs/2026-09-25-development-velocity-design.md:180`, Q0’s entry half at `:181`, and Q0’s escalation half at `:182`. The table’s invariant is false on its face.

severity: Medium  
component: shape-invariant-history  
aim: deliverable  
fix_induced: false  
evidence: The backfilled spec/plan say the shape invariant was “written at round 4 after four pattern-shaped fixes each failed to terminate”: `docs/superpowers/specs/2026-09-25-development-velocity-design.md:107`, `docs/superpowers/plans/2026-09-25-development-velocity.md:63`–`64`. The governing adopted text says “FIVE consecutive attempts” and lists the sequence: `docs/process-checklists.md:599`–`601`. The round history also includes a Phase 6 architecture review between rounds 3 and 4 as the root-cause step, which the reconstruction omits from that claim: `docs/reviews/coordinator/velocity-177-r6-coordinator.md:53`–`58`.

severity: Medium  
component: task-3-hole-owner  
aim: deliverable  
fix_induced: false  
evidence: The plan says Task 3’s Q0 gap is “THE HOLE TASK 4 CLOSES”: `docs/superpowers/plans/2026-09-25-development-velocity.md:70`–`73`. But Task 4 is only retrospective calibration: `:77`–`:92`. Task 5 is the task that actually closes the hole: `:94`–`:102`. This misroutes forward work inside the plan.

severity: Medium  
component: checkbox-evidence-label  
aim: deliverable  
fix_induced: false  
evidence: The plan’s global warning is strong, and the first checkbox in each reconstructed task is labelled, but the following checked boxes read as ordinary completed implementation-plan steps with no local caveat: Task 1 at `docs/superpowers/plans/2026-09-25-development-velocity.md:39`–`45`, Task 2 at `:53`–`64`. A reader who skips the banner and scans checked boxes can still read Tasks 1–2 as planned-and-executed evidence. The mitigation is present, but it does not travel with every checked claim.

**Low**

None.
